"""
ui/ocr_page.py
---------------
OCR Upload page: drag-and-drop or browse an image of a bill/receipt,
run OCR, review extracted fields, save as a transaction.
"""

from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QFrame, QLineEdit, QComboBox, QDateEdit, QFileDialog,
    QMessageBox, QTextEdit, QFormLayout, QSizePolicy
)
from PyQt5.QtCore import Qt, QDate, QThread, pyqtSignal
from PyQt5.QtGui import QFont, QPixmap, QImage

from datetime import datetime
from parsers.ocr_processor import process_image, is_available
from utils.categorizer import categorize

DARK_BG = "#1e1e2e"
CARD_BG = "#313244"
ACCENT  = "#cba6f7"
GREEN   = "#a6e3a1"
RED     = "#f38ba8"
YELLOW  = "#f9e2af"
TEXT    = "#cdd6f4"
MUTED   = "#6c7086"
BORDER  = "#45475a"


class OCRWorker(QThread):
    """Run OCR in a background thread so the UI doesn't freeze."""
    finished = pyqtSignal(object)   # emits result dict or None
    error    = pyqtSignal(str)

    def __init__(self, path: str):
        super().__init__()
        self.path = path

    def run(self):
        try:
            result = process_image(self.path)
            self.finished.emit(result)
        except Exception as e:
            self.error.emit(str(e))


