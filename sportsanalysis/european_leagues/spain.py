import random
import math
import numpy as np
from collections import defaultdict, Counter
from tqdm import tqdm

# ====================== ELO RATINGS WITH UNCERTAINTY (Glicko-inspired) ======================
q = math.log(10) / 400
def g(rd_val):
    return 1 / math.sqrt(1 + 3 * q**2 * rd_val**2 / math.pi**2)

elo = { "Barcelona": 1974,
          "Real Madrid": 1921,
          "Villarreal": 1766,
          "Atletico Madrid": 1852,
          "Real Betis": 1741,
          "Celta Vigo": 1692,
          "Getafe": 1655,
          "Athletic Bilbao": 1704,
          "Real Sociedad": 1685,
          "Osasuna": 1680,
          "Rayo Vallecano": 1681,
          "Valencia": 1657,
          "Espanol": 1612,
          "Elche": 1617,
          "RCD Mallorca": 1650,
          "Girona": 1637,
          "Sevilla": 1605,
          "Alaves": 1617,
          "Levante": 1612,
          "Real Oviedo": 1575,
}

# ====================== ATTACK AND DEFENCE RATINGS ======================
elo_attack = elo.copy()
elo_defence = elo.copy()

# ====================== GLICKO-2 RD (Rating Deviation) ======================
rd = {
    "Barcelona": 85,
    "Real Madrid": 80,
    "Villarreal": 85,
    "Atletico Madrid": 82,
    "Real Betis": 80,
    "Celta Vigo": 78,
    "Getafe": 79,
    "Athletic Bilbao": 77,
    "Real Sociedad": 77,
    "Osasuna": 79,
    "Rayo Vallecano": 81,
    "Valencia": 78,
    "Espanol": 79,
    "Elche": 78,
    "RCD Mallorca": 80,
    "Girona": 81,
    "Sevilla": 77,
    "Alaves": 97,
    "Levante": 83,
    "Real Oviedo": 83,
}

# ====================== CURRENT TABLE ======================
current = {
    "Barcelona":        {"MP":34,"W":29,"D":1,"L":4,"GF":89,"GA":31,"GD":58,"Pts":88,"Rem":4},
    "Real Madrid":       {"MP":34,"W":24,"D":5,"L":5,"GF":70,"GA":31,"GD":39,"Pts":77,"Rem":4},
    "Villarreal":     {"MP":34,"W":21,"D":5,"L":8,"GF":64,"GA":39,"GD":25,"Pts":68,"Rem":4},
    "Atletico Madrid":      {"MP":34,"W":19,"D":6,"L":9,"GF":58,"GA":37,"GD":21,"Pts":63,"Rem":4},
    "Real Betis":    {"MP":34,"W":13,"D":14,"L":7,"GF":52,"GA":41,"GD":11,"Pts":53,"Rem":4},
    "Celta Vigo":    {"MP":34,"W":12,"D":11,"L":11,"GF":48,"GA":44,"GD":4,"Pts":47,"Rem":4},
    "Getafe":      {"MP":34,"W":13,"D":5,"L":16,"GF":28,"GA":36,"GD":-8,"Pts":44,"Rem":4},
    "Athletic Bilbao":       {"MP":34,"W":13,"D":5,"L":16,"GF":40,"GA":50,"GD":-10,"Pts":44,"Rem":4},
    "Real Sociedad":        {"MP":34,"W":11,"D":10,"L":13,"GF":52,"GA":53,"GD":-1,"Pts":43,"Rem":4},
    "Osasuna":        {"MP":34,"W":11,"D":9,"L":14,"GF":40,"GA":42,"GD":-2,"Pts":42,"Rem":4},
    "Rayo Vallecano":     {"MP":34,"W":10,"D":12,"L":12,"GF":35,"GA":41,"GD":-6,"Pts":42,"Rem":4},
    "Valencia":          {"MP":34,"W":10,"D":9,"L":15,"GF":37,"GA":50,"GD":-13,"Pts":39,"Rem":4},
    "Espanol": {"MP":34,"W":10,"D":9,"L":15,"GF":37,"GA":51,"GD":-14,"Pts":39,"Rem":4},
    "Elche":         {"MP":34,"W":9,"D":11,"L":14,"GF":45,"GA":53,"GD":-8,"Pts":38,"Rem":4},
    "RCD Mallorca":      {"MP":34,"W":10,"D":8,"L":16,"GF":42,"GA":51,"GD":-9,"Pts":38,"Rem":4},
    "Girona":       {"MP":34,"W":9,"D":11,"L":14,"GF":36,"GA":51,"GD":-15,"Pts":38,"Rem":4},
    "Sevilla":         {"MP":34,"W":10,"D":7,"L":17,"GF":41,"GA":55,"GD":-14,"Pts":37,"Rem":4},
    "Alaves":       {"MP":34,"W":9,"D":9,"L":16,"GF":40,"GA":53,"GD":-13,"Pts":36,"Rem":4},
    "Levante":        {"MP":34,"W":8,"D":9,"L":17,"GF":38,"GA":55,"GD":-17,"Pts":33,"Rem":4},
    "Real Oviedo":        {"MP":34,"W":6,"D":10,"L":18,"GF":26,"GA":54,"GD":-28,"Pts":28,"Rem":4},
}

