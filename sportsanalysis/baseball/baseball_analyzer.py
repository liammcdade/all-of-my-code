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
class BaseballPlayer:
    """Data class for baseball player statistics."""
    name: str
    team: str
    position: str  # Pitcher, Catcher, 1B, 2B, 3B, SS, LF, CF, RF, DH
    batting_side: str  # L, R, S (Switch)
    throwing_side: str  # L, R
    
    # Batting stats
    games: int = 0
    at_bats: int = 0
    hits: int = 0
    doubles: int = 0
    triples: int = 0
    home_runs: int = 0
    rbi: int = 0
    runs: int = 0
    walks: int = 0
    strikeouts: int = 0
    stolen_bases: int = 0
    caught_stealing: int = 0
    batting_average: float = 0.0
    on_base_pct: float = 0.0
    slugging_pct: float = 0.0
    ops: float = 0.0  # On-base plus slugging
    
    # Pitching stats (for pitchers)
    wins: int = 0
    losses: int = 0
    era: float = 0.0  # Earned run average
    games_pitched: int = 0
    games_started: int = 0
    complete_games: int = 0
    shutouts: int = 0
    saves: int = 0
    innings_pitched: float = 0.0
    hits_allowed: int = 0
    runs_allowed: int = 0
    earned_runs: int = 0
    home_runs_allowed: int = 0
    walks_allowed: int = 0
    strikeouts_pitched: int = 0
    whip: float = 0.0  # Walks plus hits per inning pitched
    
    # Fielding stats
    fielding_pct: float = 0.0
    errors: int = 0
    assists: int = 0
    putouts: int = 0
    
    # Ratings (1-10)
    contact_rating: float = 5.0
    power_rating: float = 5.0
    speed_rating: float = 5.0
    fielding_rating: float = 5.0
    throwing_rating: float = 5.0
    pitching_rating: float = 5.0
    control_rating: float = 5.0  # For pitchers


@dataclass
class BaseballTeam:
    """Data class for baseball team information."""
    name: str
    league: str  # AL, NL
    division: str  # East, Central, West
    city: str
    stadium: str
    manager: str
    players: List[BaseballPlayer] = None
    
    def __post_init__(self):
        if self.players is None:
            self.players = []


@dataclass
class GameResult:
    """Data class for baseball game results."""
    home_team: str
    away_team: str
    home_score: int
    away_score: int
    innings: int
    date: str
    venue: str
    duration_minutes: int
    attendance: int
    home_pitcher: str
    away_pitcher: str
    home_hits: int
    away_hits: int
    home_errors: int
    away_errors: int
    home_players: Dict[str, Dict[str, Any]]
    away_players: Dict[str, Dict[str, Any]]


@dataclass
class Inning:
    """Data class for baseball inning."""
    inning_number: int
    home_runs: int
    away_runs: int
    home_hits: int
    away_hits: int
    home_errors: int
    away_errors: int


