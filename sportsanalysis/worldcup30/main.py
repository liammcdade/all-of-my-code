import logging
import math
import random
import sys
from dataclasses import dataclass
from typing import Dict, List, Tuple
from tqdm import tqdm

logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")
logger = logging.getLogger(__name__)

DEFAULT_ELO: int = 1000
ELO_K_FACTOR: int = 20
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
        "member_nations": ["Argentina", "Bolivia", "Brazil", "Chile", "Colombia", "Ecuador", "Paraguay", "Peru", "Uruguay", "Venezuela"],
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
            "Mexico", "Canada", "United States", "Panama", "Costa Rica", "Honduras",
            "Jamaica", "Haiti", "Guatemala", "Trinidad and Tobago", "Curaçao", "Suriname",
            "Martinique", "Guadeloupe", "Nicaragua", "El Salvador", "Guyana", "Dominican Republic",
            "Cuba", "French Guiana", "Saint Vincent and the Grenadines", "Puerto Rico",
            "Bermuda", "Grenada", "Saint Lucia", "Saint Kitts and Nevis", "Belize",
            "Montserrat", "Dominica", "Sint Maarten", "Saint Martin", "Bonaire",
            "Antigua and Barbuda", "Barbados", "Aruba", "Cayman Islands", "Bahamas",
            "Turks and Caicos Islands", "British Virgin Islands", "Anguilla", "US Virgin Islands"
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
TOTAL_HOSTS = 6
TOTAL_DIRECT = 40
PLAYOFF_WINNERS = 2
TOTAL_TEAMS = 48
NUM_SIMULATIONS = 10000

UEFA_PARTICIPATING = False

UEFA_TOTAL_HOSTS = sum(cfg["auto_hosts"] for conf, cfg in CONFEDERATIONS.items() if conf == "UEFA")
UEFA_TOTAL_DIRECT = sum(cfg["remaining_direct_slots"] for conf, cfg in CONFEDERATIONS.items() if conf == "UEFA")

if not UEFA_PARTICIPATING:
    TOTAL_HOSTS_ACTIVE = TOTAL_HOSTS - UEFA_TOTAL_HOSTS
    TOTAL_DIRECT_ACTIVE = TOTAL_DIRECT - UEFA_TOTAL_DIRECT
else:
    TOTAL_HOSTS_ACTIVE = TOTAL_HOSTS
    TOTAL_DIRECT_ACTIVE = TOTAL_DIRECT
