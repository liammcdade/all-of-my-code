import random
import math
import numpy as np
import shutil
import os
from collections import defaultdict
from tqdm import tqdm
import numba
from typing import Dict, List, Tuple

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
NUM_TEAMS = 18

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

class TeamRegistry:
    def __init__(self):
        self.elos: Dict[str, float] = {}
        self.team_to_idx: Dict[str, int] = {}
        self.idx_to_team: List[str] = []

    def add_team(self, name: str, elo: float, form: float = 0.0, injury: float = 0.0):
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

    def get_team_names(self) -> List[str]:
        return list(self.elos.keys())

    def get_elo(self, name: str) -> float:
        return self.elos[name]

@numba.jit(nopython=True, cache=True)
def calculate_match_params(adjusted_home: float, adjusted_away: float, home_advantage: float, base_xg: float, max_xg: float, xg_scale: float, closeness_scale: float) -> Tuple[float, float, float, float]:
    diff = adjusted_home - adjusted_away + home_advantage
    home_xg = base_xg + max_xg / (1 + math.exp(-diff / xg_scale))
    away_xg = base_xg + max_xg / (1 + math.exp(diff / xg_scale))
    closeness = math.exp(-(diff**2) / (2 * closeness_scale**2))
    return home_xg, away_xg, closeness, diff

@numba.jit(nopython=True, cache=True)
def poisson_random_numba(lam: float) -> int:
    if lam <= 0:
        return 0
    L = math.exp(-lam)
    k = 0
    p = 1.0
    while p > L:
        k += 1
        p *= random.random()
    return k - 1

@numba.jit(nopython=True, cache=True)
def simulate_poisson_match_numba(home_xg: float, away_xg: float, closeness: float, diff: float) -> Tuple[int, int]:
    tempo_factor = TEMPO_BASE + TEMPO_RANGE * (abs(diff) / ELO_SCALE)
    home_xg_adj = home_xg * tempo_factor
    away_xg_adj = away_xg * tempo_factor
    lambda_shared = SHARED_GOAL_BASE + closeness * SHARED_GOAL_CLOSENESS
    variance_boost = 1 + VARIANCE_BOOST_FACTOR
    lambda_home = max(MIN_LAMBDA, (home_xg_adj - lambda_shared) * variance_boost)
    lambda_away = max(MIN_LAMBDA, away_xg_adj - lambda_shared)
    shared_goals = poisson_random_numba(lambda_shared)
    home_goals = poisson_random_numba(lambda_home)
    away_goals = poisson_random_numba(lambda_away)
    home_goals += shared_goals
    away_goals += shared_goals
    return home_goals, away_goals

@numba.jit(nopython=True, cache=True, parallel=True)
def run_simulation_vectorized(
    fixtures: np.ndarray,
    elo_array: np.ndarray,
    k_factor: float,
    elo_scale: float
) -> Tuple[np.ndarray, np.ndarray, np.ndarray, np.ndarray]:
    n_teams = len(elo_array)
    table_pts = np.zeros(n_teams, dtype=np.int64)
    table_gf = np.zeros(n_teams, dtype=np.int64)
    table_ga = np.zeros(n_teams, dtype=np.int64)
    current_elo = elo_array.copy()
    
    for idx in range(len(fixtures)):
        home_idx = fixtures[idx, 0]
        away_idx = fixtures[idx, 1]
        home_elo = current_elo[home_idx]
        away_elo = current_elo[away_idx]
        diff = home_elo - away_elo
        expected_home = 1.0 / (1.0 + 10.0 ** (-diff / elo_scale))
        
        home_xg, away_xg, closeness, match_diff = calculate_match_params(
            home_elo, away_elo, HOME_ADVANTAGE, BASE_XG, MAX_XG, X_G_SCALE, CLOSENESS_SCALE
        )
        home_goals, away_goals = simulate_poisson_match_numba(home_xg, away_xg, closeness, match_diff)
        
        table_gf[home_idx] += home_goals
        table_ga[home_idx] += away_goals
        table_gf[away_idx] += away_goals
        table_ga[away_idx] += home_goals
        
        if home_goals > away_goals:
            table_pts[home_idx] += 3
            score_home, score_away = 1.0, 0.0
        elif away_goals > home_goals:
            table_pts[away_idx] += 3
            score_home, score_away = 0.0, 1.0
        else:
            table_pts[home_idx] += 1
            table_pts[away_idx] += 1
            score_home, score_away = 0.5, 0.5
        
        current_elo[home_idx] = home_elo + k_factor * (score_home - expected_home)
        current_elo[away_idx] = away_elo + k_factor * (score_away - (1 - expected_home))
    
    return table_pts, table_gf, table_ga, current_elo

