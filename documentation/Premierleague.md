# Documentation Audit Report: Premier League Simulation Suite (`26-27-season.py`)

## Executive Summary
This audit compares the implementation of the Premier League 2026–27 simulation suite (`sportsanalysis/premier-league/26-27-season.py`) with its associated documentation files (`README.md` at the repository root and `sportsanalysis/premier-league/README.md`).

The codebase underwent a major architectural refactor (commit `34ef55b`) that modularized European competitions into dedicated classes (`EuropeanCompetition`, `PLSimulator`), introduced dynamic European fatigue decay based on elimination status, integrated betting-market latent Elo calculations (`markets_to_latent_elo`), implemented locked real-world results (`ACTUAL_RESULTS`), and updated Champions League qualification rules for 5th-place conditional spots.

However, existing documentation files retain legacy descriptions, phantom feature claims (such as non-existent form/injury adjustments, Championship playoff simulations, and fixture probability tables), incorrect iteration counts, outdated formula references, and incorrect dependency listings.

---

## 1. Code-Documentation Mismatches

| Feature / Category | Documented Behavior (Root `README.md` & Sub `README.md`) | Actual Code Behavior (`26-27-season.py`) | Line Number / Reference |
| :--- | :--- | :--- | :--- |
| **Simulation Iterations** | Claims 10,000 simulations (`README.md`) or 25,000 PL / 10,000 European sims (`sportsanalysis/premier-league/README.md`). | Script sets `NUM_PL_SIMS = 2000`. | Line 26 |
| **Home Advantage** | Claims 33.8 Elo points or +100 Elo equivalent. | Global constant `HOME_ADVANTAGE_ELO = 85.0`. | Line 22 |
| **Power Ratings & ELO** | Claims base ELO is adjusted for form, player injuries, and WDL rates. | ELO ratings are derived dynamically from betting market odds (`markets_to_latent_elo()`). Form, injury penalties, and WDL rates are absent. | Lines 917–967 |
| **Promoted Teams** | Claims Championship playoff simulation determines promoted teams. | Promoted teams (e.g. Hull, Coventry) have ELO derived from betting market odds; no playoff simulation is performed. | Lines 917–967 |
| **Goal Model / Match Engine** | Claims Bivariate Poisson model with "match closeness", "tempo reduction", "shared goals for draws", and "variance adjustments". | Uses exponential xG scaling based on Elo difference: `home_xg = 1.5 * exp(0.002 * diff)`, `away_xg = 1.2 * exp(-0.002 * diff)`. Scores sampled independently from Poisson PMFs. | Lines 79–84, 70–77 |
| **European Architecture** | Claims European qualification is a static assignment (Top 4 CL, 5th EL, 6th UECL) or pre-computed once before the PL loop. | `EuropeanCompetition` class simulates full 8-matchday league phase and knockout phase dynamically inside every unified simulation iteration. | Lines 211–290, 969–1055 |
| **5th Place UCL Qualification** | Unmentioned in documentation. | Implemented in `run_unified_simulation`: if an English club wins UCL or UEL and finishes outside top 4, 5th place receives a conditional UCL spot. | Lines 1018–1034 |
| **European Fatigue Decay** | Unmentioned in documentation. | `EUROPEAN_FATIGUE_BASE` (UCL: 8.0, UEL: 6.0, UECL: 5.0) applies Elo fatigue penalty decaying linearly over the season (`1.0 - progress`) while active in Europe. | Lines 30, 313–338 |
| **Locked Actual Results** | Unmentioned in documentation. | `ACTUAL_RESULTS` dictionary overrides fixture simulation for 15 locked early-season matches. | Lines 370–388, 324–328 |
| **Console Output Features** | Claims output includes "Match Probabilities", "Extreme Match Probabilities", "Team Fixture Probabilities", "Points to Win League", and "Excitement Score". | Output is a single formatted table: `Pos`, `Team`, `Eur`, `ELO`, `Pts`, `SD`, `95%CI`, `Title%`, `UCLQ%`, `5th->UCL%`, `UCLWin%`, `UELWin%`, `UECLWin%`, `AnyEuroWin%`. | Lines 1060–1110 |
| **Dependencies** | Claims `numba` is required for JIT optimization. | Code does not import or use `numba`. Requires `numpy` and `tqdm`. | Lines 17–20 |

---

## 2. Technical & Methodological Clarifications

### Functions & Parameters
- **`markets_to_latent_elo() -> Dict[str, float]`** (Lines 917–967):
  Calculates normalized probabilities from betting market odds across all available markets (`PL_BETTING_MARKETS`), computes logarithmic market weights based on bookmaker efficiency, centers log-probabilities around zero, scales by `ELO_SCALE / ln(10)` (approx. 173.72), and centers ratings around `LEAGUE_AVERAGE_ELO = 1500.0`.
- **`EuropeanCompetition` Class** (Lines 211–290):
  - `__init__(name, fixtures, betting_market, pl_teams)`: Initializes team list, computes Elo ratings from betting market odds using log10 odds ratio.
  - `run_single_league_phase() -> List[str]`: Simulates 8 matchdays for all participating teams using Poisson goal sampling with home advantage (`+85.0` Elo) and returns ranked team names sorted by Points, GD, GF, and uniform tiebreak.
  - `simulate() -> Tuple[Optional[str], Dict[str, int]]`: Simulates league phase and knockout phase (`simulate_knockout_phase`), returning `(winner_name, elimination_rounds_dict)`. Elimination rounds mapping: `-1` = not qualified, `0` = playoff, `1` = R16, `2` = QF, `3` = SF, `4` = finalist, `5` = winner.
