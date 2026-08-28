import pandas as pd
import numpy as np
import tkinter as tk
from tkinter import ttk, filedialog, messagebox
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
import matplotlib.pyplot as plt
from sklearn.model_selection import train_test_split
from sklearn.ensemble import RandomForestRegressor, RandomForestClassifier
from sklearn.metrics import mean_squared_error, r2_score, accuracy_score
from sklearn.preprocessing import LabelEncoder
from sklearn.linear_model import LinearRegression
import warnings
import itertools
import threading
import json
import os
import re
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor, as_completed

warnings.filterwarnings('ignore')

# ---------- League Power Ratings ----------
LEAGUE_RATINGS = {
    'eng Premier League': 92.5,
    'de Bundesliga': 87.1,
    'es La Liga': 86.7,
    'it Serie A': 86.3,
    'fr Ligue 1': 85.8,
}
DEFAULT_RATING = 85.0

# ------------------- Helper functions -------------------
def load_single_csv(file_path):
    """Load and clean a CSV, adding LeagueRating."""
    df = pd.read_csv(file_path, encoding='utf-8')
    df = df[df['Rk'] != 'Rk'].copy()
    for col in df.columns:
        if df[col].dtype == object:
            df[col] = df[col].str.replace(',', '').astype(float, errors='ignore')
    if 'Min' not in df.columns and '90s' in df.columns:
        df['Min'] = df['90s'] * 90
    if 'Ast' not in df.columns:
        df['Ast'] = np.nan
    if 'CrdY' not in df.columns:
        df['CrdY'] = np.nan
    if 'PK' not in df.columns:
        df['PK'] = np.nan
    if 'PKatt' not in df.columns:
        df['PKatt'] = np.nan
    if 'G+A' not in df.columns and 'Gls' in df.columns and 'Ast' in df.columns:
        df['G+A'] = df['Gls'] + df['Ast']
    essential = ['Gls', 'Min', 'Age']
    for col in essential:
        if col not in df.columns:
            raise ValueError(f"Missing essential column: {col} in {file_path}")
    df = df.dropna(subset=essential)
    df['Age'] = pd.to_numeric(df['Age'], errors='coerce')
    df['LeagueRating'] = df['Comp'].map(LEAGUE_RATINGS).fillna(DEFAULT_RATING)
    return df

def extract_year_from_filename(filename):
    match = re.search(r'\b(19|20)\d{2}\b', filename)
    if match:
        return int(match.group())
    return None

def load_state(folder_path):
    best_weights_path = Path(folder_path) / 'best_weights.json'
    loaded_files_path = Path(folder_path) / 'loaded_files.json'
    best_weights = {'FW': 1.0, 'MF': 1.0, 'DF': 1.0, 'GK': 1.0}
    loaded_files = []
    if best_weights_path.exists():
        with open(best_weights_path, 'r') as f:
            best_weights = json.load(f)
    if loaded_files_path.exists():
        with open(loaded_files_path, 'r') as f:
            loaded_files = json.load(f)
    return best_weights, loaded_files

def save_state(folder_path, best_weights, loaded_files):
    best_weights_path = Path(folder_path) / 'best_weights.json'
    loaded_files_path = Path(folder_path) / 'loaded_files.json'
    with open(best_weights_path, 'w') as f:
        json.dump(best_weights, f, indent=2)
    with open(loaded_files_path, 'w') as f:
        json.dump(loaded_files, f, indent=2)

