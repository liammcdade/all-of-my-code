"""Combined simulation dashboard.

Flow:
    Progress  ->  Home (two giant clickable blocks, left/right)
              ->  Detail (full-screen, itself split left/right)
                  Left  : big ranked state cards (top 5)
                  Right : full detailed table

Runs two simulations sequentially on one background thread behind a
single unified progress bar:

    1. FIFA Women's World Cup 2027 qualification  (../worldcupwomens/main.py)
    2. Premier League 2026/27                     (../premier-league/26-27-season.py)

Both modules must expose a `run_simulation()` function.
"""

import sys
import time
import importlib.util
from pathlib import Path

from PyQt5.QtCore import Qt, QThread, pyqtSignal, QTimer
from PyQt5.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QLabel, QProgressBar, QTableWidget, QTableWidgetItem,
    QHeaderView, QStackedWidget, QFrame, QPushButton, QSizePolicy,
)
from PyQt5.QtGui import QFont, QColor, QMouseEvent


# ---------------------------------------------------------------------------
# Load the two simulation modules (single source of truth)
# ---------------------------------------------------------------------------
_ROOT = Path(__file__).resolve().parent.parent


def _load_module(name, relpath):
    spec = importlib.util.spec_from_file_location(name, _ROOT / relpath)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


wc = _load_module("wc_sim", "worldcupwomens/main.py")
pl = _load_module("pl_sim", "premier-league/26-27-season.py")

WC_SIMS = wc.N_SIMS
PL_SIMS = pl.NUM_PL_SIMS
TOTAL_SIMS = WC_SIMS + PL_SIMS


# ---------------------------------------------------------------------------
# Styles
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


# ---------------------------------------------------------------------------
# Worker
# ---------------------------------------------------------------------------
class SimulationWorker(QThread):
    progress = pyqtSignal(int, int, str)
    all_done = pyqtSignal(dict, dict)

    def __init__(self):
        super().__init__()
        self._running = True

    def _emit(self, current, label):
        if self._running:
            self.progress.emit(current, TOTAL_SIMS, label)

    def run(self):
        wc_results = wc.run_simulation(
            WC_SIMS,
            on_progress=lambda s, _live: self._emit(s, "Women's World Cup 2027"),
            is_running=lambda: self._running,
        )
        if not self._running:
            return
        pl_results = pl.run_simulation(
            PL_SIMS,
            on_progress=lambda s, _total: self._emit(
                WC_SIMS + s, "Premier League 2026/27"
            ),
            is_running=lambda: self._running,
        )
        if not self._running:
            return
        self._emit(TOTAL_SIMS, "Complete")
        self.all_done.emit(wc_results, pl_results)

    def stop(self):
        self._running = False


# ---------------------------------------------------------------------------
# Progress screen
# ---------------------------------------------------------------------------
class ProgressWidget(QWidget):
    def __init__(self, on_finished_callback):
        super().__init__()
        self.on_finished_callback = on_finished_callback
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

        subtitle = QLabel("Women's World Cup 2027  +  Premier League 2026/27")
        subtitle.setFont(QFont("Segoe UI", 12))
        subtitle.setAlignment(Qt.AlignCenter)
        subtitle.setStyleSheet("color: #5a7a9a;")
        layout.addWidget(subtitle)

        self.progress_bar = QProgressBar()
        self.progress_bar.setRange(0, TOTAL_SIMS)
        self.progress_bar.setTextVisible(True)
        self.progress_bar.setFormat("%p%  (%v / %m sims)")
        self.progress_bar.setFixedHeight(32)
        self.progress_bar.setStyleSheet(_PROGRESS_QSS)
        layout.addWidget(self.progress_bar)

        self.status_label = QLabel("Initializing simulation...")
        self.status_label.setFont(QFont("Segoe UI", 11))
        self.status_label.setAlignment(Qt.AlignCenter)
        self.status_label.setStyleSheet("color: #4a6a8a;")
        layout.addWidget(self.status_label)

        self.elapsed_label = QLabel("Elapsed: 0.0s")
        self.elapsed_label.setFont(QFont("Segoe UI", 9))
        self.elapsed_label.setAlignment(Qt.AlignCenter)
        self.elapsed_label.setStyleSheet("color: #8a9ab0;")
        layout.addWidget(self.elapsed_label)

        layout.addStretch()

        self.timer = QTimer()
        self.timer.timeout.connect(self._tick)
        self.timer.start(100)

    def _start(self):
        self.worker = SimulationWorker()
        self.worker.progress.connect(self._on_progress)
        self.worker.all_done.connect(self._on_done)
        self.worker.start()

    def _on_progress(self, current, total, phase):
        self.progress_bar.setValue(current)
        self.status_label.setText(
            f"[{phase}]  {current:,} / {total:,} simulations "
            f"({current / total * 100:.1f}%)"
        )

    def _tick(self):
        self.elapsed_label.setText(
            f"Elapsed: {time.time() - self.start_time:.1f}s"
        )

    def _on_done(self, wc_results, pl_results):
        self.timer.stop()
        self.on_finished_callback(wc_results, pl_results)


