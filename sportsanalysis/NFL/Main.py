import random
import math
from collections import defaultdict
from tqdm import tqdm

# =========================
# CONFIG
# =========================
N_SIMS = 10000
HOME_ADV = 65
ELO_SCALE = 600
K = 20              # base K (will be dynamically scaled)

LEAGUE_AVERAGE_ELO = 1500

# Tie probability parameters
MAX_TIE_PROB = 0.005      # 0.5% max when ΔR = 0
TIE_SIGMA = 85            # decay rate

# =========================
# INITIAL ELO
# =========================
ELO = {
    # AFC East
    "Buffalo Bills": 1827,
    "Miami Dolphins": 1630,
    "New England Patriots": 1578,
    "New York Jets": 1483,

    # AFC North
    "Baltimore Ravens": 1837,
    "Cincinnati Bengals": 1764,
    "Cleveland Browns": 1499,
    "Pittsburgh Steelers": 1687,

    # AFC South
    "Houston Texans": 1713,
    "Indianapolis Colts": 1545,
    "Jacksonville Jaguars": 1616,
    "Tennessee Titans": 1463,

    # AFC West
    "Denver Broncos": 1700,
    "Kansas City Chiefs": 1850,
    "Las Vegas Raiders": 1482,
    "Los Angeles Chargers": 1761,

    # NFC East
    "Dallas Cowboys": 1696,
    "New York Giants": 1388,
    "Philadelphia Eagles": 1892,
    "Washington Commanders": 1646,

    # NFC North
    "Chicago Bears": 1607,
    "Detroit Lions": 1790,
    "Green Bay Packers": 1746,
    "Minnesota Vikings": 1703,

    # NFC South
    "Atlanta Falcons": 1645,
    "Carolina Panthers": 1480,
    "New Orleans Saints": 1494,
    "Tampa Bay Buccaneers": 1686,

    # NFC West
    "Arizona Cardinals": 1511,
    "Los Angeles Rams": 1743,
    "San Francisco 49ers": 1882,
    "Seattle Seahawks": 1636,
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
        ("Seattle Seahawks", "New England Patriots"),
        ("San Francisco 49ers", "Los Angeles Rams"),
        ("Pittsburgh Steelers", "Atlanta Falcons"), ("Indianapolis Colts", "Baltimore Ravens"),
        ("Houston Texans", "Buffalo Bills"), ("Carolina Panthers", "Chicago Bears"),
        ("Jacksonville Jaguars", "Cleveland Browns"), ("Detroit Lions", "New Orleans Saints"),
        ("Tennessee Titans", "New York Jets"), ("Cincinnati Bengals", "Tampa Bay Buccaneers"),
        ("Los Angeles Chargers", "Arizona Cardinals"), ("Minnesota Vikings", "Green Bay Packers"),
        ("Las Vegas Raiders", "Miami Dolphins"), ("Philadelphia Eagles", "Washington Commanders"),
        ("New York Giants", "Dallas Cowboys"), ("Kansas City Chiefs", "Denver Broncos"),
    ],
    2: [
        ("Buffalo Bills", "Detroit Lions"), ("Houston Texans", "Cincinnati Bengals"),
        ("Atlanta Falcons", "Carolina Panthers"), ("Tampa Bay Buccaneers", "Cleveland Browns"),
        ("New York Jets", "Green Bay Packers"), ("Chicago Bears", "Minnesota Vikings"),
        ("Baltimore Ravens", "New Orleans Saints"), ("Tennessee Titans", "Philadelphia Eagles"),
        ("New England Patriots", "Pittsburgh Steelers"), ("Los Angeles Chargers", "Las Vegas Raiders"),
        ("Denver Broncos", "Jacksonville Jaguars"), ("San Francisco 49ers", "Miami Dolphins"),
        ("Arizona Cardinals", "Seattle Seahawks"), ("Dallas Cowboys", "Washington Commanders"),
        ("Kansas City Chiefs", "Indianapolis Colts"), ("Los Angeles Rams", "New York Giants"),
    ],
    3: [
        ("Green Bay Packers", "Atlanta Falcons"), ("Cleveland Browns", "Carolina Panthers"),
        ("Pittsburgh Steelers", "Cincinnati Bengals"), ("Indianapolis Colts", "Houston Texans"),
        ("Miami Dolphins", "Kansas City Chiefs"), ("Buffalo Bills", "Los Angeles Chargers"),
        ("Jacksonville Jaguars", "New England Patriots"), ("Detroit Lions", "New York Jets"),
        ("Washington Commanders", "Seattle Seahawks"), ("New York Giants", "Tennessee Titans"),
        ("San Francisco 49ers", "Arizona Cardinals"), ("Tampa Bay Buccaneers", "Minnesota Vikings"),
        ("Dallas Cowboys", "Baltimore Ravens"), ("New Orleans Saints", "Las Vegas Raiders"),
        ("Denver Broncos", "Los Angeles Rams"), ("Chicago Bears", "Philadelphia Eagles"),
    ],
    4: [
        ("Cleveland Browns", "Pittsburgh Steelers"), ("Washington Commanders", "Indianapolis Colts"),
        ("New York Giants", "Arizona Cardinals"), ("Houston Texans", "Dallas Cowboys"),
        ("Tampa Bay Buccaneers", "Green Bay Packers"), ("Cincinnati Bengals", "Jacksonville Jaguars"),
        ("Philadelphia Eagles", "Los Angeles Rams"), ("Buffalo Bills", "New England Patriots"),
        ("Chicago Bears", "New York Jets"), ("Baltimore Ravens", "Tennessee Titans"),
        ("Minnesota Vikings", "Miami Dolphins"), ("San Francisco 49ers", "Denver Broncos"),
        ("Las Vegas Raiders", "Kansas City Chiefs"), ("Seattle Seahawks", "Los Angeles Chargers"),
        ("Carolina Panthers", "Detroit Lions"), ("New Orleans Saints", "Atlanta Falcons"),
    ],
    5: [
        ("Dallas Cowboys", "Tampa Bay Buccaneers"), ("Jacksonville Jaguars", "Philadelphia Eagles"),
        ("Miami Dolphins", "Cincinnati Bengals"), ("New York Jets", "Cleveland Browns"),
        ("Tennessee Titans", "Houston Texans"), ("Pittsburgh Steelers", "Indianapolis Colts"),
        ("New England Patriots", "Las Vegas Raiders"), ("New Orleans Saints", "Minnesota Vikings"),
        ("Washington Commanders", "New York Giants"), ("Los Angeles Chargers", "Denver Broncos"),
        ("Green Bay Packers", "Chicago Bears"), ("Arizona Cardinals", "Detroit Lions"),
        ("Seattle Seahawks", "San Francisco 49ers"), ("Atlanta Falcons", "Baltimore Ravens"),
        ("Los Angeles Rams", "Buffalo Bills"),
    ],
    6: [
        ("Denver Broncos", "Seattle Seahawks"), ("Jacksonville Jaguars", "Houston Texans"),
        ("Philadelphia Eagles", "Carolina Panthers"), ("Cleveland Browns", "Baltimore Ravens"),
        ("Atlanta Falcons", "Chicago Bears"), ("New York Giants", "New Orleans Saints"),
        ("New England Patriots", "New York Jets"), ("Tampa Bay Buccaneers", "Pittsburgh Steelers"),
        ("Indianapolis Colts", "Tennessee Titans"), ("Los Angeles Rams", "Arizona Cardinals"),
        ("Las Vegas Raiders", "Buffalo Bills"), ("Kansas City Chiefs", "Los Angeles Chargers"),
        ("Green Bay Packers", "Dallas Cowboys"), ("San Francisco 49ers", "Washington Commanders"),
    ],
    7: [
        ("Chicago Bears", "New England Patriots"), ("New Orleans Saints", "Pittsburgh Steelers"),
        ("Tennessee Titans", "Cleveland Browns"), ("Baltimore Ravens", "Cincinnati Bengals"),
        ("Minnesota Vikings", "Indianapolis Colts"), ("New York Jets", "Miami Dolphins"),
        ("Houston Texans", "New York Giants"), ("Atlanta Falcons", "San Francisco 49ers"),
        ("Carolina Panthers", "Tampa Bay Buccaneers"), ("Arizona Cardinals", "Denver Broncos"),
        ("Detroit Lions", "Green Bay Packers"), ("Las Vegas Raiders", "Los Angeles Rams"),
        ("Seattle Seahawks", "Kansas City Chiefs"), ("Philadelphia Eagles", "Dallas Cowboys"),
    ],
    8: [
        ("Green Bay Packers", "Carolina Panthers"), ("Tampa Bay Buccaneers", "Atlanta Falcons"),
        ("Dallas Cowboys", "Arizona Cardinals"), ("Buffalo Bills", "Baltimore Ravens"),
        ("Pittsburgh Steelers", "Cleveland Browns"), ("Jacksonville Jaguars", "Indianapolis Colts"),
        ("New York Jets", "Las Vegas Raiders"), ("Detroit Lions", "Minnesota Vikings"),
        ("Cincinnati Bengals", "Tennessee Titans"), ("Los Angeles Rams", "Los Angeles Chargers"),
        ("Denver Broncos", "Kansas City Chiefs"), ("Miami Dolphins", "New England Patriots"),
        ("Washington Commanders", "Philadelphia Eagles"), ("Seattle Seahawks", "Chicago Bears"),
    ],
    9: [
        ("Baltimore Ravens", "Jacksonville Jaguars"), ("Atlanta Falcons", "Cincinnati Bengals"),
        ("New Orleans Saints", "Cleveland Browns"), ("Indianapolis Colts", "Dallas Cowboys"),
        ("Carolina Panthers", "Denver Broncos"), ("Miami Dolphins", "Detroit Lions"),
        ("Washington Commanders", "Los Angeles Rams"), ("Philadelphia Eagles", "New York Giants"),
        ("Kansas City Chiefs", "New York Jets"), ("Los Angeles Chargers", "Houston Texans"),
        ("San Francisco 49ers", "Las Vegas Raiders"), ("Seattle Seahawks", "Arizona Cardinals"),
        ("New England Patriots", "Green Bay Packers"), ("Chicago Bears", "Tampa Bay Buccaneers"),
        ("Minnesota Vikings", "Buffalo Bills"),
    ],
    10: [
        ("New York Giants", "Washington Commanders"), ("Detroit Lions", "New England Patriots"),
        ("New Orleans Saints", "Carolina Panthers"), ("New York Jets", "Buffalo Bills"),
        ("Cleveland Browns", "Houston Texans"), ("Tennessee Titans", "Jacksonville Jaguars"),
        ("Atlanta Falcons", "Kansas City Chiefs"), ("Indianapolis Colts", "Miami Dolphins"),
        ("Green Bay Packers", "Minnesota Vikings"), ("Arizona Cardinals", "Los Angeles Rams"),
        ("Las Vegas Raiders", "Seattle Seahawks"), ("Dallas Cowboys", "San Francisco 49ers"),
        ("Cincinnati Bengals", "Pittsburgh Steelers"), ("Baltimore Ravens", "Los Angeles Chargers"),
    ],
    11: [
        ("Houston Texans", "Indianapolis Colts"), ("Carolina Panthers", "Baltimore Ravens"),
        ("Kansas City Chiefs", "Arizona Cardinals"), ("New York Giants", "Jacksonville Jaguars"),
        ("Buffalo Bills", "Miami Dolphins"), ("Chicago Bears", "New Orleans Saints"),
        ("Detroit Lions", "Tampa Bay Buccaneers"), ("Dallas Cowboys", "Tennessee Titans"),
        ("Los Angeles Chargers", "New York Jets"), ("Denver Broncos", "Las Vegas Raiders"),
        ("Philadelphia Eagles", "Pittsburgh Steelers"), ("San Francisco 49ers", "Minnesota Vikings"),
        ("Washington Commanders", "Cincinnati Bengals"),
    ],
    12: [
        ("Los Angeles Rams", "Green Bay Packers"), ("Detroit Lions", "Chicago Bears"),
        ("Dallas Cowboys", "Philadelphia Eagles"), ("Buffalo Bills", "Kansas City Chiefs"),
        ("Pittsburgh Steelers", "Denver Broncos"), ("Houston Texans", "Baltimore Ravens"),
        ("Minnesota Vikings", "Atlanta Falcons"), ("Cleveland Browns", "Las Vegas Raiders"),
        ("Cincinnati Bengals", "New Orleans Saints"), ("Indianapolis Colts", "New York Giants"),
        ("Miami Dolphins", "New York Jets"), ("Jacksonville Jaguars", "Tennessee Titans"),
        ("San Francisco 49ers", "Seattle Seahawks"), ("Arizona Cardinals", "Washington Commanders"),
        ("Los Angeles Chargers", "New England Patriots"), ("Tampa Bay Buccaneers", "Carolina Panthers"),
    ],
    13: [
        ("Los Angeles Rams", "Kansas City Chiefs"), ("Cleveland Browns", "Cincinnati Bengals"),
        ("Atlanta Falcons", "Detroit Lions"), ("New Orleans Saints", "Green Bay Packers"),
        ("Chicago Bears", "Jacksonville Jaguars"), ("Tampa Bay Buccaneers", "Los Angeles Chargers"),
        ("New York Giants", "San Francisco 49ers"), ("Tennessee Titans", "Washington Commanders"),
        ("Denver Broncos", "Miami Dolphins"), ("Arizona Cardinals", "Philadelphia Eagles"),
        ("New England Patriots", "Buffalo Bills"), ("Minnesota Vikings", "Carolina Panthers"),
        ("Pittsburgh Steelers", "Houston Texans"), ("Seattle Seahawks", "Dallas Cowboys"),
    ],
    14: [
        ("New England Patriots", "Minnesota Vikings"), ("Cleveland Browns", "Atlanta Falcons"),
        ("Miami Dolphins", "Chicago Bears"), ("New York Jets", "Denver Broncos"),
        ("Washington Commanders", "Houston Texans"), ("Philadelphia Eagles", "Indianapolis Colts"),
        ("Carolina Panthers", "New Orleans Saints"), ("Baltimore Ravens", "Tampa Bay Buccaneers"),
        ("Detroit Lions", "Tennessee Titans"), ("Las Vegas Raiders", "Los Angeles Chargers"),
        ("Cincinnati Bengals", "Kansas City Chiefs"), ("San Francisco 49ers", "Los Angeles Rams"),
        ("Seattle Seahawks", "New York Giants"), ("Green Bay Packers", "Buffalo Bills"),
        ("Jacksonville Jaguars", "Pittsburgh Steelers"),
    ],
    15: [
        ("Los Angeles Chargers", "San Francisco 49ers"), ("Philadelphia Eagles", "Seattle Seahawks"),
        ("Buffalo Bills", "Chicago Bears"), ("Pittsburgh Steelers", "Baltimore Ravens"),
        ("Washington Commanders", "Atlanta Falcons"), ("Carolina Panthers", "Cincinnati Bengals"),
        ("New York Giants", "Cleveland Browns"), ("Tennessee Titans", "Indianapolis Colts"),
        ("Houston Texans", "Jacksonville Jaguars"), ("Green Bay Packers", "Miami Dolphins"),
        ("Tampa Bay Buccaneers", "New Orleans Saints"), ("Arizona Cardinals", "New York Jets"),
        ("Los Angeles Rams", "Dallas Cowboys"), ("Las Vegas Raiders", "Denver Broncos"),
        ("Minnesota Vikings", "Detroit Lions"), ("Kansas City Chiefs", "New England Patriots"),
    ],
    16: [
        ("Philadelphia Eagles", "Houston Texans"), ("Chicago Bears", "Green Bay Packers"),
        ("Denver Broncos", "Buffalo Bills"), ("Seattle Seahawks", "Los Angeles Rams"),
        ("Pittsburgh Steelers", "Carolina Panthers"), ("Indianapolis Colts", "Cincinnati Bengals"),
        ("Atlanta Falcons", "Tampa Bay Buccaneers"), ("Minnesota Vikings", "Washington Commanders"),
        ("New Orleans Saints", "Arizona Cardinals"), ("Baltimore Ravens", "Cleveland Browns"),
        ("Miami Dolphins", "Los Angeles Chargers"), ("New York Jets", "New England Patriots"),
        ("Las Vegas Raiders", "Tennessee Titans"), ("Kansas City Chiefs", "San Francisco 49ers"),
        ("Dallas Cowboys", "Jacksonville Jaguars"), ("Detroit Lions", "New York Giants"),
    ],
    17: [
        ("Cincinnati Bengals", "Baltimore Ravens"), ("Los Angeles Chargers", "Kansas City Chiefs"),
        ("New England Patriots", "Denver Broncos"), ("Tampa Bay Buccaneers", "Los Angeles Rams"),
        ("Jacksonville Jaguars", "Washington Commanders"), ("Miami Dolphins", "Buffalo Bills"),
        ("Cleveland Browns", "Indianapolis Colts"), ("New York Jets", "Minnesota Vikings"),
        ("Atlanta Falcons", "New Orleans Saints"), ("Dallas Cowboys", "New York Giants"),
        ("Tennessee Titans", "Pittsburgh Steelers"), ("Carolina Panthers", "Seattle Seahawks"),
        ("Arizona Cardinals", "Las Vegas Raiders"), ("Chicago Bears", "Detroit Lions"),
        ("San Francisco 49ers", "Philadelphia Eagles"), ("Green Bay Packers", "Houston Texans"),
    ],
    18: [
        ("Carolina Panthers", "Atlanta Falcons"), ("Minnesota Vikings", "Chicago Bears"),
        ("Cincinnati Bengals", "Cleveland Browns"), ("Washington Commanders", "Dallas Cowboys"),
        ("Green Bay Packers", "Detroit Lions"), ("Indianapolis Colts", "Jacksonville Jaguars"),
        ("Denver Broncos", "Los Angeles Chargers"), ("Kansas City Chiefs", "Las Vegas Raiders"),
        ("New England Patriots", "Miami Dolphins"), ("Buffalo Bills", "New York Jets"),
        ("New York Giants", "Philadelphia Eagles"), ("Baltimore Ravens", "Pittsburgh Steelers"),
        ("Los Angeles Rams", "Seattle Seahawks"), ("Arizona Cardinals", "San Francisco 49ers"),
        ("New Orleans Saints", "Tampa Bay Buccaneers"), ("Houston Texans", "Tennessee Titans"),
    ],
}

