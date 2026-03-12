"""
UEFA Champions League 2025-26 Tournament Database and Simulation System
========================================================================

This module provides a comprehensive database system for managing the UEFA Champions League
2025-26 tournament, including:
- SQL database schema for tournament data
- ELO rating system for match prediction
- Match simulation with aggregate scores
- Score tracking for all knockout rounds
- Statistical analysis of team performance
- Input functionality for actual match results
- Comparison with simulated predictions

Author: Sports Analysis System
Date: 2026
"""

import sqlite3
import random
import os
from datetime import datetime, date
from typing import Dict, List, Tuple, Optional, Any
from collections import Counter
import json

# ============================================================================
# DATABASE CONFIGURATION
# ============================================================================

DATABASE_PATH = "sportsanalysis/uefa/champions_league.db"
SCHEMA_PATH = "sportsanalysis/uefa/champions_league.sql"

# ============================================================================
# TOURNAMENT CONFIGURATION
# ============================================================================

# Round of 16 matchups (home team plays first leg at home)
ROUND_OF_16_MATCHES = [
    ("Paris Saint-Germain", "Chelsea"),
    ("Galatasaray", "Liverpool"),
    ("Real Madrid", "Manchester City"),
    ("Atalanta", "Bayern Munich"),
    ("Newcastle United", "Barcelona"),
    ("Atletico Madrid", "Tottenham Hotspur"),
    ("Bodø/Glimt", "Sporting CP"),
    ("Bayer Leverkusen", "Arsenal"),
]

# Match dates for Round of 16
ROUND_OF_16_FIRST_LEG_DATES = [
    ("Paris Saint-Germain", "Chelsea", "2026-03-11"),
    ("Galatasaray", "Liverpool", "2026-03-10"),
    ("Real Madrid", "Manchester City", "2026-03-11"),
    ("Atalanta", "Bayern Munich", "2026-03-10"),
    ("Newcastle United", "Barcelona", "2026-03-10"),
    ("Atletico Madrid", "Tottenham Hotspur", "2026-03-10"),
    ("Bodø/Glimt", "Sporting CP", "2026-03-11"),
    ("Bayer Leverkusen", "Arsenal", "2026-03-11"),
]

ROUND_OF_16_SECOND_LEG_DATES = [
    ("Chelsea", "Paris Saint-Germain", "2026-03-17"),
    ("Liverpool", "Galatasaray", "2026-03-18"),
    ("Manchester City", "Real Madrid", "2026-03-17"),
    ("Bayern Munich", "Atalanta", "2026-03-18"),
    ("Barcelona", "Newcastle United", "2026-03-18"),
    ("Tottenham Hotspur", "Atletico Madrid", "2026-03-18"),
    ("Sporting CP", "Bodø/Glimt", "2026-03-17"),
    ("Arsenal", "Bayer Leverkusen", "2026-03-17"),
]

# Quarter-finals dates
QF_FIRST_LEG_DATES = ["2026-04-07", "2026-04-08"]
QF_SECOND_LEG_DATES = ["2026-04-14", "2026-04-15"]

# Semi-finals dates
SF_FIRST_LEG_DATES = ["2026-04-28", "2026-04-29"]
SF_SECOND_LEG_DATES = ["2026-05-05", "2026-05-06"]

# Final date and venue
FINAL_DATE = "2026-05-30"
FINAL_TIME = "18:00"
FINAL_VENUE = "Puskás Aréna"
FINAL_CITY = "Budapest"
FINAL_COUNTRY = "Hungary"

# ELO Rating constants
ELO_INITIAL = 1500
ELO_K_FACTOR = 32  # K-factor for ELO updates
ELO_HOME_ADVANTAGE = 50  # Home advantage in ELO points

# ============================================================================
# DATABASE MANAGEMENT CLASS
# ============================================================================

