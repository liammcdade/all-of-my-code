import random
import math
from collections import defaultdict
from typing import List, Tuple, Dict
from tqdm import tqdm

NUM_SIMULATIONS = 10000

TEAMS_DATA = [
    (1, "France", 2205), (2, "Spain", 2165), (3, "England", 2152), (4, "Portugal", 2138),
    (5, "Italy", 2112), (6, "Germany", 2085), (7, "Netherlands", 2072), (8, "Belgium", 2059),
    (9, "Croatia", 2045), (10, "Denmark", 1952), (11, "Switzerland", 1939), (12, "Austria", 1925),
    (13, "Turkey", 1899), (14, "Scotland", 1886), (15, "Czechia", 1872), (16, "Norway", 1859),
    (17, "Ukraine", 1846), (18, "Sweden", 1832),
    (19, "Hungary", 1819), (20, "Serbia", 1806), (21, "Poland", 1792), (22, "Greece", 1779),
    (23, "Wales", 1766), (24, "Slovenia", 1739), (25, "Israel", 1726), (26, "Bosnia", 1713),
    (27, "Finland", 1699), (28, "Georgia", 1686), (29, "Ireland", 1673), (30, "Slovakia", 1659),
    (31, "Romania", 1646), (32, "Albania", 1633), (33, "Montenegro", 1619), (34, "Bulgaria", 1606),
    (35, "N. Macedonia", 1593), (36, "Armenia", 1579),
    (37, "Cyprus", 1566), (38, "Iceland", 1553), (39, "Kazakhstan", 1540), (40, "Faroe Is", 1526),
    (41, "Estonia", 1513), (42, "Luxembourg", 1500), (43, "Moldova", 1486), (44, "Belarus", 1473),
    (45, "Latvia", 1460), (46, "Azerbaijan", 1446), (47, "Lithuania", 1433), (48, "Kosovo", 1420),
    (49, "N. Ireland", 1406), (50, "Gibraltar", 1393), (51, "Malta", 1380), (52, "Andorra", 1367),
    (53, "Liechtenstein", 1353), (54, "San Marino", 1300)
]

class Team:
    def __init__(self, rank: int, name: str, elo: int):
        self.rank = rank
        self.name = name
        self.elo = elo
        self.league = self.group = self.pot = None
        self.played = self.won = self.drawn = self.lost = 0
        self.gf = self.ga = self.pts = 0
        self.h2h = defaultdict(list)

    def reset(self):
        self.played = self.won = self.drawn = self.lost = 0
        self.gf = self.ga = self.pts = 0
        self.h2h.clear()

    @property
    def gd(self) -> int: return self.gf - self.ga
    def __repr__(self): return f"{self.name} (#{self.rank})"

TEAMS = {n: Team(r, n, e) for r, n, e in TEAMS_DATA}

