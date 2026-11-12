"""Tkinter dashboard: board renderer, live stats, log, training controls."""
import tkinter as tk
from tkinter import ttk, messagebox

from board import BOARD, GROUP_COLORS, PLAYER_COLORS, N_TILES
from engine import Engine, play_game
from ai import Agent, HumanAgent, load_brains, save_brains, DEFAULT_BRAINS
from tuning import load_tuners, save_tuners, TUNER_FILE, fitness as fit_fn

CELL = 76
BOARD_PX = CELL * 11


def tile_rc(i):
    """Map tile index -> (row, col) on an 11x11 grid."""
    if i <= 10:
        return (10, 10 - i)
    if i <= 20:
        return (10 - (i - 10), 0)
    if i <= 30:
        return (0, i - 20)
    return (i - 30, 10)


class MonopolyGUI:
    def __init__(self, root):
        self.root = root
        root.title("Monopoly AI Lab")
        root.configure(bg="#1b1b1f")

        self.brains = load_brains(DEFAULT_BRAINS, 4)
        self.tuners = load_tuners(TUNER_FILE, 4)
        self.agents = [Agent(i, self.brains[i], self.tuners[i]) for i in range(4)]
        self.human_mode = tk.BooleanVar(value=False)
        self.engine = None
        self.auto = False
        self.speed = 250
        self.log_cursor = 0

        self._build_widgets()
        self.new_game()

    # ------------------------------------------------------------------
    def _build_widgets(self):
        outer = tk.Frame(self.root, bg="#1b1b1f")
        outer.pack(fill="both", expand=True, padx=8, pady=8)

        self.canvas = tk.Canvas(outer, width=BOARD_PX, height=BOARD_PX,
                                bg="#cfd8dc", highlightthickness=0)
        self.canvas.pack(side="left")

        side = tk.Frame(outer, bg="#1b1b1f", width=400)
        side.pack(side="right", fill="both", expand=True, padx=(10, 0))
        side.pack_propagate(False)

        tk.Label(side, text="PLAYERS", bg="#1b1b1f", fg="#f1faee",
                 font=("Segoe UI", 11, "bold")).pack(anchor="w")

        self.players_frame = tk.Frame(side, bg="#1b1b1f")
        self.players_frame.pack(fill="x", pady=(2, 8))

        tk.Label(side, text="LOG", bg="#1b1b1f", fg="#f1faee",
                 font=("Segoe UI", 11, "bold")).pack(anchor="w")

        log_wrap = tk.Frame(side, bg="#1b1b1f")
        log_wrap.pack(fill="both", expand=True)
        self.log = tk.Text(log_wrap, bg="#101014", fg="#c9d1d9", height=16,
                           font=("Consolas", 8), wrap="word", state="disabled")
        sb = ttk.Scrollbar(log_wrap, command=self.log.yview)
        self.log.configure(yscrollcommand=sb.set)
        self.log.pack(side="left", fill="both", expand=True)
        sb.pack(side="right", fill="y")

        ctrl = tk.Frame(side, bg="#1b1b1f")
        ctrl.pack(fill="x", pady=(8, 0))

        self.play_btn = tk.Button(ctrl, text="▶ Auto-play", width=12,
                                  command=self.toggle_auto,
                                  bg="#2a9d8f", fg="white", relief="flat")
        self.play_btn.grid(row=0, column=0, padx=2, pady=2)
        tk.Button(ctrl, text="Step", width=6, command=self.step,
                  bg="#457b9d", fg="white", relief="flat"
                  ).grid(row=0, column=1, padx=2)
        tk.Button(ctrl, text="New game", width=9, command=self.new_game,
                  bg="#e63946", fg="white", relief="flat"
                  ).grid(row=0, column=2, padx=2)

        tk.Label(ctrl, text="Speed", bg="#1b1b1f", fg="#c9d1d9"
                 ).grid(row=1, column=0, sticky="w", pady=(6, 0))
        self.speed_var = tk.IntVar(value=250)
        tk.Scale(ctrl, from_=20, to=1200, orient="horizontal",
                 variable=self.speed_var, bg="#1b1b1f", fg="#c9d1d9",
                 highlightthickness=0, troughcolor="#333",
                 showvalue=False, command=self._set_speed
                 ).grid(row=1, column=1, columnspan=2, sticky="we")

        tk.Label(ctrl, text="Train games", bg="#1b1b1f", fg="#c9d1d9"
                 ).grid(row=2, column=0, sticky="w", pady=(6, 0))
        self.train_var = tk.Entry(ctrl, width=6)
        self.train_var.insert(0, "25")
        self.train_var.grid(row=2, column=1, sticky="w")
        tk.Button(ctrl, text="Train", command=self.train,
                  bg="#e9c46a", fg="#1b1b1f", relief="flat"
                  ).grid(row=2, column=2, sticky="e")

        tk.Button(ctrl, text="Save brains", command=self.save,
                  bg="#3c3c3c", fg="white", relief="flat"
                  ).grid(row=3, column=0, columnspan=2, sticky="we", pady=(6, 0))
        tk.Button(ctrl, text="Load brains", command=self.load,
                  bg="#3c3c3c", fg="white", relief="flat"
                  ).grid(row=3, column=2, sticky="we", pady=(6, 0))

        tk.Checkbutton(
            ctrl, text="I play as Player 1", variable=self.human_mode,
            command=self._toggle_human, bg="#1b1b1f", fg="#f1faee",
            selectcolor="#2a2a2a", activebackground="#1b1b1f"
        ).grid(row=4, column=0, columnspan=3, sticky="w", pady=(8, 0))

        self.status = tk.Label(side, text="", bg="#1b1b1f", fg="#8ecae6",
                               font=("Segoe UI", 9))
        self.status.pack(anchor="w", pady=(6, 0))

    # ------------------------------------------------------------------
    def _set_speed(self, _=None):
        self.speed = int(self.speed_var.get())

    def _set_agents(self, human=False):
        self.agents = [Agent(i, self.brains[i], self.tuners[i]) for i in range(4)]
        if human:
            self.agents[0] = HumanAgent(self.root)

    def _toggle_human(self):
        self._set_agents(human=self.human_mode.get())
        self.new_game()

    def new_game(self):
        self.auto = False
        self.play_btn.config(text="▶ Auto-play")
        self.engine = Engine(agents=self.agents, seed=None,
                             turn_limit=700, verbose=True)
        self.log_cursor = 0
        self._clear_log()
        human = self.human_mode.get()
        who = "You (Player 1) + AI 2-4" if human else "AI 1-4"
        self.write_log(f"New game started. Players: {who}.\n")
        self.render()
        self.update_stats()

    def step(self):
        if self.engine is None or self.engine.over:
            return
        self.engine.play_turn()
        self.flush_engine_log()
        self.render()
        self.update_stats()
        if self.engine.over:
            self.auto = False
            self.play_btn.config(text="▶ Auto-play")
            w = self.engine.winner
            name = self.engine.players[w].name if w is not None else "nobody"
            self.write_log(f"\n=== GAME OVER - winner: {name} ===\n")
            for b in self.brains:
                pass  # brains already updated by play_game during training

    def toggle_auto(self):
        self.auto = not self.auto
        self.play_btn.config(text="⏸ Pause" if self.auto else "▶ Auto-play")
        if self.auto:
            self._tick()

    def _tick(self):
        if not self.auto:
            return
        if self.engine is None or self.engine.over:
            self.auto = False
            self.play_btn.config(text="▶ Auto-play")
            return
        cur = self.engine.players[self.engine.current]
        if isinstance(self.agents[cur.id], HumanAgent) and not cur.bankrupt:
            self.auto = False
            self.play_btn.config(text="▶ Auto-play")
            self.status.config(text="Your turn — press Step or Auto-play")
            return
        self.step()
        self.root.after(self.speed, self._tick)

    # ------------------------------------------------------------------
    def train(self):
        try:
            n = int(self.train_var.get())
        except ValueError:
            return
        self.auto = False
        self.play_btn.config(text="▶ Auto-play")
        for i in range(n):
            for a in self.agents:
                a.params = a.tuner.sample()
            eng = Engine(agents=self.agents, seed=None,
                         turn_limit=400, verbose=False)
            play_game(eng)
            for i, a in enumerate(self.agents):
                a.tuner.update(fit_fn(eng, i))
            if i % 5 == 0 or i == n - 1:
                self.status.config(text=f"Training {i + 1}/{n} games...")
                self.root.update()
        self.status.config(text=f"Trained {n} games (total "
                                f"{self.brains[0].games} each)")
        self.render()
        self.update_stats()

    def save(self):
        save_brains(self.brains, DEFAULT_BRAINS)
        save_tuners(self.tuners, TUNER_FILE)
        self.status.config(text=f"Brains saved to {DEFAULT_BRAINS}, tuners to {TUNER_FILE}")

    def load(self):
        self.brains = load_brains(DEFAULT_BRAINS, 4)
        self.tuners = load_tuners(TUNER_FILE, 4)
        self._set_agents()
        self.status.config(text="Brains loaded")
        self.update_stats()

    # ------------------------------------------------------------------
    def _clear_log(self):
        self.log.config(state="normal")
        self.log.delete("1.0", "end")
        self.log.config(state="disabled")

    def write_log(self, text):
        self.log.config(state="normal")
        self.log.insert("end", text)
        self.log.see("end")
        self.log.config(state="disabled")

    def flush_engine_log(self):
        lines = self.engine.drain_log()
        if lines:
            self.write_log("\n".join(lines) + "\n")

    # ------------------------------------------------------------------
    def update_stats(self):
        for w in self.players_frame.winfo_children():
            w.destroy()
        if not self.engine:
            return
        for p in self.engine.players:
            row = tk.Frame(self.players_frame, bg="#1b1b1f")
            row.pack(fill="x", pady=1)
            colour = PLAYER_COLORS[p.id]
            tk.Label(row, text="  ", bg=colour, width=2
                     ).pack(side="left", padx=(0, 6))
            state = "BANKRUPT" if p.bankrupt else f"£{p.cash}"
            text = (f"{p.name}   {state}   "
                    f"net £{self.engine.net_worth(p.id)}   "
                    f"mono {self.engine.monopolies(p.id)}")
            fg = "#6c757d" if p.bankrupt else "#f1faee"
            tk.Label(row, text=text, bg="#1b1b1f", fg=fg,
                     font=("Segoe UI", 9), anchor="w").pack(side="left")

    # ------------------------------------------------------------------
    def render(self):
        c = self.canvas
        c.delete("all")
        eng = self.engine
        if eng is None:
            return

        for tile in BOARD:
            row, col = tile_rc(tile.index)
            x, y = col * CELL, row * CELL
            fill = "#eceff1"
            if tile.kind in ("go", "jail", "freeparking", "gotojail"):
                fill = "#dfe6e9"
            c.create_rectangle(x, y, x + CELL, y + CELL,
                               fill=fill, outline="#90a4ae")

            # colour band on the inner edge
            if tile.kind in ("property", "station", "utility"):
                colr = GROUP_COLORS.get(tile.group, "#999")
                if row == 10:
                    c.create_rectangle(x, y, x + CELL, y + 11, fill=colr, outline="")
                elif row == 0:
                    c.create_rectangle(x, y + CELL - 11, x + CELL, y + CELL,
                                       fill=colr, outline="")
                elif col == 0:
                    c.create_rectangle(x + CELL - 11, y, x + CELL, y + CELL,
                                       fill=colr, outline="")
                else:
                    c.create_rectangle(x, y, x + 11, y + CELL, fill=colr, outline="")

            # name
            c.create_text(x + CELL / 2, y + CELL / 2 - 6, text=tile.name,
                          width=CELL - 8, font=("Segoe UI", 6),
                          justify="center", fill="#20232a")

            # price
            if tile.price:
                c.create_text(x + CELL / 2, y + CELL - 12,
                              text=f"£{tile.price}", font=("Segoe UI", 6, "bold"),
                              fill="#37474f")

            # owner / houses
            if tile.is_ownable:
                st = eng.props[tile.index]
                if st.owner is not None:
                    oc = PLAYER_COLORS[st.owner]
                    c.create_rectangle(x + 2, y + 2, x + 14, y + 14,
                                       fill=oc, outline="")
                    if st.mortgaged:
                        c.create_text(x + CELL / 2, y + 14, text="M",
                                      font=("Segoe UI", 7, "bold"), fill="#b00020")
                if st.houses:
                    n = st.houses
                    label = "H" if n == 5 else str(n)
                    c.create_text(x + CELL - 12, y + CELL - 12,
                                  text=label, font=("Segoe UI", 8, "bold"),
                                  fill="#1b5e20")

        # highlight the current player's tile
        p = eng.players[eng.current]
        if not p.bankrupt:
            row, col = tile_rc(p.pos)
            x, y = col * CELL, row * CELL
            c.create_rectangle(x + 1, y + 1, x + CELL - 1, y + CELL - 1,
                               outline=PLAYER_COLORS[p.id], width=3)

        # tokens
        stacks = {}
        for pl in eng.players:
            if pl.bankrupt:
                continue
            stacks.setdefault(pl.pos, []).append(pl)
        for pos, plist in stacks.items():
            row, col = tile_rc(pos)
            x, y = col * CELL, row * CELL
            for k, pl in enumerate(plist):
                ox = 18 + (k % 2) * 22
                oy = 18 + (k // 2) * 22
                c.create_oval(x + ox, y + oy, x + ox + 16, y + oy + 16,
                              fill=PLAYER_COLORS[pl.id], outline="white", width=2)

        # centre label
        cx = cy = BOARD_PX / 2
        c.create_text(cx, cy - 20, text="MONOPOLY", font=("Segoe UI", 26, "bold"),
                      fill="#37474f")
        c.create_text(cx, cy + 14, text="AI LAB",
                      font=("Segoe UI", 14), fill="#546e7a")
        if eng.over:
            w = eng.winner
            name = eng.players[w].name if w is not None else "-"
            c.create_text(cx, cy + 50, text=f"Winner: {name}",
                          font=("Segoe UI", 12, "bold"), fill="#b00020")
        else:
            c.create_text(cx, cy + 50,
                          text=f"Turn {eng.turn} - {p.name}'s move",
                          font=("Segoe UI", 10), fill="#546e7a")


def run():
    root = tk.Tk()
    root.geometry("1260x900")
    MonopolyGUI(root)
    root.mainloop()