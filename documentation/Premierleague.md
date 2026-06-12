# Premier League Simulation Documentation Audit Report

## 1. 2025-26 Season Simulation
**Files:** `sportsanalysis/premier-league/25-26-season.py` vs `sportsanalysis/premier-league/README.md`

### Mismatches
1.  **Line Number Inaccuracies:** The README contains outdated line number references throughout.
    *   **Elo Ratings:** README cites lines 8-28; actual code lines 73-94.
    *   **Current Table:** README cites lines 54-76; actual code lines 122-145.
    *   **Fixtures:** README cites lines 78-106; actual code lines 153-177.
    *   **Model Parameters:** README cites line 469 for Home Advantage; actual code line 41 and 489.
2.  **Home Advantage Value:** README specifies 33.8 Elo points. The code defines `HOME_ADVANTAGE_ELO` as 60 (line 41) and randomizes it between 50-70 during simulations (line 489).
3.  **Expected Goals (xG) Model:** README describes a "Logistic scaling" formula for xG. The code's `get_expected_goals` function (lines 206-212) uses an exponential model: `home_base * math.exp(diff / 800)`.
4.  **European Qualification Threshold:** README mentions reporting probabilities for "8+ European teams". The code (line 741) checks for `len(european_teams) >= 9`.
5.  **European Tournament Structure:** README implies a more dynamic simulation of semi-finals. The code uses hardcoded teams for semi-finals and finals (lines 665-684) and simulates the outcomes from there.
6.  **Simulation Counts:** README mentions 10,000 simulations for each European competition. While true for the tournament winner loops, the FA Cup simulation (`FA_SIMS`) is set to 1,000 (line 55).

### Suggested Clarifications
*   **xG Model:** Clarify the shift from the described logistic scaling to the implemented exponential scaling in `get_expected_goals`.
*   **Home Advantage:** Explicitly state that Home Advantage is randomized between 50 and 70 Elo points rather than being a static value of 33.8.
*   **European Logic:** Clarify that the European simulations are currently based on hardcoded semi-finalists rather than a full tournament bracket from earlier stages.

---

## 2. 2026-27 Season Simulation
**Files:** `sportsanalysis/premier-league/26-27-season.py` vs `README.md` (root)

### Mismatches
1.  **Simulation Iterations:** Root README states 10,000 simulations. The code (`NUM_SIMS`, line 155) is set to 5,000.
2.  **League Size:** The code simulates a 19-team league (18 fixed teams + 1 promoted), whereas the standard Premier League and the README imply a 20-team structure.
3.  **Promotion Logic:** README describes a "Championship Playoff Simulation". The code implements a simplified 50/50 coin flip between Southampton and Hull City (line 161).
4.  **Missing Features:**
    *   **Adjustments:** README lists adjustments for form, injuries, and WDL tendencies. These are not implemented in the 2026-27 match engine logic (the `run_simulation_vectorized` function uses base Elo ratings).
    *   **Output Types:** README lists "Extreme Match Probabilities" and "Team Fixture Probabilities" as features, but these outputs are absent from the 2026-27 script's execution.
5.  **Excitement Score Calculation:** The code calculates excitement based on the points gap between 1st and 2nd place divided by 10 (line 213), which is much simpler than the multi-factor calculation described in the 2025-26 documentation.

### Suggested Clarifications
*   **League Structure:** Explain why the simulation uses 19 teams instead of 20.
*   **Match Engine Limitations:** Clarify that the 2026-27 version uses a vectorized engine that prioritizes performance over the complex form/injury adjustments found in the 2025-26 version.
*   **Promotion:** Update the description of the promotion simulation to reflect the simplified selection logic.

---

## 3. Proposed Documentation Updates (General)

### Update for 2025-26 README
Update the xG formula description:
```markdown
- **Expected Goals (XG)**: Exponential scaling (home_xg = home_base * exp(diff/800), away_xg = away_base * exp(-diff/800)).
```

Correct line number references and Home Advantage:
```markdown
- **Elo Ratings**: Base Elo scores for Premier League teams (lines 73-94).
- **Model Parameters**: Home advantage (Randomized 50-70 Elo points).
```

### Update for 2026-27 README
Adjust feature list to match implemented vectorized logic:
```markdown
- **Vectorized Match Simulation**: High-performance simulation using Numba-accelerated Poisson goal modeling.
- **Simplified Promotion**: Probabilistic selection of promoted teams (Southampton/Hull City).
- **Core Statistics**: Focuses on average points, title, European, and relegation probabilities.
```
