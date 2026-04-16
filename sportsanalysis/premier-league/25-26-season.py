import random
import math
import numpy as np
from collections import defaultdict, Counter
from tqdm import tqdm

# ====================== ELO RATINGS ======================
elo = {
    "Arsenal": 2050,
    "Man City": 1953,
    "Liverpool": 1915,
    "Aston Villa": 1887,
    "Man United": 1869,
    "Chelsea": 1857,
    "Brighton": 1850,
    "Newcastle": 1832,
    "Brentford": 1831,
    "Everton": 1832,
    "Bournemouth": 1837,
    "Fulham": 1795,
    "Crystal Palace": 1809,
    "Forest": 1789,
    "Leeds": 1777,
    "Tottenham": 1744,
    "West Ham": 1753,
    "Sunderland": 1713,
    "Wolves": 1689,
    "Burnley": 1670,
}

# ====================== CURRENT TABLE ======================
current = {
    "Arsenal":       {"Pts":70,"GF":62,"GA":24},
    "Man City":      {"Pts":64,"GF":63,"GA":28},
    "Man United":    {"Pts":55,"GF":57,"GA":45},
    "Aston Villa":   {"Pts":55,"GF":43,"GA":38},
    "Liverpool":     {"Pts":52,"GF":52,"GA":42},
    "Chelsea":       {"Pts":48,"GF":53,"GA":38},
    "Brentford":     {"Pts":47,"GF":48,"GA":44},
    "Everton":       {"Pts":47,"GF":39,"GA":37},
    "Brighton":      {"Pts":46,"GF":43,"GA":37},
    "Sunderland":    {"Pts":46,"GF":33,"GA":36},
    "Bournemouth":   {"Pts":45,"GF":48,"GA":49},
    "Fulham":        {"Pts":44,"GF":43,"GA":46},
    "Crystal Palace":{"Pts":42,"GF":35,"GA":36},
    "Newcastle":     {"Pts":42,"GF":45,"GA":47},
    "Leeds":         {"Pts":36,"GF":39,"GA":49},
    "Forest":        {"Pts":33,"GF":32,"GA":44},
    "West Ham":      {"Pts":32,"GF":40,"GA":57},
    "Tottenham":     {"Pts":30,"GF":40,"GA":51},
    "Burnley":       {"Pts":20,"GF":33,"GA":63},
    "Wolves":        {"Pts":17,"GF":24,"GA":58},
}

# ====================== EUROPA LEAGUE ELOS ======================
el_elos = {
    "Aston Villa": 1890,
    "Bologna": 1701,
    "Braga": 1707,
    "Celta": 1710,
    "Freiburg": 1724,
    "Forest": 1792,
    "Porto": 1809,
    "Real Betis": 1752,
}

# ====================== CHAMPIONS LEAGUE ELOS ======================
cl_elos = {
    "Real Madrid": 1930,
    "Bayern Munich": 2017,
    "Arsenal": 2052,
    "Barcelona": 1990,
    "Paris Saint-Germain": 2010,
    "Liverpool": 1960,
    "Atletico Madrid": 1950,
    "Sporting CP": 1868,
}

# ====================== CONFERENCE LEAGUE ELOS ======================
conf_elos = {
    "Crystal Palace": 1811,
    "Strasbourg": 1706,
    "Mainz 05": 1703,
    "Rayo Vallecano": 1670,
    "Fiorentina": 1668,
    "AEK Athens": 1624,
    "Shakhtar Donetsk": 1585,
    "AZ Alkmaar": 1551,
}

# ====================== FA CUP ELOS ======================
fa_elo_ratings = {
    "Arsenal": 2061,
    "Chelsea": 1885,
    "Liverpool": 1936,
    "Man City": 1941,
    "Southampton": 1810,
    "West Ham": 1746,
    "Port Vale": 1410,
    "Leeds": 1764
}

league_cup_elos = {
    "Arsenal": 2061,
    "Aston Villa": 1886,
    "Bournemouth": 1785,
    "Brighton": 1834,
    "Chelsea": 1885,
    "Crystal Palace": 1795,
    "Everton": 1815,
    "Fulham": 1795,
    "Ipswich": 1700,
    "Liverpool": 1936,
    "Man City": 1941,
    "Newcastle": 1853,
    "Forest": 1785,
    "Southampton": 1810,
    "Tottenham": 1769,
    "West Ham": 1746,
    "Wolves": 1701
}

# ====================== FA CUP FUNCTIONS ======================
def simulate_fa_cup_match(home_team, away_team):
    home_elo = fa_elo_ratings.get(home_team, 1800) + 100  # home advantage
    away_elo = fa_elo_ratings.get(away_team, 1800)
    diff = home_elo - away_elo
    p_home = 1 / (1 + 10 ** (-diff / 400))
    if random.random() < p_home:
        return home_team
    else:
        return away_team

def simulate_full_fa_cup_tournament():
    # SF matches
    sf_matches = [
        ("Man City", "Southampton"),
        ("Chelsea", "Leeds")
    ]
    sf_winners = [simulate_fa_cup_match(home, away) for home, away in sf_matches]
    # Final
    winner = simulate_fa_cup_match(sf_winners[0], sf_winners[1])
    return winner

def simulate_league_cup_match(home_team, away_team):
    home_elo = league_cup_elos.get(home_team, 1800) + 100
    away_elo = league_cup_elos.get(away_team, 1800)
    diff = home_elo - away_elo
    p_home = 1 / (1 + 10 ** (-diff / 400))
    if random.random() < p_home:
        return home_team
    else:
        return away_team

