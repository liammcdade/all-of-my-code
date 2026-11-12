"""
2026 F1 Las Vegas Grand Prix — Full-Weekend Forecast
=====================================================
Qualifying + Race simulation from a flat Kaggle folder.

Sessions modelled
-----------------
  * Main qualifying (Bradley–Terry Elo)
  * Sprint qualifying / sprint grid (Bradley–Terry Elo)
  * Race pace (from lap_times median per driver)
  * Race results (from finishing positions)
  * Night-race qualifying form
  * Las Vegas-specific qualifying history
  * Wet-specialist delta (applied with RAIN_PROB)
  * Two-way car / driver decomposition
  * Teammate head-to-head skill
  * FULL RACE SIMULATION (laps, pit stops, safety cars, DNFs)

Output policy
-------------
All textual output is buffered in _OUTPUT. Only the tqdm progress
bars are shown live. The full report is flushed at the very end.
"""

from __future__ import annotations

import shutil
import sys as _sys
import unicodedata
from collections import defaultdict
from pathlib import Path

try:
    _sys.stdout.reconfigure(encoding="utf-8")
    _sys.stderr.reconfigure(encoding="utf-8")
except (AttributeError, ValueError):
    pass

import numpy as np
import pandas as pd

try:
    from tqdm import tqdm
    _HAS_TQDM = True
except ImportError:
    _HAS_TQDM = False

# ======================= OUTPUT BUFFER =======================
QUIET = False
_OUTPUT: list[str] = []


def _p(msg):
    if QUIET:
        return
    _OUTPUT.append(str(msg))


def _flush():
    """Print everything that was buffered during the run."""
    if _OUTPUT:
        print("\n".join(_OUTPUT))
        _OUTPUT.clear()


# ======================= PROGRESS BAR HELPERS =======================
def _bar(total, desc, position=0, leave=True):
    """Create a tqdm bar, or a no-op fallback."""
    if _HAS_TQDM:
        return tqdm(
            total=total, desc=desc, position=position, leave=leave,
            bar_format="{desc}: {percentage:3.0f}%|{bar:40}| {n_fmt}/{total_fmt} [{elapsed}<{remaining}]",
            dynamic_ncols=True,
        )

    class _FakeBar:
        def __init__(self, **kw):
            self.total = kw.get("total", 100)
            self.n = 0
            self.desc = kw.get("desc", "")

        def update(self, n=1):
            self.n += n

        def set_description(self, d):
            self.desc = d

        def close(self):
            pass

        def __enter__(self):
            return self

        def __exit__(self, *a):
            pass

    return _FakeBar(total=total, desc=desc)


# ======================= CONFIG =======================
USE_KAGGLE          = True
KAGGLE_HANDLE       = "jtrotman/formula-1-race-data"
RACE_DATA_DIR       = Path("./race_data")
N_SIMS              = 60_000
CHUNK               = 5_000
RNG_SEED            = 2026

# --- Las Vegas ---
LAS_VEGAS_CIRCUIT_ID = 80
RAIN_PROB            = 0.01
NIGHT_RACE_CIRCUITS  = {3, 15, 24, 77, 78, 80, 73, 79}
VEGAS_HISTORY_YEARS  = 3
RACE_LAPS            = 50  # Vegas GP distance

# --- Quali noise ---
ELO_NOISE_SCALE       = 55.0
HIGH_VARIANCE_PROB    = 0.05
HIGH_VARIANCE_MULT    = 2.0
WET_VARIANCE_SPIKE    = 2.0

# --- Model weights (qualifying focus) ---
W_TWO_WAY           = 0.30
W_SESSION_QUALI     = 0.20
W_SPRINT_QUALI      = 0.15
W_RACE_PACE         = 0.15
W_H2H               = 0.10
W_NIGHT_QUALI       = 0.05
W_VEGAS_TRACK       = 0.05

# --- Elo params ---
QUALI_SHRINK_K      = 10
QUALI_SKILL_SCALE   = 120.0
QUALI_ELO_K         = 12.0
QUALI_ELO_HALF_LIFE = 20.0
QUALI_MIN_SESSIONS  = 3
TWO_WAY_HALF_LIFE   = 30
H2H_HALF_LIFE       = 60
RACE_PACE_HALF_LIFE = 30
RACE_RESULTS_HALF_LIFE = 30

# --- Two-way shrinkage & sigma guards ---
MIN_SESSIONS_FOR_TWO_WAY = 3
TWO_WAY_SHRINK_K_DRIVER  = 10
TWO_WAY_SHRINK_K_CAR     = 20
SIGMA_FLOOR              = 0.5
SIGMA_POST_FLOOR         = 0.6
SIGMA_POST_CEIL          = 2.5
ELO_CLIP_SIGMA           = 2.5

# --- Wet detection ---
WET_DRY_BENCHMARK_SLOWDOWN = 1.08
WET_MIN_TOPN               = 10
WET_ELO_PER_MS             = 0.2

# --- Race simulation (retuned) ---
RACE_DNF_DRY      = 0.06        # fallback only
RACE_DNF_WET      = 0.12        # fallback only
RACE_SC_DRY       = 0.35
RACE_SC_WET       = 0.60
RACE_NOISE_DRY    = 2.0
RACE_NOISE_WET    = 4.0
RACE_PIT_STD_DRY  = 2.0
RACE_PIT_STD_WET  = 4.0
RACE_TRACK_FACTOR_DRY = 0.30
RACE_TRACK_FACTOR_WET = 0.20
RACE_ELO_PACE_W   = 0.70
RACE_ELO_POS_W    = 0.30
RACE_PACE_SPREAD_SEC = 38.0  # std of pace delta across field, seconds
RACE_GRID_NOISE_STD  = 0.7   # position std for starting-grid jitter2.

# --- DNF modelling ---
DNF_HALF_LIFE        = 30.0     # races; reliability trends faster than pace
DNF_SHRINK_K_DRIVER  = 5.0      # driver excess shrinks to car rate
DNF_SHRINK_K_CAR     = 10.0     # car rate shrinks to field mean
DNF_MIN_SAMPLES_DRV  = 3
DNF_MIN_SAMPLES_CAR  = 3
DNF_FLOOR            = 0.02     # no driver more reliable than 2 %
DNF_CEIL             = 0.30     # no driver above 30 % dry
DNF_WET_FLOOR_MULT   = 1.2
DNF_WET_CEIL_MULT    = 2.5
FILENAME_CANDIDATES = {
    "drivers":      ["drivers.csv", "Drivers.csv"],
    "constructors": ["constructors.csv", "Constructors.csv"],
    "circuits":     ["circuits.csv", "Circuits.csv"],
    "races":        ["races.csv", "Races.csv"],
    "results":      ["results.csv", "Results.csv"],
    "qualifying":   ["qualifying.csv", "Qualifying.csv"],
    "sprint":       ["sprint_results.csv", "SprintResults.csv"],
    "lap_times":    ["lap_times.csv", "LapTimes.csv"],
}


# ======================= KAGGLE SYNC =======================
def sync_kaggle_flat():
    if not USE_KAGGLE:
        _p(f"Using existing flat folder: {RACE_DATA_DIR}")
        return RACE_DATA_DIR

    try:
        import kagglehub
    except ImportError:
        _p("! kagglehub not installed — using existing race_data/")
        return RACE_DATA_DIR

    try:
        cached = Path(kagglehub.dataset_download(KAGGLE_HANDLE))
    except Exception as e:
        _p(f"! kagglehub download failed ({type(e).__name__}: {e})")
        _p(f"  Falling back to existing {RACE_DATA_DIR}/")
        return RACE_DATA_DIR

    version = cached.name
    marker = RACE_DATA_DIR / ".version"

    if RACE_DATA_DIR.exists() and marker.exists() and marker.read_text().strip() == version:
        _p(f"race_data/ already at v{version} — no copy needed")
        return RACE_DATA_DIR

    RACE_DATA_DIR.mkdir(parents=True, exist_ok=True)
    csvs = list(cached.glob("*.csv"))
    if not csvs:
        _p(f"! No CSVs found in cached path {cached}")
        return RACE_DATA_DIR

    for f in csvs:
        shutil.copy2(f, RACE_DATA_DIR / f.name)
    marker.write_text(version)
    _p(f"race_data/ synced to v{version} ({len(csvs)} CSV files)")
    return RACE_DATA_DIR


# ======================= LOADING =======================
def _camelize(df):
    rename = {}
    for c in df.columns:
        if "_" in c and c[0].islower():
            parts = c.split("_")
            new = parts[0] + "".join(p.capitalize() for p in parts[1:])
            if new not in df.columns:
                rename[c] = new
    return df.rename(columns=rename) if rename else df


def load_datasets():
    data_dir = sync_kaggle_flat()
    _p(f"\nReading flat files from: {data_dir}")

    out = {}
    for table, cands in FILENAME_CANDIDATES.items():
        path = None
        for c in cands:
            p = data_dir / c
            if p.exists():
                path = p
                break
        if path is None:
            continue
        out[table] = _camelize(pd.read_csv(path))
        _p(f"  ok {table:<18s} {len(out[table]):>8,} rows  ({path.name})")

    if "qualifying" not in out:
        raise SystemExit("Need qualifying.csv in race_data/")
    if "sprint" not in out:
        _p("  ! sprint_results.csv not present — sprint Elo disabled")
    if "lap_times" not in out:
        _p("  ! lap_times.csv not present — race-pace Elo disabled")
    return out


