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
EXTRA_TIME_XG_FACTOR = 0.5

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
    {"team1": "Dinamo Zagreb", "team2": "Viking", "leg1": "2-2"},
    {"team1": "NK Celje", "team2": "Slovan Bratislava", "leg1": "1-1"},
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
    "Villarreal": (50, 1),
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
    "Viking": (300, 1),
    "Sturm Graz": (300, 1),
    "Lech Poznan": (500, 1),
    "Slovan Bratislava": (500, 1),
    "Dinamo Zagreb": (500, 1),
    "Crvena zvezda": (500, 1),
    "NK Celje": (500, 1),
    "Hapoel Beer Sheva": (500, 1)
}

# ==========================================
# CHAMPIONS LEAGUE SIMULATION
# ==========================================


def calculate_cl_elos() -> Dict[str, float]:
    """Derive Elo ratings for all CL teams from betting market odds."""
    # 1. Collect implied probabilities from odds
    team_probs = {}
    for team, odds in BETTING_MARKETS_CL_WINNER.items():
        team_probs[team] = fractional_to_probability(odds)  # e.g., 5/1 → 1/6

    # 2. Normalize to sum to 1 (removes bookmaker overround)
    total_prob = sum(team_probs.values())
    normalized = {team: prob / total_prob for team, prob in team_probs.items()}

    # 3. Number of teams in the final league phase (36)
    n_teams = 36
    baseline_prob = 1.0 / n_teams   # probability if all teams were equal

    # 4. Convert each normalized probability to an Elo rating
    elos = {}
    for team, prob in normalized.items():
        # Ratio of team's chance vs. the equal‑strength baseline
        ratio = prob / baseline_prob
        # Elo difference from average (1500)
        elo_diff = 400 * math.log10(ratio)
        elo = LEAGUE_AVERAGE_ELO + elo_diff
        elos[team] = round(elo, 1)

    return elos



def simulate_playoff_ties(elos):
    winners = []
    for tie in LIVE_PLAYOFF_TIES:
        t1, t2 = tie["team1"], tie["team2"]
        leg1_t1, leg1_t2 = map(int, tie["leg1"].split("-"))
        
        elo1 = elos.get(t1, LEAGUE_AVERAGE_ELO)
        elo2 = elos.get(t2, LEAGUE_AVERAGE_ELO)
        
        # Simulate second leg (t1 home, t2 away)
        # Apply home advantage to t1
        elo_h = elo1 + HOME_ADVANTAGE_ELO
        elo_a = elo2
        xg_h, xg_a = compute_expected_goals(elo_h, elo_a)
        goals_h, goals_a = sample_score(xg_h, xg_a)
        
        agg1 = leg1_t1 + goals_h
        agg2 = leg1_t2 + goals_a
        
        if agg1 == agg2:
            # Extra time (same Poisson with reduced lambdas)
            xg_h_orig, xg_a_orig = compute_expected_goals(elo_h, elo_a)
            xg_et_h = xg_h_orig * EXTRA_TIME_XG_FACTOR
            xg_et_a = xg_a_orig * EXTRA_TIME_XG_FACTOR
            et_h, et_a = sample_score(xg_et_h, xg_et_a)
            agg1 += et_h
            agg2 += et_a
            if agg1 == agg2:
                # Penalties – use Elo probability
                p1 = 1 / (1 + 10 ** (-(elo1 - elo2) / 400))
                winner = t1 if random.random() < p1 else t2
            else:
                winner = t1 if agg1 > agg2 else t2
        else:
            winner = t1 if agg1 > agg2 else t2
        
        winners.append(winner)
    return winners


def generate_swiss_fixtures(teams: List[str], num_rounds: int = 8) -> List[Tuple[int, int]]:
    n = len(teams)
    assert n % 2 == 0
    half = n // 2
    
    fixtures = []
    used_pairs = set()
    home_count = {i: 0 for i in range(n)}
    away_count = {i: 0 for i in range(n)}
    
    # Create a deterministic base fixture list (round‑robin style)
    # This gives each pair exactly once and balances home/away over the season
    indices = list(range(n))
    for r in range(num_rounds):
        # Rotate list for variety (like a circle method)
        rotated = indices[r:] + indices[:r]
        for i in range(half):
            a = rotated[i]
            b = rotated[n - 1 - i]
            if (a, b) in used_pairs or (b, a) in used_pairs:
                continue
            # Assign home/away to balance counts
            if home_count[a] < home_count[b]:
                home, away = a, b
            elif home_count[b] < home_count[a]:
                home, away = b, a
            else:
                # Use round parity to alternate
                home, away = (a, b) if r % 2 == 0 else (b, a)
            
            if home_count[home] < 4 and away_count[away] < 4:
                fixtures.append((home, away))
                used_pairs.add((home, away))
                home_count[home] += 1
                away_count[away] += 1
    
    # Verify completeness – if not perfect, adjust manually
    # (you can add a repair step here)
    return fixtures

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


