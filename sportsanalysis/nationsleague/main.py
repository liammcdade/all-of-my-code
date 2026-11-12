import random
import math
from collections import defaultdict
from dataclasses import dataclass, field
from typing import Dict, List, Tuple, Set, Optional

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
MAX_XG = 3.5
HIST_WEIGHT = 0.30
HIST_PRIOR_MATCHES = 60.0

# Discipline points (yellow = 1, red = 3, second yellow = 3)
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

# Pre-simulated fixed results for the 2026-27 group phase.
# Keys are (home_team, away_team) with team names already stripped.
FIXED_RESULTS: Dict[Tuple[str, str], Tuple[int, int]] = {
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
    ("Türkiye", "Belgium"): (1, 2), ("Armenia", "Cyprus"): (1, 1),
    ("Italy", "France"): (2, 1), ("Czechia", "Spain"): (0, 1),
    ("England", "Croatia"): (2, 1), ("Albania", "Finland"): (2, 0),
    ("San Marino", "Belarus"): (0, 2), ("Montenegro", "Latvia"): (0, 0),
}

ELO_RATINGS: Dict[str, int] = {
    "Spain": 2287, "England": 2145, "France": 2104, "Portugal": 2055,
    "Belgium": 1956, "Switzerland": 1975, "Norway": 1900, "Netherlands": 1974,
    "Italy": 1910, "Germany": 1895, "Croatia": 1855, "Denmark": 1861,
    "Austria": 1841, "Ukraine": 1724, "Greece": 1835, "Türkiye": 1768,
    "Sweden": 1774, "Wales": 1681, "Scotland": 1718, "Serbia": 1683,
    "Kosovo": 1710, "Hungary": 1725, "Poland": 1685, "Republic of Ireland": 1711,
    "Slovenia": 1718, "Czechia": 1656, "Northern Ireland": 1672, "Slovakia": 1678,
    "Romania": 1554, "Georgia": 1628, "Iceland": 1597, "Albania": 1612,
    "Bosnia and Herzegovina": 1672, "North Macedonia": 1533, "Finland": 1529,
    "Montenegro": 1490, "Belarus": 1537, "Bulgaria": 1450, "Luxembourg": 1383,
    "Israel": 1619, "Kazakhstan": 1387, "Faroe Islands": 1397, "Armenia": 1354,
    "Cyprus": 1346, "Azerbaijan": 1326, "Moldova": 1288, "Lithuania": 1278,
    "Latvia": 1246, "Malta": 1263, "Andorra": 1056, "Gibraltar": 1034,
    "Liechtenstein": 887, "San Marino": 820, "Estonia": 1408,
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

# 2026-27 league structure (official draw, UEFA.com[reference:3])
LEAGUES_2627 = {
    "A": {
        "groups": {
            "A1": ["France", "Italy", "Belgium", "Türkiye"],
            "A2": ["Germany", "Netherlands", "Serbia", "Greece"],
            "A3": ["Spain", "Croatia", "England", "Czechia"],
            "A4": ["Portugal", "Denmark", "Norway", "Wales"],
        }
    },
    "B": {
        "groups": {
            "B1": ["Scotland", "Switzerland", "Slovenia", "North Macedonia"],
            "B2": ["Hungary", "Ukraine", "Georgia", "Northern Ireland"],
            "B3": ["Israel", "Austria", "Republic of Ireland", "Kosovo"],
            "B4": ["Poland", "Bosnia and Herzegovina", "Romania", "Sweden"],
        }
    },
    "C": {
        "groups": {
            "C1": ["Albania", "Finland", "Belarus", "San Marino"],
            "C2": ["Montenegro", "Armenia", "Cyprus", "Latvia"],
            "C3": ["Kazakhstan", "Slovakia", "Faroe Islands", "Moldova"],
            "C4": ["Iceland", "Bulgaria", "Estonia", "Luxembourg"],
        }
    },
    "D": {
        "groups": {
            "D1": ["Gibraltar", "Malta", "Andorra"],
            "D2": ["Lithuania", "Azerbaijan", "Liechtenstein"],
        }
    },
}

# ============================================================
# CLEANUP & INDEX BUILDING
# ============================================================
def _clean_team_name(name: str) -> str:
    return name.strip()

ALL_TEAMS: List[str] = [
    t for lg in LEAGUES_2627.values()
    for grp in lg["groups"].values()
    for t in grp
]

for t in ALL_TEAMS:
    if t not in DISCIPLINE_POINTS:
        DISCIPLINE_POINTS[t] = 0

ACCESS_LIST: Dict[str, int] = {}
_idx = 0
for lg_name in ("A", "B", "C", "D"):
    for gname, teams in LEAGUES_2627[lg_name]["groups"].items():
        for t in teams:
            ACCESS_LIST[t] = _idx
            _idx += 1

# ============================================================
# CORE SIMULATION HELPERS
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
        (s["matches_home"], s["goals_home"], GLOBAL_AVG_HOME)
        if is_home
        else (s["matches_away"], s["goals_away"], GLOBAL_AVG_AWAY)
    )
    if n == 0:
        return 1.0
    shrunk = (n * (g / n) + HIST_PRIOR_MATCHES * ref) / (n + HIST_PRIOR_MATCHES)
    return shrunk / ref


