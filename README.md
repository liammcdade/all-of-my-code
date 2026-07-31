# Premier League 2026-27 Season Simulation

A high-performance Monte Carlo simulation for predicting Premier League outcomes using ELO-based ratings and JIT-accelerated Poisson goal modeling.

## Features

- **ELO-Based Ratings**: Core team strength ratings with JIT-accelerated vectorized simulation.
- **Bivariate Poisson Match Simulation**: Uses expected goals (xG) based on ELO deltas with a shared goal component for realistic draw modelling.
- **Monte Carlo Simulations**: Executes 5,000 iterations to generate robust probability distributions.
- **League Structure**: Simulates a 19-team league comprising 18 fixed Premier League teams and 1 randomly selected promoted team (Southampton or Hull City).
- **Comprehensive Statistics**: Tracks probabilities for title wins, Top 4 (Champions League), 5th place (Europa League), and relegation.

## Installation

1. Clone the repository.
2. Install the required numerical and optimization libraries:
   ```bash
   pip install -r requirements.txt numba
   ```

## Usage

### Basic Usage
```bash
python sportsanalysis/premier-league/26-27-season.py
```

The script runs 5,000 simulations and outputs a detailed team statistics table to the console.

## Algorithm Overview

### 1. Match Parameter Calculation
The simulation utilizes a logistic scaling model to determine expected goals (xG):
- `home_xg = base_xg + max_xg / (1 + exp(-diff / xg_scale))`
- `away_xg = base_xg + max_xg / (1 + exp(diff / xg_scale))`
- `closeness = exp(-(diff^2) / (2 * closeness_scale^2))`

### 2. Poisson Match Engine
Goals are sampled from a modified Poisson distribution:
- **Shared Goals**: A base rate of shared goals is increased by the `closeness` factor to correlate scores.
- **Tempo Adjustment**: Goal rates are slightly modified based on the ELO gap.
- **Variance Boost**: Applied to the home team's lambda to model home-field variance.

### 3. Dynamic ELO Updates
Within each simulation iteration, team ELOs are updated after every match using a standard K-factor of 25:
- `ELO_new = ELO_old + K * (Score - Expected_Score)`

## Configuration
Tunable parameters are located at the top of `26-27-season.py`:
- `NUM_SIMS`: Total iterations (default: 5000).
- `HOME_ADVANTAGE`: ELO bonus for the home side (default: 33.8).
- `BASE_XG` / `MAX_XG`: xG scaling limits.

## Qualification Rules
- **Champions League**: League positions 1–4.
- **Europa League**: League position 5.
- **Relegation**: Bottom 3 teams.
*(Note: Conference League qualification for 6th place is not currently implemented in the 26-27 simulation engine).*

## Dependencies
- `numpy`: Numerical operations.
- `numba`: JIT compilation for simulation performance.
- `tqdm`: Progress visualization.

## Disclaimer
This simulation is for research and entertainment purposes. Actual results may vary due to factors not included in the ELO-only model.
