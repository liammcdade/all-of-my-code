"""
Render a 300-520 s / 1280x720 MP4 of the evolving Premier League table,
with looping background music.

Run after each game day. Per run:
  * duration_s is any integer in [300, 520]  →  fps = N_SIMS / duration_s
    (all 2500 snapshots shown exactly once; e.g. 300s→8.33fps, 520s→4.81fps)
  * audio start offset is randomised so the looped track isn't identical

Parallelised: frame rendering across worker processes; ffmpeg stdin writes
on a dedicated writer thread.
"""
import argparse
import os
import queue
import random
import subprocess
import sys
import threading
import time
import importlib.util
from concurrent.futures import ProcessPoolExecutor
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw, ImageFont

# ------------------------------------------------------------------ #
# CONFIG
# ------------------------------------------------------------------ #
W, H = 1280, 720

DURATION_S_MIN = 300
DURATION_S_MAX = 520

N_SIMS     = 25000
SNAP_EVERY = 1

N_WORKERS  = max(1, (os.cpu_count() or 4) - 2)

AUDIO_PATH = r"C:\Users\liam\Pictures\apple its glowtime\iPhone 16\Y2Mate.is - Heroes Tonight - Janji feat Johnning Lyrics.mp3"

# Start somewhere in the first AUDIO_OFFSET_MAX s of the track, looping from there.
AUDIO_OFFSET_MAX = 150.0

# ------------------------------------------------------------------ #
# FONTS  (module-level so spawned workers can use them)
# ------------------------------------------------------------------ #
def _font(size):
    for name in ("arial.ttf", "DejaVuSans.ttf", "LiberationSans-Regular.ttf"):
        try:
            return ImageFont.truetype(name, size)
        except OSError:
            pass
    return ImageFont.load_default()

F_TITLE = _font(24)
F_HEAD  = _font(16)
F_ROW   = _font(15)

COL_X = dict(
    pos=20, team=80, pts=380, tt=470, ucl=570,
    uel=660, uecl=750, tot=840, rel=950,
)

def _fmt_time(seconds):
    seconds = int(seconds)
    return f"{seconds // 60:02d}:{seconds % 60:02d}"

# ------------------------------------------------------------------ #
# RENDER ONE FRAME  (module-level so it is picklable)
# ------------------------------------------------------------------ #
def render_frame(snap, sim_num, total_sims, W, H):
    img  = Image.new("RGB", (W, H), (255, 255, 255))
    draw = ImageDraw.Draw(img)

    draw.rectangle([(0, 0), (W, 46)], fill=(240, 244, 252))
    draw.text((20, 10), "Premier League Projection  —  Unified Simulation",
              fill=(20, 30, 70), font=F_TITLE)
    draw.text((W - 230, 16),
              f"sim {sim_num:>4} / {total_sims}",
              fill=(40, 80, 160), font=F_HEAD)

    heads = [
        (COL_X["pos"],  "Rk"),   (COL_X["team"], "Team"),
        (COL_X["pts"],  "Pts"),  (COL_X["tt"],   "Title%"),
        (COL_X["ucl"],  "UCL%"), (COL_X["uel"],  "UEL%"),
        (COL_X["uecl"], "UECL%"),(COL_X["tot"],  "Euro%"),
        (COL_X["rel"],  "Rel%"),
    ]
    for x, h in heads:
        draw.text((x, 58), h, fill=(60, 70, 110), font=F_HEAD)
    draw.line([(16, 82), (W - 16, 82)], fill=(180, 190, 210), width=1)

    teams = sorted(snap["avg_positions"].keys(),
                   key=lambda t: snap["avg_positions"][t])

    y = 92
    row_h = 27
    for i, team in enumerate(teams):
        pos   = i + 1
        rel   = snap["relegation_prob"].get(team, 0)
        title = snap["title_prob"].get(team, 0)
        ucl   = snap["ucl_qual_prob"].get(team, 0)
        uel   = snap["uel_qual_prob"].get(team, 0)
        uecl  = snap["uecl_qual_prob"].get(team, 0)
        euro  = snap["total_euro_prob"].get(team, 0)
        pts   = snap["avg_points"].get(team, 0)

        if pos <= 5:
            bg, fg = (30, 100, 200), (255, 255, 255)
        elif pos == 6:
            bg, fg = (255, 140, 0), (20, 20, 20)
        elif pos >= 18:
            bg, fg = (255, 228, 228), (200, 20, 20)
        else:
            bg = (245, 247, 250) if pos % 2 == 0 else (255, 255, 255)
            fg = (20, 20, 20)

        draw.rectangle([(10, y - 2), (W - 10, y + row_h - 4)], fill=bg)

        vals = [
            (COL_X["pos"],  str(pos)),
            (COL_X["team"], team[:24]),
            (COL_X["pts"],  f"{pts:6.2f}"),
            (COL_X["tt"],   f"{title:6.2f}"),
            (COL_X["ucl"],  f"{ucl:6.2f}"),
            (COL_X["uel"],  f"{uel:6.2f}"),
            (COL_X["uecl"], f"{uecl:6.2f}"),
            (COL_X["tot"],  f"{euro:6.2f}"),
            (COL_X["rel"],  f"{rel:6.2f}"),
        ]
        for x, s in vals:
            draw.text((x, y), s, fill=fg, font=F_ROW)
        y += row_h

    return np.asarray(img, dtype=np.uint8)

def _render_worker(item):
    _, snap = item
    return render_frame(snap, snap["_sim"], N_SIMS, W, H).tobytes()

# ------------------------------------------------------------------ #
# SEASON LOADER — only called in the main process
# ------------------------------------------------------------------ #
def _load_season():
    season_path = str(Path(__file__).resolve().with_name("26-27-season.py"))
    spec = importlib.util.spec_from_file_location("season", season_path)
    season = importlib.util.module_from_spec(spec)
    sys.modules["season"] = season
    spec.loader.exec_module(season)
    return season

