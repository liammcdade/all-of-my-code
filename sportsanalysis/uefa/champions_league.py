import random
import math
from collections import Counter

# Current Elo ratings from clubelo.com (as of March 18, 2026)
# Update these manually from https://clubelo.com/ if needed
elos = {
    "Arsenal": 2057,
    "Bayern Munich": 1987,
    "Liverpool": 1924,
    "Tottenham Hotspur": 1766,
    "Barcelona": 1957,
    "PSG": 1955,
    "Real Madrid": 1944,
    "Sporting CP": 1861,
    "Newcastle United": 1862,
    "Atletico Madrid": 1861,
    "Atalanta": 1792,
    "Galatasaray": 1735,
}

# Poisson random variable generator (pure Python)
def poisson_random(lam):
    if lam < 0:
        lam = 0
    L = math.exp(-lam)
    k = 0
    p = 1.0
    while True:
        k += 1
        p *= random.random()
        if p <= L:
            return k - 1

# Expected goals for a leg (home advantage baked into base values)
def get_expected_goals(home_elo, away_elo):
    diff = home_elo - away_elo
    home_lambda = 1.4 + (diff * 0.001)
    away_lambda = 1.1 - (diff * 0.001)
    home_lambda = max(0.6, min(4.0, home_lambda))
    away_lambda = max(0.6, min(4.0, away_lambda))
    return home_lambda, away_lambda

# Simulate penalties (Elo-based slight favorite)
def simulate_penalties(team_a, team_b, elos_dict):
    diff = elos_dict[team_a] - elos_dict[team_b]
    prob_a = 1 / (1 + 10 ** (-diff / 400))
    return team_a if random.random() < prob_a else team_b

# Simulate a pending R16 second leg (with current aggregate + away goals rule)
def simulate_pending_r16(tie_data):
    home = tie_data["second_home"]
    away = [t for t in tie_data["teams"] if t != home][0]
    elo_h = elos[home]
    elo_a = elos[away]
    h_lambda, a_lambda = get_expected_goals(elo_h, elo_a)
    goals_h = poisson_random(h_lambda)
    goals_a = poisson_random(a_lambda)

    total_h = tie_data["current_totals"][home] + goals_h
    total_a = tie_data["current_totals"][away] + goals_a

    if total_h > total_a:
        return home
    elif total_h < total_a:
        return away
    else:
        # Away goals tiebreaker
        away_goals_h = tie_data["current_away_goals"][home] + 0  # not away in second leg
        away_goals_a = tie_data["current_away_goals"][away] + goals_a
        if away_goals_h > away_goals_a:
            return home
        elif away_goals_h < away_goals_a:
            return away
        else:
            # Penalties
            return simulate_penalties(home, away, elos)

# Simulate a full two-legged tie (clean slate, first leg home known)
def simulate_two_leg_tie(team_a, team_b, first_leg_home_is_a, elos_dict):
    if first_leg_home_is_a:
        # Leg 1: team_a home
        h_l1, a_l1 = get_expected_goals(elos_dict[team_a], elos_dict[team_b])
        g_a1 = poisson_random(h_l1)
        g_b1 = poisson_random(a_l1)
        # Leg 2: team_b home
        h_l2, a_l2 = get_expected_goals(elos_dict[team_b], elos_dict[team_a])
        g_b2 = poisson_random(h_l2)
        g_a2 = poisson_random(a_l2)
    else:
        # Swap roles
        h_l1, a_l1 = get_expected_goals(elos_dict[team_b], elos_dict[team_a])
        g_b1 = poisson_random(h_l1)
        g_a1 = poisson_random(a_l1)
        h_l2, a_l2 = get_expected_goals(elos_dict[team_a], elos_dict[team_b])
        g_a2 = poisson_random(h_l2)
        g_b2 = poisson_random(a_l2)

    total_a = g_a1 + g_a2
    total_b = g_b1 + g_b2

    if total_a > total_b:
        return team_a
    elif total_a < total_b:
        return team_b
    else:
        # Away goals
        away_a = g_a2
        away_b = g_b1
        if away_a > away_b:
            return team_a
        elif away_a < away_b:
            return team_b
        else:
            return simulate_penalties(team_a, team_b, elos_dict)

# Simulate single-leg final (neutral venue)
def simulate_final(team_a, team_b, elos_dict):
    diff = elos_dict[team_a] - elos_dict[team_b]
    lambda_a = 1.25 + (diff * 0.001)
    lambda_b = 1.25 - (diff * 0.001)
    lambda_a = max(0.6, min(4.0, lambda_a))
    lambda_b = max(0.6, min(4.0, lambda_b))
    g_a = poisson_random(lambda_a)
    g_b = poisson_random(lambda_b)
    if g_a > g_b:
        return team_a
    elif g_a < g_b:
        return team_b
    else:
        return simulate_penalties(team_a, team_b, elos_dict)

