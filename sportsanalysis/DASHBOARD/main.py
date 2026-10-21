"""Combined simulation dashboard — 7 competitions.

Flow:
    Progress -> Home (2x4 grid of clickable blocks)
             -> World Map (clickable continents + league markers)
             -> Detail  (left: top-5 cards, right: full table + "Save PNG")
             -> Video   (500-second animated table, all columns, sortable by avg pts)

Runs all simulations sequentially on one background thread behind a
single unified progress bar.  While running it captures periodic
snapshots so the Video screen can replay each league's table as it
evolves over the simulations.
"""

import sys
import time
import importlib.util
from pathlib import Path

from PyQt5.QtCore import Qt, QThread, pyqtSignal, QTimer, QPointF, QRectF
from PyQt5.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QLabel, QProgressBar, QTableWidget, QTableWidgetItem,
    QHeaderView, QStackedWidget, QFrame, QPushButton, QSizePolicy,
    QGridLayout, QFileDialog, QMessageBox, QScrollArea,
    QComboBox, QSlider, QProgressDialog,
)
from PyQt5.QtGui import (
    QFont, QColor, QMouseEvent, QPainter, QPen, QBrush, QPolygonF,
    QPainterPath, QPixmap, QLinearGradient, QFontMetrics, QImage,
)


# ---------------------------------------------------------------------------
# Load all simulation modules
# ---------------------------------------------------------------------------
def _app_root():
    if getattr(sys, "frozen", False):
        exe_dir = Path(sys.executable).resolve().parent
        if (exe_dir / "european_leagues").exists():
            return exe_dir
        return exe_dir.parent.parent
    return Path(__file__).resolve().parent.parent


_ROOT = _app_root()


def _load(name, relpath):
    spec = importlib.util.spec_from_file_location(name, _ROOT / relpath)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


wc  = _load("wc_sim",  "worldcupwomens/main.py")
pl  = _load("pl_sim",  "premier-league/26-27-season.py")
ger = _load("ger_sim", "european_leagues/germany.py")
ita = _load("ita_sim", "european_leagues/italy.py")
sco = _load("sco_sim", "european_leagues/Scotland.py")
esp = _load("esp_sim", "european_leagues/spain.py")
fra = _load("fra_sim", "european_leagues/france.py")


# ---------------------------------------------------------------------------
# League specs
# ---------------------------------------------------------------------------
LEAGUES = [
    {
        "key": "pl", "title": "Premier League", "short": "Premier League",
        "subtitle": "2026/27 Season", "accent": "#c9a227",
        "continent": "Europe",
        "geo": {"lon": -1.7, "lat": 52.5, "dx": -0.13, "dy": -0.03},
        "n_sims": pl.NUM_PL_SIMS,
        "has_video": True,
        "runner": lambda n, p, r, sc=None: pl.run_simulation(
            n, on_progress=p, is_running=r, snapshot_callback=sc),
        "get_teams": lambda r: sorted(r["pl_teams_set"]),
        "top_key": "title_prob", "top_fmt": "{:.1f}%",
        "columns": [
            ("Pos", "avg_positions", "{:.2f}"),
            ("Pts", "avg_points", "{:.1f}"),
            ("Title%", "title_prob", "{:.2f}"),
            ("UCL%", "ucl_qual_prob", "{:.2f}"),
            ("UEL%", "uel_qual_prob", "{:.2f}"),
            ("UECL%", "uecl_qual_prob", "{:.2f}"),
            ("Tot Euro%", "total_euro_prob", "{:.2f}"),
            ("Releg%", "relegation_prob", "{:.2f}"),
        ],
    },
    {
        "key": "esp", "title": "La Liga", "short": "La Liga",
        "subtitle": "2026/27 Season", "accent": "#e67e22",
        "continent": "Europe",
        "geo": {"lon": -3.7, "lat": 40.4, "dx": -0.15, "dy": 0.10},
        "n_sims": esp.N_SIMS, "has_video": True,
        "runner": lambda n, p, r, sc=None: esp.run_simulation(
            n, on_progress=p, is_running=r, snapshot_callback=sc),
        "get_teams": lambda r: r["teams"],
        "top_key": "title_prob", "top_fmt": "{:.1f}%",
        "columns": [
            ("Pts", "avg_points", "{:.1f}"),
            ("Title%", "title_prob", "{:.2f}"),
            ("Top4%", "top4_prob", "{:.2f}"),
            ("5th%", "fifth_prob", "{:.2f}"),
            ("6th%", "sixth_prob", "{:.2f}"),
            ("Releg%", "releg_prob", "{:.2f}"),
        ],
    },
    {
        "key": "ger", "title": "Bundesliga", "short": "Bundesliga",
        "subtitle": "2026/27 Season", "accent": "#d62728",
        "continent": "Europe",
        "geo": {"lon": 10.4, "lat": 51.1, "dx": 0.10, "dy": -0.10},
        "n_sims": ger.NUM_SIMS, "has_video": True,
        "runner": lambda n, p, r, sc=None: ger.run_simulation(
            n, on_progress=p, is_running=r, snapshot_callback=sc),
        "get_teams": lambda r: r["teams"],
        "top_key": "title_prob", "top_fmt": "{:.1f}%",
        "columns": [
            ("Pts", "avg_points", "{:.1f}"),
            ("Title%", "title_prob", "{:.2f}"),
            ("Top4%", "top4_prob", "{:.2f}"),
            ("5th%", "fifth_prob", "{:.2f}"),
            ("6th%", "sixth_prob", "{:.2f}"),
            ("RelPO%", "relpo_prob", "{:.2f}"),
            ("Releg%", "releg_prob", "{:.2f}"),
        ],
    },
    {
        "key": "ita", "title": "Serie A", "short": "Serie A",
        "subtitle": "2026/27 Season", "accent": "#1f77b4",
        "continent": "Europe",
        "geo": {"lon": 12.5, "lat": 42.8, "dx": 0.15, "dy": 0.10},
        "n_sims": ita.N_SIMS, "has_video": True,
        "runner": lambda n, p, r, sc=None: ita.run_simulation(
            n, on_progress=p, is_running=r, snapshot_callback=sc),
        "get_teams": lambda r: r["teams"],
        "top_key": "title_prob", "top_fmt": "{:.1f}%",
        "columns": [
            ("Pts", "avg_points", "{:.1f}"),
            ("Title%", "title_prob", "{:.2f}"),
            ("Top4%", "top4_prob", "{:.2f}"),
            ("5th%", "fifth_prob", "{:.2f}"),
            ("6th%", "sixth_prob", "{:.2f}"),
            ("Releg%", "releg_prob", "{:.2f}"),
        ],
    },
    {
        "key": "fra", "title": "Ligue 1", "short": "Ligue 1",
        "subtitle": "2026/27 Season", "accent": "#1a5276",
        "continent": "Europe",
        "geo": {"lon": 2.3, "lat": 47.0, "dx": 0.02, "dy": 0.17},
        "n_sims": fra.NUM_SIMS, "has_video": True,
        "runner": lambda n, p, r, sc=None: fra.run_simulation(
            n, on_progress=p, is_running=r, snapshot_callback=sc),
        "get_teams": lambda r: r["teams"],
        "top_key": "title_prob", "top_fmt": "{:.1f}%",
        "columns": [
            ("Pts", "avg_points", "{:.1f}"),
            ("Title%", "title_prob", "{:.2f}"),
            ("Top4%", "top4_prob", "{:.2f}"),
            ("5th%", "fifth_prob", "{:.2f}"),
            ("6th%", "sixth_prob", "{:.2f}"),
            ("RelPO%", "relpo_prob", "{:.2f}"),
            ("Releg%", "releg_prob", "{:.2f}"),
        ],
    },
    {
        "key": "sco", "title": "Scottish Premiership", "short": "Scottish Prem.",
        "subtitle": "2026/27 Season", "accent": "#2c3e50",
        "continent": "Europe",
        "geo": {"lon": -4.2, "lat": 57.0, "dx": -0.17, "dy": -0.15},
        "n_sims": sco.NUM_SIMS, "has_video": True,
        "runner": lambda n, p, r, sc=None: sco.run_simulation(
            n, on_progress=p, is_running=r, snapshot_callback=sc),
        "get_teams": lambda r: r["teams"],
        "top_key": "title_prob", "top_fmt": "{:.1f}%",
        "columns": [
            ("Pts", "avg_points", "{:.1f}"),
            ("Title%", "title_prob", "{:.2f}"),
            ("UCL%", "ucl_prob", "{:.2f}"),
            ("UECL%", "uecl_prob", "{:.2f}"),
            ("RelPO%", "relpo_prob", "{:.2f}"),
            ("Releg%", "releg_prob", "{:.2f}"),
        ],
    },
    {
        "key": "wc", "title": "Women's World Cup", "short": "Women's World Cup",
        "subtitle": "2027 Qualification", "accent": "#1e8a49",
        "continent": "Global",
        "geo": {"lon": -25.0, "lat": -10.0, "dx": 0.05, "dy": 0.0},
        "n_sims": wc.N_SIMS,
        "has_video": False,   # source not modified -> excluded from Video
        "runner": lambda n, p, r, sc=None: wc.run_simulation(
            n, on_progress=p, is_running=r),
        "is_wc": True,
    },
]

