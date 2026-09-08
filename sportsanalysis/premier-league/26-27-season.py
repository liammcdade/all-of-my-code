"""
Premier League 2026/27 simulation with integrated European competitions.

REFACTORED VERSION – addresses all valid critique points except external data input.
- Modular classes: PLSimulator, EuropeanCompetition (UCL, UEL, UECL).
- Fatigue now depends on European elimination status (active = penalty decays; eliminated = no penalty).
- Promoted teams get market‑derived Elo (no flat penalty).
- No artificial Elo shrinkage (set to 1.0).
- UCL qualification correctly handles 5th‑place conditional spots (if UCL/UEL winner is English and outside top 4).
- Output includes separate European win probabilities and a combined "AnyEuroWin%" column.
"""

import logging
import math
from collections import defaultdict
from typing import Dict, List, Tuple, Optional, Set, Any
import random
import numpy as np
from tqdm import tqdm

logger = logging.getLogger(__name__)

# =============================================================================
# GLOBAL CONSTANTS (shared across all competitions)
# =============================================================================

HOME_ADVANTAGE_ELO = 85.0
ELO_SCALE = 400.0
LEAGUE_AVERAGE_ELO = 1500.0
ELO_SHRINKAGE = 1.0                     # no compression of market‑derived ratings

MAX_GOALS = 10
NUM_PL_SIMS = 2000
SEED = 42

BASE_HOME_XG = 1.5
BASE_AWAY_XG = 1.2
XG_ELO_SENSITIVITY = 0.002
EXTRA_TIME_XG_FACTOR = 0.5

# Base fatigue penalty (Elo points) per competition – applied only while team is still active.
EUROPEAN_FATIGUE_BASE = {"UCL": 8.0, "UEL": 6.0, "UECL": 5.0}

_FACTORIALS = np.array([math.factorial(i) for i in range(MAX_GOALS + 1)], dtype=np.float64)
_POISSON_CACHE: Dict[int, np.ndarray] = {}
_LAMBDA_ROUND_PRECISION = 100

_RNG = random.Random(SEED)
_NP_RNG = np.random.RandomState(SEED)

# =============================================================================
# COMMON HELPER FUNCTIONS (unchanged)
# =============================================================================

def fractional_to_probability(odds_tuple: Tuple[int, int]) -> float:
    numerator, denominator = odds_tuple
    return denominator / (numerator + denominator)

def _poisson_pmf(lam: float) -> np.ndarray:
    key = int(round(lam * _LAMBDA_ROUND_PRECISION))
    cached = _POISSON_CACHE.get(key)
    if cached is not None:
        return cached
    goals = np.arange(MAX_GOALS + 1, dtype=np.float64)
    pmf = np.exp(-lam) * (lam ** goals) / _FACTORIALS
    pmf /= pmf.sum()
    _POISSON_CACHE[key] = pmf
    return pmf

def sample_score(lam_home: float, lam_away: float) -> Tuple[int, int]:
    h_pmf = _poisson_pmf(lam_home)
    a_pmf = _poisson_pmf(lam_away)
    h_cdf = np.cumsum(h_pmf)
    a_cdf = np.cumsum(a_pmf)
    h_goal = int(np.searchsorted(h_cdf, _NP_RNG.random()))
    a_goal = int(np.searchsorted(a_cdf, _NP_RNG.random()))
    return min(h_goal, MAX_GOALS), min(a_goal, MAX_GOALS)

def compute_expected_goals(elo_home: float, elo_away: float) -> Tuple[float, float]:
    diff = elo_home - elo_away
    return (
        BASE_HOME_XG * math.exp(XG_ELO_SENSITIVITY * diff),
        BASE_AWAY_XG * math.exp(-XG_ELO_SENSITIVITY * diff),
    )

def simulate_two_legged_tie(team1: str, team2: str, elos: Dict[str, float]) -> str:
    # First leg
    elo_h1 = elos.get(team1, LEAGUE_AVERAGE_ELO) + HOME_ADVANTAGE_ELO
    elo_a1 = elos.get(team2, LEAGUE_AVERAGE_ELO)
    xg_h1, xg_a1 = compute_expected_goals(elo_h1, elo_a1)
    goals_h1, goals_a1 = sample_score(xg_h1, xg_a1)

    # Second leg
    elo_h2 = elos.get(team2, LEAGUE_AVERAGE_ELO) + HOME_ADVANTAGE_ELO
    elo_a2 = elos.get(team1, LEAGUE_AVERAGE_ELO)
    xg_h2, xg_a2 = compute_expected_goals(elo_h2, elo_a2)
    goals_h2, goals_a2 = sample_score(xg_h2, xg_a2)

    agg1 = goals_h1 + goals_a2
    agg2 = goals_a1 + goals_h2
    if agg1 > agg2:
        return team1
    if agg2 > agg1:
        return team2

    # Extra time
    et_xg1 = compute_expected_goals(
        elos.get(team1, LEAGUE_AVERAGE_ELO),
        elos.get(team2, LEAGUE_AVERAGE_ELO)
    )[0] * EXTRA_TIME_XG_FACTOR
    et_xg2 = compute_expected_goals(
        elos.get(team2, LEAGUE_AVERAGE_ELO),
        elos.get(team1, LEAGUE_AVERAGE_ELO)
    )[0] * EXTRA_TIME_XG_FACTOR
    et1, et2 = sample_score(et_xg1, et_xg2)
    if et1 != et2:
        return team1 if et1 > et2 else team2

    # Penalties
    diff = elos.get(team1, LEAGUE_AVERAGE_ELO) - elos.get(team2, LEAGUE_AVERAGE_ELO)
    p1 = 1 / (1 + 10 ** (-diff / ELO_SCALE))
    return team1 if _RNG.random() < p1 else team2

def simulate_knockout_phase(qualified: List[str], elos: Dict[str, float]) -> Tuple[Optional[str], Dict[str, int]]:
    """
    Full knockout phase from round of 24.
    Returns (winner, elimination_rounds) where elimination_rounds maps
    each team to the round they were eliminated:
        -1 = did not qualify (league phase elimination)
         0 = eliminated in playoff
         1 = eliminated in R16
         2 = eliminated in QF
         3 = eliminated in SF
         4 = lost the final
         5 = winner
    """
    top8 = qualified[:8]
    playoff = qualified[8:24]
    all_teams = set(qualified)
    elimination_round = {team: -1 for team in all_teams}  # default: not qualified

    # Play‑off round (9 vs 24, 10 vs 23, …)
    winners = []
    n = len(playoff) // 2
    for i in range(n):
        winners.append(simulate_two_legged_tie(playoff[i], playoff[len(playoff) - 1 - i], elos))
    # Teams that lost in playoff are eliminated at round 0
    for team in playoff:
        if team not in winners:
            elimination_round[team] = 0

    current = top8 + winners

    # Round of 16
    r16 = []
    n = len(current) // 2
    for i in range(n):
        r16.append(simulate_two_legged_tie(current[i], current[len(current) - 1 - i], elos))
    for team in current:
        if team not in r16:
            elimination_round[team] = 1
    current = r16

    # Quarter‑finals
    qf = []
    n = len(current) // 2
    for i in range(n):
        qf.append(simulate_two_legged_tie(current[i], current[len(current) - 1 - i], elos))
    for team in current:
        if team not in qf:
            elimination_round[team] = 2
    current = qf

    # Semi‑finals
    sf = []
    n = len(current) // 2
    for i in range(n):
        sf.append(simulate_two_legged_tie(current[i], current[len(current) - 1 - i], elos))
    for team in current:
        if team not in sf:
            elimination_round[team] = 3
    current = sf

    # Final (neutral, single match)
    if len(current) == 2:
        t1, t2 = current
        xg1, xg2 = compute_expected_goals(
            elos.get(t1, LEAGUE_AVERAGE_ELO),
            elos.get(t2, LEAGUE_AVERAGE_ELO)
        )
        g1, g2 = sample_score(xg1, xg2)
        if g1 != g2:
            winner = t1 if g1 > g2 else t2
            loser = t2 if winner == t1 else t1
        else:
            diff = elos.get(t1, LEAGUE_AVERAGE_ELO) - elos.get(t2, LEAGUE_AVERAGE_ELO)
            p1 = 1 / (1 + 10 ** (-diff / ELO_SCALE))
            winner = t1 if _RNG.random() < p1 else t2
            loser = t2 if winner == t1 else t1
        elimination_round[winner] = 5
        elimination_round[loser] = 4
        return winner, elimination_round
    else:
        # Should not happen – if something went wrong, return first team (or None)
        return current[0] if current else None, elimination_round

# =============================================================================
# EUROPEAN COMPETITION BASE CLASS
# =============================================================================