# ------------------- Main Application -------------------
class PlayerAnalyticsApp:
    def __init__(self, root):
        self.root = root
        self.root.title("Football Analytics – League-Adjusted All-Time & Future Stars")
        self.root.geometry("1400x1050")

        self.df = None
        self.folder_path = ''
        self.best_weights = {'FW': 1.0, 'MF': 1.0, 'DF': 1.0, 'GK': 1.0}
        self.loaded_files = []
        self.is_training = False
        self.features = []
        self.model = None
        self.target = 'Gls'

        self.create_widgets()

    # ---------- GUI Creation ----------
    def create_widgets(self):
        # Top frame
        top_frame = tk.Frame(self.root)
        top_frame.pack(fill='x', padx=10, pady=5)

        tk.Label(top_frame, text="Data Folder:").pack(side=tk.LEFT, padx=5)
        self.folder_entry = tk.Entry(top_frame, width=60)
        self.folder_entry.pack(side=tk.LEFT, padx=5)
        btn_browse = tk.Button(top_frame, text="Browse", command=self.browse_folder)
        btn_browse.pack(side=tk.LEFT, padx=5)
        btn_load = tk.Button(top_frame, text="Load New Data", command=self.load_new_data, bg='lightblue')
        btn_load.pack(side=tk.LEFT, padx=5)

        self.status_label = tk.Label(top_frame, text="No folder selected.", fg='blue')
        self.status_label.pack(side=tk.LEFT, padx=10)

        self.best_weights_label = tk.Label(top_frame, text="Best weights: FW=1.0 MF=1.0 DF=1.0 GK=1.0", fg='darkgreen')
        self.best_weights_label.pack(side=tk.LEFT, padx=10)

        # Notebook
        self.notebook = ttk.Notebook(self.root)
        self.notebook.pack(fill='both', expand=True, padx=5, pady=5)

        # Tabs
        self.tab_data = ttk.Frame(self.notebook)
        self.notebook.add(self.tab_data, text="Data")
        self.setup_data_tab()

        self.tab_stats = ttk.Frame(self.notebook)
        self.notebook.add(self.tab_stats, text="Statistics")
        self.setup_stats_tab()

        self.tab_graphs = ttk.Frame(self.notebook)
        self.notebook.add(self.tab_graphs, text="Graphs")
        self.setup_graphs_tab()

        self.tab_ml = ttk.Frame(self.notebook)
        self.notebook.add(self.tab_ml, text="Machine Learning")
        self.setup_ml_tab()

        self.tab_incremental = ttk.Frame(self.notebook)
        self.notebook.add(self.tab_incremental, text="Incremental")
        self.setup_incremental_tab()

        self.tab_pos_imp = ttk.Frame(self.notebook)
        self.notebook.add(self.tab_pos_imp, text="Position Importances")
        self.setup_position_importances_tab()

        self.tab_predict = ttk.Frame(self.notebook)
        self.notebook.add(self.tab_predict, text="Predict")
        self.setup_predict_tab()

        self.tab_alltime = ttk.Frame(self.notebook)
        self.notebook.add(self.tab_alltime, text="All-Time & Future Stars")
        self.setup_alltime_tab()

    # ---------- Data Tab ----------
    def setup_data_tab(self):
        frame = self.tab_data
        self.data_tree = ttk.Treeview(frame)
        self.data_tree.pack(fill='both', expand=True, side=tk.LEFT)
        scrollbar = ttk.Scrollbar(frame, orient='vertical', command=self.data_tree.yview)
        scrollbar.pack(side=tk.RIGHT, fill='y')
        self.data_tree.configure(yscrollcommand=scrollbar.set)
        self.info_label = tk.Label(frame, text="No data loaded.")
        self.info_label.pack(side=tk.BOTTOM, pady=5)

    def update_data_tree(self):
        if self.df is None: return
        for item in self.data_tree.get_children(): self.data_tree.delete(item)
        cols = list(self.df.columns)
        self.data_tree['columns'] = cols
        self.data_tree['show'] = 'headings'
        for col in cols:
            self.data_tree.heading(col, text=col)
            self.data_tree.column(col, width=100, anchor='w')
        for idx, row in self.df.head(100).iterrows():
            self.data_tree.insert('', 'end', values=[str(row[col]) for col in cols])
        self.info_label.config(text=f"Loaded {len(self.df)} rows. Showing first 100.")

    # ---------- Statistics Tab ----------
    def setup_stats_tab(self):
        frame = self.tab_stats
        self.stats_text = tk.Text(frame, wrap='none', height=20)
        self.stats_text.pack(fill='both', expand=True, padx=5, pady=5)
        scroll_y = ttk.Scrollbar(frame, orient='vertical', command=self.stats_text.yview)
        scroll_y.pack(side=tk.RIGHT, fill='y')
        self.stats_text.configure(yscrollcommand=scroll_y.set)
        btn_update_stats = tk.Button(frame, text="Update Statistics", command=self.update_stats)
        btn_update_stats.pack(pady=5)

    def update_stats(self):
        if self.df is None:
            self.stats_text.delete(1.0, tk.END); self.stats_text.insert(tk.END, "No data loaded.")
            return
        desc = self.df.describe().to_string()
        pos_counts = self.df['Pos'].value_counts().to_string()
        year_counts = self.df['Year'].value_counts().sort_index().to_string() if 'Year' in self.df.columns else "No Year column"
        self.stats_text.delete(1.0, tk.END)
        self.stats_text.insert(tk.END, f"Data Summary:\n{desc}\n\nPosition counts:\n{pos_counts}\n\nYear distribution:\n{year_counts}")

    # ---------- Graphs Tab ----------
    def setup_graphs_tab(self):
        frame = self.tab_graphs
        control_frame = tk.Frame(frame); control_frame.pack(fill='x', pady=5)
        tk.Label(control_frame, text="Select X:").pack(side=tk.LEFT, padx=5)
        self.x_var = tk.StringVar()
        self.x_combo = ttk.Combobox(control_frame, textvariable=self.x_var, state='readonly')
        self.x_combo.pack(side=tk.LEFT, padx=5)
        tk.Label(control_frame, text="Select Y:").pack(side=tk.LEFT, padx=5)
        self.y_var = tk.StringVar()
        self.y_combo = ttk.Combobox(control_frame, textvariable=self.y_var, state='readonly')
        self.y_combo.pack(side=tk.LEFT, padx=5)
        tk.Label(control_frame, text="Filter Position:").pack(side=tk.LEFT, padx=5)
        self.pos_filter_var = tk.StringVar(value='All')
        self.pos_combo = ttk.Combobox(control_frame, textvariable=self.pos_filter_var, state='readonly')
        self.pos_combo.pack(side=tk.LEFT, padx=5)
        self.pos_combo.bind('<<ComboboxSelected>>', lambda e: self.plot_graph())
        tk.Label(control_frame, text="Filter Year:").pack(side=tk.LEFT, padx=5)
        self.year_filter_var = tk.StringVar(value='All')
        self.year_combo = ttk.Combobox(control_frame, textvariable=self.year_filter_var, state='readonly')
        self.year_combo.pack(side=tk.LEFT, padx=5)
        self.year_combo.bind('<<ComboboxSelected>>', lambda e: self.plot_graph())

        btn_plot = tk.Button(control_frame, text="Plot", command=self.plot_graph)
        btn_plot.pack(side=tk.LEFT, padx=10)

        fig_frame = tk.Frame(frame); fig_frame.pack(fill='both', expand=True)
        self.fig, self.ax = plt.subplots(figsize=(8,6))
        self.canvas = FigureCanvasTkAgg(self.fig, master=fig_frame)
        self.canvas.get_tk_widget().pack(fill='both', expand=True)
        self.x_combo['values'] = []; self.y_combo['values'] = []; self.pos_combo['values'] = ['All']; self.year_combo['values'] = ['All']

    def update_graph_options(self):
        if self.df is None: return
        num_cols = self.df.select_dtypes(include=['float64', 'int64']).columns.tolist()
        self.x_combo['values'] = num_cols; self.y_combo['values'] = num_cols
        if num_cols:
            self.x_var.set(num_cols[0])
            self.y_var.set(num_cols[1] if len(num_cols)>1 else num_cols[0])
        pos_vals = ['All'] + sorted(self.df['Pos'].dropna().unique().tolist())
        self.pos_combo['values'] = pos_vals; self.pos_filter_var.set('All')
        if 'Year' in self.df.columns:
            year_vals = ['All'] + sorted(self.df['Year'].dropna().unique().tolist())
            self.year_combo['values'] = year_vals; self.year_filter_var.set('All')
        else:
            self.year_combo['values'] = ['All']; self.year_filter_var.set('All')

    def plot_graph(self):
        if self.df is None: return
        x_col, y_col = self.x_var.get(), self.y_var.get()
        if not x_col or not y_col: return
        pos_filter = self.pos_filter_var.get()
        year_filter = self.year_filter_var.get()
        data = self.df
        if pos_filter != 'All':
            data = data[data['Pos'] == pos_filter]
        if year_filter != 'All' and 'Year' in data.columns:
            data = data[data['Year'] == int(year_filter)]
        if data.empty:
            messagebox.showinfo("Info", "No data for selected filters.")
            return
        self.ax.clear()
        self.ax.scatter(data[x_col], data[y_col], alpha=0.6, s=10)
        self.ax.set_xlabel(x_col); self.ax.set_ylabel(y_col)
        self.ax.set_title(f"{x_col} vs {y_col} (Pos: {pos_filter}, Year: {year_filter})")
        self.canvas.draw()

    # ---------- Machine Learning Tab ----------
    def setup_ml_tab(self):
        frame = self.tab_ml
        ctrl = tk.Frame(frame); ctrl.pack(side=tk.LEFT, fill='y', padx=10, pady=10)

        tk.Label(ctrl, text="Target Variable:").pack(anchor='w')
        self.target_var = tk.StringVar(value='Gls')
        self.target_combo = ttk.Combobox(ctrl, textvariable=self.target_var, state='readonly')
        self.target_combo.pack(fill='x', pady=5)

        tk.Label(ctrl, text="Model Type:").pack(anchor='w')
        self.model_type_var = tk.StringVar(value='Regression')
        self.model_type_combo = ttk.Combobox(ctrl, textvariable=self.model_type_var,
                                             values=['Regression', 'Classification'], state='readonly')
        self.model_type_combo.pack(fill='x', pady=5)

        tk.Label(ctrl, text="Test Size:").pack(anchor='w')
        self.test_size_var = tk.DoubleVar(value=0.2)
        self.test_size_entry = tk.Entry(ctrl, textvariable=self.test_size_var)
        self.test_size_entry.pack(fill='x', pady=5)

        tk.Label(ctrl, text="Position Weights (manual sliders):").pack(anchor='w', pady=(10,0))
        self.weight_frame = tk.Frame(ctrl); self.weight_frame.pack(fill='x', pady=5)
        self.weight_sliders = {}
        for pos in ['FW', 'MF', 'DF', 'GK']:
            sub = tk.Frame(self.weight_frame); sub.pack(fill='x')
            tk.Label(sub, text=pos, width=5).pack(side=tk.LEFT)
            var = tk.DoubleVar(value=self.best_weights.get(pos, 1.0))
            slider = tk.Scale(sub, from_=0.0, to=5.0, resolution=0.1, orient=tk.HORIZONTAL,
                              variable=var, length=100)
            slider.pack(side=tk.LEFT, fill='x', expand=True)
            self.weight_sliders[pos] = var

        btn_train = tk.Button(ctrl, text="Train Model (manual weights)", command=self.start_training)
        btn_train.pack(pady=5)

        self.progress_bar_ml = ttk.Progressbar(ctrl, length=300, mode='indeterminate')
        self.progress_bar_ml.pack(pady=5)
        self.progress_label_ml = tk.Label(ctrl, text="Ready")
        self.progress_label_ml.pack()

        result_frame = tk.Frame(frame); result_frame.pack(side=tk.RIGHT, fill='both', expand=True, padx=10)
        self.result_text = tk.Text(result_frame, wrap='none', height=20)
        self.result_text.pack(fill='both', expand=True)
        scroll = ttk.Scrollbar(result_frame, orient='vertical', command=self.result_text.yview)
        scroll.pack(side=tk.RIGHT, fill='y')
        self.result_text.configure(yscrollcommand=scroll.set)

        self.fig_imp, self.ax_imp = plt.subplots(figsize=(6,4))
        self.canvas_imp = FigureCanvasTkAgg(self.fig_imp, master=result_frame)
        self.canvas_imp.get_tk_widget().pack(fill='both', expand=True)

    def update_ml_options(self):
        if self.df is None: return
        num_cols = self.df.select_dtypes(include=['float64', 'int64']).columns.tolist()
        self.target_combo['values'] = num_cols
        if 'Gls' in num_cols: self.target_var.set('Gls')

    # ---------- Incremental Tab ----------
    def setup_incremental_tab(self):
        frame = self.tab_incremental
        ctrl = tk.Frame(frame)
        ctrl.pack(fill='x', padx=10, pady=10)

        self.best_weights_display = tk.Label(ctrl, text="Best weights: FW=1.0 MF=1.0 DF=1.0 GK=1.0", font=('Arial', 12))
        self.best_weights_display.pack()

        self.progress_bar_inc = ttk.Progressbar(ctrl, length=400, mode='determinate')
        self.progress_bar_inc.pack(pady=5)
        self.progress_label_inc = tk.Label(ctrl, text="Ready")
        self.progress_label_inc.pack()

        btn_manual_search = tk.Button(ctrl, text="Manual Search (256 random combos)", command=self.start_incremental_search)
        btn_manual_search.pack(pady=5)

        self.inc_log = tk.Text(ctrl, height=15, width=80)
        self.inc_log.pack(fill='both', expand=True, padx=5, pady=5)
        scroll = ttk.Scrollbar(ctrl, orient='vertical', command=self.inc_log.yview)
        scroll.pack(side=tk.RIGHT, fill='y')
        self.inc_log.configure(yscrollcommand=scroll.set)

    # ---------- Folder / Data Loading ----------
    def browse_folder(self):
        folder = filedialog.askdirectory()
        if folder:
            self.folder_entry.delete(0, tk.END)
            self.folder_entry.insert(0, folder)
            self.folder_path = folder
            self.best_weights, self.loaded_files = load_state(folder)
            self.update_best_weights_display()
            self.scan_folder()

    def scan_folder(self):
        if not self.folder_path: return
        folder = Path(self.folder_path)
        csv_files = [f for f in folder.glob('*.csv') if f.is_file()]
        self.status_label.config(text=f"Found {len(csv_files)} CSV files. Loaded: {len(self.loaded_files)}")
        return csv_files

    def load_new_data(self):
        if not self.folder_path:
            messagebox.showerror("Error", "Please select a folder first.")
            return
        folder = Path(self.folder_path)
        all_csv = [f for f in folder.glob('*.csv') if f.is_file()]
        new_files = [f for f in all_csv if str(f) not in self.loaded_files]
        if not new_files:
            messagebox.showinfo("Info", "No new CSV files found.")
            return

        new_dfs = []
        for f in new_files:
            try:
                df = load_single_csv(f)
                year = extract_year_from_filename(f.name)
                if year is None:
                    year = 1900
                df['Year'] = year
                new_dfs.append(df)
                self.loaded_files.append(str(f))
            except Exception as e:
                messagebox.showerror("Error", f"Failed to load {f.name}: {e}")
                continue

        if not new_dfs:
            messagebox.showwarning("Warning", "No files could be loaded (check year extraction).")
            return

        if self.df is None:
            self.df = pd.concat(new_dfs, ignore_index=True)
        else:
            self.df = pd.concat([self.df] + new_dfs, ignore_index=True)

        save_state(self.folder_path, self.best_weights, self.loaded_files)

        self.update_data_tree()
        self.update_stats()
        self.update_graph_options()
        self.update_ml_options()
        self.status_label.config(text=f"Loaded {len(new_dfs)} new files. Total rows: {len(self.df)}")
        messagebox.showinfo("Success", f"Added {len(new_dfs)} files. Total rows: {len(self.df)}")
        self.start_incremental_search()

    # ---------- Incremental Search ----------
    def start_incremental_search(self):
        if self.df is None or self.is_training:
            return
        self.is_training = True
        self.progress_bar_inc['mode'] = 'determinate'
        self.progress_bar_inc['value'] = 0
        self.progress_label_inc.config(text="Incremental search starting...")
        self.root.update()

        n_combos = 256
        n_estimators = 30

        def evaluate_one(combo):
            try:
                score = self._evaluate_weights(combo, n_estimators=n_estimators)
                return combo, score
            except Exception:
                return combo, -np.inf

        def search_thread():
            combos = []
            for _ in range(n_combos):
                combo = {pos: np.random.uniform(0.1, 5.0) for pos in ['FW', 'MF', 'DF', 'GK']}
                combos.append(combo)

            best_score = -np.inf
            best_combo = None

            with ThreadPoolExecutor(max_workers=os.cpu_count()) as executor:
                future_to_combo = {executor.submit(evaluate_one, combo): combo for combo in combos}
                total = len(future_to_combo)
                completed = 0
                for future in as_completed(future_to_combo):
                    combo, score = future.result()
                    completed += 1
                    pct = (completed / total) * 100
                    self.root.after(0, lambda v=pct, txt=f"Evaluated {completed}/{total}":
                                    self._update_progress_inc(v, txt))
                    if score > best_score:
                        best_score = score
                        best_combo = combo

            if best_combo is not None and best_score > self._score_for_weights(self.best_weights):
                self.best_weights = best_combo
                save_state(self.folder_path, self.best_weights, self.loaded_files)
                self.root.after(0, self.update_best_weights_display)
                self.root.after(0, lambda: self._show_info(f"New best weights found! Score: {best_score:.4f}"))
            else:
                self.root.after(0, lambda: self._show_info(f"No improvement. Best score still: {best_score:.4f}"))
            self.root.after(0, self._stop_progress_inc)

        threading.Thread(target=search_thread, daemon=True).start()

    def _evaluate_weights(self, weights_dict, n_estimators=100):
        target = 'Gls'
        if target not in self.df.columns:
            return -np.inf
        numeric_cols = self.df.select_dtypes(include=['float64', 'int64']).columns.tolist()
        leakage = ['G+A', 'G-PK', 'PK', 'Gls.1', 'G+A.1', 'G-PK.1', 'G+A-PK']
        always_exclude = ['Rk', 'Player', 'Nation', 'Squad', 'Comp', 'Born', 'Matches', 'Pos', 'Year', 'SoT%', 'Sh/90', 'SoT/90']
        features = [c for c in numeric_cols if c not in set(always_exclude + leakage + [target])]
        features = [c for c in features if self.df[c].notna().any()]
        if not features:
            return -np.inf

        X = self.df[features].copy()
        y = self.df[target].copy()
        pos_map = weights_dict
        sample_weights = self.df['Pos'].map(pos_map).fillna(1.0).values

        X_train, X_test, y_train, y_test, w_train, w_test = train_test_split(
            X, y, sample_weights, test_size=0.2, random_state=42)

        train_means = X_train.mean()
        X_train = X_train.fillna(train_means)
        X_test = X_test.fillna(train_means)
        y_train = y_train.fillna(y_train.mean())
        y_test = y_test.fillna(y_train.mean())

        model = RandomForestRegressor(n_estimators=n_estimators, random_state=42, n_jobs=-1)
        model.fit(X_train, y_train, sample_weight=w_train)
        y_pred = model.predict(X_test)
        r2 = r2_score(y_test, y_pred)
        return r2

    def _score_for_weights(self, weights_dict):
        try:
            return self._evaluate_weights(weights_dict, n_estimators=30)
        except:
            return -np.inf

    def _update_progress_inc(self, val, label_text):
        self.progress_bar_inc['value'] = val
        self.progress_label_inc.config(text=label_text)
        self.root.update()

    def _stop_progress_inc(self):
        self.progress_bar_inc['value'] = 0
        self.progress_label_inc.config(text="Ready")
        self.is_training = False
        self.root.update()

    def _show_info(self, msg):
        messagebox.showinfo("Info", msg)
        self.inc_log.insert(tk.END, msg + "\n")
        self.inc_log.see(tk.END)

    def update_best_weights_display(self):
        w = self.best_weights
        text = f"Best weights: FW={w['FW']:.2f} MF={w['MF']:.2f} DF={w['DF']:.2f} GK={w['GK']:.2f}"
        self.best_weights_label.config(text=text)
        if hasattr(self, 'best_weights_display'):
            self.best_weights_display.config(text=text)

    # ---------- Position Importances Tab ----------
    def setup_position_importances_tab(self):
        frame = self.tab_pos_imp
        ctrl = tk.Frame(frame)
        ctrl.pack(fill='x', padx=10, pady=10)

        tk.Label(ctrl, text="Target:").pack(side=tk.LEFT, padx=5)
        self.pos_target_var = tk.StringVar(value='Gls')
        self.pos_target_combo = ttk.Combobox(ctrl, textvariable=self.pos_target_var, values=['Gls', 'Ast'], state='readonly', width=10)
        self.pos_target_combo.pack(side=tk.LEFT, padx=5)

        btn_run = tk.Button(ctrl, text="Train Per‑Position Models", command=self.run_position_importances)
        btn_run.pack(side=tk.LEFT, padx=5)

        self.pos_imp_canvas = None
        self.pos_imp_fig, self.pos_imp_axes = plt.subplots(2, 2, figsize=(12, 10))
        self.pos_imp_canvas = FigureCanvasTkAgg(self.pos_imp_fig, master=frame)
        self.pos_imp_canvas.get_tk_widget().pack(fill='both', expand=True, padx=5, pady=5)

    def run_position_importances(self):
        if self.df is None:
            messagebox.showerror("Error", "No data loaded.")
            return
        target = self.pos_target_var.get()
        if target not in self.df.columns:
            messagebox.showerror("Error", f"Target '{target}' not found.")
            return

        numeric_cols = self.df.select_dtypes(include=['float64', 'int64']).columns.tolist()
        leakage = ['G+A', 'G-PK', 'PK', 'Gls.1', 'G+A.1', 'G-PK.1', 'G+A-PK']
        always_exclude = ['Rk', 'Player', 'Nation', 'Squad', 'Comp', 'Born', 'Matches', 'Pos', 'Year', 'SoT%', 'Sh/90', 'SoT/90']
        features = [c for c in numeric_cols if c not in set(always_exclude + leakage + [target])]
        features = [c for c in features if self.df[c].notna().any()]
        if not features:
            messagebox.showerror("Error", "No valid features.")
            return

        positions = ['FW', 'MF', 'DF', 'GK']
        pos_importances = {}
        pos_models = {}

        for pos in positions:
            pos_data = self.df[self.df['Pos'] == pos]
            if len(pos_data) < 5:
                pos_importances[pos] = None
                continue
            X = pos_data[features].copy()
            y = pos_data[target].copy()
            X = X.fillna(X.mean())
            y = y.fillna(y.mean())
            model = RandomForestRegressor(n_estimators=100, random_state=42, n_jobs=-1)
            model.fit(X, y)
            pos_models[pos] = model
            pos_importances[pos] = model.feature_importances_

        for ax in self.pos_imp_axes.flat:
            ax.clear()

        for i, pos in enumerate(positions):
            ax = self.pos_imp_axes.flat[i]
            if pos_importances[pos] is not None:
                imp = pos_importances[pos]
                sorted_idx = np.argsort(imp)[-10:]
                top_features = [features[j] for j in sorted_idx]
                top_imp = imp[sorted_idx]
                ax.barh(top_features, top_imp)
                ax.set_title(f'{pos} (n={len(self.df[self.df["Pos"]==pos])})')
                ax.set_xlabel('Importance')
            else:
                ax.text(0.5, 0.5, f'No data for {pos}', ha='center', va='center')
                ax.set_title(pos)

        plt.tight_layout()
        self.pos_imp_canvas.draw()
        self.pos_models = pos_models
        messagebox.showinfo("Done", "Per‑position models trained and plotted.")

    # ---------- Predict Tab ----------
    def setup_predict_tab(self):
        frame = self.tab_predict
        ctrl = tk.Frame(frame)
        ctrl.pack(fill='x', padx=10, pady=10)

        tk.Label(ctrl, text="Incomplete CSV:").pack(side=tk.LEFT, padx=5)
        self.predict_file_entry = tk.Entry(ctrl, width=50)
        self.predict_file_entry.pack(side=tk.LEFT, padx=5)
        btn_browse_predict = tk.Button(ctrl, text="Browse", command=self.browse_predict_file)
        btn_browse_predict.pack(side=tk.LEFT, padx=5)

        tk.Label(ctrl, text="Predict:").pack(side=tk.LEFT, padx=5)
        self.predict_target_var = tk.StringVar(value='Gls')
        self.predict_target_combo = ttk.Combobox(ctrl, textvariable=self.predict_target_var, values=['Gls', 'Ast'], state='readonly', width=10)
        self.predict_target_combo.pack(side=tk.LEFT, padx=5)

        self.project_var = tk.IntVar(value=0)
        chk_project = tk.Checkbutton(ctrl, text="Project to full season (starter average)", variable=self.project_var)
        chk_project.pack(side=tk.LEFT, padx=5)

        btn_predict = tk.Button(ctrl, text="Predict", command=self.run_predict, bg='lightgreen')
        btn_predict.pack(side=tk.LEFT, padx=5)

        btn_export = tk.Button(ctrl, text="Export Predictions", command=self.export_predictions)
        btn_export.pack(side=tk.LEFT, padx=5)

        result_frame = tk.Frame(frame)
        result_frame.pack(fill='both', expand=True, padx=5, pady=5)

        self.pred_tree = ttk.Treeview(result_frame)
        self.pred_tree.pack(side=tk.LEFT, fill='both', expand=True)
        scroll = ttk.Scrollbar(result_frame, orient='vertical', command=self.pred_tree.yview)
        scroll.pack(side=tk.RIGHT, fill='y')
        self.pred_tree.configure(yscrollcommand=scroll.set)

        self.prediction_df = None

    def browse_predict_file(self):
        file_path = filedialog.askopenfilename(filetypes=[("CSV files", "*.csv")])
        if file_path:
            self.predict_file_entry.delete(0, tk.END)
            self.predict_file_entry.insert(0, file_path)

    def run_predict(self):
        file_path = self.predict_file_entry.get().strip()
        if not file_path or not os.path.exists(file_path):
            messagebox.showerror("Error", "Please select a valid CSV file.")
            return
        target = self.predict_target_var.get()
        if self.df is None:
            messagebox.showerror("Error", "No training data loaded. Please load data first.")
            return

        try:
            df_in = load_single_csv(file_path)
            if 'Year' not in df_in.columns:
                df_in['Year'] = 2026

            numeric_cols = self.df.select_dtypes(include=['float64', 'int64']).columns.tolist()
            leakage = ['G+A', 'G-PK', 'PK', 'Gls.1', 'G+A.1', 'G-PK.1', 'G+A-PK']
            always_exclude = ['Rk', 'Player', 'Nation', 'Squad', 'Comp', 'Born', 'Matches', 'Pos', 'Year', 'SoT%', 'Sh/90', 'SoT/90']
            features = [c for c in numeric_cols if c not in set(always_exclude + leakage + [target])]
            features = [c for c in features if self.df[c].notna().any()]
            if 'LeagueRating' not in features and 'LeagueRating' in self.df.columns:
                features.append('LeagueRating')

            common_features = [f for f in features if f in df_in.columns]
            if not common_features:
                messagebox.showerror("Error", "No common features between training and input CSV.")
                return

            X_pred = df_in[common_features].copy()
            train_means = self.df[common_features].mean()
            X_pred = X_pred.fillna(train_means)

            if self.model is not None and hasattr(self.model, 'predict'):
                model = self.model
            else:
                X_train_all = self.df[common_features].copy()
                y_train_all = self.df[target].copy()
                X_train_all = X_train_all.fillna(train_means)
                y_train_all = y_train_all.fillna(y_train_all.mean())
                sample_weights = self.get_position_weights()
                if sample_weights is not None:
                    valid = ~np.isnan(sample_weights)
                    X_train_all = X_train_all[valid]
                    y_train_all = y_train_all[valid]
                    sample_weights = sample_weights[valid]
                else:
                    sample_weights = np.ones(len(X_train_all))
                model = RandomForestRegressor(n_estimators=100, random_state=42, n_jobs=-1)
                model.fit(X_train_all, y_train_all, sample_weight=sample_weights)
                self.model = model
                self.features = common_features

            preds = model.predict(X_pred)
            df_in['Predicted_' + target] = preds

            if self.project_var.get() == 1:
                starters = self.df[self.df['Starts'] >= 15]
                if len(starters) == 0:
                    starters = self.df
                avg_min_by_pos = starters.groupby('Pos')['Min'].mean()
                overall_avg_min = starters['Min'].mean()
                scaled_preds = []
                for idx, row in df_in.iterrows():
                    pos = row['Pos']
                    avg_min = avg_min_by_pos.get(pos, overall_avg_min)
                    current_min = row['Min']
                    if current_min > 0:
                        scale = avg_min / current_min
                        scale = min(scale, 5.0)
                    else:
                        scale = 1.0
                    scaled_preds.append(row['Predicted_' + target] * scale)
                df_in['Projected_' + target] = scaled_preds

            self.pred_tree.delete(*self.pred_tree.get_children())
            cols = ['Player', 'Squad', 'Pos', 'Min']
            if self.project_var.get() == 1:
                cols.append('Projected_' + target)
                cols.append('Predicted_' + target)
            else:
                cols.append('Predicted_' + target)
            for col in ['Age', '90s']:
                if col in df_in.columns:
                    cols.insert(3, col)
            self.pred_tree['columns'] = cols
            self.pred_tree['show'] = 'headings'
            for col in cols:
                self.pred_tree.heading(col, text=col)
                self.pred_tree.column(col, width=100, anchor='w')
            for idx, row in df_in.iterrows():
                values = [row.get(c, '') for c in cols]
                self.pred_tree.insert('', 'end', values=[str(v) for v in values])

            self.prediction_df = df_in
            messagebox.showinfo("Success", f"Predictions generated for {len(df_in)} players.")
        except Exception as e:
            messagebox.showerror("Error", f"Prediction failed:\n{str(e)}")

    def export_predictions(self):
        if self.prediction_df is None:
            messagebox.showerror("Error", "No predictions to export.")
            return
        file_path = filedialog.asksaveasfilename(defaultextension=".csv", filetypes=[("CSV files", "*.csv")])
        if file_path:
            self.prediction_df.to_csv(file_path, index=False)
            messagebox.showinfo("Success", f"Exported to {file_path}")

    # ---------- ML training helpers ----------
    def get_position_weights(self, custom_weights=None):
        if self.df is None: return None
        if custom_weights:
            pos_map = custom_weights
        else:
            pos_map = {p: self.weight_sliders[p].get() for p in ['FW', 'MF', 'DF', 'GK']}
        weights = self.df['Pos'].map(pos_map).fillna(1.0)
        return weights.values

    def _train_model(self, sample_weights, verbose=True):
        target = self.target_var.get()
        if target not in self.df.columns:
            raise ValueError(f"Target '{target}' not found in data.")
        numeric_cols = self.df.select_dtypes(include=['float64', 'int64']).columns.tolist()
        leakage_map = {
            'Gls': ['G+A', 'G-PK', 'PK', 'Gls.1', 'G+A.1', 'G-PK.1', 'G+A-PK'],
            'Ast': ['G+A', 'Ast.1', 'G+A.1'],
            'PK': ['Gls', 'G+A', 'G-PK', 'PKatt', 'Gls.1', 'G+A.1', 'G-PK.1'],
            'G+A': ['Gls', 'Ast', 'G+A.1'],
            'G-PK': ['Gls', 'PK', 'G-PK.1'],
        }
        per90 = ['Gls.1', 'Ast.1', 'G+A.1', 'G-PK.1', 'G+A-PK']
        leakage = leakage_map.get(target, []) + per90 if target in ['Gls','Ast','G+A','G-PK','PK','G+A-PK'] else per90
        always_exclude = ['Rk', 'Player', 'Nation', 'Squad', 'Comp', 'Born', 'Matches', 'Pos', 'Year']
        features = [c for c in numeric_cols if c not in set(always_exclude + leakage + [target])]
        features = [c for c in features if self.df[c].notna().any()]
        if 'LeagueRating' not in features and 'LeagueRating' in self.df.columns:
            features.append('LeagueRating')
        if not features:
            raise ValueError("No valid features remain. Try a different target.")
        X = self.df[features].copy()
        y = self.df[target].copy()
        if sample_weights is not None:
            valid = ~np.isnan(sample_weights)
            X = X[valid]; y = y[valid]; sample_weights = sample_weights[valid]
        else:
            sample_weights = np.ones(len(X))
        test_size = self.test_size_var.get()
        X_train, X_test, y_train, y_test, w_train, w_test = train_test_split(
            X, y, sample_weights, test_size=test_size, random_state=42)
        train_means = X_train.mean()
        X_train = X_train.fillna(train_means)
        X_test = X_test.fillna(train_means)
        y_train = y_train.fillna(y_train.mean())
        y_test = y_test.fillna(y_train.mean())
        model_type = self.model_type_var.get()
        if model_type == 'Regression':
            model = RandomForestRegressor(n_estimators=100, random_state=42, n_jobs=-1)
            model.fit(X_train, y_train, sample_weight=w_train)
            y_pred = model.predict(X_test)
            mse = mean_squared_error(y_test, y_pred)
            r2 = r2_score(y_test, y_pred)
            metrics = {'mse': mse, 'r2': r2}
            result_str = f"R²: {r2:.4f}, MSE: {mse:.4f}"
        else:
            y_train_binned = pd.qcut(y_train, q=3, labels=['Low', 'Medium', 'High'], duplicates='drop')
            le = LabelEncoder()
            y_train_enc = le.fit_transform(y_train_binned)
            quantiles = y_train.quantile([1/3, 2/3]).values
            def map_to_category(val):
                if val <= quantiles[0]: return 0
                elif val <= quantiles[1]: return 1
                else: return 2
            y_test_enc = np.array([map_to_category(v) for v in y_test])
            model = RandomForestClassifier(n_estimators=100, random_state=42, n_jobs=-1)
            model.fit(X_train, y_train_enc, sample_weight=w_train)
            y_pred = model.predict(X_test)
            acc = accuracy_score(y_test_enc, y_pred)
            metrics = {'accuracy': acc}
            result_str = f"Accuracy: {acc:.4f}"
        return model, features, metrics, result_str

    def start_training(self):
        if self.df is None or self.is_training: return
        self.is_training = True
        self.progress_bar_ml['mode'] = 'indeterminate'
        self.progress_bar_ml.start()
        self.progress_label_ml.config(text="Training...")
        self.root.update()
        def train_thread():
            try:
                weights = self.get_position_weights()
                model, features, metrics, result_str = self._train_model(weights)
                self.model = model; self.features = features
                self.root.after(0, self._display_results, metrics, result_str, features)
            except Exception as e:
                self.root.after(0, self._show_error_ml, str(e))
            finally:
                self.root.after(0, self._stop_progress_ml)
        threading.Thread(target=train_thread, daemon=True).start()

    def _display_results(self, metrics, result_str, features):
        self.result_text.delete(1.0, tk.END)
        self.result_text.insert(tk.END, f"Manual weights result:\n{result_str}\n\nFeature Importance:\n")
        if hasattr(self.model, 'feature_importances_'):
            imp = self.model.feature_importances_
            sorted_idx = np.argsort(imp)[::-1]
            for i in sorted_idx[:10]:
                self.result_text.insert(tk.END, f"{features[i]}: {imp[i]:.4f}\n")
        self._plot_importance(features)

    def _plot_importance(self, features):
        self.ax_imp.clear()
        if hasattr(self.model, 'feature_importances_'):
            imp = self.model.feature_importances_
            sorted_idx = np.argsort(imp)[-10:]
            self.ax_imp.barh(np.array(features)[sorted_idx], imp[sorted_idx])
            self.ax_imp.set_xlabel('Importance')
            self.ax_imp.set_title('Top 10 Feature Importances')
        else:
            self.ax_imp.text(0.5, 0.5, 'No importance available', ha='center', va='center')
            self.ax_imp.set_xlim(0,1)
        self.canvas_imp.draw()

    def _stop_progress_ml(self):
        self.progress_bar_ml.stop()
        self.progress_label_ml.config(text="Ready")
        self.is_training = False

    def _show_error_ml(self, msg):
        messagebox.showerror("Error", msg)
        self._stop_progress_ml()

    # ---------- All-Time Best & Future Stars (Fixed) ----------
    def setup_alltime_tab(self):
        frame = self.tab_alltime
        ctrl = tk.Frame(frame)
        ctrl.pack(fill='x', padx=10, pady=10)

        tk.Label(ctrl, text="Position:").pack(side=tk.LEFT, padx=5)
        self.at_pos_var = tk.StringVar(value='FW')
        self.at_pos_combo = ttk.Combobox(ctrl, textvariable=self.at_pos_var, values=['FW', 'MF', 'DF', 'GK'], state='readonly', width=8)
        self.at_pos_combo.pack(side=tk.LEFT, padx=5)

        tk.Label(ctrl, text="Weights:").pack(side=tk.LEFT, padx=10)
        self.at_weights = {}
        weight_cols = ['Gls', 'Ast', 'G+A', 'PK', 'CrdY']
        for col in weight_cols:
            tk.Label(ctrl, text=col).pack(side=tk.LEFT, padx=2)
            var = tk.DoubleVar(value=1.0)
            scale = tk.Scale(ctrl, from_=0.0, to=5.0, resolution=0.1, orient=tk.HORIZONTAL,
                             variable=var, length=80)
            scale.pack(side=tk.LEFT, padx=2)
            self.at_weights[col] = var

        btn_compute = tk.Button(ctrl, text="Compute Ratings", command=self.compute_alltime_ratings)
        btn_compute.pack(side=tk.LEFT, padx=10)

        result_frame = tk.Frame(frame)
        result_frame.pack(fill='both', expand=True, padx=5, pady=5)

        # All-Time Greats
        left_frame = tk.LabelFrame(result_frame, text="All-Time Greats (League-Adjusted)", padx=5, pady=5)
        left_frame.pack(side=tk.LEFT, fill='both', expand=True)
        self.at_greats_tree = ttk.Treeview(left_frame, columns=('Player', 'Career', 'Peak', 'Seasons'), show='headings')
        self.at_greats_tree.heading('Player', text='Player')
        self.at_greats_tree.heading('Career', text='Career Score')
        self.at_greats_tree.heading('Peak', text='Peak Score')
        self.at_greats_tree.heading('Seasons', text='Seasons')
        self.at_greats_tree.column('Player', width=150)
        self.at_greats_tree.column('Career', width=100)
        self.at_greats_tree.column('Peak', width=100)
        self.at_greats_tree.column('Seasons', width=80)
        self.at_greats_tree.pack(fill='both', expand=True)
        scroll1 = ttk.Scrollbar(left_frame, orient='vertical', command=self.at_greats_tree.yview)
        scroll1.pack(side=tk.RIGHT, fill='y')
        self.at_greats_tree.configure(yscrollcommand=scroll1.set)

        # Future Stars
        right_frame = tk.LabelFrame(result_frame, text="Future Stars (Age ≤ 23, Recent, ≥450 min)", padx=5, pady=5)
        right_frame.pack(side=tk.RIGHT, fill='both', expand=True)
        self.at_future_tree = ttk.Treeview(right_frame, columns=('Player', 'Age', 'Current', 'Trend'), show='headings')
        self.at_future_tree.heading('Player', text='Player')
        self.at_future_tree.heading('Age', text='Age')
        self.at_future_tree.heading('Current', text='Current Score')
        self.at_future_tree.heading('Trend', text='Trend')
        self.at_future_tree.column('Player', width=150)
        self.at_future_tree.column('Age', width=80)
        self.at_future_tree.column('Current', width=100)
        self.at_future_tree.column('Trend', width=100)
        self.at_future_tree.pack(fill='both', expand=True)
        scroll2 = ttk.Scrollbar(right_frame, orient='vertical', command=self.at_future_tree.yview)
        scroll2.pack(side=tk.RIGHT, fill='y')
        self.at_future_tree.configure(yscrollcommand=scroll2.set)

    def compute_alltime_ratings(self):
        if self.df is None:
            messagebox.showerror("Error", "No data loaded.")
            return
        pos = self.at_pos_var.get()
        w_gls = self.at_weights['Gls'].get()
        w_ast = self.at_weights['Ast'].get()
        w_ga = self.at_weights['G+A'].get()
        w_pk = self.at_weights['PK'].get()
        w_crd = self.at_weights['CrdY'].get()

        df_pos = self.df[self.df['Pos'] == pos].copy()
        if df_pos.empty:
            messagebox.showinfo("Info", f"No data for position {pos}.")
            return
        if 'Year' not in df_pos.columns:
            messagebox.showerror("Error", "Data must have a 'Year' column.")
            return

        stats = ['Gls', 'Ast', 'G+A', 'PK', 'CrdY']
        if 'LeagueRating' not in df_pos.columns:
            df_pos['LeagueRating'] = 100.0

        # Adjust stats by league rating
        for stat in stats:
            df_pos[f'{stat}_adj'] = df_pos[stat] * (df_pos['LeagueRating'] / 100.0)

        # Aggregate per player-season, keep Min (average)
        agg_dict = {f'{s}_adj': 'mean' for s in stats}
        agg_dict['Min'] = 'mean'   # add Min
        df_pos_agg = df_pos.groupby(['Player', 'Year', 'Age']).agg(agg_dict).reset_index()
        # Rename adjusted columns back to original names for z-score computation
        for stat in stats:
            df_pos_agg[stat] = df_pos_agg[f'{stat}_adj']

        # Compute z-scores per year
        for stat in stats:
            yearly_stats = df_pos_agg.groupby('Year')[stat].agg(['mean', 'std']).reset_index()
            yearly_stats.columns = ['Year', f'{stat}_mean', f'{stat}_std']
            df_pos_agg = df_pos_agg.merge(yearly_stats, on='Year', how='left')
            df_pos_agg[f'{stat}_z'] = (df_pos_agg[stat] - df_pos_agg[f'{stat}_mean']) / df_pos_agg[f'{stat}_std'].replace(0, 1)

        df_pos_agg['composite'] = (w_gls * df_pos_agg['Gls_z'] +
                                   w_ast * df_pos_agg['Ast_z'] +
                                   w_ga * df_pos_agg['G+A_z'] +
                                   w_pk * df_pos_agg['PK_z'] -
                                   w_crd * df_pos_agg['CrdY_z'])

        # For each player, get their last season's data (most recent season they appear)
        player_last = df_pos_agg.sort_values('Year').groupby('Player').last().reset_index()
        # Also compute career metrics
        player_career = df_pos_agg.groupby('Player').agg(
            career_score=('composite', 'mean'),
            peak_score=('composite', 'max'),
            seasons=('Year', 'count')
        ).reset_index()

        # Merge last season info
        player_data = player_career.merge(player_last[['Player', 'Age', 'Year', 'composite', 'Min']], on='Player', how='left')
        player_data.rename(columns={'Age': 'current_age', 'Year': 'last_year', 'composite': 'current_score'}, inplace=True)

        # Compute trend (slope over all seasons)
        trends = []
        for player in player_data['Player']:
            player_df = df_pos_agg[df_pos_agg['Player'] == player].sort_values('Year')
            if len(player_df) >= 2:
                X = player_df['Year'].values.reshape(-1,1)
                y = player_df['composite'].values
                model = LinearRegression()
                model.fit(X, y)
                slope = model.coef_[0]
            else:
                slope = 0
            trends.append(slope)
        player_data['trend'] = trends

        # All-time greats: top 10 by career_score
        greats = player_data.sort_values('career_score', ascending=False).head(100)

        # Future stars: age <= 23, positive trend, current_score > 0, Min >= 450, active within last 2 years
        latest_overall_year = df_pos_agg['Year'].max()
        future = player_data[
            (player_data['current_age'] <= 23) &
            (player_data['trend'] > 0) &
            (player_data['current_score'] > 0) &
            (player_data['Min'] >= 450) &
            (player_data['last_year'] >= latest_overall_year - 2)
        ].sort_values('current_score', ascending=False).head(100)

        # Clear trees
        for item in self.at_greats_tree.get_children():
            self.at_greats_tree.delete(item)
        for item in self.at_future_tree.get_children():
            self.at_future_tree.delete(item)

        for _, row in greats.iterrows():
            self.at_greats_tree.insert('', 'end', values=(
                row['Player'],
                f"{row['career_score']:.2f}",
                f"{row['peak_score']:.2f}",
                row['seasons']
            ))

        for _, row in future.iterrows():
            self.at_future_tree.insert('', 'end', values=(
                row['Player'],
                row['current_age'],
                f"{row['current_score']:.2f}",
                f"{row['trend']:.2f}"
            ))

        messagebox.showinfo("Done", f"League-adjusted ratings computed for {pos}.")

# ------------------- Run -------------------
if __name__ == "__main__":
    root = tk.Tk()
    app = PlayerAnalyticsApp(root)
    root.mainloop()