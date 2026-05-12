import math

def elo_probability(rating_a, rating_b):
    return 1 / (1 + 10 ** ((rating_b - rating_a) / 400))

# Use the estimates from earlier
fury_elo = 2175      # midpoint of 2150–2200
joshua_elo = 2075   # midpoint of 2050–2100

fury_prob = elo_probability(fury_elo, joshua_elo)
joshua_prob = 1 - fury_prob

print(f"Fury win probability: {fury_prob:.2%}")
print(f"Joshua win probability: {joshua_prob:.2%}")