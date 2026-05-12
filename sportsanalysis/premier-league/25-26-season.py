import random
import math
import numpy as np
from collections import defaultdict, Counter
from tqdm import tqdm
import numba
from dataclasses import dataclass
from typing import Dict, List, Tuple

@dataclass
class TeamStats:
    goals_for: int
    goals_against: int
    points: int

@dataclass
class EuropeanConfig:
    el_elos: Dict[str, float]
    cl_elos: Dict[str, float]
    conf_elos: Dict[str, float]
    fa_elo_ratings: Dict[str, float]

@dataclass
class SimulationResults:
    title: Dict[str, int]
    cl: Dict[str, int]
    el: Dict[str, int]
    conf: Dict[str, int]
    european: Dict[str, int]
    releg: Dict[str, int]
    releg_40_plus: Dict[str, int]
    points_40_plus: Dict[str, int]
    at_least_one_releg_40: int
    eight_european: int
    uefa_pl_win_sims: int
    all_draws: int
    avg_points: List[List[float]]
    points_distribution: List[List[int]]
    excitement_scores: List[float]
    max_win_points: int
    min_win_points: float

HOME_ADVANTAGE_ELO = 60
DRAW_BALANCE_THRESHOLD = 180
MAX_GOALS = 4.0
MIN_LAMBDA = 0.6
SEASON_DRAW_RATE = 0.25
BASE_HOME_WIN = 0.57
BASE_AWAY_WIN = 0.43
SCALE = 400
CLOSENESS_FACTOR = 180
SHIFT_SCALE = 0.2
GOAL_MULTIPLIER_SCALE = 400
K_FACTOR_BASE = 25
RD_FACTOR = 100
MULTIPLIER_BASE = 1
FINAL_LAMBDA = 1.25
SIMULATIONS = 25000
FA_SIMS = 1000
MATCH_SIMS = 10000
PENALTY_LAMBDA_REDUCTION = 80
INJURY_PENALTY_MAX = 4.0
FORM_MULTIPLIER = 3
EXPECTED_GOALS_DIFF_FACTOR = 0.001
POISSON_LAMBDA_BASE_HOME = 1.4
POISSON_LAMBDA_BASE_AWAY = 1.1
POISSON_LAMBDA_BASE_FINAL = 1.25
PENALTY_PROB_DIFF_SCALE = 400
EXTRA_TIME_GOALS_REDUCTION = 2
CONF_BASE_HOME = 1.4
CONF_BASE_AWAY = 1.1
CONF_FINAL_LAMBDA = 1.25
CL_BASE_HOME = 1.5
CL_BASE_AWAY = 1.2
CL_FINAL_LAMBDA = 1.5
EL_BASE_HOME = 1.4
EL_BASE_AWAY = 1.1
EL_FINAL_LAMBDA = 1.25

elo = { "Arsenal": 1862,
          "Man City": 1858,
          "Liverpool": 1709,
          "Aston Villa": 1629,
          "Man United": 1718,
          "Chelsea": 1618,
          "Brighton": 1644,
          "Newcastle": 1542,
          "Brentford": 1597,
          "Everton": 1549,
          "Bournemouth": 1651,
          "Fulham": 1514,
          "Crystal Palace": 1477,
          "Forest": 1506,
          "Leeds": 1498,
          "Tottenham": 1469,
          "West Ham": 1418,
          "Sunderland": 1451,
          "Wolves": 1256,
          "Burnley": 1312,
        }

elo_attack = elo.copy()
elo_defence = elo.copy()

rd = {
    "Arsenal": 88,
    "Man City": 83,
    "Liverpool": 79,
    "Aston Villa": 82,
    "Man United": 80,
    "Chelsea": 79,
    "Brighton": 78,
    "Newcastle": 77,
    "Brentford": 77,
    "Everton": 79,
    "Bournemouth": 78,
    "Fulham": 77,
    "Crystal Palace": 79,
    "Forest": 81,
    "Leeds": 78,
    "Tottenham": 78,
    "West Ham": 81,
    "Sunderland": 77,
    "Wolves": 97,
    "Burnley": 83,
}

