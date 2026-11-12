#!/usr/bin/env python3
"""
GTA 7 Leaks Shorts Generator — TikTok Portrait 9:16
Video Background + Logo + 4-Word Chunking
"""

import asyncio
import os
import re
import random
import subprocess
import tempfile
import time
from pathlib import Path
from typing import List, Dict

from PIL import Image, ImageDraw, ImageFont
from tqdm import tqdm

import edge_tts

# Handle different moviepy versions
try:
    from moviepy import AudioFileClip
except ImportError:
    from moviepy.editor import AudioFileClip

# ═══════════════════════ Config ═════════════════════════
WIDTH, HEIGHT  = 1080, 1920   # TikTok native 9:16
FPS            = 30
INTRO_DURATION = 2.5
LEAK_TITLE_DURATION = 1.5
OUTRO_DURATION = 2.5
LEAKS_PER_SHORT = 1           # 1 = 20 short videos (~2 min each).

TTS_VOICE = "en-US-GuyNeural"

# ═══════════════════════ Asset Paths ════════════════════
BASE_DIR = Path(__file__).parent.resolve()

# IMAGE LOGO
LOGO_PATH = BASE_DIR / "GTA7-removebg-preview.png"

# VIDEO BACKGROUND
BG_VIDEO_PATH = Path(r"C:\Users\liam\Pictures\apple its glowtime\iPhone 16\Launch Trailer - Grand Theft Auto VI (2026) - ROCKSTAR WEB-DL [4K 30] H.265.mp4")

