# Premier League 2025-26 Season Simulation

## Overview
This Python script simulates the remaining fixtures of the 2025-26 Premier League season, including European competitions (Champions League, Europa League, Conference League). It uses Elo ratings, Poisson distributions for goal modeling, and Monte Carlo methods to generate probabilities for titles, European qualification, relegation, match outcomes, and season excitement.

The simulation runs 25,000 iterations for the Premier League and 10,000 for each European competition. Key assumptions include fixed Elo ratings, home advantage, form adjustments, injury penalties, and observed win/draw/loss rates.

## Data Inputs
- **Elo Ratings**: Base Elo scores for Premier League teams (lines 8-28), plus rating deviations (RD) for uncertainty (lines 31-52), though RD is not actively used in match simulations.
- **Current Table**: Mid-season statistics (matches played, wins/draws/losses, goals for/against, points, remaining games) for each team (lines 54-76).
- **Fixtures**: List of remaining matches, grouped by round (lines 78-106).
- **European Elos**: Elo ratings for teams in Europa League (lines 109-114), Champions League (lines 117-122), and Conference League (lines 125-130).
- **Form Adjustments**: Elo bonuses/penalties based on last 10 games' points differential (lines 396-417).
- **WDL Rates**: Observed win/draw/loss probabilities per team (lines 420-441).
- **Injury Penalties**: Elo reductions for key player absences (lines 444-466).
- **Model Parameters**: Home advantage (33.8 Elo points) (line 469).

## Simulation Components

### European Competitions (lines 187-651)
Simulated once before the main loop to compute win probabilities.

#### Europa League (lines 187-253, simulation at 596-616)
- **Goal Model**: Poisson distribution with lambda based on Elo difference (home: 1.4 + diff*0.001, away: 1.1 - diff*0.001), capped at 0.6-4.0.
- **Tie Simulation**: Two-leg format. First leg simulated, second leg based on reversed Elo. Aggregate winner advances; penalties on draw.
- **Structure**: Quarter-finals assumed completed. Semi-finals: Aston Villa vs Nottingham Forest, Freiburg vs Sporting Braga. Final: One-leg match.
- **Output**: Win probabilities for each team.

#### Champions League (lines 254-324, simulation at 620-629)
- **Goal Model**: Similar to EL but higher base goals (home: 1.5 + diff*0.001, away: 1.2 - diff*0.001).
- **Tie Simulation**: Two-leg. First leg scores can be fixed (e.g., PSG vs Bayern: 5-4) or simulated. Penalties on aggregate draw.
- **Structure**: Semi-finals: Paris Saint-Germain vs Bayern Munich, Atlético Madrid vs Arsenal. Final: One-leg.
- **Output**: Win probabilities for each team.

#### Conference League (lines 325-390, simulation at 633-651)
- **Goal Model**: Matches EL (home: 1.4 + diff*0.001, away: 1.1 - diff*0.001).
- **Tie Simulation**: Two-leg, penalties on draw.
- **Structure**: Semi-finals: Shakhtar Donetsk vs Crystal Palace, Strasbourg vs Rayo Vallecano. Final: One-leg.
- **Output**: Win probabilities for each team.

### Premier League Simulation (lines 472-754)

#### Helper Functions
- **Adjusted Elo (lines 472-476)**: Base Elo minus nonlinear injury penalty plus form bonus.

#### Match Engine (lines 478-523)
- **Elo Difference**: Adjusted home Elo - adjusted away Elo + home advantage.
- **Expected Goals (XG)**: Logistic scaling (home_xg = 0.7 + 1.8 / (1 + exp(-diff/400)), away_xg analogous).
- **Adjustments**:
  - WDL bias: Boost XG based on team's win-loss differential.
  - Closeness factor: Increases draw probability for tight games.
  - Tempo reduction: Less effect for large Elo gaps.
  - Variance boost: From win rate.
- **Goal Simulation**: Bivariate Poisson with shared lambda for correlated goals (draw boost).
- **Output**: Home goals, away goals.

#### Apply Result (lines 525-540)
Updates table: GF/GA/GD/points based on score (win: +3, draw: +1 each).

#### Excitement Score (lines 542-576)
Measures season tightness out of 10:
- Title race: Teams within 3 points of leader.
- Top 4: Teams within 5 points of 4th.
- Relegation: Teams within 3 points of 18th.

#### Monte Carlo Loop (lines 579-754)
- **Iterations**: 25,000 simulations.
- **Per Simulation**:
  - Reset table to current state.
  - Simulate all remaining fixtures, update table.
  - Calculate excitement score.
  - Sample European winners from pre-computed probabilities.
  - Simulate FA Cup winner (simple Elo-based knockout).
  - Assign European spots: Top 5 → CL, 6th → EL, FA Cup winner → EL (if not top 5), 7th → Conf. Adjust for European winners qualifying extra spots.
  - Track: Titles, European qualifications, relegations (especially with 40+ points), points distributions.

### Statistics and Output (lines 756-967)
- **Calculations**: Average points, standard deviation, relegation probabilities with 40+ points.
- **Outputs**:
  - Team summary: Avg points, std dev, title/CL/EL/Conf/European/releg %.
  - Premier League UEFA win %.
  - European competition win probabilities.
  - Probabilities for relegation with 40+ points, 8+ European teams, average excitement.
  - Match probabilities for remaining fixtures (10,000 sims per match).
  - Extreme match probabilities (highest home/away win chances, most likely draw).
  - Team fixture probabilities (win/lose/draw all remaining games, average win %).
  - Relegation occurrences out of 25,000 simulations.

## Usage
Run the script with Python:
```
python 25-26-season.py
```
- **Dependencies**: numpy, tqdm, math, random, collections.
- **Runtime**: ~12 seconds for full simulation on typical hardware.
- **Customization**: Update Elo ratings, fixtures, or parameters for different scenarios. European first-leg scores can be fixed in the simulation calls.

## Key Notes
- **Elo System**: Uses a 400-scale Elo with home +100 equivalent, but match outcomes use custom XG formulas instead of pure Elo probabilities.
- **Assumptions**: No transfers, fixed injuries/forms, European outcomes independent of PL results.
- **Accuracy**: Provides realistic probability distributions; results are deterministic per run (no random seed set).
- **Limitations**: Does not model player transfers, injuries changing mid-season, or external factors.</content>
<parameter name="filePath">sportsanalysis\premier-league\README.md