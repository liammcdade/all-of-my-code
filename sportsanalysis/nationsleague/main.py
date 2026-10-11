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
# CONFIG
# ============================================================
MODE = "transitional"
N_SIMS = 10_000
RANDOM_SEED = 42
HOME_ADV = 108.80
BASE_XG = 1.35222
XG_ELO_SCALE = 600.0
ELO_SCALE = 400
MAX_XG = 3.5
HIST_WEIGHT = 0.30
HIST_PRIOR_MATCHES = 60.0

# ============================================================
# DISCIPLINARY POINTS
# ============================================================
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

# ============================================================
# FIXED RESULTS
# ============================================================
FIXED_RESULTS = {
    # Matchday 1 of 6
    ("Andorra", "Malta"): (1, 2),
    ("Norway", "Denmark"): (3, 2),
    ("Liechtenstein", "Lithuania"): (0, 2),
    ("Kosovo", "Republic of Ireland"): (1, 0),
    ("Netherlands", "Germany"): (1, 1),
    ("Austria", "Israel"): (3, 1),
    ("Portugal", "Wales"): (1, 0),
    ("Serbia", "Greece"): (1, 2),
    ("Georgia", "Northern Ireland"): (0, 1),
    ("Armenia", "Latvia"): (2, 0),
    ("Sweden", "Romania"): (2, 1),
    ("Montenegro", "Cyprus"): (2, 1),
    ("Hungary", "Ukraine"): (0, 1),
    ("Italy", "Belgium"): (0, 2),
    ("Türkiye", "France"): (0, 1),
    ("Poland", "Bosnia and Herzegovina"): (0, 0),
    ("Slovenia", "Scotland"): (0, 0),
    ("Faroe Islands", "Kazakhstan"): (1, 1),
    ("San Marino", "Finland"): (0, 7),
    ("Iceland", "Estonia"): (1, 1),
    ("Bulgaria", "Luxembourg"): (1, 2),
    ("Czechia", "Croatia"): (1, 2),
    ("North Macedonia", "Switzerland"): (0, 3),
    ("England", "Spain"): (2, 3),
    ("Slovakia", "Moldova"): (2, 0),
    ("Albania", "Belarus"): (2, 0),

    # Matchday 2 of 6
    ("Lithuania", "Azerbaijan"): (1, 1),
    ("Serbia", "Netherlands"): (1, 2),
    ("Gibraltar", "Andorra"): (0, 0),
    ("Austria", "Kosovo"): (3, 1),
    ("Denmark", "Wales"): (2, 0),
    ("Norway", "Portugal"): (1, 2),
    ("Israel", "Republic of Ireland"): (0, 3),
    ("Germany", "Greece"): (0, 1),
    ("Latvia", "Cyprus"): (0, 0),
    ("Georgia", "Ukraine"): (0, 0),
    ("Armenia", "Montenegro"): (2, 3),
    ("Romania", "Bosnia and Herzegovina"): (2, 4),
    ("Türkiye", "Italy"): (1, 4),
    ("Belgium", "France"): (0, 1),
    ("Northern Ireland", "Hungary"): (0, 0),
    ("Sweden", "Poland"): (3, 1),
    ("Finland", "Belarus"): (0, 0),
    ("Moldova", "Faroe Islands"): (1, 1),
    ("Spain", "Croatia"): (4, 1),
    ("Luxembourg", "Iceland"): (0, 3),
    ("Slovakia", "Kazakhstan"): (2, 1),
    ("Czechia", "England"): (0, 2),
    ("Slovenia", "North Macedonia"): (2, 0),
    ("Bulgaria", "Estonia"): (0, 0),
    ("San Marino", "Albania"): (0, 3),
    ("Scotland", "Switzerland"): (0, 3),

    # Matchday 3 of 6
    ("Azerbaijan", "Liechtenstein"): (0, 0),
    ("Israel", "Kosovo"): (0, 0),
    ("Greece", "Netherlands"): (2, 2),
    ("Germany", "Serbia"): (2, 0),
    ("Republic of Ireland", "Austria"): (2, 2),
    ("Wales", "Norway"): (2, 1),
    ("Malta", "Gibraltar"): (1, 1),
    ("Denmark", "Portugal"): (2, 4),
    ("Kazakhstan", "Moldova"): (1, 2),
    ("Cyprus", "Armenia"): (2, 0),
    ("Latvia", "Montenegro"): (1, 2),
    ("Ukraine", "Northern Ireland"): (0, 3),
    ("Poland", "Romania"): (6, 0),
    ("Faroe Islands", "Slovakia"): (1, 1),
    ("Belgium", "Türkiye"): (3, 0),
    ("Hungary", "Georgia"): (1, 0),
    ("Bosnia and Herzegovina", "Sweden"): (1, 1),
    ("France", "Italy"): (1, 1),
    ("Finland", "Albania"): (2, 1),
    ("Iceland", "Bulgaria"): (3, 0),
    ("Belarus", "San Marino"): (4, 0),
    ("Croatia", "England"): (0, 7),
    ("Estonia", "Luxembourg"): (1, 0),
    ("Switzerland", "Slovenia"): (2, 1),
    ("North Macedonia", "Scotland"): (0, 2),
    ("Spain", "Czechia"): (3, 1),

    # Matchday 4 of 6
    ("Azerbaijan", "Lithuania"): (1, 0),
    ("Kosovo", "Austria"): (1, 1),
    ("Malta", "Andorra"): (1, 0),
    ("Greece", "Germany"): (0, 0),
    ("Netherlands", "Serbia"): (2, 1),
    ("Portugal", "Norway"): (2, 1),
    ("Wales", "Denmark"): (0, 1),
    ("Republic of Ireland", "Israel"): (1, 1),
    ("Cyprus", "Latvia"): (2, 1),
    ("Italy", "Türkiye"): (3, 1),
    ("Romania", "Sweden"): (0, 1),
    ("Bosnia and Herzegovina", "Poland"): (1, 0),
    ("France", "Belgium"): (4, 1),
    ("Montenegro", "Armenia"): (0, 0),
    ("Ukraine", "Hungary"): (1, 2),
    ("Northern Ireland", "Georgia"): (0, 0),
    ("Kazakhstan", "Faroe Islands"): (2, 2),
    ("Croatia", "Spain"): (1, 2),
    ("Moldova", "Slovakia"): (0, 4),
    ("Luxembourg", "Bulgaria"): (0, 2),
    ("Belarus", "Finland"): (1, 0),
    ("Albania", "San Marino"): (2, 1),
    ("Estonia", "Iceland"): (0, 0),
    ("England", "Czechia"): (3, 0),
    ("Switzerland", "North Macedonia"): (3, 0),
    ("Scotland", "Slovenia"): (1, 2),
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

MARKET_VALUES = {
    "France": 1_450_000_000, "England": 1_490_000_000, "Spain": 1_350_000_000,
    "Germany": 1_390_000_000, "Portugal": 1_000_000_000, "Italy": 871_500_000,
    "Netherlands": 811_000_000, "Norway": 518_100_000, "Belgium": 594_800_000,
    "Croatia": 434_900_000, "Denmark": 418_500_000, "Sweden": 425_800_000,
    "Türkiye": 411_000_000, "Greece": 320_600_000, "Switzerland": 294_400_000,
    "Serbia": 289_600_000, "Russia": 265_300_000, "Georgia": 261_950_000,
    "Poland": 259_500_000, "Ukraine": 259_400_000, "Austria": 250_500_000,
    "Republic of Ireland": 188_900_000, "Hungary": 187_750_000,
    "Slovenia": 181_800_000, "Wales": 180_100_000, "Czechia": 179_200_000,
    "Scotland": 161_300_000, "Bosnia and Herzegovina": 154_200_000,
    "Kosovo": 143_850_000, "Romania": 123_500_000, "Israel": 104_830_000,
    "Northern Ireland": 103_700_000, "Albania": 99_180_000, "Iceland": 92_500_000,
    "Montenegro": 82_180_000, "Slovakia": 69_530_000, "Finland": 50_900_000,
    "Armenia": 45_330_000, "Bulgaria": 40_400_000, "North Macedonia": 36_580_000,
    "Luxembourg": 31_180_000, "Cyprus": 25_130_000, "Lithuania": 21_130_000,
    "Belarus": 19_600_000, "Kazakhstan": 18_880_000, "Azerbaijan": 16_380_000,
    "Malta": 15_750_000, "Estonia": 14_900_000, "Latvia": 14_830_000,
    "Moldova": 10_180_000, "Faroe Islands": 5_780_000, "Andorra": 3_410_000,
    "Gibraltar": 2_030_000, "San Marino": 1_220_000, "Liechtenstein": 625_000,
}

TEAM_HOME_AWAY_GOALS: Dict[str, Dict[str, float]] = {
    "France": {"matches_home": 544, "goals_home": 1134, "avg_home": 2.085, "matches_away": 399, "goals_away": 601, "avg_away": 1.506, "total_goals": 1735},
    "Italy": {"matches_home": 492, "goals_home": 1019, "avg_home": 2.071, "matches_away": 401, "goals_away": 546, "avg_away": 1.362, "total_goals": 1565},
    "Belgium": {"matches_home": 458, "goals_home": 958, "avg_home": 2.092, "matches_away": 401, "goals_away": 606, "avg_away": 1.511, "total_goals": 1564},
    "Türkiye": {"matches_home": 306, "goals_home": 482, "avg_home": 1.575, "matches_away": 339, "goals_away": 420, "avg_away": 1.239, "total_goals": 902},
    "Germany": {"matches_home": 557, "goals_home": 1394, "avg_home": 2.503, "matches_away": 478, "goals_away": 937, "avg_away": 1.960, "total_goals": 2331},
    "Netherlands": {"matches_home": 479, "goals_home": 1146, "avg_home": 2.392, "matches_away": 404, "goals_away": 706, "avg_away": 1.748, "total_goals": 1852},
    "Serbia": {"matches_home": 135, "goals_home": 250, "avg_home": 1.852, "matches_away": 213, "goals_away": 281, "avg_away": 1.319, "total_goals": 531},
    "Greece": {"matches_home": 321, "goals_home": 478, "avg_home": 1.489, "matches_away": 312, "goals_away": 316, "avg_away": 1.013, "total_goals": 794},
    "Spain": {"matches_home": 414, "goals_home": 987, "avg_home": 2.384, "matches_away": 377, "goals_away": 629, "avg_away": 1.668, "total_goals": 1616},
    "Croatia": {"matches_home": 193, "goals_home": 390, "avg_home": 2.021, "matches_away": 207, "goals_away": 304, "avg_away": 1.469, "total_goals": 694},
    "England": {"matches_home": 554, "goals_home": 1261, "avg_home": 2.276, "matches_away": 544, "goals_away": 1140, "avg_away": 2.096, "total_goals": 2401},
    "Czechia": {"matches_home": 178, "goals_home": 380, "avg_home": 2.135, "matches_away": 185, "goals_away": 265, "avg_away": 1.432, "total_goals": 645},
    "Portugal": {"matches_home": 373, "goals_home": 788, "avg_home": 2.113, "matches_away": 327, "goals_away": 447, "avg_away": 1.367, "total_goals": 1235},
    "Denmark": {"matches_home": 447, "goals_home": 961, "avg_home": 2.150, "matches_away": 427, "goals_away": 626, "avg_away": 1.466, "total_goals": 1587},
    "Norway": {"matches_home": 439, "goals_home": 747, "avg_home": 1.702, "matches_away": 439, "goals_away": 617, "avg_away": 1.405, "total_goals": 1364},
    "Wales": {"matches_home": 360, "goals_home": 526, "avg_home": 1.461, "matches_away": 366, "goals_away": 384, "avg_away": 1.049, "total_goals": 910},
    "Scotland": {"matches_home": 417, "goals_home": 788, "avg_home": 1.890, "matches_away": 437, "goals_away": 667, "avg_away": 1.526, "total_goals": 1455},
    "Switzerland": {"matches_home": 449, "goals_home": 789, "avg_home": 1.757, "matches_away": 441, "goals_away": 541, "avg_away": 1.227, "total_goals": 1330},
    "Slovenia": {"matches_home": 155, "goals_home": 223, "avg_home": 1.439, "matches_away": 162, "goals_away": 169, "avg_away": 1.043, "total_goals": 392},
    "North Macedonia": {"matches_home": 151, "goals_home": 206, "avg_home": 1.364, "matches_away": 155, "goals_away": 159, "avg_away": 1.026, "total_goals": 365},
    "Hungary": {"matches_home": 499, "goals_home": 1135, "avg_home": 2.275, "matches_away": 507, "goals_away": 876, "avg_away": 1.728, "total_goals": 2011},
    "Ukraine": {"matches_home": 163, "goals_home": 245, "avg_home": 1.503, "matches_away": 175, "goals_away": 230, "avg_away": 1.314, "total_goals": 475},
    "Georgia": {"matches_home": 145, "goals_home": 217, "avg_home": 1.497, "matches_away": 162, "goals_away": 166, "avg_away": 1.025, "total_goals": 383},
    "Northern Ireland": {"matches_home": 339, "goals_home": 429, "avg_home": 1.265, "matches_away": 368, "goals_away": 312, "avg_away": 0.848, "total_goals": 741},
    "Israel": {"matches_home": 277, "goals_home": 469, "avg_home": 1.693, "matches_away": 221, "goals_away": 281, "avg_away": 1.271, "total_goals": 750},
    "Austria": {"matches_home": 462, "goals_home": 928, "avg_home": 2.009, "matches_away": 402, "goals_away": 619, "avg_away": 1.540, "total_goals": 1547},
    "Republic of Ireland": {"matches_home": 346, "goals_home": 533, "avg_home": 1.540, "matches_away": 287, "goals_away": 325, "avg_away": 1.132, "total_goals": 858},
    "Kosovo": {"matches_home": 60, "goals_home": 97, "avg_home": 1.617, "matches_away": 46, "goals_away": 59, "avg_away": 1.283, "total_goals": 156},
    "Poland": {"matches_home": 429, "goals_home": 832, "avg_home": 1.939, "matches_away": 463, "goals_away": 667, "avg_away": 1.441, "total_goals": 1499},
    "Bosnia and Herzegovina": {"matches_home": 137, "goals_home": 209, "avg_home": 1.526, "matches_away": 150, "goals_away": 184, "avg_away": 1.227, "total_goals": 393},
    "Romania": {"matches_home": 363, "goals_home": 705, "avg_home": 1.942, "matches_away": 403, "goals_away": 534, "avg_away": 1.325, "total_goals": 1239},
    "Sweden": {"matches_home": 535, "goals_home": 1247, "avg_home": 2.331, "matches_away": 570, "goals_away": 931, "avg_away": 1.633, "total_goals": 2178},
    "Albania": {"matches_home": 210, "goals_home": 239, "avg_home": 1.138, "matches_away": 188, "goals_away": 138, "avg_away": 0.734, "total_goals": 377},
    "Finland": {"matches_home": 362, "goals_home": 524, "avg_home": 1.448, "matches_away": 456, "goals_away": 436, "avg_away": 0.956, "total_goals": 960},
    "Belarus": {"matches_home": 145, "goals_home": 184, "avg_home": 1.269, "matches_away": 170, "goals_away": 179, "avg_away": 1.053, "total_goals": 363},
    "San Marino": {"matches_home": 114, "goals_home": 26, "avg_home": 0.228, "matches_away": 111, "goals_away": 18, "avg_away": 0.162, "total_goals": 44},
    "Montenegro": {"matches_home": 91, "goals_home": 126, "avg_home": 1.385, "matches_away": 79, "goals_away": 75, "avg_away": 0.949, "total_goals": 201},
    "Armenia": {"matches_home": 133, "goals_home": 150, "avg_home": 1.128, "matches_away": 139, "goals_away": 124, "avg_away": 0.892, "total_goals": 274},
    "Cyprus": {"matches_home": 234, "goals_home": 251, "avg_home": 1.073, "matches_away": 192, "goals_away": 124, "avg_away": 0.646, "total_goals": 375},
    "Latvia": {"matches_home": 225, "goals_home": 287, "avg_home": 1.276, "matches_away": 236, "goals_away": 254, "avg_away": 1.076, "total_goals": 541},
    "Kazakhstan": {"matches_home": 125, "goals_home": 174, "avg_home": 1.392, "matches_away": 144, "goals_away": 135, "avg_away": 0.938, "total_goals": 309},
    "Slovakia": {"matches_home": 168, "goals_home": 278, "avg_home": 1.655, "matches_away": 199, "goals_away": 240, "avg_away": 1.206, "total_goals": 518},
    "Faroe Islands": {"matches_home": 140, "goals_home": 153, "avg_home": 1.093, "matches_away": 147, "goals_away": 87, "avg_away": 0.592, "total_goals": 240},
    "Moldova": {"matches_home": 132, "goals_home": 126, "avg_home": 0.955, "matches_away": 167, "goals_away": 117, "avg_away": 0.701, "total_goals": 243},
    "Iceland": {"matches_home": 236, "goals_home": 322, "avg_home": 1.364, "matches_away": 286, "goals_away": 310, "avg_away": 1.084, "total_goals": 632},
    "Bulgaria": {"matches_home": 326, "goals_home": 560, "avg_home": 1.718, "matches_away": 410, "goals_away": 456, "avg_away": 1.112, "total_goals": 1016},
    "Estonia": {"matches_home": 268, "goals_home": 304, "avg_home": 1.134, "matches_away": 282, "goals_away": 240, "avg_away": 0.851, "total_goals": 544},
    "Luxembourg": {"matches_home": 255, "goals_home": 180, "avg_home": 0.706, "matches_away": 212, "goals_away": 116, "avg_away": 0.547, "total_goals": 296},
    "Gibraltar": {"matches_home": 89, "goals_home": 114, "avg_home": 1.281, "matches_away": 70, "goals_away": 63, "avg_away": 0.900, "total_goals": 177},
    "Malta": {"matches_home": 254, "goals_home": 208, "avg_home": 0.819, "matches_away": 204, "goals_away": 90, "avg_away": 0.441, "total_goals": 298},
    "Andorra": {"matches_home": 115, "goals_home": 44, "avg_home": 0.383, "matches_away": 114, "goals_away": 31, "avg_away": 0.272, "total_goals": 75},
    "Lithuania": {"matches_home": 184, "goals_home": 207, "avg_home": 1.125, "matches_away": 249, "goals_away": 224, "avg_away": 0.900, "total_goals": 431},
    "Azerbaijan": {"matches_home": 152, "goals_home": 141, "avg_home": 0.928, "matches_away": 158, "goals_away": 97, "avg_away": 0.614, "total_goals": 238},
    "Liechtenstein": {"matches_home": 121, "goals_home": 50, "avg_home": 0.413, "matches_away": 138, "goals_away": 55, "avg_away": 0.399, "total_goals": 105},
}

LEAGUES = {
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

ALL_TEAMS = [t for lg in LEAGUES.values() for grp in lg["groups"].values() for t in grp]

for t in ALL_TEAMS:
    if t not in ELO_RATINGS:              raise ValueError(f"Missing Elo: {t}")
    if t not in MARKET_VALUES:            raise ValueError(f"Missing MV: {t}")
    if t not in TEAM_HOME_AWAY_GOALS:     raise ValueError(f"Missing HA: {t}")
    if t not in DISCIPLINE_POINTS:        DISCIPLINE_POINTS[t] = 0

# ============================================================
# ELO / xG MODELLING
# ============================================================
def effective_elo(team: str) -> float:
    return float(ELO_RATINGS[team])

_total_mh = sum(TEAM_HOME_AWAY_GOALS[t]["matches_home"] for t in ALL_TEAMS)
_total_gh = sum(TEAM_HOME_AWAY_GOALS[t]["goals_home"]   for t in ALL_TEAMS)
_total_ma = sum(TEAM_HOME_AWAY_GOALS[t]["matches_away"] for t in ALL_TEAMS)
_total_ga = sum(TEAM_HOME_AWAY_GOALS[t]["goals_away"]   for t in ALL_TEAMS)

GLOBAL_AVG_HOME = _total_gh / _total_mh
GLOBAL_AVG_AWAY = _total_ga / _total_ma

def _attack_modifier(team: str, is_home: bool) -> float:
    s = TEAM_HOME_AWAY_GOALS[team]
    n, g, ref = (
        (s["matches_home"], s["goals_home"], GLOBAL_AVG_HOME)
        if is_home
        else (s["matches_away"], s["goals_away"], GLOBAL_AVG_AWAY)
    )
    if n == 0:
        return 1.0
    shrunk = (n * (g / n) + HIST_PRIOR_MATCHES * ref) / (n + HIST_PRIOR_MATCHES)
    return shrunk / ref

HOME_ATTACK_MOD = {t: _attack_modifier(t, True)  for t in ALL_TEAMS}
AWAY_ATTACK_MOD = {t: _attack_modifier(t, False) for t in ALL_TEAMS}

def poisson_rand(lam: float, rng: random.Random) -> int:
    if lam <= 0: return 0
    L, k, p = math.exp(-lam), 0, 1.0
    while True:
        k += 1
        p *= rng.random()
        if p <= L:
            return k - 1

def poisson_pmf(k: int, lam: float) -> float:
    if lam <= 0: return 1.0 if k == 0 else 0.0
    return math.exp(-lam) * (lam ** k) / math.factorial(k)

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
    h1, a1 = simulate_match(lower, higher, rng)
    h2, a2 = simulate_match(higher, lower, rng)
    agg_h, agg_l = a1 + h2, h1 + a2
    if agg_h > agg_l: return higher
    if agg_l > agg_h: return lower
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
# TIE-BREAK TRACKER
# ============================================================
class TieBreakTracker:
    def __init__(self):
        self.n_sims = 0
        self.step_used_in_sim = [0] * 12
        self.steps_per_sim: List[int] = []
        self._current: Set[int] = set()

    def new_sim(self):
        self._current = set()
        self.n_sims += 1

    def record(self, step: int):
        self._current.add(step)

    def end_sim(self):
        for s in self._current:
            self.step_used_in_sim[s] += 1
        self.steps_per_sim.append(len(self._current))

    def report(self):
        desc = {
            1:  "H2H points (mini-table)",
            2:  "H2H goal difference",
            3:  "H2H goals scored",
            4:  "Reapply steps 1-3 to still-tied teams",
            5:  "Overall goal difference",
            6:  "Overall goals scored",
            7:  "Overall away goals scored",
            8:  "Total wins",
            9:  "Total away wins",
            10: "Disciplinary points (lower = better)",
            11: "Access List position",
        }
        n = max(self.n_sims, 1)
        print("\n=== UEFA 11-STEP TIE-BREAK USAGE ===")
        print(f"{'Step':<5} {'Description':<44} {'Sims':>7} {'%':>8}")
        for s in range(1, 12):
            c = self.step_used_in_sim[s]
            print(f"{s:<5} {desc[s]:<44} {c:>7} {c/n*100:>7.2f}%")
        avg = (sum(self.steps_per_sim) / len(self.steps_per_sim)) if self.steps_per_sim else 0.0
        print(f"\nAverage steps used per simulation: {avg:.3f} / 11  "
              f"({avg/11*100:.2f}% of the rulebook)")

# ============================================================
# GROUP STANDINGS  —  full 11-step UEFA tie-breaker
# ============================================================
def _h2h_table(subset, results):
    s = set(subset)
    h2h = {t: {"pts": 0, "gd": 0, "gf": 0} for t in subset}
    for home, away, hg, ag in results:
        if home in s and away in s:
            h2h[home]["gf"] += hg
            h2h[home]["gd"] += hg - ag
            h2h[away]["gf"] += ag
            h2h[away]["gd"] += ag - hg
            if hg > ag:      h2h[home]["pts"] += 3
            elif ag > hg:    h2h[away]["pts"] += 3
            else:            h2h[home]["pts"] += 1; h2h[away]["pts"] += 1
    return h2h

def _resolve_steps_5_11(tied, stats, access_order, tracker):
    if len(tied) <= 1:
        return list(tied)
    keys = [
        (5,  lambda t: stats[t]["gd"]),
        (6,  lambda t: stats[t]["gf"]),
        (7,  lambda t: stats[t]["away_gf"]),
        (8,  lambda t: stats[t]["won"]),
        (9,  lambda t: stats[t]["away_won"]),
        (10, lambda t: -stats[t]["disc_points"]),
    ]
    still_tied = list(tied)
    for step, fn in keys:
        if len(still_tied) <= 1:
            break
        vals = [fn(t) for t in still_tied]
        if len(set(vals)) == 1:
            continue
        tracker.record(step)
        counts = Counter(vals)
        still_tied = [t for t in still_tied if counts[fn(t)] > 1]
    if len(still_tied) > 1:
        tracker.record(11)
    return sorted(tied, key=lambda t: (
        -stats[t]["gd"], -stats[t]["gf"], -stats[t]["away_gf"],
        -stats[t]["won"], -stats[t]["away_won"],
        stats[t]["disc_points"], access_order[t],
    ))

def resolve_tie_group(tied, results, stats, access_order, tracker, depth=0):
    if len(tied) <= 1:
        return list(tied)
    if depth > 6:
        return sorted(tied, key=lambda t: access_order[t])
    h2h = _h2h_table(tied, results)
    def key(t):
        return (-h2h[t]["pts"], -h2h[t]["gd"], -h2h[t]["gf"])
    sorted_teams = sorted(tied, key=key)
    groups = [list(g) for _, g in groupby(sorted_teams, key=key)]
    if len(groups) == 1:
        return _resolve_steps_5_11(tied, stats, access_order, tracker)
    if len({h2h[t]["pts"] for t in tied}) > 1:   tracker.record(1)
    elif len({h2h[t]["gd"] for t in tied}) > 1:  tracker.record(2)
    else:                                        tracker.record(3)
    out: List[str] = []
    for g in groups:
        if len(g) == 1:
            out.append(g[0])
        else:
            out.extend(resolve_tie_group(g, results, stats, access_order, tracker, depth + 1))
    return out

def calculate_group_standings(teams, results, tracker=None, access_order=None):
    stats = {
        t: {"team": t, "played": 0, "won": 0, "drawn": 0, "lost": 0,
            "gf": 0, "ga": 0, "gd": 0, "points": 0,
            "away_gf": 0, "away_won": 0,
            "disc_points": DISCIPLINE_POINTS.get(t, 0)}
        for t in teams
    }
    if access_order is None:
        access_order = {t: i for i, t in enumerate(teams)}
    for home, away, hg, ag in results:
        stats[home]["played"] += 1
        stats[away]["played"] += 1
        stats[home]["gf"] += hg
        stats[home]["ga"] += ag
        stats[away]["gf"] += ag
        stats[away]["ga"] += hg
        stats[away]["away_gf"] += ag
        if hg > ag:
            stats[home]["won"] += 1; stats[home]["points"] += 3; stats[away]["lost"] += 1
        elif hg < ag:
            stats[away]["won"] += 1; stats[away]["away_won"] += 1
            stats[away]["points"] += 3; stats[home]["lost"] += 1
        else:
            stats[home]["drawn"] += 1; stats[away]["drawn"] += 1
            stats[home]["points"] += 1; stats[away]["points"] += 1
    for t in stats:
        stats[t]["gd"] = stats[t]["gf"] - stats[t]["ga"]
    by_pts = sorted(teams, key=lambda t: -stats[t]["points"])
    order: List[str] = []
    for _, grp in groupby(by_pts, key=lambda t: stats[t]["points"]):
        grp = list(grp)
        if len(grp) == 1:
            order.extend(grp); continue
        if tracker is not None:
            order.extend(resolve_tie_group(grp, results, stats, access_order, tracker))
        else:
            h2h = _h2h_table(grp, results)
            grp.sort(key=lambda t: (-h2h[t]["pts"], -h2h[t]["gd"], -h2h[t]["gf"],
                                    -stats[t]["gd"], -stats[t]["gf"]))
            order.extend(grp)
    return [stats[t] for t in order]

# ============================================================
# LEAGUE PHASE
# ============================================================
def simulate_league_phase(rng, tracker=None):
    gres, gstand, tpos, gwinners = {}, {}, {}, {}
    for lg_name, lg in LEAGUES.items():
        for gname, teams in lg["groups"].items():
            access_order = {t: i for i, t in enumerate(teams)}
            matches = (
                [(a, b) for i, a in enumerate(teams) for b in teams[i + 1:]] +
                [(b, a) for i, a in enumerate(teams) for b in teams[i + 1:]]
            )
            results = []
            for h, a in matches:
                if (h, a) in FIXED_RESULTS:
                    hg, ag = FIXED_RESULTS[(h, a)]
                else:
                    hg, ag = simulate_match(h, a, rng)
                results.append((h, a, hg, ag))
            st = calculate_group_standings(teams, results,
                                           tracker=tracker,
                                           access_order=access_order)
            gres[gname] = results
            gstand[gname] = st
            gwinners[gname] = st[0]["team"]
            for pos, e in enumerate(st, 1):
                tpos[e["team"]] = pos
    return {
        "group_results": gres,
        "group_standings": gstand,
        "team_positions": tpos,
        "group_winners": gwinners,
    }

def determine_league_rankings(gstand):
    rankings = {}
    for lg in LEAGUES:
        entries = [e for gname, st in gstand.items() if gname[0] == lg for e in st]
        entries.sort(key=lambda e: (-e["points"], -e["gd"], -e["gf"]))
        rankings[lg] = [e["team"] for e in entries]
    return rankings

# ============================================================
# PROMOTION / RELEGATION
# ============================================================
def simulate_promotion_relegation(league_rankings, group_standings, rng, mode=MODE):
    promoted_direct, promoted_via_playoff, relegated_direct, relegated_via_playoff = set(), set(), set(), set()
    safe_direct, safe_via_playoff = set(), set()
    ab_winners, ab_losers, bc_winners, bc_losers, cd_winners, cd_losers = set(), set(), set(), set(), set(), set()
    lg_g = {"A": [], "B": [], "C": [], "D": []}
    for gname, st in group_standings.items():
        lg_g[gname[0]].append(st)
    A = {str(i + 1): {s[i]["team"] for s in lg_g["A"]} for i in range(4)}
    B = {str(i + 1): {s[i]["team"] for s in lg_g["B"]} for i in range(4)}
    C = {str(i + 1): {s[i]["team"] for s in lg_g["C"]} for i in range(4)}
    D = {str(i + 1): {s[i]["team"] for s in lg_g["D"]} for i in range(3)}

    promoted_direct |= B["1"] | C["1"]
    relegated_direct |= A["4"] | B["4"]
    safe_direct |= A["1"] | A["2"]

    a3, b2 = list(A["3"]), list(B["2"])
    rng.shuffle(a3); rng.shuffle(b2)
    for i in range(4):
        seed, unseed = a3[i], b2[i]
        w = simulate_two_legged_tie(seed, unseed, rng)
        if w == seed:
            ab_winners.add(seed); safe_via_playoff.add(seed)
            ab_losers.add(unseed); safe_via_playoff.add(unseed)
        else:
            ab_winners.add(unseed); promoted_via_playoff.add(unseed)
            ab_losers.add(seed); relegated_via_playoff.add(seed)

    b3, c2 = list(B["3"]), list(C["2"])
    rng.shuffle(b3); rng.shuffle(c2)
    for i in range(4):
        seed, unseed = b3[i], c2[i]
        w = simulate_two_legged_tie(seed, unseed, rng)
        if w == seed:
            bc_winners.add(seed); safe_via_playoff.add(seed)
            bc_losers.add(unseed); safe_via_playoff.add(unseed)
        else:
            bc_winners.add(unseed); promoted_via_playoff.add(unseed)
            bc_losers.add(seed); relegated_via_playoff.add(seed)

    if mode == "transitional":
        b2_sorted = sorted(list(B["2"]), key=lambda t: league_rankings["B"].index(t))
        b2_top2, b2_bottom2 = set(b2_sorted[:2]), set(b2_sorted[2:])
        next_league = {}
        for t in A["1"] | A["2"] | A["3"] | B["1"] | b2_top2: next_league[t] = "A"
        for t in A["4"] | b2_bottom2 | B["3"] | C["1"] | C["2"]:  next_league[t] = "B"
        for t in B["4"] | C["3"] | C["4"] | D["1"] | D["2"] | D["3"]: next_league[t] = "C"
        current_league = {t: lg_name for lg_name, lg in LEAGUES.items()
                          for grp in lg["groups"].values() for t in grp}
        league_order = {"A": 3, "B": 2, "C": 1, "D": 0}
        promoted_direct, promoted_via_playoff, relegated_direct, relegated_via_playoff, safe_direct, safe_via_playoff = set(), set(), set(), set(), set(), set()
        for t in ALL_TEAMS:
            cur, nxt = league_order[current_league[t]], league_order[next_league[t]]
            if nxt > cur:      promoted_direct.add(t)
            elif nxt < cur:    relegated_direct.add(t)
            else:              safe_direct.add(t)
        expected_sizes = {"A": 18, "B": 18, "C": 18, "D": 0}
    elif mode == "standard":
        c4_sorted = sorted(C["4"], key=lambda t: league_rankings["C"].index(t))
        c4_playoff, c4_auto_relegated = set(c4_sorted[:2]), set(c4_sorted[-2:])
        relegated_direct |= c4_auto_relegated
        c4p, d2 = list(c4_playoff), list(D["2"])
        rng.shuffle(c4p); rng.shuffle(d2)
        for i in range(2):
            seed, unseed = c4p[i], d2[i]
            w = simulate_two_legged_tie(seed, unseed, rng)
            if w == seed:
                cd_winners.add(seed); safe_via_playoff.add(seed)
                cd_losers.add(unseed); safe_via_playoff.add(unseed)
            else:
                cd_winners.add(unseed); promoted_via_playoff.add(unseed)
                cd_losers.add(seed); relegated_via_playoff.add(seed)
        promoted_direct |= D["1"]
        safe_direct |= C["3"] | D["3"]
        next_league = {}
        for t in A["1"] | A["2"]:              next_league[t] = "A"
        for t in B["1"] | ab_winners:          next_league[t] = "A"
        for t in A["4"] | ab_losers:           next_league[t] = "B"
        for t in bc_winners | C["1"]:          next_league[t] = "B"
        for t in B["4"] | bc_losers:           next_league[t] = "C"
        for t in cd_winners | C["3"] | D["1"]: next_league[t] = "C"
        for t in c4_auto_relegated | cd_losers | D["3"]: next_league[t] = "D"
        expected_sizes = {"A": 16, "B": 16, "C": 16, "D": 6}
    else:
        raise ValueError(f"Unknown mode: {mode}")

    counts = Counter(next_league.values())
    for lg, exp in expected_sizes.items():
        if counts.get(lg, 0) != exp:
            raise ValueError(f"Size mismatch {lg}: {counts.get(lg, 0)} != {exp}")

    euro_pool = ab_winners | bc_winners if mode == "transitional" else ab_winners | bc_winners | cd_winners

    return {
        "promoted": promoted_direct | promoted_via_playoff,
        "relegated": relegated_direct | relegated_via_playoff,
        "promoted_direct": promoted_direct,
        "promoted_via_playoff": promoted_via_playoff,
        "relegated_direct": relegated_direct,
        "relegated_via_playoff": relegated_via_playoff,
        "safe_direct": safe_direct,
        "safe_via_playoff": safe_via_playoff,
        "stay": safe_direct | safe_via_playoff,
        "euro_pool": euro_pool,
        "next_league": next_league,
    }

# ============================================================
# KNOCKOUT
# ============================================================
def simulate_knockout_stage(group_standings, rng):
    seeds = [group_standings[f"A{i}"][0]["team"] for i in range(1, 5)]
    unseeded = [group_standings[f"A{i}"][1]["team"] for i in range(1, 5)]
    rng.shuffle(seeds); rng.shuffle(unseeded)
    qf_pairs = [(seeds[i], unseeded[i]) for i in range(4)]
    semis = [simulate_two_legged_tie(s, u, rng) for s, u in qf_pairs]
    rng.shuffle(semis)
    sf1 = neutral_match(semis[0], semis[1], rng)
    sf2 = neutral_match(semis[2], semis[3], rng)
    sf1_l = semis[1] if sf1 == semis[0] else semis[0]
    sf2_l = semis[3] if sf2 == semis[2] else semis[2]
    return {
        "quarter_finalists": [t for p in qf_pairs for t in p],
        "semi_finalists": semis,
        "finalists": [sf1, sf2],
        "winner": neutral_match(sf1, sf2, rng),
        "third_place": neutral_match(sf1_l, sf2_l, rng),
    }

def compute_final_ranking(group_standings, pr, ko):
    next_league = pr["next_league"]
    current_league = {t: lg_name for lg_name, lg in LEAGUES.items()
                      for grp in lg["groups"].values() for t in grp}
    team_info = {e["team"]: {"pos": pos, "points": e["points"], "gd": e["gd"], "gf": e["gf"]}
                 for st in group_standings.values() for pos, e in enumerate(st, 1)}
    league_level = {"A": 4, "B": 3, "C": 2, "D": 1}
    final_ranking = []
    for lg in ["A", "B", "C"]:
        teams = [t for t in ALL_TEAMS if next_league.get(t) == lg]
        teams.sort(key=lambda t: (
            -league_level[current_league[t]],
            team_info[t]["pos"],
            -team_info[t]["points"],
            -team_info[t]["gd"],
            -team_info[t]["gf"],
        ))
        final_ranking.extend(teams)
    winner, finalists = ko["winner"], ko["finalists"]
    runner_up = [t for t in finalists if t != winner][0]
    third, semi = ko["third_place"], ko["semi_finalists"]
    fourth = [t for t in semi if t not in finalists and t != third][0]
    qf_losers = sorted(
        [t for t in ko["quarter_finalists"] if t not in semi],
        key=lambda t: (team_info[t]["pos"], -team_info[t]["points"],
                       -team_info[t]["gd"], -team_info[t]["gf"]),
    )
    ko_top8 = [winner, runner_up, third, fourth] + qf_losers
    return ko_top8 + [t for t in final_ranking if t not in ko_top8]

# ============================================================
# MONTE CARLO
# ============================================================
def run_monte_carlo(n_sims, seed=None, mode=MODE):
    rng = random.Random(seed)
    tracker = TieBreakTracker()
    keys = ["winner", "final", "semi", "group_winner", "promoted", "relegated", "stay",
            "safe_direct", "safe_via_playoff", "promoted_direct", "promoted_via_playoff",
            "relegated_direct", "relegated_via_playoff", "euro_pool"]
    counters = {k: Counter() for k in keys}
    position_counts = defaultdict(lambda: defaultdict(int))
    final_rank_counts = defaultdict(lambda: defaultdict(int))
    euro_pot_counts = defaultdict(lambda: defaultdict(int))  # NEW: Tracks Euro 2028 Pots
    it = tqdm(range(n_sims), desc=f"Simulating ({mode})", unit="sim", ncols=80) if HAS_TQDM else range(n_sims)

    for _ in it:
        tracker.new_sim()
        lp = simulate_league_phase(rng, tracker=tracker)
        gs = lp["group_standings"]
        for gname, st in gs.items():
            counters["group_winner"][st[0]["team"]] += 1
            for pos, e in enumerate(st, 1):
                position_counts[e["team"]][pos] += 1
                
                # NEW: Calculate Euro 2028 Pot for this team in this simulation
                league = gname[0]
                team = e["team"]
                pot = None
                if league == 'A':
                    if pos in (1, 2, 3): pot = 1
                    elif pos == 4: pot = 2
                elif league == 'B':
                    if pos in (1, 2): pot = 2
                    elif pos in (3, 4): pot = 3
                elif league == 'C':
                    if pos == 1: pot = 3
                    elif pos in (2, 3, 4): pot = 4
                elif league == 'D':
                    if pos in (1, 2, 3): pot = 5
                
                if pot:
                    euro_pot_counts[team][pot] += 1

        pr = simulate_promotion_relegation(determine_league_rankings(gs), gs, rng, mode)
        for k in ["promoted", "relegated", "stay", "safe_direct", "safe_via_playoff",
                  "promoted_direct", "promoted_via_playoff", "relegated_direct",
                  "relegated_via_playoff", "euro_pool"]:
            for t in pr[k]:
                counters[k][t] += 1
        ko = simulate_knockout_stage(gs, rng)
        counters["winner"][ko["winner"]] += 1
        for t in ko["finalists"]:      counters["final"][t] += 1
        for t in ko["semi_finalists"]: counters["semi"][t] += 1
        for rank, team in enumerate(compute_final_ranking(gs, pr, ko), 1):
            final_rank_counts[team][rank] += 1
        tracker.end_sim()

    def p(key):
        return {t: counters[key][t] / n_sims for t in ALL_TEAMS}

    return {
        "mode": mode, "n_sims": n_sims,
        "winner_prob": p("winner"), "final_prob": p("final"), "semi_prob": p("semi"),
        "group_winner_prob": p("group_winner"),
        "position_prob": {t: {pos: position_counts[t][pos] / n_sims for pos in range(1, 5)}
                          for t in ALL_TEAMS},
        "promotion_prob": p("promoted"), "relegation_prob": p("relegated"),
        "stay_prob": p("stay"), "safe_direct_prob": p("safe_direct"),
        "safe_via_playoff_prob": p("safe_via_playoff"),
        "promoted_direct_prob": p("promoted_direct"),
        "promoted_via_playoff_prob": p("promoted_via_playoff"),
        "relegated_direct_prob": p("relegated_direct"),
        "relegated_via_playoff_prob": p("relegated_via_playoff"),
        "euro_pool_prob": p("euro_pool"),
        "final_rank_counts": final_rank_counts,
        "euro_pot_counts": euro_pot_counts,  # NEW
        "tie_tracker": tracker,
    }

# ============================================================
# MOST-LIKELY TABLE HELPER
# ============================================================
def most_likely_table(pos_prob, teams):
    EPS, n = 1e-9, len(teams)
    best_perm, best_score = None, -math.inf
    for perm in itertools.permutations(range(n)):
        score, valid = 0.0, True
        for i, team in enumerate(teams):
            pr = pos_prob[team].get(perm[i] + 1, 0.0) + EPS
            if pr <= 0:
                valid = False; break
            score += math.log(pr)
        if valid and score > best_score:
            best_score, best_perm = score, perm
    if best_perm is None:
        used, result = set(), []
        for team in teams:
            bp, bpr = None, -1.0
            for pos in range(1, n + 1):
                if pos in used: continue
                pr = pos_prob[team].get(pos, 0.0)
                if pr > bpr: bpr, bp = pr, pos
            if bp is None:
                for pos in range(1, n + 1):
                    if pos not in used: bp = pos; break
            if bp is None: bp = 1
            result.append((team, bp)); used.add(bp)
        return sorted(result, key=lambda x: x[1])
    return sorted([(teams[i], best_perm[i] + 1) for i in range(n)], key=lambda x: x[1])

# ============================================================
# THE ONLY THREE REPORTS
# ============================================================

def _group_current_stats(gname, teams):
    """W/D/L/GF/GA/GD/Pts earned so far, from FIXED_RESULTS only."""
    st = {t: {"W":0,"D":0,"L":0,"GF":0,"GA":0,"GD":0,"Pts":0} for t in teams}
    for (h, a), (hg, ag) in FIXED_RESULTS.items():
        if h not in st or a not in st:
            continue
        st[h]["GF"] += hg; st[h]["GA"] += ag
        st[a]["GF"] += ag; st[a]["GA"] += hg
        if hg > ag:
            st[h]["W"] += 1; st[h]["Pts"] += 3; st[a]["L"] += 1
        elif hg < ag:
            st[a]["W"] += 1; st[a]["Pts"] += 3; st[h]["L"] += 1
        else:
            st[h]["D"] += 1; st[a]["D"] += 1
            st[h]["Pts"] += 1; st[a]["Pts"] += 1
    for t in st:
        st[t]["GD"] = st[t]["GF"] - st[t]["GA"]
    return st


def _group_remaining_projection(gname, teams):
    """For each team, sum expected Pts and expected GD over remaining fixtures."""
    proj = {t: {"xPts": 0.0, "xGD": 0.0} for t in teams}
    fixtures = ([(a, b) for i, a in enumerate(teams) for b in teams[i+1:]] +
                [(b, a) for i, a in enumerate(teams) for b in teams[i+1:]])
    MAX_G = 10
    for h, a in fixtures:
        if (h, a) in FIXED_RESULTS:
            continue
        hxg, axg = expected_goals(h, a)
        ph = [poisson_pmf(i, hxg) for i in range(MAX_G + 1)]
        pa = [poisson_pmf(j, axg) for j in range(MAX_G + 1)]
        p_h = p_d = p_a = 0.0
        egd_h = 0.0
        for i in range(MAX_G + 1):
            for j in range(MAX_G + 1):
                p = ph[i] * pa[j]
                if i > j:   p_h += p
                elif i < j: p_a += p
                else:       p_d += p
                egd_h += p * (i - j)
        proj[h]["xPts"] += 3 * p_h + 1 * p_d
        proj[a]["xPts"] += 3 * p_a + 1 * p_d
        proj[h]["xGD"]  += egd_h
        proj[a]["xGD"]  -= egd_h
    return proj


def print_predicted_tables(res):
    print("\n=== PREDICTED TABLES (W/D/L + xPts + xGD) ===")
    for lg_name, lg in LEAGUES.items():
        print(f"\n[League {lg_name}]")
        for gname, teams in lg["groups"].items():
            cur = _group_current_stats(gname, teams)
            proj = _group_remaining_projection(gname, teams)

            rows = []
            for t in teams:
                final_pts = cur[t]["Pts"] + proj[t]["xPts"]
                final_gd  = cur[t]["GD"]  + proj[t]["xGD"]
                rows.append((t, cur[t]["W"], cur[t]["D"], cur[t]["L"],
                             cur[t]["Pts"], final_pts, final_gd))
            rows.sort(key=lambda r: (-r[5], -r[6]))

            print(f"\n  {gname}")
            print(f"  {'Pos':<4}{'Team':<22}{'W':>3}{'D':>3}{'L':>3}"
                  f"{'Pts':>5}{'xPts':>7}{'xGD':>7}")
            for i, (t, w, d, l, pts, xpts, xgd) in enumerate(rows, 1):
                print(f"  {i:<4}{t:<22}{w:>3}{d:>3}{l:>3}"
                      f"{pts:>5}{xpts:>7.1f}{xgd:>+7.1f}")


def print_remaining_xg():
    print("\n=== REMAINING GAMES — xG (home - away) ===")
    total = 0
    for lg_name, lg in LEAGUES.items():
        header_done = False
        for gname, teams in lg["groups"].items():
            fixtures = ([(a, b) for i, a in enumerate(teams) for b in teams[i+1:]] +
                        [(b, a) for i, a in enumerate(teams) for b in teams[i+1:]])
            remaining = [(h, a) for (h, a) in fixtures if (h, a) not in FIXED_RESULTS]
            if not remaining:
                continue
            if not header_done:
                print(f"\n[League {lg_name}]")
                header_done = True
            for h, a in remaining:
                hxg, axg = expected_goals(h, a)
                print(f"  {gname}  {h:<20} {hxg:5.2f} - {axg:5.2f} {a:<20}")
                total += 1
    print(f"\nTotal remaining fixtures: {total}")


def print_solved_summary(res):
    n_sims = res["n_sims"]
    rank_solved = {r: max(res["final_rank_counts"][t].get(r, 0) / n_sims for t in ALL_TEAMS)
                   for r in range(1, 55)}
    avg_solved = sum(rank_solved.values()) / 54
    print("\n=== HOW SOLVED ===")
    print(f"Overall: {avg_solved*100:.4f}%  (Baseline: 1.9%)")
    sections = [f"{l}={sum(rank_solved[r] for r in range(lo, hi+1))/(hi-lo+1)*100:.1f}%"
                for l, lo, hi in [("A",1,18), ("B",19,36), ("C",37,48), ("D",49,54)]]
    print(f"By League: {', '.join(sections)}")


# ============================================================
# EURO 2028 QUALIFYING POTS  (UPDATED WITH EXACT RULES)
# ============================================================
def print_euro_2028_pots(res):
    """
    Calculates the probability of each team landing in Euro 2028 Qualifying Pots 1-5
    based on the exact rules:
    - Pot 1 (12 teams): Teams that finish 1st, 2nd, or 3rd in League A groups.
    - Pot 2 (12 teams): Teams that finish 4th in League A, plus teams that finish 1st or 2nd in League B groups.
    - Pot 3 (12 teams): Teams that finish 3rd or 4th in League B, plus the group winners from League C.
    - Pot 4 (12 teams): Teams that finish 2nd, 3rd, or 4th in League C groups.
    - Pot 5 (6 teams): All teams playing in League D.
    """
    n_sims = res["n_sims"]
    euro_pot_counts = res["euro_pot_counts"]
    
    # Calculate probabilities
    pot_probs = {t: [0.0] * 5 for t in ALL_TEAMS}
    for t in ALL_TEAMS:
        for pot_idx in range(5):
            pot_probs[t][pot_idx] = euro_pot_counts[t][pot_idx + 1] / n_sims

    print("\n=== PROJECTED EURO 2028 QUALIFYING POTS ===")
    print(f"Based on {n_sims:,} simulations of the 2026-27 UEFA Nations League.")
    print("Pots determined by 2026-27 Nations League tier and final group position.\n")
    
    # Sort teams by average pot (lower is better)
    def avg_pot(t):
        probs = pot_probs[t]
        return sum((i+1)*p for i, p in enumerate(probs))
        
    teams_sorted = sorted(ALL_TEAMS, key=lambda t: (avg_pot(t), t))

    print(f"{'Team':<24} {'Pot 1':>7} {'Pot 2':>7} {'Pot 3':>7} {'Pot 4':>7} {'Pot 5':>7}")
    print("-" * 60)
    for t in teams_sorted:
        p = pot_probs[t]
        print(f"{t:<24} {p[0]*100:>6.1f}% {p[1]*100:>6.1f}% {p[2]*100:>6.1f}% {p[3]*100:>6.1f}% {p[4]*100:>6.1f}%")

    print("\n[Disqualified]")
    print(f"{'Russia':<24} {'-':>7} {'-':>7} {'-':>7} {'-':>7} {'-':>7}")


# ============================================================
# MAIN  (three original prints + Euro 2028 pots report)
# ============================================================
def main():
    print(f"=== UEFA NATIONS LEAGUE 2026/27 — {MODE.upper()} ===")
    print(f"Sims: {N_SIMS:,} | Seed: {RANDOM_SEED}")
    results = run_monte_carlo(N_SIMS, seed=RANDOM_SEED, mode=MODE)
    print_predicted_tables(results)
    print_remaining_xg()
    print_solved_summary(results)
    print_euro_2028_pots(results)


if __name__ == "__main__":
    main()