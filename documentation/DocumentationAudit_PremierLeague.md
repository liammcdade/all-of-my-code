# Documentation Audit Report: Premier League Simulations

**Auditor:** Jules (Senior Technical Writer & Software Documentation Auditor)
**Date:** June 2024
**Scope:** `sportsanalysis/premier-league/25-26-season.py`, `sportsanalysis/premier-league/26-27-season.py`, `sportsanalysis/premier-league/README.md` (25-26), and root `README.md` (26-27).

---

## 1. Mismatches & Inconsistencies

### 1.1. Premier League 2025-26 Simulation

| Category | Documentation Claim | Code Reality | Reference (Code) |
| :--- | :--- | :--- | :--- |
| **Line Numbers** | Elo ratings at lines 8-28. | Elo ratings are at lines 80-100. | `25-26-season.py`:80 |
| **Line Numbers** | Current Table at lines 54-76. | Current Table is at lines 128-153. | `25-26-season.py`:128 |
| **Line Numbers** | Fixtures at lines 78-106. | Fixtures are at lines 155-179. | `25-26-season.py`:155 |
| **Logic** | `wdl_rates` used for variance boost. | `wdl_rates` is defined but never used in logic. | `25-26-season.py`:355 |
| **Model** | XG uses "Logistic scaling" `1/(1+exp(-diff/400))`. | XG uses "Exponential scaling" `exp(diff/800)`. | `25-26-season.py`:245 |
| **Structure** | Complex European semi-finals/two-leg ties. | Simplified single-match hardcoded finals. | `25-26-season.py`:470-494 |
| **Output** | Probability for "8+ European teams". | Script reports "at least 9 European teams". | `25-26-season.py`:810, 1021 |
| **Parameters** | RD (Rating Deviation) "not actively used". | `update_elo` uses RD to adjust K-factor and G-value. | `25-26-season.py`:560, 616 |

### 1.2. Premier League 2026-27 Simulation

| Category | Documentation Claim | Code Reality | Reference (Code) |
| :--- | :--- | :--- | :--- |
| **Parameters** | Runs 10,000 simulations. | Runs 5,000 simulations. | `26-27-season.py`:181 |
| **Features** | Ratings adjusted for Form, Injury, WDL bias. | Arguments accepted but entirely ignored in logic. | `26-27-season.py`:49, 107 |
| **Outputs** | "Match Probabilities" generated for fixtures. | Not implemented in 2026-27 script. | N/A |
| **Outputs** | "Extreme Match Probabilities" generated. | Not implemented in 2026-27 script. | N/A |
| **Outputs** | "Team Fixture Probabilities" generated. | Not implemented in 2026-27 script. | N/A |
| **European** | Qualifiers for Conference League (6th). | Logic only tracks Top 4 (CL) and 5th (EL). | `26-27-season.py`:207-211 |
| **Logic** | "Realistic match-specific parameters". | Uses base Elo difference without injury/form. | `26-27-season.py`:118 |
| **Excitement** | Contender-based score (from 25-26 logic). | Simple `(1st_Pts - 2nd_Pts) / 10`. | `26-27-season.py`:213, 241 |

---

## 2. Suggested Clarifications

1. **Jargon Mitigation**:
   - **Elo Difference Scaling**: Clarify that the "400-scale" means a 400-point difference roughly translates to a 10x strength difference, which helps users understand the `exp(diff/800)` or logistic formula impact.
   - **Poisson vs. Bivariate Poisson**: The documentation mentions "Bivariate Poisson" but the 25-26 code uses a mixture model with a shared lambda for draws. This should be explained as "Correlated Scoring Model" for better clarity.
2. **Audience Knowledge Gaps**:
   - The documentation assumes users know how UEFA qualification "cascades" work (e.g., if a CL team wins the FA Cup). While the 25-26 code handles some of this in `assign_europe`, the documentation should explicitly state that the simulation follows the 2025-26 qualification rules.
3. **Execution Instructions**:
   - The `README.md` implies dependencies are in `requirements.txt`. However, `numba` and `typer` are often missing from standard data science environments and should be highlighted as mandatory for performance and CLI features.

---

## 3. Proposed Documentation Updates

### 3.1. Updated Algorithm Overview (Root README)

**2. Match Simulation**
Uses Poisson goal modeling with:
- **Home Advantage**: Fixed Elo bonus applied to the home team.
- **Dynamic XG Calculation**: Goals are modeled using an exponential growth function `exp(ELO_DIFF / 800)` for the 25-26 model and a logistic curve for 26-27.
- **Correlated Scoring**: Draw probabilities are boosted using a shared goal factor (26-27) or mean-goal draw sampling (25-26).

**3. European Qualification**
- **Champions League**: Top 4 teams (standard) or Top 5 (25-26 UEFA coefficient logic).
- **Europa League**: 5th place and FA Cup winner.
- **Conference League**: 6th place (Note: 26-27 currently only tracks CL/EL).

### 3.2. Corrected Usage & Configuration (25-26 README)

**Parameters**
- **Iterations**: 25,000 (Premier League), 10,000 (UEFA Finals).
- **Elo Ratings**: Located at lines 80-100.
- **Current Table**: Located at lines 128-153.
- **European Winners**: Sampled from pre-simulated final match probabilities (lines 190-210).

**Key Correction**: The `wdl_rates` table is for reference and is not currently incorporated into the match simulation engine. Injury penalties and form adjustments are applied directly to team ratings before fixture simulation.
