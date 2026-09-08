# Documentation Audit Report: Premier League Simulation Suite

**Auditor:** Senior Technical Writer & Software Documentation Auditor
**Date:** May 2026
**Scope:** `sportsanalysis/premier-league/26-27-season.py`, `sportsanalysis/premier-league/README.md`, and Root `README.md`

---

## Executive Summary

A comprehensive documentation audit was performed on the Premier League 2026/27 simulation suite (`sportsanalysis/premier-league/26-27-season.py`). The audit compared the codebase against both the repository root `README.md` and the sub-directory documentation `sportsanalysis/premier-league/README.md`.

Significant discrepancies were identified between the implemented Python script (`26-27-season.py`) and the root `README.md`. The root `README.md` previously described legacy features, obsolete match engine parameters (such as form adjustments, injury penalties, WDL bias, tempo factors, and Championship playoff coin-flips), and outdated output tables (match probabilities and excitement scores) that are absent in the refactored modular script. Meanwhile, `sportsanalysis/premier-league/README.md` describes the older 2025/26 season simulation (`25-26-season.py`).

This report provides a detailed breakdown of all code-documentation mismatches, suggests technical clarifications, and proposes updated documentation text for both README files to ensure complete alignment with the codebase.

---

## Section 1: Code-Documentation Mismatches

### 1. Simulation Iterations & Execution Architecture
* **Documentation Claim (`README.md`):** States that the model "Runs 10,000 simulations grouped by promoted team".
* **Code Implementation (`26-27-season.py`, Line 31 & Lines 344-420):**
  * Global constant `NUM_PL_SIMS = 2000` sets the total iteration count to 2,000.
  * The simulation runs as a single unified Monte Carlo loop (`run_unified_simulation()`), executing European competition simulations (UCL, UEL, UECL) and Premier League season simulations in tandem.
  * There is no Championship playoff simulation or grouping by promoted team; all 20 teams are fixed in `FIXTURES_LIST` and `PL_BETTING_MARKETS`.

### 2. Rating & Power Rating Calculation
* **Documentation Claim (`README.md`):** Claims Elo ratings are adjusted for "Form (based on current performance)", "Injuries (penalty reduction)", and "Win/Draw/Loss rates (bias adjustments)".
* **Code Implementation (`26-27-season.py`, Lines 312-342):**
  * Base Elo ratings are calculated dynamically via `markets_to_latent_elo()` using implied probabilities from betting markets (`PL_BETTING_MARKETS`) across League Winner, Top 2 Finish, and Relegation markets.
  * No form bonuses, injury reductions, or WDL bias factors exist in `26-27-season.py`.

### 3. Match Simulation Engine & Expected Goals (xG) Model
* **Documentation Claim (`README.md`):** Claims match outcomes use Poisson distributions with "match closeness and tempo effects, shared goals for draws, variance and bias adjustments".
* **Code Implementation (`26-27-season.py`, Lines 54-68 & Lines 206-218):**
  * Expected goals are computed in `compute_expected_goals()` using exponential scaling:
    $$\text{xG}_{\text{home}} = \text{BASE\_HOME\_XG} \times e^{\text{XG\_ELO\_SENSITIVITY} \times (\text{Elo}_{\text{home}} - \text{Elo}_{\text{away}})}$$
    $$\text{xG}_{\text{away}} = \text{BASE\_AWAY\_XG} \times e^{-\text{XG\_ELO\_SENSITIVITY} \times (\text{Elo}_{\text{home}} - \text{Elo}_{\text{away}})}$$
  * `sample_score()` generates independent home and away goal counts using Poisson PMFs up to `MAX_GOALS = 10`.
  * No tempo factors, shared draw goals, or closeness adjustments are present in the match engine.

