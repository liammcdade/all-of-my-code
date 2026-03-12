"""
Monopoly 2024 (UK board) - Full engine + Monte Carlo action advisor
 Start money: £1500 for all players.

Usage:
- Run script. It runs a demo game with AI suggesting moves.
- Import classes and call Game.simulate_action_choice(player_index) to get advice.

Notes:
- This is a practical, complete simulator with simplified Chance/Community effects,
  auction and trade heuristics, and a Monte Carlo evaluator for action choice.
- It's designed to be readable and extensible rather than optimised for max speed.
"""

import random
import copy
from collections import deque, defaultdict
from typing import List, Dict, Optional, Tuple
import tkinter as tk
from tkinter import ttk, messagebox
import threading

# ---------- Board definition (UK Monopoly) ----------
# Each square: dict with 'name', 'type' in {'property','railroad','utility','tax','go','jail','go_to_jail','chance','community','free_parking'}
# For property: 'color', 'cost', 'rent' list [base,1house,2,3,4,hotel], 'house_cost'
# For railroad: 'cost'
# For utility: 'cost'
BOARD = [
    {"name":"Go","type":"go"},
    {"name":"Old Kent Road","type":"property","color":"brown","cost":60,"rent":[2,10,30,90,160,250],"house_cost":50},
    {"name":"Community Chest","type":"community"},
    {"name":"Whitechapel Road","type":"property","color":"brown","cost":60,"rent":[4,20,60,180,320,450],"house_cost":50},
    {"name":"Income Tax","type":"tax","amount":200},
    {"name":"Kings Cross Station","type":"railroad","cost":200},
    {"name":"The Angel, Islington","type":"property","color":"light blue","cost":100,"rent":[6,30,90,270,400,550],"house_cost":50},
    {"name":"Chance","type":"chance"},
    {"name":"Euston Road","type":"property","color":"light blue","cost":100,"rent":[6,30,90,270,400,550],"house_cost":50},
    {"name":"Pentonville Road","type":"property","color":"light blue","cost":120,"rent":[8,40,100,300,450,600],"house_cost":50},
    {"name":"Just Visiting","type":"jail"},
    {"name":"Pall Mall","type":"property","color":"pink","cost":140,"rent":[10,50,150,450,625,750],"house_cost":100},
    {"name":"Electric Company","type":"utility","cost":150},
    {"name":"Whitehall","type":"property","color":"pink","cost":140,"rent":[10,50,150,450,625,750],"house_cost":100},
    {"name":"Northumberland Avenue","type":"property","color":"pink","cost":160,"rent":[12,60,180,500,700,900],"house_cost":100},
    {"name":"Marylebone Station","type":"railroad","cost":200},
    {"name":"Bow Street","type":"property","color":"orange","cost":180,"rent":[14,70,200,550,750,950],"house_cost":100},
    {"name":"Community Chest","type":"community"},
    {"name":"Marlborough Street","type":"property","color":"orange","cost":180,"rent":[14,70,200,550,750,950],"house_cost":100},
    {"name":"Vine Street","type":"property","color":"orange","cost":200,"rent":[16,80,220,600,800,1000],"house_cost":100},
    {"name":"Free Parking","type":"free_parking"},
    {"name":"Strand","type":"property","color":"red","cost":220,"rent":[18,90,250,700,875,1050],"house_cost":150},
    {"name":"Chance","type":"chance"},
    {"name":"Fleet Street","type":"property","color":"red","cost":220,"rent":[18,90,250,700,875,1050],"house_cost":150},
    {"name":"Trafalgar Square","type":"property","color":"red","cost":240,"rent":[20,100,300,750,925,1100],"house_cost":150},
    {"name":"Fenchurch Street Station","type":"railroad","cost":200},
    {"name":"Leicester Square","type":"property","color":"yellow","cost":260,"rent":[22,110,330,800,975,1150],"house_cost":150},
    {"name":"Coventry Street","type":"property","color":"yellow","cost":260,"rent":[22,110,330,800,975,1150],"house_cost":150},
    {"name":"Water Works","type":"utility","cost":150},
    {"name":"Piccadilly","type":"property","color":"yellow","cost":280,"rent":[24,120,360,850,1025,1200],"house_cost":150},
    {"name":"Go To Jail","type":"go_to_jail"},
    {"name":"Regent Street","type":"property","color":"green","cost":300,"rent":[26,130,390,900,1100,1275],"house_cost":200},
    {"name":"Oxford Street","type":"property","color":"green","cost":300,"rent":[26,130,390,900,1100,1275],"house_cost":200},
    {"name":"Community Chest","type":"community"},
    {"name":"Bond Street","type":"property","color":"green","cost":320,"rent":[28,150,450,1000,1200,1400],"house_cost":200},
    {"name":"Liverpool Street Station","type":"railroad","cost":200},
    {"name":"Chance","type":"chance"},
    {"name":"Park Lane","type":"property","color":"dark blue","cost":350,"rent":[35,175,500,1100,1300,1500],"house_cost":200},
    {"name":"Super Tax","type":"tax","amount":100},
    {"name":"Mayfair","type":"property","color":"dark blue","cost":400,"rent":[50,200,600,1400,1700,2000],"house_cost":200},
]
Real_prices = {
'Old Kent Road': 813000,
'Whitechapel Road': 590000,
'The Angel, Islington': 866000,
'Euston Road': 1080000,
'Pentonville Road': 866000,
'Pall Mall': 1380000,
'Whitehall': 1390000,
'Northumberland Avenue': 1280000,
'Bow Street': 1280000,
'Marlborough Street': 2480000,
'Vine Street': 1700000,
'Strand': 2160000,
'Fleet Street': 1080000,
'Trafalgar Square': 1280000,
'Leicester Square': 1280000,
'Coventry Street': 1900000,
'Piccadilly': 2000000,
'Regent Street': 1700000,
'Oxford Street': 1300000,
'Bond Street': 806000,
'Park Lane': 1700000,
'Mayfair': 3150000,
}
max_real = max(Real_prices.values())
for sq in BOARD:
    if sq['type'] == 'property':
        name = sq['name']
        if name in Real_prices:
            real = Real_prices[name]
            old_cost = sq['cost']
            sq['cost'] = max(60, round((real / max_real) * 400))
            mult = sq['cost'] / old_cost
            sq['rent'] = [round(x * mult) for x in sq['rent']]
            sq['house_cost'] = round(sq['house_cost'] * mult)