TOTAL_SIMS = sum(spec["n_sims"] for spec in LEAGUES)


# ---------------------------------------------------------------------------
# Styles + helpers  (unchanged from your original, except noted additions)
# ---------------------------------------------------------------------------
_TABLE_QSS = """
QTableWidget {
    background: #ffffff;
    alternate-background-color: #f7f9fc;
    border: 1px solid #d0d8e0;
    border-radius: 8px;
    gridline-color: #e0e8f0;
    font-size: 11px;
}
QHeaderView::section {
    background: #1a3c5e;
    color: white;
    padding: 6px;
    border: none;
    font-weight: bold;
}
QTableWidget::item:selected {
    background: #2e86c1;
    color: white;
}
"""

_PROGRESS_QSS = """
QProgressBar {
    border: 2px solid #1a3c5e;
    border-radius: 10px;
    text-align: center;
    background: #f0f4f8;
    font-size: 13px;
    font-weight: bold;
}
QProgressBar::chunk {
    background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
                                stop:0 #2e86c1, stop:1 #1a5276);
    border-radius: 8px;
}
"""


def _text_width(fm, text):
    try:
        return fm.horizontalAdvance(text)
    except AttributeError:
        return fm.width(text)


def _league_leader(spec, results):
    r = results.get(spec["key"])
    if r is None:
        return "—", 0.0, "—"
    if spec.get("is_wc"):
        qual = r.get("qualification_prob", {})
        teams = [t for t in wc.TEAM_CONF if wc.TEAM_CONF[t] in wc.CONF_NAMES]
        cand = [(t, qual.get(t, 0.0)) for t in teams if qual.get(t, 0.0) < 1.0]
        if not cand:
            cand = [(t, qual.get(t, 0.0)) for t in teams]
        if not cand:
            return "—", 0.0, "—"
        t, p = max(cand, key=lambda x: x[1])
        return t, p * 100.0, f"{p * 100:.2f}%"
    key = spec["top_key"]
    teams = spec["get_teams"](r)
    if not teams:
        return "—", 0.0, "—"
    t = max(teams, key=lambda x: r[key].get(x, 0.0))
    val = r[key].get(t, 0.0)
    return t, val, spec["top_fmt"].format(val)


def _safe_filename(name):
    cleaned = "".join(c if (c.isalnum() or c in " -_") else "_" for c in name)
    return cleaned.strip().replace(" ", "_") or "predictions"


# ---------------------------------------------------------------------------
# Worker — runs every league sequentially, capturing snapshots
# ---------------------------------------------------------------------------
class SimulationWorker(QThread):
    progress = pyqtSignal(int, int, str)
    all_done = pyqtSignal(dict, dict)   # results, snapshots

    def __init__(self):
        super().__init__()
        self._running = True
        self._snapshots = {}

    def _emit(self, current, label):
        if self._running:
            self.progress.emit(current, TOTAL_SIMS, label)

    def run(self):
        results = {}
        offset = 0
        for spec in LEAGUES:
            if not self._running:
                return
            n = spec["n_sims"]
            label = spec["title"]
            key = spec["key"]
            self._snapshots[key] = []

            def make_prog_cb(off, lbl):
                return lambda s, _t: self._emit(off + s, lbl)

            def make_snap_cb(k):
                def cb(done, total, snap):
                    if not self._running:
                        return
                    s = dict(snap)
                    s["done"] = done
                    s["total"] = total
                    self._snapshots[k].append(s)
                return cb

            res = spec["runner"](
                n, make_prog_cb(offset, label),
                lambda: self._running, make_snap_cb(key))
            if not self._running:
                return
            results[key] = res
            offset += res.get("n_sims", n)

        self._emit(TOTAL_SIMS, "Complete")
        self.all_done.emit(results, self._snapshots)

    def stop(self):
        self._running = False


# ---------------------------------------------------------------------------
# Progress screen
# ---------------------------------------------------------------------------
class ProgressWidget(QWidget):
    def __init__(self, on_finished):
        super().__init__()
        self.on_finished = on_finished
        self.start_time = time.time()
        self._setup_ui()
        self._start()

    def _setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(40, 40, 40, 40)
        layout.setSpacing(20)
        layout.addStretch()

        title = QLabel("Simulation Dashboard")
        title.setFont(QFont("Segoe UI", 22, QFont.Bold))
        title.setAlignment(Qt.AlignCenter)
        title.setStyleSheet("color: #1a3c5e;")
        layout.addWidget(title)

        subtitle = QLabel(
            "Premier League  ·  La Liga  ·  Bundesliga  ·  Serie A  ·  "
            "Ligue 1  ·  Scottish Premiership  ·  Women's World Cup")
        subtitle.setFont(QFont("Segoe UI", 11))
        subtitle.setAlignment(Qt.AlignCenter)
        subtitle.setWordWrap(True)
        subtitle.setStyleSheet("color: #5a7a9a;")
        layout.addWidget(subtitle)

        self.bar = QProgressBar()
        self.bar.setRange(0, TOTAL_SIMS)
        self.bar.setTextVisible(True)
        self.bar.setFormat("%p%  (%v / %m sims)")
        self.bar.setFixedHeight(32)
        self.bar.setStyleSheet(_PROGRESS_QSS)
        layout.addWidget(self.bar)

        self.status = QLabel("Initializing...")
        self.status.setFont(QFont("Segoe UI", 11))
        self.status.setAlignment(Qt.AlignCenter)
        self.status.setStyleSheet("color: #4a6a8a;")
        layout.addWidget(self.status)

        self.elapsed = QLabel("Elapsed: 0.0s")
        self.elapsed.setFont(QFont("Segoe UI", 9))
        self.elapsed.setAlignment(Qt.AlignCenter)
        self.elapsed.setStyleSheet("color: #8a9ab0;")
        layout.addWidget(self.elapsed)

        layout.addStretch()
        self.timer = QTimer()
        self.timer.timeout.connect(self._tick)
        self.timer.start(100)

    def _start(self):
        self.worker = SimulationWorker()
        self.worker.progress.connect(self._on_progress)
        self.worker.all_done.connect(self._on_done)
        self.worker.start()

    def _on_progress(self, cur, total, phase):
        self.bar.setValue(cur)
        self.status.setText(f"[{phase}]  {cur:,} / {total:,} sims  "
                            f"({cur / total * 100:.1f}%)")

    def _tick(self):
        self.elapsed.setText(f"Elapsed: {time.time() - self.start_time:.1f}s")

    def _on_done(self, results, snapshots):
        self.timer.stop()
        self.on_finished(results, snapshots)


# ---------------------------------------------------------------------------
# Reusable widgets
# ---------------------------------------------------------------------------
class StatCard(QFrame):
    def __init__(self, rank, team, value_str, accent):
        super().__init__()
        self.setFixedHeight(72)
        self.setStyleSheet(
            f"QFrame {{ background: #ffffff; border: 1px solid #d0d8e0;"
            f" border-left: 8px solid {accent}; border-radius: 10px; }}")
        h = QHBoxLayout(self); h.setContentsMargins(16, 6, 16, 6); h.setSpacing(14)

        rank_lbl = QLabel(str(rank))
        rank_lbl.setFont(QFont("Segoe UI", 22, QFont.Bold))
        rank_lbl.setStyleSheet(f"color: {accent}; border: none;")
        rank_lbl.setFixedWidth(46); rank_lbl.setAlignment(Qt.AlignCenter)
        h.addWidget(rank_lbl)

        team_lbl = QLabel(team)
        team_lbl.setFont(QFont("Segoe UI", 14, QFont.Bold))
        team_lbl.setStyleSheet("color: #1a3c5e; border: none;")
        h.addWidget(team_lbl, 1)

        val_lbl = QLabel(value_str)
        val_lbl.setFont(QFont("Segoe UI", 20, QFont.Bold))
        val_lbl.setStyleSheet(f"color: {accent}; border: none;")
        val_lbl.setAlignment(Qt.AlignRight | Qt.AlignVCenter)
        h.addWidget(val_lbl)


