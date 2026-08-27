# Documentation Audit Report: Premier League Simulation

## 1. 2025-26 Season Simulation Audit

### Mismatches Identified

| Feature | Documentation (README.md) | Actual Code Implementation | Status |
| :--- | :--- | :--- | :--- |
| **Line References** | Multiple outdated references (e.g., Elo at 8-28, Table at 54-76). | Lines have shifted (Elo ~80, Table ~104, Fixtures ~134). | **Mismatch** |
| **XG Model** | Logistic scaling: `0.7 + 1.8 / (1 + exp(-diff/400))` | Exponential scaling: `base * exp(diff / 800)` (Lines 256-257) | **Mismatch** |
| **Euro Structure** | Full knockout structure (Semi-finals, Two-leg ties). | Single-match Final only between hardcoded teams (Lines 699-715). | **Mismatch** |
| **Euro Team Prob** | Probability for "8+ European teams". | Script tracks "at least 9 teams" (`len >= 9`) (Line 775). | **Mismatch** |
| **Home Advantage** | 33.8 Elo points (line 469). | Randomized between 50-70 (Line 445) or fixed 60 (Line 41). | **Mismatch** |

### Suggested Clarifications
*   **European Simulation:** The "European simulations" mentioned in the README are currently simplified to finals only to avoid user confusion when looking for tournament brackets in the code.
*   **Home Advantage:** Specify that the home advantage is dynamic (randomized per simulation loop) rather than a static constant.

### Proposed Documentation Updates (for `sportsanalysis/premier-league/README.md`)

*   **Update Data Inputs section:**
    - Elo Ratings: lines 80-100
    - Current Table: lines 104-127
    - Fixtures: lines 134-160
    - European Elos: lines 162-184
*   **Update Match Engine section:**
    - Change XG description to: `home_xg = home_base * exp(diff / 800)`
*   **Update Statistics section:**
    - Change "8+ European teams" to "9+ European teams".
*   **Update European Competitions section:**
    - Acknowledge that the simulation currently focuses on the pre-sampled Final match outcomes.

## 2. 2026-27 Season Simulation Audit

### Mismatches Identified

| Feature | Documentation (Root README.md) | Actual Code Implementation | Status |
| :--- | :--- | :--- | :--- |
| **League Size** | Implied 20-team standard PL structure. | 19 teams per sim (18 fixed + 1 alternating promoted team). | **Mismatch** |
| **Promotion Logic** | "Championship playoff simulation". | 50/50 random selection (Southampton vs Hull). | **Mismatch** |
| **ELO Adjustments** | Mentions Form, Injuries, and WDL bias. | Uses base Elo only; modifiers not implemented in 26-27 script. | **Mismatch** |
| **European Slots** | Tracks CL, Europa, and Conference League. | Script logic only tracks Top 4 (CL) and 5th (EL). | **Mismatch** |
| **Side Effects** | Not mentioned. | Deletes `__pycache__` directory on completion (Line 262). | **Missing** |

### Suggested Clarifications
*   **Team Count Clarification:** Each simulation iteration uses 19 teams (18 fixed + 1 promoted). However, because the promoted team is chosen randomly between two candidates, the *aggregated results* will list 20 teams total.
*   **Alpha Status:** The script should be clearly labeled as a simplified or "Alpha" version due to the lack of injury/form modifiers and the 19-team match matrix.
*   **Cleanup:** The script automatically removes `__pycache__` upon finishing to keep the directory clean.

### Proposed Documentation Updates (for Root `README.md`)

*   **Update Features section:**
    - Correct league size to "19 teams per iteration".
    - Revise "Championship Playoff" to "Promoted Team Selection (50/50)".
    - Remove unimplemented Elo adjustments (Form/Injuries/WDL bias).
*   **Update Algorithm Overview:**
    - Simplify European qualification to Top 4 (CL) and 5th (Europa).
*   **Update Usage:**
    - Mention that the script performs automated cleanup of Python cache files.

## 3. General Documentation Quality Audit

### Parameters, Return Values, and Side Effects
*   **25-26 Season:** The documentation mentions "Rating Deviation (RD)" but correctly notes it is not actively used. However, it lacks a formal description of return values for helper functions like `get_expected_goals`.
*   **26-27 Season:** Side effects such as the automatic deletion of `__pycache__` are missing from the documentation. Internal constants like `SHARED_GOAL_BASE` are not explained.

### Runnable Code Examples
*   The execution commands provided (`python sportsanalysis/premier-league/25-26-season.py`) are correct but assume the user has installed specific dependencies (`numba`, `numpy`, `tqdm`) which are not explicitly listed in the 25-26 README (though they are in the root `requirements.txt`).

### Clarity and Jargon
*   The term "Bivariate Poisson" is used in the 25-26 README. While technically accurate for the model's intent, it may be jargon for non-technical users. The 26-27 README is more accessible but sacrifices detail on the actual math (e.g., sigmoid scaling for XG).

### Assumed Knowledge
*   The documentation assumes the user knows how to navigate to the correct directory or add it to their `PYTHONPATH`. Running the scripts from the root directory may cause issues if they attempt to write output to relative paths (though current versions primarily print to console).
