"""
ui/budgets_page.py
-------------------
Budget management page.
- Set a monthly budget per category
- Visual progress bars showing spent vs limit
- Red highlight when over budget
- Alert summary at the top
"""

from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QComboBox, QLineEdit, QFrame, QScrollArea, QMessageBox,
    QProgressBar, QGridLayout, QSizePolicy
)
from PyQt5.QtCore import Qt, QPropertyAnimation, QEasingCurve
from PyQt5.QtGui import QFont, QColor

from datetime import datetime

DARK_BG = "#1e1e2e"
CARD_BG = "#313244"
ACCENT  = "#cba6f7"
GREEN   = "#a6e3a1"
RED     = "#f38ba8"
YELLOW  = "#f9e2af"
TEXT    = "#cdd6f4"
MUTED   = "#6c7086"
BORDER  = "#45475a"


class BudgetProgressCard(QFrame):
    """One card per category showing budget progress."""

    def __init__(self, category: str, spent: float, limit: float,
                 over_budget: bool, parent=None):
        super().__init__(parent)
        self.setObjectName("card")
        self.setMinimumHeight(110)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(16, 12, 16, 12)
        layout.setSpacing(6)

        # Top row: category name + spent/limit
        top = QHBoxLayout()
        cat_label = QLabel(category)
        cat_label.setFont(QFont("Segoe UI", 13, QFont.Bold))
        cat_label.setStyleSheet(f"color: {TEXT};")

        amount_label = QLabel(f"₹{spent:,.0f} / ₹{limit:,.0f}")
        amount_label.setStyleSheet(
            f"color: {RED if over_budget else TEXT}; font-size: 12px;"
        )
        top.addWidget(cat_label)
        top.addStretch()
        top.addWidget(amount_label)
        layout.addLayout(top)

        # Progress bar
        pct = min(int(spent / limit * 100), 100) if limit > 0 else 0
        bar = QProgressBar()
        bar.setValue(pct)
        bar.setTextVisible(False)
        bar.setFixedHeight(10)

        if over_budget:
            bar_color = RED
        elif pct >= 80:
            bar_color = YELLOW
        else:
            bar_color = GREEN

        bar.setStyleSheet(f"""
            QProgressBar {{
                background-color: {DARK_BG};
                border-radius: 5px;
                border: none;
            }}
            QProgressBar::chunk {{
                background-color: {bar_color};
                border-radius: 5px;
            }}
        """)
        layout.addWidget(bar)

        # Bottom row: % used + remaining
        remaining = limit - spent
        status_text = (
            f"⚠  Over budget by ₹{abs(remaining):,.0f}"
            if over_budget
            else f"{pct}% used  •  ₹{remaining:,.0f} remaining"
        )
        status = QLabel(status_text)
        status.setStyleSheet(
            f"color: {RED if over_budget else MUTED}; font-size: 11px;"
        )
        layout.addWidget(status)


