import random
from collections import defaultdict
from tqdm import tqdm

# =========================
# CONFIG
# =========================
N_SIMS = 10000
HOME_ADV = 65
ELO_SCALE = 400
K = 25
PARITY_RESET_FACTOR = 0.33
LEAGUE_AVERAGE_ELO = 1500

# =========================
# INITIAL ELO
# =========================
ELO = {
    # AFC East
    "Buffalo Bills": 1810,
    "Miami Dolphins": 1620,
    "New England Patriots": 1540,
    "New York Jets": 1500,

    # AFC North
    "Baltimore Ravens": 1860,
    "Cincinnati Bengals": 1780,
    "Cleveland Browns": 1510,
    "Pittsburgh Steelers": 1660,

    # AFC South
    "Houston Texans": 1710,
    "Indianapolis Colts": 1580,
    "Jacksonville Jaguars": 1600,
    "Tennessee Titans": 1480,

    # AFC West
    "Denver Broncos": 1640,
    "Kansas City Chiefs": 1920,
    "Las Vegas Raiders": 1490,
    "Los Angeles Chargers": 1730,

    # NFC East
    "Dallas Cowboys": 1710,
    "New York Giants": 1450,
    "Philadelphia Eagles": 1880,
    "Washington Commanders": 1670,

    # NFC North
    "Chicago Bears": 1570,
    "Detroit Lions": 1810,
    "Green Bay Packers": 1760,
    "Minnesota Vikings": 1700,

    # NFC South
    "Atlanta Falcons": 1630,
    "Carolina Panthers": 1460,
    "New Orleans Saints": 1500,
    "Tampa Bay Buccaneers": 1680,

    # NFC West
    "Arizona Cardinals": 1560,
    "Los Angeles Rams": 1740,
    "San Francisco 49ers": 1830,
    "Seattle Seahawks": 1610,
}

# =========================
# DIVISIONS & CONFERENCES
# =========================
DIVISIONS = {
    "AFC East": ["Buffalo Bills", "Miami Dolphins", "New York Jets", "New England Patriots"],
    "AFC North": ["Baltimore Ravens", "Pittsburgh Steelers", "Cincinnati Bengals", "Cleveland Browns"],
    "AFC South": ["Houston Texans", "Indianapolis Colts", "Jacksonville Jaguars", "Tennessee Titans"],
    "AFC West": ["Kansas City Chiefs", "Los Angeles Chargers", "Las Vegas Raiders", "Denver Broncos"],
    "NFC East": ["Dallas Cowboys", "Philadelphia Eagles", "Washington Commanders", "New York Giants"],
    "NFC North": ["Detroit Lions", "Green Bay Packers", "Minnesota Vikings", "Chicago Bears"],
    "NFC South": ["Tampa Bay Buccaneers", "New Orleans Saints", "Atlanta Falcons", "Carolina Panthers"],
    "NFC West": ["San Francisco 49ers", "Los Angeles Rams", "Seattle Seahawks", "Arizona Cardinals"]
}

CONFERENCES = {
    "AFC": ["Buffalo Bills", "Miami Dolphins", "New York Jets", "New England Patriots",
            "Baltimore Ravens", "Pittsburgh Steelers", "Cincinnati Bengals", "Cleveland Browns",
            "Houston Texans", "Indianapolis Colts", "Jacksonville Jaguars", "Tennessee Titans",
            "Kansas City Chiefs", "Los Angeles Chargers", "Las Vegas Raiders", "Denver Broncos"],
    "NFC": ["Dallas Cowboys", "Philadelphia Eagles", "Washington Commanders", "New York Giants",
            "Detroit Lions", "Green Bay Packers", "Minnesota Vikings", "Chicago Bears",
            "Tampa Bay Buccaneers", "New Orleans Saints", "Atlanta Falcons", "Carolina Panthers",
            "San Francisco 49ers", "Los Angeles Rams", "Seattle Seahawks", "Arizona Cardinals"]
}

