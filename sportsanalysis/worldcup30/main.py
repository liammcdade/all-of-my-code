from __future__ import annotations

import math
import random
from dataclasses import dataclass
from typing import Dict, List, Tuple, Set


# Constants
DEFAULT_ELO: int = 1000
ELO_K_FACTOR: int = 20
ELO_EXPECTED_DENOMINATOR: float = 400.0
HOME_ADVANTAGE_ELO: Dict[str, int] = {
    "CONMEBOL": 70,
    "UEFA": 45,
    "AFC": 60,
    "CAF": 55,
    "CONCACAF": 55,
    "OFC": 55,
    "InterConfederation": 0,
}
HOST_NATIONS: Dict[str, List[str]] = {
    "UEFA": ["Spain", "Portugal"],
    "CAF": ["Morocco"],
    "CONMEBOL": ["Argentina", "Uruguay", "Paraguay"],
}

CONFEDERATIONS: Dict[str, Dict] = {
    "UEFA": {
        "base_slots": 16,
        "auto_hosts": 2,
        "remaining_direct_slots": 14, # 9 Direct + 5 via Playoffs
        "playoff_slots": 1, # Represents the final UEFA representative in Intercontinental
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
        "base_slots": 9,
        "auto_hosts": 1,
        "remaining_direct_slots": 8,
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
        "base_slots": 6,
        "auto_hosts": 3,
        "remaining_direct_slots": 3,
        "playoff_slots": 1,
        "member_nations": [
            "Argentina", "Bolivia", "Brazil", "Chile", "Colombia", "Ecuador", "Paraguay",
            "Peru", "Uruguay", "Venezuela",
        ],
    },
    "AFC": {
        "base_slots": 8,
        "auto_hosts": 0,
        "remaining_direct_slots": 8,
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
        "base_slots": 6,
        "auto_hosts": 0,
        "remaining_direct_slots": 6, 
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
        "base_slots": 1,
        "auto_hosts": 0,
        "remaining_direct_slots": 1,
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
NUM_SIMULATIONS = 1000

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
    # CONCACAF Specific Updates
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


@dataclass
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

    def reset(self) -> None:
        self.points = 0
        self.goals_for = 0
        self.goals_against = 0


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
    """Simulate a match using calibrated xG and Elo difference."""
    home_advantage = HOME_ADVANTAGE_ELO.get(home.confederation, 0)
    diff = float(home.elo) - float(away.elo) + float(home_advantage)
    home_xg = 1.45 + (diff * 0.001)
    away_xg = 1.10 - (diff * 0.001)
    return poisson_goals(max(0.1, home_xg)), poisson_goals(max(0.1, away_xg))


def update_elo(home: TeamRecord, away: TeamRecord, hg: int, ag: int) -> None:
    """Update Elo ratings based on match outcome."""
    diff = float(home.elo) - float(away.elo) + float(HOME_ADVANTAGE_ELO.get(home.confederation, 0))
    home_expected = 1.0 / (1.0 + 10.0 ** (-diff / ELO_EXPECTED_DENOMINATOR))
    away_expected = 1.0 / (1.0 + 10.0 ** (diff / ELO_EXPECTED_DENOMINATOR))
    
    if hg > ag:
        home_actual = 1.0
        away_actual = 0.0
    elif hg < ag:
        home_actual = 0.0
        away_actual = 1.0
    else:
        home_actual = 0.5
        away_actual = 0.5
    
    home.elo = int(home.elo + ELO_K_FACTOR * (home_actual - home_expected))
    away.elo = int(away.elo + ELO_K_FACTOR * (away_actual - away_expected))


def apply_result(
    records: Dict[str, TeamRecord],
    home_name: str,
    away_name: str,
    hg: int,
    ag: int,
) -> None:
    """Apply a match result to standings."""
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
    """Sort teams by points, goal difference, goals for."""
    return sorted(
        records.values(),
        key=lambda r: (r.points, r.goal_difference, r.goals_for),
        reverse=True,
    )


def resolve_elo(name: str) -> int:
    """Resolve Elo rating."""
    if name in ELO_RATINGS:
        return ELO_RATINGS[name]
    aliases: Dict[str, str] = {
        "Republic of Ireland": "Ireland",
        "DR Congo": "Dem. Rep. of Congo",
        "Republic of the Congo": "Congo",
    }
    alias_name = aliases.get(name)
    if alias_name and alias_name in ELO_RATINGS:
        return ELO_RATINGS[alias_name]
    return DEFAULT_ELO


# --- CONMEBOL ---
def simulate_conmebol_double_round_robin(teams: List[TeamRecord]) -> Tuple[List[str], List[str]]:
    records = {t.name: t for t in teams}
    for i in range(len(teams)):
        home = teams[i]
        for j in range(i + 1, len(teams)):
            away = teams[j]
            hg, ag = simulate_match(home, away)
            apply_result(records, home.name, away.name, hg, ag)
            hg, ag = simulate_match(away, home)
            apply_result(records, away.name, home.name, hg, ag)
            
    sorted_teams = sort_records(records)
    return [t.name for t in sorted_teams[:3]], [sorted_teams[3].name]


def simulate_conmebol_qualifying(member_names: List[str]) -> Tuple[List[str], List[str]]:
    teams = [TeamRecord(name, "CONMEBOL", elo=resolve_elo(name)) for name in member_names]
    return simulate_conmebol_double_round_robin(teams)


# --- GENERIC ROUND ROBIN (for AFC, CAF, OFC) ---
def simulate_round_robin_qualifying(
    member_names: List[str],
    confederation: str,
    direct_slots: int,
) -> Tuple[List[str], List[str]]:
    teams = [TeamRecord(name, confederation, elo=resolve_elo(name)) for name in member_names]
    records = {t.name: t for t in teams}
    
    for i in range(len(teams)):
        home = teams[i]
        for j in range(i + 1, len(teams)):
            away = teams[j]
            hg, ag = simulate_match(home, away)
            apply_result(records, home.name, away.name, hg, ag)
            hg, ag = simulate_match(away, home)
            apply_result(records, away.name, home.name, hg, ag)
            
    sorted_teams = sort_records(records)
    return [t.name for t in sorted_teams[:direct_slots]], [sorted_teams[direct_slots].name]


# --- UEFA SWISS FORMAT (UPDATED: 9 Direct + 5 Playoff) ---
# --- UEFA SWISS FORMAT (FIXED: Handles 55 Teams & 19th L2 Team) ---
def simulate_uefa_swiss_format(member_names: List[str]) -> Tuple[List[str], List[str]]:
    all_teams = [TeamRecord(name, "UEFA", elo=resolve_elo(name)) for name in member_names]
    all_teams.sort(key=lambda t: t.elo, reverse=True)
    
    league1_teams = all_teams[:36]
    league2_teams = all_teams[36:] # 19 teams
    
    # --- LEAGUE 1: 3 Groups of 12 ---
    random.shuffle(league1_teams)
    l1_groups = [league1_teams[i:i+12] for i in range(0, 36, 12)]
    
    l1_group_results = []
    
    for group in l1_groups:
        group.sort(key=lambda t: t.elo, reverse=True)
        pot1 = group[0:4]
        pot2 = group[4:8]
        pot3 = group[8:12]
        
        records: Dict[str, TeamRecord] = {t.name: t for t in group}
        
        for team in group:
            opponents = []
            def pick_from_pot(pot: List[TeamRecord]):
                available = [t for t in pot if t.name != team.name]
                random.shuffle(available)
                return available[:2]
                
            opponents.extend(pick_from_pot(pot1))
            opponents.extend(pick_from_pot(pot2))
            opponents.extend(pick_from_pot(pot3))
            
            for opp in opponents:
                if random.random() > 0.5:
                    hg, ag = simulate_match(team, opp)
                    apply_result(records, team.name, opp.name, hg, ag)
                else:
                    hg, ag = simulate_match(opp, team)
                    apply_result(records, opp.name, team.name, hg, ag)
                    
        sorted_group = sort_records(records)
        l1_group_results.append(sorted_group)

    # --- LEAGUE 2: Handle 19 Teams ---
    # 19 teams: 3 Groups of 6 (18 teams) + 1 Lowest Ranked Team (Bye to Playoffs)
    l2_competitors = league2_teams[:18]
    l2_bye_team = league2_teams[18] if len(league2_teams) > 18 else None
    
    random.shuffle(l2_competitors)
    l2_sim_groups = [l2_competitors[i:i+6] for i in range(0, 18, 6)]
    
    l2_top_6 = []
    for group in l2_sim_groups:
        records = {t.name: t for t in group}
        for i in range(len(group)):
            for j in range(i+1, len(group)):
                hg, ag = simulate_match(group[i], group[j])
                apply_result(records, group[i].name, group[j].name, hg, ag)
                hg, ag = simulate_match(group[j], group[i])
                apply_result(records, group[j].name, group[i].name, hg, ag)
        sorted_g = sort_records(records)
        l2_top_6.append(sorted_g[0]) # Winner
        l2_top_6.append(sorted_g[1]) # Runner-up
        
    # Add the bye team to playoff entrants automatically
    playoff_entrants_l2 = l2_top_6[:]
    if l2_bye_team:
        playoff_entrants_l2.append(l2_bye_team)

    # --- DETERMINE QUALIFIERS ---
    hosts = HOST_NATIONS.get("UEFA", [])
    
    # 1. Direct Qualification (9 places)
    direct_qualifiers = []
    third_placed_teams = []
    fourth_placed_teams = []
    fifth_placed_teams = []
    
    for group_res in l1_group_results:
        # 1st and 2nd qualify directly (if not host)
        for i in [0, 1]:
            team = group_res[i]
            if team.name not in hosts:
                direct_qualifiers.append(team.name)
        
        # Collect 3rd, 4th, 5th for playoff consideration
        if len(group_res) > 2:
            t3 = group_res[2]
            if t3.name not in hosts:
                third_placed_teams.append(t3)
                
        if len(group_res) > 3:
            t4 = group_res[3]
            if t4.name not in hosts:
                fourth_placed_teams.append(t4)
                
        if len(group_res) > 4:
            t5 = group_res[4]
            if t5.name not in hosts:
                fifth_placed_teams.append(t5)

    # Fill remaining direct slots with best 3rd placed teams
    third_placed_teams.sort(key=lambda t: (t.points, t.goal_difference, t.goals_for), reverse=True)
    for t in third_placed_teams:
        if len(direct_qualifiers) < 9:
            direct_qualifiers.append(t.name)
            
    # 2. Playoff Entrants
    playoff_entrants = []
    
    # Remaining 3rd placed teams
    for t in third_placed_teams:
        if t.name not in direct_qualifiers:
            playoff_entrants.append(t)
            
    # All 4th placed teams
    playoff_entrants.extend(fourth_placed_teams)
    
    # Best 3 5th placed teams
    fifth_placed_teams.sort(key=lambda t: (t.points, t.goal_difference, t.goals_for), reverse=True)
    playoff_entrants.extend(fifth_placed_teams[:3])
    
    # Add League 2 qualifiers
    playoff_entrants.extend(playoff_entrants_l2)
    
    # Ensure we have exactly 18 teams for 6 groups of 3
    # If we have more/less due to hosts skipping spots, we adjust.
    # Usually hosts taking direct spots opens up spots for next-in-line.
    # For simplicity, we take the top 18 available non-qualified, non-host teams.
    
    # Re-calculate pool strictly:
    all_l1_non_hosts = []
    for gr in l1_group_results:
        for t in gr:
            if t.name not in hosts:
                all_l1_non_hosts.append(t)
    
    # Sort all L1 non-hosts by performance
    all_l1_non_hosts.sort(key=lambda t: (t.points, t.goal_difference, t.goals_for), reverse=True)
    
    # Direct: Top 9
    direct_qualifiers = [t.name for t in all_l1_non_hosts[:9]]
    
    # Playoff Pool: Next 12 from L1 + Top 6 from L2
    l1_playoff_candidates = all_l1_non_hosts[9:21] # 12 teams
    playoff_pool = l1_playoff_candidates + playoff_entrants_l2
    
    # Trim or pad to 18 if necessary
    playoff_pool = playoff_pool[:18]
    
    # Simulate Playoff: 6 Groups of 3
    random.shuffle(playoff_pool)
    playoff_groups = [playoff_pool[i:i+3] for i in range(0, 18, 3)]
    
    playoff_winners = []
    for pg in playoff_groups:
        if not pg: continue # Safety check
        records = {t.name: t for t in pg}
        for i in range(len(pg)):
            for j in range(i+1, len(pg)):
                hg, ag = simulate_match(pg[i], pg[j])
                apply_result(records, pg[i].name, pg[j].name, hg, ag)
                hg, ag = simulate_match(pg[j], pg[i])
                apply_result(records, pg[j].name, pg[i].name, hg, ag)
        sorted_pg = sort_records(records)
        if sorted_pg:
            playoff_winners.append(sorted_pg[0])
            
    # 6 Winners for 5 Spots. Take top 5 by playoff performance.
    playoff_winners.sort(key=lambda t: (t.points, t.goal_difference, t.goals_for), reverse=True)
    
    # The top 5 qualify for World Cup
    # The 6th place goes to Intercontinental Playoff
    uefa_intercontinental_rep = None
    if len(playoff_winners) > 5:
        uefa_intercontinental_rep = playoff_winners[5].name
        
    return direct_qualifiers, [uefa_intercontinental_rep] if uefa_intercontinental_rep else []


# --- CONCACAF 2030 FORMAT ---
def simulate_concacaf_2030_format() -> Tuple[List[str], List[str]]:
    all_teams = [TeamRecord(name, "CONCACAF", elo=resolve_elo(name)) for name in CONCACAF_RANKING_ORDER]
    
    top_13 = all_teams[:13]
    bottom_22 = all_teams[13:] 
    
    random.shuffle(bottom_22)
    r1_winners = []
    for i in range(0, 22, 2):
        team_a = bottom_22[i]
        team_b = bottom_22[i+1]
        
        hg1, ag1 = simulate_match(team_a, team_b)
        hg2, ag2 = simulate_match(team_b, team_a)
        
        total_a = hg1 + ag2
        total_b = ag1 + hg2
        
        if total_a > total_b:
            r1_winners.append(team_a)
        elif total_b > total_a:
            r1_winners.append(team_b)
        else:
            r1_winners.append(random.choice([team_a, team_b]))
            
    r2_pool = top_13 + r1_winners
    random.shuffle(r2_pool)
    
    r2_groups = [r2_pool[i:i+4] for i in range(0, 24, 4)]
    r2_qualifiers = []
    
    for group in r2_groups:
        records = {t.name: t for t in group}
        for i in range(len(group)):
            for j in range(i+1, len(group)):
                hg, ag = simulate_match(group[i], group[j])
                apply_result(records, group[i].name, group[j].name, hg, ag)
                hg, ag = simulate_match(group[j], group[i])
                apply_result(records, group[j].name, group[i].name, hg, ag)
        
        sorted_group = sort_records(records)
        r2_qualifiers.append(sorted_group[0])
        r2_qualifiers.append(sorted_group[1])
        
    random.shuffle(r2_qualifiers)
    final_groups = [r2_qualifiers[i:i+4] for i in range(0, 12, 4)]
    
    direct_qualifiers = []
    third_placed_candidates = []
    
    for group in final_groups:
        records = {t.name: t for t in group}
        for i in range(len(group)):
            for j in range(i+1, len(group)):
                hg, ag = simulate_match(group[i], group[j])
                apply_result(records, group[i].name, group[j].name, hg, ag)
                hg, ag = simulate_match(group[j], group[i])
                apply_result(records, group[j].name, group[i].name, hg, ag)
        
        sorted_group = sort_records(records)
        direct_qualifiers.append(sorted_group[0].name)
        direct_qualifiers.append(sorted_group[1].name)
        third_placed_candidates.append(sorted_group[2])
        
    third_placed_candidates.sort(key=lambda t: (t.points, t.goal_difference, t.goals_for), reverse=True)
    
    play_in_team_1 = third_placed_candidates[0]
    play_in_team_2 = third_placed_candidates[1]
    
    hg1, ag1 = simulate_match(play_in_team_1, play_in_team_2)
    hg2, ag2 = simulate_match(play_in_team_2, play_in_team_1)
    
    total_1 = hg1 + ag2
    total_2 = ag1 + hg2
    
    if total_1 > total_2:
        playoff_qualifier = [play_in_team_1.name]
    elif total_2 > total_1:
        playoff_qualifier = [play_in_team_2.name]
    else:
        playoff_qualifier = [random.choice([play_in_team_1.name, play_in_team_2.name])]
        
    return direct_qualifiers, playoff_qualifier


# --- AFC 2030 FORMAT ---
def simulate_afc_2030_format() -> Tuple[List[str], List[str]]:
    member_names = CONFEDERATIONS["AFC"]["member_nations"]
    teams = [TeamRecord(name, "AFC", elo=resolve_elo(name)) for name in member_names]
    
    teams.sort(key=lambda t: t.elo, reverse=True)
    
    # Round 1
    round1_candidates = teams[-20:]  # 20 lowest-ranked teams (ranks 27-46)
    round2_teams = teams[:-20]  # top 26 teams
    
    random.shuffle(round1_candidates)
    round1_winners = []
    
    for i in range(0, 20, 2):
        t1 = round1_candidates[i]
        t2 = round1_candidates[i + 1]
        
        hg1, ag1 = simulate_match(t1, t2)
        hg2, ag2 = simulate_match(t2, t1)
        
        total1 = hg1 + ag2
        total2 = ag1 + hg2
        
        if total1 > total2:
            round1_winners.append(t1)
        elif total2 > total1:
            round1_winners.append(t2)
        else:
            round1_winners.append(random.choice([t1, t2]))
    
    # Round 2
    round2_pool = round2_teams + round1_winners
    random.shuffle(round2_pool)
    r2_groups = [round2_pool[i:i + 4] for i in range(0, 36, 4)]
    
    r2_advancers = []
    for group in r2_groups:
        records = {t.name: t for t in group}
        for i in range(4):
            for j in range(i + 1, 4):
                hg, ag = simulate_match(group[i], group[j])
                apply_result(records, group[i].name, group[j].name, hg, ag)
                hg, ag = simulate_match(group[j], group[i])
                apply_result(records, group[j].name, group[i].name, hg, ag)
        sorted_group = sort_records(records)
        r2_advancers.append(sorted_group[0])
        r2_advancers.append(sorted_group[1])
    
    # Round 3
    r3_pool = r2_advancers
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
        sorted_group = sort_records(records)
        r3_standings.append(sorted_group)
    
    # Top 2 from each Round 3 group qualify directly
    direct_qualifiers = []
    for group in r3_standings:
        direct_qualifiers.append(group[0].name)
        direct_qualifiers.append(group[1].name)
    
    # Round 4
    round4_teams = []
    for group in r3_standings:
        round4_teams.append(group[2])
        round4_teams.append(group[3])
    
    random.shuffle(round4_teams)
    r4_groups = [round4_teams[i:i + 3] for i in range(0, 6, 3)]
    
    r4_winners = []
    r4_runners_up = []
    
    for group in r4_groups:
        records = {t.name: t for t in group}
        for i in range(3):
            for j in range(i + 1, 3):
                hg, ag = simulate_match(group[i], group[j])
                apply_result(records, group[i].name, group[j].name, hg, ag)
                hg, ag = simulate_match(group[j], group[i])
                apply_result(records, group[j].name, group[i].name, hg, ag)
        sorted_group = sort_records(records)
        r4_winners.append(sorted_group[0].name)
        r4_runners_up.append(sorted_group[1])
    
    direct_qualifiers.extend(r4_winners)
    
    # Round 5
    r5_team1 = r4_runners_up[0]
    r5_team2 = r4_runners_up[1]
    
    hg1, ag1 = simulate_match(r5_team1, r5_team2)
    hg2, ag2 = simulate_match(r5_team2, r5_team1)
    
    total1 = hg1 + ag2
    total2 = ag1 + hg2
    
    if total1 > total2:
        afc_playoff_rep = r5_team1.name
    elif total2 > total1:
        afc_playoff_rep = r5_team2.name
    else:
        afc_playoff_rep = random.choice([r5_team1.name, r5_team2.name])
    
    return direct_qualifiers, [afc_playoff_rep]


# --- CAF 2030 FORMAT ---
def simulate_caf_2030_format() -> Tuple[List[str], List[str]]:
    member_names = CONFEDERATIONS["CAF"]["member_nations"]
    teams = [TeamRecord(name, "CAF", elo=resolve_elo(name)) for name in member_names]
    
    hosts = HOST_NATIONS.get("CAF", [])
    non_hosts = [t for t in teams if t.name not in hosts]
    
    non_hosts.sort(key=lambda t: t.elo, reverse=True)
    round1_candidates = non_hosts[-10:]  # 10 lowest-ranked teams
    round2_teams = non_hosts[:-10]  # top 43 teams
    
    random.shuffle(round1_candidates)
    round1_winners = []
    
    for i in range(0, 10, 2):
        t1 = round1_candidates[i]
        t2 = round1_candidates[i + 1]
        
        hg1, ag1 = simulate_match(t1, t2)
        hg2, ag2 = simulate_match(t2, t1)
        
        total1 = hg1 + ag2
        total2 = ag1 + hg2
        
        if total1 > total2:
            round1_winners.append(t1)
        elif total2 > total1:
            round1_winners.append(t2)
        else:
            round1_winners.append(random.choice([t1, t2]))
    
    round2_pool = round2_teams + round1_winners
    random.shuffle(round2_pool)
    groups = [round2_pool[i:i + 6] for i in range(0, 48, 6)]
    
    group_winners = []
    group_runners_up = []
    
    for group in groups:
        records = {t.name: t for t in group}
        for i in range(6):
            for j in range(i + 1, 6):
                hg, ag = simulate_match(group[i], group[j])
                apply_result(records, group[i].name, group[j].name, hg, ag)
                hg, ag = simulate_match(group[j], group[i])
                apply_result(records, group[j].name, group[i].name, hg, ag)
        sorted_group = sort_records(records)
        group_winners.append(sorted_group[0].name)
        group_runners_up.append(sorted_group[1])
    
    group_runners_up.sort(key=lambda t: (t.points, t.goal_difference, t.goals_for), reverse=True)
    best_runner_up = group_runners_up[0].name if group_runners_up else None
    
    return group_winners, [best_runner_up] if best_runner_up else []


# --- INTERCONTINENTAL PLAYOFF ---
def simulate_intercontinental_playoff(qualifiers: List[str]) -> List[str]:
    if len(qualifiers) != 6:
        raise ValueError("Intercontinental playoff requires exactly 6 teams")
    
    teams = [TeamRecord(name, "InterConfederation", elo=resolve_elo(name)) for name in qualifiers]
    teams.sort(key=lambda t: t.elo, reverse=True)
    
    def knockout(a, b):
        for _ in range(2):
            hg, ag = simulate_match(a, b)
            if hg != ag:
                return a if hg > ag else b
        return random.choice([a, b])

    winner1 = knockout(teams[2], teams[3])
    winner2 = knockout(teams[4], teams[5])
    
    finalist1 = knockout(teams[0], winner1)
    finalist2 = knockout(teams[1], winner2)
    
    return [finalist1.name, finalist2.name]


# --- MAIN EXECUTION ---
def validate_totals() -> bool:
    total_hosts = sum(cfg["auto_hosts"] for cfg in CONFEDERATIONS.values())
    total_direct = sum(cfg["remaining_direct_slots"] for cfg in CONFEDERATIONS.values())
    total = total_hosts + total_direct + PLAYOFF_WINNERS
    
    print("=== Slot Allocation Verification ===")
    print(f"Hosts:     {total_hosts}")
    print(f"Direct:    {total_direct}")
    print(f"Playoff:   {PLAYOFF_WINNERS}")
    print(f"Total:     {total}")
    print(f"Expected:  {TOTAL_TEAMS}")
    print(f"Status:    {'PASS' if total == TOTAL_TEAMS else 'FAIL'}\n")
    return total == TOTAL_TEAMS


def get_all_teams() -> List[str]:
    teams: List[str] = []
    for cfg in CONFEDERATIONS.values():
        teams.extend(cfg["member_nations"])
    return sorted(set(teams))


def run_qualifying_simulation() -> Dict[str, List[str]]:
    qualified: Dict[str, List[str]] = {
        "UEFA": [], "CAF": [], "CONMEBOL": [], "AFC": [],
        "CONCACAF": [], "OFC": [], "Intercontinental": [],
        "UEFA_playoff": [], "CAF_playoff": [], "CONMEBOL_playoff": [],
        "AFC_playoff": [], "CONCACAF_playoff": [], "OFC_playoff": [],
    }
    
    for conf, hosts in HOST_NATIONS.items():
        qualified[conf].extend(hosts)
    
    conmebol_non_hosts = [n for n in CONFEDERATIONS["CONMEBOL"]["member_nations"] if n not in HOST_NATIONS["CONMEBOL"]]
    direc, playoff = simulate_conmebol_qualifying(conmebol_non_hosts)
    qualified["CONMEBOL"].extend(direc)
    qualified["CONMEBOL_playoff"] = playoff
    
    uefa_direct, uefa_playoff = simulate_uefa_swiss_format(CONFEDERATIONS["UEFA"]["member_nations"])
    qualified["UEFA"].extend(uefa_direct)
    qualified["UEFA_playoff"] = uefa_playoff
    
    cacaf_direct, cacaf_playoff = simulate_concacaf_2030_format()
    qualified["CONCACAF"].extend(cacaf_direct)
    qualified["CONCACAF_playoff"] = cacaf_playoff
    
    afc_direct, afc_playoff = simulate_afc_2030_format()
    qualified["AFC"].extend(afc_direct)
    qualified["AFC_playoff"] = afc_playoff
    
    for conf in ["CAF", "OFC"]:
        cfg = CONFEDERATIONS[conf]
        members = [n for n in cfg["member_nations"] if n not in HOST_NATIONS.get(conf, [])]
        if conf == "CAF":
            direc, playoff = simulate_caf_2030_format()
            qualified[conf].extend(direc)
            qualified[f"{conf}_playoff"] = playoff
        else:
            direc, playoff = simulate_round_robin_qualifying(members, conf, cfg["remaining_direct_slots"])
            qualified[conf].extend(direc)
            qualified[f"{conf}_playoff"] = playoff
    
    playoff_teams = [
        qualified["CAF_playoff"][0],
        qualified["CONMEBOL_playoff"][0],
        qualified["AFC_playoff"][0],
        qualified["CONCACAF_playoff"][0],
        qualified["OFC_playoff"][0],
        qualified["UEFA_playoff"][0],
    ]
    inter_qualifiers = simulate_intercontinental_playoff(playoff_teams)
    qualified["Intercontinental"] = inter_qualifiers
    
    return qualified


def run_monte_carlo(num_sims: int) -> Dict[str, float]:
    qualified_count: Dict[str, int] = {name: 0 for name in get_all_teams()}
    
    for i in range(num_sims):
        results = run_qualifying_simulation()
        for conf in ["UEFA", "CAF", "CONMEBOL", "AFC", "CONCACAF", "OFC"]:
            for team in results.get(conf, []):
                qualified_count[team] += 1
        for team in results.get("Intercontinental", []):
            qualified_count[team] += 1
        
        if (i + 1) % 100 == 0 or (i + 1) == num_sims:
            print(f"\rProgress: {i + 1}/{num_sims} ({(i + 1) / num_sims * 100:.1f}%)", end="")
    
    print()
    return {name: (count / num_sims) * 100 for name, count in qualified_count.items()}


def print_probability_table(probs: Dict[str, float]) -> None:
    print("\n" + "=" * 65)
    print(f"{'2030 World Cup Qualification Probabilities':^65}")
    print(f"{f'({NUM_SIMULATIONS:,} simulations)' :^65}")
    print("=" * 65)
    
    sorted_probs = sorted(probs.items(), key=lambda x: x[1], reverse=True)
    for i, (team, prob) in enumerate(sorted_probs):
        if prob > 0:
            print(f"{team:<30} {prob:>5.1f}%")


def print_summary_table() -> None:
    print(f"\n{'CONFEDERATION':<15} {'BASE':>5} {'HOSTS':>6} {'DIRECT':>7} {'PLAYOFF':>8}")
    print("-" * 50)
    for conf, cfg in CONFEDERATIONS.items():
        print(f"{conf:<15} {cfg['base_slots']:>5} {cfg['auto_hosts']:>6} {cfg['remaining_direct_slots']:>7} {cfg['playoff_slots']:>8}")
    print("-" * 50)
    total_base = sum(cfg["base_slots"] for cfg in CONFEDERATIONS.values())
    total_hosts = sum(cfg["auto_hosts"] for cfg in CONFEDERATIONS.values())
    total_direct = sum(cfg["remaining_direct_slots"] for cfg in CONFEDERATIONS.values())
    total_playoff = sum(cfg["playoff_slots"] for cfg in CONFEDERATIONS.values())
    print(f"{'TOTAL':<15} {total_base:>5} {total_hosts:>6} {total_direct:>7} {total_playoff:>8}")


def print_qualified_teams(results: Dict[str, List[str]]) -> None:
    print("\n" + "=" * 65)
    print(f"{'2030 FIFA World Cup - Qualified Teams':^65}")
    print("=" * 65)
    
    for conf in ["UEFA", "CAF", "CONMEBOL", "AFC", "CONCACAF", "OFC"]:
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


if __name__ == "__main__":
    print_summary_table()
    validate_totals()
    
    results = run_qualifying_simulation()
    print_qualified_teams(results)
    
    total_qualified = sum(len(v) for k, v in results.items() if "playoff" not in k)
    print(f"\nTotal tournament slots filled: {total_qualified}/{TOTAL_TEAMS}")
    print(f"Hosts: {TOTAL_HOSTS} | Direct: {TOTAL_DIRECT} | Playoff winners: {PLAYOFF_WINNERS}")
    
    print(f"\nRunning Monte Carlo simulation ({NUM_SIMULATIONS:,} iterations)...")
    probabilities = run_monte_carlo(NUM_SIMULATIONS)
    print_probability_table(probabilities)