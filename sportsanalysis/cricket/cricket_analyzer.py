import random
from typing import Dict, List, Tuple, Any, Optional
from dataclasses import dataclass, asdict
from datetime import datetime
import statistics
import os
import pandas as pd
try:
    from .plotting_utils import plot_generic_top_n
except ImportError:
    # Fallback for direct execution
    import sys
    from pathlib import Path
    sys.path.append(str(Path(__file__).parent))
    from plotting_utils import plot_generic_top_n


@dataclass
class CricketPlayer:
    """Data class for cricket player statistics."""
    name: str
    team: str
    role: str  # Batsman, Bowler, All-rounder, Wicket-keeper
    batting_style: str  # Right-handed, Left-handed
    bowling_style: str  # Fast, Medium, Spin, etc.
    
    # Batting stats
    matches: int = 0
    innings: int = 0
    runs: int = 0
    highest_score: int = 0
    average: float = 0.0
    strike_rate: float = 0.0
    fifties: int = 0
    hundreds: int = 0
    
    # Bowling stats
    overs: float = 0.0
    wickets: int = 0
    best_bowling: str = "0/0"
    bowling_average: float = 0.0
    economy_rate: float = 0.0
    bowling_strike_rate: float = 0.0
    
    # Fielding stats
    catches: int = 0
    stumpings: int = 0
    
    # Ratings (1-10)
    batting_rating: float = 5.0
    bowling_rating: float = 5.0
    fielding_rating: float = 5.0
    experience_rating: float = 5.0


@dataclass
class CricketTeam:
    """Data class for cricket team information."""
    name: str
    country: str
    captain: str
    coach: str
    home_ground: str
    players: List[CricketPlayer] = None
    
    def __post_init__(self):
        if self.players is None:
            self.players = []


@dataclass
class MatchResult:
    """Data class for cricket match results."""
    match_type: str  # Test, ODI, T20
    venue: str
    date: str
    team1: str
    team2: str
    team1_score: str
    team2_score: str
    team1_overs: float
    team2_overs: float
    result: str  # Team1 won, Team2 won, Draw, Tie
    player_of_match: str
    team1_players: Dict[str, Dict[str, Any]]
    team2_players: Dict[str, Dict[str, Any]]


@dataclass
class Innings:
    """Data class for cricket innings."""
    team: str
    total_runs: int
    wickets: int
    overs: float
    run_rate: float
    extras: int
    batting_players: Dict[str, Dict[str, Any]]
    bowling_players: Dict[str, Dict[str, Any]]


