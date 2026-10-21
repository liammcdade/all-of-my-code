"""
Scottish Premiership 2026/27 — simplified league-only simulation.
12 teams, 38 games (33 pre-split + 5 post-split) using the split format.
Uses provided Elos and actual results from matchweeks 1–9.

European spots (league position):
  1st -> UCL Play-off Round (UEL league phase guaranteed if defeated)
  2nd -> UCL Second Qualifying Round
  3rd -> UECL Second Qualifying Round
  4th -> UECL Second Qualifying Round
"""

import math
import random
import sys
import numpy as np
from collections import defaultdict, Counter
from tqdm import tqdm

_DISABLE_TQDM = getattr(sys, "frozen", False)  # no bar needed inside the GUI

HOME_ADVANTAGE_ELO = 40.0
BASE_HOME_XG = 1.6644
BASE_AWAY_XG = 1.1200
XG_ELO_SENSITIVITY = 0.002
MAX_GOALS = 10
NUM_SIMS = 2500

ELO_SCALE = 400.0
LEAGUE_AVERAGE_ELO = 1500.0
ELO_MAX_PULL = 1.0
LEAGUE_TOTAL_FIXTURES = 198  # 12 teams × 33 games / 2
_ELO_LN_SCALE = math.log(10.0) / ELO_SCALE


def regress_elos(elos, games_played, total_games, mean, max_pull):
    if total_games == 0:
        return dict(elos)
    frac = max(0.0, min(1.0, games_played / total_games))
    pull = max(0.0, min(1.0, max_pull)) * (1.0 - frac)
    return {t: mean + (e - mean) * (1.0 - pull) for t, e in elos.items()}

_RNG = random.Random(0)
_NP_RNG = np.random.RandomState(0)

# =============================================================================
# TEAMS & ELOS
# =============================================================================
SCOTTISH_TEAMS = {
    "Celtic": 1676, "Rangers": 1633, "Hearts": 1567, "Dundee": 1412,
    "St Johnstone": 1364, "Dundee United": 1425, "St. Mirren": 1362,
    "Aberdeen": 1377, "Motherwell": 1484, "Hibernian": 1467,
    "Falkirk": 1389, "Kilmarnock": 1374,
}

# =============================================================================
# ACTUAL RESULTS (Matchweeks 1–9, all 54 matches played)
# =============================================================================
ACTUAL_RESULTS = {
    ("Dundee United", "Rangers"): (1, 1),
    ("Falkirk", "St. Mirren"): (0, 2),
    ("Aberdeen", "Hearts"): (2, 1),
    ("St Johnstone", "Kilmarnock"): (4, 3),
    ("Hibernian", "Motherwell"): (1, 2),
    ("Celtic", "Dundee"): (1, 0),
    ("Dundee", "Aberdeen"): (2, 0),
    ("St. Mirren", "St Johnstone"): (1, 0),
    ("Kilmarnock", "Celtic"): (1, 5),
    ("Hearts", "Dundee United"): (4, 0),
    ("Motherwell", "Falkirk"): (0, 0),
    ("Rangers", "Hibernian"): (1, 2),
    ("Dundee United", "Dundee"): (0, 2),
    ("Rangers", "St. Mirren"): (1, 0),
    ("St Johnstone", "Celtic"): (0, 1),
    ("Falkirk", "Hearts"): (2, 1),
    ("Hibernian", "Kilmarnock"): (0, 1),
    ("Motherwell", "Aberdeen"): (0, 4),
    ("Celtic", "Falkirk"): (2, 1),
    ("Hearts", "St Johnstone"): (2, 1),
    ("Kilmarnock", "Dundee United"): (0, 4),
    ("Aberdeen", "Rangers"): (0, 1),
    ("Dundee", "Hibernian"): (1, 2),
    ("St. Mirren", "Motherwell"): (3, 3),
    ("Celtic", "Aberdeen"): (3, 0),
    ("Dundee", "St Johnstone"): (1, 1),
    ("Kilmarnock", "St. Mirren"): (0, 1),
    ("Motherwell", "Dundee United"): (3, 0),
    ("Falkirk", "Rangers"): (1, 2),
    ("Hibernian", "Hearts"): (1, 3),
    ("Aberdeen", "Kilmarnock"): (0, 0),
    ("Dundee United", "Falkirk"): (1, 1),
    ("Rangers", "Motherwell"): (1, 0),
    ("St. Mirren", "Celtic"): (1, 2),
    ("Hearts", "Dundee"): (2, 1),
    ("St Johnstone", "Hibernian"): (2, 1),
    ("Celtic", "Rangers"): (0, 1),
    ("Dundee", "Motherwell"): (2, 1),
    ("Hibernian", "Aberdeen"): (1, 1),
    ("St Johnstone", "Falkirk"): (1, 1),
    ("St. Mirren", "Dundee United"): (0, 3),
    ("Kilmarnock", "Hearts"): (1, 1),
    ("Motherwell", "Celtic"): (0, 2),
    ("Aberdeen", "St Johnstone"): (0, 1),
    ("Dundee United", "Hibernian"): (1, 0),
    ("Falkirk", "Dundee"): (1, 2),
    ("Hearts", "St. Mirren"): (5, 0),
    ("Rangers", "Kilmarnock"): (3, 1),
    ("Dundee", "Rangers"): (2, 2),
    ("Aberdeen", "St. Mirren"): (3, 1),
    ("Kilmarnock", "Motherwell"): (3, 2),
    ("Hibernian", "Falkirk"): (1, 2),
    ("St Johnstone", "Dundee United"): (1, 1),
    ("Celtic", "Hearts"): (7, 1),
}