class HomeBlock(QFrame):
    def __init__(self, title, subtitle, preview_lines, accent, on_click):
        super().__init__()
        self._on_click = on_click; self._accent = accent
        self.setCursor(Qt.PointingHandCursor)
        self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        self._apply_style(False)
        v = QVBoxLayout(self); v.setContentsMargins(20, 16, 20, 16); v.setSpacing(6)
        v.addStretch()
        t = QLabel(title); t.setFont(QFont("Segoe UI", 17, QFont.Bold))
        t.setAlignment(Qt.AlignCenter); t.setWordWrap(True)
        t.setStyleSheet(f"color: {accent}; border: none;"); v.addWidget(t)
        s = QLabel(subtitle); s.setFont(QFont("Segoe UI", 10))
        s.setAlignment(Qt.AlignCenter)
        s.setStyleSheet("color: #5a7a9a; border: none;"); v.addWidget(s)
        v.addSpacing(6)
        for line in preview_lines:
            lab = QLabel(line); lab.setFont(QFont("Segoe UI", 10))
            lab.setAlignment(Qt.AlignCenter)
            lab.setStyleSheet("color: #1a3c5e; border: none;"); v.addWidget(lab)
        v.addStretch()
        hint = QLabel("Click to open  →")
        hint.setFont(QFont("Segoe UI", 9, QFont.Bold))
        hint.setAlignment(Qt.AlignCenter)
        hint.setStyleSheet("color: #8a9ab0; border: none;"); v.addWidget(hint)

    def _apply_style(self, hover):
        bg = "#eaf3fb" if hover else "#f7f9fc"
        border = self._accent if hover else "#d0d8e0"
        self.setStyleSheet(
            f"HomeBlock {{ background: {bg}; border: 3px solid {border};"
            f" border-radius: 14px; }}")

    def enterEvent(self, e): self._apply_style(True);  super().enterEvent(e)
    def leaveEvent(self, e): self._apply_style(False); super().leaveEvent(e)
    def mousePressEvent(self, e):
        if e.button() == Qt.LeftButton:
            self._on_click()


class LeagueRow(QFrame):
    clicked = pyqtSignal()
    def __init__(self, spec, team, pct_str):
        super().__init__()
        accent = spec["accent"]
        self.setCursor(Qt.PointingHandCursor)
        self.setFixedHeight(66)
        self.setStyleSheet(
            f"QFrame {{ background: #ffffff; border: 1px solid #d0d8e0;"
            f" border-left: 6px solid {accent}; border-radius: 8px; }}")
        h = QHBoxLayout(self); h.setContentsMargins(12, 6, 12, 6); h.setSpacing(8)
        v = QVBoxLayout(); v.setSpacing(2)
        t = QLabel(spec["title"]); t.setFont(QFont("Segoe UI", 10, QFont.Bold))
        t.setStyleSheet("color: #1a3c5e; border: none; background: transparent;")
        v.addWidget(t)
        s = QLabel(team); s.setFont(QFont("Segoe UI", 9))
        s.setStyleSheet("color: #6b7f95; border: none; background: transparent;")
        v.addWidget(s)
        h.addLayout(v, 1)
        p = QLabel(pct_str); p.setFont(QFont("Segoe UI", 13, QFont.Bold))
        p.setStyleSheet(f"color: {accent}; border: none; background: transparent;")
        p.setAlignment(Qt.AlignRight | Qt.AlignVCenter); h.addWidget(p)

    def mousePressEvent(self, e):
        if e.button() == Qt.LeftButton:
            self.clicked.emit()


# ---------------------------------------------------------------------------
# Preview + card + table builders
# ---------------------------------------------------------------------------
def _league_preview(spec, results):
    r = results[spec["key"]]; key = spec["top_key"]
    teams = spec["get_teams"](r)
    top = sorted(teams, key=lambda t: -r[key].get(t, 0))[:3]
    lines = ["Top title contenders:"]
    for t in top:
        lines.append(f"  •  {t}  —  {r[key][t]:.1f}%")
    return lines


def _wc_preview(results):
    w = results["wc"]; qual = w["qualification_prob"]
    teams = [t for t in wc.TEAM_CONF if wc.TEAM_CONF[t] in wc.CONF_NAMES]
    cand = [(t, qual.get(t, 0.0)) for t in teams if qual.get(t, 0.0) < 1.0]
    cand.sort(key=lambda x: -x[1])
    lines = ["Top unqualified contenders:"]
    for t, p in cand[:3]:
        lines.append(f"  •  {t}  —  {p * 100:.1f}%")
    return lines


def _cards(spec, results):
    r = results[spec["key"]]; key = spec["top_key"]
    teams = spec["get_teams"](r)
    top = sorted(teams, key=lambda t: -r[key].get(t, 0))[:5]
    return [StatCard(i, t, spec["top_fmt"].format(r[key][t]), spec["accent"])
            for i, t in enumerate(top, 1)]


def _wc_cards(results):
    w = results["wc"]; qual = w["qualification_prob"]
    teams = [t for t in wc.TEAM_CONF if wc.TEAM_CONF[t] in wc.CONF_NAMES]
    cand = [(t, qual.get(t, 0.0)) for t in teams if qual.get(t, 0.0) < 1.0]
    cand.sort(key=lambda x: -x[1])
    return [StatCard(i, t, f"{p * 100:.2f}%", "#1e8a49")
            for i, (t, p) in enumerate(cand[:5], 1)]


def _make_table(headers):
    t = QTableWidget()
    t.setColumnCount(len(headers))
    t.setHorizontalHeaderLabels(headers)
    t.horizontalHeader().setSectionResizeMode(0, QHeaderView.Stretch)
    for i in range(1, len(headers)):
        t.horizontalHeader().setSectionResizeMode(i, QHeaderView.ResizeToContents)
    t.setAlternatingRowColors(True)
    t.setEditTriggers(QTableWidget.NoEditTriggers)
    t.verticalHeader().setVisible(False)
    t.setStyleSheet(_TABLE_QSS)
    return t


def _league_table(spec, results):
    r = results[spec["key"]]
    headers = ["Team"] + [c[0] for c in spec["columns"]]
    table = _make_table(headers)
    teams = sorted(spec["get_teams"](r), key=lambda t: -r["avg_points"].get(t, 0))
    table.setRowCount(len(teams))
    for row, team in enumerate(teams):
        name = QTableWidgetItem(team); name.setFont(QFont("Segoe UI", 10))
        table.setItem(row, 0, name)
        for col, (_, key, fmt) in enumerate(spec["columns"], 1):
            it = QTableWidgetItem(fmt.format(r[key].get(team, 0.0)))
            it.setTextAlignment(Qt.AlignRight | Qt.AlignVCenter)
            it.setFont(QFont("Segoe UI", 9))
            table.setItem(row, col, it)
    return table


def _wc_table(results):
    w = results["wc"]
    table = _make_table(["Team", "Confederation", "ELO", "Qualification %"])
    qual = w["qualification_prob"]
    teams = [t for t in wc.TEAM_CONF if wc.TEAM_CONF[t] in wc.CONF_NAMES]
    rows = sorted([(t, wc.TEAM_CONF[t], wc.get_elo(t), qual.get(t, 0.0))
                   for t in teams], key=lambda r: -r[3])
    table.setRowCount(len(rows))
    for row, (team, conf, elo, prob) in enumerate(rows):
        name = QTableWidgetItem(team); name.setFont(QFont("Segoe UI", 10))
        if prob >= 0.99:   name.setBackground(QColor("#d5f5e3"))
        elif prob >= 0.75: name.setBackground(QColor("#d6eaf8"))
        elif prob >= 0.5:  name.setBackground(QColor("#fef9e7"))
        elif prob > 0:     name.setBackground(QColor("#fadbd8"))
        table.setItem(row, 0, name)
        ci = QTableWidgetItem(conf); ci.setTextAlignment(Qt.AlignCenter)
        table.setItem(row, 1, ci)
        ei = QTableWidgetItem(f"{elo:.0f}")
        ei.setTextAlignment(Qt.AlignRight | Qt.AlignVCenter)
        table.setItem(row, 2, ei)
        pi = QTableWidgetItem(f"{prob * 100:.2f}%")
        pi.setTextAlignment(Qt.AlignRight | Qt.AlignVCenter)
        pi.setFont(QFont("Segoe UI", 10, QFont.Bold))
        if prob >= 0.99:   pi.setForeground(QColor("#1e8a49"))
        elif prob >= 0.5:  pi.setForeground(QColor("#2e86c1"))
        elif prob > 0:     pi.setForeground(QColor("#c0392b"))
        table.setItem(row, 3, pi)
    return table


def _build_detail_body(spec, results):
    if spec.get("is_wc"):
        return _wc_cards(results), _wc_table(results)
    return _cards(spec, results), _league_table(spec, results)


def _make_detail_body(spec, results, full=False):
    accent = spec["accent"]
    cards, table = _build_detail_body(spec, results)
    if full:
        table.setVerticalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        table.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        for i in range(table.columnCount()):
            table.horizontalHeader().setSectionResizeMode(i, QHeaderView.ResizeToContents)
        table.resizeColumnsToContents()
        vh = table.verticalHeader(); hh = table.horizontalHeader()
        rows_h = sum(vh.sectionSize(i) for i in range(table.rowCount()))
        cols_w = sum(table.columnWidth(i) for i in range(table.columnCount()))
        hdr_h = max(hh.height(), hh.sizeHint().height())
        table.setFixedSize(cols_w + 2 * table.frameWidth() + 6,
                           hdr_h + rows_h + 2 * table.frameWidth() + 6)
    body = QWidget()
    lay = QHBoxLayout(body); lay.setContentsMargins(0, 0, 0, 0); lay.setSpacing(14)
    left_frame = QFrame()
    left_frame.setStyleSheet(
        "QFrame { background: #f7f9fc; border: 1px solid #d0d8e0; border-radius: 12px; }")
    lv = QVBoxLayout(left_frame); lv.setContentsMargins(12, 10, 12, 12); lv.setSpacing(8)
    head = QLabel("Top 5 — by probability")
    head.setFont(QFont("Segoe UI", 12, QFont.Bold))
    head.setStyleSheet(f"color: {accent}; border: none; background: transparent;")
    lv.addWidget(head)
    for c in cards: lv.addWidget(c)
    lv.addStretch()
    right_frame = QFrame()
    right_frame.setStyleSheet(
        "QFrame { background: #ffffff; border: 1px solid #d0d8e0; border-radius: 12px; }")
    rv = QVBoxLayout(right_frame); rv.setContentsMargins(12, 10, 12, 12); rv.setSpacing(8)
    rh = QLabel("Full table")
    rh.setFont(QFont("Segoe UI", 12, QFont.Bold))
    rh.setStyleSheet(f"color: {accent}; border: none; background: transparent;")
    rv.addWidget(rh); rv.addWidget(table)
    lay.addWidget(left_frame, 2); lay.addWidget(right_frame, 3)
    return body


