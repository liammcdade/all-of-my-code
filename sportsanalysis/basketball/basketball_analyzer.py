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
class Player:
    """Data class for basketball player statistics."""
    name: str
    team: str
    position: str
    ppg: float  # Points per game
    rpg: float  # Rebounds per game
    apg: float  # Assists per game
    spg: float  # Steals per game
    bpg: float  # Blocks per game
    fg_pct: float  # Field goal percentage
    three_pct: float  # Three point percentage
    ft_pct: float  # Free throw percentage
    games_played: int = 0
    minutes_per_game: float = 0.0


@dataclass
class Team:
    """Data class for basketball team statistics."""
    name: str
    conference: str
    division: str
    wins: int = 0
    losses: int = 0
    win_pct: float = 0.0
    ppg: float = 0.0
    opp_ppg: float = 0.0
    pace: float = 0.0  # Possessions per game
    off_rtg: float = 0.0  # Offensive rating
    def_rtg: float = 0.0  # Defensive rating
    players: List[Player] = None

    def __post_init__(self):
        if self.players is None:
            self.players = []


@dataclass
class GameResult:
    """Data class for game results."""
    home_team: str
    away_team: str
    home_score: int
    away_score: int
    home_players: Dict[str, Dict[str, Any]]
    away_players: Dict[str, Dict[str, Any]]
    date: str
    overtime: bool = False


class BasketballSimulator:
    """Handles basketball game simulation."""
    
    @staticmethod
    def simulate_player_performance(player: Player, minutes: int = 35) -> Dict[str, Any]:
        """Simulate individual player performance for a game."""
        # Base performance based on player stats
        base_points = player.ppg * (minutes / 35)
        base_rebounds = player.rpg * (minutes / 35)
        base_assists = player.apg * (minutes / 35)
        base_steals = player.spg * (minutes / 35)
        base_blocks = player.bpg * (minutes / 35)
        
        # Add randomness
        points = max(0, int(base_points + random.gauss(0, 8)))
        rebounds = max(0, int(base_rebounds + random.gauss(0, 3)))
        assists = max(0, int(base_assists + random.gauss(0, 2)))
        steals = max(0, int(base_steals + random.gauss(0, 1)))
        blocks = max(0, int(base_blocks + random.gauss(0, 1)))
        
        # Calculate shooting stats
        fg_attempts = max(5, int(points / 2 + random.gauss(0, 3)))
        fg_made = int(fg_attempts * player.fg_pct + random.gauss(0, 0.1 * fg_attempts))
        fg_made = max(0, min(fg_made, fg_attempts))
        
        three_attempts = max(0, int(fg_attempts * 0.4 + random.gauss(0, 2)))
        three_made = int(three_attempts * player.three_pct + random.gauss(0, 0.15 * three_attempts))
        three_made = max(0, min(three_made, three_attempts))
        
        ft_attempts = max(0, int(points * 0.3 + random.gauss(0, 2)))
        ft_made = int(ft_attempts * player.ft_pct + random.gauss(0, 0.1 * ft_attempts))
        ft_made = max(0, min(ft_made, ft_attempts))
        
        return {
            'name': player.name,
            'minutes': minutes,
            'points': points,
            'rebounds': rebounds,
            'assists': assists,
            'steals': steals,
            'blocks': blocks,
            'fg_made': fg_made,
            'fg_attempts': fg_attempts,
            'three_made': three_made,
            'three_attempts': three_attempts,
            'ft_made': ft_made,
            'ft_attempts': ft_attempts,
            'turnovers': max(0, int(random.gauss(2, 1.5)))
        }
    
    @staticmethod
    def simulate_game(team1: Team, team2: Team) -> GameResult:
        """Simulate a complete basketball game."""
        # Calculate team strength based on offensive and defensive ratings
        team1_strength = (team1.off_rtg - team2.def_rtg) / 100
        team2_strength = (team2.off_rtg - team1.def_rtg) / 100
        
        # Base scores
        base_score1 = team1.ppg + random.gauss(0, 10)
        base_score2 = team2.ppg + random.gauss(0, 10)
        
        # Adjust for team strength
        score1 = max(80, int(base_score1 + team1_strength * 10))
        score2 = max(80, int(base_score2 + team2_strength * 10))
        
        # Check for overtime
        overtime = False
        if abs(score1 - score2) <= 3 and random.random() < 0.1:
            overtime = True
            ot_points1 = random.randint(5, 15)
            ot_points2 = random.randint(5, 15)
            score1 += ot_points1
            score2 += ot_points2
        
        # Simulate player performances
        home_players = {}
        away_players = {}
        
        for player in team1.players[:8]:  # Top 8 players
            minutes = random.randint(20, 40)
            home_players[player.name] = BasketballSimulator.simulate_player_performance(player, minutes)
        
        for player in team2.players[:8]:  # Top 8 players
            minutes = random.randint(20, 40)
            away_players[player.name] = BasketballSimulator.simulate_player_performance(player, minutes)
        
        return GameResult(
            home_team=team1.name,
            away_team=team2.name,
            home_score=score1,
            away_score=score2,
            home_players=home_players,
            away_players=away_players,
            date=datetime.now().strftime("%Y-%m-%d"),
            overtime=overtime
        )


