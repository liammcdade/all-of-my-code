"""
2025-26 Carabao Cup (EFL Cup) Simulation
=========================================
Simulates the remaining games in the Carabao Cup based on the state as of February 2, 2026.

Semi-finals (second leg):
- Arsenal vs Chelsea (Arsenal home) - Arsenal leads 3-2 on aggregate
- Manchester City vs Newcastle (Man City home) -2-0 on Man City leads  aggregate

Final: March 22, 2026 at Wembley Stadium

Team Elo Ratings:
- Arsenal: 2377
- Newcastle: 2148
- Manchester City: 2237
- Chelsea: 2216
"""

import random
import math
from collections import defaultdict
from dataclasses import dataclass
from typing import Optional


# Team data with Elo ratings
TEAMS = {
    "Arsenal": {"elo": 2377},
    "Chelsea": {"elo": 2216},
    "Manchester City": {"elo": 2237},
    "Newcastle United": {"elo": 2148},
}


# Current semi-final state (first leg results)
SEMIS = {
    "semi1": {
        "team1": "Chelsea",
        "team2": "Arsenal",
        "score1": 2,
        "score2": 3,
        "first_leg_home": "Chelsea",
        "second_leg_home": "Arsenal",
    },
    "semi2": {
        "team1": "Newcastle United",
        "team2": "Manchester City",
        "score1": 0,
        "score2": 2,
        "first_leg_home": "Newcastle United",
        "second_leg_home": "Manchester City",
    },
}


@dataclass
class Team:
    """Represents a team with its properties."""
    name: str
    elo: int


@dataclass
class Match:
    """Represents a match between two teams."""
    home_team: Team
    away_team: Team
    home_goals: int = 0
    away_goals: int = 0
    is_leg: bool = False
    aggregate_home_goals: int = 0
    aggregate_away_goals: int = 0

    def __str__(self):
        return f"{self.home_team.name} {self.home_goals} - {self.away_goals} {self.away_team.name}"


def elo_to_strength(elo: int) -> float:
    """Convert Elo rating to a strength value for probability calculations."""
    return 10 ** (elo / 400)


def calculate_win_probability(home_elo: int, away_elo: int, home_advantage: int = 100) -> tuple:
    """
    Calculate win probabilities based on Elo ratings.
    Returns (home_win, draw, away_win) probabilities.
    Home advantage is added as Elo points.
    """
    home_strength = elo_to_strength(home_elo + home_advantage)
    away_strength = elo_to_strength(away_elo)
    
    total = home_strength + away_strength + 1  # +1 to avoid division issues
    
    # Base probabilities (simplified)
    home_p = home_strength / total
    away_p = away_strength / total
    draw_p = 1 - home_p - away_p
    
    # Adjust for more realistic draw probability (around 25-30% in football)
    draw_p = max(0.15, min(0.35, draw_p))
    remaining = 1 - draw_p
    home_p = home_p / (home_p + away_p) * remaining
    away_p = away_p / (home_p + away_p) * remaining
    
    return (home_p, draw_p, away_p)


def poisson_goals(lambda_param: float) -> int:
    """Generate goals using Poisson distribution."""
    return min(10, int(-math.log(1 - random.random()) / (1 / lambda_param) + 0.5))


def calculate_lambda(elo_diff: int, is_home: bool, home_advantage: int = 100) -> float:
    """
    Calculate expected goals (lambda) for Poisson distribution.
    is_home: True if team is playing at home
    """
    if is_home:
        adjusted_elo_diff = elo_diff + home_advantage
    else:
        adjusted_elo_diff = elo_diff - home_advantage
    
    # Base goals around 1.5, adjust based on Elo difference
    # Each 100 Elo points is roughly 0.3 expected goals difference
    base_goals = 1.5
    elo_factor = adjusted_elo_diff / 400 * 1.2
    
    lambda_param = base_goals + elo_factor
    return max(0.2, min(4.5, lambda_param))  # Clamp between 0.2 and 4.5


