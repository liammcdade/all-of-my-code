#!/usr/bin/env python3
"""
108-team combined European simulation (2026/27).

LEAGUE PHASE — 10 matches per club (540 total)
---------------------------------------------
Every club plays:
  * 4 different opponents from its OWN competition (2H/2A)
  * 3 different opponents from its TOP cross competition (2H/1A)
  * 3 different opponents from its BOTTOM cross competition (1H/2A)

Because there are only three competitions, the cross blocks form a 3-cycle
(UCL -> UEL -> UECL -> UCL) so every pair has exactly one 2H side and one 1H
side. Every team therefore ends with exactly 5H/5A.

All 108 clubs ranked in ONE table -> top 64 -> single-elimination knockout.

The script runs NUM_SIMS simulations (default 1000) with GUARANTEED UNIQUE
schedules (retries on any hash collision), with a live progress bar.
"""

from __future__ import annotations

import math
import random
import sys
import time
from collections import Counter, deque
from dataclasses import dataclass

try:
    from tqdm import tqdm
    _HAS_TQDM = True
except ImportError:
    _HAS_TQDM = False


# ---------------------------------------------------------------------------
# EASY CONFIG — change these
# ---------------------------------------------------------------------------
NUM_SIMS = 10000
SEED = 2026

# ---------------------------------------------------------------------------
# Model constants
# ---------------------------------------------------------------------------
HOME_ADV = 65.0
BASE_XG = 1.30
ELO_SCALE = 900.0
XG_MIN, XG_MAX = 0.20, 4.50

# ---------------------------------------------------------------------------
# Team data
# ---------------------------------------------------------------------------
TEAMS = {
    "UCL": [
        ("AEK Athens", 1694.0), ("Arsenal", 2147.0), ("Aston Villa", 1987.0),
        ("Atlético de Madrid", 1908.0), ("Barcelona", 2065.0), ("Bayern München", 2086.0),
        ("Bodø/Glimt", 1844.0), ("Borussia Dortmund", 1888.0), ("Club Brugge", 1850.0),
        ("Como", 1792.0), ("Fenerbahçe", 1738.0), ("Feyenoord", 1702.0),
        ("Galatasaray", 1744.0), ("Inter", 1920.0), ("LASK", 1584.0),
        ("Leipzig", 1803.0), ("Lens", 1793.0), ("Lille", 1765.0),
        ("Liverpool", 1956.0), ("Man City", 2047.0), ("Man United", 1942.0),
        ("Napoli", 1776.0), ("Paris", 2082.0), ("Porto", 1847.0),
        ("PSV", 1770.0), ("Real Betis", 1856.0), ("Real Madrid", 2011.0),
        ("Roma", 1843.0), ("Sabah", 1590.0), ("Shakhtar", 1683.0),
        ("Slavia Praha", 1621.0), ("Slovan Bratislava", 1542.0), ("Sporting CP", 1934.0),
        ("Stuttgart", 1796.0), ("Viking", 1740.0), ("Villarreal", 1777.0),
    ],
    "UEL": [
        ("Ararat-Armenia", 1474.0), ("Salzburg", 1594.0), ("Sturm Graz", 1593.0),
        ("Anderlecht", 1620.0), ("Union SG", 1835.0), ("Levski Sofia", 1541.0),
        ("GNK Dinamo", 1672.0), ("Omonia", 1681.0), ("Sparta Praha", 1608.0),
        ("Viktoria Plzeň", 1573.0), ("Bournemouth", 1910.0), ("Crystal Palace", 1846.0),
        ("Sunderland", 1832.0), ("Lyon", 1811.0), ("Marseille", 1710.0),
        ("Rennes", 1766.0), ("Hoffenheim", 1685.0), ("Leverkusen", 1898.0),
        ("OFI Crete", 1451.0), ("Olympiacos", 1731.0), ("Ferencváros", 1699.0),
        ("H. Beer-Sheva", 1592.0), ("Milan", 1821.0), ("Juventus", 1834.0),
        ("AZ Alkmaar", 1637.0), ("N.E.C.", 1548.0), ("Lillestrøm", 1461.0),
        ("Jagiellonia", 1545.0), ("Lech Poznań", 1641.0), ("Benfica", 1889.0),
        ("Torreense", 1441.0), ("Celtic", 1635.0), ("Celje", 1540.0),
        ("Real Sociedad", 1733.0), ("Celta", 1708.0), ("Beşiktaş", 1649.0),
    ],
    "UECL": [
        ("Egnatia", 1504.0), ("Inter Escaldes", 1438.0), ("Gent", 1667.0),
        ("Sint-Truidense", 1598.0), ("Borac", 1498.0), ("CSKA Sofia", 1461.0),
        ("Hajduk Split", 1603.0), ("Pafos", 1554.0), ("Jablonec", 1487.0),
        ("Aarhus", 1578.0), ("Copenhagen", 1684.0), ("Midtjylland", 1736.0),
        ("Nordsjælland", 1617.0), ("Brighton", 1942.0), ("KuPS Kuopio", 1443.0),
        ("Monaco", 1836.0), ("Iberia Tbilisi", 1400.0), ("Freiburg", 1798.0),
        ("L. Red Imps", 1360.0), ("Panathinaikos", 1643.0), ("Atalanta", 1784.0),
        ("Kairat Almaty", 1433.0), ("Riga", 1500.0), ("Kauno Žalgiris", 1413.0),
        ("Ajax", 1647.0), ("Twente", 1637.0), ("Brann", 1556.0),
        ("Braga", 1699.0), ("Universitatea Craiova", 1563.0), ("Hearts", 1522.0),
        ("Crvena Zvezda", 1621.0), ("Getafe", 1673.0), ("Mjällby", 1441.0),
        ("Lugano", 1639.0), ("Thun", 1545.0), ("Trabzonspor", 1624.0),
    ],
}

