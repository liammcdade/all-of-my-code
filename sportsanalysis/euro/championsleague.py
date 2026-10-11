#!/usr/bin/env python3
"""
Champions League 2025‑26 Predictor
- Uses completed fixtures (with scores) to train an ELO system.
- Simulates the remaining league fixtures.
- Then simulates the knockout phase (play‑offs to final).
- Outputs predicted final table and champion probabilities.
"""

import random
import math
import numpy as np
from collections import defaultdict
from tqdm import tqdm

# ===============================
# COMPLETED FIXTURES (matches already played with scores)
# ===============================
COMPLETED_FIXTURES = [
    # Matchday 1 – all 18 completed
    ("AEK Athens", "LASK", 1, 0),
    ("Club Brugge", "Aston Villa", 2, 3),
    ("Borussia Dortmund", "Villarreal", 3, 2),
    ("Porto", "Manchester City", 0, 2),
    ("Lille", "Real Betis", 2, 3),
    ("Real Madrid", "Inter Milan", 2, 1),
    ("Barcelona", "Feyenoord", 5, 1),
    ("VfB Stuttgart", "Viking", 3, 1),
    ("Liverpool", "Atlético Madrid", 2, 1),
    ("Paris Saint-Germain", "Slovan Bratislava", 6, 1),
    ("Sporting CP", "Galatasaray", 3, 1),
    ("Napoli", "Arsenal", 0, 1),
    ("Fenerbahçe", "Roma", 1, 1),
    ("PSV Eindhoven", "Shakhtar Donetsk", 1, 1),
    ("Como", "RB Leipzig", 4, 1),
    ("Bayern Munich", "Bodø/Glimt", 5, 0),
    ("Manchester United", "Sabah", 4, 0),
    ("Slavia Prague", "Lens", 2, 3),
]
# ===============================
# REMAINING FIXTURES (unplayed matches, no scores yet)
# Now stored as (home, away) – scores are omitted
# ===============================
REMAINING_FIXTURES = [

    # Matchday 2
    ("Lens", "Sporting CP"),
    ("Sabah", "Slavia Prague"),
    ("Arsenal", "Lille"),
    ("Atlético Madrid", "Manchester United"),
    ("Inter Milan", "Club Brugge"),
    ("Galatasaray", "Barcelona"),
    ("RB Leipzig", "PSV Eindhoven"),
    ("Viking", "Bayern Munich"),
    ("Villarreal", "Napoli"),
    ("Feyenoord", "Como"),
    ("LASK", "Liverpool"),
    ("Roma", "Real Madrid"),
    ("Aston Villa", "Fenerbahçe"),
    ("Shakhtar Donetsk", "AEK Athens"),
    ("Bodø/Glimt", "Borussia Dortmund"),
    ("Manchester City", "Paris Saint-Germain"),
    ("Real Betis", "Porto"),
    ("Slovan Bratislava", "VfB Stuttgart"),
    # Matchday 3
    ("Fenerbahçe", "Slavia Prague"),
    ("Sabah", "Borussia Dortmund"),
    ("Roma", "Slovan Bratislava"),
    ("Porto", "PSV Eindhoven"),
    ("Liverpool", "Villarreal"),
    ("Manchester City", "AEK Athens"),
    ("Paris Saint-Germain", "Barcelona"),
    ("Napoli", "Bodø/Glimt"),
    ("VfB Stuttgart", "Atlético Madrid"),
    ("Como", "Manchester United"),
    ("Lille", "Galatasaray"),
    ("Aston Villa", "Viking"),
    ("Club Brugge", "Lens"),
    ("Bayern Munich", "Arsenal"),
    ("Inter Milan", "Shakhtar Donetsk"),
    ("Real Madrid", "RB Leipzig"),
    ("Real Betis", "Feyenoord"),
    ("Sporting CP", "LASK"),
    # Matchday 4
    ("Shakhtar Donetsk", "Sporting CP"),
    ("Galatasaray", "VfB Stuttgart"),
    ("Atlético Madrid", "Bayern Munich"),
    ("Barcelona", "Aston Villa"),
    ("Feyenoord", "Inter Milan"),
    ("Bodø/Glimt", "Lille"),
    ("LASK", "Slovan Bratislava"),
    ("Manchester United", "Roma"),
    ("Villarreal", "Paris Saint-Germain"),
    ("AEK Athens", "Real Madrid"),
    ("Fenerbahçe", "Liverpool"),
    ("Borussia Dortmund", "Real Betis"),
    ("Porto", "Napoli"),
    ("PSV Eindhoven", "Club Brugge"),
    ("RB Leipzig", "Manchester City"),
    ("Lens", "Como"),
    ("Slavia Prague", "Arsenal"),
    ("Viking", "Sabah"),
    # Matchday 5
    ("Bodø/Glimt", "LASK"),
    ("Galatasaray", "Aston Villa"),
    ("Arsenal", "Borussia Dortmund"),
    ("Como", "AEK Athens"),
    ("Feyenoord", "Porto"),
    ("Manchester City", "Napoli"),
    ("RB Leipzig", "Lens"),
    ("Real Madrid", "PSV Eindhoven"),
    ("Slovan Bratislava", "Real Betis"),
    ("Sabah", "Barcelona"),
    ("Slavia Prague", "Villarreal"),
    ("Atlético Madrid", "Viking"),
    ("Club Brugge", "Liverpool"),
    ("Inter Milan", "VfB Stuttgart"),
    ("Shakhtar Donetsk", "Fenerbahçe"),
    ("Lille", "Bayern Munich"),
    ("Paris Saint-Germain", "Roma"),
    ("Sporting CP", "Manchester United"),
    # Matchday 6
    ("Viking", "Feyenoord"),
    ("Villarreal", "Sabah"),
    ("AEK Athens", "Galatasaray"),
    ("Roma", "Sporting CP"),
    ("Aston Villa", "Paris Saint-Germain"),
    ("Barcelona", "Manchester City"),
    ("Bayern Munich", "Slavia Prague"),
    ("Manchester United", "RB Leipzig"),
    ("Napoli", "Club Brugge"),
    ("Real Betis", "Como"),
    ("Slovan Bratislava", "Shakhtar Donetsk"),
    ("Arsenal", "Real Madrid"),
    ("Borussia Dortmund", "Inter Milan"),
    ("LASK", "Fenerbahçe"),
    ("Liverpool", "Porto"),
    ("PSV Eindhoven", "Atlético Madrid"),
    ("Lens", "Bodø/Glimt"),
    ("VfB Stuttgart", "Lille"),
    # Matchday 7
    ("Bodø/Glimt", "Atlético Madrid"),
    ("Galatasaray", "Feyenoord"),
    ("AEK Athens", "Roma"),
    ("Aston Villa", "Borussia Dortmund"),
    ("Inter Milan", "Liverpool"),
    ("Porto", "Slavia Prague"),
    ("Lille", "Slovan Bratislava"),
    ("Real Madrid", "LASK"),
    ("VfB Stuttgart", "Club Brugge"),
    ("Fenerbahçe", "Villarreal"),
    ("Sabah", "Napoli"),
    ("Como", "Paris Saint-Germain"),
    ("Manchester United", "Bayern Munich"),
    ("RB Leipzig", "Shakhtar Donetsk"),
    ("Lens", "Manchester City"),
    ("Real Betis", "Arsenal"),
    ("Sporting CP", "Barcelona"),
    ("Viking", "PSV Eindhoven"),
    # Matchday 8
    ("Arsenal", "Sabah"),
    ("Roma", "Lille"),
    ("Atlético Madrid", "Fenerbahçe"),
    ("Borussia Dortmund", "AEK Athens"),
    ("Club Brugge", "Bodø/Glimt"),
    ("Bayern Munich", "Real Betis"),
    ("Barcelona", "Como"),
    ("Shakhtar Donetsk", "Real Madrid"),
    ("Feyenoord", "RB Leipzig"),
    ("LASK", "Porto"),
    ("Liverpool", "Lens"),
    ("Manchester City", "Sporting CP"),
    ("Paris Saint-Germain", "Galatasaray"),
    ("PSV Eindhoven", "VfB Stuttgart"),
    ("Slavia Prague", "Aston Villa"),
    ("Napoli", "Viking"),
    ("Villarreal", "Manchester United"),
    ("Slovan Bratislava", "Inter Milan"),
]