class CricketData:
    """Contains cricket data and configuration."""
    
    # Sample teams data
    TEAMS_DATA = [
        CricketTeam("India", "India", "Rohit Sharma", "Rahul Dravid", "Wankhede Stadium"),
        CricketTeam("Australia", "Australia", "Pat Cummins", "Andrew McDonald", "MCG"),
        CricketTeam("England", "England", "Ben Stokes", "Brendon McCullum", "Lord's"),
        CricketTeam("South Africa", "South Africa", "Temba Bavuma", "Rob Walter", "Newlands"),
        CricketTeam("New Zealand", "New Zealand", "Tim Southee", "Gary Stead", "Eden Park"),
        CricketTeam("Pakistan", "Pakistan", "Babar Azam", "Grant Bradburn", "Gaddafi Stadium"),
        CricketTeam("West Indies", "West Indies", "Kraigg Brathwaite", "Andre Coley", "Kensington Oval"),
        CricketTeam("Sri Lanka", "Sri Lanka", "Dimuth Karunaratne", "Chris Silverwood", "R. Premadasa Stadium")
    ]
    
    # Sample players data
    PLAYERS_DATA = [
        # India players
        CricketPlayer("Virat Kohli", "India", "Batsman", "Right-handed", "Right-arm medium", 
                     254, 245, 12169, 183, 49.67, 93.17, 50, 46, 0, 0, "0/0", 0.0, 0.0, 0.0, 0, 0, 9.5, 3.0, 8.0, 9.0),
        CricketPlayer("Rohit Sharma", "India", "Batsman", "Right-handed", "Right-arm off-spin",
                     243, 237, 10109, 264, 42.67, 89.17, 30, 29, 0, 0, "0/0", 0.0, 0.0, 0.0, 0, 0, 9.0, 4.0, 7.0, 9.0),
        CricketPlayer("Jasprit Bumrah", "India", "Bowler", "Right-handed", "Right-arm fast",
                     30, 30, 0, 0, 0.0, 0.0, 0, 0, 120.5, 149, "6/27", 20.99, 2.69, 48.6, 0, 0, 2.0, 9.5, 8.0, 7.0),
        CricketPlayer("Ravichandran Ashwin", "India", "All-rounder", "Right-handed", "Right-arm off-spin",
                     94, 94, 3129, 124, 33.29, 53.90, 13, 5, 343.2, 489, "7/59", 23.69, 3.30, 42.1, 0, 0, 7.0, 9.0, 8.0, 9.0),
        
        # Australia players
        CricketPlayer("Steve Smith", "Australia", "Batsman", "Right-handed", "Right-arm leg-spin",
                     99, 99, 9320, 239, 58.61, 54.02, 37, 32, 0, 0, "0/0", 0.0, 0.0, 0.0, 0, 0, 9.5, 6.0, 8.0, 9.0),
        CricketPlayer("Pat Cummins", "Australia", "Bowler", "Right-handed", "Right-arm fast",
                     55, 55, 0, 0, 0.0, 0.0, 0, 0, 200.3, 239, "6/23", 22.59, 2.69, 50.3, 0, 0, 2.0, 9.5, 8.0, 8.0),
        CricketPlayer("Marnus Labuschagne", "Australia", "Batsman", "Right-handed", "Right-arm leg-spin",
                     41, 41, 3406, 215, 58.72, 53.47, 10, 11, 0, 0, "0/0", 0.0, 0.0, 0.0, 0, 0, 8.5, 5.0, 7.0, 6.0),
        CricketPlayer("Nathan Lyon", "Australia", "Bowler", "Right-handed", "Right-arm off-spin",
                     122, 122, 0, 0, 0.0, 0.0, 0, 0, 450.2, 496, "8/50", 31.38, 3.45, 54.5, 0, 0, 2.0, 9.0, 8.0, 9.0),
        
        # England players
        CricketPlayer("Joe Root", "England", "Batsman", "Right-handed", "Right-arm off-spin",
                     135, 135, 11416, 254, 50.16, 54.41, 60, 30, 0, 0, "0/0", 0.0, 0.0, 0.0, 0, 0, 9.5, 6.0, 8.0, 9.0),
        CricketPlayer("Ben Stokes", "England", "All-rounder", "Left-handed", "Right-arm fast-medium",
                     97, 97, 6119, 258, 35.34, 58.23, 31, 13, 180.5, 197, "6/22", 32.07, 3.32, 55.0, 0, 0, 8.5, 8.0, 9.0, 9.0),
        CricketPlayer("James Anderson", "England", "Bowler", "Left-handed", "Right-arm fast-medium",
                     183, 183, 0, 0, 0.0, 0.0, 0, 0, 650.3, 690, "7/42", 26.46, 2.79, 56.9, 0, 0, 2.0, 9.5, 8.0, 10.0),
        CricketPlayer("Stuart Broad", "England", "Bowler", "Left-handed", "Right-arm fast-medium",
                     167, 167, 0, 0, 0.0, 0.0, 0, 0, 600.2, 604, "8/15", 27.68, 2.94, 56.4, 0, 0, 2.0, 9.0, 8.0, 9.0)
    ]


