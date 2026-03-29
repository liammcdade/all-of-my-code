import random
from collections import defaultdict

########################################
# EXPANDED ELO RATINGS (2027 Projections)
########################################
ELO_RATINGS = {
    # UEFA (Europe)
    'Spain': 2284.01, 'England': 2169.74, 'France': 2171.51, 'Germany': 2155.64, 
    'Sweden': 2131.95, 'Netherlands': 2038.35, 'Norway': 1998.07, 'Denmark': 1975.94,
    'Italy': 1968.79, 'Iceland': 1883.96, 'Belgium': 1833.09, 'Austria': 1806.45,
    'Portugal': 1808.39, 'Scotland': 1785.39, 'Switzerland': 1782.34,
    'Finland': 1779.29, 'Republic of Ireland': 1779.41, 'Poland': 1810.72, 'Serbia': 1717.59, 'Ukraine': 1679.38,
    'Czech Republic': 1684.27, 'Slovenia': 1632.61, 'Wales': 1715.81, 'Romania': 1459.18,
    
    # AFC (Asia)
    'Japan': 2141.13, 'North Korea': 2059.17, 'Australia': 1982.34, 'China': 1888.76,
    'South Korea': 1852.65, 'Vietnam': 1769.19, 'Philippines': 1623.83, 'Thailand': 1658.36,
    'Uzbekistan': 1607.41, 'Myanmar': 1658.15, 'Chinese Taipei': 1692.19, 'India': 1473.37,
    'Iran': 1534.18, 'Jordan': 1488.89, 'Bangladesh': 1400.00,

    # CONCACAF (North/Central America)
    'USA': 2252.84, 'Canada': 2053.77, 'Mexico': 1922.50, 'Haiti': 1717.51,
    'Jamaica': 1624.41, 'Costa Rica': 1611.55, 'Panama': 1636.01, 'Trinidad and Tobago': 1531.64,
    'Guatemala': 1474.47, 'Puerto Rico': 1654.17, 'El Salvador': 1580.76, 'Cuba': 1583.30,

    # CONMEBOL (South America)
    'Brazil': 2138.81, 'Colombia': 1910.77, 'Argentina': 1766.61, 'Chile': 1637.85,
    'Paraguay': 1573.89, 'Venezuela': 1641.50, 'Uruguay': 1563.00, 'Ecuador': 1479.50,
    'Peru': 1265.35, 'Bolivia': 1243.75,

    # CAF (Africa)
    'Nigeria': 1896.33, 'South Africa': 1783.22, 'Zambia': 1745.79, 'Ghana': 1738.57,
    'Morocco': 1686.50, 'Cameroon': 1677.50, 'Senegal': 1658.02, 'Ivory Coast': 1698.65,
    'Algeria': 1663.76, 'Mali': 1597.41, 'Tunisia': 1511.55, 'Equatorial Guinea': 1517.46,
    'Kenya': 1550.00, 'Burkina Faso': 1520.00, 'Tanzania': 1530.00, 'Egypt': 1580.00,
    'Malawi': 1450.00, 'Cape Verde': 1400.00,

    # OFC (Oceania)
    'New Zealand': 1688.34, 'Papua New Guinea': 1667.68, 'Fiji': 1548.73, 'Samoa': 1450.59,
    'Tonga': 1335.45, 'New Caledonia': 1446.13, 'Solomon Islands': 1438.45, 'Vanuatu': 1419.59,
    'American Samoa': 1280.00
}

