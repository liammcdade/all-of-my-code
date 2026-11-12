"""Unified Premier League + European + Carabao Cup simulation (optimized Python port)."""
import math
import random
import sys
import time
import functools
from collections import defaultdict, Counter
from dataclasses import dataclass

if sys.stdout.encoding and sys.stdout.encoding.lower() not in ('utf-8', 'utf_8'):
    sys.stdout.reconfigure(encoding='utf-8')


# =============================================================================
# TABLE RENDERING (uses tabulate if available, custom grid fallback)
# =============================================================================
try:
    from tabulate import tabulate as _tabulate
except ImportError:
    _tabulate = None


def _table_can_unicode():
    enc = getattr(sys.stdout, "encoding", None) or ""
    return enc.lower().replace("-", "_") in ("utf_8", "utf8")


_BOX_UNICODE = {
    "tl": "┌", "tm": "┬", "tr": "┐",
    "ml": "├", "mm": "┼", "mr": "┤",
    "bl": "└", "bm": "┴", "br": "┘",
    "h": "─", "v": "│",
}
_BOX_ASCII = {
    "tl": "+", "tm": "+", "tr": "+",
    "ml": "+", "mm": "+", "mr": "+",
    "bl": "+", "bm": "+", "br": "+",
    "h": "-", "v": "|",
}


def _align_cell(text, width, align):
    s = str(text)
    if align == "r":
        return s.rjust(width)
    if align == "c":
        return s.center(width)
    return s.ljust(width)


def render_table(headers, rows, aligns=None):
    """Render a bordered grid table. Cells are pre-formatted strings."""
    headers = [str(h) for h in headers]
    rows = [[str(c) for c in row] for row in rows]
    ncols = len(headers)
    if aligns is None:
        aligns = ["l"] * ncols
    aligns = list(aligns) + ["l"] * (ncols - len(aligns))
    if _tabulate is not None:
        colalign = [{"l": "left", "r": "right", "c": "center"}.get(a, "left") for a in aligns]
        return _tabulate(rows, headers=headers, tablefmt="fancy_grid", colalign=colalign,
                         disable_numparse=True)
    box = _BOX_UNICODE if _table_can_unicode() else _BOX_ASCII
    widths = [len(headers[i]) for i in range(ncols)]
    for row in rows:
        for i in range(min(ncols, len(row))):
            widths[i] = max(widths[i], len(row[i]))

    def hline(left, mid, right):
        return left + mid.join(box["h"] * (w + 2) for w in widths) + right

    def fmt_row(cells, cell_aligns):
        parts = []
        for i in range(ncols):
            val = cells[i] if i < len(cells) else ""
            parts.append(" " + _align_cell(val, widths[i], cell_aligns[i]) + " ")
        return box["v"] + box["v"].join(parts) + box["v"]

    out = [
        hline(box["tl"], box["tm"], box["tr"]),
        fmt_row(headers, ["c"] * ncols),
        hline(box["ml"], box["mm"], box["mr"]),
    ]
    for row in rows:
        out.append(fmt_row(row, aligns))
    out.append(hline(box["bl"], box["bm"], box["br"]))
    return "\n".join(out)


def print_table(headers, rows, aligns=None):
    print(render_table(headers, rows, aligns=aligns))


# =============================================================================
# ML TEAM STRENGTH — plugged into preset_pl_elos()
# =============================================================================
from pathlib import Path as _Path

# =============================================================================
# STATS-BASED RATINGS (replaces Elo presets)
# =============================================================================
from pathlib import Path as _Path  # keep import if used elsewhere

# -----------------------------------------------------------------------------
# Raw stats (per-game where relevant). Names must match PL team names exactly.
# Shots pg, Tackles pg, Interceptions pg, Fouls pg, Offsides pg, Rating
# Goals, Shots pg, Discipline, Possession%, Pass%, AerialsWon, Rating
# Goal types: OpenPlay, CounterAttack, SetPiece, Penalty, OwnGoal
# xG, Goals, xGDiff, Shots, xG/Shots, Rating
# Assists total
# -----------------------------------------------------------------------------

_STATS_RAW = {
    # team: (shots_pg, tackles_pg, inter_pg, fouls_pg, offsides_pg,
    #        rating, goals, discipline, poss, pass_pct, aerials,
    #        open_play, counter, set_piece, penalty, own_goal,
    #        xg, xg_diff, xg_per_shot, assists)
    "Crystal Palace":   (18.9, 21.0,  9.9, 10.2, 2.3, 6.42, 10, 152, 42.2, 78.8, 12.9,  6, 1, 1, 1, 1, 14.71, -5.71, 0.13, 6),
    "Forest":           (10.0, 18.6,  7.8, 14.0, 1.8, 6.56,  9, 240, 44.5, 78.1, 16.1,  6, 2, 0, 1, 0, 18.47, -9.47, 0.11, 6),
    "Aston Villa":      (16.6, 18.1,  8.0, 11.2, 1.0, 6.50, 14, 201, 45.6, 83.3, 10.1, 10, 0, 3, 1, 0, 15.80, -1.80, 0.13, 11),
    "Hull":             (15.2, 18.1,  7.9, 11.4, 1.4, 6.57, 11, 300, 33.2, 71.4, 14.6,  4, 2, 4, 1, 0, 10.60,  0.40, 0.10, 8),
    "Man United":       (11.8, 17.8, 12.0, 11.8, 1.9, 6.58, 14, 211, 55.1, 85.5, 13.1,  8, 2, 1, 2, 1, 18.60, -5.60, 0.10, 10),
    "Tottenham":        (12.5, 17.5,  7.5, 13.5, 2.4, 6.61, 10, 161, 63.0, 88.2, 13.4,  6, 0, 3, 0, 1, 14.41, -5.41, 0.09, 7),
    "Brentford":        (15.5, 16.7, 11.3, 12.5, 1.5, 6.67, 16, 223, 43.6, 76.6, 18.9, 10, 2, 3, 0, 1, 15.34, -0.34, 0.12, 8),
    "Chelsea":          (12.3, 16.6,  9.6,  9.5, 1.3, 6.67, 19, 201, 49.8, 84.3, 14.6,  9, 3, 6, 1, 0, 15.88,  3.12, 0.12, 14),
    "Leeds":            (13.2, 16.5,  9.5, 12.9, 2.0, 6.70, 10, 190, 47.3, 78.3, 20.0,  4, 0, 5, 0, 1, 14.13, -5.13, 0.12, 6),
    "Everton":          (14.8, 16.0,  8.6,  8.4, 2.0, 6.72, 12, 180, 46.9, 83.1, 18.6,  8, 0, 4, 0, 0, 16.31, -4.31, 0.12, 8),
    "Bournemouth":      (10.4, 15.9, 12.2, 14.0, 1.2, 6.63, 16, 270, 47.6, 79.4, 18.7, 11, 1, 2, 0, 2, 19.71, -5.71, 0.14, 9),
    "Ipswich":          (15.9, 15.8,  9.5, 10.9, 2.0, 6.48, 15, 191, 46.5, 82.1, 14.6, 11, 1, 1, 2, 0, 14.08,  0.92, 0.13, 10),
    "Liverpool":        (12.9, 15.6, 10.1, 14.6, 2.0, 6.72, 14, 251, 52.9, 82.7, 16.5,  9, 2, 1, 1, 1, 16.16, -3.16, 0.10, 11),
    "Sunderland":       (13.5, 15.0,  8.2, 11.6, 2.3, 6.45,  8, 183, 47.5, 78.1, 16.7,  3, 0, 2, 3, 0, 16.87, -8.87, 0.14, 4),
    "Brighton":         (11.4, 14.9,  8.3, 12.3, 2.0, 6.87, 26, 241, 59.4, 85.0, 16.8, 11, 3, 7, 2, 3, 21.15,  1.85, 0.13, 15),
    "Fulham":           (13.7, 14.5,  7.8, 10.5, 1.6, 6.57, 10, 191, 57.7, 86.4, 12.0,  5, 1, 2, 0, 2, 15.86, -7.86, 0.11, 3),
    "Man City":         (10.6, 13.2,  6.5, 10.8, 1.6, 6.82, 21, 131, 65.9, 88.7, 13.5, 15, 2, 4, 0, 0, 21.32, -0.32, 0.14, 16),
    "Newcastle":        (16.5, 13.0,  7.0, 12.1, 2.1, 6.53, 13, 261, 50.4, 81.5, 17.6,  8, 3, 2, 0, 0, 13.02, -0.02, 0.11, 10),
    "Arsenal":          (11.0, 12.6,  6.7,  9.8, 3.5, 6.78, 15, 140, 59.8, 85.9, 16.2, 11, 2, 1, 1, 0, 16.57, -1.57, 0.12, 12),
    "Coventry":         (16.6, 11.6, 10.2, 10.8, 1.5, 6.44, 10, 111, 38.9, 77.2, 18.3,  7, 1, 1, 1, 0, 10.82, -0.82, 0.10, 5),
}

# Number of games played so far (for per-game conversion). Adjust if needed.
_STATS_GAMES_PLAYED = 10


def _build_stats_ratings():
    """Build attack/defence ratings on an Elo-like scale (~1800 mean, ~250 sd).

    All inputs are normalised to per-game and z-scored across teams before
    weighting, so the stated weights are the effective weights.

    Attack (variant A4): xG/g 0.45, Goals/g 0.20, Assists/g 0.15, Shots/g 0.10, OpenPlay/g 0.10
    Defence (variant D4): -xGA/g 0.55, -xGDiff/g 0.20, Tackles/g 0.15, Inter/g 0.10

    xGA/g is derived: xGA = xG_for − xGDiff, so xGA/g = xg_pg − xg_diff_pg.
    xGDiff weight reduced to avoid double-counting xGA + leaking attack into defence.
    Assists added as creative output signal separate from finishing (goals).
    """
    attack_weights = {"xg": 0.45, "goals": 0.20, "assists": 0.15, "shots": 0.10, "open_play": 0.10}
    defense_weights = {"neg_xga": 0.55, "neg_xgdiff": 0.20, "tackles": 0.15, "inter": 0.10}

    n = _STATS_GAMES_PLAYED
    teams = list(_STATS_RAW.keys())

    # ---- Per-game raw values ----
    per_game = {}
    for team in teams:
        s = _STATS_RAW[team]
        (shots_pg, tackles_pg, inter_pg, fouls_pg, offsides_pg,
         rating, goals, discipline, poss, pass_pct, aerials,
         open_play, counter, set_piece, penalty, own_goal,
         xg, xg_diff, xg_per_shot, assists) = s

        xg_pg = xg / n
        goals_pg = goals / n
        assists_pg = assists / n
        open_play_pg = open_play / n
        xg_diff_pg = xg_diff / n
        xga_pg = xg_pg - xg_diff_pg  # xGA/g derived from xG_for/g − xGDiff/g

        per_game[team] = {
            "xg": xg_pg,
            "goals": goals_pg,
            "assists": assists_pg,
            "shots": shots_pg,
            "open_play": open_play_pg,
            "neg_xgdiff": -xg_diff_pg,
            "neg_xga": -xga_pg,
            "tackles": tackles_pg,
            "inter": inter_pg,
        }

    # ---- Z-score each stat across teams so weights are comparable ----
    def zscore(values):
        mu = sum(values) / len(values)
        var = sum((v - mu) ** 2 for v in values) / len(values)
        sd = var ** 0.5 or 1.0
        return [(v - mu) / sd for v in values]

    stat_names = ["xg", "goals", "assists", "shots", "open_play",
                  "neg_xgdiff", "neg_xga", "tackles", "inter"]
    zscored = {stat: zscore([per_game[t][stat] for t in teams])
               for stat in stat_names}

    z_by_team = {t: {stat: zscored[stat][i] for stat in stat_names}
                 for i, t in enumerate(teams)}

    # ---- Weighted sums (weights sum to 1.0 on comparable z-scored scale) ----
    attack_raw = {}
    defense_raw = {}
    for team in teams:
        z = z_by_team[team]
        attack_raw[team] = (attack_weights["xg"] * z["xg"]
                            + attack_weights["goals"] * z["goals"]
                            + attack_weights["assists"] * z["assists"]
                            + attack_weights["shots"] * z["shots"]
                            + attack_weights["open_play"] * z["open_play"])
        defense_raw[team] = (defense_weights["neg_xga"] * z["neg_xga"]
                             + defense_weights["neg_xgdiff"] * z["neg_xgdiff"]
                             + defense_weights["tackles"] * z["tackles"]
                             + defense_weights["inter"] * z["inter"])

    def _to_elo_scale(values, mean=1800.0, spread=250.0):
        mu = sum(values.values()) / len(values)
        var = sum((v - mu) ** 2 for v in values.values()) / len(values)
        sd = var ** 0.5 or 1.0
        return {t: mean + (v - mu) / sd * spread for t, v in values.items()}

    attack = _to_elo_scale(attack_raw)
    defense = _to_elo_scale(defense_raw)
    overall = {t: (attack[t] + defense[t]) / 2.0 for t in attack}
    return overall, attack, defense


# =============================================================================
# MARKET PRIORS — Polymarket probabilities blended into per-sim ratings
# =============================================================================
# "Buy Yes" prices treated as implied probabilities (0-1). Team names mapped to
# this simulation's PL naming. These are title/UCL/top-6/relegation priors, not
# pairwise match odds; they are combined into a title-strength market prior.
POLYMARKET_TITLE_PROBS = {
    "Arsenal": 0.77, "Brighton": 0.071, "Man City": 0.07, "Liverpool": 0.06,
    "Chelsea": 0.014, "Tottenham": 0.005, "Man United": 0.004, "Aston Villa": 0.004,
    "Bournemouth": 0.002, "Brentford": 0.002, "Hull": 0.002, "Leeds": 0.001,
    "Crystal Palace": 0.001, "Newcastle": 0.001, "Everton": 0.001,
    "Sunderland": 0.001, "Forest": 0.001, "Coventry": 0.001,
    "Fulham": 0.001, "Ipswich": 0.001,
}
POLYMARKET_UCL_QUAL_PROBS = {
    "Arsenal": 0.999, "Liverpool": 0.74, "Brighton": 0.72, "Chelsea": 0.67,
    "Man City": 0.36, "Brentford": 0.28, "Bournemouth": 0.257, "Aston Villa": 0.24,
    "Tottenham": 0.23, "Man United": 0.20, "Forest": 0.18, "Leeds": 0.18,
    "Newcastle": 0.15, "Everton": 0.153, "Sunderland": 0.13, "Fulham": 0.059,
    "Crystal Palace": 0.056, "Coventry": 0.056, "Hull": 0.024, "Ipswich": 0.003,
}
POLYMARKET_TOP6_PROBS = {
    "Arsenal": 0.991, "Aston Villa": 0.37, "Bournemouth": 0.32, "Brentford": 0.38,
    "Brighton": 0.84, "Chelsea": 0.73, "Crystal Palace": 0.051, "Everton": 0.22,
    "Fulham": 0.101, "Leeds": 0.18, "Liverpool": 0.88, "Man City": 0.50,
    "Man United": 0.18, "Newcastle": 0.14, "Forest": 0.13, "Tottenham": 0.37,
    "Sunderland": 0.02, "Coventry": 0.01, "Ipswich": 0.052, "Hull": 0.032,
}
POLYMARKET_RELEGATION_PROBS = {
    "Hull": 0.56, "Coventry": 0.57, "Crystal Palace": 0.41, "Man City": 0.409,
    "Ipswich": 0.37, "Sunderland": 0.30, "Fulham": 0.16, "Forest": 0.13,
    "Newcastle": 0.086, "Leeds": 0.085, "Man United": 0.066, "Bournemouth": 0.06,
    "Tottenham": 0.05, "Aston Villa": 0.055, "Liverpool": 0.057, "Brentford": 0.03,
    "Brighton": 0.032, "Arsenal": 0.033, "Everton": 0.024, "Chelsea": 0.025,
}


# ---------------------------------------------------------------------------
# External ELO ratings (third blend factor, alongside stats and odds).
# Names are mapped to the PL team names used elsewhere in this file.
# ---------------------------------------------------------------------------
PL_EXTERNAL_ELOS = {
    "Arsenal":        2152.0,
    "Brighton":       1950.0,
    "Man City":       2010.0,
    "Liverpool":      1950.0,
    "Chelsea":        1877.0,
    "Everton":        1866.0,
    "Bournemouth":    1950.0,
    "Brentford":      1890.0,
    "Leeds":          1862.0,
    "Aston Villa":    1967.0,
    "Tottenham":      1848.0,
    "Newcastle":      1863.0,
    "Hull":           1747.0,
    "Ipswich":        1700.0,
    "Fulham":         1836.0,
    "Forest":         1850.0,
    "Coventry":       1689.0,
    "Man United":     1891.0,
    "Sunderland":     1782.0,
    "Crystal Palace": 1777.0,
}


def external_elos_to_dict(teams, mean=1800.0, spread=250.0):
    """Return a per-team Elo dict for the external ELO table, z-scored onto
    the same Elo scale as the stats and odds ratings so all three factors are
    comparable when blended (each gets a 33.33% weight).
    """
    values = [PL_EXTERNAL_ELOS.get(t, LEAGUE_AVERAGE_ELO) for t in teams]
    mu = sum(values) / len(values)
    var = sum((v - mu) ** 2 for v in values) / len(values)
    sd = var ** 0.5 or 1.0
    return {t: mean + (PL_EXTERNAL_ELOS.get(t, LEAGUE_AVERAGE_ELO) - mu) / sd * spread
            for t in teams}


def market_probs_to_elos(prob_dict, teams, anchor_mean=1800.0,
                         scale=400.0 / math.log(10.0), longshot_gamma=1.15, p_floor=1e-6):
    """Convert outright title probabilities (e.g. Polymarket) to Elo-scale ratings.

    Uses the Bradley–Terry/softmax inverse: R_i = C + scale*ln(P_i), with P_i
    the normalized (and optionally longshot-corrected) market probabilities and C
    chosen so the mean Elo equals anchor_mean. This yields a title-strength prior;
    it is blended with stats/external ratings to separate equal-probability teams.
    """
    raw = {}
    for t in teams:
        raw[t] = float(prob_dict.get(t, 1.0 / len(teams)))
    # longshot correction (gamma > 1 shrinks longshots) then normalize
    q = {t: max(p, p_floor) ** longshot_gamma for t, p in raw.items()}
    z = sum(q.values())
    p = {t: max(q[t] / z, p_floor) for t in q}
    z2 = sum(p.values())
    p = {t: v / z2 for t, v in p.items()}
    logs = {t: math.log(v) for t, v in p.items()}
    mean_log = sum(logs.values()) / len(logs)
    c = anchor_mean - scale * mean_log
    return {t: c + scale * logs[t] for t in teams}


def polymarket_prior_to_elos(teams, anchor_mean=1800.0, spread=70.0):
    """Build a market-strength prior from Polymarket outcome markets.

    Uses title/UCL/top-6 as soft strength signals and treats relegation as a weak
    penalty (markets can include non-football risk like deductions). Z-scored onto
    a controlled Elo-like scale so it informs but does not dominate match ratings.
    """
    eps = 1e-6
    scores = {}
    for t in teams:
        p_title = max(float(POLYMARKET_TITLE_PROBS.get(t, eps)), eps)
        p_ucl = min(max(float(POLYMARKET_UCL_QUAL_PROBS.get(t, eps)), eps), 1.0 - eps)
        p_top6 = min(max(float(POLYMARKET_TOP6_PROBS.get(t, eps)), eps), 1.0 - eps)
        p_rel = min(max(float(POLYMARKET_RELEGATION_PROBS.get(t, eps)), eps), 1.0 - eps)
        # soft relegation penalty only for teams market sees as genuine relegation risks
        rel_pen = 0.35 * math.log(p_rel / (1.0 - p_rel)) if p_rel >= 0.15 else 0.0
        score = (1.1 * math.log(p_title)
                 + 0.8 * math.log(p_ucl / (1.0 - p_ucl))
                 + 0.6 * math.log(p_top6 / (1.0 - p_top6))
                 - rel_pen)
        scores[t] = score
    values = list(scores.values())
    mu = sum(values) / len(values)
    var = sum((v - mu) ** 2 for v in values) / len(values)
    sd = var ** 0.5 or 1.0
    return {t: anchor_mean + (scores[t] - mu) / sd * spread for t in teams}


def build_varied_ratings(base_overall, base_attack, base_defense,
                         odds_overall, odds_attack, odds_defense,
                         external_overall, external_attack, external_defense,
                         rng, pull_to_mean_frac=0.0):
    """Return per-sim varied (overall, attack, defense) ratings.

    Each sim blends stats base ratings, Polymarket market-prior ratings, and the
    external ELO table (55% stats, 15% market, 30% external), pulls toward the
    league mean by the fraction of PL games left, then applies an independent ±5%
    multiplicative fluctuation per team.

    All six rating maps (overall/attack/defense for each of the three factors)
    are kept separate to preserve the attack/defence split integrity.
    """
    w_market = 0.15
    w_external = 0.30
    w_stats = 1.0 - w_market - w_external
    pull = max(0.0, min(1.0, pull_to_mean_frac))
    varied_overall = {}
    varied_attack = {}
    varied_defense = {}
    for t in base_overall:
        o = (w_stats * base_overall[t]
             + w_market * odds_overall.get(t, base_overall[t])
             + w_external * external_overall.get(t, base_overall[t]))
        a = (w_stats * base_attack[t]
             + w_market * odds_attack.get(t, base_attack[t])
             + w_external * external_attack.get(t, base_attack[t]))
        d = (w_stats * base_defense[t]
             + w_market * odds_defense.get(t, base_defense[t])
             + w_external * external_defense.get(t, base_defense[t]))
        if pull > 0.0:
            o = LEAGUE_AVERAGE_ELO + (o - LEAGUE_AVERAGE_ELO) * (1.0 - pull)
            a = LEAGUE_AVERAGE_ELO + (a - LEAGUE_AVERAGE_ELO) * (1.0 - pull)
            d = LEAGUE_AVERAGE_ELO + (d - LEAGUE_AVERAGE_ELO) * (1.0 - pull)
        o *= (0.95 + rng.float() * 0.10)
        a *= (0.95 + rng.float() * 0.10)
        d *= (0.95 + rng.float() * 0.10)
        varied_overall[t] = o
        varied_attack[t] = a
        varied_defense[t] = d
    return varied_overall, varied_attack, varied_defense


_STATS_CACHE = {"seed_key": None, "data": None}


def preset_pl_split_elos(recency_seed: int | None = None):
    """Return (overall, attack, defense) ratings derived from raw stats."""
    if _STATS_CACHE["data"] is None or _STATS_CACHE["seed_key"] != recency_seed:
        overall, attack, defense = _build_stats_ratings()
        _STATS_CACHE["data"] = (overall, attack, defense)
        _STATS_CACHE["seed_key"] = recency_seed
        spread = max(overall.values()) - min(overall.values())
        print(f"[STATS] PL ratings built from raw stats  "
              f"({len(overall)} teams, spread {spread:.0f}, "
              f"range {min(overall.values()):.0f}-{max(overall.values()):.0f})")
    return _STATS_CACHE["data"]


def preset_pl_elos(recency_seed: int | None = None):
    """Return just the overall (attack+defence)/2 rating dict."""
    overall, _attack, _defense = preset_pl_split_elos(recency_seed)
    return overall


# Keep the legacy state dict if anything else references it (e.g. dashboards).
_ML_STATE = {"loaded": True, "source": "stats", "cache": {}}

# =============================================================================
# CONSTANTS
# =============================================================================
HOME_ADVANTAGE_ELO = 40.0
ELO_SCALE = 400.0
LEAGUE_AVERAGE_ELO = 1800.0
PL_ELO_PULL = 0.75          # (kept for reference, no longer used for regression)
MAX_GOALS = 10
NUM_PL_SIMS = 2400
PL_TOTAL_FIXTURES = 380
PL_ELO_MAX_PULL = 1.0
BASE_HOME_XG = 1.662
BASE_AWAY_XG = 1.146
XG_ELO_SENSITIVITY = 0.0017
EXTRA_TIME_XG_FACTOR = 0.333

_ELO_LN_SCALE = math.log(10.0) / ELO_SCALE

_ELIM_ADJ = {0: 0.35, 1: 0.10, 2: -0.05, 3: -0.12, 4: -0.20, 5: -0.35}

# =============================================================================
# MAN CITY POINTS DEDUCTION
# =============================================================================
MAN_CITY_DEDUCTION_ENABLED = False

MAN_CITY_DEDUCTION_DIST = [
    (0.25,  0,   0),
    (0.02,  1,   9),
    (0.02,  10, 19),
    (0.10,  20, 29),
    (0.01,  30, 49),
    (0.31,  50, 75),
    (0.16,  None, None),
]


def sample_man_city_deduction(global_seed, sim_idx):
    if not MAN_CITY_DEDUCTION_ENABLED:
        return None
    rng = Rng(fixture_seed(global_seed, "ManCityPenalty", sim_idx, 0))
    r = rng.float()
    total = sum(p for p, _, _ in MAN_CITY_DEDUCTION_DIST)
    cum = 0.0
    for p, lo, hi in MAN_CITY_DEDUCTION_DIST:
        cum += p / total
        if r <= cum:
            if lo is None:
                return "EXPEL"
            return rng.randint(lo, hi)
    return 0

_FATIGUE_BASE = {"UCL": 8.0, "UEL": 6.0, "UECL": 5.0}

_EURO_K = {
    ("UCL", "league"): 16.0, ("UCL", "early_ko"): 20.0, ("UCL", "late_ko"): 24.0,
    ("UEL", "league"): 14.0, ("UEL", "early_ko"): 16.0, ("UEL", "late_ko"): 20.0,
    ("UECL", "league"): 12.0, ("UECL", "early_ko"): 14.0, ("UECL", "late_ko"): 16.0,
    ("PL", "league"): 20.0,
}

EURO_COMP_MEAN = {
    "UCL":  1820.0,
    "UEL":  1720.0,
    "UECL": 1620.0,
}

FINAL_VENUES = {
    "UCL": "Estadio Metropolitano",
    "UEL": "Stadion Frankfurt",
    "UECL": "Beşiktaş Stadium",
    "Carabao": "Wembley Stadium",
    "FA Cup": "Wembley Stadium",
}

TEAM_STADIUMS_RAW = {
    "Man City": "Etihad Stadium",
    "Arsenal": "Emirates Stadium",
    "Liverpool": "Anfield",
    "Man United": "Old Trafford",
    "Brighton": "Amex Stadium",
    "Bournemouth": "Vitality Stadium",
    "Brentford": "Brentford Community Stadium",
    "Aston Villa": "Villa Park",
    "Leeds": "Elland Road",
    "Everton": "Goodison Park",
    "Newcastle": "St. James' Park",
    "Chelsea": "Stamford Bridge",
    "Forest": "City Ground",
    "Fulham": "Craven Cottage",
    "Crystal Palace": "Selhurst Park",
    "West Ham": "London Stadium",
    "Sunderland": "Stadium of Light",
    "Tottenham": "Tottenham Hotspur Stadium",
    "Wolves": "Molineux",
    "Ipswich": "Portman Road",
    "Bradford City": "Valley Parade",
    "Peterborough United": "London Road",
    "Fleetwood Town": "Highbury Stadium",
}


