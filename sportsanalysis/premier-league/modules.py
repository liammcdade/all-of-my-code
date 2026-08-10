import csv
import math
from collections import defaultdict
from datetime import datetime
from pathlib import Path
from typing import Dict, Tuple

import numpy as np



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

BETTING_MARKETS = {
    "League Winner": {
        "Arsenal": (6, 4), "Man City": (11, 4), "Liverpool": (11, 2),
        "Man United": (15, 2), "Chelsea": (17, 2), "Tottenham": (22, 1),
        "Aston Villa": (40, 1), "Brighton": (175, 1), "Newcastle": (150, 1),
        "Bournemouth": (200, 1), "Everton": (250, 1), "Brentford": (250, 1),
        "Sunderland": (500, 1), "Leeds": (500, 1), "Fulham": (500, 1),
        "Forest": (500, 1), "Crystal Palace": (500, 1), "Ipswich": (1000, 1),
        "Coventry": (1000, 1), "Hull": (1000, 1),
    },
    "Top 2 Finish": {
        "Arsenal": (1, 2), "Man City": (6, 5), "Liverpool": (15, 8),
        "Man United": (5, 2), "Chelsea": (10, 3), "Tottenham": (9, 1),
        "Aston Villa": (11, 1), "Brighton": (25, 1), "Newcastle": (28, 1),
        "Bournemouth": (40, 1), "Everton": (40, 1), "Brentford": (50, 1),
        "Fulham": (80, 1), "Leeds": (80, 1), "Crystal Palace": (80, 1),
        "Sunderland": (80, 1), "Forest": (80, 1), "Hull": (150, 1),
        "Coventry": (150, 1), "Ipswich": (150, 1),
    },
    "Top 4 Finish": {
        "Arsenal": (1, 20), "Man City": (2, 9), "Liverpool": (4, 9),
        "Man United": (8, 13), "Chelsea": (5, 6), "Tottenham": (10, 3),
        "Aston Villa": (9, 2), "Brighton": (12, 1), "Newcastle": (14, 1),
        "Bournemouth": (20, 1), "Everton": (20, 1), "Brentford": (25, 1),
        "Leeds": (28, 1), "Forest": (28, 1), "Fulham": (33, 1),
        "Crystal Palace": (33, 1), "Sunderland": (40, 1), "Coventry": (80, 1),
        "Ipswich": (80, 1), "Hull": (150, 1),
    },
    "Top 5 Finish": {
        "Arsenal": (1, 25), "Man City": (1, 6), "Liverpool": (1, 4),
        "Man United": (3, 10), "Chelsea": (4, 7), "Tottenham": (15, 8),
        "Aston Villa": (9, 4), "Brighton": (6, 1), "Newcastle": (6, 1),
        "Bournemouth": (17, 2), "Everton": (9, 1), "Brentford": (10, 1),
        "Forest": (12, 1), "Leeds": (14, 1), "Crystal Palace": (14, 1),
        "Fulham": (16, 1), "Sunderland": (20, 1), "Coventry": (66, 1),
        "Ipswich": (66, 1), "Hull": (80, 1),
    },
    "Top 6 Finish": {
        "Arsenal": (1, 100), "Man City": (1, 14), "Liverpool": (1, 8),
        "Man United": (1, 5), "Chelsea": (2, 7), "Tottenham": (1, 1),
        "Aston Villa": (11, 8), "Brighton": (4, 1), "Newcastle": (9, 2),
        "Bournemouth": (13, 2), "Everton": (7, 1), "Brentford": (15, 2),
        "Forest": (8, 1), "Leeds": (9, 1), "Crystal Palace": (10, 1),
        "Fulham": (11, 1), "Sunderland": (14, 1), "Coventry": (50, 1),
        "Ipswich": (50, 1), "Hull": (66, 1),
    },
    "Top Half Finish": {
        "Arsenal": (1, 1000), "Man City": (1, 500), "Liverpool": (1, 1000),
        "Man United": (1, 500), "Chelsea": (1, 80), "Tottenham": (1, 7),
        "Aston Villa": (1, 5), "Brighton": (4, 7), "Newcastle": (10, 11),
        "Bournemouth": (5, 4), "Everton": (11, 8), "Brentford": (6, 4),
        "Forest": (7, 4), "Leeds": (9, 4), "Crystal Palace": (5, 2),
        "Fulham": (3, 1), "Sunderland": (4, 1), "Ipswich": (14, 1),
        "Coventry": (14, 1), "Hull": (28, 1),
    },
    "Relegation": {
        "Arsenal": (150, 1), "Man City": (10, 1), "Liverpool": (150, 1),
        "Man United": (150, 1), "Chelsea": (66, 1), "Tottenham": (33, 1),
        "Aston Villa": (40, 1), "Brighton": (20, 1), "Newcastle": (17, 2),
        "Bournemouth": (9, 1), "Everton": (9, 1), "Brentford": (8, 1),
        "Forest": (8, 1), "Leeds": (6, 1), "Crystal Palace": (6, 1),
        "Fulham": (5, 1), "Sunderland": (3, 1), "Ipswich": (4, 6),
        "Coventry": (4, 6), "Hull": (1, 7),
    },
    "To Finish Bottom": {
        "Arsenal": (150, 1), "Man City": (22, 1), "Liverpool": (150, 1),
        "Man United": (150, 1), "Chelsea": (150, 1), "Tottenham": (80, 1),
        "Aston Villa": (100, 1), "Brighton": (66, 1), "Newcastle": (40, 1),
        "Bournemouth": (40, 1), "Everton": (40, 1), "Brentford": (33, 1),
        "Forest": (33, 1), "Leeds": (25, 1), "Crystal Palace": (28, 1),
        "Fulham": (40, 1), "Sunderland": (18, 1), "Ipswich": (3, 1),
        "Coventry": (3, 1), "Hull": (11, 10),
    },
    "Avoid Relegation": {
        "Arsenal": (1, 1000), "Man City": (1, 33), "Liverpool": (1, 1000),
        "Man United": (1, 1000), "Chelsea": (1, 1000), "Tottenham": (1, 1000),
        "Aston Villa": (1, 1000), "Brighton": (1, 500), "Newcastle": (1, 25),
        "Bournemouth": (1, 25), "Everton": (1, 25), "Brentford": (1, 25),
        "Forest": (1, 25), "Leeds": (1, 16), "Crystal Palace": (1, 16),
        "Fulham": (1, 12), "Sunderland": (1, 6), "Ipswich": (1, 1),
        "Coventry": (11, 10), "Hull": (7, 2),
    },
}