# Compute season draw rate for base probabilities
total_matches = sum(d["MP"] for d in current.values())
total_draws = sum(d["D"] for d in current.values())
season_draw_rate = total_draws / total_matches

fixtures = [
    # Round 35
    ("Levante","Osasuna"), ("Elche","Alaves"), ("Sevilla","Espanol"),
    ("Atletico Madrid","Celta Vigo"), ("Real Sociedad","Real Betis"),
    ("RCD Mallorca","Villarreal"), ("Athletic Bilbao","Valencia"),
    ("Real Oviedo","Getafe"), ("Barcelona","Real Madrid"),
    ("Rayo Vallecano","Girona"),
    # Round 36
    ("Celta Vigo","Levante"), ("Real Betis","Elche"), ("Osasuna","Atletico Madrid"),
    ("Espanol","Athletic Bilbao"), ("Villarreal","Sevilla"),
    ("Alaves","Barcelona"), ("Getafe","RCD Mallorca"),
    ("Valencia","Rayo Vallecano"), ("Girona","Real Sociedad"),
    ("Real Madrid","Real Oviedo"),
    # Round 37
    ("Athletic Bilbao","Celta Vigo"), ("Atletico Madrid","Girona"),
    ("Barcelona","Real Betis"), ("Elche","Getafe"),
    ("Levante","RCD Mallorca"), ("Osasuna","Espanol"),
    ("Rayo Vallecano","Villarreal"), ("Real Oviedo","Alaves"),
    ("Real Sociedad","Valencia"), ("Sevilla","Real Madrid"),
    # Round 38
    ("Alaves","Rayo Vallecano"), ("Celta Vigo","Sevilla"),
    ("Espanol","Real Sociedad"), ("Getafe","Osasuna"),
    ("Girona","Elche"), ("Real Betis","Levante"),
    ("Real Madrid","Athletic Bilbao"), ("RCD Mallorca","Real Oviedo"),
    ("Valencia","Barcelona"), ("Villarreal","Atletico Madrid"),
]

# ====================== EUROPA LEAGUE ELOS ======================
el_elos = {
    "Aston Villa": 1887,
    "Freiburg": 1721,
    "Forest": 1829,
    "Sporting Braga": 1719,
}

# ====================== CHAMPIONS LEAGUE ELOS ======================
cl_elos = {
    "Bayern Munich": 2017,
    "Arsenal": 2049,
    "Paris Saint-Germain": 1973,
    "Atletico Madrid": 1844,
}

# ====================== CONFERENCE LEAGUE ELOS ======================
conf_elos = {
    "Strasbourg": 1725,
    "Shakhtar Donetsk": 1587,
    "Rayo Vallecano": 1667,
    "Crystal Palace": 1810,
}



# Print sorted ELO ratings
print("La Liga ELO Rankings:")
sorted_elo = sorted(elo.items(), key=lambda x: x[1], reverse=True)
for rank, (team, rating) in enumerate(sorted_elo, 1):
    print(f"{rank} {team}\t{rating}")
print()



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

