import os
import pandas as pd
import numpy as np
from collections import defaultdict
from tqdm import tqdm
import bisect

# ============================================================
# FILE PATHS
# ============================================================
RESULTS_PATH = r"C:\Users\liam\Documents\GitHub\all-of-my-code\sportsanalysis\F1\f1-dataset\output\results.csv"
DRIVERS_PATH = r"C:\Users\liam\Documents\GitHub\all-of-my-code\sportsanalysis\F1\f1-dataset\output\drivers.csv"
CONSTRUCTORS_PATH = r"C:\Users\liam\Documents\GitHub\all-of-my-code\sportsanalysis\F1\f1-dataset\output\constructors.csv"
QUALIFYING_PATH = r"C:\Users\liam\Documents\GitHub\all-of-my-code\sportsanalysis\F1\f1-dataset\output\qualifying.csv"
RACES_PATH = r"C:\Users\liam\Documents\GitHub\all-of-my-code\sportsanalysis\F1\f1-dataset\output\races.csv"

# ============================================================
# MODEL SETTINGS
# ============================================================
STARTING_ELO = 1500.0
BASE_K_RACE = 20.0
BASE_K_QUAL = 10.0

QUAL_WEIGHT = 0.20
GRID_POS_BONUS = 1.25

DRIVER_SHARE = float(os.environ.get("F1_DRIVER_SHARE", 0.50))
CONST_SHARE = float(os.environ.get("F1_CONST_SHARE", 0.50))

TEAMMATE_K_MULT = 1.5
QUAL_TEAMMATE_K_MULT = 2.0
SAME_TEAM_DRIVER_SHARE = 0.75
SAME_TEAM_CONST_SHARE = 0.0

DNF_MODE = "middle"
DNF_MIDDLE_WEIGHT = 0.5
IGNORE_DNF_VS_DNF = True

BASE_FINISH_PROB = 0.80
RELIABILITY_ALPHA = 0.10
DRIVER_RELIABILITY_WEIGHT = 0.35
CONSTRUCTOR_RELIABILITY_WEIGHT = 0.65
RELIABILITY_EXPECTED_WEIGHT = 0.35

CONFIDENCE_CAP = 130.0
UNCERTAINTY_MIN = 12.0
UNCERTAINTY_MAX = 100.0
CONSERVATIVE_Z = 1.65

WIN_BONUS = 3.0                       # Fixed Elo bonus for race winner (independent of pairwise)

# ============================================================
# F1 WORLD CHAMPIONSHIPS
# ============================================================
WORLD_CHAMPIONSHIPS = {
    "Lewis Hamilton": 7, "Michael Schumacher": 7, "Juan Fangio": 5,
    "Alain Prost": 4, "Sebastian Vettel": 4, "Max Verstappen": 4,
    "Jack Brabham": 3, "Jackie Stewart": 3, "Niki Lauda": 3,
    "Nelson Piquet": 3, "Ayrton Senna": 3, "Alberto Ascari": 2,
    "Graham Hill": 2, "Jim Clark": 2, "Emerson Fittipaldi": 2,
    "Fernando Alonso": 2, "Mika Häkkinen": 2, "Giuseppe Farina": 1,
    "Mike Hawthorn": 1, "Phil Hill": 1, "John Surtees": 1,
    "Denny Hulme": 1, "Jochen Rindt": 1, "James Hunt": 1,
    "Mario Andretti": 1, "Jody Scheckter": 1, "Alan Jones": 1,
    "Keke Rosberg": 1, "Nigel Mansell": 1, "Damon Hill": 1,
    "Jacques Villeneuve": 1, "Kimi Räikkönen": 1, "Jenson Button": 1,
    "Nico Rosberg": 1, "Lando Norris": 1,
}

# ============================================================
# GREATNESS RANKING FACTORS
# ============================================================
CHAMPIONSHIP_GREATNESS_BONUS = 40.0
LONGEVITY_GREATNESS_BONUS = 0.5
LONGEVITY_GREATNESS_CAP = 250
ELITE_MARGIN = 125.0                  # Points above LOO median entering Elo to qualify as elite
STREAK_GREATNESS_BONUS = 15.0
ELITE_RACE_BONUS = 0.2
ELITE_SEASON_BONUS = 3.0
PEAK_GREATNESS_WEIGHT = 0.5

