import random
import math
import numpy as np
from collections import defaultdict
from tqdm import tqdm



# ====================== ELO RATINGS ======================
elo = {
    "Coventry": 1643,
    "Ipswich": 1633,
    "Southampton": 1609,
    "Middlesbrough": 1581,
    "Millwall": 1579,
    "Norwich": 1556,
    "Derby": 1541,
    "Sheff Utd": 1540,
    "Hull City": 1537,
    "Wrexham": 1522,
    "Swansea": 1509,
    "Bristol City": 1506,
    "QPR": 1506,
    "Watford": 1505,
    "Leicester": 1502,
    "Stoke": 1487,
    "Blackburn": 1483,
    "West Brom": 1481,
    "Preston": 1481,
    "Birmingham": 1471,
    "Charlton": 1461,
    "Oxford": 1455,
    "Portsmouth": 1453,
    "Sheff Wed": 1324,
}

# ====================== CURRENT TABLE ======================
current = {
    "Coventry": {"Pts":89,"GF":90,"GA":44},
    "Ipswich": {"Pts":76,"GF":73,"GA":44},
    "Millwall": {"Pts":79,"GF":61,"GA":48},
    "Middlesbrough": {"Pts":73,"GF":64,"GA":44},
    "Southampton": {"Pts":76,"GF":77,"GA":53},
    "Hull City": {"Pts":70,"GF":67,"GA":63},
    "Wrexham": {"Pts":70,"GF":66,"GA":60},
    "Derby": {"Pts":66,"GF":63,"GA":55},
    "Norwich": {"Pts":64,"GF":61,"GA":53},
    "Bristol City": {"Pts":59,"GF":56,"GA":57},
    "QPR": {"Pts":58,"GF":59,"GA":67},
    "Watford": {"Pts":57,"GF":52,"GA":56},
    "Preston": {"Pts":57,"GF":50,"GA":55},
    "Swansea": {"Pts":60,"GF":53,"GA":57},
    "Birmingham": {"Pts":57,"GF":52,"GA":53},
    "Stoke": {"Pts":55,"GF":50,"GA":51},
    "Sheff Utd": {"Pts":57,"GF":61,"GA":59},
    "Charlton": {"Pts":50,"GF":40,"GA":52},
    "Blackburn": {"Pts":49,"GF":39,"GA":54},
    "West Brom": {"Pts":52,"GF":47,"GA":56},
    "Portsmouth": {"Pts":51,"GF":45,"GA":62},
    "Oxford": {"Pts":44,"GF":41,"GA":56},
    "Leicester": {"Pts":42,"GF":56,"GA":67},
    "Sheff Wed": {"Pts":-3,"GF":26,"GA":83},
}

# ====================== REMAINING FIXTURES ======================
fixtures = [
    ("Birmingham", "Preston"),
    ("Charlton", "Ipswich"),
    ("Middlesbrough", "Sheff Wed"),
    ("Sheff Utd", "Blackburn"),
    ("Leicester", "Millwall"),
    ("Charlton", "Hull City"),
    ("Middlesbrough", "Watford"),
    ("West Brom", "Ipswich"),
    ("Birmingham", "Bristol City"),
    ("Norwich", "Swansea"),
    ("Oxford", "Sheff Wed"),
    ("QPR", "Derby"),
    ("Sheff Utd", "Preston"),
    ("Stoke", "Portsmouth"),
    ("Coventry", "Wrexham"),
    ("Blackburn", "Leicester"),
    ("Bristol City", "Stoke"),
    ("Derby", "Sheff Utd"),
    ("Hull City", "Norwich"),
    ("Ipswich", "QPR"),
    ("Millwall", "Oxford"),
    ("Portsmouth", "Birmingham"),
    ("Preston", "Southampton"),
    ("Sheff Wed", "West Brom"),
    ("Swansea", "Charlton"),
    ("Watford", "Coventry"),
    ("Wrexham", "Middlesbrough"),
    ("Southampton", "Ipswich"),
]

# ====================== MODEL PARAMETERS ======================
HOME_ADVANTAGE = 65
DRAW_BASE = 0.255
DRAW_WIDTH = 230

# ====================== MATCH ENGINE ======================
def simulate_match(home, away):
    diff = elo[home] - elo[away] + HOME_ADVANTAGE

    p_home_base = 1 / (1 + 10 ** (-diff / 400))
    p_draw = DRAW_BASE * math.exp(-(diff**2)/(2 * DRAW_WIDTH**2))

    p_home = p_home_base * (1 - p_draw)
    p_away = (1 - p_home_base) * (1 - p_draw)

    r = random.random()

    home_xg = max(0.25, 1.45 + diff / 500)
    away_xg = max(0.25, 1.10 - diff / 550)

    if r < p_home:
        while True:
            hg = np.random.poisson(home_xg)
            ag = np.random.poisson(away_xg)
            if hg > ag:
                return hg, ag

    elif r < p_home + p_draw:
        g = np.random.poisson((home_xg + away_xg) / 2)
        return g, g

    else:
        while True:
            hg = np.random.poisson(home_xg)
            ag = np.random.poisson(away_xg)
            if ag > hg:
                return hg, ag

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

