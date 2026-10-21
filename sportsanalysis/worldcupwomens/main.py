import itertools
import random
import sys
from collections import defaultdict

# ==============================================================================
# 1. HARDCODED ELO DATA & CONFIGURATION
# ==============================================================================

ELO = {
    "Spain": 2284.9262739065603, "United States": 2254.309585058014,
    "England": 2179.5916960182017, "France": 2178.6298637210734,
    "Germany": 2161.5333220943658, "Japan": 2119.0506637646718,
    "Sweden": 2104.586100507047, "Brazil": 2078.5661801767096,
    "Canada": 2003.587144027174, "Netherlands": 2001.4301233662618,
    "Italy": 1990.4575536463165, "Denmark": 1973.935687559122,
    "Norway": 1956.6724805801093, "Australia": 1955.1906151344554,
    "Nigeria": 1924.4916747926336, "North Korea": 1917.1232780331454,
    "Mexico": 1912.6880965842267, "Colombia": 1872.1102769202141,
    "China": 1860.736158444353, "Belgium": 1846.8632779167317,
    "South Korea": 1823.9306509978148, "South Africa": 1816.361031406711,
    "Republic of Ireland": 1806.0844329950974, "Finland": 1799.4528423595425,
    "Haiti": 1793.0750708754606, "Iceland": 1780.5416539162816,
    "Portugal": 1780.1248555043198, "Jamaica": 1779.142729809712,
    "Switzerland": 1768.374441462899, "Poland": 1755.6238384879412,
    "Scotland": 1753.6452357253322, "Austria": 1752.4572412544048,
    "Panama": 1743.8159691927258, "Russia": 1743.0064282341211,
    "Ghana": 1739.5227646321755, "Argentina": 1737.2637391750538,
    "Puerto Rico": 1722.9720114141837, "Dominican Republic": 1701.4672140972434,
    "Costa Rica": 1699.820617885052, "Morocco": 1694.8758327766068,
    "Cameroon": 1691.180524429991, "Algeria": 1690.7939333289646,
    "Zambia": 1687.530729284643, "Wales": 1686.0901807306468,
    "Taiwan": 1678.376707644798, "New Zealand": 1678.110833824586,
    "El Salvador": 1671.106965703179, "Philippines": 1664.1915902969727,
    "Cuba": 1663.3002158819286, "Serbia": 1662.6430311908132,
    "Ivory Coast": 1636.88761797785, "Czech Republic": 1625.7038531384997,
    "Vietnam": 1603.8880441374074, "Slovenia": 1600.1487267379835,
    "Senegal": 1597.5527674285318, "Thailand": 1596.682474370542,
    "Trinidad and Tobago": 1592.825281912848, "Myanmar": 1589.4770041356107,
    "Guyana": 1578.891834062665, "Burkina Faso": 1577.578152613042,
    "Ukraine": 1573.7320350355546, "Papua New Guinea": 1570.6614548838156,
    "Zimbabwe": 1569.4388908492656, "Uzbekistan": 1563.8479144685493,
    "Mali": 1560.513236661854, "Kenya": 1552.294348404835,
    "Congo": 1549.3535136636406, "Chile": 1545.7068177389922,
    "Nepal": 1541.1865458520099, "Fiji": 1537.3955240938253,
    "Bermuda": 1536.587762036813, "Jordan": 1536.4531180932029,
    "Venezuela": 1528.897970597349, "Guatemala": 1527.1287017252375,
    "Tanzania": 1521.5549212562994, "Cape Verde": 1521.1714820078462,
    "Hong Kong": 1515.400717586059, "Uruguay": 1511.0812840761191,
    "Paraguay": 1506.5258263474266, "Turkey": 1505.9454059338248,
    "Pakistan": 1504.2960032773576, "American Samoa": 1498.3776020747543,
    "Lebanon": 1494.3840256633164, "Malawi": 1491.6357300114182,
    "Cook Islands": 1488.511304641914, "Nicaragua": 1487.3988518034403,
    "Cambodia": 1487.3479006038676, "Egypt": 1485.722167198696,
    "Afghanistan": 1484.7419744556605, "India": 1480.1115962685199,
    "Togo": 1479.2479173585323, "Gambia": 1477.7807598389627,
    "Tahiti": 1476.2752272472956, "Ethiopia": 1475.9127234903237,
    "Hungary": 1474.9136405974505, "Botswana": 1474.7808769944938,
    "Slovakia": 1473.1678804242747, "Samoa": 1472.7214261129045,
    "Iran": 1470.4799172690616, "Benin": 1469.6999305135014,
    "Guinea-Bissau": 1468.1213558445036, "Northern Ireland": 1465.477825380882,
    "Mauritania": 1461.8354219328246, "Sudan": 1460.5253244142732,
    "Burundi": 1456.7528765133704, "Namibia": 1454.8319351893006,
    "Tunisia": 1454.2819062399756, "Tonga": 1452.145128004699,
    "New Caledonia": 1450.2005339917528, "Saudi Arabia": 1448.455725396761,
    "Malaysia": 1447.940412650524, "Timor-Leste": 1446.921587813184,
    "Belize": 1446.6259561004124, "Comoros": 1445.6048758519385,
    "Central African Republic": 1445.1167757091232, "Vanuatu": 1444.5586025413147,
    "DR Congo": 1443.1059506029214, "Liberia": 1441.810437110895,
    "Mozambique": 1439.686001711027, "Rwanda": 1439.2910603252212,
    "Belarus": 1437.9964091616578, "Solomon Islands": 1437.3636167105312,
    "Uganda": 1432.1061725176974, "Aruba": 1428.1315830449782,
    "Suriname": 1424.6454056776552, "Saint Kitts and Nevis": 1422.6220416335123,
    "Bhutan": 1421.973855731539, "Curaçao": 1420.9851146513872,
    "Bangladesh": 1417.725086956194, "Turkmenistan": 1414.465656350618,
    "Angola": 1413.909376671671, "United Arab Emirates": 1407.6209977807707,
    "Saint Lucia": 1407.046068169602, "Guam": 1405.9068550943039,
    "Equatorial Guinea": 1405.0679012264566, "Romania": 1397.8840127524036,
    "Mauritius": 1395.2979024442543, "South Sudan": 1393.2737565950579,
    "Indonesia": 1391.679441952053, "Laos": 1391.3390674235973,
    "Sierra Leone": 1390.0442997400735, "Ecuador": 1383.8600368225375,
    "Gabon": 1382.3136024204543, "Niger": 1379.9453592859786,
    "Honduras": 1372.3136848623888, "Israel": 1367.6531159880437,
    "Lesotho": 1366.009487941098, "Sri Lanka": 1365.7773626004378,
    "Greece": 1364.5658224312074, "Seychelles": 1364.3591225469393,
    "Albania": 1364.025393260661, "Croatia": 1362.0546948449924,
    "Libya": 1359.1740374955602, "Bosnia and Herzegovina": 1358.3166198533734,
    "Kuwait": 1354.9065666318795, "Grenada": 1354.0255746127655,
    "Djibouti": 1350.3066866385122, "Macau": 1347.5457174746114,
    "Saint Vincent and the Grenadines": 1347.501685375893,
    "Iraq": 1340.2849812818554, "Eritrea": 1339.4474371758984,
    "United States Virgin Islands": 1335.4002784685401,
    "Syria": 1327.4969363023758, "Kosovo": 1325.7668788266956,
    "Kyrgyzstan": 1325.311275876686, "Palestine": 1318.881281874098,
    "Singapore": 1317.0273388218473, "Guinea": 1305.6454952450242,
    "Eswatini": 1291.3337383155517, "Barbados": 1289.8879888136405,
    "Tajikistan": 1280.216603435321, "Bahamas": 1275.049084456468,
    "Azerbaijan": 1274.4664763379076, "Bahrain": 1267.2194595781702,
    "Montenegro": 1262.5326625232722, "Mongolia": 1260.347998649735,
    "Anguilla": 1243.1909587653192, "Antigua and Barbuda": 1234.5996097184498,
    "Lithuania": 1230.3628774187287, "Luxembourg": 1210.5043460927766,
    "Dominica": 1208.8474047133852, "British Virgin Islands": 1205.4098168653713,
    "Maldives": 1200.4382840365486, "Cayman Islands": 1198.0056451940468,
    "Latvia": 1185.0186623202724, "Faroe Islands": 1179.4279758647845,
    "Malta": 1177.842984113832, "Kazakhstan": 1165.9391469671746,
    "Peru": 1154.9266280552565, "Estonia": 1151.9204175320128,
    "Moldova": 1132.881945411716, "Bolivia": 1118.031811927346,
    "Turks and Caicos Islands": 1100.3005127701151,
    "Bulgaria": 1067.869776316505, "North Macedonia": 1056.1598756065662,
    "Cyprus": 1041.1846726322742, "Georgia": 1038.976487981929,
    "Liechtenstein": 982.9585504406526, "Andorra": 976.7733151502741,
    "Armenia": 969.8234841918982, "Gibraltar": 967.5415620239187,
}