# ==============================================================================
# IDENTIFY NEUTRAL SITE / INTERNATIONAL MATCHUPS
# ==============================================================================
NEUTRAL_GAMES = {
    (1, "Los Angeles Rams", "San Francisco 49ers"),   # Melbourne, Australia
    (3, "Dallas Cowboys", "Baltimore Ravens"),         # Rio de Janeiro, Brazil
    (4, "Washington Commanders", "Indianapolis Colts"),# London, UK
    (5, "Philadelphia Eagles", "Jacksonville Jaguars"),# London, UK
    (6, "Jacksonville Jaguars", "Houston Texans"),     # London, UK
    (7, "New Orleans Saints", "Pittsburgh Steelers"),   # Paris, France
    (9, "Atlanta Falcons", "Cincinnati Bengals"),      # Madrid, Spain
    (10, "New England Patriots", "Detroit Lions"),      # Munich, Germany
    (11, "Minnesota Vikings", "San Francisco 49ers")    # Mexico City, Mexico
}

# Clean schedule (just in case of any residual typos)
CLEANED_SCHEDULE = {}
VALID_TEAMS = set(ELO.keys())

for wk, games in WEEKLY_SCHEDULE.items():
    cleaned_games = []
    for h, a in games:
        # simple exact match; we already corrected typos
        h_clean = h if h in VALID_TEAMS else next((t for t in VALID_TEAMS if t in h), h)
        a_clean = a if a in VALID_TEAMS else next((t for t in VALID_TEAMS if t in a), a)
        if h_clean in VALID_TEAMS and a_clean in VALID_TEAMS:
            cleaned_games.append((h_clean, a_clean))
    CLEANED_SCHEDULE[wk] = cleaned_games

