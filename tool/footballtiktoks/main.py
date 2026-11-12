"""
England vs Croatia – Bright Elo Short.

Dual-Rating (Attack/Defence) Elo + MoV updates
  → Exponential λ (μ · exp(β·ΔElo))
  → Dixon-Coles τ correction
  → 8 bright slides, 90 seconds, ffmpeg-encoded MP4.
"""

import csv, math, os, subprocess, sys, time
from collections import defaultdict

try:
    from PIL import Image, ImageDraw, ImageFont
except ImportError:
    os.system(f"{sys.executable} -m pip install pillow --quiet")
    from PIL import Image, ImageDraw, ImageFont

# ============================================================
# CONFIG
# ============================================================
CSV_PATH = r"C:\Users\liam\Documents\GitHub\Footballdata\data\international\games\results.csv"
HOME     = "England"
AWAY     = "Croatia"
NEUTRAL  = True                       # True = neutral; False = England at home
FALLBACK = {"England": (2000, 2000, 2000),
            "Croatia": (1930, 1930, 1930)}   # (total, att, def)

# Model hyperparameters
BETA        = 0.0020        # Elo → log-goals sensitivity (0.0018–0.0022)
BASELINE_N  = 1.35          # neutral-venue goals per team
BASELINE_H  = 1.50          # home team
BASELINE_A  = 1.15          # away team
GAMMA_HOME  = 0.25          # log home boost
RHO         = -0.11         # Dixon-Coles correlation
SCALE_ATT   = 8.0           # attack Elo reaction per goal of over/under-perf
SCALE_DEF   = 8.0           # defence Elo reaction

# ============================================================
# BRIGHT THEME
# ============================================================
W, H = 720, 1280

BG        = (252, 250, 246)   # warm off-white background
CARD      = (240, 244, 252)   # soft ice-blue card fill
CARD_BDR  = (200, 208, 224)   # soft card border
WHITE     = (22, 28, 48)      # dark navy  → BODY TEXT on light bg
GREY      = (100, 108, 125)   # medium grey
DIM       = (155, 162, 178)   # light grey captions
GOLD      = (240, 140, 0)     # bright amber accent
GOLD_SOFT = (255, 224, 150)   # soft gold hero fill
BLACK     = (20, 26, 42)      # deepest text / outlines
RED_ENG   = (220, 25, 40)     # vivid England red
RED_CRO   = (235, 40, 50)     # vivid Croatia red
BLUE_CRO  = (30, 70, 180)     # deep Croatia blue stripe
CRO_BLUE  = (55, 90, 220)     # bright Croatia blue accent
GREEN_OK  = (20, 150, 80)     # attack rating green
TRACK     = (218, 224, 235)   # bar track
BORDER_DK = (110, 118, 138)   # bar outline
PURE_WHITE = (255, 255, 255)  # real white (inside flags)


# ============================================================
# PROGRESS BAR
# ============================================================
def progress_bar(i, total, start_time, width=40, prefix="Working"):
    elapsed = time.time() - start_time
    pct     = (i + 1) / total if total else 1.0
    fps     = (i + 1) / elapsed if elapsed else 0
    eta     = (total - (i + 1)) / fps if fps else 0
    filled  = int(width * pct)
    bar     = "█" * filled + "░" * (width - filled)
    def fmt(s):
        m, s = divmod(int(s), 60); return f"{m}:{s:02d}"
    print(f"\r  {prefix} [{bar}] {pct*100:5.1f}%  {i+1}/{total}  "
          f"{fps:5.1f}/s  ETA {fmt(eta)}", end="", flush=True)
    if i + 1 == total:
        print(f"\n  ✓ Done in {fmt(elapsed)}")


# ============================================================
# DUAL ELO
# ============================================================
def _k_factor(tournament):
    t = tournament.lower()
    if "world cup" in t and "qualif" not in t: return 60
    if any(x in t for x in ("euro", "copa", "afcon", "asian cup", "gold cup")) \
       and "qualif" not in t:                  return 50
    if "qualif" in t or "nations league" in t: return 40
    if "friendly" in t:                        return 20
    return 30


