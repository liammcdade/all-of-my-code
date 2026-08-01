import random
import tkinter as tk
from tqdm import tqdm
from tkinter import ttk
from typing import Dict, List, Tuple

PARTY_COLORS = {
    "Republican": "#E81B23",
    "Democrat": "#3A86D0",
    "Independent": "#8B8B8B",
    "Competitive": "#FFD700",
}

RATING_COLORS = {
    "Safe Republican": "#E81B23",
    "Likely Republican": "#FF6B6B",
    "Lean Republican": "#FF9999",
    "Toss-up": "#000000",
    "Lean Democrat": "#87CEEB",
    "Likely Democrat": "#4A90D9",
    "Safe Democrat": "#3A86D0",
}

STATE_ABBR = [
    "AL", "AK", "AZ", "AR", "CA", "CO", "CT", "DE", "FL", "GA",
    "HI", "ID", "IL", "IN", "IA", "KS", "KY", "LA", "ME", "MD",
    "MA", "MI", "MN", "MS", "MO", "MT", "NE", "NV", "NH", "NJ",
    "NM", "NY", "NC", "ND", "OH", "OK", "OR", "PA", "RI", "SC",
    "SD", "TN", "TX", "UT", "VT", "VA", "WA", "WV", "WI", "WY",
]

STATE_NAMES = {
    "AL": "Alabama", "AK": "Alaska", "AZ": "Arizona", "AR": "Arkansas",
    "CA": "California", "CO": "Colorado", "CT": "Connecticut", "DE": "Delaware",
    "FL": "Florida", "GA": "Georgia", "HI": "Hawaii", "ID": "Idaho",
    "IL": "Illinois", "IN": "Indiana", "IA": "Iowa", "KS": "Kansas",
    "KY": "Kentucky", "LA": "Louisiana", "ME": "Maine", "MD": "Maryland",
    "MA": "Massachusetts", "MI": "Michigan", "MN": "Minnesota", "MS": "Mississippi",
    "MO": "Missouri", "MT": "Montana", "NE": "Nebraska", "NV": "Nevada",
    "NH": "New Hampshire", "NJ": "New Jersey", "NM": "New Mexico", "NY": "New York",
    "NC": "North Carolina", "ND": "North Dakota", "OH": "Ohio", "OK": "Oklahoma",
    "OR": "Oregon", "PA": "Pennsylvania", "RI": "Rhode Island", "SC": "South Carolina",
    "SD": "South Dakota", "TN": "Tennessee", "TX": "Texas", "UT": "Utah",
    "VT": "Vermont", "VA": "Virginia", "WA": "Washington", "WV": "West Virginia",
    "WI": "Wisconsin", "WY": "Wyoming",
}

HOUSE_CONTROL = {
    "AL": "Republican", "AK": "Republican", "AZ": "Republican", "AR": "Republican",
    "CA": "Democrat", "CO": "Democrat", "CT": "Democrat", "DE": "Democrat",
    "FL": "Republican", "GA": "Republican", "HI": "Democrat", "ID": "Republican",
    "IL": "Democrat", "IN": "Republican", "IA": "Republican", "KS": "Republican",
    "KY": "Republican", "LA": "Republican", "ME": "Democrat", "MD": "Democrat",
    "MA": "Democrat", "MI": "Republican", "MN": "Democrat", "MS": "Republican",
    "MO": "Republican", "MT": "Republican", "NE": "Republican", "NV": "Democrat",
    "NH": "Democrat", "NJ": "Democrat", "NM": "Democrat", "NY": "Democrat",
    "NC": "Republican", "ND": "Republican", "OH": "Republican", "OK": "Republican",
    "OR": "Democrat", "PA": "Republican", "RI": "Democrat", "SC": "Republican",
    "SD": "Republican", "TN": "Republican", "TX": "Republican", "UT": "Republican",
    "VT": "Democrat", "VA": "Democrat", "WA": "Democrat", "WV": "Republican",
    "WI": "Republican", "WY": "Republican",
}

SENATE_CONTROL = {
    "AL": "Republican", "AK": "Republican", "AZ": "Republican", "AR": "Republican",
    "CA": "Democrat", "CO": "Democrat", "CT": "Democrat", "DE": "Democrat",
    "FL": "Republican", "GA": "Republican", "HI": "Democrat", "ID": "Republican",
    "IL": "Democrat", "IN": "Republican", "IA": "Republican", "KS": "Republican",
    "KY": "Republican", "LA": "Republican", "ME": "Independent", "MD": "Democrat",
    "MA": "Democrat", "MI": "Democrat", "MN": "Democrat", "MS": "Republican",
    "MO": "Republican", "MT": "Republican", "NE": "Republican", "NV": "Democrat",
    "NH": "Democrat", "NJ": "Democrat", "NM": "Democrat", "NY": "Democrat",
    "NC": "Republican", "ND": "Republican", "OH": "Republican", "OK": "Republican",
    "OR": "Democrat", "PA": "Republican", "RI": "Democrat", "SC": "Republican",
    "SD": "Republican", "TN": "Republican", "TX": "Republican", "UT": "Republican",
    "VT": "Independent", "VA": "Democrat", "WA": "Democrat", "WV": "Republican",
    "WI": "Republican", "WY": "Republican",
}

GOV_CONTROL = {
    "AL": "Republican", "AK": "Republican", "AZ": "Republican", "AR": "Republican",
    "CA": "Democrat", "CO": "Democrat", "CT": "Democrat", "DE": "Democrat",
    "FL": "Republican", "GA": "Republican", "HI": "Democrat", "ID": "Republican",
    "IL": "Democrat", "IN": "Republican", "IA": "Republican", "KS": "Republican",
    "KY": "Republican", "LA": "Republican", "ME": "Democrat", "MD": "Democrat",
    "MA": "Democrat", "MI": "Democrat", "MN": "Democrat", "MS": "Republican",
    "MO": "Republican", "MT": "Republican", "NE": "Republican", "NV": "Republican",
    "NH": "Republican", "NJ": "Democrat", "NM": "Democrat", "NY": "Democrat",
    "NC": "Republican", "ND": "Republican", "OH": "Republican", "OK": "Republican",
    "OR": "Democrat", "PA": "Democrat", "RI": "Democrat", "SC": "Republican",
    "SD": "Republican", "TN": "Republican", "TX": "Republican", "UT": "Republican",
    "VT": "Republican", "VA": "Republican", "WA": "Democrat", "WV": "Republican",
    "WI": "Democrat", "WY": "Republican",
}

BATTLEGROUND = [
    "AZ", "GA", "NV", "PA", "WI", "MI", "NC", "MT", "FL", "TX",
    "ME", "NE", "NH", "VA", "CO", "KS",
]

