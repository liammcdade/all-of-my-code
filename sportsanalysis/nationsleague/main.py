import random
import math
import itertools
from collections import defaultdict, Counter
from itertools import groupby
from typing import Dict, List, Tuple, Set, Optional, Any

try:
    from tqdm import tqdm
    HAS_TQDM = True
except ImportError:
    HAS_TQDM = False

# ============================================================
# CONFIG & DATA
# ============================================================
N_SIMS = 10_000
RANDOM_SEED = 42
HOME_ADV = 108.80
BASE_XG = 1.35222
XG_ELO_SCALE = 600.0
ELO_SCALE = 400
MAX_XG = 3.5
HIST_WEIGHT = 0.30
HIST_PRIOR_MATCHES = 60.0

DISCIPLINE_POINTS: Dict[str, int] = {
    "Ukraine": 14, "Israel": 13, "Portugal": 12, "Belgium": 12,
    "Czechia": 12, "Andorra": 11, "Romania": 11, "Türkiye": 11,
    "Norway": 11, "North Macedonia": 11, "Greece": 11, "San Marino": 10,
    "Albania": 10, "Luxembourg": 10, "Scotland": 10, "Wales": 10,
    "Slovenia": 10, "Netherlands": 10, "Cyprus": 10, "Belarus": 9,
    "Hungary": 9, "Republic of Ireland": 9, "Austria": 9, "Bulgaria": 9,
    "Northern Ireland": 8, "Azerbaijan": 8, "Denmark": 8, "Poland": 8,
    "Lithuania": 8, "Iceland": 7, "Malta": 7, "Bosnia and Herzegovina": 7,
    "Estonia": 7, "Italy": 7, "Kazakhstan": 6, "Germany": 6,
    "France": 6, "Croatia": 6, "Georgia": 5, "Armenia": 5,
    "Liechtenstein": 4, "Slovakia": 4, "Finland": 4, "England": 4,
    "Faroe Islands": 4, "Latvia": 3, "Spain": 2, "Moldova": 1,
    "Switzerland": 1, "Sweden": 1, "Serbia": 0, "Kosovo": 0,
    "Montenegro": 0, "Gibraltar": 0,
}

