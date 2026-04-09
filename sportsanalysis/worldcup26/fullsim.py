import pandas as pd
import numpy as np
import random
from tqdm import tqdm
from itertools import product
from reportlab.lib.pagesizes import letter
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle
from reportlab.lib import colors
from reportlab.lib.units import inch
import io
import math


number_of_qualified_teams = 48

# -------------------------
# CONFIG / GROUPS (no 'points' entries)
# -------------------------
GROUPS = {
    'A': {
        'teams': ['Mexico', 'South Africa', 'South Korea', 'Czech Republic'],
        'matches': [
            ('Mexico', 'South Africa'),
            ('South Korea', 'Czech Republic'),
            ('Czech Republic', 'South Africa'),
            ('Mexico', 'South Korea'),
            ('Czech Republic', 'Mexico'),
            ('South Africa', 'South Korea')
        ]
    },
    'B': {
        'teams': ['Canada', 'Qatar', 'Switzerland', 'Bosnia and Herzegovina'],
        'matches': [
            ('Canada', 'Bosnia and Herzegovina'),
            ('Qatar', 'Switzerland'),
            ('Switzerland', 'Bosnia and Herzegovina'),
            ('Canada', 'Qatar'),
            ('Switzerland', 'Canada'),
            ('Bosnia and Herzegovina', 'Qatar')
        ]
    },
    'C': {
        'teams': ['Brazil', 'Morocco', 'Haiti', 'Scotland'],
        'matches': [
            ('Brazil', 'Morocco'),
            ('Haiti', 'Scotland'),
            ('Brazil', 'Haiti'),
            ('Scotland', 'Morocco'),
            ('Scotland', 'Brazil'),
            ('Morocco', 'Haiti')
        ]
    },
    'D': {
        'teams': ['United States', 'Paraguay', 'Australia', 'Turkey'],
        'matches': [
            ('United States', 'Paraguay'),
            ('Australia', 'Turkey'),
            ('Turkey', 'Paraguay'),
            ('United States', 'Australia'),
            ('Turkey', 'United States'),
            ('Paraguay', 'Australia')
        ]
    },
    'E': {
        'teams': ['Germany', 'Curaçao', 'Ivory Coast', 'Ecuador'],
        'matches': [
            ('Germany', 'Curaçao'),
            ('Ivory Coast', 'Ecuador'),
            ('Germany', 'Ivory Coast'),
            ('Ecuador', 'Curaçao'),
            ('Ecuador', 'Germany'),
            ('Curaçao', 'Ivory Coast')
        ]
    },
    'F': {
        'teams': ['Netherlands', 'Japan', 'Sweden', 'Tunisia'],
        'matches': [
            ('Netherlands', 'Japan'),
            ('Sweden', 'Tunisia'),
            ('Netherlands', 'Sweden'),
            ('Tunisia', 'Japan'),
            ('Tunisia', 'Netherlands'),
            ('Japan', 'Sweden')
        ]
    },
    'G': {
        'teams': ['Belgium', 'Egypt', 'Iran', 'New Zealand'],
        'matches': [
            ('Belgium', 'Egypt'),
            ('Iran', 'New Zealand'),
            ('Belgium', 'Iran'),
            ('New Zealand', 'Egypt'),
            ('New Zealand', 'Belgium'),
            ('Egypt', 'Iran')
        ]
    },
    'H': {
        'teams': ['Spain', 'Cape Verde', 'Saudi Arabia', 'Uruguay'],
        'matches': [
            ('Spain', 'Cape Verde'),
            ('Saudi Arabia', 'Uruguay'),
            ('Spain', 'Saudi Arabia'),
            ('Uruguay', 'Cape Verde'),
            ('Uruguay', 'Spain'),
            ('Cape Verde', 'Saudi Arabia')
        ]
    },
    'I': {
        'teams': ['France', 'Senegal', 'Iraq', 'Norway'],
        'matches': [
            ('France', 'Senegal'),
            ('Iraq', 'Norway'),
            ('France', 'Iraq'),
            ('Norway', 'Senegal'),
            ('Norway', 'France'),
            ('Senegal', 'Iraq')
        ]
    },
    'J': {
        'teams': ['Argentina', 'Algeria', 'Austria', 'Jordan'],
        'matches': [
            ('Argentina', 'Algeria'),
            ('Austria', 'Jordan'),
            ('Argentina', 'Austria'),
            ('Jordan', 'Algeria'),
            ('Jordan', 'Argentina'),
            ('Algeria', 'Austria')
        ]
    },
    'K': {
        'teams': ['Portugal', 'Congo DR', 'Uzbekistan', 'Colombia'],
        'matches': [
            ('Portugal', 'Congo DR'),
            ('Uzbekistan', 'Colombia'),
            ('Portugal', 'Uzbekistan'),
            ('Colombia', 'Congo DR'),
            ('Colombia', 'Portugal'),
            ('Congo DR', 'Uzbekistan')
        ]
    },
    'L': {
        'teams': ['England', 'Croatia', 'Panama', 'Ghana'],
        'matches': [
            ('England', 'Croatia'),
            ('England', 'Panama'),
            ('England', 'Ghana'),
            ('Croatia', 'Panama'),
            ('Croatia', 'Ghana'),
            ('Panama', 'Ghana')
        ]
    }
}

# =============================================================================
# CONFIGURATION AND DATA
# =============================================================================

# -------------------------
# CANONICAL TEAM NAMES AND ALIASES
# -------------------------
# Ensures consistent team identification across the simulation
TEAM_CANONICAL = {
    # Alias -> Canonical name
    'USA': 'United States',
    'US': 'United States',
    'USA United States': 'United States',
    'USAmericans': 'United States',
}

# Canonical team name for host nations (used throughout)
HOST_TEAMS = {
    'A': 'Mexico',
    'B': 'Canada', 
    'D': 'United States'
}

# -------------------------
# HOME ADVANTAGE BONUSES
# -------------------------
# Home advantage expressed as goal expectancy boost (more intuitive than Elo)
# Research suggests home teams score ~0.35-0.45 more goals on average
# In the 2026 World Cup:
# - Mexico (Group A): Strong home advantage in US/Canada/Mexico venues
# - United States (Group D): Home advantage, but shared with Canada
# - Canada (Group B): Home advantage, shared with United States
HOME_ADVANTAGE = {
    'Mexico': 0.38,       # ~0.38 goal boost (strong home advantage)
    'United States': 0.30, # ~0.30 goal boost (shared host, slightly reduced)
    'Canada': 0.30        # ~0.30 goal boost (shared host, slightly reduced)
}


def get_canonical_name(team_name):
    """
    Return the canonical name for a team, handling common aliases.
    
    This ensures consistent team identification:
    - 'USA', 'US' -> 'United States'
    """
    return TEAM_CANONICAL.get(team_name, team_name)


def resolve_team_name(team_name, team_ratings):
    """
    Resolve a team name to its canonical form and return the rating.
    
    Checks aliases first, then falls back to the original name.
    """
    canonical = get_canonical_name(team_name)
    if canonical in team_ratings:
        return canonical
    # Fallback to original if canonical not found
    return team_name



def apply_home_advantage(lambda_a, lambda_b, team_a, team_b, group_key=None):
    """
    Apply home advantage as a multiplicative boost on the home team's expected goals.

    Uses the calibrated HOME_ADVANTAGE dictionary values:
    - Group stage: host nations playing in their designated home group get full advantage
    - All three host nations get reduced advantage when playing in any of the three host groups
    - Knockout matches: host nations get half their home advantage value
    - Neutral matches: no adjustment

    Parameters:
    - lambda_a, lambda_b: Expected goals for each team
    - team_a, team_b: Team names
    - group_key: Group letter for group stage (None for knockout)

    Returns: (adjusted_lambda_a, adjusted_lambda_b)
    """

    # Group stage: groups A, B, D are all host nation groups
    if group_key in ['A', 'B', 'D']:
        # Full home boost for the designated host of this specific group
        designated_host = HOST_TEAMS[group_key]
        if team_a == designated_host:
            lambda_a *= (1 + HOME_ADVANTAGE[team_a])
        elif team_b == designated_host:
            lambda_b *= (1 + HOME_ADVANTAGE[team_b])
        
        # Reduced boost for the other two co-host nations playing in this group
        other_hosts = [host for gk, host in HOST_TEAMS.items() if gk != group_key]
        for host in other_hosts:
            if team_a == host:
                lambda_a *= (1 + HOME_ADVANTAGE[team_a] / 2)
            elif team_b == host:
                lambda_b *= (1 + HOME_ADVANTAGE[team_b] / 2)

    # Knockout stage: host nations get reduced advantage everywhere
    elif group_key is None:
        if team_a in HOST_TEAMS.values():
            lambda_a *= (1 + HOME_ADVANTAGE[team_a] / 2)
        if team_b in HOST_TEAMS.values():
            lambda_b *= (1 + HOME_ADVANTAGE[team_b] / 2)

    return lambda_a, lambda_b

# =============================================================================
# SINGLE AUTHORITATIVE TEAM RATINGS SOURCE
# =============================================================================

