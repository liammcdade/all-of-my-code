# Documentation Audit Report: Premier League Simulation Project

**Audit Date:** June 14, 2024
**Auditor:** Senior Technical Writer & Documentation Auditor
**Scope:** 2025-26 Season Simulation, 2026-27 Season Simulation, and Compliance with `instructions.md`.

---

## 1. Mismatches and Discrepancies

### 2026-27 Season (`README.md` vs `26-27-season.py`)

| Feature | Documentation Claim | Implemented Code State | Reference |
| :--- | :--- | :--- | :--- |
| **Simulation Count** | 10,000 simulations | `NUM_SIMS = 5000` | `26-27-season.py:166` |
| **League Composition** | Standard 20-team league | 19-team league (18 fixed + 1 promoted) | `26-27-season.py:22, 178-181` |
| **Promotion Logic** | "Simulates Championship playoffs" | 50/50 coin flip between two teams | `26-27-season.py:178` |
| **Power Ratings** | Adjustments for form, injuries, WDL rates | Uses base ELO only; no adjustment logic | `26-27-season.py:48-52, 139-142` |
| **Missing Outputs** | Match Probabilities, Extreme Match Probabilities, Team Fixture Probabilities | Feature not implemented in script output | N/A |
| **European Logic** | Tracks CL, EL, and Conference League | Only tracks CL (Top 4) and EL (5th) | `26-27-season.py:192-197, 226-231` |
| **Excitement Score** | "Measures season tightness" | Calculated as `(leader_pts - second_pts) / 10` | `26-27-season.py:213, 223` |

### 2025-26 Season (`sportsanalysis/premier-league/README.md` vs `25-26-season.py`)

| Feature | Documentation Claim | Implemented Code State | Reference |
| :--- | :--- | :--- | :--- |
| **Line References** | Elo ratings at lines 8-28 | Actually located at lines 80-100 | README: Data Inputs |
| **Line References** | Current table at lines 54-76 | Actually located at lines 102-125 | README: Data Inputs |
| **Line References** | Fixtures at lines 78-106 | Actually located at lines 131-155 | README: Data Inputs |
| **XG Goal Model** | "Logistic scaling" | Uses exponential scaling: `exp(diff / 800)` | `25-26-season.py:186-187` |
| **European Tracking**| Probability of "8+ European teams" | Tracks "at least 9 European teams" | `25-26-season.py:382, 458` |
| **ELO Deviation** | "RD is not actively used" | Used in `update_elo` for K-factor and G-value | `25-26-season.py:175, 290-305` |
| **Tournament Depth**| Full semi-final/two-leg structures | Limited to single-match finals for hardcoded teams | `25-26-season.py:343-366` |

---

## 2. Suggested Clarifications

*   **Jargon:** The term "Bivariate Poisson" is used in the 2025-26 documentation, but the code implements a shared lambda mixture model. This should be clarified as "Correlated Poisson modeling" to avoid confusing statistical purists.
*   **Vectorization:** The 2026-27 script utilizes a Numba-accelerated vectorized engine (`run_simulation_vectorized`) which is significantly different from the 2025-26 logic. The documentation should explain that this version prioritizes raw execution speed over granular feature depth (like injuries/form).
*   **Execution Environment:** Both scripts assume execution from the `sportsanalysis/premier-league/` directory. Running them from the repository root results in relative path errors for output files. This must be explicitly stated in the "Usage" section.
*   **Promotion Complexity:** In the 2026-27 README, "Championship Playoff Simulation" implies a tournament bracket. The documentation should be updated to reflect that it is currently a randomized selection between two candidate teams.
*   **Dependency Management:** The root `requirements.txt` is missing the `numba` package, which is required for the JIT-accelerated simulations in both scripts. Users following the installation instructions will encounter `ModuleNotFoundError`.

---

## 3. Proposed Documentation Updates

### Updated 2026-27 Features Section
```markdown
## Features (Current Implementation)
- **Vectorized Match Engine**: JIT-compiled simulation for high-speed Monte Carlo iterations.
- **Dynamic Promotion**: Randomized entry of either Southampton or Hull City to determine the final league member.
- **European Qualification**: Probability tracking for Champions League (Top 4) and Europa League (5th).
- **Season Excitement Index**: Tracks the points gap between 1st and 2nd place.
```

### Updated 2025-26 Match Engine Section
```markdown
#### Match Engine
- **Elo Difference**: Adjusted home Elo - adjusted away Elo + home advantage (60 points).
- **Expected Goals (XG)**: Exponential scaling (home_lambda = base * exp(diff/800)).
- **Goal Simulation**: Correlated Poisson distribution using a shared lambda component to reflect draw tendencies.
```

---

## 4. Coding Standard Compliance Review

*   **Rule 4 (Function Size):** **VIOLATION.** `assign_europe` in `25-26-season.py` (lines 470-622) and `main` in `26-27-season.py` exceed the 60-line limit.
*   **Rule 9 (Giant Dictionaries):** **VIOLATION.** Large ELO datasets and fixture lists are embedded directly in the scripts (e.g., `25-26-season.py:80-204`).
*   **Rule 15 (Dataclasses):** **PARTIAL COMPLIANCE.** `25-26-season.py` uses dataclasses for results, but `26-27-season.py` relies on raw dictionaries for table data.
*   **Rule 16 (File Length):** **VIOLATION.** `25-26-season.py` is 1046 lines, exceeding the 800-line hard limit.
*   **Rule 10 (Side Effects):** **VIOLATION.** `26-27-season.py` contains a hardcoded side effect that deletes the `__pycache__` directory upon completion.