HOME_ATTACK_MOD = {t: _attack_modifier(t, True) for t in ALL_TEAMS}
AWAY_ATTACK_MOD = {t: _attack_modifier(t, False) for t in ALL_TEAMS}


def poisson_rand(lam: float, rng: random.Random) -> int:
    if lam <= 0:
        return 0
    L, k, p = math.exp(-lam), 0, 1.0
    while True:
        k += 1
        p *= rng.random()
        if p <= L:
            return k - 1


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


# ============================================================
# TIEBREAKERS (Article 15 of the regulations[reference:4])
# ============================================================
def sort_tied_teams(teams: List[str],
                    results: List[Tuple[str, str, int, int]],
                    overall_stats: Dict[str, Dict],
                    access_order: Dict[str, int]) -> List[str]:
    """
    Sort a list of teams tied on points using the official UEFA criteria.

    Criteria:
      a) head-to-head points
      b) head-to-head goal difference
      c) head-to-head goals scored
      → if still level, REAPPLY (a)–(c) to the remaining teams
      e) overall goal difference
      f) overall goals scored
      g) away goals scored
      h) wins
      i) away wins
      j) disciplinary points
      k) access-list position
    """
    if len(teams) <= 1:
        return teams[:]

    h2h = {t: {"pts": 0, "gd": 0, "gf": 0} for t in teams}
    for h, a, hg, ag in results:
        if h in teams and a in teams:
            if hg > ag:
                h2h[h]["pts"] += 3
            elif hg < ag:
                h2h[a]["pts"] += 3
            else:
                h2h[h]["pts"] += 1
                h2h[a]["pts"] += 1
            h2h[h]["gd"] += hg - ag
            h2h[a]["gd"] += ag - hg
            h2h[h]["gf"] += hg
            h2h[a]["gf"] += ag

    teams_sorted = sorted(
        teams,
        key=lambda t: (-h2h[t]["pts"], -h2h[t]["gd"], -h2h[t]["gf"])
    )

    result: List[str] = []
    i = 0
    while i < len(teams_sorted):
        j = i + 1
        key_i = (h2h[teams_sorted[i]]["pts"],
                 h2h[teams_sorted[i]]["gd"],
                 h2h[teams_sorted[i]]["gf"])
        while j < len(teams_sorted):
            key_j = (h2h[teams_sorted[j]]["pts"],
                     h2h[teams_sorted[j]]["gd"],
                     h2h[teams_sorted[j]]["gf"])
            if key_j != key_i:
                break
            j += 1

        block = teams_sorted[i:j]
        if len(block) == 1:
            result.append(block[0])
        elif len(block) == len(teams):
            # Head-to-head cannot separate them → overall criteria.
            block.sort(key=lambda t: (
                -overall_stats[t]["gd"],
                -overall_stats[t]["gf"],
                -overall_stats[t]["away_gf"],
                -overall_stats[t]["wins"],
                -overall_stats[t]["away_wins"],
                overall_stats[t]["disc_points"],
                access_order[t],
                -effective_elo(t),
            ))
            result.extend(block)
        else:
            # REAPPLY head-to-head (a–c) exclusively to the remaining block.
            result.extend(sort_tied_teams(
                block, results, overall_stats, access_order))
        i = j

    return result


