import random
import math
from collections import defaultdict
from tqdm import tqdm

# === CONFIGURATION ===
TOTAL_GAMEWEEKS = 38
NUM_SIMULATIONS = 100000
ABSOLUTE_MIN_SCORE = 15
SCORE_SD_MULTIPLIER = 2.5
PER_GAMEWEEK_STD = 18.0

# === PLAYER DATA ===
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

# === EASY SCORE ENTRY ===
# Just add gameweeks here! Each list is [GW1, GW2, GW3, ...]
# Leave empty lists [] for players who haven't played yet
season_scores = {
    "Alan Souter":      [62],
    "Adam Bellew":      [48],
    "Graham Vickers":   [33],
    "Steven Hoehne":    [48],
    "Miriam Head":      [41],
    "Paul McDade":      [46],
    "Liam McDade":      [64],
}

def normal_random(mean: float, std_dev: float, min_val: int) -> int:
    while True:
        value = random.gauss(mean, std_dev * SCORE_SD_MULTIPLIER)
        int_value = max(min_val, int(round(value)))
        if int_value >= min_val:
            return int_value

def get_current_standings():
    """Calculate current totals and determine how many gameweeks have been played."""
    # Find the maximum number of weeks any player has recorded
    max_weeks = max(len(scores) for scores in season_scores.values()) if any(season_scores.values()) else 0
    
    standings = {}
    for player, scores in season_scores.items():
        total = sum(scores)
        standings[player] = total
    
    return standings, max_weeks

def simulate_season():
    """Simulate the remainder of the season based on current progress."""
    standings, gameweeks_played = get_current_standings()
    gameweeks_remaining = TOTAL_GAMEWEEKS - gameweeks_played
    
    totals = {}
    for player, profile in player_profiles.items():
        current_total = standings.get(player, 0)
        
        # Simulate remaining gameweeks
        remaining_scores = [normal_random(profile["mean"], profile["std"], ABSOLUTE_MIN_SCORE)
                           for _ in range(gameweeks_remaining)]
        totals[player] = current_total + sum(remaining_scores)

    max_score = max(totals.values())
    winners = [player for player, score in totals.items() if score == max_score]

    return random.choice(winners)

def run_predictions():
    """Run simulations and display results."""
    standings, gameweeks_played = get_current_standings()
    gameweeks_remaining = TOTAL_GAMEWEEKS - gameweeks_played
    
    win_counts = defaultdict(int)

    print(f"\nRunning {NUM_SIMULATIONS:,} simulations...")
    print(f"Gameweeks played: {gameweeks_played}")
    print(f"Gameweeks remaining: {gameweeks_remaining}")
    print(f"Total gameweeks: {TOTAL_GAMEWEEKS}")
    
    print("\nCurrent standings:")
    sorted_players = sorted(standings.keys(), key=lambda p: standings[p], reverse=True)
    for player in sorted_players:
        weeks_recorded = len(season_scores[player])
        print(f"  {player:25s}: {standings[player]:>5d} points ({weeks_recorded} weeks)")

    for _ in tqdm(range(NUM_SIMULATIONS)):
        winner = simulate_season()
        win_counts[winner] += 1

    # === RESULTS ===
    print("\n" + "="*60)
    print("WIN PROBABILITY RESULTS")
    print("="*60)

    ranked_players = sorted(
        player_profiles.keys(),
        key=lambda p: win_counts[p],
        reverse=True
    )
    for player in ranked_players:
        wins = win_counts[player]
        probability = (wins / NUM_SIMULATIONS) * 100
        bar_length = int(probability / 2)
        bar = "█" * bar_length
        print(f"{player:25s}: {probability:6.2f}% {bar}")

    print("="*60)

    leader = ranked_players[0]
    print(f"\n🏆 Current favourite: {leader}")
    
    return ranked_players, win_counts

def show_all_scores():
    """Display all recorded scores for each player."""
    print("\n" + "="*70)
    print("DETAILED SCORES BY WEEK")
    print("="*70)
    
    max_weeks = max(len(scores) for scores in season_scores.values()) if any(season_scores.values()) else 0
    
    if max_weeks == 0:
        print("No scores recorded yet.")
        return
    
    # Header
    header = f"{'Player':<20s}"
    for week in range(1, max_weeks + 1):
        header += f" GW{week:<4d}"
    header += f" {'Total':>6s}  {'Avg':>5s}"
    print(header)
    print("-" * len(header))
    
    # Data rows - sorted by total score
    players_by_total = sorted(season_scores.keys(), 
                             key=lambda p: sum(season_scores[p]), 
                             reverse=True)
    
    for player in players_by_total:
        scores = season_scores[player]
        row = f"{player:<20s}"
        for week in range(max_weeks):
            if week < len(scores):
                row += f" {scores[week]:<4d}"
            else:
                row += f" {'-':<4s}"
        total = sum(scores)
        avg = total / len(scores) if scores else 0
        row += f" {total:>6d}  {avg:>5.1f}"
        print(row)

def quick_update():
    """Helper function to easily add next gameweek scores."""
    print("\n" + "="*60)
    print("QUICK UPDATE - Add Next Gameweek")
    print("="*60)
    print("Enter scores for each player (or press Enter to skip):")
    
    max_weeks = max(len(scores) for scores in season_scores.values()) if any(season_scores.values()) else 0
    next_gw = max_weeks + 1
    
    print(f"\nGameweek {next_gw}:\n")
    
    for player in season_scores.keys():
        current_scores = season_scores[player].copy()
        prompt = f"  {player:<25s} (current total: {sum(current_scores):>4d}): "
        try:
            score_input = input(prompt)
            if score_input.strip():
                score = int(score_input)
                current_scores.append(score)
                season_scores[player] = current_scores
                print(f"    → Added {score} (new total: {sum(current_scores)})")
            else:
                print(f"    → Skipped")
        except ValueError:
            print(f"    → Invalid input, skipped")
    
    print("\n✅ Update complete!")

# === MAIN EXECUTION ===
if __name__ == "__main__":
    # Show current scores
    show_all_scores()
    
    # Run predictions
    run_predictions()
    
    # Optional: Uncomment to enable interactive mode
    # quick_update()
    # show_all_scores()
    # run_predictions()