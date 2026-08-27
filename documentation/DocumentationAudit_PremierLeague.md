# Documentation Audit Report: Premier League Simulations

## 1. Mismatches

### 2025-26 Season Simulation (`sportsanalysis/premier-league/25-26-season.py`)

| Type | Description | Location in Docs | Location in Code |
| :--- | :--- | :--- | :--- |
| **Line Numbers** | Elo ratings cited at 8-28. | Data Inputs | Line 80 |
| **Line Numbers** | Rating Deviation (RD) cited at 31-52. | Data Inputs | Line 105 |
| **Line Numbers** | Current table cited at 54-76. | Data Inputs | Line 128 |
| **Line Numbers** | Fixtures cited at 78-106. | Data Inputs | Line 155 |
| **Line Numbers** | European Elos cited at 109-130. | Data Inputs | Lines 190, 197, 204 |
| **Logic** | Rating Deviation (RD) is "not actively used". | Data Inputs | Line 567 (used in `update_elo`) |
| **Logic** | Expected Goals (XG) uses "Logistic scaling". | Match Engine | Line 246 (uses exponential `exp(diff/800)`) |
| **Parameter** | Probability for "8+ European teams". | Statistics | Line 967 (tracks "9 or more teams") |
| **Side Effect** | Deletes `__pycache__` directory silently. | Not mentioned | End of script (implicit in imports/behavior) |

### 2026-27 Season Simulation (`26-27-season.py` / Root `README.md`)

| Type | Description | Location in Docs | Location in Code |
| :--- | :--- | :--- | :--- |
| **Feature** | Form, Injuries, and WDL bias adjustments. | Algorithm Overview | Absent (Placeholder args in `add_team` only) |
| **Feature** | Championship Playoff Simulation. | Algorithm Overview | Line 194 (50/50 coin flip) |
| **Feature** | Match, Extreme, and Team Fixture Probabilities. | Output | Absent from script output |
| **Parameter** | Number of simulations: 10,000. | Monte Carlo / Usage | Line 181 (set to 5,000) |
| **Logic** | Excitement Score calculation. | Algorithm Overview | Line 213 (`leader_pts - second_pts` / 10) |
| **Undocumented** | `TeamRegistry` class for state management. | Not mentioned | Line 45 |
| **Undocumented** | `run_simulation_vectorized` using Numba. | Not mentioned | Line 107 |

---

## 2. Clarifications

*   **Jargon: "Elo Ratings"** - While common in sports analytics, the documentation should briefly define it as a relative strength rating where the difference between two teams predicts the match outcome.
*   **Jargon: "Poisson Goal Modeling"** - Explain that this treats goal scoring as a series of independent events happening at a constant average rate, which is standard for low-scoring sports like football.
*   **Knowledge Gap: "K-Factor"** - Mention that this determines how much a team's rating changes after a single match (sensitivity).
*   **Knowledge Gap: "Numba JIT"** - Explain that Numba translates Python functions into optimized machine code at runtime, significantly speeding up the 25,000+ simulations.

---

## 3. Proposed Documentation Updates

### Root `README.md` (2026-27)

*   **Update Simulation Count**: Change 10,000 to 5,000 to match `NUM_SIMS` in code.
*   **Revise Features**: Remove mentions of Form, Injury, and WDL bias for the 26-27 version, or label them as "Planned".
*   **Clarify Playoff Logic**: Update "Championship Playoff Simulation" to "Simplified Promotion Logic (Southampton vs Hull City coin flip)".
*   **Remove Unimplemented Outputs**: Remove "Match Probabilities", "Extreme Match Probabilities", and "Team Fixture Probabilities" from the Output section.

### `sportsanalysis/premier-league/README.md` (2025-26)

*   **Fix Line Numbers**: Update all line number references to match the current 1046-line script (e.g., Elo ratings at 80-100, Fixtures at 155-188).
*   **Correct Model Logic**: Update XG description from "Logistic scaling" to "Exponential Elo-based lambda: `base * exp(diff/800)`".
*   **Acknowledge RD Usage**: Update the RD section to state: "RD is used to scale the K-factor during Elo updates, reducing volatility for well-established ratings."
*   **Correct European Tracking**: Change "8+ teams" to "9+ teams" to align with the code's `eight_european` logic (which checks `>= 9`).
