import random
from itertools import combinations
import math
from collections import defaultdict
from typing import Dict, List, Tuple

import numpy as np
from tqdm import tqdm

PL_UEL_TEAMS = ["Bournemouth", "Sunderland", "Crystal Palace"]

class EuropaLeagueSwissModel:
    def __init__(self):
        # Teams already confirmed for UEL league phase
        self.confirmed_teams = [
            # Conference League winners
            "Crystal Palace",
            # England
            "Bournemouth", "Sunderland",
            # Italy
            "Milan", "Juventus",
            # Spain
            "Real Sociedad", "Celta Vigo",
            # Germany
            "Bayer Leverkusen", "TSG Hoffenheim",
            # France
            "Marseille", "Rennes",
            # Netherlands
            "AZ Alkmaar",
            # Portugal
            "Torreense",
            # From CL (already decided losers)
            "Celtic", "Hapoel Be'er Sheva", "NEC Nijmegen",
            # Other CL drop-downs
            "Union Saint-Gilloise", "Sparta Prague", "Olympiacos", "Sturm Graz",
        ]
        
        self.uel_playoff_matches = {
            'UEL Play-off Round': [
                {'team1': 'Anderlecht', 'team2': 'Kairat Almaty', 'leg1': '3-0', 'leg2_date': '27 Aug'},
                {'team1': 'Jagiellonia Białystok', 'team2': 'Iberia 1999', 'leg1': '4-0', 'leg2_date': '27 Aug'},
                {'team1': 'Red Bull Salzburg', 'team2': 'Mjällby', 'leg1': '1-0', 'leg2_date': '27 Aug'},
                {'team1': 'Ferencváros', 'team2': 'Trabzonspor', 'leg1': '1-0', 'leg2_date': '27 Aug'},
                {'team1': 'Universitatea Craiova', 'team2': 'Ararat-Armenia', 'leg1': '1-1', 'leg2_date': '27 Aug'},
                {'team1': 'Lillestrøm', 'team2': 'Egnatia', 'leg1': '0-0', 'leg2_date': '27 Aug'},
                {'team1': 'Beşiktaş', 'team2': 'Kauno Žalgiris', 'leg1': '3-0', 'leg2_date': '27 Aug'},
                {'team1': 'Lech Poznań', 'team2': 'Thun', 'leg1': '7-0', 'leg2_date': '27 Aug'},
                {'team1': 'Sint-Truiden', 'team2': 'Omonia', 'leg1': '1-0', 'leg2_date': '27 Aug'},
                {'team1': 'Crvena zvezda', 'team2': 'Viktoria Plzeň', 'leg1': '3-0', 'leg2_date': '27 Aug'},
                {'team1': 'OFI Crete', 'team2': 'CSKA Sofia', 'leg1': '3-0', 'leg2_date': '27 Aug'},
                {'team1': 'Benfica', 'team2': 'AGF Aarhus', 'leg1': '3-1', 'leg2_date': '27 Aug'},
            ]
        }
        
        self.cl_playoff_matches = {
            'CL Play-off Round (losers drop to UEL)': [
                {'team1': 'AEK Athens', 'team2': 'Levski Sofia', 'leg1': '0-0', 'leg2_date': '26 Aug'},
                {'team1': 'Viking FK', 'team2': 'Dinamo Zagreb', 'leg1': '2-2', 'leg2_date': '26 Aug'},
                {'team1': 'NK Celje', 'team2': 'ŠK Slovan Bratislava', 'leg1': '1-1', 'leg2_date': '26 Aug'},
                {'team1': 'Olympique Lyonnais', 'team2': 'Fenerbahçe', 'leg1': '1-1', 'leg2_date': '26 Aug'},
            ]
        }
        
        self.BETTING_MARKETS = {
            "UEL Winner": {
    "Juventus": (5, 1),
    "Bayer Leverkusen": (6, 1),
    "Milan": (7, 1),
    "Marseille": (10, 1),
    "Real Sociedad": (12, 1),
    "Benfica": (14, 1),
    "Olympique Lyonnais": (16, 1),
    "Red Bull Salzburg": (20, 1),
    "Fenerbahçe": (20, 1),
    "Rennes": (25, 1),
    "Crystal Palace": (28, 1),
    "Bournemouth": (33, 1),
    "Beşiktaş": (33, 1),
    "AZ Alkmaar": (40, 1),
    "Celtic": (40, 1),
    "Crvena zvezda": (50, 1),
    "TSG Hoffenheim": (50, 1),
    "Anderlecht": (66, 1),
    "Sunderland": (66, 1),
    "Celta Vigo": (66, 1),
    "Ferencváros": (80, 1),
    "Lech Poznań": (100, 1),
    "Dinamo Zagreb": (100, 1),
    "Sparta Prague": (100, 1),
    "Jagiellonia Białystok": (125, 1),
    "Union Saint-Gilloise": (150, 1),
    "Olympiacos": (150, 1),
    "NEC Nijmegen": (200, 1),
    "Sturm Graz": (250, 1),
    "Hapoel Be'er Sheva": (300, 1),
    "Universitatea Craiova": (400, 1),
    "Lillestrøm": (400, 1),
    "Ararat-Armenia": (500, 1),
    "Egnatia": (500, 1),
    "Trabzonspor": (500, 1),
    "Mjällby": (500, 1),
    "AGF Aarhus": (750, 1),
    "CSKA Sofia": (1000, 1),
    "Kauno Žalgiris": (1000, 1),
    "Kairat Almaty": (1000, 1),
    "Thun": (1500, 1),
    "Iberia 1999": (1500, 1)
}

        }
        
        self.team_elo = {}
        self.standings = {}
        self.fixtures = []
        self.results = []
    
    def fractional_to_probability(self, odds_tuple):
        """Convert fractional odds to implied probability"""
        numerator, denominator = odds_tuple
        return denominator / (numerator + denominator)
    
    def probability_to_elo(self, prob, base_elo=1500):
        """Convert win probability to Elo rating relative to average team"""
        if prob <= 0 or prob >= 1:
            return base_elo
        
        # Using logistic function inverse: Elo = base_elo - 400 * log10((1-p)/p)
        elo_diff = -400 * math.log10((1 - prob) / prob)
        return base_elo + elo_diff
    
    def calculate_elo_ratings(self):
        """Calculate Elo ratings for all teams based on betting odds"""
        print("\n" + "=" * 80)
        print("CALCULATING ELO RATINGS FROM BETTING ODDS")
        print("=" * 80)
        
        # Get probabilities for all teams
        winner_odds = self.BETTING_MARKETS["UEL Winner"]
        team_probs = {}
        
        for team, odds in winner_odds.items():
            prob = self.fractional_to_probability(odds)
            team_probs[team] = prob
        
        # Normalize probabilities to sum to 1
        total_prob = sum(team_probs.values())
        normalized_probs = {team: prob/total_prob for team, prob in team_probs.items()}
        
        # Calculate Elo ratings from normalized probabilities
        # Use log-odds to derive relative strength, centered around 1500
        base_elo = 1500
        log_probs = {
            team: math.log(max(prob, 1e-10)) for team, prob in normalized_probs.items()
        }
        mean_log_prob = sum(log_probs.values()) / len(log_probs)
        for team, prob in normalized_probs.items():
            log_odds_diff = log_probs[team] - mean_log_prob
            elo_diff = log_odds_diff * (400.0 / math.log(10))
            elo = base_elo + elo_diff
            self.team_elo[team] = round(elo, 1)
        
        # Display Elo ratings
        sorted_elo = sorted(self.team_elo.items(), key=lambda x: x[1], reverse=True)
        
        print(f"\n{'Team':<30} {'Win Odds':<12} {'Probability':<12} {'Elo Rating':<10}")
        print("-" * 80)
        
        for team, elo in sorted_elo:
            odds = winner_odds.get(team, (0, 0))
            prob = normalized_probs.get(team, 0)
            odds_str = f"{odds[0]}/{odds[1]}" if odds != (0, 0) else "N/A"
            print(f"{team:<30} {odds_str:<12} {prob*100:>6.2f}%     {elo:<10.1f}")
        
        print(f"\n✓ Elo ratings calculated for {len(self.team_elo)} teams")
    
    def simulate_remaining_playoffs(self):
        """Simulate the remaining playoff matches using Elo ratings"""
        print("\n" + "=" * 80)
        print("PLAY-OFF ROUND - REMAINING MATCHES SIMULATION")
        print("=" * 80)
        
        uel_winners = []
        cl_losers = []
        
        # Simulate UEL play-off matches
        print("\nUEL Play-off Round:")
        for match in self.uel_playoff_matches['UEL Play-off Round']:
            team1 = match['team1']
            team2 = match['team2']
            
            # Get Elo ratings
            elo1 = self.team_elo.get(team1, 1500)
            elo2 = self.team_elo.get(team2, 1500)
            
            # Calculate win probability based on Elo difference
            elo_diff = elo1 - elo2
            prob1_win = 1 / (1 + 10**(-elo_diff/400))
            
            # Parse first leg score
            leg1_scores = match['leg1'].split('-')
            leg1_t1 = int(leg1_scores[0])
            leg1_t2 = int(leg1_scores[1])
            
            # Simulate second leg with Elo-based weighting
            if prob1_win > 0.5:
                leg2_t1 = random.choices([0, 1, 2, 3, 4], weights=[15, 30, 30, 15, 10])[0]
                leg2_t2 = random.choices([0, 1, 2, 3, 4], weights=[25, 35, 25, 10, 5])[0]
            else:
                leg2_t1 = random.choices([0, 1, 2, 3, 4], weights=[25, 35, 25, 10, 5])[0]
                leg2_t2 = random.choices([0, 1, 2, 3, 4], weights=[15, 30, 30, 15, 10])[0]
            
            # Calculate aggregate
            agg_t1 = leg1_t1 + leg2_t1
            agg_t2 = leg1_t2 + leg2_t2
            
            if agg_t1 == agg_t2:
                # Extra time
                et_t1 = random.choices([0, 1, 2], weights=[60, 30, 10])[0]
                et_t2 = random.choices([0, 1, 2], weights=[60, 30, 10])[0]
                leg2_t1 += et_t1
                leg2_t2 += et_t2
                agg_t1 += et_t1
                agg_t2 += et_t2
                
                if agg_t1 == agg_t2:
                    winner = random.choice([team1, team2])
                    leg2_str = f"{leg2_t1}-{leg2_t2} (pens)"
                else:
                    winner = team1 if agg_t1 > agg_t2 else team2
                    leg2_str = f"{leg2_t1}-{leg2_t2} (a.e.t.)"
            else:
                winner = team1 if agg_t1 > agg_t2 else team2
                leg2_str = f"{leg2_t1}-{leg2_t2}"
            
            print(f"  ⚽ {team1} vs {team2}: "
                  f"{match['leg1']} / {leg2_str} → Winner: {winner}")
            uel_winners.append(winner)
        
        # Simulate CL play-off matches (losers drop to UEL)
        print("\nCL Play-off Round (losers drop to UEL):")
        for match in self.cl_playoff_matches['CL Play-off Round (losers drop to UEL)']:
            team1 = match['team1']
            team2 = match['team2']
            
            # Get Elo ratings
            elo1 = self.team_elo.get(team1, 1500)
            elo2 = self.team_elo.get(team2, 1500)
            
            # Calculate win probability based on Elo difference
            elo_diff = elo1 - elo2
            prob1_win = 1 / (1 + 10**(-elo_diff/400))
            
            # Parse first leg score
            leg1_scores = match['leg1'].split('-')
            leg1_t1 = int(leg1_scores[0])
            leg1_t2 = int(leg1_scores[1])
            
            # Simulate second leg with Elo-based weighting
            if prob1_win > 0.5:
                leg2_t1 = random.choices([0, 1, 2, 3, 4], weights=[15, 30, 30, 15, 10])[0]
                leg2_t2 = random.choices([0, 1, 2, 3, 4], weights=[25, 35, 25, 10, 5])[0]
            else:
                leg2_t1 = random.choices([0, 1, 2, 3, 4], weights=[25, 35, 25, 10, 5])[0]
                leg2_t2 = random.choices([0, 1, 2, 3, 4], weights=[15, 30, 30, 15, 10])[0]
            
            # Calculate aggregate
            agg_t1 = leg1_t1 + leg2_t1
            agg_t2 = leg1_t2 + leg2_t2
            
            if agg_t1 == agg_t2:
                # Extra time
                et_t1 = random.choices([0, 1, 2], weights=[60, 30, 10])[0]
                et_t2 = random.choices([0, 1, 2], weights=[60, 30, 10])[0]
                leg2_t1 += et_t1
                leg2_t2 += et_t2
                agg_t1 += et_t1
                agg_t2 += et_t2
                
                if agg_t1 == agg_t2:
                    winner = random.choice([team1, team2])
                    loser = team2 if winner == team1 else team1
                    leg2_str = f"{leg2_t1}-{leg2_t2} (pens)"
                else:
                    winner = team1 if agg_t1 > agg_t2 else team2
                    loser = team2 if winner == team1 else team1
                    leg2_str = f"{leg2_t1}-{leg2_t2} (a.e.t.)"
            else:
                winner = team1 if agg_t1 > agg_t2 else team2
                loser = team2 if winner == team1 else team1
                leg2_str = f"{leg2_t1}-{leg2_t2}"
            
            print(f"  ⚽ {team1} vs {team2}: "
                  f"{match['leg1']} / {leg2_str} → Winner: {winner}, Loser (to UEL): {loser}")
            cl_losers.append(loser)
        
        # Combine all teams for league phase
        self.teams = self.confirmed_teams + uel_winners + cl_losers
        
        print(f"\n✓ All {len(self.teams)} teams confirmed for UEL League Phase")
        print(f"  - Confirmed teams: {len(self.confirmed_teams)}")
        print(f"  - UEL play-off winners: {len(uel_winners)}")
        print(f"  - CL play-off losers: {len(cl_losers)}")
        return uel_winners, cl_losers
    
    def initialize_standings(self):
        """Initialize standings for all 36 teams"""
        self.standings = {team: {"points": 0, "played": 0, "won": 0, "drawn": 0, 
                                  "lost": 0, "goals_for": 0, "goals_against": 0,
                                  "home_games": 0, "away_games": 0, "elo": self.team_elo.get(team, 1500)} 
                         for team in self.teams}
    
    def generate_fixtures(self):
        """Generate fixtures using Swiss model - each team plays 8 matches (4 home, 4 away)"""
        print("\n" + "=" * 80)
        print("GENERATING EUROPA LEAGUE 2026/27 LEAGUE PHASE FIXTURES")
        print("=" * 80)
        
        all_pairs = list(combinations(self.teams, 2))
        random.shuffle(all_pairs)
        
        team_game_count = {team: 0 for team in self.teams}
        team_home_count = {team: 0 for team in self.teams}
        team_away_count = {team: 0 for team in self.teams}
        
        round_num = 1
        fixtures_per_round = 18
        
        while len(self.fixtures) < 144:
            round_fixtures = []
            used_teams = set()
            
            for team1, team2 in all_pairs:
                if len(round_fixtures) >= fixtures_per_round:
                    break
                
                if team1 in used_teams or team2 in used_teams:
                    continue
                
                if self._teams_already_played(team1, team2):
                    continue
                
                if team_game_count[team1] >= 8 or team_game_count[team2] >= 8:
                    continue
                
                home_team, away_team = self._determine_home_away(
                    team1, team2, team_home_count, team_away_count
                )
                
                if home_team and away_team:
                    round_fixtures.append((home_team, away_team))
                    used_teams.add(team1)
                    used_teams.add(team2)
                    
                    team_game_count[team1] += 1
                    team_game_count[team2] += 1
                    team_home_count[home_team] += 1
                    team_away_count[away_team] += 1
            
            if round_fixtures:
                self.fixtures.extend([(round_num, fixture) for fixture in round_fixtures])
                print(f"\nRound {round_num}:")
                for i, (home, away) in enumerate(round_fixtures, 1):
                    print(f"  Match {i:2d}: {home:<30} vs {away}")
                round_num += 1
            else:
                break
        
        print(f"\n✓ Total fixtures generated: {len(self.fixtures)}")
    
    def _teams_already_played(self, team1, team2):
        """Check if two teams have already played each other"""
        for _, (home, away) in self.fixtures:
            if (home == team1 and away == team2) or (home == team2 and away == team1):
                return True
        return False
    
    def _determine_home_away(self, team1, team2, home_count, away_count):
        """Determine which team plays at home to balance home/away games"""
        t1_home = home_count[team1]
        t1_away = away_count[team1]
        t2_home = home_count[team2]
        t2_away = away_count[team2]
        
        if t1_home < t2_home:
            return team1, team2
        elif t2_home < t1_home:
            return team2, team1
        else:
            if t1_away > t2_away:
                return team1, team2
            elif t2_away > t1_away:
                return team2, team1
            else:
                return random.choice([(team1, team2), (team2, team1)])
    
    def simulate_match_result(self, home, away):
        """Simulate a match result using Elo ratings"""
        elo_home = self.team_elo.get(home, 1500)
        elo_away = self.team_elo.get(away, 1500)
        
        # Home advantage bonus (typically 100 Elo points)
        elo_home_adj = elo_home + 100
        
        # Calculate expected outcome
        elo_diff = elo_home_adj - elo_away
        prob_home_win = 1 / (1 + 10**(-elo_diff/400))
        prob_draw = 0.25  # Base draw probability
        prob_away_win = 1 - prob_home_win - prob_draw
        
        # Normalize probabilities
        total = prob_home_win + prob_draw + prob_away_win
        prob_home_win /= total
        prob_draw /= total
        prob_away_win /= total
        
        # Determine outcome
        outcome = random.choices(['home_win', 'draw', 'away_win'], 
                                weights=[prob_home_win, prob_draw, prob_away_win])[0]
        
        # Generate goals based on outcome
        if outcome == 'home_win':
            home_goals = random.choices([1, 2, 3, 4, 5], weights=[20, 35, 25, 15, 5])[0]
            away_goals = random.choices([0, 1, 2], weights=[50, 35, 15])[0]
        elif outcome == 'away_win':
            home_goals = random.choices([0, 1, 2], weights=[50, 35, 15])[0]
            away_goals = random.choices([1, 2, 3, 4, 5], weights=[20, 35, 25, 15, 5])[0]
        else:  # draw
            goals = random.choices([0, 1, 2, 3], weights=[15, 40, 30, 15])[0]
            home_goals = goals
            away_goals = goals
        
        return home_goals, away_goals
    
    def simulate_matches(self):
        """Simulate all matches using Elo-based results"""
        print("\n" + "=" * 80)
        print("SIMULATING LEAGUE PHASE MATCHES (ELO-BASED)")
        print("=" * 80)
        
        for round_num, (home, away) in self.fixtures:
            home_goals, away_goals = self.simulate_match_result(home, away)
            
            self.results.append({
                'round': round_num,
                'home': home,
                'away': away,
                'home_goals': home_goals,
                'away_goals': away_goals
            })
            
            self._update_standings(home, away, home_goals, away_goals)
            
            # Update Elo ratings after each match
            self._update_elo(home, away, home_goals, away_goals)
    
    def _update_elo(self, team1, team2, goals1, goals2):
        """Update Elo ratings after a match"""
        elo1 = self.team_elo.get(team1, 1500)
        elo2 = self.team_elo.get(team2, 1500)
        
        # Expected scores
        elo_diff = elo1 - elo2
        expected1 = 1 / (1 + 10**(-elo_diff/400))
        expected2 = 1 - expected1
        
        # Actual score (1 for win, 0.5 for draw, 0 for loss)
        if goals1 > goals2:
            actual1, actual2 = 1, 0
        elif goals1 < goals2:
            actual1, actual2 = 0, 1
        else:
            actual1, actual2 = 0.5, 0.5
        
        # K-factor (higher for important matches)
        k = 30
        
        # Update Elo
        new_elo1 = elo1 + k * (actual1 - expected1)
        new_elo2 = elo2 + k * (actual2 - expected2)
        
        self.team_elo[team1] = round(new_elo1, 1)
        self.team_elo[team2] = round(new_elo2, 1)
    
    def _update_standings(self, home, away, home_goals, away_goals):
        """Update team standings based on match result"""
        self.standings[home]["played"] += 1
        self.standings[away]["played"] += 1
        
        self.standings[home]["goals_for"] += home_goals
        self.standings[home]["goals_against"] += away_goals
        self.standings[away]["goals_for"] += away_goals
        self.standings[away]["goals_against"] += home_goals
        
        if home_goals > away_goals:
            self.standings[home]["points"] += 3
            self.standings[home]["won"] += 1
            self.standings[away]["lost"] += 1
        elif home_goals < away_goals:
            self.standings[away]["points"] += 3
            self.standings[away]["won"] += 1
            self.standings[home]["lost"] += 1
        else:
            self.standings[home]["points"] += 1
            self.standings[away]["points"] += 1
            self.standings[home]["drawn"] += 1
            self.standings[away]["drawn"] += 1
    
    def display_standings(self):
        """Display final league table"""
        print("\n" + "=" * 80)
        print("EUROPA LEAGUE 2026/27 - FINAL LEAGUE PHASE STANDINGS")
        print("=" * 80)
        
        sorted_teams = sorted(
            self.standings.items(),
            key=lambda x: (
                x[1]["points"],
                x[1]["goals_for"] - x[1]["goals_against"],
                x[1]["goals_for"]
            ),
            reverse=True
        )
        
        print(f"{'Pos':<4} {'Team':<30} {'P':<3} {'W':<3} {'D':<3} {'L':<3} "
              f"{'GF':<3} {'GA':<3} {'GD':<4} {'Pts':<4} {'Elo':<6}")
        print("-" * 80)
        
        for pos, (team, stats) in enumerate(sorted_teams, 1):
            gd = stats["goals_for"] - stats["goals_against"]
            gd_str = f"+{gd}" if gd > 0 else str(gd)
            
            prefix = ""
            if pos <= 8:
                prefix = "🟢 "
            elif pos <= 24:
                prefix = "🟡 "
            else:
                prefix = "🔴 "
            
            elo = self.team_elo.get(team, 1500)
            
            print(f"{prefix}{pos:<2} {team:<28} {stats['played']:<3} {stats['won']:<3} "
                  f"{stats['drawn']:<3} {stats['lost']:<3} {stats['goals_for']:<3} "
                  f"{stats['goals_against']:<3} {gd_str:<4} {stats['points']:<4} {elo:<6.1f}")
        
        print("\n" + "=" * 80)
        print("QUALIFICATION:")
        print("🟢 Positions 1-8: Direct qualification to Round of 16")
        print("🟡 Positions 9-24: Knockout round playoffs")
        print("🔴 Positions 25-36: Eliminated")
        print("=" * 80)
    
    def _get_sorted_standings(self):
        """Return teams sorted by league position (points, GD, GF)."""
        return sorted(
            self.standings.items(),
            key=lambda x: (
                x[1]["points"],
                x[1]["goals_for"] - x[1]["goals_against"],
                x[1]["goals_for"],
            ),
            reverse=True,
        )

    def _simulate_two_leg_tie(self, higher_seed, lower_seed):
        """Simulate a two-leg knockout tie. Higher seed gets second leg at home.

        Returns (winner, loser, leg_results) where leg_results is a list of
        (home_team, away_team, home_goals, away_goals) tuples.
        """
        legs = []

        leg1_home, leg1_away = self.simulate_match_result(lower_seed, higher_seed)
        self._update_elo(lower_seed, higher_seed, leg1_home, leg1_away)
        legs.append((lower_seed, higher_seed, leg1_home, leg1_away))

        leg2_home, leg2_away = self.simulate_match_result(higher_seed, lower_seed)
        self._update_elo(higher_seed, lower_seed, leg2_home, leg2_away)
        legs.append((higher_seed, lower_seed, leg2_home, leg2_away))

        agg_higher = leg1_away + leg2_home
        agg_lower = leg1_home + leg2_away

        if agg_higher == agg_lower:
            et_h, et_a = self.simulate_match_result(higher_seed, lower_seed)
            self._update_elo(higher_seed, lower_seed, et_h, et_a)
            agg_higher += et_h
            agg_lower += et_a
            legs.append(("ET", higher_seed, et_h, lower_seed, et_a))

            if agg_higher == agg_lower:
                winner = random.choice([higher_seed, lower_seed])
                loser = lower_seed if winner == higher_seed else higher_seed
                legs.append(("Pens", winner))
            elif agg_higher > agg_lower:
                winner, loser = higher_seed, lower_seed
            else:
                winner, loser = lower_seed, higher_seed
        elif agg_higher > agg_lower:
            winner, loser = higher_seed, lower_seed
        else:
            winner, loser = lower_seed, higher_seed

        return winner, loser, legs

    def simulate_knockout_round_playoffs(self, playoff_teams):
        """Simulate knockout round play-offs (16 teams -> 8 winners).

        Teams are ordered by league position. Pairings:
        9th vs 24th, 10th vs 23rd, ..., 16th vs 17th.
        Higher seed gets second leg at home.
        """
        print("\n  KNOCK-OUT ROUND PLAY-OFFS")
        print("  " + "-" * 60)

        winners = []
        for i in range(8):
            higher = playoff_teams[i]
            lower = playoff_teams[15 - i]
            winner, loser, legs = self._simulate_two_leg_tie(higher, lower)

            leg1_str = f"{legs[0][2]}-{legs[0][3]}"
            leg2_str = f"{legs[1][2]}-{legs[1][3]}"
            print(f"  ⚽ {lower} {leg1_str} - {leg2_str} {higher} → Winner: {winner}")
            winners.append(winner)

        print(f"\n  ✓ {len(winners)} playoff winners advance to Round of 16")
        return winners

    def simulate_round_of_16(self, direct_qualifiers, playoff_winners):
        """Simulate Round of 16 (16 teams -> 8 winners).

        Pairings: Seed i vs playoff winner i.
        Higher seed (direct qualifier) gets second leg at home.
        """
        print("\n  ROUND OF 16")
        print("  " + "-" * 60)

        winners = []
        for i in range(8):
            higher = direct_qualifiers[i]
            lower = playoff_winners[i]
            winner, loser, legs = self._simulate_two_leg_tie(higher, lower)

            leg1_str = f"{legs[0][2]}-{legs[0][3]}"
            leg2_str = f"{legs[1][2]}-{legs[1][3]}"
            print(f"  ⚽ {lower} {leg1_str} - {leg2_str} {higher} → Winner: {winner}")
            winners.append(winner)

        print(f"\n  ✓ {len(winners)} teams advance to quarter-finals")
        return winners

    def simulate_quarter_finals(self, teams):
        """Simulate quarter-finals (8 teams -> 4 winners) in bracket order."""
        print("\n  QUARTER-FINALS")
        print("  " + "-" * 60)

        winners = []
        for i in range(4):
            team1 = teams[i * 2]
            team2 = teams[i * 2 + 1]
            higher = team1 if self.team_elo.get(team1, 1500) >= self.team_elo.get(team2, 1500) else team2
            lower = team2 if higher == team1 else team1
            winner, loser, legs = self._simulate_two_leg_tie(higher, lower)

            leg1_str = f"{legs[0][2]}-{legs[0][3]}"
            leg2_str = f"{legs[1][2]}-{legs[1][3]}"
            print(f"  ⚽ {lower} {leg1_str} - {leg2_str} {higher} → Winner: {winner}")
            winners.append(winner)

        print(f"\n  ✓ {len(winners)} teams advance to semi-finals")
        return winners

    def simulate_semi_finals(self, teams):
        """Simulate semi-finals (4 teams -> 2 winners) in bracket order."""
        print("\n  SEMI-FINALS")
        print("  " + "-" * 60)

        winners = []
        for i in range(2):
            team1 = teams[i * 2]
            team2 = teams[i * 2 + 1]
            higher = team1 if self.team_elo.get(team1, 1500) >= self.team_elo.get(team2, 1500) else team2
            lower = team2 if higher == team1 else team1
            winner, loser, legs = self._simulate_two_leg_tie(higher, lower)

            leg1_str = f"{legs[0][2]}-{legs[0][3]}"
            leg2_str = f"{legs[1][2]}-{legs[1][3]}"
            print(f"  ⚽ {lower} {leg1_str} - {leg2_str} {higher} → Winner: {winner}")
            winners.append(winner)

        print(f"\n  ✓ {len(winners)} teams advance to final")
        return winners

    def simulate_final(self, teams):
        """Simulate the final (2 teams -> 1 champion).

        Played as a single match at a neutral venue. Home advantage is
        awarded to the team with the higher Elo rating.
        """
        print("\n  FINAL")
        print("  " + "-" * 60)

        higher = teams[0] if self.team_elo.get(teams[0], 1500) >= self.team_elo.get(teams[1], 1500) else teams[1]
        lower = teams[1] if higher == teams[0] else teams[0]

        home_goals, away_goals = self.simulate_match_result(higher, lower)
        self._update_elo(higher, lower, home_goals, away_goals)

        if home_goals == away_goals:
            et_h, et_a = self.simulate_match_result(higher, lower)
            self._update_elo(higher, lower, et_h, et_a)
            home_goals += et_h
            away_goals += et_a

            if home_goals == away_goals:
                winner = random.choice([higher, lower])
                print(f"  ⚽ {higher} {home_goals}-{away_goals} {lower} (pens) → Champion: {winner}")
            else:
                winner = higher if home_goals > away_goals else lower
                print(f"  ⚽ {higher} {home_goals}-{away_goals} {lower} (a.e.t.) → Champion: {winner}")
        else:
            winner = higher if home_goals > away_goals else lower
            print(f"  ⚽ {higher} {home_goals}-{away_goals} {lower} → Champion: {winner}")

        return winner

    def run_knockout_phase(self):
        """Run the complete knockout phase from play-offs to final."""
        sorted_teams = self._get_sorted_standings()
        team_names = [team for team, _ in sorted_teams]

        direct_qualifiers = team_names[:8]
        playoff_teams = team_names[8:24]
        eliminated = team_names[24:]

        print("\n" + "=" * 80)
        print("EUROPA LEAGUE 2026/27 - KNOCK-OUT PHASE")
        print("=" * 80)

        print(f"\n  Direct qualifiers (positions 1-8):")
        for i, team in enumerate(direct_qualifiers, 1):
            print(f"    {i}. {team}")
        print(f"\n  Play-off teams (positions 9-24):")
        for i, team in enumerate(playoff_teams, 9):
            print(f"    {i}. {team}")
        print(f"\n  Eliminated (positions 25-36):")
        for team in eliminated:
            print(f"    - {team}")

        playoff_winners = self.simulate_knockout_round_playoffs(playoff_teams)
        ro16_winners = self.simulate_round_of_16(direct_qualifiers, playoff_winners)
        qf_winners = self.simulate_quarter_finals(ro16_winners)
        sf_winners = self.simulate_semi_finals(qf_winners)
        champion = self.simulate_final(sf_winners)

        return champion

    def _run_knockout_phase_silent(self) -> str:
        """Run knockout phase without printing. Returns the champion team name."""
        sorted_teams = self._get_sorted_standings()
        team_names = [team for team, _ in sorted_teams]

        direct_qualifiers = team_names[:8]
        playoff_teams = team_names[8:24]

        playoff_winners = []
        for i in range(8):
            higher = playoff_teams[i]
            lower = playoff_teams[15 - i]
            winner, _, _ = self._simulate_two_leg_tie(higher, lower)
            playoff_winners.append(winner)

        ro16_winners = []
        for i in range(8):
            higher = direct_qualifiers[i]
            lower = playoff_winners[i]
            winner, _, _ = self._simulate_two_leg_tie(higher, lower)
            ro16_winners.append(winner)

        qf_winners = []
        for i in range(4):
            team1 = ro16_winners[i * 2]
            team2 = ro16_winners[i * 2 + 1]
            higher = team1 if self.team_elo.get(team1, 1500) >= self.team_elo.get(team2, 1500) else team2
            lower = team2 if higher == team1 else team1
            winner, _, _ = self._simulate_two_leg_tie(higher, lower)
            qf_winners.append(winner)

        sf_winners = []
        for i in range(2):
            team1 = qf_winners[i * 2]
            team2 = qf_winners[i * 2 + 1]
            higher = team1 if self.team_elo.get(team1, 1500) >= self.team_elo.get(team2, 1500) else team2
            lower = team2 if higher == team1 else team1
            winner, _, _ = self._simulate_two_leg_tie(higher, lower)
            sf_winners.append(winner)

        higher = sf_winners[0] if self.team_elo.get(sf_winners[0], 1500) >= self.team_elo.get(sf_winners[1], 1500) else sf_winners[1]
        lower = sf_winners[1] if higher == sf_winners[0] else sf_winners[0]

        home_goals, away_goals = self.simulate_match_result(higher, lower)
        self._update_elo(higher, lower, home_goals, away_goals)

        if home_goals == away_goals:
            et_h, et_a = self.simulate_match_result(higher, lower)
            self._update_elo(higher, lower, et_h, et_a)
            home_goals += et_h
            away_goals += et_a
            if home_goals == away_goals:
                return random.choice([higher, lower])
            return higher if home_goals > away_goals else lower
        return higher if home_goals > away_goals else lower

    def run(self):
        """Run the complete simulation"""
        # Step 1: Calculate Elo ratings from betting odds
        self.calculate_elo_ratings()

        # Step 2: Simulate remaining playoff matches
        self.simulate_remaining_playoffs()

        # Step 3: Initialize standings
        self.initialize_standings()

        # Step 4: Generate fixtures
        self.generate_fixtures()

        # Step 5: Simulate all league phase matches
        self.simulate_matches()

        # Step 6: Display final standings
        self.display_standings()

        # Step 7: Run knockout phase
        champion = self.run_knockout_phase()
        print(f"\n✓ Europa League 2026/27 champion: {champion}")


