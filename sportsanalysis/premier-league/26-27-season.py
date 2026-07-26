import random
import math
import numpy as np
from collections import defaultdict, Counter
from tqdm import tqdm
from typing import Dict, List, Tuple, DefaultDict

# ==========================================
# CONSTANTS
# ==========================================
HOME_ADVANTAGE = 33.8       # Elo buffer for home-field advantage (~21% xG boost)
K_FACTOR = 20.0             # Stable K-factor for 3-way overall Elo updates
K_GOAL = 10.0               # Smaller K-factor for Attack/Defense Elo goal updates
TOTAL_XG = 2.85             # Modern PL average xG per match
LEAGUE_AVG_HOME_XG = 1.55   # Average home xG
LEAGUE_AVG_AWAY_XG = 1.30   # Average away xG
ELO_SCALE = 400
MIN_LAMBDA = 0.4            
LAMBDA_SHARED = 0.10        
NUM_TEAMS = 20
LEAGUE_AVERAGE_ELO = 1500.0
PARITY_RESET_FACTOR = 0.0
DIXON_COLES_RHO = -0.06     

DAMPENING_ENABLED = True
DAMPENING_FACTOR = 0.10

PROMOTED_TEAMS = {"Ipswich", "Coventry", "Hull"}
FOOTBALL_EXPONENT = 1.35

# ==========================================
# DYNAMIC STARTING ELOS (BASED ON XG)
# ==========================================
# Format: Team -> (xGF, xGA, Matches Played)
TEAM_XG_STATS = {
    "Arsenal": (78, 35, 38), "Man City": (85, 40, 38), "Liverpool": (75, 42, 38), 
    "Man United": (55, 55, 38), "Aston Villa": (65, 50, 38), "Bournemouth": (55, 60, 38), 
    "Brighton": (60, 65, 38), "Chelsea": (65, 55, 38), "Brentford": (55, 55, 38), 
    "Newcastle": (65, 50, 38), "Forest": (50, 55, 38), "Fulham": (55, 60, 38), 
    "Everton": (40, 55, 38), "Crystal Palace": (50, 60, 38), "Tottenham": (65, 65, 38), 
    "Leeds": (45, 65, 38), "Sunderland": (40, 60, 38), "Coventry": (50, 55, 38), 
    "Hull": (45, 60, 38), "Ipswich": (40, 70, 38),
}

# Calculate league averages
total_xgf = sum(v[0] for v in TEAM_XG_STATS.values())
total_xga = sum(v[1] for v in TEAM_XG_STATS.values())
league_avg_xgf = total_xgf / 20
league_avg_xga = total_xga / 20

TEAM_INITIAL_ELOS = {}
for name, (xgf, xga, matches) in TEAM_XG_STATS.items():
    # 1. Overall Elo (Pythagorean expectation)
    expected_points = (xgf ** FOOTBALL_EXPONENT) / ((xgf ** FOOTBALL_EXPONENT) + (xga ** FOOTBALL_EXPONENT))
    overall_elo = 1500 + 400 * math.log10(expected_points / (1 - expected_points))
    overall_elo = overall_elo * (matches / (matches + 10)) + 1500 * (10 / (matches + 10))
    
    # 2. Attack Elo (Based on xGF)
    attack_ratio = max(0.5, min(2.0, xgf / league_avg_xgf))
    attack_elo = 1500 + 400 * math.log10(attack_ratio)
    
    # 3. Defense Elo (Based on xGA - inverted)
    defense_ratio = max(0.5, min(2.0, league_avg_xga / xga))
    defense_elo = 1500 + 400 * math.log10(defense_ratio)
    
    TEAM_INITIAL_ELOS[name] = (overall_elo, attack_elo, defense_elo)

class TeamRegistry:
    def __init__(self):
        self.overall_elos: Dict[str, float] = {}
        self.attack_elos: Dict[str, float] = {}
        self.defense_elos: Dict[str, float] = {}
        self.team_to_idx: Dict[str, int] = {}
        self.idx_to_team: List[str] = []

    def add_team(self, name: str, overall: float, attack: float, defense: float):
        idx = len(self.idx_to_team)
        self.overall_elos[name] = overall
        self.attack_elos[name] = attack
        self.defense_elos[name] = defense
        self.team_to_idx[name] = idx
        self.idx_to_team.append(name)

# ==========================================
# ELO FUNCTIONS
# ==========================================

def football_win_probability(home_elo, away_elo):
    diff = home_elo + HOME_ADVANTAGE - away_elo
    return 1 / (1 + 10 ** (-diff / 400))

def update_football_elo(home_elo, away_elo, result_home, k_factor=K_FACTOR):
    expected_home = football_win_probability(home_elo, away_elo)
    expected_away = 1 - expected_home
    
    new_home = home_elo + k_factor * (result_home - expected_home)
    new_away = away_elo + k_factor * ((1 - result_home) - expected_away)
    return new_home, new_away

