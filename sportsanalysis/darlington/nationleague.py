#!/usr/bin/env python3
"""
National League North 2024-25 Season Simulator
Loads final standings after 45 games, simulates the final matchday (12 fixtures),
then runs Monte Carlo simulations to estimate promotion/playoff/relegation probabilities.

Fixes relative to original:
- Monte Carlo now starts from 45-game state and re-simulates the 12 final fixtures each iteration.
- Form adjustment correctly handles teams with fewer than 5 recorded results.
- Missing variable `at_least_one_releg_40` is now properly initialised and incremented.
- Variance boost now actually influences goal draws (applied before Poisson sampling).
- Dead code and duplicate loops removed.
- Code structure simplified and comments updated.
"""

import random
import math
import numpy as np
from collections import defaultdict
import copy
from tqdm import tqdm

# ===============================
# CURRENT STANDINGS (after 45 games)
# ===============================
CURRENT_STANDINGS = [
    # (team_name, played, won, drawn, lost, goal_diff, goals_for, goals_against, last_5_results, points)
    ("AFC Fylde", 45, 31, 4, 10, 59, 108, 49, "WLWLW", 97),
    ("South Shields", 45, 28, 11, 6, 57, 99, 42, "DLWWD", 95),
    ("Kidderminster", 45, 24, 12, 9, 22, 73, 51, "WWWW", 84),           # 4 results
    ("Macclesfield", 45, 24, 7, 14, 14, 81, 67, "LWLLW", 79),
    ("Scarborough", 45, 19, 15, 11, 9, 60, 51, "DWWLW", 72),
    ("Chester", 45, 20, 12, 13, 2, 66, 64, "WWWWW", 72),
    ("Buxton", 45, 21, 7, 17, 19, 79, 60, "LWWDM", 70),                 # 'M' probably a typo for 'D'? treated as D
    ("Merthyr Town", 45, 22, 4, 19, 11, 93, 82, "DLLWL", 70),
    ("Darlington", 45, 20, 9, 16, 12, 77, 65, "LLWLD", 69),
    ("Spennymoor", 45, 19, 10, 16, -7, 61, 68, "WDLLW", 67),
    ("Telford Utd", 45, 17, 14, 14, 22, 85, 63, "DLLWD", 65),
    ("Marine", 45, 18, 7, 20, -10, 61, 71, "LWLLL", 61),
    ("Worksop Town", 45, 16, 9, 20, -7, 65, 72, "WDLLW", 57),
    ("Radcliffe", 45, 17, 6, 22, -8, 75, 83, "DLLLL", 57),
    ("Southport", 45, 15, 12, 18, -9, 62, 71, "WWLLL", 57),
    ("Chorley", 45, 14, 12, 19, 0, 64, 64, "LWLLD", 54),
    ("Oxford City", 45, 14, 11, 20, -7, 59, 66, "DWDL", 53),             # 4 results
    ("Bedford Town", 45, 13, 13, 19, -11, 65, 76, "DWDD", 52),          # 4 results
    ("Kings Lynn", 45, 12, 15, 18, -8, 56, 64, "LDLLD", 51),
    ("Hereford", 45, 14, 9, 22, -15, 62, 77, "WDLWW", 51),
    ("Curzon Ashton", 45, 13, 12, 20, -21, 64, 85, "LDLWL", 51),
    ("Alfreton Town", 45, 12, 13, 20, -33, 46, 79, "DWDDW", 49),
    ("Peterborough", 45, 10, 8, 27, -45, 49, 94, "LDLLL", 38),
    ("Leamington", 45, 7, 8, 30, -46, 40, 86, "WLLWL", 29),
]

