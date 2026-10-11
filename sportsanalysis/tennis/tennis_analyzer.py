import random
import pandas as pd
from io import StringIO

# Raw data (only the 8 quarterfinalists)
data = """
Elo Rank	Player	Age	Elo	    	hElo Rank	hElo	cElo Rank	cElo	gElo Rank	gElo	    	Peak Elo	Peak Month	    	ATP Rank	Log diff
3	Alexander Zverev	29.3	2093.1		3	2027.1	3	2047.8	3	1946.7		2176.5	2022-01		2	0.41
68	Botic Van De Zandschulp	30.8	1772.7		53	1743.9	73	1696.4	103	1608.1		1938.0	2022-09		70	-0.03
56	Karen Khachanov	30.2	1790.8		55	1741.6	42	1768.6	32	1710.2		2029.5	2018-10		50	0.11
26	Alexander Blockx	21.3	1869.1		39	1770.2	20	1838.8	52	1670.7		1907.2	2026-05		34	-0.27
15	Frances Tiafoe	28.5	1934.2		14	1883.7	21	1835.6	9	1825.9		1974.0	2023-06		12	0.22
31	Alex Michelsen	21.9	1846.0		24	1827.1	67	1704.9	31	1710.5		1904.8	2025-01		46	-0.39
7	Ben Shelton	23.8	1977.5		6	1948.5	17	1853.6	6	1852.9		2024.4	2025-08		9	-0.25
2	Carlos Alcaraz	22.9	2146.8		2	2073.3	2	2086.6	2	2014.2		2308.5	2026-03		3	-0.41
"""

# Parse the data
df = pd.read_csv(StringIO(data), sep='\t', skipinitialspace=True)

# Extract hElo for the players
players = {
    "Alexander Zverev": df.loc[df['Player'] == "Alexander Zverev", 'hElo'].values[0],
    "Botic Van De Zandschulp": df.loc[df['Player'] == "Botic Van De Zandschulp", 'hElo'].values[0],
    "Karen Khachanov": df.loc[df['Player'] == "Karen Khachanov", 'hElo'].values[0],
    "Alexander Blockx": df.loc[df['Player'] == "Alexander Blockx", 'hElo'].values[0],
    "Frances Tiafoe": df.loc[df['Player'] == "Frances Tiafoe", 'hElo'].values[0],
    "Alex Michelsen": df.loc[df['Player'] == "Alex Michelsen", 'hElo'].values[0],
    "Ben Shelton": df.loc[df['Player'] == "Ben Shelton", 'hElo'].values[0],
    "Carlos Alcaraz": df.loc[df['Player'] == "Carlos Alcaraz", 'hElo'].values[0],
}

# ------------------------------------------------------------------
# Convert best-of-three win probability to best-of-five
# ------------------------------------------------------------------
def p3_to_p5(p3):
    """Given win probability in a best-of-3 match, return win probability in best-of-5,
       assuming independent sets with constant set-win probability."""
    # Binary search for set win probability s such that p3 = s^2*(3-2s)
    lo, hi = 0.0, 1.0
    for _ in range(100):
        mid = (lo + hi) / 2.0
        p3_est = mid * mid * (3.0 - 2.0 * mid)
        if p3_est < p3:
            lo = mid
        else:
            hi = mid
    s = (lo + hi) / 2.0
    # p5 = s^3 * (10 - 15s + 6s^2)
    p5 = s**3 * (10.0 - 15.0*s + 6.0*s**2)
    return p5

def match_win_prob_bo5(eloa, elob):
    """Probability that player A (elo a) beats player B in a best-of-five match."""
    p3 = 1.0 / (1.0 + 10.0 ** ((elob - eloa) / 400.0))
    return p3_to_p5(p3)

# ------------------------------------------------------------------
# Simulate one match (best-of-five)
# ------------------------------------------------------------------
def play_match(player_a, player_b, elo_dict):
    prob_a = match_win_prob_bo5(elo_dict[player_a], elo_dict[player_b])
    return player_a if random.random() < prob_a else player_b

# ------------------------------------------------------------------
# Simulate the whole tournament once
# ------------------------------------------------------------------
def simulate_tournament(elo_dict):
    # Quarterfinals
    qf1 = play_match("Alexander Zverev", "Botic Van De Zandschulp", elo_dict)
    qf2 = play_match("Karen Khachanov", "Alexander Blockx", elo_dict)
    qf3 = play_match("Frances Tiafoe", "Alex Michelsen", elo_dict)
    qf4 = play_match("Ben Shelton", "Carlos Alcaraz", elo_dict)
    
    # Semifinals
    sf1 = play_match(qf1, qf2, elo_dict)
    sf2 = play_match(qf3, qf4, elo_dict)
    
    # Final
    champion = play_match(sf1, sf2, elo_dict)
    return champion

# ------------------------------------------------------------------
# Monte Carlo simulation
# ------------------------------------------------------------------
N = 10000
random.seed(42)   # for reproducible results

wins = {player: 0 for player in players.keys()}
for _ in range(N):
    champ = simulate_tournament(players)
    wins[champ] += 1

# ------------------------------------------------------------------
# Print results
# ------------------------------------------------------------------
print(f"Tournament win probabilities after {N:,} simulations (best-of-five, hard court):\n")
for player, count in sorted(wins.items(), key=lambda x: -x[1]):
    prob = count / N * 100
    print(f"{player:25s} {prob:5.2f}%")

most_likely = max(wins, key=wins.get)
print(f"\nMost likely champion: {most_likely} ({wins[most_likely]/N*100:.2f}%)")