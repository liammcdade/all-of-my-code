"""
Scottish Premiership 2026/27 simulation with split system.
12 teams, 38 games (33 pre-split + 5 post-split).
Uses provided Elos and actual results.

Also includes Scottish Cup and Scottish League Cup simulations.
"""

import math
import random
import time
from collections import defaultdict
from typing import Dict, List, Tuple, Optional, Set, Any
import numpy as np

# =============================================================================
# CONSTANTS
# =============================================================================

HOME_ADVANTAGE_ELO = 40.0
ELO_SCALE = 400.0
LEAGUE_AVERAGE_ELO = 1500.0
MAX_GOALS = 10
NUM_SIMS = 10000

BASE_HOME_XG = 1.6644
BASE_AWAY_XG = 1.1200
XG_ELO_SENSITIVITY = 0.002

# Number of fixtures in the pre-split phase (12 teams × 11 opponents × 3 games / 2)
PRE_SPLIT_FIXTURES = 198
# Number of post-split fixtures (2 groups × 6 teams × 5 opponents / 2)
POST_SPLIT_FIXTURES = 30

_RNG = random.Random(0)
_NP_RNG = np.random.RandomState(0)

_FACTORIALS = np.array([math.factorial(i) for i in range(MAX_GOALS + 1)], dtype=np.float64)
_POISSON_CACHE: Dict[int, np.ndarray] = {}
_LAMBDA_ROUND_PRECISION = 100


# =============================================================================
# HELPERS
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


def sample_score_from_elos(elo_home: float, elo_away: float) -> Tuple[int, int]:
    """Sample a scoreline from two Elo ratings (with home advantage)."""
    diff = elo_home - elo_away + HOME_ADVANTAGE_ELO
    lam_h = BASE_HOME_XG * math.exp(XG_ELO_SENSITIVITY * diff)
    lam_a = BASE_AWAY_XG * math.exp(-XG_ELO_SENSITIVITY * diff)
    hg = int(min(_NP_RNG.poisson(lam_h), MAX_GOALS))
    ag = int(min(_NP_RNG.poisson(lam_a), MAX_GOALS))
    return hg, ag


def _poisson_batch(lam: np.ndarray) -> np.ndarray:
    """Vectorized Poisson sampling."""
    return _NP_RNG.poisson(lam)


# =============================================================================
# SCOTTISH PREMIERSHIP TEAMS & ELOS
# =============================================================================

SCOTTISH_TEAMS: Dict[str, float] = {
    "Celtic": 1676,
    "Rangers": 1633,
    "Hearts": 1567,
    "Dundee": 1412,
    "St Johnstone": 1364,
    "Dundee United": 1425,
    "St. Mirren": 1362,
    "Aberdeen": 1377,
    "Motherwell": 1484,
    "Hibernian": 1467,
    "Falkirk": 1389,
    "Kilmarnock": 1374,
}

# =============================================================================
# ACTUAL RESULTS (Matchweeks 1–9, 2026/27)
# =============================================================================