def setup_competitions():
    sorted_teams = sorted(TEAMS.values(), key=lambda t: t.rank)
    l1, l2 = sorted_teams[:36], sorted_teams[36:]
    for t in l1: t.league = "L1"
    for t in l2: t.league = "L2"

    l1_pots = {1: l1[0:12], 2: l1[12:24], 3: l1[24:36]}
    for p in l1_pots.values(): random.shuffle(p)
    
    l1_groups = [[] for _ in range(3)]
    for pot, pool in l1_pots.items():
        for g in range(3):
            for t in pool[g*4:(g+1)*4]:
                t.pot = pot
                t.group = f"L1-G{g+1}"
                l1_groups[g].append(t)

    l2_pots = {1: [], 2: [], 3: []}
    for i, t in enumerate(l2):
        l2_pots[(i//6)+1].append(t)
        t.pot = (i//6)+1

    l2_groups = [[] for _ in range(3)]
    for pot, pool in l2_pots.items():
        for g in range(3):
            for t in pool[g*2:(g+1)*2]:
                t.group = f"L2-G{g+1}"
                l2_groups[g].append(t)

    return {"L1": l1_groups, "L2": l2_groups}

def generate_fixtures_l1(group: List[Team]) -> List[Tuple[Team, Team]]:
    pots = {1: [], 2: [], 3: []}
    for t in group: pots[t.pot].append(t)
    fixtures = []

    for p in [1, 2, 3]:
        t = pots[p].copy()
        random.shuffle(t)
        fixtures.extend([(t[0], t[1]), (t[1], t[0]), (t[2], t[3]), (t[3], t[2])])

    for p1, p2 in [(1,2), (1,3), (2,3)]:
        a, b = pots[p1], pots[p2]
        for i in range(4):
            fixtures.append((a[i], b[i]))
            fixtures.append((b[(i+1)%4], a[i]))
            
    random.shuffle(fixtures)
    return fixtures

def generate_fixtures_l2(group: List[Team]) -> List[Tuple[Team, Team]]:
    pots = {1: [], 2: [], 3: []}
    for t in group: pots[t.pot].append(t)
    fixtures = []

    for p in [1, 2, 3]:
        t1, t2 = pots[p]
        fixtures.extend([(t1, t2), (t2, t1)])

    for p1, p2 in [(1,2), (1,3), (2,3)]:
        a, b = pots[p1], pots[p2]
        fixtures.extend([
            (a[0], b[0]), (b[1], a[0]),
            (a[1], b[1]), (b[0], a[1])
        ])

    random.shuffle(fixtures)
    return fixtures

def validate_constraints(group, fixtures):
    for t in group:
        matches_played = home_games = away_games = 0
        pot_matches = defaultdict(int)

        for h, a in fixtures:
            if h == t or a == t:
                matches_played += 1
                opp = a if h == t else h
                if h == t: home_games += 1
                else: away_games += 1
                pot_matches[opp.pot] += 1

        assert matches_played == 6, f"❌ {t.name} played {matches_played}"
        assert home_games == 3, f"❌ {t.name} home: {home_games}"
        for p in [1, 2, 3]:
            assert pot_matches[p] == 2, f"❌ {t.name} vs P{p}: {pot_matches[p]}"

def poisson_sample(lam: float) -> int:
    L = math.exp(-lam)
    k, p = 0, 1.0
    while True:
        k += 1
        p *= random.random()
        if p <= L: break
    return k - 1

def simulate_match(home: Team, away: Team) -> Tuple[int, int]:
    diff = home.elo - away.elo
    home_xg = max(0.25, 1.30 + diff/450)
    away_xg = max(0.25, 1.10 - diff/550)
    return min(poisson_sample(home_xg), 7), min(poisson_sample(away_xg), 7)

def apply_result(h: Team, a: Team, hg: int, ag: int):
    h.played += 1; a.played += 1
    h.gf += hg; h.ga += ag; a.gf += ag; a.ga += hg
    h.h2h[a.name].append((hg, ag))
    a.h2h[h.name].append((ag, hg))
    if hg > ag: h.won += 1; h.pts += 3; a.lost += 1
    elif ag > hg: a.won += 1; a.pts += 3; h.lost += 1
    else: h.drawn += 1; a.drawn += 1; h.pts += 1; a.pts += 1

def play_knockout(t1, t2):
    hg, ag = simulate_match(t1, t2)
    apply_result(t1, t2, hg, ag)
    if hg == ag:
        winner = t1 if random.random() < 0.5 else t2
    else:
        winner = t1 if hg > ag else t2
    loser = t2 if winner == t1 else t1
    return winner, loser, hg, ag

def get_standings(group: List[Team]) -> List[Team]:
    def h2h_pts(t: Team) -> int:
        pts = 0
        for opp in group:
            if opp.pot == t.pot and opp != t:
                for hg, ag in t.h2h.get(opp.name, []):
                    pts += 3 if hg > ag else (1 if hg == ag else 0)
        return pts
    return sorted(group, key=lambda t: (t.pts, t.gd, t.gf, h2h_pts(t), random.random()), reverse=True)

def run_single_simulation(seed: int) -> Tuple[List[str], List[str]]:
    random.seed(seed)
    for t in TEAMS.values(): t.reset()
    groups = setup_competitions()
    
    l1_st, l2_st = {}, {}
    
    for i, g in enumerate(groups["L1"]):
        fixtures = generate_fixtures_l1(g)
        validate_constraints(g, fixtures) 
        for h, a in fixtures:
            hg, ag = simulate_match(h, a)
            apply_result(h, a, hg, ag)
        l1_st[f"L1-G{i+1}"] = get_standings(g)
        
    for i, g in enumerate(groups["L2"]):
        fixtures = generate_fixtures_l2(g)
        validate_constraints(g, fixtures)
        for h, a in fixtures:
            hg, ag = simulate_match(h, a)
            apply_result(h, a, hg, ag)
        l2_st[f"L2-G{i+1}"] = get_standings(g)
    
    auto = []
    for g, table in l1_st.items(): auto.extend(table[:3])
    
    l2_winners = [table[0] for table in l2_st.values()]
    best_l2 = max(l2_winners, key=lambda t: (t.pts, t.gd, t.gf))
    auto.append(best_l2)
    
    playoff_pool = []
    for g, table in l1_st.items(): playoff_pool.extend(table[3:7])
    for g, table in l2_st.items(): playoff_pool.append(table[1])
    playoff_pool.sort(key=lambda t: (t.pts, t.gd, t.gf), reverse=True)
    playoff_teams = playoff_pool[:8]
    
    seeded = sorted(playoff_teams, key=lambda t: (t.pts, t.gd, t.gf), reverse=True)
    mini_league_1 = seeded[:4]
    mini_league_2 = seeded[4:]
    
    winners, runners_up = [], []
    for league in [mini_league_1, mini_league_2]:
        for i in range(0, 4, 2):
            t1, t2 = league[i], league[i+1]
            hg, ag = simulate_match(t1, t2)
            apply_result(t1, t2, hg, ag)
            if hg == ag:
                winner = t1 if random.random() < 0.5 else t2
            else:
                winner = t1 if hg > ag else t2
            winners.append(winner)
            runners_up.append(t2 if winner == t1 else t1)
    
    runners_up.sort(key=lambda t: (t.pts, t.gd, t.gf), reverse=True)
    
    for i in range(0, 4, 2):
        t1, t2 = runners_up[i], runners_up[i+1]
        hg, ag = simulate_match(t1, t2)
        apply_result(t1, t2, hg, ag)
        if hg == ag:
            w = t1 if random.random() < 0.5 else t2
        else:
            w = t1 if hg > ag else t2
        winners.append(w)
    
    return [t.name for t in auto], [t.name for t in winners]

def run_monte_carlo(num_sims: int):
    qual_counts: Dict[str, int] = defaultdict(int)
    auto_counts: Dict[str, int] = defaultdict(int)
    
    for sim in tqdm(range(num_sims), desc="Running simulations"):
        auto, winners = run_single_simulation(sim)
        for t in auto:
            auto_counts[t] += 1
        for t in winners:
            qual_counts[t] += 1
    
    return auto_counts, qual_counts

def display_results(auto_counts: Dict[str, int], qual_counts: Dict[str, int], num_sims: int):
    print("=" * 70)
    print(f"MONTE CARLO SIMULATION RESULTS ({num_sims:,} runs)")
    print("=" * 70)
    
    all_teams = set(auto_counts.keys()) | set(qual_counts.keys())
    team_stats = []
    for team in all_teams:
        auto_pct = auto_counts.get(team, 0) / num_sims * 100
        qual_pct = qual_counts.get(team, 0) / num_sims * 100
        total_pct = (auto_counts.get(team, 0) + qual_counts.get(team, 0)) / num_sims * 100
        team_stats.append((team, auto_pct, qual_pct, total_pct))
    
    team_stats.sort(key=lambda x: -x[3])
    
    print("\nTEAM QUALIFICATION CHANCES")
    print("-" * 70)
    print(f"{'Team':<15} {'Auto (%)':>10} {'Playoff (%)':>12} {'Total (%)':>10}")
    print("-" * 70)
    for team, auto_pct, qual_pct, total_pct in team_stats:
        print(f"{team:<15} {auto_pct:>9.1f}% {qual_pct:>11.1f}% {total_pct:>9.1f}%")
    
    print("\n" + "=" * 70)
    print(f"Expected Auto Qualifiers: {sum(auto_counts.values()) / num_sims:.1f}")
    print(f"Expected Playoff Qualifiers: {sum(qual_counts.values()) / num_sims:.1f}")

if __name__ == "__main__":
    auto_counts, qual_counts = run_monte_carlo(NUM_SIMULATIONS)
    display_results(auto_counts, qual_counts, NUM_SIMULATIONS)