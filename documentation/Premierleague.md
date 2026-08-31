# Documentation Audit Report: Premier League Simulation Suite

## Mismatches

1. **Simulation Scope and Target Season**:
   - **Documentation**: Title and text refer to "Premier League 2025-26 Season Simulation" and describe a single standalone script (`25-26-season.py`).
   - **Code Base**: The simulation suite is built for the 2026/27 season across three integrated modules: `26-27-season.py`, `UCL.py`, and `UEL.py`.

2. **Iteration Counts**:
   - **Documentation**: Claims 25,000 simulations for the Premier League and 10,000 for European competitions.
   - **Code Base**: `26-27-season.py` defines `NUM_PL_SIMS = 2000` (line 33), `UCL.py` defines `NUM_CL_SIMS = 2000` (line 27), and `UEL.py` defines `NUM_UEL_SIMS = 2000` (line 82).

3. **European Competition Integration and Fatigue System**:
   - **Documentation**: Claims European competitions are "simulated once before the main loop to compute win probabilities" with traditional two-leg knockout formats (semi-finals: Aston Villa vs Forest, Freiburg vs Sporting Braga, etc.).
   - **Code Base**: `26-27-season.py` consumes European simulation outputs from `UCL.py` (`run_champions_league_simulation`) and `UEL.py` (`run_europa_league_simulation`), implementing the new UEFA Swiss Model format (36-team single league phase followed by 2-leg knockout phases and single-leg finals). Additionally, `26-27-season.py` applies explicit European fatigue rating deductions (`EUROPEAN_PENALTIES`: UCL -45.0, UEL -30.0, UECL -20.0 Elo points) prior to running Premier League simulations (lines 35-39, lines 434-450).

4. **Elo Determination via Betting Odds**:
   - **Documentation**: Describes hardcoded static base Elo ratings, rating deviations (RD), form adjustments, injury penalties, and observed win/draw/loss rates.
   - **Code Base**: Base team strengths in `UCL.py` (lines 44-78) and `UEL.py` (lines 84-127) are calculated dynamically from fractional betting odds using `fractional_to_probability()` and `implied_prob_to_elo()` under log-odds scaling (`LEAGUE_AVERAGE_ELO = 1500.0`, `ELO_SCALE = 400.0`, `ELO_SHRINKAGE = 0.75`).

5. **Expected Goals (XG) Model & Home Advantage**:
   - **Documentation**: Describes a home advantage of 33.8 Elo points (or +100 equivalent) and a logistic XG formula with tempo reductions, closeness factors, and WDL bias.
   - **Code Base**: `UCL.py` and `26-27-season.py` use `HOME_ADVANTAGE_ELO = 85.0` (line 21 in UCL.py) and calculate expected goals linearly based on Elo difference (`BASE_HOME_XG = 1.5`, `BASE_AWAY_XG = 1.2`, `XG_ELO_SENSITIVITY = 0.002`), sample goal counts using Poisson distributions (cached via `_POISSON_CACHE`), and resolve knockouts/extra time/penalties deterministically.

6. **Undocumented Modules and Functions**:
   - **Documentation**: Does not reference `UCL.py` or `UEL.py`, nor key functions such as `run_champions_league_simulation()`, `run_europa_league_simulation()`, `run_swiss_phase()`, `simulate_knockout_round()`, or `run_pl_simulation()`.
   - **Code Base**: The entry point `26-27-season.py` orchestrates execution across all three files and prints detailed projections for PL teams and European win probabilities.

---

## Suggested Clarifications

1. **Modular Architecture & Execution Flow**:
   - Clarify that the simulation is modularized into `UCL.py` (Champions League engine), `UEL.py` (Europa League engine), and `26-27-season.py` (Premier League orchestrator and fatigue applier). Explain that running `26-27-season.py` automatically executes European simulations first to feed fatigue penalties into PL team Elo ratings.

2. **Betting Market to Elo Conversion**:
   - Clarify how betting market fractional odds (e.g. `11/2`, `80/1`) are converted to implied win probabilities and subsequently transformed into Elo ratings using log-odds scaling and shrinkage parameters.

3. **UEFA Swiss Model Structure**:
   - Explain the 36-team Swiss Model format used in European simulations, including the 8-match fixture generation (`generate_swiss_fixtures`), table ranking, direct top-8 qualification, 9th-24th play-offs, and 16-team knockout bracket.

4. **European Fatigue Penalty**:
   - Clarify that Premier League teams competing in UCL, UEL, or UECL receive fixed Elo rating reductions (-45.0, -30.0, -20.0 points respectively) to account for squad rotation and fixture congestion during domestic league matches.

---

## Proposed Updated Documentation

