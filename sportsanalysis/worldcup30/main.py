import logging
import math
import random
import sys
from dataclasses import dataclass, field
from typing import Dict, List, Tuple, Optional, Set, FrozenSet
from tqdm import tqdm

logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")
logger = logging.getLogger(__name__)

# =============================================================================
# CONFIGURATION & CONSTANTS
# =============================================================================

DEFAULT_ELO: int = 1200
ELO_K_FACTOR: int = 30
ELO_EXPECTED_DENOMINATOR: float = 400.0

HOME_ADVANTAGE_ELO: Dict[str, int] = {
    "CONMEBOL": 70, "UEFA": 45, "AFC": 60, "CAF": 55,
    "CONCACAF": 55, "OFC": 55, "InterConfederation": 0,
}

HOST_NATIONS: Dict[str, List[str]] = {
    "UEFA": ["Spain", "Portugal"],
    "CAF": ["Morocco"],
    "CONMEBOL": ["Argentina", "Uruguay", "Paraguay"],
}

CONFEDERATIONS: Dict[str, Dict] = {
    "UEFA": {
        "base_slots": 16, "auto_hosts": 2, "remaining_direct_slots": 14,
        "playoff_slots": 1,
        "member_nations": [
            "Albania", "Andorra", "Armenia", "Austria", "Azerbaijan", "Belarus", "Belgium",
            "Bosnia and Herzegovina", "Bulgaria", "Croatia", "Cyprus", "Czech Republic",
            "Denmark", "England", "Estonia", "Faroe Islands", "Finland", "France", "Georgia",
            "Germany", "Gibraltar", "Greece", "Hungary", "Iceland", "Israel", "Italy",
            "Kazakhstan", "Kosovo", "Latvia", "Liechtenstein", "Lithuania", "Luxembourg",
            "Malta", "Moldova", "Montenegro", "Netherlands", "North Macedonia", "Northern Ireland",
            "Norway", "Poland", "Portugal", "Republic of Ireland", "Romania", "San Marino",
            "Scotland", "Serbia", "Slovakia", "Slovenia", "Spain", "Sweden", "Switzerland",
            "Turkey", "Ukraine", "Wales",
        ],
    },
    "CAF": {
        "base_slots": 9, "auto_hosts": 1, "remaining_direct_slots": 8,
        "playoff_slots": 1,
        "member_nations": [
            "Algeria", "Angola", "Benin", "Botswana", "Burkina Faso", "Burundi", "Cameroon",
            "Cape Verde", "Central African Republic", "Chad", "Comoros", "Republic of the Congo",
            "DR Congo", "Djibouti", "Egypt", "Equatorial Guinea", "Eritrea", "Eswatini",
            "Ethiopia", "Gabon", "Gambia", "Ghana", "Guinea", "Guinea-Bissau", "Ivory Coast",
            "Kenya", "Lesotho", "Liberia", "Libya", "Madagascar", "Malawi", "Mali",
            "Mauritania", "Mauritius", "Morocco", "Mozambique", "Namibia", "Niger", "Nigeria",
            "Rwanda", "São Tomé and Príncipe", "Senegal", "Seychelles", "Sierra Leone",
            "Somalia", "South Africa", "South Sudan", "Sudan", "Tanzania", "Togo", "Tunisia",
            "Uganda", "Zambia", "Zimbabwe",
        ],
    },
    "CONMEBOL": {
        "base_slots": 6, "auto_hosts": 3, "remaining_direct_slots": 3,
        "playoff_slots": 1,
        "member_nations": [
            "Argentina", "Bolivia", "Brazil", "Chile", "Colombia",
            "Ecuador", "Paraguay", "Peru", "Uruguay", "Venezuela",
        ],
    },
    "AFC": {
        "base_slots": 8, "auto_hosts": 0, "remaining_direct_slots": 8,
        "playoff_slots": 1,
        "member_nations": [
            "Afghanistan", "Australia", "Bahrain", "Bangladesh", "Bhutan", "Brunei Darussalam",
            "Cambodia", "China PR", "Chinese Taipei", "Guam", "Hong Kong", "India", "Indonesia",
            "Iran", "Iraq", "Japan", "Jordan", "Kuwait", "Kyrgyzstan", "Laos", "Lebanon",
            "Macau", "Malaysia", "Maldives", "Mongolia", "Myanmar", "Nepal", "Oman", "Pakistan",
            "Palestine", "Philippines", "Qatar", "Saudi Arabia", "Singapore", "South Korea",
            "Sri Lanka", "Syria", "Tajikistan", "Thailand", "Timor-Leste", "Turkmenistan",
            "United Arab Emirates", "Uzbekistan", "Vietnam", "Yemen", "North Korea",
        ],
    },
    "CONCACAF": {
        "base_slots": 6, "auto_hosts": 0, "remaining_direct_slots": 6,
        "playoff_slots": 1,
        "member_nations": [
            "Mexico", "United States", "Canada", "Panama", "Costa Rica", "Honduras",
            "Jamaica", "Curaçao", "Haiti", "Guatemala", "El Salvador", "Trinidad and Tobago",
            "Suriname", "Dominican Republic", "Nicaragua", "Guyana", "Saint Kitts and Nevis",
            "Puerto Rico", "Antigua and Barbuda", "Cuba", "Saint Lucia",
            "Saint Vincent and the Grenadines", "Grenada", "Bermuda", "Montserrat",
            "Barbados", "Belize", "Aruba", "Dominica", "Cayman Islands",
            "Turks and Caicos Islands", "U.S. Virgin Islands", "Bahamas",
            "British Virgin Islands", "Anguilla",
        ],
    },
    "OFC": {
        "base_slots": 1, "auto_hosts": 0, "remaining_direct_slots": 1,
        "playoff_slots": 1,
        "member_nations": [
            "American Samoa", "Cook Islands", "Fiji", "New Caledonia", "New Zealand",
            "Papua New Guinea", "Samoa", "Solomon Islands", "Tahiti", "Tonga", "Vanuatu",
        ],
    },
}

TOTAL_HOSTS = sum(len(h) for h in HOST_NATIONS.values())
TOTAL_DIRECT = 40
PLAYOFF_WINNERS = 2
TOTAL_TEAMS = 48
NUM_SIMULATIONS = 10000

UEFA_PARTICIPATING = True

UEFA_TOTAL_HOSTS = CONFEDERATIONS["UEFA"]["auto_hosts"]
UEFA_TOTAL_DIRECT = CONFEDERATIONS["UEFA"]["remaining_direct_slots"]

if not UEFA_PARTICIPATING:
    TOTAL_HOSTS_ACTIVE = TOTAL_HOSTS - UEFA_TOTAL_HOSTS
    TOTAL_DIRECT_ACTIVE = TOTAL_DIRECT - UEFA_TOTAL_DIRECT
else:
    TOTAL_HOSTS_ACTIVE = TOTAL_HOSTS
    TOTAL_DIRECT_ACTIVE = TOTAL_DIRECT
TOTAL_TEAMS_ACTIVE = TOTAL_HOSTS_ACTIVE + TOTAL_DIRECT_ACTIVE + PLAYOFF_WINNERS

# =============================================================================
# NATIONS LEAGUE 2028/29 PROJECTION DATA
# Determines League 1 vs League 2 assignment for UEFA qualifying
# =============================================================================

