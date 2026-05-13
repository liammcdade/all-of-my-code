import random
import math
from collections import defaultdict
from dataclasses import dataclass
from tqdm import tqdm
import numba
from typing import Dict, List, Tuple

# ====================== CONSTANTS ======================
HOME_ADVANTAGE = 33.8
K_FACTOR = 25
BASE_XG = 0.7
MAX_XG = 1.8
ELO_SCALE = 400
XG_SCALE = 300
CLOSENESS_SCALE = 180
INJURY_SCALE = 80
TEMPO_BASE = 0.9
TEMPO_RANGE = 0.1
VARIANCE_BOOST_FACTOR = 0.2
SHARED_GOAL_BASE = 0.05
SHARED_GOAL_CLOSENESS = 0.25
MIN_LAMBDA = 0.05
NUM_SIMS = 10000
PROB_SAMPLE_SIZE = 2000


# ====================== DATA MODELS ======================
@dataclass
class TeamData:
    elo: float
    form_adjustment: float
    injury_penalty: float

# ====================== TEAM REGISTRY ======================
class TeamRegistry:
    def __init__(self):
        self.teams: Dict[str, TeamData] = {}
        self.base_table: Dict[str, Dict[str, int]] = {}

    def add_team(self, name: str, elo: float, form: float = 0.0, injury: float = 0.0):
        self.teams[name] = TeamData(elo=elo, form_adjustment=form, injury_penalty=injury)
        self.base_table[name] = {"MP": 0, "Pts": 0, "GF": 0, "GA": 0}

    def remove_team(self, name: str):
        self.teams.pop(name, None)
        self.base_table.pop(name, None)

    def get_team_names(self) -> List[str]:
        return list(self.base_table.keys())

    def get_elo(self, name: str) -> float:
        return self.teams[name].elo if name in self.teams else 0.0

    def get_adjusted_elo(self, name: str, current_elo: Dict[str, float]) -> float:
        if name not in self.teams:
            raise ValueError(f"Unknown team: {name}")
        team = self.teams.get(name)
        if team is None:
            return current_elo.get(name, 0.0)
        penalty = team.injury_penalty * (1 - math.exp(-team.injury_penalty / INJURY_SCALE))
        return current_elo.get(name, team.elo) - penalty + team.form_adjustment

# ====================== MATCH PARAMETER CACHE ======================
match_param_cache: Dict[Tuple[str, str, int, int], Tuple[float, float, float, float]] = {}

def clear_match_cache():
    match_param_cache.clear()

@numba.jit(nopython=True, cache=True)
def calculate_match_params(adjusted_home: float, adjusted_away: float, home_advantage: float, base_xg: float, max_xg: float, xg_scale: float, closeness_scale: float) -> Tuple[float, float, float, float]:
    diff = adjusted_home - adjusted_away + home_advantage
    home_xg = base_xg + max_xg / (1 + math.exp(-diff / xg_scale))
    away_xg = base_xg + max_xg / (1 + math.exp(diff / xg_scale))
    closeness = math.exp(-(diff**2) / (2 * closeness_scale**2))
    return home_xg, away_xg, closeness, diff

def get_match_params(home: str, away: str, adjusted_home: float, adjusted_away: float) -> Tuple[float, float, float, float]:
    key = (home, away, round(adjusted_home, 1), round(adjusted_away, 1))
    if key in match_param_cache:
        return match_param_cache[key]
    home_xg, away_xg, closeness, diff = calculate_match_params(
        adjusted_home, adjusted_away, HOME_ADVANTAGE, BASE_XG, MAX_XG, XG_SCALE, CLOSENESS_SCALE
    )
    match_param_cache[key] = (home_xg, away_xg, closeness, diff)
    return match_param_cache[key]

# ====================== POISSON ======================
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

# ====================== MATCH SIMULATION ======================
@numba.jit(nopython=True, cache=True)
def _simulate_poisson_match_numba(home_xg: float, away_xg: float, closeness: float, diff: float) -> Tuple[int, int]:
    tempo_factor = TEMPO_BASE + TEMPO_RANGE * (abs(diff) / ELO_SCALE)
    home_xg_adjusted = home_xg * tempo_factor
    away_xg_adjusted = away_xg * tempo_factor

    lambda_shared = SHARED_GOAL_BASE + closeness * SHARED_GOAL_CLOSENESS

    variance_boost = 1 + VARIANCE_BOOST_FACTOR

    lambda_home = max(MIN_LAMBDA, (home_xg_adjusted - lambda_shared) * variance_boost)
    lambda_away = max(MIN_LAMBDA, away_xg_adjusted - lambda_shared)

    shared_goals = poisson_random_numba(lambda_shared)
    home_goals = poisson_random_numba(lambda_home)
    away_goals = poisson_random_numba(lambda_away)

    home_goals += shared_goals
    away_goals += shared_goals

    return home_goals, away_goals