# ===============================
# HELPERS: Standings calculation and team list
# ===============================
def calculate_standings(fixtures):
    """Calculate standings from a list of (home, away, hs, aws) with scores."""
    stats = defaultdict(lambda: {
        'played': 0, 'won': 0, 'drawn': 0, 'lost': 0,
        'gf': 0, 'ga': 0, 'points': 0
    })
    for home, away, hs, aws in fixtures:
        if hs is None or aws is None:
            continue  # skip unplayed matches
        stats[home]['played'] += 1
        stats[home]['gf'] += hs
        stats[home]['ga'] += aws
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
    standings = []
    for team, s in stats.items():
        gd = s['gf'] - s['ga']
        standings.append((team, s['played'], s['won'], s['drawn'], s['lost'],
                          gd, s['gf'], s['ga'], s['points']))
    standings.sort(key=lambda x: (x[8], x[5], x[6]), reverse=True)
    return standings, stats

def get_all_teams(completed, remaining):
    teams = set()
    for h, a, _, _ in completed:
        teams.add(h); teams.add(a)
    # Remaining fixtures are now (home, away) – unpack only two values
    for h, a in remaining:
        teams.add(h); teams.add(a)
    return sorted(teams)

ALL_TEAMS = get_all_teams(COMPLETED_FIXTURES, REMAINING_FIXTURES)

