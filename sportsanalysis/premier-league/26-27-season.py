import random
import math
import csv
from pathlib import Path
from collections import defaultdict
from datetime import datetime
import numpy as np
from tqdm import tqdm
from typing import Dict, Tuple
from modules import FIXTURES_LIST, BETTING_MARKETS, POLYMARKET_TITLE, _load_historical_data

# ==========================================
# CONSTANTS
# ==========================================
BASE_K = 20.0
GOAL_DIFF_EXPECTED = 1.4

# These now match the optimized system you provided.
HOME_ADVANTAGE_ELO = 85.0
K_FACTOR = 30.0

ELO_SCALE = 400
NUM_TEAMS = 20
LEAGUE_AVERAGE_ELO = 1500.0

DAMPENING_ENABLED = True
DAMPENING_FACTOR = 0.25

PROMOTED_TEAMS = {"Ipswich", "Coventry", "Hull"}
PROMOTED_PENALTY = 75.0

# This is filled after historical loading.
# The OptimizedELORatingSystem class reads this global.
wdl_rates = {}


# ==========================================
# MISSING HELPER USED BY YOUR CLASS
# ==========================================
def get_adjusted_elo(team: str, ratings) -> float:
    """
    Simple passthrough to current rating.
    If you later want team-specific adjustments, do them here.
    """
    return float(ratings.get(team, 1500.0))


# ==========================================
# OPTIMIZED ELO RATING SYSTEM
# ==========================================
class OptimizedELORatingSystem:
    def __init__(self, k_factor=30, home_advantage=85):
        self.k_factor = k_factor
        self.home_advantage = home_advantage
        self.ratings = defaultdict(lambda: 1500.0)
        self.match_weights = {'league': 1.5}

    def expected_score(self, ra, rb):
        return 1 / (1 + 10 ** ((rb - ra) / 400))

    def update_ratings(self, home, away, hs, aws, match_type='league'):
        K = self.k_factor * self.match_weights.get(match_type, 1.5)
        hr, ar = self.ratings[home] + self.home_advantage, self.ratings[away]

        gm = min(1 + math.log(1 + abs(hs - aws)), 2.0)

        eh, ea = self.expected_score(hr, ar), self.expected_score(ar, hr)

        ah = 1 if hs > aws else (0.5 if hs == aws else 0)
        aa = 1 if aws > hs else (0.5 if hs == aws else 0)

        self.ratings[home] += K * gm * (ah - eh)
        self.ratings[away] += K * gm * (aa - ea)

    def predict_score(self, home, away, neutral=False):
        ha = 0 if neutral else self.home_advantage

        diff = (
            get_adjusted_elo(home, self.ratings)
            - get_adjusted_elo(away, self.ratings)
            + ha
        )

        hxg = 0.6 + 1.7 / (1 + math.exp(-diff / 400))
        axg = 0.6 + 1.7 / (1 + math.exp(diff / 400))

        closeness = math.exp(-(diff ** 2) / (2 * 180 ** 2))

        bd = (
            (wdl_rates[home]["win"] - wdl_rates[home]["loss"])
            - (wdl_rates[away]["win"] - wdl_rates[away]["loss"])
        ) * 0.5

        hxg = hxg + bd * 0.15
        axg = axg - bd * 0.15

        tempo = 0.9 + 0.1 * (abs(diff) / 400)

        hxg = hxg * tempo
        axg = axg * tempo

        vb = 1 + (wdl_rates[home]["win"] - wdl_rates[home]["draw"]) * 0.1
        db = max((wdl_rates[home]["draw"] + wdl_rates[away]["draw"]) / 2, 0.3)

        ls = 0.05 + closeness * 0.25 * db

        lh = max(0.05, hxg - ls) * vb
        la = max(0.05, axg - ls)

        sg = np.random.poisson(ls)

        home_goals = int(np.random.poisson(lh) + sg)
        away_goals = int(np.random.poisson(la) + sg)

        return home_goals, away_goals



# ==========================================
# HISTORICAL DATA LOADER
# ==========================================



