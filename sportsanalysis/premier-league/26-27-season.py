import random
import math
import csv
import os
from pathlib import Path
from collections import defaultdict
import numpy as np
from tqdm import tqdm
from typing import Dict, List, Tuple

# ==========================================
# CONSTANTS
# ==========================================
BASE_K = 20.0
GOAL_DIFF_EXPECTED = 1.4
HOME_ADVANTAGE_ELO = 50.0
ELO_SCALE = 400
NUM_TEAMS = 20
LEAGUE_AVERAGE_ELO = 1500.0
K_FACTOR = 15.0

DAMPENING_ENABLED = True
DAMPENING_FACTOR = 0.25

PROMOTED_TEAMS = {"Ipswich", "Coventry", "Hull"}

# ==========================================
# AUTO-CALCULATED ELO RATINGS FROM HISTORICAL CSV DATA
# ==========================================


def _load_historical_elos() -> Dict[str, float]:
    csv_dir = Path(__file__).resolve().parent
    matches = []
    name_map = {
        "Nott'm Forest": "Forest",
    }
    for csv_file in csv_dir.glob("*.csv"):
        with open(csv_file, newline="", encoding="utf-8-sig") as f:
            reader = csv.DictReader(f)
            for row in reader:
                if row.get("Div") == "E0":
                    try:
                        date = datetime.strptime(row["Date"], "%d/%m/%Y")
                    except ValueError:
                        continue
                    matches.append({
                        "date": date,
                        "home": name_map.get(row["HomeTeam"], row["HomeTeam"]),
                        "away": name_map.get(row["AwayTeam"], row["AwayTeam"]),
                        "home_goals": int(row["FTHG"]),
                        "away_goals": int(row["FTAG"]),
                    })

    matches.sort(key=lambda m: m["date"])
    teams: Dict[str, Dict] = defaultdict(lambda: {"elo": 1500.0, "played": 0})

    if matches:
        most_recent = max(m["date"] for m in matches)
        RECENCY_HALF_LIFE_DAYS = 365.0
        decay = math.log(2) / RECENCY_HALF_LIFE_DAYS
    else:
        most_recent = datetime.now()
        decay = 0.0

    fixture_teams = {t for pair in FIXTURES_LIST for t in pair}
    for m in matches:
        home = m["home"]
        away = m["away"]
        if home not in fixture_teams or away not in fixture_teams:
            continue

        hg = m["home_goals"]
        ag = m["away_goals"]

        if home not in teams:
            teams[home] = {"elo": 1500.0, "played": 0}
        if away not in teams:
            teams[away] = {"elo": 1500.0, "played": 0}

        teams[home]["played"] += 1
        teams[away]["played"] += 1

        old_home = teams[home]["elo"]
        old_away = teams[away]["elo"]
        p_home = 1 / (1 + 10 ** ((old_home + HOME_ADVANTAGE_ELO - old_away) / ELO_SCALE))

        if hg > ag:
            actual_home = 1.0
        elif hg == ag:
            actual_home = 0.5
        else:
            actual_home = 0.0

        goal_diff = abs(hg - ag)
        g_mult = math.log(goal_diff + 1) if goal_diff > 0 else 0
        days_ago = (most_recent - m["date"]).days
        recency_weight = math.exp(-decay * days_ago)
        k = BASE_K * (1 + g_mult / GOAL_DIFF_EXPECTED) * recency_weight

        teams[home]["elo"] = old_home + k * (actual_home - p_home)
        teams[away]["elo"] = old_away + k * ((1 - actual_home) - (1 - p_home))

    elos = {name: data["elo"] for name, data in teams.items()}
    avg_elo = np.mean(list(elos.values())) if elos else LEAGUE_AVERAGE_ELO
    for team in fixture_teams:
        elos.setdefault(team, avg_elo)
    return elos


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
# CORE FUNCTIONS
# ==========================================
def win_probability(home_elo, away_elo):
    diff = home_elo + HOME_ADVANTAGE_ELO - away_elo
    return 1 / (1 + 10 ** (-diff / ELO_SCALE))

