# -*- coding: utf-8 -*-
"""
THE 10-PUZZLE CHALLENGE  (granular progress edition)
====================================================
Ten different puzzle types. Progress is tracked at the tiniest level:
every letter, every cell, every tile. Percentages are shown to 3 decimals.
Everything auto-saves to  puzzle_progress.json  next to this file.

Run:  python puzzles.py
"""

import json
import os
import random
import string
import tkinter as tk
from tkinter import ttk, messagebox

SAVE_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                         "puzzle_progress.json")

BG      = "#101018"
CARD    = "#1c1c2a"
CARD_D  = "#14261c"
EDGE    = "#2e2e44"
TXT     = "#e8e8f0"
MUTED   = "#7c7c96"
BLUE    = "#7aa2f7"
GREEN   = "#9ece6a"
RED     = "#f7768e"


# ==========================================================================
#  SAVE / LOAD
# ==========================================================================
def load_data():
    try:
        with open(SAVE_FILE, "r") as f:
            return json.load(f)
    except Exception:
        return {}


def store_data(d):
    try:
        with open(SAVE_FILE, "w") as f:
            json.dump(d, f, indent=1)
    except Exception:
        pass


def norm(s):
    return "".join(ch for ch in s.upper() if ch.isalnum())


# ==========================================================================
#  FINE CANVAS PROGRESS BAR (smooth to 0.001%)
# ==========================================================================
class FineBar(tk.Canvas):
    def __init__(self, parent, height=22, show_ticks=True, **kw):
        super().__init__(parent, height=height, bg="#0a0a12",
                         highlightthickness=0, **kw)
        self.value = 0.0
        self.show_ticks = show_ticks
        self.bind("<Configure>", lambda e: self.redraw())

    def set(self, v):
        self.value = max(0.0, min(100.0, float(v)))
        self.redraw()

    def redraw(self):
        self.delete("all")
        w = self.winfo_width()
        h = self.winfo_height()
        if w < 5:
            return
        self.create_rectangle(0, 0, w, h, fill="#0a0a12", outline="#2e2e44")
        fw = int(w * self.value / 100.0)
        if fw > 2:
            color = GREEN if self.value >= 99.999 else BLUE
            self.create_rectangle(1, 1, fw, h - 1, fill=color, outline="")
        if self.show_ticks:
            for i in range(1, 10):
                x = int(w * i / 10.0)
                self.create_line(x, 2, x, h - 2, fill="#3a3a55")


# ==========================================================================
#  BASE PUZZLE
# ==========================================================================
class Puzzle:
    key = "p"
    title = "Puzzle"

    def __init__(self, app):
        self.app = app
        self.state = app.data.setdefault(self.key, {})
        if not self.state:
            self.state.update(self.init_state())
        self.win = None

    def init_state(self):
        return {}

    def progress(self):
        """Return a float 0.0 .. 1.0. MUST be granular."""
        return 0.0

    def build(self, parent):
        pass

    # ------------------------------------------------------------------
    def open(self):
        if self.progress() >= 0.99999:
            messagebox.showinfo("Complete",
                                "'%s' is already finished!" % self.title)
            return
        if self.win is not None and self.win.winfo_exists():
            self.win.lift()
            self.win.focus_force()
            return
        self.win = tk.Toplevel(self.app.root)
        self.win.title(self.title)
        self.win.configure(bg=BG)
        self.win.geometry("860x720")
        self.win.protocol("WM_DELETE_WINDOW", self.close)
        self.build(self.win)

    def close(self):
        self.app.save()
        self.app.update_progress()
        if self.win is not None:
            try:
                self.win.destroy()
            except Exception:
                pass
            self.win = None

    def touch(self):
        self.app.save()
        self.app.update_progress()


# ==========================================================================
#  1. WORD SEARCH
# ==========================================================================
WS_WORDS = ["ALGORITHM", "RECURSION", "VARIABLE", "FUNCTION", "INTERFACE",
            "COMPILER", "DATABASE", "NETWORK", "ITERATION", "BOOLEAN"]
WS_N = 12
WS_DIRS = [(0, 1), (1, 0), (1, 1), (1, -1), (0, -1), (-1, 0), (-1, -1), (-1, 1)]
WS_TOTAL_LETTERS = sum(len(w) for w in WS_WORDS)


def ws_generate(seed):
    rng = random.Random(seed)
    grid = [[None] * WS_N for _ in range(WS_N)]
    placed = {}
    for w in sorted(WS_WORDS, key=len, reverse=True):
        for _ in range(600):
            dr, dc = rng.choice(WS_DIRS)
            r = rng.randrange(WS_N)
            c = rng.randrange(WS_N)
            er, ec = r + dr * (len(w) - 1), c + dc * (len(w) - 1)
            if not (0 <= er < WS_N and 0 <= ec < WS_N):
                continue
            ok = True
            for i, ch in enumerate(w):
                v = grid[r + dr * i][c + dc * i]
                if v is not None and v != ch:
                    ok = False
                    break
            if not ok:
                continue
            for i, ch in enumerate(w):
                grid[r + dr * i][c + dc * i] = ch
            placed[w] = (r, c, dr, dc)
            break
    for r in range(WS_N):
        for c in range(WS_N):
            if grid[r][c] is None:
                grid[r][c] = rng.choice(string.ascii_uppercase)
    return grid, placed