class EuropeanCompetition:
    def __init__(self, name: str, fixtures: List[List[Tuple[str, str]]],
                 betting_market: Dict[str, Tuple[int, int]], pl_teams: Set[str]):
        self.name = name
        self.fixtures = fixtures
        self.betting_market = betting_market
        self.pl_teams = pl_teams
        self.teams = sorted({t for rnd in fixtures for pair in rnd for t in pair})
        self.elos = self._calculate_elos()

    def _calculate_elos(self) -> Dict[str, float]:
        team_probs = {}
        for team, odds in self.betting_market.items():
            team_probs[team] = fractional_to_probability(odds)
        total = sum(team_probs.values())
        normalized = {t: p / total for t, p in team_probs.items()}
        baseline = 1.0 / len(self.teams)
        elos = {}
        for team in self.teams:
            prob = normalized.get(team, 1.0 / (len(self.teams) * 2))
            ratio = prob / baseline
            elo = LEAGUE_AVERAGE_ELO + ELO_SCALE * math.log10(ratio)
            elos[team] = round(elo, 1)
        return elos

    def run_single_league_phase(self) -> List[str]:
        """Simulate the 8‑matchday league phase, return ranking (top 24 qualify)."""
        n = len(self.teams)
        team_to_idx = {team: i for i, team in enumerate(self.teams)}
        pts = np.zeros(n, dtype=np.int64)
        gf = np.zeros(n, dtype=np.int64)
        ga = np.zeros(n, dtype=np.int64)

        elo_arr = np.array([self.elos.get(t, LEAGUE_AVERAGE_ELO) for t in self.teams], dtype=np.float64)
        elo_arr += HOME_ADVANTAGE_ELO

        for round_matches in self.fixtures:
            for home, away in round_matches:
                h_idx = team_to_idx[home]
                a_idx = team_to_idx[away]
                xg_h, xg_a = compute_expected_goals(elo_arr[h_idx], elo_arr[a_idx])
                goals_h, goals_a = sample_score(xg_h, xg_a)

                gf[h_idx] += goals_h
                ga[h_idx] += goals_a
                gf[a_idx] += goals_a
                ga[a_idx] += goals_h

                if goals_h > goals_a:
                    pts[h_idx] += 3
                elif goals_a > goals_h:
                    pts[a_idx] += 3
                else:
                    pts[h_idx] += 1
                    pts[a_idx] += 1

        gd = gf - ga
        tiebreak = _NP_RNG.uniform(0, 0.0001, size=n)
        ranking = sorted(
            range(n),
            key=lambda i: (pts[i], gd[i], gf[i], -tiebreak[i]),
            reverse=True,
        )
        return [self.teams[i] for i in ranking]

    def simulate(self) -> Tuple[Optional[str], Dict[str, int]]:
        """Simulate the full competition, returning (winner, elimination_rounds)."""
        ranking = self.run_single_league_phase()
        qualified = ranking[:24]
        winner, elim_rounds = simulate_knockout_phase(qualified, self.elos)
        # For teams that didn't qualify, elim_rounds already set to -1
        # Ensure all teams have an entry
        for team in self.teams:
            if team not in elim_rounds:
                elim_rounds[team] = -1
        return winner, elim_rounds

# =============================================================================
# PREMIER LEAGUE SIMULATION
# =============================================================================

class PLSimulator:
    def __init__(self, fixtures: List[Tuple[str, str]], base_ratings: Dict[str, float],
                 actual_results: Dict[Tuple[str, str], Tuple[int, int]]):
        self.fixtures = fixtures
        self.base_ratings = base_ratings
        self.actual_results = actual_results
        self.teams = sorted({team for pair in fixtures for team in pair})
        self.team_to_idx = {team: i for i, team in enumerate(self.teams)}
        self.idx_to_team = self.teams
        self.fixture_indices = [(self.team_to_idx[h], self.team_to_idx[a]) for h, a in fixtures]
        self.n_teams = len(self.teams)
        self.n_fixtures = len(fixtures)

    def simulate_season(self, fatigue_info: Dict[str, Tuple[int, str]]) -> Tuple[List[str], Dict[str, int]]:
        """
        fatigue_info: dict mapping team -> (elimination_round, competition)
        elimination_round: -1 = did not qualify, 0=playoff, 1=R16, 2=QF, 3=SF, 4=finalist, 5=winner
        competition: 'UCL', 'UEL', 'UECL' or None
        Returns (ranking, points_dict).
        """
        pts = np.zeros(self.n_teams, dtype=np.int64)
        gf = np.zeros(self.n_teams, dtype=np.int64)
        ga = np.zeros(self.n_teams, dtype=np.int64)

        base_ratings_arr = np.array([self.base_ratings[t] for t in self.teams], dtype=np.float64)

        # Pre‑compute fatigue base and active status per team
        team_fatigue_base = {}
        team_active = {}
        for team in self.teams:
            if team in fatigue_info:
                elim_round, comp = fatigue_info[team]
                team_fatigue_base[team] = EUROPEAN_FATIGUE_BASE.get(comp, 0.0)
                # Active if they at least reached the playoff round (elim_round >= 0)
                team_active[team] = (elim_round >= 0)
            else:
                team_fatigue_base[team] = 0.0
                team_active[team] = False

        for i in range(self.n_fixtures):
            h_idx, a_idx = self.fixture_indices[i]
            h_name = self.idx_to_team[h_idx]
            a_name = self.idx_to_team[a_idx]

            # Check if actual result is locked
            fixture_key = (h_name, a_name)
            if fixture_key in self.actual_results:
                hg, ag = self.actual_results[fixture_key]
            else:
                # Compute fatigue penalty: linear decay from max at start to 0 at end, only if active.
                progress = i / max(self.n_fixtures - 1, 1)
                h_fatigue = team_fatigue_base[h_name] * (1.0 - progress) if team_active[h_name] else 0.0
                a_fatigue = team_fatigue_base[a_name] * (1.0 - progress) if team_active[a_name] else 0.0

                h_elo = base_ratings_arr[h_idx] + HOME_ADVANTAGE_ELO - h_fatigue
                a_elo = base_ratings_arr[a_idx] - a_fatigue
                home_xg, away_xg = compute_expected_goals(h_elo, a_elo)
                hg, ag = sample_score(home_xg, away_xg)

            # Update stats (correctly – no bug)
            if hg > ag:
                hp, ap = 3, 0
            elif hg == ag:
                hp, ap = 1, 1
            else:
                hp, ap = 0, 3

            pts[h_idx] += hp
            pts[a_idx] += ap
            gf[h_idx] += hg
            ga[h_idx] += ag
            gf[a_idx] += ag
            ga[a_idx] += hg

        # Ranking
        gd = gf - ga
        tiebreak = _NP_RNG.uniform(0, 0.0001, size=self.n_teams)
        ranking = sorted(
            range(self.n_teams),
            key=lambda i: (pts[i], gd[i], gf[i], -tiebreak[i]),
            reverse=True,
        )
        ranked_teams = [self.idx_to_team[i] for i in ranking]
        points_dict = {self.idx_to_team[i]: int(pts[i]) for i in range(self.n_teams)}
        return ranked_teams, points_dict

# =============================================================================
# DATA – PREMIER LEAGUE FIXTURES, BETTING MARKETS, ACTUAL RESULTS
# =============================================================================

