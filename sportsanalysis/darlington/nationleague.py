#!/usr/bin/env python3
"""
National League North 2025-26 Season Predictor - Improved Version

Improvements over original:
  1. Team strength model (attack/defense) from actual goal data, with Bayesian shrinkage
  2. League-calibrated parameters from actual season data
  3. Correct zero-sum ELO updates
  4. Standard English playoff bracket (2nd v winner(5v6), 3rd v winner(4v7))
  5. Clamped expected-goal lambdas to avoid blow-out artifacts
  6. 5000 simulations, plus points std-dev per team
  7. Removal of ad-hoc form/wdl adjustments (noise → strength model)
"""

import random
import math
import numpy as np
from collections import defaultdict
from itertools import permutations
from tqdm import tqdm

# =========================================================
# COMPLETED FIXTURES
# =========================================================
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

    # September
    ("Southport", "Spennymoor", 2, 2),
    ("South Shields", "Buxton", 4, 0),
    ("Oxford City", "Morecambe", 1, 1),
    ("Merthyr Town", "Marine", 1, 2),
    ("Macclesfield", "Harborough Town", 1, 0),
    ("Hednesford", "Radcliffe", 4, 1),
    ("Darlington", "Hebburn Town", 1, 1),
    ("Chorley", "Spalding Utd", 2, 1),
    ("Chester", "Worksop Town", 4, 1),
    ("Brackley Town", "Scarborough", 1, 1),
    ("Bedford Town", "Hereford Utd", 1, 1),
    ("Telford Utd", "Kings Lynn", 0, 5),
    ("Brackley Town", "South Shields", 3, 2),

    # October
    ("Worksop Town", "Morecambe", 2, 1),
    ("Radcliffe", "Scarborough", 4, 1),
    ("Marine", "Spalding Utd", 1, 0),
    ("Macclesfield", "South Shields", 4, 3),
    ("Kings Lynn", "Buxton", 1, 0),
    ("Hereford Utd", "Hednesford", 0, 1),
    ("Hebburn Town", "Oxford City", 0, 3),
    ("Harborough Town", "Southport", 1, 0),
    ("Darlington", "Merthyr Town", 1, 1),
    ("Chorley", "Telford Utd", 2, 1),
    ("Chester", "Bedford Town", 1, 0),
    ("Brackley Town", "Spennymoor", 2, 1),
    ("Hebburn Town", "Scarborough", 0, 2),
    ("Southport", "Radcliffe", 0, 2),
    ("Merthyr Town", "Kings Lynn", 1, 1),
    ("Hednesford", "Brackley Town", 3, 2),
    ("Buxton", "Worksop Town", 2, 2),
    ("Telford Utd", "Darlington", 2, 1),
    ("South Shields", "Chester", 3, 1),
    ("Scarborough", "Bedford Town", 1, 2),
    ("Merthyr Town", "Morecambe", 1, 3),
    ("Marine", "Oxford City", 1, 1),
    ("Macclesfield", "Hereford Utd", 1, 2),
    ("Kings Lynn", "Southport", 0, 0),
    ("Hednesford", "Spalding Utd", 2, 0),
    ("Harborough Town", "Worksop Town", 1, 1),
    ("Darlington", "Spennymoor", 3, 0),
    ("Chorley", "Buxton", 2, 3),
    ("Brackley Town", "Radcliffe", 0, 1),
    ("Telford Utd", "Hebburn Town", 2, 2),
    ("Worksop Town", "Kings Lynn", 5, 0),
    ("Spennymoor", "South Shields", 0, 1),
    ("Spalding Utd", "Brackley Town", 2, 2),
    ("Radcliffe", "Chorley", 0, 3),
    ("Oxford City", "Merthyr Town", 3, 0),
    ("Morecambe", "Darlington", 1, 0),
    ("Hereford Utd", "Telford Utd", 0, 1),
    ("Chester", "Marine", 2, 1),
    ("Buxton", "Harborough Town", 3, 0),
    ("Bedford Town", "Hednesford", 1, 0),
    ("Southport", "Telford Utd", 1, 2),
    ("Radcliffe", "Merthyr Town", 3, 3),
    ("Oxford City", "South Shields", 1, 3),
    ("Morecambe", "Scarborough", 2, 0),
    ("Hereford Utd", "Kings Lynn", 0, 3),
    ("Hebburn Town", "Harborough Town", 1, 1),
    ("Chester", "Hednesford", 0, 1),
    ("Buxton", "Marine", 4, 2),
    ("Bedford Town", "Macclesfield", 0, 3),
    ("Worksop Town", "Brackley Town", 0, 1),
    ("Spennymoor", "Chorley", 2, 0),
    ("Spalding Utd", "Darlington", 3, 2),

    # November
    ("South Shields", "Southport", 5, 1),
    ("Scarborough", "Buxton", 2, 2),
    ("Merthyr Town", "Hebburn Town", 4, 1),
    ("Kings Lynn", "Spennymoor", 2, 0),
    ("Hednesford", "Morecambe", 6, 2),
    ("Chorley", "Hereford Utd", 1, 2),
    ("Brackley Town", "Chester", 0, 1),
    ("Telford Utd", "Spalding Utd", 2, 1),
    ("Darlington", "Oxford City", 1, 1),
    ("Scarborough", "Marine", 1, 3),
    ("Morecambe", "Hereford Utd", 2, 2),
]

