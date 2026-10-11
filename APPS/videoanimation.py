"""
premier_league_montecarlo.py
============================

Premier League 2026/27 Monte Carlo simulator driven entirely by the stats
in two CSVs (current season + previous season). No Elo, no external ratings.

* For every team and every metric, the per-match rate is a weighted average
  of the two CSVs, weighted by matches played:

      combined = (n_current * rate_current + n_prior * rate_prior)
                 / (n_current + n_prior)

* Promoted teams (no prior row) get the previous season's bottom-3 average,
  regressed toward the league mean (configurable).

* Attack / defence multipliers come from z-scores of the blended rates.
* Poisson goal model for the remaining fixtures.
* 10,000 simulations.

PNG table columns: P / W / D / L / GF / GA / GD are FULL-SEASON PROJECTIONS
averaged across all simulations.  Probability columns: TITLE %, TOP 4 %,
EURO % (finish top 5), 5TH %, RELEG %.  CSV + console still log every stat
(including TOP 6 %) for auditing.

Install: pip install numpy matplotlib
Run:     python premier_league_montecarlo.py
"""

import math
import csv
import os
import sys
import time

import numpy as np
import matplotlib
matplotlib.use("Agg")
from matplotlib.figure import Figure
from matplotlib.backends.backend_agg import FigureCanvasAgg


# =====================================================================
# CONFIGURATION
# =====================================================================
N_SIMS = 10_000

OUTPUT_CSV = "final_probabilities.csv"
OUTPUT_PNG = "final_table.png"
SEED       = 42

BASE_HOME_XG = 1.56
BASE_AWAY_XG = 1.23
MAX_GOALS    = 10

CURRENT_CSV = r"C:\Users\liam\Documents\GitHub\all-of-my-code\APPS\league-chemp.csv"
PRIOR_CSV   = r"C:\Users\liam\Documents\GitHub\all-of-my-code\APPS\league-chemp (1).csv"

PROMOTED_PRIOR_REGRESSION = 0.5

ATTACK_SENS  = 0.20
DEFENCE_SENS = 0.20

# Attack z-score weights (sum to 1.0)
W_ATT_NPXG         = 0.40
W_ATT_XG           = 0.10
W_ATT_DEEP         = 0.15
W_ATT_PPDA_ALLOWED = 0.15
W_ATT_XPTS         = 0.10
W_ATT_NPXGD        = 0.10

# Defence z-score weights (sum to 1.0); metrics inverted
W_DEF_NPXGA        = 0.40
W_DEF_XGA          = 0.10
W_DEF_DEEP_ALLOWED = 0.15
W_DEF_PPDA         = 0.15
W_DEF_XPTS         = 0.10
W_DEF_NPXGD        = 0.10

# Colours
BG     = "#ffffff"
CARD   = "#eef2f7"
HEADER = "#1f3a5f"
FG     = "#111827"
GOLD   = "#f2c744"
GREEN  = "#1a7f37"
BLUE   = "#0969da"
RED    = "#cf222e"
MUTED  = "#57606a"


# =====================================================================
# PROGRESS BAR
# =====================================================================
class ProgressBar:
    def __init__(self, total, prefix="", width=36, stream=sys.stdout):
        self.total = max(1, int(total))
        self.prefix = prefix
        self.width = width
        self.stream = stream
        self.start = time.time()
        self.last_len = 0
        self.last_draw = 0.0

    def update(self, current, suffix="", force=False):
        current = max(0, min(current, self.total))
        now = time.time()
        if not force and now - self.last_draw < 0.08 and current < self.total:
            return
        self.last_draw = now
        frac = current / self.total
        filled = int(self.width * frac)
        bar = "█" * filled + "░" * (self.width - filled)
        elapsed = now - self.start
        rate = current / elapsed if current > 0 and elapsed > 0 else 0.0
        eta = (self.total - current) / rate if rate > 0 else 0.0
        line = (f"\r{self.prefix} |{bar}| {frac*100:6.2f}%  "
                f"{current:>7,}/{self.total:,}  "
                f"elapsed {self._fmt(elapsed)}  eta {self._fmt(eta)}  "
                f"{rate:7.1f}/s")
        if suffix:
            line += f"  {suffix}"
        pad = max(0, self.last_len - len(line))
        self.stream.write(line + " " * pad)
        self.stream.flush()
        self.last_len = len(line)

    def close(self, suffix=""):
        self.update(self.total, suffix=suffix, force=True)
        self.stream.write("\n")
        self.stream.flush()

    @staticmethod
    def _fmt(seconds):
        seconds = int(seconds)
        m, s = divmod(seconds, 60)
        h, m = divmod(m, 60)
        return f"{h:d}:{m:02d}:{s:02d}" if h else f"{m:02d}:{s:02d}"


