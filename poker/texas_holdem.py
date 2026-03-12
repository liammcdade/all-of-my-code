import random
import threading
import tkinter as tk
from tkinter import ttk
import math
from texasholdem import TexasHoldEm, ActionType, Card, HandPhase, PlayerState
from texasholdem.evaluator import evaluate

# ---------- CONSTANTS ----------
WINDOW_WIDTH = 1100
WINDOW_HEIGHT = 760
TABLE_WIDTH = 800
TABLE_HEIGHT = 450
CARD_WIDTH = 55
CARD_HEIGHT = 80

SUIT_COLORS = {'h': '#ff1744', 'd': '#2979ff', 's': '#212121', 'c': '#00c853'}
SUIT_SYMBOLS = {'h': '♥', 'd': '♦', 's': '♠', 'c': '♣'}

# AI Constants
SIM_COUNT = 300
DEFAULT_SIMS = 600
RAISE_THRESHOLD = 0.75
PHASE_MULTIPLIERS = {
    HandPhase.PREFLOP: 0.85,
    HandPhase.FLOP: 1.0,
    HandPhase.TURN: 1.1,
    HandPhase.RIVER: 1.25
}
BIG_BLIND_RAISE_MULT = 3
POT_RAISE_DIV = 2
TIE_MULTIPLIER = 0.5

# GUI Delays
INITIAL_DELAY = 1000
NEW_HAND_DELAY = 1000
AI_DECIDE_DELAY = 400
STEP_DELAY = 900
WINNERS_DELAY = 2500


class MyTexasHoldEm(TexasHoldEm):
    def total_pot(self):
        return sum(p.amount + sum(p.player_amounts.values()) for p in self.pots)


