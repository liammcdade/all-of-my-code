import numpy as np
from tqdm import tqdm

# Current stats for Sheffield United and Sunderland as of the end of the regular season
# Assuming Pld=46 for both as the full league season is over.
team_stats = {
    "Sheffield United": {"Pld": 46, "GF": 63, "GA": 36, "Pts": 90},
    "Sunderland": {"Pld": 46, "GF": 58, "GA": 44, "Pts": 76},
}

# --- Simulation Parameters ---
runs = 100000  # Number of times to simulate the match

# --- Outcome Counters ---
sheffield_united_wins = 0
sunderland_wins = 0
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
    f"Simulating the Sheffield United vs Sunderland Championship Play-Off Final {runs} times...\n"
)

for _ in tqdm(range(runs), desc="Simulating Matches"):
    # Calculate average goals for/against based on full season stats
    sheffield_united_avg_gf = (
        team_stats["Sheffield United"]["GF"] / team_stats["Sheffield United"]["Pld"]
    )
    sheffield_united_avg_ga = (
        team_stats["Sheffield United"]["GA"] / team_stats["Sheffield United"]["Pld"]
    )

    sunderland_avg_gf = team_stats["Sunderland"]["GF"] / team_stats["Sunderland"]["Pld"]
    sunderland_avg_ga = team_stats["Sunderland"]["GA"] / team_stats["Sunderland"]["Pld"]

    # Simulate goals for each team
    # Home/Away advantage is not explicitly modeled here as it's a neutral venue (Wembley).
    sheffield_united_goals = simulate_goals_for_team(
        sheffield_united_avg_gf, sunderland_avg_ga
    )
    sunderland_goals = simulate_goals_for_team(
        sunderland_avg_gf, sheffield_united_avg_ga
    )

    # Determine match outcome
    if sheffield_united_goals > sunderland_goals:
        sheffield_united_wins += 1
    elif sunderland_goals > sheffield_united_goals:
        sunderland_wins += 1
    else:
        # In a play-off final, a draw after 90 mins leads to extra time/penalties.
        # For this simulation, we'll consider it a 'draw' if scores are level after regular time.
        # If you wanted to simulate ET/Pens, you'd add that logic here.
        draws += 1

# --- Display Results ---

print("\n--- Simulation Results ---")
print(f"Total simulations: {runs}\n")

# Calculate percentages
sheffield_united_win_percent = (sheffield_united_wins / runs) * 100
sunderland_win_percent = (sunderland_wins / runs) * 100
draw_percent = (draws / runs) * 100

print(
    f"Sheffield United wins: {sheffield_united_wins} ({sheffield_united_win_percent:.2f}%)"
)
print(f"Sunderland wins: {sunderland_wins} ({sunderland_win_percent:.2f}%)")
print(f"Draws (after 90 mins): {draws} ({draw_percent:.2f}%)")

print("\n--- Important Note for Play-Off Finals ---")
print(
    "This simulation predicts the outcome after 90 minutes. In a real play-off final, if the score is a draw, the match goes to extra time and potentially penalties to determine a winner."
)
print(
    "The 'Draws' percentage above represents matches that would proceed to extra time."
)
