import csv
import math
import sys
import threading
from collections import defaultdict
from pathlib import Path
import tkinter as tk
from tkinter import ttk, messagebox

# ==============================================================================
# 1. CONSTANTS & DATA LOGIC
# ==============================================================================

BASE_DIR = Path(__file__).parent
CSV_PATH = BASE_DIR / "premier league data - player data.csv"
CSV_PATH_2025 = BASE_DIR / "premier league data - player data 2025.csv"
CSV_PATH_2024 = BASE_DIR / "premier league data - player data 2024.csv"
CSV_PATH_2023 = BASE_DIR / "premier league data - player data 2023.csv"
GK_CSV_PATH = BASE_DIR / "premier league data - goalkeepers.csv"

STAT_GROUPS = {
    "General": ["Player", "Nation", "Pos", "Squad", "Age", "Born"],
    "Playing Time": ["MP", "Starts", "Min", "90s"],
    "Attacking": ["Gls", "Ast", "G+A", "G-PK", "PK", "PKatt"],
    "Discipline": ["CrdY", "CrdR"],
    "Per 90 Stats": ["Gls_P90", "Ast_P90", "G+A_P90", "G-PK_P90", "G+A-PK_P90"],
}

GK_STAT_GROUPS = {
    "General": ["Player", "Nation", "Pos", "Squad", "Age", "Born"],
    "Playing Time": ["MP", "Starts", "Min", "90s"],
    "Goalkeeping": ["GA", "GA90", "SoTA", "Saves", "Save%", "CS", "CS%", "PKatt", "PKA", "PKsv", "PKm"],
}

DISPLAY_NAMES = {
    "Player": "Player", "Nation": "Nation", "Pos": "Position", "Squad": "Squad",
    "Age": "Age", "Born": "Born", "MP": "Matches Played", "Starts": "Starts",
    "Min": "Minutes", "90s": "90s Played", "Gls": "Goals", "Ast": "Assists",
    "G+A": "Goals + Assists", "G-PK": "Non-PK Goals", "PK": "Penalty Goals",
    "PKatt": "Penalty Attempts", "CrdY": "Yellow Cards", "CrdR": "Red Cards",
    "Gls_P90": "Goals per 90", "Ast_P90": "Assists per 90",
    "G+A_P90": "G+A per 90", "G-PK_P90": "Non-PK Goals per 90",
    "G+A-PK_P90": "G+A-PK per 90",
}
GK_DISPLAY_NAMES = {
    "GA": "Goals Against", "GA90": "Goals Against per 90",
    "SoTA": "Shots on Target Against", "Saves": "Saves",
    "Save%": "Save Percentage", "CS": "Clean Sheets", "CS%": "Clean Sheet %",
    "PKatt": "Penalty Attempts", "PKA": "Penalty Kicks Allowed",
    "PKsv": "Penalty Saves", "PKm": "Penalty Misses",
}

NUMERIC_STATS = ("MP", "Starts", "Min", "90s", "Gls", "Ast", "G+A", "G-PK", "PK", "PKatt", "CrdY", "CrdR")
METADATA_STATS = ("Player", "Nation", "Pos", "Squad", "Age", "Born")
PER_90_DENOM = "90s"

LEAGUE_TABLE_TAB_HEADERS = [
    "Club", "MP", "W", "D", "L", "GF", "GA", "GD", "Pts"
]


def _safe_float(value: str) -> float:
    try:
        return float(value.replace(",", ""))
    except (ValueError, TypeError):
        return 0.0


def _get_primary_position(player: dict[str, str]) -> str:
    pos = player.get("Pos", "")
    return pos.split(",")[0].strip().upper() if "," in pos else pos.strip().upper()


def _parse_csv_file(*paths: Path, year: str = "", progress_callback=None) -> list[dict[str, str]]:
    players: list[dict[str, str]] = []
    counts: dict[str, int] = defaultdict(int)
    for path in paths:
        if not path.exists():
            if progress_callback:
                progress_callback(None)
            continue
        try:
            with open(path, "r", encoding="utf-8") as f:
                reader = csv.reader(f)
                raw_headers = next(reader)
                headers = []
                counts.clear()
                for h in raw_headers:
                    counts[h] += 1
                    headers.append(f"{h}_P90" if counts[h] > 1 else h)
                for row in reader:
                    if len(row) == len(headers) and row[0] != "Rk":
                        entry = dict(zip(headers, row))
                        if year:
                            entry["_year"] = year
                        players.append(entry)
        except (IOError, csv.Error):
            pass
        if progress_callback:
            progress_callback(None)
    return players


