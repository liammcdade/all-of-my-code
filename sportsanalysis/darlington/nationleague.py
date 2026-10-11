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
# COMPLETED FIXTURES (All played matches)
# ===============================
COMPLETED_FIXTURES = [
    # Matchday 1
    ("Telford Utd", "Brackley Town", 1, 2),
    ("Buxton", "Hereford Utd", 2, 1),
    ("Chorley", "Chester", 1, 2),
    ("Darlington", "Worksop Town", 1, 2),
    ("Hebburn Town", "Southport", 3, 1),
    ("Kings Lynn", "Harborough Town", 1, 1),
    ("Marine", "Macclesfield", 0, 1),
    ("Merthyr Town", "Hednesford", 2, 0),
    ("Morecambe", "Spennymoor", 1, 1),
    ("Oxford City", "Bedford Town", 1, 0),
    ("Radcliffe", "Spalding Utd", 0, 2),
    ("Scarborough", "South Shields", 0, 1),
    # Matchday 2
    ("Bedford Town", "Darlington", 2, 3),
    ("Brackley Town", "Hebburn Town", 1, 1),
    ("Chester", "Kings Lynn", 2, 0),
    ("Harborough Town", "Morecambe", 1, 0),
    ("Hednesford", "Scarborough", 3, 4),
    ("Hereford Utd", "Marine", 1, 0),
    ("Macclesfield", "Radcliffe", 2, 1),
    ("South Shields", "Chorley", 2, 1),
    ("Southport", "Buxton", 1, 1),
    ("Spalding Utd", "Oxford City", 0, 1),
    ("Spennymoor", "Merthyr Town", 2, 1),
    ("Worksop Town", "Telford Utd", 2, 1),
    # Matchday 3
    ("Bedford Town", "Buxton", 2, 1),
    ("Brackley Town", "Kings Lynn", 0, 2),
    ("Darlington", "Chester", 0, 1),
    ("Hebburn Town", "Worksop Town", 1, 0),
    ("Hednesford", "Southport", 2, 2),
    ("Hereford Utd", "Radcliffe", 3, 0),
    ("Marine", "Chorley", 0, 2),
    ("Merthyr Town", "Telford Utd", 2, 2),
    ("Morecambe", "South Shields", 0, 1),
    ("Oxford City", "Harborough Town", 1, 1),
    ("Scarborough", "Spennymoor", 3, 0),
    ("Spalding Utd", "Macclesfield", 0, 0),
    # Matchday 4
    ("Telford Utd", "Hednesford", 1, 1),
    ("Buxton", "Hebburn Town", 1, 2),
    ("Chester", "Spalding Utd", 1, 0),
    ("Chorley", "Scarborough", 2, 1),
    ("Harborough Town", "Darlington", 4, 2),
    ("Kings Lynn", "Marine", 1, 4),
    ("Macclesfield", "Brackley Town", 2, 1),
    ("Radcliffe", "Morecambe", 2, 1),
    ("South Shields", "Merthyr Town", 1, 1),
    ("Southport", "Bedford Town", 4, 1),
    ("Spennymoor", "Oxford City", 1, 4),
    ("Worksop Town", "Hereford Utd", 0, 3),
    # Matchday 5
    ("Hednesford", "Harborough Town", 2, 1),
    ("Morecambe", "Telford Utd", 2, 1),
    ("Oxford City", "Buxton", 2, 3),
    ("Bedford Town", "Spennymoor", 3, 1),
    ("Darlington", "Macclesfield", 1, 2),
    ("Hebburn Town", "Kings Lynn", 4, 2),
    ("Hereford Utd", "Chester", 1, 1),
    ("Marine", "Radcliffe", 2, 0),
    ("Merthyr Town", "Chorley", 1, 1),
    ("Scarborough", "Southport", 5, 1),
    ("Spalding Utd", "Worksop Town", 3, 1),
    # Matchday 6
    ("Telford Utd", "Bedford Town", 0, 1),
    ("Buxton", "Merthyr Town", 2, 1),
    ("Chester", "Morecambe", 0, 1),
    ("Chorley", "Brackley Town", 2, 2),
    ("Harborough Town", "Marine", 2, 1),
    ("Kings Lynn", "Scarborough", 3, 1),
    ("Macclesfield", "Hebburn Town", 3, 0),
    ("Radcliffe", "Darlington", 0, 1),
    ("South Shields", "Spalding Utd", 1, 1),
    ("Southport", "Hereford Utd", 0, 1),
    ("Spennymoor", "Hednesford", 1, 1),
    ("Worksop Town", "Oxford City", 0, 1),
    # Matchday 7
    ("Bedford Town", "Radcliffe", 1, 0),
    ("Brackley Town", "Harborough Town", 1, 0),
    ("Darlington", "Kings Lynn", 0, 2),
    ("Hebburn Town", "Chester", 1, 1),
    ("Hednesford", "South Shields", 0, 1),
    ("Hereford Utd", "Spennymoor", 2, 1),
    ("Marine", "Worksop Town", 0, 1),
    ("Merthyr Town", "Macclesfield", 2, 1),
    ("Morecambe", "Buxton", 4, 0),
    ("Oxford City", "Chorley", 4, 0),
    ("Scarborough", "Telford Utd", 0, 1),
    ("Spalding Utd", "Southport", 2, 0),
    # Matchday 8
    ("Telford Utd", "Oxford City", 1, 0),
    ("Buxton", "Brackley Town", 5, 0),
    ("Chester", "Merthyr Town", 0, 1),
    ("Chorley", "Darlington", 5, 2),
    ("Harborough Town", "Hereford Utd", 0, 3),
    ("Kings Lynn", "Hednesford", 2, 3),
    ("Macclesfield", "Scarborough", 0, 0),
    ("Radcliffe", "Hebburn Town", 5, 1),
    ("South Shields", "Marine", 2, 1),
    ("Southport", "Morecambe", 2, 1),
    ("Spennymoor", "Spalding Utd", 1, 3),
    ("Worksop Town", "Bedford Town", 1, 2),

    ("Buxton", "Chester", 3, 1),
    ("Harborough Town", "Telford Utd", 0, 0),
    ("Hereford Utd", "South Shields", 6, 0),
    ("Kings Lynn", "Chorley", 2, 0),
    ("Marine", "Darlington", 2, 1),
    ("Morecambe", "Brackley Town", 3, 0),
    ("Radcliffe", "Oxford City", 0, 3),
    ("Scarborough", "Merthyr Town", 0, 0),
    ("Spalding Utd", "Bedford Town", 2, 1),
    ("Spennymoor", "Macclesfield", 1, 1),
    ("Worksop Town", "Southport", 2, 0),
    ("Hebburn Town", "Hednesford", 2, 1),


]

