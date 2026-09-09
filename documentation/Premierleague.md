# Documentation Audit Report: Premier League 2026/27 Simulation Suite

## 1. Overview
This report provides a comprehensive documentation audit of the Premier League 2026/27 simulation codebase (`sportsanalysis/premier-league/26-27-season.py`) in comparison with the repository's root `README.md`.

---

## 2. Code vs. Documentation Discrepancies & Mismatches

### A. Non-Existent Features Claimed in Documentation
1. **Form, Injury, and Win/Draw/Loss Bias Adjustments**
   - **Documentation Claim**: The `README.md` states under "Algorithm Overview" and "Features" that team ratings are adjusted for form, injuries, and WDL (Win/Draw/Loss) tendencies.
   - **Code Reality**: In `26-27-season.py`, Elo ratings are strictly calculated from betting market odds via `markets_to_latent_elo()` (lines 433–478). Form bonuses, injury penalties, and WDL bias factors are not present in the script or match engine.

2. **Championship Playoff Simulation**
   - **Documentation Claim**: The `README.md` describes a "Championship Playoff Simulation" that simulates Championship playoffs to determine promoted teams.
   - **Code Reality**: The script `26-27-season.py` defines a fixed 20-team Premier League field directly within `FIXTURES_LIST` (lines 173–311) and `PL_BETTING_MARKETS` (lines 314–341). There is no Championship playoff simulation or variable promoted team logic.

3. **Match Probabilities & Detailed Fixture Statistics**
   - **Documentation Claim**: Under "Output", the documentation lists tables for "Match Probabilities", "Extreme Match Probabilities", "Team Fixture Probabilities", and "Points to Win League".
   - **Code Reality**: In `run_unified_simulation()` (lines 480–601), the console output produces a single summary table containing position, average points, standard deviation, 95% confidence intervals, Title%, UCLQ%, 5th->UCL%, UCLWin%, UELWin%, UECLWin%, and AnyEuroWin%. Individual match/fixture probability tables are not generated.

4. **Excitement Score & 40+ Points Relegation Statistics**
   - **Documentation Claim**: Documentation mentions "average excitement score" and "probability of relegation with 40+ points".
   - **Code Reality**: Neither calculation exists in `26-27-season.py`.

5. **Simulation Iteration Count**
   - **Documentation Claim**: `README.md` states "Runs 10,000 simulations grouped by promoted team."
   - **Code Reality**: `NUM_PL_SIMS` is set to `2000` (line 30). Simulations run as unified iterations of European competitions and PL matches, not grouped by promoted team.

6. **Dependency Misalignment (`numba`)**
   - **Documentation Claim**: Dependencies list `numba` for JIT compilation.
   - **Code Reality**: `26-27-season.py` does not import or use `numba`. It uses standard `numpy`, `math`, `random`, and `tqdm`.

---

### B. Implemented Features Missing from Documentation
1. **Integrated European Competitions (`EuropeanCompetition` Class)**
   - **Code Implementation**: Lines 142–224 implement the `EuropeanCompetition` class to simulate full 36-team, 8-matchday league phases and 24-team multi-round knockout brackets for UCL, UEL, and UECL.
   - **Documentation Gap**: The `README.md` describes European qualification as a static post-league assignment without mentioning that European competitions are simulated dynamically prior to the Premier League matches.

2. **Dynamic European Fatigue Decay Model**
   - **Code Implementation**: Lines 247–264 calculate a per-match fatigue penalty (`EUROPEAN_FATIGUE_BASE`, line 38) that linearly decays from 1.0 to 0.0 across the season for teams actively participating in European knockout stages.
   - **Documentation Gap**: Completely unmentioned in `README.md`.

3. **Latent Elo Derived from Multi-Market Betting Odds**
   - **Code Implementation**: `markets_to_latent_elo()` (lines 433–478) computes market efficiency weights across "League Winner", "Top 2 Finish", and "Relegation" betting markets, converting centered log-probabilities into baseline Elo ratings.
   - **Documentation Gap**: Unmentioned in `README.md`.

4. **Locked Actual Results (`ACTUAL_RESULTS`)**
   - **Code Implementation**: `ACTUAL_RESULTS` (lines 344–360) locks in real-world scores for early-season fixtures (e.g. Arsenal 3-0 Coventry), overriding simulated scorelines in `PLSimulator.simulate_season` (lines 250–252).
   - **Documentation Gap**: Unmentioned in `README.md`.

5. **Conditional 5th-Place Champions League Spot Allocation**
   - **Code Implementation**: Lines 524–541 check if an English team wins the UCL or UEL while finishing outside the top 4, granting an extra Champions League spot to 5th place in the league table (`5th->UCL%`).
   - **Documentation Gap**: The `README.md` claims static top-4 CL qualification without detailing conditional winner spots.

---

## 3. Suggested Clarifications & Technical Explanations