# ═══════════════════════ 20 GTA 7 Leak Scripts ══════════
RAW_SCRIPTS = """Script 1: Project Coral

A since-deleted Reddit post claimed to come from a Rockstar San Diego QA contractor, and the poster said the build they were testing carried a debug menu string reading G-T-A-seven-dev-zero-point-three-point-one-one-seven-four-RAGE-nine, dated February 2026. The same dump allegedly showed test-map zones labeled Liberty City North, Carcer Industrial, and Alderney West, and the poster claimed a second string, streaming-zone-Carcer-Steel-version-two, appeared in the same file. They also said there was a QA checklist item for snow tire-chain level of detail and that the internal codename was Project Coral. According to the post, the build was mostly greybox but already had a working pause-menu placeholder and a rough map screen. What makes people suspicious is that there was no screenshot, the build number looked too clean, and a February 2026 QA build would still be very early for a game of this size. The post vanished within a day, which only made it spread faster.

Script 2: Liberty and Carcer Map

A 4chan thread from October 2026 claimed the poster had seen a map review PDF through a friend at a localization vendor. The claim was that GTA Seven is set around a rebuilt Liberty City, Alderney, and Carcer City, not Vice City. The map is allegedly roughly one point four to one point six times the size of GTA Six, with a permanent snowline across the northern third. Plowed roads create temporary lanes, tire-chain physics matter, and bridges can close in storms. The poster also claimed the map has three airports, one cargo rail network, and a lot of water, and that Broker and Dukes are recognizable but not nostalgia-bait. They said the northern industrial zone is built around a working steel mill and a rail yard that both appear in story missions. The red flag is that a map review PDF is vague, the size comparison is suspiciously precise, and the poster never named the vendor or the file.

Script 3: Two Protagonists Casting Sheet

A blurry casting sheet allegedly from Rockstar Lincoln was posted to X and deleted within an hour. It listed two leads: a Haitian-American smuggler in her early thirties and a fifties ex-union fixer from Carcer. The story allegedly spans 1998 and 2027, with the first act set during a Carcer steel strike. The sheet reportedly mentioned dual-protagonist fight choreography and snow-footing animation tests, and the poster claimed the 1998 section is linear but not a tutorial. The modern section allegedly opens with the fixer owing money to a rebuilt Liberty union fund, and the smuggler is introduced through a botched cargo run. The sheet also supposedly listed a third credited role described only as a federal liaison. The red flag is that casting sheets rarely name eras and plot hooks that cleanly, and the photo was too blurry to read any actual names.

Script 4: Regional Hurricane System

A supposed ex-environment artist posted on a private Discord, and screenshots were reposted to Reddit. The claim was that GTA Seven upgrades GTA Six's weather into a regional storm system. Hurricanes can redirect NPC traffic, close bridges, and alter mission routes. The artist claimed a debug command called weather-front-override was still in the build, and that storm fronts move across the map rather than switching on per district. Some missions allegedly have weather branches where a hurricane forces a different getaway route, and one early mission supposedly changes from a car chase to a boat chase if the storm arrives early. The artist also said puddles and flooding are tied to the storm front, not just the district, and that tire spray changes on flooded roads. The red flag is that an ex-environment artist with a debug command but no build footage is a very thin source, and the Discord screenshots had no timestamps.

Script 5: Heat Memory Wanted System

A now-private Twitter account claimed to have seen a design doc snippet. The claim was that police remember your vehicle, clothing, and safehouses across in-game days. Instead of instantly resetting, patrols increase around your last known area during a cooldown. The leak also claimed separate city police, state troopers, and a federal task force appear after story flags. The federal unit allegedly uses unmarked cars and surveillance vans, not tanks, and only responds to heat-memory incidents above a threshold. State troopers allegedly handle highway pursuits and bridge checkpoints, and city police handle local patrols. The poster said heat memory was tested heavily after complaints about GTA Six's wanted system, and that changing your vehicle or clothes can reduce recognition. The red flag is that a design doc snippet with no file name or date is almost impossible to verify.

Script 6: Tire Deformation and Brake Fade

A now-private Twitter account posted telemetry strings allegedly from a handling file. The claim was that GTA Seven has per-tire deformation, brake fade, and snow and ice grip values. Fuel is not in the game, but EV charging stations exist as props and can be used in one scripted heist. The strings allegedly included tire-wear-rate, brake-fade-temp, and snow-grip-mu. Tire chains are allegedly a purchasable upgrade that changes audio and handling, and one mission requires charging a getaway van while keeping NPCs away. The poster also claimed brake fade is disabled in most story missions but active in free roam, and that snow grip changes between plowed and unplowed roads. They said the handling file had separate values for ice, packed snow, and slush. The red flag is that telemetry strings are easy to fake, the EV-heist detail is oddly specific, and no actual file was ever shown.

Script 7: GTAO Next Separate Client

A purported Rockstar Leeds source posted on a burner account and then deleted it. The claim was that GTA Seven ships with a separate online client internally called GTAO Next. It allegedly has thirty-two-player free roam, persistent property, and session continuity that keeps a vehicle out between modes. The online client is installed separately but shares the same map streaming data. Properties persist across sessions, and a crew garage system lets crews pool vehicles. The source also claimed GTAO Next was why the internal date slipped, and that the online team was waiting for GTA Six's second online year before locking the roadmap. They said the client has its own launcher entry and its own update channel. The red flag is that a Rockstar Leeds source is a very convenient anonymous credential, and the post gave no build strings or file names to back any of it up.

Script 8: Radio Station List

A leaked text file was allegedly posted to a music-industry Discord and screenshotted. It listed nineteen stations, including Liberty Underground for post-punk, Carcer Steel for industrial, Vice Wave for synth, and WCTR Rebuilt for talk. Three stations are allegedly story-reactive and change hosts after major missions. One station's playlist unlocks only after the 1998 prologue. The poster claimed Rockstar licensed three unreleased 1990s industrial tracks and several Liberty City punk demos, and that one station has a call-in segment that changes after a bridge closure mission. They also said the talk station has a recurring host who comments on the steel strike in the prologue and then reappears in the modern section. The red flag is that a text file with no metadata proves nothing, and Vice Wave in a Liberty and Carcer game directly contradicts the map leak.

Script 9: Soft-Fail Missions

A supposed mission designer posted on a throwaway Reddit account. The claim was that GTA Seven uses more soft-fail missions. If you lose a target or crash a getaway, the mission continues down a different branch rather than restarting. One early mission allegedly has three outcomes depending on whether you keep the target's car, lose it, or destroy it. Another heist allegedly has at least six entry variants, including a snowplow route. The designer said this was tested after criticism of GTA Six's mission rigidity, and that some missions have a hidden timer that changes the ending rather than failing you. They also claimed one mission can end with the target escaping and later reappearing in a side mission. The red flag is that the source gave no mission names except one vague snowplow detail, and the post used generic design language that anyone could write.

Script 10: Enterable Interiors

A data-miner claimed to have parsed a build manifest. The claim was that roughly thirty-five to forty percent of buildings in the main city are enterable, with a door-push animation replacing teleport markers. Interiors are allegedly reused as apartments, offices, and heist backrooms. The manifest included asset groups for apartments, offices, and backrooms. Some interiors allegedly have windows that look onto the street in real time, and a few apartments have working blinds and lights. The miner also said some interiors are only enterable during missions, while others are open in free roam. They claimed the door-push system has a stamina cost if you run into a locked door. The red flag is that a manifest parse with no file paths and no screenshots is not evidence, and the percentage is exactly the kind of number that sounds technical but means nothing without a source file.

Script 11: NPC Multi-Day Schedules

A supposed AI and behavior leak was posted to a private game-dev forum. The claim was that NPCs have multi-day schedules tied to jobs, transit, and weather. A specific bus driver's route changes after a bridge closure, and named NPCs can reappear in different districts. Named NPCs allegedly have home, work, and third-place nodes, and weather can cancel outdoor schedules. One mission target's routine changes if you scout him on a rainy day, and a store clerk can be seen commuting if you follow him after closing. The system is allegedly not simulation-level, just persistent enough to notice. The poster also claimed the schedule system was cut from GTA Six late in development and rebuilt for Seven. The red flag is that "not simulation-level" is exactly the caveat a faker adds to sound credible, and the forum post had no screenshots or file names.

Script 12: Heist Prep Board

A leak allegedly came from a QA tester's phone photo of a whiteboard. The claim was that heists are built around a prep board. You scout entrances, buy or steal equipment, and the game remembers what you used. The whiteboard allegedly had columns for entry, exit, disguise, and complication. One heist allegedly has six entry variants, and unused prep carries into a later mission. The board is allegedly in the pause menu under a crew tab, and completed prep shows as pinned notes. The tester said one heist can be done with no prep at all, but the escape is much harder and the payout is lower. They also claimed a snowplow entry route was added late and still had placeholder audio. The red flag is that a whiteboard photo with no legible mission names is too easy to stage, and the post never explained how the tester got a phone into the room.

Script 13: The 1998 Carcer Steel Strike

A purported voice-line leak came from a localization string dump. The claim was that the prologue involves a 1998 Carcer steel strike and a botched arson that sets up the modern plot. One mission is called Last Shift. The dump allegedly included lines like "They're not reopening the mill" and "You burned the wrong building." The prologue allegedly ends with a time jump, and the modern protagonist inherits the fallout. The poster said the dump also included a radio news line about a picket line and a line from a union rep asking where the money went. Last Shift appeared alongside a mission prologue zero three string. The red flag is that localization dumps are often faked, the lines are generically gritty, and the poster never showed the file format or the surrounding strings.

Script 14: Cut Vice City Cameo and Isla Verde

A 4chan post claimed to come from a friend on the art team. The claim was that a Vice City cameo was cut from GTA Seven because it tested as distracting. A full Cuba-like island was prototyped but reduced to a mission-only location. The island was internally called Isla Verde and had one smuggling mission before being cut down. The Vice City cameo was allegedly a radio DJ voiceover, not a playable location. The poster also said the island had a small town, a runway, and a dock before it was reduced to a single beach and a warehouse. They claimed the cut happened after a focus test where players wanted to stay on the island instead of returning to the main map. The red flag is that this directly contradicts the Liberty and Carcer map leak while still using Vice City for clout, and the friend on the art team is never named.

Script 15: Pause Menu and Handheld Phone

A blurry phone photo allegedly showed a dev kit pause menu. The tabs were Map, Contacts, Property, Crew, Media, and Settings. The in-game phone is allegedly replaced by a handheld with a pager-style message system for early-story missions. The handheld has a fold-out keyboard animation, and pager messages appear in the 1998 section. The modern section unlocks a smartphone-like device later. The photo allegedly showed a placeholder character named TEST-PROTAG and a mission marker labeled debug-heist-one. The poster claimed the media tab stores radio recordings and photos, and the crew tab is where the heist prep board lives. The red flag is that TEST-PROTAG is exactly what a faker would put on a fake dev menu, and the photo was too blurry to read the tab labels without the poster's captions.

Script 16: Map Size Ratios

A supposed data-miner on Reddit claimed the road network is about one point eight times GTA Six's, but playable landmass is only one point three times because more is water and industrial zones. The map allegedly has three airports and one cargo rail network. The miner claimed to have measured road splines from a leaked manifest. Carcer's industrial zone is allegedly roughly the size of Alderney, and the snowline reduces usable road space in winter. One airport is cargo-only, and the rail network connects the mill, the port, and a freight yard. The miner also said the map has more tunnels than GTA Six because of the snowline. The red flag is that measuring from a leaked manifest is unfalsifiable, the ratios are too tidy, and the post never showed the measurement method or a single spline file.

Script 17: Three-Tier Law Enforcement

A supposed ex-QA tester posted a bullet list. The claim was that separate city police, state troopers, and a federal task force appear after certain story flags. The federal unit uses unmarked cars and surveillance vans, not military vehicles. The federal unit only responds to heat-memory incidents above a threshold and can stake out safehouses. State troopers handle highway pursuits and bridge checkpoints. The system was allegedly cut back because it made free roam too stressful, and the tester said the federal unit was originally going to use roadblocks before that was removed. They also claimed state troopers have a separate radio channel and different dialogue. The red flag is that "cut back because too stressful" is a very believable but unverifiable detail, and the bullet list had no mission names, file names, or dates.

Script 18: Motion-Capture LinkedIn Slip

A LinkedIn profile allegedly listed GTA Seven motion capture performer from 2025 to 2026 before being scrubbed. The claim was that mocap was done at Rockstar Lincoln with dual-protagonist fight choreography and snow-footing animation tests. The profile allegedly listed combat, crowd, and vehicle-interaction mocap, plus a separate snow footing credit. The profile was live for six hours and had one connection to a Rockstar Lincoln animator. The fight choreography involved two-on-one grappling, and the snow footing work allegedly included walking on ice, packed snow, and slush. The poster said the profile also listed a "crowd panic" session and a "vehicle exit" session. The red flag is that this is easy to fake with a throwaway profile and no archived screenshot, and LinkedIn credits are often vague enough to mean almost anything.

Script 19: Internal Date Slip to Late 2029

A supposed production source posted on a private industry Discord. The claim was that GTA Seven was targeting late 2029 internally, then slipped after GTA Six's online rollout. Rockstar is allegedly not announcing anything until GTA Six's second online year is mapped out. The source claimed GTA Seven had a pre-production gate in mid-2026, and the QA build from the first leak was an early technical test, not a content-complete build. The delay was about online integration, not story. A formal announce is allegedly at least two years away. The source also said the map and protagonists were locked before the online delay, and that the QA team was told to focus on streaming and weather. The red flag is that this conveniently explains away the weaknesses in the other leaks, and the Discord post had no verifiable dates or names.

Script 20: Soundtrack Licensing Leak

A now-deleted music-industry post on X claimed Rockstar licensed three unreleased 1990s industrial tracks and several Liberty City punk demos for a story-critical radio station. One station's playlist unlocks only after the 1998 prologue. The station is allegedly called Carcer Steel, and one track is tied to a mission where the player drives through a picket line. The punk demos allegedly came from a Newark label that folded in 2001. The licensing deals allegedly included no-streamer-release clauses, and one track was described as "too raw for streaming." The poster also claimed the station has a DJ who references the strike and then disappears after the time jump. The red flag is that no track names and no label names were given, which makes the whole thing impossible to verify, and the post was deleted before anyone could archive it."""


