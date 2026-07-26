import random
import math
import numpy as np
from collections import defaultdict
from dataclasses import dataclass, field
from typing import List, Dict, Tuple, Set
from multiprocessing import Pool, cpu_count
import time
import sys

# -------------------------------------------------------------
# 1. CONFIGURATION SYSTEM
# -------------------------------------------------------------
@dataclass
class Config:
    num_groups: int = 12
    num_winners: int = 12         # Group winners qualify directly
    num_best_runners_up: int = 8  # Best runners-up qualify directly
    host_safety_slots: int = 2    # Two reserved spots for the two best-ranked hosts that fail to qualify normally
    hosts: List[str] = field(default_factory=lambda: [
        "England", "Republic of Ireland", "Scotland", "Wales"
    ])
    num_simulations: int = 10000
    home_advantage_elo: int = 100
    host_home_advantage: Dict[str, int] = field(default_factory=lambda: {
        "Wales": 40,
        "England": 35,
        "Scotland": 40,
        "Republic of Ireland": 40,
        "Northern Ireland": 15,
    })
    k_factor: int = 20
    base_goals: float = 1.35
    goal_correlation: float = 0.18   # Shared-shock weight for bivariate Poisson (low-score correlation)
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
    def __init__(self, initial_ratings: Dict[str, int], config: Config):
        self.ratings = initial_ratings.copy()
        self.config = config

    def get_rating(self, team: str, is_home: bool = False) -> float:
        base = self.ratings.get(team, self.config.initial_elo)
        return base + (self.config.home_advantage_elo if is_home else 0)

    def update(self, team_a: str, team_b: str, goals_a: int, goals_b: int):
        elo_a = self.ratings.get(team_a, self.config.initial_elo)
        elo_b = self.ratings.get(team_b, self.config.initial_elo)
        
        if goals_a > goals_b: res_a, res_b = 1.0, 0.0
        elif goals_a < goals_b: res_a, res_b = 0.0, 1.0
        else: res_a, res_b = 0.5, 0.5
        
        exp_a = 1 / (1 + 10 ** ((elo_b - elo_a) / 400))
        exp_b = 1 - exp_a
        
        gd_mult = max(1, (abs(goals_a - goals_b) + 1) ** 0.5)
        
        new_a = elo_a + self.config.k_factor * gd_mult * (res_a - exp_a)
        new_b = elo_b + self.config.k_factor * gd_mult * (res_b - exp_b)
        
        self.ratings[team_a] = max(self.config.elo_min, min(self.config.elo_max, new_a))
        self.ratings[team_b] = max(self.config.elo_min, min(self.config.elo_max, new_b))

    def simulate_goals(self, team_a: str, team_b: str, scale_factor: float = 1.0) -> Tuple[int, int]:
        elo_a = self.get_rating(team_a, is_home=True)
        elo_b = self.get_rating(team_b, is_home=False)

        rating_diff = elo_a - elo_b

        lam_a = self.config.base_goals * (10 ** (rating_diff / 1000)) * scale_factor
        lam_b = self.config.base_goals * (10 ** (-rating_diff / 1000)) * scale_factor

        lam_a = max(0.2, lam_a)
        lam_b = max(0.2, lam_b)

        # Bivariate Poisson: a shared "shock" component induces positive
        # correlation between home and away goals, which realistically
        # increases low-scoring results (0-0, 1-0, 1-1, 2-1) and draws.
        shared = self.config.goal_correlation * min(lam_a, lam_b)
        shared = max(0.0, shared)

        shock = np.random.poisson(shared)
        g_a = np.random.poisson(lam_a - shared) + shock
        g_b = np.random.poisson(lam_b - shared) + shock

        return int(g_a), int(g_b)

# -------------------------------------------------------------
# 4. GROUP STAGE & TIEBREAKERS
# -------------------------------------------------------------
def generate_fixtures(teams: List[str]) -> List[List[Tuple[str, str]]]:
    """
    Generates a double round-robin fixture list.
    For 5 teams: 10 matchdays (2 matches per day, 1 bye).
    For 4 teams: 6 matchdays (2 matches per day).
    """
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
        # Rotate teams: keep the first team fixed, rotate the rest
        teams = [teams[0]] + [teams[-1]] + teams[1:-1]
        
    second_half = []
    for round_fixtures in first_half:
        second_half.append([(away, home) for home, away in round_fixtures])
        
    return first_half + second_half

