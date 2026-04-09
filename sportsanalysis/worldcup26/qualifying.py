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

# Average goals per match (international football baseline)
AVG_GOALS_PER_MATCH = 2.55

# =========================
# ELO PROBABILITY & EXPECTED GOALS
# =========================
def win_probability(team1, team2, home_adv=85):
    """Return probability team1 wins (with home advantage)."""
    e1 = elo[team1] + home_adv
    e2 = elo[team2]
    return 1 / (1 + 10 ** ((e2 - e1) / 400))

def expected_goals(team1, team2, home_adv=85):
    """Return (xG_team1, xG_team2) derived from ELO ratings."""
    p1 = win_probability(team1, team2, home_adv)
    p2 = 1 - p1
    # Split average goals by strength ratio
    total = AVG_GOALS_PER_MATCH
    xg1 = total * (p1 / (p1 + p2))
    xg2 = total * (p2 / (p1 + p2))
    return xg1, xg2

def match(team1, team2, home_adv=85):
    p1 = win_probability(team1, team2, home_adv)
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

all_games = [(h, a, "UEFA Final") for h, a in UEFA_FINALS] + \
            [(h, a, "Intercontinental") for h, a in INTERCONTINENTAL_FINALS]

print(f"{'='*65}")
print(f"  GAME-BY-GAME BREAKDOWN ({NUM_SIMULATIONS} sims)")
print(f"{'='*65}")

for home, away, label in all_games:
    p_home = win_probability(home, away)
    p_away = 1 - p_home
    xg_home, xg_away = expected_goals(home, away)
    print(f"\n  [{label}] {home} vs {away}")
    print(f"    {home:<30s}  Win: {p_home*100:5.1f}%   xG: {xg_home:.2f}")
    print(f"    {away:<30s}  Win: {p_away*100:5.1f}%   xG: {xg_away:.2f}")

print(f"\n{'='*65}")
print(f"  QUALIFICATION PROBABILITIES ({NUM_SIMULATIONS} sims)")
print(f"{'='*65}\n")

sorted_results = sorted(results.items(), key=lambda x: x[1], reverse=True)
for team, count in sorted_results:
    print(f"  {team:<30s}  {count/NUM_SIMULATIONS*100:5.1f}%")