def simulate_match(home_team: Team, away_team: Team, 
                   aggregate_home: int = 0, aggregate_away: int = 0,
                   is_second_leg: bool = False) -> tuple:
    """
    Simulate a single match.
    
    Returns:
        tuple: (winner, match_result, aggregate_result)
        - winner: Team object or None (for draw)
        - match_result: str describing the match outcome
        - aggregate_result: str describing aggregate outcome if applicable
    """
    # Calculate expected goals for each team
    elo_diff = home_team.elo - away_team.elo
    home_lambda = calculate_lambda(elo_diff, is_home=True)
    away_lambda = calculate_lambda(elo_diff, is_home=False)
    
    # Simulate goals
    home_goals = poisson_goals(home_lambda)
    away_goals = poisson_goals(away_lambda)
    
    # Handle aggregate if it's a second leg
    if is_second_leg:
        total_home = aggregate_home + home_goals
        total_away = aggregate_away + away_goals
        
        if total_home > total_away:
            winner = home_team
            aggregate_result = f"Aggregate: {total_home}-{total_away}"
        elif total_away > total_home:
            winner = away_team
            aggregate_result = f"Aggregate: {total_home}-{total_away}"
        else:
            # Aggregate tied - simulate extra time and penalties
            winner, extra_result = simulate_extra_time_penalties(home_team, away_team)
            aggregate_result = f"Aggregate: {aggregate_home + home_goals}-{aggregate_away + away_goals} (AET/Pens: {extra_result})"
    else:
        total_home = home_goals
        total_away = away_goals
        
        if home_goals > away_goals:
            winner = home_team
        elif away_goals > home_goals:
            winner = away_team
        else:
            winner = None  # Draw
        
        aggregate_result = None
    
    match_result = f"{home_goals}-{away_goals}"
    return winner, match_result, aggregate_result


def simulate_extra_time_penalties(home_team: Team, away_team: Team) -> tuple:
    """
    Simulate extra time and penalties when aggregate is tied.
    
    Returns:
        tuple: (winner_team, result_string)
    """
    # Extra time: 30 minutes, reduced scoring likelihood
    home_goals = poisson_goals(0.3)  # Lower expected goals in extra time
    away_goals = poisson_goals(0.3)
    
    if home_goals > away_goals:
        return home_team, f"Extra time: {home_goals}-{away_goals}"
    elif away_goals > home_goals:
        return away_team, f"Extra time: {home_goals}-{away_goals}"
    else:
        # Penalties - 50/50 with slight home advantage
        home_p, _, away_p = calculate_win_probability(home_team.elo, away_team.elo, home_advantage=0)
        if random.random() < home_p / (home_p + away_p):
            return home_team, f"Penalties: {home_team.name} wins"
        else:
            return away_team, f"Penalties: {away_team.name} wins"


def simulate_semi_final(semi_info: dict, num_simulations: int = 1) -> dict:
    """
    Simulate a semi-final second leg.
    
    Args:
        semi_info: Dictionary with semi-final information
        num_simulations: Number of simulations to run
    
    Returns:
        dict: Results including winners and match details
    """
    team1 = Team(semi_info["team1"], TEAMS[semi_info["team1"]]["elo"])
    team2 = Team(semi_info["team2"], TEAMS[semi_info["team2"]]["elo"])
    
    # Determine which team is home in second leg
    second_leg_home = semi_info["second_leg_home"]
    if second_leg_home == team1.name:
        home_team = team1
        away_team = team2
        # First leg was team1 home, so team2 (away) scored semi_info["score2"]
        # Team1 (home) scored semi_info["score1"]
        aggregate_home = semi_info["score1"]
        aggregate_away = semi_info["score2"]
    else:
        home_team = team2
        away_team = team1
        aggregate_home = semi_info["score2"]
        aggregate_away = semi_info["score1"]
    
    results = {
        "home_team": home_team.name,
        "away_team": away_team.name,
        "first_leg_score": f"{semi_info['score1']}-{semi_info['score2']}",
        "first_leg_home": semi_info["first_leg_home"],
        "winners": defaultdict(int),
        "match_results": defaultdict(int),
        "aggregate_results": defaultdict(int),
    }
    
    for _ in range(num_simulations):
        winner, match_result, aggregate_result = simulate_match(
            home_team, away_team,
            aggregate_home, aggregate_away,
            is_second_leg=True
        )
        
        results["winners"][winner.name if winner else "Draw"] += 1
        results["match_results"][match_result] += 1
        if aggregate_result:
            results["aggregate_results"][aggregate_result] += 1
    
    return results