########################################
# GROUP DEFINITIONS (All Confederations)
########################################
GROUPS = {
    # UEFA Qualifiers (League A)
    "UEFA_A1": ["Denmark", "Sweden", "Italy", "Serbia"],
    "UEFA_A2": ["France", "Netherlands", "Poland", "Republic of Ireland"],
    "UEFA_A3": ["England", "Spain", "Iceland", "Ukraine"],
    "UEFA_A4": ["Germany", "Norway", "Austria", "Slovenia"],

    # UEFA Qualifiers (League B)
    "UEFA_B1": ["Wales", "Czech Republic", "Albania", "Montenegro"],
    "UEFA_B2": ["Switzerland", "Turkey", "Northern Ireland", "Malta"],
    "UEFA_B3": ["Portugal", "Finland", "Slovakia", "Latvia"],
    "UEFA_B4": ["Scotland", "Belgium", "Israel", "Luxembourg"],

    # UEFA Qualifiers (League C)
    "UEFA_C1": ["Bosnia and Herzegovina", "Lithuania", "Estonia", "Liechtenstein"],
    "UEFA_C2": ["Kosovo", "Croatia", "Bulgaria", "Gibraltar"],
    "UEFA_C3": ["Hungary", "Azerbaijan", "North Macedonia", "Andorra"],
    "UEFA_C4": ["Greece", "Faroe Islands", "Georgia"],
    "UEFA_C5": ["Romania", "Moldova", "Cyprus"],
    "UEFA_C6": ["Belarus", "Kazakhstan", "Armenia"],

    # AFC Asian Cup (Group Stage)
    "AFC_A": ["South Korea", "Australia", "Philippines", "Iran"],
    "AFC_B": ["China", "North Korea", "Uzbekistan", "Bangladesh"],
    "AFC_C": ["Japan", "Chinese Taipei", "Vietnam", "India"],

    # CONMEBOL Nations League (Brazil excluded as host)
    "CONMEBOL": ["Colombia", "Argentina", "Chile", "Venezuela", "Ecuador", "Paraguay", "Uruguay", "Peru", "Bolivia"],

    # CONCACAF W Gold Cup Qualifiers
    "CONCACAF_A": ["USA", "Mexico", "Puerto Rico", "El Salvador"],
    "CONCACAF_B": ["Canada", "Costa Rica", "Haiti", "Guatemala"],
    "CONCACAF_C": ["Jamaica", "Panama", "Trinidad and Tobago", "Cuba"],

    # CAF Women's AFCON (16-team draw)
    "CAF_A": ["Morocco", "Algeria", "Senegal", "Kenya"],
    "CAF_B": ["South Africa", "Ivory Coast", "Burkina Faso", "Tanzania"],
    "CAF_C": ["Nigeria", "Zambia", "Egypt", "Malawi"],
    "CAF_D": ["Ghana", "Cameroon", "Mali", "Cape Verde"],

    # OFC Qualifiers (Phase 2 Groups)
    "OFC_A": ["New Zealand", "American Samoa", "Samoa", "Solomon Islands"],
    "OFC_B": ["Papua New Guinea", "Fiji", "New Caledonia", "Vanuatu"]
}