ACTUAL_RESULTS: Dict[Tuple[str, str], Tuple[int, int]] = {
    # Matchweek 1 (31 Jul – 3 Aug 2026)
    ("Dundee United", "Rangers"): (1, 1),
    ("Falkirk", "St. Mirren"): (0, 2),
    ("Aberdeen", "Hearts"): (2, 1),
    ("St Johnstone", "Kilmarnock"): (4, 3),
    ("Hibernian", "Motherwell"): (1, 2),
    ("Celtic", "Dundee"): (1, 0),

    # Matchweek 2 (8–9 Aug 2026)
    ("Dundee", "Aberdeen"): (2, 0),
    ("St. Mirren", "St Johnstone"): (1, 0),
    ("Kilmarnock", "Celtic"): (1, 5),
    ("Hearts", "Dundee United"): (4, 0),
    ("Motherwell", "Falkirk"): (0, 0),
    ("Rangers", "Hibernian"): (1, 2),

    # Matchweek 3 (22 Aug & 9/15 Sep 2026)
    ("Dundee United", "Dundee"): (0, 2),
    ("Rangers", "St. Mirren"): (1, 0),
    ("St Johnstone", "Celtic"): (0, 1),
    ("Falkirk", "Hearts"): (2, 1),
    ("Hibernian", "Kilmarnock"): (0, 1),
    ("Motherwell", "Aberdeen"): (0, 4),

    # Matchweek 4 (29–30 Aug 2026)
    ("Celtic", "Falkirk"): (2, 1),
    ("Hearts", "St Johnstone"): (2, 1),
    ("Kilmarnock", "Dundee United"): (0, 4),
    ("Aberdeen", "Rangers"): (0, 1),
    ("Dundee", "Hibernian"): (1, 2),
    ("St. Mirren", "Motherwell"): (3, 3),

    # Matchweek 5 (2–3 Sep 2026)
    ("Celtic", "Aberdeen"): (3, 0),
    ("Dundee", "St Johnstone"): (1, 1),
    ("Kilmarnock", "St. Mirren"): (0, 1),
    ("Motherwell", "Dundee United"): (3, 0),
    ("Falkirk", "Rangers"): (1, 2),
    ("Hibernian", "Hearts"): (1, 3),

    # Matchweek 6 (5–6 Sep 2026)
    ("Aberdeen", "Kilmarnock"): (0, 0),
    ("Dundee United", "Falkirk"): (1, 1),
    ("Rangers", "Motherwell"): (1, 0),
    ("St. Mirren", "Celtic"): (1, 2),
    ("Hearts", "Dundee"): (2, 1),
    ("St Johnstone", "Hibernian"): (2, 1),

    # Matchweek 7 (19–20 Sep 2026)
    ("Celtic", "Rangers"): (0, 1),
    ("Dundee", "Motherwell"): (2, 1),
    ("Hibernian", "Aberdeen"): (1, 1),
    ("St Johnstone", "Falkirk"): (1, 1),
    ("St. Mirren", "Dundee United"): (0, 3),
    ("Kilmarnock", "Hearts"): (1, 1),

    # Matchweek 8 (10–11 Oct 2026)
    ("Motherwell", "Celtic"): (0, 2),
    ("Aberdeen", "St Johnstone"): (0, 1),
    ("Dundee United", "Hibernian"): (1, 0),
    ("Falkirk", "Dundee"): (1, 2),
    ("Hearts", "St. Mirren"): (5, 0),
    ("Rangers", "Kilmarnock"): (3, 1),

    # Matchweek 9 (17–18 Oct 2026)
    ("Dundee", "Rangers"): (2, 2),
    ("Aberdeen", "St. Mirren"): (3, 1),
    ("Kilmarnock", "Motherwell"): (3, 2),
    ("Hibernian", "Falkirk"): (1, 2),
    ("St Johnstone", "Dundee United"): (1, 1),
    # Celtic vs Hearts — not played (scheduled 18 Oct)
}


# =============================================================================
# FIXTURE GENERATION
# =============================================================================

def generate_pre_split_fixtures(
    actual_results: Dict[Tuple[str, str], Tuple[int, int]],
) -> Tuple[List[Tuple[str, str]], Dict[Tuple[str, str], int]]:
    """Generate 198 pre-split fixtures (each pair plays 3 times).

    Actual results are included in their recorded orientation.
    Returns (fixtures, home_counts) where home_counts[(h,a)] = times h hosted a.
    """
    teams = sorted(SCOTTISH_TEAMS.keys())
    fixtures: List[Tuple[str, str]] = []
    home_counts: Dict[Tuple[str, str], int] = defaultdict(int)

    for i in range(len(teams)):
        for j in range(i + 1, len(teams)):
            a, b = teams[i], teams[j]

            games: List[Tuple[str, str]] = []
            if (a, b) in actual_results:
                games.append((a, b))
                home_counts[(a, b)] += 1
            if (b, a) in actual_results:
                games.append((b, a))
                home_counts[(b, a)] += 1

            a_home = home_counts.get((a, b), 0)
            b_home = home_counts.get((b, a), 0)

            remaining = 3 - len(games)
            for _ in range(remaining):
                if a_home <= b_home:
                    games.append((a, b))
                    a_home += 1
                    home_counts[(a, b)] += 1
                else:
                    games.append((b, a))
                    b_home += 1
                    home_counts[(b, a)] += 1

            fixtures.extend(games)

    _RNG.shuffle(fixtures)
    return fixtures, home_counts


