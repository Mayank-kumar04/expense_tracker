"""
main.py
--------
Entry point for the Smart Expense Tracker.
Wires together all pages into a single dark-themed sidebar app.
"""

import sys
from datetime import datetime

from PyQt5.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QLabel, QPushButton, QFrame, QStackedWidget, QTableWidget,
    QTableWidgetItem, QHeaderView, QLineEdit, QComboBox, QDateEdit,
    QTextEdit, QMessageBox, QSizePolicy, QDialog, QFormLayout,
    QScrollArea, QGridLayout
)
from PyQt5.QtCore import Qt, QDate, QSize
from PyQt5.QtGui import QFont, QColor, QPalette

from database import DatabaseManager
from models.transaction import Transaction
from utils.categorizer import categorize
from ui.analytics_page import AnalyticsPage
from ui.budgets_page    import BudgetsPage
from ui.import_page     import ImportPage
from ui.settings_page   import SettingsPage
from ui.ocr_page        import OCRPage

# ── Colour palette ─────────────────────────────────────────────────────────────
DARK_BG      = "#1e1e2e"
SIDEBAR_BG   = "#181825"
CARD_BG      = "#313244"
ACCENT       = "#cba6f7"
GREEN        = "#a6e3a1"
RED          = "#f38ba8"
TEXT_PRIMARY = "#cdd6f4"
TEXT_MUTED   = "#6c7086"
BORDER       = "#45475a"
HOVER        = "#45475a"

APP_STYLE = f"""
QMainWindow, QWidget {{
    background-color: {DARK_BG};
    color: {TEXT_PRIMARY};
    font-family: 'Segoe UI', sans-serif;
    font-size: 14px;
}}
QLabel {{ color: {TEXT_PRIMARY}; }}
QPushButton {{
    background-color: {CARD_BG};
    color: {TEXT_PRIMARY};
    border: 1px solid {BORDER};
    border-radius: 8px;
    padding: 8px 18px;
    font-size: 13px;
}}
QPushButton:hover {{ background-color: {HOVER}; border-color: {ACCENT}; }}
QPushButton#accent {{
    background-color: {ACCENT}; color: {DARK_BG};
    font-weight: bold; border: none;
}}
QPushButton#accent:hover {{ background-color: #b4befe; }}
QPushButton#danger {{ background-color: {RED}; color: {DARK_BG}; border: none; }}
QPushButton#nav_btn {{
    background-color: transparent; border: none; border-radius: 8px;
    text-align: left; padding: 10px 20px; font-size: 14px; color: {TEXT_MUTED};
}}
QPushButton#nav_btn:hover {{ background-color: {CARD_BG}; color: {TEXT_PRIMARY}; }}
QPushButton#nav_btn_active {{
    background-color: {CARD_BG}; border: none;
    border-left: 3px solid {ACCENT}; border-radius: 8px;
    text-align: left; padding: 10px 20px;
    font-size: 14px; color: {ACCENT}; font-weight: bold;
}}
QLineEdit, QComboBox, QDateEdit, QTextEdit {{
    background-color: {CARD_BG}; color: {TEXT_PRIMARY};
    border: 1px solid {BORDER}; border-radius: 8px; padding: 8px 12px; font-size: 13px;
}}
QLineEdit:focus, QComboBox:focus, QDateEdit:focus, QTextEdit:focus {{ border-color: {ACCENT}; }}
QComboBox QAbstractItemView {{
    background-color: {CARD_BG}; color: {TEXT_PRIMARY};
    border: 1px solid {BORDER}; selection-background-color: {HOVER};
}}
QTableWidget {{
    background-color: {CARD_BG}; color: {TEXT_PRIMARY};
    border: 1px solid {BORDER}; border-radius: 8px;
    gridline-color: {BORDER}; font-size: 13px;
}}
QTableWidget::item:selected {{ background-color: {HOVER}; }}
QHeaderView::section {{
    background-color: {SIDEBAR_BG}; color: {TEXT_MUTED};
    padding: 8px; border: none; font-weight: bold;
    font-size: 12px; text-transform: uppercase;
}}
QScrollBar:vertical {{
    background: {CARD_BG}; width: 8px; border-radius: 4px;
}}
QScrollBar::handle:vertical {{ background: {BORDER}; border-radius: 4px; }}
QFrame#card {{
    background-color: {CARD_BG}; border-radius: 12px; border: 1px solid {BORDER};
}}
QTabWidget::pane   {{ border: 1px solid {BORDER}; border-radius: 8px; background: {CARD_BG}; }}
QTabBar::tab       {{
    background: {DARK_BG}; color: {TEXT_MUTED};
    padding: 8px 20px; border-radius: 6px; margin-right: 4px;
}}
QTabBar::tab:selected {{ background: {CARD_BG}; color: {ACCENT}; font-weight: bold; }}
QProgressBar {{
    background-color: {DARK_BG}; border-radius: 5px; border: none;
}}
QProgressBar::chunk {{ background-color: {ACCENT}; border-radius: 5px; }}
"""


