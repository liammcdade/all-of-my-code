#!/usr/bin/env python3
"""
video.py - turn the one video in the tool folder into portrait (9:16) clips.

No cloud, no network - pure Python + ffmpeg + optional local LLM (Ollama).

Reads transcript from:  C:\\Users\\liam\\Documents\\GitHub\\all-of-my-code\\tool\\text.txt
Auto-detects the single video in:  C:\\Users\\liam\\Documents\\GitHub\\all-of-my-code\\tool\\
Writes clips to:        C:\\Users\\liam\\Documents\\GitHub\\all-of-my-code\\tool\\clips\\

Requires: ffmpeg/ffprobe on PATH, `pip install tqdm`
Optional: Ollama (https://ollama.com) for --llm scoring.

Examples
--------
# Top 6 highest-energy 25s+ clips (best 10 by default)
python video.py --hype --max-clips 6

# Every 25s+ chunk (override default min with --min-clip 0)
python video.py --all --min-clip 0

# Only chunks that mention a keyword, ranked by hype
python video.py --keywords "allstar,champion" --hype --max-clips 5

# Preview without encoding
python video.py --hype --max-clips 6 --dry-run

# Burn white-on-black subtitles, 4 words at a time
python video.py --hype --max-clips 6 --subtitles

# 3-word cards, bigger font
python video.py --all --subtitles --sub-words 3 --sub-font-size 96

# Use a local LLM to re-rank the top heuristic candidates
python video.py --hype --max-clips 6 --llm
python video.py --hype --max-clips 6 --llm --llm-model qwen2.5:7b
python video.py --hype --max-clips 6 --llm --llm-blend 0   # pure LLM ranking

# Fastest encode (larger files, ~5-10x faster than veryfast)
python video.py --hype --max-clips 6 --preset ultrafast
"""

import argparse
import array
import json
import math
import re
import shutil
import subprocess
import sys
import tempfile
import urllib.error
import urllib.request
from dataclasses import dataclass
from pathlib import Path
from typing import List, Optional, Tuple

try:
    from tqdm import tqdm
except ImportError:
    sys.exit("Missing dependency. Run: pip install tqdm")

try:
    import cv2
    import numpy as np
except ImportError:
    cv2 = None
    np = None


# ---------------------------- your paths -------------------------------------

TOOL_DIR   = Path(r"C:\Users\liam\Documents\GitHub\all-of-my-code\tool")
TRANSCRIPT = TOOL_DIR / "text.txt"
OUTPUT_DIR = TOOL_DIR / "clips"

VIDEO_EXTS = {".mp4", ".mov", ".mkv", ".avi", ".webm", ".m4v", ".flv", ".wmv", ".mpg", ".mpeg"}
TRANSCRIPT_EXTS = (".txt", ".srt", ".vtt", ".json")

# ----------------------------- transcript ------------------------------------

TS = r"\d{1,2}:\d{2}:\d{2}[.,]\d{1,3}|\d{1,2}:\d{2}[.,]\d{1,3}"
CUE_RE = re.compile(rf"({TS})\s*-->\s*({TS})")
BRACKET_RE = re.compile(r"^\[(\d{1,3}):(\d{2})(?::(\d{2}))?\]\s*(.*)$")


@dataclass
class Segment:
    start: float
    end: float
    text: str = ""
    hits: int = 0
    score: float = 0.0

    @property
    def dur(self) -> float:
        return max(0.0, self.end - self.start)


def parse_ts(value: str) -> float:
    value = value.strip().replace(",", ".")
    try:
        parts = [float(p) for p in value.split(":")]
    except ValueError:
        return 0.0
    while len(parts) < 3:
        parts.insert(0, 0.0)
    h, m, s = parts[-3:]
    return h * 3600 + m * 60 + s


def stamp(seconds: float) -> str:
    minutes, secs = divmod(int(round(seconds)), 60)
    return f"{minutes:02d}m{secs:02d}s"


def parse_json_transcript(raw: str) -> List[Segment]:
    data = json.loads(raw)
    if isinstance(data, dict):
        data = data.get("segments") or data.get("items") or data.get("transcript") or []
    out = []
    for item in data:
        start = item.get("start", item.get("start_time", item.get("from", 0)))
        end = item.get("end", item.get("end_time", item.get("to", 0)))
        text = item.get("text", item.get("content", "")) or ""
        if isinstance(start, str):
            start = parse_ts(start)
        if isinstance(end, str):
            end = parse_ts(end)
        out.append(Segment(float(start), float(end), text.strip()))
    return out


def parse_cue_transcript(raw: str) -> List[Segment]:
    segments, current = [], None
    for line in raw.splitlines():
        match = CUE_RE.search(line)
        if match:
            if current and current.text:
                segments.append(current)
            current = Segment(parse_ts(match.group(1)), parse_ts(match.group(2)))
            continue
        if current is None:
            continue
        text = line.strip()
        if text:
            current.text = f"{current.text} {text}".strip()
        elif current.text:
            segments.append(current)
            current = None
    if current and current.text:
        segments.append(current)
    return [s for s in segments if s.end > s.start]


def parse_bracket_transcript(raw: str, video_duration: Optional[float] = None) -> List[Segment]:
    """'[M:SS] some text' per line. Start-only stamps: end = next start."""
    entries = []
    for line in raw.splitlines():
        line = line.strip()
        if not line:
            continue
        match = BRACKET_RE.match(line)
        if match:
            a, b, c, text = match.groups()
            if c is not None:
                start = int(a) * 3600 + int(b) * 60 + int(c)
            else:
                start = int(a) * 60 + int(b)
            entries.append([start, text.strip()])
        elif entries:
            entries[-1][1] = f"{entries[-1][1]} {line}".strip()

    entries.sort(key=lambda e: e[0])
    dedup = []
    for start, text in entries:
        if dedup and start <= dedup[-1][0]:
            if text:
                dedup[-1][1] = f"{dedup[-1][1]} {text}".strip()
            continue
        dedup.append([start, text])

    segs = []
    for i, (start, text) in enumerate(dedup):
        if i + 1 < len(dedup):
            end = float(dedup[i + 1][0])
        else:
            end = float(video_duration) if video_duration else start + 8.0
        segs.append(Segment(float(start), end, text))
    return [s for s in segs if s.end > s.start]


def load_transcript(path: Path, video_duration: Optional[float] = None) -> List[Segment]:
    with open(path, encoding="utf-8-sig") as fh:
        raw = fh.read()

    probe = raw.lstrip("\ufeff \t\r\n")

    if path.suffix.lower() == ".json" or probe[:1] in "[{":
        try:
            segs = parse_json_transcript(raw)
            if segs:
                return [s for s in segs if s.end > s.start]
        except json.JSONDecodeError:
            pass

    if CUE_RE.search(raw):
        return parse_cue_transcript(raw)

    if re.search(r"^\s*\[\d{1,3}:\d{2}", raw, re.MULTILINE):
        return parse_bracket_transcript(raw, video_duration)

    head = probe[:120].replace("\n", "\\n").replace("\r", "")
    raise ValueError(
        "Unrecognised transcript format.\n"
        f"  File: {path}\n"
        f"  Starts with: {head!r}\n"
        "Expected SRT/VTT ('-->' arrows), JSON list, or '[M:SS] text' lines."
    )


# ------------------------------ chunking -------------------------------------

def chunk_by_duration(cues: List[Segment], min_len: float) -> List[Segment]:
    """Greedily close a chunk once it reaches min_len. Never emits undersized
    chunks (a short tail is merged into the previous chunk)."""
    if min_len <= 0:
        return list(cues)

    chunks: List[Segment] = []
    cur: Optional[Segment] = None

    for seg in cues:
        if cur is None:
            cur = Segment(seg.start, seg.end, seg.text)
        else:
            cur.end = max(cur.end, seg.end)
            cur.text = f"{cur.text} {seg.text}".strip()
        if cur.dur >= min_len:
            chunks.append(cur)
            cur = None

    if cur is not None:
        if chunks and cur.dur < min_len:
            chunks[-1].end = max(chunks[-1].end, cur.end)
            chunks[-1].text = f"{chunks[-1].text} {cur.text}".strip()
        else:
            chunks.append(cur)

    return chunks


