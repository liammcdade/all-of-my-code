# Documentation Audit Report: Premier League Simulations

## 1. Mismatches

### 2025-26 Season Simulation (`25-26-season.py`)

*   **Line Number Inaccuracies**: The `sportsanalysis/premier-league/README.md` contains outdated line number references for almost every section:
    *   **Elo Ratings**: Documentation cites lines 8-28; actual code is at lines 80-100.
    *   **Current Table**: Documentation cites lines 54-76; actual code is at lines 128-153.
    *   **Fixtures**: Documentation cites lines 78-106; actual code is at lines 155-188.
    *   **European Elos**: Documentation cites lines 109-130; actual code is at lines 190-210.
    *   **Simulation Components**: Documentation cites lines 187-651; actual simulation logic for European competitions is at lines 470-494 and 710-740.
*   **Expected Goals (XG) Formula**:
    *   **Documentation**: Describes logistic scaling: `home_xg = 0.7 + 1.8 / (1 + exp(-diff/400))`.
    *   **Code**: Implements exponential scaling in `get_expected_goals` (line 244): `home_lambda = home_base * math.exp(diff / 800)`.
*   **European Competition Structure**:
    *   **Documentation**: Describes two-leg ties, semi-finals, and aggregate winners.
    *   **Code**: The European simulation (`cl_simulate_final`, etc.) only performs a single-match final simulation between hardcoded teams (e.g., lines 713-736). The complex tournament structure described is absent from the actual execution loop.
*   **Rating Deviation (RD) Usage**:
    *   **Documentation**: States "RD is not actively used in match simulations."
    *   **Code**: The `update_elo` function (line 560) explicitly uses `rd_arr` to calculate `g_val` and adjust the K-factor.
*   **European Qualification Tracking**:
    *   **Documentation**: Mentions tracking probability of "8+ teams".
    *   **Code**: Line 818 tracks `eight_european` if `len(european_teams) >= 9`.

### 2026-27 Season Simulation (`26-27-season.py`)

*   **Simulation Count**:
    *   **Documentation**: Claims to run 10,000 simulations.
    *   **Code**: `NUM_SIMS` is set to 5,000 (line 181).
*   **Championship Promotion Logic**:
    *   **Documentation**: "Simulates Championship playoffs to determine promotion."
    *   **Code**: Uses a 50/50 coin flip between Southampton and Hull City (line 194).
*   **Missing Algorithm Features**:
    *   **Documentation**: Section 1 (Power Ratings) claims Elo ratings are adjusted for Form, Injuries, and WDL rates.
    *   **Code**: These adjustments are completely missing from the match simulation logic in `run_simulation_vectorized` (line 107). Ratings are used as-is.
*   **Missing Output Features**:
    *   **Documentation**: Lists "Match Probabilities", "Extreme Match Probabilities", and "Team Fixture Probabilities" as generated outputs.
    *   **Code**: These statistics are not calculated or displayed in the 26-27 script.
*   **European Qualification Logic**:
    *   **Documentation**: Mentions Conference League (6th place).
    *   **Code**: Only tracks Top 4 (Champions League) and 5th place (Europa League) (lines 208-213).

---

## 2. Suggested Clarifications

*   **Jargon Definition**: Terms like **Elo**, **RD** (Rating Deviation), **XG** (Expected Goals), and **K-factor** are used without explanation. For a general audience, a brief glossary or "Algorithm Context" section would improve understanding.
*   **Numba/Vectorization**: The 2026-27 documentation doesn't mention that the simulation is vectorized using `numba.jit`, which is a significant technical feature of that script compared to the 2025-26 version.
*   **Excitement Score**: The formula for "Excitement Score" is described vaguely in the docs. Clarifying that it's a weighted measure of contenders in the title, Top 4, and relegation races (as seen in `calculate_excitement_score` at line 610 of the 25-26 script) would be beneficial.

---

## 3. Proposed Documentation Updates

### Updated Algorithm Overview (2026-27 README.md)

```markdown
### 1. Power Ratings
Uses base ELO ratings for all 18 returning teams plus one promoted team (randomly selected from Southampton or Hull City).

### 2. Match Simulation
Uses a vectorized Poisson model optimized with Numba JIT:
- Home advantage: +33.8 Elo points.
- Expected goals: Derived from Elo difference via logistic scaling.
- Dynamic Elo: Ratings update mid-simulation based on match results (K=25).

### 3. European Qualification
- Champions League: Top 4 teams.
- Europa League: 5th place.
- Relegation: Bottom 3 teams.
```

### Corrected Line References (2025-26 README.md)

*   **Elo Ratings**: lines 80-100.
*   **Current Table**: lines 128-153.
*   **Fixtures**: lines 155-188.
*   **European Elos**: lines 190-210.
*   **Match Engine**: lines 443-480.
*   **Monte Carlo Loop**: lines 748-830.

---

## 4. Coding Standard Violations (`instructions.md`)

*   **Rule 4 (Function Size)**: `assign_europe` (152 lines) and `main` (91 lines) in `25-26-season.py` exceed the 60-line limit.
*   **Rule 9 (Giant Datasets)**: Both scripts embed large Elo and fixture dictionaries directly in the code (e.g., lines 80-204 in `25-26-season.py`).
*   **Rule 13 (Separate Calculation From Display)**: Both scripts mix statistics calculation with print statements in the final reporting blocks.
*   **Rule 16 (File Length)**: `25-26-season.py` (1046 lines) exceeds the 800-line hard limit.
