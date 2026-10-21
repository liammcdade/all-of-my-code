import random
import math
import sys
import numpy as np
from collections import defaultdict, Counter
from tqdm import tqdm

_DISABLE_TQDM = getattr(sys, "frozen", False)  # no bar needed inside the GUI

# ============================================================
# TEAMS / STARTING ELOS
# ============================================================
TEAMS = [
    "Inter", "Lazio", "Roma", "Milan", "Como", "Frosinone", "Cagliari",
    "Juventus", "Napoli", "Atalanta", "Lecce", "Sassuolo", "Torino",
    "Bologna", "Monza", "Parma", "Udinese", "Genoa", "Fiorentina", "Venezia"
]

start_elo = {
    "Inter": 1945, "Lazio": 1752, "Roma": 1839, "Milan": 1821,
    "Como": 1806, "Frosinone": 1576, "Cagliari": 1635, "Juventus": 1838,
    "Napoli": 1835, "Atalanta": 1813, "Lecce": 1619, "Sassuolo": 1674,
    "Torino": 1676, "Bologna": 1761, "Monza": 1523, "Parma": 1651,
    "Udinese": 1693, "Genoa": 1656, "Fiorentina": 1726, "Venezia": 1549,
}

HOME_ADVANTAGE = 24
K_FACTOR = 30


def regress_elos(elos, games_played, total_games, mean, max_pull):
    if total_games == 0:
        return dict(elos)
    frac = max(0.0, min(1.0, games_played / total_games))
    pull = max(0.0, min(1.0, max_pull)) * (1.0 - frac)
    return {t: mean + (e - mean) * (1.0 - pull) for t, e in elos.items()}

# ============================================================
# PLAYED MATCHES
# ============================================================
PLAYED_MATCHES = [
    ("Inter", "Monza", 4, 1),
    ("Udinese", "Como", 1, 1),
    ("Genoa", "Napoli", 0, 2),
    ("Parma", "Cagliari", 0, 1),
    ("Frosinone", "Juventus", 0, 1),
    ("Venezia", "Lecce", 0, 2),
    ("Atalanta", "Sassuolo", 2, 1),
    ("Torino", "Milan", 1, 2),
    ("Bologna", "Lazio", 0, 1),
    ("Roma", "Fiorentina", 4, 0),
    ("Milan", "Venezia", 2, 0),
    ("Fiorentina", "Frosinone", 0, 3),
    ("Monza", "Udinese", 2, 3),
    ("Sassuolo", "Torino", 2, 1),
    ("Juventus", "Parma", 2, 0),
    ("Napoli", "Como", 1, 2),
    ("Cagliari", "Inter", 0, 1),
    ("Lazio", "Genoa", 1, 0),
    ("Lecce", "Roma", 0, 4),
    ("Atalanta", "Bologna", 1, 0),
    ("Genoa", "Como", 1, 4),
    ("Fiorentina", "Torino", 1, 2),
    ("Inter", "Napoli", 3, 2),
    ("Roma", "Atalanta", 2, 1),
    ("Frosinone", "Venezia", 3, 2),
    ("Parma", "Monza", 1, 1),
    ("Bologna", "Sassuolo", 2, 2),
    ("Juventus", "Milan", 1, 1),
    ("Cagliari", "Lecce", 1, 0),
    ("Udinese", "Lazio", 1, 2),
    ("Venezia", "Fiorentina", 2, 4),
    ("Genoa", "Frosinone", 1, 1),
    ("Lazio", "Milan", 2, 2),
    ("Atalanta", "Cagliari", 1, 2),
    ("Lecce", "Monza", 3, 2),
    ("Napoli", "Bologna", 1, 0),
    ("Sassuolo", "Juventus", 3, 2),
    ("Como", "Parma", 2, 1),
    ("Torino", "Roma", 0, 2),
    ("Inter", "Udinese", 5, 3),
    ("Monza", "Sassuolo", 2, 1),
    ("Bologna", "Torino", 1, 1),
    ("Udinese", "Cagliari", 0, 1),
    ("Roma", "Inter", 2, 2),
    ("Venezia", "Lazio", 0, 2),
    ("Fiorentina", "Napoli", 1, 1),
    ("Frosinone", "Como", 2, 0),
    ("Parma", "Genoa", 2, 1),
    ("Juventus", "Atalanta", 2, 0),
    ("Milan", "Lecce", 3, 0),
    ("Genoa", "Fiorentina", 2, 1),
    ("Inter", "Parma", 3, 0),
    ("Napoli", "Frosinone", 3, 0),
    ("Como", "Roma", 0, 0),
    ("Lazio", "Monza", 3, 1),
    ("Lecce", "Bologna", 1, 2),
    ("Sassuolo", "Milan", 1, 1),
    ("Cagliari", "Juventus", 1, 1),
    ("Atalanta", "Venezia", 3, 1),
    ("Torino", "Udinese", 2, 1),
    ("Frosinone", "Sassuolo", 4, 2),
    ("Venezia", "Napoli", 1, 0),
    ("Bologna", "Inter", 1, 3),
    ("Roma", "Genoa", 2, 0),
    ("Udinese", "Lecce", 0, 3),
    ("Fiorentina", "Como", 1, 3),
    ("Milan", "Atalanta", 3, 2),
    ("Juventus", "Lazio", 0, 3),
]