BOARD_SIZE = len(BOARD)

# ---------- Chance and Community Chest decks (simplified, common effects) ----------
CHANCE_CARDS = deque([
    {"desc":"Advance to GO","type":"move","position":0,"collect":200},
    {"desc":"Go to Jail","type":"go_to_jail"},
    {"desc":"Advance to Trafalgar Square","type":"move","position":24,"collect":200},  # UK equivalent
    {"desc":"Advance to Pall Mall","type":"move","position":11},
    {"desc":"Take a trip to Kings Cross Station","type":"move","position":5},
    {"desc":"Advance to nearest Utility","type":"nearest_utility"},
    {"desc":"Advance to nearest Station","type":"nearest_railroad"},
    {"desc":"Bank pays you dividend £50","type":"cash","amount":50},
    {"desc":"Get out of Jail Free","type":"get_out_of_jail_free","deck":"chance"},
    {"desc":"Pay poor tax £15","type":"cash","amount":-15},
])
COMMUNITY_CHEST_CARDS = deque([
    {"desc":"Bank error in your favor. Collect $200","type":"cash","amount":200},
    {"desc":"Doctor's fee. Pay $50","type":"cash","amount":-50},
    {"desc":"From sale of stock you get $50","type":"cash","amount":50},
    {"desc":"Go to Jail","type":"go_to_jail"},
    {"desc":"Get out of Jail Free","type":"get_out_of_jail_free","deck":"community"},
    {"desc":"Grand Opera Night. Collect $50 from every player","type":"collect_from_players","amount":50},
])

def shuffle_decks():
    random.shuffle(CHANCE_CARDS)
    random.shuffle(COMMUNITY_CHEST_CARDS)

shuffle_decks()

# ---------- Player and property state ----------
class PropertyState:
    def __init__(self, index, info):
        self.index = index
        self.info = info
        self.owner: Optional[int] = None
        self.houses = 0  # 0-4 houses, 5 means hotel
        self.mortgaged = False

class Player:
    def __init__(self, name: str, index: int):
        self.name = name
        self.index = index
        self.cash = 1500
        self.position = 0
        self.properties: List[int] = []
        self.in_jail = False
        self.jail_turns = 0
        self.get_out_of_jail_free = 0
        self.bankrupt = False

    def net_worth(self, prop_states: Dict[int, PropertyState]) -> int:
        worth = self.cash
        for p in self.properties:
            ps = prop_states[p]
            worth += ps.info.get("cost", 0)
            # house value approximated
            worth += ps.houses * ps.info.get("house_cost", 0)
        return worth