class GroupStage:
    def __init__(self, teams: List[str], elo_system: EloSystem, config: Config):
        self.teams = teams
        self.elo = elo_system
        self.config = config
        self.standings = {t: TeamStanding(team=t) for t in teams}
        self.matches: List[MatchResult] = []

    def simulate(self):
        fixtures_by_matchday = generate_fixtures(self.teams)
        
        for matchday_fixtures in fixtures_by_matchday:
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
                if match.home_goals > match.away_goals: pts_h += 3
                elif match.home_goals == match.away_goals: pts_h += 1
                gd_h += match.home_goals - match.away_goals
                gf_h += match.home_goals
                h2h[match.home] = (pts_h, gd_h, gf_h)
                
                pts_a, gd_a, gf_a = h2h[match.away]
                if match.away_goals > match.home_goals: pts_a += 3
                elif match.away_goals == match.home_goals: pts_a += 1
                gd_a += match.away_goals - match.home_goals
                gf_a += match.away_goals
                h2h[match.away] = (pts_a, gd_a, gf_a)
        
        return h2h

    def get_sorted_teams(self) -> List[str]:
        def tiebreaker_key(team_name: str):
            s = self.standings[team_name]
            tied_teams = [t for t in self.teams if self.standings[t].points == s.points]
            
            if len(tied_teams) > 1:
                h2h = self._get_head_to_head(tied_teams)
                h2h_pts, h2h_gd, h2h_gf = h2h[team_name]
            else:
                h2h_pts, h2h_gd, h2h_gf = 0, 0, 0
            
            wins = sum(1 for m in s.matches if (m.home == team_name and m.home_goals > m.away_goals) or 
                                             (m.away == team_name and m.away_goals > m.home_goals))
            away_wins = sum(1 for m in s.matches if m.away == team_name and m.away_goals > m.home_goals)
            away_gf = sum(m.away_goals for m in s.matches if m.away == team_name)
            
            discs = random.randint(-10, 0)
            coeff = self.elo.ratings.get(team_name, self.config.initial_elo)
            
            return (
                -s.points, -h2h_pts, -h2h_gd, -h2h_gf,
                -s.gd, -s.gf, -away_gf, -wins, -away_wins, discs, -coeff
            )
            
        return sorted(self.teams, key=tiebreaker_key)

# -------------------------------------------------------------
# 5. KNOCKOUT & PLAYOFF SYSTEM
# -------------------------------------------------------------
class KnockoutMatch:
    @staticmethod
    def single_leg(elo: EloSystem, team_a: str, team_b: str) -> str:
        g_a, g_b = elo.simulate_goals(team_a, team_b)
        if g_a != g_b: return team_a if g_a > g_b else team_b
        
        et_a, et_b = elo.simulate_goals(team_a, team_b, scale_factor=0.33)
        g_a += et_a; g_b += et_b
        if g_a != g_b: return team_a if g_a > g_b else team_b
            
        return KnockoutMatch.penalties(elo, team_a, team_b)

    @staticmethod
    def home_away(elo: EloSystem, team_a: str, team_b: str) -> str:
        g_a1, g_b1 = elo.simulate_goals(team_a, team_b)
        g_b2, g_a2 = elo.simulate_goals(team_b, team_a)
        
        agg_a = g_a1 + g_a2
        agg_b = g_b1 + g_b2
        
        if agg_a != agg_b: return team_a if agg_a > agg_b else team_b
            
        et_b, et_a = elo.simulate_goals(team_b, team_a, scale_factor=0.33)
        agg_a += et_a; agg_b += et_b
        if agg_a != agg_b: return team_a if agg_a > agg_b else team_b
            
        return KnockoutMatch.penalties(elo, team_a, team_b)

    @staticmethod
    def penalties(elo: EloSystem, team_a: str, team_b: str) -> str:
        diff = elo.ratings.get(team_a, 1500) - elo.ratings.get(team_b, 1500)
        prob_a = 1 / (1 + math.exp(-diff / 150))
        return team_a if random.random() < prob_a else team_b

class PlayoffPath:
    @staticmethod
    def simulate_bracket(elo: EloSystem, teams: List[str]) -> str:
        w1 = KnockoutMatch.single_leg(elo, teams[0], teams[1])
        w2 = KnockoutMatch.single_leg(elo, teams[2], teams[3])
        return KnockoutMatch.single_leg(elo, w1, w2)