# Base ratings for all teams (canonical names only)
BASE_TEAM_RATINGS = {
    'Spain': 2165,
    'Argentina': 2113,
    'France': 2082,
    'England': 2020,

    'Colombia': 1975,
    'Portugal': 1973,
    'Brazil': 1970,
    'Netherlands': 1965,

    'Croatia': 1944,
    'Ecuador': 1929,
    'Germany': 1923,
    'Norway': 1916,

    'Uruguay': 1890,
    'Switzerland': 1885,
    'Japan': 1878,
    'Denmark': 1872,
    'Senegal': 1869,
    'Italy': 1866,
    'Mexico': 1857,
    'Belgium': 1850,

    'Paraguay': 1833,
    'Austria': 1818,
    'Morocco': 1806,
    'Canada': 1805,
    'Scotland': 1790,
    'South Korea': 1784,
    'Australia': 1779,

    'Iran': 1755,
    'United States': 1747,
    'Poland': 1746,
    'Kosovo': 1738,
    'Panama': 1733,
    'Algeria': 1728,
    'Uzbekistan': 1728,
    'Czech Republic': 1723,
    'Sweden': 1702,
    'Turkey': 1698,

    'Jordan': 1687,
    'Bolivia': 1670,
    'Ivory Coast': 1663,
    'Egypt': 1659,
    'Congo DR': 1640,
    'Tunisia': 1614,
    'Bosnia and Herzegovina': 1584,
    'Iraq': 1582,
    'New Zealand': 1585,
    'Saudi Arabia': 1571,

    'Jamaica': 1550,
    'Cape Verde': 1549,
    'Haiti': 1542,
    'Ghana': 1509,
    'Curaçao': 1440,
}

# =============================================================================
# RATING CACHING AND LOOKUP SYSTEM
# =============================================================================

# Cached ratings - populated on first access
_rating_cache = {}
_cache_initialized = False


def initialize_ratings_cache():
    """
    Initialize the ratings cache with BASE_TEAM_RATINGS.
    Called once at startup.
    """
    global _rating_cache, _cache_initialized
    if not _cache_initialized:
        _rating_cache = BASE_TEAM_RATINGS.copy()
        _cache_initialized = True


def get_rating(team_name):
    """
    Get rating for a team with caching and alias resolution.
    
    This is the SINGLE canonical function for rating lookups.
    
    Performance: O(1) lookup after initialization
    """
    global _rating_cache, _cache_initialized
    
    # Initialize cache on first call
    if not _cache_initialized:
        initialize_ratings_cache()
    
    # Resolve aliases first
    canonical_name = get_canonical_name(team_name)
    
    # Check cache
    if canonical_name in _rating_cache:
        return float(_rating_cache[canonical_name])
    
    # Check original name (for placeholders, etc.)
    if team_name in _rating_cache:
        return float(_rating_cache[team_name])
    
    # Fallback: check if this is a placeholder that needs resolution
    # This handles cases like 'UEFA_Path_A_Winner' where we need to
    # average candidate ratings
    return _resolve_placeholder_rating(team_name)


def _resolve_placeholder_rating(placeholder_name):
    """
    Resolve placeholder teams (e.g., UEFA_Path_A_Winner) to average of candidates.
    Uses BASE_TEAM_RATINGS for candidate lookups.
    """
    # Check if this placeholder exists in GROUPS possible_winners
    for group in GROUPS.values():
        if 'possible_winners' in group:
            for placeholder, opts in group['possible_winners'].items():
                if placeholder == placeholder_name:
                    ratings = []
                    for o in opts:
                        if isinstance(o, tuple):
                            ratings.append(float(o[1]))
                        else:
                            # Use BASE_TEAM_RATINGS for lookup
                            canonical = get_canonical_name(o)
                            rating = BASE_TEAM_RATINGS.get(canonical, BASE_TEAM_RATINGS.get(o, 1500.0))
                            ratings.append(float(rating))
                    return float(np.mean(ratings) if ratings else 1500.0)
    
    # Final fallback
    return 1500.0


def get_tournament_teams():
    """
    Get all teams that are in or can qualify for the tournament.
    Uses BASE_TEAM_RATINGS for lookups.
    """
    teams = set()
    for group in GROUPS.values():
        for team in group['teams']:
            canonical = get_canonical_name(team)
            if canonical in BASE_TEAM_RATINGS or team in BASE_TEAM_RATINGS:
                teams.add(canonical if canonical in BASE_TEAM_RATINGS else team)
            elif 'possible_winners' in group:
                for placeholder, opts in group['possible_winners'].items():
                    if placeholder == team:
                        for o in opts:
                            team_name = o[0] if isinstance(o, tuple) else o
                            canonical = get_canonical_name(team_name)
                            teams.add(canonical if canonical in BASE_TEAM_RATINGS else team_name)
    return list(teams)


# For backward compatibility, create teams_ratings as filtered version
# This will be populated dynamically based on tournament participants
# For backward compatibility, create teams_ratings as a proxy to BASE_TEAM_RATINGS
# This avoids maintaining two identical massive dictionaries
class RatingsProxy(dict):
    def __getitem__(self, key):
        return get_rating(key)
    def __contains__(self, key):
        canonical = get_canonical_name(key)
        return canonical in BASE_TEAM_RATINGS
    def get(self, key, default=None):
        try:
            return get_rating(key)
        except:
            return default

# Build all_possible_teams from BASE_TEAM_RATINGS
all_possible_teams = get_tournament_teams()

teams_ratings = RatingsProxy()


# -------------------------
# Win probability and match simulation (all use ratings from get_rating)
# -------------------------
def get_win_probability(rating_a, rating_b, divisor=552):
    """
    Expected win probability for team A (higher is better).
    Uses standard Elo-based probability formula.
    """
    dr = rating_a - rating_b
    return 1 / (1 + 10 ** (-dr / divisor))


def calculate_three_outcome_probs(rating_a, rating_b, draw_base=0.243):
    """
    Calculate explicit three-outcome probabilities (win/draw/loss) for a match.
    
    This uses the Dixon-Coles-style approach where:
    - P(A wins) = P(A wins outright) - P(draw adjustment)
    - P(B wins) = P(B wins outright) - P(draw adjustment)  
    - P(draw) = draw probability based on rating similarity
    
    The draw probability is calibrated based on historical World Cup data,
    where closer teams have higher draw probabilities.
    """
    # Base win probabilities from Elo difference
    p_a_win_raw = get_win_probability(rating_a, rating_b, divisor=552)
    p_b_win_raw = 1 - p_a_win_raw
    
    # Draw probability calibrated on rating difference (World Cup groups tend to have ~23-26% draws)
    # Using a sigmoid-like function that peaks at ~0.26 when ratings are equal
    rating_diff = abs(rating_a - rating_b)
    
    # Calibrated draw probability: peaks at 0.26 when ratings are equal,
    # decreases as rating difference increases (diminishing returns)
    draw_prob = 0.26 * np.exp(-rating_diff / 400) * (1 + np.tanh(rating_diff / 500) * 0.1)
    
    # Ensure draw probability is within reasonable bounds
    draw_prob = max(0.10, min(0.30, draw_prob))
    
    # Adjust win probabilities: draw probability is split proportionally from both sides
    # This preserves the Elo-based ordering while adding draw possibility
    draw_share = draw_prob / 2
    p_a_win = max(0.0, p_a_win_raw - draw_share)
    p_b_win = max(0.0, p_b_win_raw - draw_share)
    p_draw = draw_prob
    
    # Renormalize to ensure probabilities sum to 1
    total = p_a_win + p_b_win + p_draw
    if total > 0:
        p_a_win /= total
        p_b_win /= total
        p_draw /= total
    else:
        # Fallback for extreme rating differences
        p_a_win, p_b_win, p_draw = 0.45, 0.45, 0.10
    
    return p_a_win, p_b_win, p_draw


def sample_bivariate_poisson_goals(lambda_a, lambda_b, correlation=0.15):
    """
    Sample goals for two teams using a bivariate Poisson-like approach.
    
    This models goals with a shared 'excitement' component that creates
    realistic correlation between teams' scoring (e.g., high-scoring games
    tend to have both teams scoring more).
    
    Parameters:
    - lambda_a: Expected goals for team A
    - lambda_b: Expected goals for team B
    - correlation: Controls how much the teams' scoring is correlated (0-1)
    
    Returns:
    - goals_a, goals_b: Sampled goal counts
    """
    # Shared component (excitement factor) - models correlated scoring
    shared_lambda = (lambda_a + lambda_b) * correlation
    shared_goals = np.random.poisson(shared_lambda)
    
    # Team-specific components (attack vs defense)
    individual_a = np.random.poisson(lambda_a * (1 - correlation))
    individual_b = np.random.poisson(lambda_b * (1 - correlation))
    
    goals_a = shared_goals + individual_a
    goals_b = shared_goals + individual_b
    
    # Cap goals at reasonable maximum (World Cup rarely sees 8+ goals)
    max_goals = 10
    return min(goals_a, max_goals), min(goals_b, max_goals)


