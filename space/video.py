# pip install pandas numpy matplotlib tqdm
# ffmpeg required on PATH for MP4 export.

import time
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import matplotlib.animation as animation
from tqdm import tqdm

CSV_PATH     = r"C:\Users\liam\Documents\GitHub\all-of-my-code\space\Global_Space_Exploration_Dataset.csv"
OUT_PATH     = "humanity_space_journey.mp4"

DURATION_SEC = 16
FPS          = 10
TRAIL_FRAMES = 120
DPI          = 100          # 140 was overkill for MP4
BLIT         = False        # set True for a big speedup once you confirm output looks right

# ------------------------------------------------------------
# 1. Load and clean
# ------------------------------------------------------------
df = pd.read_csv(CSV_PATH)
df["Year"] = pd.to_numeric(df["Year"], errors="coerce")
df = df.dropna(subset=["Year", "Success Rate (%)", "Budget (in Billion $)"]).copy()
df["Year"] = df["Year"].astype(int)

df["n_collab"] = (
    df["Collaborating Countries"].fillna("")
      .apply(lambda x: len([c for c in str(x).split(",") if c.strip()]))
)

years = np.arange(df["Year"].min(), df["Year"].max() + 1)

# ------------------------------------------------------------
# 2. Global yearly aggregates
# ------------------------------------------------------------
yearly = df.groupby("Year").agg(
    missions     =("Mission Name", "count"),
    budget       =("Budget (in Billion $)", "sum"),
    success_mean =("Success Rate (%)", "mean"),
    collab_sum   =("n_collab", "sum"),
).reindex(years).fillna(0)

yearly["success_w"] = df.groupby("Year")["Success Rate (%)"].mean().reindex(years)

yearly["cum_budget"]   = yearly["budget"].cumsum()
yearly["cum_missions"] = yearly["missions"].cumsum()

numer = (yearly["success_w"].fillna(0) * yearly["missions"]).cumsum()
yearly["cum_success"] = numer / yearly["cum_missions"].replace(0, np.nan)
yearly["cum_success"] = yearly["cum_success"].ffill().fillna(0)

yearly["collab_ratio"] = yearly["collab_sum"] / yearly["missions"].replace(0, np.nan)
yearly["collab_ratio"] = yearly["collab_ratio"].fillna(0)

# ------------------------------------------------------------
# 3. Interpolation timeline
# ------------------------------------------------------------
n_frames = DURATION_SEC * FPS
timeline = np.linspace(years[0], years[-1], n_frames)

bx = yearly["cum_budget"].values
sy = yearly["cum_success"].values
cm = yearly["cum_missions"].values
cr = yearly["collab_ratio"].values

assert len(bx) == len(sy) == len(cm) == len(cr) == len(years), (
    f"length mismatch: {len(bx)}, {len(sy)}, {len(cm)}, {len(cr)}, {len(years)}"
)

def interp(t):
    idx = t - years[0]
    y0 = int(np.floor(idx))
    y1 = min(y0 + 1, len(years) - 1)
    f  = idx - y0
    if y0 >= len(years) - 1:
        return bx[-1], sy[-1], cm[-1], cr[-1]
    return (
        bx[y0] * (1 - f) + bx[y1] * f,
        sy[y0] * (1 - f) + sy[y1] * f,
        cm[y0] * (1 - f) + cm[y1] * f,
        cr[y0] * (1 - f) + cr[y1] * f,
    )

# ------------------------------------------------------------
# 4. Figure
# ------------------------------------------------------------
fig = plt.figure(figsize=(14, 8.5))
gs  = fig.add_gridspec(2, 3, height_ratios=[3.2, 1], hspace=0.35, wspace=0.35)

ax      = fig.add_subplot(gs[0, :])
ax_ins  = fig.add_subplot(gs[1, 0:2])
ax_bar  = fig.add_subplot(gs[1, 2])

xmax = bx[-1] * 1.10
ymin = np.nanmin(sy) * 0.96
ymax = np.nanmax(sy) * 1.04
if ymax <= ymin:
    ymin, ymax = 0, 100

ax.set_xlim(0, xmax)
ax.set_ylim(ymin, ymax)
ax.set_xlabel("Cumulative global budget spent  (billion $)", fontsize=12)
ax.set_ylabel("Global mission-weighted success rate (%)", fontsize=12)
ax.grid(alpha=0.3)

ax.text(0.02, 0.97, "EFFICIENT\n(less money, more success)",
        transform=ax.transAxes, color="#1b7f3a", fontsize=10,
        va="top", ha="left", alpha=0.75)
ax.text(0.98, 0.03, "EXPENSIVE / UNRELIABLE",
        transform=ax.transAxes, color="#a02020", fontsize=10,
        va="bottom", ha="right", alpha=0.75)

