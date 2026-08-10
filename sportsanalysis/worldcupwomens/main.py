import itertools
import random
import sys
from collections import defaultdict

ALREADY_QUALIFIED = {
    "Australia", "China", "Japan", "North Korea", "Philippines", "South Korea",
    "Argentina", "Brazil","Colombia",
    "New Zealand",
    "Denmark", "France", "Germany", "Spain",
}

SLOT_ALLOCATION = {
    "AFC": {"slots": 6, "inter_conf_slots": 2, "teams": ["Australia", "China", "Japan", "North Korea", "Philippines", "South Korea"], "inter_conf_teams": ["Uzbekistan", "Chinese Taipei"], "inter_conf_mode": "preliminary_phase"},
    "CAF": {"slots": 4, "inter_conf_slots": 2, "teams": [], "inter_conf_mode": "preliminary_phase"},
    "CONCACAF": {"slots": 4, "inter_conf_slots": 2, "teams": [], "inter_conf_mode": "final_phase_bye"},
    "CONMEBOL": {"slots": 3, "inter_conf_slots": 2, "teams": ["Argentina", "Colombia", "Brazil"], "inter_conf_teams": ["Venezuela"], "inter_conf_mode": "final_phase_bye", "preliminary_team": "Ecuador"},
    "OFC": {"slots": 1, "inter_conf_slots": 1, "teams": ["New Zealand"], "inter_conf_team": "Papua New Guinea", "inter_conf_mode": "preliminary_phase"},
    "UEFA": {"slots": 11, "inter_conf_slots": 1, "teams": ["Denmark", "France", "Germany", "Spain"], "inter_conf_mode": "final_phase_seeded"},
}

N_SIMS = 10000
RANDOM_SEED = None

for arg in sys.argv[1:]:
    if arg.startswith("--seed="):
        RANDOM_SEED = int(arg.split("=")[1])

if RANDOM_SEED is not None:
    random.seed(RANDOM_SEED)

TEAM_CONF = {
    "Australia": "AFC", "China": "AFC", "Japan": "AFC", "North Korea": "AFC", "Philippines": "AFC", "South Korea": "AFC",
    "Uzbekistan": "AFC", "Chinese Taipei": "AFC",
    "Morocco": "CAF", "Algeria": "CAF", "Senegal": "CAF", "Kenya": "CAF",
    "Ivory Coast": "CAF", "Tanzania": "CAF", "South Africa": "CAF", "Burkina Faso": "CAF",
    "Zambia": "CAF", "Malawi": "CAF", "Nigeria": "CAF", "Egypt": "CAF",
    "Ghana": "CAF", "Cameroon": "CAF", "Mali": "CAF", "Cape Verde": "CAF",
    "Djibouti": "CAF", "Mauritius": "CAF",
    "USA": "CONCACAF", "Canada": "CONCACAF", "Mexico": "CONCACAF", "Costa Rica": "CONCACAF",
    "Jamaica": "CONCACAF", "Panama": "CONCACAF", "Haiti": "CONCACAF", "El Salvador": "CONCACAF",
    "Argentina": "CONMEBOL", "Brazil": "CONMEBOL", "Colombia": "CONMEBOL", "Venezuela": "CONMEBOL", "Ecuador": "CONMEBOL",
    "New Zealand": "OFC", "Papua New Guinea": "OFC",
    "Spain": "UEFA", "Germany": "UEFA", "England": "UEFA", "France": "UEFA", "Netherlands": "UEFA",
    "Sweden": "UEFA", "Denmark": "UEFA", "Norway": "UEFA", "Italy": "UEFA", "Iceland": "UEFA",
    "Republic of Ireland": "UEFA", "Austria": "UEFA", "Poland": "UEFA", "Serbia": "UEFA", "Ukraine": "UEFA",
    "Portugal": "UEFA", "Switzerland": "UEFA", "Scotland": "UEFA", "Belgium": "UEFA", "Finland": "UEFA",
    "Wales": "UEFA", "Czech Republic": "UEFA", "Turkey": "UEFA", "Northern Ireland": "UEFA", "Israel": "UEFA",
    "Slovakia": "UEFA", "Slovenia": "UEFA", "Albania": "UEFA",
    "Lithuania": "UEFA", "Kosovo": "UEFA", "Belarus": "UEFA", "Kazakhstan": "UEFA",
    "Hungary": "UEFA", "Greece": "UEFA", "Romania": "UEFA", "Croatia": "UEFA",
}

