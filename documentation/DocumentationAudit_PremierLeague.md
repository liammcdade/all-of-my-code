# Documentation Audit Report: Premier League Simulation Scripts

**Auditor:** Jules (Senior Technical Writer & Software Documentation Auditor)
**Date:** June 24, 2024
**Scope:** Review of 2025-26 and 2026-27 season simulation scripts and their respective documentation.

---

## Executive Summary

The audit revealed significant discrepancies between the implementation code and the supporting documentation for both simulation versions. The 2025-26 documentation contains pervasive line-number inaccuracies and describes models (e.g., XG scaling) that differ from the actual code. The 2026-27 documentation describes advanced features (form adjustments, injury penalties, playoff simulations, and detailed probability outputs) that are entirely absent from the implementation script.

---

## 1. 2025-26 Season Audit
**Code:** `sportsanalysis/premier-league/25-26-season.py`
**Docs:** `sportsanalysis/premier-league/README.md`

### 1.1 Mismatches

| Feature | Documentation Claim | Actual Code Implementation | Line/Function |
| :--- | :--- | :--- | :--- |
| **Line References** | Cited for Data Inputs section (e.g., Elo at 8-28) | All line references are incorrect. | README (Data Inputs) |
| **Home Advantage** | 33.8 Elo points | 60 Elo points (randomized 50-70 per sim) | `25-26-season.py`: 46, 562 |
| **Expected Goals (XG)**| Logistic scaling formula | Exponential scaling: `home_base * exp(diff/800)` | `get_expected_goals` (244) |
| **Rating Deviation** | "RD is not actively used" | Used in `update_elo` for K-factor and G-value | `update_elo` (560) |
| **Europe Tracking** | Probability for "8+ European teams" | Tracks "at least 9 European teams" | `25-26-season.py`: 482, 1032 |

### 1.2 Missing Details
- **European Finals:** Documentation implies complex tournament structures, but implementation uses single-match finals between hardcoded teams (lines 470-494).
- **Iteration Counts:** Script runs 25,000 PL simulations, while README mentions 25k for PL and 10k for Europe, but doesn't clarify they are separate loops.

---

## 2. 2026-27 Season Audit
**Code:** `sportsanalysis/premier-league/26-27-season.py`
**Docs:** `README.md` (Root)

### 2.1 Mismatches

| Feature | Documentation Claim | Actual Code Implementation | Line/Function |
| :--- | :--- | :--- | :--- |
| **Simulations** | 10,000 simulations | 5,000 simulations | `NUM_SIMS` (181) |
| **Elo Adjustments** | Adjusted for form, injuries, and WDL bias | Base Elo used without modifiers | `main` loop (174-213) |
| **Promotion Logic** | Championship Playoff Simulation | 50/50 coin flip between Southampton/Hull | `main` loop (194) |
| **European Slots** | CL (1-4), EL (5), Conference (6) | CL (1-4) and EL (5) only; Conf omitted | `main` loop (201-205) |

### 2.2 Missing Features in Code
The following features are described in the README but **not implemented** in the script:
- **Match Probabilities:** Win/draw/loss percentages for all remaining fixtures.
- **Extreme Match Probabilities:** Most likely home wins, draws, and away wins.
- **Team Fixture Probabilities:** Winning/losing/drawing all remaining games.

### 2.3 Undocumented Internal Components
- **`TeamRegistry` Class:** (lines 43-69) Core management of team data, completely missing from docs.
- **Vectorized Engine:** `run_simulation_vectorized` (lines 115-151) uses Numba for performance, but the mechanism is undocumented.

---

## 3. General Observations

### 3.1 Clarifications Needed (Jargon)
The following terms are used without definition, potentially confusing non-technical users:
- **Elo Rating:** Needs a brief explanation of how strength is calculated.
- **Poisson Distribution:** Needs a note on why it is used for goal modeling (rare events).
- **Monte Carlo Method:** Needs clarification that results are based on aggregate random trials.

### 3.2 Installation & Prerequisites
- **Missing Dependency:** `numba` is required for the scripts to run (due to `@numba.jit` decorators) but is missing from the root `requirements.txt`.
- **Environment Context:** Instructions for `25-26-season.py` fail if run from the repository root because they expect to write output/logs locally within the `premier-league` directory.

### 3.3 Coding Standards Violations
Both scripts violate the following rules in `instructions.md`:
- **Rule 4 (Function Size):** `assign_europe` (25-26) and `main` (26-27) exceed the 60-line limit.
- **Rule 9 (Giant Dictionaries):** Large datasets are embedded directly in the logic (e.g., Elo and Fixtures).
- **Rule 16 (File Length):** `25-26-season.py` (1046 lines) exceeds the 800-line maximum.

---

## 4. Proposed Updates

### 4.1 Update 2025-26 Line Numbers
Correct all line references in `sportsanalysis/premier-league/README.md` to reflect current code positions.
- Elo ratings: 80-100
- Table: 128-153
- Fixtures: 155-188

### 4.2 Align 2026-27 Features
Remove claims of form/injury adjustments and fixture probability outputs from the root `README.md` until they are implemented, or implement the missing features in the script to match the documentation.

### 4.3 Standardize Dependencies
Update the root `requirements.txt` to include `numba` and `tqdm`.

---
*End of Report*
