# Documentation Audit Report: Premier League Simulations

**Auditor:** Jules, Senior Technical Writer & Software Documentation Auditor
**Date:** July 3, 2025
**Scope:**
- 2025-26 Premier League Simulation (`sportsanalysis/premier-league/25-26-season.py` & `sportsanalysis/premier-league/README.md`)
- 2026-27 Premier League Simulation (`sportsanalysis/premier-league/26-27-season.py` & root `README.md`)

---

## 1. Mismatches & Inconsistencies

### 2025-26 Season Simulation

| Feature / Component | Documentation Claim | Actual Code Implementation | Line Reference (Code) |
| :--- | :--- | :--- | :--- |
| **Line Number References** | Cites specific lines (e.g., Elo ratings at 8-28). | All line numbers in the README are obsolete. For example, Elo ratings are at 80, Table at 128, Fixtures at 155. | Various |
| **Expected Goals (XG) Model** | Logistic scaling: `0.7 + 1.8 / (1 + exp(-diff/400))` | Exponential scaling: `base * exp(diff / 800)` in the `get_expected_goals` function. | 246-247 |
| **FA Cup Implementation** | "Simple Elo-based knockout" or "Full tournament". | `simulate_full_fa_cup_tournament` only simulates a single match (Chelsea vs Man City). | 241-242 |
| **European Qualification** | Probabilities for "8+ European teams". | Tracks and reports the probability of "at least 9 European teams". | 774, 920 |
| **European Slots Logic** | Top 5 -> CL, 6th -> EL, etc. | `assign_top_positions` sets Top 5 to CL, 6th to EL, 7th to Conf. | 647-652 |
| **WDL Rates** | Used for variance/bias adjustments. | `wdl_rates` dictionary is defined but never called or used in logic. | 355-377 |
| **Rating Deviation (RD)** | "Not actively used in match simulations". | `update_elo` uses `rd_arr` to calculate `g_val` and adjust the K-factor. | 563-565, 588-589 |
| **Home Advantage** | 33.8 Elo points. | `HOME_ADVANTAGE_ELO` is 60 (base) and randomized between 50-70 per sim. | 43, 488 |
| **Side Effects** | None mentioned. | No script-level side effects found (earlier claim of pycache deletion was incorrect for this specific script). | N/A |

### 2026-27 Season Simulation

| Feature / Component | Documentation Claim | Actual Code Implementation | Line Reference (Code) |
| :--- | :--- | :--- | :--- |
| **Simulation Count** | 10,000 simulations. | `NUM_SIMS` is hardcoded to 5,000. | 181 |
| **Promotion Logic** | "Championship Playoff Simulation". | A 50/50 `random.random() < 0.5` coin flip between Southampton and Hull City. | 194 |
| **Excitement Score** | Complex contender-based metric. | Simple points difference: `(leader_pts - second_pts) / 10`. | 213, 240 |
| **Elo Adjustments** | Adjusts for form, injuries, and WDL. | `add_team` accepts `form` and `injury` arguments, but the vectorized engine only uses base Elo. | 49, 107-151 |
| **Output Features** | "Match Probabilities", "Extreme Match Probabilities", "Team Fixture Probabilities". | These outputs are not implemented; script only shows Team Stats and Points to Win. | 224-254 |
| **Side Effects** | None mentioned. | Deletes the `__pycache__` directory at the end of execution. | 252-254 |

---

## 2. Suggested Clarifications

- **ELO Scaling**: The READMEs mention a "400-scale Elo". It should be clarified for the audience that this is the logistic constant used for win probability calculation, not the range of the ratings themselves.
- **Vectorized Engine (26-27)**: The 2026-27 script uses a significantly different execution model (`run_simulation_vectorized` with `@numba.jit`) compared to 2025-26. This technical distinction explains why certain granular adjustments (form, injuries) are currently omitted in 26-27.
- **European Qualification**: The logic for "extra spots" in 2025-26 (lines 683-705) is complex (e.g., Aston Villa winning EL while 5th). A plain-English summary of these "special rules" would benefit the user.
- **Dependencies**: Both scripts require `numba` and `tqdm`, which are not standard library modules and may not be present in a base Python installation.

---

## 3. Proposed Documentation Updates

### For `sportsanalysis/premier-league/README.md` (2025-26)
- **Match Engine**: Update XG formula: "Uses exponential scaling where `expected_goals = base * exp(elo_diff / 800)`."
- **Line Numbers**: Conduct a full sweep to update line references (e.g., Elo Ratings -> Line 80, Current Table -> Line 128).
- **European Statistics**: Change "8+ teams" to "9+ teams" to align with the `len(european_teams) >= 9` check.
- **Elo System**: Clarify that Rating Deviation (RD) *is* used to dynamically adjust K-factors during the season simulation.

### For root `README.md` (2026-27)
- **Monte Carlo Simulations**: Update iterations to 5,000.
- **Championship Promotion**: Change "Simulates Championship playoffs" to "Randomly selects one of the top two Championship contenders for promotion."
- **Features & Output**: Remove references to "Match Probabilities" and "Fixture Probabilities" as they are missing from the current implementation.
- **Excitement Score**: Update definition: "Calculated as the final points gap between 1st and 2nd place, scaled to a 0-10 range."

---

## 4. Final Verification Notes
- **Runnability**: Both scripts were verified as runnable after installing `numpy`, `numba`, `tqdm`, and `rich`.
- **Side Effects**: The 2026-27 script's deletion of `__pycache__` is a silent side effect that should be documented as it may affect users who rely on cached bytecode for performance.
- **Code Examples**: Usage examples (`python sportsanalysis/premier-league/26-27-season.py`) are syntactically correct but assume the user has the required non-standard dependencies installed.