# =========================================================
# LEAGUE PARAMETERS (calibrated from actual match data)
# =========================================================
LEAGUE_HOME_GOALS = 1.63     # home goals / match
LEAGUE_AWAY_GOALS = 1.21     # away goals / match
LEAGUE_HOME_WIN   = 0.481
LEAGUE_DRAW       = 0.208
LEAGUE_AWAY_WIN   = 0.311

BASE_ELO          = 1500
K_FACTOR          = 20
HOME_ADV_ELO      = 60       # ~58% win-share for equal teams
PRIOR_GAMES       = 10       # shrinkage strength (higher = more conservative)

PLAYOFF_WEIGHTS = {
    'league': 1.0,
    'playoff_qf': 1.2,
    'playoff_sf': 1.3,
    'playoff_final': 1.5,
}

# Clamps to keep λ's sane even for extreme mismatches
LAMBDA_MIN = 0.35
LAMBDA_MAX = 4.20
ELO_FACTOR_MIN = 0.75
ELO_FACTOR_MAX = 1.35

NUM_SIMULATIONS = 5000

# =========================================================
# HELPERS
# =========================================================
def calculate_standings(fixtures):
    """Compute current standings (points / GD / GF and last-5 form)."""
    stats = defaultdict(lambda: {
        'played': 0, 'won': 0, 'drawn': 0, 'lost': 0,
        'gf': 0, 'ga': 0, 'points': 0,
    })
    for home, away, hs, aws in fixtures:
        stats[home]['played'] += 1
        stats[home]['gf'] += hs
        stats[home]['ga'] += aws
        stats[away]['played'] += 1
        stats[away]['gf'] += aws
        stats[away]['ga'] += hs

        if hs > aws:
            stats[home]['won'] += 1; stats[home]['points'] += 3
            stats[away]['lost'] += 1
        elif hs < aws:
            stats[away]['won'] += 1; stats[away]['points'] += 3
            stats[home]['lost'] += 1
        else:
            stats[home]['drawn'] += 1; stats[away]['drawn'] += 1
            stats[home]['points'] += 1; stats[away]['points'] += 1

    standings = []
    for team, s in stats.items():
        last5 = []
        for h, a, hs, aws in reversed(fixtures):
            if h == team:
                last5.append('W' if hs > aws else ('L' if hs < aws else 'D'))
            elif a == team:
                last5.append('W' if aws > hs else ('L' if aws < hs else 'D'))
            if len(last5) >= 5:
                break
        last5_str = ''.join(last5)
        while len(last5_str) < 5:
            last5_str += '-'
        gd = s['gf'] - s['ga']
        standings.append((team, s['played'], s['won'], s['drawn'], s['lost'],
                          gd, s['gf'], s['ga'], last5_str, s['points']))
    standings.sort(key=lambda x: (x[9], x[5], x[6]), reverse=True)
    return standings


