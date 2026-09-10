# Documentation Audit Report: Premier League 2026-27 Simulation Suite

**Auditor:** Senior Technical Writer & Software Documentation Auditor
**Target Codebase:** `sportsanalysis/premier-league/26-27-season.py`
**Target Documentation:** Repo Root `README.md` and `sportsanalysis/premier-league/README.md`
**Date:** September 2026

---

## Executive Summary

A comprehensive code and documentation audit was conducted for the **Premier League 2026-27 Simulation Engine** (`sportsanalysis/premier-league/26-27-season.py`). The audit evaluated whether current project documentation (`README.md` at repo root and `sportsanalysis/premier-league/README.md`) accurately reflects the actual implementation, parameters, return values, side effects, algorithm design, and dependencies.

The current code in `26-27-season.py` represents a refactored, unified Monte Carlo simulation model integrating European competitions (UEFA Champions League, Europa League, and Conference League) directly with Premier League season simulation and dynamic fatigue decay. However, the documentation currently in place either describes an outdated 2025-26 season script or references legacy features (e.g., form adjustments, injury penalties, WDL bias, Championship playoff coin flips) that have been completely removed or replaced in the 2026-27 refactor.

---

## 1. Mismatches & Discrepancies

### A. Core Architecture & Features

1. **Simulation Iterations:**
   - **Documentation (`README.md` & `sportsanalysis/premier-league/README.md`):** States that the simulation runs 10,000 or 25,000 iterations.
   - **Code (`26-27-season.py`, Line 24):** Configured with `NUM_PL_SIMS = 2000` unified simulations per run.

2. **Power Ratings & Market Integration:**
   - **Documentation:** Asserts that base Elo ratings are manually assigned and subsequently adjusted for form (last 10 games), injury scale reductions, and WDL bias rates.
   - **Code (`26-27-season.py`, Lines 456-508):** Derives latent Elo ratings dynamically from betting markets (`PL_BETTING_MARKETS`) using weighted log-probability centering (`markets_to_latent_elo`). Form, injury, and WDL adjustments are completely omitted.

3. **Promoted Teams & Championship Playoff Logic:**
   - **Documentation:** Mentions Championship playoff simulation and flat penalties for promoted teams.
   - **Code (`26-27-season.py`, Refactor Note & Lines 456-508):** Promoted teams receive market-derived Elo directly from betting odds without flat penalties or Championship playoff coin-flip simulations.

4. **European Competitions Integration & Fatigue Modeling:**
   - **Documentation:** Describes standalone European competition scripts or static pre-computed win probabilities without active fatigue coupling.
   - **Code (`26-27-season.py`, Lines 190-252, 258-335):** Features modular OOP classes (`EuropeanCompetition` for UCL, UEL, UECL) executed synchronously inside each Monte Carlo loop. Applied European fatigue (`EUROPEAN_FATIGUE_BASE`, Lines 31-32) decays linearly over the season (`1.0 - progress`) and applies only while a team remains active in knockout stages (`elim_round >= 0`).

5. **Champions League Qualification Rules:**
   - **Documentation:** Claims basic position-based European assignment (Top 4 → CL, 5th → EL, 6th → UECL).
   - **Code (`26-27-season.py`, Lines 542-559):** Dynamically evaluates conditional UCL qualification. If an English team wins the UCL or UEL and finishes outside the top 4, they qualify for the Champions League alongside the 5th-place Premier League team (`fifth_place_ucl_counts`).

6. **Match Engine & Goal Modeling:**
   - **Documentation:** References complex XG adjustments including closeness factors, tempo reductions, win-rate variance boosts, and bivariate Poisson draw boosts.
   - **Code (`26-27-season.py`, Lines 63-68):** Uses an exponential expected goals formula (`compute_expected_goals`):
     $$\text{XG}_{\text{home}} = \text{BASE\_HOME\_XG} \times e^{\text{XG\_ELO\_SENSITIVITY} \times \Delta\text{Elo}}$$
     Goals are sampled using pre-cached independent Poisson PMF lookups (`_poisson_pmf`, `sample_score`).

7. **Tiebreakers:**
   - **Documentation:** Claims tiebreakers are ordered Points → Goal Difference → Goals For.
   - **Code (`26-27-season.py`, Lines 239-243 & 328-332):** Tiebreakers are calculated as Points → Goal Difference → Goals For → Random Uniform Tiebreaker (`_NP_RNG.uniform(0, 0.0001)`).

---

### B. Output Format Mismatches