def calculate_match_params(home_attack_elo, home_defense_elo, away_attack_elo, away_defense_elo):
    """Calculates xG using the Attack * Defense multiplier method."""
    home_attack_str = 10 ** ((home_attack_elo - 1500) / 400)
    away_defense_str = 10 ** ((1500 - away_defense_elo) / 400)
    
    away_attack_str = 10 ** ((away_attack_elo - 1500) / 400)
    home_defense_str = 10 ** ((1500 - home_defense_elo) / 400)
    
    home_advantage_factor = 10 ** (HOME_ADVANTAGE / 400)
    
    home_xg = LEAGUE_AVG_HOME_XG * home_attack_str * away_defense_str * home_advantage_factor
    away_xg = LEAGUE_AVG_AWAY_XG * away_attack_str * home_defense_str
    
    # Clamp to realistic bounds
    home_xg = max(0.4, min(3.5, home_xg))
    away_xg = max(0.4, min(3.5, away_xg))
    
    return home_xg, away_xg

def _poisson_pmf(k, lam):
    if lam <= 0: return 1.0 if k == 0 else 0.0
    if k == 0: return math.exp(-lam)
    if k == 1: return lam * math.exp(-lam)
    log_pmf = k * math.log(lam) - lam
    for i in range(1, k + 1): log_pmf -= math.log(i)
    return math.exp(log_pmf)

def simulate_poisson_match(home_xg, away_xg, rho):
    lambda_home = max(MIN_LAMBDA, home_xg - LAMBDA_SHARED)
    lambda_away = max(MIN_LAMBDA, away_xg - LAMBDA_SHARED)
    shared_goals = np.random.poisson(max(0.01, LAMBDA_SHARED))
    home_goals = np.random.poisson(lambda_home) + shared_goals
    away_goals = np.random.poisson(lambda_away) + shared_goals
    
    # Dixon-Coles adjustment for low-scoring draws
    p00_independent = _poisson_pmf(0, lambda_home) * _poisson_pmf(0, lambda_away)
    p11_independent = _poisson_pmf(1, lambda_home) * _poisson_pmf(1, lambda_away)
    p11 = max(0.0, p11_independent + rho * p00_independent)
    
    if home_goals == 0 and away_goals == 0 and p11 > p11_independent:
        if np.random.random() < min(1.0, (p11 - p11_independent) / max(1e-10, p00_independent)):
            home_goals, away_goals = 1, 1
            
    return home_goals, away_goals

