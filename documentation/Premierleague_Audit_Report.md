# Premier League Simulation Documentation Audit Report

**Date:** 2025-05-24
**Auditor:** Senior Technical Writer / Documentation Auditor

## Overview
This report evaluates the alignment between the Premier League simulation codebase and its accompanying documentation. The audit focused on `25-26-season.py`, `26-27-season.py`, `sportsanalysis/premier-league/README.md`, and the root `README.md`.

---

## 1. Mismatches and Discrepancies

### A. Logic and Algorithm Errors
| Component | Mismatch Type | Description |
| :--- | :--- | :--- |
| **25-26 Season** | **Critical Bug** | `simulate_match` passes team indices (`h_idx`, `a_idx`) to `get_expected_goals` instead of Elo ratings at line 444. |
| **25-26 Season** | **Model Parameters** | README claims 33.8 Home Advantage; code uses 60 (randomized 50-70). |
| **25-26 Season** | **Methodology** | README describes "Logistic scaling" and "Bivariate Poisson" (likely 26-27 text); code uses "Exponential scaling" and "Custom Mixture Model". |
| **26-27 Season** | **Missing Features** | README lists "Match Probabilities" and "Fixture Probabilities" as key features; these are not implemented in the script. |
| **26-27 Season** | **Promotion Logic** | README claims full "Championship playoff simulation"; code uses 50/50 coin flip. |
| **26-27 Season** | **Algorithm** | README claims Form and Injury adjustments; these are defined but not used in the match engine. |

### B. Statistical and Configuration Mismatches
| Component | Mismatch Type | Code Value | Documentation Value |
| :--- | :--- | :--- | :--- |
| **26-27 Season** | **Iteration Count** | 5,000 simulations | 10,000 iterations |
| **26-27 Season** | **League Size** | 19 teams | Standard (20) implied |
| **25-26 Season** | **European Tracking** | "At least 9 teams" | "8+ teams" |

### C. Side Effects and Environment
*   **Undocumented Side Effect:** `26-27-season.py` deletes its `__pycache__` at line 237.
*   **Dependency Gap:** `numba` is required for execution but missing from `requirements.txt`.

---

## 2. Suggested Clarifications

1.  **Working Directory:** Specify that `25-26-season.py` must be executed from `sportsanalysis/premier-league/` to handle relative logic correctly.
2.  **Implementation Status:** Explicitly mark Form and Injury adjustments in 26-27 as "stubs" or "under development."
3.  **Data Source:** Clarify that "observed rates" are static hardcoded snapshots, not real-time data.

---

## 3. Proposed Documentation Updates

### Updated `requirements.txt`
```text
numpy>=1.21.0
pandas>=1.3.0
tqdm>=4.62.0
numba>=0.56.0  # Added: Required for simulation acceleration
rich>=10.0.0
requests>=2.25.0
beautifulsoup4>=4.9.0
tabulate>=0.8.9
```

### Revised Root README (26-27 Algorithm Overview)
```markdown
### 1. Power Ratings
Uses ELO ratings as the base for team strength.
*Note: Form and Injury adjustments are defined in the TeamRegistry but are not currently integrated into the match simulation engine.*

### 2. Match Simulation
Uses a JIT-accelerated Poisson distribution for goals with:
- Home advantage (33.8 ELO points)
- Expected Goals (XG) based on logistic scaling
- Shared goal components to model correlated scoring (draws)
```

### Revised 25-26 README (Match Engine Section)
```markdown
#### Match Engine (lines 443-490)
- **Elo Difference**: Calculated using adjusted ratings (Base Elo + Form - Injury Penalty).
- **Expected Goals (XG)**: Uses an exponential scaling model:
  `home_xg = home_base * exp(elo_diff / 800)`
```

---

## 4. Final Conclusion
The documentation is currently out of sync with the implementation, primarily due to overlapping content between seasons and descriptions of unimplemented "planned" features. The critical bug in the 25-26 XG logic should be addressed immediately to ensure the "realistic" claim in the documentation is met.
