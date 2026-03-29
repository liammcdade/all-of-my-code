import random
import math
from collections import defaultdict
from tqdm import tqdm

# ====================== UPDATED 2026 LIVE ELO ======================
teams_elo = {
    "Duke": 2200,
    "Arizona": 2188,
    "Michigan": 2176,
    "Florida": 2168,
    "Houston": 2160,
    "UConn": 2135,
    "Iowa State": 2118,
    "Purdue": 2105,
    "Michigan State": 2098,
    "Kansas": 2088,
    "Gonzaga": 2075,
    "Nebraska": 2068,
    "Illinois": 2062,
    "Arkansas": 2054,
    "Alabama": 2048,
    "St. John's": 2040,
    "Vanderbilt": 2028,
    "Louisville": 2018,
    "TCU": 2008,
    "High Point": 1960
}

DEFAULT_ELO = 1850

# ====================== LIVE LOCKED RESULTS ======================
games = {
    "East_R64_1": {"team1": "Duke", "team2": "Siena", "winner": "Duke"},
    "East_R64_2": {"team1": "Ohio State", "team2": "TCU", "winner": "TCU"},
    "East_R64_3": {"team1": "St. John's", "team2": "Northern Iowa", "winner": "St. John's"},
    "East_R64_4": {"team1": "Kansas", "team2": "California Baptist", "winner": "Kansas"},
    "East_R64_5": {"team1": "Louisville", "team2": "South Florida", "winner": "Louisville"},
    "East_R64_6": {"team1": "Michigan State", "team2": "North Dakota State", "winner": "Michigan State"},
    "East_R64_7": {"team1": "UCLA", "team2": "UCF", "winner": "UCLA"},
    "East_R64_8": {"team1": "UConn", "team2": "Furman", "winner": "UConn"},

    "South_R64_1": {"team1": "Florida", "team2": "Prairie View A&M", "winner": "Florida"},
    "South_R64_2": {"team1": "Clemson", "team2": "Iowa", "winner": "Iowa"},
    "South_R64_3": {"team1": "Vanderbilt", "team2": "McNeese", "winner": "Vanderbilt"},
    "South_R64_4": {"team1": "Nebraska", "team2": "Troy", "winner": "Nebraska"},
    "South_R64_5": {"team1": "North Carolina", "team2": "VCU", "winner": "VCU"},
    "South_R64_6": {"team1": "Illinois", "team2": "Penn", "winner": "Illinois"},
    "South_R64_7": {"team1": "Saint Mary's", "team2": "Texas A&M", "winner": "Texas A&M"},
    "South_R64_8": {"team1": "Houston", "team2": "Idaho", "winner": "Houston"},

    "West_R64_1": {"team1": "Arizona", "team2": "Long Island", "winner": "Arizona"},
    "West_R64_2": {"team1": "Villanova", "team2": "Utah State", "winner": "Utah State"},
    "West_R64_3": {"team1": "Wisconsin", "team2": "High Point", "winner": "High Point"},
    "West_R64_4": {"team1": "Arkansas", "team2": "Hawaii", "winner": "Arkansas"},
    "West_R64_5": {"team1": "BYU", "team2": "Texas", "winner": "Texas"},
    "West_R64_6": {"team1": "Gonzaga", "team2": "Kennesaw State", "winner": "Gonzaga"},
    "West_R64_7": {"team1": "Miami (FL)", "team2": "Missouri", "winner": "Miami (FL)"},
    "West_R64_8": {"team1": "Purdue", "team2": "Queens", "winner": "Purdue"},

    "Midwest_R64_1": {"team1": "Michigan", "team2": "Howard", "winner": "Michigan"},
    "Midwest_R64_2": {"team1": "Georgia", "team2": "Saint Louis", "winner": "Saint Louis"},
    "Midwest_R64_3": {"team1": "Texas Tech", "team2": "Akron", "winner": "Texas Tech"},
    "Midwest_R64_4": {"team1": "Alabama", "team2": "Hofstra", "winner": "Alabama"},
    "Midwest_R64_5": {"team1": "Tennessee", "team2": "Miami (OH)", "winner": "Tennessee"},
    "Midwest_R64_6": {"team1": "Virginia", "team2": "Wright State", "winner": "Virginia"},
    "Midwest_R64_7": {"team1": "Kentucky", "team2": "Santa Clara", "winner": "Kentucky"},
    "Midwest_R64_8": {"team1": "Iowa State", "team2": "Tennessee State", "winner": "Iowa State"},
}

