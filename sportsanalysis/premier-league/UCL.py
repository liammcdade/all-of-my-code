"""Champions League 2026/27 simulation module.

Handles playoff simulation, Swiss model fixture generation, and
multi-simulation qualification probability calculation for PL teams.
Results are consumed by 26-27-season.py for Premier League simulation.
"""

import math
import random
from collections import defaultdict
from itertools import combinations
from typing import Dict, List, Tuple

import numpy as np
from tqdm import tqdm

# ==========================================
# GLOBAL CONFIGURATION & CONSTANTS
# ==========================================

HOME_ADVANTAGE_ELO = 85.0
ELO_SCALE = 400.0
LEAGUE_AVERAGE_ELO = 1500.0
ELO_SHRINKAGE = 0.75

NUM_CL_SIMS = 2000
NUM_KNOCKOUT_ROUNDS = 4

MAX_GOALS = 10
_FACTORIALS = np.array([math.factorial(i) for i in range(MAX_GOALS + 1)], dtype=np.float64)

_POISSON_CACHE: Dict[int, np.ndarray] = {}
_LAMBDA_ROUND_PRECISION = 100

BASE_HOME_XG = 1.5
BASE_AWAY_XG = 1.2
XG_ELO_SENSITIVITY = 0.002

PL_TEAMS = ["Arsenal", "Aston Villa", "Liverpool", "Man City", "Man United"]

# ==========================================
# SHARED HELPER FUNCTIONS
# ==========================================


def fractional_to_probability(odds_tuple: Tuple[int, int]) -> float:
    """Convert fractional odds to implied probability."""
    numerator, denominator = odds_tuple
    return denominator / (numerator + denominator)


def probability_to_elo(prob: float, base_elo: float = LEAGUE_AVERAGE_ELO) -> float:
    """Convert win probability to Elo rating relative to base."""
    if prob <= 0 or prob >= 1:
        return base_elo
    elo_diff = -400 * math.log10((1 - prob) / prob)
    return base_elo + elo_diff


def _poisson_pmf(lam: float) -> np.ndarray:
    """Return precomputed/truncated Poisson PMF for lambda."""
    key = int(round(lam * _LAMBDA_ROUND_PRECISION))
    cached = _POISSON_CACHE.get(key)
    if cached is not None:
        return cached
    goals = np.arange(MAX_GOALS + 1, dtype=np.float64)
    pmf = np.exp(-lam) * (lam ** goals) / _FACTORIALS
    total = pmf.sum()
    if total > 0:
        pmf /= total
    _POISSON_CACHE[key] = pmf
    return pmf


def sample_score(lam_home: float, lam_away: float) -> Tuple[int, int]:
    """Sample a (home_goals, away_goals) pair from Poisson distributions."""
    h_pmf = _poisson_pmf(lam_home)
    a_pmf = _poisson_pmf(lam_away)
    h_cdf = np.cumsum(h_pmf)
    a_cdf = np.cumsum(a_pmf)
    h_goal = int(np.searchsorted(h_cdf, np.random.random()))
    a_goal = int(np.searchsorted(a_cdf, np.random.random()))
    return min(h_goal, MAX_GOALS), min(a_goal, MAX_GOALS)


def compute_expected_goals(elo_home: float, elo_away: float) -> Tuple[float, float]:
    """Compute expected goals for home and away teams from Elo ratings."""
    elo_diff = elo_home - elo_away
    xg_h = BASE_HOME_XG * math.exp(XG_ELO_SENSITIVITY * elo_diff)
    xg_a = BASE_AWAY_XG * math.exp(-XG_ELO_SENSITIVITY * elo_diff)
    return xg_h, xg_a


# ==========================================
# CHAMPIONS LEAGUE DATA (2026/27)
# ==========================================

AUTO_QUALIFIED_TEAMS = [
    "Arsenal", "Aston Villa", "Liverpool", "Man City", "Man United",
    "Atletico Madrid", "FC Barcelona", "Real Betis", "Real Madrid", "Villarreal FC",
    "Bayern Munich", "Borussia Dortmund", "RB Leipzig", "VfB Stuttgart",
    "Como", "Inter Milan", "Napoli", "Roma",
    "Paris Saint-Germain", "RC Lens", "Lille OSC",
    "Feyenoord", "PSV Eindhoven",
    "FC Porto", "Sporting CP",
    "Club Brugge", "Slavia Prague", "Galatasaray", "Shakhtar Donetsk",
]

