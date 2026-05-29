"""
parsers/statement_parser.py
----------------------------
Parse CSV and PDF bank statements into normalised transaction dicts.

CSV: flexible column-mapping approach so any bank's export can be handled.
PDF: uses pdfplumber to extract tables from PDF statements.
"""

import csv
import re
from datetime import datetime
from typing import List, Dict, Optional


# ── Date normalisation ────────────────────────────────────────────────────────
DATE_FMTS = [
    "%d/%m/%Y", "%d-%m-%Y", "%Y-%m-%d", "%d %b %Y",
    "%d-%b-%Y", "%d/%m/%y", "%m/%d/%Y",
]

def normalise_date(raw: str) -> str:
    raw = raw.strip()
    for fmt in DATE_FMTS:
        try:
            return datetime.strptime(raw, fmt).strftime("%Y-%m-%d")
        except ValueError:
            pass
    return datetime.today().strftime("%Y-%m-%d")   # fallback: today


def normalise_amount(raw: str) -> float:
    """Strip currency symbols, commas, whitespace and return float."""
    text = str(raw).strip()
    # Remove currency prefixes first so "Rs. 450" does not become ".450"
    text = re.sub(r"(?:Rs\.?|INR|\u20b9)\s*", "", text, flags=re.IGNORECASE)
    cleaned = re.sub(r"[^\d.]", "", text)
    try:
        return float(cleaned)
    except ValueError:
        return 0.0


def infer_type(row: dict, type_col: Optional[str] = None) -> str:
    """Determine whether a row is an expense or income."""
    if type_col and type_col in row:
        val = str(row[type_col]).lower()
        if any(k in val for k in ("cr", "credit", "deposit", "refund", "received")):
            return "income"
        if any(k in val for k in ("dr", "debit", "withdraw", "paid")):
            return "expense"

    # Check description for credit keywords
    desc = " ".join(str(v) for v in row.values()).lower()
    if any(k in desc for k in ("salary", "credited", "refund", "cashback")):
        return "income"
    return "expense"


# ── CSV Parser ────────────────────────────────────────────────────────────────

def parse_csv_statement(filepath: str, col_map: dict) -> List[Dict]:
    """
    Parse a CSV bank statement.

    col_map keys (all optional except 'amount'):
        date, amount, description, type

    Returns list of dicts: {date, amount, description, tx_type}
    """
    results = []
    try:
        with open(filepath, "r", encoding="utf-8-sig") as f:
            reader = csv.DictReader(f)
            for row in reader:
                date_col   = col_map.get("date")
                amount_col = col_map.get("amount")
                desc_col   = col_map.get("description")
                type_col   = col_map.get("type")

                if not amount_col or amount_col not in row:
                    continue

                amount = normalise_amount(row[amount_col])
                if amount <= 0:
                    continue

                date = normalise_date(row[date_col]) if date_col and date_col in row else \
                       datetime.today().strftime("%Y-%m-%d")
                desc = row[desc_col].strip() if desc_col and desc_col in row else "Bank Transaction"
                tx_type = infer_type(row, type_col)

                results.append({
                    "date":        date,
                    "amount":      amount,
                    "description": desc,
                    "tx_type":     tx_type,
                })
    except Exception as e:
        print(f"[statement_parser] CSV error: {e}")

    return results


# ── PDF Parser ────────────────────────────────────────────────────────────────

def parse_pdf_statement(filepath: str) -> List[Dict]:
    """
    Parse a PDF bank statement using pdfplumber.
    Attempts to extract the first table found on each page.

    Returns list of dicts: {date, amount, description, tx_type}
    """
    results = []
    try:
        import pdfplumber
        with pdfplumber.open(filepath) as pdf:
            for page in pdf.pages:
                tables = page.extract_tables()
                for table in tables:
                    if not table or len(table) < 2:
                        continue
                    headers = [str(h).strip().lower() if h else "" for h in table[0]]
                    for row_data in table[1:]:
                        row = dict(zip(headers, row_data))
                        # Find amount column
                        amount = 0.0
                        for key in row:
                            if "amount" in key or "debit" in key or "credit" in key:
                                amount = normalise_amount(row[key])
                                if amount > 0:
                                    break
                        if amount <= 0:
                            continue

                        date_raw = ""
                        for key in row:
                            if "date" in key:
                                date_raw = str(row[key])
                                break
                        date = normalise_date(date_raw) if date_raw else \
                               datetime.today().strftime("%Y-%m-%d")

                        desc = ""
                        for key in row:
                            if any(k in key for k in ("desc", "narr", "detail", "particular", "remark")):
                                desc = str(row[key]).strip()
                                break

                        results.append({
                            "date":        date,
                            "amount":      amount,
                            "description": desc or "PDF Transaction",
                            "tx_type":     infer_type(row),
                        })

    except ImportError:
        print("[statement_parser] pdfplumber not installed.")
    except Exception as e:
        print(f"[statement_parser] PDF error: {e}")

    return results


if __name__ == "__main__":
    # Quick test with a synthetic CSV
    import tempfile, os
    sample = "Date,Description,Amount,Type\n2025-05-01,SALARY CREDIT,50000,CR\n2025-05-05,SWIGGY,450,DR\n2025-05-10,AMAZON,1299,DR\n"
    with tempfile.NamedTemporaryFile(mode="w", suffix=".csv", delete=False) as f:
        f.write(sample)
        path = f.name

    col_map = {"date": "Date", "amount": "Amount", "description": "Description", "type": "Type"}
    rows = parse_csv_statement(path, col_map)
    for r in rows:
        print(r)
    os.unlink(path)