TOTAL_TEAMS_ACTIVE = TOTAL_HOSTS_ACTIVE + TOTAL_DIRECT_ACTIVE + PLAYOFF_WINNERS
ELO_RATINGS: Dict[str, int] = {
    "Spain": 2259, "Argentina": 2173, "England": 2125, "France": 2070, "Colombia": 2003,
    "Portugal": 1995, "Brazil": 1993, "Netherlands": 1971, "Norway": 1951, "Belgium": 1948,
    "Switzerland": 1928, "Mexico": 1913, "Germany": 1908, "Morocco": 1901, "Japan": 1888,
    "Croatia": 1882, "Ecuador": 1871, "Denmark": 1869, "Italy": 1869, "Turkey": 1852,
    "Uruguay": 1841, "Austria": 1821, "Senegal": 1816, "Paraguay": 1814, "Australia": 1795,
    "Ukraine": 1780, "Russia": 1772, "Nigeria": 1767, "Iran": 1764, "Algeria": 1756,
    "United States": 1747, "Scotland": 1745, "Greece": 1744, "Egypt": 1742, "Serbia": 1734,
    "Venezuela": 1733, "Sweden": 1731, "Canada": 1729, "Ivory Coast": 1727, "South Korea": 1723,
    "Chile": 1717, "Kosovo": 1714, "Hungary": 1710, "Poland": 1710, "DR Congo": 1704,
    "Peru": 1699, "Ireland": 1699, "Wales": 1682, "Slovenia": 1682, "Czech Republic": 1680,
    "Slovakia": 1667, "Panama": 1658, "Georgia": 1654, "Israel": 1647, "Romania": 1639,
    "Uzbekistan": 1631, "Jordan": 1628, "Bolivia": 1621, "Cape Verde": 1619, "Albania": 1616,
    "Cameroon": 1614, "Costa Rica": 1608, "Bosnia and Herzegovina": 1605, "Saudi Arabia": 1596,
    "North Macedonia": 1589, "Mali": 1588, "Ghana": 1570, "Honduras": 1570, "Iceland": 1568,
    "Tunisia": 1562, "Iraq": 1561, "South Africa": 1559, "Angola": 1542, "United Arab Emirates": 1540,
    "Finland": 1536, "New Zealand": 1534, "Burkina Faso": 1529, "Jamaica": 1527, "Belarus": 1522,
    "Haiti": 1517, "Guatemala": 1505, "Oman": 1480, "Syria": 1479, "Palestine": 1465,
    "Guinea": 1463, "Montenegro": 1461, "Bulgaria": 1458, "Luxembourg": 1450, "Curaçao": 1438,
    "Suriname": 1431, "Kazakhstan": 1428, "China": 1424, "Libya": 1420, "Gambia": 1419,
    "Bahrain": 1414, "Qatar": 1411, "Benin": 1405, "Gabon": 1401, "Uganda": 1394,
    "Trinidad and Tobago": 1386, "Niger": 1382, "Madagascar": 1380, "Togo": 1379, "Thailand": 1376,
    "Armenia": 1373, "North Korea": 1373, "Indonesia": 1372, "Zimbabwe": 1372, "Zambia": 1371,
    "Kenya": 1363, "Estonia": 1360, "Vietnam": 1353, "Sudan": 1350, "Mozambique": 1342,
    "El Salvador": 1342, "Sierra Leone": 1341, "Rwanda": 1336, "Nicaragua": 1333, "Kuwait": 1332,
    "Mauritania": 1329, "Azerbaijan": 1322, "Cyprus": 1314, "Tanzania": 1313, "Liberia": 1304,
    "Namibia": 1303, "Kyrgyzstan": 1295, "Malaysia": 1293, "Guyana": 1292, "Lebanon": 1288,
    "Latvia": 1288, "Ethiopia": 1287, "New Caledonia": 1286, "Burundi": 1285, "Dominican Republic": 1283,
    "Lithuania": 1279, "Moldova": 1270, "Botswana": 1267, "Malta": 1255, "Guinea-Bissau": 1248,
    "Malawi": 1239, "Cuba": 1239, "French Guiana": 1221, "Turkmenistan": 1209, "Congo": 1206,
    "Lesotho": 1198, "Yemen": 1195, "Philippines": 1179, "Tahiti": 1179, "Eswatini": 1148,
    "Saint Vincent and the Grenadines": 1141, "Papua New Guinea": 1136, "Puerto Rico": 1135,
    "Singapore": 1134, "India": 1128, "Bermuda": 1117, "Vanuatu": 1117, "Fiji": 1104,
    "Hong Kong": 1101, "Grenada": 1098, "Andorra": 1080, "Chad": 1073, "Belize": 1073,
    "Mauritius": 1073, "Solomon Islands": 1054, "Saint Kitts and Nevis": 1030, "Gibraltar": 1011,
    "Saint Lucia": 1003, "Bhutan": 623, "Sri Lanka": 836, "Mongolia": 726, "Maldives": 801,
    "American Samoa": 369, "Guam": 706, "Cook Islands": 623, "Samoa": 730, "Niue": 496,
    "Tonga": 521, "Timor-Leste": 734, "Macau": 589, "Brunei": 572, "Myanmar": 982,
    "Laos": 734, "Cambodia": 871, "Pakistan": 909, "Nepal": 893, "Bangladesh": 942,
    "Martinique": 1202, "Guadeloupe": 1152, "Sint Maarten": 603,
    "Saint Martin": 584, "Bonaire": 554, "Antigua and Barbuda": 553,
    "Barbados": 547, "Aruba": 542, "Cayman Islands": 433, "Bahamas": 387,
    "Turks and Caicos Islands": 272, "British Virgin Islands": 160,
    "Anguilla": 149, "US Virgin Islands": 116
}
CONCACAF_RANKING_ORDER = [
    "Mexico", "Canada", "United States", "Panama", "Costa Rica", "Honduras",
    "Jamaica", "Haiti", "Guatemala", "Trinidad and Tobago", "Curaçao", "Suriname",
    "Martinique", "Guadeloupe", "Nicaragua", "El Salvador", "Guyana", "Dominican Republic",
    "Cuba", "French Guiana", "Saint Vincent and the Grenadines", "Puerto Rico",
    "Bermuda", "Grenada", "Saint Lucia", "Saint Kitts and Nevis", "Belize",
    "Montserrat", "Dominica", "Sint Maarten", "Saint Martin", "Bonaire",
    "Antigua and Barbuda", "Barbados", "Aruba", "Cayman Islands", "Bahamas",
    "Turks and Caicos Islands", "British Virgin Islands", "Anguilla", "US Virgin Islands"
]
AFC_RANKING_ORDER = [
    "Japan", "Iran", "South Korea", "Australia", "Qatar", "Saudi Arabia", "Iraq",
    "Uzbekistan", "United Arab Emirates", "Oman", "Jordan", "Bahrain", "China",
    "Syria", "Vietnam", "Palestine", "Thailand", "Tajikistan", "Lebanon", "India",
    "Malaysia", "Kuwait", "Indonesia", "Kyrgyzstan", "North Korea", "Turkmenistan",
    "Philippines", "Hong Kong", "Chinese Taipei", "Yemen", "Afghanistan", "Myanmar",
    "Singapore", "Maldives", "Nepal", "Pakistan", "Bangladesh", "Sri Lanka",
    "Cambodia", "Mongolia", "Bhutan", "Macau", "Laos", "Brunei", "Timor-Leste", "Guam",
]