def calculate_group_standings(teams: List[str],
                              results: List[Tuple[str, str, int, int]],
                              access_order: Optional[Dict[str, int]] = None
                              ) -> List[Dict]:
    if access_order is None:
        access_order = {t: ACCESS_LIST.get(t, 999) for t in teams}

    stats = {
        t: {
            "team": t, "played": 0, "won": 0, "drawn": 0, "lost": 0,
            "gf": 0, "ga": 0, "gd": 0, "points": 0,
            "away_gf": 0, "away_won": 0,
            "disc_points": DISCIPLINE_POINTS.get(t, 0),
        }
        for t in teams
    }

    for home, away, hg, ag in results:
        stats[home]["played"] += 1
        stats[away]["played"] += 1
        stats[home]["gf"] += hg
        stats[home]["ga"] += ag
        stats[away]["gf"] += ag
        stats[away]["ga"] += hg
        stats[away]["away_gf"] += ag

        if hg > ag:
            stats[home]["won"] += 1
            stats[home]["points"] += 3
            stats[away]["lost"] += 1
        elif hg < ag:
            stats[away]["won"] += 1
            stats[away]["away_won"] += 1
            stats[away]["points"] += 3
            stats[home]["lost"] += 1
        else:
            stats[home]["drawn"] += 1
            stats[away]["drawn"] += 1
            stats[home]["points"] += 1
            stats[away]["points"] += 1

    for t in stats:
        stats[t]["gd"] = stats[t]["gf"] - stats[t]["ga"]

    overall_stats = {
        t: {
            "gd": stats[t]["gd"],
            "gf": stats[t]["gf"],
            "away_gf": stats[t]["away_gf"],
            "wins": stats[t]["won"],
            "away_wins": stats[t]["away_won"],
            "disc_points": stats[t]["disc_points"],
        }
        for t in teams
    }

    teams_sorted_by_points = sorted(
        teams, key=lambda t: -stats[t]["points"])

    final_order: List[str] = []
    i = 0
    while i < len(teams_sorted_by_points):
        j = i + 1
        pts = stats[teams_sorted_by_points[i]]["points"]
        while (j < len(teams_sorted_by_points)
               and stats[teams_sorted_by_points[j]]["points"] == pts):
            j += 1
        group = teams_sorted_by_points[i:j]
        if len(group) == 1:
            final_order.append(group[0])
        else:
            final_order.extend(
                sort_tied_teams(group, results, overall_stats, access_order))
        i = j

    return [stats[t] for t in final_order]


# ============================================================
# INTERIM OVERALL RANKING
# (Leagues A→B→C→D, then by group position, then full tiebreakers)
# ============================================================
def build_interim_ranking(group_standings: Dict[str, List[Dict]]
                          ) -> List[str]:
    """
    Returns the 1–54 interim overall ranking used to seed EURO 2028
    qualifying pots.

    The ranking is ordered strictly by:
      League A 1st, League A 2nd, League A 3rd, League A 4th,
      League B 1st, League B 2nd, … League D 2nd/3rd.
    Within each band, teams are ordered by the full group-stage
    tiebreaker chain (points → GD → GF → away GF → wins → away wins
    → discipline → access list → Elo).
    """
    bands: Dict[Tuple[str, int], List[Dict]] = defaultdict(list)

    for gname, standings in group_standings.items():
        league = gname[0]  # "A", "B", "C", "D"
        for pos, entry in enumerate(standings, 1):
            bands[(league, pos)].append(entry)

    ranking: List[str] = []
    for league in ("A", "B", "C", "D"):
        max_pos = 4 if league in ("A", "B", "C") else 3
        for pos in range(1, max_pos + 1):
            entries = bands.get((league, pos), [])
            entries.sort(key=lambda e: (
                -e["points"],
                -e["gd"],
                -e["gf"],
                -e["away_gf"],
                -e["won"],
                -e["away_won"],
                e["disc_points"],
                ACCESS_LIST.get(e["team"], 999),
                -effective_elo(e["team"]),
            ))
            ranking.extend(e["team"] for e in entries)

    assert len(ranking) == len(ALL_TEAMS), (
        f"Interim ranking has {len(ranking)} teams, "
        f"expected {len(ALL_TEAMS)}."
    )
    return ranking


# ============================================================
# PROMOTION / RELEGATION PLAY-OFFS
# ============================================================
def _resolve_playoff_pair(
    team_a: str, team_b: str, rng: random.Random
) -> Tuple[str, str]:
    """
    Two-legged promotion/relegation play-off.
    Returns (winner, loser).  The winner stays in / moves to the higher league.
    """
    hg1, ag1 = simulate_match(team_a, team_b, rng)  # leg 1: A at home
    hg2, ag2 = simulate_match(team_b, team_a, rng)  # leg 2: B at home

    agg_a = hg1 + ag2
    agg_b = ag1 + hg2

    if agg_a != agg_b:
        return (team_a, team_b) if agg_a > agg_b else (team_b, team_a)

    # Extra time (single 30-minute period simulated with reduced λ).
    et_h, et_a = simulate_match(team_b, team_a, rng)
    if et_h != et_a:
        winner = team_b if et_h > et_a else team_a
        loser = team_a if winner == team_b else team_b
        return winner, loser

    # Penalties.
    diff = effective_elo(team_a) - effective_elo(team_b)
    prob_a = 1.0 / (1.0 + math.exp(-diff / 150.0))
    if rng.random() < prob_a:
        return team_a, team_b
    return team_b, team_a


