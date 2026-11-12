"""Deterministic Monopoly rules engine. Agents make the decisions."""
import json
import os
import random
from collections import defaultdict

from board import (BOARD, GO, JAIL, GO_TO_JAIL, N_TILES,
                   CHANCE_MOVES, CHEST_MOVES, STATIONS, UTILITIES)

# --------------------------------------------------------------------------
# Static lookups
# --------------------------------------------------------------------------
GROUP_TILES = {}
for _t in BOARD:
    if _t.kind == "property":
        GROUP_TILES.setdefault(_t.group, []).append(_t.index)
PROPERTY_GROUPS = list(GROUP_TILES.keys())


_PRIOR_CACHE = "monopoly_prior.json"


def _resolve_effect(pos, kind, arg):
    """Return (new_pos, went_to_jail) for a card movement effect."""
    if kind == "none":
        return pos, False
    if kind == "jail":
        return JAIL, True
    if kind == "back3":
        return (pos - 3) % N_TILES, False
    if kind == "move":
        return arg % N_TILES, False
    if kind == "nearest_station":
        for s in STATIONS:
            if s > pos:
                return s, False
        return STATIONS[0], False
    if kind == "nearest_utility":
        for u in UTILITIES:
            if u > pos:
                return u, False
        return UTILITIES[0], False
    return pos, False


def compute_prior():
    """Landing probabilities including doubles, rerolls, and card moves.

    State space at each dice roll: (position, doubles_so_far ∈ {0,1,2}).
    T[i][j] = P(next turn starts on j | this turn started on i)
    L[i][j] = E[# landings on j during this turn | start on i]
    """
    if os.path.exists(_PRIOR_CACHE):
        try:
            v = json.load(open(_PRIOR_CACHE))
            if len(v) == N_TILES:
                return v
        except (json.JSONDecodeError, OSError):
            pass

    T = [[0.0] * N_TILES for _ in range(N_TILES)]
    L = [[0.0] * N_TILES for _ in range(N_TILES)]

    def rec(start, pos, d, prob):
        if prob < 1e-15:
            return
        for a in range(1, 7):
            for b in range(1, 7):
                p = prob / 36.0
                is_double = (a == b)

                # Third double → straight to jail, no move.
                if is_double and d == 2:
                    T[start][JAIL] += p
                    L[start][JAIL] += p
                    continue

                new_pos = (pos + a + b) % N_TILES
                if new_pos == GO_TO_JAIL:
                    T[start][JAIL] += p
                    L[start][JAIL] += p
                    continue

                L[start][new_pos] += p

                tile = BOARD[new_pos]
                if tile.kind in ("chance", "chest"):
                    deck = CHANCE_MOVES if tile.kind == "chance" else CHEST_MOVES
                    n = len(deck)
                    for kind, arg in deck:
                        pp = p / n
                        dest, jailed = _resolve_effect(new_pos, kind, arg)
                        if jailed:
                            T[start][JAIL] += pp
                            L[start][JAIL] += pp
                            continue
                        if dest != new_pos:
                            L[start][dest] += pp
                        if is_double:
                            rec(start, dest, d + 1, pp)
                        else:
                            T[start][dest] += pp
                    continue

                if is_double:
                    rec(start, new_pos, d + 1, p)
                else:
                    T[start][new_pos] += p

    for start in range(N_TILES):
        rec(start, start, 0, 1.0)

    # Steady state of turn-start distribution.
    pi = [1.0 / N_TILES] * N_TILES
    for _ in range(500):
        nxt = [0.0] * N_TILES
        for i, pii in enumerate(pi):
            if not pii:
                continue
            row = T[i]
            for j in range(N_TILES):
                if row[j]:
                    nxt[j] += pii * row[j]
        s = sum(nxt) or 1.0
        pi = [x / s for x in nxt]

    # Expected landings, averaged over turn-start distribution.
    prob = [0.0] * N_TILES
    for i in range(N_TILES):
        for j in range(N_TILES):
            prob[j] += pi[i] * L[i][j]
    s = sum(prob) or 1.0
    prob = [x / s for x in prob]

    json.dump(prob, open(_PRIOR_CACHE, "w"))
    return prob


