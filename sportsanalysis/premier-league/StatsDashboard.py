from pathlib import Path

import tkinter as tk
from tkinter import ttk
import csv
import json
import hashlib
import os
from collections import defaultdict
from tempfile import gettempdir

CSV_PATH = Path(__file__).parent / "premier league data - player data.csv"
CACHE_PATH = Path(gettempdir()) / "premier_league_ratings_cache.json"

STAT_GROUPS = {
    "General": ["Player", "Nation", "Pos", "Squad", "Age", "Born"],
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

TEAM_POWER_RANKINGS = {
    "Arsenal": 97.5,
    "Manchester City": 96.8,
    "Manchester United": 95.8,
    "Aston Villa": 95.5,
    "Bournemouth": 95.2,
    "Liverpool": 92.7,
    "Nottingham Forest": 92.5,
    "Brentford": 92.1,
    "West Ham United": 91.8,
    "Sunderland": 91.7,
    "Newcastle United": 91.6,
    "Fulham": 91.5,
    "Brighton & Hove Albion": 91.4,
    "Leeds United": 91.1,
    "Tottenham Hotspur": 90.0,
    "Crystal Palace": 89.8,
    "Chelsea": 89.6,
    "Everton": 89.6,
    "Wolverhampton Wanderers": 86.0,
    "Burnley": 84.7,
}

TEAM_NAME_ALIASES = {
    "West Ham": "West Ham United",
    "Newcastle": "Newcastle United",
    "Brighton": "Brighton & Hove Albion",
    "Tottenham": "Tottenham Hotspur",
    "Wolves": "Wolverhampton Wanderers",
    "Wolverhampton": "Wolverhampton Wanderers",
}

MEAN_TEAM_RATING = sum(TEAM_POWER_RANKINGS.values()) / len(TEAM_POWER_RANKINGS)
TEAM_RATING_SCALE = 3.0
DEFAULT_TEAM_RATING = MEAN_TEAM_RATING
MIN_90S = 3.0
MIN_90S_RATIO = 0.15

GK_CSV_PATH = Path(__file__).parent / "premier league data - goalkeepers.csv"

GK_STAT_GROUPS = {
    "General": ["Player", "Nation", "Pos", "Squad", "Age", "Born"],
    "Playing Time": ["MP", "Starts", "Min", "90s"],
    "Goalkeeping": ["GA", "GA90", "SoTA", "Saves", "Save%", "CS", "CS%", "PKatt", "PKA", "PKsv", "PKm"],
}

GK_SCORED_STATS = {
    "GK": {
        "Save%": True,
        "CS%": True,
        "CS": True,
        "GA90": False,
    }
}

GK_DISPLAY_NAMES = {
    "GA": "Goals Against",
    "GA90": "Goals Against per 90",
    "SoTA": "Shots on Target Against",
    "Saves": "Saves",
    "Save%": "Save Percentage",
    "CS": "Clean Sheets",
    "CS%": "Clean Sheet %",
    "PKatt": "Penalty Attempts",
    "PKA": "Penalty Kicks Allowed",
    "PKsv": "Penalty Saves",
    "PKm": "Penalty Misses",
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


def _normalize_team_name(name: str) -> str:
    return TEAM_NAME_ALIASES.get(name.strip(), name.strip())


def _get_min_90s_threshold(players: list[dict[str, str]]) -> float:
    avg_90s = sum(_safe_float(p.get("90s", "0")) for p in players) / max(len(players), 1)
    return max(MIN_90S, avg_90s * MIN_90S_RATIO)


def _load_gk_data() -> dict[str, dict[str, str]]:
    gk_players: dict[str, dict[str, str]] = {}
    if not GK_CSV_PATH.exists():
        return gk_players
    try:
        with open(GK_CSV_PATH, "r", encoding="utf-8") as f:
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
                    player = dict(zip(headers, row))
                    name = player.get("Player", "").strip()
                    if name:
                        gk_players[name] = player
    except (IOError, csv.Error):
        pass
    return gk_players


def load_all_players() -> list[dict[str, str]]:
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

    gk_data = _load_gk_data()
    for p in players:
        if _get_primary_position(p) == "GK":
            gk_info = gk_data.get(p["Player"].strip(), {})
            for k, v in gk_info.items():
                if k not in p or not p[k]:
                    p[k] = v

    return players


def apply_team_adjustment(raw_ratings: dict[str, float], players: list[dict[str, str]]) -> dict[str, float]:
    player_teams: dict[str, str] = {}
    for p in players:
        raw_name = p.get("Player", "").strip()
        raw_squad = p.get("Squad", "")
        if raw_name:
            player_teams[raw_name] = _normalize_team_name(raw_squad)

    adjusted: dict[str, float] = {}
    for name, raw in raw_ratings.items():
        team = player_teams.get(name, "")
        team_rating = TEAM_POWER_RANKINGS.get(team, DEFAULT_TEAM_RATING)
        team_factor = (MEAN_TEAM_RATING - team_rating) / MEAN_TEAM_RATING
        adjustment = (raw - 5.0) * team_factor * TEAM_RATING_SCALE
        adjusted[name] = raw + adjustment

    return adjusted


def calculate_ratings(players: list[dict[str, str]], progress_callback=None) -> dict[str, float]:
    ratings: dict[str, list[float]] = defaultdict(list)

    pos_groups: dict[str, list[dict[str, str]]] = defaultdict(list)
    for p in players:
        pos_groups[_get_primary_position(p)].append(p)

    total_operations = 0
    for pos_key, group in pos_groups.items():
        stat_keys = SCORED_STATS.get(pos_key, [])
        gk_stat_keys = list(GK_SCORED_STATS.get(pos_key, {}).keys())
        total_operations += len(stat_keys) * len(group) + len(gk_stat_keys) * len(group)
    
    current = 0

    for pos_key, group in pos_groups.items():
        stat_keys = SCORED_STATS.get(pos_key, [])
        gk_directions = GK_SCORED_STATS.get(pos_key, {})
        gk_stat_keys = list(gk_directions.keys())

        if not stat_keys and not gk_stat_keys:
            continue

        avg_90s = sum(_safe_float(p.get("90s", "0")) for p in group) / max(len(group), 1)
        min_90s_threshold = max(MIN_90S, avg_90s * MIN_90S_RATIO)

        for stat_key in stat_keys:
            values = []
            for p in group:
                if _safe_float(p.get("90s", "0")) < min_90s_threshold:
                    continue
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

        for stat_key in gk_stat_keys:
            values = []
            for p in group:
                if _safe_float(p.get("90s", "0")) < min_90s_threshold:
                    continue
                val = _safe_float(p.get(stat_key, "0"))
                values.append((p["Player"].strip(), val))

            higher_is_better = gk_directions.get(stat_key, True)
            values.sort(key=lambda x: x[1], reverse=higher_is_better)
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
        self.root.title("Loading")
        self.root.geometry("480x160")
        self.root.resizable(False, False)
        self.root.configure(bg="#f1f5f9")

        main = ttk.Frame(root, padding=(40, 32, 40, 32))
        main.pack(fill=tk.BOTH, expand=True)

        self.label = ttk.Label(main, text=f"Calculating ratings for {total_players} players...", font=("Segoe UI Variable", 12))
        self.label.pack(pady=(0, 20))

        self.progress = ttk.Progressbar(main, length=400, mode="determinate")
        self.progress.pack(pady=(0, 12))

        self.status = ttk.Label(main, text="0%", font=("Segoe UI Variable", 10), foreground="#475569")
        self.status.pack()

    def update_progress(self, fraction: float) -> None:
        self.progress["value"] = fraction * 100
        self.status.config(text=f"{fraction * 100:.0f}%")
        self.root.update_idletasks()


class StatsDashboard:
    def __init__(self, root: tk.Tk, ratings: dict[str, float]):
        self.root = root
        self.root.title("Premier League Player Stats")
        self.root.geometry("1280x800")
        self.root.configure(bg="#f1f5f9")
        
        self._setup_styles()

        self.players: list[dict[str, str]] = []
        self.ratings = ratings
        self.load_data()

        self._build_ui()
        self._refresh_player_list()

    def load_data(self) -> None:
        self.players = load_all_players()

    def _setup_styles(self) -> None:
        style = ttk.Style()
        style.theme_use("clam")

        bg = "#f1f5f9"
        card = "#ffffff"
        primary = "#4f46e5"
        primary_hover = "#4338ca"
        text = "#0f172a"
        text_secondary = "#475569"
        border = "#e2e8f0"
        accent_soft = "#eef2ff"
        
        style.configure(".", background=bg, foreground=text, font=("Segoe UI Variable", 10))
        style.configure("TFrame", background=bg)
        style.configure("Card.TFrame", background=card, relief=tk.FLAT)
        style.configure("TLabel", background=bg, foreground=text, font=("Segoe UI Variable", 10))
        style.configure("Header.TLabel", background=bg, foreground=text, font=("Segoe UI Variable", 20, "bold"))
        style.configure("Subheader.TLabel", background=bg, foreground=text_secondary, font=("Segoe UI Variable", 10))
        style.configure("TButton", font=("Segoe UI Variable", 10), padding=(16, 10), background=card)
        style.map("TButton", background=[("active", "#f8fafc")])
        style.configure("TEntry", fieldbackground="white", bordercolor=border, padding=10, insertcolor=text)
        style.configure("TProgressbar", background=primary, troughcolor=bg, borderwidth=0)
        
        style.configure("Treeview", 
                       background=card, 
                       foreground=text, 
                       fieldbackground=card, 
                       rowheight=40,
                       borderwidth=0,
                       relief=tk.FLAT)
        style.configure("Treeview.Heading", 
                       background=bg, 
                       foreground=text_secondary, 
                       font=("Segoe UI Variable", 10, "bold"), 
                       padding=(12, 10),
                       borderwidth=0)
        style.map("Treeview", 
                  background=[("selected", primary)],
                  foreground=[("selected", "white")])
        style.map("Treeview.Heading",
                  background=[("active", bg)])

    def _build_ui(self) -> None:
        main = ttk.Frame(self.root, padding=(32, 28, 32, 28))
        main.pack(fill=tk.BOTH, expand=True)

        header_card = ttk.Frame(main, style="Card.TFrame")
        header_card.pack(fill=tk.X, pady=(0, 24))
        header_inner = ttk.Frame(header_card, padding=(28, 24, 28, 24))
        header_inner.pack(fill=tk.X)
        
        ttk.Label(
            header_inner,
            text="Premier League Player Stats",
            style="Header.TLabel",
        ).pack(anchor=tk.W)
        
        ttk.Label(
            header_inner,
            text="Search players, view stats, and double-click any stat to see league rankings",
            style="Subheader.TLabel",
        ).pack(anchor=tk.W, pady=(6, 0))

        search_card = ttk.Frame(main, style="Card.TFrame")
        search_card.pack(fill=tk.X, pady=(0, 20))
        search_inner = ttk.Frame(search_card, padding=(20, 16, 20, 16))
        search_inner.pack(fill=tk.X)

        ttk.Label(search_inner, text="Search Player:", font=("Segoe UI Variable", 11)).pack(side=tk.LEFT)
        self.search_var = tk.StringVar()
        self.search_entry = ttk.Entry(
            search_inner, textvariable=self.search_var, width=60, font=("Segoe UI Variable", 11)
        )
        self.search_entry.pack(side=tk.LEFT, padx=16)
        self.search_entry.bind("<KeyRelease>", lambda e: self._refresh_player_list())
        self.search_entry.bind("<Return>", self._show_first_match)

        ttk.Button(search_inner, text="Clear", command=self._clear_search).pack(side=tk.LEFT, padx=8)

        content = ttk.PanedWindow(main, orient=tk.HORIZONTAL)
        content.pack(fill=tk.BOTH, expand=True)

        left_card = ttk.Frame(content, style="Card.TFrame")
        content.add(left_card, weight=1)
        left_inner = ttk.Frame(left_card, padding=(16, 16, 16, 16))
        left_inner.pack(fill=tk.BOTH, expand=True)

        list_header = ttk.Frame(left_inner)
        list_header.pack(fill=tk.X, pady=(0, 12))
        ttk.Label(list_header, text="Players", font=("Segoe UI Variable", 12, "bold")).pack(anchor=tk.W)

        self.player_listbox = tk.Listbox(
            left_inner, 
            font=("Segoe UI Variable", 10), 
            activestyle="dotbox", 
            selectbackground="#4f46e5",
            selectforeground="white",
            borderwidth=0,
            highlightthickness=1,
            highlightbackground="#e2e8f0",
            relief=tk.FLAT,
            bg="white",
            fg="#0f172a",
            selectborderwidth=0,
        )
        self.player_listbox.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, ipady=8)
        self.player_listbox.bind("<<ListboxSelect>>", self._on_player_select)

        scrollbar = ttk.Scrollbar(left_inner, orient=tk.VERTICAL, command=self.player_listbox.yview)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        self.player_listbox.config(yscrollcommand=scrollbar.set)

        right_card = ttk.Frame(content, style="Card.TFrame")
        content.add(right_card, weight=2)
        right_inner = ttk.Frame(right_card, padding=(16, 16, 16, 16))
        right_inner.pack(fill=tk.BOTH, expand=True)

        stats_header = ttk.Frame(right_inner)
        stats_header.pack(fill=tk.X, pady=(0, 12))
        ttk.Label(stats_header, text="Player Statistics", font=("Segoe UI Variable", 12, "bold")).pack(anchor=tk.W)

        columns = ("stat", "value")
        self.stats_tree = ttk.Treeview(right_inner, columns=columns, show="headings", height=22)
        self.stats_tree.heading("stat", text="Statistic")
        self.stats_tree.heading("value", text="Value")
        self.stats_tree.column("stat", width=280, anchor=tk.W)
        self.stats_tree.column("value", width=160, anchor=tk.CENTER)
        self.stats_tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        self.stats_tree.bind("<Double-1>", self._on_stat_double_click)

        stats_scroll = ttk.Scrollbar(right_inner, orient=tk.VERTICAL, command=self.stats_tree.yview)
        stats_scroll.pack(side=tk.RIGHT, fill=tk.Y)
        self.stats_tree.config(yscrollcommand=stats_scroll.set)

        self.stats_tree.tag_configure("group", background="#f8fafc", font=("Segoe UI Variable", 10, "bold"), foreground="#475569")
        self.stats_tree.tag_configure("row", font=("Segoe UI Variable", 10), background="#ffffff")
        self.stats_tree.tag_configure("alt", font=("Segoe UI Variable", 10), background="#f8fafc")
        self.stats_tree.tag_configure("highlight", background="#eef2ff", foreground="#4f46e5")

    def _refresh_player_list(self) -> None:
        term = self.search_var.get().strip().lower()
        self.player_listbox.delete(0, tk.END)

        filtered = []
        for p in self.players:
            name = p.get("Player", "")
            squad = p.get("Squad", "")
            if term in name.lower() or term in squad.lower():
                filtered.append(p)

        for display_idx, p in enumerate(filtered):
            name = p.get("Player", "")
            squad = p.get("Squad", "")
            display = f"{name}  |  {squad}  |  {p.get('Pos', '')}"
            self.player_listbox.insert(tk.END, display)
            if display_idx % 2 == 0:
                self.player_listbox.itemconfig(tk.END, background="#f8fafc")
            else:
                self.player_listbox.itemconfig(tk.END, background="#ffffff")

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

        if key is None:
            for k, v in GK_DISPLAY_NAMES.items():
                if v == display_name:
                    key = k
                    break

        if not key or key in ("Player",):
            return

        min_90s_threshold = _get_min_90s_threshold(self.players)
        eligible_players = [p for p in self.players if _safe_float(p.get("90s", "0")) >= min_90s_threshold]

        if key == "Rating":
            sorted_players = sorted(
                eligible_players,
                key=lambda p: self.ratings.get(p["Player"].strip(), 0.0),
                reverse=True,
            )
        else:
            gk_directions = GK_SCORED_STATS.get("GK", {})
            higher_is_better = gk_directions.get(key, True)
            default_val = 0.0 if higher_is_better else float("inf")
            
            sorted_players = sorted(
                eligible_players,
                key=lambda p: _safe_float(p.get(key, "0")) if key in p else default_val,
                reverse=higher_is_better,
            )

        win = tk.Toplevel(self.root)
        win.title(f"All Players - {display_name}")
        win.geometry("800x600")
        win.configure(bg="#f1f5f9")

        info_frame = ttk.Frame(win, padding=(24, 20, 24, 0))
        info_frame.pack(fill=tk.X)

        title_label = ttk.Label(
            info_frame,
            text=f"All Players — {display_name}",
            font=("Segoe UI Variable", 16, "bold"),
        )
        title_label.pack(anchor=tk.W)

        if key == "Rating":
            subtitle = f"Sorted by team-adjusted overall rating (players with ≥ {min_90s_threshold:.1f} 90s)"
        else:
            subtitle = f"Sorted by raw match data (players with ≥ {min_90s_threshold:.1f} 90s)"
        sub_label = ttk.Label(info_frame, text=subtitle, font=("Segoe UI Variable", 9), foreground="#475569")
        sub_label.pack(anchor=tk.W, pady=(4, 0))

        tree_frame = ttk.Frame(win, style="Card.TFrame")
        tree_frame.pack(fill=tk.BOTH, expand=True, padx=24, pady=16)

        cols = ("rank", "player", "squad", "value")
        tree = ttk.Treeview(tree_frame, columns=cols, show="headings", height=22)
        tree.heading("rank", text="#")
        tree.heading("player", text="Player")
        tree.heading("squad", text="Squad")
        tree.heading("value", text=display_name)
        tree.column("rank", width=60, anchor=tk.CENTER)
        tree.column("player", width=280, anchor=tk.W)
        tree.column("squad", width=220, anchor=tk.W)
        tree.column("value", width=140, anchor=tk.CENTER)
        tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=8, pady=8)

        scroll = ttk.Scrollbar(tree_frame, orient=tk.VERTICAL, command=tree.yview)
        scroll.pack(side=tk.RIGHT, fill=tk.Y)
        tree.config(yscrollcommand=scroll.set)

        tree.tag_configure("odd", background="#f8fafc")
        tree.tag_configure("even", background="#ffffff")

        for i, p in enumerate(sorted_players, start=1):
            tag = "odd" if i % 2 == 1 else "even"
            raw_value = p.get(key, "") if key != "Rating" else f"{self.ratings.get(p['Player'].strip(), 0.0):.1f}"
            tree.insert(
                "",
                tk.END,
                values=(i, p.get("Player", ""), p.get("Squad", ""), raw_value),
                tags=(tag,),
            )

    def _display_stats(self, player: dict[str, str]) -> None:
        for item in self.stats_tree.get_children():
            self.stats_tree.delete(item)

        player_rating = self.ratings.get(player["Player"].strip(), 0.0)
        rating_display = f"{player_rating:.1f}/10"

        is_first_row = True
        row_index = 0
        pos = _get_primary_position(player)
        
        if pos == "GK" and player.get("GA"):
            stat_groups = GK_STAT_GROUPS
            display_names = {**DISPLAY_NAMES, **GK_DISPLAY_NAMES}
        else:
            stat_groups = STAT_GROUPS
            display_names = DISPLAY_NAMES
        
        for group_name, keys in stat_groups.items():
            group_id = self.stats_tree.insert("", tk.END, values=(f"  {group_name}", ""), tags=("group",))
            for key in keys:
                if key == "Rating":
                    display = display_names.get(key, key)
                    value = rating_display
                    tag = "highlight" if is_first_row else ("alt" if row_index % 2 == 0 else "row")
                    self.stats_tree.insert("", tk.END, values=(f"    {display}", value), tags=(tag,))
                    is_first_row = False
                    row_index += 1
                elif key in player:
                    display = display_names.get(key, key)
                    value = player[key]
                    tag = "highlight" if is_first_row else ("alt" if row_index % 2 == 0 else "row")
                    self.stats_tree.insert("", tk.END, values=(f"    {display}", value), tags=(tag,))
                    is_first_row = False
                    row_index += 1


