# Documentation Audit Report: Premier League 2026-27 Season Simulation

**Auditor:** Jules (Senior Technical Writer & Software Documentation Auditor)
**Date:** May 2024
**Scope:** `sportsanalysis/premier-league/26-27-season.py` vs. Root `README.md`

## 1. Executive Summary
The documentation (`README.md`) significantly overstates the capabilities and complexity of the current implementation in `26-27-season.py`. The documentation appears to be a carry-over from a more complex version of the simulation (likely `25-26-season.py`), resulting in several critical mismatches regarding features, team counts, and statistical outputs.

---

## 2. Identified Mismatches and Discrepancies

### A. Scale and Scope
- **Simulation Count:** The documentation claims the simulation runs **10,000 iterations**. The code (Line 146) is configured for `NUM_SIMS = 5000`.
- **Team Count:** The code defines **18 base teams** and adds **1 promoted team**, totaling **19 teams**. A standard Premier League simulation (and the one implied by the documentation) requires **20 teams**.
- **Championship Playoffs:** The documentation claims a "simulation" of Championship playoffs. The code (Line 160) uses a simple `random.random() < 0.5` coin flip to pick one team.

### B. Feature Implementation (Documented but Missing)
The following features are described in the `Algorithm Overview` and `Features` sections but are **not present or used** in the `26-27-season.py` logic:
- **Form Adjustments:** Claimed to be used in power ratings; no logic exists in the match engine to apply form.
- **Injury Penalties:** Claimed to be used; parameters exist in `TeamRegistry.add_team` but are never utilized.
- **Win/Draw/Loss Rates:** Claimed to adjust Elo; not implemented.
- **Fixture Difficulty:** Claimed as a comprehensive statistic; not calculated or displayed.
- **Match-Specific Parameters:** Documentation mentions "Match-specific parameters" and "Tempo effects." While a `tempo_factor` exists (Line 84), it is a static calculation and does not account for the specific dynamics described in the README.
- **Conference League:** The documentation mentions Conference League qualification (6th place). The code only assigns Champions League (Top 4) and Europa League (5th place).

### C. Technical Dependencies
- **Missing Dependency:** The `Installation` and `Dependencies` sections omit **Numba**, which is a strict requirement for the script to run (Line 8, `@numba.jit`).

---

## 3. Clarifications and Actionable Feedback

### Code Alignment
- **Function Responsibility:** The `main()` function (Lines 141-213) violates the "One Function = One Responsibility" rule from `instructions.md`. It handles setup, simulation loop, data aggregation, and console output.
- **Data Integrity:** The 19-team setup is a major logical error for a "Premier League" simulation. I recommend adding the missing team to `TEAM_NAMES` and `ELO_RATINGS`.
- **Documentation Granularity:** The `Algorithm Overview` should be simplified to reflect the actual Poisson model used, or the code should be updated to include the promised form and injury factors.

### Language and Accessibility
- **Jargon:** Terms like "Poisson goal modeling" and "Monte Carlo" are used correctly but lack a brief plain-language explanation for non-technical users.
- **Assumed Knowledge:** The documentation assumes the user knows how to resolve `ModuleNotFoundError` for missing packages not listed in `requirements.txt` (specifically `numba`).

---

## 4. Proposed Updated Documentation (Snippet)

*Revised Features and Algorithm section for README.md:*

```markdown
## Features

- **ELO-Based Ratings**: Vectorized team strength ratings for high-performance simulation.
- **Match Simulation**: Numba-accelerated Poisson goal modeling with Home Advantage adjustments.
- **Monte Carlo Simulations**: Runs 5,000 iterations to generate title and relegation probabilities.
- **Promotion Variability**: Models pre-season uncertainty by alternating between top Championship contenders.

## Algorithm Overview

### 1. Power Ratings
Uses base ELO ratings to determine team strength. Ratings are used to calculate the Expected Goals (XG) for each fixture.

### 2. Match Simulation
- **XG Calculation**: Derived from ELO difference using a logistic growth model.
- **Goal Generation**: Bivariate Poisson distribution accounting for "shared goals" in close matchups.
- **Performance**: Optimized via Numba JIT compilation for rapid execution.

### 3. European Qualification
- **Champions League**: Assigned to the Top 4 finishers.
- **Europa League**: Assigned to the 5th place finisher.
```

---

## 5. Compliance with `instructions.md`
- **Rule 6 (No Magic Numbers):** Several constants like `0.5` (Line 160) and index offsets in `display_team_statistics` should be named.
- **Rule 19 (Typed Functions):** Most functions are typed, which is good, but `main` and some helper logic could benefit from stricter type hinting for dictionaries.
- **Rule 20 (No Massive Print Blocks):** The simulation summary in `main` is becoming a "massive print block." This should be moved to a `display_season_summary` function.