# ==============================================================================
# REAL CHRONOLOGICAL SCHEDULE (Cleaned and Mapped explicitly to Home vs Away)
# ==============================================================================
WEEKLY_SCHEDULE = {
    1: [
        ("Houston Texans", "Buffalo Bills"), ("Las Vegas Raiders", "Miami Dolphins"),
        ("Seattle Seahawks", "New England Patriots"), ("Tennessee Titans", "New York Jets"),
        ("Indianapolis Colts", "Baltimore Ravens"), ("Cincinnati Bengals", "Tampa Bay Buccaneers"),
        ("Jacksonville Jaguars", "Cleveland Browns"), ("Pittsburgh Steelers", "Atlanta Falcons"),
        ("Kansas City Chiefs", "Denver Broncos"), ("Los Angeles Chargers", "Arizona Cardinals"),
        ("New York Giants", "Dallas Cowboys"), ("Philadelphia Eagles", "Washington Commanders"),
        ("Carolina Panthers", "Chicago Bears"), ("Detroit Lions", "New Orleans Saints"),
        ("Minnesota Vikings", "Green Bay Packers"), ("Los Angeles Rams", "San Francisco 49ers") # Melbourne
    ],
    2: [
        ("Buffalo Bills", "Detroit Lions"), ("San Francisco 49ers", "Miami Dolphins"),
        ("New England Patriots", "Pittsburgh Steelers"), ("New York Jets", "Green Bay Packers"),
        ("New Orleans Saints", "Baltimore Ravens"), ("Houston Texans", "Cincinnati Bengals"),
        ("Tampa Bay Buccaneers", "Cleveland Browns"), ("Denver Broncos", "Jacksonville Jaguars"),
        ("Los Angeles Chargers", "Las Vegas Raiders"), ("Washington Commanders", "Dallas Cowboys"),
        ("Chicago Bears", "Minnesota Vikings"), ("Atlanta Falcons", "Carolina Panthers"),
        ("Seattle Seahawks", "Arizona Cardinals"), ("New York Giants", "Los Angeles Rams")
    ],
    3: [
        ("Buffalo Bills", "Los Angeles Chargers"), ("Miami Dolphins", "Kansas City Chiefs"),
        ("Jacksonville Jaguars", "New England Patriots"), ("Detroit Lions", "New York Jets"),
        ("Dallas Cowboys", "Baltimore Ravens"), # Rio de Janeiro
        ("Pittsburgh Steelers", "Cincinnati Bengals"),
        ("Cleveland Browns", "Carolina Panthers"), ("Indianapolis Colts", "Houston Texans"),
        ("New Orleans Saints", "Las Vegas Raiders"), ("Chicago Bears", "Philadelphia Eagles"),
        ("Washington Commanders", "Seattle Seahawks"), ("Green Bay Packers", "Atlanta Falcons"),
        ("Tampa Bay Buccaneers", "Minnesota Vikings"), ("San Francisco 49ers", "Arizona Cardinals"),
        ("Denver Broncos", "Los Angeles Rams")
    ],
    4: [
        ("Buffalo Bills", "New England Patriots"), ("Minnesota Vikings", "Miami Dolphins"),
        ("Chicago Bears", "New York Jets"), ("Baltimore Ravens", "Tennessee Titans"),
        ("Cincinnati Bengals", "Jacksonville Jaguars"), ("Cleveland Browns", "Pittsburgh Steelers"),
        ("Dallas Cowboys", "Houston Texans"), ("Washington Commanders", "Indianapolis Colts"), # London
        ("Las Vegas Raiders", "Kansas City Chiefs"), ("Seattle Seahawks", "Los Angeles Chargers"),
        ("Philadelphia Eagles", "Los Angeles Rams"), ("New York Giants", "Arizona Cardinals"),
        ("Carolina Panthers", "Detroit Lions"), ("Tampa Bay Buccaneers", "Green Bay Packers"),
        ("New Orleans Saints", "Atlanta Falcons"), ("San Francisco 49ers", "Denver Broncos")
    ],
    5: [
        ("Los Angeles Rams", "Buffalo Bills"), ("Miami Dolphins", "Cincinnati Bengals"),
        ("New England Patriots", "Las Vegas Raiders"), ("New York Jets", "Cleveland Browns"),
        ("Atlanta Falcons", "Baltimore Ravens"), ("Tennessee Titans", "Houston Texans"),
        ("Pittsburgh Steelers", "Indianapolis Colts"), ("Los Angeles Chargers", "Denver Broncos"),
        ("Dallas Cowboys", "Tampa Bay Buccaneers"), ("Washington Commanders", "New York Giants"),
        ("Philadelphia Eagles", "Jacksonville Jaguars"), # London
        ("Green Bay Packers", "Chicago Bears"),
        ("Arizona Cardinals", "Detroit Lions"), ("New Orleans Saints", "Minnesota Vikings"),
        ("Seattle Seahawks", "San Francisco 49ers")
    ],
    6: [
        ("Las Vegas Raiders", "Buffalo Bills"), ("Cleveland Browns", "Baltimore Ravens"),
        ("New England Patriots", "New York Jets"), ("Jacksonville Jaguars", "Houston Texans"), # London
        ("Indianapolis Colts", "Tennessee Titans"), ("Tampa Bay Buccaneers", "Pittsburgh Steelers"),
        ("Kansas City Chiefs", "Los Angeles Chargers"), ("Green Bay Packers", "Dallas Cowboys"),
        ("New York Giants", "New Orleans Saints"), ("San Francisco 49ers", "Washington Commanders"),
        ("Atlanta Falcons", "Chicago Bears"), ("Arizona Cardinals", "Los Angeles Rams"),
        ("Denver Broncos", "Seattle Seahawks")
    ],
    7: [
        ("New York Jets", "Miami Dolphins"), ("New England Patriots", "Chicago Bears"),
        ("Baltimore Ravens", "Cincinnati Bengals"), ("Tennessee Titans", "Cleveland Browns"),
        ("New Orleans Saints", "Pittsburgh Steelers"), # Paris
        ("Houston Texans", "New York Giants"),
        ("Minnesota Vikings", "Indianapolis Colts"), ("Arizona Cardinals", "Denver Broncos"),
        ("Seattle Seahawks", "Kansas City Chiefs"), ("Las Vegas Raiders", "Los Angeles Rams"),
        ("Philadelphia Eagles", "Dallas Cowboys"), ("Detroit Lions", "Green Bay Packers"),
        ("Atlanta Falcons", "San Francisco 49ers"), ("Carolina Panthers", "Tampa Bay Buccaneers")
    ],
    8: [
        ("Buffalo Bills", "Baltimore Ravens"), ("Miami Dolphins", "New England Patriots"),
        ("New York Jets", "Las Vegas Raiders"), ("Pittsburgh Steelers", "Cleveland Browns"),
        ("Jacksonville Jaguars", "Indianapolis Colts"), ("Cincinnati Bengals", "Tennessee Titans"),
        ("Denver Broncos", "Kansas City Chiefs"), ("Los Angeles Rams", "Los Angeles Chargers"),
        ("Dallas Cowboys", "Arizona Cardinals"), ("Washington Commanders", "Philadelphia Eagles"),
        ("Seattle Seahawks", "Chicago Bears"), ("Detroit Lions", "Minnesota Vikings"),
        ("Tampa Bay Buccaneers", "Atlanta Falcons"), ("Green Bay Packers", "Carolina Panthers")
    ],
    9: [
        ("Minnesota Vikings", "Buffalo Bills"), ("Miami Dolphins", "Detroit Lions"),
        ("New England Patriots", "Green Bay Packers"), ("Kansas City Chiefs", "New York Jets"),
        ("Baltimore Ravens", "Jacksonville Jaguars"), ("Atlanta Falcons", "Cincinnati Bengals"), # Madrid
        ("New Orleans Saints", "Cleveland Browns"), ("Los Angeles Chargers", "Houston Texans"),
        ("Indianapolis Colts", "Dallas Cowboys"), ("Philadelphia Eagles", "New York Giants"),
        ("Washington Commanders", "Los Angeles Rams"), ("Chicago Bears", "Tampa Bay Buccaneers"),
        ("Denver Broncos", "Carolina Panthers"), ("San Francisco 49ers", "Las Vegas Raiders"),
        ("Arizona Cardinals", "Seattle Seahawks")
    ],
    10: [
        ("New York Jets", "Buffalo Bills"), ("Indianapolis Colts", "Miami Dolphins"),
        ("New England Patriots", "Detroit Lions"), # Munich
        ("Baltimore Ravens", "Los Angeles Chargers"),
        ("Cincinnati Bengals", "Pittsburgh Steelers"), ("Cleveland Browns", "Houston Texans"),
        ("Tennessee Titans", "Jacksonville Jaguars"), ("Atlanta Falcons", "Kansas City Chiefs"),
        ("Las Vegas Raiders", "Seattle Seahawks"), ("Dallas Cowboys", "San Francisco 49ers"),
        ("New York Giants", "Washington Commanders"), ("Green Bay Packers", "Minnesota Vikings"),
        ("New Orleans Saints", "Carolina Panthers"), ("Arizona Cardinals", "Los Angeles Rams")
    ],
    11: [
        ("Buffalo Bills", "Miami Dolphins"), ("Los Angeles Chargers", "New York Jets"),
        ("Carolina Panthers", "Baltimore Ravens"), ("Washington Commanders", "Cincinnati Bengals"),
        ("Dallas Cowboys", "Tennessee Titans"), ("Houston Texans", "Indianapolis Colts"),
        ("New York Giants", "Jacksonville Jaguars"), ("Denver Broncos", "Las Vegas Raiders"),
        ("Arizona Cardinals", "Kansas City Chiefs"), ("Philadelphia Eagles", "Pittsburgh Steelers"),
        ("Chicago Bears", "New Orleans Saints"), ("Detroit Lions", "Tampa Bay Buccaneers"),
        ("Minnesota Vikings", "San Francisco 49ers"), # Mexico City
        ("Los Angeles Rams", "Arizona Cardinals")
    ],
    12: [
        ("Buffalo Bills", "Kansas City Chiefs"), ("Miami Dolphins", "New York Jets"),
        ("Los Angeles Chargers", "New New England Patriots"), ("Houston Texans", "Baltimore Ravens"),
        ("Cincinnati Bengals", "New Orleans Saints"), ("Cleveland Browns", "Las Vegas Raiders"),
        ("Jacksonville Jaguars", "Tennessee Titans"), ("Indianapolis Colts", "New York Giants"),
        ("Pittsburgh Steelers", "Denver Broncos"), ("Dallas Cowboys", "Philadelphia Eagles"),
        ("Arizona Cardinals", "Washington Commanders"), ("Detroit Lions", "Chicago Bears"),
        ("Los Angeles Rams", "Green Bay Packers"), ("Minnesota Vikings", "Atlanta Falcons"),
        ("Tampa Bay Buccaneers", "Carolina Panthers"), ("San Francisco 49ers", "Seattle Seahawks")
    ],
    13: [
        ("New England Patriots", "Buffalo Bills"), ("Denver Broncos", "Miami Dolphins"),
        ("Cleveland Browns", "Cincinnati Bengals"), ("Pittsburgh Steelers", "Houston Texans"),
        ("Tennessee Titans", "Washington Commanders"), ("Los Angeles Rams", "Kansas City Chiefs"),
        ("Seattle Seahawks", "Dallas Cowboys"), ("New York Giants", "San Francisco 49ers"),
        ("Arizona Cardinals", "Philadelphia Eagles"), ("New Orleans Saints", "Green Bay Packers"),
        ("Atlanta Falcons", "Detroit Lions"), ("Minnesota Vikings", "Carolina Panthers"),
        ("Tampa Bay Buccaneers", "Los Angeles Chargers")
    ],
    14: [
        ("Green Bay Packers", "Buffalo Bills"), ("Chicago Bears", "Miami Dolphins"),
        ("New England Patriots", "Minnesota Vikings"), ("New York Jets", "Denver Broncos"),
        ("Baltimore Ravens", "Tampa Bay Buccaneers"), ("Cincinnati Bengals", "Kansas City Chiefs"),
        ("Cleveland Browns", "Atlanta Falcons"), ("Jacksonville Jaguars", "Pittsburgh Steelers"),
        ("Houston Texans", "Washington Commanders"), ("Philadelphia Eagles", "Indianapolis Colts"),
        ("Las Vegas Raiders", "Los Angeles Chargers"), ("Seattle Seahawks", "New York Giants"),
        ("Carolina Panthers", "New Orleans Saints"), ("San Francisco 49ers", "Los Angeles Rams")
    ],
    15: [
        ("Buffalo Bills", "Chicago Bears"), ("Green Bay Packers", "Miami Dolphins"),
        ("Kansas City Chiefs", "New New England Patriots"), ("Arizona Cardinals", "New York Jets"),
        ("Pittsburgh Steelers", "Baltimore Ravens"), ("Carolina Panthers", "Cincinnati Bengals"),
        ("New York Giants", "Cleveland Browns"), ("Houston Texans", "Jacksonville Jaguars"),
        ("Tennessee Titans", "Indianapolis Colts"), ("Las Vegas Raiders", "Denver Broncos"),
        ("Los Angeles Chargers", "San Francisco 49ers"), ("Los Angeles Rams", "Dallas Cowboys"),
        ("Philadelphia Eagles", "Seattle Seahawks"), ("Minnesota Vikings", "Detroit Lions"),
        ("Washington Commanders", "Atlanta Falcons"), ("Tampa Bay Buccaneers", "New Orleans Saints")
    ],
    16: [
        ("Denver Broncos", "Buffalo Bills"), ("Miami Dolphins", "Los Angeles Chargers"),
        ("New York Jets", "New England Patriots"), ("Baltimore Ravens", "Cleveland Browns"),
        ("Indianapolis Colts", "Cincinnati Bengals"), ("Pittsburgh Steelers", "Carolina Panthers"),
        ("Dallas Cowboys", "Jacksonville Jaguars"), ("Las Vegas Raiders", "Tennessee Titans"),
        ("Kansas City Chiefs", "San Francisco 49ers"), ("Detroit Lions", "New York Giants"),
        ("Philadelphia Eagles", "Houston Texans"), ("Washington Commanders", "Minnesota Vikings"),
        ("Chicago Bears", "Green Bay Packers"), ("Tampa Bay Buccaneers", "Atlanta Falcons"),
        ("New Orleans Saints", "Arizona Cardinals"), ("Seattle Seahawks", "Los Angeles Rams")
    ],
    17: [
        ("Miami Dolphins", "Buffalo Bills"), ("New England Patriots", "Denver Broncos"),
        ("New York Jets", "Minnesota Vikings"), ("Cincinnati Bengals", "Baltimore Ravens"),
        ("Cleveland Browns", "Indianapolis Colts"), ("Tennessee Titans", "Pittsburgh Steelers"),
        ("Los Angeles Chargers", "Kansas City Chiefs"), ("Dallas Cowboys", "New York Giants"),
        ("San Francisco 49ers", "Philadelphia Eagles"), ("Jacksonville Jaguars", "Washington Commanders"),
        ("Chicago Bears", "Detroit Lions"), ("Green Bay Packers", "Houston Texans"),
        ("Atlanta Falcons", "New Orleans Saints"), ("Carolina Panthers", "Seattle Seahawks"),
        ("Tampa Bay Buccaneers", "Los Angeles Rams"), ("Arizona Cardinals", "Las Vegas Raiders")
    ],
    18: [
        ("Buffalo Bills", "New York Jets"), ("New England Patriots", "Miami Dolphins"),
        ("Baltimore Ravens", "Pittsburgh Steelers"), ("Cincinnati Bengals", "Cleveland Browns"),
        ("Houston Texans", "Tennessee Titans"), ("Indianapolis Colts", "Jacksonville Jaguars"),
        ("Kansas City Chiefs", "Las Vegas Raiders"), ("Denver Broncos", "Los Angeles Chargers"),
        ("Washington Commanders", "Dallas Cowboys"), ("New York Giants", "Philadelphia Eagles"),
        ("Minnesota Vikings", "Chicago Bears"), ("Green Bay Packers", "Detroit Lions"),
        ("Carolina Panthers", "Atlanta Falcons"), ("New Orleans Saints", "Tampa Bay Buccaneers"),
        ("San Francisco 49ers", "Arizona Cardinals"), ("Los Angeles Rams", "Seattle Seahawks")
    ]
}