def simulate_full_league_cup_tournament():
    # Simplified League Cup simulation
    # Assume quarter-finals
    qf_matches = [
        ("Man City", "Liverpool"),
        ("Chelsea", "Newcastle"),
        ("Arsenal", "Brighton"),
        ("Tottenham", "Fulham")
    ]
    qf_winners = [simulate_league_cup_match(home, away) for home, away in qf_matches]
    sf_matches = [
        (qf_winners[0], qf_winners[3]),
        (qf_winners[1], qf_winners[2])
    ]
    sf_winners = [simulate_league_cup_match(home, away) for home, away in sf_matches]
    winner = simulate_league_cup_match(sf_winners[0], sf_winners[1])
    return winner

# ====================== EUROPA LEAGUE FUNCTIONS ======================
def el_poisson_random(lam):
    if lam < 0:
        lam = 0
    L = math.exp(-lam)
    k = 0
    p = 1.0
    while True:
        k += 1
        p *= random.random()
        if p <= L:
            return k - 1

def el_get_expected_goals(home_elo, away_elo):
    diff = home_elo - away_elo
    home_lambda = 1.4 + (diff * 0.001)
    away_lambda = 1.1 - (diff * 0.001)
    home_lambda = max(0.6, min(4.0, home_lambda))
    away_lambda = max(0.6, min(4.0, away_lambda))
    return home_lambda, away_lambda

def el_simulate_penalties(team_a, team_b, elos_dict):
    diff = elos_dict[team_a] - elos_dict[team_b]
    prob_a = 1 / (1 + 10 ** (-diff / 400))
    return team_a if random.random() < prob_a else team_b

def el_simulate_two_leg_tie(team_a, team_b, first_leg_home_is_a, elos_dict):
    if first_leg_home_is_a:
        h_l1, a_l1 = el_get_expected_goals(elos_dict[team_a], elos_dict[team_b])
        g_a1 = el_poisson_random(h_l1)
        g_b1 = el_poisson_random(a_l1)
        h_l2, a_l2 = el_get_expected_goals(elos_dict[team_b], elos_dict[team_a])
        g_b2 = el_poisson_random(h_l2)
        g_a2 = el_poisson_random(a_l2)
    else:
        h_l1, a_l1 = el_get_expected_goals(elos_dict[team_b], elos_dict[team_a])
        g_b1 = el_poisson_random(h_l1)
        g_a1 = el_poisson_random(a_l1)
        h_l2, a_l2 = el_get_expected_goals(elos_dict[team_a], elos_dict[team_b])
        g_a2 = el_poisson_random(h_l2)
        g_b2 = el_poisson_random(a_l2)

    total_a = g_a1 + g_a2
    total_b = g_b1 + g_b2

    if total_a > total_b:
        return team_a
    elif total_a < total_b:
        return team_b
    else:
        return el_simulate_penalties(team_a, team_b, elos_dict)

def el_simulate_final(team_a, team_b, elos_dict):
    diff = elos_dict[team_a] - elos_dict[team_b]
    lambda_a = 1.25 + (diff * 0.001)
    lambda_b = 1.25 - (diff * 0.001)
    lambda_a = max(0.6, min(4.0, lambda_a))
    lambda_b = max(0.6, min(4.0, lambda_b))
    g_a = el_poisson_random(lambda_a)
    g_b = el_poisson_random(lambda_b)
    if g_a > g_b:
        return team_a
    elif g_a < g_b:
        return team_b
    else:
        return el_simulate_penalties(team_a, team_b, elos_dict)

# ====================== CHAMPIONS LEAGUE FUNCTIONS ======================
def cl_poisson_random(lam):
    if lam < 0:
        lam = 0
    L = math.exp(-lam)
    k = 0
    p = 1.0
    while True:
        k += 1
        p *= random.random()
        if p <= L:
            return k - 1

def cl_get_expected_goals(home_elo, away_elo):
    diff = home_elo - away_elo
    home_lambda = 1.5 + (diff * 0.001)
    away_lambda = 1.2 - (diff * 0.001)
    home_lambda = max(0.6, min(4.0, home_lambda))
    away_lambda = max(0.6, min(4.0, away_lambda))
    return home_lambda, away_lambda

def cl_simulate_penalties(team_a, team_b, elos_dict):
    diff = elos_dict[team_a] - elos_dict[team_b]
    prob_a = 1 / (1 + 10 ** (-diff / 400))
    return team_a if random.random() < prob_a else team_b

def cl_simulate_two_leg_tie(team_a, team_b, first_leg_home_is_a, elos_dict):
    if first_leg_home_is_a:
        h_l1, a_l1 = cl_get_expected_goals(elos_dict[team_a], elos_dict[team_b])
        g_a1 = cl_poisson_random(h_l1)
        g_b1 = cl_poisson_random(a_l1)
        h_l2, a_l2 = cl_get_expected_goals(elos_dict[team_b], elos_dict[team_a])
        g_b2 = cl_poisson_random(h_l2)
        g_a2 = cl_poisson_random(a_l2)
    else:
        h_l1, a_l1 = cl_get_expected_goals(elos_dict[team_b], elos_dict[team_a])
        g_b1 = cl_poisson_random(h_l1)
        g_a1 = cl_poisson_random(a_l1)
        h_l2, a_l2 = cl_get_expected_goals(elos_dict[team_a], elos_dict[team_b])
        g_a2 = cl_poisson_random(h_l2)
        g_b2 = cl_poisson_random(a_l2)

    total_a = g_a1 + g_a2
    total_b = g_b1 + g_b2

    if total_a > total_b:
        return team_a
    elif total_a < total_b:
        return team_b
    else:
        return cl_simulate_penalties(team_a, team_b, elos_dict)