# ---------------------------------------------------------------------------
# Big ranked card (used on detail screens)
# ---------------------------------------------------------------------------
class StatCard(QFrame):
    def __init__(self, rank, team, value_str, accent):
        super().__init__()
        self.setFixedHeight(78)
        self.setStyleSheet(
            f"QFrame {{ background: #ffffff;"
            f" border: 1px solid #d0d8e0;"
            f" border-left: 8px solid {accent};"
            f" border-radius: 10px; }}"
        )
        h = QHBoxLayout(self)
        h.setContentsMargins(18, 8, 18, 8)
        h.setSpacing(16)

        rank_lbl = QLabel(str(rank))
        rank_lbl.setFont(QFont("Segoe UI", 26, QFont.Bold))
        rank_lbl.setStyleSheet(f"color: {accent}; border: none;")
        rank_lbl.setFixedWidth(50)
        rank_lbl.setAlignment(Qt.AlignCenter)
        h.addWidget(rank_lbl)

        team_lbl = QLabel(team)
        team_lbl.setFont(QFont("Segoe UI", 16, QFont.Bold))
        team_lbl.setStyleSheet("color: #1a3c5e; border: none;")
        h.addWidget(team_lbl, 1)

        val_lbl = QLabel(value_str)
        val_lbl.setFont(QFont("Segoe UI", 22, QFont.Bold))
        val_lbl.setStyleSheet(f"color: {accent}; border: none;")
        val_lbl.setAlignment(Qt.AlignRight | Qt.AlignVCenter)
        h.addWidget(val_lbl)


# ---------------------------------------------------------------------------
# Clickable home block (occupies left or right half)
# ---------------------------------------------------------------------------
class HomeBlock(QFrame):
    """Giant clickable panel on the home screen."""

    def __init__(self, title, subtitle, preview_lines, accent, on_click):
        super().__init__()
        self._on_click = on_click
        self._accent = accent
        self.setCursor(Qt.PointingHandCursor)
        self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        self._apply_style(hover=False)

        v = QVBoxLayout(self)
        v.setContentsMargins(34, 34, 34, 34)
        v.setSpacing(14)
        v.addStretch()

        t = QLabel(title)
        t.setFont(QFont("Segoe UI", 26, QFont.Bold))
        t.setAlignment(Qt.AlignCenter)
        t.setStyleSheet(f"color: {accent}; border: none;")
        t.setWordWrap(True)
        v.addWidget(t)

        s = QLabel(subtitle)
        s.setFont(QFont("Segoe UI", 12))
        s.setAlignment(Qt.AlignCenter)
        s.setStyleSheet("color: #5a7a9a; border: none;")
        s.setWordWrap(True)
        v.addWidget(s)

        v.addSpacing(18)

        for line in preview_lines:
            lab = QLabel(line)
            lab.setFont(QFont("Segoe UI", 13))
            lab.setAlignment(Qt.AlignCenter)
            lab.setStyleSheet("color: #1a3c5e; border: none;")
            v.addWidget(lab)

        v.addStretch()

        hint = QLabel("Click to open  →")
        hint.setFont(QFont("Segoe UI", 10, QFont.Bold))
        hint.setAlignment(Qt.AlignCenter)
        hint.setStyleSheet("color: #8a9ab0; border: none;")
        v.addWidget(hint)

    def _apply_style(self, hover):
        bg = "#eaf3fb" if hover else "#f7f9fc"
        border = self._accent if hover else "#d0d8e0"
        self.setStyleSheet(
            f"HomeBlock {{ background: {bg};"
            f" border: 3px solid {border};"
            f" border-radius: 16px; }}"
        )

    def enterEvent(self, event):
        self._apply_style(hover=True)
        super().enterEvent(event)

    def leaveEvent(self, event):
        self._apply_style(hover=False)
        super().leaveEvent(event)

    def mousePressEvent(self, event: QMouseEvent):
        if event.button() == Qt.LeftButton:
            self._on_click()


