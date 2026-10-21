"""
Render a 500 s / 5 fps / 1280x720 MP4 of the evolving Premier League table,
with looping background music.

One snapshot is emitted after every simulation (2500 total). At 5 fps and
500 s, that's exactly 2500 frames, so each snapshot is shown for 1 frame.
"""
import subprocess
import sys
import time
import importlib.util
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw, ImageFont

_SEASON_PATH = str(Path(__file__).resolve().with_name("26-27-season.py"))
spec = importlib.util.spec_from_file_location("season", _SEASON_PATH)
season = importlib.util.module_from_spec(spec)
sys.modules["season"] = season
spec.loader.exec_module(season)

# ------------------------------------------------------------------ #
# CONFIG
# ------------------------------------------------------------------ #
W, H       = 1280, 720
FPS        = 5
DURATION_S = 500                 # 8 min 20 s
N_SIMS     = 2500
N_SNAP     = N_SIMS              # one snapshot per sim
SNAP_EVERY = 1                   # emit a snapshot after every sim
HOLD       = DURATION_S * FPS // N_SNAP      # 1 frame per snapshot
OUT_PATH   = "pl_table_500s_5fps_720p.mp4"

# Background music (Windows path with spaces — raw string keeps backslashes)
AUDIO_PATH = r"C:\Users\liam\Pictures\apple its glowtime\iPhone 16\Y2Mate.is - Heroes Tonight - Janji feat Johnning Lyrics.mp3"

# ------------------------------------------------------------------ #
# FONTS
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
F_NOTE  = _font(13)

COL_X = dict(
    pos=20, team=80, pts=380, tt=470, ucl=570,
    uel=660, uecl=750, tot=840, rel=950,
)

def _fmt_time(seconds):
    seconds = int(seconds)
    return f"{seconds // 60:02d}:{seconds % 60:02d}"

# ------------------------------------------------------------------ #
# RENDER ONE FRAME
# ------------------------------------------------------------------ #
def render_frame(snap, sim_num, total_sims, W, H, frame_index, total_frames):
    # White background
    img  = Image.new("RGB", (W, H), (255, 255, 255))
    draw = ImageDraw.Draw(img)

    # ---- title bar (subtle light band) ----
    draw.rectangle([(0, 0), (W, 46)], fill=(240, 244, 252))
    draw.text((20, 10), "Premier League Projection  —  Unified Simulation",
              fill=(20, 30, 70), font=F_TITLE)
    draw.text((W - 230, 16),
              f"sim {sim_num:>4} / {total_sims}",
              fill=(40, 80, 160), font=F_HEAD)

    # ---- column headings ----
    heads = [
        (COL_X["pos"],  "Rk"),
        (COL_X["team"], "Team"),
        (COL_X["pts"],  "Pts"),
        (COL_X["tt"],   "Title%"),
        (COL_X["ucl"],  "UCL%"),
        (COL_X["uel"],  "UEL%"),
        (COL_X["uecl"], "UECL%"),
        (COL_X["tot"],  "Euro%"),
        (COL_X["rel"],  "Rel%"),
    ]
    for x, h in heads:
        draw.text((x, 58), h, fill=(60, 70, 110), font=F_HEAD)
    draw.line([(16, 82), (W - 16, 82)], fill=(180, 190, 210), width=1)

    # ---- table rows ----
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

        # Zone colouring + matching text colour for contrast on white bg
        if pos <= 5:
            bg = (30, 100, 200)      # UCL blue (incl. 5th via 93% England coeff)
            fg = (255, 255, 255)
        elif pos == 6:
            bg = (255, 140, 0)       # UEL orange
            fg = (20, 20, 20)
        elif pos >= 18:
            bg = (255, 228, 228)     # light red row
            fg = (200, 20, 20)       # RED numbers
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

    # ---- video timeline progress bar ----
    video_pct = frame_index / total_frames if total_frames else 0.0
    vbar_x0, vbar_x1 = 20, W - 20
    vbar_y0, vbar_y1 = H - 78, H - 66
    draw.rectangle([(vbar_x0, vbar_y0), (vbar_x1, vbar_y1)], fill=(225, 230, 240))
    draw.rectangle(
        [(vbar_x0, vbar_y0),
         (vbar_x0 + int((vbar_x1 - vbar_x0) * video_pct), vbar_y1)],
        fill=(0, 160, 110),
    )
    elapsed_s = frame_index / FPS
    total_s   = total_frames / FPS
    draw.text(
        (vbar_x0, vbar_y1 + 2),
        f"Video {_fmt_time(elapsed_s)} / {_fmt_time(total_s)}  •  {video_pct * 100:6.2f}%",
        fill=(20, 90, 60), font=F_NOTE,
    )

    # ---- simulation progress bar ----
    pct = sim_num / total_sims
    bar_x0, bar_x1 = 20, W - 20
    bar_y0, bar_y1 = H - 40, H - 22
    draw.rectangle([(bar_x0, bar_y0), (bar_x1, bar_y1)], fill=(225, 230, 240))
    draw.rectangle(
        [(bar_x0, bar_y0),
         (bar_x0 + int((bar_x1 - bar_x0) * pct), bar_y1)],
        fill=(30, 100, 200),
    )
    draw.text(
        (bar_x0, bar_y1 + 2),
        f"{pct * 100:6.2f}% complete  •  {sim_num} / {total_sims} sims",
        fill=(30, 70, 150), font=F_NOTE,
    )

    return np.asarray(img, dtype=np.uint8)