class WordSearch(Puzzle):
    key = "word_search"
    title = "Word Search"

    def init_state(self):
        rng = random.Random()
        for _ in range(200):
            seed = rng.randrange(10 ** 9)
            _, pl = ws_generate(seed)
            if len(pl) == len(WS_WORDS):
                return {"seed": seed, "found": []}
        return {"seed": 0, "found": []}

    def progress(self):
        found = set(self.state.get("found", []))
        got = sum(len(w) for w in found if w in WS_WORDS)
        return got / float(WS_TOTAL_LETTERS)

    def cells_of(self, word):
        for r in range(WS_N):
            for c in range(WS_N):
                for dr, dc in WS_DIRS:
                    er, ec = r + dr * (len(word) - 1), c + dc * (len(word) - 1)
                    if 0 <= er < WS_N and 0 <= ec < WS_N:
                        if all(self.grid[r + dr * i][c + dc * i] == word[i]
                               for i in range(len(word))):
                            return [(r + dr * i, c + dc * i)
                                    for i in range(len(word))]
        return []

    def build(self, parent):
        self.grid, _ = ws_generate(self.state["seed"])
        self.found = set(self.state.get("found", []))
        self.sel = None

        wrap = tk.Frame(parent, bg=BG)
        wrap.pack(fill="both", expand=True, padx=14, pady=14)

        left = tk.Frame(wrap, bg=BG)
        left.pack(side="left")
        right = tk.Frame(wrap, bg=BG)
        right.pack(side="left", padx=24, anchor="n")

        self.buttons = []
        for r in range(WS_N):
            row = []
            for c in range(WS_N):
                b = tk.Button(left, text=self.grid[r][c], width=2,
                              font=("Consolas", 11, "bold"),
                              bg=CARD, fg="#c8c8e0", activebackground=EDGE,
                              relief="flat", bd=0,
                              command=lambda r=r, c=c: self.click(r, c))
                b.grid(row=r, column=c, padx=1, pady=1, ipadx=2, ipady=2)
                row.append(b)
            self.buttons.append(row)

        tk.Label(right, text="FIND THESE WORDS", font=("Segoe UI", 11, "bold"),
                 bg=BG, fg=BLUE).pack(anchor="w", pady=(0, 6))
        self.word_labels = {}
        for w in WS_WORDS:
            l = tk.Label(right, text=w, font=("Consolas", 11), bg=BG, fg=MUTED)
            l.pack(anchor="w", pady=1)
            self.word_labels[w] = l

        tk.Label(right,
                 text="\nClick the first letter,\nthen click the last letter.",
                 font=("Segoe UI", 9), bg=BG, fg=MUTED,
                 justify="left").pack(anchor="w", pady=(16, 0))

        self.repaint()

    def repaint(self):
        for r in range(WS_N):
            for c in range(WS_N):
                self.buttons[r][c].config(bg=CARD, fg="#c8c8e0")
        for w in self.found:
            for (r, c) in self.cells_of(w):
                self.buttons[r][c].config(bg="#2f6b5a", fg="#d8ffe8")
        for w in WS_WORDS:
            self.word_labels[w].config(fg=GREEN if w in self.found else MUTED)

    def click(self, r, c):
        if self.sel is None:
            self.sel = (r, c)
            self.buttons[r][c].config(bg="#3d5a80")
            return
        r0, c0 = self.sel
        self.sel = None
        if (r0, c0) == (r, c):
            self.repaint(); return
        dr, dc = r - r0, c - c0
        n = max(abs(dr), abs(dc))
        if not (dr == 0 or dc == 0 or abs(dr) == abs(dc)):
            self.repaint(); return
        dr //= n; dc //= n
        word = "".join(self.grid[r0 + dr * i][c0 + dc * i]
                       for i in range(n + 1))
        pick = None
        if word in WS_WORDS and word not in self.found:
            pick = word
        elif word[::-1] in WS_WORDS and word[::-1] not in self.found:
            pick = word[::-1]
        if pick:
            self.found.add(pick)
            self.state["found"] = sorted(self.found)
            self.touch()
        self.repaint()


# ==========================================================================
#  2. CROSSWORD
# ==========================================================================
CW5 = ("ABOUT ABOVE ACTOR ACUTE ADMIT ADOPT ADULT AFTER AGAIN AGENT AGREE "
       "AHEAD ALARM ALBUM ALERT ALIKE ALIVE ALLOW ALONE ALONG ALTER AMONG "
       "ANGER ANGLE ANGRY APART APPLE APPLY ARENA ARGUE ARISE ARRAY ARROW "
       "ASIDE ASSET AUDIO AVOID AWARD AWARE BASIC BEACH BEGAN BEGIN BEING "
       "BELOW BENCH BIRTH BLACK BLAME BLIND BLOCK BLOOD BOARD BOOST BOUND "
       "BRAIN BRAND BRAVE BREAD BREAK BREED BRIEF BRING BROAD BROKE BROWN "
       "BUILD BUILT BUYER CABLE CARRY CATCH CAUSE CHAIN CHAIR CHART CHASE "
       "CHEAP CHECK CHEST CHIEF CHILD CHOSE CIVIL CLAIM CLASS CLEAN CLEAR "
       "CLICK CLOCK CLOSE COACH COAST COUNT COURT COVER CRAFT CRASH CREAM "
       "CRIME CROSS CROWD CROWN CURVE CYCLE DAILY DANCE DEALT DEATH DEBUT "
       "DELAY DEPTH DOING DOUBT DOZEN DRAFT DRAMA DRAWN DREAM DRESS DRINK "
       "DRIVE DROVE EAGER EARLY EARTH EIGHT ELITE EMPTY ENEMY ENJOY ENTER "
       "ENTRY EQUAL ERROR EVENT EVERY EXACT EXIST EXTRA FAITH FALSE FAULT "
       "FIBER FIELD FIFTH FIFTY FIGHT FINAL FIRST FIXED FLASH FLEET FLOOR "
       "FLUID FOCUS FORCE FORTH FORTY FORUM FOUND FRAME FRANK FRAUD FRESH "
       "FRONT FRUIT FULLY FUNNY GIANT GIVEN GLASS GLOBE GOING GRACE GRADE "
       "GRAND GRANT GRASS GREAT GREEN GROSS GROUP GROWN GUARD GUESS GUEST "
       "GUIDE HAPPY HEART HEAVY HENCE HORSE HOTEL HOUSE HUMAN IDEAL IMAGE "
       "INDEX INNER INPUT ISSUE JOINT JUDGE KNOWN LABEL LARGE LASER LATER "
       "LAUGH LAYER LEARN LEASE LEAST LEAVE LEGAL LEVEL LIGHT LIMIT LOCAL "
       "LOGIC LOOSE LOWER LUCKY LUNCH LYING MAGIC MAJOR MAKER MARCH MATCH "
       "MAYBE MAYOR MEANT MEDIA METAL MIGHT MINOR MINUS MIXED MODEL MONEY "
       "MONTH MORAL MOTOR MOUNT MOUSE MOUTH MOVIE MUSIC NEEDS NEVER NEWLY "
       "NIGHT NOISE NORTH NOTED NOVEL NURSE OCCUR OCEAN OFFER OFTEN ORDER "
       "OTHER OUGHT PAINT PANEL PAPER PARTY PEACE PHASE PHONE PHOTO PIECE "
       "PILOT PITCH PLACE PLAIN PLANE PLANT PLATE POINT POUND POWER PRESS "
       "PRICE PRIDE PRIME PRINT PRIOR PRIZE PROOF PROUD PROVE QUICK QUIET "
       "QUITE RADIO RAISE RANGE RAPID RATIO REACH READY REALM REBEL REFER "
       "RELAX REPLY RIGHT RIVAL RIVER ROMAN ROUGH ROUND ROUTE ROYAL RURAL "
       "SCALE SCENE SCOPE SCORE SENSE SERVE SEVEN SHALL SHAPE SHARE SHARP "
       "SHEET SHELF SHELL SHIFT SHINE SHIRT SHOCK SHOOT SHORT SHOWN SIGHT "
       "SINCE SIXTH SIXTY SKILL SLEEP SLIDE SMALL SMART SMILE SMOKE SOLID "
       "SOLVE SORRY SOUND SOUTH SPACE SPEAK SPEED SPEND SPENT SPLIT SPOKE "
       "SPORT STAFF STAGE STAKE STAND START STATE STEAM STEEL STICK STILL "
       "STOCK STONE STOOD STORE STORM STORY STRIP STUCK STUDY STUFF STYLE "
       "SUGAR SUITE SUPER SWEET TABLE TAKEN TASTE TEACH TEETH THANK THEFT "
       "THEIR THEME THERE THESE THICK THING THINK THIRD THOSE THREE THREW "
       "THROW THUMB TIGHT TIMER TIRED TITLE TODAY TOKEN TOPIC TOTAL TOUCH "
       "TOUGH TOWER TRACK TRADE TRAIN TREAT TREND TRIAL TRIED TRUCK TRULY "
       "TRUST TRUTH TWICE UNDER UNION UNITY UNTIL UPPER UPSET URBAN USAGE "
       "USUAL VALID VALUE VIDEO VIRUS VISIT VITAL VOCAL VOICE WASTE WATCH "
       "WATER WHEEL WHERE WHICH WHILE WHITE WHOLE WHOSE WOMAN WOMEN WORLD "
       "WORRY WORSE WORST WORTH WOULD WOUND WRITE WRONG WROTE YOUNG YOUTH"
       ).split()