class ChampionsLeagueDatabase:
    """Main database manager for UEFA Champions League 2025-26"""
    
    def __init__(self, db_path: str = DATABASE_PATH):
        self.db_path = db_path
        self.conn = None
        self.cursor = None
        
    def connect(self):
        """Establish database connection"""
        self.conn = sqlite3.connect(self.db_path)
        self.conn.row_factory = sqlite3.Row
        self.cursor = self.conn.cursor()
        
    def close(self):
        """Close database connection"""
        if self.conn:
            self.conn.close()
            
    def initialize_database(self):
        """Initialize database with schema"""
        # Read and execute SQL schema
        with open(SCHEMA_PATH, 'r') as f:
            schema = f.read()
        
        # Execute schema in parts (due to SQLite limitations)
        statements = schema.split(';')
        for statement in statements:
            statement = statement.strip()
            if statement:
                try:
                    self.cursor.execute(statement)
                except sqlite3.Error as e:
                    print(f"Schema execution error (may be expected): {e}")
        
        self.conn.commit()
        
    def setup_tournament(self):
        """Setup the complete tournament structure"""
        self._insert_teams()
        self._insert_venues()
        self._insert_rounds()
        self._insert_matches()
        self._insert_tournament_progress()
        
    def _insert_teams(self):
        """Insert all teams with ELO ratings"""
        teams_data = [
            # Round of 16 teams with ELO ratings
            ("Arsenal", "ARS", "England", "Premier League", 2050),
            ("Bayern Munich", "BAY", "Germany", "Bundesliga", 1992),
            ("Liverpool", "LIV", "England", "Premier League", 1947),
            ("Tottenham Hotspur", "TOT", "England", "Premier League", 1817),
            ("Barcelona", "BAR", "Spain", "La Liga", 1944),
            ("Chelsea", "CHE", "England", "Premier League", 1894),
            ("Sporting CP", "SCP", "Portugal", "Primeira Liga", 1825),
            ("Manchester City", "MCI", "England", "Premier League", 2002),
            ("Real Madrid", "RMA", "Spain", "La Liga", 1910),
            ("Paris Saint-Germain", "PSG", "France", "Ligue 1", 1968),
            ("Newcastle United", "NEW", "England", "Premier League", 1860),
            ("Atletico Madrid", "ATM", "Spain", "La Liga", 1875),
            ("Atalanta", "ATA", "Italy", "Serie A", 1802),
            ("Bayer Leverkusen", "B04", "Germany", "Bundesliga", 1856),
            ("Galatasaray", "GAL", "Turkey", "Süper Lig", 1720),
            ("Bodø/Glimt", "BOD", "Norway", "Eliteserien", 1649),
        ]
        
        self.cursor.executemany("""
            INSERT OR IGNORE INTO teams (team_name, team_short_name, country, league, elo_rating)
            VALUES (?, ?, ?, ?, ?)
        """, teams_data)
        self.conn.commit()
        
    def _insert_venues(self):
        """Insert venues including final stadium"""
        venues_data = [
            ("Puskás Aréna", "Budapest", "Hungary", 68100, 1),
            ("Parc des Princes", "Paris", "France", 47929, 0),
            ("Stamford Bridge", "London", "England", 41837, 0),
            ("Anfield", "Liverpool", "England", 53394, 0),
            ("Santiago Bernabéu", "Madrid", "Spain", 81044, 0),
            ("Allianz Arena", "Munich", "Germany", 75000, 0),
            ("Camp Nou", "Barcelona", "Spain", 99354, 0),
            ("St. James' Park", "Newcastle", "England", 52305, 0),
            ("Metropolitano", "Madrid", "England", 68456, 0),
            ("Tottenham Hotspur Stadium", "London", "England", 62850, 0),
            ("Estádio José Alvalade", "Lisbon", "Portugal", 50466, 0),
            ("BayArena", "Leverkusen", "Germany", 30210, 0),
            ("RAM Parken", "Oslo", "Norway", 1600, 0),
            ("Türk Telekom Stadyumu", "Istanbul", "Turkey", 52000, 0),
            ("Emirates Stadium", "London", "England", 60426, 0),
        ]
        
        self.cursor.executemany("""
            INSERT OR IGNORE INTO venues (venue_name, city, country, capacity, is_neutral_venue)
            VALUES (?, ?, ?, ?, ?)
        """, venues_data)
        self.conn.commit()
        
    def _insert_rounds(self):
        """Insert tournament rounds"""
        rounds_data = [
            (1, "Round of 16", "16 teams, 8 matches"),
            (2, "Quarter-finals", "8 teams, 4 matches"),
            (3, "Semi-finals", "4 teams, 2 matches"),
            (4, "Final", "2 teams, 1 match"),
        ]
        
        self.cursor.executemany("""
            INSERT OR IGNORE INTO rounds (round_order, round_name, description)
            VALUES (?, ?, ?)
        """, rounds_data)
        self.conn.commit()
        
    def _insert_matches(self):
        """Insert all tournament matches"""
        # Get team IDs
        team_map = self._get_team_map()
        venue_map = self._get_venue_map()
        
        # Round of 16 matches
        match_id = 1
        for i, (home, away) in enumerate(ROUND_OF_16_MATCHES):
            # Get dates
            first_leg_date = None
            second_leg_date = None
            
            for h, a, d in ROUND_OF_16_FIRST_LEG_DATES:
                if h == home and a == away:
                    first_leg_date = d
                    break
                    
            for h, a, d in ROUND_OF_16_SECOND_LEG_DATES:
                if h == home and a == away:
                    second_leg_date = d
                    break
            
            home_id = team_map.get(home)
            away_id = team_map.get(away)
            
            # Get venue (home team stadium)
            venue_id = self._get_team_venue(home)
            
            self.cursor.execute("""
                INSERT INTO matches (
                    round_id, match_number, home_team_id, away_team_id, venue_id,
                    first_leg_date, second_leg_date, home_advantage_applied
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """, (1, i + 1, home_id, away_id, venue_id, first_leg_date, second_leg_date, 1))
            
        self.conn.commit()
        
        # Placeholder for QF, SF, Final (to be filled after winners determined)
        
    def _get_team_map(self) -> Dict[str, int]:
        """Get team name to ID mapping"""
        self.cursor.execute("SELECT team_id, team_name FROM teams")
        return {row[1]: row[0] for row in self.cursor.fetchall()}
    
    def _get_venue_map(self) -> Dict[str, int]:
        """Get venue name to ID mapping"""
        self.cursor.execute("SELECT venue_id, venue_name FROM venues")
        return {row[1]: row[0] for row in self.cursor.fetchall()}
    
    def _get_team_venue(self, team_name: str) -> Optional[int]:
        """Get team's home venue"""
        venue_names = {
            "Paris Saint-Germain": "Parc des Princes",
            "Chelsea": "Stamford Bridge",
            "Liverpool": "Anfield",
            "Real Madrid": "Santiago Bernabéu",
            "Manchester City": "Emirates Stadium",  # Using as placeholder
            "Bayern Munich": "Allianz Arena",
            "Barcelona": "Camp Nou",
            "Newcastle United": "St. James' Park",
            "Atletico Madrid": "Metropolitano",
            "Tottenham Hotspur": "Tottenham Hotspur Stadium",
            "Sporting CP": "Estádio José Alvalade",
            "Bayer Leverkusen": "BayArena",
            "Bodø/Glimt": "RAM Parken",
            "Galatasaray": "Türk Telekom Stadyumu",
            "Arsenal": "Emirates Stadium",
        }
        
        venue_name = venue_names.get(team_name)
        if venue_name:
            self.cursor.execute("SELECT venue_id FROM venues WHERE venue_name = ?", (venue_name,))
            result = self.cursor.fetchone()
            return result[0] if result else None
        return None
        
    def _insert_tournament_progress(self):
        """Initialize tournament progress"""
        self.cursor.execute("""
            INSERT INTO tournament_progress (current_round_id, round_complete, final_complete)
            VALUES (1, 0, 0)
        """)
        self.conn.commit()
        
    def get_matches(self, round_name: Optional[str] = None) -> List[Dict]:
        """Get matches, optionally filtered by round"""
        if round_name:
            query = """
                SELECT m.*, r.round_name, ht.team_name as home_team, at.team_name as away_team
                FROM matches m
                JOIN rounds r ON m.round_id = r.round_id
                JOIN teams ht ON m.home_team_id = ht.team_id
                JOIN teams at ON m.away_team_id = at.team_id
                WHERE r.round_name = ?
                ORDER BY m.match_number
            """
            self.cursor.execute(query, (round_name,))
        else:
            query = """
                SELECT m.*, r.round_name, ht.team_name as home_team, at.team_name as away_team
                FROM matches m
                JOIN rounds r ON m.round_id = r.round_id
                JOIN teams ht ON m.home_team_id = ht.team_id
                JOIN teams at ON m.away_team_id = at.team_id
                ORDER BY r.round_order, m.match_number
            """
            self.cursor.execute(query)
            
        return [dict(row) for row in self.cursor.fetchall()]
    
    def get_team_elo(self, team_name: str) -> int:
        """Get current ELO rating for a team"""
        self.cursor.execute("SELECT elo_rating FROM teams WHERE team_name = ?", (team_name,))
        result = self.cursor.fetchone()
        return result[0] if result else ELO_INITIAL
        
    def update_team_elo(self, team_name: str, new_elo: int):
        """Update team's ELO rating"""
        self.cursor.execute("""
            UPDATE teams SET elo_rating = ?, updated_at = CURRENT_TIMESTAMP 
            WHERE team_name = ?
        """, (new_elo, team_name))
        self.conn.commit()
        
    def record_elo_change(self, team_name: str, match_id: int, old_elo: int, new_elo: int):
        """Record ELO change in history"""
        self.cursor.execute("SELECT team_id FROM teams WHERE team_name = ?", (team_name,))
        team_id = self.cursor.fetchone()[0]
        
        self.cursor.execute("""
            INSERT INTO elo_history (team_id, match_id, old_elo, new_elo, elo_change)
            VALUES (?, ?, ?, ?, ?)
        """, (team_id, match_id, old_elo, new_elo, new_elo - old_elo))
        self.conn.commit()
        
    def record_actual_result(self, match_id: int, home_goals: int, away_goals: int, 
                            home_goals_2nd: int = None, away_goals_2nd: int = None,
                            penalty_winner: str = None):
        """Record actual match result"""
        # Get match details
        self.cursor.execute("""
            SELECT home_team_id, away_team_id, round_id FROM matches WHERE match_id = ?
        """, (match_id,))
        match = self.cursor.fetchone()
        
        if not match:
            raise ValueError(f"Match {match_id} not found")
            
        home_id, away_id, round_id = match
        
        # Determine winner
        if round_id in [1, 2, 3]:  # Knockout rounds with two legs
            if home_goals_2nd is not None and away_goals_2nd is not None:
                total_home = home_goals + home_goals_2nd
                total_away = away_goals + away_goals_2nd
                
                # Update match with both legs
                self.cursor.execute("""
                    UPDATE matches SET 
                        first_leg_home_goals = ?,
                        first_leg_away_goals = ?,
                        second_leg_home_goals = ?,
                        second_leg_away_goals = ?,
                        aggregate_home_goals = ?,
                        aggregate_away_goals = ?,
                        is_completed = 1,
                        is_draw = ?
                    WHERE match_id = ?
                """, (home_goals, away_goals, home_goals_2nd, away_goals_2nd,
                      total_home, total_away, 1 if total_home == total_away else 0,
                      match_id))
                
                # Determine winner
                if total_home > total_away:
                    winner_id = home_id
                elif total_away > total_home:
                    winner_id = away_id
                else:
                    # Draw - check for penalty winner
                    if penalty_winner:
                        self.cursor.execute("""
                            SELECT team_id FROM teams WHERE team_name = ?
                        """, (penalty_winner,))
                        winner_result = self.cursor.fetchone()
                        winner_id = winner_result[0] if winner_result else home_id
                        self.cursor.execute("""
                            UPDATE matches SET decided_on_penalties = 1,
                            penalty_shootout_home_score = 4, penalty_shootout_away_score = 3
                            WHERE match_id = ?
                        """, (match_id,))
                    else:
                        winner_id = home_id  # Default to home team
                        
                self.cursor.execute("""
                    UPDATE matches SET winner_team_id = ? WHERE match_id = ?
                """, (winner_id, match_id))
        else:
            # Single match (Final)
            is_draw = 1 if home_goals == away_goals else 0
            winner_id = home_id if home_goals > away_goals else (away_id if away_goals > home_id else None)
            
            if is_draw and penalty_winner:
                self.cursor.execute("""
                    SELECT team_id FROM teams WHERE team_name = ?
                """, (penalty_winner,))
                winner_result = self.cursor.fetchone()
                winner_id = winner_result[0] if winner_result else home_id
                self.cursor.execute("""
                    UPDATE matches SET decided_on_penalties = 1,
                    penalty_shootout_home_score = 4, penalty_shootout_away_score = 3
                    WHERE match_id = ?
                """, (match_id,))
                
            self.cursor.execute("""
                UPDATE matches SET 
                    first_leg_home_goals = ?,
                    first_leg_away_goals = ?,
                    aggregate_home_goals = ?,
                    aggregate_away_goals = ?,
                    is_completed = 1,
                    is_draw = ?,
                    winner_team_id = ?
                WHERE match_id = ?
            """, (home_goals, away_goals, home_goals, away_goals, is_draw, winner_id, match_id))
            
        # Record actual result
        self.cursor.execute("""
            INSERT INTO actual_results (match_id, actual_home_goals, actual_away_goals, actual_winner_id)
            VALUES (?, ?, ?, ?)
        """, (match_id, home_goals, away_goals, winner_id))
        
        # Update ELO ratings
        self._update_elo_ratings(match_id, home_id, away_id, home_goals, away_goals, 
                                home_goals_2nd, away_goals_2nd)
        
        self.conn.commit()
        
    def _update_elo_ratings(self, match_id: int, home_id: int, away_id: int,
                           home_goals: int, away_goals: int,
                           home_goals_2nd: int = None, away_goals_2nd: int = None):
        """Update ELO ratings after match"""
        # Get team names
        self.cursor.execute("SELECT team_name FROM teams WHERE team_id = ?", (home_id,))
        home_name = self.cursor.fetchone()[0]
        
        self.cursor.execute("SELECT team_name FROM teams WHERE team_id = ?", (away_id,))
        away_name = self.cursor.fetchone()[0]
        
        # Get current ELOs
        home_elo = self.get_team_elo(home_name)
        away_elo = self.get_team_elo(away_name)
        
        # Calculate expected scores
        home_expected = 1 / (1 + 10 ** ((away_elo - home_elo - ELO_HOME_ADVANTAGE) / 400))
        away_expected = 1 / (1 + 10 ** ((home_elo - away_elo + ELO_HOME_ADVANTAGE) / 400))
        
        # Determine actual scores
        if home_goals_2nd is not None:
            total_home = home_goals + home_goals_2nd
            total_away = away_goals + away_goals_2nd
        else:
            total_home = home_goals
            total_away = away_goals
            
        # Calculate result (1 for win, 0.5 for draw, 0 for loss)
        if total_home > total_away:
            home_actual = 1
            away_actual = 0
        elif total_away > total_home:
            home_actual = 0
            away_actual = 1
        else:
            home_actual = 0.5
            away_actual = 0.5
            
        # Update ELO
        new_home_elo = home_elo + ELO_K_FACTOR * (home_actual - home_expected)
        new_away_elo = away_elo + ELO_K_FACTOR * (away_actual - away_expected)
        
        self.update_team_elo(home_name, int(new_home_elo))
        self.update_team_elo(away_name, int(new_away_elo))
        
        # Record history
        self.record_elo_change(home_name, match_id, home_elo, int(new_home_elo))
        self.record_elo_change(away_name, match_id, away_elo, int(new_away_elo))


