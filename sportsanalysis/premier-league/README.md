# Premier League 2025-26 Season Simulation

## Overview
This script simulates the remainder of the 2025-26 Premier League season using Monte Carlo methods. It incorporates ELO ratings, form adjustments, and injury penalties to generate probabilities for final league standings and European qualification.

The simulation runs 25,000 iterations for the Premier League. Key components include dynamic ELO updates, bivariate Poisson goal modeling, and realistic European spot assignment rules.

## Data Inputs
The simulation data is stored in `season_25_26_data.py` and includes:
- **ELO Ratings**: Base strength scores for all 20 teams.
- **Current Table**: Matches played, points, and goal statistics as of the simulation start.
- **Fixtures**: The list of remaining matches to be simulated.
- **Form & Injuries**: Team-specific adjustments (bonuses for recent performance and penalties for key absences).

## Simulation Components

### Match Engine
- **ELO Difference**: (Home ELO - Away ELO) + Home Advantage (randomized 50-70).
- **Goal Model**: Uses bivariate Poisson distribution with shared goals to represent correlated scoring.
- **Dynamic Updates**: ELO ratings are updated after each simulated match based on the result.

### European Qualification
Assignments follow Premier League and UEFA rules:
- **Champions League**: Top 5 teams (assumes extra spot for PL).
- **Europa League**: 6th place and FA Cup winner.
- **Conference League**: 7th place.
- **Special Cases**: Handles scenarios where cup winners already qualified via league position.

## Usage
Run the simulation using:
```bash
python sportsanalysis/premier-league/25-26-season.py
```

### Dependencies
- `numpy`, `numba`, `tqdm`

## Algorithm Notes
- **XG Calculation**: Derived from ELO differences using an exponential scaling factor (`exp(diff/800)`).
- **Tiebreakers**: Points -> Goal Difference -> Goals For.
- **Limitations**: Does not model mid-season transfers or mid-simulation injury changes.