NATIONALS_LEAGUE_RANK = {
    "Germany": 1, "Spain": 2, "Denmark": 3, "France": 4, "England": 5,
    "Norway": 6, "Netherlands": 7, "Italy": 8, "Republic of Ireland": 9,
    "Sweden": 10, "Iceland": 11, "Austria": 12, "Slovenia": 13, "Poland": 14,
    "Serbia": 15, "Ukraine": 16, "Switzerland": 17, "Portugal": 18,
    "Scotland": 19, "Wales": 20, "Finland": 21, "Belgium": 22, "Turkey": 23,
    "Czech Republic": 24, "Albania": 25, "Northern Ireland": 26, "Slovakia": 27,
    "Israel": 28, "Montenegro": 29, "Latvia": 30, "Malta": 31, "Luxembourg": 32,
    "Hungary": 33, "Greece": 34, "Romania": 35, "Belarus": 36, "Kosovo": 37,
    "Lithuania": 38, "Croatia": 39, "Kazakhstan": 40, "Azerbaijan": 41,
    "Faroe Islands": 42, "Moldova": 43, "Bosnia and Herzegovina": 44,
    "Estonia": 45, "Cyprus": 46, "Armenia": 47, "Georgia": 48,
    "Bulgaria": 49, "North Macedonia": 50, "Andorra": 51, "Liechtenstein": 52,
    "Gibraltar": 53,
}

CONF_NAMES = ["AFC", "CAF", "CONCACAF", "CONMEBOL", "OFC", "UEFA"]

print("ALREADY QUALIFIED TEAMS")
print("=" * 35)
for conf, data in SLOT_ALLOCATION.items():
    if data["teams"]:
        print(f"\n{conf} ({len(data['teams'])}/{data['slots']} slots):")
        for team in sorted(data["teams"]):
            print(f"  {team}")
print(f"\nTotal: {len(ALREADY_QUALIFIED)} teams")

print(f"\nREMAINING SLOTS")
print("=" * 35)
total_remaining = 32 - len(ALREADY_QUALIFIED)
print(f"Total remaining: {total_remaining} slots to fill\n")
for conf, data in SLOT_ALLOCATION.items():
    remaining = data["slots"] - len(data["teams"])
    if remaining > 0:
        print(f"  {conf}: {remaining} slot(s) remaining")
    else:
        print(f"  {conf}: Full ({data['slots']} slots)")

print(f"\nINTER-CONFEDERATION PLAY-OFF ALLOCATION")
print("=" * 45)
for conf, data in SLOT_ALLOCATION.items():
    slots = data["inter_conf_slots"]
    mode = data.get("inter_conf_mode", "")
    if "inter_conf_team" in data:
        print(f"  {conf}: {slots} slot(s) — {data['inter_conf_team']} (direct qualifier from qualifiers)")
    elif "inter_conf_teams" in data:
        teams_str = ", ".join(data["inter_conf_teams"])
        print(f"  {conf}: {slots} slot(s) — {teams_str}" + (f" [{mode}]" if mode else ""))
    else:
        print(f"  {conf}: {slots} slot(s)")