# ======================= HELPERS =======================
def _race_weights(race_ids, half_life):
    if len(race_ids) == 0:
        return {}
    n = len(race_ids)
    w = 0.5 ** np.arange(n - 1, -1, -1) / half_life
    return {int(r): float(x) for r, x in zip(race_ids, w)}


def _bt_elo(pair_tuples, half_life, k=10.0, scale=400.0):
    elo = defaultdict(lambda: 1500.0)
    for w_id, l_id, wt in pair_tuples:
        ea = 1.0 / (1.0 + 10.0 ** ((elo[l_id] - elo[w_id]) / scale))
        elo[w_id] += k * wt * (1.0 - ea)
        elo[l_id] += k * wt * (0.0 - (1.0 - ea))
    return {int(k): float(v) for k, v in elo.items()}


# ======================= QUALIFYING DATA =======================
def build_quali_data(data):
    q = data["qualifying"].copy()
    races = data["races"]
    for col in ("raceId", "driverId", "constructorId"):
        if col in q.columns:
            q[col] = pd.to_numeric(q[col], errors="coerce")
    q = q.dropna(subset=["raceId", "driverId", "constructorId"])

    def _parse(s):
        if pd.isna(s):
            return np.nan
        s = str(s).strip()
        if not s or s in ("\\N", "N", "nan"):
            return np.nan
        try:
            parts = s.split(":")
            if len(parts) == 2:
                return float(parts[0]) * 60000.0 + float(parts[1]) * 1000.0
            return float(s) * 1000.0
        except (ValueError, TypeError):
            return np.nan

    for sess in ("q1", "q2", "q3"):
        q[sess] = q[sess].apply(_parse) if sess in q.columns else np.nan

    records = []
    for (rid, did, cid), grp in q.groupby(["raceId", "driverId", "constructorId"]):
        q1, q2, q3 = grp["q1"].dropna().min(), grp["q2"].dropna().min(), grp["q3"].dropna().min()
        if not pd.isna(q3):
            sess, t = 3, q3
        elif not pd.isna(q2):
            sess, t = 2, q2
        elif not pd.isna(q1):
            sess, t = 1, q1
        else:
            continue
        records.append({"raceId": int(rid), "driverId": int(did),
                        "constructorId": int(cid), "session": sess,
                        "time_ms": t, "q1_time_ms": q1})
    qdf = pd.DataFrame(records)
    if qdf.empty:
        return None
    qdf = qdf.merge(races[["raceId", "year", "circuitId", "round"]], on="raceId", how="left")

    qdf = qdf.sort_values(["raceId", "session", "time_ms"]).reset_index(drop=True)
    qdf["session_best"] = qdf.groupby(["raceId", "session"])["time_ms"].transform("min")
    qdf["delta_to_best"] = qdf["time_ms"] - qdf["session_best"]

    qdf["median_ms"] = qdf.groupby(["raceId", "session"])["time_ms"].transform("median")
    circ_all = qdf.groupby("circuitId")["time_ms"].median()
    qdf["circ_median"] = qdf["circuitId"].map(circ_all)
    dry_mask = qdf["median_ms"] <= qdf["circ_median"] * 2.5
    dry_qdf = qdf[dry_mask]
    circ_dry = dry_qdf.groupby("circuitId")["time_ms"].median()

    wet_by_slow = set()
    for (rid, cid, sess), med in qdf.groupby(["raceId", "circuitId", "session"])["median_ms"].first().items():
        bench = circ_dry.get(cid)
        if pd.isna(bench) or bench <= 0:
            continue
        if med / bench > WET_DRY_BENCHMARK_SLOWDOWN:
            wet_by_slow.add((rid, sess))

    circ_dry_std = {}
    for (rid, sess), grp in dry_qdf.groupby(["raceId", "session"]):
        if len(grp) < WET_MIN_TOPN:
            continue
        cid = grp["circuitId"].iloc[0]
        circ_dry_std.setdefault(cid, []).append(grp.nsmallest(WET_MIN_TOPN, "time_ms")["time_ms"].std())
    circ_typ_std = {c: float(np.median(v)) for c, v in circ_dry_std.items() if v}

    wet_by_var = set()
    for (rid, sess), grp in qdf.groupby(["raceId", "session"]):
        if len(grp) < WET_MIN_TOPN:
            continue
        cid = grp["circuitId"].iloc[0]
        typ = circ_typ_std.get(cid, 0.0)
        if typ <= 0:
            continue
        std = grp.nsmallest(WET_MIN_TOPN, "time_ms")["time_ms"].std()
        if std / typ > WET_VARIANCE_SPIKE:
            wet_by_var.add((rid, sess))

    qdf["wet"] = False
    for idx in qdf.index:
        key = (int(qdf.at[idx, "raceId"]), int(qdf.at[idx, "session"]))
        if key in wet_by_slow or key in wet_by_var:
            qdf.at[idx, "wet"] = True

    _p(f"    {len(qdf):,} quali entries | wet races: {qdf[qdf['wet']]['raceId'].nunique()}")
    return qdf


# ======================= SESSION ELO BUILDERS =======================
def build_quali_elo(qdf):
    if qdf is None or qdf.empty:
        return {}
    races = sorted(qdf["raceId"].unique())
    n_r = len(races)
    rw = {r: 0.5 ** ((n_r - 1 - i) / QUALI_ELO_HALF_LIFE) for i, r in enumerate(races)}

    pairs = []
    for rid, grp in qdf.groupby("raceId"):
        w = rw[rid]
        valid = grp[grp["delta_to_best"].notna()]
        for sess, sg in valid.groupby("session"):
            sg = sg.sort_values("delta_to_best").reset_index(drop=True)
            drv = sg["driverId"].values.astype(int)
            for i in range(len(drv)):
                for j in range(i + 1, len(drv)):
                    pairs.append((drv[i], drv[j], w))
    elo = _bt_elo(pairs, QUALI_ELO_HALF_LIFE, k=QUALI_ELO_K)
    _p(f"    quali Elo: {len(elo)} drivers")
    return elo


def build_sprint_quali_elo(data):
    if "sprint" not in data or data["sprint"].empty:
        return {}
    s = data["sprint"].copy()
    s["raceId"] = pd.to_numeric(s["raceId"], errors="coerce")
    s["driverId"] = pd.to_numeric(s["driverId"], errors="coerce")
    s = s.dropna(subset=["raceId", "driverId"])
    if "grid" not in s.columns:
        _p("    sprint_results has no grid column — sprint Elo disabled")
        return {}
    s["grid"] = pd.to_numeric(s["grid"], errors="coerce")
    s = s[(s["grid"] > 0) & s["grid"].notna()].copy()
    s["driverId"] = s["driverId"].astype(int)
    if s.empty:
        return {}

    races = sorted(s["raceId"].unique())
    rw = _race_weights(np.array(races), QUALI_ELO_HALF_LIFE)
    pairs = []
    for rid, grp in s.groupby("raceId"):
        w = rw.get(int(rid), 1.0)
        grp = grp.sort_values("grid").reset_index(drop=True)
        drv = grp["driverId"].values.astype(int)
        for i in range(len(drv)):
            for j in range(i + 1, len(drv)):
                pairs.append((drv[i], drv[j], w))
    elo = _bt_elo(pairs, QUALI_ELO_HALF_LIFE, k=QUALI_ELO_K)
    _p(f"    sprint Elo: {len(elo)} drivers from {s['raceId'].nunique()} sprints")
    return elo


def build_race_pace_elo(data):
    if "lap_times" not in data or data["lap_times"].empty:
        return {}
    lt = data["lap_times"].copy()
    lt["raceId"] = pd.to_numeric(lt["raceId"], errors="coerce")
    lt["driverId"] = pd.to_numeric(lt["driverId"], errors="coerce")
    lt["milliseconds"] = pd.to_numeric(lt["milliseconds"], errors="coerce")
    lt = lt.dropna(subset=["raceId", "driverId", "milliseconds"])
    if lt.empty:
        return {}

    grp_med = lt.groupby(["raceId", "driverId"])["milliseconds"].transform("median")
    lt = lt[lt["milliseconds"] <= grp_med * 1.15]

    pace = (lt.groupby(["raceId", "driverId"])["milliseconds"]
              .median().reset_index())
    races = sorted(pace["raceId"].unique())
    rw = _race_weights(np.array(races), RACE_PACE_HALF_LIFE)
    pairs = []
    for rid, g in pace.groupby("raceId"):
        w = rw.get(int(rid), 1.0)
        g = g.sort_values("milliseconds").reset_index(drop=True)
        drv = g["driverId"].astype(int).values
        for i in range(len(drv)):
            for j in range(i + 1, len(drv)):
                pairs.append((drv[i], drv[j], w))
    elo = _bt_elo(pairs, RACE_PACE_HALF_LIFE, k=8.0)
    _p(f"    race-pace Elo: {len(elo)} drivers from {pace['raceId'].nunique()} races")
    return elo


def build_race_results_elo(data):
    """Bradley-Terry Elo from race finishing positions."""
    if "results" not in data or data["results"].empty:
        return {}
    r = data["results"].copy()
    r["raceId"] = pd.to_numeric(r["raceId"], errors="coerce")
    r["driverId"] = pd.to_numeric(r["driverId"], errors="coerce")

    pos_col = None
    for c in ("positionOrder", "position", "positionText"):
        if c in r.columns:
            pos_col = c
            break
    if pos_col is None:
        return {}
    r["_pos"] = pd.to_numeric(r[pos_col], errors="coerce")
    r = r.dropna(subset=["raceId", "driverId", "_pos"])
    r = r[r["_pos"] > 0]
    if r.empty:
        return {}

    races = sorted(r["raceId"].unique())
    rw = _race_weights(np.array(races), RACE_RESULTS_HALF_LIFE)
    pairs = []
    for rid, grp in r.groupby("raceId"):
        w = rw.get(int(rid), 1.0)
        grp = grp.sort_values("_pos").reset_index(drop=True)
        drv = grp["driverId"].astype(int).values
        for i in range(len(drv)):
            for j in range(i + 1, len(drv)):
                pairs.append((drv[i], drv[j], w))
    elo = _bt_elo(pairs, RACE_RESULTS_HALF_LIFE, k=6.0)
    _p(f"    race-results Elo: {len(elo)} drivers from {r['raceId'].nunique()} races")
    return elo