def parse_scripts(raw: str) -> List[Dict[str, str]]:
    leaks = []
    for m in re.finditer(r'Script \d+:\s*([^\n]+)\n\n(.+?)(?=Script \d+:|$)', raw, re.DOTALL):
        leaks.append({"title": m.group(1).strip(), "text": m.group(2).strip()})
    return leaks


LEAKS = parse_scripts(RAW_SCRIPTS)


def split_leak(text: str):
    parts = re.split(r'(?:The red flag is|What makes people suspicious is)\s+', text, maxsplit=1)
    if len(parts) == 2:
        return parts[0].strip(), parts[1].strip()
    return text.strip(), ""


def chunk_text(text: str, chunk_size: int = 4) -> List[str]:
    if not text.strip():
        return []
    words = text.split()
    return [" ".join(words[i:i + chunk_size]) for i in range(0, len(words), chunk_size)]


# ═══════════════════════ Colors & Fonts ═════════════════
BG_TRANSPARENT = (0, 0, 0, 0)
ACCENT        = (255, 140, 0)       # orange
RED_ACCENT    = (230, 50, 50)       # red
WHITE         = (245, 245, 245)
BLACK         = (0, 0, 0)

def _find_font(size: int, bold: bool = True):
    names = (
        ("arialbd.ttf", "arial.ttf"),
        ("C:/Windows/Fonts/arialbd.ttf", "C:/Windows/Fonts/arial.ttf"),
        ("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
         "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf"),
    )
    for pair in names:
        p = pair[0] if bold else pair[1]
        try:
            return ImageFont.truetype(p, size)
        except (OSError, IOError):
            continue
    return ImageFont.load_default()

