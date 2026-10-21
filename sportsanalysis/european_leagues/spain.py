import random
import math
import sys
import numpy as np
from collections import defaultdict, Counter
from tqdm import tqdm

_DISABLE_TQDM = getattr(sys, "frozen", False)  # no bar needed inside the GUI

# ============================================================
# LA LIGA — TEAMS / STARTING & CURRENT ELOS
# ============================================================
TEAMS = [
    "Barcelona", "Atletico Madrid", "Real Madrid", "Real Betis",
    "Real Sociedad", "Sevilla", "Alavés", "Celta Vigo", "Deportivo",
    "Osasuna", "Athletic Club", "Villarreal", "Espanyol",
    "Rayo Vallecano", "Getafe", "Racing Santander", "Levante",
    "Elche CF", "Valencia", "Málaga",
]

start_elo = {
    "Barcelona": 1996, "Atletico Madrid": 1854, "Real Madrid": 1977,
    "Real Betis": 1784, "Real Sociedad": 1704, "Sevilla": 1650,
    "Alavés": 1670, "Celta Vigo": 1741, "Deportivo": 1577,
    "Osasuna": 1677, "Athletic Club": 1698, "Villarreal": 1780,
    "Espanyol": 1653, "Rayo Vallecano": 1745, "Getafe": 1692,
    "Racing Santander": 1560, "Levante": 1674, "Elche CF": 1653,
    "Valencia": 1722, "Málaga": 1547,
}

# Elos after the matches in your file
current_elo = {
    "Barcelona": 2065, "Atletico Madrid": 1908, "Real Madrid": 2012,
    "Real Betis": 1856, "Real Sociedad": 1742, "Sevilla": 1699,
    "Alavés": 1683, "Celta Vigo": 1717, "Deportivo": 1636,
    "Osasuna": 1681, "Athletic Club": 1718, "Villarreal": 1777,
    "Espanyol": 1649, "Rayo Vallecano": 1731, "Getafe": 1657,
    "Racing Santander": 1583, "Levante": 1680, "Elche CF": 1663,
    "Valencia": 1690, "Málaga": 1532,
}

HOME_ADVANTAGE = 24
K_FACTOR = 30
ELO_SCALE = 400.0
LEAGUE_AVERAGE_ELO = 1500.0
ELO_MAX_PULL = 1.0
LEAGUE_TOTAL_FIXTURES = 342  # 18 teams × 38 games / 2
_ELO_LN_SCALE = math.log(10.0) / ELO_SCALE


def regress_elos(elos, games_played, total_games, mean, max_pull):
    if total_games == 0:
        return dict(elos)
    frac = max(0.0, min(1.0, games_played / total_games))
    pull = max(0.0, min(1.0, max_pull)) * (1.0 - frac)
    return {t: mean + (e - mean) * (1.0 - pull) for t, e in elos.items()}