FIXED_RESULTS = {
    ("Andorra", "Malta"): (1, 2), ("Norway", "Denmark"): (3, 2),
    ("Liechtenstein", "Lithuania"): (0, 2), ("Kosovo", "Republic of Ireland"): (1, 0),
    ("Netherlands", "Germany"): (1, 1), ("Austria", "Israel"): (3, 1),
    ("Portugal", "Wales"): (1, 0), ("Serbia", "Greece"): (1, 2),
    ("Georgia", "Northern Ireland"): (0, 1), ("Armenia", "Latvia"): (2, 0),
    ("Sweden", "Romania"): (2, 1), ("Montenegro", "Cyprus"): (2, 1),
    ("Hungary", "Ukraine"): (0, 1), ("Italy", "Belgium"): (0, 2),
    ("Türkiye", "France"): (0, 1), ("Poland", "Bosnia and Herzegovina"): (0, 0),
    ("Slovenia", "Scotland"): (0, 0), ("Faroe Islands", "Kazakhstan"): (1, 1),
    ("San Marino", "Finland"): (0, 7), ("Iceland", "Estonia"): (1, 1),
    ("Bulgaria", "Luxembourg"): (1, 2), ("Czechia", "Croatia"): (1, 2),
    ("North Macedonia", "Switzerland"): (0, 3), ("England", "Spain"): (2, 3),
    ("Slovakia", "Moldova"): (2, 0), ("Albania", "Belarus"): (2, 0),
    ("Lithuania", "Azerbaijan"): (1, 1), ("Serbia", "Netherlands"): (1, 2),
    ("Gibraltar", "Andorra"): (0, 0), ("Austria", "Kosovo"): (3, 1),
    ("Denmark", "Wales"): (2, 0), ("Norway", "Portugal"): (1, 2),
    ("Israel", "Republic of Ireland"): (0, 3), ("Germany", "Greece"): (0, 1),
    ("Latvia", "Cyprus"): (0, 0), ("Georgia", "Ukraine"): (0, 0),
    ("Armenia", "Montenegro"): (2, 3), ("Romania", "Bosnia and Herzegovina"): (2, 4),
    ("Türkiye", "Italy"): (1, 4), ("Belgium", "France"): (0, 1),
    ("Northern Ireland", "Hungary"): (0, 0), ("Sweden", "Poland"): (3, 1),
    ("Finland", "Belarus"): (0, 0), ("Moldova", "Faroe Islands"): (1, 1),
    ("Spain", "Croatia"): (4, 1), ("Luxembourg", "Iceland"): (0, 3),
    ("Slovakia", "Kazakhstan"): (2, 1), ("Czechia", "England"): (0, 2),
    ("Slovenia", "North Macedonia"): (2, 0), ("Bulgaria", "Estonia"): (0, 0),
    ("San Marino", "Albania"): (0, 3), ("Scotland", "Switzerland"): (0, 3),
    ("Azerbaijan", "Liechtenstein"): (0, 0), ("Israel", "Kosovo"): (0, 0),
    ("Greece", "Netherlands"): (2, 2), ("Germany", "Serbia"): (2, 0),
    ("Republic of Ireland", "Austria"): (2, 2), ("Wales", "Norway"): (2, 1),
    ("Malta", "Gibraltar"): (1, 1), ("Denmark", "Portugal"): (2, 4),
    ("Kazakhstan", "Moldova"): (1, 2), ("Cyprus", "Armenia"): (2, 0),
    ("Latvia", "Montenegro"): (1, 2), ("Ukraine", "Northern Ireland"): (0, 3),
    ("Poland", "Romania"): (6, 0), ("Faroe Islands", "Slovakia"): (1, 1),
    ("Belgium", "Türkiye"): (3, 0), ("Hungary", "Georgia"): (1, 0),
    ("Bosnia and Herzegovina", "Sweden"): (1, 1), ("France", "Italy"): (1, 1),
    ("Finland", "Albania"): (2, 1), ("Iceland", "Bulgaria"): (3, 0),
    ("Belarus", "San Marino"): (4, 0), ("Croatia", "England"): (0, 7),
    ("Estonia", "Luxembourg"): (1, 0), ("Switzerland", "Slovenia"): (2, 1),
    ("North Macedonia", "Scotland"): (0, 2), ("Spain", "Czechia"): (3, 1),
    ("Azerbaijan", "Lithuania"): (1, 0), ("Kosovo", "Austria"): (1, 1),
    ("Malta", "Andorra"): (1, 0), ("Greece", "Germany"): (0, 0),
    ("Netherlands", "Serbia"): (2, 1), ("Portugal", "Norway"): (2, 1),
    ("Wales", "Denmark"): (0, 1), ("Republic of Ireland", "Israel"): (1, 1),
    ("Cyprus", "Latvia"): (2, 1), ("Italy", "Türkiye"): (3, 1),
    ("Romania", "Sweden"): (0, 1), ("Bosnia and Herzegovina", "Poland"): (1, 0),
    ("France", "Belgium"): (4, 1), ("Montenegro", "Armenia"): (0, 0),
    ("Ukraine", "Hungary"): (1, 2), ("Northern Ireland", "Georgia"): (0, 0),
    ("Kazakhstan", "Faroe Islands"): (2, 2), ("Croatia", "Spain"): (1, 2),
    ("Moldova", "Slovakia"): (0, 4), ("Luxembourg", "Bulgaria"): (0, 2),
    ("Belarus", "Finland"): (1, 0), ("Albania", "San Marino"): (2, 1),
    ("Estonia", "Iceland"): (0, 0), ("England", "Czechia"): (3, 0),
    ("Switzerland", "North Macedonia"): (3, 0), ("Scotland", "Slovenia"): (1, 2),
}

ELO_RATINGS = {
    "Spain": 2282, "England": 2144, "France": 2088, "Portugal": 2067,
    "Belgium": 1972, "Switzerland": 1927, "Norway": 1908, "Netherlands": 1974,
    "Italy": 1897, "Germany": 1894, "Croatia": 1891, "Denmark": 1864,
    "Austria": 1863, "Ukraine": 1747, "Greece": 1807, "Türkiye": 1781,
    "Sweden": 1759, "Wales": 1681, "Scotland": 1746, "Serbia": 1683,
    "Kosovo": 1710, "Hungary": 1702, "Poland": 1702, "Republic of Ireland": 1711,
    "Slovenia": 1690, "Czechia": 1658, "Northern Ireland": 1681, "Slovakia": 1665,
    "Romania": 1569, "Georgia": 1619, "Iceland": 1603, "Albania": 1612,
    "Bosnia and Herzegovina": 1655, "North Macedonia": 1536, "Finland": 1552,
    "Montenegro": 1503, "Belarus": 1515, "Bulgaria": 1411, "Luxembourg": 1422,
    "Israel": 1619, "Kazakhstan": 1393, "Faroe Islands": 1392, "Armenia": 1341,
    "Cyprus": 1346, "Azerbaijan": 1326, "Moldova": 1301, "Lithuania": 1278,
    "Latvia": 1246, "Malta": 1263, "Andorra": 1056, "Gibraltar": 1022,
    "Liechtenstein": 901, "San Marino": 820, "Estonia": 1400,
}