def build_night_quali_elo(qdf):
    if qdf is None or qdf.empty:
        return {}
    sub = qdf[qdf["circuitId"].isin(NIGHT_RACE_CIRCUITS)]
    if sub.empty:
        return {}
    races = sorted(sub["raceId"].unique())
    rw = _race_weights(np.array(races), QUALI_ELO_HALF_LIFE)
    pairs = []
    for rid, grp in sub.groupby("raceId"):
        w = rw.get(int(rid), 1.0)
        valid = grp[grp["delta_to_best"].notna()]
        for sess, sg in valid.groupby("session"):
            sg = sg.sort_values("delta_to_best").reset_index(drop=True)
            drv = sg["driverId"].astype(int).values
            for i in range(len(drv)):
                for j in range(i + 1, len(drv)):
                    pairs.append((drv[i], drv[j], w))
    elo = _bt_elo(pairs, QUALI_ELO_HALF_LIFE, k=QUALI_ELO_K)
    _p(f"    night-quali Elo: {len(elo)} drivers")
    return elo


# ======================= TWO-WAY =======================
def build_two_way_decomposition(qdf):
    if qdf is None or qdf.empty:
        return {}, {}, {}
    entries = qdf[["raceId", "driverId", "constructorId", "session", "time_ms"]].copy()
    entries = entries[entries["time_ms"].notna()]
    entries["driverId"] = entries["driverId"].astype(int)
    entries["constructorId"] = entries["constructorId"].astype(int)
    if entries.empty:
        return {}, {}, {}

    races_sorted = sorted(entries["raceId"].unique())
    rw = _race_weights(np.array(races_sorted), TWO_WAY_HALF_LIFE)

    pairs = []
    for (rid, sess), grp in entries.groupby(["raceId", "session"]):
        w = rw.get(int(rid), 1.0)
        for _, r1 in grp.iterrows():
            for _, r2 in grp.iterrows():
                if r1["driverId"] == r2["driverId"]:
                    continue
                pairs.append((int(r1["driverId"]), int(r2["driverId"]),
                              int(r1["constructorId"]), int(r2["constructorId"]),
                              r1["time_ms"] - r2["time_ms"], w))
    if not pairs:
        return {}, {}, {}

    pair_df = pd.DataFrame(pairs, columns=["d1", "d2", "c1", "c2", "gap", "w"])
    dids = sorted(set(pair_df["d1"]) | set(pair_df["d2"]))
    cids = sorted(set(pair_df["c1"]) | set(pair_df["c2"]))
    d2i = {d: i for i, d in enumerate(dids)}
    c2i = {c: i for i, c in enumerate(cids)}
    n_d, n_c = len(dids), len(cids)

    d1i = pair_df["d1"].map(d2i).values
    d2i_ = pair_df["d2"].map(d2i).values
    c1i = pair_df["c1"].map(c2i).values
    c2i_ = pair_df["c2"].map(c2i).values
    gap = pair_df["gap"].values
    w = pair_df["w"].values
    n_p = len(pair_df)

    driver_elo = np.zeros(n_d)
    car_elo = np.zeros(n_c)
    reg = 1.0
    for it in range(100):
        car_gap = car_elo[c1i] - car_elo[c2i_]
        y = gap - car_gap
        XtX = np.zeros((n_d, n_d))
        Xty = np.zeros(n_d)
        for i in range(n_p):
            wi, a, b = w[i], d1i[i], d2i_[i]
            XtX[a, a] += wi + reg
            XtX[b, b] += wi + reg
            XtX[a, b] -= wi
            XtX[b, a] -= wi
            Xty[a] += wi * y[i]
            Xty[b] -= wi * y[i]
        try:
            beta_d = np.linalg.solve(XtX, Xty)
        except np.linalg.LinAlgError:
            beta_d = np.zeros(n_d)
        new_d = beta_d - beta_d.mean()

        driver_gap = new_d[d1i] - new_d[d2i_]
        y = gap - driver_gap
        XtX = np.zeros((n_c, n_c))
        Xty = np.zeros(n_c)
        for i in range(n_p):
            wi, a, b = w[i], c1i[i], c2i_[i]
            XtX[a, a] += wi + reg
            XtX[b, b] += wi + reg
            XtX[a, b] -= wi
            XtX[b, a] -= wi
            Xty[a] += wi * y[i]
            Xty[b] -= wi * y[i]
        try:
            beta_c = np.linalg.solve(XtX, Xty)
        except np.linalg.LinAlgError:
            beta_c = np.zeros(n_c)
        new_c = beta_c - beta_c.mean()

        dd = np.max(np.abs(new_d - driver_elo))
        cd = np.max(np.abs(new_c - car_elo))
        driver_elo, car_elo = new_d, new_c
        if dd < 1.0 and cd < 1.0:
            break

    def _safe_scale(v, tgt=300.0):
        s = v.std()
        return np.zeros_like(v) if s < 1e-9 else v / s * tgt

    n_sess_drv = entries.groupby("driverId").size().to_dict()
    n_sess_car = entries.groupby("constructorId").size().to_dict()

    scaled_driver = _safe_scale(driver_elo)
    scaled_car = _safe_scale(car_elo)

    driver_q = {}
    for d, v in zip(dids, scaled_driver):
        n = int(n_sess_drv.get(int(d), 0))
        if n < MIN_SESSIONS_FOR_TWO_WAY:
            driver_q[int(d)] = 1500.0
        else:
            shrink = n / (n + TWO_WAY_SHRINK_K_DRIVER)
            driver_q[int(d)] = float(1500.0 - v * shrink)

    car_q = {}
    for c, v in zip(cids, scaled_car):
        n = int(n_sess_car.get(int(c), 0))
        if n < MIN_SESSIONS_FOR_TWO_WAY:
            car_q[int(c)] = 1500.0
        else:
            shrink = n / (n + TWO_WAY_SHRINK_K_CAR)
            car_q[int(c)] = float(1500.0 - v * shrink)

    entries = entries.copy()
    entries["d2b"] = (entries["time_ms"]
                      - entries.groupby(["raceId", "session"])["time_ms"].transform("min"))
    spread = (entries.groupby(["raceId", "session"])["d2b"]
                    .transform("std").replace(0, 1.0).fillna(1.0))
    entries["d2b_norm"] = entries["d2b"] / spread

    sigma = {}
    for did, g in entries.groupby("driverId"):
        if len(g) < MIN_SESSIONS_FOR_TWO_WAY:
            sigma[int(did)] = 1.0
            continue
        s = g["d2b_norm"].std()
        sigma[int(did)] = float(s) if pd.notna(s) and s >= 0.05 else 1.0

    _p(f"    two-way: {len(driver_q)} drivers, {len(car_q)} teams, "
       f"{len(sigma)} variances "
       f"(shrunk K_drv={TWO_WAY_SHRINK_K_DRIVER}, K_car={TWO_WAY_SHRINK_K_CAR})")
    return car_q, driver_q, sigma


# ======================= H2H =======================
def build_teammate_h2h(qdf, min_sessions=QUALI_MIN_SESSIONS):
    if qdf is None or qdf.empty:
        return {}, {}
    wins = defaultdict(float)
    n_comp = defaultdict(float)
    for rid, rgrp in qdf.groupby("raceId"):
        for cid, cgrp in rgrp.groupby("constructorId"):
            ds = cgrp["driverId"].unique()
            if len(ds) < 2:
                continue
            d1, d2 = ds[0], ds[1]
            t1 = cgrp[cgrp["driverId"] == d1]["q1_time_ms"].iloc[0]
            t2 = cgrp[cgrp["driverId"] == d2]["q1_time_ms"].iloc[0]
            if pd.isna(t1) or pd.isna(t2):
                continue
            n_comp[d1] += 1.0
            n_comp[d2] += 1.0
            if t1 < t2:
                wins[d1] += 1.0
            elif t2 < t1:
                wins[d2] += 1.0
    skill = {}
    for d in n_comp:
        n = n_comp[d]
        if n < min_sessions:
            continue
        wr = np.clip((wins[d] + 0.5) / (n + 1), 1e-6, 1 - 1e-6)
        logit = np.log(wr / (1 - wr))
        alpha = n / (n + QUALI_SHRINK_K)
        skill[int(d)] = float(1500.0 + QUALI_SKILL_SCALE * alpha * logit)
    _p(f"    H2H: {len(skill)} drivers")
    return skill, {int(d): wins[d] / max(n_comp[d], 1) for d in n_comp}


# ======================= WET & VEGAS =======================
def build_wet_specialists(qdf):
    if qdf is None or qdf.empty:
        return {}
    wet = qdf[qdf["wet"]]
    dry = qdf[~qdf["wet"]]
    if wet.empty:
        return {}
    wp = wet.groupby("driverId")["delta_to_best"].median()
    dp = dry.groupby("driverId")["delta_to_best"].median()
    common = wp.index.intersection(dp.index)
    return {int(d): float((dp[d] - wp[d]) * WET_ELO_PER_MS) for d in common}