WORLD_CUP_2026_TEAMS = {
    "Austria", "Belgium", "Bosnia and Herzegovina", "Croatia", "Czech Republic", "England",
    "France", "Germany", "Netherlands", "Norway", "Portugal", "Scotland", "Spain",
    "Sweden", "Switzerland", "Türkiye",
    "Argentina", "Brazil", "Colombia", "Ecuador", "Paraguay", "Uruguay",
    "Algeria", "Cape Verde", "DR Congo", "Egypt", "Ghana", "Ivory Coast",
    "Morocco", "Senegal", "South Africa", "Tunisia",
    "Australia", "Iran", "Iraq", "Japan", "Jordan", "Qatar", "Saudi Arabia",
    "South Korea", "Uzbekistan",
    "Canada", "Curaçao", "Haiti", "Mexico", "Panama", "United States",
    "New Zealand",
}
ALL_HISTORICAL_WORLD_CUP_TEAMS = {
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
    "United States",
    "Algeria", "Angola", "Cape Verde", "Cameroon", "DR Congo", "Egypt",
    "Ghana", "Ivory Coast", "Morocco", "Nigeria", "Senegal", "South Africa",
    "Togo", "Tunisia",
    "Australia", "China", "Indonesia", "Iran", "Iraq", "Japan", "Jordan",
    "Kuwait", "North Korea", "Qatar", "Saudi Arabia", "South Korea",
    "United Arab Emirates", "Uzbekistan",
    "New Zealand",
}


@dataclass(slots=True)
class TeamRecord:
    name: str
    confederation: str
    elo: int = DEFAULT_ELO
    points: int = 0
    goals_for: int = 0
    goals_against: int = 0

    @property
    def goal_difference(self) -> int:
        return self.goals_for - self.goals_against


def poisson_goals(expected: float) -> int:
    """Generate Poisson-distributed goals based on expected goals."""
    if expected < 0:
        raise ValueError("Expected goals cannot be negative")
    if expected == 0:
        return 0
    L = math.exp(-expected)
    k = 0
    p = 1.0
    while True:
        k += 1
        p *= random.random()
        if p <= L:
            return k - 1


def simulate_match(home: TeamRecord, away: TeamRecord) -> Tuple[int, int]:
    home_adv = HOME_ADVANTAGE_ELO.get(home.confederation, 0)
    diff = float(home.elo) - float(away.elo) + float(home_adv)
    home_xg = 1.45 + (diff * 0.001)
    away_xg = 1.10 - (diff * 0.001)
    return poisson_goals(max(0.1, home_xg)), poisson_goals(max(0.1, away_xg))


def update_elo(home: TeamRecord, away: TeamRecord, hg: int, ag: int) -> None:
    diff = float(home.elo) - float(away.elo) + float(HOME_ADVANTAGE_ELO.get(home.confederation, 0))
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


def apply_result(records: Dict[str, TeamRecord], home_name: str, away_name: str, hg: int, ag: int) -> None:
    home = records[home_name]
    away = records[away_name]
    home.goals_for += hg
    home.goals_against += ag
    away.goals_for += ag
    away.goals_against += hg
    if hg > ag:
        home.points += 3
    elif hg < ag:
        away.points += 3
    else:
        home.points += 1
        away.points += 1
    update_elo(home, away, hg, ag)