CHAMPIONSHIP_STREAKS = {
    "Michael Schumacher": 5, "Juan Fangio": 4, "Sebastian Vettel": 4,
    "Lewis Hamilton": 4, "Max Verstappen": 4, "Alberto Ascari": 2,
    "Jack Brabham": 2, "Alain Prost": 2, "Ayrton Senna": 2,
    "Mika Häkkinen": 2, "Fernando Alonso": 2,
}

# ============================================================
# HELPER FUNCTIONS
# ============================================================
def classify_status(position_text):
    pt = str(position_text).strip()
    if pt.isdigit():
        return "finish"
    if pt == "D":
        return "dq"
    if pt in {"R", "W", "F", "N"}:
        return "dnf"
    return "other"


def status_is_non_finish(status):
    return status != "finish"


def get_expected(rating_a, rating_b):
    return 1.0 / (1.0 + 10 ** ((rating_b - rating_a) / 400.0))


def get_confidence(info):
    return min(1.0, info / CONFIDENCE_CAP)


def get_uncertainty(confidence):
    return UNCERTAINTY_MIN + (1.0 - confidence) * (UNCERTAINTY_MAX - UNCERTAINTY_MIN)


def loo_median(sorted_vals, removed_val):
    """Compute median of sorted_vals with one occurrence of removed_val excluded."""
    n = len(sorted_vals)
    if n <= 1:
        return STARTING_ELO

    idx = bisect.bisect_left(sorted_vals, removed_val)
    new_vals = sorted_vals[:idx] + sorted_vals[idx + 1:]

    if not new_vals:
        return STARTING_ELO

    m = len(new_vals)
    if m % 2 == 1:
        return float(new_vals[m // 2])
    else:
        return (new_vals[m // 2 - 1] + new_vals[m // 2]) / 2.0


# ============================================================
# LOAD & CLEAN DATA
# ============================================================
print(f"Configuration: DRIVER_SHARE={DRIVER_SHARE:.2f}, CONST_SHARE={CONST_SHARE:.2f}, "
      f"CHAMPIONSHIP_GREATNESS_BONUS={CHAMPIONSHIP_GREATNESS_BONUS}, "
      f"STREAK_GREATNESS_BONUS={STREAK_GREATNESS_BONUS}, "
      f"ELITE_RACE_BONUS={ELITE_RACE_BONUS}, ELITE_SEASON_BONUS={ELITE_SEASON_BONUS}, "
      f"PEAK_GREATNESS_WEIGHT={PEAK_GREATNESS_WEIGHT}, "
      f"ELITE_MARGIN={ELITE_MARGIN}, WIN_BONUS={WIN_BONUS}")
print("Loading Data...")
df_results = pd.read_csv(RESULTS_PATH)
df_drivers = pd.read_csv(DRIVERS_PATH)
df_constructors = pd.read_csv(CONSTRUCTORS_PATH)
df_qual = pd.read_csv(QUALIFYING_PATH)
df_races = pd.read_csv(RACES_PATH)

for df, cols in [
    (df_results, ['raceId', 'driverId', 'constructorId', 'positionOrder', 'grid']),
    (df_qual, ['raceId', 'driverId', 'constructorId', 'position']),
    (df_races, ['raceId', 'year']),
]:
    for c in cols:
        if c in df.columns:
            df[c] = pd.to_numeric(df[c], errors='coerce')

df_results = df_results.dropna(subset=['raceId', 'driverId', 'constructorId', 'positionOrder'])
df_qual = df_qual.dropna(subset=['raceId', 'driverId', 'constructorId', 'position'])
df_races = df_races.dropna(subset=['raceId', 'year'])

df_results["status"] = df_results["positionText"].apply(classify_status)
df_results["non_finish"] = df_results["status"].apply(status_is_non_finish)
df_results = df_results.sort_values(["raceId", "positionOrder"])

df_drivers["driverId"] = pd.to_numeric(df_drivers["driverId"], errors="coerce").astype(int)
df_constructors["constructorId"] = pd.to_numeric(df_constructors["constructorId"], errors="coerce").astype(int)
df_drivers["fullName"] = (
    df_drivers["forename"].fillna("") + " " + df_drivers["surname"].fillna("")
).str.strip()

driver_names = dict(zip(df_drivers["driverId"], df_drivers["fullName"]))
constructor_names = dict(zip(df_constructors["constructorId"], df_constructors["name"]))

driver_titles = {
    d: WORLD_CHAMPIONSHIPS.get(name, 0)
    for d, name in driver_names.items()
}

race_year = dict(zip(df_races["raceId"].astype(int), df_races["year"].astype(int)))

# ============================================================
# STATE INITIALIZATION
# ============================================================
rElo_d, rElo_c = {}, {}
qElo_d, qElo_c = {}, {}
races_d, races_c = {}, {}
q_races_d, q_races_c = {}, {}
perf_d, perf_c = {}, {}
driver_fp, const_fp = {}, {}
info_d, info_c = {}, {}
q_info_d, q_info_c = {}, {}
peak_rElo_d, peak_rElo_c = {}, {}

season_drivers = set()
previous_year = None
era_offset = {}
driver_year_starts = defaultdict(float)

# Paired pre/post-race Elo snapshots for Pass 2
# Format: (driver_id, constructor_id, pre_elo_d, pre_elo_c, post_elo_d, post_elo_c, year)
race_elo_pairs = []


def ensure_entities(d_ids, c_ids):
    for d in d_ids:
        rElo_d.setdefault(d, STARTING_ELO)
        qElo_d.setdefault(d, STARTING_ELO)
        races_d.setdefault(d, 0)
        q_races_d.setdefault(d, 0)
        perf_d.setdefault(d, 0.0)
        driver_fp.setdefault(d, BASE_FINISH_PROB)
        info_d.setdefault(d, 0.0)
        q_info_d.setdefault(d, 0.0)
    for c in c_ids:
        rElo_c.setdefault(c, STARTING_ELO)
        qElo_c.setdefault(c, STARTING_ELO)
        races_c.setdefault(c, 0)
        q_races_c.setdefault(c, 0)
        perf_c.setdefault(c, 0.0)
        const_fp.setdefault(c, BASE_FINISH_PROB)
        info_c.setdefault(c, 0.0)
        q_info_c.setdefault(c, 0.0)


# ============================================================
# PRE-GROUP DATA
# ============================================================
all_race_ids = sorted(df_results['raceId'].unique())
grouped_results = dict(list(df_results.groupby("raceId")))
grouped_qual = dict(list(df_qual.groupby("raceId")))

global_perf_sum = 0.0
global_races_sum = 0

# ============================================================
# PASS 1: SIMULATION WITH PAIRED PRE/POST SNAPSHOTS
# ============================================================
print("\nPass 1: Simulating F1 history...")

for race_id in tqdm(all_race_ids, desc="Processing Races", unit="race", ncols=80):
    rid = int(race_id)
    year = race_year.get(rid, None)

    # --- ERA BOOKKEEPING ---
    if year is not None and previous_year is not None and year != previous_year:
        if season_drivers:
            elos = [rElo_d[d] for d in season_drivers if d in rElo_d]
            if elos:
                era_offset[previous_year] = (sum(elos) / len(elos)) - STARTING_ELO
            else:
                era_offset[previous_year] = 0.0
        season_drivers = set()
    previous_year = year

    # --- 1. QUALIFYING CONTEST ---
    q_df = grouped_qual.get(race_id)
    if q_df is not None and len(q_df) >= 2:
        q_df = q_df.sort_values('position')
        ensure_entities(q_df['driverId'].tolist(), q_df['constructorId'].tolist())

        q_entrants = q_df.to_dict('records')
        n_q = len(q_entrants)
        k_q = BASE_K_QUAL / max(1, n_q - 1)

        for i in range(n_q):
            for j in range(i + 1, n_q):
                a, b = q_entrants[i], q_entrants[j]
                same_team = a['constructorId'] == b['constructorId']

                rating_a = qElo_d[a['driverId']] + qElo_c[a['constructorId']] - STARTING_ELO
                rating_b = qElo_d[b['driverId']] + qElo_c[b['constructorId']] - STARTING_ELO

                exp_a = get_expected(rating_a, rating_b)

                if same_team:
                    k_pair = k_q * QUAL_TEAMMATE_K_MULT
                    d_share = SAME_TEAM_DRIVER_SHARE
                    c_share = SAME_TEAM_CONST_SHARE
                else:
                    k_pair = k_q
                    d_share = DRIVER_SHARE
                    c_share = CONST_SHARE

                delta = k_pair * (1.0 - exp_a)

                qElo_d[a['driverId']] += delta * d_share
                qElo_d[b['driverId']] -= delta * d_share

                if c_share > 0.0:
                    qElo_c[a['constructorId']] += delta * c_share
                    qElo_c[b['constructorId']] -= delta * c_share

        for q_entry in q_entrants:
            q_id = q_entry['driverId']
            q_cid = q_entry['constructorId']
            q_races_d[q_id] += 1
            q_races_c[q_cid] += 1
            q_info_d[q_id] += 1.0
            q_info_c[q_cid] += 1.0

    # --- 2. RACE CONTEST ---
    r_df = grouped_results.get(race_id)
    if r_df is None:
        continue

    r_df = r_df.sort_values("positionOrder").copy()
    ensure_entities(r_df['driverId'].tolist(), r_df['constructorId'].tolist())

    # *** CAPTURE TRUE PRE-RACE ELO BEFORE ANY UPDATES ***
    pre_race_elos = {}
    for idx, row in r_df.iterrows():
        d_id = int(row['driverId'])
        c_id = int(row['constructorId'])
        pre_race_elos[(d_id, c_id)] = (
            rElo_d.get(d_id, STARTING_ELO),
            rElo_c.get(c_id, STARTING_ELO),
        )

    if len(r_df) >= 2:
        valid_grids = r_df.loc[r_df['grid'] > 0, 'grid']
        avg_grid = float(valid_grids.mean()) if len(valid_grids) > 0 else 12.0

        r_df['grid_filled'] = pd.to_numeric(r_df['grid'], errors='coerce').astype('float64')
        r_df.loc[r_df['grid_filled'].isna(), 'grid_filled'] = avg_grid
        r_df.loc[r_df['grid_filled'] <= 0, 'grid_filled'] = avg_grid

        r_entrants = r_df.to_dict('records')
        n_r = len(r_entrants)
        k_r = BASE_K_RACE / max(1, n_r - 1)

        for i in range(n_r):
            a = r_entrants[i]
            a_nf = bool(a["non_finish"])

            fp_a = (
                DRIVER_RELIABILITY_WEIGHT * driver_fp.get(a['driverId'], BASE_FINISH_PROB) +
                CONSTRUCTOR_RELIABILITY_WEIGHT * const_fp.get(a['constructorId'], BASE_FINISH_PROB)
            )

            for j in range(i + 1, n_r):
                b = r_entrants[j]
                b_nf = bool(b["non_finish"])

                if IGNORE_DNF_VS_DNF and a_nf and b_nf:
                    continue

                same_team = a['constructorId'] == b['constructorId']

                if same_team:
                    k_pair = k_r * TEAMMATE_K_MULT
                    d_share = SAME_TEAM_DRIVER_SHARE
                    c_share = SAME_TEAM_CONST_SHARE
                else:
                    k_pair = k_r
                    d_share = DRIVER_SHARE
                    c_share = CONST_SHARE

                pair_weight = 1.0
                if DNF_MODE == "middle" and (a_nf or b_nf):
                    pair_weight = DNF_MIDDLE_WEIGHT

                if a_nf and b_nf:
                    actual_a = 0.5
                elif not a_nf and b_nf:
                    actual_a = 1.0
                elif a_nf and not b_nf:
                    actual_a = 0.0
                else:
                    actual_a = 1.0

                fp_b = (
                    DRIVER_RELIABILITY_WEIGHT * driver_fp.get(b['driverId'], BASE_FINISH_PROB) +
                    CONSTRUCTOR_RELIABILITY_WEIGHT * const_fp.get(b['constructorId'], BASE_FINISH_PROB)
                )

                rating_a = (
                    rElo_d[a['driverId']] + rElo_c[a['constructorId']] - STARTING_ELO +
                    QUAL_WEIGHT * (qElo_d[a['driverId']] + qElo_c[a['constructorId']] - STARTING_ELO) +
                    GRID_POS_BONUS * (avg_grid - a.get('grid_filled', avg_grid))
                )

                rating_b = (
                    rElo_d[b['driverId']] + rElo_c[b['constructorId']] - STARTING_ELO +
                    QUAL_WEIGHT * (qElo_d[b['driverId']] + qElo_c[b['constructorId']] - STARTING_ELO) +
                    GRID_POS_BONUS * (avg_grid - b.get('grid_filled', avg_grid))
                )

                rating_exp = get_expected(rating_a, rating_b)

                rel_den = fp_a + fp_b + 1e-9
                rel_exp = fp_a / rel_den

                exp_a = (
                    (1.0 - RELIABILITY_EXPECTED_WEIGHT) * rating_exp +
                    RELIABILITY_EXPECTED_WEIGHT * rel_exp
                )

                delta = k_pair * pair_weight * (actual_a - exp_a)

                rElo_d[a['driverId']] += delta * d_share
                rElo_d[b['driverId']] -= delta * d_share

        # --- 2b. CONSTRUCTOR ELO UPDATES ---
        team_entries = defaultdict(list)
        for entry in r_entrants:
            team_entries[entry['constructorId']].append(entry)

        team_avgs = {}
        team_non_finish = {}
        for c_id, entries in team_entries.items():
            finished_pos = [e for e in entries if not e['non_finish']]
            if finished_pos:
                team_avgs[c_id] = sum(e['positionOrder'] for e in finished_pos) / len(finished_pos)
            else:
                team_avgs[c_id] = float(n_r)
            team_non_finish[c_id] = all(e['non_finish'] for e in entries)

        teams = list(team_avgs.keys())
        n_teams = len(teams)
        if n_teams >= 2:
            k_c = BASE_K_RACE / max(1, n_teams - 1)
            for i in range(n_teams):
                for j in range(i + 1, n_teams):
                    c_a, c_b = teams[i], teams[j]
                    if IGNORE_DNF_VS_DNF and team_non_finish[c_a] and team_non_finish[c_b]:
                        continue
                    rating_a = rElo_c[c_a] - STARTING_ELO
                    rating_b = rElo_c[c_b] - STARTING_ELO
                    exp_c = get_expected(rating_a, rating_b)
                    actual_c = 1.0 if team_avgs[c_a] < team_avgs[c_b] else (
                        0.5 if team_avgs[c_a] == team_avgs[c_b] else 0.0
                    )
                    c_delta = k_c * (actual_c - exp_c)
                    rElo_c[c_a] += c_delta
                    rElo_c[c_b] -= c_delta

    # --- 2c. WIN BONUS (applied AFTER pairwise updates, BEFORE snapshot) ---
    winner = r_entrants[0]
    if not bool(winner["non_finish"]):
        rElo_d[winner['driverId']] += WIN_BONUS

    # --- 3. UPDATE METRICS + CAPTURE POST-RACE ELO PAIRS ---
    for idx, row in r_df.iterrows():
        d_id, c_id = int(row['driverId']), int(row['constructorId'])
        pos_score = (len(r_df) - row['positionOrder'] + 1) / len(r_df)

        perf_d[d_id] += pos_score
        perf_c[c_id] += pos_score
        races_d[d_id] += 1
        races_c[c_id] += 1

        finished_flag = 0.0 if row['non_finish'] else 1.0

        driver_fp[d_id] = (
            (1.0 - RELIABILITY_ALPHA) * driver_fp.get(d_id, BASE_FINISH_PROB) +
            RELIABILITY_ALPHA * finished_flag
        )
        const_fp[c_id] = (
            (1.0 - RELIABILITY_ALPHA) * const_fp.get(c_id, BASE_FINISH_PROB) +
            RELIABILITY_ALPHA * finished_flag
        )

        info_weight = 1.0 if finished_flag > 0.5 else 0.5
        info_d[d_id] += info_weight
        info_c[c_id] += info_weight

        season_drivers.add(d_id)
        if year is not None:
            driver_year_starts[(d_id, year)] += info_weight

        current_elo = rElo_d.get(d_id, STARTING_ELO)
        if d_id not in peak_rElo_d or current_elo > peak_rElo_d[d_id]:
            peak_rElo_d[d_id] = current_elo

        current_c_elo = rElo_c.get(c_id, STARTING_ELO)
        if c_id not in peak_rElo_c or current_c_elo > peak_rElo_c[c_id]:
            peak_rElo_c[c_id] = current_c_elo

        # *** STORE PAIRED PRE/POST SNAPSHOT (post includes WIN_BONUS) ***
        pre_d, pre_c = pre_race_elos.get((d_id, c_id), (STARTING_ELO, STARTING_ELO))
        race_elo_pairs.append((d_id, c_id, pre_d, pre_c, current_elo, current_c_elo, year))

        global_perf_sum += pos_score
        global_races_sum += 1

# Close final season
if previous_year is not None and season_drivers:
    elos = [rElo_d[d] for d in season_drivers if d in rElo_d]
    if elos:
        era_offset[previous_year] = (sum(elos) / len(elos)) - STARTING_ELO
    else:
        era_offset[previous_year] = 0.0


# ============================================================
# PASS 2: ELITE EVALUATION WITH LEAVE-ONE-OUT BASELINE
# ============================================================
print("\nPass 2: Evaluating elite with leave-one-out baselines...")

# Step 1: Collect entering Elos per (driver, year)
entering_elo = {}
for d_id, c_id, pre_d, pre_c, post_d, post_c, yr in race_elo_pairs:
    if yr is None:
        continue
    key = (d_id, yr)
    if key not in entering_elo:
        entering_elo[key] = pre_d

# Step 2: Group by year
year_driver_elos = defaultdict(dict)
for (d_id, yr), elo in entering_elo.items():
    year_driver_elos[yr][d_id] = elo

# Step 3: Precompute sorted arrays for efficient LOO
year_sorted_elos = {}
year_full_median = {}
for yr, drv_elos in year_driver_elos.items():
    vals = sorted(drv_elos.values())
    year_sorted_elos[yr] = vals
    year_full_median[yr] = float(np.median(vals))

# Step 4: Evaluate each race entry with its personal LOO baseline
elite_races_d = defaultdict(int)
elite_races_c = defaultdict(int)
elite_years_d = defaultdict(set)
elite_years_c = defaultdict(set)

for d_id, c_id, pre_d, pre_c, post_d, post_c, yr in tqdm(
    race_elo_pairs, desc="Elite Eval", unit="entry", ncols=80
):
    if yr is None or yr not in year_sorted_elos:
        continue

    sorted_vals = year_sorted_elos[yr]
    driver_entering = entering_elo.get((d_id, yr), pre_d)

    baseline = loo_median(sorted_vals, driver_entering)
    threshold = baseline + ELITE_MARGIN

    if post_d >= threshold:
        elite_races_d[d_id] += 1
        elite_years_d[d_id].add(yr)

    if post_c >= threshold:
        elite_races_c[c_id] += 1
        elite_years_c[c_id].add(yr)


# ============================================================
# DIAGNOSTIC: Schumacher Elo Trajectory
# ============================================================
print("\n=== DIAGNOSTIC: Schumacher Elo Trajectory ===")
schu_id = None
for did, name in driver_names.items():
    if "Michael Schumacher" in name:
        schu_id = did
        break

if schu_id:
    schu_pairs = [(pre_d, post_d, yr) for d_id, c_id, pre_d, pre_c, post_d, post_c, yr
                  in race_elo_pairs if d_id == schu_id]

    print(f"\nSchumacher (ID={schu_id}) peak post-race Elo by year:")
    print(f"{'Year':<6} {'Races':>6} {'Peak Post':>10}")
    print("-" * 28)

    year_race_count = defaultdict(int)
    max_post_by_year = {}
    for pre_d, post_d, yr in schu_pairs:
        year_race_count[yr] += 1
        if yr not in max_post_by_year or post_d > max_post_by_year[yr]:
            max_post_by_year[yr] = post_d

    for yr in sorted(max_post_by_year.keys()):
        if 1991 <= yr <= 2012:
            print(f"{yr:<6} {year_race_count[yr]:>6} {max_post_by_year[yr]:>10.1f}")

    print(f"\nLOO Thresholds vs Schumacher Peak Post-Race Elo:")
    print(f"{'Year':<6} {'Peak Post':>10} {'LOO Base':>10} {'Threshold':>10} {'Gap':>8} {'Elite?':>7}")
    print("-" * 58)

    for yr in range(1991, 2013):
        if yr not in year_sorted_elos or (schu_id, yr) not in entering_elo:
            continue
        peak_post = max_post_by_year.get(yr, 0)
        schu_entering = entering_elo[(schu_id, yr)]
        loo_med = loo_median(year_sorted_elos[yr], schu_entering)
        thresh = loo_med + ELITE_MARGIN
        gap = peak_post - thresh
        elite = "YES" if peak_post >= thresh else "NO"
        print(f"{yr:<6} {peak_post:>10.1f} {loo_med:>10.1f} {thresh:>10.1f} {gap:>+8.1f} {elite:>7}")
else:
    print("WARNING: Could not find Michael Schumacher in driver_names!")


# ============================================================
# ERA ADJUSTMENT HELPER
# ============================================================
def era_adjusted_elo(d_id, raw_elo):
    total = 0.0
    offset_sum = 0.0
    for (did, yr), starts in driver_year_starts.items():
        if did != d_id:
            continue
        total += starts
        offset_sum += starts * era_offset.get(yr, 0.0)
    if total == 0.0:
        return raw_elo
    return raw_elo - (offset_sum / total)


# ============================================================
# FINAL LEADERBOARD
# ============================================================
print("\nBuilding leaderboards...")


def make_leaderboard(elo_dict, info_dict, races_dict, names_dict, titles_map=None, context=None):
    rows = []
    for k, v in elo_dict.items():
        conf = get_confidence(info_dict.get(k, 0.0))
        unc = get_uncertainty(conf)
        conservative = v - CONSERVATIVE_Z * unc
        era_adj = era_adjusted_elo(k, v)
        titles = titles_map.get(k, 0) if titles_map else 0
        streak = CHAMPIONSHIP_STREAKS.get(names_dict.get(k, ""), 0)
        races = races_dict.get(k, 0)
        if context:
            peak_elo = context.get("peak_elo", {}).get(k, v)
            peak_era_adj = era_adjusted_elo(k, peak_elo)
            elite_races = context.get("elite_races", {}).get(k, 0)
            elite_seasons = len(context.get("elite_years", {}).get(k, set()))
        else:
            peak_elo = v
            peak_era_adj = era_adj
            elite_races = 0
            elite_seasons = 0
        peak_score = (
            peak_era_adj
            + titles * CHAMPIONSHIP_GREATNESS_BONUS
            + streak * STREAK_GREATNESS_BONUS
        )
        longevity_score = (
            era_adj
            + min(races, LONGEVITY_GREATNESS_CAP) * LONGEVITY_GREATNESS_BONUS
            + elite_races * ELITE_RACE_BONUS
            + elite_seasons * ELITE_SEASON_BONUS
        )
        greatness = (
            PEAK_GREATNESS_WEIGHT * peak_score
            + (1.0 - PEAK_GREATNESS_WEIGHT) * longevity_score
        )

        rows.append({
            "Id": k,
            "Name": names_dict.get(k, "Unknown"),
            "Latest Elo": v,
            "Peak Elo": peak_elo,
            "Peak Era Adjusted": peak_era_adj,
            "Era Adjusted Elo": era_adj,
            "Confidence": conf,
            "Uncertainty": unc,
            "Lower Bound Elo": conservative,
            "Peak Score": peak_score,
            "Longevity Score": longevity_score,
            "Greatness": greatness,
            "UB Low": era_adj - CONSERVATIVE_Z * unc,
            "UB High": era_adj + CONSERVATIVE_Z * unc,
            "Titles": titles,
            "Champ Streak": streak,
            "Races": races,
            "Elite Races": elite_races,
            "Elite Seasons": elite_seasons,
        })

    df = pd.DataFrame(rows)
    return df.sort_values("Latest Elo", ascending=False).reset_index(drop=True)


df_drivers_final = make_leaderboard(
    rElo_d, info_d, races_d, driver_names, driver_titles,
    context={"peak_elo": peak_rElo_d, "elite_races": elite_races_d, "elite_years": elite_years_d},
)
df_constructors_final = make_leaderboard(
    rElo_c, info_c, races_c, constructor_names,
    context={"peak_elo": peak_rElo_c, "elite_races": elite_races_c, "elite_years": elite_years_c},
)
df_qualifiers_final = make_leaderboard(
    qElo_d, q_info_d, q_races_d, driver_names, driver_titles,
    context={"peak_elo": peak_rElo_d, "elite_races": elite_races_d, "elite_years": elite_years_d},
)

# --- ALL DRIVERS ---
print("\n--- ALL DRIVERS (sorted by Latest Elo) ---")
print(
    f"{'Rank':<5} | {'Driver':<25} | {'Latest':>7} | {'Peak':>7} | {'PeakEra':>7} | {'EraAdj':>7} | "
    f"{'Evidence':>6} | {'LWB':>8} | {'EliteR':>6} | {'Tit':>4} | {'Str':>4} | {'Races':>6}"
)
print("-" * 120)
for rank, row in df_drivers_final.head(25).iterrows():
    print(
        f"{rank + 1:<5} | {row['Name']:<25} | {row['Latest Elo']:>7.1f} | "
        f"{row['Peak Elo']:>7.1f} | {row['Peak Era Adjusted']:>7.1f} | "
        f"{row['Era Adjusted Elo']:>7.1f} | {row['Confidence']:>6.1%} | "
        f"{row['Lower Bound Elo']:>8.1f} | "
        f"{row['Elite Races']:>6} | {row['Titles']:>4} | {row['Champ Streak']:>4} | {row['Races']:>6}"
    )

# --- ALL-TIME GREATNESS ---
df_greatness = df_drivers_final.sort_values("Greatness", ascending=False).reset_index(drop=True)
print("\n--- ALL-TIME GREATNESS ---")
print(
    f"{'Rank':<5} | {'Driver':<25} | {'Greatness':>9} | {'Peak':>8} | {'Longev':>8} | "
    f"{'PeakEra':>7} | {'EraAdj':>7} | {'Unc.Band':>14} | {'Evidence':>6} | "
    f"{'EliteR':>6} | {'EliteS':>6} | {'Tit':>4} | {'Str':>4} | {'Races':>6}"
)
print("-" * 155)
for rank, row in df_greatness.head(25).iterrows():
    print(
        f"{rank + 1:<5} | {row['Name']:<25} | {row['Greatness']:>9.1f} | "
        f"{row['Peak Score']:>8.1f} | {row['Longevity Score']:>8.1f} | "
        f"{row['Peak Era Adjusted']:>7.1f} | {row['Era Adjusted Elo']:>7.1f} | "
        f"[{row['UB Low']:>7.0f}–{row['UB High']:>6.0f}] | {row['Confidence']:>6.1%} | "
        f"{row['Elite Races']:>6} | {row['Elite Seasons']:>6} | "
        f"{row['Titles']:>4} | {row['Champ Streak']:>4} | {row['Races']:>6}"
    )

# --- TOP 10 CONSTRUCTORS ---
print("\n--- TOP 10 CONSTRUCTORS ---")
print(
    f"{'Rank':<5} | {'Constructor':<25} | {'Latest':>7} | {'Peak':>7} | {'PeakEra':>7} | {'EraAdj':>7} | "
    f"{'Evidence':>6} | {'LWB':>8} | {'EliteR':>6} | {'Tit':>4} | {'Races':>6}"
)
print("-" * 125)
for rank, row in df_constructors_final.head(10).iterrows():
    print(
        f"{rank + 1:<5} | {row['Name']:<25} | {row['Latest Elo']:>7.1f} | "
        f"{row['Peak Elo']:>7.1f} | {row['Peak Era Adjusted']:>7.1f} | "
        f"{row['Era Adjusted Elo']:>7.1f} | {row['Confidence']:>6.1%} | "
        f"{row['Lower Bound Elo']:>8.1f} | "
        f"{row['Elite Races']:>6} | {row['Titles']:>4} | {row['Races']:>6}"
    )

# --- TOP 10 QUALIFYING SPECIALISTS ---
print("\n--- TOP 10 ONE-LAP SPECIALISTS (Qualifying Elo) ---")
print(
    f"{'Rank':<5} | {'Driver':<25} | {'Qual Elo':>9} | {'Evidence':>6} | {'Tit':>4} | {'Races':>6}"
)
print("-" * 75)
for rank, row in df_qualifiers_final.head(10).iterrows():
    print(
        f"{rank + 1:<5} | {row['Name']:<25} | {row['Latest Elo']:>9.1f} | "
        f"{row['Confidence']:>6.1%} | {row['Titles']:>4} | {row['Races']:>6}"
    )

print("\nDone!")