ELO = {
    "Spain": 2105, "USA": 2058, "Germany": 2029, "England": 2027, "Japan": 1999,
    "France": 1984, "Brazil": 1977, "Sweden": 1938, "Canada": 1937, "Netherlands": 1912,
    "Korea DPR": 1911, "Denmark": 1910, "Italy": 1892, "Norway": 1879, "Australia": 1831,
    "China PR": 1799, "Iceland": 1792, "Belgium": 1786, "Korea Republic": 1781, "Colombia": 1772,
    "Republic of Ireland": 1770, "Portugal": 1751, "Austria": 1750, "Finland": 1745, "Scotland": 1743,
    "Switzerland": 1734, "Russia": 1718, "Mexico": 1717, "Poland": 1694, "Argentina": 1683,
    "Wales": 1669, "New Zealand": 1645, "Czech Republic": 1641, "Ukraine": 1634, "Serbia": 1634,
    "Vietnam": 1594, "Slovenia": 1579, "Philippines": 1566, "Chinese Taipei": 1566, "Nigeria": 1564,
    "Jamaica": 1537, "Venezuela": 1537, "Costa Rica": 1516, "Paraguay": 1511, "Hungary": 1507,
    "Turkey": 1497, "Haiti": 1491, "Chile": 1487, "Thailand": 1485, "Northern Ireland": 1482,
    "Uzbekistan": 1474, "Belarus": 1473, "Romania": 1472, "Slovakia": 1467, "Myanmar": 1461,
    "Panama": 1457, "Papua New Guinea": 1450, "Ghana": 1430, "Greece": 1430, "Ecuador": 1419,
    "Uruguay": 1419, "Morocco": 1410, "South Africa": 1407, "Croatia": 1406, "Zambia": 1392,
    "Israel": 1383, "Albania": 1376, "IR Iran": 1370, "India": 1369, "Cameroon": 1362,
    "Bosnia and Herzegovina": 1361, "Ivory Coast": 1355, "Peru": 1331, "Algeria": 1328, "Azerbaijan": 1318,
    "Puerto Rico": 1309, "Jordan": 1299, "El Salvador": 1295, "Fiji": 1282, "Hong Kong, China": 1281,
    "Senegal": 1277, "Trinidad and Tobago": 1269, "Guatemala": 1267, "Kosovo": 1263, "Mali": 1254,
    "Montenegro": 1250, "Samoa": 1247, "Nepal": 1239, "Solomon Islands": 1234, "Equatorial Guinea": 1230,
    "Guyana": 1217, "Malta": 1216, "Lithuania": 1208, "Dominican Republic": 1208, "Nicaragua": 1205,
    "Cuba": 1204, "Guam": 1202, "Kazakhstan": 1199, "Estonia": 1199, "Malaysia": 1198,
    "Tunisia": 1198, "Faroe Islands": 1187, "New Caledonia": 1184, "Latvia": 1180, "Congo DR": 1180,
    "Indonesia": 1179, "Bangladesh": 1171, "Vanuatu": 1168, "Bulgaria": 1166, "Congo": 1161,
    "Egypt": 1160, "Tanzania": 1160, "Bolivia": 1154, "Luxembourg": 1153, "Tonga": 1153,
    "Burkina Faso": 1147, "Bahrain": 1147, "Laos": 1141, "Cambodia": 1140, "Moldova": 1138,
    "American Samoa": 1130, "Cape Verde": 1130, "Tahiti": 1128, "United Arab Emirates": 1127, "Namibia": 1124,
    "Honduras": 1115, "Zimbabwe": 1115, "Palestine": 1111, "Kenya": 1108, "Lebanon": 1101,
    "Cook Islands": 1100, "Georgia": 1099, "Togo": 1093, "Malawi": 1087, "The Gambia": 1082,
    "Cyprus": 1076, "North Macedonia": 1075, "Kyrgyz Republic": 1071, "Ethiopia": 1068, "Benin": 1066,
    "Suriname": 1066, "Turkmenistan": 1064, "Eritrea": 1059, "Bermuda": 1053, "Guinea": 1049,
    "Central African Republic": 1046, "Singapore": 1041, "Uganda": 1036, "Mongolia": 1036, "Armenia": 1030,
    "Botswana": 1029, "Gabon": 1029, "St Kitts and Nevis": 1027, "Sierra Leone": 1021, "Pakistan": 1009,
    "Angola": 990, "Chad": 986, "Saudi Arabia": 971, "Timor-Leste": 960, "Tajikistan": 955,
    "Mauritania": 953, "St Vincent and the Grenadines": 947, "Bhutan": 933, "Syria": 931, "Barbados": 925,
    "St Lucia": 923, "Sri Lanka": 916, "Iraq": 910, "Maldives": 907, "Belize": 903,
    "Rwanda": 892, "Dominica": 885, "Afghanistan": 884, "Liberia": 882, "Grenada": 878,
    "Mozambique": 875, "Kuwait": 870, "Qatar": 864, "Niger": 864, "Seychelles": 850,
    "Macau": 847, "Guinea-Bissau": 839, "Lesotho": 836, "Burundi": 822, "Curaçao": 822,
    "Andorra": 817, "Antigua and Barbuda": 807, "Aruba": 801, "Eswatini": 797, "US Virgin Islands": 790,
    "Cayman Islands": 777, "Comoros": 745, "Libya": 740, "British Virgin Islands": 736, "Gibraltar": 734,
    "Liechtenstein": 725, "Madagascar": 724, "Anguilla": 682, "Bahamas": 666, "Sudan": 629,
    "South Sudan": 629, "Turks and Caicos Islands": 627,     "Djibouti": 557, "Mauritius": 434,
}

