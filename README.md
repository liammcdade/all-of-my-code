# Premier League 2026-27 Season Simulation

A comprehensive Monte Carlo simulation for predicting Premier League outcomes using ELO-based team ratings and Poisson goal modeling.

## Features

- **ELO-Based Ratings**: Team strength ratings using historical performance data.
- **Realistic Match Simulation**: Uses Numba-accelerated Poisson goal modeling with home advantage and match-specific parameters.
- **Dynamic Promotion**: Incorporates one of two potential Championship teams (Southampton/Hull City) per simulation iteration.
- **Monte Carlo Simulations**: Runs 5,000 simulations to generate robust probability distributions.
- **Comprehensive Statistics**: Team performance metrics including average points and qualification probabilities.

## Installation

1. Clone the repository
2. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```

## Usage

### Basic Usage
```bash
python sportsanalysis/premier-league/26-27-season.py
```

The script runs 5,000 simulations and outputs results to the console.

## Output

The simulation generates console output including:
- **Team Statistics**: Average points, standard deviation, probabilities for title, Champions League, Europa League, European qualification, and relegation.
- **Points to Win League**: Minimum and maximum points required to win the title.
- **Additional Statistics**: Probability of relegation with 40+ points, average excitement score, and total European probabilities.

## Algorithm Overview

### 1. Power Ratings
Uses ELO ratings as the primary indicator of team strength.
*Note: Current model implements base ELO; form and injury integration are defined in the registry but not currently active in the match engine.*

### 2. Match Simulation
Uses Poisson distribution for goals with:
- Home advantage factor
- Team ELO difference scaling
- Match closeness and tempo effects
- Shared goals for draws
- Variance and bias adjustments

### 3. European Qualification & Relegation
Simplified assignment based on league position:
- **Champions League**: Top 4 teams.
- **Europa League**: 5th place.
- **Relegation**: Bottom 3 teams.

*Note: This script simulates a 19-team league structure (18 fixed teams + 1 promoted team per iteration).*

## Configuration

Key parameters can be modified in the script constants:
- ELO parameters (K-factor, scale)
- Match model parameters (home advantage, XG calculations)
- Simulation settings (`NUM_SIMS`)

## Dependencies

- **numpy**: Numerical computations
- **numba**: JIT compilation for performance
- **tqdm**: Progress bars

## License

This project is for educational and research purposes.
