import numpy as np
import pandas as pd
import argparse
from rich.console import Console
from rich.table import Table
from rich import box
from tqdm import tqdm
from collections import Counter
import math
from dataclasses import dataclass, field
from typing import List, Tuple, Dict, Any

CONFIG = {
    'SIMULATION': {'DEFAULT_NUM_SIMS': 5000, 'DEFAULT_SEED': 42},
    'MATCH_SIMULATION': {'HOME_ADVANTAGE': 100, 'LEAGUE_AVG_GOALS': 2.85, 'DIXON_COLES_RHO': 0.08},
    'EUROPEAN_QUALIFICATION': {'UCL_SPOTS': 4, 'EL_SPOT_LEAGUE': 5, 'CONF_SPOT_LEAGUE': 6},
    'ELO': {'K_BASE': 40, 'HOME_ADV': 56, 'INITIAL_RATING': 1500}
}

PREMIER_LEAGUE_TEAMS = [
    "Liverpool", "Arsenal", "Manchester City", "Chelsea", "Manchester United",
    "Tottenham Hotspur", "Newcastle United", "Aston Villa", "Nottingham Forest",
    "Brighton & Hove Albion", "AFC Bournemouth", "Crystal Palace", "Everton", "Fulham",
    "Sunderland", "Leeds United", "Brentford", "Burnley", "West Ham United",
    "Wolverhampton Wanderers"
]

def calculate_current_stats(played_matches: List[Tuple[str, str, int, int]]) -> Dict[str, Dict[str, int]]:
    """Calculates current points and goal difference from played matches."""
    stats = {team: {'points': 0, 'gf': 0, 'ga': 0, 'wins': 0, 'draws': 0, 'losses': 0, 'played': 0} for team in PREMIER_LEAGUE_TEAMS}
    for home, away, h_goals, a_goals in played_matches:
        stats[home]['played'] += 1
        stats[away]['played'] += 1
        stats[home]['gf'] += h_goals
        stats[home]['ga'] += a_goals
        stats[away]['gf'] += a_goals
        stats[away]['ga'] += h_goals
        
        if h_goals > a_goals:
            stats[home]['points'] += 3
            stats[home]['wins'] += 1
            stats[away]['losses'] += 1
        elif h_goals < a_goals:
            stats[away]['points'] += 3
            stats[away]['wins'] += 1
            stats[home]['losses'] += 1
        else:
            stats[home]['points'] += 1
            stats[away]['points'] += 1
            stats[home]['draws'] += 1
            stats[away]['draws'] += 1
    return stats

def get_filtered_remaining_matches(played_matches: List[Tuple[str, str, int, int]], remaining_matches: List[Tuple[str, str]]) -> List[Tuple[str, str]]:
    """Filters out any matches from remaining_matches that have already been played."""
    played_pairs = set()
    for home, away, _, _ in played_matches:
        played_pairs.add((home, away))
    
    filtered = []
    for home, away in remaining_matches:
        if (home, away) not in played_pairs:
            filtered.append((home, away))
    return filtered


elo_ratings = {
    "Arsenal": 2066,
    "Manchester City": 1992,
    "Liverpool": 1966,
    "Chelsea": 1918,
    "Aston Villa": 1913,
    "Manchester United": 1894,
    "Newcastle United": 1865,
    "Brentford": 1853,
    "Brighton & Hove Albion": 1848,
    "AFC Bournemouth": 1841,
    "Everton": 1829,
    "Fulham": 1822,
    "Tottenham Hotspur": 1802,
    "Crystal Palace": 1797,
    "Leeds United": 1790,
    "Nottingham Forest": 1782,
    "West Ham United": 1747,
    "Burnley": 1702,
    "Sunderland": 1701,
    "Wolverhampton Wanderers": 1699,
}

# All played matches in chronological order (up to Dec 27, 2025)

CURRENT_POINTS = {
    "Arsenal": 64,
    "Manchester City": 59,
    "Manchester United": 51,
    "Aston Villa": 51,
    "Liverpool": 48,
    "Chelsea": 45,
    "Brentford": 44,
    "Everton": 43,
    "AFC Bournemouth": 40,
    "Fulham": 40,
    "Sunderland": 40,
    "Brighton & Hove Albion": 37,
    "Newcastle United": 36,
    "Crystal Palace": 35,
    "Leeds United": 31,
    "Tottenham Hotspur": 29,
    "Nottingham Forest": 27,
    "West Ham United": 25,
    "Burnley": 19,
    "Wolverhampton Wanderers": 16
}