class OCRPage(QWidget):

    def __init__(self, db):
        super().__init__()
        self.db = db
        self._image_path = None
        self._worker     = None
        self._build_ui()
        self._check_dependencies()

    def _build_ui(self):
        outer = QVBoxLayout(self)
        outer.setContentsMargins(24, 20, 24, 20)
        outer.setSpacing(16)

        title = QLabel("OCR — Scan a Bill or Receipt")
        title.setFont(QFont("Segoe UI", 22, QFont.Bold))
        outer.addWidget(title)

        # Dependency status banner
        self.dep_banner = QFrame()
        self.dep_banner.setObjectName("card")
        dep_layout = QHBoxLayout(self.dep_banner)
        dep_layout.setContentsMargins(14, 10, 14, 10)
        self.dep_label = QLabel("")
        self.dep_label.setWordWrap(True)
        dep_layout.addWidget(self.dep_label)
        outer.addWidget(self.dep_banner)

        content = QHBoxLayout()
        content.setSpacing(20)

        # ── Left: image preview ───────────────────────────────────────────────
        left = QVBoxLayout()

        self.image_frame = QFrame()
        self.image_frame.setObjectName("card")
        self.image_frame.setFixedSize(340, 280)
        img_layout = QVBoxLayout(self.image_frame)
        img_layout.setAlignment(Qt.AlignCenter)

        self.image_label = QLabel("📷\n\nNo image selected\n\nBrowse or drag & drop")
        self.image_label.setAlignment(Qt.AlignCenter)
        self.image_label.setStyleSheet(f"color: {MUTED}; font-size: 13px;")
        img_layout.addWidget(self.image_label)
        left.addWidget(self.image_frame)

        browse_btn = QPushButton("📂  Browse Image")
        browse_btn.setFixedHeight(38)
        browse_btn.clicked.connect(self._browse)
        left.addWidget(browse_btn)

        self.ocr_btn = QPushButton("🔍  Run OCR")
        self.ocr_btn.setObjectName("accent")
        self.ocr_btn.setFixedHeight(40)
        self.ocr_btn.setEnabled(False)
        self.ocr_btn.clicked.connect(self._run_ocr)
        left.addWidget(self.ocr_btn)

        self.status_label = QLabel("Select an image to begin.")
        self.status_label.setStyleSheet(f"color: {MUTED}; font-size: 12px;")
        left.addWidget(self.status_label)
        left.addStretch()

        content.addLayout(left)

        # ── Right: extracted fields ───────────────────────────────────────────
        right_frame = QFrame()
        right_frame.setObjectName("card")
        right = QVBoxLayout(right_frame)
        right.setContentsMargins(18, 16, 18, 16)
        right.setSpacing(14)

        fields_title = QLabel("Extracted Fields")
        fields_title.setFont(QFont("Segoe UI", 14, QFont.Bold))
        right.addWidget(fields_title)

        form = QFormLayout()
        form.setSpacing(10)

        self.amount_input   = QLineEdit(); self.amount_input.setPlaceholderText("Will be auto-filled")
        self.merchant_input = QLineEdit(); self.merchant_input.setPlaceholderText("Will be auto-filled")
        self.merchant_input.textChanged.connect(self._auto_cat)
        self.cat_combo      = QComboBox(); self.cat_combo.addItems(self.db.get_categories())
        self.type_combo     = QComboBox(); self.type_combo.addItems(["expense","income"])
        self.mode_combo     = QComboBox()
        self.mode_combo.addItems(["Cash","UPI","Credit Card","Debit Card","Net Banking","Wallet"])
        self.date_edit      = QDateEdit(QDate.currentDate())
        self.date_edit.setCalendarPopup(True); self.date_edit.setDisplayFormat("dd MMM yyyy")

        form.addRow("Amount (₹)",   self.amount_input)
        form.addRow("Merchant",     self.merchant_input)
        form.addRow("Category",     self.cat_combo)
        form.addRow("Type",         self.type_combo)
        form.addRow("Payment Mode", self.mode_combo)
        form.addRow("Date",         self.date_edit)
        right.addLayout(form)

        # Raw OCR output
        right.addWidget(QLabel("Raw OCR Text:"))
        self.raw_text = QTextEdit()
        self.raw_text.setReadOnly(True)
        self.raw_text.setMaximumHeight(100)
        self.raw_text.setStyleSheet(f"font-size: 11px; color: {MUTED};")
        right.addWidget(self.raw_text)

        save_btn = QPushButton("💾  Save as Transaction")
        save_btn.setObjectName("accent")
        save_btn.setFixedHeight(40)
        save_btn.clicked.connect(self._save)
        right.addWidget(save_btn)

        content.addWidget(right_frame, 1)
        outer.addLayout(content)

    # ── Dependency check ──────────────────────────────────────────────────────
    def _check_dependencies(self):
        cv2_ok, tess_ok = is_available()
        if cv2_ok and tess_ok:
            self.dep_label.setText("✅  OpenCV and Tesseract are available. OCR is ready.")
            self.dep_label.setStyleSheet(f"color: {GREEN};")
        else:
            missing = []
            if not cv2_ok:   missing.append("opencv-python")
            if not tess_ok:  missing.append("pytesseract + Pillow + Tesseract binary")
            msg = (f"⚠  Missing dependencies: {', '.join(missing)}\n"
                   f"Run:  pip install {' '.join(missing)}\n"
                   f"OCR will use fallback text extraction (no image pre-processing).")
            self.dep_label.setText(msg)
            self.dep_label.setStyleSheet(f"color: {YELLOW};")

    # ── Browse ────────────────────────────────────────────────────────────────
    def _browse(self):
        path, _ = QFileDialog.getOpenFileName(
            self, "Select Image", "",
            "Images (*.png *.jpg *.jpeg *.bmp *.tiff *.webp)"
        )
        if not path:
            return
        self._image_path = path
        self.ocr_btn.setEnabled(True)
        self.status_label.setText(f"Loaded: {path.split('/')[-1]}")

        # Show thumbnail
        pix = QPixmap(path)
        if not pix.isNull():
            pix = pix.scaled(320, 260, Qt.KeepAspectRatio, Qt.SmoothTransformation)
            self.image_label.setPixmap(pix)
        else:
            self.image_label.setText("⚠  Could not preview image")

    # ── OCR ───────────────────────────────────────────────────────────────────
    def _run_ocr(self):
        if not self._image_path:
            return
        self.ocr_btn.setEnabled(False)
        self.status_label.setText("⏳  Running OCR…")
        self._worker = OCRWorker(self._image_path)
        self._worker.finished.connect(self._on_ocr_done)
        self._worker.error.connect(self._on_ocr_error)
        self._worker.start()

    def _on_ocr_done(self, result):
        self.ocr_btn.setEnabled(True)
        if result is None:
            self.status_label.setText("⚠  No transaction data detected.")
            return
        self.status_label.setText("✅  OCR complete. Review and save.")
        self.amount_input.setText(str(result.get("amount", "")))
        self.merchant_input.setText(result.get("merchant", ""))
        self.raw_text.setPlainText(result.get("raw_text", ""))
        date_str = result.get("date", "")
        if date_str:
            d = QDate.fromString(date_str, "yyyy-MM-dd")
            if d.isValid(): self.date_edit.setDate(d)

    def _on_ocr_error(self, msg):
        self.ocr_btn.setEnabled(True)
        self.status_label.setText(f"❌  Error: {msg}")

    def _auto_cat(self, text):
        idx = self.cat_combo.findText(categorize(text))
        if idx >= 0: self.cat_combo.setCurrentIndex(idx)

    # ── Save ──────────────────────────────────────────────────────────────────
    def _save(self):
        try:
            amount = float(self.amount_input.text().strip())
            assert amount > 0
        except:
            QMessageBox.warning(self, "Invalid", "Enter a valid positive amount.")
            return
        self.db.add_transaction(
            amount       = amount,
            category     = self.cat_combo.currentText(),
            merchant     = self.merchant_input.text().strip() or "OCR Import",
            tx_type      = self.type_combo.currentText(),
            payment_mode = self.mode_combo.currentText(),
            notes        = "Imported via OCR",
            date         = self.date_edit.date().toString("yyyy-MM-dd"),
        )
        QMessageBox.information(self, "Saved", "✅  Transaction saved successfully.")
        self.amount_input.clear()
        self.merchant_input.clear()
        self.raw_text.clear()
        self.image_label.setText("📷\n\nNo image selected\n\nBrowse or drag & drop")
        self._image_path = None
        self.ocr_btn.setEnabled(False)
        mw = self.window()
        if hasattr(mw, "dashboard"): mw.dashboard.refresh()