def build_vegas_history(qdf, races):
    if qdf is None or qdf.empty:
        return {}
    max_year = int(races["year"].max())
    rids = races[(races["circuitId"] == LAS_VEGAS_CIRCUIT_ID)
                 & (races["year"] >= max_year - VEGAS_HISTORY_YEARS)]["raceId"]
    v = qdf[qdf["raceId"].isin(rids)]
    if v.empty:
        return {}
    out = {}
    for did, g in v.groupby("driverId"):
        per_race = g.groupby("raceId").apply(
            lambda x: -x["delta_to_best"].mean(), include_groups=False)
        if len(per_race) == 0:
            continue
        out[int(did)] = float(np.clip(per_race.mean() * 0.05, -40.0, 40.0))
    _p(f"    Vegas history: {len(out)} drivers")
    return out


# ======================= DNF RATES =======================
def build_dnf_rates(data, qdf=None, half_life=DNF_HALF_LIFE):
    """
    Build per-driver and per-constructor DNF rates from race history.

    Decomposition
    -------------
      * Constructor base rate   — mechanical + team errors, recency-weighted,
                                  shrunk toward field mean (K_DNF_CAR)
      * Driver "excess"          — (driver DNF rate − their historical car mean),
                                  recency-weighted, shrunk toward 0 (K_DNF_DRIVER)
      * Wet multiplier           — computed from wet-race history if available,
                                  otherwise conservative 1.8×

    Using *excess* rather than a raw rate means a driver who switches teams
    inherits their **new** car's reliability, modulated by their own crash
    tendency. Hamilton at Ferrari = Ferrari-rate + Hamilton-excess.

    Returns
    -------
      car_base      : dict[constructorId -> float]
      driver_excess : dict[driverId      -> float]   (can be negative)
      wet_mult      : float
      field_mean    : float
    """
    empty = ({}, {}, 1.8, 0.06)
    if "results" not in data or data["results"].empty:
        _p("    ! results.csv missing — DNF falls back to flat rate")
        return empty

    r = data["results"].copy()
    for c in ("raceId", "driverId", "constructorId"):
        if c in r.columns:
            r[c] = pd.to_numeric(r[c], errors="coerce")
    r = r.dropna(subset=["raceId", "driverId", "constructorId"]).copy()
    if r.empty:
        return empty
    r["driverId"]      = r["driverId"].astype(int)
    r["constructorId"] = r["constructorId"].astype(int)
    r["raceId"]        = r["raceId"].astype(int)

    # --- DNF flag ---
    if "positionText" in r.columns:
        marks = {"R", "D", "E", "W", "N", "F"}
        pt = r["positionText"].astype(str).str.strip().str.upper()
        r["dnf"] = pt.isin(marks).astype(float)
    else:
        pos = pd.to_numeric(
            r.get("positionOrder", r.get("position", pd.Series(np.nan, index=r.index))),
            errors="coerce",
        )
        r["dnf"] = pos.isna().astype(float)

    # --- Recency weights (one per raceId) ---
    race_ids = sorted(r["raceId"].unique())
    n_r = len(race_ids)
    idx_of = {rid: i for i, rid in enumerate(race_ids)}
    r["_idx"] = r["raceId"].map(idx_of)
    r["_w"]   = 0.5 ** ((n_r - 1 - r["_idx"]) / half_life)

    w_all = max(float(r["_w"].sum()), 1e-9)
    field_mean = float((r["dnf"] * r["_w"]).sum() / w_all)

    # --- Constructor base rate ---
    car_grp = r.groupby("constructorId").apply(
        lambda g: pd.Series({
            "num": float((g["dnf"] * g["_w"]).sum()),
            "den": float(g["_w"].sum()),
            "n":   len(g),
        }),
        include_groups=False,
    )
    car_raw = (car_grp["num"] / car_grp["den"].clip(lower=1e-9)).to_dict()
    car_n   = car_grp["n"].to_dict()

    car_base: dict[int, float] = {}
    for cid, raw in car_raw.items():
        n = float(car_n.get(cid, 0.0))
        if n < DNF_MIN_SAMPLES_CAR:
            car_base[int(cid)] = field_mean
            continue
        shrink = n / (n + DNF_SHRINK_K_CAR)
        car_base[int(cid)] = float(field_mean + shrink * (raw - field_mean))

    # --- Driver excess over their historical car mean ---
    r["_car_base"] = (
        r["constructorId"].map(car_base).astype(float).fillna(field_mean)
    )
    drv_grp = r.groupby("driverId").apply(
        lambda g: pd.Series({
            "num":      float((g["dnf"] * g["_w"]).sum()),
            "den":      float(g["_w"].sum()),
            "car_mean": float((g["_car_base"] * g["_w"]).sum() / max(float(g["_w"].sum()), 1e-9)),
            "n":        len(g),
        }),
        include_groups=False,
    )
    drv_raw      = (drv_grp["num"] / drv_grp["den"].clip(lower=1e-9)).to_dict()
    drv_car_mean = drv_grp["car_mean"].to_dict()
    drv_n        = drv_grp["n"].to_dict()

    driver_excess: dict[int, float] = {}
    for did, raw in drv_raw.items():
        n = float(drv_n.get(did, 0.0))
        if n < DNF_MIN_SAMPLES_DRV:
            driver_excess[int(did)] = 0.0
            continue
        excess = raw - drv_car_mean.get(did, field_mean)
        shrink = n / (n + DNF_SHRINK_K_DRIVER)
        driver_excess[int(did)] = float(excess * shrink)

    # --- Wet multiplier from history ---
    wet_rids: set[int] = set()
    if qdf is not None and not qdf.empty and "wet" in qdf.columns:
        wet_rids = {int(x) for x in qdf.loc[qdf["wet"], "raceId"].unique()}

    wet_mult = 1.8
    if len(wet_rids) >= 3:
        wet_mask = r["raceId"].isin(wet_rids)
        dry_mask = ~wet_mask
        wr = float((r.loc[wet_mask, "dnf"] * r.loc[wet_mask, "_w"]).sum()
                   / max(float(r.loc[wet_mask, "_w"].sum()), 1e-9))
        dr = float((r.loc[dry_mask, "dnf"] * r.loc[dry_mask, "_w"]).sum()
                   / max(float(r.loc[dry_mask, "_w"].sum()), 1e-9))
        if dr > 0.005 and wr > dr:
            wet_mult = float(np.clip(wr / dr, DNF_WET_FLOOR_MULT, DNF_WET_CEIL_MULT))

    car_vals = list(car_base.values())
    exc_vals = list(driver_excess.values())
    _p(f"    DNF: field={field_mean*100:.2f}%, wet_mult={wet_mult:.2f}×, "
       f"cars={len(car_base)} "
       f"(range {min(car_vals)*100:.1f}–{max(car_vals)*100:.1f}%), "
       f"driver excesses={len(driver_excess)} "
       f"(range {min(exc_vals)*100:+.1f}–{max(exc_vals)*100:+.1f}pp)")

    return car_base, driver_excess, wet_mult, field_mean


# ======================= CURRENT GRID =======================
F1_2026_GRID: list[dict[str, object]] = [
    {"name": "George Russell", "team": "Mercedes",
     "driver_keys": ["George Russell"], "team_keys": ["mercedes"]},
    {"name": "Kimi Antonelli", "team": "Mercedes",
     "driver_keys": ["Andrea Kimi Antonelli", "Kimi Antonelli"], "team_keys": ["mercedes"]},

    {"name": "Charles Leclerc", "team": "Ferrari",
     "driver_keys": ["Charles Leclerc"], "team_keys": ["ferrari"]},
    {"name": "Lewis Hamilton", "team": "Ferrari",
     "driver_keys": ["Lewis Hamilton"], "team_keys": ["ferrari"]},

    {"name": "Max Verstappen", "team": "Red Bull Racing",
     "driver_keys": ["Max Verstappen"], "team_keys": ["red_bull"]},
    {"name": "Isack Hadjar", "team": "Red Bull Racing",
     "driver_keys": ["Isack Hadjar"], "team_keys": ["red_bull"]},

    {"name": "Lando Norris", "team": "McLaren",
     "driver_keys": ["Lando Norris"], "team_keys": ["mclaren"]},
    {"name": "Oscar Piastri", "team": "McLaren",
     "driver_keys": ["Oscar Piastri"], "team_keys": ["mclaren"]},

    {"name": "Liam Lawson", "team": "Racing Bulls",
     "driver_keys": ["Liam Lawson"],
     "team_keys": ["rb", "alphatauri", "racing_bulls", "toro_rosso"]},
    {"name": "Arvid Lindblad", "team": "Racing Bulls",
     "driver_keys": ["Arvid Lindblad"],
     "team_keys": ["rb", "alphatauri", "racing_bulls", "toro_rosso"]},

    {"name": "Pierre Gasly", "team": "Alpine",
     "driver_keys": ["Pierre Gasly"], "team_keys": ["alpine"]},
    {"name": "Franco Colapinto", "team": "Alpine",
     "driver_keys": ["Franco Colapinto"], "team_keys": ["alpine"]},

    {"name": "Rafael Chaves", "team": "Haas",
     "driver_keys": ["Rafael Chaves Camara", "Rafael Chaves", "Rafa Chaves"],
     "team_keys": ["haas"]},
    {"name": "Oliver Bearman", "team": "Haas",
     "driver_keys": ["Oliver Bearman"], "team_keys": ["haas"]},

    {"name": "Nico Hulkenberg", "team": "Audi",
     "driver_keys": ["Nico Hulkenberg", "Nicolas Hulkenberg", "Nico Hülkenberg"],
     "team_keys": ["sauber", "kick_sauber", "alfa", "alfa_romeo", "audi"]},
    {"name": "Gabriel Bortoleto", "team": "Audi",
     "driver_keys": ["Gabriel Bortoleto"],
     "team_keys": ["sauber", "kick_sauber", "alfa", "alfa_romeo", "audi"]},

    {"name": "Carlos Sainz", "team": "Williams",
     "driver_keys": ["Carlos Sainz"], "team_keys": ["williams"]},
    {"name": "Alexander Albon", "team": "Williams",
     "driver_keys": ["Alexander Albon", "Alex Albon"], "team_keys": ["williams"]},

    {"name": "Fernando Alonso", "team": "Aston Martin",
     "driver_keys": ["Fernando Alonso"],
     "team_keys": ["aston_martin", "racing_point", "force_india"]},
    {"name": "Lance Stroll", "team": "Aston Martin",
     "driver_keys": ["Lance Stroll"],
     "team_keys": ["aston_martin", "racing_point", "force_india"]},

    {"name": "Sergio Perez", "team": "Cadillac",
     "driver_keys": ["Sergio Perez", "Sergio Pérez"], "team_keys": ["cadillac"]},
    {"name": "Valtteri Bottas", "team": "Cadillac",
     "driver_keys": ["Valtteri Bottas"], "team_keys": ["cadillac"]},
]