TEAM_HOME_AWAY_GOALS: Dict[str, Dict[str, float]] = {
    "France": {"matches_home": 544, "goals_home": 1134, "avg_home": 2.085, "matches_away": 399, "goals_away": 601, "avg_away": 1.506},
    "Italy": {"matches_home": 492, "goals_home": 1019, "avg_home": 2.071, "matches_away": 401, "goals_away": 546, "avg_away": 1.362},
    "Belgium": {"matches_home": 458, "goals_home": 958, "avg_home": 2.092, "matches_away": 401, "goals_away": 606, "avg_away": 1.511},
    "Türkiye": {"matches_home": 306, "goals_home": 482, "avg_home": 1.575, "matches_away": 339, "goals_away": 420, "avg_away": 1.239},
    "Germany": {"matches_home": 557, "goals_home": 1394, "avg_home": 2.503, "matches_away": 478, "goals_away": 937, "avg_away": 1.960},
    "Netherlands": {"matches_home": 479, "goals_home": 1146, "avg_home": 2.392, "matches_away": 404, "goals_away": 706, "avg_away": 1.748},
    "Serbia": {"matches_home": 135, "goals_home": 250, "avg_home": 1.852, "matches_away": 213, "goals_away": 281, "avg_away": 1.319},
    "Greece": {"matches_home": 321, "goals_home": 478, "avg_home": 1.489, "matches_away": 312, "goals_away": 316, "avg_away": 1.013},
    "Spain": {"matches_home": 414, "goals_home": 987, "avg_home": 2.384, "matches_away": 377, "goals_away": 629, "avg_away": 1.668},
    "Croatia": {"matches_home": 193, "goals_home": 390, "avg_home": 2.021, "matches_away": 207, "goals_away": 304, "avg_away": 1.469},
    "England": {"matches_home": 554, "goals_home": 1261, "avg_home": 2.276, "matches_away": 544, "goals_away": 1140, "avg_away": 2.096},
    "Czechia": {"matches_home": 178, "goals_home": 380, "avg_home": 2.135, "matches_away": 185, "goals_away": 265, "avg_away": 1.432},
    "Portugal": {"matches_home": 373, "goals_home": 788, "avg_home": 2.113, "matches_away": 327, "goals_away": 447, "avg_away": 1.367},
    "Denmark": {"matches_home": 447, "goals_home": 961, "avg_home": 2.150, "matches_away": 427, "goals_away": 626, "avg_away": 1.466},
    "Norway": {"matches_home": 439, "goals_home": 747, "avg_home": 1.702, "matches_away": 439, "goals_away": 617, "avg_away": 1.405},
    "Wales": {"matches_home": 360, "goals_home": 526, "avg_home": 1.461, "matches_away": 366, "goals_away": 384, "avg_away": 1.049},
    "Scotland": {"matches_home": 417, "goals_home": 788, "avg_home": 1.890, "matches_away": 437, "goals_away": 667, "avg_away": 1.526},
    "Switzerland": {"matches_home": 449, "goals_home": 789, "avg_home": 1.757, "matches_away": 441, "goals_away": 541, "avg_away": 1.227},
    "Slovenia": {"matches_home": 155, "goals_home": 223, "avg_home": 1.439, "matches_away": 162, "goals_away": 169, "avg_away": 1.043},
    "North Macedonia": {"matches_home": 151, "goals_home": 206, "avg_home": 1.364, "matches_away": 155, "goals_away": 159, "avg_away": 1.026},
    "Hungary": {"matches_home": 499, "goals_home": 1135, "avg_home": 2.275, "matches_away": 507, "goals_away": 876, "avg_away": 1.728},
    "Ukraine": {"matches_home": 163, "goals_home": 245, "avg_home": 1.503, "matches_away": 175, "goals_away": 230, "avg_away": 1.314},
    "Georgia": {"matches_home": 145, "goals_home": 217, "avg_home": 1.497, "matches_away": 162, "goals_away": 166, "avg_away": 1.025},
    "Northern Ireland": {"matches_home": 339, "goals_home": 429, "avg_home": 1.265, "matches_away": 368, "goals_away": 312, "avg_away": 0.848},
    "Israel": {"matches_home": 277, "goals_home": 469, "avg_home": 1.693, "matches_away": 221, "goals_away": 281, "avg_away": 1.271},
    "Austria": {"matches_home": 462, "goals_home": 928, "avg_home": 2.009, "matches_away": 402, "goals_away": 619, "avg_away": 1.540},
    "Republic of Ireland": {"matches_home": 346, "goals_home": 533, "avg_home": 1.540, "matches_away": 287, "goals_away": 325, "avg_away": 1.132},
    "Kosovo": {"matches_home": 60, "goals_home": 97, "avg_home": 1.617, "matches_away": 46, "goals_away": 59, "avg_away": 1.283},
    "Poland": {"matches_home": 429, "goals_home": 832, "avg_home": 1.939, "matches_away": 463, "goals_away": 667, "avg_away": 1.441},
    "Bosnia and Herzegovina": {"matches_home": 137, "goals_home": 209, "avg_home": 1.526, "matches_away": 150, "goals_away": 184, "avg_away": 1.227},
    "Romania": {"matches_home": 363, "goals_home": 705, "avg_home": 1.942, "matches_away": 403, "goals_away": 534, "avg_away": 1.325},
    "Sweden": {"matches_home": 535, "goals_home": 1247, "avg_home": 2.331, "matches_away": 570, "goals_away": 931, "avg_away": 1.633},
    "Albania": {"matches_home": 210, "goals_home": 239, "avg_home": 1.138, "matches_away": 188, "goals_away": 138, "avg_away": 0.734},
    "Finland": {"matches_home": 362, "goals_home": 524, "avg_home": 1.448, "matches_away": 456, "goals_away": 436, "avg_away": 0.956},
    "Belarus": {"matches_home": 145, "goals_home": 184, "avg_home": 1.269, "matches_away": 170, "goals_away": 179, "avg_away": 1.053},
    "San Marino": {"matches_home": 114, "goals_home": 26, "avg_home": 0.228, "matches_away": 111, "goals_away": 18, "avg_away": 0.162},
    "Montenegro": {"matches_home": 91, "goals_home": 126, "avg_home": 1.385, "matches_away": 79, "goals_away": 75, "avg_away": 0.949},
    "Armenia": {"matches_home": 133, "goals_home": 150, "avg_home": 1.128, "matches_away": 139, "goals_away": 124, "avg_away": 0.892},
    "Cyprus": {"matches_home": 234, "goals_home": 251, "avg_home": 1.073, "matches_away": 192, "goals_away": 124, "avg_away": 0.646},
    "Latvia": {"matches_home": 225, "goals_home": 287, "avg_home": 1.276, "matches_away": 236, "goals_away": 254, "avg_away": 1.076},
    "Kazakhstan": {"matches_home": 125, "goals_home": 174, "avg_home": 1.392, "matches_away": 144, "goals_away": 135, "avg_away": 0.938},
    "Slovakia": {"matches_home": 168, "goals_home": 278, "avg_home": 1.655, "matches_away": 199, "goals_away": 240, "avg_away": 1.206},
    "Faroe Islands": {"matches_home": 140, "goals_home": 153, "avg_home": 1.093, "matches_away": 147, "goals_away": 87, "avg_away": 0.592},
    "Moldova": {"matches_home": 132, "goals_home": 126, "avg_home": 0.955, "matches_away": 167, "goals_away": 117, "avg_away": 0.701},
    "Iceland": {"matches_home": 236, "goals_home": 322, "avg_home": 1.364, "matches_away": 286, "goals_away": 310, "avg_away": 1.084},
    "Bulgaria": {"matches_home": 326, "goals_home": 560, "avg_home": 1.718, "matches_away": 410, "goals_away": 456, "avg_away": 1.112},
    "Estonia": {"matches_home": 268, "goals_home": 304, "avg_home": 1.134, "matches_away": 282, "goals_away": 240, "avg_away": 0.851},
    "Luxembourg": {"matches_home": 255, "goals_home": 180, "avg_home": 0.706, "matches_away": 212, "goals_away": 116, "avg_away": 0.547},
    "Gibraltar": {"matches_home": 89, "goals_home": 114, "avg_home": 1.281, "matches_away": 70, "goals_away": 63, "avg_away": 0.900},
    "Malta": {"matches_home": 254, "goals_home": 208, "avg_home": 0.819, "matches_away": 204, "goals_away": 90, "avg_away": 0.441},
    "Andorra": {"matches_home": 115, "goals_home": 44, "avg_home": 0.383, "matches_away": 114, "goals_away": 31, "avg_away": 0.272},
    "Lithuania": {"matches_home": 184, "goals_home": 207, "avg_home": 1.125, "matches_away": 249, "goals_away": 224, "avg_away": 0.900},
    "Azerbaijan": {"matches_home": 152, "goals_home": 141, "avg_home": 0.928, "matches_away": 158, "goals_away": 97, "avg_away": 0.614},
    "Liechtenstein": {"matches_home": 121, "goals_home": 50, "avg_home": 0.413, "matches_away": 138, "goals_away": 55, "avg_away": 0.399},
}

