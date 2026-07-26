import numpy as np
from tqdm import tqdm

# 1. Data Setup
groups = {
    "A": ["Morocco", "Gabon", "Niger", "Lesotho"],
    "B": ["Egypt", "Angola", "Malawi", "South Sudan"],
    "C": ["Ivory Coast", "Ghana", "Gambia", "Somalia"],
    "D": ["South Africa", "Guinea", "Kenya", "Eritrea"],
    "E": ["DR Congo", "Equatorial Guinea", "Sierra Leone", "Zimbabwe"],
    "F": ["Burkina Faso", "Benin", "Mauritania", "Central African Republic"],
    "G": ["Cameroon", "Comoros", "Namibia", "Congo"],
    "H": ["Tunisia", "Uganda", "Libya", "Botswana"],
    "I": ["Algeria", "Zambia", "Togo", "Burundi"],
    "J": ["Senegal", "Mozambique", "Sudan", "Ethiopia"],
    "K": ["Mali", "Cape Verde", "Rwanda", "Liberia"],
    "L": ["Nigeria", "Madagascar", "Tanzania", "Guinea-Bissau"]
}

hosts = {"Kenya", "Uganda", "Tanzania"}

# Elo ratings extracted from the provided list
elos = {
    "Morocco": 1822, "Gabon": 1401, "Niger": 1393, "Lesotho": 1205,
    "Egypt": 1699, "Angola": 1541, "Malawi": 1241, "South Sudan": 1109,
    "Ivory Coast": 1676, "Ghana": 1503, "Gambia": 1419, "Somalia": 979,
    "South Africa": 1517, "Guinea": 1469, "Kenya": 1356, "Eritrea": 1201,
    "DR Congo": 1655, "Equatorial Guinea": 1390, "Sierra Leone": 1348, "Zimbabwe": 1372,
    "Burkina Faso": 1530, "Benin": 1429, "Mauritania": 1311, "Central African Republic": 1239,
    "Cameroon": 1614, "Comoros": 1362, "Namibia": 1303, "Congo": 1206,
    "Tunisia": 1636, "Uganda": 1394, "Libya": 1420, "Botswana": 1267,
    "Algeria": 1743, "Zambia": 1370, "Togo": 1358, "Burundi": 1285,
    "Senegal": 1866, "Mozambique": 1372, "Sudan": 1350, "Ethiopia": 1285,
    "Mali": 1596, "Cape Verde": 1576, "Rwanda": 1336, "Liberia": 1296,
    "Nigeria": 1769, "Madagascar": 1382, "Tanzania": 1313, "Guinea-Bissau": 1248
}

def get_standings(teams, matches):
    """Calculates standings applying CAF tiebreaker rules."""
    stats = {t: {'pts': 0, 'gd': 0, 'gf': 0, 'ga': 0, 'away_gf': 0} for t in teams}
    
    # Calculate overall stats
    for m in matches:
        h, a = m['home'], m['away']
        gh, ga = m['goals_home'], m['goals_away']
        stats[h]['gf'] += gh; stats[h]['ga'] += ga; stats[h]['gd'] += (gh - ga)
        stats[a]['gf'] += ga; stats[a]['ga'] += gh; stats[a]['gd'] += (ga - gh)
        stats[a]['away_gf'] += ga
        if gh > ga: stats[h]['pts'] += 3
        elif gh < ga: stats[a]['pts'] += 3
        else: stats[h]['pts'] += 1; stats[a]['pts'] += 1

    # Calculate Head-to-Head stats exclusively among teams tied on overall points
    h2h_stats = {t: {'pts': 0, 'gd': 0, 'gf': 0, 'away_gf': 0} for t in teams}
    for t in teams:
        tied_teams = [x for x in teams if stats[x]['pts'] == stats[t]['pts']]
        for m in matches:
            if m['home'] in tied_teams and m['away'] in tied_teams:
                h, a = m['home'], m['away']
                gh, ga = m['goals_home'], m['goals_away']
                if h == t:
                    h2h_stats[t]['gf'] += gh
                    h2h_stats[t]['gd'] += (gh - ga)
                    if gh > ga: h2h_stats[t]['pts'] += 3
                    elif gh == ga: h2h_stats[t]['pts'] += 1
                elif a == t:
                    h2h_stats[t]['gf'] += ga
                    h2h_stats[t]['gd'] += (ga - gh)
                    h2h_stats[t]['away_gf'] += ga
                    if ga > gh: h2h_stats[t]['pts'] += 3
                    elif ga == gh: h2h_stats[t]['pts'] += 1

    # Sort based on hierarchical tiebreakers
    sorted_teams = sorted(teams, key=lambda t: (
        stats[t]['pts'],
        h2h_stats[t]['pts'],
        h2h_stats[t]['gd'],
        h2h_stats[t]['gf'],
        h2h_stats[t]['away_gf'],
        stats[t]['gd'],
        stats[t]['gf'],
        stats[t]['away_gf']
    ), reverse=True)
    
    return sorted_teams, stats

