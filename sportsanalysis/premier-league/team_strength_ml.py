"""
team_strength_ml.py

Learns per-(season, stat) Ridge weights for THREE targets:

    1. Overall strength  → recency-weighted career PPG
                           (used for points allocation + overall Elo)
    2. Attack strength   → recency-weighted career goals scored per match
    3. Defence strength  → recency-weighted career -goals conceded per match
                           (negated so higher = better defence)

Attack and defence models each use their own stat subset:

    ATTACK_STATS  = ["goals"]
    DEFENSE_STATS = ["ga"]

Output
    points                   – 25,000-point pool distributed by predicted overall strength
    ppg                      – predicted career PPG per team (overall)
    elo                      – overall Elo map  (drop-in for preset_pl_elos())
    attack_elo               – attack-only Elo map
    defense_elo              – defence-only Elo map
    attack_ppg               – predicted goals scored per match
    defense_ppg              – predicted -goals conceded per match (higher = better defence)
    per_season_weights       – {csv: {total_abs, pct}}     ← overall model
    per_season_stat_coefs    – {csv: {stat: coef}}          ← overall model
    per_stat_totals          – {stat: Σ coef over seasons}   ← overall model
    attack_per_season_weights, attack_stat_coefs, attack_stat_totals
    defense_per_season_weights, defense_stat_coefs, defense_stat_totals
    cv_r2, attack_cv_r2, defense_cv_r2, alpha, coef, means, stds
"""
from __future__ import annotations

import csv
import json
import sys
import time
import re
from collections import defaultdict
from pathlib import Path

import numpy as np
from sklearn.linear_model import Ridge
from sklearn.model_selection import KFold

# ---------------------------------------------------------------------------
# CONFIG — edit paths / pool here
# ---------------------------------------------------------------------------
BASE_DIR = Path(r"c:/Users/liam/Documents/GitHub/Footballdata/data/ENGLAND/Premier league/GAMES")

POOL_TOTAL = 25_000

# Derive CSV_FILES automatically from the directory, filtering to seasons from 2015-16 onwards.
_CSV_SEASON_RE = re.compile(r"(\d{2,4})-(\d{2,4})\.csv$", re.IGNORECASE)

def _parse_season_year(fname: str) -> int | None:
    """Extract the starting year of a season from filenames like 2015-2016.csv or 1992-1993.csv."""
    m = _CSV_SEASON_RE.search(fname)
    if not m:
        return None
    start = m.group(1)
    y = int(start)
    if len(start) == 2:          # "92" -> 1992, "15" -> 2015
        y = 2000 + y if y < 50 else 1900 + y
    return y

# Auto-discover and sort CSV files from 2015-16 onwards
# Only accept filenames like 2015-2016.csv (no prefix like "players_" or "E0_")
# Filter to seasons where data has FTHG/FTAG/FTR columns (1992-93 onwards)
_ALL_CSVS = sorted(
    [
        f for f in BASE_DIR.iterdir()
        if (
            f.is_file()
            and f.suffix.lower() == ".csv"
            and re.fullmatch(r"\d{4}-\d{4}\.csv", f.name, re.IGNORECASE)
            and _parse_season_year(f.name) is not None
            and _parse_season_year(f.name) >= 1992
        )
    ],
    key=lambda p: _parse_season_year(p.name)
)
CSV_FILES = [
    p.name for p in _ALL_CSVS
    if _parse_season_year(p.name) is not None and _parse_season_year(p.name) >= 2015
]

RECENCY_DECAY = 0.65
RECENCY_JITTER = 0.20
RECENCY_FLOOR = 0.10

SEASON_LENGTH = 38

POOL_TOTAL = 25_000

# ---------------------------------------------------------------------------
# STAT GROUPS
# ---------------------------------------------------------------------------
# Attack-relevant stats: goals scored, expected goals, deep completions,
# and ppda_allowed (higher = opponents forced to make more passes before
# a defensive action, which correlates with attacking dominance).
ATTACK_STATS = ["goals"]
DEFENSE_STATS = ["ga"]

FEATURE_STATS = [
    "goals", "ga",
]

