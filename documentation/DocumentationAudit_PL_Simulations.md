# Documentation Audit Report: Premier League Simulations

**Date:** May 22, 2024
**Auditor:** Jules, Senior Technical Writer & Software Documentation Auditor
**Scope:** `sportsanalysis/premier-league/` (2025-26 and 2026-27 season simulations)

---

## 1. Mismatches and Discrepancies

### A. 2026-27 Season Simulation (`26-27-season.py` vs Root `README.md`)

| Feature | Documentation Claim (Root `README.md`) | Actual Implementation (`26-27-season.py`) | Reference |
| :--- | :--- | :--- | :--- |
| **Simulation Count** | "Runs 10,000 simulations" | `NUM_SIMS = 5000` | Line 181 |
| **League Size** | Implies standard 20-team league | Simulates 19 teams (18 fixed + 1 promoted) | Lines 22, 185-188 |
| **Match Engine** | Adjusted for form, injuries, and WDL rates | Ratings are base ELO; adjustments not implemented in loop | Lines 120-151 |
| **Promotion Logic** | "Simulates Championship playoffs" | 50/50 coin flip between Southampton/Hull City | Line 186 |
| **Output: Match Probs** | "Win/draw/loss percentages for all remaining fixtures" | Not implemented; no match-specific probability output | N/A |
| **Output: Extreme Probs** | "Most likely home wins, draws, and away wins" | Not implemented | N/A |
| **Output: Team Fixtures** | "Probabilities of winning/losing/drawing all games" | Not implemented | N/A |
| **Excitement Score** | "Average excitement score" | Calculated as `(1st pts - 2nd pts) / 10` | Lines 213, 273 |

### B. 2025-26 Season Simulation (`25-26-season.py` vs `sportsanalysis/premier-league/README.md`)

| Item | Documentation Claim (`README.md`) | Actual Implementation (`25-26-season.py`) | Reference |
| :--- | :--- | :--- | :--- |
| **Line Numbers** | Elo ratings (8-28), Fixtures (78-106), etc. | Elo ratings (80-100), Fixtures (131-155). | Entire File |
| **XG Model** | "Logistic scaling" formula provided | Exponential scaling: `exp(diff / 800)` | Line 238 |
| **European Tracking** | Probability of "8+ European teams" | Probability of "at least 9 teams" | Line 738 |
| **Rating Deviation** | "RD is not actively used" | Used to adjust K-factor in `update_elo` | Lines 518-519 |
| **Euro Competition** | Describes Semi-finals and Two-leg ties | Simplified to single-match finals with hardcoded teams | Lines 683-706 |
| **FA Cup Simulations** | Part of the main Monte Carlo output | Final output based on separate 1,000 iteration loop | Lines 810-817 |

---

## 2. Suggested Clarifications

### Technical Jargon
*   **ELO Ratings:** The documentation assumes users understand ELO as a relative strength metric. A brief explanation of the 400-point scale (where +100 points ≈ 64% win probability) would benefit non-technical users.
*   **Poisson Distribution:** Used for goal modeling. Clarify that this models the probability of a given number of events occurring in a fixed interval.
*   **XG (Expected Goals):** Explain that this represents the quality of chances, used here to derive match outcomes from ELO differences.
*   **Monte Carlo Simulation:** Explicitly state that the "simulation" involves running thousands of random seasons to build a probability distribution.

### Audience Knowledge Gaps
*   **Execution Environment:** The documentation fails to mention that scripts **must** be run from the `sportsanalysis/premier-league/` directory to avoid relative path errors.
*   **Missing Dependencies:** `numba` and `tqdm` are critical for performance and UI but are not clearly listed as prerequisites for the 26-27 script.
*   **Numba JIT:** Users might be confused by the initial delay during the first run; explain that Numba is compiling the code for speed.

---

## 3. Proposed Updated Documentation Text

### For Root `README.md` (2026-27 Season)

**Algorithm Overview (Revised)**
1. **Power Ratings:** Uses base ELO ratings for 18 established teams plus a 50/50 promotion simulation for the final spot (Southampton or Hull City).
2. **Match Simulation:** Uses JIT-accelerated Poisson modeling with home advantage (33.8 pts) and team-specific ELO scaling.
3. **League Structure:** Simulates a 19-team season (36 games per team) to determine final standings.

**Output (Revised)**
*   **Team Statistics:** Average points, standard deviation, and probabilities for Title, CL (Top 4), and EL (5th).
*   **Excitement Score:** Measured by the points gap between 1st and 2nd place.

---

### For `sportsanalysis/premier-league/README.md` (2025-26 Season)

**Key Model Adjustments (Revised)**
*   **XG Model:** Goals are modeled using an exponential scaling factor based on ELO difference: `Home_XG = Base * exp(ELO_Diff / 800)`.
*   **Rating Deviation (RD):** While not used in the match engine directly, RD scales the ELO update K-factor, meaning results for teams with higher uncertainty (RD) have a larger impact on their rating.
*   **European Logic:** Tracks the probability of at least 9 teams qualifying for Europe, reflecting the new UEFA coefficients and competition formats.

---

## 4. Code Quality & Compliance Issues (`instructions.md`)

*   **Rule 4 & 12:** `main()` and the core simulation loops are excessively long and should be decomposed into `simulate_season()`, `calculate_stats()`, and `display_output()`.
*   **Rule 9:** ELO and Fixture data (lines 80-204 in 25-26) should be moved to a `data.py` or JSON file.
*   **Rule 16:** `25-26-season.py` (1046 lines) exceeds the 800-line limit and must be split.
*   **Rule 15:** Use `@dataclass` for the `table` dictionary in the 26-27 script to improve type safety and readability.
