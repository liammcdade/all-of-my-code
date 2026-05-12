Python Code Quality Ruleset

Use these rules for all generated or edited code. The goal is:

maximum readability
low nesting
modular structure
predictable behavior
fast debugging
easy future expansion
1. Maximum Nesting Rule
Hard limit
Never nest more than 3 levels deep.

Bad:

if a:
    for x in items:
        if x.valid:
            while x.running:
                ...

Good:

if not a:
    return

for item in items:
    process_item(item)
2. Prefer Early Returns

Avoid giant conditional pyramids.

Bad:

def process(team):
    if team:
        if team.active:
            if team.points > 10:
                return calculate(team)

Good:

def process(team):
    if not team:
        return None

    if not team.active:
        return None

    if team.points <= 10:
        return None

    return calculate(team)
3. One Function = One Responsibility

Each function should do ONE thing only.

Bad:

def simulate():
    load_data()
    simulate_matches()
    update_table()
    print_results()
    save_csv()

Good:

def run_simulation():
    data = load_data()
    results = simulate_matches(data)
    table = build_table(results)

    export_results(table)
4. Function Size Limits
Preferred
10–40 lines per function
Maximum
60 lines absolute maximum

If longer:

split into helper functions
5. File Structure Standard

Every Python file should follow this order:

# Imports
# Constants
# Data Models
# Utility Functions
# Core Logic
# Simulation Engine
# Statistics
# Output
# Main Entry Point
6. No Magic Numbers

Every repeated number becomes a named constant.

Bad:

home_advantage = 33.8

Good:

HOME_ADVANTAGE_ELO = 33.8

Bad:

if diff > 180:

Good:

DRAW_BALANCE_THRESHOLD = 180

if diff > DRAW_BALANCE_THRESHOLD:
7. No Duplicate Logic

If code appears twice:

extract a function

Bad:

table[home]["GF"] += hg
table[home]["GA"] += ag

table[away]["GF"] += ag
table[away]["GA"] += hg

Repeated elsewhere again.

Good:

apply_goals(table, home, away, hg, ag)
8. Naming Rules
Variables
snake_case only

Good:

home_expected_goals

Bad:

homeExpectedGoals
hgx
Functions

Must start with verbs.

Good:

simulate_match()
update_elo()
calculate_table()

Bad:

match_simulation()
elo()
table()
Constants

ALL_CAPS only.

HOME_ADVANTAGE
MAX_GOALS
DEFAULT_ELO
9. Avoid Giant Dictionaries in Main Logic

Move large datasets into:

separate files
JSON
CSV
config modules

Bad:

elo = {
    ...
    200 lines
}

Good:

elo = load_elo_ratings()
10. No Hidden State Mutation

Functions should clearly show what changes.

Bad:

simulate_match()

Secretly edits:

elo
table
injuries
stats

Good:

hg, ag = simulate_match(home, away)

update_table(table, home, away, hg, ag)
update_elo(ratings, home, away, hg, ag)
11. Keep Simulation Pure

Simulation functions should:

return values
not print
not save files
not mutate globals

Bad:

def simulate():
    print("Running")

Good:

def simulate():
    return results
12. Main Loop Must Stay Small

Bad:

for sim in range(sims):
    ...
    300 lines

Good:

for _ in range(NUM_SIMULATIONS):
    result = run_single_simulation()
    update_statistics(result)
13. Separate Calculation From Display

Never mix math and printing.

Bad:

print(np.mean(points))

Good:

average_points = calculate_average(points)
display_average_points(average_points)
14. Avoid Deeply Coupled Functions

Functions should require minimal outside knowledge.

Bad:

simulate_match(home, away)

Depends on:

global elo
global injuries
global form
global constants

Good:

simulate_match(
    home,
    away,
    elo,
    injuries,
    form,
    settings
)
15. Use Dataclasses for Structured Data

Bad:

team["GF"]
team["GA"]
team["Pts"]

Good:

@dataclass
class TeamStats:
    goals_for: int
    goals_against: int
    points: int
16. No 1000-Line Files
Preferred
under 500 lines
Maximum
800 lines

17. Every Section Needs a Clear Purpose

Bad:

# random stuff

Good:

# Monte Carlo Simulation Engine
18. Limit Arguments
Preferred
3–5 arguments

If more:

use config objects/dataclasses

Bad:

simulate_match(
    home,
    away,
    elo,
    injuries,
    form,
    rd,
    settings,
    weather,
    referee
)

Good:

simulate_match(home, away, simulation_context)
19. Use Typed Functions

Always use type hints.

Good:

def calculate_probability(diff: float) -> float:
20. No Massive Print Blocks

Move output formatting into dedicated functions.

Bad:

print(f"...")
print(f"...")
print(f"...")

Good:

display_table(results)
display_probabilities(probabilities)
21. Config Must Be Centralized

All tunable values belong in one place.

Good:

SIMULATION_SETTINGS = {
    "home_advantage": 33.8,
    "draw_factor": 0.25,
    "k_factor": 25,
}
22. Comments Explain WHY, Not WHAT

Bad:

# add goals
team["GF"] += goals

Good:

# Slight inflation improves realism for high-variance matches
23. Prefer Composition Over Giant Functions

Bad:

run_everything()

Good:

results = simulate_season()
stats = calculate_statistics(results)
display_results(stats)
24. Keep Global Variables Minimal

Allowed globals:

constants
configuration
immutable lookup data

Avoid mutable global state.

25. Validate Inputs

Bad:

def poisson_random(lam):

Good:

def poisson_random(lam: float) -> int:
    if lam < 0:
        raise ValueError("Lambda cannot be negative")
26. Performance Rules

Optimize only after:

correctness
readability
modularity

Do not prematurely optimize.

27. Numba Rules

Only use @numba.jit on:

pure numeric functions
isolated hot paths

Never on:

giant orchestration functions
print logic
dictionary-heavy code
28. Avoid Long Chains

Bad:

table[team]["stats"]["attack"]["xg"]

Good:

team_stats.attack_xg
29. One Source of Truth

Avoid duplicated data.

Bad:

elo_attack
elo_defense
team_strength
power_rating

Without synchronization.

30. Final Clean Code Checklist

Before finishing:

max nesting ≤ 3
no duplicated blocks
functions small
globals minimized
constants extracted
typed functions
modular structure
no giant loops
no giant functions
calculations separated from output
no hidden mutations
descriptive names only
simulation logic isolated
reusable helpers extracted
config centralized
comments explain reasoning only