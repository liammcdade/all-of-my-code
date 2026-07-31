# Documentation Audit Report: Premier League Simulation Scripts

## Mismatches

### 1. 2025-26 Season Simulation (`25-26-season.py` vs `sportsanalysis/premier-league/README.md`)

*   **Line Reference Inaccuracies**:
    *   The README cites **Elo Ratings** at lines 8-28. In the script, they are located at lines 80-100.
    *   The README cites **Current Table** at lines 54-76. In the script, it is at lines 128-153.
    *   The README cites **Fixtures** at lines 78-106. In the script, they are at lines 155-188.
    *   The README cites **European Competition logic** starting at line 187. In the script, it begins around line 437.
*   **Simulation Parameters**:
    *   The README states **Home Advantage** is 33.8 Elo points. The script uses a randomized value between 50 and 70 (line 484).
    *   The README mentions **Poisson lambda** for European goals as `1.4 + diff*0.001`. The script uses `exp(diff/800)` scaling in `get_expected_goals` (line 246).
*   **Feature Discrepancies**:
    *   The README describes **Excitement Score** calculation based on title, top 4, and relegation contenders. The script calculates it using this logic in `calculate_excitement_score` (lines 566-602).
    *   The README claims **RD** is "not actively used," but the `update_elo` function (line 396) incorporates it into the K-factor calculation.

### 2. 2026-27 Season Simulation (`26-27-season.py` vs root `README.md`)

*   **Simulation Counts**: The README states 10,000 simulations. The script is hardcoded for 5,000 simulations (`NUM_SIMS = 5000`, line 181).
*   **Missing Features**:
    *   **Form, Injury, and WDL Adjustments**: The README claims Elo ratings are adjusted for these factors. However, the `26-27-season.py` script uses base Elo ratings without any form or injury modifiers during the match simulation.
    *   **Output Stats**: The README lists "Match Probabilities," "Extreme Match Probabilities," and "Team Fixture Probabilities" as outputs. These features are implemented in `25-26-season.py` but are entirely absent from `26-27-season.py`.
*   **Logic Implementation**:
    *   **Championship Promotion**: The README describes a "Championship Playoff Simulation." The code implements a simple 50/50 coin flip between Southampton and Hull City (line 194).
    *   **European Qualification**: The README mentions Conference League (6th place). The script only tracks Champions League (Top 4) and Europa League (5th place) in its assignment logic (lines 208-212).
*   **Excitement Score**: The README mentions an "average excitement score." The code calculates this as `(leader_pts - second_pts) / 10` (line 275), which differs significantly from the complex calculation described for the 2025-26 season.

## Suggested Clarifications

*   **Audience Knowledge**: The documentation assumes familiarity with **Elo rating scales** (specifically the 400-point scale) and **Poisson distributions**. Adding a brief glossary or links to resources on these topics would help non-technical users.
*   **Environment Setup**: The scripts require `numba` and `tqdm`, but `tqdm` is missing from the root `requirements.txt`. This should be added to ensure the "Installation" steps are runnable.
*   **Directory Context**: The scripts contain side effects (like deleting `__pycache__`) that assume execution from specific paths or have impacts on the development environment.

## Proposed Documentation Updates

### Root README.md (2026-27)
*   **Update Simulation Count**: Change "10,000 simulations" to "5,000 simulations" or make the script parameter more visible.
*   **Clarify Promotion Logic**: Replace "Simulates Championship playoffs" with "Randomly selects one promoted team from the Championship favorites (Southampton or Hull City)."
*   **Remove Unimplemented Features**: Delete references to form/injury adjustments and fixture probability outputs unless they are ported from the 25-26 script.

### sportsanalysis/premier-league/README.md (2025-26)
*   **Correct Line Numbers**: Update all line number references to match the current version of `25-26-season.py`.
*   **Update Model Parameters**: Reflect that Home Advantage is a randomized range (50-70) rather than a fixed constant.
*   **Clarify RD Usage**: Note that while RD is not used in the match simulation engine, it is used in the post-match Elo update logic.