@dataclass
class LeagueMovement:
    """Records the promotion/relegation outcomes for one league."""
    promoted_direct: List[str] = field(default_factory=list)
    relegated_direct: List[str] = field(default_factory=list)
    playoff_winners: List[str] = field(default_factory=list)
    playoff_losers: List[str] = field(default_factory=list)


def simulate_promotion_relegation(
    group_standings: Dict[str, List[Dict]],
    rng: random.Random,
) -> Dict[str, LeagueMovement]:
    """
    Applies the 2026-27 promotion/relegation rules:

    League A/B play-offs:
      – 2 lowest-ranked 3rd-placed League A teams
      – 2 highest-ranked 4th-placed League A teams
      – 4 runners-up from League B
      (8 teams → 4 two-legged ties)[reference:5]

    League B/C play-offs:
      – 4 fourth-placed League B teams
      – 4 runners-up from League C
      (8 teams → 4 two-legged ties)[reference:6]

    League C/D play-offs (2026-27 special rule):
      – All League D teams are guaranteed promotion to League C.
      – No League C team is relegated (the competition shrinks in 2028-29)[reference:7].
      For completeness the two lowest-ranked League C fourth-placed teams
      are recorded as “relegated to League D” in the historical record, but
      they will in fact play in League C in 2028-29 because League D is abolished.
    """
    movements: Dict[str, LeagueMovement] = {
        lg: LeagueMovement() for lg in ("A", "B", "C", "D")
    }

    def _league_entries(league: str, pos: int) -> List[Dict]:
        out: List[Dict] = []
        for gname, standings in group_standings.items():
            if gname[0] != league:
                continue
            if len(standings) >= pos:
                out.append(standings[pos - 1])
        return out

    def _sort_entries(entries: List[Dict]) -> List[Dict]:
        return sorted(entries, key=lambda e: (
            -e["points"], -e["gd"], -e["gf"], -e["away_gf"],
            -e["won"], -e["away_won"], e["disc_points"],
            ACCESS_LIST.get(e["team"], 999), -effective_elo(e["team"]),
        ))

    # ---- League A: automatic relegation ----
    fourth_a = _sort_entries(_league_entries("A", 4))
    if len(fourth_a) >= 2:
        movements["A"].relegated_direct = [
            fourth_a[-1]["team"], fourth_a[-2]["team"]
        ]

    # ---- League A/B play-offs ----
    third_a = _sort_entries(_league_entries("A", 3))
    fourth_a = _sort_entries(_league_entries("A", 4))
    runners_b = _sort_entries(_league_entries("B", 2))

    # Two lowest-ranked 3rd-placed League A teams.
    third_a_low = third_a[-2:] if len(third_a) >= 2 else third_a[:]
    # Two highest-ranked 4th-placed League A teams.
    fourth_a_high = fourth_a[:2] if len(fourth_a) >= 2 else fourth_a[:]

    ab_teams = (
        [e["team"] for e in third_a_low]
        + [e["team"] for e in fourth_a_high]
        + [e["team"] for e in runners_b]
    )
    rng.shuffle(ab_teams)

    for i in range(0, len(ab_teams) - 1, 2):
        winner, loser = _resolve_playoff_pair(
            ab_teams[i], ab_teams[i + 1], rng)
        movements["A"].playoff_winners.append(winner)
        movements["B"].playoff_losers.append(loser)

    # ---- League B/C play-offs ----
    fourth_b = _sort_entries(_league_entries("B", 4))
    runners_c = _sort_entries(_league_entries("C", 2))

    bc_teams = (
        [e["team"] for e in fourth_b]
        + [e["team"] for e in runners_c]
    )
    rng.shuffle(bc_teams)

    for i in range(0, len(bc_teams) - 1, 2):
        winner, loser = _resolve_playoff_pair(
            bc_teams[i], bc_teams[i + 1], rng)
        movements["B"].playoff_winners.append(winner)
        movements["C"].playoff_losers.append(loser)

    # ---- Direct promotions ----
    for league, higher in (("B", "A"), ("C", "B"), ("D", "C")):
        winners = _sort_entries(_league_entries(league, 1))
        movements[league].promoted_direct = [e["team"] for e in winners]

    # ---- League C/D special rule ----
    # All League D teams are promoted to League C in 2028-29.
    movements["D"].promoted_direct = [
        e["team"]
        for gname, standings in group_standings.items()
        if gname[0] == "D"
        for e in standings
    ]
    # No League C team is relegated in 2026-27.
    movements["C"].relegated_direct = []

    return movements


