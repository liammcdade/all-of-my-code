#!/usr/bin/env python3
"""
mars_clock_accurate.py
A fully leap-second-aware GUI clock for Mars Coordinated Time (MTC).
Uses astropy for precise UTC -> TT conversion, then the Mars24 algorithm.
"""

import tkinter as tk
import datetime
from astropy.time import Time

# --- Mars24 / AM2000 constants ------------------------------------------
J2000          = 2451545.0
SOL_RATIO      = 1.0274912517        # Earth days per Martian sol
MSD_OFFSET     = 44796.0
MSD_CORRECTION = 0.0009626

UNIX_EPOCH = datetime.datetime(1970, 1, 1, tzinfo=datetime.timezone.utc)


def mars_utc_hms(dt_utc):
    """
    Return (h, m, s) of Mars UTC (MTC) with full leap-second accuracy.
    """
    # Use astropy to convert UTC to TT (Terrestrial Time).
    # This correctly applies all historical and future leap seconds.
    t = Time(dt_utc, scale='utc')
    jd_tt = t.tt.jd  # Julian Date in Terrestrial Time

    # Mars24 / AM2000 formula for Mars Sol Date (MSD)
    msd = ((jd_tt - J2000 - 4.5) / SOL_RATIO) + MSD_OFFSET - MSD_CORRECTION

    # Coordinated Mars Time (MTC) is the fractional part of MSD, scaled to 24h
    mtc_hours = (msd * 24.0) % 24.0

    h = int(mtc_hours)
    m_float = (mtc_hours - h) * 60.0
    m = int(m_float)
    s = (m_float - m) * 60.0
    return h, m, s


class MarsClockApp:
    def __init__(self, root):
        self.root = root
        root.title("Mars UTC (MTC) — Fully Accurate")
        root.configure(bg="#101014")
        root.resizable(False, False)

        tk.Label(
            root, text="MARS UTC (MTC)",
            font=("Helvetica", 14, "bold"),
            fg="#7a7a8c", bg="#101014",
        ).pack(pady=(24, 0))

        self.mars_label = tk.Label(
            root, text="--:--:--",
            font=("Consolas", 80, "bold"),
            fg="#ff6b35", bg="#101014",
        )
        self.mars_label.pack(padx=40, pady=(0, 4))

        self.sol_label = tk.Label(
            root, text="", font=("Helvetica", 13),
            fg="#9a9ab0", bg="#101014",
        )
        self.sol_label.pack()

        tk.Frame(root, height=1, bg="#2a2a38").pack(fill="x", padx=30, pady=16)

        self.earth_label = tk.Label(
            root, text="", font=("Consolas", 15),
            fg="#5ad1a0", bg="#101014",
        )
        self.earth_label.pack(pady=(0, 6))

        self.note = tk.Label(
            root,
            text="Leap-second aware via astropy  •  Mars seconds ≈ 2.75% longer",
            font=("Helvetica", 10), fg="#5a5a70", bg="#101014",
        )
        self.note.pack(pady=(0, 20))

        self._tick()

    def _tick(self):
        now = datetime.datetime.now(datetime.timezone.utc)
        h, m, s = mars_utc_hms(now)

        # Show 2 decimal places for smooth motion
        self.mars_label.config(text=f"{h:02d}:{m:02d}:{s:05.2f}")
        self.earth_label.config(
            text=f"Earth UTC  {now.strftime('%Y-%m-%d  %H:%M:%S')}"
        )

        # Compute and display MSD using the same astropy path
        t = Time(now, scale='utc')
        jd_tt = t.tt.jd
        msd = ((jd_tt - J2000 - 4.5) / SOL_RATIO) + MSD_OFFSET - MSD_CORRECTION
        self.sol_label.config(text=f"Mars Sol Date (MSD): {msd:,.5f}")

        # 10 FPS is smooth and efficient
        self.root.after(100, self._tick)


if __name__ == "__main__":
    root = tk.Tk()
    MarsClockApp(root)
    root.mainloop()