# ===============================
# ELO SYSTEM
# ===============================
BASE_ELO = 1500

class ELOSystem:
    def __init__(self, k=20, home_advantage=60):
        self.k = k
        self.home_advantage = home_advantage
        self.ratings = defaultdict(lambda: BASE_ELO)

    def expected(self, ra, rb):
        return 1 / (1 + 10 ** ((rb - ra) / 400))

    def update(self, home, away, hs, aws):
        hr = self.ratings[home] + self.home_advantage
        ar = self.ratings[away]
        eh = self.expected(hr, ar)
        ea = self.expected(ar, hr)
        gm = min(1 + math.log(1 + abs(hs - aws)), 1.5)
        ah = 1 if hs > aws else (0.5 if hs == aws else 0)
        aa = 1 if aws > hs else (0.5 if hs == aws else 0)
        self.ratings[home] += self.k * gm * (ah - eh)
        self.ratings[away] += self.k * gm * (aa - ea)

    def train(self, fixtures):
        for home, away, hs, aws in fixtures:
            if hs is not None and aws is not None:
                self.update(home, away, hs, aws)

    def predict_score(self, home, away, neutral=False):
        ha = 0 if neutral else self.home_advantage
        diff = self.ratings[home] - self.ratings[away] + ha
        hxg = 0.6 + 1.7 / (1 + math.exp(-diff / 400))
        axg = 0.6 + 1.7 / (1 + math.exp(diff / 400))
        hs = np.random.poisson(hxg)
        aws = np.random.poisson(axg)
        return hs, aws

    def simulate_two_legs(self, home, away):
        h1, a1 = self.predict_score(home, away, neutral=False)
        h2, a2 = self.predict_score(away, home, neutral=False)
        agg_home = h1 + a2
        agg_away = a1 + h2
        if agg_home > agg_away:
            return home
        elif agg_away > agg_home:
            return away
        else:
            hs, aws = self.predict_score(home, away, neutral=True)
            if hs > aws:
                return home
            elif aws > hs:
                return away
            else:
                return random.choice([home, away])

    def simulate_single_match(self, home, away, neutral=True):
        hs, aws = self.predict_score(home, away, neutral)
        if hs > aws:
            return home
        elif aws > hs:
            return away
        else:
            return random.choice([home, away])