current = {
    "Arsenal":        {"MP":36,"W":24,"D":7,"L":5,"GF":68,"GA":26,"GD":42,"Pts":79,"Rem":2},
    "Man City":       {"MP":35,"W":22,"D":8,"L":5,"GF":72,"GA":32,"GD":40,"Pts":74,"Rem":3},
    "Man United":     {"MP":36,"W":18,"D":11,"L":7,"GF":63,"GA":48,"GD":15,"Pts":65,"Rem":2},
    "Liverpool":      {"MP":36,"W":17,"D":8,"L":11,"GF":60,"GA":48,"GD":12,"Pts":59,"Rem":2},
    "Aston Villa":    {"MP":36,"W":17,"D":8,"L":11,"GF":50,"GA":46,"GD":4,"Pts":59,"Rem":2},
    "Bournemouth":    {"MP":36,"W":13,"D":16,"L":7,"GF":56,"GA":52,"GD":4,"Pts":55,"Rem":2},
    "Brighton":       {"MP":36,"W":14,"D":11,"L":11,"GF":52,"GA":42,"GD":10,"Pts":53,"Rem":2},
    "Brentford":      {"MP":36,"W":14,"D":9,"L":13,"GF":52,"GA":49,"GD":3,"Pts":51,"Rem":2},
    "Chelsea":        {"MP":36,"W":13,"D":10,"L":13,"GF":55,"GA":49,"GD":6,"Pts":49,"Rem":2},
    "Everton":        {"MP":36,"W":13,"D":10,"L":13,"GF":46,"GA":46,"GD":0,"Pts":49,"Rem":2},
    "Fulham":         {"MP":36,"W":14,"D":6,"L":16,"GF":44,"GA":50,"GD":-6,"Pts":48,"Rem":2},
    "Sunderland":     {"MP":36,"W":12,"D":12,"L":12,"GF":37,"GA":46,"GD":-9,"Pts":48,"Rem":2},
    "Newcastle":      {"MP":36,"W":13,"D":7,"L":16,"GF":50,"GA":52,"GD":-2,"Pts":46,"Rem":2},
    "Crystal Palace": {"MP":35,"W":11,"D":11,"L":13,"GF":38,"GA":44,"GD":-6,"Pts":44,"Rem":3},
    "Forest":         {"MP":36,"W":11,"D":10,"L":15,"GF":45,"GA":47,"GD":-2,"Pts":43,"Rem":2},
    "Leeds":          {"MP":36,"W":10,"D":14,"L":12,"GF":48,"GA":53,"GD":-5,"Pts":44,"Rem":2},
    "Tottenham":      {"MP":36,"W":9,"D":11,"L":16,"GF":46,"GA":55,"GD":-9,"Pts":38,"Rem":2},
    "West Ham":       {"MP":36,"W":9,"D":9,"L":18,"GF":42,"GA":62,"GD":-20,"Pts":36,"Rem":2},
    "Burnley":        {"MP":36,"W":4,"D":9,"L":23,"GF":37,"GA":73,"GD":-36,"Pts":21,"Rem":2},
    "Wolves":         {"MP":36,"W":3,"D":9,"L":24,"GF":25,"GA":66,"GD":-41,"Pts":18,"Rem":2},
}

total_matches = sum(d["MP"] for d in current.values()) / 2
total_draws = sum(d["D"] for d in current.values()) / 2
season_draw_rate = SEASON_DRAW_RATE

fixtures = [
   # Wednesday, May 13
    ("Man City", "Crystal Palace"),
    
    # Friday, May 15
    ("Aston Villa", "Liverpool"),
    
    # Sunday, May 17
    ("Man United", "Forest"),
    ("Brentford", "Crystal Palace"),
    ("Everton", "Sunderland"),
    ("Leeds", "Brighton"),
    ("Wolves", "Fulham"),
    ("Newcastle", "West Ham"),
    
    # Monday, May 18
    ("Arsenal", "Burnley"),
    
    # Tuesday, May 19
    ("Bournemouth", "Man City"),
    ("Chelsea", "Tottenham"),
    
    # Sunday, May 24 (Final Day - Simultaneous Kickoffs)
    ("Brighton", "Man United"),
    ("Burnley", "Wolves"),
    ("Crystal Palace", "Arsenal"),
    ("Fulham", "Newcastle"),
    ("Liverpool", "Brentford"),
    ("Man City", "Aston Villa"),
    ("Forest", "Bournemouth"),
    ("Sunderland", "Chelsea"),
    ("Tottenham", "Everton"),
    ("West Ham", "Leeds"),
]

el_elos = {
    "Aston Villa": 1875,
    "Freiburg": 1716,
    "Forest": 1842,
    "Sporting Braga": 1712,
}

cl_elos = {
    "Bayern Munich": 2008,
    "Arsenal": 2053,
    "Paris Saint-Germain": 1965,
    "Atletico Madrid": 1844,
}

conf_elos = {
    "Strasbourg": 1713,
    "Shakhtar Donetsk": 1587,
    "Rayo Vallecano": 1681,
    "Crystal Palace": 1799,
}

fa_elo_ratings = {
    "Chelsea": 1841,
    "Man City": 1970,
}

print("ELO Rankings:")
sorted_elo = sorted(elo.items(), key=lambda x: x[1], reverse=True)
for rank, (team, rating) in enumerate(sorted_elo, 1):
    print(f"{rank} {team}\t{rating}")
print()

def simulate_fa_cup_match(team_a, team_b):
    elo_a = fa_elo_ratings.get(team_a, 1800)
    elo_b = fa_elo_ratings.get(team_b, 1800)
    diff = elo_a - elo_b
    lambda_a = 1.4 + (diff * 0.001)
    lambda_b = 1.4 - (diff * 0.001)
    lambda_a = max(0.6, min(4.0, lambda_a))
    lambda_b = max(0.6, min(4.0, lambda_b))
    g_a = np.random.poisson(lambda_a)
    g_b = np.random.poisson(lambda_b)
    if g_a > g_b:
        return team_a
    elif g_a < g_b:
        return team_b
    else:
        prob_a = 1 / (1 + 10 ** (-diff / 400))
        return team_a if random.random() < prob_a else team_b

def simulate_full_fa_cup_tournament():
    return simulate_fa_cup_match("Chelsea", "Man City")

