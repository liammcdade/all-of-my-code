#!/usr/bin/env python3
"""
best_team_of_all_time.py
========================
Finds the greatest team in English top-flight history (1888-89 → present).

Three rating structures, all combined into a 0-10 score:
    A. Results-only Elo               (W/D/L, classical)
    B. Goal-difference-weighted Elo   (rewards dominance)
    C. Bradley-Terry per season       (proper ML, logistic regression)

Handles both CSV schemas:
    - Old (1993-94): Date,HomeTeam,AwayTeam,FTHG,FTAG,FTR
    - New (2000-01+): same + HT scores, ref, shots, cards, odds, ...

Author: first attempt
"""

import os
import glob
import warnings
from pathlib import Path
import numpy as np
import pandas as pd

warnings.filterwarnings("ignore")

# ══════════════════════════════════════════════════════════════════════
#  CONFIG  — edit these
# ══════════════════════════════════════════════════════════════════════
DATA_DIR   = Path(r"C:\Users\liam\Documents\GitHub\Footballdata\data\ENGLAND\Premier league\GAMES")
OUTPUT_DIR = DATA_DIR.parent / "outputs"

PL_START   = None          # e.g. "1992-08-15" to restrict to PL era
TOP_DIV    = "E0"          # filter Div column if present (football-data.co.uk convention)

# Elo hyperparameters
ELO_BASE           = 1500
ELO_K              = 20
ELO_HOME_ADVANTAGE = 60
SEASON_REGRESS     = 0.75   # 1.0 = no decay, 0.0 = full reset between seasons

# Filtering thresholds (drop 1-season wonders)
MIN_MATCHES = 500
MIN_SEASONS = 15

# Composite weights
W_PEAK, W_BEST_SEASON, W_AVG = 0.35, 0.40, 0.25   # Elo component
BT_MAX_W, BT_AVG_W           = 0.60, 0.40         # Bradley-Terry component
ELO_SHARE, BT_SHARE          = 0.45, 0.35         # final blend (was 0.60/0.40)
ACH_SHARE                    = 0.20              # achievement component

BT_K_SHRINK = 5.0   # pseudo-seasons of prior for Bayesian shrinkage


# ══════════════════════════════════════════════════════════════════════
#  TEAM NAME CANONICALISATION
# ══════════════════════════════════════════════════════════════════════
ALIASES = {
    "Sheffield Weds":   "Sheffield Wednesday",
    "Nott'm Forest":    "Nottingham Forest",
    "Man United":       "Manchester United",
    "Man City":         "Manchester City",
    "Newcastle":        "Newcastle United",
    "Tottenham":        "Tottenham Hotspur",
    "West Brom":        "West Bromwich Albion",
    "West Ham":         "West Ham United",
    "QPR":              "Queens Park Rangers",
    "Stoke":            "Stoke City",
    "Swansea":          "Swansea City",
    "Wigan":            "Wigan Athletic",
    "Wolves":           "Wolverhampton Wanderers",
    "Norwich":          "Norwich City",
    "Hull":             "Hull City",
    "Brighton":         "Brighton & Hove Albion",
    "Huddersfield":     "Huddersfield Town",
    "Sheffield Utd":    "Sheffield United",
    "Bournemouth":      "AFC Bournemouth",
    "Charlton":         "Charlton Athletic",
    "Coventry":         "Coventry City",
    "Derby":            "Derby County",
    "Ipswich":          "Ipswich Town",
    "Leicester":        "Leicester City",
    "Blackburn":        "Blackburn Rovers",
    "Bolton":           "Bolton Wanderers",
    "Preston":          "Preston North End",
    "Birmingham":       "Birmingham City",
    "Luton":            "Luton Town",
}

def canon(name: str) -> str:
    return ALIASES.get(str(name).strip(), str(name).strip())


# ══════════════════════════════════════════════════════════════════════
#  DATA LOADING  (both schemas → one tidy frame)
# ══════════════════════════════════════════════════════════════════════
CORE = ["Date", "HomeTeam", "AwayTeam", "FTHG", "FTAG"]

def season_of(ts: pd.Timestamp) -> str:
    y = ts.year
    return f"{y}-{y+1}" if ts.month >= 7 else f"{y-1}-{y}"

def _read_csv(path: Path) -> pd.DataFrame | None:
    for enc in ("utf-8-sig", "utf-8", "latin-1", "cp1252"):
        try:
            return pd.read_csv(path, encoding=enc)
        except (UnicodeDecodeError, pd.errors.ParserError):
            continue
    return None