# Total number of regular-season games per season
TOTAL_GAMES_PER_SEASON = sum(len(CLEANED_SCHEDULE[w]) for w in range(1, 19))

# ==============================================================================
# ENGINE CORE
# ==============================================================================
def outcome_probs(r_home, r_away, is_neutral=False):
    """
    Returns (p_home_win, p_tie, p_away_win, expected_home_score)
    """
    diff = (r_home + (0 if is_neutral else HOME_ADV)) - r_away

    # Tie probability (Gaussian)
    p_tie = MAX_TIE_PROB * math.exp(-0.5 * (diff / TIE_SIGMA) ** 2)

    # Conditional win probability (given no tie)
    p_win_given_no_tie = 1 / (1 + 10 ** (-diff / ELO_SCALE))

    p_home = p_win_given_no_tie * (1 - p_tie)
    p_away = (1 - p_win_given_no_tie) * (1 - p_tie)

    # Expected score for home (Elo expectation)
    exp_home = p_home + 0.5 * p_tie

    return p_home, p_tie, p_away, exp_home

# Dynamic K-factor (FiveThirtyEight)
def calculate_dynamic_k(r_winner, r_loser, margin, base_k=20):
    """
    FiveThirtyEight dynamic K-factor formula:
    K_final = base_k * ln(|PD| + 1) * ( 2.2 / (0.001 * (r_winner - r_loser) + 2.2) )
    """
    pd = abs(margin)
    elo_diff = r_winner - r_loser
    
    denom = 0.001 * elo_diff + 2.2
    if denom < 0.1:
        denom = 0.1
    
    k_factor = base_k * math.log(pd + 1) * (2.2 / denom)
    return max(1.0, min(k_factor, 80.0))

