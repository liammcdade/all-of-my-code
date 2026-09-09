# Premier League 2026-27 Season Simulation Suite

A refactored, Monte Carlo simulation engine that predicts Premier League outcomes integrated with UEFA Champions League (UCL), UEFA Europa League (UEL), and UEFA Conference League (UECL) competition pipelines.

## Features

- **Latent Elo Ratings**: Generates baseline team strength ratings derived from multi-market betting odds (Title, Top 2, Relegation) using market-efficiency weighting.
- **Integrated European Competitions**: Dynamically simulates 36-team league phases and multi-round two-legged knockout stages for UCL, UEL, and UECL.
- **Dynamic European Fatigue Decay**: Models team fixture congestion by applying European fatigue penalties that decay linearly across the season for active European contenders.
- **Locked Actual Fixture Results**: Supports locking in real-world match outcomes (`ACTUAL_RESULTS`) to anchor mid-season or early-season simulations.
- **Conditional UEFA Qualification**: Implements official UEFA qualification rules, granting additional Champions League spots to 5th place when an English club wins the UCL or UEL while finishing outside the top 4.
- **Poisson Match Engine**: Simulates goal scoring using exponential Elo-XG modeling and Poisson probability mass functions.

## Installation & Setup

1. Clone the repository.
2. Install required dependencies:
   ```bash
   pip install numpy tqdm pandas tabulate rich
   ```

## Usage

Run the unified simulation script:
```bash
python sportsanalysis/premier-league/26-27-season.py
```

By default, the script executes 2,000 unified iterations (`NUM_PL_SIMS = 2000`) combining European competition brackets with full 380-match Premier League seasons.

## Algorithm Overview

### 1. Market-Derived Latent Elo
Calculates baseline Elo ratings using centered log-probabilities from fractional betting odds across multiple markets, normalized to a baseline scale ($\text{Scale} = 400$).

### 2. European Simulation & Fatigue Model
Before each PL season iteration:
- Full league phases (8 matchdays) and knockout phases (Playoffs through Final) are simulated for UCL, UEL, and UECL.
- Active European teams incur competition-specific fatigue penalties (`UCL`: 8.0, `UEL`: 6.0, `UECL`: 5.0 Elo points) that decay linearly ($1 - \frac{\text{match\_index}}{\text{total\_matches}}$) over the season.

### 3. Match Engine
- **Home Advantage**: +85.0 Elo points applied to the home team.
- **Expected Goals**:
  - $\text{xG}_{\text{home}} = 1.5 \times \exp(0.002 \times \Delta\text{Elo})$
  - $\text{xG}_{\text{away}} = 1.2 \times \exp(-0.002 \times \Delta\text{Elo})$
- Goals are drawn using cached Poisson PMF tables.

### 4. Output Statistics
Outputs a consolidated table containing:
- **Pos / Pts / SD**: Mean finishing position, mean points, and standard deviation.
- **95% CI**: 95% Confidence interval for projected points.
- **Title% / UCLQ%**: Title win probability and Champions League qualification probability.
- **5th->UCL%**: Probability of 5th place securing Champions League entry via UCL/UEL winner qualification.
- **UCLWin% / UELWin% / UECLWin% / AnyEuroWin%**: European trophy win probabilities for Premier League clubs.