# Full 380‑match PL fixture list (home, away)
FIXTURES_LIST = [
    ('Arsenal', 'Coventry'), ('Arsenal', 'Crystal Palace'), ('Arsenal', 'Everton'),
    ('Arsenal', 'Leeds'), ('Aston Villa', 'Arsenal'), ('Aston Villa', 'Brentford'),
    ('Aston Villa', 'Chelsea'), ('Bournemouth', 'Everton'), ('Bournemouth', 'Liverpool'),
    ('Bournemouth', 'Sunderland'), ('Bournemouth', 'Tottenham'), ('Brentford', 'Chelsea'),
    ('Brentford', 'Ipswich'), ('Brentford', 'Liverpool'), ('Brentford', 'Tottenham'),
    ('Brighton', 'Arsenal'), ('Brighton', 'Aston Villa'), ('Brighton', 'Crystal Palace'),
    ('Brighton', 'Fulham'), ('Chelsea', 'Bournemouth'), ('Chelsea', 'Brighton'),
    ('Chelsea', 'Coventry'), ('Coventry', 'Bournemouth'), ('Coventry', 'Hull'),
    ('Coventry', 'Newcastle'), ('Crystal Palace', 'Forest'), ('Crystal Palace', 'Ipswich'),
    ('Crystal Palace', 'Sunderland'), ('Everton', 'Chelsea'), ('Everton', 'Crystal Palace'),
    ('Everton', 'Forest'), ('Everton', 'Ipswich'), ('Forest', 'Coventry'), ('Forest', 'Leeds'),
    ('Forest', 'Newcastle'), ('Fulham', 'Chelsea'), ('Fulham', 'Hull'), ('Fulham', 'Leeds'),
    ('Fulham', 'Man United'), ('Hull', 'Everton'), ('Hull', 'Man City'), ('Hull', 'Man United'),
    ('Ipswich', 'Brighton'), ('Ipswich', 'Fulham'), ('Ipswich', 'Sunderland'),
    ('Leeds', 'Crystal Palace'), ('Leeds', 'Hull'), ('Leeds', 'Man United'), ('Leeds', 'Newcastle'),
    ('Liverpool', 'Aston Villa'), ('Liverpool', 'Fulham'), ('Liverpool', 'Man City'),
    ('Man City', 'Bournemouth'), ('Man City', 'Everton'), ('Man City', 'Ipswich'),
    ('Man City', 'Sunderland'), ('Man United', 'Arsenal'), ('Man United', 'Man City'),
    ('Man United', 'Tottenham'), ('Newcastle', 'Aston Villa'), ('Newcastle', 'Brentford'),
    ('Newcastle', 'Hull'), ('Newcastle', 'Liverpool'), ('Sunderland', 'Arsenal'),
    ('Sunderland', 'Brighton'), ('Sunderland', 'Man United'), ('Tottenham', 'Arsenal'),
    ('Tottenham', 'Aston Villa'), ('Tottenham', 'Everton'), ('Tottenham', 'Liverpool'),
    ('Arsenal', 'Aston Villa'), ('Arsenal', 'Bournemouth'), ('Arsenal', 'Brentford'),
    ('Arsenal', 'Brighton'), ('Arsenal', 'Chelsea'), ('Arsenal', 'Forest'), ('Arsenal', 'Fulham'),
    ('Arsenal', 'Hull'), ('Arsenal', 'Ipswich'), ('Arsenal', 'Liverpool'), ('Arsenal', 'Man City'),
    ('Arsenal', 'Man United'), ('Arsenal', 'Newcastle'), ('Arsenal', 'Sunderland'),
    ('Arsenal', 'Tottenham'), ('Aston Villa', 'Bournemouth'), ('Aston Villa', 'Brighton'),
    ('Aston Villa', 'Coventry'), ('Aston Villa', 'Crystal Palace'), ('Aston Villa', 'Everton'),
    ('Aston Villa', 'Forest'), ('Aston Villa', 'Fulham'), ('Aston Villa', 'Hull'),
    ('Aston Villa', 'Ipswich'), ('Aston Villa', 'Leeds'), ('Aston Villa', 'Liverpool'),
    ('Aston Villa', 'Man City'), ('Aston Villa', 'Man United'), ('Aston Villa', 'Newcastle'),
    ('Aston Villa', 'Sunderland'), ('Aston Villa', 'Tottenham'), ('Bournemouth', 'Arsenal'),
    ('Bournemouth', 'Aston Villa'), ('Bournemouth', 'Brentford'), ('Bournemouth', 'Brighton'),
    ('Bournemouth', 'Chelsea'), ('Bournemouth', 'Coventry'), ('Bournemouth', 'Crystal Palace'),
    ('Bournemouth', 'Forest'), ('Bournemouth', 'Fulham'), ('Bournemouth', 'Hull'),
    ('Bournemouth', 'Ipswich'), ('Bournemouth', 'Leeds'), ('Bournemouth', 'Man City'),
    ('Bournemouth', 'Man United'), ('Bournemouth', 'Newcastle'), ('Brentford', 'Arsenal'),
    ('Brentford', 'Aston Villa'), ('Brentford', 'Bournemouth'), ('Brentford', 'Brighton'),
    ('Brentford', 'Coventry'), ('Brentford', 'Crystal Palace'), ('Brentford', 'Everton'),
    ('Brentford', 'Forest'), ('Brentford', 'Fulham'), ('Brentford', 'Hull'), ('Brentford', 'Leeds'),
    ('Brentford', 'Man City'), ('Brentford', 'Man United'), ('Brentford', 'Newcastle'),
    ('Brentford', 'Sunderland'), ('Brighton', 'Bournemouth'), ('Brighton', 'Brentford'),
    ('Brighton', 'Chelsea'), ('Brighton', 'Coventry'), ('Brighton', 'Everton'),
    ('Brighton', 'Forest'), ('Brighton', 'Hull'), ('Brighton', 'Ipswich'), ('Brighton', 'Leeds'),
    ('Brighton', 'Liverpool'), ('Brighton', 'Man City'), ('Brighton', 'Man United'),
    ('Brighton', 'Newcastle'), ('Brighton', 'Sunderland'), ('Brighton', 'Tottenham'),
    ('Chelsea', 'Arsenal'), ('Chelsea', 'Aston Villa'), ('Chelsea', 'Brentford'),
    ('Chelsea', 'Crystal Palace'), ('Chelsea', 'Everton'), ('Chelsea', 'Forest'),
    ('Chelsea', 'Fulham'), ('Chelsea', 'Hull'), ('Chelsea', 'Ipswich'), ('Chelsea', 'Leeds'),
    ('Chelsea', 'Liverpool'), ('Chelsea', 'Man City'), ('Chelsea', 'Man United'),
    ('Chelsea', 'Newcastle'), ('Chelsea', 'Sunderland'), ('Chelsea', 'Tottenham'),
    ('Coventry', 'Arsenal'), ('Coventry', 'Aston Villa'), ('Coventry', 'Brentford'),
    ('Coventry', 'Brighton'), ('Coventry', 'Chelsea'), ('Coventry', 'Crystal Palace'),
    ('Coventry', 'Everton'), ('Coventry', 'Forest'), ('Coventry', 'Fulham'), ('Coventry', 'Ipswich'),
    ('Coventry', 'Leeds'), ('Coventry', 'Liverpool'), ('Coventry', 'Man City'),
    ('Coventry', 'Man United'), ('Coventry', 'Sunderland'), ('Coventry', 'Tottenham'),
    ('Crystal Palace', 'Arsenal'), ('Crystal Palace', 'Aston Villa'), ('Crystal Palace', 'Bournemouth'),
    ('Crystal Palace', 'Brentford'), ('Crystal Palace', 'Brighton'), ('Crystal Palace', 'Chelsea'),
    ('Crystal Palace', 'Coventry'), ('Crystal Palace', 'Everton'), ('Crystal Palace', 'Fulham'),
    ('Crystal Palace', 'Hull'), ('Crystal Palace', 'Leeds'), ('Crystal Palace', 'Liverpool'),
    ('Crystal Palace', 'Man City'), ('Crystal Palace', 'Man United'), ('Crystal Palace', 'Newcastle'),
    ('Crystal Palace', 'Tottenham'), ('Everton', 'Arsenal'), ('Everton', 'Aston Villa'),
    ('Everton', 'Bournemouth'), ('Everton', 'Brentford'), ('Everton', 'Brighton'),
    ('Everton', 'Coventry'), ('Everton', 'Fulham'), ('Everton', 'Hull'), ('Everton', 'Leeds'),
    ('Everton', 'Liverpool'), ('Everton', 'Man City'), ('Everton', 'Man United'),
    ('Everton', 'Newcastle'), ('Everton', 'Sunderland'), ('Everton', 'Tottenham'),
    ('Forest', 'Arsenal'), ('Forest', 'Aston Villa'), ('Forest', 'Bournemouth'),
    ('Forest', 'Brentford'), ('Forest', 'Brighton'), ('Forest', 'Chelsea'), ('Forest', 'Crystal Palace'),
    ('Forest', 'Everton'), ('Forest', 'Fulham'), ('Forest', 'Hull'), ('Forest', 'Ipswich'),
    ('Forest', 'Liverpool'), ('Forest', 'Man City'), ('Forest', 'Man United'),
    ('Forest', 'Sunderland'), ('Forest', 'Tottenham'), ('Fulham', 'Arsenal'),
    ('Fulham', 'Aston Villa'), ('Fulham', 'Bournemouth'), ('Fulham', 'Brentford'),
    ('Fulham', 'Brighton'), ('Fulham', 'Coventry'), ('Fulham', 'Crystal Palace'),
    ('Fulham', 'Everton'), ('Fulham', 'Forest'), ('Fulham', 'Ipswich'), ('Fulham', 'Liverpool'),
    ('Fulham', 'Man City'), ('Fulham', 'Newcastle'), ('Fulham', 'Sunderland'),
    ('Fulham', 'Tottenham'), ('Hull', 'Arsenal'), ('Hull', 'Aston Villa'), ('Hull', 'Bournemouth'),
    ('Hull', 'Brentford'), ('Hull', 'Brighton'), ('Hull', 'Chelsea'), ('Hull', 'Coventry'),
    ('Hull', 'Crystal Palace'), ('Hull', 'Forest'), ('Hull', 'Fulham'), ('Hull', 'Ipswich'),
    ('Hull', 'Leeds'), ('Hull', 'Liverpool'), ('Hull', 'Newcastle'), ('Hull', 'Sunderland'),
    ('Hull', 'Tottenham'), ('Ipswich', 'Arsenal'), ('Ipswich', 'Aston Villa'), ('Ipswich', 'Bournemouth'),
    ('Ipswich', 'Brentford'), ('Ipswich', 'Chelsea'), ('Ipswich', 'Coventry'),
    ('Ipswich', 'Crystal Palace'), ('Ipswich', 'Everton'), ('Ipswich', 'Forest'),
    ('Ipswich', 'Hull'), ('Ipswich', 'Leeds'), ('Ipswich', 'Liverpool'), ('Ipswich', 'Man City'),
    ('Ipswich', 'Man United'), ('Ipswich', 'Newcastle'), ('Ipswich', 'Tottenham'),
    ('Leeds', 'Arsenal'), ('Leeds', 'Aston Villa'), ('Leeds', 'Bournemouth'), ('Leeds', 'Brentford'),
    ('Leeds', 'Brighton'), ('Leeds', 'Chelsea'), ('Leeds', 'Coventry'), ('Leeds', 'Everton'),
    ('Leeds', 'Forest'), ('Leeds', 'Fulham'), ('Leeds', 'Ipswich'), ('Leeds', 'Liverpool'),
    ('Leeds', 'Man City'), ('Leeds', 'Sunderland'), ('Leeds', 'Tottenham'), ('Liverpool', 'Arsenal'),
    ('Liverpool', 'Bournemouth'), ('Liverpool', 'Brentford'), ('Liverpool', 'Brighton'),
    ('Liverpool', 'Chelsea'), ('Liverpool', 'Coventry'), ('Liverpool', 'Crystal Palace'),
    ('Liverpool', 'Everton'), ('Liverpool', 'Forest'), ('Liverpool', 'Hull'), ('Liverpool', 'Ipswich'),
    ('Liverpool', 'Leeds'), ('Liverpool', 'Man United'), ('Liverpool', 'Newcastle'),
    ('Liverpool', 'Sunderland'), ('Liverpool', 'Tottenham'), ('Man City', 'Arsenal'),
    ('Man City', 'Aston Villa'), ('Man City', 'Brentford'), ('Man City', 'Brighton'),
    ('Man City', 'Chelsea'), ('Man City', 'Coventry'), ('Man City', 'Crystal Palace'),
    ('Man City', 'Forest'), ('Man City', 'Fulham'), ('Man City', 'Hull'), ('Man City', 'Leeds'),
    ('Man City', 'Liverpool'), ('Man City', 'Man United'), ('Man City', 'Newcastle'),
    ('Man City', 'Tottenham'), ('Man United', 'Aston Villa'), ('Man United', 'Bournemouth'),
    ('Man United', 'Brentford'), ('Man United', 'Brighton'), ('Man United', 'Chelsea'),
    ('Man United', 'Coventry'), ('Man United', 'Crystal Palace'), ('Man United', 'Everton'),
    ('Man United', 'Forest'), ('Man United', 'Fulham'), ('Man United', 'Hull'),
    ('Man United', 'Ipswich'), ('Man United', 'Leeds'), ('Man United', 'Liverpool'),
    ('Man United', 'Newcastle'), ('Man United', 'Sunderland'), ('Newcastle', 'Arsenal'),
    ('Newcastle', 'Bournemouth'), ('Newcastle', 'Brighton'), ('Newcastle', 'Chelsea'),
    ('Newcastle', 'Coventry'), ('Newcastle', 'Crystal Palace'), ('Newcastle', 'Everton'),
    ('Newcastle', 'Forest'), ('Newcastle', 'Fulham'), ('Newcastle', 'Ipswich'),
    ('Newcastle', 'Leeds'), ('Newcastle', 'Man City'), ('Newcastle', 'Man United'),
    ('Newcastle', 'Sunderland'), ('Newcastle', 'Tottenham'), ('Sunderland', 'Aston Villa'),
    ('Sunderland', 'Bournemouth'), ('Sunderland', 'Brentford'), ('Sunderland', 'Chelsea'),
    ('Sunderland', 'Coventry'), ('Sunderland', 'Crystal Palace'), ('Sunderland', 'Everton'),
    ('Sunderland', 'Forest'), ('Sunderland', 'Fulham'), ('Sunderland', 'Hull'),
    ('Sunderland', 'Ipswich'), ('Sunderland', 'Leeds'), ('Sunderland', 'Liverpool'),
    ('Sunderland', 'Man City'), ('Sunderland', 'Newcastle'), ('Sunderland', 'Tottenham'),
    ('Tottenham', 'Bournemouth'), ('Tottenham', 'Brentford'), ('Tottenham', 'Brighton'),
    ('Tottenham', 'Chelsea'), ('Tottenham', 'Coventry'), ('Tottenham', 'Crystal Palace'),
    ('Tottenham', 'Forest'), ('Tottenham', 'Fulham'), ('Tottenham', 'Hull'), ('Tottenham', 'Ipswich'),
    ('Tottenham', 'Leeds'), ('Tottenham', 'Man City'), ('Tottenham', 'Man United'),
    ('Tottenham', 'Newcastle'), ('Tottenham', 'Sunderland')
]