def simulate_match(home: str, away: str, current_elo: Dict[str, float], registry: TeamRegistry) -> Tuple[int, int]:
    if home not in registry.teams:
        raise ValueError(f"Unknown home team: {home}")
    if away not in registry.teams:
        raise ValueError(f"Unknown away team: {away}")
    adjusted_home = registry.get_adjusted_elo(home, current_elo)
    adjusted_away = registry.get_adjusted_elo(away, current_elo)
    home_xg, away_xg, closeness, diff = get_match_params(home, away, adjusted_home, adjusted_away)
    return _simulate_poisson_match_numba(home_xg, away_xg, closeness, diff)

# ====================== RESULT APPLICATION ======================
def apply_result(table: Dict[str, Dict[str, int]], home: str, away: str, home_goals: int, away_goals: int) -> None:
    table[home]["GF"] += home_goals
    table[home]["GA"] += away_goals
    table[away]["GF"] += away_goals
    table[away]["GA"] += home_goals

    if home_goals > away_goals:
        table[home]["Pts"] += 3
    elif away_goals > home_goals:
        table[away]["Pts"] += 3
    else:
        table[home]["Pts"] += 1
        table[away]["Pts"] += 1

def update_elo(current_elo: Dict[str, float], home: str, away: str, home_goals: int, away_goals: int) -> None:
    home_elo = current_elo.get(home, 0.0)
    away_elo = current_elo.get(away, 0.0)
    diff = home_elo - away_elo
    expected_home = 1 / (1 + 10 ** (-diff / ELO_SCALE))
    expected_away = 1 - expected_home

    if home_goals > away_goals:
        score_home, score_away = 1.0, 0.0
    elif home_goals == away_goals:
        score_home, score_away = 0.5, 0.5
    else:
        score_home, score_away = 0.0, 1.0

    current_elo[home] = home_elo + K_FACTOR * (score_home - expected_home)
    current_elo[away] = away_elo + K_FACTOR * (score_away - expected_away)