def simulate_game(home, away, elo_dict, is_neutral=False, allow_tie=True):
    r_home, r_away = elo_dict[home], elo_dict[away]
    p_home, p_tie, p_away, _ = outcome_probs(r_home, r_away, is_neutral)

    if not allow_tie:
        p_tie = 0.0
        total = p_home + p_away
        if total > 0:
            p_home = p_home / total
            p_away = p_away / total
        else:
            p_home = 0.5
            p_away = 0.5

    r = random.random()
    if r < p_tie:
        return None, None, True, 0   # tie, margin=0

    if r < p_tie + p_home:
        winner, loser = home, away
    else:
        winner, loser = away, home

    # Generate margin of victory
    elo_diff_points = (elo_dict[winner] - elo_dict[loser]) / 10.0
    if not is_neutral:
        if winner == home:
            margin_mean = elo_diff_points + 3.0
        else:
            margin_mean = elo_diff_points - 3.0
    else:
        margin_mean = elo_diff_points
    margin_mean = max(margin_mean, 1.0)
    margin = int(round(random.gauss(margin_mean, 13.5)))
    margin = max(1, min(50, margin))

    return winner, loser, False, margin

def update_elo(home, away, winner, loser, tie, margin, elo_dict, is_neutral=False):
    r_home, r_away = elo_dict[home], elo_dict[away]
    _, _, _, exp_home = outcome_probs(r_home, r_away, is_neutral)

    if tie:
        s_home = 0.5
    elif winner == home:
        s_home = 1.0
    else:
        s_home = 0.0

    if tie or margin == 0:
        k_effective = 20.0
    else:
        r_winner = elo_dict[winner]
        r_loser = elo_dict[loser]
        k_effective = calculate_dynamic_k(r_winner, r_loser, margin, base_k=20)

    elo_dict[home] += k_effective * (s_home - exp_home)
    elo_dict[away] += k_effective * ((1 - s_home) - (1 - exp_home))