def generate_post_split_fixtures(
    top6: List[str],
    bottom6: List[str],
    pre_split_home_counts: Dict[Tuple[str, str], int],
) -> List[Tuple[str, str]]:
    """Generate 30 post-split fixtures (each team plays the other 5 in its group once).

    Home/away is chosen to balance the overall 4-game record (2 home, 2 away)
    against each opponent across the full season.
    """
    fixtures: List[Tuple[str, str]] = []

    for group in (top6, bottom6):
        for i in range(len(group)):
            for j in range(i + 1, len(group)):
                a, b = group[i], group[j]
                a_home_pre = pre_split_home_counts.get((a, b), 0)
                b_home_pre = pre_split_home_counts.get((b, a), 0)
                # Post-split host is the side that hosted fewer times pre-split
                if a_home_pre > b_home_pre:
                    fixtures.append((b, a))
                else:
                    fixtures.append((a, b))

    _RNG.shuffle(fixtures)
    return fixtures


# =============================================================================
# SINGLE-SEASON SIMULATION
# =============================================================================

def simulate_season(
    elos: Dict[str, float],
    pre_split_fixtures: List[Tuple[str, str]],
    pre_split_home_counts: Dict[Tuple[str, str], int],
    actual_results: Dict[Tuple[str, str], Tuple[int, int]],
) -> Tuple[List[str], Dict[str, int], Dict[str, int], Dict[str, int]]:
    """Simulate one full Scottish Premiership season (38 games with split).

    Returns (final_ranking, points, gf, ga).
    """
    teams = sorted(elos.keys())
    n = len(teams)
    team_to_idx = {t: i for i, t in enumerate(teams)}

    # ---- Pre-split phase (198 games, vectorised) ----
    elo_arr = np.array([elos[t] for t in teams], dtype=np.float64)

    h_idx = np.array([team_to_idx[h] for h, a in pre_split_fixtures], dtype=np.int64)
    a_idx = np.array([team_to_idx[a] for h, a in pre_split_fixtures], dtype=np.int64)

    diff = elo_arr[h_idx] - elo_arr[a_idx] + HOME_ADVANTAGE_ELO
    lam_h = BASE_HOME_XG * np.exp(XG_ELO_SENSITIVITY * diff)
    lam_a = BASE_AWAY_XG * np.exp(-XG_ELO_SENSITIVITY * diff)

    hg = _poisson_batch(lam_h)
    ag = _poisson_batch(lam_a)
    np.minimum(hg, MAX_GOALS, out=hg)
    np.minimum(ag, MAX_GOALS, out=ag)

    # Apply actual results
    for i, (h, a) in enumerate(pre_split_fixtures):
        if (h, a) in actual_results:
            hg[i], ag[i] = actual_results[(h, a)]

    home_win = hg > ag
    away_win = ag > hg
    draw = ~(home_win | away_win)

    pts = np.zeros(n, dtype=np.int64)
    gf = np.zeros(n, dtype=np.int64)
    ga = np.zeros(n, dtype=np.int64)

    np.add.at(pts, h_idx[home_win], 3)
    np.add.at(pts, a_idx[away_win], 3)
    np.add.at(pts, h_idx[draw], 1)
    np.add.at(pts, a_idx[draw], 1)

    np.add.at(gf, h_idx, hg)
    np.add.at(gf, a_idx, ag)
    np.add.at(ga, h_idx, ag)
    np.add.at(ga, a_idx, hg)

    # ---- Split ----
    gd = gf - ga
    tiebreak = _NP_RNG.uniform(0, 0.0001, size=n)
    order = np.lexsort((-tiebreak, gf, gd, pts))[::-1]
    ranked = [teams[i] for i in order]

    top6 = ranked[:6]
    bottom6 = ranked[6:]

    # ---- Post-split phase (30 games) ----
    post_fixtures = generate_post_split_fixtures(
        top6, bottom6, pre_split_home_counts
    )

    for home, away in post_fixtures:
        hg_i, ag_i = sample_score_from_elos(elos[home], elos[away])
        h = team_to_idx[home]
        a = team_to_idx[away]

        if hg_i > ag_i:
            pts[h] += 3
        elif ag_i > hg_i:
            pts[a] += 3
        else:
            pts[h] += 1
            pts[a] += 1

        gf[h] += hg_i
        ga[h] += ag_i
        gf[a] += ag_i
        ga[a] += hg_i

    # ---- Final ranking ----
    gd = gf - ga

    def _rank_group(group: List[str]) -> List[str]:
        return sorted(
            group,
            key=lambda t: (pts[team_to_idx[t]], gd[team_to_idx[t]], gf[team_to_idx[t]]),
            reverse=True,
        )

    final_ranking = _rank_group(top6) + _rank_group(bottom6)

    points_dict = {t: int(pts[team_to_idx[t]]) for t in teams}
    gf_dict = {t: int(gf[team_to_idx[t]]) for t in teams}
    ga_dict = {t: int(ga[team_to_idx[t]]) for t in teams}

    return final_ranking, points_dict, gf_dict, ga_dict


