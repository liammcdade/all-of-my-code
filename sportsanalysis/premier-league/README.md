# Premier League Simulation Documentation

This directory contains simulation scripts for the 2025-26 and 2026-27 Premier League seasons. Both use Monte Carlo methods based on Elo ratings and Poisson goal distributions to predict final standings.

---

## 2025-26 Season Simulation (`25-26-season.py`)

This script performs a detailed mid-season simulation, including domestic cup and European competition outcomes.

### Key Features
- **Monte Carlo Simulations**: Runs 25,000 iterations for the Premier League and 10,000 for each European competition.
- **Complex Match Engine**: Incorporates form adjustments, injury penalties, and observed win/draw/loss rates.
- **European Integration**: Simulates Champions League, Europa League, and Conference League brackets once per run to determine win probabilities, which are then sampled in the main league loop.
- **Advanced Qualification**: Tracks complex European spots, including FA Cup winner effects and extra slots for UEFA performance.

### Data Inputs
- **Elo Ratings**: Base Elo scores plus rating deviations (RD).
- **Current Table**: Current season statistics including points, goal difference, and games remaining.
- **Injury/Form**: Per-team adjustments based on squad health and recent performance.

---

## 2026-27 Season Simulation (`26-27-season.py`)

A simplified, performance-optimized pre-season simulator.

### Key Features
- **Performance**: Uses vectorized Numba logic for high-speed simulations (5,000 iterations).
- **Dynamic Promotion**: Simulates the effect of different Championship teams being promoted into the league.
- **League Size**: Currently simulates a 19-team structure (18 fixed + 1 promoted).

---

## Technical Overview (Common Algorithm)

### 1. Match Engine
Both scripts use a modified Poisson goal model:
- **Elo Difference**: Determines base expected goals (XG).
- **Home Advantage**: Added to the home team's effective rating.
- **Bivariate Poisson**: Goals are simulated with a shared component to represent the correlation in scoring patterns (increasing draw realism).

### 2. Performance
- **Numba**: JIT compilation is used on hot paths (Poisson generation, match loop) to allow thousands of seasons to be simulated in seconds.

---

## Usage & Dependencies

Install dependencies:
```bash
pip install -r requirements.txt
```

Run a simulation:
```bash
python 25-26-season.py
# or
python 26-27-season.py
```

### Required Packages
- `numpy`: Numerical operations.
- `numba`: JIT compilation.
- `tqdm`: Progress visualization.
- `dataclasses`: (Used in 25-26) Structured data management.
