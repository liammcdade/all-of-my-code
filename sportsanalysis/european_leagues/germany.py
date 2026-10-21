"""
Bundesliga 2026/27 — league simulation.
18 teams, 34 games (double round-robin, no split).
Uses provided Elos and actual results from matchdays 1–6.

Elo handling: CURRENT_ELO is treated as a NOISY mid-season snapshot.
It is regressed heavily toward the league mean at kickoff, and the pull
loosens linearly as teams accumulate games, reaching zero at MD34.
  pull = ELO_MAX_PULL * (1 - games_played / GAMES_PER_TEAM)
"""

import math
import random
import sys
import numpy as np
from collections import defaultdict, Counter
from tqdm import tqdm

_DISABLE_TQDM = getattr(sys, "frozen", False)

# =============================================================================
# CONSTANTS
# =============================================================================
HOME_ADVANTAGE_ELO = 24.0
BASE_HOME_XG = 1.60
BASE_AWAY_XG = 1.15
XG_ELO_SENSITIVITY = 0.002
MAX_GOALS = 10
NUM_SIMS = 2500

ELO_SCALE = 400.0
LEAGUE_AVERAGE_ELO = 1500.0
ELO_MAX_PULL = 1.0                 # heavy pull now → loosens to 0 by MD34
GAMES_PER_TEAM = 34                # per-team fixtures (NOT 306 league-wide)
LEAGUE_TOTAL_FIXTURES = 306        # informational only
_ELO_LN_SCALE = math.log(10.0) / ELO_SCALE


def regress_elos(elos, games_played, total_games, mean, max_pull):
    """Regress each team's Elo toward `mean` by pull = max_pull * (1 - frac).

    At frac=0 (season start) pull = max_pull (max regression).
    At frac=1 (season end)  pull = 0        (no regression).
    `games_played` may be a scalar or a per-team dict.
    """
    out = {}
    for t, e in elos.items():
        n = games_played[t] if isinstance(games_played, dict) else games_played
        if total_games == 0:
            out[t] = e
            continue
        frac = max(0.0, min(1.0, n / total_games))
        pull = max(0.0, min(1.0, max_pull)) * (1.0 - frac)
        out[t] = mean + (e - mean) * (1.0 - pull)
    return out

_RNG = random.Random(0)
_NP_RNG = np.random.RandomState(0)

# =============================================================================
# TEAMS & CURRENT ELOS (after matchday 6)
# =============================================================================
CURRENT_ELO = {
    "Bayern Munich": 2086,
    "Borussia Dortmund": 1888,
    "Freiburg": 1794,
    "Leverkusen": 1904,
    "Mainz": 1736,
    "SV 07 Elversberg": 1640,
    "RB Leipzig": 1803,
    "Bremen": 1685,
    "Hamburg": 1678,
    "Augsburg": 1713,
    "Frankfurt": 1702,
    "Köln": 1630,
    "VfB Stuttgart": 1796,
    "Hoffenheim": 1700,
    "Schalke 04": 1619,
    "SC Paderborn 07": 1557,
    "Union Berlin": 1640,
    "Mönchengladbach": 1616,
}

TEAMS = sorted(CURRENT_ELO.keys())

