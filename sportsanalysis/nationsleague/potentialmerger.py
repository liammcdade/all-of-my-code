import random
from collections import defaultdict
from tqdm import tqdm

# Set seed for reproducibility of mock data generation and simulations
random.seed(42)

# ==========================================
# 1. DATA: TEAM ELO RATINGS
# ==========================================
concacaf_elo = {
    "Mexico": 1913, "United States": 1746, "Canada": 1729, "Panama": 1650,
    "Costa Rica": 1576, "Honduras": 1570, "Haiti": 1530, "Jamaica": 1527,
    "Guatemala": 1504, "Curaçao": 1471, "Suriname": 1431, "Trinidad and Tobago": 1373,
    "El Salvador": 1342, "Guadeloupe": 1338, "Nicaragua": 1316, "Martinique": 1312,
    "Guyana": 1304, "Dominican Republic": 1300, "Cuba": 1239, "French Guiana": 1223,
    "Saint Vincent and the Grenadines": 1141, "Puerto Rico": 1124, "Bermuda": 1117,
    "Grenada": 1098, "Belize": 1073, "Saint Martin": 1053, "Saint Kitts and Nevis": 1030,
    "Saint Lucia": 1003, "Aruba": 1000, "Montserrat": 985, "Sint Maarten": 974,
    "Dominica": 925, "Barbados": 898, "Antigua and Barbuda": 874, "Bonaire": 817,
    "Cayman Islands": 812, "British Virgin Islands": 743, "Bahamas": 674,
    "Anguilla": 644, "Turks and Caicos Islands": 644, "US Virgin Islands": 627
}

uefa_elo = {
    "Spain": 2259, "France": 2125, "England": 2070, "Portugal": 1998,
    "Netherlands": 1962, "Norway": 1955, "Belgium": 1947, "Switzerland": 1928,
    "Germany": 1913, "Croatia": 1896, "Italy": 1882, "Denmark": 1859,
    "Turkey": 1852, "Austria": 1838, "Ukraine": 1786, "Russia": 1772,
    "Greece": 1769, "Scotland": 1761, "Sweden": 1755, "Serbia": 1746,
    "Hungary": 1736, "Poland": 1732, "Wales": 1728, "Romania": 1720,
    "Republic of Ireland": 1708, "Slovenia": 1704, "Czechia": 1694, "Albania": 1665,
    "North Macedonia": 1645, "Georgia": 1642, "Bosnia and Herzegovina": 1636,
    "Slovakia": 1615, "Bulgaria": 1608, "Finland": 1583, "Iceland": 1579,
    "Israel": 1571, "Montenegro": 1541, "Northern Ireland": 1536, "Kosovo": 1509,
    "Azerbaijan": 1482, "Kazakhstan": 1476, "Belarus": 1455, "Armenia": 1442,
    "Latvia": 1429, "Cyprus": 1420, "Luxembourg": 1417, "Lithuania": 1405,
    "Estonia": 1393, "Faroe Islands": 1383, "Moldova": 1308, "Malta": 1245,
    "Andorra": 1204, "Gibraltar": 1163, "Liechtenstein": 1113, "San Marino": 1084
}

CONCACAF_SET = set(concacaf_elo.keys())

# ==========================================
# 2. SIMULATION ENGINE
# ==========================================
def simulate_match(elo_a, elo_b, is_knockout=False):
    elo_diff = (elo_a - elo_b + 100) if not is_knockout else (elo_a - elo_b)
    expected_a = 1 / (1 + 10**(-elo_diff / 400))
    p_draw = max(0.10, 0.25 - abs(elo_diff) / 1000)
    remaining = 1.0 - p_draw

    if expected_a >= 1.0:
        p_home, p_away = 1.0, 0.0
    elif expected_a <= 0.0:
        p_home, p_away = 0.0, 1.0
    else:
        ratio = expected_a / (1.0 - expected_a)
        p_home = remaining * (ratio / (1.0 + ratio))
        p_away = remaining - p_home

    roll = random.random()
    if roll < p_home:
        return 'A'
    elif roll < p_home + p_draw:
        return 'D'
    else:
        return 'B'

