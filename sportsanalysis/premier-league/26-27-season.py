"""Premier League 2026/27 simulation.

Consumes Champions League simulation results from UCL.py to apply
European fatigue penalties and display CL winner probabilities
alongside PL projections.
"""

import math
import random
from collections import defaultdict
from typing import Dict, List, Tuple

import numpy as np
from tqdm import tqdm

from UCL import (
    ELO_SCALE,
    HOME_ADVANTAGE_ELO,
    LEAGUE_AVERAGE_ELO,
    ELO_SHRINKAGE,
    PL_TEAMS,
    compute_expected_goals,
    run_champions_league_simulation,
    sample_score,
)
from UEL import PL_UEL_TEAMS, run_europa_league_simulation

# ==========================================
# GLOBAL CONFIGURATION & CONSTANTS
# ==========================================

NUM_PL_SIMS = 2000

EUROPEAN_PENALTIES = {
    "UCL": 45.0,
    "UEL": 30.0,
    "UECL": 20.0,
}

# ==========================================
# PREMIER LEAGUE DATA
# ==========================================

FIXTURES_LIST = [
    ('Arsenal', 'Coventry'),
    ('Arsenal', 'Crystal Palace'),
    ('Arsenal', 'Everton'),
    ('Arsenal', 'Leeds'),
    ('Aston Villa', 'Arsenal'),
    ('Aston Villa', 'Brentford'),
    ('Aston Villa', 'Chelsea'),
    ('Bournemouth', 'Everton'),
    ('Bournemouth', 'Liverpool'),
    ('Bournemouth', 'Sunderland'),
    ('Bournemouth', 'Tottenham'),
    ('Brentford', 'Chelsea'),
    ('Brentford', 'Ipswich'),
    ('Brentford', 'Liverpool'),
    ('Brentford', 'Tottenham'),
    ('Brighton', 'Arsenal'),
    ('Brighton', 'Aston Villa'),
    ('Brighton', 'Crystal Palace'),
    ('Brighton', 'Fulham'),
    ('Chelsea', 'Bournemouth'),
    ('Chelsea', 'Brighton'),
    ('Chelsea', 'Coventry'),
    ('Coventry', 'Bournemouth'),
    ('Coventry', 'Hull'),
    ('Coventry', 'Newcastle'),
    ('Crystal Palace', 'Forest'),
    ('Crystal Palace', 'Ipswich'),
    ('Crystal Palace', 'Sunderland'),
    ('Everton', 'Chelsea'),
    ('Everton', 'Crystal Palace'),
    ('Everton', 'Forest'),
    ('Everton', 'Ipswich'),
    ('Forest', 'Coventry'),
    ('Forest', 'Leeds'),
    ('Forest', 'Newcastle'),
    ('Fulham', 'Chelsea'),
    ('Fulham', 'Hull'),
    ('Fulham', 'Leeds'),
    ('Fulham', 'Man United'),
    ('Hull', 'Everton'),
    ('Hull', 'Man City'),
    ('Hull', 'Man United'),
    ('Ipswich', 'Brighton'),
    ('Ipswich', 'Fulham'),
    ('Ipswich', 'Sunderland'),
    ('Leeds', 'Crystal Palace'),
    ('Leeds', 'Hull'),
    ('Leeds', 'Man United'),
    ('Leeds', 'Newcastle'),
    ('Liverpool', 'Aston Villa'),
    ('Liverpool', 'Fulham'),
    ('Liverpool', 'Man City'),
    ('Man City', 'Bournemouth'),
    ('Man City', 'Everton'),
    ('Man City', 'Ipswich'),
    ('Man City', 'Sunderland'),
    ('Man United', 'Arsenal'),
    ('Man United', 'Man City'),
    ('Man United', 'Tottenham'),
    ('Newcastle', 'Aston Villa'),
    ('Newcastle', 'Brentford'),
    ('Newcastle', 'Hull'),
    ('Newcastle', 'Liverpool'),
    ('Sunderland', 'Arsenal'),
    ('Sunderland', 'Brighton'),
    ('Sunderland', 'Man United'),
    ('Tottenham', 'Arsenal'),
    ('Tottenham', 'Aston Villa'),
    ('Tottenham', 'Everton'),
    ('Tottenham', 'Liverpool'),
    ('Arsenal', 'Aston Villa'),
    ('Arsenal', 'Bournemouth'),
    ('Arsenal', 'Brentford'),
    ('Arsenal', 'Brighton'),
    ('Arsenal', 'Chelsea'),
    ('Arsenal', 'Forest'),
    ('Arsenal', 'Fulham'),
    ('Arsenal', 'Hull'),
    ('Arsenal', 'Ipswich'),
    ('Arsenal', 'Liverpool'),
    ('Arsenal', 'Man City'),
    ('Arsenal', 'Man United'),
    ('Arsenal', 'Newcastle'),
    ('Arsenal', 'Sunderland'),
    ('Arsenal', 'Tottenham'),
    ('Aston Villa', 'Bournemouth'),
    ('Aston Villa', 'Brighton'),
    ('Aston Villa', 'Coventry'),
    ('Aston Villa', 'Crystal Palace'),
    ('Aston Villa', 'Everton'),
    ('Aston Villa', 'Forest'),
    ('Aston Villa', 'Fulham'),
    ('Aston Villa', 'Hull'),
    ('Aston Villa', 'Ipswich'),
    ('Aston Villa', 'Leeds'),
    ('Aston Villa', 'Liverpool'),
    ('Aston Villa', 'Man City'),
    ('Aston Villa', 'Man United'),
    ('Aston Villa', 'Newcastle'),
    ('Aston Villa', 'Sunderland'),
    ('Aston Villa', 'Tottenham'),
    ('Bournemouth', 'Arsenal'),
    ('Bournemouth', 'Aston Villa'),
    ('Bournemouth', 'Brentford'),
    ('Bournemouth', 'Brighton'),
    ('Bournemouth', 'Chelsea'),
    ('Bournemouth', 'Coventry'),
    ('Bournemouth', 'Crystal Palace'),
    ('Bournemouth', 'Forest'),
    ('Bournemouth', 'Fulham'),
    ('Bournemouth', 'Hull'),
    ('Bournemouth', 'Ipswich'),
    ('Bournemouth', 'Leeds'),
    ('Bournemouth', 'Man City'),
    ('Bournemouth', 'Man United'),
    ('Bournemouth', 'Newcastle'),
    ('Brentford', 'Arsenal'),
    ('Brentford', 'Aston Villa'),
    ('Brentford', 'Bournemouth'),
    ('Brentford', 'Brighton'),
    ('Brentford', 'Coventry'),
    ('Brentford', 'Crystal Palace'),
    ('Brentford', 'Everton'),
    ('Brentford', 'Forest'),
    ('Brentford', 'Fulham'),
    ('Brentford', 'Hull'),
    ('Brentford', 'Leeds'),
    ('Brentford', 'Man City'),
    ('Brentford', 'Man United'),
    ('Brentford', 'Newcastle'),
    ('Brentford', 'Sunderland'),
    ('Brighton', 'Bournemouth'),
    ('Brighton', 'Brentford'),
    ('Brighton', 'Chelsea'),
    ('Brighton', 'Coventry'),
    ('Brighton', 'Everton'),
    ('Brighton', 'Forest'),
    ('Brighton', 'Hull'),
    ('Brighton', 'Ipswich'),
    ('Brighton', 'Leeds'),
    ('Brighton', 'Liverpool'),
    ('Brighton', 'Man City'),
    ('Brighton', 'Man United'),
    ('Brighton', 'Newcastle'),
    ('Brighton', 'Sunderland'),
    ('Brighton', 'Tottenham'),
    ('Chelsea', 'Arsenal'),
    ('Chelsea', 'Aston Villa'),
    ('Chelsea', 'Brentford'),
    ('Chelsea', 'Crystal Palace'),
    ('Chelsea', 'Everton'),
    ('Chelsea', 'Forest'),
    ('Chelsea', 'Fulham'),
    ('Chelsea', 'Hull'),
    ('Chelsea', 'Ipswich'),
    ('Chelsea', 'Leeds'),
    ('Chelsea', 'Liverpool'),
    ('Chelsea', 'Man City'),
    ('Chelsea', 'Man United'),
    ('Chelsea', 'Newcastle'),
    ('Chelsea', 'Sunderland'),
    ('Chelsea', 'Tottenham'),
    ('Coventry', 'Arsenal'),
    ('Coventry', 'Aston Villa'),
    ('Coventry', 'Brentford'),
    ('Coventry', 'Brighton'),
    ('Coventry', 'Chelsea'),
    ('Coventry', 'Crystal Palace'),
    ('Coventry', 'Everton'),
    ('Coventry', 'Forest'),
    ('Coventry', 'Fulham'),
    ('Coventry', 'Ipswich'),
    ('Coventry', 'Leeds'),
    ('Coventry', 'Liverpool'),
    ('Coventry', 'Man City'),
    ('Coventry', 'Man United'),
    ('Coventry', 'Sunderland'),
    ('Coventry', 'Tottenham'),
    ('Crystal Palace', 'Arsenal'),
    ('Crystal Palace', 'Aston Villa'),
    ('Crystal Palace', 'Bournemouth'),
    ('Crystal Palace', 'Brentford'),
    ('Crystal Palace', 'Brighton'),
    ('Crystal Palace', 'Chelsea'),
    ('Crystal Palace', 'Coventry'),
    ('Crystal Palace', 'Everton'),
    ('Crystal Palace', 'Fulham'),
    ('Crystal Palace', 'Hull'),
    ('Crystal Palace', 'Leeds'),
    ('Crystal Palace', 'Liverpool'),
    ('Crystal Palace', 'Man City'),
    ('Crystal Palace', 'Man United'),
    ('Crystal Palace', 'Newcastle'),
    ('Crystal Palace', 'Tottenham'),
    ('Everton', 'Arsenal'),
    ('Everton', 'Aston Villa'),
    ('Everton', 'Bournemouth'),
    ('Everton', 'Brentford'),
    ('Everton', 'Brighton'),
    ('Everton', 'Coventry'),
    ('Everton', 'Fulham'),
    ('Everton', 'Hull'),
    ('Everton', 'Leeds'),
    ('Everton', 'Liverpool'),
    ('Everton', 'Man City'),
    ('Everton', 'Man United'),
    ('Everton', 'Newcastle'),
    ('Everton', 'Sunderland'),
    ('Everton', 'Tottenham'),
    ('Forest', 'Arsenal'),
    ('Forest', 'Aston Villa'),
    ('Forest', 'Bournemouth'),
    ('Forest', 'Brentford'),
    ('Forest', 'Brighton'),
    ('Forest', 'Chelsea'),
    ('Forest', 'Crystal Palace'),
    ('Forest', 'Everton'),
    ('Forest', 'Fulham'),
    ('Forest', 'Hull'),
    ('Forest', 'Ipswich'),
    ('Forest', 'Liverpool'),
    ('Forest', 'Man City'),
    ('Forest', 'Man United'),
    ('Forest', 'Sunderland'),
    ('Forest', 'Tottenham'),
    ('Fulham', 'Arsenal'),
    ('Fulham', 'Aston Villa'),
    ('Fulham', 'Bournemouth'),
    ('Fulham', 'Brentford'),
    ('Fulham', 'Brighton'),
    ('Fulham', 'Coventry'),
    ('Fulham', 'Crystal Palace'),
    ('Fulham', 'Everton'),
    ('Fulham', 'Forest'),
    ('Fulham', 'Ipswich'),
    ('Fulham', 'Liverpool'),
    ('Fulham', 'Man City'),
    ('Fulham', 'Newcastle'),
    ('Fulham', 'Sunderland'),
    ('Fulham', 'Tottenham'),
    ('Hull', 'Arsenal'),
    ('Hull', 'Aston Villa'),
    ('Hull', 'Bournemouth'),
    ('Hull', 'Brentford'),
    ('Hull', 'Brighton'),
    ('Hull', 'Chelsea'),
    ('Hull', 'Coventry'),
    ('Hull', 'Crystal Palace'),
    ('Hull', 'Forest'),
    ('Hull', 'Fulham'),
    ('Hull', 'Ipswich'),
    ('Hull', 'Leeds'),
    ('Hull', 'Liverpool'),
    ('Hull', 'Newcastle'),
    ('Hull', 'Sunderland'),
    ('Hull', 'Tottenham'),
    ('Ipswich', 'Arsenal'),
    ('Ipswich', 'Aston Villa'),
    ('Ipswich', 'Bournemouth'),
    ('Ipswich', 'Brentford'),
    ('Ipswich', 'Chelsea'),
    ('Ipswich', 'Coventry'),
    ('Ipswich', 'Crystal Palace'),
    ('Ipswich', 'Everton'),
    ('Ipswich', 'Forest'),
    ('Ipswich', 'Hull'),
    ('Ipswich', 'Leeds'),
    ('Ipswich', 'Liverpool'),
    ('Ipswich', 'Man City'),
    ('Ipswich', 'Man United'),
    ('Ipswich', 'Newcastle'),
    ('Ipswich', 'Tottenham'),
    ('Leeds', 'Arsenal'),
    ('Leeds', 'Aston Villa'),
    ('Leeds', 'Bournemouth'),
    ('Leeds', 'Brentford'),
    ('Leeds', 'Brighton'),
    ('Leeds', 'Chelsea'),
    ('Leeds', 'Coventry'),
    ('Leeds', 'Everton'),
    ('Leeds', 'Forest'),
    ('Leeds', 'Fulham'),
    ('Leeds', 'Ipswich'),
    ('Leeds', 'Liverpool'),
    ('Leeds', 'Man City'),
    ('Leeds', 'Sunderland'),
    ('Leeds', 'Tottenham'),
    ('Liverpool', 'Arsenal'),
    ('Liverpool', 'Bournemouth'),
    ('Liverpool', 'Brentford'),
    ('Liverpool', 'Brighton'),
    ('Liverpool', 'Chelsea'),
    ('Liverpool', 'Coventry'),
    ('Liverpool', 'Crystal Palace'),
    ('Liverpool', 'Everton'),
    ('Liverpool', 'Forest'),
    ('Liverpool', 'Hull'),
    ('Liverpool', 'Ipswich'),
    ('Liverpool', 'Leeds'),
    ('Liverpool', 'Man United'),
    ('Liverpool', 'Newcastle'),
    ('Liverpool', 'Sunderland'),
    ('Liverpool', 'Tottenham'),
    ('Man City', 'Arsenal'),
    ('Man City', 'Aston Villa'),
    ('Man City', 'Brentford'),
    ('Man City', 'Brighton'),
    ('Man City', 'Chelsea'),
    ('Man City', 'Coventry'),
    ('Man City', 'Crystal Palace'),
    ('Man City', 'Forest'),
    ('Man City', 'Fulham'),
    ('Man City', 'Hull'),
    ('Man City', 'Leeds'),
    ('Man City', 'Liverpool'),
    ('Man City', 'Man United'),
    ('Man City', 'Newcastle'),
    ('Man City', 'Tottenham'),
    ('Man United', 'Aston Villa'),
    ('Man United', 'Bournemouth'),
    ('Man United', 'Brentford'),
    ('Man United', 'Brighton'),
    ('Man United', 'Chelsea'),
    ('Man United', 'Coventry'),
    ('Man United', 'Crystal Palace'),
    ('Man United', 'Everton'),
    ('Man United', 'Forest'),
    ('Man United', 'Fulham'),
    ('Man United', 'Hull'),
    ('Man United', 'Ipswich'),
    ('Man United', 'Leeds'),
    ('Man United', 'Liverpool'),
    ('Man United', 'Newcastle'),
    ('Man United', 'Sunderland'),
    ('Newcastle', 'Arsenal'),
    ('Newcastle', 'Bournemouth'),
    ('Newcastle', 'Brighton'),
    ('Newcastle', 'Chelsea'),
    ('Newcastle', 'Coventry'),
    ('Newcastle', 'Crystal Palace'),
    ('Newcastle', 'Everton'),
    ('Newcastle', 'Forest'),
    ('Newcastle', 'Fulham'),
    ('Newcastle', 'Ipswich'),
    ('Newcastle', 'Leeds'),
    ('Newcastle', 'Man City'),
    ('Newcastle', 'Man United'),
    ('Newcastle', 'Sunderland'),
    ('Newcastle', 'Tottenham'),
    ('Sunderland', 'Aston Villa'),
    ('Sunderland', 'Bournemouth'),
    ('Sunderland', 'Brentford'),
    ('Sunderland', 'Chelsea'),
    ('Sunderland', 'Coventry'),
    ('Sunderland', 'Crystal Palace'),
    ('Sunderland', 'Everton'),
    ('Sunderland', 'Forest'),
    ('Sunderland', 'Fulham'),
    ('Sunderland', 'Hull'),
    ('Sunderland', 'Ipswich'),
    ('Sunderland', 'Leeds'),
    ('Sunderland', 'Liverpool'),
    ('Sunderland', 'Man City'),
    ('Sunderland', 'Newcastle'),
    ('Sunderland', 'Tottenham'),
    ('Tottenham', 'Bournemouth'),
    ('Tottenham', 'Brentford'),
    ('Tottenham', 'Brighton'),
    ('Tottenham', 'Chelsea'),
    ('Tottenham', 'Coventry'),
    ('Tottenham', 'Crystal Palace'),
    ('Tottenham', 'Forest'),
    ('Tottenham', 'Fulham'),
    ('Tottenham', 'Hull'),
    ('Tottenham', 'Ipswich'),
    ('Tottenham', 'Leeds'),
    ('Tottenham', 'Man City'),
    ('Tottenham', 'Man United'),
    ('Tottenham', 'Newcastle'),
    ('Tottenham', 'Sunderland')]


