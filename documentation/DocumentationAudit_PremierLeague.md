# Documentation Audit Report: Premier League Simulation Projects

**Auditor:** Jules, Senior Technical Writer & Software Documentation Auditor
**Date:** June 2024
**Scope:** `sportsanalysis/premier-league/` (2025-26 and 2026-27 simulations)

---

## 1. Mismatches and Inconsistencies

### A. Premier League 2026-27 Season (`26-27-season.py` vs Root `README.md`)

| Feature | Documentation Claim | Actual Code Implementation | Reference |
| :--- | :--- | :--- | :--- |
| **Simulation Count** | "10,000 simulations" | `NUM_SIMS = 5000` | Line 181 |
| **Championship Promotion** | "Simulates Championship playoffs" | 50/50 coin flip between Southampton and Hull City | Line 194 |
| **Elo Adjustments** | Form, Injuries, and WDL bias adjustments | Parameters accepted in `add_team` but **unused** in simulation logic | Lines 49, 72, 107 |
| **Output Features** | Match, Extreme, and Fixture Probabilities | **Not implemented**. Output is limited to Team Stats and Champion Pts | Main loop |
| **Qualification** | CL (4), EL (5), Conf (6) | Only CL (Top 4) and EL (5th) are tracked and displayed | Lines 209-211 |
| **Algorithm** | "Bivariate Poisson" (suggested by context) | Uses independent Poisson for home/away with a shared goal base | Line 90 |

### B. Premier League 2025-26 Season (`25-26-season.py` vs `sportsanalysis/premier-league/README.md`)

| Feature | Documentation Claim | Actual Code Implementation | Reference |
| :--- | :--- | :--- | :--- |
| **Line Numbers** | Multiple references (e.g., Elo at 8-28) | **Every single line reference is incorrect** | Entire README |
| **FA Cup** | "Full FA Cup tournament" | Simulates only the final (Chelsea vs Man City) | Line 240 |
| **WDL Rates** | Used as "observed rates" input | Defined in `wdl_rates` but **completely unused** in match engine | Line 355, 443 |
| **Goal Model** | "Logistic scaling" | Exponential scaling: `home_base * math.exp(diff / 800)` | Line 244 |
| **Rating Deviation** | "RD is not actively used" | Used in `update_elo` to modify K-factor and G-value | Line 560 |
| **European Format** | Detailed tournament structure | Implementation is limited to single-match finals for CL/EL/Conf | Lines 717-740 |

---

## 2. Suggested Clarifications

*   **Elo Rating System:** The documentation assumes the reader understands Elo. A brief note explaining that Elo is a relative strength measure (where a difference of 400 points represents a 10x difference in expected score) would help.
*   **Poisson Modeling:** Clarify that "Poisson goal modeling" means the simulation treats goal scoring as a random process where the *average* rate is determined by team strength, but individual match scores vary.
*   **Monte Carlo Method:** Explain that the "25,000 simulations" represent 25,000 different "parallel universes" of the season, and the percentages (e.g., Title%) represent the frequency of that outcome across those universes.
*   **Numba/JIT:** For the technical audience, clarify that Numba is used to compile Python code to machine code for high-performance execution, which is why the simulation of thousands of seasons takes seconds rather than minutes.

---

## 3. Proposed Updated Documentation (Drafts)

### Updated `sportsanalysis/premier-league/README.md` (2025-26) Snippet:
> ### Algorithm Overview
> - **Match Engine:** Uses a custom Poisson model where expected goals are calculated via exponential scaling of Elo differences (`exp(diff/800)`).
> - **Elo Dynamics:** Ratings are dynamic; they update after every simulated match based on a K-factor adjusted by the team's Rating Deviation (RD).
> - **FA Cup:** Currently simulates the final match between Chelsea and Man City to determine the EL qualification spot.
> - **Tiebreakers:** League positions are determined by Points > Goal Difference > Goals For.

### Updated Root `README.md` (2026-27) Snippet:
> ### Usage & Output
> The simulation runs 5,000 iterations to determine league probabilities.
> **Note:** Current version focuses on core Elo-based match simulation. Form, injury, and fixture-specific probability outputs are planned for future updates and are not present in the current `26-27-season.py` script.
> **Promotion Logic:** Determines the 20th team via a randomized selection between Southampton and Hull City.

---

## 4. Code Runnability Verification
- **2026-27:** Confirmed runnable. Performance: ~3,000 sims/sec. Output verified for Team Statistics and Additional Statistics.
- **2025-26:** Confirmed runnable. Performance: ~15 sims/sec (more complex logic). Output verified for all listed statistics including European competition winners and match probabilities.