def simulate_two_legged_tie(team1: str, team2: str, elos: Dict[str, float]) -> str:
    """Simulate a two-legged knockout tie and return the winner."""
    # First leg: team1 at home
    elo_h1 = elos.get(team1, LEAGUE_AVERAGE_ELO) + HOME_ADVANTAGE_ELO
    elo_a1 = elos.get(team2, LEAGUE_AVERAGE_ELO)
    xg_h1, xg_a1 = compute_expected_goals(elo_h1, elo_a1)
    goals_h1, goals_a1 = sample_score(xg_h1, xg_a1)
    
    # Second leg: team2 at home
    elo_h2 = elos.get(team2, LEAGUE_AVERAGE_ELO) + HOME_ADVANTAGE_ELO
    elo_a2 = elos.get(team1, LEAGUE_AVERAGE_ELO)
    xg_h2, xg_a2 = compute_expected_goals(elo_h2, elo_a2)
    goals_h2, goals_a2 = sample_score(xg_h2, xg_a2)
    
    # Aggregate score
    agg_team1 = goals_h1 + goals_a2
    agg_team2 = goals_a1 + goals_h2
    
    if agg_team1 > agg_team2:
        return team1
    elif agg_team2 > agg_team1:
        return team2
    else:
        # Away goals abolished 2021 - go to extra time
        et_xg1 = compute_expected_goals(
            elos.get(team1, LEAGUE_AVERAGE_ELO),
            elos.get(team2, LEAGUE_AVERAGE_ELO),
        )[0] * EXTRA_TIME_XG_FACTOR
        et_xg2 = compute_expected_goals(
            elos.get(team2, LEAGUE_AVERAGE_ELO),
            elos.get(team1, LEAGUE_AVERAGE_ELO),
        )[0] * EXTRA_TIME_XG_FACTOR
        et1, et2 = sample_score(et_xg1, et_xg2)
        if et1 != et2:
            return team1 if et1 > et2 else team2
        # Penalties decided by Elo probability
        elo_diff = elos.get(team1, LEAGUE_AVERAGE_ELO) - elos.get(team2, LEAGUE_AVERAGE_ELO)
        p_team1 = 1 / (1 + 10 ** (-elo_diff / 400))
        return team1 if random.random() < p_team1 else team2


def simulate_knockout_phase(
    qualified_teams: List[str],
    elos: Dict[str, float],
) -> str:
    """Simulate the full CL knockout phase and return the tournament winner.
    
    Structure: 
    - Top 8 teams advance directly to Round of 16
    - Teams 9-24 play two-legged playoff ties to produce 8 more R16 teams
    - Then: Round of 16 → Quarter-finals → Semi-finals → Final
    """
    # Top 8 go straight to Round of 16
    top_8 = qualified_teams[:8]
    
    # Teams 9-24 play playoffs (16 teams → 8 winners)
    playoff_teams = qualified_teams[8:24]
    playoff_winners = []
    
    # Pair them: 9th vs 24th, 10th vs 23rd, etc.
    n_playoff_matches = len(playoff_teams) // 2
    for i in range(n_playoff_matches):
        higher_seed = playoff_teams[i]
        lower_seed = playoff_teams[len(playoff_teams) - 1 - i]
        winner = simulate_two_legged_tie(higher_seed, lower_seed, elos)
        playoff_winners.append(winner)
    
    # Round of 16: top 8 + 8 playoff winners = 16 teams
    r16_teams = top_8 + playoff_winners
    
    # Simulate single-elimination rounds (two-legged ties)
    current = r16_teams
    
    # Round of 16 → 8 teams
    r16_winners = []
    n_r16 = len(current) // 2
    for i in range(n_r16):
        higher = current[i]
        lower = current[len(current) - 1 - i]
        winner = simulate_two_legged_tie(higher, lower, elos)
        r16_winners.append(winner)
    current = r16_winners
    
    # Quarter-finals → 4 teams
    qf_winners = []
    n_qf = len(current) // 2
    for i in range(n_qf):
        higher = current[i]
        lower = current[len(current) - 1 - i]
        winner = simulate_two_legged_tie(higher, lower, elos)
        qf_winners.append(winner)
    current = qf_winners
    
    # Semi-finals → 2 teams
    sf_winners = []
    n_sf = len(current) // 2
    for i in range(n_sf):
        higher = current[i]
        lower = current[len(current) - 1 - i]
        winner = simulate_two_legged_tie(higher, lower, elos)
        sf_winners.append(winner)
    current = sf_winners
    
    # Final (single match at neutral venue)
    if len(current) == 2:
        team1, team2 = current[0], current[1]
        # Neutral venue - no home advantage
        elo_1 = elos.get(team1, LEAGUE_AVERAGE_ELO)
        elo_2 = elos.get(team2, LEAGUE_AVERAGE_ELO)
        xg_1, xg_2 = compute_expected_goals(elo_1, elo_2)
        goals_1, goals_2 = sample_score(xg_1, xg_2)
        
        if goals_1 > goals_2:
            return team1
        elif goals_2 > goals_1:
            return team2
        else:
            # Extra time / penalties
            elo_diff = elo_1 - elo_2
            p_team1 = 1 / (1 + 10 ** (-elo_diff / 400))
            return team1 if random.random() < p_team1 else team2
    
    return current[0] if current else None


