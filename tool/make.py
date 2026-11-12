#!/usr/bin/env python3
"""make.py - run stories.py then video.py in one go.

    python make.py
    python make.py --story-min 20 --story-max 90 --model qwen2.5:14b
    python make.py --preset ultrafast --mode crop
"""

import argparse
import subprocess
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
STORIES_SRT = HERE / "stories.srt"


def run(cmd):
    print(f">> {' '.join(str(c) for c in cmd)}", flush=True)
    r = subprocess.run([str(c) for c in cmd], cwd=HERE)
    if r.returncode != 0:
        sys.exit(r.returncode)


def main():
    ap = argparse.ArgumentParser()
    # stories.py options
    ap.add_argument("--model", default="qwen2.5:3b")
    ap.add_argument("--story-min", type=int, default=25)
    ap.add_argument("--story-max", type=int, default=120)
    ap.add_argument("--no-cache", action="store_true")
    # video.py passthrough
    ap.add_argument("--preset", default="veryfast")
    ap.add_argument("--mode", choices=("blur", "crop", "speaker"), default="blur")
    ap.add_argument("--no-subtitles", action="store_true")
    ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args()

    stories_cmd = [
        sys.executable, "stories.py",
        "--model", args.model,
        "--min", str(args.story_min),
        "--max", str(args.story_max),
    ]
    if args.no_cache:
        stories_cmd.append("--no-cache")
    run(stories_cmd)

    video_cmd = [
        sys.executable, "video.py",
        "--transcript", str(STORIES_SRT),
        "--min-clip", "0",
        "--max-clips", "0",
        "--llm-titles",
        "--preset", args.preset,
        "--mode", args.mode,
    ]
    if args.no_subtitles:
        video_cmd.append("--no-subtitles")
    if args.dry_run:
        video_cmd.append("--dry-run")
    run(video_cmd)


if __name__ == "__main__":
    main()