# ============================================================================
# ELO RATING SYSTEM
# ============================================================================

class ELORatingSystem:
    """ELO rating system for match prediction"""
    
    def __init__(self, db: ChampionsLeagueDatabase):
        self.db = db
        
    def calculate_win_probability(self, home_team: str, away_team: str) -> Tuple[float, float]:
        """
        Calculate win probability for a match using ELO ratings.
        Returns (home_win_prob, away_win_prob)
        """
        home_elo = self.db.get_team_elo(home_team)
        away_elo = self.db.get_team_elo(away_team)
        
        # Adjust for home advantage
        home_elo_adjusted = home_elo + ELO_HOME_ADVANTAGE
        
        # Calculate probability
        dr = home_elo_adjusted - away_elo
        home_win_prob = 1 / (1 + (10 ** (-dr / 400)))
        
        # Draw probability (simplified)
        draw_prob = 0.25  # Base draw probability
        away_win_prob = (1 - home_win_prob) - draw_prob
        
        # Normalize to ensure they sum to 1
        total = home_win_prob + away_win_prob + draw_prob
        home_win_prob /= total
        away_win_prob /= total
        draw_prob /= total
        
        return home_win_prob, away_win_prob
    
    def predict_match_score(self, home_team: str, away_team: str) -> Tuple[int, int]:
        """
        Predict most likely score based on ELO difference.
        Returns (home_goals, away_goals)
        """
        home_win_prob, away_win_prob = self.calculate_win_probability(home_team, away_team)
        
        # Generate likely scores based on probabilities
        if random.random() < home_win_prob:
            # Home win
            home_goals = random.choices([1, 2, 3, 4], weights=[0.4, 0.35, 0.15, 0.1])[0]
            away_goals = random.randint(0, max(0, home_goals - 1))
        elif random.random() < (away_win_prob / (away_win_prob + 0.25)):
            # Away win
            away_goals = random.choices([1, 2, 3, 4], weights=[0.4, 0.35, 0.15, 0.1])[0]
            home_goals = random.randint(0, max(0, away_goals - 1))
        else:
            # Draw
            home_goals = random.randint(0, 2)
            away_goals = home_goals
            
        return home_goals, away_goals
    
    def get_team_strength_rating(self, team_name: str) -> Dict[str, Any]:
        """Get detailed strength rating for a team"""
        elo = self.db.get_team_elo(team_name)
        
        # Categorize strength
        if elo >= 2000:
            category = "Elite"
        elif elo >= 1900:
            category = "Top Tier"
        elif elo >= 1800:
            category = "Strong"
        elif elo >= 1700:
            category = "Above Average"
        elif elo >= 1600:
            category = "Average"
        else:
            category = "Below Average"
            
        return {
            "team": team_name,
            "elo_rating": elo,
            "category": category,
            "percentile": min(100, max(0, ((elo - 1000) / 1200) * 100))
        }