CONFIRMED_PLAYOFF_WINNERS = ["Bodø/Glimt", "LASK", "Sabah FK"]

LIVE_PLAYOFF_TIES = [
    {"team1": "Levski Sofia", "team2": "AEK Athens", "leg1": "0-0"},
    {"team1": "Dinamo Zagreb", "team2": "Viking FK", "leg1": "2-2"},
    {"team1": "NK Celje", "team2": "ŠK Slovan Bratislava", "leg1": "1-1"},
    {"team1": "Olympique Lyonnais", "team2": "Fenerbahçe", "leg1": "1-1"},
]


BETTING_MARKETS_CL_WINNER = {
    "Paris Saint-Germain": (5, 1),    # Bet365 lists PSG at 5/1
    "Bayern Munich": (6, 1),
    "Arsenal": (6, 1),
    "Man City": (7, 1),
    "FC Barcelona": (7, 1),
    "Real Madrid": (7, 1),
    "Liverpool": (10, 1),
    "Man United": (16, 1),
    "Inter Milan": (28, 1),
    "Atletico Madrid": (28, 1),
    "Aston Villa": (33, 1),
    "Borussia Dortmund": (33, 1),
    "Napoli": (40, 1),
    "RB Leipzig": (40, 1),
    "Roma": (50, 1),
    "Real Betis": (66, 1),
    "Villarreal FC": (50, 1),
    "Como": (50, 1),
    "VfB Stuttgart": (50, 1),
    "Sporting CP": (100, 1),
    "FC Porto": (100, 1),
    "PSV Eindhoven": (125, 1),
    "Feyenoord": (125, 1),
    "Lille OSC": (125, 1),
    "RC Lens": (125, 1),
    "Club Brugge": (150, 1),
    "Galatasaray": (150, 1),
    "Shakhtar Donetsk": (250, 1),
    "Slavia Prague": (250, 1),
    "Union SG": (250, 1),
    "AEK Athens": (250, 1),
    "LASK": (300, 1),
    "Viking FK": (300, 1),
    "Sturm Graz": (300, 1),
    "Lech Poznań": (500, 1),
    "ŠK Slovan Bratislava": (500, 1),
    "Dinamo Zagreb": (500, 1),
    "Crvena zvezda": (500, 1),
    "NK Celje": (500, 1),
    "Hapoel Be'er Sheva": (500, 1)
}

# ==========================================
# CHAMPIONS LEAGUE SIMULATION
# ==========================================


def calculate_cl_elos() -> Dict[str, float]:
    """Derive Elo ratings for all CL teams from betting market odds."""
    team_probs: Dict[str, float] = {}
    for team, odds in BETTING_MARKETS_CL_WINNER.items():
        prob = fractional_to_probability(odds)
        team_probs[team] = prob
    total_prob = sum(team_probs.values())
    normalized = {team: prob / total_prob for team, prob in team_probs.items()}
    elos: Dict[str, float] = {}
    for team, prob in normalized.items():
        elo = probability_to_elo(prob, LEAGUE_AVERAGE_ELO)
        elos[team] = round(elo, 1)
    return elos


