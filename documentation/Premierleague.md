# Premier League 2026/27 Simulation Suite — Documentation Audit Report

**Auditor Persona:** Senior Technical Writer and Software Documentation Auditor
**Scope of Review:** `sportsanalysis/premier-league/26-27-season.py`, `sportsanalysis/premier-league/UCL.py`, `sportsanalysis/premier-league/UEL.py`, `sportsanalysis/premier-league/README.md`, and repository root `README.md`.

---

## 1. Code-Documentation Mismatches

### 1.1 Season Scope and Iteration Counts
* **Code Implementation:**
  * `26-27-season.py` targets the **2026/27 season** and defines `NUM_PL_SIMS = 2000` (line 27).
  * `UCL.py` defines `NUM_CL_SIMS = 2000` (line 25).
  * `UEL.py` defines `NUM_UEL_SIMS = 2000` (line 546).
* **Documentation Claims:**
  * `sportsanalysis/premier-league/README.md` refers to the **2025-26 season** and claims the simulation runs 25,000 iterations for Premier League and 10,000 iterations for European competitions.
  * Root `README.md` states the simulation runs 10,000 simulations grouped by promoted team.
* **Impact:** Outdated documentation misinforms users regarding execution scale, target season, and runtime expectations.

### 1.2 Rating Generation: Latent Elo from Betting Markets vs. Fixed Hardcoded Ratings
* **Code Implementation:**
  * In `26-27-season.py`, base Elo ratings are dynamically derived from fractional odds in `PL_BETTING_MARKETS` (lines 310–332) via `markets_to_latent_elo()` (lines 351–392), incorporating weighted market probabilities ("League Winner", "Top 2 Finish", "Relegation") and Elo shrinkage (`ELO_SHRINKAGE = 0.75`).
  * In `UCL.py` (lines 142–167) and `UEL.py` (lines 89–131), Elo ratings for European teams are similarly computed from betting odds (`calculate_cl_elos` and `calculate_elo_ratings`).
* **Documentation Claims:**
  * `sportsanalysis/premier-league/README.md` claims Elo ratings are hardcoded base scores (lines 8–28) with Rating Deviations (RDs, lines 31–52), form adjustments (lines 396–417), WDL rates, and injury penalties (lines 444–466).
  * Root `README.md` lists form adjustments and injury penalties as active features.
* **Impact:** Features described in documentation (injury penalties, form multipliers, RD) are either unused or non-existent in the 2026/27 codebase, while the market-implied latent Elo algorithm is completely undocumented.

### 1.3 Expected Goals (XG) Model & Goal Sampling
* **Code Implementation:**
  * In `UCL.py`, `compute_expected_goals(elo_home, elo_away)` (lines 68–73) uses exponential scaling:
    $$\text{XG}_{\text{home}} = \text{BASE\_HOME\_XG} \times \exp(\text{XG\_ELO\_SENSITIVITY} \times \Delta\text{Elo})$$
    $$\text{XG}_{\text{away}} = \text{BASE\_AWAY\_XG} \times \exp(-\text{XG\_ELO\_SENSITIVITY} \times \Delta\text{Elo})$$
    with `BASE_HOME_XG = 1.5`, `BASE_AWAY_XG = 1.2`, and `XG_ELO_SENSITIVITY = 0.002`.
  * Score outcomes in `sample_score()` (lines 56–65) are sampled independently from truncated Poisson PMFs (`_poisson_pmf()`, lines 44–54).
* **Documentation Claims:**
  * `sportsanalysis/premier-league/README.md` claims the match engine uses logistic scaling ($\text{home\_xg} = 0.7 + 1.8 / (1 + \exp(-\text{diff}/400))$), WDL bias, closeness factors, tempo reduction, variance boosts, and a Bivariate Poisson distribution with shared lambda for draw correlation.
* **Impact:** The documented goal model is fundamentally different from the actual implementation.

