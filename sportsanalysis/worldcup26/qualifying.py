import random
import math
from collections import defaultdict

# =========================
# CONFIGURATION - EASILY EDITABLE
# =========================

# Teams to track for the summary table
TRACKED_TEAMS = []

# UEFA path finals (March 31)
UEFA_FINALS = [
    ("Italy", "Bosnia and Herzegovina"),        # Path A - Group B
    ("Sweden", "Poland"),                        # Path B - Group F
    ("Kosovo", "Turkey"),                        # Path C - Group D
    ("Czech Republic", "Denmark"),               # Path D - Group A
]

# Intercontinental path finals (March 31)
INTERCONTINENTAL_FINALS = [
    ("DR Congo", "Jamaica"),    # Path 1
    ("Iraq", "Bolivia"),        # Path 2
]

# Number of simulations
NUM_SIMULATIONS = 5000

# =========================
# ELO RATINGS (adjust if wanted)
# =========================
elo = {
    # UEFA finalists
    "Italy": 1817.76,
    "Bosnia and Herzegovina": 1605.79,

    "Ukraine": 1766.95,
    "Sweden": 1699.42,
    "Poland": 1738.70,
    "Albania": 1660.52,

    "Turkey": 1803.71,
    "Kosovo": 1685.16,

    "Denmark": 1822.66,
    "Czech Republic": 1721.53,

    # Intercontinental finalists
    "DR Congo": 1682.99,
    "Jamaica": 1614.12,

    "Iraq": 1646.65,
    "Bolivia": 1658.75,
}

# =========================
# ELO MATCH FUNCTION
# =========================
def match(team1, team2, home_adv=50):
    e1 = elo[team1] + home_adv
    e2 = elo[team2]

    p1 = 1 / (1 + 10 ** ((e2 - e1) / 400))

    r = random.random()

    if r < p1:
        return team1
    else:
        return team2

# =========================
# SIMULATIONS
# =========================
results = defaultdict(int)

for _ in range(NUM_SIMULATIONS):

    qualifiers = []

    # UEFA finals
    for home, away in UEFA_FINALS:
        winner = match(home, away)
        qualifiers.append(winner)

    # Intercontinental finals
    for home, away in INTERCONTINENTAL_FINALS:
        winner = match(home, away)
        qualifiers.append(winner)

    # Count results
    for team in qualifiers:
        results[team] += 1

# =========================
# OUTPUT
# =========================
sorted_results = sorted(results.items(), key=lambda x: x[1], reverse=True)

print(f"QUALIFICATION PROBABILITIES ({NUM_SIMULATIONS} sims):\n")

for team, count in sorted_results:
    print(f"{team}: {count/NUM_SIMULATIONS*100:.1f}%")