def simulate_final(team1: Team, team2: Team, neutral_venue: bool = True) -> tuple:
    """
    Simulate the final (single match at Wembley).
    
    Args:
        team1: First team
        team2: Second team
        neutral_venue: If True, no home advantage; if False, team1 has home advantage
    
    Returns:
        tuple: (winner, match_result, extra_info)
    """
    # Wembley is neutral venue, but we can give slight advantage to "designated home" team
    home_advantage = 50 if not neutral_venue else 30
    
    # Randomize home/away for simulation purposes
    if random.random() < 0.5:
        home_team = team1
        away_team = team2
    else:
        home_team = team2
        away_team = team1
    
    # Simulate goals using Elo-based probabilities
    elo_diff = home_team.elo - away_team.elo
    home_lambda = calculate_lambda(elo_diff, is_home=True, home_advantage=home_advantage)
    away_lambda = calculate_lambda(elo_diff, is_home=False, home_advantage=home_advantage)
    
    home_goals = poisson_goals(home_lambda)
    away_goals = poisson_goals(away_lambda)
    
    if home_goals > away_goals:
        winner = home_team
        extra_info = None
    elif away_goals > home_goals:
        winner = away_team
        extra_info = None
    else:
        # Draw - simulate extra time and penalties
        winner, extra_info = simulate_extra_time_penalties(home_team, away_team)
    
    match_result = f"{home_goals}-{away_goals}"
    return winner, match_result, extra_info


def run_tournament_simulation(num_simulations: int = 10000) -> dict:
    """
    Run full tournament simulation (both semis + final).
    
    Args:
        num_simulations: Number of Monte Carlo simulations to run
    
    Returns:
        dict: Comprehensive results
    """
    results = {
        "total_simulations": num_simulations,
        "semi_results": {},
        "final_matchups": defaultdict(int),
        "cup_winners": defaultdict(int),
        "path_to_final": defaultdict(lambda: defaultdict(int)),
    }
    
    for sim in range(num_simulations):
        # Create Team objects for each semi
        arsenal = Team("Arsenal", TEAMS["Arsenal"]["elo"])
        chelsea = Team("Chelsea", TEAMS["Chelsea"]["elo"])
        man_city = Team("Manchester City", TEAMS["Manchester City"]["elo"])
        newcastle = Team("Newcastle United", TEAMS["Newcastle United"]["elo"])
        
        # Simulate Semi 1: Arsenal vs Chelsea (Arsenal home, leads 3-2)
        semi1_winner, _, _ = simulate_match(
            arsenal,  # Arsenal home
            chelsea,  # Chelsea away
            aggregate_home=3,  # Arsenal's aggregate goals (home in 2nd leg)
            aggregate_away=2,  # Chelsea's aggregate goals
            is_second_leg=True
        )
        
        # Simulate Semi 2: Man City vs Newcastle (Man City home, leads 2-0)
        semi2_winner, _, _ = simulate_match(
            man_city,  # Man City home
            newcastle,  # Newcastle away
            aggregate_home=2,  # Man City's aggregate goals
            aggregate_away=0,  # Newcastle's aggregate goals
            is_second_leg=True
        )
        
        # If we have valid winners for both semis
        if semi1_winner and semi2_winner:
            # Determine final teams (randomize for neutral venue simulation)
            final_teams = [semi1_winner, semi2_winner]
            random.shuffle(final_teams)
            
            # Simulate final
            final_winner, _, _ = simulate_final(final_teams[0], final_teams[1])
            
            if final_winner:
                # Record results
                matchup = f"{semi1_winner.name} vs {semi2_winner.name}"
                results["final_matchups"][matchup] += 1
                results["cup_winners"][final_winner.name] += 1
                
                # Track paths to final for each semi winner
                results["path_to_final"][semi1_winner.name]["Finalist"] += 1
                results["path_to_final"][semi2_winner.name]["Finalist"] += 1
                results["path_to_final"][final_winner.name]["Winner"] += 1
    
    # Add semi-final statistics
    for semi_key in ["semi1", "semi2"]:
        semi_info = SEMIS[semi_key]
        results["semi_results"][semi_key] = simulate_semi_final(semi_info, 1000)  # Run 1000 for stats
    
    return results


