# NFL Playoff Simulation - Starting from Wild Card Round
# Regular season complete, simulating playoffs only

import numpy as np
import pandas as pd
from collections import defaultdict, Counter
import requests

# -----------------------------
# 0. Configuration
# -----------------------------
n_sims = 10000
HFA = 100  # home field advantage in ELO points

results = defaultdict(lambda: {
    "total_wins": 0,
    "playoffs": 0,
    "conference_win": 0,
    "superbowl": 0,
})

afc_champs = []
nfc_champs = []
super_bowl_matchups = []
# 1. ELO ratings and Divisions for all 32 teams (Projected for Feb 2026)
divisions = {
    "AFC East": ["Bills", "Dolphins", "Patriots", "Jets"],
    "AFC North": ["Ravens", "Bengals", "Browns", "Steelers"],
    "AFC South": ["Texans", "Colts", "Jaguars", "Titans"],
    "AFC West": ["Chiefs", "Chargers", "Broncos", "Raiders"],
    "NFC East": ["Eagles", "Cowboys", "Giants", "Commanders"],
    "NFC North": ["Lions", "Packers", "Bears", "Vikings"],
    "NFC South": ["Falcons", "Bucs", "Saints", "Panthers"],
    "NFC West": ["Seahawks", "Rams", "49ers", "Cardinals"]
}

elo = {
    # High tier (Contenders)
    "Seahawks": 1731, "Rams": 1687, "Bills": 1613, "Texans": 1623, 
    "Broncos": 1608, "Patriots": 1581, "Steelers": 1520, "Chiefs": 1650,
    "Ravens": 1640, "Lions": 1630, "Packers": 1590, "Eagles": 1600,
    "49ers": 1533, "Bears": 1532, "Bucs": 1540, "Falcons": 1520,
    
    # Mid tier
    "Bengals": 1510, "Colts": 1500, "Chargers": 1515, "Cowboys": 1510,
    "Dolphins": 1490, "Browns": 1480, "Vikings": 1485, "Jets": 1470,
    
    # Low tier
    "Jaguars": 1450, "Titans": 1430, "Raiders": 1440, "Saints": 1420,
    "Giants": 1410, "Commanders": 1435, "Cardinals": 1445, "Panthers": 1380
}

# Mapping teams to conferences
afc_teams = [team for div in divisions if div.startswith("AFC") for team in divisions[div]]
nfc_teams = [team for div in divisions if div.startswith("NFC") for team in divisions[div]]
all_teams = afc_teams + nfc_teams


# -----------------------------
# 3. Functions
# -----------------------------
HFA = 100  # home field advantage in ELO points

def win_prob(away_team, home_team, hfa=HFA):
    """Calculate probability of away team winning"""
    elo_away = elo[away_team]
    elo_home = elo[home_team] + hfa
    return 1 / (1 + 10 ** ((elo_home - elo_away) / 400))


