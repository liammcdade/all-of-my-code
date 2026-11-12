# Monte Carlo Simulation Engine

<cite>
**Referenced Files in This Document**
- [26-27-season.py](file://premier-league/26-27-season.py)
- [ballerleague.py](file://ballerleague/ballerleague.py)
- [nationleague.py](file://darlington/nationleague.py)
- [champions_league.py](file://uefa/champions_league.py)
- [main.py](file://worldcup30/main.py)
</cite>

## Table of Contents
1. [Introduction](#introduction)
2. [Project Structure](#project-structure)
3. [Core Components](#core-components)
4. [Architecture Overview](#architecture-overview)
5. [Detailed Component Analysis](#detailed-component-analysis)
6. [Dependency Analysis](#dependency-analysis)
7. [Performance Considerations](#performance-considerations)
8. [Troubleshooting Guide](#troubleshooting-guide)
9. [Conclusion](#conclusion)

## Introduction
This document explains the Monte Carlo simulation engine that powers league and competition predictions across multiple football models in the repository. It covers:
- Mathematical foundations: Elo rating systems, Poisson goal distributions, and expected goals (xG).
- Simulation workflow: team strength assessment, match outcome prediction, and aggregate statistics generation.
- Advanced modeling: home advantage, fatigue, manager performance analytics including sack risk.
- Competition formats: domestic leagues, European competitions, and cup tournaments.
- Integration of European competition impacts on domestic league performance.
- Performance optimization techniques, random seed management, and accuracy validation approaches.

The core engine is implemented primarily in a unified Premier League + European + Cup simulation script, with additional specialized implementations for other leagues and competitions.

## Project Structure
The Monte Carlo engine spans several modules:
- A comprehensive Premier League simulation integrating UEFA competitions and domestic cups.
- Specialized league simulators using Elo-based xG and Poisson sampling.
- Standalone European competition simulators.
- International tournament engines with confederation-aware scaling.

```mermaid
graph TB
PL["Premier League Unified Simulator<br/>Elo/xG/Poisson/Monte Carlo"] --> Euro["European Competitions<br/>UCL/UEL/UECL"]
PL --> Cups["Domestic Cups<br/>Carabao/FA Cup"]
Euro --> Stats["Aggregate Statistics<br/>Positions, Spots, Coefficients"]
Cups --> Stats
Stats --> Outputs["Projections & Probabilities"]
subgraph "Other Simulators"
BL["Baller League Elo/xG/Poisson"]
NL["Nation League Elo/xG/Poisson"]
WC["World Cup 30 Core Engine"]
UCL["Champions League Standalone"]
end
BL --> Outputs
NL --> Outputs
WC --> Outputs
UCL --> Outputs
```

**Diagram sources**
- [26-27-season.py:1-120](file://premier-league/26-27-season.py#L1-L120)
- [26-27-season.py:865-1066](file://premier-league/26-27-season.py#L865-L1066)
- [champions_league.py:1-117](file://uefa/champions_league.py#L1-L117)
- [main.py:308-406](file://worldcup30/main.py#L308-L406)

**Section sources**
- [26-27-season.py:1-120](file://premier-league/26-27-season.py#L1-L120)
- [champions_league.py:1-117](file://uefa/champions_league.py#L1-L117)
- [main.py:308-406](file://worldcup30/main.py#L308-L406)

## Core Components
The Monte Carlo engine comprises these core components:
- Random number generator wrapper with Poisson sampling.
- Elo rating system with update rules and expected score calculation.
- Expected goals (xG) model based on Elo differences and home advantage.
- Match scoring via Poisson distribution with safety caps.
- League and knockout phase simulations with fixture handling.
- Fatigue modeling for teams participating in European competitions.
- Manager performance analytics and sack risk calculations.
- European competition integration affecting domestic spots and coefficients.

Key mathematical elements:
- Elo expected score: E = 1 / (1 + 10^((R_opp - R_team)/400))
- Elo update: ΔR = K * (S_actual - E_expected)
- xG model: λ_home = base_home * exp(sensitivity * (R_home - R_away)), λ_away = base_away * exp(-sensitivity * (R_home - R_away))
- Poisson sampling: k ~ Poisson(λ), capped to avoid overflow

**Section sources**
- [26-27-season.py:95-141](file://premier-league/26-27-season.py#L95-L141)
- [26-27-season.py:127-135](file://premier-league/26-27-season.py#L127-L135)

## Architecture Overview
The unified simulation architecture integrates multiple competition layers:

```mermaid
sequenceDiagram
participant RNG as "Random Number Generator"
participant PL as "Premier League Simulator"
participant Euro as "European Competition"
participant Cups as "Domestic Cups"
participant Stats as "Statistics Aggregator"
RNG->>PL : Initialize season simulation
PL->>Euro : Simulate UCL/UEL/UECL
Euro-->>PL : Return rankings, elimination rounds, points
PL->>Cups : Simulate Carabao/FA Cup
Cups-->>PL : Return winners and results
PL->>Stats : Aggregate positions, points, probabilities
Stats-->>PL : Return projections
PL->>RNG : Generate next simulation iteration
```

**Diagram sources**
- [26-27-season.py:2328-2470](file://premier-league/26-27-season.py#L2328-L2470)
- [26-27-season.py:865-1066](file://premier-league/26-27-season.py#L865-L1066)

## Detailed Component Analysis

### Random Number Generation and Poisson Sampling
The engine uses a custom RNG wrapper that provides:
- Uniform random number generation
- Poisson sampling using inverse transform method
- Safety limits to prevent numerical overflow

```mermaid
flowchart TD
Start(["Initialize RNG"]) --> CheckExpected["Check Expected Goals Value"]
CheckExpected --> |Negative| ReturnZero["Return 0 Goals"]
CheckExpected --> |Positive| CalculateL["Calculate L = exp(-λ)"]
CalculateL --> LoopStart["Initialize k=0, p=1.0"]
LoopStart --> IncrementK["k = k + 1"]
IncrementK --> MultiplyP["p = p * random()"]
MultiplyP --> CheckCondition{"p <= L?"}
CheckCondition --> |Yes| ReturnK["Return k-1"]
CheckCondition --> |No| CheckLimit{"k > 100?"}
CheckLimit --> |Yes| ReturnCap["Return min(k-1, cap)"]
CheckLimit --> |No| LoopStart
```

**Diagram sources**
- [26-27-season.py:98-122](file://premier-league/26-27-season.py#L98-L122)
- [main.py:327-341](file://worldcup30/main.py#L327-L341)

**Section sources**
- [26-27-season.py:98-122](file://premier-league/26-27-season.py#L98-L122)
- [main.py:327-341](file://worldcup30/main.py#L327-L341)

### Elo Rating System and Expected Goals
The Elo system calculates expected scores and updates ratings based on match outcomes:

```mermaid
classDiagram
class EloSystem {
+float HOME_ADVANTAGE_ELO
+float ELO_SCALE
+update_elo(elo_w, elo_l, k) tuple
+expected_goals(elo_h, elo_a) tuple
+sample_score(rng, lam_h, lam_a) tuple
}
class TeamRecord {
+string name
+string confederation
+int elo
+int points
+int goals_for
+int goals_against
+goal_difference() int
}
class MatchSimulator {
+simulate_match(home, away, neutral) tuple
+apply_result(records, home, away, hg, ag, neutral) void
+sort_records(records) list
}
EloSystem --> TeamRecord : "calculates xG"
MatchSimulator --> TeamRecord : "updates ratings"
```

**Diagram sources**
- [26-27-season.py:127-141](file://premier-league/26-27-season.py#L127-L141)
- [main.py:308-406](file://worldcup30/main.py#L308-L406)

**Section sources**
- [26-27-season.py:127-141](file://premier-league/26-27-season.py#L127-L141)
- [main.py:308-406](file://worldcup30/main.py#L308-L406)

### Match Outcome Prediction Workflow
The match prediction process follows this sequence:

```mermaid
flowchart TD
Start(["Match Prediction"]) --> GetElos["Get Team Elo Ratings"]
GetElos --> ApplyHomeAdv["Apply Home Advantage"]
ApplyHomeAdv --> CalculateDiff["Calculate Elo Difference"]
CalculateDiff --> ComputeXG["Compute Expected Goals (xG)"]
ComputeXG --> SampleGoals["Sample Goals from Poisson Distribution"]
SampleGoals --> DetermineResult["Determine Match Result"]
DetermineResult --> UpdateElos["Update Elo Ratings"]
UpdateElos --> End(["Return Result"])
```

**Diagram sources**
- [26-27-season.py:132-141](file://premier-league/26-27-season.py#L132-L141)
- [main.py:343-360](file://worldcup30/main.py#L343-L360)

**Section sources**
- [26-27-season.py:132-141](file://premier-league/26-27-season.py#L132-L141)
- [main.py:343-360](file://worldcup30/main.py#L343-L360)

### European Competition Integration
European competitions are integrated through a sophisticated system that tracks team performance and its impact on domestic leagues:

```mermaid
classDiagram
class EuropeanCompetition {
+string name
+list teams
+dict base_elos
+dict elos
+simulate(rng, track, stop_when_no_pl_teams) EuroSimResult
}
class EuroSimResult {
+string winner
+dict elim_rounds
+list ranking
+dict league_points
+dict league_wins
+dict league_draws
+dict ko_match_pts
+dict team_results
}
class KnockoutPhase {
+simulate_two_legged_tie(team1, team2, elos, comp, round_idx, rng) tuple
+simulate_knockout_phase(qualified, elos, comp, rng, track, english_teams) tuple
}
EuropeanCompetition --> EuroSimResult : "returns"
EuropeanCompetition --> KnockoutPhase : "uses"
```

**Diagram sources**
- [26-27-season.py:868-1066](file://premier-league/26-27-season.py#L868-L1066)
- [26-27-season.py:1072-1200](file://premier-league/26-27-season.py#L1072-L1200)

**Section sources**
- [26-27-season.py:868-1066](file://premier-league/26-27-season.py#L868-L1066)
- [26-27-season.py:1072-1200](file://premier-league/26-27-season.py#L1072-L1200)

### Manager Performance Analytics and Sack Risk
The system includes advanced manager performance analytics with sack risk calculations:

```mermaid
flowchart TD
Start(["Manager Risk Calculation"]) --> GetRanking["Get Team Ranking"]
GetRanking --> GetManagerData["Retrieve Manager Data"]
GetManagerData --> CalculateUnderperf["Calculate Underperformance"]
CalculateUnderperf --> ApplyPressure["Apply Pressure Multiplier"]
ApplyPressure --> CheckRelegationZone{"In Relegation Zone?"}
CheckRelegationZone --> |Yes| AddRelegationRisk["Add Relegation Risk"]
CheckRelegationZone --> |No| CheckHonours{"Recent Honours?"}
CheckRelegationZone --> |No| CheckHonours
CheckHonours --> |Yes| ApplyProtection["Apply Protection Factor"]
CheckHonours --> |No| CheckEuroPerf["Check European Performance"]
ApplyProtection --> CheckEuroPerf
CheckEuroPerf --> AddActualForm["Add Actual Form Adjustment"]
AddActualForm --> ClampRisk["Clamp Risk to Valid Range"]
ClampRisk --> End(["Return Risk Score"])
```

**Diagram sources**
- [26-27-season.py:788-838](file://premier-league/26-27-season.py#L788-L838)

**Section sources**
- [26-27-season.py:788-838](file://premier-league/26-27-season.py#L788-L838)

### Alternative Implementation Patterns
Different simulators implement similar concepts with varying complexity:

#### Baller League Implementation
A simpler implementation focusing on indoor football characteristics:

```mermaid
flowchart TD
Start(["Indoor Football Simulation"]) --> GetTeamRatings["Get Attack/Defense Elo"]
GetTeamRatings --> ComputeEG["Compute Expected Goals"]
ComputeEG --> ApplyVolatility["Apply Indoor Volatility Multiplier"]
ApplyVolatility --> CapGoals["Cap Goals to Prevent Overflow"]
CapGoals --> MixedSampling{"Mixed Sampling"}
MixedSampling --> |70%| Poisson["Standard Poisson"]
MixedSampling --> |30%| HighVol["High Volatility Override"]
Poisson --> UpdateStats["Update Team Statistics"]
HighVol --> UpdateStats
UpdateStats --> End(["Return Updated Teams"])
```

**Diagram sources**
- [ballerleague.py:37-47](file://ballerleague/ballerleague.py#L37-L47)
- [ballerleague.py:232-276](file://ballerleague/ballerleague.py#L232-L276)

**Section sources**
- [ballerleague.py:37-47](file://ballerleague/ballerleague.py#L37-L47)
- [ballerleague.py:232-276](file://ballerleague/ballerleague.py#L232-L276)

#### Nation League Implementation
A simplified approach with form adjustments:

```mermaid
classDiagram
class OptimizedELORatingSystem {
+float k_factor
+float home_advantage
+defaultdict ratings
+dict match_weights
+expected_score(ra, rb) float
+update_ratings(home, away, hs, aws, match_type) void
+predict_match(home, away, neutral) float
+predict_score(home, away, neutral) tuple
}
class LeagueSimulator {
+OptimizedELORatingSystem elo_system
+dict team_stats
+load_current_standings() void
+initialize_elos_from_results(fixtures) void
+simulate_fixtures(fixtures) void
+run_monte_carlo_simulations(fixtures, baseline, num_simulations) tuple
}
OptimizedELORatingSystem --> LeagueSimulator : "used by"
```

**Diagram sources**
- [nationleague.py:259-306](file://darlington/nationleague.py#L259-L306)
- [nationleague.py:307-393](file://darlington/nationleague.py#L307-L393)

**Section sources**
- [nationleague.py:259-306](file://darlington/nationleague.py#L259-L306)
- [nationleague.py:307-393](file://darlington/nationleague.py#L307-L393)

## Dependency Analysis
The simulation engine has clear dependency relationships:

```mermaid
graph TD
Core["Core Math Functions<br/>Elo/xG/Poisson"] --> PL["Premier League Engine"]
Core --> Other["Other League Engines"]
PL --> EuroInt["European Integration"]
PL --> Fatigue["Fatigue Modeling"]
PL --> Manager["Manager Analytics"]
EuroInt --> Stats["Statistics Collection"]
Fatigue --> Stats
Manager --> Stats
Stats --> Output["Final Projections"]
```

**Diagram sources**
- [26-27-season.py:1-120](file://premier-league/26-27-season.py#L1-L120)
- [26-27-season.py:865-1066](file://premier-league/26-27-season.py#L865-L1066)

**Section sources**
- [26-27-season.py:1-120](file://premier-league/26-27-season.py#L1-L120)
- [26-27-season.py:865-1066](file://premier-league/26-27-season.py#L865-L1066)

## Performance Considerations
The engine implements several performance optimizations:

### Random Seed Management
- Custom RNG wrapper for consistent reproducibility
- Seeded random number generation for all simulations
- Separate random streams for different simulation components

### Computational Efficiency
- Vectorized operations where possible
- Early termination when no English teams remain in European competitions
- Capped goal values to prevent numerical overflow
- Pre-computed exponential values for Elo calculations

### Memory Optimization
- Use of `__slots__` for memory-efficient objects
- Dictionary-based data structures for fast lookups
- Minimal object creation during simulation loops

### Simulation Accuracy Validation
- Multiple simulation runs (2,500+ for Premier League)
- Statistical convergence monitoring
- Cross-validation between different competition formats
- Historical result calibration using actual match data

**Section sources**
- [26-27-season.py:98-122](file://premier-league/26-27-season.py#L98-L122)
- [26-27-season.py:2328-2470](file://premier-league/26-27-season.py#L2328-L2470)

## Troubleshooting Guide

### Common Issues and Solutions

#### Numerical Overflow in Poisson Sampling
- **Issue**: Extremely high expected goals causing overflow
- **Solution**: Implement goal caps (MAX_GOALS = 10)
- **Prevention**: Validate input parameters before simulation

#### Convergence Problems
- **Issue**: Simulation results not stabilizing
- **Solution**: Increase number of simulations or adjust random seeds
- **Monitoring**: Track convergence metrics across simulation batches

#### European Competition Integration Errors
- **Issue**: Incorrect fatigue application or spot allocation
- **Solution**: Verify fixture mappings and team qualification criteria
- **Validation**: Cross-check against official competition rules

#### Manager Sack Risk Calculation Errors
- **Issue**: Unrealistic risk scores or division by zero
- **Solution**: Add input validation and edge case handling
- **Calibration**: Adjust pressure multipliers based on historical data

**Section sources**
- [26-27-season.py:138-141](file://premier-league/26-27-season.py#L138-L141)
- [26-27-season.py:788-838](file://premier-league/26-27-season.py#L788-L838)

## Conclusion
The Monte Carlo simulation engine provides a comprehensive framework for football prediction across multiple competition formats. Its mathematical foundation combines Elo rating systems with Poisson-distributed goal modeling, while advanced features like fatigue tracking, manager analytics, and European competition integration create realistic simulation scenarios. The modular architecture allows for easy extension to new competition formats while maintaining computational efficiency through careful optimization techniques.

The engine's strength lies in its ability to handle complex interactions between domestic and international competitions, providing accurate probability distributions for various outcomes including league positions, European qualification, and managerial stability. Through rigorous validation and continuous calibration against actual results, the system maintains reliability across different seasons and competition structures.