NATIONS_LEAGUE_L1_PROB: Dict[str, float] = {
    "Albania": 0.44,
    "Andorra": 0.0,
    "Armenia": 0.004,
    "Austria": 1.0,
    "Azerbaijan": 0.0,
    "Belarus": 0.292,
    "Belgium": 1.0,
    "Bosnia and Herzegovina": 1.0,
    "Bulgaria": 0.026,
    "Croatia": 1.0,
    "Cyprus": 0.087,
    "Czech Republic": 1.0,
    "Denmark": 1.0,
    "England": 1.0,
    "Estonia": 0.084,
    "Faroe Islands": 0.002,
    "Finland": 0.268,
    "France": 1.0,
    "Georgia": 1.0,
    "Germany": 1.0,
    "Gibraltar": 0.0,
    "Greece": 1.0,
    "Hungary": 1.0,
    "Iceland": 0.884,
    "Israel": 1.0,
    "Italy": 1.0,
    "Kazakhstan": 0.0,
    "Kosovo": 1.0,
    "Latvia": 0.0,
    "Liechtenstein": 0.0,
    "Lithuania": 0.0,
    "Luxembourg": 0.007,
    "Malta": 0.0,
    "Moldova": 0.0,
    "Montenegro": 0.91,
    "Netherlands": 1.0,
    "North Macedonia": 1.0,
    "Northern Ireland": 1.0,
    "Norway": 1.0,
    "Poland": 1.0,
    "Portugal": 1.0,
    "Republic of Ireland": 1.0,
    "Romania": 1.0,
    "San Marino": 0.0,
    "Scotland": 1.0,
    "Serbia": 1.0,
    "Slovakia": 0.998,
    "Slovenia": 1.0,
    "Spain": 1.0,
    "Sweden": 1.0,
    "Switzerland": 1.0,
    "Turkey": 1.0,
    "Ukraine": 1.0,
    "Wales": 1.0,
}

# =============================================================================
# ELO RATINGS (as of Oct 2026)
# =============================================================================

ELO_RATINGS: Dict[str, int] = {
    # UEFA
    "Spain": 2287, "England": 2146, "France": 2104, "Portugal": 2055,
    "Switzerland": 1975, "Netherlands": 1974, "Belgium": 1955, "Italy": 1910,
    "Norway": 1900, "Germany": 1895, "Denmark": 1861, "Croatia": 1856,
    "Austria": 1841, "Greece": 1804, "Russia": 1778, "Sweden": 1774,
    "Turkey": 1768, "Hungary": 1725, "Ukraine": 1724, "Scotland": 1718,
    "Slovenia": 1718, "Ireland": 1711, "Kosovo": 1710, "Poland": 1685,
    "Serbia": 1683, "Wales": 1681, "Slovakia": 1678, "Northern Ireland": 1672,
    "Bosnia and Herzegovina": 1672, "Czech Republic": 1656, "Georgia": 1628,
    "Israel": 1619, "Albania": 1612, "Iceland": 1597, "Romania": 1554,
    "Belarus": 1537, "North Macedonia": 1533, "Finland": 1530, "Montenegro": 1490,
    "Bulgaria": 1460, "Estonia": 1406, "Faroe Islands": 1398, "Kazakhstan": 1387,
    "Luxembourg": 1383, "Armenia": 1354, "Cyprus": 1346, "Azerbaijan": 1326,
    "Moldova": 1288, "Lithuania": 1278, "Malta": 1263, "Latvia": 1246,
    "Andorra": 1056, "Gibraltar": 1036, "Liechtenstein": 887, "San Marino": 820,
    # CONMEBOL
    "Argentina": 2175, "Brazil": 2001, "Colombia": 1990, "Uruguay": 1851,
    "Ecuador": 1849, "Paraguay": 1836, "Venezuela": 1732, "Chile": 1723,
    "Peru": 1681, "Bolivia": 1613,
    # AFC
    "Japan": 1888, "Iran": 1764, "South Korea": 1723, "Australia": 1795,
    "Qatar": 1411, "Saudi Arabia": 1596, "Iraq": 1561, "Uzbekistan": 1631,
    "United Arab Emirates": 1540, "Oman": 1480, "Jordan": 1628, "Bahrain": 1414,
    "China": 1424, "Syria": 1479, "Vietnam": 1353, "Palestine": 1465,
    "Thailand": 1376, "Tajikistan": 1209, "Lebanon": 1288, "India": 1128,
    "Malaysia": 1293, "Kuwait": 1332, "Indonesia": 1372, "Kyrgyzstan": 1295,
    "North Korea": 1373, "Turkmenistan": 1209, "Philippines": 1179, "Hong Kong": 1101,
    "Chinese Taipei": 1101, "Yemen": 1195, "Afghanistan": 1373, "Myanmar": 982,
    "Singapore": 1134, "Maldives": 801, "Nepal": 893, "Pakistan": 909,
    "Bangladesh": 942, "Sri Lanka": 836, "Cambodia": 871, "Mongolia": 726,
    "Bhutan": 623, "Macau": 589, "Laos": 734, "Brunei Darussalam": 572,
    "Timor-Leste": 734, "Guam": 706,
    # CAF
    "Morocco": 1901, "Senegal": 1816, "Egypt": 1742, "Algeria": 1756,
    "Nigeria": 1767, "Ivory Coast": 1727, "DR Congo": 1704, "Tunisia": 1562,
    "Ghana": 1570, "Cameroon": 1614, "Cape Verde": 1619, "South Africa": 1559,
    "Mali": 1588, "Angola": 1542, "Burkina Faso": 1529, "Guinea": 1463,
    "Benin": 1405, "Gabon": 1401, "Uganda": 1394, "Libya": 1420,
    "Gambia": 1419, "Zimbabwe": 1372, "Zambia": 1371, "Kenya": 1363,
    "Sudan": 1350, "Mozambique": 1342, "Sierra Leone": 1341, "Rwanda": 1336,
    "Niger": 1382, "Madagascar": 1380, "Togo": 1379, "Tanzania": 1313,
    "Liberia": 1304, "Namibia": 1303, "Ethiopia": 1287, "Burundi": 1285,
    "Botswana": 1267, "Guinea-Bissau": 1248, "Malawi": 1239, "Congo": 1206,
    "Lesotho": 1198, "Eswatini": 1148, "Somalia": 1148, "Central African Republic": 1073,
    "Chad": 1073, "Mauritius": 1073, "São Tomé and Príncipe": 1073,
    "Djibouti": 1000, "Eritrea": 950, "Comoros": 900, "Equatorial Guinea": 1200,
    "South Sudan": 800,
    # CONCACAF
    "Mexico": 1868, "United States": 1792, "Canada": 1739, "Panama": 1654,
    "Costa Rica": 1587, "Haiti": 1563, "Jamaica": 1543, "Honduras": 1530,
    "Guatemala": 1524, "Curaçao": 1491, "Suriname": 1455, "Trinidad and Tobago": 1339,
    "Dominican Republic": 1331, "Guyana": 1325, "El Salvador": 1324, "Martinique": 1310,
    "Nicaragua": 1255, "French Guiana": 1247, "Cuba": 1245, "Guadeloupe": 1239,
    "Saint Vincent and the Grenadines": 1214, "Puerto Rico": 1158, "Saint Lucia": 1069,
    "Saint Kitts and Nevis": 1085, "Saint Martin": 1029, "Montserrat": 1024,
    "Belize": 1021, "Bermuda": 1016, "Barbados": 1012, "Grenada": 998,
    "Aruba": 990, "Sint Maarten": 929, "Antigua and Barbuda": 913, "Dominica": 885,
    "Bonaire": 856, "Cayman Islands": 797, "U.S. Virgin Islands": 694,
    "Turks and Caicos Islands": 687, "British Virgin Islands": 661, "Bahamas": 631,
    "Anguilla": 615,
    # OFC
    "New Zealand": 1534, "Fiji": 1104, "Tahiti": 1179, "New Caledonia": 1286,
    "Papua New Guinea": 1136, "Solomon Islands": 1054, "Vanuatu": 1117,
    "Samoa": 730, "Tonga": 521, "Cook Islands": 623, "American Samoa": 369,
}

