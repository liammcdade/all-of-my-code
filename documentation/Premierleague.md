# Premier League 2026/27 Simulation Suite Reference Documentation

## Overview

The Premier League 2026/27 Simulation Suite is an integrated Monte Carlo simulation system designed to model the 2026–27 English Premier League season alongside its major European companion competitions: the UEFA Champions League (UCL) and UEFA Europa League (UEL).

The simulation pipeline consists of three core Python modules:
- **`sportsanalysis/premier-league/UCL.py`**: Simulates the 36-team UEFA Champions League (Swiss-model league phase and two-legged knockout phase).
- **`sportsanalysis/premier-league/UEL.py`**: Simulates the 36-team UEFA Europa League (Swiss-model league phase and two-legged knockout phase).
- **`sportsanalysis/premier-league/26-27-season.py`**: Main entry point that consumes UCL and UEL winner probabilities, applies European squad fatigue penalties to Premier League teams, derives market-implied latent Elo ratings, and simulates 2,000 domestic league seasons.

---

## Architecture & Data Flow

```
+------------------------+      +------------------------+
|       UCL.py           |      |        UEL.py          |
| Champions League Sim   |      |  Europa League Sim     |
| (2,000 simulations)    |      |  (2,000 simulations)   |
+-----------+------------+      +-----------+------------+
            |                               |
            | UCL Win Probs                 | UEL Win Probs
            +---------------+---------------+
                            |
                            v
+--------------------------------------------------------+
|              26-27-season.py                           |
| 1. Apply European Fatigue Penalties                   |
| 2. Derive Market-Implied Latent Elo Ratings           |
| 3. Simulate 2,000 Premier League Seasons              |
| 4. Compute Projections & Output Final Statistics Table |
+--------------------------------------------------------+
```

---

## Technical Specifications & Mathematical Models

### 1. Market-Implied Latent Elo Ratings (`markets_to_latent_elo`)

Base Elo ratings for Premier League teams are derived directly from bookmaker fractional betting odds across three markets: "League Winner" (weight 1.00), "Top 2 Finish" (weight 0.55), and "Relegation" (weight 0.45).

#### Odds Conversion
Fractional odds $(n, d)$ are converted to raw implied probability:
$$p = \frac{d}{n + d}$$

#### Market Normalization & Log-Odds Centering
Raw market probabilities are normalized so they sum to $1.0$:
$$\hat{p}_i = \frac{p_i}{\sum_j p_j}$$
Log-probabilities are centered relative to the market mean:
$$c_i = \ln(\hat{p}_i) - \frac{1}{N} \sum_{k=1}^N \ln(\hat{p}_k)$$

#### Latent Rating Scaling
Weighted latent ratings $L_i$ are converted to Elo ratings relative to `LEAGUE_AVERAGE_ELO` ($1500.0$), scaled by `ELO_SCALE` ($400.0$) and `ELO_SHRINKAGE` ($0.75$):
$$\text{Elo}_i = 1500.0 + 0.75 \times \frac{400.0}{\ln(10)} \times L_i$$

### 2. Expected Goals (XG) Model (`compute_expected_goals`)

Match scoring uses an exponential Elo sensitivity model to compute expected goals ($XG$):
$$\Delta_{\text{Elo}} = \text{Elo}_{\text{home}} + \text{Home Advantage} - \text{Elo}_{\text{away}}$$
$$XG_{\text{home}} = 1.5 \times e^{0.002 \times \Delta_{\text{Elo}}}$$
$$XG_{\text{away}} = 1.2 \times e^{-0.002 \times \Delta_{\text{Elo}}}$$

- **Base Home XG**: `BASE_HOME_XG = 1.5`
- **Base Away XG**: `BASE_AWAY_XG = 1.2`
- **Sensitivity**: `XG_ELO_SENSITIVITY = 0.002`
- **Home Advantage**: `HOME_ADVANTAGE_ELO = 85.0` (in `UCL.py` and `26-27-season.py`)

### 3. Goal Sampling (`sample_score` & `_poisson_pmf`)

Goals are sampled independently from Poisson distributions parameterised by $XG_{\text{home}}$ and $XG_{\text{away}}$.
To ensure high execution performance across 2,000 iterations:
- Factorials up to `MAX_GOALS = 10` are precomputed in `_FACTORIALS`.
- Truncated Poisson PMFs are cached in `_POISSON_CACHE` indexed by rounded lambdas.
- Inverse transform sampling (`np.searchsorted` on CDF) selects goal values bounded by $[0, 10]$.

