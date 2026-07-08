# Documentation Audit Report: Premier League Simulations

**Auditor:** Senior Technical Writer / Software Documentation Auditor
**Date:** October 2023
**Project:** Premier League Season Simulations (2025-26 and 2026-27)

---

## 1. Executive Summary
This audit identifies significant discrepancies between the implementation of the Premier League simulation scripts and their respective documentation (README files). The 2025-26 documentation suffers from outdated line references and mismatched mathematical models, while the 2026-27 documentation describes several advanced features and algorithms that are entirely absent from the current code.

---

## 2. Premier League 2025-26 Season (`25-26-season.py`)

### Mismatches
1.  **Line Number Inaccuracies**:
    *   The `README.md` references Elo ratings at lines 8-28 (actual: line 80), current table at 54-76 (actual: line 128), and fixtures at 78-106 (actual: line 155).
2.  **Home Advantage Discrepancy**:
    *   **Documentation**: States home advantage is fixed at 33.8 Elo points.
    *   **Code**: `HOME_ADVANTAGE_ELO` is randomized between 50 and 70 in the `run_single_simulation` loop (line 488).
3.  **Expected Goals (XG) Model**:
    *   **Documentation**: Describes a logistic scaling model for XG.
    *   **Code**: `get_expected_goals` uses an exponential model `exp(diff / 800)` (lines 246-247).
4.  **WDL Rates Redundancy**:
    *   **Documentation**: Lists WDL rates as a data input.
    *   **Code**: The `wdl_rates` dictionary (line 355) is defined but never accessed or used by the simulation engine.
5.  **Rating Deviation (RD) Usage**:
    *   **Documentation**: Claims RD is "not actively used".
    *   **Code**: RD is used in `update_elo` (line 560) to calculate the `g_val` and K-factor.
6.  **FA Cup Simulation**:
    *   **Documentation**: Describes a "simple Elo-based knockout".
    *   **Code**: `simulate_full_fa_cup_tournament` (line 240) only simulates a single match between hardcoded teams (Chelsea vs Man City).

### Suggested Clarifications
*   **Jargon**: Terms like "Bivariate Poisson" and "logistic scaling" should be briefly explained or linked to resources if the audience includes non-technical users.
*   **RD Usage**: Clarify that while RD doesn't affect the goal model directly, it *does* affect the post-match Elo update speed.

---

## 3. Premier League 2026-27 Season (`26-27-season.py`)

### Mismatches
1.  **Simulation Count**:
    *   **Documentation**: States 10,000 simulations are run.
    *   **Code**: `NUM_SIMS` is set to 5,000 (line 181).
2.  **Unimplemented Features**:
    *   The following output tables described in the root `README.md` are not produced by the script:
        *   **Match Probabilities** (per fixture)
        *   **Extreme Match Probabilities**
        *   **Team Fixture Probabilities**
3.  **Algorithm Discrepancies**:
    *   **Documentation**: Claims Elo is adjusted for Form, Injuries, and WDL rates.
    *   **Code**: While `add_team` accepts these parameters (line 49), they are not stored or utilized in the simulation logic.
4.  **Championship Promotion**:
    *   **Documentation**: Describes a "Championship Playoff Simulation".
    *   **Code**: Uses a 50/50 coin flip between Southampton and Hull City (line 194).
5.  **European Qualification**:
    *   **Documentation**: Mentions 6th place qualifies for the Conference League.
    *   **Code**: Only assigns Champions League (Top 4) and Europa League (5th). Conference League is missing from the assignment logic.
6.  **Excitement Score**:
    *   **Documentation**: Implies a complex metric based on contenders.
    *   **Code**: Calculated simply as `(leader_pts - second_pts) / 10` (lines 186, 213).

### Suggested Clarifications
*   **Registry Pattern**: The `TeamRegistry` class is a core component but is not mentioned in the documentation.
*   **Vectorization**: The use of Numba and NumPy vectorization should be highlighted as a key performance feature.

---

## 4. Coding Standards Compliance (Rule Audit)

1.  **Rule 4 (Function Size)**: `main()` in `26-27-season.py` and several simulation functions in `25-26-season.py` exceed the 60-line limit.
2.  **Rule 9 (Giant Dictionaries)**: Both scripts embed large Elo and fixture datasets directly (e.g., lines 80-204 in `25-26-season.py`).
3.  **Rule 12 (Main Loop)**: The simulation loops in both scripts are overly large and handle orchestration, calculation, and statistics accumulation.
4.  **Rule 16 (File Length)**: `25-26-season.py` is 1046 lines, exceeding the 800-line maximum.

---

## 5. Proposed Documentation Updates

### Root README.md (2026-27)
*   Update `NUM_SIMS` to 5,000 to match code.
*   Remove unimplemented "Match Probabilities" and "Extreme Match Probabilities" from the Features and Output sections.
*   Clarify that Championship promotion is currently a simplified 50/50 selection.
*   Adjust "European Qualification" to match the Top 5 logic currently implemented.

### 25-26 README.md
*   Remove specific line number references as they are brittle and currently incorrect.
*   Correct the Home Advantage value description to reflect the randomized 50-70 range.
*   Update the XG model description to "Exponential scaling".
*   Clarify that the FA Cup simulation is currently limited to the final match.