CONCACAF_RANKING_ORDER = [
    "Mexico", "United States", "Canada", "Panama", "Costa Rica", "Honduras",
    "Jamaica", "Curaçao", "Haiti", "Guatemala", "El Salvador", "Trinidad and Tobago",
    "Suriname", "Dominican Republic", "Nicaragua", "Guyana", "Saint Kitts and Nevis",
    "Puerto Rico", "Antigua and Barbuda", "Cuba", "Saint Lucia",
    "Saint Vincent and the Grenadines", "Grenada", "Bermuda", "Montserrat",
    "Barbados", "Belize", "Aruba", "Dominica", "Cayman Islands",
    "Turks and Caicos Islands", "U.S. Virgin Islands", "Bahamas",
    "British Virgin Islands", "Anguilla",
]

WORLD_CUP_2026_TEAMS: Set[str] = {
    "Austria", "Belgium", "Bosnia and Herzegovina", "Croatia", "Czech Republic", "England",
    "France", "Germany", "Netherlands", "Norway", "Portugal", "Scotland", "Spain",
    "Sweden", "Switzerland", "Turkey",
    "Argentina", "Brazil", "Colombia", "Ecuador", "Paraguay", "Uruguay",
    "Algeria", "Cape Verde", "DR Congo", "Egypt", "Ghana", "Ivory Coast",
    "Morocco", "Senegal", "South Africa", "Tunisia",
    "Australia", "Iran", "Iraq", "Japan", "Jordan", "Qatar", "Saudi Arabia",
    "South Korea", "Uzbekistan",
    "Canada", "Curaçao", "Haiti", "Mexico", "Panama", "United States",
    "New Zealand",
}

ALL_HISTORICAL_WORLD_CUP_TEAMS: Set[str] = {
    "Austria", "Belgium", "Bosnia and Herzegovina", "Bulgaria", "Croatia",
    "Czech Republic", "Denmark", "England", "France", "Germany", "Greece",
    "Hungary", "Iceland", "Israel", "Italy", "Netherlands", "Northern Ireland",
    "Norway", "Poland", "Portugal", "Republic of Ireland", "Romania", "Russia",
    "Scotland", "Serbia", "Slovakia", "Slovenia", "Spain", "Sweden",
    "Switzerland", "Turkey", "Ukraine", "Wales",
    "Argentina", "Bolivia", "Brazil", "Chile", "Colombia", "Ecuador",
    "Paraguay", "Peru", "Uruguay",
    "Canada", "Costa Rica", "Cuba", "Curaçao", "El Salvador", "Haiti",
    "Honduras", "Jamaica", "Mexico", "Panama", "Trinidad and Tobago",
    "United States", "Syria"
    "Algeria", "Angola", "Cape Verde", "Cameroon", "DR Congo", "Egypt",
    "Ghana", "Ivory Coast", "Morocco", "Nigeria", "Senegal", "South Africa",
    "Togo", "Tunisia",
    "Australia", "China PR", "Indonesia", "Iran", "Iraq", "Japan", "Jordan",
    "Kuwait", "North Korea", "Qatar", "Saudi Arabia", "South Korea",
    "United Arab Emirates", "Uzbekistan",
    "New Zealand",
}

# =============================================================================
# DATA STRUCTURES
# =============================================================================

@dataclass(slots=True)
class TeamRecord:
    name: str
    confederation: str
    elo: int = DEFAULT_ELO
    points: int = 0
    goals_for: int = 0
    goals_against: int = 0
    h2h: Dict[str, Tuple[int, int]] = field(default_factory=dict)

    @property
    def goal_difference(self) -> int:
        return self.goals_for - self.goals_against


# =============================================================================
# CORE SIMULATION ENGINE
# =============================================================================

def poisson_goals(expected: float) -> int:
    """Generate Poisson-distributed goals with safety cap."""
    if expected <= 0:
        return 0
    L = math.exp(-expected)
    k = 0
    p = 1.0
    while True:
        k += 1
        p *= random.random()
        if p <= L:
            return min(k - 1, 10)
        if k > 100:
            return min(k - 1, 10)


def simulate_match(home: TeamRecord, away: TeamRecord, neutral: bool = False) -> Tuple[int, int]:
    """Simulate a single match with confederation-aware xG scaling."""
    home_adv = 0 if neutral else HOME_ADVANTAGE_ELO.get(home.confederation, 0)
    diff = float(home.elo) - float(away.elo) + float(home_adv)

    base_elo_factor = 0.0015
    if home.confederation == "UEFA" and away.confederation == "UEFA":
        elo_factor = 0.0018
    else:
        elo_factor = base_elo_factor

    home_xg = 1.45 * math.exp(elo_factor * diff)
    away_xg = 1.15 * math.exp(-elo_factor * diff)

    home_xg = max(0.2, min(home_xg, 5.0))
    away_xg = max(0.2, min(away_xg, 5.0))

    return poisson_goals(home_xg), poisson_goals(away_xg)


def update_elo(home: TeamRecord, away: TeamRecord, hg: int, ag: int, neutral: bool = False) -> None:
    """Update Elo ratings after a match."""
    home_adv = 0 if neutral else HOME_ADVANTAGE_ELO.get(home.confederation, 0)
    diff = float(home.elo) - float(away.elo) + float(home_adv)
    home_expected = 1.0 / (1.0 + 10.0 ** (-diff / ELO_EXPECTED_DENOMINATOR))
    away_expected = 1.0 / (1.0 + 10.0 ** (diff / ELO_EXPECTED_DENOMINATOR))

    if hg > ag:
        home_actual, away_actual = 1.0, 0.0
    elif hg < ag:
        home_actual, away_actual = 0.0, 1.0
    else:
        home_actual = away_actual = 0.5

    home.elo = int(home.elo + ELO_K_FACTOR * (home_actual - home_expected))
    away.elo = int(away.elo + ELO_K_FACTOR * (away_actual - away_expected))


def apply_result(records: Dict[str, TeamRecord], home_name: str, away_name: str,
                 hg: int, ag: int, neutral: bool = False) -> None:
    """Apply match result to standings, H2H, and Elo."""
    home = records[home_name]
    away = records[away_name]

    home.goals_for += hg
    home.goals_against += ag
    away.goals_for += ag
    away.goals_against += hg

    prev_h = home.h2h.get(away_name, (0, 0))
    home.h2h[away_name] = (prev_h[0] + hg, prev_h[1] + ag)
    prev_a = away.h2h.get(home_name, (0, 0))
    away.h2h[home_name] = (prev_a[0] + ag, prev_a[1] + hg)

    if hg > ag:
        home.points += 3
    elif hg < ag:
        away.points += 3
    else:
        home.points += 1
        away.points += 1

    update_elo(home, away, hg, ag, neutral=neutral)