# ==============================================================================
# IDENTIFY NEUTRAL SITE / INTERNATIONAL MATCHUPS
# ==============================================================================
# Keyed by (Week, Home_Listed, Away_Listed) based on the text documentation notes
NEUTRAL_GAMES = {
    (1, "Los Angeles Rams", "San Francisco 49ers"),   # Melbourne, Australia
    (3, "Dallas Cowboys", "Baltimore Ravens"),         # Rio de Janeiro, Brazil
    (4, "Washington Commanders", "Indianapolis Colts"),# London, UK
    (5, "Philadelphia Eagles", "Jacksonville Jaguars"),# London, UK
    (6, "Jacksonville Jaguars", "Houston Texans"),     # London, UK
    (7, "New Orleans Saints", "Pittsburgh Steelers"),   # Paris, France
    (9, "Atlanta Falcons", "Cincinnati Bengals"),      # Madrid, Spain
    (10, "New New England Patriots", "Detroit Lions"),  # Munich, Germany (Handled clean)
    (10, "New England Patriots", "Detroit Lions"),      # Munich, Germany
    (11, "Minnesota Vikings", "San Francisco 49ers")    # Mexico City, Mexico
}

CLEANED_SCHEDULE = {}
VALID_TEAMS = set(ELO.keys())

for wk, games in WEEKLY_SCHEDULE.items():
    cleaned_games = []
    for h, a in games:
        h_clean = next((t for t in VALID_TEAMS if t in h), h)
        a_clean = next((t for t in VALID_TEAMS if t in a), a)
        if h_clean in VALID_TEAMS and a_clean in VALID_TEAMS:
            cleaned_games.append((h_clean, a_clean))
    CLEANED_SCHEDULE[wk] = cleaned_games