def cl_simulate_final(team_a, team_b, elos_dict):
    diff = elos_dict[team_a] - elos_dict[team_b]
    lambda_a = 1.5 + (diff * 0.001)
    lambda_b = 1.5 - (diff * 0.001)
    lambda_a = max(0.6, min(4.0, lambda_a))
    lambda_b = max(0.6, min(4.0, lambda_b))
    g_a = cl_poisson_random(lambda_a)
    g_b = cl_poisson_random(lambda_b)
    if g_a > g_b:
        return team_a
    elif g_a < g_b:
        return team_b
    else:
        return cl_simulate_penalties(team_a, team_b, elos_dict)

# ====================== CONFERENCE LEAGUE FUNCTIONS ======================
def conf_poisson_random(lam):
    if lam < 0:
        lam = 0
    L = math.exp(-lam)
    k = 0
    p = 1.0
    while True:
        k += 1
        p *= random.random()
        if p <= L:
            return k - 1

def conf_get_expected_goals(home_elo, away_elo):
    diff = home_elo - away_elo
    home_lambda = 1.4 + (diff * 0.001)
    away_lambda = 1.1 - (diff * 0.001)
    home_lambda = max(0.6, min(4.0, home_lambda))
    away_lambda = max(0.6, min(4.0, away_lambda))
    return home_lambda, away_lambda

def conf_simulate_penalties(team_a, team_b, elos_dict):
    diff = elos_dict[team_a] - elos_dict[team_b]
    prob_a = 1 / (1 + 10 ** (-diff / 400))
    return team_a if random.random() < prob_a else team_b

def conf_simulate_two_leg_tie(team_a, team_b, first_leg_home_is_a, elos_dict):
    if first_leg_home_is_a:
        h_l1, a_l1 = conf_get_expected_goals(elos_dict[team_a], elos_dict[team_b])
        g_a1 = conf_poisson_random(h_l1)
        g_b1 = conf_poisson_random(a_l1)
        h_l2, a_l2 = conf_get_expected_goals(elos_dict[team_b], elos_dict[team_a])
        g_b2 = conf_poisson_random(h_l2)
        g_a2 = conf_poisson_random(a_l2)
    else:
        h_l1, a_l1 = conf_get_expected_goals(elos_dict[team_b], elos_dict[team_a])
        g_b1 = conf_poisson_random(h_l1)
        g_a1 = conf_poisson_random(a_l1)
        h_l2, a_l2 = conf_get_expected_goals(elos_dict[team_a], elos_dict[team_b])
        g_a2 = conf_poisson_random(h_l2)
        g_b2 = conf_poisson_random(a_l2)

    total_a = g_a1 + g_a2
    total_b = g_b1 + g_b2

    if total_a > total_b:
        return team_a
    elif total_a < total_b:
        return team_b
    else:
        return conf_simulate_penalties(team_a, team_b, elos_dict)

def conf_simulate_final(team_a, team_b, elos_dict):
    diff = elos_dict[team_a] - elos_dict[team_b]
    lambda_a = 1.25 + (diff * 0.001)
    lambda_b = 1.25 - (diff * 0.001)
    lambda_a = max(0.6, min(4.0, lambda_a))
    lambda_b = max(0.6, min(4.0, lambda_b))
    g_a = conf_poisson_random(lambda_a)
    g_b = conf_poisson_random(lambda_b)
    if g_a > g_b:
        return team_a
    elif g_a < g_b:
        return team_b
    else:
        return conf_simulate_penalties(team_a, team_b, elos_dict)

# ====================== FIXTURES ======================
fixtures = [
    # Round 31 (postponed)
    ("Crystal Palace","Man City"),
    # Round 33
    ("Brentford","Fulham"), ("Leeds","Wolves"), ("Newcastle","Bournemouth"),
    ("Tottenham","Brighton"), ("Chelsea","Man United"), ("Aston Villa","Sunderland"),
    ("Everton","Liverpool"), ("Forest","Burnley"), ("Man City","Arsenal"),
    ("Crystal Palace","West Ham"),
    # Round 34
    ("Brighton","Chelsea"), ("Bournemouth","Leeds"), ("Burnley","Man City"),
    ("Sunderland","Forest"), ("Fulham","Aston Villa"), ("Liverpool","Crystal Palace"),
    ("West Ham","Everton"), ("Wolves","Tottenham"), ("Arsenal","Newcastle"),
    ("Man United","Brentford"),
    # Round 35
    ("Leeds","Burnley"), ("Aston Villa","Tottenham"), ("Bournemouth","Crystal Palace"),
    ("Brentford","West Ham"), ("Newcastle","Brighton"), ("Wolves","Sunderland"),
    ("Arsenal","Fulham"), ("Man United","Liverpool"), ("Chelsea","Forest"),
    ("Everton","Man City"),
    # Round 36
    ("Liverpool","Chelsea"), ("Brighton","Wolves"), ("Burnley","Aston Villa"),
    ("Crystal Palace","Everton"), ("Fulham","Bournemouth"), ("Sunderland","Man United"),
    ("Man City","Brentford"), ("Forest","Newcastle"), ("West Ham","Arsenal"),
    ("Tottenham","Leeds"),
    # Round 37
    ("Arsenal","Burnley"), ("Aston Villa","Liverpool"), ("Bournemouth","Man City"),
    ("Brentford","Crystal Palace"), ("Chelsea","Tottenham"), ("Everton","Sunderland"),
    ("Leeds","Brighton"), ("Man United","Forest"), ("Newcastle","West Ham"),
    ("Wolves","Fulham"),
    # Round 38
    ("Brighton","Man United"), ("Burnley","Wolves"), ("Crystal Palace","Arsenal"),
    ("Fulham","Newcastle"), ("Liverpool","Brentford"), ("Man City","Aston Villa"),
    ("Forest","Bournemouth"), ("Sunderland","Chelsea"), ("Tottenham","Everton"),
    ("West Ham","Leeds"),
]