# -------------------------------------------------------------
# 6. HOST QUALIFICATION & OVERALL RANKING
# -------------------------------------------------------------
class HostManager:
    @staticmethod
    def _overall_ranking_key(team: str, gs: GroupStage, config: Config) -> Tuple:
        """Official UEFA European Qualifiers overall ranking criteria.

        Results against 5th-placed teams in 5-team groups are discarded.
        Order: group position, points, goal difference, goals for,
        away goals for, wins, away wins, fair play, Nations League rank.
        """
        s = gs.standings[team]
        group_size = len(gs.teams)

        valid_matches = s.matches
        if group_size == 5:
            sorted_teams = gs.get_sorted_teams()
            fifth_place = sorted_teams[4]
            valid_matches = [m for m in s.matches if m.home != fifth_place and m.away != fifth_place]

        pts = 0; gf = 0; ga = 0; away_gf = 0; wins = 0; away_wins = 0

        for m in valid_matches:
            if m.home == team:
                gf += m.home_goals; ga += m.away_goals
                if m.home_goals > m.away_goals: pts += 3; wins += 1
                elif m.home_goals == m.away_goals: pts += 1
            else:
                gf += m.away_goals; ga += m.home_goals; away_gf += m.away_goals
                if m.away_goals > m.home_goals: pts += 3; wins += 1; away_wins += 1
                elif m.away_goals == m.home_goals: pts += 1

        group_position = gs.get_sorted_teams().index(team) + 1
        # Fair play conduct points (noisy in reality; modelled as a small random draw)
        fair_play = random.randint(0, 15)
        # Interim Nations League ranking proxied by initial Elo (higher = better)
        nl_rank = initial_elo_ratings.get(team, config.initial_elo)

        return (
            -group_position, -pts, -(gf - ga), -gf, -away_gf,
            -wins, -away_wins, fair_play, -nl_rank
        )

    @staticmethod
    def get_overall_ranking_for_runners_up(runners_up: List[str], group_stages: Dict[str, GroupStage], config: Config) -> List[str]:
        def runner_up_key(team: str):
            for group_name, gs in group_stages.items():
                if team in gs.standings:
                    return HostManager._overall_ranking_key(team, gs, config)
            return (0, 0, 0, 0, 0, 0, 0, 0, 0)

        return sorted(runners_up, key=runner_up_key)

    @staticmethod
    def resolve(winners: List[str], runners_up: List[str], group_stages: Dict[str, GroupStage], config: Config) -> Tuple[Set[str], List[str], int]:
        hosts = config.hosts

        # 1. Group winners qualify directly
        direct = set(winners)

        # 2. Best 8 runners-up qualify directly (Hosts can qualify here normally)
        runners_up_ranked = HostManager.get_overall_ranking_for_runners_up(runners_up, group_stages, config)
        best_runners_up = runners_up_ranked[:config.num_best_runners_up]
        direct.update(best_runners_up)

        # 3. Two spots are reserved for the two best-ranked host nations that
        #    failed to qualify as group winners or among the 8 best runners-up.
        unqualified_hosts = [h for h in hosts if h not in direct]

        def host_ranking_key(host: str):
            for group_name, gs in group_stages.items():
                if host in gs.standings:
                    return HostManager._overall_ranking_key(host, gs, config)
            return (0, 0, 0, 0, 0, 0, 0, 0, 0)

        unqualified_hosts_ranked = sorted(unqualified_hosts, key=host_ranking_key)
        host_safety_teams = unqualified_hosts_ranked[:config.host_safety_slots]
        host_safety_set = set(host_safety_teams)

        # 4. Enforce 24-team cap: host free passes are guaranteed, so trim the
        #    lowest-ranked best runners-up when hosts push the total over 24.
        direct.update(host_safety_set)
        while len(direct) > 24:
            lowest_ru = next((t for t in reversed(runners_up_ranked) if t in direct and t not in hosts), None)
            if lowest_ru is None:
                break
            direct.discard(lowest_ru)
        host_slots_used = len(direct.intersection(host_safety_set))

        # 5. Playoff pool consists ONLY of non-qualified non-hosts
        playoff_pool = [t for t in all_teams if t not in direct and t not in hosts]

        assert not any(h in playoff_pool for h in hosts), "Host leaked into playoff pool!"
        assert len(direct) <= 24, f"Direct qualifiers exceed 24: {len(direct)}"

        return direct, playoff_pool, host_slots_used