def sort_records(records: Dict[str, TeamRecord]) -> List[TeamRecord]:
    return sorted(records.values(), key=lambda r: (r.points, r.goal_difference, r.goals_for), reverse=True)


def resolve_elo(name: str) -> int:
    if name in ELO_RATINGS:
        return ELO_RATINGS[name]
    aliases = {"Republic of Ireland": "Ireland", "DR Congo": "Dem. Rep. of Congo", "Republic of the Congo": "Congo", "Türkiye": "Turkey"}
    alias = aliases.get(name)
    return ELO_RATINGS.get(alias, DEFAULT_ELO) if alias else DEFAULT_ELO


def simulate_conmebol_double_round_robin(teams: List[TeamRecord]) -> Tuple[List[str], List[str]]:
    records = {t.name: t for t in teams}
    for i in range(len(teams)):
        for j in range(i + 1, len(teams)):
            hg, ag = simulate_match(teams[i], teams[j])
            apply_result(records, teams[i].name, teams[j].name, hg, ag)
            hg, ag = simulate_match(teams[j], teams[i])
            apply_result(records, teams[j].name, teams[i].name, hg, ag)
    ranked = sort_records(records)
    return [t.name for t in ranked[:3]], [ranked[3].name]


def simulate_conmebol_qualifying(member_names: List[str]) -> Tuple[List[str], List[str]]:
    teams = [TeamRecord(name, "CONMEBOL", elo=resolve_elo(name)) for name in member_names]
    return simulate_conmebol_double_round_robin(teams)


def simulate_round_robin_qualifying(member_names: List[str], confederation: str, direct_slots: int) -> Tuple[List[str], List[str]]:
    teams = [TeamRecord(name, confederation, elo=resolve_elo(name)) for name in member_names]
    records = {t.name: t for t in teams}
    for i in range(len(teams)):
        for j in range(i + 1, len(teams)):
            hg, ag = simulate_match(teams[i], teams[j])
            apply_result(records, teams[i].name, teams[j].name, hg, ag)
            hg, ag = simulate_match(teams[j], teams[i])
            apply_result(records, teams[j].name, teams[i].name, hg, ag)
    ranked = sort_records(records)
    return [t.name for t in ranked[:direct_slots]], [ranked[direct_slots].name]


def simulate_uefa_swiss_format(member_names: List[str]) -> Tuple[List[str], List[str]]:
    all_teams = [TeamRecord(name, "UEFA", elo=resolve_elo(name)) for name in member_names]
    all_teams.sort(key=lambda t: t.elo, reverse=True)
    league1 = all_teams[:36]
    league2 = all_teams[36:]
    random.shuffle(league1)
    l1_groups = [league1[i:i + 12] for i in range(0, 36, 12)]
    l1_group_results = []
    for group in l1_groups:
        group.sort(key=lambda t: t.elo, reverse=True)
        records = {t.name: t for t in group}
        for team in group:
            opponents = []
            for pot in (group[0:4], group[4:8], group[8:12]):
                available = [t for t in pot if t.name != team.name]
                random.shuffle(available)
                opponents.extend(available[:2])
            for opp in opponents:
                if random.random() > 0.5:
                    hg, ag = simulate_match(team, opp)
                    apply_result(records, team.name, opp.name, hg, ag)
                else:
                    hg, ag = simulate_match(opp, team)
                    apply_result(records, opp.name, team.name, hg, ag)
        l1_group_results.append(sort_records(records))
    l2_competitors = league2[:18]
    l2_bye = league2[18] if len(league2) > 18 else None
    random.shuffle(l2_competitors)
    l2_groups = [l2_competitors[i:i + 6] for i in range(0, 18, 6)]
    l2_top6 = []
    for group in l2_groups:
        records = {t.name: t for t in group}
        for i in range(len(group)):
            for j in range(i + 1, len(group)):
                hg, ag = simulate_match(group[i], group[j])
                apply_result(records, group[i].name, group[j].name, hg, ag)
                hg, ag = simulate_match(group[j], group[i])
                apply_result(records, group[j].name, group[i].name, hg, ag)
        ranked = sort_records(records)
        l2_top6.append(ranked[0])
        l2_top6.append(ranked[1])
    playoff_entrants_l2 = l2_top6[:]
    if l2_bye:
        playoff_entrants_l2.append(l2_bye)
    hosts = HOST_NATIONS.get("UEFA", [])
    all_l1_non_hosts = [t for gr in l1_group_results for t in gr if t.name not in hosts]
    all_l1_non_hosts.sort(key=lambda t: (t.points, t.goal_difference, t.goals_for), reverse=True)
    direct_qualifiers = [t.name for t in all_l1_non_hosts[:9]]
    playoff_pool = all_l1_non_hosts[9:21] + playoff_entrants_l2
    playoff_pool = playoff_pool[:18]
    random.shuffle(playoff_pool)
    playoff_groups = [playoff_pool[i:i + 3] for i in range(0, 18, 3)]
    playoff_winners = []
    for pg in playoff_groups:
        if not pg:
            continue
        records = {t.name: t for t in pg}
        for i in range(len(pg)):
            for j in range(i + 1, len(pg)):
                hg, ag = simulate_match(pg[i], pg[j])
                apply_result(records, pg[i].name, pg[j].name, hg, ag)
                hg, ag = simulate_match(pg[j], pg[i])
                apply_result(records, pg[j].name, pg[i].name, hg, ag)
        ranked = sort_records(records)
        playoff_winners.append(ranked[0])
    direct_qualifiers.extend([w.name for w in playoff_winners[:5]])
    uefa_inter = playoff_winners[5].name if len(playoff_winners) > 5 else None
    return direct_qualifiers, [uefa_inter] if uefa_inter else []


