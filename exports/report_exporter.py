"""
exports/report_exporter.py
---------------------------
Export transaction data to:
  - CSV (plain spreadsheet)
  - PDF (formatted report using reportlab)
"""

import csv
import os
from datetime import datetime
from typing import List


# ── CSV export ────────────────────────────────────────────────────────────────

def export_to_csv(transactions, filepath: str) -> bool:
    """
    Write transactions to a CSV file.

    transactions: list of sqlite3.Row or Transaction objects
    Returns True on success.
    """
    try:
        with open(filepath, "w", newline="", encoding="utf-8") as f:
            writer = csv.writer(f)
            writer.writerow([
                "ID", "Date", "Merchant", "Category",
                "Type", "Amount", "Payment Mode", "Notes"
            ])
            for t in transactions:
                # Support both sqlite3.Row (subscript) and Transaction dataclass
                if hasattr(t, "keys"):        # sqlite3.Row
                    writer.writerow([
                        t["id"], t["transaction_date"], t["merchant"],
                        t["category"], t["type"], t["amount"],
                        t["payment_mode"], t["notes"]
                    ])
                else:                          # Transaction dataclass
                    writer.writerow([
                        t.id, t.date, t.merchant, t.category,
                        t.tx_type, t.amount, t.payment_mode, t.notes
                    ])
        return True
    except Exception as e:
        print(f"[export] CSV error: {e}")
        return False


# ── PDF export ────────────────────────────────────────────────────────────────

