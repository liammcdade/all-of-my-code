# Premier League 2026/27 Simulation Suite

## Overview
This directory contains the Python simulation suite for the 2026–27 Premier League season and integrated UEFA European competitions. The model combines market-implied Elo ratings, Poisson goal models, European fatigue adjustments, and 36-team Swiss-model European tournaments to project domestic and European outcomes.

---

## File Structure

- **`26-27-season.py`**: Main entry point and domestic simulation engine. Derives team strength from betting odds, applies European fatigue penalties, simulates 2,000 Premier League seasons, and displays final projections.
- **`UCL.py`**: UEFA Champions League simulation module. Models 36 teams playing an 8-round Swiss-model league phase and two-legged knockout ties to produce UCL title probabilities.
- **`UEL.py`**: UEFA Europa League simulation module (`EuropaLeagueSwissModel`). Models 36 teams playing an 8-round Swiss-model league phase and two-legged knockout ties to produce UEL title probabilities.
- **`test_integration.py`**: Integration test script that executes `26-27-season.py`, `UCL.py`, and `UEL.py` end-to-end to verify pipeline integrity.

---

## Model Components

### 1. Market-Implied Latent Elo Ratings
Base team strength is calculated in `26-27-season.py` (`markets_to_latent_elo`) from bookmaker odds across three markets:
- **League Winner** (100% weight)
- **Top 2 Finish** (55% weight)
- **Relegation** (45% weight)

Odds are converted to normalized probabilities, log-centered around `LEAGUE_AVERAGE_ELO = 1500.0`, and scaled with `ELO_SCALE = 400.0` and `ELO_SHRINKAGE = 0.75`.

### 2. European Squad Fatigue Adjustments
Teams competing in European tournaments receive an Elo penalty during domestic Premier League match calculations (`EUROPEAN_PENALTIES`):
- **UCL**: $-45.0$ Elo (Arsenal, Aston Villa, Liverpool, Man City, Man United)
- **UEL**: $-30.0$ Elo (Bournemouth, Sunderland, Crystal Palace)
- **UECL**: $-20.0$ Elo

### 3. Match Engine & Goal Modeling
Match expected goals ($XG$) use exponential Elo sensitivity (`UCL.py`):
$$XG_{\text{home}} = 1.5 \times e^{0.002 \times (\text{Elo}_{\text{home}} + 85.0 - \text{Elo}_{\text{away}})}$$
$$XG_{\text{away}} = 1.2 \times e^{-0.002 \times (\text{Elo}_{\text{home}} + 85.0 - \text{Elo}_{\text{away}})}$$
Goals are sampled from Poisson distributions with cached probability lookup tables up to `MAX_GOALS = 10`.

---

## Usage

Run the main simulation from this directory:
```bash
python 26-27-season.py
```

Run integration tests:
```bash
python test_integration.py
```

### Dependencies
- `numpy`
- `tqdm`