# =============================================================================
# ACTUAL RESULTS — Matchdays 1–6 (54 matches)
# =============================================================================
PLAYED_MATCHES = [
    # Matchday 1
    ("Bayern Munich", "VfB Stuttgart", 5, 1),
    ("SV 07 Elversberg", "Leverkusen", 3, 2),
    ("Köln", "Hoffenheim", 3, 2),
    ("Mainz", "SC Paderborn 07", 0, 0),
    ("RB Leipzig", "Mönchengladbach", 3, 0),
    ("Union Berlin", "Frankfurt", 3, 3),
    ("Borussia Dortmund", "Hamburg", 2, 0),
    ("Freiburg", "Bremen", 4, 1),
    ("Augsburg", "Schalke 04", 3, 0),

    # Matchday 2
    ("VfB Stuttgart", "Köln", 4, 1),
    ("Hoffenheim", "Borussia Dortmund", 2, 3),
    ("Leverkusen", "Union Berlin", 4, 0),
    ("Mönchengladbach", "SV 07 Elversberg", 3, 4),
    ("SC Paderborn 07", "Freiburg", 0, 1),
    ("Bremen", "RB Leipzig", 3, 1),
    ("Schalke 04", "Bayern Munich", 0, 0),
    ("Hamburg", "Mainz", 0, 5),
    ("Frankfurt", "Augsburg", 1, 4),

    # Matchday 3
    ("Union Berlin", "Schalke 04", 1, 3),
    ("Borussia Dortmund", "SC Paderborn 07", 3, 0),
    ("Augsburg", "Leverkusen", 2, 2),
    ("Freiburg", "Mönchengladbach", 5, 0),
    ("Mainz", "Frankfurt", 1, 3),
    ("Hoffenheim", "VfB Stuttgart", 2, 1),
    ("Köln", "Bremen", 1, 1),
    ("RB Leipzig", "Hamburg", 5, 0),
    ("SV 07 Elversberg", "Bayern Munich", 1, 2),

    # Matchday 4
    ("Bayern Munich", "Union Berlin", 7, 0),
    ("Frankfurt", "Freiburg", 2, 2),
    ("Hamburg", "Köln", 2, 1),
    ("Mönchengladbach", "Mainz", 3, 4),
    ("Bremen", "Augsburg", 3, 2),
    ("VfB Stuttgart", "Borussia Dortmund", 0, 1),
    ("Leverkusen", "RB Leipzig", 2, 0),
    ("Schalke 04", "SV 07 Elversberg", 0, 0),
    ("SC Paderborn 07", "Hoffenheim", 3, 1),

    # Matchday 5
    ("Borussia Dortmund", "Bremen", 2, 2),
    ("Augsburg", "Bayern Munich", 2, 2),
    ("Mainz", "Leverkusen", 3, 4),
    ("Hoffenheim", "Hamburg", 2, 3),
    ("SC Paderborn 07", "VfB Stuttgart", 0, 2),
    ("Union Berlin", "SV 07 Elversberg", 1, 0),
    ("RB Leipzig", "Frankfurt", 6, 0),
    ("Köln", "Mönchengladbach", 2, 1),
    ("Freiburg", "Schalke 04", 2, 1),

    # Matchday 6
    ("Frankfurt", "Köln", 1, 0),
    ("SV 07 Elversberg", "Augsburg", 4, 3),
    ("Hamburg", "VfB Stuttgart", 1, 0),
    ("Schalke 04", "Mainz", 0, 1),
    ("Union Berlin", "Borussia Dortmund", 0, 0),
    ("Bremen", "SC Paderborn 07", 2, 2),
    ("Bayern Munich", "RB Leipzig", 6, 1),
    ("Leverkusen", "Freiburg", 2, 1),
    ("Mönchengladbach", "Hoffenheim", 1, 2),
]

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


def apply_result(tbl, home, away, hg, ag):
    tbl[home]["P"] += 1
    tbl[away]["P"] += 1
    tbl[home]["GF"] += hg
    tbl[home]["GA"] += ag
    tbl[away]["GF"] += ag
    tbl[away]["GA"] += hg

    if hg > ag:
        tbl[home]["W"] += 1
        tbl[away]["L"] += 1
        tbl[home]["Pts"] += 3
    elif ag > hg:
        tbl[away]["W"] += 1
        tbl[home]["L"] += 1
        tbl[away]["Pts"] += 3
    else:
        tbl[home]["D"] += 1
        tbl[away]["D"] += 1
        tbl[home]["Pts"] += 1
        tbl[away]["Pts"] += 1