FONT_HUGE     = _find_font(140)
FONT_CHUNK    = _find_font(100)
FONT_TITLE    = _find_font(90)
FONT_SMALL    = _find_font(40)

# ═══════════════════════ FFmpeg & Assets ════════════════
def _ffmpeg_exe() -> str:
    import shutil
    exe = shutil.which("ffmpeg")
    if exe:
        return exe
    import imageio_ffmpeg
    return imageio_ffmpeg.get_ffmpeg_exe()

LOGO_IMG = None
if LOGO_PATH.exists():
    try:
        LOGO_IMG = Image.open(LOGO_PATH).convert("RGBA")
        logo_w = 600
        aspect = LOGO_IMG.width / LOGO_IMG.height
        LOGO_IMG = LOGO_IMG.resize((logo_w, int(logo_w / aspect)), Image.Resampling.LANCZOS)
    except Exception as e:
        print(f"⚠ Failed to load LOGO: {e}")

# ═══════════════════════ Drawing Helpers ════════════════
def get_empty_overlay() -> Image.Image:
    return Image.new("RGBA", (WIDTH, HEIGHT), BG_TRANSPARENT)

def draw_logo(img: Image.Image):
    if LOGO_IMG:
        x = (WIDTH - LOGO_IMG.width) // 2
        y = 120 # Below TikTok top UI
        img.paste(LOGO_IMG, (x, y), LOGO_IMG)