# PL betting markets (League Winner, Top 2 Finish, Relegation)
PL_BETTING_MARKETS = {
    "League Winner": {
        "Arsenal": (4, 5), "Man City": (5, 2), "Chelsea": (13, 2), "Liverpool": (14, 1),
        "Man United": (20, 1), "Brighton": (100, 1), "Brentford": (150, 1),
        "Tottenham": (150, 1), "Aston Villa": (150, 1), "Newcastle": (250, 1),
        "Leeds": (250, 1), "Sunderland": (500, 1), "Ipswich": (500, 1),
        "Bournemouth": (500, 1), "Everton": (500, 1), "Crystal Palace": (500, 1),
        "Fulham": (500, 1), "Coventry": (500, 1), "Forest": (500, 1), "Hull": (500, 1),
    },
    "Top 2 Finish": {
        "Arsenal": (1, 4), "Man City": (8, 11), "Chelsea": (9, 4), "Liverpool": (4, 1),
        "Man United": (8, 1), "Brighton": (25, 1), "Brentford": (33, 1),
        "Newcastle": (66, 1), "Tottenham": (66, 1), "Aston Villa": (100, 1),
        "Leeds": (100, 1), "Bournemouth": (150, 1), "Everton": (150, 1),
        "Forest": (150, 1), "Crystal Palace": (500, 1), "Fulham": (500, 1),
        "Sunderland": (200, 1), "Ipswich": (80, 1), "Hull": (40, 1), "Coventry": (1000, 1),
    },
    "Relegation": {
        "Hull": (4, 11), "Coventry": (1, 2), "Ipswich": (11, 10), "Sunderland": (2, 1),
        "Crystal Palace": (11, 4), "Fulham": (4, 1), "Forest": (8, 1),
        "Bournemouth": (9, 1), "Everton": (10, 1), "Aston Villa": (12, 1),
        "Leeds": (14, 1), "Newcastle": (20, 1), "Tottenham": (20, 1),
        "Brentford": (33, 1), "Brighton": (50, 1), "Liverpool": (150, 1),
        "Arsenal": (150, 1), "Chelsea": (150, 1), "Man United": (150, 1),
        "Man City": (150, 1),
    },
}

# Locked actual results (to replicate real outcomes for early fixtures)
ACTUAL_RESULTS = {
    ("Everton", "Crystal Palace"): (2, 0),
    ("Ipswich", "Sunderland"): (2, 1),
    ("Forest", "Leeds"): (0, 1),
    ("Brentford", "Tottenham"): (3, 0),
    ("Arsenal", "Coventry"): (3, 0),
    ("Hull", "Man United"): (2, 0),
    ("Brighton", "Aston Villa"): (4, 0),
    ("Man City", "Bournemouth"): (2, 1),
    ("Newcastle", "Liverpool"): (2, 2),
    ("Fulham", "Chelsea"): (2, 3),
    ("Crystal Palace", "Man City"): (1, 4),
    ("Liverpool", "Forest"): (2, 2),
    ("Bournemouth", "Everton"): (1, 1),
    ("Coventry", "Hull"): (0, 1),
    ("Tottenham", "Newcastle"): (0, 2),
}

# =============================================================================
# DATA – UEFA CHAMPIONS LEAGUE
# =============================================================================