DRAW_RATE = sum(1 for _, _, hg, ag in PLAYED_MATCHES if hg == ag) / len(PLAYED_MATCHES)

# ============================================================
# HELPERS
# ============================================================
def poisson(lam):
    if lam < 0:
        lam = 0
    L = math.exp(-lam)
    k = 0
    p = 1.0
    while True:
        k += 1
        p *= random.random()
        if p <= L:
            return k - 1

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

def elo_update(ratings, home, away, hg, ag):
    h_elo = ratings[home]
    a_elo = ratings[away]

    exp_h = 1 / (1 + 10 ** ((a_elo - h_elo - HOME_ADVANTAGE) / 400))
    exp_a = 1 - exp_h

    if hg > ag:
        act_h, act_a = 1.0, 0.0
    elif hg < ag:
        act_h, act_a = 0.0, 1.0
    else:
        act_h, act_a = 0.5, 0.5

    gd = abs(hg - ag)
    if gd <= 1:
        mult = 1.0
    elif gd == 2:
        mult = 1.5
    elif gd == 3:
        mult = 1.75
    else:
        mult = 1.75 + (gd - 3) / 8

    dh = K_FACTOR * mult * (act_h - exp_h)
    da = K_FACTOR * mult * (act_a - exp_a)

    ratings[home] += dh
    ratings[away] += da
    return dh, da

def simulate_match(ratings, home, away):
    shift = (ratings[home] + HOME_ADVANTAGE - ratings[away]) / 400

    p_h = 0.471 + shift * 0.20
    p_a = 0.353 - shift * 0.20
    p_d = DRAW_RATE

    total = p_h + p_d + p_a
    p_h /= total
    p_d /= total
    p_a /= total

    r = random.random()
    if r < p_h:
        hg, ag = poisson(1.8), poisson(0.9)
    elif r < p_h + p_d:
        hg = ag = poisson(1.3)
    else:
        hg, ag = poisson(0.9), poisson(1.8)
    return hg, ag

# ============================================================
# BUILD CURRENT TABLE + CURRENT ELO FROM PLAYED MATCHES
# ============================================================
def build_current_from_played():
    tbl = {
        t: {"P": 0, "W": 0, "D": 0, "L": 0, "GF": 0, "GA": 0, "Pts": 0}
        for t in TEAMS
    }
    ratings = start_elo.copy()
    form = {t: [] for t in TEAMS}

    for home, away, hg, ag in PLAYED_MATCHES:
        apply_result(tbl, home, away, hg, ag)
        dh, da = elo_update(ratings, home, away, hg, ag)
        form[home].append(dh)
        form[away].append(da)

    return tbl, ratings, form

current, current_elo, current_form = build_current_from_played()