def _load_gk_data() -> dict[str, dict[str, str]]:
    gk: dict[str, dict[str, str]] = {}
    if not GK_CSV_PATH.exists():
        return gk
    try:
        with open(GK_CSV_PATH, "r", encoding="utf-8") as f:
            reader = csv.reader(f)
            raw_headers = next(reader)
            headers = []
            counts: dict[str, int] = defaultdict(int)
            for h in raw_headers:
                counts[h] += 1
                headers.append(f"{h}_P90" if counts[h] > 1 else h)
            for row in reader:
                if len(row) == len(headers):
                    p = dict(zip(headers, row))
                    nm = p.get("Player", "").strip()
                    if nm:
                        gk[nm] = p
    except (IOError, csv.Error):
        pass
    return gk


def _compute_per_90_stats(players: list[dict[str, str]]) -> None:
    for p in players:
        games = _safe_float(p.get(PER_90_DENOM, "0"))
        if games <= 0:
            continue
        p["Gls_P90"] = f"{_safe_float(p.get('Gls','0')) / games:.2f}"
        p["Ast_P90"] = f"{_safe_float(p.get('Ast','0')) / games:.2f}"
        p["G+A_P90"] = f"{_safe_float(p.get('G+A','0')) / games:.2f}"
        p["G-PK_P90"] = f"{_safe_float(p.get('G-PK','0')) / games:.2f}"
        p["G+A-PK_P90"] = f"{_safe_float(p.get('G+A-PK','0')) / games:.2f}"


def _combine_records(base: dict[str, str], new: dict[str, str]) -> dict[str, str]:
    combined = dict(base)
    for k, v in new.items():
        if k in METADATA_STATS:
            combined[k] = v
        elif k in NUMERIC_STATS:
            combined[k] = str(_safe_float(base.get(k, "0")) + _safe_float(v))
        else:
            combined.setdefault(k, v)
    return combined


def load_all_players(progress_callback=None) -> tuple[list[dict[str, str]], dict[str, list[dict[str, str]]]]:
    base = _parse_csv_file(CSV_PATH, progress_callback=progress_callback)
    p2025 = _parse_csv_file(CSV_PATH_2025, year="2025", progress_callback=progress_callback)
    p2024 = _parse_csv_file(CSV_PATH_2024, year="2024", progress_callback=progress_callback)
    p2023 = _parse_csv_file(CSV_PATH_2023, year="2023", progress_callback=progress_callback)
    yearly = {"2025": p2025, "2024": p2024, "2023": p2023}
    for yr_key, yr_list in yearly.items():
        deduped: dict[str, dict[str, str]] = {}
        for p in yr_list:
            name = p.get("Player", "").strip()
            if not name:
                continue
            deduped[name] = _combine_records(deduped.get(name, {}), p)
        yearly[yr_key] = list(deduped.values())
    for yr in yearly.values():
        _compute_per_90_stats(yr)
    merged: dict[str, dict[str, str]] = {}
    for p in base:
        name = p.get("Player", "").strip()
        if not name:
            continue
        merged[name] = _combine_records(merged.get(name, {}), p)

    for yr in (p2023, p2024, p2025):
        for p in yr:
            name = p.get("Player", "").strip()
            if not name:
                continue
            merged[name] = _combine_records(merged[name], p) if name in merged else p
    players = list(merged.values())
    _compute_per_90_stats(players)
    for p in players:
        nm = p.get("Player", "").strip()
        if nm:
            p["name_lower"] = nm.lower()
            p["squad_lower"] = p.get("Squad", "").strip().lower()
            p["name_stripped"] = nm
    gk_data = _load_gk_data()
    for p in players:
        if _get_primary_position(p) == "GK":
            for k, v in gk_data.get(p.get("name_stripped", ""), {}).items():
                if k not in p or not p[k]:
                    p[k] = v
    if progress_callback:
        progress_callback(None)
    return players, yearly


def calculate_ratings(players: list[dict[str, str]], **kwargs) -> dict[str, float]:
    return {}


def _league_table_qualification(rank: int) -> str:
    if rank <= 4:
        return "UEFA Champions League group stage"
    if rank == 5:
        return "Europa League group stage"
    if rank >= 18:
        return "Relegation"
    return ""


# ==============================================================================
# 2. TKINTER UI COMPONENTS
# ==============================================================================

