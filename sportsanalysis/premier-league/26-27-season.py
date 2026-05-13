import random
import math
import numpy as np
from collections import defaultdict, Counter
from tqdm import tqdm
import numba

# ====================== CONSTANTS ======================
HOME_ADVANTAGE = 33.8
K_FACTOR = 25
BASE_XG = 0.7
MAX_XG = 1.8
ELO_SCALE = 400
XG_SCALE = 300
CLOSENESS_SCALE = 180
INJURY_SCALE = 80
TEMPO_BASE = 0.9
TEMPO_RANGE = 0.1
VARIANCE_BOOST_FACTOR = 0.2
BIAS_ADJUSTMENT = 0.15
SHARED_GOAL_BASE = 0.05
SHARED_GOAL_CLOSENESS = 0.25
MIN_LAMBDA = 0.05
CLOSENESS_BOOST_FACTOR = 0.5
FORM_MULTIPLIER = 5

# ====================== MATCH PARAMETER CACHE ======================
match_param_cache = {}

@numba.jit(nopython=True)
def calculate_match_params(adjusted_home, adjusted_away, home_advantage, base_xg, max_xg, xg_scale, closeness_scale):
    diff = adjusted_home - adjusted_away + home_advantage
    home_xg = base_xg + max_xg / (1 + math.exp(-diff / xg_scale))
    away_xg = base_xg + max_xg / (1 + math.exp(diff / xg_scale))
    closeness = math.exp(-(diff**2)/(2 * closeness_scale**2))
    return home_xg, away_xg, closeness, diff

def get_match_params(home, away, adjusted_home, adjusted_away):
    key = (home, away,
            round(adjusted_home),
            round(adjusted_away))

    if key in match_param_cache:
        return match_param_cache[key]

    home_xg, away_xg, closeness, diff = calculate_match_params(
        adjusted_home, adjusted_away, HOME_ADVANTAGE, BASE_XG, MAX_XG, XG_SCALE, CLOSENESS_SCALE
    )

    match_param_cache[key] = (home_xg, away_xg, closeness, diff)

    return match_param_cache[key]

# ====================== ELO RATINGS ======================
elo = {
    "Arsenal": 1895,
    "Man City": 1885,
    "Liverpool": 1845,
    "Aston Villa": 1755,
    "Man United": 1725,
    "Chelsea": 1795,
    "Brighton": 1705,
    "Brentford": 1645,
    "Everton": 1605,
    "Bournemouth": 1665,
    "Coventry": 1495,
    "Fulham": 1620,
    "Ipswich": 1515,
    "Sunderland": 1490,
    "Crystal Palace": 1640,
    "Leeds": 1540,
    "Newcastle": 1785,
    "Nottingham": 1680,
}

# ====================== CURRENT TABLE ======================
current = {
    "Arsenal":               {"MP":0,"Pts":0,"GF":0,"GA":0},
    "Man City":              {"MP":0,"Pts":0,"GF":0,"GA":0},
    "Man United":            {"MP":0,"Pts":0,"GF":0,"GA":0},
    "Aston Villa":           {"MP":0,"Pts":0,"GF":0,"GA":0},
    "Liverpool":             {"MP":0,"Pts":0,"GF":0,"GA":0},
    "Chelsea":               {"MP":0,"Pts":0,"GF":0,"GA":0},
    "Brentford":             {"MP":0,"Pts":0,"GF":0,"GA":0},
    "Bournemouth":           {"MP":0,"Pts":0,"GF":0,"GA":0},
    "Brighton":              {"MP":0,"Pts":0,"GF":0,"GA":0},
    "Everton":               {"MP":0,"Pts":0,"GF":0,"GA":0},
    "Coventry":              {"MP":0,"Pts":0,"GF":0,"GA":0},
    "Fulham":                {"MP":0,"Pts":0,"GF":0,"GA":0},
    "Ipswich":               {"MP":0,"Pts":0,"GF":0,"GA":0},
    "Sunderland":            {"MP":0,"Pts":0,"GF":0,"GA":0},
    "Crystal Palace":        {"MP":0,"Pts":0,"GF":0,"GA":0},
    "Leeds":                 {"MP":0,"Pts":0,"GF":0,"GA":0},
    "Newcastle":             {"MP":0,"Pts":0,"GF":0,"GA":0},
    "Nottingham":            {"MP":0,"Pts":0,"GF":0,"GA":0},
}