def el_simulate_two_leg_tie(team_a, team_b, first_leg_home_is_a, elos_dict, first_leg_scores=None):
    if first_leg_scores is not None:
        if first_leg_home_is_a:
            g_a1, g_b1 = first_leg_scores
        else:
            g_b1, g_a1 = first_leg_scores
    else:
        if first_leg_home_is_a:
            h_l1, a_l1 = el_get_expected_goals(elos_dict[team_a], elos_dict[team_b])
            g_a1 = el_poisson_random(h_l1)
            g_b1 = el_poisson_random(a_l1)
        else:
            h_l1, a_l1 = el_get_expected_goals(elos_dict[team_b], elos_dict[team_a])
            g_b1 = el_poisson_random(h_l1)
            g_a1 = el_poisson_random(a_l1)

    h_l2, a_l2 = el_get_expected_goals(elos_dict[team_b], elos_dict[team_a]) if first_leg_home_is_a else el_get_expected_goals(elos_dict[team_a], elos_dict[team_b])
    g_b2 = el_poisson_random(h_l2)
    g_a2 = el_poisson_random(a_l2)

    total_a = g_a1 + g_a2
    total_b = g_b1 + g_b2

    if total_a == total_b:
        # Extra time: 30 minutes at second leg venue
        extra_home_lambda = h_l2 / 2  # Reduced for extra time
        extra_away_lambda = a_l2 / 2
        extra_home_goals = el_poisson_random(extra_home_lambda)
        extra_away_goals = el_poisson_random(extra_away_lambda)
        # Second leg home is team_b if first_leg_home_is_a else team_a
        if first_leg_home_is_a:
            total_b += extra_home_goals  # team_b extra home
            total_a += extra_away_goals  # team_a extra away
        else:
            total_a += extra_home_goals  # team_a extra home
            total_b += extra_away_goals  # team_b extra away

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

def cl_simulate_two_leg_tie(team_a, team_b, first_leg_home_is_a, elos_dict, first_leg_scores=None):
    if first_leg_scores is not None:
        if first_leg_home_is_a:
            g_a1, g_b1 = first_leg_scores
        else:
            g_b1, g_a1 = first_leg_scores
    else:
        if first_leg_home_is_a:
            h_l1, a_l1 = cl_get_expected_goals(elos_dict[team_a], elos_dict[team_b])
            g_a1 = cl_poisson_random(h_l1)
            g_b1 = cl_poisson_random(a_l1)
        else:
            h_l1, a_l1 = cl_get_expected_goals(elos_dict[team_b], elos_dict[team_a])
            g_b1 = cl_poisson_random(h_l1)
            g_a1 = cl_poisson_random(a_l1)

    h_l2, a_l2 = cl_get_expected_goals(elos_dict[team_b], elos_dict[team_a]) if first_leg_home_is_a else cl_get_expected_goals(elos_dict[team_a], elos_dict[team_b])
    g_b2 = cl_poisson_random(h_l2)
    g_a2 = cl_poisson_random(a_l2)

    total_a = g_a1 + g_a2
    total_b = g_b1 + g_b2

    if total_a == total_b:
        # Extra time: 30 minutes at second leg venue
        extra_home_lambda = h_l2 / 2  # Reduced for extra time
        extra_away_lambda = a_l2 / 2
        extra_home_goals = cl_poisson_random(extra_home_lambda)
        extra_away_goals = cl_poisson_random(extra_away_lambda)
        # Second leg home is team_b if first_leg_home_is_a else team_a
        if first_leg_home_is_a:
            total_b += extra_home_goals  # team_b extra home
            total_a += extra_away_goals  # team_a extra away
        else:
            total_a += extra_home_goals  # team_a extra home
            total_b += extra_away_goals  # team_b extra away

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