def sort_records(records: Dict[str, TeamRecord]) -> List[TeamRecord]:
    """FIFA-compliant sorting: Points → GD → GF → H2H Points → H2H GD → H2H GF."""
    teams = list(records.values())

    def h2h_stats(t: TeamRecord, group: List[TeamRecord]) -> Tuple[int, int, int]:
        pts, gd, gf = 0, 0, 0
        for opp in group:
            if opp.name == t.name:
                continue
            h2h = t.h2h.get(opp.name, (0, 0))
            gf += h2h[0]
            gd += h2h[0] - h2h[1]
            if h2h[0] > h2h[1]:
                pts += 3
            elif h2h[0] == h2h[1]:
                pts += 1
        return pts, gd, gf

    teams.sort(key=lambda t: (t.points, t.goal_difference, t.goals_for), reverse=True)

    i = 0
    while i < len(teams):
        j = i + 1
        while j < len(teams) and (
            teams[j].points == teams[i].points and
            teams[j].goal_difference == teams[i].goal_difference and
            teams[j].goals_for == teams[i].goals_for
        ):
            j += 1

        if j - i > 1:
            tie_group = teams[i:j]
            tie_group.sort(
                key=lambda t: h2h_stats(t, tie_group),
                reverse=True
            )
            teams[i:j] = tie_group
        i = j

    return teams


def resolve_elo(name: str) -> int:
    """Resolve team name to Elo rating with comprehensive alias mapping."""
    aliases = {
        "Republic of Ireland": "Ireland",
        "DR Congo": "DR Congo",
        "Dem. Rep. of Congo": "DR Congo",
        "Republic of the Congo": "Congo",
        "Türkiye": "Turkey",
        "China PR": "China",
        "Curaçao": "Curaçao",
        "North Korea": "North Korea",
        "South Korea": "South Korea",
    }
    lookup = aliases.get(name, name)
    return ELO_RATINGS.get(lookup, DEFAULT_ELO)


# =============================================================================
# CONFEDERATION QUALIFYING SIMULATIONS
# =============================================================================

def simulate_conmebol_qualifying(all_member_names: List[str], host_names: List[str]) -> Tuple[List[str], List[str]]:
    """CONMEBOL 2030: Full 10-team RR, rank only non-hosts for 3 direct + 1 playoff."""
    teams = [TeamRecord(name, "CONMEBOL", elo=resolve_elo(name)) for name in all_member_names]
    records = {t.name: t for t in teams}

    for i in range(len(teams)):
        for j in range(i + 1, len(teams)):
            hg, ag = simulate_match(teams[i], teams[j])
            apply_result(records, teams[i].name, teams[j].name, hg, ag)
            hg, ag = simulate_match(teams[j], teams[i])
            apply_result(records, teams[j].name, teams[i].name, hg, ag)

    non_host_records = {n: r for n, r in records.items() if n not in host_names}
    ranked = sort_records(non_host_records)

    direct = [t.name for t in ranked[:3]]
    playoff = [ranked[3].name] if len(ranked) > 3 else []
    return direct, playoff


def simulate_concacaf_2030_format() -> Tuple[List[str], List[str]]:
    """CONCACAF 2030: R1 knockout → R2 groups → R3 groups + 3rd-place playoff → intercontinental."""
    all_teams = [
        TeamRecord(name, "CONCACAF", elo=resolve_elo(name))
        for name in CONCACAF_RANKING_ORDER
    ]

    r1_teams = all_teams[13:]
    assert len(r1_teams) == 22
    random.shuffle(r1_teams)
    r1_winners: List[TeamRecord] = []
    for i in range(0, 22, 2):
        home, away = r1_teams[i], r1_teams[i + 1]
        h1, a1 = simulate_match(home, away)
        h2, a2 = simulate_match(away, home)
        agg_home = h1 + a2
        agg_away = a1 + h2
        if agg_home > agg_away:
            r1_winners.append(home)
        elif agg_away > agg_home:
            r1_winners.append(away)
        else:
            r1_winners.append(random.choice([home, away]))

    top13 = all_teams[:13]
    r2_pool = top13 + r1_winners
    assert len(r2_pool) == 24
    random.shuffle(r2_pool)
    r2_groups = [r2_pool[i:i + 4] for i in range(0, 24, 4)]
    r2_qualifiers: List[TeamRecord] = []
    for group in r2_groups:
        records = {t.name: t for t in group}
        for i in range(len(group)):
            for j in range(i + 1, len(group)):
                hg, ag = simulate_match(group[i], group[j])
                apply_result(records, group[i].name, group[j].name, hg, ag)
                hg, ag = simulate_match(group[j], group[i])
                apply_result(records, group[j].name, group[i].name, hg, ag)
        ranked = sort_records(records)
        r2_qualifiers.extend([ranked[0], ranked[1]])

    random.shuffle(r2_qualifiers)
    r3_groups = [r2_qualifiers[i:i + 4] for i in range(0, 12, 4)]
    direct_qualifiers: List[str] = []
    third_place_teams: List[TeamRecord] = []
    for group in r3_groups:
        records = {t.name: t for t in group}
        for i in range(len(group)):
            for j in range(i + 1, len(group)):
                hg, ag = simulate_match(group[i], group[j])
                apply_result(records, group[i].name, group[j].name, hg, ag)
                hg, ag = simulate_match(group[j], group[i])
                apply_result(records, group[j].name, group[i].name, hg, ag)
        ranked = sort_records(records)
        direct_qualifiers.extend([ranked[0].name, ranked[1].name])
        third_place_teams.append(ranked[2])

    third_place_teams.sort(
        key=lambda t: (t.points, t.goal_difference, t.goals_for), reverse=True
    )
    t1, t2 = third_place_teams[0], third_place_teams[1]
    h1, a1 = simulate_match(t1, t2)
    h2, a2 = simulate_match(t2, t1)
    agg_t1 = h1 + a2
    agg_t2 = a1 + h2
    if agg_t1 > agg_t2:
        playoff_representative = [t1.name]
    elif agg_t2 > agg_t1:
        playoff_representative = [t2.name]
    else:
        playoff_representative = [random.choice([t1.name, t2.name])]

    return direct_qualifiers, playoff_representative


def simulate_afc_2030_format() -> Tuple[List[str], List[str]]:
    """AFC 2030: R1 → R2 groups → R3 groups → R4 groups + runners-up playoff."""
    member_names = CONFEDERATIONS["AFC"]["member_nations"]
    teams = [TeamRecord(name, "AFC", elo=resolve_elo(name)) for name in member_names]
    teams.sort(key=lambda t: t.elo, reverse=True)

    round1 = teams[-20:]
    round2_teams = teams[:-20]
    random.shuffle(round1)
    r1_winners = []
    for i in range(0, 20, 2):
        a, b = round1[i], round1[i + 1]
        h1, a1 = simulate_match(a, b)
        h2, a2 = simulate_match(b, a)
        ta, tb = h1 + a2, a1 + h2
        if ta > tb:
            r1_winners.append(a)
        elif tb > ta:
            r1_winners.append(b)
        else:
            r1_winners.append(random.choice([a, b]))

    r2_pool = round2_teams + r1_winners
    random.shuffle(r2_pool)
    r2_groups = [r2_pool[i:i + 4] for i in range(0, 36, 4)]
    r2_advancers = []
    for group in r2_groups:
        records = {t.name: t for t in group}
        for i in range(4):
            for j in range(i + 1, 4):
                hg, ag = simulate_match(group[i], group[j])
                apply_result(records, group[i].name, group[j].name, hg, ag)
                hg, ag = simulate_match(group[j], group[i])
                apply_result(records, group[j].name, group[i].name, hg, ag)
        ranked = sort_records(records)
        r2_advancers.extend([ranked[0], ranked[1]])

    random.shuffle(r2_advancers)
    r3_groups = [r2_advancers[i:i + 6] for i in range(0, 18, 6)]
    direct: List[str] = []
    r4_teams: List[TeamRecord] = []
    for group in r3_groups:
        records = {t.name: t for t in group}
        for i in range(6):
            for j in range(i + 1, 6):
                hg, ag = simulate_match(group[i], group[j])
                apply_result(records, group[i].name, group[j].name, hg, ag)
                hg, ag = simulate_match(group[j], group[i])
                apply_result(records, group[j].name, group[i].name, hg, ag)
        ranked = sort_records(records)
        direct.extend([ranked[0].name, ranked[1].name])
        r4_teams.extend([ranked[2], ranked[3]])

    random.shuffle(r4_teams)
    r4_groups = [r4_teams[i:i + 3] for i in range(0, 6, 3)]
    r4_runners: List[TeamRecord] = []
    for group in r4_groups:
        records = {t.name: t for t in group}
        for i in range(3):
            for j in range(i + 1, 3):
                hg, ag = simulate_match(group[i], group[j])
                apply_result(records, group[i].name, group[j].name, hg, ag)
                hg, ag = simulate_match(group[j], group[i])
                apply_result(records, group[j].name, group[i].name, hg, ag)
        ranked = sort_records(records)
        direct.append(ranked[0].name)
        r4_runners.append(ranked[1])

    t1, t2 = r4_runners[0], r4_runners[1]
    h1, a1 = simulate_match(t1, t2)
    h2, a2 = simulate_match(t2, t1)
    ta, tb = h1 + a2, a1 + h2
    if ta > tb:
        afc_playoff = t1.name
    elif tb > ta:
        afc_playoff = t2.name
    else:
        afc_playoff = random.choice([t1.name, t2.name])

    return direct, [afc_playoff]