# Cross-competition "top" mapping.
# If CROSS_TOP[X] == Y, then X is the 2H side in the X-vs-Y cross block.
CROSS_TOP = {
    "UCL": "UEL",
    "UEL": "UECL",
    "UECL": "UCL",
}


# ---------------------------------------------------------------------------
# Team
# ---------------------------------------------------------------------------
@dataclass
class Team:
    name: str
    elo: float
    league: str
    p: int = 0
    w: int = 0
    d: int = 0
    l: int = 0
    gf: int = 0
    ga: int = 0
    pts: int = 0

    @property
    def gd(self) -> int:
        return self.gf - self.ga

    def record(self, scored: int, conceded: int) -> None:
        self.p += 1
        self.gf += scored
        self.ga += conceded
        if scored > conceded:
            self.w += 1
            self.pts += 3
        elif scored == conceded:
            self.d += 1
            self.pts += 1
        else:
            self.l += 1


# ---------------------------------------------------------------------------
# Match engine
# ---------------------------------------------------------------------------
def poisson(lam: float, rng: random.Random) -> int:
    if lam <= 0:
        return 0
    limit, k, p = math.exp(-lam), 0, 1.0
    while True:
        k += 1
        p *= rng.random()
        if p <= limit:
            return k - 1


def expected_goals(elo_a: float, elo_b: float, home_adv: float = HOME_ADV):
    diff = (elo_a + home_adv) - elo_b
    mult = 10.0 ** (diff / ELO_SCALE)
    xg_a = min(max(BASE_XG * mult, XG_MIN), XG_MAX)
    xg_b = min(max(BASE_XG / mult, XG_MIN), XG_MAX)
    return xg_a, xg_b


def sim_score(a: Team, b: Team, rng: random.Random):
    xa, xb = expected_goals(a.elo, b.elo)
    return poisson(xa, rng), poisson(xb, rng)


# ---------------------------------------------------------------------------
# Schedule helpers
# ---------------------------------------------------------------------------
def random_regular_graph(n: int, degree: int, rng: random.Random, max_tries: int = 1000):
    for _ in range(max_tries):
        stubs = []
        for v in range(n):
            stubs.extend([v] * degree)
        rng.shuffle(stubs)
        edges = set()
        ok = True
        for i in range(0, len(stubs), 2):
            a, b = stubs[i], stubs[i + 1]
            if a == b:
                ok = False
                break
            e = (a, b) if a < b else (b, a)
            if e in edges:
                ok = False
                break
            edges.add(e)
        if ok:
            return list(edges)
    raise RuntimeError("random_regular_graph failed")