# ---------------------------------------------------------------------------
# PNG export (unchanged)
# ---------------------------------------------------------------------------
def _render_detail_png(spec, results, path, scale=2):
    container = QWidget(); container.setStyleSheet("background: #ffffff;")
    v = QVBoxLayout(container); v.setContentsMargins(22, 18, 22, 18); v.setSpacing(10)
    title = QLabel(f"{spec['title']}  —  {spec['subtitle']}")
    title.setFont(QFont("Segoe UI", 16, QFont.Bold))
    title.setStyleSheet(f"color: {spec['accent']}; background: transparent;")
    v.addWidget(title)
    sub = QLabel(f"Predicted tables  ·  {spec['n_sims']:,} Monte Carlo simulations")
    sub.setFont(QFont("Segoe UI", 9))
    sub.setStyleSheet("color: #7a8ba0; background: transparent;")
    v.addWidget(sub)
    body = _make_detail_body(spec, results, full=True)
    v.addWidget(body)
    container.setAttribute(Qt.WA_DontShowOnScreen, True)
    container.show(); container.adjustSize(); QApplication.processEvents()
    size = container.size()
    if size.width() < 480: size.setWidth(480)
    pix = QPixmap(size.width() * scale, size.height() * scale)
    pix.fill(QColor("#ffffff"))
    painter = QPainter(pix)
    painter.setRenderHint(QPainter.Antialiasing, True)
    painter.setRenderHint(QPainter.TextAntialiasing, True)
    painter.scale(scale, scale)
    container.render(painter); painter.end()
    container.hide(); container.deleteLater()
    if not pix.save(path, "PNG"):
        raise RuntimeError("Could not write the PNG file.")


# ---------------------------------------------------------------------------
# World map data + widget (unchanged)
# ---------------------------------------------------------------------------
_CONTINENTS = {
    "North America": [[(-168, 66), (-160, 71), (-140, 70), (-125, 70), (-110, 69), (-95, 72),
                       (-82, 73), (-70, 68), (-60, 60), (-55, 52), (-60, 47), (-67, 45),
                       (-70, 42), (-75, 36), (-81, 31), (-81, 25), (-84, 30), (-90, 29),
                       (-97, 26), (-97, 22), (-95, 18), (-90, 20), (-86, 15), (-83, 9),
                       (-79, 9), (-83, 15), (-88, 18), (-95, 16), (-105, 19), (-110, 24),
                       (-114, 30), (-120, 34), (-124, 41), (-124, 49), (-130, 55),
                       (-140, 60), (-150, 60), (-160, 58), (-165, 60)]],
    "South America": [[(-81, 8), (-77, 8), (-72, 11), (-64, 11), (-60, 8), (-52, 5),
                       (-50, 0), (-44, -2), (-35, -6), (-38, -13), (-42, -23), (-48, -26),
                       (-53, -34), (-58, -38), (-62, -40), (-65, -45), (-68, -52),
                       (-70, -55), (-73, -52), (-75, -45), (-73, -37), (-71, -30),
                       (-70, -20), (-75, -14), (-78, -6), (-80, 0)]],
    "Europe": [[(-9, 43), (-9, 37), (-6, 36), (-2, 37), (3, 42), (7, 44), (12, 45),
                (16, 42), (19, 40), (24, 40), (28, 41), (29, 41), (28, 45), (30, 46),
                (34, 45), (40, 45), (40, 50), (38, 55), (34, 60), (30, 60), (31, 62),
                (30, 66), (25, 70), (20, 70), (15, 68), (12, 64), (8, 58), (4, 58),
                (0, 55), (-3, 50), (-5, 48), (-9, 44)],
               [(-6, 50), (-3, 51), (1, 51), (1, 53), (-1, 54), (-2, 56), (-4, 58),
                (-6, 58), (-6, 55), (-5, 53)],
               [(-10, 52), (-6, 52), (-6, 55), (-10, 55)]],
    "Africa": [[(-17, 15), (-16, 12), (-8, 5), (0, 5), (5, 5), (9, 4), (9, 0),
                (12, -5), (12, -17), (15, -22), (15, -28), (18, -34), (20, -35),
                (25, -34), (32, -29), (35, -25), (40, -16), (41, -10), (40, -3),
                (43, 2), (51, 12), (43, 12), (38, 18), (35, 22), (33, 28), (32, 32),
                (25, 32), (15, 33), (10, 37), (0, 36), (-10, 30), (-17, 21)],
               [(43, -13), (50, -15), (48, -25), (44, -25), (43, -18)]],
    "Asia": [[(40, 45), (50, 45), (60, 45), (65, 42), (70, 40), (75, 40), (80, 42),
              (85, 42), (90, 42), (95, 42), (100, 40), (105, 40), (110, 40),
              (115, 38), (120, 40), (122, 40), (126, 40), (128, 43), (130, 43),
              (132, 45), (135, 46), (140, 48), (142, 53), (145, 50), (150, 58),
              (160, 60), (170, 63), (180, 65), (180, 70), (170, 70), (160, 70),
              (140, 73), (120, 74), (100, 77), (80, 74), (70, 72), (60, 70),
              (55, 68), (50, 68), (45, 66), (40, 66), (35, 66), (30, 66),
              (31, 62), (30, 60), (34, 60), (38, 55), (40, 50)],
             [(95, 5), (100, 2), (105, -2), (110, -3), (115, -4), (120, -4),
              (125, -3), (130, -2), (135, -2), (140, -3), (140, 2), (130, 2),
              (120, 3), (110, 4), (100, 6)]],
    "Oceania": [[(113, -22), (114, -26), (115, -34), (118, -35), (122, -34),
                 (129, -32), (135, -35), (138, -35), (141, -38), (147, -38),
                 (150, -37), (153, -28), (153, -25), (146, -19), (142, -11),
                 (136, -12), (132, -11), (129, -15), (125, -14), (122, -17),
                 (117, -20)],
                [(173, -35), (178, -38), (174, -42), (170, -46), (167, -46), (170, -42)]],
}

_LABEL_TITLE_FONT = QFont("Segoe UI", 8, QFont.Bold)
_LABEL_VAL_FONT = QFont("Segoe UI", 8)


