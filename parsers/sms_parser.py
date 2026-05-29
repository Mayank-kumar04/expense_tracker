"""
parsers/sms_parser.py
----------------------
Parses SMS-style bank notification strings to extract transaction data.

Example input:
  "Rs.450 debited from SBI A/c XXXX via UPI to SWIGGY on 24-May-25"

Output (dict):
  { amount: 450, merchant: "SWIGGY", bank: "SBI",
    tx_type: "expense", date: "2025-05-24" }
"""

import re
from datetime import datetime
from typing import Optional


# ── Regex patterns ────────────────────────────────────────────────────────────

AMOUNT_PATTERN = re.compile(
    r"(?:Rs\.?|INR)\s*([\d,]+(?:\.\d{1,2})?)", re.IGNORECASE
)
DEBIT_KEYWORDS  = re.compile(r"\b(debit(?:ed)?|spent|withdrawn|paid)\b", re.IGNORECASE)
CREDIT_KEYWORDS = re.compile(r"\b(credit(?:ed)?|received|deposited|refund)\b", re.IGNORECASE)
BANK_PATTERN = re.compile(
    r"\b(SBI|HDFC|ICICI|AXIS|KOTAK|PNB|BOB|CANARA|UNION|YES\s*BANK|IDBI)\b",
    re.IGNORECASE
)
MERCHANT_PATTERN = re.compile(
    r"\b(?:to|at|for)\s+([A-Z][A-Z0-9\s&\-]{1,30}?)(?:\s+on|\s+via|\s+ref|\s+upi|$)",
    re.IGNORECASE
)
DATE_PATTERNS = [
    (re.compile(r"\d{2}-[A-Za-z]{3}-\d{2,4}"), "%d-%b-%y"),
    (re.compile(r"\d{2}/\d{2}/\d{4}"),          "%d/%m/%Y"),
    (re.compile(r"\d{4}-\d{2}-\d{2}"),          "%Y-%m-%d"),
    (re.compile(r"\d{2}-\d{2}-\d{4}"),          "%d-%m-%Y"),
]


def parse_amount(sms: str) -> Optional[float]:
    m = AMOUNT_PATTERN.search(sms)
    return float(m.group(1).replace(",", "")) if m else None


def parse_type(sms: str) -> str:
    if DEBIT_KEYWORDS.search(sms):  return "expense"
    if CREDIT_KEYWORDS.search(sms): return "income"
    return "expense"


def parse_bank(sms: str) -> str:
    m = BANK_PATTERN.search(sms)
    return m.group(1).upper() if m else "Unknown"


def parse_merchant(sms: str) -> str:
    m = MERCHANT_PATTERN.search(sms)
    return m.group(1).strip().title() if m else "Unknown"


def parse_date(sms: str) -> str:
    today = datetime.today().strftime("%Y-%m-%d")
    for pattern, fmt in DATE_PATTERNS:
        m = pattern.search(sms)
        if m:
            raw = m.group(0)
            try:
                return datetime.strptime(raw, fmt).strftime("%Y-%m-%d")
            except ValueError:
                pass
    return today


def parse_sms(sms_text: str) -> Optional[dict]:
    """
    Parse a bank SMS string. Returns None if no amount found.
    """
    amount = parse_amount(sms_text)
    if amount is None:
        return None
    return {
        "amount":   amount,
        "merchant": parse_merchant(sms_text),
        "bank":     parse_bank(sms_text),
        "tx_type":  parse_type(sms_text),
        "date":     parse_date(sms_text),
        "raw":      sms_text,
    }


def parse_bulk_sms(text: str) -> list:
    """
    Split a multi-line block of SMS messages and parse each one.
    Returns list of successfully parsed result dicts.
    """
    lines = [l.strip() for l in text.strip().splitlines() if l.strip()]
    results = []
    for line in lines:
        r = parse_sms(line)
        if r:
            results.append(r)
    return results


if __name__ == "__main__":
    samples = [
        "Rs.450 debited from SBI A/c XXXX via UPI to SWIGGY on 24-May-25",
        "INR 1,200.00 credited to your HDFC account. Received from SALARY",
        "Your ICICI A/c XX1234 is debited with Rs.299 at AMAZON on 20/05/2025",
    ]
    for sms in samples:
        print(parse_sms(sms))
