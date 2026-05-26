# Documentation Audit: Premier League Simulation Project

This audit compares the documentation (`README.md` files) with the actual implementation in `25-26-season.py` and `26-27-season.py`.

## I. Mismatches and Discrepancies

### 1. Premier League 2025-26 Season (`sportsanalysis/premier-league/README.md`)

*   **Line Number Obsolescence:** Nearly all line references in the README are incorrect due to script growth/refactoring.
    *   **Elo Ratings:** README cites lines 8-28; Code starts at **line 80**.
    *   **Rating Deviations (RD):** README cites lines 31-52; Code starts at **line 105**.
    *   **Current Table:** README cites lines 54-76; Code starts at **line 128**.
    *   **Fixtures:** README cites lines 78-106; Code starts at **line 155**.
    *   **European Elos:** README cites lines 109-130; Code starts at **line 190**.
    *   **Form Adjustments:** README cites lines 396-417; Code starts at **line 334**.
    *   **WDL Rates:** README cites lines 420-441; Code starts at **line 357**.
    *   **Injury Penalties:** README cites lines 444-466; Code starts at **line 380**.
    *   **Home Advantage Parameter:** README cites line 469; Code constant is at **line 43**.
*   **XG Model Conflict:** README (line 125) claims the model uses **Logistic scaling**. The code at line 246 implements an **Exponential model** (`math.exp(diff / 800)`). Note: The 26-27 script *does* use logistic scaling, suggesting a copy-paste error in the documentation.
*   **Home Advantage Values:** README (line 45) states a fixed **33.8 Elo points**. The code (line 43) sets a base of **60**, which is then randomized between **50 and 70** per simulation (line 488).
*   **Rating Deviation (RD) Usage:** README (line 33) states "RD is not actively used in match simulations." However, the code uses RD in the `update_elo` function (line 564) to dynamically adjust the K-factor: `k_h = K_FACTOR_BASE / (1 + rd_arr[h_idx]/100)`.
*   **European Tournament Structure:** README describes a full knockout structure (Quarter-finals, etc.) for European competitions. The code (lines 665-690) simulates a **single-match final** between two specific teams for each competition.
*   **Statistical Thresholds:** README (line 166) mentions tracking "8+ European teams," but the output (line 757) and logic (line 704) report on **9+ teams**.
*   **Missing Output Features:** The documentation fails to mention the "Probability that all remaining games are draws" (line 760) and the "Probability that 6th place qualifies for Champions League" (line 763).

### 2. Premier League 2026-27 Season (Root `README.md`)

*   **Simulation Count:** README claims **10,000** simulations. The code (`26-27-season.py` line 181) is hardcoded to **5,000**.
*   **Promotion Logic:** README claims a "Championship Playoff Simulation." The code (line 194) implements a **50/50 coin flip** between Southampton and Hull City.
*   **Ghost Features:** Several features listed in the README are missing from the 26-27 implementation (though present in the 25-26 version):
    *   **Pre-season Match Probabilities:** Claimed in "Features," but no such output is generated.
    *   **Extreme Match Probabilities:** Claimed in "Output," but absent from the script.
    *   **Elo Adjustments:** README claims adjustments for form, injuries, and WDL bias. The 26-27 script uses raw Elo only.
*   **League Size and Schedule:** The documentation implies a standard 20-team league. The code simulates a **19-team league** (18 fixed + 1 promoted), resulting in **36 matches** per team (line 154) instead of 38.
*   **European Qualification Assignments:** README claims 6th place qualifies for Conference League. The code (lines 204-212) only assigns CL (Top 4) and Europa (5th).

---

## II. Specific Review Criteria

*   **Every parameter described?** No. `update_elo` uses RD which is described as unused. `simulate_match` in 26-27 uses several constants (TEMPO_BASE, SHARED_GOAL_BASE) not mentioned in docs.
*   **Examples runnable?** Yes, the usage commands work, provided dependencies (numpy, numba) are installed.
*   **Features mismatch?** Yes, major mismatches in promotion logic, league size (26-27), and tournament structure (25-26).
*   **Clear language?** Generally yes, but "Bivariate Poisson with shared lambda" (25-26) and "Vectorized simulation" (26-27) might be jargon-heavy for non-technical users.
*   **Assumed knowledge?** Assumes users know how to interpret Elo ratings and standard European qualification spots (CL/EL/Conf).

---

## III. Suggested Clarifications

1.  **Dynamic Home Advantage:** Explain that Home Advantage is not a static constant but a range-based randomization in the 25-26 model to simulate match-to-match variance.
2.  **Promotion Modeling:** In the 26-27 season, clarify that the league size is 19 teams to focus on the impact of the final promoted team without simulating the entire Championship.
3.  **K-Factor and RD:** Clarify that RD *is* used to scale the K-factor, meaning teams with higher uncertainty (RD) see larger Elo swings after matches.

---

## IV. Proposed Updated Documentation (Excerpts)

### For `sportsanalysis/premier-league/README.md` (25-26)
> **Match Engine**
> - **Expected Goals (XG):** Home and Away XG are calculated using an exponential Elo difference model: `base_xg * exp(diff / 800)`.
> - **Home Advantage:** A dynamic factor (randomized 50-70 Elo pts) is added to the home team's rating per simulation to account for variance.
> - **Elo Updates:** Post-match Elo shifts are scaled by the team's Rating Deviation (RD), with less certain teams experiencing higher volatility.

### For root `README.md` (26-27)
> **Promotion Logic**
> To model promotion uncertainty, each simulation iteration randomly selects between Southampton and Hull City (50% probability each) as the 19th team in the league.
>
> **Known Limitations**
> This version simulates a 19-team league (36 matches/season) using raw Elo ratings. Dynamic adjustments for form and injuries are currently disabled.