CW3 = ("ACE ACT ADD AGE AGO AID AIM AIR ALL AND ANY APE ARC ARE ARM ART "
       "ASH ASK ATE AWE BAD BAG BAN BAR BAT BAY BED BEE BEG BET BID BIG "
       "BIN BIT BOW BOX BOY BUD BUG BUN BUS BUT BUY CAB CAN CAP CAR CAT "
       "COW CRY CUB CUE CUP CUT DAY DEN DEW DID DIE DIG DIM DIP DOG DOT "
       "DRY DUE DUG EAR EAT EBB EEL EGG EGO ELF ELK ELM END ERA EVE EYE "
       "FAN FAR FAT FEE FEW FIG FIN FIR FIT FLY FOG FOR FOX FRY FUN FUR "
       "GAP GAS GEL GEM GET GUM GUN GUT GUY GYM HAM HAS HAT HAY HEN HER "
       "HID HIM HIP HIS HIT HOG HOP HOT HOW HUB HUE HUG HUT ICE ICY ILL "
       "INK INN ION IRE IVY JAM JAR JAW JET JOB JOG JOY JUG KEG KEY KID "
       "KIN KIT LAB LAD LAG LAP LAW LAY LED LEG LET LID LIE LIP LIT LOG "
       "LOT LOW MAD MAN MAP MAT MEN MET MIX MOB MOP MUD MUG NAP NET NEW "
       "NIL NIP NOD NOR NOT NOW NUT OAK OAR OAT ODD ODE OIL OLD ONE OPT "
       "ORB ORE OUR OUT OWE OWL OWN PAD PAL PAN PAR PAT PAW PAY PEA PEG "
       "PEN PET PEW PIE PIG PIN PIT PLY POD POT PRO PRY PUB PUP PUT RAG "
       "RAM RAN RAP RAT RAW RAY RED REF RIB RID RIG RIM RIP ROB ROD ROE "
       "ROT ROW RUB RUG RUM RUN RYE SAD SAP SAT SAW SAY SEA SEE SET SEW "
       "SHE SHY SIN SIP SIR SIT SIX SKI SKY SLY SOB SOD SON SOW SOY SPA "
       "SPY SUM SUN TAB TAG TAN TAP TAR TAX TEA TEN THE TIE TIN TIP TOE "
       "TON TOO TOP TOW TOY TRY TUB TUG TWO URN USE VAN VAT VET VIA VIE "
       "VOW WAR WAS WAX WAY WEB WED WET WHO WHY WIG WIN WIT WOE WON WOO "
       "YES YET YOU ZOO").split()


def cw_generate(seed):
    rng = random.Random(seed)
    w3 = set(CW3)
    by12, bymid = {}, {}
    for w in CW5:
        by12.setdefault(w[1:3], []).append(w)
        bymid.setdefault(w[1:4], []).append(w)
    rows = CW5[:]
    rng.shuffle(rows)
    for r1 in rows:
        for r2 in rows:
            if r2 == r1:
                continue
            l1 = by12.get(r1[1] + r2[1])
            if not l1: continue
            l2 = by12.get(r1[2] + r2[2])
            if not l2: continue
            l3 = by12.get(r1[3] + r2[3])
            if not l3: continue
            for c1 in l1:
                for c2 in l2:
                    for c3 in l3:
                        for r3 in bymid.get(c1[3] + c2[3] + c3[3], ()):
                            if r1[0] + r2[0] + r3[0] not in w3: continue
                            if r1[4] + r2[4] + r3[4] not in w3: continue
                            if c1[0] + c2[0] + c3[0] not in w3: continue
                            if c1[4] + c2[4] + c3[4] not in w3: continue
                            return (r1, r2, r3, c1, c2, c3)
    return None


def cw_layout(r1, r2, r3, c1, c2, c3):
    g = [[None] * 5 for _ in range(5)]
    g[0][1], g[0][2], g[0][3] = c1[0], c2[0], c3[0]
    g[4][1], g[4][2], g[4][3] = c1[4], c2[4], c3[4]
    for j, ch in enumerate(r1): g[1][j] = ch
    for j, ch in enumerate(r2): g[2][j] = ch
    for j, ch in enumerate(r3): g[3][j] = ch
    return g