def generate_match_matrix(n_teams: int) -> np.ndarray:
    fixtures = []
    for i in range(n_teams):
        for j in range(i + 1, n_teams):
            fixtures.append((i, j))
    for i in range(n_teams):
        for j in range(i + 1, n_teams):
            fixtures.append((j, i))
    return np.array(fixtures, dtype=np.int64)

def run_single_simulation_vectorized(registry: TeamRegistry, match_matrix: np.ndarray) -> Tuple[Dict[str, int], List[Tuple[str, Dict[str, int]]], int]:
    team_names = registry.idx_to_team
    n_teams = len(team_names)
    elo_array = np.array([registry.elos[name] for name in team_names], dtype=np.float64)
    
    table_pts, table_gf, table_ga, _ = run_simulation_vectorized(match_matrix, elo_array, K_FACTOR, ELO_SCALE)
    
    table = {name: {"MP": 0, "Pts": int(table_pts[i]), "GF": int(table_gf[i]), "GA": int(table_ga[i])} for i, name in enumerate(team_names)}
    ranking = sorted(table.items(), key=lambda x: (x[1]["Pts"], x[1]["GF"] - x[1]["GA"], x[1]["GF"]), reverse=True)
    return table, ranking, ranking[0][1]["Pts"]

def main():
    registry = TeamRegistry()
    for i, name in enumerate(TEAM_NAMES):
        registry.add_team(name, ELO_RATINGS[i])
    
    n_teams = len(TEAM_NAMES)
    match_matrix = generate_match_matrix(n_teams)
    NUM_SIMS = 5000
    
    title_counts: Dict[str, int] = defaultdict(int)
    top4_counts: Dict[str, int] = defaultdict(int)
    europa_counts: Dict[str, int] = defaultdict(int)
    releg_counts: Dict[str, int] = defaultdict(int)
    champion_points: List[int] = []
    avg_points: Dict[str, List[int]] = defaultdict(list)
    points_distribution: Dict[str, List[int]] = defaultdict(list)
    releg_40_count = 0
    excitement_scores: List[int] = []
    
    for _ in tqdm(range(NUM_SIMS), desc="Running simulations", unit="sim"):
        promoted = "Southampton" if random.random() < 0.5 else "Hull City"
        registry.add_team(promoted, CHAMPIONSHIP_ELO[promoted])
        
        new_match_matrix = generate_match_matrix(len(registry.idx_to_team))
        table, ranking, champ_pts = run_single_simulation_vectorized(registry, new_match_matrix)
        
        registry.remove_team(promoted)
        champion_points.append(champ_pts)
        
        for pos, (team, data) in enumerate(ranking, 1):
            avg_points[team].append(data["Pts"])
            points_distribution[team].append(data["Pts"])
            
            if pos == 1:
                title_counts[team] += 1
            if pos <= 4:
                top4_counts[team] += 1
            if pos == 5:
                europa_counts[team] += 1
            if pos > len(ranking) - 3:
                releg_counts[team] += 1
        
        has_releg_40 = any(pos > len(ranking) - 3 and data["Pts"] >= 40 for pos, (team, data) in enumerate(ranking, 1))
        if has_releg_40:
            releg_40_count += 1
        
        leader_pts = ranking[0][1]["Pts"]
        second_pts = ranking[1][1]["Pts"]
        excitement_scores.append(leader_pts - second_pts)
    
    aggregated_results = {
        "title": dict(title_counts),
        "top4": dict(top4_counts),
        "europa": dict(europa_counts),
        "releg": dict(releg_counts),
        "champion_points": champion_points,
        "avg_points": dict(avg_points),
        "points_distribution": dict(points_distribution),
        "releg_40_count": releg_40_count,
        "excitement_scores": excitement_scores,
    }
    
    for team in CHAMPIONSHIP_ELO:
        registry.add_team(team, CHAMPIONSHIP_ELO[team])
    
    print("\n" + "=" * 60)
    print("TEAM STATISTICS")
    print("=" * 60)
    display_team_statistics(aggregated_results, NUM_SIMS)
    
    print("\n" + "=" * 60)
    print("POINTS TO WIN THE LEAGUE")
    print("=" * 60)
    print(f"Max points to win the league: {max(champion_points)}")
    print(f"Min points to win the league: {min(champion_points)}")
    
    print("\n" + "=" * 40)
    print("ADDITIONAL STATISTICS")
    print("=" * 40)
    print(f"Probability that at least one team is relegated with 40+ points: {releg_40_count / NUM_SIMS * 100:.4f}%")
    print(f"Average excitement score for the final day (out of 10): {sum(excitement_scores) / len(excitement_scores) / 10:.2f}")
    print(f"Total European probability (Europa League, sum of all teams): {sum(europa_counts.values()) / NUM_SIMS * 100:.2f}%")
    print(f"Total European probability (Champions League, sum of all teams): {sum(top4_counts.values()) / NUM_SIMS * 100:.2f}%")
    print(f"  - CL only (top 4): {sum(top4_counts.values()) / NUM_SIMS * 100:.2f}%")
    print(f"  - Europa only (5th): {sum(europa_counts.values()) / NUM_SIMS * 100:.2f}%")
    
    pycache_path = os.path.join(os.path.dirname(__file__), "__pycache__")
    if os.path.exists(pycache_path):
        shutil.rmtree(pycache_path)