REMAINING_MATCHES = [
 

    # Matchweek 29
    ("AFC Bournemouth", "Brentford"),
    ("Aston Villa", "Chelsea"),
    ("Brighton & Hove Albion", "Arsenal"),
    ("Everton", "Burnley"),
    ("Fulham", "West Ham United"),
    ("Leeds United", "Sunderland"),
    ("Manchester City", "Nottingham Forest"),
    ("Newcastle United", "Manchester United"),
    ("Tottenham Hotspur", "Crystal Palace"),
    ("Wolverhampton Wanderers", "Liverpool"),

    # Matchweek 30
    ("Arsenal", "Everton"),
    ("Brentford", "Wolverhampton Wanderers"),
    ("Burnley", "AFC Bournemouth"),
    ("Chelsea", "Newcastle United"),
    ("Crystal Palace", "Leeds United"),
    ("Liverpool", "Tottenham Hotspur"),
    ("Manchester United", "Aston Villa"),
    ("Nottingham Forest", "Fulham"),
    ("Sunderland", "Brighton & Hove Albion"),
    ("West Ham United", "Manchester City"),

    # Matchweek 31
    ("AFC Bournemouth", "Manchester United"),
    ("Aston Villa", "West Ham United"),
    ("Brighton & Hove Albion", "Liverpool"),
    ("Everton", "Chelsea"),
    ("Fulham", "Burnley"),
    ("Leeds United", "Brentford"),
    ("Manchester City", "Crystal Palace"),
    ("Newcastle United", "Sunderland"),
    ("Tottenham Hotspur", "Nottingham Forest"),
    ("Wolverhampton Wanderers", "Arsenal"),

    # Matchweek 32
    ("Arsenal", "AFC Bournemouth"),
    ("Brentford", "Everton"),
    ("Burnley", "Brighton & Hove Albion"),
    ("Chelsea", "Manchester City"),
    ("Crystal Palace", "Newcastle United"),
    ("Liverpool", "Fulham"),
    ("Manchester United", "Leeds United"),
    ("Nottingham Forest", "Aston Villa"),
    ("Sunderland", "Tottenham Hotspur"),
    ("West Ham United", "Wolverhampton Wanderers"),

    # Matchweek 33
    ("Aston Villa", "Sunderland"),
    ("Brentford", "Fulham"),
    ("Chelsea", "Manchester United"),
    ("Crystal Palace", "West Ham United"),
    ("Everton", "Liverpool"),
    ("Leeds United", "Wolverhampton Wanderers"),
    ("Manchester City", "Arsenal"),
    ("Newcastle United", "AFC Bournemouth"),
    ("Nottingham Forest", "Burnley"),
    ("Tottenham Hotspur", "Brighton & Hove Albion"),

    # Matchweek 34
    ("AFC Bournemouth", "Leeds United"),
    ("Arsenal", "Newcastle United"),
    ("Brighton & Hove Albion", "Chelsea"),
    ("Burnley", "Manchester City"),
    ("Fulham", "Aston Villa"),
    ("Liverpool", "Crystal Palace"),
    ("Manchester United", "Brentford"),
    ("Sunderland", "Nottingham Forest"),
    ("West Ham United", "Everton"),
    ("Wolverhampton Wanderers", "Tottenham Hotspur"),

    # Matchweek 35
    ("AFC Bournemouth", "Crystal Palace"),
    ("Arsenal", "Fulham"),
    ("Aston Villa", "Tottenham Hotspur"),
    ("Brentford", "West Ham United"),
    ("Chelsea", "Nottingham Forest"),
    ("Everton", "Manchester City"),
    ("Leeds United", "Burnley"),
    ("Manchester United", "Liverpool"),
    ("Newcastle United", "Brighton & Hove Albion"),
    ("Wolverhampton Wanderers", "Sunderland"),

    # Matchweek 36
    ("Brighton & Hove Albion", "Wolverhampton Wanderers"),
    ("Burnley", "Aston Villa"),
    ("Crystal Palace", "Everton"),
    ("Fulham", "AFC Bournemouth"),
    ("Liverpool", "Chelsea"),
    ("Manchester City", "Brentford"),
    ("Nottingham Forest", "Newcastle United"),
    ("Sunderland", "Manchester United"),
    ("Tottenham Hotspur", "Leeds United"),
    ("West Ham United", "Arsenal"),

    # Matchweek 37
    ("AFC Bournemouth", "Manchester City"),
    ("Arsenal", "Burnley"),
    ("Aston Villa", "Liverpool"),
    ("Brentford", "Crystal Palace"),
    ("Chelsea", "Tottenham Hotspur"),
    ("Everton", "Sunderland"),
    ("Leeds United", "Brighton & Hove Albion"),
    ("Manchester United", "Nottingham Forest"),
    ("Newcastle United", "West Ham United"),
    ("Wolverhampton Wanderers", "Fulham"),

    # Matchweek 38
    ("Brighton & Hove Albion", "Manchester United"),
    ("Burnley", "Wolverhampton Wanderers"),
    ("Crystal Palace", "Arsenal"),
    ("Fulham", "Newcastle United"),
    ("Liverpool", "Brentford"),
    ("Manchester City", "Aston Villa"),
    ("Nottingham Forest", "AFC Bournemouth"),
    ("Sunderland", "Chelsea"),
    ("Tottenham Hotspur", "Everton"),
    ("West Ham United", "Leeds United"),
]

