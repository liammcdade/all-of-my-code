# electoral_tie_calculator.py
# Count number of 269–269 tie scenarios using DP
# Includes Maine and Nebraska district splits

from collections import defaultdict
import time

def calculate_ties():
    print("--- Electoral College Tie Calculator ---")
    start_time = time.time()
    
    # Electoral votes per unit (states, DC, ME districts, NE districts)
    evs = {
        "AL":9,"AK":3,"AZ":11,"AR":6,"CA":54,"CO":10,"CT":7,"DE":3,"DC":3,"FL":30,"GA":16,
        "HI":4,"ID":4,"IL":19,"IN":11,"IA":6,"KS":6,"KY":8,"LA":8,
        "ME-AL":2,"ME-1":1,"ME-2":1,
        "MD":10,"MA":11,"MI":15,"MN":10,"MS":6,"MO":10,"MT":4,
        "NE-AL":2,"NE-1":1,"NE-2":1,"NE-3":1,
        "NV":6,"NH":4,"NJ":14,"NM":5,"NY":28,"NC":16,"ND":3,"OH":17,
        "OK":7,"OR":8,"PA":19,"RI":4,"SC":9,"SD":3,"TN":11,"TX":40,
        "UT":6,"VT":3,"VA":13,"WA":12,"WV":4,"WI":10,"WY":3
    }

    units = list(evs.items())
    total_ev = sum(evs.values())
    print(f"Total electoral votes (with ME/NE splits): {total_ev}")

    target = 269

    # DP table: sum -> number of ways
    dp = defaultdict(int)
    dp[0] = 1

    checked = 0
    print("Calculating...")
    for i, (name, val) in enumerate(units, 1):
        new_dp = defaultdict(int, dp)  # copy existing
        for s, cnt in dp.items():
            new_dp[s + val] += cnt
        dp = new_dp
        checked += 1
        # if checked % 10 == 0 or checked == len(units):
        #     print(f"Processed {checked}/{len(units)} units...")

    solutions = dp[target]

    print(f"Total tie scenarios (269-269): {solutions:,}")
    print(f"Calculation took {time.time() - start_time:.2f} seconds")

if __name__ == "__main__":
    calculate_ties()