# -------------------------------------------------------------
# 7. TOURNAMENT SIMULATION ENGINE
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
    def __init__(self, qualified_teams: List[str], elo_system: EloSystem, config: Config):
        self.teams = qualified_teams
        self.elo = elo_system
        self.config = config
        self.hosts = config.hosts

    def draw_groups(self):
        groups = {f"Group {chr(65+i)}": [] for i in range(6)}
        host_groups = {
            "Wales": "Group A",
            "England": "Group B",
            "Northern Ireland": "Group D",
            "Republic of Ireland": "Group E",
            "Scotland": "Group F"
        }
        
        placed_hosts = []
        for host, grp in host_groups.items():
            if host in self.teams:
                groups[grp].append(host)
                placed_hosts.append(host)
                
        remaining = [t for t in self.teams if t not in placed_hosts]
        random.shuffle(remaining)
        
        idx = 0
        for grp_name, grp_teams in groups.items():
            needed = 4 - len(grp_teams)
            for _ in range(needed):
                grp_teams.append(remaining[idx])
                idx += 1
                
        return groups

    def simulate_tournament_match(self, team_a, team_b):
        # Apply home advantage for host nations in the tournament
        elo_a_boost = self.config.home_boost(team_a) if team_a in self.hosts else 0
        elo_b_boost = self.config.home_boost(team_b) if team_b in self.hosts else 0
        
        orig_a = self.elo.ratings.get(team_a, self.config.initial_elo)
        orig_b = self.elo.ratings.get(team_b, self.config.initial_elo)
        
        self.elo.ratings[team_a] = orig_a + elo_a_boost
        self.elo.ratings[team_b] = orig_b + elo_b_boost
        
        g_a, g_b = self.elo.simulate_goals(team_a, team_b)
        
        # Restore original ratings immediately after 90 mins simulation
        self.elo.ratings[team_a] = orig_a
        self.elo.ratings[team_b] = orig_b
        
        if g_a != g_b:
            winner = team_a if g_a > g_b else team_b
            self.elo.update(team_a, team_b, g_a, g_b)
            return winner, g_a, g_b
            
        # Extra time
        self.elo.ratings[team_a] = orig_a + elo_a_boost
        self.elo.ratings[team_b] = orig_b + elo_b_boost
        et_a, et_b = self.elo.simulate_goals(team_a, team_b, scale_factor=0.33)
        self.elo.ratings[team_a] = orig_a
        self.elo.ratings[team_b] = orig_b
        
        g_a += et_a
        g_b += et_b
        if g_a != g_b:
            winner = team_a if g_a > g_b else team_b
            self.elo.update(team_a, team_b, g_a, g_b)
            return winner, g_a, g_b
            
        # Penalties
        diff = orig_a - orig_b
        prob_a = 1 / (1 + math.exp(-diff / 150))
        winner = team_a if random.random() < prob_a else team_b
        # Penalties don't update Elo (no open-play result)
        return winner, g_a, g_b

    def simulate_group_stage(self, groups):
        standings = {}
        third_placed = []
        advancers = []
        
        for grp_name, teams in groups.items():
            matches = [
                (teams[0], teams[1]), (teams[2], teams[3]),
                (teams[0], teams[2]), (teams[1], teams[3]),
                (teams[0], teams[3]), (teams[1], teams[2])
            ]
            
            group_standings = {t: {"pts": 0, "gf": 0, "ga": 0} for t in teams}
            
            for home, away in matches:
                winner, g_h, g_a = self.simulate_tournament_match(home, away)
                
                group_standings[home]["gf"] += g_h
                group_standings[home]["ga"] += g_a
                group_standings[away]["gf"] += g_a
                group_standings[away]["ga"] += g_h
                
                if winner == home:
                    group_standings[home]["pts"] += 3
                elif winner == away:
                    group_standings[away]["pts"] += 3
                else:
                    group_standings[home]["pts"] += 1
                    group_standings[away]["pts"] += 1
                    
            sorted_teams = sorted(teams, key=lambda t: (
                -group_standings[t]["pts"],
                -(group_standings[t]["gf"] - group_standings[t]["ga"]),
                -group_standings[t]["gf"]
            ))
            
            standings[grp_name] = sorted_teams
            advancers.append(sorted_teams[0])
            advancers.append(sorted_teams[1])
            third_placed.append((grp_name, sorted_teams[2], group_standings[sorted_teams[2]]))
            
        third_placed.sort(key=lambda x: (
            -x[2]["pts"],
            -(x[2]["gf"] - x[2]["ga"]),
            -x[2]["gf"]
        ))
        
        for i in range(4):
            advancers.append(third_placed[i][1])
            
        return standings, advancers, third_placed[:4]

    def resolve_r16(self, standings, third_placed_teams):
        third_grps = frozenset([t[0].replace("Group ", "") for t in third_placed_teams])
        matchups = THIRD_PLACE_MATCHUPS.get(third_grps)
        if not matchups:
            raise ValueError(f"Unknown third placed combination: {third_grps}")
            
        def get_team(grp, pos):
            if pos == 2:
                for t in third_placed_teams:
                    if t[0] == grp:
                        return t[1]
            return standings[grp][pos]
            
        r16_matches = [
            (get_team("Group A", 0), get_team("Group C", 1)), # Match 37
            (get_team("Group A", 1), get_team("Group B", 1)), # Match 38
            (get_team("Group B", 0), get_team(matchups['1B'].replace("3", "Group "), 2)), # Match 39
            (get_team("Group C", 0), get_team(matchups['1C'].replace("3", "Group "), 2)), # Match 40
            (get_team("Group F", 0), get_team(matchups['1F'].replace("3", "Group "), 2)), # Match 41
            (get_team("Group D", 1), get_team("Group E", 1)), # Match 42
            (get_team("Group D", 0), get_team("Group F", 1)), # Match 43
            (get_team("Group E", 0), get_team(matchups['1E'].replace("3", "Group "), 2))  # Match 44
        ]
        return r16_matches

    def simulate_knockout(self, r16_matches):
        def play_match(t1, t2):
            winner, _, _ = self.simulate_tournament_match(t1, t2)
            return winner
            
        w37 = play_match(*r16_matches[0])
        w38 = play_match(*r16_matches[1])
        w39 = play_match(*r16_matches[2])
        w40 = play_match(*r16_matches[3])
        w41 = play_match(*r16_matches[4])
        w42 = play_match(*r16_matches[5])
        w43 = play_match(*r16_matches[6])
        w44 = play_match(*r16_matches[7])
        
        w45 = play_match(w39, w37)
        w46 = play_match(w41, w42)
        w47 = play_match(w44, w43)
        w48 = play_match(w40, w38)
        
        w49 = play_match(w45, w46)
        w50 = play_match(w47, w48)
        
        final_w = play_match(w49, w50)
        
        return {
            "r16": [w37, w38, w39, w40, w41, w42, w43, w44],
            "qf": [w45, w46, w47, w48],
            "sf": [w49, w50],
            "final": [final_w]
        }

    def run(self):
        groups = self.draw_groups()
        standings, advancers, third_placed = self.simulate_group_stage(groups)
        
        r16_teams = set(advancers)
        r16_matches = self.resolve_r16(standings, third_placed)
        knockout_results = self.simulate_knockout(r16_matches)

        group_finishes = {}
        for grp_name, sorted_teams in standings.items():
            for pos, team in enumerate(sorted_teams):
                group_finishes[team] = pos + 1
        
        return {
            "r16": r16_teams,
            "qf": set(knockout_results["qf"]),
            "sf": set(knockout_results["sf"]),
            "final": set(knockout_results["final"]),
            "winner": knockout_results["final"][0],
            "group_finishes": group_finishes
        }