class BaseballData:
    """Contains baseball data and configuration."""
    
    # Sample MLB teams data
    TEAMS_DATA = [
        BaseballTeam("New York Yankees", "AL", "East", "New York", "Yankee Stadium", "Aaron Boone"),
        BaseballTeam("Boston Red Sox", "AL", "East", "Boston", "Fenway Park", "Alex Cora"),
        BaseballTeam("Los Angeles Dodgers", "NL", "West", "Los Angeles", "Dodger Stadium", "Dave Roberts"),
        BaseballTeam("San Francisco Giants", "NL", "West", "San Francisco", "Oracle Park", "Gabe Kapler"),
        BaseballTeam("Chicago Cubs", "NL", "Central", "Chicago", "Wrigley Field", "David Ross"),
        BaseballTeam("St. Louis Cardinals", "NL", "Central", "St. Louis", "Busch Stadium", "Oliver Marmol"),
        BaseballTeam("Houston Astros", "AL", "West", "Houston", "Minute Maid Park", "Dusty Baker"),
        BaseballTeam("Atlanta Braves", "NL", "East", "Atlanta", "Truist Park", "Brian Snitker")
    ]
    
    # Sample MLB players data
    PLAYERS_DATA = [
        # Yankees players
        BaseballPlayer("Aaron Judge", "New York Yankees", "RF", "R", "R", 
                      157, 570, 177, 28, 0, 62, 131, 133, 111, 175, 16, 3, 0.311, 0.425, 0.686, 1.111, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 9.0, 9.5, 7.0, 8.0, 9.0, 5.0, 5.0),
        BaseballPlayer("Gerrit Cole", "New York Yankees", "P", "R", "R",
                      0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0.0, 0.0, 0.0, 0.0, 13, 5, 2.63, 33, 33, 0, 0, 0, 200.2, 165, 65, 59, 16, 33, 257, 1.02, 0.0, 0, 0, 0, 5.0, 5.0, 5.0, 5.0, 5.0, 9.5, 9.0),
        BaseballPlayer("Giancarlo Stanton", "New York Yankees", "DH", "R", "R",
                      110, 398, 101, 15, 0, 31, 78, 53, 44, 139, 0, 0, 0.254, 0.349, 0.492, 0.841, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 7.0, 9.0, 4.0, 5.0, 5.0, 5.0, 5.0),
        
        # Red Sox players
        BaseballPlayer("Rafael Devers", "Boston Red Sox", "3B", "L", "R",
                      156, 614, 166, 42, 1, 33, 100, 84, 62, 113, 3, 1, 0.270, 0.341, 0.521, 0.862, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 8.0, 8.5, 5.0, 7.0, 8.0, 5.0, 5.0),
        BaseballPlayer("Chris Sale", "Boston Red Sox", "P", "L", "L",
                      0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0.0, 0.0, 0.0, 0.0, 5, 2, 4.40, 20, 20, 0, 0, 0, 102.2, 89, 52, 50, 15, 24, 125, 1.10, 0.0, 0, 0, 0, 5.0, 5.0, 5.0, 5.0, 5.0, 8.5, 8.0),
        BaseballPlayer("Trevor Story", "Boston Red Sox", "SS", "R", "R",
                      94, 396, 117, 24, 2, 16, 66, 53, 44, 122, 13, 3, 0.295, 0.343, 0.450, 0.793, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 8.0, 7.0, 8.0, 8.0, 8.0, 5.0, 5.0),
        
        # Dodgers players
        BaseballPlayer("Mookie Betts", "Los Angeles Dodgers", "RF", "R", "R",
                      142, 572, 154, 35, 1, 35, 82, 117, 61, 107, 12, 3, 0.269, 0.340, 0.533, 0.873, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 9.0, 8.0, 9.0, 9.0, 9.0, 5.0, 5.0),
        BaseballPlayer("Clayton Kershaw", "Los Angeles Dodgers", "P", "L", "L",
                      0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0.0, 0.0, 0.0, 0.0, 12, 3, 2.28, 22, 22, 0, 0, 0, 131.2, 95, 36, 33, 9, 23, 137, 0.90, 0.0, 0, 0, 0, 5.0, 5.0, 5.0, 5.0, 5.0, 9.0, 9.5),
        BaseballPlayer("Freddie Freeman", "Los Angeles Dodgers", "1B", "L", "R",
                      159, 612, 199, 47, 2, 29, 102, 131, 84, 121, 13, 2, 0.325, 0.407, 0.567, 0.974, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 9.0, 8.0, 6.0, 8.0, 7.0, 5.0, 5.0),
        
        # Giants players
        BaseballPlayer("Brandon Crawford", "San Francisco Giants", "SS", "L", "R",
                      138, 488, 114, 30, 3, 9, 52, 54, 45, 108, 3, 1, 0.234, 0.311, 0.350, 0.661, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 7.0, 5.0, 6.0, 9.0, 9.0, 5.0, 5.0),
        BaseballPlayer("Logan Webb", "San Francisco Giants", "P", "R", "R",
                      0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0.0, 0.0, 0.0, 0.0, 11, 13, 3.25, 32, 32, 0, 0, 0, 192.1, 169, 75, 69, 20, 49, 194, 1.13, 0.0, 0, 0, 0, 5.0, 5.0, 5.0, 5.0, 5.0, 8.5, 8.0),
        BaseballPlayer("Joc Pederson", "San Francisco Giants", "LF", "L", "L",
                      134, 433, 108, 19, 1, 23, 70, 56, 43, 131, 3, 1, 0.249, 0.325, 0.521, 0.846, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 7.0, 8.5, 6.0, 6.0, 6.0, 5.0, 5.0)
    ]