# =====================================================================
# LEAGUE DATA
# =====================================================================
TEAMS = [
    "Arsenal", "Aston Villa", "Bournemouth", "Brentford", "Brighton",
    "Chelsea", "Coventry", "Crystal Palace", "Everton", "Fulham",
    "Hull", "Ipswich", "Leeds", "Liverpool", "Man City",
    "Man United", "Newcastle", "Nott'm Forest", "Sunderland", "Tottenham",
]

CSV_TO_SCRIPT = {
    "Manchester City":         "Man City",
    "Manchester United":       "Man United",
    "Newcastle United":        "Newcastle",
    "Nottingham Forest":       "Nott'm Forest",
    "West Ham":                "West Ham",
    "Burnley":                 "Burnley",
    "Wolverhampton Wanderers": "Wolves",
}

PLAYED_RESULTS = [
    ("Arsenal",        "Coventry",       3, 0),
    ("Hull",           "Man United",     2, 0),
    ("Everton",        "Crystal Palace", 2, 0),
    ("Ipswich",        "Sunderland",     2, 1),
    ("Nott'm Forest",  "Leeds",          0, 1),
    ("Brentford",      "Tottenham",      3, 0),
    ("Brighton",       "Aston Villa",    4, 0),
    ("Man City",       "Bournemouth",    2, 1),
    ("Newcastle",      "Liverpool",      2, 2),
    ("Fulham",         "Chelsea",        2, 3),
    ("Crystal Palace", "Man City",       1, 4),
    ("Liverpool",      "Nott'm Forest",  2, 2),
    ("Bournemouth",    "Everton",        1, 1),
    ("Coventry",       "Hull",           0, 1),
    ("Tottenham",      "Newcastle",      0, 2),
    ("Chelsea",        "Brighton",       4, 3),
    ("Leeds",          "Brentford",      1, 1),
    ("Sunderland",     "Fulham",         1, 0),
    ("Man United",     "Ipswich",        5, 2),
    ("Aston Villa",    "Arsenal",        0, 1),
    ("Ipswich",        "Liverpool",      0, 2),
    ("Newcastle",      "Bournemouth",    2, 2),
    ("Brentford",      "Sunderland",     1, 1),
    ("Brighton",       "Leeds",          1, 1),
    ("Fulham",         "Crystal Palace", 2, 3),
    ("Man City",       "Coventry",       1, 0),
    ("Nott'm Forest",  "Tottenham",      0, 0),
    ("Hull",           "Aston Villa",    0, 0),
    ("Everton",        "Man United",     2, 2),
    ("Arsenal",        "Chelsea",        2, 1),
    ("Bournemouth",    "Brentford",      2, 2),
    ("Aston Villa",    "Nott'm Forest",  1, 2),
    ("Chelsea",        "Hull",           2, 2),
    ("Crystal Palace", "Ipswich",        2, 3),
    ("Liverpool",      "Fulham",         0, 0),
    ("Tottenham",      "Everton",        0, 0),
    ("Sunderland",     "Arsenal",        0, 2),
    ("Brighton",       "Coventry",       5, 0),
    ("Man City",       "Man United",     1, 0),
]


# =====================================================================
# CSV LOADING
# =====================================================================
PER_MATCH_KEYS = ["xG", "NPxG", "xGA", "NPxGA", "NPxGD",
                  "deep", "deep_allowed", "xPTS"]
RATE_KEYS      = ["ppda", "ppda_allowed"]
ALL_KEYS       = PER_MATCH_KEYS + RATE_KEYS