# =============================================================================
# CURRENT TABLE
# =============================================================================
def build_current_table():
    tbl = {
        t: {"P": 0, "W": 0, "D": 0, "L": 0, "GF": 0, "GA": 0, "Pts": 0}
        for t in TEAMS
    }
    for home, away, hg, ag in PLAYED_MATCHES:
        apply_result(tbl, home, away, hg, ag)
    return tbl

# =============================================================================
# REMAINING FIXTURES
# =============================================================================
def generate_remaining_fixtures():
    played = {(h, a): (hg, ag) for h, a, hg, ag in PLAYED_MATCHES}
    remaining = []

    for i in range(len(TEAMS)):
        for j in range(i + 1, len(TEAMS)):
            a, b = TEAMS[i], TEAMS[j]

            if (a, b) in played:
                remaining.append((b, a))
            elif (b, a) in played:
                remaining.append((a, b))
            else:
                remaining.append((a, b))
                remaining.append((b, a))

    _RNG.shuffle(remaining)
    return remaining

# =============================================================================
# SINGLE-SEASON SIMULATION
# =============================================================================
def simulate_season(remaining_fixtures, current, elos):
    tbl = {t: current[t].copy() for t in TEAMS}

    for home, away in remaining_fixtures:
        hg, ag = sample_score_from_elos(elos[home], elos[away])
        apply_result(tbl, home, away, hg, ag)

    ranking = sorted(
        tbl.items(),
        key=lambda x: (x[1]["Pts"], x[1]["GF"] - x[1]["GA"], x[1]["GF"]),
        reverse=True,
    )

    points = {t: tbl[t]["Pts"] for t in TEAMS}
    return [team for team, _ in ranking], points

