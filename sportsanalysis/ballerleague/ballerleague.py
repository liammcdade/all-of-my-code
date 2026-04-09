import math
from collections import defaultdict
import numpy as np
import pandas as pd
import random
from tqdm import tqdm

# =========================
# TEAM RATINGS
# =========================

teams = defaultdict(lambda: {
    "result_elo": 1500.0,
    "attack_elo": 1500.0,
    "defence_elo": 1500.0,
    "points": 0,
    "gf": 0,
    "ga": 0,
    "gd": 0
})

# =========================
# SETTINGS
# =========================

RESULT_K = 38  # Larger K for volatility
ATTACK_K = 20
DEFENCE_K = 20
BASE_GOALS = 3.1  # Higher base for indoor scoring
HOME_ADVANTAGE = 0   # set to 50 if home advantage matters
REGRESSION_FACTOR = 0.01  # regression toward mean

# =========================
# FUNCTIONS
# =========================

def expected_result(team_elo, opp_elo):
    return 1 / (1 + 10 ** ((opp_elo - team_elo) / 400))

def expected_goals(attack_elo, opp_defence_elo):
    return BASE_GOALS * (10 ** ((attack_elo - opp_defence_elo) / 400))

def goal_multiplier(goal_diff):
    if goal_diff <= 0:
        return 1
    mult = 1 + 0.12 * (goal_diff - 1)
    return min(mult, 1.5)

def update_match(teams_dict, team1, team2, goals1, goals2):
    t1 = teams_dict[team1]
    t2 = teams_dict[team2]

    # -------------------------
    # POINTS AND STATS
    # -------------------------
    t1["gf"] += goals1
    t1["ga"] += goals2
    t1["gd"] = t1["gf"] - t1["ga"]
    t2["gf"] += goals2
    t2["ga"] += goals1
    t2["gd"] = t2["gf"] - t2["ga"]

    if goals1 > goals2:
        t1["points"] += 3
    elif goals1 < goals2:
        t2["points"] += 3
    else:
        t1["points"] += 1
        t2["points"] += 1

    # -------------------------
    # RESULT ELO
    # -------------------------
    exp1 = expected_result(t1["result_elo"] + HOME_ADVANTAGE, t2["result_elo"])
    exp2 = 1 - exp1

    if goals1 > goals2:
        score1, score2 = 1, 0
    elif goals1 < goals2:
        score1, score2 = 0, 1
    else:
        score1, score2 = 0.5, 0.5

    gd = abs(goals1 - goals2)
    mult = goal_multiplier(gd)

    t1["result_elo"] += RESULT_K * mult * (score1 - exp1)
    t2["result_elo"] += RESULT_K * mult * (score2 - exp2)

    # -------------------------
    # EXPECTED GOALS
    # -------------------------
    eg1 = expected_goals(t1["attack_elo"], t2["defence_elo"])
    eg2 = expected_goals(t2["attack_elo"], t1["defence_elo"])

    # -------------------------
    # ATTACK UPDATE
    # -------------------------
    t1["attack_elo"] += ATTACK_K * (goals1 - eg1)
    t2["attack_elo"] += ATTACK_K * (goals2 - eg2)

    # Attacking bonus
    if goals1 >= 5:
        t1["attack_elo"] += 5
    if goals2 >= 5:
        t2["attack_elo"] += 5

    # -------------------------
    # DEFENCE UPDATE
    # -------------------------
    t1["defence_elo"] += DEFENCE_K * (eg2 - goals2)
    t2["defence_elo"] += DEFENCE_K * (eg1 - goals1)

    # Regression toward mean
    for rating in ["result_elo", "attack_elo", "defence_elo"]:
        t1[rating] += REGRESSION_FACTOR * (1500 - t1[rating])
        t2[rating] += REGRESSION_FACTOR * (1500 - t2[rating])

# =========================
# FIXTURE LIST (ALL PLAYED)
# =========================