# Mapping Simulation Names -> Hardcoded CSV Names
NAME_MAP = {
    "USA": "United States",
    "China PR": "China",
    "Korea DPR": "North Korea",
    "Korea Republic": "South Korea",
    "Chinese Taipei": "Taiwan",
    "Congo DR": "DR Congo",
    "The Gambia": "Gambia",
    "St Kitts and Nevis": "Saint Kitts and Nevis",
    "St Vincent and the Grenadines": "Saint Vincent and the Grenadines",
    "St Lucia": "Saint Lucia",
    "US Virgin Islands": "United States Virgin Islands",
}

def get_elo_key(team: str) -> str:
    return NAME_MAP.get(team, team)

def get_elo(team: str) -> float:
    key = get_elo_key(team)
    if key in ELO:
        return ELO[key]
    print(f"Warning: ELO not found for {team} (mapped to {key}). Using 1500.0.")
    return 1500.0

# ==============================================================================
# 2. CONFIGURATION & STATE
# ==============================================================================

ALREADY_QUALIFIED = {
    "Brazil", "Denmark", "France", "Germany", "Spain",
    "Australia", "China", "Japan", "North Korea", "South Korea", "Philippines",
    "Algeria", "Cameroon", "Malawi", "Morocco",
    "Argentina", "Colombia",
    "New Zealand",
}

