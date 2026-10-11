from pathlib import Path
import pandas as pd
import numpy as np

# ============================================================
# CONFIG
# ============================================================

LEAGUE_PATHS = {
    "E0": r"C:\Users\liam\Documents\GitHub\Footballdata\data\ENGLAND\Premier league",
    "E1": r"C:\Users\liam\Documents\GitHub\Footballdata\data\ENGLAND\championship\games",
    "E2": r"C:\Users\liam\Documents\GitHub\Footballdata\data\ENGLAND\League1",
    "E3": r"C:\Users\liam\Documents\GitHub\Footballdata\data\ENGLAND\League2",
    "ECN": r"C:\Users\liam\Documents\GitHub\Footballdata\data\ENGLAND\nationalleaguenorth",
}

PREMIER_LEAGUE_TOTAL = 35000

LEAGUE_WEIGHTS = {
    "E0": 92.8 / 92.8,
    "E1": 81.3 / 92.8,
    "E2": 74.9 / 92.8,
    "E3": 69.0 / 92.8,
    "ECN": 52.3 / 92.8,
}

LEAGUE_TOTAL = {
    div: PREMIER_LEAGUE_TOTAL * w for div, w in LEAGUE_WEIGHTS.items()
}

HOME_ADVANTAGE = 65.0
K_BASE = 20.0
USE_GOAL_DIFFERENCE = True
REGRESS_TO_MEAN = 0.10

REQUIRED_COLS = ["Date", "HomeTeam", "AwayTeam", "FTHG", "FTAG"]


# ============================================================
# LOAD DATA
# ============================================================

def load_matches(league_paths: dict) -> pd.DataFrame:
    frames = []

    for div, folder in league_paths.items():
        folder_path = Path(folder)
        if not folder_path.exists():
            print(f"[SKIP] Folder not found: {folder_path}")
            continue

        # Recursive search so nested subfolders are picked up
        csv_files = sorted(folder_path.rglob("*.csv"))
        if not csv_files:
            print(f"[SKIP] No CSVs found under: {folder_path}")
            continue

        print(f"[{div}] Found {len(csv_files)} CSV file(s) under {folder_path}")

        for file in csv_files:
            try:
                df = pd.read_csv(
                    file,
                    encoding="utf-8-sig",
                    on_bad_lines="skip",   # skip malformed rows
                    engine="python",       # more tolerant parser
                )
            except Exception as e:
                print(f"  [FAIL] {file.name}: {e}")
                continue

            # Check required columns exist
            missing = [c for c in REQUIRED_COLS if c not in df.columns]
            if missing:
                print(f"  [FAIL] {file.name}: missing columns {missing}")
                continue

            # Keep only the columns we need
            df = df[REQUIRED_COLS].copy()
            df["Season"] = file.stem
            df["Div"] = div
            frames.append(df)
            print(f"  [OK]   {file.name}  ({len(df)} rows)")

    if not frames:
        raise FileNotFoundError("No usable CSV files found.")

    df = pd.concat(frames, ignore_index=True)

    df["Date"] = pd.to_datetime(df["Date"], dayfirst=True, errors="coerce")
    df = df.dropna(subset=["Date", "HomeTeam", "AwayTeam", "FTHG", "FTAG"])

    df["FTHG"] = df["FTHG"].astype(int)
    df["FTAG"] = df["FTAG"].astype(int)

    df = df.sort_values(["Date"], kind="stable").reset_index(drop=True)
    return df


# ============================================================
# ELO HELPERS
# ============================================================

def expected_score(r_home: float, r_away: float) -> float:
    return 1.0 / (1.0 + 10 ** ((r_away - r_home - HOME_ADVANTAGE) / 400.0))


def actual_home_score(hg: int, ag: int) -> float:
    if hg > ag:
        return 1.0
    if hg == ag:
        return 0.5
    return 0.0


def season_start_adjust(ratings: dict, season_df: pd.DataFrame) -> None:
    for div in season_df["Div"].unique():
        mask = season_df["Div"] == div
        teams = pd.unique(
            season_df.loc[mask, ["HomeTeam", "AwayTeam"]].values.ravel()
        )

        target_total = LEAGUE_TOTAL.get(
            div, PREMIER_LEAGUE_TOTAL * LEAGUE_WEIGHTS.get(div, 0.5)
        )

        for t in teams:
            if t not in ratings:
                ratings[t] = target_total / len(teams)

        if REGRESS_TO_MEAN > 0:
            current_mean = np.mean([ratings[t] for t in teams])
            target_mean = target_total / len(teams)
            for t in teams:
                ratings[t] += REGRESS_TO_MEAN * (target_mean - ratings[t])

        current_sum = sum(ratings[t] for t in teams)
        shift = (target_total - current_sum) / len(teams)
        for t in teams:
            ratings[t] += shift


# ============================================================
# CALCULATE ELO
# ============================================================

def calculate_elo(df: pd.DataFrame) -> dict:
    ratings = {}

    for season, season_df in df.groupby("Season", sort=False):
        season_start_adjust(ratings, season_df)

        for _, row in season_df.iterrows():
            home = row["HomeTeam"]
            away = row["AwayTeam"]
            div = row["Div"]

            r_home = ratings.setdefault(home, 1500.0)
            r_away = ratings.setdefault(away, 1500.0)

            exp_home = expected_score(r_home, r_away)
            act_home = actual_home_score(row["FTHG"], row["FTAG"])

            k = K_BASE * LEAGUE_WEIGHTS.get(div, 0.5)
            if USE_GOAL_DIFFERENCE:
                gd = abs(row["FTHG"] - row["FTAG"])
                k *= 1.0 + np.log1p(gd)

            delta = k * (act_home - exp_home)
            ratings[home] = r_home + delta
            ratings[away] = r_away - delta

    return ratings


# ============================================================
# RUN
# ============================================================

if __name__ == "__main__":
    matches = load_matches(LEAGUE_PATHS)
    print(f"\nLoaded {len(matches)} matches from {matches['Div'].nunique()} leagues.\n")

    ratings = calculate_elo(matches)

    out = pd.DataFrame(
        sorted(ratings.items(), key=lambda x: x[1], reverse=True),
        columns=["Team", "Elo"],
    )
    out.to_csv("elo_ratings.csv", index=False)
    print("Elo ratings saved to elo_ratings.csv\n")
    print(out.head(50).to_string(index=False))