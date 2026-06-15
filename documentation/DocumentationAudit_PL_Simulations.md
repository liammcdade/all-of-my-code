# Documentation Audit Report: Premier League Simulation Projects

**Auditor:** Jules, Senior Technical Writer & Software Documentation Auditor
**Date:** June 15, 2024
**Scope:**
- 2025-26 Season Simulation (`sportsanalysis/premier-league/25-26-season.py` & its local README)
- 2026-27 Season Simulation (`sportsanalysis/premier-league/26-27-season.py` & root README.md)

---

## 1. Premier League 2026-27 Season Simulation (Root README.md)

### Mismatches
| Feature | Documentation (README.md) | Code Implementation (`26-27-season.py`) |
| :--- | :--- | :--- |
| **Simulation Iterations** | "Runs 10,000 simulations" | Hardcoded to `5000` (Line 183) |
| **League Composition** | Implies 20 teams (Standard PL) | Simulates a **19-team league** (18 fixed + 1 promoted) |
| **Promotion Logic** | "Simulates Championship playoffs" | Simplified **50/50 coin flip** (Line 186) |
| **Match Probabilities** | Listed as a primary output | **Not implemented**. Script only outputs Team Stats and summary data. |
| **Form/Injury Logic** | "Adjusted for Form and Injuries" | The match engine (`run_simulation_vectorized`) uses base ELO ratings only; form/injury arrays are never passed or used. |
| **Side Effects** | None mentioned | **Deletes `__pycache__`** directory on completion (Line 294). |

### Suggested Clarifications
- **Jargon:** Terms like "Monte Carlo simulation" and "Poisson goal modeling" are used without explanation. A brief sentence explaining that these represent "randomized trials" and "statistical scoring patterns" would aid non-technical users.
- **Algorithm Overview:** Section 1 claims ELO is adjusted for form/injuries, but the implementation lacks the variables or logic to apply these. This should be removed until implemented.
- **Excitement Score:** The "Average excitement score" in the output is not explained. Users won't know it's a simple calculation of the points gap between 1st and 2nd place divided by 10.

### Proposed Documentation Updates (README.md)
```markdown
## Features
- **Monte Carlo Simulations**: Runs 5,000 randomized iterations per promoted team scenario.
- **Dynamic Promotion**: Accounts for variable league composition by alternating between potential promoted teams (Southampton/Hull City).
- **High-Performance Engine**: Utilizes Numba JIT-acceleration for vectorized match simulation.

## Algorithm Overview
### 1. Power Ratings
Uses base ELO ratings for all 18 fixed Premier League teams and potential Championship promoted teams.
### 2. Match Simulation
Uses a modified Poisson distribution to generate match scores based on ELO differences, including:
- **Home Advantage**: Fixed bonus of 33.8 ELO points for the home team.
- **Tempo & Variance**: Adjustments for match intensity based on ELO gaps.
```

---

## 2. Premier League 2025-26 Season Simulation (`sportsanalysis/premier-league/README.md`)

### Mismatches
| Reference | Documentation (README.md) | Code Implementation (`25-26-season.py`) |
| :--- | :--- | :--- |
| **Line Numbers** | Multiple incorrect references | Most line references are off by **70-100 lines** (e.g., ELO at 8-28 vs actual 80-101). |
| **Home Advantage** | "33.8 Elo points" | Uses **60 Elo** (Line 43) and randomizes between **50-70** per sim (Line 488). |
| **XG Model** | "Logistic scaling" | Uses **Exponential scaling** (`exp(diff/800)`) in `get_expected_goals` (Line 247). |
| **Qualifying Count** | "8+ European teams" | Specifically tracks and reports "at least **9** teams" (Lines 775, 920). |
| **Rating Deviation** | "RD is not actively used" | RD is used in `update_elo` (Line 561) to adjust the K-factor and G-value. |
| **FA Cup Sims** | "10,000 for each European comp" | FA Cup is actually set to **1,000** simulations (Line 685). |

### Suggested Clarifications
- **European Assignments:** The logic in `assign_europe` is complex (handling CL/EL winners). A simple table showing the priority of spots (Top 4 -> CL, 5th -> EL, etc.) would be much clearer than the current prose.
- **Deterministic vs Random:** README says "results are deterministic per run (no random seed set)," which is contradictory. It should state "results vary per run due to randomized parameters and Monte Carlo sampling."

### Proposed Documentation Updates (`sportsanalysis/premier-league/README.md`)
```markdown
## Data Inputs
- **Elo Ratings**: Base strength scores for all 20 teams (approx. Line 80).
- **Mid-Season Table**: Current standings used as the starting state for all simulations (approx. Line 128).
- **Dynamic Parameters**: To account for uncertainty, parameters like Home Advantage (50-70 Elo) and Draw Rate (23-28%) are randomized for every simulation iteration.

## Simulation Components
### Match Engine
- **Expected Goals (XG)**: Calculated using an exponential model: `Base * exp(Elo_Diff / 800)`.
- **Correlated Scoring**: Uses a mixture model where a shared goal component is added to both teams to represent the increased likelihood of draws in tight matches.
```

---

## 3. General Code/Doc Inconsistencies (Across Project)
- **Dependency Management:** Neither README mentions `numba`, which is a hard requirement for the JIT-optimized functions. Running without it leads to significantly slower execution or errors if the environment isn't set up.
- **Rule Compliance:** Both scripts violate the repository's `instructions.md` (e.g., Rule 4: Function size limits, Rule 9: Embedding large datasets). Documentation should not claim "Best Practices" or "Modular Design" when the implementation is monolithic.
