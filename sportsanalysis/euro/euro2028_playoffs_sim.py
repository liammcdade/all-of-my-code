import random
from collections import defaultdict
import math

# -------------------------------------------------------------
# 1. INPUT DATA
# -------------------------------------------------------------

# UEFA Euro 2028 Qualifying - All 54 eligible teams with approximate Elo rankings (as of May 2026)
# Simulation includes full qualification: group stage (12 groups of 4-5 teams), direct qualification (12 winners + 8 best runners-up),
# and playoffs (8 teams in 4 home-and-away ties for 4 spots).
all_teams = [
    "Albania", "Andorra", "Armenia", "Austria", "Azerbaijan", "Belarus", "Belgium", "Bosnia and Herzegovina",
    "Bulgaria", "Croatia", "Cyprus", "Czech Republic", "Denmark", "England", "Estonia", "Faroe Islands",
    "Finland", "France", "Georgia", "Germany", "Gibraltar", "Greece", "Hungary", "Iceland", "Israel", "Italy",
    "Kazakhstan", "Kosovo", "Latvia", "Liechtenstein", "Lithuania", "Luxembourg", "Malta", "Moldova",
    "Montenegro", "Netherlands", "North Macedonia", "Northern Ireland", "Norway", "Poland", "Portugal",
    "Republic of Ireland", "Romania", "San Marino", "Scotland", "Serbia", "Slovakia", "Slovenia", "Spain",
    "Sweden", "Switzerland", "Turkey", "Ukraine", "Wales"
]

elo_ranking = {
    'Spain': 2165, 'France': 2082, 'England': 2020, 'Portugal': 1984, 'Netherlands': 1961,
    'Croatia': 1930, 'Germany': 1923, 'Norway': 1912, 'Turkey': 1902, 'Switzerland': 1889, 'Denmark': 1870,
    'Belgium': 1866, 'Italy': 1856, 'Austria': 1827, 'Serbia': 1769, 'Ukraine': 1767, 'Scotland': 1767,
    'Greece': 1752, 'Poland': 1729, 'Uzbekistan': 1727, 'Czech Republic': 1726, 'Kosovo': 1721,
    'Sweden': 1719, 'Hungary': 1703, 'Wales': 1698, 'Slovenia': 1694, 'Republic of Ireland': 1691,
    'Slovakia': 1673, 'Georgia': 1653, 'Albania': 1646, 'Israel': 1634, 'Romania': 1627,
    'Northern Ireland': 1601, 'Bosnia and Herzegovina': 1594, 'North Macedonia': 1589, 'Iceland': 1571
}

# For teams not in known Elo, set to 1500
for team in all_teams:
    if team not in elo_ranking:
        elo_ranking[team] = 1500

# -------------------------------------------------------------
# 2. MATCH SIMULATION MODEL
# -------------------------------------------------------------

def match_prob(teamA, teamB):
    """
    Convert Elo ranking points into expected win/draw/loss probabilities.
    Simple logistic Elo-style model.
    """
    A = elo_ranking[teamA]
    B = elo_ranking[teamB]

    rating_diff = A - B
    winA = 1 / (1 + math.exp(-rating_diff / 400))
    winB = 1 - winA
    draw = 0.22  # constant draw chance
    winA *= (1-draw)
    winB *= (1-draw)
    return winA, draw, winB


def match_prob(teamA, teamB):
    """
    Convert Elo ranking points into expected win/draw/loss probabilities.
    Simple logistic Elo-style model.
    """
    A = elo_ranking[teamA]
    B = elo_ranking[teamB]

    rating_diff = A - B
    winA = 1 / (1 + math.exp(-rating_diff / 400))
    winB = 1 - winA
    draw = 0.22  # constant draw chance
    winA *= (1-draw)
    winB *= (1-draw)
    return winA, draw, winB


def simulate_match(teamA, teamB):
    winA, draw, winB = match_prob(teamA, teamB)
    r = random.random()
    if r < winA:
        return teamA
    elif r < winA + draw:
        return "DRAW"
    else:
        return teamB


def poisson(lam):
    """
    Simple Poisson random variable generator.
    """
    if lam < 30:
        L = math.exp(-lam)
        k = 0
        p = 1.0
        while p > L:
            k += 1
            p *= random.random()
        return k - 1
    else:
        # For large lambda, use normal approximation
        return max(0, int(round(random.gauss(lam, math.sqrt(lam)))))