class CricketSimulator:
    """Handles cricket match simulation."""
    
    @staticmethod
    def simulate_batting_performance(player: CricketPlayer, match_type: str) -> Dict[str, Any]:
        """Simulate batting performance for a player."""
        # Base performance based on player stats and match type
        if match_type == "T20":
            base_runs = player.average * 0.4 + random.gauss(0, 15)
            base_balls = max(1, int(base_runs / (player.strike_rate / 100) + random.gauss(0, 5)))
        elif match_type == "ODI":
            base_runs = player.average * 0.6 + random.gauss(0, 20)
            base_balls = max(1, int(base_runs / (player.strike_rate / 100) + random.gauss(0, 8)))
        else:  # Test
            base_runs = player.average * 0.8 + random.gauss(0, 25)
            base_balls = max(1, int(base_runs / (player.strike_rate / 100) + random.gauss(0, 12)))
        
        runs = max(0, int(base_runs))
        balls_faced = max(1, int(base_balls))
        
        # Determine dismissal
        dismissal_types = ["bowled", "caught", "lbw", "run out", "stumped", "hit wicket"]
        dismissal = random.choice(dismissal_types) if runs < 50 else "not out"
        
        # Calculate strike rate
        strike_rate = (runs / balls_faced * 100) if balls_faced > 0 else 0
        
        return {
            "name": player.name,
            "runs": runs,
            "balls_faced": balls_faced,
            "strike_rate": strike_rate,
            "dismissal": dismissal,
            "fours": runs // 4,
            "sixes": runs // 6
        }
    
    @staticmethod
    def simulate_bowling_performance(player: CricketPlayer, match_type: str) -> Dict[str, Any]:
        """Simulate bowling performance for a player."""
        if player.role not in ["Bowler", "All-rounder"]:
            return {"name": player.name, "overs": 0, "wickets": 0, "runs": 0, "economy": 0}
        
        # Determine overs based on match type
        if match_type == "T20":
            max_overs = 4
        elif match_type == "ODI":
            max_overs = 10
        else:  # Test
            max_overs = 20
        
        overs = random.randint(1, max_overs)
        
        # Calculate wickets and runs based on player's bowling stats
        base_wickets = (player.wickets / player.overs) * overs + random.gauss(0, 1)
        wickets = max(0, min(overs * 6, int(base_wickets)))
        
        runs_conceded = int(player.economy_rate * overs + random.gauss(0, overs * 2))
        economy = runs_conceded / overs if overs > 0 else 0
        
        return {
            "name": player.name,
            "overs": overs,
            "wickets": wickets,
            "runs_conceded": runs_conceded,
            "economy": economy,
            "maidens": random.randint(0, overs // 3)
        }
    
    @staticmethod
    def simulate_innings(team: CricketTeam, match_type: str, target: int = None) -> Innings:
        """Simulate a complete innings."""
        batting_players = {}
        bowling_players = {}
        
        total_runs = 0
        wickets = 0
        overs = 0
        
        # Determine innings length
        if match_type == "T20":
            max_overs = 20
        elif match_type == "ODI":
            max_overs = 50
        else:  # Test
            max_overs = 90
        
        # Simulate batting
        for player in team.players[:11]:  # Top 11 players
            if wickets >= 10 or (target and total_runs >= target):
                break
            
            batting_perf = CricketSimulator.simulate_batting_performance(player, match_type)
            batting_players[player.name] = batting_perf
            
            total_runs += batting_perf["runs"]
            if batting_perf["dismissal"] != "not out":
                wickets += 1
            
            # Estimate overs based on runs and strike rate
            overs += batting_perf["balls_faced"] / 6
        
        overs = min(overs, max_overs)
        run_rate = total_runs / overs if overs > 0 else 0
        
        return Innings(
            team=team.name,
            total_runs=total_runs,
            wickets=wickets,
            overs=overs,
            run_rate=run_rate,
            extras=random.randint(5, 20),
            batting_players=batting_players,
            bowling_players=bowling_players
        )
    
    @staticmethod
    def simulate_match(team1: CricketTeam, team2: CricketTeam, match_type: str, venue: str) -> MatchResult:
        """Simulate a complete cricket match."""
        # Simulate first innings
        innings1 = CricketSimulator.simulate_innings(team1, match_type)
        
        # Simulate second innings
        target = innings1.total_runs + 1
        innings2 = CricketSimulator.simulate_innings(team2, match_type, target)
        
        # Determine result
        if innings2.total_runs > innings1.total_runs:
            result = f"{team2.name} won"
            winner = team2.name
        elif innings2.total_runs < innings1.total_runs:
            result = f"{team1.name} won"
            winner = team1.name
        else:
            result = "Match tied"
            winner = "Tie"
        
        # Find player of the match
        all_players = list(innings1.batting_players.items()) + list(innings2.batting_players.items())
        player_of_match = max(all_players, key=lambda x: x[1]["runs"])[0]
        
        return MatchResult(
            match_type=match_type,
            venue=venue,
            date=datetime.now().strftime("%Y-%m-%d"),
            team1=team1.name,
            team2=team2.name,
            team1_score=f"{innings1.total_runs}/{innings1.wickets}",
            team2_score=f"{innings2.total_runs}/{innings2.wickets}",
            team1_overs=innings1.overs,
            team2_overs=innings2.overs,
            result=result,
            player_of_match=player_of_match,
            team1_players=innings1.batting_players,
            team2_players=innings2.batting_players
        )


class CricketAnalyzer:
    """Analyzes cricket statistics and provides insights."""
    
    def __init__(self):
        self.teams = self._load_teams()
        self.players = self._load_players()
    
    def _load_teams(self) -> List[CricketTeam]:
        """Load teams from data."""
        csv_path = os.path.join(os.path.dirname(__file__), 'data', 'teams.csv')
        if os.path.exists(csv_path):
            df = pd.read_csv(csv_path)
            return [CricketTeam(**row) for _, row in df.iterrows()]
        # fallback to hardcoded data
        return [
            CricketTeam("India", "India", "Rohit Sharma", "Rahul Dravid", "Wankhede Stadium"),
            CricketTeam("Australia", "Australia", "Pat Cummins", "Andrew McDonald", "MCG"),
        ]
    
    def _load_players(self) -> List[CricketPlayer]:
        """Load players from data."""
        csv_path = os.path.join(os.path.dirname(__file__), 'data', 'players.csv')
        if os.path.exists(csv_path):
            df = pd.read_csv(csv_path)
            return [CricketPlayer(**row) for _, row in df.iterrows()]
        # fallback to hardcoded data
        return [
            CricketPlayer("Virat Kohli", "India", "Batsman", "Right-handed", "Right-arm medium", 254, 245, 12169, 183, 49.67, 93.17, 50, 46, 0, 0, "0/0", 0.0, 0.0, 0.0, 0, 0, 9.5, 3.0, 8.0, 9.0),
            CricketPlayer("Rohit Sharma", "India", "Batsman", "Right-handed", "Right-arm off-spin", 243, 237, 10109, 264, 42.67, 89.17, 30, 29, 0, 0, "0/0", 0.0, 0.0, 0.0, 0, 0, 9.0, 4.0, 7.0, 9.0),
        ]
    
    def get_team_by_name(self, name: str) -> Optional[CricketTeam]:
        """Get team by name."""
        for team in self.teams:
            if team.name == name:
                return team
        return None
    
    def get_player_by_name(self, name: str) -> Optional[CricketPlayer]:
        """Get player by name."""
        for player in self.players:
            if player.name == name:
                return player
        return None
    
    def analyze_player(self, player_name: str) -> Dict[str, Any]:
        """Analyze individual player performance."""
        player = self.get_player_by_name(player_name)
        if not player:
            return {"error": "Player not found"}
        
        # Calculate overall rating
        overall_rating = (
            player.batting_rating + player.bowling_rating + 
            player.fielding_rating + player.experience_rating
        ) / 4.0
        
        # Role-specific analysis
        if player.role == "Batsman":
            primary_skill = "Batting"
            primary_rating = player.batting_rating
        elif player.role == "Bowler":
            primary_skill = "Bowling"
            primary_rating = player.bowling_rating
        else:  # All-rounder
            primary_skill = "All-round"
            primary_rating = (player.batting_rating + player.bowling_rating) / 2
        
        # Career milestones
        milestones = []
        if player.hundreds >= 10:
            milestones.append(f"{player.hundreds} centuries")
        if player.fifties >= 20:
            milestones.append(f"{player.fifties} fifties")
        if player.wickets >= 100:
            milestones.append(f"{player.wickets} wickets")
        if player.matches >= 100:
            milestones.append(f"{player.matches} matches")
        
        return {
            "player": asdict(player),
            "analysis": {
                "overall_rating": overall_rating,
                "primary_skill": primary_skill,
                "primary_rating": primary_rating,
                "career_milestones": milestones,
                "batting_efficiency": player.average * player.strike_rate / 100 if player.average > 0 else 0,
                "bowling_efficiency": player.wickets / player.overs if player.overs > 0 else 0
            }
        }
    
    def get_team_analysis(self, team_name: str) -> Dict[str, Any]:
        """Analyze team composition and strength."""
        team = self.get_team_by_name(team_name)
        if not team:
            return {"error": "Team not found"}
        
        # Team composition
        batsmen = [p for p in team.players if p.role == "Batsman"]
        bowlers = [p for p in team.players if p.role == "Bowler"]
        all_rounders = [p for p in team.players if p.role == "All-rounder"]
        wicket_keepers = [p for p in team.players if p.role == "Wicket-keeper"]
        
        # Calculate team strengths
        batting_strength = statistics.mean([p.batting_rating for p in team.players])
        bowling_strength = statistics.mean([p.bowling_rating for p in team.players])
        fielding_strength = statistics.mean([p.fielding_rating for p in team.players])
        
        # Find key players
        best_batsman = max(team.players, key=lambda p: p.batting_rating)
        best_bowler = max(team.players, key=lambda p: p.bowling_rating)
        most_experienced = max(team.players, key=lambda p: p.matches)
        
        return {
            "team": asdict(team),
            "composition": {
                "batsmen": len(batsmen),
                "bowlers": len(bowlers),
                "all_rounders": len(all_rounders),
                "wicket_keepers": len(wicket_keepers)
            },
            "strengths": {
                "batting": batting_strength,
                "bowling": bowling_strength,
                "fielding": fielding_strength,
                "overall": (batting_strength + bowling_strength + fielding_strength) / 3
            },
            "key_players": {
                "best_batsman": asdict(best_batsman),
                "best_bowler": asdict(best_bowler),
                "most_experienced": asdict(most_experienced)
            }
        }
    
    def simulate_series(self, team1_name: str, team2_name: str, match_type: str, num_matches: int) -> Dict[str, Any]:
        """Simulate a series between two teams."""
        team1 = self.get_team_by_name(team1_name)
        team2 = self.get_team_by_name(team2_name)
        
        if not team1 or not team2:
            return {"error": "One or both teams not found"}
        
        series_results = []
        team1_wins = 0
        team2_wins = 0
        draws = 0
        
        venues = ["Home Ground 1", "Home Ground 2", "Neutral Venue 1", "Neutral Venue 2"]
        
        for i in range(num_matches):
            venue = venues[i % len(venues)]
            match = CricketSimulator.simulate_match(team1, team2, match_type, venue)
            series_results.append(asdict(match))
            
            if "won" in match.result:
                if team1.name in match.result:
                    team1_wins += 1
                else:
                    team2_wins += 1
            else:
                draws += 1
        
        # Determine series winner
        if team1_wins > team2_wins:
            series_winner = team1.name
        elif team2_wins > team1_wins:
            series_winner = team2.name
        else:
            series_winner = "Series drawn"
        
        return {
            "series_info": {
                "team1": team1.name,
                "team2": team2.name,
                "match_type": match_type,
                "num_matches": num_matches
            },
            "results": {
                "team1_wins": team1_wins,
                "team2_wins": team2_wins,
                "draws": draws,
                "series_winner": series_winner
            },
            "matches": series_results
        }
    
    def get_ranking_analysis(self) -> Dict[str, Any]:
        """Analyze player rankings by different criteria."""
        # Batting rankings
        batsmen = [p for p in self.players if p.role in ["Batsman", "All-rounder"]]
        batting_rankings = sorted(batsmen, key=lambda p: p.average, reverse=True)[:10]
        
        # Bowling rankings
        bowlers = [p for p in self.players if p.role in ["Bowler", "All-rounder"] and p.wickets > 0]
        bowling_rankings = sorted(bowlers, key=lambda p: p.bowling_average)[:10]
        
        # All-rounder rankings
        all_rounders = [p for p in self.players if p.role == "All-rounder"]
        all_rounder_rankings = sorted(all_rounders, 
                                    key=lambda p: (p.batting_rating + p.bowling_rating) / 2, 
                                    reverse=True)[:10]
        
        return {
            "batting_rankings": [asdict(p) for p in batting_rankings],
            "bowling_rankings": [asdict(p) for p in bowling_rankings],
            "all_rounder_rankings": [asdict(p) for p in all_rounder_rankings]
        }


def main():
    """Main function to demonstrate cricket analysis."""
    analyzer = CricketAnalyzer()
    
    print("=== Cricket Analysis Tool ===\n")
    
    # Player analysis
    print("1. Player Analysis - Virat Kohli:")
    player_analysis = analyzer.analyze_player("Virat Kohli")
    print(f"Overall Rating: {player_analysis['analysis']['overall_rating']:.2f}")
    print(f"Primary Skill: {player_analysis['analysis']['primary_skill']}")
    print(f"Batting Average: {player_analysis['player']['average']}")
    print(f"Centuries: {player_analysis['player']['hundreds']}")
    print()
    
    # Team analysis
    print("2. Team Analysis - India:")
    team_analysis = analyzer.get_team_analysis("India")
    print(f"Batting Strength: {team_analysis['strengths']['batting']:.2f}")
    print(f"Bowling Strength: {team_analysis['strengths']['bowling']:.2f}")
    print(f"Best Batsman: {team_analysis['key_players']['best_batsman']['name']}")
    print(f"Best Bowler: {team_analysis['key_players']['best_bowler']['name']}")
    print()
    
    # Match simulation
    print("3. Match Simulation - India vs Australia (T20):")
    india = analyzer.get_team_by_name("India")
    australia = analyzer.get_team_by_name("Australia")
    
    if india and australia:
        match = CricketSimulator.simulate_match(india, australia, "T20", "Wankhede Stadium")
        print(f"{match.team1}: {match.team1_score} ({match.team1_overs:.1f} overs)")
        print(f"{match.team2}: {match.team2_score} ({match.team2_overs:.1f} overs)")
        print(f"Result: {match.result}")
        print(f"Player of the Match: {match.player_of_match}")
    print()
    
    # Series simulation
    print("4. Series Simulation - India vs Australia (3 T20s):")
    series = analyzer.simulate_series("India", "Australia", "T20", 3)
    print(f"Series Winner: {series['results']['series_winner']}")
    print(f"India Wins: {series['results']['team1_wins']}")
    print(f"Australia Wins: {series['results']['team2_wins']}")
    print()
    
    # Rankings
    print("5. Top Batsmen (by average):")
    rankings = analyzer.get_ranking_analysis()
    for i, player in enumerate(rankings['batting_rankings'][:5], 1):
        print(f"{i}. {player['name']} - {player['average']:.2f}")
    
    # Plot top batsmen by average
    batting_avg_data = {player['name']: player['average'] for player in rankings['batting_rankings']}
    batting_avg_series = pd.Series(batting_avg_data) # Already sorted by average in get_ranking_analysis
    plot_generic_top_n(batting_avg_series, "Top 10 Batsmen by Average", "Player", "Batting Average", top_n=10, sort_ascending=False)

    print("\n=== Analysis Complete ===")


if __name__ == "__main__":
    main()


def plot_generic_top_n(data_series: pd.Series, title: str, xlabel: str, ylabel: str, top_n: int = 10, sort_ascending=False) -> None:
    """Displays a generic bar chart for a pandas Series in the terminal."""
    sorted_series = data_series.sort_values(ascending=sort_ascending)
    top_data = sorted_series.head(top_n)
    items = top_data.index.tolist()
    values = top_data.values.tolist()

    plt.clf()
    plt.bar(items, values)
    plt.title(title)
    plt.xlabel(xlabel)
    plt.ylabel(ylabel)
    plt.show()