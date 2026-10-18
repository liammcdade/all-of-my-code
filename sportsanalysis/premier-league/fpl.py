"""
chart_generator.py

Loads the 2026/27 season simulation module, runs the unified simulation,
and writes 1280x720 (16:9) infographic-style PNGs matching the reference
image (dark-green background, yellow / teal / cream accents).

Produces 25 charts:

   01  average_european_spots      hero card  (UCL / UEL / UECL / total)
   02  title_race                  PL title probability
   03  ucl_qualification           UCL qualification probability
   04  uel_qualification           UEL qualification probability
   05  uecl_qualification          UECL qualification probability
   06  european_qualification      Any European qualification
   07  european_win_chances        P(a PL club wins UCL/UEL/UECL)
   08  points_thresholds           Avg points needed for each outcome
   09  carabao_cup                 Carabao Cup win probability
   10  fa_cup                      FA Cup win probability
   11  coefficient_top2            UEFA coefficient Top-2 race
   12  eps_card                    England EPS hero card
   13  relegation                  Relegation probability
   14  avg_points                  Average points by team
   15  avg_finish_position         Average finishing position (lower = better)
   16  median_position             Median finishing position
   17  manutd_streak               Man United 5-game win streak tracker
   18  assoc_coefficients          Average association coefficients
   19  england_coeff_range         England coefficient p10/avg/p90
   20  ucl_league_top8             UCL league-phase Top-8 finish probability
   21  uel_league_top8             UEL league-phase Top-8 finish probability
   22  uecl_league_top8            UECL league-phase Top-8 finish probability
   23  pl_club_europe_win          P(each PL club wins each UEFA trophy)
   24  pl_elo_ratings              Elo ratings of PL clubs
   25  ucl_winner_by_pl_club       UCL win probability per PL club
"""

from __future__ import annotations

import importlib.util
import os
import sys
import traceback
from typing import Any, Callable, Dict, List, Optional, Sequence, Tuple

import numpy as np
import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import Rectangle


# =============================================================================
# CONFIG
# =============================================================================

SIM_PATH = r"C:\Users\liam\Documents\GitHub\all-of-my-code\sportsanalysis\premier-league\26-27-season.py"
OUT_DIR  = r"C:\Users\liam\Documents\GitHub\all-of-my-code\sportsanalysis\premier-league\charts"

N_SIMS = 1000

# =============================================================================
# CANVAS — 1280 x 720 px @ 100 DPI = 16:9
# =============================================================================

DPI     = 100
FIG_W   = 12.8    # inches  -> 1280 px
FIG_H   = 7.2     # inches  ->  720 px
FIGSIZE = (FIG_W, FIG_H)

# =============================================================================
# PALETTE & STYLE
# =============================================================================

BG     = "#1e3329"
BG_ALT = "#2a4235"
CREAM  = "#f5f0e6"
YELLOW = "#f0b93c"
TEAL   = "#4dbfa8"
LIGHT  = "#c4d4ce"
MUTED  = "#8ba39a"
RED    = "#d4685a"

FONT_FAMILY = "DejaVu Sans"
plt.rcParams["font.family"] = FONT_FAMILY
plt.rcParams["font.sans-serif"] = [FONT_FAMILY, "DejaVu Sans"]


# =============================================================================
# LOW-LEVEL HELPERS
# =============================================================================

def _new_fig():
    fig = plt.figure(figsize=FIGSIZE, facecolor=BG)
    ax = fig.add_axes([0, 0, 1, 1])
    ax.set_facecolor(BG)
    ax.set_xlim(0, 1)
    ax.set_ylim(0, 1)
    ax.axis("off")
    return fig, ax


def _save(fig, path: str) -> None:
    os.makedirs(os.path.dirname(path) or ".", exist_ok=True)
    fig.savefig(path, facecolor=BG, dpi=DPI)
    plt.close(fig)
    print(f"  wrote {path}")