# ==============================================================================
# ENGINE CORE
# ==============================================================================
def win_prob(ra, rb, is_neutral=False):
    # If is_neutral is true, diff excludes HOME_ADV completely
    diff = (ra + (0 if is_neutral else HOME_ADV)) - rb
    return 1 / (1 + 10 ** (-diff / ELO_SCALE))

def simulate_game(home, away, elo_dict, is_neutral=False):
    pa = win_prob(elo_dict[home], elo_dict[away], is_neutral)
    winner = home if random.random() < pa else away
    loser = away if winner == home else home
    return winner, loser

def update_elo(home, away, winner, loser, elo_dict, is_neutral=False):
    if is_neutral:
        expected_winner = 1 / (1 + 10 ** ((elo_dict[loser] - elo_dict[winner]) / ELO_SCALE))
    else:
        if winner == home:
            expected_winner = win_prob(elo_dict[home], elo_dict[away], is_neutral=False)
        else:
            expected_winner = 1 - win_prob(elo_dict[home], elo_dict[away], is_neutral=False)

    elo_dict[winner] += K * (1 - expected_winner)
    elo_dict[loser] += K * (0 - (1 - expected_winner))

def apply_parity_reset(elo_dict):
    return {
        team: (elo * (1 - PARITY_RESET_FACTOR)) + (LEAGUE_AVERAGE_ELO * PARITY_RESET_FACTOR)
        for team, elo in elo_dict.items()
    }