def simulate_caf_2030_format() -> Tuple[List[str], List[str]]:
    """CAF 2030: R1 knockout → R2 groups (8×6) → winners direct + best runner-up playoff."""
    teams = [TeamRecord(name, "CAF", elo=resolve_elo(name))
             for name in CONFEDERATIONS["CAF"]["member_nations"]]
    hosts = HOST_NATIONS.get("CAF", [])
    non_hosts = [t for t in teams if t.name not in hosts]
    non_hosts.sort(key=lambda t: t.elo, reverse=True)

    round1 = non_hosts[-10:]
    round2_teams = non_hosts[:-10]
    random.shuffle(round1)
    r1_winners = []
    for i in range(0, 10, 2):
        a, b = round1[i], round1[i + 1]
        h1, a1 = simulate_match(a, b)
        h2, a2 = simulate_match(b, a)
        ta, tb = h1 + a2, a1 + h2
        if ta > tb:
            r1_winners.append(a)
        elif tb > ta:
            r1_winners.append(b)
        else:
            r1_winners.append(random.choice([a, b]))

    r2_pool = round2_teams + r1_winners
    random.shuffle(r2_pool)
    groups = [r2_pool[i:i + 6] for i in range(0, 48, 6)]
    winners: List[str] = []
    runners: List[TeamRecord] = []
    for group in groups:
        records = {t.name: t for t in group}
        for i in range(6):
            for j in range(i + 1, 6):
                hg, ag = simulate_match(group[i], group[j])
                apply_result(records, group[i].name, group[j].name, hg, ag)
                hg, ag = simulate_match(group[j], group[i])
                apply_result(records, group[j].name, group[i].name, hg, ag)
        ranked = sort_records(records)
        winners.append(ranked[0].name)
        runners.append(ranked[1])

    runners.sort(key=lambda t: (t.points, t.goal_difference, t.goals_for), reverse=True)
    best_runner = runners[0].name if runners else None
    return winners, [best_runner] if best_runner else []


def simulate_ofc_2030_format() -> Tuple[List[str], List[str]]:
    """
    OFC 2030 Qualifying (confirmed multi-round format):
    Preliminary: Bottom 4 ranked → single-leg knockout → 1 winner
    Group Stage: Top 7 + prelim winner = 8 teams in 2 groups of 4 (double RR)
    Final Round: 4-team knockout (neutral) → winner direct, runner-up playoff
    """
    members = CONFEDERATIONS["OFC"]["member_nations"]
    teams = [TeamRecord(name, "OFC", elo=resolve_elo(name)) for name in members]
    teams.sort(key=lambda t: t.elo, reverse=True)

    def neutral_knockout(a: TeamRecord, b: TeamRecord) -> TeamRecord:
        hg, ag = simulate_match(a, b, neutral=True)
        if hg != ag:
            return a if hg > ag else b
        return random.choice([a, b])

    # Preliminary Round: Bottom 4
    prelim_teams = teams[-4:]
    random.shuffle(prelim_teams)
    prelim_sf1 = neutral_knockout(prelim_teams[0], prelim_teams[1])
    prelim_sf2 = neutral_knockout(prelim_teams[2], prelim_teams[3])
    prelim_winner = neutral_knockout(prelim_sf1, prelim_sf2)

    # Group Stage: Top 7 + prelim winner = 8 teams
    group_stage_teams = teams[:7] + [prelim_winner]
    random.shuffle(group_stage_teams)
    gs_groups = [group_stage_teams[:4], group_stage_teams[4:]]

    semifinalists: List[TeamRecord] = []
    for group in gs_groups:
        records = {t.name: t for t in group}
        for i in range(len(group)):
            for j in range(i + 1, len(group)):
                hg, ag = simulate_match(group[i], group[j])
                apply_result(records, group[i].name, group[j].name, hg, ag)
                hg, ag = simulate_match(group[j], group[i])
                apply_result(records, group[j].name, group[i].name, hg, ag)
        ranked = sort_records(records)
        semifinalists.extend(ranked[:2])

    # Final Round: Cross-seeded knockout at neutral venue
    sf1 = neutral_knockout(semifinalists[0], semifinalists[3])
    sf2 = neutral_knockout(semifinalists[1], semifinalists[2])

    final_score = simulate_match(sf1, sf2, neutral=True)
    if final_score[0] > final_score[1]:
        champion, runner_up = sf1, sf2
    elif final_score[1] > final_score[0]:
        champion, runner_up = sf2, sf1
    else:
        champion, runner_up = random.choice([(sf1, sf2), (sf2, sf1)])

    return [champion.name], [runner_up.name]


# =============================================================================
# UEFA SWISS FORMAT HELPERS
# =============================================================================