def simulate_knockout(elo_a, elo_b):
    elo_diff = elo_a - elo_b
    p_a = 1 / (1 + 10**(-elo_diff / 400))
    return 'A' if random.random() < p_a else 'B'

def simulate_group(teams):
    standings = {t: {'pts': 0, 'gd': 0, 'gf': 0, 'ga': 0, 'name': t} for t in teams}
    team_list = list(teams)

    for i in range(len(team_list)):
        for j in range(i + 1, len(team_list)):
            t1, t2 = team_list[i], team_list[j]
            elo1, elo2 = teams[t1], teams[t2]

            if (i + j) % 2 == 0:
                result = simulate_match(elo1, elo2)
                home, away = t1, t2
            else:
                result = simulate_match(elo2, elo1)
                home, away = t2, t1

            if result == 'D':
                standings[t1]['pts'] += 1
                standings[t2]['pts'] += 1
                goals = random.choice([0, 1, 2])
                standings[t1]['gf'] += goals
                standings[t1]['ga'] += goals
                standings[t2]['gf'] += goals
                standings[t2]['ga'] += goals
            elif result == 'A':
                standings[home]['pts'] += 3
                gf_h = random.choice([1, 2, 3, 4])
                gf_a = random.choice([0, 1])
                standings[home]['gf'] += gf_h
                standings[home]['ga'] += gf_a
                standings[away]['gf'] += gf_a
                standings[away]['ga'] += gf_h
            else:
                standings[away]['pts'] += 3
                gf_h = random.choice([0, 1])
                gf_a = random.choice([1, 2, 3, 4])
                standings[home]['gf'] += gf_h
                standings[home]['ga'] += gf_a
                standings[away]['gf'] += gf_a
                standings[away]['ga'] += gf_h

    for t in standings:
        standings[t]['gd'] = standings[t]['gf'] - standings[t]['ga']

    sorted_teams = sorted(standings.values(), key=lambda x: (x['pts'], x['gd'], x['gf'], random.random()), reverse=True)
    return sorted_teams

def allocate_leagues():
    all_teams = {**concacaf_elo, **uefa_elo}
    teams_to_allocate = {k: v for k, v in all_teams.items() if k != "Russia"}

    sorted_by_elo = sorted(teams_to_allocate.items(), key=lambda x: x[1], reverse=True)
    fifa_ranks = {team: rank for rank, (team, _) in enumerate(sorted_by_elo, start=1)}
    total_teams = len(fifa_ranks)

    nl_performance = {}
    historical_standing = {}

    for team in sorted(teams_to_allocate.keys()):
        elo = teams_to_allocate[team]
        base_perf = (elo - 600) / (2300 - 600)
        noise_nl = random.uniform(-0.15, 0.15)
        noise_hist = random.uniform(-0.10, 0.10)
        nl_performance[team] = max(0.0, min(1.0, base_perf + noise_nl))
        historical_standing[team] = max(0.0, min(1.0, base_perf + noise_hist))

    def calc_composite(team):
        rank = fifa_ranks[team]
        r_fifa = (total_teams - rank + 1) / total_teams
        p_nl = nl_performance[team]
        h_league = historical_standing[team]
        return (r_fifa * 0.60) + (p_nl * 0.30) + (h_league * 0.10)

    uefa_teams = [t for t in teams_to_allocate if t in uefa_elo]
    concacaf_teams = [t for t in teams_to_allocate if t in concacaf_elo]

    uefa_teams.sort(key=calc_composite, reverse=True)
    concacaf_teams.sort(key=calc_composite, reverse=True)

    # 95 Teams Total (54 UEFA, 41 CONCACAF)
    league_a = uefa_teams[:14] + concacaf_teams[:10]     # 24
    league_b = uefa_teams[14:28] + concacaf_teams[10:20] # 24
    league_c = uefa_teams[28:40] + concacaf_teams[20:32] # 24
    league_d = uefa_teams[40:] + concacaf_teams[32:]     # 23

    random.shuffle(league_a)
    random.shuffle(league_b)
    random.shuffle(league_c)
    random.shuffle(league_d)

    return league_a, league_b, league_c, league_d, teams_to_allocate