- **Documentation Claims:** Promises match-level probabilities, extreme match outcome tables (most likely home wins, draws, away wins), fixture difficulty tables, and excitement score metrics.
- **Actual Code Output (`26-27-season.py`, Lines 600-620):** Outputs a formatted summary table displaying:
  - `Pos` (Average Projected Position)
  - `Team`
  - `Eur` (European Competition Code: UCL, UEL, UECL, or `-`)
  - `ELO` (Market-Derived Base Elo)
  - `Pts` (Average Points)
  - `SD` (Standard Deviation of Points)
  - `95%CI` (95% Confidence Interval for Points)
  - `Title%` (League Title Probability)
  - `UCLQ%` (Champions League Qualification Probability)
  - `5th->UCL%` (Probability 5th Place qualifies for CL)
  - `UCLWin%`, `UELWin%`, `UECLWin%` (Individual European Trophy Win Probabilities)
  - `AnyEuroWin%` (Combined European Trophy Win Probability)

---

### C. Missing Parameter & Return Value Specifications

1. **`compute_expected_goals(elo_home: float, elo_away: float) -> Tuple[float, float]`**
   - **Parameters:** `elo_home` (float, home team Elo rating including home advantage), `elo_away` (float, away team Elo rating).
   - **Returns:** `(xg_home, xg_away)` tuple of float expected goals values.
   - **Side Effects:** None. Pure mathematical calculation.

2. **`simulate_two_legged_tie(team1: str, team2: str, elos: Dict[str, float]) -> str`**
   - **Parameters:** `team1`, `team2` (team name strings), `elos` (dictionary mapping team names to Elo ratings).
   - **Returns:** `str` (winning team name string).
   - **Side Effects:** Mutates global `_RNG` and `_NP_RNG` state when sampling scores, extra-time goals, and penalty shootouts.

3. **`simulate_knockout_phase(qualified: List[str], elos: Dict[str, float]) -> Tuple[Optional[str], Dict[str, int]]`**
   - **Parameters:** `qualified` (List of 24 qualified team names ordered by league phase rank), `elos` (dictionary of Elo ratings).
   - **Returns:** Tuple `(winner_name, elimination_rounds)` where `elimination_rounds` maps team names to integer elimination round indicators (`-1`: unqualified, `0`: playoff loss, `1`: R16, `2`: QF, `3`: SF, `4`: finalist, `5`: winner).

4. **`EuropeanCompetition.simulate() -> Tuple[Optional[str], Dict[str, int]]`**
   - **Parameters:** None.
   - **Returns:** Tuple `(winner, elimination_rounds)` mapping competition progress across league phase and knockouts.

5. **`PLSimulator.simulate_season(fatigue_info: Dict[str, Tuple[int, str]]) -> Tuple[List[str], Dict[str, int]]`**
   - **Parameters:** `fatigue_info` (dictionary mapping PL team names to `(elimination_round, competition_name)` tuples).
   - **Returns:** Tuple `(ranked_teams, points_dict)` detailing end-of-season league standings and total accumulated points.

---

### D. Dependencies & Prerequisites

- **Documentation Claim:** Lists `numba` as a core JIT dependency.
- **Actual Code Need:** `numba` is not imported or used in `26-27-season.py`. The required runtime dependencies are `numpy`, `tqdm`, and Python standard library modules (`math`, `random`, `logging`, `collections`, `typing`).

---

## 2. Suggested Clarifications & Improvements

1. **Unified Architecture Explanation:** Clearly document that `26-27-season.py` is a standalone, refactored single-file engine. Explain how European competitions and Premier League fixtures run synchronously per iteration.
2. **Latent Market Elo Derivation:** Document the `markets_to_latent_elo` function. Explain how betting odds for League Winner, Top 2, and Relegation markets are converted to implied probabilities and mapped to centered Elo ratings around a 1500 baseline.
3. **Dynamic Fatigue Model:** Explain the fatigue calculation formula:
   $$\text{Penalty} = \text{EUROPEAN\_FATIGUE\_BASE}[\text{comp}] \times \left(1 - \frac{i}{N_{\text{fixtures}} - 1}\right)$$
   Emphasize that the penalty only applies to teams actively competing in European knockout rounds (`elim_round >= 0`).
4. **Conditional European Spots:** Clarify the logic governing 5th-place UCL qualification when English clubs win UEFA competitions.

---

## 3. Proposed Updated Documentation Text

Below is the proposed, fully aligned replacement text for `sportsanalysis/premier-league/README.md` and repo root documentation regarding the 2026-27 simulation engine.

