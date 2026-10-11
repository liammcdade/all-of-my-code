"""
Combined Premier League 2026/27 + European Competitions + Carabao Cup simulation.

Elo ratings are built PURELY from ACTUAL_RESULTS for Premier League teams
(no betting markets). All PL teams start at LEAGUE_AVERAGE_ELO (1500) and are
updated walk-forward through the actual PL scorelines. Non-PL teams in
European competitions default to LEAGUE_AVERAGE_ELO.

Carabao Cup still uses its own hardcoded Elo table.

The PL league phase and the European league phases are now fully vectorised
with NumPy, which makes the whole simulation dramatically faster.
"""

import logging
import math
from collections import defaultdict
from typing import Dict, List, Tuple, Optional, Set, Any
import random
import numpy as np

logger = logging.getLogger(__name__)

# =============================================================================
# GLOBAL CONSTANTS
# =============================================================================

HOME_ADVANTAGE_ELO = 70.0
ELO_SCALE = 400.0
LEAGUE_AVERAGE_ELO = 1500.0

ELO_K = 24.0
PL_TOTAL_MATCHES = 38

MAX_GOALS = 10
NUM_PL_SIMS = 2000
SEED = 42

BASE_HOME_XG = 1.5
BASE_AWAY_XG = 1.2
XG_ELO_SENSITIVITY = 0.002
EXTRA_TIME_XG_FACTOR = 0.5

EUROPEAN_FATIGUE_BASE = {"UCL": 8.0, "UEL": 6.0, "UECL": 5.0}

_FACTORIALS = np.array([math.factorial(i) for i in range(MAX_GOALS + 1)], dtype=np.float64)
_POISSON_CACHE: Dict[int, np.ndarray] = {}
_LAMBDA_ROUND_PRECISION = 100

_RNG = random.Random(SEED)
_NP_RNG = np.random.RandomState(SEED)

# =============================================================================
# COMMON HELPERS
# =============================================================================

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
    elo_h1 = elos.get(team1, LEAGUE_AVERAGE_ELO) + HOME_ADVANTAGE_ELO
    elo_a1 = elos.get(team2, LEAGUE_AVERAGE_ELO)
    xg_h1, xg_a1 = compute_expected_goals(elo_h1, elo_a1)
    goals_h1, goals_a1 = sample_score(xg_h1, xg_a1)

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

    diff = elos.get(team1, LEAGUE_AVERAGE_ELO) - elos.get(team2, LEAGUE_AVERAGE_ELO)
    p1 = 1 / (1 + 10 ** (-diff / ELO_SCALE))
    return team1 if _RNG.random() < p1 else team2

def simulate_knockout_phase(qualified: List[str], elos: Dict[str, float]) -> Tuple[Optional[str], Dict[str, int]]:
    top8 = qualified[:8]
    playoff = qualified[8:24]
    all_teams = set(qualified)
    elimination_round = {team: -1 for team in all_teams}

    winners = []
    n = len(playoff) // 2
    for i in range(n):
        winners.append(simulate_two_legged_tie(playoff[i], playoff[len(playoff) - 1 - i], elos))
    for team in playoff:
        if team not in winners:
            elimination_round[team] = 0

    current = top8 + winners

    r16 = []
    n = len(current) // 2
    for i in range(n):
        r16.append(simulate_two_legged_tie(current[i], current[len(current) - 1 - i], elos))
    for team in current:
        if team not in r16:
            elimination_round[team] = 1
    current = r16

    qf = []
    n = len(current) // 2
    for i in range(n):
        qf.append(simulate_two_legged_tie(current[i], current[len(current) - 1 - i], elos))
    for team in current:
        if team not in qf:
            elimination_round[team] = 2
    current = qf

    sf = []
    n = len(current) // 2
    for i in range(n):
        sf.append(simulate_two_legged_tie(current[i], current[len(current) - 1 - i], elos))
    for team in current:
        if team not in sf:
            elimination_round[team] = 3
    current = sf

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
        return current[0] if current else None, elimination_round

# =============================================================================
# EUROPEAN COMPETITION  (vectorised league phase)
# =============================================================================

class EuropeanCompetition:
    """
    European competition Elo is taken directly from the PL results-only Elo
    for PL teams; all other teams default to LEAGUE_AVERAGE_ELO.
    """

    def __init__(self, name: str, fixtures: List[List[Tuple[str, str]]],
                 pl_elos: Dict[str, float], pl_teams: Set[str],
                 actual_results: Optional[Dict[Tuple[str, str], Tuple[int, int]]] = None):
        self.name = name
        self.fixtures = fixtures
        self.pl_elos = pl_elos
        self.pl_teams = pl_teams
        self.actual_results = actual_results or {}
        self.teams = sorted({t for rnd in fixtures for pair in rnd for t in pair})
        self.elos = self._calculate_elos()

        # ---- precompute everything we can ----
        self.team_to_idx = {t: i for i, t in enumerate(self.teams)}
        n = len(self.teams)

        flat = [(h, a) for rnd in fixtures for h, a in rnd]
        self.n_fixtures = len(flat)

        h_idx = np.empty(self.n_fixtures, dtype=np.int64)
        a_idx = np.empty(self.n_fixtures, dtype=np.int64)
        for i, (h, a) in enumerate(flat):
            h_idx[i] = self.team_to_idx[h]
            a_idx[i] = self.team_to_idx[a]
        self.fixture_h_idx = h_idx
        self.fixture_a_idx = a_idx

        # Note: the original code adds HOME_ADVANTAGE_ELO to every team in
        # elo_arr, which cancels out in the diff.  We preserve that behaviour.
        elo_arr = np.array([self.elos[t] for t in self.teams], dtype=np.float64)
        elo_arr += HOME_ADVANTAGE_ELO
        diff = elo_arr[h_idx] - elo_arr[a_idx]

        self.lam_h_pre = BASE_HOME_XG * np.exp(XG_ELO_SENSITIVITY * diff)
        self.lam_a_pre = BASE_AWAY_XG * np.exp(-XG_ELO_SENSITIVITY * diff)

        # Actual-result overrides
        actual_hg = np.zeros(self.n_fixtures, dtype=np.int64)
        actual_ag = np.zeros(self.n_fixtures, dtype=np.int64)
        actual_mask = np.zeros(self.n_fixtures, dtype=bool)
        for i, (h, a) in enumerate(flat):
            key = (h, a)
            if key in self.actual_results:
                actual_hg[i], actual_ag[i] = self.actual_results[key]
                actual_mask[i] = True
        self.actual_hg = actual_hg
        self.actual_ag = actual_ag
        self.actual_mask = actual_mask
        self._has_actual = bool(actual_mask.any())

    def _calculate_elos(self) -> Dict[str, float]:
        elos = {}
        for team in self.teams:
            if team in self.pl_teams and team in self.pl_elos:
                elos[team] = self.pl_elos[team]
            else:
                elos[team] = LEAGUE_AVERAGE_ELO
        return elos

    def run_single_league_phase(self) -> List[str]:
        n = len(self.teams)

        hg = _NP_RNG.poisson(self.lam_h_pre)
        ag = _NP_RNG.poisson(self.lam_a_pre)
        np.minimum(hg, MAX_GOALS, out=hg)
        np.minimum(ag, MAX_GOALS, out=ag)

        if self._has_actual:
            hg[self.actual_mask] = self.actual_hg[self.actual_mask]
            ag[self.actual_mask] = self.actual_ag[self.actual_mask]

        home_win = hg > ag
        away_win = ag > hg
        draw = ~(home_win | away_win)

        pts_h = np.where(home_win, 3, np.where(draw, 1, 0)).astype(np.float64)
        pts_a = np.where(away_win, 3, np.where(draw, 1, 0)).astype(np.float64)

        pts = (np.bincount(self.fixture_h_idx, weights=pts_h, minlength=n).astype(np.int64)
               + np.bincount(self.fixture_a_idx, weights=pts_a, minlength=n).astype(np.int64))

        gf = (np.bincount(self.fixture_h_idx, weights=hg.astype(np.float64), minlength=n).astype(np.int64)
              + np.bincount(self.fixture_a_idx, weights=ag.astype(np.float64), minlength=n).astype(np.int64))

        ga = (np.bincount(self.fixture_h_idx, weights=ag.astype(np.float64), minlength=n).astype(np.int64)
              + np.bincount(self.fixture_a_idx, weights=hg.astype(np.float64), minlength=n).astype(np.int64))

        gd = gf - ga
        tiebreak = _NP_RNG.uniform(0, 0.0001, size=n)
        # lexsort uses last key as primary; reverse for descending
        order = np.lexsort((-tiebreak, gf, gd, pts))[::-1]
        return [self.teams[i] for i in order]

    def simulate(self) -> Tuple[Optional[str], Dict[str, int]]:
        ranking = self.run_single_league_phase()
        qualified = ranking[:24]
        winner, elim_rounds = simulate_knockout_phase(qualified, self.elos)
        for team in self.teams:
            if team not in elim_rounds:
                elim_rounds[team] = -1
        return winner, elim_rounds