def update_elo(home_elo, away_elo, result_home, k_factor=K_FACTOR):
    expected_home = win_probability(home_elo, away_elo)
    expected_away = 1 - expected_home
    new_home = home_elo + k_factor * (result_home - expected_home)
    new_away = away_elo + k_factor * ((1 - result_home) - expected_away)
    return new_home, new_away

def simulate_match(home_elo, away_elo):
    p_home = win_probability(home_elo, away_elo)
    r = random.random()
    if r < p_home:
        return 3, 0, 1.0
    elif r < p_home + 0.25:
        return 1, 1, 0.5
    else:
        return 0, 3, 0.0

# ==========================================
# FIXTURES (VALIDATED)
# ==========================================
FIXTURES_LIST = [
    ('Arsenal', 'Coventry'), ('Brentford', 'Tottenham'), ('Everton', 'Crystal Palace'), ('Hull', 'Man United'),
    ('Ipswich', 'Sunderland'), ('Forest', 'Leeds'), ('Brighton', 'Aston Villa'), ('Man City', 'Bournemouth'),
    ('Newcastle', 'Liverpool'), ('Fulham', 'Chelsea'), ('Bournemouth', 'Everton'), ('Aston Villa', 'Arsenal'),
    ('Chelsea', 'Brighton'), ('Coventry', 'Hull'), ('Crystal Palace', 'Man City'), ('Leeds', 'Brentford'),
    ('Liverpool', 'Forest'), ('Man United', 'Ipswich'), ('Sunderland', 'Fulham'), ('Tottenham', 'Newcastle'),
    ('Arsenal', 'Chelsea'), ('Brentford', 'Sunderland'), ('Brighton', 'Leeds'), ('Everton', 'Man United'),
    ('Fulham', 'Crystal Palace'), ('Hull', 'Aston Villa'), ('Ipswich', 'Liverpool'), ('Man City', 'Coventry'),
    ('Newcastle', 'Bournemouth'), ('Forest', 'Tottenham'), ('Bournemouth', 'Brentford'), ('Aston Villa', 'Forest'),
    ('Chelsea', 'Hull'), ('Coventry', 'Brighton'), ('Crystal Palace', 'Ipswich'), ('Leeds', 'Newcastle'),
    ('Liverpool', 'Fulham'), ('Man United', 'Man City'), ('Sunderland', 'Arsenal'), ('Tottenham', 'Everton'),
    ('Bournemouth', 'Liverpool'), ('Brentford', 'Chelsea'), ('Brighton', 'Arsenal'), ('Everton', 'Ipswich'),
    ('Fulham', 'Man United'), ('Leeds', 'Crystal Palace'), ('Man City', 'Sunderland'), ('Newcastle', 'Hull'),
    ('Forest', 'Coventry'), ('Tottenham', 'Aston Villa'), ('Arsenal', 'Leeds'), ('Aston Villa', 'Brentford'),
    ('Chelsea', 'Bournemouth'), ('Coventry', 'Newcastle'), ('Crystal Palace', 'Forest'), ('Hull', 'Everton'),
    ('Ipswich', 'Fulham'), ('Liverpool', 'Man City'), ('Man United', 'Tottenham'), ('Sunderland', 'Brighton'),
    ('Bournemouth', 'Sunderland'), ('Brentford', 'Liverpool'), ('Brighton', 'Crystal Palace'), ('Everton', 'Chelsea'),
    ('Fulham', 'Hull'), ('Leeds', 'Man United'), ('Man City', 'Ipswich'), ('Newcastle', 'Aston Villa'),
    ('Forest', 'Arsenal'), ('Tottenham', 'Coventry'), ('Chelsea', 'Tottenham'), ('Coventry', 'Fulham'),
    ('Crystal Palace', 'Newcastle'), ('Hull', 'Brentford'), ('Ipswich', 'Forest'), ('Liverpool', 'Brighton'),
    ('Man United', 'Bournemouth'), ('Sunderland', 'Leeds'), ('Bournemouth', 'Leeds'), ('Aston Villa', 'Fulham'),
    ('Brentford', 'Forest'), ('Chelsea', 'Man United'), ('Coventry', 'Sunderland'), ('Hull', 'Ipswich'),
    ('Liverpool', 'Arsenal'), ('Man City', 'Brighton'), ('Newcastle', 'Everton'), ('Tottenham', 'Crystal Palace'),
    ('Arsenal', 'Hull'), ('Brighton', 'Brentford'), ('Crystal Palace', 'Liverpool'), ('Everton', 'Coventry'),
    ('Aston Villa', 'Man City'), ('Ipswich', 'Bournemouth'), ('Leeds', 'Chelsea'), ('Man United', 'Liverpool'),
    ('Forest', 'Man City'), ('Sunderland', 'Chelsea'), ('Bournemouth', 'Forest'), ('Aston Villa', 'Sunderland'),
    ('Brentford', 'Everton'), ('Chelsea', 'Leeds'), ('Coventry', 'Crystal Palace'), ('Hull', 'Brighton'),
    ('Liverpool', 'Man United'), ('Man City', 'Fulham'), ('Newcastle', 'Arsenal'), ('Tottenham', 'Ipswich'),
    ('Arsenal', 'Man City'), ('Brighton', 'Newcastle'), ('Crystal Palace', 'Hull'), ('Everton', 'Liverpool'),
    ('Fulham', 'Bournemouth'), ('Ipswich', 'Aston Villa'), ('Leeds', 'Coventry'), ('Man United', 'Brentford'),
    ('Forest', 'Chelsea'), ('Sunderland', 'Tottenham'), ('Bournemouth', 'Brighton'), ('Aston Villa', 'Everton'),
    ('Brentford', 'Arsenal'), ('Chelsea', 'Crystal Palace'), ('Coventry', 'Ipswich'), ('Hull', 'Forest'),
    ('Liverpool', 'Sunderland'), ('Man City', 'Leeds'), ('Newcastle', 'Man United'), ('Tottenham', 'Fulham'),
    ('Bournemouth', 'Hull'), ('Aston Villa', 'Crystal Palace'), ('Brentford', 'Man City'), ('Chelsea', 'Liverpool'),
    ('Everton', 'Fulham'), ('Leeds', 'Ipswich'), ('Man United', 'Coventry'), ('Newcastle', 'Sunderland'),
    ('Forest', 'Brighton'), ('Tottenham', 'Arsenal'), ('Arsenal', 'Bournemouth'), ('Brighton', 'Everton'),
    ('Coventry', 'Aston Villa'), ('Crystal Palace', 'Man United'), ('Fulham', 'Brentford'), ('Hull', 'Tottenham'),
    ('Ipswich', 'Newcastle'), ('Liverpool', 'Leeds'), ('Man City', 'Chelsea'), ('Sunderland', 'Forest'),
    ('Bournemouth', 'Coventry'), ('Arsenal', 'Man United'), ('Brentford', 'Newcastle'), ('Brighton', 'Ipswich'),
    ('Chelsea', 'Aston Villa'), ('Leeds', 'Fulham'), ('Liverpool', 'Tottenham'), ('Man City', 'Hull'),
    ('Forest', 'Everton'), ('Sunderland', 'Crystal Palace'), ('Aston Villa', 'Leeds'), ('Coventry', 'Chelsea'),
    ('Crystal Palace', 'Arsenal'), ('Everton', 'Sunderland'), ('Fulham', 'Brighton'), ('Hull', 'Liverpool'),
    ('Ipswich', 'Brentford'), ('Man United', 'Forest'), ('Newcastle', 'Man City'), ('Tottenham', 'Bournemouth'),
    ('Aston Villa', 'Liverpool'), ('Coventry', 'Brentford'), ('Crystal Palace', 'Bournemouth'), ('Everton', 'Man City'),
    ('Fulham', 'Arsenal'), ('Hull', 'Leeds'), ('Ipswich', 'Chelsea'), ('Man United', 'Sunderland'),
    ('Newcastle', 'Forest'), ('Tottenham', 'Brighton'), ('Bournemouth', 'Aston Villa'), ('Arsenal', 'Ipswich'),
    ('Brentford', 'Crystal Palace'), ('Brighton', 'Man United'), ('Chelsea', 'Newcastle'), ('Leeds', 'Everton'),
    ('Liverpool', 'Coventry'), ('Man City', 'Tottenham'), ('Forest', 'Fulham'), ('Sunderland', 'Hull'),
    ('Bournemouth', 'Fulham'), ('Aston Villa', 'Man United'), ('Brentford', 'Man United'), ('Chelsea', 'Forest'),
    ('Coventry', 'Leeds'), ('Hull', 'Crystal Palace'), ('Liverpool', 'Everton'), ('Man City', 'Arsenal'),
    ('Newcastle', 'Brighton'), ('Tottenham', 'Leeds'), ('Arsenal', 'Newcastle'), ('Brighton', 'Man City'),
    ('Crystal Palace', 'Tottenham'), ('Everton', 'Brentford'), ('Fulham', 'Aston Villa'), ('Ipswich', 'Coventry'),
    ('Leeds', 'Man City'), ('Man United', 'Newcastle'), ('Forest', 'Hull'), ('Sunderland', 'Liverpool'),
    ('Bournemouth', 'Ipswich'), ('Man United', 'Aston Villa'), ('Brentford', 'Brighton'), ('Chelsea', 'Sunderland'),
    ('Coventry', 'Everton'), ('Hull', 'Arsenal'), ('Liverpool', 'Crystal Palace'), ('Man City', 'Forest'),
    ('Newcastle', 'Fulham'), ('Leeds', 'Tottenham'), ('Arsenal', 'Liverpool'), ('Brighton', 'Hull'),
    ('Crystal Palace', 'Coventry'), ('Everton', 'Newcastle'), ('Fulham', 'Man City'), ('Ipswich', 'Tottenham'),
    ('Leeds', 'Bournemouth'), ('Man United', 'Chelsea'), ('Forest', 'Brentford'), ('Sunderland', 'Aston Villa'),
    ('Aston Villa', 'Bournemouth'), ('Coventry', 'Liverpool'), ('Crystal Palace', 'Brentford'), ('Everton', 'Leeds'),
    ('Fulham', 'Forest'), ('Hull', 'Sunderland'), ('Ipswich', 'Arsenal'), ('Man United', 'Brighton'),
    ('Newcastle', 'Chelsea'), ('Tottenham', 'Man City'), ('Bournemouth', 'Crystal Palace'), ('Arsenal', 'Fulham'),
    ('Brentford', 'Coventry'), ('Brighton', 'Tottenham'), ('Chelsea', 'Ipswich'), ('Leeds', 'Aston Villa'),
    ('Liverpool', 'Hull'), ('Man City', 'Newcastle'), ('Forest', 'Man United'), ('Sunderland', 'Everton'),
    ('Aston Villa', 'Chelsea'), ('Coventry', 'Bournemouth'), ('Crystal Palace', 'Sunderland'), ('Everton', 'Forest'),
    ('Fulham', 'Leeds'), ('Hull', 'Man City'), ('Ipswich', 'Brighton'), ('Man United', 'Arsenal'),
    ('Newcastle', 'Brentford'), ('Tottenham', 'Liverpool'), ('Bournemouth', 'Tottenham'), ('Arsenal', 'Crystal Palace'),
    ('Brentford', 'Ipswich'), ('Brighton', 'Fulham'), ('Chelsea', 'Coventry'), ('Leeds', 'Hull'),
    ('Liverpool', 'Aston Villa'), ('Man City', 'Everton'), ('Forest', 'Newcastle'), ('Sunderland', 'Man United'),
    ('Bournemouth', 'Newcastle'), ('Aston Villa', 'Hull'), ('Chelsea', 'Arsenal'), ('Coventry', 'Man City'),
    ('Crystal Palace', 'Fulham'), ('Leeds', 'Brighton'), ('Liverpool', 'Ipswich'), ('Man United', 'Everton'),
    ('Sunderland', 'Brentford'), ('Tottenham', 'Forest'), ('Arsenal', 'Sunderland'), ('Brentford', 'Bournemouth'),
    ('Brighton', 'Coventry'), ('Everton', 'Tottenham'), ('Fulham', 'Liverpool'), ('Hull', 'Chelsea'),
    ('Ipswich', 'Crystal Palace'), ('Man City', 'Man United'), ('Newcastle', 'Leeds'), ('Forest', 'Aston Villa'),
    ('Bournemouth', 'Man City'), ('Aston Villa', 'Brighton'), ('Chelsea', 'Fulham'), ('Coventry', 'Arsenal'),
    ('Crystal Palace', 'Everton'), ('Leeds', 'Forest'), ('Liverpool', 'Newcastle'), ('Man United', 'Hull'),
    ('Sunderland', 'Ipswich'), ('Tottenham', 'Brentford'), ('Arsenal', 'Aston Villa'), ('Brentford', 'Leeds'),
    ('Brighton', 'Chelsea'), ('Everton', 'Bournemouth'), ('Fulham', 'Sunderland'), ('Hull', 'Coventry'),
    ('Ipswich', 'Man United'), ('Man City', 'Crystal Palace'), ('Newcastle', 'Tottenham'), ('Forest', 'Liverpool'),
    ('Bournemouth', 'Arsenal'), ('Aston Villa', 'Coventry'), ('Brentford', 'Fulham'), ('Chelsea', 'Man City'),
    ('Everton', 'Brighton'), ('Leeds', 'Liverpool'), ('Man United', 'Crystal Palace'), ('Newcastle', 'Ipswich'),
    ('Forest', 'Sunderland'), ('Tottenham', 'Hull'), ('Arsenal', 'Tottenham'), ('Brighton', 'Forest'),
    ('Coventry', 'Man United'), ('Crystal Palace', 'Aston Villa'), ('Fulham', 'Everton'), ('Hull', 'Bournemouth'),
    ('Ipswich', 'Leeds'), ('Liverpool', 'Chelsea'), ('Man City', 'Brentford'), ('Sunderland', 'Newcastle'),
    ('Bournemouth', 'Man United'), ('Brentford', 'Aston Villa'), ('Brighton', 'Sunderland'), ('Everton', 'Hull'),
    ('Fulham', 'Ipswich'), ('Leeds', 'Arsenal'), ('Man City', 'Liverpool'), ('Newcastle', 'Coventry'),
    ('Forest', 'Crystal Palace'), ('Tottenham', 'Chelsea'), ('Arsenal', 'Forest'), ('Aston Villa', 'Newcastle'),
    ('Chelsea', 'Everton'), ('Coventry', 'Tottenham'), ('Crystal Palace', 'Brighton'), ('Hull', 'Fulham'),
    ('Ipswich', 'Man City'), ('Liverpool', 'Brentford'), ('Man United', 'Leeds'), ('Sunderland', 'Bournemouth'),
    ('Bournemouth', 'Chelsea'), ('Brentford', 'Hull'), ('Brighton', 'Liverpool'), ('Everton', 'Arsenal'),
    ('Fulham', 'Coventry'), ('Leeds', 'Sunderland'), ('Man City', 'Aston Villa'), ('Newcastle', 'Crystal Palace'),
    ('Forest', 'Ipswich'), ('Tottenham', 'Man United'), ('Arsenal', 'Brighton'), ('Aston Villa', 'Tottenham'),
    ('Chelsea', 'Brentford'), ('Coventry', 'Forest'), ('Crystal Palace', 'Leeds'), ('Hull', 'Newcastle'),
    ('Ipswich', 'Everton'), ('Liverpool', 'Bournemouth'), ('Man United', 'Fulham'), ('Sunderland', 'Man City'),
    ('Sunderland', 'Coventry'), ('Ipswich', 'Hull'), ('Forest', 'Bournemouth'), ('Aston Villa', 'Ipswich'),
    ('Tottenham', 'Sunderland'), ('Brighton', 'Bournemouth'), ('Everton', 'Aston Villa'), ('Arsenal', 'Brentford'),
    ('Crystal Palace', 'Chelsea'), ('Fulham', 'Tottenham'), ('Fulham', 'Newcastle'), ('Arsenal', 'Everton')
]

