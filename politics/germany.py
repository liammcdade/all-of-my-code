import numpy as np
from scipy.stats import dirichlet

# Data from the 73.9% count
counted_pct = 78.8
remaining_pct = 100 - counted_pct

parties = {
    'AfD': 46.2, 'CDU': 16.3, 'SPD': 8.8, 'GRÜNE': 8.7,
    'LINKE': 8.2, 'BSW': 5.2, 'FDP': 2.5, 'FW': 1.1,
    'Tierschutz': 1.1, 'Garten': 0.6, 'Tierallianz': 0.6,
    'Volt': 0.3, 'PARTEI': 0.3, 'PdF': 0.2, 'Basis': 0.1
}

names = list(parties.keys())
props = np.array([parties[n] for n in names]) / 100.0

# Effective sample size – adjusts uncertainty (higher = less variance)
n_eff = 4000
alpha = props * n_eff

n_sim = 100_000
np.random.seed(2026)

# Simulate remaining vote distribution
rem_samples = dirichlet.rvs(alpha, size=n_sim)

# Final percentages (out of 100 total points)
counted_contrib = counted_pct * props
final_pcts = counted_contrib + remaining_pct * rem_samples

# 1. Popular vote winner
winners = np.argmax(final_pcts, axis=1)
winner_probs = np.bincount(winners, minlength=len(names)) / n_sim * 100

# 2. AfD > 50% popular vote
afd_idx = names.index('AfD')
afd_abs_majority = np.mean(final_pcts[:, afd_idx] > 50) * 100

# 3. BSW below 5%
bsw_idx = names.index('BSW')
bsw_below_5 = np.mean(final_pcts[:, bsw_idx] < 5) * 100

# Print
print("Simulation Results (100,000 runs)")
print("="*55)
print(f"Counted: {counted_pct}% | Remaining: {remaining_pct}%")
print("-"*55)
print("Popular vote win probabilities:")
for name, prob in zip(names, winner_probs):
    print(f"  {name:12} {prob:6.2f}%")
print("-"*55)
print(f"AfD reaches >50% popular vote: {afd_abs_majority:.2f}%")
print(f"BSW finishes below 5%:         {bsw_below_5:.2f}%")
print("-"*55)
print(f"⇒ AfD governing majority:     {bsw_below_5:.2f}%")