# =============================================================================
# POISSON CALCULATOR FUNCTIONS (from poisson_calculator.py)
# =============================================================================

def expected_goals_skellam_random_cap(team_a_elo, team_b_elo, baseline_goals=2.531666667,
                                       cap_min=200, cap_max=350):
    """
    Calculate expected goals with a random cap applied between cap_min and cap_max.
    
    This uses the Skellam distribution approach with Elo-based goal expectancy.
    """
    lambda_base = baseline_goals / 2
    D = team_b_elo - team_a_elo
    
    # Hard limit Elo difference to maximum 400 points to prevent unrealistic dominance
    D = max(-400, min(400, D))

    # Random cap between min and max
    elo_cap = np.random.uniform(cap_min, cap_max)

    # Adjust large differences
    if D > elo_cap:
        excess = D - elo_cap
        D = elo_cap - math.sqrt(excess)
    elif D < -elo_cap:
        excess = -D - elo_cap
        D = -elo_cap + math.sqrt(excess)

    lambda_A = lambda_base * 10 ** (-D / 400)
    lambda_B = lambda_base * 10 ** (D / 400)

    return lambda_A, lambda_B


def simulate_average_score(team_a_elo, team_b_elo, sims=1000):
    """
    Simulate matches with random caps and return average goals, goal difference,
    and most likely scoreline.
    """
    goals_A_list = []
    goals_B_list = []

    for _ in range(sims):
        lambda_A, lambda_B = expected_goals_skellam_random_cap(team_a_elo, team_b_elo)
        gA = np.random.poisson(lambda_A)
        gB = np.random.poisson(lambda_B)
        goals_A_list.append(gA)
        goals_B_list.append(gB)

    avg_A = np.mean(goals_A_list)
    avg_B = np.mean(goals_B_list)
    avg_diff = np.mean(np.array(goals_A_list) - np.array(goals_B_list))
    score_pairs = list(zip(goals_A_list, goals_B_list))
    most_common_score = max(set(score_pairs), key=score_pairs.count)

    return {
        "avg_goals_A": round(avg_A, 4),
        "avg_goals_B": round(avg_B, 4),
        "avg_goal_diff": round(avg_diff, 4),
        "most_common_score": most_common_score
    }


def simulate_match(team_a, team_b, group_key=None, allow_draw=True, use_poisson_calc=False):
    """
    Simulate one 90-minute match with realistic goal scoring.

    Uses explicit three-outcome modelling with bivariate Poisson goal
    distribution to naturally emerge:
    - Win/Draw/Loss outcomes
    - Goal difference
    - Goals scored
    - Tie-break realism

    Parameters:
    - use_poisson_calc: If True, uses the poisson_calculator.py approach with random Elo caps
                       If False (default), uses the original bivariate Poisson approach

    Returns: (points_a, points_b, goals_a, goals_b)
    """
    rating_a = get_rating(team_a)
    rating_b = get_rating(team_b)

    # Calculate three-outcome probabilities based on ratings
    p_a_win, p_b_win, p_draw = calculate_three_outcome_probs(rating_a, rating_b)

    # Decide outcome based on calibrated probabilities
    r = random.random()
    if r < p_a_win:
        outcome = 'a_win'
    elif r < p_a_win + p_draw:
        outcome = 'draw'
    else:
        outcome = 'b_win'

    if use_poisson_calc:
        # Use the poisson_calculator.py approach with random Elo caps
        # This applies a random cap between 200-350 to the Elo difference
        lambda_a, lambda_b = expected_goals_skellam_random_cap(
            rating_a, rating_b, baseline_goals=2.531666667
        )

        # Apply home advantage as goal expectancy adjustment
        lambda_a, lambda_b = apply_home_advantage(
            lambda_a, lambda_b, team_a, team_b, group_key
        )

        # Sample goals using simple Poisson, resampling until outcome matches
        while True:
            goals_a = min(np.random.poisson(lambda_a), 10)
            goals_b = min(np.random.poisson(lambda_b), 10)
            if (outcome == 'a_win' and goals_a > goals_b) or \
               (outcome == 'draw' and goals_a == goals_b) or \
               (outcome == 'b_win' and goals_b > goals_a):
                break
    else:
        # Original approach: Calculate expected goals (lambda) for each team
        # Base lambda reflects overall match excitement (World Cup avg ~2.5 goals)
        rating_diff = rating_a - rating_b
        # Hard limit Elo difference to maximum 400 points
        effective_diff = max(-400, min(400, rating_diff))

        base_lambda = 2.45 + 0.0004 * abs(effective_diff)
        base_lambda = max(1.8, min(3.8, base_lambda))

        # Cap effective ratings to prevent unrealistic dominance
        effective_rating_a = rating_a if rating_a <= rating_b + 400 else rating_b + 400
        effective_rating_b = rating_b if rating_b <= rating_a + 400 else rating_a + 400

        # Team's share of expected goals based on capped Elo ratings
        exp_rating_a = 10 ** (effective_rating_a / 400)
        exp_rating_b = 10 ** (effective_rating_b / 400)
        share_a = exp_rating_a / (exp_rating_a + exp_rating_b)

        lambda_a = base_lambda * share_a
        lambda_b = base_lambda * (1 - share_a)

        # Apply home advantage as goal expectancy adjustment
        lambda_a, lambda_b = apply_home_advantage(
            lambda_a, lambda_b, team_a, team_b, group_key
        )

        # Sample goals using bivariate Poisson, resampling until outcome matches
        while True:
            goals_a, goals_b = sample_bivariate_poisson_goals(
                lambda_a, lambda_b, correlation=0.12
            )
            if (outcome == 'a_win' and goals_a > goals_b) or \
               (outcome == 'draw' and goals_a == goals_b) or \
               (outcome == 'b_win' and goals_b > goals_a):
                break

    # Return points based on outcome
    if outcome == 'a_win':
        return 3, 0, goals_a, goals_b
    elif outcome == 'b_win':
        return 0, 3, goals_a, goals_b
    else:  # draw
        return 1, 1, goals_a, goals_b

def simulate_knockout_match(team_a, team_b, group_key=None, use_poisson_calc=False):
    """
    Knockout simulation with regulation time, extra time, and penalties if needed.
    
    Uses bivariate Poisson goal distribution for realistic scoring:
    - Regulation time: Full 90-minute expected goals
    - Extra time: ~30% of regulation expected goals
    - Penalties: Rating-based shootout probability
    
    Home advantage applies to knockout matches hosted in host nation venues.
    
    Parameters:
    - use_poisson_calc: If True, uses the poisson_calculator.py approach with random Elo caps
                       If False (default), uses the original bivariate Poisson approach
    
    Returns the winner team name.
    """
    rating_a = get_rating(team_a)
    rating_b = get_rating(team_b)

    if use_poisson_calc:
        # Use the poisson_calculator.py approach with random Elo caps
        lambda_a, lambda_b = expected_goals_skellam_random_cap(
            rating_a, rating_b, baseline_goals=2.531666667
        )
        
        # Apply home advantage for knockout matches
        lambda_a, lambda_b = apply_home_advantage(
            lambda_a, lambda_b, team_a, team_b, group_key
        )
        
        # Regulation time: Sample goals from simple Poisson
        goals_a_reg = min(np.random.poisson(lambda_a), 10)
        goals_b_reg = min(np.random.poisson(lambda_b), 10)
        
        # If not tied after regulation, return winner
        if goals_a_reg != goals_b_reg:
            return team_a if goals_a_reg > goals_b_reg else team_b

        # Extra time: ~30% of regulation expected goals
        lambda_a_et = lambda_a * 0.30
        lambda_b_et = lambda_b * 0.30
        
        # Apply home advantage to extra time as well
        lambda_a_et, lambda_b_et = apply_home_advantage(
            lambda_a_et, lambda_b_et, team_a, team_b, group_key
        )

        goals_a_et = min(np.random.poisson(lambda_a_et), 10)
        goals_b_et = min(np.random.poisson(lambda_b_et), 10)
    else:
        # Original approach
        rating_diff = rating_a - rating_b
        effective_diff = max(-400, min(400, rating_diff))
        rating_diff_abs = abs(effective_diff)

        # Calculate expected goals for regulation time
        base_lambda = 2.45 + 0.0004 * rating_diff_abs
        base_lambda = max(1.8, min(3.8, base_lambda))

        # Cap effective ratings to prevent unrealistic dominance
        effective_rating_a = rating_a if rating_a <= rating_b + 400 else rating_b + 400
        effective_rating_b = rating_b if rating_b <= rating_a + 400 else rating_a + 400

        exp_rating_a = 10 ** (effective_rating_a / 400)
        exp_rating_b = 10 ** (effective_rating_b / 400)
        share_a = exp_rating_a / (exp_rating_a + exp_rating_b)
        
        lambda_a = base_lambda * share_a
        lambda_b = base_lambda * (1 - share_a)
        
        # Apply home advantage for knockout matches (if hosted in host nation venues)
        lambda_a, lambda_b = apply_home_advantage(
            lambda_a, lambda_b, team_a, team_b, group_key
        )

        # Regulation time: Sample goals from bivariate Poisson
        goals_a_reg, goals_b_reg = sample_bivariate_poisson_goals(
            lambda_a, lambda_b, correlation=0.12
        )

        # If not tied after regulation, return winner
        if goals_a_reg != goals_b_reg:
            return team_a if goals_a_reg > goals_b_reg else team_b

        # Extra time: ~30% of regulation expected goals (reduced scoring in ET)
        lambda_et = 0.30 * base_lambda
        lambda_a_et = lambda_et * share_a
        lambda_b_et = lambda_et * (1 - share_a)

        goals_a_et, goals_b_et = sample_bivariate_poisson_goals(
            lambda_a_et, lambda_b_et, correlation=0.10  # Lower correlation in ET
        )

    total_goals_a = goals_a_reg + goals_a_et
    total_goals_b = goals_b_reg + goals_b_et

    # If not tied after extra time, return winner
    if total_goals_a != total_goals_b:
        return team_a if total_goals_a > total_goals_b else team_b

    # Penalties: Rating-based shootout probability
    # Higher-rated teams have slight advantage in pressure situations
    rating_diff_penalty = rating_a - rating_b
    p_penalty_win = 0.5 + (rating_diff_penalty / 400) * 0.04
    prob_a_penalty = max(0.42, min(0.58, p_penalty_win))

    # Penalty shootout: simulate until there's a winner
    # Each penalty pair is ~50/50 with rating adjustment
    while True:
        # Simulate one penalty each
        a_scores = random.random() < prob_a_penalty
        b_scores = random.random() < (1 - prob_a_penalty)
        
        # Check if one team has advantage (simplified shootout)
        # In reality, shootouts continue until there's a winner
        # This approximation gives correct ~50/50 outcome
        if a_scores and not b_scores:
            return team_a
        elif b_scores and not a_scores:
            return team_b
        # If both score or both miss, continue to next pair
        # Probability of infinite shootout is negligible