# ---------------------------------------------------------------------------
# Home screen: two giant blocks left / right
# ---------------------------------------------------------------------------
class HomeScreen(QWidget):
    def __init__(self, wc_results, pl_results, on_open_pl, on_open_wc):
        super().__init__()
        self.wc = wc_results
        self.pl = pl_results
        self._setup_ui(on_open_pl, on_open_wc)

    def _setup_ui(self, on_open_pl, on_open_wc):
        outer = QVBoxLayout(self)
        outer.setContentsMargins(18, 18, 18, 18)
        outer.setSpacing(14)

        header = QLabel("Simulation Results  —  click a panel")
        header.setFont(QFont("Segoe UI", 15, QFont.Bold))
        header.setAlignment(Qt.AlignCenter)
        header.setStyleSheet("color: #1a3c5e;")
        outer.addWidget(header)

        row = QHBoxLayout()
        row.setSpacing(18)

        # Left: Premier League
        pl_preview = self._pl_preview_lines()
        left = HomeBlock(
            title="Premier League",
            subtitle="2026/27 Season",
            preview_lines=pl_preview,
            accent="#c9a227",
            on_click=on_open_pl,
        )
        row.addWidget(left, 1)

        # Right: Women's World Cup
        wc_preview = self._wc_preview_lines()
        right = HomeBlock(
            title="Women's World Cup",
            subtitle="2027 Qualification",
            preview_lines=wc_preview,
            accent="#1e8a49",
            on_click=on_open_wc,
        )
        row.addWidget(right, 1)

        outer.addLayout(row, 1)

        footer = QLabel(
            f"World Cup: {self.wc['n_sims']:,} sims   |   "
            f"Premier League: {self.pl['n_sims']:,} sims   |   "
            f"ELO-based Monte Carlo"
        )
        footer.setFont(QFont("Segoe UI", 9))
        footer.setAlignment(Qt.AlignCenter)
        footer.setStyleSheet("color: #8a9ab0;")
        outer.addWidget(footer)

    def _pl_preview_lines(self):
        r = self.pl
        top = sorted(r['pl_teams_set'],
                     key=lambda t: -r['title_prob'][t])[:3]
        lines = ["Top title contenders:"]
        for t in top:
            lines.append(f"  •  {t}  —  {r['title_prob'][t]:.1f}%")
        return lines

    def _wc_preview_lines(self):
        w = self.wc
        qual = w['qualification_prob']
        teams = [t for t in wc.TEAM_CONF if wc.TEAM_CONF[t] in wc.CONF_NAMES]
        contenders = [(t, qual.get(t, 0.0)) for t in teams
              if qual.get(t, 0.0) < 1.0]
        contenders.sort(key=lambda x: -x[1])
        lines = ["Top unqualified contenders:"]
        for t, p in contenders[:3]:
            lines.append(f"  •  {t}  —  {p * 100:.1f}%")
        return lines