def simulate_playoff_ties(elos: Dict[str, float]) -> List[str]:
    """Simulate the four remaining playoff ties and return winners."""
    winners: List[str] = []
    for tie in LIVE_PLAYOFF_TIES:
        t1 = tie["team1"]
        t2 = tie["team2"]
        leg1_scores = tie["leg1"].split("-")
        leg1_t1 = int(leg1_scores[0])
        leg1_t2 = int(leg1_scores[1])

        elo1 = elos.get(t1, LEAGUE_AVERAGE_ELO)
        elo2 = elos.get(t2, LEAGUE_AVERAGE_ELO)

        elo_diff = elo1 - elo2
        prob1_win = 1 / (1 + 10 ** (-elo_diff / 400))

        if prob1_win > 0.5:
            leg2_t1 = random.choices([0, 1, 2, 3, 4], weights=[15, 30, 30, 15, 10])[0]
            leg2_t2 = random.choices([0, 1, 2, 3, 4], weights=[25, 35, 25, 10, 5])[0]
        else:
            leg2_t1 = random.choices([0, 1, 2, 3, 4], weights=[25, 35, 25, 10, 5])[0]
            leg2_t2 = random.choices([0, 1, 2, 3, 4], weights=[15, 30, 30, 15, 10])[0]

        agg_t1 = leg1_t1 + leg2_t1
        agg_t2 = leg1_t2 + leg2_t2

        if agg_t1 == agg_t2:
            et_t1 = random.choices([0, 1, 2], weights=[60, 30, 10])[0]
            et_t2 = random.choices([0, 1, 2], weights=[60, 30, 10])[0]
            agg_t1 += et_t1
            agg_t2 += et_t2
            if agg_t1 == agg_t2:
                winner = random.choice([t1, t2])
            else:
                winner = t1 if agg_t1 > agg_t2 else t2
        else:
            winner = t1 if agg_t1 > agg_t2 else t2

        winners.append(winner)
    return winners


def generate_swiss_fixtures(teams: List[str], num_rounds: int = 8) -> List[Tuple[int, int]]:
    """Generate Swiss-model fixtures (4 home, 4 away per team)."""
    n = len(teams)
    fixture_indices: List[Tuple[int, int]] = []
    played_pairs = set()
    home_count = defaultdict(int)
    away_count = defaultdict(int)
    total_games = defaultdict(int)

    all_pairs = list(combinations(range(n), 2))
    random.shuffle(all_pairs)

    rounds: List[List[Tuple[int, int]]] = [[] for _ in range(num_rounds)]

    for r in range(num_rounds):
        used_in_round = set()
        matches_this_round = 0
        candidates = list(all_pairs)
        random.shuffle(candidates)

        for i, j in candidates:
            if matches_this_round >= n // 2:
                break
            if i in used_in_round or j in used_in_round:
                continue
            if (i, j) in played_pairs or (j, i) in played_pairs:
                continue
            if total_games[i] >= num_rounds or total_games[j] >= num_rounds:
                continue

            if home_count[i] < home_count[j]:
                home, away = i, j
            elif home_count[j] < home_count[i]:
                home, away = j, i
            else:
                if random.random() < 0.5:
                    home, away = i, j
                else:
                    home, away = j, i

            if home_count[home] >= 4 or away_count[away] >= 4:
                if home_count[away] < 4 and away_count[home] < 4:
                    home, away = away, home
                else:
                    continue

            rounds[r].append((home, away))
            used_in_round.add(i)
            used_in_round.add(j)
            played_pairs.add((i, j))
            home_count[home] += 1
            away_count[away] += 1
            total_games[i] += 1
            total_games[j] += 1
            matches_this_round += 1

    for r_matches in rounds:
        fixture_indices.extend(r_matches)
    return fixture_indices


def run_single_cl_simulation(
    teams: List[str],
    elos: Dict[str, float],
    fixture_indices: List[Tuple[int, int]],
) -> List[str]:
    """Simulate one CL season and return teams ranked by standing."""
    n_teams = len(teams)
    pts = np.zeros(n_teams, dtype=np.int64)
    gf = np.zeros(n_teams, dtype=np.int64)
    ga = np.zeros(n_teams, dtype=np.int64)

    elo_arr = np.array([elos.get(t, LEAGUE_AVERAGE_ELO) for t in teams], dtype=np.float64)
    elo_arr += HOME_ADVANTAGE_ELO

    for h_idx, a_idx in fixture_indices:
        elo_h = elo_arr[h_idx]
        elo_a = elo_arr[a_idx]
        xg_h, xg_a = compute_expected_goals(elo_h, elo_a)
        goals_h, goals_a = sample_score(xg_h, xg_a)

        gf[h_idx] += goals_h
        ga[h_idx] += goals_a
        gf[a_idx] += goals_a
        ga[a_idx] += goals_h

        if goals_h > goals_a:
            pts[h_idx] += 3
        elif goals_a > goals_h:
            pts[a_idx] += 3
        else:
            pts[h_idx] += 1
            pts[a_idx] += 1

    ranking = sorted(
        range(n_teams),
        key=lambda i: (pts[i], gf[i] - ga[i], gf[i]),
        reverse=True,
    )
    return [teams[i] for i in ranking]