### 1.4 European Tournament Structure & Qualification Integration
* **Code Implementation:**
  * `UCL.py` implements the 36-team UEFA Champions League Swiss-model phase with 8 rounds generated via `generate_swiss_fixtures` (lines 197–232), playoff ties (`LIVE_PLAYOFF_TIES`, lines 94–99), a knockout round playoff (teams 9–24), and single-elimination knockout stages (`simulate_knockout_phase`, lines 277–352).
  * `UEL.py` implements a parallel 36-team Swiss-model simulation (`EuropaLeagueSwissModel`, `run_europa_league_simulation`).
  * `26-27-season.py` imports and runs `run_champions_league_simulation()` and `run_europa_league_simulation()` in `main()` (lines 538–547), using probabilities to calculate CL/UEL winner overlays and European fatigue penalties (`EUROPEAN_PENALTIES = {"UCL": 45.0, "UEL": 30.0, "UECL": 20.0}`, lines 29–33).
* **Documentation Claims:**
  * `sportsanalysis/premier-league/README.md` describes fixed 2025-26 two-leg ties (e.g. Aston Villa vs Nottingham Forest in UEL, PSG vs Bayern in CL) simulated once before the main loop, without Swiss-model phases or dynamic integration.
  * Root `README.md` describes European qualification as a static mapping based purely on league position without multi-tournament integration.
* **Impact:** European fatigue penalties and Swiss-model tournament structures are major features present in the code but entirely omitted from documentation.

### 1.5 Unfulfilled Output Features
* **Code Implementation:**
  * `26-27-season.py` prints a single summary table (`FINAL PREMIER LEAGUE PROJECTIONS`, lines 489–531) containing Position, Team, European status, Base Elo, Avg Points, SD, Title %, UCL %, Europa %, TopHalf %, StayUp %, Releg %, and CL/UEL win probabilities.
* **Documentation Claims:**
  * Both `README.md` files describe detailed outputs including fixture-by-fixture match probabilities (10,000 sims per match), extreme match probabilities (most likely home wins, draws, away wins), team fixture probabilities, FA Cup winner simulation, points to win the league, and season excitement scores.
* **Impact:** Users looking for match-level output tables or FA Cup simulations will find no such functionality in `26-27-season.py`.

---

## 2. Suggested Clarifications

1. **Latent Elo Rating Derivation from Betting Markets:**
   * Explain how fractional odds (e.g., 4/5, 5/2) are converted to implied probabilities ($p = \text{denominator} / (\text{numerator} + \text{denominator})$), normalized to remove bookmaker overround, centered, and scaled using `ELO_SCALE` (400.0) and `ELO_SHRINKAGE` (0.75).
2. **European Fatigue Penalty Concept:**
   * Clarify that teams competing in European tournaments receive an Elo deduction (`UCL`: -45.0, `UEL`: -30.0, `UECL`: -20.0) in Premier League match calculations (`run_single_pl_simulation()`) to model squad rotation and fatigue.
3. **Poisson Expected Goals (XG) Model:**
   * Clarify that match goals are modeled using independent Poisson distributions parameterized by team Elo differences, replacing outdated descriptions of Bivariate Poisson models.
4. **Swiss-Model Tournament Format:**
   * Provide explicit context on the 36-team Swiss-model league phase used in Champions League (`UCL.py`) and Europa League (`UEL.py`), including 8-match fixture scheduling and 24-team playoff/knockout qualification.

---

## 3. Proposed Updated Documentation Text

Below is the updated `README.md` for `sportsanalysis/premier-league/`.