# ── Summary card ─────────────────────────────────────────────────────────────
class SummaryCard(QFrame):
    def __init__(self, title, value, color=TEXT_PRIMARY, emoji="💰", parent=None):
        super().__init__(parent)
        self.setObjectName("card")
        self.setFixedHeight(110)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(18, 14, 18, 14)
        layout.setSpacing(4)
        top = QHBoxLayout()
        icon = QLabel(emoji)
        icon.setFont(QFont("Segoe UI", 20))
        ttl = QLabel(title)
        ttl.setStyleSheet(f"color: {TEXT_MUTED}; font-size: 12px; font-weight: bold;")
        top.addWidget(icon)
        top.addWidget(ttl)
        top.addStretch()
        layout.addLayout(top)
        self.value_lbl = QLabel(value)
        self.value_lbl.setFont(QFont("Segoe UI", 20, QFont.Bold))
        self.value_lbl.setStyleSheet(f"color: {color};")
        layout.addWidget(self.value_lbl)

    def update_value(self, v): self.value_lbl.setText(v)


# ── Dashboard page ────────────────────────────────────────────────────────────
class DashboardPage(QWidget):
    def __init__(self, db):
        super().__init__()
        self.db = db
        self._build_ui()
        self.refresh()

    def _build_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(24, 20, 24, 20)
        layout.setSpacing(20)

        title = QLabel("Dashboard")
        title.setFont(QFont("Segoe UI", 22, QFont.Bold))
        layout.addWidget(title)

        cards = QHBoxLayout()
        cards.setSpacing(16)
        self.card_balance = SummaryCard("Net Balance",    "₹0", ACCENT, "💼")
        self.card_income  = SummaryCard("Monthly Income", "₹0", GREEN,  "📈")
        self.card_expense = SummaryCard("Monthly Spend",  "₹0", RED,    "📉")
        self.card_savings = SummaryCard("Savings Rate",   "0%", ACCENT, "🏦")
        for c in (self.card_balance, self.card_income, self.card_expense, self.card_savings):
            cards.addWidget(c)
        layout.addLayout(cards)

        rec = QLabel("Recent Transactions")
        rec.setFont(QFont("Segoe UI", 15, QFont.Bold))
        layout.addWidget(rec)

        self.table = QTableWidget()
        self.table.setColumnCount(6)
        self.table.setHorizontalHeaderLabels(["Date","Merchant","Category","Mode","Type","Amount"])
        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.table.setSelectionBehavior(QTableWidget.SelectRows)
        self.table.setEditTriggers(QTableWidget.NoEditTriggers)
        self.table.verticalHeader().setVisible(False)
        layout.addWidget(self.table)

    def refresh(self):
        month   = datetime.today().strftime("%Y-%m")
        summary = self.db.get_monthly_summary(month)
        inc, exp = summary["income"], summary["expense"]
        bal  = inc - exp
        rate = (bal / inc * 100) if inc > 0 else 0.0
        self.card_balance.update_value(f"₹{bal:,.0f}")
        self.card_income.update_value(f"₹{inc:,.0f}")
        self.card_expense.update_value(f"₹{exp:,.0f}")
        self.card_savings.update_value(f"{rate:.0f}%")

        rows = self.db.get_transactions(limit=10)
        self.table.setRowCount(len(rows))
        for i, row in enumerate(rows):
            tx = Transaction.from_db_row(row)
            for j, text in enumerate([tx.display_date, tx.merchant or "—",
                                       tx.category, tx.payment_mode,
                                       tx.tx_type.capitalize(), tx.formatted_amount]):
                item = QTableWidgetItem(text)
                item.setTextAlignment(Qt.AlignCenter)
                if j == 5:
                    item.setForeground(QColor(GREEN if tx.tx_type == "income" else RED))
                self.table.setItem(i, j, item)