LEAGUES_2627 = {
    "A": {"groups": {
        "A1": ["France", "Italy", "Belgium", "Türkiye"],
        "A2": ["Germany", "Netherlands", "Serbia", "Greece"],
        "A3": ["Spain", "Croatia", "England", "Czechia"],
        "A4": ["Portugal", "Denmark", "Norway", "Wales"]}},
    "B": {"groups": {
        "B1": ["Scotland", "Switzerland", "Slovenia", "North Macedonia"],
        "B2": ["Hungary", "Ukraine", "Georgia", "Northern Ireland"],
        "B3": ["Israel", "Austria", "Republic of Ireland", "Kosovo"],
        "B4": ["Poland", "Bosnia and Herzegovina", "Romania", "Sweden"]}},
    "C": {"groups": {
        "C1": ["Albania", "Finland", "Belarus", "San Marino"],
        "C2": ["Montenegro", "Armenia", "Cyprus", "Latvia"],
        "C3": ["Kazakhstan", "Slovakia", "Faroe Islands", "Moldova"],
        "C4": ["Iceland", "Bulgaria", "Estonia", "Luxembourg"]}},
    "D": {"groups": {
        "D1": ["Gibraltar", "Malta", "Andorra"],
        "D2": ["Lithuania", "Azerbaijan", "Liechtenstein"]}},
}