# Sanity: the two groups must be disjoint and together cover FEATURE_STATS.
assert set(ATTACK_STATS) | set(DEFENSE_STATS) == set(FEATURE_STATS), (
    "ATTACK_STATS + DEFENSE_STATS must cover all FEATURE_STATS"
)
assert not (set(ATTACK_STATS) & set(DEFENSE_STATS)), (
    "ATTACK_STATS and DEFENSE_STATS must be disjoint"
)

# Per-stat EWMA across seasons (older -> newer) replaces per-season features.
# This gives a single exponentially-weighted feature per stat, so Ridge
# has only 2 coefficients and recency is enforced by construction.
PER_MATCH_STATS = {
    "goals", "ga",
}

NAME_MAP = {
    "Manchester City":         "Man City",
    "Manchester United":       "Man United",
    "Newcastle United":        "Newcastle",
    "Nottingham Forest":       "Forest",
    "Wolverhampton Wanderers": "Wolves",
    "Tottenham Hotspur":       "Tottenham",
    "Brighton & Hove Albion":  "Brighton",
    "West Ham United":         "West Ham",
    "Leicester City":          "Leicester",
    "Leeds United":            "Leeds",
}

PL_TEAMS = {
    "Man City", "Arsenal", "Man United", "Liverpool", "Brighton",
    "Brentford", "Aston Villa", "Bournemouth", "Chelsea", "Everton",
    "Leeds", "Newcastle", "Crystal Palace", "Forest", "Sunderland",
    "Fulham", "Hull", "Tottenham", "Ipswich", "Coventry",
}

ELO_MEAN = 1880.0
ELO_SD   = 120.0


# ---------------------------------------------------------------------------
# RECENCY WEIGHTS
# ---------------------------------------------------------------------------
def _make_recency_weights(n: int, seed: int | None = None) -> list[float]:
    if n <= 0:
        return []
    # file_order is oldest -> newest, so index n-1 is the newest season.
    # Newest gets 1.0; older seasons decay backwards.
    weights = [
        max(RECENCY_FLOOR, RECENCY_DECAY ** (n - 1 - i))
        for i in range(n)
    ]
    if seed is not None:
        rng = np.random.default_rng(seed)
        weights = [
            max(RECENCY_FLOOR, w + w * rng.uniform(-RECENCY_JITTER, RECENCY_JITTER))
            for w in weights
        ]
    # IMPORTANT: keep chronological alignment — do NOT sort.
    return weights


def _derive_recency_weights(seed: int | None,
                             match_counts: list[float] | None = None,
                             n_seasons: int | None = None) -> list[float]:
    if n_seasons is None:
        n_seasons = len(match_counts) if match_counts is not None else 3

    weights = _make_recency_weights(n_seasons, seed=seed)

    if match_counts is None:
        return weights

    n = len(weights)
    weights = list(weights)

    for i in range(n):
        ratio = min(match_counts[i] / SEASON_LENGTH, 1.0) if match_counts[i] > 0 else 0.0
        if ratio < 1.0:
            deficit = weights[i] * (1.0 - ratio)
            weights[i] *= ratio
            if n > 1:
                share = deficit / (n - 1)
                for k in range(n):
                    if k != i:
                        weights[k] += share

    # IMPORTANT: keep chronological alignment — do NOT sort.
    return weights


# ---------------------------------------------------------------------------
# PROGRESS BAR
# ---------------------------------------------------------------------------
def _progress_bar(done: int, total: int, start: float,
                  prefix: str = "", width: int = 30) -> str:
    frac = done / max(total, 1)
    elapsed = time.time() - start
    eta = elapsed * (1.0 - frac) / frac if done > 0 else 0.0
    filled = min(round(frac * width), width)
    if filled >= width:
        bar = "[" + "=" * width + "]"
    else:
        bar = "[" + "=" * filled + ">" + " " * (width - filled - 1) + "]"
    return f"{prefix}{bar} {frac*100:5.1f}%  ETA {eta:4.0f}s"


# ---------------------------------------------------------------------------
# DATA LOADING
# ---------------------------------------------------------------------------
def _norm(name: str) -> str:
    return NAME_MAP.get(name.strip(), name.strip())


