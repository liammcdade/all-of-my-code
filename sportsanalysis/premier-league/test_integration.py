#!/usr/bin/env python3
"""
match_video.py — fast build (with progress) — Chatterbox TTS
------------------------------------------------------------
Pipeline
  1. Parse text dump -> Match / Elo data
  2. PIL slide images (1920x1080)
  3. Chatterbox TTS (neural, high-quality) — serial generation, one model load
  4. Bake caption into base image per chunk -> static ImageClips
  5. concatenate_videoclips(method="chain") + one concatenated audio track
  6. Encode with ultrafast preset, fps=15, multithreaded x264
"""

from __future__ import annotations

import math
import os
import re
import shutil
import subprocess
import wave
from dataclasses import dataclass, field
from typing import List, Optional, Tuple

import numpy as np
import torch
import torchaudio as ta
from PIL import Image, ImageDraw, ImageFont

from chatterbox.tts import ChatterboxTTS

from moviepy import (
    AudioFileClip,
    ImageClip,
    concatenate_audioclips,
    concatenate_videoclips,
)

try:
    from tqdm import tqdm
    _HAS_TQDM = True
except ImportError:
    _HAS_TQDM = False

# ----------------------------------------------------------------------
# CONFIG
# ----------------------------------------------------------------------
W, H          = 1920, 1080
FPS           = 15                   # static content, no visual cost
SOURCE_FILE   = r"C:\Users\liam\Documents\GitHub\all-of-my-code\sportsanalysis\premier-league\pl_predictions.txt"
BUILD_DIR     = "build"
AUDIO_DIR     = os.path.join(BUILD_DIR, "audio")
OUTPUT_FILE   = "match_predictions.mp4"
CAPTION_Y     = 962
CAPTION_SIZE  = 40
CAPTION_MAX_W = 1500
SAVE_SLIDE_PNGS = False              # debug only

# Chatterbox device: use CUDA when available, otherwise CPU
TTS_DEVICE = "cuda" if torch.cuda.is_available() else "cpu"

# Palette
BG       = (10, 14, 22)
PANEL    = (22, 29, 43)
PANEL_2  = (30, 39, 56)
FG       = (237, 242, 250)
MUTED    = (138, 155, 178)
DIM      = (90, 104, 124)
HOME_C   = (0, 200, 120)
DRAW_C   = (226, 188, 60)
AWAY_C   = (64, 146, 255)
ACCENT   = (255, 92, 60)
LINE     = (44, 56, 76)


# ----------------------------------------------------------------------
# FONTS / TEXT
# ----------------------------------------------------------------------
_FONT_CACHE: dict = {}


def _font_path(bold: bool) -> Optional[str]:
    name = "DejaVuSans-Bold.ttf" if bold else "DejaVuSans.ttf"
    for c in (
        f"/usr/share/fonts/truetype/dejavu/{name}",
        f"/usr/share/fonts/dejavu/{name}",
        f"/usr/local/share/fonts/{name}",
        f"/Library/Fonts/{name}",
        f"/System/Library/Fonts/Supplemental/{name}",
        "C:/Windows/Fonts/arialbd.ttf" if bold else "C:/Windows/Fonts/arial.ttf",
        "C:/Windows/Fonts/segoeuib.ttf" if bold else "C:/Windows/Fonts/segoeui.ttf",
    ):
        if os.path.exists(c):
            return c
    return None


def font(size: int, bold: bool = False) -> ImageFont.FreeTypeFont:
    key = (size, bold)
    if key in _FONT_CACHE:
        return _FONT_CACHE[key]
    path = _font_path(bold)
    f = ImageFont.truetype(path, size) if path else ImageFont.load_default()
    _FONT_CACHE[key] = f
    return f


def text_w(draw, s, f) -> float:
    try:
        return draw.textlength(s, font=f)
    except Exception:
        return draw.textsize(s, font=f)[0]


def wrap(draw, text, f, max_w) -> List[str]:
    words, lines, cur = text.split(), [], ""
    for w in words:
        test = (cur + " " + w).strip()
        if text_w(draw, test, f) <= max_w or not cur:
            cur = test
        else:
            lines.append(cur)
            cur = w
    if cur:
        lines.append(cur)
    return lines