def draw_groups(league_teams, group_sizes, concacaf_set=CONCACAF_SET,
                min_concacaf=1, max_concacaf=2):
    """
    Draw groups from a league with a guaranteed balanced CONCACAF distribution.

    Rules:
      - Every group gets at least `min_concacaf` CONCACAF team(s).
      - No group gets more than `max_concacaf` CONCACAF teams.
      - Remaining slots are filled with UEFA teams.

    league_teams : list of team names in the league
    group_sizes  : list of group capacities, e.g. [4,4,4,4,4,4] or [4,4,4,4,4,3]
    """
    concacaf = [t for t in league_teams if t in concacaf_set]
    uefa = [t for t in league_teams if t not in concacaf_set]

    random.shuffle(concacaf)
    random.shuffle(uefa)

    num_groups = len(group_sizes)
    total_slots = sum(group_sizes)

    # --- Feasibility checks ---
    if len(concacaf) + len(uefa) != total_slots:
        raise ValueError("Team count does not match total group capacity.")
    if len(concacaf) < num_groups * min_concacaf:
        raise ValueError(
            f"Not enough CONCACAF teams ({len(concacaf)}) for "
            f"{num_groups} groups with min {min_concacaf}."
        )
    max_possible = sum(min(max_concacaf, size) for size in group_sizes)
    if len(concacaf) > max_possible:
        raise ValueError(
            f"Too many CONCACAF teams ({len(concacaf)}) for "
            f"{num_groups} groups with max {max_concacaf}."
        )

    groups = [[] for _ in group_sizes]
    capacities = list(group_sizes)
    concacaf_count = [0] * num_groups

    # --- Phase 1: seed each group with min_concacaf CONCACAF teams ---
    for _ in range(min_concacaf):
        for i in range(num_groups):
            team = concacaf.pop()
            groups[i].append(team)
            capacities[i] -= 1
            concacaf_count[i] += 1

    # --- Phase 2: distribute remaining CONCACAF teams, respecting max per group ---
    for team in concacaf:
        candidates = [
            i for i in range(num_groups)
            if concacaf_count[i] < max_concacaf and capacities[i] > 0
        ]
        i = random.choice(candidates)
        groups[i].append(team)
        capacities[i] -= 1
        concacaf_count[i] += 1

    # --- Phase 3: fill remaining slots with UEFA teams ---
    for team in uefa:
        candidates = [i for i in range(num_groups) if capacities[i] > 0]
        i = random.choice(candidates)
        groups[i].append(team)
        capacities[i] -= 1

    # Shuffle inside each group so display order is not fixed
    for g in groups:
        random.shuffle(g)

    return groups