SENATE_UP_2026 = [
    "AK", "AL", "AR", "CO", "DE", "FL", "GA", "IA", "ID", "IL",
    "KS", "KY", "LA", "MA", "ME", "MI", "MN", "MS", "MT", "NC",
    "NE", "NH", "NJ", "NM", "OH", "OK", "OR", "RI", "SC", "SD",
    "TN", "TX", "VA",
]

SENATE_RATINGS: Dict[str, Tuple[str, float, str]] = {
    "AL": ("Safe Republican", 96.0, "Republican"),
    "AR": ("Safe Republican", 96.0, "Republican"),
    "ID": ("Safe Republican", 93.0, "Republican"),
    "KY": ("Safe Republican", 94.0, "Republican"),
    "LA": ("Safe Republican", 94.0, "Republican"),
    "MS": ("Safe Republican", 93.0, "Republican"),
    "OK": ("Safe Republican", 97.0, "Republican"),
    "SD": ("Safe Republican", 96.0, "Republican"),
    "TN": ("Safe Republican", 96.0, "Republican"),
    "FL": ("Likely Republican", 86.0, "Republican"),
    "WV": ("Safe Republican", 97.0, "Republican"),
    "KS": ("Likely Republican", 84.0, "Republican"),
    "MT": ("Likely Republican", 78.0, "Republican"),
    "SC": ("Likely Republican", 88.0, "Republican"),
    "NE": ("Lean Republican", 71.0, "Republican"),
    "AK": ("Toss-up", 55.0, "Democrat"),
    "IA": ("Toss-up", 60.0, "Republican"),
    "OH": ("Toss-up", 53.0, "Democrat"),
    "TX": ("Toss-up", 55.0, "Republican"),
    "NH": ("Likely Democrat", 85.0, "Democrat"),
    "ME": ("Lean Democrat", 64.0, "Democrat"),
    "MI": ("Lean Democrat", 71.0, "Democrat"),
    "CO": ("Safe Democrat", 96.0, "Democrat"),
    "DE": ("Safe Democrat", 97.0, "Democrat"),
    "GA": ("Safe Democrat", 90.0, "Democrat"),
    "IL": ("Safe Democrat", 96.0, "Democrat"),
    "MA": ("Safe Democrat", 97.0, "Democrat"),
    "MN": ("Safe Democrat", 93.0, "Democrat"),
    "NC": ("Safe Democrat", 90.0, "Democrat"),
    "NJ": ("Safe Democrat", 96.0, "Democrat"),
    "NM": ("Safe Democrat", 96.0, "Democrat"),
    "OR": ("Safe Democrat", 97.0, "Democrat"),
    "RI": ("Safe Democrat", 95.0, "Democrat"),
    "VA": ("Safe Democrat", 95.0, "Democrat"),
}

GOV_RATINGS: Dict[str, Tuple[str, float, str]] = {
    "WI": ("Toss-up", 55.0, "Democrat"),
    "CA": ("Safe Democrat", 95.0, "Democrat"),
    "CO": ("Safe Democrat", 94.0, "Democrat"),
    "NY": ("Safe Democrat", 93.0, "Democrat"),
    "TX": ("Likely Republican", 89.0, "Republican"),
    "MN": ("Safe Democrat", 93.0, "Democrat"),
    "AZ": ("Likely Democrat", 81.0, "Democrat"),
    "OH": ("Toss-up", 51.0, "Republican"),
    "GA": ("Toss-up", 59.0, "Democrat"),
    "NV": ("Toss-up", 58.0, "Democrat"),
    "IA": ("Lean Democrat", 64.0, "Democrat"),
    "AK": ("Toss-up", 53.0, "Republican"),
    "FL": ("Likely Republican", 84.0, "Republican"),
    "MI": ("Likely Democrat", 84.0, "Democrat"),
    "SC": ("Safe Republican", 90.0, "Republican"),
    "AL": ("Safe Republican", 92.0, "Republican"),
    "MA": ("Safe Democrat", 93.0, "Democrat"),
    "OR": ("Likely Democrat", 88.0, "Democrat"),
    "KY": ("Likely Republican", 81.0, "Republican"),
    "PA": ("Safe Democrat", 94.0, "Democrat"),
    "ME": ("Safe Democrat", 90.0, "Democrat"),
    "NH": ("Likely Republican", 82.0, "Republican"),
    "NE": ("Likely Republican", 81.0, "Republican"),
    "NM": ("Likely Democrat", 88.0, "Democrat"),
    "RI": ("Likely Democrat", 88.0, "Democrat"),
    "OK": ("Safe Republican", 93.0, "Republican"),
    "VT": ("Likely Republican", 86.0, "Republican"),
    "TN": ("Safe Republican", 95.0, "Republican"),
    "SD": ("Safe Republican", 94.0, "Republican"),
    "WY": ("Safe Republican", 96.0, "Republican"),
    "ID": ("Safe Republican", 96.0, "Republican"),
    "IL": ("Safe Democrat", 96.0, "Democrat"),
    "HI": ("Safe Democrat", 96.0, "Democrat"),
    "DE": ("Safe Democrat", 91.0, "Democrat"),
    "CT": ("Safe Democrat", 92.0, "Democrat"),
    "AR": ("Safe Republican", 99.0, "Republican"),
    "MD": ("Safe Democrat", 96.0, "Democrat"),
}

HOUSE_TOTAL = 435
SENATE_TOTAL = 100
SENATE_UP = 34
GOV_TOTAL = 50
GOV_UP_2026 = 36


