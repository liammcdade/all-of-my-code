import random
import math
import numpy as np
from collections import defaultdict
from tqdm import tqdm

# ====================== ELO RATINGS ======================
elo = {
    "Arsenal": 2061,
    "Man City": 1941,
    "Liverpool": 1936,
    "Chelsea": 1885,
    "Man Utd": 1881,
    "Aston Villa": 1879,
    "Newcastle": 1853,
    "Brighton": 1834,
    "Brentford": 1833,
    "Bournemouth": 1821,
    "Everton": 1815,
    "Fulham": 1795,
    "Crystal Palace": 1794,
    "Tottenham": 1769,
    "Leeds": 1764,
    "Nott'm Forest": 1769,
    "West Ham": 1746,
    "Wolves": 1701,
    "Sunderland": 1691,
    "Burnley": 1683,
}

# ====================== CURRENT TABLE ======================
current = {
    "Arsenal":       {"Pts":70,"GF":61,"GA":22},
    "Man City":      {"Pts":61,"GF":60,"GA":28},
    "Man Utd":       {"Pts":55,"GF":54,"GA":41},
    "Aston Villa":   {"Pts":51,"GF":40,"GA":37},
    "Liverpool":     {"Pts":49,"GF":50,"GA":42},
    "Chelsea":       {"Pts":48,"GF":53,"GA":33},
    "Brentford":     {"Pts":46,"GF":46,"GA":42},
    "Everton":       {"Pts":46,"GF":37,"GA":35},
    "Newcastle":     {"Pts":42,"GF":43,"GA":43},
    "Bournemouth":   {"Pts":41,"GF":44,"GA":46},
    "Fulham":        {"Pts":44,"GF":43,"GA":41},
    "Brighton":      {"Pts":43,"GF":39,"GA":36},
    "Sunderland":    {"Pts":40,"GF":30,"GA":35},
    "Crystal Palace":{"Pts":39,"GF":33,"GA":35},
    "Leeds":         {"Pts":33,"GF":37,"GA":48},
    "Tottenham":     {"Pts":30,"GF":40,"GA":47},
    "Nott'm Forest": {"Pts":29,"GF":28,"GA":43},
    "West Ham":      {"Pts":29,"GF":36,"GA":55},
    "Burnley":       {"Pts":20,"GF":32,"GA":58},
    "Wolves":        {"Pts":17,"GF":24,"GA":54},
}

# ====================== FIXTURES ======================
fixtures = [
    
    
    ("Newcastle","Sunderland"), ("Aston Villa","West Ham"), ("Tottenham","Nott'm Forest"),
    ("Man City", "Crystal Palace"),

    ("West Ham","Wolves"), ("Arsenal","Bournemouth"), ("Brentford","Everton"),
    ("Burnley","Brighton"), ("Crystal Palace","Newcastle"), ("Nott'm Forest","Aston Villa"),
    ("Liverpool","Fulham"), ("Sunderland","Tottenham"), ("Chelsea","Man City"),
    ("Man Utd","Leeds"),

    ("Brentford","Fulham"), ("Aston Villa","Sunderland"), ("Leeds","Wolves"),
    ("Newcastle","Bournemouth"), ("Nott'm Forest","Burnley"), ("Tottenham","Brighton"),
    ("Chelsea","Man Utd"), ("Everton","Liverpool"), ("Man City","Arsenal"),
    ("Crystal Palace","West Ham"),

    ("Sunderland","Nott'm Forest"), ("Fulham","Aston Villa"), ("Bournemouth","Leeds"),
    ("Liverpool","Crystal Palace"), ("West Ham","Everton"), ("Wolves","Tottenham"),
    ("Arsenal","Newcastle"), ("Burnley","Man City"), ("Brighton","Chelsea"),
    ("Man Utd","Brentford"),

    ("Arsenal","Fulham"), ("Aston Villa","Tottenham"), ("Bournemouth","Crystal Palace"),
    ("Brentford","West Ham"), ("Chelsea","Nott'm Forest"), ("Everton","Man City"),
    ("Leeds","Burnley"), ("Man Utd","Liverpool"), ("Newcastle","Brighton"),
    ("Wolves","Sunderland"),

    ("Brighton","Wolves"), ("Burnley","Aston Villa"), ("Crystal Palace","Everton"),
    ("Fulham","Bournemouth"), ("Liverpool","Chelsea"), ("Man City","Brentford"),
    ("Nott'm Forest","Newcastle"), ("Sunderland","Man Utd"), ("Tottenham","Leeds"),
    ("West Ham","Arsenal"),

    ("Arsenal","Burnley"), ("Aston Villa","Liverpool"), ("Bournemouth","Man City"),
    ("Brentford","Crystal Palace"), ("Chelsea","Tottenham"), ("Everton","Sunderland"),
    ("Leeds","Brighton"), ("Man Utd","Nott'm Forest"), ("Newcastle","West Ham"),
    ("Wolves","Fulham"),

    ("Brighton","Man Utd"), ("Burnley","Wolves"), ("Crystal Palace","Arsenal"),
    ("Fulham","Newcastle"), ("Liverpool","Brentford"), ("Man City","Aston Villa"),
    ("Nott'm Forest","Bournemouth"), ("Sunderland","Chelsea"), ("Tottenham","Everton"),
    ("West Ham","Leeds"),
]

