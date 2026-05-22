# Premier League 2026-27 Season Simulation

A comprehensive Monte Carlo simulation for predicting Premier League outcomes using ELO-based team ratings and Poisson goal modeling.

## Features

- **ELO-Based Ratings**: Dynamic team strength ratings adjusted during the simulation.
- **Realistic Match Simulation**: Uses JIT-accelerated Poisson goal modeling with home advantage and match-specific parameters.
- **Monte Carlo Simulations**: Runs 5,000 simulations grouped by promoted team (Southampton or Hull City).
- **Comprehensive Statistics**: Team performance metrics (Avg Points, StdDev), Title/CL/EL/Relegation probabilities.
- **Progress Tracking**: Real-time progress bars for simulations via `tqdm`.

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
- **Team Statistics**: Average points, standard deviation, probabilities for Title, Champions League, Europa League, European qualification, and Relegation.
- **Points to Win League**: Minimum and maximum points required to win the title across all simulations.
- **Additional Statistics**: Probability of relegation with 40+ points, average season excitement score.

## Algorithm Overview

### 1. Power Ratings
Uses ELO ratings that update after every match based on result vs. expectation (K-factor: 25).

### 2. Match Simulation
Uses Poisson distribution for goals with:
- **Home Advantage**: +33.8 ELO boost for the home team.
- **Expected Goals (XG)**: Calculated via logistic scaling based on ELO difference.
- **Shared Goals**: Correlated scoring patterns to represent realistic draw probabilities.
- **Tempo**: Adjusted based on ELO disparity.

### 3. European Qualification
Simplified assignment based on league position:
- **Champions League**: Top 4 teams.
- **Europa League**: 5th place.
- **Relegation**: Bottom 3 teams.

### 4. Tiebreakers
Uses Premier League standards: Points -> Goal Difference -> Goals For.

## Configuration

Key parameters in `26-27-season.py`:
- `NUM_SIMS`: 5,000 (default)
- `HOME_ADVANTAGE`: 33.8
- `K_FACTOR`: 25
- `ELO_SCALE`: 400

## Dependencies

- **numpy**: Numerical computations.
- **numba**: JIT compilation for performance.
- **tqdm**: Progress bars.

## License

This project is for educational and research purposes.