### 4. European Fatigue Penalties (`EUROPEAN_PENALTIES`)

Teams competing in European competitions incur an Elo reduction during domestic Premier League match simulations to reflect squad rotation and fixture congestion:
- **Champions League (UCL)**: $-45.0$ Elo points
- **Europa League (UEL)**: $-30.0$ Elo points
- **Conference League (UECL)**: $-20.0$ Elo points

In `26-27-season.py`, fatigue assignments are set as follows:
- **UCL Teams**: Arsenal, Aston Villa, Liverpool, Man City, Man United
- **UEL Teams**: Bournemouth, Sunderland, Crystal Palace

---

## Global Configuration & Key Parameters

| Constant | Value | Module | Description |
| :--- | :--- | :--- | :--- |
| `NUM_PL_SIMS` | `2000` | `26-27-season.py` | Number of Premier League Monte Carlo iterations |
| `NUM_CL_SIMS` | `2000` | `UCL.py` | Number of Champions League Monte Carlo iterations |
| `NUM_UEL_SIMS` | `2000` | `UEL.py` | Number of Europa League Monte Carlo iterations |
| `HOME_ADVANTAGE_ELO` | `85.0` | `UCL.py` / `26-27-season.py` | Elo bonus awarded to home team in domestic & European matches |
| `LEAGUE_AVERAGE_ELO` | `1500.0` | `UCL.py` | Baseline Elo for average team strength |
| `ELO_SCALE` | `400.0` | `UCL.py` | Standard Elo logistic scale factor |
| `ELO_SHRINKAGE` | `0.75` | `UCL.py` | Shrinkage factor applied to latent Elo ratings |
| `BASE_HOME_XG` | `1.5` | `UCL.py` | Baseline home expected goals |
| `BASE_AWAY_XG` | `1.2` | `UCL.py` | Baseline away expected goals |
| `XG_ELO_SENSITIVITY` | `0.002` | `UCL.py` | Exponential multiplier for Elo difference in XG calculation |
| `EXTRA_TIME_XG_FACTOR` | `0.5` | `UCL.py` | Multiplier applied to XG during extra time in knockout ties |

---

## Module Specifications

### Module 1: `sportsanalysis/premier-league/26-27-season.py`

#### Functions
- `_fractional_to_probability(odds_tuple: Tuple[int, int]) -> float`
  - Converts a fractional odds tuple (e.g. `(4, 5)`) to an implied probability ($d / (n+d)$).
- `_probability_to_elo(prob: float, base_elo: float = 1500.0) -> float`
  - Converts a probability to an Elo rating relative to `base_elo`.
- `markets_to_latent_elo() -> Dict[str, float]`
  - Calculates base Elo ratings for all 20 Premier League teams by blending League Winner, Top 2, and Relegation odds. Returns a dict mapping team names to Elo ratings.
- `_parse_locked_scores(fixtures: List[Tuple[str, str]], locked: List[str]) -> Dict[Tuple[str, str], Tuple[int, int]]`
  - Parses score strings into fixture score mappings.
- `run_single_pl_simulation(registry: TeamRegistry, fixture_indices: List[Tuple[int, int]], base_ratings: Dict[str, float], actual_results: Dict) -> Tuple[Dict, List[Tuple[str, Dict]]]`
  - Simulates one 38-game Premier League season for 20 teams (342 total fixtures in `FIXTURES_LIST`). Applies European fatigue penalties, simulates unplayed games using Poisson XG, incorporates actual played results (`ACTUAL_RESULTS`), and returns table statistics and final standings.
- `run_premier_league_simulation(cl_win_probs: Dict[str, float], uel_win_probs: Dict[str, float]) -> None`
  - Sets up European status, seeds random number generators (seed `42`), executes 2,000 PL simulations, and prints formatted summary statistics to console.
- `main() -> None`
  - Main entry point that sets random seeds, invokes `run_champions_league_simulation()`, `run_europa_league_simulation()`, and `run_premier_league_simulation()`.

