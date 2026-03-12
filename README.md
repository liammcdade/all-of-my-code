# Premier League 2025-26 Season Simulation

A comprehensive Monte Carlo simulation for predicting Premier League outcomes based on betting market odds.

## Features

- **Multiple Betting Markets**: Integrates winner, top 4/6/10, and relegation odds
- **Realistic Match Simulation**: Uses Poisson goal modeling with home advantage
- **European Qualification**: Proper cascading logic for FA Cup and Carabao Cup winners
- **Configurable Parameters**: Command-line arguments for simulations and seeds
- **Progress Tracking**: Real-time progress bars for long-running operations
- **Rich Output**: Beautiful tables and formatting with the Rich library
- **Comprehensive Logging**: Detailed logs for debugging and monitoring

## Installation

1. Clone the repository
2. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```

## Usage

### Basic Usage
```bash
python sportsanalysis/premier-league/25-26-season.py
```

### Custom Parameters
```bash
# Run with 1000 simulations
python sportsanalysis/premier-league/25-26-season.py --nsims 1000

# Use custom random seed for reproducibility
python sportsanalysis/premier-league/25-26-season.py --seed 42

# Enable debug logging
python sportsanalysis/premier-league/25-26-season.py --debug

# Combine parameters
python sportsanalysis/premier-league/25-26-season.py --nsims 10000 --seed 123 --debug
```

## Output

The simulation generates:
- **Console Output**: Formatted tables showing team probabilities
- **HTML File**: `premier_league_simulation.html` with detailed results
- **Log File**: `premier_league_simulation.log` with execution details

## Algorithm Overview

### 1. Power Ratings
Combines multiple betting markets using weighted arithmetic mean:
- Winner odds (25% weight)
- Top 4 odds (25% weight)
- Top 6 odds (20% weight)
- Top 10 odds (20% weight)
- Relegation odds (10% weight)

### 2. Match Simulation
Uses Poisson distribution for goals with:
- Home advantage factor (6.5%)
- Team strength exponent (1.15)
- Goal expectation constraints

### 3. European Qualification
Implements proper cascading logic:
- Champions League: Top 5 teams (with extra UCL spot)
- Europa League: 6th place + FA Cup winner (with cascading)
- Conference League: Carabao Cup winner (with cascading)

### 4. Tiebreakers
Uses simplified approach: Points -> Goal Difference -> Goals For
*(Note: Real Premier League uses head-to-head records)*

## Configuration

Key parameters can be modified in the `CONFIG` dictionary:
- Simulation parameters (number of sims, seeds)
- Match model parameters (home advantage, goal expectations)
- Power rating weights
- European qualification settings

## Dependencies

- **numpy**: Numerical computations and random number generation
- **pandas**: Data manipulation and analysis
- **tqdm**: Progress bars
- **rich**: Beautiful console output and tables

## License

This project is for educational and research purposes.

## Contributing

1. Fork the repository
2. Create a feature branch
3. Add tests for new functionality
4. Submit a pull request

## Disclaimer

This simulation is for entertainment and educational purposes only.
Actual football results depend on many factors not captured in this model.