### 4. European Competition Fatigue Decay
* **Documentation Claim (`README.md`):** Omits any mention of European competition fatigue or dynamic decay.
* **Code Implementation (`26-27-season.py`, Line 40 & Lines 202-212):**
  * Introduces `EUROPEAN_FATIGUE_BASE = {"UCL": 8.0, "UEL": 6.0, "UECL": 5.0}`.
  * In `PLSimulator.simulate_season()`, active European teams suffer an Elo fatigue penalty that linearly decays from maximum at matchday 1 to 0 at matchday 38:
    $$\text{Fatigue} = \text{BaseFatigue} \times \left(1.0 - \frac{i}{379}\right)$$
  * Teams eliminated from European competitions receive no fatigue penalty.

### 5. European Qualification Rules & Champion Entry
* **Documentation Claim (`README.md`):** Describes simplified static assignment: Top 4 $\rightarrow$ Champions League, 5th $\rightarrow$ Europa League, 6th $\rightarrow$ Conference League.
* **Code Implementation (`26-27-season.py`, Lines 372-388):**
  * Incorporates conditional UEFA qualification rules: if an English team wins the UCL or UEL and finishes outside the top 4, they qualify for the UCL, and a 5th-place Premier League team receives an additional UCL qualification spot (`fifth_place_ucl_counts`).

### 6. Output & Reporting Metrics
* **Documentation Claim (`README.md`):** Lists outputs including "Match Probabilities", "Extreme Match Probabilities", "Team Fixture Probabilities", "Points to Win League", and "Average Excitement Score".
* **Code Implementation (`26-27-season.py`, Lines 422-452):**
  * The script outputs a single formatted summary table showing:
    `Pos`, `Team`, `Eur` (Current European competition), `ELO`, `Pts` (Average points), `SD` (Standard Deviation), `95%CI` (Confidence Interval), `Title%`, `UCLQ%`, `5th->UCL%`, `UCLWin%`, `UELWin%`, `UECLWin%`, and `AnyEuroWin%`.
  * Individual fixture probability matrices, extreme score tables, and excitement metrics are not output by `26-27-season.py`.

### 7. Dependencies & Installation
* **Documentation Claim (`README.md`):** Lists `numpy`, `numba`, `tqdm`, `collections`, `math`, `random`.
* **Code Implementation (`26-27-season.py`, Lines 11-18):**
  * Script uses standard libraries (`logging`, `math`, `collections`, `typing`, `random`), `numpy`, and `tqdm`. `numba` is not used in `26-27-season.py`.
  * Running tests requires `pytest`.

---

## Section 2: Suggested Clarifications

1. **Latent Elo Ratings from Betting Odds (`markets_to_latent_elo`)**:
   * **Clarification:** Clarify that team base strengths are not arbitrarily assigned or taken from external historical lists, but derived statistically from consensus market odds (League Winner, Top 2, Relegation) using log-odds normalization centered at 1500 Elo.

2. **Poisson Goal Model & Expected Goals**:
   * **Clarification:** Explain that expected goals ($\text{xG}$) are calculated exponentially from Elo differences with parameters $\text{BASE\_HOME\_XG} = 1.5$, $\text{BASE\_AWAY\_XG} = 1.2$, and $\text{XG\_ELO\_SENSITIVITY} = 0.002$. Goals are sampled independently using cached Poisson Probability Mass Functions (PMFs).

3. **Dynamic European Fatigue Mechanics**:
   * **Clarification:** Detail how European competition participation impacts domestic league performance. Active teams in the Champions League, Europa League, and Conference League experience initial Elo penalties of 8.0, 6.0, and 5.0 points respectively, decaying linearly to 0.0 over the 380 PL fixtures. Eliminated teams suffer 0 fatigue penalty.

4. **European Knockout & Tiebreaker System**:
   * **Clarification:** Document that two-legged European ties simulate home advantage for each leg (+85 Elo), aggregate goals, extra time (with 0.5 xG multiplier), and penalty shoot-outs using Elo-difference logistic win probabilities ($P = 1 / (1 + 10^{-\Delta / 400})$).

