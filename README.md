# Premier League 2026-27 Season Simulation

A high-performance Monte Carlo simulation for 2026-27 season outcomes using JIT-accelerated vectorization.

## Features

- **Elo-Based Ratings**: Team strength ratings for a simulated 19-team league.
- **Realistic Match Simulation**: Uses Poisson goal modeling with logistic XG scaling and home advantage.
- **Promoted Team Logic**: Randomly selects between Southampton and Hull City for the 19th league spot.
- **Monte Carlo Simulations**: Runs 5,000 simulations using `numba` for performance optimization.
- **Configurable Parameters**: Adjustable constants for ELO scale, K-factor, and XG calculations.
- **Comprehensive Statistics**: Team performance metrics (average points, standard deviation, European probabilities).

## Installation

1. Clone the repository
2. Install dependencies:
   ```bash
   pip install numpy numba tqdm
   ```

## Usage

```bash
python sportsanalysis/premier-league/26-27-season.py
```

The script runs 5,000 simulations and outputs results to the console.

## Algorithm Overview

### 1. Power Ratings
Uses base Elo ratings. While the `TeamRegistry` supports form and injury tracking, the current simulation engine uses fixed base ratings for match calculations.

### 2. Match Simulation
Uses Poisson distribution for goals with:
- Home advantage (33.8 Elo points)
- Logistic ELO difference scaling for Expected Goals (XG)
- Shared goal component for realistic draw representation
- Tempo factors based on Elo disparity

### 3. European Qualification
Simplified assignment based on league position:
- Champions League: Top 4 teams
- Europa League: 5th place
- Relegation: Bottom 3 teams

### 4. Side Effects
- **Cache Management**: The script automatically deletes the `__pycache__` directory upon completion.

## Dependencies

- **numpy**: Numerical computations
- **numba**: JIT compilation for performance
- **tqdm**: Progress tracking

## License

This project is for educational and research purposes.
