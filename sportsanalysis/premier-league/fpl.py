import random
import math
from collections import defaultdict
from tqdm import tqdm

# === CONFIGURATION ===
TOTAL_GAMEWEEKS = 38
GAMEWEEKS_PLAYED = 0
GAMEWEEKS_REMAINING = TOTAL_GAMEWEEKS - GAMEWEEKS_PLAYED
NUM_SIMULATIONS = 100000
ABSOLUTE_MIN_SCORE = 15
SCORE_SD_MULTIPLIER = 2.5

# Per-gameweek standard deviation used for every player (no weekly history
# available, only last season's final total). Tune to taste.
PER_GAMEWEEK_STD = 18.0

# === PLAYER DATA ===
# Season has not started. Each player's expected per-gameweek mean is derived
# from their previous season's final total (total / 38 gameweeks).
random.seed(42)
last_year_totals = {
    "Alan Souter": 2206,
    "Adam Bellew": 2191,
    "Graham Vickers": 2041,
    "Steven Hoehne": 2020,
    "Miriam Head": 1955,
    "Paul McDade": 1930,
    "Liam McDade": 1764,
}

player_profiles = {
    name: {"mean": total / TOTAL_GAMEWEEKS, "std": PER_GAMEWEEK_STD}
    for name, total in last_year_totals.items()
}

def normal_random(mean: float, std_dev: float, min_val: int) -> int:
    while True:
        value = random.gauss(mean, std_dev * SCORE_SD_MULTIPLIER)
        int_value = max(min_val, int(round(value)))
        if int_value >= min_val:
            return int_value

def simulate_season():
    totals = {}

    for player, profile in player_profiles.items():
        scores = [normal_random(profile["mean"], profile["std"], ABSOLUTE_MIN_SCORE)
                  for _ in range(GAMEWEEKS_REMAINING)]
        totals[player] = sum(scores)

    max_score = max(totals.values())
    winners = [player for player, score in totals.items() if score == max_score]

    return random.choice(winners)

# Run simulations
win_counts = defaultdict(int)

print(f"Running {NUM_SIMULATIONS:,} simulations...")
print(f"Gameweeks played: {GAMEWEEKS_PLAYED}")
print(f"Gameweeks remaining: {GAMEWEEKS_REMAINING}")
print(f"Total gameweeks: {TOTAL_GAMEWEEKS}")
print("\nPlayer profiles (expected per-gameweek mean from last season):")
for name, total in last_year_totals.items():
    profile = player_profiles[name]
    print(f"  {name}: last_year={total}, mean={profile['mean']:.1f}, std={profile['std']:.1f}")
print("\nCurrent standings:")
print("  All players start at 0 points (season not yet started)")

for _ in tqdm(range(NUM_SIMULATIONS)):
    winner = simulate_season()
    win_counts[winner] += 1

# === RESULTS ===
print("\n" + "="*50)
print("WIN PROBABILITY RESULTS")
print("="*50)

ranked_players = sorted(
    player_profiles.keys(),
    key=lambda p: win_counts[p],
    reverse=True
)
for player in ranked_players:
    wins = win_counts[player]
    probability = (wins / NUM_SIMULATIONS) * 100
    print(f"{player:25s}: {probability:6.2f}% ({wins:,} wins)")

print("="*50)

leader = ranked_players[0]
print(f"\nPre-season favourite: {leader}")