class Crossword(Puzzle):
    key = "crossword"
    title = "Crossword"

    def init_state(self):
        rng = random.Random()
        for _ in range(300):
            words = cw_generate(rng.randrange(10 ** 9))
            if words:
                return {"words": list(words), "cells": {}}
        return {"words": None, "cells": {}}

    def solution(self):
        if not self.state.get("words"):
            return None
        return cw_layout(*self.state["words"])

    def progress(self):
        sol = self.solution()
        if not sol: return 0.0
        cells = self.state.get("cells", {})
        total = sum(1 for r in range(5) for c in range(5) if sol[r][c])
        if not total: return 0.0
        good = sum(1 for r in range(5) for c in range(5)
                   if sol[r][c] and cells.get("%d,%d" % (r, c)) == sol[r][c])
        return good / float(total)

    def build(self, parent):
        sol = self.solution()
        if sol is None:
            tk.Label(parent, text="Crossword generation failed.",
                     bg=BG, fg=RED).pack(pady=40)
            return
        wrap = tk.Frame(parent, bg=BG)
        wrap.pack(fill="both", expand=True, padx=20, pady=20)
        left = tk.Frame(wrap, bg=BG); left.pack(side="left")
        right = tk.Frame(wrap, bg=BG); right.pack(side="left", padx=28, anchor="n")

        saved = self.state.get("cells", {})
        self.entries = {}
        self.vars = {}
        for r in range(5):
            for c in range(5):
                if sol[r][c] is None:
                    tk.Label(left, text="", width=3, height=1, bg="#000000",
                             font=("Consolas", 16)).grid(
                        row=r, column=c, padx=2, pady=2, ipadx=6, ipady=6)
                    continue
                v = tk.StringVar(value=saved.get("%d,%d" % (r, c), ""))
                e = tk.Entry(left, textvariable=v, width=2,
                             font=("Consolas", 16), justify="center",
                             bg=CARD, fg=TXT, insertbackground=BLUE,
                             relief="flat", bd=0)
                e.grid(row=r, column=c, padx=2, pady=2, ipadx=6, ipady=6)
                self.entries[(r, c)] = e
                self.vars[(r, c)] = v
                v.trace_add("write", lambda *a: self.changed())

        tk.Label(right, text="WORDS TO PLACE", font=("Segoe UI", 11, "bold"),
                 bg=BG, fg=BLUE).pack(anchor="w", pady=(0, 8))
        words = self.state["words"]
        five = sorted([w for w in words if len(w) == 5])
        three = sorted([w for w in words if len(w) == 3])
        tk.Label(right, text="5 letters", font=("Segoe UI", 9, "bold"),
                 bg=BG, fg=MUTED).pack(anchor="w")
        for w in five:
            tk.Label(right, text="  " + w, font=("Consolas", 12),
                     bg=BG, fg=TXT).pack(anchor="w")
        tk.Label(right, text="\n3 letters", font=("Segoe UI", 9, "bold"),
                 bg=BG, fg=MUTED).pack(anchor="w")
        for w in three:
            tk.Label(right, text="  " + w, font=("Consolas", 12),
                     bg=BG, fg=TXT).pack(anchor="w")
        tk.Label(right,
                 text="\nFill every white square.\nCorrect letters turn green.",
                 font=("Segoe UI", 9), bg=BG, fg=MUTED,
                 justify="left").pack(anchor="w", pady=(18, 0))
        self.sol = sol
        self.repaint()

    def changed(self):
        cells = {}
        for (r, c), v in self.vars.items():
            t = v.get().strip().upper()[:1]
            if t:
                cells["%d,%d" % (r, c)] = t
        self.state["cells"] = cells
        self.repaint()
        self.touch()

    def repaint(self):
        for (r, c), e in self.entries.items():
            val = self.vars[(r, c)].get().strip().upper()
            if val and val == self.sol[r][c]:
                e.config(bg="#1f4436", fg=GREEN)
            else:
                e.config(bg=CARD, fg=TXT)


# ==========================================================================
#  3. SUDOKU 6x6
# ==========================================================================
def sd_generate(seed):
    rng = random.Random(seed)
    base = [[1, 2, 3, 4, 5, 6], [4, 5, 6, 1, 2, 3],
            [2, 3, 4, 5, 6, 1], [5, 6, 1, 2, 3, 4],
            [3, 4, 5, 6, 1, 2], [6, 1, 2, 3, 4, 5]]
    perm = [1, 2, 3, 4, 5, 6]
    rng.shuffle(perm)
    g = [[perm[v - 1] for v in row] for row in base]
    bands = [g[0:2], g[2:4], g[4:6]]
    for b in bands: rng.shuffle(b)
    rng.shuffle(bands)
    g = bands[0] + bands[1] + bands[2]
    stacks = [[0, 1, 2], [3, 4, 5]]
    for s in stacks: rng.shuffle(s)
    rng.shuffle(stacks)
    order = stacks[0] + stacks[1]
    g = [[row[i] for i in order] for row in g]
    cells = [(r, c) for r in range(6) for c in range(6)]
    rng.shuffle(cells)
    keep = set(cells[:16])
    given = [[g[r][c] if (r, c) in keep else 0 for c in range(6)]
             for r in range(6)]
    return g, given


class Sudoku(Puzzle):
    key = "sudoku"
    title = "Sudoku 6x6"

    def init_state(self):
        sol, given = sd_generate(random.randrange(10 ** 9))
        return {"solution": sol, "given": given, "cells": {}}

    def blanks(self):
        g = self.state["given"]
        return [(r, c) for r in range(6) for c in range(6) if g[r][c] == 0]

    def progress(self):
        sol = self.state["solution"]
        cells = self.state.get("cells", {})
        blanks = self.blanks()
        if not blanks: return 0.0
        good = sum(1 for (r, c) in blanks
                   if cells.get("%d,%d" % (r, c)) == str(sol[r][c]))
        return good / float(len(blanks))

    def build(self, parent):
        sol = self.state["solution"]
        given = self.state["given"]
        saved = self.state.get("cells", {})

        tk.Label(parent,
                 text="Fill every empty square with 1-6.\n"
                      "Every row, column and 2x3 box must contain each digit once.",
                 font=("Segoe UI", 10), bg=BG, fg=MUTED,
                 justify="left").pack(anchor="w", padx=20, pady=(16, 8))
        frame = tk.Frame(parent, bg=BG); frame.pack(pady=10)
        self.vars = {}; self.entries = {}
        for r in range(6):
            for c in range(6):
                px = 6 if c % 3 == 0 and c else 2
                py = 6 if r % 2 == 0 and r else 2
                if given[r][c]:
                    tk.Label(frame, text=str(given[r][c]), width=2,
                             font=("Consolas", 20, "bold"), bg="#22223a",
                             fg="#c8c8e0").grid(row=r, column=c, padx=px,
                                                pady=py, ipadx=8, ipady=8)
                else:
                    v = tk.StringVar(value=saved.get("%d,%d" % (r, c), ""))
                    e = tk.Entry(frame, textvariable=v, width=2,
                                 font=("Consolas", 20), justify="center",
                                 bg=CARD, fg=BLUE, relief="flat", bd=0,
                                 insertbackground=BLUE)
                    e.grid(row=r, column=c, padx=px, pady=py, ipadx=8, ipady=8)
                    self.vars[(r, c)] = v
                    self.entries[(r, c)] = e
                    v.trace_add("write", lambda *a: self.changed())
        self.sol = sol
        self.repaint()

    def changed(self):
        cells = {}
        for (r, c), v in self.vars.items():
            t = v.get().strip()[:1]
            if t:
                cells["%d,%d" % (r, c)] = t
        self.state["cells"] = cells
        self.repaint()
        self.touch()

    def repaint(self):
        for (r, c), e in self.entries.items():
            val = self.vars[(r, c)].get().strip()
            if val and val == str(self.sol[r][c]):
                e.config(bg="#1f4436", fg=GREEN)
            else:
                e.config(bg=CARD, fg=BLUE)