def calculate_elo(path):
    total = defaultdict(lambda: 1500.0)
    att   = defaultdict(lambda: 1500.0)
    dfn   = defaultdict(lambda: 1500.0)

    if not os.path.exists(path):
        print(f"⚠  CSV not found: {path} — using fallback")
        return {k: {"total": v[0], "att": v[1], "def": v[2]}
                for k, v in FALLBACK.items()}

    with open(path, encoding="utf-8-sig") as f:
        rows = list(csv.DictReader(f))
    print(f"  Loaded {len(rows):,} matches\n")
    start = time.time()

    for i, row in enumerate(rows):
        try:
            h, a    = row["home_team"].strip(), row["away_team"].strip()
            hs, as_ = int(row["home_score"]), int(row["away_score"])
            neutral = row.get("neutral", "FALSE").strip().upper() == "TRUE"
            tourn   = row.get("tournament", "Friendly")
        except (ValueError, KeyError, AttributeError, TypeError):
            progress_bar(i, len(rows), start, prefix="Parsing CSV")
            continue

        k  = _k_factor(tourn)
        ha = 0 if neutral else 100

        # ---- Total Elo (MoV) ----
        dr    = total[h] - total[a] - ha
        we    = 1.0 / (1.0 + 10.0 ** (-dr / 400.0))
        w     = 1.0 if hs > as_ else 0.5 if hs == as_ else 0.0
        gd    = abs(hs - as_)
        g     = 1.0 if gd <= 1 else 1.5 if gd == 2 else (11 + gd) / 8.0
        delta = k * g * (w - we)
        total[h] += delta
        total[a] -= delta

        # ---- Attack / Defence Elo ----
        gamma = 0.0 if neutral else GAMMA_HOME
        lam_h = BASELINE_N * math.exp(BETA * (att[h] - dfn[a]) + gamma)
        lam_a = BASELINE_N * math.exp(BETA * (att[a] - dfn[h]))

        att[h] += SCALE_ATT * g * (hs  - lam_h)
        att[a] += SCALE_ATT * g * (as_ - lam_a)
        dfn[h] += SCALE_DEF * g * (lam_a - as_)
        dfn[a] += SCALE_DEF * g * (lam_h - hs)

        progress_bar(i, len(rows), start, prefix="Parsing CSV")

    teams = set(total) | set(att) | set(dfn)
    return {t: {"total": total[t], "att": att[t], "def": dfn[t]} for t in teams}


# ============================================================
# DIXON-COLES POISSON
# ============================================================
def poisson_pmf(k, lam):
    if lam <= 0: return 1.0 if k == 0 else 0.0
    return math.exp(-lam) * lam ** k / math.factorial(k)


def dc_tau(x, y, lh, la, rho=RHO):
    if x == 0 and y == 0: return 1 - lh * la * rho
    if x == 0 and y == 1: return 1 + lh * rho
    if x == 1 and y == 0: return 1 + la * rho
    if x == 1 and y == 1: return 1 - rho
    return 1.0


def predict(path):
    elos = calculate_elo(path)
    e_h  = elos.get(HOME, {"total": FALLBACK[HOME][0],
                            "att":   FALLBACK[HOME][1],
                            "def":   FALLBACK[HOME][2]})
    e_a  = elos.get(AWAY, {"total": FALLBACK[AWAY][0],
                            "att":   FALLBACK[AWAY][1],
                            "def":   FALLBACK[AWAY][2]})

    gamma = 0.0 if NEUTRAL else GAMMA_HOME
    lam_h = BASELINE_N * math.exp(BETA * (e_h["att"] - e_a["def"]) + gamma)
    lam_a = BASELINE_N * math.exp(BETA * (e_a["att"] - e_h["def"]))

    raw = [(h, a, poisson_pmf(h, lam_h) * poisson_pmf(a, lam_a))
           for h in range(8) for a in range(8)]
    dc  = [(h, a, p * dc_tau(h, a, lam_h, lam_a)) for h, a, p in raw]
    tot = sum(p for _, _, p in dc)
    dc  = [(h, a, p / tot) for h, a, p in dc]
    ranked = sorted(dc, key=lambda x: -x[2])

    win_h = sum(p for h, a, p in dc if h > a)
    draw  = sum(p for h, a, p in dc if h == a)
    win_a = sum(p for h, a, p in dc if h < a)

    return {
        "elo_h": e_h, "elo_a": e_a,
        "gap": e_h["total"] - e_a["total"],
        "lam_h": lam_h, "lam_a": lam_a,
        "scores": ranked[:5],
        "win_h": win_h, "draw": draw, "win_a": win_a,
    }