def compute_current_elo():
    ratings = {team: CONFIG['ELO']['INITIAL_RATING'] for team in PREMIER_LEAGUE_TEAMS}
    
    for home, away, home_goals, away_goals in PLAYED_MATCHES:
        dr = ratings[home] - ratings[away] + CONFIG['ELO']['HOME_ADV']
        we_home = 1 / (1 + math.pow(10, -dr / 400))
        
        if home_goals > away_goals:
            w_home = 1
            gd = home_goals - away_goals
        elif home_goals < away_goals:
            w_home = 0
            gd = away_goals - home_goals
        else:
            w_home = 0.5
            gd = 0
        
        if gd <= 1:
            k_adj = CONFIG['ELO']['K_BASE']
        elif gd == 2:
            k_adj = CONFIG['ELO']['K_BASE'] * 1.5
        elif gd == 3:
            k_adj = CONFIG['ELO']['K_BASE'] * 1.75
        else:
            k_adj = CONFIG['ELO']['K_BASE'] * (1.75 + (gd - 3) / 8)
        
        delta = k_adj * (w_home - we_home)
        ratings[home] += delta
        ratings[away] -= delta
    
    # Round to nearest int
    return {team: round(ratings[team]) for team in PREMIER_LEAGUE_TEAMS}

# Compute fresh every run - but use hardcoded values from above instead
# elo_ratings = compute_current_elo()  # Commented out - using hardcoded ELO instead

# Update min/max for normalization
max_elo = max(elo_ratings.values())
min_elo = min(elo_ratings.values())
elo_range = max_elo - min_elo if max_elo > min_elo else 1

# Rest of your simulation code unchanged...

def simulate_match_points(home_team, away_team, rng):
    home_adv = CONFIG['MATCH_SIMULATION']['HOME_ADVANTAGE']
    league_avg = CONFIG['MATCH_SIMULATION']['LEAGUE_AVG_GOALS']
    rho = CONFIG['MATCH_SIMULATION']['DIXON_COLES_RHO']

    home_elo = elo_ratings.get(home_team, CONFIG['ELO']['INITIAL_RATING']) + home_adv
    away_elo = elo_ratings.get(away_team, CONFIG['ELO']['INITIAL_RATING'])

    home_attack = (home_elo - min_elo) / elo_range
    home_defense = 1 - home_attack
    away_attack = (away_elo - min_elo) / elo_range
    away_defense = 1 - away_attack

    lambda_home = league_avg * home_attack * (1 - away_defense)
    lambda_away = league_avg * away_attack * (1 - home_defense)

    home_goals = rng.poisson(lambda_home)
    away_goals = rng.poisson(lambda_away)

    if home_goals == 0 and away_goals == 0:
        if rng.random() < rho:
            home_goals = away_goals = 1
    elif home_goals == 1 and away_goals == 1:
        if rng.random() < rho:
            home_goals = away_goals = 0

    if home_goals > away_goals:
        return home_goals, away_goals, 3, 0
    elif home_goals == away_goals:
        return home_goals, away_goals, 1, 1
    else:
        return home_goals, away_goals, 0, 3

# Keep the rest exactly as before: simulate_season, cup sims, monte carlo, print_rich_table, main with current_points

def simulate_season(teams, matches, rng, current_points):
    from collections import Counter
    match_counts = Counter()
    for home, away in matches:
        match_counts[home] += 1
        match_counts[away] += 1
    stats = {team: {'wins': 0, 'draws': 0, 'losses': 0, 'gf': 0, 'ga': 0, 'points': current_points[team]} for team in teams}

    for home, away in matches:
        home_goals, away_goals, home_pts, away_pts = simulate_match_points(home, away, rng)
        stats[home]['gf'] += home_goals
        stats[home]['ga'] += away_goals
        stats[away]['gf'] += away_goals
        stats[away]['ga'] += home_goals
        if home_pts == 3:
            stats[home]['wins'] += 1
            stats[away]['losses'] += 1
        elif home_pts == 1:
            stats[home]['draws'] += 1
            stats[away]['draws'] += 1
        else:
            stats[home]['losses'] += 1
            stats[away]['wins'] += 1
        stats[home]['points'] += home_pts
        stats[away]['points'] += away_pts
    return stats