# ==========================================================================
#  4. QUIZ
# ==========================================================================
QUIZ = [
    ("What is the capital of Australia?",
     ["Sydney", "Canberra", "Melbourne", "Perth"], 1),
    ("Which element has the chemical symbol 'W'?",
     ["Wolframite", "Tungsten", "Titanium", "Tin"], 1),
    ("Who wrote 'One Hundred Years of Solitude'?",
     ["Jorge Luis Borges", "Isabel Allende", "Gabriel Garcia Marquez",
      "Pablo Neruda"], 2),
    ("What is the smallest prime number greater than 100?",
     ["101", "103", "107", "109"], 0),
    ("Which planet has the most confirmed moons?",
     ["Jupiter", "Saturn", "Uranus", "Neptune"], 1),
    ("In which year did the Berlin Wall fall?",
     ["1987", "1988", "1989", "1991"], 2),
    ("What is the longest river in Asia?",
     ["Yellow River", "Mekong", "Ganges", "Yangtze"], 3),
    ("Who proved Fermat's Last Theorem in 1994?",
     ["Andrew Wiles", "Terence Tao", "Paul Erdos", "John Nash"], 0),
    ("Which country spans the most time zones?",
     ["Russia", "USA", "France", "China"], 2),
    ("What is the only metal that is liquid at room temperature?",
     ["Gallium", "Mercury", "Caesium", "Bromine"], 1),
]


class Quiz(Puzzle):
    key = "quiz"
    title = "Trivia Quiz"

    def init_state(self):
        return {"solved": [], "wrong": []}

    def progress(self):
        return len(self.state.get("solved", [])) / float(len(QUIZ))

    def build(self, parent):
        solved = set(self.state.get("solved", []))
        wrong = set(self.state.get("wrong", []))
        self.buttons = {}

        tk.Label(parent, text="Answer all ten correctly.",
                 font=("Segoe UI", 11), bg=BG, fg=MUTED).pack(pady=(12, 6))
        holder = tk.Frame(parent, bg=BG)
        holder.pack(fill="both", expand=True, padx=16)

        for i, (q, opts, correct) in enumerate(QUIZ):
            row = tk.Frame(holder, bg=BG); row.pack(fill="x", pady=3)
            done = i in solved
            tk.Label(row, text="%d. %s" % (i + 1, q), font=("Segoe UI", 10),
                     bg=BG, fg=GREEN if done else TXT, anchor="w",
                     width=42, wraplength=380, justify="left").pack(side="left")
            for j, o in enumerate(opts):
                b = tk.Button(row, text=o, font=("Segoe UI", 9),
                              bg=CARD, fg="#c8c8e0", relief="flat",
                              activebackground=EDGE, width=14,
                              command=lambda i=i, j=j: self.answer(i, j))
                b.pack(side="left", padx=2)
                self.buttons[(i, j)] = b
                if done and j == correct:
                    b.config(bg="#1f4436", fg=GREEN)
                elif (i, j) in self._wrong_set:
                    b.config(bg="#4a1f28", fg=RED)

    _wrong_set = set()

    def answer(self, i, j):
        solved = set(self.state.get("solved", []))
        if i in solved:
            return
        q, opts, correct = QUIZ[i]
        if j == correct:
            solved.add(i)
            self.state["solved"] = sorted(solved)
            self.touch()
            self.buttons[(i, j)].config(bg="#1f4436", fg=GREEN)
        else:
            self.buttons[(i, j)].config(bg="#4a1f28", fg=RED)


# ==========================================================================
#  5. ANAGRAMS
# ==========================================================================
ANAGRAMS = ["ZEPHYR", "QUARTZ", "RHYTHM", "MNEMONIC", "PARADOX",
            "JUXTAPOSE", "QUARANTINE", "KALEIDOSCOPE", "OXYMORON", "XYLOPHONE"]
ANA_TOTAL_LETTERS = sum(len(w) for w in ANAGRAMS)


class Anagram(Puzzle):
    key = "anagram"
    title = "Anagrams"

    def init_state(self):
        rng = random.Random()
        scram = {}
        for w in ANAGRAMS:
            letters = list(w)
            for _ in range(50):
                rng.shuffle(letters)
                s = "".join(letters)
                if s != w: break
            scram[w] = s
        return {"scram": scram, "solved": []}

    def progress(self):
        solved = set(self.state.get("solved", []))
        got = sum(len(w) for w in solved if w in ANAGRAMS)
        return got / float(ANA_TOTAL_LETTERS)

    def build(self, parent):
        solved = set(self.state.get("solved", []))
        self.entries = {}
        self.labels = {}
        tk.Label(parent, text="Unscramble the words. Longer words = harder.",
                 font=("Segoe UI", 11), bg=BG, fg=MUTED).pack(pady=(14, 10))
        holder = tk.Frame(parent, bg=BG)
        holder.pack(padx=30, fill="x")
        for w in ANAGRAMS:
            row = tk.Frame(holder, bg=BG); row.pack(fill="x", pady=5)
            tk.Label(row, text=self.state["scram"][w],
                     font=("Consolas", 16, "bold"), bg=BG,
                     fg=BLUE if w not in solved else GREEN,
                     width=16, anchor="w").pack(side="left")
            v = tk.StringVar()
            e = tk.Entry(row, textvariable=v, font=("Consolas", 14),
                         bg=CARD, fg=TXT, relief="flat", width=18,
                         insertbackground=BLUE)
            e.pack(side="left", padx=10, ipady=4)
            e.bind("<KeyRelease>", lambda ev, w=w: self.check(w))
            self.entries[w] = (e, v)
            self.labels[w] = row
            if w in solved:
                v.set(w)
                e.config(state="disabled", disabledbackground="#1f4436",
                         disabledforeground=GREEN)

    def check(self, w):
        solved = set(self.state.get("solved", []))
        if w in solved: return
        e, v = self.entries[w]
        if norm(v.get()) == w:
            solved.add(w)
            self.state["solved"] = sorted(solved)
            v.set(w)
            e.config(state="disabled", disabledbackground="#1f4436",
                     disabledforeground=GREEN)
            self.touch()


