import random
import math
import numpy as np
import shutil
import os
from collections import defaultdict
from tqdm import tqdm
import numba
from typing import Dict, List, Tuple, Any
from dataclasses import dataclass, field

# Constants
HOME_ADVANTAGE = 33.8
K_FACTOR = 25
BASE_XG = 0.7
MAX_XG = 1.8
ELO_SCALE = 400
X_G_SCALE = 300
CLOSENESS_SCALE = 180
INJURY_SCALE = 80
TEMPO_BASE = 0.9
TEMPO_RANGE = 0.1
VARIANCE_BOOST_FACTOR = 0.2
SHARED_GOAL_BASE = 0.05
SHARED_GOAL_CLOSENESS = 0.25
MIN_LAMBDA = 0.05
NUM_SIMS = 5000

TEAM_NAMES = [
    "Arsenal", "Man City", "Liverpool", "Aston Villa",
    "Man United", "Chelsea", "Brighton", "Brentford",
    "Everton", "Bournemouth", "Coventry", "Fulham",
    "Ipswich", "Sunderland", "Crystal Palace", "Leeds",
    "Newcastle", "Nottingham", "Tottenham"
]

ELO_RATINGS = np.array([
    1895, 1885, 1845, 1755,
    1725, 1795, 1705, 1645,
    1605, 1665, 1495, 1620,
    1515, 1490, 1640, 1540,
    1785, 1680, 1740
], dtype=np.float64)

CHAMPIONSHIP_ELO = {"Southampton": 1635, "Hull City": 1637}

# Data Models
@dataclass
class AggregatedStats:
    """Holds accumulated statistics across all simulation runs."""
    title_counts: Dict[str, int] = field(default_factory=lambda: defaultdict(int))
    top4_counts: Dict[str, int] = field(default_factory=lambda: defaultdict(int))
    europa_counts: Dict[str, int] = field(default_factory=lambda: defaultdict(int))
    releg_counts: Dict[str, int] = field(default_factory=lambda: defaultdict(int))
    champion_points: List[int] = field(default_factory=list)
    points_distribution: Dict[str, List[int]] = field(default_factory=lambda: defaultdict(list))
    releg_40_count: int = 0
    excitement_scores: List[float] = field(default_factory=list)

@dataclass
class TeamFinalStats:
    """Consolidated final probability statistics for a single team."""
    team_name: str
    avg_pts: float
    std_dev: float
    title_pct: float
    cl_pct: float
    europa_pct: float
    europe_pct: float
    releg_pct: float

class TeamRegistry:
    """Manages team metadata and ELO mappings for the simulation."""
    def __init__(self):
        self.elos: Dict[str, float] = {}
        self.team_to_idx: Dict[str, int] = {}
        self.idx_to_team: List[str] = []

    def add_team(self, name: str, elo: float):
        """Registers a new team into the registry."""
        idx = len(self.idx_to_team)
        self.elos[name] = elo
        self.team_to_idx[name] = idx
        self.idx_to_team.append(name)

    def remove_last_team(self):
        """Removes the most recently added team (used for promoted team randomization)."""
        if not self.idx_to_team:
            return
        name = self.idx_to_team.pop()
        self.elos.pop(name, None)
        self.team_to_idx.pop(name, None)

# Core Logic
@numba.jit(nopython=True, cache=True)
def calculate_match_params(adjusted_home: float, adjusted_away: float) -> Tuple[float, float, float, float]:
    """
    Computes xG and match dynamics based on ELO ratings.
    Returns: (home_xg, away_xg, closeness_factor, elo_diff)
    """
    diff = adjusted_home - adjusted_away + HOME_ADVANTAGE
    home_xg = BASE_XG + MAX_XG / (1 + math.exp(-diff / X_G_SCALE))
    away_xg = BASE_XG + MAX_XG / (1 + math.exp(diff / X_G_SCALE))
    closeness = math.exp(-(diff**2) / (2 * CLOSENESS_SCALE**2))
    return home_xg, away_xg, closeness, diff