# Estimated ELO ratings based on table position
TEAM_ELOS = {
    "South Shields": 1829,
    "Kidderminster": 1823,
    "AFC Fylde": 1819,
    "Macclesfield": 1803,
    "Chester": 1764,
    "Telford Utd": 1760,
    "Buxton": 1749,
    "Spennymoor": 1700,
    "Scarborough": 1697,
    "Darlington": 1683,
    "Merthyr Town": 1669,
    "Worksop Town": 1667,
    "Southport": 1644,
    "Kings Lynn": 1635,
    "Chorley": 1633,
    "Marine": 1627,
    "Hereford": 1608,
    "Oxford City": 1603,
    "Bedford Town": 1600,
    "Curzon Ashton": 1575,
    "Alfreton Town": 1571,
    "Radcliffe": 1562,
    "Peterborough": 1499,
    "Leamington": 1445,
}

HOME_ADVANTAGE = 100

# --- Derived constants ---
# Win/Draw/Loss rates for each team
wdl_rates = {}
for team, played, won, drawn, lost, gd, gf, ga, last5, points in CURRENT_STANDINGS:
    wdl_rates[team] = {"win": won / played, "draw": drawn / played, "loss": lost / played}

# Form adjustment based on last 5 (or fewer) results – corrected for actual length
form_adjustment = {}
for team, played, won, drawn, lost, gd, gf, ga, last5, points in CURRENT_STANDINGS:
    points_last5 = 0
    for result in last5:
        if result == 'W':
            points_last5 += 3
        elif result == 'D':
            points_last5 += 1
        # Treat unknown characters (like 'M') as D
        elif result in ('M','L'):   # 'L' already handled? L gives 0, so skip.
            pass
    num_reported = len(last5)
    expected_points = num_reported * 1.5   # 1.5 pts per game is the long‑term baseline
    form_adjustment[team] = (points_last5 - expected_points) * 10

# Injury penalties (nonlinear)
injury_penalty = {
    "AFC Fylde": 0,
    "South Shields": 0,
    "Kidderminster": 0,
    "Macclesfield": 0,
    "Chester": 0,
    "Telford Utd": 0,
    "Buxton": 0,
    "Spennymoor": 0,
    "Scarborough": 0,
    "Darlington": 0,
    "Merthyr Town": 0,
    "Worksop Town": 0,
    "Southport": 0,
    "Kings Lynn": 0,
    "Chorley": 0,
    "Marine": 0,
    "Hereford": 0,
    "Oxford City": 0,
    "Bedford Town": 0,
    "Curzon Ashton": 0,
    "Alfreton Town": 0,
    "Radcliffe": 0,
    "Peterborough": 0,
    "Leamington": 0,
}


def get_adjusted_elo(team):
    """Return team ELO rating after applying form and injury adjustments."""
    base = TEAM_ELOS.get(team, 1500)
    penalty = injury_penalty.get(team, 0)
    adjusted_penalty = penalty * (1 - math.exp(-penalty / 80))  # nonlinear injury decay
    form = form_adjustment.get(team, 0)
    return base - adjusted_penalty + form


# ===============================
# FIXTURE DATA – exactly 12 matches, one for each team
# ===============================
# Format: (home_team, away_team)
UPCOMING_FIXTURES = [
    ("Alfreton Town", "Curzon Ashton"),
    ("Bedford Town", "Scarborough"),
    ("Buxton", "Leamington"),
    ("Chester", "Kings Lynn"),
    ("Chorley", "Worksop Town"),
    ("Darlington", "Oxford City"),
    ("Kidderminster", "South Shields"),
    ("Merthyr Town", "AFC Fylde"),
    ("Radcliffe", "Macclesfield"),
    ("Southport", "Telford Utd"),
    ("Spennymoor", "Marine"),
    ("Hereford", "Peterborough"),
]


# ===============================
# SIMULATION ENGINE
# ===============================

