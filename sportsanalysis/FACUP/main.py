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

# FA Cup Semi-finalists (as of April 2026) - Southampton eliminated by Man City
SF_TEAMS = [
    "Chelsea", "Leeds United", "Manchester City"
]

# Basic Elo ratings for FA Cup semi-finalists (updated from 25-26 season)
elo_ratings = {
    "Arsenal": 2044,
    "Chelsea": 1840,
    "Liverpool": 1926,
    "Manchester City": 1969,
    "Southampton": 1624,
    "West Ham United": 1759,
    "Port Vale": 1410,
    "Leeds United": 1792	
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
        sorted_teams = sorted(teams, key=lambda x: elo_ratings.get(x, 1800), reverse=True)
        matches = []
        for i in range(len(sorted_teams) // 2):
            matches.append((sorted_teams[i], sorted_teams[-(i+1)]))
        return matches
    
    elif strategy == 1:  # Reverse seeded (best vs 2nd best, 3rd vs 4th, etc.)
        sorted_teams = sorted(teams, key=lambda x: elo_ratings.get(x, 1800), reverse=True)
        matches = []
        for i in range(0, len(sorted_teams), 2):
            matches.append((sorted_teams[i], sorted_teams[i+1]))
        return matches
    
    elif strategy == 2:  # Balanced brackets (split into two halves, pair across halves)
        sorted_teams = sorted(teams, key=lambda x: elo_ratings.get(x, 1800), reverse=True)
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
        sorted_teams = sorted(teams, key=lambda x: elo_ratings.get(x, 1800), reverse=True)
        matches = []
        for i in range(len(sorted_teams) // 2):
            matches.append((sorted_teams[i], sorted_teams[i + len(sorted_teams) // 2]))
        return matches
    
    else:  # strategy == 5: Random with slight seeding bias
        sorted_teams = sorted(teams, key=lambda x: elo_ratings.get(x, 1800), reverse=True)
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

    home_elo = elo_ratings.get(home_team, 1800) + home_adv
    away_elo = elo_ratings.get(away_team, 1800)

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
    """Simulate a complete FA Cup tournament from Semi-finals to Final"""
    teams = SF_TEAMS.copy()

    if len(teams) == 3:
        # Man City already advanced, remaining semi-final
        remaining = [t for t in teams if t != "Manchester City"]
        sf_match = (remaining[0], remaining[1])
        _, _, sf_winner, _ = simulate_fa_cup_match(sf_match[0], sf_match[1], rng)
        sf_winners = [sf_winner, "Manchester City"]

        # Final
        final_match = (sf_winners[0], sf_winners[1])
        _, _, winner, _ = simulate_fa_cup_match(final_match[0], final_match[1], rng)
    else:
        # Standard 4-team simulation
        # Semi-finals using pairing strategy
        sf_matches = generate_pairings(teams, pairing_strategy, rng)
        sf_winners = []
        for home, away in sf_matches:
            _, _, winner, _ = simulate_fa_cup_match(home, away, rng)
            sf_winners.append(winner)

        # Final
        final_match = (sf_winners[0], sf_winners[1])
        _, _, winner, _ = simulate_fa_cup_match(final_match[0], final_match[1], rng)

    return winner, sf_winners

def run_fa_cup_simulation(num_simulations=5000, random_seed=42):
    """Run Monte Carlo simulation of the complete FA Cup tournament with all pairing strategies"""
    rng = np.random.default_rng(random_seed)

    # Track championship wins, final advancement, and final matchups
    championship = {team: 0 for team in SF_TEAMS}
    final_advance = {team: 0 for team in SF_TEAMS}
    final_matchups = {}

    print(f"Running {num_simulations} FA Cup tournament simulations with all pairing strategies...")
    for sim in tqdm(range(num_simulations), desc="Simulating"):
        # Cycle through pairing strategies (6 strategies total)
        pairing_strategy = sim % 6
        winner, sf_winners = simulate_full_fa_cup_tournament(rng, pairing_strategy=pairing_strategy)
        for team in sf_winners:
            final_advance[team] += 1
        championship[winner] += 1
        finalists = tuple(sorted(sf_winners))
        if finalists not in final_matchups:
            final_matchups[finalists] = 0
        final_matchups[finalists] += 1

    return championship, final_advance, final_matchups

def print_fa_cup_win_percentages(championship, final_advance, final_matchups, num_simulations):
    """Print FA Cup win percentage table for teams still in contention"""
    console = Console()

    console.print("\n[bold green]FA CUP ADVANCEMENT PROBABILITIES FROM SEMI-FINALS[/bold green]")
    console.print(f"Based on {num_simulations} simulations with all possible pairing strategies")
    console.print(f"Showing semi-finalists\n")

    # Final advancement
    final_results = []
    for team in final_advance.keys():
        advances = final_advance[team]
        probability = (advances / num_simulations) * 100
        final_results.append({
            'Team': team,
            'Advances': advances,
            'Probability': probability
        })

    final_results.sort(key=lambda x: x['Probability'], reverse=True)

    final_table = Table(box=box.SQUARE, border_style="blue", title="Final Advancement Probabilities")
    final_table.add_column("Rank", style="dim", header_style="bold dim", justify="right", width=6)
    final_table.add_column("Team", style="cyan", header_style="bold cyan")
    final_table.add_column("Advances", style="green", header_style="bold green", justify="right", width=8)
    final_table.add_column("Advance %", style="yellow", header_style="bold yellow", justify="right", width=10)

    for rank, result in enumerate(final_results, 1):
        final_table.add_row(
            str(rank),
            result['Team'],
            str(int(result['Advances'])),
            f"{result['Probability']:.2f}%"
        )

    console.print(final_table)

    # Final matchups
    matchup_results = []
    for matchup, count in final_matchups.items():
        probability = (count / num_simulations) * 100
        matchup_results.append({
            'Matchup': f"{matchup[0]} vs {matchup[1]}",
            'Occurrences': count,
            'Probability': probability
        })

    matchup_results.sort(key=lambda x: x['Probability'], reverse=True)

    matchup_table = Table(box=box.SQUARE, border_style="blue", title="Final Matchup Probabilities")
    matchup_table.add_column("Rank", style="dim", header_style="bold dim", justify="right", width=6)
    matchup_table.add_column("Matchup", style="cyan", header_style="bold cyan")
    matchup_table.add_column("Occurrences", style="green", header_style="bold green", justify="right", width=12)
    matchup_table.add_column("Matchup %", style="yellow", header_style="bold yellow", justify="right", width=10)

    for rank, result in enumerate(matchup_results, 1):
        matchup_table.add_row(
            str(rank),
            result['Matchup'],
            str(int(result['Occurrences'])),
            f"{result['Probability']:.2f}%"
        )

    console.print(matchup_table)

    # Championship
    results = []
    for team in championship.keys():
        wins = championship[team]
        probability = (wins / num_simulations) * 100
        results.append({
            'Team': team,
            'Wins': wins,
            'Probability': probability
        })

    results.sort(key=lambda x: x['Probability'], reverse=True)

    table = Table(box=box.SQUARE, border_style="blue", title="FA Cup Championship Probabilities")
    table.add_column("Rank", style="dim", header_style="bold dim", justify="right", width=6)
    table.add_column("Team", style="cyan", header_style="bold cyan")
    table.add_column("Wins", style="green", header_style="bold green", justify="right", width=8)
    table.add_column("Win %", style="yellow", header_style="bold yellow", justify="right", width=10)

    for rank, result in enumerate(results, 1):
        table.add_row(
            str(rank),
            result['Team'],
            str(int(result['Wins'])),
            f"{result['Probability']:.2f}%"
        )

    console.print(table)

def main():
    parser = argparse.ArgumentParser(description='FA Cup Tournament Simulation from Semi-finals - All Pairing Strategies')
    parser.add_argument('--nsims', type=int, default=5000, help='Number of simulations to run (default 5000)')
    parser.add_argument('--seed', type=int, default=42, help='Random seed')

    args = parser.parse_args()

    console = Console()
    console.print("[bold green]FA CUP TOURNAMENT SIMULATION FROM SEMI-FINALS[/bold green]")
    console.print("[bold yellow]Using pairing strategies for semi-finals and final[/bold yellow]\n")

    championship, final_advance, final_matchups = run_fa_cup_simulation(num_simulations=args.nsims, random_seed=args.seed)
    print_fa_cup_win_percentages(championship, final_advance, final_matchups, args.nsims)

if __name__ == "__main__":
    main()