# Documentation Audit Report: Premier League Simulation Project

**Auditor:** Jules (Senior Technical Writer & Software Documentation Auditor)
**Date:** May 2024
**Project:** Premier League Season Simulations (2025-26 & 2026-27)

## 1. Mismatches

### 2025-26 Season Simulation (`sportsanalysis/premier-league/25-26-season.py`)
- **Incorrect Line References**: Every line number reference in `sportsanalysis/premier-league/README.md` is outdated.
    - *Example*: Elo Ratings are documented as being at lines 8-28, but they actually start at line 80.
    - *Example*: Match Engine is documented at lines 478-523, but it is implemented at lines 443-480.
- **Home Advantage Value**: README (Line 469) states `Home advantage (33.8 Elo points)`. The code (Line 43) defines `HOME_ADVANTAGE_ELO = 60` and further randomizes it between 50 and 70 in `run_single_simulation` (Line 488).
- **European Tournament Depth**: README (Lines 187-324) describes semi-finals and two-leg ties for CL/EL/Conf. The code (Lines 718-744) only simulates a single-leg final for each.
- **RD (Rating Deviation)**: README states RD is "not actively used." However, `simulate_match` uses `rd_arr` (Line 568) via the `g(rd_val)` function to scale Elo updates.
- **Goal Model Discrepancy**: README describes a logistic scaling for XG. The code uses a probability-based outcome selector (Win/Draw/Loss) which then generates goals based on Poisson means.

### 2026-27 Season Simulation (`sportsanalysis/premier-league/26-27-season.py`)
- **Phantom Features**: The root `README.md` lists several features that are completely missing from the `26-27-season.py` script:
    - **Injury Penalties**: Not implemented.
    - **Form Adjustments**: Not implemented.
    - **Win/Draw/Loss Rates**: Not implemented.
    - **Match Probabilities Output**: The script does not output individual match probabilities or fixture difficulty.
- **Simulation Count**: README specifies 10,000 simulations. The code (Line 172) is set to `NUM_SIMS = 5000`.
- **Promotion Logic**: README claims to "Simulate Championship playoffs." The code (Line 183) uses a 50/50 `random.random()` check between Southampton and Hull City.
- **European Tiers**: README mentions Conference League tracking, but the code only tracks Champions League (Top 4) and Europa League (5th).

---

## 2. Suggested Clarifications

- **Dependency List**: Both READMEs are missing `numba`, which is a critical dependency for performance (especially in the 26-27 version).
- **Tiebreaker Rules**: Documentation should explicitly state that the simulation uses `Points > Goal Difference > Goals For` as the tiebreaking sequence, as implemented in the sorting keys (e.g., Line 545 in 25-26).
- **Runtime Performance**: The 25-26 simulation takes ~25-30 seconds for 25k iterations, significantly longer than the "12 seconds" documented.
- **Code Standards**: The documentation implies high-quality implementation, but the scripts violate several `instructions.md` rules:
    - **Rule 13 (Separate Calculation From Display)**: Massive print blocks are mixed with logic.
    - **Rule 10 (No Hidden State Mutation)**: 25-26 uses `global` to mutate simulation parameters mid-run.

---

## 3. Proposed Updated Documentation (Excerpts)

### Proposed for Root `README.md` (Features Section)
```markdown
## Features
- **Vectorized ELO Engine**: High-performance Monte Carlo simulation using Numba JIT.
- **Dynamic Promotion**: Simple randomized promotion logic for Championship contenders.
- **League Statistics**: Comprehensive tracking of average points, standard deviations, and qualification probabilities.
- **European Tracking**: Champions League (Top 4) and Europa League (5th place) qualification analysis.
```

### Proposed for 25-26 `README.md` (Match Engine Section)
```markdown
#### Match Engine
- **Elo Difference**: Adjusted Home Elo - Adjusted Away Elo + Randomized Home Advantage (50-70).
- **Outcome Selection**: Probabilities for Win/Draw/Loss derived from Elo gaps.
- **Goal Generation**: Bivariate Poisson model used to generate scorelines consistent with the selected outcome.
```

### Proposed Installation Instructions
```bash
## Installation
1. Clone the repository
2. Install required packages:
   ```bash
   pip install numpy numba tqdm
   ```
```