# Format: state -> [(district, party, win_pct, favored_party), ...]
HOUSE_SEATS_DATA: Dict[str, List[Tuple[int, str, float, str]]] = {
    "AK": [(1, "Republican", 74.0, "Republican")],
    "AL": [(1, "Republican", 95.0, "Republican"), (2, "Republican", 73.0, "Republican"), (3, "Republican", 95.0, "Republican"), (4, "Republican", 96.0, "Republican"), (5, "Republican", 91.0, "Republican"), (6, "Republican", 95.0, "Republican"), (7, "Democrat", 96.0, "Democrat")],
    "AR": [(1, "Republican", 97.0, "Republican"), (2, "Republican", 90.0, "Republican"), (3, "Republican", 95.0, "Republican"), (4, "Republican", 95.0, "Republican")],
    "AZ": [(1, "Democrat", 74.0, "Democrat"), (2, "Republican", 69.0, "Republican"), (3, "Democrat", 92.0, "Democrat"), (4, "Democrat", 91.0, "Democrat"), (5, "Republican", 90.0, "Republican"), (6, "Democrat", 83.0, "Democrat"), (7, "Democrat", 95.0, "Democrat"), (8, "Republican", 86.0, "Republican"), (9, "Republican", 91.0, "Republican")],
    "CA": [(1, "Democrat", 96.0, "Democrat"), (2, "Democrat", 95.0, "Democrat"), (3, "Democrat", 94.0, "Democrat"), (4, "Democrat", 100.0, "Democrat"), (5, "Republican", 90.0, "Republican"), (6, "Democrat", 95.0, "Democrat"), (7, "Democrat", 100.0, "Democrat"), (8, "Democrat", 90.0, "Democrat"), (9, "Democrat", 92.0, "Democrat"), (10, "Democrat", 96.0, "Democrat"), (11, "Democrat", 100.0, "Democrat"), (12, "Democrat", 100.0, "Democrat"), (13, "Democrat", 92.0, "Democrat"), (14, "Democrat", 100.0, "Democrat"), (15, "Democrat", 95.0, "Democrat"), (16, "Democrat", 94.0, "Democrat"), (17, "Democrat", 98.0, "Democrat"), (18, "Democrat", 96.0, "Democrat"), (19, "Democrat", 96.0, "Democrat"), (20, "Republican", 96.0, "Republican"), (21, "Democrat", 92.0, "Democrat"), (22, "Democrat", 80.0, "Democrat"), (23, "Republican", 91.0, "Republican"), (24, "Democrat", 97.0, "Democrat"), (25, "Democrat", 91.0, "Democrat"), (26, "Democrat", 98.0, "Democrat"), (27, "Democrat", 93.0, "Democrat"), (28, "Democrat", 90.0, "Democrat"), (29, "Democrat", 100.0, "Democrat"), (30, "Democrat", 95.0, "Democrat"), (31, "Democrat", 96.0, "Democrat"), (32, "Democrat", 95.0, "Democrat"), (33, "Democrat", 93.0, "Democrat"), (34, "Democrat", 100.0, "Democrat"), (35, "Democrat", 97.0, "Democrat"), (36, "Democrat", 93.0, "Democrat"), (37, "Democrat", 100.0, "Democrat"), (38, "Democrat", 94.0, "Democrat"), (39, "Democrat", 92.0, "Democrat"), (40, "Republican", 100.0, "Republican"), (41, "Democrat", 93.0, "Democrat"), (42, "Democrat", 97.0, "Democrat"), (43, "Democrat", 97.0, "Democrat"), (44, "Democrat", 97.0, "Democrat"), (45, "Democrat", 89.0, "Democrat"), (46, "Democrat", 87.0, "Democrat"), (47, "Democrat", 94.0, "Democrat"), (48, "Democrat", 88.0, "Democrat"), (49, "Democrat", 98.0, "Democrat"), (50, "Democrat", 95.0, "Democrat"), (51, "Democrat", 97.0, "Democrat"), (52, "Democrat", 79.0, "Democrat")],
    "CO": [(1, "Democrat", 94.0, "Democrat"), (2, "Democrat", 96.0, "Democrat"), (3, "Republican", 73.0, "Republican"), (4, "Republican", 70.0, "Republican"), (5, "Republican", 74.0, "Republican"), (6, "Democrat", 96.0, "Democrat"), (7, "Democrat", 97.0, "Democrat"), (8, "Democrat", 74.0, "Democrat")],
    "CT": [(1, "Democrat", 94.0, "Democrat"), (2, "Democrat", 96.0, "Democrat"), (3, "Democrat", 96.0, "Democrat"), (4, "Democrat", 96.0, "Democrat"), (5, "Democrat", 78.0, "Democrat")],
    "DE": [(1, "Democrat", 91.0, "Democrat")],
    "FL": [(1, "Republican", 92.0, "Republican"), (2, "Republican", 93.0, "Republican"), (3, "Republican", 93.0, "Republican"), (4, "Republican", 85.0, "Republican"), (5, "Republican", 93.0, "Republican"), (6, "Republican", 93.0, "Republican"), (7, "Republican", 71.0, "Republican"), (8, "Republican", 89.0, "Republican"), (9, "Republican", 79.0, "Republican"), (10, "Democrat", 95.0, "Democrat"), (11, "Republican", 86.0, "Republican"), (12, "Republican", 85.0, "Republican"), (13, "Republican", 74.0, "Republican"), (14, "Democrat", 60.0, "Democrat"), (15, "Republican", 87.0, "Republican"), (16, "Republican", 81.0, "Republican"), (17, "Republican", 93.0, "Republican"), (18, "Republican", 92.0, "Republican"), (19, "Republican", 92.0, "Republican"), (20, "Democrat", 96.0, "Democrat"), (21, "Republican", 90.0, "Republican"), (22, "Republican", 68.0, "Republican"), (23, "Democrat", 94.0, "Democrat"), (24, "Democrat", 97.0, "Democrat"), (25, "Democrat", 63.0, "Democrat"), (26, "Republican", 90.0, "Republican"), (27, "Republican", 85.0, "Republican"), (28, "Republican", 88.0, "Republican")],
    "GA": [(1, "Republican", 90.0, "Republican"), (2, "Democrat", 96.0, "Democrat"), (3, "Republican", 94.0, "Republican"), (4, "Democrat", 97.0, "Democrat"), (5, "Democrat", 98.0, "Democrat"), (6, "Democrat", 92.0, "Democrat"), (7, "Republican", 91.0, "Republican"), (8, "Republican", 92.0, "Republican"), (9, "Republican", 95.0, "Republican"), (10, "Republican", 93.0, "Republican"), (11, "Republican", 94.0, "Republican"), (12, "Republican", 86.0, "Republican"), (13, "Democrat", 95.0, "Democrat"), (14, "Republican", 95.0, "Republican")],
    "HI": [(1, "Democrat", 97.0, "Democrat"), (2, "Democrat", 95.0, "Democrat")],
    "IA": [(1, "Democrat", 77.0, "Democrat"), (2, "Republican", 61.0, "Republican"), (3, "Democrat", 73.0, "Democrat"), (4, "Republican", 91.0, "Republican")],
    "ID": [(1, "Republican", 96.0, "Republican"), (2, "Republican", 94.0, "Republican")],
    "IL": [(1, "Democrat", 90.0, "Democrat"), (2, "Democrat", 97.0, "Democrat"), (3, "Democrat", 97.0, "Democrat"), (4, "Democrat", 94.0, "Democrat"), (5, "Democrat", 97.0, "Democrat"), (6, "Democrat", 93.0, "Democrat"), (7, "Democrat", 97.0, "Democrat"), (8, "Democrat", 93.0, "Democrat"), (9, "Democrat", 95.0, "Democrat"), (10, "Democrat", 97.0, "Democrat"), (11, "Democrat", 93.0, "Democrat"), (12, "Republican", 93.0, "Republican"), (13, "Democrat", 96.0, "Democrat"), (14, "Democrat", 94.0, "Democrat"), (15, "Republican", 94.0, "Republican"), (16, "Republican", 91.0, "Republican"), (17, "Democrat", 89.0, "Democrat")],
    "IN": [(1, "Democrat", 90.0, "Democrat"), (2, "Republican", 91.0, "Republican"), (3, "Republican", 96.0, "Republican"), (4, "Republican", 92.0, "Republican"), (5, "Republican", 89.0, "Republican"), (6, "Republican", 96.0, "Republican"), (7, "Democrat", 94.0, "Democrat"), (8, "Republican", 96.0, "Republican"), (9, "Republican", 93.0, "Republican")],
    "KS": [(1, "Republican", 93.0, "Republican"), (2, "Republican", 91.0, "Republican"), (3, "Democrat", 91.0, "Democrat"), (4, "Republican", 92.0, "Republican")],
    "KY": [(1, "Republican", 96.0, "Republican"), (2, "Republican", 94.0, "Republican"), (3, "Democrat", 94.0, "Democrat"), (4, "Republican", 93.0, "Republican"), (5, "Republican", 97.0, "Republican"), (6, "Republican", 77.0, "Republican")],
    "LA": [(1, "Republican", 96.0, "Republican"), (2, "Democrat", 96.0, "Democrat"), (3, "Republican", 96.0, "Republican"), (4, "Republican", 94.0, "Republican"), (5, "Republican", 94.0, "Republican"), (6, "Republican", 93.0, "Republican")],
    "MA": [(1, "Democrat", 99.0, "Democrat"), (2, "Democrat", 97.0, "Democrat"), (3, "Democrat", 92.0, "Democrat"), (4, "Democrat", 91.0, "Democrat"), (5, "Democrat", 96.0, "Democrat"), (6, "Democrat", 93.0, "Democrat"), (7, "Democrat", 99.0, "Democrat"), (8, "Democrat", 97.0, "Democrat"), (9, "Democrat", 96.0, "Democrat")],
    "MD": [(1, "Republican", 87.0, "Republican"), (2, "Democrat", 95.0, "Democrat"), (3, "Democrat", 98.0, "Democrat"), (4, "Democrat", 91.0, "Democrat"), (5, "Democrat", 91.0, "Democrat"), (6, "Democrat", 92.0, "Democrat"), (7, "Democrat", 96.0, "Democrat"), (8, "Democrat", 96.0, "Democrat")],
    "ME": [(1, "Democrat", 96.0, "Democrat"), (2, "Republican", 68.0, "Republican")],
    "MI": [(1, "Republican", 93.0, "Republican"), (2, "Republican", 95.0, "Republican"), (3, "Democrat", 88.0, "Democrat"), (4, "Republican", 69.0, "Republican"), (5, "Republican", 93.0, "Republican"), (6, "Democrat", 91.0, "Democrat"), (7, "Democrat", 63.0, "Democrat"), (8, "Democrat", 88.0, "Democrat"), (9, "Republican", 96.0, "Republican"), (10, "Democrat", 65.0, "Democrat"), (11, "Democrat", 95.0, "Democrat"), (12, "Democrat", 98.0, "Democrat"), (13, "Democrat", 98.0, "Democrat")],
    "MN": [(1, "Republican", 80.0, "Republican"), (2, "Democrat", 92.0, "Democrat"), (3, "Democrat", 90.0, "Democrat"), (4, "Democrat", 94.0, "Democrat"), (5, "Democrat", 91.0, "Democrat"), (6, "Republican", 93.0, "Republican"), (7, "Republican", 94.0, "Republican"), (8, "Republican", 84.0, "Republican")],
    "MO": [(1, "Democrat", 93.0, "Democrat"), (2, "Republican", 81.0, "Republican"), (3, "Republican", 94.0, "Republican"), (4, "Republican", 90.0, "Republican"), (5, "Republican", 87.0, "Republican"), (6, "Republican", 98.0, "Republican"), (7, "Republican", 98.0, "Republican"), (8, "Republican", 98.0, "Republican")],
    "MS": [(1, "Republican", 96.0, "Republican"), (2, "Democrat", 92.0, "Democrat"), (3, "Republican", 95.0, "Republican"), (4, "Republican", 96.0, "Republican")],
    "MT": [(1, "Republican", 65.0, "Republican"), (2, "Republican", 94.0, "Republican")],
    "NC": [(1, "Democrat", 58.0, "Democrat"), (2, "Democrat", 96.0, "Democrat"), (3, "Republican", 91.0, "Republican"), (4, "Democrat", 99.0, "Democrat"), (5, "Republican", 92.0, "Republican"), (6, "Republican", 86.0, "Republican"), (7, "Republican", 81.0, "Republican"), (8, "Republican", 89.0, "Republican"), (9, "Republican", 80.0, "Republican"), (10, "Republican", 90.0, "Republican"), (11, "Democrat", 52.0, "Democrat"), (12, "Democrat", 95.0, "Democrat"), (13, "Republican", 86.0, "Republican"), (14, "Republican", 84.0, "Republican")],
    "ND": [(1, "Republican", 95.0, "Republican")],
    "NE": [(1, "Republican", 90.0, "Republican"), (2, "Democrat", 87.0, "Democrat"), (3, "Republican", 98.0, "Republican")],
    "NH": [(1, "Democrat", 89.0, "Democrat"), (2, "Democrat", 95.0, "Democrat")],
    "NJ": [(1, "Democrat", 94.0, "Democrat"), (2, "Republican", 87.0, "Republican"), (3, "Democrat", 92.0, "Democrat"), (4, "Republican", 95.0, "Republican"), (5, "Democrat", 92.0, "Democrat"), (6, "Democrat", 93.0, "Democrat"), (7, "Democrat", 82.0, "Democrat"), (8, "Democrat", 96.0, "Democrat"), (9, "Democrat", 91.0, "Democrat"), (10, "Democrat", 98.0, "Democrat"), (11, "Democrat", 96.0, "Democrat"), (12, "Democrat", 96.0, "Democrat")],
    "NM": [(1, "Democrat", 95.0, "Democrat"), (2, "Democrat", 88.0, "Democrat"), (3, "Democrat", 90.0, "Democrat")],
    "NV": [(1, "Democrat", 91.0, "Democrat"), (2, "Republican", 83.0, "Republican"), (3, "Democrat", 87.0, "Democrat"), (4, "Democrat", 87.0, "Democrat")],
    "NY": [(1, "Republican", 83.0, "Republican"), (2, "Republican", 89.0, "Republican"), (3, "Democrat", 83.0, "Democrat"), (4, "Democrat", 90.0, "Democrat"), (5, "Democrat", 97.0, "Democrat"), (6, "Democrat", 98.0, "Democrat"), (7, "Democrat", 98.0, "Democrat"), (8, "Democrat", 96.0, "Democrat"), (9, "Democrat", 92.0, "Democrat"), (10, "Democrat", 98.0, "Democrat"), (11, "Republican", 93.0, "Republican"), (12, "Democrat", 99.0, "Democrat"), (13, "Democrat", 98.0, "Democrat"), (14, "Democrat", 99.0, "Democrat"), (15, "Democrat", 96.0, "Democrat"), (16, "Democrat", 91.0, "Democrat"), (17, "Democrat", 69.0, "Democrat"), (18, "Democrat", 95.0, "Democrat"), (19, "Democrat", 87.0, "Democrat"), (20, "Democrat", 95.0, "Democrat"), (21, "Republican", 83.0, "Republican"), (22, "Democrat", 94.0, "Democrat"), (23, "Republican", 90.0, "Republican"), (24, "Republican", 89.0, "Republican"), (25, "Democrat", 96.0, "Democrat"), (26, "Democrat", 97.0, "Democrat")],
    "OH": [(1, "Democrat", 88.0, "Democrat"), (2, "Republican", 91.0, "Republican"), (3, "Democrat", 98.0, "Democrat"), (4, "Republican", 94.0, "Republican"), (5, "Republican", 92.0, "Republican"), (6, "Republican", 92.0, "Republican"), (7, "Democrat", 56.0, "Democrat"), (8, "Republican", 89.0, "Republican"), (9, "Democrat", 75.0, "Democrat"), (10, "Republican", 88.0, "Republican"), (11, "Democrat", 94.0, "Democrat"), (12, "Republican", 92.0, "Republican"), (13, "Democrat", 90.0, "Democrat"), (14, "Republican", 94.0, "Republican"), (15, "Republican", 76.0, "Republican")],
    "OK": [(1, "Republican", 88.0, "Republican"), (2, "Republican", 96.0, "Republican"), (3, "Republican", 97.0, "Republican"), (4, "Republican", 96.0, "Republican"), (5, "Republican", 89.0, "Republican")],
    "OR": [(1, "Democrat", 90.0, "Democrat"), (2, "Republican", 96.0, "Republican"), (3, "Democrat", 97.0, "Democrat"), (4, "Democrat", 97.0, "Democrat"), (5, "Democrat", 92.0, "Democrat"), (6, "Democrat", 97.0, "Democrat")],
    "PA": [(1, "Republican", 60.0, "Republican"), (2, "Democrat", 99.0, "Democrat"), (3, "Democrat", 99.0, "Democrat"), (4, "Democrat", 94.0, "Democrat"), (5, "Democrat", 93.0, "Democrat"), (6, "Democrat", 91.0, "Democrat"), (7, "Democrat", 71.0, "Democrat"), (8, "Democrat", 65.0, "Democrat"), (9, "Republican", 94.0, "Republican"), (10, "Democrat", 76.0, "Democrat"), (11, "Republican", 91.0, "Republican"), (12, "Democrat", 96.0, "Democrat"), (13, "Republican", 95.0, "Republican"), (14, "Republican", 95.0, "Republican"), (15, "Republican", 92.0, "Republican"), (16, "Republican", 88.0, "Republican"), (17, "Democrat", 91.0, "Democrat")],
    "RI": [(1, "Democrat", 97.0, "Democrat"), (2, "Democrat", 95.0, "Democrat")],
    "SC": [(1, "Republican", 76.0, "Republican"), (2, "Republican", 88.0, "Republican"), (3, "Republican", 98.0, "Republican"), (4, "Republican", 93.0, "Republican"), (5, "Republican", 93.0, "Republican"), (6, "Democrat", 95.0, "Democrat"), (7, "Republican", 92.0, "Republican")],
    "SD": [(1, "Republican", 95.0, "Republican")],
    "TN": [(1, "Republican", 96.0, "Republican"), (2, "Republican", 95.0, "Republican"), (3, "Republican", 94.0, "Republican"), (4, "Republican", 94.0, "Republican"), (5, "Republican", 86.0, "Republican"), (6, "Republican", 95.0, "Republican"), (7, "Republican", 92.0, "Republican"), (8, "Republican", 88.0, "Republican"), (9, "Republican", 86.0, "Republican")],
    "TX": [(1, "Republican", 94.0, "Republican"), (2, "Republican", 91.0, "Republican"), (3, "Republican", 95.0, "Republican"), (4, "Republican", 94.0, "Republican"), (5, "Republican", 94.0, "Republican"), (6, "Republican", 94.0, "Republican"), (7, "Democrat", 95.0, "Democrat"), (8, "Republican", 95.0, "Republican"), (9, "Republican", 81.0, "Republican"), (10, "Republican", 90.0, "Republican"), (11, "Republican", 94.0, "Republican"), (12, "Republican", 91.0, "Republican"), (13, "Republican", 96.0, "Republican"), (14, "Republican", 94.0, "Republican"), (15, "Democrat", 53.0, "Democrat"), (16, "Democrat", 97.0, "Democrat"), (17, "Republican", 91.0, "Republican"), (18, "Democrat", 98.0, "Democrat"), (19, "Republican", 95.0, "Republican"), (20, "Democrat", 96.0, "Democrat"), (21, "Republican", 92.0, "Republican"), (22, "Republican", 90.0, "Republican"), (23, "Democrat", 50.0, "Democrat"), (24, "Republican", 90.0, "Republican"), (25, "Republican", 92.0, "Republican"), (26, "Republican", 89.0, "Republican"), (27, "Republican", 92.0, "Republican"), (28, "Democrat", 85.0, "Democrat"), (29, "Democrat", 95.0, "Democrat"), (30, "Democrat", 97.0, "Democrat"), (31, "Republican", 90.0, "Republican"), (32, "Republican", 82.0, "Republican"), (33, "Democrat", 99.0, "Democrat"), (34, "Democrat", 77.0, "Democrat"), (35, "Republican", 58.0, "Republican"), (36, "Republican", 92.0, "Republican"), (37, "Democrat", 97.0, "Democrat"), (38, "Republican", 88.0, "Republican")],
    "UT": [(1, "Democrat", 93.0, "Democrat"), (2, "Republican", 95.0, "Republican"), (3, "Republican", 95.0, "Republican"), (4, "Republican", 95.0, "Republican")],
    "VA": [(1, "Democrat", 50.0, "Democrat"), (2, "Democrat", 79.0, "Democrat"), (3, "Democrat", 95.0, "Democrat"), (4, "Democrat", 64.0, "Democrat"), (5, "Republican", 89.0, "Republican"), (6, "Republican", 92.0, "Republican"), (7, "Democrat", 95.0, "Democrat"), (8, "Democrat", 97.0, "Democrat"), (9, "Republican", 96.0, "Republican"), (10, "Democrat", 95.0, "Democrat"), (11, "Democrat", 98.0, "Democrat")],
    "VT": [(1, "Democrat", 99.0, "Democrat")],
    "WA": [(1, "Democrat", 96.0, "Democrat"), (2, "Democrat", 99.0, "Democrat"), (3, "Democrat", 84.0, "Democrat"), (4, "Republican", 91.0, "Republican"), (5, "Republican", 83.0, "Republican"), (6, "Democrat", 96.0, "Democrat"), (7, "Democrat", 98.0, "Democrat"), (8, "Democrat", 94.0, "Democrat"), (9, "Democrat", 90.0, "Democrat"), (10, "Democrat", 97.0, "Democrat")],
    "WI": [(1, "Republican", 73.0, "Republican"), (2, "Democrat", 95.0, "Democrat"), (3, "Democrat", 66.0, "Democrat"), (4, "Democrat", 98.0, "Democrat"), (5, "Republican", 92.0, "Republican"), (6, "Republican", 91.0, "Republican"), (7, "Republican", 91.0, "Republican"), (8, "Republican", 86.0, "Republican")],
    "WV": [(1, "Republican", 93.0, "Republican"), (2, "Republican", 96.0, "Republican")],
    "WY": [(1, "Republican", 95.0, "Republican")],
}