# ==========================================================================
#  6. NUMBER SEQUENCES
# ==========================================================================
SEQUENCES = [
    ("2, 3, 5, 7, 11, 13, ?", "17"),
    ("1, 1, 2, 3, 5, 8, 13, ?", "21"),
    ("1, 4, 9, 16, 25, ?", "36"),
    ("2, 6, 12, 20, 30, ?", "42"),
    ("1, 2, 6, 24, 120, ?", "720"),
    ("3, 7, 15, 31, 63, ?", "127"),
    ("1, 8, 27, 64, 125, ?", "216"),
    ("2, 12, 36, 80, 150, ?", "252"),
    ("1, 3, 8, 21, 55, ?", "144"),
    ("4, 9, 25, 49, 121, ?", "169"),
]


class Sequence(Puzzle):
    key = "sequence"
    title = "Number Sequences"

    def init_state(self):
        return {"solved": [], "typed": {}}

    def progress(self):
        # solved ones count fully, typed-but-unconfirmed partials count a bit
        solved = set(self.state.get("solved", []))
        n = len(SEQUENCES)
        base = len(solved) / float(n)
        return min(0.999, base)

    def build(self, parent):
        solved = set(self.state.get("solved", []))
        self.entries = {}
        tk.Label(parent, text="Work out the next number in each sequence.",
                 font=("Segoe UI", 11), bg=BG, fg=MUTED).pack(pady=(16, 14))
        holder = tk.Frame(parent, bg=BG)
        holder.pack(padx=30, fill="x")
        for idx, (seq, ans) in enumerate(SEQUENCES):
            row = tk.Frame(holder, bg=BG); row.pack(fill="x", pady=6)
            tk.Label(row, text="%2d." % (idx + 1), font=("Consolas", 13),
                     bg=BG, fg=MUTED).pack(side="left")
            tk.Label(row, text=seq, font=("Consolas", 15, "bold"),
                     bg=BG, fg=BLUE if idx not in solved else GREEN,
                     width=30, anchor="w").pack(side="left")
            v = tk.StringVar()
            e = tk.Entry(row, textvariable=v, font=("Consolas", 14),
                         bg=CARD, fg=TXT, relief="flat", width=10,
                         insertbackground=BLUE)
            e.pack(side="left", padx=10, ipady=3)
            e.bind("<KeyRelease>", lambda ev, i=idx: self.check(i))
            self.entries[idx] = (e, v)
            if idx in solved:
                v.set(ans)
                e.config(state="disabled", disabledbackground="#1f4436",
                         disabledforeground=GREEN)

    def check(self, idx):
        solved = set(self.state.get("solved", []))
        if idx in solved: return
        e, v = self.entries[idx]
        if norm(v.get()) == SEQUENCES[idx][1]:
            solved.add(idx)
            self.state["solved"] = sorted(solved)
            v.set(SEQUENCES[idx][1])
            e.config(state="disabled", disabledbackground="#1f4436",
                     disabledforeground=GREEN)
            self.touch()


# ==========================================================================
#  7. CIPHER
# ==========================================================================
CIPHER_PLAIN = "THE ONLY WAY TO DO GREAT WORK IS TO LOVE WHAT YOU DO"
CIPHER_NORM = norm(CIPHER_PLAIN)
CIPHER_LEN = len(CIPHER_NORM)


def caesar(text, k):
    out = []
    for ch in text:
        if ch.isalpha():
            out.append(chr((ord(ch) - 65 + k) % 26 + 65))
        else:
            out.append(ch)
    return "".join(out)


class Cipher(Puzzle):
    key = "cipher"
    title = "Cipher Decode"

    def init_state(self):
        return {"shift": random.randint(4, 22), "answer": ""}

    def progress(self):
        # count matching letters one at a time — TINY increments
        ans = norm(self.state.get("answer", ""))
        if not CIPHER_NORM: return 0.0
        matches = sum(1 for i, ch in enumerate(ans)
                      if i < CIPHER_LEN and ch == CIPHER_NORM[i])
        return matches / float(CIPHER_LEN)

    def build(self, parent):
        cipher = caesar(CIPHER_PLAIN, self.state["shift"])

        tk.Label(parent, text="CAESAR CIPHER", font=("Segoe UI", 16, "bold"),
                 bg=BG, fg=BLUE).pack(pady=(24, 4))
        tk.Label(parent,
                 text="Every letter has been shifted forward in the alphabet.\n"
                      "Work out the shift and type the decoded sentence below.",
                 font=("Segoe UI", 10), bg=BG, fg=MUTED,
                 justify="center").pack(pady=(0, 20))

        box = tk.Frame(parent, bg=CARD); box.pack(padx=40, pady=10)
        tk.Label(box, text=cipher, font=("Consolas", 15, "bold"),
                 bg=CARD, fg="#ffcc66", wraplength=680,
                 justify="center").pack(padx=24, pady=18)

        tk.Label(parent, text="DECODED MESSAGE", font=("Segoe UI", 9, "bold"),
                 bg=BG, fg=MUTED).pack(pady=(24, 4))

        v = tk.StringVar(value=self.state.get("answer", ""))
        e = tk.Entry(parent, textvariable=v, font=("Consolas", 14),
                     bg=CARD, fg=TXT, relief="flat", width=64,
                     insertbackground=BLUE)
        e.pack(ipady=8, padx=40)
        e.bind("<KeyRelease>", lambda ev: self.changed(v))
        e.focus_set()

        self.status = tk.Label(parent, text="", font=("Segoe UI", 10),
                               bg=BG, fg=GREEN)
        self.status.pack(pady=12)
        self.changed(v, first=True)

    def changed(self, v, first=False):
        self.state["answer"] = v.get().upper()
        p = self.progress()
        self.status.config(text="%d of %d letters correct (%.3f%%)"
                                % (round(p * CIPHER_LEN), CIPHER_LEN,
                                   p * 100.0))
        if not first:
            self.touch()