from datetime import datetime

EXTERNAL_ELOS = _load_historical_elos()

# ==========================================
# BETTING MARKET DATA
# ==========================================
BETTING_MARKETS = {
    "League Winner": {
        "Arsenal": (6, 4), "Man City": (11, 4), "Liverpool": (11, 2),
        "Man United": (7, 1), "Chelsea": (8, 1), "Tottenham": (20, 1),
        "Aston Villa": (33, 1), "Brighton": (150, 1), "Newcastle": (150, 1),
        "Bournemouth": (200, 1), "Everton": (250, 1), "Brentford": (250, 1),
        "Sunderland": (500, 1), "Leeds": (500, 1), "Fulham": (500, 1),
        "Forest": (500, 1), "Crystal Palace": (500, 1), "Ipswich": (1000, 1),
        "Coventry": (1000, 1), "Hull": (1000, 1),
    },
    "Top 4 Finish": {
        "Arsenal": (1, 9), "Man City": (2, 7), "Liverpool": (8, 15),
        "Man United": (4, 7), "Chelsea": (10, 11), "Tottenham": (7, 2),
        "Aston Villa": (4, 1), "Newcastle": (9, 1), "Brighton": (12, 1),
        "Bournemouth": (20, 1), "Everton": (20, 1), "Brentford": (25, 1),
        "Forest": (25, 1), "Crystal Palace": (33, 1), "Fulham": (33, 1),
        "Leeds": (33, 1), "Sunderland": (50, 1), "Ipswich": (150, 1),
        "Coventry": (200, 1), "Hull": (400, 1),
    },
    "Top 2 Finish": {
        "Arsenal": (8, 15), "Man City": (6, 5), "Liverpool": (2, 1),
        "Man United": (5, 2), "Chelsea": (10, 3), "Tottenham": (9, 1),
        "Aston Villa": (11, 1), "Brighton": (22, 1), "Newcastle": (25, 1),
        "Bournemouth": (33, 1), "Everton": (33, 1), "Brentford": (40, 1),
        "Fulham": (80, 1), "Leeds": (80, 1), "Crystal Palace": (80, 1),
        "Sunderland": (80, 1), "Forest": (80, 1), "Hull": (150, 1),
        "Coventry": (150, 1), "Ipswich": (150, 1),
    },
    "To Finish Bottom": {
        "Hull": (11, 8), "Coventry": (11, 4), "Ipswich": (3, 1),
        "Sunderland": (18, 1), "Man City": (22, 1), "Fulham": (22, 1),
        "Leeds": (25, 1), "Crystal Palace": (28, 1), "Forest": (33, 1),
        "Brentford": (33, 1), "Everton": (40, 1), "Bournemouth": (40, 1),
        "Newcastle": (40, 1), "Brighton": (66, 1), "Tottenham": (80, 1),
        "Aston Villa": (100, 1), "Chelsea": (100, 1), "Arsenal": (150, 1),
        "Liverpool": (150, 1), "Man United": (150, 1),
    },
    "Relegation": {
        "Hull": (1, 3), "Coventry": (1, 2), "Ipswich": (1, 2),
        "Sunderland": (1, 4), "Leeds": (1, 5), "Fulham": (1, 8),
        "Crystal Palace": (1, 10), "Brentford": (1, 10), "Forest": (1, 10),
        "Bournemouth": (1, 12), "Everton": (1, 12), "Brighton": (1, 50),
        "Newcastle": (1, 50), "Tottenham": (1, 100), "Aston Villa": (1, 100),
        "Chelsea": (1, 200), "Man United": (1, 500), "Liverpool": (1000, 1),
        "Man City": (1000, 1), "Arsenal": (10000, 1),
    },
    "Top 6": {
        "Arsenal": (1, 33), "Man City": (1, 10), "Liverpool": (1, 6),
        "Man United": (2, 9), "Chelsea": (1, 3), "Tottenham": (1, 1),
        "Aston Villa": (11, 10), "Brighton": (7, 2), "Newcastle": (7, 2),
        "Bournemouth": (6, 1), "Brentford": (7, 1), "Everton": (7, 1),
        "Forest": (7, 1), "Crystal Palace": (9, 1), "Leeds": (9, 1),
        "Fulham": (12, 1), "Sunderland": (16, 1), "Coventry": (66, 1),
        "Ipswich": (66, 1), "Hull": (100, 1),
    },
    "Top Half": {
        "Arsenal": (1, 200), "Man City": (1, 200), "Liverpool": (1, 100),
        "Man United": (1, 50), "Chelsea": (1, 20), "Aston Villa": (1, 6),
        "Tottenham": (1, 6), "Newcastle": (4, 9), "Brighton": (1, 2),
        "Bournemouth": (6, 5), "Everton": (6, 4), "Brentford": (33, 20),
        "Forest": (15, 8), "Crystal Palace": (2,1),
        "Leeds": (9, 4), "Fulham": (7, 2), "Sunderland": (4, 1),
        "Coventry": (12, 1), "Ipswich": (14, 1), "Hull": (33, 1),
    },
}