# --------------------------- hype scoring ------------------------------------
#
# Regexes are precompiled once at import. Previously we compiled the pattern
# string inside _count_phrase on every call - on a 100-cue video with 20
# phrases that's ~1200 re.compile() calls that just hit re's internal cache.
# Precompiling avoids the lookup and the argument plumbing entirely.

# Whitelist of genuine reaction tags. Auto-transcript junk like
# [Music], [Applause], [Silence], [BLANK_AUDIO], [Inaudible], [Foreign],
# [Sound], [cough] is explicitly excluded - those are emitted constantly by
# Whisper and friends and would otherwise add +10 each.
_HYPE_TAGS = re.compile(
    r"\[(screaming|laughter|laughs|laugh|snorts|snort|"
    r"chuckles|chuckle|giggles|giggle|"
    r"scream|sigh|sighs|crying|shouting|cheering)\]",
    re.IGNORECASE,
)

# Phrases tiered by excitement strength: mild, medium, high.
_HYPE_PHRASES_MILD = [
    "no", "noo", "nooo", "yes", "yesss", "please", "damn",
    "stupid", "idiot", "cheat", "cheating",
    # NEW - podcast/banter
    "absolutely", "brilliant", "never", "what", "stop",
]
_HYPE_PHRASES_MEDIUM = [
    "please don't", "god damn", "god damn it", "are you ready",
    "watch this", "look at this", "here we go", "best out of",
    # NEW - podcast/banter
    "you're wrong", "no way", "shut up", "stop it", "get in",
    "i love it", "i love that", "that's amazing", "that's brilliant",
    "play the game", "paddle pals", "paddle guy", "paddle maniac",
    "biffing off golf",
]
_HYPE_PHRASES_HIGH = [
    "for god's sake", "champion", "oh my god", "are you kidding",
    "holy shit", "jesus christ",
    # NEW - transcript-specific punchlines
    "right in my face", "what a pig", "absolute pig",
    "i can't believe", "are you kidding me",
    "brains could come out", "we are related",
    "you're absolutely wrong",
]
_HYPE_PHRASE_RES = (
    [(re.compile(rf"\b{re.escape(p)}\b", re.IGNORECASE), 1.0) for p in _HYPE_PHRASES_MILD]
    + [(re.compile(rf"\b{re.escape(p)}\b", re.IGNORECASE), 2.0) for p in _HYPE_PHRASES_MEDIUM]
    + [(re.compile(rf"\b{re.escape(p)}\b", re.IGNORECASE), 3.5) for p in _HYPE_PHRASES_HIGH]
)

_HYPE_THEMATIC = [
    "goal", "score", "win", "won", "beat", "beating", "bot", "robot",
    "champion", "easy", "hard", "impossible",
]
_HYPE_THEMATIC_RES = [
    (re.compile(rf"\b{re.escape(w)}\b", re.IGNORECASE), 1.5) for w in _HYPE_THEMATIC
]

# Filler words that signal dead air / low energy - subtract from score.
_FILLER_RE = re.compile(
    r"\b(um+|uh+|like|you know|i mean|basically|literally|uh huh|yeah)\b",
    re.IGNORECASE,
)

# Repeated hype words: "no no no", "yesss yesss", etc. - strong excitement signal.
_REPEAT_RE = re.compile(
    r"\b(no+|ye+s+|stop|wait|go+|come on)\b(?:\s+\1\b){2,}",
    re.IGNORECASE,
)

# Uppercase shouting: words that are fully uppercase AND len >= 3.
_UPPER_WORD_RE = re.compile(r"\b[A-Z]{3,}\b")


def hype_score(seg: Segment, loudness_db: Optional[float] = None,
               audio_weight: float = 1.0,
               audio_zscore: Optional[float] = None) -> float:
    """Pure-heuristic 'exciting moment' score, normalised per minute.

    Each sub-feature is raw-accumulated then squashed through tanh so no
    single factor (tags, phrases, upper-case, wps, audio) can dominate.
    The sub-scores are weighted and summed into a [0, ~12] range, then
    length-normalised by 60s and optionally boosted/damped by audio.

    Parameters
    ----------
    loudness_db : optional RMS dB of the chunk (kept for backward compat;
        when audio_zscore is available it is preferred - see §6).
    audio_zscore : optional z-scored peak-RMS relative to all chunks.
        When provided, the audio multiplier uses a sigmoid transform of
        the z-score for real dynamic spread (§6).
    """
    t = seg.text

    # --- §1: tags with diminishing returns ---
    bare, tag_count = _HYPE_TAGS.subn("", t)
    if tag_count > 0:
        tag_pts = 10.0 * min(tag_count, 2) + 4.0 * max(0, tag_count - 2)
    else:
        tag_pts = 0.0

    # --- §5: tiered phrase weights ---
    phrase_pts = 0.0
    for rx, weight in _HYPE_PHRASE_RES:
        phrase_pts += len(rx.findall(t)) * weight

    # --- §11: thematic words at 1.5 each ---
    thematic_pts = sum(len(rx.findall(t)) * w for rx, w in _HYPE_THEMATIC_RES)

    # --- §4: punctuation with saturation ---
    n_excl = t.count("!")
    n_quest = t.count("?")
    excl_pts = min(n_excl, 3) * 1.5 + max(0, n_excl - 3) * 0.3
    quest_pts = min(n_quest, 3) * 0.8 + max(0, n_quest - 3) * 0.2

    # --- §3: uppercase by word, not character ratio ---
    upper_pts = min(len(_UPPER_WORD_RE.findall(t)), 4) * 1.5

    # --- §2: words-per-second (fast speech = excitement) ---
    words = re.findall(r"\b\w+\b", bare)
    wps = len(words) / seg.dur if seg.dur > 0 else 0.0
    wps_pts = max(0.0, (wps - 2.5)) * 4.0

    # --- §10: repetition bonus ("no no no", "watch watch watch") ---
    repeat_pts = len(_REPEAT_RE.findall(t)) * 5.0

    # --- §9: filler penalty ---
    filler_hits = len(_FILLER_RE.findall(t))
    filler_pts = filler_hits * -0.5

    # --- §12: tanh blending so magnitudes are balanced ---
    score = (
        3.0 * math.tanh(tag_pts / 15.0)
        + 2.5 * math.tanh(phrase_pts / 6.0)
        + 1.0 * math.tanh(thematic_pts / 8.0)
        + 1.5 * math.tanh(excl_pts / 4.0)
        + 1.0 * math.tanh(quest_pts / 4.0)
        + 1.0 * math.tanh(upper_pts / 3.0)
        + 1.5 * math.tanh(wps_pts / 2.0)
        + 1.0 * math.tanh(repeat_pts / 5.0)
        + 1.0 * math.tanh(max(0, -filler_pts) / 5.0)
    )

    # --- §7: gentler length normalisation ---
    # sqrt curve: dense short clips still get a boost, but ultra-short cues
    # don't nuke the ranking.  sqrt(60*dur) normalises so a 60s clip = ×1.
    norm = 60.0 / math.sqrt(max(1.0, seg.dur * 60.0))
    score *= norm

    # --- §6: audio multiplier ---
    # Prefer the z-scored peak energy when available (real dynamic spread,
    # neutral 1.0 centre).  Fall back to the old dB-linear multiplier.
    if audio_zscore is not None and audio_weight > 0:
        energy = 1.0 / (1.0 + math.exp(-audio_zscore))  # sigmoid -> [0,1]
        score *= 1.0 + audio_weight * (energy - 0.5) * 2.0
    elif loudness_db is not None and audio_weight > 0:
        energy = max(0.0, min(1.0, (loudness_db + 40.0) / 40.0))
        score *= 1.0 + audio_weight * (energy - 0.5) * 2.0

    return max(0.0, score)


def smooth_scores(chunks: List[Segment]) -> None:
    """§8: cross-cue smoothing.

    A highlight cue is usually surrounded by other excited cues. A quiet
    cue sandwiched between two loud ones is probably filler. Applies a
    weighted average in-place: 70% self, 15% each neighbour.
    """
    if len(chunks) < 2:
        return
    for i, c in enumerate(chunks):
        left = chunks[i - 1].score if i > 0 else c.score
        right = chunks[i + 1].score if i + 1 < len(chunks) else c.score
        c.score = 0.7 * c.score + 0.15 * left + 0.15 * right


# --------------------- speaker tracking (optional) ---------------------------
# Requires: pip install opencv-python-headless numpy
# If not installed, --mode speaker silently falls back to --mode crop.