def load_matches(folder: Path) -> pd.DataFrame:
    files = sorted(glob.glob(str(folder / "*.csv")))
    if not files:
        raise FileNotFoundError(f"No CSVs in {folder}")

    frames, bad = [], []
    for f in files:
        df = _read_csv(Path(f))
        if df is None:
            bad.append((Path(f).name, "unreadable")); continue
        df.columns = [c.strip() for c in df.columns]

        # Optional Div filter
        if "Div" in df.columns and TOP_DIV:
            df = df[df["Div"].astype(str).str.strip() == TOP_DIV]

        missing = [c for c in CORE if c not in df.columns]
        if missing:
            bad.append((Path(f).name, f"missing {missing}")); continue

        sub = df[CORE].copy()
        sub["source"] = Path(f).stem
        frames.append(sub)

    if not frames:
        raise RuntimeError("No readable match files found.")

    m = pd.concat(frames, ignore_index=True)
    m["HomeTeam"] = m["HomeTeam"].map(canon)
    m["AwayTeam"] = m["AwayTeam"].map(canon)
    m["FTHG"]     = pd.to_numeric(m["FTHG"], errors="coerce")
    m["FTAG"]     = pd.to_numeric(m["FTAG"], errors="coerce")
    m["Date"]     = pd.to_datetime(m["Date"], dayfirst=True, errors="coerce")

    n0 = len(m)
    m = m.dropna(subset=CORE)
    m = m[(m["HomeTeam"] != "") & (m["AwayTeam"] != "")]
    m = m.drop_duplicates(subset=["Date", "HomeTeam", "AwayTeam"])
    m = m.sort_values("Date").reset_index(drop=True)
    m["season"] = m["Date"].apply(season_of)

    if PL_START:
        m = m[m["Date"] >= pd.Timestamp(PL_START)].reset_index(drop=True)

    # ── report ──
    print(f"\nLoaded {len(m):,} matches from {len(frames)} files")
    print(f"  dropped {n0 - len(m):,} invalid / duplicate rows")
    print(f"  dates  : {m['Date'].min().date()} → {m['Date'].max().date()}")
    print(f"  seasons: {m['season'].nunique()}")
    print(f"  teams  : {m['HomeTeam'].nunique()}")
    if bad:
        print(f"  ⚠ {len(bad)} files skipped (first 5):")
        for name, why in bad[:5]:
            print(f"     - {name}: {why}")
    return m


# ══════════════════════════════════════════════════════════════════════
#  ELO ENGINE
# ══════════════════════════════════════════════════════════════════════
def _goal_mult(gd: int) -> float:
    if gd <= 1: return 1.0
    if gd == 2: return 1.5
    return (11.0 + gd) / 8.0

def run_elo(matches: pd.DataFrame, *, goal_weight: bool):
    ratings, season_end, sp = {}, {}, {}
    rows = []
    for season in sorted(matches["season"].unique()):
        sm = matches[matches["season"] == season]
        for r in sm.itertuples(index=False):
            h, a = r.HomeTeam, r.AwayTeam
            rh, ra = ratings.get(h, ELO_BASE), ratings.get(a, ELO_BASE)
            exp_h  = 1.0 / (1.0 + 10 ** ((ra - rh - ELO_HOME_ADVANTAGE) / 400.0))

            if   r.FTHG > r.FTAG: sh = 1.0
            elif r.FTHG < r.FTAG: sh = 0.0
            else:                 sh = 0.5

            k = ELO_K * (_goal_mult(int(abs(r.FTHG - r.FTAG))) if goal_weight else 1.0)
            nh, na = rh + k * (sh - exp_h), ra + k * ((1 - sh) - (1 - exp_h))
            ratings[h], ratings[a] = nh, na
            sp.setdefault(h, set()).add(season)
            sp.setdefault(a, set()).add(season)
            rows.append((r.Date, season, h, a, nh, na))

        for t, rt in ratings.items():
            season_end[(season, t)] = rt
        for t in ratings:
            ratings[t] = SEASON_REGRESS * ratings[t] + (1 - SEASON_REGRESS) * ELO_BASE

    pm = pd.DataFrame(rows, columns=["Date", "season", "home", "away",
                                     "home_post", "away_post"])
    return pm, season_end, sp