# ====================== FORM ADJUSTMENTS ======================
# Based on current W-L differential per game played * 50
form_adjustment = {
    "Arsenal": (21 - 4) / 32 * 50,        # 17/32 * 50 ≈ 26.56
    "Man City": (19 - 5) / 31 * 50,       # 14/31 * 50 ≈ 22.58
    "Man United": (15 - 7) / 32 * 50,     # 8/32 * 50 = 12.5
    "Aston Villa": (16 - 9) / 32 * 50,    # 7/32 * 50 ≈ 10.94
    "Liverpool": (15 - 10) / 32 * 50,     # 5/32 * 50 ≈ 7.81
    "Chelsea": (13 - 10) / 32 * 50,       # 3/32 * 50 ≈ 4.69
    "Brentford": (13 - 11) / 32 * 50,     # 2/32 * 50 ≈ 3.13
    "Everton": (13 - 11) / 32 * 50,       # 2/32 * 50 ≈ 3.13
    "Brighton": (12 - 10) / 32 * 50,      # 2/32 * 50 ≈ 3.13
    "Sunderland": (12 - 10) / 32 * 50,    # 2/32 * 50 ≈ 3.13
    "Bournemouth": (10 - 7) / 32 * 50,    # 3/32 * 50 ≈ 4.69
    "Fulham": (13 - 14) / 32 * 50,        # -1/32 * 50 ≈ -1.56
    "Crystal Palace": (11 - 11) / 31 * 50,# 0/31 * 50 = 0
    "Newcastle": (12 - 14) / 32 * 50,     # -2/32 * 50 ≈ -3.13
    "Leeds": (8 - 12) / 32 * 50,          # -4/32 * 50 ≈ -6.25
    "Forest": (8 - 15) / 32 * 50,         # -7/32 * 50 ≈ -10.94
    "West Ham": (8 - 16) / 32 * 50,       # -8/32 * 50 ≈ -12.5
    "Tottenham": (7 - 16) / 32 * 50,      # -9/32 * 50 ≈ -14.06
    "Burnley": (4 - 20) / 32 * 50,        # -16/32 * 50 = -25
    "Wolves": (3 - 21) / 32 * 50,         # -18/32 * 50 ≈ -28.13
}

# ====================== W/D/L RATES ======================
wdl_rates = {
    "Arsenal": {"win": 21/32, "draw": 7/32, "loss": 4/32},
    "Man City": {"win": 19/31, "draw": 7/31, "loss": 5/31},
    "Man United": {"win": 15/32, "draw": 10/32, "loss": 7/32},
    "Aston Villa": {"win": 16/32, "draw": 7/32, "loss": 9/32},
    "Liverpool": {"win": 15/32, "draw": 7/32, "loss": 10/32},
    "Chelsea": {"win": 13/32, "draw": 9/32, "loss": 10/32},
    "Brentford": {"win": 13/32, "draw": 8/32, "loss": 11/32},
    "Everton": {"win": 13/32, "draw": 8/32, "loss": 11/32},
    "Brighton": {"win": 12/32, "draw": 10/32, "loss": 10/32},
    "Sunderland": {"win": 12/32, "draw": 10/32, "loss": 10/32},
    "Bournemouth": {"win": 10/32, "draw": 15/32, "loss": 7/32},
    "Fulham": {"win": 13/32, "draw": 5/32, "loss": 14/32},
    "Crystal Palace": {"win": 11/31, "draw": 9/31, "loss": 11/31},
    "Newcastle": {"win": 12/32, "draw": 6/32, "loss": 14/32},
    "Leeds": {"win": 8/32, "draw": 12/32, "loss": 12/32},
    "Forest": {"win": 8/32, "draw": 9/32, "loss": 15/32},
    "West Ham": {"win": 8/32, "draw": 8/32, "loss": 16/32},
    "Tottenham": {"win": 7/32, "draw": 9/32, "loss": 16/32},
    "Burnley": {"win": 4/32, "draw": 8/32, "loss": 20/32},
    "Wolves": {"win": 3/32, "draw": 8/32, "loss": 21/32},
}

# ====================== INJURY PENALTIES ======================
# ELO reduction: TRACK number * 10 points (e.g., TRACK 3 = 30 points penalty)
injury_penalty = {
    "Bournemouth": 30,
    "Arsenal": 50,
    "Aston Villa": 50,
    "Brentford": 80,
    "Brighton": 40,
    "Burnley": 70,
    "Chelsea": 70,
    "Crystal Palace": 30,
    "Everton": 20,
    "Fulham": 30,
    "Leeds": 30,
    "Liverpool": 50,
    "Man City": 40,
    "Man United": 50,
    "Newcastle": 40,
    "Forest": 50,
    "Sunderland": 60,
    "Tottenham": 80,
    "West Ham": 10,
    "Wolves": 40,
}