# =============================================================================
# PL RATINGS: PURE RESULTS-BASED ELO
# =============================================================================

def build_current_pl_ratings(
    actual_results: Dict[Tuple[str, str], Tuple[int, int]],
    pl_teams: Set[str],
) -> Dict[str, float]:
    """
    Build Premier League Elo ratings purely from ACTUAL_RESULTS.
    No betting odds, no mean reversion.
    """
    ratings = {team: LEAGUE_AVERAGE_ELO for team in pl_teams}

    for (home, away), (hg, ag) in actual_results.items():
        if home not in ratings or away not in ratings:
            continue

        rh = ratings[home]
        ra = ratings[away]

        exp_h = 1.0 / (1.0 + 10.0 ** ((ra - (rh + HOME_ADVANTAGE_ELO)) / ELO_SCALE))
        exp_a = 1.0 - exp_h

        if hg > ag:
            sh, sa = 1.0, 0.0
        elif hg < ag:
            sh, sa = 0.0, 1.0
        else:
            sh = sa = 0.5

        ratings[home] = rh + ELO_K * (sh - exp_h)
        ratings[away] = ra + ELO_K * (sa - exp_a)

    return {team: round(rating, 1) for team, rating in ratings.items()}

def ensure_full_pl_fixtures(fixtures: List[Tuple[str, str]]) -> List[Tuple[str, str]]:
    teams = sorted({t for h, a in fixtures for t in (h, a)})
    fixture_set = set(fixtures)
    full = list(fixtures)

    for h in teams:
        for a in teams:
            if h == a:
                continue
            if (h, a) not in fixture_set:
                full.append((h, a))
                fixture_set.add((h, a))

    counts = defaultdict(int)
    for h, a in full:
        counts[h] += 1
        counts[a] += 1

    bad = {t: c for t, c in counts.items() if c != 38}
    if bad:
        print(f"Warning: fixture counts are not 38 for: {bad}")

    return full

# =============================================================================
# PREMIER LEAGUE SIMULATOR  (vectorised season)
# =============================================================================

class PLSimulator:
    def __init__(self, fixtures: List[Tuple[str, str]],
                 current_ratings: Dict[str, float],
                 actual_results: Dict[Tuple[str, str], Tuple[int, int]]):
        self.fixtures = fixtures
        self.current_ratings = current_ratings
        self.actual_results = actual_results

        self.teams = sorted({team for pair in fixtures for team in pair})
        self.team_to_idx = {team: i for i, team in enumerate(self.teams)}
        self.idx_to_team = self.teams
        self.n_teams = len(self.teams)
        self.n_fixtures = len(fixtures)

        # Precompute fixture indices
        h_idx = np.empty(self.n_fixtures, dtype=np.int64)
        a_idx = np.empty(self.n_fixtures, dtype=np.int64)
        for i, (h, a) in enumerate(fixtures):
            h_idx[i] = self.team_to_idx[h]
            a_idx[i] = self.team_to_idx[a]
        self.home_idx_arr = h_idx
        self.away_idx_arr = a_idx

        # Ratings as numpy array
        self.ratings_arr = np.array(
            [current_ratings.get(t, LEAGUE_AVERAGE_ELO) for t in self.teams],
            dtype=np.float64,
        )

        # Progress / inverse progress for fatigue decay
        if self.n_fixtures > 1:
            self.inv_progress_arr = 1.0 - (
                np.arange(self.n_fixtures, dtype=np.float64) / (self.n_fixtures - 1)
            )
        else:
            self.inv_progress_arr = np.ones(self.n_fixtures, dtype=np.float64)

        # Actual results as arrays
        actual_hg = np.zeros(self.n_fixtures, dtype=np.int64)
        actual_ag = np.zeros(self.n_fixtures, dtype=np.int64)
        actual_mask = np.zeros(self.n_fixtures, dtype=bool)
        for i, (h, a) in enumerate(fixtures):
            key = (h, a)
            if key in actual_results:
                actual_hg[i], actual_ag[i] = actual_results[key]
                actual_mask[i] = True
        self.actual_hg = actual_hg
        self.actual_ag = actual_ag
        self.actual_mask = actual_mask
        self._has_actual = bool(actual_mask.any())

        # Base Elo diff (without fatigue), precomputed once
        self.base_diff = (
            self.ratings_arr[self.home_idx_arr]
            - self.ratings_arr[self.away_idx_arr]
            + HOME_ADVANTAGE_ELO
        )

    def simulate_season(self, fatigue_info: Dict[str, Tuple[int, str]]) -> Tuple[List[str], Dict[str, int]]:
        n = self.n_teams

        # Per-team fatigue arrays
        fatigue_base_arr = np.zeros(n, dtype=np.float64)
        active_arr = np.zeros(n, dtype=bool)
        for team, (elim_round, comp) in fatigue_info.items():
            idx = self.team_to_idx.get(team)
            if idx is None:
                continue
            fatigue_base_arr[idx] = EUROPEAN_FATIGUE_BASE.get(comp, 0.0)
            if elim_round >= 0:
                active_arr[idx] = True

        h_active = active_arr[self.home_idx_arr]
        a_active = active_arr[self.away_idx_arr]

        h_fatigue = np.where(
            h_active,
            fatigue_base_arr[self.home_idx_arr] * self.inv_progress_arr,
            0.0,
        )
        a_fatigue = np.where(
            a_active,
            fatigue_base_arr[self.away_idx_arr] * self.inv_progress_arr,
            0.0,
        )

        diff = self.base_diff - h_fatigue + a_fatigue

        lam_h = BASE_HOME_XG * np.exp(XG_ELO_SENSITIVITY * diff)
        lam_a = BASE_AWAY_XG * np.exp(-XG_ELO_SENSITIVITY * diff)

        hg = _NP_RNG.poisson(lam_h)
        ag = _NP_RNG.poisson(lam_a)
        np.minimum(hg, MAX_GOALS, out=hg)
        np.minimum(ag, MAX_GOALS, out=ag)

        if self._has_actual:
            hg[self.actual_mask] = self.actual_hg[self.actual_mask]
            ag[self.actual_mask] = self.actual_ag[self.actual_mask]

        home_win = hg > ag
        away_win = ag > hg
        draw = ~(home_win | away_win)

        pts_h = np.where(home_win, 3, np.where(draw, 1, 0)).astype(np.float64)
        pts_a = np.where(away_win, 3, np.where(draw, 1, 0)).astype(np.float64)

        pts = (np.bincount(self.home_idx_arr, weights=pts_h, minlength=n).astype(np.int64)
               + np.bincount(self.away_idx_arr, weights=pts_a, minlength=n).astype(np.int64))

        gf = (np.bincount(self.home_idx_arr, weights=hg.astype(np.float64), minlength=n).astype(np.int64)
              + np.bincount(self.away_idx_arr, weights=ag.astype(np.float64), minlength=n).astype(np.int64))

        ga = (np.bincount(self.home_idx_arr, weights=ag.astype(np.float64), minlength=n).astype(np.int64)
              + np.bincount(self.away_idx_arr, weights=hg.astype(np.float64), minlength=n).astype(np.int64))

        gd = gf - ga
        tiebreak = _NP_RNG.uniform(0, 0.0001, size=n)
        order = np.lexsort((-tiebreak, gf, gd, pts))[::-1]

        ranked_teams = [self.idx_to_team[i] for i in order]
        points_dict = {self.idx_to_team[i]: int(pts[i]) for i in range(n)}
        return ranked_teams, points_dict

