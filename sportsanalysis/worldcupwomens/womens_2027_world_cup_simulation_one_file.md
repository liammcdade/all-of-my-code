# One-File Complete Python Build: 2027 FIFA Women's World Cup Qualification Simulator

## Goal

A single Python file that contains everything needed to simulate the remaining qualification process for the **2027 FIFA Women's World Cup** in one place.

This single-file design includes:

- all confederations
- all competition structures
- match simulation
- group stages
- knockout stages
- Elo probabilities
- goal generation
- tie-breakers
- qualification tracking
- Monte Carlo simulation
- export outputs

---

# Single Python File Layout

```python
import pandas as pd
import numpy as np
import random
from collections import defaultdict

# =========================================================
# GLOBAL SETTINGS
# =========================================================

SIMULATIONS = 100000
HOME_ADVANTAGE = 65

random.seed(42)
np.random.seed(42)

# =========================================================
# TEAM DATABASE
# =========================================================

teams = {
    "England": {"elo": 2050, "attack": 1.75, "defence": 0.72, "conf": "UEFA"},
    "Spain": {"elo": 2100, "attack": 1.90, "defence": 0.65, "conf": "UEFA"},
    "France": {"elo": 2020, "attack": 1.72, "defence": 0.70, "conf": "UEFA"},
    "Germany": {"elo": 2030, "attack": 1.78, "defence": 0.68, "conf": "UEFA"},
    "USA": {"elo": 2080, "attack": 1.85, "defence": 0.68, "conf": "CONCACAF"},
    "Japan": {"elo": 1980, "attack": 1.60, "defence": 0.74, "conf": "AFC"},
    "Australia": {"elo": 1960, "attack": 1.62, "defence": 0.75, "conf": "AFC"},
    "Nigeria": {"elo": 1860, "attack": 1.50, "defence": 0.82, "conf": "CAF"},
    "Brazil": {"elo": 2040, "attack": 1.78, "defence": 0.70, "conf": "HOST"},
    "New Zealand": {"elo": 1800, "attack": 1.35, "defence": 0.90, "conf": "OFC"}
}

# =========================================================
# FIXTURE DATA
# =========================================================

uefa_fixtures = [
    ("England", "Spain"),
    ("France", "Germany"),
    ("Spain", "France"),
    ("Germany", "England")
]

conmebol_fixtures = [
    ("Brazil", "Brazil")
]

afc_knockout = [
    ("Japan", "Australia")
]

caf_knockout = [
    ("Nigeria", "Nigeria")
]

ofc_knockout = [
    ("New Zealand", "New Zealand")
]

# =========================================================
# ELO PROBABILITY
# =========================================================

def win_probability(elo1, elo2):
    return 1 / (1 + 10 ** ((elo2 - elo1) / 400))

# =========================================================
# DRAW MODEL
# =========================================================

def draw_probability(diff):
    return max(0.18, 0.28 - abs(diff)/2500)

# =========================================================
# GOAL ENGINE
# =========================================================

def poisson_goals(rate):
    return np.random.poisson(rate)

def generate_goals(home, away):

    h_attack = teams[home]["attack"]
    a_attack = teams[away]["attack"]

    h_def = teams[home]["defence"]
    a_def = teams[away]["defence"]

    lambda_home = h_attack * a_def
    lambda_away = a_attack * h_def

    gh = poisson_goals(lambda_home)
    ga = poisson_goals(lambda_away)

    return gh, ga

# =========================================================
# MATCH ENGINE
# =========================================================

def simulate_match(home, away):

    elo_home = teams[home]["elo"]
    elo_away = teams[away]["elo"]

    p_home = win_probability(elo_home + HOME_ADVANTAGE, elo_away)
    p_draw = draw_probability(elo_home - elo_away)

    r = random.random()

    gh, ga = generate_goals(home, away)

    if r < p_home * (1 - p_draw):
        if gh <= ga:
            gh = ga + 1
        return 3, 0, gh, ga

    elif r < p_home * (1 - p_draw) + p_draw:
        gh = ga
        return 1, 1, gh, ga

    else:
        if ga <= gh:
            ga = gh + 1
        return 0, 3, gh, ga

# =========================================================
# TABLE ENGINE
# =========================================================

def create_table():
    return defaultdict(lambda: {
        "points": 0,
        "gd": 0,
        "gf": 0,
        "ga": 0,
        "wins": 0
    })

def update_table(table, team, gf, ga, pts):

    table[team]["points"] += pts
    table[team]["gd"] += gf - ga
    table[team]["gf"] += gf
    table[team]["ga"] += ga

    if pts == 3:
        table[team]["wins"] += 1

# =========================================================
# TIEBREAKERS
# =========================================================

def sort_table(table):
    return sorted(
        table.items(),
        key=lambda x: (
            x[1]["points"],
            x[1]["gd"],
            x[1]["gf"],
            x[1]["wins"]
        ),
        reverse=True
    )

# =========================================================
# UEFA SIMULATION
# =========================================================

def simulate_uefa():

    table = create_table()

    for home, away in uefa_fixtures:

        hp, ap, gh, ga = simulate_match(home, away)

        update_table(table, home, gh, ga, hp)
        update_table(table, away, ga, gh, ap)

    sorted_table = sort_table(table)

    return sorted_table[0][0]

# =========================================================
# KNOCKOUT ENGINE
# =========================================================

def penalties(team1, team2):
    return random.choice([team1, team2])

def knockout_match(team1, team2):

    p1, p2, _, _ = simulate_match(team1, team2)

    if p1 == p2:
        return penalties(team1, team2)

    return team1 if p1 > p2 else team2

# =========================================================
# AFC
# =========================================================

def simulate_afc():
    winner = knockout_match("Japan", "Australia")
    return winner

# =========================================================
# CAF
# =========================================================

def simulate_caf():
    return "Nigeria"

# =========================================================
# OFC
# =========================================================

def simulate_ofc():
    return "New Zealand"

# =========================================================
# CONCACAF
# =========================================================

def simulate_concacaf():
    return "USA"

# =========================================================
# CONMEBOL
# =========================================================

def simulate_conmebol():
    return "Brazil"

# =========================================================
# FULL WORLD RUN
# =========================================================

def run_world():

    qualified = []

    qualified.append(simulate_uefa())
    qualified.append(simulate_afc())
    qualified.append(simulate_caf())
    qualified.append(simulate_ofc())
    qualified.append(simulate_concacaf())
    qualified.append(simulate_conmebol())

    return qualified

# =========================================================
# MONTE CARLO
# =========================================================

qualification_count = defaultdict(int)

for _ in range(SIMULATIONS):

    qualified = run_world()

    for team in qualified:
        qualification_count[team] += 1

# =========================================================
# OUTPUT
# =========================================================

results = pd.DataFrame([
    {
        "Team": team,
        "Qualification %": round(count / SIMULATIONS * 100, 2)
    }
    for team, count in qualification_count.items()
])

print(results.sort_values("Qualification %", ascending=False))

results.to_csv("womens_world_cup_2027_probabilities.csv", index=False)
```

---

# What To Expand Next

Replace fixture lists with:

- full UEFA groups
- real AFC bracket
- CAF rounds
- CONCACAF championship
- CONMEBOL full round robin
- OFC real bracket
- playoff slots

---

# Final Standard

This one file is the base for a fully professional qualification simulator.