# ====================== MODEL PARAMETERS ======================
HOME_ADVANTAGE = 33.8

# ====================== HELPER FUNCTIONS ======================
def get_adjusted_elo(team):
    penalty = injury_penalty.get(team, 0)
    adjusted_penalty = penalty * (1 - math.exp(-penalty / 80))  # nonlinear injury penalty
    return elo[team] - adjusted_penalty + form_adjustment.get(team, 0)

# ====================== MATCH ENGINE ======================
def simulate_match(home, away):
    diff = get_adjusted_elo(home) - get_adjusted_elo(away) + HOME_ADVANTAGE

    # Base expected goals (logistic scaling for diminishing returns)
    home_xg = 0.8 + 2.2 / (1 + math.exp(-diff / 250))
    away_xg = 0.8 + 2.2 / (1 + math.exp(diff / 250))

    # Closeness factor
    closeness = math.exp(-(diff**2)/(2 * 180**2))

    # W/D/L bias adjustment for expected goals
    home_bias = wdl_rates[home]["win"] - wdl_rates[home]["loss"]
    away_bias = wdl_rates[away]["win"] - wdl_rates[away]["loss"]
    bias_diff = home_bias - away_bias
    home_xg += bias_diff * 0.4
    away_xg -= bias_diff * 0.4

    # Tempo reduction (stronger effect for close games)
    tempo_factor = 1 - 0.25 * closeness
    home_xg *= tempo_factor
    away_xg *= tempo_factor

    # Draw bias for bivariate Poisson
    draw_bias = (wdl_rates[home]["draw"] + wdl_rates[away]["draw"]) / 2
    closeness_boost = closeness * draw_bias * 0.5
    lambda_shared = 0.15 + closeness_boost

    lambda_home = max(0.05, home_xg - lambda_shared)
    lambda_away = max(0.05, away_xg - lambda_shared)

    shared_goals = np.random.poisson(lambda_shared)
    home_goals = np.random.poisson(lambda_home)
    away_goals = np.random.poisson(lambda_away)

    hg = home_goals + shared_goals
    ag = away_goals + shared_goals

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
sims = 10000

title = defaultdict(int)
cl = defaultdict(int)
el = defaultdict(int)
conf = defaultdict(int)
european = defaultdict(int)
releg = defaultdict(int)
uefa_pl_win_sims = 0
avg_points = defaultdict(list)
points_distribution = defaultdict(list)

# ====================== EUROPA LEAGUE SIMULATION ======================
NUM_SIMS_EL = 10000
el_champion_counts = Counter()

el_qf_first_leg = {
    ("Real Betis", "Braga"): (1, 1),  # Real Betis home 1, Braga away 1
    ("Bologna", "Aston Villa"): (1, 3),  # Bologna home 1, Aston Villa away 3
    ("Freiburg", "Celta"): (3, 0),  # Freiburg home 3, Celta away 0
    ("Porto", "Forest"): (1, 1),  # Porto home 1, Forest away 1
}

for sim in range(NUM_SIMS_EL):
    qf_winners = {}
    # Use real first leg for Bologna vs Aston Villa
    bologna_h, villa_a = el_qf_first_leg[("Bologna", "Aston Villa")]
    h_l2, a_l2 = el_get_expected_goals(el_elos["Aston Villa"], el_elos["Bologna"])
    g_villa = el_poisson_random(h_l2) + villa_a
    g_bologna = el_poisson_random(a_l2) + bologna_h
    if g_villa > g_bologna:
        qf_winners["qf1"] = "Aston Villa"
    elif g_bologna > g_villa:
        qf_winners["qf1"] = "Bologna"
    else:
        qf_winners["qf1"] = el_simulate_penalties("Aston Villa", "Bologna", el_elos)
    # Use real first leg for Porto vs Forest
    porto_h, forest_a = el_qf_first_leg[("Porto", "Forest")]
    h_l2, a_l2 = el_get_expected_goals(el_elos["Forest"], el_elos["Porto"])
    g_forest = el_poisson_random(h_l2) + forest_a
    g_porto = el_poisson_random(a_l2) + porto_h
    if g_forest > g_porto:
        qf_winners["qf2"] = "Forest"
    elif g_porto > g_forest:
        qf_winners["qf2"] = "Porto"
    else:
        qf_winners["qf2"] = el_simulate_penalties("Forest", "Porto", el_elos)
    # Use real first leg for Real Betis vs Braga
    betis_h, braga_a = el_qf_first_leg[("Real Betis", "Braga")]
    h_l2, a_l2 = el_get_expected_goals(el_elos["Braga"], el_elos["Real Betis"])
    g_braga = el_poisson_random(h_l2) + braga_a
    g_betis = el_poisson_random(a_l2) + betis_h
    if g_braga > g_betis:
        qf_winners["qf3"] = "Braga"
    elif g_betis > g_braga:
        qf_winners["qf3"] = "Real Betis"
    else:
        qf_winners["qf3"] = el_simulate_penalties("Braga", "Real Betis", el_elos)
    # Use real first leg for Freiburg vs Celta
    freiburg_h, celta_a = el_qf_first_leg[("Freiburg", "Celta")]
    h_l2, a_l2 = el_get_expected_goals(el_elos["Celta"], el_elos["Freiburg"])
    g_celta = el_poisson_random(h_l2) + celta_a
    g_freiburg = el_poisson_random(a_l2) + freiburg_h
    if g_celta > g_freiburg:
        qf_winners["qf4"] = "Celta"
    elif g_freiburg > g_celta:
        qf_winners["qf4"] = "Freiburg"
    else:
        qf_winners["qf4"] = el_simulate_penalties("Celta", "Freiburg", el_elos)
    sf1 = el_simulate_two_leg_tie(qf_winners["qf1"], qf_winners["qf2"], True, el_elos)
    sf2 = el_simulate_two_leg_tie(qf_winners["qf3"], qf_winners["qf4"], True, el_elos)
    champion = el_simulate_final(sf1, sf2, el_elos)
    el_champion_counts[champion] += 1