# ------------------------------------------------------------------ #
# MAIN
# ------------------------------------------------------------------ #
def main():
    snapshots = []

    def cb(completed, total, snap):
        snap = dict(snap)
        snap["_sim"] = completed
        snapshots.append(snap)

    print(f"Running {N_SIMS} simulations (snapshot after every sim) …")
    season.run_simulation(
        n_sims=N_SIMS,
        snapshot_callback=cb,
        snapshot_every=SNAP_EVERY,   # = 1  →  2500 snapshots
    )
    print(f"Captured {len(snapshots)} snapshots — encoding {DURATION_S}s video at {FPS} fps …")
    print(f"Audio: {AUDIO_PATH}")

    total_frames = DURATION_S * FPS  # 2500

    # ffmpeg: raw video from stdin + looping background music, cut to video length
    ff = subprocess.Popen(
        [
            "ffmpeg", "-y", "-hide_banner", "-loglevel", "error",
            "-f", "rawvideo", "-pix_fmt", "rgb24",
            "-s", f"{W}x{H}", "-r", str(FPS), "-i", "-",
            "-stream_loop", "-1", "-i", AUDIO_PATH,   # loop music forever
            "-map", "0:v:0", "-map", "1:a:0",
            "-c:v", "libx264", "-preset", "medium", "-crf", "20",
            "-pix_fmt", "yuv420p",
            "-c:a", "aac", "-b:a", "192k", "-ar", "44100",
            "-shortest",                              # stop when video ends
            "-movflags", "+faststart",
            OUT_PATH,
        ],
        stdin=subprocess.PIPE, stdout=subprocess.DEVNULL,
    )

    def _print_progress(written, total, t0):
        pct     = written / total if total else 1.0
        elapsed = time.time() - t0
        fps     = written / elapsed if elapsed > 0 else 0.0
        eta     = (total - written) / fps if fps > 0 else 0.0
        bar_w   = 30
        filled  = int(bar_w * pct)
        bar     = "█" * filled + "░" * (bar_w - filled)
        sys.stdout.write(
            f"\r  [{bar}] {pct*100:6.2f}%  "
            f"{written:>5}/{total} frames  "
            f"{fps:5.1f} fps  "
            f"elapsed {_fmt_time(elapsed)}  "
            f"ETA {_fmt_time(eta)}"
        )
        sys.stdout.flush()

    written    = 0
    last_snap  = None
    t0         = time.time()
    last_print = 0.0

    for snap in snapshots:
        last_snap = snap
        img = render_frame(
            snap, snap["_sim"], N_SIMS, W, H,
            frame_index=written, total_frames=total_frames,
        )
        for _ in range(HOLD):          # HOLD = 1 at 5 fps
            ff.stdin.write(img.tobytes())
            written += 1

            now = time.time()
            if now - last_print >= 0.1:
                _print_progress(written, total_frames, t0)
                last_print = now

            if written >= total_frames:
                break
        if written >= total_frames:
            break

    # Pad if the last snapshot needs more frames (paranoia)
    while written < total_frames and last_snap is not None:
        img = render_frame(
            last_snap, last_snap["_sim"], N_SIMS, W, H,
            frame_index=written, total_frames=total_frames,
        )
        ff.stdin.write(img.tobytes())
        written += 1
        now = time.time()
        if now - last_print >= 0.1:
            _print_progress(written, total_frames, t0)
            last_print = now

    ff.stdin.close()
    ff.wait()

    _print_progress(written, total_frames, t0)   # final 100% line
    sys.stdout.write("\n")
    sys.stdout.flush()
    print(f"Done → {OUT_PATH}  ({written} frames @ {FPS} fps = {written / FPS:.0f}s)")

if __name__ == "__main__":
    main()