NAME_MAP = {
    "North Korea": "Korea DPR",
    "South Korea": "Korea Republic",
    "China": "China PR",
}


def get_elo_key(team: str) -> str:
    return NAME_MAP.get(team, team)


def get_elo(team: str) -> int:
    return ELO[get_elo_key(team)]


def simulate_tie(team1, team2):
    """Two-legged tie. team1 hosts 1st leg, team2 hosts 2nd leg."""
    elo_diff_1 = get_elo(team1) + 60 - get_elo(team2)
    p_home = 1 / (1 + 10 ** (-elo_diff_1 / 400))
    draw_prob = 0.24

    r = random.random()
    if r < p_home * (1 - draw_prob):
        goals1_1, goals2_1 = 2, 0
    elif r < p_home * (1 - draw_prob) + draw_prob:
        goals1_1, goals2_1 = 1, 1
    else:
        goals1_1, goals2_1 = 0, 2

    elo_diff_2 = get_elo(team2) + 60 - get_elo(team1)
    p_home2 = 1 / (1 + 10 ** (-elo_diff_2 / 400))
    r = random.random()
    if r < p_home2 * (1 - draw_prob):
        goals2_2, goals1_2 = 2, 0
    elif r < p_home2 * (1 - draw_prob) + draw_prob:
        goals2_2, goals1_2 = 1, 1
    else:
        goals2_2, goals1_2 = 0, 2

    agg1 = goals1_1 + goals1_2
    agg2 = goals2_1 + goals2_2

    if agg1 > agg2:
        return team1
    elif agg2 > agg1:
        return team2
    else:
        elo_pen = get_elo(team2) + 30 - get_elo(team1)
        p = 1 / (1 + 10 ** (-elo_pen / 400))
        return team2 if random.random() < p else team1

def simulate_match(team1, team2, draw_factor: float = 0.25):
    """Single match at neutral venue. Returns winner."""
    elo_diff = get_elo(team1) - get_elo(team2)
    p_team1 = 1 / (1 + 10 ** (-elo_diff / 400))
    r = random.random()
    if r < p_team1 * (1 - draw_factor):
        return team1
    elif r < p_team1 * (1 - draw_factor) + draw_factor:
        return None
    else:
        return team2

def simulate_win(team1, team2, draw_factor: float = 0.25) -> str:
    result = simulate_match(team1, team2, draw_factor)
    if result is None:
        p_team1 = 1 / (1 + 10 ** (-(get_elo(team1) - get_elo(team2)) / 400))
        return team1 if random.random() < p_team1 else team2
    return result