el_win_probs = {team: count / NUM_SIMS_EL for team, count in el_champion_counts.items()}

# ====================== CHAMPIONS LEAGUE SIMULATION ======================
NUM_SIMS_CL = 10000
cl_champion_counts = Counter()

cl_qf_first_leg = {
    ("Paris Saint-Germain", "Liverpool"): (2, 0),
    ("Real Madrid", "Bayern Munich"): (1, 2),
    ("Barcelona", "Atletico Madrid"): (0, 2),
    ("Sporting CP", "Arsenal"): (0, 1),
}

for sim in range(NUM_SIMS_CL):
    qf_winners = {}
    psg_h, psg_a = cl_qf_first_leg[("Paris Saint-Germain", "Liverpool")]
    real_h, real_a = cl_qf_first_leg[("Real Madrid", "Bayern Munich")]
    barca_h, barca_a = cl_qf_first_leg[("Barcelona", "Atletico Madrid")]
    sporting_h, sporting_a = cl_qf_first_leg[("Sporting CP", "Arsenal")]
    
    # PSG won 2-0 on the night, progress 4-0 on aggregate
    qf_winners["qf1"] = "Paris Saint-Germain"
    
    # Bayern Munich beat Real Madrid in quarterfinals
    qf_winners["qf2"] = "Bayern Munich"
    
    h_l2, a_l2 = cl_get_expected_goals(cl_elos["Atletico Madrid"], cl_elos["Barcelona"])
    g_atl = cl_poisson_random(h_l2) + barca_a
    g_barca = cl_poisson_random(a_l2) + barca_h
    qf_winners["qf3"] = "Atletico Madrid" if g_atl > g_barca else "Barcelona"
    
    # Arsenal beat Sporting CP in quarterfinals
    qf_winners["qf4"] = "Arsenal"
    
    sf1 = cl_simulate_two_leg_tie(qf_winners["qf1"], qf_winners["qf2"], True, cl_elos)
    sf2 = cl_simulate_two_leg_tie(qf_winners["qf3"], qf_winners["qf4"], True, cl_elos)
    champion = cl_simulate_final(sf1, sf2, cl_elos)
    cl_champion_counts[champion] += 1

cl_win_probs = {team: count / NUM_SIMS_CL for team, count in cl_champion_counts.items()}

# ====================== CONFERENCE LEAGUE SIMULATION ======================
NUM_SIMS_CONF = 10000
conf_champion_counts = Counter()

conf_qf_first_leg = {
    ("Rayo Vallecano", "AEK Athens"): (3, 0),  # Rayo Vallecano home 3, AEK Athens away 0
    ("Mainz 05", "Strasbourg"): (2, 0),  # Mainz 05 home 2, Strasbourg away 0
    ("Shakhtar Donetsk", "AZ Alkmaar"): (3, 0),  # Shakhtar Donetsk home 3, AZ Alkmaar away 0
    ("Crystal Palace", "Fiorentina"): (3, 0),  # Crystal Palace home 3, Fiorentina away 0
}

