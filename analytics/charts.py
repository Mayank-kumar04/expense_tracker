"""
analytics/charts.py
--------------------
Matplotlib figures embedded inside PyQt5 widgets.

Each chart class is self-contained: give it a DB reference and a month,
call .refresh(), and it draws itself inside a QWidget.
"""

from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as FigureCanvas
from matplotlib.figure import Figure
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
from collections import defaultdict
from datetime import datetime, timedelta

# ── Colour tokens (match the dark theme) ─────────────────────────────────────
BG      = "#1e1e2e"
CARD_BG = "#313244"
TEXT    = "#cdd6f4"
MUTED   = "#6c7086"
ACCENT  = "#cba6f7"
GREEN   = "#a6e3a1"
RED     = "#f38ba8"
YELLOW  = "#f9e2af"
BLUE    = "#89b4fa"
PEACH   = "#fab387"
TEAL    = "#94e2d5"
PINK    = "#f5c2e7"
MAUVE   = "#cba6f7"

CATEGORY_COLORS = [ACCENT, GREEN, RED, YELLOW, BLUE, PEACH, TEAL, PINK, MAUVE,
                   "#b5e8e0", "#eba0ac", "#f2cdcd"]


def _apply_dark_style(fig, ax_list):
    """Apply dark theme to a matplotlib figure and its axes."""
    fig.patch.set_facecolor(CARD_BG)
    for ax in ax_list:
        ax.set_facecolor(CARD_BG)
        ax.tick_params(colors=MUTED, labelsize=9)
        ax.xaxis.label.set_color(MUTED)
        ax.yaxis.label.set_color(MUTED)
        ax.title.set_color(TEXT)
        for spine in ax.spines.values():
            spine.set_edgecolor(MUTED)
            spine.set_alpha(0.3)


# ── Base canvas ───────────────────────────────────────────────────────────────
class BaseChart(FigureCanvas):
    def __init__(self, db, width=5, height=4):
        self.db = db
        self.fig = Figure(figsize=(width, height), tight_layout=True)
        super().__init__(self.fig)
        self.setStyleSheet(f"background-color: {CARD_BG}; border-radius: 12px;")

    def clear(self):
        self.fig.clear()


# ── 1. Pie chart: spending by category ───────────────────────────────────────
class CategoryPieChart(BaseChart):
    """Donut-style pie chart of expense distribution for a given month."""

    def refresh(self, year_month: str):
        self.clear()
        rows = self.db.get_category_totals(year_month)
        if not rows:
            ax = self.fig.add_subplot(111)
            ax.text(0.5, 0.5, "No expense data", ha="center", va="center",
                    color=MUTED, fontsize=13)
            _apply_dark_style(self.fig, [ax])
            ax.set_axis_off()
            self.draw()
            return

        labels = [r["category"] for r in rows]
        values = [r["total"]    for r in rows]
        colors = CATEGORY_COLORS[:len(labels)]

        ax = self.fig.add_subplot(111)
        wedges, texts, autotexts = ax.pie(
            values,
            labels=None,
            colors=colors,
            autopct=lambda p: f"{p:.1f}%" if p > 4 else "",
            startangle=140,
            wedgeprops=dict(width=0.55, edgecolor=CARD_BG, linewidth=2),
            pctdistance=0.78,
        )
        for at in autotexts:
            at.set_color(BG)
            at.set_fontsize(8)
            at.set_fontweight("bold")

        ax.set_title(f"Spending by Category — {year_month}", color=TEXT, fontsize=11, pad=10)

        # Legend outside
        patches = [mpatches.Patch(color=colors[i], label=f"{labels[i]}  ₹{values[i]:,.0f}")
                   for i in range(len(labels))]
        ax.legend(handles=patches, loc="lower center",
                  bbox_to_anchor=(0.5, -0.25),
                  ncol=3, frameon=False,
                  fontsize=8, labelcolor=TEXT)

        _apply_dark_style(self.fig, [ax])
        self.draw()


# ── 2. Bar chart: monthly spending trend ─────────────────────────────────────
class MonthlyTrendChart(BaseChart):
    """Grouped bar chart showing income vs expense for last 6 months."""

    def refresh(self, user_id: int = 1):
        self.clear()
        rows = self.db.get_monthly_trend(user_id, months=6)

        # Build month→{income, expense} dict
        data = defaultdict(lambda: {"income": 0.0, "expense": 0.0})
        for row in rows:
            data[row["month"]][row["type"]] += row["total"]

        # Sort chronologically, take last 6
        months = sorted(data.keys())[-6:]
        incomes  = [data[m]["income"]  for m in months]
        expenses = [data[m]["expense"] for m in months]

        # Short labels: "Jan 25"
        labels = []
        for m in months:
            try:
                labels.append(datetime.strptime(m, "%Y-%m").strftime("%b %y"))
            except ValueError:
                labels.append(m)

        ax = self.fig.add_subplot(111)
        x = range(len(months))
        w = 0.38

        bars_inc = ax.bar([i - w/2 for i in x], incomes,  width=w,
                          color=GREEN, alpha=0.85, label="Income",  zorder=3)
        bars_exp = ax.bar([i + w/2 for i in x], expenses, width=w,
                          color=RED,   alpha=0.85, label="Expense", zorder=3)

        ax.set_xticks(list(x))
        ax.set_xticklabels(labels)
        ax.set_title("Income vs Expense — Last 6 Months", color=TEXT, fontsize=11)
        ax.yaxis.set_major_formatter(plt.FuncFormatter(lambda v, _: f"₹{v/1000:.0f}k" if v >= 1000 else f"₹{v:.0f}"))
        ax.grid(axis="y", color=MUTED, alpha=0.2, zorder=0)
        ax.legend(frameon=False, labelcolor=TEXT, fontsize=9)

        # Value labels on bars
        for bar in list(bars_inc) + list(bars_exp):
            h = bar.get_height()
            if h > 0:
                ax.text(bar.get_x() + bar.get_width() / 2, h + h * 0.02,
                        f"₹{h:,.0f}", ha="center", va="bottom",
                        color=TEXT, fontsize=7)

        _apply_dark_style(self.fig, [ax])
        self.draw()