def display_pre_season_elo(elo_dict):
    print("\n" + "="*50)
    print("PRE-SEASON ELO RATINGS (After Parity Reset)")
    print("="*50)
    sorted_elo = sorted(elo_dict.items(), key=lambda x: x[1], reverse=True)
    for team, rating in sorted_elo:
        print(f"{team:<25} | {rating:.0f}")

def display_team_game_counts(elo_dict, schedule):
    game_count = {team: 0 for team in elo_dict}
    for week, games in schedule.items():
        for home, away in games:
            game_count[home] += 1
            game_count[away] += 1
    print("\n" + "="*50)
    print("TOTAL REGULAR‑SEASON GAMES PER TEAM (from schedule)")
    print("="*50)
    sorted_teams = sorted(game_count.items(), key=lambda x: x[1], reverse=True)
    for team, count in sorted_teams:
        print(f"{team:<25} | {count}")

# MODIFIED: simulate_season now also returns home_record
def simulate_season(elo_dict):
    record = {team: [0, 0, 0] for team in elo_dict}          # overall [W, L, T]
    home_record = {team: [0, 0, 0] for team in elo_dict}     # home [W, L, T]
    elo = elo_dict.copy()

    for week in range(1, 19):
        for home, away in CLEANED_SCHEDULE[week]:
            is_intl = (week, home, away) in NEUTRAL_GAMES
            winner, loser, tie, margin = simulate_game(home, away, elo, is_neutral=is_intl, allow_tie=True)

            if tie:
                record[home][2] += 1
                record[away][2] += 1
                home_record[home][2] += 1   # home team tied at home
            else:
                record[winner][0] += 1
                record[loser][1] += 1
                if winner == home:
                    home_record[home][0] += 1
                else:  # winner is away, so home team loses
                    home_record[home][1] += 1

            update_elo(home, away, winner, loser, tie, margin, elo, is_neutral=is_intl)

    return record, home_record, elo

