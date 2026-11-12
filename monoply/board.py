"""UK Monopoly board definition (40 tiles, sequential order)."""
from dataclasses import dataclass
from typing import Tuple

N_TILES = 40
GO = 0
JAIL = 10
FREE_PARKING = 20
GO_TO_JAIL = 30


@dataclass(frozen=True)
class Tile:
    index: int
    name: str
    kind: str                 # property | station | utility | tax | card | special
    group: str = ""
    price: int = 0
    rent: Tuple[int, ...] = ()
    house_cost: int = 0
    amount: int = 0

    @property
    def is_ownable(self) -> bool:
        return self.kind in ("property", "station", "utility")


# (name, kind, group, price, rents[0-5], house_cost, tax_amount)
_RAW = [
    ("Go", "go"),
    ("Old Kent Road", "property", "Brown", 60, (2, 10, 30, 90, 160, 250), 50),
    ("Community Chest", "chest"),
    ("Whitechapel Road", "property", "Brown", 60, (4, 20, 60, 180, 320, 450), 50),
    ("Income Tax", "tax", "", 0, (), 0, 200),
    ("Kings Cross Station", "station", "Station", 200),
    ("The Angel, Islington", "property", "Light Blue", 100, (6, 30, 90, 270, 400, 550), 50),
    ("Chance", "chance"),
    ("Euston Road", "property", "Light Blue", 100, (6, 30, 90, 270, 400, 550), 50),
    ("Pentonville Road", "property", "Light Blue", 120, (8, 40, 100, 300, 450, 600), 50),
    ("Jail / Just Visiting", "jail"),
    ("Pall Mall", "property", "Pink", 140, (10, 50, 150, 450, 625, 750), 100),
    ("Electric Company", "utility", "Utility", 150),
    ("Whitehall", "property", "Pink", 140, (10, 50, 150, 450, 625, 750), 100),
    ("Northumberland Avenue", "property", "Pink", 160, (12, 60, 180, 500, 700, 900), 100),
    ("Marylebone Station", "station", "Station", 200),
    ("Bow Street", "property", "Orange", 180, (14, 70, 200, 550, 750, 950), 100),
    ("Community Chest", "chest"),
    ("Marlborough Street", "property", "Orange", 180, (14, 70, 200, 550, 750, 950), 100),
    ("Vine Street", "property", "Orange", 200, (16, 80, 220, 600, 800, 1000), 100),
    ("Free Parking", "freeparking"),
    ("Strand", "property", "Red", 220, (18, 90, 250, 700, 875, 1050), 150),
    ("Chance", "chance"),
    ("Fleet Street", "property", "Red", 220, (18, 90, 250, 700, 875, 1050), 150),
    ("Trafalgar Square", "property", "Red", 240, (20, 100, 300, 750, 925, 1100), 150),
    ("Fenchurch St. Station", "station", "Station", 200),
    ("Leicester Square", "property", "Yellow", 260, (22, 110, 330, 800, 975, 1150), 150),
    ("Coventry Street", "property", "Yellow", 260, (22, 110, 330, 800, 975, 1150), 150),
    ("Water Works", "utility", "Utility", 150),
    ("Piccadilly", "property", "Yellow", 280, (24, 120, 360, 850, 1025, 1200), 150),
    ("Go To Jail", "gotojail"),
    ("Regent Street", "property", "Green", 300, (26, 130, 390, 900, 1100, 1275), 200),
    ("Oxford Street", "property", "Green", 300, (26, 130, 390, 900, 1100, 1275), 200),
    ("Community Chest", "chest"),
    ("Bond Street", "property", "Green", 320, (28, 150, 450, 1000, 1200, 1400), 200),
    ("Liverpool St. Station", "station", "Station", 200),
    ("Chance", "chance"),
    ("Park Lane", "property", "Dark Blue", 350, (35, 175, 500, 1100, 1300, 1500), 200),
    ("Super Tax", "tax", "", 0, (), 0, 100),
    ("Mayfair", "property", "Dark Blue", 400, (50, 200, 600, 1400, 1700, 2000), 200),
]

BOARD = []
for _i, _r in enumerate(_RAW):
    BOARD.append(Tile(
        index=_i,
        name=_r[0],
        kind=_r[1],
        group=_r[2] if len(_r) > 2 else "",
        price=_r[3] if len(_r) > 3 else 0,
        rent=_r[4] if len(_r) > 4 else (),
        house_cost=_r[5] if len(_r) > 5 else 0,
        amount=_r[6] if len(_r) > 6 else 0,
    ))

GROUP_COLORS = {
    "Brown": "#8B5A2B", "Light Blue": "#ADD8E6", "Pink": "#D93A96",
    "Orange": "#F7941D", "Red": "#ED1B24", "Yellow": "#FEF200",
    "Green": "#1FB25A", "Dark Blue": "#0072BB",
    "Station": "#3C3C3C", "Utility": "#8A8A8A",
}

PLAYER_COLORS = ["#E63946", "#457B9D", "#2A9D8F", "#E9C46A"]

# ---------------------------------------------------------------------------
# Movement summaries for Chance / Community Chest cards and board features.
# These mirror the real-card effects used by compute_prior() and the engine.
# (kind, arg)  kind ∈ {move, jail, back3, nearest_station, nearest_utility, none}
# ---------------------------------------------------------------------------
STATIONS = [5, 15, 25, 35]
UTILITIES = [12, 28]

CHANCE_MOVES = [
    ("move", 0), ("move", 24), ("move", 11), ("move", 39),
    ("jail", None), ("back3", None),
    ("nearest_station", None), ("nearest_station", None),
    ("nearest_utility", None),
    ("none", None), ("none", None), ("none", None),
    ("none", None), ("none", None), ("none", None),
    ("none", None),
]

CHEST_MOVES = [
    ("move", 0), ("jail", None),
    ("none", None), ("none", None), ("none", None),
    ("none", None), ("none", None), ("none", None),
    ("none", None), ("none", None), ("none", None),
    ("none", None), ("none", None), ("none", None),
    ("none", None), ("none", None),
]