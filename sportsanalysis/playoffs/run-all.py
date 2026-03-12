"""
EFL Play-Off Finals Simulation

This script simulates all three EFL Play-Off Finals using Poisson distribution
for goal scoring based on team statistics from the regular season.
"""

import numpy as np
from tqdm import tqdm
from typing import Dict, List, Tuple


# Configuration
SIMULATION_RUNS = 100000


# Team statistics for all three finals
TEAM_STATS = {
    # Championship Play-Off Final
    "Sheffield United": {"Pld": 46, "GF": 63, "GA": 36, "Pts": 90},
    "Sunderland": {"Pld": 46, "GF": 58, "GA": 44, "Pts": 76},
    
    # League One Play-Off Final
    "Charlton Athletic": {"Pld": 46, "GF": 67, "GA": 43, "Pts": 85},
    "Leyton Orient": {"Pld": 46, "GF": 72, "GA": 48, "Pts": 78},
    
    # League Two Play-Off Final
    "Walsall": {"Pld": 46, "GF": 75, "GA": 54, "Pts": 77},
    "AFC Wimbledon": {"Pld": 46, "GF": 56, "GA": 35, "Pts": 73},
}


def calculate_average_goals(team_stats: Dict[str, int]) -> Tuple[float, float]:
    """Calculate average goals for and against for a team."""
    avg_gf = team_stats["GF"] / team_stats["Pld"]
    avg_ga = team_stats["GA"] / team_stats["Pld"]
    return avg_gf, avg_ga


def simulate_goals_for_team(team_avg_gf: float, opponent_avg_ga: float) -> int:
    """
    Simulate goals scored by a team using Poisson distribution.
    
    Args:
        team_avg_gf: Team's average goals for per game
        opponent_avg_ga: Opponent's average goals against per game
    
    Returns:
        Simulated number of goals scored
    """
    lambda_val = max(0.1, (team_avg_gf + opponent_avg_ga) / 2)
    return np.random.poisson(lambda_val)


def run_match_simulation(team1_name: str, team2_name: str, 
                        team_stats: Dict[str, Dict[str, int]], 
                        num_runs: int) -> Dict[str, any]:
    """
    Run a single match simulation and return results.
    
    Args:
        team1_name: Name of first team
        team2_name: Name of second team
        team_stats: Dictionary containing team statistics
        num_runs: Number of simulations to run
    
    Returns:
        Dictionary containing simulation results
    """
    team1_stats = team_stats[team1_name]
    team2_stats = team_stats[team2_name]
    
    # Calculate average goals for/against
    team1_avg_gf, team1_avg_ga = calculate_average_goals(team1_stats)
    team2_avg_gf, team2_avg_ga = calculate_average_goals(team2_stats)
    
    # Initialize counters
    team1_wins = 0
    team2_wins = 0
    draws = 0
    
    # Run simulations
    for _ in tqdm(range(num_runs), desc=f"Simulating {team1_name} vs {team2_name}"):
        team1_goals = simulate_goals_for_team(team1_avg_gf, team2_avg_ga)
        team2_goals = simulate_goals_for_team(team2_avg_gf, team1_avg_ga)
        
        if team1_goals > team2_goals:
            team1_wins += 1
        elif team2_goals > team1_goals:
            team2_wins += 1
        else:
            draws += 1
    
    # Calculate percentages
    team1_win_percent = (team1_wins / num_runs) * 100
    team2_win_percent = (team2_wins / num_runs) * 100
    draw_percent = (draws / num_runs) * 100
    
    return {
        "team1_name": team1_name,
        "team2_name": team2_name,
        "team1_wins": team1_wins,
        "team2_wins": team2_wins,
        "draws": draws,
        "team1_win_percent": team1_win_percent,
        "team2_win_percent": team2_win_percent,
        "draw_percent": draw_percent,
        "total_runs": num_runs,
    }


def print_match_results(results: Dict[str, any], final_type: str) -> None:
    """Print formatted results for a single match."""
    print(f"--- {final_type} Play-Off Final: {results['team1_name']} vs {results['team2_name']} ---")
    print(f"Total simulations: {results['total_runs']}\n")
    
    print(f"{results['team1_name']} wins: {results['team1_wins']} ({results['team1_win_percent']:.2f}%)")
    print(f"{results['team2_name']} wins: {results['team2_wins']} ({results['team2_win_percent']:.2f}%)")
    print(f"Draws (after 90 mins): {results['draws']} ({results['draw_percent']:.2f}%)")
    print()