# =============================================================================
# MONTE CARLO
# =============================================================================
def run_simulation(n_sims=NUM_SIMS, seed=None, on_progress=None, is_running=None,
                   snapshot_callback=None, snapshot_every=None):
    if seed is None:
        seed = random.SystemRandom().randint(0, 2**32 - 1)
    _RNG.seed(seed)
    _NP_RNG.seed(seed)

    current = build_current_table()
    remaining = generate_remaining_fixtures()

    # --- Regress Elos: heavy pull now, loosening each game ---
    games_played = {t: current[t]["P"] for t in TEAMS}   # all 6 right now
    mean_elo = sum(CURRENT_ELO.values()) / len(CURRENT_ELO)
    elos = regress_elos(
        CURRENT_ELO,
        games_played=games_played,
        total_games=GAMES_PER_TEAM,   # 34, NOT 306
        mean=mean_elo,
        max_pull=ELO_MAX_PULL,        # 1.0 -> pull 0.824 at MD6
    )

    top4 = Counter()
    title = Counter()
    fifth = Counter()
    sixth = Counter()
    relpo = Counter()
    releg = Counter()
    points_dist = defaultdict(list)

    if snapshot_every is None:
        snapshot_every = max(1, n_sims // 250)

    completed = 0
    for _ in tqdm(range(n_sims), desc="Bundesliga", unit="sim", ncols=80,
                  disable=_DISABLE_TQDM):
        if is_running is not None and not is_running():
            break
        # *** FIX: use regressed `elos`, NOT raw `CURRENT_ELO` ***
        ranking, points = simulate_season(remaining, current, elos)
        for pos, team in enumerate(ranking, 1):
            points_dist[team].append(points[team])
            if pos == 1:
                title[team] += 1
            if pos <= 4:
                top4[team] += 1
            elif pos == 5:
                fifth[team] += 1
            elif pos == 6:
                sixth[team] += 1
            if pos == 16:
                relpo[team] += 1
            if pos >= 17:
                releg[team] += 1
        completed += 1
        if on_progress is not None:
            on_progress(completed, n_sims)
        if snapshot_callback is not None and (completed % snapshot_every == 0 or completed == n_sims):
            snapshot_callback(completed, n_sims, {
                "avg_points": {t: float(np.mean(points_dist[t])) if points_dist[t] else 0.0 for t in TEAMS},
                "title_prob": {t: title[t] / completed * 100 for t in TEAMS},
                "top4_prob":  {t: top4[t]  / completed * 100 for t in TEAMS},
                "fifth_prob": {t: fifth[t] / completed * 100 for t in TEAMS},
                "sixth_prob": {t: sixth[t] / completed * 100 for t in TEAMS},
                "relpo_prob": {t: relpo[t] / completed * 100 for t in TEAMS},
                "releg_prob": {t: releg[t] / completed * 100 for t in TEAMS},
            })

    n = completed or 1
    return {
        "n_sims": completed,
        "teams": TEAMS,
        "avg_points": {t: float(np.mean(points_dist[t])) for t in TEAMS},
        "title_prob": {t: title[t] / n * 100 for t in TEAMS},
        "top4_prob":  {t: top4[t]  / n * 100 for t in TEAMS},
        "fifth_prob": {t: fifth[t] / n * 100 for t in TEAMS},
        "sixth_prob": {t: sixth[t] / n * 100 for t in TEAMS},
        "relpo_prob": {t: relpo[t] / n * 100 for t in TEAMS},
        "releg_prob": {t: releg[t] / n * 100 for t in TEAMS},
        "regressed_elos": elos,
        "seed": seed,
    }

# =============================================================================
# MAIN
# =============================================================================
if __name__ == "__main__":
    current = build_current_table()

    # --- Current table ---
    print("\nCURRENT BUNDESLIGA TABLE (from played matches)\n")
    print(f"{'#':<3}{'CLUB':<22}{'P':<4}{'W':<4}{'D':<4}{'L':<4}"
          f"{'GF':<4}{'GA':<4}{'GD':<5}{'PTS':<5}")
    print("-" * 60)

    sorted_current = sorted(
        current.items(),
        key=lambda x: (x[1]["Pts"], x[1]["GF"] - x[1]["GA"], x[1]["GF"]),
        reverse=True,
    )
    for rank, (team, d) in enumerate(sorted_current, 1):
        gd = d["GF"] - d["GA"]
        print(f"{rank:<3}{team:<22}{d['P']:<4}{d['W']:<4}{d['D']:<4}{d['L']:<4}"
              f"{d['GF']:<4}{d['GA']:<4}{gd:<+5}{d['Pts']:<5}")

    # --- Monte Carlo ---
    print(f"\nRunning {NUM_SIMS:,} simulations...\n")
    results = run_simulation(NUM_SIMS)

    # --- Projected final table ---
    print(f"\nPREDICTED FINAL TABLE — averages over {NUM_SIMS:,} simulations\n")
    print(f"{'#':<3}{'CLUB':<22}{'AvgPTS':<9}{'Title%':<8}{'Top4%':<8}"
          f"{'5th%':<8}{'6th%':<8}{'RelPO%':<8}{'Releg%':<8}")
    print("-" * 84)

    sorted_teams = sorted(
        results["teams"],
        key=lambda t: results["avg_points"][t],
        reverse=True,
    )

    for rank, team in enumerate(sorted_teams, 1):
        print(f"{rank:<3}{team:<22}"
              f"{results['avg_points'][team]:<9.2f}"
              f"{results['title_prob'][team]:<8.2f}"
              f"{results['top4_prob'][team]:<8.2f}"
              f"{results['fifth_prob'][team]:<8.2f}"
              f"{results['sixth_prob'][team]:<8.2f}"
              f"{results['relpo_prob'][team]:<8.2f}"
              f"{results['releg_prob'][team]:<8.2f}")

    print("\nNotes:")
    print("  Title% = 1st place (Bundesliga champion)")
    print("  Top4%  = 1st–4th (UEFA Champions League places)")
    print("  5th%   = 5th place (UEFA Europa League)")
    print("  6th%   = 6th place (UEFA Conference League)")
    print("  RelPO% = 16th place (relegation play-off)")
    print("  Releg% = 17th–18th (automatic relegation)")

    print(f"\nSeed: {results['seed']}")