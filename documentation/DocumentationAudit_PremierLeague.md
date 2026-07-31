# Documentation Audit Report: Premier League Simulations

**Auditor:** Senior Technical Writer & Software Documentation Auditor
**Date:** July 5, 2024
**Scope:**
- Root `README.md` (pertaining to 2026-27 Season)
- `sportsanalysis/premier-league/README.md` (pertaining to 2025-26 Season)
- `sportsanalysis/premier-league/25-26-season.py`
- `sportsanalysis/premier-league/26-27-season.py`

---

## 1. Mismatches

### 2026-27 Season Simulation (Root `README.md` vs `26-27-season.py`)

1.  **Simulation Count**:
    - **Documentation**: Claims 10,000 simulations.
    - **Code**: `NUM_SIMS = 5000` (line 181).
2.  **Promotion Logic**:
    - **Documentation**: Describes a "Championship Playoff Simulation".
    - **Code**: Implements a simple 50/50 coin flip between Southampton and Hull City (line 194).
3.  **Power Rating Adjustments**:
    - **Documentation**: Lists adjustments for form, injuries, and WDL tendencies.
    - **Code**: While the `TeamRegistry.add_team` method accepts `form` and `injury` arguments (line 49), they are never stored or used. The simulation uses raw Elo ratings from `ELO_RATINGS` (lines 35-41).
4.  **Missing Output Features**:
    - **Documentation**: Lists "Match Probabilities", "Extreme Match Probabilities", and "Team Fixture Probabilities" as generated outputs.
    - **Code**: These features are not implemented. The output is limited to Team Statistics, Points to Win League, and specific European/Relegation probabilities (lines 240-260).
5.  **European Qualification**:
    - **Documentation**: Mentions "Conference League: 6th place".
    - **Code**: The tracking logic for Conference League is absent from the simulation loop (lines 201-210) and the final summary display.
6.  **Excitement Score**:
    - **Documentation**: Describes a "contender-based metric" in the Algorithm Overview.
    - **Code**: Calculates it simply as `(leader_pts - second_pts) / 10` (lines 186 and 213).

### 2025-26 Season Simulation (`sportsanalysis/premier-league/README.md` vs `25-26-season.py`)

1.  **Line Number References**:
    - **Discrepancy**: Nearly all line number references in the README are incorrect. For example:
        - Elo ratings: Cited at 8-28; actually at 80-100.
        - Current Table: Cited at 54-76; actually at 128-153.
        - Fixtures: Cited at 78-106; actually at 155-179.
        - European Elos: Cited at 109-130; actually at 190-210.
2.  **Unused Logic (WDL Rates)**:
    - **Documentation**: Lists "WDL Rates" as a data input (line 420-441).
    - **Code**: The `wdl_rates` dictionary (line 355) is defined but is never accessed by `simulate_match` or the simulation engine.
3.  **FA Cup "Tournament"**:
    - **Documentation**: Describes a "simple Elo-based knockout" for the FA Cup winner.
    - **Code**: `simulate_full_fa_cup_tournament` (line 228) only simulates a single match between Chelsea and Man City.
4.  **XG Model Discrepancy**:
    - **Documentation**: Claims "Logistic scaling" for XG.
    - **Code**: Uses an exponential model `exp(diff/800)` in `get_expected_goals` (lines 232-233).
5.  **RD Usage**:
    - **Documentation**: Claims "RD is not actively used in match simulations."
    - **Code**: The `update_elo` function (line 560) explicitly uses `rd_arr` to calculate the `g_val` and K-factor.

### Coding Standards Compliance (`instructions.md`)

1.  **Rule 4 (Function Size)**: `main()` in `26-27-season.py` (~89 lines) and `run_single_simulation` in `25-26-season.py` (~95 lines) exceed the 60-line maximum.
2.  **Rule 9 (Giant Dictionaries)**: Both scripts embed massive Elo and fixture datasets (hundreds of lines) directly in the source code rather than externalizing them.
3.  **Rule 16 (File Length)**: `25-26-season.py` is ~1050 lines, exceeding the 800-line absolute maximum.

---

## 2. Clarifications

- **Elo vs. XG**: The documentation for 25-26 mentions that match outcomes use "custom XG formulas instead of pure Elo probabilities," but the `update_elo` function still relies on standard Elo probability math. This needs to be clarified to explain how the two systems interact.
- **Monte Carlo Iterations**: The difference between the 5,000 simulations in the 26-27 script and the 25,000 in the 25-26 script should be explained (likely a trade-off for performance vs. granularity).
- **"Rating Deviation" (RD)**: This term should be defined for a non-technical audience as a measure of "rating uncertainty" or "recent activity level."

---

## 3. Proposed Documentation Updates

### Updated Root `README.md` (Features & Algorithm)

*   **Monte Carlo Simulations**: Runs 5,000 simulations grouped by promoted team.
*   **Championship Promotion**: Randomly determines the 20th team between top Championship contenders (Southampton and Hull City).
*   **Excitement Score**: A simplified metric based on the points gap between 1st and 2nd place.
*   **Outputs**: Provides Team Statistics (Avg Pts, Title%, CL%, Releg%) and points ranges for title winners.

### Updated `sportsanalysis/premier-league/README.md` (Corrected References)

*   **Elo Ratings**: Base Elo scores (Lines 80-100).
*   **Current Table**: Mid-season statistics (Lines 128-153).
*   **Fixtures**: Remaining match list (Lines 155-179).
*   **Match Engine**: Uses exponential XG scaling based on Elo differences to determine scoring probabilities.
*   **Elo Updates**: Incorporates Rating Deviation (RD) to adjust the K-factor, making ratings more reactive for teams with high uncertainty.