def calculate_standings(fixtures):
    """Calculate standings from completed fixtures"""
    stats = defaultdict(lambda: {
        'played': 0, 'won': 0, 'drawn': 0, 'lost': 0,
        'gf': 0, 'ga': 0, 'points': 0
    })
    
    for home, away, hs, aws in fixtures:
        # Home team stats
        stats[home]['played'] += 1
        stats[home]['gf'] += hs
        stats[home]['ga'] += aws
        
        # Away team stats
        stats[away]['played'] += 1
        stats[away]['gf'] += aws
        stats[away]['ga'] += hs
        
        if hs > aws:
            stats[home]['won'] += 1
            stats[home]['points'] += 3
            stats[away]['lost'] += 1
        elif hs < aws:
            stats[away]['won'] += 1
            stats[away]['points'] += 3
            stats[home]['lost'] += 1
        else:
            stats[home]['drawn'] += 1
            stats[away]['drawn'] += 1
            stats[home]['points'] += 1
            stats[away]['points'] += 1
    
    # Build standings with form (last 5 results)
    standings = []
    for team, s in stats.items():
        # Get last 5 results for this team
        last5 = []
        for h, a, hs, aws in reversed(fixtures):
            if h == team:
                if hs > aws:
                    last5.append('W')
                elif hs < aws:
                    last5.append('L')
                else:
                    last5.append('D')
            elif a == team:
                if aws > hs:
                    last5.append('W')
                elif aws < hs:
                    last5.append('L')
                else:
                    last5.append('D')
            if len(last5) >= 5:
                break
        # Pad with '-' if fewer than 5 games
        while len(last5) < 5:
            last5.append('-')
        last5 = ''.join(last5[:5])
        
        gd = s['gf'] - s['ga']
        standings.append((
            team,
            s['played'],
            s['won'],
            s['drawn'],
            s['lost'],
            gd,
            s['gf'],
            s['ga'],
            last5,
            s['points']
        ))
    
    # Sort by points, then goal difference, then goals for
    standings.sort(key=lambda x: (x[9], x[5], x[6]), reverse=True)
    return standings

