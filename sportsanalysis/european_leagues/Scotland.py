#!/usr/bin/env python3
"""
Scottish Premiership 2025-26 Season Predictor
Adapted for the 38-game format, featuring the 33-game regular season 
and the post-split Top 6 / Bottom 6 structure.
"""

import random
import math
import numpy as np
from collections import defaultdict
from tqdm import tqdm

# ===============================
# MATCHDAY 1 RESULTS
# ===============================
COMPLETED_FIXTURES = [
    ("Celtic", "Dundee FC", 1, 0),
    ("Dundee FC", "Aberdeen", 2, 0),
    ("St. Mirren", "St. Johnstone", 1, 0),
    ("Kilmarnock", "Celtic", 1, 5),
    ("Hearts", "Dundee Utd", 4, 0),
    ("Motherwell", "Falkirk", 0, 0)
]

# Current Standings derived from MD1 results
# Format: (Team, P, W, D, L, GD, GF, GA, L5, Pts)
CURRENT_STANDINGS = [
    ("Celtic", 2, 2, 0, 0, 5, 6, 1, "WW", 6),
    ("Hearts", 1, 1, 0, 0, 4, 4, 0, "W", 3),
    ("Dundee FC", 2, 1, 0, 1, 1, 2, 1, "LW", 3),
    ("St. Mirren", 1, 1, 0, 0, 1, 1, 0, "W", 3),
    ("Motherwell", 1, 0, 1, 0, 0, 0, 0, "D", 1),
    ("Falkirk", 1, 0, 1, 0, 0, 0, 0, "D", 1),
    ("Aberdeen", 1, 0, 0, 1, -2, 0, 2, "L", 0),
    ("St. Johnstone", 1, 0, 0, 1, -1, 0, 1, "L", 0),
    ("Dundee Utd", 1, 0, 0, 1, -4, 0, 4, "L", 0),
    ("Kilmarnock", 1, 0, 0, 1, -4, 1, 5, "L", 0),
    ("Rangers", 0, 0, 0, 0, 0, 0, 0, "", 0),
    ("Hibernian", 0, 0, 0, 0, 0, 0, 0, "", 0),
]

# Base ELOs to reflect actual team strength (crucial for teams with 0 games played)
BASE_ELOS = {
    "Celtic": 1750, "Rangers": 1720, "Hearts": 1580, "Hibernian": 1550,
    "Aberdeen": 1540, "Kilmarnock": 1520, "St. Mirren": 1510, "Dundee FC": 1500,
    "Motherwell": 1490, "Dundee Utd": 1470, "St. Johnstone": 1460, "Falkirk": 1430
}

MAX_GAMES = 38
PHASE1_GAMES = 33
NUM_TEAMS = 12

# Calculate form and rates safely (handling 0 games played for Rangers/Hibs)
wdl_rates = {}
for team, p, w, d, l, gd, gf, ga, l5, pts in CURRENT_STANDINGS:
    if p > 0:
        wdl_rates[team] = {"win": w/p, "draw": d/p, "loss": l/p}
    else:
        wdl_rates[team] = {"win": 0.33, "draw": 0.34, "loss": 0.33}

form_adjustment = {}
for team, p, w, d, l, gd, gf, ga, l5, pts in CURRENT_STANDINGS:
    if p > 0 and len(l5) > 0:
        pts_l5 = sum(3 if r == 'W' else (1 if r == 'D' else 0) for r in l5)
        form_adjustment[team] = ((pts_l5 - len(l5)*1.5) * 10) * 0.5
    else:
        form_adjustment[team] = 0.0

def get_adjusted_elo(team, ratings_dict):
    base = ratings_dict.get(team, 1500)
    return base + form_adjustment.get(team, 0)

def generate_phase1_remaining(teams, completed):
    """Generates remaining Phase 1 fixtures ensuring every pair plays exactly 3 times."""
    pair_counts = defaultdict(int)
    for h, a, _, _ in completed:
        pair_counts[tuple(sorted((h, a)))] += 1
        
    remaining = []
    for i in range(len(teams)):
        for j in range(i + 1, len(teams)):
            t1, t2 = teams[i], teams[j]
            played = pair_counts[(t1, t2)]
            needed = 3 - played
            for _ in range(needed):
                if random.choice([True, False]):
                    remaining.append((t1, t2))
                else:
                    remaining.append((t2, t1))
    random.shuffle(remaining)
    return remaining