# ============================================================================
# MATCH SIMULATION
# ============================================================================

class MatchSimulator:
    """Match simulation with ELO-based predictions"""
    
    def __init__(self, db: ChampionsLeagueDatabase):
        self.db = db
        self.elo_system = ELORatingSystem(db)
        
    def simulate_match(self, home_team: str, away_team: str, is_neutral: bool = False) -> Tuple[int, int, str]:
        """
        Simulate a single match.
        Returns (home_goals, away_goals, result)
        """
        home_elo = self.db.get_team_elo(home_team)
        away_elo = self.db.get_team_elo(away_team)
        
        if not is_neutral:
            home_elo += ELO_HOME_ADVANTAGE
            
        dr = home_elo - away_elo
        home_win_prob = 1 / (1 + (10 ** (-dr / 400)))
        
        # Simulate goals
        if random.random() < home_win_prob:
            # Home win
            home_goals = random.choices([1, 2, 3, 4, 5], weights=[0.35, 0.3, 0.2, 0.1, 0.05])[0]
            away_goals = random.randint(0, max(0, home_goals - 1))
            result = "HOME_WIN"
        elif random.random() < 0.28:  # Draw probability
            home_goals = random.randint(0, 2)
            away_goals = home_goals
            result = "DRAW"
        else:
            # Away win
            away_goals = random.choices([1, 2, 3, 4, 5], weights=[0.35, 0.3, 0.2, 0.1, 0.05])[0]
            home_goals = random.randint(0, max(0, away_goals - 1))
            result = "AWAY_WIN"
            
        return home_goals, away_goals, result
    
    def simulate_knockout_pair(self, home_team: str, away_team: str) -> Tuple[str, Dict]:
        """
        Simulate a two-legged knockout tie.
        Returns (winner, {match_details})
        """
        # First leg (home_team at home)
        leg1_home, leg1_away, _ = self.simulate_match(home_team, away_team)
        
        # Second leg (away_team at home)
        leg2_home, leg2_away, _ = self.simulate_match(away_team, home_team)
        
        # Aggregate
        total_home = leg1_home + leg2_away  # Original home team total
        total_away = leg1_away + leg2_home  # Original away team total
        
        # Determine winner
        if total_home > total_away:
            winner = home_team
        elif total_away > total_home:
            winner = away_team
        else:
            # Extra time / Penalties - 50/50
            winner = home_team if random.random() < 0.5 else away_team
            
        details = {
            "leg1_home_team": home_team,
            "leg1_away_team": away_team,
            "leg1_score": f"{leg1_home}-{leg1_away}",
            "leg2_home_team": away_team,
            "leg2_away_team": home_team,
            "leg2_score": f"{leg2_home}-{leg2_away}",
            "aggregate": f"{total_home}-{total_away}",
            "winner": winner,
            "required_extra_time": total_home == total_away
        }
        
        return winner, details
    
    def simulate_final(self, team1: str, team2: str) -> Tuple[str, int, int]:
        """
        Simulate final match (single game, neutral venue).
        Returns (winner, goals_home, goals_away)
        """
        goals_home, goals_away, _ = self.simulate_match(team1, team2, is_neutral=True)
        
        if goals_home > goals_away:
            winner = team1
        elif goals_away > goals_home:
            winner = team2
        else:
            # Penalties
            winner = team1 if random.random() < 0.5 else team2
            
        return winner, goals_home, goals_away