def final_home_advantage(team_a, team_b, comp):
    venue = FINAL_VENUES.get(comp)
    if venue is None:
        return 0.0, 0.0
    return (HOME_ADVANTAGE_ELO if TEAM_STADIUMS_RAW.get(team_a) == venue else 0.0,
            HOME_ADVANTAGE_ELO if TEAM_STADIUMS_RAW.get(team_b) == venue else 0.0)


def fatigue_penalty(elim_round, comp):
    if elim_round < 0:
        return 0.0
    base = _FATIGUE_BASE.get(comp, 0.0)
    return base * min(elim_round, 5) / 5.0


def fatigue_base(comp):
    return _FATIGUE_BASE.get(comp, 0.0)


def euro_k(comp, stage):
    return _EURO_K.get((comp, stage), 20.0)


def knockout_k(comp, round_idx):
    return euro_k(comp, "early_ko" if round_idx in (0, 1) else "late_ko")


# =============================================================================
# RNG WRAPPER + POISSON
# =============================================================================
class Rng:
    __slots__ = ('_rng',)

    def __init__(self, seed):
        self._rng = random.Random(seed)

    def float(self):
        return self._rng.random()

    @property
    def random(self):
        return self._rng.random

    def randint(self, low, high):
        return self._rng.randint(low, high)

    def poisson(self, lam):
        return self.poisson_L(math.exp(-lam))

    def poisson_L(self, L):
        random = self._rng.random
        k = 0
        p = 1.0
        while True:
            k += 1
            p *= random()
            if p <= L:
                return k - 1

    def shuffle(self, lst):
        self._rng.shuffle(lst)

    def sample(self, population, k):
        return self._rng.sample(population, k)


# =============================================================================
# DETERMINISTIC SEED + DIRECT FIXTURE SAMPLING HELPERS
# =============================================================================

_SCRATCH_RNG = random.Random()


def sub_seed(global_seed, comp, sim_idx):
    h = (global_seed * 0x9E3779B97F4A7C15 + sim_idx * 0xBF584B0B4E5E3B7D) & 0xFFFFFFFFFFFFFFFF
    h = (h ^ (h >> 30)) & 0xFFFFFFFFFFFFFFFF
    h = (h * 0xBF584B0B4E5E3B7D) & 0xFFFFFFFFFFFFFFFF
    h = (h ^ (h >> 27)) & 0xFFFFFFFFFFFFFFFF
    h = (h * 0x94D049BB133111EB) & 0xFFFFFFFFFFFFFFFF
    h = (h ^ (h >> 31)) & 0xFFFFFFFFFFFFFFFF
    h = (h + hash(comp) * 0x9E3779B97F4A7C15) & 0xFFFFFFFFFFFFFFFF
    return h


def fixture_seed(global_seed, comp, sim_idx, fix_idx):
    h = (global_seed * 0x9E3779B97F4A7C15 + sim_idx * 0xBF584B0B4E5E3B7D) & 0xFFFFFFFFFFFFFFFF
    h = (h ^ (h >> 30)) & 0xFFFFFFFFFFFFFFFF
    h = (h * 0xBF584B0B4E5E3B7D) & 0xFFFFFFFFFFFFFFFF
    h = (h ^ (h >> 27)) & 0xFFFFFFFFFFFFFFFF
    h = (h * 0x94D049BB133111EB) & 0xFFFFFFFFFFFFFFFF
    h = (h ^ (h >> 31)) & 0xFFFFFFFFFFFFFFFF
    h = (h + fix_idx * 0xBF584B0B4E5E3B7D + hash(comp) * 0x9E3779B97F4A7C15) & 0xFFFFFFFFFFFFFFFF
    return h


def input_sig(*parts):
    h = hash(repr(parts)) & 0xFFFFFFFFFFFFFFFF
    h = (h ^ (h >> 30)) & 0xFFFFFFFFFFFFFFFF
    h = (h * 0xBF584B0B4E5E3B7D) & 0xFFFFFFFFFFFFFFFF
    h = (h ^ (h >> 27)) & 0xFFFFFFFFFFFFFFFF
    h = (h * 0x94D049BB133111EB) & 0xFFFFFFFFFFFFFFFF
    h = (h ^ (h >> 31)) & 0xFFFFFFFFFFFFFFFF
    return h.to_bytes(8, 'little', signed=False)


def _poisson_inline(rnd, lam):
    L = math.exp(-lam)
    k = 0
    p = 1.0
    while True:
        k += 1
        p *= rnd()
        if p <= L:
            v = k - 1
            return v if v < MAX_GOALS else MAX_GOALS


def sample_score_seeded(seed, lam_h, lam_a):
    _SCRATCH_RNG.seed(seed)
    rnd = _SCRATCH_RNG.random
    return _poisson_inline(rnd, lam_h), _poisson_inline(rnd, lam_a)


# =============================================================================
# ELO / GOAL HELPERS
# =============================================================================
def update_elo(elo_a, elo_b, k, score_a, goal_diff=None):
    """Update Elo for a match between A and B.

    score_a ∈ {0.0, 0.5, 1.0} is the result from A's perspective.
    goal_diff (if given) scales the update via the margin-of-victory multiplier.
    """
    exp_a = 1.0 / (1.0 + math.exp((elo_b - elo_a) * _ELO_LN_SCALE))
    mult = margin_of_victory_multiplier(goal_diff) if goal_diff is not None else 1.0
    delta = k * (score_a - exp_a) * mult
    return elo_a + delta, elo_b - delta


def margin_of_victory_multiplier(goal_diff):
    if goal_diff <= 0:
        return 1.0
    g = float(abs(goal_diff))
    return min((g + 1.0) / 1.5, 2.25)


def pen_win_probability(elo_h, elo_a):
    p = 1.0 / (1.0 + math.exp((elo_a - elo_h) * _ELO_LN_SCALE))
    return max(0.40, min(0.60, p))


def expected_goals(h_elo, a_elo, atk_h=None, def_h=None, atk_a=None, def_a=None, home_adv=HOME_ADVANTAGE_ELO):
    if atk_h is not None and def_h is not None and atk_a is not None and def_a is not None:
        return expected_goals_split(atk_h, def_h, atk_a, def_a, home_adv=home_adv)
    d = h_elo + home_adv - a_elo
    return (min(BASE_HOME_XG * math.exp(XG_ELO_SENSITIVITY * d), 5.5),
            min(BASE_AWAY_XG * math.exp(-XG_ELO_SENSITIVITY * d), 5.5))


def expected_goals_split(atk_h, def_h, atk_a, def_a, home_adv=HOME_ADVANTAGE_ELO):
    d_h = atk_h - def_a + home_adv
    d_a = atk_a - def_h
    return (min(BASE_HOME_XG * math.exp(XG_ELO_SENSITIVITY * d_h), 5.5),
            min(BASE_AWAY_XG * math.exp(XG_ELO_SENSITIVITY * d_a), 5.5))


def precompute_elo_factors(atk_table, def_table, home_adv=HOME_ADVANTAGE_ELO):
    """Precompute exp(XG_ELO_SENSITIVITY * diff) factors per team to avoid
    calling math.exp per fixture in hot loops.

    Returns (exp_atk, exp_neg_def, exp_home) where:
      - exp_atk[t]     = exp(SENS * atk[t])   — multiply for attacker
      - exp_neg_def[t] = exp(-SENS * def[t])  — multiply for defender
      - exp_home       = exp(SENS * home_adv)
    """
    s = XG_ELO_SENSITIVITY
    exp_atk = {t: math.exp(s * a) for t, a in atk_table.items()}
    exp_neg_def = {t: math.exp(-s * d) for t, d in def_table.items()}
    exp_home = math.exp(s * home_adv)
    return exp_atk, exp_neg_def, exp_home


def compute_lam_h(lam_h_base, exp_atk_h, exp_neg_def_a, exp_home):
    return min(lam_h_base * exp_home * exp_atk_h * exp_neg_def_a, 5.5)


def compute_lam_a(lam_a_base, exp_atk_a, exp_neg_def_h, exp_home):
    return min(lam_a_base * exp_atk_a * exp_neg_def_h, 5.5)


def sample_score(rng, lam_h, lam_a):
    h = min(rng.poisson(lam_h), MAX_GOALS)
    a = min(rng.poisson(lam_a), MAX_GOALS)
    return (h, a)


def max_consecutive_wins(results):
    best = cur = 0
    for r in results:
        cur = cur + 1 if r == 'W' else 0
        best = max(best, cur)
    return best


# =============================================================================
# DATA TABLES
# =============================================================================
def preset_ucl_elos():
    rows = [
        ("Arsenal", 2151.0), ("Bayern Munich", 2088.0), ("FC Barcelona", 2042.0),
        ("Paris Saint-Germain", 2104.0), ("Man City", 2022.0), ("Real Madrid", 2036.0),
        ("Sporting CP", 1869.0), ("Aston Villa", 1985.0), ("Inter Milan", 1908.0),
        ("Borussia Dortmund", 1910.0), ("Atletico Madrid", 1931.0), ("Liverpool", 1967.0),
        ("Man United", 1883.0), ("Roma", 1863.0), ("Real Betis", 1859.0),
        ("Bodø/Glimt", 1820.0), ("Club Brugge", 1888.0), ("FC Porto", 1831.0),
        ("Como", 1843.0), ("PSV Eindhoven", 1817.0), ("RB Leipzig", 1811.0),
        ("VfB Stuttgart", 1795.0), ("Napoli", 1787.0), ("Villarreal FC", 1764.0),
        ("Viking", 1729.0), ("RC Lens", 1773.0), ("AEK Athens", 1688.0),
        ("Fenerbahçe", 1721.0), ("Lille OSC", 1761.0), ("Galatasaray", 1792.0),
        ("Shakhtar Donetsk", 1670.0), ("Feyenoord", 1716.0), ("Slavia Prague", 1668.0),
        ("Sabah FK", 1563.0), ("LASK", 1614.0), ("Slovan Bratislava", 1549.0),
    ]
    return dict(rows)


def preset_uel_elos():
    rows = [
        ("Bayer Leverkusen", 1857.0), ("Benfica", 1898.0), ("Union Saint-Gilloise", 1843.0),
        ("Juventus", 1819.0), ("Bournemouth", 1943.0), ("Milan", 1812.0),
        ("Crystal Palace", 1794.0), ("Olympique Lyonnais", 1788.0), ("Olympiacos", 1755.0),
        ("Rennes", 1760.0), ("Sunderland", 1799.0), ("Omonia", 1650.0),
        ("Real Sociedad", 1747.0), ("Celta Vigo", 1720.0), ("Dinamo Zagreb", 1653.0),
        ("Marseille", 1718.0), ("Celtic", 1610.0), ("Lech Poznań", 1669.0),
        ("Sparta Prague", 1601.0), ("TSG Hoffenheim", 1712.0), ("Hapoel Be'er Sheva", 1604.0),
        ("Beşiktaş", 1647.0), ("Viktoria Plzeň", 1550.0), ("Red Bull Salzburg", 1635.0),
        ("AZ Alkmaar", 1636.0), ("Sturm Graz", 1606.0), ("Anderlecht", 1652.0),
        ("NK Celje", 1531.0), ("Levski Sofia", 1561.0), ("Jagiellonia Białystok", 1542.0),
        ("NEC Nijmegen", 1566.0), ("OFI Crete", 1465.0), ("Lillestrøm", 1487.0),
        ("Torreense", 1413.0), ("Ararat-Armenia", 1454.0), ("Ferencváros", 1702.0),
    ]
    return dict(rows)


def preset_uecl_elos():
    rows = [
        ("Brighton", 1940.0), ("Monaco", 1804.0), ("Freiburg", 1789.0),
        ("Atalanta", 1724.0), ("Midtjylland", 1732.0), ("Red Star Belgrade", 1630.0),
        ("Braga", 1687.0), ("Lugano", 1698.0), ("Ajax", 1695.0),
        ("FC Copenhagen", 1677.0), ("Panathinaikos", 1690.0), ("Getafe", 1662.0),
        ("Twente", 1674.0), ("Gent", 1653.0), ("Hajduk Split", 1623.0),
        ("FC Nordsjaelland", 1597.0), ("Universitatea Craiova", 1595.0), ("Trabzonspor", 1654.0),
        ("Pafos FC", 1557.0), ("Thun", 1500.0), ("AGF", 1564.0),
        ("Sint Truiden", 1602.0), ("Hearts", 1517.0), ("Brann", 1552.0),
        ("FK Jablonec", 1480.0), ("FK Riga", 1511.0), ("Borac Banja Luka", 1501.0),
        ("Mjallby", 1434.0), ("Egnatia Rrogozhine", 1500.0), ("CSKA Sofia", 1465.0),
        ("KuPS Kuopio", 1429.0), ("Inter Club d'Escaldes", 1420.0), ("Kairat", 1423.0),
        ("FK Kauno Zalgiris", 1392.0), ("Iberia", 1403.0), ("Lincoln Red Imps", 1357.0),
    ]
    return dict(rows)


def association_map():
    rows = [
        ("AEK Athens", "Greece"), ("LASK", "Austria"), ("Club Brugge", "Belgium"),
        ("Aston Villa", "England"), ("Borussia Dortmund", "Germany"), ("Villarreal FC", "Spain"),
        ("FC Porto", "Portugal"), ("Man City", "England"), ("Lille OSC", "France"),
        ("Real Betis", "Spain"), ("Real Madrid", "Spain"), ("Inter Milan", "Italy"),
        ("FC Barcelona", "Spain"), ("Feyenoord", "Netherlands"), ("VfB Stuttgart", "Germany"),
        ("Viking", "Norway"), ("Liverpool", "England"), ("Atletico Madrid", "Spain"),
        ("Paris Saint-Germain", "France"), ("Slovan Bratislava", "Slovakia"),
        ("Sporting CP", "Portugal"), ("Galatasaray", "Turkey"), ("Napoli", "Italy"),
        ("Arsenal", "England"), ("Fenerbahçe", "Turkey"), ("Roma", "Italy"),
        ("PSV Eindhoven", "Netherlands"), ("Shakhtar Donetsk", "Ukraine"),
        ("Como", "Italy"), ("RB Leipzig", "Germany"), ("Bayern Munich", "Germany"),
        ("Bodø/Glimt", "Norway"), ("Man United", "England"), ("Sabah FK", "Azerbaijan"),
        ("Slavia Prague", "Czech Republic"), ("RC Lens", "France"),
        ("Ararat-Armenia", "Armenia"), ("Sparta Prague", "Czech Republic"),
        ("Omonia", "Cyprus"), ("Celta Vigo", "Spain"), ("Milan", "Italy"),
        ("Benfica", "Portugal"), ("Bayer Leverkusen", "Germany"), ("NK Celje", "Slovenia"),
        ("Hapoel Be'er Sheva", "Israel"), ("Dinamo Zagreb", "Croatia"), ("Olympiacos", "Greece"),
        ("Jagiellonia Białystok", "Poland"), ("Anderlecht", "Belgium"),
        ("Olympique Lyonnais", "France"), ("Sturm Graz", "Austria"), ("Rennes", "France"),
        ("Sunderland", "England"), ("AZ Alkmaar", "Netherlands"), ("OFI Crete", "Greece"),
        ("TSG Hoffenheim", "Germany"), ("Levski Sofia", "Bulgaria"), ("Red Bull Salzburg", "Austria"),
        ("Beşiktaş", "Turkey"), ("Marseille", "France"), ("Celtic", "Scotland"),
        ("Ferencváros", "Hungary"), ("Crystal Palace", "England"), ("Lech Poznań", "Poland"),
        ("Viktoria Plzeň", "Czech Republic"), ("Union Saint-Gilloise", "Belgium"),
        ("Juventus", "Italy"), ("NEC Nijmegen", "Netherlands"), ("Lillestrøm", "Norway"),
        ("Torreense", "Portugal"), ("Real Sociedad", "Spain"), ("Bournemouth", "England"),
        ("Lugano", "Switzerland"), ("Red Star Belgrade", "Serbia"), ("Hajduk Split", "Croatia"),
        ("Ajax", "Netherlands"), ("Gent", "Belgium"), ("AGF", "Denmark"),
        ("Egnatia Rrogozhine", "Albania"), ("Midtjylland", "Denmark"), ("KuPS Kuopio", "Finland"),
        ("Trabzonspor", "Turkey"), ("Mjallby", "Sweden"), ("Inter Club d'Escaldes", "Andorra"),
        ("Panathinaikos", "Greece"), ("Borac Banja Luka", "Bosnia"), ("CSKA Sofia", "Bulgaria"),
        ("Monaco", "France"), ("FK Riga", "Latvia"), ("Kairat", "Kazakhstan"),
        ("Universitatea Craiova", "Romania"), ("Getafe", "Spain"), ("Atalanta", "Italy"),
        ("Pafos FC", "Cyprus"), ("Brighton", "England"), ("FK Kauno Zalgiris", "Lithuania"),
        ("FC Copenhagen", "Denmark"), ("Braga", "Portugal"), ("Twente", "Netherlands"),
        ("Thun", "Switzerland"), ("Hearts", "Scotland"), ("FC Nordsjaelland", "Denmark"),
        ("Sint Truiden", "Belgium"), ("Iberia", "Georgia"), ("Freiburg", "Germany"),
        ("FK Jablonec", "Czech Republic"), ("Brann", "Norway"), ("Lincoln Red Imps", "Gibraltar"),
    ]
    return dict(rows)


def assoc_entrants():
    rows = [
        ("England", 9), ("Spain", 8), ("Italy", 8), ("Germany", 8), ("France", 7),
        ("Netherlands", 6), ("Portugal", 6), ("Belgium", 5), ("Turkey", 5),
        ("Czech Republic", 5), ("Austria", 5), ("Greece", 5), ("Switzerland", 4),
        ("Scotland", 4), ("Denmark", 4), ("Norway", 4), ("Poland", 4), ("Croatia", 4),
        ("Serbia", 3), ("Romania", 3), ("Israel", 3), ("Cyprus", 3), ("Sweden", 3),
        ("Bulgaria", 3), ("Hungary", 3), ("Slovakia", 3), ("Slovenia", 2),
        ("Azerbaijan", 2), ("Kazakhstan", 2), ("Ukraine", 2), ("Russia", 2),
        ("Bosnia", 2), ("Albania", 2), ("Armenia", 2), ("Georgia", 2),
        ("Finland", 2), ("Latvia", 2), ("Lithuania", 2), ("Andorra", 1), ("Gibraltar", 1),
    ]
    return dict(rows)


# =============================================================================
# MANAGER DATA
# =============================================================================
MANAGER_DATA = {
    "Arsenal":        ("Mikel Arteta",       "Spain",    1, 1.5),
    "Aston Villa":    ("Unai Emery",         "Spain",    5, 1.2),
    "Bournemouth":    ("Marco Rose",         "Germany", 10, 1.0),
    "Brentford":      ("Keith Andrews",      "Ireland", 10, 0.9),
    "Brighton":       ("Fabian Hürzeler",    "Germany",  8, 1.1),
    "Chelsea":        ("Xabi Alonso",        "Spain",    6, 1.4),
    "Coventry":       ("Frank Lampard",      "England", 19, 1.0),
    "Crystal Palace": ("Pierre Sage",        "France",  12, 0.95),
    "Everton":        ("David Moyes",        "Scotland",13, 1.0),
    "Fulham":         ("Álvaro Arbeloa",     "Spain",   15, 0.95),
    "Hull":           ("Sergej Jakirović",   "Croatia", 19, 1.0),
    "Ipswich":        ("Gary O'Neil",        "England", 20, 1.0),
    "Leeds":          ("Daniel Farke",       "Germany", 14, 1.0),
    "Liverpool":      ("Andoni Iraola",      "Spain",    4, 1.5),
    "Man City":       ("Enzo Maresca",       "Italy",    2, 1.5),
    "Man United":     ("Michael Carrick",    "England",  5, 1.7),
    "Newcastle":      ("Matthias Jaissle",   "Germany",  8, 1.2),
    "Forest":         ("Oliver Glasner",     "Austria", 13, 1.05),
    "Sunderland":     ("Régis Le Bris",      "France",  16, 0.95),
    "Tottenham":      ("Roberto De Zerbi",   "Italy",    9, 1.4),
}


RECENT_HONOURS = {
    "Arsenal":        {"pl_champion_recent": 2},
    "Aston Villa":    {"european_winner_last": "UEL"},
    "Crystal Palace": {"european_winner_last": "UECL"},
}

EURO_RISK_WEIGHT = {
    "UCL": 1.00,
    "UEL": 0.60,
    "UECL": 0.35,
}


def european_sack_adjustment(team, res, comp, weight):
    if team not in res.elim_rounds:
        return 0.0
    try:
        pos = res.ranking.index(team) + 1
    except ValueError:
        return 0.0
    elim = res.elim_rounds.get(team, -1)
    expected_pos = comp.elo_rank.get(team, 24)
    adj = 0.0
    if pos > expected_pos + 8:
        adj += 0.25 * weight
    elif pos > expected_pos + 4:
        adj += 0.12 * weight
    if pos > 24:
        adj += 0.60 * weight
    else:
        adj += _ELIM_ADJ.get(elim, 0.0) * weight
    return adj


ACTUAL_RESULTS_ARR = [
    (("Arsenal", "Coventry"), (3, 0)), (("Hull", "Man United"), (2, 0)),
    (("Everton", "Crystal Palace"), (2, 0)), (("Ipswich", "Sunderland"), (2, 1)),
    (("Forest", "Leeds"), (0, 1)), (("Brentford", "Tottenham"), (3, 0)),
    (("Brighton", "Aston Villa"), (4, 0)), (("Man City", "Bournemouth"), (2, 1)),
    (("Newcastle", "Liverpool"), (2, 2)), (("Fulham", "Chelsea"), (2, 3)),
    (("Crystal Palace", "Man City"), (1, 4)), (("Liverpool", "Forest"), (2, 2)),
    (("Bournemouth", "Everton"), (1, 1)), (("Coventry", "Hull"), (0, 1)),
    (("Tottenham", "Newcastle"), (0, 2)), (("Chelsea", "Brighton"), (4, 3)),
    (("Leeds", "Brentford"), (1, 1)), (("Sunderland", "Fulham"), (1, 0)),
    (("Man United", "Ipswich"), (5, 2)), (("Aston Villa", "Arsenal"), (0, 1)),
    (("Ipswich", "Liverpool"), (0, 2)), (("Newcastle", "Bournemouth"), (2, 2)),
    (("Brentford", "Sunderland"), (1, 1)), (("Brighton", "Leeds"), (1, 1)),
    (("Fulham", "Crystal Palace"), (2, 3)), (("Man City", "Coventry"), (1, 0)),
    (("Forest", "Tottenham"), (0, 0)), (("Hull", "Aston Villa"), (0, 0)),
    (("Everton", "Man United"), (2, 2)), (("Arsenal", "Chelsea"), (2, 1)),
    (("Aston Villa", "Forest"), (1, 2)), (("Bournemouth", "Brentford"), (2, 2)),
    (("Chelsea", "Hull"), (2, 2)), (("Crystal Palace", "Ipswich"), (2, 3)),
    (("Liverpool", "Fulham"), (0, 0)), (("Tottenham", "Everton"), (0, 0)),
    (("Sunderland", "Arsenal"), (0, 2)), (("Coventry", "Brighton"), (0, 5)),
    (("Man United", "Man City"), (0, 1)), (("Leeds", "Newcastle"), (4, 1)),
    (("Brentford", "Chelsea"), (3, 0)), (("Tottenham", "Aston Villa"), (2, 3)),
    (("Brighton", "Arsenal"), (3, 0)), (("Everton", "Ipswich"), (1, 0)),
    (("Newcastle", "Hull"), (2, 1)), (("Forest", "Coventry"), (0, 1)),
    (("Bournemouth", "Liverpool"), (0, 1)), (("Leeds", "Crystal Palace"), (0, 0)),
    (("Man City", "Sunderland"), (5, 3)), (("Fulham", "Man United"), (1, 1)),
    (("Arsenal", "Leeds"), (2, 1)), (("Chelsea", "Bournemouth"), (5, 1)),
    (("Sunderland", "Brighton"), (0, 2)), (("Aston Villa", "Brentford"), (2, 2)),
    (("Ipswich", "Fulham"), (2, 1)), (("Man United", "Tottenham"), (1, 1)),
    (("Coventry", "Newcastle"), (4, 1)), (("Crystal Palace", "Forest"), (3, 1)),
    (("Hull", "Everton"), (2, 2)), (("Liverpool", "Man City"), (0, 3)),
    (("Everton", "Chelsea"), (0, 2)), (("Brentford", "Liverpool"), (1, 2)),
    (("Fulham", "Hull"), (1, 0)), (("Man City", "Ipswich"), (3, 2)),
    (("Newcastle", "Aston Villa"), (0, 1)), (("Brighton", "Crystal Palace"), (5, 0)),
    (("Bournemouth", "Sunderland"), (2, 0)), (("Leeds", "Man United"), (0, 1)),
    (("Forest", "Arsenal"), (0, 1)), (("Tottenham", "Coventry"), (3, 1)),
    (("Ipswich", "Forest"), (1, 1)), (("Aston Villa", "Man City"), (2, 1)),
    (("Arsenal", "Everton"), (2, 0)), (("Coventry", "Fulham"), (0, 1)),
    (("Chelsea", "Tottenham"), (0, 2)),(("Crystal Palace", "Newcastle"), (0, 2)),
    (("Hull", "Brentford"), (1, 1)),(("Liverpool", "Brighton"), (2, 0)),
    (("Man United", "Bournemouth"), (0, 3)),(("Sunderland", "Leeds"), (0, 0)),
    (("Chelsea", "Man United"), (2, 0)),(("Bournemouth", "Leeds"), (2, 0)),
    (("Brentford", "Forest"), (2, 0)),(("Coventry", "Sunderland"), (3, 1)),
    (("Hull", "Ipswich"), (2, 2)),(("Man City", "Brighton"), (0, 1)),
    (("Tottenham", "Crystal Palace"), (2, 0)),(("Aston Villa", "Fulham"), (1, 1)),
    (("Liverpool", "Arsenal"), (0, 1)),(("Newcastle", "Everton"), (0, 1)),
    (("Everton", "Coventry"), (3, 1)), (("Leeds", "Tottenham"), (1, 0)),
    (("Arsenal", "Hull"), (1, 0)), (("Fulham", "Newcastle"), (1, 1)),
    (("Forest", "Man City"), (3, 1)),(("Brighton", "Brentford"), (2, 0)),
    (("Crystal Palace", "Liverpool"), (1, 3)),(("Ipswich", "Bournemouth"), (1, 2)),
    (("Sunderland", "Chelsea"), (1, 0)),(("Man United", "Aston Villa"), (4, 4)),
]



