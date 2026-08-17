# Premier League 2025-26 Season Simulation

## Overview
This Python script simulates the remaining fixtures of the 2025-26 Premier League season, including European competitions (Champions League, Europa League, Conference League). It uses Elo ratings, Poisson distributions for goal modeling, and Monte Carlo methods to generate probabilities for titles, European qualification, relegation, match outcomes, and season excitement.

The simulation runs 25,000 iterations for the Premier League and 10,000 for each European competition. Key assumptions include fixed Elo ratings, home advantage, form adjustments, injury penalties, and observed win/draw/loss rates.

## Data Inputs
- **Elo Ratings**: Base Elo scores for Premier League teams (Line 80), plus rating deviations (RD) used for K-factor scaling (Line 104).
- **Current Table**: Standings and statistics for each team (Line 128).
- **Fixtures**: List of remaining matches (Line 155).
- **European Elos**: Elo ratings for UEFA competitions (Line 178).
- **Form Adjustments**: Elo bonuses/penalties based on last 10 games (Line 332).
- **WDL Rates**: Observed win/draw/loss probabilities per team (Line 355).
- **Injury Penalties**: Elo reductions for player absences (Line 378).
- **Model Parameters**: Dynamic Home Advantage (50-70 Elo points) (Line 488).

## Simulation Components

### European Competitions (Lines 226-300)
Simulated by determining probabilities from 10,000-iteration Monte Carlo finals.

### Premier League Simulation (Lines 660-754)
#### Helper Functions
- **Adjusted Elo (Lines 470-476)**: Base Elo minus nonlinear injury penalty plus form bonus.
#### Match Engine (Lines 478-523)
- **Elo Difference**: Adjusted home Elo - adjusted away Elo + home advantage.
- **Goal Simulation**: Bivariate Poisson with shared lambda for correlated goals.
#### Apply Result (Lines 575-585)
Updates GF/GA/GD/points based on score.
#### Excitement Score (Lines 587-620)
Measures season tightness out of 10.

### Statistics and Output (Lines 770-1046)
Calculates average points, standard deviation, and various competition probabilities.

## Usage
```bash
python sportsanalysis/premier-league/25-26-season.py
```