# ===============================
# LEAGUE SIMULATION (remaining fixtures)
# ===============================
def simulate_remaining_fixtures(elo, remaining, completed, num_sims=10000):
    """
    Simulate the remaining fixtures many times.
    Returns:
      - avg_points: dict team -> list of points across simulations
      - rankings_sims: list of rankings (list of teams) for each sim
    """
    # Get standings and stats from completed fixtures
    base_standings, base_stats = calculate_standings(completed)

    # Pre‑initialize stats for ALL teams with zeros
    stats_template = {
        'played': 0, 'won': 0, 'drawn': 0, 'lost': 0,
        'gf': 0, 'ga': 0, 'points': 0
    }
    stats = {team: stats_template.copy() for team in ALL_TEAMS}

    # Overwrite with completed stats (for teams that have played)
    for team, s in base_stats.items():
        stats[team] = s.copy()  # safe copy

    # We'll keep track of points per team across sims
    avg_points = {team: [] for team in ALL_TEAMS}
    rankings_sims = []

    for _ in tqdm(range(num_sims), desc="Simulating league phase", unit="sim"):
        # Reset stats to the base (completed) state for this simulation
        sim_stats = {team: s.copy() for team, s in stats.items()}

        # Simulate each remaining fixture
        for home, away in remaining:  # remaining are (home, away) tuples
            hs, aws = elo.predict_score(home, away, neutral=False)

            # Update home team
            sim_stats[home]['played'] += 1
            sim_stats[home]['gf'] += hs
            sim_stats[home]['ga'] += aws
            # Update away team
            sim_stats[away]['played'] += 1
            sim_stats[away]['gf'] += aws
            sim_stats[away]['ga'] += hs

            if hs > aws:
                sim_stats[home]['won'] += 1
                sim_stats[home]['points'] += 3
                sim_stats[away]['lost'] += 1
            elif hs < aws:
                sim_stats[away]['won'] += 1
                sim_stats[away]['points'] += 3
                sim_stats[home]['lost'] += 1
            else:
                sim_stats[home]['drawn'] += 1
                sim_stats[away]['drawn'] += 1
                sim_stats[home]['points'] += 1
                sim_stats[away]['points'] += 1

        # Build standings list for this simulation
        sim_standings = []
        for team in ALL_TEAMS:
            s = sim_stats[team]
            gd = s['gf'] - s['ga']
            sim_standings.append((team, s['played'], s['won'], s['drawn'], s['lost'],
                                  gd, s['gf'], s['ga'], s['points']))
        sim_standings.sort(key=lambda x: (x[8], x[5], x[6]), reverse=True)

        rankings = [team for team, _, _, _, _, _, _, _, _ in sim_standings]
        rankings_sims.append(rankings)

        # Record points
        for team, _, _, _, _, _, _, _, pts in sim_standings:
            avg_points[team].append(pts)

    return avg_points, rankings_sims

# ===============================
# KNOCKOUT SIMULATION (based on final rankings)
# ===============================
def simulate_knockouts(elo, rankings, num_sims_per_tournament=1000):
    """
    Given a ranking list (1st to 36th), simulate the knockout bracket once.
    Returns the champion.
    """
    # Play-off pairs: 9th vs 24th, 10th vs 23rd, ... 16th vs 17th
    play_off_pairs = [(rankings[8+i], rankings[23-i]) for i in range(8)]
    seeds = rankings[:8]

    # Play-offs
    po_winners = []
    for h, a in play_off_pairs:
        po_winners.append(elo.simulate_two_legs(h, a))
    # Round of 16
    r16_winners = []
    for i, seed in enumerate(seeds):
        opponent = po_winners[7 - i]  # seed 1 vs winner of pair 7, etc.
        r16_winners.append(elo.simulate_two_legs(seed, opponent))
    # Quarter-finals (1 vs 8, 2 vs 7, 3 vs 6, 4 vs 5)
    qf_winners = []
    for i in range(4):
        h, a = r16_winners[i], r16_winners[7-i]
        qf_winners.append(elo.simulate_two_legs(h, a))
    # Semi-finals
    sf_winners = []
    sf_pairs = [(qf_winners[0], qf_winners[3]), (qf_winners[1], qf_winners[2])]
    for h, a in sf_pairs:
        sf_winners.append(elo.simulate_two_legs(h, a))
    # Final
    champion = elo.simulate_single_match(sf_winners[0], sf_winners[1], neutral=True)
    return champion

