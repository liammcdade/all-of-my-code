import numpy as np
import pandas as pd
import argparse
from rich.console import Console
from rich.table import Table
from rich import box
from tqdm import tqdm
import math

CONFIG = {
    'SIMULATION': {'DEFAULT_NUM_SIMS': 1000, 'DEFAULT_SEED': 42},
    'MATCH_SIMULATION': {'HOME_ADVANTAGE': 100, 'LEAGUE_AVG_GOALS': 2.85, 'DIXON_COLES_RHO': 0.08},
    'ELO': {'K_BASE': 40, 'HOME_ADV': 100, 'INITIAL_RATING': 1800}
}

# FA Cup teams in Fourth Round
FA_CUP_TEAMS = [
    "Hull City", "Chelsea", "Wrexham", "Ipswich Town", "Burton Albion", "West Ham United",
    "Burnley", "Mansfield Town", "Manchester City", "Salford City", "Norwich City",
    "West Bromwich Albion", "Southampton", "Leicester City", "Liverpool", "Brighton & Hove Albion",
    "Birmingham City", "Leeds United", "Grimsby Town", "Wolverhampton Wanderers", "Oxford United",
    "Sunderland", "Stoke City", "Fulham", "Arsenal", "Wigan Athletic", "Port Vale", "Bristol City",
    "Macclesfield", "Brentford", "Aston Villa", "Newcastle United"
]

# FA Cup Fourth Round fixtures
FA_CUP_MATCHES = [
    ("Hull City", "Chelsea"),
    ("Wrexham", "Ipswich Town"),
    ("Burton Albion", "West Ham United"),
    ("Burnley", "Mansfield Town"),
    ("Manchester City", "Salford City"),
    ("Norwich City", "West Bromwich Albion"),
    ("Southampton", "Leicester City"),
    ("Liverpool", "Brighton & Hove Albion"),
    ("Birmingham City", "Leeds United"),
    ("Grimsby Town", "Wolverhampton Wanderers"),
    ("Oxford United", "Sunderland"),
    ("Stoke City", "Fulham"),
    ("Arsenal", "Wigan Athletic"),
    ("Macclesfield", "Brentford"),
    ("Port Vale", "Bristol City"),
    ("Aston Villa", "Newcastle United")
]

knownwinners = [
    "Chelsea", "Wrexham", "West Ham United", "Mansfield Town", "Manchester City",
    "Norwich City", "Southampton", "Newcastle United", "Liverpool"
]

# Basic Elo ratings - higher for Premier League teams, lower for lower league teams
elo_ratings = {
    # Premier League teams
    "Arsenal": 2042, "Aston Villa": 1830, "Bournemouth": 1770, "Brighton & Hove Albion": 1820,
    "Burnley": 1750, "Chelsea": 1910, "Crystal Palace": 1805, "Everton": 1800,
    "Fulham": 1810, "Liverpool": 2034, "Manchester City": 1978, "Manchester United": 1900,
    "Newcastle United": 1897, "Nottingham Forest": 1780, "Tottenham Hotspur": 1890, "West Ham United": 1790,
    "Wolverhampton Wanderers": 1840, "Southampton": 1810,

    # Championship teams
    "Blackburn Rovers": 1640, "Brentford": 1700, "Derby County": 1570, "Hull City": 1720,
    "Ipswich Town": 1760, "Leeds United": 1770, "Leicester City": 1780, "Middlesbrough": 1680,
    "Millwall": 1630, "Norwich City": 1690, "Portsmouth": 1580, "Preston North End": 1710,
    "Queens Park Rangers": 1590, "Sheffield United": 1650, "Sheffield Wednesday": 1660,
    "Sunderland": 1730, "Swansea City": 1610, "West Bromwich Albion": 1740,
    "Stoke City": 1640, "Bristol City": 1670, "Birmingham City": 1580,

    # League One teams
    "Barnsley": 1520, "Blackpool": 1510, "Charlton Athletic": 1460, "Cheltenham Town": 1450,
    "Exeter City": 1480, "Fleetwood Town": 1420, "Milton Keynes Dons": 1380, "Oxford United": 1540,
    "Port Vale": 1410, "Wigan Athletic": 1470, "Burton Albion": 1450,

    # League Two teams
    "Grimsby Town": 1180, "Mansfield Town": 1360, "Salford City": 1340, "Swindon Town": 1350,
    "Walsall": 1190, "Wrexham": 1370,

    # National League teams
    "Boreham Wood": 1180, "Brackley Town": 1170,

    # Other teams
    "Macclesfield": 950, "Weston-super-Mare": 900
}