def _clear_pngs(out_dir: str) -> int:
    """Delete every .png in out_dir. Returns the number removed."""
    if not os.path.isdir(out_dir):
        return 0
    removed = 0
    for name in os.listdir(out_dir):
        if name.lower().endswith(".png"):
            full = os.path.join(out_dir, name)
            if os.path.isfile(full):
                try:
                    os.remove(full)
                    removed += 1
                except OSError as exc:
                    print(f"  WARNING: could not remove {full}: {exc}",
                          file=sys.stderr)
    return removed


def _title_block(ax, eyebrow: str, title: str,
                 eyebrow_y: float = 0.94,
                 title_y: float = 0.88,
                 title_size: int = 26) -> None:
    ax.text(0.05, eyebrow_y, eyebrow, fontsize=10, color=MUTED,
            va="top", ha="left")
    ax.text(0.05, title_y, title, fontsize=title_size, color=CREAM,
            va="top", ha="left", fontweight="bold", linespacing=1.05)


# =============================================================================
# CHART TYPE 1 — hero card (big number + stacked bar)
# =============================================================================

def draw_hero_card(
    path: str,
    eyebrow: str,
    title: str,
    big_value: str,
    caption: str,
    segments: Sequence[Tuple[float, str, str, str, str]],
) -> None:
    fig, ax = _new_fig()

    # Header
    ax.text(0.05, 0.94, eyebrow, fontsize=11, color=MUTED,
            va="top", ha="left")
    ax.text(0.05, 0.875, title, fontsize=44, color=CREAM,
            va="top", ha="left", fontweight="bold", linespacing=1.05)

    # Big number on the left, caption to its right
    ax.text(0.05, 0.46, big_value, fontsize=140, color=YELLOW,
            va="center", ha="left", fontweight="bold")
    ax.text(0.60, 0.40, caption, fontsize=13, color=CREAM,
            va="center", ha="left")

    # Stacked horizontal bar
    bar_x0, bar_x1 = 0.05, 0.95
    bar_y, bar_h = 0.20, 0.036
    bar_w = bar_x1 - bar_x0
    total = sum(s[0] for s in segments) or 1.0

    x = bar_x0
    starts: List[float] = []
    for val, _, _, _, color in segments:
        w = bar_w * (val / total)
        starts.append(x)
        ax.add_patch(Rectangle((x, bar_y), w, bar_h,
                               facecolor=color, edgecolor="none"))
        x += w

    # Legend under each segment start
    for (val, num_txt, tag, sub, color), lx in zip(segments, starts):
        ax.text(lx, 0.135, num_txt, fontsize=26, color=color,
                va="center", ha="left", fontweight="bold")
        ax.text(lx, 0.095, tag, fontsize=12, color=CREAM,
                va="center", ha="left", fontweight="bold")
        ax.text(lx, 0.065, sub, fontsize=9, color=MUTED,
                va="center", ha="left")

    _save(fig, path)


# =============================================================================
# CHART TYPE 2 — horizontal bars
# =============================================================================

def draw_horizontal_bars(
    path: str,
    eyebrow: str,
    title: str,
    items: Sequence[Tuple[str, float]],
    value_fmt: str = "{:.2f}%",
    bar_color: Any = YELLOW,
    max_bars: Optional[int] = None,
    label_w: float = 0.30,
    bar_value_fn: Optional[Callable[[float], float]] = None,
    label_fmt: Optional[str] = None,
    title_size: int = 24,
) -> None:
    """
    Horizontal bars.

    items         : sequence of (label, value)
    bar_value_fn  : optional transform used only for the bar *length*
                    (value shown in text is still the raw value).
    label_fmt     : optional format string for the label (e.g. "{:<20}").
    """
    items = list(items)
    if max_bars:
        items = items[:max_bars]
    if not items:
        return

    fig, ax = _new_fig()
    _title_block(ax, eyebrow, title, title_size=title_size)

    n = len(items)
    top = 0.80
    bottom = 0.05
    row_h = (top - bottom) / n

    bar_x = 0.05 + label_w + 0.01
    bar_max_w = 0.95 - bar_x - 0.08

    raw_values = [v for _, v in items]
    display_values = (raw_values if bar_value_fn is None
                      else [bar_value_fn(v) for v in raw_values])
    max_v = max(display_values, default=1.0) or 1.0

    if isinstance(bar_color, (list, tuple, np.ndarray)):
        colors = list(bar_color)
        if len(colors) < n:
            colors = (colors * n)[:n]
    else:
        colors = [bar_color] * n

    # Auto font sizing for long tables.
    row_fs = 10 if n <= 15 else (9 if n <= 20 else 8)
    label_fmt = label_fmt or "{:<24}"

    for i, (label, value) in enumerate(items):
        y = top - (i + 0.5) * row_h
        ax.text(0.05, y, label_fmt.format(label),
                fontsize=row_fs, color=CREAM, va="center", ha="left")
        h = row_h * 0.55
        w = bar_max_w * (display_values[i] / max_v)
        ax.add_patch(Rectangle((bar_x, y - h / 2.0), w, h,
                               facecolor=colors[i], edgecolor="none"))
        ax.text(bar_x + w + 0.008, y,
                value_fmt.format(value),
                fontsize=row_fs, color=CREAM,
                va="center", ha="left", fontweight="bold")

    _save(fig, path)