def compute_team_strengths(fixtures, teams, prior_games=PRIOR_GAMES):
    """
    Dixon-Coles style attack/defence strengths with Bayesian shrinkage.
    Attack = team's goal rate / league-average rate (normalised so avg ≈ 1.0).
    Defence = team's concede rate / league-average rate (lower = better defence).
    """
    raw = defaultdict(lambda: {
        'gf_h': 0, 'gp_h': 0, 'ga_h': 0,
        'gf_a': 0, 'gp_a': 0, 'ga_a': 0,
    })
    for h, a, hs, aws in fixtures:
        raw[h]['gf_h'] += hs; raw[h]['gp_h'] += 1; raw[h]['ga_h'] += aws
        raw[a]['gf_a'] += aws; raw[a]['gp_a'] += 1; raw[a]['ga_a'] += hs

    strengths = {}
    for team in teams:
        s = raw[team]

        # Attack: shrink towards 1.0 (league avg)
        home_att = (
            (s['gf_h'] + LEAGUE_HOME_GOALS * prior_games) /
            (s['gp_h'] + prior_games) / LEAGUE_HOME_GOALS
        )
        away_att = (
            (s['gf_a'] + LEAGUE_AWAY_GOALS * prior_games) /
            (s['gp_a'] + prior_games) / LEAGUE_AWAY_GOALS
        )
        # Defence: concede rate scaled so league avg = 1.0
        home_def = (
            (s['ga_h'] + LEAGUE_AWAY_GOALS * prior_games) /
            (s['gp_h'] + prior_games) / LEAGUE_AWAY_GOALS
        )
        away_def = (
            (s['ga_a'] + LEAGUE_HOME_GOALS * prior_games) /
            (s['gp_a'] + prior_games) / LEAGUE_HOME_GOALS
        )

        strengths[team] = {
            'attack':  (home_att + away_att) / 2,
            'defense': (home_def + away_def) / 2,
        }
    return strengths


def generate_remaining_fixtures(teams, completed):
    """Return the list of remaining (home, away) fixtures."""
    completed_set = {(h, a) for h, a, _, _ in completed}
    remaining = [(h, a) for h, a in permutations(teams, 2) if (h, a) not in completed_set]
    random.shuffle(remaining)
    return remaining