def display_team_statistics(results: Dict, sims: int) -> None:
    team_stats: Dict[str, Dict[str, float]] = {}
    for team in results["points_distribution"].keys():
        pts = results["points_distribution"][team]
        avg = sum(pts) / len(pts)
        std = math.sqrt(sum((x - avg) ** 2 for x in pts) / len(pts))
        sorted_pts = sorted(pts)
        p25 = sorted_pts[int(len(pts) * 0.25)]
        med = sorted_pts[int(len(pts) * 0.50)]
        p75 = sorted_pts[int(len(pts) * 0.75)]
        team_stats[team] = {"avg": avg, "std": std, "p25": p25, "med": med, "p75": p75}
    
    print(f"{'Team':<15}{'AvgPts':<8}{'StdDev':<8}{'Title%':<8}{'CL%':<8}{'Europa%':<10}{'Europe%':<10}{'Releg%':<8}")
    print("-" * 80)
    for team in sorted(results["points_distribution"].keys(), key=lambda x: sum(results["avg_points"][x]) / len(results["avg_points"][x]), reverse=True):
        times_played = len(results["points_distribution"][team])
        title_pct = results['title'].get(team, 0) / times_played * 100
        top4_pct = results['top4'].get(team, 0) / times_played * 100
        europa_pct = results['europa'].get(team, 0) / times_played * 100
        combined_europe_pct = top4_pct + europa_pct
        avg_points = sum(results['avg_points'][team]) / times_played
        releg_pct = results['releg'].get(team, 0) / times_played * 100
        print(
            f"{team:<15}"
            f"{avg_points:<8.2f}"
            f"{team_stats[team]['std']:<8.2f}"
            f"{title_pct:<8.2f}"
            f"{top4_pct:<8.2f}"
            f"{europa_pct:<10.2f}"
            f"{combined_europe_pct:<10.2f}"
            f"{releg_pct:.2f}"
        )

if __name__ == "__main__":
    main()