# Documentation Audit Report: Premier League Simulations

**Auditor:** Jules (Senior Technical Writer & Software Documentation Auditor)
**Date:** May 2024
**Scope:** 2025-26 and 2026-27 Premier League Monte Carlo Simulation Scripts

---

## 1. 2026-27 Season Simulation (Root `README.md` vs `26-27-season.py`)

### Mismatches
- **Simulation Iterations:** README states 10,000 simulations (Usage section), but the code `NUM_SIMS` is set to 5,000 (line 181).
- **Promotion Logic:** README claims a "Championship Playoff Simulation" is implemented. In reality, the code performs a simple 50/50 coin flip between Southampton and Hull City (line 194).
- **League Size:** The code simulates a 19-team league (18 fixed + 1 promoted), whereas standard Premier League structure and the README imply a 20-team league.
- **Rating Adjustments:** README lists form, injuries, and WDL tendencies as active ELO adjustments. These features are absent from the match engine in `26-27-season.py`. The `TeamRegistry.add_team` method accepts `form` and `injury` parameters (line 52), but they are never stored or used in simulations.
- **Missing Output Features:** The README describes "Match Probabilities", "Extreme Match Probabilities", and "Team Fixture Probabilities" as generated outputs. These are completely absent from the script's output logic.
- **European Qualification:** README mentions Conference League (6th place), but the script only tracks Top 4 (Champions League) and 5th (Europa League) (lines 208-212).
- **Side Effects:** The script deletes the `__pycache__` directory upon completion (lines 241-243), a side effect not mentioned in the documentation.
- **Dependencies:** `requirements.txt` is missing `numba`, which is a hard dependency for the 26-27 script.

### Suggested Clarifications
- **Numba JIT:** Clarify that the simulation uses Just-In-Time compilation for performance; users may need to install LLVM or specific build tools.
- **Vectorized Engine:** Explain that `run_simulation_vectorized` processes fixtures in bulk for speed, which is why individual match logs aren't available during the simulation.
- **Monte Carlo:** Briefly define this as "running thousands of random scenarios to find the most likely outcomes" for non-technical users.

---

## 2. 2025-26 Season Simulation (`sportsanalysis/premier-league/README.md` vs `25-26-season.py`)

### Mismatches
- **Line Number References:** Nearly all line number citations are incorrect.
    - Elo ratings: Cited lines 8-28; Actual: Line 80.
    - Current table: Cited lines 54-76; Actual: Line 128.
    - Fixtures: Cited lines 78-106; Actual: Line 155.
    - European Competitions: Cited 187-651; Actual: Line 190 (EL/CL/Conf data) and Line 470 (Sampling logic).
- **Home Advantage:** README cites 33.8 Elo points (line 469). The code uses `HOME_ADVANTAGE_ELO = 60` (line 50), randomized between 50 and 70 (line 445).
- **Goal Modeling:** README describes "Logistic scaling". The code uses exponential scaling in `get_expected_goals`: `home_base * math.exp(diff / 800)` (line 244).
- **European Qualification:** README claims 5th place gets CL, 6th gets EL. The code tracks "at least 9 teams" (line 722), but the assignment logic in `assign_europe` (line 683) has complex overrides for tournament winners that aren't fully detailed in the docs.
- **Rating Deviation (RD):** README states RD is "not actively used". However, the `update_elo` function (line 560) uses `g(rd_avg)` (line 396) to scale updates.
- **Execution Path:** README provides `python 25-26-season.py`, which fails if run from the repository root due to file path expectations.

### Suggested Clarifications
- **WDL Bias:** Explain how "observed win/draw/loss rates" are used to adjust the random distribution, as it's a sophisticated feature that is currently undersold.
- **Poisson Model:** Define "Lambda" as "average expected goals per match" to make the algorithm overview more accessible.

---

## 3. Implementation vs. Coding Standards (`instructions.md`)

The documentation fails to reflect that the code violates several internal standards:
- **Rule 4 (Function Size):** `assign_europe` (approx 100 lines) and `main` in 25-26 exceed the 60-line limit.
- **Rule 16 (File Length):** `25-26-season.py` (1046 lines) exceeds the 800-line hard limit.
- **Rule 9 (Data Separation):** Large ELO and fixture dictionaries are embedded in the logic instead of being in JSON/CSV files.

---

## 4. Proposed Updated Documentation Text

### For Root `README.md` (2026-27)
```markdown
## Features
- **Performance**: High-speed simulation using Numba-accelerated vectorized logic.
- **Promotion Modeling**: Stochastic promotion selection between top Championship contenders.
- **League Coverage**: 19-team simulation tracking title race, top 4 qualification, and relegation.

## Algorithm Overview
- **ELO Ratings**: Base team strength ratings used for match probability calculations.
- **Match Engine**: Poisson-based goal distribution with Home Advantage (33.8 Elo) and match-closeness factors.
```

### For `sportsanalysis/premier-league/README.md` (2025-26)
- *Remove all line number references.*
- **Elo System**: "Uses a 400-scale Elo with variable Home Advantage (50-70 points). Rating Deviation (RD) is utilized to weight Elo updates after each match."
- **Goal Model**: "Exponential scaling based on Elo differential, incorporating form adjustments and injury penalties."