def simulate_concacaf_2030_format() -> Tuple[List[str], List[str]]:
    all_teams = [TeamRecord(name, "CONCACAF", elo=resolve_elo(name)) for name in CONCACAF_RANKING_ORDER]
    top13 = all_teams[:13]
    bottom22 = all_teams[13:]
    random.shuffle(bottom22)
    r1_winners = []
    for i in range(0, 22, 2):
        a, b = bottom22[i], bottom22[i + 1]
        h1, a1 = simulate_match(a, b)
        h2, a2 = simulate_match(b, a)
        ta, tb = h1 + a2, a1 + h2
        if ta > tb:
            r1_winners.append(a)
        elif tb > ta:
            r1_winners.append(b)
        else:
            r1_winners.append(random.choice([a, b]))
    r2_pool = top13 + r1_winners
    random.shuffle(r2_pool)
    r2_groups = [r2_pool[i:i + 4] for i in range(0, 24, 4)]
    r2_qualifiers = []
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
    final_groups = [r2_qualifiers[i:i + 4] for i in range(0, 12, 4)]
    direct_qualifiers = []
    third = []
    for group in final_groups:
        records = {t.name: t for t in group}
        for i in range(len(group)):
            for j in range(i + 1, len(group)):
                hg, ag = simulate_match(group[i], group[j])
                apply_result(records, group[i].name, group[j].name, hg, ag)
                hg, ag = simulate_match(group[j], group[i])
                apply_result(records, group[j].name, group[i].name, hg, ag)
        ranked = sort_records(records)
        direct_qualifiers.extend([ranked[0].name, ranked[1].name])
        third.append(ranked[2])
    third.sort(key=lambda t: (t.points, t.goal_difference, t.goals_for), reverse=True)
    t1, t2 = third[0], third[1]
    h1, a1 = simulate_match(t1, t2)
    h2, a2 = simulate_match(t2, t1)
    ta, tb = h1 + a2, a1 + h2
    if ta > tb:
        playoff = [t1.name]
    elif tb > ta:
        playoff = [t2.name]
    else:
        playoff = [random.choice([t1.name, t2.name])]
    return direct_qualifiers, playoff