# Initial Standings (Partial Progress as per user prompt)
ALL_STANDINGS = {
    # AFC Asian Cup 2026 - COMPLETED (all teams P=3)
    "AFC_A": {
        "South Korea": {"P": 3, "W": 2, "D": 1, "L": 0, "GF": 9, "GA": 3, "GD": 6, "PTS": 7},
        "Australia": {"P": 3, "W": 2, "D": 1, "L": 0, "GF": 8, "GA": 3, "GD": 5, "PTS": 7},
        "Philippines": {"P": 3, "W": 1, "D": 0, "L": 2, "GF": 2, "GA": 4, "GD": -2, "PTS": 3},
        "Iran": {"P": 3, "W": 0, "D": 0, "L": 3, "GF": 0, "GA": 9, "GD": -9, "PTS": 0}
    },
    "AFC_B": {
        "China": {"P": 3, "W": 3, "D": 0, "L": 0, "GF": 7, "GA": 1, "GD": 6, "PTS": 9},
        "North Korea": {"P": 3, "W": 2, "D": 0, "L": 1, "GF": 9, "GA": 2, "GD": 7, "PTS": 6},
        "Uzbekistan": {"P": 3, "W": 1, "D": 0, "L": 2, "GF": 4, "GA": 6, "GD": -2, "PTS": 3},
        "Bangladesh": {"P": 3, "W": 0, "D": 0, "L": 3, "GF": 0, "GA": 11, "GD": -11, "PTS": 0}
    },
    "AFC_C": {
        "Japan": {"P": 3, "W": 3, "D": 0, "L": 0, "GF": 17, "GA": 0, "GD": 17, "PTS": 9},
        "Chinese Taipei": {"P": 3, "W": 2, "D": 0, "L": 1, "GF": 4, "GA": 3, "GD": 1, "PTS": 6},
        "Vietnam": {"P": 3, "W": 1, "D": 0, "L": 2, "GF": 2, "GA": 6, "GD": -4, "PTS": 3},
        "India": {"P": 3, "W": 0, "D": 0, "L": 3, "GF": 2, "GA": 16, "GD": -14, "PTS": 0}
    },
    # OFC Phase 2 - COMPLETED (all teams P=3)
    "OFC_A": {
        "New Zealand": {"P": 3, "W": 3, "D": 0, "L": 0, "GF": 19, "GA": 0, "GD": 19, "PTS": 9},
        "American Samoa": {"P": 3, "W": 2, "D": 0, "L": 1, "GF": 2, "GA": 3, "GD": -1, "PTS": 6},
        "Samoa": {"P": 3, "W": 1, "D": 0, "L": 2, "GF": 2, "GA": 10, "GD": -8, "PTS": 3},
        "Solomon Islands": {"P": 3, "W": 0, "D": 0, "L": 3, "GF": 1, "GA": 11, "GD": -10, "PTS": 0}
    },
    "OFC_B": {
        "Papua New Guinea": {"P": 3, "W": 3, "D": 0, "L": 0, "GF": 10, "GA": 0, "GD": 10, "PTS": 9},
        "Fiji": {"P": 3, "W": 2, "D": 0, "L": 1, "GF": 6, "GA": 1, "GD": 5, "PTS": 6},
        "New Caledonia": {"P": 3, "W": 1, "D": 0, "L": 2, "GF": 2, "GA": 10, "GD": -8, "PTS": 3},
        "Vanuatu": {"P": 3, "W": 0, "D": 0, "L": 3, "GF": 1, "GA": 8, "GD": -7, "PTS": 0}
    },
    "UEFA_A1": {
        "Denmark": {"P": 2, "W": 1, "D": 1, "L": 0, "GF": 4, "GA": 2, "GD": 2, "PTS": 4},
        "Sweden": {"P": 2, "W": 1, "D": 1, "L": 0, "GF": 1, "GA": 0, "GD": 1, "PTS": 4},
        "Italy": {"P": 2, "W": 0, "D": 1, "L": 1, "GF": 1, "GA": 2, "GD": -1, "PTS": 1},
        "Serbia": {"P": 2, "W": 0, "D": 1, "L": 1, "GF": 1, "GA": 3, "GD": -2, "PTS": 1}
    },

    "UEFA_A2": {
        "France": {"P": 2, "W": 2, "D": 0, "L": 0, "GF": 6, "GA": 2, "GD": 4, "PTS": 6},
        "Netherlands": {"P": 2, "W": 1, "D": 1, "L": 0, "GF": 4, "GA": 3, "GD": 1, "PTS": 4},
        "Poland": {"P": 2, "W": 0, "D": 1, "L": 1, "GF": 3, "GA": 6, "GD": -3, "PTS": 1},
        "Republic of Ireland": {"P": 2, "W": 0, "D": 0, "L": 2, "GF": 2, "GA": 4, "GD": -2, "PTS": 0}
    },

    "UEFA_A3": {
        "England": {"P": 2, "W": 2, "D": 0, "L": 0, "GF": 8, "GA": 1, "GD": 7, "PTS": 6},
        "Spain": {"P": 2, "W": 2, "D": 0, "L": 0, "GF": 6, "GA": 1, "GD": 5, "PTS": 6},
        "Iceland": {"P": 2, "W": 0, "D": 0, "L": 2, "GF": 0, "GA": 5, "GD": -5, "PTS": 0},
        "Ukraine": {"P": 2, "W": 0, "D": 0, "L": 2, "GF": 2, "GA": 9, "GD": -7, "PTS": 0}
    },

    "UEFA_A4": {
        "Germany": {"P": 2, "W": 2, "D": 0, "L": 0, "GF": 9, "GA": 0, "GD": 9, "PTS": 6},
        "Norway": {"P": 2, "W": 1, "D": 0, "L": 1, "GF": 1, "GA": 4, "GD": -3, "PTS": 3},
        "Slovenia": {"P": 2, "W": 1, "D": 0, "L": 1, "GF": 1, "GA": 5, "GD": -4, "PTS": 3},
        "Austria": {"P": 2, "W": 0, "D": 0, "L": 2, "GF": 0, "GA": 2, "GD": -2, "PTS": 0}
    },

    "UEFA_B1": {
        "Wales": {"P": 2, "W": 1, "D": 1, "L": 0, "GF": 8, "GA": 3, "GD": 5, "PTS": 4},
        "Czech Republic": {"P": 2, "W": 1, "D": 1, "L": 0, "GF": 7, "GA": 3, "GD": 4, "PTS": 4},
        "Albania": {"P": 2, "W": 1, "D": 0, "L": 1, "GF": 3, "GA": 6, "GD": -3, "PTS": 3},
        "Montenegro": {"P": 2, "W": 0, "D": 0, "L": 2, "GF": 2, "GA": 8, "GD": -6, "PTS": 0}
    },

    "UEFA_B2": {
        "Switzerland": {"P": 2, "W": 2, "D": 0, "L": 0, "GF": 6, "GA": 1, "GD": 5, "PTS": 6},
        "Turkey": {"P": 2, "W": 2, "D": 0, "L": 0, "GF": 4, "GA": 0, "GD": 4, "PTS": 6},
        "Northern Ireland": {"P": 2, "W": 0, "D": 0, "L": 2, "GF": 0, "GA": 3, "GD": -3, "PTS": 0},
        "Malta": {"P": 2, "W": 0, "D": 0, "L": 2, "GF": 1, "GA": 7, "GD": -6, "PTS": 0}
    },

    "UEFA_B3": {
        "Portugal": {"P": 2, "W": 2, "D": 0, "L": 0, "GF": 6, "GA": 0, "GD": 6, "PTS": 6},
        "Finland": {"P": 2, "W": 1, "D": 0, "L": 1, "GF": 3, "GA": 3, "GD": 0, "PTS": 3},
        "Slovakia": {"P": 2, "W": 1, "D": 0, "L": 1, "GF": 3, "GA": 6, "GD": -3, "PTS": 3},
        "Latvia": {"P": 2, "W": 0, "D": 0, "L": 2, "GF": 3, "GA": 6, "GD": -3, "PTS": 0}
    },

    "UEFA_B4": {
        "Scotland": {"P": 2, "W": 2, "D": 0, "L": 0, "GF": 12, "GA": 0, "GD": 12, "PTS": 6},
        "Belgium": {"P": 2, "W": 2, "D": 0, "L": 0, "GF": 8, "GA": 0, "GD": 8, "PTS": 6},
        "Israel": {"P": 2, "W": 0, "D": 0, "L": 2, "GF": 0, "GA": 8, "GD": -8, "PTS": 0},
        "Luxembourg": {"P": 2, "W": 0, "D": 0, "L": 2, "GF": 0, "GA": 12, "GD": -12, "PTS": 0}
    },

    "UEFA_C1": {
        "Bosnia and Herzegovina": {"P": 2, "W": 2, "D": 0, "L": 0, "GF": 16, "GA": 2, "GD": 14, "PTS": 6},
        "Lithuania": {"P": 2, "W": 1, "D": 1, "L": 0, "GF": 6, "GA": 1, "GD": 5, "PTS": 4},
        "Estonia": {"P": 2, "W": 0, "D": 1, "L": 1, "GF": 1, "GA": 3, "GD": -2, "PTS": 1},
        "Liechtenstein": {"P": 2, "W": 0, "D": 0, "L": 2, "GF": 2, "GA": 19, "GD": -17, "PTS": 0}
    },

    "UEFA_C2": {
        "Kosovo": {"P": 2, "W": 2, "D": 0, "L": 0, "GF": 7, "GA": 0, "GD": 7, "PTS": 6},
        "Croatia": {"P": 2, "W": 1, "D": 0, "L": 1, "GF": 1, "GA": 1, "GD": 0, "PTS": 3},
        "Bulgaria": {"P": 2, "W": 1, "D": 0, "L": 1, "GF": 5, "GA": 1, "GD": 4, "PTS": 3},
        "Gibraltar": {"P": 2, "W": 0, "D": 0, "L": 2, "GF": 0, "GA": 11, "GD": -11, "PTS": 0}
    },

    "UEFA_C3": {
        "Hungary": {"P": 2, "W": 1, "D": 1, "L": 0, "GF": 1, "GA": 0, "GD": 1, "PTS": 4},
        "Azerbaijan": {"P": 2, "W": 1, "D": 0, "L": 1, "GF": 2, "GA": 1, "GD": 1, "PTS": 3},
        "North Macedonia": {"P": 2, "W": 1, "D": 0, "L": 1, "GF": 3, "GA": 2, "GD": 1, "PTS": 3},
        "Andorra": {"P": 2, "W": 0, "D": 1, "L": 1, "GF": 0, "GA": 3, "GD": -3, "PTS": 1}
    },

    "UEFA_C4": {
        "Greece": {"P": 2, "W": 2, "D": 0, "L": 0, "GF": 5, "GA": 0, "GD": 5, "PTS": 6},
        "Faroe Islands": {"P": 1, "W": 0, "D": 0, "L": 1, "GF": 0, "GA": 2, "GD": -2, "PTS": 0},
        "Georgia": {"P": 1, "W": 0, "D": 0, "L": 1, "GF": 0, "GA": 3, "GD": -3, "PTS": 0}
    },

    "UEFA_C5": {
        "Romania": {"P": 2, "W": 2, "D": 0, "L": 0, "GF": 5, "GA": 0, "GD": 5, "PTS": 6},
        "Moldova": {"P": 1, "W": 0, "D": 0, "L": 1, "GF": 0, "GA": 1, "GD": -1, "PTS": 0},
        "Cyprus": {"P": 1, "W": 0, "D": 0, "L": 1, "GF": 0, "GA": 4, "GD": -4, "PTS": 0}
    },

    "UEFA_C6": {
        "Belarus": {"P": 1, "W": 1, "D": 0, "L": 0, "GF": 1, "GA": 0, "GD": 1, "PTS": 3},
        "Kazakhstan": {"P": 2, "W": 1, "D": 0, "L": 1, "GF": 3, "GA": 1, "GD": 2, "PTS": 3},
        "Armenia": {"P": 1, "W": 0, "D": 0, "L": 1, "GF": 0, "GA": 3, "GD": -3, "PTS": 0}
    }
}

