import numpy as np
from tqdm import tqdm

# Current stats for Charlton Athletic and Leyton Orient as of the end of the regular season
# Pld=46 for both as the full league season is over.
team_stats = {
    "Charlton Athletic": {"Pld": 46, "GF": 67, "GA": 43, "Pts": 85},
    "Leyton Orient": {"Pld": 46, "GF": 72, "GA": 48, "Pts": 78},
}

# --- Simulation Parameters ---
runs = 100000  # Number of times to simulate the match

# --- Outcome Counters ---
charlton_athletic_wins = 0
leyton_orient_wins = 0
draws = 0

# --- Simulation Logic ---


def simulate_goals_for_team(team_avg_gf, opponent_avg_ga):
    """
    Simulates goals scored by a team in a match using a Poisson distribution.
    The expected goals are influenced by the team's average goals for and the opponent's average goals against.
    """
    # Simple average for expected goals in this specific match context
    # More sophisticated models might use strength ratings, etc.
    lambda_val = max(0, (team_avg_gf + opponent_avg_ga) / 2)
    return np.random.poisson(lambda_val)


print(
    f"Simulating the Charlton Athletic vs Leyton Orient League One Play-Off Final {runs} times...\n"
)

for _ in tqdm(range(runs), desc="Simulating Matches"):
    # Calculate average goals for/against based on full season stats
    charlton_avg_gf = (
        team_stats["Charlton Athletic"]["GF"] / team_stats["Charlton Athletic"]["Pld"]
    )
    charlton_avg_ga = (
        team_stats["Charlton Athletic"]["GA"] / team_stats["Charlton Athletic"]["Pld"]
    )

    orient_avg_gf = (
        team_stats["Leyton Orient"]["GF"] / team_stats["Leyton Orient"]["Pld"]
    )
    orient_avg_ga = (
        team_stats["Leyton Orient"]["GA"] / team_stats["Leyton Orient"]["Pld"]
    )

    # Simulate goals for each team
    # Home/Away advantage is not explicitly modeled here as it's a neutral venue (Wembley).
    charlton_goals = simulate_goals_for_team(charlton_avg_gf, orient_avg_ga)
    orient_goals = simulate_goals_for_team(orient_avg_gf, charlton_avg_ga)

    # Determine match outcome
    if charlton_goals > orient_goals:
        charlton_athletic_wins += 1
    elif orient_goals > charlton_goals:
        leyton_orient_wins += 1
    else:
        # In a play-off final, a draw after 90 mins leads to extra time/penalties.
        # For this simulation, we'll consider it a 'draw' if scores are level after regular time.
        draws += 1

# --- Display Results ---

print("\n--- Simulation Results ---")
print(f"Total simulations: {runs}\n")

# Calculate percentages
charlton_win_percent = (charlton_athletic_wins / runs) * 100
orient_win_percent = (leyton_orient_wins / runs) * 100
draw_percent = (draws / runs) * 100

print(f"Charlton Athletic wins: {charlton_athletic_wins} ({charlton_win_percent:.2f}%)")
print(f"Leyton Orient wins: {leyton_orient_wins} ({orient_win_percent:.2f}%)")
print(f"Draws (after 90 mins): {draws} ({draw_percent:.2f}%)")

print("\n--- Important Note for Play-Off Finals ---")
print(
    "This simulation predicts the outcome after 90 minutes. In a real play-off final, if the score is a draw, the match goes to extra time and potentially penalties to determine a winner."
)
print(
    "The 'Draws' percentage above represents matches that would proceed to extra time."
)