def run_tournament(include_details=False):
    league_a, league_b, league_c, league_d, teams_to_allocate = allocate_leagues()
    league_details = {'A': [], 'B': [], 'C': [], 'D': []}

    # --- SIMULATE LEAGUE A ---
    groups_a = draw_groups(league_a, [4] * 6)
    groups_a_results = []
    for group in groups_a:
        standings = simulate_group({t: teams_to_allocate[t] for t in group})
        groups_a_results.append(standings)
        if include_details:
            league_details['A'].append(standings)

    winners_a_with_stats = [res[0] for res in groups_a_results]
    winners_a_with_stats.sort(key=lambda x: (x['pts'], x['gd'], x['gf'], random.random()), reverse=True)
    top_4_winners_names = [w['name'] for w in winners_a_with_stats[:4]]

    sf1_winner = top_4_winners_names[0] if simulate_knockout(teams_to_allocate[top_4_winners_names[0]], teams_to_allocate[top_4_winners_names[1]]) == 'A' else top_4_winners_names[1]
    sf2_winner = top_4_winners_names[2] if simulate_knockout(teams_to_allocate[top_4_winners_names[2]], teams_to_allocate[top_4_winners_names[3]]) == 'A' else top_4_winners_names[3]
    overall_winner = sf1_winner if simulate_knockout(teams_to_allocate[sf1_winner], teams_to_allocate[sf2_winner]) == 'A' else sf2_winner

    # --- SIMULATE LEAGUE B ---
    groups_b = draw_groups(league_b, [4] * 6)
    winners_b = []
    for group in groups_b:
        standings = simulate_group({t: teams_to_allocate[t] for t in group})
        winners_b.append(standings[0]['name'])
        if include_details:
            league_details['B'].append(standings)

    # --- SIMULATE LEAGUE C ---
    groups_c = draw_groups(league_c, [4] * 6)
    winners_c = []
    for group in groups_c:
        standings = simulate_group({t: teams_to_allocate[t] for t in group})
        winners_c.append(standings[0]['name'])
        if include_details:
            league_details['C'].append(standings)

    # --- SIMULATE LEAGUE D ---
    groups_d = draw_groups(league_d, [4, 4, 4, 4, 4, 3])
    winners_d = []
    for group in groups_d:
        standings = simulate_group({t: teams_to_allocate[t] for t in group})
        winners_d.append(standings[0]['name'])
        if include_details:
            league_details['D'].append(standings)

    if include_details:
        return overall_winner, winners_b, winners_c, winners_d, league_details
    return overall_winner, winners_b, winners_c, winners_d

def print_breakdown(league_details, overall_winner):
    print("\n" + "="*75)
    print("DETAILED TOURNAMENT BREAKDOWN (Single Simulation Example)")
    print("="*75)

    for league, groups in league_details.items():
        print(f"\n{'='*25} LEAGUE {league} ({len(groups)} Groups) {'='*25}")
        for i, group in enumerate(groups):
            print(f"\n  Group {i+1}:")
            print(f"  {'Team':<25} | {'Conf':<8} | {'Pts':>3} | {'GD':>4} | {'GF':>3} | {'GA':>3}")
            print(f"  {'-'*25}-+-{'-'*8}-+-{'-'*3}-+-{'-'*4}-+-{'-'*3}-+-{'-'*3}")
            for team in group:
                conf = 'CONCACAF' if team['name'] in CONCACAF_SET else 'UEFA'
                print(f"  {team['name']:<25} | {conf:<8} | {team['pts']:>3} | {team['gd']:>4} | {team['gf']:>3} | {team['ga']:>3}")

    print(f"\n{'='*75}")
    print(f">>> OVERALL CHAMPION: {overall_winner} <<<")
    print(f"{'='*75}\n")

# ==========================================
# 3. EXECUTE SIMULATIONS WITH TQDM
# ==========================================
def run_simulation(scenario_name, sims=10000):
    print(f"\n{'='*60}")
    print(f"SCENARIO: {scenario_name} ({sims} Simulations)")
    print(f"{'='*60}")
    print("Note: Russia is permanently excluded per the definitive regulatory protocol.")
    print("Note: Every group has 1 or 2 CONCACAF teams (balanced distribution).")

    overall_wins = defaultdict(int)
    league_wins = defaultdict(int)

    for _ in tqdm(range(sims), desc="Simulating Tournaments", unit="sim"):
        overall_winner, winners_b, winners_c, winners_d = run_tournament(include_details=False)

        overall_wins[overall_winner] += 1
        league_wins[overall_winner] += 1

        for w in winners_b: league_wins[w] += 1
        for w in winners_c: league_wins[w] += 1
        for w in winners_d: league_wins[w] += 1

    print(f"\n--- OVERALL CHAMPIONSHIP PROBABILITIES (Top 20) ---")
    overall_probs = [(team, (count / sims) * 100) for team, count in overall_wins.items()]
    overall_probs.sort(key=lambda x: x[1], reverse=True)

    for i, (team, prob) in enumerate(overall_probs[:20]):
        print(f"{i+1:2}. {team:<25} {prob:5.2f}%")

    print(f"\n--- CHANCE TO WIN THEIR RESPECTIVE LEAGUE/GROUP (Top 30) ---")
    league_probs = [(team, (count / sims) * 100) for team, count in league_wins.items()]
    league_probs.sort(key=lambda x: x[1], reverse=True)

    for i, (team, prob) in enumerate(league_probs[:30]):
        print(f"{i+1:2}. {team:<25} {prob:5.2f}%")