def _norm_key(s: object) -> str:
    s = unicodedata.normalize("NFKD", str(s))
    s = "".join(c for c in s if not unicodedata.combining(c))
    return "".join(c for c in s.lower() if c.isalnum())


def build_current_grid(data: dict[str, pd.DataFrame]) -> pd.DataFrame:
    drivers = data["drivers"].copy()
    constructors = data["constructors"].copy()

    drivers["_full"] = (drivers["forename"].fillna("").astype(str) + " "
                        + drivers["surname"].fillna("").astype(str)).str.strip()
    drivers["_norm"] = drivers["_full"].map(_norm_key)
    drivers["driverId"] = pd.to_numeric(drivers["driverId"], errors="coerce")
    drivers = drivers.dropna(subset=["driverId"])
    drivers["driverId"] = drivers["driverId"].astype(int)
    driver_by_norm = dict(zip(drivers["_norm"], drivers["driverId"]))

    surname_to_ids: defaultdict[str, list[int]] = defaultdict(list)
    for _, r in drivers.iterrows():
        surname_to_ids[_norm_key(r["surname"])].append(int(r["driverId"]))

    constructors["constructorId"] = pd.to_numeric(constructors["constructorId"],
                                                  errors="coerce")
    constructors = constructors.dropna(subset=["constructorId"])
    constructors["constructorId"] = constructors["constructorId"].astype(int)
    cid_by_ref: dict[str, int] = {}
    for _, r in constructors.iterrows():
        ref = _norm_key(r.get("constructorRef", ""))
        if ref:
            cid_by_ref[ref] = int(r["constructorId"])

    synthetic_dids: dict[str, int] = {}
    synthetic_cids: dict[str, int] = {}
    next_syn = -1
    rows: list[dict[str, object]] = []

    for entry in F1_2026_GRID:
        did: int | None = None
        for hint in entry["driver_keys"]:
            did = driver_by_norm.get(_norm_key(hint))
            if did is not None:
                break
        if did is None:
            for hint in entry["driver_keys"]:
                parts = str(hint).split()
                if not parts:
                    continue
                cands = surname_to_ids.get(_norm_key(parts[-1]), [])
                if len(cands) == 1:
                    did = cands[0]
                    break
        if did is None:
            name = str(entry["name"])
            if name not in synthetic_dids:
                synthetic_dids[name] = next_syn
                next_syn -= 1
            did = synthetic_dids[name]
            _p(f"    ! Driver not in dataset: {entry['name']} "
               f"-> synthetic driverId={did} (Elo defaults to 1500)")

        cid: int | None = None
        for hint in entry["team_keys"]:
            cid = cid_by_ref.get(_norm_key(hint))
            if cid is not None:
                break
        if cid is None:
            team = str(entry["team"])
            if team not in synthetic_cids:
                synthetic_cids[team] = next_syn
                next_syn -= 1
            cid = synthetic_cids[team]
            _p(f"    ! Team not in dataset: {entry['team']} "
               f"-> synthetic constructorId={cid} (car Elo defaults to 1500)")

        rows.append({
            "driverId": int(did),
            "name": entry["name"],
            "team": entry["team"],
            "constructorId": int(cid),
        })

    grid = pd.DataFrame(rows).reset_index(drop=True)
    matched_d = int((grid["driverId"] >= 0).sum())
    teams_neg = int((grid["constructorId"] < 0).sum())
    teams_total = int(grid["constructorId"].nunique())
    matched_t = teams_total - teams_neg
    _p(f"    2026 grid hardcoded: {len(grid)} drivers, "
       f"{teams_total} teams "
       f"(driver match {matched_d}/{len(grid)}, "
       f"team match {matched_t}/{teams_total})")
    return grid


# ======================= QUALIFYING SIMULATION =======================
def simulate_quali(grid, n_sims=N_SIMS, rain_prob=RAIN_PROB, seed=RNG_SEED,
                   force_wet=None, pbar=None):
    n = len(grid)
    names = grid["name"].values
    teams = grid["team"].values
    base = grid["q_base"].values.astype(float)
    sigma = np.maximum(grid["sigma"].values.astype(float), SIGMA_FLOOR)
    wet_d = grid["wet_delta"].values.astype(float)

    rng = np.random.default_rng(seed)
    pos_counts = np.zeros((n_sims, n, n), dtype=np.int32)
    wet_count = 0

    for start in range(0, n_sims, CHUNK):
        chunk = min(CHUNK, n_sims - start)
        if force_wet is True:
            wet = np.ones(chunk, dtype=bool)
        elif force_wet is False:
            wet = np.zeros(chunk, dtype=bool)
        else:
            wet = rng.random(chunk) < rain_prob
        wet_count += int(wet.sum())

        chaos = rng.random(chunk) < HIGH_VARIANCE_PROB
        noise_scale = sigma[None, :] * np.where(chaos, HIGH_VARIANCE_MULT, 1.0)[:, None]
        if wet.any():
            noise_scale = noise_scale * np.where(wet[:, None], WET_VARIANCE_SPIKE, 1.0)

        gumbel = rng.gumbel(size=(chunk, n), scale=ELO_NOISE_SCALE) * noise_scale
        scores = base[None, :] + gumbel
        if wet.any():
            scores = scores + wet[:, None] * wet_d[None, :]

        order = np.argsort(-scores, axis=1)
        for pos in range(n):
            idx = order[:, pos]
            np.add.at(pos_counts, (np.arange(start, start + chunk), idx, pos), 1)

        if pbar is not None:
            pbar.update(chunk)

    return {"names": names, "teams": teams, "pos_counts": pos_counts,
            "n_sims": n_sims, "wet_sims": wet_count}


# ============================================================
# HISTORICAL LAS VEGAS DRY-TYRE MODEL (2023–2025 data)
# ============================================================

# --- Compound-specific linear degradation rates (s/lap) ---
# Anchored to FastF1-derived Las Vegas degradation magnitudes.
# Soft is high because it grains heavily and is not a race compound.
HIST_DEG_RATE = {
    "SOFT":   0.055,   # C5 — high graining, short-stint only
    "MEDIUM": 0.030,   # C4 — peak observed ~0.0302 s/lap in 2023
    "HARD":   0.014,   # C3 — long-lived; ~half the Medium rate
}

# --- Graining behaviour (cold Las Vegas night) ---
# In the first few laps of a stint, effective degradation is multiplied.
# 2023 reports: Hard needed ~7 laps to warm up; Medium grained early.
GRAINING_LAPS = 7
HIST_GRAINING_MULT = {
    "SOFT":   2.8,
    "MEDIUM": 1.9,
    "HARD":   1.25,
}

# --- Pit-loss & stint constraints (historical) ---
HIST_PIT_LOSS = 20.5          # seconds (F1.com official Vegas figure)
HIST_FUEL_CORRECTION = 0.045  # s/lap (literature standard)

# --- Historically observed strategy structures ---
# Each entry: (compound_sequence, default_pit_lap_or_None)
# For 1-stops, pit_lap is optimised inside a historical window.
HIST_DRY_STRATEGIES = [
    # 1-stop options (dominant in 2025, viable in 2023/24)
    {"name": "1-stop M→H", "stints": ["MEDIUM", "HARD"], "pit_window": (14, 26)},
    {"name": "1-stop H→M", "stints": ["HARD", "MEDIUM"], "pit_window": (28, 34)},
    # 2-stop options (dominant in 2024 due to graining)
    {"name": "2-stop M→H→H", "stints": ["MEDIUM", "HARD", "HARD"], "pit_laps": (18, 24)},
    {"name": "2-stop S→H→H", "stints": ["SOFT", "HARD", "HARD"], "pit_laps": (10, 16)},
]


def _stint_time_historical(compound, n_laps, stint_start_lap, base_lap_time):
    """
    Accumulate historical dry-tyre stint time.
    Uses linear degradation + early-stint graining multiplier.
    Fuel correction makes the car faster as the race progresses.
    """
    deg = HIST_DEG_RATE[compound]
    grain_mult = HIST_GRAINING_MULT[compound]
    total = 0.0
    for i in range(n_laps):
        race_lap = stint_start_lap + i
        # Fuel-corrected base pace
        lap_base = base_lap_time - HIST_FUEL_CORRECTION * race_lap
        # Tyre degradation
        tyre_deg = deg * i
        # Graining penalty only in the first GRAINING_LAPS of the stint
        if i < GRAINING_LAPS:
            tyre_deg += deg * (grain_mult - 1.0) * (GRAINING_LAPS - i)
        total += lap_base + tyre_deg
    return total


