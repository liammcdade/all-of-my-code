# Premier League 2026-27 Season Simulation

A comprehensive Monte Carlo simulation suite for predicting Premier League outcomes, integrated with Champions League (`UCL.py`) and Europa League (`UEL.py`) simulations to model European fatigue penalties and multi-competition projections.

## Features

- **Betting Market Latent Elo**: Converts fractional betting odds across League Winner, Top 2 Finish, and Relegation markets into weighted latent Elo ratings.
- **European Fatigue Adjustments**: Applies Elo penalties for teams competing in European tournaments (`UCL`: -45.0, `UEL`: -30.0, `UECL`: -20.0).
- **Realistic Match Simulation**: Models expected goals (xG) using team Elo difference and home advantage (+33.8 Elo equivalent), with Poisson goal sampling.
- **Integrated European Competitions**: Simulates Champions League and Europa League tournaments first to derive tournament victory probabilities and determine fatigue impacts.
- **Monte Carlo Simulations**: Runs 2,000 iterations for Premier League projections alongside European tournament simulations.
- **Progress Tracking**: Real-time progress indicators powered by `tqdm`.
- **Comprehensive Table Output**: Generates detailed projections for average position, points, standard deviation, title %, UCL %, Europa %, top half %, stay up %, relegation %, and overall CL/UEL win probabilities.

## Installation

1. Clone the repository
2. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```

## Usage

### Premier League Simulation
Run the primary simulation script directly:
```bash
python sportsanalysis/premier-league/26-27-season.py
```

### Running Tests
Execute the integration test suite:
```bash
PYTHONPATH=sportsanalysis/premier-league pytest sportsanalysis/premier-league/test_integration.py
```

## Output

The simulation generates formatted console output including:
- **European Fatigue Status**: Lists each team's assigned European competition status and associated Elo penalty.
- **Final Premier League Projections Table**:
  - `Pos`: Average finishing position
  - `Team`: Club name
  - `Eur`: European tournament status (`UCL`, `UEL`, `-`)
  - `ELO`: Latent Elo rating derived from betting markets
  - `Pts`: Average accumulated points
  - `SD`: Standard deviation of final points
  - `Title`: Probability (%) of winning the Premier League title
  - `UCL`: Probability (%) of finishing in the top 4 (Champions League qualification)
  - `Europa`: Probability (%) of finishing 5th (Europa League qualification)
  - `TopHalf`: Probability (%) of finishing in positions 1–10
  - `StayUp`: Probability (%) of avoiding relegation (positions 1–17)
  - `Releg`: Probability (%) of finishing in positions 18–20
  - `CL Win % / UEL Win %`: Overall probability of winning the Champions League or Europa League, accounting for qualification.

## Algorithm Overview

### 1. Latent Elo Derivation
Uses betting market odds from `PL_BETTING_MARKETS`:
- Converts fractional odds to win probabilities across League Winner, Top 2 Finish, and Relegation markets.
- Scales and centers log probabilities, applying weighted latent strength formulas (`LEAGUE_AVERAGE_ELO = 1500.0`, `ELO_SCALE = 400.0`, `ELO_SHRINKAGE = 0.85`).

### 2. Fatigue & Match Engine
- Subtracts competition-specific fatigue penalties from team base Elo ratings.
- Adds `HOME_ADVANTAGE_ELO` (+33.8 Elo points) to the home team's rating.
- Computes expected goals (xG) using a logistic scaling formula:
  - `home_xg = 0.7 + 1.8 / (1 + exp(-diff / 400))`
  - `away_xg = 0.7 + 1.8 / (1 + exp(diff / 400))`
- Samples goals using Poisson distributions via `sample_score`.
- Locked actual match results in `ACTUAL_RESULTS` override simulated fixtures.

### 3. European Competition Pipeline
- `run_champions_league_simulation()` models the Champions League knockouts and outputs winning probabilities for PL teams.
- `run_europa_league_simulation()` models Europa League ties and outputs winning probabilities for PL teams.
- Overall European tournament win percentages factor in both domestic qualification probability and European tournament simulation success.

### 4. League Table & Tiebreakers
Teams are sorted by: Points -> Goal Difference -> Goals For (`Pts` -> `GD` -> `GF`).

## Configuration

Key constants can be configured within `sportsanalysis/premier-league/26-27-season.py`, `UCL.py`, and `UEL.py`:
- `NUM_PL_SIMS`: Number of Premier League iterations (default: `2000`).
- `EUROPEAN_PENALTIES`: Elo penalties per competition (`UCL`: 45.0, `UEL`: 30.0, `UECL`: 20.0).
- `HOME_ADVANTAGE_ELO`: Home field Elo advantage (default: `33.8`).

## Dependencies

- **numpy**: Matrix operations and random sampling
- **tqdm**: Simulation progress tracking
- **UCL.py / UEL.py**: Champions League and Europa League simulation engines

## License

This project is for educational and research purposes.

## Disclaimer

This simulation is for entertainment and educational purposes only.
Actual football results depend on many factors not captured in this model.
