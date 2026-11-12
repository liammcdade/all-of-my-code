"""
draft_value_realization.py

Computes the Draft Value Realization (DVR) stat for every player in the
2023–2025 draft classes that appear in player_career_successes.csv.

Reads from / writes to:
    C:\\Users\\liam\\Pictures\\apple its glowtime\\iPhone 16\\nfl-big-data-bowl-2027
"""

from pathlib import Path
import pandas as pd
import numpy as np

# ---------------------------------------------------------------------------
# 0. Paths
# ---------------------------------------------------------------------------
BASE_DIR = Path(r"C:\Users\liam\Pictures\apple its glowtime\iPhone 16\nfl-big-data-bowl-2027")

if not BASE_DIR.exists():
    raise FileNotFoundError(f"Data folder not found: {BASE_DIR}")

REQUIRED_FILES = [
    "games.csv",
    "player_career_successes.csv",
    "players.csv",
    "combine_results.csv",
    "combine_tracking.csv",
]
missing = [f for f in REQUIRED_FILES if not (BASE_DIR / f).exists()]
if missing:
    raise FileNotFoundError(
        f"Missing file(s) in {BASE_DIR}:\n  " + "\n  ".join(missing)
    )

# ---------------------------------------------------------------------------
# 1. Load
# ---------------------------------------------------------------------------
games    = pd.read_csv(BASE_DIR / "games.csv")               # schedule context (not used in DVR directly)
careers  = pd.read_csv(BASE_DIR / "player_career_successes.csv")
players  = pd.read_csv(BASE_DIR / "players.csv")
combine  = pd.read_csv(BASE_DIR / "combine_results.csv")
tracking = pd.read_csv(BASE_DIR / "combine_tracking.csv")

# ---------------------------------------------------------------------------
# 2. Aggregate the raw tracking data (drill time-series) per player
#    Only the 2025 class has tracking data, so most players will be NaN here.
# ---------------------------------------------------------------------------
tracking_agg = (
    tracking.groupby("nfl_id")
            .agg(peak_speed=("s", "max"),
                 peak_accel=("a", "max"),
                 avg_speed =("s", "mean"),
                 n_events  =("event_id", "nunique"))
            .reset_index()
)

# ---------------------------------------------------------------------------
# 3. Merge player + career + combine + tracking
# ---------------------------------------------------------------------------
df = players.merge(careers, on="nfl_id", how="inner")
df = df.merge(combine, on="nfl_id", how="left", suffixes=("", "_combine"))
df = df.merge(tracking_agg, on="nfl_id", how="left")

# ---------------------------------------------------------------------------
# 4. Broad position grouping (so combine percentiles have meaningful samples)
# ---------------------------------------------------------------------------
POS_GROUPS = {
    "T":"OL","G":"OL","C":"OL","OL":"OL","OT":"OL","OG":"OL",
    "DE":"DL","DT":"DL","NT":"DL","DL":"DL",
    "OLB":"LB","ILB":"LB","MLB":"LB","LB":"LB",
    "CB":"DB","FS":"DB","SS":"DB","S":"DB","DB":"DB",
    "WR":"WR","TE":"TE","RB":"RB","FB":"RB","QB":"QB",
}
df["pos_group"] = df["nfl_position"].map(POS_GROUPS).fillna("OTHER")

# ---------------------------------------------------------------------------
# 5. Combine percentiles (within position group)
# ---------------------------------------------------------------------------
COMBINE_METRICS = {
    "forty":                 False,  # lower is better
    "vertical":              True,
    "broad_jump":            True,
    "three_cone":            False,
    "short_shuttle":         False,
    "bench_reps":            True,
    "ngs_athleticism_score": True,
}

def percentile_within_group(s: pd.Series, higher_better: bool) -> pd.Series:
    """Rank within the position group; fall back to 0.5 if group is tiny."""
    if s.notna().sum() < 5:
        return pd.Series(0.5, index=s.index)
    return s.rank(pct=True, ascending=higher_better)

pct_cols = []
for metric, higher_better in COMBINE_METRICS.items():
    col = f"{metric}_pct"
    df[col] = df.groupby("pos_group")[metric].transform(
        lambda s: percentile_within_group(s, higher_better)
    )
    pct_cols.append(col)