def _assign_uefa_leagues(member_names: List[str]) -> Tuple[List[str], List[str]]:
    """Assign teams to League 1/2 based on Nations League probabilities."""
    league_a: List[str] = []
    league_b: List[str] = []
    uncertain: List[Tuple[str, float]] = []

    for name in member_names:
        prob = NATIONS_LEAGUE_L1_PROB.get(name, 0.0)
        if prob >= 1.0:
            league_a.append(name)
        elif prob <= 0.0:
            league_b.append(name)
        else:
            uncertain.append((name, prob))

    # Sort uncertain by probability descending for prioritized filling
    uncertain.sort(key=lambda x: x[1], reverse=True)

    # Fill League A to exactly 36 from uncertain teams
    needed = 36 - len(league_a)
    promoted_from_uncertain: List[str] = []
    remaining_uncertain: List[Tuple[str, float]] = []

    for name, prob in uncertain:
        if len(promoted_from_uncertain) < needed:
            if random.random() < prob or needed - len(promoted_from_uncertain) >= len(uncertain) - uncertain.index((name, prob)):
                promoted_from_uncertain.append(name)
            else:
                remaining_uncertain.append((name, prob))
        else:
            remaining_uncertain.append((name, prob))

    league_a.extend(promoted_from_uncertain)

    # If still short (all uncertain teams failed probabilistic check), force-fill
    still_needed = 36 - len(league_a)
    if still_needed > 0:
        # Take from remaining uncertain first, then from league_b (lowest Elo)
        fill_candidates = [n for n, _ in remaining_uncertain]
        # Add league_b teams sorted by Elo ascending as backup
        lb_by_elo = sorted(league_b, key=lambda n: resolve_elo(n))
        fill_candidates.extend(lb_by_elo)

        for name in fill_candidates:
            if still_needed <= 0:
                break
            if name in league_b:
                league_b.remove(name)
            league_a.append(name)
            still_needed -= 1

    # All remaining uncertain go to League B
    for name, _ in remaining_uncertain:
        if name not in league_a and name not in league_b:
            league_b.append(name)

    # Final safety: trim excess from League A (demote lowest Elo)
    while len(league_a) > 36:
        worst = min(league_a, key=lambda n: NATIONS_LEAGUE_L1_PROB.get(n, 0.0) * 10000 + resolve_elo(n))
        league_a.remove(worst)
        league_b.append(worst)

    assert len(league_a) == 36, f"League A has {len(league_a)} teams, expected 36"
    assert len(league_b) == len(member_names) - 36, f"League B has {len(league_b)} teams, expected {len(member_names) - 36}"
    return league_a, league_b


def _generate_swiss_fixtures(group: List[TeamRecord]) -> List[Tuple[str, str]]:
    """
    Generate 6-match Swiss fixtures for a 12-team group.
    Each team plays exactly 6 matches (3H/3A) against 6 unique opponents.
    4 pots of 3 ensure balanced opposition strength distribution.
    """
    sorted_group = sorted(group, key=lambda t: t.elo, reverse=True)
    team_names = [t.name for t in sorted_group]

    pots = [
        set(team_names[0:3]),
        set(team_names[3:6]),
        set(team_names[6:9]),
        set(team_names[9:12]),
    ]

    fixtures: List[Tuple[str, str]] = []
    played: Set[FrozenSet[str]] = set()
    home_count: Dict[str, int] = {name: 0 for name in team_names}

    for team in sorted_group:
        needed = 6 - sum(1 for f in fixtures if team.name in f)
        if needed <= 0:
            continue

        candidates = []
        for pot in pots:
            for opp_name in pot:
                if opp_name != team.name and frozenset({team.name, opp_name}) not in played:
                    candidates.append(opp_name)

        random.shuffle(candidates)
        selected = candidates[:needed]

        for opp_name in selected:
            pair = frozenset({team.name, opp_name})
            if pair in played:
                continue

            if home_count[team.name] < 3 and home_count[opp_name] < 3:
                if home_count[team.name] <= home_count[opp_name]:
                    fixtures.append((team.name, opp_name))
                    home_count[team.name] += 1
                else:
                    fixtures.append((opp_name, team.name))
                    home_count[opp_name] += 1
            elif home_count[team.name] < 3:
                fixtures.append((team.name, opp_name))
                home_count[team.name] += 1
            elif home_count[opp_name] < 3:
                fixtures.append((opp_name, team.name))
                home_count[opp_name] += 1
            else:
                if random.random() > 0.5:
                    fixtures.append((team.name, opp_name))
                else:
                    fixtures.append((opp_name, team.name))

            played.add(pair)

    return fixtures


def simulate_uefa_swiss_format(member_names: List[str]) -> Tuple[List[str], List[str]]:
    """
    UEFA 2030 World Cup Qualifying (Confirmed Format):
    LEAGUE 1: Top 36 (by NL ranking) in 3 groups of 12. Swiss-style: 6 matches (3H/3A).
              3 group winners qualify directly.
    LEAGUE 2: Remaining 18 teams in 3 groups of 6. Double round-robin.
              3 group winners advance to playoffs.
    PLAYOFFS: Fixed bracket for remaining direct slots + 1 intercontinental spot.
    Hosts (Spain, Portugal) participate but qualification is automatic.
    """
    hosts = set(HOST_NATIONS.get("UEFA", []))

    la_names, lb_names = _assign_uefa_leagues(member_names)
    league_a = [TeamRecord(name, "UEFA", elo=resolve_elo(name)) for name in la_names]
    league_b = [TeamRecord(name, "UEFA", elo=resolve_elo(name)) for name in lb_names]

    # === LEAGUE 1: 3 groups of 12, Swiss fixtures ===
    random.shuffle(league_a)
    la_groups = [league_a[i:i+12] for i in range(0, 36, 12)]
    la_group_results: List[List[TeamRecord]] = []

    for group in la_groups:
        records = {t.name: t for t in group}
        fixtures = _generate_swiss_fixtures(group)
        for home_name, away_name in fixtures:
            hg, ag = simulate_match(records[home_name], records[away_name])
            apply_result(records, home_name, away_name, hg, ag)
        la_group_results.append(sort_records(records))

    # === DIRECT QUALIFIERS FROM LEAGUE 1 ===
    direct_qualifiers: List[str] = []
    la_non_winners: List[TeamRecord] = []

    for grp in la_group_results:
        winner = grp[0]
        if winner.name not in hosts:
            direct_qualifiers.append(winner.name)
        la_non_winners.extend(grp[1:])

    for grp in la_group_results:
        if grp[0].name in hosts:
            la_non_winners.append(grp[0])

    # === LEAGUE 2: 3 groups of 6, double round-robin ===
    assert len(league_b) == 18, f"Expected 18 League B teams, got {len(league_b)}"
    random.shuffle(league_b)
    lb_groups = [league_b[i:i+6] for i in range(0, 18, 6)]
    lb_winners: List[TeamRecord] = []

    for group in lb_groups:
        records = {t.name: t for t in group}
        for i in range(len(group)):
            for j in range(i+1, len(group)):
                hg, ag = simulate_match(group[i], group[j])
                apply_result(records, group[i].name, group[j].name, hg, ag)
                hg, ag = simulate_match(group[j], group[i])
                apply_result(records, group[j].name, group[i].name, hg, ag)
        ranked = sort_records(records)
        lb_winners.append(ranked[0])

    # === PLAYOFF PHASE ===
    remaining_direct = CONFEDERATIONS["UEFA"]["remaining_direct_slots"] - len(direct_qualifiers)

    playoff_pool = [t for t in la_non_winners if t.name not in hosts] + lb_winners
    random.shuffle(playoff_pool)

    playoff_direct: List[str] = []
    current_round = playoff_pool[:]

    while len(playoff_direct) < remaining_direct and len(current_round) >= 2:
        next_round: List[TeamRecord] = []
        for i in range(0, len(current_round) - 1, 2):
            t1, t2 = current_round[i], current_round[i+1]
            h1, a1 = simulate_match(t1, t2)
            h2, a2 = simulate_match(t2, t1)
            agg1, agg2 = h1 + a2, a1 + h2

            if agg1 > agg2:
                winner, loser = t1, t2
            elif agg2 > agg1:
                winner, loser = t2, t1
            else:
                winner, loser = random.choice([(t1, t2), (t2, t1)])

            if len(playoff_direct) < remaining_direct:
                playoff_direct.append(winner.name)
            else:
                next_round.append(winner)

            if len(playoff_direct) >= remaining_direct:
                next_round.append(loser)

        current_round = next_round

    uefa_inter: List[str] = []
    if current_round:
        current_round.sort(key=lambda t: (t.points, t.goal_difference, t.goals_for), reverse=True)
        uefa_inter = [current_round[0].name]
    elif playoff_pool:
        playoff_pool.sort(key=lambda t: (t.points, t.goal_difference, t.goals_for), reverse=True)
        uefa_inter = [playoff_pool[0].name]

    return direct_qualifiers + playoff_direct, uefa_inter


