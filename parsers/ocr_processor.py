"""
parsers/ocr_processor.py
-------------------------
Extracts transaction data from uploaded images (screenshots, scanned bills)
using OpenCV pre-processing + Tesseract OCR.

Requires:
    pip install pytesseract opencv-python Pillow
    + Tesseract binary:  sudo apt install tesseract-ocr   (Linux)
                         https://github.com/UB-Mannheim/tesseract/wiki  (Windows)
"""

import re
import os
from typing import Optional
from datetime import datetime


# ── Try importing optional dependencies gracefully ────────────────────────────
try:
    import cv2
    import numpy as np
    CV2_AVAILABLE = True
except ImportError:
    CV2_AVAILABLE = False

try:
    import pytesseract
    from PIL import Image
    TESS_AVAILABLE = True
except ImportError:
    TESS_AVAILABLE = False


# ── Regex patterns (reuse from sms_parser logic) ─────────────────────────────
AMOUNT_RE   = re.compile(r"(?:Rs\.?|INR|₹)\s*([\d,]+(?:\.\d{1,2})?)", re.IGNORECASE)
DATE_RE     = re.compile(r"\b(\d{2}[/-]\d{2}[/-]\d{2,4})\b")
MERCHANT_RE = re.compile(r"(?:merchant|store|shop|to|at|from)\s*[:\-]?\s*([A-Za-z0-9 &]+)", re.IGNORECASE)


def _preprocess_image(image_path: str):
    """
    Load and pre-process image for better OCR accuracy:
    - Convert to grayscale
    - Denoise
    - Adaptive threshold (handles uneven lighting)
    Returns a PIL Image ready for pytesseract.
    """
    if not CV2_AVAILABLE:
        from PIL import Image as PILImage
        return PILImage.open(image_path)

    img = cv2.imread(image_path)
    if img is None:
        raise FileNotFoundError(f"Could not read image: {image_path}")

    gray    = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
    denoised = cv2.fastNlMeansDenoising(gray, h=10)
    thresh  = cv2.adaptiveThreshold(
        denoised, 255,
        cv2.ADAPTIVE_THRESH_GAUSSIAN_C,
        cv2.THRESH_BINARY, 11, 2
    )
    # Scale up small images for better OCR
    h, w = thresh.shape
    if w < 800:
        scale = 800 / w
        thresh = cv2.resize(thresh, None, fx=scale, fy=scale,
                            interpolation=cv2.INTER_CUBIC)

    from PIL import Image as PILImage
    return PILImage.fromarray(thresh)


def extract_text_from_image(image_path: str) -> str:
    """
    Run OCR on the given image file.
    Returns the extracted text string.
    Raises RuntimeError if pytesseract is not available.
    """
    if not TESS_AVAILABLE:
        raise RuntimeError(
            "pytesseract / Pillow not installed.\n"
            "Run: pip install pytesseract Pillow\n"
            "Also install Tesseract binary from your OS package manager."
        )

    pil_img = _preprocess_image(image_path)
    config  = "--oem 3 --psm 6"   # LSTM engine, assume uniform block of text
    return pytesseract.image_to_string(pil_img, config=config)


def parse_ocr_text(text: str) -> dict:
    """
    Extract transaction fields from raw OCR text.

    Returns dict with keys: amount, merchant, date, raw_text
    (tx_type defaults to 'expense' since most bills are expenses)
    """
    # Amount
    m = AMOUNT_RE.search(text)
    amount = float(m.group(1).replace(",", "")) if m else 0.0

    # Date
    dm = DATE_RE.search(text)
    date_str = datetime.today().strftime("%Y-%m-%d")
    if dm:
        raw_date = dm.group(1)
        for fmt in ("%d/%m/%Y", "%d-%m-%Y", "%d/%m/%y", "%d-%m-%y"):
            try:
                date_str = datetime.strptime(raw_date, fmt).strftime("%Y-%m-%d")
                break
            except ValueError:
                pass

    # Merchant
    mm = MERCHANT_RE.search(text)
    merchant = mm.group(1).strip().title() if mm else "Unknown"

    return {
        "amount":   amount,
        "merchant": merchant,
        "date":     date_str,
        "tx_type":  "expense",
        "raw_text": text,
    }


def process_image(image_path: str) -> Optional[dict]:
    """
    Full pipeline: image → OCR text → parsed transaction dict.

    Returns None if OCR fails or no amount found.
    """
    try:
        text   = extract_text_from_image(image_path)
        result = parse_ocr_text(text)
        if result["amount"] <= 0:
            return None
        return result
    except RuntimeError as e:
        print(f"[OCR] Runtime error: {e}")
        return None
    except Exception as e:
        print(f"[OCR] Failed on {image_path}: {e}")
        return None


def is_available() -> tuple:
    """
    Returns (cv2_ok, tesseract_ok) booleans for UI to show status.
    """
    return CV2_AVAILABLE, TESS_AVAILABLE
