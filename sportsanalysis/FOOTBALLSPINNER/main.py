"""
LUCKY SEVENS — 12-machine casino floor.

Every machine runs the exact same 97.32% RTP slot math (see below), each one
running at 100 spins per second, all simultaneously.

TURBO ARCHITECTURE
------------------
One shared GUI clock ticks every TURBO_FRAME_MS (50 ms). Each tick advances
every machine by TURBO_BATCH spins (5), then repaints all 12 panels once.
12 machines x 5 spins = 60 spins per 50 ms frame = 100 spins/sec PER MACHINE.

The RNG, paytable and independence are identical to single manual spins.

THE MATH (identical on every machine)
-------------------------------------
Each reel is a weighted strip. Weights sum to 100 per reel, so the game is
equivalent to 100 x 100 x 100 = 1,000,000 equally likely virtual stops.
Only 3-of-a-kind pays. The weighted payout sum is:

    CHERRY   30*30*28 = 25,200   x    4  =   100,800
    LEMON    25*25*24 = 15,000   x   10  =   150,000
    BELL     20*20*20 =  8,000   x   30  =   240,000
    BAR      12*12*14 =  2,016   x   60  =   120,960
    SEVEN     8* 8* 8 =    512   x  120  =    61,440
    DIAMOND   5* 5* 6 =    150   x 2000  =   300,000
                                            ---------
                                             973,200

    RTP = 973,200 / 1,000,000 = 0.9732  ->  97.32%   (exact, by construction)

Every spin is INDEPENDENT. No memory, no compensation, no near-miss fudging.
The 97.32% only emerges as the long-run average across many spins.
"""

import random
import tkinter as tk
from tkinter import font as tkfont

# ----------------------------------------------------------------------
#  MACHINE CONFIGURATION   (this is the "rigged" part: rigged to 97.32%)
# ----------------------------------------------------------------------
SYMBOLS = ["CHERRY", "LEMON", "BELL", "BAR", "SEVEN", "DIAMOND"]

SYMBOL_INFO = {
    "CHERRY":  {"label": "CHERRY",  "fg": "#ff4d6d", "bg": "#2b0710"},
    "LEMON":   {"label": "LEMON",   "fg": "#ffe066", "bg": "#2b2407"},
    "BELL":    {"label": "BELL",    "fg": "#ffb347", "bg": "#2b1c07"},
    "BAR":     {"label": "BAR",     "fg": "#6ee7ff", "bg": "#07202b"},
    "SEVEN":   {"label": "7",       "fg": "#ff5252", "bg": "#2b0707"},
    "DIAMOND": {"label": "DIAMOND", "fg": "#c084fc", "bg": "#1c072b"},
}

REEL_STRIPS = [
    [("CHERRY", 30), ("LEMON", 25), ("BELL", 20), ("BAR", 12), ("SEVEN", 8), ("DIAMOND", 5)],
    [("CHERRY", 30), ("LEMON", 25), ("BELL", 20), ("BAR", 12), ("SEVEN", 8), ("DIAMOND", 5)],
    [("CHERRY", 28), ("LEMON", 24), ("BELL", 20), ("BAR", 14), ("SEVEN", 8), ("DIAMOND", 6)],
]

PAYTABLE = {
    "CHERRY":  4,
    "LEMON":   10,
    "BELL":    30,
    "BAR":     60,
    "SEVEN":   120,
    "DIAMOND": 2000,
}

BET = 1
STARTING_CREDITS = 1000

NUM_MACHINES        = 12
TURBO_SPINS_PER_SEC = 100
TURBO_FRAME_MS      = 50
TURBO_BATCH         = TURBO_SPINS_PER_SEC * TURBO_FRAME_MS // 1000   # 5


# ----------------------------------------------------------------------
#  CORE MACHINE MATH  (shared by every machine, identical odds)
# ----------------------------------------------------------------------
def _build_cdfs():
    out = []
    for strip in REEL_STRIPS:
        total = sum(w for _, w in strip)
        cum, cdf = 0, []
        for sym, w in strip:
            cum += w
            cdf.append((cum / total, sym))
        out.append(cdf)
    return out


CDFS = _build_cdfs()


def spin_reel(index):
    r = random.random()
    for p, sym in CDFS[index]:
        if r < p:
            return sym
    return CDFS[index][-1][1]


def spin_all():
    return [spin_reel(0), spin_reel(1), spin_reel(2)]


def evaluate(result):
    if result[0] == result[1] == result[2]:
        return PAYTABLE[result[0]]
    return 0