def load_or_calculate_ratings(players: list[dict[str, str]]) -> dict[str, float]:
    csv_hash = _get_csv_hash()
    cache_file = CACHE_PATH
    ratings_version = "1.4"

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
    splash.geometry("480x160")
    splash.resizable(False, False)
    splash.configure(bg="#f1f5f9")

    main = ttk.Frame(splash, padding=(40, 32, 40, 32))
    main.pack(fill=tk.BOTH, expand=True)

    ttk.Label(main, text=f"Calculating ratings for {len(players)} players...", font=("Segoe UI Variable", 12)).pack(pady=(0, 20))
    progress = ttk.Progressbar(main, length=400, mode="determinate")
    progress.pack(pady=(0, 12))
    status_label = ttk.Label(main, text="0%", font=("Segoe UI Variable", 10), foreground="#475569")
    status_label.pack()

    splash.update()

    def progress_callback(fraction: float) -> None:
        progress["value"] = fraction * 100
        status_label.config(text=f"{fraction * 100:.0f}%")
        splash.update_idletasks()

    ratings = calculate_ratings(players, progress_callback)
    ratings = apply_team_adjustment(ratings, players)

    splash.destroy()
    splash_root.destroy()

    try:
        with open(cache_file, "w", encoding="utf-8") as f:
            json.dump({"csv_hash": csv_hash, "version": ratings_version, "ratings": ratings}, f)
    except IOError:
        pass

    return ratings


def main() -> None:
    players = load_all_players()

    ratings = load_or_calculate_ratings(players)

    root = tk.Tk()
    app = StatsDashboard(root, ratings)
    root.mainloop()


if __name__ == "__main__":
    main()
