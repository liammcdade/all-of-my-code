import random
import math
import html
from pathlib import Path
from collections import defaultdict
from itertools import combinations

import numpy as np
from tqdm import tqdm


# ====================== ELO RATINGS ======================
elo = {
    "West Ham United": 2228.80,
    "Middlesbrough": 2182.06,
    "Southampton": 2162.39,
    "Wolverhampton Wanderers": 2159.79,
    "Burnley": 2132.62,
    "Birmingham City": 2104.62,
    "Millwall": 2095.24,
    "Derby County": 2079.97,
    "Sheffield United": 2078.60,
    "Norwich City": 2072.70,
    "Watford": 2066.36,
    "Wrexham": 2062.50,
    "West Bromwich Albion": 2048.33,
    "Cardiff City": 2041.61,
    "Lincoln City": 2016.16,
    "Queens Park Rangers": 2015.12,
    "Swansea City": 2006.02,
    "Bolton Wanderers": 2004.82,
    "Blackburn Rovers": 2002.73,
    "Charlton Athletic": 2000.16,
    "Bristol City": 1998.98,
    "Portsmouth": 1993.43,
    "Stoke City": 1983.52,
    "Preston North End": 1973.06,
}

teams = list(elo.keys())
NUM_TEAMS = len(teams)
GAMES_PER_TEAM = NUM_TEAMS - 1
TOTAL_GAMES = NUM_TEAMS * GAMES_PER_TEAM
# ====================== FINISHED RESULTS ======================
finished_results = [
    ("Wolverhampton Wanderers", "Blackburn Rovers", 2, 2),
    ("Bolton Wanderers", "Preston North End", 2, 1),
    ("Bristol City", "Millwall", 0, 2),
    ("Charlton Athletic", "Derby County", 2, 1),
    ("Middlesbrough", "Lincoln City", 2, 1),
    ("Norwich City", "West Bromwich Albion", 1, 2),
    ("Portsmouth", "Queens Park Rangers", 1, 3),
    ("Stoke City", "Swansea City", 1, 2),
    ("Sheffield United", "Birmingham City", 0, 0),
    ("Southampton", "Watford", 0, 2),
    ("West Ham United", "Burnley", 2, 2),
    ("Cardiff City", "Wrexham", 1, 1),
    ("Birmingham City", "Bristol City", 1, 1),
    ("Lincoln City", "Portsmouth", 1, 3),
    ("Millwall", "Norwich City", 2, 0),



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
HOME_ADVANTAGE = 65
DRAW_BASE = 0.255
DRAW_WIDTH = 230

# ====================== STARTING POINTS ======================
STARTING_POINTS = {
    "Southampton": -4,
}

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

    home_xg = max(0.25, 1.45 + diff / 500)
    away_xg = max(0.25, 1.10 - diff / 550)

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


# ====================== PLAYOFF SIMULATION ======================
def games_played_per_team():
    return max(1, len(finished_results) * 2 // len(teams))


def simulate_goals_for_team(team_avg_gf, opponent_avg_ga, is_home=False):
    lambda_val = max(0, (team_avg_gf + opponent_avg_ga) / 2)
    if is_home:
        lambda_val *= 1.1
    return np.random.poisson(lambda_val)


def simulate_single_match(home_team, away_team, table):
    gp = games_played_per_team()
    home_avg_gf = table[home_team]["GF"] / gp
    home_avg_ga = table[home_team]["GA"] / gp
    away_avg_gf = table[away_team]["GF"] / gp
    away_avg_ga = table[away_team]["GA"] / gp

    home_goals = simulate_goals_for_team(home_avg_gf, away_avg_ga, is_home=True)
    away_goals = simulate_goals_for_team(away_avg_gf, home_avg_ga, is_home=False)

    if home_goals > away_goals:
        return home_team
    elif away_goals > home_goals:
        return away_team
    else:
        return np.random.choice([home_team, away_team])


def simulate_two_leg_tie(home_team, away_team, table):
    gp = games_played_per_team()
    home_avg_gf = table[home_team]["GF"] / gp
    home_avg_ga = table[home_team]["GA"] / gp
    away_avg_gf = table[away_team]["GF"] / gp
    away_avg_ga = table[away_team]["GA"] / gp

    leg1_home_goals = simulate_goals_for_team(home_avg_gf, away_avg_ga, is_home=True)
    leg1_away_goals = simulate_goals_for_team(away_avg_gf, home_avg_ga, is_home=False)
    leg2_home_goals = simulate_goals_for_team(away_avg_gf, home_avg_ga, is_home=True)
    leg2_away_goals = simulate_goals_for_team(home_avg_gf, away_avg_ga, is_home=False)

    home_agg = leg1_home_goals + leg2_away_goals
    away_agg = leg1_away_goals + leg2_home_goals

    if home_agg > away_agg:
        return home_team
    elif away_agg > home_agg:
        return away_team
    else:
        return np.random.choice([home_team, away_team])


# ====================== MONTE CARLO ======================
sims = 5000

auto_promotion = defaultdict(int)
playoff_qualify = defaultdict(int)
total_promotion = defaultdict(int)
releg = defaultdict(int)
avg_points = defaultdict(list)
promoted_trios = defaultdict(int)
relegated_trios = defaultdict(int)
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

        if pos <= 2:
            auto_promotion[team] += 1
            total_promotion[team] += 1
        if 3 <= pos <= 8:
            playoff_qualify[team] += 1
        if pos >= len(teams) - 2:
            releg[team] += 1

    # Eliminators: 5th vs 8th, 6th vs 7th — single leg
    elim1_winner = simulate_single_match(ranking[4][0], ranking[7][0], table)
    elim2_winner = simulate_single_match(ranking[5][0], ranking[6][0], table)

    # Semi-finals: eliminator winners face 3rd & 4th — two legs
    semi1_winner = simulate_two_leg_tie(ranking[2][0], elim1_winner, table)
    semi2_winner = simulate_two_leg_tie(ranking[3][0], elim2_winner, table)

    # Final — single leg
    winner = simulate_single_match(semi1_winner, semi2_winner, table)
    total_promotion[winner] += 1

    # Record promoted trio
    promoted = [ranking[0][0], ranking[1][0], winner]
    promoted_trios[frozenset(promoted)] += 1

    # Record relegated trio
    relegated = [
        ranking[len(teams) - 3][0],
        ranking[len(teams) - 2][0],
        ranking[len(teams) - 1][0],
    ]
    relegated_trios[frozenset(relegated)] += 1


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

# Most likely promoted trio
most_likely_trio = max(promoted_trios, key=lambda k: promoted_trios[k])
combined_percent = promoted_trios[most_likely_trio] / sims * 100
print(f"\nMost likely 3 teams to go up: {', '.join(sorted(most_likely_trio))}")
print(f"Combined percentage: {combined_percent:.2f}%")

# Most likely relegated trio
most_likely_relegated = max(relegated_trios, key=lambda k: relegated_trios[k])
relegated_percent = relegated_trios[most_likely_relegated] / sims * 100
print(f"\nMost likely 3 teams to go down: {', '.join(sorted(most_likely_relegated))}")
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
    auto_count = sum(position_counts[team].get(pos, 0) for pos in range(1, 3))
    playoff_count = sum(position_counts[team].get(pos, 0) for pos in range(3, 9))
    releg_count = sum(position_counts[team].get(pos, 0) for pos in range(len(teams) - 2, len(teams) + 1))

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
    <title>Championship Playoff Simulation — 2026/27</title>
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
        .highlight-row td {{ background: #fff9c4; }}
        .footer {{ margin-top: 30px; color: #666; font-size: 0.85em; }}
        .badge {{ display: inline-block; padding: 2px 8px; border-radius: 3px; font-size: 0.85em; }}
        .badge-promo {{ background: #c8e6c9; color: #2e7d32; }}
        .badge-releg {{ background: #ffcdd2; color: #c62828; }}
    </style>
</head>
<body>
<div class="container">
    <h1>EFL Championship Playoff Simulation</h1>
    <div class="meta">2026/27 season · {sims:,} simulations · {total_fixtures} fixtures per sim · {NUM_TEAMS} teams</div>

    <h2>Table 1: Final League Table &amp; Season Stats</h2>
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
        <p><strong>Playoff structure:</strong> Eliminators (5th vs 8th, 6th vs 7th — single leg) → Semi-finals vs 3rd &amp; 4th (two legs) → Final (single leg)</p>
        <p><strong>Most likely promoted trio:</strong> {', '.join(sorted(most_likely_trio))} ({combined_percent:.2f}%)</p>
        <p><strong>Most likely relegated trio:</strong> {', '.join(sorted(most_likely_relegated))} ({relegated_percent:.2f}%)</p>
    </div>
</div>
</body>
</html>"""

output_path = Path(__file__).parent / "championship_results.html"
output_path.write_text(html_doc, encoding="utf-8")
print(f"\nHTML report written to: {output_path}")