# ==========================================
# KEEP YOUR EXISTING FIXTURES_LIST HERE
# ==========================================
# FIXTURES_LIST = [...]
#
# IMPORTANT:
# The loader call must come after FIXTURES_LIST is defined.

EXTERNAL_ELOS, WDL_RATES = _load_historical_data()
wdl_rates = WDL_RATES


# ==========================================
# KEEP YOUR EXISTING BETTING_MARKETS AND POLYMARKET_TITLE HERE
# ==========================================
# BETTING_MARKETS = {...}
# POLYMARKET_TITLE = {...}


# ==========================================
# PROBABILITY UTILITIES
# ==========================================
def fractional_to_prob(num, den):
    return den / (num + den)


def implied_probabilities(odds_dict, normalize: bool = False):
    raw = {team: fractional_to_prob(num, den) for team, (num, den) in odds_dict.items()}

    if normalize:
        total_raw = sum(raw.values())
        return {team: (raw[team] / total_raw) * 100.0 for team in raw}

    return {team: raw[team] * 100.0 for team in raw}


def blend_probabilities(
    sim_pcts: Dict[str, float],
    implied_pcts: Dict[str, float],
    sim_weight: float = 0.7
) -> Dict[str, float]:
    return {
        team: sim_weight * sim_pcts.get(team, 0.0)
        + (1 - sim_weight) * implied_pcts.get(team, 0.0)
        for team in sim_pcts
    }


# ==========================================
# TEAM REGISTRY
# ==========================================
class TeamRegistry:
    def __init__(self):
        self.elos: Dict[str, float] = {}
        self.team_to_idx: Dict[str, int] = {}
        self.idx_to_team: List[str] = []

    def add_team(self, name: str, elo: float):
        idx = len(self.idx_to_team)
        self.elos[name] = elo
        self.team_to_idx[name] = idx
        self.idx_to_team.append(name)


# ==========================================
# SIMULATION USING OPTIMIZED ELO SYSTEM
# ==========================================
def run_single_simulation(registry, fixtures, base_ratings):
    team_names = registry.idx_to_team
    n_teams = len(team_names)

    # Fresh rating system for each simulation.
    system = OptimizedELORatingSystem(
        k_factor=K_FACTOR,
        home_advantage=HOME_ADVANTAGE_ELO
    )

    # Start each season from the same baseline ratings.
    system.ratings.update(base_ratings)

    pts = np.zeros(n_teams, dtype=np.int64)
    gf = np.zeros(n_teams, dtype=np.int64)
    ga = np.zeros(n_teams, dtype=np.int64)

    for home_name, away_name in fixtures:
        h_idx = registry.team_to_idx[home_name]
        a_idx = registry.team_to_idx[away_name]

        # Simulate actual scoreline.
        home_goals, away_goals = system.predict_score(
            home_name,
            away_name,
            neutral=False
        )

        # Update ELO based on actual simulated goals.
        system.update_ratings(
            home_name,
            away_name,
            home_goals,
            away_goals,
            match_type="league"
        )

        if home_goals > away_goals:
            home_pts, away_pts = 3, 0
        elif home_goals == away_goals:
            home_pts, away_pts = 1, 1
        else:
            home_pts, away_pts = 0, 3

        pts[h_idx] += home_pts
        pts[a_idx] += away_pts

        gf[h_idx] += home_goals
        ga[h_idx] += away_goals

        gf[a_idx] += away_goals
        ga[a_idx] += home_goals

    table = {
        name: {
            "Pts": int(pts[i]),
            "GF": int(gf[i]),
            "GA": int(ga[i]),
            "GD": int(gf[i] - ga[i]),
        }
        for i, name in enumerate(team_names)
    }

    ranking = sorted(
        table.items(),
        key=lambda x: (x[1]["Pts"], x[1]["GD"], x[1]["GF"]),
        reverse=True
    )

    return table, ranking, dict(system.ratings)