def print_results(results: dict):
    """Print simulation results in a formatted way."""
    print("\n" + "="*70)
    print("2025-26 CARABAO CUP SIMULATION RESULTS")
    print("="*70)
    
    # Semi-final results
    print("\n--- SEMI-FINAL SECOND LEGS ---")
    for semi_key, semi_info in SEMIS.items():
        if semi_key == "semi1":
            print(f"\nSemi 1: {semi_info['team2']} vs {semi_info['team1']}")
            print(f"First Leg: {semi_info['score1']}-{semi_info['score2']} ({semi_info['first_leg_home']} home)")
            print(f"Second Leg: {semi_info['second_leg_home']} home")
        else:
            print(f"\nSemi 2: {semi_info['team2']} vs {semi_info['team1']}")
            print(f"First Leg: {semi_info['score1']}-{semi_info['score2']} ({semi_info['first_leg_home']} home)")
            print(f"Second Leg: {semi_info['second_leg_home']} home")
        
        # Use simulation results for semi
        if "semi_results" in results:
            semi_res = results["semi_results"][semi_key]
            print(f"\nSecond Leg Simulation (1000 runs):")
            for winner, count in sorted(semi_res["winners"].items(), key=lambda x: -x[1]):
                pct = count / 1000 * 100
                print(f"  {winner}: {pct:.1f}%")
    
    # Final matchups
    print("\n" + "-"*50)
    print("\n--- POSSIBLE FINAL MATCHUPS ---")
    total_matchups = sum(results["final_matchups"].values())
    for matchup, count in sorted(results["final_matchups"].items(), key=lambda x: -x[1]):
        pct = count / total_matchups * 100
        print(f"  {matchup}: {pct:.1f}%")
    
    # Cup winners
    print("\n" + "-"*50)
    print("\n--- CUP WIN PROBABILITIES ---")
    total_wins = sum(results["cup_winners"].values())
    for team, count in sorted(results["cup_winners"].items(), key=lambda x: -x[1]):
        pct = count / total_wins * 100
        print(f"  {team}: {pct:.1f}%")
    
    print("\n" + "="*70)
    print(f"Based on {results['total_simulations']} Monte Carlo simulations")
    print("="*70 + "\n")