class WorldMapWidget(QWidget):
    league_clicked = pyqtSignal(str)
    continent_selected = pyqtSignal(object)

    def __init__(self, results):
        super().__init__()
        self.results = results
        self.setMinimumHeight(380)
        self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        self.setMouseTracking(True)
        self._hover_key = None
        self._hover_cont = None
        self._selected_cont = None
        self._markers = []
        self._continent_paths = {}
        self._build_geometry()

    def _map_rect(self):
        margin = 8.0
        avail_w = self.width() - 2 * margin
        avail_h = self.height() - 2 * margin
        if avail_w <= 10 or avail_h <= 10:
            return QRectF(margin, margin, max(avail_w, 10.0), max(avail_h, 10.0))
        if avail_w > avail_h * 2.0:
            mw = avail_h * 2.0; mh = avail_h
        else:
            mw = avail_w; mh = avail_w / 2.0
        x = margin + (avail_w - mw) / 2.0
        y = margin + (avail_h - mh) / 2.0
        return QRectF(x, y, mw, mh)

    def _to_screen(self, lon, lat, rect):
        return QPointF(rect.left() + (lon + 180.0) / 360.0 * rect.width(),
                       rect.top() + (90.0 - lat) / 180.0 * rect.height())

    def _build_geometry(self):
        rect = self._map_rect()
        self._continent_paths = {}
        for name, polys in _CONTINENTS.items():
            path = QPainterPath()
            for poly in polys:
                pts = [self._to_screen(lon, lat, rect) for lon, lat in poly]
                path.addPolygon(QPolygonF(pts)); path.closeSubpath()
            self._continent_paths[name] = path
        fm_t = QFontMetrics(_LABEL_TITLE_FONT); fm_v = QFontMetrics(_LABEL_VAL_FONT)
        self._markers = []
        for spec in LEAGUES:
            geo = spec["geo"]
            dot = self._to_screen(geo["lon"], geo["lat"], rect)
            team, _pct, pct_str = _league_leader(spec, self.results)
            t1 = spec.get("short", spec["title"]); t2 = f"{team}  {pct_str}"
            w = max(_text_width(fm_t, t1), _text_width(fm_v, t2)) + 18
            h = fm_t.height() + fm_v.height() + 12
            ax = dot.x() + geo["dx"] * rect.width()
            ay = dot.y() + geo["dy"] * rect.height()
            box = QRectF(ax - w / 2.0, ay - h / 2.0, w, h)
            if box.left() < rect.left() + 2: box.moveLeft(rect.left() + 2)
            if box.right() > rect.right() - 2: box.moveRight(rect.right() - 2)
            if box.top() < rect.top() + 2: box.moveTop(rect.top() + 2)
            if box.bottom() > rect.bottom() - 2: box.moveBottom(rect.bottom() - 2)
            self._markers.append({"key": spec["key"], "accent": spec["accent"],
                                  "dot": dot, "box": box, "t1": t1, "t2": t2,
                                  "global": spec["key"] == "wc"})

    def paintEvent(self, ev):
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing, True)
        p.setRenderHint(QPainter.TextAntialiasing, True)
        grad = QLinearGradient(0, 0, 0, self.height())
        grad.setColorAt(0.0, QColor("#f4f9fd")); grad.setColorAt(1.0, QColor("#e7f1f9"))
        p.fillRect(self.rect(), QBrush(grad))
        rect = self._map_rect()
        p.save(); p.setClipRect(rect)
        p.setPen(QPen(QColor(190, 210, 228, 110), 0.6))
        for lon in range(-150, 181, 30):
            x = self._to_screen(lon, 0, rect).x()
            p.drawLine(QPointF(x, rect.top()), QPointF(x, rect.bottom()))
        for lat in range(-60, 90, 30):
            y = self._to_screen(0, lat, rect).y()
            p.drawLine(QPointF(rect.left(), y), QPointF(rect.right(), y))
        p.restore()
        for name, path in self._continent_paths.items():
            fill = (QColor("#c3dbf1") if name in (self._hover_cont, self._selected_cont)
                    else QColor("#dce8f4"))
            p.setBrush(fill); p.setPen(QPen(QColor("#a9c0d6"), 1.0)); p.drawPath(path)
        p.setBrush(Qt.NoBrush); p.setPen(QPen(QColor("#b9cde0"), 1.2))
        p.drawRoundedRect(rect, 10, 10)
        if self._hover_cont:
            fm = QFontMetrics(_LABEL_TITLE_FONT)
            cw = _text_width(fm, self._hover_cont) + 22; ch = fm.height() + 10
            chip = QRectF(rect.left() + 10, rect.top() + 10, cw, ch)
            p.setPen(Qt.NoPen); p.setBrush(QColor(26, 60, 94, 205))
            p.drawRoundedRect(chip, 8, 8); p.setPen(QColor("#ffffff"))
            p.setFont(_LABEL_TITLE_FONT); p.drawText(chip, Qt.AlignCenter, self._hover_cont)
        for m in self._markers:
            accent = QColor(m["accent"]); hovered = (m["key"] == self._hover_key)
            box = m["box"]; dot = m["dot"]
            p.setPen(QPen(QColor(accent.red(), accent.green(), accent.blue(), 170),
                          1.2, Qt.DashLine))
            p.drawLine(dot, self._edge_point(box, dot))
            if m["global"]:
                p.setBrush(Qt.NoBrush)
                p.setPen(QPen(accent, 1.6, Qt.DashLine))
                p.drawEllipse(dot, 11, 11)
            p.setBrush(accent); p.setPen(QPen(QColor("#ffffff"), 2.0))
            p.drawEllipse(dot, 6.5 if hovered else 5.5, 6.5 if hovered else 5.5)
            p.setBrush(QColor(255, 255, 255, 238))
            p.setPen(QPen(accent, 2.0 if hovered else 1.3))
            p.drawRoundedRect(box, 7, 7)
            p.setPen(QColor("#1a3c5e")); p.setFont(_LABEL_TITLE_FONT)
            p.drawText(QRectF(box.left() + 8, box.top() + 4,
                              box.width() - 16, box.height() / 2 - 2),
                       Qt.AlignLeft | Qt.AlignVCenter, m["t1"])
            p.setPen(accent); p.setFont(_LABEL_VAL_FONT)
            p.drawText(QRectF(box.left() + 8, box.center().y(),
                              box.width() - 16, box.height() / 2 - 4),
                       Qt.AlignLeft | Qt.AlignVCenter, m["t2"])
        p.end()

    @staticmethod
    def _edge_point(box, pt):
        x = min(max(pt.x(), box.left()), box.right())
        y = min(max(pt.y(), box.top()), box.bottom())
        return QPointF(x, y)

    def _hit_marker(self, pos):
        pt = QPointF(pos)
        for m in self._markers:
            if m["box"].contains(pt): return m["key"]
            if (pt - m["dot"]).manhattanLength() <= 16: return m["key"]
        return None

    def _hit_continent(self, pos):
        pt = QPointF(pos)
        for name, path in self._continent_paths.items():
            if path.contains(pt): return name
        return None

    def set_selected_continent(self, name):
        self._selected_cont = name; self.update()

    def mouseMoveEvent(self, e):
        key = self._hit_marker(e.pos())
        cont = None if key else self._hit_continent(e.pos())
        if key != self._hover_key or cont != self._hover_cont:
            self._hover_key = key; self._hover_cont = cont
            self.setCursor(Qt.PointingHandCursor if (key or cont) else Qt.ArrowCursor)
            self.update()
        super().mouseMoveEvent(e)

    def leaveEvent(self, e):
        if self._hover_key or self._hover_cont:
            self._hover_key = None; self._hover_cont = None; self.update()
        super().leaveEvent(e)

    def mousePressEvent(self, e):
        if e.button() != Qt.LeftButton: return
        key = self._hit_marker(e.pos())
        if key:
            self.league_clicked.emit(key); return
        cont = self._hit_continent(e.pos())
        self._selected_cont = None if cont == self._selected_cont else cont
        self.continent_selected.emit(self._selected_cont); self.update()

    def resizeEvent(self, e):
        self._build_geometry(); super().resizeEvent(e)


# ---------------------------------------------------------------------------
# World map screen (unchanged)
# ---------------------------------------------------------------------------
class MapSidePanel(QWidget):
    league_clicked = pyqtSignal(str)
    show_all = pyqtSignal()

    def __init__(self, results):
        super().__init__()
        self.results = results
        self._continent = None
        self.setFixedWidth(330)
        v = QVBoxLayout(self); v.setContentsMargins(0, 0, 0, 0); v.setSpacing(8)
        self.title = QLabel("All competitions")
        self.title.setFont(QFont("Segoe UI", 13, QFont.Bold))
        self.title.setStyleSheet("color: #1a3c5e;"); v.addWidget(self.title)
        self.hint = QLabel("Click a continent on the map to filter it, or click any "
                           "league marker / row to open its predicted tables.")
        self.hint.setFont(QFont("Segoe UI", 9)); self.hint.setWordWrap(True)
        self.hint.setStyleSheet("color: #7a8ba0;"); v.addWidget(self.hint)
        scroll = QScrollArea(); scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.NoFrame)
        scroll.setStyleSheet("QScrollArea { background: transparent; }")
        self._host = QWidget(); self._host.setStyleSheet("background: transparent;")
        self._lay = QVBoxLayout(self._host); self._lay.setContentsMargins(0, 0, 0, 0)
        self._lay.setSpacing(8); scroll.setWidget(self._host)
        v.addWidget(scroll, 1)
        self._clear_btn = QPushButton("Show all competitions")
        self._clear_btn.setCursor(Qt.PointingHandCursor)
        self._clear_btn.setFont(QFont("Segoe UI", 10, QFont.Bold))
        self._clear_btn.setStyleSheet(
            "QPushButton { background: #ffffff; color: #1a3c5e;"
            " border: 2px solid #1a3c5e; padding: 7px 14px; border-radius: 8px; }"
            "QPushButton:hover { background: #1a3c5e; color: #ffffff; }")
        self._clear_btn.clicked.connect(self.show_all.emit)
        v.addWidget(self._clear_btn)
        self.set_continent(None)

    def set_continent(self, name):
        self._continent = name
        while self._lay.count():
            item = self._lay.takeAt(0); w = item.widget()
            if w is not None: w.deleteLater()
        self.title.setText(name if name else "All competitions")
        self._clear_btn.setVisible(name is not None)
        specs = [s for s in LEAGUES if name is None or s.get("continent") == name]
        if not specs:
            empty = QLabel("No competitions in this region.")
            empty.setStyleSheet("color: #8a9ab0;"); empty.setWordWrap(True)
            self._lay.addWidget(empty)
        for spec in specs:
            team, _pct, pct_str = _league_leader(spec, self.results)
            row = LeagueRow(spec, team, pct_str)
            row.clicked.connect(lambda k=spec["key"]: self.league_clicked.emit(k))
            self._lay.addWidget(row)
        self._lay.addStretch()