def simulate_group(group_teams, hosts):
    """Simulates all matches in a group and returns exactly 2 qualifiers."""
    matches = []
    
    # Each pair plays twice (home and away)
    for i in range(len(group_teams)):
        for j in range(i + 1, len(group_teams)):
            t1, t2 = group_teams[i], group_teams[j]
            elo1, elo2 = elos[t1], elos[t2]
            
            # Match 1: t1 is home (+50 Elo advantage)
            mu_home = 1.2 * (10 ** ((elo1 + 50 - elo2) / 400))
            mu_away = 1.2 * (10 ** ((elo2 - (elo1 + 50)) / 400))
            g_home = np.random.poisson(mu_home)
            g_away = np.random.poisson(mu_away)
            matches.append({'home': t1, 'away': t2, 'goals_home': int(g_home), 'goals_away': int(g_away)})
            
            # Match 2: t2 is home (+50 Elo advantage)
            mu_home = 1.2 * (10 ** ((elo2 + 50 - elo1) / 400))
            mu_away = 1.2 * (10 ** ((elo1 - (elo2 + 50)) / 400))
            g_home = np.random.poisson(mu_home)
            g_away = np.random.poisson(mu_away)
            matches.append({'home': t2, 'away': t1, 'goals_home': int(g_home), 'goals_away': int(g_away)})
            
    sorted_teams, stats = get_standings(group_teams, matches)
    
    qualifiers = []
    has_host = any(t in hosts for t in group_teams)
    
    if has_host:
        # Host qualifies automatically
        host_team = [t for t in group_teams if t in hosts][0]
        qualifiers.append(host_team)
        
        # The best-performing non-host team qualifies alongside them
        for t in sorted_teams:
            if t != host_team:
                qualifiers.append(t)
                break
    else:
        # Standard rule: Best 2 performing teams qualify
        qualifiers.append(sorted_teams[0])
        qualifiers.append(sorted_teams[1])
        
    return qualifiers

# 2. Run Monte Carlo Simulation
NUM_SIMS = 10000
qualification_counts = {t: 0 for t in elos.keys()}

print(f"Starting {NUM_SIMS:,} Monte Carlo simulations...\n")

# Wrap the loop with tqdm for a real-time progress bar
for _ in tqdm(range(NUM_SIMS), desc="Simulating Groups", unit="sim"):
    for group_name, teams in groups.items():
        qs = simulate_group(teams, hosts)
        for q in qs:
            qualification_counts[q] += 1

# 3. Output Results
print("\n" + "="*70)
print("MOST LIKELY QUALIFIERS PER GROUP (Top 2)")
print("="*70)
for group_name, teams in groups.items():
    group_counts = {t: qualification_counts[t] for t in teams}
    sorted_group = sorted(group_counts.items(), key=lambda x: x[1], reverse=True)
    
    has_host = any(t in hosts for t in teams)
    if has_host:
        host_team = [t for t in teams if t in hosts][0]
        non_hosts = [t for t, c in sorted_group if t != host_team]
        print(f"Group {group_name:<2}: {host_team:<18} (Host) & {non_hosts[0]}")
    else:
        print(f"Group {group_name:<2}: {sorted_group[0][0]:<18} & {sorted_group[1][0]}")

print("\n" + "="*70)
print("TOP QUALIFICATION PROBABILITIES (All Teams)")
print("="*70)
sorted_probs = sorted(qualification_counts.items(), key=lambda x: x[1], reverse=True)
for team, count in sorted_probs:
    if count > 0:
        print(f"{team:<25} {count / NUM_SIMS * 100:6.2f}%")