ALL_TEAMS = [t for lg in LEAGUES_2627.values() for grp in lg["groups"].values() for t in grp]
for t in ALL_TEAMS:
    if t not in DISCIPLINE_POINTS: DISCIPLINE_POINTS[t] = 0

# ============================================================
# CORE SIMULATION FUNCTIONS
# ============================================================
def effective_elo(team: str) -> float:
    return float(ELO_RATINGS[team])

_total_mh = sum(TEAM_HOME_AWAY_GOALS[t]["matches_home"] for t in ALL_TEAMS)
_total_gh = sum(TEAM_HOME_AWAY_GOALS[t]["goals_home"] for t in ALL_TEAMS)
_total_ma = sum(TEAM_HOME_AWAY_GOALS[t]["matches_away"] for t in ALL_TEAMS)
_total_ga = sum(TEAM_HOME_AWAY_GOALS[t]["goals_away"] for t in ALL_TEAMS)
GLOBAL_AVG_HOME = _total_gh / _total_mh
GLOBAL_AVG_AWAY = _total_ga / _total_ma

def _attack_modifier(team: str, is_home: bool) -> float:
    s = TEAM_HOME_AWAY_GOALS[team]
    n, g, ref = (
        (s["matches_home"], s["goals_home"], GLOBAL_AVG_HOME) if is_home
        else (s["matches_away"], s["goals_away"], GLOBAL_AVG_AWAY)
    )
    if n == 0: return 1.0
    shrunk = (n * (g / n) + HIST_PRIOR_MATCHES * ref) / (n + HIST_PRIOR_MATCHES)
    return shrunk / ref

HOME_ATTACK_MOD = {t: _attack_modifier(t, True) for t in ALL_TEAMS}
AWAY_ATTACK_MOD = {t: _attack_modifier(t, False) for t in ALL_TEAMS}

def poisson_rand(lam: float, rng: random.Random) -> int:
    if lam <= 0: return 0
    L, k, p = math.exp(-lam), 0, 1.0
    while True:
        k += 1; p *= rng.random()
        if p <= L: return k - 1

def expected_goals(home: str, away: str) -> Tuple[float, float]:
    diff = (effective_elo(home) + HOME_ADV) - effective_elo(away)
    h_elo = BASE_XG * math.exp(diff / XG_ELO_SCALE)
    a_elo = BASE_XG * math.exp(-diff / XG_ELO_SCALE)
    h = h_elo * (1.0 + HIST_WEIGHT * (HOME_ATTACK_MOD[home] - 1.0))
    a = a_elo * (1.0 + HIST_WEIGHT * (AWAY_ATTACK_MOD[away] - 1.0))
    return min(h, MAX_XG), min(a, MAX_XG)

def simulate_match(home: str, away: str, rng: random.Random) -> Tuple[int, int]:
    hxg, axg = expected_goals(home, away)
    return poisson_rand(hxg, rng), poisson_rand(axg, rng)

def simulate_two_legged_tie(higher: str, lower: str, rng: random.Random) -> str:
    # Higher ranked team hosts 2nd leg
    h1, a1 = simulate_match(lower, higher, rng) # Leg 1 at Lower
    h2, a2 = simulate_match(higher, lower, rng) # Leg 2 at Higher
    
    agg_h, agg_l = a1 + h2, h1 + a2
    if agg_h > agg_l: return higher
    if agg_l > agg_h: return lower
    
    # Extra time & Penalties approximated by Elo advantage
    e1, e2 = effective_elo(higher), effective_elo(lower)
    return higher if rng.random() < 0.5 + (e1 - e2) / (2 * ELO_SCALE) else lower

