"""Learning agents: Expected Value + learned group multipliers + Q-table."""
import json
import os
import random

from board import BOARD, PLAYER_COLORS
from tuning import PARAM_SPEC

GROUPS = ["Brown", "Light Blue", "Pink", "Orange", "Red",
          "Yellow", "Green", "Dark Blue", "Station", "Utility"]

DEFAULT_BRAINS = "monopoly_brains.json"


# --------------------------------------------------------------------------
# Persistent brain
# --------------------------------------------------------------------------
class Brain:
    def __init__(self):
        # learned ROI per colour group (accumulated income vs spend)
        self.income = {g: 0.0 for g in GROUPS}
        self.spend = {g: 0.0 for g in GROUPS}
        # Q-table: key "state|action" -> value
        self.q = {}
        self.games = 0

    # --- EV multiplier learned from realised ROI -------------------------
    def group_multiplier(self, group):
        group = group if group in GROUPS else "Station"
        inc = self.income.get(group, 0.0)
        sp = self.spend.get(group, 0.0)
        if sp < 100.0:
            return 1.0
        ratio = inc / sp
        return max(0.6, min(1.8, 0.55 + ratio))

    # --- Q helpers -------------------------------------------------------
    def q_get(self, state, action):
        return self.q.get(f"{state}|{action}", 0.0)

    def q_set(self, state, action, value):
        self.q[f"{state}|{action}"] = value

    def q_update(self, state, action, reward, next_state, alpha, gamma):
        key = f"{state}|{action}"
        old = self.q.get(key, 0.0)
        best_next = max(self.q_get(next_state, a) for a in (0, 1))
        self.q[key] = old + alpha * (reward + gamma * best_next - old)

    # --- persistence -----------------------------------------------------
    def to_dict(self):
        return {"income": self.income, "spend": self.spend,
                "q": self.q, "games": self.games}

    @classmethod
    def from_dict(cls, d):
        b = cls()
        b.income.update(d.get("income", {}))
        b.spend.update(d.get("spend", {}))
        b.q.update(d.get("q", {}))
        b.games = d.get("games", 0)
        return b


def load_brains(path=DEFAULT_BRAINS, n=4):
    if os.path.exists(path):
        try:
            with open(path) as f:
                data = json.load(f)
            brains = [Brain.from_dict(d) for d in data][:n]
            while len(brains) < n:
                brains.append(Brain())
            return brains
        except (json.JSONDecodeError, OSError):
            pass
    return [Brain() for _ in range(n)]


def save_brains(brains, path=DEFAULT_BRAINS):
    with open(path, "w") as f:
        json.dump([b.to_dict() for b in brains], f, indent=1)


