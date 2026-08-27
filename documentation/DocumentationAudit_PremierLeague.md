# Documentation Audit Report: Premier League Simulations

## Overview
This report provides a comprehensive audit of the documentation for the 2025-26 and 2026-27 Premier League simulation projects. It identifies discrepancies between the implemented Python code and the accompanying README files, suggests clarifications for technical concepts, and proposes updated documentation text to ensure accuracy.

---

## 2025-26 Season Audit

### Mismatches

1.  **Line Number References**:
    *   **Mismatch**: The `sportsanalysis/premier-league/README.md` contains numerous incorrect line number references for the `25-26-season.py` script.
    *   **Examples**:
        *   Elo ratings: Documented at lines 8-28; actual location is lines 80-100.
        *   Current Table: Documented at lines 54-76; actual location is lines 128-153.
        *   Fixtures: Documented at lines 78-106; actual location is lines 155-186.
        *   European Elos: Documented at lines 109-130; actual location is lines 190-210.
        *   Excitement Score: Documented at lines 542-576; actual location is lines 610-645.

2.  **FA Cup Logic**:
    *   **Mismatch**: Documentation describes the FA Cup as a "simple Elo-based knockout" (lines 579-754) and mentions simulating the winner.
    *   **Code Reality**: The function `simulate_full_fa_cup_tournament()` (line 241) is hardcoded to only simulate a single match between "Chelsea" and "Man City" using `simulate_fa_cup_match`. There is no actual tournament structure.

3.  **Unused WDL Rates**:
    *   **Mismatch**: Documentation mentions "Observed win/draw/loss rates" as a data input (lines 420-441) and claims they are used to "Boost XG based on team's win-loss differential".
    *   **Code Reality**: The `wdl_rates` dictionary is defined at line 355 but is never accessed by `simulate_match()` or any other part of the simulation engine.

4.  **Expected Goals (XG) Model**:
    *   **Mismatch**: Documentation claims the match engine uses "Logistic scaling (home_xg = 0.7 + 1.8 / (1 + exp(-diff/400))".
    *   **Code Reality**: The `get_expected_goals()` function (line 244) uses an exponential model: `home_lambda = home_base * math.exp(diff / 800)`.

5.  **Simulation Iterations**:
    *   **Mismatch**: Documentation states "10,000 for each European competition".
    *   **Code Reality**: The script runs 10,000 iterations for CL, EL, and Conf pre-simulations (lines 722, 731, 740), but the Premier League Monte Carlo loop is set to 25,000 (line 711). This is consistent, but the wording in the "Overview" could be clearer.

### Clarifications

*   **Elo RD (Rating Deviation)**: The documentation notes RD is "not actively used" but the `update_elo` function (line 560) actually incorporates it into the K-factor calculation: `k_h = K_FACTOR_BASE / (1 + rd_arr[h_idx]/100)`. This should be clarified as RD does impact Elo progression during the simulation.
*   **Excitement Score**: The term "title contenders" and "relegation contenders" used in the Excitement Score calculation should be explicitly defined (e.g., within 3 points of the leader).

---

## 2026-27 Season Audit

### Mismatches

1.  **Simulation Iterations**:
    *   **Mismatch**: The root `README.md` states "Runs 10,000 simulations" under Features and Usage.
    *   **Code Reality**: `NUM_SIMS` is set to 5,000 at line 181 of `26-27-season.py`.

2.  **Championship Promotion Logic**:
    *   **Mismatch**: Documentation claims a "Championship Playoff Simulation: Simulates Championship playoffs to determine promotion".
    *   **Code Reality**: The promotion logic at line 194 is a simple 50/50 coin flip between "Southampton" and "Hull City": `promoted = "Southampton" if random.random() < 0.5 else "Hull City"`. No playoff tournament is simulated.

3.  **ELO Adjustments**:
    *   **Mismatch**: README claims ratings are adjusted for "form, injuries, and win/draw/loss tendencies".
    *   **Code Reality**: While `TeamRegistry.add_team` accepts `form` and `injury` parameters (line 49), they are defaults set to 0.0 and are never updated or used in the `run_simulation_vectorized` logic (lines 107-151). The simulation uses static `ELO_RATINGS`.

4.  **Missing Output Features**:
    *   **Mismatch**: The "Output" section lists "Match Probabilities", "Extreme Match Probabilities", and "Team Fixture Probabilities".
    *   **Code Reality**: These features are completely absent from `26-27-season.py`. The script only outputs Team Statistics, Points to Win League, and Additional Statistics (relegation with 40+ pts, excitement, European prob).

5.  **Excitement Score Calculation**:
    *   **Mismatch**: Root README implies a complex metric based on contenders.
    *   **Code Reality**: The script calculates it as `(leader_pts - second_pts) / 10` (line 213).

### Clarifications

*   **Vectorization**: The documentation does not mention that the 2026-27 script uses a vectorized engine with `numba` for performance, which is a significant architectural change from the 2025-26 version.
*   **19-Team Simulation**: The script simulates an 18-team fixed league plus 1 promoted team, totaling 19 teams, which is unusual for the Premier League (normally 20).

---

## Proposed Updated Documentation (2026-27 README Snippet)

```markdown
## Features
- **ELO-Based Ratings**: Team strength ratings using static ELO values.
- **Performance Optimized**: Uses Numba JIT and vectorization for high-speed Monte Carlo simulations.
- **Dynamic Promotion**: Randomly selects between top Championship contenders for each simulation run.
- **Monte Carlo Simulations**: Runs 5,000 iterations to determine probability distributions.

## Output
- **Team Statistics**: Average points, standard deviation, and probabilities for European spots and relegation.
- **Points to Win League**: Statistical range for the title-winning threshold.
- **Additional Insights**: Final day excitement scores and relegation anomalies.
```