# ==========================================
# MULTI-SIMULATION ENTRY POINT
# ==========================================

NUM_UEL_SIMS = 2000


def generate_swiss_fixtures_silent(teams: List[str]) -> List[Tuple[int, int, str, str]]:
    """Generate Swiss-model fixtures without printing.

    Returns a list of (round_num, idx, home, away) tuples.
    """
    n = len(teams)
    all_pairs = list(combinations(range(n), 2))
    random.shuffle(all_pairs)

    team_game_count = defaultdict(int)
    team_home_count = defaultdict(int)
    team_away_count = defaultdict(int)
    played_pairs = set()

    fixtures: List[Tuple[int, int, str, str]] = []
    round_num = 1
    fixtures_per_round = n // 2

    while len(fixtures) < n * 4:
        round_fixtures = []
        used_teams = set()

        for i, j in all_pairs:
            if len(round_fixtures) >= fixtures_per_round:
                break
            if i in used_teams or j in used_teams:
                continue
            if (i, j) in played_pairs or (j, i) in played_pairs:
                continue
            if team_game_count[i] >= 8 or team_game_count[j] >= 8:
                continue

            if team_home_count[i] < team_home_count[j]:
                home, away = i, j
            elif team_home_count[j] < team_home_count[i]:
                home, away = j, i
            elif team_away_count[i] > team_away_count[j]:
                home, away = i, j
            elif team_away_count[j] > team_away_count[i]:
                home, away = j, i
            else:
                if random.random() < 0.5:
                    home, away = i, j
                else:
                    home, away = j, i

            if team_home_count[home] >= 4 or team_away_count[away] >= 4:
                if team_home_count[away] < 4 and team_away_count[home] < 4:
                    home, away = away, home
                else:
                    continue

            round_fixtures.append((round_num, len(fixtures), teams[home], teams[away]))
            used_teams.add(i)
            used_teams.add(j)
            played_pairs.add((i, j))
            team_game_count[i] += 1
            team_game_count[j] += 1
            team_home_count[home] += 1
            team_away_count[away] += 1

        if round_fixtures:
            fixtures.extend(round_fixtures)
            round_num += 1
        else:
            break

    return fixtures