5. **Prerequisites & Testing**:
   * **Clarification:** Specify required package dependencies (`numpy`, `tqdm`) and explain how to run integration tests using `python sportsanalysis/premier-league/test_integration.py`.

---

## Section 3: Proposed Updated Documentation

### Proposed Root `README.md`

```markdown
# Premier League 2026-27 Season Simulation Suite

A modular, multi-threaded Monte Carlo simulation suite for predicting Premier League and European competition outcomes using market-derived Elo ratings and Poisson goal modeling.

## Overview

This project simulates the complete 2026/27 Premier League season in conjunction with UEFA European competitions (Champions League, Europa League, and Conference League).

Key features include:
- **Market-Derived Elo Ratings**: Team strength ratings calculated directly from betting market odds (League Winner, Top 2, Relegation).
- **Integrated European Competitions**: Full simulation of UCL, UEL, and UECL 8-matchday league phases and multi-leg knockout rounds.
- **Dynamic Fatigue Decay**: European active status applies a decaying Elo fatigue penalty over the 38-game PL season.
- **Poisson xG Goal Engine**: Goal generation via exponential Expected Goals (xG) scaling and cached Poisson distributions.
- **Conditional UEFA Qualification**: Accurate tracking of UCL top 4 spots and conditional 5th-place entry via UCL/UEL winner qualification.

## Installation

1. Clone the repository:
   ```bash
   git clone <repository-url>
   cd <repository-folder>
   ```
2. Install required Python packages:
   ```bash
   pip install numpy tqdm pytest
   ```

## Usage

### Run Premier League 2026/27 Simulation
```bash
python sportsanalysis/premier-league/26-27-season.py
```

### Run Integration Test Suite
```bash
python sportsanalysis/premier-league/test_integration.py
```

## Simulation Architecture & Parameters

### Global Constants
- `NUM_PL_SIMS`: 2,000 unified simulations (default).
- `HOME_ADVANTAGE_ELO`: +85.0 Elo points for home teams.
- `BASE_HOME_XG`: 1.5 baseline expected goals.
- `BASE_AWAY_XG`: 1.2 baseline expected goals.
- `XG_ELO_SENSITIVITY`: 0.002 exponential Elo scaling factor.
- `EUROPEAN_FATIGUE_BASE`: UCL = 8.0, UEL = 6.0, UECL = 5.0 Elo penalty.

### Output Metrics
The simulation outputs a comprehensive projection table including:
- **Pos / Team / ELO**: Average simulated finishing position, team name, and base Elo rating.
- **Pts / SD / 95%CI**: Mean points, standard deviation, and 95% confidence interval bounds.
- **Title% / UCLQ%**: Title win probability and overall Champions League qualification probability.
- **5th->UCL%**: Probability of 5th place earning a UCL spot via English UCL/UEL winners.
- **UCLWin% / UELWin% / UECLWin% / AnyEuroWin%**: Individual and cumulative European trophy win probabilities.

## License
Educational and research purposes only.
```

---

### Proposed `sportsanalysis/premier-league/README.md`

```markdown
# Premier League & European Simulations

This directory contains simulation scripts for Premier League seasons and integrated UEFA competitions.

## Available Scripts

1. **`26-27-season.py`**:
   - Refactored, object-oriented simulation engine for the 2026/27 season.
   - Integrates Premier League matches with Champions League (UCL), Europa League (UEL), and Conference League (UECL).
   - Incorporates dynamic European fatigue decay and market-derived Elo ratings.

2. **`25-26-season.py`**:
   - Legacy simulation engine for remaining fixtures of the 2025/26 season.
   - Features mid-season table tracking, form adjustments, and FA Cup knockout simulations.

3. **`test_integration.py`**:
   - Test harness for validating execution and pipeline integrity across simulation modules.

## Execution

Run the 2026/27 simulation:
```bash
python sportsanalysis/premier-league/26-27-season.py
```

Run integration tests:
```bash
python sportsanalysis/premier-league/test_integration.py
```
```