# =============================================================================
# EUROPEAN SPOT ALLOCATION WITH CASCADE
# =============================================================================

def allocate_european_spots(
    ranking: List[str],
    carabao_winner: str,
    pl_teams: Set[str],
    ucl_winner: Optional[str] = None,
    uel_winner: Optional[str] = None,
    uecl_winner: Optional[str] = None,
    extra_ucl_spots: int = 0,
) -> Dict[str, Set[str]]:
    ucl = set(ranking[:4])

    if extra_ucl_spots:
        for team in ranking[4:4 + extra_ucl_spots]:
            if team not in ucl:
                ucl.add(team)

    if ucl_winner in pl_teams and ucl_winner not in ucl:
        ucl.add(ucl_winner)
    if uel_winner in pl_teams and uel_winner not in ucl:
        ucl.add(uel_winner)

    uel = set()

    for team in ranking[4:]:
        if team not in ucl:
            uel.add(team)
            break

    if uecl_winner in pl_teams and uecl_winner not in ucl and uecl_winner not in uel:
        uel.add(uecl_winner)

    uecl = set()

    if carabao_winner in pl_teams and carabao_winner not in ucl and carabao_winner not in uel:
        uecl.add(carabao_winner)
    else:
        for team in ranking:
            if team not in ucl and team not in uel and team not in uecl:
                uecl.add(team)
                break

    return {"UCL": ucl, "UEL": uel, "UECL": uecl}

# =============================================================================
# CARABAO CUP SIMULATION (integrated)
# =============================================================================

carabao_elo_ratings = {
    "Man City": 2010.7836367639238, "Arsenal": 1989.3611057333628,
    "Liverpool": 1860.7279670985145, "Man United": 1850.8891970173254,
    "Brighton": 1841.0211575935816, "Bournemouth": 1824.0609850918595,
    "Brentford": 1821.5243401977068, "Aston Villa": 1786.127671831527,
    "Leeds": 1775.3342197987322, "Everton": 1767.6484544799212,
    "Newcastle": 1764.9138653134823, "Chelsea": 1762.583783993479,
    "Nott'm Forest": 1747.7984777256838, "Fulham": 1711.9018852380646,
    "Crystal Palace": 1699.5569009945032, "West Ham": 1681.5692755637274,
    "Sunderland": 1672.8181922794574, "Tottenham": 1639.3816342781274,
    "Wolves": 1547.9475992242556, "Ipswich": 1532.5831519737835,
    "Coventry": 1504.3809028862806, "Burnley": 1500.9217078231452,
    "Southampton": 1447.6563255960123, "Hull": 1436.602469710685,
    "Lincoln": 1417.8185712259785, "Millwall": 1395.4777264514241,
    "Middlesbrough": 1350.2234625213373, "Norwich": 1334.1518789628956,
    "Wrexham": 1327.6505571747773, "Derby": 1304.6505604221713,
    "Swansea": 1304.5265381809784, "Birmingham": 1304.1358066488485,
    "Cardiff": 1303.6074095037484, "Sheffield United": 1286.6149271597833,
    "Plymouth": 1275.6565204656315, "Luton": 1273.998562783496,
    "Portsmouth": 1261.4982564324473, "Stockport": 1256.6657496463106,
    "Bolton": 1250.5291959079238, "Bristol City": 1247.496621117459,
    "Blackburn": 1236.4502820647497, "West Brom": 1233.4181670128185,
    "Mansfield": 1230.4205520583453, "Leicester": 1228.5432051115192,
    "Stevenage": 1221.0605594655588, "Milton Keynes Dons": 1218.284411630823,
    "Bromley": 1217.8090646204216, "Bradford": 1213.6029718526481,
    "QPR": 1212.8887412208367, "Preston": 1212.7451552629345,
    "Charlton": 1207.2216735987472, "Oxford": 1197.4328769980957,
    "Cambridge": 1197.0425123612229, "Wycombe": 1195.170639123425,
    "Chesterfield": 1193.1123525684566, "Blackpool": 1192.8340257602906,
    "Huddersfield": 1190.2318512622132, "Reading": 1186.2473475007585,
    "Watford": 1185.3055164175332, "Grimsby": 1181.0298872693552,
    "Salford": 1174.9622003277593, "Barnet": 1174.093806044488,
    "Stoke": 1167.1772717066501, "Doncaster": 1165.6987476475947,
    "Notts County": 1161.5672800815744, "Bury": 1150.2025934752996,
    "Wigan": 1139.4908831553203, "Burton": 1132.1021596493315,
    "Barnsley": 1128.175953658714, "Leyton Orient": 1121.873228643075,
    "Swindon": 1115.8737617595834, "Colchester": 1114.3899557534487,
    "Bristol Rvs": 1107.0769802556172, "Oldham": 1105.142695211731,
    "Port Vale": 1100.9617836837888, "Peterboro": 1095.2031553596712,
    "Exeter": 1092.601831334788, "Wimbledon": 1090.0873060346191,
    "Kidderminster": 1088.4040827224283, "Crewe": 1086.7678170767635,
    "Fleetwood Town": 1078.006687370749, "AFC Wimbledon": 1066.2836822296788,
    "Walsall": 1055.9740039532194, "Rotherham": 1038.8180537371202,
    "Aldershot": 1028.0711340564974, "Sutton": 1024.153951117176,
    "Sheffield Weds": 1023.0331018110688, "Scarborough": 1021.0215515684511,
    "Cheltenham": 1020.1317567750524, "Hereford": 1018.2144177180269,
    "Southend": 1015.7681099281735, "Accrington": 1000.2484328619208,
    "Gillingham": 999.9154533450713, "Hartlepool": 996.0150027099122,
    "Carlisle": 994.4381977078381, "Crawley Town": 994.0393658529027,
    "Shrewsbury": 993.945127351084, "Torquay": 991.0809360931482,
    "Rochdale": 985.9930267575577, "Newport County": 981.8853419911738,
    "Boston": 980.8713456843165, "Rushden & D": 979.6498467696737,
    "Macclesfield": 979.0637709111596, "Forest Green": 979.0550230154435,
    "Harrogate": 976.2396044856182, "Northampton": 959.8689781377024,
    "York": 955.7216475475888, "Dag and Red": 948.8543031624317,
    "Halifax": 945.0602120106844, "Darlington": 944.045409328075,
    "Tranmere": 942.6429782827647, "Barrow": 933.5254193209282,
    "Morecambe": 931.2309537577223, "Yeovil": 924.1398432835155,
    "Chester": 917.062405028551, "Scunthorpe": 847.0195044912501
}