PL_BETTING_MARKETS = {
    "League Winner": {
        "Arsenal": (4, 5), "Man City": (5, 2), "Liverpool": (7, 1), "Chelsea": (10, 1),
        "Man United": (22, 1), "Tottenham": (50, 1), "Aston Villa": (80, 1), "Brighton": (50, 1),
        "Newcastle": (80, 1), "Bournemouth": (250, 1), "Brentford": (100, 1), "Everton": (125, 1),
        "Leeds": (200, 1), "Forest": (500, 1), "Crystal Palace": (500, 1), "Fulham": (400, 1),
        "Sunderland": (1000, 1), "Ipswich": (500, 1), "Hull": (250, 1), "Coventry": (2500, 1),
    },
    "Top 2 Finish": {
        "Arsenal": (1, 5), "Man City": (1, 2), "Liverpool": (9, 4), "Chelsea": (3, 1),
        "Man United": (7, 1), "Tottenham": (25, 1), "Aston Villa": (33, 1), "Brighton": (16, 1),
        "Newcastle": (28, 1), "Bournemouth": (100, 1), "Brentford": (25, 1), "Everton": (33, 1),
        "Leeds": (66, 1), "Forest": (150, 1), "Crystal Palace": (150, 1), "Fulham": (150, 1),
        "Hull": (40, 1), "Ipswich": (80, 1), "Sunderland": (200, 1), "Coventry": (1000, 1),
    },
    "Relegation": {
        "Coventry": (1, 2), "Sunderland": (2, 1), "Hull": (10, 3), "Ipswich": (5, 2),
        "Crystal Palace": (4, 1), "Forest": (9, 2), "Fulham": (5, 1), "Leeds": (7, 1),
        "Bournemouth": (8, 1), "Newcastle": (16, 1), "Brentford": (16, 1), "Everton": (14, 1),
        "Aston Villa": (16, 1), "Brighton": (50, 1), "Tottenham": (40, 1), "Chelsea": (100, 1),
        "Man United": (250, 1), "Liverpool": (500, 1), "Man City": (500, 1), "Arsenal": (1000, 1),
    },
}