for sim in range(NUM_SIMS_CONF):
    qf_winners = {}
    # Use real first leg for Crystal Palace vs Fiorentina
    palace_h, fior_a = conf_qf_first_leg[("Crystal Palace", "Fiorentina")]
    h_l2, a_l2 = conf_get_expected_goals(conf_elos["Fiorentina"], conf_elos["Crystal Palace"])
    g_fior = conf_poisson_random(h_l2) + fior_a
    g_palace = conf_poisson_random(a_l2) + palace_h
    if g_fior > g_palace:
        qf_winners["qf1"] = "Fiorentina"
    elif g_palace > g_fior:
        qf_winners["qf1"] = "Crystal Palace"
    else:
        qf_winners["qf1"] = conf_simulate_penalties("Fiorentina", "Crystal Palace", conf_elos)
    # Use real first leg for Mainz 05 vs Strasbourg
    mainz_h, stras_a = conf_qf_first_leg[("Mainz 05", "Strasbourg")]
    h_l2, a_l2 = conf_get_expected_goals(conf_elos["Strasbourg"], conf_elos["Mainz 05"])
    g_stras = conf_poisson_random(h_l2) + stras_a
    g_mainz = conf_poisson_random(a_l2) + mainz_h
    if g_stras > g_mainz:
        qf_winners["qf2"] = "Strasbourg"
    elif g_mainz > g_stras:
        qf_winners["qf2"] = "Mainz 05"
    else:
        qf_winners["qf2"] = conf_simulate_penalties("Strasbourg", "Mainz 05", conf_elos)
    # Use real first leg for Rayo Vallecano vs AEK Athens
    rayo_h, aek_a = conf_qf_first_leg[("Rayo Vallecano", "AEK Athens")]
    h_l2, a_l2 = conf_get_expected_goals(conf_elos["AEK Athens"], conf_elos["Rayo Vallecano"])
    g_aek = conf_poisson_random(h_l2) + aek_a
    g_rayo = conf_poisson_random(a_l2) + rayo_h
    if g_aek > g_rayo:
        qf_winners["qf3"] = "AEK Athens"
    elif g_rayo > g_aek:
        qf_winners["qf3"] = "Rayo Vallecano"
    else:
        qf_winners["qf3"] = conf_simulate_penalties("AEK Athens", "Rayo Vallecano", conf_elos)
    # Use real first leg for Shakhtar Donetsk vs AZ Alkmaar
    shakh_h, az_a = conf_qf_first_leg[("Shakhtar Donetsk", "AZ Alkmaar")]
    h_l2, a_l2 = conf_get_expected_goals(conf_elos["AZ Alkmaar"], conf_elos["Shakhtar Donetsk"])
    g_az = conf_poisson_random(h_l2) + az_a
    g_shakh = conf_poisson_random(a_l2) + shakh_h
    if g_az > g_shakh:
        qf_winners["qf4"] = "AZ Alkmaar"
    elif g_shakh > g_az:
        qf_winners["qf4"] = "Shakhtar Donetsk"
    else:
        qf_winners["qf4"] = conf_simulate_penalties("AZ Alkmaar", "Shakhtar Donetsk", conf_elos)
    sf1 = conf_simulate_two_leg_tie(qf_winners["qf1"], qf_winners["qf2"], True, conf_elos)
    sf2 = conf_simulate_two_leg_tie(qf_winners["qf3"], qf_winners["qf4"], True, conf_elos)
    champion = conf_simulate_final(sf1, sf2, conf_elos)
    conf_champion_counts[champion] += 1

conf_win_probs = {team: count / NUM_SIMS_CONF for team, count in conf_champion_counts.items()}

# FA Cup simulation using ELO

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

    el_winner = random.choices(list(el_win_probs.keys()), weights=list(el_win_probs.values()))[0]
    conf_winner = random.choices(list(conf_win_probs.keys()), weights=list(conf_win_probs.values()))[0]
    cl_winner = random.choices(list(cl_win_probs.keys()), weights=list(cl_win_probs.values()))[0]

    uefa_winners = {cl_winner, el_winner, conf_winner}
    if any(w in current for w in uefa_winners):
        uefa_pl_win_sims += 1

    fa_winner = simulate_full_fa_cup_tournament()
    league_cup_winner = "Man City"

    cl_teams = [ranking[i][0] for i in range(5)]  # Top 5 qualify for CL
    el_teams = [ranking[5][0]]  # 6th qualifies for EL

    # If EL winner is PL team not in CL top 5, they get CL spot
    if el_winner in current and el_winner not in cl_teams:
        cl_teams.append(el_winner)
        # Remove from EL if they were assigned there
        if el_winner in el_teams:
            el_teams.remove(el_winner)

    if fa_winner in current and fa_winner not in cl_teams and fa_winner not in el_teams:
        el_teams.append(fa_winner)

    if conf_winner in current and conf_winner not in cl_teams and conf_winner not in el_teams:
        el_teams.append(conf_winner)

    conf_team = ranking[6 + (len(el_teams) - 1)][0]
    if league_cup_winner in current and league_cup_winner not in cl_teams and league_cup_winner not in el_teams:
        conf_team = league_cup_winner

    for pos, (team, data) in enumerate(ranking, 1):
        avg_points[team].append(data["Pts"])
        points_distribution[team].append(data["Pts"])

        if pos == 1:
            title[team] += 1
        if pos >= 18:
            releg[team] += 1

    european_teams = set(cl_teams) | set(el_teams) | {conf_team}

    for team in cl_teams:
        cl[team] += 1
    for team in el_teams:
        el[team] += 1
    conf[conf_team] += 1
    for team in european_teams:
        european[team] += 1

# ====================== STATISTICS ======================
team_stats = {}
for team in current.keys():
    pts = points_distribution[team]
    avg = np.mean(pts)
    std = np.std(pts)
    p25, med, p75 = np.percentile(pts, [25, 50, 75])
    team_stats[team] = {'avg': avg, 'std': std, 'p25': p25, 'med': med, 'p75': p75}

# ====================== MATCH PROBABILITIES ======================
match_cache = {}

def get_match_probs(home, away, n_sims=10000):
    key = (home, away)
    if key not in match_cache:
        match_cache[key] = _get_match_probs(home, away, n_sims)
    return match_cache[key]

def _get_match_probs(home, away, n_sims=10000):
    home_wins = 0
    draws = 0
    away_wins = 0
    for _ in range(n_sims):
        hg, ag = simulate_match(home, away)
        if hg > ag:
            home_wins += 1
        elif hg == ag:
            draws += 1
        else:
            away_wins += 1
    return home_wins / n_sims * 100, draws / n_sims * 100, away_wins / n_sims * 100

# ====================== OUTPUT ======================
print(f"{'Team':<15}{'AvgPts':<8}{'StdDev':<8}{'Title%':<8}{'CL%':<8}{'EL%':<8}{'Conf%':<8}{'European%':<10}{'Releg%'}")
print("-" * 98)