# ====================== BRACKET BUILD ======================
def build():
    # EAST
    games["East_R32_1"] = {"team1": "Duke", "team2": "TCU", "winner": "Duke"}
    games["East_R32_2"] = {"team1": "St. John's", "team2": "Kansas", "winner": None}
    games["East_R32_3"] = {"team1": "Louisville", "team2": "Michigan State", "winner": "Michigan State"}
    games["East_R32_4"] = {"team1": "UCLA", "team2": "UConn", "winner": None}

    games["East_S16_1"] = {"team1": "East_R32_1", "team2": "East_R32_2", "winner": None}
    games["East_S16_2"] = {"team1": "East_R32_3", "team2": "East_R32_4", "winner": None}
    games["East_E8_1"] = {"team1": "East_S16_1", "team2": "East_S16_2", "winner": None}

    # SOUTH
    games["South_R32_1"] = {"team1": "Florida", "team2": "Iowa", "winner": None}
    games["South_R32_2"] = {"team1": "Vanderbilt", "team2": "Nebraska", "winner": None}
    games["South_R32_3"] = {"team1": "VCU", "team2": "Illinois", "winner": None}
    games["South_R32_4"] = {"team1": "Texas A&M", "team2": "Houston", "winner": None}

    games["South_S16_1"] = {"team1": "South_R32_1", "team2": "South_R32_2", "winner": None}
    games["South_S16_2"] = {"team1": "South_R32_3", "team2": "South_R32_4", "winner": None}
    games["South_E8_1"] = {"team1": "South_S16_1", "team2": "South_S16_2", "winner": None}

    # WEST
    games["West_R32_1"] = {"team1": "Arizona", "team2": "Utah State", "winner": None}
    games["West_R32_2"] = {"team1": "High Point", "team2": "Arkansas", "winner": None}
    games["West_R32_3"] = {"team1": "Texas", "team2": "Gonzaga", "winner": None}
    games["West_R32_4"] = {"team1": "Miami (FL)", "team2": "Purdue", "winner": None}

    games["West_S16_1"] = {"team1": "West_R32_1", "team2": "West_R32_2", "winner": None}
    games["West_S16_2"] = {"team1": "West_R32_3", "team2": "West_R32_4", "winner": None}
    games["West_E8_1"] = {"team1": "West_S16_1", "team2": "West_S16_2", "winner": None}

    # MIDWEST
    games["Midwest_R32_1"] = {"team1": "Michigan", "team2": "Saint Louis", "winner": None}
    games["Midwest_R32_2"] = {"team1": "Texas Tech", "team2": "Alabama", "winner": None}
    games["Midwest_R32_3"] = {"team1": "Tennessee", "team2": "Virginia", "winner": None}
    games["Midwest_R32_4"] = {"team1": "Kentucky", "team2": "Iowa State", "winner": None}

    games["Midwest_S16_1"] = {"team1": "Midwest_R32_1", "team2": "Midwest_R32_2", "winner": None}
    games["Midwest_S16_2"] = {"team1": "Midwest_R32_3", "team2": "Midwest_R32_4", "winner": None}
    games["Midwest_E8_1"] = {"team1": "Midwest_S16_1", "team2": "Midwest_S16_2", "winner": None}

    # FINAL FOUR
    games["FF_Semi1"] = {"team1": "East_E8_1", "team2": "West_E8_1", "winner": None}
    games["FF_Semi2"] = {"team1": "South_E8_1", "team2": "Midwest_E8_1", "winner": None}

    # TITLE
    games["Champion"] = {"team1": "FF_Semi1", "team2": "FF_Semi2", "winner": None}

# ====================== SIMULATION ======================
def elo(team):
    return teams_elo.get(team, DEFAULT_ELO)

def prob(a, b):
    return 1 / (1 + 10 ** (-(elo(a)-elo(b))/400))

def resolve(k):
    g = games[k]

    if g["winner"] is not None:
        return g["winner"]

    a = resolve(g["team1"]) if g["team1"] in games else g["team1"]
    b = resolve(g["team2"]) if g["team2"] in games else g["team2"]

    g["winner"] = a if random.random() < prob(a,b) else b
    return g["winner"]

LOCKED = {k for k,v in games.items() if v["winner"] is not None}

def reset():
    for k in games:
        if k not in LOCKED:
            games[k]["winner"] = None

def run(n=10000):
    build()
    count = defaultdict(int)

    for _ in tqdm(range(n)):
        reset()
        champ = resolve("Champion")
        count[champ] += 1

    print("\nLIVE TITLE ODDS")
    for t,c in sorted(count.items(), key=lambda x:x[1], reverse=True)[:]:
        print(f"{t:<20} {c/n*100:.2f}%")

run(10000)