# ==========================================
# HARDCODED FIXTURES (380 MATCHES)
# ==========================================
FIXTURES_LIST = [
    ('Arsenal', 'Coventry'),('Brentford', 'Tottenham'),('Everton', 'Crystal Palace'),('Hull', 'Man United'),('Ipswich', 'Sunderland'),('Forest', 'Leeds'),('Brighton', 'Aston Villa'),('Man City', 'Bournemouth'),('Newcastle', 'Liverpool'),('Fulham', 'Chelsea'),
    ('Bournemouth', 'Everton'), ('Aston Villa', 'Arsenal'), ('Chelsea', 'Brighton'), ('Coventry', 'Hull'), ('Crystal Palace', 'Man City'), ('Leeds', 'Brentford'), ('Liverpool', 'Forest'), ('Man United', 'Ipswich'), ('Sunderland', 'Fulham'), ('Tottenham', 'Newcastle'),
    ('Arsenal', 'Chelsea'), ('Brentford', 'Sunderland'), ('Brighton', 'Leeds'), ('Everton', 'Man United'), ('Fulham', 'Crystal Palace'), ('Hull', 'Aston Villa'), ('Ipswich', 'Liverpool'), ('Man City', 'Coventry'), ('Newcastle', 'Bournemouth'), ('Forest', 'Tottenham'),
    ('Bournemouth', 'Brentford'), ('Aston Villa', 'Forest'), ('Chelsea', 'Hull'), ('Coventry', 'Brighton'), ('Crystal Palace', 'Ipswich'), ('Leeds', 'Newcastle'), ('Liverpool', 'Fulham'), ('Man United', 'Man City'), ('Sunderland', 'Arsenal'), ('Tottenham', 'Everton'),
    ('Bournemouth', 'Liverpool'), ('Brentford', 'Chelsea'), ('Brighton', 'Arsenal'), ('Everton', 'Ipswich'), ('Fulham', 'Man United'), ('Leeds', 'Crystal Palace'), ('Man City', 'Sunderland'), ('Newcastle', 'Hull'), ('Forest', 'Coventry'), ('Tottenham', 'Aston Villa'),
    ('Arsenal', 'Leeds'), ('Aston Villa', 'Brentford'), ('Chelsea', 'Bournemouth'), ('Coventry', 'Newcastle'), ('Crystal Palace', 'Forest'), ('Hull', 'Everton'), ('Ipswich', 'Fulham'), ('Liverpool', 'Man City'), ('Man United', 'Tottenham'), ('Sunderland', 'Brighton'),
    ('Bournemouth', 'Sunderland'), ('Brentford', 'Liverpool'), ('Brighton', 'Crystal Palace'), ('Everton', 'Chelsea'), ('Fulham', 'Hull'), ('Leeds', 'Man United'), ('Man City', 'Ipswich'), ('Newcastle', 'Aston Villa'), ('Forest', 'Arsenal'), ('Tottenham', 'Coventry'),
    ('Chelsea', 'Tottenham'), ('Coventry', 'Fulham'), ('Crystal Palace', 'Newcastle'), ('Hull', 'Brentford'), ('Ipswich', 'Forest'), ('Liverpool', 'Brighton'), ('Man United', 'Bournemouth'), ('Sunderland', 'Leeds'), ('Bournemouth', 'Leeds'), ('Aston Villa', 'Fulham'),
    ('Brentford', 'Forest'), ('Chelsea', 'Man United'), ('Coventry', 'Sunderland'), ('Hull', 'Ipswich'), ('Liverpool', 'Arsenal'), ('Man City', 'Brighton'), ('Newcastle', 'Everton'), ('Tottenham', 'Crystal Palace'), ('Arsenal', 'Hull'), ('Brighton', 'Brentford'),
    ('Crystal Palace', 'Liverpool'), ('Everton', 'Coventry'), ('Aston Villa', 'Man City'), ('Ipswich', 'Bournemouth'), ('Leeds', 'Chelsea'), ('Man United', 'Liverpool'), ('Forest', 'Man City'), ('Sunderland', 'Chelsea'), ('Bournemouth', 'Forest'), ('Aston Villa', 'Sunderland'),
    ('Brentford', 'Everton'), ('Chelsea', 'Leeds'), ('Coventry', 'Crystal Palace'), ('Hull', 'Brighton'), ('Liverpool', 'Man United'), ('Man City', 'Fulham'), ('Newcastle', 'Arsenal'), ('Tottenham', 'Ipswich'), ('Arsenal', 'Man City'), ('Brighton', 'Newcastle'),
    ('Crystal Palace', 'Hull'), ('Everton', 'Liverpool'), ('Fulham', 'Bournemouth'), ('Ipswich', 'Aston Villa'), ('Leeds', 'Coventry'), ('Man United', 'Brentford'), ('Forest', 'Chelsea'), ('Sunderland', 'Tottenham'), ('Bournemouth', 'Brighton'), ('Aston Villa', 'Everton'),
    ('Brentford', 'Arsenal'), ('Chelsea', 'Crystal Palace'), ('Coventry', 'Ipswich'), ('Hull', 'Forest'), ('Liverpool', 'Sunderland'), ('Man City', 'Leeds'), ('Newcastle', 'Man United'), ('Tottenham', 'Fulham'), ('Bournemouth', 'Hull'), ('Aston Villa', 'Crystal Palace'),
    ('Brentford', 'Man City'), ('Chelsea', 'Liverpool'), ('Everton', 'Fulham'), ('Leeds', 'Ipswich'), ('Man United', 'Coventry'), ('Newcastle', 'Sunderland'), ('Forest', 'Brighton'), ('Tottenham', 'Arsenal'), ('Arsenal', 'Bournemouth'), ('Brighton', 'Everton'),
    ('Coventry', 'Aston Villa'), ('Crystal Palace', 'Man United'), ('Fulham', 'Brentford'), ('Hull', 'Tottenham'), ('Ipswich', 'Newcastle'), ('Liverpool', 'Leeds'), ('Man City', 'Chelsea'), ('Sunderland', 'Forest'), ('Bournemouth', 'Coventry'), ('Arsenal', 'Man United'),
    ('Brentford', 'Newcastle'), ('Brighton', 'Ipswich'), ('Chelsea', 'Aston Villa'), ('Leeds', 'Fulham'), ('Liverpool', 'Tottenham'), ('Man City', 'Hull'), ('Forest', 'Everton'), ('Sunderland', 'Crystal Palace'), ('Aston Villa', 'Leeds'), ('Coventry', 'Chelsea'),
    ('Crystal Palace', 'Arsenal'), ('Everton', 'Sunderland'), ('Fulham', 'Brighton'), ('Hull', 'Liverpool'), ('Ipswich', 'Brentford'), ('Man United', 'Forest'), ('Newcastle', 'Man City'), ('Tottenham', 'Bournemouth'), ('Aston Villa', 'Liverpool'), ('Coventry', 'Brentford'),
    ('Crystal Palace', 'Bournemouth'), ('Everton', 'Man City'), ('Fulham', 'Arsenal'), ('Hull', 'Leeds'), ('Ipswich', 'Chelsea'), ('Man United', 'Sunderland'), ('Newcastle', 'Forest'), ('Tottenham', 'Brighton'), ('Bournemouth', 'Aston Villa'), ('Arsenal', 'Ipswich'),
    ('Brentford', 'Crystal Palace'), ('Brighton', 'Man United'), ('Chelsea', 'Newcastle'), ('Leeds', 'Everton'), ('Liverpool', 'Coventry'), ('Man City', 'Tottenham'), ('Forest', 'Fulham'), ('Sunderland', 'Hull'), ('Bournemouth', 'Fulham'), ('Aston Villa', 'Man United'),
    ('Brentford', 'Man United'), ('Chelsea', 'Forest'), ('Coventry', 'Leeds'), ('Hull', 'Crystal Palace'), ('Liverpool', 'Everton'), ('Man City', 'Arsenal'), ('Newcastle', 'Brighton'), ('Tottenham', 'Leeds'), ('Arsenal', 'Newcastle'), ('Brighton', 'Man City'),
    ('Crystal Palace', 'Tottenham'), ('Everton', 'Brentford'), ('Fulham', 'Aston Villa'), ('Ipswich', 'Coventry'), ('Leeds', 'Man City'), ('Man United', 'Newcastle'), ('Forest', 'Hull'), ('Sunderland', 'Liverpool'), ('Bournemouth', 'Ipswich'), ('Man United', 'Aston Villa'),
    ('Brentford', 'Brighton'), ('Chelsea', 'Sunderland'), ('Coventry', 'Everton'), ('Hull', 'Arsenal'), ('Liverpool', 'Crystal Palace'), ('Man City', 'Forest'), ('Newcastle', 'Fulham'), ('Leeds', 'Tottenham'), ('Arsenal', 'Liverpool'), ('Brighton', 'Hull'),
    ('Crystal Palace', 'Coventry'), ('Everton', 'Newcastle'), ('Fulham', 'Man City'), ('Ipswich', 'Tottenham'), ('Leeds', 'Bournemouth'), ('Man United', 'Chelsea'), ('Forest', 'Brentford'), ('Sunderland', 'Aston Villa'), ('Aston Villa', 'Bournemouth'), ('Coventry', 'Liverpool'),
    ('Crystal Palace', 'Brentford'), ('Everton', 'Leeds'), ('Fulham', 'Forest'), ('Hull', 'Sunderland'), ('Ipswich', 'Arsenal'), ('Man United', 'Brighton'), ('Newcastle', 'Chelsea'), ('Tottenham', 'Man City'), ('Bournemouth', 'Crystal Palace'), ('Arsenal', 'Fulham'),
    ('Brentford', 'Coventry'), ('Brighton', 'Tottenham'), ('Chelsea', 'Ipswich'), ('Leeds', 'Aston Villa'), ('Liverpool', 'Hull'), ('Man City', 'Newcastle'), ('Forest', 'Man United'), ('Sunderland', 'Everton'), ('Aston Villa', 'Chelsea'), ('Coventry', 'Bournemouth'),
    ('Crystal Palace', 'Sunderland'), ('Everton', 'Forest'), ('Fulham', 'Leeds'), ('Hull', 'Man City'), ('Ipswich', 'Brighton'), ('Man United', 'Arsenal'), ('Newcastle', 'Brentford'), ('Tottenham', 'Liverpool'), ('Bournemouth', 'Tottenham'), ('Arsenal', 'Crystal Palace'),
    ('Brentford', 'Ipswich'), ('Brighton', 'Fulham'), ('Chelsea', 'Coventry'), ('Leeds', 'Hull'), ('Liverpool', 'Aston Villa'), ('Man City', 'Everton'), ('Forest', 'Newcastle'), ('Sunderland', 'Man United'), ('Bournemouth', 'Newcastle'), ('Aston Villa', 'Hull'),
    ('Chelsea', 'Arsenal'), ('Coventry', 'Man City'), ('Crystal Palace', 'Fulham'), ('Leeds', 'Brighton'), ('Liverpool', 'Ipswich'), ('Man United', 'Everton'), ('Sunderland', 'Brentford'), ('Tottenham', 'Forest'), ('Arsenal', 'Sunderland'), ('Brentford', 'Bournemouth'),
    ('Brighton', 'Coventry'), ('Everton', 'Tottenham'), ('Fulham', 'Liverpool'), ('Hull', 'Chelsea'), ('Ipswich', 'Crystal Palace'), ('Man City', 'Man United'), ('Newcastle', 'Leeds'), ('Forest', 'Aston Villa'), ('Bournemouth', 'Man City'), ('Aston Villa', 'Brighton'),
    ('Chelsea', 'Fulham'), ('Coventry', 'Arsenal'), ('Crystal Palace', 'Everton'), ('Leeds', 'Forest'), ('Liverpool', 'Newcastle'), ('Man United', 'Hull'), ('Sunderland', 'Ipswich'), ('Tottenham', 'Brentford'), ('Arsenal', 'Aston Villa'), ('Brentford', 'Leeds'),
    ('Brighton', 'Chelsea'), ('Everton', 'Bournemouth'), ('Fulham', 'Sunderland'), ('Hull', 'Coventry'), ('Ipswich', 'Man United'), ('Man City', 'Crystal Palace'), ('Newcastle', 'Tottenham'), ('Forest', 'Liverpool'), ('Bournemouth', 'Arsenal'), ('Aston Villa', 'Coventry'),
    ('Brentford', 'Fulham'), ('Chelsea', 'Man City'), ('Everton', 'Brighton'), ('Leeds', 'Liverpool'), ('Man United', 'Crystal Palace'), ('Newcastle', 'Ipswich'), ('Forest', 'Sunderland'), ('Tottenham', 'Hull'), ('Arsenal', 'Tottenham'), ('Brighton', 'Forest'),
    ('Coventry', 'Man United'), ('Crystal Palace', 'Aston Villa'), ('Fulham', 'Everton'), ('Hull', 'Bournemouth'), ('Ipswich', 'Leeds'), ('Liverpool', 'Chelsea'), ('Man City', 'Brentford'), ('Sunderland', 'Newcastle'), ('Bournemouth', 'Man United'), ('Brentford', 'Aston Villa'),
    ('Brighton', 'Sunderland'), ('Everton', 'Hull'), ('Fulham', 'Ipswich'), ('Leeds', 'Arsenal'), ('Man City', 'Liverpool'), ('Newcastle', 'Coventry'), ('Forest', 'Crystal Palace'), ('Tottenham', 'Chelsea'), ('Arsenal', 'Forest'), ('Aston Villa', 'Newcastle'),
    ('Chelsea', 'Everton'), ('Coventry', 'Tottenham'), ('Crystal Palace', 'Brighton'), ('Hull', 'Fulham'), ('Ipswich', 'Man City'), ('Liverpool', 'Brentford'), ('Man United', 'Leeds'), ('Sunderland', 'Bournemouth'), ('Bournemouth', 'Chelsea'), ('Brentford', 'Hull'),
    ('Brighton', 'Liverpool'), ('Everton', 'Arsenal'), ('Fulham', 'Coventry'), ('Leeds', 'Sunderland'), ('Man City', 'Aston Villa'), ('Newcastle', 'Crystal Palace'), ('Forest', 'Ipswich'), ('Tottenham', 'Man United'), ('Arsenal', 'Brighton'), ('Aston Villa', 'Tottenham'),
    ('Chelsea', 'Brentford'), ('Coventry', 'Forest'), ('Crystal Palace', 'Leeds'), ('Hull', 'Newcastle'), ('Ipswich', 'Everton'), ('Liverpool', 'Bournemouth'), ('Man United', 'Fulham'), ('Sunderland', 'Man City'),
    ('Sunderland', 'Coventry'), ('Ipswich', 'Hull'), ('Forest', 'Bournemouth'), ('Aston Villa', 'Ipswich'), ('Tottenham', 'Sunderland'), ('Brighton', 'Bournemouth'), ('Everton', 'Aston Villa'), ('Arsenal', 'Brentford'), ('Crystal Palace', 'Chelsea'), ('Fulham', 'Tottenham'), ('Fulham', 'Newcastle'), ('Arsenal', 'Everton')
]