def simulate_afc_2030_format() -> Tuple[List[str], List[str]]:
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
    r3_pool = r2_advancers[:]
    random.shuffle(r3_pool)
    r3_groups = [r3_pool[i:i + 6] for i in range(0, 18, 6)]
    r3_standings = []
    for group in r3_groups:
        records = {t.name: t for t in group}
        for i in range(6):
            for j in range(i + 1, 6):
                hg, ag = simulate_match(group[i], group[j])
                apply_result(records, group[i].name, group[j].name, hg, ag)
                hg, ag = simulate_match(group[j], group[i])
                apply_result(records, group[j].name, group[i].name, hg, ag)
        r3_standings.append(sort_records(records))
    direct = []
    for g in r3_standings:
        direct.extend([g[0].name, g[1].name])
    r4_teams = [g[2] for g in r3_standings] + [g[3] for g in r3_standings]
    random.shuffle(r4_teams)
    r4_groups = [r4_teams[i:i + 3] for i in range(0, 6, 3)]
    r4_winners = []
    r4_runners = []
    for group in r4_groups:
        records = {t.name: t for t in group}
        for i in range(3):
            for j in range(i + 1, 3):
                hg, ag = simulate_match(group[i], group[j])
                apply_result(records, group[i].name, group[j].name, hg, ag)
                hg, ag = simulate_match(group[j], group[i])
                apply_result(records, group[j].name, group[i].name, hg, ag)
        ranked = sort_records(records)
        r4_winners.append(ranked[0].name)
        r4_runners.append(ranked[1])
    direct.extend(r4_winners)
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
    teams = [TeamRecord(name, "CAF", elo=resolve_elo(name)) for name in CONFEDERATIONS["CAF"]["member_nations"]]
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
    winners, runners = [], []
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
    best = runners[0].name if runners else None
    return winners, [best] if best else []


def simulate_intercontinental_playoff(qualifiers: List[str]) -> List[str]:
    if len(qualifiers) < 4:
        raise ValueError("Intercontinental playoff requires at least 4 teams")
    teams = [TeamRecord(name, "InterConfederation", elo=resolve_elo(name)) for name in qualifiers]
    teams.sort(key=lambda t: t.elo, reverse=True)

    def knockout(a, b):
        for _ in range(2):
            hg, ag = simulate_match(a, b)
            if hg != ag:
                return a if hg > ag else b
        return random.choice([a, b])

    if len(teams) == 6:
        return [knockout(teams[0], knockout(teams[2], teams[3])).name,
                knockout(teams[1], knockout(teams[4], teams[5])).name]
    if len(teams) == 5:
        return [knockout(teams[0], knockout(teams[2], teams[3])).name,
                knockout(teams[1], teams[4]).name]
    if len(teams) == 4:
        return [knockout(teams[0], teams[3]).name,
                knockout(teams[1], teams[2]).name]

    winners = []
    for i in range(0, len(teams) - 1, 2):
        winners.append(knockout(teams[i], teams[i + 1]))
    if len(teams) % 2 == 1:
        winners.append(teams[-1])
    return winners[:2]


def validate_totals() -> bool:
    total_hosts = TOTAL_HOSTS_ACTIVE
    total_direct = TOTAL_DIRECT_ACTIVE
    total = total_hosts + total_direct + PLAYOFF_WINNERS
    logger.info("Slot allocation verified: %s/%s", total, TOTAL_TEAMS_ACTIVE)
    return total == TOTAL_TEAMS_ACTIVE


def run_qualifying_simulation(seed: int | None = None) -> Dict[str, List[str]]:
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
    conmebol_non_hosts = [n for n in CONFEDERATIONS["CONMEBOL"]["member_nations"] if n not in HOST_NATIONS["CONMEBOL"]]
    direc, playoff = simulate_conmebol_qualifying(conmebol_non_hosts)
    qualified["CONMEBOL"].extend(direc)
    qualified["CONMEBOL_playoff"] = playoff
    if UEFA_PARTICIPATING:
        uefa_direct, uefa_playoff = simulate_uefa_swiss_format(CONFEDERATIONS["UEFA"]["member_nations"])
        qualified["UEFA"].extend(uefa_direct)
        qualified["UEFA_playoff"] = uefa_playoff
    concacaf_direct, concacaf_playoff = simulate_concacaf_2030_format()
    qualified["CONCACAF"].extend(concacaf_direct)
    qualified["CONCACAF_playoff"] = concacaf_playoff
    afc_direct, afc_playoff = simulate_afc_2030_format()
    qualified["AFC"].extend(afc_direct)
    qualified["AFC_playoff"] = afc_playoff
    for conf in ("CAF", "OFC"):
        members = [n for n in CONFEDERATIONS[conf]["member_nations"] if n not in HOST_NATIONS.get(conf, [])]
        if conf == "CAF":
            d, p = simulate_caf_2030_format()
        else:
            d, p = simulate_round_robin_qualifying(members, conf, CONFEDERATIONS[conf]["remaining_direct_slots"])
        qualified[conf].extend(d)
        qualified[f"{conf}_playoff"] = p
    playoff_teams = [
        qualified["CAF_playoff"][0],
        qualified["CONMEBOL_playoff"][0],
        qualified["AFC_playoff"][0],
        qualified["CONCACAF_playoff"][0],
        qualified["OFC_playoff"][0],
    ]
    if UEFA_PARTICIPATING:
        playoff_teams.append(qualified["UEFA_playoff"][0])
    qualified["Intercontinental"] = simulate_intercontinental_playoff(playoff_teams)
    return qualified