@numba.jit(nopython=True)
def get_expected_goals(home_elo, away_elo, home_base, away_base, min_lambda, max_lambda):
    diff = home_elo - away_elo
    home_lambda = home_base * math.exp(diff / 800)
    away_lambda = away_base * math.exp(-diff / 800)
    home_lambda = max(min_lambda, min(max_lambda, home_lambda))
    away_lambda = max(min_lambda, min(max_lambda, away_lambda))
    return home_lambda, away_lambda

def simulate_penalties(team_a, team_b, elos_dict):
    diff = elos_dict[team_a] - elos_dict[team_b]
    prob_a = 1 / (1 + 10 ** (-diff / 400))
    return team_a if random.random() < prob_a else team_b

def simulate_two_leg_tie(team_a, team_b, first_leg_home_is_a, elos_dict, home_base=1.4, away_base=1.1, first_leg_scores=None):
    if first_leg_scores is not None:
        if first_leg_home_is_a:
            g_a1, g_b1 = first_leg_scores
        else:
            g_b1, g_a1 = first_leg_scores
    else:
        if first_leg_home_is_a:
            h_l1, a_l1 = get_expected_goals(elos_dict[team_a], elos_dict[team_b], home_base, away_base)
            g_a1 = poisson_random(h_l1)
            g_b1 = poisson_random(a_l1)
        else:
            h_l1, a_l1 = get_expected_goals(elos_dict[team_b], elos_dict[team_a], home_base, away_base)
            g_b1 = poisson_random(h_l1)
            g_a1 = poisson_random(a_l1)

    h_l2, a_l2 = get_expected_goals(elos_dict[team_b], elos_dict[team_a], home_base, away_base) if first_leg_home_is_a else get_expected_goals(elos_dict[team_a], elos_dict[team_b], home_base, away_base)
    g_b2 = poisson_random(h_l2)
    g_a2 = poisson_random(a_l2)

    total_a = g_a1 + g_a2
    total_b = g_b1 + g_b2

    if total_a == total_b:
        extra_home_lambda = h_l2 / 2
        extra_away_lambda = a_l2 / 2
        extra_home_goals = poisson_random(extra_home_lambda)
        extra_away_goals = poisson_random(extra_away_lambda)
        if first_leg_home_is_a:
            total_b += extra_home_goals
            total_a += extra_away_goals
        else:
            total_a += extra_home_goals
            total_b += extra_away_goals

    if total_a > total_b:
        return team_a
    elif total_a < total_b:
        return team_b
    else:
        return simulate_penalties(team_a, team_b, elos_dict)

def simulate_final(team_a, team_b, elos_dict, final_lambda=1.25):
    diff = elos_dict[team_a] - elos_dict[team_b]
    lambda_a = final_lambda + (diff * 0.001)
    lambda_b = final_lambda - (diff * 0.001)
    lambda_a = max(0.6, min(4.0, lambda_a))
    lambda_b = max(0.6, min(4.0, lambda_b))
    g_a = poisson_random(lambda_a)
    g_b = poisson_random(lambda_b)
    if g_a > g_b:
        return team_a
    elif g_a < g_b:
        return team_b
    else:
        return simulate_penalties(team_a, team_b, elos_dict)

def el_simulate_two_leg_tie(team_a, team_b, first_leg_home_is_a, elos_dict, first_leg_scores=None):
    return simulate_two_leg_tie(team_a, team_b, first_leg_home_is_a, elos_dict, 1.4, 1.1, first_leg_scores)

def el_simulate_final(team_a, team_b, elos_dict):
    return simulate_final(team_a, team_b, elos_dict, 1.25)

def cl_simulate_two_leg_tie(team_a, team_b, first_leg_home_is_a, elos_dict, first_leg_scores=None):
    return simulate_two_leg_tie(team_a, team_b, first_leg_home_is_a, elos_dict, 1.5, 1.2, first_leg_scores)

def cl_simulate_final(team_a, team_b, elos_dict):
    return simulate_final(team_a, team_b, elos_dict, 1.5)

def conf_simulate_two_leg_tie(team_a, team_b, first_leg_home_is_a, elos_dict, first_leg_scores=None):
    return simulate_two_leg_tie(team_a, team_b, first_leg_home_is_a, elos_dict, 1.4, 1.1, first_leg_scores)

def conf_simulate_final(team_a, team_b, elos_dict):
    return simulate_final(team_a, team_b, elos_dict, 1.25)

form_adjustment = {
    "Arsenal": (21 - 15) * 3,
    "Man City": (24 - 15) * 3,
    "Man United": (21 - 15) * 3,
    "Aston Villa": (17 - 15) * 3,
    "Liverpool": (21 - 15) * 3,
    "Chelsea": (13 - 15) * 3,
    "Brentford": (18 - 15) * 3,
    "Bournemouth": (19 - 15) * 3,
    "Brighton": (18 - 15) * 3,
    "Everton": (16 - 15) * 3,
    "Sunderland": (15 - 15) * 3,
    "Fulham": (16 - 15) * 3,
    "Crystal Palace": (14 - 15) * 3,
    "Newcastle": (14 - 15) * 3,
    "Leeds": (15 - 15) * 3,
    "Forest": (16 - 15) * 3,
    "West Ham": (15 - 15) * 3,
    "Tottenham": (8 - 15) * 3,
    "Burnley": (6 - 15) * 3,
    "Wolves": (9 - 15) * 3,
}

