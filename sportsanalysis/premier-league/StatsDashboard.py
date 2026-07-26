import tkinter as tk
from tkinter import ttk
import csv
import json
import hashlib
import os
from collections import defaultdict
from tempfile import gettempdir

CSV_PATH = r"C:\Users\liam\Documents\GitHub\all-of-my-code\sportsanalysis\premier-league\premier league data - player data.csv"
CACHE_PATH = os.path.join(gettempdir(), "premier_league_ratings_cache.json")

STAT_GROUPS = {
    "General": ["Rk", "Player", "Nation", "Pos", "Squad", "Age", "Born"],
    "Playing Time": ["MP", "Starts", "Min", "90s"],
    "Attacking": ["Gls", "Ast", "G+A", "G-PK", "PK", "PKatt"],
    "Discipline": ["CrdY", "CrdR"],
    "Per 90 Stats": ["Gls_P90", "Ast_P90", "G+A_P90", "G-PK_P90", "G+A-PK_P90"],
    "Score": ["Rating"],
}

SCORED_STATS = {
    "FW": ["Gls_P90", "Ast_P90", "G+A_P90", "G-PK_P90", "G+A-PK_P90"],
    "MF": ["Gls_P90", "Ast_P90", "G+A_P90", "G-PK_P90", "G+A-PK_P90"],
    "DF": ["Ast_P90", "G+A_P90", "G-PK_P90"],
    "GK": ["Gls_P90", "Ast_P90", "G+A_P90", "G-PK_P90", "G+A-PK_P90"],
}

DISPLAY_NAMES = {
    "Rk": "Rank",
    "Player": "Player",
    "Nation": "Nation",
    "Pos": "Position",
    "Squad": "Squad",
    "Age": "Age",
    "Born": "Born",
    "MP": "Matches Played",
    "Starts": "Starts",
    "Min": "Minutes",
    "90s": "90s Played",
    "Gls": "Goals",
    "Ast": "Assists",
    "G+A": "Goals + Assists",
    "G-PK": "Non-PK Goals",
    "PK": "Penalty Goals",
    "PKatt": "Penalty Attempts",
    "CrdY": "Yellow Cards",
    "CrdR": "Red Cards",
    "Gls_P90": "Goals per 90",
    "Ast_P90": "Assists per 90",
    "G+A_P90": "G+A per 90",
    "G-PK_P90": "Non-PK Goals per 90",
    "G+A-PK_P90": "G+A-PK per 90",
    "Rating": "Overall Rating",
}


def _get_csv_hash() -> str:
    with open(CSV_PATH, "rb") as f:
        return hashlib.md5(f.read()).hexdigest()


def _safe_float(value: str) -> float:
    try:
        return float(value.replace(",", ""))
    except (ValueError, TypeError):
        return 0.0


def _get_primary_position(player: dict[str, str]) -> str:
    pos = player.get("Pos", "")
    if "," in pos:
        return pos.split(",")[0].strip()
    return pos.strip().upper()


def calculate_ratings(players: list[dict[str, str]], progress_callback=None) -> dict[str, float]:
    ratings: dict[str, list[float]] = defaultdict(list)

    pos_groups: dict[str, list[dict[str, str]]] = defaultdict(list)
    for p in players:
        pos_groups[_get_primary_position(p)].append(p)

    total_operations = sum(len(stats) * len(group) for pos_key, group in pos_groups.items() for stats in [SCORED_STATS.get(pos_key, [])])
    current = 0

    for pos_key, group in pos_groups.items():
        stat_keys = SCORED_STATS.get(pos_key, [])
        if not stat_keys:
            continue

        for stat_key in stat_keys:
            values = []
            for p in group:
                val = _safe_float(p.get(stat_key, ""))
                values.append((p["Player"].strip(), val))

            values.sort(key=lambda x: x[1], reverse=True)
            n = len(values)
            for rank, (name, val) in enumerate(values, start=1):
                percentile = 1.0 - (rank - 1) / max(n - 1, 1)
                ratings[name].append(percentile)

                current += 1
                if progress_callback and total_operations > 0:
                    progress_callback(current / total_operations)

    overall: dict[str, float] = {}
    for name, percentiles in ratings.items():
        if percentiles:
            overall[name] = (sum(percentiles) / len(percentiles)) * 10.0

    return overall


class SplashScreen:
    def __init__(self, root: tk.Tk, total_players: int):
        self.root = root
        self.root.title("Loading Stats")
        self.root.geometry("400x120")
        self.root.resizable(False, False)

        self.label = ttk.Label(root, text=f"Calculating ratings for {total_players} players...", font=("Segoe UI", 11))
        self.label.pack(pady=20)

        self.progress = ttk.Progressbar(root, length=300, mode="determinate")
        self.progress.pack(pady=10)

        self.status = ttk.Label(root, text="", font=("Segoe UI", 9))
        self.status.pack()

    def update_progress(self, fraction: float) -> None:
        self.progress["value"] = fraction * 100
        self.status.config(text=f"{fraction * 100:.0f}%")
        self.root.update_idletasks()


