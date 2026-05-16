# Premier League 2026-27 Season Simulation

A high-performance Monte Carlo simulation for predicting Premier League outcomes using ELO-based team ratings and a modified Poisson goal model, accelerated with JIT compilation via Numba.

## Features

- **ELO-Based Ratings**: Core team strength ratings used to derive match probabilities.
- **JIT-Accelerated Match Simulation**: Optimized Numba-compiled match engine for high-speed iterations.
- **Promoted Team Randomization**: Simulates the impact of different promoted teams (Southampton or Hull City) within a 20-team league structure.
- **Monte Carlo Simulations**: Runs 5,000 iterations to generate robust outcome probabilities.
- **Comprehensive Statistics**: Detailed team performance metrics including title, Champions League, and relegation probabilities.

## Installation

1. Clone the repository.
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
- **Team Statistics**: Average points, standard deviation, and probabilities for:
  - Title Win
  - Champions League Qualification (Top 4)
  - Europa League Qualification (5th Place)
  - Relegation (Bottom 3)
- **League Statistics**: Maximum and minimum points to win the league.
- **Special Scenarios**: Probability of relegation with 40+ points and season excitement scores.

## Algorithm Overview

### 1. Power Ratings
Uses fixed ELO ratings as the baseline for team strength. Ratings are updated dynamically after each simulated match using a K-factor of 25.

### 2. Match Simulation
Uses a modified Poisson engine with:
- **Home Advantage**: Static ELO boost applied to the home side.
- **xG Conversion**: Logistic scaling of ELO differences to derive Expected Goals (xG).
- **Correlation**: A shared goal component (correlated Poisson) to accurately model draw tendencies.
- **Dynamics**: Match tempo and closeness adjustments based on ELO parity.

### 3. Qualification Logic
- **Champions League**: Assigned to the top 4 teams.
- **Europa League**: Assigned to the 5th place team.
- **Relegation**: Assigned to the bottom 3 teams.

### 4. Tiebreakers
Standard Premier League criteria: Points → Goal Difference → Goals For.

## Configuration

Key parameters can be modified in the script constants:
- `NUM_SIMS`: Number of simulation iterations.
- `ELO_RATINGS`: Baseline team strengths.
- `HOME_ADVANTAGE`: ELO boost for the home team.

## Dependencies

- **numpy**: Numerical computations.
- **numba**: JIT compilation for performance optimization.
- **tqdm**: Progress tracking.

## Disclaimer

This simulation is for entertainment and educational purposes only.
Actual football results depend on many factors not captured in this model.
