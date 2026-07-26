import random
import math
from collections import defaultdict

try:
    from tqdm import tqdm
except ImportError:
    def tqdm(iterable, *args, **kwargs):
        return iterable

# === CONFIGURATION ===
NUM_SIMULATIONS = 100000
GAMWEEKS_PLAYED = 6
GAMWEEKS_REMAINING = 1
ABSOLUTE_MIN_SCORE = 0
SCORE_SD_MULTIPLIER = 2.5

# === PLAYER DATA ===
random.seed(42)
streamy_scores = [80, 101, 84, 118, 63, 71, 55]
crumpet_scores = [41, 56, 48, 101, 65, 95, 40]
sir_good_scores = [75, 53, 80, 57, 69, 41, 35]

players = {
    "Streamy": streamy_scores,
    "Crumpet1453": crumpet_scores,
    "Sir_Good_Fort_Trooper": sir_good_scores
}

def calculate_standard_deviation(scores: list) -> float:
    if len(scores) < 2:
        return 0.0
    mean = sum(scores) / len(scores)
    variance = sum((x - mean) ** 2 for x in scores) / len(scores)
    return math.sqrt(variance)

def normal_random(mean: float, std_dev: float, min_val: int) -> int:
    while True:
        value = random.gauss(mean, std_dev * SCORE_SD_MULTIPLIER)
        int_value = max(min_val, int(round(value)))
        if int_value >= min_val:
            return int_value

def simulate_season():
    totals = {}
    
    for player, scores in players.items():
        current_total = sum(scores)
        avg = sum(scores) / len(scores)
        std_dev = calculate_standard_deviation(scores)
        remaining_scores = [normal_random(avg, std_dev, ABSOLUTE_MIN_SCORE) 
                          for _ in range(GAMWEEKS_REMAINING)]
        final_total = current_total + sum(remaining_scores)
        totals[player] = final_total
    
    max_score = max(totals.values())
    winners = [player for player, score in totals.items() if score == max_score]
    
    return random.choice(winners)

# Run simulations
win_counts = defaultdict(int)

print(f"Running {NUM_SIMULATIONS:,} simulations...")
print(f"Gameweeks played: {GAMWEEKS_PLAYED}")
print(f"Gameweeks remaining: {GAMWEEKS_REMAINING}")
print("\nPlayer statistics (based on historical data):")
for player, scores in players.items():
    avg = sum(scores) / len(scores)
    std_dev = calculate_standard_deviation(scores)
    print(f"  {player}: avg={avg:.1f}, std_dev={std_dev:.1f} pts (GW scores: {scores})")
print("\nCurrent standings:")
for player, scores in players.items():
    print(f"  {player}: {sum(scores)} points")

for _ in tqdm(range(NUM_SIMULATIONS)):
    winner = simulate_season()
    win_counts[winner] += 1

# === RESULTS ===
print("\n" + "="*50)
print("WIN PROBABILITY RESULTS")
print("="*50)

for player in players.keys():
    wins = win_counts[player]
    probability = (wins / NUM_SIMULATIONS) * 100
    print(f"{player:25s}: {probability:6.2f}% ({wins:,} wins)")

print("="*50)

# Show current leader
current_totals = {player: sum(scores) for player, scores in players.items()}
leader = max(current_totals, key=current_totals.get)
print(f"\nCurrent leader: {leader} with {current_totals[leader]} points")