# ==============================================================================
# SEEDING PROPELLOR ENGINE
# ==============================================================================
def win_pct(record):
    w, l, t = record
    games = w + l + t
    if games == 0:
        return 0.0
    return (w + 0.5 * t) / games

def process_playoff_seeding(record):
    seeds = {"AFC": [], "NFC": []}
    for conf, conf_teams in CONFERENCES.items():
        div_winners = []
        for div_name, div_teams in DIVISIONS.items():
            if div_name.startswith(conf):
                winner = max(div_teams, key=lambda t: (win_pct(record[t]), random.random()))
                div_winners.append(winner)

        div_winners_sorted = sorted(div_winners, key=lambda t: (win_pct(record[t]), random.random()), reverse=True)
        wildcards = [t for t in conf_teams if t not in div_winners]
        wildcards_sorted = sorted(wildcards, key=lambda t: (win_pct(record[t]), random.random()), reverse=True)[:3]

        seeds[conf] = div_winners_sorted + wildcards_sorted

    return seeds["AFC"], seeds["NFC"]

def run_conference_playoffs(seeds, elo_dict):
    wc_winners = [seeds[0]]
    for h_idx, a_idx in [(1, 6), (2, 5), (3, 4)]:
        winner, _, _, _ = simulate_game(seeds[h_idx], seeds[a_idx], elo_dict, is_neutral=False, allow_tie=False)
        wc_winners.append(winner)

    remaining_sorted_by_seed = sorted(wc_winners, key=lambda t: seeds.index(t))
    div_w1, _, _, _ = simulate_game(remaining_sorted_by_seed[0], remaining_sorted_by_seed[3],
                                    elo_dict, is_neutral=False, allow_tie=False)
    div_w2, _, _, _ = simulate_game(remaining_sorted_by_seed[1], remaining_sorted_by_seed[2],
                                    elo_dict, is_neutral=False, allow_tie=False)

    cc_teams = sorted([div_w1, div_w2], key=lambda t: seeds.index(t))
    conference_champion, _, _, _ = simulate_game(cc_teams[0], cc_teams[1],
                                                elo_dict, is_neutral=False, allow_tie=False)

    return conference_champion