class BaseballSimulator:
    """Handles baseball game simulation."""
    
    @staticmethod
    def simulate_at_bat(batter: BaseballPlayer, pitcher: BaseballPlayer) -> Dict[str, Any]:
        """Simulate a single at-bat."""
        # Calculate hit probability based on batter's contact rating and pitcher's control
        contact_prob = batter.contact_rating / 10.0
        control_factor = (10 - pitcher.control_rating) / 10.0
        hit_prob = contact_prob * (1 - control_factor * 0.3)
        
        # Determine outcome
        outcome = random.random()
        
        if outcome < hit_prob * 0.6:  # Single
            return {"outcome": "single", "bases": 1, "rbi": 0}
        elif outcome < hit_prob * 0.8:  # Double
            return {"outcome": "double", "bases": 2, "rbi": 0}
        elif outcome < hit_prob * 0.95:  # Triple
            return {"outcome": "triple", "bases": 3, "rbi": 0}
        elif outcome < hit_prob:  # Home run
            return {"outcome": "home_run", "bases": 4, "rbi": 1}
        elif outcome < hit_prob + 0.1:  # Walk
            return {"outcome": "walk", "bases": 1, "rbi": 0}
        else:  # Out
            return {"outcome": "out", "bases": 0, "rbi": 0}
    
    @staticmethod
    def simulate_inning(home_team: BaseballTeam, away_team: BaseballTeam, is_home: bool) -> Dict[str, Any]:
        """Simulate a single inning."""
        team = home_team if is_home else away_team
        opponent = away_team if is_home else home_team
        
        runs = 0
        hits = 0
        errors = 0
        outs = 0
        bases = [False, False, False]  # First, Second, Third
        
        # Get starting pitcher
        pitchers = [p for p in opponent.players if p.position == "P"]
        pitcher = random.choice(pitchers) if pitchers else None
        
        # Simulate until 3 outs
        while outs < 3:
            # Select batter
            batters = [p for p in team.players if p.position != "P"]
            batter = random.choice(batters) if batters else None
            
            if not batter or not pitcher:
                outs += 1
                continue
            
            # Simulate at-bat
            at_bat = BaseballSimulator.simulate_at_bat(batter, pitcher)
            
            if at_bat["outcome"] == "out":
                outs += 1
            elif at_bat["outcome"] == "walk":
                # Move runners
                if bases[2]:  # Runner on third scores
                    runs += 1
                if bases[1]:  # Runner on second moves to third
                    bases[2] = True
                if bases[0]:  # Runner on first moves to second
                    bases[1] = True
                bases[0] = True  # Batter to first
            else:  # Hit
                hits += 1
                bases_advanced = at_bat["bases"]
                
                # Move runners and score runs
                for i in range(3):
                    if bases[2-i]:  # Start from third base
                        if 2-i + bases_advanced >= 3:
                            runs += 1
                        else:
                            bases[2-i + bases_advanced] = True
                        bases[2-i] = False
                
                # Place batter
                if bases_advanced == 4:  # Home run
                    runs += 1
                else:
                    bases[bases_advanced - 1] = True
        
        return {
            "runs": runs,
            "hits": hits,
            "errors": errors
        }
    
    @staticmethod
    def simulate_game(home_team: BaseballTeam, away_team: BaseballTeam, venue: str) -> GameResult:
        """Simulate a complete baseball game."""
        home_score = 0
        away_score = 0
        home_hits = 0
        away_hits = 0
        home_errors = 0
        away_errors = 0
        innings = []
        
        # Simulate 9 innings (or more if tied)
        for inning_num in range(1, 10):
            # Away team bats first
            away_inning = BaseballSimulator.simulate_inning(home_team, away_team, False)
            away_score += away_inning["runs"]
            away_hits += away_inning["hits"]
            away_errors += away_inning["errors"]
            
            # Home team bats
            home_inning = BaseballSimulator.simulate_inning(home_team, away_team, True)
            home_score += home_inning["runs"]
            home_hits += home_inning["hits"]
            home_errors += home_inning["errors"]
            
            innings.append(Inning(
                inning_number=inning_num,
                home_runs=home_inning["runs"],
                away_runs=away_inning["runs"],
                home_hits=home_inning["hits"],
                away_hits=away_inning["hits"],
                home_errors=home_inning["errors"],
                away_errors=away_inning["errors"]
            ))
        
        # Extra innings if tied
        extra_innings = 0
        while home_score == away_score and extra_innings < 3:
            extra_innings += 1
            
            away_inning = BaseballSimulator.simulate_inning(home_team, away_team, False)
            away_score += away_inning["runs"]
            away_hits += away_inning["hits"]
            away_errors += away_inning["errors"]
            
            home_inning = BaseballSimulator.simulate_inning(home_team, away_team, True)
            home_score += home_inning["runs"]
            home_hits += home_inning["hits"]
            home_errors += home_inning["errors"]
            
            innings.append(Inning(
                inning_number=9 + extra_innings,
                home_runs=home_inning["runs"],
                away_runs=away_inning["runs"],
                home_hits=home_inning["hits"],
                away_hits=away_inning["hits"],
                home_errors=home_inning["errors"],
                away_errors=away_inning["errors"]
            ))
        
        # Get starting pitchers
        home_pitchers = [p for p in home_team.players if p.position == "P"]
        away_pitchers = [p for p in away_team.players if p.position == "P"]
        home_pitcher = random.choice(home_pitchers).name if home_pitchers else "Unknown"
        away_pitcher = random.choice(away_pitchers).name if away_pitchers else "Unknown"
        
        # Simulate player performances
        home_players = {}
        away_players = {}
        
        for player in home_team.players[:9]:  # Starting lineup
            if player.position != "P":
                at_bats = random.randint(3, 5)
                hits = random.randint(0, at_bats)
                home_players[player.name] = {
                    "at_bats": at_bats,
                    "hits": hits,
                    "runs": random.randint(0, hits),
                    "rbi": random.randint(0, hits)
                }
        
        for player in away_team.players[:9]:  # Starting lineup
            if player.position != "P":
                at_bats = random.randint(3, 5)
                hits = random.randint(0, at_bats)
                away_players[player.name] = {
                    "at_bats": at_bats,
                    "hits": hits,
                    "runs": random.randint(0, hits),
                    "rbi": random.randint(0, hits)
                }
        
        return GameResult(
            home_team=home_team.name,
            away_team=away_team.name,
            home_score=home_score,
            away_score=away_score,
            innings=9 + extra_innings,
            date=datetime.now().strftime("%Y-%m-%d"),
            venue=venue,
            duration_minutes=random.randint(150, 210),
            attendance=random.randint(20000, 50000),
            home_pitcher=home_pitcher,
            away_pitcher=away_pitcher,
            home_hits=home_hits,
            away_hits=away_hits,
            home_errors=home_errors,
            away_errors=away_errors,
            home_players=home_players,
            away_players=away_players
        )