# ----------------------------------------------------------------------
# DATA MODEL
# ----------------------------------------------------------------------
@dataclass
class Record:
    w: int; d: int; l: int
    total: int
    wp: float; dp: float; lp: float


@dataclass
class FormRow:
    date: str; result: str; score: str; opponent: str


@dataclass
class Match:
    home: str; away: str
    home_rec: Optional[Record] = None
    away_rec: Optional[Record] = None
    h2h_n: int = 0
    h2h_home_w: int = 0; h2h_home_p: float = 0.0
    h2h_draws: int = 0;  h2h_draw_p: float = 0.0
    h2h_away_w: int = 0; h2h_away_p: float = 0.0
    home_last5: List[FormRow] = field(default_factory=list)
    away_last5: List[FormRow] = field(default_factory=list)
    elo_h: int = 1500; elo_a: int = 1500
    xg_h: float = 0.0; xg_a: float = 0.0
    p_h: float = 0.0; p_d: float = 0.0; p_a: float = 0.0

    @property
    def delta(self) -> int:
        return self.elo_h - self.elo_a


# ----------------------------------------------------------------------
# PARSER
# ----------------------------------------------------------------------
REC_RE = re.compile(
    r"([^\n]+?) — (?:HOME|AWAY) record since 2000\n"
    r"\s+(\d+)W (\d+)D (\d+)L\s+\((\d+) matches\)\s+→ "
    r"W ([\d.]+)% \| D ([\d.]+)% \| L ([\d.]+)%"
)
H2H_RE = re.compile(
    r"HEAD-TO-HEAD since 2000: (\d+) matches\n"
    r"\s+(.+?): (\d+)W \(([\d.]+)%\)\s+"
    r"Draws: (\d+) \(([\d.]+)%\)\s+"
    r"(.+?): (\d+)W \(([\d.]+)%\)"
)
FORM_RE = re.compile(
    r"([^\n]+?) — last 5\n"
    r"((?:\s+\d{4}-\d{2}-\d{2}\s+[WDL]\s+[\d.]+-[\d.]+\s+vs\s+.+\n){5})"
)
FORM_ROW_RE = re.compile(r"(\d{4}-\d{2}-\d{2})\s+([WDL])\s+([\d.]+-[\d.]+)\s+vs\s+(.+)")
ELO_RE = re.compile(r"Elo:\s+(.+?)=(\d+)\s+(.+?)=(\d+)\s+\(Δ=([+-]?\d+)\)")
XG_RE  = re.compile(r"xG goals:\s+(.+?)\s+([\d.]+)\s+–\s+([\d.]+)\s+(.+)")
PROB_RE = re.compile(
    r"P\(home\):\s+([\d.]+)%\n\s+P\(draw\):\s+([\d.]+)%\n\s+P\(away\):\s+([\d.]+)%"
)
ELO_LIST_RE = re.compile(r"^\s{2}(.+?)\s{2,}(\d{3,4}\.\d)\s*$", re.M)


def parse_matches(text: str) -> List[Match]:
    parts = re.split(r"={20,}\n\s*(.+?)\s+vs\s+(.+?)\s*\n={20,}", text)
    out: List[Match] = []
    for i in range(1, len(parts) - 2, 3):
        home, away, body = parts[i].strip(), parts[i + 1].strip(), parts[i + 2]
        m = Match(home=home, away=away)
        for name, w, d, l, tot, wp, dp, lp in REC_RE.findall(body):
            r = Record(int(w), int(d), int(l), int(tot), float(wp), float(dp), float(lp))
            if name.strip() == home:
                m.home_rec = r
            elif name.strip() == away:
                m.away_rec = r
        h = H2H_RE.search(body)
        if h:
            m.h2h_n       = int(h.group(1))
            m.h2h_home_w  = int(h.group(3)); m.h2h_home_p = float(h.group(4))
            m.h2h_draws   = int(h.group(5)); m.h2h_draw_p = float(h.group(6))
            m.h2h_away_w  = int(h.group(8)); m.h2h_away_p = float(h.group(9))
        for name, block in FORM_RE.findall(body):
            rows = [FormRow(*r) for r in FORM_ROW_RE.findall(block)]
            if name.strip() == home:
                m.home_last5 = rows
            elif name.strip() == away:
                m.away_last5 = rows
        e = ELO_RE.search(body)
        if e:
            m.elo_h, m.elo_a = int(e.group(2)), int(e.group(4))
        x = XG_RE.search(body)
        if x:
            m.xg_h, m.xg_a = float(x.group(2)), float(x.group(3))
        p = PROB_RE.search(body)
        if p:
            m.p_h, m.p_d, m.p_a = float(p.group(1)), float(p.group(2)), float(p.group(3))
        out.append(m)
    return out