def _load_csv(path: Path) -> list[dict]:
    rows = []
    with open(path, newline="", encoding="utf-8-sig", errors="replace") as f:
        reader = csv.DictReader(f, delimiter=",")
        if not reader.fieldnames:
            print(f"  [SKIP] {path.name}: no header")
            return rows
        # strip whitespace/BOM
        reader.fieldnames = [h.strip() for h in reader.fieldnames]

        required = {"HomeTeam", "AwayTeam", "FTHG", "FTAG", "FTR"}
        missing = required - set(reader.fieldnames)
        if missing:
            print(f"  [SKIP] {path.name}: missing {sorted(missing)} "
                  f"(first cols: {reader.fieldnames[:8]})")
            return rows

        for r in reader:
            hg  = float(r["FTHG"]) if (r["FTHG"] or "").strip() else 0.0
            ag  = float(r["FTAG"]) if (r["FTAG"] or "").strip() else 0.0
            ftr = (r["FTR"] or "D").strip().upper()

            if ftr == "H":
                hp, ap = 3.0, 0.0
            elif ftr == "A":
                hp, ap = 0.0, 3.0
            else:
                hp, ap = 1.0, 1.0

            rows.append({
                "team": _norm(r["HomeTeam"]),
                "matches": 1.0,
                "feat": {"goals": hg, "ga": ag},
                "points": hp,
            })
            rows.append({
                "team": _norm(r["AwayTeam"]),
                "matches": 1.0,
                "feat": {"goals": ag, "ga": hg},
                "points": ap,
            })
    return rows


def load_all(base_dir: Path, verbose: bool = True,
             recency_weights: list[float] | None = None) -> tuple[dict, list[str], list[float]]:
    rows_by_file: dict[str, list[dict]] = {}
    loaded_order: list[str] = []
    match_counts: list[float] = []
    for fname in CSV_FILES:
        p = base_dir / fname
        if not p.exists():
            print(f"  [MISSING] {fname}")
            continue
        rows = _load_csv(p)
        rows_by_file[fname] = rows
        loaded_order.append(fname)
        # Accumulate matches per team instead of using median of a single row
        per_team = defaultdict(float)
        for r in rows:
            per_team[r["team"]] += r["matches"]
        mc = float(np.median(list(per_team.values()))) if per_team else 0.0
        match_counts.append(mc)
        if verbose:
            ratio = mc / SEASON_LENGTH if mc > 0 else 0.0
            weight_str = ""
            if recency_weights is not None:
                weight_str = f"  ×{recency_weights[len(loaded_order)-1]:.2f} recency"
            print(f"  [{fname:<24}] {len(rows):>3} teams  "
                  f"({mc:.0f} games each, "
                  f"{ratio:.0%} complete,{weight_str})")
    return rows_by_file, loaded_order, match_counts