# ============================================================
# FONTS
# ============================================================
_FONT_CACHE = {}
_BOLD = ["arialbd.ttf",
         "C:/Windows/Fonts/arialbd.ttf",
         "/System/Library/Fonts/Supplemental/Arial Bold.ttf",
         "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
         "DejaVuSans-Bold.ttf"]
_REG  = ["arial.ttf",
         "C:/Windows/Fonts/arial.ttf",
         "/System/Library/Fonts/Supplemental/Arial.ttf",
         "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
         "DejaVuSans.ttf"]

def get_font(size, bold=True):
    key = (size, bold)
    if key in _FONT_CACHE: return _FONT_CACHE[key]
    for c in (_BOLD if bold else _REG):
        try:
            f = ImageFont.truetype(c, size)
            _FONT_CACHE[key] = f
            return f
        except (IOError, OSError):
            continue
    f = ImageFont.load_default()
    _FONT_CACHE[key] = f
    return f


# ============================================================
# DRAW HELPERS
# ============================================================
def center_text(d, cx, y, text, font, fill):
    bbox = d.textbbox((0, 0), text, font=font)
    d.text((cx - (bbox[2] - bbox[0]) // 2, y), text, font=font, fill=fill)

def draw_flag_eng(d, x, y, w, h):
    d.rectangle([x, y, x + w, y + h], fill=PURE_WHITE)
    d.rectangle([x + w // 2 - w // 10, y, x + w // 2 + w // 10, y + h], fill=RED_ENG)
    d.rectangle([x, y + h // 2 - h // 10, x + w, y + h // 2 + h // 10], fill=RED_ENG)
    d.rectangle([x, y, x + w, y + h], outline=BLACK, width=3)

def draw_flag_cro(d, x, y, w, h):
    t = h // 3
    d.rectangle([x, y, x + w, y + t], fill=RED_CRO)
    d.rectangle([x, y + t, x + w, y + 2*t], fill=PURE_WHITE)
    d.rectangle([x, y + 2*t, x + w, y + h], fill=BLUE_CRO)
    sx, sy = x + w//2 - w//8, y + h//3 - h//12
    cw, ch = max(1, w//16), max(1, h//16)
    for i in range(4):
        for j in range(4):
            col = RED_CRO if (i + j) % 2 == 0 else PURE_WHITE
            d.rectangle([sx+i*cw, sy+j*ch, sx+(i+1)*cw, sy+(j+1)*ch], fill=col)
    d.rectangle([x, y, x + w, y + h], outline=BLACK, width=3)

def draw_hbar(d, x, y, w, h, pct, color, track=TRACK):
    d.rectangle([x, y, x + w, y + h], fill=track)
    if pct > 0:
        d.rectangle([x, y, x + int(w * pct), y + h], fill=color)


# ============================================================
# SLIDES
# ============================================================
def slide_title(p):
    img = Image.new("RGB", (W, H), BG); d = ImageDraw.Draw(img)
    # accent bars
    d.rectangle([0, 0, W, 16], fill=GOLD)
    d.rectangle([0, H - 16, W // 2, H], fill=RED_ENG)
    d.rectangle([W // 2, H - 16, W, H], fill=BLUE_CRO)

    center_text(d, W//2, 110, "DUAL-RATING ELO", get_font(30, False), GREY)
    center_text(d, W//2, 165, "PREDICTION",      get_font(56), GOLD)

    draw_flag_eng(d, W//2 - 90, 340, 180, 110)
    center_text(d, W//2, 480, HOME, get_font(56), WHITE)
    center_text(d, W//2, 575, "vs", get_font(48, False), GOLD)
    draw_flag_cro(d, W//2 - 90, 640, 180, 110)
    center_text(d, W//2, 780, AWAY, get_font(56), WHITE)

    center_text(d, W//2, 1010, "Attack + Defence Elo · Dixon-Coles",
                get_font(24, False), DIM)
    center_text(d, W//2, 1055, "Poisson · Margin-of-Victory updates",
                get_font(24, False), DIM)
    return img

def slide_dual_rating(p):
    img = Image.new("RGB", (W, H), BG); d = ImageDraw.Draw(img)
    center_text(d, W//2, 100, "DUAL RATINGS", get_font(52), GOLD)
    center_text(d, W//2, 170, "Attack Elo  ·  Defence Elo",
                get_font(24, False), GREY)

    eh, ea = p["elo_h"], p["elo_a"]
    for name, e, color, y in [(HOME, eh, RED_ENG, 260),
                              (AWAY, ea, CRO_BLUE, 660)]:
        center_text(d, W//2, y, name.upper(), get_font(34), WHITE)
        card_w = (W - 160) // 3
        cx0 = 80
        stats = [("TOTAL",   e["total"], color),
                 ("ATTACK",  e["att"],   GREEN_OK),
                 ("DEFENCE", e["def"],   GOLD)]
        for j, (lbl, val, c) in enumerate(stats):
            x = cx0 + j * card_w
            d.rectangle([x, y + 60, x + card_w - 10, y + 260],
                        fill=CARD, outline=CARD_BDR, width=2)
            center_text(d, x + (card_w - 10)//2, y + 75, lbl,
                        get_font(20, False), GREY)
            center_text(d, x + (card_w - 10)//2, y + 115,
                        f"{val:.0f}", get_font(56), c)
    return img

def slide_xg(p):
    img = Image.new("RGB", (W, H), BG); d = ImageDraw.Draw(img)
    center_text(d, W//2, 100, "EXPECTED GOALS", get_font(52), GOLD)
    center_text(d, W//2, 170, "λ = μ · exp(β·ΔElo)", get_font(26, False), GREY)

    # England card (soft red)
    d.rectangle([60, 260, W - 60, 500], fill=(255, 235, 235),
                outline=RED_ENG, width=5)
    center_text(d, W//2, 285, HOME.upper(), get_font(30), WHITE)
    center_text(d, W//2, 335, f"{p['lam_h']:.2f}", get_font(140), RED_ENG)

    # Croatia card (soft blue)
    d.rectangle([60, 560, W - 60, 800], fill=(235, 240, 255),
                outline=CRO_BLUE, width=5)
    center_text(d, W//2, 585, AWAY.upper(), get_font(30), WHITE)
    center_text(d, W//2, 635, f"{p['lam_a']:.2f}", get_font(140), CRO_BLUE)

    center_text(d, W//2, 870, "xG", get_font(36), GREY)
    center_text(d, W//2, 1000,
                f"β={BETA}   μ={BASELINE_N}   venue={'neutral' if NEUTRAL else 'home'}",
                get_font(22, False), DIM)
    center_text(d, W//2, 1050,
                "Attack A vs Defence B  |  Attack B vs Defence A",
                get_font(22, False), DIM)
    return img

def slide_most_likely(p):
    img = Image.new("RGB", (W, H), BG); d = ImageDraw.Draw(img)
    h, a, prob = p["scores"][0]
    center_text(d, W//2, 100, "MOST LIKELY SCORE", get_font(46), GOLD)
    center_text(d, W//2, 170, "Dixon-Coles adjusted", get_font(24, False), GREY)

    # amber hero card behind score
    d.rectangle([60, 320, W - 60, 760], fill=GOLD_SOFT, outline=GOLD, width=6)
    center_text(d, W//2, 360, f"{h}  –  {a}", get_font(230), WHITE)

    center_text(d, W//2, 810, f"{prob*100:.1f}%", get_font(130), GOLD)
    center_text(d, W//2, 965, "probability  (τ-corrected)",
                get_font(28, False), GREY)
    center_text(d, W//2, 1090, f"{HOME}  {h} – {a}  {AWAY}",
                get_font(34, False), WHITE)
    return img

def slide_top5(p):
    img = Image.new("RGB", (W, H), BG); d = ImageDraw.Draw(img)
    center_text(d, W//2, 100, "TOP 5 SCORELINES", get_font(46), GOLD)
    center_text(d, W//2, 170, "After Dixon-Coles τ correction",
                get_font(24, False), GREY)

    top = p["scores"]
    mx  = top[0][2] if top else 1
    y = 270
    for i, (h, a, prob) in enumerate(top):
        d.rectangle([40, y, W-40, y+140], fill=CARD,
                    outline=CARD_BDR, width=2)
        d.text((70, y + 12), f"#{i+1}", font=get_font(32), fill=GOLD)
        d.text((160, y + 18), f"{h} – {a}", font=get_font(48), fill=WHITE)
        pct  = f"{prob*100:.1f}%"
        bbox = d.textbbox((0, 0), pct, font=get_font(32))
        d.text((W - 70 - (bbox[2] - bbox[0]), y + 25), pct,
               font=get_font(32), fill=GOLD)
        draw_hbar(d, 70, y + 90, W - 140, 22, prob / mx, GOLD)
        y += 155
    return img

def slide_outcomes(p):
    img = Image.new("RGB", (W, H), BG); d = ImageDraw.Draw(img)
    center_text(d, W//2, 100, "MATCH OUTCOMES", get_font(46), GOLD)
    center_text(d, W//2, 170, "From 8×8 DC-adjusted grid",
                get_font(24, False), GREY)

    rows = [(f"{HOME} WIN", p["win_h"], RED_ENG, 300),
            ("DRAW",        p["draw"],  GOLD,    590),
            (f"{AWAY} WIN", p["win_a"], CRO_BLUE, 880)]
    for label, prob, color, y in rows:
        center_text(d, W//2, y,      label,              get_font(34), WHITE)
        center_text(d, W//2, y + 55, f"{prob*100:.1f}%", get_font(90), color)
        draw_hbar(d, 80, y + 165, W - 160, 32, prob, color)
        d.rectangle([80, y + 165, W - 80, y + 197],
                    outline=BORDER_DK, width=2)
    return img

def slide_model_notes(p):
    img = Image.new("RGB", (W, H), BG); d = ImageDraw.Draw(img)
    center_text(d, W//2, 100, "HOW IT WORKS", get_font(52), GOLD)
    bullets = [
        ("1", "Margin-of-Victory Elo",
              "K × G × (W − We)  ·  K 20–60 by tier"),
        ("2", "Dual Attack & Defence Elo",
              "attack ← goals vs exp  ·  def ← goals vs exp"),
        ("3", "Exponential λ",
              "λ = μ · exp(β·ΔElo)  ·  no negative goals"),
        ("4", "Dixon-Coles τ",
              "ρ = −0.11 boosts 0-0 / 1-1 draws"),
    ]
    y = 240
    for num, title, sub in bullets:
        d.rectangle([40, y, W - 40, y + 190], fill=CARD,
                    outline=CARD_BDR, width=2)
        d.ellipse([60, y + 60, 120, y + 120], fill=GOLD)
        center_text(d, 90, y + 68, num, get_font(40), PURE_WHITE)
        d.text((150, y + 30),  title, font=get_font(34), fill=WHITE)
        d.text((150, y + 100), sub,   font=get_font(22, False), fill=GREY)
        y += 205
    return img

def slide_outro(p):
    img = Image.new("RGB", (W, H), BG); d = ImageDraw.Draw(img)
    # accent bars
    d.rectangle([0, 0, W, 16], fill=GOLD)
    d.rectangle([0, H - 16, W // 2, H], fill=RED_ENG)
    d.rectangle([W // 2, H - 16, W, H], fill=BLUE_CRO)

    h, a, prob = p["scores"][0]
    center_text(d, W//2, 190, "FINAL PREDICTION", get_font(46), GOLD)
    center_text(d, W//2, 380, HOME, get_font(46), WHITE)

    # amber hero card
    d.rectangle([80, 440, W - 80, 660], fill=GOLD_SOFT,
                outline=GOLD, width=6)
    center_text(d, W//2, 470, f"{h} – {a}", get_font(180), WHITE)

    center_text(d, W//2, 690, AWAY, get_font(46), WHITE)
    gap = p["gap"]
    lines = [
        f"Total Elo gap : {gap:+.0f}",
        f"xG            : {p['lam_h']:.2f} – {p['lam_a']:.2f}",
        f"Confidence    : {prob*100:.1f}%   (DC-adjusted)",
    ]
    y = 860
    for t in lines:
        center_text(d, W//2, y, t, get_font(30, False), GREY)
        y += 55
    center_text(d, W//2, 1110,
                "Dual Elo  →  Exponential λ  →  Dixon-Coles",
                get_font(22, False), DIM)
    return img


# ============================================================
# COMPILE
# ============================================================
def compile_video(slides, output="england_croatia_prediction.mp4"):
    os.makedirs("slides", exist_ok=True)
    print()
    start = time.time()
    lines, last_path = [], ""
    for i, (img, dur) in enumerate(slides):
        last_path = os.path.abspath(f"slides/scene_{i:02d}.png")
        img.save(last_path)
        lines += [f"file '{last_path}'", f"duration {dur}"]
        progress_bar(i, len(slides), start, prefix="Rendering slides")
    lines.append(f"file '{last_path}'")

    concat = os.path.abspath("slides/concat.txt")
    with open(concat, "w") as f:
        f.write("\n".join(lines))

    out = os.path.abspath(output)
    cmd = ["ffmpeg", "-y", "-f", "concat", "-safe", "0",
           "-i", concat, "-vf", "fps=30,format=yuv420p",
           "-c:v", "libx264", out]
    print("\n  Encoding with ffmpeg…")
    t0 = time.time()
    r  = subprocess.run(cmd, capture_output=True, text=True)
    if r.returncode == 0 and os.path.exists(out):
        size_mb = os.path.getsize(out) / (1024 * 1024)
        dur = sum(s[1] for s in slides)
        print(f"  ✓ Encoded in {time.time()-t0:.1f}s")
        print(f"\n✓ Video saved: {out}  ({size_mb:.1f} MB, {dur}s)")
    else:
        print("✗ ffmpeg failed:\n", r.stderr[-1200:])


# ============================================================
# MAIN
# ============================================================
if __name__ == "__main__":
    print(f"CSV: {CSV_PATH}\n")
    if not os.path.exists(CSV_PATH):
        print(f"✗ CSV not found: {CSV_PATH}"); sys.exit(1)

    p = predict(CSV_PATH)

    print("\n" + "=" * 60)
    print(f"  {HOME}  vs  {AWAY}  ({'NEUTRAL' if NEUTRAL else 'HOME'} venue)")
    print("=" * 60)
    for label, e in [(HOME, p["elo_h"]), (AWAY, p["elo_a"])]:
        print(f"  {label:10s}  total {e['total']:6.0f}   "
              f"att {e['att']:6.0f}   def {e['def']:6.0f}")
    print(f"  Elo gap   : {p['gap']:+.0f}")
    print(f"  xG        : {p['lam_h']:.2f} – {p['lam_a']:.2f}")
    print(f"  Outcomes  : {HOME} {p['win_h']*100:.1f}%  |  "
          f"Draw {p['draw']*100:.1f}%  |  {AWAY} {p['win_a']*100:.1f}%")
    print("  Top 5 (DC-adjusted):")
    for i, (h, a, pr) in enumerate(p["scores"], 1):
        print(f"    {i}. {h}-{a}   {pr*100:5.2f}%")
    print("=" * 60)

    slides = [
        (slide_title(p),         5),
        (slide_dual_rating(p),  14),
        (slide_xg(p),           10),
        (slide_most_likely(p),  12),
        (slide_top5(p),         16),
        (slide_outcomes(p),     10),
        (slide_model_notes(p),  13),
        (slide_outro(p),        10),
    ]
    print(f"\n  Slides sum to {sum(s[1] for s in slides)}s")
    compile_video(slides)