wdl_rates = {
    "Arsenal": {"win": 23/35, "draw": 7/35, "loss": 5/35},
    "Man City": {"win": 21/33, "draw": 7/33, "loss": 5/33},
    "Man United": {"win": 17/34, "draw": 10/34, "loss": 7/34},
    "Aston Villa": {"win": 17/34, "draw": 7/34, "loss": 10/34},
    "Liverpool": {"win": 17/34, "draw": 7/34, "loss": 10/34},
    "Chelsea": {"win": 13/34, "draw": 9/34, "loss": 12/34},
    "Brentford": {"win": 14/35, "draw": 9/35, "loss": 12/35},
    "Bournemouth": {"win": 11/34, "draw": 16/34, "loss": 7/34},
    "Brighton": {"win": 13/35, "draw": 11/35, "loss": 11/35},
    "Everton": {"win": 13/34, "draw": 8/34, "loss": 13/34},
    "Sunderland": {"win": 12/35, "draw": 11/35, "loss": 12/35},
    "Fulham": {"win": 14/35, "draw": 6/35, "loss": 15/35},
    "Crystal Palace": {"win": 11/33, "draw": 10/33, "loss": 12/33},
    "Newcastle": {"win": 13/35, "draw": 6/35, "loss": 16/35},
    "Leeds": {"win": 10/35, "draw": 13/35, "loss": 12/35},
    "Forest": {"win": 10/34, "draw": 9/34, "loss": 15/34},
    "West Ham": {"win": 9/35, "draw": 9/35, "loss": 17/35},
    "Tottenham": {"win": 8/34, "draw": 10/34, "loss": 16/34},
    "Burnley": {"win": 4/35, "draw": 8/35, "loss": 23/35},
    "Wolves": {"win": 3/35, "draw": 9/35, "loss": 23/35},
}

injury_penalty = {
    "Bournemouth": 30,
    "Arsenal": 60,
    "Aston Villa": 20,
    "Brentford": 70,
    "Brighton": 50,
    "Burnley": 70,
    "Chelsea": 70,
    "Crystal Palace": 50,
    "Everton": 20,
    "Fulham": 30,
    "Leeds": 20,
    "Liverpool": 70,
    "Man City": 40,
    "Man United": 60,
    "Newcastle": 40,
    "Forest": 70,
    "Sunderland": 60,
    "Tottenham": 60,
    "West Ham": 10,
    "Wolves": 50,
}

team_list = list(current.keys())
num_teams = len(team_list)
team_index = {team: i for i, team in enumerate(team_list)}
current_pts = np.array([current[t]['Pts'] for t in team_list])
current_gf = np.array([current[t]['GF'] for t in team_list])
current_ga = np.array([current[t]['GA'] for t in team_list])
elo_attack_arr = np.array([elo_attack[t] for t in team_list])
elo_defence_arr = np.array([elo_defence[t] for t in team_list])
rd_arr = np.array([rd[t] for t in team_list])
form_arr = np.array([form_adjustment[t] for t in team_list])
injury_arr = np.array([injury_penalty[t] for t in team_list])
fixture_indices = [(team_index[h], team_index[a]) for h, a in fixtures]

@numba.jit(nopython=True)
def g(rd_val):
    q = math.log(10) / math.pi
    return 1 / math.sqrt(1 + 3 * q**2 * rd_val**2 / math.pi**2)

@numba.jit(nopython=True)
def poisson_random(lam):
    if lam < 0:
        lam = 0
    L = math.exp(-lam)
    k = 0
    p = 1.0
    while True:
        k += 1
        p *= np.random.random()
        if p <= L:
            return k - 1

@numba.jit(nopython=True)
def get_adjusted_ratings(idx, elo_att, elo_def, form_arr, injury_arr):
    penalty = injury_arr[idx]
    adjusted_penalty = penalty * (1 - math.exp(-penalty / 80))
    att_penalty = adjusted_penalty / 2
    def_penalty = adjusted_penalty / 2
    att = elo_att[idx] - att_penalty + form_arr[idx]
    defe = elo_def[idx] - def_penalty + form_arr[idx]
    return att, defe

@numba.jit(nopython=True)
def simulate_match(h_idx, a_idx, elo_att, elo_def, form_arr, injury_arr, min_lambda, max_goals):
    home_xg, away_xg = get_expected_goals(h_idx, a_idx, POISSON_LAMBDA_BASE_HOME, POISSON_LAMBDA_BASE_AWAY, min_lambda, max_goals)
    h_att, h_def = get_adjusted_ratings(h_idx, elo_att, elo_def, form_arr, injury_arr)
    a_att, a_def = get_adjusted_ratings(a_idx, elo_att, elo_def, form_arr, injury_arr)
    diff_home = h_att - a_def + HOME_ADVANTAGE_ELO
    diff_away = a_att - h_def
    diff = diff_home - diff_away

    base_draw = np.random.uniform(0.65 * season_draw_rate, 0.833 * season_draw_rate)
    remaining = 1 - base_draw
    base_home_win = remaining * BASE_HOME_WIN
    base_away_win = remaining * BASE_AWAY_WIN

    scale = SCALE
    closeness = math.exp(-(diff**2)/(2 * CLOSENESS_FACTOR**2))
    shift = diff / scale * SHIFT_SCALE
    p_home_win = base_home_win + shift
    p_away_win = base_away_win - shift
    p_draw = base_draw + closeness * 0.1

    total = p_home_win + p_draw + p_away_win
    p_home_win /= total
    p_draw /= total
    p_away_win /= total

    r = np.random.random()
    if r < p_home_win:
        hg = poisson_random(home_xg)
        ag = poisson_random(away_xg)
    elif r < p_home_win + p_draw:
        mean_goals = (home_xg + away_xg) / 2
        hg = poisson_random(mean_goals)
        ag = hg
    else:
        hg = poisson_random(away_xg)
        ag = poisson_random(home_xg)

    return hg, ag

