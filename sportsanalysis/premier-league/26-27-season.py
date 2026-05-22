import random
import math
import shutil
import os
from collections import defaultdict
from dataclasses import dataclass, field
from typing import Dict, List, Tuple

import numpy as np
import numba
from tqdm import tqdm

# ==============================================================================
# Constants
# ==============================================================================

HOME_ADVANTAGE = 33.8
K_FACTOR = 25
BASE_XG = 0.7
MAX_XG = 1.8
ELO_SCALE = 400
X_G_SCALE = 300
CLOSENESS_SCALE = 180
TEMPO_BASE = 0.9
TEMPO_RANGE = 0.1
VARIANCE_BOOST_FACTOR = 0.2
SHARED_GOAL_BASE = 0.05
SHARED_GOAL_CLOSENESS = 0.25
MIN_LAMBDA = 0.05
NUM_TEAMS = 18
NUM_SIMS = 5000

TEAM_NAMES = [
    "Arsenal", "Man City", "Liverpool", "Aston Villa",
    "Man United", "Chelsea", "Brighton", "Brentford",
    "Everton", "Bournemouth", "Coventry", "Fulham",
    "Ipswich", "Sunderland", "Crystal Palace", "Leeds",
    "Newcastle", "Nottingham"
]

ELO_RATINGS = np.array([
    1895, 1885, 1845, 1755,
    1725, 1795, 1705, 1645,
    1605, 1665, 1495, 1620,
    1515, 1490, 1640, 1540,
    1785, 1680
], dtype=np.float64)

CHAMPIONSHIP_ELO = {"Southampton": 1635, "Hull City": 1637}

# ==============================================================================
# Data Models
# ==============================================================================

@dataclass
class TeamStats:
    mp: int = 0
    pts: int = 0
    gf: int = 0
    ga: int = 0

    @property
    def gd(self) -> int:
        return self.gf - self.ga

@dataclass
class SimulationSummary:
    title_counts: Dict[str, int] = field(default_factory=lambda: defaultdict(int))
    top4_counts: Dict[str, int] = field(default_factory=lambda: defaultdict(int))
    europa_counts: Dict[str, int] = field(default_factory=lambda: defaultdict(int))
    releg_counts: Dict[str, int] = field(default_factory=lambda: defaultdict(int))
    champion_points: List[int] = field(default_factory=list)
    points_distribution: Dict[str, List[int]] = field(default_factory=lambda: defaultdict(list))
    releg_40_count: int = 0
    excitement_scores: List[float] = field(default_factory=list)

class TeamRegistry:
    def __init__(self):
        self.elos: Dict[str, float] = {}
        self.team_to_idx: Dict[str, int] = {}
        self.idx_to_team: List[str] = []

    def add_team(self, name: str, elo: float):
        idx = len(self.idx_to_team)
        self.elos[name] = elo
        self.team_to_idx[name] = idx
        self.idx_to_team.append(name)

    def remove_team(self, name: str):
        self.elos.pop(name, None)
        if name in self.team_to_idx:
            del self.team_to_idx[name]
        if name in self.idx_to_team:
            self.idx_to_team.remove(name)

# ==============================================================================
# Utility Functions
# ==============================================================================

@numba.jit(nopython=True, cache=True)
def poisson_random_numba(lam: float) -> int:
    if lam <= 0:
        return 0
    limit = math.exp(-lam)
    count = 0
    prob_sum = 1.0
    while prob_sum > limit:
        count += 1
        prob_sum *= random.random()
    return count - 1

def generate_match_matrix(n_teams: int) -> np.ndarray:
    fixtures = []
    for i in range(n_teams):
        for j in range(i + 1, n_teams):
            fixtures.append((i, j))
            fixtures.append((j, i))
    return np.array(fixtures, dtype=np.int64)

# ==============================================================================
# Core Logic
# ==============================================================================