# =========================================================
# SIMULATOR
# =========================================================
class LeagueSimulator:

    def __init__(self):
        self.teams = []
        self.ratings = {}
        self.strengths = {}
        self.stats = {}

    # ---------- SETUP ----------
    def setup(self, completed_fixtures):
        self.teams = sorted({
            h for h, _, _, _ in completed_fixtures
        } | {
            a for _, a, _, _ in completed_fixtures
        })

        # Raw goal counters for incremental strength updates
        self.raw = defaultdict(lambda: {
            'gf_h': 0, 'gp_h': 0, 'ga_h': 0,
            'gf_a': 0, 'gp_a': 0, 'ga_a': 0,
        })
        for h, a, hs, aws in completed_fixtures:
            self.raw[h]['gf_h'] += hs; self.raw[h]['gp_h'] += 1; self.raw[h]['ga_h'] += aws
            self.raw[a]['gf_a'] += aws; self.raw[a]['gp_a'] += 1; self.raw[a]['ga_a'] += hs

        # Team attack/defense strengths
        self.strengths = compute_team_strengths(completed_fixtures, self.teams)

        # Current standings
        self.stats = {}
        for team, p, w, d, l, gd, gf, ga, l5, pts in calculate_standings(completed_fixtures):
            self.stats[team] = {
                'played': p, 'won': w, 'drawn': d, 'lost': l,
                'gf': gf, 'ga': ga, 'points': pts,
            }

        # Initialise ELOs then walk through results
        self.ratings = {t: BASE_ELO for t in self.teams}
        for h, a, hs, aws in completed_fixtures:
            self._update_elo(h, a, hs, aws)

    # ---------- ELO ----------
    def _update_elo(self, home, away, hs, aws, match_type='league'):
        K = K_FACTOR * PLAYOFF_WEIGHTS.get(match_type, 1.0)
        hr = self.ratings[home] + HOME_ADV_ELO
        ar = self.ratings[away]

        # Goal margin multiplier (diminishing)
        gm = 1.0 + math.log(1.0 + abs(hs - aws)) if abs(hs - aws) > 0 else 1.0
        gm = min(gm, 1.5)

        # Expected "win share" for the home side
        eh = 1.0 / (1.0 + 10 ** ((ar - hr) / 400.0))
        ea = 1.0 - eh     # zero-sum: E[away] = 1 - E[home]

        ah = 1.0 if hs > aws else (0.5 if hs == aws else 0.0)
        aa = 1.0 - ah

        self.ratings[home] += K * gm * (ah - eh)
        self.ratings[away] += K * gm * (aa - ea)

    # ---------- GOAL MODEL ----------
    def expected_goals(self, home, away, neutral=False):
        """Return (λ_home, λ_away) from team strengths + ELO diff."""
        ha = 0.0 if neutral else HOME_ADV_ELO
        elo_diff = self.ratings[home] + ha - self.ratings[away]
        elo_factor = 1.0 + 0.0008 * elo_diff
        elo_factor = max(ELO_FACTOR_MIN, min(ELO_FACTOR_MAX, elo_factor))

        a_h = self.strengths[home]['attack']
        d_h = self.strengths[home]['defense']
        a_a = self.strengths[away]['attack']
        d_a = self.strengths[away]['defense']

        lam_h = LEAGUE_HOME_GOALS * a_h * d_a * elo_factor
        lam_a = LEAGUE_AWAY_GOALS * a_a * d_h / elo_factor

        # Guard against blowing up for extreme strengths
        lam_h = max(LAMBDA_MIN, min(LAMBDA_MAX, lam_h))
        lam_a = max(LAMBDA_MIN, min(LAMBDA_MAX, lam_a))
        return lam_h, lam_a

    def predict_score(self, home, away, neutral=False):
        lam_h, lam_a = self.expected_goals(home, away, neutral)
        return int(np.random.poisson(lam_h)), int(np.random.poisson(lam_a))

    # ---------- TABLE ----------
    def update_stats(self, home, away, hs, aws):
        sh, sa = self.stats[home], self.stats[away]
        sh['played'] += 1; sh['gf'] += hs; sh['ga'] += aws
        sa['played'] += 1; sa['gf'] += aws; sa['ga'] += hs
        if hs > aws:
            sh['won'] += 1; sh['points'] += 3; sa['lost'] += 1
        elif hs < aws:
            sa['won'] += 1; sa['points'] += 3; sh['lost'] += 1
        else:
            sh['drawn'] += 1; sa['drawn'] += 1
            sh['points'] += 1; sa['points'] += 1

    def update_strengths_incremental(self, home, away, hs, aws):
        for team, gf, ga, side in [(home, hs, aws, 'h'), (away, aws, hs, 'a')]:
            r = self.raw[team]
            r[f'gf_{side}'] += gf
            r[f'gp_{side}'] += 1
            r[f'ga_{side}'] += ga

            home_att = (r['gf_h'] + LEAGUE_HOME_GOALS * PRIOR_GAMES) / (r['gp_h'] + PRIOR_GAMES) / LEAGUE_HOME_GOALS
            away_att = (r['gf_a'] + LEAGUE_AWAY_GOALS * PRIOR_GAMES) / (r['gp_a'] + PRIOR_GAMES) / LEAGUE_AWAY_GOALS
            home_def = (r['ga_h'] + LEAGUE_AWAY_GOALS * PRIOR_GAMES) / (r['gp_h'] + PRIOR_GAMES) / LEAGUE_AWAY_GOALS
            away_def = (r['ga_a'] + LEAGUE_HOME_GOALS * PRIOR_GAMES) / (r['gp_a'] + PRIOR_GAMES) / LEAGUE_HOME_GOALS

            self.strengths[team]['attack']  = (home_att + away_att) / 2
            self.strengths[team]['defense'] = (home_def + away_def) / 2

    def get_table(self):
        return sorted(
            self.teams,
            key=lambda t: (
                self.stats[t]['points'],
                self.stats[t]['gf'] - self.stats[t]['ga'],
                self.stats[t]['gf'],
            ),
            reverse=True,
        )

    # ---------- STATE ----------
    def save_state(self):
        return {
            'ratings':   dict(self.ratings),
            'stats':     {t: dict(s) for t, s in self.stats.items()},
            'raw':       {t: dict(s) for t, s in self.raw.items()},
            'strengths': {t: dict(s) for t, s in self.strengths.items()},
        }

    def restore_state(self, state):
        self.ratings   = dict(state['ratings'])
        self.stats     = {t: dict(s) for t, s in state['stats'].items()}
        self.raw       = {t: dict(s) for t, s in state['raw'].items()}
        self.strengths = {t: dict(s) for t, s in state['strengths'].items()}

    # ---------- KNOCKOUT / PLAYOFFS ----------
    def _knockout(self, home, away, match_type, neutral=False):
        hs, aws = self.predict_score(home, away, neutral=neutral)
        if hs != aws:
            return home if hs > aws else away
        # Penalty shootout: ELO-weighted coin flip
        ha = 0.0 if neutral else HOME_ADV_ELO
        diff = self.ratings[home] + ha - self.ratings[away]
        p_home = 1.0 / (1.0 + 10 ** (-diff / 400.0))
        return home if random.random() < p_home else away

    def simulate_playoffs(self, final_table):
        """
        Standard English playoff bracket (fixed, not reseeded):
            2nd       vs winner(5v6)   → SF1
            3rd       vs winner(4v7)   → SF2
            Final at neutral venue.
        """
        pos2 = final_table[1]
        pos3 = final_table[2]
        pos4 = final_table[3]
        pos5 = final_table[4]
        pos6 = final_table[5]
        pos7 = final_table[6]

        qf_5_6 = self._knockout(pos5, pos6, 'playoff_qf')  # 5th vs 6th
        qf_4_7 = self._knockout(pos4, pos7, 'playoff_qf')  # 4th vs 7th

        sf1 = self._knockout(pos2, qf_5_6, 'playoff_sf')   # 2nd vs winner(5v6)
        sf2 = self._knockout(pos3, qf_4_7, 'playoff_sf')   # 3rd vs winner(4v7)

        return self._knockout(sf1, sf2, 'playoff_final', neutral=True)

    # ---------- MONTE CARLO ----------
    def run_simulations(self, remaining_fixtures, baseline, num_sims):
        promotion = {t: 0 for t in self.teams}
        top7      = {t: 0 for t in self.teams}
        relegated = {t: 0 for t in self.teams}
        points_hist = {t: [] for t in self.teams}

        for _ in tqdm(range(num_sims), desc="Simulating", unit="sim"):
            self.restore_state(baseline)

            for h, a in remaining_fixtures:
                hs, aws = self.predict_score(h, a)
                self._update_elo(h, a, hs, aws)
                self.update_stats(h, a, hs, aws)
                self.update_strengths_incremental(h, a, hs, aws)

            table = self.get_table()

            # Champions (auto-promotion)
            promotion[table[0]] += 1
            for t in table[:7]:
                top7[t] += 1
            # Playoff winner (2nd promotion)
            promotion[self.simulate_playoffs(table)] += 1

            for pos, team in enumerate(table, 1):
                if pos >= 21:
                    relegated[team] += 1
                points_hist[team].append(self.stats[team]['points'])

        return promotion, top7, relegated, points_hist

    # ---------- OUTPUT ----------
    def print_results(self, promotion, top7, releg, points_hist, n):
        teams = sorted(points_hist.keys(),
                       key=lambda t: np.mean(points_hist[t]),
                       reverse=True)

        line = "=" * 108
        print(f"\n{line}")
        print(f"PREDICTED FINAL TABLE  ({n:,} Monte Carlo Simulations)")
        print(f"{line}")
        print(f"{'Pos':<4}{'Team':<20}{'ELO':<7}{'AvgPts':<9}{'StdP':<8}"
              f"{'Prom%':<9}{'Top7%':<9}{'Rel%':<9}")
        print("-" * 108)

        for i, team in enumerate(teams, 1):
            avg_pts = np.mean(points_hist[team])
            std_pts = np.std(points_hist[team])
            prom_pct  = 100.0 * promotion[team] / n
            top7_pct  = 100.0 * top7[team]      / n
            rel_pct   = 100.0 * releg[team]     / n
            elo = int(self.ratings.get(team, BASE_ELO))
            print(f"{i:<4}{team:<20}{elo:<7}{avg_pts:<9.1f}{std_pts:<8.2f}"
                  f"{prom_pct:<9.1f}{top7_pct:<9.1f}{rel_pct:<9.1f}")

        print(line)
        print("Prom % : Champions (1st) OR playoff winner.")
        print("Top7 % : Finish inside playoff positions 1-7.")
        print("Rel  % : Finish in relegation zone (21st-24th).")
        print("StdP   : Standard deviation of final points across simulations.")
        print(line)