def parse_elo_table(text: str) -> List[Tuple[str, float]]:
    start = text.find("ELO RATINGS – ALL TEAMS")
    end   = text.find("Calibrating xG goal model")
    if start == -1 or end == -1:
        return []
    return [(n.strip(), float(v)) for n, v in ELO_LIST_RE.findall(text[start:end])]


# ----------------------------------------------------------------------
# SLIDE RENDERING
# ----------------------------------------------------------------------
def new_canvas():
    img = Image.new("RGB", (W, H), BG)
    d = ImageDraw.Draw(img)
    d.rectangle([0, 0, W, 96], fill=PANEL)
    d.line([(0, 96), (W, 96)], fill=LINE, width=2)
    return img, d


def draw_centered(d, y, s, f, fill=FG):
    w = text_w(d, s, f)
    d.text(((W - w) / 2, y), s, font=f, fill=fill)


def draw_pill(d, x, y, text, f, fg, bg):
    pad_x, pad_y = 18, 8
    tw = text_w(d, text, f)
    th = f.size + pad_y * 2
    d.rounded_rectangle([x, y, x + tw + pad_x * 2, y + th], radius=th // 2, fill=bg)
    d.text((x + pad_x, y + pad_y - 2), text, font=f, fill=fg)
    return tw + pad_x * 2, th


def draw_prob_bar(d, x, y, w, h, ph, pd, pa):
    cx = x
    for frac, col in ((ph, HOME_C), (pd, DRAW_C), (pa, AWAY_C)):
        seg_w = w * frac / 100.0
        d.rectangle([cx, y, cx + seg_w, y + h], fill=col)
        cx += seg_w
    d.rounded_rectangle([x, y, x + w, y + h], radius=h // 2, outline=BG, width=3)


def slide_title():
    img, d = new_canvas()
    d.rectangle([0, 96, W, H], fill=BG)
    draw_centered(d, 300, "PREMIER LEAGUE", font(56, True), MUTED)
    draw_centered(d, 380, "MATCH PREDICTIONS", font(132, True), FG)
    draw_centered(d, 560, "Elo + Poisson xG model", font(52), HOME_C)
    draw_centered(d, 660, "10 fixtures  •  model probabilities  •  form & head-to-head",
                  font(36), MUTED)
    draw_centered(d, 800, "2000-08-19  →  2026-11-02   •   8,830 matches",
                  font(30), DIM)
    narr = ("Welcome to the Premier League match prediction show. "
            "We are using an Elo rating system blended with a Poisson expected-goals "
            "model, trained on over eight thousand eight hundred matches. "
            "Ten fixtures coming up.")
    return img, narr


def slide_baselines():
    img, d = new_canvas()
    draw_centered(d, 150, "HISTORICAL BASELINES", font(64, True), FG)
    draw_centered(d, 240, "What the average match looks like since 2000", font(34), MUTED)
    cards = [("HOME WIN", "45.6%", HOME_C), ("DRAW", "24.7%", DRAW_C), ("AWAY WIN", "29.7%", AWAY_C)]
    cw, gap = 460, 50
    x0 = (W - (cw * 3 + gap * 2)) / 2
    for i, (label, val, col) in enumerate(cards):
        x = x0 + i * (cw + gap)
        d.rounded_rectangle([x, 340, x + cw, 620], radius=26, fill=PANEL)
        d.rectangle([x, 340, x + cw, 348], fill=col)
        lw = text_w(d, label, font(34, True))
        d.text((x + (cw - lw) / 2, 380), label, font=font(34, True), fill=MUTED)
        vw = text_w(d, val, font(120, True))
        d.text((x + (cw - vw) / 2, 450), val, font=font(120, True), fill=col)
    draw_centered(d, 700, "AVERAGE GOALS PER MATCH", font(36, True), FG)
    d.rounded_rectangle([360, 770, 1560, 900], radius=20, fill=PANEL)
    draw_pill(d, 420, 805, "HOME  1.54", font(38, True), BG, HOME_C)
    draw_pill(d, 860, 805, "AWAY  1.19", font(38, True), BG, AWAY_C)
    narr = ("Across the full dataset the home side wins forty-five point six percent "
            "of matches, twenty-four point seven percent are draws, and the away "
            "side wins twenty-nine point seven percent. "
            "Average goals per match: one point five four for the home team, "
            "and one point one nine for the away team.")
    return img, narr


def slide_elo_chunk(rows, start_rank, total):
    img, d = new_canvas()
    draw_centered(d, 130, "ELO RATINGS", font(64, True), FG)
    draw_centered(d, 215, f"Ranks {start_rank}–{start_rank + len(rows) - 1} of {total}",
                  font(34), MUTED)
    col_x = [220, 1080]; col_w = 760
    per_col = math.ceil(len(rows) / 2); row_h = 46; y0 = 300
    for i, (name, elo) in enumerate(rows):
        col, idx = divmod(i, per_col)
        rank = start_rank + i
        x = col_x[col]; y = y0 + idx * row_h
        if idx % 2 == 0:
            d.rounded_rectangle([x - 14, y - 6, x + col_w, y + row_h - 10], radius=8, fill=PANEL)
        d.text((x, y), f"{rank:>3}", font=font(26, True), fill=DIM)
        d.text((x + 70, y), name[:34], font=font(30, True), fill=FG)
        ew = text_w(d, f"{elo:.1f}", font(30, True))
        d.text((x + col_w - ew - 14, y), f"{elo:.1f}", font=font(30, True), fill=HOME_C)
    top = rows[0]
    narr = (f"Current Elo ratings, ranks {start_rank} to {start_rank + len(rows) - 1}. "
            f"Leading this block: {top[0]} on {top[1]:.0f}.")
    if start_rank == 1:
        narr = ("Here is the Elo table. " + narr +
                " Arsenal and Manchester City sit well clear at the top, "
                "with Liverpool and Brighton next.")
    return img, narr


RES_COLOR = {"W": HOME_C, "D": DRAW_C, "L": AWAY_C}


def _draw_form_row(d, x, y, row, col):
    d.rounded_rectangle([x, y, x + 46, y + 46], radius=10, fill=col)
    lw = text_w(d, row.result, font(28, True))
    d.text((x + (46 - lw) / 2, y + 6), row.result, font=font(28, True), fill=BG)
    d.text((x + 62, y + 4), row.opponent[:24], font=font(24), fill=FG)
    d.text((x + 62, y + 32), f"{row.date}   {row.score}", font=font(19), fill=MUTED)


def slide_match(m, idx, total):
    img, d = new_canvas()
    d.text((44, 28), "MATCH PREDICTIONS", font=font(30, True), fill=MUTED)
    tag = f"{idx:02d} / {total:02d}"
    tw = text_w(d, tag, font(30, True))
    d.text((W - 44 - tw, 28), tag, font=font(30, True), fill=HOME_C)
    draw_centered(d, 130, m.home, font(76, True), FG)
    draw_centered(d, 218, "vs", font(38, True), DIM)
    draw_centered(d, 265, m.away, font(76, True), FG)
    col_x = [70, 990]; col_w = 860; y = 400
    for side, (name, rec, form) in enumerate(
        [(m.home, m.home_rec, m.home_last5), (m.away, m.away_rec, m.away_last5)]
    ):
        x = col_x[side]
        d.rounded_rectangle([x, y - 20, x + col_w, y + 470], radius=22, fill=PANEL)
        label = "HOME" if side == 0 else "AWAY"
        d.text((x + 26, y), f"{label}  •  {name[:26]}", font=font(26, True), fill=MUTED)
        if rec:
            d.text((x + 26, y + 42), f"{rec.w}W {rec.d}D {rec.l}L  ({rec.total})",
                   font=font(32, True), fill=FG)
            d.text((x + 26, y + 86),
                   f"W {rec.wp:.1f}%   D {rec.dp:.1f}%   L {rec.lp:.1f}%",
                   font=font(24), fill=MUTED)
        d.text((x + 26, y + 140), "LAST 5", font=font(22, True), fill=DIM)
        for j, row in enumerate(form):
            _draw_form_row(d, x + 26, y + 175 + j * 56, row, RES_COLOR.get(row.result, DIM))
    py = 900
    d.rounded_rectangle([70, py - 60, W - 70, py + 60], radius=22, fill=PANEL_2)
    d.text((100, py - 42), f"ELO  {m.elo_h}  vs  {m.elo_a}   ({m.delta:+d})",
           font=font(28, True), fill=FG)
    xg_txt = f"xG  {m.xg_h:.2f}  –  {m.xg_a:.2f}"
    xgw = text_w(d, xg_txt, font(28, True))
    d.text((W - 100 - xgw, py - 42), xg_txt, font=font(28, True), fill=FG)
    bar_x, bar_w, bar_h = 100, W - 200, 26
    draw_prob_bar(d, bar_x, py + 4, bar_w, bar_h, m.p_h, m.p_d, m.p_a)
    for txt, col, xpos in [
        (f"HOME {m.p_h:.1f}%", HOME_C, bar_x),
        (f"DRAW {m.p_d:.1f}%", DRAW_C, bar_x + bar_w * m.p_h / 100 - 60),
        (f"AWAY {m.p_a:.1f}%", AWAY_C, bar_x + bar_w - 130),
    ]:
        d.text((xpos, py + 38), txt, font=font(24, True), fill=col)
    def form_words(rows):
        if not rows:
            return "no recent form on record"
        mp_ = {"W": "win", "D": "draw", "L": "loss"}
        return ", ".join(mp_[r.result] for r in rows)
    narr = (
        f"{m.home} versus {m.away}. "
        f"{m.home} sit on {m.elo_h} Elo, {m.away} on {m.elo_a}, gap of {abs(m.delta)}. "
        f"Model expected goals: {m.xg_h:.2f} for {m.home}, {m.xg_a:.2f} for {m.away}. "
        f"Recent form, {m.home}: {form_words(m.home_last5)}. "
        f"{m.away}: {form_words(m.away_last5)}. "
        f"The model gives {m.home} {m.p_h:.1f} percent, "
        f"the draw {m.p_d:.1f} percent, and {m.away} {m.p_a:.1f} percent."
    )
    return img, narr


def slide_summary(matches):
    img, d = new_canvas()
    draw_centered(d, 70, "PREDICTION SUMMARY", font(56, True), FG)
    draw_centered(d, 145, "All ten fixtures", font(30), MUTED)
    headers = ["FIXTURE", "ELO", "xG", "HOME", "DRAW", "AWAY"]
    xs = [70, 900, 1090, 1310, 1500, 1690]
    y = 220
    for h, x in zip(headers, xs):
        d.text((x, y), h, font=font(24, True), fill=DIM)
    y += 44
    for i, m in enumerate(matches):
        if i % 2 == 0:
            d.rounded_rectangle([50, y - 6, W - 50, y + 44], radius=8, fill=PANEL)
        d.text((xs[0], y), f"{m.home[:22]}  v  {m.away[:22]}", font=font(24, True), fill=FG)
        d.text((xs[1], y), f"{m.elo_h}–{m.elo_a}", font=font(22), fill=MUTED)
        d.text((xs[2], y), f"{m.xg_h:.2f}–{m.xg_a:.2f}", font=font(22), fill=MUTED)
        d.text((xs[3], y), f"{m.p_h:.1f}%", font=font(22, True), fill=HOME_C)
        d.text((xs[4], y), f"{m.p_d:.1f}%", font=font(22, True), fill=DRAW_C)
        d.text((xs[5], y), f"{m.p_a:.1f}%", font=font(22, True), fill=AWAY_C)
        y += 50
    strongest = max(matches, key=lambda m: max(m.p_h, m.p_a))
    pick = strongest.home if strongest.p_h > strongest.p_a else strongest.away
    narr = ("And there is the full summary. "
            f"The most one-sided call of the round is {pick} — "
            "the model gives them the largest win probability on the card. "
            "That's it for this round — thanks for watching.")
    return img, narr


# ----------------------------------------------------------------------
# CAPTIONS
# ----------------------------------------------------------------------
def chunk_text(text: str, max_chars: int = 46) -> List[str]:
    words, chunks, cur = text.split(), [], ""
    for w in words:
        test = (cur + " " + w).strip()
        if len(test) > max_chars and cur:
            chunks.append(cur); cur = w
        else:
            cur = test
    if cur:
        chunks.append(cur)
    return chunks


def render_caption(text: str) -> Image.Image:
    f = font(CAPTION_SIZE, bold=True)
    probe = ImageDraw.Draw(Image.new("RGBA", (1, 1)))
    lines = wrap(probe, text, f, CAPTION_MAX_W)
    lh = int(CAPTION_SIZE * 1.32)
    tw = max(int(text_w(probe, l, f)) for l in lines)
    pad_x, pad_y = 26, 16
    img = Image.new("RGBA", (tw + pad_x * 2, lh * len(lines) + pad_y * 2), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)
    d.rounded_rectangle([0, 0, img.width - 1, img.height - 1],
                        radius=18, fill=(0, 0, 0, 175))
    y = pad_y
    for l in lines:
        lw = text_w(d, l, f)
        d.text(((img.width - lw) / 2, y), l, font=f, fill=(255, 255, 255, 255))
        y += lh
    return img


def bake_caption(base: Image.Image, caption: Image.Image, y: int) -> np.ndarray:
    """Composite a caption onto a copy of base; return RGB numpy array."""
    canvas = base.copy()
    cx = max(0, (canvas.width - caption.width) // 2)
    y  = min(y, canvas.height - caption.height)
    canvas.paste(caption, (cx, y), caption)
    return np.array(canvas)


# ----------------------------------------------------------------------
# TTS — Chatterbox (replaces espeak-ng / pyttsx3)
# ----------------------------------------------------------------------
def _chatterbox_synth(
    text: str,
    out_path: str,
    model: ChatterboxTTS,
) -> bool:
    """
    Generate speech with Chatterbox and save to WAV.
    Returns True on success.
    """
    try:
        wav = model.generate(text)
        ta.save(out_path, wav, model.sr)
        return os.path.exists(out_path) and os.path.getsize(out_path) > 4000
    except Exception as e:
        print(f"   ! Chatterbox failed: {e}")
        return False


def _silent_wav(path: str, seconds: float) -> None:
    """Fallback: generate silence of the estimated duration."""
    rate = 22050
    with wave.open(path, "wb") as w:
        w.setnchannels(1); w.setsampwidth(2); w.setframerate(rate)
        w.writeframes(b"\x00\x00" * int(rate * seconds))


def _synth_one(args: Tuple[int, str, str], model: ChatterboxTTS) -> Tuple[int, str, bool]:
    """Synthesize a single slide with Chatterbox (serial-safe)."""
    idx, text, out_path = args
    if _chatterbox_synth(text, out_path, model):
        return idx, out_path, True
    # fallback: silence
    est = max(3.0, len(text.split()) / 2.6)
    _silent_wav(out_path, est)
    return idx, out_path, False


# ----------------------------------------------------------------------
# BUILD
# ----------------------------------------------------------------------
def main() -> None:
    os.makedirs(BUILD_DIR, exist_ok=True)
    os.makedirs(AUDIO_DIR, exist_ok=True)

    print("Reading source…")
    with open(SOURCE_FILE, "r", encoding="utf-8") as fh:
        text = fh.read()

    matches   = parse_matches(text)
    elo_table = parse_elo_table(text)
    print(f"   {len(matches)} matches, {len(elo_table)} Elo entries")

    # --- slide plan -----------------------------------------------------
    plan: List[Tuple[Image.Image, str, str]] = []
    plan.append((*slide_title(), "title"))
    plan.append((*slide_baselines(), "baselines"))
    CHUNK = 12
    for i in range(0, len(elo_table), CHUNK):
        plan.append((*slide_elo_chunk(elo_table[i:i + CHUNK], i + 1, len(elo_table)),
                     f"elo_{i}"))
    for i, m in enumerate(matches, start=1):
        plan.append((*slide_match(m, i, len(matches)), f"match_{i}"))
    plan.append((*slide_summary(matches), "summary"))
    print(f"Building {len(plan)} slides…")

    if SAVE_SLIDE_PNGS:
        os.makedirs(os.path.join(BUILD_DIR, "slides"), exist_ok=True)
        for i, (img, _, tag) in enumerate(plan, start=1):
            img.save(os.path.join(BUILD_DIR, "slides", f"{i:02d}_{tag}.png"))

    # --- Chatterbox TTS (serial) -----------------------------------------
    print(f"Loading Chatterbox on {TTS_DEVICE}…")
    tts_model = ChatterboxTTS.from_pretrained(device=TTS_DEVICE)

    print("Synthesising narration (Chatterbox, serial)…")
    jobs = [(i, narr, os.path.join(AUDIO_DIR, f"{i:02d}_{tag}.wav"))
            for i, (_, narr, tag) in enumerate(plan)]
    n_jobs = len(jobs)

    results: List[Tuple[int, str, bool]] = []
    it = jobs
    if _HAS_TQDM:
        it = tqdm(jobs, desc="   TTS", unit="slide")
    for j in it:
        results.append(_synth_one(j, tts_model))

    results.sort(key=lambda x: x[0])
    real = sum(1 for _, _, ok in results if ok)
    print(f"   {real}/{len(results)} real Chatterbox TTS, {len(results) - real} silent")

    # --- bake captions + build ImageClips -------------------------------
    print("Baking captions…")
    chunk_lists = [chunk_text(n) or [n] for _, n, _ in plan]
    total_caps  = sum(len(cl) for cl in chunk_lists)

    video_clips: List[ImageClip] = []
    audio_clips: List[AudioFileClip] = []
    done = 0

    cap_iter = range(len(plan))
    if _HAS_TQDM:
        cap_iter = tqdm(cap_iter, desc="   Captions", unit="slide")

    for i in cap_iter:
        img, _narr, _tag = plan[i]
        chunks = chunk_lists[i]
        _, wav_path, _ = results[i]
        audio = AudioFileClip(wav_path)
        dur = max(audio.duration, 2.0)
        audio_clips.append(audio)

        total = sum(len(c) for c in chunks)
        for c in chunks:
            cd = dur * len(c) / total
            cap = render_caption(c)
            arr = bake_caption(img, cap, CAPTION_Y)
            video_clips.append(ImageClip(arr).with_duration(cd))
            done += 1

    if not _HAS_TQDM:
        print(f"   {done}/{total_caps} chunks")
    else:
        print(f"   {len(video_clips)} caption chunks total")

    # --- concatenate (chain is much faster than compose) ----------------
    print("Concatenating…")
    video = concatenate_videoclips(video_clips, method="chain")

    # --- audio: normalise sample rates then concat ----------------------
    srs = {int(a.fps) for a in audio_clips}
    if len(srs) > 1:
        target = max(srs)
        audio_clips = [a if int(a.fps) == target else a.with_fps(target)
                       for a in audio_clips]
    total_audio = concatenate_audioclips(audio_clips)
    if total_audio.duration > video.duration:
        total_audio = total_audio.subclipped(0, video.duration)
    video = video.with_audio(total_audio)

    # --- encode (progress bar restored via logger="bar") ----------------
    print(f"Writing {OUTPUT_FILE}  ({video.duration:.1f}s @ {FPS}fps)…")
    video.write_videofile(
        OUTPUT_FILE,
        fps=FPS,
        codec="libx264",
        audio_codec="aac",
        threads=os.cpu_count() or 4,
        preset="ultrafast",
        logger="bar",
        ffmpeg_params=["-crf", "24"],
    )

    for c in video_clips:
        c.close()
    for a in audio_clips:
        a.close()
    video.close()
    total_audio.close()
    print("Done.")


if __name__ == "__main__":
    main()