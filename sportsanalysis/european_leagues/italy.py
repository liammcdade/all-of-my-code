import random
import math
import numpy as np
from collections import defaultdict, Counter
from tqdm import tqdm

# ====================== ELO RATINGS ======================
elo = {
    "Inter Milan": 1920,
    "Napoli": 1850,
    "AC Milan": 1830,
    "Juventus": 1820,
    "Roma": 1800,
    "Como": 1780,
    "Atalanta": 1770,
    "Lazio": 1750,
    "Bologna": 1720,
    "Sassuolo": 1710,
    "Udinese": 1700,
    "Parma": 1680,
    "Torino": 1670,
    "Genoa": 1660,
    "Cagliari": 1650,
    "Fiorentina": 1640,
    "Lecce": 1620,
    "Cremonese": 1600,
    "Verona": 1550,
    "Pisa": 1530,
    "Bayern Munich": 2017,
    "Arsenal": 2049,
    "Paris Saint-Germain": 1973,
    "Atletico Madrid": 1844,
    "Aston Villa": 1875,
    "Freiburg": 1721,
    "Forest": 1829,
    "Sporting Braga": 1719,
    "Strasbourg": 1725,
    "Shakhtar Donetsk": 1587,
    "Rayo Vallecano": 1667,
    "Crystal Palace": 1799
}

elo_attack = elo.copy()
elo_defence = elo.copy()

# ====================== CURRENT TABLE ======================
current = {
    "Inter Milan": {"MP":35,"W":26,"D":4,"L":5,"GF":82,"GA":31,"Pts":82},
    "Napoli": {"MP":35,"W":21,"D":7,"L":7,"GF":52,"GA":33,"Pts":70},
    "AC Milan": {"MP":35,"W":19,"D":10,"L":6,"GF":48,"GA":29,"Pts":67},
    "Juventus": {"MP":35,"W":18,"D":11,"L":6,"GF":58,"GA":30,"Pts":65},
    "Roma": {"MP":35,"W":20,"D":4,"L":11,"GF":52,"GA":29,"Pts":64},
    "Como": {"MP":35,"W":17,"D":11,"L":7,"GF":59,"GA":28,"Pts":62},
    "Atalanta": {"MP":35,"W":14,"D":13,"L":8,"GF":47,"GA":32,"Pts":55},
    "Lazio": {"MP":35,"W":13,"D":12,"L":10,"GF":39,"GA":34,"Pts":51},
    "Bologna": {"MP":35,"W":14,"D":7,"L":14,"GF":42,"GA":41,"Pts":49},
    "Sassuolo": {"MP":35,"W":14,"D":7,"L":14,"GF":43,"GA":44,"Pts":49},
    "Udinese": {"MP":35,"W":13,"D":8,"L":14,"GF":43,"GA":46,"Pts":47},
    "Parma": {"MP":35,"W":10,"D":12,"L":13,"GF":25,"GA":42,"Pts":42},
    "Torino": {"MP":35,"W":11,"D":8,"L":16,"GF":39,"GA":58,"Pts":41},
    "Genoa": {"MP":35,"W":10,"D":10,"L":15,"GF":40,"GA":48,"Pts":40},
    "Cagliari": {"MP":35,"W":9,"D":10,"L":16,"GF":36,"GA":49,"Pts":37},
    "Fiorentina": {"MP":35,"W":8,"D":13,"L":14,"GF":38,"GA":49,"Pts":37},
    "Lecce": {"MP":35,"W":8,"D":8,"L":19,"GF":24,"GA":47,"Pts":32},
    "Cremonese": {"MP":35,"W":6,"D":10,"L":19,"GF":27,"GA":53,"Pts":28},
    "Verona": {"MP":35,"W":3,"D":11,"L":21,"GF":24,"GA":57,"Pts":20},
    "Pisa": {"MP":35,"W":2,"D":12,"L":21,"GF":25,"GA":63,"Pts":18},
}

# ====================== FIXTURES ======================
fixtures = [
    # Round 36
    ("Torino","Sassuolo"),
    ("Cagliari","Udinese"),
    ("Lazio","Inter Milan"),
    ("Lecce","Juventus"),
    ("Verona","Como"),
    ("Cremonese","Pisa"),
    ("Fiorentina","Genoa"),
    ("Parma","Roma"),
    ("AC Milan","Atalanta"),
    ("Napoli","Bologna"),

    # Round 37
    ("Atalanta","Bologna"),
    ("Cagliari","Torino"),
    ("Como","Parma"),
    ("Genoa","AC Milan"),
    ("Inter Milan","Verona"),
    ("Juventus","Fiorentina"),
    ("Pisa","Napoli"),
    ("Roma","Lazio"),
    ("Sassuolo","Lecce"),
    ("Udinese","Cremonese"),

    # Round 38
    ("AC Milan","Cagliari"),
    ("Bologna","Inter Milan"),
    ("Cremonese","Como"),
    ("Fiorentina","Atalanta"),
    ("Lazio","Pisa"),
    ("Lecce","Genoa"),
    ("Napoli","Udinese"),
    ("Parma","Sassuolo"),
    ("Torino","Juventus"),
    ("Verona","Roma"),
]