# ============================================================================
# TOURNAMENT SIMULATION
# ============================================================================

class TournamentSimulator:
    """Complete tournament simulation with statistics"""
    
    def __init__(self, db: ChampionsLeagueDatabase, num_simulations: int = 10000):
        self.db = db
        self.num_simulations = num_simulations
        self.simulator = MatchSimulator(db)
        
    def run_simulation(self) -> Dict:
        """Run full tournament simulation"""
        results = {team: {
            'Round of 16': 0, 
            'Quarter-finals': 0, 
            'Semi-finals': 0, 
            'Final': 0, 
            'Winner': 0
        } for team in self._get_all_teams()}
        
        round_of_16_scores = {}
        quarterfinal_scores = {}
        semifinal_scores = {}
        final_scores = []
        
        for _ in range(self.num_simulations):
            # Run Round of 16
            ro16_winners = self._simulate_round_of_16(round_of_16_scores)
            
            # Update results
            for winner in ro16_winners:
                results[winner]['Quarter-finals'] += 1
                
            # Run Quarter-finals
            qf_winners = self._simulate_quarterfinals(ro16_winners, quarterfinal_scores)
            
            for winner in qf_winners:
                results[winner]['Semi-finals'] += 1
                
            # Run Semi-finals
            sf_winners = self._simulate_semifinals(qf_winners, semifinal_scores)
            
            for winner in sf_winners:
                results[winner]['Final'] += 1
                
            # Run Final
            final_winner, final_home, final_away = self._simulate_final(sf_winners[0], sf_winners[1])
            results[final_winner]['Winner'] += 1
            final_scores.append((final_home, final_away))
            
        # Calculate percentages
        for team in results:
            for round_name in list(results[team].keys()):
                results[team][f'{round_name}_pct'] = (results[team][round_name] / self.num_simulations) * 100
                
        return {
            'results': results,
            'round_of_16_scores': round_of_16_scores,
            'quarterfinal_scores': quarterfinal_scores,
            'semifinal_scores': semifinal_scores,
            'final_scores': final_scores
        }
    
    def _get_all_teams(self) -> List[str]:
        """Get all team names"""
        self.db.cursor.execute("SELECT team_name FROM teams")
        return [row[0] for row in self.db.cursor.fetchall()]
    
    def _simulate_round_of_16(self, score_tracking: Dict) -> List[str]:
        """Simulate Round of 16"""
        winners = []
        
        for home, away in ROUND_OF_16_MATCHES:
            winner, details = self.simulator.simulate_knockout_pair(home, away)
            winners.append(winner)
            
            # Track scores
            match_key = (home, away)
            if match_key not in score_tracking:
                score_tracking[match_key] = []
            score_tracking[match_key].append(details['aggregate'])
            
        return winners
    
    def _simulate_quarterfinals(self, ro16_winners: List[str], score_tracking: Dict) -> List[str]:
        """Simulate Quarter-finals"""
        # Pair winners: (R16-1 vs R16-2), (R16-3 vs R16-4), etc.
        qf_pairs = [
            (ro16_winners[0], ro16_winners[1]),
            (ro16_winners[2], ro16_winners[3]),
            (ro16_winners[4], ro16_winners[5]),
            (ro16_winners[6], ro16_winners[7]),
        ]
        
        winners = []
        for home, away in qf_pairs:
            winner, details = self.simulator.simulate_knockout_pair(home, away)
            winners.append(winner)
            
            match_key = (home, away)
            if match_key not in score_tracking:
                score_tracking[match_key] = []
            score_tracking[match_key].append(details['aggregate'])
            
        return winners
    
    def _simulate_semifinals(self, qf_winners: List[str], score_tracking: Dict) -> List[str]:
        """Simulate Semi-finals"""
        sf_pairs = [
            (qf_winners[0], qf_winners[1]),
            (qf_winners[2], qf_winners[3]),
        ]
        
        winners = []
        for home, away in sf_pairs:
            winner, details = self.simulator.simulate_knockout_pair(home, away)
            winners.append(winner)
            
            match_key = (home, away)
            if match_key not in score_tracking:
                score_tracking[match_key] = []
            score_tracking[match_key].append(details['aggregate'])
            
        return winners
    
    def _simulate_final(self, team1: str, team2: str) -> Tuple[str, int, int]:
        """Simulate Final"""
        return self.simulator.simulate_final(team1, team2)
    
    def get_most_likely_score(self, scores: List[str]) -> Tuple[str, float]:
        """Get most likely aggregate score"""
        if not scores:
            return "0-0", 0.0
            
        score_counts = Counter(scores)
        most_common = score_counts.most_common(1)[0]
        return most_common[0], (most_common[1] / len(scores)) * 100
    
    def get_average_score(self, scores: List[str]) -> Tuple[float, float]:
        """Get average goals for each team"""
        if not scores:
            return 0.0, 0.0
            
        total_home = 0
        total_away = 0
        
        for score in scores:
            home, away = score.split('-')
            total_home += int(home)
            total_away += int(away)
            
        return total_home / len(scores), total_away / len(scores)


