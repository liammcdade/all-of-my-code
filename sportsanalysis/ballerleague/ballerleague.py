import math
from collections import defaultdict

# =========================
# TEAM RATINGS
# =========================

teams = defaultdict(lambda: {
    "result_elo": 1500.0,
    "attack_elo": 1500.0,
    "defence_elo": 1500.0
})

# =========================
# SETTINGS
# =========================

RESULT_K = 30
ATTACK_K = 20
DEFENCE_K = 20
BASE_GOALS = 2.5
HOME_ADVANTAGE = 0   # set to 50 if home advantage matters

# =========================
# FUNCTIONS
# =========================

def expected_result(team_elo, opp_elo):
    return 1 / (1 + 10 ** ((opp_elo - team_elo) / 400))

def expected_goals(attack_elo, opp_defence_elo):
    return BASE_GOALS * (10 ** ((attack_elo - opp_defence_elo) / 400))

def goal_multiplier(goal_diff):
    if goal_diff == 0:
        return 1
    return min(math.log(goal_diff + 1), 2)

def update_match(team1, team2, goals1, goals2):
    t1 = teams[team1]
    t2 = teams[team2]

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

    # -------------------------
    # DEFENCE UPDATE
    # -------------------------
    t1["defence_elo"] += DEFENCE_K * (eg2 - goals2)
    t2["defence_elo"] += DEFENCE_K * (eg1 - goals1)

# =========================
# FIXTURE LIST
# =========================

fixtures = [
    ("SDS FC", "Wembley Rangers AFC", 3, 2),
    ("Deportrio", "Gold Devils FC", 6, 2),
    ("Prime FC", "N5 FC", 6, 3),

    # add future matches below:
    # ("Yanited", "VZN FC", goals1, goals2),
    # ("Community FC", "NDL FC", goals1, goals2),
]

# =========================
# RUN ALL MATCHES
# =========================

for match in fixtures:
    update_match(*match)

# =========================
# POWER TABLE
# =========================

def total_power(team):
    t = teams[team]
    return t["result_elo"] + (t["attack_elo"] + t["defence_elo"]) / 2

# =========================
# SORTED TABLE
# =========================

sorted_teams = sorted(
    teams.keys(),
    key=lambda x: total_power(x),
    reverse=True
)

print("\nBALLER LEAGUE POWER TABLE\n")

for i, team in enumerate(sorted_teams, 1):
    t = teams[team]
    print(f"{i}. {team}")
    print(f"   Result Elo : {t['result_elo']:.2f}")
    print(f"   Attack Elo : {t['attack_elo']:.2f}")
    print(f"   Defence Elo: {t['defence_elo']:.2f}")
    print(f"   Total Power: {total_power(team):.2f}")
    print("-" * 30)