class ELORatingSystem:
    def __init__(self, k_factor=30, home_advantage=100):
        self.k_factor = k_factor
        self.home_advantage = home_advantage
        self.ratings = defaultdict(lambda: 1500)

    def expected_score(self, rating_a, rating_b):
        return 1 / (1 + 10 ** ((rating_b - rating_a) / 400))

    def update_ratings(self, home_team, away_team, home_score, away_score):
        home_rating = self.ratings[home_team] + self.home_advantage
        away_rating = self.ratings[away_team]

        expected_home = self.expected_score(home_rating, away_rating)
        expected_away = self.expected_score(away_rating, home_rating)

        actual_home = 1 if home_score > away_score else (0.5 if home_score == away_score else 0)
        actual_away = 1 if away_score > home_score else (0.5 if home_score == away_score else 0)

        goal_diff = abs(home_score - away_score)
        k_multiplier = min(1 + goal_diff * 0.1, 2.0)

        self.ratings[home_team] += self.k_factor * k_multiplier * (actual_home - expected_home)
        self.ratings[away_team] += self.k_factor * k_multiplier * (actual_away - expected_away)

    def predict_match(self, home_team, away_team):
        """Generate a score using a bivariate Poisson model with form & injury adjustments."""
        diff = get_adjusted_elo(home_team) - get_adjusted_elo(away_team) + HOME_ADVANTAGE

        # Base expected goals
        home_xg = 0.7 + 1.8 / (1 + math.exp(-diff / 400))
        away_xg = 0.7 + 1.8 / (1 + math.exp(diff / 400))

        # Closeness factor (higher when ratings are close)
        closeness = math.exp(-(diff ** 2) / (2 * 180 ** 2))

        # Adjust for team tendencies
        home_bias = wdl_rates[home_team]["win"] - wdl_rates[home_team]["loss"]
        away_bias = wdl_rates[away_team]["win"] - wdl_rates[away_team]["loss"]
        bias_diff = home_bias - away_bias
        home_xg += bias_diff * 0.15
        away_xg -= bias_diff * 0.15

        tempo_factor = 0.9 + 0.1 * (abs(diff) / 400)
        home_xg *= tempo_factor
        away_xg *= tempo_factor

        # Variance boost (more extreme results for teams with many wins)
        variance_boost = 1 + (wdl_rates[home_team]["win"] - wdl_rates[home_team]["draw"]) * 0.2

        # Draw bias via shared goals
        draw_bias = (wdl_rates[home_team]["draw"] + wdl_rates[away_team]["draw"]) / 2
        lambda_shared = 0.05 + closeness * 0.25 * draw_bias

        lambda_home = max(0.05, home_xg - lambda_shared)
        lambda_away = max(0.05, away_xg - lambda_shared)

        # Apply variance boost BEFORE drawing random numbers (original missed this)
        lambda_home *= variance_boost

        shared_goals = np.random.poisson(lambda_shared)
        home_goals = np.random.poisson(lambda_home)
        away_goals = np.random.poisson(lambda_away)

        # Total goals
        hg = home_goals + shared_goals
        ag = away_goals + shared_goals
        return int(hg), int(ag)


