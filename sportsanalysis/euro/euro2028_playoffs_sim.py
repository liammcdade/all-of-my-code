import random
from collections import defaultdict
import math

# -------------------------------------------------------------
# 1. INPUT DATA
# -------------------------------------------------------------

# UEFA Euro 2028 Qualifying Playoffs - Paths with teams and approximate FIFA rankings (as of late 2024)
euro_paths = {
    'A': {'Italy': 1900 - 10, 'Northern Ireland': 1900 - 50, 'Wales': 1900 - 30, 'Bosnia and Herzegovina': 1900 - 75},
    'B': {'Ukraine': 1900 - 25, 'Sweden': 1900 - 20, 'Poland': 1900 - 35, 'Albania': 1900 - 65},
    'C': {'Turkey': 1900 - 45, 'Romania': 1900 - 50, 'Slovakia': 1900 - 55, 'Kosovo': 1900 - 105},
    'D': {'Denmark': 1900 - 15, 'North Macedonia': 1900 - 70, 'Czech Republic': 1900 - 40, 'Republic of Ireland': 1900 - 55}
}

fifa_ranking = {}
for path in euro_paths.values():
    fifa_ranking.update(path)

teams = list(fifa_ranking.keys())

# -------------------------------------------------------------
# 2. MATCH SIMULATION MODEL
# -------------------------------------------------------------

def match_prob(teamA, teamB):
    """
    Convert FIFA ranking points into expected win/draw/loss probabilities.
    Simple logistic Elo-style model.
    """
    A = fifa_ranking[teamA]
    B = fifa_ranking[teamB]

    rating_diff = A - B
    winA = 1 / (1 + math.exp(-rating_diff / 400))
    winB = 1 - winA
    draw = 0.22  # constant draw chance
    winA *= (1-draw)
    winB *= (1-draw)
    return winA, draw, winB


def simulate_match(teamA, teamB):
    winA, draw, winB = match_prob(teamA, teamB)
    r = random.random()
    if r < winA:
        return teamA
    elif r < winA + draw:
        return "DRAW"
    else:
        return teamB

# -------------------------------------------------------------
# 3. PLAYOFF SIMULATION
# -------------------------------------------------------------

def simulate_euro_path(path_teams):
    teams = list(path_teams.keys())
    # Semi-finals: 0 vs 1, 2 vs 3
    semi1 = simulate_match(teams[0], teams[1])
    while semi1 == "DRAW":
        semi1 = simulate_match(teams[0], teams[1])
    semi2 = simulate_match(teams[2], teams[3])
    while semi2 == "DRAW":
        semi2 = simulate_match(teams[2], teams[3])
    # Final
    final = simulate_match(semi1, semi2)
    while final == "DRAW":
        final = simulate_match(semi1, semi2)
    return final

# -------------------------------------------------------------
# 4. FULL SIMULATION
# -------------------------------------------------------------

win_counter = defaultdict(int)
total_simulations = 10000  # Number of simulations

for _ in range(total_simulations):
    qualifiers = []
    for path in euro_paths.values():
        winner = simulate_euro_path(path)
        qualifiers.append(winner)
        win_counter[winner] += 1

# -------------------------------------------------------------
# 5. OUTPUT QUALIFICATION PROBABILITIES
# -------------------------------------------------------------

print("UEFA EURO 2028 QUALIFYING PLAYOFFS SIMULATION RESULTS")
print(f"Total simulations: {total_simulations}")
print("\nQUALIFICATION PROBABILITIES:")
for team in sorted(fifa_ranking.keys()):
    pct = 100 * win_counter[team] / total_simulations
    print(f"{team}: {pct:.2f}%")

print("\nPATH WINNERS SUMMARY:")
for path_name, path_teams in euro_paths.items():
    print(f"\nPath {path_name}:")
    for team in path_teams.keys():
        pct = 100 * win_counter[team] / total_simulations
        print(f"  {team}: {pct:.2f}%")