def machine_stats():
    combos = 1
    for strip in REEL_STRIPS:
        combos *= sum(w for _, w in strip)

    paid = hits = 0
    per_symbol = {}
    for s in SYMBOLS:
        w = 1
        for strip in REEL_STRIPS:
            w *= dict(strip)[s]
        per_symbol[s] = w
        paid += w * PAYTABLE[s]
        hits += w

    return {
        "combos": combos,
        "rtp": paid / combos,
        "hit_rate": hits / combos,
        "jackpot_odds": combos / per_symbol["DIAMOND"],
        "per_symbol": per_symbol,
    }


# ----------------------------------------------------------------------
#  MACHINE  (pure logic, no GUI)
# ----------------------------------------------------------------------
class Machine:
    def __init__(self, idx):
        self.idx = idx
        self.reset()

    def reset(self):
        self.credits = STARTING_CREDITS
        self.spins = 0
        self.total_wagered = 0
        self.total_won = 0
        self.last_result = ["SEVEN", "CHERRY", "BAR"]
        self.last_win = 0
        self.jackpot = False        # True if a DIAMOND x3 landed this frame

    def run_batch(self, n):
        """Run up to n independent spins. Returns number actually executed."""
        self.jackpot = False
        self.last_win = 0
        ran = 0

        for _ in range(n):
            if self.credits < BET:
                break
            self.credits -= BET
            self.total_wagered += BET
            self.spins += 1

            r = spin_all()
            self.last_result = r
            m = evaluate(r)

            if m:
                payout = m * BET
                self.credits += payout
                self.total_won += payout
                self.last_win += payout
                if r[0] == "DIAMOND":
                    self.jackpot = True

            ran += 1

        return ran

    @property
    def rtp(self):
        return (self.total_won / self.total_wagered * 100) if self.total_wagered else 0.0


# ----------------------------------------------------------------------
#  THEME
# ----------------------------------------------------------------------
BG        = "#08080c"
PANEL_BG  = "#12121c"
BORDER    = "#2a2a3d"
BORDER_HI = "#c084fc"
GOLD      = "#ffd93b"
GREEN     = "#7dffa0"
GREY      = "#7a7a92"
DIM       = "#5f5f78"


# ----------------------------------------------------------------------
#  MACHINE PANEL  (one tile in the casino floor)
# ----------------------------------------------------------------------
class MachinePanel:
    def __init__(self, parent, machine, fonts, on_toggle):
        self.m = machine
        self.fonts = fonts
        self.on_toggle = on_toggle
        self.flash = 0                       # frames of jackpot flash remaining

        self.frame = tk.Frame(parent, bg=PANEL_BG,
                              highlightthickness=2,
                              highlightbackground=BORDER)
        self.frame.pack_propagate(False)

        # --- title bar ---
        head = tk.Frame(self.frame, bg=PANEL_BG)
        head.pack(fill="x", padx=8, pady=(6, 2))

        self.title = tk.Label(head, text=f"MACHINE {machine.idx + 1:02d}",
                              font=fonts["title"], fg=GOLD, bg=PANEL_BG)
        self.title.pack(side="left")

        self.rtp_lbl = tk.Label(head, text="RTP  --", font=fonts["tiny"],
                                fg=DIM, bg=PANEL_BG)
        self.rtp_lbl.pack(side="right")

        # --- reels ---
        reels = tk.Frame(self.frame, bg=PANEL_BG)
        reels.pack(pady=(2, 4))

        self.reels = []
        for i in range(3):
            lbl = tk.Label(reels, text="?", font=fonts["reel"],
                           width=7, height=1, fg="#ffffff", bg=PANEL_BG)
            lbl.grid(row=0, column=i, padx=2)
            self.reels.append(lbl)

        # --- credits ---
        self.credits_lbl = tk.Label(self.frame, text="1,000",
                                    font=fonts["credits"], fg=GREEN, bg=PANEL_BG)
        self.credits_lbl.pack()

        # --- win / info line ---
        self.win_lbl = tk.Label(self.frame, text="—", font=fonts["tiny"],
                                fg=DIM, bg=PANEL_BG)
        self.win_lbl.pack(pady=(0, 6))

        # click the panel to toggle the whole floor
        for w in (self.frame, self.title, self.credits_lbl, self.win_lbl):
            w.bind("<Button-1>", lambda e: self.on_toggle())

    # ---- repaint from the model (called once per frame) ----
    def refresh(self):
        m = self.m

        for i, sym in enumerate(m.last_result):
            info = SYMBOL_INFO[sym]
            self.reels[i].configure(text=info["label"], fg=info["fg"], bg=info["bg"])

        self.credits_lbl.configure(text=f"{m.credits:,}")
        self.rtp_lbl.configure(text=f"RTP {m.rtp:.1f}%")

        if m.jackpot:
            self.win_lbl.configure(text=f"★ JACKPOT +{m.last_win:,}", fg=BORDER_HI)
            self.flash = 10
        elif m.last_win:
            self.win_lbl.configure(text=f"+{m.last_win:,}", fg=GREEN)
        else:
            self.win_lbl.configure(text=f"spins {m.spins:,}", fg=DIM)

        # jackpot flash on the border
        if self.flash > 0:
            self.frame.configure(highlightbackground=BORDER_HI)
            self.flash -= 1
        else:
            self.frame.configure(highlightbackground=BORDER)