# =============================================================================
# INTERCONTINENTAL PLAYOFF
# =============================================================================

def simulate_intercontinental_playoff(qualifiers: List[str]) -> List[str]:
    """6-team single-elimination at neutral venue. Seeds 1&2 get byes."""
    if len(qualifiers) < 4:
        raise ValueError(f"Intercontinental playoff requires ≥4 teams, got {len(qualifiers)}")

    teams = [TeamRecord(name, "InterConfederation", elo=resolve_elo(name)) for name in qualifiers]
    teams.sort(key=lambda t: t.elo, reverse=True)

    def knockout(a: TeamRecord, b: TeamRecord) -> TeamRecord:
        hg1, ag1 = simulate_match(a, b, neutral=True)
        hg2, ag2 = simulate_match(b, a, neutral=True)
        agg_a = hg1 + ag2
        agg_b = ag1 + hg2
        if agg_a > agg_b:
            return a
        elif agg_b > agg_a:
            return b
        return random.choice([a, b])

    if len(teams) == 6:
        play_in_1 = knockout(teams[2], teams[5])
        play_in_2 = knockout(teams[3], teams[4])
        finalist_1 = knockout(teams[0], play_in_1)
        finalist_2 = knockout(teams[1], play_in_2)
        return [finalist_1.name, finalist_2.name]

    if len(teams) == 5:
        play_in = knockout(teams[2], teams[4])
        finalist_1 = knockout(teams[0], play_in)
        finalist_2 = knockout(teams[1], teams[3])
        return [finalist_1.name, finalist_2.name]

    if len(teams) == 4:
        return [knockout(teams[0], teams[3]).name,
                knockout(teams[1], teams[2]).name]

    winners = []
    for i in range(0, len(teams) - 1, 2):
        winners.append(knockout(teams[i], teams[i + 1]))
    return [w.name for w in winners[:2]]


# =============================================================================
# ORCHESTRATION
# =============================================================================

def validate_totals() -> bool:
    total = TOTAL_HOSTS_ACTIVE + TOTAL_DIRECT_ACTIVE + PLAYOFF_WINNERS
    logger.info("Slot allocation verified: %s/%s", total, TOTAL_TEAMS_ACTIVE)
    return total == TOTAL_TEAMS_ACTIVE


def run_qualifying_simulation(seed: Optional[int] = None) -> Dict[str, List[str]]:
    if seed is not None:
        random.seed(seed)

    qualified: Dict[str, List[str]] = {
        "UEFA": [], "CAF": [], "CONMEBOL": [], "AFC": [],
        "CONCACAF": [], "OFC": [], "Intercontinental": [],
        "UEFA_playoff": [], "CAF_playoff": [], "CONMEBOL_playoff": [],
        "AFC_playoff": [], "CONCACAF_playoff": [], "OFC_playoff": [],
    }

    for conf, hosts in HOST_NATIONS.items():
        if conf == "UEFA" and not UEFA_PARTICIPATING:
            continue
        qualified[conf].extend(hosts)

    conmebol_hosts = HOST_NATIONS.get("CONMEBOL", [])
    direc, playoff = simulate_conmebol_qualifying(
        CONFEDERATIONS["CONMEBOL"]["member_nations"], conmebol_hosts
    )
    qualified["CONMEBOL"].extend(direc)
    qualified["CONMEBOL_playoff"] = playoff

    if UEFA_PARTICIPATING:
        uefa_direct, uefa_playoff = simulate_uefa_swiss_format(
            CONFEDERATIONS["UEFA"]["member_nations"]
        )
        qualified["UEFA"].extend(uefa_direct)
        qualified["UEFA_playoff"] = uefa_playoff

    concacaf_direct, concacaf_playoff = simulate_concacaf_2030_format()
    qualified["CONCACAF"].extend(concacaf_direct)
    qualified["CONCACAF_playoff"] = concacaf_playoff

    afc_direct, afc_playoff = simulate_afc_2030_format()
    qualified["AFC"].extend(afc_direct)
    qualified["AFC_playoff"] = afc_playoff

    # CAF & OFC
    for conf in ("CAF", "OFC"):
        if conf == "CAF":
            d, p = simulate_caf_2030_format()
        else:
            d, p = simulate_ofc_2030_format()
        qualified[conf].extend(d)
        qualified[f"{conf}_playoff"] = p

    playoff_teams = [
        qualified["CAF_playoff"][0],
        qualified["CONMEBOL_playoff"][0],
        qualified["AFC_playoff"][0],
        qualified["CONCACAF_playoff"][0],
        qualified["OFC_playoff"][0],
    ]
    if UEFA_PARTICIPATING and qualified["UEFA_playoff"]:
        playoff_teams.append(qualified["UEFA_playoff"][0])

    qualified["Intercontinental"] = simulate_intercontinental_playoff(playoff_teams)
    return qualified


# =============================================================================
# MONTE CARLO & REPORTING
# =============================================================================

NEVER_WORLD_CUP_TEAMS_FULL = sorted({
    t for cfg in CONFEDERATIONS.values() for t in cfg["member_nations"]
    if t not in ALL_HISTORICAL_WORLD_CUP_TEAMS
})


def run_monte_carlo(num_sims: int, seed: Optional[int] = None):
    if UEFA_PARTICIPATING:
        all_teams = sorted({t for cfg in CONFEDERATIONS.values() for t in cfg["member_nations"]})
        never_wc_teams = NEVER_WORLD_CUP_TEAMS_FULL
        exact_match_set = WORLD_CUP_2026_TEAMS
        confs_to_count = ("UEFA", "CAF", "CONMEBOL", "AFC", "CONCACAF", "OFC")
    else:
        all_teams = sorted({t for conf, cfg in CONFEDERATIONS.items()
                           if conf != "UEFA" for t in cfg["member_nations"]})
        never_wc_teams = [t for t in NEVER_WORLD_CUP_TEAMS_FULL
                         if t not in CONFEDERATIONS["UEFA"]["member_nations"]]
        exact_match_set = {t for t in WORLD_CUP_2026_TEAMS
                          if t not in CONFEDERATIONS["UEFA"]["member_nations"]}
        confs_to_count = ("CAF", "CONMEBOL", "AFC", "CONCACAF", "OFC")

    qualified_count: Dict[str, int] = {name: 0 for name in all_teams}
    exact_match_count = 0
    never_qualified_count: Dict[str, int] = {name: 0 for name in never_wc_teams}
    debutant_sim_count = 0
    total_debutants = 0

    if seed is not None:
        random.seed(seed)

    for _ in tqdm(range(num_sims), desc="Monte Carlo", unit="sim"):
        results = run_qualifying_simulation()
        sim_qualified: Set[str] = set()

        for conf in confs_to_count:
            for team in results.get(conf, []):
                qualified_count[team] += 1
                sim_qualified.add(team)
        for team in results.get("Intercontinental", []):
            qualified_count[team] += 1
            sim_qualified.add(team)

        if sim_qualified == exact_match_set:
            exact_match_count += 1

        debutants_in_sim = sum(1 for t in never_wc_teams if t in sim_qualified)
        for t in never_wc_teams:
            if t in sim_qualified:
                never_qualified_count[t] += 1
        total_debutants += debutants_in_sim
        if debutants_in_sim > 0:
            debutant_sim_count += 1

    avg_debutants = total_debutants / num_sims if num_sims > 0 else 0.0
    return (
        {name: (count / num_sims) * 100 for name, count in qualified_count.items()},
        exact_match_count,
        {name: (count / num_sims) * 100 for name, count in never_qualified_count.items()},
        debutant_sim_count,
        avg_debutants,
    )