```markdown
# Premier League 2026/27 Simulation Suite

## Overview
The Premier League 2026/27 Simulation Suite models the 2026/27 English Premier League season alongside the UEFA Champions League (UCL) and UEFA Europa League (UEL). The suite consists of three interconnected modules:
- `UCL.py`: Simulates the Champions League (Swiss model + knockout phase).
- `UEL.py`: Simulates the Europa League (play-offs, Swiss model + knockout phase).
- `26-27-season.py`: Main entry point. Consumes European simulation outputs, applies European fatigue penalties to domestic Elo ratings, and simulates the full Premier League season.

The default simulation engine runs 2,000 Monte Carlo iterations across all competitions.

## System Architecture & Data Inputs

### Betting Market Elo Ratings (`UCL.py` & `UEL.py`)
Rather than static historical ratings, team strengths are computed dynamically from market outright winning odds:
- **Implied Probability**: $P = \frac{\text{Denominator}}{\text{Numerator} + \text{Denominator}}$
- **Elo Conversion**:
  $$ \text{Elo} = \text{LEAGUE\_AVERAGE\_ELO} + \text{ELO\_SHRINKAGE} \times \text{ELO\_SCALE} \times \log_{10}\left(\frac{P}{1 - P}\right) $$
  where `LEAGUE_AVERAGE_ELO` = 1500.0, `ELO_SCALE` = 400.0, and `ELO_SHRINKAGE` = 0.75.

### Expected Goals (xG) Model
Match score probabilities use Poisson distributions based on team Elo differences:
- **Home Advantage**: +85.0 Elo points.
- **Base xG**: `BASE_HOME_XG` = 1.5, `BASE_AWAY_XG` = 1.2.
- **Sensitivity**: $\text{xG}_{\text{home}} = 1.5 + 0.002 \times \Delta\text{Elo}$, $\text{xG}_{\text{away}} = 1.2 - 0.002 \times \Delta\text{Elo}$ (bounded between 0.2 and 4.0 goals).

## European Fatigue System (`26-27-season.py`)
Premier League teams participating in European competitions suffer an Elo penalty during domestic simulation to reflect fixture congestion and squad rotation:
- **UCL Penalty**: -45.0 Elo points (`Arsenal`, `Aston Villa`, `Liverpool`, `Man City`, `Man United`)
- **UEL Penalty**: -30.0 Elo points (`Bournemouth`, `Sunderland`, `Crystal Palace`)
- **UECL Penalty**: -20.0 Elo points

## Simulation Components

### 1. Champions League Engine (`UCL.py`)
- **Swiss Phase**: 36 teams play 8 matches generated using Elo-tier pot matching (`generate_swiss_fixtures`). Top 8 advance to Round of 16; 9th–24th enter play-offs.
- **Knockout Phase**: Two-leg home/away matches for play-offs, Round of 16, Quarter-finals, and Semi-finals (with extra time xG multiplier of 0.5 and penalty shootout resolution on ties). Single-leg neutral final.
- **Outputs**: Win probabilities for PL teams (`run_champions_league_simulation()`).

### 2. Europa League Engine (`UEL.py`)
- **Play-off Round**: Simulates remaining play-off legs and CL drop-down matches to finalize the 36-team Swiss phase lineup.
- **Swiss & Knockout Phases**: Uses `EuropaLeagueSwissModel` to simulate Swiss standings and subsequent multi-leg knockout rounds.
- **Outputs**: Win probabilities for UEL participants (`run_europa_league_simulation()`).

### 3. Premier League Engine (`26-27-season.py`)
- **Market Calibration**: Converts domestic title betting odds into latent team Elo ratings.
- **Fatigue Adjustment**: Deducts European fatigue penalties from relevant team Elos.
- **Fixture Simulation**: Simulates all 380 Premier League matches per iteration using `run_simulation_vectorized()`.
- **Outputs**: Projected average points, standard deviation, title probability, Champions League qualification probability, Europa League probability, top-half finish probability, and relegation probability.

## Usage & Execution

### Running the Full Simulation Pipeline
To run the complete integrated simulation suite:
```bash
python 26-27-season.py
```

### Module Direct Execution
Each component can also be executed independently for diagnostics:
```bash
python UCL.py
python UEL.py
```

## Dependencies
- Python 3.10+
- `numpy`
- `tqdm`

## Key Differences from 2025/26 Model
- **UEFA Competition Format**: Transitioned from 4-team groups to 36-team Swiss Model format.
- **Dynamic Elo Calibration**: Elo ratings dynamically inferred from live market odds instead of hardcoded ratings.
- **European Fatigue Modeling**: Introduced explicit domestic Elo penalties for European participants.
```
