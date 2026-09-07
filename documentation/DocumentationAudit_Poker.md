# Documentation Audit Report: Poker AI Simulator (`poker/texas_holdem.py`)

**Auditor:** Senior Technical Writer & Software Documentation Auditor
**Scope:** `poker/texas_holdem.py` & `poker/test_api.py`
**Status:** Comprehensive Audit Complete

---

## 1. Code-Documentation Mismatches

### 1.1 Class & Extension Architecture (`MyTexasHoldEm`)
- **Location:** Line 39 (`class MyTexasHoldEm(TexasHoldEm):`)
- **Mismatch:** The custom subclass `MyTexasHoldEm` inherits from `texasholdem.TexasHoldEm` and overrides/adds `get_total_pot(self)` (Line 40). Existing documentation or docstrings fail to describe why `TexasHoldEm` is subclassed or how main and side pots are calculated.
- **Parameters & Return Value:** `get_total_pot(self)` takes no parameters (other than `self`) and returns an `int` representing the sum total of chips across all active pots (`sum(pot.get_total_amount() for pot in self.pots)`).
- **Side Effects:** None.

### 1.2 AI Probability Engine (`PokerAI.calculate_win_probability`)
- **Location:** Line 51 (`def calculate_win_probability(self, game, sims=DEFAULT_SIMS):`)
- **Mismatch:**
  - Parameter `sims` defaults to `DEFAULT_SIMS` (600), which is undocumented.
  - Undocumented return value: Returns a float between `0.0` and `1.0` representing equity (wins + 0.5 * ties) / total simulations.
  - Hidden state mutation: Stores the resulting probability in `self.last_win_prob` when called via `decide_action(self, game)` (Line 102).
  - Short-circuit side effect: If `len(deck) < total_cards_needed` (Line 76), the function returns the previously cached `self.last_win_prob` without running simulations.
  - Opponent filtering: Opponents are filtered strictly to active states (`PlayerState.IN`, `PlayerState.TO_CALL`, `PlayerState.ALL_IN`). If no active opponents remain, it immediately returns `1.0`.

### 1.3 AI Decision Heuristics (`PokerAI.decide_action`)
- **Location:** Line 101 (`def decide_action(self, game):`)
- **Mismatch:** Undocumented mathematical adjustments and return formats:
  - **SPR Adjustment:** Calculates Stack-to-Pot Ratio `spr = player_chips / (pot + 1)` and applies `spr_mult = 1.0 + (0.15 if spr < 3 else -0.1 if spr > 10 else 0.0)`.
  - **Phase Multipliers:** Uses `PHASE_MULTIPLIERS` dictionary (`PREFLOP`: 0.9, `FLOP`: 1.0, `TURN`: 1.15, `RIVER`: 1.3).
  - **Aggression Factor:** Randomly initialized per AI instance in `__init__` as `random.uniform(0.9, 1.15)`.
  - **Pot Odds Thresholds:** Compares `adjusted = win_prob * phase_mult * spr_mult * aggression_factor` against `pot_odds = to_call / (pot + to_call)`.
  - **Bluff / Random Call Chance:** Includes a 4% random call chance when `adjusted > pot_odds - 0.1`.
  - **Return Format:** Returns a tuple `(ActionType, amount_or_None)`, e.g., `(ActionType.RAISE, raise_amt)`, `(ActionType.CALL, None)`, or `(ActionType.CHECK, None)`.

### 1.4 Multithreaded Execution & GUI Loop (`PokerGUI`)
- **Location:** Lines 132–439 (`class PokerGUI`)
- **Mismatch:**
  - **Multithreading:** Line 340 spawns a daemon thread (`threading.Thread(target=ai_worker, daemon=True).start()`) for AI decision calculation to prevent freezing the Tkinter mainloop during Monte Carlo simulations.
  - **Thread Synchronization:** The worker thread uses `self.root.after(AI_DECIDE_DELAY, ...)` (Line 339) to safely schedule GUI updates on the main Tkinter thread.
  - **Action Error Fallback:** In `apply_action` (Line 343), invalid action exceptions (`ValueError`) catch errors and force a `FOLD` (Line 375).
  - **Automatic Rebuy / Bankruptcy:** In `resolve_hand` (Line 390), players whose chips fall to `0` or below are automatically reset to `self.game.buyin` ($1000) (Line 431), modifying player state as a side effect.

---

## 2. Suggested Clarifications

### 2.1 Technical Jargon Explanation
- **Pot Odds:** Expressed as `to_call / (pot + to_call)`. It represents the ratio of the amount required to call relative to the total pot size after calling.
- **Stack-to-Pot Ratio (SPR):** Calculated as `effective_chips / pot_size`. High SPR (> 10) encourages conservative play due to deeper implied risk; low SPR (< 3) increases commitment and raises aggression.
- **Monte Carlo Simulation:** A computational method that estimates equity by randomly shuffling remaining undealt cards from the deck across hundreds of trials (`sims=600`) and evaluating hand rankings against all active opponents.

### 2.2 System Prerequisites & Environment Dependencies
- **PyPI Package Name:** The library imported as `texasholdem` is installed via `pip install texasholdem`.
- **Display Environment:** `PokerGUI` relies on `tkinter`. Running in headless Linux environments (without X11 / xvfb) will raise `_tkinter.TclError: no display name and no $DISPLAY environment variable`.

---

## 3. Proposed Updated Documentation Text