class MapScreen(QWidget):
    def __init__(self, results, on_open, on_back):
        super().__init__()
        outer = QVBoxLayout(self); outer.setContentsMargins(14, 12, 14, 12)
        outer.setSpacing(10)
        top = QHBoxLayout(); top.setSpacing(12)
        back = QPushButton("←  Back"); back.setCursor(Qt.PointingHandCursor)
        back.setFont(QFont("Segoe UI", 11, QFont.Bold))
        back.setStyleSheet(
            "QPushButton { background: #ffffff; color: #1a3c5e;"
            " border: 2px solid #1a3c5e; padding: 8px 18px; border-radius: 8px; }"
            "QPushButton:hover { background: #1a3c5e; color: #ffffff; }")
        back.clicked.connect(on_back); top.addWidget(back)
        lbl = QLabel("World Map  —  leagues by country")
        lbl.setFont(QFont("Segoe UI", 17, QFont.Bold))
        lbl.setStyleSheet("color: #1a3c5e;"); lbl.setAlignment(Qt.AlignCenter)
        top.addWidget(lbl, 1)
        spacer = QWidget(); spacer.setFixedWidth(back.sizeHint().width())
        top.addWidget(spacer); outer.addLayout(top)
        body = QHBoxLayout(); body.setSpacing(14)
        map_frame = QFrame()
        map_frame.setStyleSheet(
            "QFrame { background: #ffffff; border: 1px solid #d0d8e0; border-radius: 12px; }")
        mv = QVBoxLayout(map_frame); mv.setContentsMargins(6, 6, 6, 6)
        self.map = WorldMapWidget(results); mv.addWidget(self.map)
        self.panel = MapSidePanel(results)
        body.addWidget(map_frame, 3); body.addWidget(self.panel, 1)
        outer.addLayout(body, 1)
        self.map.league_clicked.connect(on_open)
        self.map.continent_selected.connect(self.panel.set_continent)
        self.panel.league_clicked.connect(on_open)
        self.panel.show_all.connect(self._clear_selection)

    def _clear_selection(self):
        self.map.set_selected_continent(None)
        self.panel.set_continent(None)


# ===========================================================================
# NEW: Video playback screen — 500-second animated table
# ===========================================================================
def _frozen_team_order(snaps):
    """Canonical row order for the whole video (prevents row-swapping)."""
    if not snaps:
        return []
    final = snaps[-1]
    avg_pts = final.get("avg_points", {})
    return sorted(avg_pts.keys(), key=lambda t: (-avg_pts.get(t, 0), t))


def _lerp_snapshots(a, b, frac):
    """Return an interpolated snapshot. All values are numeric."""
    out = {"done": int(round(a.get("done", 0) * (1 - frac) + b.get("done", 0) * frac)),
           "total": a.get("total", b.get("total", 0))}
    for key, va in a.items():
        if key in ("done", "total"):
            continue
        vb = b.get(key, va)
        if isinstance(va, dict):
            out[key] = {t: va[t] * (1 - frac) + vb.get(t, va[t]) * frac
                        for t in va.keys()}
        else:
            try:
                out[key] = va * (1 - frac) + vb * frac
            except TypeError:
                out[key] = va
    return out


class VideoScreen(QWidget):
    DEFAULT_DURATION = 500.0    # seconds, as requested
    TICK_MS = 50                # 20 fps UI updates

    def __init__(self, results, snapshots, on_back):
        super().__init__()
        self._on_back = on_back
        self._results = results
        self._snapshots = snapshots
        self._spec = None
        self._snaps = []
        self._current_time = 0.0
        self._duration = self.DEFAULT_DURATION
        self._playing = False
        self._table = None

        self._video_leagues = [
            s for s in LEAGUES
            if s.get("has_video", True)
            and s["key"] in snapshots
            and len(snapshots[s["key"]]) >= 2
        ]

        self._build_ui()
        if self._video_leagues:
            self._select_league(self._video_leagues[0]["key"])

    def _build_ui(self):
        outer = QVBoxLayout(self); outer.setContentsMargins(14, 12, 14, 12)
        outer.setSpacing(10)

        top = QHBoxLayout(); top.setSpacing(10)
        back = QPushButton("←  Back"); back.setCursor(Qt.PointingHandCursor)
        back.setFont(QFont("Segoe UI", 11, QFont.Bold))
        back.setStyleSheet(
            "QPushButton { background: #ffffff; color: #1a3c5e;"
            " border: 2px solid #1a3c5e; padding: 8px 18px; border-radius: 8px; }"
            "QPushButton:hover { background: #1a3c5e; color: #ffffff; }")
        back.clicked.connect(self._on_back); top.addWidget(back)

        header = QLabel("Progress Video  —  table over simulations")
        header.setFont(QFont("Segoe UI", 15, QFont.Bold))
        header.setAlignment(Qt.AlignCenter)
        header.setStyleSheet("color: #1a3c5e;"); top.addWidget(header, 1)

        self._selector = QComboBox()
        self._selector.setFont(QFont("Segoe UI", 10, QFont.Bold))
        for spec in self._video_leagues:
            self._selector.addItem(spec["title"], spec["key"])
        self._selector.currentIndexChanged.connect(self._on_select_changed)
        top.addWidget(self._selector)

        self._export_btn = QPushButton("Export MP4…")
        self._export_btn.setCursor(Qt.PointingHandCursor)
        self._export_btn.setFont(QFont("Segoe UI", 10, QFont.Bold))
        self._export_btn.setStyleSheet(
            "QPushButton { background: #1a3c5e; color: #ffffff;"
            " border: 2px solid #1a3c5e; padding: 8px 14px; border-radius: 8px; }"
            "QPushButton:hover { background: #ffffff; color: #1a3c5e; }")
        self._export_btn.clicked.connect(self._export_mp4)
        top.addWidget(self._export_btn)

        outer.addLayout(top)

        self._title_lbl = QLabel("")
        self._title_lbl.setFont(QFont("Segoe UI", 16, QFont.Bold))
        self._title_lbl.setAlignment(Qt.AlignCenter); outer.addWidget(self._title_lbl)

        self._sub_lbl = QLabel("")
        self._sub_lbl.setFont(QFont("Segoe UI", 10))
        self._sub_lbl.setAlignment(Qt.AlignCenter)
        self._sub_lbl.setStyleSheet("color: #5a7a9a;"); outer.addWidget(self._sub_lbl)

        self._table_host = QFrame()
        self._table_host.setStyleSheet(
            "QFrame { background: #ffffff; border: 1px solid #d0d8e0;"
            " border-radius: 12px; }")
        th = QVBoxLayout(self._table_host)
        th.setContentsMargins(12, 10, 12, 12); th.setSpacing(8)
        self._table_layout = th
        outer.addWidget(self._table_host, 1)

        controls = QHBoxLayout(); controls.setSpacing(10)
        self._play_btn = QPushButton("▶  Play")
        self._play_btn.setCheckable(True)
        self._play_btn.setCursor(Qt.PointingHandCursor)
        self._play_btn.setFont(QFont("Segoe UI", 10, QFont.Bold))
        self._play_btn.setStyleSheet(
            "QPushButton { background: #ffffff; color: #1a3c5e;"
            " border: 2px solid #1a3c5e; padding: 6px 18px; border-radius: 8px; }"
            "QPushButton:hover { background: #eaf3fb; }")
        self._play_btn.clicked.connect(self._toggle_play)
        controls.addWidget(self._play_btn)

        self._slider = QSlider(Qt.Horizontal)
        self._slider.setRange(0, 100000)
        self._slider.sliderMoved.connect(self._on_slider)
        controls.addWidget(self._slider, 1)

        self._time_lbl = QLabel(f"0.0s / {self._duration:.0f}s")
        self._time_lbl.setFont(QFont("Segoe UI", 10, QFont.Bold))
        self._time_lbl.setStyleSheet("color: #1a3c5e;")
        self._time_lbl.setMinimumWidth(240)
        self._time_lbl.setAlignment(Qt.AlignRight | Qt.AlignVCenter)
        controls.addWidget(self._time_lbl)
        outer.addLayout(controls)

        self._timer = QTimer(self)
        self._timer.timeout.connect(self._tick)

    # ---- selection & rebuild ---------------------------------------
    def _on_select_changed(self, idx):
        if 0 <= idx < len(self._video_leagues):
            self._select_league(self._video_leagues[idx]["key"])

    def _select_league(self, key):
        spec = next((s for s in LEAGUES if s["key"] == key), None)
        if spec is None:
            return
        self._spec = spec
        self._snaps = self._snapshots.get(key, [])
        self._team_order = _frozen_team_order(self._snaps)   # <-- new

        self._title_lbl.setText(f"{spec['title']}  —  {spec['subtitle']}")
        self._title_lbl.setStyleSheet(f"color: {spec['accent']};")
        self._sub_lbl.setText(
            f"Playback: {self._duration:.0f}s  ·  "
            f"{len(self._snaps)} snapshots  ·  {spec['n_sims']:,} sims")

        while self._table_layout.count():
            item = self._table_layout.takeAt(0); w = item.widget()
            if w is not None: w.deleteLater()

        headers = ["Team"] + [c[0] for c in spec["columns"]]
        self._table = _make_table(headers)
        first = self._snaps[0] if self._snaps else {}
        n_rows = len(first.get("avg_points", {}))
        self._table.setRowCount(n_rows)
        for row in range(n_rows):
            self._table.setItem(row, 0, QTableWidgetItem(""))
            for col in range(1, len(headers)):
                it = QTableWidgetItem("")
                it.setTextAlignment(Qt.AlignRight | Qt.AlignVCenter)
                it.setFont(QFont("Segoe UI", 9))
                self._table.setItem(row, col, it)
        self._table_layout.addWidget(self._table)

        self._playing = False
        self._play_btn.setChecked(False)
        self._play_btn.setText("▶  Play")
        self._timer.stop()
        self._current_time = 0.0
        self._slider.setValue(0)
        self._render_frame()

    # ---- frame math -------------------------------------------------
    def _current_snapshot(self):
        n = len(self._snaps)
        if n == 0: return {}
        if n == 1: return self._snaps[0]
        pos = (self._current_time / self._duration) * (n - 1)
        i = int(pos)
        if i >= n - 1:
            i = n - 2; frac = 1.0
        else:
            frac = pos - i
        return _lerp_snapshots(self._snaps[i], self._snaps[i + 1], frac)

    def _render_frame(self):
        if not self._spec or not self._snaps or self._table is None:
            return
        snap = self._current_snapshot()
        spec = self._spec
        # NOTE: use the fixed order from the final snapshot, not a fresh sort,
        # so rows don't swap positions mid-playback.
        teams = self._team_order
        for row, team in enumerate(teams):
            if row >= self._table.rowCount(): break
            self._table.item(row, 0).setText(team)
            for col, (_, key, fmt) in enumerate(spec["columns"], 1):
                val = snap.get(key, {}).get(team, 0.0)
                self._table.item(row, col).setText(fmt.format(val))
        done = snap.get("done", 0); total = snap.get("total", 0)
        self._time_lbl.setText(
            f"{self._current_time:6.1f}s / {self._duration:.0f}s   "
            f"(sim {done:,}/{total:,})")

    # ---- playback ---------------------------------------------------
    def _toggle_play(self):
        self._playing = self._play_btn.isChecked()
        if self._playing:
            if self._current_time >= self._duration:
                self._current_time = 0.0
            self._play_btn.setText("⏸  Pause")
            self._timer.start(self.TICK_MS)
        else:
            self._play_btn.setText("▶  Play")
            self._timer.stop()

    def _tick(self):
        self._current_time += self.TICK_MS / 1000.0
        if self._current_time >= self._duration:
            self._current_time = self._duration
            self._play_btn.setChecked(False)
            self._toggle_play()
        self._slider.blockSignals(True)
        self._slider.setValue(int(self._current_time / self._duration * 100000))
        self._slider.blockSignals(False)
        self._render_frame()

    def _on_slider(self, value):
        self._current_time = value / 100000.0 * self._duration
        self._render_frame()

    # ---- export -----------------------------------------------------
    def _export_mp4(self):
        if not self._spec or len(self._snaps) < 2:
            QMessageBox.warning(self, "Export failed", "No snapshots available.")
            return
        default_name = _safe_filename(f"{self._spec['title']}_progress") + ".mp4"
        default_path = str(Path.home() / default_name)
        path, _ = QFileDialog.getSaveFileName(
            self, "Save progress video", default_path, "MP4 video (*.mp4)")
        if not path: return
        if not path.lower().endswith(".mp4"): path += ".mp4"
        try:
            _export_progress_video(self, path)
        except Exception as exc:
            QMessageBox.warning(self, "Export failed", str(exc))