def print_probability_table(probs: Dict[str, float], limit: int = 48) -> None:
    print(f"\n{'2030 World Cup Qualification Probabilities':^65}")
    print(f"{f'(Top {limit} of {len(probs)} teams from {NUM_SIMULATIONS:,} simulations)':^65}")
    print("=" * 65)
    sorted_probs = sorted(probs.items(), key=lambda x: x[1], reverse=True)
    for team, prob in sorted_probs[:limit]:
        if prob > 0:
            print(f"{team:<30} {prob:>5.1f}%")


def print_exact_match_probability(num_sims: int, exact_count: int) -> None:
    pct = (exact_count / num_sims) * 100 if num_sims > 0 else 0.0
    team_count = TOTAL_TEAMS_ACTIVE if not UEFA_PARTICIPATING else TOTAL_TEAMS
    print(f"\n{'Exact World Cup field replication':^65}")
    print("=" * 65)
    print(f"  Simulations matching all {team_count} teams: {exact_count}/{num_sims}")
    print(f"  Probability: {pct:.4f}%")


def print_never_qualified_probabilities(probs, num_sims, debutant_sim_count, avg_debutants):
    pct = (debutant_sim_count / num_sims) * 100 if num_sims > 0 else 0.0
    print(f"\n{'Debutant Candidates (never at any World Cup)':^65}")
    print("=" * 65)
    print(f"  Chance of at least one new debutant: {debutant_sim_count}/{num_sims} ({pct:.2f}%)")
    print(f"  Average number of debutants per sim: {avg_debutants:.2f}")
    print("-" * 65)
    for team, prob in sorted(probs.items(), key=lambda x: x[1], reverse=True):
        if prob > 0:
            print(f"{team:<30} {prob:>5.1f}%")


def print_summary_table() -> None:
    print(f"\n{'CONFEDERATION':<15} {'BASE':>5} {'HOSTS':>6} {'DIRECT':>7} {'PLAYOFF':>8} {'PARTICIPATING':>13}")
    print("-" * 63)
    for conf, cfg in CONFEDERATIONS.items():
        participating = "Yes" if (conf != "UEFA" or UEFA_PARTICIPATING) else "No"
        print(f"{conf:<15} {cfg['base_slots']:>5} {cfg['auto_hosts']:>6} "
              f"{cfg['remaining_direct_slots']:>7} {cfg['playoff_slots']:>8} {participating:>13}")
    print("-" * 63)
    active_confs = CONFEDERATIONS.values() if UEFA_PARTICIPATING else \
        [cfg for conf, cfg in CONFEDERATIONS.items() if conf != "UEFA"]
    print(f"{'TOTAL':<15} {sum(c['base_slots'] for c in active_confs):>5} "
          f"{sum(c['auto_hosts'] for c in active_confs):>6} "
          f"{sum(c['remaining_direct_slots'] for c in active_confs):>7} "
          f"{sum(c['playoff_slots'] for c in active_confs):>8} {'':>13}")


def print_qualified_teams(results: Dict[str, List[str]]) -> None:
    print(f"\n{'2030 FIFA World Cup - Qualified Teams':^65}")
    print("=" * 65)
    confs = ("UEFA", "CAF", "CONMEBOL", "AFC", "CONCACAF", "OFC") if UEFA_PARTICIPATING \
        else ("CAF", "CONMEBOL", "AFC", "CONCACAF", "OFC")
    for conf in confs:
        direct = results.get(conf, [])
        playoff = results.get(f"{conf}_playoff", [])
        print(f"\n{conf} ({len(direct)} direct, {len(playoff)} playoff):")
        if direct:
            print("  Direct qualifiers:")
            for i in range(0, len(direct), 4):
                row = direct[i:i + 4]
                print("    " + "  ".join(f"{t:<20}" for t in row))
        if playoff:
            print("  Playoff qualifier:")
            print("    " + ", ".join(playoff))
    inter = results.get("Intercontinental", [])
    if inter:
        print(f"\nIntercontinental Playoff Winners ({len(inter)}):")
        print("  " + ", ".join(inter))


def run_inline_tests() -> None:
    import logging as _logging
    _logging.basicConfig(level=_logging.WARNING)

    assert poisson_goals(0) == 0
    random.seed(0)
    h, a = simulate_match(TeamRecord("A", "UEFA", elo=2000), TeamRecord("B", "UEFA", elo=1000))
    assert isinstance(h, int) and isinstance(a, int)

    r = {"A": TeamRecord("A", "UEFA", elo=1000), "B": TeamRecord("B", "UEFA", elo=1000)}
    apply_result(r, "A", "B", 1, 0)
    assert r["A"].points == 3 and r["B"].points == 0
    assert sort_records(r)[0].name == "A"

    assert resolve_elo("Spain") == 2287
    assert resolve_elo("Unknown") == DEFAULT_ELO
    assert resolve_elo("Türkiye") == ELO_RATINGS["Turkey"]
    assert resolve_elo("China PR") == ELO_RATINGS["China"]

    random.seed(1)
    res = run_qualifying_simulation(seed=1)
    total = sum(len(v) for k, v in res.items() if "playoff" not in k)
    assert total == TOTAL_TEAMS_ACTIVE, f"Expected {TOTAL_TEAMS_ACTIVE}, got {total}"

    for conf in HOST_NATIONS:
        if conf == "UEFA" and not UEFA_PARTICIPATING:
            continue
        for host in HOST_NATIONS[conf]:
            assert host in res[conf], f"Host {host} missing from {conf}"

    probs, _, _, _, _ = run_monte_carlo(10, seed=42)
    if UEFA_PARTICIPATING:
        assert len(probs) == len(set(t for cfg in CONFEDERATIONS.values() for t in cfg["member_nations"]))
    else:
        non_uefa = {t for conf, cfg in CONFEDERATIONS.items() if conf != "UEFA" for t in cfg["member_nations"]}
        assert len(probs) == len(non_uefa)

    print("✅ All inline tests passed")


if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] == "--test":
        run_inline_tests()
    elif len(sys.argv) > 1 and sys.argv[1] == "--single":
        seed = int(sys.argv[2]) if len(sys.argv) > 2 else None
        results = run_qualifying_simulation(seed=seed)
        print_qualified_teams(results)
        total = sum(len(v) for k, v in results.items() if "playoff" not in k)
        print(f"\nSlots filled: {total}/{TOTAL_TEAMS_ACTIVE}")
    else:
        print_summary_table()
        validate_totals()

        seed = None
        if len(sys.argv) > 1:
            try:
                seed = int(sys.argv[1])
            except ValueError:
                pass

        # Generate random seed if none provided, and display it for reproducibility
        if seed is None:
            seed = random.randint(0, 2**31 - 1)
            print(f"\nUsing random seed: {seed} (pass as argument to reproduce)")

        print(f"\nRunning Monte Carlo simulation ({NUM_SIMULATIONS:,} iterations)...")
        probabilities, exact_count, never_qualified_probs, debutant_sim_count, avg_debutants = \
            run_monte_carlo(NUM_SIMULATIONS, seed=seed)

        print_probability_table(probabilities, limit=48)
        print_exact_match_probability(NUM_SIMULATIONS, exact_count)
        print_never_qualified_probabilities(never_qualified_probs, NUM_SIMULATIONS,
                                           debutant_sim_count, avg_debutants)