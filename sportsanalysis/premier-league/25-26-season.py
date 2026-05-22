import random
import math
from collections import defaultdict
from dataclasses import dataclass, field
from typing import Dict, List, Tuple

import numpy as np
import numba
from tqdm import tqdm

from season_25_26_data import (
    ELO, CURRENT_TABLE, FIXTURES, FORM_ADJUSTMENT, INJURY_PENALTY
)

# ==============================================================================
# Constants
# ==============================================================================

HOME_ADVANTAGE_ELO = 60
MAX_GOALS = 4.0
MIN_LAMBDA = 0.6
SEASON_DRAW_RATE = 0.25
BASE_HOME_WIN = 0.57
BASE_AWAY_WIN = 0.43
SCALE = 400
CLOSENESS_FACTOR = 180
SHIFT_SCALE = 0.2
K_FACTOR_BASE = 25
SIMULATIONS = 25000

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
class SimulationGlobalStats:
    title: Dict[str, int] = field(default_factory=lambda: defaultdict(int))
    cl: Dict[str, int] = field(default_factory=lambda: defaultdict(int))
    el: Dict[str, int] = field(default_factory=lambda: defaultdict(int))
    conf: Dict[str, int] = field(default_factory=lambda: defaultdict(int))
    european: Dict[str, int] = field(default_factory=lambda: defaultdict(int))
    releg: Dict[str, int] = field(default_factory=lambda: defaultdict(int))
    releg_40_count: int = 0
    excitement_scores: List[float] = field(default_factory=list)
    pts_dist: List[List[int]] = field(default_factory=list)
    win_points: List[int] = field(default_factory=list)

# ==============================================================================
# Utility Functions
# ==============================================================================

@numba.jit(nopython=True)
def poisson_random(lam: float) -> int:
    if lam <= 0:
        return 0
    limit = math.exp(-lam)
    count, p = 0, 1.0
    while p > limit:
        count += 1
        p *= random.random()
    return count - 1

@numba.jit(nopython=True)
def get_expected_goals(h_elo: float, a_elo: float, h_base: float, a_base: float) -> Tuple[float, float]:
    diff = h_elo - a_elo
    h_lam = h_base * math.exp(diff / 800)
    a_lam = a_base * math.exp(-diff / 800)
    return max(0.6, min(4.0, h_lam)), max(0.6, min(4.0, a_lam))

@numba.jit(nopython=True)
def get_adjusted_ratings(idx: int, elo_arr: np.ndarray, form_arr: np.ndarray, injury_arr: np.ndarray) -> Tuple[float, float]:
    penalty = injury_arr[idx]
    adj_penalty = penalty * (1 - math.exp(-penalty / 80))
    att = elo_arr[idx] - (adj_penalty / 2) + form_arr[idx]
    defe = elo_arr[idx] - (adj_penalty / 2) + form_arr[idx]
    return att, defe

# ==============================================================================
# Core Logic
# ==============================================================================

@numba.jit(nopython=True)
def simulate_match(
    h_idx: int, a_idx: int, elo_arr: np.ndarray,
    form_arr: np.ndarray, injury_arr: np.ndarray,
    h_adv: float, dr_rate: float, scale_val: float
) -> Tuple[int, int]:
    h_xg, a_xg = get_expected_goals(elo_arr[h_idx], elo_arr[a_idx], 1.5, 1.2)
    h_att, h_def = get_adjusted_ratings(h_idx, elo_arr, form_arr, injury_arr)
    a_att, a_def = get_adjusted_ratings(a_idx, elo_arr, form_arr, injury_arr)

    diff = (h_att - a_def + h_adv) - (a_att - h_def)
    base_draw = 0.75 * dr_rate
    rem = 1 - base_draw

    closeness = math.exp(-(diff**2)/(2 * CLOSENESS_FACTOR**2))
    p_draw = base_draw + closeness * 0.1
    p_home = (rem * BASE_HOME_WIN) + (diff / scale_val * SHIFT_SCALE)
    p_away = (rem * BASE_AWAY_WIN) - (diff / scale_val * SHIFT_SCALE)

    tot = p_home + p_draw + p_away
    r = random.random()
    if r < p_home / tot:
        return poisson_random(h_xg), poisson_random(a_xg)
    if r < (p_home + p_draw) / tot:
        g = poisson_random((h_xg + a_xg) / 2)
        return g, g
    return poisson_random(a_xg), poisson_random(h_xg)

def update_elo_inplace(h_idx: int, a_idx: int, hg: int, ag: int, elo_arr: np.ndarray, h_adv: float):
    diff = elo_arr[h_idx] - elo_arr[a_idx] + h_adv
    exp_h = 1 / (1 + 10 ** (-diff / SCALE))
    res_h = 1.0 if hg > ag else (0.5 if hg == ag else 0.0)
    k = K_FACTOR_BASE
    elo_arr[h_idx] += k * (res_h - exp_h)
    elo_arr[a_idx] += k * ((1 - res_h) - (1 - exp_h))

# ==============================================================================
# Simulation Engine
# ==============================================================================