rank = 1
for team in sorted(current.keys(), key=lambda x: sum(avg_points[x]) / sims, reverse=True):
    print(
        f"{team:<15}"
        f"{sum(avg_points[team])/sims:<8.2f}"
        f"{team_stats[team]['std']:<8.2f}"
        f"{title[team]/sims*100:<8.2f}"
        f"{cl[team]/sims*100:<8.2f}"
        f"{el[team]/sims*100:<8.2f}"
        f"{conf[team]/sims*100:<8.2f}"
        f"{european[team]/sims*100:<10.2f}"
        f"{releg[team]/sims*100:.2f}"
    )
    rank += 1

uefa_win_percent = uefa_pl_win_sims / sims * 100
print(f"\nPremier League teams win UEFA competitions: {uefa_win_percent:.2f}%")

print("\n" + "="*60)
print("MATCH PROBABILITIES (Home Win % | Draw % | Away Win %)")
print("="*60)

max_home_win = 0
max_home_match = None
max_draw = 0
max_draw_match = None
max_away_win = 0
max_away_match = None

first_home, first_away = fixtures[0]
first_hw, first_d, first_aw = get_match_probs(first_home, first_away)
max_home_win = first_hw
max_home_match = (first_home, first_away)
max_draw = first_d
max_draw_match = (first_home, first_away)
max_away_win = first_aw
max_away_match = (first_home, first_away)

for home, away in fixtures:
    hw, d, aw = get_match_probs(home, away)
    print(f"{home:<15} vs {away:<15}: {hw:<6.2f}% | {d:<6.2f}% | {aw:<6.2f}%")

    if hw > max_home_win:
        max_home_win = hw
        max_home_match = (home, away)
    if d > max_draw:
        max_draw = d
        max_draw_match = (home, away)
    if aw > max_away_win:
        max_away_win = aw
        max_away_match = (home, away)

print("\n" + "="*40)
print("EXTREME MATCH PROBABILITIES")
print("="*40)
print(f"Biggest Home Win Chance: {max_home_match[0]} vs {max_home_match[1]} - {max_home_win:.2f}%")
print(f"Most Likely Draw: {max_draw_match[0]} vs {max_draw_match[1]} - {max_draw:.2f}%")
print(f"Biggest Away Win Chance: {max_away_match[0]} vs {max_away_match[1]} - {max_away_win:.2f}%")

print("\n" + "="*60)
print("TEAM REMAINING FIXTURE PROBABILITIES")
print("="*60)

# Get remaining fixtures per team
team_fixtures = defaultdict(list)
for home, away in fixtures:
    team_fixtures[home].append(('home', away))
    team_fixtures[away].append(('away', home))

# Calculate win all / lose all / draw all probabilities
win_all = {}
lose_all = {}
draw_all = {}

for team in current.keys():
    p_win_all = 1.0
    p_lose_all = 1.0
    p_draw_all = 1.0
    
    for is_home, opponent in team_fixtures[team]:
        if is_home == 'home':
            hw, d, aw = get_match_probs(team, opponent, n_sims=1000)
            t_win = hw / 100
            t_draw = d / 100
            t_lose = aw / 100
        else:
            hw, d, aw = get_match_probs(opponent, team, n_sims=1000)
            t_win = aw / 100
            t_draw = d / 100
            t_lose = hw / 100
            
        p_win_all *= t_win
        p_lose_all *= t_lose
        p_draw_all *= t_draw
    
    win_all[team] = p_win_all * 100
    lose_all[team] = p_lose_all * 100
    draw_all[team] = p_draw_all * 100

# Calculate average win probability
avg_win_prob = {}
for team in current.keys():
    win_probs = []
    for is_home, opponent in team_fixtures[team]:
        if is_home == 'home':
            hw, d, aw = get_match_probs(team, opponent, n_sims=1000)
            win_probs.append(hw / 100)
        else:
            hw, d, aw = get_match_probs(opponent, team, n_sims=1000)
            win_probs.append(aw / 100)
    if win_probs:
        avg_win_prob[team] = sum(win_probs) / len(win_probs) * 100
    else:
        avg_win_prob[team] = 0

print(f"{'Team':<15}{'Win All %':<12}{'Lose All %':<12}{'Draw All %':<12}{'Avg Win %'}")
print("-" * 65)
for team in sorted(current.keys(), key=lambda x: win_all[x], reverse=True):
    print(f"{team:<15}{win_all[team]:<12.4f}{lose_all[team]:<12.4f}{draw_all[team]:<12.4f}{avg_win_prob[team]:.2f}%")

print("\n" + "="*40)
print("MOST LIKELY TEAMS")
print("="*40)
most_win_all = max(win_all.items(), key=lambda x: x[1])
most_lose_all = max(lose_all.items(), key=lambda x: x[1])
most_draw_all = max(draw_all.items(), key=lambda x: x[1])
easiest_run = max(avg_win_prob.items(), key=lambda x: x[1])

print(f"Most likely to win all remaining games: {most_win_all[0]} ({most_win_all[1]:.4f}%)")
print(f"Most likely to lose all remaining games: {most_lose_all[0]} ({most_lose_all[1]:.4f}%)")
print(f"Most likely to draw all remaining games: {most_draw_all[0]} ({most_draw_all[1]:.4f}%)")
print(f"Easiest remaining fixtures (highest avg win %): {easiest_run[0]} ({easiest_run[1]:.2f}%)")