# =============================================================================
# HELPERS
# =============================================================================
def sample_score_from_elos(elo_home, elo_away):
    diff = elo_home - elo_away + HOME_ADVANTAGE_ELO
    lam_h = BASE_HOME_XG * math.exp(XG_ELO_SENSITIVITY * diff)
    lam_a = BASE_AWAY_XG * math.exp(-XG_ELO_SENSITIVITY * diff)
    hg = int(min(_NP_RNG.poisson(lam_h), MAX_GOALS))
    ag = int(min(_NP_RNG.poisson(lam_a), MAX_GOALS))
    return hg, ag

# =============================================================================
# FIXTURE GENERATION
# =============================================================================
def generate_pre_split_fixtures(actual_results):
    """198 fixtures: each pair plays 3 times, actual results preserved."""
    teams = sorted(SCOTTISH_TEAMS.keys())
    fixtures = []
    home_counts = defaultdict(int)

    for i in range(len(teams)):
        for j in range(i + 1, len(teams)):
            a, b = teams[i], teams[j]
            games = []

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


def generate_post_split_fixtures(top6, bottom6, pre_split_home_counts):
    """30 fixtures: each team plays the other 5 in its half once."""
    fixtures = []
    for group in (top6, bottom6):
        for i in range(len(group)):
            for j in range(i + 1, len(group)):
                a, b = group[i], group[j]
                a_home = pre_split_home_counts.get((a, b), 0)
                b_home = pre_split_home_counts.get((b, a), 0)
                fixtures.append((b, a) if a_home > b_home else (a, b))
    _RNG.shuffle(fixtures)
    return fixtures