# ============================================================================
# STATISTICAL ANALYSIS
# ============================================================================

class StatisticalAnalyzer:
    """Statistical analysis of tournament and team performance"""
    
    def __init__(self, db: ChampionsLeagueDatabase):
        self.db = db
        
    def get_team_statistics(self, team_name: str) -> Dict:
        """Get comprehensive statistics for a team"""
        # Get ELO rating
        elo = self.db.get_team_elo(team_name)
        
        # Get ELO history
        self.db.cursor.execute("""
            SELECT old_elo, new_elo, elo_change, recorded_at
            FROM elo_history eh
            JOIN teams t ON eh.team_id = t.team_id
            WHERE t.team_name = ?
            ORDER BY recorded_at DESC
            LIMIT 10
        """, (team_name,))
        
        elo_history = [dict(row) for row in self.db.cursor.fetchall()]
        
        # Get match results
        self.db.cursor.execute("""
            SELECT m.match_id, r.round_name, 
                   ht.team_name as home_team, at.team_name as away_team,
                   m.first_leg_home_goals, m.first_leg_away_goals,
                   m.second_leg_home_goals, m.second_leg_away_goals,
                   m.winner_team_id, m.is_completed
            FROM matches m
            JOIN rounds r ON m.round_id = r.round_id
            JOIN teams ht ON m.home_team_id = ht.team_id
            JOIN teams at ON m.away_team_id = at.team_id
            WHERE ht.team_name = ? OR at.team_name = ?
            ORDER BY r.round_order, m.match_number
        """, (team_name, team_name))
        
        matches = []
        wins = 0
        losses = 0
        draws = 0
        goals_scored = 0
        goals_conceded = 0
        
        for row in self.db.cursor.fetchall():
            match = dict(row)
            is_home = match['home_team'] == team_name
            
            if match['is_completed']:
                if is_home:
                    goals_scored += match['first_leg_home_goals'] or 0
                    goals_conceded += match['first_leg_away_goals'] or 0
                    if match['second_leg_home_goals']:
                        goals_scored += match['second_leg_home_goals']
                        goals_conceded += match['second_leg_away_goals']
                else:
                    goals_scored += match['first_leg_away_goals'] or 0
                    goals_conceded += match['first_leg_home_goals'] or 0
                    if match['second_leg_away_goals']:
                        goals_scored += match['second_leg_away_goals']
                        goals_conceded += match['second_leg_home_goals']
                        
                if match['winner_team_id']:
                    self.db.cursor.execute("SELECT team_name FROM teams WHERE team_id = ?", 
                                          (match['winner_team_id'],))
                    winner = self.db.cursor.fetchone()[0]
                    if winner == team_name:
                        wins += 1
                    else:
                        losses += 1
                else:
                    draws += 1
                    
            matches.append(match)
            
        return {
            'team': team_name,
            'elo_rating': elo,
            'elo_history': elo_history,
            'matches': matches,
            'record': {'wins': wins, 'losses': losses, 'draws': draws},
            'goals': {'scored': goals_scored, 'conceded': goals_conceded},
            'goal_difference': goals_scored - goals_conceded
        }
    
    def get_tournament_statistics(self) -> Dict:
        """Get overall tournament statistics"""
        # Total matches
        self.db.cursor.execute("SELECT COUNT(*) FROM matches")
        total_matches = self.db.cursor.fetchone()[0]
        
        # Completed matches
        self.db.cursor.execute("SELECT COUNT(*) FROM matches WHERE is_completed = 1")
        completed_matches = self.db.cursor.fetchone()[0]
        
        # Total goals
        self.db.cursor.execute("""
            SELECT SUM(COALESCE(first_leg_home_goals, 0) + COALESCE(second_leg_home_goals, 0) +
                       COALESCE(first_leg_away_goals, 0) + COALESCE(second_leg_away_goals, 0))
            FROM matches WHERE is_completed = 1
        """)
        total_goals = self.db.cursor.fetchone()[0] or 0
        
        # Top scorers (teams with highest ELO)
        self.db.cursor.execute("""
            SELECT team_name, elo_rating FROM teams ORDER BY elo_rating DESC LIMIT 10
        """)
        top_teams = [dict(row) for row in self.db.cursor.fetchall()]
        
        # Recent results
        self.db.cursor.execute("""
            SELECT m.match_id, r.round_name,
                   ht.team_name as home_team, at.team_name as away_team,
                   m.aggregate_home_goals, m.aggregate_away_goals,
                   m.is_completed
            FROM matches m
            JOIN rounds r ON m.round_id = r.round_id
            JOIN teams ht ON m.home_team_id = ht.team_id
            JOIN teams at ON m.away_team_id = at.team_id
            WHERE m.is_completed = 1
            ORDER BY m.match_id DESC
            LIMIT 10
        """)
        recent_results = [dict(row) for row in self.db.cursor.fetchall()]
        
        return {
            'total_matches': total_matches,
            'completed_matches': completed_matches,
            'remaining_matches': total_matches - completed_matches,
            'total_goals': total_goals,
            'average_goals': total_goals / completed_matches if completed_matches > 0 else 0,
            'top_teams': top_teams,
            'recent_results': recent_results
        }
    
    def compare_prediction_with_actual(self, match_id: int, simulation_results: Dict) -> Dict:
        """Compare simulated prediction with actual result"""
        # Get actual result
        self.db.cursor.execute("""
            SELECT actual_home_goals, actual_away_goals, actual_winner_id
            FROM actual_results WHERE match_id = ?
        """, (match_id,))
        
        actual = self.db.cursor.fetchone()
        if not actual:
            return {"error": "No actual result recorded for this match"}
            
        actual_home, actual_away, actual_winner_id = actual
        
        # Get match details
        self.db.cursor.execute("""
            SELECT home_team_id, away_team_id FROM matches WHERE match_id = ?
        """, (match_id,))
        match = self.db.cursor.fetchone()
        
        # Get team names
        self.db.cursor.execute("SELECT team_name FROM teams WHERE team_id = ?", (match[0],))
        home_team = self.db.cursor.fetchone()[0]
        
        self.db.cursor.execute("SELECT team_name FROM teams WHERE team_id = ?", (match[1],))
        away_team = self.db.cursor.fetchone()[0]
        
        # Get predicted result (from simulation)
        predicted_winner = None
        predicted_home = None
        predicted_away = None
        
        # Find prediction in simulation results
        round_name = self._get_round_for_match(match_id)
        
        return {
            'match_id': match_id,
            'home_team': home_team,
            'away_team': away_team,
            'round': round_name,
            'actual': {
                'home_goals': actual_home,
                'away_goals': actual_away,
                'winner_id': actual_winner_id
            },
            'predicted': {
                'home_goals': predicted_home,
                'away_goals': predicted_away,
                'winner': predicted_winner
            },
            'prediction_correct': predicted_winner == actual_winner_id if predicted_winner else None
        }
    
    def _get_round_for_match(self, match_id: int) -> str:
        """Get round name for a match"""
        self.db.cursor.execute("""
            SELECT r.round_name FROM matches m
            JOIN rounds r ON m.round_id = r.round_id
            WHERE m.match_id = ?
        """, (match_id,))
        return self.db.cursor.fetchone()[0]