def _load_historical_data() -> Tuple[Dict[str, float], Dict[str, Dict[str, float]]]:
    """
    Loads historical CSV match data and returns:
      1. initial ELO ratings
      2. wdl_rates for OptimizedELORatingSystem.predict_score()
    """
    try:
        csv_dir = Path(__file__).resolve().parent
    except NameError:
        csv_dir = Path.cwd()

    matches = []
    name_map = {
        "Nott'm Forest": "Forest",
    }

    for csv_file in csv_dir.glob("*.csv"):
        with open(csv_file, newline="", encoding="utf-8-sig") as f:
            reader = csv.DictReader(f)
            for row in reader:
                if row.get("Div") != "E0":
                    continue

                try:
                    date = datetime.strptime(row["Date"], "%d/%m/%Y")
                    home = name_map.get(row["HomeTeam"], row["HomeTeam"])
                    away = name_map.get(row["AwayTeam"], row["AwayTeam"])
                    home_goals = int(row["FTHG"])
                    away_goals = int(row["FTAG"])
                except (ValueError, KeyError, TypeError):
                    continue

                matches.append({
                    "date": date,
                    "home": home,
                    "away": away,
                    "home_goals": home_goals,
                    "away_goals": away_goals,
                })

    matches.sort(key=lambda m: m["date"])

    fixture_teams = {team for pair in FIXTURES_LIST for team in pair}

    teams: Dict[str, Dict] = defaultdict(lambda: {"elo": 1500.0, "played": 0})
    wdl_counts = defaultdict(lambda: {"win": 0, "draw": 0, "loss": 0})

    if matches:
        most_recent = max(m["date"] for m in matches)
        recency_half_life_days = 365.0
        decay = math.log(2) / recency_half_life_days
    else:
        most_recent = datetime.now()
        decay = 0.0

    for m in matches:
        home = m["home"]
        away = m["away"]

        if home not in fixture_teams or away not in fixture_teams:
            continue

        hg = m["home_goals"]
        ag = m["away_goals"]

        # Ensure entries exist.
        _ = teams[home]
        _ = teams[away]

        teams[home]["played"] += 1
        teams[away]["played"] += 1

        old_home = teams[home]["elo"]
        old_away = teams[away]["elo"]

        # Correct expected-home probability.
        p_home = 1 / (
            1 + 10 ** ((old_away - (old_home + HOME_ADVANTAGE_ELO)) / ELO_SCALE)
        )

        if hg > ag:
            actual_home = 1.0
            wdl_counts[home]["win"] += 1
            wdl_counts[away]["loss"] += 1
        elif hg == ag:
            actual_home = 0.5
            wdl_counts[home]["draw"] += 1
            wdl_counts[away]["draw"] += 1
        else:
            actual_home = 0.0
            wdl_counts[home]["loss"] += 1
            wdl_counts[away]["win"] += 1

        goal_diff = abs(hg - ag)
        g_mult = math.log(goal_diff + 1) if goal_diff > 0 else 0.0

        days_ago = (most_recent - m["date"]).days
        recency_weight = math.exp(-decay * days_ago)

        k = BASE_K * (1 + g_mult / GOAL_DIFF_EXPECTED) * recency_weight

        teams[home]["elo"] = old_home + k * (actual_home - p_home)
        teams[away]["elo"] = old_away + k * ((1 - actual_home) - (1 - p_home))

    elos = {name: data["elo"] for name, data in teams.items()}
    avg_elo = float(np.mean(list(elos.values()))) if elos else LEAGUE_AVERAGE_ELO

    # Make sure every fixture team has an initial rating.
    for team in fixture_teams:
        elos.setdefault(team, avg_elo)

    # Build smoothed W/D/L rates for every fixture team.
    wdl_rates_out = {}
    for team in fixture_teams:
        c = wdl_counts[team]
        total = c["win"] + c["draw"] + c["loss"]

        # Laplace smoothing toward 1/3 each.
        win = (c["win"] + 1.0) / (total + 3.0)
        draw = (c["draw"] + 1.0) / (total + 3.0)
        loss = (c["loss"] + 1.0) / (total + 3.0)

        s = win + draw + loss
        wdl_rates_out[team] = {
            "win": win / s,
            "draw": draw / s,
            "loss": loss / s,
        }

    return elos, wdl_rates_out

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