# ============================================================
# PLAYED MATCHES — La Liga results from your file
# (Rayo Vallecano vs Athletic Club pp. is skipped)
# ============================================================
PLAYED_MATCHES = [
    ("Alavés", "Getafe", 3, 0),
    ("Sevilla", "Rayo Vallecano", 2, 1),
    ("Racing Santander", "Villarreal", 2, 2),
    ("Espanyol", "Levante", 3, 0),
    ("Deportivo", "Elche CF", 1, 1),
    ("Atletico Madrid", "Málaga", 2, 0),
    ("Rayo Vallecano", "Alavés", 1, 1),
    ("Real Betis", "Real Sociedad", 1, 0),
    ("Athletic Club", "Sevilla", 1, 3),
    ("Valencia", "Celta Vigo", 0, 0),
    ("Espanyol", "Real Madrid", 1, 2),
    ("Atletico Madrid", "Villarreal", 2, 2),
    ("Getafe", "Racing Santander", 1, 0),
    ("Elche CF", "Barcelona", 0, 5),
    ("Osasuna", "Levante", 0, 0),
    ("Málaga", "Deportivo", 1, 1),
    ("Valencia", "Real Betis", 0, 1),
    ("Real Madrid", "Real Sociedad", 4, 1),
    ("Celta Vigo", "Osasuna", 1, 2),
    ("Barcelona", "Athletic Club", 2, 0),
    ("Racing Santander", "Elche CF", 3, 2),
    ("Alavés", "Villarreal", 1, 0),
    ("Levante", "Real Betis", 5, 2),
    ("Real Sociedad", "Espanyol", 2, 1),
    ("Sevilla", "Atletico Madrid", 1, 3),
    ("Real Madrid", "Málaga", 4, 0),
    ("Deportivo", "Valencia", 3, 1),
    ("Celta Vigo", "Athletic Club", 0, 2),
    ("Osasuna", "Getafe", 1, 0),
    ("Barcelona", "Rayo Vallecano", 5, 2),
    ("Real Sociedad", "Celta Vigo", 0, 0),
    ("Real Betis", "Real Madrid", 1, 0),
    ("Athletic Club", "Atletico Madrid", 3, 0),
    ("Rayo Vallecano", "Racing Santander", 3, 2),
    ("Villarreal", "Deportivo", 2, 3),
    ("Valencia", "Barcelona", 0, 5),
    ("Alavés", "Osasuna", 5, 2),
    ("Málaga", "Levante", 0, 0),
    ("Espanyol", "Sevilla", 1, 1),
    ("Getafe", "Celta Vigo", 1, 1),
    ("Elche CF", "Real Sociedad", 2, 3),
    ("Sevilla", "Valencia", 1, 0),
    ("Racing Santander", "Alavés", 2, 1),
    ("Osasuna", "Espanyol", 0, 2),
    ("Athletic Club", "Elche CF", 1, 1),
    ("Real Madrid", "Rayo Vallecano", 4, 1),
    ("Celta Vigo", "Málaga", 1, 1),
    ("Levante", "Barcelona", 2, 4),
    ("Getafe", "Deportivo", 1, 1),
    ("Real Sociedad", "Atletico Madrid", 0, 3),
    ("Villarreal", "Real Betis", 1, 2),
    ("Rayo Vallecano", "Espanyol", 2, 1),
    ("Alavés", "Valencia", 0, 1),
    ("Elche CF", "Real Madrid", 2, 3),
    ("Atletico Madrid", "Osasuna", 4, 0),
    ("Deportivo", "Sevilla", 0, 1),
    ("Barcelona", "Racing Santander", 7, 2),
    ("Real Betis", "Getafe", 1, 0),
    ("Málaga", "Villarreal", 1, 3),
    ("Espanyol", "Elche CF", 1, 3),
    ("Osasuna", "Rayo Vallecano", 1, 1),
    ("Athletic Club", "Alavés", 0, 0),
    ("Celta Vigo", "Racing Santander", 5, 0),
    ("Sevilla", "Barcelona", 1, 3),
    ("Getafe", "Málaga", 1, 0),
    ("Atletico Madrid", "Real Madrid", 2, 1),
    ("Deportivo", "Real Betis", 1, 1),
    ("Villarreal", "Levante", 3, 1),
    ("Valencia", "Real Sociedad", 2, 3),
    ("Málaga", "Espanyol", 1, 1),
    ("Alavés", "Atletico Madrid", 1, 2),
    ("Barcelona", "Getafe", 3, 0),
    ("Real Madrid", "Villarreal", 1, 0),
    ("Elche CF", "Celta Vigo", 0, 0),
    ("Real Sociedad", "Deportivo", 3, 2),
    ("Real Betis", "Osasuna", 5, 2),
    ("Racing Santander", "Valencia", 2, 2),
    ("Levante", "Sevilla", 3, 3),
    ("Deportivo", "Levante", 1, 1),
    ("Espanyol", "Atletico Madrid", 0, 1),
    ("Villarreal", "Elche CF", 0, 0),
    ("Real Betis", "Barcelona", 2, 5),
    ("Valencia", "Athletic Club", 0, 0),
    ("Osasuna", "Racing Santander", 2, 0),
    ("Celta Vigo", "Alavés", 2, 1),
    ("Málaga", "Real Sociedad", 2, 5),
    ("Real Madrid", "Sevilla", 4, 1),
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
# CURRENT TABLE FROM PLAYED MATCHES
# ============================================================
def build_current_table():
    tbl = {
        t: {"P": 0, "W": 0, "D": 0, "L": 0, "GF": 0, "GA": 0, "Pts": 0}
        for t in TEAMS
    }
    for home, away, hg, ag in PLAYED_MATCHES:
        apply_result(tbl, home, away, hg, ag)
    return tbl

current = build_current_table()

# ============================================================
# REMAINING FIXTURES — generated so every team reaches 38 games
# ============================================================
def generate_remaining_fixtures():
    counts = Counter()
    for h, a, _, _ in PLAYED_MATCHES:
        counts[h] += 1
        counts[a] += 1

    slots = []
    for t in TEAMS:
        needed = 38 - counts[t]
        slots.extend([t] * needed)

    random.shuffle(slots)
    fixtures = []

    i = 0
    while i < len(slots):
        a = slots[i]
        b = slots[i + 1]

        # avoid pairing a team with itself
        if a == b:
            for k in range(len(slots)):
                if k not in (i, i + 1) and slots[k] != a:
                    slots[i + 1], slots[k] = slots[k], slots[i + 1]
                    b = slots[i + 1]
                    break

        if random.random() < 0.5:
            fixtures.append((a, b))
        else:
            fixtures.append((b, a))

        i += 2

    return fixtures

# ============================================================
# MONTE CARLO / DASHBOARD ENTRY POINT
# ============================================================
N_SIMS = 2500

# ============================================================
# OUTPUT: PREDICTED TABLE
# ============================================================
def print_predicted_table():
    title_counts = Counter(); top4_counts = Counter(); fifth_counts = Counter()
    sixth_counts = Counter(); releg_counts = Counter()
    final_Pts = defaultdict(list)

    for _ in tqdm(range(N_SIMS), desc="La Liga", unit="sim", ncols=80,
                  disable=_DISABLE_TQDM):
        tbl = {t: current[t].copy() for t in TEAMS}
        ratings = current_elo.copy()
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
            if pos == 1:  title_counts[team] += 1
            if pos <= 4:  top4_counts[team] += 1
            elif pos == 5: fifth_counts[team] += 1
            elif pos == 6: sixth_counts[team] += 1
            if pos >= 18: releg_counts[team] += 1

    print(f"\nPREDICTED LA LIGA TABLE — averages over {N_SIMS} simulations\n")
    print(f"{'#':<3}{'CLUB':<18}{'AvgPTS':<9}{'Top4%':<9}{'5th%':<9}{'6th%':<9}{'Releg%':<9}")
    print("-" * 68)

    sorted_teams = sorted(TEAMS, key=lambda t: np.mean(final_Pts[t]), reverse=True)

    for rank, team in enumerate(sorted_teams, 1):
        avg_pts = np.mean(final_Pts[team])
        p_top4 = top4_counts[team] / N_SIMS * 100
        p_5th = fifth_counts[team] / N_SIMS * 100
        p_6th = sixth_counts[team] / N_SIMS * 100
        p_releg = releg_counts[team] / N_SIMS * 100

        print(
            f"{rank:<3}{team:<18}{avg_pts:<9.1f}"
            f"{p_top4:<9.2f}{p_5th:<9.2f}{p_6th:<9.2f}{p_releg:<9.2f}"
        )


# ============================================================
# DASHBOARD ENTRY POINT
# ============================================================
# ============================================================
# OUTPUT: PREDICTED TABLE
# ============================================================
def print_predicted_table():
    title_counts = Counter(); top4_counts = Counter(); fifth_counts = Counter()
    sixth_counts = Counter(); releg_counts = Counter()
    final_Pts = defaultdict(list)

    for _ in tqdm(range(N_SIMS), desc="La Liga", unit="sim", ncols=80,
                  disable=_DISABLE_TQDM):
        tbl = {t: current[t].copy() for t in TEAMS}
        ratings = current_elo.copy()
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
            if pos == 1:  title_counts[team] += 1
            if pos <= 4:  top4_counts[team] += 1
            elif pos == 5: fifth_counts[team] += 1
            elif pos == 6: sixth_counts[team] += 1
            if pos >= 18: releg_counts[team] += 1

    print(f"\nPREDICTED LA LIGA TABLE — averages over {N_SIMS} simulations\n")
    print(f"{'#':<3}{'CLUB':<18}{'AvgPTS':<9}{'Top4%':<9}{'5th%':<9}{'6th%':<9}{'Releg%':<9}")
    print("-" * 68)

    sorted_teams = sorted(TEAMS, key=lambda t: np.mean(final_Pts[t]), reverse=True)

    for rank, team in enumerate(sorted_teams, 1):
        avg_pts = np.mean(final_Pts[team])
        p_top4 = top4_counts[team] / N_SIMS * 100
        p_5th = fifth_counts[team] / N_SIMS * 100
        p_6th = sixth_counts[team] / N_SIMS * 100
        p_releg = releg_counts[team] / N_SIMS * 100

        print(
            f"{rank:<3}{team:<18}{avg_pts:<9.1f}"
            f"{p_top4:<9.2f}{p_5th:<9.2f}{p_6th:<9.2f}{p_releg:<9.2f}"
        )


# ============================================================
# DASHBOARD ENTRY POINT
# ============================================================
def run_simulation(n_sims=N_SIMS, seed=None, on_progress=None, is_running=None,
                   snapshot_callback=None, snapshot_every=None):
    if seed is not None:
        random.seed(seed)

    games_played_all = len(PLAYED_MATCHES)
    total_games_all_comps = 18 * 37  # 342 total games in season
    preset_mean = sum(current_elo.values()) / len(current_elo)
    sim_elos = regress_elos(current_elo, games_played_all, total_games_all_comps,
                            preset_mean, ELO_MAX_PULL)

    title_counts = Counter(); top4_counts = Counter(); fifth_counts = Counter()
    sixth_counts = Counter(); releg_counts = Counter()
    final_Pts = defaultdict(list)

    if snapshot_every is None:
        snapshot_every = max(1, n_sims // 250)

    completed = 0
    for _ in tqdm(range(n_sims), desc="La Liga", unit="sim", ncols=80,
                  disable=_DISABLE_TQDM):
        if is_running is not None and not is_running():
            break
        tbl = {t: current[t].copy() for t in TEAMS}
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
            if pos == 1:  title_counts[team] += 1
            if pos <= 4:  top4_counts[team] += 1
            elif pos == 5: fifth_counts[team] += 1
            elif pos == 6: sixth_counts[team] += 1
            if pos >= 18: releg_counts[team] += 1
        completed += 1
        if on_progress is not None:
            on_progress(completed, n_sims)
        if snapshot_callback is not None and (completed % snapshot_every == 0 or completed == n_sims):
            snapshot_callback(completed, n_sims, {
                "avg_points": {t: float(np.mean(final_Pts[t])) if final_Pts[t] else 0.0 for t in TEAMS},
                "title_prob": {t: title_counts[t] / completed * 100 for t in TEAMS},
                "top4_prob":  {t: top4_counts[t]   / completed * 100 for t in TEAMS},
                "fifth_prob": {t: fifth_counts[t]   / completed * 100 for t in TEAMS},
                "sixth_prob": {t: sixth_counts[t]   / completed * 100 for t in TEAMS},
                "releg_prob": {t: releg_counts[t]   / completed * 100 for t in TEAMS},
            })

    n = completed or 1
    return {
        "n_sims": completed,
        "teams": TEAMS,
        "avg_points":  {t: float(np.mean(final_Pts[t])) for t in TEAMS},
        "title_prob":  {t: title_counts[t] / n * 100 for t in TEAMS},
        "top4_prob":   {t: top4_counts[t]   / n * 100 for t in TEAMS},
        "fifth_prob":  {t: fifth_counts[t]   / n * 100 for t in TEAMS},
        "sixth_prob":  {t: sixth_counts[t]   / n * 100 for t in TEAMS},
        "releg_prob":  {t: releg_counts[t]   / n * 100 for t in TEAMS},
    }


if __name__ == "__main__":
    print_predicted_table()