"""
utils/categorizer.py
---------------------
Maps merchant names / keywords to expense categories automatically.

Usage:
    from utils.categorizer import categorize
    category = categorize("Swiggy")   # → "Food"
"""

# ── Keyword → Category mapping ───────────────────────────────────────────────
# Keys are lowercase keywords; the value is the category label.

KEYWORD_MAP = {
    # Food & dining
    "swiggy":      "Food",
    "zomato":      "Food",
    "dominos":     "Food",
    "pizza":       "Food",
    "burger":      "Food",
    "mcdonalds":   "Food",
    "kfc":         "Food",
    "starbucks":   "Food",
    "cafe":        "Food",
    "restaurant":  "Food",
    "hotel":       "Food",
    "dhaba":       "Food",
    "biryani":     "Food",
    "bakery":      "Food",

    # Transport
    "uber":        "Transport",
    "ola":         "Transport",
    "rapido":      "Transport",
    "metro":       "Transport",
    "irctc":       "Transport",
    "railway":     "Transport",
    "petrol":      "Transport",
    "fuel":        "Transport",
    "indigo":      "Transport",
    "air india":   "Transport",
    "spicejet":    "Transport",
    "bus":         "Transport",

    # Shopping
    "amazon":      "Shopping",
    "flipkart":    "Shopping",
    "myntra":      "Shopping",
    "ajio":        "Shopping",
    "nykaa":       "Shopping",
    "meesho":      "Shopping",
    "blinkit":     "Shopping",
    "zepto":       "Shopping",
    "bigbasket":   "Shopping",
    "dmart":       "Shopping",
    "reliance":    "Shopping",
    "mall":        "Shopping",
    "store":       "Shopping",
    "shop":        "Shopping",

    # Entertainment
    "netflix":      "Entertainment",
    "hotstar":      "Entertainment",
    "prime video":  "Entertainment",
    "spotify":      "Entertainment",
    "youtube":      "Entertainment",
    "bookmyshow":   "Entertainment",
    "pvr":          "Entertainment",
    "inox":         "Entertainment",
    "cinema":       "Entertainment",
    "gaming":       "Entertainment",
    "steam":        "Entertainment",

    # Health
    "apollo":      "Health",
    "medplus":     "Health",
    "pharmacy":    "Health",
    "hospital":    "Health",
    "doctor":      "Health",
    "clinic":      "Health",
    "lab":         "Health",
    "gym":         "Health",
    "cult fit":    "Health",
    "healthkart":  "Health",

    # Utilities
    "electricity": "Utilities",
    "water":       "Utilities",
    "gas":         "Utilities",
    "wifi":        "Utilities",
    "broadband":   "Utilities",
    "airtel":      "Utilities",
    "jio":         "Utilities",
    "bsnl":        "Utilities",
    "vi ":         "Utilities",
    "mobile":      "Utilities",
    "recharge":    "Utilities",

    # Education
    "udemy":       "Education",
    "coursera":    "Education",
    "byjus":       "Education",
    "byju":        "Education",
    "unacademy":   "Education",
    "school":      "Education",
    "college":     "Education",
    "university":  "Education",
    "book":        "Education",
    "tuition":     "Education",
    "fees":        "Education",

    # Rent
    "rent":        "Rent",
    "pg ":         "Rent",
    "hostel":      "Rent",
    "housing":     "Rent",
    "nobroker":    "Rent",

    # Travel
    "oyo":         "Travel",
    "makemytrip":  "Travel",
    "goibibo":     "Travel",
    "trivago":     "Travel",
    "airbnb":      "Travel",

    # Income markers (for completeness)
    "salary":      "Salary",
    "payroll":     "Salary",
    "freelance":   "Freelance",
    "upwork":      "Freelance",
    "fiverr":      "Freelance",
    "dividend":    "Investment",
    "mutual fund": "Investment",
    "zerodha":     "Investment",
    "groww":       "Investment",
}


def categorize(merchant_or_text: str) -> str:
    """
    Return the best-matching category for a merchant name or free text.
    Defaults to 'Other' if no keyword matches.

    Args:
        merchant_or_text: Merchant name, SMS text, or any description string.

    Returns:
        Category string, e.g. "Food", "Transport", "Shopping" …
    """
    text = merchant_or_text.lower().strip()

    for keyword, category in KEYWORD_MAP.items():
        if keyword in text:
            return category

    return "Other"


def get_all_categories() -> list:
    """Return sorted unique list of all categories in the map."""
    return sorted(set(KEYWORD_MAP.values()))


# ── Quick self-test ──────────────────────────────────────────────────────────
if __name__ == "__main__":
    tests = [
        "Swiggy", "Uber", "Amazon", "Netflix", "Apollo Pharmacy",
        "Airtel Broadband", "Zerodha", "Random Shop", "IRCTC Train"
    ]
    for t in tests:
        print(f"{t:25s} → {categorize(t)}")