```markdown
# Premier League & European Competitions 2026/27 Simulation Suite

## Overview
This Python simulation suite models the **2026/27 Premier League season** alongside the **UEFA Champions League (UCL)** and **UEFA Europa League (UEL)**. It uses betting market odds to derive latent Elo ratings, models match outcomes via Poisson distributions, applies European fatigue penalties to domestic fixtures, and executes Monte Carlo simulations to project league standings and continental champions.

## Architecture & Workflow

1. **UEFA Champions League Simulation (`UCL.py`)**:
   - Calculates latent Elo ratings for 36 qualified/playoff teams from betting odds.
   - Simulates remaining live playoff ties (`LIVE_PLAYOFF_TIES`).
   - Generates an 8-round Swiss-model league phase schedule (`generate_swiss_fixtures`).
   - Simulates league phase matches and 24-team knockout stages to compute CL winning probabilities (`run_champions_league_simulation`).

2. **UEFA Europa League Simulation (`UEL.py`)**:
   - Runs a parallel Swiss-model and knockout phase simulation for UEL teams (`run_europa_league_simulation`).

3. **Premier League Simulation (`26-27-season.py`)**:
   - Converts betting market odds (League Winner, Top 2 Finish, Relegation) into base Elo ratings (`markets_to_latent_elo`).
   - Applies European fatigue deductions: UCL (-45 Elo), UEL (-30 Elo), UECL (-20 Elo).
   - Incorporates actual played results (`ACTUAL_RESULTS`) and simulates remaining fixtures (`FIXTURES_LIST`) across 2,000 Monte Carlo iterations.
   - Computes statistical distributions for standings, European qualification, relegation, and overlay probabilities for UCL/UEL titles.

## Mathematical Model

### 1. Market-Implied Latent Elo
Betting odds are converted to implied probabilities:
$$P = \frac{\text{Denominator}}{\text{Numerator} + \text{Denominator}}$$

Probabilities across markets are normalized, log-transformed, centered, and converted to Elo ratings:
$$\text{Elo}_{\text{raw}} = \text{LEAGUE\_AVERAGE\_ELO} + \left(\frac{400}{\ln(10)}\right) \times \text{LatentStrength}$$
$$\text{Elo}_{\text{final}} = \text{LEAGUE\_AVERAGE\_ELO} + \text{ELO\_SHRINKAGE} \times (\text{Elo}_{\text{raw}} - \text{LEAGUE\_AVERAGE\_ELO})$$
*(Constants: `LEAGUE_AVERAGE_ELO = 1500.0`, `ELO_SHRINKAGE = 0.75`)*

### 2. Expected Goals (XG) & Score Sampling
Match XG is computed using exponential Elo sensitivity:
$$\text{XG}_{\text{home}} = 1.5 \times \exp\left(0.002 \times (\text{Elo}_{\text{home}} + 85.0 - \text{Elo}_{\text{away}})\right)$$
$$\text{XG}_{\text{away}} = 1.2 \times \exp\left(-0.002 \times (\text{Elo}_{\text{home}} + 85.0 - \text{Elo}_{\text{away}})\right)$$
*(Constants: `HOME_ADVANTAGE_ELO = 85.0`)*

Goals are sampled independently from Poisson distributions using cached probability mass functions (`_poisson_pmf`).

## Output Parameters & Summary Table

The simulation outputs a comprehensive projection table:
- **Pos**: Projected average league finishing position.
- **Team**: Premier League club name.
- **Eur**: European competition status (`UCL`, `UEL`, `UECL`, or `-`).
- **ELO**: Derived base Elo rating.
- **Pts**: Projected average season points.
- **SD**: Standard deviation of season points.
- **Title %**: Probability of winning the Premier League title (1st place).
- **UCL %**: Probability of finishing in the top 4 (Champions League qualification).
- **Europa %**: Probability of finishing 5th (Europa League qualification).
- **TopHalf %**: Probability of finishing in positions 1–10.
- **StayUp %**: Probability of avoiding relegation (positions 1–17).
- **Releg %**: Probability of relegation (positions 18–20).
- **CL/UEL Win %**: Overall probability of winning the Champions League or Europa League.

## Usage

### Prerequisites
Install required dependencies:
```bash
pip install numpy tqdm
```

### Execution
Run the full simulation pipeline:
```bash
python sportsanalysis/premier-league/26-27-season.py
```

To run individual European simulation modules independently:
```bash
python sportsanalysis/premier-league/UCL.py
python sportsanalysis/premier-league/UEL.py
```
```