trail_line, = ax.plot([], [], "-", color="#2b6cb0", linewidth=2.5, alpha=0.85, zorder=3)
glow,       = ax.plot([], [], "o", color="#2b6cb0", alpha=0.15, zorder=2)
dot,        = ax.plot([], [], "o", color="#2b6cb0", markersize=14,
                      markeredgecolor="white", markeredgewidth=2, zorder=4)
human_lbl   = ax.text(0, 0, "HUMANITY", fontsize=11, fontweight="bold",
                      color="#1a365d", zorder=5)

year_lbl = ax.text(0.5, 1.03, "", transform=ax.transAxes,
                   ha="center", va="bottom",
                   fontsize=22, fontweight="bold", color="#1a202c")

info_box = ax.text(
    0.015, 0.03, "", transform=ax.transAxes,
    ha="left", va="bottom", fontsize=10, family="monospace",
    bbox=dict(boxstyle="round,pad=0.5", facecolor="#f7fafc",
              edgecolor="#cbd5e0", alpha=0.95)
)

ax_ins.set_xlim(years[0], years[-1])
ax_ins.set_ylim(0, max(1, cm[-1]) * 1.10)
ax_ins.set_xlabel("Year", fontsize=9)
ax_ins.set_ylabel("Cumulative missions", fontsize=9)
ax_ins.grid(alpha=0.3)
ax_ins.set_title("Humanity's launch count", fontsize=10, loc="left")
missions_line, = ax_ins.plot([], [], color="#805ad5", linewidth=2.5)
missions_dot,  = ax_ins.plot([], [], "o", color="#805ad5", markersize=8)

ax_bar.set_xlim(years[0], years[-1])
ax_bar.set_ylim(0, max(1.0, cr.max() * 1.15))
ax_bar.set_xlabel("Year", fontsize=9)
ax_bar.set_ylabel("Avg countries / mission", fontsize=9)
ax_bar.grid(alpha=0.3)
ax_bar.set_title("Collective effort", fontsize=10, loc="left")
collab_line, = ax_bar.plot([], [], color="#dd6b20", linewidth=2.5)
collab_dot,  = ax_bar.plot([], [], "o", color="#dd6b20", markersize=8)

trail_x, trail_y = [], []

# ------------------------------------------------------------
# 5. Update
# ------------------------------------------------------------
def update(frame):
    t = timeline[frame]
    b, s, m, c = interp(t)

    trail_x.append(b)
    trail_y.append(s)
    if len(trail_x) > TRAIL_FRAMES:
        trail_x.pop(0)
        trail_y.pop(0)

    trail_line.set_data(trail_x, trail_y)

    base_size = 14
    scale     = 1 + 3.5 * (c / max(1.0, cr.max()))
    ms        = base_size * scale

    dot.set_data([b], [s])
    dot.set_markersize(ms)
    glow.set_data([b], [s])
    glow.set_markersize(ms * 2.8)
    human_lbl.set_position((b + xmax * 0.008, s + 0.35))

    xs_year = np.linspace(years[0], t, 200)
    ys_miss = np.interp(xs_year, years, cm)
    missions_line.set_data(xs_year, ys_miss)
    missions_dot.set_data([t], [np.interp(t, years, cm)])

    ys_col = np.interp(xs_year, years, cr)
    collab_line.set_data(xs_year, ys_col)
    collab_dot.set_data([t], [np.interp(t, years, cr)])

    year_lbl.set_text(f"Year {t:.1f}")

    info_box.set_text(
        f"cumulative budget : ${b:,.0f} B\n"
        f"success rate      : {s:5.1f} %\n"
        f"missions launched : {int(m):,}\n"
        f"avg partners/miss : {c:.2f}"
    )

    return (trail_line, glow, dot, human_lbl, year_lbl,
            missions_line, missions_dot, collab_line, collab_dot, info_box)

# ------------------------------------------------------------
# 6. Render with tqdm progress bar
# ------------------------------------------------------------
ani = animation.FuncAnimation(
    fig, update, frames=n_frames,
    interval=1000 / FPS, blit=BLIT,
    cache_frame_data=False,
)

writer = animation.FFMpegWriter(fps=FPS, bitrate=2400)

pbar = tqdm(total=n_frames, desc="Rendering", unit="frame",
            dynamic_ncols=True, smoothing=0.05)
t_start = time.perf_counter()

def progress(cur, total):
    pbar.n = cur
    elapsed = time.perf_counter() - t_start
    fps_now = cur / elapsed if elapsed > 0 else 0
    eta = (total - cur) / fps_now if fps_now > 0 else 0
    pbar.set_postfix_str(f"{fps_now:5.1f} fps | ETA {eta/60:5.1f} min")
    pbar.refresh()

try:
    ani.save(OUT_PATH, writer=writer, dpi=DPI, progress_callback=progress)
finally:
    pbar.n = n_frames
    pbar.refresh()
    pbar.close()
    plt.close(fig)

total_time = time.perf_counter() - t_start
print(f"Saved: {OUT_PATH}  ({total_time/60:.1f} min total)")