carabao_name_mapping = {
    "Bradford City": "Bradford",
    "Peterborough United": "Peterboro",
    "Manchester City": "Man City",
    "Brighton & Hove Albion": "Brighton",
    "Newcastle United": "Newcastle",
    "Forest": "Nott'm Forest",
}

def get_carabao_elo(team_name):
    csv_name = carabao_name_mapping.get(team_name, team_name)
    return carabao_elo_ratings.get(csv_name, 1500.0)

def simulate_carabao_match(team_a, team_b):
    elo_a = get_carabao_elo(team_a)
    elo_b = get_carabao_elo(team_b)
    exp_a = 1 / (1 + 10 ** ((elo_b - elo_a) / 400))
    if _RNG.random() < exp_a:
        return team_a
    else:
        return team_b

carabao_round_4_fixtures = [
    ("Bradford City", "Peterborough United"),
    ("Fleetwood Town", "Arsenal"),
    ("Manchester City", "Brighton & Hove Albion"),
    ("Bournemouth", "Aston Villa"),
    ("Fulham", "Crystal Palace"),
    ("Sunderland", "Brentford"),
    ("Liverpool", "Chelsea"),
    ("Everton", "Newcastle United")
]

def run_single_carabao_tournament():
    quarter_finalists = []
    for team_a, team_b in carabao_round_4_fixtures:
        winner = simulate_carabao_match(team_a, team_b)
        quarter_finalists.append(winner)

    _RNG.shuffle(quarter_finalists)
    semi_finalists = []
    for i in range(0, len(quarter_finalists), 2):
        winner = simulate_carabao_match(quarter_finalists[i], quarter_finalists[i+1])
        semi_finalists.append(winner)

    _RNG.shuffle(semi_finalists)
    finalists = []
    for i in range(0, len(semi_finalists), 2):
        winner = simulate_carabao_match(semi_finalists[i], semi_finalists[i+1])
        finalists.append(winner)

    winner = simulate_carabao_match(finalists[0], finalists[1])
    return winner

# =============================================================================
# DATA – PREMIER LEAGUE FIXTURES, ACTUAL RESULTS
# =============================================================================

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

ACTUAL_RESULTS = {
    ("Arsenal", "Coventry"): (3, 0),
    ("Hull", "Man United"): (2, 0),
    ("Everton", "Crystal Palace"): (2, 0),
    ("Ipswich", "Sunderland"): (2, 1),
    ("Forest", "Leeds"): (0, 1),
    ("Brentford", "Tottenham"): (3, 0),
    ("Brighton", "Aston Villa"): (4, 0),
    ("Man City", "Bournemouth"): (2, 1),
    ("Newcastle", "Liverpool"): (2, 2),
    ("Fulham", "Chelsea"): (2, 3),
    ("Crystal Palace", "Man City"): (1, 4),
    ("Liverpool", "Forest"): (2, 2),
    ("Bournemouth", "Everton"): (1, 1),
    ("Coventry", "Hull"): (0, 1),
    ("Tottenham", "Newcastle"): (0, 2),
    ("Chelsea", "Brighton"): (4, 3),
    ("Leeds", "Brentford"): (1, 1),
    ("Sunderland", "Fulham"): (1, 0),
    ("Man United", "Ipswich"): (5, 2),
    ("Aston Villa", "Arsenal"): (0, 1),
    ("Ipswich", "Liverpool"): (0, 2),
    ("Newcastle", "Bournemouth"): (2, 2),
    ("Brentford", "Sunderland"): (1, 1),
    ("Brighton", "Leeds"): (1, 1),
    ("Fulham", "Crystal Palace"): (2, 3),
    ("Man City", "Coventry"): (1, 0),
    ("Forest", "Tottenham"): (0, 0),
    ("Hull", "Aston Villa"): (0, 0),
    ("Everton", "Man United"): (2, 2),
    ("Arsenal", "Chelsea"): (2, 1),
    ("Aston Villa", "Forest"): (1, 2),
    ("Bournemouth", "Brentford"): (2, 2),
    ("Chelsea", "Hull"): (2, 2),
    ("Crystal Palace", "Ipswich"): (2, 3),
    ("Liverpool", "Fulham"): (0, 0),
    ("Tottenham", "Everton"): (0, 0),
    ("Sunderland", "Arsenal"): (0, 2),
    ("Coventry", "Brighton"): (0, 5),
    ("Man United", "Man City"): (0, 1),
    ("Leeds", "Newcastle"): (4, 1),
    ("Brentford", "Chelsea"): (3, 0),
    ("Tottenham", "Aston Villa"): (2, 3),
    ("Brighton", "Arsenal"): (3, 0),
    ("Everton", "Ipswich"): (1, 0),
    ("Newcastle", "Hull"): (2, 1),
    ("Forest", "Coventry"): (0, 1),
    ("Bournemouth", "Liverpool"): (0, 1),
    ("Leeds", "Crystal Palace"): (0, 0),
    ("Man City", "Sunderland"): (5, 3),
    ("Fulham", "Man United"): (1, 1),

    ("Arsenal", "Leeds"): (2, 1),
    ("Chelsea", "Bournemouth"): (5, 1),
    ("Sunderland", "Brighton"): (0, 2),
    ("Aston Villa", "Brentford"): (2, 2),
    ("Ipswich", "Fulham"): (2, 1),
    ("Man United", "Tottenham"): (1, 1),
}