def run_monte_carlo(num_sims: int, seed: int | None = None) -> Tuple[Dict[str, float], int, Dict[str, float], int, float]:
    if UEFA_PARTICIPATING:
        all_teams = sorted({t for cfg in CONFEDERATIONS.values() for t in cfg["member_nations"]})
        never_wc_teams = NEVER_WORLD_CUP_TEAMS_FULL
        exact_match_set = WORLD_CUP_2026_TEAMS
        confs_to_count = ("UEFA", "CAF", "CONMEBOL", "AFC", "CONCACAF", "OFC")
    else:
        all_teams = sorted({t for conf, cfg in CONFEDERATIONS.items() if conf != "UEFA" for t in cfg["member_nations"]})
        never_wc_teams = [t for t in NEVER_WORLD_CUP_TEAMS_FULL if t not in CONFEDERATIONS["UEFA"]["member_nations"]]
        exact_match_set = {t for t in WORLD_CUP_2026_TEAMS if t not in CONFEDERATIONS["UEFA"]["member_nations"]}
        confs_to_count = ("CAF", "CONMEBOL", "AFC", "CONCACAF", "OFC")

    qualified_count: Dict[str, int] = {name: 0 for name in all_teams}
    exact_match_count = 0
    never_qualified_count: Dict[str, int] = {name: 0 for name in never_wc_teams}
    debutant_sim_count = 0
    total_debutants = 0
    if seed is not None:
        random.seed(seed)
    for i in tqdm(range(num_sims), desc="Monte Carlo", unit="sim"):
        results = run_qualifying_simulation()
        sim_qualified = set()
        for conf in confs_to_count:
            for team in results.get(conf, []):
                qualified_count[team] += 1
                sim_qualified.add(team)
        for team in results.get("Intercontinental", []):
            qualified_count[team] += 1
            sim_qualified.add(team)
        if sim_qualified == exact_match_set:
            exact_match_count += 1
        debutants_in_sim = 0
        for team in never_wc_teams:
            if team in sim_qualified:
                never_qualified_count[team] += 1
                debutants_in_sim += 1
        total_debutants += debutants_in_sim
        if debutants_in_sim > 0:
            debutant_sim_count += 1
    avg_debutants = total_debutants / num_sims if num_sims > 0 else 0.0
    return {name: (count / num_sims) * 100 for name, count in qualified_count.items()}, exact_match_count, {name: (count / num_sims) * 100 for name, count in never_qualified_count.items()}, debutant_sim_count, avg_debutants


def print_probability_table(probs: Dict[str, float]) -> None:
    print(f"\n{'2030 World Cup Qualification Probabilities':^65}")
    print(f"{f'({NUM_SIMULATIONS:,} simulations)' :^65}")
    print("=" * 65)
    for team, prob in sorted(probs.items(), key=lambda x: x[1], reverse=True):
        if prob > 0:
            print(f"{team:<30} {prob:>5.1f}%")


def print_exact_match_probability(num_sims: int, exact_count: int) -> None:
    pct = (exact_count / num_sims) * 100 if num_sims > 0 else 0.0
    team_count = TOTAL_TEAMS_ACTIVE if not UEFA_PARTICIPATING else TOTAL_TEAMS
    print(f"\n{'Exact World Cup field replication':^65}")
    print("=" * 65)
    print(f"  Simulations matching all {team_count} teams: {exact_count}/{num_sims}")
    print(f"  Probability: {pct:.4f}%")