# ==========================================================================
#  8. RIDDLES
# ==========================================================================
RIDDLES = [
    ("I speak without a mouth and hear without ears. "
     "I have no body, but I come alive with wind. What am I?", ["ECHO"]),
    ("The more you take, the more you leave behind. What am I?",
     ["FOOTSTEPS", "FOOTPRINTS", "STEPS"]),
    ("I have keys but no locks. I have space but no room. "
     "You can enter, but you can't go outside. What am I?", ["KEYBOARD"]),
    ("What has a head, a tail, but no body?", ["COIN"]),
    ("What gets wetter and wetter the more it dries?", ["TOWEL"]),
    ("I am not alive, but I grow. I don't have lungs, but I need air. "
     "I don't have a mouth, and I die if I drink. What am I?",
     ["FIRE", "A FIRE"]),
]


class Riddle(Puzzle):
    key = "riddle"
    title = "Riddles"

    def init_state(self):
        return {"solved": []}

    def progress(self):
        return len(self.state.get("solved", [])) / float(len(RIDDLES))

    def build(self, parent):
        solved = set(self.state.get("solved", []))
        self.entries = {}
        tk.Label(parent, text="Solve every riddle.",
                 font=("Segoe UI", 11), bg=BG, fg=MUTED).pack(pady=(14, 10))
        holder = tk.Frame(parent, bg=BG)
        holder.pack(fill="both", expand=True, padx=24)
        for i, (q, answers) in enumerate(RIDDLES):
            box = tk.Frame(holder, bg=CARD); box.pack(fill="x", pady=5)
            tk.Label(box, text="%d.  %s" % (i + 1, q), font=("Segoe UI", 10),
                     bg=CARD, fg=GREEN if i in solved else TXT,
                     wraplength=740, justify="left",
                     anchor="w").pack(anchor="w", padx=14, pady=(10, 4))
            v = tk.StringVar()
            e = tk.Entry(box, textvariable=v, font=("Consolas", 13),
                         bg="#101018", fg=TXT, relief="flat", width=30,
                         insertbackground=BLUE)
            e.pack(anchor="w", padx=14, pady=(0, 12), ipady=4)
            e.bind("<KeyRelease>", lambda ev, i=i: self.check(i))
            self.entries[i] = (e, v, answers)
            if i in solved:
                v.set(answers[0])
                e.config(state="disabled", disabledbackground="#1f4436",
                         disabledforeground=GREEN)

    def check(self, i):
        solved = set(self.state.get("solved", []))
        if i in solved: return
        e, v, answers = self.entries[i]
        if norm(v.get()) in [norm(a) for a in answers]:
            solved.add(i)
            self.state["solved"] = sorted(solved)
            v.set(answers[0])
            e.config(state="disabled", disabledbackground="#1f4436",
                     disabledforeground=GREEN)
            self.touch()