ACTUAL_RESULTS: Dict[Tuple[str, str], Tuple[int, int]] = {
    ("Everton", "Crystal Palace"): (2, 0), ("Ipswich", "Sunderland"): (2, 1),
    ("Forest", "Leeds"): (0, 1), ("Brentford", "Tottenham"): (3, 0),
    ("Arsenal", "Coventry"): (3, 0), ("Hull", "Man United"): (2, 0),
    ("Brighton", "Aston Villa"): (4, 0), ("Man City", "Bournemouth"): (2, 1),
    ("Newcastle", "Liverpool"): (2, 2), ("Fulham", "Chelsea"): (2, 3),
}

LOCKED_SCORES: List[str] = []

TEAM_EUROPE_STATUS: Dict[str, str] = {}

# ==========================================
# PREMIER LEAGUE SIMULATION
# ==========================================


def _fractional_to_probability(odds_tuple: Tuple[int, int]) -> float:
    """Convert fractional odds to implied probability."""
    numerator, denominator = odds_tuple
    return denominator / (numerator + denominator)


def _probability_to_elo(prob: float, base_elo: float = LEAGUE_AVERAGE_ELO) -> float:
    """Convert win probability to Elo rating relative to base."""
    if prob <= 0 or prob >= 1:
        return base_elo
    elo_diff = -400 * math.log10((1 - prob) / prob)
    return base_elo + elo_diff