def conf_simulate_two_leg_tie(team_a, team_b, first_leg_home_is_a, elos_dict, first_leg_scores=None):
    if first_leg_scores is not None:
        if first_leg_home_is_a:
            g_a1, g_b1 = first_leg_scores
        else:
            g_b1, g_a1 = first_leg_scores
    else:
        if first_leg_home_is_a:
            h_l1, a_l1 = conf_get_expected_goals(elos_dict[team_a], elos_dict[team_b])
            g_a1 = conf_poisson_random(h_l1)
            g_b1 = conf_poisson_random(a_l1)
        else:
            h_l1, a_l1 = conf_get_expected_goals(elos_dict[team_b], elos_dict[team_a])
            g_b1 = conf_poisson_random(h_l1)
            g_a1 = conf_poisson_random(a_l1)

    h_l2, a_l2 = conf_get_expected_goals(elos_dict[team_b], elos_dict[team_a]) if first_leg_home_is_a else conf_get_expected_goals(elos_dict[team_a], elos_dict[team_b])
    g_b2 = conf_poisson_random(h_l2)
    g_a2 = conf_poisson_random(a_l2)

    total_a = g_a1 + g_a2
    total_b = g_b1 + g_b2

    if total_a == total_b:
        # Extra time: 30 minutes at second leg venue
        extra_home_lambda = h_l2 / 2  # Reduced for extra time
        extra_away_lambda = a_l2 / 2
        extra_home_goals = conf_poisson_random(extra_home_lambda)
        extra_away_goals = conf_poisson_random(extra_away_lambda)
        # Second leg home is team_b if first_leg_home_is_a else team_a
        if first_leg_home_is_a:
            total_b += extra_home_goals  # team_b extra home
            total_a += extra_away_goals  # team_a extra away
        else:
            total_a += extra_home_goals  # team_a extra home
            total_b += extra_away_goals  # team_b extra away

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

# ====================== FORM ADJUSTMENTS ======================
# Set to 0 for simplicity
form_adjustment = {
    "Barcelona": 0,
    "Real Madrid": 0,
    "Villarreal": 0,
    "Atletico Madrid": 0,
    "Real Betis": 0,
    "Celta Vigo": 0,
    "Getafe": 0,
    "Athletic Bilbao": 0,
    "Real Sociedad": 0,
    "Osasuna": 0,
    "Rayo Vallecano": 0,
    "Valencia": 0,
    "Espanol": 0,
    "Elche": 0,
    "RCD Mallorca": 0,
    "Girona": 0,
    "Sevilla": 0,
    "Alaves": 0,
    "Levante": 0,
    "Real Oviedo": 0,
}

# ====================== W/D/L RATES ======================
wdl_rates = {
    "Barcelona": {"win": 29/34, "draw": 1/34, "loss": 4/34},
    "Real Madrid": {"win": 24/34, "draw": 5/34, "loss": 5/34},
    "Villarreal": {"win": 21/34, "draw": 5/34, "loss": 8/34},
    "Atletico Madrid": {"win": 19/34, "draw": 6/34, "loss": 9/34},
    "Real Betis": {"win": 13/34, "draw": 14/34, "loss": 7/34},
    "Celta Vigo": {"win": 12/34, "draw": 11/34, "loss": 11/34},
    "Getafe": {"win": 13/34, "draw": 5/34, "loss": 16/34},
    "Athletic Bilbao": {"win": 13/34, "draw": 5/34, "loss": 16/34},
    "Real Sociedad": {"win": 11/34, "draw": 10/34, "loss": 13/34},
    "Osasuna": {"win": 11/34, "draw": 9/34, "loss": 14/34},
    "Rayo Vallecano": {"win": 10/34, "draw": 12/34, "loss": 12/34},
    "Valencia": {"win": 10/34, "draw": 9/34, "loss": 15/34},
    "Espanol": {"win": 10/34, "draw": 9/34, "loss": 15/34},
    "Elche": {"win": 9/34, "draw": 11/34, "loss": 14/34},
    "RCD Mallorca": {"win": 10/34, "draw": 8/34, "loss": 16/34},
    "Girona": {"win": 9/34, "draw": 11/34, "loss": 14/34},
    "Sevilla": {"win": 10/34, "draw": 7/34, "loss": 17/34},
    "Alaves": {"win": 9/34, "draw": 9/34, "loss": 16/34},
    "Levante": {"win": 8/34, "draw": 9/34, "loss": 17/34},
    "Real Oviedo": {"win": 6/34, "draw": 10/34, "loss": 18/34},
}