def generate_summary_report(results: List[Dict[str, any]]) -> str:
    """Generate a comprehensive summary report."""
    report_lines = [
        "=" * 80,
        "=== PLAY-OFF FINALS SIMULATION REPORT ===",
        "=" * 80,
        f"Date of Report: Friday, May 23, 2025\n",
        "This report summarizes the results of 100,000 simulations for each of the upcoming EFL Play-Off Finals, based on the teams' full regular season statistics.\n"
    ]
    
    # Championship Summary
    championship_results = results[0]
    championship_winner = (
        championship_results["team1_name"]
        if championship_results["team1_win_percent"] > championship_results["team2_win_percent"]
        else championship_results["team2_name"]
    )
    championship_likelihood = max(
        championship_results["team1_win_percent"], 
        championship_results["team2_win_percent"]
    )
    
    report_lines.extend([
        f"**Championship Play-Off Final: {championship_results['team1_name']} vs {championship_results['team2_name']}**",
        f"- Based on stats, {championship_winner} has the highest likelihood of winning in 90 minutes ({championship_likelihood:.2f}%).",
        f"- There is a {championship_results['draw_percent']:.2f}% chance this high-stakes match will go to extra time.",
        "-" * 40
    ])
    
    # League One Summary
    league_one_results = results[1]
    league_one_winner = (
        league_one_results["team1_name"]
        if league_one_results["team1_win_percent"] > league_one_results["team2_win_percent"]
        else league_one_results["team2_name"]
    )
    league_one_likelihood = max(
        league_one_results["team1_win_percent"], 
        league_one_results["team2_win_percent"]
    )
    
    report_lines.extend([
        f"**League One Play-Off Final: {league_one_results['team1_name']} vs {league_one_results['team2_name']}**",
        f"- The simulation suggests {league_one_winner} is more likely to secure victory within 90 minutes ({league_one_likelihood:.2f}%).",
        f"- A draw after 90 minutes, leading to extra time, occurs in {league_one_results['draw_percent']:.2f}% of simulations.",
        "-" * 40
    ])
    
    # League Two Summary
    league_two_results = results[2]
    league_two_winner = (
        league_two_results["team1_name"]
        if league_two_results["team1_win_percent"] > league_two_results["team2_win_percent"]
        else league_two_results["team2_name"]
    )
    league_two_likelihood = max(
        league_two_results["team1_win_percent"], 
        league_two_results["team2_win_percent"]
    )
    
    report_lines.extend([
        f"**League Two Play-Off Final: {league_two_results['team1_name']} vs {league_two_results['team2_name']}**",
        f"- {league_two_winner} shows a statistical edge to win in regulation time ({league_two_likelihood:.2f}%).",
        f"- There's a {league_two_results['draw_percent']:.2f}% probability of this match proceeding to extra time.",
        "-" * 40
    ])
    
    return "\n".join(report_lines)


def main() -> None:
    """Main function to run all play-off final simulations."""
    print("Starting Play-Off Finals Simulations...\n")
    
    # Define the matches to simulate
    matches = [
        ("Sheffield United", "Sunderland", "Championship"),
        ("Charlton Athletic", "Leyton Orient", "League One"),
        ("Walsall", "AFC Wimbledon", "League Two")
    ]
    
    all_results = []
    
    # Run simulations for each match
    for team1, team2, final_type in matches:
        results = run_match_simulation(team1, team2, TEAM_STATS, SIMULATION_RUNS)
        all_results.append(results)
    
    # Display all results
    print("\n" + "=" * 80)
    print("=== ALL EFL PLAY-OFF FINAL SIMULATION RESULTS (90 MINUTES) ===")
    print("=" * 80 + "\n")
    
    for results, (_, _, final_type) in zip(all_results, matches):
        print_match_results(results, final_type)
    
    # Generate and display summary report
    summary_report = generate_summary_report(all_results)
    print(summary_report)


if __name__ == "__main__":
    main()