def run_single_simulation(
    elo_attack_arr, elo_defence_arr, current_pts, current_gf, current_ga,
    fixture_indices, form_arr, injury_arr, team_list,
    el_win_probs, conf_win_probs, cl_win_probs, current
):
    global HOME_ADVANTAGE_ELO, POISSON_LAMBDA_BASE_HOME, POISSON_LAMBDA_BASE_AWAY, MIN_LAMBDA, MAX_GOALS, SEASON_DRAW_RATE, SCALE, K_FACTOR_BASE
    HOME_ADVANTAGE_ELO = random.uniform(50, 70)
    POISSON_LAMBDA_BASE_HOME = random.uniform(1.45, 1.65)
    POISSON_LAMBDA_BASE_AWAY = random.uniform(1.10, 1.30)
    MIN_LAMBDA = random.uniform(0.2, 0.4)
    MAX_GOALS = random.uniform(3.5, 4.5)
    SEASON_DRAW_RATE = random.uniform(0.23, 0.28)
    SCALE = random.uniform(350, 450)
    K_FACTOR_BASE = random.uniform(15, 30)

    elo_att = elo_attack_arr.copy()
    elo_def = elo_defence_arr.copy()
    pts = current_pts.copy()
    gf_arr = current_gf.copy()
    ga_arr = current_ga.copy()

    draw_count = 0
    for h_idx, a_idx in fixture_indices:
        hg, ag = simulate_match(h_idx, a_idx, elo_att, elo_def, form_arr, injury_arr, MIN_LAMBDA, MAX_GOALS)
        if hg == ag:
            draw_count += 1
        gf_arr[h_idx] += hg
        ga_arr[h_idx] += ag
        gf_arr[a_idx] += ag
        ga_arr[a_idx] += hg
        if hg > ag:
            pts[h_idx] += 3
        elif ag > hg:
            pts[a_idx] += 3
        else:
            pts[h_idx] += 1
            pts[a_idx] += 1
        update_elo(h_idx, a_idx, hg, ag, elo_att, elo_def, rd_arr)

    is_all_draws = draw_count == len(fixtures)

    table = {team_list[i]: {"Pts": pts[i], "GF": gf_arr[i], "GA": ga_arr[i]} for i in range(len(team_list))}
    excitement_score = calculate_excitement_score(table)
    ranking = sorted(
        [(team_list[i], {"Pts": pts[i], "GF": gf_arr[i], "GA": ga_arr[i]}) for i in range(len(team_list))],
        key=lambda x: (x[1]["Pts"], x[1]["GF"] - x[1]["GA"], x[1]["GF"]),
        reverse=True
    )

    el_winner = random.choices(list(el_win_probs.keys()), weights=list(el_win_probs.values()))[0]
    conf_winner = random.choices(list(conf_win_probs.keys()), weights=list(conf_win_probs.values()))[0]
    cl_winner = random.choices(list(cl_win_probs.keys()), weights=list(cl_win_probs.values()))[0]

    fa_winner = simulate_full_fa_cup_tournament()

    european_assignments = assign_europe(current, ranking, el_winner, fa_winner, conf_winner)

    win_points = ranking[0][1]["Pts"]

    releg_40_this_sim = False
    points_list = []
    for pos, (team, data) in enumerate(ranking, 1):
        points_list.append(data["Pts"])
        if pos >= 18 and data["Pts"] >= 40:
            releg_40_this_sim = True

    return {
        "is_all_draws": is_all_draws,
        "excitement_score": excitement_score,
        "ranking": ranking,
        "european_assignments": european_assignments,
        "win_points": win_points,
        "releg_40_this_sim": releg_40_this_sim,
        "points_list": points_list,
        "uefa_winners": {cl_winner, el_winner, conf_winner}
    }

