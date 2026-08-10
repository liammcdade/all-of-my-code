#!/usr/bin/env python3
"""
Simplified National League North 2025-26 Season Predictor
Outputs the predicted final table with average points and probabilities.
"""

import random
import math
import numpy as np
from collections import defaultdict
from itertools import permutations
from tqdm import tqdm

# ===============================
# MATCHDAY 1 RESULTS (Sat 8 Aug)
# ===============================
COMPLETED_FIXTURES = [
    ("Buxton", "Hereford Utd", 2, 1), ("Chorley", "Chester", 1, 2),
    ("Darlington", "Worksop Town", 1, 2), ("Hebburn Town", "Southport", 3, 1),
    ("Kings Lynn", "Harborough Town", 1, 1), ("Marine", "Macclesfield", 0, 1),
    ("Merthyr Town", "Hednesford", 2, 0), ("Morecambe", "Spennymoor", 1, 1),
    ("Oxford City", "Bedford Town", 1, 0), ("Radcliffe", "Spalding Utd", 0, 2),
    ("Scarborough", "South Shields", 0, 1), ("Telford Utd", "Brackley Town", 1, 2),
]

CURRENT_STANDINGS = [
    ("Hebburn Town", 1, 1, 0, 0, 2, 3, 1, "W", 3), ("Merthyr Town", 1, 1, 0, 0, 2, 2, 0, "W", 3),
    ("Spalding Utd", 1, 1, 0, 0, 2, 2, 0, "W", 3), ("Brackley Town", 1, 1, 0, 0, 1, 2, 1, "W", 3),
    ("Buxton", 1, 1, 0, 0, 1, 2, 1, "W", 3), ("Chester", 1, 1, 0, 0, 1, 2, 1, "W", 3),
    ("Worksop Town", 1, 1, 0, 0, 1, 2, 1, "W", 3), ("Macclesfield", 1, 1, 0, 0, 1, 1, 0, "W", 3),
    ("Oxford City", 1, 1, 0, 0, 1, 1, 0, "W", 3), ("South Shields", 1, 1, 0, 0, 1, 1, 0, "W", 3),
    ("Harborough Town", 1, 0, 1, 0, 0, 1, 1, "D", 1), ("Kings Lynn", 1, 0, 1, 0, 0, 1, 1, "D", 1),
    ("Morecambe", 1, 0, 1, 0, 0, 1, 1, "D", 1), ("Spennymoor", 1, 0, 1, 0, 0, 1, 1, "D", 1),
    ("Chorley", 1, 0, 0, 1, -1, 1, 2, "L", 0), ("Darlington", 1, 0, 0, 1, -1, 1, 2, "L", 0),
    ("Hereford Utd", 1, 0, 0, 1, -1, 1, 2, "L", 0), ("Telford Utd", 1, 0, 0, 1, -1, 1, 2, "L", 0),
    ("Bedford Town", 1, 0, 0, 1, -1, 0, 1, "L", 0), ("Marine", 1, 0, 0, 1, -1, 0, 1, "L", 0),
    ("Scarborough", 1, 0, 0, 1, -1, 0, 1, "L", 0), ("Southport", 1, 0, 0, 1, -2, 1, 3, "L", 0),
    ("Hednesford", 1, 0, 0, 1, -2, 0, 2, "L", 0), ("Radcliffe", 1, 0, 0, 1, -2, 0, 2, "L", 0),
]

BASE_ELO = 1500
MAX_GAMES = 46

wdl_rates = {}
for team, p, w, d, l, gd, gf, ga, l5, pts in CURRENT_STANDINGS:
    wdl_rates[team] = {"win": w/p, "draw": d/p, "loss": l/p}

form_adjustment = {}
for team, p, w, d, l, gd, gf, ga, l5, pts in CURRENT_STANDINGS:
    pts_l5 = sum(3 if r == 'W' else (1 if r == 'D' else 0) for r in l5)
    form_adjustment[team] = ((pts_l5 - len(l5)*1.5) * 10) * 0.5

def get_adjusted_elo(team, ratings_dict):
    base = ratings_dict.get(team, BASE_ELO)
    return base + form_adjustment.get(team, 0)

def generate_remaining_fixtures(teams, completed):
    completed_set = {(h, a) for h, a, _, _ in completed}
    fixtures = [(h, a) for h, a in permutations(teams, 2) if (h, a) not in completed_set]
    random.shuffle(fixtures)
    return fixtures

ALL_TEAMS = [t[0] for t in CURRENT_STANDINGS]
REMAINING_FIXTURES = generate_remaining_fixtures(ALL_TEAMS, COMPLETED_FIXTURES)

class OptimizedELORatingSystem:
    def __init__(self, k_factor=30, home_advantage=85):
        self.k_factor = k_factor
        self.home_advantage = home_advantage
        self.ratings = defaultdict(lambda: BASE_ELO)
        self.match_weights = {'league': 1.5, 'playoff_qf': 2.0, 'playoff_sf': 2.5, 'playoff_final': 3.0}

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

    def predict_match(self, home, away, neutral=False):
        ha = 0 if neutral else self.home_advantage
        return 1 / (1 + 10 ** (-(self.ratings[home] - self.ratings[away] + ha) / 400))

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

    def decide_knockout(self, home, away, neutral=False, match_type='playoff_qf'):
        return home if self.predict_match(home, away, neutral) >= 0.5 else away