# ---------------------------------------------------------------------------
# FEATURE BUILDING
# ---------------------------------------------------------------------------
def _build_features(rows_by_file, file_order, recency_weights: list[float] | None = None):
    rw = recency_weights or _make_recency_weights(len(file_order))
    n_seasons = len(file_order)

    # Per-stat EWMA across seasons (older -> newer), using normalised recency weights
    rw_arr = np.array(rw, dtype=float)
    rw_arr = rw_arr / rw_arr.sum()  # normalise to sum=1

    by_team = defaultdict(lambda: {
        "feats":   [None] * n_seasons,
        "matches": [0.0]  * n_seasons,
        "ppgs":    [0.0]  * n_seasons,
        "points":  [0.0]  * n_seasons,
        "goals":   [0.0]  * n_seasons,
        "ga":      [0.0]  * n_seasons,
    })
    for fname, rows in rows_by_file.items():
        s = file_order.index(fname) if fname in file_order else 0
        for r in rows:
            d = by_team[r["team"]]
            d["matches"][s] += r["matches"]
            d["points"][s]  += r["points"]
            d["goals"][s]   += r["feat"]["goals"]
            d["ga"][s]      += r["feat"]["ga"]

    # Compute per-match rates
    for d in by_team.values():
        for s in range(n_seasons):
            m = d["matches"][s]
            if m > 0:
                d["ppgs"][s]  = d["points"][s] / m
                d["goals"][s] = d["goals"][s]  / m
                d["ga"][s]    = d["ga"][s]     / m
                d["feats"][s] = {"goals": d["goals"][s], "ga": d["ga"][s]}

    # Build EWMA features: one weighted average per stat across seasons
    teams = sorted(by_team.keys())
    n_teams = len(teams)
    ewma_X = np.zeros((n_teams, len(FEATURE_STATS)))
    ewma_w = np.zeros(n_teams)

    # Compute targets in one pass, store arrays up-front
    y_ppg     = np.zeros(n_teams)
    y_attack  = np.zeros(n_teams)
    y_defense = np.zeros(n_teams)
    w         = np.zeros(n_teams)

    for i, t in enumerate(teams):
        d = by_team[t]
        tw = tp = tg = tga = 0.0
        for s in range(n_seasons):
            if d["feats"][s] is None:
                continue
            mw  = d["matches"][s] * rw[s]
            tw  += mw
            tp  += mw * d["ppgs"][s]
            tg  += mw * d["goals"][s]
            tga += mw * d["ga"][s]
        if tw > 0:
            y_ppg[i]     =  tp / tw
            y_attack[i]  =  tg / tw
            y_defense[i] = -tga / tw
        w[i] = tw

        # EWMA feature: weighted average of per-season stat values
        for j, stat in enumerate(FEATURE_STATS):
            num = den = 0.0
            for s in range(n_seasons):
                if d["feats"][s] is None:
                    continue
                num += rw_arr[s] * d["feats"][s][stat]
                den += rw_arr[s]
            ewma_X[i, j] = num / den if den > 0 else 0.0

    # Standardise features (per stat across teams)
    means = np.zeros(len(FEATURE_STATS))
    stds  = np.ones(len(FEATURE_STATS))
    for j in range(len(FEATURE_STATS)):
        vals = ewma_X[:, j]
        m, sd = vals.mean(), vals.std()
        if sd < 1e-9:
            sd = 1.0
        means[j] = m
        stds[j]  = sd
        ewma_X[:, j] = (vals - m) / sd

    # Column indices for attack / defence sub-models (each has 1 column now,
    # indexing into the 2-dimensional ewma_X)
    attack_cols  = [0]  # goals EWMA column index
    defense_cols = [1]  # ga EWMA column index

    # Add recency_weights to feat_data for easy access
    feat_data = {
        "X": ewma_X,
        "X_raw": None,
        "y_ppg": y_ppg,
        "y_attack": y_attack,
        "y_defense": y_defense,
        "w": w,
        "teams": teams,
        "present": None,
        "means": means,
        "stds": stds,
        "rows_by_file": rows_by_file,
        "file_order": file_order,
        "n_seasons": n_seasons,
        "n_feat": len(FEATURE_STATS),
        "attack_cols": attack_cols,
        "defense_cols": defense_cols,
        "recency_weights": rw,
    }

    return feat_data


# ---------------------------------------------------------------------------
# ML FIT
# ---------------------------------------------------------------------------
def _fit_ridge_cv(X, y, w, progress=True, label="Ridge CV"):
    alphas = np.logspace(-2, 3, 26)
    kf = KFold(n_splits=5, shuffle=True, random_state=42)
    best_alpha, best_cv = None, -np.inf
    start = time.time()

    for i, a in enumerate(alphas):
        scores = []
        for tr, va in kf.split(X):
            m = Ridge(alpha=a)
            m.fit(X[tr], y[tr], sample_weight=w[tr])
            pred = m.predict(X[va])
            ss_res = np.sum(w[va] * (y[va] - pred) ** 2)
            ss_tot = np.sum(w[va] * (y[va] - np.average(y[va], weights=w[va])) ** 2)
            scores.append(1.0 - ss_res / ss_tot if ss_tot > 1e-12 else 0.0)
        cv = float(np.mean(scores))
        if cv > best_cv:
            best_cv, best_alpha = cv, a
        if progress:
            sys.stderr.write(
                "\r" + _progress_bar(i + 1, len(alphas), start, prefix=f"  {label}: "))
            sys.stderr.flush()
    if progress:
        sys.stderr.write(
            "\r" + _progress_bar(len(alphas), len(alphas), start, prefix=f"  {label}: ") + "  \n")

    final = Ridge(alpha=best_alpha)
    final.fit(X, y, sample_weight=w)
    return {"model": final, "alpha": float(best_alpha),
            "cv_r2": best_cv, "coef": final.coef_, "intercept": float(final.intercept_)}