@numba.jit(nopython=True)
def update_elo(h_idx, a_idx, hg, ag, elo_att, elo_def, rd_arr):
    h_att, h_def = get_adjusted_ratings(h_idx, elo_att, elo_def, form_arr, injury_arr)
    a_att, a_def = get_adjusted_ratings(a_idx, elo_att, elo_def, form_arr, injury_arr)
    diff_att = h_att - a_def + HOME_ADVANTAGE_ELO
    diff_def = a_att - h_def
    rd_avg = (rd_arr[h_idx] + rd_arr[a_idx]) / 2
    g_val = g(rd_avg)
    expected_h_att = 1 / (1 + 10 ** (-g_val * diff_att / SCALE))
    expected_a_att = 1 - expected_h_att
    expected_h_def = 1 / (1 + 10 ** (-g_val * diff_def / SCALE))
    expected_a_def = 1 - expected_h_def
    goal_diff = abs(hg - ag)
    multiplier = 1 + 0.5 * goal_diff
    if hg > ag:
        score_h_att = multiplier
        score_a_att = 0
        score_h_def = multiplier
        score_a_def = 0
    elif hg == ag:
        score_h_att = 0.5
        score_a_att = 0.5
        score_h_def = 0.5
        score_a_def = 0.5
    else:
        score_h_att = 0
        score_a_att = multiplier
        score_h_def = 0
        score_a_def = multiplier
    k_h = K_FACTOR_BASE / (1 + rd_arr[h_idx]/100)
    k_a = K_FACTOR_BASE / (1 + rd_arr[a_idx]/100)
    elo_att[h_idx] += k_h * (score_h_att - expected_h_att)
    elo_att[a_idx] += k_a * (score_a_att - expected_a_att)
    elo_def[h_idx] += k_h * (score_h_def - expected_h_def)
    elo_def[a_idx] += k_a * (score_a_def - expected_a_def)

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

def calculate_excitement_score(table):
    ranking = sorted(
        table.items(),
        key=lambda x: (
            x[1]["Pts"],
            x[1]["GF"] - x[1]["GA"],
            x[1]["GF"]
        ),
        reverse=True
    )
    
    if ranking:
        leader_pts = ranking[0][1]["Pts"]
        title_contenders = sum(1 for _, data in ranking[1:] if data["Pts"] >= leader_pts - 3)
    else:
        title_contenders = 0
    
    if len(ranking) > 3:
        fourth_pts = ranking[3][1]["Pts"]
        top4_contenders = sum(1 for _, data in ranking[4:] if data["Pts"] >= fourth_pts - 5)
    else:
        top4_contenders = 0
    
    if len(ranking) > 17:
        releg_pts = ranking[17][1]["Pts"]
        releg_contenders = sum(1 for _, data in ranking[:17] if data["Pts"] <= releg_pts + 3)
    else:
        releg_contenders = 0
    
    raw_score = (title_contenders * 2 + top4_contenders + releg_contenders * 1.5) / 5
    return min(10, raw_score)

def assign_top_positions(ranking: List[Tuple[str, Dict]], european_assignments: Dict[str, str]) -> None:
    for i in range(min(5, len(ranking))):
        european_assignments[ranking[i][0]] = "CL"
    if len(ranking) > 5:
        european_assignments[ranking[5][0]] = "EL"
    if len(ranking) > 6:
        european_assignments[ranking[6][0]] = "Conf"

def assign_fa_cup_winner(fa_winner: str, current_table: Dict[str, Dict], european_assignments: Dict[str, str]) -> None:
    if fa_winner in current_table and fa_winner not in european_assignments:
        european_assignments[fa_winner] = "EL"

def assign_conf_winner(conf_winner: str, current_table: Dict[str, Dict], european_assignments: Dict[str, str]) -> None:
    if conf_winner in current_table:
        if conf_winner in european_assignments and european_assignments[conf_winner] == "Conf":
            european_assignments[conf_winner] = "EL"
        elif conf_winner not in european_assignments:
            european_assignments[conf_winner] = "EL"

def assign_el_winner(el_winner: str, current_table: Dict[str, Dict], european_assignments: Dict[str, str]) -> None:
    if el_winner in current_table:
        if el_winner not in european_assignments:
            european_assignments[el_winner] = "CL"
        elif european_assignments[el_winner] != "CL":
            european_assignments[el_winner] = "CL"

def apply_special_rules(el_winner: str, fa_winner: str, conf_winner: str, current_table: Dict[str, Dict], ranking: List[Tuple[str, Dict]], european_assignments: Dict[str, str]) -> None:
    if el_winner == "Aston Villa" and len(ranking) > 4 and ranking[4][0] == "Aston Villa":
        if len(ranking) > 5:
            european_assignments[ranking[5][0]] = "CL"

    if fa_winner in current_table and len(ranking) > 5 and ranking[5][0] == fa_winner:
        if len(ranking) > 6:
            european_assignments[ranking[6][0]] = "EL"
        if len(ranking) > 7:
            european_assignments[ranking[7][0]] = "Conf"

    if conf_winner in current_table and len(ranking) > 6 and ranking[6][0] == conf_winner:
        if len(ranking) > 7:
            european_assignments[ranking[7][0]] = "Conf"

def assign_europe(current_table: Dict[str, Dict], ranking: List[Tuple[str, Dict]], el_winner: str, fa_winner: str, conf_winner: str) -> Dict[str, str]:
    european_assignments = {}
    assign_top_positions(ranking, european_assignments)
    assign_fa_cup_winner(fa_winner, current_table, european_assignments)
    assign_conf_winner(conf_winner, current_table, european_assignments)
    assign_el_winner(el_winner, current_table, european_assignments)
    apply_special_rules(el_winner, fa_winner, conf_winner, current_table, ranking, european_assignments)
    return european_assignments

sims = 25000