PRIOR = compute_prior()


# --------------------------------------------------------------------------
# Entities
# --------------------------------------------------------------------------
class PropState:
    __slots__ = ("owner", "houses", "mortgaged")

    def __init__(self):
        self.owner = None
        self.houses = 0          # 5 == hotel
        self.mortgaged = False


class Player:
    def __init__(self, pid, name, is_ai=True):
        self.id = pid
        self.name = name
        self.is_ai = is_ai
        self.cash = 1500
        self.pos = 0
        self.in_jail = False
        self.jail_turns = 0
        self.jail_cards = 0
        self.doubles = 0
        self.bankrupt = False
        self.group_income = defaultdict(float)   # for the learning brains
        self.group_spend = defaultdict(float)


# --------------------------------------------------------------------------
# Cards (deliberately compact but representative)
# --------------------------------------------------------------------------
CHANCE = [
    {"text": "Advance to GO", "action": "move", "value": GO},
    {"text": "Advance to Trafalgar Square", "action": "move", "value": 24},
    {"text": "Advance to Mayfair", "action": "move", "value": 39},
    {"text": "Advance to Pall Mall", "action": "move", "value": 11},
    {"text": "Advance to St. Charles Place", "action": "move", "value": 11},
    {"text": "Advance to the nearest Station", "action": "nearest_station"},
    {"text": "Advance to the nearest Utility", "action": "nearest_utility"},
    {"text": "Go to Jail", "action": "jail"},
    {"text": "Bank pays you dividend of £50", "action": "cash", "value": 50},
    {"text": "Pay poor tax of £15", "action": "cash", "value": -15},
    {"text": "Get Out of Jail Free", "action": "goojf"},
    {"text": "Go back 3 spaces", "action": "back3"},
    {"text": "You win a crossword competition — collect £100", "action": "cash", "value": 100},
    {"text": "Speeding fine of £15", "action": "cash", "value": -15},
    {"text": "Your building loan matures — collect £150", "action": "cash", "value": 150},
    {"text": "Collect £50 from each player", "action": "each_player", "value": 50},
]
CHEST = [
    {"text": "Advance to GO", "action": "move", "value": GO},
    {"text": "Bank error in your favour — collect £200", "action": "cash", "value": 200},
    {"text": "Doctor's fee — pay £50", "action": "cash", "value": -50},
    {"text": "Get Out of Jail Free", "action": "goojf"},
    {"text": "Go to Jail", "action": "jail"},
    {"text": "Inheritance — collect £100", "action": "cash", "value": 100},
    {"text": "Holiday fund matures — collect £100", "action": "cash", "value": 100},
    {"text": "Pay school fees — pay £50", "action": "cash", "value": -50},
    {"text": "It is your birthday — collect £25 from each player", "action": "each_player", "value": 25},
    {"text": "Income Tax refund — collect £20", "action": "cash", "value": 20},
    {"text": "Life insurance premium — collect £100", "action": "cash", "value": 100},
    {"text": "Hospital fees — pay £100", "action": "cash", "value": -100},
    {"text": "Income Tax refund — collect £20", "action": "cash", "value": 20},
    {"text": "Listen to the house rules — collect £50", "action": "cash", "value": 50},
    {"text": "You find money in your old coat — collect £20", "action": "cash", "value": 20},
    {"text": "All players pay you £50 for road tax", "action": "each_player", "value": 50},
]