def simulate_league_phase_silent(model: "EuropaLeagueSwissModel", fixtures: List[Tuple[int, int, str, str]]) -> None:
    """Simulate all league phase matches silently (no prints)."""
    for _, _, home, away in fixtures:
        home_goals, away_goals = model.simulate_match_result(home, away)
        model._update_standings(home, away, home_goals, away_goals)
        model._update_elo(home, away, home_goals, away_goals)


def run_europa_league_simulation(num_sims: int = NUM_UEL_SIMS) -> Dict[str, float]:
    """Run the full UEL simulation and return team champion probabilities.

    The league phase determines the top 8 (direct to Round of 16) and
    positions 9-24 (knockout round play-offs). A knockout phase then
    reduces the 36 teams to a single tournament winner via two-leg
    ties, extra time and penalties as needed.
    Returns a dict mapping team names to their chance of winning the
    Europa League (0-100).
    """
    print("\nSTARTING UEFA EUROPA LEAGUE 2026/27 SIMULATION")
    print(f"Number of Simulations: {num_sims}")

    print("\nCalculating Elo ratings from betting odds...")
    model = EuropaLeagueSwissModel()
    model.calculate_elo_ratings()

    print("Simulating remaining play-off matches...")
    model.simulate_remaining_playoffs()

    print(f"\nRunning {num_sims} Europa League simulations...")
    uel_win_counts: Dict[str, int] = defaultdict(int)

    for _ in tqdm(range(num_sims), desc="UEL Sim"):
        sim_model = EuropaLeagueSwissModel()
        sim_model.team_elo = dict(model.team_elo)
        sim_model.teams = list(model.teams)
        sim_model.initialize_standings()
        fixture_indices = generate_swiss_fixtures_silent(sim_model.teams)
        simulate_league_phase_silent(sim_model, fixture_indices)
        champion = sim_model._run_knockout_phase_silent()
        uel_win_counts[champion] += 1

    uel_win_probs: Dict[str, float] = {
        team: (count / num_sims) * 100 for team, count in uel_win_counts.items()
    }

    print("\n" + "=" * 60)
    print("CHANCE OF WINNING THE EUROPA LEAGUE (ALL TEAMS)")
    print("=" * 60)
    for team, prob in sorted(uel_win_probs.items(), key=lambda x: x[1], reverse=True):
        print(f"  {team:<30} {prob:<8.2f}%")

    return uel_win_probs


if __name__ == "__main__":
    random.seed(42)
    np.random.seed(42)

    run_europa_league_simulation()