# ==========================================================================
#  9. 15-PUZZLE
# ==========================================================================
class Slide(Puzzle):
    key = "slide"
    title = "15-Puzzle"

    def init_state(self):
        rng = random.Random()
        board = list(range(1, 16)) + [0]
        blank = 15
        last = -1
        for _ in range(500):
            r, c = divmod(blank, 4)
            opts = []
            for dr, dc in ((1, 0), (-1, 0), (0, 1), (0, -1)):
                nr, nc = r + dr, c + dc
                if 0 <= nr < 4 and 0 <= nc < 4:
                    ni = nr * 4 + nc
                    if ni != last:
                        opts.append(ni)
            ni = rng.choice(opts)
            board[blank], board[ni] = board[ni], board[blank]
            last = blank
            blank = ni
        return {"board": board, "best": 0.0}

    def correct(self):
        b = self.state["board"]
        return sum(1 for i in range(15) if b[i] == i + 1)

    def progress(self):
        # every in-place tile moves the needle by 1/15 ≈ 6.667%
        return self.correct() / 15.0

    def build(self, parent):
        tk.Label(parent,
                 text="Slide the tiles back into order (1-15, gap last).\n"
                      "Click any tile next to the empty space.",
                 font=("Segoe UI", 10), bg=BG, fg=MUTED,
                 justify="center").pack(pady=(18, 12))
        frame = tk.Frame(parent, bg=BG); frame.pack()
        self.buttons = []
        for i in range(16):
            b = tk.Button(frame, text="", width=4, height=2,
                          font=("Consolas", 20, "bold"),
                          bg=CARD, fg=TXT, relief="flat",
                          activebackground=EDGE,
                          command=lambda i=i: self.click(i))
            b.grid(row=i // 4, column=i % 4, padx=3, pady=3)
            self.buttons.append(b)
        self.info = tk.Label(parent, text="", font=("Segoe UI", 11),
                             bg=BG, fg=BLUE)
        self.info.pack(pady=16)
        self.repaint()

    def repaint(self):
        b = self.state["board"]
        for i in range(16):
            v = b[i]
            if v == 0:
                self.buttons[i].config(text="", bg="#0a0a12", state="normal")
            else:
                self.buttons[i].config(text=str(v), state="normal",
                                       bg="#1f4436" if v == i + 1 else CARD,
                                       fg=GREEN if v == i + 1 else TXT)
        c = self.correct()
        self.info.config(text="%d / 15 tiles in place  —  %.3f%%"
                              % (c, c / 15.0 * 100.0))

    def click(self, i):
        b = self.state["board"]
        blank = b.index(0)
        br, bc = divmod(blank, 4)
        r, c = divmod(i, 4)
        if abs(br - r) + abs(bc - c) != 1:
            return
        b[blank], b[i] = b[i], b[blank]
        cur = self.correct() / 15.0
        if cur > self.state.get("best", 0.0):
            self.state["best"] = cur
        self.repaint()
        self.touch()


# ==========================================================================
#  10. MEMORY MATCH
# ==========================================================================
MEM_SYMBOLS = list("ABCDEFGHIJ")


class Memory(Puzzle):
    key = "memory"
    title = "Memory Match"

    def init_state(self):
        rng = random.Random()
        cards = MEM_SYMBOLS * 2
        rng.shuffle(cards)
        return {"cards": cards, "matched": []}

    def progress(self):
        # 20 cards — every matched card is worth 5%
        return len(self.state.get("matched", [])) / 20.0

    def build(self, parent):
        self.cards = self.state["cards"]
        self.matched = set(self.state.get("matched", []))
        self.flipped = []
        self.lock = False

        tk.Label(parent, text="Find all 10 matching pairs.",
                 font=("Segoe UI", 11), bg=BG, fg=MUTED).pack(pady=(18, 12))
        frame = tk.Frame(parent, bg=BG); frame.pack()
        self.buttons = []
        for i in range(20):
            b = tk.Button(frame, text="", width=4, height=2,
                          font=("Consolas", 20, "bold"),
                          bg=CARD, fg=TXT, relief="flat",
                          activebackground=EDGE,
                          command=lambda i=i: self.click(i))
            b.grid(row=i // 5, column=i % 5, padx=4, pady=4)
            self.buttons.append(b)
        self.info = tk.Label(parent, text="", font=("Segoe UI", 11),
                             bg=BG, fg=BLUE)
        self.info.pack(pady=16)
        self.repaint()

    def repaint(self):
        for i in range(20):
            if i in self.matched:
                self.buttons[i].config(text=self.cards[i], bg="#1f4436",
                                       fg=GREEN, state="disabled",
                                       disabledforeground=GREEN)
            elif i in self.flipped:
                self.buttons[i].config(text=self.cards[i], bg="#22223a",
                                       fg="#ffcc66", state="normal")
            else:
                self.buttons[i].config(text="?", bg=CARD, fg=MUTED,
                                       state="normal")
        self.info.config(text="%d / 20 cards matched  —  %.3f%%"
                              % (len(self.matched),
                                 len(self.matched) / 20.0 * 100.0))

    def click(self, i):
        if self.lock or i in self.matched or i in self.flipped:
            return
        self.flipped.append(i)
        self.repaint()
        if len(self.flipped) == 2:
            a, b = self.flipped
            if self.cards[a] == self.cards[b]:
                self.matched.add(a); self.matched.add(b)
                self.state["matched"] = sorted(self.matched)
                self.flipped = []
                self.repaint()
                self.touch()
            else:
                self.lock = True
                self.win.after(700, self.unflip)

    def unflip(self):
        self.flipped = []
        self.lock = False
        try: self.repaint()
        except Exception: pass


# ==========================================================================
#  APPLICATION
# ==========================================================================
class App:
    def __init__(self, root):
        self.root = root
        root.title("The 10-Puzzle Challenge")
        root.geometry("1180x820")
        root.configure(bg=BG)
        root.minsize(1040, 740)

        self.data = load_data()

        self.puzzles = [
            WordSearch(self), Crossword(self), Sudoku(self), Quiz(self),
            Anagram(self), Sequence(self), Cipher(self), Riddle(self),
            Slide(self), Memory(self),
        ]

        self.build_ui()
        self.update_progress()
        root.protocol("WM_DELETE_WINDOW", self.quit)

    # ------------------------------------------------------------------
    def save(self):
        store_data(self.data)

    def quit(self):
        self.save()
        self.root.destroy()

    # ------------------------------------------------------------------
    def build_ui(self):
        bottom = tk.Frame(self.root, bg="#181824")
        bottom.pack(side="bottom", fill="x")

        self.status = tk.Label(bottom, text="", font=("Segoe UI", 13, "bold"),
                               bg="#181824", fg=TXT)
        self.status.pack(pady=(10, 4))

        self.overall_bar = FineBar(bottom, height=26, show_ticks=True)
        self.overall_bar.pack(fill="x", padx=24, pady=(0, 14))

        header = tk.Frame(self.root, bg=BG)
        header.pack(fill="x", pady=(16, 6))
        tk.Label(header, text="THE 10-PUZZLE CHALLENGE",
                 font=("Segoe UI", 21, "bold"), bg=BG, fg=TXT).pack()
        tk.Label(header,
                 text="Progress is tracked down to every letter  •  "
                      "saves automatically",
                 font=("Segoe UI", 10), bg=BG, fg=MUTED).pack(pady=(2, 0))

        grid = tk.Frame(self.root, bg=BG)
        grid.pack(fill="both", expand=True, padx=18, pady=12)
        for i in range(5):
            grid.columnconfigure(i, weight=1)
        for i in range(2):
            grid.rowconfigure(i, weight=1)

        self.tiles = []
        for i, p in enumerate(self.puzzles):
            f = tk.Frame(grid, bg=CARD, highlightthickness=1,
                         highlightbackground=EDGE)
            f.grid(row=i // 5, column=i % 5, padx=8, pady=8, sticky="nsew")
            f.grid_propagate(False)

            num = tk.Label(f, text="%02d" % (i + 1),
                           font=("Consolas", 10, "bold"), bg=CARD, fg="#3d5a80")
            num.pack(anchor="nw", padx=10, pady=(8, 0))

            nm = tk.Label(f, text=p.title, font=("Segoe UI", 12, "bold"),
                          bg=CARD, fg=TXT, wraplength=180)
            nm.pack(pady=(2, 0))

            pct = tk.Label(f, text="0.000%", font=("Consolas", 15, "bold"),
                           bg=CARD, fg=BLUE)
            pct.pack(pady=(6, 2))

            bar = FineBar(f, height=12, show_ticks=False)
            bar.pack(pady=4, padx=10, fill="x")

            st = tk.Label(f, text="not started", font=("Segoe UI", 8),
                          bg=CARD, fg=MUTED)
            st.pack()

            for w in (f, num, nm, pct, st, bar):
                w.bind("<Button-1>", lambda e, p=p: p.open())
                try: w.config(cursor="hand2")
                except Exception: pass

            self.tiles.append((f, num, nm, pct, bar, st))

    # ------------------------------------------------------------------
    def update_progress(self):
        total = 0.0
        done = 0
        for i, p in enumerate(self.puzzles):
            try:
                pr = max(0.0, min(1.0, p.progress()))
            except Exception:
                pr = 0.0
            total += pr

            f, num, nm, pct, bar, st = self.tiles[i]
            bar.set(pr * 100.0)
            pct.config(text="%.3f%%" % (pr * 100.0))

            if pr >= 0.99999:
                done += 1
                nm.config(text=p.title, fg=GREEN)
                pct.config(fg=GREEN)
                st.config(text="COMPLETE", fg=GREEN)
                bg = CARD_D
            else:
                nm.config(text=p.title, fg=TXT)
                pct.config(fg=BLUE)
                st.config(text="in progress" if pr > 0 else "not started",
                          fg=MUTED)
                bg = CARD

            for w in (f, num, nm, pct, st):
                w.config(bg=bg)

        overall = total / len(self.puzzles) * 100.0
        self.overall_bar.set(overall)
        self.status.config(
            text="TOTAL PROGRESS  %.3f%%        %d / 10 puzzles complete"
                 % (overall, done))

        if done == len(self.puzzles):
            self.status.config(text="ALL 10 PUZZLES COMPLETE  •  100.000%")
            self.overall_bar.set(100.0)


# ==========================================================================
def main():
    root = tk.Tk()
    App(root)
    root.mainloop()


if __name__ == "__main__":
    main()