# ----------------------------------------------------------------------
#  CASINO FLOOR
# ----------------------------------------------------------------------
class CasinoFloor:
    def __init__(self, root):
        self.root = root
        root.title("Lucky Sevens  •  12 Machines  •  97.32% RTP")
        root.configure(bg=BG)
        root.resizable(False, False)

        self.stats = machine_stats()
        self.alive = True
        self.running = False
        self.job = None

        self.machines = [Machine(i) for i in range(NUM_MACHINES)]

        self._make_fonts()
        self._build()

        root.bind("<space>", lambda e: self.toggle())
        root.protocol("WM_DELETE_WINDOW", self._on_close)

        self._refresh_all()
        self._update_footer()

    # ---------------- fonts ----------------
    def _make_fonts(self):
        self.fonts = {
            "title":   tkfont.Font(family="Consolas", size=8,  weight="bold"),
            "tiny":    tkfont.Font(family="Consolas", size=7),
            "reel":    tkfont.Font(family="Consolas", size=11, weight="bold"),
            "credits": tkfont.Font(family="Consolas", size=10, weight="bold"),
            "h1":      tkfont.Font(family="Consolas", size=16, weight="bold"),
            "btn":     tkfont.Font(family="Consolas", size=10, weight="bold"),
            "foot":    tkfont.Font(family="Consolas", size=9),
        }

    # ---------------- layout ----------------
    def _build(self):
        # ---- header ----
        tk.Label(self.root, text="LUCKY  SEVENS  —  CASINO FLOOR",
                 font=self.fonts["h1"], fg=GOLD, bg=BG).pack(pady=(12, 2))

        tk.Label(
            self.root,
            text=(f"12 machines  •  {TURBO_SPINS_PER_SEC} spins/sec each  "
                  f"=  {NUM_MACHINES * TURBO_SPINS_PER_SEC:,} spins/sec total  •  "
                  f"RTP {self.stats['rtp'] * 100:.2f}%  •  "
                  f"jackpot 1 in {self.stats['jackpot_odds']:,.0f}"),
            font=self.fonts["foot"], fg=GREY, bg=BG
        ).pack()

        # ---- floor grid (4 columns x 3 rows) ----
        floor = tk.Frame(self.root, bg=BG)
        floor.pack(padx=10, pady=10)

        cols = 4
        self.panels = []
        for i, machine in enumerate(self.machines):
            panel = MachinePanel(floor, machine, self.fonts, self.toggle)
            panel.frame.configure(width=210, height=118)
            panel.frame.grid(row=i // cols, column=i % cols, padx=4, pady=4)
            self.panels.append(panel)

        # ---- controls ----
        ctl = tk.Frame(self.root, bg=BG)
        ctl.pack(pady=(2, 4))

        self.start_btn = tk.Button(
            ctl, text="▶  START ALL", font=self.fonts["btn"], width=13,
            bg=GOLD, fg="#101018",
            activebackground="#ffe680", activeforeground="#101018",
            relief="flat", bd=0, highlightthickness=0,
            cursor="hand2", command=self.toggle
        )
        self.start_btn.grid(row=0, column=0, padx=4, ipady=7)

        tk.Button(
            ctl, text="+500 ALL", font=self.fonts["btn"], width=9,
            bg="#1e1e2c", fg=GREEN,
            activebackground="#2a2a3d", activeforeground=GREEN,
            relief="flat", bd=0, highlightthickness=0,
            cursor="hand2", command=self._add_credits
        ).grid(row=0, column=1, padx=4, ipady=7)

        tk.Button(
            ctl, text="RESET ALL", font=self.fonts["btn"], width=9,
            bg="#1e1e2c", fg="#8a8aa0",
            activebackground="#2a2a3d", activeforeground="#c8c8d8",
            relief="flat", bd=0, highlightthickness=0,
            cursor="hand2", command=self._reset
        ).grid(row=0, column=2, padx=4, ipady=7)

        # ---- footer ----
        self.footer = tk.Label(self.root, text="", font=self.fonts["foot"],
                               fg=DIM, bg=BG)
        self.footer.pack(pady=(4, 14))

    # ---------------- control actions ----------------
    def toggle(self):
        if self.running:
            self._stop()
        else:
            self._start()

    def _start(self):
        if self.running or not self.alive:
            return
        if not any(m.credits >= BET for m in self.machines):
            self.footer.configure(text="All machines out of credits — press +500 ALL",
                                  fg="#ff8080")
            return
        self.running = True
        self.start_btn.configure(text="■  STOP ALL", bg="#ff6b6b",
                                 activebackground="#ff8a8a")
        self._tick()

    def _stop(self):
        self.running = False
        if self.job is not None:
            try:
                self.root.after_cancel(self.job)
            except Exception:
                pass
            self.job = None
        if self.alive:
            self.start_btn.configure(text="▶  START ALL", bg=GOLD,
                                     activebackground="#ffe680")
            self._update_footer()

    def _add_credits(self):
        for m in self.machines:
            m.credits += 500
        self._refresh_all()

    def _reset(self):
        if self.running:
            self._stop()
        for m in self.machines:
            m.reset()
        for p in self.panels:
            p.flash = 0
        self._refresh_all()
        self._update_footer()

    def _on_close(self):
        self.alive = False
        self._stop()
        self.root.destroy()

    # ---------------- turbo loop: 100 spins/sec x 12 machines ----------------
    def _tick(self):
        if not self.alive or not self.running:
            return

        any_active = False
        for m in self.machines:
            if m.credits >= BET:
                m.run_batch(TURBO_BATCH)
                any_active = True
            else:
                m.jackpot = False
                m.last_win = 0

        # one repaint per frame for every panel
        for p in self.panels:
            p.refresh()

        self._update_footer()

        if not any_active:
            self._stop()
            self.footer.configure(text="All machines out of credits — press +500 ALL",
                                  fg="#ff8080")
            return

        self.job = self.root.after(TURBO_FRAME_MS, self._tick)

    # ---------------- readouts ----------------
    def _refresh_all(self):
        for p in self.panels:
            p.refresh()

    def _update_footer(self):
        spins = sum(m.spins for m in self.machines)
        wagered = sum(m.total_wagered for m in self.machines)
        won = sum(m.total_won for m in self.machines)
        credits = sum(m.credits for m in self.machines)
        rtp = (won / wagered * 100) if wagered else 0.0

        self.footer.configure(
            text=(f"spins {spins:,}   |   wagered {wagered:,}   |   won {won:,}   "
                  f"|   observed RTP {rtp:.2f}%  (target {self.stats['rtp'] * 100:.2f}%)   "
                  f"|   credits in play {credits:,}"),
            fg=DIM
        )


# ----------------------------------------------------------------------
def main():
    st = machine_stats()
    print("=" * 64)
    print("  LUCKY SEVENS — 12-machine floor")
    print("=" * 64)
    for s in SYMBOLS:
        w = st["per_symbol"][s]
        print(f"  3 x {s:<8} weight {w:>8,}  pays {PAYTABLE[s]:>5}  "
              f"-> contributes {w * PAYTABLE[s]:>9,}")
    print("-" * 64)
    total = sum(st["per_symbol"][s] * PAYTABLE[s] for s in SYMBOLS)
    print(f"  weighted payout sum : {total:,}")
    print(f"  virtual outcomes    : {st['combos']:,}")
    print(f"  RTP                 : {st['rtp'] * 100:.4f}%")
    print(f"  hit rate            : {st['hit_rate'] * 100:.4f}%")
    print(f"  jackpot odds        : 1 in {st['jackpot_odds']:,.0f}")
    print(f"  machines            : {NUM_MACHINES}")
    print(f"  per-machine rate    : {TURBO_SPINS_PER_SEC} spins/sec "
          f"({TURBO_BATCH} per {TURBO_FRAME_MS} ms frame)")
    print(f"  floor rate          : {NUM_MACHINES * TURBO_SPINS_PER_SEC:,} spins/sec")
    print("=" * 64)

    root = tk.Tk()
    CasinoFloor(root)
    root.mainloop()


if __name__ == "__main__":
    main()