CL_FIXTURES_ARR = [
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
    [("Fenerbahçe", "Slavia Prague"), ("Sabah FK", "Borussia Dortmund"), ("Roma", "Slovan Bratislava"),
     ("FC Porto", "PSV Eindhoven"), ("Liverpool", "Villarreal FC"), ("Man City", "AEK Athens"),
     ("Paris Saint-Germain", "FC Barcelona"), ("Napoli", "Bodø/Glimt"),
     ("VfB Stuttgart", "Atletico Madrid"), ("Como", "Man United"), ("Lille OSC", "Galatasaray"),
     ("Aston Villa", "Viking"), ("Club Brugge", "RC Lens"), ("Bayern Munich", "Arsenal"),
     ("Inter Milan", "Shakhtar Donetsk"), ("Real Madrid", "RB Leipzig"), ("Real Betis", "Feyenoord"),
     ("Sporting CP", "LASK")],
    [("Shakhtar Donetsk", "Sporting CP"), ("Galatasaray", "VfB Stuttgart"), ("Atletico Madrid", "Bayern Munich"),
     ("FC Barcelona", "Aston Villa"), ("Feyenoord", "Inter Milan"), ("Bodø/Glimt", "Lille OSC"),
     ("LASK", "Slovan Bratislava"), ("Man United", "Roma"), ("Villarreal FC", "Paris Saint-Germain"),
     ("AEK Athens", "Real Madrid"), ("Fenerbahçe", "Liverpool"), ("Borussia Dortmund", "Real Betis"),
     ("FC Porto", "Napoli"), ("PSV Eindhoven", "Club Brugge"), ("RB Leipzig", "Man City"),
     ("RC Lens", "Como"), ("Slavia Prague", "Arsenal"), ("Viking", "Sabah FK")],
    [("Bodø/Glimt", "LASK"), ("Galatasaray", "Aston Villa"), ("Arsenal", "Borussia Dortmund"),
     ("Como", "AEK Athens"), ("Feyenoord", "FC Porto"), ("Man City", "Napoli"), ("RB Leipzig", "RC Lens"),
     ("Real Madrid", "PSV Eindhoven"), ("Slovan Bratislava", "Real Betis"), ("Sabah FK", "FC Barcelona"),
     ("Slavia Prague", "Villarreal FC"), ("Atletico Madrid", "Viking"), ("Club Brugge", "Liverpool"),
     ("Inter Milan", "VfB Stuttgart"), ("Shakhtar Donetsk", "Fenerbahçe"), ("Lille OSC", "Bayern Munich"),
     ("Paris Saint-Germain", "Roma"), ("Sporting CP", "Man United")],
    [("Viking", "Feyenoord"), ("Villarreal FC", "Sabah FK"), ("AEK Athens", "Galatasaray"),
     ("Roma", "Sporting CP"), ("Aston Villa", "Paris Saint-Germain"), ("FC Barcelona", "Man City"),
     ("Bayern Munich", "Slavia Prague"), ("Man United", "RB Leipzig"), ("Napoli", "Club Brugge"),
     ("Real Betis", "Como"), ("Slovan Bratislava", "Shakhtar Donetsk"), ("Arsenal", "Real Madrid"),
     ("Borussia Dortmund", "Inter Milan"), ("LASK", "Fenerbahçe"), ("Liverpool", "FC Porto"),
     ("PSV Eindhoven", "Atletico Madrid"), ("RC Lens", "Bodø/Glimt"), ("VfB Stuttgart", "Lille OSC")],
    [("Bodø/Glimt", "Atletico Madrid"), ("Galatasaray", "Feyenoord"), ("AEK Athens", "Roma"),
     ("Aston Villa", "Borussia Dortmund"), ("Inter Milan", "Liverpool"), ("FC Porto", "Slavia Prague"),
     ("Lille OSC", "Slovan Bratislava"), ("Real Madrid", "LASK"), ("VfB Stuttgart", "Club Brugge"),
     ("Fenerbahçe", "Villarreal FC"), ("Sabah FK", "Napoli"), ("Como", "Paris Saint-Germain"),
     ("Man United", "Bayern Munich"), ("RB Leipzig", "Shakhtar Donetsk"), ("RC Lens", "Man City"),
     ("Real Betis", "Arsenal"), ("Sporting CP", "FC Barcelona"), ("Viking", "PSV Eindhoven")],
    [("Arsenal", "Sabah FK"), ("Roma", "Lille OSC"), ("Atletico Madrid", "Fenerbahçe"),
     ("Borussia Dortmund", "AEK Athens"), ("Club Brugge", "Bodø/Glimt"), ("Bayern Munich", "Real Betis"),
     ("FC Barcelona", "Como"), ("Shakhtar Donetsk", "Real Madrid"), ("Feyenoord", "RB Leipzig"),
     ("LASK", "FC Porto"), ("Liverpool", "RC Lens"), ("Man City", "Sporting CP"),
     ("Paris Saint-Germain", "Galatasaray"), ("PSV Eindhoven", "VfB Stuttgart"),
     ("Slavia Prague", "Aston Villa"), ("Napoli", "Viking"), ("Villarreal FC", "Man United"),
     ("Slovan Bratislava", "Inter Milan")],
]

CL_ACTUAL_RESULTS_ARR = [
    (("AEK Athens", "LASK"), (1, 0)), (("Club Brugge", "Aston Villa"), (2, 3)),
    (("Borussia Dortmund", "Villarreal FC"), (3, 2)), (("FC Porto", "Man City"), (0, 2)),
    (("Lille OSC", "Real Betis"), (2, 3)), (("Real Madrid", "Inter Milan"), (2, 1)),
    (("FC Barcelona", "Feyenoord"), (5, 1)), (("VfB Stuttgart", "Viking"), (3, 1)),
    (("Liverpool", "Atletico Madrid"), (2, 1)), (("Paris Saint-Germain", "Slovan Bratislava"), (6, 1)),
    (("Sporting CP", "Galatasaray"), (3, 1)), (("Napoli", "Arsenal"), (0, 1)),
    (("Fenerbahçe", "Roma"), (1, 1)), (("PSV Eindhoven", "Shakhtar Donetsk"), (1, 1)),
    (("Como", "RB Leipzig"), (4, 1)), (("Bayern Munich", "Bodø/Glimt"), (5, 0)),
    (("Man United", "Sabah FK"), (4, 0)), (("Slavia Prague", "RC Lens"), (2, 3)),
    (("RC Lens", "Sporting CP"), (0, 2)), (("Sabah FK", "Slavia Prague"), (2, 0)),
    (("Arsenal", "Lille OSC"), (3, 0)), (("Atletico Madrid", "Man United"), (2, 0)),
    (("Galatasaray", "FC Barcelona"), (1, 4)), (("Inter Milan", "Club Brugge"), (3, 4)),
    (("RB Leipzig", "PSV Eindhoven"), (1, 0)), (("Viking", "Bayern Munich"), (3, 3)),
    (("Villarreal FC", "Napoli"), (3, 1)), (("LASK", "Liverpool"), (3, 6)),
    (("Feyenoord", "Como"), (3, 2)), (("Man City", "Paris Saint-Germain"), (2, 4)),
    (("Roma", "Real Madrid"), (3, 4)), (("Bodø/Glimt", "Borussia Dortmund"), (1, 0)),
    (("Real Betis", "FC Porto"), (3, 2)), (("Shakhtar Donetsk", "AEK Athens"), (3, 1)),
    (("Slovan Bratislava", "VfB Stuttgart"), (0, 3)), (("Aston Villa", "Fenerbahçe"), (6, 0)),
    (("Fenerbahçe", "Slavia Prague"), (2, 2)),
    (("Sabah FK", "Borussia Dortmund"), (1, 2)),
    (("Paris Saint-Germain", "FC Barcelona"), (3, 2)),
    (("Liverpool", "Villarreal FC"), (4, 2)),
    (("Man City", "AEK Athens"), (5, 1)),
    (("Roma", "Slovan Bratislava"), (4, 0)),
    (("FC Porto", "PSV Eindhoven"), (0, 1)),
    (("Napoli", "Bodø/Glimt"), (2, 2)),
    (("VfB Stuttgart", "Atletico Madrid"), (2, 2)),
    (("Como", "Man United"), (4, 1)),
    (("Lille OSC", "Galatasaray"), (2, 4)),
    (("Aston Villa", "Viking"), (3, 1)),
    (("Club Brugge", "RC Lens"), (3, 0)),
    (("Bayern Munich", "Arsenal"), (2, 2)),
    (("Inter Milan", "Shakhtar Donetsk"), (1, 0)),
    (("Real Betis", "Feyenoord"), (1, 0)),
    (("Real Madrid", "RB Leipzig"), (4, 1)),
    (("Sporting CP", "LASK"), (2, 3)),
    # Round 4 in-progress / upcoming (added 2026-11-03)
    (("Galatasaray", "VfB Stuttgart"), (2, 0)),
    (("Shakhtar Donetsk", "Sporting CP"), (0, 1)),
    (("Man United", "Roma"), (3, 2)),
    (("FC Barcelona", "Aston Villa"), (3, 0)),
    (("Atletico Madrid", "Bayern Munich"), (0, 2)),
    (("Feyenoord", "Inter Milan"), (0, 3)),
    (("Villarreal FC", "Paris Saint-Germain"), (0, 6)),
    (("Bodø/Glimt", "Lille OSC"), (0, 0)),
    (("LASK", "Slovan Bratislava"), (4, 0)),
    (("Fenerbahçe", "Liverpool"), (3, 2)),
    (("AEK Athens", "Real Madrid"), (2, 3)),
    (("Slavia Prague", "Arsenal"), (0, 1)),
    (("RC Lens", "Como"), (0, 1)),
    (("FC Porto", "Napoli"), (1, 0)),
    (("Viking", "Sabah FK"), (1, 1)),
    (("Borussia Dortmund", "Real Betis"), (0, 0)),
    (("RB Leipzig", "Man City"), (0, 0)),
    (("PSV Eindhoven", "Club Brugge"), (0, 1)),
]

UEL_FIXTURES_RAW = [
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
     ("Benfica", "AZ Alkmaar"), ("Sunderland", "Levski Sofia"), ("Hoffenheim", "Ferencváros")],
]

UEL_NAME_MAP = {
    "Sparta Praha": "Sparta Prague", "Celta": "Celta Vigo",
    "Leverkusen": "Bayer Leverkusen", "Celje": "NK Celje",
    "H. Beer-Sheva": "Hapoel Be'er Sheva", "GNK Dinamo": "Dinamo Zagreb",
    "Lyon": "Olympique Lyonnais", "Salzburg": "Red Bull Salzburg",
    "Hoffenheim": "TSG Hoffenheim", "N.E.C.": "NEC Nijmegen",
    "Union SG": "Union Saint-Gilloise", "Jagiellonia": "Jagiellonia Białystok",
}


def standardise_uel(name):
    return UEL_NAME_MAP.get(name, name)


UEL_ACTUAL_RESULTS_ARR = [
    (("Ararat-Armenia", "Sparta Prague"), (1, 4)), (("Omonia", "Celta Vigo"), (1, 0)),
    (("Milan", "Benfica"), (0, 2)), (("Bayer Leverkusen", "NK Celje"), (2, 0)),
    (("Hapoel Be'er Sheva", "Dinamo Zagreb"), (0, 0)), (("Olympiacos", "Jagiellonia Białystok"), (2, 1)),
    (("Anderlecht", "Olympique Lyonnais"), (1, 2)), (("Sturm Graz", "Rennes"), (0, 0)),
    (("Sunderland", "AZ Alkmaar"), (1, 0)), (("OFI Crete", "TSG Hoffenheim"), (2, 0)),
    (("Levski Sofia", "Red Bull Salzburg"), (0, 1)), (("Beşiktaş", "Marseille"), (4, 1)),
    (("Celtic", "Ferencváros"), (1, 3)), (("Crystal Palace", "Lech Poznań"), (4, 0)),
    (("Viktoria Plzeň", "Union Saint-Gilloise"), (0, 3)), (("Juventus", "NEC Nijmegen"), (5, 0)),
    (("Lillestrøm", "Torreense"), (1, 2)), (("Real Sociedad", "Bournemouth"), (1, 2)),
    (("Red Bull Salzburg", "Milan"), (0, 4)), (("Lech Poznań", "Bayer Leverkusen"), (0, 4)),
    (("Olympique Lyonnais", "Crystal Palace"), (3, 2)), (("NK Celje", "Omonia"), (0, 3)),
    (("Torreense", "Sunderland"), (1, 2)), (("AZ Alkmaar", "Hapoel Be'er Sheva"), (2, 1)),
    (("Sparta Prague", "Lillestrøm"), (1, 1)), (("Union Saint-Gilloise", "Real Sociedad"), (1, 1)),
    (("Benfica", "Celtic"), (4, 1)), (("Bournemouth", "Sturm Graz"), (3, 0)),
    (("Celta Vigo", "Juventus"), (1, 2)), (("Ferencváros", "Viktoria Plzeň"), (2, 1)),
    (("Rennes", "OFI Crete"), (2, 1)), (("Dinamo Zagreb", "Anderlecht"), (1, 0)),
    (("NEC Nijmegen", "Levski Sofia"), (1, 1)), (("TSG Hoffenheim", "Beşiktaş"), (2, 3)),
    (("Jagiellonia Białystok", "Ararat-Armenia"), (3, 1)), (("Marseille", "Olympiacos"), (0, 1)),
    (("Ararat-Armenia", "AZ Alkmaar"), (0, 4)), (("Ferencváros", "Torreense"), (4, 1)),
    (("Dinamo Zagreb", "NEC Nijmegen"), (2, 4)), (("Juventus", "Rennes"), (2, 2)),
    (("Lech Poznań", "Sunderland"), (1, 1)), (("OFI Crete", "Bayer Leverkusen"), (0, 2)),
    (("Union Saint-Gilloise", "Hapoel Be'er Sheva"), (4, 0)), (("Sturm Graz", "Marseille"), (1, 0)),
    (("Beşiktaş", "Crystal Palace"), (2, 2)), (("Bournemouth", "Milan"), (3, 0)),
    (("Celtic", "Celta Vigo"), (1, 2)), (("Viktoria Plzeň", "Levski Sofia"), (1, 2)),
    (("Jagiellonia Białystok", "Anderlecht"), (0, 3)), (("Lillestrøm", "Real Sociedad"), (0, 6)),
    (("NK Celje", "Red Bull Salzburg"), (2, 2)), (("Olympiacos", "Sparta Prague"), (1, 0)),
    (("Omonia", "Benfica"), (1, 4)), (("TSG Hoffenheim", "Olympique Lyonnais"), (3, 0)),
    (("Rennes", "Olympiacos"), (0, 0)),
    (("Milan", "Ferencváros"), (0, 2)), (("Sparta Prague", "Bournemouth"), (1, 3)),
    (("Levski Sofia", "Jagiellonia Białystok"), (1, 0)), (("Lillestrøm", "Viktoria Plzeň"), (0, 1)),
    (("NEC Nijmegen", "Omonia"), (3, 1)), (("Real Sociedad", "Olympique Lyonnais"), (1, 1)),
    (("Anderlecht", "Red Bull Salzburg"), (2, 0)), (("Crystal Palace", "TSG Hoffenheim"), (1, 1)),
    (("AZ Alkmaar", "Juventus"), (1, 2)), (("Bayer Leverkusen", "Marseille"), (0, 1)),
    (("Benfica", "Lech Poznań"), (3, 1)), (("Celta Vigo", "Union Saint-Gilloise"), (1, 2)),
    (("Celtic", "Beşiktaş"), (3, 2)), (("Hapoel Be'er Sheva", "OFI Crete"), (0, 2)),
    (("Sturm Graz", "NK Celje"), (2, 3)), (("Sunderland", "Dinamo Zagreb"), (0, 2)),
    (("Torreense", "Ararat-Armenia"), (3, 2)),
]

UECL_FIXTURES_RAW = [
    [("Lugano", "Crvena Zvezda"), ("Hajduk Split", "Ajax"), ("Gent", "Aarhus"), ("Egnatia", "Midtjylland"),
     ("KuPS Kuopio", "Trabzonspor"), ("Mjällby", "Inter Escaldes"), ("Panathinaikos", "Borac"),
     ("CSKA Sofia", "Monaco"), ("Riga", "Kairat Almaty"), ("Universitatea Craiova", "Getafe"),
     ("Atalanta", "Pafos"), ("Brighton", "Kauno Žalgiris"), ("Copenhagen", "Braga"), ("Twente", "Thun"),
     ("Hearts", "Nordsjælland"), ("Sint-Truidense", "Iberia Tbilisi"), ("Freiburg", "Jablonec"),
     ("Brann", "Lincoln Red Imps")],
    [("Kairat Almaty", "Panathinaikos"), ("Iberia Tbilisi", "Mjällby"), ("Nordsjælland", "CSKA Sofia"),
     ("Crvena Zvezda", "Copenhagen"), ("Jablonec", "Brighton"), ("Kauno Žalgiris", "Brann"),
     ("Getafe", "Lugano"), ("Inter Escaldes", "Universitatea Craiova"), ("Pafos", "Riga"),
     ("Trabzonspor", "Hearts"), ("Ajax", "Atalanta"), ("Aarhus", "Egnatia"), ("Monaco", "Freiburg"),
     ("Midtjylland", "Sint-Truidense"), ("Thun", "Hajduk Split"), ("Borac", "KuPS Kuopio"),
     ("Lincoln Red Imps", "Twente"), ("Braga", "Gent")],
    [("Aarhus", "Braga"), ("Atalanta", "Kairat Almaty"), ("Midtjylland", "Ajax"), ("Thun", "Hearts"),
     ("Crvena Zvezda", "Inter Escaldes"), ("KuPS Kuopio", "Gent"), ("Lincoln Red Imps", "Hajduk Split"),
     ("Mjällby", "Borac"), ("Trabzonspor", "Freiburg"), ("Monaco", "Nordsjælland"),
     ("Copenhagen", "Iberia Tbilisi"), ("Lugano", "Kauno Žalgiris"), ("Twente", "Pafos"),
     ("Getafe", "Brighton"), ("Sint-Truidense", "Brann"), ("Panathinaikos", "CSKA Sofia"),
     ("Riga", "Jablonec"), ("Universitatea Craiova", "Egnatia")],
    [("Kairat Almaty", "Mjällby"), ("Ajax", "Thun"), ("Brighton", "Universitatea Craiova"),
     ("Iberia Tbilisi", "Getafe"), ("Jablonec", "Lugano"), ("Kauno Žalgiris", "Riga"),
     ("Hearts", "Monaco"), ("Egnatia", "Lincoln Red Imps"), ("Pafos", "Midtjylland"),
     ("Brann", "Aarhus"), ("Nordsjælland", "Panathinaikos"), ("Borac", "Atalanta"),
     ("Hajduk Split", "Sint-Truidense"), ("Inter Escaldes", "Copenhagen"), ("Gent", "Crvena Zvezda"),
     ("CSKA Sofia", "Trabzonspor"), ("Braga", "KuPS Kuopio"), ("Freiburg", "Twente")],
    [("Kairat Almaty", "Universitatea Craiova"), ("Copenhagen", "Lugano"), ("Iberia Tbilisi", "Crvena Zvezda"),
     ("Getafe", "Inter Escaldes"), ("KuPS Kuopio", "CSKA Sofia"), ("Lincoln Red Imps", "Midtjylland"),
     ("Riga", "Atalanta"), ("Freiburg", "Panathinaikos"), ("Brann", "Braga"), ("Trabzonspor", "Jablonec"),
     ("Aarhus", "Twente"), ("Brighton", "Monaco"), ("Thun", "Gent"), ("Hearts", "Borac"),
     ("Hajduk Split", "Nordsjælland"), ("Sint-Truidense", "Ajax"), ("Egnatia", "Kauno Žalgiris"),
     ("Mjällby", "Pafos")],
    [("Ajax", "Getafe"), ("Monaco", "Lincoln Red Imps"), ("Atalanta", "Mjällby"), ("Lugano", "Sint-Truidense"),
     ("Midtjylland", "Hajduk Split"), ("Nordsjælland", "KuPS Kuopio"), ("Twente", "Kairat Almaty"),
     ("Borac", "Riga"), ("Crvena Zvezda", "Trabzonspor"), ("Jablonec", "Iberia Tbilisi"),
     ("Kauno Žalgiris", "Freiburg"), ("Inter Escaldes", "Aarhus"), ("Gent", "Brann"),
     ("Pafos", "Hearts"), ("Panathinaikos", "Brighton"), ("CSKA Sofia", "Thun"),
     ("Braga", "Egnatia"), ("Universitatea Craiova", "Copenhagen")],
]

UECL_NAME_MAP = {
    "Crvena Zvezda": "Red Star Belgrade", "Sint-Truidense": "Sint Truiden",
    "Nordsjælland": "FC Nordsjaelland", "Kauno Žalgiris": "FK Kauno Zalgiris",
    "Borac": "Borac Banja Luka", "Jablonec": "FK Jablonec", "Riga": "FK Riga",
    "Aarhus": "AGF", "Inter Escaldes": "Inter Club d'Escaldes",
    "Iberia Tbilisi": "Iberia", "Egnatia": "Egnatia Rrogozhine",
    "Pafos": "Pafos FC", "Mjällby": "Mjallby", "Kairat Almaty": "Kairat",
    "Copenhagen": "FC Copenhagen", "KuPS": "KuPS Kuopio",
}


def standardise_uecl(name):
    return UECL_NAME_MAP.get(name, name)


UECL_ACTUAL_RESULTS_ARR = [
    (("Hajduk Split", "Ajax"), (2, 1)), (("CSKA Sofia", "Monaco"), (1, 2)),
    (("Lugano", "Red Star Belgrade"), (3, 2)), (("KuPS Kuopio", "Trabzonspor"), (2, 4)),
    (("Panathinaikos", "Borac Banja Luka"), (2, 1)), (("Mjallby", "Inter Club d'Escaldes"), (2, 0)),
    (("Gent", "AGF"), (1, 0)), (("Egnatia Rrogozhine", "Midtjylland"), (1, 1)),
    (("Universitatea Craiova", "Getafe"), (1, 1)), (("FK Riga", "Kairat"), (1, 1)),
    (("Brighton", "FK Kauno Zalgiris"), (4, 0)), (("Atalanta", "Pafos FC"), (3, 1)),
    (("Freiburg", "FK Jablonec"), (3, 2)), (("Hearts", "FC Nordsjaelland"), (1, 1)),
    (("Sint Truiden", "Iberia"), (2, 0)), (("Brann", "Lincoln Red Imps"), (2, 1)),
    (("FC Copenhagen", "Braga"), (3, 0)), (("Twente", "Thun"), (1, 0)),
    (("Kairat", "Panathinaikos"), (1, 5)),
    (("Iberia", "Mjallby"), (1, 1)), (("FC Nordsjaelland", "CSKA Sofia"), (2, 2)),
    (("Red Star Belgrade", "FC Copenhagen"), (2, 2)), (("FK Jablonec", "Brighton"), (0, 0)),
    (("FK Kauno Zalgiris", "Brann"), (1, 4)), (("Getafe", "Lugano"), (2, 5)),
    (("Inter Club d'Escaldes", "Universitatea Craiova"), (1, 3)), (("Pafos FC", "FK Riga"), (1, 1)),
    (("Trabzonspor", "Hearts"), (2, 0)), (("Ajax", "Atalanta"), (2, 0)),
    (("AGF", "Egnatia Rrogozhine"), (1, 1)), (("Monaco", "Freiburg"), (3, 0)),
    (("Midtjylland", "Sint Truiden"), (0, 1)), (("Thun", "Hajduk Split"), (0, 1)),
    (("Borac Banja Luka", "KuPS Kuopio"), (2, 0)), (("Lincoln Red Imps", "Twente"), (1, 4)),
    (("Braga", "Gent"), (2, 0)),
    (("Aarhus", "Braga"), (0, 0)), (("Atalanta", "Kairat"), (1, 1)),
    (("Midtjylland", "Ajax"), (1, 6)), (("Thun", "Hearts"), (3, 1)),
    (("Red Star Belgrade", "Inter Club d'Escaldes"), (2, 1)), (("KuPS Kuopio", "Gent"), (0, 0)),
    (("Lincoln Red Imps", "Hajduk Split"), (1, 0)), (("Mjällby", "Borac Banja Luka"), (2, 0)),
    (("Trabzonspor", "Freiburg"), (0, 1)), (("Monaco", "FC Nordsjælland"), (2, 0)),
    (("FC Copenhagen", "Iberia"), (2, 1)), (("Lugano", "FK Kauno Žalgiris"), (3, 0)),
    (("Twente", "Pafos FC"), (3, 1)), (("Getafe", "Brighton"), (0, 1)),
    (("Sint-Truiden", "SK Brann"), (1, 1)), (("Panathinaikos", "CSKA Sofia"), (2, 1)),
    (("Riga FC", "FK Jablonec"), (1, 1)), (("Universitatea Craiova", "Egnatia"), (2, 0)),
]