OFC_BRACKET = {
    "SemiFinal1": {
        "home": "New Zealand",
        "away": "Fiji",
        "date": "2026-04-12"
    },

    "SemiFinal2": {
        "home": "Papua New Guinea",
        "away": "American Samoa",
        "date": "2026-04-12"
    },

    "Final": {
        "home": "Winner SemiFinal1",
        "away": "Winner SemiFinal2",
        "date": "2026-04-15"
    }
}

UEFA_SCHEDULE = {
    "Matchday3": {
        "date": "2026-04-14",
        "matches": [
            ("Armenia", "Belarus"),
            ("Bulgaria", "Kosovo"),
            ("Moldova", "Cyprus"),
            ("North Macedonia", "Hungary"),
            ("Estonia", "Liechtenstein"),
            ("Lithuania", "Bosnia and Herzegovina"),
            ("Czech Republic", "Montenegro"),
            ("Finland", "Slovakia"),
            ("Faroe Islands", "Greece"),
            ("Norway", "Slovenia"),
            ("Poland", "Republic of Ireland"),
            ("Germany", "Austria"),
            ("Serbia", "Italy"),
            ("Andorra", "Azerbaijan"),
            ("Gibraltar", "Croatia"),
            ("Latvia", "Portugal"),
            ("Sweden", "Denmark"),
            ("Switzerland", "Turkey"),
            ("Israel", "Luxembourg"),
            ("England", "Spain"),
            ("Northern Ireland", "Malta"),
            ("Wales", "Albania"),
            ("Iceland", "Ukraine"),
            ("Scotland", "Belgium"),
            ("Netherlands", "France"),
        ]
    },
    "Matchday4": {
        "date": "2026-04-18",
        "matches": [
            ("Azerbaijan", "Andorra"),
            ("Belarus", "Kazakhstan"),
            ("Denmark", "Italy"),
            ("Hungary", "North Macedonia"),
            ("Romania", "Cyprus"),
            ("Estonia", "Lithuania"),
            ("Liechtenstein", "Bosnia and Herzegovina"),
            ("Republic of Ireland", "Poland"),
            ("Slovakia", "Portugal"),
            ("Spain", "Ukraine"),
            ("Sweden", "Serbia"),
            ("Croatia", "Gibraltar"),
            ("Slovenia", "Norway"),
            ("Albania", "Wales"),
            ("Austria", "Germany"),
            ("Faroe Islands", "Georgia"),
            ("Kosovo", "Bulgaria"),
            ("Luxembourg", "Israel"),
            ("Montenegro", "Czech Republic"),
            ("Turkey", "Switzerland"),
            ("Iceland", "England"),
            ("Latvia", "Finland"),
            ("Malta", "Northern Ireland"),
            ("Belgium", "Scotland"),
            ("France", "Netherlands"),
        ]
    }
}


