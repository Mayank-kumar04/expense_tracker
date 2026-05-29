"""
ui/settings_page.py
--------------------
Settings & Export page:
  - Export transactions to CSV
  - Export monthly report to PDF
  - Manage categories
  - About section
"""

from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QFrame, QComboBox, QFileDialog, QMessageBox, QLineEdit,
    QGroupBox, QGridLayout
)
from PyQt5.QtCore import Qt
from PyQt5.QtGui import QFont

from datetime import datetime, timedelta
from exports.report_exporter import export_to_csv, export_to_pdf

CARD_BG = "#313244"
ACCENT  = "#cba6f7"
GREEN   = "#a6e3a1"
RED     = "#f38ba8"
TEXT    = "#cdd6f4"
MUTED   = "#6c7086"
BORDER  = "#45475a"


class SettingsPage(QWidget):

    def __init__(self, db):
        super().__init__()
        self.db = db
        self._build_ui()

    def _build_ui(self):
        outer = QVBoxLayout(self)
        outer.setContentsMargins(24, 20, 24, 20)
        outer.setSpacing(20)

        title = QLabel("Settings & Export")
        title.setFont(QFont("Segoe UI", 22, QFont.Bold))
        outer.addWidget(title)

        # ── Export section ────────────────────────────────────────────────────
        outer.addWidget(self._section("📤  Export Reports", self._build_export_section()))

        # ── Category manager ──────────────────────────────────────────────────
        outer.addWidget(self._section("🏷  Manage Categories", self._build_category_section()))

        # ── About ─────────────────────────────────────────────────────────────
        outer.addWidget(self._section("ℹ  About", self._build_about_section()))

        outer.addStretch()

    # ── Section wrapper ───────────────────────────────────────────────────────
    def _section(self, title: str, content: QWidget) -> QFrame:
        frame = QFrame()
        frame.setObjectName("card")
        layout = QVBoxLayout(frame)
        layout.setContentsMargins(18, 14, 18, 14)
        layout.setSpacing(12)

        lbl = QLabel(title)
        lbl.setFont(QFont("Segoe UI", 13, QFont.Bold))
        lbl.setStyleSheet(f"color: {ACCENT};")
        layout.addWidget(lbl)

        sep = QFrame()
        sep.setFrameShape(QFrame.HLine)
        sep.setStyleSheet(f"color: {BORDER};")
        layout.addWidget(sep)

        layout.addWidget(content)
        return frame

    # ── Export section ────────────────────────────────────────────────────────
    def _build_export_section(self) -> QWidget:
        w = QWidget()
        layout = QVBoxLayout(w)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(12)

        # Month picker
        row1 = QHBoxLayout()
        row1.addWidget(QLabel("Select Month:"))
        self.export_month_combo = QComboBox()
        self.export_month_combo.setFixedWidth(160)
        today = datetime.today()
        for i in range(12):
            dt = (today.replace(day=1) - timedelta(days=30 * i))
            self.export_month_combo.addItem(dt.strftime("%B %Y"), userData=dt.strftime("%Y-%m"))
        row1.addWidget(self.export_month_combo)
        row1.addStretch()
        layout.addLayout(row1)

        # Export buttons
        btn_row = QHBoxLayout()
        btn_row.setSpacing(12)

        csv_btn = QPushButton("⬇  Export as CSV")
        csv_btn.setFixedHeight(38)
        csv_btn.clicked.connect(self._export_csv)

        pdf_btn = QPushButton("⬇  Export as PDF Report")
        pdf_btn.setFixedHeight(38)
        pdf_btn.setObjectName("accent")
        pdf_btn.clicked.connect(self._export_pdf)

        all_csv_btn = QPushButton("⬇  Export ALL Transactions (CSV)")
        all_csv_btn.setFixedHeight(38)
        all_csv_btn.clicked.connect(self._export_all_csv)

        btn_row.addWidget(csv_btn)
        btn_row.addWidget(pdf_btn)
        btn_row.addWidget(all_csv_btn)
        layout.addLayout(btn_row)
        return w

    def _get_export_month(self):
        return self.export_month_combo.currentData()

    def _export_csv(self):
        month = self._get_export_month()
        start = f"{month}-01"
        # End of month
        try:
            dt = datetime.strptime(start, "%Y-%m-%d")
            end = (dt.replace(month=dt.month % 12 + 1, day=1) - __import__("datetime").timedelta(days=1)).strftime("%Y-%m-%d") if dt.month < 12 else f"{dt.year}-12-31"
        except Exception:
            end = f"{month}-31"

        rows = self.db.get_transactions(start_date=start, end_date=end)
        path, _ = QFileDialog.getSaveFileName(self, "Save CSV", f"report_{month}.csv", "CSV (*.csv)")
        if not path:
            return
        if export_to_csv(rows, path):
            QMessageBox.information(self, "Done", f"✅ CSV exported to:\n{path}")
        else:
            QMessageBox.critical(self, "Error", "Failed to export CSV.")

    def _export_pdf(self):
        month = self._get_export_month()
        start = f"{month}-01"
        try:
            dt  = datetime.strptime(start, "%Y-%m-%d")
            end = (dt.replace(month=dt.month % 12 + 1, day=1) - __import__("datetime").timedelta(days=1)).strftime("%Y-%m-%d") if dt.month < 12 else f"{dt.year}-12-31"
        except Exception:
            end = f"{month}-31"

        rows    = self.db.get_transactions(start_date=start, end_date=end)
        summary = self.db.get_monthly_summary(month)
        path, _ = QFileDialog.getSaveFileName(self, "Save PDF", f"report_{month}.pdf", "PDF (*.pdf)")
        if not path:
            return
        if export_to_pdf(rows, summary, month, path):
            QMessageBox.information(self, "Done", f"✅ PDF report exported to:\n{path}")
        else:
            QMessageBox.critical(self, "Error", "Failed to export PDF. Is reportlab installed?")

    def _export_all_csv(self):
        rows = self.db.get_transactions()
        path, _ = QFileDialog.getSaveFileName(self, "Save CSV", "all_transactions.csv", "CSV (*.csv)")
        if not path:
            return
        if export_to_csv(rows, path):
            QMessageBox.information(self, "Done", f"✅ Exported {len(rows)} transactions to:\n{path}")

    # ── Category manager ──────────────────────────────────────────────────────
    def _build_category_section(self) -> QWidget:
        w = QWidget()
        layout = QVBoxLayout(w)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(10)

        # Existing categories display
        self.cats_label = QLabel()
        self.cats_label.setWordWrap(True)
        self.cats_label.setStyleSheet(f"color: {MUTED}; font-size: 12px;")
        layout.addWidget(self.cats_label)
        self._refresh_cats_label()

        add_row = QHBoxLayout()
        self.new_cat_input = QLineEdit()
        self.new_cat_input.setPlaceholderText("New category name…")
        self.new_cat_input.setFixedWidth(200)
        add_cat_btn = QPushButton("+ Add")
        add_cat_btn.setObjectName("accent")
        add_cat_btn.setFixedHeight(34)
        add_cat_btn.clicked.connect(self._add_category)
        add_row.addWidget(self.new_cat_input)
        add_row.addWidget(add_cat_btn)
        add_row.addStretch()
        layout.addLayout(add_row)
        return w

    def _refresh_cats_label(self):
        cats = self.db.get_categories()
        self.cats_label.setText("Current categories:  " + "  •  ".join(cats))

    def _add_category(self):
        name = self.new_cat_input.text().strip()
        if not name:
            return
        if self.db.add_category(name):
            QMessageBox.information(self, "Added", f"Category '{name}' added.")
            self.new_cat_input.clear()
            self._refresh_cats_label()
        else:
            QMessageBox.warning(self, "Duplicate", f"Category '{name}' already exists.")

    # ── About ─────────────────────────────────────────────────────────────────
    def _build_about_section(self) -> QWidget:
        w = QWidget()
        layout = QVBoxLayout(w)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(6)

        for line in [
            ("Smart Expense Tracker", ACCENT, 14, True),
            ("A modern personal finance desktop application built with Python + PyQt5.", TEXT, 12, False),
            ("", TEXT, 11, False),
            ("Stack: Python 3 · PyQt5 · SQLite · Matplotlib · Reportlab", MUTED, 11, False),
            ("Features: Dashboard · Transactions · Analytics · Budgets · SMS Import · CSV Import · PDF/CSV Export", MUTED, 11, False),
        ]:
            lbl = QLabel(line[0])
            lbl.setWordWrap(True)
            lbl.setStyleSheet(
                f"color: {line[1]}; font-size: {line[2]}px;"
                + (" font-weight: bold;" if line[3] else "")
            )
            layout.addWidget(lbl)
        return w