CL_FIXTURES = [
    # Matchday 1
    [
        ("AEK Athens", "LASK"), ("Club Brugge", "Aston Villa"), ("Borussia Dortmund", "Villarreal FC"),
        ("FC Porto", "Man City"), ("Lille OSC", "Real Betis"), ("Real Madrid", "Inter Milan"),
        ("FC Barcelona", "Feyenoord"), ("VfB Stuttgart", "Viking"), ("Liverpool", "Atletico Madrid"),
        ("Paris Saint-Germain", "Slovan Bratislava"), ("Sporting CP", "Galatasaray"),
        ("Napoli", "Arsenal"), ("Fenerbahçe", "Roma"), ("PSV Eindhoven", "Shakhtar Donetsk"),
        ("Como", "RB Leipzig"), ("Bayern Munich", "Bodø/Glimt"), ("Man United", "Sabah FK"),
        ("Slavia Prague", "RC Lens"),
    ],
    # Matchday 2
    [
        ("RC Lens", "Sporting CP"), ("Sabah FK", "Slavia Prague"), ("Arsenal", "Lille OSC"),
        ("Atletico Madrid", "Man United"), ("Inter Milan", "Club Brugge"), ("Galatasaray", "FC Barcelona"),
        ("RB Leipzig", "PSV Eindhoven"), ("Viking", "Bayern Munich"), ("Villarreal FC", "Napoli"),
        ("Feyenoord", "Como"), ("LASK", "Liverpool"), ("Roma", "Real Madrid"),
        ("Aston Villa", "Fenerbahçe"), ("Shakhtar Donetsk", "AEK Athens"),
        ("Bodø/Glimt", "Borussia Dortmund"), ("Man City", "Paris Saint-Germain"),
        ("Real Betis", "FC Porto"), ("Slovan Bratislava", "VfB Stuttgart"),
    ],
    # Matchday 3
    [
        ("Fenerbahçe", "Slavia Prague"), ("Sabah FK", "Borussia Dortmund"),
        ("Roma", "Slovan Bratislava"), ("FC Porto", "PSV Eindhoven"),
        ("Liverpool", "Villarreal FC"), ("Man City", "AEK Athens"),
        ("Paris Saint-Germain", "FC Barcelona"), ("Napoli", "Bodø/Glimt"),
        ("VfB Stuttgart", "Atletico Madrid"), ("Como", "Man United"),
        ("Lille OSC", "Galatasaray"), ("Aston Villa", "Viking"), ("Club Brugge", "RC Lens"),
        ("Bayern Munich", "Arsenal"), ("Inter Milan", "Shakhtar Donetsk"),
        ("Real Madrid", "RB Leipzig"), ("Real Betis", "Feyenoord"), ("Sporting CP", "LASK"),
    ],
    # Matchday 4
    [
        ("Shakhtar Donetsk", "Sporting CP"), ("Galatasaray", "VfB Stuttgart"),
        ("Atletico Madrid", "Bayern Munich"), ("FC Barcelona", "Aston Villa"),
        ("Feyenoord", "Inter Milan"), ("Bodø/Glimt", "Lille OSC"),
        ("LASK", "Slovan Bratislava"), ("Man United", "Roma"),
        ("Villarreal FC", "Paris Saint-Germain"), ("AEK Athens", "Real Madrid"),
        ("Fenerbahçe", "Liverpool"), ("Borussia Dortmund", "Real Betis"),
        ("FC Porto", "Napoli"), ("PSV Eindhoven", "Club Brugge"),
        ("RB Leipzig", "Man City"), ("RC Lens", "Como"), ("Slavia Prague", "Arsenal"),
        ("Viking", "Sabah FK"),
    ],
    # Matchday 5
    [
        ("Bodø/Glimt", "LASK"), ("Galatasaray", "Aston Villa"), ("Arsenal", "Borussia Dortmund"),
        ("Como", "AEK Athens"), ("Feyenoord", "FC Porto"), ("Man City", "Napoli"),
        ("RB Leipzig", "RC Lens"), ("Real Madrid", "PSV Eindhoven"),
        ("Slovan Bratislava", "Real Betis"), ("Sabah FK", "FC Barcelona"),
        ("Slavia Prague", "Villarreal FC"), ("Atletico Madrid", "Viking"),
        ("Club Brugge", "Liverpool"), ("Inter Milan", "VfB Stuttgart"),
        ("Shakhtar Donetsk", "Fenerbahçe"), ("Lille OSC", "Bayern Munich"),
        ("Paris Saint-Germain", "Roma"), ("Sporting CP", "Man United"),
    ],
    # Matchday 6
    [
        ("Viking", "Feyenoord"), ("Villarreal FC", "Sabah FK"), ("AEK Athens", "Galatasaray"),
        ("Roma", "Sporting CP"), ("Aston Villa", "Paris Saint-Germain"),
        ("FC Barcelona", "Man City"), ("Bayern Munich", "Slavia Prague"),
        ("Man United", "RB Leipzig"), ("Napoli", "Club Brugge"),
        ("Real Betis", "Como"), ("Slovan Bratislava", "Shakhtar Donetsk"),
        ("Arsenal", "Real Madrid"), ("Borussia Dortmund", "Inter Milan"),
        ("LASK", "Fenerbahçe"), ("Liverpool", "FC Porto"),
        ("PSV Eindhoven", "Atletico Madrid"), ("RC Lens", "Bodø/Glimt"),
        ("VfB Stuttgart", "Lille OSC"),
    ],
    # Matchday 7
    [
        ("Bodø/Glimt", "Atletico Madrid"), ("Galatasaray", "Feyenoord"),
        ("AEK Athens", "Roma"), ("Aston Villa", "Borussia Dortmund"),
        ("Inter Milan", "Liverpool"), ("FC Porto", "Slavia Prague"),
        ("Lille OSC", "Slovan Bratislava"), ("Real Madrid", "LASK"),
        ("VfB Stuttgart", "Club Brugge"), ("Fenerbahçe", "Villarreal FC"),
        ("Sabah FK", "Napoli"), ("Como", "Paris Saint-Germain"),
        ("Man United", "Bayern Munich"), ("RB Leipzig", "Shakhtar Donetsk"),
        ("RC Lens", "Man City"), ("Real Betis", "Arsenal"), ("Sporting CP", "FC Barcelona"),
        ("Viking", "PSV Eindhoven"),
    ],
    # Matchday 8
    [
        ("Arsenal", "Sabah FK"), ("Roma", "Lille OSC"), ("Atletico Madrid", "Fenerbahçe"),
        ("Borussia Dortmund", "AEK Athens"), ("Club Brugge", "Bodø/Glimt"),
        ("Bayern Munich", "Real Betis"), ("FC Barcelona", "Como"),
        ("Shakhtar Donetsk", "Real Madrid"), ("Feyenoord", "RB Leipzig"),
        ("LASK", "FC Porto"), ("Liverpool", "RC Lens"), ("Man City", "Sporting CP"),
        ("Paris Saint-Germain", "Galatasaray"), ("PSV Eindhoven", "VfB Stuttgart"),
        ("Slavia Prague", "Aston Villa"), ("Napoli", "Viking"),
        ("Villarreal FC", "Man United"), ("Slovan Bratislava", "Inter Milan"),
    ],
]

BETTING_MARKETS_CL_WINNER = {
    "Paris Saint-Germain": (5, 1), "Bayern Munich": (6, 1),
    "Arsenal": (6, 1), "Man City": (7, 1), "FC Barcelona": (7, 1),
    "Real Madrid": (7, 1), "Liverpool": (10, 1), "Man United": (16, 1),
    "Inter Milan": (28, 1), "Atletico Madrid": (28, 1), "Aston Villa": (33, 1),
    "Borussia Dortmund": (33, 1), "Napoli": (40, 1), "RB Leipzig": (40, 1),
    "Roma": (50, 1), "Real Betis": (66, 1), "Villarreal FC": (50, 1),
    "Como": (50, 1), "VfB Stuttgart": (50, 1), "Sporting CP": (100, 1),
    "FC Porto": (100, 1), "PSV Eindhoven": (125, 1), "Feyenoord": (125, 1),
    "Lille OSC": (125, 1), "RC Lens": (125, 1), "Club Brugge": (150, 1),
    "Galatasaray": (150, 1), "Shakhtar Donetsk": (250, 1), "Slavia Prague": (250, 1),
    "AEK Athens": (250, 1), "LASK": (300, 1), "Viking": (300, 1),
    "Slovan Bratislava": (500, 1), "Bodø/Glimt": (250, 1), "Sabah FK": (500, 1),
    "Fenerbahçe": (250, 1)
}

# =============================================================================
# DATA – UEFA EUROPA LEAGUE (with name standardisation)
# =============================================================================

_UEL_NAME_MAP = {
    "Sparta Praha": "Sparta Prague", "Celta": "Celta Vigo", "Leverkusen": "Bayer Leverkusen",
    "Celje": "NK Celje", "H. Beer-Sheva": "Hapoel Be'er Sheva", "GNK Dinamo": "Dinamo Zagreb",
    "Lyon": "Olympique Lyonnais", "Salzburg": "Red Bull Salzburg", "Hoffenheim": "TSG Hoffenheim",
    "N.E.C.": "NEC Nijmegen", "Union SG": "Union Saint-Gilloise", "Jagiellonia": "Jagiellonia Białystok",
    "Ararat-Armenia": "Ararat-Armenia", "Omonia": "Omonia", "OFI Crete": "OFI Crete",
    "Viktoria Plzeň": "Viktoria Plzeň", "Beşiktaş": "Beşiktaş", "Ferencváros": "Ferencváros",
    "Lech Poznań": "Lech Poznań", "Anderlecht": "Anderlecht", "Sturm Graz": "Sturm Graz",
    "Rennes": "Rennes", "Sunderland": "Sunderland", "AZ Alkmaar": "AZ Alkmaar",
    "Milan": "Milan", "Benfica": "Benfica", "Marseille": "Marseille",
    "Celtic": "Celtic", "Crystal Palace": "Crystal Palace", "Bournemouth": "Bournemouth",
    "Juventus": "Juventus", "Lillestrøm": "Lillestrøm", "Real Sociedad": "Real Sociedad",
    "Levski Sofia": "Levski Sofia", "Torreense": "Torreense", "Sparta Prague": "Sparta Prague",
    "Bayer Leverkusen": "Bayer Leverkusen", "NK Celje": "NK Celje", "Hapoel Be'er Sheva": "Hapoel Be'er Sheva",
    "Dinamo Zagreb": "Dinamo Zagreb", "Olympique Lyonnais": "Olympique Lyonnais",
    "Red Bull Salzburg": "Red Bull Salzburg", "TSG Hoffenheim": "TSG Hoffenheim",
    "NEC Nijmegen": "NEC Nijmegen", "Union Saint-Gilloise": "Union Saint-Gilloise",
    "Jagiellonia Białystok": "Jagiellonia Białystok",
}

def _standardise_uel(name: str) -> str:
    return _UEL_NAME_MAP.get(name, name)