# Calculate standings from fixtures
CURRENT_STANDINGS = calculate_standings(COMPLETED_FIXTURES)

BASE_ELO = 1500
MAX_GAMES = 46

wdl_rates = {}
for team, p, w, d, l, gd, gf, ga, l5, pts in CURRENT_STANDINGS:
    # Avoid division by zero if p=0
    if p > 0:
        wdl_rates[team] = {"win": w/p, "draw": d/p, "loss": l/p}
    else:
        wdl_rates[team] = {"win": 0.33, "draw": 0.33, "loss": 0.33}

form_adjustment = {}
for team, p, w, d, l, gd, gf, ga, l5, pts in CURRENT_STANDINGS:
    if p > 0:
        pts_l5 = sum(3 if r == 'W' else (1 if r == 'D' else 0) for r in l5 if r != '-')
        games_in_l5 = sum(1 for r in l5 if r != '-')
        if games_in_l5 > 0:
            form_adjustment[team] = ((pts_l5 / games_in_l5 - 1.5) * 10) * 0.3  # Reduced from 0.5
        else:
            form_adjustment[team] = 0
    else:
        form_adjustment[team] = 0

def get_adjusted_elo(team, ratings_dict):
    base = ratings_dict.get(team, BASE_ELO)
    return base + form_adjustment.get(team, 0)

def generate_remaining_fixtures(teams, completed):
    completed_set = {(h, a) for h, a, _, _ in completed}
    # For a double round-robin, each team plays every other team twice
    fixtures = []
    for h, a in permutations(teams, 2):
        if (h, a) not in completed_set:
            fixtures.append((h, a))
    random.shuffle(fixtures)
    return fixtures

# Get all teams from completed fixtures
ALL_TEAMS = sorted(set([h for h, _, _, _ in COMPLETED_FIXTURES] + [a for _, a, _, _ in COMPLETED_FIXTURES]))
REMAINING_FIXTURES = generate_remaining_fixtures(ALL_TEAMS, COMPLETED_FIXTURES)