# --------------------------------------------------------------------------
# Agent
# --------------------------------------------------------------------------
class Agent:
    def __init__(self, pid, brain=None, tuner=None, rng=None):
        self.pid = pid
        self.brain = brain or Brain()
        self.tuner = tuner
        self.rng = rng or random.Random()
        self.params = tuner.sample() if tuner else {k: v[2] for k, v in PARAM_SPEC.items()}

    # -------- Expected value --------
    def property_value(self, eng, pid, idx):
        t = BOARD[idx]
        p_land = eng.landing_prob(idx)

        if t.kind == "property":
            if eng.would_complete_monopoly(pid, idx):
                rent = t.rent[0] * 2.0 + (t.rent[2] - t.rent[0]) * 0.6
            elif eng.group_count(pid, t.group) > 0:
                rent = t.rent[0] * 1.5
            else:
                rent = float(t.rent[0])
        elif t.kind == "station":
            n = eng.count_kind(pid, "station") + 1
            rent = 25.0 * (2 ** max(0, n - 1))
        else:
            rent = 40.0

        mult = self.brain.group_multiplier(t.group or t.kind)
        return p_land * self.params["horizon"] * rent * mult

    def _reserve(self, eng, pid):
        return eng.players[pid].cash * self.params["reserve_frac"]

    # -------- Buying --------
    def decide_buy(self, eng, pid, idx):
        t = BOARD[idx]
        p = eng.players[pid]
        value = self.property_value(eng, pid, idx)
        denial = 0.0
        if t.kind == "property" and any(
                eng.props[i].owner not in (None, pid)
                for i in eng.props if BOARD[i].group == t.group):
            denial = self.params["denial_weight"] * t.price
        total = value + 0.5 * t.price + denial
        if total < self.params["buy_threshold"] * t.price:
            return False
        if p.cash - t.price < self._reserve(eng, pid) and total < 1.8 * t.price:
            return False
        return True

    def bid_auction(self, eng, pid, idx):
        """Sealed-bid auction: submit a bid for an unowned property, or 0."""
        t = BOARD[idx]
        p = eng.players[pid]
        value = self.property_value(eng, pid, idx)
        # Bid up to the property's EV, clamped by cash and reserve
        max_bid = min(value, p.cash - self._reserve(eng, pid))
        if max_bid < t.price * 0.5:
            return 0
        return int(max_bid)

    def choose_unmortgage(self, eng, pid):
        """Return a list of property indices to unmortgage, or None."""
        p = eng.players[pid]
        reserve = self._reserve(eng, pid)
        unmortgage = []
        for i, st in eng.props.items():
            if st.owner == pid and st.mortgaged:
                t = BOARD[i]
                cost = int(t.price * 1.1)
                if p.cash - cost >= reserve:
                    unmortgage.append(i)
        return unmortgage if unmortgage else None

    # -------- Building --------
    def _payback_threshold(self, eng, pid):
        cash = eng.players[pid].cash
        return self.params["payback_base"] + self.params["payback_cash_scale"] * cash

    def choose_build(self, eng, pid):
        p = eng.players[pid]
        reserve = self._reserve(eng, pid)
        threshold = self._payback_threshold(eng, pid)
        best, best_pp = None, None
        for idx in eng.buildable(pid):
            t = BOARD[idx]
            st = eng.props[idx]
            if p.cash - t.house_cost < reserve:
                continue
            cur = eng.rent_at(idx, st.houses, pid)
            nxt = eng.rent_at(idx, st.houses + 1, pid)
            gain = nxt - cur
            if gain <= 0:
                continue
            per_turn = gain * eng.landing_prob(idx)
            if per_turn <= 0:
                continue
            pp = t.house_cost / per_turn
            if pp < threshold and (best_pp is None or pp < best_pp):
                best, best_pp = idx, pp
        return best

    def decide_bail(self, eng, pid):
        return eng.players[pid].cash > self.params["bail_threshold"]

    # -------- Q-learning --------
    def _state(self, eng, pid):
        p = eng.players[pid]
        cash_lvl = 0 if p.cash < 200 else (1 if p.cash < 700 else 2)
        opp_mono = min(2, sum(eng.monopolies(q.id) for q in eng.players
                              if not q.bankrupt and q.id != pid))
        phase = min(2, eng.turn // 120)
        return f"{cash_lvl},{opp_mono},{phase}"

    def _q_choice(self, state):
        if self.rng.random() < self.params["epsilon"]:
            return self.rng.choice((0, 1))
        return 0 if (self.brain.q_get(state, 0) >= self.brain.q_get(state, 1)) else 1

    def consider_trade(self, eng, pid, buyer, idx, cash):
        state = self._state(eng, pid)
        my_value = self.property_value(eng, pid, idx)
        reward = (cash - my_value * 0.6) / 100.0
        if eng.would_complete_monopoly(buyer, idx):
            reward -= 4.0
        action = self._q_choice(state)
        self.brain.q_update(state, action, reward, state,
                            self.params["alpha"], self.params["gamma"])
        return action == 0

    def end_game(self, eng, pid):
        p = eng.players[pid]
        b = self.brain
        b.games += 1
        for g, v in p.group_income.items():
            if g in b.income:
                b.income[g] += v
        for g, v in p.group_spend.items():
            if g in b.spend:
                b.spend[g] += v


# --------------------------------------------------------------------------
# Human agent (used when the GUI enables "I play")
# --------------------------------------------------------------------------
class HumanAgent:
    def __init__(self, root):
        self.root = root

    def _choose(self, title, message, options):
        """Modal picker. options = [(label, value), ...]; returns value or None."""
        import tkinter as tk
        win = tk.Toplevel(self.root)
        win.title(title)
        win.configure(bg="#1b1b1f")
        win.transient(self.root)
        win.grab_set()
        result = {"v": None}

        tk.Label(win, text=message, bg="#1b1b1f", fg="#f1faee",
                 justify="left", wraplength=420,
                 font=("Segoe UI", 10)
                 ).pack(padx=12, pady=10)

        for label, val in options:
            def _cb(v=val):
                result["v"] = v
                win.destroy()
            tk.Button(win, text=label, command=_cb, bg="#2a9d8f", fg="white",
                      relief="flat", anchor="w"
                      ).pack(fill="x", padx=12, pady=2)

        win.protocol("WM_DELETE_WINDOW", win.destroy)
        self.root.wait_window(win)
        return result["v"]

    def decide_buy(self, eng, pid, idx):
        t = BOARD[idx]
        p = eng.players[pid]
        rents = " → ".join(f"£{r}" for r in t.rent) if t.rent else "n/a"
        return bool(self._choose(
            "Buy property?",
            f"{t.name} ({t.group})\nPrice: £{t.price}\n"
            f"Rents (0–5 houses): {rents}\nYour cash: £{p.cash}",
            [("Buy", True), ("Pass", False)]))

    def choose_build(self, eng, pid):
        opts = eng.buildable(pid)
        p = eng.players[pid]
        if not opts:
            return None
        options = [("Don't build", None)]
        for i in opts:
            t = BOARD[i]
            st = eng.props[i]
            cur = eng.rent_at(i, st.houses, pid)
            nxt = eng.rent_at(i, st.houses + 1, pid)
            label = (f"{t.name}: {st.houses}→{st.houses + 1} houses  "
                     f"(rent £{cur}→£{nxt}, cost £{t.house_cost})")
            options.append((label, i))
        return self._choose("Build phase",
                            f"Your cash: £{p.cash}", options)

    def decide_bail(self, eng, pid):
        return bool(self._choose(
            "Jail",
            f"Pay £50 bail?\nYour cash: £{eng.players[pid].cash}",
            [("Pay £50", True), ("Roll for doubles", False)]))

    def consider_trade(self, eng, pid, buyer, idx, cash):
        t = BOARD[idx]
        p = eng.players[pid]
        would_complete = eng.would_complete_monopoly(buyer, idx)
        return bool(self._choose(
            "Trade offer",
            f"{eng.players[buyer].name} offers £{cash} for {t.name}.\n"
            f"Your cash: £{p.cash}\n"
            f"Completes their {t.group} monopoly: "
            f"{'YES — dangerous' if would_complete else 'no'}",
            [("Accept", True), ("Reject", False)]))

    def bid_auction(self, eng, pid, idx):
        """Ask the human for a sealed bid in an auction."""
        t = BOARD[idx]
        p = eng.players[pid]
        msg = (f"Auction for {t.name}\n"
               f"Price: £{t.price}\nYour cash: £{p.cash}")
        v = self._choose("Auction bid", msg, [
            (f"Bid £{t.price}", t.price),
            (f"Bid £{t.price // 2}", t.price // 2),
            (f"Bid £50", 50),
            ("Pass", 0),
        ])
        if v is None:
            return 0
        return v

    def propose_trade(self, eng, pid):
        return None

    def choose_unmortgage(self, eng, pid):
        """Ask the human which mortgaged properties to unmortgage."""
        p = eng.players[pid]
        targets = []
        for i, st in eng.props.items():
            if st.owner == pid and st.mortgaged:
                t = BOARD[i]
                cost = int(t.price * 1.1)
                targets.append((i, t, cost))
        if not targets or p.cash < int(targets[0][2]):
            return None
        options = [("Don't unmortgage now", None)]
        for i, t, cost in targets:
            options.append((f"Unmortgage {t.name} (£{cost})", [i]))
        v = self._choose("Unmortgage properties",
                         f"Your cash: £{p.cash}", options)
        if v is None or v is None:
            return None
        return v

    def end_game(self, eng, pid):
        pass