# ==========================================
# 3b. AVERAGED GROUP TABLES (DYNAMIC)
# ==========================================
def render_table(headers, rows, aligns):
    """Render an auto-sized ASCII table. Column widths adapt to the widest cell."""
    widths = [len(h) for h in headers]
    for row in rows:
        for i, cell in enumerate(row):
            widths[i] = max(widths[i], len(str(cell)))

    def fmt(cells):
        parts = []
        for cell, w, a in zip(cells, widths, aligns):
            s = str(cell)
            parts.append(s.rjust(w) if a == 'r' else s.ljust(w))
        return '  ' + ' | '.join(parts)

    lines = [fmt(headers), '  ' + '-+-'.join('-' * w for w in widths)]
    for row in rows:
        lines.append(fmt(row))
    return '\n'.join(lines)

def build_fixed_groups():
    """Allocate leagues ONCE and freeze the group composition for averaged tables."""
    league_a, league_b, league_c, league_d, teams_to_allocate = allocate_leagues()
    groups = {
        'A': draw_groups(league_a, [4] * 6),
        'B': draw_groups(league_b, [4] * 6),
        'C': draw_groups(league_c, [4] * 6),
        'D': draw_groups(league_d, [4, 4, 4, 4, 4, 3]),
    }
    return groups, teams_to_allocate

def run_averaged_simulations(groups, teams_to_allocate, sims=10000):
    """Run N tournaments on a FIXED bracket and accumulate per-team group statistics."""
    stats = {}
    for league in ('A', 'B', 'C', 'D'):
        for team in [t for g in groups[league] for t in g]:
            stats[team] = {
                'league': league,
                'pts': 0.0, 'gd': 0.0, 'gf': 0.0, 'ga': 0.0, 'pos': 0.0,
                'group_wins': 0, 'final_four': 0, 'titles': 0
            }

    def record(standings):
        for pos, row in enumerate(standings, start=1):
            s = stats[row['name']]
            s['pts'] += row['pts']
            s['gd'] += row['gd']
            s['gf'] += row['gf']
            s['ga'] += row['ga']
            s['pos'] += pos
        stats[standings[0]['name']]['group_wins'] += 1

    for _ in tqdm(range(sims), desc="Averaging Group Tables", unit="sim"):
        # Leagues B, C, D — group stage only
        for league in ('B', 'C', 'D'):
            for group in groups[league]:
                record(simulate_group({t: teams_to_allocate[t] for t in group}))

        # League A — group stage + final four
        winners_a = []
        for group in groups['A']:
            standings = simulate_group({t: teams_to_allocate[t] for t in group})
            record(standings)
            winners_a.append(standings[0])

        winners_a.sort(key=lambda x: (x['pts'], x['gd'], x['gf'], random.random()), reverse=True)
        top4 = [w['name'] for w in winners_a[:4]]
        for name in top4:
            stats[name]['final_four'] += 1

        sf1 = top4[0] if simulate_knockout(teams_to_allocate[top4[0]], teams_to_allocate[top4[1]]) == 'A' else top4[1]
        sf2 = top4[2] if simulate_knockout(teams_to_allocate[top4[2]], teams_to_allocate[top4[3]]) == 'A' else top4[3]
        champ = sf1 if simulate_knockout(teams_to_allocate[sf1], teams_to_allocate[sf2]) == 'A' else sf2
        stats[champ]['titles'] += 1

    return stats