def solved_pct_from_probs(probs: List[float]) -> float:
    product = 1.0
    for p in probs:
        product *= p
    return product * 100.0


def simulate_house_control(trials: int = 100000) -> Tuple[float, float]:
    rep_seats_list = []
    for seats in HOUSE_SEATS_DATA.values():
        for _, party, win_pct, _ in seats:
            prob = win_pct / 100.0
            rep_seats_list.append(prob if party == "Republican" else 1.0 - prob)

    rep_wins = 0
    dem_wins = 0
    ties = 0
    for _ in range(trials):
        seats = sum(1 for p in rep_seats_list if random.random() < p)
        if seats > 218:
            rep_wins += 1
        elif seats < 218:
            dem_wins += 1
        else:
            ties += 1

    total = trials
    rep_pct = (rep_wins / total) * 100.0
    dem_pct = (dem_wins / total) * 100.0
    return rep_pct, dem_pct


def senate_control_probabilities() -> Tuple[float, float]:
    probs = []
    for abbr in SENATE_UP_2026:
        if abbr in SENATE_RATINGS:
            _, win_pct, favored = SENATE_RATINGS[abbr]
            if favored == "Republican":
                probs.append(win_pct / 100.0)
            else:
                probs.append(1.0 - win_pct / 100.0)
        else:
            probs.append(0.5)

    rep_wins = 0
    dem_wins = 0
    ties = 0
    for _ in range(trials):
        seats = sum(1 for p in probs if random.random() < p)
        if seats > 50:
            rep_wins += 1
        elif seats < 50:
            dem_wins += 1
        else:
            ties += 1

    total = trials
    rep_pct = (rep_wins / total) * 100.0
    dem_pct = (dem_wins / total) * 100.0
    return rep_pct, dem_pct


