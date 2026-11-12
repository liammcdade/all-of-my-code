#!/usr/bin/env python3
"""
Fortnite XP Pacer + GTA VI Countdown — Windows desktop widget.
Sits at the bottom of the window z-order (behind every other window).

Season window (fixed, UK time):
    START = Oct 31, 2026  @ 20:14 GMT (8:14 PM UK)
    END   = Nov 19, 2026  @ 00:00 GMT (12:00 AM UK)
"""

import os
import sys
import json
import ctypes
from datetime import datetime, timezone

try:
    import tkinter as tk
except Exception as e:
    print("Tkinter missing:", e)
    sys.exit(1)

try:
    from PIL import Image, ImageOps, ImageEnhance, ImageTk
except ImportError:
    print("Missing Pillow. Run:  pip install pillow")
    sys.exit(1)

try:
    import win32gui
    import win32con
    HAS_WIN32 = True
except ImportError:
    HAS_WIN32 = False

# Crisp text on high-DPI screens
try:
    ctypes.windll.shcore.SetProcessDpiAwareness(2)
except Exception:
    try:
        ctypes.windll.user32.SetProcessDPIAware()
    except Exception:
        pass


# ─────────────────────── CONFIG ───────────────────────────────
IMAGE_PATH = r"C:\Users\liam\Documents\GitHub\all-of-my-code\grand-theft-auto-vi-3840x2160-26939.jpg"

XP_PER_LEVEL = 80_000
TOTAL_LEVELS = 70
TOTAL_XP     = XP_PER_LEVEL * TOTAL_LEVELS   # 5,600,000
TARGET_LEVEL = TOTAL_LEVELS + 1              # final level (71)

# Late Oct & all of Nov 2026: UK is on GMT (UTC+0). Using timezone-aware
# datetimes means the widget shows/compares UK time even if your PC is
# set to a different region.
UK_TZ = timezone.utc

# ★ FIXED SEASON WINDOW (as requested) ★
SEASON_START = datetime(2026, 11, 1, 8, 14, 0, tzinfo=UK_TZ)  # Nov 1, 8:14 AM UK
SEASON_END   = datetime(2026, 11, 19,  0,  0, 0, tzinfo=UK_TZ)  # Nov 19, 12:00 AM UK

GTA6_RELEASE = datetime(2026, 11, 19,  0,  0, 0, tzinfo=UK_TZ)  # same as season end

W, H = 1000, 400

STATE_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                          "fortnite_pacer_state.json")

# Colours
TEXT      = "#e6edf3"
MUTED     = "#8b98a9"
CARD_BG   = "#0b1220"
BORDER    = "#1e293b"
INPUT_BG  = "#0f172a"
ACCENT_B  = "#38bdf8"
ACCENT_P  = "#a78bfa"
GOOD      = "#34d399"
BAD       = "#f87171"
WARN      = "#fbbf24"


# ─────────────────────── HELPERS ──────────────────────────────
def fmt_int(n):  return f"{int(round(n)):,}"
def fmt2(n):     return f"{float(n):,.2f}"
def fmt3(n):     return f"{float(n):,.3f}"

def on_pace_level(now: datetime) -> float:
    total = (SEASON_END - SEASON_START).total_seconds()
    if total <= 0:
        return float(TARGET_LEVEL)
    frac = (now - SEASON_START).total_seconds() / total
    frac = max(0.0, min(1.0, frac))
    return 1.0 + TOTAL_LEVELS * frac

def days_remaining_exact(now: datetime) -> float:
    start = max(now, SEASON_START)
    diff = (SEASON_END - start).total_seconds()
    return diff / 86400.0 if diff > 0 else 0.0