def markets_to_latent_elo() -> Dict[str, float]:
    """Derive base Elo ratings for PL teams from betting market odds."""
    teams = list(PL_BETTING_MARKETS["League Winner"].keys())
    MARKET_WEIGHTS = {"League Winner": 1.00, "Top 2 Finish": 0.55, "Relegation": 0.45}
    team_strength: Dict[str, float] = defaultdict(float)
    team_weight: Dict[str, float] = defaultdict(float)

    for market_name, market_weight in MARKET_WEIGHTS.items():
        odds_dict = PL_BETTING_MARKETS[market_name]
        raw_probs: List[float] = []
        teams_in_market: List[str] = []
        for team in teams:
            if team in odds_dict:
                num, den = odds_dict[team]
                prob = den / (num + den)
                raw_probs.append(prob)
                teams_in_market.append(team)
        if not raw_probs:
            continue
        raw_probs_arr = np.array(raw_probs, dtype=np.float64)
        total = raw_probs_arr.sum()
        if total > 0:
            probs = raw_probs_arr / total
        else:
            continue
        log_probs = np.log(np.clip(probs, 1e-6, 1.0 - 1e-6))
        mean_log_prob = np.mean(log_probs)
        centered = log_probs - mean_log_prob
        for i, team in enumerate(teams_in_market):
            team_strength[team] += market_weight * centered[i]
            team_weight[team] += market_weight

    raw_elo: Dict[str, float] = {}
    scale_factor = ELO_SCALE / math.log(10)
    for team in teams:
        if team_weight[team] > 0:
            latent = team_strength[team] / team_weight[team]
            elo = LEAGUE_AVERAGE_ELO + scale_factor * latent
        else:
            elo = LEAGUE_AVERAGE_ELO
        raw_elo[team] = elo

    mean_elo = np.mean(list(raw_elo.values()))
    centered_elo = {team: LEAGUE_AVERAGE_ELO + (elo - mean_elo) for team, elo in raw_elo.items()}
    ratings = {team: LEAGUE_AVERAGE_ELO + ELO_SHRINKAGE * (elo - LEAGUE_AVERAGE_ELO) for team, elo in centered_elo.items()}
    return {team: round(float(rating), 1) for team, rating in ratings.items()}