- **`PLSimulator.simulate_season(fatigue_info: Dict[str, Tuple[int, str]]) -> Tuple[List[str], Dict[str, int]]`** (Lines 301–347):
  - Parameters: `fatigue_info` maps team names to `(elimination_round, competition_name)`.
  - Behavior: Iterates through `FIXTURES_LIST` (`n_fixtures = 342`). For locked matches in `ACTUAL_RESULTS`, uses fixed goals. For remaining matches, computes linear fatigue decay:
    $$\text{fatigue} = \text{base\_fatigue} \times \left(1.0 - \frac{i}{n\_fixtures - 1}\right)$$
    Active status is determined by `elimination_round >= 0`. Applies fatigue reduction to home/away Elo prior to expected goals calculation.
  - Returns: `(ranking, points_dict)`.

### Side Effects & Global State
- **Random Seeds**: `run_unified_simulation()` explicitly calls `_RNG.seed(42)` and `_NP_RNG.seed(42)` at the start of execution for deterministic reproducibility.
- **Console Output & Logging**: Uses `tqdm` progress bar during simulation and prints ASCII formatted results directly to stdout via `print()`.

---

## 3. Proposed Updated Documentation Text

Below is the proposed, fully aligned documentation text to replace outdated README files.

```markdown
# Premier League 2026-27 Unified Season & European Simulation

A Monte Carlo simulation engine for the 2026–27 Premier League season fully integrated with European club competitions (UEFA Champions League, UEFA Europa League, and UEFA Conference League).

## Key Features

- **Latent ELO Derivation**: Base team ratings are dynamically derived from betting market odds across multiple markets using log-odds normalization and bookmaker efficiency weighting.
- **Unified European Competition Engine**: Simulates full 8-matchday league phases and multi-round knockout phases for UCL, UEL, and UECL inside each Monte Carlo iteration.
- **Dynamic European Fatigue Decay**: Models team fatigue based on active European competition status, decaying linearly across the 38-game domestic season.
- **Conditional UEFA Qualification**: Models 5th-place Champions League qualification conditions triggered when an English club wins the UCL or UEL while finishing outside the top 4.
- **Locked Actual Results**: Incorporates completed early-season match results (`ACTUAL_RESULTS`) into fixture projections.
- **Statistical Confidence Intervals**: Computes 95% confidence intervals, standard deviations, title probabilities, and European trophy probabilities.

## Installation

Ensure Python 3.10+ is installed along with required dependencies:

```bash
pip install numpy tqdm
```

## Usage

Run the unified simulation script from the repository root:

```bash
python sportsanalysis/premier-league/26-27-season.py
```

## Model Architecture

### 1. Market-Derived Latent ELO
Team ratings are derived from betting market probabilities ($P_i$):
1. Compute market efficiency $E = 1 / \sum P_i$ and market weight $W_m = E / \sum E$.
2. Compute centered log-probability: $L_i = \ln(P_i) - \bar{L}$.
3. Convert latent strength to Elo scale:
   $$\text{ELO}_i = 1500 + \frac{400}{\ln(10)} \times L_i$$

### 2. Match Engine & Goal Model
Expected goals (xG) for home ($h$) and away ($a$) teams are calculated using exponential Elo diff scaling:
$$\text{xG}_{\text{home}} = 1.5 \times \exp\left(0.002 \times (\text{ELO}_{\text{home}} + 85.0 - \text{fatigue}_{\text{home}} - \text{ELO}_{\text{away}} + \text{fatigue}_{\text{away}})\right)$$
$$\text{xG}_{\text{away}} = 1.2 \times \exp\left(-0.002 \times (\text{ELO}_{\text{home}} + 85.0 - \text{fatigue}_{\text{home}} - \text{ELO}_{\text{away}} + \text{fatigue}_{\text{away}})\right)$$

Scores are sampled independently from Poisson distributions capped at 10 goals.

### 3. European Fatigue Decay
Active European participants receive a base fatigue penalty ($\text{Base}_{\text{UCL}}=8.0$, $\text{Base}_{\text{UEL}}=6.0$, $\text{Base}_{\text{UECL}}=5.0$) that decays linearly as the domestic fixture schedule progresses:
$$\text{Fatigue}(i) = \text{Base} \times \left(1.0 - \frac{i}{N_{\text{fixtures}} - 1}\right)$$

### 4. Output Statistics
The simulation outputs a formatted table containing:
- **Pos**: Mean projected finishing position.
- **Eur**: Active European competition indicator (UCL, UEL, UECL).
- **ELO**: Market-derived base Elo rating.
- **Pts**: Average projected season points.
- **SD**: Standard deviation of points across simulations.
- **95%CI**: 95% confidence interval for projected points.
- **Title%**: Probability of winning the Premier League title.
- **UCLQ%**: Probability of qualifying for the UEFA Champions League.
- **5th->UCL%**: Probability of 5th place earning a Champions League berth via winner conditions.
- **UCLWin% / UELWin% / UECLWin%**: Probability of winning respective European trophies.
- **AnyEuroWin%**: Combined probability of winning any European trophy.
```
