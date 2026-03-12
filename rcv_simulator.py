import pandas as pd
from tabulate import tabulate
from tqdm import tqdm
import time

def simulate_rcv(first_prefs, transfer_map, sleep=0.5, verbose=True):
    votes = first_prefs.copy()
    votes["Exhausted"] = 0
    history = [votes.copy()]

    while True:
        total_valid = sum(v for c, v in votes.items() if c != "Exhausted")
        if total_valid == 0:
            return pd.DataFrame(history), "No Winner", len(history) - 1
            
        for cand, v in votes.items():
            if cand != "Exhausted" and v > total_valid / 2:
                return pd.DataFrame(history), cand, len(history) - 1

        active = {c: v for c, v in votes.items() if v > 0 and c != "Exhausted"}
        if not active:
             return pd.DataFrame(history), "Tie/No Winner", len(history) - 1
             
        loser = min(active, key=active.get)

        if verbose:
            print(f"\nEliminating {loser}...")

        transfers = transfer_map.get(loser, {})
        loser_votes = votes[loser]

        for target, frac in transfers.items():
            votes[target] = votes.get(target, 0) + loser_votes * frac
        
        # Remainder goes to exhausted if not fully transferred
        transferred_frac = sum(transfers.values())
        if transferred_frac < 1.0:
            votes["Exhausted"] += loser_votes * (1.0 - transferred_frac)

        del votes[loser]
        history.append(votes.copy())

        # Progress bar for the elimination
        for _ in tqdm(range(10), desc=f"Redistributing {loser}'s votes"):
            time.sleep(sleep / 10)

def run_simulation():
    print("--- Ranked Choice Voting Simulator ---")
    
    # First preference votes
    first_prefs = {
        "Labour": 16621,
        "Conservative": 14323,
        "Reform UK": 6852,
        "Green": 2847,
        "Liberal Democrat": 1735,
    }

    # Transfer map for eliminations
    transfer_map = {
        "Liberal Democrat": {"Labour": 0.3, "Conservative": 0.1, "Green": 0.6},
        "Green": {"Labour": 0.7, "Conservative": 0.1, "Exhausted": 0.2}, # Exhausted is handled automatically if sum < 1, but explicit is fine
        "Reform UK": {"Conservative": 0.8, "Labour": 0.1},
    }
    
    print("Initial Votes:")
    for k, v in first_prefs.items():
        print(f"{k}: {v}")

    # Run the simulation
    rounds_df, winner, nrounds = simulate_rcv(first_prefs, transfer_map, sleep=0.2, verbose=True)

    # Pretty table
    print("\nFinal RCV Rounds:")
    print(tabulate(rounds_df.round(1), headers="keys", tablefmt="fancy_grid"))

    print(f"\nWinner: {winner} in {nrounds} rounds")

if __name__ == "__main__":
    run_simulation()