# =============================================================================
# CHART TYPE 3 — three big numbers
# =============================================================================

def draw_three_stats(
    path: str,
    eyebrow: str,
    title: str,
    items: Sequence[Tuple[str, str, str, str]],
) -> None:
    fig, ax = _new_fig()
    _title_block(ax, eyebrow, title, title_size=32, title_y=0.85)

    n = len(items)
    col_w = 0.90 / max(n, 1)

    for i, (tag, name, val_s, color) in enumerate(items):
        x = 0.05 + i * col_w
        ax.text(x, 0.52, tag, fontsize=15, color=MUTED,
                va="center", ha="left", fontweight="bold")
        ax.text(x, 0.46, name, fontsize=12, color=CREAM,
                va="center", ha="left")
        ax.text(x, 0.26, val_s, fontsize=72, color=color,
                va="center", ha="left", fontweight="bold")

    _save(fig, path)


# =============================================================================
# LOAD THE SIMULATION MODULE
# =============================================================================

def load_sim_module(path: str):
    spec = importlib.util.spec_from_file_location("season_26_27", path)
    if spec is None or spec.loader is None:
        raise ImportError(f"Cannot load module from {path}")
    module = importlib.util.module_from_spec(spec)
    sys.modules["season_26_27"] = module
    spec.loader.exec_module(module)
    return module


# =============================================================================
# NAME CLEANUPS
# =============================================================================

_CARABAO_SHORT = {
    "Manchester City": "Man City",
    "Brighton & Hove Albion": "Brighton",
    "Newcastle United": "Newcastle",
    "Bradford City": "Bradford",
    "Peterborough United": "Peterboro",
    "Fleetwood Town": "Fleetwood",
}


def _short(name: str) -> str:
    return _CARABAO_SHORT.get(name, name)


# =============================================================================
# SMALL HELPERS FOR CHART DATA PREP
# =============================================================================

def _sorted_desc(d: Dict[str, float], teams: Optional[Sequence[str]] = None,
                 top: Optional[int] = None) -> List[Tuple[str, float]]:
    src = teams if teams is not None else d.keys()
    rows = sorted(((t, d[t]) for t in src), key=lambda x: -x[1])
    return rows[:top] if top else rows


def _top_n_league_probability(euro_positions_comp: Dict[str, Dict[int, int]],
                              n_sims: int,
                              lo: int = 1, hi: int = 8,
                              top: Optional[int] = None
                              ) -> List[Tuple[str, float]]:
    """Chance a team finishes in league-phase positions [lo, hi]."""
    rows: List[Tuple[str, float]] = []
    for team, pos_counts in euro_positions_comp.items():
        c = sum(v for p, v in pos_counts.items() if lo <= p <= hi)
        rows.append((team, c / max(1, n_sims) * 100.0))
    rows.sort(key=lambda x: -x[1])
    return rows[:top] if top else rows


# =============================================================================
# BUILD ALL CHARTS
# =============================================================================

