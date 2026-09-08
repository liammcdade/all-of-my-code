import tkinter as tk
from datetime import datetime, timezone
import math

# ============================================================
#  MARS TIME CALCULATION ENGINE
# ============================================================

def msd_from_utc(utc_dt):
    epoch = datetime(1873, 12, 29, 12, 3, 36, tzinfo=timezone.utc)
    delta = utc_dt - epoch
    jd_diff = delta.total_seconds() / 86400.0
    return jd_diff / 1.0274912517

def mtc_from_msd(msd):
    fraction = msd - math.floor(msd)
    return fraction * 24

def hours_to_time_str(hours):
    hours = hours % 24
    total_seconds = int(hours * 3600)
    h = total_seconds // 3600
    m = (total_seconds % 3600) // 60
    s = total_seconds % 60
    return f"{h:02d}:{m:02d}:{s:02d}"

def local_time_at_longitude(mtc_hours, longitude_deg):
    offset_hours = longitude_deg / 15.0
    return (mtc_hours + offset_hours) % 24

# ============================================================
#  ROVER DATA (now includes driving stats!)
# ============================================================
rovers = [
    {
        "name": "Perseverance",
        "mission": "NASA",
        "lat": "18.447°N",
        "lon": 77.402,
        "lon_str": "77.402°E",
        "color": "#f38ba8",      # pink-red
        "drive_typical": "100 – 300+ m",
        "drive_record": "411.7 m (single sol)",
        "tech": "AutoNav (thinks while driving)"
    },
    {
        "name": "Curiosity",
        "mission": "NASA",
        "lat": "4.5895°S",
        "lon": 137.4417,
        "lon_str": "137.442°E",
        "color": "#a6e3a1",      # green
        "drive_typical": "30 – 100 m",
        "drive_record": "~144 m (single sol)",
        "tech": "Stop-Think-Drive cycle"
    }
]

# ============================================================
#  BUILD THE GUI
# ============================================================

root = tk.Tk()
root.title("🪐 Mars Rover Real-Time Dashboard")
root.geometry("620x500")
root.resizable(False, False)
root.configure(bg="#1e1e2e")

def make_label(parent, text, font_size, weight="normal", fg="white", bg="#1e1e2e"):
    return tk.Label(parent, text=text, font=("Segoe UI", font_size, weight),
                    fg=fg, bg=bg)

# --- Header ---
header = make_label(root, "🔴 MARS ROVER DASHBOARD", 18, "bold", "#f9a825")
header.pack(pady=(15, 5))

# --- Earth UTC ---
tk.Label(root, text="🌍 Earth UTC Time", font=("Segoe UI", 11, "bold"),
         fg="#a6e3a1", bg="#1e1e2e").pack(pady=(10, 0))
utc_label = make_label(root, "--:--:--", 16, "bold", "#cdd6f4")
utc_label.pack()

# --- MTC ---
tk.Label(root, text="🕒 Mars Coordinated Time (MTC — 0° longitude)",
         font=("Segoe UI", 11, "bold"), fg="#89b4fa", bg="#1e1e2e").pack(pady=(6, 0))
mtc_label = make_label(root, "--:--:--", 16, "bold", "#89b4fa")
mtc_label.pack()

# --- Separator ---
tk.Label(root, text="━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━", font=("Segoe UI", 10),
         fg="#585b70", bg="#1e1e2e").pack(pady=(10, 5))

# --- Rover Cards (each in a framed container) ---
rover_widgets = {}  # store the time labels for updating

for rover in rovers:
    # Main frame for this rover (like a card)
    card = tk.Frame(root, bg="#313244", bd=2, relief=tk.GROOVE)
    card.pack(pady=6, padx=20, fill=tk.X)

    # Row 1: Name + Mission + Location
    header_row = tk.Frame(card, bg="#313244")
    header_row.pack(pady=(8, 0), padx=10, anchor=tk.W)
    
    name_color = rover["color"]
    tk.Label(header_row, text=f"🛰️  {rover['name']}", font=("Segoe UI", 12, "bold"),
             fg=name_color, bg="#313244").pack(side=tk.LEFT)
    tk.Label(header_row, text=f"({rover['mission']})", font=("Segoe UI", 10),
             fg="#a6adc8", bg="#313244").pack(side=tk.LEFT, padx=(6, 12))
    tk.Label(header_row, text=f"📍 {rover['lat']}, {rover['lon_str']}", font=("Segoe UI", 10),
             fg="#cdd6f4", bg="#313244").pack(side=tk.LEFT)

    # Row 2: The actual ticking clock (local time)
    time_row = tk.Frame(card, bg="#313244")
    time_row.pack(pady=(2, 0), padx=10, anchor=tk.W)
    
    tk.Label(time_row, text="Local Solar Time:", font=("Segoe UI", 10, "bold"),
             fg="#b4befe", bg="#313244").pack(side=tk.LEFT)
    time_label = tk.Label(time_row, text="--:--:--", font=("Courier New", 18, "bold"),
                          fg=name_color, bg="#313244")
    time_label.pack(side=tk.LEFT, padx=(10, 0))
    rover_widgets[rover["name"]] = time_label

    # Row 3: Driving stats (the new info you provided!)
    stats_row = tk.Frame(card, bg="#313244")
    stats_row.pack(pady=(4, 8), padx=10, anchor=tk.W)
    
    tk.Label(stats_row, text="🚗 Daily Drive:", font=("Segoe UI", 9, "bold"),
             fg="#fab387", bg="#313244").pack(side=tk.LEFT)
    tk.Label(stats_row, text=rover["drive_typical"], font=("Segoe UI", 9),
             fg="#cdd6f4", bg="#313244").pack(side=tk.LEFT, padx=(5, 15))
    
    tk.Label(stats_row, text="🏆 Record:", font=("Segoe UI", 9, "bold"),
             fg="#f9e2af", bg="#313244").pack(side=tk.LEFT)
    tk.Label(stats_row, text=rover["drive_record"], font=("Segoe UI", 9),
             fg="#cdd6f4", bg="#313244").pack(side=tk.LEFT, padx=(5, 15))
    
    tk.Label(stats_row, text=f"⚙️ {rover['tech']}", font=("Segoe UI", 8, "italic"),
             fg="#6c7086", bg="#313244").pack(side=tk.LEFT)

# --- Footer (Sol Date) ---
sol_label = make_label(root, "MSD: --.------", 10, "normal", "#6c7086")
sol_label.pack(pady=(12, 5))

# ============================================================
#  TICK FUNCTION
# ============================================================

def update_clock():
    utc_now = datetime.now(timezone.utc)
    msd = msd_from_utc(utc_now)
    mtc_hours = mtc_from_msd(msd)

    # Update Earth & MTC
    utc_label.config(text=utc_now.strftime('%Y-%m-%d  %H:%M:%S') + " UTC")
    mtc_label.config(text=hours_to_time_str(mtc_hours))
    sol_label.config(text=f"MSD: {msd:.6f}")

    # Update each rover's local time
    for rover in rovers:
        local_hours = local_time_at_longitude(mtc_hours, rover["lon"])
        rover_widgets[rover["name"]].config(text=hours_to_time_str(local_hours))

    root.after(1000, update_clock)

# ============================================================
#  START
# ============================================================

update_clock()
root.mainloop()