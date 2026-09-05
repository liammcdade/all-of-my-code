# Premier League 2026-27 Season Simulation

An integrated Monte Carlo simulation suite predicting Premier League 2026-27 outcomes, seamlessly combined with UEFA Champions League (UCL) and UEFA Europa League (UEL) simulations.

## Key Features

- **Market-Implied Latent Elo Ratings**: Derives team strength ratings from bookmaker betting odds across multiple markets (League Winner, Top 2 Finish, Relegation).
- **Integrated European Competitions**: Simulates the 36-team UEFA Champions League (`UCL.py`) and UEFA Europa League (`UEL.py`) using Swiss-model league phases and multi-leg knockout stages.
- **European Squad Fatigue Penalties**: Applies domestic Elo penalties for teams competing in European competitions (UCL: -45.0 Elo, UEL: -30.0 Elo, UECL: -20.0 Elo) to model schedule congestion.
- **Poisson Goal Modeling**: Uses exponential Elo sensitivity scaling for expected goals ($XG_{\text{home}} = 1.5 \times e^{0.002 \Delta}$, $XG_{\text{away}} = 1.2 \times e^{-0.002 \Delta}$) and cached Poisson PMFs.
- **2,000 Monte Carlo Iterations**: Runs 2,000 simulations per competition with deterministic random seeding (`seed=42`).
- **Comprehensive Projections**: Computes average positions, average points, standard deviations, and probabilities for Title, UCL (Top 4), Europa League (5th), Top Half, Survival, Relegation, and European trophy wins.

---

## Installation

1. Clone the repository:
   ```bash
   git clone https://github.com/your-org/All-code-in-one.git
   cd All-code-in-one
   ```
2. Install required dependencies:
   ```bash
   pip install numpy tqdm
   ```

---

## Usage

Run the full simulation suite by executing the main script from the `sportsanalysis/premier-league` directory:

```bash
cd sportsanalysis/premier-league
python 26-27-season.py
```

### Execution Flow
1. **Champions League Simulation**: Simulates 2,000 UCL iterations to determine PL teams' chances of winning the Champions League.
2. **Europa League Simulation**: Simulates 2,000 UEL iterations to determine PL teams' chances of winning the Europa League.
3. **Premier League Simulation**: Derives market-implied Elo ratings, applies European fatigue penalties, incorporates actual played results (`ACTUAL_RESULTS`), and simulates 2,000 domestic league seasons.

---

## Simulation Architecture

```
sportsanalysis/premier-league/
├── 26-27-season.py      # Main entry point & Premier League simulation engine
├── UCL.py               # UEFA Champions League 36-team Swiss model & knockout simulator
├── UEL.py               # UEFA Europa League 36-team Swiss model & knockout simulator
├── test_integration.py  # Integration test suite validating the multi-file pipeline
└── README.md            # Sub-directory documentation
```

---

## Output Metrics

The console output generates a projection table with the following columns:

- **Pos**: Average final league position
- **Team**: Premier League club name
- **Eur**: European competition assignment (`UCL`, `UEL`, or `-`)
- **ELO**: Base market-derived Elo rating
- **Pts**: Mean final points
- **SD**: Standard deviation of final points
- **Title**: Title win probability (%)
- **UCL**: Champions League qualification probability (Top 4 finish, %)
- **Europa**: Europa League qualification probability (5th place finish, %)
- **TopHalf**: Top 10 finish probability (%)
- **StayUp**: Relegation avoidance probability (Positions 1–17, %)
- **Releg**: Relegation probability (Positions 18–20, %)
- **Trophy Win Probs**: Individual team European title probabilities (`CL Win: X.X%`, `UEL Win: X.X%`)

---

## Algorithm Overview

### 1. Market-Implied Latent Elo Ratings
Base Elo ratings are derived from bookmaker odds by converting fractional odds to implied probabilities, removing overround via normalization, and centering log-odds around `LEAGUE_AVERAGE_ELO = 1500.0` with `ELO_SCALE = 400.0` and `ELO_SHRINKAGE = 0.75`.

### 2. Match Engine & Expected Goals
Expected goals are calculated per fixture using exponential Elo scaling:
$$\Delta_{\text{Elo}} = \text{Elo}_{\text{home}} + 85.0 - \text{Elo}_{\text{away}}$$
$$XG_{\text{home}} = 1.5 \times e^{0.002 \times \Delta_{\text{Elo}}}, \quad XG_{\text{away}} = 1.2 \times e^{-0.002 \times \Delta_{\text{Elo}}}$$
Scores are sampled from Poisson distributions using cached probability mass functions.

### 3. European Qualification & Relegation Bounding
League positions determine outcomes:
- **Champions League**: Top 4 teams
- **Europa League**: 5th place
- **Relegation**: Bottom 3 teams (Positions 18–20)
- **Tiebreakers**: Points $\rightarrow$ Goal Difference $\rightarrow$ Goals For

---

## Testing

Run the integration test to verify that the entire pipeline executes properly:

```bash
cd sportsanalysis/premier-league
python test_integration.py
```

---

## License

This project is for educational and research purposes only.