def enumerate_all_possible_outcomes():
    """
    Enumerate all possible outcomes deterministically (ignoring score specifics).
    
    Since there are 2 semis, each with 2 possible winners, there are 4 possible finals.
    Each final has 2 possible winners, giving 8 total outcomes.
    """
    print("\n" + "="*70)
    print("ALL POSSIBLE OUTCOMES (DETERMINISTIC ENUMERATION)")
    print("="*70)
    
    teams = ["Arsenal", "Chelsea", "Manchester City", "Newcastle United"]
    
    # Semi 1: Arsenal leads 3-2, but Chelsea could still win
    # Semi 2: Man City leads 2-0, Newcastle could still win
    
    print("\nSemi-final 1: Arsenal leads 3-2 on aggregate")
    print("  Possible winners: Arsenal (favored) or Chelsea")
    
    print("\nSemi-final 2: Manchester City leads 2-0 on aggregate")
    print("  Possible winners: Manchester City (favored) or Newcastle United")
    
    print("\n" + "-"*50)
    print("\nPOSSIBLE FINALS:")
    
    finals = [
        ("Arsenal", "Manchester City"),
        ("Arsenal", "Newcastle United"),
        ("Chelsea", "Manchester City"),
        ("Chelsea", "Newcastle United"),
    ]
    
    for team1, team2 in finals:
        print(f"  • {team1} vs {team2}")
    
    print("\n" + "-"*50)
    print("\nALL 8 POSSIBLE CUP WINNERS:")
    
    outcomes = []
    for team1, team2 in finals:
        outcomes.append((team1, team2, team1))
        outcomes.append((team1, team2, team2))
    
    for final, winner in [(f"{t1} vs {t2}", w) for t1, t2, w in outcomes]:
        print(f"  {final} -> {winner} wins")
    
    print("\n" + "="*70)


def main():
    """Main function to run the simulation."""
    print("\n" + "#"*70)
    print("# 2025-26 CARABAO CUP (EFL CUP) SIMULATION")
    print("#"*70)
    
    print("\nCurrent State (February 2, 2026):")
    print("-" * 40)
    print("\nSEMI-FINALS:")
    print("  Semi 1: Chelsea 2-3 Arsenal")
    print("    First leg: Chelsea home (2-1 win)")
    print("    Second leg: Arsenal home, Feb 5")
    print("    Aggregate: Arsenal leads 3-2")
    print()
    print("  Semi 2: Newcastle 0-2 Manchester City")
    print("    First leg: Newcastle home (2-0 loss)")
    print("    Second leg: Man City home, Feb 5")
    print("    Aggregate: Man City leads 2-0")
    
    print("\nFINAL:")
    print("  Date: March 22, 2026")
    print("  Venue: Wembley Stadium")
    
    print("\n" + "-" * 40)
    print("\nTEAM ELO RATINGS:")
    for team, data in sorted(TEAMS.items(), key=lambda x: -x[1]["elo"]):
        print(f"  {team}: {data['elo']}")
    
    # Run deterministic enumeration
    enumerate_all_possible_outcomes()
    
    # Run Monte Carlo simulation
    print("\n\nRunning Monte Carlo simulation...")
    print("(This may take a moment...)\n")
    
    results = run_tournament_simulation(num_simulations=10000)
    print_results(results)
    
    # Additional analysis: Win probability by path
    print("\n--- DETAILED ANALYSIS ---")
    print("\nPath Analysis (how each team could win):")
    
    for team in ["Arsenal", "Chelsea", "Manchester City", "Newcastle United"]:
        if team in results["cup_winners"]:
            wins = results["cup_winners"][team]
            total = sum(results["cup_winners"].values())
            pct = wins / total * 100
            
            # Determine semi opponent
            if team in ["Arsenal", "Chelsea"]:
                semi_opponent = "Chelsea" if team == "Arsenal" else "Arsenal"
                potential_finals = ["Manchester City", "Newcastle United"]
            else:
                semi_opponent = "Newcastle United" if team == "Manchester City" else "Manchester City"
                potential_finals = ["Arsenal", "Chelsea"]
            
            print(f"\n  {team} ({pct:.1f}% chance):")
            print(f"    Must beat {semi_opponent} in semi-final")
            print(f"    Final opponents: {potential_finals[0]} or {potential_finals[1]}")
            
            # Calculate win probability conditional on reaching final
            final_appearances = sum(
                count for matchup, count in results["final_matchups"].items()
                if team in matchup
            )
            if final_appearances > 0:
                conditional_pct = wins / final_appearances * 100
                print(f"    Win probability IF reach final: {conditional_pct:.1f}%")


if __name__ == "__main__":
    main()