# -------------------------------------------------------------
# 8. MAIN SIMULATION
# -------------------------------------------------------------
all_teams = [
    "Albania", "Andorra", "Armenia", "Austria", "Azerbaijan", "Belarus", "Belgium", "Bosnia and Herzegovina",
    "Bulgaria", "Croatia", "Cyprus", "Czech Republic", "Denmark", "England", "Estonia", "Faroe Islands",
    "Finland", "France", "Georgia", "Germany", "Gibraltar", "Greece", "Hungary", "Iceland", "Israel", "Italy",
    "Kazakhstan", "Kosovo", "Latvia", "Liechtenstein", "Lithuania", "Luxembourg", "Malta", "Moldova",
    "Montenegro", "Netherlands", "North Macedonia", "Northern Ireland", "Norway", "Poland", "Portugal",
    "Republic of Ireland", "Romania", "San Marino", "Scotland", "Serbia", "Slovakia", "Slovenia", "Spain",
    "Sweden", "Switzerland", "Turkey", "Ukraine", "Wales"
]

initial_elo_ratings = {
    'Spain': 2165, 'France': 2082, 'England': 2020, 'Portugal': 1984, 'Netherlands': 1961,
    'Croatia': 1930, 'Germany': 1923, 'Norway': 1912, 'Turkey': 1902, 'Switzerland': 1889, 'Denmark': 1870,
    'Belgium': 1866, 'Italy': 1856, 'Austria': 1827, 'Serbia': 1769, 'Ukraine': 1767, 'Scotland': 1767,
    'Greece': 1752, 'Poland': 1729, 'Czech Republic': 1726, 'Kosovo': 1721,
    'Sweden': 1719, 'Hungary': 1703, 'Wales': 1698, 'Slovenia': 1694, 'Republic of Ireland': 1691,
    'Slovakia': 1673, 'Georgia': 1653, 'Albania': 1646, 'Israel': 1634, 'Romania': 1627,
    'Northern Ireland': 1601, 'Bosnia and Herzegovina': 1594, 'North Macedonia': 1589, 'Iceland': 1571
}
for team in all_teams:
    if team not in initial_elo_ratings:
        initial_elo_ratings[team] = 1500