fixtures = [
    ("SDS FC", "Wembley Rangers AFC", 3, 2),
    ("Deportrio", "Gold Devils FC", 6, 2),
    ("Prime FC", "N5 FC", 7, 3),
    ("Yanited", "VZN FC", 3, 3),
    ("Community FC", "NDL FC", 2, 7),
    ("Rukkas FC", "Clutch FC", 7, 5),
    ("Yanited", "Community FC", 5, 3),
    ("Deportrio", "Clutch FC", 1, 4),
    ("Rukkas FC", "Prime FC", 3, 8),
    ("Wembley Rangers AFC", "NDL FC", 2, 2),
    ("SDS FC", "N5 FC", 2, 1),
    ("Gold Devils FC", "VZN FC", 3, 1),
    ("Wembley Rangers AFC", "VZN FC", 3, 3),
    ("Prime FC", "Clutch FC", 6, 2),
    ("Deportrio", "NDL FC", 3, 6),
    ("Yanited", "Rukkas FC", 2, 1),
    ("Gold Devils FC", "N5 FC", 3, 5),
    ("Community FC", "SDS FC", 3, 7),
    ("Community FC", "VZN FC", 4, 3),
    ("Clutch FC", "SDS FC", 3, 6),
    ("Yanited", "N5 FC", 8, 6),
    ("Gold Devils FC", "Prime FC",  0, 0),
    ("Rukkas FC", "NDL FC", 0, 0),
    ("Deportrio", "Wembley Rangers AFC", 0, 0),
]

# =========================
# TEAMS LIST
# =========================

teams_list = ["SDS FC", "Wembley Rangers AFC", "Deportrio", "Gold Devils FC", "Prime FC", "N5 FC", "Yanited", "VZN FC", "Community FC", "NDL FC", "Rukkas FC", "Clutch FC"]

# =========================
# RUN PLAYED MATCHES
# =========================

for match in fixtures:
    update_match(teams, *match)

# =========================
# GENERATE REMAINING FIXTURES
# =========================

played_pairs = set()
for t1, t2, _, _ in fixtures:
    played_pairs.add(tuple(sorted([t1, t2])))

remaining_fixtures = []
for i in range(len(teams_list)):
    for j in range(i+1, len(teams_list)):
        pair = tuple(sorted([teams_list[i], teams_list[j]]))
        if pair not in played_pairs:
            remaining_fixtures.append((teams_list[i], teams_list[j]))

# =========================
# SIMULATE PLAYOFF MATCH
# =========================

def simulate_playoff_match(team1, team2):
    eg1 = expected_goals(sim_teams[team1]["attack_elo"], sim_teams[team2]["defence_elo"])
    eg2 = expected_goals(sim_teams[team2]["attack_elo"], sim_teams[team1]["defence_elo"])

    eg1 *= np.random.uniform(0.82, 1.18)
    eg2 *= np.random.uniform(0.82, 1.18)

    eg1 = min(eg1, 15)
    eg2 = min(eg2, 15)

    if np.random.random() < 0.7:
        g1 = np.random.poisson(eg1)
        g2 = np.random.poisson(eg2)
    else:
        boosted_eg1 = min(eg1 * 1.5, 15)
        boosted_eg2 = min(eg2 * 1.5, 15)
        g1 = np.random.poisson(boosted_eg1)
        g2 = np.random.poisson(boosted_eg2)
        if np.random.random() < 0.5:
            g1 += 2
        else:
            g2 += 2

    if np.random.random() < 0.25:
        if np.random.random() < 0.5:
            g1, g2 = g2, g1
        else:
            g1 += np.random.randint(1, 3)
            g2 += np.random.randint(1, 3)

    if g1 > g2:
        return team1
    elif g2 > g1:
        return team2
    else:
        return random.choice([team1, team2])

# =========================
# MONTE CARLO
# =========================

num_sim = 10000

position_counts = {team: {pos: 0 for pos in range(1, 13)} for team in teams_list}
points_lists = {team: [] for team in teams_list}
gd_lists = {team: [] for team in teams_list}
match_predictions = {match: {"scores": [], "home_win": 0, "draw": 0, "away_win": 0} for match in remaining_fixtures}
playoff_title = defaultdict(int)
top4_qualify = defaultdict(int)

