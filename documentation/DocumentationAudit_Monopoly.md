# Documentation Audit Report: Monopoly 2024 Simulator & Monte Carlo Advisor

**Auditor:** Senior Technical Writer & Software Documentation Auditor
**Target Module:** `monoply/main.py`
**Date:** August 2026

---

## Executive Summary

An audit of the Monopoly 2024 (UK Board) simulator (`monoply/main.py`) was performed to evaluate code-documentation alignment, completeness, syntax accuracy, and clarity. The codebase contains a complete game engine, a Monte Carlo action evaluator, an interactive CLI, a move advisor prompt, and a Tkinter-based GUI dashboard. However, external documentation (`monoply/README.md`) is missing entirely, and the module-level docstring in `monoply/main.py` (lines 1–13) contains incorrect class references, missing function signatures, and unmentioned user interfaces.

---

## 1. Code-Documentation Mismatches

### 1.1 Inaccurate Class Reference in Docstrings
* **Location:** `monoply/main.py` line 6
* **Code Reference:** `class MonopolyGame` (line 120)
* **Mismatch:** The module docstring instructs users to call `Game.simulate_action_choice(player_index)`. There is no class named `Game`; the actual engine class is `MonopolyGame`. Attempting `Game.simulate_action_choice(...)` results in a `NameError`.

### 1.2 Undocumented Real-World Price Scaling Side Effect
* **Location:** `monoply/main.py` lines 68–80
* **Code Reference:** Real-world London property price adjustment loop
* **Mismatch:** At startup, the script iterates over `BOARD` and modifies property `cost`, `rent`, and `house_cost` in-place based on the `Real_prices` dictionary (scaling prices relative to Mayfair at £3,150,000, capped at £400). This alters standard UK Monopoly board costs (e.g., Old Kent Road base cost becomes £103 instead of £60). This side effect is completely undocumented.

### 1.3 Discrepancy Between Legal Action Generation and Execution Logic
* **Location:** `monoply/main.py` lines 282, 351–363
* **Code Reference:** `MonopolyGame.legal_actions` vs. `MonopolyGame.execute_action`
* **Mismatch:** Line 282 contains a comment stating `# mortgage / unmortgage removed as per request`, and `legal_actions()` omits mortgage/unmortgage actions. However, `execute_action()` (lines 351–363) and `action_repr()` (lines 420–422) still contain full logic for `"mortgage"` and `"unmortgage"` actions.

### 1.4 Unmentioned Main Execution Mode & User Interfaces
* **Location:** `monoply/main.py` lines 507–539 (`advisor`), lines 542–692 (`gui_advisor`), line 695 (`if __name__ == "__main__":`)
* **Mismatch:** The module docstring claims that running the script runs a CLI demo game (`demo()`). However, line 695 sets the main entry point to `gui_advisor()`, which launches a full-screen Tkinter GUI dashboard. Neither `advisor()`, `interactive_game()`, `print_board_layout()`, nor `gui_advisor()` are mentioned in the module documentation.

### 1.5 Missing Parameter & Return Value Documentation
* **Location:** `monoply/main.py` lines 120–433 (`MonopolyGame` methods)
* **Mismatch:** Key public methods lack docstrings specifying parameter types, return types, or internal side effects:
  * `MonopolyGame.__init__(player_names: List[str])`: Mutates internal player states and deck queues.
  * `MonopolyGame.simulate_action_choice(player_index: int, sims_per_action: int = 100, future_turns: int = 5)`: Returns a tuple `(best_action: Dict, stats: Dict[str, float])` mapping action string representations to average player net worth.
  * `MonopolyGame.simulate_random_game(max_turns: int = 200)`: Returns `Optional[int]` (the player index of the winner by net worth).
  * `MonopolyGame.legal_actions(player: Player)`: Returns `List[Dict]` representing available move structures.

---

## 2. Suggested Clarifications & Audience Considerations

### 2.1 Monte Carlo Metric Explanation
* **Jargon / Ambiguity:** The docstrings and comments refer to action evaluation stats as "win rates" in `demo()` print statements (e.g., line 487: `Action stats (win rates)`), but the evaluator actually scores actions using **Average Net Worth** over `future_turns` (line 393: `score = sim.players[player_index].net_worth(...)`).
* **Clarification:** Clarify that `simulate_action_choice` evaluates actions based on expected total net worth (Cash + Property Value + House Value) after `future_turns` (default 5 turns) across `sims_per_action` Monte Carlo playouts, rather than binary win/loss probabilities.

### 2.2 Trade & Auction Heuristics
* **Assumed Knowledge:** Users running simulations may expect standard human decision-making or full Monopoly rules for trades and auctions.
* **Clarification:** Explicitly document the underlying heuristics:
  * **Auctions:** Bidders bid up to property base cost, capped at current cash (lines 336–342).
  * **Trades:** Proposed trades offer 120% of property cost; opponent AI auto-accepts if offer >= 110% of cost or if opponent cash < £100 (lines 364–377).
  * **Liquidation:** Solvent players forced into debt mortgage highest-cost unmortgaged properties first, then sell houses from highest house-cost color groups first (lines 250–267).

