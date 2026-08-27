# Premier League 2025-26 Season Simulation

## Overview
This Python script simulates the remaining fixtures of the 2025-26 Premier League season. It uses Elo ratings, Poisson distributions with shared-goal modifiers for draws, and Monte Carlo methods to generate probabilities for titles, European qualification, and relegation.

The simulation runs 25,000 iterations for the Premier League and 10,000 for each European competition winner sampling.

## Data Inputs
- **Elo Ratings**: Base ratings (line 80), RD for uncertainty (line 105).
- **Current Table**: Mid-season statistics including points, goal difference, and remaining games (line 128).
- **Fixtures**: List of remaining matches by round (line 155).
- **European Elos**: Ratings for teams in Europa League (line 190), Champions League (line 197), and Conference League (line 204).
- **Adjustments**: Form bonuses (line 332) and Injury penalties (line 378).
- **Model Parameters**: Randomized Home Advantage (50-70 Elo points) set per simulation.

## Simulation Components

### European Competitions (lines 711-736)
Simulated as single-match finals between pre-defined semi-finalists to compute win probabilities.
- **Champions League**: PSG, Bayern, Atletico, Arsenal.
- **Europa League**: Villa, Freiburg, Forest, Braga.
- **Conference League**: Strasbourg, Shakhtar, Rayo, Palace.

### Premier League Simulation (lines 482-588)

#### Match Engine (lines 443-480)
- **Elo Difference**: Adjusted Home Elo - Adjusted Away Elo + Home Advantage.
- **Expected Goals (XG)**: Exponential scaling using `base * exp(diff / 800)`.
- **Goal Simulation**: Modified Poisson model where a shared goal component is added to both teams to represent correlated scoring patterns and enhance draw realism.

#### European Qualification
Assigns spots based on league position and simulated winners of the FA Cup and UEFA competitions. Tracks the probability of at least 9 teams qualifying for Europe.

### Statistics and Output
- **Team Summary**: Avg points, std dev, title/CL/EL/Conf/European/relegation percentages.
- **Special Scenarios**: Probability of relegation with 40+ points, 9+ European teams, and average excitement scores.
- **Match Odds**: Individual win/draw/loss probabilities for all remaining fixtures.

## Usage
Run the script with Python:
```bash
python sportsanalysis/premier-league/25-26-season.py
```
- **Dependencies**: `numpy`, `numba`, `tqdm`.
- **Note**: This script uses `numba` for JIT acceleration; ensure it is installed via `pip install numba`.

## Key Implementation Notes
- **XG Model**: Uses an exponential model rather than logistic.
- **Home Advantage**: Dynamic range of 50-70 Elo points per simulation.
- **Tiebreakers**: Points -> Goal Difference -> Goals For.
- **FA Cup**: Simulated as a one-match final between Chelsea and Man City based on Elo.