# ══════════════════════════════════════════════════════════════════════
#  BRADLEY-TERRY  (per-season logistic regression = real ML)
# ══════════════════════════════════════════════════════════════════════
def run_bradley_terry(matches: pd.DataFrame) -> pd.DataFrame:
    from sklearn.linear_model import LogisticRegression

    out = []
    for season in sorted(matches["season"].unique()):
        sm = matches[matches["season"] == season]
        nd = sm[sm["FTHG"] != sm["FTAG"]]
        teams = sorted(set(sm["HomeTeam"]) | set(sm["AwayTeam"]))
        if len(nd) < 50 or len(teams) < 6:
            continue

        idx = {t: i for i, t in enumerate(teams)}
        X = np.zeros((len(nd), len(teams)))
        for i, r in enumerate(nd.itertuples(index=False)):
            X[i, idx[r.HomeTeam]] =  1.0
            X[i, idx[r.AwayTeam]] = -1.0
        y = (nd["FTHG"] > nd["FTAG"]).astype(int).values

        try:
            clf = LogisticRegression(C=0.5, max_iter=500, solver="lbfgs")
            clf.fit(X, y)
        except Exception as e:
            print(f"  BT skipped {season}: {e}"); continue

        # Z-score within season so early small-league seasons don't dominate
        coefs = clf.coef_[0]
        mu, sd = coefs.mean(), coefs.std()
        z = (coefs - mu) / (sd + 1e-9)

        for t, i in idx.items():
            out.append((season, t, float(z[i])))

    raw = pd.DataFrame(out, columns=["season", "team", "bt_z"])

    # Per-team aggregated stats with Bayesian shrinkage
    agg = raw.groupby("team")["bt_z"].agg(["max", "mean", "count"]).rename(
        columns={"max": "bt_peak_raw", "mean": "bt_avg_raw", "count": "bt_seasons"})
    shrink = agg["bt_seasons"] / (agg["bt_seasons"] + BT_K_SHRINK)
    agg["bt_peak"] = agg["bt_peak_raw"] * shrink
    agg["bt_avg"]  = agg["bt_avg_raw"]  * shrink
    return agg.reset_index()


# ══════════════════════════════════════════════════════════════════════
#  SCORING
# ══════════════════════════════════════════════════════════════════════
def minmax(s: pd.Series) -> pd.Series:
    lo, hi = s.min(), s.max()
    return pd.Series(1.0, index=s.index) if hi == lo else (s - lo) / (hi - lo)

def summarize_elo(pm: pd.DataFrame, season_end: dict, sp: dict) -> pd.DataFrame:
    long = pd.concat([
        pm[["home", "home_post"]].rename(columns={"home": "team", "home_post": "rating"}),
        pm[["away", "away_post"]].rename(columns={"away": "team", "away_post": "rating"}),
    ])
    base = long.groupby("team")["rating"].agg(
        peak_raw="max", avg="mean", matches="size")
    # Longevity-aware peak: compress short-career spikes toward the mean
    base["peak"] = base["peak_raw"] - 0.5 * (base["peak_raw"] - base["avg"])
    bse = (pd.Series({(s, t): r for (s, t), r in season_end.items()})
             .groupby(level=1).max().rename("best_season"))
    ns  = pd.Series({t: len(v) for t, v in sp.items()}, name="seasons")
    return base.join(bse).join(ns)

def summarize_bt(df: pd.DataFrame) -> pd.DataFrame:
    return df.set_index("team")[["bt_peak", "bt_avg"]]

def summarize_achievements(matches: pd.DataFrame) -> pd.DataFrame:
    """Compute titles and top-4 finishes per team from per-season standings."""
    m = matches.copy()
    m["home_pts"] = np.where(m["FTHG"] > m["FTAG"], 3,
                   np.where(m["FTHG"] == m["FTAG"], 1, 0))
    m["away_pts"] = np.where(m["FTAG"] > m["FTHG"], 3,
                   np.where(m["FTHG"] == m["FTAG"], 1, 0))

    home = m[["season", "HomeTeam", "home_pts"]].rename(
        columns={"HomeTeam": "team", "home_pts": "pts"})
    away = m[["season", "AwayTeam", "away_pts"]].rename(
        columns={"AwayTeam": "team", "away_pts": "pts"})
    tbl = pd.concat([home, away], ignore_index=True)
    tbl = tbl.groupby(["season", "team"])["pts"].sum().reset_index()
    tbl = tbl.sort_values(["season", "pts"], ascending=[True, False])
    tbl["pos"] = tbl.groupby("season")["pts"].rank(
        method="min", ascending=False).astype(int)

    titles = tbl[tbl["pos"] == 1].groupby("team").size().rename("titles")
    top4   = tbl[tbl["pos"] <= 4].groupby("team").size().rename("top4")
    return pd.concat([titles, top4], axis=1).fillna(0).astype(int)


