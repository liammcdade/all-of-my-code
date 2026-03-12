"""
Farmer's League Index Calculator

Calculates the "Farmer's League Index" which measures how dominant a league is.
Formula: x = (38/games_in_season) × (title_wins_ratio) × sqrt(winning_margin + cbrt(avg_gd))

Where:
- games_in_season: Number of games per team in a season (default 38 for Premier League)
- title_wins_ratio: Ratio of title wins of the most successful team (wins / total seasons)
- winning_margin: Average points difference between 1st and 2nd place
- avg_gd: Average goal difference of winning teams
"""

import math
from typing import Dict, List, Tuple
from collections import Counter


def calculate_farmers_league_index(
    games_per_season: int,
    title_wins: Dict[str, int],
    winning_margins: List[float],
    winning_goal_differences: List[float]
) -> float:
    """
    Calculate the Farmer's League Index.
    
    Args:
        games_per_season: Number of games each team plays per season
        title_wins: Dictionary mapping team names to number of title wins
        winning_margins: List of points differences between 1st and 2nd place for each season
        winning_goal_differences: List of goal differences for winning teams each season
    
    Returns:
        The Farmer's League Index value
    """
    # Calculate total number of seasons
    total_seasons = sum(title_wins.values())
    
    if total_seasons == 0:
        raise ValueError("No title wins data provided")
    
    # Find the most successful team
    most_successful_team = max(title_wins.items(), key=lambda x: x[1])
    most_wins = most_successful_team[1]
    
    # Calculate ratio of title wins of most successful team
    title_wins_ratio = most_wins / total_seasons
    
    # Calculate average winning margin
    if not winning_margins:
        raise ValueError("No winning margins data provided")
    avg_winning_margin = sum(winning_margins) / len(winning_margins)
    
    # Calculate average goal difference of winning teams
    if not winning_goal_differences:
        raise ValueError("No goal difference data provided")
    avg_gd = sum(winning_goal_differences) / len(winning_goal_differences)
    
    # Apply the formula: x = (38/games_in_season) × ratio × sqrt(margin + cbrt(gd))
    games_factor = 38 / games_per_season
    cube_root_gd = math.pow(abs(avg_gd), 1/3) if avg_gd >= 0 else -math.pow(abs(avg_gd), 1/3)
    sqrt_component = math.sqrt(avg_winning_margin + cube_root_gd)
    
    farmers_index = games_factor * title_wins_ratio * sqrt_component
    
    return farmers_index


def calculate_from_season_results(
    games_per_season: int,
    season_results: List[Tuple[str, float, float]]
) -> float:
    """
    Calculate Farmer's League Index from season-by-season results.
    
    Args:
        games_per_season: Number of games each team plays per season
        season_results: List of tuples (winner, points_margin, goal_difference) for each season
    
    Returns:
        The Farmer's League Index value
    """
    # Count title wins
    title_wins = Counter([result[0] for result in season_results])
    
    # Extract winning margins and goal differences
    winning_margins = [result[1] for result in season_results]
    winning_goal_differences = [result[2] for result in season_results]
    
    return calculate_farmers_league_index(
        games_per_season,
        dict(title_wins),
        winning_margins,
        winning_goal_differences
    )


# Example: Premier League data (1992-93 to 2023-24)
# Format: (winner, points_margin, goal_difference)
PREMIER_LEAGUE_EXAMPLE = [
    ("Manchester United", 10, 36),  # 1992-93
    ("Manchester United", 8, 40),  # 1993-94
    ("Blackburn Rovers", 1, 41),    # 1994-95
    ("Manchester United", 4, 38),   # 1995-96
    ("Manchester United", 7, 32),   # 1996-97
    ("Arsenal", 1, 35),             # 1997-98
    ("Manchester United", 1, 43),   # 1998-99
    ("Manchester United", 18, 52), # 1999-00
    ("Manchester United", 10, 41), # 2000-01
    ("Arsenal", 7, 43),             # 2001-02
    ("Manchester United", 5, 40),  # 2002-03
    ("Arsenal", 11, 47),            # 2003-04
    ("Chelsea", 12, 57),            # 2004-05
    ("Chelsea", 8, 50),             # 2005-06
    ("Manchester United", 6, 56),   # 2006-07
    ("Manchester United", 2, 58),  # 2007-08
    ("Manchester United", 4, 44),  # 2008-09
    ("Chelsea", 1, 71),             # 2009-10
    ("Manchester United", 9, 41),  # 2010-11
    ("Manchester City", 0, 64),     # 2011-12 (goal difference)
    ("Manchester United", 11, 43), # 2012-13
    ("Manchester City", 2, 65),     # 2013-14
    ("Chelsea", 8, 41),             # 2014-15
    ("Leicester City", 10, 32),     # 2015-16
    ("Chelsea", 15, 52),            # 2016-17
    ("Manchester City", 19, 79),    # 2017-18
    ("Manchester City", 1, 72),     # 2018-19
    ("Liverpool", 18, 52),          # 2019-20
    ("Manchester City", 12, 51),    # 2020-21
    ("Manchester City", 1, 73),     # 2021-22
    ("Manchester City", 5, 61),     # 2022-23
    ("Manchester City", 2, 62),     # 2023-24
]


if __name__ == "__main__":
    # Calculate for Premier League
    games_per_season = 38
    
    print("=" * 60)
    print("Farmer's League Index Calculator")
    print("=" * 60)
    print()
    
    # Calculate using example data
    index = calculate_from_season_results(games_per_season, PREMIER_LEAGUE_EXAMPLE)
    
    # Display results
    title_wins = Counter([result[0] for result in PREMIER_LEAGUE_EXAMPLE])
    most_successful = max(title_wins.items(), key=lambda x: x[1])
    total_seasons = len(PREMIER_LEAGUE_EXAMPLE)
    avg_margin = sum([r[1] for r in PREMIER_LEAGUE_EXAMPLE]) / len(PREMIER_LEAGUE_EXAMPLE)
    avg_gd = sum([r[2] for r in PREMIER_LEAGUE_EXAMPLE]) / len(PREMIER_LEAGUE_EXAMPLE)
    
    print(f"League: Premier League")
    print(f"Games per season: {games_per_season}")
    print(f"Total seasons analyzed: {total_seasons}")
    print(f"Most successful team: {most_successful[0]} ({most_successful[1]} titles)")
    print(f"Title wins ratio: {most_successful[1]/total_seasons:.3f}")
    print(f"Average winning margin: {avg_margin:.2f} points")
    print(f"Average goal difference (winners): {avg_gd:.2f}")
    print()
    print(f"Farmer's League Index: {index:.4f}")
    print("=" * 60)
    print()
    print("Interpretation:")
    print("- Higher values indicate a more 'farmers league' (dominant by one team)")
    print("- Lower values indicate more competitive/balanced leagues")
    print()
    
    # Show top title winners
    print("Top Title Winners:")
    for team, wins in title_wins.most_common(5):
        print(f"  {team}: {wins} titles ({wins/total_seasons*100:.1f}%)")
