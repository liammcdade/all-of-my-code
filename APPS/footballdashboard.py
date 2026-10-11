# dashboard.py — local desktop League Team Radar (Tkinter + matplotlib)
# Run with:  python dashboard.py
# No browser, no Streamlit server, no PATH headaches.

import re
import numpy as np
import pandas as pd
import tkinter as tk
from tkinter import ttk
import matplotlib
matplotlib.use("TkAgg")
from matplotlib.figure import Figure
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg

# --------------------------------------------------------------------------- #
CSV_PATH = r"C:\Users\liam\Documents\GitHub\all-of-my-code\APPS\league-chemp.csv"

# Radar spokes.  label -> (source column, higher_is_better?)
# Stats where lower is better get inverted so the radar always reads:
#   outward = better.
METRICS = {
    "Points / Match":  ("points_per_match", True),
    "Goals / Match":   ("goals_per_match",  True),
    "xG / Match":      ("xg_per_match",     True),
    "xPTS / Match":    ("xpts_per_match",   True),
    "Win Rate":        ("win_rate",         True),
    "Non-pen xGD":     ("npxgd",            True),
    "Goals Against":   ("ga_per_match",     False),
    "xGA / Match":     ("xga_per_match",    False),
    "Pressing (PPDA)": ("ppda",             False),
}
METRIC_LABELS = list(METRICS.keys())
METRIC_COLS   = [v[0] for v in METRICS.values()]

COLOR_A = "#00C2FF"
COLOR_B = "#FF6B6B"

BG     = "#0e1117"
PANEL  = "#161b22"
FG     = "#e6edf3"
SUBTLE = "#8b949e"
GRID   = "#30363d"


# --------------------------------------------------------------------------- #
def load_data(path: str) -> pd.DataFrame:
    df = pd.read_csv(path, sep=";", encoding="utf-8-sig")

    def clean(c):
        s = str(c).replace("\ufeff", "").replace('"', "").replace("'", "")
        s = re.sub(r"[\u200b-\u200f\u202a-\u202e]", "", s)
        return s.strip().lower()

    df.columns = [clean(c) for c in df.columns]

    required = {"team", "matches", "wins", "draws", "loses",
                "goals", "ga", "points", "xg", "npxgd", "xga", "ppda", "xpts"}
    missing = required - set(df.columns)
    if missing:
        raise ValueError(f"Missing columns {sorted(missing)}. "
                         f"Found: {list(df.columns)}")

    for c in df.columns:
        if c != "team":
            df[c] = pd.to_numeric(df[c], errors="coerce")

    df["team"] = df["team"].astype(str).str.strip()

    m = df["matches"].replace(0, np.nan)
    df["points_per_match"] = df["points"] / m
    df["goals_per_match"]  = df["goals"]  / m
    df["ga_per_match"]     = df["ga"]     / m
    df["xg_per_match"]     = df["xg"]     / m
    df["xga_per_match"]    = df["xga"]    / m
    df["xpts_per_match"]   = df["xpts"]   / m
    df["win_rate"]         = df["wins"]   / m

    for c in METRIC_COLS:
        df[c] = df[c].fillna(df[c].median())

    return df


def percentile(pool: pd.Series, value: float, hib: bool) -> float:
    """Percentile rank of `value`, always oriented so bigger = better."""
    s = pool.dropna()
    if len(s) == 0 or pd.isna(value):
        return 0.0
    if hib:
        return float((s < value).sum()) / len(s) * 100.0
    return float((s > value).sum()) / len(s) * 100.0