# =============================================================================
# DATA – UEFA CHAMPIONS LEAGUE
# =============================================================================

CL_FIXTURES = [
    [("AEK Athens", "LASK"), ("Club Brugge", "Aston Villa"), ("Borussia Dortmund", "Villarreal FC"),
     ("FC Porto", "Man City"), ("Lille OSC", "Real Betis"), ("Real Madrid", "Inter Milan"),
     ("FC Barcelona", "Feyenoord"), ("VfB Stuttgart", "Viking"), ("Liverpool", "Atletico Madrid"),
     ("Paris Saint-Germain", "Slovan Bratislava"), ("Sporting CP", "Galatasaray"),
     ("Napoli", "Arsenal"), ("Fenerbahçe", "Roma"), ("PSV Eindhoven", "Shakhtar Donetsk"),
     ("Como", "RB Leipzig"), ("Bayern Munich", "Bodø/Glimt"), ("Man United", "Sabah FK"),
     ("Slavia Prague", "RC Lens")],
    [("RC Lens", "Sporting CP"), ("Sabah FK", "Slavia Prague"), ("Arsenal", "Lille OSC"),
     ("Atletico Madrid", "Man United"), ("Inter Milan", "Club Brugge"), ("Galatasaray", "FC Barcelona"),
     ("RB Leipzig", "PSV Eindhoven"), ("Viking", "Bayern Munich"), ("Villarreal FC", "Napoli"),
     ("Feyenoord", "Como"), ("LASK", "Liverpool"), ("Roma", "Real Madrid"),
     ("Aston Villa", "Fenerbahçe"), ("Shakhtar Donetsk", "AEK Athens"),
     ("Bodø/Glimt", "Borussia Dortmund"), ("Man City", "Paris Saint-Germain"),
     ("Real Betis", "FC Porto"), ("Slovan Bratislava", "VfB Stuttgart")],
    [("Fenerbahçe", "Slavia Prague"), ("Sabah FK", "Borussia Dortmund"),
     ("Roma", "Slovan Bratislava"), ("FC Porto", "PSV Eindhoven"),
     ("Liverpool", "Villarreal FC"), ("Man City", "AEK Athens"),
     ("Paris Saint-Germain", "FC Barcelona"), ("Napoli", "Bodø/Glimt"),
     ("VfB Stuttgart", "Atletico Madrid"), ("Como", "Man United"),
     ("Lille OSC", "Galatasaray"), ("Aston Villa", "Viking"), ("Club Brugge", "RC Lens"),
     ("Bayern Munich", "Arsenal"), ("Inter Milan", "Shakhtar Donetsk"),
     ("Real Madrid", "RB Leipzig"), ("Real Betis", "Feyenoord"), ("Sporting CP", "LASK")],
    [("Shakhtar Donetsk", "Sporting CP"), ("Galatasaray", "VfB Stuttgart"),
     ("Atletico Madrid", "Bayern Munich"), ("FC Barcelona", "Aston Villa"),
     ("Feyenoord", "Inter Milan"), ("Bodø/Glimt", "Lille OSC"),
     ("LASK", "Slovan Bratislava"), ("Man United", "Roma"),
     ("Villarreal FC", "Paris Saint-Germain"), ("AEK Athens", "Real Madrid"),
     ("Fenerbahçe", "Liverpool"), ("Borussia Dortmund", "Real Betis"),
     ("FC Porto", "Napoli"), ("PSV Eindhoven", "Club Brugge"),
     ("RB Leipzig", "Man City"), ("RC Lens", "Como"), ("Slavia Prague", "Arsenal"),
     ("Viking", "Sabah FK")],
    [("Bodø/Glimt", "LASK"), ("Galatasaray", "Aston Villa"), ("Arsenal", "Borussia Dortmund"),
     ("Como", "AEK Athens"), ("Feyenoord", "FC Porto"), ("Man City", "Napoli"),
     ("RB Leipzig", "RC Lens"), ("Real Madrid", "PSV Eindhoven"),
     ("Slovan Bratislava", "Real Betis"), ("Sabah FK", "FC Barcelona"),
     ("Slavia Prague", "Villarreal FC"), ("Atletico Madrid", "Viking"),
     ("Club Brugge", "Liverpool"), ("Inter Milan", "VfB Stuttgart"),
     ("Shakhtar Donetsk", "Fenerbahçe"), ("Lille OSC", "Bayern Munich"),
     ("Paris Saint-Germain", "Roma"), ("Sporting CP", "Man United")],
    [("Viking", "Feyenoord"), ("Villarreal FC", "Sabah FK"), ("AEK Athens", "Galatasaray"),
     ("Roma", "Sporting CP"), ("Aston Villa", "Paris Saint-Germain"),
     ("FC Barcelona", "Man City"), ("Bayern Munich", "Slavia Prague"),
     ("Man United", "RB Leipzig"), ("Napoli", "Club Brugge"),
     ("Real Betis", "Como"), ("Slovan Bratislava", "Shakhtar Donetsk"),
     ("Arsenal", "Real Madrid"), ("Borussia Dortmund", "Inter Milan"),
     ("LASK", "Fenerbahçe"), ("Liverpool", "FC Porto"),
     ("PSV Eindhoven", "Atletico Madrid"), ("RC Lens", "Bodø/Glimt"),
     ("VfB Stuttgart", "Lille OSC")],
    [("Bodø/Glimt", "Atletico Madrid"), ("Galatasaray", "Feyenoord"),
     ("AEK Athens", "Roma"), ("Aston Villa", "Borussia Dortmund"),
     ("Inter Milan", "Liverpool"), ("FC Porto", "Slavia Prague"),
     ("Lille OSC", "Slovan Bratislava"), ("Real Madrid", "LASK"),
     ("VfB Stuttgart", "Club Brugge"), ("Fenerbahçe", "Villarreal FC"),
     ("Sabah FK", "Napoli"), ("Como", "Paris Saint-Germain"),
     ("Man United", "Bayern Munich"), ("RB Leipzig", "Shakhtar Donetsk"),
     ("RC Lens", "Man City"), ("Real Betis", "Arsenal"), ("Sporting CP", "FC Barcelona"),
     ("Viking", "PSV Eindhoven")],
    [("Arsenal", "Sabah FK"), ("Roma", "Lille OSC"), ("Atletico Madrid", "Fenerbahçe"),
     ("Borussia Dortmund", "AEK Athens"), ("Club Brugge", "Bodø/Glimt"),
     ("Bayern Munich", "Real Betis"), ("FC Barcelona", "Como"),
     ("Shakhtar Donetsk", "Real Madrid"), ("Feyenoord", "RB Leipzig"),
     ("LASK", "FC Porto"), ("Liverpool", "RC Lens"), ("Man City", "Sporting CP"),
     ("Paris Saint-Germain", "Galatasaray"), ("PSV Eindhoven", "VfB Stuttgart"),
     ("Slavia Prague", "Aston Villa"), ("Napoli", "Viking"),
     ("Villarreal FC", "Man United"), ("Slovan Bratislava", "Inter Milan")]
]