title = defaultdict(int)
cl = defaultdict(int)
el = defaultdict(int)
conf = defaultdict(int)
european = defaultdict(int)
releg = defaultdict(int)
releg_40_plus = defaultdict(int)
points_40_plus = defaultdict(int)
at_least_one_releg_40 = 0
eight_european = 0
uefa_pl_win_sims = 0
all_draws = 0
sixth_cl = 0
avg_points = [[] for _ in range(num_teams)]
points_distribution = [[] for _ in range(num_teams)]
excitement_scores = []
max_win_points = 0
min_win_points = float('inf')
win_points_list = []
avg_win_points = 0.0

el_champion_counts = Counter()

for sim in range(10000):
    sf1 = "Aston Villa"
    sf2 = "Freiburg"
    champion = el_simulate_final(sf1, sf2, el_elos)
    el_champion_counts[champion] += 1

el_win_probs = {team: count / 10000 for team, count in el_champion_counts.items()}

cl_champion_counts = Counter()

for sim in range(10000):
    sf1_winner = "Paris Saint-Germain"
    sf2_winner = "Arsenal"
    champion = cl_simulate_final(sf1_winner, sf2_winner, cl_elos)
    cl_champion_counts[champion] += 1

cl_win_probs = {team: count / 10000 for team, count in cl_champion_counts.items()}

conf_champion_counts = Counter()

for sim in range(10000):
    sf1 = "Crystal Palace"
    sf2 = "Rayo Vallecano"
    champion = conf_simulate_final(sf1, sf2, conf_elos)
    conf_champion_counts[champion] += 1

conf_win_probs = {team: count / 10000 for team, count in conf_champion_counts.items()}

fa_sims = 1000

print(f"Running {sims:,} simulations...")

completed_sims = 0
try:
    for _ in tqdm(range(sims), desc="Simulating", unit="sim"):
        result = run_single_simulation(
            elo_attack_arr, elo_defence_arr, current_pts, current_gf, current_ga,
            fixture_indices, form_arr, injury_arr, team_list,
            el_win_probs, conf_win_probs, cl_win_probs, current
        )

        if result["is_all_draws"]:
            all_draws += 1

        excitement_scores.append(result["excitement_score"])

        ranking = result["ranking"]
        european_assignments = result["european_assignments"]
        win_points = result["win_points"]
        releg_40_this_sim = result["releg_40_this_sim"]
        points_list = result["points_list"]
        uefa_winners = result["uefa_winners"]

        if any(w in current for w in uefa_winners):
            uefa_pl_win_sims += 1

        european_teams = set(european_assignments.keys())
        if len(european_teams) >= 9:
            eight_european += 1

        if len(ranking) > 5 and ranking[5][0] in european_assignments and european_assignments[ranking[5][0]] == "CL":
            sixth_cl += 1

        for team, comp in european_assignments.items():
            if comp == 'CL':
                cl[team] += 1
            elif comp == 'EL':
                el[team] += 1
            else:
                conf[team] += 1
            european[team] += 1

        for i, pts in enumerate(points_list):
            avg_points[i].append(pts)
            points_distribution[i].append(pts)

        title[ranking[0][0]] += 1
        max_win_points = max(max_win_points, win_points)
        min_win_points = min(min_win_points, win_points)
        win_points_list.append(win_points)

        for pos, (team, data) in enumerate(ranking, 1):
            if pos >= 18:
                releg[team] += 1
                if data["Pts"] >= 40:
                    releg_40_plus[team] += 1
            if data["Pts"] >= 40:
                points_40_plus[team] += 1
        if releg_40_this_sim:
            at_least_one_releg_40 += 1

        completed_sims += 1

except KeyboardInterrupt:
    print(f"\nSimulation interrupted after {completed_sims} simulations.")
    if completed_sims == 0:
        print("No simulations completed. Exiting.")
        exit()
    sims = completed_sims

avg_win_points = sum(win_points_list) / len(win_points_list) if win_points_list else 0.0

team_stats = {}
releg_40_prob = {}
for i, team in enumerate(team_list):
    pts = points_distribution[i]
    avg = np.mean(pts)
    std = np.std(pts)
    p25, med, p75 = np.percentile(pts, [25, 50, 75])
    team_stats[team] = {'avg': avg, 'std': std, 'p25': p25, 'med': med, 'p75': p75}

    if points_40_plus[team] > 0:
        releg_40_prob[team] = (releg_40_plus[team] / points_40_plus[team]) * 100
    else:
        releg_40_prob[team] = 0.0

match_cache = {}

def get_match_probs(home, away, n_sims=10000):
    key = (home, away)
    if key not in match_cache:
        match_cache[key] = _get_match_probs(home, away, n_sims)
    return match_cache[key]

def _get_match_probs(home, away, n_sims=1000):
    home_wins = 0
    draws = 0
    away_wins = 0
    h_idx = team_index[home]
    a_idx = team_index[away]
    for _ in range(n_sims):
        hg, ag = simulate_match(h_idx, a_idx, elo_attack_arr, elo_defence_arr, form_arr, injury_arr, MIN_LAMBDA, MAX_GOALS)
        if hg > ag:
            home_wins += 1
        elif hg == ag:
            draws += 1
        else:
            away_wins += 1
    return home_wins / n_sims * 100, draws / n_sims * 100, away_wins / n_sims * 100

print(f"{'Team':<15}{'AvgPts':<8}{'StdDev':<8}{'Title%':<8}{'CL%':<8}{'EL%':<8}{'Conf%':<8}{'European%':<10}{'Releg%':<8}")
print("-" * 106)

