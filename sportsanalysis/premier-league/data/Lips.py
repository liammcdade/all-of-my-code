#!/usr/bin/env python3
"""
split_leagues.py

Splits the hardcoded matches CSV into one folder per league and one CSV per season:

    output/<League>/<season>.csv
    e.g.  output/Second Division/1888-89.csv

Rules
-----
* Tier 1 ("First Division" / Premier League) is SKIPPED.
* Only tiers 2, 3 and 4 are exported.
* Only seasons up to and including 1999-2000 are exported.
* A pre-flight check reports the tier distribution before splitting.
* A progress bar is shown during the pre-flight and split passes.

Install tqdm for a nicer bar (optional):
    pip install tqdm

Just run:
    python split_leagues.py
"""

from __future__ import annotations

import re
import sys
from collections import Counter, defaultdict
from pathlib import Path

import pandas as pd

# optional dependency - falls back to a plain row counter if not installed
try:
    from tqdm import tqdm
    _HAS_TQDM = True
except ImportError:
    tqdm = None
    _HAS_TQDM = False

# ==========================================================================
# HARDCODED PATHS - edit these if the files move
# ==========================================================================
SOURCE_CSV = Path(
    r"C:\Users\liam\Documents\GitHub\all-of-my-code\sportsanalysis\premier-league\data\matches.csv"
)
OUTPUT_DIR = Path(__file__).resolve().parent / "output"

# ==========================================================================
# configuration - tweak here
# ==========================================================================
TIERS_TO_KEEP = {2, 3, 4}       # tier 1 ("First Division") deliberately excluded
MAX_SEASON_END_YEAR = 2000      # keep everything up to and including 1999-2000
CHUNKSIZE = 250_000
APPEND_MODE = False             # True = append to existing files, False = overwrite
BY_TIER = False                 # True = folders named "Tier 2", "Tier 3", ...
SHOW_PROGRESS = True            # set False to silence the progress bars

DIVISION_TO_TIER = {
    "first division": 1,
    "premier league": 1,
    "second division": 2,
    "championship": 2,
    "third division": 3,
    "league one": 3,
    "fourth division": 4,
    "league two": 4,
}

INVALID_CHARS = re.compile(r'[\\/:*?"<>|\x00-\x1f]')


