# Documentation Audit Report: Premier League Simulations

**Auditor:** Jules (Senior Technical Writer & Software Documentation Auditor)
**Date:** May 2024
**Scope:** `README.md` (Root), `sportsanalysis/premier-league/README.md`, `25-26-season.py`, `26-27-season.py`

---

## 1. Mismatches & Inconsistencies

### A. Premier League 2026-27 Season (`README.md` vs `26-27-season.py`)

| Feature | Documentation Claim | Actual Code Implementation | Line Reference |
| :--- | :--- | :--- | :--- |
| **Simulation Count** | 10,000 simulations | `NUM_SIMS = 5000` | Line 181 |
| **Promotion Logic** | "Simulates Championship playoffs" | Simple 50/50 coin flip between Southampton and Hull | Line 194 |
| **Missing Outputs** | Lists "Match Probabilities", "Extreme Match Probabilities", and "Team Fixture Probabilities" | These sections are not implemented and do not appear in console output. | N/A |
| **Algorithm** | "Poisson goal modeling" | Uses a Shared Goal Poisson model (Bivariate-style) with a `lambda_shared` variable for draw correlation. | Lines 84-101 |
| **Parameter Usage** | Ratings adjusted for Form, Injuries, and WDL rates | `add_team` accepts these parameters, but they are never passed or updated in the main simulation loop. | Lines 193-219 |
| **Internal Classes** | Not mentioned | `TeamRegistry` and `run_simulation_vectorized` are core but undocumented. | Lines 45, 107 |

### B. Premier League 2025-26 Season (`sportsanalysis/premier-league/README.md` vs `25-26-season.py`)

| Section | Documentation Reference | Actual Line Number | Discrepancy |
| :--- | :--- | :--- | :--- |
| **Elo Ratings** | Lines 8-28 | Lines 80-100 | **Major Mismatch** |
| **Current Table** | Lines 54-76 | Lines 128-153 | **Major Mismatch** |
| **Fixtures** | Lines 78-106 | Lines 155-185 | **Major Mismatch** |
| **European Elos** | Lines 109-130 | Lines 190-209 | **Major Mismatch** |
| **European Stats** | "8+ teams" qualifying | `len(european_teams) >= 9` | Tracked as "9+ teams" in code (Line 774). |
| **XG Model** | "Logistic scaling" | Exponential scaling: `exp(diff / 800)` | Lines 246-247 |
| **WDL Rates** | "Observed WDL probabilities used" | `wdl_rates` dict is defined but **never used** in logic. | Line 355 |
| **Side Effects** | Not mentioned | Deletes `__pycache__` directory upon completion. | Line 963 |

---

## 2. Suggested Clarifications

*   **Elo Scaling (Jargon):** The documentation mentions "400-scale Elo". For non-technical users, clarify that this means a 400-point difference represents a ~10x difference in win probability.
*   **Poisson Lambda:** When describing the goal model, clarify that "lambda" is the statistical term for the "expected number of goals" per match.
*   **Shared Goal Model:** The code uses `lambda_shared` to increase draw probability. The documentation should explain that this "Shared Goal" factor accounts for the fact that football scores are not purely independent (e.g., a 0-0 or 1-1 draw is more likely than independent Poisson would suggest).
*   **Monte Carlo Method:** Briefly explain that this means "running the season thousands of times with random variations to find the most likely outcomes."

---

## 3. Proposed Documentation Updates

### Updated Root `README.md` (Partial - Algorithm Section)
```markdown
### 1. Power Ratings
Uses base Elo ratings for the 18 starting teams, with a dynamic 50/50 promotion simulation between high-performing Championship sides (Southampton and Hull City).

### 2. Match Simulation
Uses a Correlation-Adjusted Poisson distribution:
- **Home Advantage**: +33.8 Elo boost for home teams.
- **Shared Goal Factor**: Increases realism by correlating scores in tight matches, improving draw accuracy.
- **Tempo Scaling**: Reduces goal expectations in high-stakes, high-Elo matchups.
```

### Updated `sportsanalysis/premier-league/README.md` (Partial - Line References)
```markdown
## Data Inputs
- **Elo Ratings**: Base scores (Lines 80-100).
- **Current Table**: Current season standings (Lines 128-153).
- **Fixtures**: Remaining matches (Lines 155-185).
- **European Elos**: Ratings for UEFA competitions (Lines 190-209).
```

---

## 4. Final Recommendations

1.  **Code-Doc Synchronization:** Update the 26-27 script to either implement the missing "Match Probabilities" output or remove the reference from the README.
2.  **Logic Cleanup:** Remove the `wdl_rates` dictionary from the 25-26 script if it is truly deprecated, or integrate it into the `simulate_match` function as the documentation suggests.
3.  **Transparency:** Document the deletion of `__pycache__` as a side effect or remove that logic to follow standard Python behavior.