def _total_strategy_time_historical(strategy, base_lap_time):
    """
    Compute total race time for a historical dry strategy.
    Handles both fixed-pit-lap (2-stop) and window-optimised (1-stop) plans.
    Returns (total_time, chosen_pit_laps).
    """
    compounds = strategy["stints"]
    n_stints = len(compounds)

    if "pit_laps" in strategy:
        # Fixed pit laps (multi-stop plans)
        pit_laps = list(strategy["pit_laps"])
        total = 0.0
        start = 1
        for s_idx, comp in enumerate(compounds):
            if s_idx == n_stints - 1:
                stint_len = RACE_LAPS - start + 1
            else:
                stint_len = pit_laps[s_idx] - start + 1
            total += _stint_time_historical(comp, max(stint_len, 1), start, base_lap_time)
            start += max(stint_len, 1)
            if s_idx < n_stints - 1:
                total += HIST_PIT_LOSS
        return total, pit_laps

    # Optimise a single pit lap inside the historical window (1-stop)
    lo, hi = strategy["pit_window"]
    best_time = np.inf
    best_lap = lo
    for p in range(lo, hi + 1):
        total = 0.0
        start = 1
        for s_idx, comp in enumerate(compounds):
            if s_idx == 0:
                stint_len = p - start + 1
            else:
                stint_len = RACE_LAPS - p
            total += _stint_time_historical(comp, max(stint_len, 1), start, base_lap_time)
            start += max(stint_len, 1)
            if s_idx < n_stints - 1:
                total += HIST_PIT_LOSS
        if total < best_time:
            best_time = total
            best_lap = p
    return best_time, [best_lap]


# ======================= RACE SIMULATION =======================
def simulate_race(grid, likely_grid, n_sims=N_SIMS, rng_seed=RNG_SEED,
                  wet=False, pbar=None):
    """
    Simulate the full race from the likely qualifying grid.

    Model
    -----
      * Starting grid: likely_grid + Gaussian noise, re-ranked to a valid permutation
      * Race pace: 70 % lap-time Elo + 30 % race-results Elo
      * Track-position bonus (Vegas = street circuit, very hard to pass)
      * Dry: historical stint-based strategy engine (compound degradation,
        early-stint graining, fuel correction, 20.5 s pit loss, pit-window
        optimisation) using Las Vegas 2023–2025 evidence
      * Wet: generic 1–2 stop model with higher variance
      * Safety car: compresses the field, cancels most of the track bonus
      * DNF: per-driver Bernoulli (modelled from history)
      * Final order: ascending total race time (DNFs at the back)
    """
    n = len(grid)
    rng = np.random.default_rng(rng_seed)

    pace_elo = grid["race_pace"].values.astype(float)
    pos_elo = grid["race_results"].values.astype(float)
    race_elo = RACE_ELO_PACE_W * pace_elo + RACE_ELO_POS_W * pos_elo

    # Normalise race Elo to a known std so output doesn't drift with the data
    re_m, re_s = float(race_elo.mean()), float(race_elo.std())
    re_z = (race_elo - re_m) / re_s if re_s > 1e-6 else np.zeros_like(race_elo)
    pace_delta = re_z * RACE_PACE_SPREAD_SEC

    # ---- Per-driver DNF probability (modelled, not flat) ----
    if wet:
        dnf_prob = grid["dnf_wet_prob"].values.astype(float)
    else:
        dnf_prob = grid["dnf_dry_prob"].values.astype(float)
    dnf_prob = np.clip(dnf_prob, 0.01, 0.50)   # sanity

    base_time = RACE_LAPS * 95.0

    if wet:
        sc_prob      = RACE_SC_WET
        noise_scale  = RACE_NOISE_WET
        pit_std      = RACE_PIT_STD_WET
        track_factor = RACE_TRACK_FACTOR_WET
    else:
        sc_prob      = RACE_SC_DRY
        noise_scale  = RACE_NOISE_DRY
        pit_std      = RACE_PIT_STD_DRY
        track_factor = RACE_TRACK_FACTOR_DRY

    pos_counts = np.zeros((n_sims, n, n), dtype=np.int32)
    dnf_counts = np.zeros((n_sims, n), dtype=bool)
    use_historical_dry = not wet
    strategy_counts = {s["name"]: 0 for s in HIST_DRY_STRATEGIES} if use_historical_dry else {}
    driver_strategy_counts = (
        np.zeros((n, len(HIST_DRY_STRATEGIES)), dtype=np.int32)
        if use_historical_dry else None
    )

    for start in range(0, n_sims, CHUNK):
        chunk = min(CHUNK, n_sims - start)

        grid_noise = rng.normal(0, RACE_GRID_NOISE_STD, (chunk, n))
        noisy_pos  = likely_grid[None, :] + grid_noise
        grid_pos   = np.argsort(np.argsort(noisy_pos, axis=1), axis=1) + 1
        track_bonus = track_factor * (11.0 - grid_pos)

        if use_historical_dry:
            # --- historical dry strategy evaluation per driver ---
            # Per-driver pace: convert pace delta to an effective base lap time.
            # base_time is total race time at 95s/lap baseline; per-lap base is 95s.
            base_lap = 95.0
            race_time = np.zeros((chunk, n), dtype=float)
            chosen = np.empty((chunk, n), dtype=object)

            for d_idx in range(n):
                driver_base_lap = base_lap - (pace_delta[d_idx] / RACE_LAPS)
                strat_times = []
                for strat in HIST_DRY_STRATEGIES:
                    t_total, _ = _total_strategy_time_historical(strat, driver_base_lap)
                    strat_times.append(t_total)

                best_idx = int(np.argmin(strat_times))
                best_time = strat_times[best_idx]
                best_name = HIST_DRY_STRATEGIES[best_idx]["name"]

                # Soft-max over strategies: allow suboptimal historical plans to
                # appear due to execution/track-condition variance.
                diffs = np.array(strat_times, dtype=float) - best_time
                weights = np.exp(-diffs / 2.5)
                weights = weights / weights.sum()
                picks = rng.choice(len(HIST_DRY_STRATEGIES), size=chunk, p=weights)
                for pi, pick in enumerate(picks):
                    nm = HIST_DRY_STRATEGIES[pick]["name"]
                    race_time[pi, d_idx] = strat_times[pick]
                    strategy_counts[nm] += 1
                    driver_strategy_counts[d_idx, pick] += 1

            # Track-position effect (street circuit: very hard to pass)
            race_time -= track_bonus
            # Stochastic lap-time / execution noise
            race_time += rng.normal(0, noise_scale, (chunk, n))
            # Safety-car compression
            sc = rng.random(chunk) < sc_prob
            if sc.any():
                race_time[sc] += track_bonus[sc] * 0.6
        else:
            race_time = (base_time
                         - pace_delta[None, :]
                         - track_bonus
                         + rng.normal(0, noise_scale, (chunk, n)))

            n_stops = rng.integers(1, 3, (chunk, n))
            race_time += n_stops * 23.0 + rng.normal(0, pit_std, (chunk, n))

            sc = rng.random(chunk) < sc_prob
            if sc.any():
                race_time[sc] += track_bonus[sc] * 0.6

        # ---- Per-driver DNF ----
        dnf = rng.random((chunk, n)) < dnf_prob[None, :]
        dnf_counts[start:start + chunk] = dnf
        race_time[dnf] = np.inf

        order = np.argsort(race_time, axis=1)
        for pos in range(n):
            idx = order[:, pos]
            np.add.at(pos_counts, (np.arange(start, start + chunk), idx, pos), 1)

        if pbar is not None:
            pbar.update(chunk)

    return {
        "names":           grid["name"].values,
        "teams":           grid["team"].values,
        "pos_counts":      pos_counts,
        "dnf_counts":      dnf_counts,
        "n_sims":          n_sims,
        "wet":             wet,
        "dnf_prob":        dnf_prob,   # modelled, for report
        "strategy_counts": strategy_counts,
        "driver_strategy_counts": driver_strategy_counts,
        "strategy_names": [s["name"] for s in HIST_DRY_STRATEGIES],
    }