def print_group_average_tables(groups, stats, sims=10000):
    print(f"\n{'#'*100}")
    print(f"#  AVERAGED GROUP TABLES  —  {sims:,} simulations on a frozen bracket")
    print(f"#  Each cell is the per-simulation average for that team in that group.")
    print(f"#  Every group contains 1 or 2 CONCACAF teams (balanced).")
    print(f"{'#'*100}")

    for league in ('A', 'B', 'C', 'D'):
        total_groups = len(groups[league])
        print(f"\n{'='*100}")
        print(f"  LEAGUE {league}  —  {total_groups} groups")
        print(f"{'='*100}")

        for gi, group in enumerate(groups[league], start=1):
            concacaf_in_group = sum(1 for t in group if t in CONCACAF_SET)
            entries = []
            for team in group:
                s = stats[team]
                entries.append({
                    'name': team,
                    'conf': 'CONCACAF' if team in CONCACAF_SET else 'UEFA',
                    'pts': s['pts'] / sims,
                    'gd': s['gd'] / sims,
                    'gf': s['gf'] / sims,
                    'ga': s['ga'] / sims,
                    'pos': s['pos'] / sims,
                    'win': s['group_wins'] / sims * 100.0,
                    'f4': s['final_four'] / sims * 100.0,
                    'title': s['titles'] / sims * 100.0,
                })

            entries.sort(key=lambda e: (e['pts'], e['gd'], e['gf']), reverse=True)

            if league == 'A':
                headers = ['Team', 'Conf', 'Avg Pts', 'Avg GD', 'Avg GF', 'Avg GA',
                           'Avg Pos', 'Win Group %', 'Final 4 %', 'Title %']
                aligns = ['l', 'l', 'r', 'r', 'r', 'r', 'r', 'r', 'r', 'r']
                rows = [[
                    e['name'], e['conf'], f"{e['pts']:.2f}", f"{e['gd']:+.2f}",
                    f"{e['gf']:.2f}", f"{e['ga']:.2f}", f"{e['pos']:.2f}",
                    f"{e['win']:.1f}", f"{e['f4']:.1f}", f"{e['title']:.2f}"
                ] for e in entries]
            else:
                headers = ['Team', 'Conf', 'Avg Pts', 'Avg GD', 'Avg GF', 'Avg GA',
                           'Avg Pos', 'Win Group %']
                aligns = ['l', 'l', 'r', 'r', 'r', 'r', 'r', 'r']
                rows = [[
                    e['name'], e['conf'], f"{e['pts']:.2f}", f"{e['gd']:+.2f}",
                    f"{e['gf']:.2f}", f"{e['ga']:.2f}", f"{e['pos']:.2f}",
                    f"{e['win']:.1f}"
                ] for e in entries]

            print(f"\n  League {league} — Group {gi}  "
                  f"({len(group)} teams, CONCACAF count: {concacaf_in_group})")
            print(render_table(headers, rows, aligns))

    print()

# ==========================================
# 4. MAIN EXECUTION BLOCK
# ==========================================
if __name__ == "__main__":
    TOTAL_SIMS = 10000

    print("Generating a single detailed simulation to display group and league breakdowns...")
    overall_winner, winners_b, winners_c, winners_d, details = run_tournament(include_details=True)
    print_breakdown(details, overall_winner)

    print(f"Freezing bracket and averaging group tables across {TOTAL_SIMS:,} simulations...")
    frozen_groups, frozen_teams = build_fixed_groups()
    group_stats = run_averaged_simulations(frozen_groups, frozen_teams, sims=TOTAL_SIMS)
    print_group_average_tables(frozen_groups, group_stats, sims=TOTAL_SIMS)

    print(f"Now running {TOTAL_SIMS:,} simulations for statistical probabilities...")
    run_simulation("RUSSIA PERMANENTLY BANNED (BALANCED 1–2 CONCACAF PER GROUP)", sims=TOTAL_SIMS)