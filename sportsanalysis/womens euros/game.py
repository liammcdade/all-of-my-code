# Fractional odds to decimal
def frac_to_decimal(frac):
    num, denom = map(int, frac.split('/'))
    return 1 + (num / denom)

# Odds
odds = {
    'England': '5/2',
    'Draw': '2/1',
    'Italy': '23/20'
}

# Step 1: Convert to decimal
decimal_odds = {team: frac_to_decimal(odds_str) for team, odds_str in odds.items()}

# Step 2: Convert to implied probabilities
implied_probs = {team: 1 / dec for team, dec in decimal_odds.items()}

# Step 3: Normalize
total_prob = sum(implied_probs.values())
normalized_probs = {team: prob / total_prob for team, prob in implied_probs.items()}

# Output
for team, prob in normalized_probs.items():
    print(f"{team}: {prob:.4f}")