def run_single_simulation(
    elo_arr: np.ndarray, pts_arr: np.ndarray, gf_arr: np.ndarray, ga_arr: np.ndarray,
    fix_indices: List[Tuple[int, int]], form_arr: np.ndarray, injury_arr: np.ndarray,
    eu_probs: Dict[str, Dict[str, float]]
) -> Dict:
    cur_elo, pts, gf, ga = elo_arr.copy(), pts_arr.copy(), gf_arr.copy(), ga_arr.copy()
    h_adv = random.uniform(50, 70)
    dr_rate = random.uniform(0.23, 0.28)
    
    for h_idx, a_idx in fix_indices:
        hg, ag = simulate_match(h_idx, a_idx, cur_elo, form_arr, injury_arr, h_adv, dr_rate, SCALE)
        gf[h_idx], ga[h_idx] = gf[h_idx] + hg, ga[h_idx] + ag
        gf[a_idx], ga[a_idx] = gf[a_idx] + ag, ga[a_idx] + hg
        if hg > ag: pts[h_idx] += 3
        elif ag > hg: pts[a_idx] += 3
        else: pts[h_idx] += 1; pts[a_idx] += 1
        update_elo_inplace(h_idx, a_idx, hg, ag, cur_elo, h_adv)

    ranking = sorted(range(len(pts)), key=lambda i: (pts[i], gf[i]-ga[i], gf[i]), reverse=True)
    
    winners = {k: random.choices(list(v.keys()), weights=list(v.values()))[0] for k, v in eu_probs.items()}
    fa_winner = random.choice(["Chelsea", "Man City"]) # Simplified FA Cup
    
    return {"ranking": ranking, "pts": pts, "gf": gf, "ga": ga, "winners": winners, "fa": fa_winner}

def assign_europe(ranking_idx: List[int], team_list: List[str], winners: Dict, fa: str) -> Dict[str, str]:
    assignments = {}
    for i in range(min(5, len(ranking_idx))): assignments[team_list[ranking_idx[i]]] = "CL"
    if len(ranking_idx) > 5: assignments[team_list[ranking_idx[5]]] = "EL"
    if len(ranking_idx) > 6: assignments[team_list[ranking_idx[6]]] = "Conf"

    if fa in team_list and fa not in assignments: assignments[fa] = "EL"
    if winners["CL"] in team_list: assignments[winners["CL"]] = "CL"
    if winners["EL"] in team_list: assignments[winners["EL"]] = "CL"
    return assignments

# ==============================================================================
# Statistics & Display
# ==============================================================================

def display_summary(g_stats: SimulationGlobalStats, team_list: List[str], sims: int):
    print(f"{'Team':<15}{'AvgPts':<8}{'Title%':<8}{'CL%':<8}{'EL%':<8}{'Releg%':<8}")
    print("-" * 60)
    sorted_idx = sorted(range(len(team_list)), key=lambda i: np.mean(g_stats.pts_dist[i]), reverse=True)
    for i in sorted_idx:
        t = team_list[i]
        avg = np.mean(g_stats.pts_dist[i])
        print(f"{t:<15}{avg:<8.2f}{g_stats.title[t]/sims*100:<8.2f}{g_stats.cl[t]/sims*100:<8.2f}{g_stats.el[t]/sims*100:<8.2f}{g_stats.releg[t]/sims*100:<8.2f}")

# ==============================================================================
# Main Entry Point
# ==============================================================================

def main():
    teams = list(CURRENT_TABLE.keys())
    t_idx = {t: i for i, t in enumerate(teams)}
    pts_arr = np.array([CURRENT_TABLE[t]["Pts"] for t in teams])
    gf_arr = np.array([CURRENT_TABLE[t]["GF"] for t in teams])
    ga_arr = np.array([CURRENT_TABLE[t]["GA"] for t in teams])
    elo_arr = np.array([ELO[t] for t in teams], dtype=np.float64)
    form_arr = np.array([FORM_ADJUSTMENT[t] for t in teams])
    injury_arr = np.array([INJURY_PENALTY[t] for t in teams])
    fix_indices = [(t_idx[h], t_idx[a]) for h, a in FIXTURES]

    eu_probs = {
        "CL": {"Arsenal": 0.4, "Bayern Munich": 0.3, "PSG": 0.2, "Atletico Madrid": 0.1},
        "EL": {"Aston Villa": 0.5, "Forest": 0.3, "Freiburg": 0.1, "Sporting Braga": 0.1},
        "CONF": {"Crystal Palace": 0.6, "Strasbourg": 0.2, "Rayo Vallecano": 0.1, "Shakhtar": 0.1}
    }
    
    g_stats = SimulationGlobalStats(pts_dist=[[] for _ in teams])
    
    for _ in tqdm(range(SIMULATIONS), desc="Simulating"):
        res = run_single_simulation(elo_arr, pts_arr, gf_arr, ga_arr, fix_indices, form_arr, injury_arr, eu_probs)
        rank_idx, pts = res["ranking"], res["pts"]

        g_stats.title[teams[rank_idx[0]]] += 1
        for i, p in enumerate(pts): g_stats.pts_dist[i].append(p)
        for i in rank_idx[-3:]: g_stats.releg[teams[i]] += 1

        assignments = assign_europe(rank_idx, teams, res["winners"], res["fa"])
        for t, comp in assignments.items():
            if comp == "CL": g_stats.cl[t] += 1
            elif comp == "EL": g_stats.el[t] += 1
            elif comp == "Conf": g_stats.conf[t] += 1

    display_summary(g_stats, teams, SIMULATIONS)

if __name__ == "__main__":
    main()