def run_champions_league_simulation(num_sims: int = NUM_CL_SIMS) -> Dict[str, float]:
    """Run the full CL simulation and return PL team winner probabilities.

    The league phase determines the top 24 of 36 teams. A knockout phase
    then reduces those 24 to a single tournament winner.
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

    cl_win_counts: Dict[str, int] = defaultdict(int)

    print(f"Step 5: Running {num_sims} CL simulations...")
    for _ in tqdm(range(num_sims), desc="CL Sim"):
        ranked_teams = run_single_cl_simulation(final_teams, elos, fixture_indices)
        qualified = ranked_teams[:24]
        winner = simulate_knockout_phase(qualified, elos)
        if winner:
            cl_win_counts[winner] += 1

    cl_win_probs: Dict[str, float] = {
        team: (cl_win_counts.get(team, 0) / num_sims) * 100
        for team in PL_TEAMS
    }

    print("\n" + "=" * 60)
    print("CHANCE OF WINNING THE CHAMPIONS LEAGUE (PL TEAMS)")
    print("=" * 60)
    for team, prob in sorted(cl_win_probs.items(), key=lambda x: x[1], reverse=True):
        print(f"  {team:<22} {prob:<8.2f}%")

    return cl_win_probs

def verify_fixtures(fixtures: List[Tuple[int, int]], n_teams: int, num_rounds: int = 8) -> Tuple[bool, str]:
    """
    Check that the generated fixture list is valid:
    - Each team plays exactly num_rounds matches.
    - Home/away counts are balanced (num_rounds//2 each).
    - No duplicate pairings (regardless of order).
    - Total matches = n_teams * num_rounds // 2.
    """
    home_count = [0] * n_teams
    away_count = [0] * n_teams
    total_matches = [0] * n_teams
    seen_pairs = set()

    for h, a in fixtures:
        if h == a:
            return False, f"Team {h} plays itself"
        pair = (h, a) if h < a else (a, h)  # Normalize to avoid order issues
        if pair in seen_pairs:
            return False, f"Duplicate match between teams {h} and {a}"
        seen_pairs.add(pair)

        home_count[h] += 1
        away_count[a] += 1
        total_matches[h] += 1
        total_matches[a] += 1

    for i in range(n_teams):
        if total_matches[i] != num_rounds:
            return False, f"Team {i} has {total_matches[i]} matches, expected {num_rounds}"
        if home_count[i] != num_rounds // 2 or away_count[i] != num_rounds // 2:
            return False, f"Team {i} has {home_count[i]} home / {away_count[i]} away, expected {num_rounds//2} each"

    expected_total = n_teams * num_rounds // 2
    if len(fixtures) != expected_total:
        return False, f"Total fixtures = {len(fixtures)}, expected {expected_total}"

    return True, "OK"
# ==========================================
# MAIN ENTRY POINT
# ==========================================

if __name__ == "__main__":
    random.seed(42)
    np.random.seed(42)
    run_champions_league_simulation()