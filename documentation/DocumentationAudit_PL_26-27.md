# Documentation Audit Report: Premier League 2026-27 Simulation

**Auditor:** Jules (Senior Technical Writer & Software Documentation Auditor)
**Date:** June 18, 2024
**Target Code:** `sportsanalysis/premier-league/26-27-season.py`
**Target Documentation:** Root `README.md`

---

## 1. Mismatches & Inconsistencies

### A. League Structure (Critical)
- **Documentation:** Implies a standard Premier League structure (usually 20 teams).
- **Code:** Implements a **19-team league**.
  - `NUM_TEAMS = 18` (Line 25) refers to the fixed teams in `TEAM_NAMES`.
  - The simulation adds exactly one promoted team (`Southampton` or `Hull City`) per iteration (Lines 194-195).
  - Total matches per team is 36 (18 opponents × 2 matches), confirming a 19-team structure.

### B. Simulation Parameters
- **Documentation:** "Runs 10,000 simulations grouped by promoted team" (Features section) and "The script runs 10,000 simulations" (Usage section).
- **Code:** `NUM_SIMS = 5000` (Line 181).

### C. Missing Features (Documented but not Implemented)
- **Power Ratings:** Documentation claims Elo is adjusted for **Form**, **Injuries**, and **Win/Draw/Loss rates** (Algorithm Overview Section 1).
  - **Code:** The `TeamRegistry.add_team` method accepts `form` and `injury` parameters (Line 51), but they are defaulted to 0.0 and never updated or used in the match calculation. The code uses base Elo only.
- **Match Simulation:** Documentation claims "Variance and bias adjustments" and "bias adjustments" based on WDL (Algorithm Overview Section 2).
  - **Code:** `simulate_poisson_match_numba` (Lines 91-104) uses a fixed `VARIANCE_BOOST_FACTOR` but does not implement any team-specific WDL bias logic.
- **European Qualification:** Documentation lists **Conference League (6th place)**.
  - **Code:** The simulation only tracks and prints probabilities for Title (1st), Top 4 (CL), and 5th (Europa) (Lines 207-212, 255-258). 6th place is not tracked.
- **Championship Promotion:** Documentation claims a "Championship playoffs to determine promotion".
  - **Code:** Promotion is determined by a `random.random() < 0.5` coin flip between Southampton and Hull City (Line 194). No playoff matches are simulated.

### D. Missing Output Data
- **Documentation:** Lists "Match Probabilities", "Extreme Match Probabilities", and "Team Fixture Probabilities" as generated console output.
- **Code:** These features are completely absent. The output is limited to Team Statistics, Points to Win League, and Additional Statistics (Relegation with 40+ pts, Excitement, and aggregate European probabilities).

---

## 2. Clarifications & Improvements

### A. Jargon & Prerequisite Knowledge
- **Elo Ratings:** The documentation assumes the user understands the Elo system. A brief note explaining that higher numbers represent stronger teams would benefit non-technical users.
- **Poisson Modeling:** "Poisson goal modeling" is used without context. Clarify that this is a statistical method to predict the number of goals scored based on independent events.
- **Excitement Score:** The "Average excitement score" (Line 254) is calculated as `(Leader Points - Second Place Points) / 10`. This is highly specific and should be defined in the documentation to avoid confusion.
- **Numba/JIT:** The "Dependencies" section mentions `numba`. It should explicitly state that the first run might be slower due to JIT compilation.

### B. Installation/Execution
- **Missing Dependencies:** Running the script as instructed fails because `numpy`, `numba`, and `tqdm` are not in the root `requirements.txt`. These must be added or mentioned explicitly.
- **Pathing:** The "Usage" instruction `python sportsanalysis/premier-league/26-27-season.py` is correct, but the code has a side effect of deleting `__pycache__` at the end (Lines 260-262), which may be unexpected for some users.

---

## 3. Proposed Updated Documentation (README.md)

```markdown
# Premier League 2026-27 Season Simulation

A high-performance Monte Carlo simulation for predicting Premier League outcomes using Elo-based team ratings and vectorized Poisson goal modeling.

## Features

- **Vectorized Match Engine**: JIT-accelerated simulation using Numba for maximum performance.
- **Poisson Goal Modeling**: Realistic scoreline generation incorporating home advantage and match closeness.
- **Dynamic Promotion**: Simulates the impact of different promoted teams (Southampton vs. Hull City) on league outcomes.
- **Monte Carlo Analysis**: Runs 5,000 iterations to generate robust probability distributions.
- **Automated Tiebreakers**: Resolves league positions using Points, Goal Difference, and Goals For.

## Installation

1. Clone the repository.
2. Install the required high-performance libraries:
   ```bash
   pip install numpy numba tqdm
   ```

## Usage

Run the simulation from the repository root:
```bash
python sportsanalysis/premier-league/26-27-season.py
```

The script executes 5,000 simulations and outputs a detailed statistical summary to the console.

## Output

The simulation provides the following statistics:
- **Team Statistics**: Average points, standard deviation, and percentage chance for Title, Champions League (Top 4), Europa League (5th), and Relegation.
- **League Benchmarks**: Maximum and minimum points observed to win the title across all simulations.
- **Relegation Safety**: Probability of a team being relegated despite reaching the "safe" 40-point mark.
- **Excitement Score**: A metric (0-10) where lower values indicate a tighter title race (based on the points gap between 1st and 2nd).

## Algorithm Overview

### 1. Power Ratings
Teams are assigned Elo ratings based on historical performance.
*Note: This version uses base Elo ratings without active form or injury modifiers.*

### 2. Match Simulation
The engine calculates match outcomes using:
- **Expected Goals (xG)**: Derived from the Elo difference between teams, scaled by a logistic function.
- **Home Advantage**: A constant boost (+33.8 Elo) applied to the home team.
- **Shared Goals**: A factor representing the tendency for matches to end in draws when teams are closely matched.
- **Tempo Scaling**: Adjusts goal frequency based on the Elo gap between opponents.

### 3. League Structure
- **19-Team Format**: The simulation currently models an 18-team core with one additional promoted team added per iteration.
- **Qualification**:
  - **Champions League**: Top 4 finishers.
  - **Europa League**: 5th place finisher.
  - **Relegation**: Bottom 3 finishers.

## Dependencies

- **numpy**: Vectorized array operations.
- **numba**: Just-In-Time (JIT) compilation for simulation speed.
- **tqdm**: Real-time progress tracking.

## Disclaimer

This simulation is for entertainment and research purposes. Actual results vary based on hundreds of factors not captured by Elo-based modeling.
```
