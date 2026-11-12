"""
Farmer's League Index Calculator (FLI*)

Improved formula that separates league dominance from cup noise.

Components:
    - Premier League index  L = (38/G) * D_L * sqrt(1 + m_bar/10 + GD_bar/50)
    - Cup index (FA Cup, League Cup)  C = D_C * sqrt(1 + Delta_bar/3)
    - Combined  FLI* = w_L*L + w_FA*C_FA + w_LC*C_LC (default 0.60, 0.25, 0.15)

Where D_c is a concentration/dominance score in [0, 1]:
    D_c = 0.7 * max_i(p_i) + 0.3 * HHI_norm
    HHI_norm = (HHI - 1/S) / (1 - 1/S)

This replaces the old single sqrt(margin + cbrt(GD)) term, which mixed
one-match cup finals with 38-match leagues and used an unscaled cbrt(GD).
"""

from pathlib import Path
from collections import Counter, defaultdict
import csv
import math
import re
from typing import Dict, List, Tuple, Optional


SEASON_RE = re.compile(r"(\d{4})-(\d{4})")


def season_from_filename(p: Path) -> str:
    """Extract a season string (e.g. '2011-2012') from a filename."""
    name = p.name
    m = SEASON_RE.search(name)
    if m:
        return f"{m.group(1)}-{m.group(2)}"
    m2 = re.search(r"(\d{4})_(\d{4})", name)
    if m2:
        return f"{m2.group(1)}-{m2.group(2)}"
    return p.stem


def read_league_csvs(paths: List[Path]) -> List[dict]:
    """
    Read Premier League match CSVs and derive champion, points margin
    (1st vs 2nd), and champion goal difference for each season.
    """
    by_season: Dict[str, dict] = {}
    for p in paths:
        season = season_from_filename(p)
        table: defaultdict = defaultdict(lambda: {"pts": 0, "gf": 0, "ga": 0})

        def _open_with_encoding(path: Path):
            """Try utf-8-sig with replacement, then fall back to latin-1."""
            for enc in ("utf-8-sig", "latin-1"):
                try:
                    f = path.open(newline="", encoding=enc, errors="replace")
                    return f
                except Exception:
                    continue
            return path.open(newline="", encoding="latin-1", errors="replace")

        with _open_with_encoding(p) as f:
            reader = csv.DictReader(f)
            for row in reader:
                if row.get("Div") != "E0":
                    continue
                try:
                    hg = int(row["FTHG"])
                    ag = int(row["FTAG"])
                except (KeyError, ValueError):
                    continue

                home = row["HomeTeam"].strip()
                away = row["AwayTeam"].strip()

                table[home]["gf"] += hg
                table[home]["ga"] += ag
                table[away]["gf"] += ag
                table[away]["ga"] += hg

                if hg > ag:
                    table[home]["pts"] += 3
                elif hg < ag:
                    table[away]["pts"] += 3
                else:
                    table[home]["pts"] += 1
                    table[away]["pts"] += 1

        standings: List[Tuple[str, int, int, int]] = []
        for team, s in table.items():
            standings.append((team, s["pts"], s["gf"] - s["ga"], s["gf"]))

        standings.sort(key=lambda x: (x[1], x[2], x[3]), reverse=True)

        if len(standings) < 2:
            continue

        winner, pts, gd, _ = standings[0]
        runner_pts = standings[1][1]

        by_season[season] = {
            "season": season,
            "winner": winner,
            "margin": pts - runner_pts,
            "winner_gd": gd,
        }

    return [by_season[k] for k in sorted(by_season)]


def dominance_stats(
    winners: List[str],
    margins: Optional[List[float]] = None,
    lam: float = 0.7,
) -> dict:
    """
    Compute a dominance/concentration score for a set of winners.

    D_c = lam * max_share + (1 - lam) * HHI_norm

    where HHI_norm is the normalised Herfindahl index in [0, 1].
    """
    n = len(winners)
    if n == 0:
        raise ValueError("No winners data provided")
    counts = Counter(winners)
    max_share = max(counts.values()) / n
    hhi = sum((c / n) ** 2 for c in counts.values())
    hhi_min = 1 / n
    hhi_norm = (hhi - hhi_min) / (1 - hhi_min) if n > 1 else 0.0
    dominance = lam * max_share + (1 - lam) * hhi_norm

    out: dict = {
        "n": n,
        "counts": counts,
        "max_share": max_share,
        "hhi": hhi,
        "hhi_norm": hhi_norm,
        "dominance": dominance,
    }
    if margins is not None:
        out["avg_final_margin"] = sum(margins) / len(margins)

    return out


