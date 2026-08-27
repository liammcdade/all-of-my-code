# Documentation Audit Report: Premier League Simulation

**Auditor:** Jules (Senior Technical Writer & Software Documentation Auditor)
**Date:** May 22, 2024
**Scope:** `sportsanalysis/premier-league/26-27-season.py`, `sportsanalysis/premier-league/25-26-season.py`, and `sportsanalysis/premier-league/README.md`

---

## 1. Mismatches (Code vs. Documentation)

### A. Simulation Parameters (2026-27 Season)
- **Mismatch:** The README states the script runs 10,000 simulations (Usage section).
- **Reality:** `26-27-season.py` (Line 181) defines `NUM_SIMS = 5000`.
- **Mismatch:** The README claims Monte Carlo simulations are "grouped by promoted team."
- **Reality:** While the script randomly selects a promoted team (Southampton or Hull City) at Line 194, it aggregates all results into a single set of statistics without grouping or separate reporting by promoted team.

### B. Feature Implementation (2026-27 Season)
- **Mismatch:** README lists "Match Probabilities," "Extreme Match Probabilities," and "Team Fixture Probabilities" as generated outputs.
- **Reality:** These features are **completely missing** from the 26-27 script. They appear to be remnants from the 25-26 version (`25-26-season.py`).
- **Mismatch:** README describes a "Championship Playoff Simulation" to determine promotion.
- **Reality:** Promotion is handled by a simplified 50/50 coin flip between Southampton and Hull City at Line 194: `promoted = "Southampton" if random.random() < 0.5 else "Hull City"`.

### C. Algorithm Logic (2026-27 Season)
- **Mismatch:** README (Algorithm Overview) claims ELO ratings are adjusted for Form, Injuries, and WDL rates.
- **Reality:** Although the `add_team` method (Line 51) accepts `form` and `injury` parameters, they are **never used** in the simulation logic. The vectorized engine `run_simulation_vectorized` (Line 107) uses base ELO only.
- **Mismatch:** README (European Qualification) mentions "Conference League: 6th place."
- **Reality:** The 26-27 script only tracks Champions League (Top 4) and Europa League (5th place). Conference League qualification is omitted from the aggregation logic (Lines 206-211) and the output table (Lines 282-296).

### D. 2025-26 Season Discrepancies
- **Mismatch:** The 25-26 script (`25-26-season.py`) tracks "at least 9 European teams," while the 25-26 README (noted in memory but not provided in current context) likely refers to 8+ teams.
- **Mismatch:** The 25-26 script contains a `wdl_rates` dictionary (Line 355) that is **entirely unused** by the simulation engine.
- **Mismatch:** The 25-26 script uses an exponential XG model (`exp(diff/800)`) whereas the 26-27 script uses a logistic model (Logistic scaling). The documentation fails to distinguish between these two different modeling approaches.

---

## 2. Suggested Clarifications

### Jargon & Technical Concepts
- **ELO-Based Ratings:** The documentation assumes the audience understands ELO mechanics. A brief note explaining that higher ELO indicates higher probability of winning would be beneficial.
- **Poisson Goal Modeling:** Clarify that this is a statistical distribution used to predict the number of independent events (goals) occurring in a fixed interval (a match).
- **Monte Carlo Simulation:** Explain that this involves running thousands of random trials to generate a probability distribution of outcomes.
- **Vectorized Engine:** (Internal) The 26-27 script uses NumPy vectorization for performance, but this is undocumented. If "Configurable Parameters" are mentioned, the documentation should specify that many are hardcoded as constants in the script.

### Instructions & Assumptions
- **Dependency Missing:** The `README.md` (Line 30) mentions `pip install -r requirements.txt`. However, the root `requirements.txt` is missing `numba`, which is a critical dependency for both scripts.
- **Execution Path:** The README assumes the user is in the repository root. Running the scripts from within the `sportsanalysis/premier-league/` directory may cause issues if file paths are relative.

---

## 3. Proposed Documentation Updates (for `sportsanalysis/premier-league/README.md`)

### Algorithm Overview (Revised)
Uses a Monte Carlo approach (5,000 simulations) with a Numba-accelerated vectorized engine.
1. **Power Ratings**: Uses base ELO ratings for all teams. Note: Form and injury adjustments are placeholders in the current implementation.
2. **Promotion Logic**: Randomly selects one of two Championship teams (Southampton or Hull City) for each simulation run.
3. **Match Simulation**: Uses a logistic scaling factor for ELO differences, mapped to Poisson-distributed goals with home advantage and shared goal (draw) logic.

### Output Features (Revised)
- **Team Statistics**: Average points, standard deviation, and percentage probabilities for Title, Top 4 (CL), 5th Place (EL), and Relegation.
- **League Metrics**: Minimum and maximum points required for the title across all simulations.
- **Excitement Score**: A calculation based on the points gap between the leader and second place.

### Installation Update
```bash
pip install -r requirements.txt numba
```

---

## 4. Coding Standards Compliance Notes
- **Rule 4 & 16 (Size):** `25-26-season.py` violates the 800-line limit (1046 lines). The `main()` function in `26-27-season.py` (89 lines) exceeds the 60-line maximum.
- **Rule 9 (Data):** Both scripts violate the rule against giant dictionaries in logic; ELO ratings and fixtures should be moved to JSON/CSV.
- **Rule 15 (Dataclasses):** The 26-27 script uses nested dictionaries for results instead of the required Dataclasses (though 25-26 correctly uses them).
- **Rule 21 (Config):** While constants are defined, some parameters (like promotion 50/50) are hardcoded within function logic.