def simulate_governor_control(trials: int = 100000) -> Tuple[float, float]:
    probs = []
    for abbr in STATE_ABBR:
        if abbr in GOV_RATINGS:
            _, win_pct, favored = GOV_RATINGS[abbr]
            if favored == "Republican":
                probs.append(win_pct / 100.0)
            else:
                probs.append(1.0 - win_pct / 100.0)
        else:
            probs.append(0.5)

    rep_wins = 0
    dem_wins = 0
    ties = 0
    for _ in range(trials):
        seats = sum(1 for p in probs if random.random() < p)
        if seats > 25:
            rep_wins += 1
        elif seats < 25:
            dem_wins += 1
        else:
            ties += 1

    total = trials
    rep_pct = (rep_wins / total) * 100.0
    dem_pct = (dem_wins / total) * 100.0
    return rep_pct, dem_pct


def house_control_probabilities() -> Tuple[float, float, float]:
    rep_seats_probs = []
    for seats in HOUSE_SEATS_DATA.values():
        for _, party, win_pct, _ in seats:
            prob = win_pct / 100.0
            if party == "Republican":
                rep_seats_probs.append(prob)
            else:
                rep_seats_probs.append(1.0 - prob)

    rep_wins = 0
    dem_wins = 0
    ties = 0
    trials = 100000
    for _ in tqdm(range(trials), desc="House sim"):
        seats = sum(1 for p in rep_seats_probs if random.random() < p)
        if seats > 218:
            rep_wins += 1
        elif seats < 218:
            dem_wins += 1
        else:
            ties += 1

    total = trials
    rep_pct = (rep_wins / total) * 100.0
    dem_pct = (dem_wins / total) * 100.0
    tie_pct = (ties / total) * 100.0
    return rep_pct, dem_pct, tie_pct


