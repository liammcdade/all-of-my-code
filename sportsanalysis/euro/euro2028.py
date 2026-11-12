import random
import math
import numpy as np
from collections import defaultdict
from dataclasses import dataclass, field
from typing import List, Dict, Tuple, Set, Optional
from multiprocessing import Pool, cpu_count
import time
import sys
import argparse
import os

# -------------------------------------------------------------
# 1. CONFIGURATION  (host names WITHOUT trailing spaces)
# -------------------------------------------------------------
@dataclass
class Config:
    num_groups: int = 12
    num_winners: int = 12
    num_best_runners_up: int = 8
    host_safety_slots: int = 2
    hosts: List[str] = field(default_factory=lambda: [
        "England", "Republic of Ireland", "Scotland", "Wales"
    ])
    num_simulations: int = 10000
    home_advantage_elo: int = 73.65
    host_home_advantage: Dict[str, int] = field(default_factory=lambda: {
        "Wales": 40,
        "England": 35,
        "Scotland": 40,
        "Republic of Ireland": 40,
    })
    k_factor: int = 20
    base_goals: float = 1.35
    goal_correlation: float = 0.18
    initial_elo: int = 1500
    elo_min: int = 1200
    elo_max: int = 2400

    def home_boost(self, team: str) -> int:
        return self.host_home_advantage.get(team, self.home_advantage_elo)

CONFIG = Config()

# -------------------------------------------------------------
# 2. DATA MODELS
# -------------------------------------------------------------
@dataclass
class MatchResult:
    home: str
    away: str
    home_goals: int
    away_goals: int

@dataclass
class TeamStanding:
    team: str
    points: int = 0
    gf: int = 0
    ga: int = 0
    matches: List[MatchResult] = field(default_factory=list)

    @property
    def gd(self) -> int:
        return self.gf - self.ga

# -------------------------------------------------------------
# 3. ELO & MATCH SIMULATION ENGINE
# -------------------------------------------------------------
class EloSystem:
    def __init__(self, initial_ratings: Dict[str, int], config: Config,
                 rng: random.Random = None):
        self.ratings = initial_ratings.copy()
        self.config = config
        if rng is None:
            self.rng = random
            self._np_rng = np.random
        else:
            self.rng = rng
            self._np_rng = np.random.default_rng(rng.randrange(2 ** 32))

    def get_rating(self, team: str, is_home: bool = False) -> float:
        base = self.ratings.get(team, self.config.initial_elo)
        return base + (self.config.home_advantage_elo if is_home else 0)

    def update(self, team_a: str, team_b: str, goals_a: int, goals_b: int):
        elo_a = self.ratings.get(team_a, self.config.initial_elo)
        elo_b = self.ratings.get(team_b, self.config.initial_elo)

        if goals_a > goals_b:
            res_a, res_b = 1.0, 0.0
        elif goals_a < goals_b:
            res_a, res_b = 0.0, 1.0
        else:
            res_a, res_b = 0.5, 0.5

        exp_a = 1 / (1 + 10 ** ((elo_b - elo_a) / 400))
        exp_b = 1 - exp_a
        gd_mult = max(1, (abs(goals_a - goals_b) + 1) ** 0.5)

        new_a = elo_a + self.config.k_factor * gd_mult * (res_a - exp_a)
        new_b = elo_b + self.config.k_factor * gd_mult * (res_b - exp_b)

        self.ratings[team_a] = max(self.config.elo_min,
                                   min(self.config.elo_max, new_a))
        self.ratings[team_b] = max(self.config.elo_min,
                                   min(self.config.elo_max, new_b))

    def simulate_goals(self, team_a: str, team_b: str,
                       scale_factor: float = 1.0,
                       neutral: bool = False) -> Tuple[int, int]:
        elo_a = self.ratings.get(team_a, self.config.initial_elo)
        elo_b = self.ratings.get(team_b, self.config.initial_elo)

        if not neutral:
            elo_a += self.config.home_advantage_elo

        rating_diff = elo_a - elo_b
        lam_a = max(0.2, self.config.base_goals *
                    (10 ** (rating_diff / 1000)) * scale_factor)
        lam_b = max(0.2, self.config.base_goals *
                    (10 ** (-rating_diff / 1000)) * scale_factor)

        shared = max(0.0, self.config.goal_correlation *
                     min(lam_a, lam_b))
        shock = self._np_rng.poisson(shared)

        g_a = self._np_rng.poisson(lam_a - shared) + shock
        g_b = self._np_rng.poisson(lam_b - shared) + shock

        return int(g_a), int(g_b)

