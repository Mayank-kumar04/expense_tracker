"""
ui/analytics_page.py
---------------------
Full Analytics page: month selector + 4 embedded matplotlib charts
+ key stats cards.
"""

from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QComboBox,
    QScrollArea, QFrame, QGridLayout, QSizePolicy
)
from PyQt5.QtCore import Qt
from PyQt5.QtGui import QFont

from datetime import datetime, timedelta
from analytics.charts import (
    CategoryPieChart, MonthlyTrendChart,
    DailySpendingChart, TopMerchantsChart
)

DARK_BG   = "#1e1e2e"
CARD_BG   = "#313244"
ACCENT    = "#cba6f7"
GREEN     = "#a6e3a1"
RED       = "#f38ba8"
TEXT      = "#cdd6f4"
MUTED     = "#6c7086"
BORDER    = "#45475a"


def _stat_card(title: str, value: str, color: str = TEXT, emoji: str = "") -> QFrame:
    frame = QFrame()
    frame.setObjectName("card")
    frame.setFixedHeight(90)
    layout = QVBoxLayout(frame)
    layout.setContentsMargins(16, 10, 16, 10)
    layout.setSpacing(2)

    top = QHBoxLayout()
    if emoji:
        e = QLabel(emoji)
        e.setFont(QFont("Segoe UI", 16))
        top.addWidget(e)
    t = QLabel(title)
    t.setStyleSheet(f"color: {MUTED}; font-size: 11px; font-weight: bold;")
    top.addWidget(t)
    top.addStretch()
    layout.addLayout(top)

    v = QLabel(value)
    v.setFont(QFont("Segoe UI", 18, QFont.Bold))
    v.setStyleSheet(f"color: {color};")
    layout.addWidget(v)
    return frame


class AnalyticsPage(QWidget):

    def __init__(self, db):
        super().__init__()
        self.db = db
        self._current_month = datetime.today().strftime("%Y-%m")
        self._build_ui()
        self.refresh()

    # ── Build UI ─────────────────────────────────────────────────────────────
    def _build_ui(self):
        outer = QVBoxLayout(self)
        outer.setContentsMargins(24, 20, 24, 20)
        outer.setSpacing(16)

        # Header
        hdr = QHBoxLayout()
        title = QLabel("Analytics")
        title.setFont(QFont("Segoe UI", 22, QFont.Bold))
        hdr.addWidget(title)
        hdr.addStretch()

        # Month picker
        self.month_combo = QComboBox()
        self.month_combo.setFixedWidth(160)
        self._populate_months()
        self.month_combo.currentTextChanged.connect(self._on_month_change)
        hdr.addWidget(QLabel("Month:"))
        hdr.addWidget(self.month_combo)
        outer.addLayout(hdr)

        # Stat cards row
        self.stats_row = QHBoxLayout()
        self.stats_row.setSpacing(14)
        self.stat_frames = []
        for _ in range(5):
            f = _stat_card("—", "—")
            self.stats_row.addWidget(f)
            self.stat_frames.append(f)
        outer.addLayout(self.stats_row)

        # Scrollable chart area
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.NoFrame)

        container = QWidget()
        grid = QGridLayout(container)
        grid.setSpacing(16)

        # Instantiate charts
        self.pie_chart     = CategoryPieChart(self.db,  width=5, height=4.2)
        self.trend_chart   = MonthlyTrendChart(self.db, width=6, height=4.2)
        self.daily_chart   = DailySpendingChart(self.db, width=5, height=3.8)
        self.merch_chart   = TopMerchantsChart(self.db,  width=5, height=3.8)

        for chart in (self.pie_chart, self.trend_chart,
                      self.daily_chart, self.merch_chart):
            chart.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)

        grid.addWidget(self._wrap(self.pie_chart),   0, 0)
        grid.addWidget(self._wrap(self.trend_chart), 0, 1)
        grid.addWidget(self._wrap(self.daily_chart), 1, 0)
        grid.addWidget(self._wrap(self.merch_chart), 1, 1)

        scroll.setWidget(container)
        outer.addWidget(scroll)

    def _wrap(self, chart) -> QFrame:
        """Wrap a chart canvas in a styled card frame."""
        frame = QFrame()
        frame.setObjectName("card")
        layout = QVBoxLayout(frame)
        layout.setContentsMargins(8, 8, 8, 8)
        layout.addWidget(chart)
        return frame

    # ── Month combo ───────────────────────────────────────────────────────────
    def _populate_months(self):
        today = datetime.today()
        self.month_combo.blockSignals(True)
        self.month_combo.clear()
        for i in range(12):
            dt = (today.replace(day=1) - timedelta(days=30 * i))
            val = dt.strftime("%Y-%m")
            lbl = dt.strftime("%B %Y")
            self.month_combo.addItem(lbl, userData=val)
        self.month_combo.blockSignals(False)

    def _on_month_change(self, _):
        self._current_month = self.month_combo.currentData()
        self.refresh()

    # ── Refresh all charts + stat cards ──────────────────────────────────────
    def refresh(self):
        month = self._current_month

        # Charts
        self.pie_chart.refresh(month)
        self.trend_chart.refresh()
        self.daily_chart.refresh(month)
        self.merch_chart.refresh(month)

        # Summary stats
        summary = self.db.get_monthly_summary(month)
        income  = summary["income"]
        expense = summary["expense"]
        balance = income - expense
        rate    = (balance / income * 100) if income > 0 else 0.0

        cats = self.db.get_category_totals(month)
        top_cat = cats[0]["category"] if cats else "—"
        top_amt = cats[0]["total"]    if cats else 0.0

        # Rebuild stat cards (simpler than updating dynamically)
        for frame in self.stat_frames:
            self.stats_row.removeWidget(frame)
            frame.deleteLater()
        self.stat_frames.clear()

        defs = [
            ("Total Income",    f"₹{income:,.0f}",   GREEN,  "📈"),
            ("Total Expense",   f"₹{expense:,.0f}",  RED,    "📉"),
            ("Net Balance",     f"₹{balance:,.0f}",  ACCENT, "💼"),
            ("Savings Rate",    f"{rate:.1f}%",       ACCENT, "🏦"),
            ("Top Category",    f"{top_cat}  ₹{top_amt:,.0f}", "#f9e2af", "🏆"),
        ]
        for title, val, color, emoji in defs:
            f = _stat_card(title, val, color, emoji)
            self.stats_row.addWidget(f)
            self.stat_frames.append(f)