def export_to_pdf(transactions, summary: dict, month: str, filepath: str) -> bool:
    """
    Write a formatted PDF report with summary cards and a full transactions table.

    summary: dict with keys income, expense, balance
    month:   "YYYY-MM" string
    """
    try:
        from reportlab.lib.pagesizes import A4
        from reportlab.lib import colors
        from reportlab.lib.units import cm
        from reportlab.platypus import (
            SimpleDocTemplate, Table, TableStyle, Paragraph,
            Spacer, HRFlowable
        )
        from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
        from reportlab.lib.enums import TA_CENTER, TA_RIGHT

        # ── Colours ────────────────────────────────────────────────────────────
        DARK   = colors.HexColor("#1e1e2e")
        PURPLE = colors.HexColor("#cba6f7")
        GREEN  = colors.HexColor("#a6e3a1")
        RED    = colors.HexColor("#f38ba8")
        GREY   = colors.HexColor("#313244")
        LIGHT  = colors.HexColor("#cdd6f4")
        MUTED  = colors.HexColor("#6c7086")
        WHITE  = colors.white

        doc = SimpleDocTemplate(
            filepath,
            pagesize=A4,
            leftMargin=2*cm, rightMargin=2*cm,
            topMargin=2*cm,  bottomMargin=2*cm
        )

        styles = getSampleStyleSheet()
        story  = []

        # Title
        title_style = ParagraphStyle("title", fontSize=22, textColor=PURPLE,
                                     alignment=TA_CENTER, spaceAfter=4,
                                     fontName="Helvetica-Bold")
        sub_style   = ParagraphStyle("sub", fontSize=11, textColor=MUTED,
                                     alignment=TA_CENTER, spaceAfter=16)
        story.append(Paragraph("💰 Expense Tracker Report", title_style))
        try:
            month_display = datetime.strptime(month, "%Y-%m").strftime("%B %Y")
        except ValueError:
            month_display = month
        story.append(Paragraph(f"Monthly Report — {month_display}", sub_style))
        story.append(HRFlowable(width="100%", color=GREY, thickness=1))
        story.append(Spacer(1, 0.4*cm))

        # Summary table
        inc = summary.get("income", 0)
        exp = summary.get("expense", 0)
        bal = inc - exp
        rate = (bal / inc * 100) if inc > 0 else 0.0

        summary_data = [
            ["Total Income", "Total Expense", "Net Balance", "Savings Rate"],
            [f"₹{inc:,.2f}", f"₹{exp:,.2f}", f"₹{bal:,.2f}", f"{rate:.1f}%"],
        ]
        sum_table = Table(summary_data, colWidths=[4.4*cm]*4)
        sum_table.setStyle(TableStyle([
            ("BACKGROUND",  (0, 0), (-1, 0), GREY),
            ("TEXTCOLOR",   (0, 0), (-1, 0), MUTED),
            ("TEXTCOLOR",   (0, 1), (0, 1),  GREEN),
            ("TEXTCOLOR",   (1, 1), (1, 1),  RED),
            ("TEXTCOLOR",   (2, 1), (2, 1),  PURPLE),
            ("TEXTCOLOR",   (3, 1), (3, 1),  PURPLE),
            ("FONTNAME",    (0, 0), (-1, -1), "Helvetica"),
            ("FONTNAME",    (0, 1), (-1, 1),  "Helvetica-Bold"),
            ("FONTSIZE",    (0, 0), (-1, 0),  9),
            ("FONTSIZE",    (0, 1), (-1, 1),  14),
            ("ALIGN",       (0, 0), (-1, -1), "CENTER"),
            ("VALIGN",      (0, 0), (-1, -1), "MIDDLE"),
            ("ROWBACKGROUNDS", (0, 0), (-1, -1), [GREY, DARK]),
            ("BOX",         (0, 0), (-1, -1), 0.5, MUTED),
            ("INNERGRID",   (0, 0), (-1, -1), 0.5, GREY),
            ("TOPPADDING",  (0, 0), (-1, -1), 8),
            ("BOTTOMPADDING",(0, 0), (-1, -1), 8),
        ]))
        story.append(sum_table)
        story.append(Spacer(1, 0.6*cm))

        # Transactions table
        hdr_style = ParagraphStyle("hdr", fontSize=13, textColor=LIGHT,
                                   fontName="Helvetica-Bold", spaceAfter=8)
        story.append(Paragraph("Transactions", hdr_style))

        tx_headers = ["Date", "Merchant", "Category", "Type", "Mode", "Amount"]
        tx_data = [tx_headers]
        for t in transactions:
            if hasattr(t, "keys"):
                row = [
                    t["transaction_date"], t["merchant"] or "—", t["category"],
                    t["type"].capitalize(), t["payment_mode"],
                    f"₹{t['amount']:,.2f}"
                ]
                is_income = t["type"] == "income"
            else:
                row = [
                    t.date, t.merchant or "—", t.category,
                    t.tx_type.capitalize(), t.payment_mode,
                    f"₹{t.amount:,.2f}"
                ]
                is_income = t.tx_type == "income"
            tx_data.append(row)

        col_widths = [2.5*cm, 4*cm, 3*cm, 2*cm, 3*cm, 3*cm]
        tx_table = Table(tx_data, colWidths=col_widths, repeatRows=1)
        tx_style = [
            ("BACKGROUND",  (0, 0), (-1, 0), GREY),
            ("TEXTCOLOR",   (0, 0), (-1, 0), MUTED),
            ("FONTNAME",    (0, 0), (-1, 0), "Helvetica-Bold"),
            ("FONTSIZE",    (0, 0), (-1, -1), 8),
            ("ALIGN",       (0, 0), (-1, -1), "CENTER"),
            ("VALIGN",      (0, 0), (-1, -1), "MIDDLE"),
            ("TOPPADDING",  (0, 0), (-1, -1), 5),
            ("BOTTOMPADDING",(0, 0),(-1, -1), 5),
            ("BOX",         (0, 0), (-1, -1), 0.5, MUTED),
            ("INNERGRID",   (0, 0), (-1, -1), 0.3, GREY),
        ]
        # Alternate row colours + amount colour
        for i in range(1, len(tx_data)):
            bg = colors.HexColor("#2a2a3e") if i % 2 == 0 else DARK
            tx_style.append(("BACKGROUND", (0, i), (-1, i), bg))
            tx_style.append(("TEXTCOLOR", (0, i), (-1, i), LIGHT))
            # Amount column coloured by type
            row_raw = tx_data[i]
            is_inc  = row_raw[3].lower() == "income"
            tx_style.append(("TEXTCOLOR", (5, i), (5, i), GREEN if is_inc else RED))

        tx_table.setStyle(TableStyle(tx_style))
        story.append(tx_table)

        # Footer
        story.append(Spacer(1, 0.6*cm))
        footer_style = ParagraphStyle("footer", fontSize=8, textColor=MUTED,
                                      alignment=TA_CENTER)
        story.append(Paragraph(
            f"Generated by Smart Expense Tracker on {datetime.today().strftime('%d %b %Y %H:%M')}",
            footer_style
        ))

        doc.build(story)
        return True

    except ImportError:
        print("[export] reportlab not installed. Run: pip install reportlab")
        return False
    except Exception as e:
        print(f"[export] PDF error: {e}")
        return False