CL_ACTUAL_RESULTS = {
    ("AEK Athens", "LASK"): (1, 0),
    ("Club Brugge", "Aston Villa"): (2, 3),
    ("Borussia Dortmund", "Villarreal FC"): (3, 2),
    ("FC Porto", "Man City"): (0, 2),
    ("Lille OSC", "Real Betis"): (2, 3),
    ("Real Madrid", "Inter Milan"): (2, 1),
    ("FC Barcelona", "Feyenoord"): (5, 1),
    ("VfB Stuttgart", "Viking"): (3, 1),
    ("Liverpool", "Atletico Madrid"): (2, 1),
    ("Paris Saint-Germain", "Slovan Bratislava"): (6, 1),
    ("Sporting CP", "Galatasaray"): (3, 1),
    ("Napoli", "Arsenal"): (0, 1),
    ("Fenerbahçe", "Roma"): (1, 1),
    ("PSV Eindhoven", "Shakhtar Donetsk"): (1, 1),
    ("Como", "RB Leipzig"): (4, 1),
    ("Bayern Munich", "Bodø/Glimt"): (5, 0),
    ("Man United", "Sabah FK"): (4, 0),
    ("Slavia Prague", "RC Lens"): (2, 3),
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
    [("Ararat-Armenia", "Sparta Praha"), ("Omonia", "Celta"), ("Milan", "Benfica"),
     ("Leverkusen", "Celje"), ("H. Beer-Sheva", "GNK Dinamo"), ("Olympiacos", "Jagiellonia"),
     ("Anderlecht", "Lyon"), ("Sturm Graz", "Rennes"), ("Sunderland", "AZ Alkmaar"),
     ("OFI Crete", "Hoffenheim"), ("Levski Sofia", "Salzburg"), ("Beşiktaş", "Marseille"),
     ("Celtic", "Ferencváros"), ("Crystal Palace", "Lech Poznań"), ("Viktoria Plzeň", "Union SG"),
     ("Juventus", "N.E.C."), ("Lillestrøm", "Torreense"), ("Real Sociedad", "Bournemouth")],
    [("Sparta Praha", "Lillestrøm"), ("AZ Alkmaar", "H. Beer-Sheva"), ("Salzburg", "Milan"),
     ("Lech Poznań", "Leverkusen"), ("Celje", "Omonia"), ("Lyon", "Crystal Palace"),
     ("Union SG", "Real Sociedad"), ("Torreense", "Sunderland"), ("Bournemouth", "Sturm Graz"),
     ("Ferencváros", "Viktoria Plzeň"), ("GNK Dinamo", "Anderlecht"), ("Jagiellonia", "Ararat-Armenia"),
     ("N.E.C.", "Levski Sofia"), ("Marseille", "Olympiacos"), ("Celta", "Juventus"),
     ("Benfica", "Celtic"), ("Rennes", "OFI Crete"), ("Hoffenheim", "Beşiktaş")],
    [("Ararat-Armenia", "AZ Alkmaar"), ("Ferencváros", "Torreense"), ("GNK Dinamo", "N.E.C."),
     ("Juventus", "Rennes"), ("Lech Poznań", "Sunderland"), ("OFI Crete", "Leverkusen"),
     ("Union SG", "H. Beer-Sheva"), ("Sturm Graz", "Marseille"), ("Bournemouth", "Milan"),
     ("Beşiktaş", "Crystal Palace"), ("Celtic", "Celta"), ("Viktoria Plzeň", "Levski Sofia"),
     ("Jagiellonia", "Anderlecht"), ("Lillestrøm", "Real Sociedad"), ("Celje", "Salzburg"),
     ("Olympiacos", "Sparta Praha"), ("Omonia", "Benfica"), ("Hoffenheim", "Lyon")],
    [("Milan", "Ferencváros"), ("Sparta Praha", "Bournemouth"), ("Crystal Palace", "Hoffenheim"),
     ("Lillestrøm", "Viktoria Plzeň"), ("N.E.C.", "Omonia"), ("Levski Sofia", "Jagiellonia"),
     ("Real Sociedad", "Lyon"), ("Anderlecht", "Salzburg"), ("Rennes", "Olympiacos"),
     ("AZ Alkmaar", "Juventus"), ("Leverkusen", "Marseille"), ("Celtic", "Beşiktaş"),
     ("H. Beer-Sheva", "OFI Crete"), ("Celta", "Union SG"), ("Torreense", "Ararat-Armenia"),
     ("Sturm Graz", "Celje"), ("Benfica", "Lech Poznań"), ("Sunderland", "GNK Dinamo")],
    [("Beşiktaş", "H. Beer-Sheva"), ("Salzburg", "Ararat-Armenia"), ("Viktoria Plzeň", "Benfica"),
     ("GNK Dinamo", "Leverkusen"), ("Olympiacos", "Milan"), ("Marseille", "Levski Sofia"),
     ("Union SG", "Lech Poznań"), ("Celta", "Bournemouth"), ("Sparta Praha", "AZ Alkmaar"),
     ("Crystal Palace", "Real Sociedad"), ("Ferencváros", "Celje"), ("Juventus", "Omonia"),
     ("N.E.C.", "Rennes"), ("OFI Crete", "Anderlecht"), ("Lyon", "Lillestrøm"),
     ("Torreense", "Celtic"), ("Sunderland", "Jagiellonia"), ("Hoffenheim", "Sturm Graz")],
    [("AZ Alkmaar", "Sturm Graz"), ("Ararat-Armenia", "N.E.C."), ("H. Beer-Sheva", "Juventus"),
     ("Jagiellonia", "Crystal Palace"), ("Marseille", "Celta"), ("Omonia", "Celtic"),
     ("Anderlecht", "Hoffenheim"), ("Rennes", "GNK Dinamo"), ("Milan", "Sunderland"),
     ("Bournemouth", "Viktoria Plzeň"), ("Leverkusen", "Beşiktaş"), ("Salzburg", "Sparta Praha"),
     ("Lech Poznań", "Ferencváros"), ("Celje", "Olympiacos"), ("Lyon", "Union SG"),
     ("Levski Sofia", "Lillestrøm"), ("Real Sociedad", "Torreense"), ("Benfica", "OFI Crete")],
    [("Beşiktaş", "Union SG"), ("Ararat-Armenia", "Celje"), ("Ferencváros", "Juventus"),
     ("Jagiellonia", "Lyon"), ("Lillestrøm", "Bournemouth"), ("N.E.C.", "Benfica"),
     ("Olympiacos", "Hoffenheim"), ("Real Sociedad", "Viktoria Plzeň"), ("Sturm Graz", "OFI Crete"),
     ("AZ Alkmaar", "GNK Dinamo"), ("Leverkusen", "Salzburg"), ("Celtic", "Marseille"),
     ("Crystal Palace", "Sparta Praha"), ("H. Beer-Sheva", "Celta"), ("Lech Poznań", "Torreense"),
     ("Levski Sofia", "Milan"), ("Anderlecht", "Sunderland"), ("Rennes", "Omonia")],
    [("Milan", "Ararat-Armenia"), ("Sparta Praha", "Rennes"), ("Bournemouth", "H. Beer-Sheva"),
     ("Salzburg", "Crystal Palace"), ("Viktoria Plzeň", "Jagiellonia"), ("GNK Dinamo", "Sturm Graz"),
     ("Juventus", "Real Sociedad"), ("Celje", "N.E.C."), ("OFI Crete", "Lech Poznań"),
     ("Marseille", "Anderlecht"), ("Lyon", "Leverkusen"), ("Omonia", "Beşiktaş"),
     ("Union SG", "Celtic"), ("Celta", "Lillestrøm"), ("Torreense", "Olympiacos"),
     ("Benfica", "AZ Alkmaar"), ("Sunderland", "Levski Sofia"), ("Hoffenheim", "Ferencváros")]
]

