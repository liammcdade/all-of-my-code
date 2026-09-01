# Comprehensive Documentation Audit Report: Premier League 2026/27 Simulation Suite

**Auditor Persona**: Senior Technical Writer & Software Documentation Auditor
**Scope**: Premier League 2026/27 Simulation Suite (`sportsanalysis/premier-league/26-27-season.py`, `UCL.py`, `UEL.py`) and associated documentation (`README.md`, `sportsanalysis/premier-league/README.md`)
**Date**: September 2026

---

## Executive Summary

This audit evaluates the codebase and documentation implementation for the **Premier League 2026/27 Simulation Suite**. The suite consists of three interconnected simulation scripts: `26-27-season.py` (main Premier League simulation engine), `UCL.py` (UEFA Champions League 36-team Swiss model & knockout simulator), and `UEL.py` (UEFA Europa League Swiss model & knockout simulator).

Our audit revealed significant discrepancies between the implemented Python codebase and the project documentation (`README.md` and `sportsanalysis/premier-league/README.md`). Most notably, the documentation references legacy features from previous season models (such as explicit form/injury adjustments, bivariate Poisson draw boosts, Championship playoff simulations, and fixture probability tables) that are absent or fundamentally altered in the current 2026/27 codebase. Conversely, major architectural innovations in the current code—such as betting market latent Elo derivation, multi-stage European competition simulations with fatigue penalties, and actual result locking—are entirely unmentioned in the documentation.

This report provides a structured audit covering:
1. **Code vs. Documentation Mismatches & Discrepancies** (with explicit function names and line numbers).
2. **Suggested Clarifications & Audience Guidance** (mathematical concepts, execution flow, and jargon demystification).
3. **Software Architecture & Code Quality Audit** (evaluating code against `instructions.md`).
4. **Proposed Updated Documentation Text** (a production-ready, accurate README).

---

## 1. Discrepancies & Code-Documentation Mismatches

### 1.1. Simulation Iteration Counts
* **Documentation Claim**: Root `README.md` claims the script "Runs 10,000 simulations grouped by promoted team." `sportsanalysis/premier-league/README.md` claims 25,000 iterations for Premier League and 10,000 for European competitions.
* **Code Implementation**:
  * `26-27-season.py` (line 27): `NUM_PL_SIMS = 2000` (2,000 simulations).
  * `UCL.py` (line 26): `NUM_CL_SIMS = 2000` (2,000 simulations).
  * `UEL.py` (line 668): `NUM_UEL_SIMS = 2000` (2,000 simulations).
* **Impact**: Users expecting 10,000–25,000 Monte Carlo iterations will be surprised by the default 2,000 iterations in the codebase.

### 1.2. Championship Playoff & Promotion Logic
* **Documentation Claim**: Root `README.md` states the script "Simulates Championship playoffs to determine promotion" and groups Monte Carlo runs by promoted team.
* **Code Implementation**:
  * `26-27-season.py` (lines 347–348): Promoted teams are hardcoded as `PROMOTED_TEAMS = {"Ipswich", "Coventry", "Hull"}` within the fixture list.
  * Line 348: `PROMOTED_PENALTY = 0`. Promoted teams are directly assigned to the team registry based on market Elo without any Championship playoff simulation loop or outcome grouping.
* **Impact**: The documentation falsely advertises a multi-tier Championship promotion simulation feature that does not exist in the code.

### 1.3. Form, Injury, and Win/Draw/Loss (WDL) Bias Adjustments
* **Documentation Claim**: Root `README.md` claims power ratings use "adjustments for form, injuries, and win/draw/loss tendencies." `sportsanalysis/premier-league/README.md` details specific linear/nonlinear form bonuses and injury penalties.
* **Code Implementation**:
  * `26-27-season.py` derives team Elo ratings solely from betting market odds using `markets_to_latent_elo()` (lines 304–338).
  * Form adjustments, injury penalties, and WDL bias functions are absent from `26-27-season.py`. The only Elo adjustment applied during runtime is the European fatigue penalty (`EUROPEAN_PENALTIES`, lines 29, 378–385).
* **Impact**: Readers are misled regarding how team strengths are constructed. In reality, market odds implicitly bake in form, injuries, and team strength.