# ---------- Game engine ----------
class MonopolyGame:
    def __init__(self, player_names: List[str]):
        self.players: List[Player] = [Player(n, i) for i,n in enumerate(player_names)]
        self.turn = 0
        self.prop_states: Dict[int, PropertyState] = {}
        for i, sq in enumerate(BOARD):
            if sq["type"] in ("property","railroad","utility"):
                self.prop_states[i] = PropertyState(i, sq)
        self.chance = deque(CHANCE_CARDS)
        self.community = deque(COMMUNITY_CHEST_CARDS)
        self.free_parking_cash = 0
        self.last_dice = (0,0)
        self.log = []
        self.game_history = []  # snapshots optional

    def clone(self):
        return copy.deepcopy(self)

    def active_players(self) -> List[Player]:
        return [p for p in self.players if not p.bankrupt]

    def roll_dice(self):
        a = random.randint(1,6)
        b = random.randint(1,6)
        self.last_dice = (a,b)
        return a, b

    def move_player(self, p: Player, steps:int):
        prev = p.position
        p.position = (p.position + steps) % BOARD_SIZE
        if p.position < prev:
            # passed GO
            p.cash += 200

    def send_to_jail(self, p: Player):
        p.position = 10
        p.in_jail = True
        p.jail_turns = 0

    def draw_card(self, deck: str):
        if deck == "chance":
            card = self.chance.popleft()
            self.chance.append(card)
            return card
        else:
            card = self.community.popleft()
            self.community.append(card)
            return card

    def nearest(self, pos, kind):
        # nearest utility or railroad forward
        for offset in range(1, BOARD_SIZE):
            idx = (pos + offset) % BOARD_SIZE
            if BOARD[idx]["type"] == kind:
                return idx
        return None

    def resolve_card(self, player: Player, card):
        t = card["type"]
        if t == "move":
            player.position = card["position"]
            if card.get("collect"):
                player.cash += card["collect"]
        elif t == "go_to_jail":
            self.send_to_jail(player)
        elif t == "cash":
            player.cash += card["amount"]
        elif t == "get_out_of_jail_free":
            player.get_out_of_jail_free += 1
        elif t == "collect_from_players":
            amt = card["amount"]
            for oth in self.players:
                if oth.index != player.index and not oth.bankrupt:
                    pay = min(oth.cash, amt)
                    oth.cash -= pay
                    player.cash += pay
        elif t == "nearest_utility":
            idx = self.nearest(player.position, "utility")
            if idx is not None:
                player.position = idx
                self.handle_landing(player, idx)
        elif t == "nearest_railroad":
            idx = self.nearest(player.position, "railroad")
            if idx is not None:
                player.position = idx
                self.handle_landing(player, idx)

    def handle_landing(self, player: Player, idx: int):
        sq = BOARD[idx]
        st = sq["type"]
        if st == "property":
            ps = self.prop_states[idx]
            if ps.owner is None:
                # offer to buy is external decision
                return
            elif ps.owner != player.index and not ps.mortgaged:
                rent = self.calculate_rent(ps)
                self.transfer_cash(player, self.players[ps.owner], rent)
        elif st == "railroad":
            ps = self.prop_states[idx]
            if ps.owner is None:
                return
            elif ps.owner != player.index and not ps.mortgaged:
                # rent = 25 * 2^(owned-1)
                owned = sum(1 for v in self.prop_states.values() if v.info["type"]=="railroad" and v.owner==ps.owner)
                rent = 25 * (2 ** (owned-1))
                self.transfer_cash(player, self.players[ps.owner], rent)
        elif st == "utility":
            ps = self.prop_states[idx]
            if ps.owner is None:
                return
            elif ps.owner != player.index and not ps.mortgaged:
                owner = ps.owner
                dice_total = sum(self.last_dice) if all(self.last_dice) else random.randint(1,6)+random.randint(1,6)
                owned = sum(1 for v in self.prop_states.values() if v.info["type"]=="utility" and v.owner==owner)
                if owned == 1:
                    rent = 4 * dice_total
                else:
                    rent = 10 * dice_total
                self.transfer_cash(player, self.players[owner], rent)
        elif st == "tax":
            amt = sq.get("amount", 0)
            self.transfer_cash(player, None, amt)
        elif st == "chance":
            card = self.draw_card("chance")
            self.resolve_card(player, card)
        elif st == "community":
            card = self.draw_card("community")
            self.resolve_card(player, card)
        elif st == "go_to_jail":
            self.send_to_jail(player)
        elif st == "free_parking":
            player.cash += self.free_parking_cash
            self.free_parking_cash = 0

    def calculate_rent(self, prop_state: PropertyState) -> int:
        info = prop_state.info
        base_rents = info.get("rent", [0])
        h = prop_state.houses
        if h >= 0 and h < len(base_rents):
            return base_rents[h]
        return base_rents[0]

    def transfer_cash(self, payer: Player, payee: Optional[Player], amount: int):
        if amount < 0:
            amount = -amount
        if payer.cash >= amount:
            payer.cash -= amount
            if payee:
                payee.cash += amount
            else:
                # bank collects (tax)
                self.free_parking_cash += 0  # can tweak house rules
        else:
            # try liquidate properties then bankruptcy
            needed = amount - payer.cash
            self.liquidate_for(payer, needed)
            if payer.cash >= amount:
                payer.cash -= amount
                if payee:
                    payee.cash += amount
            else:
                # bankruptcy
                self.declare_bankruptcy(payer, payee)

    def liquidate_for(self, player: Player, needed:int):
        # simple heuristic: mortgage most expensive unmortgaged properties first
        props = sorted([self.prop_states[i] for i in player.properties if not self.prop_states[i].mortgaged],
                       key=lambda x: x.info.get("cost",0), reverse=True)
        for ps in props:
            if player.cash >= needed:
                break
            # mortgage gives half cost
            ps.mortgaged = True
            player.cash += ps.info.get("cost",0)//2
        # sell houses if still needed
        if player.cash < needed:
            # sell houses one by one from most expensive color group
            owned = [self.prop_states[i] for i in player.properties if self.prop_states[i].houses>0]
            owned.sort(key=lambda x: x.info.get("house_cost",0), reverse=True)
            for ps in owned:
                if player.cash >= needed:
                    break
                # selling a house returns half house cost
                ps.houses -= 1
                player.cash += ps.info.get("house_cost",0)//2

    def declare_bankruptcy(self, player: Player, creditor: Optional[Player]):
        # transfer assets to creditor if any, else revert to bank
        player.bankrupt = True
        for idx in list(player.properties):
            ps = self.prop_states[idx]
            ps.owner = None if creditor is None else creditor.index
            if creditor:
                creditor.properties.append(idx)
        player.properties.clear()
        player.cash = 0

    # ---------- Actions: buy, auction, build, trade (simplified), end turn ----------
    def legal_actions(self, player: Player) -> List[Dict]:
        actions = []
        pos = player.position
        sq = BOARD[pos]
        if sq["type"] == "property" and pos in self.prop_states:
            ps = self.prop_states[pos]
            if ps.owner is None and player.cash >= ps.info["cost"]:
                actions.append({"action":"buy","property":pos})
        # build actions: if player has monopoly color and enough cash
        builds = self.possible_builds(player)
        for b in builds:
            actions.append({"action":"build","property":b})
        # mortgage / unmortgage removed as per request
        # trades: propose simple trade (offer cash for property)
        # propose trades include asking any opponent property that is un-mortgaged
        for opp in self.players:
            if opp.index==player.index or opp.bankrupt: continue
            for idx in opp.properties:
                if not self.prop_states[idx].mortgaged:
                    if player.cash>0:
                        # propose buy offer at 120% cost heuristic
                        actions.append({"action":"propose_trade","from":player.index,"to":opp.index,"property":idx,"offer":int(self.prop_states[idx].info.get("cost",0)*1.2)})
        # end turn
        actions.append({"action":"end_turn"})
        # if landed on unowned property but cannot afford, auction is possible by rules
        if sq["type"]=="property" and pos in self.prop_states and self.prop_states[pos].owner is None:
            actions.append({"action":"auction","property":pos})
        return actions

    def possible_builds(self, player: Player) -> List[int]:
        # build if player has monopoly on color and houses less than 5
        builds = []
        color_groups = defaultdict(list)
        for idx in player.properties:
            info = self.prop_states[idx].info
            if info["type"]=="property":
                color_groups[info["color"]].append(idx)
        for color, props in color_groups.items():
            # count total color size
            total = sum(1 for i,sq in enumerate(BOARD) if sq.get("color")==color)
            if len(props)==total:
                # can build evenly: choose property with minimal houses
                min_h = min(self.prop_states[i].houses for i in props)
                for i in props:
                    if self.prop_states[i].houses==min_h and self.prop_states[i].houses<5:
                        builds.append(i)
        return builds

    def execute_action(self, player: Player, action: Dict):
        a = action["action"]
        if a=="buy":
            idx = action["property"]
            ps = self.prop_states[idx]
            player.cash -= ps.info["cost"]
            ps.owner = player.index
            player.properties.append(idx)
        elif a=="auction":
            idx = action["property"]
            # simple auction: players bid in order random starting with current player
            highest = None
            highest_bid = 0
            order = [p for p in self.players if not p.bankrupt]
            start = order.index(player)
            order = order[start:]+order[:start]
            for bidder in order:
                # heuristic bid up to property cost
                maxbid = min(bidder.cash, ps_cost := self.prop_states[idx].info["cost"])
                bid = random.randint(0, maxbid)
                if bid>highest_bid:
                    highest_bid = bid
                    highest = bidder
            if highest and highest_bid>0:
                highest.cash -= highest_bid
                self.prop_states[idx].owner = highest.index
                highest.properties.append(idx)
        elif a=="build":
            idx = action["property"]
            ps = self.prop_states[idx]
            cost = ps.info["house_cost"]
            if player.cash >= cost:
                ps.houses += 1
                player.cash -= cost
        elif a=="mortgage":
            idx = action["property"]
            ps = self.prop_states[idx]
            if not ps.mortgaged:
                ps.mortgaged = True
                player.cash += ps.info.get("cost",0)//2
        elif a=="unmortgage":
            idx = action["property"]
            ps = self.prop_states[idx]
            cost = int(ps.info.get("cost",0)*0.55)
            if player.cash >= cost:
                ps.mortgaged = False
                player.cash -= cost
        elif a=="propose_trade":
            to = action["to"]
            prop = action["property"]
            offer = action["offer"]
            # auto accept heuristic: accept if offer >= cost*1.1 or cash needed
            opp = self.players[to]
            cost = self.prop_states[prop].info.get("cost",0)
            if offer >= cost*1.1 or opp.cash < 100:
                # transfer
                if self.players[action["from"]].cash >= offer:
                    self.players[action["from"]].cash -= offer
                    opp.cash += offer
                    opp.properties.remove(prop)
                    self.prop_states[prop].owner = action["from"]
                    self.players[action["from"]].properties.append(prop)
        elif a=="end_turn":
            pass

    # ---------- Turn progression ----------
    def play_single_turn(self):
        p = self.players[self.turn % len(self.players)]
        if p.bankrupt:
            self.turn += 1
            return
        if p.in_jail:
            # try to use card or pay or roll doubles within 3 tries
            if p.get_out_of_jail_free>0:
                p.get_out_of_jail_free -= 1
                p.in_jail = False
            elif p.cash >= 50:
                p.cash -= 50
                p.in_jail = False
            else:
                a,b = self.roll_dice()
                if a==b:
                    p.in_jail = False
                    self.move_player(p, a+b)
                    self.handle_landing(p, p.position)
                else:
                    p.jail_turns += 1
                    if p.jail_turns >= 3:
                        # forced to pay if can
                        if p.cash >= 50:
                            p.cash -= 50
                            p.in_jail = False
                            a,b = self.roll_dice()
                            self.move_player(p, a+b)
                            self.handle_landing(p, p.position)
                        else:
                            # try liquidation
                            self.liquidate_for(p, 50)
        else:
            a,b = self.roll_dice()
            self.move_player(p, a+b)
            self.handle_landing(p, p.position)
            # if landed on unowned property, basic policy: buy if affordable and good ROI
            pos = p.position
            if pos in self.prop_states and self.prop_states[pos].owner is None:
                # naive buy heuristic
                info = self.prop_states[pos].info
                if p.cash >= info.get("cost",0) and info.get("type")=="property":
                    if p.cash - info["cost"] >= 100 or info["cost"] <= 200:
                        # auto buy
                        self.execute_action(p, {"action":"buy","property":pos})
        self.turn += 1

    # ---------- Monte Carlo evaluator ----------
    def simulate_random_game(self, max_turns:int=200):
        # clone and play random playout to terminal or max_turns
        sim = self.clone()
        for _ in range(max_turns):
            active = sim.active_players()
            if len(active) <= 1:
                break
            sim.play_single_turn()
        # determine winner index with highest net worth
        scores = [(pl.net_worth(sim.prop_states), pl.index) for pl in sim.players if not pl.bankrupt]
        if not scores:
            return None
        return max(scores)[1]

    def simulate_action_choice(self, player_index:int, sims_per_action:int=100, future_turns:int=5) -> Tuple[Dict, Dict]:
        """
        Enumerate legal actions for player at their current state.
        For each action, run sims_per_action random playouts starting from the state after taking that action.
        Simulate future_turns additional turns, then score by net worth of player_index.
        Return best_action, stats dict mapping action->ave_net_worth
        """
        player = self.players[player_index]
        actions = self.legal_actions(player)
        if not actions:
            return {"action":"end_turn"}, {}
        stats = {}
        for action in actions:
            total_score = 0.0
            trials = sims_per_action
            for _ in range(trials):
                sim = self.clone()
                sim_player = sim.players[player_index]
                # execute action in sim
                sim.execute_action(sim_player, action)
                # simulate future turns
                for _ in range(future_turns):
                    if len(sim.active_players()) <= 1:
                        break
                    sim.play_single_turn()
                # score by net worth
                score = sim.players[player_index].net_worth(sim.prop_states)
                total_score += score
            avg_score = total_score / trials
            stats[self.action_repr(action)] = avg_score
        best = max(stats.items(), key=lambda x: x[1])
        # find action object matching repr
        best_action = None
        for a in actions:
            if self.action_repr(a)==best[0]:
                best_action = a
                break
        return best_action, stats

    def action_repr(self, action: Dict) -> str:
        a = action["action"]
        if a == "buy":
            prop_name = BOARD[action['property']]['name']
            return f"Buy {prop_name}"
        if a == "auction":
            prop_name = BOARD[action['property']]['name']
            return f"Auction {prop_name}"
        if a == "build":
            prop_name = BOARD[action['property']]['name']
            return f"Build house on {prop_name}"
        if a in ("mortgage", "unmortgage"):
            prop_name = BOARD[action['property']]['name']
            return f"{a.capitalize()} {prop_name}"
        if a == "propose_trade":
            prop_name = BOARD[action['property']]['name']
            opp_num = action['to'] + 1  # player numbers start at 1
            offer = action['offer']
            return f"Propose to buy {prop_name} from Player {opp_num} for £{offer}"
        if a == "end_turn":
            return "End turn"
        return a.upper()

