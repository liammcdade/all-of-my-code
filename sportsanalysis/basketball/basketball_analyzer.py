import random
import copy
from collections import Counter
from tqdm import tqdm

# =========================
# TEAM DATA
# =========================
teams = {
    "Thunder": {"elo": 1764, "conf": "W"},
    "Spurs": {"elo": 1728, "conf": "W"},
    "Celtics": {"elo": 1640, "conf": "E"},
    "Lakers": {"elo": 1641, "conf": "W"},
    "Pistons": {"elo": 1657, "conf": "E"},
    "Nuggets": {"elo": 1634, "conf": "W"},
    "Cavaliers": {"elo": 1611, "conf": "E"},
    "Knicks": {"elo": 1639, "conf": "E"},
    "Timberwolves": {"elo": 1613, "conf": "W"},
    "Hawks": {"elo": 1561, "conf": "E"},
    "Magic": {"elo": 1554, "conf": "E"},
    "Blazers": {"elo": 1532, "conf": "W"},
    "76ers": {"elo": 1575, "conf": "E"},
    "Raptors": {"elo": 1531, "conf": "E"},
    "Suns": {"elo": 1497, "conf": "W"},
    "Rockets": {"elo": 1590, "conf": "W"},
}

# =========================
# CURRENT SERIES
# =========================
second_round = [
    # East
    ["Pistons", "Cavaliers", 0, 0],
    ["Knicks", "76ers", 0, 0],
    
    # West
    ["Thunder", "Lakers", 0, 0],
    ["Timberwolves", "Spurs", 0, 0],
]


# =========================
# FUNCTIONS
# =========================
def win_prob(a, b, teams_dict, home=None):
    eloA = teams_dict[a]["elo"]
    eloB = teams_dict[b]["elo"]
    if home == a:
        eloA += 100
    elif home == b:
        eloB += 100
    return 1 / (1 + 10 ** ((eloB - eloA) / 400))

def simulate_game(a, b, teams_dict, home=None):
    prob_a = win_prob(a, b, teams_dict, home)
    winner = a if random.random() < prob_a else b
    # Update Elo dynamically
    k = 32
    expected_a = prob_a
    expected_b = 1 - expected_a
    actual_a = 1 if winner == a else 0
    actual_b = 1 - actual_a
    teams_dict[a]["elo"] += k * (actual_a - expected_a)
    teams_dict[b]["elo"] += k * (actual_b - expected_b)
    return winner

def simulate_series(a, b, teams_dict, wa=0, wb=0, higher=None):
    if higher is None:
        higher = a
    game_num = wa + wb
    while wa < 4 and wb < 4:
        game_num += 1
        home = higher if game_num in [1, 2, 5, 7] else b
        winner = simulate_game(a, b, teams_dict, home)
        if winner == a:
            wa += 1
        else:
            wb += 1
    return a if wa == 4 else b

def simulate_round(series, teams_dict):
    winners = []
    for a, b, wa, wb in series:
        higher = a  # assuming a is higher seed
        winners.append(simulate_series(a, b, teams_dict, wa, wb, higher))
    return winners

def next_round(ts):
    # Reseed: 1vs8 winner vs 4vs5 winner, 2vs7 winner vs 3vs6 winner
    return [[ts[0], ts[3], 0, 0], [ts[1], ts[2], 0, 0]]

def simulate_playoffs():
    teams_dict = copy.deepcopy(teams)

    # Conference semifinals
    r2 = simulate_round(second_round, teams_dict)

    east = [t for t in r2 if teams_dict[t]["conf"] == "E"]
    west = [t for t in r2 if teams_dict[t]["conf"] == "W"]

    # Conference finals
    east_final = simulate_series(east[0], east[1], teams_dict)
    west_final = simulate_series(west[0], west[1], teams_dict)

    # NBA Finals
    champion = simulate_series(east_final, west_final, teams_dict)

    return champion
# =========================
# MONTE CARLO SIMULATION
# =========================
N = 10000
results = Counter()

for _ in tqdm(range(N)):
    champ = simulate_playoffs()
    results[champ] += 1

# =========================
# OUTPUT PROBABILITIES
# =========================
print("\n=== Championship Probabilities ===\n")

for team, count in results.most_common():
    prob = (count / N) * 100
    print(f"{team:15s}: {prob:6.2f}%")