# small helper for bracket simulation where ratings are given as pairs or names
def rating_for_candidate(candidate):
    if isinstance(candidate, tuple):
        # (name, rating)
        return candidate[1]
    return teams_ratings.get(candidate, 1500.0)

def simulate_group(group, num_sims, group_key=None):
    results = {team: {'1st': 0, '2nd': 0, '3rd': 0, '4th': 0} for team in group['teams']}
    for _ in range(num_sims):
        group_stats = {team: {'points': 0, 'gf': 0, 'ga': 0} for team in group['teams']}
        for team_a, team_b in group['matches']:
            sa, sb, ga, gb = simulate_match(team_a, team_b, group_key=group_key, allow_draw=True)
            group_stats[team_a]['points'] += sa
            group_stats[team_b]['points'] += sb
            group_stats[team_a]['gf'] += ga
            group_stats[team_a]['ga'] += gb
            group_stats[team_b]['gf'] += gb
            group_stats[team_b]['ga'] += ga
        standings_list = []
        for team, stats in group_stats.items():
            gd = stats['gf'] - stats['ga']
            elo = get_rating(team)
            standings_list.append((team, stats['points'], gd, stats['gf'], elo))
        standings = sorted(standings_list, key=lambda x: (x[1], x[2], x[3], x[4]), reverse=True)
        results[standings[0][0]]['1st'] += 1
        results[standings[1][0]]['2nd'] += 1
        results[standings[2][0]]['3rd'] += 1
        results[standings[3][0]]['4th'] += 1
    return results

# =============================================================================
# QUALIFIER SIMULATION HELPERS — module-level so both modes share them
# =============================================================================
QUALIFIER_SIMS = 10000


def simulate_bracket_by_candidates(candidates, sims=QUALIFIER_SIMS):
    """
    Simulate a 4-team bracket qualification path.
    Returns {team_name: qualification_count} for probability-weighted sampling.
    """
    wins = {}
    patched = {}
    temp_names = []
    try:
        for i, c in enumerate(candidates):
            if isinstance(c, tuple):
                name = f"__temp_candidate_{i}__"
                teams_ratings[name] = float(c[1])
                patched[name] = c[0]
                temp_names.append(name)
                wins[name] = 0
            else:
                name = c
                wins[name] = 0
                temp_names.append(name)
        for _ in range(sims):
            semi1 = simulate_knockout_match(temp_names[0], temp_names[1])
            semi2 = simulate_knockout_match(temp_names[2], temp_names[3])
            final_winner = simulate_knockout_match(semi1, semi2)
            wins[final_winner] = wins.get(final_winner, 0) + 1
        mapped_wins = {}
        for k, v in wins.items():
            real_name = patched[k] if k in patched else k
            mapped_wins[real_name] = mapped_wins.get(real_name, 0) + v
        return mapped_wins
    finally:
        for name in patched.keys():
            teams_ratings.pop(name, None)


def simulate_round_robin_candidates(candidates, sims=QUALIFIER_SIMS):
    """
    Simulate a 3-team round robin qualification path.
    Returns {team_name: qualification_count} for probability weighting.
    """
    wins = {}
    patched = {}
    temp_names = []
    try:
        for i, c in enumerate(candidates):
            if isinstance(c, tuple):
                name = f"__temp_rr_{i}__"
                teams_ratings[name] = float(c[1])
                patched[name] = c[0]
                temp_names.append(name)
                wins[name] = 0
            else:
                name = c
                wins[name] = 0
                temp_names.append(name)
        for _ in range(sims):
            group_stats = {n: {'points': 0, 'gf': 0, 'ga': 0} for n in temp_names}
            rr_matches = [
                (temp_names[0], temp_names[1]),
                (temp_names[0], temp_names[2]),
                (temp_names[1], temp_names[2])
            ]
            for a, b in rr_matches:
                sa, sb, ga, gb = simulate_match(a, b, allow_draw=True)
                group_stats[a]['points'] += sa
                group_stats[b]['points'] += sb
                group_stats[a]['gf'] += ga
                group_stats[a]['ga'] += gb
                group_stats[b]['gf'] += gb
                group_stats[b]['ga'] += ga
            standings = []
            for team, stats in group_stats.items():
                gd = stats['gf'] - stats['ga']
                elo = get_rating(team)
                standings.append((team, stats['points'], gd, stats['gf'], elo))
            standings.sort(key=lambda x: (x[1], x[2], x[3], x[4]), reverse=True)
            winner = standings[0][0]
            wins[winner] += 1
        mapped_wins = {}
        for k, v in wins.items():
            real_name = patched[k] if k in patched else k
            mapped_wins[real_name] = mapped_wins.get(real_name, 0) + v
        return mapped_wins
    finally:
        for name in patched.keys():
            teams_ratings.pop(name, None)


def sample_qualifier_from_probs(prob_dict):
    """
    Weighted-random selection of a team from a {team: count} probability dict.
    """
    if not prob_dict:
        return None
    total = sum(prob_dict.values())
    if total == 0:
        return random.choice(list(prob_dict.keys()))
    r = random.uniform(0, total)
    cumulative = 0
    for team, count in prob_dict.items():
        cumulative += count
        if r <= cumulative:
            return team
    return list(prob_dict.keys())[-1]


def _build_qualifier_probabilities(groups_structure):
    """
    Pre-calculate qualification probability distributions for every placeholder
    found in groups_structure['possible_winners']. Returns a dict of
    {placeholder_name: {team_name: weight}}.
    """
    probs = {}
    for group in groups_structure.values():
        for placeholder, opts in group.get('possible_winners', {}).items():
            if len(opts) == 3 and all(isinstance(o, tuple) for o in opts):
                prob_dist = simulate_round_robin_candidates(opts)
            elif len(opts) == 4:
                prob_dist = simulate_bracket_by_candidates(opts)
            else:
                prob_dist = {}
                total_w = 0
                for o in opts:
                    name = o[0] if isinstance(o, tuple) else o
                    rating = float(o[1]) if isinstance(o, tuple) else BASE_TEAM_RATINGS.get(name, 1500.0)
                    w = np.exp((rating - 1500) / 200)
                    prob_dist[name] = w
                    total_w += w
                for name in prob_dist:
                    prob_dist[name] = prob_dist[name] / total_w * QUALIFIER_SIMS
            probs[placeholder] = prob_dist
    return probs


def sample_qualifier(placeholder):
    """Sample a concrete team for a placeholder based on pre-calculated probs."""
    return sample_qualifier_from_probs(qualifier_probabilities.get(placeholder, {}))