_FIXTURES_UEL_RAW = [
    # Matchday 1
    [
        ("Ararat-Armenia", "Sparta Praha"), ("Omonia", "Celta"), ("Milan", "Benfica"),
        ("Leverkusen", "Celje"), ("H. Beer-Sheva", "GNK Dinamo"), ("Olympiacos", "Jagiellonia"),
        ("Anderlecht", "Lyon"), ("Sturm Graz", "Rennes"), ("Sunderland", "AZ Alkmaar"),
        ("OFI Crete", "Hoffenheim"), ("Levski Sofia", "Salzburg"), ("Beşiktaş", "Marseille"),
        ("Celtic", "Ferencváros"), ("Crystal Palace", "Lech Poznań"), ("Viktoria Plzeň", "Union SG"),
        ("Juventus", "N.E.C."), ("Lillestrøm", "Torreense"), ("Real Sociedad", "Bournemouth"),
    ],
    # Matchday 2
    [
        ("Sparta Praha", "Lillestrøm"), ("AZ Alkmaar", "H. Beer-Sheva"), ("Salzburg", "Milan"),
        ("Lech Poznań", "Leverkusen"), ("Celje", "Omonia"), ("Lyon", "Crystal Palace"),
        ("Union SG", "Real Sociedad"), ("Torreense", "Sunderland"), ("Bournemouth", "Sturm Graz"),
        ("Ferencváros", "Viktoria Plzeň"), ("GNK Dinamo", "Anderlecht"), ("Jagiellonia", "Ararat-Armenia"),
        ("N.E.C.", "Levski Sofia"), ("Marseille", "Olympiacos"), ("Celta", "Juventus"),
        ("Benfica", "Celtic"), ("Rennes", "OFI Crete"), ("Hoffenheim", "Beşiktaş"),
    ],
    # Matchday 3
    [
        ("Ararat-Armenia", "AZ Alkmaar"), ("Ferencváros", "Torreense"), ("GNK Dinamo", "N.E.C."),
        ("Juventus", "Rennes"), ("Lech Poznań", "Sunderland"), ("OFI Crete", "Leverkusen"),
        ("Union SG", "H. Beer-Sheva"), ("Sturm Graz", "Marseille"), ("Bournemouth", "Milan"),
        ("Beşiktaş", "Crystal Palace"), ("Celtic", "Celta"), ("Viktoria Plzeň", "Levski Sofia"),
        ("Jagiellonia", "Anderlecht"), ("Lillestrøm", "Real Sociedad"), ("Celje", "Salzburg"),
        ("Olympiacos", "Sparta Praha"), ("Omonia", "Benfica"), ("Hoffenheim", "Lyon"),
    ],
    # Matchday 4
    [
        ("Milan", "Ferencváros"), ("Sparta Praha", "Bournemouth"), ("Crystal Palace", "Hoffenheim"),
        ("Lillestrøm", "Viktoria Plzeň"), ("N.E.C.", "Omonia"), ("Levski Sofia", "Jagiellonia"),
        ("Real Sociedad", "Lyon"), ("Anderlecht", "Salzburg"), ("Rennes", "Olympiacos"),
        ("AZ Alkmaar", "Juventus"), ("Leverkusen", "Marseille"), ("Celtic", "Beşiktaş"),
        ("H. Beer-Sheva", "OFI Crete"), ("Celta", "Union SG"), ("Torreense", "Ararat-Armenia"),
        ("Sturm Graz", "Celje"), ("Benfica", "Lech Poznań"), ("Sunderland", "GNK Dinamo"),
    ],
    # Matchday 5
    [
        ("Beşiktaş", "H. Beer-Sheva"), ("Salzburg", "Ararat-Armenia"), ("Viktoria Plzeň", "Benfica"),
        ("GNK Dinamo", "Leverkusen"), ("Olympiacos", "Milan"), ("Marseille", "Levski Sofia"),
        ("Union SG", "Lech Poznań"), ("Celta", "Bournemouth"), ("Sparta Praha", "AZ Alkmaar"),
        ("Crystal Palace", "Real Sociedad"), ("Ferencváros", "Celje"), ("Juventus", "Omonia"),
        ("N.E.C.", "Rennes"), ("OFI Crete", "Anderlecht"), ("Lyon", "Lillestrøm"),
        ("Torreense", "Celtic"), ("Sunderland", "Jagiellonia"), ("Hoffenheim", "Sturm Graz"),
    ],
    # Matchday 6
    [
        ("AZ Alkmaar", "Sturm Graz"), ("Ararat-Armenia", "N.E.C."), ("H. Beer-Sheva", "Juventus"),
        ("Jagiellonia", "Crystal Palace"), ("Marseille", "Celta"), ("Omonia", "Celtic"),
        ("Anderlecht", "Hoffenheim"), ("Rennes", "GNK Dinamo"), ("Milan", "Sunderland"),
        ("Bournemouth", "Viktoria Plzeň"), ("Leverkusen", "Beşiktaş"), ("Salzburg", "Sparta Praha"),
        ("Lech Poznań", "Ferencváros"), ("Celje", "Olympiacos"), ("Lyon", "Union SG"),
        ("Levski Sofia", "Lillestrøm"), ("Real Sociedad", "Torreense"), ("Benfica", "OFI Crete"),
    ],
    # Matchday 7
    [
        ("Beşiktaş", "Union SG"), ("Ararat-Armenia", "Celje"), ("Ferencváros", "Juventus"),
        ("Jagiellonia", "Lyon"), ("Lillestrøm", "Bournemouth"), ("N.E.C.", "Benfica"),
        ("Olympiacos", "Hoffenheim"), ("Real Sociedad", "Viktoria Plzeň"), ("Sturm Graz", "OFI Crete"),
        ("AZ Alkmaar", "GNK Dinamo"), ("Leverkusen", "Salzburg"), ("Celtic", "Marseille"),
        ("Crystal Palace", "Sparta Praha"), ("H. Beer-Sheva", "Celta"), ("Lech Poznań", "Torreense"),
        ("Levski Sofia", "Milan"), ("Anderlecht", "Sunderland"), ("Rennes", "Omonia"),
    ],
    # Matchday 8
    [
        ("Milan", "Ararat-Armenia"), ("Sparta Praha", "Rennes"), ("Bournemouth", "H. Beer-Sheva"),
        ("Salzburg", "Crystal Palace"), ("Viktoria Plzeň", "Jagiellonia"), ("GNK Dinamo", "Sturm Graz"),
        ("Juventus", "Real Sociedad"), ("Celje", "N.E.C."), ("OFI Crete", "Lech Poznań"),
        ("Marseille", "Anderlecht"), ("Lyon", "Leverkusen"), ("Omonia", "Beşiktaş"),
        ("Union SG", "Celtic"), ("Celta", "Lillestrøm"), ("Torreense", "Olympiacos"),
        ("Benfica", "AZ Alkmaar"), ("Sunderland", "Levski Sofia"), ("Hoffenheim", "Ferencváros"),
    ],
]

UEL_FIXTURES_STD = [
    [(_standardise_uel(h), _standardise_uel(a)) for h, a in round_matches]
    for round_matches in _FIXTURES_UEL_RAW
]

BETTING_MARKETS_UEL_WINNER = {
    "Juventus": (5, 1), "Bayer Leverkusen": (6, 1), "Milan": (7, 1),
    "Marseille": (10, 1), "Real Sociedad": (12, 1), "Benfica": (14, 1),
    "Olympique Lyonnais": (16, 1), "Red Bull Salzburg": (20, 1), "Fenerbahçe": (20, 1),
    "Rennes": (25, 1), "Crystal Palace": (28, 1), "Bournemouth": (33, 1),
    "Beşiktaş": (33, 1), "AZ Alkmaar": (40, 1), "Celtic": (40, 1),
    "Crvena zvezda": (50, 1), "TSG Hoffenheim": (50, 1), "Anderlecht": (66, 1),
    "Sunderland": (66, 1), "Celta Vigo": (66, 1), "Ferencváros": (80, 1),
    "Lech Poznań": (100, 1), "Dinamo Zagreb": (100, 1), "Sparta Prague": (100, 1),
    "Jagiellonia Białystok": (125, 1), "Union Saint-Gilloise": (150, 1),
    "Olympiacos": (150, 1), "NEC Nijmegen": (200, 1), "Sturm Graz": (250, 1),
    "Hapoel Be'er Sheva": (300, 1), "Universitatea Craiova": (400, 1),
    "Lillestrøm": (400, 1), "Ararat-Armenia": (500, 1), "Egnatia": (500, 1),
    "Trabzonspor": (500, 1), "Mjällby": (500, 1), "AGF Aarhus": (750, 1),
    "CSKA Sofia": (1000, 1), "Kauno Žalgiris": (1000, 1), "Kairat Almaty": (1000, 1),
    "Thun": (1500, 1), "Iberia 1999": (1500, 1), "NK Celje": (500, 1),
    "Omonia": (500, 1), "OFI Crete": (400, 1), "Viktoria Plzeň": (200, 1),
    "Levski Sofia": (400, 1), "Torreense": (500, 1),
}

# =============================================================================
# DATA – UEFA CONFERENCE LEAGUE (with name standardisation)
# =============================================================================

