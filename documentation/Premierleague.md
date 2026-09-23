# Documentation Audit Report: Premier League Simulation Suite

**Auditor:** Senior Technical Writer & Software Documentation Auditor
**Date:** September 2026
**Target Files:**
- Code: `sportsanalysis/premier-league/26-27-season.py`, `sportsanalysis/premier-league/UCL.py`, `sportsanalysis/premier-league/UEL.py`
- Current Documentation: `sportsanalysis/premier-league/README.md`
- Audit Report File: `documentation/Premierleague.md`

---

## 1. Mismatches & Discrepancies Between Code and Documentation

### 1.1. Season Target & General Architecture Mismatch
* **Documentation**: Focuses entirely on the **2025-26** Premier League season simulation (`25-26-season.py`).
* **Code Implementation**: The codebase now features the **2026-27** season pipeline (`26-27-season.py`), which integrates multi-file European competition modules (`UCL.py` and `UEL.py`).
* **Line References / Functions**:
  * `26-27-season.py`: Lines 1–418.
  * `UCL.py`: `run_champions_league_simulation()` (line 331).
  * `UEL.py`: `run_europa_league_simulation()` (line 616).

### 1.2. Simulation Iteration Counts & Execution Parameters
* **Documentation Claims**: Claims 25,000 iterations for the Premier League and 10,000 for each European competition.
* **Code Implementation**:
  * `26-27-season.py` sets `NUM_PL_SIMS = 2000` (line 28).
  * `UCL.py` sets `NUM_CL_SIMS = 2000` (line 23).
  * `UEL.py` sets `NUM_UEL_SIMS = 2000` (line 551).

### 1.3. Rating Methodology & Data Inputs
* **Documentation Claims**: Describes static base Elo ratings manually listed in `25-26-season.py` with RD (Rating Deviation) values, form adjustments (last 10 games), and injury penalties.
* **Code Implementation**:
  * `26-27-season.py` derives latent Elo ratings from betting market fractional odds (`PL_BETTING_MARKETS`, lines 183–204) via `markets_to_latent_elo()` (lines 222–267).
  * Unused / Missing in 2026-27 code: Injury penalties, form adjustments, WDL bias rates, and RD values are absent or unreferenced.
  * Promoted team penalties are handled via a baseline adjustment (`PROMOTED_TEAMS = {"Ipswich", "Coventry", "Hull"}`, line 348).

### 1.4. European Competitions Structure & Formats
* **Documentation Claims**: Describes European competitions as 2-leg knockout ties starting from semi-finals (e.g., Aston Villa vs Nottingham Forest in EL, PSG vs Bayern in CL) using old fixed structures.
* **Code Implementation**:
  * **UCL** (`UCL.py`): Implements the 36-team Swiss-model league phase (8 matches per team generated via `generate_swiss_fixtures`, line 211), preceded by live playoff tie resolution (`simulate_playoff_ties`, line 161) and followed by a full knockout phase (`simulate_knockout_phase`, line 269).
  * **UEL** (`UEL.py`): Implements `EuropaLeagueSwissModel` with 36 teams playing 8 matches (4 home, 4 away), playoff ties, and a full knockout bracket (`run_knockout_phase`, line 489).

### 1.5. Inter-Competition Coupling & Fatigue Side Effects
* **Documentation Claims**: States "European outcomes independent of PL results".
* **Code Implementation**:
  * `26-27-season.py` explicitly applies **European fatigue penalties** (`EUROPEAN_PENALTIES`, lines 30–34) to team Elo ratings prior to match simulation (`run_single_pl_simulation`, lines 289–299) based on participation in UCL (-45.0 Elo) or UEL (-30.0 Elo).
  * Global side effect variable `TEAM_EUROPE_STATUS` (line 217) is dynamically populated during `run_premier_league_simulation()` (lines 328–338).

### 1.6. Goal Modeling & Expected Goals (xG) Formulas
* **Documentation Claims**: Describes xG derived via logistic scaling `0.7 + 1.8 / (1 + exp(-diff/400))` and bivariate Poisson with shared lambda for correlated goals.
* **Code Implementation**:
  * `UCL.py` (`compute_expected_goals`, lines 82–87): Uses exponential Elo scaling:
    $$\text{home\_xg} = 1.5 \times e^{0.002 \times \text{elo\_diff}}$$
    $$\text{away\_xg} = 1.2 \times e^{-0.002 \times \text{elo\_diff}}$$
  * Goal sampling uses independent Poisson distributions truncated with precomputed PMF lookup tables (`sample_score`, lines 70–79, `_poisson_pmf`, lines 56–68).

### 1.7. Output Statistics & Reporting
* **Documentation Claims**: Describes detailed per-match probabilities, extreme match probabilities (highest win chances/draws), and team fixture probabilities.
* **Code Implementation**:
  * `26-27-season.py` outputs a combined summary table containing Average Position, Average Points, Standard Deviation, Title %, UCL %, Europa %, Top Half %, Stay Up %, Relegation %, and combined Champions League / Europa League win probabilities (`run_premier_league_simulation`, lines 392–410).
  * Per-match individual fixture outcome tables are not rendered by `26-27-season.py`.

---

## 2. Clarifications & Jargon Explanations

To ensure readability for both technical and non-technical stakeholders, the documentation must clarify the following domain terms and technical concepts:

1. **Latent Elo Rating from Betting Odds (`markets_to_latent_elo`)**:
   * *Clarification*: Market odds reflect aggregate bettor sentiment and bookmaker probabilities. The simulation converts fractional odds (e.g., `4/1`) into implied probabilities, removes bookmaker margin (overround), takes log-odds, centers them around a zero-mean baseline, scales by $400 / \ln(10)$, and applies shrinkage (`ELO_SHRINKAGE = 0.75`) towards the league average Elo (1500.0).