# ---------- Interactive Game Functions ----------
def describe_state(game, player_index):
    p = game.players[player_index]
    print(f"\n--- State for {p.name} ---")
    print(f"Position: {p.position} ({BOARD[p.position]['name']})")
    print(f"Cash: £{p.cash}")
    print(f"In Jail: {'Yes' if p.in_jail else 'No'}")
    print(f"Get Out of Jail Free Cards: {p.get_out_of_jail_free}")
    print("Properties owned:")
    if not p.properties:
        print("  None")
    else:
            for i in p.properties:
                ps = game.prop_states[i]
                status = f"{ps.houses} houses"
                print(f"  - {BOARD[i]['name']}: {status}")
    print(f"Net Worth: £{p.net_worth(game.prop_states)}")

def suggest_move(game, player_index):
    best_action, stats = game.simulate_action_choice(player_index, sims_per_action=50)
    return best_action, stats

def interactive_game(player_names=["You", "AI1", "AI2"]):
    game = MonopolyGame(player_names)
    rounds = 0
    max_rounds = 500  # prevent infinite loop
    human_player = player_names[0] if player_names else "You"
    while len(game.active_players()) > 1 and rounds < max_rounds:
        cur_idx = game.turn % len(game.players)
        cur = game.players[cur_idx]
        if cur.bankrupt:
            game.turn += 1
            continue
        print(f"\nRound {rounds}, Turn {game.turn} - {cur.name}'s turn")
        # Roll dice and move
        a, b = game.roll_dice()
        print(f"Rolled {a} + {b} = {a+b}")
        game.move_player(cur, a + b)
        game.handle_landing(cur, cur.position)
        print(f"Landed on: {BOARD[cur.position]['name']}")
        if cur.name == human_player:
            # Human player interactive
            describe_state(game, cur_idx)
            best_action, stats = suggest_move(game, cur_idx)
            print(f"Suggested move: {game.action_repr(best_action)} (win rate {stats.get(game.action_repr(best_action), 0):.2f} if stats else '')")
            actions = game.legal_actions(cur)
            print("Legal actions:")
            for i, act in enumerate(actions):
                print(f"{i}: {game.action_repr(act)}")
            while True:
                try:
                    choice = int(input("Choose action number: "))
                    if 0 <= choice < len(actions):
                        selected_action = actions[choice]
                        game.execute_action(cur, selected_action)
                        print(f"Executed: {game.action_repr(selected_action)}")
                        break
                    else:
                        print("Invalid choice.")
                except ValueError:
                    print("Please enter a number.")
        else:
            # AI player
            best_action, stats = game.simulate_action_choice(cur_idx, sims_per_action=50)
            game.execute_action(cur, best_action)
            print(f"AI chose: {game.action_repr(best_action)}")
        game.turn += 1
        rounds += 1
    winners = game.active_players()
    if winners:
        print(f"\nGame ended. Winner(s): {', '.join(w.name for w in winners)}")
    else:
        print("\nGame ended. No winners.")