# ---------------------------------------------------------------------------
# WEIGHT EXTRACTION
# ---------------------------------------------------------------------------
def _extract_weights(coef, feat_data, stat_names=None):
    """Extract per-(season, stat) and per-season weights from a coefficient vector.

    With EWMA features, coef has length n_feat (one per stat), not per-season.
    Returns per_season_weights as the recency weights themselves.
    """
    stat_names = list(stat_names) if stat_names is not None else list(FEATURE_STATS)
    coef = np.atleast_1d(coef)

    # Per-stat totals: map coef[j] to stat_names[j]
    per_stat_totals = {
        s: float(coef[j]) if j < len(coef) else 0.0
        for j, s in enumerate(stat_names)
    }

    # "per-season weights" are literally the recency weights — they are baked
    # into the EWMA features, NOT recovered from Ridge coefficients.
    rw = feat_data["recency_weights"]
    tot = sum(rw) or 1.0
    per_season_weights = {
        fname: {"total_abs": float(w), "pct": float(100.0 * w / tot)}
        for fname, w in zip(feat_data["file_order"], rw)
    }

    return per_season_weights, per_stat_totals


# ---------------------------------------------------------------------------
# PREDICTION + ALLOCATION + ELO
# ---------------------------------------------------------------------------
def _predict_from_model(model, X, teams) -> dict:
    return dict(zip(teams, model.predict(X).tolist()))


def _distribute(ppg: dict, pool_total: float, floor: float = 0.10) -> dict:
    teams = list(ppg.keys())
    vals = np.maximum(np.array([ppg[t] for t in teams]), floor)
    total = vals.sum()
    return {t: float(pool_total * v / total) for t, v in zip(teams, vals)}


def _to_elo(values: dict, team_filter: set | None = None) -> dict:
    """Map arbitrary per-team values to an Elo scale via z-score."""
    if team_filter is None:
        team_filter = set(values.keys())
    teams = [t for t in team_filter if t in values]
    if len(teams) < 2:
        return {}
    arr = np.array([values[t] for t in teams])
    mu, sigma = arr.mean(), arr.std()
    if sigma < 1e-9:
        return {t: ELO_MEAN for t in teams}
    return {
        t: float(ELO_MEAN + (values[t] - mu) / sigma * ELO_SD)
        for t in teams
    }


def _current_ppg(feat_data) -> dict:
    newest = feat_data["file_order"][-1] if feat_data["file_order"] else None
    if newest is None:
        return {}
    totals = defaultdict(lambda: [0.0, 0.0])   # [points, matches]
    for r in feat_data["rows_by_file"].get(newest, []):
        totals[r["team"]][0] += r["points"]
        totals[r["team"]][1] += r["matches"]
    return {t: p / m for t, (p, m) in totals.items() if m > 0}


# ---------------------------------------------------------------------------
# PUBLIC API
# ---------------------------------------------------------------------------
_CACHE: dict[int | None, dict] | None = None


def _cache_key(base_dir, pool_total, recency_seed: int | None) -> tuple:
    return (str(Path(base_dir).resolve()), float(pool_total), recency_seed)


