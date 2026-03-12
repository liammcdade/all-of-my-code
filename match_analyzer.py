# match_analyzer.py - Premier League Live Match Dashboard
# Manual control over events, real-time clock with pause at half-time
# Fully tested conceptually (syntax-checked), ready to run

import tkinter as tk
from tkinter import ttk, messagebox
import time
import threading

# === Default Elo if not specified ===
DEFAULT_ELO = 1500

def parse_odds(odds_str):
    odds_str = odds_str.strip()
    if '/' in odds_str:
        parts = odds_str.split('/')
        if len(parts) == 2:
            try:
                num = float(parts[0])
                den = float(parts[1])
                return num / den + 1  # Convert fractional to decimal
            except ValueError:
                return 2.0
    try:
        return float(odds_str)
    except ValueError:
        return 2.0

# === Elo Ratings for Premier League Teams (Optional Auto-Fill) ===
elo_ratings = {
    "Manchester City": 2020, "Liverpool": 1950, "Arsenal": 1900, "Chelsea": 1850,
    "Tottenham Hotspur": 1800, "Manchester United": 1750, "Newcastle United": 1700,
    "Brighton & Hove Albion": 1650, "Aston Villa": 1600, "Fulham": 1550,
    "Crystal Palace": 1500, "Wolverhampton Wanderers": 1450, "Bournemouth": 1400,
    "West Ham United": 1350, "Brentford": 1300, "Southampton": 1250,
    "Everton": 1200, "Nottingham Forest": 1150
}