# ====================== SIMULATE PLAYOFFS ======================
def simulate_goals_for_team(team_avg_gf, opponent_avg_ga, is_home=False):
    lambda_val = max(0, (team_avg_gf + opponent_avg_ga) / 2)
    if is_home:
        lambda_val *= (1 + 0.1)
    return np.random.poisson(lambda_val)

def simulate_two_leg_tie(home_team, away_team, table):
    home_avg_gf = table[home_team]["GF"] / 46  # approx
    home_avg_ga = table[home_team]["GA"] / 46
    away_avg_gf = table[away_team]["GF"] / 46
    away_avg_ga = table[away_team]["GA"] / 46

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
sims = 10000

auto_promotion = defaultdict(int)
playoff_qualify = defaultdict(int)
total_promotion = defaultdict(int)
releg = defaultdict(int)
avg_points = defaultdict(list)
promoted_trios = defaultdict(int)
relegated_trios = defaultdict(int)

print(f"Running {sims:,} simulations...")

for _ in tqdm(range(sims), desc="Simulating", unit="sim"):

    table = {
        t: {"Pts": current[t]["Pts"], "GF": current[t]["GF"], "GA": current[t]["GA"]}
        for t in current
    }

    for home, away in fixtures:
        hg, ag = simulate_match(home, away)
        apply_result(table, home, away, hg, ag)

    ranking = sorted(
        table.items(),
        key=lambda x: (
            x[1]["Pts"],
            x[1]["GF"] - x[1]["GA"],
            x[1]["GF"]
        ),
        reverse=True
    )

    for pos, (team, data) in enumerate(ranking, 1):
        avg_points[team].append(data["Pts"])

        if pos <= 2:
            auto_promotion[team] += 1
            total_promotion[team] += 1
        if 3 <= pos <= 6:
            playoff_qualify[team] += 1
        if pos >= 22:
            releg[team] += 1

    # Simulate playoffs for teams 3-6
    playoff_teams = [team for team, _ in ranking[2:6]]
    semi1 = (playoff_teams[0], playoff_teams[3])  # 3rd vs 6th
    semi2 = (playoff_teams[1], playoff_teams[2])  # 4th vs 5th

    semi_winners = []
    for home, away in [semi1, semi2]:
        winner = simulate_two_leg_tie(home, away, table)
        semi_winners.append(winner)

    # Final
    final_team1, final_team2 = semi_winners
    team1_avg_gf = table[final_team1]["GF"] / 46  # approx
    team1_avg_ga = table[final_team1]["GA"] / 46
    team2_avg_gf = table[final_team2]["GF"] / 46
    team2_avg_ga = table[final_team2]["GA"] / 46

    team1_goals = simulate_goals_for_team(team1_avg_gf, team2_avg_ga)
    team2_goals = simulate_goals_for_team(team2_avg_gf, team1_avg_ga)

    if team1_goals > team2_goals:
        winner = final_team1
        total_promotion[final_team1] += 1
    elif team2_goals > team1_goals:
        winner = final_team2
        total_promotion[final_team2] += 1
    else:
        # Draw: random winner
        winner = np.random.choice([final_team1, final_team2])
        total_promotion[winner] += 1

    # Record promoted trio
    promoted = [ranking[0][0], ranking[1][0], winner]
    promoted_trios[frozenset(promoted)] += 1

    # Record relegated trio
    relegated = [ranking[21][0], ranking[22][0], ranking[23][0]]
    relegated_trios[frozenset(relegated)] += 1

# ====================== OUTPUT ======================
print(f"{'Team':<15}{'AvgPts':<8}{'Auto Promo%':<12}{'Playoff%':<10}{'Promo%':<8}{'Releg%'}")
print("-" * 70)

for team in sorted(current.keys(), key=lambda x: sum(avg_points[x]) / sims, reverse=True):
    auto = auto_promotion[team] / sims * 100
    po = playoff_qualify[team] / sims * 100
    total_promo = total_promotion[team] / sims * 100
    rel = releg[team] / sims * 100
    print(
        f"{team:<15}"
        f"{sum(avg_points[team])/sims:<8.2f}"
        f"{auto:<12.2f}"
        f"{po:<10.2f}"
        f"{total_promo:<8.2f}"
        f"{rel:.2f}"
    )

# Most likely promoted trio
most_likely_trio = max(promoted_trios.keys(), key=lambda k: promoted_trios[k])
combined_percent = promoted_trios[most_likely_trio] / sims * 100
print(f"\nMost likely 3 teams to go up: {', '.join(sorted(most_likely_trio))}")
print(f"Combined percentage: {combined_percent:.2f}%")

# Most likely relegated trio
most_likely_relegated = max(relegated_trios.keys(), key=lambda k: relegated_trios[k])
relegated_percent = relegated_trios[most_likely_relegated] / sims * 100
print(f"\nMost likely 3 teams to go down: {', '.join(sorted(most_likely_relegated))}")
print(f"Combined percentage: {relegated_percent:.2f}%")