def _read_stats_csv(path):
    if not os.path.exists(path):
        raise FileNotFoundError(f"CSV not found: {path}")
    out = {}
    with open(path, newline="", encoding="utf-8-sig") as f:
        reader = csv.DictReader(f, delimiter=";")
        for row in reader:
            csv_team = row["team"].strip()
            team = CSV_TO_SCRIPT.get(csv_team, csv_team)
            n = max(1, int(row["matches"]))
            out[team] = {
                "matches":      n,
                "xG":           float(row["xG"])           / n,
                "NPxG":         float(row["NPxG"])         / n,
                "xGA":          float(row["xGA"])          / n,
                "NPxGA":        float(row["NPxGA"])        / n,
                "NPxGD":        float(row["NPxGD"])        / n,
                "deep":         int(row["deep"])           / n,
                "deep_allowed": int(row["deep_allowed"])   / n,
                "xPTS":         float(row["xPTS"])         / n,
                "ppda":         float(row["ppda"]),
                "ppda_allowed": float(row["ppda_allowed"]),
            }
    return out


def load_current_stats(path=CURRENT_CSV):
    raw = _read_stats_csv(path)
    stats = {}
    with open(path, newline="", encoding="utf-8-sig") as f:
        reader = csv.DictReader(f, delimiter=";")
        for row in reader:
            csv_team = row["team"].strip()
            team = CSV_TO_SCRIPT.get(csv_team, csv_team)
            if team not in TEAMS:
                continue
            stats[team] = {
                "number":       int(row["number"]),
                "matches":      int(row["matches"]),
                "wins":         int(row["wins"]),
                "draws":        int(row["draws"]),
                "loses":        int(row["loses"]),
                "goals":        int(row["goals"]),
                "ga":           int(row["ga"]),
                "points":       int(row["points"]),
                "xG":           float(row["xG"]),
                "NPxG":         float(row["NPxG"]),
                "xGA":          float(row["xGA"]),
                "NPxGA":        float(row["NPxGA"]),
                "NPxGD":        float(row["NPxGD"]),
                "ppda":         float(row["ppda"]),
                "ppda_allowed": float(row["ppda_allowed"]),
                "deep":         int(row["deep"]),
                "deep_allowed": int(row["deep_allowed"]),
                "xPTS":         float(row["xPTS"]),
            }
    missing = [t for t in TEAMS if t not in stats]
    if missing:
        raise ValueError(f"Missing teams in {path}: {missing}")
    stats["_per_match"] = raw
    return stats


def load_prior_stats(path=PRIOR_CSV):
    return _read_stats_csv(path)


# =====================================================================
# BLEND — pure weighted average of the two CSVs' per-match rates
# =====================================================================
def blend_stats(current, prior,
                promoted_prior_regression=PROMOTED_PRIOR_REGRESSION):
    if prior:
        league_mean_prior = {k: float(np.mean([s[k] for s in prior.values()]))
                             for k in ALL_KEYS}
        bottom3 = sorted(prior.values(), key=lambda s: s["xPTS"])[:3]
        promoted_prior = {}
        for k in ALL_KEYS:
            b3 = float(np.mean([s[k] for s in bottom3]))
            promoted_prior[k] = ((1.0 - promoted_prior_regression) * b3
                                 + promoted_prior_regression * league_mean_prior[k])
    else:
        promoted_prior = {k: 0.0 for k in ALL_KEYS}

    blended = {}
    for t in TEAMS:
        n_cur = max(1, current[t]["matches"])
        p = prior.get(t)
        if p is None:
            rates_prior = promoted_prior
            n_prior = 38.0
        else:
            rates_prior = p
            n_prior = max(1, p["matches"])

        total = n_cur + n_prior
        blended[t] = {}
        for k in ALL_KEYS:
            if k in PER_MATCH_KEYS:
                rate_cur = current["_per_match"][t][k]
            else:
                rate_cur = current[t][k]
            blended[t][k] = (n_cur * rate_cur + n_prior * rates_prior[k]) / total
    return blended