# ============================================================================
# MAIN FUNCTIONS
# ============================================================================

def initialize_database(db_path: str = DATABASE_PATH) -> ChampionsLeagueDatabase:
    """Initialize the tournament database"""
    db = ChampionsLeagueDatabase(db_path)
    db.connect()
    db.initialize_database()
    db.setup_tournament()
    return db


def run_full_simulation(db: ChampionsLeagueDatabase, num_simulations: int = 10000) -> Dict:
    """Run full tournament simulation and return results"""
    simulator = TournamentSimulator(db, num_simulations)
    return simulator.run_simulation()


def print_bracket():
    """Print the tournament bracket"""
    print("\n" + "="*80)
    print("UEFA CHAMPIONS LEAGUE 2025-26 KNOCKOUT STAGE BRACKET")
    print("="*80)
    
    print("\n### Round of 16 (First Leg: March 10-11, 2026 | Second Leg: March 17-18, 2026)")
    print("-"*80)
    
    for i, (home, away) in enumerate(ROUND_OF_16_MATCHES, 1):
        print(f"Match {i}: {home} vs {away}")
        
    print("\n### Quarter-finals (First Leg: April 7-8, 2026 | Second Leg: April 14-15, 2026)")
    print("-"*80)
    print("QF1: Winner R16-1 vs Winner R16-2")
    print("QF2: Winner R16-3 vs Winner R16-4")
    print("QF3: Winner R16-5 vs Winner R16-6")
    print("QF4: Winner R16-7 vs Winner R16-8")
    
    print("\n### Semi-finals (First Leg: April 28-29, 2026 | Second Leg: May 5-6, 2026)")
    print("-"*80)
    print("SF1: Winner QF1 vs Winner QF2")
    print("SF2: Winner QF3 vs Winner QF4")
    
    print("\n### Final (May 30, 2026, 18:00 UTC+2)")
    print("-"*80)
    print(f"Venue: {FINAL_VENUE}, {FINAL_CITY}, {FINAL_COUNTRY}")
    print("SF1 Winner vs SF2 Winner")
    print("="*80 + "\n")