# ---------------------------------------------------------------------------
# Detail screen: full-screen, split left/right
# ---------------------------------------------------------------------------
class DetailScreen(QWidget):
    def __init__(self, title, accent, left_content, right_content,
                 on_back):
        super().__init__()
        outer = QVBoxLayout(self)
        outer.setContentsMargins(14, 12, 14, 12)
        outer.setSpacing(10)

        # --- Top bar ---
        top = QHBoxLayout()
        top.setSpacing(12)

        back = QPushButton("←  Back")
        back.setCursor(Qt.PointingHandCursor)
        back.setFont(QFont("Segoe UI", 11, QFont.Bold))
        back.setStyleSheet(
            "QPushButton {"
            "  background: #ffffff;"
            f" color: {accent};"
            f" border: 2px solid {accent};"
            "  padding: 8px 18px;"
            "  border-radius: 8px;"
            "}"
            f"QPushButton:hover {{ background: {accent}; color: #ffffff; }}"
        )
        back.clicked.connect(on_back)
        top.addWidget(back)

        title_lbl = QLabel(title)
        title_lbl.setFont(QFont("Segoe UI", 17, QFont.Bold))
        title_lbl.setStyleSheet(f"color: {accent};")
        title_lbl.setAlignment(Qt.AlignCenter)
        top.addWidget(title_lbl, 1)

        # spacer to keep title centred
        spacer = QWidget()
        spacer.setFixedWidth(back.sizeHint().width())
        top.addWidget(spacer)

        outer.addLayout(top)

        # --- Split: left / right ---
        split = QHBoxLayout()
        split.setSpacing(16)

        left_frame = QFrame()
        left_frame.setStyleSheet(
            "QFrame { background: #f7f9fc;"
            " border: 1px solid #d0d8e0; border-radius: 12px; }"
        )
        lv = QVBoxLayout(left_frame)
        lv.setContentsMargins(14, 12, 14, 14)
        lv.setSpacing(10)

        l_head = QLabel("Top 5 — by probability")
        l_head.setFont(QFont("Segoe UI", 12, QFont.Bold))
        l_head.setStyleSheet("color: #1a3c5e; border: none;")
        lv.addWidget(l_head)
        for w in left_content:
            lv.addWidget(w)
        lv.addStretch()

        right_frame = QFrame()
        right_frame.setStyleSheet(
            "QFrame { background: #ffffff;"
            " border: 1px solid #d0d8e0; border-radius: 12px; }"
        )
        rv = QVBoxLayout(right_frame)
        rv.setContentsMargins(14, 12, 14, 14)
        rv.setSpacing(10)

        r_head = QLabel("Full table")
        r_head.setFont(QFont("Segoe UI", 12, QFont.Bold))
        r_head.setStyleSheet("color: #1a3c5e; border: none;")
        rv.addWidget(r_head)
        rv.addWidget(right_content)

        split.addWidget(left_frame, 2)
        split.addWidget(right_frame, 3)
        outer.addLayout(split, 1)


# ---------------------------------------------------------------------------
# Helpers: build the content shown inside each DetailScreen
# ---------------------------------------------------------------------------
_PL_PALETTE = ["#c9a227", "#7f8c8d", "#b87333", "#2e86c1", "#2e86c1"]
_WC_PALETTE = ["#1e8a49", "#2e86c1", "#2e86c1", "#2e86c1", "#2e86c1"]


def _accent_for(rank, palette):
    return palette[rank - 1] if rank - 1 < len(palette) else palette[-1]


def _make_table(headers, stretch_col=0):
    t = QTableWidget()
    t.setColumnCount(len(headers))
    t.setHorizontalHeaderLabels(headers)
    for i in range(len(headers)):
        mode = (QHeaderView.Stretch if i == stretch_col
                else QHeaderView.ResizeToContents)
        t.horizontalHeader().setSectionResizeMode(i, mode)
    t.setAlternatingRowColors(True)
    t.setEditTriggers(QTableWidget.NoEditTriggers)
    t.verticalHeader().setVisible(False)
    t.setStyleSheet(_TABLE_QSS)
    return t