class LeagueSimulator:
    def __init__(self):
        self.elo_system = OptimizedELORatingSystem()
        self.team_stats = {}

    def load_current_standings(self):
        for team, p, w, d, l, gd, gf, ga, l5, pts in CURRENT_STANDINGS:
            self.team_stats[team] = {'played': p, 'won': w, 'drawn': d, 'lost': l, 'gf': gf, 'ga': ga, 'points': pts}

    def initialize_elos_from_results(self, completed_fixtures):
        for team in self.team_stats: 
            self.elo_system.ratings[team] = BASE_ELO
        for home, away, hs, aws in completed_fixtures:
            self.elo_system.update_ratings(home, away, hs, aws, match_type='league')

    def save_state(self):
        # Deep copy both ratings and stats
        return {
            'ratings': dict(self.elo_system.ratings), 
            'stats': {t: dict(s) for t, s in self.team_stats.items()}
        }

    def restore_state(self, state):
        # Properly reset ratings defaultdict
        self.elo_system.ratings = defaultdict(lambda: BASE_ELO)
        self.elo_system.ratings.update(state['ratings'])
        
        # Properly reset team_stats as a regular dict to avoid defaultdict accumulation issues
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

    def simulate_playoffs(self, final_table):
        pos2, pos3, pos4, pos5, pos6, pos7 = final_table[1], final_table[2], final_table[3], final_table[4], final_table[5], final_table[6]
        qf1_winner = self.elo_system.decide_knockout(pos4, pos7, match_type='playoff_qf')
        qf2_winner = self.elo_system.decide_knockout(pos5, pos6, match_type='playoff_qf')
        qf_winners = sorted([qf1_winner, qf2_winner], key=lambda t: final_table.index(t))
        sf1_winner = self.elo_system.decide_knockout(pos2, qf_winners[1], match_type='playoff_sf')
        sf2_winner = self.elo_system.decide_knockout(pos3, qf_winners[0], match_type='playoff_sf')
        return self.elo_system.decide_knockout(sf1_winner, sf2_winner, neutral=True, match_type='playoff_final')

    def run_monte_carlo_simulations(self, fixtures, baseline, num_simulations=2500):
        teams = list(baseline['stats'].keys())
        promotion_counts = {t: 0 for t in teams}
        top7_counts = {t: 0 for t in teams}
        releg = {t: 0 for t in teams}
        avg_points = {t: [] for t in teams}

        for _ in tqdm(range(num_simulations), desc="Simulating", unit="sim"):
            self.restore_state(baseline)
            self.simulate_fixtures(fixtures)
            ft = self.get_league_table()
            
            promotion_counts[ft[0]] += 1  # Champion
            for team in ft[:7]: 
                top7_counts[team] += 1
            
            if len(ft) >= 7:
                pw = self.simulate_playoffs(ft)
                promotion_counts[pw] += 1  # Playoff Winner
                
            for pos, team in enumerate(ft, 1):
                if pos >= 21: 
                    releg[team] += 1
                avg_points[team].append(self.team_stats[team]['points'])

        return (promotion_counts, top7_counts, releg, avg_points)

    def print_predicted_table(self, prom, top7, rel, avg_pts, n):
        teams = sorted(avg_pts.keys(), key=lambda t: np.mean(avg_pts[t]), reverse=True)
        
        print("\n" + "=" * 85)
        print(f"PREDICTED FINAL TABLE ({n:,} Monte Carlo Simulations)")
        print("=" * 85)
        print(f"{'Pos':<4} {'Team':<20} {'Avg Pts':<10} {'Prom %':<10} {'Top 7 %':<10} {'Rel %':<10}")
        print("-" * 85)
        
        for i, team in enumerate(teams, 1):
            avg_p = np.mean(avg_pts[team])
            prom_pct = (prom[team] / n) * 100
            top7_pct = (top7[team] / n) * 100
            rel_pct = (rel[team] / n) * 100
            print(f"{i:<4} {team:<20} {avg_p:<10.1f} {prom_pct:<10.1f} {top7_pct:<10.1f} {rel_pct:<10.1f}")
            
        print("=" * 85)
        print("Prom %: Probability of winning the league OR winning the playoffs.")
        print("Top 7 %: Probability of qualifying for the playoffs.")
        print("Rel %: Probability of finishing in the relegation zone (21st-24th).")

def main():
    random.seed(42)
    np.random.seed(42)

    sim = LeagueSimulator()
    sim.load_current_standings()
    sim.initialize_elos_from_results(COMPLETED_FIXTURES)
    baseline = sim.save_state()

    print("Running 2,500 Monte Carlo simulations...\n")
    results = sim.run_monte_carlo_simulations(fixtures=REMAINING_FIXTURES, baseline=baseline, num_simulations=2500)
    sim.print_predicted_table(*results, n=2500)

if __name__ == "__main__":
    main()