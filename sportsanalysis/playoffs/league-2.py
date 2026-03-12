import numpy as np
from tqdm import tqdm

# Current stats for Walsall and AFC Wimbledon as of the end of the regular season
# Pld=46 for both as the full league season is over.
team_stats = {
    "Walsall": {"Pld": 46, "GF": 75, "GA": 54, "Pts": 77},
    "AFC Wimbledon": {"Pld": 46, "GF": 56, "GA": 35, "Pts": 73},
}

# --- Simulation Parameters ---
runs = 100000  # Number of times to simulate the match

# --- Outcome Counters ---
walsall_wins = 0
afc_wimbledon_wins = 0
draws = 0

# --- Simulation Logic ---


def simulate_goals_for_team(team_avg_gf, opponent_avg_ga):
    """
    Simulates goals scored by a team in a match using a Poisson distribution.
    The expected goals are influenced by the team's average goals for and the opponent's average goals against.
    """
    # Simple average for expected goals in this specific match context
    lambda_val = max(0, (team_avg_gf + opponent_avg_ga) / 2)
    return np.random.poisson(lambda_val)


print(
    f"Simulating the Walsall vs AFC Wimbledon League Two Play-Off Final {runs} times...\n"
)

for _ in tqdm(range(runs), desc="Simulating Matches"):
    # Calculate average goals for/against based on full season stats
    walsall_avg_gf = team_stats["Walsall"]["GF"] / team_stats["Walsall"]["Pld"]
    walsall_avg_ga = team_stats["Walsall"]["GA"] / team_stats["Walsall"]["Pld"]

    wimbledon_avg_gf = (
        team_stats["AFC Wimbledon"]["GF"] / team_stats["AFC Wimbledon"]["Pld"]
    )
    wimbledon_avg_ga = (
        team_stats["AFC Wimbledon"]["GA"] / team_stats["AFC Wimbledon"]["Pld"]
    )

    # Simulate goals for each team
    # Home/Away advantage is not explicitly modeled here as it's a neutral venue (Wembley).
    walsall_goals = simulate_goals_for_team(walsall_avg_gf, wimbledon_avg_ga)
    wimbledon_goals = simulate_goals_for_team(wimbledon_avg_gf, walsall_avg_ga)

    # Determine match outcome
    if walsall_goals > wimbledon_goals:
        walsall_wins += 1
    elif wimbledon_goals > walsall_goals:
        afc_wimbledon_wins += 1
    else:
        # In a play-off final, a draw after 90 mins leads to extra time/penalties.
        # For this simulation, we'll consider it a 'draw' if scores are level after regular time.
        draws += 1

# --- Display Results ---

print("\n--- Simulation Results ---")
print(f"Total simulations: {runs}\n")

# Calculate percentages
walsall_win_percent = (walsall_wins / runs) * 100
wimbledon_win_percent = (afc_wimbledon_wins / runs) * 100
draw_percent = (draws / runs) * 100

print(f"Walsall wins: {walsall_wins} ({walsall_win_percent:.2f}%)")
print(f"AFC Wimbledon wins: {afc_wimbledon_wins} ({wimbledon_win_percent:.2f}%)")
print(f"Draws (after 90 mins): {draws} ({draw_percent:.2f}%)")