@numba.jit(nopython=True, cache=True)
def poisson_random_numba(lam: float) -> int:
    """Generates a Poisson-distributed random integer."""
    if lam <= 0:
        return 0
    limit = math.exp(-lam)
    k = 0
    p = 1.0
    while p > limit:
        k += 1
        p *= random.random()
    return k - 1

@numba.jit(nopython=True, cache=True)
def simulate_match_numba(home_xg: float, away_xg: float, closeness: float, diff: float) -> Tuple[int, int]:
    """
    Simulates a single match score using modified Poisson logic with shared goals.
    Returns: (home_goals, away_goals)
    """
    tempo_factor = TEMPO_BASE + TEMPO_RANGE * (abs(diff) / ELO_SCALE)
    lambda_shared = SHARED_GOAL_BASE + closeness * SHARED_GOAL_CLOSENESS
    v_boost = 1 + VARIANCE_BOOST_FACTOR

    lambda_home = max(MIN_LAMBDA, (home_xg * tempo_factor - lambda_shared) * v_boost)
    lambda_away = max(MIN_LAMBDA, away_xg * tempo_factor - lambda_shared)

    shared = poisson_random_numba(lambda_shared)
    home = poisson_random_numba(lambda_home) + shared
    away = poisson_random_numba(lambda_away) + shared
    return home, away

@numba.jit(nopython=True, cache=True)
def run_simulation_jit(
    fixtures: np.ndarray,
    elo_array: np.ndarray
) -> Tuple[np.ndarray, np.ndarray, np.ndarray, np.ndarray]:
    """
    Performs a full season simulation using JIT-accelerated logic.
    Updates ELO ratings dynamically after each match.
    """
    n_teams = len(elo_array)
    table_pts = np.zeros(n_teams, dtype=np.int64)
    table_gf = np.zeros(n_teams, dtype=np.int64)
    table_ga = np.zeros(n_teams, dtype=np.int64)
    current_elo = elo_array.copy()
    
    for idx in range(len(fixtures)):
        h_idx, a_idx = fixtures[idx, 0], fixtures[idx, 1]
        h_elo, a_elo = current_elo[h_idx], current_elo[a_idx]
        
        expected_home = 1.0 / (1.0 + 10.0 ** (-(h_elo - a_elo) / ELO_SCALE))
        h_xg, a_xg, clos, m_diff = calculate_match_params(h_elo, a_elo)
        h_g, a_g = simulate_match_numba(h_xg, a_xg, clos, m_diff)
        
        table_gf[h_idx] += h_g
        table_ga[h_idx] += a_g
        table_gf[a_idx] += a_g
        table_ga[a_idx] += h_g
        
        score_h = 0.5
        if h_g > a_g:
            table_pts[h_idx] += 3
            score_h = 1.0
        elif a_g > h_g:
            table_pts[a_idx] += 3
            score_h = 0.0
        else:
            table_pts[h_idx] += 1
            table_pts[a_idx] += 1

        current_elo[h_idx] += K_FACTOR * (score_h - expected_home)
        current_elo[a_idx] += K_FACTOR * ((1 - score_h) - (1 - expected_home))
    
    return table_pts, table_gf, table_ga, current_elo

# Simulation Engine
def generate_fixtures(n_teams: int) -> np.ndarray:
    """Generates a full double round-robin fixture list."""
    f = []
    for i in range(n_teams):
        for j in range(n_teams):
            if i != j:
                f.append((i, j))
    return np.array(f, dtype=np.int64)

def run_single_season(registry: TeamRegistry, fixtures: np.ndarray) -> Tuple[List[Tuple[str, int]], int]:
    """Executes one season simulation and returns the final ranking."""
    elo_arr = np.array([registry.elos[name] for name in registry.idx_to_team], dtype=np.float64)
    pts, gf, ga, _ = run_simulation_jit(fixtures, elo_arr)
    
    results = []
    for i, name in enumerate(registry.idx_to_team):
        results.append((name, int(pts[i]), int(gf[i]), int(ga[i])))
    
    ranking = sorted(results, key=lambda x: (x[1], x[2] - x[3], x[2]), reverse=True)
    return [(r[0], r[1]) for r in ranking], ranking[0][1]