# ======================= REPORTING =======================
def report(res, title="QUALIFYING FORECAST"):
    n_sims = res["n_sims"]
    names = res["names"]
    teams = res["teams"]
    pc = res["pos_counts"]
    n = len(names)

    p_pole = pc[:, :, 0].sum(axis=0) / n_sims * 100
    p_front = pc[:, :, :2].sum(axis=(0, 2)) / n_sims * 100
    p_top3 = pc[:, :, :3].sum(axis=(0, 2)) / n_sims * 100
    p_top10 = pc[:, :, :10].sum(axis=(0, 2)) / n_sims * 100

    pos_idx = np.arange(1, n + 1)
    e_pos = (pc * pos_idx[None, None, :]).sum(axis=(0, 2)) / n_sims
    sq = (pc * (pos_idx[None, None, :] ** 2)).sum(axis=(0, 2)) / n_sims
    sd_pos = np.sqrt(np.maximum(sq - e_pos ** 2, 0.0))

    order = np.argsort(-p_pole)

    _p(f"\n{'═' * 115}")
    _p(f"  {title}")
    _p(f"  {n_sims:,} sims | wet: {res['wet_sims']:,} "
       f"({100 * res['wet_sims'] / n_sims:.1f}%)")
    _p(f"{'═' * 115}\n")
    _p(f"{'#':>2} {'Driver':<24s} {'Team':<16s} "
       f"{'P(Pole)':>8s} {'P(Front)':>9s} {'P(Top3)':>8s} "
       f"{'P(Top10)':>9s} {'E[slot]':>8s} {'σ':>5s}  {'Bar':<18s}")
    _p(f"{'─' * 115}")

    for r, i in enumerate(order, 1):
        tp = float(p_pole[i])
        tf = float(p_front[i])
        tt3 = float(p_top3[i])
        tt10 = float(p_top10[i])
        ep = float(e_pos[i])
        sd = float(sd_pos[i])
        bar_n = int(round(tp / 100 * 18))
        bar = "█" * bar_n + "·" * (18 - bar_n)
        _p(f"{r:>2} {names[i]:<24s} {teams[i]:<16s} "
           f"{tp:>7.2f}% {tf:>8.2f}% "
           f"{tt3:>7.2f}% {tt10:>8.2f}% "
           f"{ep:>7.2f} {sd:>5.2f}  {bar}")

    _p(f"\n{'─' * 115}")
    _p("  MOST LIKELY GRID")
    _p(f"{'─' * 115}")
    likely = pc.sum(axis=0).argmax(axis=1) + 1
    for p, i in enumerate(np.argsort(likely), 1):
        _p(f"  P{p:<2d}  {names[i]:<24s} {teams[i]:<16s}  "
           f"(E[slot]={e_pos[i]:.1f})")
    _p("")


def report_race(res, title="RACE FORECAST"):
    n_sims = res["n_sims"]
    names = res["names"]
    teams = res["teams"]
    pc = res["pos_counts"]
    dnf = res["dnf_counts"]
    n = len(names)

    p_win = pc[:, :, 0].sum(axis=0) / n_sims * 100
    p_podium = pc[:, :, :3].sum(axis=(0, 2)) / n_sims * 100
    p_points = pc[:, :, :10].sum(axis=(0, 2)) / n_sims * 100
    p_dnf = dnf.sum(axis=0) / n_sims * 100

    pos_idx = np.arange(1, n + 1)
    pos_sum = (pc * pos_idx[None, None, :]).sum(axis=(0, 2))
    n_finish = n_sims - dnf.sum(axis=0)
    pos_sum_finish = pos_sum - dnf.sum(axis=0) * n
    e_pos_finish = np.where(n_finish > 0, pos_sum_finish / np.maximum(n_finish, 1), float(n))

    order = np.argsort(-p_win)
    max_pw = max(p_win.max(), 0.01)

    _p(f"\n{'═' * 115}")
    _p(f"  {title}")
    _p(f"  {n_sims:,} sims | {RACE_LAPS} laps | "
       f"{'WET' if res['wet'] else 'DRY'}")
    _p(f"{'═' * 115}\n")
    _p(f"{'#':>2} {'Driver':<24s} {'Team':<16s} "
       f"{'P(Win)':>8s} {'P(Podium)':>10s} {'P(Points)':>10s} "
       f"{'E[Pos]':>8s} {'P(DNF)':>8s}  {'Bar':<18s}")
    _p(f"{'─' * 115}")

    for r, i in enumerate(order, 1):
        pw = float(p_win[i])
        pp = float(p_podium[i])
        ppt = float(p_points[i])
        ep = float(e_pos_finish[i]) if n_finish[i] > 0 else float(n)
        pd = float(p_dnf[i])
        bar_n = int(round(pw / max_pw * 18))
        bar = "█" * bar_n + "·" * (18 - bar_n)
        _p(f"{r:>2} {names[i]:<24s} {teams[i]:<16s} "
           f"{pw:>7.2f}% {pp:>9.2f}% {ppt:>9.2f}% "
           f"{ep:>7.2f} {pd:>7.2f}%  {bar}")

    likely = pc.sum(axis=0).argmax(axis=1) + 1
    _p(f"\n{'─' * 115}")
    _p("  MOST LIKELY RACE RESULT")
    _p(f"{'─' * 115}")
    for p, i in enumerate(np.argsort(likely), 1):
        _p(f"  P{p:<2d}  {names[i]:<24s} {teams[i]:<16s}  "
           f"(E[P]={e_pos_finish[i]:.1f})")

    strat_counts = res.get("strategy_counts") or {}
    total_strat = sum(strat_counts.values())
    drv_strat = res.get("driver_strategy_counts")
    strat_names = res.get("strategy_names") or []
    if total_strat > 0 and not res.get("wet") and drv_strat is not None:
        _p(f"\n{'─' * 115}")
        _p("  HISTORICAL DRY STRATEGY DISTRIBUTION (Vegas 2023–2025)")
        _p(f"{'─' * 115}")
        for name, count in sorted(strat_counts.items(), key=lambda x: -x[1]):
            pct = 100.0 * count / total_strat
            bar_n = int(round(pct / 100 * 30))
            bar = "█" * bar_n + "·" * (30 - bar_n)
            _p(f"  {name:<16s} {pct:>7.2f}%  {bar}")

        _p(f"\n{'─' * 115}")
        _p("  BEST SIMULATED STRATEGY PER DRIVER (most frequent in sims)")
        _p(f"{'─' * 115}")
        _p(f"{'#':>2} {'Driver':<24s} {'Team':<16s} {'Best Strategy':<16s} {'%':>8s}  {'Distribution':<44s}")
        _p(f"{'─' * 115}")
        for r, i in enumerate(order, 1):
            counts = drv_strat[i]
            total_d = int(counts.sum())
            if total_d <= 0:
                continue
            best_idx = int(np.argmax(counts))
            best_name = strat_names[best_idx]
            best_pct = 100.0 * counts[best_idx] / total_d
            dist_parts = []
            for j, nm in enumerate(strat_names):
                pct_j = 100.0 * counts[j] / total_d
                if pct_j >= 1.0:
                    dist_parts.append(f"{nm} {pct_j:.0f}%")
            dist = " | ".join(dist_parts)
            _p(f"{r:>2} {names[i]:<24s} {teams[i]:<16s} {best_name:<16s} {best_pct:>7.2f}%  {dist}")
    _p("")


def report_scenarios(res_dry, res_wet, names, teams):
    n_d = res_dry["n_sims"]
    n_w = res_wet["n_sims"]
    p_dry = res_dry["pos_counts"][:, :, 0].sum(axis=0) / n_d * 100
    p_wet = res_wet["pos_counts"][:, :, 0].sum(axis=0) / n_w * 100
    order = np.argsort(-(p_dry + 0.05 * p_wet))

    _p(f"\n{'═' * 80}")
    _p("  QUALIFYING — DRY vs WET (Pole Probability)")
    _p(f"{'═' * 80}")
    _p(f"{'Driver':<24s} {'Team':<16s} {'Dry':>12s} {'Wet':>12s}")
    _p(f"{'─' * 80}")
    for i in order[:20]:
        _p(f"{names[i]:<24s} {teams[i]:<16s} "
           f"{p_dry[i]:>11.2f}% {p_wet[i]:>11.2f}%")
    _p("")


def report_race_scenarios(res_dry, res_wet):
    n_d = res_dry["n_sims"]
    n_w = res_wet["n_sims"]
    p_dry = res_dry["pos_counts"][:, :, 0].sum(axis=0) / n_d * 100
    p_wet = res_wet["pos_counts"][:, :, 0].sum(axis=0) / n_w * 100
    names = res_dry["names"]
    teams = res_dry["teams"]
    order = np.argsort(-(p_dry + 0.05 * p_wet))

    _p(f"\n{'═' * 80}")
    _p("  RACE — DRY vs WET (Win Probability)")
    _p(f"{'═' * 80}")
    _p(f"{'Driver':<24s} {'Team':<16s} {'Dry':>12s} {'Wet':>12s}")
    _p(f"{'─' * 80}")
    for i in order[:20]:
        _p(f"{names[i]:<24s} {teams[i]:<16s} "
           f"{p_dry[i]:>11.2f}% {p_wet[i]:>11.2f}%")
    _p("")