class StatsDashboard:
    def __init__(self, root: tk.Tk, ratings: dict[str, float]):
        self.root = root
        self.root.title("Premier League Player Stats Dashboard")
        self.root.geometry("1100x700")

        self.players: list[dict[str, str]] = []
        self.ratings = ratings
        self.load_data()

        self._build_ui()
        self._refresh_player_list()

    def load_data(self) -> None:
        with open(CSV_PATH, "r", encoding="utf-8") as f:
            reader = csv.reader(f)
            raw_headers = next(reader)

            headers = []
            counts: dict[str, int] = defaultdict(int)
            for h in raw_headers:
                counts[h] += 1
                if counts[h] > 1:
                    headers.append(f"{h}_P90")
                else:
                    headers.append(h)

            for row in reader:
                if len(row) == len(headers):
                    self.players.append(dict(zip(headers, row)))

    def _build_ui(self) -> None:
        main = ttk.Frame(self.root)
        main.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)

        search_frame = ttk.Frame(main)
        search_frame.pack(fill=tk.X, pady=(0, 10))

        ttk.Label(search_frame, text="Search Player:", font=("Segoe UI", 11, "bold")).pack(side=tk.LEFT)
        self.search_var = tk.StringVar()
        self.search_entry = ttk.Entry(
            search_frame, textvariable=self.search_var, width=50, font=("Segoe UI", 11)
        )
        self.search_entry.pack(side=tk.LEFT, padx=10)
        self.search_entry.bind("<KeyRelease>", lambda e: self._refresh_player_list())
        self.search_entry.bind("<Return>", self._show_first_match)

        ttk.Button(search_frame, text="Clear", command=self._clear_search).pack(side=tk.LEFT, padx=5)

        content = ttk.PanedWindow(main, orient=tk.HORIZONTAL)
        content.pack(fill=tk.BOTH, expand=True)

        left = ttk.Frame(content)
        content.add(left, weight=1)

        ttk.Label(left, text="Players", font=("Segoe UI", 10, "bold")).pack(anchor=tk.W, pady=(0, 5))

        self.player_listbox = tk.Listbox(
            left, font=("Segoe UI", 10), activestyle="dotbox", selectbackground="#0078d4"
        )
        self.player_listbox.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        self.player_listbox.bind("<<ListboxSelect>>", self._on_player_select)

        scrollbar = ttk.Scrollbar(left, orient=tk.VERTICAL, command=self.player_listbox.yview)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        self.player_listbox.config(yscrollcommand=scrollbar.set)

        right = ttk.Frame(content)
        content.add(right, weight=2)

        ttk.Label(right, text="Player Statistics", font=("Segoe UI", 10, "bold")).pack(anchor=tk.W, pady=(0, 5))

        columns = ("stat", "value")
        self.stats_tree = ttk.Treeview(right, columns=columns, show="headings", height=25)
        self.stats_tree.heading("stat", text="Statistic")
        self.stats_tree.heading("value", text="Value")
        self.stats_tree.column("stat", width=220, anchor=tk.W)
        self.stats_tree.column("value", width=120, anchor=tk.CENTER)
        self.stats_tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        self.stats_tree.bind("<Double-1>", self._on_stat_double_click)

        stats_scroll = ttk.Scrollbar(right, orient=tk.VERTICAL, command=self.stats_tree.yview)
        stats_scroll.pack(side=tk.RIGHT, fill=tk.Y)
        self.stats_tree.config(yscrollcommand=stats_scroll.set)

        self.stats_tree.tag_configure("group", background="#e5e5e5", font=("Segoe UI", 10, "bold"))
        self.stats_tree.tag_configure("row", font=("Segoe UI", 10))
        self.stats_tree.tag_configure("highlight", background="#fff4ce")

    def _refresh_player_list(self) -> None:
        term = self.search_var.get().strip().lower()
        self.player_listbox.delete(0, tk.END)

        filtered = []
        for p in self.players:
            name = p.get("Player", "")
            squad = p.get("Squad", "")
            if term in name.lower() or term in squad.lower():
                filtered.append(p)
                display = f"{name}  |  {squad}  |  {p.get('Pos', '')}"
                self.player_listbox.insert(tk.END, display)

        self._filtered_players = filtered

    def _clear_search(self) -> None:
        self.search_var.set("")
        self._refresh_player_list()

    def _show_first_match(self, event=None) -> None:
        if not self._filtered_players:
            return
        self.player_listbox.selection_clear(0, tk.END)
        self.player_listbox.selection_set(0)
        self.player_listbox.activate(0)
        self._on_player_select(None)

    def _on_player_select(self, event) -> None:
        selection = self.player_listbox.curselection()
        if not selection or not hasattr(self, "_filtered_players"):
            return

        idx = selection[0]
        if idx >= len(self._filtered_players):
            return

        player = self._filtered_players[idx]
        self._display_stats(player)

    def _on_stat_double_click(self, event) -> None:
        selection = self.stats_tree.selection()
        if not selection:
            return

        item = selection[0]
        values = self.stats_tree.item(item, "values")
        display_name = values[0].strip()

        key = None
        for k, v in DISPLAY_NAMES.items():
            if v == display_name:
                key = k
                break

        if not key or key in ("Player",):
            return

        sorted_players = sorted(
            self.players,
            key=lambda p: _safe_float(p.get(key, "")),
            reverse=True,
        )

        win = tk.Toplevel(self.root)
        win.title(f"All Players - {display_name} (Descending)")
        win.geometry("700x500")

        cols = ("rank", "player", "squad", "value")
        tree = ttk.Treeview(win, columns=cols, show="headings")
        tree.heading("rank", text="#")
        tree.heading("player", text="Player")
        tree.heading("squad", text="Squad")
        tree.heading("value", text=display_name)
        tree.column("rank", width=40, anchor=tk.CENTER)
        tree.column("player", width=220, anchor=tk.W)
        tree.column("squad", width=180, anchor=tk.W)
        tree.column("value", width=100, anchor=tk.CENTER)
        tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

        scroll = ttk.Scrollbar(win, orient=tk.VERTICAL, command=tree.yview)
        scroll.pack(side=tk.RIGHT, fill=tk.Y)
        tree.config(yscrollcommand=scroll.set)

        for i, p in enumerate(sorted_players, start=1):
            tree.insert(
                "",
                tk.END,
                values=(i, p.get("Player", ""), p.get("Squad", ""), p.get(key, "")),
            )

    def _display_stats(self, player: dict[str, str]) -> None:
        for item in self.stats_tree.get_children():
            self.stats_tree.delete(item)

        player_rating = self.ratings.get(player["Player"].strip(), 0.0)
        rating_display = f"{player_rating:.1f}/10"

        is_first_row = True
        for group_name, keys in STAT_GROUPS.items():
            group_id = self.stats_tree.insert("", tk.END, values=(f"  {group_name}", ""), tags=("group",))
            for key in keys:
                if key == "Rating":
                    display = DISPLAY_NAMES.get(key, key)
                    value = rating_display
                    tag = "highlight" if is_first_row else "row"
                    self.stats_tree.insert("", tk.END, values=(f"    {display}", value), tags=(tag,))
                    is_first_row = False
                elif key in player:
                    display = DISPLAY_NAMES.get(key, key)
                    value = player[key]
                    tag = "highlight" if is_first_row else "row"
                    self.stats_tree.insert("", tk.END, values=(f"    {display}", value), tags=(tag,))
                    is_first_row = False