# ====================== INJURY PENALTIES ======================
# Set to 0 for simplicity
injury_penalty = {
    "Barcelona": 0,
    "Real Madrid": 0,
    "Villarreal": 0,
    "Atletico Madrid": 0,
    "Real Betis": 0,
    "Celta Vigo": 0,
    "Getafe": 0,
    "Athletic Bilbao": 0,
    "Real Sociedad": 0,
    "Osasuna": 0,
    "Rayo Vallecano": 0,
    "Valencia": 0,
    "Espanol": 0,
    "Elche": 0,
    "RCD Mallorca": 0,
    "Girona": 0,
    "Sevilla": 0,
    "Alaves": 0,
    "Levante": 0,
    "Real Oviedo": 0,
}

# ====================== MODEL PARAMETERS ======================
HOME_ADVANTAGE = 80

# ====================== HELPER FUNCTIONS ======================
def update_elo(current_elo_attack, current_elo_defence, home, away, hg, ag):
    home_attack, home_defence = get_adjusted_ratings(home, current_elo_attack, current_elo_defence)
    away_attack, away_defence = get_adjusted_ratings(away, current_elo_attack, current_elo_defence)
    diff_attack = home_attack - away_defence + HOME_ADVANTAGE
    diff_defence = away_attack - home_defence
    rd_avg = (rd[home] + rd[away]) / 2
    g_val = g(rd_avg)
    expected_home_attack = 1 / (1 + 10 ** (-g_val * diff_attack / 400))
    expected_away_attack = 1 - expected_home_attack
    expected_home_defence = 1 / (1 + 10 ** (-g_val * diff_defence / 400))
    expected_away_defence = 1 - expected_home_defence
    goal_diff = abs(hg - ag)
    multiplier = math.log(goal_diff + 1)
    if hg > ag:
        score_home_attack, score_away_attack = 1 * multiplier, 0
        score_home_defence, score_away_defence = 1 * multiplier, 0
    elif hg == ag:
        score_home_attack, score_away_attack = 0.5, 0.5
        score_home_defence, score_away_defence = 0.5, 0.5
    else:
        score_home_attack, score_away_attack = 0, 1 * multiplier
        score_home_defence, score_away_defence = 0, 1 * multiplier
    K_home = 25 / (1 + rd[home]/100)
    K_away = 25 / (1 + rd[away]/100)
    current_elo_attack[home] += K_home * (score_home_attack - expected_home_attack)
    current_elo_attack[away] += K_away * (score_away_attack - expected_away_attack)
    current_elo_defence[home] += K_home * (score_home_defence - expected_home_defence)
    current_elo_defence[away] += K_away * (score_away_defence - expected_away_defence)

def get_adjusted_ratings(team, current_elo_attack, current_elo_defence):
    penalty = injury_penalty.get(team, 0)
    adjusted_penalty = penalty * (1 - math.exp(-penalty / 80))  # nonlinear injury penalty
    # Split injury impact: assume half affects attack, half defence
    attack_penalty = adjusted_penalty / 2
    defence_penalty = adjusted_penalty / 2
    attack = current_elo_attack[team] - attack_penalty + form_adjustment.get(team, 0)
    defence = current_elo_defence[team] - defence_penalty + form_adjustment.get(team, 0)
    return attack, defence

# ====================== MATCH ENGINE ======================
def simulate_match(home, away, current_elo_attack, current_elo_defence):
    home_attack, home_defence = get_adjusted_ratings(home, current_elo_attack, current_elo_defence)
    away_attack, away_defence = get_adjusted_ratings(away, current_elo_attack, current_elo_defence)
    diff_home = home_attack - away_defence + HOME_ADVANTAGE
    diff_away = away_attack - home_defence
    diff = diff_home - diff_away

    # Base probabilities for outcomes, using this season's combined draw rate
    base_home_win = 1 - season_draw_rate + 0.1
    base_draw = season_draw_rate
    base_away_win = 1 - season_draw_rate - 0.1 

    # Scale for adjustments
    scale = 400

    # Closeness factor (higher for even matches)
    closeness = math.exp(-(diff**2)/(2 * 180**2))

    # Adjust probabilities based on strength difference
    shift = diff / scale
    p_home_win = base_home_win + shift * 0.2
    p_away_win = base_away_win - shift * 0.2
    p_draw = base_draw + closeness * 0.1

    # Normalize probabilities
    total = p_home_win + p_draw + p_away_win
    p_home_win /= total
    p_draw /= total
    p_away_win /= total

    # Sample match outcome
    r = np.random.random()
    if r < p_home_win:
        # Home win
        hg = np.random.poisson(1.8)
        ag = np.random.poisson(0.9)
    elif r < p_home_win + p_draw:
        # Draw
        mean_goals = 1.35
        hg = np.random.poisson(mean_goals)
        ag = hg
    else:
        # Away win
        hg = np.random.poisson(0.9)
        ag = np.random.poisson(1.8)

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

