# Premier League 2026-27 Season Simulation Suite

A Monte Carlo simulation suite for predicting Premier League 2026-27 outcomes, integrated with UEFA Champions League and UEFA Europa League simulation engines.

## Features

- **Betting Market Latent Elo Ratings**: Derives team strength ratings directly from betting market fractional odds, centered around a 1500 baseline Elo.
- **European Tournament Integration**: Runs full Champions League (`UCL.py`) and Europa League (`UEL.py`) simulations (36-team Swiss model, playoff ties, and two-legged knockouts) to compute tournament winner probabilities.
- **European Fatigue Penalties**: Applies Elo reductions (-45.0 for Champions League, -30.0 for Europa League, -20.0 for Conference League) to reflect squad fatigue during domestic fixtures.
- **Poisson Goal Modeling**: Simulates match scores using expected goals ($xG$) derived from adjusted Elo differences, incorporating home advantage (+85 Elo).
- **Locked Fixture Results**: Integrates actual completed match results (`ACTUAL_RESULTS`) into the simulation pipeline.
- **Monte Carlo League Engine**: Runs 2,000 season simulations to produce detailed distributions for points, title probabilities, European qualification, and relegation risk.

## Installation

1. Clone the repository
2. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```

## Usage

Run the integrated simulation suite:
```bash
python sportsanalysis/premier-league/26-27-season.py
```

The script sequentially executes:
1. UEFA Champions League 2026/27 simulation (2,000 iterations)
2. UEFA Europa League 2026/27 simulation (2,000 iterations)
3. Premier League 2026/27 simulation (2,000 iterations)

## Output

The simulation generates console tables detailing:
- **Average Position & Points**: Projected final standings with standard deviations (`Pts` and `SD`).
- **Domestic Probabilities**: Title %, Champions League (Top 4) %, Europa League (5th Place) %, Top Half %, Stay Up %, and Relegation %.
- **European Win Probabilities**: Appended Champions League (`CL Win %`) and Europa League (`UEL Win %`) tournament win chances for qualified English clubs.

## Algorithm Overview

### 1. Power Ratings & Latent Elo
Uses betting market fractional odds from `PL_BETTING_MARKETS` across multiple markets (League Winner, Top 2 Finish, Relegation) to derive centered Elo ratings:
$$\text{Elo}_{\text{team}} = 1500 + \text{Scale} \times \text{LatentStrength}$$

### 2. Match Simulation Engine
Match goals are sampled using Poisson distributions based on expected goals:
$$xG_{\text{home}} = 1.5 \times e^{0.002 \times (\text{Elo}_{\text{home}} + 85 - \text{Elo}_{\text{away}})}$$
$$xG_{\text{away}} = 1.2 \times e^{-0.002 \times (\text{Elo}_{\text{home}} + 85 - \text{Elo}_{\text{away}})}$$

Completed matches stored in `ACTUAL_RESULTS` override randomized match sampling.

### 3. European Fatigue Adjustments
Teams competing in UEFA competitions receive Elo penalties during domestic match evaluations:
- Champions League (`UCL`): -45.0 Elo
- Europa League (`UEL`): -30.0 Elo
- Conference League (`UECL`): -20.0 Elo

### 4. Tiebreakers
Standings are ordered by:
1. Points
2. Goal Difference
3. Goals For

## Configuration

Key parameters can be modified in script constants:
- `NUM_PL_SIMS` in `26-27-season.py` (default: 2,000)
- `NUM_CL_SIMS` in `UCL.py` (default: 2,000)
- `NUM_UEL_SIMS` in `UEL.py` (default: 2,000)
- `EUROPEAN_PENALTIES` in `26-27-season.py`
- `HOME_ADVANTAGE_ELO` in `UCL.py` (default: 85.0 Elo)

## Dependencies

- **numpy**: Numerical calculations and array operations
- **tqdm**: Real-time progress bars
- **math, random, collections, itertools, typing**: Python standard library modules

## License

This project is for educational and research purposes.