@numba.jit(nopython=True, cache=True)
def calculate_match_params(
    adj_home: float,
    adj_away: float,
    home_adv: float,
    base_xg: float,
    max_xg: float,
    xg_scale: float,
    closeness_scale: float
) -> Tuple[float, float, float, float]:
    diff = adj_home - adj_away + home_adv
    home_xg = base_xg + max_xg / (1 + math.exp(-diff / xg_scale))
    away_xg = base_xg + max_xg / (1 + math.exp(diff / xg_scale))
    closeness = math.exp(-(diff**2) / (2 * closeness_scale**2))
    return home_xg, away_xg, closeness, diff

@numba.jit(nopython=True, cache=True)
def simulate_poisson_match_numba(
    home_xg: float,
    away_xg: float,
    closeness: float,
    diff: float
) -> Tuple[int, int]:
    tempo = TEMPO_BASE + TEMPO_RANGE * (abs(diff) / ELO_SCALE)
    h_xg_adj = home_xg * tempo
    a_xg_adj = away_xg * tempo

    sh_lambda = SHARED_GOAL_BASE + closeness * SHARED_GOAL_CLOSENESS
    v_boost = 1 + VARIANCE_BOOST_FACTOR

    h_lambda = max(MIN_LAMBDA, (h_xg_adj - sh_lambda) * v_boost)
    a_lambda = max(MIN_LAMBDA, a_xg_adj - sh_lambda)

    shared = poisson_random_numba(sh_lambda)
    hg = poisson_random_numba(h_lambda) + shared
    ag = poisson_random_numba(a_lambda) + shared

    return hg, ag

# ==============================================================================
# Simulation Engine
# ==============================================================================

@numba.jit(nopython=True, cache=True)
def run_simulation_vectorized(
    fixtures: np.ndarray,
    elo_array: np.ndarray,
    k_factor: float,
    elo_scale: float
) -> Tuple[np.ndarray, np.ndarray, np.ndarray]:
    n_teams = len(elo_array)
    table_pts = np.zeros(n_teams, dtype=np.int64)
    table_gf = np.zeros(n_teams, dtype=np.int64)
    table_ga = np.zeros(n_teams, dtype=np.int64)
    current_elo = elo_array.copy()
    
    for idx in range(len(fixtures)):
        h_idx, a_idx = fixtures[idx, 0], fixtures[idx, 1]
        h_elo, a_elo = current_elo[h_idx], current_elo[a_idx]

        diff = h_elo - a_elo
        exp_home = 1.0 / (1.0 + 10.0 ** (-diff / elo_scale))
        
        h_xg, a_xg, clos, m_diff = calculate_match_params(
            h_elo, a_elo, HOME_ADVANTAGE, BASE_XG, MAX_XG, X_G_SCALE, CLOSENESS_SCALE
        )
        hg, ag = simulate_poisson_match_numba(h_xg, a_xg, clos, m_diff)
        
        table_gf[h_idx] += hg
        table_ga[h_idx] += ag
        table_gf[a_idx] += ag
        table_ga[a_idx] += hg
        
        if hg > ag:
            table_pts[h_idx] += 3
            res_h, res_a = 1.0, 0.0
        elif ag > hg:
            table_pts[a_idx] += 3
            res_h, res_a = 0.0, 1.0
        else:
            table_pts[h_idx] += 1
            table_pts[a_idx] += 1
            res_h, res_a = 0.5, 0.5
        
        current_elo[h_idx] = h_elo + k_factor * (res_h - exp_home)
        current_elo[a_idx] = a_elo + k_factor * (res_a - (1 - exp_home))
    
    return table_pts, table_gf, table_ga

def run_single_iteration(registry: TeamRegistry) -> List[Tuple[str, TeamStats]]:
    team_names = registry.idx_to_team
    elo_array = np.array([registry.elos[name] for name in team_names], dtype=np.float64)
    fixtures = generate_match_matrix(len(team_names))

    pts, gf, ga = run_simulation_vectorized(fixtures, elo_array, K_FACTOR, ELO_SCALE)

    results = []
    # 19 teams, each team plays 18 opponents twice = 36 matches
    matches_played = (len(team_names) - 1) * 2
    for i, name in enumerate(team_names):
        results.append((name, TeamStats(mp=matches_played, pts=int(pts[i]), gf=int(gf[i]), ga=int(ga[i]))))

    return sorted(results, key=lambda x: (x[1].pts, x[1].gd, x[1].gf), reverse=True)

