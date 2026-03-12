import pandas as pd

# Load your data files
chelsea_df = pd.read_csv('sportsanalysis/clubworldcup/chelsea.csv')
psg_df = pd.read_csv('sportsanalysis/clubworldcup/psg.csv')

# Define the xG estimation function
# xG = PK * 0.79 + (Sh - PKatt) * 0.10

def estimate_xg(row):
    penalty_xg = row['PK'] * 0.79
    non_penalty_shots = row['Sh'] - row['PKatt']
    non_penalty_xg = non_penalty_shots * 0.10
    return penalty_xg + non_penalty_xg

# Apply the xG estimation to both dataframes
chelsea_df['xG_est'] = chelsea_df.apply(estimate_xg, axis=1)
psg_df['xG_est'] = psg_df.apply(estimate_xg, axis=1)

# Show selected columns including the new xG estimate

print("Chelsea xG Estimation:")
print(chelsea_df[['Age', 'Min', 'Gls', 'Ast', 'PK', 'PKatt', 'Sh', 'SoT', 'xG_est']])
chelsea_total_xg = chelsea_df['xG_est'].sum()
print(f"Total Chelsea xG: {chelsea_total_xg:.2f}")

print("\nPSG xG Estimation:")
print(psg_df[['Age', 'Min', 'Gls', 'Ast', 'PK', 'PKatt', 'Sh', 'SoT', 'xG_est']])
psg_total_xg = psg_df['xG_est'].sum()
print(f"Total PSG xG: {psg_total_xg:.2f}")
