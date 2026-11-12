import csv
import math
import os
from collections import defaultdict

try:
    from tqdm.auto import tqdm
    _USE_TQDM = True
except ImportError:
    _USE_TQDM = False


# =============================================================================
# Paths
# =============================================================================
COMBINED_PATH = "/kaggle/input/datasets/flynn28/1926-2024-nfl-scores/1926-2024_COMBINED_NFL_SCORES.csv"
RECENT_CANDIDATES = [
    "/kaggle/input/datasets/keonim/nfl-game-scores-dataset-2017-2023/2010-2026_scores.csv",
    "/kaggle/input/nfl-game-scores-dataset-2017-2023/2010-2026_scores.csv",
    "2010-2026_scores.csv",
]

if not os.path.exists(COMBINED_PATH):
    raise FileNotFoundError(f"Missing: {COMBINED_PATH}")
RECENT_PATH = next((p for p in RECENT_CANDIDATES if os.path.exists(p)), None)
if RECENT_PATH is None:
    raise FileNotFoundError("Missing 2010-2026_scores.csv")

print(f"Combined: {COMBINED_PATH}")
print(f"Recent:   {RECENT_PATH}")


# =============================================================================
# Team universe and name mapping
# =============================================================================
CURRENT_TEAMS = {
    "ARI", "ATL", "BAL", "BUF", "CAR", "CHI", "CIN", "CLE",
    "DAL", "DEN", "DET", "GB", "HOU", "IND", "JAX", "KC",
    "LV", "LAC", "LAR", "MIA", "MIN", "NE", "NO", "NYG",
    "NYJ", "PHI", "PIT", "SF", "SEA", "TB", "TEN", "WAS",
}

# Abbreviation -> current full team name (for final display)
DISPLAY_NAMES = {
    "ARI": "Arizona Cardinals",
    "ATL": "Atlanta Falcons",
    "BAL": "Baltimore Ravens",
    "BUF": "Buffalo Bills",
    "CAR": "Carolina Panthers",
    "CHI": "Chicago Bears",
    "CIN": "Cincinnati Bengals",
    "CLE": "Cleveland Browns",
    "DAL": "Dallas Cowboys",
    "DEN": "Denver Broncos",
    "DET": "Detroit Lions",
    "GB":  "Green Bay Packers",
    "HOU": "Houston Texans",
    "IND": "Indianapolis Colts",
    "JAX": "Jacksonville Jaguars",
    "KC":  "Kansas City Chiefs",
    "LV":  "Las Vegas Raiders",
    "LAC": "Los Angeles Chargers",
    "LAR": "Los Angeles Rams",
    "MIA": "Miami Dolphins",
    "MIN": "Minnesota Vikings",
    "NE":  "New England Patriots",
    "NO":  "New Orleans Saints",
    "NYG": "New York Giants",
    "NYJ": "New York Jets",
    "PHI": "Philadelphia Eagles",
    "PIT": "Pittsburgh Steelers",
    "SF":  "San Francisco 49ers",
    "SEA": "Seattle Seahawks",
    "TB":  "Tampa Bay Buccaneers",
    "TEN": "Tennessee Titans",
    "WAS": "Washington Commanders",
}

RECENT_ALIASES = {
    "AZ": "ARI", "JAC": "JAX", "STL": "LAR", "LA": "LAR",
    "SD": "LAC", "OAK": "LV",
}

# Full-name -> 3-letter abbreviation (only current franchises)
NAME_MAP = {
    'Chicago Cardinals': 'ARI', 'St. Louis Cardinals': 'ARI',
    'Phoenix Cardinals': 'ARI', 'Arizona Cardinals': 'ARI',
    'Atlanta Falcons': 'ATL',
    'Baltimore Ravens': 'BAL',
    'Buffalo Bills': 'BUF',
    'Carolina Panthers': 'CAR',
    'Decatur Staleys': 'CHI', 'Chicago Staleys': 'CHI', 'Chicago Bears': 'CHI',
    'Cincinnati Bengals': 'CIN',
    'Cleveland Browns': 'CLE',
    'Dallas Cowboys': 'DAL',
    'Denver Broncos': 'DEN',
    'Portsmouth Spartans': 'DET', 'Detroit Lions': 'DET',
    'Green Bay Packers': 'GB',
    'Houston Texans': 'HOU',
    'Baltimore Colts': 'IND', 'Indianapolis Colts': 'IND',
    'Jacksonville Jaguars': 'JAX',
    'Kansas City Chiefs': 'KC',
    'Oakland Raiders': 'LV', 'Los Angeles Raiders': 'LV', 'Las Vegas Raiders': 'LV',
    'San Diego Chargers': 'LAC', 'Los Angeles Chargers': 'LAC',
    'Cleveland Rams': 'LAR', 'Los Angeles Rams': 'LAR', 'St. Louis Rams': 'LAR',
    'Miami Dolphins': 'MIA',
    'Minnesota Vikings': 'MIN',
    'Boston Patriots': 'NE', 'New England Patriots': 'NE',
    'New Orleans Saints': 'NO',
    'New York Giants': 'NYG',
    'New York Titans': 'NYJ', 'New York Jets': 'NYJ',
    'Philadelphia Eagles': 'PHI',
    'Pittsburgh Pirates': 'PIT', 'Pittsburgh Steelers': 'PIT',
    'San Francisco 49ers': 'SF',
    'Seattle Seahawks': 'SEA',
    'Tampa Bay Buccaneers': 'TB',
    'Houston Oilers': 'TEN', 'Tennessee Oilers': 'TEN', 'Tennessee Titans': 'TEN',
    'Boston Braves': 'WAS', 'Boston Redskins': 'WAS',
    'Washington Redskins': 'WAS', 'Washington Football Team': 'WAS',
    'Washington Commanders': 'WAS',
}