def random_bipartite_regular(n: int, degree: int, rng: random.Random, max_tries: int = 1000):
    for _ in range(max_tries):
        xs, ys = [], []
        for i in range(n):
            xs.extend([i] * degree)
            ys.extend([i] * degree)
        rng.shuffle(xs)
        rng.shuffle(ys)
        edges = set()
        ok = True
        for x, y in zip(xs, ys):
            if (x, y) in edges:
                ok = False
                break
            edges.add((x, y))
        if ok:
            return list(edges)
    raise RuntimeError("random_bipartite_regular failed")


# ---------------------------------------------------------------------------
# Max-flow orientation (guaranteed correct or cleanly infeasible)
# ---------------------------------------------------------------------------
def max_flow_orient(edges, vertices, quotas):
    """
    Orient each edge so vertex v gets exactly quotas[v] home games.
    Returns [(home, away), ...] or None if infeasible.
    """
    n_v, n_e = len(vertices), len(edges)
    S, T = 0, 1 + n_e + n_v
    N = T + 1
    graph = [[] for _ in range(N)]

    def add_edge(u, v, cap):
        graph[u].append([v, cap, len(graph[v])])
        graph[v].append([u, 0, len(graph[u]) - 1])

    for i, (u, v) in enumerate(edges):
        add_edge(S, 1 + i, 1)
        add_edge(1 + i, 1 + n_e + u, 1)
        add_edge(1 + i, 1 + n_e + v, 1)
    for idx in range(n_v):
        add_edge(1 + n_e + idx, T, quotas[idx])

    flow = 0
    while True:
        level = [-1] * N
        level[S] = 0
        q = deque([S])
        while q:
            u = q.popleft()
            for v, cap, _ in graph[u]:
                if cap > 0 and level[v] == -1:
                    level[v] = level[u] + 1
                    q.append(v)
        if level[T] == -1:
            break

        it = [0] * N

        def dfs(u, pushed):
            if u == T:
                return pushed
            while it[u] < len(graph[u]):
                e = graph[u][it[u]]
                v, cap, rev = e
                if cap > 0 and level[v] == level[u] + 1:
                    d = dfs(v, min(pushed, cap))
                    if d > 0:
                        e[1] -= d
                        graph[v][rev][1] += d
                        return d
                it[u] += 1
            return 0

        while True:
            pushed = dfs(S, float("inf"))
            if pushed == 0:
                break
            flow += pushed

    if flow != n_e:
        return None

    result = []
    for i, (u, v) in enumerate(edges):
        for to, cap, _ in graph[1 + i]:
            if 1 + n_e <= to < 1 + n_e + n_v and cap == 0:
                home_idx = to - (1 + n_e)
                if home_idx == u:
                    result.append((vertices[u], vertices[v]))
                else:
                    result.append((vertices[v], vertices[u]))
                break
    return result


def orient_component(edges, vertices, high_names, rng):
    quotas = [2 if v.name in high_names else 1 for v in vertices]
    result = max_flow_orient(edges, vertices, quotas)
    if result is None:
        raise RuntimeError("orientation infeasible for this graph")
    return result