# ---------- Demo / CLI ----------
def demo():
    names = ["AI","Bob","Carol","Dave"]
    game = MonopolyGame(names)
    rounds = 0
    SIM_PLAYOUTS = 80  # adjust higher for stronger decisions
    while rounds < 200 and len(game.active_players())>1:
        cur_idx = game.turn % len(game.players)
        cur = game.players[cur_idx]
        if cur.bankrupt:
            game.turn += 1
            continue
        if cur.name=="AI":
            # get best action by Monte Carlo
            best, stats = game.simulate_action_choice(cur_idx, sims_per_action=SIM_PLAYOUTS)
            print(f"\nTurn {game.turn} - {cur.name} at pos {cur.position} cash ${cur.cash}")
            print("Action stats (win rates):")
            for k,v in stats.items():
                print(f"  {k}: {v:.2f}")
            print("Chosen:", best)
            game.execute_action(cur, best)
            # then finish turn normally (move etc.)
            game.play_single_turn()
        else:
            # simple autoplayer
            game.play_single_turn()
        rounds += 1

    winners = [p for p in game.players if not p.bankrupt]
    if winners:
        print("Winner(s):", ", ".join(w.name for w in winners))
    else:
        print("No winners. All bankrupt.")


def print_board_layout():
    # Simple ASCII representation of the Monopoly board
    # Top row: GO to Free Parking (positions 0-19)
    top = [f"{i}:{sq['name']}" for i, sq in enumerate(BOARD[:20])]
    top_row = " | ".join(top[:11])  # GO to Whitechapel (0-10), but adjust for length
    # Actually, better to do a grid

    # Create a list of square names
    squares = [sq['name'] for sq in BOARD]

    # Define the layout positions
    # Top: 20 to 30 (reverse order, but adjusted)
    # Actually, standard monopoly board in ASCII is like:


    # Too complicated. Perhaps just list columns or something.

    # Print the squares in order around the board
    print("\nMonopoly Board Layout (clockwise from GO):")
    sides = [
        BOARD[:11],  # GO to JAIL
        BOARD[11:21], # PALL MALL to FREE PARKING
        BOARD[21:31], # STRAND to JAIL
        BOARD[31:40]  # REGENT ST to MAYFAIR
    ]
    for side_name, side in zip(["Bottom", "Right", "Top", "Left"], sides):
        print(f"{side_name}: {' | '.join([f'{i}:{sq['name']}' for i, sq in enumerate(side if side_name != 'Top' else side[::-1])])}")
    print()