def generate_schedule(divisions):
    """
    Generate the official 2026 NFL schedule based on provided home opponents.
    Each entry is (Home Team: [Away Opponents])
    """
    home_opponents = {
        "Bills": ["Patriots", "Dolphins", "Jets", "Chiefs", "Chargers", "Ravens", "Bears", "Lions"],
        "Dolphins": ["Bills", "Patriots", "Jets", "Chiefs", "Chargers", "Bengals", "Bears", "Lions"],
        "Patriots": ["Bills", "Dolphins", "Jets", "Broncos", "Raiders", "Steelers", "Vikings", "Packers"],
        "Jets": ["Patriots", "Dolphins", "Bills", "Broncos", "Raiders", "Browns", "Vikings", "Packers"],
        "Ravens": ["Bengals", "Browns", "Steelers", "Jaguars", "Titans", "Chargers", "Saints", "Bucs"],
        "Bengals": ["Ravens", "Browns", "Steelers", "Jaguars", "Titans", "Chiefs", "Saints", "Bucs"],
        "Browns": ["Steelers", "Bengals", "Ravens", "Texans", "Colts", "Raiders", "Falcons", "Panthers"],
        "Steelers": ["Ravens", "Bengals", "Browns", "Texans", "Colts", "Broncos", "Falcons", "Panthers"],
        "Texans": ["Colts", "Jaguars", "Titans", "Ravens", "Bengals", "Bills", "Cowboys", "Giants"],
        "Colts": ["Texans", "Jaguars", "Titans", "Ravens", "Bengals", "Dolphins", "Cowboys", "Giants"],
        "Jaguars": ["Texans", "Colts", "Titans", "Browns", "Steelers", "Patriots", "Commanders", "Eagles"],
        "Titans": ["Texans", "Colts", "Jaguars", "Browns", "Steelers", "Jets", "Commanders", "Eagles"],
        "Broncos": ["Chiefs", "Chargers", "Raiders", "Bills", "Dolphins", "Jaguars", "Seahawks", "Rams"],
        "Chiefs": ["Broncos", "Chargers", "Raiders", "Patriots", "Jets", "Colts", "49ers", "Cardinals"],
        "Raiders": ["Chiefs", "Chargers", "Broncos", "Bills", "Dolphins", "Titans", "Rams", "Seahawks"],
        "Chargers": ["Broncos", "Chiefs", "Raiders", "Bills", "Dolphins", "Ravens", "Rams", "Seahawks"],
        "Cowboys": ["Giants", "Eagles", "Commanders", "Cardinals", "49ers", "Bucs", "Jaguars", "Titans", "Ravens"],
        "Giants": ["Commanders", "Cowboys", "Eagles", "Cardinals", "49ers", "Saints", "Jaguars", "Titans", "Browns"],
        "Eagles": ["Giants", "Cowboys", "Commanders", "Rams", "Seahawks", "Panthers", "Texans", "Colts", "Steelers"],
        "Commanders": ["Cowboys", "Eagles", "Giants", "Rams", "Seahawks", "Falcons", "Texans", "Colts", "Bengals"],
        "Bears": ["Lions", "Packers", "Vikings", "Saints", "Bucs", "Eagles", "Patriots", "Jets", "Jaguars"],
        "Lions": ["Bears", "Packers", "Vikings", "Saints", "Bucs", "Giants", "Patriots", "Jets", "Titans"],
        "Packers": ["Bears", "Lions", "Vikings", "Falcons", "Panthers", "Cowboys", "Bills", "Dolphins", "Texans"],
        "Vikings": ["Bears", "Lions", "Packers", "Falcons", "Panthers", "Commanders", "Bills", "Dolphins", "Colts"],
        "Falcons": ["Panthers", "Saints", "Bucs", "Bears", "Lions", "49ers", "Ravens", "Bengals", "Chiefs"],
        "Panthers": ["Falcons", "Saints", "Bucs", "Bears", "Lions", "Seahawks", "Ravens", "Bengals", "Broncos"],
        "Saints": ["Falcons", "Bucs", "Panthers", "Packers", "Vikings", "Cardinals", "Browns", "Steelers", "Raiders"],
        "Bucs": ["Falcons", "Panthers", "Saints", "Packers", "Vikings", "Rams", "Browns", "Steelers", "Chargers"],
        "Cardinals": ["49ers", "Rams", "Seahawks", "Eagles", "Commanders", "Lions", "Broncos", "Raiders", "Jets"],
        "Rams": ["49ers", "Cardinals", "Seahawks", "Cowboys", "Giants", "Packers", "Chiefs", "Chargers", "Bills"],
        "49ers": ["Cardinals", "Rams", "Seahawks", "Eagles", "Commanders", "Vikings", "Broncos", "Raiders", "Dolphins"],
        "Seahawks": ["Rams", "Cardinals", "49ers", "Cowboys", "Giants", "Bears", "Chiefs", "Chargers", "Patriots"],
    }
    
    schedule = []
    for home_team, aways in home_opponents.items():
        for away_team in aways:
            schedule.append((away_team, home_team))
            
    return schedule