#### Classes
- `TeamRegistry`
  - High-performance mapping class using `__slots__ = ('elos', 'team_to_idx', 'idx_to_team')` for fast indexing during simulation loops.

#### Side Effects
- Prints progress bars (`tqdm`) and formatted ASCII tables to console output.

---

### Module 2: `sportsanalysis/premier-league/UCL.py`

#### Functions
- `calculate_cl_elos() -> Dict[str, float]`
  - Converts Champions League winner betting odds (`BETTING_MARKETS_CL_WINNER`) into normalized Elo ratings for 36 teams relative to equal-baseline probability ($1/36$).
- `simulate_playoff_ties(elos: Dict[str, float]) -> List[str]`
  - Simulates 2nd leg of live playoff ties (`LIVE_PLAYOFF_TIES`), incorporating extra time and penalty shootouts as needed.
- `generate_swiss_fixtures(teams: List[str], num_rounds: int = 8) -> List[Tuple[int, int]]`
  - Generates balanced 8-round Swiss-model league phase fixtures (4 home, 4 away per team) using a circle-method pairing algorithm.
- `run_single_cl_simulation(teams: List[str], elos: Dict[str, float], fixture_indices: List[Tuple[int, int]]) -> List[str]`
  - Simulates 8 league phase rounds for 36 teams and returns teams ranked by points, goal difference, and goals scored.
- `simulate_two_legged_tie(team1: str, team2: str, elos: Dict[str, float]) -> str`
  - Simulates a two-legged knockout tie with home advantage per leg, extra time (0.5x XG factor), and penalty shootouts based on Elo probability ($P_1 = \frac{1}{1 + 10^{-\Delta/400}}$).
- `simulate_knockout_phase(qualified_teams: List[str], elos: Dict[str, float]) -> str`
  - Simulates the full knockout structure: Top 8 teams advance directly to Round of 16; teams 9–24 play 2-legged knockout playoffs. Proceeds through R16, Quarter-finals, Semi-finals, and Final (single neutral-venue match) to produce a tournament champion.
- `run_champions_league_simulation(num_sims: int = 2000) -> Dict[str, float]`
  - Executes `num_sims` complete Champions League simulations and returns a dictionary mapping Premier League team names to their probability of winning the Champions League.

---

### Module 3: `sportsanalysis/premier-league/UEL.py`

#### Functions
- `run_europa_league_simulation(num_sims: int = 2000) -> Dict[str, float]`
  - Instantiates `EuropaLeagueSwissModel`, calculates Elo ratings from `BETTING_MARKETS["UEL Winner"]`, simulates remaining playoffs, and runs 2,000 simulations of the 36-team Swiss model league phase and knockout phase. Returns a dictionary mapping all participating teams to their UEL title probabilities.

#### Classes
- `EuropaLeagueSwissModel`
  - Encapsulates Europa League state, team lists (20 confirmed + 12 UEL playoff winners + 4 CL playoff losers = 36 teams), standings tracking, fixture generation, match simulation, and knockout phase execution.

---

## Output Metrics & Statistical Table

The simulation suite outputs a console table displaying:
- **Pos**: Average final league position across 2,000 simulations.
- **Team**: Premier League team name.
- **Eur**: European competition status (`UCL`, `UEL`, or `-`).
- **ELO**: Base market-derived Elo rating.
- **Pts**: Average final points.
- **SD**: Standard deviation of final points.
- **Title**: Title win probability (%).
- **UCL**: Champions League qualification probability (Top 4 finish, %).
- **Europa**: Europa League qualification probability (5th place finish, %).
- **TopHalf**: Top 10 finish probability (%).
- **StayUp**: Relegation avoidance probability (Positions 1–17, %).
- **Releg**: Relegation probability (Positions 18–20, %).
- **Trophy Win Probs**: Appended text showing Champions League win probability (`CL Win: X.X%`) and Europa League win probability (`UEL Win: X.X%`).

---

## Installation & Execution

### Prerequisites
Install Python dependencies:
```bash
pip install numpy tqdm
```

### Running the Full Simulation Pipeline
Execute `26-27-season.py` directly from the `sportsanalysis/premier-league` directory:
```bash
cd sportsanalysis/premier-league
python 26-27-season.py
```

### Running Integration Tests
To verify all modules run cleanly without errors:
```bash
cd sportsanalysis/premier-league
python test_integration.py
```