# =====================================================================
# STRENGTH MODEL
# =====================================================================
def compute_strengths(blended):
    def z_scores(key, invert=False):
        vals = np.array([blended[t][key] for t in TEAMS], dtype=float)
        mu, sd = vals.mean(), vals.std() + 1e-9
        z = (vals - mu) / sd
        if invert:
            z = -z
        return {t: float(z[i]) for i, t in enumerate(TEAMS)}

    z_npxg         = z_scores("NPxG")
    z_xg           = z_scores("xG")
    z_deep         = z_scores("deep")
    z_ppda_allowed = z_scores("ppda_allowed")
    z_xpts         = z_scores("xPTS")
    z_npxgd        = z_scores("NPxGD")

    z_npxga        = z_scores("NPxGA",        invert=True)
    z_xga          = z_scores("xGA",          invert=True)
    z_deep_allowed = z_scores("deep_allowed", invert=True)
    z_ppda         = z_scores("ppda",         invert=True)

    strengths = {}
    for t in TEAMS:
        attack_z = (W_ATT_NPXG           * z_npxg[t]
                    + W_ATT_XG           * z_xg[t]
                    + W_ATT_DEEP         * z_deep[t]
                    + W_ATT_PPDA_ALLOWED * z_ppda_allowed[t]
                    + W_ATT_XPTS         * z_xpts[t]
                    + W_ATT_NPXGD        * z_npxgd[t])
        defence_z = (W_DEF_NPXGA           * z_npxga[t]
                     + W_DEF_XGA           * z_xga[t]
                     + W_DEF_DEEP_ALLOWED  * z_deep_allowed[t]
                     + W_DEF_PPDA          * z_ppda[t]
                     + W_DEF_XPTS          * z_xpts[t]
                     + W_DEF_NPXGD         * z_npxgd[t])

        attack  = max(0.55, min(1.65, math.exp(ATTACK_SENS  * attack_z)))
        defence = max(0.55, min(1.65, math.exp(-DEFENCE_SENS * defence_z)))

        strengths[t] = {
            "attack":    attack,
            "defence":   defence,
            "z_attack":  attack_z,
            "z_defence": defence_z,
        }
    return strengths


# =====================================================================
# LEAGUE STATE
# =====================================================================
def build_state(played_results):
    """
    Build the current league table from the results actually played
    so far in the 2026/27 season.  The CURRENT_CSV is only used for
    the strength model (blended attack/defence stats), NOT for the
    current W/D/L/GF/GA totals.
    """
    table = {t: {"p": 0, "w": 0, "d": 0, "l": 0,
                 "gf": 0, "ga": 0, "pts": 0} for t in TEAMS}

    for h, a, hg, ag in played_results:
        table[h]["p"] += 1
        table[a]["p"] += 1
        table[h]["gf"] += hg
        table[h]["ga"] += ag
        table[a]["gf"] += ag
        table[a]["ga"] += hg

        if hg > ag:
            table[h]["w"] += 1
            table[a]["l"] += 1
            table[h]["pts"] += 3
        elif ag > hg:
            table[a]["w"] += 1
            table[h]["l"] += 1
            table[a]["pts"] += 3
        else:
            table[h]["d"] += 1
            table[a]["d"] += 1
            table[h]["pts"] += 1
            table[a]["pts"] += 1

    played = {(h, a) for h, a, _, _ in played_results}
    all_fixtures = [(h, a) for h in TEAMS for a in TEAMS if h != a]
    remaining = [f for f in all_fixtures if f not in played]
    return list(TEAMS), table, remaining


# =====================================================================
# GOAL MODEL
# =====================================================================
def expected_goals(home_team, away_team, strengths):
    sh = strengths[home_team]
    sa = strengths[away_team]
    lam_h = BASE_HOME_XG * sh["attack"] * sa["defence"]
    lam_a = BASE_AWAY_XG * sa["attack"] * sh["defence"]
    return max(0.05, min(lam_h, 6.0)), max(0.05, min(lam_a, 6.0))


def poisson_pmf(lam, max_goals=MAX_GOALS):
    probs = [0.0] * (max_goals + 1)
    p = math.exp(-lam)
    for k in range(max_goals + 1):
        probs[k] = p
        p *= lam / (k + 1)
    s = sum(probs)
    return [x / s for x in probs]