class CollapsibleGroup(ttk.Frame):
    def __init__(self, parent, title: str, children: list[tuple[str, str]]):
        super().__init__(parent)
        self._title = title
        self.expanded = True
        
        self.header_btn = ttk.Button(self, text=f"▼ {title}", command=self.toggle, style='Header.TButton')
        self.header_btn.pack(fill=tk.X)
        
        self.body = ttk.Frame(self)
        self.body.pack(fill=tk.X)
        
        for label, value in children:
            row = ttk.Frame(self.body)
            row.pack(fill=tk.X, pady=1)
            
            lbl = ttk.Label(row, text=label, width=25, anchor='w')
            lbl.pack(side=tk.LEFT, padx=5)
            
            val_lbl = ttk.Label(row, text=str(value), anchor='e')
            val_lbl.pack(side=tk.RIGHT, padx=5, fill=tk.X, expand=True)

    def toggle(self):
        self.expanded = not self.expanded
        symbol = "▼" if self.expanded else "▶"
        self.header_btn.config(text=f"{symbol} {self._title}")
        if self.expanded:
            self.body.pack(fill=tk.X)
        else:
            self.body.pack_forget()


class StatsPanel(ttk.Frame):
    def __init__(self, parent):
        super().__init__(parent)
        
        self.canvas = tk.Canvas(self, borderwidth=0, highlightthickness=0, background="#f8fafc")
        self.scrollbar = ttk.Scrollbar(self, orient="vertical", command=self.canvas.yview)
        self.scrollable_frame = ttk.Frame(self.canvas)
        
        self.scrollable_frame.bind(
            "<Configure>",
            lambda e: self.canvas.configure(scrollregion=self.canvas.bbox("all"))
        )
        
        self.canvas.create_window((0, 0), window=self.scrollable_frame, anchor="nw")
        self.canvas.configure(yscrollcommand=self.scrollbar.set)
        
        self.canvas.pack(side="left", fill="both", expand=True)
        self.scrollbar.pack(side="right", fill="y")
        
        for widget in (self.canvas, self.scrollable_frame):
            widget.bind("<MouseWheel>", self._on_mousewheel)
            widget.bind("<Button-4>", self._on_mousewheel)
            widget.bind("<Button-5>", self._on_mousewheel)

    def _on_mousewheel(self, event):
        if sys.platform == 'win32':
            self.canvas.yview_scroll(int(-1*(event.delta/120)), "units")
        else:
            if event.num == 4:
                self.canvas.yview_scroll(-1, "units")
            elif event.num == 5:
                self.canvas.yview_scroll(1, "units")

    def show_player(self, player: dict):
        for widget in self.scrollable_frame.winfo_children():
            widget.destroy()
            
        name = player.get("name_stripped", player.get("Player", ""))
        
        name_lbl = ttk.Label(self.scrollable_frame, text=name, font=("Segoe UI", 16, "bold"))
        name_lbl.pack(anchor='w', pady=(0, 5))
        
        is_gk = _get_primary_position(player) == "GK" and bool(player.get("GA"))
        stat_groups = GK_STAT_GROUPS if is_gk else STAT_GROUPS
        display_names = {**DISPLAY_NAMES, **GK_DISPLAY_NAMES} if is_gk else DISPLAY_NAMES
        
        for group_name, keys in stat_groups.items():
            children = []
            for key in keys:
                if key in player and player[key]:
                    value = player[key]
                    children.append((display_names.get(key, key), value))
            
            if children:
                group = CollapsibleGroup(self.scrollable_frame, group_name, children)
                group.pack(fill=tk.X, pady=5)