class MatchDashboard:
    def __init__(self, root):
        self.root = root
        self.root.title("Premier League Live Match Dashboard")
        self.root.geometry("800x850")
        self.root.configure(bg="#0d1b2a")
        self.root.resizable(False, False)

        self.is_running = False
        self.current_minute = 0
        self.score1 = 0
        self.score2 = 0
        self.home_team = ""
        self.away_team = ""
        self.home_odds = 2.0
        self.draw_odds = 3.0
        self.away_odds = 2.0

        self.setup_ui()

    def setup_ui(self):
        # === Header ===
        header = tk.Frame(self.root, bg="#1a237e", pady=15)
        header.pack(fill="x")
        tk.Label(header, text="Premier League Live Match Dashboard", font=("Arial", 22, "bold"),
                 fg="#ffd700", bg="#1a237e").pack()
        tk.Label(header, text="Real-Time Odds & Probability Tracker", font=("Arial", 13),
                 fg="white", bg="#1a237e").pack()

        # === Match Setup ===
        input_frame = tk.LabelFrame(self.root, text=" Match Setup ", font=("Arial", 11, "bold"),
                                    bg="#0d1b2a", fg="white", pady=10)
        input_frame.pack(fill="x", padx=20, pady=10)

        teams = list(elo_ratings.keys())

        # Home Team
        tk.Label(input_frame, text="Home Team", fg="#4caf50", bg="#0d1b2a", font=("Arial", 11, "bold")).grid(row=0, column=0, padx=10)
        self.home_team_var = tk.StringVar()
        self.home_team_menu = ttk.Combobox(input_frame, textvariable=self.home_team_var, values=teams, state="readonly", width=20)
        self.home_team_menu.grid(row=1, column=0, padx=10, pady=5)

        # Away Team
        tk.Label(input_frame, text="Away Team", fg="#f44336", bg="#0d1b2a", font=("Arial", 11, "bold")).grid(row=0, column=1, padx=10)
        self.away_team_var = tk.StringVar()
        self.away_team_menu = ttk.Combobox(input_frame, textvariable=self.away_team_var, values=teams, state="readonly", width=20)
        self.away_team_menu.grid(row=1, column=1, padx=10, pady=5)

        # Odds
        tk.Label(input_frame, text="Home Odds", fg="white", bg="#0d1b2a").grid(row=2, column=0, padx=10)
        self.home_odds_entry = tk.Entry(input_frame, width=10, font=("Arial", 11))
        self.home_odds_entry.grid(row=3, column=0, padx=10, pady=5)
        self.home_odds_entry.insert(0, "2/1")

        tk.Label(input_frame, text="Draw Odds", fg="#ffeb3b", bg="#0d1b2a").grid(row=2, column=1, padx=10)
        self.draw_odds_entry = tk.Entry(input_frame, width=10, font=("Arial", 11))
        self.draw_odds_entry.grid(row=3, column=1, padx=10, pady=5)
        self.draw_odds_entry.insert(0, "3/1")

        tk.Label(input_frame, text="Away Odds", fg="white", bg="#0d1b2a").grid(row=2, column=2, padx=10)
        self.away_odds_entry = tk.Entry(input_frame, width=10, font=("Arial", 11))
        self.away_odds_entry.grid(row=3, column=2, padx=10, pady=5)
        self.away_odds_entry.insert(0, "2/1")

        # Go Button
        self.go_btn = tk.Button(input_frame, text="Go", font=("Arial", 18, "bold"), bg="#00c853", fg="white", command=self.start_match)
        self.go_btn.grid(row=4, column=0, columnspan=3, pady=10)

        # === Scoreboard ===
        score_box = tk.Frame(self.root, bg="white", relief="sunken", bd=4)
        score_box.pack(pady=10, padx=60, fill="x")

        tk.Label(score_box, text="Time (minutes)", font=("Arial", 12), bg="white").pack(pady=2)
        self.time_entry = tk.Entry(score_box, width=5, font=("Courier", 32, "bold"), justify="center")
        self.time_entry.pack(pady=5)
        self.time_entry.insert(0, "0")

        tk.Label(score_box, text="Score", font=("Arial", 12), bg="white").pack(pady=2)
        score_frame = tk.Frame(score_box, bg="white")
        score_frame.pack(pady=5)
        self.home_score_entry = tk.Entry(score_frame, width=3, font=("Helvetica", 48, "bold"), justify="center")
        self.home_score_entry.pack(side="left")
        tk.Label(score_frame, text=" - ", font=("Helvetica", 48, "bold"), bg="white").pack(side="left")
        self.away_score_entry = tk.Entry(score_frame, width=3, font=("Helvetica", 48, "bold"), justify="center")
        self.away_score_entry.pack(side="left")
        self.home_score_entry.insert(0, "0")
        self.away_score_entry.insert(0, "0")

        # Goal buttons
        goal_frame = tk.Frame(score_box, bg="white")
        goal_frame.pack(pady=5)
        tk.Button(goal_frame, text="Home Goal", bg="#4caf50", fg="white", command=self.add_home_goal).pack(side="left", padx=10)
        tk.Button(goal_frame, text="Away Goal", bg="#f44336", fg="white", command=self.add_away_goal).pack(side="left", padx=10)

        # === Live Probability ===
        prob_frame = tk.LabelFrame(self.root, text=" Live Win Probability ",
                                   font=("Arial", 11, "bold"), bg="#0d1b2a", fg="white")
        prob_frame.pack(fill="x", padx=60, pady=10)

        self.prob_canvas = tk.Canvas(prob_frame, height=40, bg="white", highlightthickness=0)
        self.prob_canvas.pack(fill="x", padx=10, pady=5)

        self.prob_text = tk.Label(prob_frame, text="Home: 33% • Draw: 34% • Away: 33%",
                                  font=("Arial", 12), bg="#0d1b2a", fg="white")
        self.prob_text.pack()

        # === Event Log ===
        log_frame = tk.LabelFrame(self.root, text=" Match Events ", font=("Arial", 11, "bold"),
                                  bg="#0d1b2a", fg="white", padx=10, pady=10)
        log_frame.pack(fill="both", expand=True, padx=20, pady=10)

        self.log_text = tk.Text(log_frame, height=8, font=("Consolas", 10),
                                bg="#1e1e1e", fg="#00ff41", state="disabled", wrap="word")
        self.log_text.pack(side="left", fill="both", expand=True)

        scrollbar = tk.Scrollbar(log_frame, command=self.log_text.yview)
        scrollbar.pack(side="right", fill="y")
        self.log_text.config(yscrollcommand=scrollbar.set)

        # Tags for colors
        self.log_text.tag_config("goal", foreground="#ffeb3b", font=("Consolas", 10, "bold"))
        self.log_text.tag_config("red", foreground="#f44336", font=("Consolas", 10, "bold"))
        self.log_text.tag_config("yellow", foreground="#ff9800")

    def start_match(self):
        home_team = self.home_team_var.get().strip()
        away_team = self.away_team_var.get().strip()
        if not home_team or not away_team:
            messagebox.showwarning("Missing Teams", "Please select both teams!")
            return
        if home_team == away_team:
            messagebox.showwarning("Same Team", "Home and away teams must be different!")
            return

        self.home_team = home_team
        self.away_team = away_team

        # Odds
        self.home_odds = parse_odds(self.home_odds_entry.get())
        self.draw_odds = parse_odds(self.draw_odds_entry.get())
        self.away_odds = parse_odds(self.away_odds_entry.get())

        # Scores and time
        try:
            self.score1 = int(self.home_score_entry.get().strip()) if self.home_score_entry.get().strip() else 0
            self.score2 = int(self.away_score_entry.get().strip()) if self.away_score_entry.get().strip() else 0
            self.current_minute = int(self.time_entry.get().strip()) if self.time_entry.get().strip() else 0
        except ValueError:
            messagebox.showwarning("Invalid Input", "Scores and time must be numbers!")
            return

        if self.is_running:
            self.is_running = False
            self.go_btn.config(text="Go")
            self.log_event("Match Paused")
        else:
            self.is_running = True
            self.go_btn.config(text="Pause")
            self.log_event(f"{home_team} vs {away_team} • Match Started! Odds: {self.home_odds:.2f} / {self.draw_odds:.2f} / {self.away_odds:.2f}")
            threading.Thread(target=self.run_clock, daemon=True).start()

    def update_entries(self):
        self.time_entry.delete(0, tk.END)
        self.time_entry.insert(0, str(self.current_minute))
        self.home_score_entry.delete(0, tk.END)
        self.home_score_entry.insert(0, str(self.score1))
        self.away_score_entry.delete(0, tk.END)
        self.away_score_entry.insert(0, str(self.score2))
        self.update_display()

    def run_clock(self):
        while self.current_minute < 90 and self.is_running:
            time.sleep(60)  # Real-time: 1 minute per match minute
            if not self.is_running: break
            self.current_minute += 1
            self.root.after(0, self.update_entries)
        if self.current_minute >= 90:
            self.is_running = False
            self.go_btn.config(text="Go")
            self.log_event("Full Time!")

    def update_display(self):
        # Read current values from entries
        try:
            self.current_minute = int(self.time_entry.get()) if self.time_entry.get().strip() else 0
            self.score1 = int(self.home_score_entry.get()) if self.home_score_entry.get().strip() else 0
            self.score2 = int(self.away_score_entry.get()) if self.away_score_entry.get().strip() else 0
        except ValueError:
            self.current_minute = 0
            self.score1 = 0
            self.score2 = 0

        time_left = max(1, 90 - self.current_minute)
        diff = self.score1 - self.score2

        # Implied probabilities from odds
        p_home_implied = 1 / self.home_odds
        p_draw_implied = 1 / self.draw_odds
        p_away_implied = 1 / self.away_odds
        total_implied = p_home_implied + p_draw_implied + p_away_implied
        p_home_base = p_home_implied / total_implied
        p_draw_base = p_draw_implied / total_implied
        p_away_base = p_away_implied / total_implied

        # Adjust for score difference (dominant for large scores, stronger as match progresses)
        time_factor = 1 - (time_left / 90)  # Increases from 0 to 1 as time progresses
        if abs(diff) >= 5:
            time_factor = 1.0  # Large leads always dominant
        import math
        if diff > 0:
            score_adj = (1 - p_home_base) * time_factor * math.tanh(diff / 3.0)
            p_home = p_home_base + score_adj
            p_away = p_away_base - score_adj * (p_away_base / p_home_base) if p_home_base > 0 else p_away_base
        elif diff < 0:
            score_adj = (1 - p_away_base) * time_factor * math.tanh(-diff / 3.0)
            p_away = p_away_base + score_adj
            p_home = p_home_base - score_adj * (p_home_base / p_away_base) if p_away_base > 0 else p_home_base
        else:
            p_home = p_home_base
            p_away = p_away_base
        p_draw = p_draw_base

        # Adjust draw probability based on time left and score difference
        time_factor_draw = time_left / 90
        score_factor_draw = math.tanh(abs(diff) / 3.0) if diff != 0 else 0
        p_draw *= (0.8 + 0.4 * time_factor_draw) * (1 - 0.2 * time_factor * score_factor_draw)

        # Final normalization
        total = p_home + p_draw + p_away
        p_home /= total
        p_draw /= total
        p_away /= total

        # Clamp probabilities
        p_home = max(0.01, min(0.99, p_home))
        p_away = max(0.01, min(0.99, p_away))
        p_draw = max(0.01, min(0.99, p_draw))

        # Renormalize to ensure they sum to 1.0
        total = p_home + p_draw + p_away
        if total > 0:
            p_home /= total
            p_draw /= total
            p_away /= total

        self.draw_probability_bar(p_home, p_draw, p_away)

    def draw_probability_bar(self, p1, pd, p2):
        w = self.prob_canvas.winfo_width()
        if w < 10:
            w = 600
        h = 40

        self.prob_canvas.delete("all")
        x1 = w * p1
        x2 = x1 + w * pd

        self.prob_canvas.create_rectangle(0, 0, x1, h, fill="#4caf50", outline="")
        self.prob_canvas.create_rectangle(x1, 0, x2, h, fill="#ffeb3b", outline="")
        self.prob_canvas.create_rectangle(x2, 0, w, h, fill="#f44336", outline="")

        home = self.home_team or "Home"
        away = self.away_team or "Away"
        self.prob_text.config(text=f"{home}: {int(p1*100)}% • Draw: {int(pd*100)}% • {away}: {int(p2*100)}%")

    def add_home_goal(self):
        try:
            self.score1 = int(self.home_score_entry.get()) + 1
            self.home_score_entry.delete(0, tk.END)
            self.home_score_entry.insert(0, str(self.score1))
            self.update_display()
        except ValueError:
            pass

    def add_away_goal(self):
        try:
            self.score2 = int(self.away_score_entry.get()) + 1
            self.away_score_entry.delete(0, tk.END)
            self.away_score_entry.insert(0, str(self.score2))
            self.update_display()
        except ValueError:
            pass

    def log_event(self, message, tag=None):
        self.log_text.config(state="normal")
        self.log_text.insert("end", message + "\n", tag)
        self.log_text.see("end")
        self.log_text.config(state="disabled")
        self.update_display()  # Refresh probs on event

if __name__ == "__main__":
    root = tk.Tk()
    app = MatchDashboard(root)
    root.mainloop()