def compute_team_strengths(base_dir: Path | str = BASE_DIR,
                           pool_total: float = POOL_TOTAL,
                           verbose: bool = True,
                           save_json: bool = True,
                           progress: bool = True,
                           recency_seed: int | None = None) -> dict:
    global _CACHE

    key = _cache_key(base_dir, pool_total, recency_seed)
    if _CACHE is not None and key in _CACHE:
        cached = _CACHE[key]
        if verbose:
            print(f"[cache hit] recency_seed={recency_seed!r}")
        return cached

    base_dir = Path(base_dir)

    if verbose:
        print("=" * 78)
        print("ML TEAM STRENGTH — overall + attack + defence Ridge models")
        print("=" * 78)
        print(f"Pool: {pool_total:,} pts   |   Files: {len(CSV_FILES)}")
        print(f"Attack stats : {', '.join(ATTACK_STATS)}")
        print(f"Defence stats: {', '.join(DEFENSE_STATS)}")
        print()

    rows_by_file, file_order, match_counts = load_all(base_dir, verbose=verbose,
                                                      recency_weights=None)
    if not rows_by_file:
        raise FileNotFoundError(f"No CSVs found in {base_dir}")

    recency_weights = _derive_recency_weights(recency_seed, match_counts,
                                              n_seasons=len(file_order))

    if verbose:
        label = "jittered" if recency_seed is not None else "baseline"
        print(f"\nRecency weights ({label}): "
              + ", ".join(f"{w:.3f}" for w in recency_weights))

    if verbose:
        n_rows = sum(len(v) for v in rows_by_file.values())
        print(f"\nTotal team-rows: {n_rows}   "
              f"| Unique teams: {len({r['team'] for v in rows_by_file.values() for r in v})}\n")

    feat_data = _build_features(rows_by_file, file_order, recency_weights=recency_weights)

    show_progress = progress and verbose

    # ---- Overall PPG model (drives points + overall Elo) -------------------
    fit = _fit_ridge_cv(feat_data["X"], feat_data["y_ppg"], feat_data["w"],
                        progress=show_progress, label="PPG")

    # ---- Attack model ------------------------------------------------------
    X_attack = feat_data["X"][:, feat_data["attack_cols"]]
    fit_attack = _fit_ridge_cv(X_attack, feat_data["y_attack"], feat_data["w"],
                               progress=show_progress, label="Attack")

    # ---- Defence model -----------------------------------------------------
    X_defense = feat_data["X"][:, feat_data["defense_cols"]]
    fit_defense = _fit_ridge_cv(X_defense, feat_data["y_defense"], feat_data["w"],
                                progress=show_progress, label="Defence")

    if verbose:
        print(f"Ridge CV R² — overall {fit['cv_r2']:+.4f}  "
              f"| attack {fit_attack['cv_r2']:+.4f}  "
              f"| defence {fit_defense['cv_r2']:+.4f}")

    # ---- Extract weights for all three models ------------------------------
    per_season_weights, per_stat_totals = \
        _extract_weights(fit["coef"], feat_data)

    attack_weights, attack_stat_totals = \
        _extract_weights(fit_attack["coef"], feat_data, ATTACK_STATS)

    defense_weights, defense_stat_totals = \
        _extract_weights(fit_defense["coef"], feat_data, DEFENSE_STATS)

    # ---- Predict + allocate ------------------------------------------------
    ppg = _predict_from_model(fit["model"], feat_data["X"], feat_data["teams"])
    points = _distribute(ppg, pool_total)
    elo = _to_elo(points, PL_TEAMS)

    attack_ppg  = _predict_from_model(fit_attack["model"],  X_attack,  feat_data["teams"])
    defense_ppg = _predict_from_model(fit_defense["model"], X_defense, feat_data["teams"])

    attack_elo  = _to_elo(attack_ppg,  PL_TEAMS)
    defense_elo = _to_elo(defense_ppg, PL_TEAMS)

    cur_ppg = _current_ppg(feat_data)

    # ---- Report ------------------------------------------------------------
    if verbose:
        _print_report(
            feat_data, fit, ppg, points, elo, cur_ppg,
            per_season_weights, per_stat_totals,
            attack_ppg, defense_ppg, attack_elo, defense_elo,
            attack_weights, attack_stat_totals,
            defense_weights, defense_stat_totals,
            fit_attack, fit_defense,
        )

    result = {
        "points":                  points,
        "ppg":                     ppg,
        "current_ppg":             cur_ppg,
        "elo":                     elo,            # overall (backward-compat)
        "attack_elo":              attack_elo,
        "defense_elo":             defense_elo,
        "attack_ppg":              attack_ppg,     # predicted goals scored / match
        "defense_ppg":             defense_ppg,    # predicted -goals conceded / match
        "per_season_weights":      per_season_weights,
        "per_stat_totals":         per_stat_totals,
        "attack_per_season_weights": attack_weights,
        "attack_stat_totals":        attack_stat_totals,
        "defense_per_season_weights": defense_weights,
        "defense_stat_totals":        defense_stat_totals,
        "cv_r2":                   fit["cv_r2"],
        "attack_cv_r2":            fit_attack["cv_r2"],
        "defense_cv_r2":           fit_defense["cv_r2"],
        "alpha":                   fit["alpha"],
        "attack_alpha":            fit_attack["alpha"],
        "defense_alpha":           fit_defense["alpha"],
        "coef":                    fit["coef"].tolist(),
        "attack_coef":             fit_attack["coef"].tolist(),
        "defense_coef":            fit_defense["coef"].tolist(),
        "intercept":               fit["intercept"],
        "attack_intercept":        fit_attack["intercept"],
        "defense_intercept":       fit_defense["intercept"],
        "means":                   feat_data["means"].tolist(),
        "stds":                    feat_data["stds"].tolist(),
        "feature_stats":           list(FEATURE_STATS),
        "attack_stats":            list(ATTACK_STATS),
        "defense_stats":           list(DEFENSE_STATS),
        "season_order":            list(file_order),
        "pool_total":              pool_total,
        "recency_weights":         recency_weights,
    }

    if save_json and recency_seed is None:
        out_path = base_dir / "team_strength.json"
        with open(out_path, "w") as f:
            json.dump(result, f, indent=2)
        if verbose:
            print(f"\nWrote {out_path}")

    if _CACHE is None:
        _CACHE = {}
    _CACHE[key] = {
        "elo":         elo,
        "attack_elo":  attack_elo,
        "defense_elo": defense_elo,
        "points":      points,
        "ppg":         ppg,
        "attack_ppg":  attack_ppg,
        "defense_ppg": defense_ppg,
        "alpha":          fit["alpha"],
        "attack_alpha":   fit_attack["alpha"],
        "defense_alpha":  fit_defense["alpha"],
        "cv_r2":          fit["cv_r2"],
        "attack_cv_r2":   fit_attack["cv_r2"],
        "defense_cv_r2":  fit_defense["cv_r2"],
    }
    return result