# =============================================================================
# HELPERS
# =============================================================================
def _generate_double_round_robin(teams, rng=None):
    teams = list(teams)
    n = len(teams)
    if n % 2 != 0:
        teams.append(None)
        n += 1
    fixtures = []
    for r in range(n - 1):
        pairs = []
        for i in range(n // 2):
            home = teams[i]
            away = teams[n - 1 - i]
            if r % 2 == 0:
                pairs.append((home, away))
            else:
                pairs.append((away, home))
        fixtures.extend(pairs)
        teams = [teams[0]] + [teams[-1]] + teams[1:-1]
    first_leg = [(h, a) for h, a in fixtures if h is not None and a is not None]
    second_leg = [(a, h) for h, a in first_leg]
    return first_leg + second_leg


def build_full_round_robin(actual, rng=None):
    teams = sorted({t for (h, a), _ in actual for t in (h, a)})
    all_fixtures = _generate_double_round_robin(teams, rng=rng)
    actual_set = {(h, a) for (h, a), _ in actual}
    actual_order = [(h, a) for (h, a), _ in actual]
    remaining = [f for f in all_fixtures if f not in actual_set]
    if rng is not None:
        rng.shuffle(remaining)
    ordered_fixtures = [f for f in actual_order if f in actual_set]
    ordered_fixtures.extend(remaining)
    seen = set()
    deduped = []
    for f in ordered_fixtures:
        if f not in seen:
            deduped.append(f)
            seen.add(f)
    return deduped


def build_christmas_schedule(teams_list, rng=None, actual_results_arr=None):
    """Build a balanced Christmas schedule (first 167 games ≈ 16.7 per team).

    Creates a balanced double round-robin, overlays actual results onto their
    corresponding fixtures, then takes the first 160 fixtures + 7 from round 17.
    This ensures each team has ~16-17 games, not the biased ~11-27 from the
    previous actual-first ordering.
    """
    teams_sorted = sorted(teams_list)
    # Generate a balanced double round-robin
    all_fixtures = _generate_double_round_robin(teams_sorted, rng=rng)

    # Map actual results onto the balanced schedule
    if actual_results_arr is not None:
        actual_map = {(h, a): (hg, ag) for (h, a), (hg, ag) in actual_results_arr}
        # Create a new list with actual results overlaid at their correct positions
        balanced_with_actual = []
        for fixture in all_fixtures:
            if fixture in actual_map:
                balanced_with_actual.append(fixture)
        # Add remaining fixtures not yet played
        for fixture in all_fixtures:
            if fixture not in actual_map:
                balanced_with_actual.append(fixture)
        all_fixtures = balanced_with_actual

    base_fixtures = all_fixtures[:160]
    round17_fixtures = all_fixtures[160:170]
    if rng is not None:
        rng.shuffle(round17_fixtures)
    return base_fixtures, round17_fixtures


def _simulate_christmas_once(teams_sorted, team_to_idx,
                             base_fixtures, base_is_actual,
                             base_hg, base_ag,
                             round17_fixtures, r17_is_actual,
                             r17_hg, r17_ag,
                             global_seed=None, sim_idx=None,
                             base_lam_h=None, base_lam_a=None,
                             r17_lam_h=None, r17_lam_a=None,
                             n_extra=7, rng=None):
    n = len(teams_sorted)
    pts = [0] * n
    gf = [0] * n
    ga = [0] * n
    w = [0] * n
    d = [0] * n
    l = [0] * n
    form = {t: [] for t in teams_sorted}
    n_base = len(base_fixtures)
    n_r17 = len(round17_fixtures)

    if rng is None:
        rng = Rng(sub_seed(global_seed, "Christmas", sim_idx))
    rnd = rng.random

    for i in range(n_base):
        home_team, away_team = base_fixtures[i]
        h_idx = team_to_idx[home_team]
        a_idx = team_to_idx[away_team]
        if base_is_actual[i]:
            hg = base_hg[i]
            ag = base_ag[i]
        else:
            hg = _poisson_inline(rnd, base_lam_h[i])
            ag = _poisson_inline(rnd, base_lam_a[i])
        gf[h_idx] += hg; ga[h_idx] += ag
        gf[a_idx] += ag; ga[a_idx] += hg
        if hg > ag:
            pts[h_idx] += 3; w[h_idx] += 1
            form[home_team].append('W'); form[away_team].append('L'); l[a_idx] += 1
        elif ag > hg:
            pts[a_idx] += 3; w[a_idx] += 1
            form[away_team].append('W'); form[home_team].append('L'); l[h_idx] += 1
        else:
            pts[h_idx] += 1; pts[a_idx] += 1
            d[h_idx] += 1; d[a_idx] += 1
            form[home_team].append('D'); form[away_team].append('D')

    r17_selector_rng = rng
    selected = r17_selector_rng.sample(range(n_r17), min(n_extra, n_r17)) if n_r17 else []
    for j in selected:
        home_team, away_team = round17_fixtures[j]
        h_idx = team_to_idx[home_team]
        a_idx = team_to_idx[away_team]
        if r17_is_actual[j]:
            hg = r17_hg[j]; ag = r17_ag[j]
        else:
            hg = _poisson_inline(rnd, r17_lam_h[j])
            ag = _poisson_inline(rnd, r17_lam_a[j])
        gf[h_idx] += hg; ga[h_idx] += ag
        gf[a_idx] += ag; ga[a_idx] += hg
        if hg > ag:
            pts[h_idx] += 3; w[h_idx] += 1
            form[home_team].append('W'); form[away_team].append('L'); l[a_idx] += 1
        elif ag > hg:
            pts[a_idx] += 3; w[a_idx] += 1
            form[away_team].append('W'); form[home_team].append('L'); l[h_idx] += 1
        else:
            pts[h_idx] += 1; pts[a_idx] += 1
            d[h_idx] += 1; d[a_idx] += 1
            form[home_team].append('D'); form[away_team].append('D')
    return pts, gf, ga, w, d, l, form


def _precompute_lambdas(fixtures, atk_table, def_table, actual_results):
    n = len(fixtures)
    lam_h = [0.0] * n
    lam_a = [0.0] * n
    hg = [0] * n
    ag = [0] * n
    is_actual = [False] * n
    for i, (h, a) in enumerate(fixtures):
        atk_h = atk_table.get(h, LEAGUE_AVERAGE_ELO)
        def_h = def_table.get(h, LEAGUE_AVERAGE_ELO)
        atk_a = atk_table.get(a, LEAGUE_AVERAGE_ELO)
        def_a = def_table.get(a, LEAGUE_AVERAGE_ELO)
        lam_h[i], lam_a[i] = expected_goals_split(atk_h, def_h, atk_a, def_a)
        if (h, a) in actual_results:
            hg[i], ag[i] = actual_results[(h, a)]
            is_actual[i] = True
    return lam_h, lam_a, hg, ag, is_actual


def print_christmas_table(pl_teams, pl_elos, actual_results, rng,
                          attack_elos=None, defense_elos=None,
                          global_seed=None, num_sims=NUM_PL_SIMS,
                          odds_elos=None, external_elos=None):
    """Predicted Boxing-Day table.

    ``odds_elos`` and ``external_elos`` are the two other blend factors; when
    both are supplied an extra ``AvgELO`` column prints each team's average
    Elo across the three factors (stats + odds + external ELO) for the ATTACK
    and DEFENCE ratings that actually drive the match engine.
    """
    print("\n" + "=" * 80)
    print("PREDICTED PREMIER LEAGUE TABLE — AT BOXING DAY (~167 games, ~16.7/team avg)")
    print("=" * 80)
    n = len(pl_teams)
    teams_sorted = sorted(pl_teams)
    team_to_idx = {t: i for i, t in enumerate(teams_sorted)}
    base_fixtures, round17_fixtures = build_christmas_schedule(
        teams_sorted, rng=rng, actual_results_arr=ACTUAL_RESULTS_ARR)

    atk_table = attack_elos if attack_elos is not None else pl_elos
    def_table = defense_elos if defense_elos is not None else pl_elos

    base_lam_h, base_lam_a, base_hg, base_ag, base_is_actual = _precompute_lambdas(
        base_fixtures, atk_table, def_table, actual_results)
    r17_lam_h, r17_lam_a, r17_hg, r17_ag, r17_is_actual = _precompute_lambdas(
        round17_fixtures, atk_table, def_table, actual_results)

    if global_seed is not None:
        christmas_seed = sub_seed(global_seed, "Christmas", 0)
    else:
        christmas_seed = sub_seed(rng.randint(0, 2**63 - 1), "Christmas", 0)
    pos_counts = {t: defaultdict(int) for t in teams_sorted}
    avg_pts = {t: 0.0 for t in teams_sorted}
    avg_gf = {t: 0.0 for t in teams_sorted}
    avg_ga = {t: 0.0 for t in teams_sorted}
    avg_w = {t: 0.0 for t in teams_sorted}
    avg_d = {t: 0.0 for t in teams_sorted}
    avg_l = {t: 0.0 for t in teams_sorted}
    form_accum = {t: [] for t in teams_sorted}
    n_fix = len(base_fixtures) + 7

    for sim_i in range(num_sims):
        rng = Rng(sub_seed(christmas_seed, "Christmas", sim_i))
        pts, gf, ga, w, d, l, form = _simulate_christmas_once(
            teams_sorted, team_to_idx, base_fixtures, base_is_actual,
            base_hg, base_ag, round17_fixtures, r17_is_actual,
            r17_hg, r17_ag, global_seed=christmas_seed, sim_idx=sim_i,
            base_lam_h=base_lam_h, base_lam_a=base_lam_a,
            r17_lam_h=r17_lam_h, r17_lam_a=r17_lam_a, rng=rng)
        gd = [gf[i] - ga[i] for i in range(n)]
        tiebreak = [rng.float() * 0.0001 for _ in range(n)]
        order = list(range(n))
        order.sort(key=lambda i: (-pts[i], -gd[i], -gf[i], tiebreak[i]))
        for pos, idx in enumerate(order):
            team = teams_sorted[idx]
            pos_counts[team][pos + 1] += 1
            avg_pts[team] += pts[idx]
            avg_gf[team] += gf[idx]
            avg_ga[team] += ga[idx]
            avg_w[team] += w[idx]
            avg_d[team] += d[idx]
            avg_l[team] += l[idx]
            form_accum[team].append(form[team])

    avg_order = list(range(n))
    avg_order.sort(key=lambda i: (
        -avg_pts[teams_sorted[i]],
        -(avg_gf[teams_sorted[i]] - avg_ga[teams_sorted[i]]),
        -avg_gf[teams_sorted[i]]))
    xmas_rows = []
    for pos, idx in enumerate(avg_order):
        team = teams_sorted[idx]
        ap = avg_pts[team] / num_sims
        agf = avg_gf[team] / num_sims
        aga = avg_ga[team] / num_sims
        aw = avg_w[team] / num_sims
        ad = avg_d[team] / num_sims
        al = avg_l[team] / num_sims
        games = aw + ad + al
        form_str = "".join(form_accum[team][-1][-5:]) if form_accum[team] else "-"
        # Average Elo across the three blend factors (additive split, matches engine)
        if odds_elos is not None and external_elos is not None:
            base_atk = atk_table.get(team, LEAGUE_AVERAGE_ELO)
            base_def = def_table.get(team, LEAGUE_AVERAGE_ELO)
            base_overall = pl_elos.get(team, LEAGUE_AVERAGE_ELO)
            odds_ov = odds_elos.get(team, base_overall)
            ext_ov = external_elos.get(team, base_overall)
            odds_off = odds_ov - base_overall
            ext_off = ext_ov - base_overall
            avg_atk = (base_atk + (base_atk + odds_off) + (base_atk + ext_off)) / 3.0
            avg_def = (base_def + (base_def + odds_off) + (base_def + ext_off)) / 3.0
            avg_elo = (avg_atk + avg_def) / 2.0
            elo_str = "{:.0f}".format(avg_elo)
        else:
            elo_str = "{:.0f}".format(pl_elos.get(team, LEAGUE_AVERAGE_ELO))
        xmas_rows.append([
            str(pos + 1), team, "{:.1f}".format(games), "{:.1f}".format(aw),
            "{:.1f}".format(ad), "{:.1f}".format(al), "{:.1f}".format(agf),
            "{:.1f}".format(aga), "{:+.1f}".format(agf - aga),
            "{:.1f}".format(ap), elo_str, form_str,
        ])
    print_table(
        ["Rk", "Team", "P", "W", "D", "L", "GF", "GA", "GD", "Pts", "AvgELO", "Form"],
        xmas_rows,
        aligns=["r", "l", "r", "r", "r", "r", "r", "r", "r", "r", "r", "l"],
    )
    print("\n  Total games played (avg per sim): {}  |  Simulations: {}".format(n_fix, num_sims))


def results_to_map(arr):
    return dict(arr)


def flatten_fixtures(fixtures):
    return [f for r in fixtures for f in r]


# =============================================================================
# ELO REGRESSION / RATING BUILDERS
# =============================================================================
def regress_elos(elos, games_played, total_games, mean, max_pull, decay_rate=None):
    """Pull Elo values toward `mean`.

    The pull stays at `max_pull` until 50% of games are played, then decays
    exponentially toward 0. This keeps the Elo spread tight early on and
    widens it after the halfway point.

    pull(frac) = max_pull                      for frac <= 0.5
    pull(frac) = max_pull * exp(-decay_rate * (frac - 0.5))  for frac > 0.5

    where frac = games_played / total_games
    """
    if total_games == 0:
        return dict(elos)
    frac = max(0.0, min(1.0, games_played / total_games))
    if decay_rate is None:
        decay_rate = 3.0
    if frac <= 0.5:
        pull = max_pull
    else:
        pull = max_pull * math.exp(-decay_rate * (frac - 0.5))
    pull = max(0.0, min(1.0, pull))
    return {t: mean + (e - mean) * (1.0 - pull) for t, e in elos.items()}


def build_current_pl_ratings(actual, pl_teams, preset, k_prior):
    base = {t: preset.get(t, LEAGUE_AVERAGE_ELO) for t in pl_teams}
    observed = dict(base)
    for (h, a), (hg, ag) in actual.items():
        eh, ea = observed[h], observed[a]
        score = 1.0 if hg > ag else 0.0 if hg < ag else 0.5
        nh, na = update_elo(eh, ea, 20.0, score, goal_diff=abs(hg - ag))
        observed[h], observed[a] = nh, na
    n = len(actual)
    w_prior = k_prior / (k_prior + n)
    return {t: w_prior * base[t] + (1.0 - w_prior) * observed[t] for t in pl_teams}


# =============================================================================
# ACTUAL PL TABLE + MANAGER SACK RISK
# =============================================================================
def build_actual_team_form(actual_results_arr):
    form = defaultdict(list)
    for (h, a), (hg, ag) in actual_results_arr:
        if hg > ag:
            form[h].append('W'); form[a].append('L')
        elif ag > hg:
            form[a].append('W'); form[h].append('L')
        else:
            form[h].append('D'); form[a].append('D')
    return dict(form)


def last_n_form(form_list, n=5):
    return form_list[-n:]


def form_to_rating(form_list):
    return sum({'W': 3, 'D': 1, 'L': 0}[r] for r in form_list) / len(form_list) if form_list else 0.0


def actual_sack_form_adjustment(actual_form, pl_teams, recent_weight=0.7):
    adjustments = {}
    for team in pl_teams:
        all_form = actual_form.get(team, [])
        if not all_form:
            adjustments[team] = 0.0
            continue
        all_rating = form_to_rating(all_form)
        last5_rating = form_to_rating(last_n_form(all_form, 5))
        all_adj = (all_rating - 1.0) * 1.5
        last5_adj = (last5_rating - 1.0) * 1.5
        risk_adj = -((1.0 - recent_weight) * all_adj + recent_weight * last5_adj)
        adjustments[team] = max(-2.0, min(2.0, risk_adj))
    return adjustments


def build_actual_pl_table(actual_results, teams):
    stats = {t: {'P': 0, 'W': 0, 'D': 0, 'L': 0, 'GF': 0, 'GA': 0, 'Pts': 0, 'form': []}
             for t in teams}
    for (h, a), (hg, ag) in actual_results.items():
        if h not in stats or a not in stats:
            continue
        sh, sa = stats[h], stats[a]
        sh['P'] += 1; sa['P'] += 1
        sh['GF'] += hg; sh['GA'] += ag
        sa['GF'] += ag; sa['GA'] += hg
        if hg > ag:
            sh['W'] += 1; sh['Pts'] += 3; sa['L'] += 1
            sh['form'].append('W'); sa['form'].append('L')
        elif ag > hg:
            sa['W'] += 1; sa['Pts'] += 3; sh['L'] += 1
            sa['form'].append('W'); sh['form'].append('L')
        else:
            sh['D'] += 1; sa['D'] += 1
            sh['Pts'] += 1; sa['Pts'] += 1
            sh['form'].append('D'); sa['form'].append('D')
    for t in stats:
        stats[t]['GD'] = stats[t]['GF'] - stats[t]['GA']
    sorted_teams = sorted(stats.items(),
                          key=lambda x: (-x[1]['Pts'], -x[1]['GD'], -x[1]['GF'], x[0]))
    return sorted_teams, stats


def compute_sack_risk(ranking, manager_data=MANAGER_DATA,
                      recent_honours=RECENT_HONOURS,
                      euro_adjustments=None,
                      actual_form_adjustments=None):
    scores = {}
    euro_adjustments = euro_adjustments or {}
    actual_form_adjustments = actual_form_adjustments or {}
    for pos, team in enumerate(ranking):
        sim_pos = pos + 1
        entry = manager_data.get(team)
        if entry is None:
            scores[team] = 1.0
            continue
        _name, _nat, expected, pressure = entry
        underperf = sim_pos - expected
        overperf  = -underperf
        risk = 1.0
        if underperf > 0:
            exp_factor = underperf if expected >= 12 else (underperf ** 1.3)
            risk += exp_factor * 0.5 * pressure
        if sim_pos >= 18:
            risk += 2.5 + (sim_pos - 17) * 1.2
            risk *= pressure
        discount = 1.0
        if overperf >= 6 or sim_pos <= 2:
            discount = 0.35
        elif overperf >= 3 or sim_pos <= 4:
            discount = 0.60
        elif sim_pos <= 6:
            discount = 0.85
        risk *= discount

        honours = recent_honours.get(team, {})
        pl_recent = honours.get("pl_champion_recent", 0)
        if pl_recent >= 2:
            risk *= 0.35
        elif pl_recent >= 1:
            risk *= 0.55
        if honours.get("european_winner_last"):
            risk *= 0.70
        risk += euro_adjustments.get(team, 0.0)
        risk += actual_form_adjustments.get(team, 0.0)
        scores[team] = max(0.05, risk)
    return scores


def print_actual_pl_table(actual_results, pl_teams, pl_elos, managers=None):
    managers = managers or MANAGER_DATA
    sorted_teams, stats = build_actual_pl_table(actual_results, pl_teams)
    print("\n" + "=" * 138)
    print("PREMIER LEAGUE — CURRENT ACTUAL TABLE (real results so far) + ELO + MANAGER")
    print("=" * 138)
    actual_rows = []
    for pos, (team, s) in enumerate(sorted_teams, 1):
        entry = managers.get(team, ("Unknown", ""))
        mgr, nat = entry[0], entry[1]
        elo = pl_elos.get(team, LEAGUE_AVERAGE_ELO)
        form_str = "".join(s['form'][-5:]) if s['form'] else "-"
        actual_rows.append([
            str(pos), team, mgr, nat,
            str(s['P']), str(s['W']), str(s['D']), str(s['L']),
            str(s['GF']), str(s['GA']), "{:+d}".format(s['GD']),
            str(s['Pts']), "{:.1f}".format(elo), form_str,
        ])
    print_table(
        ["Rk", "Team", "Manager", "Nationality", "P", "W", "D", "L",
         "GF", "GA", "GD", "Pts", "Elo", "Form"],
        actual_rows,
        aligns=["r", "l", "l", "l", "r", "r", "r", "r", "r", "r", "r", "r", "r", "l"],
    )


# =============================================================================
# EUROPEAN COMPETITION
# =============================================================================
@dataclass(slots=True)
class EuroSimResult:
    winner: str
    elim_rounds: dict
    ranking: list
    league_points: dict
    league_wins: dict
    league_draws: dict
    ko_match_pts: dict
    team_results: dict


class EuropeanCompetition:
    def __init__(self, name, fixtures, pl_elos, pl_teams, actual_results, preset=None):
        team_set = set()
        for r in fixtures:
            for h, a in r:
                team_set.add(h)
                team_set.add(a)
        self.teams = sorted(team_set)
        self.name = name
        base_elos = {}
        for t in self.teams:
            if preset is not None and t in preset:
                e = preset[t]
            elif t in pl_teams and t in pl_elos:
                e = pl_elos[t]
            else:
                e = LEAGUE_AVERAGE_ELO
            base_elos[t] = e
        target_mean = EURO_COMP_MEAN.get(self.name, 1800.0)
        if base_elos:
            current_mean = sum(base_elos.values()) / len(base_elos)
            offset = target_mean - current_mean
            base_elos = {t: e + offset for t, e in base_elos.items()}
        self.base_elos = base_elos
        self.elos = dict(base_elos)
        self.english_teams = frozenset(t for t in self.teams if t in pl_teams)
        team_to_idx = {t: i for i, t in enumerate(self.teams)}
        self.team_to_idx = team_to_idx
        flat = flatten_fixtures(fixtures)
        self.fixture_h = []
        self.fixture_a = []
        self.lam_h_pre = []
        self.lam_a_pre = []
        self.actual_hg = [0] * len(flat)
        self.actual_ag = [0] * len(flat)
        mask = [False] * len(flat)
        for i, (h, a) in enumerate(flat):
            self.fixture_h.append(team_to_idx[h])
            self.fixture_a.append(team_to_idx[a])
            lh, la = expected_goals(base_elos[h], base_elos[a])
            self.lam_h_pre.append(lh)
            self.lam_a_pre.append(la)
            if (h, a) in actual_results:
                hg, ag = actual_results[(h, a)]
                self.actual_hg[i] = hg
                self.actual_ag[i] = ag
                mask[i] = True
        self.actual_mask = mask
        self.has_actual = any(mask)
        self.elo_rank = {t: i + 1 for i, t in
                         enumerate(sorted(self.base_elos,
                                          key=self.base_elos.get, reverse=True))}

    def simulate(self, global_seed, sim_idx, rng=None, track=(), stop_when_no_pl_teams=True,
                 base_elos_override=None):
        if rng is None:
            rng = Rng(sub_seed(global_seed, self.name, sim_idx))
        self.elos = (base_elos_override or self.base_elos).copy()
        n_teams = len(self.teams)
        n_fix = len(self.fixture_h)
        k = euro_k(self.name, "league")
        teams_list = self.teams
        team_to_idx = self.team_to_idx
        track_idx_set = {team_to_idx[t] for t in track if t in team_to_idx}
        team_results_idx = {idx: [] for idx in track_idx_set}
        pts = [0] * n_teams
        wins = [0] * n_teams
        draws = [0] * n_teams
        gf = [0] * n_teams
        ga = [0] * n_teams
        away_goals = [0] * n_teams
        away_wins = [0] * n_teams
        lam_h_pre = self.lam_h_pre
        lam_a_pre = self.lam_a_pre
        fixture_h = self.fixture_h
        fixture_a = self.fixture_a
        elos = self.elos
        has_actual = self.has_actual
        actual_mask = self.actual_mask
        actual_hg = self.actual_hg
        actual_ag = self.actual_ag
        rnd = rng.random
        for i in range(n_fix):
            if has_actual and actual_mask[i]:
                hg_v = actual_hg[i]
                ag_v = actual_ag[i]
            else:
                hg_v = _poisson_inline(rnd, lam_h_pre[i])
                ag_v = _poisson_inline(rnd, lam_a_pre[i])
            h = fixture_h[i]
            a = fixture_a[i]
            gf[h] += hg_v; ga[h] += ag_v
            gf[a] += ag_v; ga[a] += hg_v
            away_goals[a] += ag_v
            if hg_v > ag_v:
                pts[h] += 3; wins[h] += 1
                rh, ra = 'W', 'L'
            elif ag_v > hg_v:
                pts[a] += 3; wins[a] += 1; away_wins[a] += 1
                rh, ra = 'L', 'W'
            else:
                pts[h] += 1; pts[a] += 1
                draws[h] += 1; draws[a] += 1
                rh, ra = 'D', 'D'
            th = teams_list[h]; ta = teams_list[a]
            eh = elos[th]; ea = elos[ta]
            score = 1.0 if hg_v > ag_v else 0.0 if hg_v < ag_v else 0.5
            nh, na = update_elo(eh, ea, k, score, goal_diff=abs(hg_v - ag_v))
            elos[th] = nh; elos[ta] = na
            if h in track_idx_set:
                team_results_idx[h].append(rh)
            if a in track_idx_set:
                team_results_idx[a].append(ra)
        gd = [gf[i] - ga[i] for i in range(n_teams)]
        opp_pts = [0] * n_teams
        opp_gd = [0] * n_teams
        opp_gf = [0] * n_teams
        for i in range(n_fix):
            h = fixture_h[i]; a = fixture_a[i]
            opp_pts[h] += pts[a]; opp_pts[a] += pts[h]
            opp_gd[h] += gd[a]; opp_gd[a] += gd[h]
            opp_gf[h] += gf[a]; opp_gf[a] += gf[h]
        tiebreak = [rng.float() * 0.0001 for _ in range(n_teams)]
        order = list(range(n_teams))
        order.sort(key=lambda i: (
            -pts[i], -gd[i], -gf[i], -away_goals[i], -wins[i], -away_wins[i],
            -opp_pts[i], -opp_gd[i], -opp_gf[i], tiebreak[i]))
        ranking = [teams_list[i] for i in order]
        team_results = {teams_list[idx]: v for idx, v in team_results_idx.items()}
        qualified = ranking[:24]
        winner, elim_rounds, ko_match_pts, ko_team_results = \
            simulate_knockout_phase(qualified, self.elos, self.name, rng,
                                    track=track,
                                    english_teams=self.english_teams,
                                    stop_when_no_english=stop_when_no_pl_teams,
                                    global_seed=global_seed, sim_idx=sim_idx)
        for t in self.teams:
            elim_rounds.setdefault(t, -1)
        combined = {}
        for t in track:
            if t not in team_to_idx:
                continue
            v = list(team_results.get(t, []))
            v.extend(ko_team_results.get(t, []))
            combined[t] = v
        league_points = {teams_list[i]: pts[i] for i in range(n_teams)}
        league_wins = {teams_list[i]: wins[i] for i in range(n_teams)}
        league_draws = {teams_list[i]: draws[i] for i in range(n_teams)}
        ko_pts_full = {t: ko_match_pts.get(t, 0.0) for t in self.teams}
        return EuroSimResult(
            winner=winner,
            elim_rounds=elim_rounds,
            ranking=ranking,
            league_points=league_points,
            league_wins=league_wins,
            league_draws=league_draws,
            ko_match_pts=ko_pts_full,
            team_results=combined,
        )


# =============================================================================
# KNOCKOUT PHASE
# =============================================================================
def simulate_two_legged_tie(team1, team2, elos, comp, round_idx, rng,
                             global_seed=None, sim_idx=None, ko_fix_idx=None):
    e1 = elos.get(team1, LEAGUE_AVERAGE_ELO)
    e2 = elos.get(team2, LEAGUE_AVERAGE_ELO)
    lh1, la1 = expected_goals(e2, e1)
    rnd = rng.random
    l1_h = _poisson_inline(rnd, lh1)
    l1_a = _poisson_inline(rnd, la1)
    if l1_h > l1_a:
        r1_t1, r1_t2 = 'L', 'W'
    elif l1_h < l1_a:
        r1_t1, r1_t2 = 'W', 'L'
    else:
        r1_t1, r1_t2 = 'D', 'D'
    lh2, la2 = expected_goals(e1, e2)
    l2_h = _poisson_inline(rnd, lh2)
    l2_a = _poisson_inline(rnd, la2)
    if l2_h > l2_a:
        r2_t1, r2_t2 = 'W', 'L'
    elif l2_h < l2_a:
        r2_t1, r2_t2 = 'L', 'W'
    else:
        r2_t1, r2_t2 = 'D', 'D'
    agg1 = l1_a + l2_h
    agg2 = l1_h + l2_a
    _W = 2.0
    _D = 1.0
    pts_map = {
        team1: (_W if r1_t1 == 'W' else _D if r1_t1 == 'D' else 0.0)
             + (_W if r2_t1 == 'W' else _D if r2_t1 == 'D' else 0.0),
        team2: (_W if r1_t2 == 'W' else _D if r1_t2 == 'D' else 0.0)
             + (_W if r2_t2 == 'W' else _D if r2_t2 == 'D' else 0.0),
    }
    leg_results = {team1: [r1_t1, r2_t1], team2: [r1_t2, r2_t2]}
    et1 = et2 = 0
    if agg1 > agg2:
        winner, loser = team1, team2
    elif agg2 > agg1:
        winner, loser = team2, team1
    else:
        eth, eta = expected_goals(e1, e2)
        et1 = _poisson_inline(rnd, eth * EXTRA_TIME_XG_FACTOR)
        et2 = _poisson_inline(rnd, eta * EXTRA_TIME_XG_FACTOR)
        tot1 = l1_a + l2_h + et1
        tot2 = l1_h + l2_a + et2
        if tot1 > tot2:
            winner, loser = team1, team2
        elif tot2 > tot1:
            winner, loser = team2, team1
        else:
            p1 = pen_win_probability(e1, e2)
            winner, loser = (team1, team2) if rnd() < p1 else (team2, team1)
    k = knockout_k(comp, round_idx)
    agg_diff = abs(agg1 - agg2)
    nw, nl = update_elo(elos[winner], elos[loser], k, score_a=1.0,
                        goal_diff=agg_diff if agg1 != agg2 else (et1 - et2))
    elos[winner], elos[loser] = nw, nl
    return winner, pts_map, leg_results


def simulate_knockout_phase(qualified, elos, comp, rng, track=(),
                            english_teams=frozenset(),
                            stop_when_no_english=True,
                            global_seed=None, sim_idx=None):
    track_set = set(track)
    top8 = qualified[:8]
    playoff = qualified[8:24]
    elim_rounds = {t: -1 for t in qualified}
    ko_pts = {t: 0.0 for t in qualified}
    team_results = {t: [] for t in qualified if t in track_set}
    if stop_when_no_english and not any(t in english_teams for t in qualified):
        return None, elim_rounds, ko_pts, team_results
    ko_fix_counter = [0]

    def next_ko_idx():
        ko_fix_counter[0] += 1
        return ko_fix_counter[0]

    def run_round(participants, round_idx):
        winners = []
        if round_idx == 0 and len(participants) == 16:
            pods = [(0, 15), (1, 14), (2, 13), (3, 12)]
            for s_lo, u_hi in pods:
                seeded = [participants[s_lo], participants[s_lo + 1]]
                unseeded = [participants[u_hi - 1], participants[u_hi]]
                rng.shuffle(seeded)
                rng.shuffle(unseeded)
                for home, away in [(seeded[0], unseeded[0]), (seeded[1], unseeded[1])]:
                    kfi = next_ko_idx()
                    w, kp, lr = simulate_two_legged_tie(
                        home, away, elos, comp, round_idx, rng,
                        global_seed=global_seed, sim_idx=sim_idx, ko_fix_idx=kfi)
                    for t, v in kp.items():
                        ko_pts[t] += v
                    for t, v in lr.items():
                        if t in track_set:
                            team_results[t].extend(v)
                    winners.append(w)
        else:
            n = len(participants)
            for i in range(n // 2):
                kfi = next_ko_idx()
                w, kp, lr = simulate_two_legged_tie(
                    participants[i], participants[n - 1 - i], elos, comp, round_idx, rng,
                    global_seed=global_seed, sim_idx=sim_idx, ko_fix_idx=kfi)
                for t, v in kp.items():
                    ko_pts[t] += v
                for t, v in lr.items():
                    if t in track_set:
                        team_results[t].extend(v)
                winners.append(w)
        return winners

    winners = run_round(playoff, 0)
    winner_set = set(winners)
    for t in playoff:
        if t not in winner_set:
            elim_rounds[t] = 0
    pod_a = winners[0:2].copy()
    pod_b = winners[2:4].copy()
    pod_c = winners[4:6].copy()
    pod_d = winners[6:8].copy()
    for p in (pod_a, pod_b, pod_c, pod_d):
        rng.shuffle(p)
    r16_field = [
        top8[0], top8[1], pod_d[0], pod_d[1],
        top8[2], top8[3], pod_c[0], pod_c[1],
        top8[4], top8[5], pod_b[0], pod_b[1],
        top8[6], top8[7], pod_a[0], pod_a[1],
    ]
    current = r16_field
    for round_idx in range(1, 4):
        if stop_when_no_english and not any(t in english_teams for t in current):
            return None, elim_rounds, ko_pts, team_results
        winners = run_round(current, round_idx)
        winner_set = set(winners)
        for t in current:
            if t not in winner_set:
                elim_rounds[t] = round_idx
        current = winners
    if stop_when_no_english and not any(t in english_teams for t in current):
        return None, elim_rounds, ko_pts, team_results
    if len(current) == 2:
        t1, t2 = current[0], current[1]
        ha1, ha2 = final_home_advantage(t1, t2, comp)
        e1 = elos.get(t1, LEAGUE_AVERAGE_ELO) + ha1
        e2 = elos.get(t2, LEAGUE_AVERAGE_ELO) + ha2
        lh, la = expected_goals(e1, e2, home_adv=0.0)
        rnd = rng.random
        g1 = _poisson_inline(rnd, lh)
        g2 = _poisson_inline(rnd, la)
        if g1 != g2:
            winner, loser = (t1, t2) if g1 > g2 else (t2, t1)
        else:
            eth, eta = expected_goals(e1, e2, home_adv=0.0)
            et1 = _poisson_inline(rnd, eth * EXTRA_TIME_XG_FACTOR)
            et2 = _poisson_inline(rnd, eta * EXTRA_TIME_XG_FACTOR)
            if et1 != et2:
                winner, loser = (t1, t2) if et1 > et2 else (t2, t1)
            else:
                p1 = pen_win_probability(e1, e2)
                winner, loser = (t1, t2) if rnd() < p1 else (t2, t1)
        ko_pts[winner] += 2.0
        if t1 in track_set:
            team_results[t1].append('W' if winner == t1 else 'L')
        if t2 in track_set:
            team_results[t2].append('W' if winner == t2 else 'L')
        k = euro_k(comp, "late_ko")
        final_diff = abs(g1 - g2)
        nw, nl = update_elo(elos[winner], elos[loser], k, score_a=1.0, goal_diff=final_diff)
        elos[winner], elos[loser] = nw, nl
        elim_rounds[winner] = 5
        elim_rounds[loser] = 4
        return winner, elim_rounds, ko_pts, team_results
    w = current[0] if current else None
    return w, elim_rounds, ko_pts, team_results


# =============================================================================
# UEFA COEFFICIENT
# =============================================================================
def club_coeff_points(comp, league_position, elimination_round, league_wins, league_draws, ko_match_points):
    total = 2.0 * league_wins + league_draws + ko_match_points

    def tier(top_bonus, pos, tier_start):
        return top_bonus - 0.25 * (pos - tier_start)

    if comp == "UCL":
        if league_position <= 8:
            total += tier(12.0, league_position, 1)
        elif league_position <= 24:
            total += tier(8.0, league_position, 9)
        else:
            total += max(tier(4.0, league_position, 25), 0.0)
        total += min(4, max(0, elimination_round)) * 1.5
    elif comp == "UEL":
        if league_position <= 8:
            total += tier(6.0, league_position, 1)
        elif league_position <= 24:
            total += max(tier(4.0, league_position, 9), 0.0)
        total += min(4, max(0, elimination_round)) * 1.0
    elif comp == "UECL":
        if league_position <= 8:
            total += tier(4.0, league_position, 1)
        elif league_position <= 24:
            total += max(tier(2.0, league_position, 9), 0.0)
        total += min(4, max(0, elimination_round)) * 0.5
    return total


def all_association_coefficients(ucl, uel, uecl, assoc_map, entrants):
    assoc_clubs = defaultdict(dict)

    def add(r, comp):
        rank_map = {t: i + 1 for i, t in enumerate(r.ranking)}
        for team, elim in r.elim_rounds.items():
            assoc = assoc_map.get(team)
            if assoc is None:
                continue
            pos = rank_map.get(team, 99)
            assoc_clubs[assoc][team] = (
                comp, pos, elim,
                r.league_wins[team], r.league_draws[team], r.ko_match_pts[team],
            )

    add(ucl, "UCL")
    add(uel, "UEL")
    add(uecl, "UECL")
    out = {}
    for assoc, teams in assoc_clubs.items():
        if not teams:
            continue
        total_pts = sum(club_coeff_points(c, p, e, w, d, ko)
                        for c, p, e, w, d, ko in teams.values())
        denom = entrants.get(assoc, len(teams))
        out[assoc] = math.floor(total_pts * 1000.0 / denom) / 1000.0 if denom > 0 else 0.0
    return out


# =============================================================================
# PL SIMULATOR
# =============================================================================
class PLSimulator:
    def __init__(self, fixtures, current_ratings, actual_results,
                 attack_elos=None, defense_elos=None):
        teams = sorted({t for f in fixtures for t in f})
        team_to_idx = {t: i for i, t in enumerate(teams)}
        self.team_to_idx = team_to_idx
        self.base_elos = dict(current_ratings)
        self.attack_elos = dict(attack_elos) if attack_elos else dict(current_ratings)
        self.defense_elos = dict(defense_elos) if defense_elos else dict(current_ratings)
        self.actual_results = dict(actual_results) if actual_results else {}
        n_fixtures = len(fixtures)
        home_idx, away_idx = [], []
        base_diff_h_for, base_diff_a_for = [], []
        actual_hg = [0] * n_fixtures
        actual_ag = [0] * n_fixtures
        actual_mask = [False] * n_fixtures

        for i, (h, a) in enumerate(fixtures):
            home_idx.append(team_to_idx[h])
            away_idx.append(team_to_idx[a])

            atk_h = self.attack_elos.get(h, LEAGUE_AVERAGE_ELO)
            def_h = self.defense_elos.get(h, LEAGUE_AVERAGE_ELO)
            atk_a = self.attack_elos.get(a, LEAGUE_AVERAGE_ELO)
            def_a = self.defense_elos.get(a, LEAGUE_AVERAGE_ELO)

            base_diff_h_for.append(atk_h - def_a + HOME_ADVANTAGE_ELO)
            base_diff_a_for.append(atk_a - def_h)

            if (h, a) in actual_results:
                hg, ag = actual_results[(h, a)]
                actual_hg[i], actual_ag[i] = hg, ag
                actual_mask[i] = True

        self.teams = teams
        self.n_fixtures = n_fixtures
        self.home_idx = home_idx
        self.away_idx = away_idx
        self.fixtures = fixtures
        self.base_diff_h_for = base_diff_h_for
        self.base_diff_a_for = base_diff_a_for
        self.actual_hg = actual_hg
        self.actual_ag = actual_ag
        self.actual_mask = actual_mask
        self.has_actual = any(actual_mask)

        atk_table = self.attack_elos
        def_table = self.defense_elos
        self.base_lam_h, self.base_lam_a, _, _, _ = _precompute_lambdas(
            fixtures, atk_table, def_table, self.actual_results)

        # Tier 1.2: precompute exp(SENS * atk) and exp(-SENS * def) per team
        # so the hot loop uses multiplication instead of math.exp calls.
        s = XG_ELO_SENSITIVITY
        exp_atk = {t: math.exp(s * a) for t, a in atk_table.items()}
        exp_neg_def = {t: math.exp(-s * d) for t, d in def_table.items()}
        self.exp_atk_arr = [exp_atk.get(t, math.exp(s * LEAGUE_AVERAGE_ELO)) for t in teams]
        self.exp_neg_def_arr = [exp_neg_def.get(t, math.exp(-s * LEAGUE_AVERAGE_ELO)) for t in teams]
        self.exp_home = math.exp(s * HOME_ADVANTAGE_ELO)
        # Precompute fatigue penalty exp factors (only 6 possible values per comp)
        self._fatigue_exp_cache = {}
        for comp in ("UCL", "UEL", "UECL"):
            for round_ in range(6):
                fp = fatigue_penalty(round_, comp)
                self._fatigue_exp_cache[(round_, comp)] = math.exp(-s * fp)

    def simulate_season(self, fatigue_info, rng, global_seed=None, sim_idx=None, track=(),
                        man_city_penalty=None, sim_attack=None, sim_defense=None):
        n = len(self.teams)
        team_to_idx = self.team_to_idx
        teams_list = self.teams
        fatigue_info_map = {}
        active = [False] * n
        for team, (round_, comp) in fatigue_info.items():
            idx = team_to_idx.get(team)
            if idx is not None and round_ >= 0:
                active[idx] = True
                fatigue_info_map[team] = (round_, comp)
        track_idx_set = {team_to_idx[t] for t in track if t in team_to_idx}
        team_results_idx = {idx: [] for idx in track_idx_set}
        pts = [0] * n
        gf = [0] * n
        ga = [0] * n
        home_idx = self.home_idx
        away_idx = self.away_idx
        base_lam_h = self.base_lam_h
        base_lam_a = self.base_lam_a
        has_actual = self.has_actual
        actual_mask = self.actual_mask
        actual_hg = self.actual_hg
        actual_ag = self.actual_ag
        exp_atk_arr = self.exp_atk_arr
        exp_neg_def_arr = self.exp_neg_def_arr
        exp_home = self.exp_home
        fatigue_exp_cache = self._fatigue_exp_cache
        s = XG_ELO_SENSITIVITY
        use_sim = sim_attack is not None and sim_defense is not None
        if use_sim:
            sim_lam_h, sim_lam_a, _, _, _ = _precompute_lambdas(
                self.fixtures, sim_attack, sim_defense, self.actual_results)
            # Precompute exp factors for sim ratings for fatigue branch
            sim_exp_atk = {t: math.exp(s * a) for t, a in sim_attack.items()}
            sim_exp_neg_def = {t: math.exp(-s * d) for t, d in sim_defense.items()}
            sim_exp_atk_arr = [sim_exp_atk.get(t, math.exp(s * LEAGUE_AVERAGE_ELO)) for t in teams_list]
            sim_exp_neg_def_arr = [sim_exp_neg_def.get(t, math.exp(-s * LEAGUE_AVERAGE_ELO)) for t in teams_list]
        else:
            sim_lam_h = base_lam_h
            sim_lam_a = base_lam_a
            sim_exp_atk_arr = exp_atk_arr
            sim_exp_neg_def_arr = exp_neg_def_arr
        if global_seed is not None and rng is None:
            rng = Rng(sub_seed(global_seed, "PL", sim_idx))
        rnd = rng.random
        for i in range(self.n_fixtures):
            h = home_idx[i]
            a = away_idx[i]
            home_team = teams_list[h]
            away_team = teams_list[a]
            if has_actual and actual_mask[i]:
                hg = actual_hg[i]
                ag = actual_ag[i]
            else:
                if active[h] or active[a]:
                    h_round, h_comp = fatigue_info_map.get(home_team, (0, ""))
                    a_round, a_comp = fatigue_info_map.get(away_team, (0, ""))
                    h_exp_fat = fatigue_exp_cache.get((h_round, h_comp), 1.0) if active[h] else 1.0
                    a_exp_fat = fatigue_exp_cache.get((a_round, a_comp), 1.0) if active[a] else 1.0
                    lh = min(BASE_HOME_XG * exp_home * sim_exp_atk_arr[h]
                             * sim_exp_neg_def_arr[a] * h_exp_fat, 5.5)
                    la = min(BASE_AWAY_XG * sim_exp_atk_arr[a]
                             * sim_exp_neg_def_arr[h] * a_exp_fat, 5.5)
                else:
                    lh, la = sim_lam_h[i], sim_lam_a[i]
                hg = _poisson_inline(rnd, lh)
                ag = _poisson_inline(rnd, la)
            gf[h] += hg; ga[h] += ag
            gf[a] += ag; ga[a] += hg
            if hg > ag:
                pts[h] += 3
                if h in track_idx_set: team_results_idx[h].append('W')
                if a in track_idx_set: team_results_idx[a].append('L')
            elif ag > hg:
                pts[a] += 3
                if a in track_idx_set: team_results_idx[a].append('W')
                if h in track_idx_set: team_results_idx[h].append('L')
            else:
                pts[h] += 1; pts[a] += 1
                if h in track_idx_set: team_results_idx[h].append('D')
                if a in track_idx_set: team_results_idx[a].append('D')
        gd = [gf[i] - ga[i] for i in range(n)]
        if man_city_penalty is not None:
            mc_idx = team_to_idx.get("Man City")
            if mc_idx is not None:
                if man_city_penalty == "EXPEL":
                    pts[mc_idx] = -115
                else:
                    pts[mc_idx] -= man_city_penalty
        tiebreak = [rnd() * 0.0001 for _ in range(n)]
        order = list(range(n))
        order.sort(key=lambda i: (-pts[i], -gd[i], -gf[i], tiebreak[i]))
        ranked = [teams_list[i] for i in order]
        points_map = {teams_list[i]: pts[i] for i in range(n)}
        team_results = {teams_list[idx]: v for idx, v in team_results_idx.items()}
        return ranked, points_map, team_results


# =============================================================================
# EUROPEAN SPOT ALLOCATION
# =============================================================================
def allocate_european_spots(ranking, carabao_winner, pl_teams, ucl_winner, uel_winner,
                            uecl_winner, has_eps, fa_cup_winner):
    relegated = set(ranking[-3:]) if len(ranking) >= 3 else set()

    def _can_take_spot(team, *blocked_sets):
        return (team in pl_teams
                and team not in relegated
                and all(team not in s for s in blocked_sets))

    ucl = set(ranking[:4])
    for w in (ucl_winner, uel_winner):
        if _can_take_spot(w):
            ucl.add(w)
    if has_eps:
        for t in ranking:
            if _can_take_spot(t, ucl):
                ucl.add(t)
                break
    uel = set()
    for t in ranking:
        if _can_take_spot(t, ucl):
            uel.add(t)
            break
    if fa_cup_winner and _can_take_spot(fa_cup_winner, ucl, uel):
        uel.add(fa_cup_winner)
    elif fa_cup_winner and fa_cup_winner in pl_teams and fa_cup_winner in (ucl | uel):
        for t in ranking:
            if _can_take_spot(t, ucl, uel):
                uel.add(t)
                break
    carabao_pl_name = carabao_name_map(carabao_winner)
    uecl = set()
    carabao_is_pl = carabao_pl_name in pl_teams
    if carabao_is_pl and _can_take_spot(carabao_pl_name, ucl, uel):
        uecl.add(carabao_pl_name)
    elif carabao_is_pl:
        for t in ranking:
            if _can_take_spot(t, ucl, uel, uecl):
                uecl.add(t)
                break
    if uecl_winner and _can_take_spot(uecl_winner, ucl):
        uel.add(uecl_winner)
        if uecl_winner in uecl:
            uecl.remove(uecl_winner)
            for t in ranking:
                if _can_take_spot(t, ucl, uel, uecl):
                    uecl.add(t)
                    break
    return {"UCL": ucl, "UEL": uel, "UECL": uecl}


# =============================================================================
# CARABAO CUP
# =============================================================================
_carabao_elo_cache = None
_fa_cup_data_cache = None

_CARABAO_NAME_MAP = {
    "Bradford City": "Bradford",
    "Peterborough United": "Peterboro",
    "Manchester City": "Man City",
    "Brighton & Hove Albion": "Brighton",
    "Newcastle United": "Newcastle",
    "Forest": "Nott'm Forest",
}


def carabao_elo():
    global _carabao_elo_cache
    if _carabao_elo_cache is None:
        _CARABAO_AVERAGE_ELOS = {
            "Man City": 1963, "Liverpool": 1919, "Arsenal": 2089,
            "Chelsea": 1791, "Newcastle": 1739, "Aston Villa": 1889,
            "Bournemouth": 1683, "Brentford": 1738, "Everton": 1787,
            "Brighton": 1713, "Fulham": 1724, "Crystal Palace": 1762,
            "Sunderland": 1696, "Fleetwood Town": 1535,
            "Peterboro": 1558, "Bradford": 1670,
        }
        rows = [
            ("Man City", _CARABAO_AVERAGE_ELOS["Man City"]),
            ("Arsenal", _CARABAO_AVERAGE_ELOS["Arsenal"]),
            ("Liverpool", _CARABAO_AVERAGE_ELOS["Liverpool"]),
            ("Man United", 1850.89),
            ("Brighton", _CARABAO_AVERAGE_ELOS["Brighton"]),
            ("Bournemouth", _CARABAO_AVERAGE_ELOS["Bournemouth"]),
            ("Brentford", _CARABAO_AVERAGE_ELOS["Brentford"]),
            ("Aston Villa", _CARABAO_AVERAGE_ELOS["Aston Villa"]),
            ("Leeds", 1775.33),
            ("Everton", _CARABAO_AVERAGE_ELOS["Everton"]),
            ("Newcastle", _CARABAO_AVERAGE_ELOS["Newcastle"]),
            ("Chelsea", _CARABAO_AVERAGE_ELOS["Chelsea"]),
            ("Nott'm Forest", 1747.80),
            ("Fulham", _CARABAO_AVERAGE_ELOS["Fulham"]),
            ("Crystal Palace", _CARABAO_AVERAGE_ELOS["Crystal Palace"]),
            ("West Ham", 1681.57),
            ("Sunderland", _CARABAO_AVERAGE_ELOS["Sunderland"]),
            ("Tottenham", 1639.38),
            ("Wolves", 1547.95),
            ("Ipswich", 1532.58),
            ("Coventry", 1504.38),
            ("Burnley", 1500.92),
            ("Southampton", 1447.66),
            ("Hull", 1436.60),
            ("Lincoln", 1417.82),
            ("Millwall", 1395.48),
            ("Middlesbrough", 1350.22),
            ("Norwich", 1334.15),
            ("Wrexham", 1327.65),
            ("Derby", 1304.65),
            ("Swansea", 1304.53),
            ("Birmingham", 1304.14),
            ("Cardiff", 1303.61),
            ("Sheffield United", 1286.61),
            ("Plymouth", 1275.66),
            ("Luton", 1274.00),
            ("Portsmouth", 1261.50),
            ("Stockport", 1256.67),
            ("Bolton", 1250.53),
            ("Bristol City", 1247.50),
            ("Blackburn", 1236.45),
            ("West Brom", 1233.42),
            ("Mansfield", 1230.42),
            ("Leicester", 1228.54),
            ("Stevenage", 1221.06),
            ("Milton Keynes Dons", 1218.28),
            ("Bromley", 1217.81),
            ("Bradford", _CARABAO_AVERAGE_ELOS["Bradford"]),
            ("QPR", 1212.89),
            ("Preston", 1212.75),
            ("Charlton", 1207.22),
            ("Oxford", 1197.43),
            ("Cambridge", 1197.04),
            ("Wycombe", 1195.17),
            ("Chesterfield", 1193.11),
            ("Blackpool", 1192.83),
            ("Huddersfield", 1190.23),
            ("Reading", 1186.25),
            ("Watford", 1185.31),
            ("Grimsby", 1181.03),
            ("Salford", 1174.96),
            ("Barnet", 1174.09),
            ("Stoke", 1167.18),
            ("Doncaster", 1165.70),
            ("Notts County", 1161.57),
            ("Bury", 1150.20),
            ("Wigan", 1139.49),
            ("Burton", 1132.10),
            ("Barnsley", 1128.18),
            ("Leyton Orient", 1121.87),
            ("Swindon", 1115.87),
            ("Colchester", 1114.39),
            ("Bristol Rvs", 1107.08),
            ("Oldham", 1105.14),
            ("Port Vale", 1100.96),
            ("Peterboro", _CARABAO_AVERAGE_ELOS["Peterboro"]),
            ("Exeter", 1092.60),
            ("Wimbledon", 1090.09),
            ("Kidderminster", 1088.40),
            ("Crewe", 1086.77),
            ("Fleetwood Town", _CARABAO_AVERAGE_ELOS["Fleetwood Town"]),
            ("AFC Wimbledon", 1066.28),
            ("Walsall", 1055.97),
            ("Rotherham", 1038.82),
            ("Aldershot", 1028.07),
            ("Sutton", 1024.15),
            ("Sheffield Weds", 1023.03),
            ("Scarborough", 1021.02),
            ("Cheltenham", 1020.13),
            ("Hereford", 1018.21),
            ("Southend", 1015.77),
            ("Accrington", 1000.25),
            ("Gillingham", 999.92),
            ("Hartlepool", 996.02),
            ("Carlisle", 994.44),
            ("Crawley Town", 994.04),
            ("Shrewsbury", 993.95),
            ("Torquay", 991.08),
            ("Rochdale", 985.99),
            ("Newport County", 981.89),
            ("Boston", 980.87),
            ("Rushden & D", 979.65),
            ("Macclesfield", 979.06),
            ("Forest Green", 979.06),
            ("Harrogate", 976.24),
            ("Northampton", 959.87),
            ("York", 955.72),
            ("Dag and Red", 948.85),
            ("Halifax", 945.06),
            ("Darlington", 944.05),
            ("Tranmere", 942.64),
            ("Barrow", 933.53),
            ("Morecambe", 931.23),
            ("Yeovil", 924.14),
            ("Chester", 917.06),
            ("Scunthorpe", 847.02),
        ]
        _carabao_elo_cache = dict(rows)
    return _carabao_elo_cache


def carabao_name_map(name):
    return _CARABAO_NAME_MAP.get(name, name)


@functools.lru_cache(maxsize=None)
def get_carabao_elo(team):
    key = carabao_name_map(team)
    return carabao_elo().get(key, 1500.0)


@functools.lru_cache(maxsize=None)
def get_carabao_compressed_elo(team):
    raw = get_carabao_elo(team)
    pulled = CARABAO_MEAN_ELO + (raw - CARABAO_MEAN_ELO) * (1.0 - CARABAO_PULL)
    return CARABAO_MEAN_ELO + (pulled - CARABAO_MEAN_ELO) * CARABAO_ELO_COMPRESS


def carabao_penalty_winner(rng, a, b):
    ea = get_carabao_compressed_elo(a)
    eb = get_carabao_compressed_elo(b)
    p = pen_win_probability(ea, eb)
    return a if rng.float() < p else b


CARABAO_FIXED_RESULTS = {
    ("Bradford City", "Peterborough United"): (2, 0, None),
    ("Fleetwood Town", "Arsenal"):            (2, 1, None),
    ("Manchester City", "Brighton & Hove Albion"): (3, 2, None),
    ("Bournemouth", "Aston Villa"): (3, 0, None),
    ("Fulham", "Crystal Palace"): (0, 1, None),
    ("Sunderland", "Brentford"): (3, 1, None),
    ("Liverpool", "Chelsea"): (2, 1, None), 
    ("Everton", "Newcastle United"): (2, 0, None),
}

# Confirmed Carabao Cup Quarter-Final draw (week commencing 14 December 2026).
# Maps index pairs from the R4 `winners` list (R4 is ordered as defined in
# run_carabao_tournament).  QF1: Fleetwood Town vs Everton/Newcastle winner;
# QF2: Manchester City vs Bradford City winner;
# QF3: Crystal Palace vs Sunderland winner;
# QF4: Liverpool vs Bournemouth winner.
CARABAO_QF_PAIRINGS = [(1, 7), (2, 0), (4, 5), (6, 3)]


def _carabao_pen(rng, a, b, global_seed=None, sim_idx=None, fix_idx=None, offset=None):
    p = pen_win_probability(get_carabao_compressed_elo(a), get_carabao_compressed_elo(b))
    return a if rng.float() < p else b


def _carabao_score(rng, lh, la, global_seed=None, sim_idx=None, fix_idx=None):
    h = _poisson_inline(rng.random, lh)
    a = _poisson_inline(rng.random, la)
    return h, a


def _carabao_do_et(rng, global_seed=None, sim_idx=None, fix_idx=None):
    return rng.float() < 0.20


def _carabao_resolve_tie(rng, team_a, team_b, extra_time, lh, la,
                         global_seed=None, sim_idx=None, fix_idx=None):
    if not extra_time:
        return _carabao_pen(rng, team_a, team_b)
    et_skip = _carabao_do_et(rng)
    if not et_skip:
        et_h = _poisson_inline(rng.random, lh * EXTRA_TIME_XG_FACTOR)
        et_a = _poisson_inline(rng.random, la * EXTRA_TIME_XG_FACTOR)
        if et_h != et_a:
            return team_a if et_h > et_a else team_b
        return _carabao_pen(rng, team_a, team_b)
    return _carabao_pen(rng, team_a, team_b)


def sim_carabao_match(rng, team_a, team_b, extra_time, track=(), neutral=False,
                       venue_aware=True, global_seed=None, sim_idx=None, fix_idx=None):
    results = {t: None for t in track if t in (team_a, team_b)}
    fixed = CARABAO_FIXED_RESULTS.get((team_a, team_b))
    if fixed is not None:
        hg, ag, pen = fixed
        if hg > ag:
            winner = team_a
        elif ag > hg:
            winner = team_b
        else:
            winner = pen if pen is not None else _carabao_pen(rng, team_a, team_b)
        return (winner, {t: "W" if t == winner else "L" for t in results})
    ea = get_carabao_compressed_elo(team_a)
    eb = get_carabao_compressed_elo(team_b)
    if neutral:
        ha, ha_opp = (0.0, 0.0)
        if venue_aware:
            ha, ha_opp = final_home_advantage(team_a, team_b, "Carabao")
    else:
        ha = HOME_ADVANTAGE_ELO
        ha_opp = 0.0
    lh, la = expected_goals(ea + ha, eb + ha_opp, home_adv=0.0)
    hg, ag = _carabao_score(rng, lh, la)
    if hg > ag:
        winner = team_a
    elif ag > hg:
        winner = team_b
    else:
        winner = _carabao_resolve_tie(rng, team_a, team_b, extra_time, lh, la)
    return (winner, {t: 'W' if t == winner else 'L' for t in results})


def sim_carabao_two_legged(rng, a, b, track=(), global_seed=None, sim_idx=None, fix_idx=None, neutral=False):
    results = {t: None for t in track if t in (a, b)}
    fixed = CARABAO_FIXED_RESULTS.get((a, b))
    if fixed is not None:
        hg, ag, pen = fixed
        if hg > ag:
            winner = a
        elif ag > hg:
            winner = b
        else:
            winner = pen if pen is not None else _carabao_pen(rng, a, b)
        return (winner, {t: 'W' if t == winner else 'L' for t in results})
    ea = get_carabao_compressed_elo(a)
    eb = get_carabao_compressed_elo(b)
    ha_bonus = 0.0 if neutral else HOME_ADVANTAGE_ELO
    lh1, la1 = expected_goals(ea + ha_bonus, eb, home_adv=0.0)
    lh2, la2 = expected_goals(eb + ha_bonus, ea, home_adv=0.0)
    rnd = rng.random
    h1 = _poisson_inline(rnd, lh1)
    a1 = _poisson_inline(rnd, la1)
    h2 = _poisson_inline(rnd, lh2)
    a2 = _poisson_inline(rnd, la2)
    agg_a = h1 + a2
    agg_b = a1 + h2
    if agg_a > agg_b:
        winner = a
    elif agg_b > agg_a:
        winner = b
    else:
        winner = _carabao_pen(rng, a, b)
    return (winner, {t: 'W' if t == winner else 'L' for t in results})


def run_carabao_tournament(rng=None, track=(), global_seed=None, sim_idx=None):
    if rng is None and global_seed is not None:
        rng = Rng(sub_seed(global_seed, "Carabao", sim_idx))
    R4 = [
        ("Bradford City", "Peterborough United"),
        ("Fleetwood Town", "Arsenal"),
        ("Manchester City", "Brighton & Hove Albion"),
        ("Bournemouth", "Aston Villa"),
        ("Fulham", "Crystal Palace"),
        ("Sunderland", "Brentford"),
        ("Liverpool", "Chelsea"),
        ("Everton", "Newcastle United"),
    ]
    team_results = {t: [] for t in track} if track else {}
    fix_counter = [0]

    def next_fix():
        fix_counter[0] += 1
        return fix_counter[0]

    def play_match(func, a, b, **kwargs):
        """Play one Carabao match, accumulate tracked results, return winner."""
        fi = next_fix()
        w, r = func(rng, a, b, track=track, global_seed=global_seed,
                    sim_idx=sim_idx, fix_idx=fi, **kwargs)
        if track:
            for t, v in r.items(): team_results[t].append(v)
        return w

    def shuffle_teams(lst):
        rng.shuffle(lst)

    winners = [play_match(sim_carabao_match, a, b, extra_time=False) for a, b in R4]
    qf = [play_match(sim_carabao_match, winners[i], winners[j], extra_time=False)
          for i, j in CARABAO_QF_PAIRINGS]
    shuffle_teams(qf)
    sf = [play_match(sim_carabao_two_legged, qf[i], qf[i + 1], neutral=True)
          for i in range(0, len(qf), 2)]
    shuffle_teams(sf)
    final = play_match(sim_carabao_match, sf[0], sf[1], extra_time=True, neutral=True)
    if track:
        return final, team_results
    return final


# =============================================================================
# FA CUP
# =============================================================================
_FA_CUP_MISSING_ELOS = {
    "Dover Athletic": 1150.0, "Wealdstone": 1190.0, "Anstey Nomads": 950.0,
    "Chesham United": 1000.0, "Harborough Town": 990.0, "Tadley Calleva": 900.0,
    "Plymouth Parkway": 1000.0, "Berkhamsted": 950.0, "Leatherhead": 1000.0,
    "Gloucester City": 1100.0, "AFC Fylde": 1200.0,
    "AFC Rushden & Diamonds": 1000.0, "Bedford Town": 1000.0,
    "Cray Wanderers": 1000.0, "Chorley": 1150.0, "Worcester City": 950.0,
    "Eastleigh": 1250.0, "Wimborne Town": 1000.0, "Spalding United": 950.0,
    "Alvechurch": 1000.0, "Hornchurch": 1100.0, "Guiseley": 1050.0,
    "Gateshead": 1250.0, "Stafford Rangers": 1000.0, "Oxford City": 1150.0,
    "Marine": 1050.0, "Altrincham": 1250.0, "FC United of Manchester": 1050.0,
    "Boreham Wood": 1250.0, "Salisbury": 1150.0, "Sholing": 1000.0,
}

_FA_CUP_EXTRA_NAMES = {
    "Sheffield Wednesday": "Sheffield Weds", "Peterborough United": "Peterboro",
    "Brighton & Hove Albion": "Brighton", "Newcastle United": "Newcastle",
    "Nottingham Forest": "Nott'm Forest", "Wolverhampton Wanderers": "Wolves",
    "West Bromwich Albion": "West Brom", "Bristol Rovers": "Bristol Rvs",
    "MK Dons": "Milton Keynes Dons", "Milton Keynes Dons": "Milton Keynes Dons",
    "Forest Green Rovers": "Forest Green", "Harrogate Town": "Harrogate",
    "Sutton United": "Sutton", "Mansfield Town": "Mansfield",
    "Huddersfield Town": "Huddersfield", "Luton Town": "Luton",
    "Exeter City": "Exeter", "Wycombe Wanderers": "Wycombe",
    "Doncaster Rovers": "Doncaster", "Swindon Town": "Swindon",
    "Tranmere Rovers": "Tranmere", "York City": "York",
    "Northampton Town": "Northampton", "Oxford United": "Oxford",
    "Crewe Alexandra": "Crewe", "Cheltenham Town": "Cheltenham",
    "Colchester United": "Colchester", "Shrewsbury Town": "Shrewsbury",
    "Grimsby Town": "Grimsby", "Bradford City": "Bradford",
    "Wigan Athletic": "Wigan", "Carlisle United": "Carlisle",
    "Salford City": "Salford", "AFC Rushden & Diamonds": "Rushden & D",
    "Manchester City": "Man City", "Cambridge United": "Cambridge",
    "Leicester City": "Leicester", "Rotherham United": "Rotherham",
    "Scunthorpe United": "Scunthorpe", "Yeovil Town": "Yeovil",
    "FC Halifax Town": "Halifax", "Stockport County": "Stockport",
    "Oldham Athletic": "Oldham", "Notts County": "Notts County",
    "Port Vale": "Port Vale", "Burton Albion": "Burton",
    "Accrington Stanley": "Accrington", "Kidderminster Harriers": "Kidderminster",
    "Plymouth Argyle": "Plymouth",
}

_FA_CUP_R1_TIES = [
    ("Dover Athletic", "Wealdstone"), ("Mansfield Town", "Macclesfield"),
    ("Huddersfield Town", "Exeter City"), ("Luton Town", "Forest Green Rovers"),
    ("Bristol Rovers", "Cambridge United"), ("Oldham Athletic", "Sheffield Wednesday"),
    ("Kidderminster Harriers", "Doncaster Rovers"), ("Leyton Orient", "Harborough Town"),
    ("Accrington Stanley", "Wycombe Wanderers"), ("MK Dons", "Swindon Town"),
    ("Newport County", "Walsall"), ("Bromley", "Rotherham United"),
    ("Barnet", "Tranmere Rovers"), ("Fleetwood Town", "Rochdale"),
    ("Barnsley", "Aldershot"), ("Plymouth Parkway", "Berkhamsted"),
    ("Chesterfield", "Yeovil Town"), ("Gillingham", "Barrow"),
    ("Harrogate Town", "AFC Fylde"), ("Crewe Alexandra", "AFC Wimbledon"),
    ("Oxford United", "Stevenage"), ("Burton Albion", "AFC Rushden & Diamonds"),
    ("Cray Wanderers", "Stockport County"), ("Port Vale", "Scunthorpe United"),
    ("Cheltenham Town", "FC Halifax Town"), ("Colchester United", "Worcester City"),
    ("Eastleigh", "Shrewsbury Town"), ("Peterborough United", "Reading"),
    ("Wimborne Town", "Crawley Town"), ("Plymouth Argyle", "Alvechurch"),
    ("Hornchurch", "Blackpool"), ("Guiseley", "Sutton United"),
    ("Stafford Rangers", "Grimsby Town"), ("Oxford City", "Leicester City"),
    ("Bradford City", "Marine"), ("York City", "Northampton Town"),
    ("Altrincham", "Notts County"), ("Boreham Wood", "Wigan Athletic"),
    ("Carlisle United", "Salford City"), ("Salisbury", "Sholing"),
]

# =============================================================================
# FA CUP — ACTUAL R1 RESULTS (Friday 6 & Saturday 7 November 2026)
# Keyed by (home, away) using the SAME team names as _FA_CUP_R1_TIES.
# Value = winning team name (handles AET + penalty shootouts).
# Ties not listed here fall back to simulation.
# =============================================================================
_FA_CUP_R1_ACTUAL = {
    ("Dover Athletic", "Wealdstone"):                "Dover Athletic",        # 2-0
    ("Altrincham", "Notts County"):                  "Notts County",          # 2-2, 2-3 pens
    ("Accrington Stanley", "Wycombe Wanderers"):     "Wycombe Wanderers",     # 0-2
    ("Barnet", "Tranmere Rovers"):                   "Barnet",                # 3-0
    ("Barnsley", "Aldershot"):                       "Barnsley",              # 7-2
    ("Boreham Wood", "Wigan Athletic"):              "Wigan Athletic",        # 0-3
    ("Bradford City", "Marine"):                     "Bradford City",         # 7-0
    ("Bristol Rovers", "Cambridge United"):          "Bristol Rovers",        # 2-0
    ("Bromley", "Rotherham United"):                 "Rotherham United",      # 0-2
    ("Burton Albion", "AFC Rushden & Diamonds"):     "Burton Albion",         # 4-0
    ("Carlisle United", "Salford City"):             "Carlisle United",       # 1-0
    ("Cheltenham Town", "FC Halifax Town"):          "Cheltenham Town",       # 2-0
    ("Chesterfield", "Yeovil Town"):                 "Chesterfield",          # 4-3
    ("Colchester United", "Worcester City"):         "Colchester United",     # 1-0
    ("Crewe Alexandra", "AFC Wimbledon"):            "Crewe Alexandra",       # 2-1
    ("Fleetwood Town", "Rochdale"):                  "Rochdale",              # 1-2 AET
    ("Guiseley", "Sutton United"):                   "Guiseley",              # 1-0 (94' pen)
    ("Harrogate Town", "AFC Fylde"):                 "AFC Fylde",             # 1-4
    ("Kidderminster Harriers", "Doncaster Rovers"):  "Kidderminster Harriers",# 3-0
    ("Leyton Orient", "Harborough Town"):            "Leyton Orient",         # 5-1
    ("Luton Town", "Forest Green Rovers"):           "Luton Town",            # 2-0
    ("Mansfield Town", "Macclesfield"):              "Mansfield Town",        # 3-0
    ("Newport County", "Walsall"):                   "Newport County",        # 3-1
    ("Oxford City", "Leicester City"):               "Leicester City",        # 2-4
    ("Oxford United", "Stevenage"):                  "Stevenage",             # 0-1
    ("Plymouth Argyle", "Alvechurch"):               "Plymouth Argyle",       # 4-0
    ("Port Vale", "Scunthorpe United"):              "Port Vale",             # 4-2
    ("Salisbury", "Sholing"):                        "Salisbury",             # 6-0
    ("Shrewsbury Town", "Eastleigh"):                "Shrewsbury Town",       # 2-1
    ("York City", "Northampton Town"):               "York City",             # 4-0
    ("Gillingham", "Barrow"):                        "Barrow",                # 0-1 (90+')
}

_FA_CUP_R2_ACTUAL = {}

_FA_CUP_R2_TIES = [
    ("Chesterfield", "Cheltenham Town"),
    ("Guiseley", "Notts County"),
    ("Wigan Athletic", "Barnsley"),
    ("Exeter City", "Stevenage"),
    (("Plymouth Parkway", "Berkhamsted"), "Barnet"),
    ("York City", "Carlisle United"),
    ("Crewe Alexandra", "Plymouth Argyle"),
    ("AFC Fylde", "Luton Town"),
    ("Barrow", "Kidderminster Harriers"),
    ("Colchester United", "Mansfield Town"),
    ("Rochdale", "Newport County"),
    ("Dover Athletic", "Leicester City"),
    ("Port Vale", "Leyton Orient"),
    ("Grimsby Town", "Oldham Athletic"),
    ("Shrewsbury Town", "Burton Albion"),
    ("Salisbury", "Blackpool"),
    ("Wimborne Town", "Bradford City"),
    ("Rotherham United", "Bristol Rovers"),
    ("Reading", "Stockport County"),
    ("Wycombe Wanderers", "Milton Keynes Dons"),
]

_FA_CUP_R3_CHAMPIONSHIP = [
    "Wolves", "Southampton", "Burnley", "Norwich",
    "West Brom", "Middlesbrough", "Sheffield United", "Bristol City",
    "Millwall", "Swansea", "QPR", "Preston",
    "Stoke", "Watford", "Blackburn", "Portsmouth",
    "Derby", "Cardiff", "Charlton", "Wrexham",
    "Birmingham", "Bolton", "Stockport", "Huddersfield",
]


def _fa_cup_elo(team, pl_elos=None, pl_teams=None):
    if pl_elos and pl_teams and team in pl_teams:
        return pl_elos.get(team, LEAGUE_AVERAGE_ELO)
    if pl_elos and team in pl_elos:
        return pl_elos[team]
    table = carabao_elo()
    if team in table:
        return table[team]
    mapped = carabao_name_map(team)
    if mapped in table:
        return table[mapped]
    alt = _FA_CUP_EXTRA_NAMES.get(team)
    if alt and alt in table:
        return table[alt]
    if team in _FA_CUP_MISSING_ELOS:
        return _FA_CUP_MISSING_ELOS[team]
    return 1100.0


FA_CUP_ELO_COMPRESS = 0.55
FA_CUP_MEAN_ELO = 1750.0
FA_CUP_PULL = 0.35

CARABAO_ELO_COMPRESS = 0.6
CARABAO_MEAN_ELO = 1750.0
CARABAO_PULL = 0.30


def _build_fa_cup_elo_table(pl_elos, pl_teams, extra_teams=()):
    base_lookup = {}
    for t in extra_teams:
        base_lookup[t] = _fa_cup_elo(t, pl_elos, pl_teams)
    for t in pl_teams:
        base_lookup[t] = _fa_cup_elo(t, pl_elos, pl_teams)
    for t in _FA_CUP_R3_CHAMPIONSHIP:
        if t not in base_lookup:
            base_lookup[t] = _fa_cup_elo(t, pl_elos, pl_teams)
    for t in _FA_CUP_MISSING_ELOS:
        if t not in base_lookup:
            base_lookup[t] = _fa_cup_elo(t, pl_elos, pl_teams)
    return {t: FA_CUP_MEAN_ELO + (e - FA_CUP_MEAN_ELO) * (1.0 - FA_CUP_PULL)
            for t, e in base_lookup.items()}


def _sim_fa_cup_match(rng, team_a, team_b, ea, eb, neutral=False, track=(),
                       venue_aware=True, global_seed=None, sim_idx=None, fix_idx=None):
    results = {t: None for t in track if t in (team_a, team_b)}
    if neutral:
        ha, ha_b = (0.0, 0.0)
        if venue_aware:
            ha, ha_b = final_home_advantage(team_a, team_b, "FA Cup")
    else:
        ha, ha_b = HOME_ADVANTAGE_ELO, 0.0
    diff = (ea + ha - eb - ha_b) * FA_CUP_ELO_COMPRESS
    lh, la = expected_goals(LEAGUE_AVERAGE_ELO + diff, LEAGUE_AVERAGE_ELO, home_adv=0.0)
    rnd = rng.random
    hg = _poisson_inline(rnd, lh)
    ag = _poisson_inline(rnd, la)
    if hg > ag:
        winner = team_a
    elif ag > hg:
        winner = team_b
    else:
        h2 = _poisson_inline(rnd, lh * EXTRA_TIME_XG_FACTOR)
        a2 = _poisson_inline(rnd, la * EXTRA_TIME_XG_FACTOR)
        if h2 > a2:
            winner = team_a
        elif a2 > h2:
            winner = team_b
        else:
            p = pen_win_probability(ea + ha, eb + ha_b)
            winner = team_a if rnd() < p else team_b
    return (winner, {t: 'W' if t == winner else 'L' for t in results})


def _resolve_slot(rng, slot, elo_table, track=(),
                   global_seed=None, sim_idx=None, fix_idx=None):
    """Resolve a fixture slot (string or (a, b) tuple) to a team name.

    Always returns ``(winner, results)`` where *results* is ``{}`` when the
    slot is already a concrete team name.
    """
    if isinstance(slot, str):
        return slot, {}
    a, b = slot
    return _sim_fa_cup_match(rng, a, b,
                             elo_table.get(a, 1500.0),
                             elo_table.get(b, 1500.0),
                             track=track,
                             global_seed=global_seed, sim_idx=sim_idx, fix_idx=fix_idx)


def _draw_pairs(rng, teams, global_seed=None, sim_idx=None, fix_idx=None):
    if len(teams) % 2 != 0:
        raise ValueError(f"Expected even number of teams ({len(teams)}) for FA Cup draw")
    shuffled = list(teams)
    rng.shuffle(shuffled)
    return [(shuffled[i], shuffled[i + 1]) for i in range(0, len(shuffled), 2)]


def _play_round(rng, pairs, elo_table, neutral=False, track=(),
                global_seed=None, sim_idx=None, fix_idx_prefix=0):
    out = []
    tr = {t: [] for t in track}
    for j, (home, away) in enumerate(pairs):
        eh = elo_table.get(home, 1500.0)
        ea = elo_table.get(away, 1500.0)
        w, r = _sim_fa_cup_match(rng, home, away, eh, ea,
                                 neutral=neutral, track=track,
                                 global_seed=global_seed, sim_idx=sim_idx, fix_idx=None)
        out.append(w)
        for t, v in r.items():
            tr[t].extend(v)
    return out, tr


def _fa_cup_advance(rng, teams, elo_table, neutral, track, team_results,
                    next_fix, global_seed, sim_idx):
    """Draw pairs, play one FA Cup round, merge tracked results, return winners."""
    pairs = _draw_pairs(rng, teams, global_seed=global_seed, sim_idx=sim_idx, fix_idx=None)
    winners, res = _play_round(rng, pairs, elo_table, neutral=neutral, track=track,
                               global_seed=global_seed, sim_idx=sim_idx, fix_idx_prefix=next_fix())
    if track:
        for t, v in res.items():
            team_results[t].extend(v)
    return winners


def simulate_fa_cup(rng=None, pl_elos=None, pl_teams=None, track=(),
                    global_seed=None, sim_idx=None):
    if len(_FA_CUP_R1_TIES) % 2 != 0:
        raise ValueError(
            f"_FA_CUP_R1_TIES must have an even number of ties (has {len(_FA_CUP_R1_TIES)})"
        )
    pl_teams = pl_teams or set()
    pl_elos = pl_elos or {}
    if rng is None and global_seed is not None:
        rng = Rng(sub_seed(global_seed, "FACup", sim_idx))
    elo_table = _build_fa_cup_elo_table(pl_elos, pl_teams, extra_teams=[
        t for pair in _FA_CUP_R1_TIES for t in pair])
    team_results = {t: [] for t in track} if track else {}
    fix_counter = [0]

    def next_fix():
        fix_counter[0] += 1
        return fix_counter[0]

    # Round 1 — resolve slots then play knockout ties
    r1_winners = []
    for home_slot, away_slot in _FA_CUP_R1_TIES:
        fi = next_fix()
        home, hr = _resolve_slot(rng, home_slot, elo_table, track=track,
                                 global_seed=global_seed, sim_idx=sim_idx, fix_idx=fi)
        fi = next_fix()
        away, ar = _resolve_slot(rng, away_slot, elo_table, track=track,
                                 global_seed=global_seed, sim_idx=sim_idx, fix_idx=fi)
        if track:
            for t, v in hr.items(): team_results[t].append(v)
            for t, v in ar.items(): team_results[t].append(v)

        # ---- NEW: use the real R1 result if we have one ----
        actual_winner = _FA_CUP_R1_ACTUAL.get((home, away))
        if actual_winner is not None:
            r1_winners.append(actual_winner)
            if track:
                if actual_winner == home:
                    team_results.setdefault(home, []).append('W')
                    team_results.setdefault(away, []).append('L')
                else:
                    team_results.setdefault(away, []).append('W')
                    team_results.setdefault(home, []).append('L')
            continue

        eh = elo_table.get(home, 1500.0)
        ea = elo_table.get(away, 1500.0)
        fi = next_fix()
        w, r = _sim_fa_cup_match(rng, home, away, eh, ea, track=track,
                                 global_seed=global_seed, sim_idx=sim_idx, fix_idx=fi)
        r1_winners.append(w)
        if track:
            for t, v in r.items(): team_results[t].append(v)

    r2_winners = []
    for home_slot, away_slot in _FA_CUP_R2_TIES:
        fi = next_fix()
        home, hr = _resolve_slot(rng, home_slot, elo_table, track=track,
                                 global_seed=global_seed, sim_idx=sim_idx, fix_idx=fi)
        fi = next_fix()
        away, ar = _resolve_slot(rng, away_slot, elo_table, track=track,
                                 global_seed=global_seed, sim_idx=sim_idx, fix_idx=fi)
        if track:
            for t, v in hr.items(): team_results[t].append(v)
            for t, v in ar.items(): team_results[t].append(v)

        actual_winner = _FA_CUP_R2_ACTUAL.get((home, away))
        if actual_winner is not None:
            r2_winners.append(actual_winner)
            if track:
                if actual_winner == home:
                    team_results.setdefault(home, []).append('W')
                    team_results.setdefault(away, []).append('L')
                else:
                    team_results.setdefault(away, []).append('W')
                    team_results.setdefault(home, []).append('L')
            continue

        eh = elo_table.get(home, 1500.0)
        ea = elo_table.get(away, 1500.0)
        fi = next_fix()
        w, r = _sim_fa_cup_match(rng, home, away, eh, ea, track=track,
                                 global_seed=global_seed, sim_idx=sim_idx, fix_idx=fi)
        r2_winners.append(w)
        if track:
            for t, v in r.items(): team_results[t].append(v)
    r3_field = list(r2_winners)
    for t in sorted(pl_teams):
        if t not in r3_field:
            r3_field.append(t)
    for t in _FA_CUP_R3_CHAMPIONSHIP:
        if t not in pl_teams and t not in r3_field:
            r3_field.append(t)
    if len(r3_field) % 2 == 1:
        raise ValueError(f"FA Cup Third Round field has odd number of teams ({len(r3_field)}), cannot form pairs")
    r3_winners = _fa_cup_advance(rng, r3_field, elo_table, False, track, team_results, next_fix, global_seed, sim_idx)
    r4_winners = _fa_cup_advance(rng, r3_winners, elo_table, False, track, team_results, next_fix, global_seed, sim_idx)
    r5_winners = _fa_cup_advance(rng, r4_winners, elo_table, False, track, team_results, next_fix, global_seed, sim_idx)
    qf_winners = _fa_cup_advance(rng, r5_winners, elo_table, False, track, team_results, next_fix, global_seed, sim_idx)
    sf_winners = _fa_cup_advance(rng, qf_winners, elo_table, True, track, team_results, next_fix, global_seed, sim_idx)
    fi = next_fix()
    final_winners, f_res = _play_round(rng, [(sf_winners[0], sf_winners[1])],
                                       elo_table, neutral=True, track=track,
                                       global_seed=global_seed, sim_idx=sim_idx, fix_idx_prefix=fi)
    if track:
        for t, v in f_res.items(): team_results[t].extend(v)
    return final_winners[0], team_results


# =============================================================================
# SOLVED METRIC — modal position
# =============================================================================
def solved_metric(position_counts, teams, total_sims, n_positions=None, smoothing=1.0):
    """Greedy modal assignment: each position gets its most-likely remaining team.

    Returns (avg_pct, joint_pct, assignment) where:
      avg_pct   = mean assigned probability across positions (percent)
      joint_pct = product of assigned probabilities (percent)
      assignment = [(pos, team, prob_pct), ...]

    Every team *must* finish in exactly one of the ``n_positions`` slots, so
    empirical zeros (a team that never finished at a given position in the
    simulated sample) are smoothed over with Laplace smoothing.  This keeps the
    joint product strictly positive instead of collapsing to exactly ``0.0``.
    """
    if n_positions is None:
        n_positions = len(teams)
    probs = {}
    for t in teams:
        counts = position_counts.get(t, {})
        total_t = sum(counts.values()) if counts else 0.0
        denom = total_t + smoothing * n_positions
        probs[t] = {p: (counts.get(p, 0) + smoothing) / denom
                    for p in range(1, n_positions + 1)}

    remaining = set(teams)
    assignment = []
    for pos in range(1, n_positions + 1):
        if not remaining:
            break
        best = max(remaining, key=lambda t: probs[t][pos])
        p = probs[best][pos]
        assignment.append((pos, best, p * 100.0))
        remaining.remove(best)

    if not assignment:
        return 0.0, 0.0, []
    avg = sum(p for _, _, p in assignment) / len(assignment)
    joint = 1.0
    for _, _, p in assignment:
        joint *= p / 100.0
    return avg, joint * 100.0, assignment


def _fmt_tiny_pct(pct):
    """Format a percentage, using 10^-N notation when it rounds to 0.000000%.

    Joint probabilities (products of many assigned probs) can be so small that
    ``{:.6f}%`` prints as 0.000000%, which is uninformative.  For those cases
    show the order of magnitude instead, e.g. ~10^-12%.
    """
    if pct <= 0.0:
        return "0.000000%"
    if pct < 0.0000005:  # would print as 0.000000 at 6 decimal places
        exp = math.floor(math.log10(pct))
        return "~10^{}%".format(exp)
    return "{:.6f}%".format(pct)


def _fmt_solved_pct(pct):
    """Format a solved percentage: 3-dp regular if > 1e-4, else tiny notation."""
    if pct > 1e-4:
        return "{:.3f}%".format(pct)
    return _fmt_tiny_pct(pct)


# =============================================================================
# PROGRESS RENDERER
# =============================================================================
def render_progress(done, total, start):
    frac = done / max(total, 1)
    elapsed = time.time() - start
    eta = elapsed * (1.0 - frac) / frac if done > 0 else 0.0
    width = 30
    filled = min(round(frac * width), width)
    if filled >= width:
        bar = '[' + ('=' * width) + ']'
    else:
        bar = '[' + ('=' * filled) + '>' + (' ' * (width - filled - 1)) + ']'
    return f"{bar} {frac*100:.1f}%  ETA {eta:.0f}s"


def spot_pct_map(spots):
    n = len(spots) or 1
    counts = Counter(spots)
    return {k: v / n * 100.0 for k, v in counts.items()}


# =============================================================================
# SETUP — shared between main() and run_simulation()
# =============================================================================
def _shared_setup(seed=None):
    if seed is None:
        seed = (int(time.time()) ^ (time.time_ns() % 1_000_000_000)) & 0xFFFFFFFFFFFFFFFF
    rng = Rng(seed)
    ucl_preset = preset_ucl_elos()
    uel_preset = preset_uel_elos()
    uecl_preset = preset_uecl_elos()
    assoc_map = association_map()
    entrants = assoc_entrants()
    actual_results = results_to_map(ACTUAL_RESULTS_ARR)
    cl_actual = results_to_map(CL_ACTUAL_RESULTS_ARR)
    uel_actual = results_to_map(UEL_ACTUAL_RESULTS_ARR)
    uecl_actual = results_to_map(UECL_ACTUAL_RESULTS_ARR)
    fixtures_list = build_full_round_robin(ACTUAL_RESULTS_ARR, rng=rng)
    pl_teams = {t for f in fixtures_list for t in f}
    actual_form = build_actual_team_form(ACTUAL_RESULTS_ARR)
    actual_form_adjustments = actual_sack_form_adjustment(actual_form, pl_teams)
    # ---- Build split PL Elos: ML prior → blend with actual results ----
    pl_overall_prior, pl_attack_prior, pl_defense_prior = \
        preset_pl_split_elos(recency_seed=seed)

    pl_overall_built = build_current_pl_ratings(actual_results, pl_teams,
                                                pl_overall_prior, 50.0)
    pl_attack_built  = build_current_pl_ratings(actual_results, pl_teams,
                                                pl_attack_prior, 50.0)
    pl_defense_built = build_current_pl_ratings(actual_results, pl_teams,
                                                pl_defense_prior, 50.0)

    # Base ratings from stats+actual results; final blend is pulled toward the
    # league mean by the percentage of PL games left (based on ACTUAL_RESULTS_ARR).
    pl_overall = pl_overall_built
    pl_attack = pl_attack_built
    pl_defense = pl_defense_built
    pl_games_left_frac = max(0.0, min(1.0,
        (PL_TOTAL_FIXTURES - len(ACTUAL_RESULTS_ARR)) / PL_TOTAL_FIXTURES))

    pl_elos = pl_overall                       # overall Elo (used for European comps etc.)
    ucl_elos = ucl_preset
    uel_elos = uel_preset
    uecl_elos = uecl_preset
    uel_fixtures_std = [[(standardise_uel(h), standardise_uel(a)) for (h, a) in r]
                        for r in UEL_FIXTURES_RAW]
    uecl_fixtures_std = [[(standardise_uecl(h), standardise_uecl(a)) for (h, a) in r]
                         for r in UECL_FIXTURES_RAW]
    ucl_comp = EuropeanCompetition("UCL", CL_FIXTURES_ARR, pl_elos, pl_teams, cl_actual, ucl_elos)
    uel_comp = EuropeanCompetition("UEL", uel_fixtures_std, pl_elos, pl_teams, uel_actual, uel_elos)
    uecl_comp = EuropeanCompetition("UECL", uecl_fixtures_std, pl_elos, pl_teams, uecl_actual, uecl_elos)
    pl_sim = PLSimulator(fixtures_list, pl_elos, actual_results,
                         attack_elos=pl_attack, defense_elos=pl_defense)
    # Base market-derived ratings from Polymarket (title/UCL/top6/relegation priors)
    pl_teams_list = sorted(pl_teams)
    odds_overall = polymarket_prior_to_elos(pl_teams_list)
    # External ELO table (third blend factor, alongside stats and market)
    external_overall = external_elos_to_dict(pl_teams_list)

    # Split market/external overall into attack/defense with additive offsets so
    # the split is preserved and (atk+def)/2 stays aligned with overall.
    odds_attack = {}
    odds_defense = {}
    external_attack = {}
    external_defense = {}
    for team in pl_teams_list:
        base_atk = pl_attack.get(team, LEAGUE_AVERAGE_ELO)
        base_def = pl_defense.get(team, LEAGUE_AVERAGE_ELO)
        base_overall = pl_elos.get(team, LEAGUE_AVERAGE_ELO)
        odds_off = odds_overall.get(team, base_overall) - base_overall
        ext_off = external_overall.get(team, base_overall) - base_overall
        odds_attack[team] = base_atk + odds_off
        odds_defense[team] = base_def + odds_off
        external_attack[team] = base_atk + ext_off
        external_defense[team] = base_def + ext_off

    return {
        'seed': seed,             # <-- fix #2: expose the seed
        'rng': rng,
        'ucl_preset': ucl_preset,
        'uel_preset': uel_preset,
        'uecl_preset': uecl_preset,
        'assoc_map': assoc_map,
        'entrants': entrants,
        'actual_results': actual_results,
        'cl_actual': cl_actual,
        'uel_actual': uel_actual,
        'uecl_actual': uecl_actual,
        'fixtures_list': fixtures_list,
        'pl_teams': pl_teams,
        'actual_form_adjustments': actual_form_adjustments,
        'pl_elos': pl_elos,
        'pl_attack': pl_attack,          # <-- new
        'pl_defense': pl_defense,        # <-- new
        'odds_overall': odds_overall,    # <-- new: base odds ratings
        'odds_attack': odds_attack,
        'odds_defense': odds_defense,
        'external_overall': external_overall,  # <-- new: external ELO ratings
        'external_attack': external_attack,
        'external_defense': external_defense,
        'ucl_comp': ucl_comp,
        'uel_comp': uel_comp,
        'uecl_comp': uecl_comp,
        'pl_sim': pl_sim,
        'pl_games_left_frac': pl_games_left_frac,
    }


def _normalize_tournament_result(result, context):
    """Coerce a tournament return into ``(winner, team_results)`` and validate.

    ``run_carabao_tournament`` and ``simulate_fa_cup`` return either a bare
    winner string (tracking off) or a ``(winner, team_results)`` tuple
    (tracking on).  This normalises both forms and raises if the winner is
    missing or not a string.
    """
    if not isinstance(result, tuple) or len(result) != 2:
        result = (result, {}) if isinstance(result, str) else (result, {})
    winner, team_results = result
    if not isinstance(winner, str) or not winner:
        raise RuntimeError(
            f"{context}: winner is {winner!r} "
            f"(type={type(winner).__name__}) — check simulation return")
    return winner, team_results


def _simulate_comp(comp, global_seed, sim_idx, **kwargs):
    return comp.simulate(global_seed, sim_idx, **kwargs)


def _simulate_carabao(global_seed, sim_idx, track=()):
    raw = run_carabao_tournament(global_seed=global_seed, sim_idx=sim_idx, track=track)
    return _normalize_tournament_result(raw, "_simulate_carabao/run_carabao_tournament")


def _simulate_fa_cup(global_seed, sim_idx, pl_elos, pl_teams, track=()):
    raw = simulate_fa_cup(global_seed=global_seed, sim_idx=sim_idx,
                          pl_elos=pl_elos, pl_teams=pl_teams, track=track)
    return _normalize_tournament_result(raw, "_simulate_fa_cup/simulate_fa_cup")


def _simulate_pl(pl_sim, global_seed, sim_idx, fatigue_info, track=(),
                 man_city_penalty=None, sim_attack=None, sim_defense=None):
    result = pl_sim.simulate_season(fatigue_info, None,
                                    global_seed=global_seed, sim_idx=sim_idx, track=track,
                                    man_city_penalty=man_city_penalty,
                                    sim_attack=sim_attack, sim_defense=sim_defense)
    return result


def _run_one_sim(s, sim_idx, global_seed):
    pl_teams = s['pl_teams']
    actual_form_adjustments = s['actual_form_adjustments']
    ucl_comp = s['ucl_comp']
    uel_comp = s['uel_comp']
    uecl_comp = s['uecl_comp']
    pl_sim = s['pl_sim']
    # Per-sim varied ratings: blend stats + Polymarket + external, pull toward
    # league average by % of PL games left (ACTUAL_RESULTS_ARR), then ±5% variation.
    var_rng = Rng(sub_seed(global_seed, "RatingVariation", sim_idx))
    varied_overall, varied_attack, varied_defense = build_varied_ratings(
        s['pl_elos'], s['pl_attack'], s['pl_defense'],
        s['odds_overall'], s['odds_attack'], s['odds_defense'],
        s['external_overall'], s['external_attack'], s['external_defense'],
        var_rng, pull_to_mean_frac=s.get('pl_games_left_frac', 0.0))
    # Merge with base elos so non-PL European teams keep their preset ratings
    ucl_overall = dict(ucl_comp.base_elos); ucl_overall.update(varied_overall)
    uel_overall = dict(uel_comp.base_elos); uel_overall.update(varied_overall)
    uecl_overall = dict(uecl_comp.base_elos); uecl_overall.update(varied_overall)
    ucl_res = _simulate_comp(ucl_comp, global_seed, sim_idx,
                             track={"Man United"}, stop_when_no_pl_teams=False,
                             base_elos_override=ucl_overall)
    uel_res = _simulate_comp(uel_comp, global_seed, sim_idx,
                             stop_when_no_pl_teams=False,
                             base_elos_override=uel_overall)
    uecl_res = _simulate_comp(uecl_comp, global_seed, sim_idx,
                              stop_when_no_pl_teams=False,
                              base_elos_override=uecl_overall)
    fatigue_info = {}
    for team in pl_teams:
        if team in ucl_res.elim_rounds:
            fatigue_info[team] = (ucl_res.elim_rounds[team], "UCL")
        elif team in uel_res.elim_rounds:
            fatigue_info[team] = (uel_res.elim_rounds[team], "UEL")
        elif team in uecl_res.elim_rounds:
            fatigue_info[team] = (uecl_res.elim_rounds[team], "UECL")
    mc_penalty = sample_man_city_deduction(global_seed, sim_idx)
    # fix #1: unpack 3, since simulate_season now returns 3
    ranking, points, pl_team_results = _simulate_pl(
        pl_sim, global_seed, sim_idx,
        fatigue_info, track={"Man United"},
        man_city_penalty=mc_penalty,
        sim_attack=varied_attack, sim_defense=varied_defense)
    euro_adj = {}
    for team in pl_teams:
        adj = 0.0
        adj += european_sack_adjustment(team, ucl_res, ucl_comp, EURO_RISK_WEIGHT["UCL"])
        adj += european_sack_adjustment(team, uel_res, uel_comp, EURO_RISK_WEIGHT["UEL"])
        adj += european_sack_adjustment(team, uecl_res, uecl_comp, EURO_RISK_WEIGHT["UECL"])
        euro_adj[team] = adj
    risks = compute_sack_risk(ranking, euro_adjustments=euro_adj,
                              actual_form_adjustments=actual_form_adjustments)
    tot_risk = sum(risks.values())
    carabao_result = _simulate_carabao(global_seed, sim_idx, track={"Man United"})
    if isinstance(carabao_result, tuple) and len(carabao_result) == 2:
        carabao_winner, carabao_team_results = carabao_result
    else:
        carabao_winner = carabao_result if isinstance(carabao_result, str) else None
        carabao_team_results = {"Man United": []}
    if carabao_winner is None:
        raise RuntimeError(
            f"carabao_winner is None at sim {sim_idx} "
            f"— check _simulate_carabao/run_carabao_tournament return")

    fa_cup_result = _simulate_fa_cup(
        global_seed, sim_idx, s['pl_elos'], pl_teams, track={"Man United"})
    if isinstance(fa_cup_result, tuple) and len(fa_cup_result) == 2:
        fa_cup_winner, fa_cup_team_results = fa_cup_result
    else:
        fa_cup_winner = fa_cup_result if isinstance(fa_cup_result, str) else None
        fa_cup_team_results = {"Man United": []}
    if fa_cup_winner is None:
        raise RuntimeError(
            f"fa_cup_winner is None at sim {sim_idx} "
            f"— check _simulate_fa_cup/simulate_fa_cup return")
    coeffs = all_association_coefficients(ucl_res, uel_res, uecl_res, s['assoc_map'], s['entrants'])
    ranked_coeffs = sorted(coeffs.items(), key=lambda x: -x[1])
    top2 = {a for a, _ in ranked_coeffs[:2]}
    has_eps = "England" in top2
    spots = allocate_european_spots(
        ranking, carabao_winner, pl_teams,
        ucl_res.winner, uel_res.winner, uecl_res.winner,
        has_eps, fa_cup_winner)
    manu_results = None
    if "Man United" in pl_teams:
        manu_results = list(pl_team_results.get("Man United", []))
    return {
        'ucl_res': ucl_res,
        'uel_res': uel_res,
        'uecl_res': uecl_res,
        'ranking': ranking,
        'points': points,
        'risks': risks,
        'tot_risk': tot_risk,
        'carabao_winner': carabao_winner,
        'fa_cup_winner': fa_cup_winner,
        'carabao_team_results': carabao_team_results,
        'fa_cup_team_results': fa_cup_team_results,
        'pl_team_results': pl_team_results,
        'manu_results': manu_results,
        'coeffs': coeffs,
        'ranked_coeffs': ranked_coeffs,
        'top2': top2,
        'has_eps': has_eps,
        'spots': spots,
        'points_dist': {t: points[t] for t in ranking},
        'position_counts': {pos + 1: team for pos, team in enumerate(ranking)},
        'title_winner': ranking[0] if ranking else None,
        'euro_winners': {c: r.winner for c, r in (("UCL", ucl_res), ("UEL", uel_res), ("UECL", uecl_res))},
        'english_three_comp': (
            ucl_res.winner in pl_teams and uel_res.winner in pl_teams and uecl_res.winner in pl_teams
            if (ucl_res.winner and uel_res.winner and uecl_res.winner) else False),
        'man_city_penalty': mc_penalty,
    }


# =============================================================================
# SIM OUTPUT ACCUMULATION HELPERS (shared by main() and run_simulation())
# =============================================================================
_EURO_COMPS = ("UCL", "UEL", "UECL")
_REACH_THRESHOLDS = (1, 2, 3, 4, 5)
_REACH_NAMES = ("r16", "qf", "sf", "final", "wins")
_EURO_LABELS = {
    "UCL": "UCL  (Champions League)",
    "UEL": "UEL  (Europa League)",
    "UECL": "UECL (Conference League)",
}
_PENALTY_BUCKETS = {"0": 0, "1-9": 0, "10-19": 0, "20-29": 0, "30-49": 0, "50-75": 0}


def _compute_penalty_dist(penalties):
    """Bucket Man City point penalties into ranges; return (buckets, n_total, n_expel)."""
    n_total = len(penalties)
    n_expel = sum(1 for p in penalties if p == "EXPEL")
    buckets = dict(_PENALTY_BUCKETS)
    for d in penalties:
        if not isinstance(d, int):
            continue
        if d ==  0:        buckets["0"]     += 1
        elif d <=  9:      buckets["1-9"]   += 1
        elif d <= 19:      buckets["10-19"] += 1
        elif d <= 29:      buckets["20-29"] += 1
        elif d <= 49:      buckets["30-49"] += 1
        else:              buckets["50-75"] += 1
    return buckets, n_total, n_expel


def _accumulate_euro_results(r, comp_name, euro_positions, euro_points, reach_stores):
    """Accumulate league positions/points and knockout-round elimination counts."""
    pos_map = euro_positions[comp_name]
    pts_map = euro_points[comp_name]
    for pos, team in enumerate(r.ranking):
        pos_map[team][pos + 1] += 1
        pts_map[team].append(r.league_points[team])
    if r.winner is not None:
        for team, elim in r.elim_rounds.items():
            for threshold, store in zip(_REACH_THRESHOLDS, reach_stores):
                if elim >= threshold:
                    store[comp_name][team] += 1


def _accumulate_sack_risk(risks, tot_risk, sack_prob_accum, sack_any_accum):
    """Return expected firings for one sim; updates accumulators in place."""
    if tot_risk <= 0.0:
        return 0.0
    for team, r in risks.items():
        sack_prob_accum[team] += r / tot_risk
    avg_r = tot_risk / len(risks)
    total_p = 0.0
    for team, r in risks.items():
        p_any = 1.0 - math.exp(-0.35 * r / avg_r)
        sack_any_accum[team] += p_any
        total_p += p_any
    return total_p


# =============================================================================
# MAIN — thin formatter; delegates simulation to run_simulation()
# =============================================================================
_MAIN_START = None


def cli_progress(done, total):
    if _MAIN_START is None:
        return
    sys.stderr.write("\r" + render_progress(done, total, _MAIN_START) + "  ")
    sys.stderr.flush()


def main():
    global _MAIN_START
    print("\n" + "=" * 80)
    print("UNIFIED PREMIER LEAGUE + EUROPEAN + CARABAO CUP SIMULATION (Python)")
    print("=" * 80)
    s = _shared_setup()
    rng = s['rng']
    pl_teams = s['pl_teams']
    pl_elos = s['pl_elos']
    print_christmas_table(pl_teams, pl_elos, s['actual_results'], rng,
                          attack_elos=s['pl_attack'],
                          defense_elos=s['pl_defense'],
                          global_seed=s['seed'],
                          odds_elos=s['odds_overall'],
                          external_elos=s['external_overall'])
    _MAIN_START = time.time()
    res = run_simulation(NUM_PL_SIMS, s=s, on_progress=cli_progress)
    sys.stderr.write("\r" + render_progress(NUM_PL_SIMS, NUM_PL_SIMS, _MAIN_START) + "  \n")
    total = res["n_sims"]
    pl_teams_set = res["pl_teams_set"]
    points_dist = res["points_dist_raw"]
    position_counts = res["position_counts_raw"]
    title_counts = res["title_counts_raw"]
    relegation_counts = res["relegation_counts_raw"]
    ucl_qual_counts = res["ucl_qual_counts_raw"]
    uel_qual_counts = res["uel_qual_counts_raw"]
    uecl_qual_counts = res["uecl_qual_counts_raw"]
    euro_positions = res["euro_positions_raw"]
    euro_points = res["euro_points_raw"]
    euro_reach = res["euro_reach"]
    euro_wins = res["euro_wins_raw"]
    euro_win_counts = res["euro_win_counts_raw"]
    carabao_wins = res["carabao_wins_raw"]
    carabao_pl_winner_count = res["carabao_pl_winner_count"]
    carabao_nonpl_winner_count = res["carabao_nonpl_winner_count"]
    fa_cup_wins = res["fa_cup_wins_raw"]
    english_three_comp = res["english_three_comp"]
    eps_earned = res["eps_earned"]
    fifth_place_ucl = res["fifth_place_ucl"]
    england_coeff_accum = res["england_coeff_accum"]
    assoc_coeff_accum = res["assoc_coeff_accum"]
    assoc_top2_count = res["assoc_top2_count"]
    manutd_streaks = res["manutd_streaks"]
    manutd_5plus = res["manutd_5plus"]
    manutd_streak_max = res["manutd_streak_max"]
    man_city_penalties = res["man_city_penalties"]
    pl_ucl_spots = res["pl_ucl_spots"]
    pl_uel_spots = res["pl_uel_spots"]
    pl_uecl_spots = res["pl_uecl_spots"]
    pl_total_spots = res["pl_total_spots"]
    pl_ucl_min = res["pl_ucl_min"]
    pl_ucl_max = res["pl_ucl_max"]
    pl_uel_min = res["pl_uel_min"]
    pl_uel_max = res["pl_uel_max"]
    pl_uecl_min = res["pl_uecl_min"]
    pl_uecl_max = res["pl_uecl_max"]
    pl_total_min = res["pl_total_min"]
    pl_total_max = res["pl_total_max"]
    sack_prob_accum = res["sack_prob_raw"]
    sack_any_accum = res["sack_any_prob_raw"]
    avg_firings = res["avg_firings_per_season"]
    print("\nElapsed {:.1f}s".format(time.time() - _MAIN_START))
    print("\nElo method: blended ratings (stats 55%, Polymarket market prior 15%, external ELO 30%), "
          "then pulled toward league average by % of PL games left (based on ACTUAL_RESULTS_ARR), "
          "with additive atk/def offsets and per-sim ±5% variation. "
          "xG uses home-attack × away-defence and away-attack × home-defence split.")
    print("\n" + "=" * 80)
    print("EPS (EXTRA PERFORMANCE SPOT) — 2027/28 UCL")
    print("=" * 80)
    if england_coeff_accum:
        mean_eng = sum(england_coeff_accum) / len(england_coeff_accum)
        print("England avg coefficient: {:.3f}".format(mean_eng))
    print("P(England Top 2 -> EPS 5th PL team in UCL): {:.2f}%".format(eps_earned / total * 100.0))
    print("P(5th place actually takes UCL spot): {:.2f}%".format(fifth_place_ucl / total * 100.0))
    print("\n" + "=" * 80)
    print("MANAGER SACK RISK")
    print("=" * 80)
    print("Avg managers fired / season: {:.2f}".format(avg_firings))
    sack_sorted = sorted(sack_prob_accum.items(), key=lambda x: -x[1])
    sack_rows = []
    for team, prob in sack_sorted:
        p_next = prob / total * 100.0
        p_any = sack_any_accum.get(team, 0.0) / total * 100.0
        sack_rows.append([
            "{} ({})".format(MANAGER_DATA.get(team, ("?",))[0], team),
            "{:.2f}%".format(p_next), "{:.2f}%".format(p_any),
        ])
    print_table(["Manager (Team)", "P(next)", "P(sacked)"], sack_rows,
                aligns=["l", "r", "r"])
    top2_sorted = sorted(assoc_top2_count.items(), key=lambda x: -x[1])
    print("\nTop-2 finish probability by association:")
    assoc_rows = []
    for assoc, count in top2_sorted:
        vals = assoc_coeff_accum.get(assoc, [])
        avg = sum(vals) / len(vals) if vals else 0.0
        assoc_rows.append([assoc, "{:.2f}%".format(count / total * 100.0),
                           "{:.3f}".format(avg)])
    print_table(["Association", "%", "Avg coeff"], assoc_rows,
                aligns=["l", "r", "r"])
    print("\n" + "=" * 80)
    print("AVERAGE PREMIER LEAGUE EUROPEAN SPOTS")
    print("=" * 80)
    avg_spot_rows = [
        ["UCL", "{:.2f}".format(sum(pl_ucl_spots) / total), str(pl_ucl_min), str(pl_ucl_max)],
        ["UEL", "{:.2f}".format(sum(pl_uel_spots) / total), str(pl_uel_min), str(pl_uel_max)],
        ["UECL", "{:.2f}".format(sum(pl_uecl_spots) / total), str(pl_uecl_min), str(pl_uecl_max)],
        ["Total", "{:.2f}".format(sum(pl_total_spots) / total), str(pl_total_min), str(pl_total_max)],
    ]
    print_table(["Comp", "Avg", "Min", "Max"], avg_spot_rows,
                aligns=["l", "r", "r", "r"])
    spot_dist = res["spot_dist"]
    ucl_dist = spot_dist["UCL"]
    uel_dist = spot_dist["UEL"]
    uecl_dist = spot_dist["UECL"]
    total_dist = spot_dist["Total"]
    d_min = min(pl_ucl_min, pl_uel_min, pl_uecl_min, pl_total_min)
    d_max = max(pl_ucl_max, pl_uel_max, pl_uecl_max, pl_total_max)
    print("\nSPOT COUNT DISTRIBUTION (% chance per simulation)")

    def fmt(m, sp):
        v = m.get(sp)
        return "{:.2f}%".format(v) if v is not None and v > 0.0 else "-"

    dist_rows = []
    for sp in range(d_min, d_max + 1):
        dist_rows.append([
            str(sp), fmt(ucl_dist, sp), fmt(uel_dist, sp),
            fmt(uecl_dist, sp), fmt(total_dist, sp),
        ])
    print_table(["Spots", "UCL", "UEL", "UECL", "Total"], dist_rows,
                aligns=["r", "r", "r", "r", "r"])
    print("\n" + "=" * 135)
    print("FINAL PREMIER LEAGUE PROJECTIONS")
    print("=" * 135)
    avg_pts_map = res["avg_points"]
    teams_sorted = sorted(pl_teams_set, key=avg_pts_map.__getitem__, reverse=True)
    proj_rows = []
    for rank, t in enumerate(teams_sorted):
        title_pct = title_counts.get(t, 0) / total * 100.0
        ucl_pct = ucl_qual_counts.get(t, 0) / total * 100.0
        uel_pct = uel_qual_counts.get(t, 0) / total * 100.0
        uecl_pct = uecl_qual_counts.get(t, 0) / total * 100.0
        euro_pct = ucl_pct + uel_pct + uecl_pct
        rel_pct = relegation_counts.get(t, 0) / total * 100.0
        proj_rows.append([
            str(rank + 1), t, "{:.2f}".format(avg_pts_map[t]),
            "{:.2f}".format(title_pct), "{:.2f}".format(ucl_pct),
            "{:.2f}".format(uel_pct), "{:.2f}".format(uecl_pct),
            "{:.2f}".format(euro_pct), "{:.2f}".format(rel_pct),
        ])
    print_table(
        ["Rk", "Team", "Pts", "Title%", "UCLAny%", "UELAny%", "UECLAny%", "EuroAny%", "Releg%"],
        proj_rows,
        aligns=["r", "l", "r", "r", "r", "r", "r", "r", "r"],
    )
    print("\n" + "=" * 80)
    print("RELEGATION — POINTS NEEDED TO STAY UP")
    print("=" * 80)
    print("  Avg pts of 17th-placed (last safe) team:   {:.1f}".format(res["safety_line_avg_pts"]))
    print("  Avg pts of 18th-placed (first relegated) team: {:.1f}".format(res["rel_line_avg_pts"]))
    print("  Points typically needed to avoid relegation: {:.1f}".format(res["safety_line_avg_pts"] + 0.5))
    avg_pct, solved_pct, assigned = solved_metric(position_counts, teams_sorted, total)
    print("\n" + "=" * 80)
    print("MOST LIKELY FINAL TABLE (greedy modal assignment)")
    print("=" * 80)
    print("\nLeague 'solved' (avg assigned prob): {}".format(_fmt_solved_pct(avg_pct)))
    print("League 'actually solved' (product of all 20 assigned probs): {}"
          .format(_fmt_solved_pct(solved_pct)))
    top5_avg_pct, top5_solved_pct, top5_assigned = solved_metric(
        position_counts, teams_sorted, total, n_positions=5)
    print("\nTop 5 'solved' (avg assigned prob): {}".format(_fmt_solved_pct(top5_avg_pct)))
    print("Top 5 'actually solved' (product of all 5 assigned probs): {}"
          .format(_fmt_solved_pct(top5_solved_pct)))
    top5_rows = [[str(pos), team, "{:.2f}%".format(pct)] for pos, team, pct in top5_assigned]
    print_table(["Pos", "Team", "P(assigned)"], top5_rows, aligns=["r", "l", "r"])
    assigned_rows = [[str(pos), team, "{:.2f}%".format(pct)] for pos, team, pct in assigned]
    print_table(["Pos", "Team", "P(assigned)"], assigned_rows, aligns=["r", "l", "r"])
    print("\n" + "=" * 80)
    print("CHANCE A PREMIER LEAGUE TEAM WINS EACH EUROPEAN COMPETITION")
    print("=" * 80)
    for comp in _EURO_COMPS:
        total_wins = sum(euro_win_counts[comp].values())
        pct = total_wins / total * 100.0
        label = _EURO_LABELS[comp]
        print("  {}: {:.2f}%".format(label, pct))
    print("  English teams win all 3: {:.2f}%".format(english_three_comp / total * 100.0))
    print("\n  PL team breakdown by winner:")
    for comp in _EURO_COMPS:
        label = _EURO_LABELS[comp]
        pl_wins = {t: v for t, v in euro_win_counts[comp].items() if t in pl_teams_set and v > 0}
        top = sorted(pl_wins.items(), key=lambda x: -x[1])[:5]
        if top:
            winner_rows = [[t, "{:.2f}%".format(c / total * 100.0)] for t, c in top]
            print("\n  {}".format(label))
            print_table(["Team", "%"], winner_rows, aligns=["l", "r"])
        else:
            print("    (no PL team won {} in any sim)".format(label))
    for comp_name in _EURO_COMPS:
        print("\n" + "=" * 130)
        print("{} PREDICTED TABLE".format(comp_name))
        print("=" * 130)
        pos_map = euro_positions[comp_name]
        pts_map = euro_points[comp_name]
        reach_r16 = euro_reach[comp_name]["r16"]
        reach_qf = euro_reach[comp_name]["qf"]
        reach_sf = euro_reach[comp_name]["sf"]
        reach_final = euro_reach[comp_name]["final"]
        wins_map = euro_wins[comp_name]

        def _avg_pts_euro(t):
            v = pts_map.get(t, [])
            return sum(v) / len(v) if v else 0.0

        teams = sorted(
            pos_map.keys(),
            key=lambda t: (
                -reach_r16.get(t, 0),
                -reach_qf.get(t, 0),
                -reach_sf.get(t, 0),
                -reach_final.get(t, 0),
                -wins_map.get(t, 0),
                -_avg_pts_euro(t),
            ),
        )
        euro_rows = []
        for team in teams:
            counts = pos_map[team]
            t8 = sum(counts.get(p, 0) for p in range(1, 9))
            mid = sum(counts.get(p, 0) for p in range(9, 25))
            low = sum(counts.get(p, 0) for p in range(25, 41))
            euro_rows.append([
                team, "{:.2f}".format(_avg_pts_euro(team)),
                "{:.2f}".format(t8 / total * 100.0),
                "{:.2f}".format(mid / total * 100.0),
                "{:.2f}".format(low / total * 100.0),
                "{:.2f}".format(reach_r16.get(team, 0) / total * 100.0),
                "{:.2f}".format(reach_qf.get(team, 0) / total * 100.0),
                "{:.2f}".format(reach_sf.get(team, 0) / total * 100.0),
                "{:.2f}".format(reach_final.get(team, 0) / total * 100.0),
                "{:.2f}".format(wins_map.get(team, 0) / total * 100.0),
            ])
        print_table(
            ["Team", "Pts", "Top8%", "Pos9-24%", "Pos25+%", "R16%", "QF%", "SF%", "Final%", "Win%"],
            euro_rows,
            aligns=["l", "r", "r", "r", "r", "r", "r", "r", "r", "r"],
        )
    print("\n" + "=" * 80)
    print("UEFA LEAGUE PHASES — 'SOLVED' METRICS")
    print("=" * 80)

    def _team_avg_pts_euro(t, pm):
        v = pm.get(t, [])
        return sum(v) / len(v) if v else 0.0

    euro_positions = res["euro_positions_raw"]
    euro_points = res["euro_points_raw"]
    euro_solved_avg = res.get("euro_solved_avg") or {}
    euro_solved = res.get("euro_solved") or {}
    if not euro_solved_avg:
        # Fallback if res was built without the solved-avg keys.
        for comp_name in ("UCL", "UEL", "UECL"):
            pos_map = euro_positions[comp_name]
            pts_map = euro_points[comp_name]
            teams_in_comp = sorted(pos_map.keys(),
                                   key=lambda t: -_team_avg_pts_euro(t, pts_map))
            avg_pct, solved_pct, _ = solved_metric(pos_map, teams_in_comp, total)
            euro_solved_avg[comp_name] = avg_pct
            euro_solved[comp_name] = solved_pct
    unified_euro_solved_avg = (
        res.get("unified_euro_solved_avg")
        or (sum(euro_solved_avg.values()) / len(euro_solved_avg) if euro_solved_avg else 0.0))
    unified_euro_solved = (
        res.get("unified_euro_solved")
        if res.get("unified_euro_solved") is not None
        else (euro_solved.get("UCL", 0.0) * euro_solved.get("UEL", 0.0) * euro_solved.get("UECL", 0.0)))

    print("\nUCL league phase 'solved' (avg assigned prob): {}".format(_fmt_solved_pct(euro_solved_avg.get("UCL", 0.0))))
    print("UCL league phase 'actually solved' (product): {}".format(_fmt_solved_pct(euro_solved.get("UCL", 0.0))))
    print("UEL league phase 'solved' (avg assigned prob): {}".format(_fmt_solved_pct(euro_solved_avg.get("UEL", 0.0))))
    print("UEL league phase 'actually solved' (product): {}".format(_fmt_solved_pct(euro_solved.get("UEL", 0.0))))
    print("UECL league phase 'solved' (avg assigned prob): {}".format(_fmt_solved_pct(euro_solved_avg.get("UECL", 0.0))))
    print("UECL league phase 'actually solved' (product): {}".format(_fmt_solved_pct(euro_solved.get("UECL", 0.0))))

    solved_rows = [
        ["Unified UEFA (avg assigned prob)", _fmt_solved_pct(unified_euro_solved_avg)],
    ]
    for comp_name in ("UCL", "UEL", "UECL"):
        solved_rows.append([
            "{} (avg assigned prob)".format(comp_name),
            _fmt_solved_pct(euro_solved_avg.get(comp_name, 0.0)),
        ])
    solved_rows.append([
        "Unified UEFA actually solved (product)",
        _fmt_solved_pct(unified_euro_solved),
    ])
    print_table(["Metric", "Value"], solved_rows, aligns=["l", "r"])
    print("\n" + "=" * 80)
    print("CARABAO CUP WIN PROBABILITY")
    print("=" * 80)
    r4_teams = {
        "Bradford City", "Peterborough United", "Fleetwood Town", "Arsenal",
        "Manchester City", "Brighton & Hove Albion", "Bournemouth", "Aston Villa",
        "Fulham", "Crystal Palace", "Sunderland", "Brentford",
        "Liverpool", "Chelsea", "Everton", "Newcastle United",
    }
    none_bucket = carabao_wins.pop(None, 0)
    if none_bucket:
        print(f"  WARNING: {none_bucket} sims returned no Carabao winner "
              f"(={none_bucket / total * 100:.2f}%) — investigate _simulate_carabao/run_carabao_tournament")
    carabao_sorted = sorted(r4_teams, key=lambda t: -carabao_wins.get(t, 0))
    carabao_rows = [[team, "{:.2f}%".format(carabao_wins.get(team, 0) / total * 100.0)]
                    for team in carabao_sorted]
    print_table(["Team", "%"], carabao_rows, aligns=["l", "r"])
    print("\n  P(the Carabao Cup winner is a Premier League team): {:.2f}%"
          .format(carabao_pl_winner_count / total * 100.0))
    print("  P(the Carabao Cup winner is a non-PL EFL club): {:.2f}%"
          .format(carabao_nonpl_winner_count / total * 100.0))
    print("\n" + "=" * 80)
    print("FA CUP WIN PROBABILITY (simulated bracket from R1)")
    print("=" * 80)
    none_bucket = fa_cup_wins.pop(None, 0)
    if none_bucket:
        print(f"  WARNING: {none_bucket} sims returned no FA Cup winner "
              f"(={none_bucket / total * 100:.2f}%) — investigate _simulate_fa_cup/simulate_fa_cup")
    fa_sorted = sorted(((team, count) for team, count in fa_cup_wins.items() if count > 0),
                       key=lambda x: -x[1])
    if fa_sorted:
        fa_rows = [[team, "{:.2f}%".format(count / total * 100.0)] for team, count in fa_sorted]
        print_table(["Team", "%"], fa_rows, aligns=["l", "r"])
    pl_fa_total = sum(v for t, v in fa_cup_wins.items() if t in pl_teams_set)
    print("\n  P(a PL team wins the FA Cup): {:.2f}%"
          .format(pl_fa_total / total * 100.0))
    if manutd_streaks:
        avg = sum(manutd_streaks) / len(manutd_streaks)
        print("\n" + "=" * 80)
        print("MAN UNITED 5-GAME WINNING STREAK (Premier League only)")
        print("=" * 80)
        print("  Average longest W streak:   {:.2f}".format(avg))
        print("  P(>=5 consecutive wins):     {:.2f}%".format(manutd_5plus / total * 100.0))
        print("  Max streak across all sims: {}".format(manutd_streak_max))
    if MAN_CITY_DEDUCTION_ENABLED and man_city_penalties:
        buckets, n_total, n_expel = _compute_penalty_dist(man_city_penalties)
        print("\n" + "=" * 80)
        print("MAN CITY POINTS DEDUCTION DISTRIBUTION")
        print("=" * 80)
        penalty_rows = []
        for k, v in buckets.items():
            penalty_rows.append(["{} pts".format(k), "{:.2f}%".format(v / n_total * 100.0)])
        penalty_rows.append(["Expelled", "{:.2f}%".format(n_expel / n_total * 100.0)])
        print_table(["Outcome", "%"], penalty_rows, aligns=["l", "r"])


# =============================================================================
# DASHBOARD ENTRY POINT
# =============================================================================
def run_simulation(n_sims=NUM_PL_SIMS, seed=None, on_progress=None, is_running=None,
                   snapshot_callback=None, snapshot_every=None, s=None):
    if s is None:
        s = _shared_setup(seed=seed)
    pl_teams = s['pl_teams']
    pl_elos = s['pl_elos']
    pl_attack = s['pl_attack']
    pl_defense = s['pl_defense']
    sim_seed = s['seed']
    points_dist = {t: [] for t in pl_teams}
    position_counts = {t: defaultdict(int) for t in pl_teams}
    title_counts = defaultdict(int)
    ucl_qual_counts = defaultdict(int)
    uel_qual_counts = defaultdict(int)
    uecl_qual_counts = defaultdict(int)
    relegation_counts = defaultdict(int)
    euro_positions = {c: defaultdict(lambda: defaultdict(int)) for c in _EURO_COMPS}
    sack_prob_accum = defaultdict(float)
    sack_any_accum  = defaultdict(float)
    man_city_penalties = []
    euro_reach_r16   = {c: defaultdict(int) for c in _EURO_COMPS}
    euro_reach_qf    = {c: defaultdict(int) for c in _EURO_COMPS}
    euro_reach_sf    = {c: defaultdict(int) for c in _EURO_COMPS}
    euro_reach_final = {c: defaultdict(int) for c in _EURO_COMPS}
    euro_wins        = {c: defaultdict(int) for c in _EURO_COMPS}
    carabao_pl_winner_count = 0
    carabao_wins = defaultdict(int)
    carabao_nonpl_winner_count = 0
    fa_cup_wins = defaultdict(int)
    english_three_comp = 0
    eps_earned = 0
    fifth_place_ucl = 0
    england_coeff_accum = []
    assoc_coeff_accum = defaultdict(list)
    assoc_top2_count = defaultdict(int)
    manutd_streaks = []
    manutd_5plus = 0
    manutd_streak_max = 0
    pl_ucl_spots, pl_uel_spots, pl_uecl_spots, pl_total_spots = [], [], [], []
    pl_ucl_min, pl_ucl_max = 10 ** 9, 0
    pl_uel_min, pl_uel_max = 10 ** 9, 0
    pl_uecl_min, pl_uecl_max = 10 ** 9, 0
    pl_total_min, pl_total_max = 10 ** 9, 0
    rel_line_pts_accum = 0.0   # pts of 17th-placed (first relegated) team per sim
    safety_line_pts_accum = 0.0  # pts of 16th-placed (last safe) team per sim
    euro_win_counts = {c: defaultdict(int) for c in _EURO_COMPS}
    euro_points = {c: defaultdict(list) for c in _EURO_COMPS}
    if snapshot_every is None:
        snapshot_every = max(1, n_sims // 250)
    total_expected_firings = 0.0
    completed = 0
    for sim_i in range(n_sims):
        if is_running is not None and not is_running():
            break
        res = _run_one_sim(s, sim_i, sim_seed)
        ucl_res = res['ucl_res']
        uel_res = res['uel_res']
        uecl_res = res['uecl_res']
        ranking = res['ranking']
        points = res['points']
        risks = res['risks']
        tot_risk = res['tot_risk']
        carabao_winner = res['carabao_winner']
        fa_cup_winner = res['fa_cup_winner']
        coeffs = res['coeffs']
        ranked = res['ranked_coeffs']
        top2 = res['top2']
        has_eps = res['has_eps']
        spots = res['spots']
        man_city_penalties.append(res['man_city_penalty'])
        _reach_stores = (euro_reach_r16, euro_reach_qf, euro_reach_sf, euro_reach_final, euro_wins)
        for comp_name, r in (("UCL", ucl_res), ("UEL", uel_res), ("UECL", uecl_res)):
            _accumulate_euro_results(r, comp_name, euro_positions, euro_points, _reach_stores)
        total_expected_firings += _accumulate_sack_risk(risks, tot_risk, sack_prob_accum, sack_any_accum)
        for t in spots["UCL"]: ucl_qual_counts[t] += 1
        for t in spots["UEL"]: uel_qual_counts[t] += 1
        for t in spots["UECL"]: uecl_qual_counts[t] += 1
        for pos, team in enumerate(ranking):
            points_dist[team].append(points[team])
            position_counts[team][pos + 1] += 1
            if pos == 0: title_counts[team] += 1
            if pos >= 18: relegation_counts[team] += 1
            if pos == 17:
                rel_line_pts_accum += points[team]
            if pos == 16:
                safety_line_pts_accum += points[team]
        if "Man United" in pl_teams:
            mr = res.get('manu_results', [])
            st = max_consecutive_wins(mr)
            manutd_streaks.append(st)
            if st >= 5:
                manutd_5plus += 1
            if st > manutd_streak_max:
                manutd_streak_max = st
        if has_eps:
            eps_earned += 1
        if has_eps and len(ranking) > 4:
            fifth = ranking[4]
            non_eps_ucl = set(ranking[:4]) | {ucl_res.winner, uel_res.winner}
            non_eps_ucl.discard(None)
            if fifth in spots["UCL"] and fifth not in non_eps_ucl:
                fifth_place_ucl += 1
        england_coeff_accum.append(coeffs.get("England", 0.0))
        for assoc, coeff in ranked[:8]:
            assoc_coeff_accum[assoc].append(coeff)
            if assoc in top2:
                assoc_top2_count[assoc] += 1
        if (ucl_res.winner and uel_res.winner and uecl_res.winner
                and all(w in pl_teams for w in (ucl_res.winner, uel_res.winner, uecl_res.winner))):
            english_three_comp += 1
        ucl_n = len(spots["UCL"]); uel_n = len(spots["UEL"]); uecl_n = len(spots["UECL"])
        pl_ucl_spots.append(ucl_n); pl_uel_spots.append(uel_n)
        pl_uecl_spots.append(uecl_n); pl_total_spots.append(ucl_n + uel_n + uecl_n)
        pl_ucl_min = min(pl_ucl_min, ucl_n); pl_ucl_max = max(pl_ucl_max, ucl_n)
        pl_uel_min = min(pl_uel_min, uel_n); pl_uel_max = max(pl_uel_max, uel_n)
        pl_uecl_min = min(pl_uecl_min, uecl_n); pl_uecl_max = max(pl_uecl_max, uecl_n)
        pl_total_min = min(pl_total_min, ucl_n + uel_n + uecl_n)
        pl_total_max = max(pl_total_max, ucl_n + uel_n + uecl_n)
        carabao_wins[carabao_winner] += 1
        if carabao_name_map(carabao_winner) in pl_teams:
            carabao_pl_winner_count += 1
        else:
            carabao_nonpl_winner_count += 1
        fa_cup_wins[fa_cup_winner] += 1
        for comp, w in (("UCL", ucl_res.winner), ("UEL", uel_res.winner), ("UECL", uecl_res.winner)):
            if w and w in pl_teams:
                euro_win_counts[comp][w] += 1
        completed += 1
        if on_progress is not None:
            on_progress(completed, n_sims)
        if snapshot_callback is not None and (completed % snapshot_every == 0 or completed == n_sims):
            snapshot_callback(completed, n_sims, {
                "avg_positions": {t: sum(p * c for p, c in position_counts[t].items()) / completed
                                  for t in pl_teams},
                "avg_points":      {t: sum(points_dist[t]) / completed for t in pl_teams},
                "title_prob":      {t: title_counts.get(t, 0)      / completed * 100 for t in pl_teams},
                "ucl_qual_prob":   {t: ucl_qual_counts.get(t, 0)   / completed * 100 for t in pl_teams},
                "uel_qual_prob":   {t: uel_qual_counts.get(t, 0)   / completed * 100 for t in pl_teams},
                "uecl_qual_prob":  {t: uecl_qual_counts.get(t, 0)  / completed * 100 for t in pl_teams},
                "total_euro_prob": {t: (ucl_qual_counts.get(t, 0) + uel_qual_counts.get(t, 0) + uecl_qual_counts.get(t, 0)) / completed * 100 for t in pl_teams},
                "relegation_prob": {t: relegation_counts.get(t, 0) / completed * 100 for t in pl_teams},
                "sack_prob":     {t: sack_prob_accum[t] / completed * 100 for t in pl_teams},
                "sack_any_prob": {t: sack_any_accum[t]  / completed * 100 for t in pl_teams},
                "avg_firings_per_season": (
                    total_expected_firings / completed if completed else 0.0
                ),
                "rel_line_avg_pts": rel_line_pts_accum / completed if completed else 0.0,
                "safety_line_avg_pts": safety_line_pts_accum / completed if completed else 0.0,
            })
    n = completed or 1
    avg_firings = total_expected_firings / n
    rel_line_avg_pts = rel_line_pts_accum / n
    safety_line_avg_pts = safety_line_pts_accum / n
    euro_solved = {}
    euro_solved_avg = {}
    for comp_name in _EURO_COMPS:
        pos_map = euro_positions[comp_name]
        teams_in_comp = sorted(
            pos_map.keys(),
            key=lambda t: sum(p * c for p, c in pos_map[t].items())
                          / max(1, sum(pos_map[t].values())))
        avg_pct, solved_pct, _ = solved_metric(pos_map, teams_in_comp, n)
        euro_solved[comp_name] = solved_pct        # joint product ("actually solved")
        euro_solved_avg[comp_name] = avg_pct        # mean assigned prob ("solved", league method)
    if all(v > 0.0 for v in euro_solved.values()):
        # Unified UEFA "actually solved": product of all assigned probabilities
        # across all three competitions (UCL product × UEL product × UECL product),
        # mirroring the league's "product of all assigned probs" line.
        unified_euro_solved = (
            euro_solved["UCL"] * euro_solved["UEL"] * euro_solved["UECL"])
    else:
        unified_euro_solved = 0.0
    # Unified UEFA "solved" using the same method as the league table:
    # arithmetic mean of the assigned probabilities (all three comps weighted equally;
    # each comp has the same number of league-phase positions, so this equals the
    # mean assigned prob across every UEFA league-phase slot).  Replaces the
    # geometric-mean-of-products value that collapsed to 0.000000%.
    unified_euro_solved_avg = (
        sum(euro_solved_avg.values()) / len(euro_solved_avg) if euro_solved_avg else 0.0)
    man_city_penalty_dist = None
    if MAN_CITY_DEDUCTION_ENABLED and man_city_penalties:
        buckets, n_total, n_expel = _compute_penalty_dist(man_city_penalties)
        man_city_penalty_dist = {k: v / n_total * 100.0 for k, v in buckets.items()}
        man_city_penalty_dist["Expelled"] = n_expel / n_total * 100.0
    return {
        "n_sims": completed,
        "pl_teams_set": pl_teams,
        "points_dist_raw": points_dist,
        "position_counts_raw": position_counts,
        "title_counts_raw": title_counts,
        "relegation_counts_raw": relegation_counts,
        "ucl_qual_counts_raw": ucl_qual_counts,
        "uel_qual_counts_raw": uel_qual_counts,
        "uecl_qual_counts_raw": uecl_qual_counts,
        "euro_positions_raw": euro_positions,
        "euro_points_raw": euro_points,
        "euro_reach": {
            c: {
                "r16": euro_reach_r16[c],
                "qf": euro_reach_qf[c],
                "sf": euro_reach_sf[c],
                "final": euro_reach_final[c],
            }
            for c in ("UCL", "UEL", "UECL")
        },
        "euro_wins_raw": euro_wins,
        "euro_win_counts_raw": euro_win_counts,
        "sack_prob_raw": sack_prob_accum,
        "sack_any_prob_raw": sack_any_accum,
        "man_city_penalties": man_city_penalties,
        "avg_points":      {t: sum(points_dist[t]) / n for t in pl_teams},
        "avg_positions":   {t: sum(p * c for p, c in position_counts[t].items()) / n
                            for t in pl_teams},
        "title_prob":      {t: title_counts.get(t, 0)      / n * 100 for t in pl_teams},
        "ucl_qual_prob":   {t: ucl_qual_counts.get(t, 0)   / n * 100 for t in pl_teams},
        "uel_qual_prob":   {t: uel_qual_counts.get(t, 0)   / n * 100 for t in pl_teams},
        "uecl_qual_prob":  {t: uecl_qual_counts.get(t, 0)  / n * 100 for t in pl_teams},
        "total_euro_prob": {t: (ucl_qual_counts.get(t, 0) + uel_qual_counts.get(t, 0) + uecl_qual_counts.get(t, 0)) / n * 100 for t in pl_teams},
        "relegation_prob": {t: relegation_counts.get(t, 0) / n * 100 for t in pl_teams},
        "euro_solved":             euro_solved,
        "unified_euro_solved":     unified_euro_solved,
        "euro_solved_avg":         euro_solved_avg,
        "unified_euro_solved_avg": unified_euro_solved_avg,
        "sack_prob":     {t: sack_prob_accum[t] / n * 100 for t in pl_teams},
        "sack_any_prob": {t: sack_any_accum[t] / n * 100 for t in pl_teams},
        "avg_firings_per_season": avg_firings,
        "rel_line_avg_pts": rel_line_avg_pts,
        "safety_line_avg_pts": safety_line_avg_pts,
        "man_city_penalty_dist": man_city_penalty_dist,
        "euro_reach_r16":   {c: {t: euro_reach_r16[c].get(t, 0)   / n * 100 for t in euro_positions[c]}
                             for c in ("UCL", "UEL", "UECL")},
        "euro_reach_qf":    {c: {t: euro_reach_qf[c].get(t, 0)    / n * 100 for t in euro_positions[c]}
                             for c in ("UCL", "UEL", "UECL")},
        "euro_reach_sf":    {c: {t: euro_reach_sf[c].get(t, 0)    / n * 100 for t in euro_positions[c]}
                             for c in ("UCL", "UEL", "UECL")},
        "euro_reach_final": {c: {t: euro_reach_final[c].get(t, 0) / n * 100 for t in euro_positions[c]}
                             for c in ("UCL", "UEL", "UECL")},
        "euro_win_comp":    {c: {t: euro_wins[c].get(t, 0)        / n * 100 for t in euro_positions[c]}
                              for c in ("UCL", "UEL", "UECL")},
        "carabao_pl_winner_count": carabao_pl_winner_count,
        "carabao_nonpl_winner_count": carabao_nonpl_winner_count,
        "carabao_wins_raw": carabao_wins,
        "carabao_nonpl_winner_pct": carabao_nonpl_winner_count / n * 100.0,
        "carabao_wins_pct": {t: c / n * 100.0 for t, c in carabao_wins.items()},
        "fa_cup_wins_raw": fa_cup_wins,
        "fa_cup_wins_pct": {t: c / n * 100.0 for t, c in fa_cup_wins.items()},
        "fa_cup_pl_total_pct": sum(v for t, v in fa_cup_wins.items() if t in pl_teams) / n * 100.0,
        "manutd_streaks":      manutd_streaks,
        "manutd_5plus":        manutd_5plus,
        "manutd_avg_longest_streak": sum(manutd_streaks) / len(manutd_streaks) if manutd_streaks else 0.0,
        "manutd_5plus_pct":    manutd_5plus / n * 100.0,
        "manutd_streak_max":   manutd_streak_max,
        "eps_earned":          eps_earned,
        "eps_earned_pct":      eps_earned / n * 100.0,
        "fifth_place_ucl":     fifth_place_ucl,
        "fifth_place_ucl_pct": fifth_place_ucl / n * 100.0,
        "english_three_comp":  english_three_comp,
        "english_three_comp_pct": english_three_comp / n * 100.0,
        "england_coeff_accum":   england_coeff_accum,
        "england_coeff_avg":     sum(england_coeff_accum) / len(england_coeff_accum) if england_coeff_accum else 0.0,
        "assoc_coeff_accum":     {k: v for k, v in assoc_coeff_accum.items()},
        "assoc_top2_count":      {k: v for k, v in assoc_top2_count.items()},
        "pl_ucl_spots": pl_ucl_spots,
        "pl_uel_spots": pl_uel_spots,
        "pl_uecl_spots": pl_uecl_spots,
        "pl_total_spots": pl_total_spots,
        "pl_ucl_spots_avg": sum(pl_ucl_spots) / n,
        "pl_uel_spots_avg": sum(pl_uel_spots) / n,
        "pl_uecl_spots_avg": sum(pl_uecl_spots) / n,
        "pl_total_spots_avg": sum(pl_total_spots) / n,
        "pl_ucl_min": pl_ucl_min,
        "pl_ucl_max": pl_ucl_max,
        "pl_uel_min": pl_uel_min,
        "pl_uel_max": pl_uel_max,
        "pl_uecl_min": pl_uecl_min,
        "pl_uecl_max": pl_uecl_max,
        "pl_total_min": pl_total_min,
        "pl_total_max": pl_total_max,
        "spot_dist": {
            "UCL": spot_pct_map(pl_ucl_spots),
            "UEL": spot_pct_map(pl_uel_spots),
            "UECL": spot_pct_map(pl_uecl_spots),
            "Total": spot_pct_map(pl_total_spots),
        },
        "pl_elos":       dict(pl_elos),
        "pl_attack":     dict(pl_attack),
        "pl_defense":    dict(pl_defense),
        "manager_info":  {t: (MANAGER_DATA.get(t, ("Unknown", "", 10, 1.0))[0],
                               MANAGER_DATA.get(t, ("Unknown", "", 10, 1.0))[1])
                           for t in pl_teams},
    }


if __name__ == "__main__":
    main()