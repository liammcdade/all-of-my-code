import pygame
import ctypes
import time
import os
from datetime import datetime
from zoneinfo import ZoneInfo

# ============================================================
# SETTINGS
# ============================================================

BACKGROUND = r"C:\Users\liam\Documents\GitHub\all-of-my-code\grand-theft-auto-vi-3840x2160-26939.jpg"
# Countdown target
TARGET_DATE = datetime(2026, 11, 19, 0, 0, 0)

# UK timezone
UK_TZ = ZoneInfo("Europe/London")

# Progress percentage range
START_DATE = datetime(2023, 12, 4, 22, 0, 0, tzinfo=UK_TZ)
END_DATE = datetime(2026, 11, 1, 0, 0, 0, tzinfo=UK_TZ)

# Text
COUNTDOWN_FONT_SIZE = 90
LABEL_FONT_SIZE = 20
DATE_FONT_SIZE = 32
PERCENTAGE_FONT_SIZE = 36

# Darkness over wallpaper
OVERLAY_ALPHA = 105

# ============================================================
# WINDOWS API
# ============================================================

user32 = ctypes.windll.user32

FindWindow = user32.FindWindowW
FindWindowEx = user32.FindWindowExW
SendMessageTimeout = user32.SendMessageTimeoutW
SetParent = user32.SetParent
SetWindowPos = user32.SetWindowPos
GetSystemMetrics = user32.GetSystemMetrics

SM_CXSCREEN = 0
SM_CYSCREEN = 1

HWND_BOTTOM = 1

SWP_NOSIZE = 0x0001
SWP_NOMOVE = 0x0002
SWP_NOACTIVATE = 0x0010
SWP_SHOWWINDOW = 0x0040

# ============================================================
# FIND WINDOWS DESKTOP WORKER
# ============================================================

def get_desktop_worker():

    # Get Program Manager
    progman = FindWindow("Progman", None)

    # Tell Windows to create the WorkerW behind desktop icons
    result = ctypes.c_ulong()

    SendMessageTimeout(
        progman,
        0x052C,
        0,
        0,
        0,
        1000,
        ctypes.byref(result)
    )

    workerw = None

    def enum_windows(hwnd, lParam):

        nonlocal workerw

        shell_view = FindWindowEx(
            hwnd,
            0,
            "SHELLDLL_DefView",
            None
        )

        if shell_view:
            workerw = FindWindowEx(
                0,
                hwnd,
                "WorkerW",
                None
            )

        return True

    EnumWindowsProc = ctypes.WINFUNCTYPE(
        ctypes.c_bool,
        ctypes.c_void_p,
        ctypes.c_void_p
    )

    user32.EnumWindows(
        EnumWindowsProc(enum_windows),
        0
    )

    return workerw


# ============================================================
# COUNTDOWN
# ============================================================

def get_countdown():

    now = datetime.now()

    difference = TARGET_DATE - now

    if difference.total_seconds() <= 0:
        return 0, 0, 0, 0

    total_seconds = int(difference.total_seconds())

    days = total_seconds // 86400
    hours = (total_seconds % 86400) // 3600
    minutes = (total_seconds % 3600) // 60
    seconds = total_seconds % 60

    return days, hours, minutes, seconds


def get_progress_percentage():

    now = datetime.now(tz=UK_TZ)

    elapsed = (now - START_DATE).total_seconds()
    total = (END_DATE - START_DATE).total_seconds()

    if elapsed <= 0:
        return 0.0

    if elapsed >= total:
        return 100.0

    return (elapsed / total) * 100.0


# ============================================================
# LOAD IMAGE
# ============================================================

if not os.path.exists(BACKGROUND):
    raise FileNotFoundError(
        f"Could not find {BACKGROUND}"
    )

pygame.init()

screen_width = GetSystemMetrics(SM_CXSCREEN)
screen_height = GetSystemMetrics(SM_CYSCREEN)

screen = pygame.display.set_mode(
    (screen_width, screen_height),
    pygame.NOFRAME
)

pygame.display.set_caption("Live Wallpaper")

# Get Pygame window handle
hwnd = pygame.display.get_wm_info()["window"]