def _build_video_container(spec, snaps):
    container = QWidget(); container.setStyleSheet("background: #ffffff;")
    v = QVBoxLayout(container); v.setContentsMargins(28, 24, 28, 24); v.setSpacing(10)

    title = QLabel(f"{spec['title']}  —  {spec['subtitle']}")
    title.setFont(QFont("Segoe UI", 20, QFont.Bold))
    title.setStyleSheet(f"color: {spec['accent']}; background: transparent;")
    v.addWidget(title)

    total = snaps[-1].get("total", 0)
    sub = QLabel(f"Progression across {total:,} simulations  ·  sorted by average points")
    sub.setFont(QFont("Segoe UI", 11))
    sub.setStyleSheet("color: #7a8ba0; background: transparent;")
    v.addWidget(sub)

    headers = ["Team"] + [c[0] for c in spec["columns"]]
    table = _make_table(headers)
    n_rows = len(snaps[0].get("avg_points", {}))
    table.setRowCount(n_rows)
    for row in range(n_rows):
        table.setItem(row, 0, QTableWidgetItem(""))
        for col in range(1, len(headers)):
            it = QTableWidgetItem("")
            it.setTextAlignment(Qt.AlignRight | Qt.AlignVCenter)
            it.setFont(QFont("Segoe UI", 10))
            table.setItem(row, col, it)
    table.setObjectName("video_table")

    # Pre-populate with final snapshot so column widths are measured
    # against the widest content that will ever appear.
    final = snaps[-1]
    final_teams = sorted(
        final.get("avg_points", {}).keys(),
        key=lambda t: (-final["avg_points"].get(t, 0), t),
    )
    for row, team in enumerate(final_teams):
        if row >= table.rowCount():
            break
        table.item(row, 0).setText(team)
        for col, (_, key, fmt) in enumerate(spec["columns"], 1):
            val = final.get(key, {}).get(team, 0.0)
            table.item(row, col).setText(fmt.format(val))

    # Kill scrollbars, fix row height so every team is visible
    table.setVerticalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
    table.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
    table.verticalHeader().setVisible(False)
    table.verticalHeader().setDefaultSectionSize(24)

    hh = table.horizontalHeader()
    for i in range(table.columnCount()):
        hh.setSectionResizeMode(i, QHeaderView.ResizeToContents)
    table.resizeColumnsToContents()
    table.setColumnWidth(0, table.columnWidth(0) + 30)
    for i in range(table.columnCount()):
        hh.setSectionResizeMode(i, QHeaderView.Fixed)

    margins_w = 28 + 28
    min_table_w = 1280 - margins_w
    cols_w = sum(table.columnWidth(i) for i in range(table.columnCount()))
    inner_w = cols_w + 2 * table.frameWidth() + 4
    if inner_w < min_table_w:
        extra = min_table_w - inner_w
        table.setColumnWidth(0, table.columnWidth(0) + extra)
        cols_w = sum(table.columnWidth(i) for i in range(table.columnCount()))
        inner_w = cols_w + 2 * table.frameWidth() + 4
    table.setFixedWidth(inner_w)

    vh = table.verticalHeader()
    rows_h = sum(vh.sectionSize(i) for i in range(table.rowCount()))
    hdr_h = max(hh.height(), hh.sizeHint().height())
    table_h = hdr_h + rows_h + 2 * table.frameWidth() + 8
    table.setFixedHeight(table_h)
    table.setSizePolicy(QSizePolicy.Fixed, QSizePolicy.Fixed)

    v.addWidget(table, 0, Qt.AlignLeft)
    v.addStretch(1)

    status = QLabel("")
    status.setFont(QFont("Segoe UI", 10, QFont.Bold))
    status.setStyleSheet("color: #1a3c5e; background: transparent;")
    status.setAlignment(Qt.AlignCenter)
    status.setObjectName("status_label")
    v.addWidget(status)
    return container


def _update_video_container(container, spec, snap, team_order):
    table = container.findChild(QTableWidget, "video_table")
    if table is None:
        return
    for row, team in enumerate(team_order):
        if row >= table.rowCount():
            break
        table.item(row, 0).setText(team)
        for col, (_, key, fmt) in enumerate(spec["columns"], 1):
            val = snap.get(key, {}).get(team, 0.0)
            table.item(row, col).setText(fmt.format(val))
    status = container.findChild(QLabel, "status_label")
    if status is not None:
        status.setText(
            f"Simulation {snap.get('done', 0):,} / {snap.get('total', 0):,}"
        )