def simulate_knockout_round(
    teams: List[str],
    elos: Dict[str, float],
    winners_needed: int,
) -> List[str]:
    """Simulate a single-elimination knockout round.

    Teams are paired 1st vs 24th, 2nd vs 23rd, etc. (by Elo ranking).
    Each match is decided by Elo-based win probability with Poisson goal sampling.
    Returns the list of winners.
    """
    ranked = sorted(teams, key=lambda t: elos.get(t, LEAGUE_AVERAGE_ELO), reverse=True)
    winners: List[str] = []
    n_matches = len(ranked) // 2

    for i in range(n_matches) if len(ranked) % 2 == 0 else range((len(ranked) - 1) // 2):
        higher = ranked[i]
        lower = ranked[len(ranked) - 1 - i]

        elo_h = elos.get(higher, LEAGUE_AVERAGE_ELO) + HOME_ADVANTAGE_ELO
        elo_a = elos.get(lower, LEAGUE_AVERAGE_ELO)
        xg_h, xg_a = compute_expected_goals(elo_h, elo_a)
        goals_h, goals_a = sample_score(xg_h, xg_a)

        if goals_h > goals_a:
            winners.append(higher)
        elif goals_a > goals_h:
            winners.append(lower)
        else:
            p_home = 1 / (1 + 10 ** (-(elo_h - elo_a) / 400))
            winners.append(higher if random.random() < p_home else lower)

    if len(ranked) % 2 == 1:
        winners.append(ranked[-1])

    return winners[:winners_needed]


def simulate_knockout_phase(
    qualified_teams: List[str],
    elos: Dict[str, float],
) -> str:
    """Simulate the full CL knockout phase and return the tournament winner.
    
    Structure: 
    - Top 8 teams advance directly to Round of 16
    - Teams 9-24 play playoff matches (two-legged) to produce 8 more R16 teams
    - Then: Round of 16 → Quarter-finals → Semi-finals → Final
    """
    # Sort by league phase ranking (already ranked from run_single_cl_simulation)
    # Top 8 go straight through
    top_8 = qualified_teams[:8]
    playoff_teams = qualified_teams[8:24]  # 16 teams
    
    # Simulate playoffs between teams 9-24 (two-legged ties)
    # Pair them: 9th vs 24th, 10th vs 23rd, etc.
    playoff_winners = []
    n_playoff_matches = len(playoff_teams) // 2
    
    for i in range(n_playoff_matches):
        higher_seed = playoff_teams[i]
        lower_seed = playoff_teams[len(playoff_teams) - 1 - i]
        
        # First leg (higher seed at home)
        elo_h = elos.get(higher_seed, LEAGUE_AVERAGE_ELO) + HOME_ADVANTAGE_ELO
        elo_a = elos.get(lower_seed, LEAGUE_AVERAGE_ELO)
        xg_h, xg_a = compute_expected_goals(elo_h, elo_a)
        goals_h_leg1, goals_a_leg1 = sample_score(xg_h, xg_a)
        
        # Second leg (lower seed at home)
        elo_h2 = elos.get(lower_seed, LEAGUE_AVERAGE_ELO) + HOME_ADVANTAGE_ELO
        elo_a2 = elos.get(higher_seed, LEAGUE_AVERAGE_ELO)
        xg_h2, xg_a2 = compute_expected_goals(elo_h2, elo_a2)
        goals_h_leg2, goals_a_leg2 = sample_score(xg_h2, xg_a2)
        
        # Aggregate score
        agg_higher = goals_h_leg1 + goals_a_leg2
        agg_lower = goals_a_leg1 + goals_h_leg2
        
        if agg_higher > agg_lower:
            playoff_winners.append(higher_seed)
        elif agg_lower > agg_higher:
            playoff_winners.append(lower_seed)
        else:
            # Away goals rule or extra time/penalties
            away_higher = goals_a_leg1
            away_lower = goals_h_leg2
            if away_higher > away_lower:
                playoff_winners.append(higher_seed)
            elif away_lower > away_higher:
                playoff_winners.append(lower_seed)
            else:
                # Random if still tied (simplified)
                playoff_winners.append(random.choice([higher_seed, lower_seed]))
    
    # Round of 16: top 8 + 8 playoff winners = 16 teams
    r16_teams = top_8 + playoff_winners
    
    # Now simulate single-elimination rounds
    current = r16_teams
    knockout_sizes = [8, 4, 2]  # QF, SF, Final
    
    for next_size in knockout_sizes:
        if len(current) <= next_size:
            break
        current = simulate_knockout_round(current, elos, next_size)
    
    # Final
    if len(current) == 2:
        elo_h = elos.get(current[0], LEAGUE_AVERAGE_ELO) + HOME_ADVANTAGE_ELO
        elo_a = elos.get(current[1], LEAGUE_AVERAGE_ELO)
        xg_h, xg_a = compute_expected_goals(elo_h, elo_a)
        goals_h, goals_a = sample_score(xg_h, xg_a)
        
        if goals_h > goals_a:
            return current[0]
        elif goals_a > goals_h:
            return current[1]
        else:
            p_home = 1 / (1 + 10 ** (-(elo_h - elo_a) / 400))
            return current[0] if random.random() < p_home else current[1]
    
    return current[0] if current else None


def run_champions_league_simulation(num_sims: int = NUM_CL_SIMS) -> Dict[str, float]:
    """Run the full CL simulation and return PL team winner probabilities.

    The league phase determines the top 24 of 36 teams. A knockout phase
    then reduces those 24 to a single tournament winner via single
    elimination (Round of 24 → 16 → 8 → 4 → 2 → Final).
    Returns a dict mapping PL team names to their chance of winning the
    Champions League (0-100).
    """
    print("\nSTARTING UEFA CHAMPIONS LEAGUE 2026/27 SIMULATION")
    print(f"Number of Simulations: {num_sims}")

    print("\nStep 1: Calculating Elo ratings from betting odds...")
    elos = calculate_cl_elos()

    print("Step 2: Simulating remaining play-off matches...")
    playoff_winners = simulate_playoff_ties(elos)

    final_teams: List[str] = (
        list(AUTO_QUALIFIED_TEAMS) + list(CONFIRMED_PLAYOFF_WINNERS) + playoff_winners
    )
    for winner in playoff_winners:
        print(f"  Play-off winner: {winner}")

    print(f"Step 3: {len(final_teams)} teams in league phase.")

    print("Step 4: Generating Swiss-model fixtures (8 matches per team)...")
    fixture_indices = generate_swiss_fixtures(final_teams)

    cl_win_counts: Dict[str, int] = {t: 0 for t in PL_TEAMS}

    print(f"Step 5: Running {num_sims} CL simulations...")
    for _ in tqdm(range(num_sims), desc="CL Sim"):
        ranked_teams = run_single_cl_simulation(final_teams, elos, fixture_indices)
        qualified = ranked_teams[:24]
        winner = simulate_knockout_phase(qualified, elos)
        if winner in cl_win_counts:
            cl_win_counts[winner] += 1

    cl_win_probs: Dict[str, float] = {
        team: (count / num_sims) * 100 for team, count in cl_win_counts.items()
    }

    print("\n" + "=" * 60)
    print("CHANCE OF WINNING THE CHAMPIONS LEAGUE (PL TEAMS)")
    print("=" * 60)
    for team, prob in sorted(cl_win_probs.items(), key=lambda x: x[1], reverse=True):
        print(f"  {team:<22} {prob:<8.2f}%")

    return cl_win_probs


# ==========================================
# MAIN ENTRY POINT
# ==========================================

if __name__ == "__main__":
    random.seed(42)
    np.random.seed(42)
    run_champions_league_simulation()
