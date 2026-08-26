import random
import threading
import tkinter as tk
from tkinter import ttk
import math
from texasholdem import TexasHoldEm, ActionType, Card, HandPhase, PlayerState
from texasholdem.evaluator import evaluate, rank_to_string

# ---------- CONSTANTS ----------
WINDOW_WIDTH = 1100
WINDOW_HEIGHT = 760
TABLE_WIDTH = 800
TABLE_HEIGHT = 450
CARD_WIDTH = 55
CARD_HEIGHT = 80

SUIT_COLORS = {'h': '#ff1744', 'd': '#2979ff', 's': '#ffffff', 'c': '#00e676'}
SUIT_SYMBOLS = {'h': '♥', 'd': '♦', 's': '♠', 'c': '♣'}

# Precompute deck for O(1) Monte Carlo lookups
ALL_CARDS = [Card(r + s) for r in "23456789TJQKA" for s in "shdc"]

# AI Constants
DEFAULT_SIMS = 600
PHASE_MULTIPLIERS = {
    HandPhase.PREFLOP: 0.9,
    HandPhase.FLOP: 1.0,
    HandPhase.TURN: 1.15,
    HandPhase.RIVER: 1.3
}

# GUI Delays (ms)
INITIAL_DELAY = 800
NEW_HAND_DELAY = 1200
AI_DECIDE_DELAY = 300
WINNERS_DELAY = 2500


class MyTexasHoldEm(TexasHoldEm):
    def get_total_pot(self):
        """Accurately sums all main and side pots."""
        return sum(pot.get_total_amount() for pot in self.pots)