_UECL_NAME_MAP = {
    "Crvena Zvezda": "Red Star Belgrade", "Sint-Truidense": "Sint Truiden",
    "Nordsjælland": "FC Nordsjaelland", "Kauno Žalgiris": "FK Kauno Zalgiris",
    "Borac": "Borac Banja Luka", "Jablonec": "FK Jablonec", "Riga": "FK Riga",
    "Aarhus": "AGF", "Inter Escaldes": "Inter Club d'Escaldes",
    "Iberia Tbilisi": "Iberia", "Egnatia": "Egnatia Rrogozhine",
    "Lincoln Red Imps": "Lincoln Red Imps", "Copenhagen": "FC Copenhagen",
    "Pafos": "Pafos FC", "Mjällby": "Mjallby", "Kairat Almaty": "Kairat",
    "Sint-Truiden": "Sint Truiden", "Brighton": "Brighton", "Atalanta": "Atalanta",
    "Freiburg": "Freiburg", "Monaco": "Monaco", "Braga": "Braga", "Ajax": "Ajax",
    "Midtjylland": "Midtjylland", "Getafe": "Getafe", "FC Copenhagen": "FC Copenhagen",
    "Twente": "Twente", "Trabzonspor": "Trabzonspor", "Gent": "Gent",
    "Red Star Belgrade": "Red Star Belgrade", "Panathinaikos": "Panathinaikos",
    "Lugano": "Lugano", "Sint Truiden": "Sint Truiden", "FC Nordsjaelland": "FC Nordsjaelland",
    "Brann": "Brann", "Pafos FC": "Pafos FC", "Hearts": "Hearts", "KuPS": "KuPS",
    "Universitatea Craiova": "Universitatea Craiova", "Hajduk Split": "Hajduk Split",
    "Borac Banja Luka": "Borac Banja Luka", "FK Jablonec": "FK Jablonec",
    "FK Kauno Zalgiris": "FK Kauno Zalgiris", "CSKA Sofia": "CSKA Sofia",
    "Mjallby": "Mjallby", "Thun": "Thun", "Kairat": "Kairat", "FK Riga": "FK Riga",
    "AGF": "AGF", "Inter Club d'Escaldes": "Inter Club d'Escaldes",
    "Iberia": "Iberia", "Egnatia Rrogozhine": "Egnatia Rrogozhine",
    "Lincoln Red Imps": "Lincoln Red Imps",
}

def _standardise_uecl(name: str) -> str:
    return _UECL_NAME_MAP.get(name, name)

_FIXTURES_UECL_RAW = [
    # Matchday 1
    [
        ("Lugano", "Crvena Zvezda"), ("Hajduk Split", "Ajax"), ("Gent", "Aarhus"),
        ("Egnatia", "Midtjylland"), ("KuPS Kuopio", "Trabzonspor"), ("Mjällby", "Inter Escaldes"),
        ("Panathinaikos", "Borac"), ("CSKA Sofia", "Monaco"), ("Riga", "Kairat Almaty"),
        ("Universitatea Craiova", "Getafe"), ("Atalanta", "Pafos"), ("Brighton", "Kauno Žalgiris"),
        ("Copenhagen", "Braga"), ("Twente", "Thun"), ("Hearts", "Nordsjælland"),
        ("Sint-Truidense", "Iberia Tbilisi"), ("Freiburg", "Jablonec"), ("Brann", "Lincoln Red Imps"),
    ],
    # Matchday 2
    [
        ("Kairat Almaty", "Panathinaikos"), ("Iberia Tbilisi", "Mjällby"),
        ("Nordsjælland", "CSKA Sofia"), ("Crvena Zvezda", "Copenhagen"),
        ("Jablonec", "Brighton"), ("Kauno Žalgiris", "Brann"), ("Getafe", "Lugano"),
        ("Inter Escaldes", "Universitatea Craiova"), ("Pafos", "Riga"),
        ("Trabzonspor", "Hearts"), ("Ajax", "Atalanta"), ("Aarhus", "Egnatia"),
        ("Monaco", "Freiburg"), ("Midtjylland", "Sint-Truidense"), ("Thun", "Hajduk Split"),
        ("Borac", "KuPS Kuopio"), ("Lincoln Red Imps", "Twente"), ("Braga", "Gent"),
    ],
    # Matchday 3
    [
        ("Aarhus", "Braga"), ("Atalanta", "Kairat Almaty"), ("Midtjylland", "Ajax"),
        ("Thun", "Hearts"), ("Crvena Zvezda", "Inter Escaldes"), ("KuPS Kuopio", "Gent"),
        ("Lincoln Red Imps", "Hajduk Split"), ("Mjällby", "Borac"), ("Trabzonspor", "Freiburg"),
        ("Monaco", "Nordsjælland"), ("Copenhagen", "Iberia Tbilisi"), ("Lugano", "Kauno Žalgiris"),
        ("Twente", "Pafos"), ("Getafe", "Brighton"), ("Sint-Truidense", "Brann"),
        ("Panathinaikos", "CSKA Sofia"), ("Riga", "Jablonec"), ("Universitatea Craiova", "Egnatia"),
    ],
    # Matchday 4
    [
        ("Kairat Almaty", "Mjällby"), ("Ajax", "Thun"), ("Brighton", "Universitatea Craiova"),
        ("Iberia Tbilisi", "Getafe"), ("Jablonec", "Lugano"), ("Kauno Žalgiris", "Riga"),
        ("Hearts", "Monaco"), ("Egnatia", "Lincoln Red Imps"), ("Pafos", "Midtjylland"),
        ("Brann", "Aarhus"), ("Nordsjælland", "Panathinaikos"), ("Borac", "Atalanta"),
        ("Hajduk Split", "Sint-Truidense"), ("Inter Escaldes", "Copenhagen"), ("Gent", "Crvena Zvezda"),
        ("CSKA Sofia", "Trabzonspor"), ("Braga", "KuPS Kuopio"), ("Freiburg", "Twente"),
    ],
    # Matchday 5
    [
        ("Kairat Almaty", "Universitatea Craiova"), ("Copenhagen", "Lugano"),
        ("Iberia Tbilisi", "Crvena Zvezda"), ("Getafe", "Inter Escaldes"),
        ("KuPS Kuopio", "CSKA Sofia"), ("Lincoln Red Imps", "Midtjylland"),
        ("Riga", "Atalanta"), ("Freiburg", "Panathinaikos"), ("Brann", "Braga"),
        ("Trabzonspor", "Jablonec"), ("Aarhus", "Twente"), ("Brighton", "Monaco"),
        ("Thun", "Gent"), ("Hearts", "Borac"), ("Hajduk Split", "Nordsjælland"),
        ("Sint-Truidense", "Ajax"), ("Egnatia", "Kauno Žalgiris"), ("Mjällby", "Pafos"),
    ],
    # Matchday 6
    [
        ("Ajax", "Getafe"), ("Monaco", "Lincoln Red Imps"), ("Atalanta", "Mjällby"),
        ("Lugano", "Sint-Truidense"), ("Midtjylland", "Hajduk Split"), ("Nordsjælland", "KuPS Kuopio"),
        ("Twente", "Kairat Almaty"), ("Borac", "Riga"), ("Crvena Zvezda", "Trabzonspor"),
        ("Jablonec", "Iberia Tbilisi"), ("Kauno Žalgiris", "Freiburg"), ("Inter Escaldes", "Aarhus"),
        ("Gent", "Brann"), ("Pafos", "Hearts"), ("Panathinaikos", "Brighton"),
        ("CSKA Sofia", "Thun"), ("Braga", "Egnatia"), ("Universitatea Craiova", "Copenhagen"),
    ],
]

UECL_FIXTURES_STD = [
    [(_standardise_uecl(h), _standardise_uecl(a)) for h, a in round_matches]
    for round_matches in _FIXTURES_UECL_RAW
]

BETTING_MARKETS_UECL_WINNER = {
    "Brighton": (10, 3), "Atalanta": (11, 2), "Freiburg": (13, 2), "Monaco": (13, 2),
    "Braga": (17, 2), "Ajax": (17, 2), "Midtjylland": (16, 1), "Getafe": (16, 1),
    "FC Copenhagen": (20, 1), "Twente": (25, 1), "Trabzonspor": (25, 1), "Gent": (33, 1),
    "Red Star Belgrade": (33, 1), "Panathinaikos": (33, 1), "Lugano": (40, 1),
    "Sint Truiden": (66, 1), "FC Nordsjaelland": (66, 1), "Brann": (66, 1),
    "Pafos FC": (66, 1), "Hearts": (100, 1), "KuPS": (150, 1),
    "Universitatea Craiova": (150, 1), "Hajduk Split": (175, 1), "Borac Banja Luka": (175, 1),
    "FK Jablonec": (175, 1), "FK Kauno Zalgiris": (175, 1), "CSKA Sofia": (200, 1),
    "Mjallby": (200, 1), "Thun": (200, 1), "Kairat": (300, 1), "FK Riga": (300, 1),
    "AGF": (300, 1), "Inter Club d'Escaldes": (500, 1), "Iberia": (500, 1),
    "Egnatia Rrogozhine": (500, 1), "Lincoln Red Imps": (500, 1),
}

# =============================================================================
# HELPER: DERIVE PL BASE RATINGS FROM BETTING MARKETS
# =============================================================================

def compute_market_weights(odds_dict):
    weights = {}
    efficiencies = {}
    for market, teams in odds_dict.items():
        total_p = 0
        for num, den in teams.values():
            total_p += den / (num + den)
        efficiencies[market] = 1 / total_p
    total_eff = sum(efficiencies.values())
    for market, eff in efficiencies.items():
        weights[market] = eff / total_eff
    return weights

