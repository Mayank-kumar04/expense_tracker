"""
models/transaction.py
----------------------
Plain Python classes (data models) that represent core business objects.
These are NOT tied to any GUI — they can be used anywhere in the app.
"""

from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional


@dataclass
class Transaction:
    """
    Represents a single financial transaction (expense or income).

    Example:
        t = Transaction(amount=450, category="Food",
                        merchant="Swiggy", tx_type="expense")
    """
    amount:           float
    category:         str
    tx_type:          str           # 'expense' or 'income'
    merchant:         str   = ""
    payment_mode:     str   = "Cash"
    notes:            str   = ""
    date:             str   = field(default_factory=lambda: datetime.today().strftime("%Y-%m-%d"))
    id:               Optional[int] = None
    user_id:          int   = 1

    # ── Validation ───────────────────────────────────────────────────────────
    def __post_init__(self):
        if self.amount <= 0:
            raise ValueError("Amount must be positive.")
        if self.tx_type not in ("expense", "income"):
            raise ValueError("tx_type must be 'expense' or 'income'.")

    # ── Convenience properties ───────────────────────────────────────────────
    @property
    def is_expense(self) -> bool:
        return self.tx_type == "expense"

    @property
    def formatted_amount(self) -> str:
        symbol = "-" if self.is_expense else "+"
        return f"{symbol}₹{self.amount:,.2f}"

    @property
    def display_date(self) -> str:
        """Return date in DD MMM YYYY format."""
        try:
            dt = datetime.strptime(self.date, "%Y-%m-%d")
            return dt.strftime("%d %b %Y")
        except ValueError:
            return self.date

    # ── Build from a sqlite3.Row ─────────────────────────────────────────────
    @classmethod
    def from_db_row(cls, row) -> "Transaction":
        """Convert a sqlite3.Row (dict-like) into a Transaction object."""
        return cls(
            id           = row["id"],
            user_id      = row["user_id"],
            amount       = row["amount"],
            category     = row["category"],
            merchant     = row["merchant"] or "",
            tx_type      = row["type"],
            payment_mode = row["payment_mode"] or "Cash",
            notes        = row["notes"] or "",
            date         = row["transaction_date"],
        )

    def __repr__(self):
        return (f"Transaction(id={self.id}, {self.formatted_amount}, "
                f"category={self.category!r}, merchant={self.merchant!r})")


@dataclass
class Budget:
    """Represents a monthly budget limit for a category."""
    category:     str
    limit_amount: float
    month:        str        # "YYYY-MM"
    id:           Optional[int] = None

    @property
    def display_month(self) -> str:
        try:
            dt = datetime.strptime(self.month, "%Y-%m")
            return dt.strftime("%B %Y")
        except ValueError:
            return self.month

    @classmethod
    def from_db_row(cls, row) -> "Budget":
        return cls(
            id           = row["id"],
            category     = row["category"],
            limit_amount = row["limit_amount"],
            month        = row["month"],
        )