1. **Expected Goals (XG) & Match Simulation Model**
   - The match engine calculates expected goals using an exponential Elo differential formula:
     $$\text{xG}_{\text{home}} = 1.5 \times e^{0.002 \times (\text{Elo}_{\text{home}} + 85 - \text{Elo}_{\text{away}} - \text{Fatigue}_{\text{home}})}$$
     $$\text{xG}_{\text{away}} = 1.2 \times e^{-0.002 \times (\text{Elo}_{\text{home}} + 85 - \text{Elo}_{\text{away}} - \text{Fatigue}_{\text{away}})}$$
   - Scores are sampled from independent Poisson distributions parameterized by $\text{xG}_{\text{home}}$ and $\text{xG}_{\text{away}}$, truncated at `MAX_GOALS = 10`.

2. **Function Parameter & Return Value Reference**
   - `fractional_to_probability(odds_tuple: Tuple[int, int]) -> float`: Converts fractional odds $(a, b)$ into implied probability $b / (a + b)$.
   - `compute_expected_goals(elo_home: float, elo_away: float) -> Tuple[float, float]`: Takes home/away ratings and returns $(\text{xG}_{\text{home}}, \text{xG}_{\text{away}})$.
   - `simulate_two_legged_tie(team1: str, team2: str, elos: Dict[str, float]) -> str`: Simulates two-legged European knockout ties, handling aggregate scores, extra time xG, and penalty shootouts.
   - `EuropeanCompetition.simulate() -> Tuple[Optional[str], Dict[str, int]]`: Returns `(winner_team_name, elimination_rounds_dict)`.
   - `PLSimulator.simulate_season(fatigue_info: Dict[str, Tuple[int, str]]) -> Tuple[List[str], Dict[str, int]]`: Returns `(ranked_team_list, points_dict)`.

---

## 4. Proposed Updated Documentation

```markdown
# Premier League 2026-27 Season Simulation Suite

A refactored, Monte Carlo simulation engine that predicts Premier League outcomes integrated with UEFA Champions League (UCL), UEFA Europa League (UEL), and UEFA Conference League (UECL) competition pipelines.

## Features

- **Latent Elo Ratings**: Generates baseline team strength ratings derived from multi-market betting odds (Title, Top 2, Relegation) using market-efficiency weighting.
- **Integrated European Competitions**: Dynamically simulates 36-team league phases and multi-round two-legged knockout stages for UCL, UEL, and UECL.
- **Dynamic European Fatigue Decay**: Models team fixture congestion by applying European fatigue penalties that decay linearly across the season for active European contenders.
- **Locked Actual Fixture Results**: Supports locking in real-world match outcomes (`ACTUAL_RESULTS`) to anchor mid-season or early-season simulations.
- **Conditional UEFA Qualification**: Implements official UEFA qualification rules, granting additional Champions League spots to 5th place when an English club wins the UCL or UEL while finishing outside the top 4.
- **Poisson Match Engine**: Simulates goal scoring using exponential Elo-XG modeling and Poisson probability mass functions.

## Installation & Setup

1. Clone the repository.
2. Install required dependencies:
   ```bash
   pip install numpy tqdm pandas tabulate rich
   ```

## Usage

Run the unified simulation script:
```bash
python sportsanalysis/premier-league/26-27-season.py
```

By default, the script executes 2,000 unified iterations (`NUM_PL_SIMS = 2000`) combining European competition brackets with full 380-match Premier League seasons.

## Algorithm Overview

### 1. Market-Derived Latent Elo
Calculates baseline Elo ratings using centered log-probabilities from fractional betting odds across multiple markets, normalized to a baseline scale ($\text{Scale} = 400$).

### 2. European Simulation & Fatigue Model
Before each PL season iteration:
- Full league phases (8 matchdays) and knockout phases (Playoffs through Final) are simulated for UCL, UEL, and UECL.
- Active European teams incur competition-specific fatigue penalties (`UCL`: 8.0, `UEL`: 6.0, `UECL`: 5.0 Elo points) that decay linearly ($1 - \frac{\text{match\_index}}{\text{total\_matches}}$) over the season.

### 3. Match Engine
- **Home Advantage**: +85.0 Elo points applied to the home team.
- **Expected Goals**:
  - $\text{xG}_{\text{home}} = 1.5 \times \exp(0.002 \times \Delta\text{Elo})$
  - $\text{xG}_{\text{away}} = 1.2 \times \exp(-0.002 \times \Delta\text{Elo})$
- Goals are drawn using cached Poisson PMF tables.

### 4. Output Statistics
Outputs a consolidated table containing:
- **Pos / Pts / SD**: Mean finishing position, mean points, and standard deviation.
- **95% CI**: 95% Confidence interval for projected points.
- **Title% / UCLQ%**: Title win probability and Champions League qualification probability.
- **5th->UCL%**: Probability of 5th place securing Champions League entry via UCL/UEL winner qualification.
- **UCLWin% / UELWin% / UECLWin% / AnyEuroWin%**: European trophy win probabilities for Premier League clubs.
```