def league_index(
    seasons: List[dict],
    games_per_season: int = 38,
    margin_scale: float = 10.0,
    gd_scale: float = 50.0,
) -> Tuple[float, dict]:
    """
    Premier League component:

    L = (38 / G) * D_L * sqrt(1 + m_bar / margin_scale + GD_bar / gd_scale)

    Uses max(m, 0) and max(GD, 0) to avoid invalid square roots.
    """
    if not seasons:
        raise ValueError("No league seasons provided")

    winners = [s["winner"] for s in seasons]
    st = dominance_stats(winners)

    avg_margin = sum(max(s["margin"], 0) for s in seasons) / len(seasons)
    avg_gd = sum(max(s["winner_gd"], 0) for s in seasons) / len(seasons)

    games_factor = 38 / games_per_season
    idx = games_factor * st["dominance"] * math.sqrt(
        1 + avg_margin / margin_scale + avg_gd / gd_scale
    )

    st["avg_margin"] = avg_margin
    st["avg_winner_gd"] = avg_gd
    return idx, st


def margin_from_score(score: str) -> float:
    """Extract absolute goal margin from a score string like '2-1' or '2–1'.
    Drawn finals / penalty wins count as margin 0."""
    if not score:
        return 0.0
    m = re.search(r"(\d+)\s*[–-]\s*(\d+)", score)
    if not m:
        return 0.0
    return float(abs(int(m.group(1)) - int(m.group(2))))


def cup_index(
    finals: List[Tuple[str, str, str, str]],
    margin_scale: float = 3.0,
) -> Tuple[float, dict]:
    """
    Cup component (FA Cup, League Cup):

    C = D_C * sqrt(1 + Delta_bar / margin_scale)

    where Delta_bar is the average final goal margin.
    Drawn finals / penalty wins count as margin 0.

    Each entry in `finals` is (season, winner, runner, score_string).
    """
    if not finals:
        raise ValueError("No cup finals provided")

    winners = [w for _, w, _, _ in finals]
    margins = [margin_from_score(sc) for _, _, _, sc in finals]
    st = dominance_stats(winners, margins)
    sqrt_term = 1 + st["avg_final_margin"] / margin_scale
    idx = st["dominance"] * math.sqrt(sqrt_term)
    return idx, st


def combined_index(
    league_seasons: List[dict],
    fa_finals: List[Tuple[str, str, str, str]],
    lc_finals: List[Tuple[str, str, str, str]],
    weights: Tuple[float, float, float] = (0.60, 0.25, 0.15),
) -> Tuple[float, Tuple[float, float, float]]:
    """
    Combined Farmer's League Index:

    FLI* = w_L * L + w_FA * C_FA + w_LC * C_LC
    """
    L, _ = league_index(league_seasons)
    F, _ = cup_index(fa_finals)
    C, _ = cup_index(lc_finals)
    total = weights[0] * L + weights[1] * F + weights[2] * C
    return total, (L, F, C)


# ---------------------------------------------------------------------------
# Last-15-seasons window: 2011-12 through 2025-26
# The 2011 League Cup final belongs to the 2010-11 season, so it is excluded
# when aligning to the 2011-12 start of the window.
# ---------------------------------------------------------------------------