# ── Add/Edit Transaction dialog ───────────────────────────────────────────────
class TransactionDialog(QDialog):
    def __init__(self, db, transaction=None, parent=None):
        super().__init__(parent)
        self.db = db
        self.existing = transaction
        self.setWindowTitle("Edit Transaction" if transaction else "Add Transaction")
        self.setMinimumWidth(420)
        self.setStyleSheet(APP_STYLE)
        self._build_ui()
        if transaction:
            self._populate(transaction)

    def _build_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(24, 20, 24, 20)
        layout.setSpacing(14)
        title = QLabel("Edit Transaction" if self.existing else "New Transaction")
        title.setFont(QFont("Segoe UI", 16, QFont.Bold))
        layout.addWidget(title)
        form = QFormLayout()
        form.setSpacing(12)

        self.amount_input   = QLineEdit(); self.amount_input.setPlaceholderText("e.g. 450")
        self.type_combo     = QComboBox(); self.type_combo.addItems(["expense","income"])
        self.cat_combo      = QComboBox(); self.cat_combo.addItems(self.db.get_categories())
        self.merchant_input = QLineEdit(); self.merchant_input.setPlaceholderText("e.g. Swiggy")
        self.merchant_input.textChanged.connect(self._auto_cat)
        self.mode_combo     = QComboBox()
        self.mode_combo.addItems(["Cash","UPI","Credit Card","Debit Card","Net Banking","Wallet"])
        self.date_edit      = QDateEdit(QDate.currentDate())
        self.date_edit.setCalendarPopup(True); self.date_edit.setDisplayFormat("dd MMM yyyy")
        self.notes_input    = QTextEdit(); self.notes_input.setMaximumHeight(80)
        self.notes_input.setPlaceholderText("Optional notes…")

        form.addRow("Amount (₹)", self.amount_input)
        form.addRow("Type",        self.type_combo)
        form.addRow("Category",    self.cat_combo)
        form.addRow("Merchant",    self.merchant_input)
        form.addRow("Payment Mode",self.mode_combo)
        form.addRow("Date",        self.date_edit)
        form.addRow("Notes",       self.notes_input)
        layout.addLayout(form)

        btns = QHBoxLayout()
        cancel = QPushButton("Cancel"); cancel.clicked.connect(self.reject)
        save   = QPushButton("Save Transaction"); save.setObjectName("accent")
        save.clicked.connect(self._save)
        btns.addWidget(cancel); btns.addWidget(save)
        layout.addLayout(btns)

    def _auto_cat(self, text):
        if text.strip():
            idx = self.cat_combo.findText(categorize(text))
            if idx >= 0: self.cat_combo.setCurrentIndex(idx)

    def _populate(self, tx):
        self.amount_input.setText(str(tx.amount))
        self.type_combo.setCurrentText(tx.tx_type)
        idx = self.cat_combo.findText(tx.category)
        if idx >= 0: self.cat_combo.setCurrentIndex(idx)
        self.merchant_input.setText(tx.merchant)
        self.mode_combo.setCurrentText(tx.payment_mode)
        self.date_edit.setDate(QDate.fromString(tx.date, "yyyy-MM-dd"))
        self.notes_input.setPlainText(tx.notes)

    def _save(self):
        try:
            amount = float(self.amount_input.text().strip())
            assert amount > 0
        except:
            QMessageBox.warning(self, "Invalid", "Enter a valid positive amount.")
            return
        date_str = self.date_edit.date().toString("yyyy-MM-dd")
        args = (amount, self.cat_combo.currentText(), self.merchant_input.text().strip(),
                self.type_combo.currentText(), self.mode_combo.currentText(),
                self.notes_input.toPlainText().strip(), date_str)
        if self.existing:
            self.db.update_transaction(self.existing.id, *args)
        else:
            self.db.add_transaction(*args)
        self.accept()