# ============================================================
# GENERATE REMAINING FIXTURES
# ============================================================
def generate_remaining_fixtures():
    counts = Counter()
    for h, a, _, _ in PLAYED_MATCHES:
        counts[h] += 1
        counts[a] += 1

    # Teams with a game in hand
    min_p = min(counts[t] for t in TEAMS)
    short = [t for t in TEAMS if counts[t] == min_p]

    fixtures = []

    # Catch-up matches among teams with fewer games
    random.shuffle(short)
    for i in range(0, len(short), 2):
        a, b = short[i], short[i + 1]
        fixtures.append((a, b) if random.random() < 0.5 else (b, a))

    # Remaining full rounds: total season = 380 matches
    total_needed = 380 - len(PLAYED_MATCHES) - len(fixtures)
    rounds = total_needed // 10  # 10 matches per round

    pool = TEAMS[:]
    for _ in range(rounds):
        random.shuffle(pool)
        for i in range(0, 20, 2):
            a, b = pool[i], pool[i + 1]
            fixtures.append((a, b) if random.random() < 0.5 else (b, a))

    return fixtures

# ============================================================
# MONTE CARLO
# ============================================================
N_SIMS = 2500


def run_simulation(n_sims=N_SIMS, seed=None, on_progress=None, is_running=None,
                   snapshot_callback=None, snapshot_every=None):
    # Only seed once if provided, not each iteration
    if seed is not None:
        random.seed(seed)

    # Build base state once
    tbl_base, elo_base, _ = build_current_from_played()

    games_played_all = len(PLAYED_MATCHES)
    total_games_all_comps = 20 * 19  # 380 total games in season
    preset_mean = sum(start_elo.values()) / len(start_elo)
    sim_elos = regress_elos(elo_base, games_played_all, total_games_all_comps,
                            preset_mean, 1.0)

    top4 = Counter(); title = Counter(); fifth = Counter()
    sixth = Counter(); releg = Counter()
    final_Pts = defaultdict(list)

    if snapshot_every is None:
        snapshot_every = max(1, n_sims // 250)

    completed = 0
    for _ in tqdm(range(n_sims), desc="Serie A", unit="sim", ncols=80,
                  disable=_DISABLE_TQDM):
        if is_running is not None and not is_running():
            break
        tbl = {t: tbl_base[t].copy() for t in TEAMS}
        ratings = sim_elos.copy()
        fixtures = generate_remaining_fixtures()

        for home, away in fixtures:
            hg, ag = simulate_match(ratings, home, away)
            elo_update(ratings, home, away, hg, ag)
            apply_result(tbl, home, away, hg, ag)

        ranking = sorted(
            tbl.items(),
            key=lambda x: (x[1]["Pts"], x[1]["GF"] - x[1]["GA"]),
            reverse=True,
        )
        for pos, (team, data) in enumerate(ranking, 1):
            final_Pts[team].append(data["Pts"])
            if pos == 1:  title[team] += 1
            if pos <= 4:  top4[team] += 1
            elif pos == 5: fifth[team] += 1
            elif pos == 6: sixth[team] += 1
            if pos >= 18: releg[team] += 1
        completed += 1
        if on_progress is not None:
            on_progress(completed, n_sims)
        if snapshot_callback is not None and (completed % snapshot_every == 0 or completed == n_sims):
            snapshot_callback(completed, n_sims, {
                "avg_points": {t: float(np.mean(final_Pts[t])) if final_Pts[t] else 0.0 for t in TEAMS},
                "title_prob": {t: title[t] / completed * 100 for t in TEAMS},
                "top4_prob":  {t: top4[t]  / completed * 100 for t in TEAMS},
                "fifth_prob": {t: fifth[t] / completed * 100 for t in TEAMS},
                "sixth_prob": {t: sixth[t] / completed * 100 for t in TEAMS},
                "releg_prob": {t: releg[t] / completed * 100 for t in TEAMS},
            })

    n = completed or 1
    return {
        "n_sims": completed,
        "teams": TEAMS,
        "avg_points":  {t: float(np.mean(final_Pts[t])) for t in TEAMS},
        "title_prob":  {t: title[t] / n * 100 for t in TEAMS},
        "top4_prob":   {t: top4[t]  / n * 100 for t in TEAMS},
        "fifth_prob":  {t: fifth[t] / n * 100 for t in TEAMS},
        "sixth_prob":  {t: sixth[t] / n * 100 for t in TEAMS},
        "releg_prob":  {t: releg[t] / n * 100 for t in TEAMS},
    }


if __name__ == "__main__":
    results = run_simulation()