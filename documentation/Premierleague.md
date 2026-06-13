# Premier League Simulation Documentation Audit Report

## 1. Mismatches

### 2025-26 Season Simulation (`25-26-season.py` vs `sportsanalysis/premier-league/README.md`)

*   **Line References:** The README contains numerous outdated line number references:
    *   Elo ratings cited at lines 8-28 (actual: 80-100).
    *   Current table cited at lines 54-76 (actual: 128-154).
    *   Fixtures cited at lines 78-106 (actual: 155-181).
    *   European Elos cited at lines 109-130 (actual: 183-205).
    *   Match engine cited at lines 478-523 (actual: 489-536).
*   **XG Model:** README describes "logistic scaling" (line 120), but `get_expected_goals` (line 253) uses an exponential model: `home_base * math.exp(diff / 800)`.
*   **Home Advantage:** README cites 33.8 Elo points (line 45), but `HOME_ADVANTAGE_ELO` is defined as 60 (line 61) and randomized between 50 and 70 in `run_single_simulation` (line 538).
*   **European Qualification Reporting:** README mentions tracking "8+ European teams" (line 152), but the code tracks "at least 9 teams" (`len(european_teams) >= 9` at line 837).
*   **Rating Deviation (RD):** README states RD is "not actively used" (line 30), but `update_elo` (line 622) uses it to calculate the `g_val` and K-factor adjustments.

### 2026-27 Season Simulation (`26-27-season.py` vs Root `README.md`)

*   **League Size:** The script simulates a 19-team league (18 fixed + 1 promoted), while the README and standard Premier League structure imply 20 teams.
*   **Simulation Count:** README claims 10,000 simulations (line 11), but `NUM_SIMS` in the code is set to 5,000 (line 181).
*   **Implementation Gaps:**
    *   README lists "adjustments for form, injuries, and win/draw/loss tendencies" (line 7), but these are not implemented in the 26-27 script (unlike the 25-26 version).
    *   README mentions "Pre-Season Match Probabilities" (line 11), "Match Probabilities" (line 33), and "Extreme Match Probabilities" (line 34) as outputs, but none of these features are implemented in `26-27-season.py`.
*   **Championship Promotion:** README describes "Championship playoff simulation" (line 10), but the code uses a simple 50/50 coin flip between Southampton and Hull City (line 194).

### Technical Discrepancies & Potential Bugs

*   **JIT Global State Bug:** In `25-26-season.py`, several global variables used for simulation (e.g., `HOME_ADVANTAGE_ELO`, `SEASON_DRAW_RATE`) are modified in the main loop but used within `@numba.jit` functions. This can lead to the JIT-compiled code using stale values if the functions were already compiled with the initial global state.
*   **European Finals Structure:** Documentation implies a full tournament structure, but the scripts often jump directly to semi-finals or use simplified single-match finals (e.g., `simulate_full_fa_cup_tournament` at line 249 in 25-26).

### Coding Standard Violations (`instructions.md`)

*   **Rule 9 (Giant Dictionaries):** Both scripts embed large datasets (Elo ratings, fixture lists, current tables) directly in the code, violating the rule to move them to external files.
*   **Rule 16 (File Length):** `25-26-season.py` is 1046 lines, exceeding the 800-line hard limit.
*   **Rule 4 (Function Size):** `main()` in `26-27-season.py` is approximately 89 lines long, exceeding the 60-line maximum.

## 2. Suggested Clarifications

*   **Excitement Score:** Clarify that the "Excitement Score" is a custom heuristic. In 25-26, it factors in title, top 4, and relegation races (lines 669-693). In 26-27, it is simply the point gap between 1st and 2nd place divided by 10 (line 222).
*   **European Winners:** Clarify that European competition winners are sampled from pre-computed probabilities rather than being simulated in parallel with the league season (lines 805-824 in 25-26-season.py).
*   **JIT Compilation:** Mention that `numba` is required for the 26-27 simulation, as it heavily relies on `@numba.jit` for performance in the vectorized engine.

## 3. Proposed Documentation Updates

### For `sportsanalysis/premier-league/README.md` (2025-26)

*   Update all line number references to match the current script version.
*   Correct the Home Advantage value to "Randomized between 50-70 Elo points".
*   Update XG model description to "Exponential scaling: `base * exp(diff/800)`".
*   Update European qualification probability to "9+ teams" to align with script logic.

### For Root `README.md` (2026-27)

*   Correct the simulation count to 5,000.
*   Note that the current simulation uses a 19-team format with a single randomized promoted team.
*   Remove mentions of form, injury, and WDL adjustments until they are implemented.
*   Remove mentions of Match/Fixture probabilities from the Output section as they are currently unavailable in this version.
*   Clarify that Championship promotion is currently a 50/50 random selection.
