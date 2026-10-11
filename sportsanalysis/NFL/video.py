#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
NFL — all-time franchise table (MP4).

Landscape 720p (1280x720), 16:9.

Updates every single game. Lifetime stats from the earliest game in the
CSV to the latest. No season reset.

Sorted by raw win percentage (W / GP). Ties broken by games played so a
team with a longer proven record sits above one with fewer games at the
same win rate.

Columns: # | Team | W% | D% | L% | H-PPG | A-PPG | GP | W | D | L

Run from PowerShell:
    python video.py
    python video.py -f "C:\\path\\to\\spreadspoke_scores.csv"
"""

import csv
import glob
import os
import sys
import multiprocessing as mp
from functools import lru_cache
from collections import defaultdict
from datetime import datetime

import numpy as np
from PIL import Image, ImageDraw, ImageFont
import imageio.v2 as imageio
from tqdm.auto import tqdm


# ----------------------------------------------------------------------
# CONFIG
# ----------------------------------------------------------------------
CSV_PATH = r"C:\Users\liam\Documents\GitHub\all-of-my-code\sportsanalysis\NFL\spreadspoke_scores.csv"

OUTPUT           = "nfl_table.mp4"
DISPLAY_SIZE     = 32                # NFL has 32 franchises; show them all
GAMES_PER_SECOND = 20.0               # playback speed (games per second)
FPS              = 20
WIDTH, HEIGHT    = 1280, 720         # 16:9, 720p landscape

PRESET           = "veryfast"
X264_TUNE        = "stillimage"
QUALITY          = 8
CHUNKSIZE        = 4
WORKERS          = None

TITLE_MAIN       = "NFL"
TITLE_SUB        = "ALL-TIME FRANCHISE TABLE  \u2022  WIN %"


# ----------------------------------------------------------------------
# Jupyter detection
# ----------------------------------------------------------------------
def _running_in_jupyter():
    if "ipykernel" in sys.modules or "ipykernel_launcher" in sys.modules:
        return True
    if "IPython" in sys.modules:
        try:
            from IPython import get_ipython  # noqa
            if get_ipython() is not None:
                return True
        except Exception:
            pass
    return False


IN_JUPYTER = _running_in_jupyter()

FLAG_TAKES_VALUE = {"-f", "--file", "--csv", "-i", "--input",
                    "-o", "--output"}


def parse_positional_args():
    if IN_JUPYTER:
        return []
    argv = sys.argv[1:]
    positional = []
    i = 0
    while i < len(argv):
        a = argv[i]
        if a in FLAG_TAKES_VALUE:
            if i + 1 < len(argv):
                positional.append(argv[i + 1])
                i += 2
                continue
            i += 1
            continue
        if a.startswith("-"):
            i += 1
            continue
        positional.append(a)
        i += 1
    return positional


def clean(p):
    return p.strip().strip('"').strip("'")


def _is_csv(p):
    return p.lower().endswith(".csv")


# ----------------------------------------------------------------------
# Path resolution
# ----------------------------------------------------------------------
def resolve_csv_path(positional):
    for p in positional:
        cp = clean(p)
        if os.path.isdir(cp):
            return cp
        if os.path.isfile(cp) and _is_csv(cp):
            return cp
    if os.path.isdir(CSV_PATH):
        return CSV_PATH
    if os.path.isfile(CSV_PATH) and _is_csv(CSV_PATH):
        return CSV_PATH
    for name in ("spreadspoke_scores.csv", "nfl.csv", "scores.csv"):
        if os.path.isfile(name):
            return os.path.abspath(name)
    return None


def resolve_output_path(positional):
    for p in positional[1:]:
        cp = clean(p)
        if cp and cp.lower().endswith(".mp4"):
            return cp
    return os.path.join(os.getcwd(), OUTPUT)


# ----------------------------------------------------------------------
# Fonts — cached so they load once per process, not per frame
# ----------------------------------------------------------------------
@lru_cache(maxsize=32)
def load_font(size, bold=False):
    candidates = [
        "C:/Windows/Fonts/arialbd.ttf" if bold else "C:/Windows/Fonts/arial.ttf",
        "C:/Windows/Fonts/segoeuib.ttf" if bold else "C:/Windows/Fonts/segoeui.ttf",
        "C:/Windows/Fonts/calibrib.ttf" if bold else "C:/Windows/Fonts/calibri.ttf",
        "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf" if bold
            else "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
        "/System/Library/Fonts/Supplemental/Arial Bold.ttf" if bold
            else "/System/Library/Fonts/Supplemental/Arial.ttf",
    ]
    for path in candidates:
        if os.path.exists(path):
            try:
                return ImageFont.truetype(path, size)
            except Exception:
                continue
    return ImageFont.load_default()


# ----------------------------------------------------------------------
# CSV loading — NFL "spreadspoke_scores" layout
# ----------------------------------------------------------------------
ALIASES = {
    "date":       ["schedule_date", "date", "game_date", "match_date"],
    "season":     ["schedule_season", "season", "year"],
    "home_team":  ["team_home", "home_team", "home", "hometeam"],
    "away_team":  ["team_away", "away_team", "away", "awayteam"],
    "home_score": ["score_home", "home_score", "home score",
                   "homescore", "home_goals"],
    "away_score": ["score_away", "away_score", "away score",
                   "awayscore", "away_goals"],
}

DATE_FORMATS = ("%m/%d/%Y", "%Y-%m-%d", "%d/%m/%Y", "%d/%m/%y",
                "%d-%m-%Y", "%Y/%m/%d", "%m/%d/%y")


def _norm(s):
    return s.strip().strip('"').strip("'").lstrip("\ufeff").lower()


def _parse_date(s):
    s = s.strip()
    for fmt in DATE_FORMATS:
        try:
            return datetime.strptime(s, fmt).date()
        except ValueError:
            continue
    raise ValueError("Unparseable date: {!r}".format(s))


def _find_column(header_cells, field):
    for alias in ALIASES[field]:
        if alias in header_cells:
            return header_cells.index(alias)
    return None


def _load_single_csv(path):
    if not _is_csv(path):
        print("[load_matches] Skipping non-CSV file:", path)
        return []

    try:
        with open(path, newline="", encoding="utf-8-sig",
                  errors="replace") as f:
            raw = list(csv.reader(f))
    except OSError as e:
        print("[load_matches] Could not read {}: {}".format(path, e))
        return []

    rows = [r for r in raw if any(c.strip() for c in r)]
    if not rows:
        print("[load_matches] File appears empty:", path)
        return []

    header_idx = None
    idx = None
    for i, r in enumerate(rows[:10]):
        cells = [_norm(c) for c in r]
        candidate = {field: _find_column(cells, field) for field in ALIASES}
        required = ["date", "home_team", "away_team",
                    "home_score", "away_score"]
        if all(candidate.get(k) is not None for k in required):
            header_idx = i
            idx = candidate
            break

    if header_idx is None:
        print("[load_matches] No header row detected in {}".format(
            os.path.basename(path)))
        return []

    data_rows = rows[header_idx + 1:]

    matches = []
    skipped = 0
    max_i = max(v for v in idx.values() if v is not None)
    for r in data_rows:
        if len(r) <= max_i:
            skipped += 1
            continue
        try:
            d  = _parse_date(r[idx["date"]])
            hs_raw = r[idx["home_score"]].strip()
            as_raw = r[idx["away_score"]].strip()
            if not hs_raw or not as_raw:
                skipped += 1
                continue
            hs = int(float(hs_raw))
            ag = int(float(as_raw))
            if hs < 0 or ag < 0:
                skipped += 1
                continue
        except (ValueError, IndexError, TypeError):
            skipped += 1
            continue
        home = r[idx["home_team"]].strip()
        away = r[idx["away_team"]].strip()
        if not home or not away:
            skipped += 1
            continue
        season = None
        if idx.get("season") is not None:
            try:
                season = r[idx["season"]].strip()
            except IndexError:
                season = None
        matches.append({
            "date":   d,
            "home":   home,
            "away":   away,
            "hs":     hs,
            "as":     ag,
            "season": season,
        })

    if skipped:
        print("[load_matches] {} — skipped {} unparseable rows".format(
            os.path.basename(path), skipped))

    return matches


def load_matches(path):
    if os.path.isdir(path):
        files = sorted(glob.glob(os.path.join(path, "*.csv")))
        if not files:
            files = sorted(glob.glob(os.path.join(path, "*", "*.csv")))
        if not files:
            print("[load_matches] No CSVs found in directory:", path)
            return []
        print("[load_matches] Loading {} CSV file(s) from {}".format(
            len(files), path))
        all_matches = []
        for f in files:
            all_matches.extend(_load_single_csv(f))
        all_matches.sort(key=lambda m: m["date"])
        return all_matches

    return _load_single_csv(path)


# ----------------------------------------------------------------------
# All teams
# ----------------------------------------------------------------------
def all_teams(matches):
    names = set()
    for m in matches:
        names.add(m["home"])
        names.add(m["away"])
    return sorted(names)


# ----------------------------------------------------------------------
# Lifetime stats
# ----------------------------------------------------------------------
def empty_row():
    return {
        "GP": 0, "W": 0, "D": 0, "L": 0,
        "HomeGP": 0, "HomePts": 0,     # points scored while at home
        "AwayGP": 0, "AwayPts": 0,     # points scored while away
    }


def apply_result(row_home, row_away, hs, as_):
    # Home team
    row_home["GP"] += 1
    row_home["HomeGP"] += 1
    row_home["HomePts"] += hs
    if hs > as_:
        row_home["W"] += 1
    elif hs == as_:
        row_home["D"] += 1
    else:
        row_home["L"] += 1

    # Away team
    row_away["GP"] += 1
    row_away["AwayGP"] += 1
    row_away["AwayPts"] += as_
    if as_ > hs:
        row_away["W"] += 1
    elif as_ == hs:
        row_away["D"] += 1
    else:
        row_away["L"] += 1


# ----------------------------------------------------------------------
# Ranking — sorted by the raw win percentage that is shown on screen.
# GP is the tiebreaker so a team with more games beats one with fewer
# when their win percentages are identical.
# ----------------------------------------------------------------------
def raw_win_pct(r):
    gp = r["GP"]
    return (r["W"] / gp) if gp else 0.0


def rank(stats):
    def key(item):
        t, r = item
        return (-raw_win_pct(r), -r["GP"], -r["W"], t)
    return sorted(stats.items(), key=key)


# ----------------------------------------------------------------------
# Snapshots — one per game
# ----------------------------------------------------------------------
def build_snapshots(matches, teams):
    rows = {t: empty_row() for t in teams}
    snapshots = []

    for m in matches:
        apply_result(rows[m["home"]], rows[m["away"]], m["hs"], m["as"])

        combined = {t: dict(r) for t, r in rows.items()}
        frozen = rank(combined)
        snapshots.append((m["date"], frozen))

    return snapshots


# ----------------------------------------------------------------------
# Rendering
# ----------------------------------------------------------------------
def render_frame(snapshot, w=WIDTH, h=HEIGHT, display_size=DISPLAY_SIZE):
    date, ranked = snapshot
    img = Image.new("RGB", (w, h), "white")
    d = ImageDraw.Draw(img)

    f_big   = load_font(34, bold=True)
    f_med   = load_font(20, bold=True)
    f_row   = load_font(15)
    f_hdr   = load_font(14, bold=True)

    d.text((w // 2, 12), TITLE_MAIN,
           font=f_big, fill=(10, 10, 60), anchor="mt")
    d.text((w // 2, 50), TITLE_SUB,
           font=f_med, fill=(120, 120, 120), anchor="mt")
    d.text((w // 2, 76), date.strftime("%d %b %Y"),
           font=f_med, fill=(0, 0, 0), anchor="mt")

    y_hdr = 108
    d.line([(20, y_hdr - 6), (w - 20, y_hdr - 6)], fill=(0, 0, 0), width=2)

    # Column x-positions --------------------------------------------------
    col_pos   = 30
    col_team  = 65
    col_wpct  = 400
    col_dpct  = 490
    col_lpct  = 580
    col_hppg  = 670
    col_appg  = 760
    col_gp    = 850
    col_w     = 915
    col_d     = 980
    col_l     = 1045

    d.text((col_pos,   y_hdr), "#",     font=f_hdr, fill=(60, 60, 60))
    d.text((col_team,  y_hdr), "TEAM",  font=f_hdr, fill=(60, 60, 60))
    d.text((col_wpct,  y_hdr), "W%",    font=f_hdr, fill=(60, 60, 60))
    d.text((col_dpct,  y_hdr), "D%",    font=f_hdr, fill=(60, 60, 60))
    d.text((col_lpct,  y_hdr), "L%",    font=f_hdr, fill=(60, 60, 60))
    d.text((col_hppg,  y_hdr), "H-PPG", font=f_hdr, fill=(60, 60, 60))
    d.text((col_appg,  y_hdr), "A-PPG", font=f_hdr, fill=(60, 60, 60))
    d.text((col_gp,    y_hdr), "GP",    font=f_hdr, fill=(60, 60, 60))
    d.text((col_w,     y_hdr), "W",     font=f_hdr, fill=(60, 60, 60))
    d.text((col_d,     y_hdr), "D",     font=f_hdr, fill=(60, 60, 60))
    d.text((col_l,     y_hdr), "L",     font=f_hdr, fill=(60, 60, 60))

    y_hdr_end = y_hdr + 22
    d.line([(20, y_hdr_end), (w - 20, y_hdr_end)],
           fill=(170, 170, 170), width=1)

    top = ranked[:display_size]
    n = len(top)
    top_y = y_hdr_end + 6
    avail = h - top_y - 16
    row_h = max(14, avail // max(n, 1))

    # Subtle vertical grid separators
    for x in (col_wpct - 12, col_hppg - 12, col_gp - 12):
        d.line([(x, y_hdr_end), (x, h - 10)], fill=(225, 225, 225), width=1)

    for i, (team, r) in enumerate(top):
        pos = i + 1
        y = top_y + i * row_h

        gp = r["GP"]
        if gp:
            w_pct = r["W"] / gp
            d_pct = r["D"] / gp
            l_pct = r["L"] / gp
        else:
            w_pct = d_pct = l_pct = 0.0

        h_ppg = (r["HomePts"] / r["HomeGP"]) if r["HomeGP"] else 0.0
        a_ppg = (r["AwayPts"] / r["AwayGP"]) if r["AwayGP"] else 0.0

        # Top 4 green, bottom 3 red (based on the currently shown set)
        if pos <= 4:
            color = (0, 130, 0)
        elif n >= 6 and pos > n - 3:
            color = (190, 0, 0)
        else:
            color = (20, 20, 20)

        # 3-decimal formatting with a leading "." for a cleaner look
        w_txt = "{:.3f}".format(w_pct).lstrip("0")
        d_txt = "{:.3f}".format(d_pct).lstrip("0")
        l_txt = "{:.3f}".format(l_pct).lstrip("0")

        d.text((col_pos,   y), str(pos),       font=f_row, fill=color)
        d.text((col_team,  y), team,           font=f_row, fill=color)
        d.text((col_wpct,  y), w_txt,          font=f_row, fill=color)
        d.text((col_dpct,  y), d_txt,          font=f_row, fill=color)
        d.text((col_lpct,  y), l_txt,          font=f_row, fill=color)
        d.text((col_hppg,  y), "{:5.1f}".format(h_ppg),
               font=f_row, fill=color)
        d.text((col_appg,  y), "{:5.1f}".format(a_ppg),
               font=f_row, fill=color)
        d.text((col_gp,    y), str(gp),        font=f_row, fill=color)
        d.text((col_w,     y), str(r["W"]),    font=f_row, fill=color)
        d.text((col_d,     y), str(r["D"]),    font=f_row, fill=color)
        d.text((col_l,     y), str(r["L"]),    font=f_row, fill=color)

    return img


def _render_worker(args):
    snapshot, w, h, display_size = args
    img = render_frame(snapshot, w, h, display_size)
    return np.asarray(img, dtype=np.uint8).tobytes()


# ----------------------------------------------------------------------
# Output frame distribution
# ----------------------------------------------------------------------
def precompute_frame_counts(n_snapshots, total_frames):
    counts = [0] * n_snapshots
    if n_snapshots == 0 or total_frames <= 0:
        return counts
    for i in range(total_frames):
        idx = int(i * n_snapshots / total_frames)
        if idx >= n_snapshots:
            idx = n_snapshots - 1
        counts[idx] += 1
    return counts


def default_workers():
    if WORKERS is not None:
        return WORKERS
    try:
        n = mp.cpu_count() or 1
    except Exception:
        n = 1
    return max(1, n - 1)


# ----------------------------------------------------------------------
# Main
# ----------------------------------------------------------------------
def main():
    positional = parse_positional_args()

    in_path = resolve_csv_path(positional)
    if not in_path:
        sys.exit(
            "Could not find the NFL scores CSV.\n"
            "Make sure this file exists:\n"
            "    {}\n"
            "Or pass a path explicitly:\n"
            "    python video.py -f \"C:\\full\\path\\spreadspoke_scores.csv\""
            .format(CSV_PATH)
        )

    out_path = os.path.abspath(resolve_output_path(positional))
    print("Input:   {}".format(in_path))
    print("Output:  {}".format(out_path))
    print("Workers: {}".format(default_workers()))

    # --- Load CSV -----------------------------------------------------
    with tqdm(total=1, desc="Loading CSV", unit="file",
              bar_format="{l_bar}{bar}| {n_fmt}/{total_fmt}") as pbar:
        matches = load_matches(in_path)
        pbar.update(1)

    if not matches:
        sys.exit("No valid games parsed from {}".format(in_path))
    print("  {} games  ({} -> {})".format(
        len(matches), matches[0]["date"], matches[-1]["date"]))

    teams = all_teams(matches)
    print("  {} unique teams".format(len(teams)))

    # --- Snapshots (one per game) -------------------------------------
    snapshots = build_snapshots(matches, teams)
    n_snaps = len(snapshots)
    print("  {} game snapshots".format(n_snaps))
    if not snapshots:
        sys.exit("No snapshots built.")

    # --- Frame counts -------------------------------------------------
    total_frames = max(1, int(round(n_snaps * FPS / GAMES_PER_SECOND)))
    frame_counts = precompute_frame_counts(n_snaps, total_frames)
    duration_sec = total_frames / FPS
    print("  {} output frames at {} fps (~{:.1f}s = {:d}m{:02d}s) — "
          "{:.1f} games/s".format(
              total_frames, FPS, duration_sec,
              int(duration_sec // 60), int(duration_sec % 60),
              n_snaps / duration_sec if duration_sec else 0.0))

    # --- Writer -------------------------------------------------------
    writer_kwargs = dict(
        fps=FPS, codec="libx264", quality=QUALITY,
        macro_block_size=None,
    )
    try:
        writer = imageio.get_writer(
            out_path,
            output_params=["-preset", PRESET, "-tune", X264_TUNE],
            **writer_kwargs
        )
    except Exception:
        writer = imageio.get_writer(out_path, **writer_kwargs)

    # --- Render + encode streaming ------------------------------------
    tasks = [(snap, WIDTH, HEIGHT, DISPLAY_SIZE) for snap in snapshots]
    n_workers = default_workers()

    pbar = tqdm(total=total_frames, desc="Render + encode", unit="frame",
                bar_format="{l_bar}{bar}| {n_fmt}/{total_fmt} "
                           "[{elapsed}<{remaining}, {rate_fmt}]")

    try:
        if n_workers > 1:
            pool = mp.Pool(processes=n_workers)
            try:
                for snap_idx, buf in enumerate(
                        pool.imap(_render_worker, tasks,
                                  chunksize=CHUNKSIZE)):
                    arr = np.frombuffer(buf, dtype=np.uint8).reshape(
                        HEIGHT, WIDTH, 3)
                    for _ in range(frame_counts[snap_idx]):
                        writer.append_data(arr)
                        pbar.update(1)
            finally:
                pool.close()
                pool.join()
        else:
            for snap_idx, snap in enumerate(snapshots):
                img = render_frame(snap, WIDTH, HEIGHT, DISPLAY_SIZE)
                arr = np.asarray(img, dtype=np.uint8)
                for _ in range(frame_counts[snap_idx]):
                    writer.append_data(arr)
                    pbar.update(1)
    finally:
        pbar.close()
        writer.close()

    print("Done: {}".format(out_path))


if __name__ == "__main__":
    main()