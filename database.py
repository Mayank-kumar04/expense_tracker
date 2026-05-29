"""
database.py
-----------
Handles all SQLite database operations for the Expense Tracker.
Uses a singleton DatabaseManager class so the same connection
is reused across the whole app.
"""

import sqlite3
import hashlib
import os
from datetime import datetime


# ── Path to the SQLite file (sits next to this script) ──────────────────────
DB_PATH = os.path.join(os.path.dirname(__file__), "expense_tracker.db")


# ── Helper: hash a password with SHA-256 ────────────────────────────────────
def hash_password(password: str) -> str:
    return hashlib.sha256(password.encode()).hexdigest()


# ── DatabaseManager ──────────────────────────────────────────────────────────
class DatabaseManager:
    """
    Central class for all database interactions.

    Usage:
        db = DatabaseManager()
        db.add_transaction(...)
    """

    _instance = None  # singleton holder

    def __new__(cls):
        """Return the same instance every time (Singleton pattern)."""
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._init_db()
        return cls._instance

    # ── Initialisation ───────────────────────────────────────────────────────
    def _init_db(self):
        """Create tables if they don't exist yet."""
        self.conn = sqlite3.connect(DB_PATH, check_same_thread=False)
        self.conn.row_factory = sqlite3.Row  # rows behave like dicts
        self._create_tables()
        self._seed_categories()

    def _create_tables(self):
        cursor = self.conn.cursor()
        cursor.executescript("""
            -- Users table for optional login system
            CREATE TABLE IF NOT EXISTS users (
                id            INTEGER PRIMARY KEY AUTOINCREMENT,
                username      TEXT    UNIQUE NOT NULL,
                password_hash TEXT    NOT NULL,
                created_at    TEXT    DEFAULT (datetime('now'))
            );

            -- All transactions (expenses + income)
            CREATE TABLE IF NOT EXISTS transactions (
                id               INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id          INTEGER DEFAULT 1,
                amount           REAL    NOT NULL,
                category         TEXT    NOT NULL,
                merchant         TEXT,
                type             TEXT    NOT NULL CHECK(type IN ('expense','income')),
                payment_mode     TEXT    DEFAULT 'Cash',
                notes            TEXT,
                transaction_date TEXT    NOT NULL,
                created_at       TEXT    DEFAULT (datetime('now')),
                FOREIGN KEY(user_id) REFERENCES users(id)
            );

            -- Expense / income categories
            CREATE TABLE IF NOT EXISTS categories (
                id   INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT UNIQUE NOT NULL
            );

            -- Monthly budgets per category
            CREATE TABLE IF NOT EXISTS budgets (
                id           INTEGER PRIMARY KEY AUTOINCREMENT,
                category     TEXT NOT NULL,
                limit_amount REAL NOT NULL,
                month        TEXT NOT NULL,   -- format: "YYYY-MM"
                UNIQUE(category, month)
            );
        """)
        self.conn.commit()

    def _seed_categories(self):
        """Insert default categories if the table is empty."""
        default_categories = [
            "Food", "Transport", "Shopping", "Entertainment",
            "Health", "Utilities", "Education", "Travel",
            "Rent", "Salary", "Freelance", "Investment", "Other"
        ]
        cursor = self.conn.cursor()
        for name in default_categories:
            cursor.execute(
                "INSERT OR IGNORE INTO categories (name) VALUES (?)", (name,)
            )
        self.conn.commit()

    # ── User methods ─────────────────────────────────────────────────────────
    def create_user(self, username: str, password: str) -> bool:
        """Register a new user. Returns True on success, False if name taken."""
        try:
            self.conn.execute(
                "INSERT INTO users (username, password_hash) VALUES (?, ?)",
                (username, hash_password(password))
            )
            self.conn.commit()
            return True
        except sqlite3.IntegrityError:
            return False  # username already exists

    def verify_user(self, username: str, password: str):
        """Return user row if credentials match, else None."""
        row = self.conn.execute(
            "SELECT * FROM users WHERE username=? AND password_hash=?",
            (username, hash_password(password))
        ).fetchone()
        return row

    # ── Transaction methods ──────────────────────────────────────────────────
    def add_transaction(self, amount: float, category: str, merchant: str,
                        tx_type: str, payment_mode: str = "Cash",
                        notes: str = "", date: str = None,
                        user_id: int = 1) -> int:
        """
        Insert a transaction. Returns the new row's id.

        tx_type must be 'expense' or 'income'.
        date defaults to today if not provided (format: YYYY-MM-DD).
        """
        if date is None:
            date = datetime.today().strftime("%Y-%m-%d")

        cursor = self.conn.execute(
            """INSERT INTO transactions
               (user_id, amount, category, merchant, type,
                payment_mode, notes, transaction_date)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
            (user_id, amount, category, merchant, tx_type,
             payment_mode, notes, date)
        )
        self.conn.commit()
        return cursor.lastrowid

    def get_transactions(self, user_id: int = 1, limit: int = None,
                         category: str = None, tx_type: str = None,
                         start_date: str = None, end_date: str = None):
        """
        Fetch transactions with optional filters.
        Returns a list of sqlite3.Row objects (access by column name).
        """
        query = "SELECT * FROM transactions WHERE user_id=?"
        params = [user_id]

        if category:
            query += " AND category=?"
            params.append(category)
        if tx_type:
            query += " AND type=?"
            params.append(tx_type)
        if start_date:
            query += " AND transaction_date >= ?"
            params.append(start_date)
        if end_date:
            query += " AND transaction_date <= ?"
            params.append(end_date)

        query += " ORDER BY transaction_date DESC, id DESC"

        if limit:
            query += f" LIMIT {int(limit)}"

        return self.conn.execute(query, params).fetchall()

    def update_transaction(self, tx_id: int, amount: float, category: str,
                           merchant: str, tx_type: str, payment_mode: str,
                           notes: str, date: str):
        """Update an existing transaction by id."""
        self.conn.execute(
            """UPDATE transactions
               SET amount=?, category=?, merchant=?, type=?,
                   payment_mode=?, notes=?, transaction_date=?
               WHERE id=?""",
            (amount, category, merchant, tx_type,
             payment_mode, notes, date, tx_id)
        )
        self.conn.commit()

    def delete_transaction(self, tx_id: int):
        """Delete a transaction by id."""
        self.conn.execute("DELETE FROM transactions WHERE id=?", (tx_id,))
        self.conn.commit()

    def search_transactions(self, keyword: str, user_id: int = 1):
        """Search by merchant name or notes (case-insensitive)."""
        kw = f"%{keyword}%"
        return self.conn.execute(
            """SELECT * FROM transactions
               WHERE user_id=?
                 AND (merchant LIKE ? OR notes LIKE ? OR category LIKE ?)
               ORDER BY transaction_date DESC""",
            (user_id, kw, kw, kw)
        ).fetchall()

    # ── Analytics helpers ────────────────────────────────────────────────────
    def get_monthly_summary(self, year_month: str, user_id: int = 1) -> dict:
        """
        Return total income and expenses for a given month.
        year_month format: "YYYY-MM"
        """
        rows = self.conn.execute(
            """SELECT type, SUM(amount) as total
               FROM transactions
               WHERE user_id=? AND strftime('%Y-%m', transaction_date)=?
               GROUP BY type""",
            (user_id, year_month)
        ).fetchall()

        summary = {"income": 0.0, "expense": 0.0}
        for row in rows:
            summary[row["type"]] = row["total"] or 0.0
        summary["balance"] = summary["income"] - summary["expense"]
        return summary

    def get_category_totals(self, year_month: str, user_id: int = 1):
        """Return per-category spending totals for the given month."""
        return self.conn.execute(
            """SELECT category, SUM(amount) as total
               FROM transactions
               WHERE user_id=?
                 AND type='expense'
                 AND strftime('%Y-%m', transaction_date)=?
               GROUP BY category
               ORDER BY total DESC""",
            (user_id, year_month)
        ).fetchall()

    def get_monthly_trend(self, user_id: int = 1, months: int = 6):
        """Return the last N months of income/expense totals for trend charts."""
        return self.conn.execute(
            """SELECT strftime('%Y-%m', transaction_date) as month,
                      type,
                      SUM(amount) as total
               FROM transactions
               WHERE user_id=?
               GROUP BY month, type
               ORDER BY month DESC
               LIMIT ?""",
            (user_id, months * 2)  # *2 because income+expense per month
        ).fetchall()

    # ── Category methods ─────────────────────────────────────────────────────
    def get_categories(self) -> list:
        rows = self.conn.execute(
            "SELECT name FROM categories ORDER BY name"
        ).fetchall()
        return [r["name"] for r in rows]

    def add_category(self, name: str) -> bool:
        try:
            self.conn.execute(
                "INSERT INTO categories (name) VALUES (?)", (name,)
            )
            self.conn.commit()
            return True
        except sqlite3.IntegrityError:
            return False

    # ── Budget methods ───────────────────────────────────────────────────────
    def set_budget(self, category: str, limit_amount: float, month: str):
        """Insert or update a category budget for a given month."""
        self.conn.execute(
            """INSERT INTO budgets (category, limit_amount, month)
               VALUES (?, ?, ?)
               ON CONFLICT(category, month)
               DO UPDATE SET limit_amount=excluded.limit_amount""",
            (category, limit_amount, month)
        )
        self.conn.commit()

    def get_budgets(self, month: str):
        return self.conn.execute(
            "SELECT * FROM budgets WHERE month=?", (month,)
        ).fetchall()

    def get_budget_status(self, month: str, user_id: int = 1):
        """
        Compare actual spending vs budget for each category.
        Returns list of dicts with keys: category, limit, spent, remaining, over_budget
        """
        budgets = {r["category"]: r["limit_amount"] for r in self.get_budgets(month)}
        actuals = {
            r["category"]: r["total"]
            for r in self.get_category_totals(month, user_id)
        }

        result = []
        for cat, limit in budgets.items():
            spent = actuals.get(cat, 0.0)
            result.append({
                "category":   cat,
                "limit":      limit,
                "spent":      spent,
                "remaining":  limit - spent,
                "over_budget": spent > limit
            })
        return result

    # ── Cleanup ──────────────────────────────────────────────────────────────
    def close(self):
        self.conn.close()