# =====================================================================
# SIMULATOR
# =====================================================================
class SeasonSimulator:
    def __init__(self, teams, strengths, current_table, remaining, seed=None):
        self.teams = list(teams)
        self.n = len(self.teams)
        self.idx = {t: i for i, t in enumerate(self.teams)}
        self.rng = np.random.default_rng(seed)

        # Current league state (seeds every simulation)
        self.cur_pts = np.array([current_table[t]["pts"] for t in self.teams], dtype=np.int64)
        self.cur_w   = np.array([current_table[t]["w"]   for t in self.teams], dtype=np.int64)
        self.cur_d   = np.array([current_table[t]["d"]   for t in self.teams], dtype=np.int64)
        self.cur_l   = np.array([current_table[t]["l"]   for t in self.teams], dtype=np.int64)
        self.cur_gd  = np.array([current_table[t]["gf"] - current_table[t]["ga"]
                                 for t in self.teams], dtype=np.int64)
        self.cur_gf  = np.array([current_table[t]["gf"] for t in self.teams], dtype=np.int64)
        self.cur_ga  = np.array([current_table[t]["ga"] for t in self.teams], dtype=np.int64)

        self.hi = np.array([self.idx[h] for h, _ in remaining], dtype=np.int64)
        self.ai = np.array([self.idx[a] for _, a in remaining], dtype=np.int64)
        self.m  = len(self.hi)

        # Pre-computed Poisson CDFs for every remaining fixture
        cum_h = np.empty((self.m, MAX_GOALS + 1))
        cum_a = np.empty((self.m, MAX_GOALS + 1))
        for k, (h, a) in enumerate(remaining):
            lh, la = expected_goals(h, a, strengths)
            cum_h[k] = np.cumsum(poisson_pmf(lh))
            cum_a[k] = np.cumsum(poisson_pmf(la))
        self.cum_h = cum_h
        self.cum_a = cum_a

        # Event counters (positional outcomes)
        z = np.zeros(self.n, dtype=np.int64)
        self.title_c = z.copy()
        self.top4_c  = z.copy()
        self.fifth_c = z.copy()
        self.top6_c  = z.copy()
        self.rel_c   = z.copy()
        self.pos_hist = np.zeros((self.n, self.n), dtype=np.int64)

        # NEW: per-sim tallies of W / D / L accumulated from remaining matches
        self.win_c  = np.zeros(self.n, dtype=np.int64)
        self.draw_c = np.zeros(self.n, dtype=np.int64)
        self.loss_c = np.zeros(self.n, dtype=np.int64)

        # Running totals (float, for averaging)
        f = np.zeros(self.n)
        self.pts_sum = f.copy()
        self.gf_sum  = f.copy()
        self.ga_sum  = f.copy()
        self.pos_sum = f.copy()
        self.sims_done = 0

    def simulate_one(self):
        n, m = self.n, self.m
        u = self.rng.random((2, m))
        hg = (self.cum_h < u[0][:, None]).sum(axis=1)
        ag = (self.cum_a < u[1][:, None]).sum(axis=1)

        hw = hg > ag
        aw = ag > hg
        dr = ~(hw | aw)

        hpts = np.where(hw, 3, np.where(dr, 1, 0)).astype(np.int64)
        apts = np.where(aw, 3, np.where(dr, 1, 0)).astype(np.int64)

        # --- Totals after this sim's remaining fixtures ---
        pts = (self.cur_pts
               + np.bincount(self.hi, weights=hpts, minlength=n).astype(np.int64)
               + np.bincount(self.ai, weights=apts, minlength=n).astype(np.int64))

        dh = hg - ag
        gd = (self.cur_gd
              + np.bincount(self.hi, weights=dh,  minlength=n).astype(np.int64)
              + np.bincount(self.ai, weights=-dh, minlength=n).astype(np.int64))
        gf = (self.cur_gf
              + np.bincount(self.hi, weights=hg, minlength=n).astype(np.int64)
              + np.bincount(self.ai, weights=ag, minlength=n).astype(np.int64))
        ga = (self.cur_ga
              + np.bincount(self.hi, weights=ag, minlength=n).astype(np.int64)
              + np.bincount(self.ai, weights=hg, minlength=n).astype(np.int64))

        # --- NEW: tally wins / draws / losses from remaining fixtures only ---
        if hw.any():
            np.add.at(self.win_c,  self.hi[hw], 1)
            np.add.at(self.loss_c, self.ai[hw], 1)
        if aw.any():
            np.add.at(self.win_c,  self.ai[aw], 1)
            np.add.at(self.loss_c, self.hi[aw], 1)
        if dr.any():
            np.add.at(self.draw_c, self.hi[dr], 1)
            np.add.at(self.draw_c, self.ai[dr], 1)

        # --- Rankings (points, GD, GF, then random tie-break) ---
        tb = self.rng.random(n)
        order = np.lexsort((tb, -gf, -gd, -pts))
        ranks = np.empty(n, dtype=np.int64)
        ranks[order] = np.arange(1, n + 1)

        self.title_c[order[0]] += 1
        self.top4_c[order[:4]] += 1
        self.fifth_c[order[4]] += 1
        self.top6_c[order[:6]] += 1
        self.rel_c[order[-3:]] += 1
        self.pos_hist[order, np.arange(n)] += 1

        self.pts_sum += pts
        self.gf_sum  += gf
        self.ga_sum  += ga
        self.pos_sum += ranks
        self.sims_done += 1

    def snapshot(self):
        s = max(1, self.sims_done)
        top5 = self.top4_c + self.fifth_c      # = "EURO %"
        return {
            "sims":    self.sims_done,
            "title":   self.title_c / s * 100.0,
            "top4":    self.top4_c  / s * 100.0,
            "fifth":   self.fifth_c / s * 100.0,
            "euro":    top5 / s * 100.0,        # top-5 finish total
            "top6":    self.top6_c  / s * 100.0,
            "rel":     self.rel_c   / s * 100.0,
            "avg_pts": self.pts_sum / s,
            # NEW: full-season averages (current + remaining), all per sim
            "avg_w":   self.cur_w  + self.win_c  / s,
            "avg_d":   self.cur_d  + self.draw_c / s,
            "avg_l":   self.cur_l  + self.loss_c / s,
            "avg_gf":  self.gf_sum / s,
            "avg_ga":  self.ga_sum / s,
            "avg_gd":  (self.gf_sum - self.ga_sum) / s,
            "avg_pos": self.pos_sum / s,
        }