class PokerAI:
    def __init__(self, player_id):
        self.player_id = player_id
        self.aggression_factor = random.uniform(0.9, 1.15)
        self.last_win_prob = 0.0

    def calculate_win_probability(self, game, sims=DEFAULT_SIMS):
        if self.player_id not in game.hands or not game.hands[self.player_id]:
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

        known_set = set(my_cards + board)
        deck = [c for c in ALL_CARDS if c not in known_set]
        
        cards_needed = 5 - len(board)
        total_cards_needed = cards_needed + len(opponents) * 2
        
        if len(deck) < total_cards_needed:
            return self.last_win_prob

        for _ in range(sims):
            random.shuffle(deck)
            
            sim_board = board + deck[:cards_needed]
            my_score = evaluate(my_cards, sim_board)
            best_opp = 10000 

            idx = cards_needed
            for _ in opponents:
                opp_cards = [deck[idx], deck[idx+1]]
                idx += 2
                opp_score = evaluate(opp_cards, sim_board)
                if opp_score < best_opp:
                    best_opp = opp_score

            if my_score < best_opp:
                wins += 1
            elif my_score == best_opp:
                ties += 1

        return (wins + ties * 0.5) / sims

    def decide_action(self, game):
        self.last_win_prob = self.calculate_win_probability(game)
        to_call = game.chips_to_call(self.player_id)
        pot = game.get_total_pot()
        player_chips = game.players[self.player_id].chips

        pot_odds = to_call / (pot + to_call) if (pot + to_call) > 0 else 0
        spr = player_chips / (pot + 1)
        spr_mult = 1.0 + (0.15 if spr < 3 else -0.1 if spr > 10 else 0.0)

        phase_mult = PHASE_MULTIPLIERS.get(game.hand_phase, 1.0)
        adjusted = self.last_win_prob * phase_mult * spr_mult * self.aggression_factor

        if to_call == 0:
            if adjusted > 0.65:
                raise_amt = int(min(player_chips, max(game.big_blind * 2, pot // 2)))
                return (ActionType.ALL_IN, None) if raise_amt >= player_chips else (ActionType.RAISE, raise_amt)
            return ActionType.CHECK, None

        if adjusted > pot_odds + 0.08:
            if adjusted > 0.75:
                raise_amt = int(min(player_chips, max(game.big_blind * 3, pot // 2 + to_call)))
                return (ActionType.ALL_IN, None) if raise_amt >= player_chips else (ActionType.RAISE, raise_amt)
            return ActionType.CALL, None
        
        if adjusted > pot_odds - 0.1 and random.random() < 0.04:
            return ActionType.CALL, None

        return ActionType.FOLD, None


class PokerGUI:
    def __init__(self, root):
        self.root = root
        self.root.title("Antigravity Poker AI Simulator")
        self.root.geometry(f"{WINDOW_WIDTH}x{WINDOW_HEIGHT}")
        self.root.configure(bg="#121212")

        self.game = MyTexasHoldEm(buyin=1000, big_blind=20, small_blind=10, max_players=6)
        self.ais = {i: PokerAI(i) for i in range(6)}
        self.wins = {i: 0 for i in range(6)}
        self.total_hands = 0
        self.paused = True
        self.showdown_mode = False # To reveal cards at the end

        self.setup_styles()
        self.create_widgets()
        self.root.after(INITIAL_DELAY, self.toggle_pause)

    def setup_styles(self):
        style = ttk.Style()
        style.theme_use("clam")
        style.configure("TButton", background="#333", foreground="white", borderwidth=0)
        style.map("TButton", background=[("active", "#00e5ff")])

    def create_widgets(self):
        tk.Label(self.root, text="TEXAS HOLD'EM AI SIMULATOR",
                 font=("Segoe UI", 22, "bold"), bg="#121212", fg="#00e5ff").pack(pady=10)

        self.main = tk.Frame(self.root, bg="#121212")
        self.main.pack(fill="both", expand=True)

        self.canvas = tk.Canvas(self.main, width=TABLE_WIDTH + 100,
                                height=TABLE_HEIGHT + 240,
                                bg="#121212", highlightthickness=0)
        self.canvas.pack(side="left", padx=20)

        self.side = tk.Frame(self.main, bg="#1a1a1a", width=280)
        self.side.pack(side="right", fill="y", padx=20, pady=20)

        tk.Label(self.side, text="ACTION LOG", bg="#1a1a1a",
                 fg="#bbb", font=("Segoe UI", 10, "bold")).pack(pady=5)

        self.log_box = tk.Text(self.side, bg="#000", fg="#00e676",
                               font=("Consolas", 9), height=24, width=32,
                               borderwidth=1, relief="solid")
        self.log_box.pack(padx=10)

        controls = tk.Frame(self.side, bg="#1a1a1a")
        controls.pack(pady=15)

        self.pause_btn = ttk.Button(controls, text="RESUME", command=self.toggle_pause)
        self.pause_btn.pack(side="left", padx=5)
        ttk.Button(controls, text="RESET", command=self.reset_game).pack(side="left", padx=5)

        tk.Label(self.side, text="SIM SPEED (ms)", bg="#1a1a1a", fg="#bbb", font=("Segoe UI", 9)).pack(pady=(15, 0))
        self.speed_var = tk.IntVar(value=400)
        tk.Scale(self.side, from_=50, to=1500, orient="horizontal", 
                 variable=self.speed_var, bg="#1a1a1a", fg="white", 
                 highlightthickness=0, troughcolor="#333").pack(fill="x", padx=20)

    def draw_game(self):
        self.canvas.delete("all")
        cx = (TABLE_WIDTH + 100) // 2
        cy = (TABLE_HEIGHT + 240) // 2 - 20

        self.canvas.create_oval(cx - TABLE_WIDTH//2, cy - TABLE_HEIGHT//2,
                                cx + TABLE_WIDTH//2, cy + TABLE_HEIGHT//2,
                                fill="#0d47a1", outline="#00e5ff", width=4)

        self.canvas.create_text(cx, cy - 85, text=self.game.hand_phase.name,
                                fill="#00e5ff", font=("Segoe UI", 14, "bold"))
        self.canvas.create_text(cx, cy - 55, text=f"POT: ${self.game.get_total_pot()}",
                                fill="#ffd600", font=("Segoe UI", 18, "bold"))

        bx = cx - ((len(self.game.board) * (CARD_WIDTH + 10)) - 10) / 2
        for i, card in enumerate(self.game.board):
            self.draw_card(bx + i * (CARD_WIDTH + 10), cy + 10, card, face_up=True)

        for pid in range(self.game.max_players):
            angle = (pid * 60 - 90) * math.pi / 180
            px = cx + (TABLE_WIDTH//2 + 70) * math.cos(angle)
            py = cy + (TABLE_HEIGHT//2 + 50) * math.sin(angle)
            self.draw_player(pid, px, py)

        self.draw_probabilities()

    def draw_probabilities(self):
        x, y, width = 40, TABLE_HEIGHT + 100, 400
        self.canvas.create_text(x, y - 25, text="TOURNAMENT WIN RATE",
                                fill="#00e5ff", font=("Segoe UI", 11, "bold"), anchor="w")

        for pid in range(self.game.max_players):
            prob = self.wins[pid] / self.total_hands if self.total_hands > 0 else 0
            bar = int(width * prob)
            
            self.canvas.create_rectangle(x, y + pid * 22, x + width, y + pid * 22 + 16,
                                         fill="#222", outline="#444")
            self.canvas.create_rectangle(x, y + pid * 22, x + bar, y + pid * 22 + 16,
                                         fill="#00e5ff", outline="")
            self.canvas.create_text(x + width + 15, y + pid * 22 + 8,
                                    text=f"P{pid}: {prob:.1%} ({self.wins[pid]} wins)",
                                    fill="#ccc", anchor="w", font=("Segoe UI", 9))
            
        if self.game.is_hand_running():
            cpid = self.game.current_player
            ai_prob = self.ais[cpid].last_win_prob
            self.canvas.create_text(x, y + 140, 
                                    text=f"▶ AI P{cpid} Est. Win Probability: {ai_prob:.1%}",
                                    fill="#ffd600", font=("Segoe UI", 11, "bold"), anchor="w")

    def draw_card(self, x, y, card, face_up=True):
        w, h = CARD_WIDTH, CARD_HEIGHT
        self.canvas.create_rectangle(x - w//2, y - h//2, x + w//2, y + h//2,
                                     fill="white" if face_up else "#1a1a1a", 
                                     outline="#888", width=1)
        if not face_up:
            self.canvas.create_rectangle(x - w//2 + 4, y - h//2 + 4, x + w//2 - 4, y + h//2 - 4,
                                         fill="#0d47a1", outline="#00e5ff", width=1)
            for i in range(-w//2 + 8, w//2 - 4, 8):
                self.canvas.create_line(x + i, y - h//2 + 8, x + i + 8, y + h//2 - 8, fill="#1565c0", width=2)
            return

        rank = str(card)[0]
        rank = "10" if rank == "T" else rank
        suit = str(card)[1]
        color = SUIT_COLORS[suit]
        symbol = SUIT_SYMBOLS[suit]

        self.canvas.create_text(x - w//2 + 12, y - h//2 + 14, 
                                text=rank, fill=color, font=("Arial", 10, "bold"), anchor="center")
        self.canvas.create_text(x - w//2 + 12, y - h//2 + 28, 
                                text=symbol, fill=color, font=("Arial", 14), anchor="center")
        self.canvas.create_text(x, y + 4, text=symbol, fill=color, font=("Arial", 26))

    def draw_player(self, pid, x, y):
        p = self.game.players[pid]
        active = p.state in (PlayerState.IN, PlayerState.TO_CALL, PlayerState.ALL_IN)
        is_current = (pid == self.game.current_player)
        
        bg_color = "#2d2d2d" if active else "#1a1a1a"
        outline_color = "#00e5ff" if is_current else "#ffd600" if p.last_pot > 0 else "#555"
        width = 3 if is_current else 2

        self.canvas.create_rectangle(x - 65, y - 55, x + 65, y + 55,
                                     fill=bg_color, outline=outline_color, width=width)

        self.canvas.create_text(x, y - 40, text=f"PLAYER {pid}",
                                fill="white", font=("Segoe UI", 10, "bold"))
        self.canvas.create_text(x, y - 22, text=f"${p.chips}",
                                fill="#ffd600", font=("Segoe UI", 11, "bold"))
        
        state_text = p.state.name.replace("_", " ").title()
        self.canvas.create_text(x, y + 40, text=state_text,
                                fill="#00e5ff" if active else "#888", font=("Segoe UI", 9, "bold"))

        if pid in self.game.hands:
            h = self.game.hands[pid]
            # Show cards if active, OR if showdown mode is on and they didn't fold
            show_cards = active or (self.showdown_mode and p.state != PlayerState.OUT)
            self.draw_card(x - 22, y + 5, h[0], face_up=show_cards)
            self.draw_card(x + 22, y + 5, h[1], face_up=show_cards)
            
        if hasattr(self.game, 'btn_loc') and pid == self.game.btn_loc:
            self.canvas.create_oval(x + 45, y - 45, x + 60, y - 30, fill="white", outline="#000")
            self.canvas.create_text(x + 52, y - 37, text="D", fill="#000", font=("Arial", 8, "bold"))

    def log(self, msg):
        self.log_box.insert(tk.END, msg + "\n")
        lines = self.log_box.get("1.0", tk.END).split("\n")
        if len(lines) > 100:
            self.log_box.delete("1.0", f"{len(lines) - 100}.0")
        self.log_box.see(tk.END)

    def toggle_pause(self):
        self.paused = not self.paused
        self.pause_btn.config(text="PAUSE" if not self.paused else "RESUME")
        if not self.paused:
            self.step()

    def reset_game(self):
        self.paused = True
        self.game = MyTexasHoldEm(buyin=1000, big_blind=20, small_blind=10, max_players=6)
        self.wins = {i: 0 for i in range(6)}
        self.total_hands = 0
        for ai in self.ais.values():
            ai.last_win_prob = 0.0
        self.log("\n--- NEW GAME INITIATED ---")
        self.draw_game()
        self.pause_btn.config(text="RESUME")

    def step(self):
        if self.paused:
            return

        if not self.game.is_hand_running():
            self.game.start_hand()
            self.showdown_mode = False
            self.log("\n--- NEW HAND ---")
            self.draw_game()
            self.root.after(NEW_HAND_DELAY, self.step)
            return

        pid = self.game.current_player
        ai = self.ais[pid]

        def ai_worker():
            action, amt = ai.decide_action(self.game)
            self.root.after(AI_DECIDE_DELAY, lambda: self.apply_action(pid, action, amt))

        threading.Thread(target=ai_worker, daemon=True).start()

    def apply_action(self, pid, action, amount):
        current_delay = self.speed_var.get()
        try:
            if action == ActionType.RAISE:
                to_call = self.game.chips_to_call(pid)
                min_raise = self.game.min_raise()
                current_bet = sum(pot.player_amounts.get(pid, 0) for pot in self.game.pots)
                player_chips = self.game.players[pid].chips
                max_total_bet = current_bet + player_chips
                
                valid_raise = max(amount, to_call + min_raise)
                valid_raise = min(valid_raise, max_total_bet)
                
                if valid_raise >= max_total_bet:
                    self.game.take_action(ActionType.ALL_IN)
                    action_str, amount_str = "ALL-IN", f"${player_chips}"
                else:
                    self.game.take_action(ActionType.RAISE, total=valid_raise)
                    action_str, amount_str = "RAISE", f"${valid_raise}"
                    
            elif action == ActionType.ALL_IN:
                self.game.take_action(ActionType.ALL_IN)
                action_str, amount_str = "ALL-IN", f"${self.game.players[pid].chips}"
            else:
                self.game.take_action(action)
                action_str, amount_str = action.name, ""

            self.log(f"P{pid} {action_str} {amount_str}".strip())
            self.draw_game()

            if self.game.is_hand_running():
                self.root.after(current_delay, self.step)
            else:
                self.resolve_hand()
                
        except ValueError as e:
            self.log(f"Action error for P{pid}: {e}. Forcing FOLD.")
            try:
                self.game.take_action(ActionType.FOLD)
            except ValueError:
                pass
            self.draw_game()
            if self.game.is_hand_running():
                self.root.after(current_delay, self.step)
            else:
                self.resolve_hand()

    def resolve_hand(self):
        self.showdown_mode = True
        self.draw_game()
        
        # Robust Winner Determination using Evaluator
        active_players = [p for p in self.game.players if p.state != PlayerState.OUT]
        
        if len(active_players) == 1:
            winners = [active_players[0].player_id]
        else:
            best_rank = 10000
            winning_ids = []
            for p in active_players:
                score = evaluate(self.game.hands[p.player_id], self.game.board)
                if score < best_rank:
                    best_rank = score
                    winning_ids = [p.player_id]
                elif score == best_rank:
                    winning_ids.append(p.player_id)
            winners = winning_ids

        # Distribute winnings manually for visual accuracy if needed, 
        # but the library handles the chip transfer internally.
        # We just need to identify who got money for the stats.
        stat_winners = [p.player_id for p in self.game.players if p.last_pot > 0]
        if not stat_winners:
            stat_winners = winners # Fallback to our calculated winners

        for pid in stat_winners:
            self.wins[pid] += 1
            
        # Bankruptcy Check & Rebuy
        for p in self.game.players:
            if p.chips <= 0:
                p.chips = self.game.buyin
                self.log(f"⚠️ P{p.player_id} went bankrupt! Rebuying ${self.game.buyin}.")

        self.total_hands += 1
        winner_names = ", ".join(f"P{w}" for w in stat_winners)
        winning_hand = rank_to_string(best_rank) if len(active_players) > 1 else "Walkover"
        
        self.log(f"🏆 WINNERS: {winner_names} | Hand: {winning_hand}")
        
        self.root.after(WINNERS_DELAY, self.step)


if __name__ == "__main__":
    root = tk.Tk()
    app = PokerGUI(root)
    root.mainloop()