# --------------------------------------------------------------------------
# progress bar (tqdm if available, plain counter otherwise)
# --------------------------------------------------------------------------
class _FallbackBar:
    """Minimal progress printer used when tqdm isn't installed."""
    def __init__(self, total=None, desc="", unit="row", **_):
        self.total = total
        self.desc = desc
        self.n = 0
        self._kept = ""
        self._tty = sys.stdout.isatty()
        self._next_report = 0

    def update(self, n: int) -> None:
        self.n += n
        if self._tty:
            self._print()
        elif self.n >= self._next_report:
            self._print()
            step = max(500_000, (self.total or 0) // 10)
            self._next_report = self.n + step

    def set_postfix(self, **kw) -> None:
        if "kept" in kw:
            self._kept = f"  kept {kw['kept']}"
        if self._tty:
            self._print()

    def _print(self) -> None:
        if self.total:
            pct = 100 * self.n / self.total
            line = (f"  {self.desc}: {self.n:,}/{self.total:,} rows "
                    f"({pct:5.1f}%){self._kept}")
        else:
            line = f"  {self.desc}: {self.n:,} rows{self._kept}"
        if self._tty:
            print("\r" + line, end="", flush=True)
        else:
            print(line, flush=True)

    def close(self) -> None:
        self._print()
        if self._tty:
            print()

    def __enter__(self):
        return self

    def __exit__(self, *a):
        self.close()


def _make_bar(total=None, desc="working"):
    if not SHOW_PROGRESS:
        return _FallbackBar(total=total, desc=desc)  # silenced below
    if _HAS_TQDM:
        return tqdm(
            total=total,
            desc=desc,
            unit="row",
            unit_scale=True,
            dynamic_ncols=True,
            leave=True,
            disable=False,
        )
    return _FallbackBar(total=total, desc=desc)


# --------------------------------------------------------------------------
# helpers
# --------------------------------------------------------------------------
def sanitize(name: str) -> str:
    name = INVALID_CHARS.sub("-", str(name)).strip()
    name = re.sub(r"\s+", " ", name).strip(" .")
    return name or "unknown"


def season_end_year(season: str) -> int | None:
    """End year of a season label: '1888' -> 1889, '1888-89' -> 1889, '1999-2000' -> 2000."""
    s = str(season).strip()
    years = re.findall(r"\d{2,4}", s)
    if not years:
        return None
    if len(years) == 1:
        return int(years[0]) + 1 if len(years[0]) == 4 else None
    start, end_raw = int(years[0]), years[1]
    end = int(end_raw)
    if len(end_raw) == 2:
        end += (start // 100) * 100
        if end < start:
            end += 100
    return end


def season_label(season: str) -> str:
    """Canonical, sortable, filesystem-safe season name ('1888' -> '1888-89')."""
    s = str(season).strip()
    years = re.findall(r"\d{2,4}", s)
    if len(years) == 1 and len(years[0]) == 4:
        start = int(years[0])
        return f"{start}-{str(start + 1)[-2:]}"
    if len(years) >= 2 and len(years[0]) == 4:
        end = season_end_year(s)
        if end is not None:
            return f"{years[0]}-{str(end)[-2:]}"
    return sanitize(s)


def league_folder_name(tier: int, division: str, subdivision: str) -> str:
    div = str(division).strip()
    sub = str(subdivision).strip()
    if div.lower() in ("", "none", "nan"):
        div = f"Tier {tier}"
    if sub.lower() not in ("", "none", "nan"):
        return sanitize(f"{div} {sub}")
    return sanitize(div)


def _infer_tiers(chunk: pd.DataFrame) -> pd.Series:
    """Tier number for each row, numeric column first, division name as fallback."""
    num = pd.to_numeric(
        chunk["tier"].astype(str).str.extract(r"^(\d+)", expand=False),
        errors="coerce",
    ).astype("Int64")
    if "division" in chunk.columns:
        div_lower = chunk["division"].astype(str).str.lower()
        fallback = pd.Series(pd.NA, index=chunk.index, dtype="Int64")
        for name, tier in DIVISION_TO_TIER.items():
            hit = div_lower.str.contains(name, regex=False)
            fallback = fallback.mask(fallback.isna() & hit, tier)
        num = num.fillna(fallback)
    return num


# --------------------------------------------------------------------------
# pre-flight
# --------------------------------------------------------------------------
def preflight_check(csv_path: Path, skiprows: int) -> dict:
    tier_counts: Counter = Counter()
    season_min: int | None = None
    season_max: int | None = None
    total = 0

    reader = pd.read_csv(
        csv_path,
        dtype=str,
        chunksize=CHUNKSIZE,
        skiprows=skiprows,
        encoding="utf-8-sig",
        on_bad_lines="skip",
        keep_default_na=False,
        usecols=lambda c: c.strip() in ("key_id", "tier", "division", "season"),
    )

    with _make_bar(total=None, desc="pre-flight") as bar:
        for chunk in reader:
            chunk.columns = [str(c).strip() for c in chunk.columns]
            if "key_id" in chunk.columns:
                chunk = chunk[chunk["key_id"].str.strip().str.lower() != "key_id"]
            if chunk.empty:
                continue
            total += len(chunk)

            if "tier" in chunk.columns:
                for v in _infer_tiers(chunk):
                    tier_counts["unknown" if pd.isna(v) else int(v)] += 1

            if "season" in chunk.columns:
                for s in chunk["season"]:
                    ey = season_end_year(s)
                    if ey is None:
                        continue
                    season_min = ey if season_min is None else min(season_min, ey)
                    season_max = ey if season_max is None else max(season_max, ey)

            bar.update(len(chunk))

    return {
        "total": total,
        "tiers": dict(sorted(tier_counts.items(), key=lambda kv: str(kv[0]))),
        "season_min": season_min,
        "season_max": season_max,
    }


def print_preflight(info: dict, will_export: bool) -> None:
    print("Pre-flight check")
    print(f"  source file ............... {SOURCE_CSV}")
    print(f"  output folder ............. {OUTPUT_DIR}")
    print(f"  rows found ................ {info['total']:,}")
    if info["tiers"]:
        print("  rows per tier ............. " + ", ".join(
            f"tier {k}={v:,}" for k, v in info["tiers"].items()
        ))
        kept = sum(v for k, v in info["tiers"].items()
                   if isinstance(k, int) and k in TIERS_TO_KEEP)
        print(f"  rows in target tiers ...... {kept:,}  "
              f"(tiers {sorted(TIERS_TO_KEEP)})")
    if info["season_min"] is not None:
        print(f"  season end-year span ...... {info['season_min']} to "
              f"{info['season_max']}  (keeping up to {MAX_SEASON_END_YEAR})")
    if not will_export:
        print("  !! no rows in target tiers - nothing will be exported")
        print("  !! this file may only contain tier-1 / Premier League matches")
    print()


# --------------------------------------------------------------------------
# main
# --------------------------------------------------------------------------
def main() -> None:
    if not SOURCE_CSV.exists():
        raise SystemExit(f"Source CSV not found: {SOURCE_CSV}")

    # Does the first physical line really contain the header?
    with SOURCE_CSV.open("r", encoding="utf-8-sig", errors="replace") as fh:
        first_line = fh.readline()
    skiprows = 0 if "match_id" in first_line else 1

    # ---- pre-flight -------------------------------------------------------
    info = preflight_check(SOURCE_CSV, skiprows)
    will_export = any(
        isinstance(k, int) and k in TIERS_TO_KEEP and v > 0
        for k, v in info["tiers"].items()
    )
    print_preflight(info, will_export)
    if not will_export:
        print("Nothing to do - all rows are outside the target tiers.")
        return

    # ---- split ------------------------------------------------------------
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    written_files: set[Path] = set()
    counts: dict[tuple[str, int, str], int] = defaultdict(int)
    paths: dict[tuple[str, int, str], Path] = {}
    skipped_tier = 0
    skipped_season = 0
    skipped_unknown = 0
    kept_rows = 0

    reader = pd.read_csv(
        SOURCE_CSV,
        dtype=str,
        chunksize=CHUNKSIZE,
        skiprows=skiprows,
        encoding="utf-8-sig",
        on_bad_lines="skip",
        keep_default_na=False,
    )

    with _make_bar(total=info["total"], desc="splitting") as bar:
        for chunk in reader:
            chunk.columns = [str(c).strip() for c in chunk.columns]
            chunk = chunk[chunk["key_id"].str.strip().str.lower() != "key_id"]
            if chunk.empty:
                continue

            tier_num = _infer_tiers(chunk)
            end_years = chunk["season"].map(season_end_year)

            in_tier = tier_num.isin(TIERS_TO_KEEP)
            in_range = end_years.notna() & (end_years <= MAX_SEASON_END_YEAR)

            skipped_unknown += int(tier_num.isna().sum())
            skipped_tier += int((~in_tier & tier_num.notna()).sum())
            skipped_season += int((in_tier & ~in_range).sum())

            keep = in_tier & in_range
            chunk = chunk[keep].copy()
            if not chunk.empty:
                chunk["__tier"] = tier_num[keep].astype(int).values
                chunk["__season"] = [season_label(s) for s in chunk["season"]]

                if BY_TIER:
                    chunk["__league"] = chunk["__tier"].map(lambda t: f"Tier {t}")
                else:
                    chunk["__league"] = [
                        league_folder_name(t, d, s)
                        for t, d, s in zip(chunk["__tier"], chunk["division"],
                                           chunk["subdivision"])
                    ]

                for (league, tier, season), group in chunk.groupby(
                    ["__league", "__tier", "__season"], sort=True
                ):
                    folder = OUTPUT_DIR / league
                    folder.mkdir(parents=True, exist_ok=True)
                    path = folder / f"{season}.csv"

                    if path in written_files:
                        mode, header = "a", False
                    else:
                        written_files.add(path)
                        mode = "a" if APPEND_MODE else "w"
                        header = not (APPEND_MODE and path.exists())

                    group.drop(
                        columns=["__league", "__tier", "__season"]
                    ).to_csv(
                        path, mode=mode, header=header, index=False,
                        encoding="utf-8", quoting=1,
                    )

                    key = (league, int(tier), season)
                    counts[key] += len(group)
                    paths[key] = path
                    kept_rows += len(group)

            # advance bar by rows read (so total stays consistent) and post kept
            bar.update(len(chunk) if not chunk.empty else 0)
            bar.set_postfix(kept=f"{kept_rows:,}")

    # ---- manifest ---------------------------------------------------------
    manifest = OUTPUT_DIR / "manifest.csv"
    with manifest.open("w", newline="", encoding="utf-8") as fh:
        import csv as _csv
        w = _csv.writer(fh)
        w.writerow(["league", "tier", "season", "rows", "file"])
        for key in sorted(counts):
            league, tier, season = key
            w.writerow([league, tier, season, counts[key],
                        paths[key].relative_to(OUTPUT_DIR)])

    # ---- summary ----------------------------------------------------------
    print(f"Wrote {len(counts)} files, {kept_rows:,} matches "
          f"-> {OUTPUT_DIR.resolve()}")
    print(f"Manifest: {manifest}")
    if skipped_tier or skipped_season or skipped_unknown:
        print("Skipped rows:")
        if skipped_tier:
            print(f"  {skipped_tier:,} outside target tiers "
                  f"(tier 1 / Premier League etc.)")
        if skipped_season:
            print(f"  {skipped_season:,} after {MAX_SEASON_END_YEAR - 1}-"
                  f"{str(MAX_SEASON_END_YEAR)[-2:]}")
        if skipped_unknown:
            print(f"  {skipped_unknown:,} with no detectable tier")


if __name__ == "__main__":
    main()