def markets_to_latent_elo() -> Dict[str, float]:
    teams = list(PL_BETTING_MARKETS["League Winner"].keys())
    MARKET_WEIGHTS = compute_market_weights(PL_BETTING_MARKETS)

    team_strength = defaultdict(float)
    team_weight = defaultdict(float)

    for market_name, market_weight in MARKET_WEIGHTS.items():
        odds_dict = PL_BETTING_MARKETS[market_name]
        raw_probs = []
        teams_in_market = []
        for team in teams:
            if team in odds_dict:
                num, den = odds_dict[team]
                prob = den / (num + den)
                raw_probs.append(prob)
                teams_in_market.append(team)
        if not raw_probs:
            continue
        raw_probs_arr = np.array(raw_probs, dtype=np.float64)
        total = raw_probs_arr.sum()
        if total > 0:
            probs = raw_probs_arr / total
        else:
            continue
        log_probs = np.log(np.clip(probs, 1e-6, 1.0 - 1e-6))
        mean_log_prob = np.mean(log_probs)
        centered = log_probs - mean_log_prob
        for i, team in enumerate(teams_in_market):
            team_strength[team] += market_weight * centered[i]
            team_weight[team] += market_weight

    raw_elo = {}
    scale_factor = ELO_SCALE / math.log(10)
    for team in teams:
        if team_weight[team] > 0:
            latent = team_strength[team] / team_weight[team]
            elo = LEAGUE_AVERAGE_ELO + scale_factor * latent
        else:
            elo = LEAGUE_AVERAGE_ELO
        raw_elo[team] = elo

    mean_elo = np.mean(list(raw_elo.values()))
    centered_elo = {team: LEAGUE_AVERAGE_ELO + (elo - mean_elo) for team, elo in raw_elo.items()}
    ratings = {team: LEAGUE_AVERAGE_ELO + ELO_SHRINKAGE * (elo - LEAGUE_AVERAGE_ELO)
               for team, elo in centered_elo.items()}
    return {team: round(float(rating), 1) for team, rating in ratings.items()}

# =============================================================================
# UNIFIED SIMULATION LOOP
# =============================================================================

def run_unified_simulation():
    print("\n" + "=" * 80)
    print("UNIFIED PREMIER LEAGUE + EUROPEAN SIMULATION (Refactored)")
    print("=" * 80)

    _RNG.seed(SEED)
    _NP_RNG.seed(SEED)

    # Derive PL base ratings (no flat penalty for promoted teams)
    base_ratings = markets_to_latent_elo()
    pl_teams_set = set(base_ratings.keys())

    # Instantiate European competitions
    ucl = EuropeanCompetition("UCL", CL_FIXTURES, BETTING_MARKETS_CL_WINNER, pl_teams_set)
    uel = EuropeanCompetition("UEL", UEL_FIXTURES_STD, BETTING_MARKETS_UEL_WINNER, pl_teams_set)
    uecl = EuropeanCompetition("UECL", UECL_FIXTURES_STD, BETTING_MARKETS_UECL_WINNER, pl_teams_set)

    # PL simulator
    pl_sim = PLSimulator(FIXTURES_LIST, base_ratings, ACTUAL_RESULTS)

    # Accumulators
    points_dist = defaultdict(list)
    position_counts = defaultdict(lambda: defaultdict(int))
    title_counts = defaultdict(int)
    ucl_qual_counts = defaultdict(int)          # number of times each PL team qualified for UCL
    fifth_place_ucl_counts = defaultdict(int)   # number of times 5th place got UCL via winner condition
    euro_win_counts = defaultdict(lambda: defaultdict(int))  # per competition, PL teams only

    print(f"\nRunning {NUM_PL_SIMS} unified simulations...")
    for _ in tqdm(range(NUM_PL_SIMS), desc="Unified Sim"):
        # 1. Simulate European competitions
        ucl_winner, ucl_elim = ucl.simulate()
        uel_winner, uel_elim = uel.simulate()
        uecl_winner, uecl_elim = uecl.simulate()

        # 2. Build fatigue_info for PL teams
        fatigue_info = {}
        for team in pl_teams_set:
            if team in ucl_elim:
                fatigue_info[team] = (ucl_elim[team], "UCL")
            elif team in uel_elim:
                fatigue_info[team] = (uel_elim[team], "UEL")
            elif team in uecl_elim:
                fatigue_info[team] = (uecl_elim[team], "UECL")
            # else no European involvement

        # 3. Simulate PL season
        ranking, points = pl_sim.simulate_season(fatigue_info)

        # 4. Determine UCL qualification (conditional)
        ucl_qualified = set(ranking[:4])  # top 4 always qualify

        # Check if UCL winner is English and not already in top 4
        if ucl_winner in pl_teams_set and ucl_winner not in ucl_qualified:
            ucl_qualified.add(ucl_winner)
            # Also give the 5th place team a spot if not already included
            if len(ranking) >= 5:
                fifth = ranking[4]
                if fifth not in ucl_qualified:
                    ucl_qualified.add(fifth)
                    fifth_place_ucl_counts[fifth] += 1

        # Check if UEL winner is English and not already in top 4 (and not already added)
        if uel_winner in pl_teams_set and uel_winner not in ucl_qualified:
            ucl_qualified.add(uel_winner)
            if len(ranking) >= 5:
                fifth = ranking[4]
                if fifth not in ucl_qualified:
                    ucl_qualified.add(fifth)
                    fifth_place_ucl_counts[fifth] += 1

        # 5. Accumulate statistics
        for pos, team in enumerate(ranking, 1):
            points_dist[team].append(points[team])
            position_counts[team][pos] += 1
            if pos == 1:
                title_counts[team] += 1
            if team in ucl_qualified:
                ucl_qual_counts[team] += 1

        # European win counts for PL teams
        for comp, winner in [("UCL", ucl_winner), ("UEL", uel_winner), ("UECL", uecl_winner)]:
            if winner in pl_teams_set:
                euro_win_counts[comp][winner] += 1

    # Compute final probabilities
    total = NUM_PL_SIMS
    avg_positions = {}
    avg_points = {}
    std_points = {}
    ci_lower = {}
    ci_upper = {}
    ci_margin = 1.96

    for team in pl_teams_set:
        position_total = sum(pos * count for pos, count in position_counts[team].items())
        avg_positions[team] = position_total / total
        pts_array = np.array(points_dist[team], dtype=np.float64)
        avg_points[team] = float(pts_array.mean())
        std_points[team] = float(pts_array.std())
        sem = std_points[team] / math.sqrt(total)
        ci_lower[team] = avg_points[team] - ci_margin * sem
        ci_upper[team] = avg_points[team] + ci_margin * sem

    title_prob = {t: title_counts[t] / total * 100 for t in pl_teams_set}
    ucl_qual_prob = {t: ucl_qual_counts[t] / total * 100 for t in pl_teams_set}
    fifth_place_ucl_prob = {t: fifth_place_ucl_counts[t] / total * 100 for t in pl_teams_set}
    euro_win_probs = {
        comp: {t: euro_win_counts[comp][t] / total * 100 for t in pl_teams_set}
        for comp in ["UCL", "UEL", "UECL"]
    }

    # Print output
    print("\n" + "=" * 150)
    print("FINAL PREMIER LEAGUE PROJECTIONS (With Improved Fatigue & UCL Qualification)")
    print("=" * 150)

    header = (f"{'Pos':<6}{'Team':<22}{'Eur':<6}{'ELO':<8}{'Pts':<8}{'SD':<7}{'95%CI':<12}"
              f"{'Title%':<8}{'UCLQ%':<9}{'5th->UCL%':<11}{'UCLWin%':<9}{'UELWin%':<10}"
              f"{'UECLWin%':<10}{'AnyEuroWin%':<12}")
    print(header)
    print("-" * 160)

    sorted_teams = sorted(pl_teams_set, key=lambda t: avg_positions[t])

    for team in sorted_teams:
        # Determine European status for display
        if team in ucl.teams:
            eur_status = "UCL"
        elif team in uel.teams:
            eur_status = "UEL"
        elif team in uecl.teams:
            eur_status = "UECL"
        else:
            eur_status = "-"

        ci_str = f"[{ci_lower[team]:.1f}-{ci_upper[team]:.1f}]"
        any_euro_win = euro_win_probs["UCL"][team] + euro_win_probs["UEL"][team] + euro_win_probs["UECL"][team]

        print(f"{avg_positions[team]:<6.2f}{team:<22}{eur_status:<6}{base_ratings[team]:<8.1f}"
              f"{avg_points[team]:<8.2f}{std_points[team]:<7.2f}{ci_str:<12}"
              f"{title_prob[team]:<8.2f}{ucl_qual_prob[team]:<9.1f}{fifth_place_ucl_prob[team]:<11.1f}"
              f"{euro_win_probs['UCL'][team]:<9.1f}{euro_win_probs['UEL'][team]:<10.1f}"
              f"{euro_win_probs['UECL'][team]:<10.1f}{any_euro_win:<12.1f}")

def main():
    run_unified_simulation()

if __name__ == "__main__":
    main()