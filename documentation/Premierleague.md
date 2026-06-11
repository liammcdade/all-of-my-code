# Premier League Simulation Documentation Audit Report

**Auditor:** Jules (Senior Technical Writer & Software Documentation Auditor)
**Date:** May 22, 2024
**Scope:** Premier League 2025-26 & 2026-27 Simulations

## 1. Executive Summary
This audit evaluated the alignment between the Premier League simulation scripts and their respective documentation. Significant discrepancies were found in both seasons, ranging from incorrect line number references and simulation counts to missing algorithm implementations and league structure mismatches. The 2025-26 documentation is outdated regarding code structure, while the 2026-27 documentation lists several features that are not yet implemented in the current codebase.

---

## 2. 2026-27 Season Audit (Code vs. Root README.md)

### Mismatches
1. **Simulation Count**:
   - **README**: States 10,000 simulations are run.
   - **Code (Line 181)**: `NUM_SIMS` is set to 5,000.
2. **League Size and Structure**:
   - **README**: Describes a standard Premier League structure (implies 20 teams).
   - **Code (Lines 31-40, 134)**: Simulates a 19-team league (18 fixed teams + 1 promoted from a choice of two).
3. **Championship Promotion Logic**:
   - **README**: Claims a "Championship Playoff Simulation" is used.
   - **Code (Line 202)**: Uses a simple 50/50 `random.random() < 0.5` coin flip between Southampton and Hull City.
4. **Missing Algorithm Features**:
   - **README**: Lists adjustments for **Form**, **Injuries**, and **Win/Draw/Loss tendencies** in the Algorithm Overview.
   - **Code**: These features are completely absent from the 2026-27 script. The `TeamRegistry` and `run_simulation_vectorized` functions use only base Elo.
5. **Missing Output Features**:
   - **README**: Lists "Match Probabilities", "Extreme Match Probabilities", and "Team Fixture Probabilities" as generated outputs.
   - **Code**: These functions (present in the 25-26 version) have not been ported to the 26-27 vectorized script.
6. **Excitement Score Calculation**:
   - **README**: Does not specify the formula.
   - **Code (Line 213)**: Calculates excitement as `(Leader Points - Second Place Points) / 10`, which differs significantly from the complex weighted formula used in the 25-26 season.

---

## 3. 2025-26 Season Audit (Code vs. sportsanalysis/premier-league/README.md)

### Mismatches
1. **Incorrect Line Number References**:
   The README references nearly all code blocks incorrectly due to script growth:
   - **Elo Ratings**: README says lines 8-28; **Actual**: Lines 80-100.
   - **Current Table**: README says lines 54-76; **Actual**: Lines 102-125.
   - **Fixtures**: README says lines 78-106; **Actual**: Lines 131-155.
   - **European Elos**: README says lines 109-130; **Actual**: Lines 157-178.
   - **Form Adjustments**: README says 396-417; **Actual**: 332-353.
2. **European Qualification Tracking**:
   - **README**: Mentions tracking probabilities for "8+ teams".
   - **Code (Line 768)**: Specifically tracks `if len(european_teams) >= 9: eight_european += 1`.
3. **Rating Deviation (RD) Usage**:
   - **README**: States "RD is not actively used in match simulations."
   - **Code (Lines 565, 590)**: RD is actively used to calculate the G-value for the expected score and to adjust the K-factor for Elo updates.
4. **Home Advantage Discrepancy**:
   - **README**: States a fixed home advantage of 33.8 Elo points.
   - **Code (Line 499)**: Randomizes home advantage between 50 and 70 for every simulation (`random.uniform(50, 70)`).
5. **XG Model Scaling**:
   - **README**: Describes "Logistic scaling" for XG.
   - **Code (Lines 246-247)**: Uses an exponential model `home_base * math.exp(diff / 800)`.

---

## 4. Code Quality & Consistency Audit (instructions.md Compliance)

### Violations
1. **Rule 16 (File Length)**: `25-26-season.py` is 1046 lines, exceeding the 800-line hard limit.
2. **Rule 9 (Embedded Datasets)**: Both scripts embed massive dictionaries for team data, Elo ratings, and fixtures directly in the logic.
3. **Rule 4 (Function Size)**:
   - `run_single_simulation` (25-26): ~76 lines (Max 60).
   - `main` (26-27): ~89 lines (Max 60).
4. **Rule 13 (Separation of Calculation and Display)**: The 25-26 script mixes complex statistical calculations with print statements throughout the final 300 lines of the file.
5. **Rule 15 (Dataclasses)**: While 25-26 uses dataclasses for some structures, 26-27 uses raw dictionaries for simulation results.

---

## 5. Suggested Clarifications
1. **European Competition Sim**: Clarify that for the PL Monte Carlo loop, European winners are sampled from pre-computed probabilities to ensure performance, rather than simulated in full during every iteration.
2. **Excitement Score**: Define what a "10" represents. Is it a points gap or a qualitative measure of tension?
3. **Promotion Logic**: Clarify if the 19-team simulation in 26-27 is a temporary development state or a specific "what-if" scenario.

---

## 6. Proposed Documentation Updates (Examples)

### Updated Algorithm Overview (2026-27 README)
> ### 1. Power Ratings
> Uses base ELO ratings for 18 core teams and one of two potential promoted teams (Southampton or Hull City), determined by a 50/50 probability at the start of each simulation. *Note: Advanced adjustments for form and injuries are currently only available in the 2025-26 simulation.*

### Corrected References (2025-26 README)
> - **Elo Ratings**: Base Elo scores for Premier League teams (lines 80-100).
> - **Current Table**: Mid-season statistics including points and goal difference (lines 102-125).
> - **Fixtures**: List of the 20 remaining matches (lines 131-155).