# --------------------------------------------------------------------------
# Engine
# --------------------------------------------------------------------------
class Engine:
    def __init__(self, agents=None, names=None, seed=None,
                 turn_limit=700, verbose=True):
        self.rng = random.Random(seed)
        names = names or [f"AI {i+1}" for i in range(4)]
        self.players = [Player(i, n) for i, n in enumerate(names)]
        self.agents = agents if agents is not None else [None] * len(self.players)
        self.props = {i: PropState() for i, t in enumerate(BOARD) if t.is_ownable}

        self.landing_counts = [0] * N_TILES
        self.total_landings = 0
        self.prior = PRIOR

        self.house_stock = 32     # total houses in the bank
        self.hotel_stock = 12     # total hotels in the bank

        self.turn = 0
        self.current = 0
        self.over = False
        self.winner = None
        self.turn_limit = turn_limit
        self.verbose = verbose
        self.log_buffer = []
        self.last_trade_turn = {}

        self._chance = CHANCE[:]
        self._chest = CHEST[:]
        self.rng.shuffle(self._chance)
        self.rng.shuffle(self._chest)

    # ---------------- logging ----------------
    def _log(self, msg):
        if self.verbose:
            self.log_buffer.append(msg)
            if len(self.log_buffer) > 3000:
                del self.log_buffer[:1000]

    def drain_log(self):
        out = self.log_buffer
        self.log_buffer = []
        return out

    # ---------------- probabilities ----------------
    def landing_prob(self, idx):
        """Blend the analytic prior with empirical landings from this game."""
        a = self.prior[idx]
        if self.total_landings < 60:
            return a
        emp = self.landing_counts[idx] / self.total_landings
        w = min(0.75, self.total_landings / 800.0)
        return (1 - w) * a + w * emp

    # ---------------- queries ----------------
    def group_count(self, pid, group):
        return sum(1 for i in GROUP_TILES.get(group, ()) if self.props[i].owner == pid)

    def owns_monopoly(self, pid, group):
        tiles = GROUP_TILES.get(group)
        return bool(tiles) and all(self.props[i].owner == pid for i in tiles)

    def would_complete_monopoly(self, pid, idx):
        t = BOARD[idx]
        if t.kind != "property":
            return False
        return all(i == idx or self.props[i].owner == pid
                   for i in GROUP_TILES[t.group])

    def count_kind(self, pid, kind):
        return sum(1 for i, st in self.props.items()
                   if st.owner == pid and BOARD[i].kind == kind)

    def monopolies(self, pid):
        return sum(1 for g in PROPERTY_GROUPS if self.owns_monopoly(pid, g))

    def live_opponents(self, pid):
        return max(1, sum(1 for p in self.players
                          if not p.bankrupt and p.id != pid))

    def net_worth(self, pid):
        p = self.players[pid]
        total = p.cash
        for i, st in self.props.items():
            if st.owner != pid:
                continue
            t = BOARD[i]
            total += t.price // 2 if st.mortgaged else t.price
            total += st.houses * t.house_cost
        return total

    # ---------------- rent ----------------
    def rent_at(self, idx, houses, owner, dice=7):
        t = BOARD[idx]
        if t.kind == "property":
            if houses == 0:
                base = t.rent[0]
                return base * 2 if self.owns_monopoly(owner, t.group) else base
            return t.rent[houses]
        if t.kind == "station":
            n = max(1, self.count_kind(owner, "station"))
            return 25 * (2 ** (n - 1))
        if t.kind == "utility":
            n = self.count_kind(owner, "utility")
            return (10 if n >= 2 else 4) * dice
        return 0

    def rent_for(self, idx, dice=7):
        st = self.props[idx]
        if st.owner is None or st.mortgaged:
            return 0
        return self.rent_at(idx, st.houses, st.owner, dice)

    # ---------------- building ----------------
    def buildable(self, pid):
        out = []
        for g, tiles in GROUP_TILES.items():
            if any(self.props[i].owner != pid for i in tiles):
                continue
            if any(self.props[i].mortgaged for i in tiles):
                continue
            hs = [self.props[i].houses for i in tiles]
            low = min(hs)
            if low >= 5:
                continue
            for i in tiles:
                if self.props[i].houses == low and self.props[i].houses < 5:
                    # Check bank supply
                    if self.props[i].houses == 4 and self.hotel_stock <= 0:
                        continue
                    if self.props[i].houses < 4 and self.house_stock <= 0:
                        continue
                    out.append(i)
        return out

    def _buy_house(self, pid, idx):
        """Buy/place one house (or upgrade 4→hotel) on a property."""
        t = BOARD[idx]
        p = self.players[pid]
        st = self.props[idx]

        if st.houses == 4 and st.houses >= 4:
            # upgrade 4 houses → hotel
            if self.hotel_stock <= 0:
                self._log(f"No hotels available in the bank")
                return False
            self.hotel_stock -= 1
            st.houses = 5
            label = "hotel"
        else:
            if self.house_stock <= 0:
                self._log(f"No houses available in the bank")
                return False
            self.house_stock -= 1
            st.houses += 1
            label = "hotel" if st.houses == 5 else f"{st.houses} house(s)"

        p.cash -= t.house_cost
        p.group_spend[t.group] += t.house_cost
        self._log(f"{p.name} builds {label} on {t.name} (-£{t.house_cost})")
        return True

    def _sell_house(self, pid, idx):
        """Sell back one house/hotel (used by _raise_funds)."""
        t = BOARD[idx]
        st = self.props[idx]
        if st.houses <= 0:
            return 0
        refund = t.house_cost // 2
        self.players[pid].cash += refund
        self._log(f"{self.players[pid].name} sells back on {t.name} (+£{refund})")
        if st.houses == 5:
            self.hotel_stock += 1
            st.houses = 4
        else:
            self.house_stock += 1
            st.houses -= 1
        return refund

    # ---------------- money ----------------
    def _pay(self, pid, amount, creditor=None):
        if amount <= 0:
            return True
        p = self.players[pid]
        if p.cash < amount:
            self._raise_funds(pid, amount)
        if p.cash >= amount:
            p.cash -= amount
            if creditor is not None:
                c = self.players[creditor]
                c.cash += amount
                c.group_income[BOARD[self.players[pid].pos].group] += amount
            return True
        self._bankrupt(pid, creditor)
        return False

    def _raise_funds(self, pid, target):
        p = self.players[pid]
        guard = 0
        while p.cash < target and guard < 60:
            guard += 1
            housed = [i for i, st in self.props.items()
                      if st.owner == pid and st.houses > 0]
            if housed:
                i = max(housed, key=lambda k: self.props[k].houses)
                self._sell_house(pid, i)
                continue
            free = [i for i, st in self.props.items()
                    if st.owner == pid and not st.mortgaged]
            if not free:
                break
            i = min(free, key=lambda k: BOARD[k].price)
            self.props[i].mortgaged = True
            p.cash += BOARD[i].price // 2
            self._log(f"{p.name} mortgages {BOARD[i].name} (+£{BOARD[i].price // 2})")

    def _bankrupt(self, pid, creditor=None):
        p = self.players[pid]
        p.bankrupt = True
        for i, st in self.props.items():
            if st.owner != pid:
                continue
            st.houses = 0
            if creditor is not None:
                st.owner = creditor
            else:
                st.owner = None
                st.mortgaged = False
        if creditor is not None:
            self.players[creditor].cash += p.cash
        p.cash = 0
        self._log(f"*** {p.name} is BANKRUPT ***")
        alive = [q for q in self.players if not q.bankrupt]
        if len(alive) <= 1:
            self.over = True
            self.winner = alive[0].id if alive else None

    # ---------------- movement ----------------
    def _send_to_jail(self, pid):
        p = self.players[pid]
        p.pos = JAIL
        p.in_jail = True
        p.jail_turns = 0
        p.doubles = 0

    def _move(self, pid, steps):
        p = self.players[pid]
        old = p.pos
        p.pos = (p.pos + steps) % N_TILES
        if steps > 0 and p.pos < old:
            p.cash += 200
            self._log(f"{p.name} passes GO (+£200)")

    # ---------------- landings ----------------
    def _resolve_tile(self, pid, dice, depth=0):
        p = self.players[pid]
        idx = p.pos
        tile = BOARD[idx]
        self.landing_counts[idx] += 1
        self.total_landings += 1

        if tile.is_ownable:
            st = self.props[idx]
            if st.owner is None:
                if self._ask_buy(pid, idx):
                    self._buy(pid, idx)
            elif st.owner != pid and not st.mortgaged:
                rent = self.rent_for(idx, dice)
                if rent > 0:
                    self._log(f"{p.name} pays £{rent} rent to "
                              f"{self.players[st.owner].name} for {tile.name}")
                    self._pay(pid, rent, st.owner)
            return

        if tile.kind == "tax":
            self._log(f"{p.name} pays {tile.name} £{tile.amount}")
            self._pay(pid, tile.amount)
        elif tile.kind == "go":
            p.cash += 200
            self._log(f"{p.name} lands on GO (+£200)")
        elif tile.kind == "gotojail":
            self._log(f"{p.name} goes to jail")
            self._send_to_jail(pid)
        elif tile.kind in ("chance", "chest") and depth < 3:
            self._draw_card(pid, tile.kind, dice, depth)

    def _ask_buy(self, pid, idx):
        """Ask the agent to buy; if it declines, run an auction."""
        agent = self.agents[pid]
        if agent is None:
            self._auction(pid, idx)
            return
        if agent.decide_buy(self, pid, idx):
            self._buy(pid, idx)
        else:
            t = BOARD[idx]
            self._log(f"{self.players[pid].name} declines {t.name}; "
                      f"going to auction")
            self._auction(pid, idx)

    def _buy(self, pid, idx, price=None):
        t = BOARD[idx]
        p = self.players[pid]
        cost = price if price is not None else t.price
        if p.cash < cost:
            return
        p.cash -= cost
        p.group_spend[t.group] += cost
        self.props[idx].owner = pid
        self._log(f"{p.name} buys {t.name} for £{cost}")

    def _auction(self, decliner, idx):
        """First-price sealed-bid auction for an unowned property.

        Each alive player with a bid_auction method submits a bid.
        Highest bidder wins and pays their bid.  No bidders → stays
        unowned.
        """
        t = BOARD[idx]
        active = []
        for p in self.players:
            if p.bankrupt:
                continue
            agent = self.agents[p.id]
            if agent is None or not hasattr(agent, "bid_auction"):
                continue
            bid = agent.bid_auction(self, p.id, idx)
            if bid and bid > 0:
                active.append((p.id, bid))

        if not active:
            self._log(f"No bidders for {t.name} — remains unowned")
            return

        active.sort(key=lambda x: x[1], reverse=True)
        winner_id, price = active[0]
        if self.players[winner_id].cash < price:
            price = self.players[winner_id].cash
        if price <= 0:
            return
        self._buy(winner_id, idx, price=price)
        self._log(f"AUCTION: {self.players[winner_id].name} wins "
                  f"{t.name} for £{price}")

    def _draw_card(self, pid, deck_name, dice, depth):
        deck = self._chance if deck_name == "chance" else self._chest
        if not deck:
            deck = (CHANCE if deck_name == "chance" else CHEST)[:]
            self.rng.shuffle(deck)
            if deck_name == "chance":
                self._chance = deck
            else:
                self._chest = deck
        card = deck.pop(0)
        p = self.players[pid]
        self._log(f"{p.name} draws: {card['text']}")
        act = card["action"]
        if act == "move":
            dest = card["value"] % N_TILES
            if dest > p.pos:
                p.cash += 200
                self._log(f"{p.name} passes GO (+£200)")
            p.pos = dest
            self._resolve_tile(pid, dice, depth + 1)
        elif act == "back3":
            p.pos = (p.pos - 3) % N_TILES
            self._resolve_tile(pid, dice, depth + 1)
        elif act == "nearest_station":
            dest = STATIONS[0]
            for s in STATIONS:
                if s > p.pos:
                    dest = s
                    break
            if dest > p.pos:
                p.cash += 200
                self._log(f"{p.name} passes GO (+£200)")
            p.pos = dest
            self._resolve_tile(pid, dice, depth + 1)
        elif act == "nearest_utility":
            dest = UTILITIES[0]
            for u in UTILITIES:
                if u > p.pos:
                    dest = u
                    break
            if dest > p.pos:
                p.cash += 200
                self._log(f"{p.name} passes GO (+£200)")
            p.pos = dest
            self._resolve_tile(pid, dice, depth + 1)
        elif act == "jail":
            self._send_to_jail(pid)
        elif act == "cash":
            if card["value"] >= 0:
                p.cash += card["value"]
            else:
                self._pay(pid, -card["value"])
        elif act == "each_player":
            amt = card["value"]
            for other in self.players:
                if other.id == pid or other.bankrupt:
                    continue
                if other.cash >= amt:
                    other.cash -= amt
                    p.cash += amt
                else:
                    # They pay all they have
                    p.cash += other.cash
                    other.cash = 0
            self._log(f"{p.name} collects £{amt} from each player")
        elif act == "goojf":
            p.jail_cards += 1
        # Return the card to the bottom of the deck (except GOOJF, which
        # is held in the player's hand and returned when used).
        if act != "goojf":
            deck.append(card)

    # ---------------- trading ----------------
    def _maybe_trade(self, pid):
        agent = self.agents[pid]
        if agent is None or not hasattr(agent, "propose_trade"):
            return
        if self.turn - self.last_trade_turn.get(pid, -99) < 6:
            return
        offer = agent.propose_trade(self, pid)
        if not offer:
            return
        idx, seller, cash = offer
        seller_agent = self.agents[seller]
        if seller_agent is None:
            return
        if not seller_agent.consider_trade(self, seller, pid, idx, cash):
            return
        buyer = self.players[pid]
        vend = self.players[seller]
        if buyer.cash < cash:
            return
        buyer.cash -= cash
        vend.cash += cash
        self.props[idx].owner = pid
        self.last_trade_turn[pid] = self.turn
        self._log(f"TRADE: {buyer.name} buys {BOARD[idx].name} "
                  f"from {vend.name} for £{cash}")

    # ---------------- turn loop ----------------
    def play_turn(self):
        if self.over:
            return
        pid = self.current
        p = self.players[pid]
        if p.bankrupt:
            self._next_player()
            return

        self._log(f"--- {p.name} | cash £{p.cash} | pos {BOARD[p.pos].name} ---")
        self._maybe_trade(pid)

        # ---------- jail ----------
        if p.in_jail:
            got_out = False
            if p.jail_cards > 0:
                p.jail_cards -= 1
                p.in_jail = False
                got_out = True
                self._log(f"{p.name} uses Get Out of Jail Free card")
            elif self.agents[pid] is not None and self.agents[pid].decide_bail(self, pid):
                if self._pay(pid, 50):
                    p.in_jail = False
                    got_out = True
                    self._log(f"{p.name} pays £50 to leave jail")
                if p.bankrupt:
                    self._next_player()
                    return

            if not got_out:
                d1, d2 = self.rng.randint(1, 6), self.rng.randint(1, 6)
                p.jail_turns += 1
                if d1 == d2:
                    # Leave on doubles — move by the doubles; no extra turn.
                    p.in_jail = False
                    p.jail_turns = 0
                    self._log(f"{p.name} rolls doubles ({d1}+{d2}) and leaves jail")
                    self._move(pid, d1 + d2)
                    self._resolve_tile(pid, d1 + d2)
                    self._next_player()
                    return
                if p.jail_turns >= 3:
                    # Forced fine, then move by the roll you just made.
                    p.jail_turns = 0
                    if self._pay(pid, 50):
                        p.in_jail = False
                        self._log(f"{p.name} pays £50 after 3 attempts, rolls {d1}+{d2}")
                        self._move(pid, d1 + d2)
                        self._resolve_tile(pid, d1 + d2)
                    self._next_player()
                    return
                self._log(f"{p.name} stays in jail (rolled {d1}+{d2})")
                self._next_player()
                return

        # ---------- normal turn ----------
        self._try_unmortgage(pid)
        self._ai_build(pid)
        if self.over:
            return

        doubles = 0
        while True:
            d1, d2 = self.rng.randint(1, 6), self.rng.randint(1, 6)
            total = d1 + d2
            self._log(f"{p.name} rolls {d1}+{d2} = {total}")

            if d1 == d2:
                doubles += 1
                if doubles == 3:
                    # Three doubles → straight to jail, no move.
                    self._log(f"{p.name} rolls 3 doubles - straight to jail")
                    self._send_to_jail(pid)
                    break

            self._move(pid, total)
            self._resolve_tile(pid, total)
            if self.over or p.bankrupt:
                break
            if d1 != d2:
                break
            # else loop for the extra double roll

        self._next_player()

    def _ai_build(self, pid):
        agent = self.agents[pid]
        if agent is None:
            return
        for _ in range(8):
            idx = agent.choose_build(self, pid)
            if idx is None:
                break
            t = BOARD[idx]
            if self.players[pid].cash < t.house_cost:
                break
            if not self._buy_house(pid, idx):
                break

    def _try_unmortgage(self, pid):
        """Ask the agent to unmortgage properties it can afford."""
        agent = self.agents[pid]
        if agent is None or not hasattr(agent, "choose_unmortgage"):
            return
        targets = agent.choose_unmortgage(self, pid)
        if not targets:
            return
        p = self.players[pid]
        for i in targets:
            st = self.props[i]
            if not st.mortgaged or st.owner != pid:
                continue
            t = BOARD[i]
            cost = int(t.price * 1.1)
            if p.cash < cost:
                continue
            p.cash -= cost
            st.mortgaged = False
            p.group_spend[t.group] += cost
            self._log(f"{p.name} unmortgages {t.name} (-£{cost})")

    def _next_player(self):
        self.turn += 1
        if self.turn >= self.turn_limit:
            self.over = True
            alive = [q for q in self.players if not q.bankrupt]
            self.winner = max(alive, key=lambda q: self.net_worth(q.id)).id
            self._log("Turn limit reached - highest net worth wins")
            return
        for _ in range(len(self.players)):
            self.current = (self.current + 1) % len(self.players)
            if not self.players[self.current].bankrupt:
                break

    def summary(self):
        rows = []
        for p in self.players:
            rows.append({
                "name": p.name,
                "cash": p.cash,
                "net_worth": self.net_worth(p.id),
                "monopolies": self.monopolies(p.id),
                "properties": sum(1 for st in self.props.values() if st.owner == p.id),
                "bankrupt": p.bankrupt,
            })
        return rows


def play_game(eng, max_turns=3000):
    """Run a whole game headless and let every agent learn from it."""
    guard = 0
    while not eng.over and guard < max_turns:
        eng.play_turn()
        guard += 1
    if not eng.over:
        eng.over = True
        alive = [q for q in eng.players if not q.bankrupt]
        eng.winner = max(alive, key=lambda q: eng.net_worth(q.id)).id
    for i, a in enumerate(eng.agents):
        if a is not None:
            a.end_game(eng, i)
    return eng