# ==========================================
# MAIN EXECUTION
# ==========================================
def main():
    # Optional reproducibility.
    SEED = 42
    if SEED is not None:
        random.seed(SEED)
        np.random.seed(SEED)

    registry = TeamRegistry()

    fixture_teams = {team for pair in FIXTURES_LIST for team in pair}
    min_elo = min(EXTERNAL_ELOS[name] for name in fixture_teams)

    # Sorted for deterministic team ordering.
    for name in sorted(fixture_teams):
        elo = EXTERNAL_ELOS[name]

        if name in PROMOTED_TEAMS:
            elo = min_elo - PROMOTED_PENALTY

        registry.add_team(name, elo)

    team_names = registry.idx_to_team
    teams = list(team_names)

    initial_elos = np.array(
        [registry.elos[name] for name in team_names],
        dtype=np.float64
    )

    # Regress toward league average.
    initial_elos = 0.68 * initial_elos + 0.32 * LEAGUE_AVERAGE_ELO

    # Optional dampening.
    if DAMPENING_ENABLED:
        mean_elo = np.mean(initial_elos)
        initial_elos = initial_elos - DAMPENING_FACTOR * (initial_elos - mean_elo)

    base_ratings = {
        team: float(elo)
        for team, elo in zip(team_names, initial_elos)
    }

    NUM_SIMS = 2500

    print("\n" + "=" * 80)
    print(f"RUNNING PREMIER LEAGUE SIMULATIONS | Sims: {NUM_SIMS}")
    print("=" * 80)

    # Only title odds are blended in your original output.
    imp_title = implied_probabilities(
        {
            t: BETTING_MARKETS["League Winner"].get(t, (1000, 1))
            for t in teams
        },
        normalize=True
    )

    poly_title = {t: POLYMARKET_TITLE.get(t, 0.0) for t in teams}

    per_sim_blended = {
        "ucl": defaultdict(float),
        "europaleague": defaultdict(float),
        "tophalf": defaultdict(float),
        "stayup": defaultdict(float),
        "releg": defaultdict(float),
        "bottom": defaultdict(float),
    }

    points_dist = defaultdict(list)
    position_counts = defaultdict(lambda: defaultdict(int))
    title_counts = defaultdict(int)

    for _ in tqdm(range(NUM_SIMS), desc="Simulating", unit="sim"):
        table, ranking, _ = run_single_simulation(
            registry,
            FIXTURES_LIST,
            base_ratings
        )

        for pos, (team, data) in enumerate(ranking, 1):
            pts = data["Pts"]

            points_dist[team].append(pts)
            position_counts[team][pos] += 1

            if pos == 1:
                title_counts[team] += 1

            if pos <= 4:
                per_sim_blended["ucl"][team] += 100.0

            if pos == 5:
                per_sim_blended["europaleague"][team] += 100.0

            if pos <= 10:
                per_sim_blended["tophalf"][team] += 100.0

            if pos <= 17:
                per_sim_blended["stayup"][team] += 100.0

            if pos >= 18:
                per_sim_blended["releg"][team] += 100.0

            if pos == 20:
                per_sim_blended["bottom"][team] += 100.0

    pure_sim_title = {
        t: title_counts[t] / NUM_SIMS * 100
        for t in teams
    }

    combined_title = {
        t: (pure_sim_title[t] + imp_title[t] + poly_title[t]) / 3
        for t in teams
    }

    total_title = sum(combined_title.values())
    if total_title > 0:
        combined_title = {
            t: (v / total_title) * 100
            for t, v in combined_title.items()
        }

    combined_ucl = {
        t: per_sim_blended["ucl"][t] / NUM_SIMS
        for t in teams
    }

    combined_europaleague = {
        t: per_sim_blended["europaleague"][t] / NUM_SIMS
        for t in teams
    }

    combined_tophalf = {
        t: per_sim_blended["tophalf"][t] / NUM_SIMS
        for t in teams
    }

    combined_stayup = {
        t: per_sim_blended["stayup"][t] / NUM_SIMS
        for t in teams
    }

    combined_releg = {
        t: per_sim_blended["releg"][t] / NUM_SIMS
        for t in teams
    }

    combined_bottom = {
        t: per_sim_blended["bottom"][t] / NUM_SIMS
        for t in teams
    }

    print("\n" + "=" * 80)
    print("TEAM STATISTICS (2500 Sims | Blended)")
    print("=" * 80)
    print(
        f"{'Team':<15} {'AvgPts':<8} {'StdDev':<8} {'Title%':<8} "
        f"{'UCL%':<8} {'EuropaLeague%':<13} {'TotalEurope%':<13} "
        f"{'TopHalf%':<10} {'StayUp%':<9} {'Releg%':<8} {'Bottom%':<8}"
    )
    print("-" * 118)

    team_avgs = {
        team: sum(points_dist[team]) / len(points_dist[team])
        for team in teams
    }

    sorted_by_title = sorted(teams, key=lambda t: combined_title[t], reverse=True)

    for team in sorted_by_title:
        pts = points_dist[team]
        avg = team_avgs[team]
        std = math.sqrt(sum((x - avg) ** 2 for x in pts) / len(pts))

        print(
            f"{team:<15} {avg:<8.2f} {std:<8.2f} "
            f"{combined_title[team]:<8.2f} {combined_ucl[team]:<8.2f} "
            f"{combined_europaleague[team]:<13.2f} "
            f"{combined_ucl[team] + combined_europaleague[team]:<13.2f} "
            f"{combined_tophalf[team]:<10.2f} "
            f"{combined_stayup[team]:<9.2f} "
            f"{combined_releg[team]:<8.2f} {combined_bottom[team]:<8.2f}"
        )

    print("\n" + "=" * 80)
    print("MOST LIKELY FINISHING POSITIONS")
    print("=" * 80)

    team_solved = []

    for team, pos_counts in position_counts.items():
        most_likely_pos = max(pos_counts.items(), key=lambda x: x[1])[0]
        pct = pos_counts[most_likely_pos] / NUM_SIMS * 100
        team_solved.append((team, most_likely_pos, pct))

    team_solved.sort(key=lambda x: x[2], reverse=True)

    for team, pos, pct in team_solved:
        print(f"{team:<15} Most likely: {pos}th ({pct:.2f}%)")

    combined_solved = 1.0
    for _, _, pct in team_solved:
        combined_solved *= (pct / 100.0)

    print(f"\nCombined table solved %: {combined_solved * 100:.20f}%")

    stats_solved = {}

    for team in teams:
        title_count = position_counts[team].get(1, 0)
        ucl_count = sum(position_counts[team].get(pos, 0) for pos in range(1, 5))
        europa_count = position_counts[team].get(5, 0)
        tophalf_count = sum(position_counts[team].get(pos, 0) for pos in range(1, 11))
        stayup_count = sum(position_counts[team].get(pos, 0) for pos in range(1, 18))
        releg_count = sum(position_counts[team].get(pos, 0) for pos in range(18, 21))
        bottom_count = position_counts[team].get(20, 0)

        if title_count > 0:
            stats_solved.setdefault("Title", []).append(combined_title[team] / 100.0)

        if ucl_count > 0:
            stats_solved.setdefault("UCL", []).append(combined_ucl[team] / 100.0)

        if europa_count > 0:
            stats_solved.setdefault("EuropaLeague", []).append(
                combined_europaleague[team] / 100.0
            )

        if tophalf_count > 0:
            stats_solved.setdefault("TopHalf", []).append(combined_tophalf[team] / 100.0)

        if stayup_count > 0:
            stats_solved.setdefault("StayUp", []).append(combined_stayup[team] / 100.0)

        if releg_count > 0:
            stats_solved.setdefault("Releg", []).append(combined_releg[team] / 100.0)

        if bottom_count > 0:
            stats_solved.setdefault("Bottom", []).append(combined_bottom[team] / 100.0)

    print("\nCombined stats solved %:")
    for stat_name, probs in stats_solved.items():
        solved = 1.0
        for p in probs:
            solved *= p
        print(f"  {stat_name}: {solved * 100:.20f}%")


if __name__ == "__main__":
    main()