def print_never_qualified_probabilities(probs: Dict[str, float], num_sims: int, debutant_sim_count: int, avg_debutants: float) -> None:
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
        print(f"{conf:<15} {cfg['base_slots']:>5} {cfg['auto_hosts']:>6} {cfg['remaining_direct_slots']:>7} {cfg['playoff_slots']:>8} {participating:>13}")
    print("-" * 63)
    if UEFA_PARTICIPATING:
        total_base = sum(cfg["base_slots"] for cfg in CONFEDERATIONS.values())
        total_hosts = sum(cfg["auto_hosts"] for cfg in CONFEDERATIONS.values())
        total_direct = sum(cfg["remaining_direct_slots"] for cfg in CONFEDERATIONS.values())
        total_playoff = sum(cfg["playoff_slots"] for cfg in CONFEDERATIONS.values())
    else:
        total_base = sum(cfg["base_slots"] for conf, cfg in CONFEDERATIONS.items() if conf != "UEFA")
        total_hosts = sum(cfg["auto_hosts"] for conf, cfg in CONFEDERATIONS.items() if conf != "UEFA")
        total_direct = sum(cfg["remaining_direct_slots"] for conf, cfg in CONFEDERATIONS.items() if conf != "UEFA")
        total_playoff = sum(cfg["playoff_slots"] for conf, cfg in CONFEDERATIONS.items() if conf != "UEFA")
    print(f"{'TOTAL':<15} {total_base:>5} {total_hosts:>6} {total_direct:>7} {total_playoff:>8} {'':>13}")


def print_qualified_teams(results: Dict[str, List[str]]) -> None:
    print(f"\n{'2030 FIFA World Cup - Qualified Teams':^65}")
    print("=" * 65)
    confs = ("UEFA", "CAF", "CONMEBOL", "AFC", "CONCACAF", "OFC") if UEFA_PARTICIPATING else ("CAF", "CONMEBOL", "AFC", "CONCACAF", "OFC")
    for conf in confs:
        direct = results.get(conf, [])
        playoff = results.get(f"{conf}_playoff", [])
        print(f"\n{conf} ({len(direct)} direct, {len(playoff)} playoff):")
        if direct:
            print("  Direct qualifiers:")
            for i in range(0, len(direct), 4):
                row = direct[i : i + 4]
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
    assert resolve_elo("Spain") == 2259
    assert resolve_elo("Unknown") == DEFAULT_ELO
    assert resolve_elo("Türkiye") == ELO_RATINGS["Turkey"]
    random.seed(1)
    res = run_qualifying_simulation(seed=1)
    active_key = "TOTAL_TEAMS_ACTIVE"
    total = sum(len(v) for k, v in res.items() if "playoff" not in k)
    assert total == TOTAL_TEAMS_ACTIVE, total
    for conf in HOST_NATIONS:
        if conf == "UEFA" and not UEFA_PARTICIPATING:
            continue
        for host in HOST_NATIONS[conf]:
            assert host in res[conf]
    probs, _, _, _, _ = run_monte_carlo(10, seed=42)
    if UEFA_PARTICIPATING:
        assert len(probs) == len(get_all_teams())
    else:
        non_uefa_teams = [t for t in get_all_teams() if t not in CONFEDERATIONS["UEFA"]["member_nations"]]
        assert len(probs) == len(non_uefa_teams), f"{len(probs)} != {len(non_uefa_teams)}"
    print("Inline tests passed")


def get_all_teams() -> List[str]:
    return sorted({t for cfg in CONFEDERATIONS.values() for t in cfg["member_nations"]})


NEVER_WORLD_CUP_TEAMS_FULL = sorted({
    t for t in get_all_teams() if t not in ALL_HISTORICAL_WORLD_CUP_TEAMS
})


if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] == "--test":
        run_inline_tests()
    else:
        print_summary_table()
        validate_totals()
        seed = None
        if len(sys.argv) > 1:
            try:
                seed = int(sys.argv[1])
            except ValueError:
                pass
        results = run_qualifying_simulation(seed)
        print_qualified_teams(results)
        total_qualified = sum(len(v) for k, v in results.items() if "playoff" not in k)
        print(f"\nTotal tournament slots filled: {total_qualified}/{TOTAL_TEAMS_ACTIVE}")
        print(f"Hosts: {TOTAL_HOSTS_ACTIVE} | Direct: {TOTAL_DIRECT_ACTIVE} | Playoff winners: {PLAYOFF_WINNERS}")
        print(f"\nRunning Monte Carlo simulation ({NUM_SIMULATIONS:,} iterations)...")
        probabilities, exact_count, never_qualified_probs, debutant_sim_count, avg_debutants = run_monte_carlo(NUM_SIMULATIONS, seed=seed)
        print_probability_table(probabilities)
        print_exact_match_probability(NUM_SIMULATIONS, exact_count)
        print_never_qualified_probabilities(never_qualified_probs, NUM_SIMULATIONS, debutant_sim_count, avg_debutants)