def neutral_match(t1: str, t2: str, rng: random.Random) -> str:
    e1, e2 = effective_elo(t1), effective_elo(t2)
    d = e1 - e2
    xg1_elo = min(BASE_XG * math.exp(d / XG_ELO_SCALE), MAX_XG)
    xg2_elo = min(BASE_XG * math.exp(-d / XG_ELO_SCALE), MAX_XG)
    mod1 = 0.5 * (HOME_ATTACK_MOD[t1] + AWAY_ATTACK_MOD[t1])
    mod2 = 0.5 * (HOME_ATTACK_MOD[t2] + AWAY_ATTACK_MOD[t2])
    xg1 = min(xg1_elo * (1.0 + HIST_WEIGHT * (mod1 - 1.0)), MAX_XG)
    xg2 = min(xg2_elo * (1.0 + HIST_WEIGHT * (mod2 - 1.0)), MAX_XG)
    g1, g2 = poisson_rand(xg1, rng), poisson_rand(xg2, rng)
    if g1 > g2: return t1
    if g2 > g1: return t2
    return t1 if rng.random() < 0.5 + (e1 - e2) / (2 * ELO_SCALE) else t2

# ============================================================
# STANDINGS & TIE-BREAKS
# ============================================================
def calculate_group_standings(teams, results, access_order=None):
    stats = {t: {"team": t, "played": 0, "won": 0, "drawn": 0, "lost": 0,
                 "gf": 0, "ga": 0, "gd": 0, "points": 0,
                 "away_gf": 0, "away_won": 0, "disc_points": DISCIPLINE_POINTS.get(t, 0)}
             for t in teams}
    if access_order is None: access_order = {t: i for i, t in enumerate(teams)}
    
    for home, away, hg, ag in results:
        stats[home]["played"] += 1; stats[away]["played"] += 1
        stats[home]["gf"] += hg; stats[home]["ga"] += ag
        stats[away]["gf"] += ag; stats[away]["ga"] += hg
        stats[away]["away_gf"] += ag
        if hg > ag: stats[home]["won"] += 1; stats[home]["points"] += 3; stats[away]["lost"] += 1
        elif hg < ag: stats[away]["won"] += 1; stats[away]["away_won"] += 1; stats[away]["points"] += 3; stats[home]["lost"] += 1
        else: stats[home]["drawn"] += 1; stats[away]["drawn"] += 1; stats[home]["points"] += 1; stats[away]["points"] += 1
            
    for t in stats: stats[t]["gd"] = stats[t]["gf"] - stats[t]["ga"]
    
    # Sort by Points, GD, GF, then Access Order (Seed)
    order = sorted(teams, key=lambda t: (-stats[t]["points"], -stats[t]["gd"], -stats[t]["gf"], access_order[t]))
    return [stats[t] for t in order]

# ============================================================
# 2026/27 SIMULATION
# ============================================================
def simulate_2627_season(rng):
    group_standings = {}
    for lg_name, lg in LEAGUES_2627.items():
        for gname, teams in lg["groups"].items():
            matches = [(a, b) for i, a in enumerate(teams) for b in teams[i+1:]] + \
                      [(b, a) for i, a in enumerate(teams) for b in teams[i+1:]]
            results = []
            for h, a in matches:
                if (h, a) in FIXED_RESULTS: results.append((h, a, FIXED_RESULTS[(h,a)][0], FIXED_RESULTS[(h,a)][1]))
                else:
                    hg, ag = simulate_match(h, a, rng)
                    results.append((h, a, hg, ag))
            
            st = calculate_group_standings(teams, results)
            group_standings[gname] = st
            
    return group_standings

def get_overall_ranking_2627(group_standings):
    """
    Creates the 1-54 ranking used to seed the 2028/29 leagues.
    Rules: League Level > Group Position > Points > GD > GF
    """
    league_level = {"A": 4, "B": 3, "C": 2, "D": 1}
    all_teams_ranked = []
    
    for gname, st in group_standings.items():
        lg = gname[0]
        for pos, entry in enumerate(st, 1):
            entry["league_level"] = league_level[lg]
            entry["group_pos"] = pos
            all_teams_ranked.append(entry)
            
    # Sort by League Level (Desc), Group Pos (Asc), Points (Desc), GD (Desc), GF (Desc)
    all_teams_ranked.sort(key=lambda x: (-x["league_level"], x["group_pos"], -x["points"], -x["gd"], -x["gf"]))
    return [e["team"] for e in all_teams_ranked]

def determine_2829_leagues(ranking_2627):
    """
    Splits the 54 teams into 3 leagues of 18 based on 26/27 ranking.
    """
    return {
        "A": ranking_2627[0:18],
        "B": ranking_2627[18:36],
        "C": ranking_2627[36:54]
    }

