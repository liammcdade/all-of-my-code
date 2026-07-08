# Premier League 2025-26 Season Simulation

## Overview
This Python script simulates the remaining fixtures of the 2025-26 Premier League season, including European competitions (Champions League, Europa League, Conference League). It uses Elo ratings, Poisson distributions for goal modeling, and Monte Carlo methods to generate probabilities for titles, European qualification, relegation, match outcomes, and season excitement.

The simulation runs 25,000 iterations for the Premier League and 10,000 for each European competition. Key assumptions include home advantage (randomized between 50-70 Elo points), form adjustments, injury penalties, and observed win/draw/loss rates.

## Data Inputs
- **Elo Ratings**: Base Elo scores for Premier League teams, plus rating deviations (RD) for uncertainty. RD is used in Elo updates to adjust K-factors.
- **Current Table**: Mid-season statistics (matches played, wins/draws/losses, goals for/against, points, remaining games) for each team.
- **Fixtures**: List of remaining matches, grouped by round.
- **European Elos**: Elo ratings for teams in Europa League, Champions League, and Conference League.
- **Form Adjustments**: Elo bonuses/penalties based on last 10 games' points differential.
- **Injury Penalties**: Elo reductions for key player absences.
- **Model Parameters**: Home advantage (randomized), scale factors, and draw rates.

## Simulation Components

### European Competitions
Simulated before the main loop to compute win probabilities.

#### Europa League
- **Goal Model**: Poisson distribution with lambda based on Elo difference (home: 1.4 + diff*0.001, away: 1.1 - diff*0.001), capped at 0.6-4.0.
- **Tie Simulation**: Two-leg format. Aggregate winner advances; penalties on draw.
- **Structure**: Semi-finals and Final.
- **Output**: Win probabilities for each team.

#### Champions League
- **Goal Model**: Similar to EL but higher base goals (home: 1.5 + diff*0.001, away: 1.2 - diff*0.001).
- **Tie Simulation**: Two-leg format. Penalties on aggregate draw.
- **Structure**: Semi-finals and Final.
- **Output**: Win probabilities for each team.

#### Conference League
- **Goal Model**: Matches EL (home: 1.4 + diff*0.001, away: 1.1 - diff*0.001).
- **Tie Simulation**: Two-leg format, penalties on draw.
- **Structure**: Semi-finals and Final.
- **Output**: Win probabilities for each team.

### Premier League Simulation

#### Helper Functions
- **Adjusted Elo**: Base Elo minus nonlinear injury penalty plus form bonus.

#### Match Engine
- **Elo Difference**: Adjusted home Elo - adjusted away Elo + home advantage.
- **Expected Goals (XG)**: Exponential scaling (`exp(diff/800)`).
- **Adjustments**:
  - Closeness factor: Increases draw probability for tight games.
  - Variance boost: Adjusted based on simulation parameters.
- **Goal Simulation**: Bivariate Poisson with shared lambda for correlated goals (draw boost).
- **Output**: Home goals, away goals.

#### Excitement Score
Measures season tightness out of 10 based on title, Top 4, and relegation contenders.

#### Monte Carlo Loop
- **Iterations**: 25,000 simulations.
- **Per Simulation**:
  - Reset table to current state.
  - Simulate all remaining fixtures, update table and Elo ratings.
  - Calculate excitement score.
  - Sample European winners from pre-computed probabilities.
  - Simulate FA Cup winner (Final simulated between Chelsea and Man City).
  - Assign European spots based on league position and cup winners.
  - Track: Titles, European qualifications, relegations, points distributions.

### Statistics and Output
- **Calculations**: Average points, standard deviation, relegation probabilities with 40+ points.
- **Outputs**:
  - Team summary: Avg points, std dev, title/CL/EL/Conf/European/releg %.
  - FA Cup win probabilities.
  - European competition win probabilities.
  - Match probabilities for remaining fixtures.
  - Extreme match probabilities.
  - Team fixture probabilities.

## Usage
Run the script with Python:
```
python 25-26-season.py
```
- **Dependencies**: numpy, tqdm, numba.
- **Runtime**: ~12 seconds for full simulation on typical hardware.

## Key Notes
- **Elo System**: Uses a 400-scale Elo with dynamic K-factors influenced by Rating Deviation.
- **Assumptions**: Fixed injury/form levels throughout the simulation period.
- **Limitations**: FA Cup simulation is currently limited to the final match.
