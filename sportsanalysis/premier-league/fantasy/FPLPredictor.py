import numpy as np
import pandas as pd
from tqdm import tqdm

# ---------------------------------------------------------
# 1. UPDATED LEAGUE DATA (From your latest message)
# ---------------------------------------------------------
teams = {
    "Streamy FC":       482,  # You!
    "Bellews Booters":  443,
    "G Town XI":        442,
    "Nomags":           429,
    "Tommy 2 U":        422,
    "bronze woos":      416,
    "ButteryCrumpet":   386
}

GAMEWEEKS_PLAYED = 7.1
REMAINING_GAMEWEEKS = 31   # Assuming 38 total weeks
N_SIMULATIONS = 100_000

# ---------------------------------------------------------
# 2. SETUP PARAMETERS
# ---------------------------------------------------------
team_means = {team: points / GAMEWEEKS_PLAYED for team, points in teams.items()}

# Standard deviation range for per-simulation variance
STD_DEV_MIN = 10.0
STD_DEV_MAX = 20.0

# ---------------------------------------------------------
# 3. MONTE CARLO SIMULATION
# ---------------------------------------------------------
win_counts = {team: 0 for team in teams}

for _ in tqdm(range(N_SIMULATIONS), desc="Simulating FPL", unit="sim"):
    final_totals = {}
    
    for team, current_total in teams.items():
        mean_score = team_means[team]
        sim_std = np.random.uniform(STD_DEV_MIN, STD_DEV_MAX)
        
        # Simulate remaining weeks
        simulated_scores = np.random.normal(loc=mean_score, scale=sim_std, size=REMAINING_GAMEWEEKS)
        simulated_scores = np.maximum(simulated_scores, 0) # No negative scores
        
        final_totals[team] = current_total + simulated_scores.sum()
    
    # Find the winner
    winner = max(final_totals, key=final_totals.get)
    win_counts[winner] += 1

# ---------------------------------------------------------
# 4. CALCULATE AND DISPLAY WIN PERCENTAGES
# ---------------------------------------------------------
results = []
for team in teams:
    win_pct = (win_counts[team] / N_SIMULATIONS) * 100
    results.append({"Team": team, "Win %": f"{win_pct:.3f}"})

df_results = pd.DataFrame(results).sort_values("Win %", ascending=False).reset_index(drop=True)
df_results.index += 1 
print(df_results.to_string())