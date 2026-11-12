#!/usr/bin/env python3
"""manual_stories.py - write stories.srt from a hardcoded story list.

No LLM. No Ollama. Parses text.txt and emits the SRT video.py expects.
"""
import re
from pathlib import Path

TOOL = Path(r"C:\Users\liam\Documents\GitHub\all-of-my-code\tool")
TXT  = TOOL / "text.txt"
SRT  = TOOL / "stories.srt"

BRACKET_RE = re.compile(r"^\[(\d{1,3}):(\d{2})(?::(\d{2}))?\]\s*(.*)$")
TAG_RE     = re.compile(r"\[[^\]]*\]")

STORIES = [
    ("6:19",  "7:25",  "Sausage Special"),
    ("8:20",  "10:20", "Plane Cough Kid"),
    ("10:29", "12:28", "Rock Names"),
    ("12:32", "14:05", "Paddle Mania"),
    ("14:05", "15:40", "Paddle Pals"),
    ("17:54", "18:41", "Rolling Stones Banned"),
    ("19:01", "20:25", "Cinema Hot Pizza"),
    ("20:25", "21:39", "Play the Game"),
    ("21:42", "23:10", "Cinema Fart Roulette"),
    ("23:13", "23:52", "Gondola Fart"),
    ("32:14", "33:41", "Blowing Nose Debate"),
    ("34:53", "36:30", "Driving Grumbles"),
    ("36:30", "37:38", "Butter Grumble"),
    ("37:38", "39:36", "Lady in Red Grumble"),
    ("43:57", "45:01", "BGT Judges Offer"),
    ("46:55", "47:48", "Grow Tube Impression"),
    ("47:48", "49:42", "Owl Impression"),
    ("53:42", "55:30", "Japan Advice"),
    ("55:30", "57:28", "Aaron Donnelly Relative"),
]

def parse_ts(s):
    parts = [int(x) for x in s.strip().split(":")]
    while len(parts) < 3:
        parts.insert(0, 0)
    h, m, sec = parts[-3:]
    return h * 3600 + m * 60 + sec

def fmt_srt(seconds):
    ms = int(round(seconds * 1000))
    h, ms = divmod(ms, 3600000)
    m, ms = divmod(ms, 60000)
    s, ms = divmod(ms, 1000)
    return f"{h:02d}:{m:02d}:{s:02d},{ms:03d}"

def parse_brackets(raw):
    entries = []
    for line in raw.splitlines():
        line = line.strip()
        if not line:
            continue
        m = BRACKET_RE.match(line)
        if m:
            a, b, c, text = m.groups()
            start = (int(a) * 3600 + int(b) * 60 + int(c)) if c else (int(a) * 60 + int(b))
            entries.append([start, text.strip()])
        elif entries:
            entries[-1][1] = (entries[-1][1] + " " + line).strip()
    return entries

def excerpt_for(entries, start_s, end_s):
    parts = []
    for i, (s, text) in enumerate(entries):
        next_s = entries[i + 1][0] if i + 1 < len(entries) else end_s + 1
        if next_s <= start_s or s >= end_s:
            continue
        clean = TAG_RE.sub("", text).strip()
        if clean:
            parts.append(clean)
    return " ".join(parts)

def main():
    entries = parse_brackets(TXT.read_text(encoding="utf-8-sig"))
    if not entries:
        raise SystemExit("Could not parse text.txt - expected '[M:SS] text' lines")

    lines = []
    for i, (start, end, title) in enumerate(STORIES, 1):
        s, e = parse_ts(start), parse_ts(end)
        body = excerpt_for(entries, s, e).replace("\n", " ").strip() or title
        lines += [str(i), f"{fmt_srt(s)} --> {fmt_srt(e)}", body, ""]

    SRT.write_text("\n".join(lines), encoding="utf-8")
    print(f"Wrote {len(STORIES)} stories -> {SRT}")
    for start, end, title in STORIES:
        s, e = parse_ts(start), parse_ts(end)
        print(f"  {fmt_srt(s)} -> {fmt_srt(e)}  ({e-s:>3}s)  {title}")

if __name__ == "__main__":
    main()