# ==============================================================================
# MAIN SIMULATION RUNNER
# ==============================================================================
def run_sim():
    pre_season_elo = ELO.copy()
    display_pre_season_elo(pre_season_elo)
    display_team_game_counts(pre_season_elo, CLEANED_SCHEDULE)

    sb_wins = defaultdict(int)
    conf_wins = defaultdict(int)
    total_ties = 0

    # Aggregated records across all simulations
    total_record = {team: [0, 0, 0] for team in VALID_TEAMS}
    total_home_record = {team: [0, 0, 0] for team in VALID_TEAMS}

    print(f"Running {N_SIMS} NFL simulations with ties and neutral locations...")
    print(f"Total regular-season games per season: {TOTAL_GAMES_PER_SEASON}\n")

    for _ in tqdm(range(N_SIMS), desc="Running simulations", unit="sim"):
        record, home_record, final_elo = simulate_season(pre_season_elo.copy())
        afc_seeds, nfc_seeds = process_playoff_seeding(record)

        # Accumulate records
        for team in VALID_TEAMS:
            for i in range(3):
                total_record[team][i] += record[team][i]
                total_home_record[team][i] += home_record[team][i]

        season_ties = sum(rec[2] for rec in record.values()) // 2
        total_ties += season_ties

        afc_champ = run_conference_playoffs(afc_seeds, final_elo)
        nfc_champ = run_conference_playoffs(nfc_seeds, final_elo)

        conf_wins[afc_champ] += 1
        conf_wins[nfc_champ] += 1

        sb_winner, _, _, _ = simulate_game(afc_champ, nfc_champ, final_elo,
                                           is_neutral=True, allow_tie=False)
        sb_wins[sb_winner] += 1

    # --- Tie statistics ---
    avg_ties_per_season = total_ties / N_SIMS
    draw_pct = (avg_ties_per_season / TOTAL_GAMES_PER_SEASON) * 100

    print(f"\n{'='*55}")
    print(f"TIE / DRAW STATISTICS (over {N_SIMS} simulated seasons):")
    print(f"  • Average ties per season     : {avg_ties_per_season:.3f}")
    print(f"  • Average draw probability    : {draw_pct:.3f}% per game")
    print(f"  • Total games per season      : {TOTAL_GAMES_PER_SEASON}")
    print(f"{'='*55}\n")

    # --- Compute overall and home win percentages ---
    overall_pct = {}
    home_pct = {}
    for team in VALID_TEAMS:
        w, l, t = total_record[team]
        games = w + l + t
        overall_pct[team] = (w + 0.5 * t) / games if games > 0 else 0.0

        hw, hl, ht = total_home_record[team]
        home_games = hw + hl + ht
        home_pct[team] = (hw + 0.5 * ht) / home_games if home_games > 0 else 0.0

    # --- Final results table ---
    print("\n" + "="*85)
    print(f"{'TEAM':<25} | {'CONF TITLES':<12} | {'SB ODDS':<10} | {'OVERALL W%':<10} | {'HOME W%':<10}")
    print("="*85)

    sorted_teams = sorted(VALID_TEAMS, key=lambda x: sb_wins[x], reverse=True)
    for team in sorted_teams:
        # Only show teams that have at least some chance (or all teams)
        print(f"{team:<25} | {conf_wins[team] / N_SIMS :<12.2%} | {sb_wins[team] / N_SIMS :<10.2%} | "
              f"{overall_pct[team]:<10.2%} | {home_pct[team]:<10.2%}")

    # =========================================================================
    # NEW INTERACTIVE MODE – added at the bottom as requested
    # =========================================================================
    interactive_mode(ELO.copy(), CLEANED_SCHEDULE, NEUTRAL_GAMES)