# -------------------------------------------------------------
# 4. GROUP STAGE
# -------------------------------------------------------------
def generate_fixtures(teams: List[str]) -> List[List[Tuple[str, str]]]:
    n = len(teams)
    if n % 2 != 0:
        teams = list(teams) + ["BYE"]
        n += 1

    first_half = []
    for _ in range(n - 1):
        round_fixtures = []
        for i in range(n // 2):
            home = teams[i]
            away = teams[n - 1 - i]
            if home != "BYE" and away != "BYE":
                round_fixtures.append((home, away))
        first_half.append(round_fixtures)
        teams = [teams[0]] + [teams[-1]] + teams[1:-1]

    second_half = [[(a, h) for h, a in rd] for rd in first_half]
    return first_half + second_half

class GroupStage:
    def __init__(self, teams, elo_system, config, rng=None,
                 matchday_offset: int = 0):
        self.teams = teams
        self.elo = elo_system
        self.config = config
        self.rng = rng if rng is not None else random
        self.standings = {t: TeamStanding(team=t) for t in teams}
        self.matches: List[MatchResult] = []
        self.matchday_offset = matchday_offset

    def simulate(self):
        fixtures_by_matchday = generate_fixtures(self.teams)
        for md_index, matchday_fixtures in enumerate(fixtures_by_matchday):
            for home, away in matchday_fixtures:
                g_h, g_a = self.elo.simulate_goals(home, away)
                match = MatchResult(home, away, g_h, g_a)
                self.matches.append(match)
                self.standings[home].gf += g_h
                self.standings[home].ga += g_a
                self.standings[away].gf += g_a
                self.standings[away].ga += g_h

                if g_h > g_a:
                    self.standings[home].points += 3
                elif g_a > g_h:
                    self.standings[away].points += 3
                else:
                    self.standings[home].points += 1
                    self.standings[away].points += 1

                self.standings[home].matches.append(match)
                self.standings[away].matches.append(match)
                self.elo.update(home, away, g_h, g_a)

    def _get_head_to_head(self, teams_subset: List[str]) -> Dict[str, Tuple[int, int, int]]:
        h2h = {t: (0, 0, 0) for t in teams_subset}
        subset_set = set(teams_subset)
        for match in self.matches:
            if match.home in subset_set and match.away in subset_set:
                pts_h, gd_h, gf_h = h2h[match.home]
                if match.home_goals > match.away_goals:
                    pts_h += 3
                elif match.home_goals == match.away_goals:
                    pts_h += 1
                h2h[match.home] = (pts_h,
                                   gd_h + match.home_goals - match.away_goals,
                                   gf_h + match.home_goals)

                pts_a, gd_a, gf_a = h2h[match.away]
                if match.away_goals > match.home_goals:
                    pts_a += 3
                elif match.away_goals == match.home_goals:
                    pts_a += 1
                h2h[match.away] = (pts_a,
                                   gd_a + match.away_goals - match.home_goals,
                                   gf_a + match.away_goals)
        return h2h

    def get_sorted_teams(self) -> List[str]:
        def tiebreaker_key(team_name: str):
            s = self.standings[team_name]
            tied_teams = [t for t in self.teams
                          if self.standings[t].points == s.points]
            if len(tied_teams) > 1:
                h2h = self._get_head_to_head(tied_teams)
                h2h_pts, h2h_gd, h2h_gf = h2h[team_name]
            else:
                h2h_pts, h2h_gd, h2h_gf = 0, 0, 0

            wins = sum(1 for m in s.matches
                       if (m.home == team_name and m.home_goals > m.away_goals)
                       or (m.away == team_name and m.away_goals > m.home_goals))
            away_wins = sum(1 for m in s.matches
                            if m.away == team_name
                            and m.away_goals > m.home_goals)
            away_gf = sum(m.away_goals for m in s.matches
                          if m.away == team_name)
            discs = self.rng.randint(-10, 0)
            coeff = self.elo.ratings.get(team_name, self.config.initial_elo)

            return (-s.points, -h2h_pts, -h2h_gd, -h2h_gf,
                    -s.gd, -s.gf, -away_gf, -wins, -away_wins,
                    discs, -coeff)

        return sorted(self.teams, key=tiebreaker_key)

# -------------------------------------------------------------
# 5. KNOCKOUT
# -------------------------------------------------------------
class KnockoutMatch:
    @staticmethod
    def single_leg(elo: EloSystem, team_a: str, team_b: str) -> str:
        g_a, g_b = elo.simulate_goals(team_a, team_b)
        if g_a != g_b:
            return team_a if g_a > g_b else team_b
        et_a, et_b = elo.simulate_goals(team_a, team_b, scale_factor=0.33)
        g_a += et_a; g_b += et_b
        if g_a != g_b:
            return team_a if g_a > g_b else team_b
        return KnockoutMatch.penalties(elo, team_a, team_b)

    @staticmethod
    def home_away(elo: EloSystem, team_a: str, team_b: str) -> str:
        g_a1, g_b1 = elo.simulate_goals(team_a, team_b)
        g_b2, g_a2 = elo.simulate_goals(team_b, team_a)
        agg_a = g_a1 + g_a2
        agg_b = g_b1 + g_b2
        if agg_a != agg_b:
            return team_a if agg_a > agg_b else team_b
        et_b, et_a = elo.simulate_goals(team_b, team_a, scale_factor=0.33)
        agg_a += et_a; agg_b += et_b
        if agg_a != agg_b:
            return team_a if agg_a > agg_b else team_b
        return KnockoutMatch.penalties(elo, team_a, team_b)

    @staticmethod
    def penalties(elo: EloSystem, team_a: str, team_b: str) -> str:
        diff = elo.ratings.get(team_a, 1500) - elo.ratings.get(team_b, 1500)
        prob_a = 1 / (1 + math.exp(-diff / 150))
        return team_a if elo.rng.random() < prob_a else team_b

class PlayoffPath:
    @staticmethod
    def simulate_bracket(elo: EloSystem, teams: List[str]) -> str:
        w1 = KnockoutMatch.single_leg(elo, teams[0], teams[1])
        w2 = KnockoutMatch.single_leg(elo, teams[2], teams[3])
        return KnockoutMatch.single_leg(elo, w1, w2)

# -------------------------------------------------------------
# 6. HOST QUALIFICATION
# -------------------------------------------------------------
class HostManager:
    @staticmethod
    def _overall_ranking_key(team: str, gs: GroupStage, config: Config,
                             rng: random.Random) -> Tuple:
        s = gs.standings[team]
        group_size = len(gs.teams)
        valid_matches = s.matches
        if group_size == 5:
            sorted_teams = gs.get_sorted_teams()
            fifth_place = sorted_teams[4]
            valid_matches = [m for m in s.matches
                             if m.home != fifth_place and m.away != fifth_place]

        pts = gf = ga = away_gf = wins = away_wins = 0
        for m in valid_matches:
            if m.home == team:
                gf += m.home_goals; ga += m.away_goals
                if m.home_goals > m.away_goals:
                    pts += 3; wins += 1
                elif m.home_goals == m.away_goals:
                    pts += 1
            else:
                gf += m.away_goals; ga += m.home_goals; away_gf += m.away_goals
                if m.away_goals > m.home_goals:
                    pts += 3; wins += 1; away_wins += 1
                elif m.away_goals == m.home_goals:
                    pts += 1

        group_position = gs.get_sorted_teams().index(team) + 1
        fair_play = rng.randint(0, 15)
        nl_rank = ELO_RATINGS.get(team, config.initial_elo)
        return (-group_position, -pts, -(gf - ga), -gf, -away_gf,
                -wins, -away_wins, fair_play, -nl_rank)

    @staticmethod
    def get_overall_ranking_for_runners_up(runners_up, group_stages,
                                           config, rng):
        def key(team):
            for gs in group_stages.values():
                if team in gs.standings:
                    return HostManager._overall_ranking_key(
                        team, gs, config, rng)
            return (0,) * 9
        return sorted(runners_up, key=key)

    @staticmethod
    def resolve(winners, runners_up, group_stages, config, rng, all_teams):
        hosts = config.hosts
        direct = set(winners)
        runners_up_ranked = HostManager.get_overall_ranking_for_runners_up(
            runners_up, group_stages, config, rng)
        best_runners_up = runners_up_ranked[:config.num_best_runners_up]
        direct.update(best_runners_up)

        unqualified_hosts = [h for h in hosts if h not in direct]

        def host_key(host):
            for gs in group_stages.values():
                if host in gs.standings:
                    return HostManager._overall_ranking_key(
                        host, gs, config, rng)
            return (0,) * 9

        unqualified_hosts_ranked = sorted(unqualified_hosts, key=host_key)
        host_safety_teams = unqualified_hosts_ranked[:config.host_safety_slots]
        host_safety_set = set(host_safety_teams)
        direct.update(host_safety_set)

        while len(direct) > 24:
            lowest_ru = next((t for t in reversed(runners_up_ranked)
                              if t in direct and t not in hosts), None)
            if lowest_ru is None:
                break
            direct.discard(lowest_ru)

        host_slots_used = len(direct.intersection(host_safety_set))
        playoff_pool = [t for t in all_teams if t not in direct]

        assert len(direct) <= 24, f"Direct qualifiers exceed 24: {len(direct)}"
        return direct, playoff_pool, host_slots_used

# -------------------------------------------------------------
# 7. FINAL TOURNAMENT POTS
# -------------------------------------------------------------
def rank_qualified_teams(winners, runners_up, playoff_qualifiers,
                         direct_qualifiers, group_stages, elo_ratings,
                         config, rng):
    hosts = set(config.hosts)
    winners_set = set(winners)
    runners_up_set = set(runners_up)

    def qualification_method(team: str) -> str:
        if team in winners_set:
            return "group_winner"
        if team in runners_up_set and team in direct_qualifiers:
            return "runner_up"
        if team in playoff_qualifiers:
            return "playoff_winner"
        if team in hosts and team in direct_qualifiers:
            return "host"
        return "unknown"

    def qualifying_stats(team: str) -> Dict:
        for gs in group_stages.values():
            if team in gs.standings:
                s = gs.standings[team]
                wins = sum(1 for m in s.matches
                           if (m.home == team and m.home_goals > m.away_goals)
                           or (m.away == team and m.away_goals > m.home_goals))
                away_wins = sum(1 for m in s.matches
                                if m.away == team
                                and m.away_goals > m.home_goals)
                away_gf = sum(m.away_goals for m in s.matches
                              if m.away == team)
                return {"points": s.points, "gd": s.gd, "gf": s.gf,
                        "away_gf": away_gf, "wins": wins,
                        "away_wins": away_wins}
        return {"points": 0, "gd": 0, "gf": 0, "away_gf": 0,
                "wins": 0, "away_wins": 0}

    all_qualified = list(direct_qualifiers) + list(playoff_qualifiers)

    def sort_key(team: str):
        qs = qualifying_stats(team)
        access = ACCESS_LIST_NATIONS.get(team, 9999)
        coeff = elo_ratings.get(team, config.initial_elo)
        discs = rng.randint(-10, 0)
        return (-qs["points"], -qs["gd"], -qs["gf"], -qs["away_gf"],
                -qs["wins"], -qs["away_wins"], discs, access, -coeff)

    ranked = sorted(all_qualified, key=sort_key)
    return [(team, qualification_method(team)) for team in ranked]

def build_final_pots(winners, runners_up, playoff_qualifiers,
                     direct_qualifiers, group_stages, elo_ratings,
                     config, rng):
    ranked = rank_qualified_teams(
        winners, runners_up, playoff_qualifiers, direct_qualifiers,
        group_stages, elo_ratings, config, rng)
    ranked_teams = [team for team, _ in ranked]
    hosts = set(config.hosts)

    hosts_outside = [t for t in ranked_teams[12:] if t in hosts]
    if hosts_outside:
        top12 = ranked_teams[:12]
        rest = ranked_teams[12:]
        non_host_top12_indices = [i for i, t in enumerate(top12)
                                  if t not in hosts]
        n_swap = len(hosts_outside)
        assert n_swap <= len(non_host_top12_indices), \
            "More hosts than available top-12 slots"
        swap_out_indices = non_host_top12_indices[-n_swap:]
        host_rest_positions = [i for i, t in enumerate(rest)
                               if t in hosts_outside]
        for i, top12_idx in enumerate(swap_out_indices):
            rest_idx = host_rest_positions[i]
            top12[top12_idx], rest[rest_idx] = rest[rest_idx], top12[top12_idx]
        ranked_teams = top12 + rest

    pots = {
        1: ranked_teams[0:6],
        2: ranked_teams[6:12],
        3: ranked_teams[12:18],
        4: ranked_teams[18:24],
    }
    for pot_num, lst in pots.items():
        assert len(lst) == 6, f"Pot {pot_num} has {len(lst)} teams: {lst}"
    return pots

# -------------------------------------------------------------
# 8. TOURNAMENT
# -------------------------------------------------------------
THIRD_PLACE_MATCHUPS = {
    frozenset(['A', 'B', 'C', 'D']): {'1B': '3A', '1C': '3D', '1E': '3B', '1F': '3C'},
    frozenset(['A', 'B', 'C', 'E']): {'1B': '3A', '1C': '3E', '1E': '3B', '1F': '3C'},
    frozenset(['A', 'B', 'C', 'F']): {'1B': '3A', '1C': '3F', '1E': '3B', '1F': '3C'},
    frozenset(['A', 'B', 'D', 'E']): {'1B': '3D', '1C': '3E', '1E': '3A', '1F': '3B'},
    frozenset(['A', 'B', 'D', 'F']): {'1B': '3D', '1C': '3F', '1E': '3A', '1F': '3B'},
    frozenset(['A', 'B', 'E', 'F']): {'1B': '3E', '1C': '3F', '1E': '3B', '1F': '3A'},
    frozenset(['A', 'C', 'D', 'E']): {'1B': '3E', '1C': '3D', '1E': '3C', '1F': '3A'},
    frozenset(['A', 'C', 'D', 'F']): {'1B': '3F', '1C': '3D', '1E': '3C', '1F': '3A'},
    frozenset(['A', 'C', 'E', 'F']): {'1B': '3E', '1C': '3F', '1E': '3C', '1F': '3A'},
    frozenset(['A', 'D', 'E', 'F']): {'1B': '3E', '1C': '3F', '1E': '3D', '1F': '3A'},
    frozenset(['B', 'C', 'D', 'E']): {'1B': '3E', '1C': '3D', '1E': '3B', '1F': '3C'},
    frozenset(['B', 'C', 'D', 'F']): {'1B': '3F', '1C': '3D', '1E': '3C', '1F': '3B'},
    frozenset(['B', 'C', 'E', 'F']): {'1B': '3F', '1C': '3E', '1E': '3C', '1F': '3B'},
    frozenset(['B', 'D', 'E', 'F']): {'1B': '3F', '1C': '3E', '1E': '3D', '1F': '3B'},
    frozenset(['C', 'D', 'E', 'F']): {'1B': '3F', '1C': '3E', '1E': '3D', '1F': '3C'},
}

class TournamentSimulation:
    def __init__(self, qualified_teams, elo_system, config, pots, rng):
        self.teams = qualified_teams
        self.elo = elo_system
        self.config = config
        self.hosts = config.hosts
        self.pots = pots
        self.rng = rng

    def draw_groups(self):
        groups = {f"Group {chr(65+i)}": [] for i in range(6)}
        host_groups = {"Wales": "Group A", "England": "Group B",
                       "Republic of Ireland": "Group E", "Scotland": "Group F"}
        placed_hosts = []
        for host, grp in host_groups.items():
            if host in self.teams:
                groups[grp].append(host)
                placed_hosts.append(host)

        group_pots: Dict[str, Set[int]] = {g: set() for g in groups}
        for host in placed_hosts:
            for gname, gteams in groups.items():
                if host in gteams:
                    host_pot = next((p for p, lst in self.pots.items()
                                     if host in lst), None)
                    if host_pot is None:
                        raise RuntimeError(f"Host {host} not in any pot.")
                    group_pots[gname].add(host_pot)

        for pot_num in sorted(self.pots.keys()):
            pot_teams = list(self.pots[pot_num])
            self.rng.shuffle(pot_teams)
            for team in pot_teams:
                if team in placed_hosts:
                    continue
                candidates = [g for g in groups
                              if pot_num not in group_pots[g]
                              and len(groups[g]) < 4]
                if not candidates:
                    raise RuntimeError(
                        f"Draw failed for Pot {pot_num}, team {team}")
                chosen = self.rng.choice(candidates)
                groups[chosen].append(team)
                group_pots[chosen].add(pot_num)

        for gname, gteams in groups.items():
            if len(gteams) != 4:
                raise RuntimeError(f"Group {gname} has {len(gteams)} teams.")
        return groups

    def _host_boosted_match(self, team_a, team_b):
        boost_a = self.config.home_boost(team_a) if team_a in self.hosts else 0
        boost_b = self.config.home_boost(team_b) if team_b in self.hosts else 0
        orig_a = self.elo.ratings.get(team_a, self.config.initial_elo)
        orig_b = self.elo.ratings.get(team_b, self.config.initial_elo)

        self.elo.ratings[team_a] = orig_a + boost_a
        self.elo.ratings[team_b] = orig_b + boost_b
        try:
            g_a, g_b = self.elo.simulate_goals(team_a, team_b, neutral=True)
        finally:
            self.elo.ratings[team_a] = orig_a
            self.elo.ratings[team_b] = orig_b
        return g_a, g_b, orig_a, orig_b

    def simulate_group_match(self, team_a, team_b):
        g_a, g_b, _, _ = self._host_boosted_match(team_a, team_b)
        self.elo.update(team_a, team_b, g_a, g_b)
        return g_a, g_b

    def simulate_tournament_match(self, team_a, team_b):
        g_a, g_b, orig_a, orig_b = self._host_boosted_match(team_a, team_b)
        if g_a != g_b:
            winner = team_a if g_a > g_b else team_b
            self.elo.update(team_a, team_b, g_a, g_b)
            return winner, g_a, g_b

        boost_a = self.config.home_boost(team_a) if team_a in self.hosts else 0
        boost_b = self.config.home_boost(team_b) if team_b in self.hosts else 0
        self.elo.ratings[team_a] = orig_a + boost_a
        self.elo.ratings[team_b] = orig_b + boost_b
        try:
            et_a, et_b = self.elo.simulate_goals(
                team_a, team_b, scale_factor=0.33, neutral=True)
        finally:
            self.elo.ratings[team_a] = orig_a
            self.elo.ratings[team_b] = orig_b

        g_a += et_a; g_b += et_b
        if g_a != g_b:
            winner = team_a if g_a > g_b else team_b
            self.elo.update(team_a, team_b, g_a, g_b)
            return winner, g_a, g_b

        diff = orig_a - orig_b
        prob_a = 1 / (1 + math.exp(-diff / 150))
        winner = team_a if self.rng.random() < prob_a else team_b
        return winner, g_a, g_b

    def simulate_group_stage(self, groups):
        standings = {}
        third_placed = []
        advancers = []
        for grp_name, teams in groups.items():
            matches = [(teams[0], teams[1]), (teams[2], teams[3]),
                       (teams[0], teams[2]), (teams[1], teams[3]),
                       (teams[0], teams[3]), (teams[1], teams[2])]
            group_standings = {t: {"pts": 0, "gf": 0, "ga": 0, "wins": 0}
                               for t in teams}
            group_matches = []
            for home, away in matches:
                g_h, g_a = self.simulate_group_match(home, away)
                group_matches.append((home, away, g_h, g_a))
                group_standings[home]["gf"] += g_h
                group_standings[home]["ga"] += g_a
                group_standings[away]["gf"] += g_a
                group_standings[away]["ga"] += g_h
                if g_h > g_a:
                    group_standings[home]["pts"] += 3
                    group_standings[home]["wins"] += 1
                elif g_a > g_h:
                    group_standings[away]["pts"] += 3
                    group_standings[away]["wins"] += 1
                else:
                    group_standings[home]["pts"] += 1
                    group_standings[away]["pts"] += 1

            def h2h_stats(team, tied_set):
                pts = gd = gf = 0
                for home, away, gh, ga in group_matches:
                    if home in tied_set and away in tied_set:
                        if home == team:
                            gf += gh; gd += gh - ga
                            pts += 3 if gh > ga else (1 if gh == ga else 0)
                        elif away == team:
                            gf += ga; gd += ga - gh
                            pts += 3 if ga > gh else (1 if ga == gh else 0)
                return pts, gd, gf

            def sort_key(t):
                s = group_standings[t]
                tied = [x for x in teams
                        if group_standings[x]["pts"] == s["pts"]]
                if len(tied) > 1:
                    hp, hgd, hgf = h2h_stats(t, set(tied))
                else:
                    hp, hgd, hgf = 0, 0, 0
                elo = self.elo.ratings.get(t, 1500)
                return (-s["pts"], -hp, -hgd, -hgf,
                        -(s["gf"] - s["ga"]), -s["gf"], -elo)

            sorted_teams = sorted(teams, key=sort_key)
            standings[grp_name] = sorted_teams
            advancers.append(sorted_teams[0])
            advancers.append(sorted_teams[1])
            third_placed.append(
                (grp_name, sorted_teams[2], group_standings[sorted_teams[2]]))

        third_placed.sort(key=lambda x: (-x[2]["pts"],
                                         -(x[2]["gf"] - x[2]["ga"]),
                                         -x[2]["gf"], -x[2]["wins"],
                                         -self.elo.ratings.get(x[1], 1500)))
        for i in range(4):
            advancers.append(third_placed[i][1])
        return standings, advancers, third_placed[:4]

    def resolve_r16(self, standings, third_placed_teams):
        third_grps = frozenset(t[0].replace("Group ", "")
                               for t in third_placed_teams)
        matchups = THIRD_PLACE_MATCHUPS.get(third_grps)
        if not matchups:
            raise ValueError(
                f"Unknown third placed combination: {third_grps}")

        def get_team(grp, pos):
            if pos == 2:
                for t in third_placed_teams:
                    if t[0] == grp:
                        return t[1]
            return standings[grp][pos]

        return [
            (get_team("Group A", 0), get_team("Group C", 1)),
            (get_team("Group A", 1), get_team("Group B", 1)),
            (get_team("Group B", 0),
             get_team(matchups['1B'].replace("3", "Group "), 2)),
            (get_team("Group C", 0),
             get_team(matchups['1C'].replace("3", "Group "), 2)),
            (get_team("Group F", 0),
             get_team(matchups['1F'].replace("3", "Group "), 2)),
            (get_team("Group D", 1), get_team("Group E", 1)),
            (get_team("Group D", 0), get_team("Group F", 1)),
            (get_team("Group E", 0),
             get_team(matchups['1E'].replace("3", "Group "), 2)),
        ]

    def simulate_knockout(self, r16_matches):
        england_opponents: Dict[str, str] = {}

        def play(t1, t2, stage):
            winner, _, _ = self.simulate_tournament_match(t1, t2)
            if t1 == "England":
                england_opponents[stage] = t2
            elif t2 == "England":
                england_opponents[stage] = t1
            return winner

        w37 = play(r16_matches[0][0], r16_matches[0][1], "r16")
        w38 = play(r16_matches[1][0], r16_matches[1][1], "r16")
        w39 = play(r16_matches[2][0], r16_matches[2][1], "r16")
        w40 = play(r16_matches[3][0], r16_matches[3][1], "r16")
        w41 = play(r16_matches[4][0], r16_matches[4][1], "r16")
        w42 = play(r16_matches[5][0], r16_matches[5][1], "r16")
        w43 = play(r16_matches[6][0], r16_matches[6][1], "r16")
        w44 = play(r16_matches[7][0], r16_matches[7][1], "r16")

        w45 = play(w39, w37, "qf")
        w46 = play(w41, w42, "qf")
        w47 = play(w44, w43, "qf")
        w48 = play(w40, w38, "qf")

        w49 = play(w45, w46, "sf")
        w50 = play(w47, w48, "sf")

        final_w = play(w49, w50, "final")

        return {"r16": [w37, w38, w39, w40, w41, w42, w43, w44],
                "qf": [w45, w46, w47, w48],
                "sf": [w49, w50],
                "final": [w49, w50],
                "winner": final_w,
                "england_opponents": england_opponents}

    def run(self):
        groups = self.draw_groups()
        standings, advancers, third_placed = self.simulate_group_stage(groups)
        r16_matches = self.resolve_r16(standings, third_placed)
        ko = self.simulate_knockout(r16_matches)

        group_finishes = {}
        for grp_name, sorted_teams in standings.items():
            for pos, team in enumerate(sorted_teams):
                group_finishes[team] = pos + 1

        eng_opps = ko.get("england_opponents", {})
        eng_group = next((g.replace("Group ", "")
                          for g, ts in groups.items() if "England" in ts), None)
        eng_mates = next(([t for t in ts if t != "England"]
                          for ts in groups.values() if "England" in ts), None)

        return {"r16": set(advancers), "qf": set(ko["qf"]),
                "sf": set(ko["sf"]), "final": set(ko["final"]),
                "winner": ko["winner"],
                "group_finishes": group_finishes, "groups": groups,
                "england_group": eng_group,
                "england_groupmates": eng_mates,
                "england_r16_opp": eng_opps.get("r16"),
                "england_qf_opp": eng_opps.get("qf"),
                "england_sf_opp": eng_opps.get("sf"),
                "england_final_opp": eng_opps.get("final")}

# -------------------------------------------------------------
# 9. NATIONS LEAGUE IMPORT  (with robust path handling)
# -------------------------------------------------------------
_current_dir = os.path.dirname(os.path.abspath(__file__))
_parent_dir = os.path.dirname(_current_dir)
if _parent_dir not in sys.path:
    sys.path.insert(0, _parent_dir)

try:
    from nationsleague.main import (
        ALL_TEAMS as _NL_ALL_TEAMS,
        ELO_RATINGS as _NL_ELO_RATINGS,
        ACCESS_LIST as _NL_ACCESS_LIST,
        DISCIPLINE_POINTS as _NL_DISCIPLINE_POINTS,
        simulate_nl_season_state as _simulate_nl_season_state,
        NLSeasonState,   # for type hints / future use
    )
except ImportError as e:
    raise ImportError(
        f"Could not import from nationsleague.main. "
        f"Ensure main.py is in the 'nationsleague' folder. Error: {e}")

_LEGACY_NAMES = {"Czechia": "Czech Republic", "Türkiye": "Turkey"}

# Filter out Russia – not eligible for EURO 2028 qualifying.
all_teams = [_LEGACY_NAMES.get(t, t) for t in _NL_ALL_TEAMS if t != "Russia"]

ACCESS_LIST_NATIONS: Dict[str, int] = {}
for _t, _idx in _NL_ACCESS_LIST.items():
    if _t == "Russia":
        continue
    ACCESS_LIST_NATIONS[_LEGACY_NAMES.get(_t, _t)] = _idx

ELO_RATINGS = dict(_NL_ELO_RATINGS)
for canonical, legacy in _LEGACY_NAMES.items():
    ELO_RATINGS[legacy] = ELO_RATINGS[canonical]
for team in all_teams:
    ELO_RATINGS.setdefault(team, 1500)
if "Russia" in ELO_RATINGS:
    del ELO_RATINGS["Russia"]

DISCIPLINE_POINTS_EURO: Dict[str, int] = {}
for t, pts in _NL_DISCIPLINE_POINTS.items():
    if t == "Russia":
        continue
    DISCIPLINE_POINTS_EURO[_LEGACY_NAMES.get(t, t)] = pts

# -------------------------------------------------------------
# 10. POT HELPERS
# -------------------------------------------------------------
def nl_pots_from_ranking(ranking_nl: List[str]) -> Dict[str, int]:
    pot_sizes = [12, 12, 12, 12, 6]  # 54 teams, UEFA-style
    pot_by_team: Dict[str, int] = {}
    idx = 0
    for pot, size in enumerate(pot_sizes, 1):
        for _ in range(size):
            if idx >= len(ranking_nl):
                break
            euro_name = _LEGACY_NAMES.get(ranking_nl[idx], ranking_nl[idx])
            pot_by_team[euro_name] = pot
            idx += 1
    assert len(pot_by_team) == len(ranking_nl), \
        "Pot mapping is missing teams."
    return pot_by_team

def build_groups(hosts, config, pot_by_team, nl_qf_teams, rng):
    """
    Draw qualifying groups using a 5-pot structure and enforce that UNL QF
    teams are placed in 4-team groups only.
    """
    groups: List[List[str]] = [[] for _ in range(config.num_groups)]
    qf_set = set(nl_qf_teams)

    # 1. Place hosts, one per group (first 4 groups).
    shuffled_hosts = list(hosts)
    rng.shuffle(shuffled_hosts)
    for i, host in enumerate(shuffled_hosts):
        groups[i].append(host)

    # 2. Determine which groups are 4-team.
    host_qf_indices = [i for i, h in enumerate(shuffled_hosts) if h in qf_set]
    mandatory_four = set(host_qf_indices)

    if len(mandatory_four) > 6:
        raise RuntimeError("Too many QF-team hosts to fit into 6 four-team groups.")

    optional = [i for i in range(config.num_groups) if i not in mandatory_four]
    additional = rng.sample(optional, 6 - len(mandatory_four))
    four_team_indices = mandatory_four | set(additional)

    sizes = [4 if i in four_team_indices else 5
             for i in range(config.num_groups)]

    group_pots: List[Set[int]] = [set() for _ in range(config.num_groups)]
    for i, host in enumerate(shuffled_hosts):
        p = pot_by_team.get(host, 1)
        group_pots[i].add(p)

    # 3. Place non-host QF teams into 4-team groups only.
    non_host_qf = [t for t in qf_set if t in all_teams and t not in hosts]
    non_host_qf_set = set(non_host_qf)

    # Sort by pot to distribute high-pot QFs first.
    non_host_qf.sort(key=lambda t: pot_by_team.get(t, 3))

    for qf in non_host_qf:
        qf_pot = pot_by_team.get(qf, 3)
        candidates = [i for i in four_team_indices
                      if len(groups[i]) < sizes[i]
                      and qf_pot not in group_pots[i]]
        if not candidates:
            candidates = [i for i in four_team_indices
                          if len(groups[i]) < sizes[i]]
        if not candidates:
            # Fallback: relax pot constraint completely for 4-team groups.
            candidates = [i for i in range(config.num_groups)
                          if len(groups[i]) < sizes[i]]
        if not candidates:
            raise RuntimeError(f"No slot available for QF team {qf}.")

        if qf_pot != 1:
            clean_candidates = [i for i in candidates
                                if 1 not in group_pots[i]]
            if clean_candidates:
                candidates = clean_candidates

        chosen = min(candidates, key=lambda i: (len(groups[i]), rng.random()))
        groups[chosen].append(qf)
        group_pots[chosen].add(qf_pot)

    # 4. Place remaining teams by pot.
    teams_by_pot: Dict[int, List[str]] = {p: [] for p in range(1, 6)}
    for team in all_teams:
        if team in hosts or team in non_host_qf_set:
            continue
        teams_by_pot[pot_by_team.get(team, 3)].append(team)

    for p in teams_by_pot:
        rng.shuffle(teams_by_pot[p])

    for pot in range(1, 6):
        for team in teams_by_pot[pot]:
            candidates = [i for i in range(config.num_groups)
                          if len(groups[i]) < sizes[i]
                          and pot not in group_pots[i]]
            if not candidates:
                # Emergency fallback: ignore pot uniqueness.
                candidates = [i for i in range(config.num_groups)
                              if len(groups[i]) < sizes[i]]
            if not candidates:
                raise RuntimeError(
                    f"Draw failed completely for Pot {pot}, team {team}.")
            chosen = rng.choice(candidates)
            groups[chosen].append(team)
            group_pots[chosen].add(pot)

    for i, g in enumerate(groups):
        assert len(g) == sizes[i], \
            f"Group {i} has {len(g)} teams, expected {sizes[i]}."
    return groups, sizes

# -------------------------------------------------------------
# 11. SINGLE SIMULATION
# -------------------------------------------------------------
def run_single_simulation(seed: int):
    rng = random.Random(seed)
    config = CONFIG
    elo = EloSystem(ELO_RATINGS, config, rng)

    # --- 1. Nations League season ---
    nl_rng = random.Random(rng.randrange(2 ** 32))
    nl_state = _simulate_nl_season_state(nl_rng)
    nl_ranking_nl = nl_state.ranking
    qf_teams_nl = nl_state.qf_teams
    pot_by_team = nl_pots_from_ranking(nl_ranking_nl)
    nl_qf_teams = [_LEGACY_NAMES.get(t, t) for t in qf_teams_nl]
    qf_set = set(nl_qf_teams)
    assert len(nl_qf_teams) == 8, \
        f"Expected 8 QF teams, got {len(nl_qf_teams)}"

    # --- 2. UNL QF (March) ---
    shuffled_qf = list(nl_qf_teams)
    rng.shuffle(shuffled_qf)
    for i in range(0, 8, 2):
        KnockoutMatch.home_away(elo, shuffled_qf[i], shuffled_qf[i + 1])

    # --- 3. Euro qualifying draw + group stage ---
    groups, sizes = build_groups(config.hosts, config, pot_by_team,
                                 nl_qf_teams=nl_qf_teams, rng=rng)
    winners, runners_up, group_stages = [], [], {}
    for i, group in enumerate(groups):
        group_name = chr(65 + i)
        has_qf = any(t in qf_set for t in group)
        matchday_offset = 2 if (sizes[i] == 4 and has_qf) else 0
        gs = GroupStage(group, elo, config, rng=rng,
                        matchday_offset=matchday_offset)
        gs.simulate()
        sorted_t = gs.get_sorted_teams()
        winners.append(sorted_t[0])
        runners_up.append(sorted_t[1])
        group_stages[group_name] = gs

    # --- 4. Host resolution ---
    direct_qualifiers, playoff_pool, host_slots_used = HostManager.resolve(
        winners, runners_up, group_stages, config, rng, all_teams)
    assert len(direct_qualifiers) <= 24, \
        f"Direct: {len(direct_qualifiers)} exceeds 24"

    expected_playoffs = 24 - len(direct_qualifiers)
    playoff_qualifiers: Set[str] = set()

    if expected_playoffs > 0:
        # ----- 4a. Rank the play-off candidate pools -----

        # (1) Remaining runners-up (not directly qualified), ranked by Elo.
        remaining_runners_up_ranked = sorted(
            [t for t in runners_up if t not in direct_qualifiers],
            key=lambda t: -elo.ratings.get(t, 1500),
        )

        # (2) Non-qualified UNL group winners, ranked by interim UNL position.
        _nl_to_euro_position = {
            _LEGACY_NAMES.get(t, t): i
            for i, t in enumerate(nl_ranking_nl)
        }
        nl_group_winners_euro = [
            _LEGACY_NAMES.get(t, t)
            for t in nl_state.group_winners
            if _LEGACY_NAMES.get(t, t) not in direct_qualifiers
        ]
        nl_group_winners_ranked = sorted(
            nl_group_winners_euro,
            key=lambda t: _nl_to_euro_position.get(t, 9999),
        )

        # (3) Fallback: any non-qualified team ranked by UNL position.
        # Only used if (1) + (2) cannot fill the required pool size.
        _all_euro_ranked = [
            _LEGACY_NAMES.get(t, t) for t in nl_ranking_nl
        ]
        _in_pool = set(remaining_runners_up_ranked) | set(nl_group_winners_ranked)
        fallback_pool = [
            t for t in _all_euro_ranked
            if t not in direct_qualifiers and t not in _in_pool
        ]

        # ----- 4b. Scenario-dependent sizing -----
        if host_slots_used == 2:
            total_playoff_teams, num_paths = 8, 2
        elif host_slots_used == 1:
            total_playoff_teams, num_paths = 12, 3
        else:  # host_slots_used == 0
            total_playoff_teams, num_paths = 8, 4

        # ----- 4c. Build the pool: runners-up → UNL group winners → padding -----
        playoff_teams = remaining_runners_up_ranked[:4]

        for t in nl_group_winners_ranked:
            if len(playoff_teams) >= total_playoff_teams:
                break
            if t not in playoff_teams:
                playoff_teams.append(t)

        for t in fallback_pool:
            if len(playoff_teams) >= total_playoff_teams:
                break
            if t not in playoff_teams:
                playoff_teams.append(t)

        assert len(playoff_teams) == total_playoff_teams, (
            f"Play-off pool mismatch: got {len(playoff_teams)}, "
            f"expected {total_playoff_teams} "
            f"(host_slots={host_slots_used}, "
            f"RU={len(remaining_runners_up_ranked)}, "
            f"NLgw={len(nl_group_winners_ranked)}, "
            f"fallback={len(fallback_pool)})"
        )

        # ----- 4d. Seed deterministically by interim UNL ranking -----
        def playoff_seed_key(t):
            return _nl_to_euro_position.get(t, 9999)

        playoff_teams.sort(key=playoff_seed_key)

        # ----- 4e. Simulate the play-offs -----
        if host_slots_used == 0:
            # Four two-legged ties (4 spots).
            for i in range(0, len(playoff_teams), 2):
                playoff_qualifiers.add(
                    KnockoutMatch.home_away(
                        elo, playoff_teams[i], playoff_teams[i + 1]))
        else:
            # Single-leg semi-finals + final, one winner per path.
            for path in range(num_paths):
                path_teams = playoff_teams[path * 4:(path + 1) * 4]
                if len(path_teams) == 4:
                    w1 = KnockoutMatch.single_leg(
                        elo, path_teams[0], path_teams[3])
                    w2 = KnockoutMatch.single_leg(
                        elo, path_teams[1], path_teams[2])
                    winner = KnockoutMatch.single_leg(elo, w1, w2)
                    playoff_qualifiers.add(winner)

    assert len(playoff_qualifiers) == expected_playoffs, \
        f"Playoffs: {len(playoff_qualifiers)}, expected {expected_playoffs}"
    assert len(direct_qualifiers & playoff_qualifiers) == 0, \
        "Overlap between direct and playoff."
    assert len(direct_qualifiers) + len(playoff_qualifiers) == 24, \
        "Total qualifiers != 24."

    # --- 5. Build final-tournament pots ---
    pots = build_final_pots(
        winners, runners_up, playoff_qualifiers, direct_qualifiers,
        group_stages, ELO_RATINGS, config, rng)

    direct_counter = {t: 1 for t in direct_qualifiers}
    playoff_counter = {t: 1 for t in playoff_qualifiers}
    all_hosts = list(config.hosts)
    all_qualified = 1 if all(
        t in direct_qualifiers or t in playoff_qualifiers
        for t in all_hosts) else 0

    qualified_teams = list(direct_qualifiers) + list(playoff_qualifiers)
    t_stats = {s: defaultdict(int)
               for s in ("winner", "final", "semi", "qf", "r16")}
    g_stats = {s: defaultdict(int)
               for s in ("win_group", "second", "third_advance")}

    base_ratings = elo.ratings.copy()
    england_groups, england_groupmates_list = [], []
    england_r16_opps, england_qf_opps = [], []
    england_sf_opps, england_final_opps = [], []
    group_draw_counts: Dict[str, Dict[str, int]] = defaultdict(
        lambda: defaultdict(int))

    for tourn_idx in range(10):
        tournament_rng = random.Random(seed + 1000 + tourn_idx)
        tournament_elo = EloSystem(base_ratings, config, tournament_rng)
        tourn_sim = TournamentSimulation(
            qualified_teams, tournament_elo, config,
            pots=pots, rng=tournament_rng)
        results = tourn_sim.run()

        england_groups.append(results.get("england_group"))
        england_groupmates_list.append(results.get("england_groupmates"))
        england_r16_opps.append(results.get("england_r16_opp"))
        england_qf_opps.append(results.get("england_qf_opp"))
        england_sf_opps.append(results.get("england_sf_opp"))
        england_final_opps.append(results.get("england_final_opp"))

        for gname, gteams in results.get("groups", {}).items():
            glabel = gname.replace("Group ", "")
            for t in gteams:
                group_draw_counts[glabel][t] += 1

        for stage in ("r16", "qf", "sf", "final"):
            for t in results[stage]:
                t_stats[stage][t] += 1
        t_stats["winner"][results["winner"]] += 1

        for team, pos in results["group_finishes"].items():
            if pos == 1:
                g_stats["win_group"][team] += 1
            elif pos == 2:
                g_stats["second"][team] += 1
            elif pos == 3:
                g_stats["third_advance"][team] += 1

    group_draw_counts_plain = {g: dict(teams)
                               for g, teams in group_draw_counts.items()}
    return (direct_counter, playoff_counter, all_qualified,
            t_stats, g_stats, host_slots_used,
            england_groups, england_r16_opps, england_qf_opps,
            england_sf_opps, england_final_opps, england_groupmates_list,
            group_draw_counts_plain, pots)

def worker_task(seed: int):
    return run_single_simulation(seed)

# -------------------------------------------------------------
# 12. MAIN
# -------------------------------------------------------------
if __name__ == "__main__":
    print("Starting UEFA EURO 2028 Qualifying & Tournament Simulation...")
    start_time = time.time()
    num_cores = cpu_count()

    parser = argparse.ArgumentParser(
        description="UEFA EURO 2028 Simulation")
    parser.add_argument("--seed", type=int, default=None,
                        help="Base seed for reproducibility "
                             "(random if omitted)")
    args = parser.parse_args()
    base_seed = args.seed if args.seed is not None \
        else random.randint(0, 2 ** 31 - 1)
    print(f"Run seed: {base_seed}")

    standard_direct_counter = defaultdict(int)
    playoff_counter = defaultdict(int)
    total_host_qualifications = 0
    total_host_slots = 0
    host_slots_counter = defaultdict(int)
    england_group_counter = defaultdict(int)
    england_groupmate_combos = defaultdict(int)
    england_r16_counter = defaultdict(int)
    england_qf_counter = defaultdict(int)
    england_sf_counter = defaultdict(int)
    england_final_counter = defaultdict(int)
    group_draw_counter: Dict[str, Dict[str, int]] = {}
    pot_membership_counter: Dict[str, Dict[int, int]] = defaultdict(
        lambda: defaultdict(int))
    tournament_stats = {s: defaultdict(int)
                        for s in ("winner", "final", "semi", "qf", "r16")}
    group_stats = {s: defaultdict(int)
                   for s in ("win_group", "second", "third_advance")}

    with Pool(num_cores) as pool:
        for i, result in enumerate(
                pool.imap_unordered(
                    worker_task,
                    range(base_seed,
                          base_seed + CONFIG.num_simulations))):
            (d_c, p_c, af, t_stats, g_stats, host_slots_used,
             eng_groups, eng_r16s, eng_qfs, eng_sfs, eng_finals,
             eng_mates, gd_counts, pots) = result

            for t, v in d_c.items():
                standard_direct_counter[t] += v
            for t, v in p_c.items():
                playoff_counter[t] += v
            total_host_qualifications += af
            total_host_slots += host_slots_used
            host_slots_counter[host_slots_used] += 1

            for g in eng_groups:
                if g is not None:
                    england_group_counter[g] += 1
            for mates in eng_mates:
                if mates:
                    england_groupmate_combos[frozenset(mates)] += 1
            for o in eng_r16s:
                if o is not None:
                    england_r16_counter[o] += 1
            for o in eng_qfs:
                if o is not None:
                    england_qf_counter[o] += 1
            for o in eng_sfs:
                if o is not None:
                    england_sf_counter[o] += 1
            for o in eng_finals:
                if o is not None:
                    england_final_counter[o] += 1

            for glabel, team_counts in gd_counts.items():
                group_draw_counter.setdefault(glabel, {})
                for t, c in team_counts.items():
                    group_draw_counter[glabel][t] = \
                        group_draw_counter[glabel].get(t, 0) + c

            for pot_num, teams in pots.items():
                for team in teams:
                    pot_membership_counter[team][pot_num] += 1

            for stage, counts in t_stats.items():
                for t, v in counts.items():
                    tournament_stats[stage][t] += v
            for finish, counts in g_stats.items():
                for t, v in counts.items():
                    group_stats[finish][t] += v

            done = i + 1
            pct = done / CONFIG.num_simulations
            bar = '=' * int(40 * pct) + '-' * (40 - int(40 * pct))
            elapsed = time.time() - start_time
            eta = elapsed / pct - elapsed if pct > 0 else 0
            sys.stdout.write(
                f'\rProgress: |{bar}| {pct*100:.2f}% '
                f'({done}/{CONFIG.num_simulations})  '
                f'Elapsed: {time.strftime("%H:%M:%S", time.gmtime(elapsed))}  '
                f'ETA: {time.strftime("%H:%M:%S", time.gmtime(eta))}')
            sys.stdout.flush()

    print(f"\nSimulation completed in {time.time() - start_time:.2f}s.\n")
    print("UEFA EURO 2028 QUALIFYING SIMULATION RESULTS")
    print(f"Total qualifying simulations: {CONFIG.num_simulations}\n")
    print("EURO 2028 TOTAL QUALIFICATION PROBABILITIES:\n")

    total_qual = {team: standard_direct_counter[team]
                  + playoff_counter[team] for team in all_teams}
    for team in sorted(all_teams, key=lambda t: total_qual[t],
                       reverse=True):
        if total_qual[team] > 0:
            pct = 100 * total_qual[team] / CONFIG.num_simulations
            dp = 100 * standard_direct_counter[team] / CONFIG.num_simulations
            pp = 100 * playoff_counter[team] / CONFIG.num_simulations
            label = " (Host)" if team in CONFIG.hosts else ""
            print(f"{team:22}: {pct:6.2f}% "
                  f"(Direct: {dp:6.2f}%, Playoffs: {pp:6.2f}%){label}")

    all_hosts_pct = 100 * total_host_qualifications / CONFIG.num_simulations
    print(f"\nProbability all four hosts qualify: {all_hosts_pct:.2f}%")
    avg_host_slots = total_host_slots / CONFIG.num_simulations
    slots_breakdown = ", ".join(
        f"{k}: {100*host_slots_counter[k]/CONFIG.num_simulations:.1f}%"
        for k in sorted(host_slots_counter))
    print(f"Avg host safety slots used: {avg_host_slots:.3f} "
          f"({slots_breakdown})")