def update_aggregated_stats(stats: AggregatedStats, ranking: List[Tuple[str, int]], champ_pts: int):
    """Updates the global stats container with results from a single simulation run."""
    stats.champion_points.append(champ_pts)
    num_teams = len(ranking)
    
    for pos, (team, pts) in enumerate(ranking, 1):
        stats.points_distribution[team].append(pts)
        if pos == 1:
            stats.title_counts[team] += 1
        if pos <= 4:
            stats.top4_counts[team] += 1
        if pos == 5:
            stats.europa_counts[team] += 1
        if pos > num_teams - 3:
            stats.releg_counts[team] += 1

    if any(pts >= 40 for team, pts in ranking[-3:]):
        stats.releg_40_count += 1
    
    stats.excitement_scores.append(ranking[0][1] - ranking[1][1])

def run_monte_carlo(registry: TeamRegistry, num_sims: int) -> AggregatedStats:
    """Runs multiple Monte Carlo simulations with varying promoted teams."""
    stats = AggregatedStats()
    fixtures = generate_fixtures(len(TEAM_NAMES) + 1)
    
    for _ in tqdm(range(num_sims), desc="Simulating"):
        promoted = random.choice(list(CHAMPIONSHIP_ELO.keys()))
        registry.add_team(promoted, CHAMPIONSHIP_ELO[promoted])
        
        ranking, champ_pts = run_single_season(registry, fixtures)
        
        update_aggregated_stats(stats, ranking, champ_pts)
        registry.remove_last_team()
    return stats

# Statistics
def calculate_team_final_stats(team: str, stats: AggregatedStats) -> TeamFinalStats:
    """Calculates final probabilities and averages for a specific team."""
    pts = stats.points_distribution[team]
    count = len(pts)
    avg_pts = sum(pts) / count
    std_dev = math.sqrt(sum((x - avg_pts)**2 for x in pts) / count)

    return TeamFinalStats(
        team_name=team,
        avg_pts=avg_pts,
        std_dev=std_dev,
        title_pct=stats.title_counts[team] / count * 100,
        cl_pct=stats.top4_counts[team] / count * 100,
        europa_pct=stats.europa_counts[team] / count * 100,
        europe_pct=(stats.top4_counts[team] + stats.europa_counts[team]) / count * 100,
        releg_pct=stats.releg_counts[team] / count * 100
    )

# Output
def display_results(stats: AggregatedStats, team_names: List[str]):
    """Formats and prints simulation results to the console."""
    all_teams = set(team_names) | set(CHAMPIONSHIP_ELO.keys())
    final_results = [calculate_team_final_stats(t, stats) for t in all_teams]
    final_results.sort(key=lambda x: x.avg_pts, reverse=True)
    
    print("\n" + "=" * 80)
    print(f"{'Team':<15}{'AvgPts':<8}{'StdDev':<8}{'Title%':<8}{'CL%':<8}{'Europa%':<10}{'Europe%':<10}{'Releg%':<8}")
    print("-" * 80)
    for r in final_results:
        print(f"{r.team_name:<15}{r.avg_pts:<8.2f}{r.std_dev:<8.2f}{r.title_pct:<8.2f}"
              f"{r.cl_pct:<8.2f}{r.europa_pct:<10.2f}{r.europe_pct:<10.2f}{r.releg_pct:.2f}")

    print("\n" + "=" * 60)
    print(f"Max points to win: {max(stats.champion_points)}")
    print(f"Min points to win: {min(stats.champion_points)}")
    print(f"Relegation with 40+ Pts Probability: {stats.releg_40_count / NUM_SIMS * 100:.4f}%")
    print(f"Avg Excitement (0-10 Scale): {sum(stats.excitement_scores) / len(stats.excitement_scores) / 10:.2f}")

def main():
    """Main entry point for the Premier League simulation."""
    registry = TeamRegistry()
    for i, name in enumerate(TEAM_NAMES):
        registry.add_team(name, ELO_RATINGS[i])

    stats = run_monte_carlo(registry, NUM_SIMS)
    display_results(stats, TEAM_NAMES)

    # Cleanup Numba cache/pycache if necessary
    if os.path.exists("__pycache__"):
        shutil.rmtree("__pycache__")

if __name__ == "__main__":
    main()