def build_pl_left_cards(pl_results):
    r = pl_results
    top = sorted(r['pl_teams_set'], key=lambda t: -r['title_prob'][t])[:5]
    cards = []
    for i, team in enumerate(top, 1):
        cards.append(StatCard(
            rank=i,
            team=team,
            value_str=f"{r['title_prob'][team]:.1f}%",
            accent=_accent_for(i, _PL_PALETTE),
        ))
    return cards


def build_wc_left_cards(wc_results):
    w = wc_results
    qual = w['qualification_prob']
    teams = [t for t in wc.TEAM_CONF if wc.TEAM_CONF[t] in wc.CONF_NAMES]
    contenders = [(t, qual.get(t, 0.0)) for t in teams if qual.get(t, 0.0) < 1.0]
    contenders.sort(key=lambda x: -x[1])
    cards = []
    for i, (team, prob) in enumerate(contenders[:5], 1):
        cards.append(StatCard(
            rank=i,
            team=team,
            value_str=f"{prob * 100:.2f}%",
            accent=_accent_for(i, _WC_PALETTE),
        ))
    return cards


def build_wc_table(wc_results):
    w = wc_results
    table = _make_table(
        ["Team", "Confederation", "ELO", "Qualification %"],
        stretch_col=0,
    )
    qual = w['qualification_prob']
    teams = [t for t in wc.TEAM_CONF if wc.TEAM_CONF[t] in wc.CONF_NAMES]
    rows = sorted(
        ((t, wc.TEAM_CONF[t], wc.get_elo(t), qual.get(t, 0.0)) for t in teams),
        key=lambda r: -r[3],
    )
    table.setRowCount(len(rows))
    for row, (team, conf, elo, prob) in enumerate(rows):
        name_item = QTableWidgetItem(team)
        name_item.setFont(QFont("Segoe UI", 10))
        if prob >= 0.99:
            name_item.setBackground(QColor("#d5f5e3"))
        elif prob >= 0.75:
            name_item.setBackground(QColor("#d6eaf8"))
        elif prob >= 0.5:
            name_item.setBackground(QColor("#fef9e7"))
        elif prob > 0:
            name_item.setBackground(QColor("#fadbd8"))

        conf_item = QTableWidgetItem(conf)
        conf_item.setTextAlignment(Qt.AlignCenter)
        conf_item.setFont(QFont("Segoe UI", 9))

        elo_item = QTableWidgetItem(f"{elo:.0f}")
        elo_item.setTextAlignment(Qt.AlignRight | Qt.AlignVCenter)
        elo_item.setFont(QFont("Consolas", 9))

        prob_item = QTableWidgetItem(f"{prob * 100:.2f}%")
        prob_item.setTextAlignment(Qt.AlignRight | Qt.AlignVCenter)
        prob_item.setFont(QFont("Segoe UI", 10, QFont.Bold))
        if prob >= 0.99:
            prob_item.setForeground(QColor("#1e8a49"))
        elif prob >= 0.5:
            prob_item.setForeground(QColor("#2e86c1"))
        elif prob > 0:
            prob_item.setForeground(QColor("#c0392b"))

        table.setItem(row, 0, name_item)
        table.setItem(row, 1, conf_item)
        table.setItem(row, 2, elo_item)
        table.setItem(row, 3, prob_item)
    return table