# =====================================================================
# FINAL TABLE RENDERER
# =====================================================================
def render_final_table(teams, snap, sims, path=OUTPUT_PNG):
    fig = Figure(figsize=(15.5, 11.0), dpi=160, facecolor=BG)
    canvas = FigureCanvasAgg(fig)

    fig.text(0.5, 0.980,
             "PREMIER LEAGUE 2026/27  —  PREDICTED FINAL TABLE",
             ha="center", va="top", color=FG, fontsize=20, fontweight="bold")

    fig.text(0.5, 0.952,
             f"Monte Carlo simulation  •  {sims:,} full seasons  •  "
             f"current + prior-season stats blended by games played",
             ha="center", va="top", color=BLUE, fontsize=12, fontweight="bold")

    fig.text(0.5, 0.928,
             "Sorted by projected average points.  "
             "P / W / D / L / GF / GA / GD are full-season totals "
             "averaged across all simulations.  Percentages are the "
             "share of simulations in which the event occurred.",
             ha="center", va="top", color=MUTED, fontsize=10, style="italic")

    ax = fig.add_axes([0.020, 0.045, 0.960, 0.865])
    ax.axis("off")
    ax.set_facecolor(BG)

    order = sorted(range(len(teams)), key=lambda i: -snap["avg_pts"][i])

    # Full-season game count (double round-robin)
    total_games = 2 * (len(teams) - 1)

    # ---- table columns -------------------------------------------------
    header = ["#", "TEAM", "P", "W", "D", "L", "GF", "GA", "GD",
              "AVG PTS",
              "TITLE %", "TOP 4 %", "EURO %", "5TH %",
              "RELEG %", "AVG POS"]

    cell_text = [header]
    for rank, i in enumerate(order, 1):
        t = teams[i]
        cell_text.append([
            str(rank),
            t,
            str(total_games),                       # full season
            f"{snap['avg_w'][i]:.1f}",              # projected avg W
            f"{snap['avg_d'][i]:.1f}",              # projected avg D
            f"{snap['avg_l'][i]:.1f}",              # projected avg L
            f"{snap['avg_gf'][i]:.1f}",             # projected avg GF
            f"{snap['avg_ga'][i]:.1f}",             # projected avg GA
            f"{snap['avg_gd'][i]:+.1f}",            # projected avg GD
            f"{snap['avg_pts'][i]:.2f}",
            f"{snap['title'][i]:.2f}",
            f"{snap['top4'][i]:.2f}",
            f"{snap['euro'][i]:.2f}",
            f"{snap['fifth'][i]:.2f}",
            f"{snap['rel'][i]:.2f}",
            f"{snap['avg_pos'][i]:.2f}",
        ])

    n_cols = len(header)
    col_widths = [0.028, 0.170,         # # TEAM
                  0.030, 0.030, 0.030, 0.030,   # P W D L
                  0.036, 0.036, 0.040,          # GF GA GD
                  0.068,                        # AVG PTS
                  0.070, 0.070, 0.072, 0.062,   # TITLE TOP4 EURO 5TH
                  0.072, 0.070]                 # RELEG AVG POS
    col_widths = col_widths[:n_cols]
    while len(col_widths) < n_cols:
        col_widths.append(0.05)

    tbl = ax.table(cellText=cell_text, loc="center", cellLoc="center",
                   colWidths=col_widths)
    tbl.auto_set_font_size(False)
    tbl.set_fontsize(10.5)
    tbl.scale(1, 1.85)

    for (r, c), cell in tbl.get_celld().items():
        cell.set_edgecolor("#21262d")
        cell.set_linewidth(0.6)

        if r == 0:
            cell.set_facecolor(HEADER)
            cell.set_text_props(color=GOLD, fontweight="bold", fontsize=10.5)
            continue

        cell.set_facecolor(CARD if r % 2 == 0 else BG)

        rank = r
        if c == 1:
            base_colour, weight = FG, "bold"
        elif rank <= 4:
            base_colour, weight = GREEN, "normal"
        elif rank >= 18:
            base_colour, weight = RED, "normal"
        else:
            base_colour, weight = FG, "normal"

        colour = base_colour
        if c in (10, 11, 12, 13):
            val = float(cell_text[r][c])
            if val >= 50:
                colour, weight = GREEN, "bold"
            elif val >= 10:
                colour = BLUE
            else:
                colour = FG
        elif c == 14:
            val = float(cell_text[r][c])
            if val >= 50:
                colour, weight = RED, "bold"
            elif val >= 10:
                colour = RED
            else:
                colour = FG

        cell.set_text_props(color=colour, fontweight=weight)

    fig.text(0.5, 0.020,
             "P / W / D / L / GF / GA / GD = full-season projections "
             "(average across all simulations).   "
             "TITLE % = champions.   TOP 4 % = finish in top 4.   "
             "EURO % = finish in top 5.   "
             "5TH % = finish exactly 5th.   RELEG % = bottom three.",
             ha="center", va="center", color=MUTED,
             fontsize=9.5, style="italic")

    canvas.draw()
    fig.savefig(path, facecolor=BG)
    return path