def senate_control_probabilities() -> Tuple[float, float, float]:
    probs = []
    current_republican = 53
    republican_up = 0
    for abbr in SENATE_UP_2026:
        if abbr in SENATE_RATINGS:
            _, win_pct, favored = SENATE_RATINGS[abbr]
            if favored == "Republican":
                probs.append(win_pct / 100.0)
                republican_up += 1
            else:
                probs.append(1.0 - win_pct / 100.0)
        else:
            probs.append(0.5)

    rep_wins = 0
    dem_wins = 0
    ties = 0
    trials = 100000
    for _ in tqdm(range(trials), desc="Senate sim"):
        won = sum(1 for p in probs if random.random() < p)
        final_republican = (current_republican - republican_up) + won
        if final_republican > 50:
            rep_wins += 1
        elif final_republican < 50:
            dem_wins += 1
        else:
            ties += 1

    total = trials
    rep_pct = (rep_wins / total) * 100.0
    dem_pct = (dem_wins / total) * 100.0
    tie_pct = (ties / total) * 100.0
    return rep_pct, dem_pct, tie_pct


def governor_control_probabilities() -> Tuple[float, float, float]:
    probs = []
    for abbr in STATE_ABBR:
        if abbr in GOV_RATINGS:
            _, win_pct, favored = GOV_RATINGS[abbr]
            probs.append(win_pct / 100.0 if favored == "Republican" else 1.0 - win_pct / 100.0)
        else:
            probs.append(0.5)

    rep_wins = 0
    dem_wins = 0
    ties = 0
    trials = 100000
    for _ in tqdm(range(trials), desc="Governor sim"):
        seats = sum(1 for p in probs if random.random() < p)
        if seats > 25:
            rep_wins += 1
        elif seats < 25:
            dem_wins += 1
        else:
            ties += 1

    total = trials
    rep_pct = (rep_wins / total) * 100.0
    dem_pct = (dem_wins / total) * 100.0
    tie_pct = (ties / total) * 100.0
    return rep_pct, dem_pct, tie_pct


def combined_control_probabilities() -> Tuple[float, float, float]:
    house_probs = []
    for seats in HOUSE_SEATS_DATA.values():
        for _, party, win_pct, _ in seats:
            prob = win_pct / 100.0
            house_probs.append(prob if party == "Republican" else 1.0 - prob)

    senate_probs = []
    current_republican = 53
    republican_up = 0
    for abbr in SENATE_UP_2026:
        if abbr in SENATE_RATINGS:
            _, win_pct, favored = SENATE_RATINGS[abbr]
            if favored == "Republican":
                senate_probs.append(win_pct / 100.0)
                republican_up += 1
            else:
                senate_probs.append(1.0 - win_pct / 100.0)
        else:
            senate_probs.append(0.5)

    rep_wins = 0
    dem_wins = 0
    ties = 0
    trials = 100000
    for _ in tqdm(range(trials), desc="Unified sim"):
        house_seats = sum(1 for p in house_probs if random.random() < p)
        senate_won = sum(1 for p in senate_probs if random.random() < p)
        final_republican = (current_republican - republican_up) + senate_won
        house_rep = house_seats > 218
        house_dem = house_seats < 218
        senate_rep = final_republican > 50
        senate_dem = final_republican < 50
        if house_rep and senate_rep:
            rep_wins += 1
        elif house_dem and senate_dem:
            dem_wins += 1
        else:
            ties += 1

    total = trials
    rep_pct = (rep_wins / total) * 100.0
    dem_pct = (dem_wins / total) * 100.0
    tie_pct = (ties / total) * 100.0
    return rep_pct, dem_pct, tie_pct