# ============================================================
# 2028/29 SIMULATION
# ============================================================
def draw_groups_2829(teams, rng):
    """
    Draws 3 groups of 6 from 18 teams.
    Seeding: 3 pots of 6. Each group gets 2 from each pot.
    """
    pots = [teams[0:6], teams[6:12], teams[12:18]]
    for pot in pots: rng.shuffle(pot)
    
    groups = {"G1": [], "G2": [], "G3": []}
    for pot in pots:
        groups["G1"].extend(pot[0:2])
        groups["G2"].extend(pot[2:4])
        groups["G3"].extend(pot[4:6])
    return groups

def generate_2829_fixtures_indices():
    """
    Returns a list of (home_idx, away_idx) for a group of 6 teams.
    Indices 0,1 are Pot 1; 2,3 are Pot 2; 4,5 are Pot 3.
    Ensures: 
    - 2 games vs same pot opponent.
    - 1 game vs each of the 4 other opponents.
    - Balanced Home/Away against each Pot.
    """
    return [
        # Pot 1 Rivalry (0 vs 1)
        (0, 1), (1, 0),
        # Team 0 vs Pot 2 (2,3) & Pot 3 (4,5)
        (0, 2), (3, 0), (4, 0), (0, 5),
        # Team 1 vs Pot 2 (2,3) & Pot 3 (4,5)
        (2, 1), (1, 3), (1, 4), (5, 1),
        # Pot 2 Rivalry (2 vs 3)
        (2, 3), (3, 2),
        # Team 2 vs Pot 3 (4,5) - remaining matches for 2
        (2, 4), (5, 2),
        # Team 3 vs Pot 3 (4,5) - remaining matches for 3
        (4, 3), (3, 5),
        # Pot 3 Rivalry (4 vs 5)
        (4, 5), (5, 4)
    ]

def simulate_2829_league_phase(teams_dict, rng):
    """
    Simulates the league phase for Leagues A, B, C.
    Returns final standings for each league.
    """
    final_standings = {}
    fixture_template = generate_2829_fixtures_indices()
    
    for lg_name, teams in teams_dict.items():
        groups = draw_groups_2829(teams, rng)
        lg_entries = []
        
        for g_idx, (g_name, g_teams) in enumerate(groups.items()):
            results = []
            for h_idx, a_idx in fixture_template:
                home_team = g_teams[h_idx]
                away_team = g_teams[a_idx]
                hg, ag = simulate_match(home_team, away_team, rng)
                results.append((home_team, away_team, hg, ag))
            
            access_order = {t: i for i, t in enumerate(g_teams)}
            st = calculate_group_standings(g_teams, results, access_order)
            
            # Add metadata for overall ranking
            for pos, entry in enumerate(st, 1):
                entry["group_pos"] = pos
                entry["league"] = lg_name
                
            lg_entries.extend(st)
            
        # Sort League Standings (for display/internal logic, though overall ranking uses group pos)
        lg_entries.sort(key=lambda e: (-e["points"], -e["gd"], -e["gf"]))
        final_standings[lg_name] = lg_entries
        
    return final_standings

def get_overall_ranking_2829(standings_2829):
    """
    Creates the 1-54 ranking after 28/29 League Phase.
    This is the ranking used for World Cup Qualifying seeding.
    Rules: League Level (A>B>C) > Group Position > Points > GD > GF
    """
    league_level = {"A": 3, "B": 2, "C": 1}
    all_teams_ranked = []
    
    for lg_name, entries in standings_2829.items():
        for entry in entries:
            entry["league_level"] = league_level[lg_name]
            all_teams_ranked.append(entry)
            
    # Sort by League Level (Desc), Group Pos (Asc), Points (Desc), GD (Desc), GF (Desc)
    all_teams_ranked.sort(key=lambda x: (-x["league_level"], x["group_pos"], -x["points"], -x["gd"], -x["gf"]))
    return [e["team"] for e in all_teams_ranked]