rank = 1
for team in sorted(current.keys(), key=lambda x: sum(avg_points[team_index[x]]) / sims, reverse=True):
    print(
        f"{team:<15}"
        f"{sum(avg_points[team_index[team]])/sims:<8.2f}"
        f"{team_stats[team]['std']:<8.2f}"
        f"{title[team]/sims*100:<8.2f}"
        f"{cl[team]/sims*100:<8.2f}"
        f"{el[team]/sims*100:<8.2f}"
        f"{conf[team]/sims*100:<8.2f}"
        f"{european[team]/sims*100:<10.2f}"
        f"{releg[team]/sims*100:<8.2f}"

    )
    rank += 1

uefa_win_percent = uefa_pl_win_sims / sims * 100

chelsea_wins = 0
man_city_wins = 0
for _ in range(fa_sims):
    winner = simulate_fa_cup_match("Chelsea", "Man City")
    if winner == "Chelsea":
        chelsea_wins += 1
    else:
        man_city_wins += 1

chelsea_win_prob = chelsea_wins / fa_sims * 100
man_city_win_prob = man_city_wins / fa_sims * 100

print(f"FA Cup Win Probabilities:")
print(f"Chelsea: {chelsea_win_prob:.2f}%")
print(f"Man City: {man_city_win_prob:.2f}%")

print(f"Probability of at least one Premier League team wins one UEFA competition: {uefa_win_percent:.2f}%")

print(f"Max points to win the league: {max_win_points}")
print(f"Min points to win the league: {min_win_points}")
print(f"Average points to win the league: {avg_win_points:.2f}")

print("\n========================================")
print("UEFA COMPETITION WIN PROBABILITIES")
print("========================================")

print("CL Win Probabilities:")
for team, prob in sorted(cl_win_probs.items(), key=lambda x: x[1], reverse=True):
    print(f"{team}: {prob*100:.2f}%")

print("EL Win Probabilities:")
for team, prob in sorted(el_win_probs.items(), key=lambda x: x[1], reverse=True):
    print(f"{team}: {prob*100:.2f}%")

print("Conf Win Probabilities:")
for team, prob in sorted(conf_win_probs.items(), key=lambda x: x[1], reverse=True):
    print(f"{team}: {prob*100:.2f}%")

at_least_one_releg_40_percent = at_least_one_releg_40 / sims * 100
print(f"Probability that at least one team is relegated with 40+ points: {at_least_one_releg_40_percent:.3f}%")

eight_european_percent = eight_european / sims * 100
print(f"Probability that at least 9 teams qualify for European competitions: {eight_european_percent:.3f}%")

avg_excitement = sum(excitement_scores) / sims
print(f"Average excitement score for the final day (out of 10): {avg_excitement:.2f}")

all_draws_percent = all_draws / sims * 100
print(f"Probability that all remaining games are draws: {all_draws_percent:.3f}%")

sixth_cl_percent = sixth_cl / sims * 100
print(f"Probability that 6th place qualifies for Champions League: {sixth_cl_percent:.3f}%")

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

team_fixtures = defaultdict(list)
for home, away in fixtures:
    team_fixtures[home].append(('home', away))
    team_fixtures[away].append(('away', home))

win_all = {}
lose_all = {}
draw_all = {}

for team in current.keys():
    p_win_all = 1.0
    p_lose_all = 1.0
    p_draw_all = 1.0
    
    for is_home, opponent in team_fixtures[team]:
        if is_home == 'home':
            hw, d, aw = get_match_probs(team, opponent, 100)
            t_win = hw / 100
            t_draw = d / 100
            t_lose = aw / 100
        else:
            hw, d, aw = get_match_probs(opponent, team, 100)
            t_win = aw / 100
            t_draw = d / 100
            t_lose = hw / 100
            
        p_win_all *= t_win
        p_lose_all *= t_lose
        p_draw_all *= t_draw
    
    win_all[team] = p_win_all * 100
    lose_all[team] = p_lose_all * 100
    draw_all[team] = p_draw_all * 100

avg_win_prob = {}
for team in current.keys():
    win_probs = []
    for is_home, opponent in team_fixtures[team]:
        if is_home == 'home':
            hw, d, aw = get_match_probs(team, opponent, 1000)
            win_probs.append(hw / 100)
        else:
            hw, d, aw = get_match_probs(opponent, team, 1000)
            win_probs.append(aw / 100)
    if win_probs:
        avg_win_prob[team] = sum(win_probs) / len(win_probs) * 100
    else:
        avg_win_prob[team] = 0

print(f"{'Team':<15}{'Win All %':<12}{'Lose All %':<12}{'Draw All %':<12}{'Avg Win %'}")
print("-" * 65)
for rank, team in enumerate(sorted(current.keys(), key=lambda x: avg_win_prob[x], reverse=True), 1):
    print(f"{rank:<3}{team:<15}{win_all[team]:<12.4f}{lose_all[team]:<12.4f}{draw_all[team]:<12.4f}{avg_win_prob[team]:.2f}%")

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

print("\n" + "="*40)
print("RELEGATION OCCURRENCES OUT OF SIMULATIONS")
print("="*40)
for team in sorted(current.keys(), key=lambda x: releg[x], reverse=True):
    print(f"{team}: {releg[team]} out of {sims}")