def simulate_match_with_scores(team1, team2, draw_factor: float = 0.25):
    """Simulate a single match and return (goals1, goals2)."""
    elo_diff = get_elo(team1) - get_elo(team2)
    p_team1 = 1 / (1 + 10 ** (-elo_diff / 400))
    r = random.random()

    team1_win_prob = p_team1 * (1 - draw_factor)
    draw_prob = draw_factor
    team2_win_prob = (1 - p_team1) * (1 - draw_factor)

    if r < team1_win_prob:
        return (2, 0) if random.random() < 0.6 else (1, 0)
    elif r < team1_win_prob + draw_prob:
        return (1, 1) if random.random() < 0.5 else (0, 0)
    else:
        return (0, 2) if random.random() < 0.6 else (0, 1)


def simulate_preliminary_phase(teams):
    """Simulate preliminary phase round-robin. Returns (top_2, stats_dict)."""
    stats = {t: {'pts': 0, 'gf': 0, 'ga': 0, 'gd': 0, 'wins': 0, 'draws': 0, 'losses': 0} for t in teams}
    for i in range(len(teams)):
        for j in range(i + 1, len(teams)):
            g1, g2 = simulate_match_with_scores(teams[i], teams[j])
            stats[teams[i]]['gf'] += g1
            stats[teams[i]]['ga'] += g2
            stats[teams[i]]['gd'] += g1 - g2
            stats[teams[j]]['gf'] += g2
            stats[teams[j]]['ga'] += g1
            stats[teams[j]]['gd'] += g2 - g1
            if g1 > g2:
                stats[teams[i]]['pts'] += 3
                stats[teams[i]]['wins'] += 1
                stats[teams[j]]['losses'] += 1
            elif g2 > g1:
                stats[teams[j]]['pts'] += 3
                stats[teams[j]]['wins'] += 1
                stats[teams[i]]['losses'] += 1
            else:
                stats[teams[i]]['pts'] += 1
                stats[teams[j]]['pts'] += 1
                stats[teams[i]]['draws'] += 1
                stats[teams[j]]['draws'] += 1

    ranked = sorted(teams, key=lambda t: (
        stats[t]['pts'],
        stats[t]['gd'],
        stats[t]['gf'],
        stats[t]['wins']
    ), reverse=True)
    return ranked[:2], stats


def simulate_final_phase(teams):
    """Simulate final phase with 3 pathways. Returns (qualified, matchups)."""
    ranked = sorted(teams, key=lambda t: get_elo(t), reverse=True)
    seeded = ranked[:3]
    unseeded = ranked[3:]

    best_matchups = _find_pathways(seeded, unseeded)

    qualified = []
    matchups = []
    for seed, unseed in best_matchups:
        winner = simulate_win(seed, unseed)
        qualified.append(winner)
        matchups.append((seed, unseed, winner))

    return qualified, matchups


def _find_pathways(seeded, unseeded):
    """Find 3 pathway pairings avoiding same-confederation matchups."""
    best_matchups = list(zip(seeded, unseeded))
    best_same_conf = sum(1 for s, u in best_matchups if TEAM_CONF.get(s) == TEAM_CONF.get(u))

    for perm in itertools.permutations(unseeded):
        matchups = list(zip(seeded, perm))
        same_conf = sum(1 for s, u in matchups if TEAM_CONF.get(s) == TEAM_CONF.get(u))
        if same_conf < best_same_conf:
            best_same_conf = same_conf
            best_matchups = matchups
            if same_conf == 0:
                break

    return best_matchups


def simulate_inter_conf_playoff(preliminary_teams, bye_teams):
    """Simulate inter-confederation playoff. Returns (final_qualified, prelim_winners, prelim_stats, matchups)."""
    prelim_winners, prelim_stats = simulate_preliminary_phase(preliminary_teams)
    final_teams = bye_teams + prelim_winners
    final_qualified, matchups = simulate_final_phase(final_teams)
    return final_qualified, prelim_winners, prelim_stats, matchups