2. **Swiss-Model League Phase**:
   * *Clarification*: A non-elimination tournament format where 36 teams each play 8 distinct opponents (4 home, 4 away). Top 8 advance directly to the Round of 16; teams ranked 9th–24th compete in a 2-legged knockout playoff round.
3. **European Fatigue Penalty**:
   * *Clarification*: An Elo rating deduction applied to domestic match calculations to account for mid-week European travel and squad congestion (`UCL`: -45.0 Elo, `UEL`: -30.0 Elo, `UECL`: -20.0 Elo).
4. **Poisson PMF Pre-computation**:
   * *Clarification*: To accelerate Monte Carlo sampling, Poisson probability mass functions (PMF) are pre-calculated and cached in `_POISSON_CACHE` based on expected goal values ($\lambda$) rounded to two decimal places.

---

## 3. Updated Documentation Text

Below is the updated documentation text for `sportsanalysis/premier-league/README.md`.

```markdown
# Premier League & European Competitions 2026/27 Simulation Suite

## Overview
This suite simulates the 2026-27 Premier League season alongside full models for the UEFA Champions League (UCL) and UEFA Europa League (UEL). The pipeline integrates market-derived Elo ratings, Swiss-model European competition mechanics, European fatigue adjustments, and Monte Carlo methods to project domestic table standings, qualification probabilities, and European trophy winners.

## Suite Architecture & Execution Flow
1. **Champions League Simulation (`UCL.py`)**:
   - Converts betting market odds into latent Elo ratings.
   - Simulates remaining live playoff ties (including extra time and penalty probabilities).
   - Generates Swiss-model league phase fixtures (8 matches per team).
   - Simulates 2,000 iterations of the league phase and full knockout phase (Round of 16 through Final) to calculate UCL title win probabilities for Premier League teams.

2. **Europa League Simulation (`UEL.py`)**:
   - Derives Elo ratings and simulates remaining UEL playoff and CL drop-down ties.
   - Simulates 2,000 iterations of the 36-team Swiss-model league phase and knockout bracket.
   - Returns UEL title win probabilities for participating Premier League clubs.

3. **Premier League Simulation (`26-27-season.py`)**:
   - Derives latent Elo ratings from multi-market betting odds (`League Winner`, `Top 2 Finish`, `Relegation`).
   - Applies European fatigue deductions (`UCL`: -45 Elo, `UEL`: -30 Elo) to domestic Elo ratings.
   - Executes 2,000 Monte Carlo iterations across all 380 fixture slots (incorporating locked/actual results).
   - Outputs comprehensive season projections and cross-competition probabilities.

## Key Mathematical & Simulation Models

### 1. Latent Elo Derivation
Implied probabilities $P_i$ are calculated from fractional odds $(N:D)$ as $P_i = \frac{D}{N + D}$.
After normalizing probabilities across markets, log-probabilities are centered and scaled:
$$\text{Elo}_i = \text{LEAGUE\_AVERAGE\_ELO} + \left(\frac{400}{\ln 10}\right) \times \hat{z}_i$$
Shrinkage ($\gamma = 0.75$) is applied to pull extreme ratings toward the mean (1500.0).

### 2. Match Engine & Expected Goals (xG)
Expected goals for home ($H$) and away ($A$) teams are modeled exponentially based on Elo difference ($\Delta E = E_H + E_{\text{home\_adj}} - E_A$):
$$\lambda_{\text{home}} = 1.5 \times e^{0.002 \times \Delta E}$$
$$\lambda_{\text{away}} = 1.2 \times e^{-0.002 \times \Delta E}$$
Goals are sampled from Poisson distributions using cached PMF tables (`sample_score`).

### 3. Home Advantage & Fatigue Penalties
- **Home Advantage**: +85.0 Elo points (`HOME_ADVANTAGE_ELO`).
- **European Fatigue**:
  - UCL Participants: -45.0 Elo points
  - UEL Participants: -30.0 Elo points
  - UECL Participants: -20.0 Elo points

## Programmatic API Reference

### `UCL.py`
* `calculate_cl_elos() -> Dict[str, float]`: Converts `BETTING_MARKETS_CL_WINNER` fractional odds to Elo ratings.
* `compute_expected_goals(elo_home: float, elo_away: float) -> Tuple[float, float]`: Calculates $(\lambda_{\text{home}}, \lambda_{\text{away}})$.
* `run_champions_league_simulation(num_sims: int = 2000) -> Dict[str, float]`: Runs full UCL Monte Carlo simulation. Returns dictionary of `{team_name: win_percentage}`.

### `UEL.py`
* `EuropaLeagueSwissModel`: Class encapsulating UEL standings, fixtures, and knockout simulation logic.
* `run_europa_league_simulation(num_sims: int = 2000) -> Dict[str, float]`: Multi-simulation entry point for UEL.

### `26-27-season.py`
* `markets_to_latent_elo() -> Dict[str, float]`: Blends multi-market betting odds into base team Elo ratings.
* `run_single_pl_simulation(...) -> Tuple[Dict, List[Tuple[str, Dict]]]`: Simulates a single 380-match domestic season.
* `run_premier_league_simulation(cl_win_probs: Dict, uel_win_probs: Dict) -> None`: Orchestrates the simulation pipeline and prints final standings table.

## Usage & Requirements

### Dependencies
- Python 3.10+
- `numpy`, `tqdm`

### Running the Full Pipeline
To execute the complete simulation pipeline:
```bash
python sportsanalysis/premier-league/26-27-season.py
```

To run integration testing:
```bash
python -m unittest sportsanalysis/premier-league/test_integration.py
```
```