def calculate_standings(games_results, divisions):
    """
    Calculate detailed stats for all teams for tiebreakers.
    standings[team] = {
        "W": wins, "L": losses, "T": ties,
        "div_W": divisional wins, "div_L": divisional losses,
        "conf_W": conference wins, "conf_L": conference losses,
        "h2h": {opponent: wins},
        "wins_against": [list of teams beaten],
        "opponents": [list of all opponents]
    }
    """
    standings = {team: {
        "W": 0, "L": 0, "T": 0,
        "div_W": 0, "div_L": 0,
        "conf_W": 0, "conf_L": 0,
        "h2h": defaultdict(int),
        "wins_against": [],
        "opponents": []
    } for team in all_teams}

    # Map teams to their division and conference once
    team_to_div = {}
    team_to_conf = {}
    for div, teams in divisions.items():
        conf = "AFC" if div.startswith("AFC") else "NFC"
        for t in teams:
            team_to_div[t] = div
            team_to_conf[t] = conf

    for winner, loser in games_results:
        # Standard Record
        standings[winner]["W"] += 1
        standings[winner]["wins_against"].append(loser)
        standings[loser]["L"] += 1
        
        # Track opponents for SOS
        standings[winner]["opponents"].append(loser)
        standings[loser]["opponents"].append(winner)
        
        # Head-to-Head
        standings[winner]["h2h"][loser] += 1
        
        # Divisional Record
        if team_to_div[winner] == team_to_div[loser]:
            standings[winner]["div_W"] += 1
            standings[loser]["div_L"] += 1
            
        # Conference Record
        if team_to_conf[winner] == team_to_conf[loser]:
            standings[winner]["conf_W"] += 1
            standings[loser]["conf_L"] += 1
            
    return standings

def get_sov(team, standings):
    """Strength of Victory: Average win % of teams beaten"""
    winners = standings[team]["wins_against"]
    if not winners: return 0
    total_w = sum(standings[t]["W"] for t in winners)
    total_g = sum(standings[t]["W"] + standings[t]["L"] for t in winners)
    return total_w / total_g if total_g > 0 else 0

def get_sos(team, standings):
    """Strength of Schedule: Average win % of all opponents"""
    opps = standings[team]["opponents"]
    if not opps: return 0
    total_w = sum(standings[t]["W"] for t in opps)
    total_g = sum(standings[t]["W"] + standings[t]["L"] for t in opps)
    return total_w / total_g if total_g > 0 else 0

def get_common_games_pct(teams, standings):
    """Calculate win % in games against common opponents for a group of teams"""
    if len(teams) < 2: return {t: 1.0 for t in teams}
    
    # Find common opponents
    common_opps = set(standings[teams[0]]["opponents"])
    for t in teams[1:]:
        common_opps &= set(standings[t]["opponents"])
    
    results = {}
    for t in teams:
        w = 0
        g = 0
        # This is a bit complex since we don't store individual game results in standings
        # But we can reconstruct it from wins_against and h2h
        # Actually, let's simplify: if we don't have the full game log, we'll skip for now
        # OR we can pass the game log. Let's stick to Conference/Div record for now as they are higher priority.
        results[t] = 0.5
    return results

def resolve_tie(tied_teams, standings, is_division=True):
    """
    Generic iterative tiebreaker. 
    Following NFL rule: if one drops out, restart.
    """
    if len(tied_teams) <= 1:
        return tied_teams

    # Current criteria to apply sequentially
    def h2h_pct(team, group):
        wins = 0
        games = 0
        for opp in group:
            if opp == team: continue
            w = standings[team]["h2h"].get(opp, 0)
            l = standings[opp]["h2h"].get(team, 0)
            wins += w
            games += (w + l)
        return wins / games if games > 0 else 0.5

    criteria = [
        lambda t, g: h2h_pct(t, g),
        lambda t, g: standings[t]["div_W"] if is_division else 0, # Div record only for div ties
        lambda t, g: standings[t]["conf_W"],
        lambda t, g: get_sov(t, standings),
        lambda t, g: get_sos(t, standings)
    ]

    for criterion in criteria:
        # Get values for this criterion
        values = {t: criterion(t, tied_teams) for t in tied_teams}
        max_val = max(values.values())
        min_val = min(values.values())
        
        if max_val == min_val:
            continue # All tied on this one, move to next
            
        # Someone is better. Keep the top performers.
        winners = [t for t, v in values.items() if v == max_val]
        
        if len(winners) < len(tied_teams):
            # We made progress! Restart from step 1 with the smaller group
            return resolve_tie(winners, standings, is_division)
            
    # If still tied after all criteria, use ELO or random
    return sorted(tied_teams, key=lambda t: elo[t] + np.random.random(), reverse=True)

