# Premier League 2025-26 Season Simulation

## Overview
This Python script (`25-26-season.py`) simulates the remaining fixtures of the 2025-26 Premier League season, including European competitions (Champions League, Europa League, Conference League). It uses a legacy bivariate Poisson-style goal model with dynamic Elo updates.

The simulation runs 25,000 iterations for the Premier League and 1,000 for the FA Cup and match probabilities. Key features include dynamic Elo ratings, form adjustments, and injury penalties.

## Data Inputs
- **Elo Ratings**: Base Elo scores for Premier League teams and rating deviations (RD).
- **Current Table**: Mid-season statistics used as the starting point for simulations.
- **Fixtures**: List of remaining matches to be simulated.
- **European Elos**: Specific Elo ratings for teams in various European competitions.
- **Form Adjustments**: Elo bonuses/penalties based on points differential from the last 10 games.
- **Injury Penalties**: Elo reductions for key player absences.
- **Model Parameters**: Home advantage (set to 60 Elo points).

## Simulation Components

### European Competitions
Pre-simulated once (10,000 iterations each) to compute win probabilities for assignment in the main league loop.
- **Champions League**: High-scoring Poisson model (Base Home: 1.5, Away: 1.2).
- **Europa League**: Standard Poisson model (Base Home: 1.4, Away: 1.1).
- **Conference League**: Standard Poisson model (Base Home: 1.4, Away: 1.1).

### Premier League Simulation

#### Match Engine
- **Elo Difference**: Home Elo - Away Elo + Home Advantage.
- **Expected Goals (XG)**: Calculated using exponential scaling:
  - `home_xg = home_base * exp(diff/800)`
  - `away_xg = away_base * exp(-diff/800)`
- **Goal Simulation**: A bivariate-style Poisson model that adjusts for expected win/draw/loss rates and match closeness to realistically distribute goals and points.
- **Dynamic Updates**: Elo ratings are updated after every match based on the result and goal difference, influencing future matches within the same simulation.

#### European Qualification
Assigns spots based on:
1. League Position (Top 4 → CL, 5th → EL, 6th → Conf).
2. FA Cup Winner (EL).
3. Continental Winners (European winners can earn extra spots for their league).

## Usage
Run the script with Python:
```bash
python sportsanalysis/premier-league/25-26-season.py
```
- **Dependencies**: numpy, tqdm, numba.

## Key Notes
- **Accuracy**: Provides a distribution of possible outcomes based on Monte Carlo methods.
- **Performance**: Partially uses Numba JIT acceleration for match simulation.
- **Legacy Version**: This script uses the 2025-26 data and the original bivariate model, unlike the newer 2026-27 JIT-vectorized script.