# Tracking percentiles (also within position group)
df["peak_speed_pct"] = df.groupby("pos_group")["peak_speed"].transform(
    lambda s: percentile_within_group(s, True)
)
df["peak_accel_pct"] = df.groupby("pos_group")["peak_accel"].transform(
    lambda s: percentile_within_group(s, True)
)

# ---------------------------------------------------------------------------
# 6. Athleticism composite
#    Combine portion  = mean of available combine percentiles
#    Tracking portion = mean of peak speed / acceleration percentiles
#    Combined         = 70% combine + 30% tracking (when tracking exists)
# ---------------------------------------------------------------------------
df["combine_ath"]  = df[pct_cols].mean(axis=1)
df["tracking_ath"] = df[["peak_speed_pct", "peak_accel_pct"]].mean(axis=1)

has_tracking = df["tracking_ath"].notna()
df["athleticism"] = np.where(
    has_tracking,
    0.7 * df["combine_ath"].fillna(0.5) + 0.3 * df["tracking_ath"].fillna(0.5),
    df["combine_ath"].fillna(0.5),   # neutral 0.5 if no combine data at all
)

# 7. Draft buckets + expected start rate per bucket (self-calibrating)
# ---------------------------------------------------------------------------
df["draft_bucket"] = pd.cut(
    df["draft_overall_pick"],
    bins=[0, 10, 32, 64, 100, 150, 200, 256],
    labels=["1-10","11-32","33-64","65-100","101-150","151-200","201-256"],
)
# Drop the categorical dtype so groupby/map behave like plain strings
df["draft_bucket"] = df["draft_bucket"].astype("string").fillna("UDFA")

df["start_rate"] = df["career_games_started"] / df["career_games_active"].clip(lower=1)

bucket_expected = df.groupby("draft_bucket")["start_rate"].mean()
df["expected_start_rate"] = (
    df["draft_bucket"].map(bucket_expected).astype(float).replace(0, 0.05)
)

# ---------------------------------------------------------------------------
# 8. Compose DVR
# ---------------------------------------------------------------------------
df["draft_perf_ratio"]  = df["start_rate"] / df["expected_start_rate"]
df["athleticism_mult"]  = 0.7 + 0.6 * df["athleticism"]
df["honors_mult"] = (
    1
    + 0.50 * df["ap_all_pro_1st_team"].fillna(0)
    + 0.25 * df["ap_all_pro_2nd_team"].fillna(0)
    + 0.10 * df["pro_bowl_original_ballot"].fillna(0)
)
df["DVR"] = df["draft_perf_ratio"] * df["athleticism_mult"] * df["honors_mult"]

# ---------------------------------------------------------------------------
# 9. Report
# ---------------------------------------------------------------------------
scored = df[df["DVR"].notna()].copy()

print("=" * 78)
print(" DRAFT VALUE REALIZATION (DVR)")
print("=" * 78)
print(f"Data dir                 : {BASE_DIR}")
print(f"Players scored           : {len(scored)}")
print(f"Mean DVR                 : {scored['DVR'].mean():.3f}")
print(f"Median DVR               : {scored['DVR'].median():.3f}")
print(f"Players with tracking    : {scored['tracking_ath'].notna().sum()} (2025 class only)")
print()

out_cols = ["display_name", "nfl_position", "draft_year", "draft_overall_pick",
            "career_games_started", "career_games_active",
            "draft_perf_ratio", "athleticism", "honors_mult", "DVR"]

print("TOP 20 — biggest value over draft + athletic expectation")
print(scored.nlargest(20, "DVR")[out_cols].to_string(index=False))
print()
print("BOTTOM 20 — biggest value shortfall")
print(scored.nsmallest(20, "DVR")[out_cols].to_string(index=False))

# Save full table back into the data folder
OUT_PATH = BASE_DIR / "dvr_results.csv"
scored.sort_values("DVR", ascending=False).to_csv(OUT_PATH, index=False)
print(f"\nFull results written to {OUT_PATH}")