def generate_round_robin(teams):
    """Generates a balanced round-robin for the post-split 5-game phase."""
    n = len(teams)
    fixtures = []
    teams = list(teams)
    if n % 2 != 0:
        teams.append("BYE")
        n += 1
    
    for round_idx in range(n - 1):
        for i in range(n // 2):
            home = teams[i]
            away = teams[n - 1 - i]
            if home != "BYE" and away != "BYE":
                if round_idx % 2 == 0:
                    fixtures.append((home, away))
                else:
                    fixtures.append((away, home))
        teams = [teams[0]] + [teams[-1]] + teams[1:-1]
    return fixtures

ALL_TEAMS = [t[0] for t in CURRENT_STANDINGS]
PHASE1_REMAINING = generate_phase1_remaining(ALL_TEAMS, COMPLETED_FIXTURES)

class OptimizedELORatingSystem:
    def __init__(self, k_factor=30, home_advantage=85):
        self.k_factor = k_factor
        self.home_advantage = home_advantage
        self.ratings = defaultdict(lambda: 1500)
        self.match_weights = {'league': 1.5}

    def expected_score(self, ra, rb):
        return 1 / (1 + 10 ** ((rb - ra) / 400))

    def update_ratings(self, home, away, hs, aws, match_type='league'):
        K = self.k_factor * self.match_weights.get(match_type, 1.5)
        hr, ar = self.ratings[home] + self.home_advantage, self.ratings[away]
        gm = min(1 + math.log(1 + abs(hs - aws)), 2.0)
        eh, ea = self.expected_score(hr, ar), self.expected_score(ar, hr)
        ah = 1 if hs > aws else (0.5 if hs == aws else 0)
        aa = 1 if aws > hs else (0.5 if hs == aws else 0)
        self.ratings[home] += K * gm * (ah - eh)
        self.ratings[away] += K * gm * (aa - ea)

    def predict_score(self, home, away, neutral=False):
        ha = 0 if neutral else self.home_advantage
        diff = get_adjusted_elo(home, self.ratings) - get_adjusted_elo(away, self.ratings) + ha
        hxg, axg = 0.6 + 1.7 / (1 + math.exp(-diff / 400)), 0.6 + 1.7 / (1 + math.exp(diff / 400))
        closeness = math.exp(-(diff ** 2) / (2 * 180 ** 2))
        bd = ((wdl_rates[home]["win"] - wdl_rates[home]["loss"]) - (wdl_rates[away]["win"] - wdl_rates[away]["loss"])) * 0.5
        hxg, axg = hxg + bd * 0.15, axg - bd * 0.15
        tempo = 0.9 + 0.1 * (abs(diff) / 400)
        hxg, axg = hxg * tempo, axg * tempo
        vb = 1 + (wdl_rates[home]["win"] - wdl_rates[home]["draw"]) * 0.1
        db = max((wdl_rates[home]["draw"] + wdl_rates[away]["draw"]) / 2, 0.3)
        ls = 0.05 + closeness * 0.25 * db
        lh, la = max(0.05, hxg - ls) * vb, max(0.05, axg - ls)
        sg = np.random.poisson(ls)
        return int(np.random.poisson(lh) + sg), int(np.random.poisson(la) + sg)

class LeagueSimulator:
    def __init__(self):
        self.elo_system = OptimizedELORatingSystem()
        self.team_stats = {}

    def load_current_standings(self):
        for team, p, w, d, l, gd, gf, ga, l5, pts in CURRENT_STANDINGS:
            self.team_stats[team] = {'played': p, 'won': w, 'drawn': d, 'lost': l, 'gf': gf, 'ga': ga, 'points': pts}

    def initialize_elos_from_results(self, completed_fixtures):
        for team in self.team_stats: 
            self.elo_system.ratings[team] = BASE_ELOS.get(team, 1500)
        for home, away, hs, aws in completed_fixtures:
            self.elo_system.update_ratings(home, away, hs, aws, match_type='league')

    def save_state(self):
        return {
            'ratings': dict(self.elo_system.ratings), 
            'stats': {t: dict(s) for t, s in self.team_stats.items()}
        }

    def restore_state(self, state):
        self.elo_system.ratings = defaultdict(lambda: 1500)
        self.elo_system.ratings.update(state['ratings'])
        self.team_stats = {t: dict(s) for t, s in state['stats'].items()}

    def update_team_stats(self, home, away, hs, aws):
        self.team_stats[home]['played'] += 1; self.team_stats[home]['gf'] += hs; self.team_stats[home]['ga'] += aws
        self.team_stats[away]['played'] += 1; self.team_stats[away]['gf'] += aws; self.team_stats[away]['ga'] += hs
        if hs > aws:
            self.team_stats[home]['won'] += 1; self.team_stats[home]['points'] += 3; self.team_stats[away]['lost'] += 1
        elif hs < aws:
            self.team_stats[away]['won'] += 1; self.team_stats[away]['points'] += 3; self.team_stats[home]['lost'] += 1
        else:
            self.team_stats[home]['drawn'] += 1; self.team_stats[away]['drawn'] += 1
            self.team_stats[home]['points'] += 1; self.team_stats[away]['points'] += 1

    def simulate_fixtures(self, fixtures):
        for h, a in fixtures:
            hs, aws = self.elo_system.predict_score(h, a)
            self.elo_system.update_ratings(h, a, hs, aws, match_type='league')
            self.update_team_stats(h, a, hs, aws)

    def get_league_table(self):
        teams = list(self.team_stats.keys())
        teams.sort(key=lambda t: (
            self.team_stats[t]['points'], 
            self.team_stats[t]['gf'] - self.team_stats[t]['ga'], 
            self.team_stats[t]['gf']
        ), reverse=True)
        return teams

    def run_monte_carlo_simulations(self, phase1_fixtures, baseline, num_simulations=2500):
        teams = list(baseline['stats'].keys())
        champ_counts = {t: 0 for t in teams}
        euro_counts = {t: 0 for t in teams}
        top6_counts = {t: 0 for t in teams}
        rel_play_counts = {t: 0 for t in teams}
        rel_counts = {t: 0 for t in teams}
        avg_points = {t: [] for t in teams}

        for _ in tqdm(range(num_simulations), desc="Simulating", unit="sim"):
            self.restore_state(baseline)
            
            # Phase 1: 33 Games
            self.simulate_fixtures(phase1_fixtures)
            
            # The Split
            table_phase1 = self.get_league_table()
            top6 = table_phase1[:6]
            bottom6 = table_phase1[6:]
            
            for team in top6: top6_counts[team] += 1
            
            # Phase 2: 5 Games within groups
            top6_fixtures = generate_round_robin(top6)
            bottom6_fixtures = generate_round_robin(bottom6)
            self.simulate_fixtures(top6_fixtures + bottom6_fixtures)
            
            # Final Table with "Golden Rule" (Groups cannot cross)
            top6_stats = {t: self.team_stats[t] for t in top6}
            bottom6_stats = {t: self.team_stats[t] for t in bottom6}
            
            sorted_top6 = sorted(top6, key=lambda t: (
                top6_stats[t]['points'], top6_stats[t]['gf'] - top6_stats[t]['ga'], top6_stats[t]['gf']
            ), reverse=True)
            
            sorted_bottom6 = sorted(bottom6, key=lambda t: (
                bottom6_stats[t]['points'], bottom6_stats[t]['gf'] - bottom6_stats[t]['ga'], bottom6_stats[t]['gf']
            ), reverse=True)
            
            ft = sorted_top6 + sorted_bottom6
            
            # Track Outcomes
            champ_counts[ft[0]] += 1                 # 1st: Champion
            for team in ft[1:5]: euro_counts[team] += 1  # 2nd-5th: Europe
            rel_play_counts[ft[10]] += 1             # 11th: Relegation Playoff
            rel_counts[ft[11]] += 1                  # 12th: Auto Relegated
            
            for team in teams:
                avg_points[team].append(self.team_stats[team]['points'])

        return (champ_counts, euro_counts, top6_counts, rel_play_counts, rel_counts, avg_points)

    def print_predicted_table(self, champ, euro, top6, rel_play, rel, avg_pts, n):
        teams = sorted(avg_pts.keys(), key=lambda t: np.mean(avg_pts[t]), reverse=True)
        
        print("\n" + "=" * 100)
        print(f"SCOTTISH PREMIERSHIP PREDICTED FINAL TABLE ({n:,} Monte Carlo Simulations)")
        print("=" * 100)
        print(f"{'Pos':<4} {'Team':<16} {'Avg Pts':<9} {'Champ%':<8} {'Europe%':<9} {'Top 6%':<8} {'Rel Pl%':<9} {'Rel%':<6}")
        print("-" * 100)
        
        for i, team in enumerate(teams, 1):
            avg_p = np.mean(avg_pts[team])
            champ_pct = (champ[team] / n) * 100
            euro_pct = (euro[team] / n) * 100
            top6_pct = (top6[team] / n) * 100
            rel_play_pct = (rel_play[team] / n) * 100
            rel_pct = (rel[team] / n) * 100
            print(f"{i:<4} {team:<16} {avg_p:<9.1f} {champ_pct:<8.1f} {euro_pct:<9.1f} {top6_pct:<8.1f} {rel_play_pct:<9.1f} {rel_pct:<6.1f}")
            
        print("=" * 100)
        print("Champ%: Wins the league | Europe%: Qualifies for Europe (2nd-5th) | Top 6%: Makes Championship Split")
        print("Rel Pl%: Relegation Playoff (11th) | Rel%: Automatic Relegation (12th)")

def main():
    random.seed(42)
    np.random.seed(42)

    sim = LeagueSimulator()
    sim.load_current_standings()
    sim.initialize_elos_from_results(COMPLETED_FIXTURES)
    baseline = sim.save_state()

    print("Running 2,500 Monte Carlo simulations (incorporating the 33-game Split logic)...\n")
    results = sim.run_monte_carlo_simulations(phase1_fixtures=PHASE1_REMAINING, baseline=baseline, num_simulations=2500)
    sim.print_predicted_table(*results, n=2500)

if __name__ == "__main__":
    main()