# ============================================================
# PUT WINDOW BEHIND DESKTOP ICONS
# ============================================================

workerw = get_desktop_worker()

if workerw:

    SetParent(hwnd, workerw)

    SetWindowPos(
        hwnd,
        HWND_BOTTOM,
        0,
        0,
        screen_width,
        screen_height,
        SWP_NOACTIVATE | SWP_SHOWWINDOW
    )

else:
    print("Could not find Windows desktop WorkerW.")

# ============================================================
# LOAD AND SCALE WALLPAPER
# ============================================================

background = pygame.image.load(BACKGROUND).convert()

image_width, image_height = background.get_size()

scale = max(
    screen_width / image_width,
    screen_height / image_height
)

new_width = int(image_width * scale)
new_height = int(image_height * scale)

background = pygame.transform.smoothscale(
    background,
    (new_width, new_height)
)

# Center/crop image
x = (new_width - screen_width) // 2
y = (new_height - screen_height) // 2

background = background.subsurface(
    (x, y, screen_width, screen_height)
)

# ============================================================
# FONTS
# ============================================================

countdown_font = pygame.font.SysFont(
    "Arial",
    COUNTDOWN_FONT_SIZE,
    bold=True
)

label_font = pygame.font.SysFont(
    "Arial",
    LABEL_FONT_SIZE,
    bold=False
)

date_font = pygame.font.SysFont(
    "Arial",
    DATE_FONT_SIZE,
    bold=True
)

percentage_font = pygame.font.SysFont(
    "Arial",
    PERCENTAGE_FONT_SIZE,
    bold=True
)

# ============================================================
# DARK OVERLAY
# ============================================================

overlay = pygame.Surface(
    (screen_width, screen_height)
)

overlay.fill((0, 0, 0))
overlay.set_alpha(OVERLAY_ALPHA)

# ============================================================
# MAIN LOOP
# ============================================================

clock = pygame.time.Clock()

running = True

while running:

    for event in pygame.event.get():

        if event.type == pygame.QUIT:
            running = False

        # Press ESC to quit
        if event.type == pygame.KEYDOWN:
            if event.key == pygame.K_ESCAPE:
                running = False

    # --------------------------------------------------------
    # DRAW WALLPAPER
    # --------------------------------------------------------

    screen.blit(background, (0, 0))

    # Darken background
    screen.blit(overlay, (0, 0))

    # --------------------------------------------------------
    # COUNTDOWN
    # --------------------------------------------------------

    days, hours, minutes, seconds = get_countdown()

    countdown_text = (
        f"{days:02d} : "
        f"{hours:02d} : "
        f"{minutes:02d} : "
        f"{seconds:02d}"
    )

    countdown_surface = countdown_font.render(
        countdown_text,
        True,
        (255, 255, 255)
    )

    countdown_rect = countdown_surface.get_rect(
        center=(
            screen_width // 2,
            int(screen_height * 0.48)
        )
    )

    screen.blit(
        countdown_surface,
        countdown_rect
    )

    # --------------------------------------------------------
    # DATE
    # --------------------------------------------------------

    date_text = TARGET_DATE.strftime(
        "%B %d, %Y"
    ).upper()

    date_surface = date_font.render(
        date_text,
        True,
        (255, 80, 40)
    )

    date_rect = date_surface.get_rect(
        center=(
            screen_width // 2,
            int(screen_height * 0.63)
        )
    )

    screen.blit(
        date_surface,
        date_rect
    )

    # --------------------------------------------------------
    # PROGRESS PERCENTAGE
    # --------------------------------------------------------

    percentage = get_progress_percentage()

    percentage_text = f"{percentage:.6f}% COMPLETE"

    percentage_surface = percentage_font.render(
        percentage_text,
        True,
        (255, 255, 255)
    )

    percentage_rect = percentage_surface.get_rect(
        center=(
            screen_width // 2,
            int(screen_height * 0.70)
        )
    )

    screen.blit(
        percentage_surface,
        percentage_rect
    )

    pygame.display.flip()

    # 30 FPS is more than enough for a countdown
    clock.tick(30)


pygame.quit()