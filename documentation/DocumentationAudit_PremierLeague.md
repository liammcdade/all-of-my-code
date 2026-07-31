# Documentation Audit Report: Premier League Simulations
**Date:** June 20, 2024
**Auditor:** Senior Technical Writer & Software Documentation Auditor
**Scope:** `sportsanalysis/premier-league/25-26-season.py`, `sportsanalysis/premier-league/26-27-season.py`, and associated README files.

---

## 1. Premier League 2025-26 Season Simulation

### 1.1 Mismatches & Inconsistencies

*   **Critical Line Number Mismatches:** The `sportsanalysis/premier-league/README.md` is significantly out of sync with `25-26-season.py`.
    *   **Elo Ratings:** README cites lines 8-28; actual code is at lines 80-100.
    *   **Current Table:** README cites lines 54-76; actual code is at lines 128-153.
    *   **Fixtures:** README cites lines 78-106; actual code is at lines 155-184.
    *   **Match Engine:** README cites lines 478-523; actual code is at lines 443-480.
    *   **Monte Carlo Loop:** README cites lines 579-754; actual code is at lines 751-808.
*   **XG Model Discrepancy:** The README (Premier League Simulation > Match Engine) claims the model uses "Logistic scaling" for Expected Goals (XG). However, `get_expected_goals` (line 247) implements an **exponential model** (`exp(diff / 800)`).
*   **European Qualification Logic:**
    *   The README mentions tracking the probability of "**8+ European teams**" qualifying. The code actually tracks "**at least 9**" teams (line 782: `if len(european_teams) >= 9: eight_european += 1`).
    *   The README describes a complex two-leg tournament structure for European competitions. While helper functions for this exist (lines 257-330), the main simulation actually uses a mixture of pre-computed win probabilities (lines 717-748) and simplified final matches.
*   **Side Effects:** The script contains an undocumented side effect: it forcibly deletes the `__pycache__` directory upon completion (line 806).

### 1.2 Suggested Clarifications

*   **Rating Deviation (RD):** The README states RD is "not actively used," but the `update_elo` function (line 560) explicitly incorporates `rd_arr` into the G-value calculation, which directly affects the K-factor and ELO updates. This contradiction should be resolved.
*   **Bivariate Poisson:** The README mentions "Bivariate Poisson with shared lambda." For a general audience, it should be clarified that this is a statistical method used to correlate home and away scores (increasing draw probability).

### 1.3 Compliance Notes (Internal)

*   **Rule 16 Violation:** `25-26-season.py` is 1046 lines, exceeding the 800-line hard limit.
*   **Rule 9 Violation:** Large ELO and fixture datasets are embedded directly in the script (lines 80-204) rather than externalized to CSV or JSON.

---

## 2. Premier League 2026-27 Season Simulation

### 2.1 Mismatches & Inconsistencies

*   **Simulation Parameter Discrepancy:** The root `README.md` states the simulation runs **10,000 iterations**. The actual script `26-27-season.py` is configured for **5,000 iterations** (line 181: `NUM_SIMS = 5000`).
*   **Championship Promotion Logic:** The README describes a "Championship playoff simulation." In reality, the code performs a **50/50 coin flip** between Southampton and Hull City (line 194) to determine the 20th team.
*   **Feature Gaps (README vs. Code):** The following features listed in the "Output" section of the README are **not implemented** in the 2026-27 script:
    *   Match Probabilities (Win/Draw/Loss for remaining fixtures).
    *   Extreme Match Probabilities (Biggest home/away wins).
    *   Team Fixture Probabilities (Win/Lose/Draw all games).
*   **ELO Adjustment Claims:** The README claims ratings are adjusted for "Form, Injuries, and WDL rates." While the `add_team` method (line 51) accepts these parameters, they are **ignored** by the core simulation engine (`run_simulation_vectorized`, lines 107-151), which only uses base ELO.
*   **European Qualification:** The script tracks Champions League (Top 4) and Europa League (5th) but completely omits the **Conference League** qualification mentioned in the README.

### 2.2 Suggested Clarifications

*   **Excitement Score:** The script calculates an "Excitement Score" by dividing the points gap between 1st and 2nd place by 10 (line 254). This is a very specific (and arguably inverse) metric that should be clearly defined in the documentation to avoid confusing users who might expect a high score to represent a *close* race.
*   **TeamRegistry:** The script uses a `TeamRegistry` class (lines 45-69) to manage team data, but this internal architecture is not mentioned in the documentation, making it difficult for developers to extend.

### 2.3 Compliance Notes (Internal)

*   **Rule 4 Violation:** The `main()` function (lines 174-263) is ~89 lines long, exceeding the 60-line maximum.
*   **Rule 15 Violation:** The script uses raw dictionaries for team data instead of the required `dataclasses`.

---

## 3. Actionable Recommendations

1.  **Sync Line Numbers:** Immediately update the 2025-26 README to reflect the current file structure.
2.  **Correct Mathematical Descriptions:** Update the README to accurately reflect the Exponential XG model and the ELO-only simulation logic in the 26-27 script.
3.  **Externalize Data:** Move the ELO ratings and fixtures from both scripts into a `data/` directory as CSV files to satisfy Rule 9 and improve documentation readability.
4.  **Feature Alignment:** Either implement the missing "Match Probabilities" in the 26-27 script or remove them from the root README to avoid misleading users.
5.  **Refactor for Compliance:** Split the `main()` functions and large classes in both scripts to adhere to the Python Code Quality Ruleset before the next documentation cycle.

---

## 4. Proposed Documentation Updates (Samples)

### 4.1 Corrected 25-26 README Section (Data Inputs)
```markdown
## Data Inputs
- **Elo Ratings**: Base Elo scores for Premier League teams (lines 80-100), plus rating deviations (RD) for uncertainty (lines 105-126). RD is used to calculate the K-factor during ELO updates.
- **Current Table**: Mid-season statistics (matches played, wins/draws/losses, goals for/against, points, remaining games) for each team (lines 128-153).
- **Fixtures**: List of remaining matches, grouped by round (lines 155-184).
- **European Elos**: Elo ratings for teams in Europa League (lines 190-195), Champions League (lines 197-202), and Conference League (lines 204-209).
```

### 4.2 Updated 26-27 README Section (Features & Output)
```markdown
## Features
- **ELO-Based Ratings**: Pure ELO-based strength ratings for 18 Premier League teams.
- **Monte Carlo Simulations**: Runs 5,000 iterations to generate league outcomes.
- **Championship Promotion**: Simplified promotion logic featuring a coin flip between top contenders.
- **Progress Tracking**: Real-time progress bars using `tqdm`.

## Output
The simulation generates console output including:
- **Team Statistics**: Average points, standard deviation, and qualification probabilities (Title, CL, EL, Relegation).
- **Points to Win League**: Minimum and maximum points observed in simulations.
- **Relegation Stats**: Probability of a team being relegated with 40+ points.
- **Season Excitement**: A metric based on the final points gap between the top two teams.
```