### 1.4. Goal Modeling & Match Engine Physics
* **Documentation Claim**: Root `README.md` states match simulation uses "Match closeness and tempo effects, shared goals for draws, variance and bias adjustments."
* **Code Implementation**:
  * `26-27-season.py` delegates match goal simulation to `compute_expected_goals(h_elo, a_elo)` and `sample_score(home_xg, away_xg)` imported from `UCL.py` (lines 80–84).
  * `compute_expected_goals()` in `UCL.py` (lines 80–84) calculates expected goals using an exponential scaling formula:
    $$\text{xg}_h = \text{BASE\_HOME\_XG} \times e^{\text{XG\_ELO\_SENSITIVITY} \times (elo_h - elo_a)}$$
    $$\text{xg}_a = \text{BASE\_AWAY\_XG} \times e^{-\text{XG\_ELO\_SENSITIVITY} \times (elo_h - elo_a)}$$
  * `sample_score()` in `UCL.py` (lines 69–77) samples home and away goals independently from Poisson PMFs cached in `_POISSON_CACHE`.
  * Closeness factors, tempo scaling, shared draw lambdas (bivariate Poisson), and WDL variance boosts are not present in the 2026/27 codebase.
* **Impact**: Documentation misrepresents the underlying statistical model (Poisson vs. Bivariate Poisson / Closeness model).

### 1.5. Suite Architecture & European Competition Integration
* **Documentation Claim**: Root `README.md` describes European qualification as a simple post-simulation placement (Top 4 → CL, 5th → EL, 6th → Conf). It makes no reference to `UCL.py` or `UEL.py`.
* **Code Implementation**:
  * The 2026/27 suite is a multi-file architecture (`26-27-season.py`, `UCL.py`, `UEL.py`).
  * `26-27-season.py` imports `run_champions_league_simulation` from `UCL.py` (line 22) and `run_europa_league_simulation` from `UEL.py` (line 23).
  * `main()` in `26-27-season.py` (lines 539–548) executes `run_champions_league_simulation()` and `run_europa_league_simulation()` *first*, generating European winning probabilities for Premier League clubs.
  * European involvement reduces domestic Elo ratings (`EUROPEAN_PENALTIES`, lines 29, 378–385): UCL (-45.0 Elo), UEL (-30.0 Elo), UECL (-20.0 Elo).
* **Impact**: The documentation omits the main architectural highlight of the suite—integrated European tournament simulations with domestic fatigue penalties.

### 1.6. Console Output & Statistical Features
* **Documentation Claim**: Documentation states the output includes:
  1. Match Probabilities (W/D/L % for remaining fixtures)
  2. Extreme Match Probabilities (highest home/away win chance, most likely draw)
  3. Team Fixture Probabilities (win/draw/lose all remaining games)
  4. Points to Win League (min/max points)
  5. Probability of Relegation with 40+ Points
  6. Average Excitement Score
* **Code Implementation**:
  * `26-27-season.py` (lines 500–533) outputs a single table containing:
    `Pos`, `Team`, `Eur`, `ELO`, `Pts`, `SD`, `Title`, `UCL`, `Europa`, `TopHalf`, `StayUp`, `Releg`, and `CL/UEL Win %`.
  * None of fixture match probabilities, extreme match tables, fixture streaks, 40+ points relegation metrics, or excitement scores are computed or printed in `26-27-season.py`.
* **Impact**: Users attempting to locate fixture-level probability tables or excitement scores mentioned in the documentation will fail to find them.

### 1.7. Actual Results & Score Locking Feature
* **Documentation Claim**: Documentation makes no mention of actual played match scores or locked fixture capability.
* **Code Implementation**:
  * `26-27-season.py` defines `ACTUAL_RESULTS` dictionary (lines 280–286) with real match scores (e.g. `("Everton", "Crystal Palace"): (2, 0)`).
  * `LOCKED_SCORES` list and `_parse_locked_scores()` (lines 288, 357–366) allow forcing locked score outputs.
  * `run_single_pl_simulation()` (lines 394–420) checks `actual_results_mask`; played fixtures use exact actual goals rather than random simulation.