########################################
# SIMULATION ENGINE
########################################

def win_prob(elo_a, elo_b):
    return 1 / (1 + 10 ** ((elo_b - elo_a) / 400))

def simulate_match(team1, team2):
    elo1 = ELO_RATINGS.get(team1, 1500)
    elo2 = ELO_RATINGS.get(team2, 1500)
    p = win_prob(elo1, elo2)
    r = random.random()

    # Weight goals based on Elo probability
    if r < p * 0.75: # Team 1 Strong Favorite/Wins
        g1 = random.randint(1, 4)
        g2 = random.randint(0, 2)
    elif r < p * 0.75 + (1 - p) * 0.75: # Team 2 Upsets/Wins
        g1 = random.randint(0, 2)
        g2 = random.randint(1, 4)
    else: # Draw
        g1 = g2 = random.randint(0, 2)
    return g1, g2

def update_table(table, t1, t2, g1, g2):
    for t in (t1, t2):
        if t not in table:
            table[t] = {"P":0,"W":0,"D":0,"L":0,"GF":0,"GA":0,"GD":0,"PTS":0}

    table[t1]["P"] += 1
    table[t2]["P"] += 1
    table[t1]["GF"] += g1
    table[t1]["GA"] += g2
    table[t2]["GF"] += g2
    table[t2]["GA"] += g1

    if g1 > g2:
        table[t1]["W"] += 1; table[t2]["L"] += 1; table[t1]["PTS"] += 3
    elif g2 > g1:
        table[t2]["W"] += 1; table[t1]["L"] += 1; table[t2]["PTS"] += 3
    else:
        table[t1]["D"] += 1; table[t2]["D"] += 1; table[t1]["PTS"] += 1; table[t2]["PTS"] += 1

    table[t1]["GD"] = table[t1]["GF"] - table[t1]["GA"]
    table[t2]["GD"] = table[t2]["GF"] - table[t2]["GA"]