def run_monte_carlo_simulation(teams, played_matches, remaining_matches, num_simulations=500, random_seed=42, current_points=None):
    """Runs the Monte Carlo simulation for the rest of the season."""
    # Use hard-coded CURRENT_POINTS if not provided
    if current_points is None:
        current_stats = calculate_current_stats(played_matches)
        current_points = {team: current_stats[team]['points'] for team in teams}
    matches = get_filtered_remaining_matches(played_matches, remaining_matches)

    match_counts = Counter()
    for home, away in matches:
        match_counts[home] += 1
        match_counts[away] += 1
    matches_remaining = {team: match_counts.get(team, 0) for team in teams}

    if num_simulations > 0:
        rng = np.random.default_rng(random_seed)
        all_results = {team: [] for team in teams}
        for _ in tqdm(range(num_simulations), desc="Simulating Seasons"):
            season_results = simulate_season(teams, matches, rng, current_points)
            for team in teams:
                all_results[team].append(season_results[team])

        # Compute averages
        avg_stats = {}
        for team in teams:
            team_stats = all_results[team]
            avg_stats[team] = {
                'points': np.mean([s['points'] for s in team_stats])
            }

        # For probabilities, count positions
        title_counts = Counter()
        top4_counts = Counter()
        top6_counts = Counter()
        releg_counts = Counter()
        fifth_counts = Counter()
        conf_counts = Counter()
        
        for sim in range(num_simulations):
            points_in_sim = {team: all_results[team][sim]['points'] for team in teams}
            # Add goal difference as a tie-breaker (simulated)
            # Actually, let's keep it simple for now as per original
            sorted_sim = sorted(teams, key=lambda t: points_in_sim[t], reverse=True)
            
            title_counts[sorted_sim[0]] += 1
            for team in sorted_sim[:4]:
                top4_counts[team] += 1
            for team in sorted_sim[:6]:
                top6_counts[team] += 1
            for team in sorted_sim[17:]:
                releg_counts[team] += 1
            
            fifth_counts[sorted_sim[4]] += 1
            fifth_counts[sorted_sim[5]] += 1
            conf_counts[sorted_sim[6]] += 1

        results = {
            'Team': teams,
            'Expected Points': [avg_stats[t]['points'] for t in teams],
            'Chance of Winning': [title_counts[t] / num_simulations * 100 for t in teams],
            'Chance of Top 4': [top4_counts[t] / num_simulations * 100 for t in teams],
            'Chance of Europa League': [fifth_counts[t] / num_simulations * 100 for t in teams],
            'Chance of Conference League': [conf_counts[t] / num_simulations * 100 for t in teams],
            'Chance of Relegation': [releg_counts[t] / num_simulations * 100 for t in teams]
        }

        final_df = pd.DataFrame(results).sort_values('Expected Points', ascending=False).reset_index(drop=True)
        return final_df

def print_rich_table(df):
    console = Console()

    table = Table(title="Premier League 2025-26 Simulation", box=box.SQUARE, border_style="blue")

    columns = [
        "Pos", "Team", "Exp Pts", "Title %", "CL %", "EL %", "Conf %", "Releg %"
    ]

    for col in columns:
        table.add_column(col, style="cyan", header_style="bold cyan")

    for pos, (_, row) in enumerate(df.iterrows(), 1):
        table.add_row(
            str(pos),
            str(row['Team']),
            f"{row['Expected Points']:.1f}",
            f"{row['Chance of Winning']:.1f}%",
            f"{row['Chance of Top 4']:.1f}%",
            f"{row['Chance of Europa League']:.1f}%",
            f"{row['Chance of Conference League']:.1f}%",
            f"{row['Chance of Relegation']:.1f}%"
        )

    console.print(table)

    console.print("\n[bold green]Top 3 Title Contenders:[/bold green]")
    for i, (_, row) in enumerate(df.head(3).iterrows(), 1):
        console.print(f"  {i}. {row['Team']} - {row['Chance of Winning']:.1f}%")

    console.print("\n[bold red]Most Likely Relegation:[/bold red]")
    relegation_candidates = df.nlargest(3, 'Chance of Relegation')
    for i, (_, row) in enumerate(relegation_candidates.iterrows(), 1):
        console.print(f"  {i}. {row['Team']} - {row['Chance of Relegation']:.1f}%")

def main():
    parser = argparse.ArgumentParser(description='Premier League Simulation')
    parser.add_argument('--nsims', type=int, default=5000)
    parser.add_argument('--seed', type=int, default=42)
    args = parser.parse_args()

    # Use empty played_matches and hard-coded CURRENT_POINTS
    results_df = run_monte_carlo_simulation(
        teams=PREMIER_LEAGUE_TEAMS,
        played_matches=[],  # No played matches - only simulating future games
        remaining_matches=REMAINING_MATCHES,
        num_simulations=args.nsims,
        random_seed=args.seed,
        current_points=CURRENT_POINTS  # Use hard-coded current points
    )

    print_rich_table(results_df)

if __name__ == "__main__":
    main()