* **Impact**: A powerful feature that allows mid-season simulation based on real played games is undocumented.

### 1.8. Dependencies & Numba JIT Optimization Claims
* **Documentation Claim**: Root `README.md` lists `numba` as a key dependency and claims it uses "JIT compilation for performance optimization."
* **Code Implementation**:
  * Neither `26-27-season.py`, `UCL.py`, nor `UEL.py` imports or uses `numba`.
  * Vectorization/acceleration is achieved via standard NumPy arrays (`np.array`, `np.searchsorted`, `np.cumsum`) and cached Poisson PMF arrays (`_POISSON_CACHE` in `UCL.py`, lines 58–67).
* **Impact**: Unnecessary dependency listed in documentation; misleading performance mechanism claims.

---

## 2. Suggested Clarifications & Audience Guidance

### 2.1. Deriving Latent Elo Ratings from Betting Odds (`markets_to_latent_elo`)
* **Code Reference**: `26-27-season.py`, lines 304–338.
* **Explanation for Audience**:
  The simulation does not require manual entry of team Elo ratings. Instead, `markets_to_latent_elo()` reads fractional odds from three betting markets in `PL_BETTING_MARKETS` (League Winner, Top 2 Finish, Relegation).
  1. Converts fractional odds $\frac{a}{b}$ to implied probability $P = \frac{b}{a+b}$.
  2. Normalizes probabilities across teams and converts to log-probabilities.
  3. Computes mean log-probability to center ratings around `LEAGUE_AVERAGE_ELO` (1500.0).
  4. Applies Elo scaling factor ($\text{scale} = \frac{400}{\ln 10} \approx 173.72$) and shrinkage factor (`ELO_SHRINKAGE = 0.75`) to prevent extreme outlier ratings.

### 2.2. Mathematical Model for Goal Sampling
* **Code Reference**: `UCL.py`, lines 58–84.
* **Explanation for Audience**:
  Matches are simulated using independent Poisson distributions for home and away goals:
  $$\text{Prob}(G = k) = \frac{\lambda^k e^{-\lambda}}{k!}$$
  where expected goals ($\lambda_h, \lambda_a$) depend on the adjusted Elo difference between home and away teams. Home advantage (`HOME_ADVANTAGE_ELO = 85.0`) is added to the home team's rating before computing expected goals.
  To optimize speed, Poisson Probability Mass Functions (PMFs) are precomputed and cached in `_POISSON_CACHE` up to `MAX_GOALS = 10`.

### 2.3. European Fatigue Penalty Mechanism
* **Code Reference**: `26-27-season.py`, lines 29, 378–385.
* **Explanation for Audience**:
  Teams participating in European club competitions face domestic performance penalties due to fixture congestion and squad rotation:
  * **Champions League (UCL)**: $-45.0$ Elo rating penalty
  * **Europa League (UEL)**: $-30.0$ Elo rating penalty
  * **Conference League (UECL)**: $-20.0$ Elo rating penalty
  These penalties are subtracted from base Elo ratings during domestic fixture simulation in `run_single_pl_simulation()`.

### 2.4. Swiss Model European Competitions (`UCL.py` & `UEL.py`)
* **Code Reference**: `UCL.py` (lines 184–381) and `UEL.py` (lines 13–662).
* **Explanation for Audience**:
  Both `UCL.py` and `UEL.py` model the UEFA 36-team Swiss-system league phase (8 matches per team: 4 home, 4 away). Following the league phase:
  * Top 8 teams qualify directly to the Round of 16.
  * Teams 9–24 enter a two-legged playoff round (9th vs 24th, 10th vs 23rd, etc.).
  * Single-elimination knockout rounds (R16, Quarter-finals, Semi-finals, Final) determine the European champion.

---

## 3. Code Standards & Architectural Audit (`instructions.md`)

Evaluating `26-27-season.py`, `UCL.py`, and `UEL.py` against the project's Python Engineering Standards (`instructions.md`):