UEL_FIXTURES_STD = [
    [(_standardise_uel(h), _standardise_uel(a)) for h, a in round_matches]
    for round_matches in _FIXTURES_UEL_RAW
]

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
    [("Lugano", "Crvena Zvezda"), ("Hajduk Split", "Ajax"), ("Gent", "Aarhus"),
     ("Egnatia", "Midtjylland"), ("KuPS Kuopio", "Trabzonspor"), ("Mjällby", "Inter Escaldes"),
     ("Panathinaikos", "Borac"), ("CSKA Sofia", "Monaco"), ("Riga", "Kairat Almaty"),
     ("Universitatea Craiova", "Getafe"), ("Atalanta", "Pafos"), ("Brighton", "Kauno Žalgiris"),
     ("Copenhagen", "Braga"), ("Twente", "Thun"), ("Hearts", "Nordsjælland"),
     ("Sint-Truidense", "Iberia Tbilisi"), ("Freiburg", "Jablonec"), ("Brann", "Lincoln Red Imps")],
    [("Kairat Almaty", "Panathinaikos"), ("Iberia Tbilisi", "Mjällby"),
     ("Nordsjælland", "CSKA Sofia"), ("Crvena Zvezda", "Copenhagen"),
     ("Jablonec", "Brighton"), ("Kauno Žalgiris", "Brann"), ("Getafe", "Lugano"),
     ("Inter Escaldes", "Universitatea Craiova"), ("Pafos", "Riga"),
     ("Trabzonspor", "Hearts"), ("Ajax", "Atalanta"), ("Aarhus", "Egnatia"),
     ("Monaco", "Freiburg"), ("Midtjylland", "Sint-Truidense"), ("Thun", "Hajduk Split"),
     ("Borac", "KuPS Kuopio"), ("Lincoln Red Imps", "Twente"), ("Braga", "Gent")],
    [("Aarhus", "Braga"), ("Atalanta", "Kairat Almaty"), ("Midtjylland", "Ajax"),
     ("Thun", "Hearts"), ("Crvena Zvezda", "Inter Escaldes"), ("KuPS Kuopio", "Gent"),
     ("Lincoln Red Imps", "Hajduk Split"), ("Mjällby", "Borac"), ("Trabzonspor", "Freiburg"),
     ("Monaco", "Nordsjælland"), ("Copenhagen", "Iberia Tbilisi"), ("Lugano", "Kauno Žalgiris"),
     ("Twente", "Pafos"), ("Getafe", "Brighton"), ("Sint-Truidense", "Brann"),
     ("Panathinaikos", "CSKA Sofia"), ("Riga", "Jablonec"), ("Universitatea Craiova", "Egnatia")],
    [("Kairat Almaty", "Mjällby"), ("Ajax", "Thun"), ("Brighton", "Universitatea Craiova"),
     ("Iberia Tbilisi", "Getafe"), ("Jablonec", "Lugano"), ("Kauno Žalgiris", "Riga"),
     ("Hearts", "Monaco"), ("Egnatia", "Lincoln Red Imps"), ("Pafos", "Midtjylland"),
     ("Brann", "Aarhus"), ("Nordsjælland", "Panathinaikos"), ("Borac", "Atalanta"),
     ("Hajduk Split", "Sint-Truidense"), ("Inter Escaldes", "Copenhagen"), ("Gent", "Crvena Zvezda"),
     ("CSKA Sofia", "Trabzonspor"), ("Braga", "KuPS Kuopio"), ("Freiburg", "Twente")],
    [("Kairat Almaty", "Universitatea Craiova"), ("Copenhagen", "Lugano"),
     ("Iberia Tbilisi", "Crvena Zvezda"), ("Getafe", "Inter Escaldes"),
     ("KuPS Kuopio", "CSKA Sofia"), ("Lincoln Red Imps", "Midtjylland"),
     ("Riga", "Atalanta"), ("Freiburg", "Panathinaikos"), ("Brann", "Braga"),
     ("Trabzonspor", "Jablonec"), ("Aarhus", "Twente"), ("Brighton", "Monaco"),
     ("Thun", "Gent"), ("Hearts", "Borac"), ("Hajduk Split", "Nordsjælland"),
     ("Sint-Truidense", "Ajax"), ("Egnatia", "Kauno Žalgiris"), ("Mjällby", "Pafos")],
    [("Ajax", "Getafe"), ("Monaco", "Lincoln Red Imps"), ("Atalanta", "Mjällby"),
     ("Lugano", "Sint-Truidense"), ("Midtjylland", "Hajduk Split"), ("Nordsjælland", "KuPS Kuopio"),
     ("Twente", "Kairat Almaty"), ("Borac", "Riga"), ("Crvena Zvezda", "Trabzonspor"),
     ("Jablonec", "Iberia Tbilisi"), ("Kauno Žalgiris", "Freiburg"), ("Inter Escaldes", "Aarhus"),
     ("Gent", "Brann"), ("Pafos", "Hearts"), ("Panathinaikos", "Brighton"),
     ("CSKA Sofia", "Thun"), ("Braga", "Egnatia"), ("Universitatea Craiova", "Copenhagen")],
]

UECL_FIXTURES_STD = [
    [(_standardise_uecl(h), _standardise_uecl(a)) for h, a in round_matches]
    for round_matches in _FIXTURES_UECL_RAW
]

# =============================================================================
# UNIFIED SIMULATION LOOP
# =============================================================================