# =====================================================================
# CSV EXPORT
# =====================================================================
def save_csv(path, teams, current_table, snap, stats, blended, prior_stats):
    order = sorted(range(len(teams)), key=lambda i: -snap["avg_pts"][i])
    with open(path, "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["Rank", "Team", "Played", "W", "D", "L", "GF", "GA", "GD",
                    "CurrentPoints", "AvgFinalPoints", "AvgPosition",
                    "AvgW", "AvgD", "AvgL",
                    "AvgGF", "AvgGA", "AvgGD",
                    "TitlePct", "Top4Pct", "EuroPct", "FifthPct",
                    "Top6Pct", "RelegationPct", "AvoidRelegationPct",
                    "BlendedNPxG", "BlendedNPxGA", "BlendedNPxGD",
                    "BlendedxPTS", "BlendedPPDA", "BlendedPPDAAllowed",
                    "PriorMatches"])
        for r, i in enumerate(order, 1):
            t = teams[i]
            row = current_table[t]
            gd  = row["gf"] - row["ga"]
            pm  = prior_stats.get(t, {}).get("matches", 0)
            b   = blended[t]
            w.writerow([
                r, t, row["p"], row["w"], row["d"], row["l"],
                row["gf"], row["ga"], gd, row["pts"],
                f"{snap['avg_pts'][i]:.4f}",
                f"{snap['avg_pos'][i]:.4f}",
                f"{snap['avg_w'][i]:.4f}",
                f"{snap['avg_d'][i]:.4f}",
                f"{snap['avg_l'][i]:.4f}",
                f"{snap['avg_gf'][i]:.4f}",
                f"{snap['avg_ga'][i]:.4f}",
                f"{snap['avg_gd'][i]:.4f}",
                f"{snap['title'][i]:.4f}",
                f"{snap['top4'][i]:.4f}",
                f"{snap['euro'][i]:.4f}",
                f"{snap['fifth'][i]:.4f}",
                f"{snap['top6'][i]:.4f}",
                f"{snap['rel'][i]:.4f}",
                f"{100.0 - snap['rel'][i]:.4f}",
                f"{b['NPxG']:.3f}",
                f"{b['NPxGA']:.3f}",
                f"{b['NPxGD']:.3f}",
                f"{b['xPTS']:.3f}",
                f"{b['ppda']:.3f}",
                f"{b['ppda_allowed']:.3f}",
                pm,
            ])


