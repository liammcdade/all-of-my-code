# Premier League 2026-27 Season Simulation

A comprehensive Monte Carlo simulation for predicting Premier League outcomes using ELO-based team ratings and Poisson goal modeling.

## Features
- **ELO-Based Ratings**: Static team strength ratings
- **Realistic Match Simulation**: Uses Poisson goal modeling with home advantage (33.8 Elo pts)
- **Promotion Logic**: Randomly selects between Southampton and Hull City (50/50 flip)
- **Monte Carlo Simulations**: Runs 5,000 simulations
- **~~Pre-Season Match Probabilities~~**: (Not implemented for 26-27)
- **Configurable Parameters**: Adjustable constants for model tuning
- **Progress Tracking**: Real-time progress bars for simulations
- **Comprehensive Statistics**: Team performance metrics

## Installation
```bash
pip install numpy numba tqdm
```

## Usage
```bash
python sportsanalysis/premier-league/26-27-season.py
```
The script runs 5,000 simulations and outputs results to the console. Note: This simulates a 19-team structure (18 fixed + 1 randomized promoted team).

## Algorithm Overview
### 1. Power Ratings
Uses static ELO ratings. Form and injury adjustments are not currently implemented for this pre-season model.
### 2. Match Simulation
Uses Poisson distribution for goals with a logistic scaling model for expected goals.
### 3. European Qualification
- Champions League: Top 4 teams
- Europa League: 5th place
