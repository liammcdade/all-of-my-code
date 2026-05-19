# Premier League 2026-27 Season Simulation

A performance-optimized Monte Carlo simulation for the 2026-27 Premier League season using JIT-accelerated modeling.

## Overview
This simulation uses a high-performance match engine optimized with `numba` to predict season outcomes. It employs a shared-Poisson goal model to capture correlated scoring patterns and realistic match dynamics.

## Features

- **JIT-Accelerated Engine**: Core simulation logic is optimized for speed, allowing for thousands of iterations in seconds.
- **Shared-Goal Model**: A bivariate Poisson approach where teams share a "closeness" goal component to model draws more accurately.
- **Dynamic ELO Ratings**: Ratings update match-by-match within each simulation iteration.
- **Championship Promotion**: Randomly selects between Southampton and Hull City to join the top flight.
- **Performance Optimized**: Vectorized fixture processing for maximum efficiency.

## Output
The simulation generates detailed console output:
- **Team Statistics**: Average points, standard deviation, and probabilities for:
  - Title Win
  - Champions League Qualification (Top 4)
  - Europa League Qualification (5th)
  - Relegation (Bottom 3)
- **League Context**: Minimum and maximum points required to win the title across all simulations.
- **Season Excitement**: An excitement score based on the point gap between 1st and 2nd place.
- **Relegation Statistics**: Probability of a team being relegated even with 40+ points.

## Algorithm & Model

### Match Engine
The `run_simulation_vectorized` engine uses:
- **Logistic XG Scaling**: Expected goals scale with ELO difference via a logistic function.
- **Home Advantage**: Constant bonus of 33.8 ELO points.
- **Tempo & Variance**: Match-specific adjustments for goal rates and outcome variance.

### Known Limitations
- **League Size**: The current implementation simulates a **19-team league** (18 fixed PL teams + 1 promoted team). Standard Premier League structure requires 20 teams.
- **Form & Injuries**: These parameters are defined in the code but are currently **placeholders** and not integrated into the JIT-accelerated engine.
- **Promotion Logic**: Modeled as a simple 50/50 choice between two teams rather than a full playoff simulation.

## Installation

```bash
pip install -r requirements.txt
```

## Usage

```bash
python sportsanalysis/premier-league/26-27-season.py
```
*Note: The script defaults to 5,000 simulations.*

## Dependencies

- **numpy**: Matrix operations.
- **numba**: JIT compilation.
- **tqdm**: Progress bars.

## Disclaimer
This project is for educational and research purposes. Actual results may vary.