def senate_solved_pct() -> float:
    probs = []
    for abbr in SENATE_UP_2026:
        if abbr in SENATE_RATINGS:
            _, win_pct, _ = SENATE_RATINGS[abbr]
        else:
            win_pct = 0
        probs.append(win_pct / 100.0 if win_pct > 0 else 1.0)
    return solved_pct_from_probs(probs)


def house_solved_pct() -> float:
    probs = []
    for seats in HOUSE_SEATS_DATA.values():
        for _, _, win_pct, _ in seats:
            probs.append(win_pct / 100.0)
    return solved_pct_from_probs(probs)


def governor_solved_pct() -> float:
    probs = []
    for abbr in STATE_ABBR:
        if abbr in GOV_RATINGS:
            _, win_pct, _ = GOV_RATINGS[abbr]
        else:
            win_pct = 0
        probs.append(win_pct / 100.0 if win_pct > 0 else 1.0)
    return solved_pct_from_probs(probs)


class RaceBox(tk.LabelFrame):
    def __init__(self, parent, title: str, races: List[Tuple[str, str, float, str]], fg: str = "#000"):
        super().__init__(parent, text=title, padx=10, pady=10)
        self.configure(bg="white")
        canvas = tk.Canvas(self, bg="white", highlightthickness=0)
        scrollbar = ttk.Scrollbar(self, orient="vertical", command=canvas.yview)
        inner = tk.Frame(canvas, bg="white")

        inner.bind("<Configure>", lambda e: canvas.configure(scrollregion=canvas.bbox("all")))
        canvas.create_window((0, 0), window=inner, anchor="nw")
        canvas.configure(yscrollcommand=scrollbar.set)

        canvas.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")

        for label, party, win_pct, favored in races:
            text = f"{label} - {party}: {win_pct:.1f}% ({favored})"
            color = PARTY_COLORS.get(party, RATING_COLORS.get(party, PARTY_COLORS["Competitive"]))
            lbl = tk.Label(inner, text=text, fg=color, bg="white", anchor="w", font=("Segoe UI", 9))
            lbl.pack(fill="x", pady=1)