def make_all_charts(r: Dict[str, Any], out_dir: str) -> None:
    os.makedirs(out_dir, exist_ok=True)
    print(f"\nWriting 1280x720 charts to {out_dir}\n")

    teams = r["pl_teams_set"]
    n_sims = r["n_sims"]

    # =========================================================================
    # 01 — Hero card: average European spots
    # =========================================================================
    ucl_s  = r["avg_pl_ucl_spots"]
    uel_s  = r["avg_pl_uel_spots"]
    uecl_s = r["avg_pl_uecl_spots"]
    tot_s  = r["avg_pl_total_spots"]

    draw_hero_card(
        path=os.path.join(out_dir, "01_average_european_spots.png"),
        eyebrow="PREMIER LEAGUE · AVERAGE PER SEASON",
        title="Average European spots",
        big_value=f"{tot_s:.2f}",
        caption="total European spots",
        segments=[
            (ucl_s,  f"{ucl_s:.2f}",  "UCL",  "Champions League",  YELLOW),
            (uel_s,  f"{uel_s:.2f}",  "UEL",  "Europa League",     TEAL),
            (uecl_s, f"{uecl_s:.2f}", "UECL", "Conference League", LIGHT),
        ],
    )

    # =========================================================================
    # 02 — Title race
    # =========================================================================
    draw_horizontal_bars(
        path=os.path.join(out_dir, "02_title_race.png"),
        eyebrow="PREMIER LEAGUE · 2026/27",
        title="Title probability",
        items=_sorted_desc(r["title_prob"], teams, top=10),
        bar_color=YELLOW,
    )

    # =========================================================================
    # 03 — UCL qualification
    # =========================================================================
    draw_horizontal_bars(
        path=os.path.join(out_dir, "03_ucl_qualification.png"),
        eyebrow="PREMIER LEAGUE · 2026/27",
        title="Champions League qualification probability",
        items=_sorted_desc(r["ucl_qual_prob"], teams, top=14),
        bar_color=YELLOW,
    )

    # =========================================================================
    # 04 — UEL qualification
    # =========================================================================
    draw_horizontal_bars(
        path=os.path.join(out_dir, "04_uel_qualification.png"),
        eyebrow="PREMIER LEAGUE · 2026/27",
        title="Europa League qualification probability",
        items=_sorted_desc(r["uel_qual_prob"], teams, top=14),
        bar_color=TEAL,
    )

    # =========================================================================
    # 05 — UECL qualification
    # =========================================================================
    draw_horizontal_bars(
        path=os.path.join(out_dir, "05_uecl_qualification.png"),
        eyebrow="PREMIER LEAGUE · 2026/27",
        title="Conference League qualification probability",
        items=_sorted_desc(r["uecl_qual_prob"], teams, top=14),
        bar_color=LIGHT,
    )

    # =========================================================================
    # 06 — Any European qualification
    # =========================================================================
    euro_items = sorted(
        ((t, r["ucl_qual_prob"][t] + r["uel_qual_prob"][t] + r["uecl_qual_prob"][t])
         for t in teams),
        key=lambda x: -x[1],
    )[:16]
    draw_horizontal_bars(
        path=os.path.join(out_dir, "06_european_qualification.png"),
        eyebrow="PREMIER LEAGUE · 2026/27",
        title="Any European qualification probability",
        items=euro_items,
        bar_color=TEAL,
    )

    # =========================================================================
    # 07 — European win chances
    # =========================================================================
    draw_three_stats(
        path=os.path.join(out_dir, "07_european_win_chances.png"),
        eyebrow="PL CLUBS · CONTINENTAL SILVERWARE",
        title="Chance a PL team wins",
        items=[
            ("UCL",  "Champions League",  f"{r['pl_ucl_win_prob']:.2f}%",  YELLOW),
            ("UEL",  "Europa League",     f"{r['pl_uel_win_prob']:.2f}%",  TEAL),
            ("UECL", "Conference League", f"{r['pl_uecl_win_prob']:.2f}%", LIGHT),
        ],
    )

    # =========================================================================
    # 08 — Points thresholds
    # =========================================================================
    thresholds = [
        ("Premier League title",  r["avg_title_points"]),
        ("Champions League",      r["avg_ucl_qual_points"]),
        ("Europa League",         r["avg_uel_qual_points"]),
        ("Conference League",     r["avg_uecl_qual_points"]),
        ("Avoid relegation",      r["avg_avoid_relegation_points"]),
    ]
    draw_horizontal_bars(
        path=os.path.join(out_dir, "08_points_thresholds.png"),
        eyebrow="PREMIER LEAGUE · SEASON PROJECTION",
        title="Average points needed",
        items=thresholds,
        value_fmt="{:.2f}",
        bar_color=[YELLOW, YELLOW, TEAL, TEAL, LIGHT],
        label_w=0.36,
    )

    # =========================================================================
    # 09 — Carabao Cup
    # =========================================================================
    carabao_rows = sorted(
        ((_short(t), cnt / n_sims * 100.0)
         for t, cnt in r["carabao_win_counts"].items()),
        key=lambda x: -x[1],
    )
    draw_horizontal_bars(
        path=os.path.join(out_dir, "09_carabao_cup.png"),
        eyebrow="CARABAO CUP · 2026/27",
        title="Win probability",
        items=carabao_rows,
        bar_color=YELLOW,
        label_w=0.34,
        max_bars=15,
    )

    # =========================================================================
    # 10 — FA Cup
    # =========================================================================
    fa_cup_rows = sorted(
        ((t, cnt / n_sims * 100.0)
         for t, cnt in r["fa_cup_win_counts"].items()),
        key=lambda x: -x[1],
    )[:20]
    draw_horizontal_bars(
        path=os.path.join(out_dir, "10_fa_cup.png"),
        eyebrow="FA CUP · 2026/27",
        title="Win probability",
        items=fa_cup_rows,
        bar_color=LIGHT,
        label_w=0.32,
    )

    # =========================================================================
    # 11 — Coefficient Top-2 race
    # =========================================================================
    assoc_rows = sorted(
        r["assoc_top2_prob"].items(),
        key=lambda x: -x[1],
    )[:14]
    draw_horizontal_bars(
        path=os.path.join(out_dir, "11_coefficient_top2.png"),
        eyebrow="UEFA COEFFICIENT · 2026/27",
        title="Chance of a Top-2 finish",
        items=assoc_rows,
        bar_color=TEAL,
        label_w=0.30,
    )

    # =========================================================================
    # 12 — EPS hero card
    # =========================================================================
    eps = r["eps_earned_prob"]
    draw_hero_card(
        path=os.path.join(out_dir, "12_eps_card.png"),
        eyebrow="EPS · EXTRA PERFORMANCE SPOT · 2027/28 UCL",
        title="England Top-2 coefficient",
        big_value=f"{eps:.1f}%",
        caption="chance the 5th PL side enters the UCL",
        segments=[
            (eps,         f"{eps:.1f}%",         "EPS",    "England Top 2", YELLOW),
            (100.0 - eps, f"{100.0 - eps:.1f}%", "NO EPS", "Outside Top 2", BG_ALT),
        ],
    )

    # =========================================================================
    # 13 — Relegation battle
    # =========================================================================
    draw_horizontal_bars(
        path=os.path.join(out_dir, "13_relegation.png"),
        eyebrow="PREMIER LEAGUE · 2026/27",
        title="Relegation probability",
        items=_sorted_desc(r["relegation_prob"], teams, top=10),
        bar_color=RED,
    )

    # =========================================================================
    # 14 — Average points by team
    # =========================================================================
    avg_pts_rows = sorted(
        ((t, r["avg_points"][t]) for t in teams),
        key=lambda x: -x[1],
    )
    draw_horizontal_bars(
        path=os.path.join(out_dir, "14_avg_points.png"),
        eyebrow="PREMIER LEAGUE · SEASON PROJECTION",
        title="Average points per season",
        items=avg_pts_rows,
        value_fmt="{:.2f}",
        bar_color=YELLOW,
        label_w=0.32,
    )

    # =========================================================================
    # 15 — Average finish position (lower is better → invert bar length)
    # =========================================================================
    pos_rows = sorted(
        ((t, r["avg_positions"][t]) for t in teams),
        key=lambda x: x[1],
    )
    draw_horizontal_bars(
        path=os.path.join(out_dir, "15_avg_finish_position.png"),
        eyebrow="PREMIER LEAGUE · SEASON PROJECTION",
        title="Average finishing position",
        items=pos_rows,
        value_fmt="{:.2f}",
        bar_color=TEAL,
        label_w=0.32,
        bar_value_fn=lambda v: 21.0 - v,
    )

    # =========================================================================
    # 16 — Median position
    # =========================================================================
    med_rows = sorted(
        ((t, float(r["median_positions"][t])) for t in teams),
        key=lambda x: x[1],
    )
    draw_horizontal_bars(
        path=os.path.join(out_dir, "16_median_position.png"),
        eyebrow="PREMIER LEAGUE · SEASON PROJECTION",
        title="Median finishing position",
        items=med_rows,
        value_fmt="{:.0f}",
        bar_color=LIGHT,
        label_w=0.32,
        bar_value_fn=lambda v: 21.0 - v,
    )

    # =========================================================================
    # 17 — Man United 5-game winning streak tracker
    # =========================================================================
    draw_three_stats(
        path=os.path.join(out_dir, "17_manutd_streak.png"),
        eyebrow="MAN UNITED · PL + UCL RESULT TRACKER",
        title="Longest winning streak",
        items=[
            ("AVG",     "Average streak",
             f"{r['manutd_streak_avg']:.2f}", TEAL),
            ("P(>=5)",  "Chance of 5+ wins in a row",
             f"{r['manutd_streak_5plus_prob']:.1f}%", YELLOW),
            ("MAX",     "Longest observed streak",
             f"{r['manutd_streak_max']}", CREAM),
        ],
    )

    # =========================================================================
    # 18 — Association average coefficients
    # =========================================================================
    assoc_avg_rows = sorted(
        ((a, c) for a, c in r.get("assoc_avg_coeff", {}).items()),
        key=lambda x: -x[1],
    )[:15]
    if assoc_avg_rows:
        draw_horizontal_bars(
            path=os.path.join(out_dir, "18_assoc_coefficients.png"),
            eyebrow="UEFA COEFFICIENT · SEASON AVERAGE",
            title="Association coefficient",
            items=assoc_avg_rows,
            value_fmt="{:.3f}",
            bar_color=TEAL,
            label_w=0.32,
        )

    # =========================================================================
    # 19 — England coefficient range
    # =========================================================================
    draw_three_stats(
        path=os.path.join(out_dir, "19_england_coeff_range.png"),
        eyebrow="ENGLAND · UEFA COEFFICIENT DISTRIBUTION",
        title="England coefficient spread",
        items=[
            ("P10", "10th percentile",
             f"{r['england_coeff_p10']:.3f}", LIGHT),
            ("AVG", "Average",
             f"{r['england_avg_coeff']:.3f}", YELLOW),
            ("P90", "90th percentile",
             f"{r['england_coeff_p90']:.3f}", TEAL),
        ],
    )

    # =========================================================================
    # 20 — UCL league-phase Top-8 probability
    # =========================================================================
    ucl_top8 = _top_n_league_probability(
        r["euro_league_positions"]["UCL"], n_sims, lo=1, hi=8, top=14)
    draw_horizontal_bars(
        path=os.path.join(out_dir, "20_ucl_league_top8.png"),
        eyebrow="UCL · LEAGUE PHASE",
        title="Chance of a Top-8 finish",
        items=ucl_top8,
        bar_color=YELLOW,
        label_w=0.32,
    )

    # =========================================================================
    # 21 — UEL league-phase Top-8 probability
    # =========================================================================
    uel_top8 = _top_n_league_probability(
        r["euro_league_positions"]["UEL"], n_sims, lo=1, hi=8, top=14)
    draw_horizontal_bars(
        path=os.path.join(out_dir, "21_uel_league_top8.png"),
        eyebrow="UEL · LEAGUE PHASE",
        title="Chance of a Top-8 finish",
        items=uel_top8,
        bar_color=TEAL,
        label_w=0.32,
    )

    # =========================================================================
    # 22 — UECL league-phase Top-8 probability
    # =========================================================================
    uecl_top8 = _top_n_league_probability(
        r["euro_league_positions"]["UECL"], n_sims, lo=1, hi=8, top=14)
    draw_horizontal_bars(
        path=os.path.join(out_dir, "22_uecl_league_top8.png"),
        eyebrow="UECL · LEAGUE PHASE",
        title="Chance of a Top-8 finish",
        items=uecl_top8,
        bar_color=LIGHT,
        label_w=0.32,
    )

    # =========================================================================
    # 23 — Per-PL-club European win probability
    # =========================================================================
    combined_euro: Dict[str, float] = {}
    for t in teams:
        combined_euro[t] = (
            r["ucl_win_prob"].get(t, 0.0)
            + r["uel_win_prob"].get(t, 0.0)
            + r["uecl_win_prob"].get(t, 0.0)
        )
    combined_rows = sorted(
        ((t, v) for t, v in combined_euro.items() if v > 0.0),
        key=lambda x: -x[1],
    )[:16]
    if combined_rows:
        draw_horizontal_bars(
            path=os.path.join(out_dir, "23_pl_club_europe_win.png"),
            eyebrow="PL CLUBS · EUROPEAN TROPHY PROBABILITY",
            title="Chance of winning a UEFA trophy",
            items=combined_rows,
            bar_color=YELLOW,
            label_w=0.32,
        )

    # =========================================================================
    # 24 — PL Elo ratings
    # =========================================================================
    elo_rows = sorted(
        ((t, r["pl_elos"][t]) for t in teams if t in r["pl_elos"]),
        key=lambda x: -x[1],
    )
    draw_horizontal_bars(
        path=os.path.join(out_dir, "24_pl_elo_ratings.png"),
        eyebrow="PREMIER LEAGUE · MODEL INPUTS",
        title="Elo ratings",
        items=elo_rows,
        value_fmt="{:.0f}",
        bar_color=TEAL,
        label_w=0.32,
    )

    # =========================================================================
    # 25 — UCL win probability per PL club
    # =========================================================================
    ucl_win_rows = sorted(
        ((t, r["ucl_win_prob"].get(t, 0.0)) for t in teams
         if r["ucl_win_prob"].get(t, 0.0) > 0.0),
        key=lambda x: -x[1],
    )[:14]
    if ucl_win_rows:
        draw_horizontal_bars(
            path=os.path.join(out_dir, "25_ucl_winner_by_pl_club.png"),
            eyebrow="UCL · 2026/27",
            title="Champions League win probability",
            items=ucl_win_rows,
            bar_color=YELLOW,
            label_w=0.32,
        )

    print(f"\nAll charts written ({len(os.listdir(out_dir))} files in dir).")


# =============================================================================
# MAIN
# =============================================================================

def main() -> int:
    print("=" * 70)
    print("Loading simulation module …")
    print(f"  {SIM_PATH}")
    print("=" * 70)

    if not os.path.isfile(SIM_PATH):
        print(f"ERROR: file not found: {SIM_PATH}", file=sys.stderr)
        return 1

    # ---- Wipe any stale PNGs before we start ----
    removed = _clear_pngs(OUT_DIR)
    print(f"Cleared {removed} existing PNG(s) from {OUT_DIR}")

    try:
        sim = load_sim_module(SIM_PATH)
    except Exception:
        traceback.print_exc()
        return 1

    if hasattr(sim, "NUM_PL_SIMS"):
        sim.NUM_PL_SIMS = N_SIMS

    print(f"\nRunning {N_SIMS} simulations …")
    try:
        result = sim.run_simulation(N_SIMS)
    except TypeError:
        result = sim.run_simulation()

    print("\nSimulations complete. Building charts …")
    make_all_charts(result, OUT_DIR)

    print("\nDone.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())