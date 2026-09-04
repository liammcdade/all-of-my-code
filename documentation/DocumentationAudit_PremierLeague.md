# Documentation Audit Report: Premier League 2026/27 Simulation Suite

**Auditor**: Senior Technical Writer & Software Documentation Auditor
**Scope**: `sportsanalysis/premier-league/26-27-season.py`, `UCL.py`, `UEL.py`, `README.md`, and `sportsanalysis/premier-league/README.md`

---

## 1. Mismatches Between Documentation and Implementation

### Mismatch 1: Simulation Iteration Counts
* **Documentation**: Root `README.md` states "Runs 10,000 simulations grouped by promoted team" and "The script runs 10,000 simulations and outputs results to the console."
* **Code Implementation**:
  - `sportsanalysis/premier-league/26-27-season.py` (line 28): `NUM_PL_SIMS = 2000`
  - `sportsanalysis/premier-league/UCL.py` (line 26): `NUM_CL_SIMS = 2000`
  - `sportsanalysis/premier-league/UEL.py` (line 649): `NUM_UEL_SIMS = 2000`
* **Impact**: Users expecting 10,000 iterations will observe only 2,000 simulations executed per script run. Additionally, there is no grouping of iterations by promoted team in `26-27-season.py`.

### Mismatch 2: Power Ratings & Elo Adjustment Features
* **Documentation**: Root `README.md` claims power ratings use "ELO ratings adjusted for: Form (based on current performance), Injuries (penalty reduction), Win/Draw/Loss rates (bias adjustments)".
* **Code Implementation**:
  - `26-27-season.py` (lines 208-251 `markets_to_latent_elo()`): Base Elo ratings are derived from betting market odds (`PL_BETTING_MARKETS`).
  - `26-27-season.py` (lines 135-143 in `run_single_pl_simulation()`): Elo ratings are adjusted strictly for European fatigue penalties (`EUROPEAN_PENALTIES`: UCL -45.0, UEL -30.0, UECL -20.0).
  - No form tracking, injury penalties, or win/draw/loss bias adjustments are active in `26-27-season.py`.
* **Impact**: Readers are misled regarding the inputs and features of the Premier League rating engine.

### Mismatch 3: Championship Playoff Simulation
* **Documentation**: Root `README.md` lists "Championship Playoff Simulation: Simulates Championship playoffs to determine promotion".
* **Code Implementation**:
  - `26-27-season.py` (lines 298-299): Promoted teams are hardcoded directly into the registry (`PROMOTED_TEAMS = {"Ipswich", "Coventry", "Hull"}` with `PROMOTED_PENALTY = 0`). No Championship playoff simulation takes place in `26-27-season.py`.
* **Impact**: Documentation claims functionality that is absent from the current codebase.

### Mismatch 4: Output Sections & Match Probabilities
* **Documentation**: Root `README.md` describes output sections including "Match Probabilities", "Extreme Match Probabilities", "Team Fixture Probabilities", "Points to Win League", and "Additional Statistics (average excitement score)".
* **Code Implementation**:
  - `26-27-season.py` (lines 334-367): The script outputs a single comprehensive standings table containing: `Pos`, `Team`, `Eur` (European competition status), `ELO`, `Pts`, `SD`, `Title`, `UCL`, `Europa`, `TopHalf`, `StayUp`, and `Releg`, with appended `(CL Win: X%)` or `(UEL Win: Y%)` probabilities.
  - Per-fixture probabilities, extreme outcome tables, points-to-win metrics, and excitement scores are not computed or printed by `26-27-season.py`.
* **Impact**: Users attempting to locate fixture breakdown tables will find that the output differs substantially from the documentation.

### Mismatch 5: European Qualification Assignment
* **Documentation**: Root `README.md` states: "Conference League: 6th place".
* **Code Implementation**:
  - `26-27-season.py` (lines 320-332): Tracks Champions League (top 4, `pos <= 4`) and Europa League (5th place, `pos == 5`). Conference League qualification is omitted from the tracking dictionaries and console output.
* **Impact**: Inconsistent description of European tournament qualifying slots.

### Mismatch 6: Module Dependencies
* **Documentation**: Root `README.md` lists `numba` under dependencies ("numba: JIT compilation for performance optimization").
* **Code Implementation**:
  - `26-27-season.py`, `UCL.py`, and `UEL.py` rely on `numpy`, `tqdm`, `math`, `random`, `collections`, `itertools`, and `typing`. `numba` is not imported or used in the 2026/27 simulation suite.
* **Impact**: Unnecessary dependency listed for running the 2026/27 simulation suite.

---

## 2. Suggested Clarifications

1. **Betting Market Latent Elo Derivation**:
   - Clarify how `markets_to_latent_elo()` in `26-27-season.py` (lines 208-251) and `calculate_cl_elos()` / `calculate_elo_ratings()` in `UCL.py` / `UEL.py` convert fractional betting market odds into latent Elo ratings centered around a base Elo of 1500.
2. **European Fatigue Penalty**:
   - Explain that teams competing in European tournaments suffer an Elo reduction during domestic league fixture evaluations (`EUROPEAN_PENALTIES`: UCL -45.0, UEL -30.0, UECL -20.0) to model mid-week fatigue.
3. **European Competition Integration**:
   - Explicitly describe the workflow: `26-27-season.py` invokes `run_champions_league_simulation()` from `UCL.py` and `run_europa_league_simulation()` from `UEL.py` first to derive European winner probabilities before executing the Premier League Monte Carlo loop.
4. **Poisson Goal Sampling**:
   - Detail the Poisson expectation model where home expected goals ($xG_H$) and away expected goals ($xG_A$) are calculated using exponential scaling on Elo differences, combined with precomputed Poisson PMFs (`_poisson_pmf()`) in `UCL.py`.

---

## 3. Updated Documentation Text

*(See updated `README.md` and `documentation/Premierleague.md` in the repository.)*