class StatsDashboard(ttk.Frame):
    def __init__(self, parent, players: list[dict], yearly: dict):
        super().__init__(parent)
        self.pack(fill=tk.BOTH, expand=True)
        
        self.all_players = players
        self.yearly_players = yearly
        self.players = players
        
        self._filtered_players = list(self.players)
        
        self._setup_styles()
        self._build_ui()
        self._refresh_all()
        
    def _setup_styles(self):
        style = ttk.Style(self)
        style.theme_use('clam')
        
        style.configure("TFrame", background="#f8fafc")
        style.configure("TLabel", background="#f8fafc", font=("Segoe UI", 10))
        style.configure("Header.TLabel", font=("Segoe UI", 20, "bold"), background="#f8fafc")
        style.configure("Subheader.TLabel", font=("Segoe UI", 10), foreground="#475569", background="#f8fafc")
        style.configure("Card.TFrame", background="white", relief="solid", borderwidth=1)
        style.configure("Card.TLabel", background="white")
        
        style.configure("Treeview", rowheight=28, font=("Segoe UI", 10))
        style.configure("Treeview.Heading", font=("Segoe UI", 10, "bold"))
        
        style.configure("Header.TButton", font=("Segoe UI", 10, "bold"), foreground="#4f46e5")

    def _build_ui(self):
        main_frame = ttk.Frame(self, padding=20)
        main_frame.pack(fill=tk.BOTH, expand=True)
        
        header_card = ttk.Frame(main_frame, style="Card.TFrame", padding=20)
        header_card.pack(fill=tk.X, pady=(0, 15))
        ttk.Label(header_card, text="Premier League Player Stats", style="Header.TLabel").pack(anchor='w')
        ttk.Label(header_card, text="Browse player statistics across seasons", style="Subheader.TLabel").pack(anchor='w')
        
        search_card = ttk.Frame(main_frame, style="Card.TFrame", padding=15)
        search_card.pack(fill=tk.X, pady=(0, 15))
        
        ttk.Label(search_card, text="Search Player:").pack(side=tk.LEFT, padx=(0, 5))
        self.search_var = tk.StringVar()
        self.search_var.trace("w", self._on_search_changed)
        self.search_entry = ttk.Entry(search_card, textvariable=self.search_var, width=30)
        self.search_entry.pack(side=tk.LEFT, padx=(0, 15))
        
        ttk.Label(search_card, text="Period:").pack(side=tk.LEFT, padx=(15, 5))
        self.year_var = tk.StringVar(value="All")
        self.year_combo = ttk.Combobox(search_card, textvariable=self.year_var, values=["All", "2023", "2024", "2025"], state="readonly", width=10)
        self.year_combo.pack(side=tk.LEFT)
        self.year_combo.bind("<<ComboboxSelected>>", self._on_year_change)
        
        self.notebook = ttk.Notebook(main_frame)
        self.notebook.pack(fill=tk.BOTH, expand=True)
        
        # Tab 1: Player Explorer
        self.player_tab = ttk.Frame(self.notebook)
        self.notebook.add(self.player_tab, text="Player Explorer")
        
        paned = ttk.PanedWindow(self.player_tab, orient=tk.HORIZONTAL)
        paned.pack(fill=tk.BOTH, expand=True)
        
        list_frame = ttk.Frame(paned)
        paned.add(list_frame, weight=1)
        
        self.player_tree = ttk.Treeview(list_frame, columns=("Name", "Pos", "Squad"), show="headings")
        self.player_tree.heading("Name", text="Player")
        self.player_tree.heading("Pos", text="Position")
        self.player_tree.heading("Squad", text="Squad")
        
        self.player_tree.column("Name", width=200)
        self.player_tree.column("Pos", width=80)
        self.player_tree.column("Squad", width=150)
        
        tree_scroll = ttk.Scrollbar(list_frame, orient="vertical", command=self.player_tree.yview)
        self.player_tree.configure(yscrollcommand=tree_scroll.set)
        
        self.player_tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        tree_scroll.pack(side=tk.RIGHT, fill=tk.Y)
        
        self.player_tree.bind("<<TreeviewSelect>>", self._on_player_select)
        
        detail_frame = ttk.Frame(paned)
        paned.add(detail_frame, weight=1)
        
        self.stats_panel = StatsPanel(detail_frame)
        self.stats_panel.pack(fill=tk.BOTH, expand=True)
        
        # Tab 2: Heat Map
        self.heat_tab = ttk.Frame(self.notebook)
        self.notebook.add(self.heat_tab, text="Heat Map")
        
        self.heat_tree = ttk.Treeview(self.heat_tab, columns=("Player", "Pos", "Squad", "Gls/90", "Ast/90"), show="headings")
        for col in ("Player", "Pos", "Squad", "Gls/90", "Ast/90"):
            self.heat_tree.heading(col, text=col)
            self.heat_tree.column(col, width=120 if col not in ("Player", "Squad") else 200)
            
        heat_scroll = ttk.Scrollbar(self.heat_tab, orient="vertical", command=self.heat_tree.yview)
        self.heat_tree.configure(yscrollcommand=heat_scroll.set)
        self.heat_tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        heat_scroll.pack(side=tk.RIGHT, fill=tk.Y)
        
        # Tab 3: Rankings
        self.rank_tab = ttk.Frame(self.notebook)
        self.notebook.add(self.rank_tab, text="Rankings")
        
        self.rank_tree = ttk.Treeview(self.rank_tab, columns=("#", "Player", "Pos", "Squad"), show="headings")
        for col in ("#", "Player", "Pos", "Squad"):
            self.rank_tree.heading(col, text=col)
            self.rank_tree.column(col, width=120 if col not in ("Player", "Squad") else 200)
            
        rank_scroll = ttk.Scrollbar(self.rank_tab, orient="vertical", command=self.rank_tree.yview)
        self.rank_tree.configure(yscrollcommand=rank_scroll.set)
        self.rank_tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        rank_scroll.pack(side=tk.RIGHT, fill=tk.Y)
        
        # Tab 4: League Table
        self.ltable_tab = ttk.Frame(self.notebook)
        self.notebook.add(self.ltable_tab, text="League Table")
        
        self.ltable_tree = ttk.Treeview(self.ltable_tab, columns=LEAGUE_TABLE_TAB_HEADERS, show="headings")
        for col in LEAGUE_TABLE_TAB_HEADERS:
            self.ltable_tree.heading(col, text=col)
            self.ltable_tree.column(col, width=100 if col != "Club" else 200)
            
        ltable_scroll = ttk.Scrollbar(self.ltable_tab, orient="vertical", command=self.ltable_tree.yview)
        self.ltable_tree.configure(yscrollcommand=ltable_scroll.set)
        self.ltable_tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        ltable_scroll.pack(side=tk.RIGHT, fill=tk.Y)

    def _on_search_changed(self, *args):
        if hasattr(self, '_search_after_id'):
            self.after_cancel(self._search_after_id)
        self._search_after_id = self.after(200, self._apply_search)

    def _apply_search(self):
        term = self.search_var.get().strip().lower()
        if term:
            self._filtered_players = [
                p for p in self.players
                if term in p.get("name_lower", "") or term in p.get("squad_lower", "")
            ]
        else:
            self._filtered_players = list(self.players)
        self._refresh_player_tree()

    def _on_year_change(self, event=None):
        year = self.year_var.get()
        if year == "All":
            self.players = self.all_players
        else:
            self.players = self.yearly_players.get(year, [])
        
        self._filtered_players = list(self.players)
        self._refresh_all()

    def _on_player_select(self, event=None):
        selected = self.player_tree.selection()
        if not selected:
            return
        item = self.player_tree.item(selected[0])
        player_name = item['values'][0]
        
        player = next((p for p in self.players if p.get("name_stripped") == player_name), None)
        if player:
            self.stats_panel.show_player(player)

    def _refresh_all(self):
        self._refresh_player_tree()
        self._refresh_heat_map()
        self._refresh_rankings()
        self._refresh_league_table()

    def _refresh_player_tree(self):
        self.player_tree.delete(*self.player_tree.get_children())
        sorted_players = sorted(self._filtered_players, key=lambda p: p.get("name_stripped", ""))
        
        for p in sorted_players:
            name = p.get("name_stripped", "")
            self.player_tree.insert("", tk.END, values=(
                name, _get_primary_position(p), p.get("Squad", "")
            ))

    def _refresh_heat_map(self):
        self.heat_tree.delete(*self.heat_tree.get_children())
        if not self.players:
            return
            
        sorted_players = sorted(self.players, key=lambda p: _safe_float(p.get("Gls_P90", "0")), reverse=True)
        
        for p in sorted_players:
            name = p.get("name_stripped", "")
            gls = _safe_float(p.get("Gls_P90", "0"))
            ast = _safe_float(p.get("Ast_P90", "0"))
            
            intensity = gls + ast
            max_val = max((_safe_float(p.get("Gls_P90", "0")) + _safe_float(p.get("Ast_P90", "0")) for p in self.players), default=1.0)
            norm = intensity / max_val if max_val > 0 else 0
            
            if norm > 0.75:
                tag = "heat_high"
            elif norm > 0.4:
                tag = "heat_med"
            else:
                tag = "heat_low"
                
            self.heat_tree.insert("", tk.END, values=(
                name, _get_primary_position(p), p.get("Squad", ""),
                f"{gls:.2f}", f"{ast:.2f}"
            ), tags=(tag,))
            
        self.heat_tree.tag_configure("heat_high", background="#0047b3", foreground="white")
        self.heat_tree.tag_configure("heat_med", background="#668df2", foreground="white")
        self.heat_tree.tag_configure("heat_low", background="#eef2ff", foreground="black")

    def _refresh_rankings(self):
        self.rank_tree.delete(*self.rank_tree.get_children())
        if not self.players:
            return
            
        sorted_players = sorted(self.players, key=lambda p: p.get("name_stripped", ""))
        seen = set()
        
        idx = 1
        for p in sorted_players:
            name = p.get("name_stripped", "")
            if name and name not in seen:
                seen.add(name)
                self.rank_tree.insert("", tk.END, values=(
                    idx, name, _get_primary_position(p), p.get("Squad", "")
                ))
                idx += 1

    def _refresh_league_table(self):
        self.ltable_tree.delete(*self.ltable_tree.get_children())
        
        clubs = [
            "Bournemouth", "Arsenal", "Aston Villa", "Brentford", "Brighton",
            "Chelsea", "Coventry", "Palace", "Everton", "Fulham",
            "Hull", "Ipswich Town", "Leeds", "Liverpool", "Man City",
            "Man United", "Newcastle", "Nottm Forest", "Sunderland", "Spurs"
        ]
        
        for rank, club in enumerate(clubs, start=1):
            qual = _league_table_qualification(rank)
            tag = ""
            if "Champions League" in qual: tag = "ucl"
            elif "Europa League" in qual: tag = "uel"
            elif "Relegation" in qual: tag = "rel"
            
            self.ltable_tree.insert("", tk.END, values=(
                club, "0", "0", "0", "0", "0", "0", "0", "0"
            ), tags=(tag,))
            
        self.ltable_tree.tag_configure("ucl", background="#dcfce7")
        self.ltable_tree.tag_configure("uel", background="#dbeafe")
        self.ltable_tree.tag_configure("rel", background="#fee2e2")