def map_team(name, season=None):
    if not name:
        return None
    name = name.strip()
    if not name:
        return None
    if name == 'Dallas Texans':
        return 'KC' if (season is not None and season >= 1960) else name
    return NAME_MAP.get(name, name)


def is_counted_week(week):
    if not week:
        return False
    w = week.upper()
    return not ("PRESEASON" in w or "HALL OF FAME" in w or "PRO BOWL" in w
                or "BYE" in w or "TBD" in w)


def is_playoff_week(week):
    w = week.upper()
    return any(x in w for x in (
        "WILD CARD", "DIVISIONAL", "CONFERENCE CHAMPIONSHIP", "SUPER BOWL"))


# =============================================================================
# Elo parameters
# =============================================================================
BASE_ELO = 1500.0
HFA = 50.0
K_REGULAR = 20.0
K_PLAYOFF = 25.0
MOV_CAP = 2.5
SEASON_REGRESSION = 0.25

ratings = defaultdict(lambda: BASE_ELO)


def update_game(home, away, home_score, away_score, k, hfa):
    hr = ratings[home] + hfa
    ar = ratings[away]
    expected_home = 1.0 / (1.0 + 10.0 ** ((ar - hr) / 400.0))

    if home_score > away_score:
        actual_home = 1.0
    elif home_score < away_score:
        actual_home = 0.0
    else:
        actual_home = 0.5

    margin = abs(home_score - away_score)
    if margin == 0:
        mov = 1.0
    else:
        elo_diff = abs(hr - ar)
        mov = math.log(margin + 1.0) * (2.2 / (0.001 * elo_diff + 2.2))
        mov = min(mov, MOV_CAP)

    delta = k * mov * (actual_home - expected_home)
    ratings[home] += delta
    ratings[away] -= delta


def regress_all():
    for team in list(ratings.keys()):
        ratings[team] += SEASON_REGRESSION * (BASE_ELO - ratings[team])


def count_rows(path):
    with open(path, "rb") as f:
        return max(sum(1 for _ in f) - 1, 1)


# =============================================================================
# Phase 1 — pre-2010 games (combined file, no home/away data -> HFA = 0)
# =============================================================================
games_processed = 0
last_season = None

combined_total = count_rows(COMBINED_PATH)
print(f"\n[1/2] Processing pre-2010 games from combined file "
      f"({combined_total} rows, HFA=0) ...")

with open(COMBINED_PATH, newline="", encoding="utf-8-sig") as f:
    reader = csv.DictReader(f)
    iterator = tqdm(reader, total=combined_total, desc="1926-2009",
                    unit="row") if _USE_TQDM else reader

    for row in iterator:
        if not row.get("Date") or not row.get("WT") or not row.get("LT"):
            continue
        try:
            season = int(row["Season"])
        except (ValueError, KeyError, TypeError):
            continue
        if season >= 2010:
            continue

        if last_season is not None and season != last_season:
            regress_all()
        last_season = season

        wt = map_team(row["WT"], season)
        lt = map_team(row["LT"], season)
        if not wt or not lt or wt == lt:
            continue
        try:
            wts = float(row["WTS"])
            lts = float(row["LTS"])
        except (ValueError, KeyError, TypeError):
            continue

        k = K_PLAYOFF if "Playoff" in (row.get("Type") or "") else K_REGULAR
        update_game(wt, lt, wts, lts, k, hfa=0.0)
        games_processed += 1


# =============================================================================
# Phase 2 — 2010+ games (recent file, home/away known -> HFA = 50)
# =============================================================================
recent_total = count_rows(RECENT_PATH)
print(f"\n[2/2] Processing 2010+ games from recent file "
      f"({recent_total} rows, HFA={HFA:.0f}) ...")

with open(RECENT_PATH, newline="", encoding="utf-8-sig") as f:
    reader = csv.DictReader(f)
    iterator = tqdm(reader, total=recent_total, desc="2010-2026",
                    unit="row") if _USE_TQDM else reader

    for row in iterator:
        if (row.get("GameStatus") or "").strip().upper() != "FINAL":
            continue
        week = row.get("Week", "")
        if not is_counted_week(week):
            continue
        try:
            season = int(row["Season"])
        except (ValueError, KeyError, TypeError):
            continue

        if last_season is not None and season != last_season:
            regress_all()
        last_season = season

        away = (row.get("AwayTeam") or "").strip().upper()
        home = (row.get("HomeTeam") or "").strip().upper()
        away = RECENT_ALIASES.get(away, away)
        home = RECENT_ALIASES.get(home, home)

        if away not in CURRENT_TEAMS or home not in CURRENT_TEAMS:
            continue
        try:
            away_score = float(row["AwayScore"])
            home_score = float(row["HomeScore"])
        except (ValueError, KeyError, TypeError):
            continue

        k = K_PLAYOFF if is_playoff_week(week) else K_REGULAR
        update_game(home, away, home_score, away_score, k, hfa=HFA)
        games_processed += 1


# =============================================================================
# Output — full team names
# =============================================================================
current_sorted = sorted(
    ((t, ratings[t]) for t in CURRENT_TEAMS), key=lambda x: -x[1]
)

print()
print(f"Games processed : {games_processed}")
print(f"Teams tracked   : {len(ratings)} (current + defunct)")
print()
print(f"{'Rank':<5}{'Team':<28}{'Elo':>9}")
print("-" * 43)
for rank, (team, elo) in enumerate(current_sorted, 1):
    print(f"{rank:<5}{DISPLAY_NAMES[team]:<28}{elo:9.2f}")