def _import_cv2():
    try:
        import cv2
        import numpy as np
        return cv2, np
    except ImportError:
        return None, None


def _iou(a, b):
    ax, ay, aw, ah = a
    bx, by, bw, bh = b
    ix = max(0, min(ax + aw, bx + bw) - max(ax, bx))
    iy = max(0, min(ay + ah, by + bh) - max(ay, by))
    inter = ix * iy
    union = aw * ah + bw * bh - inter
    return inter / union if union > 0 else 0.0


def speaker_crop_trajectory(video: Path, start: float, end: float,
                            src_w: int, src_h: int,
                            crop_w: int, crop_h: int,
                            sample_fps: float = 6.0,
                            smooth_sec: float = 0.7) -> list:
    """Track faces over [start, end] and return crop-x keyframes.

    Returns [(t_rel_to_start, x_in_scaled_px), ...].
    Empty list => caller falls back to centre crop.
    """
    cv2, np = _import_cv2()
    if cv2 is None or src_w <= 0 or src_h <= 0:
        return []

    cascade = cv2.CascadeClassifier(
        cv2.data.haarcascades + "haarcascade_frontalface_default.xml")
    if cascade.empty():
        return []

    # Crop-mode geometry: scale up to fill, then crop at (x, y)
    scale = max(crop_w / src_w, crop_h / src_h)
    scaled_w = int(round(src_w * scale))
    max_x = max(0, scaled_w - crop_w)

    cap = cv2.VideoCapture(str(video))
    if not cap.isOpened():
        return []
    native_fps = cap.get(cv2.CAP_PROP_FPS) or 30.0
    cap.set(cv2.CAP_PROP_POS_MSEC, start * 1000.0)

    frame_skip = max(1, int(round(native_fps / sample_fps)))
    ds = 2 if src_w > 640 else 1    # downscale before face detect for speed

    frames = []                     # (t_rel, faces, mouth_motion_per_face)
    prev_gray, prev_boxes = None, []
    n = 0

    while True:
        ok, frame = cap.read()
        if not ok:
            break
        cur_t = cap.get(cv2.CAP_PROP_POS_MSEC) / 1000.0
        t_rel = cur_t - start
        if t_rel < 0:
            continue
        if t_rel > (end - start):
            break
        if n % frame_skip != 0:
            n += 1
            continue
        n += 1

        small = cv2.resize(frame, (frame.shape[1] // ds, frame.shape[0] // ds)) if ds > 1 else frame
        gray = cv2.cvtColor(small, cv2.COLOR_BGR2GRAY)
        faces_small = cascade.detectMultiScale(gray, 1.15, 5, minSize=(40, 40))
        faces = [(int(x * ds), int(y * ds), int(w * ds), int(h * ds))
                 for (x, y, w, h) in faces_small]

        motions = []
        for (x, y, w, h) in faces:
            m = 0.0
            if prev_gray is not None and prev_boxes:
                best_iou, best_prev = 0.0, None
                for pb in prev_boxes:
                    iou = _iou((x, y, w, h), pb)
                    if iou > best_iou:
                        best_iou, best_prev = iou, pb
                if best_prev is not None and best_iou > 0.3:
                    px, py, pw, ph = best_prev
                    # mouth regions in *small* coords
                    mx = x // ds + (w // ds) // 4
                    my = y // ds + int((h // ds) * 0.6)
                    mw = (w // ds) // 2
                    mh = int((h // ds) * 0.35)
                    pmx = px // ds + (pw // ds) // 4
                    pmy = py // ds + int((ph // ds) * 0.6)
                    ww = min(mw, (pw // ds) // 2)
                    hh = min(mh, int((ph // ds) * 0.35))
                    if ww > 3 and hh > 3:
                        cur = gray[my:my + hh, mx:mx + ww]
                        prv = prev_gray[pmy:pmy + hh, pmx:pmx + ww]
                        if cur.shape == prv.shape and cur.size > 0:
                            m = float(np.abs(cur.astype(np.int16)
                                             - prv.astype(np.int16)).mean())
            motions.append(m)

        frames.append((t_rel, faces, motions))
        prev_gray, prev_boxes = gray, faces

    cap.release()
    if not frames:
        return []

    # Sliding-window sum of per-face mouth motion
    dt = frame_skip / native_fps
    win = max(1, int(0.8 / dt))
    scores = []
    for i, (_, faces, _) in enumerate(frames):
        lo, hi = max(0, i - win), min(len(frames), i + win + 1)
        fs = []
        for (fx, fy, fw, fh) in faces:
            s = 0.0
            for j in range(lo, hi):
                _, jfaces, jmotions = frames[j]
                best_iou, best_m = 0.0, 0.0
                for k, jb in enumerate(jfaces):
                    iou = _iou((fx, fy, fw, fh), jb)
                    if iou > best_iou:
                        best_iou, best_m = iou, jmotions[k]
                if best_iou > 0.25:
                    s += best_m
            fs.append(s)
        scores.append(fs)

    # Per frame: pick the speaking face, convert to crop x
    trajectory = []
    for i, (t_rel, faces, _) in enumerate(frames):
        if not faces:
            continue
        if scores[i] and max(scores[i]) > 0.2:
            best = max(range(len(faces)), key=lambda k: scores[i][k])
        else:
            best = max(range(len(faces)), key=lambda k: faces[k][2] * faces[k][3])
        x, y, w, h = faces[best]
        cx = (x + w / 2.0) * scale
        trajectory.append((t_rel, max(0.0, min(float(max_x),
                                                   cx - crop_w / 2.0))))

    if not trajectory:
        return []

    # EMA smoothing
    alpha = max(0.0, min(0.95, 1.0 - dt / max(dt, smooth_sec)))
    sx = trajectory[0][1]
    smoothed = [(trajectory[0][0], sx)]
    for t_rel, x in trajectory[1:]:
        sx = alpha * sx + (1 - alpha) * x
        smoothed.append((t_rel, sx))

    # Reduce keyframes: emit only on meaningful change
    reduced = [smoothed[0]]
    for t_rel, x in smoothed[1:]:
        if abs(x - reduced[-1][1]) > 25 or (t_rel - reduced[-1][0]) > 2.0:
            reduced.append((t_rel, x))
    return reduced


def _crop_x_expr(trajectory: list) -> str:
    """Build a piecewise-linear ffmpeg x expression from [(t, x), ...]."""
    if not trajectory:
        return "(iw-ow)/2"
    if len(trajectory) == 1:
        return f"{trajectory[0][1]:.1f}"

    pieces = []
    for i in range(len(trajectory) - 1):
        t0, x0 = trajectory[i]
        t1, x1 = trajectory[i + 1]
        if t1 <= t0:
            continue
        pieces.append((t0, t1, x0, (x1 - x0) / (t1 - t0)))
    if not pieces:
        return f"{trajectory[0][1]:.1f}"

    expr = f"{trajectory[-1][1]:.1f}"
    for t0, t1, x0, slope in reversed(pieces):
        expr = (f"if(lt(t,{t1:.3f}),{x0:.1f}+({slope:.4f})*(t-{t0:.3f}),"
                f"{expr})")
    return expr


# --------------------------- llm prompts -------------------------------------

# Scoring prompt used by llm_hype_score(). Must contain {context_block} and {text}.
_LLM_PROMPT = """\
You are rating short video transcript segments for how exciting, funny,
or highlight-worthy they are - as candidates for a social-media highlights reel.

Rate on a scale of 0 to 10:
- 0-2  = boring / filler / low energy
- 3-5  = mildly interesting
- 6-8  = entertaining, funny, engaging
- 9-10 = outstanding, hilarious, dramatic, or very high energy

{context_block}Transcript segment to score:
\"\"\"
{text}
\"\"\"

Reply with ONLY a single number from 0 to 10. No words, no explanation.
Score:"""

_TITLE_PROMPT = """\
You are naming short vertical video clips for TikTok / Reels / Shorts.

Write ONE catchy, punchy title for this clip based on its transcript.

Rules:
- 2 to 6 words, max 40 characters
- Title Case
- No hashtags, no emoji, no trailing punctuation
- No quotes, no markdown, no "Title:" prefix
- Be specific to the actual content, not generic

Transcript:
\"\"\"
{text}
\"\"\"

Reply with ONLY the title on a single line, nothing else."""

# Successful calls cached by (model, text, context). Failures are NOT cached,
# so a temporary Ollama outage doesn't poison subsequent runs.
_LLM_CACHE: dict = {}


def _llm_available(url: str, timeout: float = 3.0) -> bool:
    """True if an Ollama service is reachable at url."""
    try:
        req = urllib.request.Request(url.rstrip("/") + "/api/tags", method="GET")
        with urllib.request.urlopen(req, timeout=timeout) as r:
            return r.status == 200
    except Exception:  # noqa: BLE001
        return False


def _llm_generate(prompt: str, model: str, url: str,
                  timeout: float = 60.0, num_predict: int = 6) -> Optional[str]:
    body = json.dumps({
        "model": model,
        "prompt": prompt,
        "stream": False,
        "options": {
            "temperature": 0,
            "num_predict": num_predict,
            "seed": 42,
            "stop": ["\n"],
        },
    }).encode("utf-8")
    req = urllib.request.Request(
        url.rstrip("/") + "/api/generate",
        data=body,
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    try:
        with urllib.request.urlopen(req, timeout=timeout) as r:
            data = json.loads(r.read())
        return data.get("response", "")
    except Exception:  # noqa: BLE001
        return None


def _llm_warmup(model: str, url: str, timeout: float = 90.0) -> bool:
    """First call is slow (model load). Force it up front so the loop is fast."""
    body = json.dumps({
        "model": model,
        "prompt": "Reply with the single digit 0.",
        "stream": False,
        "options": {"temperature": 0, "num_predict": 2},
    }).encode("utf-8")
    req = urllib.request.Request(
        url.rstrip("/") + "/api/generate",
        data=body,
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    try:
        with urllib.request.urlopen(req, timeout=timeout) as r:
            r.read()
        return True
    except Exception:  # noqa: BLE001
        return False


def _parse_llm_score(raw: str) -> Optional[float]:
    """Extract 0-10 integer from the LLM's response, tolerating '7/10' etc."""
    if not raw:
        return None
    m = re.search(r"\b(\d+(?:\.\d+)?)\s*(?:/|out\s+of)\s*10\b", raw, re.IGNORECASE)
    if m:
        val = float(m.group(1))
        if 0.0 <= val <= 10.0:
            return val
    for m in re.finditer(r"\b(\d+(?:\.\d+)?)\b", raw):
        val = float(m.group(1))
        if 0.0 <= val <= 10.0:
            return val
    return None


def llm_hype_score(text: str, model: str, url: str,
                   timeout: float = 60.0,
                   context: str = "") -> Optional[float]:
    """Return 0-10 LLM score, or None on any failure. Cached on success."""
    text = text.strip()
    if not text:
        return None
    if len(text) > 2500:
        text = text[:2500].rsplit(" ", 1)[0] + " ..."

    key = (model, text, context)
    if key in _LLM_CACHE:
        return _LLM_CACHE[key]

    ctx_block = ""
    if context.strip():
        ctx_block = (
            "Context (for reference only - do NOT score this):\n"
            f"\"\"\"\n{context.strip()}\n\"\"\"\n\n"
        )
    prompt = _LLM_PROMPT.format(context_block=ctx_block, text=text)
    raw = _llm_generate(prompt, model, url, timeout)
    score = _parse_llm_score(raw or "")
    if score is not None:
        _LLM_CACHE[key] = score
    return score


def _context_for_chunk(chunk: Segment, cues: List[Segment],
                       n: int = 1, per_cue_max: int = 200) -> str:
    """One cue before + one cue after the chunk, trimmed, marked with >>>."""
    idx_first: Optional[int] = None
    idx_last: Optional[int] = None
    for i, c in enumerate(cues):
        if c.end > chunk.start and c.start < chunk.end:
            if idx_first is None:
                idx_first = i
            idx_last = i
    if idx_first is None or idx_last is None:
        return ""
    lo = max(0, idx_first - n)
    hi = min(len(cues) - 1, idx_last + n)
    lines = []
    for i in range(lo, hi + 1):
        mark = ">>>" if idx_first <= i <= idx_last else "   "
        txt = cues[i].text[:per_cue_max]
        lines.append(f"{mark} [{stamp(cues[i].start)}] {txt}")
    return "\n".join(lines)


# -------------------------- llm titles ---------------------------------------
#
# Turns each clip's transcript into a punchy TikTok-style filename using the
# same Ollama endpoint as --llm. Falls back to the old clip_NN_stamp.mp4 naming
# on any failure (unreachable Ollama, bad output, etc.), so this is safe to
# enable unconditionally.

_TITLE_CACHE: dict = {}
_INVALID_FILENAME_CHARS = re.compile(r'[<>:"/\\|?*\x00-\x1f]')


def _clean_title(raw: str) -> Optional[str]:
    """Turn a raw LLM response into a filename-safe title (or None)."""
    if not raw:
        return None

    line = ""
    for ln in raw.splitlines():
        ln = ln.strip()
        if ln:
            line = ln
            break
    if not line:
        return None

    # Strip common LLM prefixes, surrounding punctuation, markdown, hashtags.
    line = re.sub(r"^(title|clip|output|filename)\s*[:\-]\s*", "", line,
                  flags=re.IGNORECASE).strip()
    line = line.strip("\"'`*").strip()
    line = re.sub(r"#\w+", "", line).strip()
    line = line.rstrip(".,;:!?").strip()
    line = _INVALID_FILENAME_CHARS.sub("", line)
    line = re.sub(r"\s+", " ", line).strip()

    if len(line) > 60:
        line = line[:60].rsplit(" ", 1)[0].strip()

    # Enforce hard cap of 6 words (prompt says "2 to 6 words").
    words = line.split()
    if len(words) > 6:
        line = " ".join(words[:6])
    return line or None


_LLM_COUNT_PROMPT = """\
You are the editor of a short highlight reel made from a comedy podcast.

Below are {n} candidate clips, ranked from best to worst, each with its
excitement score (0-10) and a short snippet.

Decide how many of these top clips make a good highlight reel.
Guidance:
- Reels are usually 20-40% of the candidates (skip the weak tail).
- Keep it tight; do not pad with mediocre clips.
- If you see a natural drop-off in the snippet quality, stop there.

Reply with ONLY one integer between 1 and {n}. No words, no punctuation.

Candidates:
{summary}

Count:"""


def _parse_llm_count(raw: str, max_n: int) -> Optional[int]:
    """Extract a single integer 1..max_n from the LLM's response."""
    if not raw:
        return None
    for m in re.finditer(r"\b(\d+)\b", raw):
        v = int(m.group(1))
        if 1 <= v <= max_n:
            return v
    return None


def llm_decide_count(ranked: List[Segment], model: str, url: str,
                     timeout: float = 60.0, max_entries: int = 80
                     ) -> Optional[int]:
    """Ask the LLM how many of these ranked chunks to keep.

    Returns 1..len(ranked), or None on any failure.
    """
    if not ranked:
        return None

    n = min(len(ranked), max_entries)
    lines = []
    for i, c in enumerate(ranked[:n]):
        snippet = re.sub(r"\[[^\]]*\]", "", c.text)
        snippet = re.sub(r"\s+", " ", snippet).strip()[:110]
        lines.append(
            f"{i + 1:>3}. [{stamp(c.start)}] "
            f"score={c.score / 10:.1f}  {snippet}"
        )

    prompt = _LLM_COUNT_PROMPT.format(n=n, summary="\n".join(lines))
    raw = _llm_generate(prompt, model, url, timeout=timeout, num_predict=8)
    return _parse_llm_count(raw or "", n)


def llm_title_for_chunk(text: str, model: str, url: str,
                        timeout: float = 60.0) -> Optional[str]:
    """Return a catchy filename-safe title, or None on any failure."""
    text = text.strip()
    if not text:
        return None
    if len(text) > 2000:
        text = text[:2000].rsplit(" ", 1)[0] + " ..."

    key = (model, text)
    if key in _TITLE_CACHE:
        return _TITLE_CACHE[key]

    prompt = _TITLE_PROMPT.format(text=text)
    raw = _llm_generate(prompt, model, url, timeout=timeout, num_predict=40)
    title = _clean_title(raw or "")
    if title:
        _TITLE_CACHE[key] = title
    return title


def make_clip_name(index: int, seg: Segment, title: Optional[str]) -> str:
    """Build the output filename, using the LLM title when available."""
    tail = f"{stamp(seg.start)}-{stamp(seg.end)}.mp4"
    if title:
        return f"clip_{index:02d}_{title.replace(' ', '_')}_{tail}"
    return f"clip_{index:02d}_{tail}"


# --------------------------- folder handling ---------------------------------

def find_video(folder: Path) -> Path:
    if not folder.is_dir():
        sys.exit(f"Folder not found:\n  {folder}")
    videos = sorted(
        p for p in folder.iterdir()
        if p.is_file() and p.suffix.lower() in VIDEO_EXTS
    )
    if not videos:
        sys.exit(
            f"No video found in:\n  {folder}\n"
            f"Supported extensions: {', '.join(sorted(VIDEO_EXTS))}"
        )
    if len(videos) > 1:
        listing = "\n  ".join(v.name for v in videos)
        sys.exit(
            f"Found {len(videos)} videos in:\n  {folder}\n  {listing}\n"
            "Keep only one at a time (move the extras elsewhere) and re-run."
        )
    return videos[0]


def find_transcript(folder: Path, explicit: Optional[Path]) -> Path:
    """Locate the transcript. Priority: --transcript > text.txt > single matching file."""
    if explicit is not None:
        if not explicit.is_file():
            sys.exit(f"Transcript not found:\n  {explicit}")
        return explicit
    if not folder.is_dir():
        sys.exit(f"Folder not found:\n  {folder}")

    preferred = folder / "text.txt"
    if preferred.is_file():
        return preferred

    candidates = sorted(
        p for p in folder.iterdir()
        if p.is_file() and p.suffix.lower() in TRANSCRIPT_EXTS
    )
    if not candidates:
        sys.exit(
            f"No transcript found in:\n  {folder}\n"
            f"Expected text.txt or any of: {', '.join(TRANSCRIPT_EXTS)}"
        )
    if len(candidates) > 1:
        texts = [c for c in candidates if c.stem.lower() == "text"]
        if len(texts) == 1:
            return texts[0]
        listing = "\n  ".join(c.name for c in candidates)
        sys.exit(
            f"Found {len(candidates)} transcript files in:\n  {folder}\n  {listing}\n"
            "Rename the one you want to 'text.txt' (or pass --transcript)."
        )
    return candidates[0]


# -------------------------------- ffmpeg -------------------------------------

def check_tools() -> None:
    for tool in ("ffmpeg", "ffprobe"):
        if not shutil.which(tool):
            sys.exit(f"{tool} not found on PATH. Install ffmpeg first.")


def has_subtitles_filter(ffmpeg_exe: str = "ffmpeg") -> bool:
    """True if this ffmpeg build has the libass-backed 'subtitles' filter."""
    try:
        out = subprocess.check_output(
            [ffmpeg_exe, "-hide_banner", "-filters"],
            text=True, stderr=subprocess.STDOUT, timeout=30,
        )
    except Exception:  # noqa: BLE001
        return False
    return bool(re.search(r"^\s*\S+\s+subtitles\s", out, re.MULTILINE))


def probe_duration(path: Path) -> Optional[float]:
    try:
        out = subprocess.check_output(
            ["ffprobe", "-v", "error", "-show_entries", "format=duration",
             "-of", "default=nw=1:nk=1", str(path)],
            text=True, timeout=60,
        )
        return float(out.strip())
    except Exception:  # noqa: BLE001
        return None


def probe_dimensions(path: Path) -> Optional[Tuple[int, int]]:
    """Return (width, height) of the first video stream, or None."""
    try:
        out = subprocess.check_output(
            ["ffprobe", "-v", "error", "-select_streams", "v:0",
             "-show_entries", "stream=width,height",
             "-of", "csv=p=0", str(path)],
            text=True, timeout=60,
        )
        w, h = out.strip().split(",")[:2]
        return int(w), int(h)
    except Exception:  # noqa: BLE001
        return None


def _percentile(values: List[float], pct: float) -> float:
    """Return the pct-th percentile of a non-empty list (0..100)."""
    if not values:
        return 0.0
    s = sorted(values)
    k = (len(s) - 1) * (pct / 100.0)
    f = math.floor(k)
    c = math.ceil(k)
    if f == c:
        return s[int(k)]
    return s[f] * (c - k) + s[c] * (k - f)


def audio_loudness_batch(video: Path, chunks: List[Segment],
                         ffmpeg_exe: str = "ffmpeg",
                         sample_rate: int = 2000
                         ) -> Tuple[List[Optional[float]], List[Optional[float]]]:
    """One ffmpeg pass -> (peak_RMS_dB, zscore) per chunk.

    Decodes the audio stream once at low sample rate (2000 Hz mono s16le),
    then bins sum-of-squares in Python. Much faster than spawning one ffmpeg
    per chunk: eliminates ~200-300 ms process spawn per clip plus per-call
    astats filter overhead. 2000 Hz is plenty for loudness ranking - it
    covers the fundamental + bass energy that dominates perceived volume.

    §6 change: instead of returning mean RMS per chunk (which averages out
    a 5s shout in a 25s clip to near-silence), we compute the 90th-percentile
    RMS within each chunk. This captures peak energy bursts - the actual
    exciting moments. We then z-score those peak dB values across all
    chunks so the multiplier has real dynamic spread (sigmoid(z) -> [0,1]
    centred at 0.5).

    Returns (peak_dbs, zscores) - both lists aligned with ``chunks``.
    Falls back to None per chunk on any failure (no audio stream, ffmpeg
    error, etc.) so hype_score() just uses the text-only score.
    """
    peak_dbs: List[Optional[float]] = [None] * len(chunks)
    if not chunks:
        return peak_dbs, []

    try:
        proc = subprocess.Popen(
            [
                ffmpeg_exe, "-hide_banner", "-loglevel", "error", "-nostdin",
                "-i", str(video), "-vn",
                "-ac", "1", "-ar", str(sample_rate),
                "-f", "s16le", "-acodec", "pcm_s16le", "-",
            ],
            stdout=subprocess.PIPE, stderr=subprocess.DEVNULL,
        )
        raw = proc.stdout.read()
        proc.wait()
    except Exception:  # noqa: BLE001
        return peak_dbs, [None] * len(chunks)
    if proc.returncode != 0 or not raw:
        return peak_dbs, [None] * len(chunks)

    n_samples = len(raw) // 2
    if n_samples == 0:
        return peak_dbs, [None] * len(chunks)

    samples = array.array("h")
    samples.frombytes(raw[: n_samples * 2])
    if sys.byteorder == "big":
        samples.byteswap()
    total = len(samples)

    # 100 ms bins -> ~600 bins for a 60s clip. Sum-of-squares per bin is done
    # once; per-chunk lookup then just sums a handful of bins.
    bin_samples = max(1, sample_rate // 10)
    n_bins = (total + bin_samples - 1) // bin_samples
    bins_sq = [0] * n_bins
    bins_n = [0] * n_bins
    idx = 0
    for b in range(n_bins):
        end = idx + bin_samples
        if end > total:
            end = total
        s = 0
        for j in range(idx, end):
            v = samples[j]
            s += v * v
        bins_sq[b] = s
        bins_n[b] = end - idx
        idx = end

    for i, c in enumerate(chunks):
        s_bin = int(c.start * sample_rate) // bin_samples
        e_bin = (int(c.end * sample_rate) + bin_samples - 1) // bin_samples
        if s_bin < 0:
            s_bin = 0
        if e_bin > n_bins:
            e_bin = n_bins
        if e_bin <= s_bin:
            continue
        # §6: collect per-bin RMS values, then take the 90th percentile.
        bin_rms_vals: List[float] = []
        for b in range(s_bin, e_bin):
            n = bins_n[b]
            if n == 0:
                continue
            mean_sq = bins_sq[b] / n
            if mean_sq <= 0:
                bin_rms_vals.append(-100.0)
                continue
            rms = math.sqrt(mean_sq) / 32768.0
            bin_rms_vals.append(20.0 * math.log10(rms) if rms > 1e-10 else -100.0)
        if not bin_rms_vals:
            continue
        peak_dbs[i] = _percentile(bin_rms_vals, 90)

    # §6b: z-score the peak dB values across all chunks.
    valid = [d for d in peak_dbs if d is not None]
    if len(valid) >= 2:
        mean_db = sum(valid) / len(valid)
        var = sum((v - mean_db) ** 2 for v in valid) / len(valid)
        std_db = math.sqrt(var)
        if std_db > 0:
            zscores = []
            for d in peak_dbs:
                zscores.append((d - mean_db) / std_db if d is not None else None)
            return peak_dbs, zscores

    return peak_dbs, [None] * len(chunks)


def compute_blur_layout(width: int, height: int,
                        video_w: int, video_h: int) -> Tuple[int, int]:
    """Return (title_margin_from_top, sub_margin_from_bottom) in px.

    In blur mode the fg video is scaled with `force_original_aspect_ratio=
    decrease` and centred, so the top and bottom blur bands are the same
    height. We put the title 50% down into the top band and the subtitles
    50% up into the bottom band -> both values are half_band // 2.
    """
    if video_w <= 0 or video_h <= 0:
        return height // 8, height // 8

    target_ar = width / height
    src_ar = video_w / video_h
    if src_ar >= target_ar:            # landscape / square -> width-bound
        fg_h = int(width * video_h / video_w)
    else:                              # portrait -> height-bound
        fg_h = height

    half_band = max(0, (height - fg_h) // 2)
    margin = max(40, half_band // 2)   # never hug the frame edge
    return margin, margin


def build_filter(width: int, height: int, mode: str, sub_file: Optional[str] = None,
                 crop_trajectory: Optional[list] = None):
    sub = f",subtitles={sub_file}" if sub_file else ""
    if mode == "crop":
        return None, (
            f"scale={width}:{height}:force_original_aspect_ratio=increase,"
            f"crop={width}:{height},setsar=1{sub},format=yuv420p"
        )
    if mode == "speaker":
        x_expr = _crop_x_expr(crop_trajectory or [])
        return None, (
            f"scale={width}:{height}:force_original_aspect_ratio=increase,"
            f"crop={width}:{height}:x='{x_expr}':y=(ih-oh)/2,"
            f"setsar=1{sub},format=yuv420p"
        )
    # blur (unchanged)
    graph = (
        f"[0:v]split=2[bg][fg];"
        f"[bg]scale={width}:{height}:force_original_aspect_ratio=increase,"
        f"crop={width}:{height},gblur=sigma=24[bgb];"
        f"[fg]scale={width}:{height}:force_original_aspect_ratio=decrease[fgs];"
        f"[bgb][fgs]overlay=(W-w)/2:(H-h)/2,setsar=1{sub},format=yuv420p[v]"
    )
    return graph, None


def build_command(src: Path, dst: Path, start, dur, args, width, height,
                  sub_file: Optional[str] = None, ffmpeg_exe: str = "ffmpeg",
                  crop_trajectory: Optional[list] = None):
    graph, vf = build_filter(width, height, args.mode, sub_file,
                             crop_trajectory=crop_trajectory)
    cmd = [
        ffmpeg_exe, "-hide_banner", "-loglevel", "error", "-nostdin", "-y",
        "-ss", f"{start:.3f}", "-t", f"{dur:.3f}", "-i", str(src),
    ]
    if graph:
        cmd += ["-filter_complex", graph, "-map", "[v]"]
    else:
        cmd += ["-vf", vf, "-map", "0:v:0"]
    cmd += [
        "-map", "0:a?",
        "-c:v", "libx264", "-preset", args.preset, "-crf", str(args.crf),
        "-profile:v", "high", "-pix_fmt", "yuv420p",
        "-c:a", "aac", "-b:a", "128k", "-ac", "2",
        "-movflags", "+faststart",
        "-progress", "pipe:1", "-nostats",
        str(dst),
    ]
    return cmd


def encode(cmd, duration, bar, cwd: Optional[Path] = None) -> None:
    with tempfile.TemporaryFile(mode="w+") as err:
        proc = subprocess.Popen(
            cmd, stdout=subprocess.PIPE, stderr=err, text=True, bufsize=1,
            cwd=str(cwd) if cwd else None,
        )
        done = 0.0
        for line in proc.stdout:
            line = line.strip()
            if line.startswith("out_time="):
                seconds = parse_ts(line.split("=", 1)[1])
                pct = 100.0 if duration <= 0 else min(100.0, seconds / duration * 100)
                if pct > done:
                    bar.update(pct - done)
                    done = pct
        proc.wait()
        if proc.returncode != 0:
            err.seek(0)
            raise RuntimeError(err.read().strip()[-1500:] or "ffmpeg failed")
    if done < 100:
        bar.update(100 - done)


# ----------------------------- subtitles -------------------------------------

# ASS header: white text, black opaque box (BorderStyle=3), bottom-centre.
_ASS_HEADER = """[Script Info]
ScriptType: v4.00+
PlayResX: {width}
PlayResY: {height}
WrapStyle: 2
ScaledBorderAndShadow: yes

[V4+ Styles]
Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding
Style: Default,{font},{size},&H00FFFFFF,&H000000FF,&H00000000,&H00000000,-1,0,0,0,100,100,0,0,3,{pad},0,2,{ml},{mr},{mv},1
Style: Title,{font},{title_size},&H00FFFFFF,&H000000FF,&H00000000,&H00000000,-1,0,0,0,100,100,0,0,3,{title_pad},0,8,{ml},{mr},{title_mv},1

[Events]
Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text
"""


def fmt_ass_time(t: float) -> str:
    if t < 0:
        t = 0.0
    cs = int(round(t * 100))
    h, cs = divmod(cs, 360000)
    m, cs = divmod(cs, 6000)
    s, cs = divmod(cs, 100)
    return f"{h:d}:{m:02d}:{s:02d}.{cs:02d}"


def segment_words(seg: Segment) -> List[Tuple[float, float, str]]:
    """Estimate per-word timings inside a cue, proportional to word length."""
    text = re.sub(r"\[[^\]]*\]", "", seg.text)
    words = text.split()
    if not words:
        return []
    weights = [len(w) + 1 for w in words]
    total = float(sum(weights))
    dur = seg.dur
    t = seg.start
    out: List[Tuple[float, float, str]] = []
    for w, wt in zip(words, weights):
        wd = dur * wt / total
        out.append((t, t + wd, w))
        t += wd
    return out


def group_words(words: List[Tuple[float, float, str]], per_group: int = 4,
                max_gap: float = 0.35) -> List[List[Tuple[float, float, str]]]:
    per_group = max(1, per_group)
    groups: List[List[Tuple[float, float, str]]] = []
    cur: List[Tuple[float, float, str]] = []
    for w in words:
        if cur and (len(cur) >= per_group or w[0] - cur[-1][1] > max_gap):
            groups.append(cur)
            cur = []
        cur.append(w)
    if cur:
        groups.append(cur)
    return groups


def build_ass(groups, clip_start: float, clip_end: float,
              width: int, height: int,
              font_size: int = 0, margin_v: int = 0,
              max_card_sec: float = 4.0, min_card_sec: float = 0.6,
              title: Optional[str] = None,
              title_margin_v: int = 0,
              title_font_size: int = 0) -> str:
    clip_dur = max(0.0, clip_end - clip_start)
    fs = font_size or max(28, height // 22)
    mv = margin_v or max(40, height // 12)
    tfs = title_font_size or max(fs, int(fs * 1.35))
    tmv = title_margin_v or mv
    pad = max(3, fs // 8)
    tpad = max(3, tfs // 8)
    side = max(20, width // 20)

    parts = [_ASS_HEADER.format(
        width=width, height=height, font="Arial",
        size=fs, pad=pad, ml=side, mr=side, mv=mv,
        title_size=tfs, title_pad=tpad, title_mv=tmv,
    )]

    if title:
        safe = title.replace("{", "").replace("}", "").replace("\\", "")
        parts.append(
            f"Dialogue: 0,{fmt_ass_time(0)},{fmt_ass_time(clip_dur)},"
            f"Title,,0,0,0,,{safe}"
        )

    for g in groups:
        start = g[0][0] - clip_start
        end = g[-1][1] - clip_start
        if end <= 0 or start >= clip_dur:
            continue
        start = max(0.0, start)
        end = min(clip_dur, end)

        # Cap overly long cards (slow words / silent tail in the cue)
        if end - start > max_card_sec:
            end = start + max_card_sec
        # Make sure the card is up long enough to actually read
        if end - start < min_card_sec:
            end = min(clip_dur, start + min_card_sec)
        text = " ".join(w[2] for w in g)
        text = text.replace("{", "").replace("}", "").replace("\\", "")
        parts.append(
            f"Dialogue: 0,{fmt_ass_time(start)},{fmt_ass_time(end)},"
            f"Default,,0,0,0,,{text}"
        )
    return "\n".join(parts) + "\n"


# --------------------------------- main --------------------------------------

def main():
    ap = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter
    )

    ap.add_argument("--dir", type=Path, default=TOOL_DIR,
                    help=f"folder containing the video (default: {TOOL_DIR})")
    ap.add_argument("--transcript", type=Path, default=None,
                    help="transcript path (default: <dir>/text.txt)")
    ap.add_argument("--video", type=Path, default=None,
                    help="explicit video file (default: auto-detect in --dir)")
    ap.add_argument("-o", "--outdir", type=Path, default=None,
                    help="output folder (default: <dir>/clips)")

    # selection
    ap.add_argument("--all", action="store_true",
                    help="keep every chunk (default when nothing else given)")
    ap.add_argument("--keywords", default="",
                    help="comma separated terms; keep chunks containing them")
    ap.add_argument("--hype", action="store_true",
                    help="rank chunks by a pure-Python 'exciting moment' score")
    ap.add_argument("--max-clips", type=int, default=None,
                    help="keep only the top N clips after ranking (default 10, "
                         "or 0 = uncapped). With --llm-decide-count, acts as an "
                         "upper bound (default = uncapped when LLM decides).")
    ap.add_argument("--audio-weight", type=float, default=1.0, metavar="0..1",
                    help="how strongly audio loudness boosts the score (0 = off, 1 = full)")

    # LLM re-ranking
    ap.add_argument("--llm", action="store_true",
                    help="re-rank the top heuristic chunks with a local LLM (Ollama)")
    ap.add_argument("--llm-model", default="qwen2.5:3b",
                    help="Ollama model name (default: qwen2.5:3b)")
    ap.add_argument("--llm-url", default="http://localhost:11434",
                    help="Ollama base URL (default: http://localhost:11434)")
    ap.add_argument("--llm-top", type=int, default=0, metavar="N",
                    help="how many top heuristic chunks to LLM-score "
                         "(0 = auto: max(25, max_clips*3))")
    ap.add_argument("--llm-blend", type=float, default=0.25, metavar="0..1",
                    help="mix in heuristic score: 0 = pure LLM, 1 = pure heuristic "
                         "(default 0.25)")
    ap.add_argument("--llm-timeout", type=float, default=60.0, metavar="SECONDS",
                    help="per-call LLM timeout in seconds (default 60)")
    ap.add_argument("--llm-context", action="store_true",
                    help="include 1 cue before/after each chunk as context")
    ap.add_argument("--llm-decide-count", action="store_true",
                    help="let the LLM decide how many clips to produce. "
                         "Requires --llm and scores every chunk. "
                         "Use --max-clips N to cap the LLM's choice.")
    ap.add_argument("--llm-count-model", default=None,
                    help="separate Ollama model for the count decision "
                         "(default: same as --llm-model)")
    ap.add_argument("--llm-titles", action="store_true",
                    help="use the local LLM to name each clip with a catchy TikTok title")

    # chunking
    ap.add_argument("--min-clip", type=float, default=25.0, metavar="SECONDS",
                    help="minimum length of each output clip (default 25)")

    # encoding / reframing
    ap.add_argument("--mode", choices=("blur", "crop", "speaker"), default="blur",
                    help="how to fill the 9:16 frame. 'crop' = centre crop (~2x faster); "
                         "'speaker' = auto-track the active face (needs opencv-python); "
                         "'blur' = padded bands")
    ap.add_argument("--resolution", default="1080x1920")
    ap.add_argument("--crf", type=int, default=20)
    ap.add_argument("--preset", default="veryfast",
                    help="x264 preset (default: veryfast). 'ultrafast' is ~5-10x "
                         "faster but larger files; 'medium' is slower but smaller.")
    ap.add_argument("--dry-run", action="store_true")

    # subtitles
    ap.add_argument("--subtitles", action="store_true", default=True,
                    help="burn white-on-black subtitles into each clip "
                         "(default on; use --no-subtitles to disable)")
    ap.add_argument("--no-subtitles", dest="subtitles", action="store_false",
                    help="disable subtitle burn-in")
    ap.add_argument("--sub-words", type=int, default=4, metavar="N",
                    help="words per subtitle card (default 4)")
    ap.add_argument("--sub-font-size", type=int, default=0,
                    help="subtitle font size in px (0 = auto from resolution)")
    ap.add_argument("--title-font-size", type=int, default=0,
                    help="title font size in px (0 = auto, ~1.35x subtitle size)")
    ap.add_argument("--sub-margin", type=int, default=0,
                    help="bottom margin in px (0 = auto from resolution)")

    args = ap.parse_args()

    if args.mode == "speaker":
        cv2, _ = _import_cv2()
        if cv2 is None:
            print(
                "! --mode speaker needs opencv-python-headless + numpy. "
                "Install with:  pip install opencv-python-headless numpy\n"
                "  Falling back to --mode crop.",
                file=sys.stderr,
            )
            args.mode = "crop"

    if args.max_clips is None:
        args.max_clips = 0 if args.llm_decide_count else 10

    check_tools()
    ffmpeg_exe = shutil.which("ffmpeg") or "ffmpeg"

    try:
        width, height = (int(v) for v in args.resolution.lower().split("x"))
    except ValueError:
        sys.exit("--resolution must look like 1080x1920")

    folder = args.dir
    transcript = find_transcript(folder, args.transcript)
    outdir = args.outdir or (folder / "clips")
    video = args.video or find_video(folder)

    if not video.is_file():
        sys.exit(f"Video not found:\n  {video}")

    print(f"Video:      {video.name}")
    print(f"Transcript: {transcript.name}")
    print(f"Output:     {outdir}")

    duration = probe_duration(video)
    video_dims = probe_dimensions(video)
    if duration and duration < args.min_clip:
        print(
            f"! video is {duration:.0f}s, shorter than --min-clip "
            f"{args.min_clip:.0f}s. Producing one clip of the full video.",
            file=sys.stderr,
        )

    try:
        cues = load_transcript(transcript, duration)
    except ValueError as exc:
        sys.exit(str(exc))
    if not cues:
        sys.exit("No timed segments found in the transcript.")

    chunks = chunk_by_duration(cues, args.min_clip)

    if duration:
        for c in chunks:
            if c.end > duration + 0.5:
                c.end = duration
        chunks = [c for c in chunks if c.dur >= 1.0]

    if not chunks:
        sys.exit("No chunks could be built from this transcript.")

    # ---- heuristic scoring (audio measurement batched into one ffmpeg pass) ----
    if args.audio_weight > 0:
        peak_dbs, zscores = audio_loudness_batch(video, chunks, ffmpeg_exe)
    else:
        peak_dbs, zscores = [None] * len(chunks), [None] * len(chunks)

    for c, db, z in zip(chunks, peak_dbs, zscores):
        c.score = hype_score(c, db, args.audio_weight, audio_zscore=z)

    selected = list(chunks)

    # §8: cross-cue smoothing - a quiet cue between two loud ones is probably
    # filler.  Applied on the full chunk list (temporal neighbours).
    smooth_scores(selected)

    if args.keywords.strip():
        kws = [k.strip().lower() for k in args.keywords.split(",") if k.strip()]
        filtered = []
        for c in selected:
            low = c.text.lower()
            c.hits = sum(low.count(k) for k in kws)
            if c.hits:
                filtered.append(c)
        if not filtered:
            sys.exit("No chunks matched those keywords.")
        selected = filtered

    if args.keywords.strip() and not args.hype:
        rank_key = lambda s: (-s.hits, -s.score)  # noqa: E731
    else:
        rank_key = lambda s: -s.score             # noqa: E731

    # ---- LLM setup (availability + warmup once, for both ranking and titles) ----
    llm_ready = False
    if args.llm or args.llm_titles:
        if not _llm_available(args.llm_url):
            print(
                f"! Ollama not reachable at {args.llm_url} - LLM features disabled. "
                "Start it with: ollama serve",
                file=sys.stderr,
            )
            args.llm = False
            args.llm_titles = False
        else:
            print(f"LLM: warming up {args.llm_model}...", file=sys.stderr)
            if not _llm_warmup(args.llm_model, args.llm_url):
                print(
                    f"! LLM warmup failed for '{args.llm_model}'. Is the model pulled?\n"
                    f"  Run: ollama pull {args.llm_model}",
                    file=sys.stderr,
                )
                args.llm = False
                args.llm_titles = False
            else:
                llm_ready = True

    # ---- optional LLM re-ranking ----
    if args.llm and llm_ready and len(selected) > 0:
        if args.llm_decide_count:
            top_n = len(selected)
        else:
            mc = args.max_clips if args.max_clips > 0 else len(selected)
            auto_top = max(25, mc * 3)
            top_n = args.llm_top if args.llm_top > 0 else auto_top
            top_n = max(top_n, mc)
            top_n = min(top_n, len(selected))

        ranked = sorted(selected, key=rank_key)
        candidates = ranked[:top_n]
        rest = ranked[top_n:]

        pool_max_heur = max((c.score for c in candidates), default=100.0) or 100.0
        blend = max(0.0, min(1.0, args.llm_blend))

        print(
            f"LLM: scoring top {top_n}/{len(selected)} chunks with "
            f"{args.llm_model} (blend={blend:.2f})",
            file=sys.stderr,
        )

        llm_failures = 0
        bar = tqdm(candidates, desc="llm", unit="chunk",
                   position=0, leave=False)
        try:
            for c in bar:
                ctx = _context_for_chunk(c, cues, 1) if args.llm_context else ""
                llm = llm_hype_score(
                    c.text, args.llm_model, args.llm_url,
                    args.llm_timeout, ctx,
                )
                heur_norm = min(100.0, c.score / pool_max_heur * 100.0)
                if llm is None:
                    llm_failures += 1
                    c.score = heur_norm
                    continue
                llm_norm = (llm / 10.0) * 100.0
                c.score = (1.0 - blend) * llm_norm + blend * heur_norm
        except KeyboardInterrupt:
            print("\n! LLM scoring interrupted - using partial results",
                  file=sys.stderr)
        finally:
            bar.close()

        if llm_failures:
            print(
                f"! {llm_failures}/{top_n} LLM calls failed - those chunks "
                "kept their normalised heuristic score",
                file=sys.stderr,
            )

        # Normalise rest onto the same [0, 100] scale as LLM-scored
        # candidates. Without this, un-scored chunks could keep their
        # raw per-minute heuristic (e.g. 200+) and silently outrank
        # every LLM-scored chunk when the final sort runs.
        for c in rest:
            c.score = min(100.0, c.score / pool_max_heur * 100.0)

        candidates.sort(key=lambda s: -s.score)
        selected = candidates + rest

    # ---- final truncation (now that LLM has re-ranked) ----
    if args.llm and llm_ready and args.llm_decide_count:
        ranked = sorted(selected, key=lambda s: -s.score)
        count_model = args.llm_count_model or args.llm_model
        llm_count = llm_decide_count(
            ranked, count_model, args.llm_url, args.llm_timeout,
        )

        if llm_count is None:
            if args.max_clips > 0 and len(ranked) > args.max_clips:
                selected = ranked[: args.max_clips]
                print(
                    f"! LLM count decision failed - falling back to "
                    f"--max-clips {args.max_clips}", file=sys.stderr,
                )
            else:
                selected = ranked
        else:
            if args.max_clips > 0:
                llm_count = min(llm_count, args.max_clips)
            llm_count = max(1, llm_count)
            selected = ranked[:llm_count]
            print(
                f"LLM count decision: keep {llm_count} of "
                f"{len(ranked)} chunks", file=sys.stderr,
            )

    elif args.max_clips and len(selected) > args.max_clips:
        selected = sorted(selected, key=lambda s: -s.score)[: args.max_clips]

    selected.sort(key=lambda s: s.start)

    if not args.all and not args.keywords.strip() and not args.hype and not args.llm:
        print("No selector given - ranking by score and taking top "
              f"{args.max_clips} clips.", file=sys.stderr)

    print(
        f"{len(cues)} cues -> {len(chunks)} chunks (>= {args.min_clip:.0f}s each)"
        f" -> {len(selected)} clips\n"
    )
    if args.dry_run:
        for i, c in enumerate(selected, 1):
            title = None
            if args.llm_titles:
                title = llm_title_for_chunk(
                    c.text, args.llm_model, args.llm_url, args.llm_timeout,
                )
            tag = f'  "{title}"' if title else ""
            print(
                f"  {i:02d}  {stamp(c.start)} -> {stamp(c.end)}  "
                f"[{c.dur:5.1f}s  hype={c.score:5.1f}]{tag}  {c.text[:70]}"
            )
        return

    if args.mode == "blur" and video_dims:
        title_mv, computed_sub_mv = compute_blur_layout(
            width, height, video_dims[0], video_dims[1]
        )
    elif args.mode == "blur":
        title_mv, computed_sub_mv = height // 8, height // 8
    else:                                # crop or speaker: video fills the frame
        title_mv, computed_sub_mv = height // 10, height // 12

    sub_mv = args.sub_margin or computed_sub_mv

    need_ass = args.subtitles or args.llm_titles
    sub_dir: Optional[Path] = None
    all_words: List[Tuple[float, float, str]] = []
    if need_ass:
        if not has_subtitles_filter(ffmpeg_exe):
            print(
                "! This ffmpeg build has no 'subtitles' filter (needs libass) - "
                "continuing without subtitles/titles.\n"
                "  Install a libass-enabled build: https://www.gyan.dev/ffmpeg/builds/",
                file=sys.stderr,
            )
            args.subtitles = False
            args.llm_titles = False
        else:
            sub_dir = Path(tempfile.mkdtemp(prefix="clipsubs_"))
            for c in cues:
                all_words.extend(segment_words(c))
            if not all_words and not args.llm_titles:
                print("! no words found for subtitles - skipping burn-in",
                      file=sys.stderr)
                shutil.rmtree(sub_dir, ignore_errors=True)
                sub_dir = None

    outdir.mkdir(parents=True, exist_ok=True)
    failures = []

    outer = tqdm(total=len(selected), desc="clips", unit="clip", position=0)
    try:
        for index, seg in enumerate(selected, 1):
            title = None
            if args.llm_titles:
                title = llm_title_for_chunk(
                    seg.text, args.llm_model, args.llm_url, args.llm_timeout,
                )
            name = make_clip_name(index, seg, title)
            dest = outdir / name
            bar = tqdm(
                total=100,
                desc=f"{index:02d} {name}"[:40],
                leave=False,
                position=1,
            )

            sub_name: Optional[str] = None
            if sub_dir is not None:
                words = [w for w in all_words
                         if w[1] > seg.start and w[0] < seg.end]
                groups = group_words(words, args.sub_words) if args.subtitles else []
                ass_text = build_ass(
                    groups, seg.start, seg.end, width, height,
                    font_size=args.sub_font_size,
                    margin_v=sub_mv,
                    title=title,
                    title_margin_v=title_mv,
                    title_font_size=args.title_font_size,
                )
                sub_name = f"subs_{index:02d}.ass"
                (sub_dir / sub_name).write_text(ass_text, encoding="utf-8")

            try:
                traj = None
                if args.mode == "speaker" and video_dims:
                    traj = speaker_crop_trajectory(
                        video, seg.start, seg.end,
                        video_dims[0], video_dims[1],
                        width, height,
                    )
                cmd = build_command(video, dest, seg.start, seg.dur, args,
                                    width, height, sub_name, ffmpeg_exe,
                                    crop_trajectory=traj)
                encode(cmd, seg.dur, bar, cwd=sub_dir)
            except Exception as exc:  # noqa: BLE001
                failures.append(name)
                tqdm.write(f"x {name}: {exc}")
            else:
                tqdm.write(f"+ {dest}")
            finally:
                bar.close()
                outer.update(1)
    finally:
        outer.close()
        if sub_dir is not None:
            shutil.rmtree(sub_dir, ignore_errors=True)

    ok = len(selected) - len(failures)
    print(f"\nDone. {ok}/{len(selected)} clips -> {outdir}")
    if failures:
        print("Failed: " + ", ".join(failures))
        sys.exit(1)


if __name__ == "__main__":
    main()