# Auto-generate "To Stay Up" as the inverse of "Relegation"
BETTING_MARKETS["To Stay Up"] = {team: (den, num) for team, (num, den) in BETTING_MARKETS["Relegation"].items()}

POLYMARKET_TITLE = {
    "Arsenal": 37.0,
    "Man City": 24.0,
    "Chelsea": 14.0,
    "Liverpool": 13.0,
    "Man United": 12.0,
    "Tottenham": 5.0,
    "Aston Villa": 3.0,
    "Bournemouth": 1.0,
    "Brentford": 1.0,
    "Brighton": 1.0,
    "Coventry": 1.0,
    "Crystal Palace": 1.0,
    "Everton": 1.0,
    "Fulham": 1.0,
    "Hull": 1.0,
    "Ipswich": 1.0,
    "Leeds": 1.0,
    "Newcastle": 1.0,
    "Forest": 1.0,
    "Sunderland": 1.0,
}

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
        team: sim_weight * sim_pcts.get(team, 0.0) + (1 - sim_weight) * implied_pcts.get(team, 0.0)
        for team in sim_pcts
    }

# ==========================================
# DOMESTIC SIMULATION
# ==========================================
def run_single_simulation(registry, fixtures, initial_elos):
    team_names = registry.idx_to_team
    n_teams = len(team_names)
    elos = initial_elos.copy()
    pts = np.zeros(n_teams, dtype=np.int64)
    gf = np.zeros(n_teams, dtype=np.int64)
    ga = np.zeros(n_teams, dtype=np.int64)

    for home_name, away_name in fixtures:
        h_idx = registry.team_to_idx[home_name]
        a_idx = registry.team_to_idx[away_name]

        home_pts, away_pts, result = simulate_match(elos[h_idx], elos[a_idx])
        elos[h_idx], elos[a_idx] = update_elo(elos[h_idx], elos[a_idx], result)

        gf[h_idx] += home_pts if home_pts > away_pts else (1 if home_pts == away_pts else 0)
        ga[h_idx] += away_pts if away_pts > home_pts else (1 if home_pts == away_pts else 0)
        gf[a_idx] += away_pts if away_pts > home_pts else (1 if home_pts == away_pts else 0)
        ga[a_idx] += home_pts if home_pts > away_pts else (1 if home_pts == away_pts else 0)

        pts[h_idx] += home_pts
        pts[a_idx] += away_pts

    table = {name: {"Pts": int(pts[i]), "GF": int(gf[i]), "GA": int(ga[i])} for i, name in enumerate(team_names)}
    ranking = sorted(table.items(), key=lambda x: (x[1]["Pts"], x[1]["GF"] - x[1]["GA"], x[1]["GF"]), reverse=True)
    return table, ranking, elos

