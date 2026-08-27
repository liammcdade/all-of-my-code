# Premier League 2026-27 Season Simulation

A comprehensive Monte Carlo simulation for predicting Premier League outcomes using ELO-based team ratings and Poisson goal modeling.

## Features

- **ELO-Based Ratings**: Team strength ratings using logistic XG scaling and JIT acceleration
- **Realistic Match Simulation**: Uses Poisson goal modeling with home advantage, tempo adjustments, and shared goals for draws
- **Promoted Team Selection**: Randomly selects one Championship team (Southampton/Hull City) to complete a 19-team league
- **Monte Carlo Simulations**: Runs 5,000 simulations per execution
- **Configurable Parameters**: Adjustable constants for model tuning
- **Progress Tracking**: Real-time progress bars for simulations
- **Comprehensive Statistics**: Team performance metrics and league outcomes

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
- **Team Statistics**: Average points, standard deviation, probabilities for title, Champions League, Europa League, and relegation
- **Points to Win League**: Minimum and maximum points required to win the title
- **Additional Statistics**: Probability of relegation with 40+ points, average excitement score, and aggregate European probabilities

## Algorithm Overview

### 1. Power Ratings
Uses base ELO ratings for 18 fixed teams and 1 randomly selected promoted team.

### 2. Match Simulation
Uses Poisson distribution for goals with:
- Home advantage factor (fixed at 33.8)
- Logistic ELO difference scaling for XG
- Match closeness and tempo effects
- Shared goals for correlated scoring (draw boost)
- Variance boost factor

### 3. European Qualification
Simplified assignment based on league position:
- Champions League: Top 4 teams
- Europa League: 5th place
- Relegation: Bottom 3 teams

### 4. Tiebreakers
Uses simplified approach: Points -> Goal Difference -> Goals For
*(Note: Real Premier League uses head-to-head records)*

## Configuration

Key parameters can be modified in the script constants:
- ELO parameters (K-factor, scale)
- Match model parameters (home advantage, XG calculations)
- Simulation settings (number of sims)
- Adjustment factors (tempo range, variance boost)

## Dependencies

- **numpy**: Numerical computations and random number generation
- **numba**: JIT compilation for performance optimization
- **tqdm**: Progress bars
- **collections, math, random**: Standard library modules

## License

This project is for educational and research purposes.

## Contributing

1. Fork the repository
2. Create a feature branch
3. Add tests for new functionality
4. Submit a pull request

## Disclaimer

This simulation is for entertainment and educational purposes only.
Actual football results depend on many factors not captured in this model.
