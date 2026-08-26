import random
import math
import html
from pathlib import Path
from collections import defaultdict
from itertools import combinations

import numpy as np
from tqdm import tqdm


# ====================== ELO RATINGS (LEAGUE TWO) ======================
# Estimated ELOs based on recent performance, squad strength & promoted/relegated teams
elo = {
    "Newport County": 1545,
    "Rochdale": 1520,
    "Oldham Athletic": 1560,
    "Port Vale": 1535,
    "Accrington Stanley": 1510,
    "Colchester United": 1505,
    "Barnet": 1555,
    "Salford City": 1570,
    "Cheltenham Town": 1540,
    "Rotherham United": 1580,
    "Chesterfield": 1565,
    "Fleetwood Town": 1575,
    "Crawley Town": 1550,
    "Crewe Alexandra": 1560,
    "Gillingham": 1530,
    "Walsall": 1585,
    "Grimsby Town": 1525,
    "Exeter City": 1545,
    "Northampton Town": 1555,
    "Swindon Town": 1540,
    "Tranmere Rovers": 1535,
    "Shrewsbury Town": 1550,
    "York City": 1530,
    "Bristol Rovers": 1565,
}

teams = list(elo.keys())
NUM_TEAMS = len(teams)  # 24
GAMES_PER_TEAM = NUM_TEAMS - 1
TOTAL_GAMES = NUM_TEAMS * GAMES_PER_TEAM

# ====================== FINISHED RESULTS ======================
# Results from Matchday 1 (Sat 15 Aug) as provided
finished_results = [
    ("Newport County", "Rochdale", 3, 0),
    ("Oldham Athletic", "Port Vale", 2, 0),
    ("Accrington Stanley", "Colchester United", 2, 2),
    ("Barnet", "Salford City", 3, 1),
    ("Cheltenham Town", "Rotherham United", 2, 1),
    ("Chesterfield", "Fleetwood Town", 0, 1),
    ("Crawley Town", "Crewe Alexandra", 0, 1),
    ("Gillingham", "Walsall", 0, 3),
    ("Grimsby Town", "Exeter City", 1, 0),
    ("Northampton Town", "Swindon Town", 0, 0),
    ("Tranmere Rovers", "Shrewsbury Town", 2, 0),
    ("York City", "Bristol Rovers", 3, 2),
    ("Bristol Rovers", "Newport County", 4, 2),
    ("Salford City", "Chesterfield", 0, 1),
    ("Walsall", "Grimsby Town", 0, 0),
]

# ====================== AUTO-GENERATE REMAINING FIXTURES ======================
all_fixtures = set()
for home, away in combinations(teams, 2):
    all_fixtures.add((home, away))
    all_fixtures.add((away, home))

finished_pairs = {(h, a) for h, a, _, _ in finished_results}

remaining_fixtures = [
    (home, away)
    for home, away in sorted(all_fixtures)
    if (home, away) not in finished_pairs
]

# ====================== MODEL PARAMETERS ======================
HOME_ADVANTAGE = 55       # Lower than League One/Championship
DRAW_BASE = 0.27          # League Two is historically more draw-prone
DRAW_WIDTH = 210

# ====================== STARTING POINTS ======================
# No points deductions currently active
STARTING_POINTS = {}

# ====================== APPLY RESULT ======================
def apply_result(table, home, away, hg, ag):
    table[home]["GF"] += hg
    table[home]["GA"] += ag
    table[away]["GF"] += ag
    table[away]["GA"] += hg

    if hg > ag:
        table[home]["Pts"] += 3
    elif ag > hg:
        table[away]["Pts"] += 3
    else:
        table[home]["Pts"] += 1
        table[away]["Pts"] += 1


# ====================== BUILD STARTING TABLE ======================
def build_starting_table():
    table = {t: {"Pts": STARTING_POINTS.get(t, 0), "GF": 0, "GA": 0} for t in teams}
    for home, away, hg, ag in finished_results:
        apply_result(table, home, away, hg, ag)
    return table


# ====================== MATCH ENGINE ======================
def simulate_match(home, away):
    diff = elo[home] - elo[away] + HOME_ADVANTAGE

    p_home_base = 1 / (1 + 10 ** (-diff / 400))
    p_draw = DRAW_BASE * math.exp(-(diff**2) / (2 * DRAW_WIDTH**2))

    p_home = p_home_base * (1 - p_draw)
    p_away = (1 - p_home_base) * (1 - p_draw)

    r = random.random()

    home_xg = max(0.25, 1.35 + diff / 500)
    away_xg = max(0.25, 1.00 - diff / 550)

    if r < p_home:
        return _sample_win(home_xg, away_xg, home_wins=True)
    elif r < p_home + p_draw:
        g = np.random.poisson((home_xg + away_xg) / 2)
        return g, g
    else:
        return _sample_win(home_xg, away_xg, home_wins=False)


