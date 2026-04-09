import random
import math
from collections import Counter

# Current Elo ratings from clubelo.com (as of April 8, 2026)
# Update these manually from https://clubelo.com/ if needed
elos = {
    "Crystal Palace": 1795,
    "Strasbourg": 1715,
    "Mainz 05": 1696,
    "Rayo Vallecano": 1672,
    "Fiorentina": 1670,
    "AEK Athens": 1639,
    "Shakhtar Donetsk": 1566,
    "AZ Alkmaar": 1559,
}

# Poisson random variable generator (pure Python)
def poisson_random(lam):
    if lam < 0:
        lam = 0
    L = math.exp(-lam)
    k = 0
    p = 1.0
    while True:
        k += 1
        p *= random.random()
        if p <= L:
            return k - 1

# Expected goals for a leg (home advantage baked into base values)
def get_expected_goals(home_elo, away_elo):
    diff = home_elo - away_elo
    home_lambda = 1.4 + (diff * 0.001)
    away_lambda = 1.1 - (diff * 0.001)
    home_lambda = max(0.6, min(4.0, home_lambda))
    away_lambda = max(0.6, min(4.0, away_lambda))
    return home_lambda, away_lambda

# Simulate penalties (Elo-based slight favorite)
def simulate_penalties(team_a, team_b, elos_dict):
    diff = elos_dict[team_a] - elos_dict[team_b]
    prob_a = 1 / (1 + 10 ** (-diff / 400))
    return team_a if random.random() < prob_a else team_b

# Simulate a two-legged tie (first leg home known)
def simulate_two_leg_tie(team_a, team_b, first_leg_home_is_a, elos_dict):
    if first_leg_home_is_a:
        # Leg 1: team_a home
        h_l1, a_l1 = get_expected_goals(elos_dict[team_a], elos_dict[team_b])
        g_a1 = poisson_random(h_l1)
        g_b1 = poisson_random(a_l1)
        # Leg 2: team_b home
        h_l2, a_l2 = get_expected_goals(elos_dict[team_b], elos_dict[team_a])
        g_b2 = poisson_random(h_l2)
        g_a2 = poisson_random(a_l2)
    else:
        # Swap roles
        h_l1, a_l1 = get_expected_goals(elos_dict[team_b], elos_dict[team_a])
        g_b1 = poisson_random(h_l1)
        g_a1 = poisson_random(a_l1)
        h_l2, a_l2 = get_expected_goals(elos_dict[team_a], elos_dict[team_b])
        g_a2 = poisson_random(h_l2)
        g_b2 = poisson_random(a_l2)

    total_a = g_a1 + g_a2
    total_b = g_b1 + g_b2

    if total_a > total_b:
        return team_a
    elif total_a < total_b:
        return team_b
    else:
        # Away goals
        away_a = g_a2
        away_b = g_b1
        if away_a > away_b:
            return team_a
        elif away_a < away_b:
            return team_b
        else:
            return simulate_penalties(team_a, team_b, elos_dict)

# Simulate single-leg final (neutral venue)
def simulate_final(team_a, team_b, elos_dict):
    diff = elos_dict[team_a] - elos_dict[team_b]
    lambda_a = 1.25 + (diff * 0.001)
    lambda_b = 1.25 - (diff * 0.001)
    lambda_a = max(0.6, min(4.0, lambda_a))
    lambda_b = max(0.6, min(4.0, lambda_b))
    g_a = poisson_random(lambda_a)
    g_b = poisson_random(lambda_b)
    if g_a > g_b:
        return team_a
    elif g_a < g_b:
        return team_b
    else:
        return simulate_penalties(team_a, team_b, elos_dict)

# Quarter-finals (fixed as of April 8, 2026)
qf_teams = list(elos.keys())

# Run Monte Carlo simulations
NUM_SIMS = 50000
champion_counts = Counter()

print("Simulating Europa Conference League (QF + SF + Final)...")
print(f"Running {NUM_SIMS} simulations using current Elo + Poisson goals...\n")

for sim in range(NUM_SIMS):
    # Quarter-finals (two-legged, first leg home advantage)
    qf_winners = {}

    # QF1: Rayo Vallecano vs AEK Athens - Rayo home first
    qf_winners["qf1"] = simulate_two_leg_tie("Rayo Vallecano", "AEK Athens", True, elos)

    # QF2: Crystal Palace vs Fiorentina - Crystal Palace home first
    qf_winners["qf2"] = simulate_two_leg_tie("Crystal Palace", "Fiorentina", True, elos)

    # QF3: Mainz 05 vs Strasbourg - Mainz home first
    qf_winners["qf3"] = simulate_two_leg_tie("Mainz 05", "Strasbourg", True, elos)

    # QF4: Shakhtar Donetsk vs AZ Alkmaar - Shakhtar home first
    qf_winners["qf4"] = simulate_two_leg_tie("Shakhtar Donetsk", "AZ Alkmaar", True, elos)

    # Semi-finals
    sf1 = simulate_two_leg_tie(qf_winners["qf1"], qf_winners["qf2"], True, elos)  # QF1 winner home first
    sf2 = simulate_two_leg_tie(qf_winners["qf3"], qf_winners["qf4"], True, elos)  # QF3 winner home first

    # Final (neutral)
    champion = simulate_final(sf1, sf2, elos)
    champion_counts[champion] += 1

# Results
print("=== EUROPA CONFERENCE LEAGUE WIN PROBABILITIES ===")
sorted_champs = sorted(champion_counts.items(), key=lambda x: x[1], reverse=True)
for team, count in sorted_champs:
    prob = (count / NUM_SIMS) * 100
    print(f"{team:20} : {prob:5.1f}%  ({count} simulations)")

print("\nNote: This accounts for current QF, away goals rule, and penalties.")
print("Run again for new random outcomes. Update elos dict from clubelo.com for future accuracy.")