def run_simulation(n_sims: int = NUM_PL_SIMS,
                   on_progress=None,
                   is_running=None) -> Dict[str, Any]:
    _RNG.seed(SEED)
    _NP_RNG.seed(SEED)

    pl_teams_set = {t for h, a in FIXTURES_LIST for t in (h, a)}

    # Results-only Elo
    pl_elos = build_current_pl_ratings(ACTUAL_RESULTS, pl_teams_set)

    ucl = EuropeanCompetition(
        "UCL", CL_FIXTURES, pl_elos, pl_teams_set,
        actual_results=CL_ACTUAL_RESULTS,
    )
    uel = EuropeanCompetition(
        "UEL", UEL_FIXTURES_STD, pl_elos, pl_teams_set,
        actual_results={},
    )
    uecl = EuropeanCompetition(
        "UECL", UECL_FIXTURES_STD, pl_elos, pl_teams_set,
        actual_results={},
    )

    pl_fixtures = ensure_full_pl_fixtures(FIXTURES_LIST)
    pl_sim = PLSimulator(pl_fixtures, pl_elos, ACTUAL_RESULTS)

    points_dist = defaultdict(list)
    position_counts = defaultdict(lambda: defaultdict(int))
    title_counts = defaultdict(int)
    ucl_qual_counts = defaultdict(int)
    uel_qual_counts = defaultdict(int)
    uecl_qual_counts = defaultdict(int)
    relegation_counts = defaultdict(int)
    euro_win_counts = defaultdict(lambda: defaultdict(int))
    carabao_win_counts = defaultdict(int)

    pl_ucl_spots, pl_uel_spots, pl_uecl_spots, pl_total_spots = [], [], [], []

    update_interval = max(1, n_sims // 100)

    for i in range(n_sims):
        if is_running is not None and not is_running():
            break
        if on_progress is not None and i % update_interval == 0:
            on_progress(i, n_sims)

        ucl_winner, ucl_elim = ucl.simulate()
        uel_winner, uel_elim = uel.simulate()
        uecl_winner, uecl_elim = uecl.simulate()

        fatigue_info = {}
        for team in pl_teams_set:
            if team in ucl_elim:
                fatigue_info[team] = (ucl_elim[team], "UCL")
            elif team in uel_elim:
                fatigue_info[team] = (uel_elim[team], "UEL")
            elif team in uecl_elim:
                fatigue_info[team] = (uecl_elim[team], "UECL")

        ranking, points = pl_sim.simulate_season(fatigue_info)
        carabao_winner = run_single_carabao_tournament()

        spots = allocate_european_spots(
            ranking,
            carabao_winner=carabao_winner,
            pl_teams=pl_teams_set,
            ucl_winner=ucl_winner,
            uel_winner=uel_winner,
            uecl_winner=uecl_winner,
            extra_ucl_spots=0,
        )

        pl_ucl_spots.append(len(spots["UCL"]))
        pl_uel_spots.append(len(spots["UEL"]))
        pl_uecl_spots.append(len(spots["UECL"]))
        pl_total_spots.append(
            len(spots["UCL"]) + len(spots["UEL"]) + len(spots["UECL"])
        )

        for team in spots["UCL"]:
            ucl_qual_counts[team] += 1
        for team in spots["UEL"]:
            uel_qual_counts[team] += 1
        for team in spots["UECL"]:
            uecl_qual_counts[team] += 1

        for pos, team in enumerate(ranking, 1):
            points_dist[team].append(points[team])
            position_counts[team][pos] += 1
            if pos == 1:
                title_counts[team] += 1
            if pos >= 18:
                relegation_counts[team] += 1

        for comp, winner in [("UCL", ucl_winner),
                             ("UEL", uel_winner),
                             ("UECL", uecl_winner)]:
            if winner in pl_teams_set:
                euro_win_counts[comp][winner] += 1
        if carabao_winner in pl_teams_set:
            carabao_win_counts[carabao_winner] += 1

    total = n_sims
    avg_positions, avg_points = {}, {}
    for team in pl_teams_set:
        pos_total = sum(p * c for p, c in position_counts[team].items())
        avg_positions[team] = pos_total / total
        arr = np.array(points_dist[team], dtype=np.float64)
        avg_points[team] = float(arr.mean()) if arr.size else 0.0

    return {
        'n_sims': n_sims,
        'pl_teams_set': pl_teams_set,
        'pl_elos': pl_elos,
        'avg_positions': avg_positions,
        'avg_points': avg_points,
        'title_prob': {t: title_counts[t] / total * 100 for t in pl_teams_set},
        'ucl_qual_prob': {t: ucl_qual_counts[t] / total * 100 for t in pl_teams_set},
        'uel_qual_prob': {t: uel_qual_counts[t] / total * 100 for t in pl_teams_set},
        'uecl_qual_prob': {t: uecl_qual_counts[t] / total * 100 for t in pl_teams_set},
        'relegation_prob': {t: relegation_counts[t] / total * 100 for t in pl_teams_set},
        'avg_pl_ucl_spots': float(np.mean(pl_ucl_spots)),
        'avg_pl_uel_spots': float(np.mean(pl_uel_spots)),
        'avg_pl_uecl_spots': float(np.mean(pl_uecl_spots)),
        'avg_pl_total_spots': float(np.mean(pl_total_spots)),
        'euro_win_counts': {c: dict(d) for c, d in euro_win_counts.items()},
        'carabao_win_counts': dict(carabao_win_counts),
    }


def run_unified_simulation():
    print("\n" + "=" * 80)
    print("UNIFIED PREMIER LEAGUE + EUROPEAN + CARABAO CUP SIMULATION")
    print("(Elo built purely from actual PL results – no betting odds)")
    print("=" * 80)
    print(f"\nRunning {NUM_PL_SIMS} unified simulations...")

    def progress(sim, total):
        print(f"\r  {sim * 100 // max(total, 1):3d}% ({sim}/{total})",
              end="", flush=True)

    r = run_simulation(NUM_PL_SIMS, on_progress=progress)
    print("\r  100% done.               ")

    print("\n" + "=" * 80)
    print("RESULTS-BASED PREMIER LEAGUE ELO RATINGS")
    print("=" * 80)
    for team in sorted(r['pl_elos'], key=lambda t: r['pl_elos'][t], reverse=True):
        print(f"  {team:<22} {r['pl_elos'][team]:>7.1f}")

    print("\n" + "=" * 80)
    print("AVERAGE PREMIER LEAGUE EUROPEAN SPOTS")
    print("=" * 80)
    print(f"Average PL UCL spots: {r['avg_pl_ucl_spots']:.2f}")
    print(f"Average PL UEL spots: {r['avg_pl_uel_spots']:.2f}")
    print(f"Average PL UECL spots: {r['avg_pl_uecl_spots']:.2f}")
    print(f"Average total PL European spots: {r['avg_pl_total_spots']:.2f}")

    print("\n" + "=" * 135)
    print("FINAL PREMIER LEAGUE PROJECTIONS")
    print("=" * 135)
    header = (
        f"{'AvgPos':<7}{'Team':<22}{'Pts':<8}"
        f"{'Title%':<8}{'UCLAny%':<9}{'UELAny%':<9}"
        f"{'UECLAny%':<9}{'EuroAny%':<10}{'Releg%':<8}"
    )
    print(header)
    print("-" * 135)

    for team in sorted(r['pl_teams_set'], key=lambda t: r['avg_positions'][t]):
        euro = (r['ucl_qual_prob'][team] + r['uel_qual_prob'][team]
                + r['uecl_qual_prob'][team])
        print(
            f"{r['avg_positions'][team]:<7.2f}{team:<22}"
            f"{r['avg_points'][team]:<8.2f}{r['title_prob'][team]:<8.2f}"
            f"{r['ucl_qual_prob'][team]:<9.2f}{r['uel_qual_prob'][team]:<9.2f}"
            f"{r['uecl_qual_prob'][team]:<9.2f}{euro:<10.2f}"
            f"{r['relegation_prob'][team]:<8.2f}"
        )


def main():
    run_unified_simulation()


if __name__ == "__main__":
    main()