# ------------------------------------------------------------------ #
# FFMPEG STDIN WRITER THREAD
# ------------------------------------------------------------------ #
def _writer_loop(stdin, q, errors):
    try:
        while True:
            buf = q.get()
            if buf is None:
                break
            stdin.write(buf)
    except Exception as e:
        errors.append(e)
    finally:
        try:
            stdin.close()
        except Exception:
            pass

def _print_progress(written, total, t0):
    pct     = written / total if total else 1.0
    elapsed = time.time() - t0
    enc_fps = written / elapsed if elapsed > 0 else 0.0
    eta     = (total - written) / enc_fps if enc_fps > 0 else 0.0
    bar_w   = 30
    filled  = int(bar_w * pct)
    bar     = "█" * filled + "░" * (bar_w - filled)
    sys.stdout.write(
        f"\r  [{bar}] {pct*100:6.2f}%  "
        f"{written:>5}/{total} frames  "
        f"{enc_fps:5.1f} enc-fps  "
        f"elapsed {_fmt_time(elapsed)}  "
        f"ETA {_fmt_time(eta)}"
    )
    sys.stdout.flush()

# ------------------------------------------------------------------ #
# MAIN
# ------------------------------------------------------------------ #
def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--duration", type=int, default=None,
        help=f"Video duration in seconds ({DURATION_S_MIN}-{DURATION_S_MAX}); "
             f"any integer. Omit for random.")
    parser.add_argument("--audio-offset", type=float, default=None,
        help="Override the audio start offset in seconds. Omit for random.")
    args = parser.parse_args()

    if args.duration is not None:
        if not (DURATION_S_MIN <= args.duration <= DURATION_S_MAX):
            raise SystemExit(
                f"--duration must be in [{DURATION_S_MIN}, {DURATION_S_MAX}] seconds"
            )
        duration_s = args.duration
    else:
        duration_s = random.randint(DURATION_S_MIN, DURATION_S_MAX)

    audio_offset = (round(max(0.0, args.audio_offset), 2)
                    if args.audio_offset is not None
                    else round(random.uniform(0.0, AUDIO_OFFSET_MAX), 2))

    # ---- simulate ----
    season = _load_season()
    snapshots = []

    def cb(completed, total, snap):
        snap = dict(snap)
        snap["_sim"] = completed
        snapshots.append(snap)

    print(f"Running {N_SIMS} simulations (snapshot after every sim) …")
    season.run_simulation(
        n_sims=N_SIMS,
        snapshot_callback=cb,
        snapshot_every=SNAP_EVERY,
    )
    print(f"Captured {len(snapshots)} snapshots")

    if not snapshots:
        raise SystemExit("No snapshots captured; aborting.")

    total_frames = len(snapshots)                 # 2500
    video_fps    = total_frames / duration_s
    fps_arg      = f"{total_frames}/{duration_s}" # exact rational for ffmpeg

    out_path = f"pl_table_{duration_s}s_{video_fps:.2f}fps_720p.mp4"

    print(f"Duration:     {duration_s}s  →  {total_frames} frames "
          f"@ {video_fps:.4f} fps")
    print(f"Audio offset: {audio_offset:.2f}s into track")
    print(f"Output:       {out_path}")
    print(f"Workers:      {N_WORKERS}  (cpu_count={os.cpu_count()})")

    tasks = [(i, snapshots[i]) for i in range(total_frames)]

    # ---- ffmpeg  (-ss BEFORE -i so it seeks in the input) ----
    ff = subprocess.Popen(
        [
            "ffmpeg", "-y", "-hide_banner", "-loglevel", "error",
            "-f", "rawvideo", "-pix_fmt", "rgb24",
            "-s", f"{W}x{H}", "-r", fps_arg, "-i", "-",
            "-ss", f"{audio_offset:.3f}",
            "-stream_loop", "-1", "-i", AUDIO_PATH,
            "-map", "0:v:0", "-map", "1:a:0",
            "-c:v", "libx264", "-preset", "medium", "-crf", "20",
            "-pix_fmt", "yuv420p",
            "-c:a", "aac", "-b:a", "192k", "-ar", "44100",
            "-shortest",
            "-movflags", "+faststart",
            out_path,
        ],
        stdin=subprocess.PIPE, stdout=subprocess.DEVNULL,
    )

    # ---- parallel render → writer thread → ffmpeg ----
    write_q   = queue.Queue(maxsize=N_WORKERS * 4)
    write_err = []
    writer = threading.Thread(
        target=_writer_loop, args=(ff.stdin, write_q, write_err), daemon=True
    )
    writer.start()

    written    = 0
    t0         = time.time()
    last_print = 0.0
    batch_size = max(N_WORKERS * 4, 16)

    try:
        with ProcessPoolExecutor(max_workers=N_WORKERS) as ex:
            for bs in range(0, total_frames, batch_size):
                be    = min(bs + batch_size, total_frames)
                batch = tasks[bs:be]
                for raw in ex.map(_render_worker, batch, chunksize=1):
                    write_q.put(raw)
                    written += 1
                    now = time.time()
                    if now - last_print >= 0.1:
                        _print_progress(written, total_frames, t0)
                        last_print = now
    finally:
        write_q.put(None)
        writer.join()
        ff.wait()

    _print_progress(written, total_frames, t0)
    sys.stdout.write("\n")
    sys.stdout.flush()

    if write_err:
        raise write_err[0]

    print(f"Done → {out_path}  ({written} frames @ {video_fps:.4f} fps "
          f"= {written / video_fps:.1f}s)")

if __name__ == "__main__":
    main()