def _print_report(feat_data, fit, ppg, points, elo, cur_ppg,
                  per_season_weights, per_stat_totals,
                  attack_ppg, defense_ppg, attack_elo, defense_elo,
                  attack_weights, attack_stat_totals,
                  defense_weights, defense_stat_totals,
                  fit_attack, fit_defense):

    order = feat_data["file_order"]

    # ------------------------------------------------------------------
    # A. Recency weights used in EWMA features
    # ------------------------------------------------------------------
    print("\n" + "=" * 78)
    print("A. RECENCY WEIGHTS USED IN EWMA FEATURES (oldest -> newest)")
    print("=" * 78)
    for fname, w in zip(order, feat_data["recency_weights"]):
        print(f"  {fname:<28}{w:>12.4f}")

    # ------------------------------------------------------------------
    # B. Overall model — per-stat coefficients (standardised features)
    # ------------------------------------------------------------------
    print("\n" + "=" * 78)
    print("B. OVERALL MODEL — PER-STAT COEFFICIENTS (standardised features)")
    print("=" * 78)
    for stat, c in sorted(per_stat_totals.items(), key=lambda kv: -abs(kv[1])):
        tag = "good" if c > 0 else "bad" if c < 0 else "n/a"
        print(f"  {stat:<18}{c:>+12.4f}   ({tag})")

    # ------------------------------------------------------------------
    # C. Aggregate stat importance (overall)
    # ------------------------------------------------------------------
    print("\n" + "=" * 78)
    print("C. OVERALL MODEL — AGGREGATE STAT IMPORTANCE (sum of coef across seasons)")
    print("=" * 78)
    ranked_totals = sorted(per_stat_totals.items(), key=lambda kv: -abs(kv[1]))
    print(f"  {'stat':<18}{'total coef':>12}   direction")
    print("  " + "-" * 42)
    for stat, c in ranked_totals:
        tag = "good" if c > 0 else "bad" if c < 0 else "n/a"
        print(f"  {stat:<18}{c:>+12.4f}   ({tag})")

    # ------------------------------------------------------------------
    # D. Team table — overall + attack + defence
    # ------------------------------------------------------------------
    print("\n" + "=" * 78)
    print(f"D. TEAM STRENGTH — {POOL_TOTAL:,}-POINT POOL + ATTACK / DEFENCE ELO")
    print("=" * 78)
    print(f"  {'':<2}{'team':<20}{'pred PPG':>10}{'cur PPG':>10}"
          f"{'points':>10}{'atk Elo':>9}{'def Elo':>9}{'ovr Elo':>9}")
    print("  " + "-" * 80)
    ordered = sorted(points, key=lambda t: -points[t])
    for t in ordered:
        marker = "*" if t in PL_TEAMS else " "
        cur = f"{cur_ppg[t]:.2f}" if t in cur_ppg else "—"
        a_elo = f"{attack_elo[t]:.0f}"  if t in attack_elo  else "—"
        d_elo = f"{defense_elo[t]:.0f}" if t in defense_elo else "—"
        o_elo = f"{elo[t]:.0f}"         if t in elo         else "—"
        print(f"  {marker} {t:<20}{ppg[t]:>10.3f}{cur:>10}"
              f"{points[t]:>10.1f}{a_elo:>9}{d_elo:>9}{o_elo:>9}")
    print(f"\n  (*) = PL team (Elo shown);  ( ) = older-season team, no Elo")
    pl_points = sum(points[t] for t in PL_TEAMS if t in points)
    print(f"  Sum of PL points: {pl_points:,.0f} / {POOL_TOTAL:,}")

    # ------------------------------------------------------------------
    # E. Attack model summary
    # ------------------------------------------------------------------
    print("\n" + "=" * 78)
    print(f"E. ATTACK MODEL  (CV R² = {fit_attack['cv_r2']:+.4f}, "
          f"alpha = {fit_attack['alpha']:.4g})")
    print("=" * 78)
    print(f"  Stats used: {', '.join(ATTACK_STATS)}")
    print(f"\n  {'stat':<18}{'total coef':>12}   direction")
    print("  " + "-" * 42)
    for stat, c in sorted(attack_stat_totals.items(), key=lambda kv: -abs(kv[1])):
        tag = "more attack" if c > 0 else "less attack" if c < 0 else "n/a"
        print(f"  {stat:<18}{c:>+12.4f}   ({tag})")

    # ------------------------------------------------------------------
    # F. Defence model summary
    # ------------------------------------------------------------------
    print("\n" + "=" * 78)
    print(f"F. DEFENCE MODEL  (CV R² = {fit_defense['cv_r2']:+.4f}, "
          f"alpha = {fit_defense['alpha']:.4g})")
    print("=" * 78)
    print(f"  Stats used: {', '.join(DEFENSE_STATS)}")
    print(f"\n  {'stat':<18}{'total coef':>12}   direction")
    print("  " + "-" * 42)
    for stat, c in sorted(defense_stat_totals.items(), key=lambda kv: -abs(kv[1])):
        # target = -goals conceded → positive coef on 'ga' would *increase*
        # -GA (i.e. worsen defence), so interpret signs accordingly.
        tag = "worse def" if c > 0 else "better def" if c < 0 else "n/a"
        print(f"  {stat:<18}{c:>+12.4f}   ({tag})")