# ============================================================
# SEASON SIMULATION
# ============================================================
def simulate_2627_season(rng: random.Random
                         ) -> Tuple[Dict[str, List[Dict]],
                                    List[Tuple[str, str, int, int]]]:
    """
    Simulates all 2026-27 group-stage matches.
    Returns (group_standings, all_results).
    """
    group_standings: Dict[str, List[Dict]] = {}
    all_results: List[Tuple[str, str, int, int]] = []

    for lg_name, lg in LEAGUES_2627.items():
        for gname, teams in lg["groups"].items():
            matches = (
                [(a, b) for i, a in enumerate(teams)
                 for b in teams[i + 1:]]
                + [(b, a) for i, a in enumerate(teams)
                   for b in teams[i + 1:]]
            )
            results: List[Tuple[str, str, int, int]] = []
            for h, a in matches:
                fixed = _resolve_fixed_result(h, a)
                if fixed is not None:
                    hg, ag = fixed
                else:
                    hg, ag = simulate_match(h, a, rng)
                results.append((h, a, hg, ag))
                all_results.append((h, a, hg, ag))

            st = calculate_group_standings(teams, results)
            group_standings[gname] = st

    return group_standings, all_results


def _resolve_fixed_result(home: str, away: str
                          ) -> Optional[Tuple[int, int]]:
    """
    Checks FIXED_RESULTS for (home, away) and, if absent, for (away, home)
    with the score reversed.
    """
    if (home, away) in FIXED_RESULTS:
        return FIXED_RESULTS[(home, away)]
    if (away, home) in FIXED_RESULTS:
        ag, hg = FIXED_RESULTS[(away, home)]
        return hg, ag
    return None


# ============================================================
# PUBLIC INTERFACE FOR euro2028.py
# ============================================================
@dataclass
class NLSeasonState:
    """
    Everything EURO 2028 qualifying needs from the 2026-27 Nations League.

    Attributes
    ----------
    ranking : list[str]
        1–54 interim overall ranking (drives qualifying draw pots).
    qf_teams : set[str]
        The 8 teams that advance to the League A quarter-finals
        (top two from each League A group).
    group_winners : set[str]
        All 14 UNL group winners (4 from A, 4 from B, 4 from C, 2 from D).
        These are the teams eligible for the EURO 2028 play-off route.
    group_standings : dict[str, list[dict]]
        Raw group standings keyed by group name (A1, A2, … D2).
    league_movement : dict[str, LeagueMovement]
        Promotion / relegation / play-off outcomes.
    playoff_winners : set[str]
        Teams that won a promotion/relegation play-off.
    """
    ranking: List[str]
    qf_teams: Set[str]
    group_winners: Set[str]
    group_standings: Dict[str, List[Dict]]
    league_movement: Dict[str, LeagueMovement]
    playoff_winners: Set[str]


def simulate_nl_season_state(rng: random.Random) -> NLSeasonState:
    """
    Run one complete 2026-27 Nations League season.

    This is the single function that euro2028.py should call.
    """
    group_standings, _ = simulate_2627_season(rng)

    ranking = build_interim_ranking(group_standings)

    # Quarter-finalists: top two from each League A group.
    qf_teams: Set[str] = set()
    for gname in ("A1", "A2", "A3", "A4"):
        standings = group_standings.get(gname, [])
        for entry in standings[:2]:
            qf_teams.add(entry["team"])
    assert len(qf_teams) == 8, (
        f"Expected 8 quarter-finalists, got {len(qf_teams)}.")

    # All UNL group winners.
    group_winners: Set[str] = set()
    for gname, standings in group_standings.items():
        if standings:
            group_winners.add(standings[0]["team"])
    assert len(group_winners) == 14, (
        f"Expected 14 group winners, got {len(group_winners)}.")

    # Promotion / relegation.
    league_movement = simulate_promotion_relegation(
        group_standings, rng)

    playoff_winners: Set[str] = set()
    for lg in league_movement.values():
        playoff_winners.update(lg.playoff_winners)

    return NLSeasonState(
        ranking=ranking,
        qf_teams=qf_teams,
        group_winners=group_winners,
        group_standings=group_standings,
        league_movement=league_movement,
        playoff_winners=playoff_winners,
    )


