# Documentation Audit Report: Premier League Simulation Projects

## 1. 2025-26 Season Simulation
**Files:** `sportsanalysis/premier-league/25-26-season.py`, `sportsanalysis/premier-league/README.md`

### Mismatches
*   **Critical Bug in Logic:** In `simulate_match` (line 444), `get_expected_goals` is called using team indices (`h_idx`, `a_idx`) instead of their Elo ratings. This causes the simulation to use values like 0-19 for team strength, effectively nullifying the Elo system.
*   **Mathematical Model:** The README (Simulation Components > Match Engine) describes "Logistic scaling" for XG. However, `get_expected_goals` (lines 246-247) implements an exponential model: `home_base * math.exp(diff / 800)`.
*   **Data References:** Line number references in the README are severely outdated.
    *   Elo Ratings: README says lines 8-28; Actual: lines 80-100.
    *   Current Table: README says lines 54-76; Actual: lines 128-148.
    *   Fixtures: README says lines 78-106; Actual: lines 155-184.
*   **Home Advantage:** README specifies 33.8 Elo points (line 469). The code defines a constant `HOME_ADVANTAGE_ELO = 60` (line 43) but then randomizes it between 50 and 70 in the simulation loop (line 488).
*   **European Competition Structure:** The README describes a semi-final tournament structure. The code simplifies this by pre-calculating win probabilities using a single-match final between two hardcoded teams (e.g., Aston Villa vs Freiburg for EL) and then sampling from those results.
*   **Qualification Statistics:** README mentions "8+ European teams", but the console output (line 924) reports the probability of "at least 9 teams".

### Suggested Clarifications
*   **Simulation Runtime:** README claims ~12 seconds. On modern hardware with Numba, it may be faster, but the 25,000 iteration count is heavy.
*   **Elo system:** The README states it uses a "400-scale Elo with home +100 equivalent", but the match engine uses a custom XG formula and the home advantage is actually 50-70.

---

## 2. 2026-27 Season Simulation
**Files:** `sportsanalysis/premier-league/26-27-season.py`, `README.md` (root)

### Mismatches
*   **League Structure:** The simulation (line 33) uses 18 fixed teams and adds 1 promoted team, resulting in a **19-team league**. Standard Premier League (and the README's implication) is 20 teams.
*   **Simulation Count:** README claims 10,000 simulations. The script defines `NUM_SIMS = 5000` (line 197).
*   **Championship Promotion:** README claims a "Championship playoff simulation". The code performs a 50/50 coin flip between Southampton and Hull City (line 194).
*   **Unimplemented Features:**
    *   **Form/Injuries:** The README (Algorithm Overview) claims Elo is adjusted for form and injuries. While `TeamRegistry.add_team` accepts these parameters, they are completely ignored by the simulation logic.
    *   **Match Probabilities:** README claims "Pre-Season Match Probabilities" and "fixture difficulty" are output. These features are absent from the code.
    *   **WDL Bias:** README claims Elo is adjusted for WDL tendencies, which is not implemented.
*   **Side Effects:** The script silently deletes its own `__pycache__` directory upon completion (lines 239-241), which is not documented.

### Suggested Clarifications
*   **Dependencies:** The script requires `numba` and `numpy`, but the root README only mentions `numpy` in the algorithm overview and doesn't emphasize that `numba` is a hard requirement for the JIT-accelerated simulation.

---

## Proposed Updates

### Update for `sportsanalysis/premier-league/README.md` (25-26)
```markdown
- **Model Parameters**: Home advantage (Randomized 50-70 Elo points) (line 488).
- **Match Engine**: Uses exponential scaling for XG: `home_xg = base * exp(diff / 800)`.
- **European Assignments**: Tracks probability of 9+ teams qualifying for Europe.
```

### Update for `README.md` (2026-27)
```markdown
## Algorithm Overview
- **League Structure**: 19-team simulation (18 fixed + 1 promoted).
- **Promotion**: Simple 50/50 selection between top Championship contenders.
- **Monte Carlo**: 5,000 iterations for performance.
```

### Required Code Fix (25-26 Season)
In `sportsanalysis/premier-league/25-26-season.py`, line 444 should be changed from:
`home_xg, away_xg = get_expected_goals(h_idx, a_idx, ...)`
to:
`home_xg, away_xg = get_expected_goals(elo_att[h_idx], elo_def[a_idx], ...)`