def build_groups(hosts: List[str], config: Config) -> List[List[str]]:
    """Builds 12 groups (6 of 4 teams, 6 of 5 teams) with hosts separated and unique draws."""
    groups = [[] for _ in range(config.num_groups)]
    
    shuffled_hosts = list(hosts)
    random.shuffle(shuffled_hosts)
    for i, host in enumerate(shuffled_hosts):
        groups[i].append(host)
        
    remaining = [t for t in all_teams if t not in hosts]
    random.shuffle(remaining)
    
    group_sizes = [4] * 6 + [5] * 6
    random.shuffle(group_sizes)
    
    idx = 0
    for i in range(config.num_groups):
        needed = group_sizes[i] - len(groups[i])
        for _ in range(needed):
            groups[i].append(remaining[idx])
            idx += 1
            
    return groups

def run_single_simulation(seed: int) -> Tuple[Dict[str, int], Dict[str, int], int, Dict[str, Dict[str, int]]]:
    """Runs one full qualifying simulation + 10 tournament simulations."""
    random.seed(seed)
    np.random.seed(seed)
    
    config = CONFIG
    elo = EloSystem(initial_elo_ratings, config)
    groups = build_groups(config.hosts, config)
    
    winners = []
    runners_up = []
    group_stages = {}

    for i, group in enumerate(groups):
        group_name = chr(65 + i)
        gs = GroupStage(group, elo, config)
        gs.simulate()
        standings = gs.get_sorted_teams()
        winners.append(standings[0])
        runners_up.append(standings[1])
        group_stages[group_name] = gs

    direct_qualifiers, playoff_pool, host_slots_used = HostManager.resolve(
        winners, runners_up, group_stages, config
    )
    
    assert len(direct_qualifiers) <= 24, f"Direct: {len(direct_qualifiers)} exceeds 24"
    expected_playoffs = 24 - len(direct_qualifiers)
    playoff_qualifiers = set()

    if expected_playoffs > 0:
        # Select playoff participants by Elo: the weakest runners-up and the
        # strongest remaining non-qualified teams act as the Nations League pool.
        runners_up_sorted = sorted(runners_up, key=lambda t: elo.ratings.get(t, 1500))
        worst_runners_up = [t for t in runners_up_sorted if t not in direct_qualifiers]

        nl_candidates = [t for t in all_teams if t not in direct_qualifiers and t not in runners_up]
        nl_candidates_sorted = sorted(nl_candidates, key=lambda t: elo.ratings.get(t, 1500), reverse=True)

        if host_slots_used == 2:
            num_paths, num_worst_ru, teams_needed = 2, 4, 8
        elif host_slots_used == 1:
            num_paths, num_worst_ru, teams_needed = 3, 3, 12
        else:
            num_paths, num_worst_ru, teams_needed = 4, 4, 8

        playoff_teams = list(worst_runners_up[:num_worst_ru])
        for t in nl_candidates_sorted:
            if len(playoff_teams) >= teams_needed:
                break
            if t not in playoff_teams:
                playoff_teams.append(t)

        random.shuffle(playoff_teams)

        if host_slots_used == 0:
            for i in range(0, len(playoff_teams) - 1, 2):
                playoff_qualifiers.add(KnockoutMatch.home_away(elo, playoff_teams[i], playoff_teams[i + 1]))
        else:
            for path in range(num_paths):
                path_teams = playoff_teams[path*4:(path+1)*4]
                if len(path_teams) == 4:
                    playoff_qualifiers.add(PlayoffPath.simulate_bracket(elo, path_teams))

    assert len(playoff_qualifiers) == expected_playoffs, f"Playoffs: {len(playoff_qualifiers)}, expected {expected_playoffs}"
    assert len(direct_qualifiers.intersection(playoff_qualifiers)) == 0, "Overlap detected"
    assert len(direct_qualifiers) + len(playoff_qualifiers) == 24, f"Total: {len(direct_qualifiers) + len(playoff_qualifiers)}"

    direct_counter = {t: 1 for t in direct_qualifiers}
    playoff_counter = {t: 1 for t in playoff_qualifiers}

    all_five = ["England", "Scotland", "Wales", "Republic of Ireland", "Northern Ireland"]
    all_qualified = 1 if all(t in direct_qualifiers or t in playoff_qualifiers for t in all_five) else 0

    # --- TOURNAMENT SIMULATION (10 runs per qualifying sim) ---
    qualified_teams = list(direct_qualifiers) + list(playoff_qualifiers)
    t_stats = {
        "winner": defaultdict(int),
        "final": defaultdict(int),
        "semi": defaultdict(int),
        "qf": defaultdict(int),
        "r16": defaultdict(int)
    }
    g_stats = {
        "win_group": defaultdict(int),
        "second": defaultdict(int),
        "third_advance": defaultdict(int),
    }

    # Use final qualifying Elo ratings as the baseline for the tournament
    base_ratings = elo.ratings.copy()

    for _ in range(10):
        tournament_elo = EloSystem(base_ratings, config)
        tourn_sim = TournamentSimulation(qualified_teams, tournament_elo, config)
        results = tourn_sim.run()

        for t in results["r16"]: t_stats["r16"][t] += 1
        for t in results["qf"]: t_stats["qf"][t] += 1
        for t in results["sf"]: t_stats["semi"][t] += 1
        for t in results["final"]: t_stats["final"][t] += 1
        t_stats["winner"][results["winner"]] += 1

        for team, pos in results["group_finishes"].items():
            if pos == 1:
                g_stats["win_group"][team] += 1
            elif pos == 2:
                g_stats["second"][team] += 1
            elif pos == 3:
                g_stats["third_advance"][team] += 1

    return direct_counter, playoff_counter, all_qualified, t_stats, g_stats, host_slots_used