def simulate_goals(teamA, teamB):
    """
    Simulate goals scored in a match using Poisson distribution.
    """
    rating_diff = elo_ranking[teamA] - elo_ranking[teamB]
    expected_goals_A = 1.5 + rating_diff / 600
    expected_goals_B = 1.5 - rating_diff / 600
    goals_A = poisson(expected_goals_A)
    goals_B = poisson(expected_goals_B)
    return goals_A, goals_B


def simulate_group(group_teams):
    """
    Simulate round-robin home-and-away for a group.
    Return sorted list of teams by points, GD, GF.
    """
    points = {t: 0 for t in group_teams}
    gf = {t: 0 for t in group_teams}
    ga = {t: 0 for t in group_teams}
    for i in range(len(group_teams)):
        for j in range(i+1, len(group_teams)):
            # First leg: i home vs j away
            goals_i, goals_j = simulate_goals(group_teams[i], group_teams[j])
            gf[group_teams[i]] += goals_i
            ga[group_teams[i]] += goals_j
            gf[group_teams[j]] += goals_j
            ga[group_teams[j]] += goals_i
            if goals_i > goals_j:
                points[group_teams[i]] += 3
            elif goals_j > goals_i:
                points[group_teams[j]] += 3
            else:
                points[group_teams[i]] += 1
                points[group_teams[j]] += 1
            # Second leg: j home vs i away
            goals_j2, goals_i2 = simulate_goals(group_teams[j], group_teams[i])
            gf[group_teams[i]] += goals_i2
            ga[group_teams[i]] += goals_j2
            gf[group_teams[j]] += goals_j2
            ga[group_teams[j]] += goals_i2
            if goals_i2 > goals_j2:
                points[group_teams[i]] += 3
            elif goals_j2 > goals_i2:
                points[group_teams[j]] += 3
            else:
                points[group_teams[i]] += 1
                points[group_teams[j]] += 1
    # Sort by points desc, GD desc, GF desc
    def sort_key(team):
        gd = gf[team] - ga[team]
        return (-points[team], -gd, -gf[team])
    sorted_teams = sorted(group_teams, key=sort_key)
    # Update global stats
    for team in group_teams:
        team_points[team] += points[team]
        team_gf[team] += gf[team]
        team_ga[team] += ga[team]
    return sorted_teams


def simulate_home_away(teamA, teamB):
    """
    Simulate home-and-away tie between two teams.
    Return the winner based on aggregate wins.
    """
    m1 = simulate_match(teamA, teamB)  # teamA home
    m2 = simulate_match(teamB, teamA)  # teamB home
    wins_A = (m1 == teamA) + (m2 == teamA)
    wins_B = (m1 == teamB) + (m2 == teamB)
    if wins_A > wins_B:
        return teamA
    elif wins_B > wins_A:
        return teamB
    else:
        return random.choice([teamA, teamB])  # random on tie

# -------------------------------------------------------------
# 3. PLAYOFF SIMULATION
# -------------------------------------------------------------

def simulate_euro_path(path_teams):
    teams = list(path_teams.keys())
    # Semi-finals: 0 vs 1, 2 vs 3
    semi1 = simulate_match(teams[0], teams[1])
    while semi1 == "DRAW":
        semi1 = simulate_match(teams[0], teams[1])
    semi2 = simulate_match(teams[2], teams[3])
    while semi2 == "DRAW":
        semi2 = simulate_match(teams[2], teams[3])
    # Final
    final = simulate_match(semi1, semi2)
    while final == "DRAW":
        final = simulate_match(semi1, semi2)
    return final

# -------------------------------------------------------------
# 4. FULL SIMULATION
# -------------------------------------------------------------

hosts = ["England", "Republic of Ireland", "Scotland", "Wales"]

standard_direct_counter = defaultdict(int)
reserved_counter = defaultdict(int)
playoff_counter = defaultdict(int)
total_simulations = 1000  # Number of simulations