def simulate_group(group_name, teams, current_standings):
    # Start with existing data or fresh dict
    table = {team: {"P":0,"W":0,"D":0,"L":0,"GF":0,"GA":0,"GD":0,"PTS":0} for team in teams}
    
    # Merge existing results if they exist
    if group_name in current_standings:
        for team, stats in current_standings[group_name].items():
            if team in table: table[team].update(stats)

    # Check if group is already complete (all teams played num_teams-1 matches)
    complete = group_name in current_standings and all(
        table[t]["P"] >= len(teams) - 1 for t in teams if t in table
    )
    if complete:
        ranking = sorted(table.items(), key=lambda x: (x[1]["PTS"], x[1]["GD"], x[1]["GF"]), reverse=True)
        return ranking

    # Simulate remaining matches of single round robin
    for i in range(len(teams)):
        for j in range(i + 1, len(teams)):
            t1, t2 = teams[i], teams[j]
            g1, g2 = simulate_match(t1, t2)
            update_table(table, t1, t2, g1, g2)

    ranking = sorted(table.items(), key=lambda x: (x[1]["PTS"], x[1]["GD"], x[1]["GF"]), reverse=True)
    return ranking

def run_all_confederations():
    all_results = {}
    for g_name, teams in GROUPS.items():
        all_results[g_name] = simulate_group(g_name, teams, ALL_STANDINGS)
    return all_results

if __name__ == "__main__":
    print("--- 2027 WOMEN'S WORLD CUP QUALIFICATION SIMULATOR ---")
    
    # Confirmed qualifiers as of March 2026
    QUALIFIED = [
        "Brazil",  # Host
        "Australia", "China", "South Korea", "Japan", "Philippines", "North Korea"  # AFC
    ]
    
    print("\n=== CONFIRMED QUALIFIERS (as of March 2026) ===")
    for team in QUALIFIED:
        print(f"  - {team}")
    print(f"  Total: {len(QUALIFIED)}/32 slots filled\n")
    
    print("=== GROUP STANDINGS ===")
    results = run_all_confederations()
    
    for g, r in results.items():
        print(f"\nGroup: {g}")
        print(f"{'Pos':<4} {'Team':<20} {'P':<3} {'W':<3} {'D':<3} {'L':<3} {'GD':<4} {'PTS':<4}")
        for i, (team, s) in enumerate(r, 1):
            print(f"{i:<4} {team:<20} {s['P']:<3} {s['W']:<3} {s['D']:<3} {s['L']:<3} {s['GD']:<4} {s['PTS']:<4}")