# ── 3. Line chart: daily spending for a month ─────────────────────────────────
class DailySpendingChart(BaseChart):
    """Cumulative spending line for the current month."""

    def refresh(self, year_month: str, user_id: int = 1):
        self.clear()
        start = f"{year_month}-01"
        # Last day of the month
        first = datetime.strptime(start, "%Y-%m-%d")
        if first.month == 12:
            last = first.replace(day=31)
        else:
            last = first.replace(month=first.month + 1) - timedelta(days=1)
        end = last.strftime("%Y-%m-%d")

        rows = self.db.get_transactions(user_id=user_id, tx_type="expense",
                                        start_date=start, end_date=end)

        # Accumulate by day
        daily = defaultdict(float)
        for r in rows:
            daily[r["transaction_date"]] += r["amount"]

        if not daily:
            ax = self.fig.add_subplot(111)
            ax.text(0.5, 0.5, "No data this month", ha="center", va="center",
                    color=MUTED, fontsize=13)
            _apply_dark_style(self.fig, [ax])
            ax.set_axis_off()
            self.draw()
            return

        sorted_days = sorted(daily.keys())
        values      = [daily[d] for d in sorted_days]
        cumulative  = []
        running = 0.0
        for v in values:
            running += v
            cumulative.append(running)

        day_labels = [d.split("-")[2].lstrip("0") for d in sorted_days]

        ax = self.fig.add_subplot(111)
        ax.plot(day_labels, cumulative, color=ACCENT, linewidth=2.5,
                marker="o", markersize=4, zorder=3)
        ax.fill_between(day_labels, cumulative, alpha=0.15, color=ACCENT)
        ax.set_title(f"Cumulative Spending — {year_month}", color=TEXT, fontsize=11)
        ax.set_xlabel("Day of Month")
        ax.yaxis.set_major_formatter(plt.FuncFormatter(
            lambda v, _: f"₹{v/1000:.1f}k" if v >= 1000 else f"₹{v:.0f}"))
        ax.grid(color=MUTED, alpha=0.15, zorder=0)
        ax.tick_params(axis="x", rotation=45)

        _apply_dark_style(self.fig, [ax])
        self.draw()


# ── 4. Horizontal bar: top merchants ─────────────────────────────────────────
class TopMerchantsChart(BaseChart):
    """Horizontal bar chart showing the top 8 merchants by spend."""

    def refresh(self, year_month: str, user_id: int = 1):
        self.clear()
        start = f"{year_month}-01"
        try:
            first = datetime.strptime(start, "%Y-%m-%d")
            if first.month == 12:
                last = first.replace(day=31)
            else:
                last = first.replace(month=first.month + 1) - timedelta(days=1)
            end = last.strftime("%Y-%m-%d")
        except ValueError:
            end = start

        rows = self.db.get_transactions(user_id=user_id, tx_type="expense",
                                        start_date=start, end_date=end)

        merchant_totals = defaultdict(float)
        for r in rows:
            name = r["merchant"] or "Unknown"
            merchant_totals[name] += r["amount"]

        if not merchant_totals:
            ax = self.fig.add_subplot(111)
            ax.text(0.5, 0.5, "No expense data", ha="center", va="center",
                    color=MUTED, fontsize=13)
            _apply_dark_style(self.fig, [ax])
            ax.set_axis_off()
            self.draw()
            return

        top = sorted(merchant_totals.items(), key=lambda x: x[1], reverse=True)[:8]
        names  = [t[0] for t in reversed(top)]
        values = [t[1] for t in reversed(top)]

        ax = self.fig.add_subplot(111)
        bars = ax.barh(names, values, color=ACCENT, alpha=0.85)

        for bar, val in zip(bars, values):
            ax.text(bar.get_width() + max(values) * 0.01, bar.get_y() + bar.get_height() / 2,
                    f"₹{val:,.0f}", va="center", color=TEXT, fontsize=8)

        ax.set_title(f"Top Merchants — {year_month}", color=TEXT, fontsize=11)
        ax.set_xlim(0, max(values) * 1.2)
        ax.grid(axis="x", color=MUTED, alpha=0.15)
        _apply_dark_style(self.fig, [ax])
        self.draw()
