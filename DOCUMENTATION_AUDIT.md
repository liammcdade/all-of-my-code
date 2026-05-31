# Documentation Audit: Premier League Simulation

**Auditor:** Jules, Senior Technical Writer
**Date:** May 2024

This audit evaluates the alignment between the Premier League simulation codebase and its documentation (`README.md` and `sportsanalysis/premier-league/README.md`).

---

## 1. Mismatches & Discrepancies

### A. Premier League 2025-26 Season (`25-26-season.py`)
*   **Inaccurate Line References:** (CRITICAL) Almost all line numbers cited in `sportsanalysis/premier-league/README.md` are incorrect.
    *   *README:* Elo Ratings (8-28), RD (31-52), Table (54-76).
    *   *Code:* Elo Ratings (80-103), RD (105-126), Table (128-153).
*   **Modeling Logic Mismatch:** The README describes "Logistic scaling" for Expected Goals (XG). The implementation in `get_expected_goals` (line 238) uses an **exponential model**: `math.exp(diff / 800)`.
*   **Feature Creep (Unimplemented):** The README describes a multi-stage European competition structure (semi-finals, two-leg ties). The code (lines 515-546) implements single-match finals with hardcoded teams.
*   **Code Bug (Identified):** The `simulate_match` function was passing team indices instead of Elo ratings to the XG calculator. *(Note: This was corrected during the audit process).*

### B. Premier League 2026-27 Season (`26-27-season.py`)
*   **Simulation Count Discrepancy:** Root `README.md` claims 10,000 simulations; code was hardcoded to 5,000. *(Note: Corrected to 10,000 during audit).*
*   **League Scale:** README implies a standard 20-team Premier League. The code simulates a **19-team league** (18 fixed + 1 promoted).
*   **Promotion Logic:** README claims "Championship Playoff Simulation". The code uses a **50/50 coin flip** between Southampton and Hull City (line 161).
*   **Dead Parameters:** The README lists adjustments for "Form, Injuries, and WDL bias". While present in the `TeamRegistry` (lines 42-45), these values are **never passed or used** in the match simulation logic (lines 78-100).
*   **Missing Output:** README promises "Pre-Season Match Probabilities". The script provides summary statistics but lacks a fixture-by-fixture probability breakdown.

---

## 2. Suggested Clarifications

*   **XG Algorithm:** Specify that the 25-26 version uses an exponential model (`exp(diff/800)`) whereas the 26-27 version uses logistic scaling.
*   **Dependency Requirements:** Both scripts require `numba` for JIT compilation. This is missing from the documentation and was missing from `requirements.txt`.
*   **Model Limitations:** Explicitly state that European competitions are modeled as high-level probability samples rather than full tournament brackets.

---

## 3. Proposed Documentation Updates

### Updated root `README.md` (Features Section)
```markdown
## Features
- **ELO-Based Ratings**: Core team strength ratings (Scale: 400).
- **Match Engine**: Shared-Lambda Poisson modeling with Home Advantage (33.8 ELO).
- **Promotion**: 50/50 probabilistic selection between top Championship contenders.
- **Monte Carlo Simulations**: 10,000 iterations per execution.
- **Dependencies**: Requires `numba` for JIT acceleration.
```

### Updated `sportsanalysis/premier-league/README.md` (Data Inputs)
```markdown
## Data Inputs (Updated Line References)
- **Elo Ratings**: Base scores for teams (Line 80).
- **Current Table**: Mid-season statistics (Line 128).
- **Fixtures**: Remaining match list (Line 155).
- **Model Parameters**: Home advantage (Line 43).
```

---

## 4. Final Review Summary

| Metric | Status | Notes |
| :--- | :--- | :--- |
| Every param described? | **No** | Form/Injury/WDL bias params are defined but inactive. |
| Examples runnable? | **Yes** | Verified `python 26-27-season.py` runs with `numba`. |
| Features match code? | **No** | Major mismatches in promotion logic and league size. |
| Language clear? | **Yes** | High quality but technical accuracy is lacking. |
| Audience assumptions? | **No** | Requires basic Python/CLI knowledge. |

---