# ==========================================
# MAIN EXECUTION
# ==========================================
def main():
    registry = TeamRegistry()
    fixture_teams = {t for pair in FIXTURES_LIST for t in pair}
    min_elo = min(EXTERNAL_ELOS[name] for name in fixture_teams)
    for name, elo in EXTERNAL_ELOS.items():
        if name in PROMOTED_TEAMS:
            registry.add_team(name, min_elo - 75.0)
        else:
            registry.add_team(name, elo)

    team_names = registry.idx_to_team
    teams = list(team_names)
    initial_elos = np.array([registry.elos[name] for name in team_names], dtype=np.float64)
    initial_elos = 0.68 * initial_elos + 0.32 * LEAGUE_AVERAGE_ELO
    if DAMPENING_ENABLED:
        mean_elo = np.mean(initial_elos)
        initial_elos = initial_elos - DAMPENING_FACTOR * (initial_elos - mean_elo)

    NUM_SIMS = 2500
    print("\n" + "=" * 80)
    print(f"RUNNING PREMIER LEAGUE SIMULATIONS | Sims: {NUM_SIMS}")
    print("=" * 80)

    # Pre-compute implied probabilities for blending
    imp_title = implied_probabilities({t: BETTING_MARKETS["League Winner"].get(t, (1000, 1)) for t in teams}, normalize=True)
    imp_ucl = implied_probabilities({t: BETTING_MARKETS["Top 4 Finish"].get(t, (1000, 1)) for t in teams}, normalize=False)
    imp_europaleague = implied_probabilities({t: BETTING_MARKETS["Top 6"].get(t, (1000, 1)) for t in teams}, normalize=False)
    imp_tophalf = implied_probabilities({t: BETTING_MARKETS["Top Half"].get(t, (1000, 1)) for t in teams}, normalize=False)
    imp_stayup = implied_probabilities({t: BETTING_MARKETS["To Stay Up"].get(t, (1000, 1)) for t in teams}, normalize=False)
    imp_releg = implied_probabilities({t: BETTING_MARKETS["Relegation"].get(t, (1000, 1)) for t in teams}, normalize=False)
    imp_bottom = implied_probabilities({t: BETTING_MARKETS["To Finish Bottom"].get(t, (1000, 1)) for t in teams}, normalize=False)

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
        table, ranking, _ = run_single_simulation(registry, FIXTURES_LIST, initial_elos)
        teams_in_order = [t[0] for t in ranking]

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

    pure_sim_title = {t: title_counts[t] / NUM_SIMS * 100 for t in teams}
    combined_title = {t: (pure_sim_title[t] + imp_title[t] + poly_title[t]) / 3 for t in teams}
    total_title = sum(combined_title.values())
    if total_title > 0:
        combined_title = {t: (v / total_title) * 100 for t, v in combined_title.items()}
    combined_ucl = {t: per_sim_blended["ucl"][t] / NUM_SIMS for t in teams}
    combined_europaleague = {t: per_sim_blended["europaleague"][t] / NUM_SIMS for t in teams}
    combined_tophalf = {t: per_sim_blended["tophalf"][t] / NUM_SIMS for t in teams}
    combined_stayup = {t: per_sim_blended["stayup"][t] / NUM_SIMS for t in teams}
    combined_releg = {t: per_sim_blended["releg"][t] / NUM_SIMS for t in teams}
    combined_bottom = {t: per_sim_blended["bottom"][t] / NUM_SIMS for t in teams}

    print("\n" + "=" * 80)
    print("TEAM STATISTICS (2500 Sims | Blended)")
    print("=" * 80)
    print(f"{'Team':<15} {'AvgPts':<8} {'StdDev':<8} {'Title%':<8} {'UCL%':<8} {'EuropaLeague%':<13} {'TotalEurope%':<13} {'TopHalf%':<10} {'StayUp%':<9} {'Releg%':<8} {'Bottom%':<8}")
    print("-" * 118)

    team_avgs = {team: sum(points_dist[team]) / len(points_dist[team]) for team in teams}
    for team in sorted(teams, key=lambda t: team_avgs[t], reverse=True):
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
            stats_solved.setdefault("EuropaLeague", []).append(combined_europaleague[team] / 100.0)
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