class TeamRegistry:
    """Maps team names to array indices for fast simulation."""

    __slots__ = ('elos', 'team_to_idx', 'idx_to_team')

    def __init__(self) -> None:
        self.elos: Dict[str, float] = {}
        self.team_to_idx: Dict[str, int] = {}
        self.idx_to_team: List[str] = []

    def add_team(self, name: str, elo: float) -> None:
        idx = len(self.idx_to_team)
        self.elos[name] = elo
        self.team_to_idx[name] = idx
        self.idx_to_team.append(name)


def _parse_locked_scores(fixtures: List[Tuple[str, str]], locked: List[str]) -> Dict[Tuple[str, str], Tuple[int, int]]:
    actual: Dict[Tuple[str, str], Tuple[int, int]] = {}
    for i, score_str in enumerate(locked):
        if i >= len(fixtures):
            break
        if not score_str.strip():
            continue
        h, a = score_str.split(',')
        actual[fixtures[i]] = (int(h.strip()), int(a.strip()))
    return actual


def run_single_pl_simulation(
    registry: TeamRegistry,
    fixture_indices: List[Tuple[int, int]],
    base_ratings: Dict[str, float],
    actual_results: Dict[Tuple[str, str], Tuple[int, int]],
) -> Tuple[Dict, List[Tuple[str, Dict]]]:
    """Simulate one Premier League season, return table and ranking."""
    n_teams = len(registry.idx_to_team)
    n_fixtures = len(fixture_indices)
    pts = np.zeros(n_teams, dtype=np.int64)
    gf = np.zeros(n_teams, dtype=np.int64)
    ga = np.zeros(n_teams, dtype=np.int64)

    adjusted_ratings: List[float] = []
    for i in range(n_teams):
        team_name = registry.idx_to_team[i]
        elo = base_ratings[team_name]
        if team_name in TEAM_EUROPE_STATUS:
            comp = TEAM_EUROPE_STATUS[team_name]
            penalty = EUROPEAN_PENALTIES.get(comp, 0)
            adjusted_ratings.append(elo - penalty)
        else:
            adjusted_ratings.append(elo)

    base_ratings_arr = np.array(adjusted_ratings, dtype=np.float64)

    actual_results_mask = np.zeros(n_fixtures, dtype=np.bool_)
    actual_results_home = np.zeros(n_fixtures, dtype=np.int64)
    actual_results_away = np.zeros(n_fixtures, dtype=np.int64)

    for i, (h_idx, a_idx) in enumerate(fixture_indices):
        h_name = registry.idx_to_team[h_idx]
        a_name = registry.idx_to_team[a_idx]
        fixture_key = (h_name, a_name)
        if fixture_key in actual_results:
            actual_results_mask[i] = True
            actual_results_home[i] = actual_results[fixture_key][0]
            actual_results_away[i] = actual_results[fixture_key][1]

    for i in range(n_fixtures):
        h_idx, a_idx = fixture_indices[i]

        if actual_results_mask[i]:
            hg = int(actual_results_home[i])
            ag = int(actual_results_away[i])
        else:
            h_elo = base_ratings_arr[h_idx] + HOME_ADVANTAGE_ELO
            a_elo = base_ratings_arr[a_idx]
            home_xg, away_xg = compute_expected_goals(h_elo, a_elo)
            hg, ag = sample_score(home_xg, away_xg)

        if hg > ag:
            hp, ap = 3, 0
        elif hg == ag:
            hp, ap = 1, 1
        else:
            hp, ap = 0, 3

        pts[h_idx] += hp
        pts[a_idx] += ap
        gf[h_idx] += hg
        ga[h_idx] += ag
        gf[a_idx] += ag
        ga[a_idx] += hg

    table = {
        registry.idx_to_team[i]: {
            "Pts": int(pts[i]),
            "GF": int(gf[i]),
            "GA": int(ga[i]),
            "GD": int(gf[i] - ga[i]),
        }
        for i in range(n_teams)
    }
    ranking = sorted(
        table.items(),
        key=lambda x: (x[1]["Pts"], x[1]["GD"], x[1]["GF"]),
        reverse=True,
    )
    return table, ranking


