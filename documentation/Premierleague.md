# Documentation Audit Report: Premier League Simulations

**Auditor:** Jules (Senior Technical Writer & Software Documentation Auditor)
**Date:** May 20, 2024
**Scope:**
1. Root `README.md` vs `sportsanalysis/premier-league/26-27-season.py`
2. `sportsanalysis/premier-league/README.md` vs `sportsanalysis/premier-league/25-26-season.py`

---

## 1. Premier League 2026-27 Season Audit

### Mismatches
| Feature | Documentation (README.md) | Code Implementation (`26-27-season.py`) | Line Reference |
| :--- | :--- | :--- | :--- |
| **Simulation Iterations** | 10,000 simulations | `NUM_SIMS = 5000` | 155 |
| **League Size** | Standard 20-team league implied | 19 teams total (18 fixed + 1 promoted) | 20, 159 |
| **ELO Adjustments** | Claims Form, Injury, and WDL bias adjustments | Uses base ELOs without these modifiers | 62, 102 |
| **Promotion Logic** | "Championship Playoff Simulation" | 50/50 coin flip between Southampton and Hull City | 161 |
| **Output: European Spots** | Includes Conference League tracking | Only tracks Title, Top 4 (CL), and 5th (EL) | 173-179 |
| **Output: Match Probs** | Claims "Match Probabilities for all remaining fixtures" | Not implemented in this version | N/A |
| **Side Effects** | Not mentioned | Deletes `__pycache__` directory on exit | 219 |

### Suggested Clarifications
* **Excitement Score:** The README states it is "out of 10". In code, it calculates `leader_pts - second_pts` and divides by 10. This means a *lower* score is "more exciting" (closer race), which contradicts typical "excitement" metrics where higher is better.
* **Match Matrix:** The code creates 342 fixtures for 19 teams. The documentation should specify that this is a 19-team simulation to explain why there aren't 380 games.

---

## 2. Premier League 2025-26 Season Audit

### Mismatches
| Feature | Documentation (`README.md`) | Code Implementation (`25-26-season.py`) | Line Reference |
| :--- | :--- | :--- | :--- |
| **Line Citations** | Most line references are outdated (e.g., Elo Ratings at 8-28) | ELO Ratings are actually at 80-100 | 80-100 |
| **XG Model** | Claims "Logistic scaling" | Uses "Exponential scaling" (`exp(diff/800)`) | 211 |
| **European Tourneys** | Describes full semi-finals and two-leg ties | Simulates only the Final between hardcoded teams | 763-780 |
| **Home Advantage** | Claims 33.8 Elo points | Base is 60; randomized 50-70 during sims | 43, 506 |
| **FA Cup Simulations** | Claims 10,000 simulations | `FA_SIMS = 1000` | 59 |
| **European Qualification** | Claims probability for "8+ European teams" | Tracks "9+ European teams" | 697 |

### Suggested Clarifications
* **Rating Deviation (RD):** Documentation notes RD is not used; this is correct, but the code still contains large RD dictionaries that clutter the source.
* **Fixture Grouping:** README mentions fixtures grouped by "Round"; the code uses a flat list of 21 remaining matches.

---

## 3. General Observations & Actionable Feedback

1. **Syntactic Correctness:** Both scripts are syntactically correct and runnable, provided dependencies (`numpy`, `numba`, `tqdm`) are installed.
2. **Jargon:** The term "Bivariate Poisson" is used in memory/intent but the documentation and code use a simplified "Shared Goal" model.
3. **Prerequisite Knowledge:** The documentation assumes the user knows how to install `pip` requirements, which is standard, but does not mention that `numba` requires a compatible C compiler in some environments for the JIT to work optimally.

### Proposed Documentation Update (26-27 Season)
**Algorithm Overview - Power Ratings:**
*Current:* Uses ELO ratings adjusted for Form, Injuries, and WDL rates.
*Proposed:* Uses base ELO ratings for 18 core teams and one of two potential promoted teams (Southampton or Hull City).

**Usage:**
*Current:* The script runs 10,000 simulations...
*Proposed:* The script runs 5,000 Monte Carlo simulations per run.