# ---------- AI ----------
class PokerAI:
    def __init__(self, player_id):
        self.player_id = player_id

    def calculate_win_probability(self, game, sims=DEFAULT_SIMS):
        if self.player_id not in game.hands:
            return 0.0

        my_cards = game.hands[self.player_id]
        board = game.board[:]

        opponents = [
            p.player_id for p in game.players
            if p.player_id != self.player_id
            and p.state in (PlayerState.IN, PlayerState.TO_CALL, PlayerState.ALL_IN)
        ]

        if not opponents:
            return 1.0

        wins = 0
        ties = 0

        all_cards = [Card(r+s) for r in "23456789TJQKA" for s in "shdc"]
        known = my_cards + board
        deck = [c for c in all_cards if c not in known]

        for _ in range(sims):
            random.shuffle(deck)

            sim_board = board + deck[:5-len(board)]
            idx = 5 - len(board)

            my_score = evaluate(my_cards, sim_board)
            best_opp = float("inf")

            for _ in opponents:
                opp_cards = [deck[idx], deck[idx+1]]
                idx += 2
                opp_score = evaluate(opp_cards, sim_board)
                best_opp = min(best_opp, opp_score)

            if my_score < best_opp:
                wins += 1
            elif my_score == best_opp:
                ties += 1

        return (wins + ties * TIE_MULTIPLIER) / sims

    def decide_action(self, game):
        win_prob = self.calculate_win_probability(game)
        to_call = game.chips_to_call(self.player_id)
        pot = game.total_pot()

        pot_odds = to_call / (pot + to_call) if to_call > 0 else 0

        phase_mult = PHASE_MULTIPLIERS[game.hand_phase]

        adjusted = win_prob * phase_mult

        if adjusted > RAISE_THRESHOLD:
            raise_amt = min(
                game.players[self.player_id].chips,
                max(game.big_blind * BIG_BLIND_RAISE_MULT, pot // POT_RAISE_DIV)
            )
            if raise_amt >= game.players[self.player_id].chips:
                return ActionType.ALL_IN, None
            return ActionType.RAISE, raise_amt

        if adjusted > pot_odds:
            return ActionType.CALL, None

        if to_call == 0:
            return ActionType.CHECK, None

        return ActionType.FOLD, None


# ---------- GUI ----------
class PokerGUI:
    def __init__(self, root):
        self.root = root
        self.root.title("Antigravity Poker")
        self.root.geometry(f"{WINDOW_WIDTH}x{WINDOW_HEIGHT}")
        self.root.configure(bg="#121212")

        self.game = MyTexasHoldEm(buyin=1000, big_blind=20, small_blind=10, max_players=6)
        self.ais = {i: PokerAI(i) for i in range(6)}
        self.wins = {i: 0 for i in range(6)}
        self.total_hands = 0
        self.lock = threading.Lock()
        self.paused = True

        self.setup_styles()
        self.create_widgets()

        self.root.after(INITIAL_DELAY, self.toggle_pause)

    # ---------- HELPERS ----------

    # ---------- UI ----------
    def setup_styles(self):
        style = ttk.Style()
        style.theme_use("clam")
        style.configure("TButton", background="#333", foreground="white")

    def create_widgets(self):
        tk.Label(self.root, text="TEXAS HOLD'EM SIMULATOR",
                 font=("Arial", 24, "bold"),
                 bg="#121212", fg="#00e5ff").pack(pady=10)

        self.main = tk.Frame(self.root, bg="#121212")
        self.main.pack(fill="both", expand=True)

        self.canvas = tk.Canvas(self.main, width=TABLE_WIDTH+100,
                                height=TABLE_HEIGHT+240,
                                bg="#121212", highlightthickness=0)
        self.canvas.pack(side="left", padx=20)

        self.side = tk.Frame(self.main, bg="#1a1a1a", width=260)
        self.side.pack(side="right", fill="y", padx=20, pady=20)

        tk.Label(self.side, text="ACTION LOG", bg="#1a1a1a",
                 fg="#bbb", font=("Arial", 10, "bold")).pack(pady=5)

        self.log_box = tk.Text(self.side, bg="#000", fg="#0f0",
                               font=("Consolas", 9), height=28, width=30)
        self.log_box.pack(padx=10)

        controls = tk.Frame(self.side, bg="#1a1a1a")
        controls.pack(pady=20)

        self.pause_btn = ttk.Button(controls, text="RESUME", command=self.toggle_pause)
        self.pause_btn.pack(side="left", padx=5)

        ttk.Button(controls, text="RESET", command=self.reset_game).pack(side="left", padx=5)

    # ---------- DRAWING ----------
    def draw_game(self):
        self.canvas.delete("all")

        cx = (TABLE_WIDTH + 100) // 2
        cy = (TABLE_HEIGHT + 240) // 2 - 20

        self.canvas.create_oval(cx-TABLE_WIDTH//2, cy-TABLE_HEIGHT//2,
                                cx+TABLE_WIDTH//2, cy+TABLE_HEIGHT//2,
                                fill="#0d47a1", outline="#00e5ff", width=4)

        self.canvas.create_text(cx, cy-55, text=f"POT: ${self.game.total_pot()}",
                                fill="#ffd600", font=("Arial", 16, "bold"))
        self.canvas.create_text(cx, cy-80, text=self.game.hand_phase.name,
                                fill="#00e5ff", font=("Arial", 12))

        bx = cx - ((len(self.game.board) * (CARD_WIDTH + 10)) - 10) / 2
        for i, card in enumerate(self.game.board):
            self.draw_card(bx + i*(CARD_WIDTH+10), cy+10, card)

        for pid in range(6):
            angle = (pid*60 - 90) * math.pi/180
            px = cx + (TABLE_WIDTH//2+60)*math.cos(angle)
            py = cy + (TABLE_HEIGHT//2+40)*math.sin(angle)
            self.draw_player(pid, px, py)

        self.draw_probabilities()

    def draw_probabilities(self):
        x = 80
        y = TABLE_HEIGHT + 140
        width = 880

        self.canvas.create_text(x, y-25, text="TOURNAMENT WIN PERCENTAGE",
                                fill="#00e5ff", font=("Arial", 11, "bold"),
                                anchor="w")

        for pid in range(6):
            prob = self.wins[pid] / self.total_hands if self.total_hands > 0 else 0
            bar = int(width * prob)

            self.canvas.create_rectangle(x, y+pid*18,
                                          x+bar, y+pid*18+12,
                                          fill="#ffd600", outline="")
            self.canvas.create_text(x+width+10, y+pid*18+6,
                                    text=f"P{pid}: {prob:.1%}",
                                    fill="white", anchor="w", font=("Arial", 9))

    def draw_card(self, x, y, card):
        self.canvas.create_rectangle(x-CARD_WIDTH//2, y-CARD_HEIGHT//2,
                                     x+CARD_WIDTH//2, y+CARD_HEIGHT//2,
                                     fill="white", outline="#ccc")
        rank = str(card)[0]
        if rank == "T":
            rank = "10"
        suit = str(card)[1]

        self.canvas.create_text(x, y-15, text=rank,
                                fill=SUIT_COLORS[suit], font=("Arial", 14, "bold"))
        self.canvas.create_text(x, y+12, text=SUIT_SYMBOLS[suit],
                                fill=SUIT_COLORS[suit], font=("Arial", 24))

    def draw_player(self, pid, x, y):
        p = self.game.players[pid]
        active = p.state in (PlayerState.IN, PlayerState.TO_CALL, PlayerState.ALL_IN)
        outline = "#00e5ff" if pid == self.game.current_player else "#555"

        self.canvas.create_rectangle(x-60, y-50, x+60, y+50,
                                     fill="#333" if active else "#111",
                                     outline=outline, width=2)

        self.canvas.create_text(x, y-35, text=f"P{pid}",
                                fill="white", font=("Arial", 10, "bold"))
        self.canvas.create_text(x, y-18, text=f"${p.chips}",
                                fill="#ffd600", font=("Arial", 9))
        self.canvas.create_text(x, y+38, text=p.state.name,
                                fill="#bbb", font=("Arial", 8))

        if pid in self.game.hands and active:
            h = self.game.hands[pid]
            self.draw_card(x-18, y+10, h[0])
            self.draw_card(x+18, y+10, h[1])

    # ---------- LOGIC ----------
    def log(self, msg):
        self.log_box.insert(tk.END, msg+"\n")
        self.log_box.see(tk.END)

    def toggle_pause(self):
        self.paused = not self.paused
        self.pause_btn.config(text="PAUSE" if not self.paused else "RESUME")
        if not self.paused:
            self.step()

    def reset_game(self):
        self.game = MyTexasHoldEm(buyin=1000, big_blind=20, small_blind=10, max_players=6)
        self.wins = {i: 0 for i in range(6)}
        self.total_hands = 0
        self.log("\n--- NEW GAME ---")
        self.draw_game()


    def step(self):
        if self.paused:
            return

        if not self.game.is_hand_running():
            self.game.start_hand()
            print("Starting new hand")
            self.log("\n--- NEW HAND ---")
            self.draw_game()
            self.root.after(NEW_HAND_DELAY, self.step)
            return

        pid = self.game.current_player
        print(f"Player {pid} is deciding action")
        ai = self.ais[pid]

        def ai_worker():
            action, amt = ai.decide_action(self.game)
            self.root.after(AI_DECIDE_DELAY, lambda: self.apply_action(pid, action, amt))

        threading.Thread(target=ai_worker, daemon=True).start()

    def apply_action(self, pid, action, amount):
        try:
            to_call = self.game.chips_to_call(pid)
            if action == ActionType.RAISE:
                min_raise = self.game.min_raise()
                amount = max(amount, to_call + min_raise)
                total_bet = self.game.players[pid].amount + amount
                self.game.take_action(action, total=total_bet)
            elif action == ActionType.ALL_IN:
                self.game.take_action(action)
            else:
                self.game.take_action(action, value=amount)
            print(f"Player {pid} took {action.name} {'$' + str(amount) if amount else ''}")
            self.log(f"P{pid}: {action.name} {'' if amount is None else '$'+str(amount)}")

        except ValueError as e:
            print(f"Action error for Player {pid}: {e}")
            self.log(f"Action error for P{pid}: {e}")
            try:
                self.game.take_action(ActionType.FOLD)
            except ValueError:
                pass  # If fold fails, ignore

        self.draw_game()

        if self.game.is_hand_running():
            self.root.after(STEP_DELAY, self.step)
        else:
            winners = [p.player_id for p in self.game.players if p.last_pot > 0]
            for pid in winners:
                self.wins[pid] += 1
            self.total_hands += 1
            print(f"Winners: {winners}")
            self.log(f"WINNERS: {winners}")
            self.root.after(WINNERS_DELAY, self.step)


# ---------- MAIN ----------
if __name__ == "__main__":
    root = tk.Tk()
    PokerGUI(root)
    root.mainloop()