def interactive_mode(initial_elo, schedule, neutral_games):
    """
    Interactive prompt:
    - Enter a week number (1-18) to see predictions for that week's games.
    - Press Enter (blank) to see predictions for all remaining (unplayed) games.
    - Type 'r' to record a completed game (enter week, home, away, scores).
    - Type 'q' to quit.
    """
    elo = initial_elo.copy()
    played_games = set()   # (week, home, away) tuples already entered

    print("\n" + "="*70)
    print("INTERACTIVE MODE – Predict & Update with Real Results")
    print("="*70)
    print("Commands:")
    print("  <week number>   : Show predictions for that week (e.g., 5)")
    print("  <Enter>         : Show predictions for all remaining (unplayed) games")
    print("  r               : Record a completed game (then follow prompts)")
    print("  q               : Quit interactive mode")
    print("="*70)

    while True:
        cmd = input("\nEnter command: ").strip()
        if cmd.lower() == 'q':
            break
        elif cmd.lower() == 'r':
            # Record a result
            try:
                week_str = input("Week number: ").strip()
                week = int(week_str)
                home = input("Home team: ").strip()
                away = input("Away team: ").strip()
                home_score = int(input("Home score: ").strip())
                away_score = int(input("Away score: ").strip())
            except ValueError:
                print("Invalid input. Please enter numbers where required.")
                continue

            # Validate
            if week not in schedule:
                print(f"Week {week} not in schedule.")
                continue
            if home not in elo or away not in elo:
                print("One or both teams not recognized.")
                continue
            # Check if this game exists in that week
            game_list = schedule[week]
            if (home, away) not in game_list:
                # Try reversed order (maybe user swapped home/away)
                if (away, home) in game_list:
                    print("You entered teams in reverse order. Swapping to match schedule.")
                    home, away = away, home
                else:
                    print("This game is not scheduled for that week.")
                    continue

            if (week, home, away) in played_games:
                print("This game has already been recorded.")
                continue

            is_neutral = (week, home, away) in neutral_games

            # Determine winner, loser, tie, margin
            if home_score > away_score:
                winner, loser = home, away
                tie = False
                margin = home_score - away_score
            elif away_score > home_score:
                winner, loser = away, home
                tie = False
                margin = away_score - home_score
            else:
                winner, loser = None, None
                tie = True
                margin = 0

            # Update Elo
            update_elo(home, away, winner, loser, tie, margin, elo, is_neutral)
            played_games.add((week, home, away))
            print("Game recorded. Elo updated.")

        elif cmd == '':
            # Show all remaining unplayed games
            print("\nRemaining games (not yet recorded):")
            found = False
            for week in range(1, 19):
                for home, away in schedule.get(week, []):
                    if (week, home, away) not in played_games:
                        found = True
                        is_neutral = (week, home, away) in neutral_games
                        r_home, r_away = elo[home], elo[away]
                        p_home, p_tie, p_away, _ = outcome_probs(r_home, r_away, is_neutral)
                        diff = (r_home + (0 if is_neutral else HOME_ADV)) - r_away
                        expected_margin = diff / 10.0 + (0 if is_neutral else 3.0)
                        win_prob_home = p_home + 0.5 * p_tie
                        neutral_tag = " (neutral)" if is_neutral else ""
                        print(f"Week {week}: {home} vs {away}{neutral_tag} – "
                              f"Home win prob {win_prob_home:.1%}, "
                              f"Predicted margin: {expected_margin:+.1f} points (home team)")
            if not found:
                print("All games have been recorded!")

        else:
            # Try to parse as week number
            try:
                week = int(cmd)
                if week < 1 or week > 18:
                    print("Week must be between 1 and 18.")
                    continue
                games = schedule.get(week, [])
                if not games:
                    print("No games scheduled for that week.")
                    continue
                print(f"\nPredictions for Week {week}:")
                for home, away in games:
                    is_neutral = (week, home, away) in neutral_games
                    r_home, r_away = elo[home], elo[away]
                    p_home, p_tie, p_away, _ = outcome_probs(r_home, r_away, is_neutral)
                    diff = (r_home + (0 if is_neutral else HOME_ADV)) - r_away
                    expected_margin = diff / 10.0 + (0 if is_neutral else 3.0)
                    win_prob_home = p_home + 0.5 * p_tie
                    played = " (played)" if (week, home, away) in played_games else ""
                    neutral_tag = " (neutral)" if is_neutral else ""
                    print(f"{home} vs {away}{neutral_tag}{played} – "
                          f"Home win prob {win_prob_home:.1%}, "
                          f"Predicted margin: {expected_margin:+.1f} points (home team)")
            except ValueError:
                print("Unknown command. Please enter a week number, 'r', or 'q'.")


if __name__ == "__main__":
    run_sim()