# ====================== FIXTURE GENERATION ======================
def generate_round_robin_fixtures(teams: List[str]) -> List[Tuple[str, str]]:
    if len(teams) % 2 != 0:
        teams = teams + ["BYE"]

    fixtures: List[Tuple[str, str]] = []
    n = len(teams)

    for _ in range(n - 1):
        round_fixtures: List[Tuple[str, str]] = []
        for i in range(n // 2):
            home = teams[i]
            away = teams[n - 1 - i]
            if home != "BYE" and away != "BYE":
                round_fixtures.append((home, away))
        fixtures.extend(round_fixtures)
        teams = [teams[0]] + [teams[-1]] + teams[1:-1]

    reverse_fixtures = [(away, home) for home, away in fixtures]
    fixtures.extend(reverse_fixtures)
    return fixtures

# ====================== CHAMPIONSHIP PLAYOFFS ======================
CHAMPIONSHIP_ELO: Dict[str, float] = {
    
    "Southampton": 1635,
    
    "Hull City": 1637,
}

CURRENT_CHAMPIONSHIP_POINTS: Dict[str, int] = {
    "Southampton": 86,
    
    "Hull City": 72,
}
# hull vs southampton are in the final 
def simulate_playoffs() -> str:
    temp_registry = TeamRegistry()
    for team, elo in CHAMPIONSHIP_ELO.items():
        temp_registry.add_team(team, elo)

    current_elo = {team: CHAMPIONSHIP_ELO[team] for team in CHAMPIONSHIP_ELO}

    home_goals, away_goals = simulate_match("Hull City", "Southampton", current_elo, temp_registry)

    if home_goals > away_goals:
        return "Hull City"
    elif away_goals > home_goals:
        return "Southampton"
    else:
        return "Hull City" if random.random() < 0.5 else "Southampton"

# ====================== SIMULATION ENGINE ======================
@numba.jit(nopython=True, cache=True, parallel=True)
def run_simulation_numba(
    fixtures: List[Tuple[int, int]],
    elo_array: List[float],
    k_factor: float,
    elo_scale: float
) -> Tuple[List[int], List[int], List[int], List[int], List[float]]:
    n_teams = len(elo_array)
    table_pts = [0] * n_teams
    table_gf = [0] * n_teams
    table_ga = [0] * n_teams
    current_elo = elo_array.copy()

    for idx in range(len(fixtures)):
        home_idx, away_idx = fixtures[idx]
        home_elo = current_elo[home_idx]
        away_elo = current_elo[away_idx]
        diff = home_elo - away_elo
        expected_home = 1.0 / (1.0 + 10.0 ** (-diff / elo_scale))

        home_xg, away_xg, closeness, match_diff = calculate_match_params(
            home_elo, away_elo, HOME_ADVANTAGE, BASE_XG, MAX_XG, XG_SCALE, CLOSENESS_SCALE
        )
        home_goals, away_goals = _simulate_poisson_match_numba(home_xg, away_xg, closeness, match_diff)

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

def run_simulation(registry: TeamRegistry, fixtures: List[Tuple[str, str]]) -> Tuple[Dict[str, int], Dict[str, int], int]:
    current_elo = {name: registry.get_elo(name) for name in registry.get_team_names()}
    table: Dict[str, Dict[str, int]] = {name: {"MP": 0, "Pts": 0, "GF": 0, "GA": 0} for name in registry.get_team_names()}

    for home, away in fixtures:
        home_goals, away_goals = simulate_match(home, away, current_elo, registry)
        apply_result(table, home, away, home_goals, away_goals)
        update_elo(current_elo, home, away, home_goals, away_goals)

    ranking = sorted(table.items(), key=lambda x: (x[1]["Pts"], x[1]["GF"] - x[1]["GA"], x[1]["GF"]), reverse=True)
    return table, ranking, ranking[0][1]["Pts"]

# ====================== MATCH PROBABILITIES ======================
def precompute_match_probs(registry: TeamRegistry, fixtures: List[Tuple[str, str]]) -> Dict[Tuple[str, str], Tuple[float, float, float]]:
    match_prob_cache: Dict[Tuple[str, str], Tuple[float, float, float]] = {}
    for home, away in fixtures:
        home_wins = draw_count = away_wins = 0
        for _ in range(PROB_SAMPLE_SIZE):
            hg, ag = simulate_match(home, away, {name: registry.get_elo(name) for name in registry.get_team_names()}, registry)
            if hg > ag:
                home_wins += 1
            elif hg == ag:
                draw_count += 1
            else:
                away_wins += 1
        match_prob_cache[(home, away)] = (home_wins / PROB_SAMPLE_SIZE * 100, draw_count / PROB_SAMPLE_SIZE * 100, away_wins / PROB_SAMPLE_SIZE * 100)
    return match_prob_cache

# ====================== OUTPUT ======================
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

    print(f"{'Team':<15}{'AvgPts':<8}{'StdDev':<8}{'Title%':<8}{'CL%':<8}{'Europa%':<8}{'Releg%':<8}")
    print("-" * 72)
    for team in sorted(results["points_distribution"].keys(), key=lambda x: sum(results["avg_points"][x]) / sims, reverse=True):
        print(
            f"{team:<15}"
            f"{sum(results['avg_points'][team]) / sims:<8.2f}"
            f"{team_stats[team]['std']:<8.2f}"
            f"{results['title'].get(team, 0) / sims * 100:<8.2f}"
            f"{results['top4'].get(team, 0) / sims * 100:<8.2f}"
            f"{results['europa'].get(team, 0) / sims * 100:<8.2f}"
            f"{results['releg'].get(team, 0) / sims * 100:.2f}"
        )

def display_match_probabilities(match_prob_cache: Dict[Tuple[str, str], Tuple[float, float, float]], fixtures: List[Tuple[str, str]]) -> None:
    max_home_win = max_draw = max_away_win = 0
    max_home_match = max_draw_match = max_away_match = None

    for home, away in fixtures:
        hw, dr, aw = match_prob_cache[(home, away)]
        print(f"{home:<15} vs {away:<15}: {hw:<6.2f}% | {dr:<6.2f}% | {aw:<6.2f}%")
        if hw > max_home_win:
            max_home_win, max_home_match = hw, (home, away)
        if dr > max_draw:
            max_draw, max_draw_match = dr, (home, away)
        if aw > max_away_win:
            max_away_win, max_away_match = aw, (home, away)

    print(f"\nBiggest Home Win Chance: {max_home_match[0]} vs {max_home_match[1]} - {max_home_win:.2f}%")
    print(f"Most Likely Draw: {max_draw_match[0]} vs {max_draw_match[1]} - {max_draw:.2f}%")
    print(f"Biggest Away Win Chance: {max_away_match[0]} vs {max_away_match[1]} - {max_away_win:.2f}%")

def display_fixture_probabilities(match_prob_cache: Dict[Tuple[str, str], Tuple[float, float, float]], teams: List[str]) -> None:
    team_fixtures: Dict[str, List[Tuple[str, str]]] = defaultdict(list)
    for home, away in match_prob_cache.keys():
        team_fixtures[home].append(("home", away))
        team_fixtures[away].append(("away", home))

    avg_win_prob: Dict[str, float] = {}
    win_all: Dict[str, float] = {}
    lose_all: Dict[str, float] = {}
    draw_all: Dict[str, float] = {}

    for team in teams:
        p_win = p_lose = p_draw = 1.0
        win_probs: List[float] = []
        for is_home, opponent in team_fixtures[team]:
            match_key = (opponent, team) if is_home == "away" else (team, opponent)
            hw, dr, aw = match_prob_cache[match_key]
            if is_home == "home":
                t_win, t_draw, t_lose = hw / 100, dr / 100, aw / 100
            else:
                t_win, t_draw, t_lose = aw / 100, dr / 100, hw / 100
            p_win *= t_win
            p_lose *= t_lose
            p_draw *= t_draw
            win_probs.append(t_win)
        win_all[team] = p_win * 100
        lose_all[team] = p_lose * 100
        draw_all[team] = p_draw * 100
        avg_win_prob[team] = sum(win_probs) / len(win_probs) * 100 if win_probs else 0

    print(f"\n{'Team':<15}{'Win All %':<12}{'Lose All %':<12}{'Draw All %':<12}{'Avg Win %'}")
    print("-" * 65)
    for team in sorted(teams, key=lambda x: avg_win_prob[x], reverse=True):
        print(f"{team:<15}{win_all[team]:<12.4f}{lose_all[team]:<12.4f}{draw_all[team]:<12.4f}{avg_win_prob[team]:.2f}%")

# ====================== MAIN ======================
def run_single_simulation(registry: TeamRegistry) -> Tuple[Dict[str, int], Dict[str, int], int, str]:
    promoted = simulate_playoffs()
    registry.add_team(promoted, CHAMPIONSHIP_ELO[promoted])
    fixtures = generate_round_robin_fixtures(registry.get_team_names())
    clear_match_cache()
    table, ranking, champ_pts = run_simulation(registry, fixtures)
    registry.remove_team(promoted)
    return table, ranking, champ_pts, promoted

def main():
    registry = TeamRegistry()

    elo_ratings: Dict[str, float] = {
        "Arsenal": 1895, "Man City": 1885, "Liverpool": 1845, "Aston Villa": 1755,
        "Man United": 1725, "Chelsea": 1795, "Brighton": 1705, "Brentford": 1645,
        "Everton": 1605, "Bournemouth": 1665, "Coventry": 1495, "Fulham": 1620,
        "Ipswich": 1515, "Sunderland": 1490, "Crystal Palace": 1640, "Leeds": 1540,
        "Newcastle": 1785, "Nottingham": 1680,
    }
    for name, elo in elo_ratings.items():
        registry.add_team(name, elo)

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
        table, ranking, champ_pts, promoted = run_single_simulation(registry)
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

    all_teams = registry.get_team_names()
    all_fixtures = generate_round_robin_fixtures(all_teams)
    match_prob_cache = precompute_match_probs(registry, all_fixtures)

    for team in CHAMPIONSHIP_ELO:
        registry.remove_team(team)

    print("\n" + "=" * 60)
    print("TEAM STATISTICS")
    print("=" * 60)
    display_team_statistics(aggregated_results, NUM_SIMS)

    print("\n" + "=" * 60)
    print("MATCH PROBABILITIES (Home Win % | Draw % | Away Win %)")
    print("=" * 60)
    display_match_probabilities(match_prob_cache, all_fixtures)

    print("\n" + "=" * 60)
    print("TEAM REMAINING FIXTURE PROBABILITIES")
    print("=" * 60)
    display_fixture_probabilities(match_prob_cache, all_teams)

    print("\n" + "=" * 40)
    print("POINTS TO WIN THE LEAGUE")
    print("=" * 40)
    print(f"Max points to win the league: {max(champion_points)}")
    print(f"Min points to win the league: {min(champion_points)}")

    print("\n" + "=" * 40)
    print("ADDITIONAL STATISTICS")
    print("=" * 40)
    print(f"Probability that at least one team is relegated with 40+ points: {releg_40_count / NUM_SIMS * 100:.4f}%")
    print(f"Average excitement score for the final day (out of 10): {sum(excitement_scores) / len(excitement_scores) / 10:.2f}")

if __name__ == "__main__":
    main()