def draw_text_centered(draw: ImageDraw.Draw, text: str, font, fill, y_offset: int = 0, shadow: bool = True):
    max_width = WIDTH - 160
    words = text.split()
    lines, curr_line = [], []
    for word in words:
        curr_line.append(word)
        if draw.textbbox((0, 0), " ".join(curr_line), font=font)[2] > max_width:
            curr_line.pop()
            if curr_line: lines.append(" ".join(curr_line))
            curr_line = [word]
    if curr_line: lines.append(" ".join(curr_line))
    wrapped = "\n".join(lines)
    
    bbox = draw.multiline_textbbox((0, 0), wrapped, font=font, align="center")
    tw, th = bbox[2] - bbox[0], bbox[3] - bbox[1]
    
    x = (WIDTH - tw) // 2
    y = (HEIGHT - th) // 2 + y_offset
    
    if shadow:
        draw.multiline_text((x+4, y+4), wrapped, font=font, fill=BLACK, align="center")
    draw.multiline_text((x, y), wrapped, font=font, fill=fill, align="center")

# ═══════════════════════ Slide Generators ═══════════════
def make_short_intro(short_num: int, leak_start: int, leak_end: int, total_leaks: int) -> Image.Image:
    img = get_empty_overlay()
    d = ImageDraw.Draw(img)
    draw_logo(img)

    if leak_start == leak_end:
        subtitle = f"LEAK {leak_start} OF {total_leaks}"
    else:
        subtitle = f"LEAKS {leak_start}–{leak_end}"
    
    draw_text_centered(d, subtitle, FONT_HUGE, ACCENT, y_offset=50)
    draw_text_centered(d, "UNVERIFIED RUMORS", FONT_SMALL, RED_ACCENT, y_offset=250)
    return img