# =====================================================================
# SIMULATION PASS
# =====================================================================
def run_simulations(sim, n_sims, snapshot_every=250):
    n_blocks = max(1, n_sims // snapshot_every)
    bar = ProgressBar(n_blocks, prefix="Simulating", width=40)
    for step in range(1, n_blocks + 1):
        for _ in range(snapshot_every):
            sim.simulate_one()
        bar.update(step, suffix=f"sim {sim.sims_done:>7,}/{n_sims:,}")
    leftover = n_sims - sim.sims_done
    for _ in range(leftover):
        sim.simulate_one()
    bar.close(suffix="done")
    return sim.snapshot()


# =====================================================================
# MAIN
# =====================================================================
def main():
    print("=" * 78)
    print("  Premier League 2026/27 Monte Carlo Simulator")
    print("=" * 78)

    current = load_current_stats(CURRENT_CSV)
    prior   = load_prior_stats(PRIOR_CSV)
    blended = blend_stats(current, prior)
    strengths = compute_strengths(blended)

    # Build the current league table from the ACTUAL results played
    # so far in the 2026/27 season (PLAYED_RESULTS), NOT from the
    # full-season CURRENT_CSV.  The CURRENT_CSV is only used for the
    # blended strength model.
    teams, current_table, remaining = build_state(PLAYED_RESULTS)

    print(f"  Current CSV        : {CURRENT_CSV}")
    print(f"  Prior CSV          : {PRIOR_CSV}")
    print(f"  Prior teams found  : {len(prior)}")
    missing_prior = [t for t in TEAMS if t not in prior]
    if missing_prior:
        print(f"  No prior row for   : {', '.join(missing_prior)}"
              f"  (bottom-3 prior used)")
    print(f"  Teams              : {len(teams)}")
    print(f"  Fixtures remaining : {len(remaining)}  "
          f"(played so far: {len(PLAYED_RESULTS)})")
    print(f"  Simulations        : {N_SIMS:,}")
    print(f"  Seed               : {SEED}")
    print("=" * 78)
    print("  Blended strengths (attack / defence multipliers):")
    print(f"  {'TEAM':<18}{'CUR N':>7}{'PRIOR N':>9}"
          f"{'ATTACK':>9}{'DEFENCE':>10}")
    print("  " + "-" * 53)
    for t in sorted(TEAMS, key=lambda x: -strengths[x]["attack"]):
        n_cur = current[t]["matches"]
        n_pri = prior.get(t, {}).get("matches", 0)
        print(f"  {t:<18}{n_cur:>7}{n_pri:>9}"
              f"{strengths[t]['attack']:>9.3f}"
              f"{strengths[t]['defence']:>10.3f}")
    print("=" * 78)

    sim = SeasonSimulator(teams, strengths, current_table, remaining, seed=SEED)
    print()
    t0 = time.time()
    final_snap = run_simulations(sim, N_SIMS)
    print(f"  Simulation finished in {time.time()-t0:.1f}s\n")

    print("=" * 78)
    print("  Outputs")
    print("=" * 78)
    png_path = render_final_table(teams, final_snap, N_SIMS, OUTPUT_PNG)
    print(f"  PNG saved    -> {png_path}")
    save_csv(OUTPUT_CSV, teams, current_table, final_snap,
             current, blended, prior)
    print(f"  CSV saved    -> {OUTPUT_CSV}")

    print()
    print("=" * 78)
    print(f"  FINAL PROJECTION ({N_SIMS:,} simulations)")
    print("=" * 78)
    order = sorted(range(len(teams)), key=lambda i: -final_snap["avg_pts"][i])
    print(f"  {'#':>2}  {'TEAM':<18}{'AVG PTS':>9}"
          f"{'TITLE%':>9}{'TOP4%':>9}{'EURO%':>9}{'5TH%':>9}"
          f"{'REL%':>9}")
    print("  " + "-" * 91)
    for r, i in enumerate(order, 1):
        print(f"  {r:>2}  {teams[i]:<18}"
              f"{final_snap['avg_pts'][i]:>9.2f}"
              f"{final_snap['title'][i]:>9.2f}"
              f"{final_snap['top4'][i]:>9.2f}"
              f"{final_snap['euro'][i]:>9.2f}"
              f"{final_snap['fifth'][i]:>9.2f}"
              f"{final_snap['rel'][i]:>9.2f}")
    print("=" * 78)


if __name__ == "__main__":
    main()