# ---------------------------------------------------------------------------
# CONVENIENCE WRAPPERS
# ---------------------------------------------------------------------------
def preset_pl_elos_from_ml(base_dir: Path | str = BASE_DIR,
                          recency_seed: int | None = None) -> dict:
    """Drop-in replacement for the simulation's preset_pl_elos() — overall Elo."""
    result = compute_team_strengths(base_dir=base_dir, verbose=False,
                                    save_json=False, progress=False,
                                    recency_seed=recency_seed)
    return dict(result["elo"])


def preset_pl_attack_elos_from_ml(base_dir: Path | str = BASE_DIR,
                                  recency_seed: int | None = None) -> dict:
    """Attack-only Elo map."""
    result = compute_team_strengths(base_dir=base_dir, verbose=False,
                                    save_json=False, progress=False,
                                    recency_seed=recency_seed)
    return dict(result["attack_elo"])


def preset_pl_defense_elos_from_ml(base_dir: Path | str = BASE_DIR,
                                   recency_seed: int | None = None) -> dict:
    """Defence-only Elo map (higher = better defence)."""
    result = compute_team_strengths(base_dir=base_dir, verbose=False,
                                    save_json=False, progress=False,
                                    recency_seed=recency_seed)
    return dict(result["defense_elo"])


def preset_pl_split_elos_from_ml(base_dir: Path | str = BASE_DIR,
                                 recency_seed: int | None = None) -> dict:
    """Return {'overall': …, 'attack': …, 'defense': …} Elo maps in one call."""
    result = compute_team_strengths(base_dir=base_dir, verbose=False,
                                    save_json=False, progress=False,
                                    recency_seed=recency_seed)
    return {
        "overall": dict(result["elo"]),
        "attack":  dict(result["attack_elo"]),
        "defense": dict(result["defense_elo"]),
    }


# ---------------------------------------------------------------------------
if __name__ == "__main__":
    compute_team_strengths()
    print("\nDone.")