# =============================================================================
# SCOTTISH CUP & LEAGUE CUP
# =============================================================================

# Scottish Cup outright odds (fractional, normalised to PL-style names)
SCOTTISH_CUP_ODDS: Dict[str, str] = {
    "Celtic": "2/1",
    "Rangers": "5/2",
    "Hearts": "8/1",
    "Hibernian": "10/1",
    "Aberdeen": "12/1",
    "Motherwell": "16/1",
    "Dundee United": "20/1",
    "Dundee": "25/1",
    "St Johnstone": "28/1",
    "Kilmarnock": "33/1",
    "St. Mirren": "40/1",
    "Falkirk": "50/1",
}


def _frac_to_prob(s: str) -> float:
    num, den = s.split("/")
    return int(den) / (int(num) + int(den))


_sc_raw = {t: _frac_to_prob(o) for t, o in SCOTTISH_CUP_ODDS.items()}
_sc_total = sum(_sc_raw.values())
SCOTTISH_CUP_WIN_PROBS: Dict[str, float] = {
    t: p / _sc_total for t, p in _sc_raw.items()
}

_SC_NAMES: List[str] = list(SCOTTISH_CUP_WIN_PROBS.keys())
_SC_WEIGHTS: np.ndarray = np.array(
    [SCOTTISH_CUP_WIN_PROBS[t] for t in _SC_NAMES], dtype=np.float64
)


def sample_scottish_cup_winner() -> str:
    return _SC_NAMES[int(_NP_RNG.choice(len(_SC_NAMES), p=_SC_WEIGHTS))]


# League Cup: simple knockout simulation using Elos
LEAGUE_CUP_TEAMS = list(SCOTTISH_TEAMS.keys())


def _penalty_winner(a: str, b: str, elos: Dict[str, float]) -> str:
    exp_a = 1 / (1 + 10 ** ((elos[b] - elos[a]) / ELO_SCALE))
    return a if _RNG.random() < exp_a else b


def _league_cup_match(a: str, b: str, elos: Dict[str, float]) -> str:
    hg, ag = sample_score_from_elos(elos[a], elos[b])
    if hg > ag:
        return a
    if ag > hg:
        return b
    return _penalty_winner(a, b, elos)