# ====================== EXCITEMENT SCORE FUNCTION ======================
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
    
    # Title race: teams within 3 points of 1st
    if ranking:
        leader_pts = ranking[0][1]["Pts"]
        title_contenders = sum(1 for _, data in ranking[1:] if data["Pts"] >= leader_pts - 3)
    else:
        title_contenders = 0
    
    # Top 4: teams within 5 points of 4th
    if len(ranking) > 3:
        fourth_pts = ranking[3][1]["Pts"]
        top4_contenders = sum(1 for _, data in ranking[4:] if data["Pts"] >= fourth_pts - 5)
    else:
        top4_contenders = 0
    
    # Relegation: teams within 3 points of 18th
    if len(ranking) > 17:
        releg_pts = ranking[17][1]["Pts"]
        releg_contenders = sum(1 for _, data in ranking[:17] if data["Pts"] <= releg_pts + 3)
    else:
        releg_contenders = 0
    
    # Score out of 10 (weighted and scaled)
    raw_score = (title_contenders * 2 + top4_contenders + releg_contenders * 1.5) / 5
    return min(10, raw_score)

# ====================== MONTE CARLO ======================
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
avg_points = defaultdict(list)
points_distribution = defaultdict(list)
excitement_scores = []
max_win_points = 0
min_win_points = float('inf')

# ====================== EUROPA LEAGUE SIMULATION ======================
NUM_SIMS_EL = 10000
el_champion_counts = Counter()

for sim in range(NUM_SIMS_EL):
    # Semi-finals
    # SF1: Forest vs Aston Villa - Forest home first
    sf1 = el_simulate_two_leg_tie("Forest", "Aston Villa", True, el_elos, first_leg_scores=(1,0))
    
    # SF2: Sporting Braga vs Freiburg - Sporting Braga home first
    sf2 = el_simulate_two_leg_tie("Sporting Braga", "Freiburg", True, el_elos, first_leg_scores=(2,1))
    
    champion = el_simulate_final(sf1, sf2, el_elos)
    el_champion_counts[champion] += 1

el_win_probs = {team: count / NUM_SIMS_EL for team, count in el_champion_counts.items()}

# ====================== CHAMPIONS LEAGUE SIMULATION ======================
NUM_SIMS_CL = 10000
cl_champion_counts = Counter()

# Quarter-finals completed: Semi-finalists are PSG, Bayern, Atletico, Arsenal
for sim in range(NUM_SIMS_CL):
    sf1 = cl_simulate_two_leg_tie("Paris Saint-Germain", "Bayern Munich", True, cl_elos, first_leg_scores=(5,4))
    sf2 = "Arsenal"
    champion = cl_simulate_final(sf1, sf2, cl_elos)
    cl_champion_counts[champion] += 1

cl_win_probs = {team: count / NUM_SIMS_CL for team, count in cl_champion_counts.items()}


# ====================== CONFERENCE LEAGUE SIMULATION ======================
NUM_SIMS_CONF = 10000
conf_champion_counts = Counter()

for sim in range(NUM_SIMS_CONF):
    # Semi-finals
    # SF1: shakhtar donetsk vs Crystal Palace - shakhtar donetsk home first
    sf1 = conf_simulate_two_leg_tie("Shakhtar Donetsk", "Crystal Palace", True, conf_elos, first_leg_scores=(1,3))
    # SF2: strasbourg vs rayo vallecano - Strasbourg home first
    sf2 = conf_simulate_two_leg_tie("Rayo Vallecano", "Strasbourg", True, conf_elos, first_leg_scores=(1,0))

    champion = conf_simulate_final(sf1, sf2, conf_elos)
    conf_champion_counts[champion] += 1