def get_playoff_seeds(standings, divisions):
    """Determine top 7 teams per conference using official tiebreakers"""
    def get_conf_seeds(conf_name):
        conf_divs = [d for d in divisions if d.startswith(conf_name)]
        div_winners = []
        for d in conf_divs:
            d_teams = divisions[d]
            # 1. Resolve tie within division
            # Sort all teams in division by wins first
            top_wins = max(standings[t]["W"] for t in d_teams)
            tied_for_first = [t for t in d_teams if standings[t]["W"] == top_wins]
            
            if len(tied_for_first) > 1:
                winner = resolve_tie(tied_for_first, standings, is_division=True)[0]
            else:
                winner = tied_for_first[0]
            div_winners.append(winner)
        
        # 2. Seed Division Winners (1-4)
        # Ties among division winners use conference tiebreakers
        div_winners_seeds = []
        remaining_winners = div_winners.copy()
        while remaining_winners:
            top_wins = max(standings[t]["W"] for t in remaining_winners)
            tied = [t for t in remaining_winners if standings[t]["W"] == top_wins]
            if len(tied) > 1:
                best = resolve_tie(tied, standings, is_division=False)[0]
            else:
                best = tied[0]
            div_winners_seeds.append(best)
            remaining_winners.remove(best)
            
        # 3. Wildcards (5-7)
        all_conf_teams = afc_teams if conf_name == "AFC" else nfc_teams
        remaining = [t for t in all_conf_teams if t not in div_winners]
        
        wildcards = []
        while len(wildcards) < 3 and remaining:
            top_wins = max(standings[t]["W"] for t in remaining)
            tied = [t for t in remaining if standings[t]["W"] == top_wins]
            if len(tied) > 1:
                best = resolve_tie(tied, standings, is_division=False)[0]
            else:
                best = tied[0]
            wildcards.append(best)
            remaining.remove(best)
            
        return div_winners_seeds + wildcards

    return get_conf_seeds("AFC"), get_conf_seeds("NFC")

def simulate_game(team1, team2, home=None):
    """Simulate a game between two teams. If home is specified, that team has home field."""
    if home is None:  # neutral site (Super Bowl)
        prob = 1 / (1 + 10 ** ((elo[team2] - elo[team1]) / 400))
        return team1 if np.random.random() < prob else team2

    elif home == team1:
        prob = win_prob(team2, team1)  # prob of team2 (away) winning
        return team2 if np.random.random() < prob else team1
    else:  # home == team2
        prob = win_prob(team1, team2)  # prob of team1 (away) winning
        return team1 if np.random.random() < prob else team2

def simulate_conference_playoffs(seeded_teams):
    """
    Simulate complete conference playoffs from Wild Card to Championship.
    
    Args:
        seeded_teams: List of teams in seed order [1, 2, 3, 4, 5, 6, 7]
    
    Returns:
        Conference champion
    """
    # Seed #1 gets bye
    seed1 = seeded_teams[0]
    
    # Wild Card Round
    # #2 vs #7, #3 vs #6, #4 vs #5
    wc_matches = [(seeded_teams[6], seeded_teams[1]), (seeded_teams[5], seeded_teams[2]), (seeded_teams[4], seeded_teams[3])]
    wc_winners = []
    for away, home in wc_matches:
        wc_winners.append(simulate_game(away, home, home=home))
    
    # Divisional Round
    # #1 plays lowest remaining seed
    # Other two winners play each other
    remaining = [seed1] + wc_winners
    seed_map = {team: i+1 for i, team in enumerate(seeded_teams)}
    remaining_sorted = sorted(remaining, key=lambda t: seed_map[t])
    
    # #1 vs lowest seed (highest number)
    lowest_seed = remaining_sorted[-1]
    div1_winner = simulate_game(lowest_seed, seed1, home=seed1)
    
    # Other two
    other_two = remaining_sorted[1:3]
    higher_seed = other_two[0]
    lower_seed = other_two[1]
    div2_winner = simulate_game(lower_seed, higher_seed, home=higher_seed)
    
    # Conference Championship
    # Higher seed home
    finalists = sorted([div1_winner, div2_winner], key=lambda t: seed_map[t])
    conf_champ = simulate_game(finalists[1], finalists[0], home=finalists[0])
    
    return conf_champ

# -----------------------------
# 4. Monte Carlo Simulation
# -----------------------------
# Pre-generate schedule
full_schedule = generate_schedule(divisions)