for sim in tqdm(range(num_sim), desc="Simulating", unit="sim"):
    # Copy current teams
    sim_teams = {k: v.copy() for k, v in teams.items()}
    
    # Simulate remaining matches
    for t1, t2 in remaining_fixtures:
        eg1 = expected_goals(sim_teams[t1]["attack_elo"], sim_teams[t2]["defence_elo"])
        eg2 = expected_goals(sim_teams[t2]["attack_elo"], sim_teams[t1]["defence_elo"])

        # Indoor volatility multiplier
        eg1 *= np.random.uniform(0.82, 1.18)
        eg2 *= np.random.uniform(0.82, 1.18)

        # Cap expected goals to avoid Poisson overflow
        eg1 = min(eg1, 15)
        eg2 = min(eg2, 15)

        # Score generation: 70% Poisson, 30% high-volatility override
        if np.random.random() < 0.7:
            goals1 = np.random.poisson(eg1)
            goals2 = np.random.poisson(eg2)
        else:
            # High-volatility override: boost lambda and add extras
            boosted_eg1 = min(eg1 * 1.5, 15)
            boosted_eg2 = min(eg2 * 1.5, 15)
            goals1 = np.random.poisson(boosted_eg1)
            goals2 = np.random.poisson(boosted_eg2)
            # Add +2 to one team randomly for late twist
            if np.random.random() < 0.5:
                goals1 += 2
            else:
                goals2 += 2

        # Additional volatility event in 25% of matches
        if np.random.random() < 0.25:
            # Rule twist: force upset or extra chaos
            if np.random.random() < 0.5:
                # Swap goals for upset
                goals1, goals2 = goals2, goals1
            else:
                # Add extra goals
                goals1 += np.random.randint(1, 3)
                goals2 += np.random.randint(1, 3)

        update_match(sim_teams, t1, t2, goals1, goals2)
        
        # Record for predictions
        match_predictions[(t1, t2)]["scores"].append((goals1, goals2))
        if goals1 > goals2:
            match_predictions[(t1, t2)]["home_win"] += 1
        elif goals1 < goals2:
            match_predictions[(t1, t2)]["away_win"] += 1
        else:
            match_predictions[(t1, t2)]["draw"] += 1
    
    # Calculate final standings
    def get_sort_key(team):
        t = sim_teams[team]
        return (t["points"], t["gd"], t["gf"])
    
    sorted_teams_sim = sorted(teams_list, key=get_sort_key, reverse=True)
    
    for pos, team in enumerate(sorted_teams_sim, 1):
        position_counts[team][pos] += 1
        points_lists[team].append(sim_teams[team]["points"])
        gd_lists[team].append(sim_teams[team]["gd"])

        if pos <= 4:
            top4_qualify[team] += 1

    # Simulate playoffs
    top4 = sorted_teams_sim[:4]
    random.shuffle(top4)
    semi1_winner = simulate_playoff_match(top4[0], top4[1])
    semi2_winner = simulate_playoff_match(top4[2], top4[3])
    champ = simulate_playoff_match(semi1_winner, semi2_winner)
    playoff_title[champ] += 1

# Normalize predictions
for match in match_predictions:
    pred = match_predictions[match]
    pred["home_win"] /= num_sim
    pred["draw"] /= num_sim
    pred["away_win"] /= num_sim
    from collections import Counter
    score_counts = Counter(pred["scores"])
    pred["most_likely_score"] = score_counts.most_common(1)[0][0]
    pred["upset_prob"] = pred["away_win"] if expected_result(teams[match[0]]["result_elo"], teams[match[1]]["result_elo"]) < 0.5 else 0

# =========================
# OUTPUT
# =========================

print(" ")
print(" ")



print("\nPLAYOFF TITLE CHANCES (%)\n")
for team in sorted(teams_list, key=lambda t: playoff_title[t], reverse=True):
    prob = playoff_title[team] / num_sim * 100
    print(f"{team}: {prob:.1f}%")

print("\nTOP 4 QUALIFICATION CHANCES (%)\n")
for team in sorted(teams_list, key=lambda t: top4_qualify[t], reverse=True):
    prob = top4_qualify[team] / num_sim * 100
    print(f"{team}: {prob:.1f}%")