conf_win_probs = {team: count / NUM_SIMS_CONF for team, count in conf_champion_counts.items()}

# FA Cup simulation using ELO

print(f"Running {sims:,} simulations...")

completed_sims = 0
try:
    for _ in tqdm(range(sims), desc="Simulating", unit="sim"):

        current_elo_attack = elo_attack.copy()
        current_elo_defence = elo_defence.copy()

        table = {
            t: {"Pts": current[t]["Pts"], "GF": current[t]["GF"], "GA": current[t]["GA"]}
            for t in current
        }

        draw_count = 0
        for home, away in fixtures:
            hg, ag = simulate_match(home, away, current_elo_attack, current_elo_defence)
            if hg == ag:
                draw_count += 1
            apply_result(table, home, away, hg, ag)
            update_elo(current_elo_attack, current_elo_defence, home, away, hg, ag)

        if draw_count == len(fixtures):
            all_draws += 1

        # Calculate excitement score for this simulation
        score = calculate_excitement_score(table)
        excitement_scores.append(score)

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



        def assign_europe(current_table, ranking, el_winner, fa_winner, conf_winner):
            european_assignments = {}

            # League spots: top 5 CL, 6th EL, 7th Conf
            for i in range(5):
                european_assignments[ranking[i][0]] = "CL"

            if len(ranking) > 5:
                european_assignments[ranking[5][0]] = "EL"

            if len(ranking) > 6:
                european_assignments[ranking[6][0]] = "Conf"

            # Copa del Rey winner (Real Sociedad) to EL if not in CL
            if "Real Sociedad" in current_table and "Real Sociedad" not in european_assignments:
                european_assignments["Real Sociedad"] = "EL"

            # Conference League winner to EL if not in CL
            if conf_winner in current_table and conf_winner not in european_assignments:
                european_assignments[conf_winner] = "EL"

            # Europa League winner to CL if not already in CL
            if el_winner in current_table and el_winner not in european_assignments:
                european_assignments[el_winner] = "CL"

            return european_assignments

        european_assignments = assign_europe(current, ranking, el_winner, None, conf_winner)

        european_teams = set(european_assignments.keys())
        if len(european_teams) >= 9:
            eight_european += 1

        for team, comp in european_assignments.items():
            if comp == 'CL':
                cl[team] += 1
            elif comp == 'EL':
                el[team] += 1
            else:
                conf[team] += 1
            european[team] += 1

        releg_40_this_sim = False
        for pos, (team, data) in enumerate(ranking, 1):
            avg_points[team].append(data["Pts"])
            points_distribution[team].append(data["Pts"])

            if pos == 1:
                title[team] += 1
                win_points = data["Pts"]
                max_win_points = max(max_win_points, win_points)
                min_win_points = min(min_win_points, win_points)
            if pos >= 18:
                releg[team] += 1
                if data["Pts"] >= 40:
                    releg_40_plus[team] += 1
                    releg_40_this_sim = True
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
    sims = completed_sims  # Adjust for stats calculation

# ====================== STATISTICS ======================
team_stats = {}
releg_40_prob = {}
for team in current.keys():
    pts = points_distribution[team]
    avg = np.mean(pts)
    std = np.std(pts)
    p25, med, p75 = np.percentile(pts, [25, 50, 75])
    team_stats[team] = {'avg': avg, 'std': std, 'p25': p25, 'med': med, 'p75': p75}

    if points_40_plus[team] > 0:
        releg_40_prob[team] = (releg_40_plus[team] / points_40_plus[team]) * 100
    else:
        releg_40_prob[team] = 0.0

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
        hg, ag = simulate_match(home, away, elo_attack, elo_defence)
        if hg > ag:
            home_wins += 1
        elif hg == ag:
            draws += 1
        else:
            away_wins += 1
    return home_wins / n_sims * 100, draws / n_sims * 100, away_wins / n_sims * 100

# ====================== OUTPUT ======================
print(f"{'Team':<20}{'AvgPts':<8}{'StdDev':<8}{'Title%':<8}{'CL%':<8}{'EL%':<8}{'Conf%':<8}{'European%':<10}{'Releg%':<8}")
print("-" * 106)