def load_or_calculate_ratings(players: list[dict[str, str]]) -> dict[str, float]:
    csv_hash = _get_csv_hash()
    cache_file = CACHE_PATH
    ratings_version = "1.1"

    if os.path.exists(cache_file):
        try:
            with open(cache_file, "r", encoding="utf-8") as f:
                cache = json.load(f)
            if cache.get("csv_hash") == csv_hash and cache.get("version") == ratings_version:
                return cache.get("ratings", {})
        except (json.JSONDecodeError, IOError):
            pass

    splash_root = tk.Tk()
    splash_root.withdraw()

    splash = tk.Toplevel(splash_root)
    splash.title("Loading")
    splash.geometry("400x100")
    splash.resizable(False, False)

    ttk.Label(splash, text=f"Calculating ratings for {len(players)} players...", font=("Segoe UI", 11)).pack(pady=15)
    progress = ttk.Progressbar(splash, length=300, mode="determinate")
    progress.pack(pady=5)
    status_label = ttk.Label(splash, text="0%", font=("Segoe UI", 9))
    status_label.pack()

    splash.update()

    def progress_callback(fraction: float) -> None:
        progress["value"] = fraction * 100
        status_label.config(text=f"{fraction * 100:.0f}%")
        splash.update_idletasks()

    ratings = calculate_ratings(players, progress_callback)

    splash.destroy()
    splash_root.destroy()

    try:
        with open(cache_file, "w", encoding="utf-8") as f:
            json.dump({"csv_hash": csv_hash, "version": ratings_version, "ratings": ratings}, f)
    except IOError:
        pass

    return ratings


def main() -> None:
    players: list[dict[str, str]] = []
    with open(CSV_PATH, "r", encoding="utf-8") as f:
        reader = csv.reader(f)
        raw_headers = next(reader)
        headers = []
        counts: dict[str, int] = defaultdict(int)
        for h in raw_headers:
            counts[h] += 1
            if counts[h] > 1:
                headers.append(f"{h}_P90")
            else:
                headers.append(h)
        for row in reader:
            if len(row) == len(headers):
                players.append(dict(zip(headers, row)))

    ratings = load_or_calculate_ratings(players)

    root = tk.Tk()
    app = StatsDashboard(root, ratings)
    root.mainloop()


if __name__ == "__main__":
    main()
