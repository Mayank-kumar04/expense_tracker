"""
ui/import_page.py
------------------
Import page with two tabs:
  Tab 1 — Paste SMS messages in bulk and import detected transactions
  Tab 2 — Upload a CSV bank statement and map columns
"""

from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QTextEdit, QTableWidget, QTableWidgetItem, QHeaderView,
    QFrame, QTabWidget, QFileDialog, QMessageBox, QComboBox,
    QCheckBox, QScrollArea, QSizePolicy
)
from PyQt5.QtCore import Qt
from PyQt5.QtGui import QFont, QColor

from parsers.sms_parser import parse_bulk_sms
from parsers.statement_parser import parse_csv_statement
from utils.categorizer import categorize

DARK_BG = "#1e1e2e"
CARD_BG = "#313244"
ACCENT  = "#cba6f7"
GREEN   = "#a6e3a1"
RED     = "#f38ba8"
TEXT    = "#cdd6f4"
MUTED   = "#6c7086"
BORDER  = "#45475a"


class ImportPage(QWidget):

    def __init__(self, db):
        super().__init__()
        self.db = db
        self._parsed_sms   = []
        self._parsed_csv   = []
        self._build_ui()

    def _build_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(24, 20, 24, 20)
        layout.setSpacing(16)

        title = QLabel("Import Transactions")
        title.setFont(QFont("Segoe UI", 22, QFont.Bold))
        layout.addWidget(title)

        tabs = QTabWidget()
        tabs.setStyleSheet(f"""
            QTabWidget::pane   {{ border: 1px solid {BORDER}; border-radius: 8px; background: {CARD_BG}; }}
            QTabBar::tab       {{ background: {DARK_BG}; color: {MUTED}; padding: 8px 20px; border-radius: 6px; margin-right: 4px; }}
            QTabBar::tab:selected {{ background: {CARD_BG}; color: {ACCENT}; font-weight: bold; }}
        """)

        tabs.addTab(self._build_sms_tab(),  "📱  SMS Import")
        tabs.addTab(self._build_csv_tab(),  "📄  CSV Import")
        layout.addWidget(tabs)

    # ══ SMS TAB ═══════════════════════════════════════════════════════════════
    def _build_sms_tab(self) -> QWidget:
        w = QWidget()
        layout = QVBoxLayout(w)
        layout.setContentsMargins(16, 16, 16, 16)
        layout.setSpacing(12)

        layout.addWidget(QLabel(
            "Paste one SMS per line. The parser will detect amounts, merchants, dates and types automatically."
        ))

        # Sample button
        sample_btn = QPushButton("Load sample SMS messages")
        sample_btn.setFixedWidth(220)
        sample_btn.clicked.connect(self._load_sample_sms)
        layout.addWidget(sample_btn)

        self.sms_input = QTextEdit()
        self.sms_input.setPlaceholderText(
            "Rs.450 debited from SBI A/c XXXX via UPI to SWIGGY on 24-May-25\n"
            "INR 1200 credited to HDFC. Received from SALARY\n"
            "Rs.299 debited from ICICI at AMAZON on 20/05/2025"
        )
        self.sms_input.setMinimumHeight(120)
        self.sms_input.setMaximumHeight(160)
        layout.addWidget(self.sms_input)

        parse_btn = QPushButton("🔍  Parse Messages")
        parse_btn.setObjectName("accent")
        parse_btn.setFixedHeight(38)
        parse_btn.clicked.connect(self._parse_sms)
        layout.addWidget(parse_btn)

        self.sms_table = self._make_table(
            ["✓", "Date", "Merchant", "Amount", "Type", "Category", "Bank"]
        )
        layout.addWidget(self.sms_table)

        import_btn = QPushButton("💾  Import Checked Transactions")
        import_btn.setObjectName("accent")
        import_btn.setFixedHeight(38)
        import_btn.clicked.connect(self._import_sms)
        layout.addWidget(import_btn)

        return w

    def _load_sample_sms(self):
        samples = [
            "Rs.450 debited from SBI A/c XXXX via UPI to SWIGGY on 24-May-25",
            "INR 50000 credited to HDFC. Received from SALARY on 01-May-25",
            "Your ICICI A/c XX1234 is debited with Rs.299 at AMAZON on 05-May-25",
            "Rs 85 spent at UBER via AXIS debit card on 10-May-25",
            "Rs.1200 debited from HDFC via UPI to NETFLIX on 15-May-25",
            "INR 2000 credited to SBI. Refund from FLIPKART on 18-May-25",
        ]
        self.sms_input.setPlainText("\n".join(samples))

    def _parse_sms(self):
        text = self.sms_input.toPlainText().strip()
        if not text:
            QMessageBox.information(self, "Empty", "Please paste some SMS messages first.")
            return

        self._parsed_sms = parse_bulk_sms(text)
        self.sms_table.setRowCount(len(self._parsed_sms))

        for i, r in enumerate(self._parsed_sms):
            cat = categorize(r["merchant"])

            chk = QTableWidgetItem()
            chk.setCheckState(Qt.Checked)
            chk.setTextAlignment(Qt.AlignCenter)
            self.sms_table.setItem(i, 0, chk)

            cells = [r["date"], r["merchant"], f"₹{r['amount']:,.2f}",
                     r["tx_type"].capitalize(), cat, r["bank"]]
            for j, val in enumerate(cells):
                item = QTableWidgetItem(val)
                item.setTextAlignment(Qt.AlignCenter)
                if j == 2:   # amount
                    item.setForeground(QColor(GREEN if r["tx_type"] == "income" else RED))
                self.sms_table.setItem(i, j + 1, item)

        if not self._parsed_sms:
            QMessageBox.warning(self, "No Results",
                                "No transactions detected. Check the SMS format.")

    def _import_sms(self):
        if not self._parsed_sms:
            QMessageBox.information(self, "Nothing to import", "Parse messages first.")
            return

        count = 0
        for i, r in enumerate(self._parsed_sms):
            chk = self.sms_table.item(i, 0)
            if chk and chk.checkState() == Qt.Checked:
                cat = categorize(r["merchant"])
                self.db.add_transaction(
                    amount       = r["amount"],
                    category     = cat,
                    merchant     = r["merchant"],
                    tx_type      = r["tx_type"],
                    payment_mode = "UPI" if "upi" in r["raw"].lower() else "Bank",
                    notes        = f"Imported from SMS ({r['bank']})",
                    date         = r["date"],
                )
                count += 1

        QMessageBox.information(self, "Done",
                                f"✅ Successfully imported {count} transaction(s).")
        self.sms_input.clear()
        self.sms_table.setRowCount(0)
        self._parsed_sms = []

    # ══ CSV TAB ═══════════════════════════════════════════════════════════════
    def _build_csv_tab(self) -> QWidget:
        w = QWidget()
        layout = QVBoxLayout(w)
        layout.setContentsMargins(16, 16, 16, 16)
        layout.setSpacing(12)

        layout.addWidget(QLabel(
            "Upload a CSV bank statement. Select the columns that contain date, amount, "
            "description, and transaction type."
        ))

        file_row = QHBoxLayout()
        self.csv_path_label = QLabel("No file selected")
        self.csv_path_label.setStyleSheet(f"color: {MUTED};")

        browse_btn = QPushButton("📂  Browse CSV")
        browse_btn.setFixedHeight(36)
        browse_btn.clicked.connect(self._browse_csv)

        file_row.addWidget(browse_btn)
        file_row.addWidget(self.csv_path_label, 1)
        layout.addLayout(file_row)

        # Column mapping
        map_frame = QFrame()
        map_frame.setObjectName("card")
        map_layout = QHBoxLayout(map_frame)
        map_layout.setContentsMargins(14, 12, 14, 12)
        map_layout.setSpacing(16)

        self.col_combos = {}
        for lbl, key in [("Date col", "date"), ("Amount col", "amount"),
                         ("Description col", "description"), ("Type col (opt)", "type")]:
            map_layout.addWidget(QLabel(lbl + ":"))
            cb = QComboBox()
            cb.setFixedWidth(140)
            self.col_combos[key] = cb
            map_layout.addWidget(cb)

        layout.addWidget(map_frame)

        parse_csv_btn = QPushButton("🔍  Parse CSV")
        parse_csv_btn.setObjectName("accent")
        parse_csv_btn.setFixedHeight(38)
        parse_csv_btn.clicked.connect(self._parse_csv)
        layout.addWidget(parse_csv_btn)

        self.csv_table = self._make_table(
            ["✓", "Date", "Description", "Amount", "Type", "Category"]
        )
        layout.addWidget(self.csv_table)

        import_csv_btn = QPushButton("💾  Import Checked Transactions")
        import_csv_btn.setObjectName("accent")
        import_csv_btn.setFixedHeight(38)
        import_csv_btn.clicked.connect(self._import_csv)
        layout.addWidget(import_csv_btn)

        return w

    def _browse_csv(self):
        path, _ = QFileDialog.getOpenFileName(
            self, "Open CSV Statement", "", "CSV Files (*.csv)"
        )
        if not path:
            return
        self._csv_path = path
        self.csv_path_label.setText(path.split("/")[-1])

        # Read headers to populate column combos
        import csv
        try:
            with open(path, "r", encoding="utf-8-sig") as f:
                reader = csv.reader(f)
                headers = next(reader, [])
            for cb in self.col_combos.values():
                cb.clear()
                cb.addItem("— none —")
                cb.addItems(headers)
            # Best-guess defaults
            for h in headers:
                hl = h.lower()
                if "date" in hl:
                    self.col_combos["date"].setCurrentText(h)
                elif "amount" in hl or "debit" in hl or "credit" in hl:
                    self.col_combos["amount"].setCurrentText(h)
                elif "desc" in hl or "narr" in hl or "detail" in hl or "particular" in hl:
                    self.col_combos["description"].setCurrentText(h)
        except Exception as e:
            QMessageBox.warning(self, "Error", f"Could not read CSV:\n{e}")

    def _parse_csv(self):
        if not hasattr(self, "_csv_path"):
            QMessageBox.information(self, "No File", "Please browse and select a CSV file first.")
            return

        col_map = {k: cb.currentText() for k, cb in self.col_combos.items()}
        col_map = {k: v for k, v in col_map.items() if v != "— none —"}

        self._parsed_csv = parse_csv_statement(self._csv_path, col_map)

        self.csv_table.setRowCount(len(self._parsed_csv))
        for i, r in enumerate(self._parsed_csv):
            cat = categorize(r.get("description", ""))
            chk = QTableWidgetItem()
            chk.setCheckState(Qt.Checked)
            self.csv_table.setItem(i, 0, chk)
            cells = [r.get("date",""), r.get("description",""),
                     f"₹{float(r.get('amount',0)):,.2f}",
                     r.get("tx_type","expense").capitalize(), cat]
            for j, val in enumerate(cells):
                item = QTableWidgetItem(str(val))
                item.setTextAlignment(Qt.AlignCenter)
                if j == 2:
                    item.setForeground(QColor(
                        GREEN if r.get("tx_type") == "income" else RED
                    ))
                self.csv_table.setItem(i, j + 1, item)

    def _import_csv(self):
        if not self._parsed_csv:
            QMessageBox.information(self, "Nothing to import", "Parse a CSV file first.")
            return
        count = 0
        for i, r in enumerate(self._parsed_csv):
            chk = self.csv_table.item(i, 0)
            if chk and chk.checkState() == Qt.Checked:
                cat = categorize(r.get("description", ""))
                self.db.add_transaction(
                    amount       = float(r.get("amount", 0)),
                    category     = cat,
                    merchant     = r.get("description", "")[:50],
                    tx_type      = r.get("tx_type", "expense"),
                    payment_mode = "Bank Transfer",
                    notes        = "Imported from CSV statement",
                    date         = r.get("date", ""),
                )
                count += 1
        QMessageBox.information(self, "Done", f"✅ Imported {count} transaction(s).")
        self.csv_table.setRowCount(0)
        self._parsed_csv = []

    # ── Helper ────────────────────────────────────────────────────────────────
    def _make_table(self, headers: list) -> QTableWidget:
        t = QTableWidget()
        t.setColumnCount(len(headers))
        t.setHorizontalHeaderLabels(headers)
        t.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        t.horizontalHeader().setSectionResizeMode(0, QHeaderView.Fixed)
        t.setColumnWidth(0, 36)
        t.setSelectionBehavior(QTableWidget.SelectRows)
        t.setEditTriggers(QTableWidget.NoEditTriggers)
        t.verticalHeader().setVisible(False)
        return t