FA_CUP_FINAL = [
    ("2011-2012", "Chelsea", "Liverpool", "2-1"),
    ("2012-2013", "Wigan Athletic", "Manchester City", "1-0"),
    ("2013-2014", "Arsenal", "Hull City", "3-2"),
    ("2014-2015", "Arsenal", "Aston Villa", "4-0"),
    ("2015-2016", "Manchester United", "Crystal Palace", "2-1"),
    ("2016-2017", "Arsenal", "Chelsea", "2-1"),
    ("2017-2018", "Chelsea", "Manchester United", "1-0"),
    ("2018-2019", "Manchester City", "Watford", "6-0"),
    ("2019-2020", "Arsenal", "Chelsea", "2-1"),
    ("2020-2021", "Leicester City", "Chelsea", "1-0"),
    ("2021-2022", "Liverpool", "Chelsea", "0-0"),
    ("2022-2023", "Manchester City", "Manchester United", "2-1"),
    ("2023-2024", "Manchester United", "Manchester City", "2-1"),
    ("2024-2025", "Crystal Palace", "Manchester City", "1-0"),
    ("2025-2026", "Manchester City", "Chelsea", "1-0"),
]

LEAGUE_CUP_FINAL = [
    ("2011-2012", "Liverpool", "Cardiff City", "2-2"),
    ("2012-2013", "Swansea City", "Bradford City", "5-0"),
    ("2013-2014", "Manchester City", "Sunderland", "3-1"),
    ("2014-2015", "Chelsea", "Tottenham Hotspur", "2-0"),
    ("2015-2016", "Manchester City", "Liverpool", "1-1"),
    ("2016-2017", "Manchester United", "Southampton", "3-2"),
    ("2017-2018", "Manchester City", "Arsenal", "3-0"),
    ("2018-2019", "Manchester City", "Chelsea", "0-0"),
    ("2019-2020", "Manchester City", "Aston Villa", "2-1"),
    ("2020-2021", "Manchester City", "Tottenham Hotspur", "1-0"),
    ("2021-2022", "Liverpool", "Chelsea", "0-0"),
    ("2022-2023", "Manchester United", "Newcastle United", "2-0"),
    ("2023-2024", "Liverpool", "Chelsea", "1-0"),
    ("2024-2025", "Newcastle United", "Liverpool", "2-1"),
    ("2025-2026", "Manchester City", "Arsenal", "2-0"),
]


if __name__ == "__main__":
    data_dir = (
        "C:\\Users\\liam\\Documents\\GitHub\\Footballdata"
        "\\data\\ENGLAND\\Premier league\\GAMES"
    )
    paths = sorted(Path(data_dir).glob("*.csv"))

    league = read_league_csvs(paths)
    league = [r for r in league if r["season"] >= "2011-2012"]

    fa = [(s, w, r, sc) for s, w, r, sc in FA_CUP_FINAL]
    lc = [(s, w, r, sc) for s, w, r, sc in LEAGUE_CUP_FINAL]

    total, parts = combined_index(league, fa, lc)

    print("=" * 60)
    print("Farmer's League Index (FLI*)")
    print("=" * 60)
    print()
    print(f"League seasons analyzed: {len(league)}")
    print(f"FA Cup finals: {len(fa)}")
    print(f"League Cup finals: {len(lc)}")
    print()
    print(f"League component (L):   {parts[0]:.4f}")
    print(f"FA Cup component (F):   {parts[1]:.4f}")
    print(f"League Cup component (C): {parts[2]:.4f}")
    print()
    print(f"Combined FLI*: {total:.4f}")
    print("  (weights 0.60 L + 0.25 FA + 0.15 LC)")
    print("=" * 60)

    for name, finals in [("FA Cup", fa), ("League Cup", lc)]:
        idx, st = cup_index(finals)
        print(f"\n{name}")
        print(f"  index:        {idx:.4f}")
        print(f"  dominance:    {st['dominance']:.4f}")
        print(f"  max share:    {st['max_share']:.4f}")
        print(f"  avg final margin: {st['avg_final_margin']:.3f}")
        print(f"  top winners:  {st['counts'].most_common(5)}")

    L, l_st = league_index(league)
    print(f"\nPremier League (league component)")
    print(f"  index:        {L:.4f}")
    print(f"  dominance:    {l_st['dominance']:.4f}")
    print(f"  max share:    {l_st['max_share']:.4f}")
    avg_margin = sum(max(s["margin"], 0) for s in league) / len(league)
    avg_gd = sum(max(s["winner_gd"], 0) for s in league) / len(league)
    print(f"  avg margin:   {avg_margin:.2f}")
    print(f"  avg winner GD: {avg_gd:.2f}")
    print(f"  top winners:  {l_st['counts'].most_common(5)}")