def main():
    """Main function to demonstrate the system"""
    print("Initializing UEFA Champions League 2025-26 Database...")
    
    # Initialize database
    db = initialize_database()
    
    # Print bracket
    print_bracket()
    
    # Get matches
    print("\n### Tournament Matches")
    matches = db.get_matches()
    
    for match in matches:
        print(f"Round: {match['round_name']}, Match: {match['home_team']} vs {match['away_team']}")
    
    # Get ELO ratings
    print("\n### Team ELO Ratings")
    elo_system = ELORatingSystem(db)
    
    for home, away in ROUND_OF_16_MATCHES[:3]:
        prob_home, prob_away = elo_system.calculate_win_probability(home, away)
        print(f"{home} vs {away}")
        print(f"  Home win: {prob_home*100:.1f}%, Away win: {prob_away*100:.1f}%")
    
    # Run simulation
    print("\n### Running Tournament Simulation (1000 simulations)...")
    results = run_full_simulation(db, 1000)
    
    # Print winning probabilities
    print("\n### Win Probabilities")
    for team, data in sorted(results['results'].items(), 
                             key=lambda x: x[1]['Winner'], reverse=True)[:10]:
        if data['Winner'] > 0:
            print(f"{team}: {data['Winner_pct']:.2f}%")
    
    # Get statistics
    print("\n### Tournament Statistics")
    analyzer = StatisticalAnalyzer(db)
    stats = analyzer.get_tournament_statistics()
    print(f"Total matches: {stats['total_matches']}")
    print(f"Completed: {stats['completed_matches']}")
    print(f"Remaining: {stats['remaining_matches']}")
    
    print("\n### Top Teams by ELO")
    for team in stats['top_teams'][:5]:
        print(f"  {team['team_name']}: {team['elo_rating']}")
    
    db.close()
    
    print("\n✓ Database and simulation system ready!")
    return db, results


if __name__ == "__main__":
    db, results = main()