# ── Transactions page ─────────────────────────────────────────────────────────
class TransactionsPage(QWidget):
    def __init__(self, db):
        super().__init__()
        self.db = db
        self._build_ui()
        self.refresh()

    def _build_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(24, 20, 24, 20)
        layout.setSpacing(16)

        hdr = QHBoxLayout()
        title = QLabel("Transactions"); title.setFont(QFont("Segoe UI", 22, QFont.Bold))
        hdr.addWidget(title); hdr.addStretch()
        add_btn = QPushButton("+ Add Transaction"); add_btn.setObjectName("accent")
        add_btn.clicked.connect(self._add)
        hdr.addWidget(add_btn)
        layout.addLayout(hdr)

        flt = QHBoxLayout(); flt.setSpacing(12)
        self.search_input = QLineEdit()
        self.search_input.setPlaceholderText("🔍  Search by merchant, category, notes…")
        self.search_input.textChanged.connect(self.refresh)
        self.type_filter = QComboBox(); self.type_filter.addItems(["All Types","expense","income"])
        self.type_filter.currentTextChanged.connect(self.refresh)
        self.cat_filter = QComboBox(); self.cat_filter.addItem("All Categories")
        self.cat_filter.addItems(self.db.get_categories())
        self.cat_filter.currentTextChanged.connect(self.refresh)
        flt.addWidget(self.search_input, 3)
        flt.addWidget(self.type_filter, 1)
        flt.addWidget(self.cat_filter, 1)
        layout.addLayout(flt)

        self.table = QTableWidget()
        self.table.setColumnCount(7)
        self.table.setHorizontalHeaderLabels(["ID","Date","Merchant","Category","Mode","Type","Amount"])
        self.table.setColumnHidden(0, True)
        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.table.setSelectionBehavior(QTableWidget.SelectRows)
        self.table.setEditTriggers(QTableWidget.NoEditTriggers)
        self.table.verticalHeader().setVisible(False)
        self.table.doubleClicked.connect(self._edit_selected)
        layout.addWidget(self.table)

        act = QHBoxLayout(); act.addStretch()
        edit_btn   = QPushButton("✏  Edit");   edit_btn.clicked.connect(self._edit_selected)
        del_btn    = QPushButton("🗑  Delete"); del_btn.setObjectName("danger")
        del_btn.clicked.connect(self._delete_selected)
        act.addWidget(edit_btn); act.addWidget(del_btn)
        layout.addLayout(act)

    def refresh(self):
        kw  = self.search_input.text().strip()
        typ = self.type_filter.currentText()
        cat = self.cat_filter.currentText()
        rows = (self.db.search_transactions(kw) if kw else
                self.db.get_transactions(
                    tx_type  = None if typ == "All Types"      else typ,
                    category = None if cat == "All Categories" else cat
                ))
        self.table.setRowCount(len(rows))
        for i, row in enumerate(rows):
            tx = Transaction.from_db_row(row)
            for j, text in enumerate([str(tx.id), tx.display_date, tx.merchant or "—",
                                       tx.category, tx.payment_mode,
                                       tx.tx_type.capitalize(), tx.formatted_amount]):
                item = QTableWidgetItem(text)
                item.setTextAlignment(Qt.AlignCenter)
                if j == 6: item.setForeground(QColor(GREEN if tx.tx_type == "income" else RED))
                self.table.setItem(i, j, item)

    def _selected_tx(self):
        row = self.table.currentRow()
        if row < 0:
            QMessageBox.information(self, "Select", "Select a transaction first.")
            return None
        tx_id = int(self.table.item(row, 0).text())
        rows  = self.db.get_transactions()
        r     = next((r for r in rows if r["id"] == tx_id), None)
        return Transaction.from_db_row(r) if r else None

    def _add(self):
        dlg = TransactionDialog(self.db, parent=self)
        if dlg.exec_() == QDialog.Accepted:
            self.refresh()
            mw = self.window()
            if hasattr(mw, "dashboard"): mw.dashboard.refresh()

    def _edit_selected(self):
        tx = self._selected_tx()
        if not tx: return
        dlg = TransactionDialog(self.db, transaction=tx, parent=self)
        if dlg.exec_() == QDialog.Accepted:
            self.refresh()
            mw = self.window()
            if hasattr(mw, "dashboard"): mw.dashboard.refresh()

    def _delete_selected(self):
        tx = self._selected_tx()
        if not tx: return
        if QMessageBox.question(self, "Delete", "Delete this transaction?",
                                QMessageBox.Yes | QMessageBox.No) == QMessageBox.Yes:
            self.db.delete_transaction(tx.id)
            self.refresh()
            mw = self.window()
            if hasattr(mw, "dashboard"): mw.dashboard.refresh()


# ── Sidebar nav button ────────────────────────────────────────────────────────
class NavButton(QPushButton):
    def __init__(self, label):
        super().__init__(label)
        self.setObjectName("nav_btn")
        self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        self.setFixedHeight(44)
        self.setCursor(Qt.PointingHandCursor)

    def set_active(self, active):
        self.setObjectName("nav_btn_active" if active else "nav_btn")
        self.style().unpolish(self); self.style().polish(self)