def calculate_group_closeness_rating(group_data, num_sims):
    """
    Calculate a Group Closeness Rating (0-10) measuring competitive balance.

    Compares each team's simulated probability of finishing in each group position
    against a perfectly even distribution (25% per position for 4-team groups,
    20% per position for 5-team groups). Maps the average total variation distance
    to a 0-10 scale where 10 = perfectly balanced, 0 = completely lopsided.

    Parameters:
    - group_data: dict of {team: {'1st_Place': n, '2nd_Place': n, ...}}
    - num_sims: total number of simulations run

    Returns:
    - closeness_rating: float 0.0-10.0
    """
    teams = [t for t, d in group_data.items()
             if d.get('1st_Place', 0) + d.get('2nd_Place', 0) +
             d.get('3rd_Place', 0) + d.get('4th_Place', 0) > 0]
    n_teams = len(teams)
    if n_teams < 2:
        return 0.0

    ideal_prob = 1.0 / n_teams
    total_deviation = 0.0
    count = 0

    for team in teams:
        data = group_data[team]
        for pos in ['1st_Place', '2nd_Place', '3rd_Place', '4th_Place']:
            actual = data.get(pos, 0) / num_sims if num_sims > 0 else 0
            total_deviation += abs(actual - ideal_prob)
            count += 1

    avg_deviation = total_deviation / count if count > 0 else 0
    # Normalize: max avg deviation is (n-1)/n, map 0 deviation -> 10, max deviation -> 0
    max_deviation = (n_teams - 1) / n_teams
    if max_deviation <= 0:
        return 10.0
    closeness_rating = 10.0 * (1.0 - avg_deviation / max_deviation)
    return round(max(0.0, min(10.0, closeness_rating)), 1)


def display_group_position_probabilities(group_position_results, num_sims):
    """
    Calculate and display the probability distribution for each team's final
    position within their World Cup group.

    For each group, shows every team's percentage chance of finishing 1st, 2nd,
    3rd, and 4th based on simulation results, formatted as a clear breakdown table.

    Parameters:
    - group_position_results: dict of {group_key: {team: {'1st_Place': n, '2nd_Place': n, ...}}}
    - num_sims: total number of simulations run
    """
    print("\n## Group Position Probability Distributions")
    print("---")
    for group_key in sorted(group_position_results.keys()):
        group_data = group_position_results[group_key]
        if not group_data:
            continue
        print(f"\n### Group {group_key}")
        position_percentages = {}
        for team, data in group_data.items():
            total_appearances = data.get('1st_Place', 0) + data.get('2nd_Place', 0) + \
                                data.get('3rd_Place', 0) + data.get('4th_Place', 0)
            if total_appearances == 0:
                continue
            position_percentages[team] = {
                '1st (%)': round((data.get('1st_Place', 0) / num_sims) * 100, 2),
                '2nd (%)': round((data.get('2nd_Place', 0) / num_sims) * 100, 2),
                '3rd Eliminated (%)': round(((data.get('3rd_Place', 0) - data.get('3rd_Place_Advance', 0)) / num_sims) * 100, 2),
                '3rd Advanced (%)': round((data.get('3rd_Place_Advance', 0) / num_sims) * 100, 2),
                '4th (%)': round((data.get('4th_Place', 0) / num_sims) * 100, 2),
            }
        if position_percentages:
            closeness = calculate_group_closeness_rating(group_data, num_sims)
            print(f"**Group Closeness Rating: {closeness}/10**")
            df = pd.DataFrame.from_dict(position_percentages, orient='index')
            df = df.sort_values(by='1st (%)', ascending=False)
            print(df.to_markdown())

            # Print group stats
            qualify_probs = {}
            for team, pcts in position_percentages.items():
                qualify_probs[team] = pcts['1st (%)'] + pcts['2nd (%)'] + pcts['3rd Advanced (%)']
            most_likely_1st = max(position_percentages, key=lambda t: position_percentages[t]['1st (%)'])
            most_likely_qualify = max(qualify_probs, key=lambda t: qualify_probs[t])
            least_likely_qualify = min(qualify_probs, key=lambda t: qualify_probs[t])
            print(f"\n**Most likely to win group:** {most_likely_1st} ({position_percentages[most_likely_1st]['1st (%)']}%)")
            print(f"**Most likely to qualify:** {most_likely_qualify} ({qualify_probs[most_likely_qualify]:.2f}%)")
            print(f"**Least likely to qualify:** {least_likely_qualify} ({qualify_probs[least_likely_qualify]:.2f}%)")

        # Expected points table
        if group_key in group_points_tracker:
            exp_data = {}
            for team, track in group_points_tracker[group_key].items():
                apps = track['appearances']
                if apps == 0:
                    continue
                exp_data[team] = {
                    'Exp Pts': round(track['total_points'] / apps, 2),
                    'Exp GF': round(track['total_gf'] / apps, 2),
                    'Exp GA': round(track['total_ga'] / apps, 2),
                    'Exp GD': round((track['total_gf'] - track['total_ga']) / apps, 2),
                }
            if exp_data:
                print(f"\n**Expected Points — Group {group_key}**")
                df_pts = pd.DataFrame.from_dict(exp_data, orient='index')
                df_pts = df_pts.sort_values(by='Exp Pts', ascending=False)
                print(df_pts.to_markdown())


# -------------------------
# Build original_groups_structure (preserves possible_winners for both modes)
# -------------------------
original_groups_structure = {}
for _gk, _grp in GROUPS.items():
    original_groups_structure[_gk] = {
        'teams': _grp['teams'].copy(),
        'matches': _grp['matches'].copy(),
    }
    if 'possible_winners' in _grp:
        original_groups_structure[_gk]['possible_winners'] = {
            k: list(v) for k, v in _grp['possible_winners'].items()
        }

# Store original possible_winners for scenario printing
original_possible = {g: grp.get('possible_winners', {}).copy() for g, grp in GROUPS.items()}

# Pre-calculate qualification probabilities (shared by both modes)
print("Pre-calculating qualifier probabilities...")
qualifier_probabilities = _build_qualifier_probabilities(original_groups_structure)

# Remove possible_winners from live GROUPS now that probabilities are stored
for _grp in GROUPS.values():
    _grp.pop('possible_winners', None)

# -------------------------
# MAIN SIMULATION
# -------------------------
from collections import defaultdict

def _empty_knockout_record():
    return {'Round_of_32': 0, 'Round_of_16': 0, 'Quarterfinals': 0,
            'Semifinals': 0, 'Final': 0, 'Winner': 0,
            'Third': 0, 'Runner_up': 0, 'Fourth': 0}

unique_finals = set()
# Use defaultdict so any dynamically-sampled team name is handled safely
knockout_results = defaultdict(_empty_knockout_record)
for team in all_possible_teams:
    knockout_results[team]  # pre-populate known teams

NUM_SIMULATIONS = 10000
total_sims = NUM_SIMULATIONS
print(f"Monte Carlo mode: {NUM_SIMULATIONS} simulations")
print("Qualification outcomes sampled probabilistically per simulation")

# Track group position results for probability distribution display
group_position_results = {}
for gk in original_groups_structure:
    group_position_results[gk] = defaultdict(lambda: {'1st_Place': 0, '2nd_Place': 0, '3rd_Place': 0, '3rd_Place_Advance': 0, '4th_Place': 0})

group_points_tracker = {}
for gk in original_groups_structure:
    group_points_tracker[gk] = defaultdict(lambda: {'total_points': 0, 'total_gf': 0, 'total_ga': 0, 'appearances': 0})

