# Python Engineering Standards

These standards apply to **all generated, modified, and reviewed Python code**.

## Core Principles

Every solution must prioritize, in this order:

1. Correctness
2. Readability
3. Maintainability
4. Modularity
5. Testability
6. Predictable behavior
7. Performance (only after correctness)

Never sacrifice readability for cleverness.

---

## 1. Maximum Nesting

**Rule**

- Never exceed **3 levels of indentation**.
- Use helper functions, guard clauses, or early returns instead.

---

## 2. Prefer Guard Clauses

Replace nested condition pyramids with early returns.

### Good

```python
if not team:
    return None

if not team.active:
    return None

return calculate(team)
3. Single Responsibility Principle

Every function should perform one clearly defined task.

Functions should not simultaneously:

Load data
Simulate
Calculate
Save files
Print output

Break work into dedicated functions.

4. Function Size

Preferred:

10–40 lines

Maximum:

60 lines

If longer:

Split into helper functions.
Remove duplicated logic.
Simplify branching.
5. Module Size

Preferred:

Under 500 lines

Maximum:

1000 lines however if the file has multiple segments each segment can be max 500 and 500 x the amount of segment

Split larger files into modules or packages.

6. Standard File Layout
Imports
Constants
Enums
Dataclasses
Type Aliases
Configuration
Utilities
Validation
Core Logic
Simulation Engine
Statistics
Formatting / Display
Main Entry Point
7. Imports

Order imports as:

Standard library
Third-party packages
Local project imports

Alphabetize each section.

Never use wildcard imports.

8. Naming
Variables

Use snake_case.

Functions

Use verbs.

Examples:

calculate_rating
simulate_match
update_table
Classes

Use PascalCase.

Examples:

TeamStats
SimulationContext
Constants

Use UPPER_SNAKE_CASE.

9. Type Hints

Every public function must use type hints.

Type all collections.

Avoid untyped code.

10. Docstrings

Public modules, classes, and functions require docstrings.

Use Google or NumPy style consistently.

11. Dataclasses

Prefer dataclasses for structured data.

Use:

@dataclass(slots=True)

where appropriate.

Avoid deeply nested dictionaries.

12. Constants

Replace repeated or unexplained numbers with named constants.

Never leave magic numbers in code.

13. Configuration

All configurable values belong in a single configuration module or dataclass.

Never scatter configuration throughout the project.

14. DRY

Never duplicate logic.

Extract repeated code into reusable helpers.

15. Explicit Side Effects

Functions should make mutations obvious.

Prefer returning values over modifying external state.

16. Pure Functions

Calculation functions should:

Return values
Avoid printing
Avoid file I/O
Avoid modifying globals
17. Separate Logic from Presentation

Business logic must never be mixed with UI or console output.

18. Global State

Allowed globals:

Constants
Immutable lookup tables
Configuration

Avoid mutable global variables.

19. Parameters

Preferred:

3–5 parameters

If more are required, use a dataclass or context object.

20. Validation

Validate all public inputs.

Raise meaningful exceptions for invalid data.

21. Error Handling

Catch only expected exceptions.

Never use:

except:

Always catch specific exception types.

22. Logging

Use the logging module for diagnostics.

Use print() only for user-facing output.

23. Comments

Comments explain why, never what.

Avoid redundant comments.

24. Performance

Optimize only after:

Correctness
Readability
Profiling

Never prematurely optimize.

25. Numba

Only use @numba.jit or @numba.njit for isolated numeric hot paths.

Never decorate orchestration, UI, or I/O code.

26. Composition

Prefer many small functions over one large function.

27. Data Structures

Prefer classes or dataclasses over deeply nested dictionaries.

28. Single Source of Truth

Avoid storing the same information in multiple places.

29. Testing

Write deterministic, testable functions.

Prefer dependency injection over global state.

30. PEP 8

Follow PEP 8 unless project requirements explicitly state otherwise.

Use:

pathlib
f-strings
context managers
enumerate()
zip()

Avoid unnecessary complexity.

31. Modern Python

Prefer modern language features:

pathlib.Path
dataclass(slots=True)
Enum
StrEnum
match
Union operator (|)
Self

when appropriate.

32. Security

Never:

use eval()
use exec()
hardcode secrets
trust external input

Validate all user input.

33. Resource Management

Always use context managers.

Example:

with open(path) as file:
    ...
34. Deterministic Simulations

Support reproducibility through explicit random seeds.

35. API Design

Functions should have predictable inputs, outputs, and behavior.

Avoid surprising side effects.

36. Final Checklist

Before completing any code:

Correctness verified
PEP 8 compliant
Max nesting ≤ 3
Small functions
No duplicated logic
No hidden mutations
No magic numbers
Typed functions
Dataclasses where appropriate
Pure calculations
Modular design
Descriptive names
Proper error handling
Logging instead of debug prints
Configuration centralized
Easy to extend
Easy to test
Modern Python practices
No dead or unused code
Guiding Principle

Write code as if it will be maintained by another experienced engineer five years from now. Favor clarity, correctness, modularity, and long-term maintainability over clever or overly concise solutions.


This format is ideal for a `README.md` or `PYTHON_STANDARDS.md` because it uses proper Markdown headings, lists, co