| Rule | Requirement | Code Base Status | Recommendation |
| :--- | :--- | :--- | :--- |
| **Rule 1: Maximum Nesting** | $\le 3$ levels of indentation | **Compliant**. Early returns and clean loops keep nesting $\le 3$. | Maintain current structure. |
| **Rule 3: Single Responsibility** | Separate data, calculation, simulation, display | **Partial Violation**. `run_premier_league_simulation()` in `26-27-season.py` (lines 453–533) combines setup, Monte Carlo execution, probability calculations, AND console printing. | Extract formatting and printing into a dedicated `display_results()` function. |
| **Rule 4: Function Size** | Preferred 10–40 lines, Max 60 lines | **Violation**. `run_premier_league_simulation()` is ~81 lines long. `run_single_pl_simulation()` is ~81 lines long. | Refactor large orchestrator functions into smaller helper functions. |
| **Rule 9: Type Hints** | Typed parameters & return values on public functions | **Partial Violation**. Functions like `markets_to_latent_elo()` and `_parse_locked_scores()` lack full type annotations for complex returns. | Add complete type annotations across all modules. |
| **Rule 13 & 18: Global State** | Avoid mutable global variables | **Violation**. `26-27-season.py` uses mutable global `TEAM_EUROPE_STATUS` (lines 291, 462). | Pass `TEAM_EUROPE_STATUS` as an explicit parameter into `run_single_pl_simulation()`. |
| **Rule 25: Numba** | JIT only on numeric hot paths | **Compliant**. Numba is not used. | Remove `numba` from `README.md` and `requirements.txt`. |

---

## 4. Proposed Updated Documentation Text

Below is the proposed, production-ready `README.md` text that accurately reflects the Premier League 2026/27 Simulation Suite.