for _ in tqdm(range(NUM_SIMULATIONS)):
    # Sample concrete teams for each placeholder this simulation
    sampled_qualifiers = {}
    for placeholder in qualifier_probabilities.keys():
        sampled_qualifiers[placeholder] = sample_qualifier(placeholder)
    
    # Build resolved groups for this simulation
    current_GROUPS = {}
    for g, group in original_groups_structure.items():
        resolved_teams = []
        for t in group['teams']:
            resolved_teams.append(sampled_qualifiers.get(t, t))
        
        resolved_matches = []
        for a, b in group['matches']:
            resolved_a = sampled_qualifiers.get(a, a)
            resolved_b = sampled_qualifiers.get(b, b)
            resolved_matches.append((resolved_a, resolved_b))
        
        current_GROUPS[g] = {
            'teams': resolved_teams,
            'matches': resolved_matches
        }

    group_standings = {}
    for group_key, group in current_GROUPS.items():
        teams = group['teams']
        group_stats = {team: {'points': 0, 'gf': 0, 'ga': 0} for team in teams}
        for team_a, team_b in group['matches']:
            sa, sb, ga, gb = simulate_match(team_a, team_b, group_key=group_key, allow_draw=True)
            group_stats[team_a]['points'] += sa
            group_stats[team_b]['points'] += sb
            group_stats[team_a]['gf'] += ga
            group_stats[team_a]['ga'] += gb
            group_stats[team_b]['gf'] += gb
            group_stats[team_b]['ga'] += ga

        # Calculate goal difference and create standings with tiebreakers
        standings_list = []
        for team, stats in group_stats.items():
            gd = stats['gf'] - stats['ga']
            elo = get_rating(team)
            standings_list.append((team, stats['points'], gd, stats['gf'], elo))

        # Sort by: points (desc), goal diff (desc), goals scored (desc), Elo rating (desc)
        standings_list.sort(key=lambda x: (x[1], x[2], x[3], x[4]), reverse=True)
        group_standings[group_key] = standings_list

        # Track group position results
        group_position_results[group_key][standings_list[0][0]]['1st_Place'] += 1
        group_position_results[group_key][standings_list[1][0]]['2nd_Place'] += 1
        group_position_results[group_key][standings_list[2][0]]['3rd_Place'] += 1
        group_position_results[group_key][standings_list[3][0]]['4th_Place'] += 1

        # Track cumulative points for expected points table
        for team, stats in group_stats.items():
            group_points_tracker[group_key][team]['total_points'] += stats['points']
            group_points_tracker[group_key][team]['total_gf'] += stats['gf']
            group_points_tracker[group_key][team]['total_ga'] += stats['ga']
            group_points_tracker[group_key][team]['appearances'] += 1

    # Determine advancing teams: top 2 from each group + best 8 thirds
    winners = {group: group_standings[group][0][0] for group in 'ABCDEFGHIJKL'}
    runners_up = {group: group_standings[group][1][0] for group in 'ABCDEFGHIJKL'}
    third_places_with_group = [(group, group_standings[group][2][0], group_standings[group][2][1], group_standings[group][2][2], group_standings[group][2][3], group_standings[group][2][4]) for group in 'ABCDEFGHIJKL']
    # Sort by: points (desc), goal diff (desc), goals scored (desc), Elo rating (desc)
    third_places_with_group.sort(key=lambda x: (x[2], x[3], x[4], x[5]), reverse=True)
    selected_thirds = third_places_with_group[:8]
    advancing_thirds = [t[1] for t in selected_thirds]

    # Track which 3rd-place teams advanced (top 8)
    for t in selected_thirds:
        group_position_results[t[0]][t[1]]['3rd_Place_Advance'] += 1

    # Assign thirds to R32 matches (shuffle for randomness)
    third_teams = advancing_thirds.copy()
    random.shuffle(third_teams)
    third_assign = {
        74: third_teams[0],
        77: third_teams[1],
        79: third_teams[2],
        80: third_teams[3],
        81: third_teams[4],
        82: third_teams[5],
        85: third_teams[6],
        87: third_teams[7]
    }

    # Mark Round of 32 appearance
    advancing = list(winners.values()) + list(runners_up.values()) + advancing_thirds
    for team in advancing:
        knockout_results[team]['Round_of_32'] += 1

    # Simulate Round of 32
    r32_matches = {
        73: (runners_up['A'], runners_up['B']),
        74: (winners['E'], third_assign[74]),
        75: (winners['F'], runners_up['C']),
        76: (winners['C'], runners_up['F']),
        77: (winners['I'], third_assign[77]),
        78: (runners_up['E'], runners_up['I']),
        79: (winners['A'], third_assign[79]),
        80: (winners['L'], third_assign[80]),
        81: (winners['D'], third_assign[81]),
        82: (winners['G'], third_assign[82]),
        83: (runners_up['K'], runners_up['L']),
        84: (winners['H'], runners_up['J']),
        85: (winners['B'], third_assign[85]),
        86: (winners['J'], runners_up['H']),
        87: (winners['K'], third_assign[87]),
        88: (runners_up['D'], runners_up['G'])
    }
    r32_winners = {}
    for match, (t1, t2) in r32_matches.items():
        winner = simulate_knockout_match(t1, t2)
        r32_winners[match] = winner
        knockout_results[winner]['Round_of_16'] += 1

    # Round of 16
    r16_matches = {
        89: (r32_winners[74], r32_winners[77]),
        90: (r32_winners[73], r32_winners[75]),
        91: (r32_winners[76], r32_winners[78]),
        92: (r32_winners[79], r32_winners[80]),
        93: (r32_winners[83], r32_winners[84]),
        94: (r32_winners[81], r32_winners[82]),
        95: (r32_winners[86], r32_winners[88]),
        96: (r32_winners[85], r32_winners[87])
    }
    r16_winners = {}
    for match, (t1, t2) in r16_matches.items():
        winner = simulate_knockout_match(t1, t2)
        r16_winners[match] = winner
        knockout_results[winner]['Quarterfinals'] += 1

    # Quarterfinals
    qf_matches = {
        97: (r16_winners[89], r16_winners[90]),
        98: (r16_winners[93], r16_winners[94]),
        99: (r16_winners[91], r16_winners[92]),
        100: (r16_winners[95], r16_winners[96])
    }
    qf_winners = {}
    for match, (t1, t2) in qf_matches.items():
        winner = simulate_knockout_match(t1, t2)
        qf_winners[match] = winner
        knockout_results[winner]['Semifinals'] += 1

    # Semifinals
    sf_matches = {
        101: (qf_winners[97], qf_winners[98]),
        102: (qf_winners[99], qf_winners[100])
    }
    sf_winners = {}
    for match, (t1, t2) in sf_matches.items():
        winner = simulate_knockout_match(t1, t2)
        sf_winners[match] = winner
        knockout_results[winner]['Final'] += 1

    # Third place
    loser101 = qf_winners[97] if sf_winners[101] == qf_winners[98] else qf_winners[98]
    loser102 = qf_winners[99] if sf_winners[102] == qf_winners[100] else qf_winners[100]
    third = simulate_knockout_match(loser101, loser102)
    knockout_results[third]['Third'] += 1
    fourth_team = loser101 if third == loser102 else loser102
    knockout_results[fourth_team]['Fourth'] += 1

    # Final
    final_winner = simulate_knockout_match(sf_winners[101], sf_winners[102])
    knockout_results[final_winner]['Winner'] += 1
    runner_up = sf_winners[101] if final_winner == sf_winners[102] else sf_winners[102]
    knockout_results[runner_up]['Runner_up'] += 1
    unique_finals.add(frozenset([sf_winners[101], sf_winners[102]]))



# -------------------------
# OUTPUT
# -------------------------
display_group_position_probabilities(group_position_results, total_sims)

print("\n## Final Positions Matrix")
print("\n---")
positions = ['Round_of_32', 'Round_of_16', 'Quarterfinals', 'Semifinals', 'Final', 'Winner', 'Runner_up', 'Third', 'Fourth']
teams_reached = [team for team, data in knockout_results.items() if any(data[pos] > 0 for pos in positions)]
teams_reached.sort(key=lambda t: knockout_results[t]['Winner'], reverse=True)
data = {pos: [knockout_results[team][pos] for team in teams_reached] for pos in positions}
df = pd.DataFrame(data, index=teams_reached)
df = df / total_sims * 100
df = df.round(2).astype(str) + '%'
df.columns = ['Round of 32', 'Round of 16', 'Quarterfinals', 'Semifinals', 'Final', 'Winner', 'Runner-up', 'Third', 'Fourth']
print(df.to_markdown())

# Cool facts: teams that reached each round at least once
print("\n## Cool Facts")
print("---")
total_teams = len(all_possible_teams)
round_names = {
    'Round_of_32': 'Round of 32',
    'Round_of_16': 'Round of 16',
    'Quarterfinals': 'Quarterfinals',
    'Semifinals': 'Semifinals',
    'Final': 'Final',
    'Winner': 'Winner',
    'Runner_up': 'Runner-up',
    'Third': 'Third Place',
    'Fourth': 'Fourth Place'
}

for pos in positions:
    teams_count = sum(1 for team_data in knockout_results.values() if team_data[pos] > 0)
    percentage = (teams_count / number_of_qualified_teams) * 100
    print(f"Teams that reached {round_names[pos]} at least once: {teams_count} ({percentage:.1f}%)")

print(f"\nNumber of different final matchups: {len(unique_finals)}")