def make_leak_title(leak_num: int, title: str, total_leaks: int) -> Image.Image:
    img = get_empty_overlay()
    d = ImageDraw.Draw(img)
    draw_logo(img)

    label = f"LEAK {leak_num:02d} / {total_leaks:02d}"
    draw_text_centered(d, label, FONT_SMALL, ACCENT, y_offset=-150)
    draw_text_centered(d, title, FONT_TITLE, WHITE, y_offset=0)
    draw_text_centered(d, "UNVERIFIED", FONT_SMALL, RED_ACCENT, y_offset=200)
    return img

def make_chunk_slide(chunk: str, is_red_flag: bool = False) -> Image.Image:
    img = get_empty_overlay()
    d = ImageDraw.Draw(img)
    draw_logo(img)
    color = RED_ACCENT if is_red_flag else WHITE
    draw_text_centered(d, chunk, FONT_CHUNK, color, y_offset=0)
    return img

def make_outro() -> Image.Image:
    img = get_empty_overlay()
    d = ImageDraw.Draw(img)
    draw_logo(img)

    draw_text_centered(d, "FOLLOW FOR MORE", FONT_SMALL, WHITE, y_offset=50)
    draw_text_centered(d, "GTA 7 LEAKS", FONT_HUGE, ACCENT, y_offset=150)
    draw_text_centered(d, "FAKE OR REAL?", FONT_SMALL, RED_ACCENT, y_offset=300)
    return img

# ═══════════════════════ TTS ════════════════════════════
async def _tts_async(text: str, path: Path):
    communicate = edge_tts.Communicate(text, TTS_VOICE)
    await communicate.save(str(path))

def tts_save(text: str, path: Path) -> float:
    temp_mp3 = path.with_suffix(".mp3")
    asyncio.run(_tts_async(text, temp_mp3))
    subprocess.run([
        _ffmpeg_exe(), "-y", "-i", str(temp_mp3),
        "-ar", "24000", "-ac", "1", str(path)
    ], capture_output=True)
    
    with AudioFileClip(str(path)) as clip:
        dur = clip.duration
    if temp_mp3.exists(): temp_mp3.unlink()
    return dur

def make_silence(seconds: float, path: Path):
    subprocess.run([
        _ffmpeg_exe(), "-y", "-f", "lavfi",
        "-i", "anullsrc=r=24000:cl=mono",
        "-t", f"{seconds:.3f}", str(path)
    ], check=True, capture_output=True)