# ===============================
# MONTE CARLO: combine league + knockout
# ===============================
def run_monte_carlo(elo, completed, remaining, num_sims=10000):
    avg_points, rankings_sims = simulate_remaining_fixtures(elo, remaining, completed, num_sims)

    # Now for each ranking, simulate knockouts (we can just do one per ranking to save time, or multiple)
    champion_counts = defaultdict(int)
    top8_counts = defaultdict(int)
    playoff_counts = defaultdict(int)  # 9-24
    # We'll also compute average position? Not needed.

    for rankings in tqdm(rankings_sims, desc="Simulating knockouts", unit="ranking"):
        champion = simulate_knockouts(elo, rankings, num_sims_per_tournament=1)  # one per ranking
        champion_counts[champion] += 1
        for i, team in enumerate(rankings):
            if i < 8:
                top8_counts[team] += 1
            elif i < 24:
                playoff_counts[team] += 1

    return avg_points, champion_counts, top8_counts, playoff_counts

# ===============================
# OUTPUT FUNCTIONS
# ===============================
def print_results(avg_points, champion_counts, top8_counts, playoff_counts, num_sims):
    # Sort teams by average points (descending)
    teams_sorted = sorted(avg_points.keys(), key=lambda t: np.mean(champion_counts[t]), reverse=True)

    print("\n" + "=" * 100)
    print(f"PREDICTED FINAL LEAGUE TABLE ({num_sims:,} Monte Carlo Simulations)")
    print("=" * 100)
    print(f"{'Pos':<4} {'Team':<25} {'Avg Pts':<10} {'Top 8 %':<10} {'Playoff %':<10} {'Champion %':<10}")
    print("-" * 100)

    for i, team in enumerate(teams_sorted, 1):
        avg_p = np.mean(avg_points[team])
        top8_pct = (top8_counts[team] / num_sims) * 100
        playoff_pct = (playoff_counts[team] / num_sims) * 100
        champ_pct = (champion_counts[team] / num_sims) * 100
        print(f"{i:<4} {team:<25} {avg_p:<10.1f} {top8_pct:<10.1f} {playoff_pct:<10.1f} {champ_pct:<10.2f}")

    print("=" * 100)
    print("Top 8 %: Probability of finishing 1st-8th (direct R16 qualification).")
    print("Playoff %: Probability of finishing 9th-24th (play-off qualification).")
    print("Champion %: Probability of winning the Champions League.")

# ===============================
# MAIN
# ===============================
def main():
    random.seed(42)
    np.random.seed(42)

    # Train ELO on completed fixtures
    elo = ELOSystem(k=20, home_advantage=60)
    elo.train(COMPLETED_FIXTURES)

    # Show current standings (from completed matches)
    current_standings, _ = calculate_standings(COMPLETED_FIXTURES)
    print("\nCurrent Standings (from completed matches):")
    print("-" * 70)
    print(f"{'Pos':<4} {'Team':<25} {'P':<3} {'W':<3} {'D':<3} {'L':<3} {'GD':<5} {'Pts':<4}")
    for i, (team, p, w, d, l, gd, gf, ga, pts) in enumerate(current_standings, 1):
        print(f"{i:<4} {team:<25} {p:<3} {w:<3} {d:<3} {l:<3} {gd:<5} {pts:<4}")
    print("-" * 70)
    print(f"Remaining fixtures: {len(REMAINING_FIXTURES)}")
    print(f"Total teams: {len(ALL_TEAMS)}")
    print("\nRunning 10,000 Monte Carlo simulations...\n")

    num_sims = 10000
    avg_points, champion_counts, top8_counts, playoff_counts = run_monte_carlo(
        elo, COMPLETED_FIXTURES, REMAINING_FIXTURES, num_sims
    )
    print_results(avg_points, champion_counts, top8_counts, playoff_counts, num_sims)

if __name__ == "__main__":
    main()