# Legacy helper (kept for backward compatibility with any existing callers).
def simulate_nl_ranking(rng: random.Random) -> List[str]:
    return simulate_nl_season_state(rng).ranking


# ============================================================
# PRINTING HELPERS
# ============================================================
def print_group_standings_2627(
    group_standings: Dict[str, List[Dict]]
) -> None:
    print("\n=== 2026-27 UEFA NATIONS LEAGUE GROUP STANDINGS ===")
    for gname in sorted(group_standings.keys()):
        print(f"\nGroup {gname}")
        print(f"{'Pos':<4} {'Team':<24} {'Pld':>3} {'W':>2} {'D':>2} "
              f"{'L':>2} {'GF':>3} {'GA':>3} {'GD':>4} {'Pts':>4}")
        print("-" * 55)
        for pos, entry in enumerate(group_standings[gname], 1):
            print(
                f"{pos:<4} {entry['team']:<24} {entry['played']:>3} "
                f"{entry['won']:>2} {entry['drawn']:>2} {entry['lost']:>2} "
                f"{entry['gf']:>3} {entry['ga']:>3} "
                f"{entry['gd']:>+4} {entry['points']:>4}"
            )


def print_most_likely_ranking_2627(
    rank_counts: Dict[str, Dict[int, int]], n_sims: int
) -> None:
    print("\n=== MOST LIKELY INTERIM OVERALL RANKING (2026-27) ===")
    print("This ranking is used for EURO 2028 qualifying pot allocation.")
    print("-" * 65)
    print(f"{'Rank':<5} {'Team':<24} {'Prob %':>8} {'Avg Rank':>10}")
    print("-" * 65)

    team_best: Dict[str, Tuple[int, float, float]] = {}
    for team in ALL_TEAMS:
        probs = rank_counts.get(team)
        if not probs:
            continue
        best_r = max(probs, key=probs.get)
        best_p = probs[best_r] / n_sims
        avg_r = sum(r * c for r, c in probs.items()) / sum(probs.values())
        team_best[team] = (best_r, best_p, avg_r)

    sorted_teams = sorted(
        ALL_TEAMS, key=lambda t: team_best.get(t, (99, 0.0, 0.0))[0])

    for team in sorted_teams[:54]:
        best_r, best_p, avg_r = team_best[team]
        print(f"{best_r:<5} {team:<24} {best_p * 100:>7.1f}% "
              f"{avg_r:>9.1f}")


# ============================================================
# MAIN (stand-alone NL simulation)
# ============================================================
def run_2627_simulation(
    n_sims: int, seed: Optional[int] = None
) -> Dict[str, Dict[int, int]]:
    rng = random.Random(seed)
    rank_counts: Dict[str, Dict[int, int]] = defaultdict(
        lambda: defaultdict(int))

    iterator = (
        tqdm(range(n_sims), desc="Simulating 2026-27", unit="sim")
        if HAS_TQDM else range(n_sims)
    )
    for _ in iterator:
        state = simulate_nl_season_state(rng)
        for rank, team in enumerate(state.ranking, 1):
            rank_counts[team][rank] += 1

    return rank_counts


def main() -> None:
    print("=== UEFA NATIONS LEAGUE 2026-27 SIMULATION ===")
    print(f"Sims: {N_SIMS:,} | Seed: {RANDOM_SEED}")

    # Single simulation for display.
    rng = random.Random(RANDOM_SEED)
    state = simulate_nl_season_state(rng)
    print_group_standings_2627(state.group_standings)

    print("\nInterim Overall Ranking (single simulation):")
    for i, team in enumerate(state.ranking, 1):
        print(f"{i:>2}. {team}")

    print("\nQuarter-finalists (League A top two):")
    for t in sorted(state.qf_teams):
        print(f"  – {t}")

    print("\nLeague A/B play-off winners:")
    for t in state.league_movement["A"].playoff_winners:
        print(f"  – {t}")

    # Probabilistic ranking.
    rank_counts = run_2627_simulation(N_SIMS, seed=RANDOM_SEED)
    print_most_likely_ranking_2627(rank_counts, N_SIMS)


if __name__ == "__main__":
    main()