def simulate_league_cup(elos: Dict[str, float]) -> str:
    """Simulate the Scottish League Cup (12-team knockout with byes).

    Format:
      - Preliminary round: seeds 5-12 play four knockout matches.
      - Quarter-finals: top 4 seeds join the 4 preliminary winners (8 teams).
      - Semi-finals (4) -> Final (2).

    Seeding: 5v12, 6v11, 7v10, 8v9 in the prelim; then 1v(8/9 winner),
    2v(7/10 winner), 3v(6/11 winner), 4v(5/12 winner) in the QF.
    """
    seeded = sorted(LEAGUE_CUP_TEAMS, key=lambda t: elos[t], reverse=True)

    # --- Preliminary round: seeds 5-12 ---
    prelim_pairs = [
        (seeded[4], seeded[11]),   # 5 v 12
        (seeded[5], seeded[10]),   # 6 v 11
        (seeded[6], seeded[9]),    # 7 v 10
        (seeded[7], seeded[8]),    # 8 v 9
    ]
    prelim_winners = [_league_cup_match(a, b, elos) for a, b in prelim_pairs]

    # --- Quarter-finals: seeds 1-4 vs prelim winners ---
    qf_pairs = [
        (seeded[0], prelim_winners[3]),   # 1 v winner(8/9)
        (seeded[1], prelim_winners[2]),   # 2 v winner(7/10)
        (seeded[2], prelim_winners[1]),   # 3 v winner(6/11)
        (seeded[3], prelim_winners[0]),   # 4 v winner(5/12)
    ]
    qf_winners = [_league_cup_match(a, b, elos) for a, b in qf_pairs]

    # --- Semi-finals ---
    sf_pairs = [(qf_winners[0], qf_winners[1]), (qf_winners[2], qf_winners[3])]
    sf_winners = [_league_cup_match(a, b, elos) for a, b in sf_pairs]

    # --- Final ---
    return _league_cup_match(sf_winners[0], sf_winners[1], elos)


# =============================================================================
# EUROPEAN QUALIFICATION
# =============================================================================

def allocate_european_spots(
    ranking: List[str],
    scottish_cup_winner: str,
    league_cup_winner: str,
) -> Dict[str, Set[str]]:
    """Allocate Scottish European spots.

    Scotland typically gets:
      - 1 UCL (champion)
      - 1 UEL (2nd, or Scottish Cup winner)
      - 2 UECL (3rd, 4th, or cup winners)

    Cascading applies if cup winners are already qualified.
    """
    ucl = {ranking[0]}

    # UEL: 2nd place + Scottish Cup winner (cascade if already qualified)
    uel: Set[str] = set()
    for team in ranking[1:]:
        if team not in ucl:
            uel.add(team)
            break

    if scottish_cup_winner not in ucl and scottish_cup_winner not in uel:
        uel.add(scottish_cup_winner)
    else:
        for team in ranking:
            if team not in ucl and team not in uel:
                uel.add(team)
                break

    # UECL: 3rd + 4th (cascade)
    uecl: Set[str] = set()
    for team in ranking:
        if team not in ucl and team not in uel and team not in uecl:
            uecl.add(team)
            if len(uecl) >= 2:
                break

    # League Cup winner: UECL spot (cascade)
    if league_cup_winner not in ucl and league_cup_winner not in uel and league_cup_winner not in uecl:
        uecl.add(league_cup_winner)
        # If that makes 3 UECL spots, fine — Scotland can have up to 3

    return {"UCL": ucl, "UEL": uel, "UECL": uecl}


# =============================================================================
# MAIN SIMULATION LOOP
# =============================================================================