class MainApp(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("2026 U.S. Midterms Dashboard")
        self.geometry("1400x800")
        self.configure(bg="#f8f9fa")

        container = tk.Frame(self, bg="#f8f9fa")
        container.pack(fill="both", expand=True, padx=20, pady=20)

        header = tk.Label(container, text="2026 U.S. Midterms", font=("Segoe UI", 22, "bold"), bg="#f8f9fa")
        header.pack(anchor="w", pady=(0, 10))

        solved_frame = tk.Frame(container, bg="#f8f9fa")
        solved_frame.pack(fill="x", pady=(0, 20))

        house_pct = house_solved_pct()
        senate_pct = senate_solved_pct()
        gov_pct = governor_solved_pct()

        house_rep_ctrl, house_dem_ctrl, house_tie_ctrl = house_control_probabilities()
        senate_rep_ctrl, senate_dem_ctrl, senate_tie_ctrl = senate_control_probabilities()
        gov_rep_ctrl, gov_dem_ctrl, gov_tie_ctrl = governor_control_probabilities()

        def format_pct(pct: float) -> str:
            if pct >= 0.01:
                return f"{pct:.2f}%"
            return f"{pct:.2e}%"

        for label, pct in [("House", house_pct), ("Senate", senate_pct), ("Governors", gov_pct)]:
            box = tk.Frame(solved_frame, bg="white", padx=30, pady=20, relief="raised", bd=1)
            box.pack(side="left", expand=True, fill="both", padx=5)
            tk.Label(box, text=label, font=("Segoe UI", 12, "bold"), bg="white").pack()
            tk.Label(box, text=format_pct(pct), font=("Segoe UI", 18, "bold"), bg="white", fg="#333").pack()
            tk.Label(box, text="Solved", font=("Segoe UI", 10), bg="white", fg="#666").pack()

        control_frame = tk.Frame(container, bg="#f8f9fa")
        control_frame.pack(fill="x", pady=(0, 20))

        for label, rep_pct, dem_pct, tie_pct in [
            ("House Control", house_rep_ctrl, house_dem_ctrl, house_tie_ctrl),
            ("Senate Control", senate_rep_ctrl, senate_dem_ctrl, senate_tie_ctrl),
            ("Governor Control", gov_rep_ctrl, gov_dem_ctrl, gov_tie_ctrl),
        ]:
            box = tk.Frame(control_frame, bg="white", padx=30, pady=15, relief="raised", bd=1)
            box.pack(side="left", expand=True, fill="both", padx=5)
            tk.Label(box, text=label, font=("Segoe UI", 12, "bold"), bg="white").pack()
            tk.Label(box, text=f"Republican: {rep_pct:.1f}%", font=("Segoe UI", 11), bg="white", fg=PARTY_COLORS["Republican"]).pack()
            tk.Label(box, text=f"Democrat: {dem_pct:.1f}%", font=("Segoe UI", 11), bg="white", fg=PARTY_COLORS["Democrat"]).pack()
            tie_text = "Tie" if label in ("House Control", "Senate Control") else ""
            tk.Label(box, text=f"{tie_text}: {tie_pct:.1f}%", font=("Segoe UI", 11), bg="white", fg="#000000").pack()

        boxes_frame = tk.Frame(container, bg="#f8f9fa")
        boxes_frame.pack(fill="both", expand=True)
        boxes_frame.columnconfigure(0, weight=1)
        boxes_frame.columnconfigure(1, weight=1)
        boxes_frame.columnconfigure(2, weight=1)

        house_races = []
        for abbr in STATE_ABBR:
            if abbr in HOUSE_SEATS_DATA:
                for district, party, win_pct, favored in HOUSE_SEATS_DATA[abbr]:
                    house_races.append((f"{abbr}-{district}", party, win_pct, favored))
        house_box = RaceBox(boxes_frame, "House", house_races)
        house_box.grid(row=0, column=0, sticky="nsew", padx=5)

        senate_races = []
        for abbr in SENATE_UP_2026:
            if abbr in SENATE_RATINGS:
                rating, win_pct, favored = SENATE_RATINGS[abbr]
            else:
                rating, win_pct, favored = "Safe Democrat", 0, "Democrat"
            senate_races.append((abbr, rating, float(win_pct), favored))
        senate_box = RaceBox(boxes_frame, "Senate", senate_races)
        senate_box.grid(row=0, column=1, sticky="nsew", padx=5)

        gov_races = []
        for abbr in STATE_ABBR:
            if abbr in GOV_RATINGS:
                rating, win_pct, favored = GOV_RATINGS[abbr]
            else:
                rating, win_pct, favored = "Safe Democrat", 0.0, "Democrat"
            gov_races.append((abbr, rating, float(win_pct), favored))
        gov_box = RaceBox(boxes_frame, "Governors", gov_races)
        gov_box.grid(row=0, column=2, sticky="nsew", padx=5)


def format_pct(pct: float) -> str:
    if pct >= 0.01:
        return f"{pct:.2f}%"
    return f"{pct:.2e}%"


class LoadingScreen(tk.Toplevel):
    def __init__(self, parent):
        super().__init__(parent)
        self.title("Loading")
        self.geometry("500x150")
        self.configure(bg="#f8f9fa")
        self.transient(parent)
        self.grab_set()

        tk.Label(self, text="Running 2026 Midterms Simulations...", font=("Segoe UI", 12, "bold"), bg="#f8f9fa").pack(pady=20)

        self.progress = ttk.Progressbar(self, length=400, mode="determinate")
        self.progress.pack(pady=10)

        self.percent_label = tk.Label(self, text="0%", font=("Segoe UI", 10), bg="#f8f9fa")
        self.percent_label.pack()

        self.progress["value"] = 0
        self.percent_label.config(text="0%")
        self.update()

    def set_progress(self, value):
        self.progress["value"] = value
        self.percent_label.config(text=f"{int(value)}%")
        self.update_idletasks()


class MainApp(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("2026 U.S. Midterms Dashboard")
        self.geometry("1400x800")
        self.configure(bg="#f8f9fa")

        container = tk.Frame(self, bg="#f8f9fa")
        container.pack(fill="both", expand=True, padx=20, pady=20)

        header = tk.Label(container, text="2026 U.S. Midterms", font=("Segoe UI", 22, "bold"), bg="#f8f9fa")
        header.pack(anchor="w", pady=(0, 10))

        solved_frame = tk.Frame(container, bg="#f8f9fa")
        solved_frame.pack(fill="x", pady=(0, 20))

        house_pct = house_solved_pct()
        senate_pct = senate_solved_pct()
        gov_pct = governor_solved_pct()

        house_rep_ctrl, house_dem_ctrl, house_tie_ctrl = house_control_probabilities()
        senate_rep_ctrl, senate_dem_ctrl, senate_tie_ctrl = senate_control_probabilities()
        gov_rep_ctrl, gov_dem_ctrl, gov_tie_ctrl = governor_control_probabilities()
        unified_rep_ctrl, unified_dem_ctrl, unified_tie_ctrl = combined_control_probabilities()

        control_frame = tk.Frame(container, bg="#f8f9fa")
        control_frame.pack(fill="x", pady=(0, 20))

        for label, rep_pct, dem_pct, tie_pct in [
            ("House Control", house_rep_ctrl, house_dem_ctrl, house_tie_ctrl),
            ("Senate Control", senate_rep_ctrl, senate_dem_ctrl, senate_tie_ctrl),
            ("Unified Control", unified_rep_ctrl, unified_dem_ctrl, unified_tie_ctrl),
            ("Governor Control", gov_rep_ctrl, gov_dem_ctrl, gov_tie_ctrl),
        ]:
            box = tk.Frame(control_frame, bg="white", padx=30, pady=15, relief="raised", bd=1)
            box.pack(side="left", expand=True, fill="both", padx=5)
            tk.Label(box, text=label, font=("Segoe UI", 12, "bold"), bg="white").pack()
            tk.Label(box, text=f"Republican: {rep_pct:.1f}%", font=("Segoe UI", 11), bg="white", fg=PARTY_COLORS["Republican"]).pack()
            tk.Label(box, text=f"Democrat: {dem_pct:.1f}%", font=("Segoe UI", 11), bg="white", fg=PARTY_COLORS["Democrat"]).pack()
            tie_text = "Tie" if label in ("House Control", "Senate Control") else "No Unified Control" if label == "Unified Control" else "No Governor Control"
            tk.Label(box, text=f"{tie_text}: {tie_pct:.1f}%", font=("Segoe UI", 11), bg="white", fg="#000000").pack()

        boxes_frame = tk.Frame(container, bg="#f8f9fa")
        boxes_frame.pack(fill="both", expand=True)
        boxes_frame.columnconfigure(0, weight=1)
        boxes_frame.columnconfigure(1, weight=1)
        boxes_frame.columnconfigure(2, weight=1)

        house_races = []
        for abbr in STATE_ABBR:
            if abbr in HOUSE_SEATS_DATA:
                for district, party, win_pct, favored in HOUSE_SEATS_DATA[abbr]:
                    house_races.append((f"{abbr}-{district}", party, win_pct, favored))
        house_box = RaceBox(boxes_frame, "House", house_races)
        house_box.grid(row=0, column=0, sticky="nsew", padx=5)

        senate_races = []
        for abbr in SENATE_UP_2026:
            if abbr in SENATE_RATINGS:
                rating, win_pct, favored = SENATE_RATINGS[abbr]
            else:
                rating, win_pct, favored = "Safe Democrat", 0, "Democrat"
            senate_races.append((abbr, rating, float(win_pct), favored))
        senate_box = RaceBox(boxes_frame, "Senate", senate_races)
        senate_box.grid(row=0, column=1, sticky="nsew", padx=5)

        gov_races = []
        for abbr in STATE_ABBR:
            if abbr in GOV_RATINGS:
                rating, win_pct, favored = GOV_RATINGS[abbr]
            else:
                rating, win_pct, favored = "Safe Democrat", 0.0, "Democrat"
            gov_races.append((abbr, rating, float(win_pct), favored))
        gov_box = RaceBox(boxes_frame, "Governors", gov_races)
        gov_box.grid(row=0, column=2, sticky="nsew", padx=5)

        for label, pct in [("House", house_pct), ("Senate", senate_pct), ("Governors", gov_pct)]:
            box = tk.Frame(solved_frame, bg="white", padx=30, pady=20, relief="raised", bd=1)
            box.pack(side="left", expand=True, fill="both", padx=5)
            tk.Label(box, text=label, font=("Segoe UI", 12, "bold"), bg="white").pack()
            tk.Label(box, text=format_pct(pct), font=("Segoe UI", 18, "bold"), bg="white", fg="#333").pack()
            tk.Label(box, text="Solved", font=("Segoe UI", 10), bg="white", fg="#666").pack()


def main():
    app = MainApp()
    app.mainloop()


if __name__ == "__main__":
    main()