for sim in range(n_sims):
    # Progress Bar
    if (sim + 1) % (n_sims // 50) == 0:
        pct = (sim + 1) / n_sims * 100
        bar = "#" * int(pct // 2) + "-" * (50 - int(pct // 2))
        print(f"\rSimulating: |{bar}| {pct:.1f}%", end="")

    # 1. Regular Season
    season_results = []
    for away, home in full_schedule:
        winner = simulate_game(away, home, home=home)
        loser = home if winner == away else away
        season_results.append((winner, loser))
    
    standings = calculate_standings(season_results, divisions)
    
    # Track season wins for results table later
    for team in all_teams:
        results[team]["total_wins"] += standings[team]["W"]
    
    # 2. Seeding
    afc_seeds, nfc_seeds = get_playoff_seeds(standings, divisions)
    
    for t in afc_seeds + nfc_seeds:
        results[t]["playoffs"] += 1

    # 3. Playoffs
    afc_champ = simulate_conference_playoffs(afc_seeds)
    nfc_champ = simulate_conference_playoffs(nfc_seeds)
    
    results[afc_champ]["conference_win"] += 1
    results[nfc_champ]["conference_win"] += 1
    
    # Super Bowl
    sb_winner = simulate_game(afc_champ, nfc_champ, home=None)
    results[sb_winner]["superbowl"] += 1
    super_bowl_matchups.append((afc_champ, nfc_champ))


# -----------------------------
# 5. Output Results
# -----------------------------
print("=" * 100)
print(f"2025-2026 NFL FULL SEASON SIMULATION (Monte Carlo)")
print("=" * 100)
print(f"Simulations: {n_sims:,}")
print(f"Home Field Advantage: {HFA} ELO points (Neutral Site for Super Bowl)")
print("-" * 100)

data = []
for team in all_teams:
    conf = "AFC" if team in afc_teams else "NFC"
    div = next(d for d in divisions if team in divisions[d])
    
    avg_wins = results[team]["total_wins"] / n_sims
    playoff_pct = results[team]["playoffs"] / n_sims * 100
    conf_pct = results[team]["conference_win"] / n_sims * 100
    sb_pct = results[team]["superbowl"] / n_sims * 100
    
    data.append({
        "Team": team,
        "Conf": conf,
        "Div": div,
        "ELO": elo[team],
        "Avg Wins": round(avg_wins, 1),
        "Playoff %": round(playoff_pct, 1),
        "Conf Champ %": round(conf_pct, 1),
        "Super Bowl %": round(sb_pct, 1)
    })

df = pd.DataFrame(data)
df = df.sort_values("Avg Wins", ascending=False)

print("\nTOP 32 TEAMS BY PROJECTED WINS")
print("-" * 100)
print(df.head(32).to_string(index=False))

print("\n" + "=" * 100)
print("SUPER BOWL FAVORITES (Top 32)")
print("-" * 100)
print(df.sort_values("Super Bowl %", ascending=False).head(32)[["Team", "Conf", "Avg Wins", "Playoff %", "Super Bowl %"]].to_string(index=False))

# Conference breakdowns
for conf in ["AFC", "NFC"]:
    print("\n" + "=" * 100)
    print(f"{conf} STANDINGS PROJECTIONS")
    print("-" * 100)
    conf_df = df[df["Conf"] == conf].sort_values("Avg Wins", ascending=False)
    print(conf_df[["Team", "Div", "Avg Wins", "Playoff %", "Super Bowl %"]].to_string(index=False))

# Super Bowl matchup
sb_matchup_counts = Counter(super_bowl_matchups)
if sb_matchup_counts:
    most_common_sb = sb_matchup_counts.most_common(10)
    print("\n" + "=" * 100)
    print(f"Top 10 Most Likely Super Bowl Matchups:")
    print("-" * 100)
    for i, ((afc_team, nfc_team), count) in enumerate(most_common_sb, 1):
        pct = count / n_sims * 100
        print(f"{i:2}. {afc_team} vs {nfc_team}: {pct:.1f}%")

print("\n" + "=" * 100)
print("Simulation Complete")
print("=" * 100)

if __name__ == "__main__":
    # The simulation runs automatically when the file is executed
    pass

print("\n" + "=" * 100)