class BudgetsPage(QWidget):

    def __init__(self, db):
        super().__init__()
        self.db = db
        self._current_month = datetime.today().strftime("%Y-%m")
        self._build_ui()
        self.refresh()

    def _build_ui(self):
        outer = QVBoxLayout(self)
        outer.setContentsMargins(24, 20, 24, 20)
        outer.setSpacing(16)

        # ── Header ────────────────────────────────────────────────────────────
        hdr = QHBoxLayout()
        title = QLabel("Budgets")
        title.setFont(QFont("Segoe UI", 22, QFont.Bold))
        hdr.addWidget(title)
        hdr.addStretch()

        # Month indicator
        month_lbl = QLabel(datetime.today().strftime("%B %Y"))
        month_lbl.setStyleSheet(f"color: {MUTED}; font-size: 13px;")
        hdr.addWidget(month_lbl)
        outer.addLayout(hdr)

        # ── Alert banner (hidden by default) ──────────────────────────────────
        self.alert_frame = QFrame()
        self.alert_frame.setStyleSheet(
            f"background-color: #45212a; border-radius: 10px; border: 1px solid {RED};"
        )
        alert_layout = QHBoxLayout(self.alert_frame)
        alert_layout.setContentsMargins(16, 10, 16, 10)
        self.alert_label = QLabel("")
        self.alert_label.setStyleSheet(f"color: {RED}; font-size: 13px;")
        self.alert_label.setWordWrap(True)
        alert_layout.addWidget(QLabel("⚠"))
        alert_layout.addWidget(self.alert_label, 1)
        self.alert_frame.hide()
        outer.addWidget(self.alert_frame)

        # ── Add budget form ───────────────────────────────────────────────────
        form_frame = QFrame()
        form_frame.setObjectName("card")
        form_layout = QHBoxLayout(form_frame)
        form_layout.setContentsMargins(16, 14, 16, 14)
        form_layout.setSpacing(12)

        form_layout.addWidget(QLabel("Category:"))
        self.cat_combo = QComboBox()
        self.cat_combo.setFixedWidth(160)
        self.cat_combo.addItems(self.db.get_categories())
        form_layout.addWidget(self.cat_combo)

        form_layout.addWidget(QLabel("Monthly Limit (₹):"))
        self.limit_input = QLineEdit()
        self.limit_input.setPlaceholderText("e.g. 5000")
        self.limit_input.setFixedWidth(120)
        form_layout.addWidget(self.limit_input)

        set_btn = QPushButton("Set Budget")
        set_btn.setObjectName("accent")
        set_btn.setFixedHeight(36)
        set_btn.clicked.connect(self._set_budget)
        form_layout.addWidget(set_btn)
        form_layout.addStretch()

        outer.addWidget(form_frame)

        # ── Budget cards grid ─────────────────────────────────────────────────
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.NoFrame)

        self.cards_container = QWidget()
        self.cards_grid = QGridLayout(self.cards_container)
        self.cards_grid.setSpacing(14)
        scroll.setWidget(self.cards_container)
        outer.addWidget(scroll)

    # ── Actions ───────────────────────────────────────────────────────────────
    def _set_budget(self):
        try:
            limit = float(self.limit_input.text().strip())
            if limit <= 0:
                raise ValueError
        except ValueError:
            QMessageBox.warning(self, "Invalid", "Enter a valid positive number for the limit.")
            return

        category = self.cat_combo.currentText()
        self.db.set_budget(category, limit, self._current_month)
        self.limit_input.clear()
        self.refresh()

    def refresh(self):
        month = self._current_month

        # Clear existing cards
        while self.cards_grid.count():
            item = self.cards_grid.takeAt(0)
            if item.widget():
                item.widget().deleteLater()

        statuses = self.db.get_budget_status(month)

        if not statuses:
            placeholder = QLabel("No budgets set for this month.\nUse the form above to add one.")
            placeholder.setAlignment(Qt.AlignCenter)
            placeholder.setStyleSheet(f"color: {MUTED}; font-size: 14px;")
            self.cards_grid.addWidget(placeholder, 0, 0, 1, 2)
            self.alert_frame.hide()
            return

        over_list = [s for s in statuses if s["over_budget"]]

        # Alert banner
        if over_list:
            alerts = " | ".join(
                f"{s['category']} exceeded by ₹{s['spent'] - s['limit']:,.0f}"
                for s in over_list
            )
            self.alert_label.setText(f"Budget alerts this month: {alerts}")
            self.alert_frame.show()
        else:
            self.alert_frame.hide()

        # Cards — 2 per row
        for i, s in enumerate(statuses):
            card = BudgetProgressCard(
                category   = s["category"],
                spent      = s["spent"],
                limit      = s["limit"],
                over_budget = s["over_budget"],
            )
            self.cards_grid.addWidget(card, i // 2, i % 2)

        # Fill empty column if odd count
        if len(statuses) % 2 != 0:
            spacer = QWidget()
            spacer.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Preferred)
            self.cards_grid.addWidget(spacer, len(statuses) // 2, 1)
