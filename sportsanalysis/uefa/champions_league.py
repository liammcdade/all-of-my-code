import random
import math
from collections import Counter

# Elo ratings (update as needed)
elos = {
    "Arsenal": 2057,
    "Bayern Munich": 1987,
    "Liverpool": 1924,
    "Tottenham Hotspur": 1766,
    "Barcelona": 1957,
    "PSG": 1955,
    "Real Madrid": 1944,
    "Sporting CP": 1861,
    "Newcastle United": 1862,
    "Atletico Madrid": 1861,
    "Atalanta": 1792,
    "Galatasaray": 1735,
}

# Poisson generator
def poisson_random(lam):
    L = math.exp(-lam)
    k = 0
    p = 1.0
    while True:
        k += 1
        p *= random.random()
        if p <= L:
            return k - 1

# Expected goals
def get_expected_goals(home_elo, away_elo):
    diff = home_elo - away_elo
    home_lambda = 1.4 + (diff * 0.001)
    away_lambda = 1.1 - (diff * 0.001)
    return max(0.6, min(4.0, home_lambda)), max(0.6, min(4.0, away_lambda))

# Penalties (Elo-weighted)
def simulate_penalties(team_a, team_b):
    diff = elos[team_a] - elos[team_b]
    prob_a = 1 / (1 + 10 ** (-diff / 400))
    return team_a if random.random() < prob_a else team_b

# Two-legged tie (NO away goals)
def simulate_two_leg_tie(team_a, team_b, first_leg_home_is_a):
    # Leg 1
    if first_leg_home_is_a:
        h1, a1 = get_expected_goals(elos[team_a], elos[team_b])
        g_a1 = poisson_random(h1)
        g_b1 = poisson_random(a1)

        # Leg 2
        h2, a2 = get_expected_goals(elos[team_b], elos[team_a])
        g_b2 = poisson_random(h2)
        g_a2 = poisson_random(a2)
    else:
        h1, a1 = get_expected_goals(elos[team_b], elos[team_a])
        g_b1 = poisson_random(h1)
        g_a1 = poisson_random(a1)

        h2, a2 = get_expected_goals(elos[team_a], elos[team_b])
        g_a2 = poisson_random(h2)
        g_b2 = poisson_random(a2)

    total_a = g_a1 + g_a2
    total_b = g_b1 + g_b2

    if total_a > total_b:
        return team_a
    elif total_b > total_a:
        return team_b
    else:
        return simulate_penalties(team_a, team_b)

# Final (single match)
def simulate_final(team_a, team_b):
    diff = elos[team_a] - elos[team_b]
    lam_a = max(0.6, min(4.0, 1.25 + diff * 0.001))
    lam_b = max(0.6, min(4.0, 1.25 - diff * 0.001))

    g_a = poisson_random(lam_a)
    g_b = poisson_random(lam_b)

    if g_a > g_b:
        return team_a
    elif g_b > g_a:
        return team_b
    else:
        return simulate_penalties(team_a, team_b)

# Monte Carlo
NUM_SIMS = 50000
champion_counts = Counter()

print(f"Running {NUM_SIMS} simulations...\n")

for _ in range(NUM_SIMS):

    # Remaining Quarter-finals
    # QF2: Bayern Munich beat Real Madrid
    qf2 = "Bayern Munich"
    # QF4: Arsenal beat Sporting CP
    qf4 = "Arsenal"

    # Semi-finals
    sf1 = simulate_two_leg_tie("PSG", qf2, True)
    sf2 = simulate_two_leg_tie("Atletico Madrid", qf4, True)

    # Final
    winner = simulate_final(sf1, sf2)
    champion_counts[winner] += 1

# Results
print("=== WIN PROBABILITIES ===")
for team, count in sorted(champion_counts.items(), key=lambda x: x[1], reverse=True):
    print(f"{team:20} : {count / NUM_SIMS * 100:5.2f}%")