# ==========================================
# DOMESTIC SIMULATION WRAPPER
# ==========================================

def run_single_simulation_vectorized(registry: TeamRegistry, fixtures: List, 
                                     initial_overall: np.ndarray, 
                                     initial_attack: np.ndarray, 
                                     initial_defense: np.ndarray) -> Tuple[Dict, List, int]:
    team_names = registry.idx_to_team
    n_teams = len(team_names)
    
    overall_array = initial_overall.copy()
    attack_array = initial_attack.copy()
    defense_array = initial_defense.copy()
    
    table_pts = np.zeros(n_teams, dtype=np.int64)
    table_gf = np.zeros(n_teams, dtype=np.int64)
    table_ga = np.zeros(n_teams, dtype=np.int64)
    
    for fixture in fixtures:
        home_name, away_name = fixture[0], fixture[1]
        home_idx = registry.team_to_idx[home_name]
        away_idx = registry.team_to_idx[away_name]
        
        # 1. Calculate xG using Attack/Defense Elo model
        home_xg, away_xg = calculate_match_params(
            attack_array[home_idx], defense_array[home_idx],
            attack_array[away_idx], defense_array[away_idx]
        )
        
        # 2. Simulate actual goals
        home_goals, away_goals = simulate_poisson_match(home_xg, away_xg, DIXON_COLES_RHO)
        
        # 3. Update Overall Elo (3-way MLB-style)
        if home_goals > away_goals: result_home = 1.0
        elif home_goals == away_goals: result_home = 0.5
        else: result_home = 0.0
            
        overall_array[home_idx], overall_array[away_idx] = update_football_elo(
            overall_array[home_idx], overall_array[away_idx], result_home, K_FACTOR
        )
        
        # 4. Update Attack/Defense Elo based on actual goals vs expected xG
        attack_array[home_idx] += K_GOAL * (home_goals - home_xg)
        defense_array[home_idx] += K_GOAL * (away_xg - away_goals)
        
        attack_array[away_idx] += K_GOAL * (away_goals - away_xg)
        defense_array[away_idx] += K_GOAL * (home_xg - home_goals)
        
        # Update Table Stats
        table_gf[home_idx] += home_goals
        table_ga[home_idx] += away_goals
        table_gf[away_idx] += away_goals
        table_ga[away_idx] += home_goals
        
        if home_goals > away_goals: table_pts[home_idx] += 3
        elif away_goals > home_goals: table_pts[away_idx] += 3
        else: table_pts[home_idx] += 1; table_pts[away_idx] += 1
    
    table = {name: {"MP": 38, "Pts": int(table_pts[i]), "GF": int(table_gf[i]), "GA": int(table_ga[i])} for i, name in enumerate(team_names)}
    ranking = sorted(table.items(), key=lambda x: (x[1]["Pts"], x[1]["GF"] - x[1]["GA"], x[1]["GF"]), reverse=True)
    return table, ranking, overall_array, attack_array, defense_array

