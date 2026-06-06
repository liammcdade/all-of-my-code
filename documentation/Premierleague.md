# Premier League Simulation Documentation Audit Report

## Audit Scope
- **2026-27 Season Simulation**: `sportsanalysis/premier-league/26-27-season.py` vs. Root `README.md`
- **2025-26 Season Simulation**: `sportsanalysis/premier-league/25-26-season.py` vs. `sportsanalysis/premier-league/README.md`

---

## 1. 2026-27 Season Simulation Audit

### Mismatches
| Type | Description | Reference |
| :--- | :--- | :--- |
| **Simulations** | Documentation states 10,000 simulations; code is hardcoded to `NUM_SIMS = 5000`. | `26-27-season.py`:155 |
| **League Structure** | Documentation implies standard 20 teams; code simulates a **19-team** league (18 fixed + 1 promoted). | `26-27-season.py`:31 |
| **ELO Adjustments** | Documentation claims adjustments for Form, Injuries, and WDL; code currently uses raw ratings. | `26-27-season.py`:39-49 |
| **Promotion Logic** | Documentation describes a playoff simulation; code uses a 50/50 coin flip. | `26-27-season.py`:161 |
| **Missing Features**| Match Probabilities, Extreme Probs, and Team Fixture Probs are listed in README but absent in code. | Root `README.md` |
| **Europe Spots** | Conference League (6th) is mentioned in README but not reported in code output. | `26-27-season.py`:174-177 |

### Suggested Clarifications
- **Reduced Team Set**: Explicitly mention that the 26-27 model currently uses 19 teams and a simplified promotion mechanic.
- **Feature Roadmap**: Clarify that Form/Injury/WDL adjustments and advanced match statistics are planned features but not yet active in the 26-27 script.

### Proposed Documentation Updates (Root `README.md`)
- **Update Usage**: Change "10,000 simulations" to "5,000 simulations".
- **Update Algorithm**: "ELO Ratings: Basic ratings (Form, Injuries, and WDL adjustments are currently under development)."
- **Update Output**: Remove the sections for "Match Probabilities", "Extreme Match Probabilities", and "Team Fixture Probabilities" to align with current script output.

---

## 2. 2025-26 Season Simulation Audit

### Mismatches
| Type | Description | Reference |
| :--- | :--- | :--- |
| **Home Advantage**| README says 33.8 Elo; code uses `HOME_ADVANTAGE_ELO = 60` (randomized 50-70). | `25-26-season.py`:46, 307 |
| **XG Model** | README describes "Logistic scaling"; code implements **Exponential scaling** (`exp(diff/800)`). | `25-26-season.py`:136 |
| **WDL Bias** | README claims XG boost based on W/L differential; `wdl_rates` are defined but **unused**. | `25-26-season.py`:206-227 |
| **Euro Qual** | README mentions "8+ teams"; code tracks and reports "**at least 9 teams**". | `25-26-season.py`:527 |
| **Resolved Bug** | **FIXED**: `simulate_match` previously passed team indices to the XG function; now corrected to pass Elo ratings. | `25-26-season.py`:444 |

### Suggested Clarifications
- **K-Factor & RD**: Clarify that Rating Deviation (RD) is used for the post-match Elo update K-factor, even though it is not used in the match simulation engine.
- **Match Engine Details**: The "Bivariate Poisson" mentioned in docs is implemented as independent Poisson samples with a draw-boost logic in `simulate_match`.

### Proposed Documentation Updates (`sportsanalysis/premier-league/README.md`)
- **Update Parameters**: "Home advantage (Variable 50-70 Elo points)."
- **Update Model**: "Expected Goals (XG): Exponential model based on Elo difference (`base * exp(diff/800)`)."
- **Update European Logic**: Clarify that the seasonal simulation samples from pre-computed "Finals" probabilities rather than running the full knockout bracket in every iteration.

---

## 3. General Implementation Feedback

- **Runnable Examples**: The usage instructions are correct, but `numba` is missing from the root `requirements.txt`, which may cause installation issues for some users.
- **Language**: The documentation is generally clear, but technical model descriptions (e.g., "Mixture Model" vs "Bivariate Poisson") should be standardized to match the specific logic in `simulate_match`.