# ============================================================
# MAIN SIMULATION LOOP
# ============================================================
def run_full_simulation(n_sims, seed=None):
    rng = random.Random(seed)
    
    # Counters
    rank_counts = defaultdict(lambda: defaultdict(int)) # team -> {rank: count}
    wc_league_1_counts = Counter()
    wc_league_2_counts = Counter()
    
    it = tqdm(range(n_sims), desc="Simulating 2026-2029", unit="sim") if HAS_TQDM else range(n_sims)
    
    for _ in it:
        # 1. Simulate 2026/27
        gs_2627 = simulate_2627_season(rng)
        ranking_2627 = get_overall_ranking_2627(gs_2627)
        
        # 2. Allocate 2028/29 Leagues
        teams_2829 = determine_2829_leagues(ranking_2627)
        
        # 3. Simulate 2028/29 League Phase
        standings_2829 = simulate_2829_league_phase(teams_2829, rng)
        
        # 4. Get Final Ranking 28/29 (Pre-Finals)
        ranking_2829 = get_overall_ranking_2829(standings_2829)
        
        # 5. Record Data
        for rank, team in enumerate(ranking_2829, 1):
            rank_counts[team][rank] += 1
            
        # 6. Determine WC Qualifying Leagues
        # League A & B -> WC League 1
        # League C -> WC League 2
        for team in teams_2829["A"] + teams_2829["B"]:
            wc_league_1_counts[team] += 1
        for team in teams_2829["C"]:
            wc_league_2_counts[team] += 1
            
    return rank_counts, wc_league_1_counts, wc_league_2_counts

def print_most_likely_ranking(rank_counts, n_sims):
    print("\n=== MOST LIKELY FINAL RANKING (2028/29 League Phase) ===")
    print("This ranking determines the 2030 World Cup Qualifying Paths.")
    print("-" * 65)
    print(f"{'Rank':<5} {'Team':<24} {'Prob %':>8} {'Avg Rank':>10}")
    print("-" * 65)
    
    # Calculate most likely rank for each team
    team_best_rank = {}
    for team in ALL_TEAMS:
        probs = rank_counts[team]
        if not probs: continue
        # Find rank with highest probability
        best_r = max(probs, key=probs.get)
        best_p = probs[best_r] / n_sims
        avg_r = sum(r*c for r,c in probs.items()) / sum(probs.values())
        team_best_rank[team] = (best_r, best_p, avg_r)
        
    # Sort teams by their most likely rank
    sorted_teams = sorted(ALL_TEAMS, key=lambda t: team_best_rank.get(t, (99,0,0))[0])
    
    for i, team in enumerate(sorted_teams[:54]): # Top 54
        best_r, best_p, avg_r = team_best_rank[team]
        print(f"{best_r:<5} {team:<24} {best_p*100:>7.1f}% {avg_r:>9.1f}")

def print_wc_summary_with_certainty(wc1, wc2, n_sims):
    print("\n=== 2030 WORLD CUP QUALIFYING LEAGUE PROJECTIONS ===")
    print(f"{'Team':<24} {'Most Likely':>12} {'Certainty %':>11} {'L1 %':>8} {'L2 %':>8}")
    print("-" * 65)
    
    certainties = []
    
    for team in sorted(ALL_TEAMS):
        p1 = wc1.get(team, 0) / n_sims * 100
        p2 = wc2.get(team, 0) / n_sims * 100
        
        # Determine most likely league and certainty
        if p1 >= p2:
            most_likely = "League 1"
            certainty = p1
        else:
            most_likely = "League 2"
            certainty = p2
        
        certainties.append(certainty)
        
        if p1 > 0.1 or p2 > 0.1:
            print(f"{team:<24} {most_likely:>12} {certainty:>10.1f}% {p1:>7.1f}% {p2:>7.1f}%")
    
    # Calculate and display average certainty
    avg_certainty = sum(certainties) / len(certainties)
    median_certainty = sorted(certainties)[len(certainties) // 2]
    min_certainty = min(certainties)
    max_certainty = max(certainties)
    
    print("-" * 65)
    print(f"\n=== LEAGUE ALLOCATION CERTAINTY ===")
    print(f"Average Certainty: {avg_certainty:.2f}%")
    print(f"Median Certainty:  {median_certainty:.2f}%")
    print(f"Range:             {min_certainty:.2f}% - {max_certainty:.2f}%")
    print(f"\nThe league allocation is {avg_certainty:.1f}% 'solved'")
    
    # Show most uncertain teams
    teams_with_certs = [(team, max(wc1.get(team, 0) / n_sims * 100, 
                                     wc2.get(team, 0) / n_sims * 100)) 
                        for team in ALL_TEAMS]
    teams_with_certs.sort(key=lambda x: x[1])
    
    print(f"\n=== MOST UNCERTAIN TEAMS (Bottom 5) ===")
    for team, cert in teams_with_certs[:5]:
        print(f"{team:<24} {cert:>6.2f}%")


def main():
    print(f"=== UEFA NATIONS LEAGUE 2026-2029 SIMULATION ===")
    print(f"Sims: {N_SIMS:,} | Seed: {RANDOM_SEED}")
    
    rank_counts, wc1, wc2 = run_full_simulation(N_SIMS, seed=RANDOM_SEED)
    
    print_most_likely_ranking(rank_counts, N_SIMS)
    print_wc_summary_with_certainty(wc1, wc2, N_SIMS)

if __name__ == "__main__":
    main()