def advisor():
    print("Monopoly Move Advisor - Enter current game state.")

    # Show board key
    print("\nBoard Key (positions 0-39):")
    for i, sq in enumerate(BOARD):
        print(f"{i:2}: {sq['name']}")

    # Number of players and user index
    num_players = int(input("\nPlayers? "))
    user_index = int(input("Your player # (1-N)? ")) - 1

    player_names = [f"P{i+1}" for i in range(num_players)]

    # Create game
    game = MonopolyGame(player_names)
    game.turn = user_index

    # Positions: comma-separated
    print("\nPositions (0-39, comma-separated for each player):")
    poses = input().split(',')
    for i in range(num_players):
        game.players[i].position = int(poses[i].strip()) if i < len(poses) else 0

    # Cash: comma-separated
    print("Cash (£, comma-separated):")
    cashes = input().split(',')
    for i in range(num_players):
        game.players[i].cash = int(cashes[i].strip()) if i < len(cashes) else 1500

    # Properties: for each player, comma-separated indices
    print("\nProperties owned (player1 indices, then player2, etc. Use 0 or blank for none):")
    for i in range(num_players):
        props_str = input(f"P{i+1}: ")
        if props_str.strip():
            props = [int(x.strip()) for x in props_str.split(',') if x.strip()]
            valid_props = []
            for p_idx in props:
                if p_idx in game.prop_states:
                    valid_props.append(p_idx)
                    game.prop_states[p_idx].owner = i
                else:
                    print(f"Skip invalid {p_idx}")
            game.players[i].properties = valid_props

    # Houses: for each owned property, comma-separated counts (assume order of ownership or by index?)
    # To make fast: list all owned properties with indices, input counts in order
    all_owned = [(sq_idx, prop_info.owner) for sq_idx, prop_info in game.prop_states.items() if prop_info.owner is not None]
    if all_owned:
        print("Houses (comma-separated counts for owned properties, 0-5):")
        owned_indices = [sq_idx for sq_idx, owner in all_owned]
        print("For properties:", owned_indices)
        houses_str = input().split(',')
        for j, (sq_idx, owner) in enumerate(all_owned):
            if j < len(houses_str):
                game.prop_states[sq_idx].houses = int(houses_str[j].strip()) % 6  # 0-5

    # Jail: for each player, y/n turns
    print("Jail (comma-separated: y/n/t or blank for none):")
    jails = input().split(',')
    for i in range(num_players):
        if i < len(jails):
            j_data = jails[i].strip().split('/')
            if len(j_data) >= 1 and j_data[0].lower().startswith('y'):
                game.players[i].in_jail = True
                if len(j_data) > 1:
                    game.players[i].jail_turns = int(j_data[1])
                else:
                    game.players[i].jail_turns = 1

    # Get out of jail cards: comma-separated numbers
    print("GOOJF cards (comma-separated):")
    gooifs = input().split(',')
    for i in range(num_players):
        if i < len(gooifs):
            game.players[i].get_out_of_jail_free = int(gooifs[i].strip()) if gooifs[i].strip() else 0

    # Free parking
    free_parking = int(input("Free Parking cash (£): ") or "0")
    game.free_parking_cash = free_parking

    # Calculate
    print(f"\nCalculating for {game.players[user_index].name}...")
    best_action, stats = game.simulate_action_choice(user_index, 100, future_turns=5)

    print("Best:", game.action_repr(best_action))
    print("Ave Net Worth after 5 turns:")
    for a, r in sorted(stats.items(), key=lambda x: x[1], reverse=True):
        print(f"{a}: £{r:.0f}")