# ---------------------------------------------------------------------------
# Build schedule with retries
# ---------------------------------------------------------------------------
def _try_build_schedule(leagues, rng):
    fixtures = []
    keys = list(leagues)

    # Own-league blocks: 4 distinct opponents, exactly 2H / 2A.
    for lg in keys:
        teams = leagues[lg]
        high_names = {t.name for t in teams}
        for _ in range(100):
            edges = random_regular_graph(len(teams), 4, rng)
            try:
                fixtures.extend(orient_component(edges, teams, high_names, rng))
                break
            except RuntimeError:
                continue
        else:
            raise RuntimeError(f"own block {lg} infeasible")

    # Cross-league blocks: 3 opponents.
    for i in range(len(keys)):
        for j in range(i + 1, len(keys)):
            X, Y = leagues[keys[i]], leagues[keys[j]]
            assert len(X) == len(Y)
            n = len(X)
            vertices = X + Y

            if CROSS_TOP[keys[i]] == keys[j]:
                high_lg = keys[i]
            elif CROSS_TOP[keys[j]] == keys[i]:
                high_lg = keys[j]
            else:
                raise RuntimeError(
                    f"invalid cross-top mapping for {keys[i]}-{keys[j]}"
                )

            high_names = {t.name for t in leagues[high_lg]}

            for _ in range(100):
                edges_bip = random_bipartite_regular(n, 3, rng)
                edges = [(x, n + y) for x, y in edges_bip]
                try:
                    fixtures.extend(orient_component(edges, vertices, high_names, rng))
                    break
                except RuntimeError:
                    continue
            else:
                raise RuntimeError(f"cross block {keys[i]}-{keys[j]} infeasible")

    rng.shuffle(fixtures)
    return fixtures


def build_schedule(leagues, rng):
    for _ in range(20):
        try:
            return _try_build_schedule(leagues, rng)
        except RuntimeError:
            continue
    raise RuntimeError("build_schedule failed after many retries")


def signature(fixtures) -> int:
    return hash(frozenset((h.name, a.name) for h, a in fixtures))


def validate_schedule(fixtures, leagues) -> None:
    league_of = {t.name: lg for lg, ts in leagues.items() for t in ts}
    info = {
        t.name: {"home": 0, "away": 0, "blocks": {}}
        for ts in leagues.values()
        for t in ts
    }

    for h, a in fixtures:
        lh, la = league_of[h.name], league_of[a.name]
        block = f"own:{lh}" if lh == la else f"cross:{'-'.join(sorted([lh, la]))}"

        info[h.name]["home"] += 1
        info[a.name]["away"] += 1

        for name, opp, is_home in ((h.name, a.name, True), (a.name, h.name, False)):
            bd = info[name]["blocks"].setdefault(block, {"opps": set(), "home": 0})
            bd["opps"].add(opp)
            if is_home:
                bd["home"] += 1

    for name, d in info.items():
        total = d["home"] + d["away"]
        assert total == 10, f"{name} plays {total} games"
        assert d["home"] == 5, f"{name} has {d['home']} home"
        assert d["away"] == 5, f"{name} has {d['away']} away"
        assert len(d["blocks"]) == 3, f"{name} faces {len(d['blocks'])} blocks"

        for block, bd in d["blocks"].items():
            opps = bd["opps"]
            if block.startswith("own:"):
                assert len(opps) == 4, f"{name} in {block} faces {len(opps)} opponents"
                assert bd["home"] == 2, f"{name} in {block} has {bd['home']} home"
            else:
                assert len(opps) == 3, f"{name} in {block} faces {len(opps)} opponents"
                assert bd["home"] in (1, 2), f"{name} in {block} has {bd['home']} home"

        cross_homes = sorted(
            bd["home"]
            for block, bd in d["blocks"].items()
            if not block.startswith("own:")
        )
        assert cross_homes == [1, 2], f"{name} cross home split is {cross_homes}"


# ---------------------------------------------------------------------------
# League table
# ---------------------------------------------------------------------------
def standings(teams) -> list[Team]:
    return sorted(teams, key=lambda t: (-t.pts, -t.gd, -t.gf, -t.elo, t.name))


# ---------------------------------------------------------------------------
# Knockout
# ---------------------------------------------------------------------------
def seed_order(n: int) -> list[int]:
    order = [1]
    while len(order) < n:
        m = len(order) * 2
        nxt = []
        for s in order:
            nxt.append(s)
            nxt.append(m + 1 - s)
        order = nxt
    return order


def shootout(rng: random.Random, a: Team, b: Team):
    pa = min(max(0.76 + (a.elo - b.elo) / 12000.0, 0.68), 0.84)
    pb = min(max(0.76 + (b.elo - a.elo) / 12000.0, 0.68), 0.84)
    sa = sb = 0
    for _ in range(5):
        sa += rng.random() < pa
        sb += rng.random() < pb
    while sa == sb:
        sa += rng.random() < pa
        sb += rng.random() < pb
    return sa, sb