# ─────────────────────── APP ──────────────────────────────────
class WallpaperTracker:
    def __init__(self):
        self.root = tk.Tk()
        self.root.overrideredirect(True)
        self.root.configure(bg="#000000")

        sw = self.root.winfo_screenwidth()
        sh = self.root.winfo_screenheight()
        x = max(0, sw - W - 32)
        y = max(0, sh - H - 96)
        self.root.geometry(f"{W}x{H}+{x}+{y}")

        self._bg_photo = None
        self._drag_dx = 0
        self._drag_dy = 0

        self._build_background()
        self._build_left_card()
        self._build_right_card()
        self._load_state()
        self._bind_events()
        self._build_chrome()

        self.root.bind("<Escape>", lambda e: self._quit())

        if HAS_WIN32:
            self.root.after(150, self.send_to_bottom)
            self.root.after(500, self._keep_bottom_loop)

        self.root.after(5000, self._autosave_loop)
        self._tick()

    # ── Background (GTA VI image) ─────────────────────────────
    def _build_background(self):
        self.bg_canvas = tk.Canvas(self.root, width=W, height=H,
                                   highlightthickness=0, bd=0, bg="#0a0a0a")
        self.bg_canvas.place(x=0, y=0, width=W, height=H)

        if os.path.exists(IMAGE_PATH):
            try:
                img = Image.open(IMAGE_PATH).convert("RGB")
                img = ImageOps.fit(img, (W, H), method=Image.LANCZOS)
                img = ImageEnhance.Brightness(img).enhance(0.42)
                img = ImageEnhance.Color(img).enhance(1.20)
                self._bg_photo = ImageTk.PhotoImage(img)
                self.bg_canvas.create_image(0, 0, anchor="nw",
                                            image=self._bg_photo)
            except Exception as e:
                print("Image load failed:", e)

        self.bg_canvas.create_rectangle(0, 0, W - 1, H - 1,
                                        outline=BORDER, width=1)

    def _make_card(self, x, y, w, h):
        f = tk.Frame(self.root, bg=CARD_BG,
                     highlightbackground=BORDER, highlightthickness=1)
        f.place(x=x, y=y, width=w, height=h)
        return f

    # ── Left card: GTA VI countdown ───────────────────────────
    def _build_left_card(self):
        c = self._make_card(20, 20, 470, 360)
        self.left_card = c

        tk.Label(c, text="GRAND THEFT AUTO VI",
                 font=("Segoe UI", 12, "bold"), fg=TEXT, bg=CARD_BG,
                 anchor="w").place(x=24, y=18)
        tk.Label(c, text="RELEASE COUNTDOWN",
                 font=("Segoe UI", 8), fg=MUTED, bg=CARD_BG,
                 anchor="w").place(x=24, y=42)

        self.gta_days_lbl = tk.Label(c, text="—",
                                     font=("Segoe UI", 96, "bold"),
                                     fg=ACCENT_P, bg=CARD_BG, anchor="w")
        self.gta_days_lbl.place(x=18, y=56)

        self.gta_days_caption = tk.Label(c, text="DAYS",
                                         font=("Segoe UI", 10, "bold"),
                                         fg=MUTED, bg=CARD_BG, anchor="w")
        self.gta_days_caption.place(x=26, y=192)

        self.gta_hms_lbl = tk.Label(c, text="00:00:00",
                                    font=("Consolas", 30, "bold"),
                                    fg=TEXT, bg=CARD_BG, anchor="w")
        self.gta_hms_lbl.place(x=24, y=214)

        tk.Label(c, text="HOURS   ·   MINUTES   ·   SECONDS",
                 font=("Segoe UI", 8), fg=MUTED, bg=CARD_BG,
                 anchor="w").place(x=24, y=258)

        tk.Label(c, text=f"Expected release: {GTA6_RELEASE.strftime('%B %d, %Y')} (UK)",
                 font=("Segoe UI", 9), fg=MUTED, bg=CARD_BG,
                 anchor="w").place(x=24, y=318)

    # ── Right card: Fortnite XP pacer ─────────────────────────
    def _build_right_card(self):
        c = self._make_card(510, 20, 470, 360)
        self.right_card = c

        tk.Label(c, text="FORTNITE XP PACER",
                 font=("Segoe UI", 12, "bold"), fg=TEXT, bg=CARD_BG,
                 anchor="w").place(x=24, y=18)

        start_str = SEASON_START.strftime("%b %d, %H:%M")
        end_str   = SEASON_END.strftime("%b %d, %H:%M")
        tk.Label(c, text=f"70 levels × 80,000 XP   ·   {start_str} → {end_str} UK",
                 font=("Segoe UI", 8), fg=MUTED, bg=CARD_BG,
                 anchor="w").place(x=24, y=42)

        # Inputs
        tk.Label(c, text="CURRENT LEVEL", font=("Segoe UI", 8),
                 fg=MUTED, bg=CARD_BG, anchor="w").place(x=24, y=70)
        self.level_var = tk.StringVar(value="1")
        self.level_entry = tk.Entry(c, textvariable=self.level_var, width=6,
                                    font=("Consolas", 16, "bold"),
                                    bg=INPUT_BG, fg=TEXT, insertbackground=TEXT,
                                    relief="flat", justify="center",
                                    highlightthickness=1,
                                    highlightbackground=BORDER,
                                    highlightcolor=ACCENT_B)
        self.level_entry.place(x=24, y=90, width=90, height=34)

        tk.Label(c, text="XP IN CURRENT LEVEL", font=("Segoe UI", 8),
                 fg=MUTED, bg=CARD_BG, anchor="w").place(x=128, y=70)
        self.xp_var = tk.StringVar(value="0")
        self.xp_entry = tk.Entry(c, textvariable=self.xp_var, width=10,
                                 font=("Consolas", 16, "bold"),
                                 bg=INPUT_BG, fg=TEXT, insertbackground=TEXT,
                                 relief="flat", justify="center",
                                 highlightthickness=1,
                                 highlightbackground=BORDER,
                                 highlightcolor=ACCENT_B)
        self.xp_entry.place(x=128, y=90, width=170, height=34)

        # Stats
        self.xp_left_val = self._stat(c, 24,  148, "XP LEFT")
        self.xp_day_val  = self._stat(c, 250, 148, "XP / DAY NEEDED")
        self.lvl_day_val = self._stat(c, 24,  208, "LEVELS / DAY NEEDED")
        self.onpace_val  = self._stat(c, 250, 208, "ON-PACE LEVEL (3 DP)")

        # Progress bar
        self.pbar = tk.Canvas(c, width=422, height=8, bg="#1a2332",
                              highlightthickness=0, bd=0)
        self.pbar.place(x=24, y=274)
        self.pbar_fill = self.pbar.create_rectangle(0, 0, 0, 8,
                                                    fill=ACCENT_B, width=0)

        # Status
        self.status_lbl = tk.Label(c, text="—", font=("Segoe UI", 11, "bold"),
                                   fg=MUTED, bg=CARD_BG, anchor="w")
        self.status_lbl.place(x=24, y=294)
        self.status_sub_lbl = tk.Label(c, text="", font=("Segoe UI", 8),
                                       fg=MUTED, bg=CARD_BG, anchor="w")
        self.status_sub_lbl.place(x=24, y=318)

    def _stat(self, parent, x, y, label):
        tk.Label(parent, text=label, font=("Segoe UI", 8), fg=MUTED,
                 bg=CARD_BG, anchor="w").place(x=x, y=y)
        v = tk.Label(parent, text="—", font=("Consolas", 20, "bold"),
                     fg=TEXT, bg=CARD_BG, anchor="w")
        v.place(x=x, y=y + 16)
        return v

    # ── Chrome: close button ─────────────────────────────────
    def _build_chrome(self):
        self.close_btn = tk.Label(self.root, text="✕",
                                  font=("Segoe UI", 10, "bold"),
                                  fg=MUTED, bg="#0a0a0a",
                                  cursor="hand2", padx=6, pady=2)
        self.close_btn.place(x=W - 30, y=6)
        self.close_btn.bind("<Button-1>", lambda e: self._quit())
        self.close_btn.bind("<Enter>", lambda e: self.close_btn.configure(fg=BAD))
        self.close_btn.bind("<Leave>", lambda e: self.close_btn.configure(fg=MUTED))

    # ── Events (drag + right-click menu) ─────────────────────
    def _bind_events(self):
        targets = [self.bg_canvas, self.left_card, self.right_card]
        for root_w in (self.left_card, self.right_card):
            targets.extend(self._iter_children(root_w))

        for w in targets:
            if isinstance(w, tk.Entry):
                continue
            w.bind("<ButtonPress-1>", self._drag_start)
            w.bind("<B1-Motion>",     self._drag_move)
            w.bind("<Button-3>",      self._context_menu)
            w.bind("<Button-2>",      self._context_menu)

        self.bg_canvas.bind("<ButtonPress-1>", self._drag_start)
        self.bg_canvas.bind("<B1-Motion>",     self._drag_move)
        self.bg_canvas.bind("<Button-3>",      self._context_menu)

    def _iter_children(self, w):
        out = []
        for c in w.winfo_children():
            out.append(c)
            out.extend(self._iter_children(c))
        return out

    def _drag_start(self, event):
        self._drag_dx = event.x_root - self.root.winfo_x()
        self._drag_dy = event.y_root - self.root.winfo_y()

    def _drag_move(self, event):
        x = event.x_root - self._drag_dx
        y = event.y_root - self._drag_dy
        self.root.geometry(f"+{x}+{y}")

    def _context_menu(self, event):
        m = tk.Menu(self.root, tearoff=0, bg=CARD_BG, fg=TEXT,
                    activebackground=ACCENT_B, activeforeground="#000")
        m.add_command(label="Bring to front", command=self.bring_to_front)
        m.add_command(label="Send to bottom", command=self.send_to_bottom)
        m.add_separator()
        m.add_command(label="Quit", command=self._quit)
        try:
            m.tk_popup(event.x_root, event.y_root)
        finally:
            m.grab_release()

    # ── Win32 z-order ────────────────────────────────────────
    def _hwnd(self):
        try:
            h = ctypes.windll.user32.GetParent(self.root.winfo_id())
            return h if h else self.root.winfo_id()
        except Exception:
            return self.root.winfo_id()

    def send_to_bottom(self):
        if not HAS_WIN32:
            return
        try:
            win32gui.SetWindowPos(
                self._hwnd(), win32con.HWND_BOTTOM, 0, 0, 0, 0,
                win32con.SWP_NOMOVE | win32con.SWP_NOSIZE | win32con.SWP_NOACTIVATE
            )
        except Exception:
            pass

    def bring_to_front(self):
        if not HAS_WIN32:
            self.root.lift()
            return
        try:
            win32gui.SetWindowPos(
                self._hwnd(), win32con.HWND_TOP, 0, 0, 0, 0,
                win32con.SWP_NOMOVE | win32con.SWP_NOSIZE | win32con.SWP_NOACTIVATE
            )
        except Exception:
            pass

    def _keep_bottom_loop(self):
        try:
            if HAS_WIN32:
                h = self._hwnd()
                if win32gui.GetForegroundWindow() != h:
                    win32gui.SetWindowPos(
                        h, win32con.HWND_BOTTOM, 0, 0, 0, 0,
                        win32con.SWP_NOMOVE | win32con.SWP_NOSIZE |
                        win32con.SWP_NOACTIVATE
                    )
        except Exception:
            pass
        self.root.after(500, self._keep_bottom_loop)

    # ── State persistence (level + XP only; season is fixed now) ──
    def _load_state(self):
        try:
            with open(STATE_PATH, "r", encoding="utf-8") as f:
                d = json.load(f)
            if "level" in d: self.level_var.set(str(d["level"]))
            if "xp"    in d: self.xp_var.set(str(d["xp"]))
        except Exception:
            pass

    def _save_state(self):
        try:
            with open(STATE_PATH, "w", encoding="utf-8") as f:
                json.dump({"level": self.level_var.get(),
                           "xp":    self.xp_var.get()}, f)
        except Exception:
            pass

    def _autosave_loop(self):
        self._save_state()
        self.root.after(5000, self._autosave_loop)

    def _quit(self):
        self._save_state()
        try:
            self.root.destroy()
        except Exception:
            pass

    # ── Main live update (every 50 ms) ───────────────────────
    def _tick(self):
        try:
            self._update_all()
        except Exception:
            pass
        self.root.after(50, self._tick)

    def _update_all(self):
        now = datetime.now(UK_TZ)   # ★ always evaluate in UK time

        # GTA VI countdown
        delta = GTA6_RELEASE - now
        if delta.total_seconds() <= 0:
            self.gta_days_lbl.configure(text="OUT", fg=GOOD)
            self.gta_days_caption.configure(text="OUT NOW")
            self.gta_hms_lbl.configure(text="GTA VI IS HERE", fg=GOOD)
        else:
            d = delta.days
            h, rem = divmod(delta.seconds, 3600)
            mi, s = divmod(rem, 60)
            self.gta_days_lbl.configure(text=str(d), fg=ACCENT_P)
            self.gta_days_caption.configure(text="DAYS")
            self.gta_hms_lbl.configure(text=f"{h:02d}:{mi:02d}:{s:02d}",
                                       fg=TEXT)

        # Fortnite inputs
        try:
            level = int(float(self.level_var.get() or "1"))
        except ValueError:
            level = 1
        level = max(1, min(level, 200))

        try:
            xp_in = int(float(self.xp_var.get() or "0"))
        except ValueError:
            xp_in = 0
        xp_in = max(0, min(xp_in, XP_PER_LEVEL - 1))

        earned = (level - 1) * XP_PER_LEVEL + xp_in
        left   = max(0.0, TOTAL_XP - earned)

        days_left = days_remaining_exact(now)
        if days_left > 0 and left > 0:
            xp_day  = left / days_left
            lvl_day = xp_day / XP_PER_LEVEL
        else:
            xp_day  = 0.0
            lvl_day = 0.0

        self.xp_left_val.configure(text=fmt_int(left))
        self.xp_day_val.configure(text=fmt2(xp_day) if days_left > 0 else "—")
        self.lvl_day_val.configure(text=fmt2(lvl_day) if days_left > 0 else "—")

        onpace = on_pace_level(now)
        your   = level + xp_in / XP_PER_LEVEL
        diff   = your - onpace

        self.onpace_val.configure(text=fmt3(onpace))
        if now < SEASON_START:
            self.onpace_val.configure(fg=ACCENT_P)
        elif diff >= 0.0005:
            self.onpace_val.configure(fg=GOOD)
        elif diff <= -0.0005:
            self.onpace_val.configure(fg=BAD)
        else:
            self.onpace_val.configure(fg=WARN)

        # Progress bar
        frac = max(0.0, min(1.0, earned / TOTAL_XP))
        self.pbar.coords(self.pbar_fill, 0, 0, int(422 * frac), 8)
        self.pbar.itemconfigure(self.pbar_fill,
                                fill=GOOD if frac >= 1.0 else ACCENT_B)

        # Status
        if now < SEASON_START:
            status = "⏳ NOT STARTED"
            color  = WARN
            sub    = f"Season begins {SEASON_START.strftime('%b %d, %H:%M')} UK"
        elif left <= 0:
            status = "✅ COMPLETE — 70/70"
            color  = GOOD
            sub    = "You hit the 70-level goal."
        elif days_left <= 0:
            status = "⏰ SEASON ENDED"
            color  = BAD
            sub    = ""
        else:
            if diff >= 0.0005:
                status = f"🟢 AHEAD   (+{fmt3(diff)} lvl)"
                color  = GOOD
            elif diff <= -0.0005:
                status = f"🔴 BEHIND   ({fmt3(diff)} lvl)"
                color  = BAD
            else:
                status = "🟡 ON PACE"
                color  = WARN
            sub = f"You: {fmt3(your)}   •   On-pace: {fmt3(onpace)}   •   {fmt2(days_left)} days left"

        self.status_lbl.configure(text=status, fg=color)
        self.status_sub_lbl.configure(text=sub)


# ─────────────────────── MAIN ─────────────────────────────────
def main():
    app = WallpaperTracker()
    app.root.mainloop()


if __name__ == "__main__":
    main()