```markdown
# Antigravity Texas Hold'em Poker AI Simulator

A multi-threaded, Monte Carlo-driven Texas Hold'em Poker simulator and interactive graphical interface built with Python, Tkinter, and the `texasholdem` game engine.

---

## Features

- **Custom Pot Calculation Engine (`MyTexasHoldEm`)**: Extended `TexasHoldEm` class providing accurate multi-pot and side-pot tracking.
- **Monte Carlo AI Evaluator (`PokerAI`)**: Real-time equity calculation using O(1) pre-computed card lookups and multi-opponent simulation loops.
- **Dynamic Decision Heuristics**: Action selection driven by Pot Odds, Stack-to-Pot Ratio (SPR), street phase multipliers, and individual player aggression factors.
- **Non-Blocking Multithreaded GUI (`PokerGUI`)**: Smooth Tkinter interface running AI calculations in background daemon threads to maintain UI responsiveness.
- **Automated Hand Resolution & Rebuys**: Automatic showdown hand evaluation, side-pot distribution logging, and instant bankruptcy rebuys.

---

## Installation & Setup

### Prerequisites
- Python 3.8+
- Tkinter (standard GUI package for Python)
- `texasholdem` PyPI library

```bash
pip install texasholdem
```

*Note for headless Linux systems:* Running `texas_holdem.py` requires an active display server (X11/Wayland) or a virtual display like `xvfb-run python poker/texas_holdem.py`.

---

## API & Architecture Reference

### 1. `MyTexasHoldEm` Subclass
Extends `texasholdem.TexasHoldEm`.

#### `get_total_pot(self) -> int`
- **Description:** Sums chip amounts across all active main and side pots in `self.pots`.
- **Parameters:** None.
- **Returns:** Total pot value in chips (`int`).
- **Side Effects:** None.

---

### 2. `PokerAI` Class
Represents an AI agent capable of assessing equity and taking actions.

#### `__init__(self, player_id: int)`
- **Parameters:** `player_id` (`int`) – The index (0 to 5) assigned to the player.
- **Attributes Initialized:**
  - `self.aggression_factor`: Randomized float between `0.9` and `1.15`.
  - `self.last_win_prob`: Float cached equity score (defaults to `0.0`).

#### `calculate_win_probability(self, game: MyTexasHoldEm, sims: int = 600) -> float`
- **Parameters:**
  - `game` (`MyTexasHoldEm`) – The active game state instance.
  - `sims` (`int`, optional) – Number of Monte Carlo iterations (default: `600`).
- **Returns:** Win probability / equity as a float from `0.0` to `1.0`.
- **Logic:**
  1. Identifies hole cards and community board cards.
  2. Filters active opponents (`PlayerState.IN`, `PlayerState.TO_CALL`, `PlayerState.ALL_IN`).
  3. Returns `1.0` if no active opponents exist.
  4. Runs `sims` random deck shuffles, evaluating scores via `texasholdem.evaluator.evaluate`.
  5. Computes `(wins + 0.5 * ties) / sims`.
- **Side Effects:** Returns cached `self.last_win_prob` if remaining undealt deck size is insufficient.

#### `decide_action(self, game: MyTexasHoldEm) -> Tuple[ActionType, Optional[int]]`
- **Parameters:** `game` (`MyTexasHoldEm`) – Active game instance.
- **Returns:** Tuple containing `(ActionType, amount_or_None)`.
- **Logic & Heuristics:**
  - Updates `self.last_win_prob`.
  - Calculates Pot Odds: `to_call / (pot + to_call)`.
  - Calculates Stack-to-Pot Ratio (SPR): `player_chips / (pot + 1)`. Applies multiplier (`1.15` if SPR < 3, `0.9` if SPR > 10).
  - Applies street phase multiplier (`PREFLOP`: 0.9, `FLOP`: 1.0, `TURN`: 1.15, `RIVER`: 1.3).
  - Multiplies equity by SPR multiplier, phase multiplier, and individual `aggression_factor`.
  - Determines action (`CHECK`, `CALL`, `RAISE`, `ALL_IN`, or `FOLD`).
  - Includes a 4% random call variance for unpredictable play.

---

### 3. `PokerGUI` Class
Tkinter application managing game display and timing.

#### Key Methods
- `__init__(self, root: tk.Tk)`: Constructs GUI window, initializes 6 AI players with $1,000 buy-in ($20/$10 blinds), and schedules automatic game start.
- `step(self)`: Initiates hand or spawns daemon thread (`ai_worker`) for active AI player action calculation.
- `apply_action(self, pid: int, action: ActionType, amount: Optional[int])`: Validates raise boundaries, executes `game.take_action`, logs to UI, and advances state. Catches `ValueError` to force a `FOLD` if invalid.
- `resolve_hand(self)`: Determines winner(s), updates tournament victory statistics, logs winning hand combinations, and rebuys bankrupt players ($0 chips) back to $1,000.

---

## Code Example

```python
from texasholdem import ActionType
from poker.texas_holdem import MyTexasHoldEm, PokerAI

# Initialize game engine
game = MyTexasHoldEm(buyin=1000, big_blind=20, small_blind=10, max_players=6)
game.start_hand()

# Instantiate AI player for position 0
ai = PokerAI(player_id=0)

# Calculate win probability (equity) over 600 Monte Carlo trials
equity = ai.calculate_win_probability(game, sims=600)
print(f"Player 0 Equity: {equity:.1%}")

# Get recommended action
action, amount = ai.decide_action(game)
print(f"Decision: {action.name}, Amount: {amount}")
```