def knockout_tie(a: Team, b: Team, rng: random.Random) -> Team:
    ga, gb = sim_score(a, b, rng)
    if ga != gb:
        return a if ga > gb else b
    xa, xb = expected_goals(a.elo, b.elo)
    ga += poisson(xa / 3.0, rng)
    gb += poisson(xb / 3.0, rng)
    if ga != gb:
        return a if ga > gb else b
    sa, sb = shootout(rng, a, b)
    return a if sa > sb else b


def run_knockout_stats(qualified: list[Team], rng: random.Random):
    """Run knockout and return (champion, stages dict of name-sets)."""
    order = seed_order(len(qualified))
    slots = [qualified[s - 1] for s in order]
    seed_of = {t.name: i + 1 for i, t in enumerate(qualified)}
    stages: dict[str, set[str]] = {}
    round_num = 0
    while len(slots) > 1:
        winners = []
        for i in range(0, len(slots), 2):
            a, b = slots[i], slots[i + 1]
            if seed_of[a.name] > seed_of[b.name]:
                a, b = b, a
            winners.append(knockout_tie(a, b, rng))
        round_num += 1
        # Store NAMES (Team objects are unhashable).
        winner_names = {t.name for t in winners}
        if round_num == 1:
            stages["r32"] = winner_names
        elif round_num == 2:
            stages["r16"] = winner_names
        elif round_num == 3:
            stages["qf"] = winner_names
        elif round_num == 4:
            stages["sf"] = winner_names
        elif round_num == 5:
            stages["f"] = winner_names
        slots = winners
    champion = slots[0]
    return champion, stages


def run_knockout(qualified: list[Team], rng: random.Random) -> Team:
    champion, _ = run_knockout_stats(qualified, rng)
    return champion