# ── Main window ───────────────────────────────────────────────────────────────
class MainWindow(QMainWindow):

    NAV_ITEMS = [
        ("🏠  Dashboard",    0),
        ("💸  Transactions", 1),
        ("📊  Analytics",    2),
        ("🎯  Budgets",      3),
        ("📥  Import",       4),
        ("🖼   OCR Upload",    5),
        ("⚙   Settings",     6),
    ]

    def __init__(self):
        super().__init__()
        self.db = DatabaseManager()
        self.setWindowTitle("Smart Expense Tracker")
        self.setMinimumSize(1100, 700)
        self.setStyleSheet(APP_STYLE)
        self._build_ui()

    def _build_ui(self):
        central = QWidget()
        self.setCentralWidget(central)
        root = QHBoxLayout(central)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)

        # ── Sidebar ────────────────────────────────────────────────────────────
        sidebar = QWidget()
        sidebar.setFixedWidth(220)
        sidebar.setStyleSheet(f"background-color: {SIDEBAR_BG};")
        sb_layout = QVBoxLayout(sidebar)
        sb_layout.setContentsMargins(12, 20, 12, 20)
        sb_layout.setSpacing(4)

        app_name = QLabel("💰 ExpenseTracker")
        app_name.setFont(QFont("Segoe UI", 14, QFont.Bold))
        app_name.setStyleSheet(f"color: {ACCENT}; padding: 8px 8px 20px 8px;")
        sb_layout.addWidget(app_name)

        month_lbl = QLabel(datetime.today().strftime("%B %Y"))
        month_lbl.setStyleSheet(f"color: {TEXT_MUTED}; font-size: 11px; padding-left: 8px;")
        sb_layout.addWidget(month_lbl)

        sep = QFrame(); sep.setFrameShape(QFrame.HLine)
        sep.setStyleSheet(f"color: {BORDER};")
        sb_layout.addWidget(sep)
        sb_layout.addSpacing(8)

        self.nav_buttons = []
        for label, idx in self.NAV_ITEMS:
            btn = NavButton(label)
            btn.clicked.connect(lambda _, i=idx: self._switch(i))
            sb_layout.addWidget(btn)
            self.nav_buttons.append(btn)

        sb_layout.addStretch()

        quick = QPushButton("＋  Quick Add")
        quick.setObjectName("accent")
        quick.setFixedHeight(40)
        quick.setCursor(Qt.PointingHandCursor)
        quick.clicked.connect(self._quick_add)
        sb_layout.addWidget(quick)

        root.addWidget(sidebar)

        # ── Pages ──────────────────────────────────────────────────────────────
        self.stack = QStackedWidget()
        self.dashboard    = DashboardPage(self.db)
        self.transactions = TransactionsPage(self.db)
        self.analytics    = AnalyticsPage(self.db)
        self.budgets      = BudgetsPage(self.db)
        self.imports      = ImportPage(self.db)
        self.ocr_pg       = OCRPage(self.db)
        self.settings_pg  = SettingsPage(self.db)

        for page in (self.dashboard, self.transactions, self.analytics,
                     self.budgets, self.imports, self.ocr_pg, self.settings_pg):
            self.stack.addWidget(page)

        root.addWidget(self.stack)
        self._switch(0)

    def _switch(self, idx):
        self.stack.setCurrentIndex(idx)
        for i, btn in enumerate(self.nav_buttons):
            btn.set_active(i == idx)
        refresh_map = {0: self.dashboard, 1: self.transactions,
                       2: self.analytics,  3: self.budgets}
        if idx in refresh_map and hasattr(refresh_map[idx], "refresh"):
            refresh_map[idx].refresh()

    def _quick_add(self):
        dlg = TransactionDialog(self.db, parent=self)
        if dlg.exec_() == QDialog.Accepted:
            self.dashboard.refresh()
            self.transactions.refresh()


# ── Entry point ───────────────────────────────────────────────────────────────
def main():
    app = QApplication(sys.argv)
    app.setStyle("Fusion")
    p = QPalette()
    p.setColor(QPalette.Window,        QColor(DARK_BG))
    p.setColor(QPalette.WindowText,    QColor(TEXT_PRIMARY))
    p.setColor(QPalette.Base,          QColor(CARD_BG))
    p.setColor(QPalette.AlternateBase, QColor(SIDEBAR_BG))
    p.setColor(QPalette.Text,          QColor(TEXT_PRIMARY))
    p.setColor(QPalette.Button,        QColor(CARD_BG))
    p.setColor(QPalette.ButtonText,    QColor(TEXT_PRIMARY))
    p.setColor(QPalette.Highlight,     QColor(ACCENT))
    p.setColor(QPalette.HighlightedText, QColor(DARK_BG))
    app.setPalette(p)
    w = MainWindow()
    w.show()
    sys.exit(app.exec_())

if __name__ == "__main__":
    main()
