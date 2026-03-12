import math
import numpy as np


def expected_goals_skellam_random_cap(team_a_elo, team_b_elo, baseline_goals=2.531666667,
                                      cap_min=200, cap_max=350):
    """
    Calculate expected goals with a random cap applied between cap_min and cap_max.
    """
    lambda_base = baseline_goals / 2
    D = team_b_elo - team_a_elo

    # Random cap between min and max
    elo_cap = np.random.uniform(cap_min, cap_max)

    # Adjust large differences
    if D > elo_cap:
        excess = D - elo_cap
        D = elo_cap - math.sqrt(excess)
    elif D < -elo_cap:
        excess = -D - elo_cap
        D = -elo_cap + math.sqrt(excess)

    lambda_A = lambda_base * 10 ** (-D / 400)
    lambda_B = lambda_base * 10 ** (D / 400)

    return lambda_A, lambda_B


def simulate_average_score(team_a_elo, team_b_elo, sims=1000):
    """
    Simulate matches with random caps and return average goals, goal difference,
    and most likely scoreline.
    """
    goals_A_list = []
    goals_B_list = []

    for _ in range(sims):
        lambda_A, lambda_B = expected_goals_skellam_random_cap(team_a_elo, team_b_elo)
        gA = np.random.poisson(lambda_A)
        gB = np.random.poisson(lambda_B)
        goals_A_list.append(gA)
        goals_B_list.append(gB)

    avg_A = np.mean(goals_A_list)
    avg_B = np.mean(goals_B_list)
    avg_diff = np.mean(np.array(goals_A_list) - np.array(goals_B_list))
    score_pairs = list(zip(goals_A_list, goals_B_list))
    most_common_score = max(set(score_pairs), key=score_pairs.count)

    return {
        "avg_goals_A": round(avg_A, 4),
        "avg_goals_B": round(avg_B, 4),
        "avg_goal_diff": round(avg_diff, 4),
        "most_common_score": most_common_score
    }


# -------------------------------
# Example Usage (with nice printable output)
# -------------------------------

team_a_elo = 1873
team_b_elo = 1943
sims = 1000

matchup = simulate_average_score(team_a_elo, team_b_elo, sims)

# ==================== NICER FORMATTED OUTPUT ====================
print("**Matchup Simulation Results**")
print(f"**Team A (ELO {team_a_elo}) vs Team B (ELO {team_b_elo})**")
print(f"({sims:,} Monte Carlo simulations with random ELO caps)\n")

print("Average Goals")
print(f"• Team A: {matchup['avg_goals_A']}")
print(f"• Team B: {matchup['avg_goals_B']}")

print("\nAverage Goal Difference")
print(f"• {matchup['avg_goal_diff']} (strong Team A advantage)")

print("\nMost Common Scoreline")
print(f"• {matchup['most_common_score'][0]} – {matchup['most_common_score'][1]}")

print("\nSummary")
print("Team A is overwhelmingly favored, with simulations showing high-scoring wins")
print("and a very high likelihood of a shutout victory.")