# ==============================================================================
# Statistics
# ==============================================================================

def update_summary(summary: SimulationSummary, ranking: List[Tuple[str, TeamStats]]):
    n_teams = len(ranking)
    champ_pts = ranking[0][1].pts
    summary.champion_points.append(champ_pts)

    has_releg_40 = False
    for pos, (team, stats) in enumerate(ranking, 1):
        summary.points_distribution[team].append(stats.pts)
        if pos == 1:
            summary.title_counts[team] += 1
        if pos <= 4:
            summary.top4_counts[team] += 1
        if pos == 5:
            summary.europa_counts[team] += 1
        if pos > n_teams - 3:
            summary.releg_counts[team] += 1
            if stats.pts >= 40:
                has_releg_40 = True

    if has_releg_40:
        summary.releg_40_count += 1

    summary.excitement_scores.append(float(ranking[0][1].pts - ranking[1][1].pts))

# ==============================================================================
# Output
# ==============================================================================

def display_results(summary: SimulationSummary):
    print("\n" + "=" * 60)
    print("TEAM STATISTICS")
    print("=" * 60)

    print(f"{'Team':<15}{'AvgPts':<8}{'StdDev':<8}{'Title%':<8}{'CL%':<8}{'Europa%':<10}{'Europe%':<10}{'Releg%':<8}")
    print("-" * 80)
    
    sorted_teams = sorted(
        summary.points_distribution.keys(),
        key=lambda x: np.mean(summary.points_distribution[x]),
        reverse=True
    )
    
    for team in sorted_teams:
        pts = summary.points_distribution[team]
        n = len(pts)
        avg = np.mean(pts)
        std = np.std(pts)

        t_pct = summary.title_counts[team] / n * 100
        cl_pct = summary.top4_counts[team] / n * 100
        el_pct = summary.europa_counts[team] / n * 100
        releg_pct = summary.releg_counts[team] / n * 100

        print(f"{team:<15}{avg:<8.2f}{std:<8.2f}{t_pct:<8.2f}{cl_pct:<8.2f}{el_pct:<10.2f}{cl_pct+el_pct:<10.2f}{releg_pct:.2f}")

    print("\n" + "=" * 60)
    print("ADDITIONAL STATISTICS")
    print("=" * 60)
    print(f"Max points to win the league: {max(summary.champion_points)}")
    print(f"Min points to win the league: {min(summary.champion_points)}")
    print(f"Probability of relegation with 40+ points: {summary.releg_40_count / NUM_SIMS * 100:.4f}%")
    avg_excitement = sum(summary.excitement_scores) / len(summary.excitement_scores) / 10
    print(f"Average excitement score (out of 10): {avg_excitement:.2f}")

# ==============================================================================
# Main Entry Point
# ==============================================================================

def main():
    registry = TeamRegistry()
    for i, name in enumerate(TEAM_NAMES):
        registry.add_team(name, ELO_RATINGS[i])
    
    summary = SimulationSummary()
    
    for _ in tqdm(range(NUM_SIMS), desc="Simulating"):
        promoted = "Southampton" if random.random() < 0.5 else "Hull City"
        registry.add_team(promoted, CHAMPIONSHIP_ELO[promoted])
        
        ranking = run_single_iteration(registry)
        update_summary(summary, ranking)
        
        registry.remove_team(promoted)
    
    display_results(summary)
    
    cache_path = os.path.join(os.path.dirname(__file__), "__pycache__")
    if os.path.exists(cache_path):
        shutil.rmtree(cache_path)

if __name__ == "__main__":
    main()