rank = 1
table_rows = []
for team in sorted(current.keys(), key=lambda x: sum(avg_points[x]) / sims, reverse=True):
    row_data = (
        team,
        f"{sum(avg_points[team])/sims:.2f}",
        f"{team_stats[team]['std']:.2f}",
        f"{title[team]/sims*100:.2f}",
        f"{cl[team]/sims*100:.2f}",
        f"{el[team]/sims*100:.2f}",
        f"{conf[team]/sims*100:.2f}",
        f"{european[team]/sims*100:.2f}",
        f"{releg[team]/sims*100:.2f}"
    )
    print(f"{row_data[0]:<20}{row_data[1]:<8}{row_data[2]:<8}{row_data[3]:<8}{row_data[4]:<8}{row_data[5]:<8}{row_data[6]:<8}{row_data[7]:<10}{row_data[8]:<8}")
    table_rows.append(row_data)
    rank += 1

# Generate HTML
def generate_html():
    html = """<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>La Liga Simulation Results</title>
    <style>
        body { font-family: Arial, sans-serif; margin: 20px; }
        h1 { color: #333; }
        table { border-collapse: collapse; width: 100%; }
        th, td { border: 1px solid #ddd; padding: 8px; text-align: left; }
        th { background-color: #f2f2f2; }
        tr:nth-child(even) { background-color: #f9f9f9; }
        td { font-size: 14px; }
    </style>
</head>
<body>
    <h1>La Liga Simulation Results</h1>
    <p>Simulations run: """ + str(sims) + """,</p>
    <table>
        <thead>
            <tr>
                <th>Team</th>
                <th>AvgPts</th>
                <th>StdDev</th>
                <th>Title%</th>
                <th>CL%</th>
                <th>EL%</th>
                <th>Conf%</th>
                <th>European%</th>
                <th>Releg%</th>
            </tr>
        </thead>
        <tbody>"""
    for row in table_rows:
        html += "            <tr>\n"
        for col in row:
            html += "                <td>" + str(col) + "</td>\n"
        html += "            </tr>\n"
    
    html += """
        </tbody>
    </table>
    <p>Last updated: """ + str(__import__('datetime').datetime.now()) + """</p>
</body>
</html>"""
    with open("C:/Users/liam/Documents/GitHub/all-of-my-code/sportsanalysis/european_leagues/htmls/laliga_simulation_results.html", "w") as f:
        f.write(html)
    print("HTML file generated: htmls/laliga_simulation_results.html")

generate_html()

uefa_win_percent = uefa_pl_win_sims / sims * 100



print(f"Probability of at least one Spanish team wins one UEFA competition: {uefa_win_percent:.2f}%")



print(f"Max points to win the league: {max_win_points}")
print(f"Min points to win the league: {min_win_points}")

print("\n========================================")
print("UEFA COMPETITION WIN PROBABILITIES")
print("========================================")

print("Champions League Win Probabilities:")
for team, prob in sorted(cl_win_probs.items(), key=lambda x: x[1], reverse=True):
    print(f"{team}: {prob*100:.2f}%")

print("Europa League Win Probabilities:")
for team, prob in sorted(el_win_probs.items(), key=lambda x: x[1], reverse=True):
    print(f"{team}: {prob*100:.2f}%")

print("Conference League Win Probabilities:")
for team, prob in sorted(conf_win_probs.items(), key=lambda x: x[1], reverse=True):
    print(f"{team}: {prob*100:.2f}%")
    
print("\n========================================")


at_least_one_releg_40_percent = at_least_one_releg_40 / sims * 100
print(f"Probability that at least one team is relegated with 40+ points: {at_least_one_releg_40_percent:.4f}%")

eight_european_percent = eight_european / sims * 100
print(f"Probability that at least 9 teams qualify for European competitions: {eight_european_percent:.4f}%")

# Average excitement score for the final day
avg_excitement = sum(excitement_scores) / sims
print(f"Average excitement score for the final day (out of 10): {avg_excitement:.2f}")

all_draws_percent = all_draws / sims * 100
print(f"Probability that all remaining games are draws: {all_draws_percent:.4f}%")

# Historical note: In Premier League history (1992-2024), no team has been relegated with 40 or more points.
# The highest points for relegation is 38 (West Ham 2009-10, Sunderland 2005-06, etc.).

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