# Generate HTML output
def create_html():
    num_sims_html = total_sims
    group_source = group_position_results

    mode_label = 'All Possibilities'
    html_content = (
        '<!DOCTYPE html>\n<html lang="en">\n<head>\n'
        '<meta charset="UTF-8">\n'
        '<meta name="viewport" content="width=device-width, initial-scale=1.0">\n'
        '<title>World Cup 2026 Simulation Results</title>\n'
        '<style>\n'
        '  *, *::before, *::after {{ color: #39ff14 !important; border-color: #39ff14 !important; background-color: transparent; }}\n'
        '  body {{ font-family: "Segoe UI", Arial, sans-serif; margin: 0; padding: 20px; background-color: #000000; }}\n'
        '  .container {{ max-width: 1200px; margin: 0 auto; }}\n'
        '  h1 {{ text-shadow: 0 0 15px #39ff14, 0 0 30px #39ff14; text-align: center; font-size: 2.2em; margin-bottom: 5px; }}\n'
        '  h2 {{ text-shadow: 0 0 10px #39ff14, 0 0 20px #39ff14; border-bottom: 2px solid #39ff14 !important; padding-bottom: 8px; margin-top: 40px; }}\n'
        '  h3 {{ text-shadow: 0 0 5px #39ff14; margin-bottom: 5px; }}\n'
        '  p, li {{ text-shadow: 0 0 5px #39ff14; }}\n'
        '  .subtitle {{ text-align: center; font-size: 0.95em; margin-bottom: 30px; }}\n'
        '  table {{ border-collapse: collapse; width: 100%; margin-bottom: 15px; border: 2px solid #39ff14 !important; box-shadow: 0 0 15px rgba(57,255,20,0.3); font-size: 0.9em; background-color: #000000; }}\n'
        '  th, td {{ border: 1px solid #39ff14 !important; padding: 8px 10px; text-align: left; }}\n'
        '  th {{ background-color: #0a0a0a !important; text-shadow: 0 0 8px #39ff14; font-weight: bold; }}\n'
        '  td {{ background-color: #000000 !important; text-shadow: none; }}\n'
        '  tbody tr:nth-child(even) td {{ background-color: #080808 !important; }}\n'
        '  tbody tr:nth-child(odd) td {{ background-color: #000000 !important; }}\n'
        '  tbody tr:hover td {{ background-color: #0a1a0a !important; }}\n'
        '  .group-section {{ margin-bottom: 40px; padding: 15px 20px; background-color: #050505 !important; border: 1px solid #39ff14 !important; border-radius: 8px; box-shadow: 0 0 10px rgba(57,255,20,0.15); }}\n'
        '  .closeness-badge {{ display: inline-block; padding: 4px 14px; border-radius: 12px; font-weight: bold; font-size: 1.1em; margin: 8px 0 12px 0; text-shadow: 0 0 8px #39ff14; background-color: rgba(57,255,20,0.15) !important; border: 1px solid #39ff14 !important; }}\n'
        '  .closeness-label {{ font-size: 0.75em; font-weight: normal; opacity: 0.8; }}\n'
        '  .teams-list {{ font-size: 0.9em; margin-bottom: 10px; }}\n'
        '  .knockout-section {{ margin-top: 40px; padding: 15px 20px; background-color: #050505 !important; border: 1px solid #39ff14 !important; border-radius: 8px; }}\n'
        '  .cool-facts {{ margin-top: 40px; padding: 15px 20px; background-color: #050505 !important; border: 1px solid #39ff14 !important; border-radius: 8px; }}\n'
        '  .cool-facts li {{ margin-bottom: 6px; }}\n'
        '  .matchup-count {{ font-size: 1.1em; margin-top: 10px; text-shadow: 0 0 5px #39ff14; }}\n'
        '  footer {{ text-align: center; margin-top: 50px; padding-top: 15px; border-top: 1px solid #39ff14 !important; font-size: 0.85em; }}\n'
        '  a {{ text-decoration: underline; }}\n'
        '</style>\n'
        '</head>\n<body>\n'
        '<div class="container">\n'
        '  <h1>World Cup 2026 Simulation Results</h1>\n'
        '  <p class="subtitle">Monte Carlo Simulation &mdash; '
        + f'{num_sims_html:,}'
        + ' Iterations &mdash; Mode: '
        + mode_label
        + '</p>\n'
    )

    # ---- GROUP SECTIONS ----
    positions_out = ['Round_of_32', 'Round_of_16', 'Quarterfinals', 'Semifinals',
                     'Final', 'Winner', 'Runner_up', 'Third', 'Fourth']
    round_names = {
        'Round_of_32': 'Round of 32', 'Round_of_16': 'Round of 16',
        'Quarterfinals': 'Quarterfinals', 'Semifinals': 'Semifinals',
        'Final': 'Final', 'Winner': 'Winner', 'Runner_up': 'Runner-up',
        'Third': 'Third Place', 'Fourth': 'Fourth Place'
    }

    for group_key in sorted(GROUPS.keys()):
        # Resolve the group data — look up from the appropriate source
        if group_key not in group_source or not group_source[group_key]:
            continue
        group_data = group_source[group_key]

        # Build the teams string
        current_teams = [t for t in GROUPS[group_key]['teams'] if t not in qualifier_probabilities]
        placeholder_info = []
        for t in GROUPS[group_key]['teams']:
            if t in qualifier_probabilities:
                candidates = list(qualifier_probabilities[t].keys())
                placeholder_info.append(f"{t} \u2192 {candidates}")
        teams_str = ', '.join(current_teams)
        if placeholder_info:
            teams_str += ' (' + ', '.join(placeholder_info) + ')'

        # Calculate closeness rating
        closeness = calculate_group_closeness_rating(group_data, num_sims_html)
        if closeness >= 7.0:
            badge_class = 'closeness-high'
            label = 'Highly Competitive'
        elif closeness >= 4.0:
            badge_class = 'closeness-medium'
            label = 'Moderately Balanced'
        else:
            badge_class = 'closeness-low'
            label = 'Lopsided'

        html_content += f"<div class='group-section'>"
        html_content += f"<h2>Group {group_key}</h2>"
        html_content += f"<p class='teams-list'><strong>Teams:</strong> {teams_str}</p>"
        html_content += f"<div class='closeness-badge {badge_class}'>Group Closeness Rating: {closeness}/10 <span class='closeness-label'>&mdash; {label}</span></div>"

        # Build the position percentages table
        position_percentages = {}
        for team, data in group_data.items():
            total_apps = (data.get('1st_Place', 0) + data.get('2nd_Place', 0) +
                         data.get('3rd_Place', 0) + data.get('4th_Place', 0))
            if total_apps == 0:
                continue
            position_percentages[team] = {
                    '1st (%)': round((data.get('1st_Place', 0) / num_sims_html) * 100, 2),
                    '2nd (%)': round((data.get('2nd_Place', 0) / num_sims_html) * 100, 2),
                    '3rd (%)': round((data.get('3rd_Place', 0) / num_sims_html) * 100, 2),
                    '4th (%)': round((data.get('4th_Place', 0) / num_sims_html) * 100, 2),
                }

        if position_percentages:
            df_final = pd.DataFrame.from_dict(position_percentages, orient='index')
            df_final = df_final.sort_values(by='1st (%)', ascending=False)
            html_content += "<h3>Predicted Finishing Positions</h3>"
            html_content += df_final.to_html(float_format='%.2f')

        # Expected points table in HTML
        if group_key in group_points_tracker:
            exp_data = {}
            for team, track in group_points_tracker[group_key].items():
                apps = track['appearances']
                if apps == 0:
                    continue
                exp_data[team] = {
                    'Exp Pts': round(track['total_points'] / apps, 2),
                    'Exp GF': round(track['total_gf'] / apps, 2),
                    'Exp GA': round(track['total_ga'] / apps, 2),
                    'Exp GD': round((track['total_gf'] - track['total_ga']) / apps, 2),
                }
            if exp_data:
                html_content += "<h3>Expected Points</h3>"
                df_pts = pd.DataFrame.from_dict(exp_data, orient='index')
                df_pts = df_pts.sort_values(by='Exp Pts', ascending=False)
                html_content += df_pts.to_html(float_format='%.2f')

        html_content += "</div>"  # close group-section

    # ---- KNOCKOUT STAGE MATRIX ----
    html_content += "<div class='knockout-section'>"
    html_content += "<h2>Knockout Stage Probabilities</h2>"

    teams_reached = [team for team, data in knockout_results.items()
                     if any(data[pos] > 0 for pos in positions_out)]
    teams_reached.sort(key=lambda t: knockout_results[t]['Winner'], reverse=True)

    if teams_reached:
        # Full matrix table
        ko_data = {pos: [knockout_results[team][pos] for team in teams_reached]
                   for pos in positions_out}
        df_ko = pd.DataFrame(ko_data, index=teams_reached)
        df_ko = df_ko / num_sims_html * 100
        df_ko = df_ko.round(1)
        df_ko.columns = ['Round of 32', 'Round of 16', 'Quarterfinals', 'Semifinals',
                         'Final', 'Winner', 'Runner-up', '3rd Place', '4th Place']

        html_content += "<table><thead><tr>"
        html_content += "<th>Team</th>"
        for col in df_ko.columns:
            html_content += f"<th>{col}</th>"
        html_content += "</tr></thead><tbody>"
        for team in df_ko.index:
            html_content += "<tr>"
            html_content += f"<td><strong>{team}</strong></td>"
            for col in df_ko.columns:
                val = df_ko.loc[team, col]
                if val == 0.0:
                    html_content += "<td>0.0%</td>"
                else:
                    html_content += f"<td>{val}%</td>"
            html_content += "</tr>"
        html_content += "</tbody></table>"

        # Individual stage breakdowns with borders
        stage_groups = [
            ('Group Stage Advancement', ['Round of 32']),
            ('Knockout Rounds', ['Round of 16', 'Quarterfinals', 'Semifinals']),
            ('Finals', ['Final', 'Winner', 'Runner-up', '3rd Place', '4th Place']),
        ]
        stage_col_map = {
            'Round_of_32': 'Round of 32', 'Round_of_16': 'Round of 16',
            'Quarterfinals': 'Quarterfinals', 'Semifinals': 'Semifinals',
            'Final': 'Final', 'Winner': 'Winner', 'Runner_up': 'Runner-up',
            'Third': '3rd Place', 'Fourth': '4th Place',
        }

        for group_title, stage_labels in stage_groups:
            html_content += f"<div style='border:1px solid #39ff14 !important; border-radius:8px; padding:12px 16px; margin:20px 0; background-color:#050505 !important;'>"
            html_content += f"<h3 style='margin-top:0;'>{group_title}</h3>"
            html_content += "<table style='margin-bottom:0;'><thead><tr><th>Team</th>"
            for label in stage_labels:
                html_content += f"<th>{label}</th>"
            html_content += "</tr></thead><tbody>"

            # Find teams active in any stage of this group
            stage_keys = [k for k, v in stage_col_map.items() if v in stage_labels]
            active_teams = [t for t in teams_reached
                           if any(knockout_results[t][k] > 0 for k in stage_keys)]
            active_teams.sort(key=lambda t: max(knockout_results[t][k] for k in stage_keys), reverse=True)

            for team in active_teams:
                html_content += f"<tr><td><strong>{team}</strong></td>"
                for label in stage_labels:
                    raw_key = [k for k, v in stage_col_map.items() if v == label][0]
                    val = round(knockout_results[team][raw_key] / num_sims_html * 100, 1)
                    if val == 0.0:
                        html_content += "<td>0.0%</td>"
                    else:
                        html_content += f"<td>{val}%</td>"
                html_content += "</tr>"
            html_content += "</tbody></table></div>"

    html_content += "</div>"  # close knockout-section

    # ---- COOL FACTS ----
    html_content += "<div class='cool-facts'>"
    html_content += "<h2>Cool Facts</h2><ul>"

    for pos in positions_out:
        teams_count = sum(1 for team_data in knockout_results.values() if team_data[pos] > 0)
        percentage = (teams_count / number_of_qualified_teams) * 100
        html_content += f"<li>Teams that reached {round_names[pos]} at least once: <strong>{teams_count}</strong> ({percentage:.1f}%)</li>"

    html_content += f"<li class='matchup-count'>Number of different final matchups: <strong>{len(unique_finals)}</strong></li>"

    html_content += "</ul></div>"

    html_content += """
    <footer>World Cup 2026 &mdash; Monte Carlo Simulation Engine</footer>
</div>
</body>
</html>
"""

    try:
        with open('worldcup_simulation_results.html', 'w', encoding='utf-8') as f:
            f.write(html_content)
    except Exception as e:
        print(f"Error generating HTML file: {e}")
        return False
    return True