# --------------------------------------------------------------------------- #
class Dashboard(tk.Tk):
    def __init__(self, df: pd.DataFrame):
        super().__init__()
        self.df = df
        self.title("League Team Radar")
        self.geometry("1500x920")
        self.minsize(1150, 720)
        self.configure(bg=BG)

        self._setup_style()
        self._build_ui()
        self._refresh()

    # ------------------------------------------------------------------ #
    def _setup_style(self):
        style = ttk.Style(self)
        try:
            style.theme_use("clam")
        except tk.TclError:
            pass

        style.configure("TFrame",       background=BG)
        style.configure("TLabel",       background=BG, foreground=FG,
                        font=("Segoe UI", 10))
        style.configure("Head.TLabel",  background=BG, foreground=FG,
                        font=("Segoe UI", 15, "bold"))
        style.configure("Sub.TLabel",   background=BG, foreground=SUBTLE,
                        font=("Segoe UI", 9))
        style.configure("TCombobox",
                        fieldbackground=PANEL, background=PANEL,
                        foreground=FG, arrowcolor=FG)
        style.configure("TCheckbutton",
                        background=BG, foreground=FG,
                        font=("Segoe UI", 10))
        style.map("TCheckbutton", background=[("active", BG)])
        style.configure("Treeview",
                        background=PANEL, fieldbackground=PANEL,
                        foreground=FG, rowheight=26, borderwidth=0,
                        font=("Segoe UI", 10))
        style.configure("Treeview.Heading",
                        background="#21262d", foreground=FG,
                        font=("Segoe UI", 10, "bold"), borderwidth=0)
        style.map("Treeview",
                  background=[("selected", "#1f6feb")],
                  foreground=[("selected", "white")])
        style.configure("TNotebook", background=BG, borderwidth=0)
        style.configure("TNotebook.Tab",
                        background=PANEL, foreground=SUBTLE,
                        padding=[14, 6], font=("Segoe UI", 10))
        style.map("TNotebook.Tab",
                  background=[("selected", "#1f6feb")],
                  foreground=[("selected", "white")])

    # ------------------------------------------------------------------ #
    def _build_ui(self):
        # ---- header ----
        header = ttk.Frame(self, padding=(18, 14, 18, 4))
        header.pack(fill="x")
        ttk.Label(header, text="⚽  League Team Radar",
                  style="Head.TLabel").pack(anchor="w")
        ttk.Label(
            header,
            text=("Outward = better. Percentiles vs the league. "
                  "Lower-is-better stats (GA, xGA, PPDA) are inverted."),
            style="Sub.TLabel",
        ).pack(anchor="w")

        # ---- controls ----
        controls = ttk.Frame(self, padding=(18, 10, 18, 6))
        controls.pack(fill="x")

        ttk.Label(controls, text="Team").grid(row=0, column=0, padx=(0, 6))
        self.team_var = tk.StringVar()
        self.team_cb = ttk.Combobox(controls, textvariable=self.team_var,
                                    state="readonly", width=26)
        self.team_cb.grid(row=0, column=1, padx=(0, 22))
        self.team_cb.bind("<<ComboboxSelected>>", lambda _e: self._refresh())

        self.compare_var = tk.BooleanVar(value=False)
        ttk.Checkbutton(controls, text="Compare with",
                        variable=self.compare_var,
                        command=self._on_compare_toggle,
                        ).grid(row=0, column=2, padx=(0, 6))

        self.compare_team_var = tk.StringVar()
        self.compare_cb = ttk.Combobox(controls, textvariable=self.compare_team_var,
                                       state="disabled", width=26)
        self.compare_cb.grid(row=0, column=3, padx=(0, 22))
        self.compare_cb.bind("<<ComboboxSelected>>", lambda _e: self._refresh())

        ttk.Label(controls, text="Rank by").grid(row=0, column=4, padx=(0, 6))
        self.rank_var = tk.StringVar(value=METRIC_LABELS[0])
        self.rank_cb = ttk.Combobox(controls, textvariable=self.rank_var,
                                    values=METRIC_LABELS,
                                    state="readonly", width=18)
        self.rank_cb.grid(row=0, column=5)
        self.rank_cb.bind("<<ComboboxSelected>>", lambda _e: self._refresh())

        # ---- main split: radar | tabs ----
        main = ttk.Frame(self)
        main.pack(fill="both", expand=True, padx=12, pady=(4, 4))
        main.columnconfigure(0, weight=3)
        main.columnconfigure(1, weight=4)
        main.rowconfigure(0, weight=1)

        radar_frame = tk.Frame(main, bg=PANEL,
                               highlightbackground=GRID, highlightthickness=1)
        radar_frame.grid(row=0, column=0, sticky="nsew", padx=(6, 6))

        self.radar_fig = Figure(figsize=(6, 6), dpi=100, facecolor=PANEL)
        self.radar_canvas = FigureCanvasTkAgg(self.radar_fig, master=radar_frame)
        self.radar_canvas.get_tk_widget().pack(fill="both", expand=True,
                                               padx=6, pady=6)

        nb_frame = tk.Frame(main, bg=BG)
        nb_frame.grid(row=0, column=1, sticky="nsew", padx=(6, 6))

        self.notebook = ttk.Notebook(nb_frame)
        self.notebook.pack(fill="both", expand=True)

        self.bar_fig = Figure(figsize=(6, 5), dpi=100, facecolor=PANEL)
        self.bar_canvas = FigureCanvasTkAgg(self.bar_fig, master=self.notebook)
        self.notebook.add(self.bar_canvas.get_tk_widget(), text="vs League avg")

        self.top_fig = Figure(figsize=(6, 5), dpi=100, facecolor=PANEL)
        self.top_canvas = FigureCanvasTkAgg(self.top_fig, master=self.notebook)
        self.notebook.add(self.top_canvas.get_tk_widget(), text="Top 10")

        self.sc_fig = Figure(figsize=(6, 5), dpi=100, facecolor=PANEL)
        self.sc_canvas = FigureCanvasTkAgg(self.sc_fig, master=self.notebook)
        self.notebook.add(self.sc_canvas.get_tk_widget(), text="xG vs xGA")

        # ---- table ----
        table_frame = tk.Frame(self, bg=PANEL,
                               highlightbackground=GRID, highlightthickness=1)
        table_frame.pack(fill="x", padx=18, pady=(4, 14))

        cols = ("metric", "value", "avg", "pct", "better")
        self.tree = ttk.Treeview(table_frame, columns=cols, show="headings",
                                 height=9)
        headings = {
            "metric": ("Metric", 220),
            "value":  ("Value", 110),
            "avg":    ("League avg", 110),
            "pct":    ("Percentile", 110),
            "better": ("Better", 100),
        }
        for c, (text, w) in headings.items():
            self.tree.heading(c, text=text)
            self.tree.column(c, width=w,
                             anchor="w" if c == "metric" else "center")
        self.tree.pack(fill="x", padx=2, pady=2)

    # ------------------------------------------------------------------ #
    def _on_compare_toggle(self):
        state = "readonly" if self.compare_var.get() else "disabled"
        self.compare_cb.configure(state=state)
        self._refresh()

    # ------------------------------------------------------------------ #
    def _populate_team_list(self):
        teams = self.df.sort_values("points", ascending=False)["team"].tolist()
        self.team_cb["values"] = teams
        if self.team_var.get() not in teams:
            self.team_var.set(teams[0])

        self.compare_cb["values"] = teams
        if self.compare_team_var.get() not in teams:
            default_other = next((t for t in teams if t != self.team_var.get()),
                                 teams[0])
            self.compare_team_var.set(default_other)

    # ------------------------------------------------------------------ #
    def _refresh(self):
        self._populate_team_list()
        pool = self.df
        row_a = pool[pool["team"] == self.team_var.get()].iloc[0]

        row_b = None
        if self.compare_var.get():
            picked = self.compare_team_var.get()
            if picked and picked != row_a["team"]:
                row_b = pool[pool["team"] == picked].iloc[0]

        self._draw_radar(pool, row_a, row_b)
        self._draw_bar(pool, row_a)
        self._draw_top(pool, row_a)
        self._draw_scatter(pool, row_a)
        self._draw_table(pool, row_a)

    # ------------------------------------------------------------------ #
    def _draw_radar(self, pool, row_a, row_b):
        self.radar_fig.clear()
        ax = self.radar_fig.add_subplot(111, polar=True)
        ax.set_facecolor(PANEL)

        n = len(METRIC_LABELS)
        angles = np.linspace(0, 2 * np.pi, n, endpoint=False).tolist()
        angles += angles[:1]

        ax.plot(angles, [50] * (n + 1), color=SUBTLE, lw=1,
                ls=(0, (2, 3)), zorder=1)
        ax.plot(angles, [100] * (n + 1), color=GRID, lw=1, zorder=1)

        def poly(row, color, label):
            vals = [percentile(pool[col], row[col], hib)
                    for col, hib in METRICS.values()]
            vals += vals[:1]
            ax.plot(angles, vals, color=color, lw=2.2, label=label, zorder=3)
            ax.fill(angles, vals, color=color, alpha=0.22, zorder=2)

        poly(row_a, COLOR_A, row_a["team"])
        if row_b is not None:
            poly(row_b, COLOR_B, row_b["team"])

        ax.set_xticks(angles[:-1])
        ax.set_xticklabels(METRIC_LABELS, color=FG, fontsize=9)
        ax.set_ylim(0, 100)
        ax.set_yticks([20, 40, 60, 80, 100])
        ax.set_yticklabels(["20", "40", "60", "80", "100"],
                           color=SUBTLE, fontsize=8)
        ax.tick_params(pad=8)
        ax.grid(color=GRID, lw=0.6)
        ax.spines["polar"].set_color(GRID)

        legend = ax.legend(loc="lower center",
                           bbox_to_anchor=(0.5, -0.16),
                           ncol=2, frameon=False, fontsize=10)
        for txt in legend.get_texts():
            txt.set_color(FG)

        self.radar_fig.tight_layout()
        self.radar_canvas.draw_idle()

    # ------------------------------------------------------------------ #
    def _draw_bar(self, pool, row_a):
        self.bar_fig.clear()
        ax = self.bar_fig.add_subplot(111)
        ax.set_facecolor(PANEL)

        labels = METRIC_LABELS[::-1]
        player_vals = [row_a[col] for col, _ in METRICS.values()][::-1]
        avg_vals = [pool[col].mean() for col, _ in METRICS.values()][::-1]

        y = np.arange(len(labels))
        h = 0.38
        ax.barh(y + h / 2, avg_vals,    height=h, color="#6e7681",
                label="League avg")
        ax.barh(y - h / 2, player_vals, height=h, color=COLOR_A,
                label=row_a["team"])

        ax.set_yticks(y)
        ax.set_yticklabels(labels, color=FG, fontsize=9)
        ax.tick_params(axis="x", colors=SUBTLE)
        ax.set_title("Per-match output vs league average",
                     color=FG, fontsize=11, pad=10)
        ax.grid(axis="x", color=GRID, lw=0.6, alpha=0.6)
        ax.set_axisbelow(True)
        for spine in ax.spines.values():
            spine.set_color(GRID)

        leg = ax.legend(loc="lower right", frameon=False, fontsize=9)
        for txt in leg.get_texts():
            txt.set_color(FG)

        self.bar_fig.tight_layout()
        self.bar_canvas.draw_idle()

    # ------------------------------------------------------------------ #
    def _draw_top(self, pool, row_a):
        self.top_fig.clear()
        ax = self.top_fig.add_subplot(111)
        ax.set_facecolor(PANEL)

        label = self.rank_var.get()
        col, hib = METRICS[label]

        top = pool.sort_values(col, ascending=not hib).head(10).iloc[::-1]
        colors = [COLOR_A if t == row_a["team"] else "#6e7681"
                  for t in top["team"]]

        y = np.arange(len(top))
        ax.barh(y, top[col].values, color=colors)
        ax.set_yticks(y)
        ax.set_yticklabels(top["team"].values, color=FG, fontsize=9)
        ax.tick_params(axis="x", colors=SUBTLE)
        ax.set_title(f"Top 10 — {label}", color=FG, fontsize=11, pad=10)
        ax.grid(axis="x", color=GRID, lw=0.6, alpha=0.6)
        ax.set_axisbelow(True)
        for spine in ax.spines.values():
            spine.set_color(GRID)

        self.top_fig.tight_layout()
        self.top_canvas.draw_idle()

    # ------------------------------------------------------------------ #
    def _draw_scatter(self, pool, row_a):
        self.sc_fig.clear()
        ax = self.sc_fig.add_subplot(111)
        ax.set_facecolor(PANEL)

        ax.scatter(pool["xg_per_match"], pool["xga_per_match"],
                   s=60, color="#6e7681", alpha=0.65, label="League")
        ax.scatter([row_a["xg_per_match"]], [row_a["xga_per_match"]],
                   s=180, color=COLOR_A, edgecolor="white", linewidth=1.4,
                   label=row_a["team"], zorder=5)

        for _, r in pool.iterrows():
            ax.annotate(r["team"], (r["xg_per_match"], r["xga_per_match"]),
                        color=SUBTLE, fontsize=7,
                        xytext=(4, 3), textcoords="offset points")

        ax.set_xlabel("xG / match", color=FG, fontsize=9)
        ax.set_ylabel("xGA / match  (lower = better)", color=FG, fontsize=9)
        ax.set_title("Attack vs Defence", color=FG, fontsize=11, pad=10)
        ax.tick_params(colors=SUBTLE)
        ax.grid(color=GRID, lw=0.6, alpha=0.6)
        ax.set_axisbelow(True)
        for spine in ax.spines.values():
            spine.set_color(GRID)

        leg = ax.legend(loc="upper right", frameon=False, fontsize=9)
        for txt in leg.get_texts():
            txt.set_color(FG)

        self.sc_fig.tight_layout()
        self.sc_canvas.draw_idle()

    # ------------------------------------------------------------------ #
    def _draw_table(self, pool, row_a):
        for i in self.tree.get_children():
            self.tree.delete(i)

        for label, (col, hib) in METRICS.items():
            pct = percentile(pool[col], row_a[col], hib)
            self.tree.insert("", "end", values=(
                label,
                f"{row_a[col]:.2f}",
                f"{pool[col].mean():.2f}",
                f"{int(round(pct))}th",
                "↑ higher" if hib else "↓ lower",
            ))


# --------------------------------------------------------------------------- #
def main():
    df = load_data(CSV_PATH)
    app = Dashboard(df)
    app.mainloop()


if __name__ == "__main__":
    main()