class BaseballAnalyzer:
    """Analyzes baseball statistics and provides insights."""
    
    def __init__(self):
        self.teams = self._load_teams()
        self.players = self._load_players()
    
    def _load_teams(self) -> List[BaseballTeam]:
        """Load teams from data."""
        csv_path = os.path.join(os.path.dirname(__file__), 'data', 'teams.csv')
        if os.path.exists(csv_path):
            df = pd.read_csv(csv_path)
            return [BaseballTeam(**row) for _, row in df.iterrows()]
        # fallback to hardcoded data
        return [
            BaseballTeam("New York Yankees", "AL", "East", "New York", "Yankee Stadium", "Aaron Boone"),
            BaseballTeam("Boston Red Sox", "AL", "East", "Boston", "Fenway Park", "Alex Cora"),
        ]
    
    def _load_players(self) -> List[BaseballPlayer]:
        """Load players from data."""
        csv_path = os.path.join(os.path.dirname(__file__), 'data', 'players.csv')
        if os.path.exists(csv_path):
            df = pd.read_csv(csv_path)
            return [BaseballPlayer(**row) for _, row in df.iterrows()]
        # fallback to hardcoded data
        return [
            BaseballPlayer("Aaron Judge", "New York Yankees", "RF", "R", "R", 157, 570, 177, 28, 0, 62, 131, 133, 111, 175, 16, 3, 0.311, 0.425, 0.686, 1.111, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 9.0, 9.5, 7.0, 8.0, 9.0, 5.0, 5.0),
            BaseballPlayer("Gerrit Cole", "New York Yankees", "P", "R", "R", 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0.0, 0.0, 0.0, 0.0, 13, 5, 2.63, 33, 33, 0, 0, 0, 200.2, 165, 65, 59, 16, 33, 257, 1.02, 0.0, 0, 0, 0, 5.0, 5.0, 5.0, 5.0, 5.0, 9.5, 9.0),
        ]
    
    def get_team_by_name(self, name: str) -> Optional[BaseballTeam]:
        """Get team by name."""
        for team in self.teams:
            if team.name == name:
                return team
        return None
    
    def get_player_by_name(self, name: str) -> Optional[BaseballPlayer]:
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
        
        # Calculate advanced stats
        if player.at_bats > 0:
            babip = (player.hits - player.home_runs) / (player.at_bats - player.home_runs - player.strikeouts + player.sacrifice_flies) if (player.at_bats - player.home_runs - player.strikeouts) > 0 else 0
            iso = player.slugging_pct - player.batting_average
        else:
            babip = 0
            iso = 0
        
        # Position-specific analysis
        if player.position == "P":
            primary_skill = "Pitching"
            primary_rating = player.pitching_rating
            key_stats = {
                "era": player.era,
                "wins": player.wins,
                "losses": player.losses,
                "strikeouts": player.strikeouts_pitched,
                "whip": player.whip
            }
        else:
            primary_skill = "Batting"
            primary_rating = (player.contact_rating + player.power_rating) / 2
            key_stats = {
                "batting_average": player.batting_average,
                "home_runs": player.home_runs,
                "rbi": player.rbi,
                "ops": player.ops,
                "stolen_bases": player.stolen_bases
            }
        
        return {
            "player": asdict(player),
            "analysis": {
                "primary_skill": primary_skill,
                "primary_rating": primary_rating,
                "key_stats": key_stats,
                "advanced_stats": {
                    "babip": babip,
                    "iso": iso,
                    "overall_rating": (player.contact_rating + player.power_rating + player.speed_rating + 
                                     player.fielding_rating + player.throwing_rating) / 5
                }
            }
        }
    
    def get_team_analysis(self, team_name: str) -> Dict[str, Any]:
        """Analyze team composition and strength."""
        team = self.get_team_by_name(team_name)
        if not team:
            return {"error": "Team not found"}
        
        # Team composition
        pitchers = [p for p in team.players if p.position == "P"]
        position_players = [p for p in team.players if p.position != "P"]
        
        # Calculate team strengths
        batting_strength = statistics.mean([p.contact_rating + p.power_rating for p in position_players]) / 2
        pitching_strength = statistics.mean([p.pitching_rating + p.control_rating for p in pitchers]) / 2
        fielding_strength = statistics.mean([p.fielding_rating + p.throwing_rating for p in team.players]) / 2
        
        # Find key players
        best_batter = max(position_players, key=lambda p: p.ops) if position_players else None
        best_pitcher = min(pitchers, key=lambda p: p.era) if pitchers else None
        most_home_runs = max(position_players, key=lambda p: p.home_runs) if position_players else None
        
        return {
            "team": asdict(team),
            "composition": {
                "pitchers": len(pitchers),
                "position_players": len(position_players),
                "total_players": len(team.players)
            },
            "strengths": {
                "batting": batting_strength,
                "pitching": pitching_strength,
                "fielding": fielding_strength,
                "overall": (batting_strength + pitching_strength + fielding_strength) / 3
            },
            "key_players": {
                "best_batter": asdict(best_batter) if best_batter else None,
                "best_pitcher": asdict(best_pitcher) if best_pitcher else None,
                "most_home_runs": asdict(most_home_runs) if most_home_runs else None
            }
        }
    
    def simulate_series(self, team1_name: str, team2_name: str, num_games: int) -> Dict[str, Any]:
        """Simulate a series between two teams."""
        team1 = self.get_team_by_name(team1_name)
        team2 = self.get_team_by_name(team2_name)
        
        if not team1 or not team2:
            return {"error": "One or both teams not found"}
        
        series_results = []
        team1_wins = 0
        team2_wins = 0
        
        venues = [team1.stadium, team2.stadium]
        
        for i in range(num_games):
            venue = venues[i % 2]  # Alternate venues
            home_team = team1 if i % 2 == 0 else team2
            away_team = team2 if i % 2 == 0 else team1
            
            game = BaseballSimulator.simulate_game(home_team, away_team, venue)
            series_results.append(asdict(game))
            
            if game.home_score > game.away_score:
                if home_team == team1:
                    team1_wins += 1
                else:
                    team2_wins += 1
            else:
                if away_team == team1:
                    team1_wins += 1
                else:
                    team2_wins += 1
        
        # Determine series winner
        if team1_wins > team2_wins:
            series_winner = team1.name
        elif team2_wins > team1_wins:
            series_winner = team2.name
        else:
            series_winner = "Series tied"
        
        return {
            "series_info": {
                "team1": team1.name,
                "team2": team2.name,
                "num_games": num_games
            },
            "results": {
                "team1_wins": team1_wins,
                "team2_wins": team2_wins,
                "series_winner": series_winner
            },
            "games": series_results
        }
    
    def get_league_rankings(self) -> Dict[str, Any]:
        """Get league rankings by different criteria."""
        # Batting rankings
        batters = [p for p in self.players if p.position != "P" and p.at_bats > 100]
        batting_rankings = sorted(batters, key=lambda p: p.ops, reverse=True)[:10]
        
        # Pitching rankings
        pitchers = [p for p in self.players if p.position == "P" and p.innings_pitched > 50]
        pitching_rankings = sorted(pitchers, key=lambda p: p.era)[:10]
        
        # Home run leaders
        hr_leaders = sorted(batters, key=lambda p: p.home_runs, reverse=True)[:10]
        
        # Stolen base leaders
        sb_leaders = sorted(batters, key=lambda p: p.stolen_bases, reverse=True)[:10]
        
        return {
            "batting_rankings": [asdict(p) for p in batting_rankings],
            "pitching_rankings": [asdict(p) for p in pitching_rankings],
            "home_run_leaders": [asdict(p) for p in hr_leaders],
            "stolen_base_leaders": [asdict(p) for p in sb_leaders]
        }