# =============================================================================
# SINGLE-SEASON SIMULATION
# =============================================================================
def simulate_season(elos, pre_split_fixtures, pre_split_home_counts, actual_results):
    teams = sorted(elos.keys())
    n = len(teams)
    team_to_idx = {t: i for i, t in enumerate(teams)}

    # ---- Pre-split (198 games, vectorised) ----
    elo_arr = np.array([elos[t] for t in teams], dtype=np.float64)
    h_idx = np.array([team_to_idx[h] for h, _ in pre_split_fixtures], dtype=np.int64)
    a_idx = np.array([team_to_idx[a] for _, a in pre_split_fixtures], dtype=np.int64)

    diff = elo_arr[h_idx] - elo_arr[a_idx] + HOME_ADVANTAGE_ELO
    lam_h = BASE_HOME_XG * np.exp(XG_ELO_SENSITIVITY * diff)
    lam_a = BASE_AWAY_XG * np.exp(-XG_ELO_SENSITIVITY * diff)

    hg = _NP_RNG.poisson(lam_h)
    ag = _NP_RNG.poisson(lam_a)
    np.minimum(hg, MAX_GOALS, out=hg)
    np.minimum(ag, MAX_GOALS, out=ag)

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

    # ---- Split (top 6 / bottom 6 by pts, GD, GF) ----
    gd = gf - ga
    tiebreak = _NP_RNG.uniform(0, 0.0001, size=n)
    order = np.lexsort((-tiebreak, gf, gd, pts))[::-1]
    ranked = [teams[i] for i in order]
    top6, bottom6 = ranked[:6], ranked[6:]

    # ---- Post-split (30 games) ----
    post_fixtures = generate_post_split_fixtures(top6, bottom6, pre_split_home_counts)
    for home, away in post_fixtures:
        hg_i, ag_i = sample_score_from_elos(elos[home], elos[away])
        h, a = team_to_idx[home], team_to_idx[away]
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

    gd = gf - ga

    def _rank(group):
        return sorted(
            group,
            key=lambda t: (pts[team_to_idx[t]],
                           gd[team_to_idx[t]],
                           gf[team_to_idx[t]]),
            reverse=True,
        )

    # Bottom-6 teams cannot outrank top-6, even with more points.
    final_ranking = _rank(top6) + _rank(bottom6)
    points_dict = {t: int(pts[team_to_idx[t]]) for t in teams}

    return final_ranking, points_dict, gf, ga

# =============================================================================
# CURRENT TABLE (from played matches)
# =============================================================================
def build_current_table(actual_results, teams):
    tbl = {t: {"P": 0, "W": 0, "D": 0, "L": 0, "GF": 0, "GA": 0, "Pts": 0}
           for t in teams}
    for (h, a), (hg, ag) in actual_results.items():
        tbl[h]["P"] += 1
        tbl[a]["P"] += 1
        tbl[h]["GF"] += hg
        tbl[h]["GA"] += ag
        tbl[a]["GF"] += ag
        tbl[a]["GA"] += hg
        if hg > ag:
            tbl[h]["W"] += 1
            tbl[a]["L"] += 1
            tbl[h]["Pts"] += 3
        elif ag > hg:
            tbl[a]["W"] += 1
            tbl[h]["L"] += 1
            tbl[a]["Pts"] += 3
        else:
            tbl[h]["D"] += 1
            tbl[a]["D"] += 1
            tbl[h]["Pts"] += 1
            tbl[a]["Pts"] += 1
    return tbl

