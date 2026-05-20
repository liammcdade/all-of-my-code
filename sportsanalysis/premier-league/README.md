# Premier League 2025-26 Season Simulation

## Overview
This script provides a detailed simulation of the remaining 2025-26 Premier League season. It integrates complex modeling for domestic fixtures and European competitions (Champions League, Europa League, and Conference League) using Monte Carlo methods (25,000 iterations).

## Model Components

### 1. Match Engine
The simulation uses a dual-ELO (Attack/Defense) system. Expected goals are derived using an exponential model:
- `home_lambda = base_home * exp(diff / 800)`
- `away_lambda = base_away * exp(-diff / 800)`

Matches are then simulated using a weighted probability model:
- **Result Probability**: Derived from ELO differences and a dynamic draw rate (approx. 25%).
- **Goal Distribution**: Goals are sampled from a Poisson distribution based on the calculated lambdas.
- **Home Advantage**: Randomized per simulation (range: 50–70 ELO points).

### 2. Team Strength Adjustments
- **Form Bonus**: Linear adjustment based on points delta in the last 10 games.
- **Injury Penalty**: Non-linear ELO reduction: `penalty * (1 - exp(-penalty / 80))`.

### 3. European Qualification Assignment
The simulation includes logic for the complex UEFA qualification paths:
- **Champions League**: Top 5 teams (including the additional UEFA coefficient slot) plus European winners.
- **Europa League**: 6th place, FA Cup winner, and Conference League champions.
- **Conference League**: 7th place.

## Data Inputs
- **Base ELO Ratings**: Starting team strengths.
- **Current Table**: Matches played, wins, draws, losses, and goal data.
- **WDL Rates**: Observed win/draw/loss tendencies per team used to bias the match engine.

## Usage
Ensure `numpy`, `numba`, and `tqdm` are installed:
```bash
python 25-26-season.py
```

## Algorithm Details
The script uses Numba-JIT to accelerate the 25,000 season iterations. It dynamically updates ELO ratings after every match based on the scoreline and goal difference, modeling the momentum effects seen in real-world football seasons.

## Known Limitations
- The current implementation (approx. 1050 lines) exceeds the repository's 800-line modularity limit.
- Line number references in previous documentation versions have been removed to prevent maintenance rot.