# ====================== MODEL PARAMETERS ======================
HOME_ADVANTAGE = 65
DRAW_BASE = 0.255
DRAW_WIDTH = 230

# ====================== MATCH ENGINE ======================
def simulate_match(home, away):
    diff = elo[home] - elo[away] + HOME_ADVANTAGE

    p_home_base = 1 / (1 + 10 ** (-diff / 400))
    p_draw = DRAW_BASE * math.exp(-(diff**2)/(2 * DRAW_WIDTH**2))

    p_home = p_home_base * (1 - p_draw)
    p_away = (1 - p_home_base) * (1 - p_draw)

    r = random.random()

    home_xg = max(0.25, 1.45 + diff / 500)
    away_xg = max(0.25, 1.10 - diff / 550)

    if r < p_home:
        while True:
            hg = np.random.poisson(home_xg)
            ag = np.random.poisson(away_xg)
            if hg > ag:
                return hg, ag

    elif r < p_home + p_draw:
        g = np.random.poisson((home_xg + away_xg) / 2)
        return g, g

    else:
        while True:
            hg = np.random.poisson(home_xg)
            ag = np.random.poisson(away_xg)
            if ag > hg:
                return hg, ag

# ====================== APPLY RESULT ======================
def apply_result(table, home, away, hg, ag):
    table[home]["GF"] += hg
    table[home]["GA"] += ag

    table[away]["GF"] += ag
    table[away]["GA"] += hg

    if hg > ag:
        table[home]["Pts"] += 3
    elif ag > hg:
        table[away]["Pts"] += 3
    else:
        table[home]["Pts"] += 1
        table[away]["Pts"] += 1

# ====================== MONTE CARLO ======================
sims = 50000

title = defaultdict(int)
top4 = defaultdict(int)
fifth = defaultdict(int)
releg = defaultdict(int)
avg_points = defaultdict(list)

print(f"Running {sims:,} simulations...")

for _ in tqdm(range(sims), desc="Simulating", unit="sim"):

    table = {
        t: {"Pts": current[t]["Pts"], "GF": current[t]["GF"], "GA": current[t]["GA"]}
        for t in current
    }

    for home, away in fixtures:
        hg, ag = simulate_match(home, away)
        apply_result(table, home, away, hg, ag)

    ranking = sorted(
        table.items(),
        key=lambda x: (
            x[1]["Pts"],
            x[1]["GF"] - x[1]["GA"],
            x[1]["GF"]
        ),
        reverse=True
    )

    for pos, (team, data) in enumerate(ranking, 1):
        avg_points[team].append(data["Pts"])

        if pos == 1:
            title[team] += 1
        if pos <= 4:
            top4[team] += 1
        if pos == 5:
            fifth[team] += 1
        if pos >= 18:
            releg[team] += 1

# ====================== OUTPUT ======================
print(f"{'Team':<15}{'AvgPts':<8}{'Title%':<8}{'Top4%':<8}{'5th%':<8}{'Releg%'}")
print("-" * 65)

for team in sorted(current.keys(), key=lambda x: sum(avg_points[x]) / sims, reverse=True):
    print(
        f"{team:<15}"
        f"{sum(avg_points[team])/sims:<8.2f}"
        f"{title[team]/sims*100:<8.2f}"
        f"{top4[team]/sims*100:<8.2f}"
        f"{fifth[team]/sims*100:<8.2f}"
        f"{releg[team]/sims*100:.2f}"
    )