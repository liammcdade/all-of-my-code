# Premier League 2026/27 Simulation Suite Documentation

## Module Architecture

The simulation suite comprises three primary scripts located in `sportsanalysis/premier-league/`:

1. **`26-27-season.py`**: The primary entry point for simulating the Premier League season. Consumes European tournament win probabilities from `UCL.py` and `UEL.py`, applies European fatigue adjustments, and runs Monte Carlo simulations for domestic league standings.
2. **`UCL.py`**: Simulates the 2026/27 UEFA Champions League season (36-team Swiss model league phase, playoff ties, two-legged knockout ties, and single-match final).
3. **`UEL.py`**: Simulates the 2026/27 UEFA Europa League season (36-team Swiss model league phase, knockout round playoffs, two-legged knockout ties, and single-match final).

## Key Parameters & Constants

| Constant | File | Value | Description |
| :--- | :--- | :--- | :--- |
| `NUM_PL_SIMS` | `26-27-season.py` | 2000 | Number of Monte Carlo simulations for the Premier League |
| `NUM_CL_SIMS` | `UCL.py` | 2000 | Number of Monte Carlo simulations for the Champions League |
| `NUM_UEL_SIMS` | `UEL.py` | 2000 | Number of Monte Carlo simulations for the Europa League |
| `HOME_ADVANTAGE_ELO` | `UCL.py` | 85.0 | Elo rating bonus awarded to home teams in match expected goals calculations |
| `EUROPEAN_PENALTIES` | `26-27-season.py` | `{"UCL": 45.0, "UEL": 30.0, "UECL": 20.0}` | Elo rating reductions applied to teams competing in European competitions during domestic fixtures |

## Main Functions

### `26-27-season.py`

* `markets_to_latent_elo() -> Dict[str, float]`: Converts fractional betting market odds from `PL_BETTING_MARKETS` across multiple markets into centered, scaled base Elo ratings around 1500.
* `run_single_pl_simulation(registry, fixture_indices, base_ratings, actual_results) -> Tuple[Dict, List[Tuple[str, Dict]]]`: Simulates a single 380-match Premier League season, overriding simulated scores with completed actual scores from `ACTUAL_RESULTS`, applying European fatigue penalties, and returning the updated table and sorted team ranking.
* `run_premier_league_simulation(cl_win_probs, uel_win_probs) -> None`: Coordinates the Premier League simulation loop across `NUM_PL_SIMS` iterations and outputs formatted probability tables.

### `UCL.py`

* `calculate_cl_elos() -> Dict[str, float]`: Derives Elo ratings for all Champions League teams from betting odds.
* `run_champions_league_simulation(num_sims=2000) -> Dict[str, float]`: Runs `NUM_CL_SIMS` Champions League simulations and returns a dictionary mapping English Premier League team names to their probability of winning the Champions League.

### `UEL.py`

* `run_europa_league_simulation(num_sims=2000) -> Dict[str, float]`: Runs `NUM_UEL_SIMS` Europa League simulations and returns a dictionary mapping team names to their probability of winning the Europa League.
