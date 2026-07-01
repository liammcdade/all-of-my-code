# Documentation Audit Report: Premier League Simulations

**Auditor:** Jules (Senior Technical Writer & Software Documentation Auditor)
**Date:** May 20, 2024
**Scope:** Review of 2025-26 and 2026-27 Premier League simulation scripts and their respective README files.

---

## 1. 2025-26 Season Simulation
**Files:** `sportsanalysis/premier-league/25-26-season.py` vs `sportsanalysis/premier-league/README.md`

### Mismatches
1.  **Goal Model Implementation (Line 244-246):**
    *   **README:** Describes a logistic scaling model for Expected Goals (XG): `0.7 + 1.8 / (1 + exp(-diff/400))`.
    *   **Code:** Uses an exponential model: `home_base * math.exp(diff / 800)`. This results in significantly different goal distributions for high Elo differences.
2.  **Critical Logic Bug - `get_expected_goals` (Line 444) [FIXED]:**
    *   **Initial Status:** `simulate_match` passed team indices (`h_idx`, `a_idx`) to `get_expected_goals` instead of their Elo ratings.
    *   **Impact:** The simulation previously used values like 0, 1, 2... as Elo ratings, making the strength of teams irrelevant to the XG calculation.
    *   **Correction:** The code has been updated to pass the average of attack and defense Elo ratings for each team.
3.  **FA Cup Simulation (Line 227):**
    *   **README:** Claims to simulate the FA Cup winner using a "simple Elo-based knockout."
    *   **Code:** `simulate_full_fa_cup_tournament()` only simulates a single match between Chelsea and Man City. It does not account for other Premier League teams.
4.  **Unused Data Features (Line 355):**
    *   **README:** Lists "WDL Rates" as a simulation component used for bias adjustments.
    *   **Code:** The `wdl_rates` dictionary is defined but never accessed or used in the `simulate_match` engine.
5.  **European Qualification Tracking (Line 780):**
    *   **README:** Mentions tracking "8+ European teams."
    *   **Code:** Specifically checks for `len(european_teams) >= 9`.
6.  **Broken Line References:**
    *   Almost all line references in the README are incorrect due to script updates.
    *   *Elo Ratings:* README says 8-28; Code is 80-100.
    *   *Current Table:* README says 54-76; Code is 128-153.
    *   *Fixtures:* README says 78-106; Code is 155-184.

### Suggested Clarifications
*   **"Bivariate Poisson":** The README mentions Bivariate Poisson, but the implementation in `simulate_match` (lines 463-475) uses a custom probability-based goal assignment for draws rather than a standard bivariate distribution.
*   **"RD is not actively used":** The README correctly states RD isn't used in match sims, but it *is* used in the `update_elo` function (line 560) to adjust the K-factor. This should be clarified as "not used for goal prediction but used for rating updates."

### Proposed Documentation Updates (2025-26)
*   Update `get_expected_goals` description to reflect exponential scaling or fix the code to match the logistic formula.
*   Correct all line number references.
*   Clarify that the FA Cup "tournament" is currently a placeholder simulation of a single final.

---

## 2. 2026-27 Season Simulation
**Files:** `sportsanalysis/premier-league/26-27-season.py` vs root `README.md`

### Mismatches
1.  **Simulation Iterations (Line 181):**
    *   **README:** States 10,000 simulations are run.
    *   **Code:** `NUM_SIMS` is set to 5,000.
2.  **Unimplemented Power Rating Adjustments (Lines 49-53):**
    *   **README:** Claims ratings are adjusted for form, injuries, and WDL tendencies.
    *   **Code:** While `add_team` accepts these as arguments, they are not stored in the registry's `elos` dictionary and are entirely ignored by the `run_simulation_vectorized` engine.
3.  **Promotion Logic (Line 194):**
    *   **README:** Describes a "Championship Playoff Simulation."
    *   **Code:** Uses a `random.random() < 0.5` coin flip between Southampton and Hull City.
4.  **Missing Output Features:**
    *   **README:** Lists "Match Probabilities," "Extreme Match Probabilities," and "Team Fixture Probabilities" as outputs.
    *   **Code:** These features are not implemented in the 26-27 script; only team-level statistics and the champion points range are printed.
5.  **Conference League Qualification:**
    *   **README:** Lists Conference League qualification for 6th place.
    *   **Code:** Only tracks positions 1-5 for CL/EL. The `Europe%` in the output table is simply `CL% + Europa%`.
6.  **Excitement Score Calculation (Line 213):**
    *   **README:** Describes a complex metric involving title, Top 4, and relegation contenders.
    *   **Code:** Calculates it as `(leader_pts - second_pts) / 10`.

### Suggested Clarifications
*   **"Vectorized Simulation":** The README fails to mention that the 26-27 version uses a Numba-accelerated vectorized engine, which is a major technical difference from the 25-26 version.
*   **"TeamRegistry":** This class is the core of team management but is completely undocumented.

### Proposed Documentation Updates (2026-27)
*   Synchronize `NUM_SIMS` between code and README.
*   Remove mentions of injury/form/WDL adjustments until they are integrated into the vectorized engine.
*   Add a section describing the `TeamRegistry` and the performance benefits of the `numba` JIT implementation.
*   Correct the "Excitement Score" definition to reflect the current points-gap implementation.

---

## Final Recommendation
The documentation for both seasons appears to have been written for a more feature-complete version of the simulation than what is currently implemented in the scripts. To align them:
1.  **Fix the Index Bug** in `25-26-season.py` immediately.
2.  **Synchronize Line Numbers** or remove specific line references from the READMEs to prevent them from becoming stale.
3.  **Update Feature Lists** to accurately reflect what the code actually outputs (e.g., removing "Fixture Probabilities" from the 26-27 README).