### 2.3 Required Dependencies
* **Missing Details:** Running `gui_advisor()` requires `tkinter`, which may not be installed by default in minimal Linux environments (requiring `python3-tk`).

---

## 3. Proposed Updated Documentation Text

Below is the proposed external `monoply/README.md` to be placed in the `monoply/` directory and integrated into project documentation.

```markdown
# Monopoly 2024 (UK Board) Engine & Monte Carlo Advisor

A complete Python simulation engine and Monte Carlo action decision advisor for UK Monopoly. Features custom property pricing models, AI trade and auction heuristics, terminal CLI modes, and an interactive Tkinter GUI dashboard.

---

## Features

- **UK Board Engine**: Supports full 40-square UK board mechanics, Chance & Community Chest cards, Jail, Passing GO (£200), and Free Parking.
- **Dynamic Price Scaling**: Option-adjusted property pricing scaled relative to real-world London property valuations.
- **Monte Carlo Advisor**: Evaluates legal actions (`buy`, `build`, `propose_trade`, `auction`, `end_turn`) by cloning game state and projecting average player net worth across forward simulation playouts.
- **Multiple Interfaces**:
  - **Tkinter GUI Dashboard** (`gui_advisor`): Graphical interface for state setup and move calculation.
  - **CLI Move Advisor** (`advisor`): Interactive terminal prompt for real-time game advice.
  - **Interactive CLI Game** (`interactive_game`): Human vs. AI terminal gameplay.
  - **Automated Demo** (`demo`): Fast headless AI-vs-AI simulation runs.

---

## Installation & Setup

1. Ensure Python 3.8+ is installed.
2. If using the Tkinter GUI on Linux, install `python3-tk`:
   ```bash
   sudo apt-get install python3-tk
   ```
3. Run the script directly to launch the GUI dashboard:
   ```bash
   python monoply/main.py
   ```

---

## Core API Reference

### `MonopolyGame`

The primary game state manager and simulation engine.

```python
from monoply.main import MonopolyGame

# Initialize a 3-player game
game = MonopolyGame(player_names=["Alice", "Bob", "Charlie"])
```

#### Key Methods

##### `simulate_action_choice(player_index: int, sims_per_action: int = 100, future_turns: int = 5) -> Tuple[Dict, Dict[str, float]]`
Enumerates legal actions for `player_index` at current turn state, simulates `sims_per_action` Monte Carlo playouts per action across `future_turns`, and returns the optimal action along with average net worth statistics for each legal move.

- **Parameters:**
  - `player_index` (*int*): Index of the player receiving advice (0 to N-1).
  - `sims_per_action` (*int*, default=100): Number of random forward simulation trials per legal action.
  - `future_turns` (*int*, default=5): Number of turns to simulate into the future per trial.
- **Returns:**
  - `Tuple[Dict, Dict[str, float]]`: `(best_action_dict, stats_dict)` where `stats_dict` maps action string representations to projected average net worth in pounds (£).

##### `play_single_turn() -> None`
Executes a single turn for the active player (`game.turn % len(game.players)`), including dice rolling, movement, landing resolution, card drawing, rent collection, and auto-buy heuristics. Advances `game.turn`.

##### `legal_actions(player: Player) -> List[Dict]`
Generates a list of all legal actions available to `player` based on position, cash, monopolies owned, and unowned landed properties.

##### `clone() -> MonopolyGame`
Creates a deep copy of the current game state for Monte Carlo simulation playouts.

---

## Data Models

### `Player`
Tracks player financial and spatial state.
- **Attributes:** `name` (*str*), `index` (*int*), `cash` (*int*, default=1500), `position` (*int*, 0-39), `properties` (*List[int]*), `in_jail` (*bool*), `jail_turns` (*int*), `get_out_of_jail_free` (*int*), `bankrupt` (*bool*).
- **Methods:** `net_worth(prop_states: Dict[int, PropertyState]) -> int` — Returns total liquid cash plus base property cost and house investments.

### `PropertyState`
Tracks ownership and development state of board squares.
- **Attributes:** `index` (*int*), `info` (*Dict*), `owner` (*Optional[int]*), `houses` (*int*, 0-4=houses, 5=hotel), `mortgaged` (*bool*).

---

## CLI & GUI Usage Examples

### Running the Interactive CLI Advisor
```python
from monoply.main import advisor

# Prompts for board positions, cash, property ownership, and outputs optimal move
advisor()
```

### Running an AI Demo Game
```python
from monoply.main import demo

# Runs an automated 200-round game between AI Monte Carlo and auto-players
demo()
```
```