# ====================== FIXTURE GENERATION ======================
def generate_round_robin_fixtures(teams):
    """
    Generate a round-robin fixture list where each team plays every other team
    once at home and once away. Returns list of (home, away) tuples.
    """
    if len(teams) % 2 != 0:
        teams = teams + ["BYE"]  # Add bye if odd number of teams

    fixtures = []
    n = len(teams)

    # Generate each round
    for round_num in range(n - 1):
        round_fixtures = []

        # Pair teams for this round
        for i in range(n // 2):
            home = teams[i]
            away = teams[n - 1 - i]

            # Skip bye matches
            if home != "BYE" and away != "BYE":
                round_fixtures.append((home, away))

        fixtures.extend(round_fixtures)

        # Rotate teams for next round (keep first team fixed)
        teams = [teams[0]] + [teams[-1]] + teams[1:-1]

    # Extend to double round-robin by adding reverse fixtures
    reverse_fixtures = [(away, home) for home, away in fixtures]
    fixtures.extend(reverse_fixtures)

    return fixtures

# Generate fixtures for all remaining matches
teams = list(current.keys())
fixtures = generate_round_robin_fixtures(teams)


# ====================== FIXTURES ======================

# ====================== FORM ADJUSTMENTS ======================
# Based on current W-L differential per game played * 50
form_adjustment = {
    "Arsenal": 0,
    "Man City": 0,
    "Man United": 0,
    "Aston Villa": 0,
    "Liverpool": 0,
    "Chelsea": 0,
    "Brentford": 0,
    "Bournemouth": 0,
    "Brighton": 0,
    "Everton": 0,
    "Coventry": 0,
    "Fulham": 0,
    "Ipswich": 0,
    "Sunderland": 0,
    "Crystal Palace": 0,
    "Leeds": 0,
    "Newcastle": 0,
    "Nottingham": 0,
}

# ====================== W/D/L RATES ======================
wdl_rates = {
    "Arsenal": {"win": 1/3, "draw": 1/3, "loss": 1/3},
    "Man City": {"win": 1/3, "draw": 1/3, "loss": 1/3},
    "Man United": {"win": 1/3, "draw": 1/3, "loss": 1/3},
    "Aston Villa": {"win": 1/3, "draw": 1/3, "loss": 1/3},
    "Liverpool": {"win": 1/3, "draw": 1/3, "loss": 1/3},
    "Chelsea": {"win": 1/3, "draw": 1/3, "loss": 1/3},
    "Brentford": {"win": 1/3, "draw": 1/3, "loss": 1/3},
    "Bournemouth": {"win": 1/3, "draw": 1/3, "loss": 1/3},
    "Brighton": {"win": 1/3, "draw": 1/3, "loss": 1/3},
    "Everton": {"win": 1/3, "draw": 1/3, "loss": 1/3},
    "Coventry": {"win": 1/3, "draw": 1/3, "loss": 1/3},
    "Fulham": {"win": 1/3, "draw": 1/3, "loss": 1/3},
    "Ipswich": {"win": 1/3, "draw": 1/3, "loss": 1/3},
    "Sunderland": {"win": 1/3, "draw": 1/3, "loss": 1/3},
    "Crystal Palace": {"win": 1/3, "draw": 1/3, "loss": 1/3},
    "Leeds": {"win": 1/3, "draw": 1/3, "loss": 1/3},
    "Newcastle": {"win": 1/3, "draw": 1/3, "loss": 1/3},
    "Nottingham": {"win": 1/3, "draw": 1/3, "loss": 1/3},
}



# ====================== INJURY PENALTIES ======================
# ELO reduction: TRACK number * 10 points (e.g., TRACK 3 = 30 points penalty)
injury_penalty = {
    "Arsenal": 0,
    "Man City": 0,
    "Man United": 0,
    "Aston Villa": 0,
    "Liverpool": 0,
    "Chelsea": 0,
    "Brentford": 0,
    "Bournemouth": 0,
    "Brighton": 0,
    "Everton": 0,
    "Coventry": 0,
    "Fulham": 0,
    "Ipswich": 0,
    "Sunderland": 0,
    "Crystal Palace": 0,
    "Leeds": 0,
    "Newcastle": 0,
    "Nottingham": 0,
}

# ====================== MODEL PARAMETERS ======================
HOME_ADVANTAGE = 33.8

# ====================== HELPER FUNCTIONS ======================
def update_elo(current_elo, home, away, hg, ag):
    home_elo = get_adjusted_elo(home, current_elo)
    away_elo = get_adjusted_elo(away, current_elo)
    diff = home_elo - away_elo
    expected_home = 1 / (1 + 10 ** (-diff / ELO_SCALE))
    expected_away = 1 - expected_home
    if hg > ag:
        score_home, score_away = 1, 0
    elif hg == ag:
        score_home, score_away = 0.5, 0.5
    else:
        score_home, score_away = 0, 1
    current_elo[home] += K_FACTOR * (score_home - expected_home)
    current_elo[away] += K_FACTOR * (score_away - expected_away)

def get_adjusted_elo(team, current_elo):
    penalty = injury_penalty.get(team, 0)
    adjusted_penalty = penalty * (1 - math.exp(-penalty / INJURY_SCALE))  # nonlinear injury penalty
    return current_elo[team] - adjusted_penalty + form_adjustment.get(team, 0)

# ====================== MATCH ENGINE ======================
def simulate_match(home, away, current_elo):
    adjusted_home = get_adjusted_elo(home, current_elo)
    adjusted_away = get_adjusted_elo(away, current_elo)
    home_xg, away_xg, closeness, diff = get_match_params(home, away, adjusted_home, adjusted_away)

    # W/D/L bias adjustment for expected goals
    home_bias = wdl_rates[home]["win"] - wdl_rates[home]["loss"]
    away_bias = wdl_rates[away]["win"] - wdl_rates[away]["loss"]
    bias_diff = home_bias - away_bias
    home_xg += bias_diff * BIAS_ADJUSTMENT
    away_xg -= bias_diff * BIAS_ADJUSTMENT

    # Tempo reduction (stronger effect for close games)
    tempo_factor = TEMPO_BASE + TEMPO_RANGE * (abs(diff) / ELO_SCALE)
    home_xg *= tempo_factor
    away_xg *= tempo_factor

    variance_boost = 1 + (wdl_rates[home]["win"] - wdl_rates[home]["draw"]) * VARIANCE_BOOST_FACTOR
    

    # Draw bias for bivariate Poisson
    draw_bias = (wdl_rates[home]["draw"] + wdl_rates[away]["draw"]) / 2
    closeness_boost = closeness * draw_bias * CLOSENESS_BOOST_FACTOR
    lambda_shared = SHARED_GOAL_BASE + closeness * SHARED_GOAL_CLOSENESS * draw_bias

    lambda_home = max(MIN_LAMBDA, home_xg - lambda_shared)
    lambda_away = max(MIN_LAMBDA, away_xg - lambda_shared)

    shared_goals = np.random.poisson(lambda_shared)
    home_goals = np.random.poisson(lambda_home)
    away_goals = np.random.poisson(lambda_away)
    lambda_home *= variance_boost

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

# ====================== CHAMPIONSHIP PLAYOFF TEAMS ======================
championship_elo = {
    "Millwall": 1601,
    "Southampton": 1635,
    "Middlesbrough": 1658,
    "Hull City": 1637,
}

# Add WDL rates and form adjustments for Championship playoff teams
current_championship_points = {
    "Southampton": 86,
    "Millwall": 80,
    "Middlesbrough": 75,
    "Hull City": 72,
}
average_points = sum(current_championship_points.values()) / len(current_championship_points)
for team in championship_elo.keys():
    wdl_rates[team] = {"win": 1/3, "draw": 1/3, "loss": 1/3}
    form_adjustment[team] = (current_championship_points[team] - average_points) * FORM_MULTIPLIER

# ====================== SIMULATE PLAYOFFS ======================
def simulate_playoffs():
    # Final: Southampton vs Hull City at Wembley (neutral)
    # Hull City treated as "home" for simulation purposes
    diff = get_adjusted_elo("Hull City", championship_elo) - get_adjusted_elo("Southampton", championship_elo)  # no home advantage, but arbitrary order
    home_xg = BASE_XG + MAX_XG / (1 + math.exp(-diff / XG_SCALE))
    away_xg = BASE_XG + MAX_XG / (1 + math.exp(diff / XG_SCALE))
    closeness = math.exp(-(diff**2)/(2 * CLOSENESS_SCALE**2))
    home_bias = wdl_rates["Hull City"]["win"] - wdl_rates["Hull City"]["loss"]
    away_bias = wdl_rates["Southampton"]["win"] - wdl_rates["Southampton"]["loss"]
    bias_diff = home_bias - away_bias
    home_xg += bias_diff * BIAS_ADJUSTMENT
    away_xg -= bias_diff * BIAS_ADJUSTMENT
    tempo_factor = TEMPO_BASE + TEMPO_RANGE * (abs(diff) / ELO_SCALE)
    home_xg *= tempo_factor
    away_xg *= tempo_factor
    variance_boost = 1 + (wdl_rates["Hull City"]["win"] - wdl_rates["Hull City"]["draw"]) * VARIANCE_BOOST_FACTOR
    draw_bias = (wdl_rates["Hull City"]["draw"] + wdl_rates["Southampton"]["draw"]) / 2
    closeness_boost = closeness * draw_bias * CLOSENESS_BOOST_FACTOR
    lambda_shared = SHARED_GOAL_BASE + closeness * SHARED_GOAL_CLOSENESS * draw_bias
    lambda_home = max(MIN_LAMBDA, home_xg - lambda_shared)
    lambda_away = max(MIN_LAMBDA, away_xg - lambda_shared)
    shared_goals = np.random.poisson(lambda_shared)
    home_goals = np.random.poisson(lambda_home)
    away_goals = np.random.poisson(lambda_away)
    lambda_home *= variance_boost
    hg_final = home_goals + shared_goals
    ag_final = away_goals + shared_goals

    if hg_final > ag_final:
        promoted_team = "Hull City"
    elif ag_final > hg_final:
        promoted_team = "Southampton"
    else:
        # Draw, coin flip
        promoted_team = "Hull City" if random.random() < 0.5 else "Southampton"

    return promoted_team

# Simulate playoffs 10000 times to determine promotion distribution (final between Southampton and Hull City)
promotion_counts = {team: 0 for team in ["Southampton", "Hull City"]}
for _ in range(10000):
    promoted = simulate_playoffs()
    promotion_counts[promoted] += 1

print("Championship playoff promotion counts (out of 10000 simulations):")
for team, count in sorted(promotion_counts.items(), key=lambda x: x[1], reverse=True):
    print(f"{team}: {count}")

# Generate fixtures for match probabilities (using all teams including all possible promoted)
# Add all championship teams temporarily
for team in championship_elo:
    elo[team] = championship_elo[team]
    current[team] = {"MP":0,"Pts":0,"GF":0,"GA":0}
    form_adjustment[team] = 0
    injury_penalty[team] = 0

all_teams = list(current.keys())
all_fixtures = generate_round_robin_fixtures(all_teams)

# Remove them after generating fixtures
for team in championship_elo:
    del elo[team]
    del current[team]
    del form_adjustment[team]
    del injury_penalty[team]

# ====================== MONTE CARLO ======================
sims = 10000

title = defaultdict(int)
top4 = defaultdict(int)
europa = defaultdict(int)
conference = defaultdict(int)
total_euro = defaultdict(int)
releg = defaultdict(int)
excitement_scores = []
releg_40_count = 0
champion_points = []
avg_points = defaultdict(list)
points_distribution = defaultdict(list)



# Now run simulations grouped by promoted team
for promoted_team in sorted(promotion_counts.keys(), key=lambda x: promotion_counts[x], reverse=True):
    if promotion_counts[promoted_team] == 0:
        continue
    print(f"\nRunning {promotion_counts[promoted_team]} simulations with {promoted_team} promoted...")

    # Add promoted team to Premier League
    elo[promoted_team] = championship_elo[promoted_team]
    current[promoted_team] = {"MP":0,"Pts":0,"GF":0,"GA":0}
    form_adjustment[promoted_team] = 0
    injury_penalty[promoted_team] = 0

    teams = list(current.keys())
    fixtures = generate_round_robin_fixtures(teams)

    completed_sims = 0
    try:
        for _ in tqdm(range(promotion_counts[promoted_team]), desc=f"Simulating with {promoted_team}", unit="sim"):
            current_elo = elo.copy()

            table = {
                t: {"Pts": current[t]["Pts"], "GF": current[t]["GF"], "GA": current[t]["GA"]}
                for t in current
            }

            for home, away in fixtures:
                hg, ag = simulate_match(home, away, current_elo)
                apply_result(table, home, away, hg, ag)
                update_elo(current_elo, home, away, hg, ag)

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
                points_distribution[team].append(data["Pts"])

                if pos == 1:
                    title[team] += 1
                if pos <= 4:
                    top4[team] += 1
                if pos == 5:
                    europa[team] += 1

                if pos <= 5:
                    total_euro[team] += 1
                if pos > len(ranking) - 3:
                    releg[team] += 1

            champion_points.append(ranking[0][1]["Pts"])

            has_releg_40 = False
            for pos, (team, data) in enumerate(ranking, 1):
                if pos > len(ranking) - 3 and data["Pts"] >= 40:
                    has_releg_40 = True
                    break
            if has_releg_40:
                releg_40_count += 1

            leader_pts = ranking[0][1]["Pts"]
            second_pts = ranking[1][1]["Pts"]
            gap = leader_pts - second_pts
            excitement_scores.append(gap)

            completed_sims += 1

    except KeyboardInterrupt:
        print(f"\nSimulation interrupted after {completed_sims} simulations for {promoted_team}.")
        if completed_sims == 0:
            print("No simulations completed for this promoted team. Skipping.")

    # Remove promoted team after simulations
    del elo[promoted_team]
    del current[promoted_team]
    del form_adjustment[promoted_team]
    del injury_penalty[promoted_team]

# Add back championship teams to elo for match probabilities
for team in championship_elo:
    elo[team] = championship_elo[team]

# ====================== STATISTICS ======================
sims = 10000
team_stats = {}
for team in points_distribution.keys():
    pts = points_distribution[team]
    avg = np.mean(pts)
    std = np.std(pts)
    p25, med, p75 = np.percentile(pts, [25, 50, 75])
    team_stats[team] = {'avg': avg, 'std': std, 'p25': p25, 'med': med, 'p75': p75}

# ====================== MATCH PROBABILITIES ======================
match_prob_cache = {}

# Precompute match probabilities for all fixtures
print("Precomputing match probabilities...")
for home, away in all_fixtures:
    hw = 0
    d = 0
    aw = 0
    for _ in range(2000):
        hg, ag = simulate_match(home, away, elo)
        if hg > ag:
            hw += 1
        elif hg == ag:
            d += 1
        else:
            aw += 1
    match_prob_cache[(home, away)] = (
        hw / 2000 * 100,
        d / 2000 * 100,
        aw / 2000 * 100
    )
print("Match probabilities precomputed.")

def get_match_probs(home, away, n_sims=None):
    return match_prob_cache[(home, away)]

# ====================== OUTPUT ======================
print(f"{'Team':<15}{'AvgPts':<8}{'StdDev':<8}{'Title%':<8}{'CL%':<8}{'Europa%':<8}{'Conf%':<8}{'European%':<10}{'Releg%'}")
print("-" * 82)

rank = 1
for team in sorted(points_distribution.keys(), key=lambda x: sum(avg_points[x]) / sims, reverse=True):
    print(
        f"{team:<15}"
        f"{sum(avg_points[team])/sims:<8.2f}"
        f"{team_stats[team]['std']:<8.2f}"
        f"{title[team]/sims*100:<8.2f}"
        f"{top4[team]/sims*100:<8.2f}"
        f"{europa[team]/sims*100:<8.2f}"
        f"{conference[team]/sims*100:<8.2f}"
        f"{total_euro[team]/sims*100:<10.2f}"
        f"{releg[team]/sims*100:.2f}"
    )
    rank += 1

# Set up for remaining sections
current = {team: {"MP":0,"Pts":0,"GF":0,"GA":0} for team in all_teams}
fixtures = all_fixtures

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
print("POINTS TO WIN THE LEAGUE")
print("="*40)
print(f"Max points to win the league: {max(champion_points)}")
print(f"Min points to win the league: {min(champion_points)}")

print("\n" + "="*40)
print("ADDITIONAL STATISTICS")
print("="*40)
print(f"Probability that at least one team is relegated with 40+ points: {releg_40_count / sims * 100:.4f}%")
print(f"Average excitement score for the final day (out of 10): {np.mean(excitement_scores) / 10:.2f}")