# ======================= MAIN =======================
def main():
    # -------- progress scaffolding --------
    main_bar = _bar(100, "Initializing", position=0, leave=True)
    sim_bar = None

    def advance(n, desc=None):
        if desc is not None:
            main_bar.set_description(desc)
        main_bar.update(n)

    try:
        # ---- 1. Load ----
        advance(0, "Loading datasets")
        data = load_datasets()
        races = data["races"]
        circuits = data.get("circuits", pd.DataFrame())
        advance(1)

        vegas = races[(races["circuitId"] == LAS_VEGAS_CIRCUIT_ID) & (races["year"] == 2026)]
        if vegas.empty:
            raise SystemExit("2026 Las Vegas GP not found in races.csv")
        vegas = vegas.iloc[0]
        circuit_name = "Las Vegas Street Circuit"
        if not circuits.empty and "circuitId" in circuits.columns:
            row = circuits[circuits["circuitId"] == LAS_VEGAS_CIRCUIT_ID]
            if not row.empty:
                circuit_name = str(row.iloc[0].get("name", circuit_name))
        _p(f"\n2026 Las Vegas GP: raceId={vegas['raceId']}, round={vegas['round']}, "
           f"quali={vegas.get('quali_date', '?')} {vegas.get('quali_time', '?')} UTC")

        # ---- 2. Parse qualifying ----
        advance(0, "Parsing qualifying")
        qdf = build_quali_data(data)
        advance(3)

        # ---- 3. Elo models ----
        advance(0, "Qualifying Elo")
        session_quali = build_quali_elo(qdf)
        advance(2)

        advance(0, "Sprint Elo")
        sprint_quali = build_sprint_quali_elo(data)
        advance(1)

        advance(0, "Race pace Elo")
        race_pace = build_race_pace_elo(data)
        advance(2)

        advance(0, "Race results Elo")
        race_results = build_race_results_elo(data)
        advance(1)

        advance(0, "Night quali Elo")
        night_quali = build_night_quali_elo(qdf)
        advance(1)

        advance(0, "Two-way decomposition")
        car_quali, driver_quali, driver_sigma = build_two_way_decomposition(qdf)
        advance(3)

        advance(0, "Teammate H2H")
        h2h_elo, _ = build_teammate_h2h(qdf)
        advance(1)

        advance(0, "Wet specialists + Vegas history")
        wet_spec = build_wet_specialists(qdf)
        vegas_hist = build_vegas_history(qdf, races)
        advance(1)

        # ---- 4. Grid ----
        advance(0, "Building 2026 grid")
        grid = build_current_grid(data)
        advance(2)

        _p("\n    ! NOTE: jtrotman/formula-1-race-data does not contain free-practice")
        _p("      CSVs. Practice pace cannot be modelled from this source.")

        # ---- 4b. DNF rates (driver + car) ----
        advance(0, "DNF rates (driver + car)")
        car_dnf_base, drv_dnf_excess, dnf_wet_mult, dnf_field_mean = \
            build_dnf_rates(data, qdf)
        advance(2)

        grid["dnf_car_base"] = grid["constructorId"].astype(int).map(car_dnf_base) \
                                                .fillna(dnf_field_mean).astype(float)
        grid["dnf_excess"]   = grid["driverId"].astype(int).map(drv_dnf_excess) \
                                                .fillna(0.0).astype(float)
        grid["dnf_dry_prob"] = np.clip(
            grid["dnf_car_base"] + grid["dnf_excess"],
            DNF_FLOOR, DNF_CEIL,
        )
        grid["dnf_wet_prob"] = np.clip(
            grid["dnf_dry_prob"] * dnf_wet_mult,
            DNF_FLOOR * 1.5, DNF_CEIL * 1.5,
        )

        _p(f"\n    Per-driver DNF rates (dry / wet):")
        _p(f"    {'Driver':<24s} {'Team':<14s} {'car':>7s} "
           f"{'excess':>8s} {'dry':>7s} {'wet':>7s}")
        for _, r_ in grid.sort_values("dnf_dry_prob", ascending=False).iterrows():
            _p(f"    {r_['name'][:24]:<24s} {r_['team'][:14]:<14s} "
               f"{r_['dnf_car_base']*100:>6.2f}% "
               f"{r_['dnf_excess']*100:>+7.2f}pp "
               f"{r_['dnf_dry_prob']*100:>6.2f}% "
               f"{r_['dnf_wet_prob']*100:>6.2f}%")

        # ---- 5. Composite qualifying Elo ----
        advance(0, "Composite Elo")
        grid["two_way"] = grid.apply(
            lambda r: driver_quali.get(int(r["driverId"]), 1500.0)
            + car_quali.get(int(r["constructorId"]), 1500.0) - 1500.0, axis=1)
        grid["q_session"] = grid["driverId"].astype(int).map(session_quali).fillna(1500.0)
        grid["q_sprint"] = grid["driverId"].astype(int).map(sprint_quali).fillna(1500.0)
        grid["q_race"] = grid["driverId"].astype(int).map(race_pace).fillna(1500.0)
        grid["q_night"] = grid["driverId"].astype(int).map(night_quali).fillna(1500.0)
        grid["q_h2h"] = grid["driverId"].astype(int).map(h2h_elo).fillna(1500.0)
        grid["q_vegas"] = grid["driverId"].astype(int).map(vegas_hist).fillna(0.0)
        grid["wet_delta"] = grid["driverId"].astype(int).map(wet_spec).fillna(0.0)
        grid["sigma"] = grid["driverId"].astype(int).map(driver_sigma).fillna(1.0)
        if grid["sigma"].std() > 0:
            grid["sigma"] = grid["sigma"] / grid["sigma"].mean()
        grid["sigma"] = grid["sigma"].clip(SIGMA_POST_FLOOR, SIGMA_POST_CEIL)

        grid["q_base"] = (
            W_TWO_WAY * (grid["two_way"] - 1500.0) +
            W_SESSION_QUALI * (grid["q_session"] - 1500.0) +
            W_SPRINT_QUALI * (grid["q_sprint"] - 1500.0) +
            W_RACE_PACE * (grid["q_race"] - 1500.0) +
            W_H2H * (grid["q_h2h"] - 1500.0) +
            W_NIGHT_QUALI * (grid["q_night"] - 1500.0) +
            W_VEGAS_TRACK * grid["q_vegas"]
        ) + 1500.0

        mu = grid["q_base"].mean()
        sd = grid["q_base"].std()
        grid["q_base"] = grid["q_base"].clip(mu - ELO_CLIP_SIGMA * sd,
                                              mu + ELO_CLIP_SIGMA * sd)

        # race-specific Elo columns
        grid["race_pace"] = grid["driverId"].astype(int).map(race_pace).fillna(1500.0)
        grid["race_results"] = grid["driverId"].astype(int).map(race_results).fillna(1500.0)

        _p(f"\n    Composite Elo after clipping: "
           f"min={grid['q_base'].min():.1f} max={grid['q_base'].max():.1f} "
           f"std={grid['q_base'].std():.1f}")
        _p(f"    σ range: {grid['sigma'].min():.2f} – {grid['sigma'].max():.2f}")
        _p(f"    Elo components (sorted by q_base):")
        _p(f"    {'Driver':<24s} {'Team':<14s} {'two_way':>8s} "
           f"{'session':>8s} {'h2h':>8s} {'q_base':>8s} {'σ':>5s}")
        for _, r in grid.sort_values("q_base", ascending=False).iterrows():
            _p(f"    {r['name'][:24]:<24s} {r['team'][:14]:<14s} "
               f"{r['two_way']:>8.1f} {r['q_session']:>8.1f} "
               f"{r['q_h2h']:>8.1f} {r['q_base']:>8.1f} {r['sigma']:>5.2f}")
        advance(1)

        # ---- 6. Qualifying simulation ----
        advance(0, "Simulating qualifying")
        sim_bar = _bar(N_SIMS, "  Quali", position=1, leave=False)
        res = simulate_quali(grid, n_sims=N_SIMS, rain_prob=RAIN_PROB,
                             force_wet=None, pbar=sim_bar)
        sim_bar.close()
        sim_bar = None
        advance(25)

        # ---- 7. Race simulation ----
        advance(0, "Simulating race")
        # Rank drivers by expected qualifying position (avoids duplicate-modal slots)
        pos_idx = np.arange(1, len(grid) + 1)
        e_pos_q = (res["pos_counts"] * pos_idx[None, None, :]).sum(axis=(0, 2)) / N_SIMS
        likely_grid = np.argsort(np.argsort(e_pos_q)) + 1
        sim_bar = _bar(N_SIMS, "  Race", position=1, leave=False)
        race_res = simulate_race(grid, likely_grid, n_sims=N_SIMS,
                                 rng_seed=RNG_SEED, wet=False, pbar=sim_bar)
        sim_bar.close()
        sim_bar = None
        advance(25)

        # ---- 8. Dry / wet qualifying scenarios ----
        advance(0, "Dry qualifying scenario")
        sim_bar = _bar(N_SIMS // 2, "  Dry-Q", position=1, leave=False)
        res_dry = simulate_quali(grid, n_sims=N_SIMS // 2, force_wet=False,
                                 seed=RNG_SEED + 1, pbar=sim_bar)
        sim_bar.close()
        sim_bar = None
        advance(5)

        advance(0, "Wet qualifying scenario")
        sim_bar = _bar(N_SIMS // 4, "  Wet-Q", position=1, leave=False)
        res_wet = simulate_quali(grid, n_sims=N_SIMS // 4, force_wet=True,
                                 seed=RNG_SEED + 2, pbar=sim_bar)
        sim_bar.close()
        sim_bar = None
        advance(5)

        # ---- 9. Race dry / wet scenarios ----
        advance(0, "Dry race scenario")
        sim_bar = _bar(N_SIMS // 4, "  Dry-R", position=1, leave=False)
        race_dry = simulate_race(grid, likely_grid, n_sims=N_SIMS // 4,
                                 rng_seed=RNG_SEED + 3, wet=False, pbar=sim_bar)
        sim_bar.close()
        sim_bar = None
        advance(7)

        advance(0, "Wet race scenario")
        sim_bar = _bar(N_SIMS // 4, "  Wet-R", position=1, leave=False)
        race_wet = simulate_race(grid, likely_grid, n_sims=N_SIMS // 4,
                                 rng_seed=RNG_SEED + 4, wet=True, pbar=sim_bar)
        sim_bar.close()
        sim_bar = None
        advance(7)

        # ---- 10. Reporting (buffered) ----
        advance(0, "Generating reports")
        report(res, title=f"2026 LAS VEGAS GP — QUALIFYING FORECAST  ({circuit_name})")
        report_race(race_res, title=f"2026 LAS VEGAS GP — RACE FORECAST  ({circuit_name})")
        report_scenarios(res_dry, res_wet, res["names"], res["teams"])
        report_race_scenarios(race_dry, race_wet)
        advance(2)

        main_bar.set_description("Done")

    finally:
        if sim_bar is not None:
            sim_bar.close()
        main_bar.close()
        _flush()


if __name__ == "__main__":
    main()