def display_pre_season_elo(elo_dict):
    print("\n" + "="*50)
    print("PRE-SEASON ELO RATINGS (After Parity Reset)")
    print("="*50)
    sorted_elo = sorted(elo_dict.items(), key=lambda x: x[1], reverse=True)
    for team, rating in sorted_elo:
        print(f"{team:<25} | {rating:.0f}")

def simulate_season(elo_dict):
    wins = defaultdict(int)
    elo = elo_dict
    
    for week in range(1, 19):
        for home, away in CLEANED_SCHEDULE[week]:
            is_intl = (week, home, away) in NEUTRAL_GAMES
            
            winner, loser = simulate_game(home, away, elo, is_neutral=is_intl)
            wins[winner] += 1
            update_elo(home, away, winner, loser, elo, is_neutral=is_intl)
    return wins, elo

# ==============================================================================
# SEEDING PROPELLOR ENGINE
# ==============================================================================
def process_playoff_seeding(wins):
    seeds = {"AFC": [], "NFC": []}
    for conf, conf_teams in CONFERENCES.items():
        div_winners = []
        for div_name, div_teams in DIVISIONS.items():
            if div_name.startswith(conf):
                winner = max(div_teams, key=lambda t: (wins[t], random.random()))
                div_winners.append(winner)
                
        div_winners_sorted = sorted(div_winners, key=lambda t: (wins[t], random.random()), reverse=True)
        wildcards = [t for t in conf_teams if t not in div_winners]
        wildcards_sorted = sorted(wildcards, key=lambda t: (wins[t], random.random()), reverse=True)[:3]
        seeds[conf] = div_winners_sorted + wildcards_sorted
        
    return seeds["AFC"], seeds["NFC"]

