# Input fractional odds

fractional_odds = {
    'Spain Women': '4/6',
    'England Women': '5/2',
    'France Women': '11/2',
    'Germany Women': '14/1',
    'Italy Women': '20/1',
    'Switzerland Women': '100/1'
}

def fractional_to_float(frac):
    num, denom = map(int, frac.split('/'))
    return num / denom

# Convert fractional odds to implied probabilities
def implied_probability(frac):
    odd = fractional_to_float(frac)
    return 1 / (odd + 1)

# Calculate and normalize
implied_probs = {team: implied_probability(odd) for team, odd in fractional_odds.items()}
total = sum(implied_probs.values())
normalized_probs = {team: prob / total for team, prob in implied_probs.items()}

print("\nWomens Euros 2025 Title Probabilities (normalized):")

# Output
for team, prob in normalized_probs.items():
    print(f"{team:20}: ({prob * 100:.2f}%)")