# ═══════════════════════ FFmpeg Render ══════════════════
def render_via_ffmpeg(segments, audio_files, output_path: str, total_duration: float):
    ffmpeg = _ffmpeg_exe()

    def p(pp): return str(pp).replace("\\", "/")

    vlist = Path("temp_video.txt")
    with open(vlist, "w") as f:
        f.write("ffconcat version 1.0\n")
        for img, dur in segments:
            f.write(f"file '{p(img)}'\nduration {dur:.6f}\n")
        if segments:
            f.write(f"file '{p(segments[-1][0])}'\n")
            f.write(f"duration {segments[-1][1]:.6f}\n")

    alist = Path("temp_audio.txt")
    with open(alist, "w") as f:
        f.write("ffconcat version 1.0\n")
        for a in audio_files:
            f.write(f"file '{p(a)}'\n")

    # Added -progress pipe:1 and -nostats so Python can read the progress cleanly
    cmd = [
        ffmpeg, "-y",
        "-stream_loop", "-1", "-i", str(BG_VIDEO_PATH),
        "-f", "concat", "-safe", "0", "-i", str(vlist),
        "-f", "concat", "-safe", "0", "-i", str(alist),
        "-filter_complex",
        "[0:v]scale=1080:1920:force_original_aspect_ratio=increase,crop=1080:1920,fps=30[bg];"
        "[1:v]format=rgba[ov];"
        "[bg][ov]overlay=shortest=1[v]",
        "-map", "[v]", "-map", "2:a",
        "-c:v", "libx264", "-preset", "medium",
        "-crf", "18", "-maxrate", "12M", "-bufsize", "24M",
        "-c:a", "aac", "-b:a", "192k", "-ar", "24000", "-ac", "1",
        "-af", "aresample=async=1",
        "-movflags", "+faststart",
        "-progress", "pipe:1", "-nostats",  # <--- FIXED PROGRESS BAR
        "-t", f"{total_duration:.3f}", output_path
    ]

    process = subprocess.Popen(cmd, stdout=subprocess.PIPE,
                                stderr=subprocess.STDOUT, text=True)
    
    with tqdm(total=total_duration, desc=f"  Rendering {Path(output_path).name}",
              unit="s", ncols=100,
              bar_format="{desc} |{bar}| {n:.1f}/{total:.1f}s") as pbar:
        for line in process.stdout:
            line = line.strip()
            # FFmpeg sends out_time_us (microseconds) and out_time_ms (sometimes ms, sometimes us depending on version)
            if line.startswith("out_time_us=") or line.startswith("out_time_ms="):
                try:
                    # Extract the number and divide by 1,000,000 to get seconds
                    val = int(line.split("=")[1])
                    seconds = val / 1_000_000.0
                    pbar.n = min(seconds, total_duration)
                    pbar.refresh()
                except ValueError:
                    pass
            elif line == "progress=end":
                pbar.n = total_duration
                pbar.refresh()

    process.wait()
    if process.returncode != 0:
        raise RuntimeError("FFmpeg failed.")


# ═══════════════════════ Pipeline ═══════════════════════
def cleanup_temp_files(short_num: int):
    patterns = [f"temp_*_{short_num}.*", f"temp_*_{short_num}_*.*"]
    for pattern in patterns:
        for p in Path(".").glob(pattern):
            if p.is_file():
                try: p.unlink()
                except OSError: pass