# =========================================================
# MAIN
# =========================================================
def main():
    random.seed(42)
    np.random.seed(42)

    sim = LeagueSimulator()
    sim.setup(COMPLETED_FIXTURES)
    baseline = sim.save_state()

    # ---- Current standings printout ----
    print(f"Current standings from {len(COMPLETED_FIXTURES)} completed fixtures:")
    print("-" * 100)
    print(f"{'Pos':<4}{'Team':<20}{'P':<4}{'W':<4}{'D':<4}{'L':<4}"
          f"{'GD':<5}{'Pts':<5}{'ELO':<7}{'Form':<7}")
    print("-" * 100)
    for i, (team, p, w, d, l, gd, gf, ga, l5, pts) in enumerate(
        calculate_standings(COMPLETED_FIXTURES), 1
    ):
        print(f"{i:<4}{team:<20}{p:<4}{w:<4}{d:<4}{l:<4}"
              f"{gd:<5}{pts:<5}{int(sim.ratings[team]):<7}{l5:<7}")
    print("-" * 100)

    # ---- Remaining fixtures ----
    remaining = generate_remaining_fixtures(sim.teams, COMPLETED_FIXTURES)
    total_matches = len(COMPLETED_FIXTURES) + len(remaining)
    print(f"Remaining fixtures: {len(remaining):,}")
    print(f"Total fixtures (completed + remaining): {total_matches:,}")
    print(f"Teams: {len(sim.teams)}  •  Each team plays {2 * (len(sim.teams) - 1)} matches")

    # ---- Simulate ----
    print(f"\nRunning {NUM_SIMULATIONS:,} Monte Carlo simulations...\n")
    results = sim.run_simulations(remaining, baseline, NUM_SIMULATIONS)
    sim.print_results(*results, n=NUM_SIMULATIONS)


if __name__ == "__main__":
    main()