class OptimizedELORatingSystem:
    def __init__(self, k_factor=20, home_advantage=60):  # Reduced K-factor and home advantage
        self.k_factor = k_factor
        self.home_advantage = home_advantage
        self.ratings = defaultdict(lambda: BASE_ELO)
        self.match_weights = {'league': 1.0, 'playoff_qf': 1.2, 'playoff_sf': 1.3, 'playoff_final': 1.5}  # Reduced multipliers

    def expected_score(self, ra, rb):
        return 1 / (1 + 10 ** ((rb - ra) / 400))

    def update_ratings(self, home, away, hs, aws, match_type='league'):
        K = self.k_factor * self.match_weights.get(match_type, 1.0)
        hr, ar = self.ratings[home] + self.home_advantage, self.ratings[away]
        gm = min(1 + math.log(1 + abs(hs - aws)), 1.5)  # Reduced goal margin impact
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
        
        # Get wdl rates safely
        home_wdl = wdl_rates.get(home, {"win": 0.33, "draw": 0.33, "loss": 0.33})
        away_wdl = wdl_rates.get(away, {"win": 0.33, "draw": 0.33, "loss": 0.33})
        
        bd = ((home_wdl["win"] - home_wdl["loss"]) - (away_wdl["win"] - away_wdl["loss"])) * 0.5
        hxg, axg = hxg + bd * 0.15, axg - bd * 0.15
        tempo = 0.9 + 0.1 * (abs(diff) / 400)
        hxg, axg = hxg * tempo, axg * tempo
        vb = 1 + (home_wdl["win"] - home_wdl["draw"]) * 0.1
        db = max((home_wdl["draw"] + away_wdl["draw"]) / 2, 0.3)
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
        return {
            'ratings': dict(self.elo_system.ratings), 
            'stats': {t: dict(s) for t, s in self.team_stats.items()}
        }

    def restore_state(self, state):
        self.elo_system.ratings = defaultdict(lambda: BASE_ELO)
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
        
        print("\n" + "=" * 100)
        print(f"PREDICTED FINAL TABLE ({n:,} Monte Carlo Simulations)")
        print("=" * 100)
        print(f"{'Pos':<4} {'Team':<20} {'Current':<8} {'Avg Pts':<10} {'Prom %':<10} {'Top 7 %':<10} {'Rel %':<10}")
        print(f"{'':<4} {'':<20} {'ELO':<8} {'':<10} {'':<10} {'':<10} {'':<10}")
        print("-" * 100)
        
        for i, team in enumerate(teams, 1):
            avg_p = np.mean(avg_pts[team])
            prom_pct = (prom[team] / n) * 100
            top7_pct = (top7[team] / n) * 100
            rel_pct = (rel[team] / n) * 100
            current_elo = int(self.elo_system.ratings.get(team, BASE_ELO))
            print(f"{i:<4} {team:<20} {current_elo:<8} {avg_p:<10.1f} {prom_pct:<10.1f} {top7_pct:<10.1f} {rel_pct:<10.1f}")
            
        print("=" * 100)
        print("Prom %: Probability of winning the league OR winning the playoffs.")
        print("Top 7 %: Probability of qualifying for the playoffs.")
        print("Rel %: Probability of finishing in the relegation zone (21st-24th).")
        print("Current ELO: ELO rating after completed fixtures (before form adjustment).")

def main():
    random.seed(42)
    np.random.seed(42)

    sim = LeagueSimulator()
    sim.load_current_standings()
    sim.initialize_elos_from_results(COMPLETED_FIXTURES)
    baseline = sim.save_state()

    print(f"Current standings from {len(COMPLETED_FIXTURES)} completed fixtures:")
    print("-" * 95)
    print(f"{'Pos':<4} {'Team':<20} {'P':<4} {'W':<4} {'D':<4} {'L':<4} {'GD':<5} {'Pts':<4} {'ELO':<8} {'Form':<6}")
    print("-" * 95)
    for i, (team, p, w, d, l, gd, gf, ga, l5, pts) in enumerate(CURRENT_STANDINGS, 1):
        elo = int(sim.elo_system.ratings.get(team, BASE_ELO))
        print(f"{i:<4} {team:<20} {p:<4} {w:<4} {d:<4} {l:<4} {gd:<5} {pts:<4} {elo:<8} {l5:<6}")
    print("-" * 95)
    print(f"Remaining fixtures: {len(REMAINING_FIXTURES)}")
    print(f"Total fixtures per team: {len(REMAINING_FIXTURES) * 2 // len(ALL_TEAMS) + min(8, 0)} games played + remaining")
    print("\nRunning 2,500 Monte Carlo simulations...\n")
    
    results = sim.run_monte_carlo_simulations(fixtures=REMAINING_FIXTURES, baseline=baseline, num_simulations=2500)
    sim.print_predicted_table(*results, n=2500)

if __name__ == "__main__":
    main()