# ====================== MODEL PARAMETERS ======================
HOME_ADVANTAGE = 80

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

# Calculate observed draw rate from current table
total_draws = sum(current[t]["D"] for t in current) // 2
total_matches = sum(current[t]["MP"] for t in current) // 2
draw_rate = total_draws / total_matches

# ====================== MATCH ENGINE ======================
def simulate_match(home, away, home_adv=HOME_ADVANTAGE):
    diff = elo[home] - elo[away] + home_adv

    base_home = 0.44
    base_draw = draw_rate
    base_away = 0.29

    shift = diff / 400

    p_home = base_home + shift * 0.2
    p_away = base_away - shift * 0.2
    p_draw = base_draw

    total = p_home + p_draw + p_away
    p_home /= total
    p_draw /= total
    p_away /= total

    r = np.random.random()

    if r < p_home:
        hg = np.random.poisson(1.8)
        ag = np.random.poisson(0.9)
    elif r < p_home + p_draw:
        hg = ag = np.random.poisson(1.3)
    else:
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

# Quarter-finals completed: Semi-finalists are Inter, Atalanta, Bologna, Roma
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

# ====================== MONTE CARLO ======================
sims = 20000
title = defaultdict(int)
releg = defaultdict(int)
champions_league = defaultdict(int)
europa_league = defaultdict(int)
conference_league = defaultdict(int)
total_euro = defaultdict(int)
avg_points = defaultdict(list)

for _ in tqdm(range(sims)):
    table = {
        t: {"W": current[t]["W"], "D": current[t]["D"], "L": current[t]["L"], "GF": current[t]["GF"], "GA": current[t]["GA"], "Pts": current[t]["Pts"]}
        for t in current
    }

    for home, away in fixtures:
        hg, ag = simulate_match(home, away)
        apply_result(table, home, away, hg, ag)

    ranking = sorted(
        table.items(),
        key=lambda x: (x[1]["Pts"], x[1]["GF"] - x[1]["GA"]),
        reverse=True
    )

    # Simulate Coppa Italia final (neutral venue, no home advantage)
    coppa_hg, coppa_ag = simulate_match("Inter Milan", "Lazio", home_adv=0)
    if coppa_hg > coppa_ag:
        coppa_winner = "Inter Milan"
    elif coppa_ag > coppa_hg:
        coppa_winner = "Lazio"
    else:
        # In case of draw, random winner (simplifying extra time/penalties)
        coppa_winner = random.choice(["Inter Milan", "Lazio"])

    coppa_pos = None
    for pos, (team, data) in enumerate(ranking, 1):
        if team == coppa_winner:
            coppa_pos = pos

    for pos, (team, data) in enumerate(ranking, 1):
        avg_points[team].append(data["Pts"])

        if pos == 1:
            title[team] += 1
        if pos <= 4:
            champions_league[team] += 1
        if pos >= 18:
            releg[team] += 1

    # Europa League
    if coppa_pos > 5:
        europa_league[coppa_winner] += 1
    else:
        europa_league[ranking[5][0]] += 1  # 6th place

    # Conference League
    if coppa_pos > 6:
        conference_league[ranking[5][0]] += 1  # 6th place
    else:
        conference_league[ranking[6][0]] += 1  # 7th place

for team in current:
    total_euro[team] = champions_league[team] + europa_league[team] + conference_league[team]

# ====================== OUTPUT ======================
print(f"{'Team':<15}{'AvgPts':<10}{'Title%':<10}{'CL%':<8}{'EL%':<8}{'ConfL%':<8}{'Euro%':<8}{'Releg%':<10}")
print("-"*78)

for team in sorted(current.keys(), key=lambda x: np.mean(avg_points[x]), reverse=True):
    print(f"{team:<15}{np.mean(avg_points[team]):<10.2f}{title[team]/sims*100:<10.2f}{champions_league[team]/sims*100:<8.2f}{europa_league[team]/sims*100:<8.2f}{conference_league[team]/sims*100:<8.2f}{total_euro[team]/sims*100:<8.2f}{releg[team]/sims*100:<10.2f}")

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