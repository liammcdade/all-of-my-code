import random
import math
import numpy as np
from collections import defaultdict, Counter
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
    "Man Utd":       {"Pts":55,"GF":56,"GA":43},
    "Aston Villa":   {"Pts":54,"GF":42,"GA":37},
    "Liverpool":     {"Pts":49,"GF":50,"GA":42},
    "Chelsea":       {"Pts":48,"GF":53,"GA":38},
    "Brentford":     {"Pts":46,"GF":46,"GA":42},
    "Everton":       {"Pts":46,"GF":37,"GA":35},
    "Fulham":        {"Pts":44,"GF":43,"GA":44},
    "Brighton":      {"Pts":43,"GF":41,"GA":37},
    "Sunderland":    {"Pts":43,"GF":32,"GA":36},
    "Newcastle":     {"Pts":42,"GF":44,"GA":45},
    "Bournemouth":   {"Pts":42,"GF":44,"GA":45},
    "Crystal Palace":{"Pts":39,"GF":33,"GA":35},
    "Leeds":         {"Pts":33,"GF":37,"GA":48},
    "Nott'm Forest": {"Pts":32,"GF":31,"GA":43},
    "Tottenham":     {"Pts":30,"GF":40,"GA":50},
    "West Ham":      {"Pts":29,"GF":36,"GA":57},
    "Burnley":       {"Pts":20,"GF":33,"GA":61},
    "Wolves":        {"Pts":17,"GF":24,"GA":54},
}

# ====================== EUROPA LEAGUE ELOS ======================
el_elos = {
    "Aston Villa": 1886,
    "Bologna": 1704,
    "Braga": 1709,
    "Celta": 1748,
    "Freiburg": 1694,
    "Nott'm Forest": 1785,
    "Porto": 1809,
    "Real Betis": 1750,
}

# ====================== CHAMPIONS LEAGUE ELOS ======================
cl_elos = {
    "Real Madrid": 2100,
    "Bayern Munich": 2050,
    "Arsenal": 2000,
    "Barcelona": 1990,
    "Paris Saint-Germain": 1970,
    "Liverpool": 1960,
    "Atletico Madrid": 1950,
    "Sporting CP": 1940,
}

# ====================== CONFERENCE LEAGUE ELOS ======================
conf_elos = {
    "Crystal Palace": 1795,
    "Strasbourg": 1715,
    "Mainz 05": 1696,
    "Rayo Vallecano": 1672,
    "Fiorentina": 1670,
    "AEK Athens": 1639,
    "Shakhtar Donetsk": 1566,
    "AZ Alkmaar": 1559,
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
    "Nott'm Forest": 1785,
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
DRAW_BASE = 0.269
DRAW_WIDTH = 240

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
cl = defaultdict(int)
el = defaultdict(int)
conf = defaultdict(int)
european = defaultdict(int)
releg = defaultdict(int)
avg_points = defaultdict(list)

# ====================== EUROPA LEAGUE SIMULATION ======================
NUM_SIMS_EL = 10000
el_champion_counts = Counter()

el_qf_first_leg = {
    ("Real Betis", "Braga"): (1, 1),  # Real Betis home 1, Braga away 1
    ("Bologna", "Aston Villa"): (1, 3),  # Bologna home 1, Aston Villa away 3
    ("Freiburg", "Celta"): (3, 0),  # Freiburg home 3, Celta away 0
    ("Porto", "Nott'm Forest"): (1, 1),  # Porto home 1, Nott'm Forest away 1
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
    # Use real first leg for Porto vs Nott'm Forest
    porto_h, forest_a = el_qf_first_leg[("Porto", "Nott'm Forest")]
    h_l2, a_l2 = el_get_expected_goals(el_elos["Nott'm Forest"], el_elos["Porto"])
    g_forest = el_poisson_random(h_l2) + forest_a
    g_porto = el_poisson_random(a_l2) + porto_h
    if g_forest > g_porto:
        qf_winners["qf2"] = "Nott'm Forest"
    elif g_porto > g_forest:
        qf_winners["qf2"] = "Porto"
    else:
        qf_winners["qf2"] = el_simulate_penalties("Nott'm Forest", "Porto", el_elos)
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
    
    h_l2, a_l2 = cl_get_expected_goals(cl_elos["Liverpool"], cl_elos["Paris Saint-Germain"])
    g_liv = cl_poisson_random(h_l2) + psg_a
    g_psg = cl_poisson_random(a_l2) + psg_h
    qf_winners["qf1"] = "Liverpool" if g_liv > g_psg else "Paris Saint-Germain"
    
    h_l2, a_l2 = cl_get_expected_goals(cl_elos["Bayern Munich"], cl_elos["Real Madrid"])
    g_bay = cl_poisson_random(h_l2) + real_a
    g_real = cl_poisson_random(a_l2) + real_h
    qf_winners["qf2"] = "Bayern Munich" if g_bay > g_real else "Real Madrid"
    
    h_l2, a_l2 = cl_get_expected_goals(cl_elos["Atletico Madrid"], cl_elos["Barcelona"])
    g_atl = cl_poisson_random(h_l2) + barca_a
    g_barca = cl_poisson_random(a_l2) + barca_h
    qf_winners["qf3"] = "Atletico Madrid" if g_atl > g_barca else "Barcelona"
    
    h_l2, a_l2 = cl_get_expected_goals(cl_elos["Arsenal"], cl_elos["Sporting CP"])
    g_ars = cl_poisson_random(h_l2) + sporting_a
    g_sport = cl_poisson_random(a_l2) + sporting_h
    qf_winners["qf4"] = "Arsenal" if g_ars > g_sport else "Sporting CP"
    
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
    fa_winner = simulate_full_fa_cup_tournament()
    league_cup_winner = "Man City"

    cl_teams = [ranking[i][0] for i in range(5)]
    el_teams = [ranking[5][0], ranking[6][0]]

    if fa_winner in current and fa_winner not in cl_teams and fa_winner not in el_teams:
        el_teams.append(fa_winner)

    if conf_winner in current and conf_winner not in cl_teams and conf_winner not in el_teams:
        el_teams.append(conf_winner)

    conf_team = ranking[7 + (len(el_teams) - 2)][0]
    if league_cup_winner in current and league_cup_winner not in cl_teams and league_cup_winner not in el_teams:
        conf_team = league_cup_winner

    for pos, (team, data) in enumerate(ranking, 1):
        avg_points[team].append(data["Pts"])

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

# ====================== OUTPUT ======================
print(f"{'Team':<15}{'AvgPts':<8}{'Title%':<8}{'CL%':<8}{'EL%':<8}{'Conf%':<8}{'European%':<10}{'Releg%'}")
print("-" * 90)

rank = 1
for team in sorted(current.keys(), key=lambda x: sum(avg_points[x]) / sims, reverse=True):
    print(
        f"{team:<15}"
        f"{sum(avg_points[team])/sims:<8.2f}"
        f"{title[team]/sims*100:<8.2f}"
        f"{cl[team]/sims*100:<8.2f}"
        f"{el[team]/sims*100:<8.2f}"
        f"{conf[team]/sims*100:<8.2f}"
        f"{european[team]/sims*100:<10.2f}"
        f"{releg[team]/sims*100:.2f}"
    )
    rank += 1