# ---------------------------------------------------------------------------
# Progress bar fallback
# ---------------------------------------------------------------------------
def manual_bar(completed: int, total: int, start: float, length: int = 40) -> None:
    elapsed = time.time() - start
    eta = (elapsed / completed * (total - completed)) if completed else 0.0
    frac = completed / total
    filled = int(length * frac)
    bar = "█" * filled + "░" * (length - filled)
    sys.stdout.write(
        f"\rSims |{bar}| {completed}/{total} ({100*frac:5.1f}%) "
        f"[{elapsed:6.1f}s<{eta:6.1f}s]"
    )
    sys.stdout.flush()


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------
def main(num_sims: int = NUM_SIMS, seed: int = SEED) -> None:
    rng = random.Random(seed)

    seen: set[int] = set()
    collisions = 0

    winners: Counter[str] = Counter()
    qual_counts: Counter[str] = Counter()
    champs_by_lg: Counter[str] = Counter()
    distinct_winners: set[str] = set()

    stage_names = ["top64", "r32", "r16", "qf", "sf", "f", "champion"]
    stage_counts = {name: Counter() for name in stage_names}

    # Track total league-phase points per team (for averages)
    points_total: Counter[str] = Counter()

    start = time.time()

    if _HAS_TQDM:
        pbar = tqdm(
            total=num_sims,
            desc="Sims",
            unit="sim",
            bar_format="{l_bar}{bar}| {n_fmt}/{total_fmt} [{elapsed}<{remaining}, {rate_fmt}]",
        )

    for sim in range(num_sims):
        # 1. Build a GUARANTEED UNIQUE schedule
        while True:
            leagues = {lg: [Team(n, e, lg) for n, e in rows] for lg, rows in TEAMS.items()}
            all_teams = [t for ts in leagues.values() for t in ts]
            fixtures = build_schedule(leagues, rng)
            sig = signature(fixtures)
            if sig not in seen:
                seen.add(sig)
                break
            collisions += 1
            if collisions > 1_000_000:
                raise RuntimeError("Too many collisions — aborting")

        if sim == 0:
            validate_schedule(fixtures, leagues)

        # 2. Play league phase
        for h, a in fixtures:
            hg, ag = sim_score(h, a, rng)
            h.record(hg, ag)
            a.record(ag, hg)

        for t in all_teams:
            points_total[t.name] += t.pts

        table = standings(all_teams)
        qualified = table[:64]

        # 3. Record top-64 qualification
        for t in qualified:
            qual_counts[t.name] += 1
            stage_counts["top64"][t.name] += 1

        # 4. Knockout with stage tracking
        champ, stages = run_knockout_stats(qualified, rng)

        # 5. Record knockout stage advancements
        for stage in ("r32", "r16", "qf", "sf", "f"):
            for name in stages[stage]:
                stage_counts[stage][name] += 1
        stage_counts["champion"][champ.name] += 1

        winners[champ.name] += 1
        champs_by_lg[champ.league] += 1
        distinct_winners.add(champ.name)

        # 6. Progress
        if _HAS_TQDM:
            pbar.update(1)
        elif (sim + 1) % 25 == 0 or (sim + 1) == num_sims:
            manual_bar(sim + 1, num_sims, start)

    if _HAS_TQDM:
        pbar.close()
    else:
        sys.stdout.write("\n")

    elapsed = time.time() - start

    # =================== REPORT ===================
    print()
    print("=" * 80)
    print(f"SIMULATION COMPLETE — {num_sims} runs in {elapsed:.1f}s")
    print("=" * 80)

    print(f"Schedules generated:        {num_sims}")
    print(f"Unique schedules stored:    {len(seen)}")
    print(f"Hash collisions (retried):  {collisions}")
    print(f"Distinct champions:         {len(distinct_winners)}")

    unique_ok = len(seen) == num_sims
    print(
        "UNIQUENESS GUARANTEE:       "
        f"{'✓ PASS — every schedule is unique' if unique_ok else '✗ FAIL'}"
    )

    print("\n--- Champions by competition ---")
    for lg, cnt in champs_by_lg.most_common():
        print(f"  {lg:<5}: {cnt:>5} ({100*cnt/num_sims:5.2f}%)")

    print("\n--- Top 25 champion counts ---")
    max_cnt = max(winners.values()) if winners else 1
    for rank, (name, cnt) in enumerate(winners.most_common(25), 1):
        pct = 100 * cnt / num_sims
        bar = "█" * int(30 * cnt / max_cnt)
        print(f"  {rank:>2}. {name:<22} {cnt:>5} ({pct:5.2f}%) {bar}")

    print("\n--- Top 15 top-64 qualifiers ---")
    max_q = max(qual_counts.values()) if qual_counts else 1
    for rank, (name, cnt) in enumerate(qual_counts.most_common(15), 1):
        pct = 100 * cnt / num_sims
        bar = "█" * int(30 * cnt / max_q)
        print(f"  {rank:>2}. {name:<22} {cnt:>5} ({pct:5.2f}%) {bar}")

    # ---- Full stage probability table + average points ----
    print("\n--- Team stage probabilities (%) — sorted by average league points ---")
    header = (
        f"{'Team':<22} {'AvgPts':>7} {'Top64':>6} {'R32':>6} {'R16':>6} "
        f"{'QF':>6} {'SF':>6} {'F':>6} {'Win':>6}"
    )
    print(header)
    print("-" * len(header))

    # TEAMS stores (name, elo) tuples — unpack the name.
    all_team_names = [name for ts in TEAMS.values() for name, _ in ts]

    def avg_pts(name: str) -> float:
        return points_total[name] / num_sims

    for name in sorted(
        all_team_names,
        key=lambda n: (-avg_pts(n), -stage_counts["champion"][n], n),
    ):
        vals = []
        for stage in ("top64", "r32", "r16", "qf", "sf", "f", "champion"):
            cnt = stage_counts[stage][name]
            pct = 100 * cnt / num_sims
            vals.append(f"{pct:6.2f}")
        print(f"{name:<22} {avg_pts(name):7.3f} " + " ".join(vals))

    print("\n" + "=" * 80)


if __name__ == "__main__":
    # Optional CLI override, otherwise use NUM_SIMS / SEED from the top of the file.
    n = int(sys.argv[1]) if len(sys.argv) > 1 else NUM_SIMS
    s = int(sys.argv[2]) if len(sys.argv) > 2 else SEED
    main(num_sims=n, seed=s)