# ==============================================================================
# RE-SEEDING BRACKET SIMULATION
# ==============================================================================
def run_conference_playoffs(seeds, elo_dict):
    # Wild Card Round (Seed 1 Bye)
    wc_winners = [seeds[0]] 
    for h_idx, a_idx in [(1, 6), (2, 5), (3, 4)]:
        winner, _ = simulate_game(seeds[h_idx], seeds[a_idx], elo_dict, is_neutral=False)
        wc_winners.append(winner)
        
    # Divisional Round (Re-seeded)
    remaining_sorted_by_seed = sorted(wc_winners, key=lambda t: seeds.index(t))
    div_w1, _ = simulate_game(remaining_sorted_by_seed[0], remaining_sorted_by_seed[3], elo_dict, is_neutral=False)
    div_w2, _ = simulate_game(remaining_sorted_by_seed[1], remaining_sorted_by_seed[2], elo_dict, is_neutral=False)
    
    # Conference Championship
    cc_teams = sorted([div_w1, div_w2], key=lambda t: seeds.index(t))
    conference_champion, _ = simulate_game(cc_teams[0], cc_teams[1], elo_dict, is_neutral=False)
    
    return conference_champion

# ==============================================================================
# MAIN SIMULATION RUNNER
# ==============================================================================
def run_sim():
    pre_season_elo = apply_parity_reset(ELO)
    display_pre_season_elo(pre_season_elo)
    
    sb_wins = defaultdict(int)
    conf_wins = defaultdict(int)

    print(f"Running {N_SIMS} NFL simulations with international neutral locations applied...")
    
    for _ in tqdm(range(N_SIMS), desc="Running simulations", unit="sim"):
        wins, final_elo = simulate_season(pre_season_elo.copy())
        afc_seeds, nfc_seeds = process_playoff_seeding(wins)
        
        afc_champ = run_conference_playoffs(afc_seeds, final_elo)
        nfc_champ = run_conference_playoffs(nfc_seeds, final_elo)
        
        conf_wins[afc_champ] += 1
        conf_wins[nfc_champ] += 1
        
        # Super Bowl (Always Neutral)
        sb_winner, _ = simulate_game(afc_champ, nfc_champ, final_elo, is_neutral=True)
        sb_wins[sb_winner] += 1

    print("\n" + "="*55)
    print(f"{'TEAM':<25} | {'CONF TITLES':<12} | {'SUPER BOWL WIN ODDS'}")
    print("="*55)
    sorted_results = sorted(VALID_TEAMS, key=lambda x: sb_wins[x], reverse=True)
    for team in sorted_results:
        if conf_wins[team] > 0 or sb_wins[team] > 0:
            print(f"{team:<25} | {conf_wins[team] / N_SIMS :<12.2%} | {sb_wins[team] / N_SIMS:.2%}")

if __name__ == "__main__":
    run_sim()