import tkinter as tk
import threading
import random
import json
import os
import chess


class DualRLChessGUI:
    def __init__(self, master):
        self.master = master
        self.master.title("Dual RL Self-Play Chess (Self-Play Learning)")
        self.master.geometry("1000x700")
        self.master.resizable(True, True)

        # Core state
        self.board = chess.Board()
        self.square_colors = {"light": "#DCCBA6", "dark": "#8A6D4B"}
        self.current_display_color = chess.WHITE

        # Files
        base_dir = os.path.dirname(os.path.abspath(__file__))
        self.q_white_file = os.path.join(base_dir, "q_white.json")
        self.q_black_file = os.path.join(base_dir, "q_black.json")
        self.score_file = os.path.join(base_dir, "dual_rl_score.json")

        # Q-learning params
        self.q_white = self._load_json(self.q_white_file, default={})
        self.q_black = self._load_json(self.q_black_file, default={})
        # Different learning hyperparameters per side to diversify play styles
        self.learning_rate_white = 0.12
        self.learning_rate_black = 0.08
        self.discount_white = 0.92
        self.discount_black = 0.88

        # Exploration schedules (different per side)
        self.epsilon_white = 0.40
        self.epsilon_black = 0.25
        self.epsilon_white_min = 0.02
        self.epsilon_black_min = 0.01
        self.epsilon_white_decay = 0.985
        self.epsilon_black_decay = 0.995
        # Draw avoidance and repetition discouragement (asymmetric: harsher for White)
        self.draw_reward_white = -0.15
        self.draw_reward_black = -0.05
        self.repeat_penalty_white = 0.04
        self.repeat_penalty_black = 0.01
        self.max_plies = 200
        self.per_move_white_penalty = 0.002
        self.per_move_black_reward = 0.002
        self.survive_bonus_black = 0.10
        # Rewards: sparse terminal only; intermediate steps get 0

        # Live scores (per game outcome)
        score_default = {"white": 0, "black": 0, "games": 0}
        self.scores = self._load_json(self.score_file, default=score_default)

        # Learning history for one game: (fen, move_uci, mover_color)
        self.history = []
        self.state_visit_counts = {}

        # GUI
        self._build_gui()

        # Start first game
        self._new_game()

    # ---------- GUI ----------
    def _build_gui(self):
        self.main_frame = tk.Frame(self.master, bg="#2c3e50", padx=10, pady=10)
        self.main_frame.pack(fill=tk.BOTH, expand=True)

        self.canvas = tk.Canvas(self.main_frame, width=640, height=640, bg="white")
        self.canvas.pack(side=tk.LEFT, padx=10, pady=10, expand=True, fill=tk.BOTH)
        self.canvas.bind("<Configure>", lambda e: (self._draw_board(), self._update_board()))

        sidebar = tk.Frame(self.main_frame, bg="#34495e", width=280)
        sidebar.pack(side=tk.RIGHT, fill=tk.Y)
        sidebar.pack_propagate(False)

        self.status_label = tk.Label(sidebar, text="Initializing...", fg="white", bg="#34495e")
        self.status_label.pack(fill=tk.X, pady=(10, 4))

        # No engine evaluation display (per user request)

        self.score_label = tk.Label(
            sidebar,
            text=self._score_text(),
            fg="#8aff8a",
            bg="#34495e",
            font=("Inter", 11, "bold"),
        )
        self.score_label.pack(fill=tk.X, pady=6)

        self.epsilon_label = tk.Label(
            sidebar,
            text=f"Epsilon W/B: {self.epsilon_white:.2f} / {self.epsilon_black:.2f}",
            fg="#b0e0e6",
            bg="#34495e",
        )
        self.epsilon_label.pack(fill=tk.X, pady=6)

        btn_frame = tk.Frame(sidebar, bg="#34495e")
        btn_frame.pack(pady=10)

        tk.Button(btn_frame, text="New Game", command=self._new_game, bg="#28a745", fg="white").grid(row=0, column=0, padx=4)
        tk.Button(btn_frame, text="Reset Scores", command=self._reset_scores, bg="#dc3545", fg="white").grid(row=0, column=1, padx=4)

        tk.Button(sidebar, text="Flip Board", command=self._flip_view, bg="#17a2b8", fg="white").pack(pady=4)

        self._draw_board()
        self._update_board()

    # ---------- Persistence helpers ----------
    def _load_json(self, path, default):
        try:
            if os.path.exists(path):
                with open(path, "r") as f:
                    return json.load(f)
        except Exception:
            pass
        return default

    def _save_json(self, path, data):
        try:
            with open(path, "w") as f:
                json.dump(data, f, indent=2)
        except Exception:
            pass

    def _score_text(self):
        leader = "Tie"
        if self.scores["white"] > self.scores["black"]:
            leader = "White leads"
        elif self.scores["black"] > self.scores["white"]:
            leader = "Black leads"
        return f"Score — White: {self.scores['white']} | Black: {self.scores['black']} | Games: {self.scores['games']}\n{leader}"

    def _reset_scores(self):
        self.scores = {"white": 0, "black": 0, "games": 0}
        self.score_label.config(text=self._score_text())
        self._save_json(self.score_file, self.scores)

    # (No engine required)

    # ---------- Board drawing ----------
    def _draw_board(self):
        self.canvas.delete("all")
        w = self.canvas.winfo_width()
        h = self.canvas.winfo_height()
        self.square_size = min(w, h) // 8
        for row in range(8):
            for col in range(8):
                x1 = col * self.square_size
                y1 = row * self.square_size
                x2 = x1 + self.square_size
                y2 = y1 + self.square_size
                color = self.square_colors["light"] if (row + col) % 2 == 0 else self.square_colors["dark"]
                self.canvas.create_rectangle(x1, y1, x2, y2, fill=color, outline=color)

    def _update_board(self):
        self.canvas.delete("pieces")
        rows = range(8) if self.current_display_color == chess.WHITE else range(7, -1, -1)
        cols = range(8) if self.current_display_color == chess.WHITE else range(7, -1, -1)
        for r_idx, row in enumerate(rows):
            for c_idx, col in enumerate(cols):
                sq = chess.square(col, row)
                piece = self.board.piece_at(sq)
                if not piece:
                    continue
                x = c_idx * self.square_size + self.square_size // 2
                y = r_idx * self.square_size + self.square_size // 2
                sym = piece.symbol()
                color = "white" if piece.color == chess.WHITE else "black"
                self.canvas.create_text(
                    x,
                    y,
                    text=self._unicode_piece(sym),
                    font=("Inter", int(self.square_size * 0.7), "bold"),
                    fill=color,
                    tags="pieces",
                )

    def _unicode_piece(self, s):
        mapping = {
            "P": "\u2659",
            "N": "\u2658",
            "B": "\u2657",
            "R": "\u2656",
            "Q": "\u2655",
            "K": "\u2654",
            "p": "\u265F",
            "n": "\u265E",
            "b": "\u265D",
            "r": "\u265C",
            "q": "\u265B",
            "k": "\u265A",
        }
        return mapping.get(s, s)

    def _flip_view(self):
        self.current_display_color = not self.current_display_color
        self._draw_board()
        self._update_board()

    # ---------- Game flow ----------
    def _new_game(self):
        self.board = chess.Board()
        self.history.clear()
        self.state_visit_counts = {}
        self.status_label.config(text="New game started.", fg="white")
        self._update_board()
        self._schedule_next_move(delay_ms=100)

    def _schedule_next_move(self, delay_ms=100):
        if self.board.is_game_over():
            self._handle_game_over()
            return
        self.master.after(delay_ms, self._play_next_move_threaded)

    def _play_next_move_threaded(self):
        def worker():
            try:
                # Choose move via epsilon-greedy for current side
                if self.board.turn == chess.WHITE:
                    move = self._choose_move(self.q_white, self.epsilon_white)
                else:
                    move = self._choose_move(self.q_black, self.epsilon_black)

                if move is None:
                    self.master.after(0, lambda: self.status_label.config(text="No legal moves.", fg="red"))
                    return

                fen = self.board.board_fen()
                mover_color = self.board.turn
                self.board.push(move)
                # Track repetition on the resulting position
                new_fen = self.board.board_fen()
                count = self.state_visit_counts.get(new_fen, 0) + 1
                self.state_visit_counts[new_fen] = count
                self.history.append((fen, move.uci(), mover_color, count))

                # Update UI
                self.master.after(0, self._update_board)
                # No performance analysis display

                if not self.board.is_game_over():
                    # Stop very long games to avoid endless draws
                    if len(self.history) >= self.max_plies:
                        self.master.after(0, self._handle_game_over)
                    else:
                        self._schedule_next_move(80)
                else:
                    self.master.after(0, self._handle_game_over)
            except Exception as e:
                self.master.after(0, lambda: self.status_label.config(text=f"Error: {e}", fg="red"))

        threading.Thread(target=worker, daemon=True).start()

    def _choose_move(self, q_table, epsilon):
        legal = list(self.board.legal_moves)
        if not legal:
            return None
        if random.random() < epsilon:
            return random.choice(legal)
        fen = self.board.board_fen()
        best_q = -1e18
        best_moves = []
        for m in legal:
            key = f"{fen}-{m.uci()}"
            qv = q_table.get(key, 0.0)
            if qv > best_q:
                best_q = qv
                best_moves = [m]
            elif qv == best_q:
                best_moves.append(m)
        return random.choice(best_moves) if best_moves else random.choice(legal)

    # ---------- Learning ----------
    def _handle_game_over(self):
        outcome_reward_white = 0
        outcome_reward_black = 0
        if self.board.is_checkmate():
            # side to move is checkmated
            loser = self.board.turn
            if loser == chess.WHITE:
                outcome_reward_white = -1
                outcome_reward_black = 1
                self.scores["black"] += 1
                self.status_label.config(text="Checkmate! Black wins.", fg="red")
            else:
                outcome_reward_white = 1
                outcome_reward_black = -1
                self.scores["white"] += 1
                self.status_label.config(text="Checkmate! White wins.", fg="red")
        else:
            # Treat all other terminations as draw
            self.status_label.config(text="Game drawn.", fg="yellow")

        self.scores["games"] += 1
        self.score_label.config(text=self._score_text())

        # Learn for both players from the recorded history (sparse terminal reward only)
        self._learn_from_history(outcome_reward_white, outcome_reward_black)

        # Decay epsilons (asymmetric schedules)
        self.epsilon_white = max(self.epsilon_white_min, self.epsilon_white * self.epsilon_white_decay)
        self.epsilon_black = max(self.epsilon_black_min, self.epsilon_black * self.epsilon_black_decay)
        self.epsilon_label.config(text=f"Epsilon W/B: {self.epsilon_white:.2f} / {self.epsilon_black:.2f}")

        # Persist
        self._save_json(self.q_white_file, self.q_white)
        self._save_json(self.q_black_file, self.q_black)
        self._save_json(self.score_file, self.scores)

        # Start a new game after short delay
        self.master.after(300, self._new_game)

    def _learn_from_history(self, final_white_reward, final_black_reward):
        # Iterate from last to first
        for i in reversed(range(len(self.history))):
            fen, move_uci, mover_color, visit_count = self.history[i]

            # Build next state
            temp = chess.Board(fen)
            try:
                temp.push_uci(move_uci)
            except ValueError:
                continue

            # Terminal?
            if temp.is_game_over() or (i == len(self.history) - 1 and len(self.history) >= self.max_plies):
                # Draw discouragement if no decisive result
                if (temp.is_game_over() and not temp.is_checkmate()) or (len(self.history) >= self.max_plies):
                    base_reward = self.draw_reward_white if mover_color == chess.WHITE else self.draw_reward_black
                else:
                    base_reward = final_white_reward if mover_color == chess.WHITE else final_black_reward
                # Survival bonus for Black if game dragged to limit without decisive result
                if (len(self.history) >= self.max_plies) and mover_color == chess.BLACK and base_reward < 0:
                    base_reward += self.survive_bonus_black
                reward = base_reward
                max_q_next = 0.0
            else:
                # Intermediate shaping: repetition discouragement and slight time preference asymmetry
                rp = self.repeat_penalty_white if mover_color == chess.WHITE else self.repeat_penalty_black
                reward = -rp * max(0, visit_count - 1)
                # Per-move shaping: penalize White for taking too long; reward Black for surviving
                if mover_color == chess.WHITE:
                    reward -= self.per_move_white_penalty
                else:
                    reward += self.per_move_black_reward
                # Estimate max Q at next state for the same player when they move again
                next_fen = temp.board_fen()
                max_q_next = 0.0
                q_tbl = self.q_white if mover_color == chess.WHITE else self.q_black
                for key, val in q_tbl.items():
                    if key.startswith(next_fen + "-"):
                        if val > max_q_next:
                            max_q_next = val

            # Update Q for (fen, move)
            key = f"{fen}-{move_uci}"
            if mover_color == chess.WHITE:
                q_tbl = self.q_white
                lr = self.learning_rate_white
                gamma = self.discount_white
            else:
                q_tbl = self.q_black
                lr = self.learning_rate_black
                gamma = self.discount_black
            old_v = q_tbl.get(key, 0.0)
            new_v = old_v + lr * (reward + gamma * max_q_next - old_v)
            q_tbl[key] = new_v

    # ---------- Utils ----------
    def on_close(self):
        try:
            self._save_json(self.q_white_file, self.q_white)
            self._save_json(self.q_black_file, self.q_black)
            self._save_json(self.score_file, self.scores)
        finally:
            self.master.destroy()


if __name__ == "__main__":
    root = tk.Tk()
    app = DualRLChessGUI(root)
    root.protocol("WM_DELETE_WINDOW", app.on_close)
    root.mainloop()