def build_pl_table(pl_results):
    r = pl_results
    table = _make_table(
        ["Team", "Avg Pos", "Avg Pts",
         "Title %", "UCL %", "UEL %", "UECL %", "Releg %"],
        stretch_col=0,
    )
    teams = sorted(r['pl_teams_set'], key=lambda t: r['avg_positions'][t])
    table.setRowCount(len(teams))

    def num(text, bold=False, color=None):
        it = QTableWidgetItem(text)
        it.setTextAlignment(Qt.AlignRight | Qt.AlignVCenter)
        it.setFont(QFont("Segoe UI", 9,
                         QFont.Bold if bold else QFont.Normal))
        if color:
            it.setForeground(QColor(color))
        return it

    for row, team in enumerate(teams):
        ucl = r['ucl_qual_prob'][team]
        releg = r['relegation_prob'][team]

        name_item = QTableWidgetItem(team)
        name_item.setFont(QFont("Segoe UI", 10))
        if ucl >= 75:
            name_item.setBackground(QColor("#d6eaf8"))
        elif releg >= 50:
            name_item.setBackground(QColor("#fadbd8"))
        elif r['title_prob'][team] >= 25:
            name_item.setBackground(QColor("#d5f5e3"))

        table.setItem(row, 0, name_item)
        table.setItem(row, 1, num(f"{r['avg_positions'][team]:.2f}"))
        table.setItem(row, 2, num(f"{r['avg_points'][team]:.1f}"))
        table.setItem(row, 3, num(
            f"{r['title_prob'][team]:.2f}",
            bold=r['title_prob'][team] >= 10,
            color="#1e8a49" if r['title_prob'][team] >= 10 else None,
        ))
        table.setItem(row, 4, num(
            f"{ucl:.2f}",
            bold=ucl >= 50,
            color="#2e86c1" if ucl >= 50 else None,
        ))
        table.setItem(row, 5, num(f"{r['uel_qual_prob'][team]:.2f}"))
        table.setItem(row, 6, num(f"{r['uecl_qual_prob'][team]:.2f}"))
        table.setItem(row, 7, num(
            f"{releg:.2f}",
            bold=releg >= 25,
            color="#c0392b" if releg >= 25 else None,
        ))
    return table


# ---------------------------------------------------------------------------
# Main window: stacked Progress -> Home -> Detail(PL / WC)
# ---------------------------------------------------------------------------
class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Simulation Dashboard  —  WC 2027 + PL 2026/27")
        self.resize(1400, 900)
        self.setMinimumSize(1100, 750)

        self.stacked = QStackedWidget()
        self.setCentralWidget(self.stacked)

        self.progress_widget = ProgressWidget(self._on_done)
        self.stacked.addWidget(self.progress_widget)

        self._wc_results = None
        self._pl_results = None
        self._home = None
        self._pl_detail = None
        self._wc_detail = None

    # ------------------------------------------------------------------
    def _on_done(self, wc_results, pl_results):
        self._wc_results = wc_results
        self._pl_results = pl_results

        self._home = HomeScreen(
            wc_results=wc_results,
            pl_results=pl_results,
            on_open_pl=self._show_pl_detail,
            on_open_wc=self._show_wc_detail,
        )
        self.stacked.addWidget(self._home)
        self.stacked.setCurrentWidget(self._home)

        # Pre-build detail screens lazily on first open
        self.progress_widget.deleteLater()

    # ------------------------------------------------------------------
    def _show_pl_detail(self):
        if self._pl_detail is None:
            left_cards = build_pl_left_cards(self._pl_results)
            right_table = build_pl_table(self._pl_results)
            self._pl_detail = DetailScreen(
                title="Premier League 2026/27",
                accent="#c9a227",
                left_content=left_cards,
                right_content=right_table,
                on_back=self._show_home,
            )
            self.stacked.addWidget(self._pl_detail)
        self.stacked.setCurrentWidget(self._pl_detail)

    def _show_wc_detail(self):
        if self._wc_detail is None:
            left_cards = build_wc_left_cards(self._wc_results)
            right_table = build_wc_table(self._wc_results)
            self._wc_detail = DetailScreen(
                title="Women's World Cup 2027",
                accent="#1e8a49",
                left_content=left_cards,
                right_content=right_table,
                on_back=self._show_home,
            )
            self.stacked.addWidget(self._wc_detail)
        self.stacked.setCurrentWidget(self._wc_detail)

    def _show_home(self):
        if self._home is not None:
            self.stacked.setCurrentWidget(self._home)


# ---------------------------------------------------------------------------
def main():
    app = QApplication(sys.argv)
    app.setStyle("Fusion")
    app.setFont(QFont("Segoe UI", 9))
    window = MainWindow()
    window.show()
    return app.exec_()


if __name__ == "__main__":
    sys.exit(main())