for _ in range(total_simulations):
    team_points = defaultdict(int)
    team_gf = defaultdict(int)
    team_ga = defaultdict(int)
    # Assign hosts to separate groups
    groups = [[] for _ in range(12)]
    for i, host in enumerate(hosts):
        groups[i].append(host)
    remaining = [t for t in all_teams if t not in hosts]
    random.shuffle(remaining)
    # Groups 0-3: 4 more each (total 5)
    for i in range(4):
        groups[i].extend(remaining[i*4:(i+1)*4])
    # Groups 4-11: 4 each
    idx = 16
    for i in range(4, 12):
        groups[i].extend(remaining[idx:idx+4])
        idx += 4
    # Simulate group stage
    winners = []
    runners_up = []
    for group in groups:
        standings = simulate_group(group)
        winners.append(standings[0])
        runners_up.append(standings[1])
    # Direct qualifiers: 12 winners + 8 best runners-up (sorted by group performance)
    def sort_key(team):
        gd = team_gf[team] - team_ga[team]
        return (-team_points[team], -gd, -team_gf[team])
    runners_up_sorted = sorted(runners_up, key=sort_key)
    best_runners_up = runners_up_sorted[:8]
    initial_direct = winners + best_runners_up
    # Check hosts for reserved spots
    hosts_not_direct = [h for h in hosts if h not in set(initial_direct)]
    reserved = []
    if hosts_not_direct:
        sorted_hosts = sorted(hosts_not_direct, key=sort_key)
        reserved = sorted_hosts[:2]  # up to 2
    for team in initial_direct:
        standard_direct_counter[team] += 1
    for team in reserved:
        reserved_counter[team] += 1
    direct_qualifiers = initial_direct + reserved
    # Non-qualifiers
    non_qualifiers = [t for t in all_teams if t not in set(direct_qualifiers)]
    # Playoff spots = 4 - len(reserved)
    playoff_spots = 4 - len(reserved)
    num_playoff_teams = {4: 8, 3: 12, 2: 8}[playoff_spots]
    if playoff_spots > 0:
        playoff_teams = random.sample(non_qualifiers, num_playoff_teams)
        random.shuffle(playoff_teams)
        if playoff_spots == 4:
            # 4 home-and-away ties
            pairs = [(playoff_teams[i], playoff_teams[i+1]) for i in range(0, 8, 2)]
            for pair in pairs:
                winner = simulate_home_away(pair[0], pair[1])
                playoff_counter[winner] += 1
        elif playoff_spots == 3:
            # 3 paths: each 4 teams, single-leg semi-finals and final
            for path_start in range(0, 12, 4):
                path_teams = playoff_teams[path_start:path_start+4]
                # Semi-finals
                semi1 = simulate_match(path_teams[0], path_teams[1])
                if semi1 == "DRAW":
                    semi1 = random.choice([path_teams[0], path_teams[1]])
                semi2 = simulate_match(path_teams[2], path_teams[3])
                if semi2 == "DRAW":
                    semi2 = random.choice([path_teams[2], path_teams[3]])
                # Final
                final = simulate_match(semi1, semi2)
                if final == "DRAW":
                    final = random.choice([semi1, semi2])
                playoff_counter[final] += 1
        elif playoff_spots == 2:
            # 2 paths: each 4 teams
            for path_start in [0, 4]:
                path_teams = playoff_teams[path_start:path_start+4]
                # Semi-finals
                semi1 = simulate_match(path_teams[0], path_teams[1])
                if semi1 == "DRAW":
                    semi1 = random.choice([path_teams[0], path_teams[1]])
                semi2 = simulate_match(path_teams[2], path_teams[3])
                if semi2 == "DRAW":
                    semi2 = random.choice([path_teams[2], path_teams[3]])
                # Final
                final = simulate_match(semi1, semi2)
                if final == "DRAW":
                    final = random.choice([semi1, semi2])
                playoff_counter[final] += 1

# -------------------------------------------------------------
# 5. OUTPUT QUALIFICATION PROBABILITIES
# -------------------------------------------------------------

print("UEFA EURO 2028 QUALIFYING PLAYOFFS SIMULATION RESULTS")
print(f"Total simulations: {total_simulations}")
print("\nEURO 2028 TOTAL QUALIFICATION PROBABILITIES:")
# Total qualification = standard direct + reserved + playoff
total_qual = {team: standard_direct_counter[team] + reserved_counter[team] + playoff_counter[team] for team in all_teams}
# Sort by probability descending
sorted_teams = sorted(all_teams, key=lambda t: total_qual[t], reverse=True)
for team in sorted_teams:
    if total_qual[team] > 0:
        pct = 100 * total_qual[team] / total_simulations
        std_direct_pct = 100 * standard_direct_counter[team] / total_simulations
        res_pct = 100 * reserved_counter[team] / total_simulations
        playoff_pct = 100 * playoff_counter[team] / total_simulations
        print(f"{team}: {pct:.2f}% (Std Direct: {std_direct_pct:.2f}%, Reserved: {res_pct:.2f}%, Playoff: {playoff_pct:.2f}%)")