class LoadingDialog(tk.Toplevel):
    def __init__(self, parent):
        super().__init__(parent)
        self.title("Loading")
        self.geometry("480x160")
        self.resizable(False, False)
        self.transient(parent)
        self.grab_set()
        
        self.protocol("WM_DELETE_WINDOW", lambda: None)
        
        frame = ttk.Frame(self, padding=30)
        frame.pack(fill=tk.BOTH, expand=True)
        
        self.status_label = ttk.Label(frame, text="Loading player data...", font=("Segoe UI", 12, "bold"))
        self.status_label.pack(pady=(0, 15))
        
        self.progress = ttk.Progressbar(frame, orient="horizontal", length=300, mode="determinate")
        self.progress.pack(pady=(0, 10))
        
        self.pct_label = ttk.Label(frame, text="0%", font=("Segoe UI", 10))
        self.pct_label.pack()
        
        self.center()

    def center(self):
        self.update_idletasks()
        width = self.winfo_width()
        height = self.winfo_height()
        x = (self.winfo_screenwidth() // 2) - (width // 2)
        y = (self.winfo_screenheight() // 2) - (height // 2)
        self.geometry(f"+{x}+{y}")

    def update_progress(self, value):
        if value is None:
            return
        self.progress['value'] = value * 100
        self.pct_label.config(text=f"{int(value * 100)}%")
        self.update_idletasks()


class LoaderThread(threading.Thread):
    def __init__(self, progress_callback, finish_callback, error_callback):
        super().__init__()
        self.progress_callback = progress_callback
        self.finish_callback = finish_callback
        self.error_callback = error_callback
        self.daemon = True

    def run(self):
        try:
            players, yearly = load_all_players(progress_callback=self.progress_callback)
            self.progress_callback(1.0)
            self.finish_callback(players, yearly)
        except Exception as e:
            self.error_callback(str(e))


def load_or_show_dashboard():
    root = tk.Tk()
    root.title("Premier League Player Stats")
    root.geometry("1360x860")
    root.withdraw()
    
    dialog = LoadingDialog(root)
    
    def on_progress(f=None):
        root.after(0, dialog.update_progress, f)
        
    def on_finished(players, yearly):
        def _show():
            dialog.destroy()
            root.deiconify()
            StatsDashboard(root, players, yearly)
        root.after(0, _show)
        
    def on_error(err):
        def _show_err():
            dialog.destroy()
            messagebox.showerror("Error", f"Error loading data: {err}")
            root.destroy()
        root.after(0, _show_err)
        
    thread = LoaderThread(on_progress, on_finished, on_error)
    thread.start()
    
    root.mainloop()


if __name__ == "__main__":
    load_or_show_dashboard()