def _sample_win(home_xg, away_xg, home_wins):
    while True:
        hg = np.random.poisson(home_xg)
        ag = np.random.poisson(away_xg)
        if home_wins and hg > ag:
            return hg, ag
        if not home_wins and ag > hg:
            return hg, ag


# ====================== PLAYOFF SIMULATION (LEAGUE TWO FORMAT) ======================
def games_played_per_team():
    return max(1, len(finished_results) * 2 // len(teams))


def simulate_goals_for_team(team_avg_gf, opponent_avg_ga, is_home=False):
    lambda_val = max(0, (team_avg_gf + opponent_avg_ga) / 2)
    if is_home:
        lambda_val *= 1.1
    return np.random.poisson(lambda_val)


def simulate_single_match(home_team, away_team, table):
    """Used for neutral venue Final"""
    gp = games_played_per_team()
    home_avg_gf = table[home_team]["GF"] / gp
    home_avg_ga = table[home_team]["GA"] / gp
    away_avg_gf = table[away_team]["GF"] / gp
    away_avg_ga = table[away_team]["GA"] / gp

    # Neutral venue - no home advantage multiplier
    home_goals = simulate_goals_for_team(home_avg_gf, away_avg_ga, is_home=False)
    away_goals = simulate_goals_for_team(away_avg_gf, home_avg_ga, is_home=False)

    if home_goals > away_goals:
        return home_team
    elif away_goals > home_goals:
        return away_team
    else:
        return np.random.choice([home_team, away_team])


def simulate_two_leg_tie(higher_seed, lower_seed, table):
    """Standard League Two Semi-Final: Higher seed gets 2nd leg at home"""
    gp = games_played_per_team()

    h_gf = table[higher_seed]["GF"] / gp
    h_ga = table[higher_seed]["GA"] / gp
    l_gf = table[lower_seed]["GF"] / gp
    l_ga = table[lower_seed]["GA"] / gp

    # Leg 1: Lower seed at home
    leg1_h_goals = simulate_goals_for_team(l_gf, h_ga, is_home=True)
    leg1_a_goals = simulate_goals_for_team(h_gf, l_ga, is_home=False)

    # Leg 2: Higher seed at home
    leg2_h_goals = simulate_goals_for_team(h_gf, l_ga, is_home=True)
    leg2_a_goals = simulate_goals_for_team(l_gf, h_ga, is_home=False)

    higher_agg = leg1_a_goals + leg2_h_goals
    lower_agg = leg1_h_goals + leg2_a_goals

    if higher_agg > lower_agg:
        return higher_seed
    elif lower_agg > higher_agg:
        return lower_seed
    else:
        # Tied aggregate: random choice (could add penalties logic)
        return np.random.choice([higher_seed, lower_seed])


# ====================== MONTE CARLO ======================
sims = 5000

auto_promotion = defaultdict(int)
playoff_qualify = defaultdict(int)
total_promotion = defaultdict(int)
releg = defaultdict(int)
avg_points = defaultdict(list)
promoted_quartets = defaultdict(int)   # League Two promotes 4 teams total
relegated_pairs = defaultdict(int)     # League Two relegates 2 teams
position_counts = defaultdict(lambda: defaultdict(int))

stats_tracking = {t: {"W": 0, "D": 0, "L": 0, "GD": 0} for t in teams}

total_fixtures = len(finished_results) + len(remaining_fixtures)
print(f"Running {sims:,} simulations...")
print(f"  Finished games: {len(finished_results)}")
print(f"  Remaining fixtures to simulate: {len(remaining_fixtures)}")
print(f"  Total fixtures per sim: {total_fixtures}")


def _track_stats(stats, team, gf, ga):
    diff = gf - ga
    if diff > 0:
        stats[team]["W"] += 1
    elif diff < 0:
        stats[team]["L"] += 1
    else:
        stats[team]["D"] += 1
    stats[team]["GD"] += diff


for _ in tqdm(range(sims), desc="Simulating", unit="sim"):
    table = build_starting_table()

    for home, away in remaining_fixtures:
        hg, ag = simulate_match(home, away)
        apply_result(table, home, away, hg, ag)
        _track_stats(stats_tracking, home, hg, ag)
        _track_stats(stats_tracking, away, ag, hg)

    ranking = sorted(
        table.items(),
        key=lambda x: (
            x[1]["Pts"],
            x[1]["GF"] - x[1]["GA"],
            x[1]["GF"],
        ),
        reverse=True,
    )

    for pos, (team, data) in enumerate(ranking, 1):
        avg_points[team].append(data["Pts"])
        position_counts[team][pos] += 1

        # LEAGUE TWO: Top 3 Auto, 4-7 Playoffs, Bottom 2 Relegated
        if pos <= 3:
            auto_promotion[team] += 1
            total_promotion[team] += 1
        if 4 <= pos <= 7:
            playoff_qualify[team] += 1
        if pos >= NUM_TEAMS - 1:  # Positions 23, 24
            releg[team] += 1

    # LEAGUE TWO PLAYOFFS
    # Semi-Finals: 4th vs 7th, 5th vs 6th (Two Legs)
    semi1_winner = simulate_two_leg_tie(ranking[3][0], ranking[6][0], table)
    semi2_winner = simulate_two_leg_tie(ranking[4][0], ranking[5][0], table)

    # Final: Single Leg at Neutral Venue
    winner = simulate_single_match(semi1_winner, semi2_winner, table)
    total_promotion[winner] += 1

    # Record promoted quartet (3 auto + 1 playoff winner)
    promoted = [ranking[0][0], ranking[1][0], ranking[2][0], winner]
    promoted_quartets[frozenset(promoted)] += 1

    # Record relegated pair (Bottom 2)
    relegated = [ranking[NUM_TEAMS - 2][0], ranking[NUM_TEAMS - 1][0]]
    relegated_pairs[frozenset(relegated)] += 1


# ====================== OUTPUT ======================
teams_sorted = sorted(teams, key=lambda x: sum(avg_points[x]) / sims, reverse=True)

print(f"\n{'Team':<25}{'AvgPts':<10}{'W':>5}{'D':>5}{'L':>5}{'GD':>8}  {'Auto Promo%':<12}{'Playoff%':<10}{'Promo%':<8}{'Releg%'}")
print("-" * 104)

for team in teams_sorted:
    s = stats_tracking[team]
    auto = auto_promotion[team] / sims * 100
    po = playoff_qualify[team] / sims * 100
    total_promo = total_promotion[team] / sims * 100
    rel = releg[team] / sims * 100
    print(
        f"{team:<25}"
        f"{sum(avg_points[team]) / sims:<10.2f}"
        f"{s['W'] / sims:>5.3f}"
        f"{s['D'] / sims:>5.3f}"
        f"{s['L'] / sims:>5.3f}"
        f"{s['GD'] / sims:>8.3f}  "
        f"{auto:<10.2f}"
        f"{po:<10.2f}"
        f"{total_promo:<8.2f}"
        f"{rel:.2f}"
    )

# Most likely promoted quartet
most_likely_quartet = max(promoted_quartets, key=lambda k: promoted_quartets[k])
combined_percent = promoted_quartets[most_likely_quartet] / sims * 100
print(f"\nMost likely 4 teams to go up: {', '.join(sorted(most_likely_quartet))}")
print(f"Combined percentage: {combined_percent:.2f}%")

# Most likely relegated pair
most_likely_relegated = max(relegated_pairs, key=lambda k: relegated_pairs[k])
relegated_percent = relegated_pairs[most_likely_relegated] / sims * 100
print(f"\nMost likely 2 teams to go down: {', '.join(sorted(most_likely_relegated))}")
print(f"Combined percentage: {relegated_percent:.2f}%")


# ====================== MOST LIKELY POSITIONS & SOLVED % ======================
print("\n" + "=" * 80)
print("MOST LIKELY FINISHING POSITIONS")
print("=" * 80)

team_solved = []

for team, pos_counts in position_counts.items():
    most_likely_pos = max(pos_counts.items(), key=lambda x: x[1])[0]
    pct = pos_counts[most_likely_pos] / sims * 100
    team_solved.append((team, most_likely_pos, pct))

team_solved.sort(key=lambda x: x[2], reverse=True)

for team, pos, pct in team_solved:
    print(f"{team:<25} Most likely: {pos}th ({pct:.2f}%)")

combined_solved = 1.0
for _, _, pct in team_solved:
    combined_solved *= (pct / 100.0)

print(f"\nCombined table solved %: {combined_solved * 100:.20e}%")

combined_auto = {team: auto_promotion[team] / sims * 100 for team in teams}
combined_playoff = {team: playoff_qualify[team] / sims * 100 for team in teams}
combined_releg = {team: releg[team] / sims * 100 for team in teams}

stats_solved = {}

for team in teams:
    auto_count = sum(position_counts[team].get(pos, 0) for pos in range(1, 4))
    playoff_count = sum(position_counts[team].get(pos, 0) for pos in range(4, 8))
    releg_count = sum(position_counts[team].get(pos, 0) for pos in range(NUM_TEAMS - 1, NUM_TEAMS + 1))

    if auto_count > 0:
        stats_solved.setdefault("AutoPromo", []).append(combined_auto[team] / 100.0)

    if playoff_count > 0:
        stats_solved.setdefault("Playoff", []).append(combined_playoff[team] / 100.0)

    if releg_count > 0:
        stats_solved.setdefault("Releg", []).append(combined_releg[team] / 100.0)

print("\nCombined stats solved %:")
for stat_name, probs in stats_solved.items():
    solved = 1.0
    for p in probs:
        solved *= p
    print(f"  {stat_name}: {solved * 100:.20e}%")


# ====================== HTML OUTPUT ======================
def _row(rank, team):
    s = stats_tracking[team]
    auto = auto_promotion[team] / sims * 100
    po = playoff_qualify[team] / sims * 100
    total_promo = total_promotion[team] / sims * 100
    rel = releg[team] / sims * 100
    return f"""        <tr>
            <td>{rank}</td>
            <td>{html.escape(team)}</td>
            <td>{sum(avg_points[team]) / sims:.2f}</td>
            <td>{s['W'] / sims:.3f}</td>
            <td>{s['D'] / sims:.3f}</td>
            <td>{s['L'] / sims:.3f}</td>
            <td>{s['GD'] / sims:+.3f}</td>
            
            <td>{auto:.2f}%</td>
            <td>{po:.2f}%</td>
            <td>{total_promo:.2f}%</td>
            <td>{rel:.2f}%</td>
        </tr>"""


table_rows = "\n".join(_row(i, t) for i, t in enumerate(teams_sorted, 1))

html_doc = f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>League Two Playoff Simulation — 2026/27</title>
    <style>
        body {{ font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif; margin: 0; padding: 20px; background: #f0f2f5; color: #333; }}
        .container {{ max-width: 1100px; margin: 0 auto; }}
        h1 {{ color: #1a1a2e; margin-bottom: 5px; }}
        h2 {{ color: #16213e; margin-top: 30px; }}
        .meta {{ color: #666; font-size: 0.9em; margin-bottom: 20px; }}
        table {{ border-collapse: collapse; width: 100%; margin: 15px 0; background: white; box-shadow: 0 1px 3px rgba(0,0,0,0.1); }}
        th, td {{ border: 1px solid #e0e0e0; padding: 8px 12px; text-align: left; }}
        th {{ background: #16213e; color: white; }}
        tr:nth-child(even) {{ background: #f8f9fa; }}
        tr:hover {{ background: #e8f0fe; }}
        .footer {{ margin-top: 30px; color: #666; font-size: 0.85em; }}
    </style>
</head>
<body>
<div class="container">
    <h1>EFL League Two Playoff Simulation</h1>
    <div class="meta">2026/27 season · {sims:,} simulations · {total_fixtures} fixtures per sim · {NUM_TEAMS} teams</div>

    <h2>Final League Table &amp; Season Stats</h2>
    <table>
        <thead>
            <tr>
                <th>Pos</th>
                <th>Team</th>
                <th>AvgPts</th>
                <th>Wins</th>
                <th>Draws</th>
                <th>Losses</th>
                <th>GD</th>
                <th>Auto Promo%</th>
                <th>Playoff%</th>
                <th>Total Promo%</th>
                <th>Releg%</th>
            </tr>
        </thead>
        <tbody>
{table_rows}
        </tbody>
    </table>

    <div class="footer">
        <p><strong>Playoff structure:</strong> Semi-finals (4th vs 7th, 5th vs 6th — two legs) → Final (single leg, neutral venue)</p>
        <p><strong>Most likely promoted quartet:</strong> {', '.join(sorted(most_likely_quartet))} ({combined_percent:.2f}%)</p>
        <p><strong>Most likely relegated pair:</strong> {', '.join(sorted(most_likely_relegated))} ({relegated_percent:.2f}%)</p>
    </div>
</div>
</body>
</html>"""

output_path = Path(__file__).parent / "league_two_results.html"
output_path.write_text(html_doc, encoding="utf-8")
print(f"\nHTML report written to: {output_path}")