SLOT_ALLOCATION = {
    "AFC": {"slots": 6, "inter_conf_slots": 2, "teams": ["Australia", "China", "Japan", "North Korea", "Philippines", "South Korea"], "inter_conf_teams": ["Uzbekistan", "Chinese Taipei"]},
    "CAF": {"slots": 4, "inter_conf_slots": 2, "teams": ["Algeria", "Cameroon", "Malawi", "Morocco"], "inter_conf_teams": ["Ghana", "South Africa"]},
    "CONCACAF": {"slots": 4, "inter_conf_slots": 2, "teams": [], "inter_conf_mode": "final_phase_bye"},
    "CONMEBOL": {"slots": 3, "inter_conf_slots": 2, "teams": ["Argentina", "Colombia", "Brazil"], "inter_conf_teams": ["Venezuela", "Ecuador"]},
    "OFC": {"slots": 1, "inter_conf_slots": 1, "teams": ["New Zealand"], "inter_conf_team": "Papua New Guinea"},
    "UEFA": {"slots": 11, "inter_conf_slots": 1, "teams": ["Denmark", "France", "Germany", "Spain"], "inter_conf_mode": "final_phase_seeded"},
}

N_SIMS = 2500
RANDOM_SEED = None

for arg in sys.argv[1:]:
    if arg.startswith("--seed="):
        RANDOM_SEED = int(arg.split("=")[1])