def process_short(batch: List[dict], short_num: int, total_shorts: int):
    print(f"\n--- Building GTA 7 Leaks Short {short_num}/{total_shorts} ---")

    intro_silence = Path(f"temp_introsil_{short_num}.wav")
    make_silence(INTRO_DURATION, intro_silence)
    leak_title_silence = Path(f"temp_lt_sil_{short_num}.wav")
    make_silence(LEAK_TITLE_DURATION, leak_title_silence)
    outro_silence = Path(f"temp_outrosil_{short_num}.wav")
    make_silence(OUTRO_DURATION, outro_silence)

    assets = []
    with tqdm(total=len(batch), desc="  1/3 TTS + Chunking", ncols=100) as pbar:
        for i, leak in enumerate(batch):
            claim, red_flag = split_leak(leak["text"])
            
            claim_audio = Path(f"temp_claim_{short_num}_{i}.wav")
            claim_dur = tts_save(claim, claim_audio) if claim.strip() else 0

            rf_audio = None
            rf_dur = 0
            if red_flag.strip():
                rf_audio = Path(f"temp_rf_{short_num}_{i}.wav")
                rf_dur = tts_save(red_flag, rf_audio)

            claim_chunks = chunk_text(claim, 4)
            rf_chunks = chunk_text(red_flag, 4)

            assets.append({
                "title": leak["title"],
                "claim_chunks": claim_chunks,
                "claim_audio": claim_audio,
                "claim_dur": claim_dur,
                "rf_chunks": rf_chunks,
                "rf_audio": rf_audio,
                "rf_dur": rf_dur,
            })
            pbar.update(1)

    all_segments = []
    all_audio = []
    total_dur = 0.0

    with tqdm(total=1 + 2 * len(assets) + 1, desc="  2/3 Baking Overlays", ncols=100) as pbar:
        intro_path = Path(f"temp_intro_{short_num}.png")
        leak_start = (short_num - 1) * LEAKS_PER_SHORT + 1
        leak_end = leak_start + len(batch) - 1
        make_short_intro(short_num, leak_start, leak_end, len(LEAKS)).save(intro_path, "PNG")
        all_segments.append((intro_path, INTRO_DURATION))
        all_audio.append(intro_silence)
        total_dur += INTRO_DURATION
        pbar.update(1)

        for i, a in enumerate(assets):
            lt_path = Path(f"temp_leakt_{short_num}_{i}.png")
            make_leak_title(leak_start + i, a["title"], len(LEAKS)).save(lt_path, "PNG")
            all_segments.append((lt_path, LEAK_TITLE_DURATION))
            all_audio.append(leak_title_silence)
            total_dur += LEAK_TITLE_DURATION

            if a["claim_chunks"]:
                total_chars = sum(len(c) for c in a["claim_chunks"])
                for j, chunk in enumerate(a["claim_chunks"]):
                    chunk_dur = a["claim_dur"] * (len(chunk) / total_chars)
                    img_path = Path(f"temp_claimc_{short_num}_{i}_{j}.png")
                    make_chunk_slide(chunk, is_red_flag=False).save(img_path, "PNG")
                    all_segments.append((img_path, chunk_dur))
                    total_dur += chunk_dur
                all_audio.append(a["claim_audio"])

            if a["rf_chunks"]:
                total_chars = sum(len(c) for c in a["rf_chunks"])
                for j, chunk in enumerate(a["rf_chunks"]):
                    chunk_dur = a["rf_dur"] * (len(chunk) / total_chars)
                    img_path = Path(f"temp_rfc_{short_num}_{i}_{j}.png")
                    make_chunk_slide(chunk, is_red_flag=True).save(img_path, "PNG")
                    all_segments.append((img_path, chunk_dur))
                    total_dur += chunk_dur
                all_audio.append(a["rf_audio"])

            pbar.update(1)

        outro_path = Path(f"temp_outro_{short_num}.png")
        make_outro().save(outro_path, "PNG")
        all_segments.append((outro_path, OUTRO_DURATION))
        all_audio.append(outro_silence)
        total_dur += OUTRO_DURATION
        pbar.update(1)

    out_file = f"gta7_leaks_short_{short_num}.mp4"
    print(f"  Total duration: {total_dur:.1f}s")
    render_via_ffmpeg(all_segments, all_audio, out_file, total_dur)

    cleanup_temp_files(short_num)


def main():
    if not BG_VIDEO_PATH.exists():
        print(f"❌ ERROR: Background video not found at:\n{BG_VIDEO_PATH}")
        print("Please update the path in the script or ensure the file is there.")
        return

    t_start = time.time()

    if len(LEAKS) == 0:
        print("❌ No leaks parsed. Check RAW_SCRIPTS formatting.")
        return

    batches = [LEAKS[i:i + LEAKS_PER_SHORT] for i in range(0, len(LEAKS), LEAKS_PER_SHORT)]

    print(f"GTA 7 Leaks Generator — {len(LEAKS)} leaks across {len(batches)} shorts")
    print(f"Voice: {TTS_VOICE} | {WIDTH}×{HEIGHT} @ {FPS}fps | {LEAKS_PER_SHORT} per short\n")

    for idx, batch in enumerate(batches):
        if not batch:
            continue
        process_short(batch, idx + 1, len(batches))

    print(f"\n✅ All {len(batches)} TikTok shorts generated in {time.time() - t_start:.1f}s!")

if __name__ == "__main__":
    main()