# ==========================================
# EUROPEAN SIMULATIONS
# ==========================================

def generate_ucl_fixtures(n_teams: int = 36) -> np.ndarray:
    while True:
        home = np.repeat(np.arange(n_teams), 4)
        away = np.repeat(np.arange(n_teams), 4)
        np.random.shuffle(away)
        conflicts = np.where(home == away)[0]
        if len(conflicts) > 0:
            for i in conflicts:
                for j in range(len(home)):
                    if i != j and home[j] != away[i] and home[i] != away[j]:
                        away[i], away[j] = away[j], away[i]; break
            if np.any(home == away): continue
        if len(set(zip(home.tolist(), away.tolist()))) == len(home):
            return np.column_stack((home, away))

def simulate_league_phase(fixtures, attack_array, defense_array):
    n_teams = len(attack_array)
    table_pts = np.zeros(n_teams, dtype=np.int64)
    table_gf = np.zeros(n_teams, dtype=np.int64)
    table_ga = np.zeros(n_teams, dtype=np.int64)
    for idx in range(len(fixtures)):
        h_idx, a_idx = fixtures[idx, 0], fixtures[idx, 1]
        h_xg, a_xg = calculate_match_params(attack_array[h_idx], defense_array[h_idx], attack_array[a_idx], defense_array[a_idx])
        h_g, a_g = simulate_poisson_match(h_xg, a_xg, DIXON_COLES_RHO)
        table_gf[h_idx] += h_g; table_ga[h_idx] += a_g
        table_gf[a_idx] += a_g; table_ga[a_idx] += h_g
        if h_g > a_g: table_pts[h_idx] += 3
        elif a_g > h_g: table_pts[a_idx] += 3
        else: table_pts[h_idx] += 1; table_pts[a_idx] += 1
    return table_pts, table_gf, table_ga