if RANDOM_SEED is not None:
    random.seed(RANDOM_SEED)

TEAM_CONF = {
    "Australia": "AFC", "China": "AFC", "Japan": "AFC", "North Korea": "AFC", "Philippines": "AFC", "South Korea": "AFC",
    "Uzbekistan": "AFC", "Chinese Taipei": "AFC",
    "Algeria": "CAF", "Cameroon": "CAF", "Malawi": "CAF", "Morocco": "CAF",
    "Ghana": "CAF", "South Africa": "CAF", "Nigeria": "CAF", "Egypt": "CAF", "Ivory Coast": "CAF", 
    "Senegal": "CAF", "Kenya": "CAF", "Tanzania": "CAF", "Burkina Faso": "CAF", "Zambia": "CAF", 
    "Mali": "CAF", "Cape Verde": "CAF",
    "USA": "CONCACAF", "Canada": "CONCACAF", "Mexico": "CONCACAF", "Costa Rica": "CONCACAF",
    "Jamaica": "CONCACAF", "Panama": "CONCACAF", "Haiti": "CONCACAF", "El Salvador": "CONCACAF",
    "Argentina": "CONMEBOL", "Brazil": "CONMEBOL", "Colombia": "CONMEBOL",
    "Venezuela": "CONMEBOL", "Ecuador": "CONMEBOL",
    "New Zealand": "OFC", "Papua New Guinea": "OFC",
    "Spain": "UEFA", "Germany": "UEFA", "England": "UEFA", "France": "UEFA", "Netherlands": "UEFA",
    "Sweden": "UEFA", "Denmark": "UEFA", "Norway": "UEFA", "Italy": "UEFA", "Iceland": "UEFA",
    "Republic of Ireland": "UEFA", "Austria": "UEFA", "Poland": "UEFA", "Serbia": "UEFA", "Ukraine": "UEFA",
    "Portugal": "UEFA", "Switzerland": "UEFA", "Scotland": "UEFA", "Belgium": "UEFA", "Finland": "UEFA",
    "Wales": "UEFA", "Czech Republic": "UEFA", "Turkey": "UEFA", "Northern Ireland": "UEFA", "Israel": "UEFA",
    "Slovakia": "UEFA", "Slovenia": "UEFA", "Albania": "UEFA", "Lithuania": "UEFA", "Kosovo": "UEFA", 
    "Belarus": "UEFA", "Kazakhstan": "UEFA", "Hungary": "UEFA", "Greece": "UEFA", "Romania": "UEFA", 
    "Croatia": "UEFA",
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

# ==============================================================================
# 3. SIMULATION FUNCTIONS
# ==============================================================================

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


def simulate_tie_with_first_leg(team1, team2, first_leg_goals1, first_leg_goals2):
    """Two-legged tie with a known first-leg result.
    team1 hosted the 1st leg, team2 hosts the 2nd leg."""
    goals1_1 = first_leg_goals1
    goals2_1 = first_leg_goals2

    elo_diff_2 = get_elo(team2) + 60 - get_elo(team1)
    p_home2 = 1 / (1 + 10 ** (-elo_diff_2 / 400))
    draw_prob = 0.24

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
    """Single match at neutral venue. Returns winner or None for draw."""
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

    seeded = []
    used_confs = set()
    for team in ranked:
        conf = TEAM_CONF.get(team)
        if conf and conf not in used_confs:
            seeded.append(team)
            used_confs.add(conf)
            if len(seeded) == 3:
                break

    unseeded = [t for t in ranked if t not in seeded]

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
    """Simulate inter-confederation playoff.
    Returns (final_qualified, prelim_winners, prelim_stats, matchups)."""
    prelim_winners, prelim_stats = simulate_preliminary_phase(preliminary_teams)
    final_teams = bye_teams + prelim_winners
    final_qualified, matchups = simulate_final_phase(final_teams)
    return final_qualified, prelim_winners, prelim_stats, matchups


# ==============================================================================
# 4. SIMULATION ENGINE  (single source of truth for CLI + dashboard)
# ==============================================================================

def run_simulation(n_sims, on_progress=None, is_running=None):
    """
    Run the Monte Carlo qualification simulation.

    on_progress : optional callable(sim_index, live_data_dict) fired ~100x per run
    is_running  : optional callable() -> bool; return False to stop early

    Returns a dict of aggregated results.
    """
    wc_qualifiers = defaultdict(int)
    uefa_inter_conf = defaultdict(int)
    uefa_final_phase = defaultdict(int)
    inter_conf_participants = defaultdict(int)
    inter_conf_wc_qualifiers = defaultdict(int)
    inter_conf_by_conf = defaultdict(int)
    preliminary_winners = defaultdict(int)
    preliminary_runners_up = defaultdict(int)
    prelim_stats_sum = {t: {'pts': 0, 'gf': 0, 'ga': 0, 'gd': 0,
                            'wins': 0, 'draws': 0, 'losses': 0}
                        for t in ["Uzbekistan", "Chinese Taipei", "Ghana",
                                  "South Africa", "Papua New Guinea", "Ecuador"]}

    update_interval = max(1, n_sims // 100)
    last_matchups = None

    for sim in range(n_sims):
        if is_running is not None and not is_running():
            break

        if on_progress is not None and sim % update_interval == 0:
            on_progress(sim, {
                'wc_qualifiers': dict(wc_qualifiers),
                'uefa_inter_conf': dict(uefa_inter_conf),
                'inter_conf_wc': dict(inter_conf_wc_qualifiers),
            })

        # --- UEFA PLAYOFFS (Round 2) ---
        r2_ties = [
            ("Ukraine", "England"),
            ("Finland", "Italy"),
            ("Portugal", "Iceland"),
            ("Wales", "Norway"),
            ("Switzerland", "Austria"),
            ("Scotland", "Sweden"),
            ("Poland", "Republic of Ireland"),
            ("Slovenia", "Netherlands"),
        ]
        r2_winners = [simulate_tie(t1, t2) for t1, t2 in r2_ties]
        r2_sorted = sorted(r2_winners,
                           key=lambda t: NATIONALS_LEAGUE_RANK.get(t, 999))

        for i in range(7):
            wc_qualifiers[r2_sorted[i]] += 1
        uefa_inter_conf[r2_sorted[7]] += 1

        # --- CONCACAF CHAMPIONSHIP ---
        concacaf_d1 = simulate_win("USA", "El Salvador")
        concacaf_d2 = simulate_win("Jamaica", "Costa Rica")
        concacaf_d3 = simulate_win("Canada", "Panama")
        concacaf_d4 = simulate_win("Mexico", "Haiti")

        wc_qualifiers[concacaf_d1] += 1
        wc_qualifiers[concacaf_d2] += 1
        wc_qualifiers[concacaf_d3] += 1
        wc_qualifiers[concacaf_d4] += 1

        all_concacaf_qf = ["USA", "El Salvador", "Jamaica", "Costa Rica",
                           "Canada", "Panama", "Mexico", "Haiti"]
        concacaf_losers = [t for t in all_concacaf_qf
                           if t not in (concacaf_d1, concacaf_d2,
                                        concacaf_d3, concacaf_d4)]
        concacaf_p1 = simulate_win(concacaf_losers[0], concacaf_losers[1])
        concacaf_p2 = simulate_win(concacaf_losers[2], concacaf_losers[3])

        # --- INTER-CONFEDERATION PLAYOFF ---
        preliminary_teams = ["Uzbekistan", "Chinese Taipei", "Ghana",
                             "South Africa", "Papua New Guinea", "Ecuador"]
        bye_teams = [concacaf_p1, concacaf_p2, r2_sorted[7], "Venezuela"]

        inter_conf_wc, prelim_winners_list, prelim_stats, matchups = \
            simulate_inter_conf_playoff(preliminary_teams, bye_teams)

        for team in preliminary_teams + bye_teams:
            inter_conf_participants[team] += 1
        for team in inter_conf_wc:
            inter_conf_wc_qualifiers[team] += 1
            wc_qualifiers[team] += 1

        for conf in {TEAM_CONF.get(t, "Unknown") for t in inter_conf_wc}:
            inter_conf_by_conf[conf] += 1

        uefa_final_phase[r2_sorted[7]] += 1
        preliminary_winners[prelim_winners_list[0]] += 1
        preliminary_runners_up[prelim_winners_list[1]] += 1

        for team, stats in prelim_stats.items():
            for key in prelim_stats_sum[team]:
                prelim_stats_sum[team][key] += stats[key]

        last_matchups = matchups

    # --- Aggregate ---
    qualification_prob = defaultdict(float)
    for team in ALREADY_QUALIFIED:
        qualification_prob[team] = 1.0
    for team, count in wc_qualifiers.items():
        qualification_prob[team] += count / n_sims

    all_qualifiers = sorted(qualification_prob.items(),
                            key=lambda x: x[1], reverse=True)

    return {
        'wc_qualifiers': dict(wc_qualifiers),
        'qualification_prob': dict(qualification_prob),
        'all_qualifiers': all_qualifiers,
        'uefa_inter_conf': dict(uefa_inter_conf),
        'uefa_final_phase': dict(uefa_final_phase),
        'inter_conf_participants': dict(inter_conf_participants),
        'inter_conf_wc_qualifiers': dict(inter_conf_wc_qualifiers),
        'inter_conf_by_conf': dict(inter_conf_by_conf),
        'preliminary_winners': dict(preliminary_winners),
        'preliminary_runners_up': dict(preliminary_runners_up),
        'prelim_stats_sum': prelim_stats_sum,
        'last_matchups': last_matchups,
        'n_sims': n_sims,
    }


# ==============================================================================
# 5. CLI ENTRY POINT
# ==============================================================================

def main():
    print(f"\nRunning {N_SIMS} simulations...", file=sys.stderr)

    def progress(sim, _):
        print(f"\rProgress: {sim / N_SIMS * 100:.0f}%",
              end="", file=sys.stderr)

    results = run_simulation(N_SIMS, on_progress=progress)
    print(f"\rProgress: 100%", file=sys.stderr)

    n = results['n_sims']
    qualification_prob = results['qualification_prob']
    all_qualifiers = results['all_qualifiers']
    uefa_inter_conf = results['uefa_inter_conf']
    inter_conf_participants = results['inter_conf_participants']
    inter_conf_wc_qualifiers = results['inter_conf_wc_qualifiers']
    inter_conf_by_conf = results['inter_conf_by_conf']
    preliminary_winners = results['preliminary_winners']
    preliminary_runners_up = results['preliminary_runners_up']
    prelim_stats_sum = results['prelim_stats_sum']
    last_matchups = results['last_matchups']

    top_32 = all_qualifiers[:32]
    certainty = sum(prob for _, prob in top_32) / 32 * 100

    most_likely = max(uefa_inter_conf.items(), key=lambda x: x[1], default=(None, 0))
    if most_likely[0]:
        print(f"\nMOST LIKELY UEFA TEAM TO ENTER INTER-CONFEDERATION PLAY-OFF FINAL PHASE:")
        print(f"-> {most_likely[0]} ({most_likely[1] / n * 100:.2f}%)")

    print(f"\n\n{'='*60}")
    print(f"PRELIMINARY PHASE RESULTS (Average over {n} simulations)")
    print(f"(Top 2 advance to final phase)")
    print(f"{'='*60}")
    print(f"{'Team':20s} {'Pld':>4s} {'W':>4s} {'D':>4s} {'L':>4s} "
          f"{'GF':>5s} {'GA':>5s} {'GD':>6s} {'Pts':>5s}")
    print("-" * 60)
    for team in sorted(
        prelim_stats_sum.keys(),
        key=lambda t: (prelim_stats_sum[t]['pts'] / n,
                       prelim_stats_sum[t]['gd'] / n,
                       prelim_stats_sum[t]['gf'] / n,
                       prelim_stats_sum[t]['wins'] / n),
        reverse=True,
    ):
        s = prelim_stats_sum[team]
        pld = (s['wins'] + s['draws'] + s['losses']) / n
        print(f"{team:20s} {pld:4.1f} {s['wins']/n:4.2f} {s['draws']/n:4.2f} "
              f"{s['losses']/n:4.2f} {s['gf']/n:5.2f} {s['ga']/n:5.2f} "
              f"{s['gd']/n:6.2f} {s['pts']/n:5.2f}")
    print("-" * 60)
    top2 = sorted(
        prelim_stats_sum.keys(),
        key=lambda t: (prelim_stats_sum[t]['pts'] / n,
                       prelim_stats_sum[t]['gd'] / n,
                       prelim_stats_sum[t]['gf'] / n,
                       prelim_stats_sum[t]['wins'] / n),
        reverse=True,
    )[:2]
    print(f"Avg top 2: {', '.join(top2)}")

    print(f"\n\nPRELIMINARY PHASE - PROBABILITY OF ADVANCING")
    print(f"(Chance of finishing in top 2)")
    print("-" * 45)
    print(f"{'Team':25s} {'Advance %':>12s}")
    prelim_advance = sorted(
        [(team, (preliminary_winners[team] + preliminary_runners_up[team]) / n)
         for team in set(list(preliminary_winners) + list(preliminary_runners_up))],
        key=lambda x: x[1], reverse=True,
    )
    for team, prob in prelim_advance:
        print(f"{team:25s} {prob*100:11.2f}%")

    print(f"\n\nFINAL PHASE RESULTS (Last Simulation)")
    print("-" * 65)
    if last_matchups:
        for seed, unseed, winner in last_matchups:
            print(f"{seed:20s} vs {unseed:20s} -> {winner:20s} WIN")
    print("-" * 65)

    print(f"\n\nINTER-CONFEDERATION PLAY-OFF PROBABILITIES")
    print(f"(Chance of qualifying for the World Cup through play-offs)")
    print("-" * 70)
    print(f"{'Team':25s} {'Reach Play-off':>15s} {'Qualify via Play-off':>20s}")
    inter_conf_teams = sorted(
        [(team, inter_conf_participants[team] / n,
          inter_conf_wc_qualifiers[team] / n)
         for team in inter_conf_participants],
        key=lambda x: x[2], reverse=True,
    )
    for team, reach, qualify in inter_conf_teams:
        print(f"{team:25s} {reach*100:13.2f}% {qualify*100:19.2f}%")

    print(f"\n\nCONFEDERATION INTER-CONFEDERATION SLOT PROBABILITY")
    print(f"(Chance of getting at least one World Cup spot via inter-confederation playoff)")
    print("-" * 70)
    for conf in CONF_NAMES:
        if conf in inter_conf_by_conf:
            print(f"{conf:10s}: {inter_conf_by_conf[conf] / n * 100:.2f}%")

    print(f"\n\nWORLD CUP QUALIFICATION PROBABILITY BY CONFEDERATION\n")
    for conf in CONF_NAMES:
        conf_teams = sorted(
            [(t, p) for t, p in all_qualifiers if TEAM_CONF.get(t) == conf],
            key=lambda x: x[1], reverse=True,
        )
        if not conf_teams:
            continue
        print(f"\n[{conf}]")
        print("-" * 40)
        for team, prob in conf_teams:
            marker = " [Q]" if prob >= 0.99 else ""
            print(f"{team:25s} {prob*100:6.2f}%{marker}")

    print(f"\n{'='*60}")
    print(f"QUALIFICATION CERTAINTY: {certainty:.2f}%")
    print(f"(Average probability of the 32 most likely qualifiers)")
    print(f"{'='*60}\n")


if __name__ == "__main__":
    main()