def simulate_caf_qualification():
    """
    Simulate CAF WC qualification starting directly from WAFCON 2026 QFs.
    
    QF1: Morocco vs South Africa (Simulated)
    QF2: Ivory Coast 1-2 Algeria (FIXED - Aug 8 result)
    QF3: Malawi vs Ghana (Simulated)
    QF4: Cameroon vs Nigeria (Simulated)
    
    QF winners qualify directly for WC (4 slots).
    QF losers enter play-in matches; play-in winners advance to inter-conf playoff.
    """
    # --- QUARTER-FINALS ---
    # QF1: Morocco vs South Africa
    qf1_winner = simulate_win("Morocco", "South Africa")
    qf1_loser = "South Africa" if qf1_winner == "Morocco" else "Morocco"

    # QF2: FIXED RESULT - Algeria beat Ivory Coast 2-1
    qf2_winner = "Algeria"
    qf2_loser = "Ivory Coast"

    # QF3: Malawi vs Ghana
    qf3_winner = simulate_win("Malawi", "Ghana")
    qf3_loser = "Ghana" if qf3_winner == "Malawi" else "Malawi"

    # QF4: Cameroon vs Nigeria
    qf4_winner = simulate_win("Cameroon", "Nigeria")
    qf4_loser = "Nigeria" if qf4_winner == "Cameroon" else "Cameroon"

    # Semi-finalists = Direct WC qualifiers (4 CAF slots)
    sf_participants = [qf1_winner, qf2_winner, qf3_winner, qf4_winner]

    # Simulate semis/final for completeness (doesn't affect WC qualification)
    sf1_winner = simulate_win(qf1_winner, qf4_winner)
    sf2_winner = simulate_win(qf2_winner, qf3_winner)
    simulate_win(sf1_winner, sf2_winner)  # Final

    # --- PLAY-IN MATCHES (determine inter-confederation playoff berths) ---
    # Play-in 1: Loser QF2 (Ivory Coast) vs Loser QF3
    playin1 = simulate_win(qf2_loser, qf3_loser)

    # Play-in 2: Loser QF1 vs Loser QF4
    playin2 = simulate_win(qf1_loser, qf4_loser)

    inter_conf = [playin1, playin2]
    return sf_participants, inter_conf


wc_qualifiers = defaultdict(int)
uefa_inter_conf = defaultdict(int)
uefa_final_phase = defaultdict(int)
inter_conf_participants = defaultdict(int)
inter_conf_wc_qualifiers = defaultdict(int)
inter_conf_by_conf = defaultdict(int)
preliminary_winners = defaultdict(int)
preliminary_runners_up = defaultdict(int)