def generate_pairings(teams, strategy, rng):
    """
    Generate match pairings for a round using different strategies.
    
    Args:
        teams: List of teams to pair
        strategy: Integer indicating which pairing strategy to use (0-indexed)
        rng: Random number generator
    
    Returns:
        List of tuples (home_team, away_team)
    """
    teams = teams.copy()
    num_teams = len(teams)
    
    # Ensure even number
    if num_teams % 2 != 0:
        teams = teams[:-1]
    
    num_strategies = 6
    strategy = strategy % num_strategies
    
    if strategy == 0:  # Seeded pairing (best vs worst, 2nd best vs 2nd worst, etc.)
        # Sort teams by Elo rating
        sorted_teams = sorted(teams, key=lambda x: elo_ratings.get(x, CONFIG['ELO']['INITIAL_RATING']), reverse=True)
        matches = []
        for i in range(len(sorted_teams) // 2):
            matches.append((sorted_teams[i], sorted_teams[-(i+1)]))
        return matches
    
    elif strategy == 1:  # Reverse seeded (best vs 2nd best, 3rd vs 4th, etc.)
        sorted_teams = sorted(teams, key=lambda x: elo_ratings.get(x, CONFIG['ELO']['INITIAL_RATING']), reverse=True)
        matches = []
        for i in range(0, len(sorted_teams), 2):
            matches.append((sorted_teams[i], sorted_teams[i+1]))
        return matches
    
    elif strategy == 2:  # Balanced brackets (split into two halves, pair across halves)
        sorted_teams = sorted(teams, key=lambda x: elo_ratings.get(x, CONFIG['ELO']['INITIAL_RATING']), reverse=True)
        mid = len(sorted_teams) // 2
        top_half = sorted_teams[:mid]
        bottom_half = sorted_teams[mid:]
        matches = []
        # Pair across halves: best of top vs best of bottom, etc.
        min_len = min(len(top_half), len(bottom_half))
        for i in range(min_len):
            matches.append((top_half[i], bottom_half[i]))
        return matches
    
    elif strategy == 3:  # Random pairing (original approach)
        rng.shuffle(teams)
        matches = [(teams[i], teams[i+1]) for i in range(0, len(teams), 2)]
        return matches
    
    elif strategy == 4:  # Alternating strength (1st vs 3rd, 2nd vs 4th, etc.)
        sorted_teams = sorted(teams, key=lambda x: elo_ratings.get(x, CONFIG['ELO']['INITIAL_RATING']), reverse=True)
        matches = []
        for i in range(len(sorted_teams) // 2):
            matches.append((sorted_teams[i], sorted_teams[i + len(sorted_teams) // 2]))
        return matches
    
    else:  # strategy == 5: Random with slight seeding bias
        sorted_teams = sorted(teams, key=lambda x: elo_ratings.get(x, CONFIG['ELO']['INITIAL_RATING']), reverse=True)
        # Shuffle but keep some structure - swap pairs
        rng.shuffle(sorted_teams)
        # Group into pairs and swap occasionally
        matches = [(sorted_teams[i], sorted_teams[i+1]) for i in range(0, len(sorted_teams), 2)]
        # Randomly swap some pairs
        for i in range(len(matches)):
            if rng.random() < 0.3:
                matches[i] = (matches[i][1], matches[i][0])
        return matches

def simulate_fa_cup_match(home_team, away_team, rng, fixed_winner=None):
    """Simulate a single FA Cup match"""
    # If a fixed winner is specified, return that result
    if fixed_winner:
        if fixed_winner == home_team:
            return 2, 1, home_team, f"{home_team} 2-1 {away_team}"
        elif fixed_winner == away_team:
            return 1, 2, away_team, f"{away_team} 2-1 {home_team}"
    
    home_adv = CONFIG['MATCH_SIMULATION']['HOME_ADVANTAGE']
    league_avg = CONFIG['MATCH_SIMULATION']['LEAGUE_AVG_GOALS']
    rho = CONFIG['MATCH_SIMULATION']['DIXON_COLES_RHO']

    home_elo = elo_ratings.get(home_team, CONFIG['ELO']['INITIAL_RATING']) + home_adv
    away_elo = elo_ratings.get(away_team, CONFIG['ELO']['INITIAL_RATING'])

    # Normalize Elo ratings to create attack/defense strengths
    max_elo = max(elo_ratings.values())
    min_elo = min(elo_ratings.values())
    elo_range = max_elo - min_elo if max_elo > min_elo else 1

    home_attack = (home_elo - min_elo) / elo_range
    home_defense = 1 - home_attack
    away_attack = (away_elo - min_elo) / elo_range
    away_defense = 1 - away_attack

    # Ensure values are within reasonable bounds
    home_attack = max(0.1, min(0.9, home_attack))
    home_defense = max(0.1, min(0.9, home_defense))
    away_attack = max(0.1, min(0.9, away_attack))
    away_defense = max(0.1, min(0.9, away_defense))

    lambda_home = league_avg * home_attack * away_defense
    lambda_away = league_avg * away_attack * home_defense

    # Ensure lambda values are positive and not too large
    lambda_home = max(0.1, min(5.0, lambda_home))
    lambda_away = max(0.1, min(5.0, lambda_away))

    home_goals = rng.poisson(lambda_home)
    away_goals = rng.poisson(lambda_away)

    if home_goals == 0 and away_goals == 0:
        if rng.random() < rho:
            home_goals = away_goals = 1
    elif home_goals == 1 and away_goals == 1:
        if rng.random() < rho:
            home_goals = away_goals = 0

    if home_goals > away_goals:
        return home_goals, away_goals, home_team, f"{home_team} {home_goals}-{away_goals} {away_team}"
    elif home_goals == away_goals:
        # In FA Cup, draws go to replay - for simulation purposes, we'll simulate a winner
        # In reality, there would be a replay, but we'll decide winner here
        if rng.random() < 0.5:
            return home_goals, away_goals, home_team, f"{home_team} {home_goals}-{away_goals} {away_team} (after replay)"
        else:
            return home_goals, away_goals, away_team, f"{away_team} {away_goals}-{home_goals} {home_team} (after replay)"
    else:
        return home_goals, away_goals, away_team, f"{away_team} {away_goals}-{home_goals} {home_team}"

def simulate_full_fa_cup_tournament(rng, pairing_strategy=0):
    """Simulate a complete FA Cup tournament from Round 4 to Final"""
    # Round 4 - handle known winners
    round4_winners = []

    for home, away in FA_CUP_MATCHES:
        # Check if either team is a known winner
        if home in knownwinners:
            _, _, winner, _ = simulate_fa_cup_match(home, away, rng, fixed_winner=home)
        elif away in knownwinners:
            _, _, winner, _ = simulate_fa_cup_match(home, away, rng, fixed_winner=away)
        else:
            _, _, winner, _ = simulate_fa_cup_match(home, away, rng)
        round4_winners.append(winner)

    # Round 5 - use pairing strategy
    round5_matches = generate_pairings(round4_winners, pairing_strategy, rng)
    round5_winners = []
    for home, away in round5_matches:
        _, _, winner, _ = simulate_fa_cup_match(home, away, rng)
        round5_winners.append(winner)

    # Quarter-finals - use pairing strategy
    qf_matches = generate_pairings(round5_winners, pairing_strategy + 1, rng)
    qf_winners = []
    for home, away in qf_matches:
        _, _, winner, _ = simulate_fa_cup_match(home, away, rng)
        qf_winners.append(winner)

    # Semi-finals - use pairing strategy
    sf_matches = generate_pairings(qf_winners, pairing_strategy + 2, rng)
    sf_winners = []
    for home, away in sf_matches:
        _, _, winner, _ = simulate_fa_cup_match(home, away, rng)
        sf_winners.append(winner)

    # Final - 1 match
    if len(sf_winners) < 2:
        # If we don't have 2 semifinal winners, this shouldn't happen, but handle it
        available_teams = [team for team in FA_CUP_TEAMS]
        if len(sf_winners) == 1:
            sf_winners.append(rng.choice([t for t in available_teams if t != sf_winners[0]]))
        else:
            sf_winners = rng.choice(available_teams, 2, replace=False).tolist()

    final_match = (sf_winners[0], sf_winners[1])
    _, _, winner, _ = simulate_fa_cup_match(final_match[0], final_match[1], rng)

    return winner

def run_fa_cup_simulation(num_simulations=5000, random_seed=42):
    """Run Monte Carlo simulation of the complete FA Cup tournament with all pairing strategies"""
    rng = np.random.default_rng(random_seed)

    # Track only teams that actually advance to Round 5 (Round 4 winners)
    # First, get all Round 4 winners (both known and potential)
    round4_winners = set()
    for home, away in FA_CUP_MATCHES:
        if home in knownwinners:
            round4_winners.add(home)
        elif away in knownwinners:
            round4_winners.add(away)
        else:
            # These matches are simulated, so both teams could advance
            round4_winners.add(home)
            round4_winners.add(away)

    # Track only final winners among teams that could still win
    final_winners = {team: 0 for team in round4_winners}

    print(f"Running {num_simulations} FA Cup tournament simulations with all pairing strategies...")
    for sim in tqdm(range(num_simulations), desc="Simulating"):
        # Cycle through pairing strategies (6 strategies total)
        pairing_strategy = sim % 6
        winner = simulate_full_fa_cup_tournament(rng, pairing_strategy=pairing_strategy)
        if winner in final_winners:
            final_winners[winner] += 1
        else:
            final_winners[winner] = 1  # Handle teams not in initial list

    return final_winners

def print_fa_cup_win_percentages(final_winners, num_simulations):
    """Print FA Cup win percentage table for teams still in contention"""
    console = Console()

    console.print("\n[bold green]FA CUP WIN PERCENTAGES[/bold green]")
    console.print(f"Based on {num_simulations} simulations with all possible pairing strategies")
    console.print(f"Showing only teams that can still advance past Round 4\n")

    # Only show teams that are still mathematically in contention (Round 4 participants)
    results = []
    for team in final_winners.keys():
        wins = final_winners[team]
        probability = (wins / num_simulations) * 100
        results.append({
            'Team': team,
            'Wins': wins,
            'Probability': probability
        })

    # Sort by probability (descending)
    results.sort(key=lambda x: x['Probability'], reverse=True)

    # Create comprehensive table
    table = Table(box=box.SQUARE, border_style="blue", title="FA Cup Championship Probabilities")
    table.add_column("Rank", style="dim", header_style="bold dim", justify="right", width=6)
    table.add_column("Team", style="cyan", header_style="bold cyan")
    table.add_column("Wins", style="green", header_style="bold green", justify="right", width=8)
    table.add_column("Win %", style="yellow", header_style="bold yellow", justify="right", width=10)

    # Add all teams to table
    for rank, result in enumerate(results, 1):
        table.add_row(
            str(rank),
            result['Team'],
            str(int(result['Wins'])),
            f"{result['Probability']:.2f}%"
        )

    console.print(table)

def main():
    parser = argparse.ArgumentParser(description='FA Cup Tournament Simulation - All Pairing Strategies')
    parser.add_argument('--nsims', type=int, default=5000, help='Number of simulations to run (default 5000)')
    parser.add_argument('--seed', type=int, default=42, help='Random seed')

    args = parser.parse_args()

    console = Console()
    console.print("[bold green]FA CUP TOURNAMENT SIMULATION[/bold green]")
    console.print("[bold yellow]Running all rounds with all possible pairing strategies[/bold yellow]")
    console.print("[bold yellow]Using known winners for Round 4 matches[/bold yellow]\n")

    final_winners = run_fa_cup_simulation(num_simulations=args.nsims, random_seed=args.seed)
    print_fa_cup_win_percentages(final_winners, args.nsims)

if __name__ == "__main__":
    main()