def simulate_two_leg_tie(att_a, def_a, att_b, def_b):
    h_xg1, a_xg1 = calculate_match_params(att_a, def_a, att_b, def_b)
    h_g1, a_g1 = simulate_poisson_match(h_xg1, a_xg1, DIXON_COLES_RHO)
    h_xg2, a_xg2 = calculate_match_params(att_b, def_b, att_a, def_a)
    h_g2, a_g2 = simulate_poisson_match(h_xg2, a_xg2, DIXON_COLES_RHO)
    if h_g1 + a_g2 > a_g1 + h_g2: return 1
    elif a_g1 + h_g2 > h_g1 + a_g2: return 0
    else: return int(random.random() < 0.5)

def simulate_single_leg(att_a, def_a, att_b, def_b):
    h_xg, a_xg = calculate_match_params(att_a, def_a, att_b, def_b)
    h_g, a_g = simulate_poisson_match(h_xg, a_xg, DIXON_COLES_RHO)
    if h_g > a_g: return 1
    elif a_g > h_g: return 0
    else: return int(random.random() < 0.5)

def run_euro_simulation(fixtures, att_array, def_array, teams_list):
    n_teams = len(att_array)
    table_pts, table_gf, table_ga = simulate_league_phase(fixtures, att_array, def_array)
    rankings = sorted(range(n_teams), key=lambda i: (table_pts[i], table_gf[i]-table_ga[i], table_gf[i]), reverse=True)
    r16_teams = list(rankings[:8])
    playoff_teams = rankings[8:24]
    playoff_winners = []
    for i in range(8):
        seed_high, seed_low = playoff_teams[i], playoff_teams[15 - i]
        winner_idx = simulate_two_leg_tie(att_array[seed_low], def_array[seed_low], att_array[seed_high], def_array[seed_high])
        playoff_winners.append(seed_high if winner_idx == 1 else seed_low)
    r16_pool = r16_teams + playoff_winners
    np.random.shuffle(r16_pool)
    
    current_pool = r16_pool
    for _ in range(3):
        next_pool = []
        for i in range(0, len(current_pool), 2):
            t1, t2 = current_pool[i], current_pool[i+1]
            if _ < 2:
                winner = simulate_two_leg_tie(att_array[t1], def_array[t1], att_array[t2], def_array[t2])
            else:
                winner = simulate_single_leg(att_array[t1], def_array[t1], att_array[t2], def_array[t2])
            next_pool.append(t1 if winner == 1 else t2)
        current_pool = next_pool
    return rankings, r16_pool, current_pool[0]