print(f"\nRunning {N_SIMS} simulations...", file=sys.stderr)
update_interval = max(1, N_SIMS // 100)

for sim in range(N_SIMS):
    if sim % update_interval == 0:
        pct = sim / N_SIMS * 100
        print(f"\rProgress: {pct:.0f}%", end="", file=sys.stderr)

    w1 = simulate_tie("Lithuania", "Sweden")
    w2 = simulate_tie("Romania", "Norway")
    w3 = simulate_tie("Greece", "England")
    w4 = simulate_tie("Croatia", "Iceland")
    w5 = simulate_tie("Kazakhstan", "Republic of Ireland")
    w6 = simulate_tie("Kosovo", "Austria")
    w7 = simulate_tie("Hungary", "Netherlands")
    w8 = simulate_tie("Belarus", "Italy")

    w9  = simulate_tie("Albania", "Wales")
    w10 = simulate_tie("Turkey", "Slovenia")
    w11 = simulate_tie("Slovakia", "Ukraine")
    w12 = simulate_tie("Israel", "Switzerland")
    w13 = simulate_tie("Belgium", "Poland")
    w14 = simulate_tie("Czech Republic", "Scotland")
    w15 = simulate_tie("Northern Ireland", "Portugal")
    w16 = simulate_tie("Finland", "Serbia")

    path1 = [w1, w2, w3, w4, w5, w6, w7, w8]
    path2 = [w9, w10, w11, w12, w13, w14, w15, w16]
    r2_from_path1 = [
        simulate_tie(path1[0], path1[7]),
        simulate_tie(path1[1], path1[6]),
        simulate_tie(path1[2], path1[5]),
        simulate_tie(path1[3], path1[4]),
    ]
    r2_from_path2 = [
        simulate_tie(path2[0], path2[7]),
        simulate_tie(path2[1], path2[6]),
        simulate_tie(path2[2], path2[5]),
        simulate_tie(path2[3], path2[4]),
    ]
    r2_winners = r2_from_path1 + r2_from_path2
    r2_sorted = sorted(r2_winners, key=lambda t: NATIONALS_LEAGUE_RANK.get(t, 999))
    for i in range(7):
        wc_qualifiers[r2_sorted[i]] += 1
    uefa_inter_conf[r2_sorted[7]] += 1

    concacaf_d1 = simulate_win("USA", "El Salvador")
    concacaf_d2 = simulate_win("Jamaica", "Costa Rica")
    concacaf_d3 = simulate_win("Canada", "Panama")
    concacaf_d4 = simulate_win("Mexico", "Haiti")

    wc_qualifiers[concacaf_d1] += 1
    wc_qualifiers[concacaf_d2] += 1
    wc_qualifiers[concacaf_d3] += 1
    wc_qualifiers[concacaf_d4] += 1

    concacaf_losers = [t for t in ["USA", "El Salvador", "Jamaica", "Costa Rica", "Canada", "Panama", "Mexico", "Haiti"] if t not in [concacaf_d1, concacaf_d2, concacaf_d3, concacaf_d4]]

    concacaf_p1 = simulate_win(concacaf_losers[0], concacaf_losers[1])
    concacaf_p2 = simulate_win(concacaf_losers[2], concacaf_losers[3])

    # CAF qualification (starts directly from WAFCON QFs)
    caf_direct, caf_inter_conf = simulate_caf_qualification()
    for team in caf_direct:
        wc_qualifiers[team] += 1

    # Inter-confederation playoff
    preliminary_teams = ["Uzbekistan", "Chinese Taipei"] + caf_inter_conf + ["Papua New Guinea", "Ecuador"]
    bye_teams = [concacaf_p1, concacaf_p2, r2_sorted[7], "Venezuela"]

    inter_conf_wc, prelim_winners, prelim_stats, matchups = simulate_inter_conf_playoff(preliminary_teams, bye_teams)

    for team in preliminary_teams + bye_teams:
        inter_conf_participants[team] += 1

    for team in inter_conf_wc:
        inter_conf_wc_qualifiers[team] += 1

    confs_with_slot = {TEAM_CONF.get(team, "Unknown") for team in inter_conf_wc}
    for conf in confs_with_slot:
        inter_conf_by_conf[conf] += 1

    uefa_final_phase[r2_sorted[7]] += 1
    preliminary_winners[prelim_winners[0]] += 1
    preliminary_runners_up[prelim_winners[1]] += 1
    last_prelim_stats = prelim_stats
    last_matchups = matchups

qualification_prob = defaultdict(float)

for team in ALREADY_QUALIFIED:
    qualification_prob[team] = 1.0

for team in wc_qualifiers:
    qualification_prob[team] += wc_qualifiers[team] / N_SIMS

for team in inter_conf_wc_qualifiers:
    qualification_prob[team] += inter_conf_wc_qualifiers[team] / N_SIMS

print(f"\rProgress: 100%", file=sys.stderr)

all_qualifiers = sorted(qualification_prob.items(), key=lambda x: x[1], reverse=True)
top_32 = all_qualifiers[:32]
certainty = sum(prob for _, prob in top_32) / 32 * 100

print(f"\nQUALIFICATION CERTAINTY: {certainty:.2f}%")
print(f"(Average probability of the 32 most likely qualifiers)\n")

print(f"\nWORLD CUP QUALIFICATION PROBABILITY BY CONFEDERATION\n")
for conf in CONF_NAMES:
    conf_teams = sorted(
        [(team, prob) for team, prob in all_qualifiers if TEAM_CONF.get(team) == conf],
    key=lambda x: x[1],
        reverse=True,
    )
    if not conf_teams:
        continue
    print(f"\n{conf}")
    print("-" * 35)
    for team, prob in conf_teams:
        print(f"{team:25s}{prob*100:6.2f}%")

most_likely_uefa_inter = max(uefa_inter_conf.items(), key=lambda x: x[1], default=(None, 0))
if most_likely_uefa_inter[0]:
    print(f"\nMOST LIKELY UEFA TEAM TO ENTER INTER-CONFEDERATION PLAY-OFF FINAL PHASE: {most_likely_uefa_inter[0]} ({most_likely_uefa_inter[1] / N_SIMS * 100:.2f}%)")

print(f"\n\nPRELIMINARY PHASE RESULTS (Last Simulation)")
print(f"(Top 2 advance to final phase)\n")
if last_prelim_stats:
    print("-" * 50)
    print(f"{'Team':20s} {'Pld':>4s} {'W':>3s} {'D':>3s} {'L':>3s} {'GF':>4s} {'GA':>4s} {'GD':>5s} {'Pts':>4s}")
    print("-" * 50)
    for team in sorted(last_prelim_stats.keys(), key=lambda t: (last_prelim_stats[t]['pts'], last_prelim_stats[t]['gd'], last_prelim_stats[t]['gf'], last_prelim_stats[t]['wins']), reverse=True):
        s = last_prelim_stats[team]
        pld = s['wins'] + s['draws'] + s['losses']
        print(f"{team:20s} {pld:4d} {s['wins']:3d} {s['draws']:3d} {s['losses']:3d} {s['gf']:4d} {s['ga']:4d} {s['gd']:5d} {s['pts']:4d}")
    print("-" * 50)
    top2 = sorted(last_prelim_stats.keys(), key=lambda t: (last_prelim_stats[t]['pts'], last_prelim_stats[t]['gd'], last_prelim_stats[t]['gf'], last_prelim_stats[t]['wins']), reverse=True)[:2]
    print(f"Advancing: {', '.join(top2)}")

print(f"\n\nPRELIMINARY PHASE - PROBABILITY OF ADVANCING\n")
print(f"(Chance of finishing in top 2)\n")
prelim_advance = sorted(
    [(team, (preliminary_winners[team] + preliminary_runners_up[team]) / N_SIMS)
     for team in preliminary_winners],
    key=lambda x: x[1],
    reverse=True,
)
print("-" * 40)
print(f"{'Team':25s} {'Advance %':>12s}")
for team, prob in prelim_advance:
    print(f"{team:25s} {prob*100:11.2f}%")

print(f"\n\nFINAL PHASE RESULTS (Last Simulation)\n")
if last_matchups:
    print("-" * 60)
    for seed, unseed, winner in last_matchups:
        print(f"{seed:20s} vs {unseed:20s} -> {winner:20s} WIN")
    print("-" * 60)

print(f"\n\nINTER-CONFEDERATION PLAY-OFF PROBABILITIES\n")
print(f"(Chance of qualifying for the World Cup through play-offs)\n")
inter_conf_teams = sorted(
    [(team, inter_conf_participants[team] / N_SIMS, inter_conf_wc_qualifiers[team] / N_SIMS)
     for team in inter_conf_participants],
    key=lambda x: x[2],
    reverse=True,
)
print("-" * 60)
print(f"{'Team':25s} {'Reach Play-off':>15s} {'Qualify via Play-off':>20s}")
for team, reach, qualify in inter_conf_teams:
    print(f"{team:25s} {reach*100:13.2f}% {qualify*100:19.2f}%")

print(f"\n\nCONFEDERATION INTER-CONFEDERATION SLOT PROBABILITY\n")
print(f"(Chance of getting at least one World Cup spot via inter-confederation playoff)\n")
for conf in CONF_NAMES:
    if conf in inter_conf_by_conf:
        prob = inter_conf_by_conf[conf] / N_SIMS * 100
        print(f"{conf}: {prob:.2f}%")