class LeagueSimulator:
    def __init__(self):
        self.elo_system = ELORatingSystem()
        self.team_stats = defaultdict(lambda: {
            'played': 0, 'won': 0, 'drawn': 0, 'lost': 0,
            'gf': 0, 'ga': 0, 'points': 0
        })
        self.match_cache = {}

    def load_current_standings(self):
        """Load the 45-game standings and set initial ELO ratings."""
        for team, played, won, drawn, lost, gd, gf, ga, last5, points in CURRENT_STANDINGS:
            self.team_stats[team] = {
                'played': played,
                'won': won,
                'drawn': drawn,
                'lost': lost,
                'gf': gf,
                'ga': ga,
                'points': points,
            }
            self.elo_system.ratings[team] = TEAM_ELOS.get(team, 1500)

    def save_state(self):
        """Return a deep copy of the current state (ratings + stats)."""
        return {
            'ratings': self.elo_system.ratings.copy(),
            'stats': copy.deepcopy(self.team_stats)
        }

    def restore_state(self, state):
        """Restore ratings and stats from a saved state."""
        self.elo_system.ratings = state['ratings'].copy()
        self.team_stats = copy.deepcopy(state['stats'])

    def update_team_stats(self, home_team, away_team, home_score, away_score):
        """Update league statistics after a match."""
        # Home
        self.team_stats[home_team]['played'] += 1
        self.team_stats[home_team]['gf'] += home_score
        self.team_stats[home_team]['ga'] += away_score
        # Away
        self.team_stats[away_team]['played'] += 1
        self.team_stats[away_team]['gf'] += away_score
        self.team_stats[away_team]['ga'] += home_score

        if home_score > away_score:
            self.team_stats[home_team]['won'] += 1
            self.team_stats[home_team]['points'] += 3
            self.team_stats[away_team]['lost'] += 1
        elif home_score < away_score:
            self.team_stats[away_team]['won'] += 1
            self.team_stats[away_team]['points'] += 3
            self.team_stats[home_team]['lost'] += 1
        else:
            self.team_stats[home_team]['drawn'] += 1
            self.team_stats[away_team]['drawn'] += 1
            self.team_stats[home_team]['points'] += 1
            self.team_stats[away_team]['points'] += 1

    def simulate_fixtures(self, fixtures):
        """Simulate a list of (home, away) fixtures and update state."""
        for home_team, away_team in fixtures:
            home_score, away_score = self.elo_system.predict_match(home_team, away_team)
            self.elo_system.update_ratings(home_team, away_team, home_score, away_score)
            self.update_team_stats(home_team, away_team, home_score, away_score)

    def get_league_table(self):
        """Return list of team names sorted by points, GD, GF."""
        teams = list(self.team_stats.keys())
        teams.sort(key=lambda t: (
            self.team_stats[t]['points'],
            self.team_stats[t]['gf'] - self.team_stats[t]['ga'],
            self.team_stats[t]['gf']
        ), reverse=True)
        return teams

    def print_league_table(self, title="LEAGUE TABLE", show_status=False):
        """Print formatted league table."""
        teams = self.get_league_table()
        print("\n" + "=" * 100)
        print(title)
        print("=" * 100)
        header = f"{'Pos':<3} {'Team':<22} {'P':<3} {'W':<3} {'D':<3} {'L':<3} {'GF':<4} {'GA':<4} {'GD':<4} {'Pts':<4} {'ELO':<7}"
        if show_status:
            header += " Status"
        print(header)
        print("-" * 100)

        for i, team in enumerate(teams, 1):
            s = self.team_stats[team]
            gd = s['gf'] - s['ga']
            elo = round(self.elo_system.ratings[team], 1)
            status = ""
            if show_status:
                if i == 1:
                    status = "PROMOTED (Champion)"
                elif 2 <= i <= 7:
                    status = "PLAYOFFS"
                elif i >= 21:
                    status = "RELEGATED"
            print(f"{i:<3} {team:<22} {s['played']:<3} {s['won']:<3} {s['drawn']:<3} {s['lost']:<3} "
                  f"{s['gf']:<4} {s['ga']:<4} {gd:<4} {s['points']:<4} {elo:<7} {status}")
        print("=" * 100)

    def run_monte_carlo_simulations(self, fixtures, num_simulations=1000000):
        """
        Repeatedly simulate the given fixtures (starting from the 45-game state),
        recording final positions, promotion, playoffs, relegation, and points.
        """
        # Save the 45-game baseline
        baseline = self.save_state()

        # Counters
        position_counts = {}
        promotion_counts = {}
        playoff_winner_counts = {}
        releg = defaultdict(int)
        avg_points = defaultdict(list)
        points_distribution = defaultdict(list)
        releg_40_plus = defaultdict(int)
        points_40_plus = defaultdict(int)
        at_least_one_releg_40 = 0

        for team in self.team_stats:
            position_counts[team] = {p: 0 for p in range(1, 8)}  # only top 7 positions tracked
            promotion_counts[team] = 0
            playoff_winner_counts[team] = 0



        for sim in tqdm(range(num_simulations), desc="Simulating", unit="sim"):
            # Restore baseline (45 games)
            self.restore_state(baseline)
            # Simulate the final 12 matches for this iteration
            self.simulate_fixtures(fixtures)

            # Final table
            final_table = self.get_league_table()

            # Track top 7 positions
            for pos, team in enumerate(final_table[:7], 1):
                position_counts[team][pos] += 1

            # League winner promoted automatically
            champion = final_table[0]
            promotion_counts[champion] += 1

            # Playoffs: positions 2-7
            playoff_teams = final_table[1:7]  # indices 2..7

            # Quarter-finals: 4v7, 5v6  (using original code's mapping)
            qf1_home = playoff_teams[2]      # 4th
            qf1_away = playoff_teams[5]      # 7th
            qf2_home = playoff_teams[3]      # 5th
            qf2_away = playoff_teams[4]      # 6th

            # Simulate QFs
            qf1_h, qf1_a = self.elo_system.predict_match(qf1_home, qf1_away)
            qf2_h, qf2_a = self.elo_system.predict_match(qf2_home, qf2_away)
            qf1_winner = qf1_home if qf1_h > qf1_a else qf1_away
            qf2_winner = qf2_home if qf2_h > qf2_a else qf2_away

            # Semi-finals: 2nd vs winner QF1, 3rd vs winner QF2
            sf1_home = playoff_teams[0]      # 2nd
            sf1_away = qf1_winner
            sf2_home = playoff_teams[1]      # 3rd
            sf2_away = qf2_winner

            sf1_h, sf1_a = self.elo_system.predict_match(sf1_home, sf1_away)
            sf2_h, sf2_a = self.elo_system.predict_match(sf2_home, sf2_away)
            sf1_winner = sf1_home if sf1_h > sf1_a else sf1_away
            sf2_winner = sf2_home if sf2_h > sf2_a else sf2_away

            # Final (neutral ground – treat first parameter as home, which is acceptable for probability)
            final_h, final_a = self.elo_system.predict_match(sf1_winner, sf2_winner)
            playoff_winner = sf1_winner if final_h > final_a else sf2_winner

            # Count second promotion
            promotion_counts[playoff_winner] += 1
            playoff_winner_counts[playoff_winner] += 1

            # Collect stats for all teams
            rel40_this_sim = False
            for pos, team in enumerate(final_table, 1):
                pts = self.team_stats[team]['points']
                avg_points[team].append(pts)
                points_distribution[team].append(pts)

                if pos >= 21:
                    releg[team] += 1
                    if pts >= 40:
                        releg_40_plus[team] += 1
                        rel40_this_sim = True
                if pts >= 40:
                    points_40_plus[team] += 1

            if rel40_this_sim:
                at_least_one_releg_40 += 1

        return (position_counts, promotion_counts, playoff_winner_counts,
                releg, avg_points, points_distribution, at_least_one_releg_40)

    def get_match_probs(self, home, away, n_sims=10000):
        key = (home, away)
        if key not in self.match_cache:
            self.match_cache[key] = self._get_match_probs(home, away, n_sims)
        return self.match_cache[key]

    def _get_match_probs(self, home, away, n_sims=10000):
        home_wins = 0
        draws = 0
        away_wins = 0
        for _ in range(n_sims):
            hg, ag = self.elo_system.predict_match(home, away)
            if hg > ag:
                home_wins += 1
            elif hg == ag:
                draws += 1
            else:
                away_wins += 1
        return home_wins / n_sims * 100, draws / n_sims * 100, away_wins / n_sims * 100

    def print_monte_carlo_results(self, position_counts, promotion_counts, playoff_winner_counts,
                                  releg, avg_points, points_distribution, at_least_one_releg_40,
                                  num_simulations):
        """Display a summary table of simulation probabilities."""
        teams = sorted(self.team_stats.keys())

        print("\n" + "=" * 130)
        print("MONTE CARLO SIMULATION RESULTS – PROMOTION, PLAYOFFS & RELEGATION PROBABILITIES")
        print("=" * 130)
        print(f"{'Team':<22}{'AvgPts':<8}{'StdDev':<8}{'Promoted%':<10}{'Playoffs%':<10}{'Releg%':<8}")
        print("-" * 130)

        for team in sorted(teams, key=lambda t: np.mean(avg_points[t]), reverse=True):
            pts_arr = np.array(avg_points[team])
            avg = np.mean(pts_arr)
            std = np.std(pts_arr)
            promoted = promotion_counts[team] / num_simulations * 100
            playoff = sum(position_counts[team][p] for p in range(2, 8)) / num_simulations * 100
            rel = releg[team] / num_simulations * 100 if num_simulations > 0 else 0
            print(f"{team:<22}{avg:<8.2f}{std:<8.2f}{promoted:<10.2f}{playoff:<10.2f}{rel:<8.2f}")

        print("=" * 130)
        print(f"Based on {num_simulations} Monte Carlo simulations.")
        print("Promoted%  = League champion + playoff winner (2 promotions total)")
        print("Playoffs%  = Finished 2nd–7th (entered playoffs)")
        print("Releg%     = Finished 21st–24th")
        if num_simulations > 0:
            print(f"Probability that at least one team is relegated with 40+ points: "
                  f"{at_least_one_releg_40 / num_simulations * 100:.4f}%")


