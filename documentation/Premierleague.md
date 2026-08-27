# Documentation Audit Report: Premier League Simulations

This report identifies inconsistencies between the implementation code and the documentation for the Premier League 2025-26 and 2026-27 simulation projects.

---

## 1. Premier League 2026-27 Season (Root README.md)

### Mismatches
*   **Simulation Count:** The README (Monte Carlo Simulations section) states 10,000 simulations, but `NUM_SIMS` in `26-27-season.py` (line 181) is set to **5,000**.
*   **League Size:** The documentation implies a standard 20-team Premier League. However, the code defines **18 fixed teams** (lines 24-30) and adds **1 promoted team** (line 186), resulting in a **19-team simulation**.
*   **Unimplemented Features:** The "Algorithm Overview" and "Features" sections claim the model adjusts for **Form**, **Injuries**, and **Win/Draw/Loss rates**. While `TeamRegistry.add_team` (line 43) accepts form/injury parameters, they are **never used** in the match engine (`calculate_match_params` or `run_simulation_vectorized`). WDL bias logic is entirely absent from the script.
*   **Championship Promotion:** The README describes a "Championship playoff simulation." In reality, the code performs a simple **50/50 coin flip** between Southampton and Hull City (line 186).
*   **Missing Outputs:** The README lists "Match Probabilities," "Extreme Match Probabilities," and "Team Fixture Probabilities" as generated outputs. These features are **not implemented** in the 26-27 script's `main` function.
*   **European Qualification:** The README mentions Conference League qualification for 6th place. The code only tracks Champions League (Top 4) and Europa League (5th), combining them into a single "Europe%" statistic (lines 284-290) without specific 6th-place logic.
*   **Side Effects:** The script has a side effect of **deleting the `__pycache__` directory** upon completion (line 259), which is not mentioned in the documentation.

### Suggested Clarifications
*   **Excitement Score:** The "Additional Statistics" output shows an "Average excitement score." The documentation should clarify that this is currently calculated as the **points gap between 1st and 2nd place** divided by 10 (line 251).
*   **Jargon:** Terms like "Monte Carlo," "Poisson modeling," and "JIT compilation" should be briefly defined for non-technical users.

### Proposed Documentation Updates (README.md snippet)
```markdown
- **Monte Carlo Simulations**: Runs 5,000 simulations (randomly selecting one of two potential promoted teams).
- **Algorithm Overview**: Uses ELO ratings with a Poisson-based match engine. Promotion is determined by a weighted random selection between Southampton and Hull City.
- **Output**: Generates team statistics (average points, standard deviation, and qualification probabilities) and excitement metrics.
```

---

## 2. Premier League 2025-26 Season (sportsanalysis/premier-league/README.md)

### Mismatches
*   **Broken References:** Nearly all line number references in the README are incorrect due to script updates. For example:
    *   Elo Ratings: Cited lines 8-28; Actual lines **80-100**.
    *   Current Table: Cited lines 54-76; Actual lines **102-125**.
    *   Fixtures: Cited lines 78-106; Actual lines **131-155**.
*   **XG Model Discrepancy:** The README (Match Engine section) describes "Logistic scaling" for Expected Goals. The code actually uses **Exponential scaling** via `math.exp(diff / 800)` (line 188).
*   **Qualification Thresholds:** The README (Statistics section) mentions tracking "8+ European teams," but the code tracks the probability of "**at least 9 teams**" qualifying (lines 490, 966).
*   **Tournament Logic:** The README describes complex Semi-final and Quarter-final structures for European competitions. However, the simulation simplifies this by running a **10,000-iteration sub-simulation of the Final only** (lines 470-500) to generate win probabilities for the main loop.
*   **Rating Deviation (RD):** The README states RD is "not actively used." However, the `update_elo` function (line 396) incorporates `rd_arr` into the K-factor and G-value calculations.

### Suggested Clarifications
*   **Bivariate Poisson:** The documentation refers to "Bivariate Poisson" modeling. The code implements a **Mixture Model** that switches between independent Poissons and shared means based on a random roll (lines 350-362). This should be clarified as a "modified Poisson model for correlated scoring."

### Proposed Documentation Updates (README.md snippet)
*   Update all line numbers to reflect the current 1046-line script.
*   Change the "Match Engine" description: "Expected Goals (XG): Exponential scaling (home_xg = home_base * exp(diff/800))."
*   Clarify European tracking: "Tracks probability of 9+ teams qualifying for Europe."

---

## 3. General Observations
*   **Dependencies:** Neither README mentions that `numba` is a required dependency for execution, which will cause a `ModuleNotFoundError` on a clean install of `requirements.txt`.
*   **Runnability:** While the scripts are syntactically correct, the 25-26 script assumes execution from the `sportsanalysis/premier-league/` directory to handle potential pathing for outputs.