```markdown
# Premier League 2026/27 Simulation Suite

An integrated Monte Carlo simulation suite for predicting Premier League 2026/27 outcomes alongside UEFA Champions League (UCL) and UEFA Europa League (UEL) tournament projections.

## Overview

The Premier League 2026/27 Simulation Suite uses betting market implied probabilities to derive latent team Elo ratings, models match outcomes using Poisson goal sampling, simulates 36-team European Swiss-model competitions, and applies domestic European fatigue adjustments to project full season standings.

### Key Features

- **Latent Market Elo Derivation**: Automatically calculates team Elo ratings from fractional odds across multiple betting markets (League Winner, Top 2 Finish, Relegation).
- **Integrated European Simulations**: Runs full 36-team Swiss-model league phase and knockout stage simulations for UEFA Champions League (`UCL.py`) and UEFA Europa League (`UEL.py`).
- **European Fatigue Penalties**: Adjusts domestic Elo ratings based on European competition involvement (UCL: -45 Elo, UEL: -30 Elo, UECL: -20 Elo).
- **Poisson Goal Modeling**: Uses exponential Elo scaling to compute expected goals ($\text{xG}$) and samples match scores from cached Poisson distributions.
- **Mid-Season Played Match Locking**: Supports pre-populating actual played match results (`ACTUAL_RESULTS`) to simulate remaining fixtures from mid-season states.
- **Monte Carlo Projection Table**: Outputs projected average points, standard deviation, title probability, Top 4 (UCL), Europa League qualification, top half, relegation, and European cup winning probabilities.

---

## File Structure

```
sportsanalysis/premier-league/
├── 26-27-season.py       # Main entry point & Premier League Monte Carlo engine
├── UCL.py                # UEFA Champions League 36-team Swiss model & knockout simulator
├── UEL.py                # UEFA Europa League 36-team Swiss model & knockout simulator
├── test_integration.py   # Integration test suite for simulation pipeline
└── README.md             # Suite documentation
```

---

## Installation & Setup

### Prerequisites
Python 3.10+ with standard packages.

### Dependencies
Install required packages:
```bash
pip install numpy tqdm rich pandas
```

---

## Usage

### Running the Full Simulation Suite
Execute the main script from the `sportsanalysis/premier-league/` directory:
```bash
python 26-27-season.py
```

Execution flow:
1. **Champions League Simulation (`UCL.py`)**: Runs 2,000 simulations of the UCL Swiss model and knockout phase to determine PL teams' CL winning probabilities.
2. **Europa League Simulation (`UEL.py`)**: Runs 2,000 simulations of the UEL Swiss model and knockout phase to determine PL teams' UEL winning probabilities.
3. **Premier League Simulation (`26-27-season.py`)**: Derives market Elo ratings, applies European fatigue penalties, and executes 2,000 Monte Carlo simulations of remaining fixtures.

### Running Standalone European Simulations
You can also run Champions League or Europa League simulations independently:
```bash
python UCL.py
python UEL.py
```

---

## Technical Architecture & Mathematical Model

### 1. Market Implied Latent Elo (`markets_to_latent_elo`)
Base Elo ratings are derived from betting market odds in `PL_BETTING_MARKETS`:
1. Fractional odds $(a, b)$ are converted to implied probabilities: $P = \frac{b}{a + b}$.
2. Probabilities are normalized and converted to log-space relative to the mean.
3. Centered ratings are scaled ($\text{scale} = \frac{400}{\ln 10}$) and shrunk (`ELO_SHRINKAGE = 0.75`) around `LEAGUE_AVERAGE_ELO` (1500.0).

### 2. Match Expected Goals & Poisson Sampling
Expected goals ($\text{xG}$) for home ($h$) and away ($a$) teams are calculated as:
$$\text{xG}_h = \text{BASE\_HOME\_XG} \times e^{\text{XG\_ELO\_SENSITIVITY} \times (\text{Elo}_h + \text{HOME\_ADVANTAGE\_ELO} - \text{Elo}_a)}$$
$$\text{xG}_a = \text{BASE\_AWAY\_XG} \times e^{-\text{XG\_ELO\_SENSITIVITY} \times (\text{Elo}_h + \text{HOME\_ADVANTAGE\_ELO} - \text{Elo}_a)}$$

Where:
- `BASE_HOME_XG` = 1.5, `BASE_AWAY_XG` = 1.2
- `HOME_ADVANTAGE_ELO` = 85.0
- `XG_ELO_SENSITIVITY` = 0.002

Goal totals are sampled from cached Poisson distributions ($\text{MAX\_GOALS} = 10$).

### 3. European Fatigue Adjustments
Domestic Elo ratings are reduced based on European status before fixture simulation:
- **UCL Teams** (Arsenal, Aston Villa, Liverpool, Man City, Man United): $-45.0$ Elo
- **UEL Teams** (Bournemouth, Sunderland, Crystal Palace): $-30.0$ Elo

---

## Console Output Example

```
====================================================================================================
FINAL PREMIER LEAGUE PROJECTIONS (With CL Fatigue Adjustments)
====================================================================================================
Pos   Team                  Eur   ELO     Pts     SD     Title   UCL     Europa   TopHalf  StayUp   Releg
----------------------------------------------------------------------------------------------------
1.42  Arsenal               UCL   1625.4  84.12   6.21   52.40   94.10   4.20     100.00   100.00   0.00     (CL Win: 14.2%)
2.15  Man City              UCL   1612.0  80.45   6.85   31.20   88.50   7.80     100.00   100.00   0.00     (CL Win: 11.5%)
...
```

---

## Configuration & Customization

Key constants in `26-27-season.py`:
- `NUM_PL_SIMS`: Number of Monte Carlo iterations (default: `2000`).
- `EUROPEAN_PENALTIES`: Elo penalties for UCL, UEL, UECL participation.
- `ACTUAL_RESULTS`: Dictionary mapping `(Home, Away)` tuples to actual match scores `(HomeGoals, AwayGoals)`.

---

## Verification & Testing

Run integration tests using `pytest`:
```bash
pytest sportsanalysis/premier-league/test_integration.py
```
```

---

## Conclusion & Actionable Next Steps

1. **Update `README.md` Files**: Replace outdated claims in root `README.md` and `sportsanalysis/premier-league/README.md` with the proposed updated text above.
2. **Clean Up Unused Dependencies**: Remove `numba` from root `requirements.txt` to eliminate user confusion.
3. **Refactor Code for Standards Compliance**:
   - Refactor `run_premier_league_simulation()` in `26-27-season.py` to separate simulation execution from console output formatting (`instructions.md` Rules 3, 17).
   - Eliminate global mutable variable `TEAM_EUROPE_STATUS` (`instructions.md` Rule 18).