def worker_task(seed: int) -> Tuple[Dict[str, int], Dict[str, int], int, Dict[str, Dict[str, int]], Dict[str, Dict[str, int]], int]:
    """Worker function for multiprocessing."""
    return run_single_simulation(seed)

# -------------------------------------------------------------
# 9. OUTPUT DISPLAY LOGIC
# -------------------------------------------------------------
if __name__ == "__main__":
    print("Starting UEFA EURO 2028 Qualifying & Tournament Simulation...")
    start_time = time.time()
    
    num_cores = cpu_count()
    import argparse
    parser = argparse.ArgumentParser(description="UEFA EURO 2028 Simulation")
    parser.add_argument("--seed", type=int, default=None, help="Base seed for reproducibility (random if omitted)")
    args = parser.parse_args()

    base_seed = args.seed if args.seed is not None else random.randint(0, 2**31 - 1)
    seed_rng = random.Random(base_seed)
    seeds = [seed_rng.getrandbits(32) for _ in range(CONFIG.num_simulations)]
    print(f"Run seed: {base_seed}")
    
    standard_direct_counter = defaultdict(int)
    playoff_counter = defaultdict(int)
    total_all_five = 0
    total_host_slots = 0
    host_slots_counter = defaultdict(int)

    tournament_stats = {
        "winner": defaultdict(int),
        "final": defaultdict(int),
        "semi": defaultdict(int),
        "qf": defaultdict(int),
        "r16": defaultdict(int)
    }

    group_stats = {
        "win_group": defaultdict(int),
        "second": defaultdict(int),
        "third_advance": defaultdict(int)
    }

    with Pool(num_cores) as pool:
        for i, result in enumerate(pool.imap_unordered(worker_task, seeds)):
            d_c, p_c, af, t_stats, g_stats, host_slots_used = result
            for t, v in d_c.items(): standard_direct_counter[t] += v
            for t, v in p_c.items(): playoff_counter[t] += v
            total_all_five += af
            total_host_slots += host_slots_used
            host_slots_counter[host_slots_used] += 1

            for stage, counts in t_stats.items():
                for t, v in counts.items():
                    tournament_stats[stage][t] += v

            for finish, counts in g_stats.items():
                for t, v in counts.items():
                    group_stats[finish][t] += v
            
            completed_sims = i + 1
            percent = completed_sims / CONFIG.num_simulations
            bar_len = 40
            filled = int(bar_len * percent)
            bar = '=' * filled + '-' * (bar_len - filled)

            elapsed = time.time() - start_time
            if percent > 0:
                eta = elapsed / percent - elapsed
                eta_str = time.strftime("%H:%M:%S", time.gmtime(eta))
            else:
                eta_str = "--:--:--"
            elapsed_str = time.strftime("%H:%M:%S", time.gmtime(elapsed))

            sys.stdout.write(f'\rProgress: |{bar}| {percent*100:.3f}% ({completed_sims}/{CONFIG.num_simulations})  Elapsed: {elapsed_str}  ETA: {eta_str}')
            sys.stdout.flush()
            
    print()
    elapsed = time.time() - start_time
    print(f"Simulation completed in {elapsed:.2f} seconds.\n")
    
    print("UEFA EURO 2028 QUALIFYING SIMULATION RESULTS")
    print(f"Total qualifying simulations: {CONFIG.num_simulations}")
    print("\nEURO 2028 TOTAL QUALIFICATION PROBABILITIES:")
    
    total_qual = {team: standard_direct_counter[team] + playoff_counter[team] for team in all_teams}
    sorted_teams = sorted(all_teams, key=lambda t: total_qual[t], reverse=True)
    
    for team in sorted_teams:
        if total_qual[team] > 0:
            pct = 100 * total_qual[team] / CONFIG.num_simulations
            std_direct_pct = 100 * standard_direct_counter[team] / CONFIG.num_simulations
            playoff_pct = 100 * playoff_counter[team] / CONFIG.num_simulations
            label = " (Host)" if team in CONFIG.hosts else ""
            print(f"{team:22}: {pct:6.2f}% (Direct: {std_direct_pct:6.2f}%, Playoffs: {playoff_pct:6.2f}%){label}")
            
    all_five_pct = 100 * total_all_five / CONFIG.num_simulations
    print(f"\nProbability that England, Scotland, Wales, Republic of Ireland and Northern Ireland ALL qualify: {all_five_pct:.2f}%")

    avg_host_slots = total_host_slots / CONFIG.num_simulations
    slots_breakdown = ", ".join(f"{k} slot(s): {100*host_slots_counter[k]/CONFIG.num_simulations:.1f}%" for k in sorted(host_slots_counter))
    

    # --- GROUP STAGE OUTPUT ---
    total_tourn_sims = CONFIG.num_simulations * 10
    print("\n" + "="*60)
    print("UEFA EURO 2028 TOURNAMENT GROUP STAGE FINISH PROBABILITIES")
    print(f"Total tournament simulations: {total_tourn_sims}")
    print("="*60)

    sorted_group_teams = sorted(
        all_teams,
        key=lambda t: (group_stats["win_group"][t], group_stats["second"][t], group_stats["third_advance"][t]),
        reverse=True
    )

    for team in sorted_group_teams:
        if group_stats["win_group"][team] > 0:
            win_g_pct = 100 * group_stats["win_group"][team] / total_tourn_sims
            second_pct = 100 * group_stats["second"][team] / total_tourn_sims
            third_pct = 100 * group_stats["third_advance"][team] / total_tourn_sims
            label = " (Host)" if team in CONFIG.hosts else ""
            print(f"{team:22}: Win Group: {win_g_pct:6.2f}% | 2nd: {second_pct:6.2f}% | 3rd: {third_pct:6.2f}%{label}")

    # --- TOURNAMENT OUTPUT ---
    print("\n" + "="*60)
    print("UEFA EURO 2028 TOURNAMENT PROBABILITIES")
    print(f"Total tournament simulations: {total_tourn_sims}")
    print("="*60)
    
    sorted_tourn_teams = sorted(all_teams, key=lambda t: tournament_stats["r16"][t], reverse=True)
    
    for team in sorted_tourn_teams:
        if tournament_stats["r16"][team] > 0:
            r16_pct = 100 * tournament_stats["r16"][team] / total_tourn_sims
            qf_pct = 100 * tournament_stats["qf"][team] / total_tourn_sims
            semi_pct = 100 * tournament_stats["semi"][team] / total_tourn_sims
            final_pct = 100 * tournament_stats["final"][team] / total_tourn_sims
            win_pct = 100 * tournament_stats["winner"][team] / total_tourn_sims
            print(f"{team:22} | R16: {r16_pct:5.2f}% | QF: {qf_pct:5.2f}% | SF: {semi_pct:5.2f}% | Final: {final_pct:5.2f}% | Win: {win_pct:5.2f}%")

    print(f"\nAverage reserved host slots required per qualifying sim: {avg_host_slots:.3f}  (by count -> {slots_breakdown})")