# =============================================================================
# MONTE CARLO
# =============================================================================
def run_simulation(n_sims=NUM_SIMS, seed=None, on_progress=None, is_running=None,
                   snapshot_callback=None, snapshot_every=None):
    if seed is None:
        seed = random.SystemRandom().randint(0, 2**32 - 1)
    _RNG.seed(seed); _NP_RNG.seed(seed)
    pre_split_fixtures, pre_split_home_counts = generate_pre_split_fixtures(ACTUAL_RESULTS)
    teams = sorted(SCOTTISH_TEAMS.keys())
    games_played_all = 54
    total_games_all_comps = 198  # total season games
    preset_mean = sum(SCOTTISH_TEAMS.values()) / len(SCOTTISH_TEAMS)
    sim_elos = regress_elos(SCOTTISH_TEAMS, games_played_all, total_games_all_comps,
                            preset_mean, ELO_MAX_PULL)

    title_counts = Counter(); ucl_counts = Counter(); uecl_counts = Counter()
    relpo_counts = Counter(); releg_counts = Counter()
    points_dist = defaultdict(list)

    if snapshot_every is None:
        snapshot_every = max(1, n_sims // 250)

    completed = 0
    for _ in tqdm(range(n_sims), desc="Scottish Prem", unit="sim", ncols=80,
                  disable=_DISABLE_TQDM):
        if is_running is not None and not is_running():
            break
        ranking, points, _, _ = simulate_season(
            sim_elos, pre_split_fixtures,
            pre_split_home_counts, ACTUAL_RESULTS,
        )
        for pos, team in enumerate(ranking, 1):
            points_dist[team].append(points[team])
            if pos == 1:  title_counts[team] += 1
            if pos <= 2:  ucl_counts[team] += 1
            if pos in (3, 4): uecl_counts[team] += 1
            if pos == 11: relpo_counts[team] += 1
            if pos == 12: releg_counts[team] += 1
        completed += 1
        if on_progress is not None:
            on_progress(completed, n_sims)
        if snapshot_callback is not None and (completed % snapshot_every == 0 or completed == n_sims):
            snapshot_callback(completed, n_sims, {
                "avg_points": {t: float(np.mean(points_dist[t])) if points_dist[t] else 0.0 for t in teams},
                "title_prob": {t: title_counts[t] / completed * 100 for t in teams},
                "ucl_prob":   {t: ucl_counts[t]   / completed * 100 for t in teams},
                "uecl_prob":  {t: uecl_counts[t]  / completed * 100 for t in teams},
                "relpo_prob": {t: relpo_counts[t] / completed * 100 for t in teams},
                "releg_prob": {t: releg_counts[t] / completed * 100 for t in teams},
            })

    n = completed or 1
    return {
        "n_sims": completed,
        "teams": teams,
        "avg_points":  {t: float(np.mean(points_dist[t])) for t in teams},
        "title_prob":  {t: title_counts[t] / n * 100 for t in teams},
        "ucl_prob":    {t: ucl_counts[t]   / n * 100 for t in teams},
        "uecl_prob":   {t: uecl_counts[t]  / n * 100 for t in teams},
        "relpo_prob":  {t: relpo_counts[t] / n * 100 for t in teams},
        "releg_prob":  {t: releg_counts[t] / n * 100 for t in teams},
        "seed": seed,
    }

# =============================================================================
# MAIN
# =============================================================================
if __name__ == "__main__":
    teams = sorted(SCOTTISH_TEAMS.keys())

    # --- Current table ---
    current = build_current_table(ACTUAL_RESULTS, teams)

    print("\nCURRENT SCOTTISH PREMIERSHIP TABLE (from played matches)\n")
    print(f"{'#':<3}{'CLUB':<18}{'P':<4}{'W':<4}{'D':<4}{'L':<4}"
          f"{'GF':<4}{'GA':<4}{'GD':<5}{'PTS':<5}")
    print("-" * 55)

    sorted_current = sorted(
        current.items(),
        key=lambda x: (x[1]["Pts"], x[1]["GF"] - x[1]["GA"], x[1]["GF"]),
        reverse=True,
    )
    for rank, (team, d) in enumerate(sorted_current, 1):
        gd = d["GF"] - d["GA"]
        print(f"{rank:<3}{team:<18}{d['P']:<4}{d['W']:<4}{d['D']:<4}{d['L']:<4}"
              f"{d['GF']:<4}{d['GA']:<4}{gd:<+5}{d['Pts']:<5}")

    # --- Monte Carlo ---
    print(f"\nRunning {NUM_SIMS:,} simulations...\n")
    results = run_simulation(NUM_SIMS)

    # --- Projected final table with European probabilities ---
    print(f"\nPREDICTED FINAL TABLE — averages over {NUM_SIMS:,} simulations\n")
    print(f"{'#':<3}{'CLUB':<18}{'AvgPTS':<9}{'Title%':<9}"
          f"{'UCL%':<9}{'UECL%':<9}{'RelPO%':<9}{'Releg%':<9}")
    print("-" * 75)

    sorted_teams = sorted(
        results["teams"],
        key=lambda t: results["avg_points"][t],
        reverse=True,
    )

    for rank, team in enumerate(sorted_teams, 1):
        print(f"{rank:<3}{team:<18}"
              f"{results['avg_points'][team]:<9.2f}"
              f"{results['title_prob'][team]:<9.2f}"
              f"{results['ucl_prob'][team]:<9.2f}"
              f"{results['uecl_prob'][team]:<9.2f}"
              f"{results['relpo_prob'][team]:<9.2f}"
              f"{results['releg_prob'][team]:<9.2f}")

    print("\nNotes:")
    print("  Title%  = 1st place (UCL Play-off Round; UEL league phase guaranteed if defeated)")
    print("  UCL%    = 1st or 2nd place (1st: Play-off Round; 2nd: Second Qualifying Round)")
    print("  UECL%   = 3rd or 4th place (Second Qualifying Round)")
    print("  RelPO%  = 11th place (relegation play-off)")
    print("  Releg%  = 12th place (automatic relegation)")

    