# Generate PDF output
def create_pdf():
    doc = SimpleDocTemplate('worldcup_simulation_results.pdf', pagesize=letter)
    styles = getSampleStyleSheet()

    # Create custom styles
    title_style = ParagraphStyle('Title', parent=styles['Heading1'], fontSize=18, spaceAfter=30)
    heading_style = ParagraphStyle('Heading', parent=styles['Heading2'], fontSize=14, spaceAfter=20)
    normal_style = styles['Normal']

    story = []

    # Title
    story.append(Paragraph("World Cup 2026 Simulation Results", title_style))
    story.append(Spacer(1, 12))

    # Final Positions Matrix
    story.append(Paragraph("Final Positions Matrix", heading_style))

    positions = ['Round_of_32', 'Round_of_16', 'Quarterfinals', 'Semifinals', 'Final', 'Winner', 'Runner_up', 'Third', 'Fourth']
    teams_reached = [team for team, data in knockout_results.items() if any(data[pos] > 0 for pos in positions)]
    teams_reached.sort(key=lambda t: knockout_results[t]['Winner'], reverse=True)
    data = {pos: [knockout_results[team][pos] for team in teams_reached] for pos in positions}
    df = pd.DataFrame(data, index=teams_reached)
    df = df / total_sims * 100
    df = df.round(1)

    # Convert to formatted strings with %
    for col in df.columns:
        df[col] = df[col].astype(str) + '%'

    df.columns = ['Round of 32', 'Round of 16', 'Quarterfinals', 'Semifinals', 'Final', 'Winner', 'Runner-up', 'Third', 'Fourth']

    # Convert to table data
    table_data = [list(df.columns)]
    for team in df.index:
        table_data.append([team] + list(df.loc[team]))

    # Set column widths for final positions matrix
    # Team names need more space, percentages can be narrower
    col_widths = [90] + [35] * 9  # Team name wider, percentages much narrower
    table = Table(table_data, colWidths=col_widths)
    table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.grey),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
        ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, 0), 6),  # Very small font for headers
        ('FONTSIZE', (0, 1), (-1, -1), 5),  # Very small for content
        ('BOTTOMPADDING', (0, 0), (-1, 0), 4),
        ('TOPPADDING', (0, 0), (-1, 0), 4),
        ('LEFTPADDING', (0, 0), (-1, -1), 2),
        ('RIGHTPADDING', (0, 0), (-1, -1), 2),
        ('BACKGROUND', (0, 1), (-1, -1), colors.beige),
        ('GRID', (0, 0), (-1, -1), 0.3, colors.black)
    ]))
    story.append(table)
    story.append(Spacer(1, 20))

    # Cool Facts
    story.append(Paragraph("Cool Facts", heading_style))

    round_names = {
        'Round_of_32': 'Round of 32',
        'Round_of_16': 'Round of 16',
        'Quarterfinals': 'Quarterfinals',
        'Semifinals': 'Semifinals',
        'Final': 'Final',
        'Winner': 'Winner',
        'Runner_up': 'Runner-up',
        'Third': 'Third Place',
        'Fourth': 'Fourth Place'
    }

    for pos in positions:
        teams_count = sum(1 for team_data in knockout_results.values() if team_data[pos] > 0)
        percentage = (teams_count / number_of_qualified_teams) * 100
        fact_text = f"Teams that reached {round_names[pos]} at least once: {teams_count} ({percentage:.1f}%)"
        story.append(Paragraph(f"• {fact_text}", normal_style))
        story.append(Spacer(1, 6))

    doc.build(story)


def calculate_confidence_interval(successes, total_sims, confidence=0.95):
    """
    Calculate confidence interval for a proportion using Wilson score interval.
    
    Parameters:
    - successes: Number of successful outcomes
    - total_sims: Total number of simulations
    - confidence: Confidence level (default 0.95 for 95% CI)
    
    Returns: (lower_bound, upper_bound) as percentages
    """
    if total_sims == 0:
        return 0.0, 0.0
    
    p = successes / total_sims
    n = total_sims
    
    # Wilson score interval
    z = 1.96  # 95% confidence level
    denominator = 1 + z**2 / n
    center = (p + z**2 / (2 * n)) / denominator
    margin = z * np.sqrt((p * (1 - p) + z**2 / (4 * n)) / n) / denominator
    
    lower = max(0.0, (center - margin) * 100)
    upper = min(100.0, (center + margin) * 100)
    
    return lower, upper


def generate_uncertainty_report(knockout_results, num_sims):
    """
    Generate uncertainty metrics for simulation results.
    
    Shows:
    - 95% confidence intervals for key probabilities
    - Coefficient of variation for high-impact outcomes
    - Sensitivity analysis notes
    """
    report = []
    report.append("## Uncertainty Analysis")
    report.append("---")
    report.append(f"""
**Simulation Statistics:**
- Total simulations: {num_sims}
- Confidence level: 95%
- Method: Monte Carlo sampling with per-simulation qualifier selection

**Interpretation Notes:**
- Confidence intervals show the range where the true probability likely falls
- Narrower intervals = more confident predictions
- Wide intervals indicate high uncertainty (close races, many possibilities)
- Results near 50% have inherently high uncertainty

**Key Uncertainties:**
1. **Home advantage sensitivity**: Actual impact may vary ±20% from model
2. **Qualification path**: Placeholder teams sampled probabilistically
3. **Goal variance**: Poisson model captures average, but individual matches vary
""")
    
    # Calculate confidence intervals for top teams
    report.append("### 95% Confidence Intervals (Winner Probability)")
    report.append("")
    report.append("| Team | Mean % | 95% CI |")
    report.append("|------|---------|----------|")
    
    # Sort by winner probability
    sorted_teams = []
    for team, data in knockout_results.items():
        wins = data.get('Winner', 0)
        sorted_teams.append((team, wins))
    
    sorted_teams.sort(key=lambda x: x[1], reverse=True)
    sorted_teams = sorted_teams[:16]  # Top 16 teams
    
    for team, wins in sorted_teams:
        mean_pct = (wins / num_sims) * 100
        if mean_pct > 0:
            lower, upper = calculate_confidence_interval(wins, num_sims)
            report.append(f"| {team} | {mean_pct:.1f}% | [{lower:.1f}%, {upper:.1f}%] |")
    
    return "\n".join(report)

html_success = create_html()
if html_success:
    print("\nHTML file 'worldcup_simulation_results.html' generated.")
else:
    print("\nFailed to generate HTML file.")

try:
    create_pdf()
    print("PDF file 'worldcup_simulation_results.pdf' generated.")
except PermissionError as e:
    print(f"Error generating PDF: {e}")
    print("The PDF file may be open in another program. Please close it and try again.")
except Exception as e:
    print(f"Error generating PDF: {e}")

# Generate and print uncertainty report
try:
    uncertainty_report = generate_uncertainty_report(knockout_results, total_sims)
    print("\n" + uncertainty_report)
except Exception as e:
    print(f"\nNote: Could not generate uncertainty report: {e}")

print("\nSimulation complete.")