```markdown
# Premier League 2026-27 Unified Monte Carlo Simulation

## Overview
`sportsanalysis/premier-league/26-27-season.py` is an integrated, refactored Monte Carlo simulation engine that projects Premier League 2026-27 season outcomes alongside UEFA European competitions (Champions League, Europa League, Conference League).

The engine uses market-derived latent Elo ratings, Poisson expected goal modeling, dynamic European fatigue decay, and realistic UEFA conditional qualification rules.

---

## Core Features & Methodology

### 1. Market-Derived Latent Elo Ratings
Base team Elo ratings are dynamically computed from betting markets (`League Winner`, `Top 2 Finish`, and `Relegation`). The function `markets_to_latent_elo()` converts fractional betting odds into implied probabilities, centers them relative to a 1500 baseline, and scales ratings to reflect true market expectations without arbitrary promoted-team penalties.

### 2. Integrated European Competitions (`EuropeanCompetition`)
Each simulation iteration synchronously models all three major UEFA competitions:
- **League Phase:** 8-matchday league phase using team Elo ratings and Poisson goal generation.
- **Knockout Phase:** 24-team knockout phase (playoffs, Round of 16, Quarter-finals, Semi-finals, and Final) with two-legged ties, extra time, and penalty shootouts.
- **Elimination Tracking:** Returns detailed elimination round metadata (`-1` to `5`) used to determine Premier League fatigue.

### 3. Dynamic European Fatigue Modeling
Premier League teams active in European competition suffer a fatigue penalty applied to their base Elo:
- Base fatigue penalties: UCL = -8.0 Elo, UEL = -6.0 Elo, UECL = -5.0 Elo.
- Fatigue decays linearly over the 380-fixture domestic season ($1 - \text{progress}$).
- Teams eliminated from European competitions no longer incur fatigue penalties.

### 4. Conditional Champions League Qualification
Implements realistic UEFA qualification rules:
- Top 4 Premier League teams automatically qualify for the Champions League.
- If an English team wins the UCL or UEL and finishes outside the top 4, they qualify for the UCL.
- Under UEFA performance/winner allocation rules, an additional 5th-place spot (`5th->UCL%`) is awarded when applicable.

---

## Match Simulation & Poisson Goal Engine

Expected goals (XG) for any fixture are calculated as:
$$\text{XG}_{\text{home}} = \text{BASE\_HOME\_XG} \times e^{\text{XG\_ELO\_SENSITIVITY} \times (\text{Elo}_{\text{home}} + \text{HOME\_ADVANTAGE} - \text{Fatigue}_{\text{home}} - \text{Elo}_{\text{away}})}$$
$$\text{XG}_{\text{away}} = \text{BASE\_AWAY\_XG} \times e^{-\text{XG\_ELO\_SENSITIVITY} \times (\text{Elo}_{\text{home}} + \text{HOME\_ADVANTAGE} - \text{Fatigue}_{\text{home}} - \text{Elo}_{\text{away}})}$$

Key parameters:
- `HOME_ADVANTAGE_ELO`: +85.0 Elo points
- `BASE_HOME_XG`: 1.5
- `BASE_AWAY_XG`: 1.2
- `XG_ELO_SENSITIVITY`: 0.002

Goals are sampled using Poisson probability mass functions with lookups cached in `_POISSON_CACHE`. Locked real-world match outcomes in `ACTUAL_RESULTS` overwrite simulated scores for completed fixtures.

---

## Execution & Output Format

### Installation Dependencies
Install required packages:
```bash
pip install numpy tqdm
```

### Running the Simulation
Execute the script from the repository root:
```bash
python sportsanalysis/premier-league/26-27-season.py
```

### Output Table Specification
The simulation generates a console summary table across 2,000 unified iterations:

| Column | Description |
| :--- | :--- |
| `Pos` | Average projected league finishing position |
| `Team` | Club name |
| `Eur` | Active European competition (UCL, UEL, UECL, or `-`) |
| `ELO` | Market-derived initial base Elo rating |
| `Pts` | Projected average season points |
| `SD` | Standard deviation of accumulated points |
| `95%CI` | 95% Confidence Interval for projected points |
| `Title%` | Probability of winning the Premier League title |
| `UCLQ%` | Total probability of Champions League qualification |
| `5th->UCL%` | Probability of 5th-place team securing UCL spot via winner rules |
| `UCLWin%` | Probability of winning the UEFA Champions League |
| `UELWin%` | Probability of winning the UEFA Europa League |
| `UECLWin%` | Probability of winning the UEFA Conference League |
| `AnyEuroWin%` | Combined probability of winning any European trophy |
```