class BasketballAnalyzer:
    """Analyzes basketball statistics and provides insights."""
    
    def __init__(self):
        self.players = self._load_players()
        self.teams = self._load_teams()
    
    def _load_players(self) -> List[Player]:
        """Load players from data."""
        csv_path = os.path.join(os.path.dirname(__file__), 'data', 'players', 'current_season.csv')
        if os.path.exists(csv_path):
            df = pd.read_csv(csv_path)
            return [Player(**row) for _, row in df.iterrows()]
        # fallback to hardcoded data
        return [
            Player('LeBron James', 'Los Angeles Lakers', 'SF', 25.7, 7.3, 8.1, 1.1, 0.6, 0.504, 0.321, 0.748, 55, 35.5),
            Player('Anthony Davis', 'Los Angeles Lakers', 'PF', 24.7, 12.3, 3.7, 1.2, 2.4, 0.556, 0.267, 0.793, 56, 34.0),
            Player('Austin Reaves', 'Los Angeles Lakers', 'SG', 15.9, 4.3, 5.5, 0.8, 0.3, 0.486, 0.362, 0.864, 82, 32.1),
            Player('Jayson Tatum', 'Boston Celtics', 'SF', 30.1, 8.8, 4.6, 1.0, 0.7, 0.471, 0.375, 0.831, 74, 35.7),
            Player('Jaylen Brown', 'Boston Celtics', 'SG', 23.5, 5.5, 3.6, 1.1, 0.3, 0.494, 0.355, 0.705, 70, 33.4),
            Player('Derrick White', 'Boston Celtics', 'PG', 15.2, 4.2, 5.2, 1.0, 1.2, 0.461, 0.386, 0.904, 82, 32.6),
        ]
    
    def _load_teams(self) -> List[Team]:
        """Load teams from data."""
        csv_path = os.path.join(os.path.dirname(__file__), 'data', 'teams', 'team_stats.csv')
        if os.path.exists(csv_path):
            df = pd.read_csv(csv_path)
            return [Team(**row) for _, row in df.iterrows()]
        # fallback to hardcoded data
        return [
            Team('Los Angeles Lakers', 'Western', 'Pacific', 45, 37, 0.549, 113.2, 111.8, 100.2, 113.8, 111.4),
            Team('Boston Celtics', 'Eastern', 'Atlantic', 57, 25, 0.695, 118.6, 109.2, 98.8, 118.9, 109.5),
        ]
    
    def get_team_by_name(self, name: str) -> Optional[Team]:
        """Get team by name."""
        for team in self.teams:
            if team.name == name:
                team.players = [p for p in self.players if p.team == name]
                return team
        return None
    
    def get_player_by_name(self, name: str) -> Optional[Player]:
        """Get player by name."""
        for player in self.players:
            if player.name == name:
                return player
        return None
    
    def analyze_player_performance(self, player_name: str) -> Dict[str, Any]:
        """Analyze individual player performance."""
        player = self.get_player_by_name(player_name)
        if not player:
            return {"error": "Player not found"}
        
        # Calculate advanced stats
        ts_pct = (player.ppg * 2) / (2 * (player.fg_pct * 2 + 0.44 * player.ft_pct))
        per = player.ppg + player.rpg * 1.2 + player.apg * 1.5 + player.spg * 2 + player.bpg * 2 - player.games_played * 0.5
        
        return {
            "player": asdict(player),
            "advanced_stats": {
                "true_shooting_pct": ts_pct,
                "per_estimate": per,
                "efficiency_rating": (player.ppg + player.rpg + player.apg) / 3
            },
            "rankings": {
                "ppg_rank": self._get_ppg_rank(player.ppg),
                "rpg_rank": self._get_rpg_rank(player.rpg),
                "apg_rank": self._get_apg_rank(player.apg)
            }
        }
    
    def _get_ppg_rank(self, ppg: float) -> int:
        """Get PPG ranking among all players."""
        ppg_list = [p.ppg for p in self.players]
        ppg_list.sort(reverse=True)
        return ppg_list.index(ppg) + 1 if ppg in ppg_list else len(ppg_list)
    
    def _get_rpg_rank(self, rpg: float) -> int:
        """Get RPG ranking among all players."""
        rpg_list = [p.rpg for p in self.players]
        rpg_list.sort(reverse=True)
        return rpg_list.index(rpg) + 1 if rpg in rpg_list else len(rpg_list)
    
    def _get_apg_rank(self, apg: float) -> int:
        """Get APG ranking among all players."""
        apg_list = [p.apg for p in self.players]
        apg_list.sort(reverse=True)
        return apg_list.index(apg) + 1 if apg in apg_list else len(apg_list)
    
    def get_team_analysis(self, team_name: str) -> Dict[str, Any]:
        """Analyze team performance."""
        team = self.get_team_by_name(team_name)
        if not team:
            return {"error": "Team not found"}
        
        team_players = [p for p in self.players if p.team == team_name]
        
        # Calculate team stats
        avg_ppg = statistics.mean([p.ppg for p in team_players])
        avg_rpg = statistics.mean([p.rpg for p in team_players])
        avg_apg = statistics.mean([p.apg for p in team_players])
        
        # Find top performers
        top_scorer = max(team_players, key=lambda p: p.ppg)
        top_rebounder = max(team_players, key=lambda p: p.rpg)
        top_assister = max(team_players, key=lambda p: p.apg)
        
        return {
            "team": asdict(team),
            "team_stats": {
                "avg_ppg": avg_ppg,
                "avg_rpg": avg_rpg,
                "avg_apg": avg_apg,
                "team_efficiency": (team.off_rtg - team.def_rtg)
            },
            "top_performers": {
                "top_scorer": asdict(top_scorer),
                "top_rebounder": asdict(top_rebounder),
                "top_assister": asdict(top_assister)
            },
            "player_count": len(team_players)
        }
    
    def simulate_season(self, num_games: int = 82) -> Dict[str, Any]:
        """Simulate a full season."""
        season_results = []
        team_records = {team.name: {'wins': 0, 'losses': 0} for team in self.teams}
        
        # Generate schedule
        for _ in range(num_games // 2):  # Each team plays roughly half the games
            for i, team1 in enumerate(self.teams):
                for team2 in self.teams[i+1:]:
                    if len(season_results) >= num_games:
                        break
                    
                    game = BasketballSimulator.simulate_game(team1, team2)
                    season_results.append(game)
                    
                    # Update records
                    if game.home_score > game.away_score:
                        team_records[game.home_team]['wins'] += 1
                        team_records[game.away_team]['losses'] += 1
                    else:
                        team_records[game.away_team]['wins'] += 1
                        team_records[game.home_team]['losses'] += 1
        
        return {
            "season_results": [asdict(result) for result in season_results],
            "final_standings": team_records
        }


def main():
    """Main function to demonstrate basketball analysis."""
    analyzer = BasketballAnalyzer()
    
    print("=== Basketball Analysis Tool ===\n")
    
    # Analyze a player
    print("1. Player Analysis - LeBron James:")
    player_analysis = analyzer.analyze_player_performance("LeBron James")
    print(f"PPG: {player_analysis['player']['ppg']}")
    print(f"RPG: {player_analysis['player']['rpg']}")
    print(f"APG: {player_analysis['player']['apg']}")
    print(f"PPG Rank: {player_analysis['rankings']['ppg_rank']}")
    print()
    
    # Analyze a team
    print("2. Team Analysis - Boston Celtics:")
    team_analysis = analyzer.get_team_analysis("Boston Celtics")
    print(f"Record: {team_analysis['team']['wins']}-{team_analysis['team']['losses']}")
    print(f"PPG: {team_analysis['team']['ppg']}")
    print(f"Top Scorer: {team_analysis['top_performers']['top_scorer']['name']}")
    print()
    
    # Simulate a game
    print("3. Game Simulation - Lakers vs Celtics:")
    lakers = analyzer.get_team_by_name("Los Angeles Lakers")
    celtics = analyzer.get_team_by_name("Boston Celtics")
    
    if lakers and celtics:
        game = BasketballSimulator.simulate_game(lakers, celtics)
        print(f"{game.home_team} {game.home_score} - {game.away_score} {game.away_team}")
        if game.overtime:
            print("(Overtime)")
        
        # Show top performers
        home_top = max(game.home_players.values(), key=lambda p: p['points'])
        away_top = max(game.away_players.values(), key=lambda p: p['points'])
        print(f"Top Scorer - {home_top['name']}: {home_top['points']} pts")
        print(f"Top Scorer - {away_top['name']}: {away_top['points']} pts")
    print()

    # Simulate a season and plot standings
    print("4. Season Simulation and Standings Plot:")
    season_data = analyzer.simulate_season()
    standings = season_data['final_standings']
    # Convert standings to a Series for plotting (Team: Wins)
    # Example: {'Los Angeles Lakers': {'wins': 45, 'losses': 37}, ...}
    # We want: Series({'Los Angeles Lakers': 45, ...})
    wins_data = {team: data['wins'] for team, data in standings.items()}
    wins_series = pd.Series(wins_data).sort_values(ascending=False) # Sort by wins descending

    plot_generic_top_n(wins_series, "Team Wins in Simulated Season", "Team", "Wins", top_n=len(wins_series), sort_ascending=False) # Plot all teams

    print("\nFinal Standings from Simulation:")
    for team, record in sorted(standings.items(), key=lambda item: item[1]['wins'], reverse=True):
        print(f"{team}: {record['wins']} Wins, {record['losses']} Losses")
    
    print("\n=== Analysis Complete ===")


if __name__ == "__main__":
    main()