def _export_progress_video(screen, path):
    try:
        import cv2
        import numpy as np
    except ImportError as e:
        raise RuntimeError(
            "MP4 export needs opencv-python and numpy.\n"
            "Install with:  pip install opencv-python numpy") from e

    fps = 5
    duration = screen._duration
    n_frames = int(fps * duration)
    n_snaps = len(screen._snaps)
    if n_snaps < 2:
        raise RuntimeError("Not enough snapshots to render a video.")

    container = _build_video_container(screen._spec, screen._snaps)
    frozen_order = _frozen_team_order(screen._snaps)
    container.setAttribute(Qt.WA_DontShowOnScreen, True)
    container.show()
    QApplication.processEvents()
    container.adjustSize()
    QApplication.processEvents()
    size = container.size()
    W = max(size.width(), 1280)
    H = max(size.height(), 720)
    container.resize(W, H)
    QApplication.processEvents()

    fourcc = cv2.VideoWriter_fourcc(*"mp4v")
    writer = cv2.VideoWriter(path, fourcc, fps, (W, H))
    if not writer.isOpened():
        container.hide(); container.deleteLater()
        raise RuntimeError("OpenCV could not open the output file. "
                           "Try installing ffmpeg or using a different path.")

    progress = QProgressDialog("Rendering video…", "Cancel", 0, n_frames, screen)
    progress.setWindowModality(Qt.WindowModal)
    progress.setMinimumDuration(0)
    progress.setValue(0)

    try:
        for frame_i in range(n_frames):
            if progress.wasCanceled():
                break
            t = frame_i / (n_frames - 1) if n_frames > 1 else 0.0
            pos = t * (n_snaps - 1)
            i = int(pos)
            if i >= n_snaps - 1:
                i = n_snaps - 2
                frac = 1.0
            else:
                frac = pos - i
            snap = _lerp_snapshots(screen._snaps[i], screen._snaps[i + 1], frac)

            _update_video_container(container, screen._spec, snap, frozen_order)
            QApplication.processEvents()

            pix = QPixmap(W, H)
            pix.fill(QColor("#ffffff"))
            painter = QPainter(pix)
            painter.setRenderHint(QPainter.Antialiasing, True)
            painter.setRenderHint(QPainter.TextAntialiasing, True)
            container.render(painter)
            painter.end()

            img = pix.toImage().convertToFormat(QImage.Format_RGB888)
            ptr = img.bits(); ptr.setsize(img.byteCount())
            arr = np.frombuffer(ptr, np.uint8).reshape(
                img.height(), img.bytesPerLine()
            )[:, :img.width() * 3].reshape(img.height(), img.width(), 3)
            bgr = cv2.cvtColor(arr, cv2.COLOR_RGB2BGR)
            writer.write(bgr)

            if frame_i % 20 == 0:
                progress.setValue(frame_i)
                QApplication.processEvents()
    finally:
        writer.release()
        progress.setValue(n_frames)
        container.hide()
        container.deleteLater()

    QMessageBox.information(screen, "Saved", f"Video saved to:\n{path}")


# ---------------------------------------------------------------------------
# Home screen — now has a Video button
# ---------------------------------------------------------------------------
class HomeScreen(QWidget):
    def __init__(self, results, on_open, on_map, on_video):
        super().__init__()
        self.results = results
        outer = QVBoxLayout(self); outer.setContentsMargins(16, 14, 16, 14)
        outer.setSpacing(10)
        top = QHBoxLayout(); top.setSpacing(12)

        def _nav_button(text):
            b = QPushButton(text)
            b.setCursor(Qt.PointingHandCursor)
            b.setFont(QFont("Segoe UI", 11, QFont.Bold))
            b.setStyleSheet(
                "QPushButton { background: #ffffff; color: #1a3c5e;"
                " border: 2px solid #1a3c5e; padding: 8px 18px; border-radius: 8px; }"
                "QPushButton:hover { background: #1a3c5e; color: #ffffff; }")
            return b

        map_btn = _nav_button("World Map"); map_btn.clicked.connect(on_map)
        top.addWidget(map_btn)

        video_btn = _nav_button("Progress Video")
        video_btn.clicked.connect(on_video)
        top.addWidget(video_btn)

        header = QLabel("Simulation Results  —  click a panel")
        header.setFont(QFont("Segoe UI", 15, QFont.Bold))
        header.setAlignment(Qt.AlignCenter)
        header.setStyleSheet("color: #1a3c5e;")
        top.addWidget(header, 1)

        spacer = QWidget(); spacer.setFixedWidth(map_btn.sizeHint().width())
        top.addWidget(spacer)
        outer.addLayout(top)

        grid = QGridLayout(); grid.setSpacing(12)
        for idx, spec in enumerate(LEAGUES):
            preview = _wc_preview(results) if spec.get("is_wc") else _league_preview(spec, results)
            block = HomeBlock(title=spec["title"], subtitle=spec["subtitle"],
                              preview_lines=preview, accent=spec["accent"],
                              on_click=lambda k=spec["key"]: on_open(k))
            grid.addWidget(block, idx // 2, idx % 2)
        outer.addLayout(grid, 1)

        footer = QLabel(
            f"{len(LEAGUES)} competitions   |   {TOTAL_SIMS:,} total simulations"
            f"   |   ELO-based Monte Carlo")
        footer.setFont(QFont("Segoe UI", 9)); footer.setAlignment(Qt.AlignCenter)
        footer.setStyleSheet("color: #8a9ab0;")
        outer.addWidget(footer)


# ---------------------------------------------------------------------------
# Detail screen (unchanged)
# ---------------------------------------------------------------------------
class DetailScreen(QWidget):
    def __init__(self, spec, results, on_back):
        super().__init__()
        self._spec = spec; self._results = results
        accent = spec["accent"]
        outer = QVBoxLayout(self); outer.setContentsMargins(14, 12, 14, 12)
        outer.setSpacing(10)
        top = QHBoxLayout(); top.setSpacing(12)
        back = QPushButton("←  Back"); back.setCursor(Qt.PointingHandCursor)
        back.setFont(QFont("Segoe UI", 11, QFont.Bold))
        back.setStyleSheet(
            "QPushButton { background: #ffffff;"
            f" color: {accent}; border: 2px solid {accent};"
            " padding: 8px 18px; border-radius: 8px; }"
            f"QPushButton:hover {{ background: {accent}; color: #ffffff; }}")
        back.clicked.connect(on_back); top.addWidget(back)
        top.addStretch()
        lbl = QLabel(f"{spec['title']}  {spec['subtitle']}")
        lbl.setFont(QFont("Segoe UI", 17, QFont.Bold))
        lbl.setStyleSheet(f"color: {accent};")
        lbl.setAlignment(Qt.AlignCenter); top.addWidget(lbl)
        top.addStretch()
        export_btn = QPushButton("Save PNG"); export_btn.setCursor(Qt.PointingHandCursor)
        export_btn.setFont(QFont("Segoe UI", 11, QFont.Bold))
        export_btn.setStyleSheet(
            f"QPushButton {{ background: {accent}; color: #ffffff;"
            f" border: 2px solid {accent}; padding: 8px 18px; border-radius: 8px; }}"
            f"QPushButton:hover {{ background: #ffffff; color: {accent}; }}")
        export_btn.clicked.connect(self._export_png)
        top.addWidget(export_btn)
        outer.addLayout(top)
        outer.addWidget(_make_detail_body(spec, results, full=False), 1)

    def _export_png(self):
        spec = self._spec
        default_name = _safe_filename(f"{spec['title']} {spec['subtitle']}") + ".png"
        default_path = str(Path.home() / default_name)
        path, _ = QFileDialog.getSaveFileName(
            self, "Save predicted tables as PNG", default_path, "PNG image (*.png)")
        if not path: return
        if not path.lower().endswith(".png"): path += ".png"
        try:
            _render_detail_png(spec, self._results, path)
        except Exception as exc:
            QMessageBox.warning(self, "Export failed", str(exc)); return
        QMessageBox.information(self, "Saved", f"Predictions saved to:\n{path}")


# ---------------------------------------------------------------------------
# Main window
# ---------------------------------------------------------------------------
class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Simulation Dashboard  —  7 Competitions")
        self.resize(1400, 950)
        self.setMinimumSize(1100, 800)
        self.stack = QStackedWidget(); self.setCentralWidget(self.stack)
        self.progress = ProgressWidget(self._on_finished)
        self.stack.addWidget(self.progress)
        self._results = None; self._snapshots = {}
        self._home = None; self._map = None; self._video = None
        self._details = {}
        self._detail_origin = "home"

    def _on_finished(self, results, snapshots):
        self._results = results
        self._snapshots = snapshots
        self._home = HomeScreen(results, self._open_detail, self._open_map, self._open_video)
        self.stack.addWidget(self._home)
        self.stack.setCurrentWidget(self._home)
        self.progress.deleteLater()

    def _open_map(self):
        if self._map is None:
            self._map = MapScreen(self._results,
                                  on_open=lambda k: self._open_detail(k, origin="map"),
                                  on_back=self._show_home)
            self.stack.addWidget(self._map)
        self.stack.setCurrentWidget(self._map)

    def _open_video(self):
        if self._video is None:
            self._video = VideoScreen(self._results, self._snapshots, self._show_home)
            self.stack.addWidget(self._video)
        self.stack.setCurrentWidget(self._video)

    def _open_detail(self, key, origin="home"):
        self._detail_origin = origin
        if key not in self._details:
            spec = next(s for s in LEAGUES if s["key"] == key)
            self._details[key] = DetailScreen(spec, self._results,
                                              on_back=self._back_from_detail)
            self.stack.addWidget(self._details[key])
        self.stack.setCurrentWidget(self._details[key])

    def _back_from_detail(self):
        if self._detail_origin == "map" and self._map is not None:
            self.stack.setCurrentWidget(self._map)
        else:
            self._show_home()

    def _show_home(self):
        if self._home is not None:
            self.stack.setCurrentWidget(self._home)


def main():
    app = QApplication(sys.argv)
    app.setStyle("Fusion")
    app.setFont(QFont("Segoe UI", 9))
    w = MainWindow(); w.show()
    return app.exec_()


if __name__ == "__main__":
    sys.exit(main())