def gui_advisor():
    root = tk.Tk()
    root.title("Monopoly Move Advisor Dashboard")
    root.attributes('-fullscreen', True)  # Full screen

    # Main frame
    main_frame = ttk.Frame(root)
    main_frame.pack(fill='both', expand=True)

    # Top frame for player setup
    players_frame = ttk.Frame(main_frame)
    players_frame.pack(side='top', fill='both', expand=True)

    # Number of players
    players_label = ttk.Label(main_frame, text="Number of Players:", font=('Arial', 14))
    players_label.pack(anchor='nw', padx=10, pady=5)
    players_var = tk.IntVar(value=2)
    players_spin = ttk.Spinbox(main_frame, from_=2, to=4, textvariable=players_var, font=('Arial', 12))
    players_spin.pack(anchor='nw', padx=10)

    # Property indices
    prop_indices = [i for i, sq in enumerate(BOARD) if sq["type"] in ("property", "railroad", "utility")]
    prop_names = [f"{i}: {BOARD[i]['name']}" for i in prop_indices]

    player_frames = []
    position_vars = []
    cash_vars = []
    property_selects = []
    house_spinboxes = []

    def update_players():
        num_p = players_var.get()
        # Clear existing
        for frame in player_frames:
            frame.pack_forget()
        player_frames.clear()
        position_vars.clear()
        cash_vars.clear()
        property_selects.clear()
        house_spinboxes.clear()

        # Arrange in grid, 2 per row
        for i in range(num_p):
            frame = ttk.Frame(players_frame, borderwidth=2, relief='groove')
            frame.grid(row=i//2, column=i%2, padx=5, pady=5, sticky='nsew')
            ttk.Label(frame, text=f"Player {i+1}", font=('Arial', 16)).grid(row=0, column=0, columnspan=2, pady=5)

            ttk.Label(frame, text="Position (0-39):", font=('Arial', 10)).grid(row=1, column=0, sticky='w')
            pos_var = tk.StringVar(value="0")
            pos_combo = ttk.Combobox(frame, textvariable=pos_var, values=[f"{j}: {BOARD[j]['name']}" for j in range(40)], state="readonly", width=30)
            pos_combo.grid(row=1, column=1, pady=2)
            position_vars.append(pos_var)

            ttk.Label(frame, text="Cash (£):", font=('Arial', 10)).grid(row=2, column=0, sticky='w')
            cash_var = tk.IntVar(value=1500)
            cash_entry = ttk.Entry(frame, textvariable=cash_var, width=10)
            cash_entry.grid(row=2, column=1, pady=2)
            cash_vars.append(cash_var)

            ttk.Label(frame, text="Owned Properties:", font=('Arial', 10)).grid(row=3, column=0, sticky='w')
            # Scrollable frame for checkboxes
            checkbox_frame = tk.Frame(frame, height=150, width=300)
            canvas = tk.Canvas(checkbox_frame, width=300, height=150)
            v_scroll = ttk.Scrollbar(checkbox_frame, orient=tk.VERTICAL, command=canvas.yview)
            canvas.config(yscrollcommand=v_scroll.set)
            canvas.pack(side=tk.LEFT, fill='both', expand=True)
            v_scroll.pack(side=tk.RIGHT, fill='y')
            inner_frame = tk.Frame(canvas)
            canvas.create_window((0,0), window=inner_frame, anchor='nw')

            prop_vars = []
            for name in prop_names:
                var = tk.BooleanVar()
                chk = ttk.Checkbutton(inner_frame, text=name, variable=var)
                chk.pack(anchor='w')
                prop_vars.append(var)
            checkbox_frame.grid(row=3, column=1, pady=2)
            property_selects.append(prop_vars)
            # Update scroll region
            inner_frame.update_idletasks()
            canvas.config(scrollregion=canvas.bbox("all"))

            ttk.Label(frame, text="Houses (comma sep for owned):", font=('Arial', 10)).grid(row=4, column=0, sticky='w')
            house_var = tk.StringVar(value="")
            house_entry = ttk.Entry(frame, textvariable=house_var, width=30)
            house_entry.grid(row=4, column=1, pady=2)
            house_spinboxes.append(house_var)

            player_frames.append(frame)

    players_spin.config(command=lambda: update_players())
    update_players()

    # Bottom frame for advice
    bottom_frame = ttk.Frame(main_frame)
    bottom_frame.pack(side='bottom', fill='x', pady=10)

    advice_text = tk.Text(bottom_frame, height=10, wrap=tk.WORD, font=('Arial', 12))
    advice_text.pack(fill='both', expand=True, padx=10)

    def start_calc():
        num_players = players_var.get()

        player_names = [f"P{i+1}" for i in range(num_players)]
        game = MonopolyGame(player_names)
        game.turn = 0  # Assuming player 1 is P1

        # Set positions
        for i in range(num_players):
            pos_str = position_vars[i].get()
            pos = int(pos_str.split(':')[0])
            game.players[i].position = pos

        # Set cash
        for i in range(num_players):
            cash = cash_vars[i].get()
            game.players[i].cash = cash

        # Set properties and houses
        for p_idx in range(num_players):
            selected_indices = [i for i, var in enumerate(property_selects[p_idx]) if var.get()]
            props = [prop_indices[idx] for idx in selected_indices]
            game.players[p_idx].properties = props
            for prop in props:
                game.prop_states[prop].owner = p_idx

            house_str = house_spinboxes[p_idx].get().strip()
            if house_str:
                houses = [int(x.strip()) for x in house_str.split(',')]
                for idx, prop in enumerate(props):
                    if idx < len(houses):
                        game.prop_states[prop].houses = houses[idx]

        # Calculate for Player 1
        advice_text.delete(1.0, tk.END)
        advice_text.insert(tk.END, "Calculating...")
        calculate_thread = threading.Thread(target=run_calc, args=(game,))
        calculate_thread.start()

    def run_calc(game):
        best_action, stats = game.simulate_action_choice(0, 100, future_turns=5)  # Player 1
        result = f"Best Move for Player 1: {game.action_repr(best_action)}\n\nAverage Net Worth after 5 turns:\n"
        for a, r in sorted(stats.items(), key=lambda x: x[1], reverse=True):
            result += f"{a}: £{r:.0f}\n"
        advice_text.delete(1.0, tk.END)
        advice_text.insert(tk.END, result)

    calc_button = tk.Button(bottom_frame, text="Calculate Best Move for Player 1", command=start_calc, font=('Arial', 14))
    calc_button.pack(pady=5)

    root.mainloop()

if __name__ == "__main__":
    gui_advisor()