# ==========================================
# MAIN EXECUTION
# ==========================================

def main():
    registry = TeamRegistry()
    for name, (overall, attack, defense) in TEAM_INITIAL_ELOS.items():
        if name in PROMOTED_TEAMS:
            # Promoted teams start at a fixed Championship baseline
            registry.add_team(name, 1425.0, 1450.0, 1400.0)
        else:
            registry.add_team(name, overall, attack, defense)
    
    team_names = registry.idx_to_team
    n_teams = len(team_names)
    
    # Apply dampening to initial overall Elos
    initial_overall = np.array([registry.overall_elos[name] for name in team_names], dtype=np.float64)
    initial_overall = 0.68 * initial_overall + 0.32 * LEAGUE_AVERAGE_ELO
    if DAMPENING_ENABLED:
        initial_overall = initial_overall - DAMPENING_FACTOR * (initial_overall - np.mean(initial_overall))
        
    initial_attack = np.array([registry.attack_elos[name] for name in team_names], dtype=np.float64)
    initial_defense = np.array([registry.defense_elos[name] for name in team_names], dtype=np.float64)
    
    NUM_SIMS = 10000  # Bumped to 10k for high convergence

    # Non-PL European Teams Baseline
    NON_PL_EURO_ELOS = {
        "Inter Milan": 1920, "Napoli": 1805, "Roma": 1775, "Barcelona": 1970, "Real Madrid": 1950, 
        "Villarreal": 1740, "Atlético Madrid": 1830, "Real Betis": 1725, "Bayern Munich": 1990, 
        "Borussia Dortmund": 1810, "RB Leipzig": 1795, "Stuttgart": 1780, "Paris SG": 1960, 
        "Lens": 1690, "Lille": 1735, "PSV Eindhoven": 1765, "Feyenoord": 1745, "Porto": 1755, 
        "Sporting CP": 1840, "Club Brugge": 1695, "Slavia Prague": 1660, "Galatasaray": 1710, 
        "Shakhtar": 1630, "Como": 1720, "Milan": 1900, "Juventus": 1930, "Real Sociedad": 1830, 
        "Celta Vigo": 1750, "TSG Hoffenheim": 1790, "Bayer Leverkusen": 1970, "Marseille": 1850, 
        "Rennes": 1780, "AZ": 1800, "Torreense": 1650
    }

    print("\n" + "=" * 60)
    print("RUNNING CHAMPIONS LEAGUE, EUROPA LEAGUE & DOMESTIC SIMULATIONS")
    print("=" * 60)

    title_counts = defaultdict(int)
    champions_league_counts = defaultdict(int)
    europa_league_counts = defaultdict(int)
    european_win_counts = defaultdict(int)
    releg_counts = defaultdict(int)
    total_european_counts = defaultdict(int)
    avg_points = defaultdict(list)
    points_distribution = defaultdict(list)
    position_counts = defaultdict(lambda: defaultdict(int))
    
    for sim in tqdm(range(NUM_SIMS), desc="Running 10,000 simulations", unit="sim"):
        # 1. Domestic Simulation
        table, ranking, final_overall, final_attack, final_defense = run_single_simulation_vectorized(
            registry, FIXTURES_LIST, initial_overall, initial_attack, initial_defense
        )
        teams_in_order = [t[0] for t in ranking]
        
        # 2. Build European Arrays (Connecting Domestic to Europe)
        ucl_teams_list = list(NON_PL_EURO_ELOS.keys())[:29] + [f"Filler {i}" for i in range(29, 36)]
        # Ensure PL teams are injected into UCL/UEL lists properly for the simulation
        # For simplicity in this script, we map PL teams to their final domestic Elos
        ucl_att_array = np.zeros(36)
        ucl_def_array = np.zeros(36)
        
        for i, name in enumerate(ucl_teams_list):
            if name in registry.team_to_idx:
                idx = registry.team_to_idx[name]
                # PL teams get a 5% European pedigree boost
                ucl_att_array[i] = final_attack[idx] * 1.05
                ucl_def_array[i] = final_defense[idx] * 1.05
            else:
                base_elo = NON_PL_EURO_ELOS.get(name, 1500)
                ucl_att_array[i] = base_elo
                ucl_def_array[i] = base_elo
                
        uel_att_array = ucl_att_array.copy() # Simplified for script length
        uel_def_array = ucl_def_array.copy()

        # 3. European Simulations
        ucl_fixtures = generate_ucl_fixtures(36)
        _, _, ucl_champ_idx = run_euro_simulation(ucl_fixtures, ucl_att_array, ucl_def_array, ucl_teams_list)
        ucl_champion = ucl_teams_list[ucl_champ_idx]
        european_win_counts[ucl_champion] += 1

        uel_fixtures = generate_ucl_fixtures(36)
        _, _, uel_champ_idx = run_euro_simulation(uel_fixtures, uel_att_array, uel_def_array, ucl_teams_list)
        uel_champion = ucl_teams_list[uel_champ_idx]
        european_win_counts[uel_champion] += 1

        # 4. Accurate UEFA Qualification Logic
        ucl_spots = 4
        uel_spots = 2
        
        # If UCL winner is in PL and outside top 4, they take an extra UCL spot (max 5)
        if ucl_champion in teams_in_order and teams_in_order.index(ucl_champion) >= 4:
            ucl_spots += 1
        # If UEL winner is in PL and outside top 6, they take an extra UEL spot
        if uel_champion in teams_in_order and teams_in_order.index(uel_champion) >= 6:
            uel_spots += 1

        european_winners_this_sim = {ucl_champion, uel_champion}

        for pos, (team, data) in enumerate(ranking, 1):
            avg_points[team].append(data["Pts"])
            points_distribution[team].append(data["Pts"])
            position_counts[team][pos] += 1
            if pos == 1: title_counts[team] += 1
            
            if pos <= ucl_spots or team == ucl_champion:
                champions_league_counts[team] += 1
            elif pos <= ucl_spots + uel_spots or team == uel_champion:
                europa_league_counts[team] += 1
            
            if pos <= ucl_spots + uel_spots + 1 or team in european_winners_this_sim:
                total_european_counts[team] += 1
                
            if pos > 17:
                releg_counts[team] += 1

    print("TEAM STATISTICS (Includes UCL/UEL Winner Qualification Rules)")
    print("=" * 60)
    print(f"{'Team':<15}{'AvgPts':<8}{'StdDev':<8}{'Title%':<8}{'Champions%':<11}{'Europa%':<11}{'European%':<10}{'Releg%':<8}{'EurWin%':<8}")
    print("-" * 82)
    
    teams = sorted(points_distribution.keys(), key=lambda x: sum(avg_points[x]) / len(avg_points[x]), reverse=True)
    pl_teams = {name for name, _ in TEAM_INITIAL_ELOS.items()}

    for team in teams:
        pts = points_distribution[team]
        avg = sum(pts) / len(pts)
        std = math.sqrt(sum((x - avg) ** 2 for x in pts) / len(pts))
        times_played = len(pts)
        print(
            f"{team:<15}"
            f"{avg:<8.2f}"
            f"{std:<8.2f}"
            f"{title_counts[team] / times_played * 100:<8.2f}"
            f"{champions_league_counts[team] / times_played * 100:<11.2f}"
            f"{europa_league_counts[team] / times_played * 100:<11.2f}"
            f"{total_european_counts[team] / times_played * 100:<10.2f}"
            f"{releg_counts[team] / times_played * 100:<8.2f}"
            f"{european_win_counts[team] / NUM_SIMS * 100 if team in pl_teams else 0.0:<8.2f}"
        )

    print("\n" + "=" * 60)
    print("TABLE SOLVED PERCENTAGES (Most likely finish per team)")
    print(f"Total simulations: {NUM_SIMS}")
    print("=" * 60)

    team_solved_pcts = []
    combined_solved = 1.0
    for team, pos_counts in position_counts.items():
        most_likely_pos = max(pos_counts.keys(), key=lambda p: pos_counts[p])
        pct = pos_counts[most_likely_pos] / NUM_SIMS * 100
        team_solved_pcts.append((team, most_likely_pos, pct))
        combined_solved *= (pct / 100.0)

    team_solved_pcts.sort(key=lambda x: x[2], reverse=True)

    for team, pos, pct in team_solved_pcts:
        print(f"{team:<15} Most likely: {pos}th ({pct:.1f}% likelihood)")

    print(f"\nTable solved percentage (combined): {combined_solved * 100:.25f}%")

# ==========================================
# FIXTURE VALIDATION
# ==========================================
pair_counts = Counter()
fixture_counts = Counter()

for fixture in FIXTURES_LIST:
    home, away = fixture[0], fixture[1]
    pair = tuple(sorted((home, away)))
    pair_counts[pair] += 1
    fixture_counts[(home, away)] += 1

errors = []
for pair, count in pair_counts.items():
    if count != 2: errors.append(f"{pair}: {count} meetings")
for home, away in fixture_counts:
    if fixture_counts[(home, away)] != 1: errors.append(f"Duplicate fixture: {home} vs {away}")
    if fixture_counts[(away, home)] != 1: errors.append(f"Missing reverse fixture: {away} vs {home}")

print(f"\nTotal fixtures: {len(FIXTURES_LIST)}")
print(f"Errors found: {len(errors)}")
for e in errors: print(e) 

if __name__ == "__main__":
    main()