def run_premier_league_simulation(
    cl_win_probs: Dict[str, float],
    uel_win_probs: Dict[str, float],
) -> None:
    """Run the full Premier League simulation using CL/UEL qualification data."""
    print("\n" + "=" * 80)
    print("STEP 2: PREMIER LEAGUE SIMULATION")
    print("=" * 80)

    global TEAM_EUROPE_STATUS
    TEAM_EUROPE_STATUS = {}

    for team in PL_TEAMS:
        TEAM_EUROPE_STATUS[team] = "UCL"
    for team in PL_UEL_TEAMS:
        if team not in TEAM_EUROPE_STATUS:
            TEAM_EUROPE_STATUS[team] = "UEL"

    print("European Fatigue Status Updated:")
    for team, status in TEAM_EUROPE_STATUS.items():
        print(f"  {team}: {status}")

    SEED = 42
    if SEED is not None:
        random.seed(SEED)
        np.random.seed(SEED)

    print("\nConverting betting markets to latent strength ELO...")
    base_ratings = markets_to_latent_elo()

    registry = TeamRegistry()
    fixture_teams = {team for pair in FIXTURES_LIST for team in pair}
    missing = fixture_teams - set(base_ratings.keys())
    if missing:
        raise ValueError(f"Missing ELO ratings for teams in fixtures: {missing}")

    min_elo = min(base_ratings.values())
    PROMOTED_TEAMS = {"Ipswich", "Coventry", "Hull"}
    PROMOTED_PENALTY = 0

    for name in sorted(fixture_teams):
        elo = base_ratings[name]
        if name in PROMOTED_TEAMS:
            elo = min_elo - PROMOTED_PENALTY
        registry.add_team(name, elo)

    teams = list(registry.idx_to_team)
    fixture_indices = [
        (registry.team_to_idx[h], registry.team_to_idx[a]) for h, a in FIXTURES_LIST
    ]

    print(f"\nRunning {NUM_PL_SIMS} Premier League simulations...")

    points_dist: Dict[str, List[int]] = defaultdict(list)
    position_counts: Dict[str, Dict[int, int]] = defaultdict(lambda: defaultdict(int))
    title_counts: Dict[str, int] = defaultdict(int)
    probabilities = {k: defaultdict(float) for k in ["ucl", "europaleague", "tophalf", "stayup", "releg", "bottom"]}

    actual_results = {**ACTUAL_RESULTS, **_parse_locked_scores(FIXTURES_LIST, LOCKED_SCORES)}

    for _ in tqdm(range(NUM_PL_SIMS), desc="Simulating PL"):
        _, ranking = run_single_pl_simulation(registry, fixture_indices, base_ratings, actual_results)

        for pos, (team, data) in enumerate(ranking, 1):
            points_dist[team].append(data["Pts"])
            position_counts[team][pos] += 1
            if pos == 1:
                title_counts[team] += 1
            if pos <= 4:
                probabilities["ucl"][team] += 1
            if pos == 5:
                probabilities["europaleague"][team] += 1
            if pos <= 10:
                probabilities["tophalf"][team] += 1
            if pos <= 17:
                probabilities["stayup"][team] += 1
            if pos >= 18:
                probabilities["releg"][team] += 1
            if pos == 20:
                probabilities["bottom"][team] += 1

    print("\n" + "=" * 130)
    print("FINAL PREMIER LEAGUE PROJECTIONS (With CL Fatigue Adjustments)")
    print("=" * 130)

    avg_positions: Dict[str, float] = {}
    avg_points: Dict[str, float] = {}
    std_points: Dict[str, float] = {}

    for team in teams:
        position_total = sum(pos * count for pos, count in position_counts[team].items())
        avg_positions[team] = position_total / NUM_PL_SIMS
        pts_array = np.array(points_dist[team], dtype=np.float64)
        avg_points[team] = float(pts_array.mean())
        std_points[team] = float(pts_array.std())

    title_probability = {t: title_counts[t] / NUM_PL_SIMS * 100 for t in teams}
    for key in probabilities:
        probabilities[key] = {t: probabilities[key][t] / NUM_PL_SIMS * 100 for t in teams}

    print(
        f"{'Pos':<6}" f"{'Team':<22}" f"{'Eur':<6}" f"{'ELO':<8}" f"{'Pts':<8}" f"{'SD':<7}"
        f"{'Title':<8}" f"{'UCL':<8}" f"{'Europa':<9}" f"{'TopHalf':<9}" f"{'StayUp':<9}" f"{'Releg':<9}"
    )
    print("-" * 130)

    sorted_teams = sorted(teams, key=lambda team: avg_positions[team])

    for team in sorted_teams:
        eur_status = TEAM_EUROPE_STATUS.get(team, "-")
        probs_str = ""
        if team in cl_win_probs:
            ucl_qual_prob = probabilities["ucl"][team] / 100.0
            overall_cl_win = cl_win_probs[team] * ucl_qual_prob
            probs_str += f" (CL Win: {overall_cl_win:.1f}%)"
        if team in uel_win_probs:
            probs_str += f" (UEL Win: {uel_win_probs[team]:.1f}%)"

        print(
            f"{avg_positions[team]:<6.2f}" f"{team:<22}" f"{eur_status:<6}" f"{base_ratings[team]:<8.1f}"
            f"{avg_points[team]:<8.2f}" f"{std_points[team]:<7.2f}" f"{title_probability[team]:<8.2f}"
            f"{probabilities['ucl'][team]:<8.2f}" f"{probabilities['europaleague'][team]:<9.2f}"
            f"{probabilities['tophalf'][team]:<9.2f}" f"{probabilities['stayup'][team]:<9.2f}"
            f"{probabilities['releg'][team]:<9.2f}"
            + probs_str
        )


# ==========================================
# MAIN EXECUTION
# ==========================================

def main() -> None:
    random.seed(42)
    np.random.seed(42)

    cl_win_probs = run_champions_league_simulation()
    uel_win_probs = run_europa_league_simulation()
    run_premier_league_simulation(cl_win_probs, uel_win_probs)


if __name__ == "__main__":
    main()
