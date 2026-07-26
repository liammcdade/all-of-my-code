import random
import math
import numpy as np
from tqdm import tqdm
from collections import Counter

# =============================================================================
# 1. ELO RATINGS
# =============================================================================

P_RED_CARD = 0.04

TEAM_RATINGS = {
    'Argentina': 2200, 'Spain': 2232, 'France': 2143, 'England': 2076,
    'Portugal': 2013, 'Switzerland': 1949, 'Belgium': 1910,
    'Morocco': 1921, 'Norway': 1972, 'Egypt': 1747,
}

# =============================================================================
# 2. MATCH SIMULATION (Dixon-Coles, Time-Weighted Red Cards)
# =============================================================================

def sample_dixon_coles(lambda_a, lambda_b, rho=-0.12):
    max_goals = 8
    probs = np.zeros((max_goals, max_goals))
    for x in range(max_goals):
        for y in range(max_goals):
            p_x = np.exp(-lambda_a) * (lambda_a ** x) / math.factorial(x)
            p_y = np.exp(-lambda_b) * (lambda_b ** y) / math.factorial(y)
            tau = 1.0
            if x == 0 and y == 0: tau = 1 - lambda_a * lambda_b * rho
            elif x == 1 and y == 0: tau = 1 + lambda_a * rho
            elif x == 0 and y == 1: tau = 1 + lambda_b * rho
            elif x == 1 and y == 1: tau = 1 - rho

            tau = max(tau, 0.0)
            probs[x, y] = p_x * p_y * tau

    probs = np.clip(probs, 0.0, None)
    prob_sum = probs.sum()
    if prob_sum > 0:
        probs /= prob_sum
    else:
        probs = np.ones((max_goals, max_goals)) / (max_goals * max_goals)

    idx = np.random.choice(len(probs.flatten()), p=probs.flatten())
    return idx // max_goals, idx % max_goals

def simulate_match(team_a, team_b, rating_a, rating_b):
    diff = rating_a - rating_b
    base_lambda = 1.35
    c = 800.0
    lambda_a = base_lambda * (10 ** (diff / c))
    lambda_b = base_lambda * (10 ** (-diff / c))

    # Time-weighted red card impact
    if random.random() < P_RED_CARD:
        minute = random.randint(1, 90)
        impact = (90 - minute) / 90.0
        lambda_a *= (1 - 0.65 * impact); lambda_b *= (1 + 0.54 * impact)
    elif random.random() < P_RED_CARD:
        minute = random.randint(1, 90)
        impact = (90 - minute) / 90.0
        lambda_b *= (1 - 0.65 * impact); lambda_a *= (1 + 0.54 * impact)

    goals_a, goals_b = sample_dixon_coles(lambda_a, lambda_b)
    if goals_a != goals_b:
        return (team_a if goals_a > goals_b else team_b), goals_a, goals_b

    lambda_et_a, lambda_et_b = lambda_a * 0.30, lambda_b * 0.30
    goals_a_et, goals_b_et = sample_dixon_coles(lambda_et_a, lambda_et_b, rho=-0.10)
    total_a, total_b = goals_a + goals_a_et, goals_b + goals_b_et
    if total_a != total_b:
        return (team_a if total_a > total_b else team_b), total_a, total_b

    prob_a_pen = max(0.42, min(0.58, 0.5 + (diff / 800.0) * 0.08))
    while True:
        a_scores = random.random() < prob_a_pen
        b_scores = random.random() < (1.0 - prob_a_pen)
        if a_scores and not b_scores: return team_a, total_a, total_b
        if b_scores and not a_scores: return team_b, total_b, total_a

# =============================================================================
# 3. SIMULATION
# =============================================================================
#
# Bracket state:
#   Semi-Final 1: France vs Spain  -> Spain won
#   Semi-Final 2: England vs Argentina -> Argentina won
#   Final:  Spain vs Argentina
#   Bronze: France vs England
# =============================================================================

if __name__ == "__main__":
    NUM_SIMS = 5000

    SF1_WINNER, SF1_LOSER = 'Spain', 'France'
    SF2_WINNER, SF2_LOSER = 'Argentina', 'England'

    winner_tracker = Counter()

    print(f"Running {NUM_SIMS} simulations (Final)...\n")

    for _ in tqdm(range(NUM_SIMS), desc="Simulating", leave=False):
        champion, _, _ = simulate_match(
            SF1_WINNER, SF2_WINNER,
            TEAM_RATINGS[SF1_WINNER], TEAM_RATINGS[SF2_WINNER]
        )
        winner_tracker[champion] += 1

    # -------------------------------------------------------------------------
    # OUTPUT
    # -------------------------------------------------------------------------
    print("\n" + "=" * 60)
    print("FINAL: Spain vs Argentina")
    print("=" * 60)
    for team in (SF1_WINNER, SF2_WINNER):
        print(f"  {team:<12}: {winner_tracker[team] / NUM_SIMS * 100:.2f}%")

    print("\n" + "=" * 60)
    print("BRONZE MEDAL: France vs England")
    print("=" * 60)
    print(f"  England     : 100.00% (Winner)")