# ══════════════════════════════════════════════════════════════════════
#  MAIN
# ══════════════════════════════════════════════════════════════════════
def main():
    print("=" * 74)
    print("  BEST ENGLISH TOP-FLIGHT TEAM OF ALL TIME")
    print("=" * 74)

    matches = load_matches(DATA_DIR)

    print("\n[1/3]  Results-only Elo...")
    pm_a, se_a, sp_a = run_elo(matches, goal_weight=False)
    sum_a = summarize_elo(pm_a, se_a, sp_a)

    print("[2/3]  Goal-difference Elo...")
    pm_b, se_b, sp_b = run_elo(matches, goal_weight=True)
    sum_b = summarize_elo(pm_b, se_b, sp_b)

    print("[3/4]  Bradley-Terry ML...")
    bt_df = run_bradley_terry(matches)
    sum_bt = summarize_bt(bt_df)
    print(f"       BT fit for {len(bt_df):,} teams")

    print("[4/4]  Achievements (titles & top-4)...")
    ach = summarize_achievements(matches)

    # ── Combine the two Elo structures first ──
    elo = pd.DataFrame({
        "peak":        (sum_a["peak"] + sum_b["peak"]) / 2,
        "best_season": (sum_a["best_season"] + sum_b["best_season"]) / 2,
        "avg":         (sum_a["avg"] + sum_b["avg"]) / 2,
        "matches":     sum_a["matches"],
        "seasons":     sum_a["seasons"],
    })
    elo["elo_score"] = (W_PEAK * minmax(elo["peak"]) +
                        W_BEST_SEASON * minmax(elo["best_season"]) +
                        W_AVG * minmax(elo["avg"]))

    # ── Merge BT in ──
    combined = elo.join(sum_bt, how="left").fillna({"bt_peak": 0, "bt_avg": 0})
    combined["bt_score"] = (BT_MAX_W * minmax(combined["bt_peak"]) +
                            BT_AVG_W * minmax(combined["bt_avg"]))

    # ── Merge achievements in ──
    combined = combined.join(ach, how="left").fillna({"titles": 0, "top4": 0})
    combined["ach_score"] = (
        0.7 * minmax(combined["titles"]) +
        0.3 * minmax(combined["top4"]))

    # ── Final score ──
    combined["score_10"] = (
        ELO_SHARE * combined["elo_score"] +
        BT_SHARE * combined["bt_score"] +
        ACH_SHARE * combined["ach_score"]) * 10

    # ── Filter and sort ──
    combined = combined[(combined["matches"] >= MIN_MATCHES) &
                        (combined["seasons"] >= MIN_SEASONS)]
    combined = combined.sort_values("score_10", ascending=False)

    # ── Report ──
    print("\n" + "=" * 74)
    print("  TOP 20 — COMBINED RANKING (score / 10)")
    print("=" * 74)
    show = combined.head(20)[
        ["score_10", "elo_score", "bt_score", "ach_score", "peak", "best_season",
         "avg", "matches", "seasons", "titles", "top4"]].round(2)
    show.columns = ["Score/10", "Elo", "BT", "Ach", "Peak Elo", "Best Season",
                    "Avg Elo", "Matches", "Seasons", "Titles", "Top-4"]
    print(show.to_string())

    # ── Best single season (interesting side-quest) ──
    print("\n" + "=" * 74)
    print("  TOP 10 BEST SINGLE SEASONS (Elo at season end)")
    print("=" * 74)
    bs = pd.DataFrame(
        [(t, s, r) for (s, t), r in se_b.items()],
        columns=["team", "season", "elo"]).nlargest(10, "elo")
    print(bs.to_string(index=False))

    # ── Save everything ──
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    combined.round(3).to_csv(OUTPUT_DIR / "all_time_ranking.csv")
    sum_a.round(3).to_csv(OUTPUT_DIR / "elo_results_only.csv")
    sum_b.round(3).to_csv(OUTPUT_DIR / "elo_goal_diff.csv")
    bt_df.round(3).to_csv(OUTPUT_DIR / "bradley_terry.csv")
    ach.round(3).to_csv(OUTPUT_DIR / "achievements.csv")
    print(f"\nResults saved to  {OUTPUT_DIR}")

    winner = combined.index[0]
    print(f"\n🏆 WINNER:  {winner}   —   {combined.iloc[0]['score_10']:.2f} / 10\n")


if __name__ == "__main__":
    main()