def main():
    """Main function to demonstrate baseball analysis."""
    analyzer = BaseballAnalyzer()
    
    print("=== Baseball Analysis Tool ===\n")
    
    # Player analysis
    print("1. Player Analysis - Aaron Judge:")
    player_analysis = analyzer.analyze_player("Aaron Judge")
    print(f"Primary Skill: {player_analysis['analysis']['primary_skill']}")
    print(f"Batting Average: {player_analysis['player']['batting_average']:.3f}")
    print(f"Home Runs: {player_analysis['player']['home_runs']}")
    print(f"OPS: {player_analysis['player']['ops']:.3f}")
    print()
    
    # Team analysis
    print("2. Team Analysis - New York Yankees:")
    team_analysis = analyzer.get_team_analysis("New York Yankees")
    print(f"Batting Strength: {team_analysis['strengths']['batting']:.2f}")
    print(f"Pitching Strength: {team_analysis['strengths']['pitching']:.2f}")
    if team_analysis['key_players']['best_batter']:
        print(f"Best Batter: {team_analysis['key_players']['best_batter']['name']}")
    if team_analysis['key_players']['best_pitcher']:
        print(f"Best Pitcher: {team_analysis['key_players']['best_pitcher']['name']}")
    print()
    
    # Game simulation
    print("3. Game Simulation - Yankees vs Red Sox:")
    yankees = analyzer.get_team_by_name("New York Yankees")
    red_sox = analyzer.get_team_by_name("Boston Red Sox")
    
    if yankees and red_sox:
        game = BaseballSimulator.simulate_game(yankees, red_sox, "Yankee Stadium")
        print(f"{game.home_team}: {game.home_score}")
        print(f"{game.away_team}: {game.away_score}")
        print(f"Innings: {game.innings}")
        print(f"Duration: {game.duration_minutes} minutes")
    print()
    
    # Series simulation
    print("4. Series Simulation - Yankees vs Red Sox (3 games):")
    series = analyzer.simulate_series("New York Yankees", "Boston Red Sox", 3)
    print(f"Series Winner: {series['results']['series_winner']}")
    print(f"Yankees Wins: {series['results']['team1_wins']}")
    print(f"Red Sox Wins: {series['results']['team2_wins']}")
    print()
    
    # League rankings
    print("5. Top Batters (by OPS):")
    rankings = analyzer.get_league_rankings()
    for i, player in enumerate(rankings['batting_rankings'][:5], 1):
        print(f"{i}. {player['name']} - {player['ops']:.3f}")
    
    print("\nTop Batters by OPS:")
    batting_data = {player['name']: player['ops'] for player in rankings['batting_rankings']}
    batting_series = pd.Series(batting_data)
    # Ensure the function is defined before it's called, or defined globally.
    # For simplicity, assuming plot_generic_top_n is defined globally or imported.
    plot_generic_top_n(batting_series, "Top 10 Batters by OPS", "Player", "OPS")

    print("\n=== Analysis Complete ===")


if __name__ == "__main__":
    main()


def plot_generic_top_n(data_series: pd.Series, title: str, xlabel: str, ylabel: str, top_n: int = 10) -> None:
    """Displays a generic bar chart for a pandas Series in the terminal."""
    top_data = data_series.head(top_n)
    items = top_data.index.tolist()
    values = top_data.values.tolist()

    plt.clf()
    plt.bar(items, values)
    plt.title(title)
    plt.xlabel(xlabel)
    plt.ylabel(ylabel)
    plt.show()