# Documentation Audit Report: Premier League Simulation Project

This audit compares the implementation of the Premier League simulation scripts (`25-26-season.py` and `26-27-season.py`) against their respective documentation (`sportsanalysis/premier-league/README.md` and the root `README.md`).

---

## 1. Mismatches & Technical Inconsistencies

### **2025-26 Season Simulation (`sportsanalysis/premier-league/25-26-season.py`)**

*   **Critical Logic Bug (Match Engine)**:
    *   **Mismatch**: In `simulate_match` (line 455), the function `get_expected_goals` is passed `h_idx` and `a_idx` (team indices 0-19) instead of the actual Elo ratings.
    *   **Impact**: Team strength is virtually ignored during goal expectation calculation, making results nearly random regardless of Elo.
*   **Model Type Discrepancy**:
    *   **Mismatch**: The documentation (lines 100-101) describes the model as "Bivariate Poisson." The code (lines 474-479) uses a "Shared Lambda Poisson Model" where a shared component is added to independent Poisson samples.
*   **European Qualification Logic**:
    *   **Mismatch**: Documentation mentions tracking the probability of "8+ European teams" (line 145), but the code (line 616) specifically checks for `>= 9`.
*   **Tournament Structure Oversimplification**:
    *   **Mismatch**: Documentation describes a full semi-final and final structure for EL/CL/Conf (lines 62-90). However, the simulation loop (lines 566-586) only simulates a single-match final between two hardcoded teams per competition.
*   **Missing Parameters in Docs**:
    *   **Mismatch**: `get_expected_goals` (line 213) accepts `min_lambda` and `max_lambda` which are not mentioned in the documentation's algorithm overview.

### **2026-27 Season Simulation (`sportsanalysis/premier-league/26-27-season.py`)**

*   **Simulation Count Mismatch**:
    *   **Mismatch**: Root README states "Runs 10,000 simulations" (Features section). The code `NUM_SIMS` is hardcoded to `5,000` (line 144).
*   **Unimplemented Model Modifiers**:
    *   **Mismatch**: The "Algorithm Overview" describes adjustments for "Form, Injuries, and Win/Draw/Loss rates." While the `TeamRegistry` class has placeholders for these (line 52), the `main` loop and `calculate_match_params` (line 74) completely ignore these factors.
*   **Promotion Logic**:
    *   **Mismatch**: README claims a "Championship Playoff Simulation." The code (line 161) performs a simple 50/50 `random.random() < 0.5` coin flip between Southampton and Hull City.
*   **League Size Inconsistency**:
    *   **Mismatch**: The simulation is hardcoded for 19 teams (18 fixed + 1 promoted, line 23), whereas the Premier League standard and parts of the documentation imply a 20-team structure.
*   **Undocumented Side Effects**:
    *   **Mismatch**: The script explicitly deletes the `__pycache__` directory at the end of execution (line 217), which is not mentioned in the documentation.

---

## 2. Suggested Clarifications

*   **Installation Prerequisites**: The `requirements.txt` file is missing `numba`. Since both scripts rely heavily on `@numba.jit`, the installation instructions should explicitly include `pip install numba`.
*   **Usage Context**: The 25-26 script assumes certain relative pathing or execution context. Clarify that scripts should be run from the repository root as `python sportsanalysis/premier-league/25-26-season.py`.
*   **XG Model Specification**: The 25-26 model uses an **Exponential** scaling (`exp(diff/800)`), while the 26-27 model uses **Logistic** scaling (`1 / (1 + exp(-diff/300))`). The documentation should specify which model is being used in each season's README to avoid confusion for users tuning parameters.

---

## 3. Proposed Documentation Updates (Snippets)

### **Updated root `README.md` (2026-27 Season)**

```markdown
## Algorithm Overview

### 1. Power Ratings
Uses ELO ratings as the primary indicator of team strength.
- **Note**: Modifiers for form and injuries are currently reserved for future implementation and are not active in the 5,000-sim version.

### 3. Promotion
- **Promotion Model**: Simulates a 50/50 probability between the top two Championship contenders (Southampton and Hull City) for the final promotion spot.
```

### **Updated `sportsanalysis/premier-league/README.md` (2025-26 Season)**

```markdown
### Match Engine
- **Elo Difference**: Adjusted home Elo - adjusted away Elo + home advantage.
- **Expected Goals (XG)**: Uses an **Exponential model** (home_lambda = base * exp(diff/800)) to calculate scoring potential.
- **Goal Simulation**: Shared Lambda Poisson model to account for correlated scoring and draws.
- **European Tracking**: Probabilities for 9+ teams qualifying are calculated to reflect extreme coefficient scenarios.
```

### **General Installation Instructions**

```bash
# Recommended installation for JIT-accelerated simulations
pip install numpy numba tqdm rich pandas
```

---
**Review Conclusion**: The documentation is currently an "idealized" version of the project. To align with the code, the descriptions of complex playoff simulations and Elo modifiers (Form/Injury) should be removed or marked as "Planned," and the critical logic bug in the 25-26 XG calculation should be fixed to match the documentation's intent.