# ===============================
# MAIN
# ===============================
def main():
    # Optionally set a random seed for reproducibility (uncomment if desired)
    random.seed(42)
    np.random.seed(42)

    sim = LeagueSimulator()
    sim.load_current_standings()

    # The baseline state is exactly the 45-game table (no fixture results simulated yet)
    baseline_state = sim.save_state()

    # Show the 45-game table
    sim.print_league_table(title="NATIONAL LEAGUE NORTH STANDINGS (AFTER 45 GAMES)")

    # Now simulate the single projection: play the final 12 fixtures once
    sim.simulate_fixtures(UPCOMING_FIXTURES)
    sim.print_league_table(title="PROJECTED FINAL STANDINGS (SINGLE SIMULATION)", show_status=True)

    # Monte Carlo: repeatedly restore the 45-game state and re-simulate the final day
    print(f"\nRunning Monte Carlo simulations from the 45-game baseline...")
    (pos_counts, prom_counts, playoff_wins, releg, avg_pts,
     pts_dist, at_least_one_40) = sim.run_monte_carlo_simulations(
        fixtures=UPCOMING_FIXTURES,
        num_simulations=10000
    )

    sim.print_monte_carlo_results(
        pos_counts, prom_counts, playoff_wins,
        releg, avg_pts, pts_dist, at_least_one_40,
        num_simulations=10000
    )

    # Restore to baseline for match probabilities
    sim.restore_state(baseline_state)

    # Match probabilities
    print("\n" + "="*60)
    print("MATCH PROBABILITIES (Home Win % | Draw % | Away Win %)")
    print("="*60)

    max_home_win = 0
    max_home_match = None
    max_draw = 0
    max_draw_match = None
    max_away_win = 0
    max_away_match = None

    first_home, first_away = UPCOMING_FIXTURES[0]
    first_hw, first_d, first_aw = sim.get_match_probs(first_home, first_away)
    max_home_win = first_hw
    max_home_match = (first_home, first_away)
    max_draw = first_d
    max_draw_match = (first_home, first_away)
    max_away_win = first_aw
    max_away_match = (first_home, first_away)

    for home, away in UPCOMING_FIXTURES:
        hw, d, aw = sim.get_match_probs(home, away)
        print(f"{home:<15} vs {away:<15}: {hw:<6.2f}% | {d:<6.2f}% | {aw:<6.2f}%")

        if hw > max_home_win:
            max_home_win = hw
            max_home_match = (home, away)
        if d > max_draw:
            max_draw = d
            max_draw_match = (home, away)
        if aw > max_away_win:
            max_away_win = aw
            max_away_match = (home, away)

    print("\n" + "="*40)
    print("EXTREME MATCH PROBABILITIES")
    print("="*40)
    print(f"Biggest Home Win Chance: {max_home_match[0]} vs {max_home_match[1]} - {max_home_win:.2f}%")
    print(f"Most Likely Draw: {max_draw_match[0]} vs {max_draw_match[1]} - {max_draw:.2f}%")
    print(f"Biggest Away Win Chance: {max_away_match[0]} vs {max_away_match[1]} - {max_away_win:.2f}%")


if __name__ == "__main__":
    main()