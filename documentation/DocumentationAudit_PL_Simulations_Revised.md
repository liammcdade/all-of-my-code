# Documentation Audit Report: Premier League Simulations

**Auditor:** Jules (Senior Technical Writer & Software Documentation Auditor)
**Date:** 2025-05-13
**Scope:**
- Root `README.md` (2026-27 Season) vs `sportsanalysis/premier-league/26-27-season.py`
- `sportsanalysis/premier-league/README.md` (2025-26 Season) vs `sportsanalysis/premier-league/25-26-season.py`

---

## 1. Mismatches

### A. 2026-27 Season (Root README.md vs 26-27-season.py)

1.  **Simulation Count**:
    - **README**: "Runs 10,000 simulations"
    - **Code (Line 181)**: `NUM_SIMS = 5000`
2.  **Team Count/League Structure**:
    - **README**: Implies a standard Premier League structure (20 teams).
    - **Code (Lines 21-34)**: Defines 18 fixed teams + 1 promoted team (`promoted = "Southampton" if random.random() < 0.5 else "Hull City"`), totaling 19 teams per simulation. This results in 36 matches played per team, not 38.
3.  **ELO Adjustments**:
    - **README (Algorithm Overview)**: Claims ELO is adjusted for Form, Injuries, and Win/Draw/Loss rates.
    - **Code**: The `TeamRegistry` and simulation logic do not implement these adjustments. ELO is used statically or updated solely based on match results via `run_simulation_vectorized`.
4.  **Championship Promotion**:
    - **README**: "Simulates Championship playoffs to determine promotion"
    - **Code (Line 194)**: Uses a 50/50 coin flip between Southampton and Hull City.
5.  **Output Features**:
    - **README**: Lists "Match Probabilities", "Extreme Match Probabilities", and "Team Fixture Probabilities" as generated outputs.
    - **Code**: These features are missing from the `26-27-season.py` script.
6.  **Installation/Dependencies**:
    - **README**: References `requirements.txt`.
    - **Code**: Requires `numba` for JIT compilation, which is missing from the root `requirements.txt`.

### B. 2025-26 Season (sportsanalysis/premier-league/README.md vs 25-26-season.py)

1.  **Line Number References**:
    - **README**: Every line number reference is incorrect (e.g., Elo ratings at lines 8-28 when they are actually at 80-100; Current Table at 54-76 when at 128-153; Fixtures at 78-106 when at 131-155).
2.  **Expected Goals (XG) Model**:
    - **README**: Describes "Logistic scaling (home_xg = 0.7 + 1.8 / (1 + exp(-diff/400))".
    - **Code (Line 247-248)**: Implements an exponential model: `home_lambda = home_base * math.exp(diff / 800)`.
3.  **Rating Deviation (RD)**:
    - **README**: States "RD is not actively used in match simulations."
    - **Code (Line 396)**: Incorporates RD into K-factor calculation: `k_h = K_FACTOR_BASE / (1 + rd_arr[h_idx]/100)`.
4.  **European Qualification Probability**:
    - **README**: Mentions tracking "8+ European teams".
    - **Code (Line 731)**: Specifically checks for `len(european_teams) >= 9`.

---

## 2. Suggested Clarifications

- **ELO Rating**: For a general audience, clarify that this is a relative skill rating system where the probability of winning is a function of the difference between ratings.
- **Poisson Distribution**: Explain that this is used to model the number of independent events (goals) occurring in a fixed interval (a football match).
- **Monte Carlo Simulation**: Clarify that this involves running the entire season thousands of times with random variability to find the most probable distributions of outcomes.
- **K-Factor**: Briefly explain that the K-factor determines how much a team's rating changes after a match (higher K = more volatility/responsiveness to recent results).

---

## 3. Proposed Updated Documentation (Selected Sections)

### Proposed Update for Root README.md (2026-27)

#### Algorithm Overview
1. **Power Ratings**: Uses static ELO ratings. Future versions are planned to include adjustments for form and injuries.
2. **Promotion Logic**: Currently models a 19-team top flight where the final spot is determined by a weighted probability between top Championship contenders (Southampton and Hull City).

#### Usage
**Note**: Ensure `numba` is installed for performance optimization:
```bash
pip install numba
```

### Proposed Update for 2025-26 README.md

#### Match Engine
- **Expected Goals (XG)**: Calculated using an exponential relationship to ELO difference: `λ = base * exp(ΔELO / 800)`. This ensures that goal expectations scale realistically with team strength gaps.
- **Rating Deviation**: While not used to adjust the match outcome directly, RD is used to scale the K-factor, allowing ratings for teams with higher uncertainty to adjust more rapidly.

---
