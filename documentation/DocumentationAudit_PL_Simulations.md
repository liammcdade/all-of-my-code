# Documentation Audit Report: Premier League Simulation (26-27 Season)

## Mismatches

1. **Simulation Iterations**: The `README.md` (root) states the script runs 10,000 simulations, but the code in `sportsanalysis/premier-league/26-27-season.py` (line 181) defines `NUM_SIMS = 5000`.
2. **League Size**: The script simulates a 19-team league (`TEAM_NAMES` at line 23 has 18 teams, plus 1 promoted team), whereas the README's algorithm overview implicitly assumes the standard 20-team Premier League structure.
3. **Form and Injury Adjustments**: The `README.md` (Algorithm Overview > Power Ratings) claims Elo ratings are adjusted for Form and Injuries. However, in `26-27-season.py`, these features are not implemented; base Elo ratings from `ELO_RATINGS` (line 33) are used without any modifiers in the match engine.
4. **Championship Playoff Simulation**: The `README.md` describes a "Championship playoffs" simulation. In contrast, the code (line 194) uses a simple 50/50 coin flip to select the promoted team: `promoted = "Southampton" if random.random() < 0.5 else "Hull City"`.
5. **Output Features**: The `README.md` (Output section) lists "Match Probabilities," "Extreme Match Probabilities," and "Team Fixture Probabilities" as generated outputs. These features are completely absent from the script's `main()` function (line 153) and output logic.
6. **European Qualification Logic**: The `README.md` describes qualification for the Conference League (6th place). The script's logic (lines 208-212) only tracks Title (1st), Champions League (Top 4), and Europa League (5th).
7. **Excitement Score Calculation**: The `README.md` implies a complex calculation based on title, top 4, and relegation contenders. The code (lines 213-214) calculates it simply as the points difference between the leader and second place: `excitement_scores.append(leader_pts - second_pts)`.

## Suggested Clarifications

1. **Undocumented Components**: The `TeamRegistry` class (lines 43-69) and the vectorized simulation engine (`run_simulation_vectorized`, lines 115-151) are core internal components that are not mentioned in the documentation.
2. **Dependency Management**: The script requires `numba` for JIT compilation, which is not listed in `requirements.txt` or the installation instructions.
3. **Execution Context**: The script's `display_team_statistics` function (line 253) calculates stats for all teams encountered, which correctly handles the alternating 19th team but should be explained in the docs.

## Proposed Updated Documentation

### Algorithm Overview
*   **Power Ratings**: Uses fixed Elo ratings for 18 permanent teams and 1 alternating promoted team (selected between Southampton and Hull City per simulation).
*   **Match Simulation**: Vectorized Poisson match engine with home advantage (33.8 Elo) and shared-goal logic for draws.
*   **Performance**: Utilizes Numba JIT acceleration; requires `numba` and `numpy` dependencies.

---

# Documentation Audit Report: Premier League Simulation (25-26 Season)

## Mismatches

1. **Line Number References**: Every line number reference in `sportsanalysis/premier-league/README.md` is inaccurate. Key examples include:
    *   Elo Ratings: Cited at 8-28; actually at 80-100.
    *   Current Table: Cited at 54-76; actually at 128-153.
    *   Fixtures: Cited at 78-106; actually at 155-188.
    *   European Elos: Cited at 109-130; actually at 190-210.
2. **XG Scaling Model**: The `README.md` (Premier League Simulation > Match Engine) describes "Logistic scaling" for Expected Goals. However, the `get_expected_goals` function (line 244) uses exponential scaling: `home_lambda = home_base * math.exp(diff / 800)`.
3. **European Qualification Statistics**: The README claims 8+ European teams are tracked; the script (line 826) specifically reports the probability of "at least 9 European teams."
4. **FA Cup Simulation**: The README describes a simple Elo-based knockout; the script actually hardcodes a final between Chelsea and Man City (lines 228, 861).

## Suggested Clarifications

1. **Elo Update Logic**: The README states RD (Rating Deviation) is "not actively used," but the `update_elo` function (line 560) uses it to calculate the G-value (`g(rd_avg)`) and adjust the K-factor.
2. **Goal Model Details**: The model is described as "Bivariate Poisson," but the implementation uses a more sophisticated mixture model with shared goal components (`lambda_shared`) and variance boosts to account for draw bias (lines 443-480).

## Proposed Updated Documentation

### Match Engine Implementation
*   **XG Model**: Uses exponential scaling `exp(Elo_Diff / 800)` to derive Poisson lambdas for home and away teams.
*   **Shared Goals**: Incorporates a shared goal component proportional to match closeness to represent correlated scoring patterns and draw tendencies.
*   **Dynamic Elo**: Team ratings are updated mid-simulation using Glicko-style adjustments based on match outcomes and Rating Deviation (RD).