def run_simulation(
    n_sims: int = NUM_SIMS,
    seed: Optional[int] = None,
    on_progress=None,
    is_running=None,
) -> Dict[str, Any]:
    if seed is None:
        seed = random.SystemRandom().randint(0, 2**32 - 1)
    _RNG.seed(seed)
    _NP_RNG.seed(seed)

    pre_split_fixtures, pre_split_home_counts = generate_pre_split_fixtures(ACTUAL_RESULTS)
    assert len(pre_split_fixtures) == PRE_SPLIT_FIXTURES, (
        f"Expected {PRE_SPLIT_FIXTURES} pre-split fixtures, got {len(pre_split_fixtures)}"
    )

    teams = sorted(SCOTTISH_TEAMS.keys())

    # Tracking
    points_dist = defaultdict(list)
    position_counts = defaultdict(lambda: defaultdict(int))
    title_counts = defaultdict(int)
    ucl_qual_counts = defaultdict(int)
    uel_qual_counts = defaultdict(int)
    uecl_qual_counts = defaultdict(int)
    relegation_counts = defaultdict(int)
    relegation_playoff_counts = defaultdict(int)
    scottish_cup_win_counts = defaultdict(int)
    league_cup_win_counts = defaultdict(int)

    avg_title_points: List[float] = []
    avg_ucl_qual_points: List[float] = []

    update_interval = max(1, n_sims // 1000)
    completed = 0

    for i in range(n_sims):
        if is_running is not None and not is_running():
            break
        if on_progress is not None and i % update_interval == 0:
            on_progress(i, n_sims)

        ranking, points, gf, ga = simulate_season(
            SCOTTISH_TEAMS, pre_split_fixtures, pre_split_home_counts, ACTUAL_RESULTS
        )

        sc_winner = sample_scottish_cup_winner()
        lc_winner = simulate_league_cup(SCOTTISH_TEAMS)

        spots = allocate_european_spots(ranking, sc_winner, lc_winner)

        for pos, team in enumerate(ranking, 1):
            points_dist[team].append(points[team])
            position_counts[team][pos] += 1
            if pos == 1:
                title_counts[team] += 1
            if pos == 12:
                relegation_counts[team] += 1
            if pos == 11:
                relegation_playoff_counts[team] += 1

        for team in spots["UCL"]:
            ucl_qual_counts[team] += 1
        for team in spots["UEL"]:
            uel_qual_counts[team] += 1
        for team in spots["UECL"]:
            uecl_qual_counts[team] += 1

        scottish_cup_win_counts[sc_winner] += 1
        league_cup_win_counts[lc_winner] += 1

        avg_title_points.append(float(points[ranking[0]]))
        if spots["UCL"]:
            avg_ucl_qual_points.append(
                float(np.mean([points[t] for t in spots["UCL"]]))
            )

        completed += 1

    total = completed if completed > 0 else n_sims

    avg_points = {}
    avg_positions = {}
    median_positions = {}

    for team in teams:
        arr = np.array(points_dist[team], dtype=np.float64)
        avg_points[team] = float(arr.mean()) if arr.size else 0.0

        pos_total = sum(p * c for p, c in position_counts[team].items())
        avg_positions[team] = pos_total / total

        all_positions = []
        for pos, count in position_counts[team].items():
            all_positions.extend([pos] * count)
        all_positions.sort()
        median_positions[team] = all_positions[len(all_positions) // 2] if all_positions else 0

    return {
        "n_sims": total,
        "teams": teams,
        "avg_points": avg_points,
        "avg_positions": avg_positions,
        "median_positions": median_positions,
        "title_prob": {t: title_counts[t] / total * 100 for t in teams},
        "ucl_qual_prob": {t: ucl_qual_counts[t] / total * 100 for t in teams},
        "uel_qual_prob": {t: uel_qual_counts[t] / total * 100 for t in teams},
        "uecl_qual_prob": {t: uecl_qual_counts[t] / total * 100 for t in teams},
        "relegation_prob": {t: relegation_counts[t] / total * 100 for t in teams},
        "relegation_playoff_prob": {t: relegation_playoff_counts[t] / total * 100 for t in teams},
        "avg_title_points": float(np.mean(avg_title_points)) if avg_title_points else 0.0,
        "avg_ucl_qual_points": float(np.mean(avg_ucl_qual_points)) if avg_ucl_qual_points else 0.0,
        "scottish_cup_win_prob": {t: scottish_cup_win_counts.get(t, 0) / total * 100 for t in teams},
        "league_cup_win_prob": {t: league_cup_win_counts.get(t, 0) / total * 100 for t in teams},
        "seed": seed,
    }


# =============================================================================
# OUTPUT
# =============================================================================

def run_simulation_cli():
    print("\n" + "=" * 90)
    print("SCOTTISH PREMIERSHIP 2026/27 — MONTE CARLO SIMULATION")
    print("(12 teams, 38 games, split system; Elos from provided table)")
    print("=" * 90)

    print(f"\nRunning {NUM_SIMS:,} simulations...")

    bar_width = 30
    start_time = time.time()

    def format_eta(seconds):
        if seconds < 60:
            return f"{seconds:.0f}s"
        if seconds < 3600:
            return f"{seconds // 60:.0f}m {seconds % 60:.0f}s"
        return f"{seconds // 3600:.0f}h {(seconds % 3600) // 60:.0f}m"

    def progress(sim, total):
        pct = sim / total if total else 0
        filled = int(bar_width * pct)
        bar = "#" * filled + " " * (bar_width - filled)
        elapsed = time.time() - start_time
        if sim > 0 and pct > 0:
            eta_secs = elapsed * (1 - pct) / pct
            eta_str = format_eta(eta_secs)
        else:
            eta_str = "--"
        print(f"\r  [{bar}] {pct*100:5.1f}% ({sim}/{total}) ETA: {eta_str}",
              end="", flush=True)

    r = run_simulation(NUM_SIMS, on_progress=progress)
    print("\r" + " " * 70 + "\r", end="", flush=True)

    teams = r["teams"]

    print("\n" + "=" * 100)
    print("FINAL SCOTTISH PREMIERSHIP PROJECTIONS")
    print("=" * 100)
    print(
        f"{'Team':<22}{'Pts':<8}{'Pos':<7}{'Title%':<9}"
        f"{'UCL%':<8}{'UEL%':<8}{'UECL%':<8}"
        f"{'RelPO%':<9}{'Rel%':<8}"
    )
    print("-" * 100)

    sorted_teams = sorted(teams, key=lambda t: r["avg_points"][t], reverse=True)

    for team in sorted_teams:
        print(
            f"{team:<22}"
            f"{r['avg_points'][team]:<8.2f}"
            f"{r['avg_positions'][team]:<7.2f}"
            f"{r['title_prob'][team]:<9.2f}"
            f"{r['ucl_qual_prob'][team]:<8.2f}"
            f"{r['uel_qual_prob'][team]:<8.2f}"
            f"{r['uecl_qual_prob'][team]:<8.2f}"
            f"{r['relegation_playoff_prob'][team]:<9.2f}"
            f"{r['relegation_prob'][team]:<8.2f}"
        )

    print(f"\nAverage title-winning points: {r['avg_title_points']:.1f}")
    print(f"Average UCL qualifier points:  {r['avg_ucl_qual_points']:.1f}")

    print("\n" + "=" * 80)
    print("SCOTTISH CUP WIN PROBABILITY (from outright odds)")
    print("=" * 80)
    sc_sorted = sorted(
        SCOTTISH_CUP_WIN_PROBS.keys(),
        key=lambda t: SCOTTISH_CUP_WIN_PROBS[t],
        reverse=True,
    )
    for team in sc_sorted:
        implied = SCOTTISH_CUP_WIN_PROBS[team] * 100
        sim = r["scottish_cup_win_prob"].get(team, 0.0)
        print(f"  {team:<22} {implied:>6.2f}%  (sim: {sim:.2f}%)")

    print("\n" + "=" * 80)
    print("SCOTTISH LEAGUE CUP WIN PROBABILITY (simulated)")
    print("=" * 80)
    lc_sorted = sorted(teams, key=lambda t: r["league_cup_win_prob"][t], reverse=True)
    for team in lc_sorted:
        print(f"  {team:<22} {r['league_cup_win_prob'][team]:>6.2f}%")

    print(f"\nSimulation seed: {r['seed']}")


# =============================================================================
# ENTRY POINT
# =============================================================================

if __name__ == "__main__":
    run_simulation_cli()