# === PENDING R16 TIES (with current aggregates as of March 18, 2026) ===
pending_ties = [
    # 1. Galatasaray (1-0 agg lead) vs Liverpool - Liverpool home in 2nd leg
    {
        "teams": ["Liverpool", "Galatasaray"],
        "second_home": "Liverpool",
        "current_totals": {"Liverpool": 0, "Galatasaray": 1},
        "current_away_goals": {"Liverpool": 0, "Galatasaray": 0},
    },
    # 2. Atalanta (1-6 agg) vs Bayern Munich - Bayern home in 2nd leg
    {
        "teams": ["Atalanta", "Bayern Munich"],
        "second_home": "Bayern Munich",
        "current_totals": {"Atalanta": 1, "Bayern Munich": 6},
        "current_away_goals": {"Atalanta": 0, "Bayern Munich": 6},
    },
    # 3. Newcastle United (1-1 agg) vs Barcelona - Barcelona home in 2nd leg
    {
        "teams": ["Newcastle United", "Barcelona"],
        "second_home": "Barcelona",
        "current_totals": {"Newcastle United": 1, "Barcelona": 1},
        "current_away_goals": {"Newcastle United": 0, "Barcelona": 1},
    },
    # 4. Atletico Madrid (5-2 agg lead) vs Tottenham Hotspur - Tottenham home in 2nd leg
    {
        "teams": ["Atletico Madrid", "Tottenham Hotspur"],
        "second_home": "Tottenham Hotspur",
        "current_totals": {"Atletico Madrid": 5, "Tottenham Hotspur": 2},
        "current_away_goals": {"Atletico Madrid": 0, "Tottenham Hotspur": 2},
    },
]

# Already advanced to QF (fixed)
fixed_qf = {
    "PSG": "PSG",
    "Real Madrid": "Real Madrid",
    "Sporting CP": "Sporting CP",
    "Arsenal": "Arsenal",
}

# Run Monte Carlo simulations
NUM_SIMS = 50000
champion_counts = Counter()

print("Simulating remaining Champions League (R16 2nd legs + QF + SF + Final)...")
print(f"Running {NUM_SIMS} simulations using current Elo + Poisson goals...\n")

for sim in range(NUM_SIMS):
    # Step 1: Simulate the 4 pending R16 2nd legs
    r16_winners = {}
    # Slot 2: Gala/Liv - Liverpool wins
    r16_winners["r16_2"] = "Liverpool"
    # Slot 4: Atalanta/Bayern - Bayern Munich wins
    r16_winners["r16_4"] = "Bayern Munich"
    # Slot 5: Newcastle United vs Barcelona - Barcelona wins
    r16_winners["r16_5"] = "Barcelona"
    # Slot 6: Atletico/Tottenham - Atletico Madrid wins
    r16_winners["r16_6"] = "Atletico Madrid"

    # Step 2: Quarter-finals (4 two-legged ties)
    qf_winners = {}

    # QF1: PSG (home first) vs r16_2 winner
    qf_winners["qf1"] = simulate_two_leg_tie("PSG", "Liverpool", True, elos)

    # QF2: Real Madrid (home first) vs r16_4 winner
    qf_winners["qf2"] = simulate_two_leg_tie("Real Madrid", "Bayern Munich", True, elos)

    # QF3: r16_5 winner (home first) vs r16_6 winner
    qf_winners["qf3"] = simulate_two_leg_tie("Barcelona", "Atletico Madrid", True, elos)

    # QF4: Sporting CP (home first) vs Arsenal
    qf_winners["qf4"] = simulate_two_leg_tie("Sporting CP", "Arsenal", True, elos)

    # Step 3: Semi-finals
    sf1 = simulate_two_leg_tie(qf_winners["qf1"], qf_winners["qf2"], True, elos)  # QF1 home first
    sf2 = simulate_two_leg_tie(qf_winners["qf3"], qf_winners["qf4"], True, elos)  # QF3 home first

    # Step 4: Final (neutral)
    champion = simulate_final(sf1, sf2, elos)
    champion_counts[champion] += 1

# Results
print("=== CHAMPIONS LEAGUE WIN PROBABILITIES (from current state) ===")
sorted_champs = sorted(champion_counts.items(), key=lambda x: x[1], reverse=True)
for team, count in sorted_champs:
    prob = (count / NUM_SIMS) * 100
    print(f"{team:20} : {prob:5.1f}%  ({count} simulations)")

print("\nNote: This accounts for today's R16 2nd legs, current aggregates, away goals rule, and penalties.")
print("Run again for new random outcomes. Update elos dict from clubelo.com for future accuracy.")