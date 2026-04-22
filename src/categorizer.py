"""
Rule-based categorizer.

Banks export transactions with merchant names but no categories.
This module assigns categories using keyword matching — the same kind of
approach personal finance tools like Mint, Copilot, and YNAB use as a baseline
before layering ML on top.

Why rules first: they're interpretable, fast, and auditable. For an ops analyst,
being able to explain *why* a transaction was categorized a certain way matters
more than squeezing the last 2% of accuracy.
"""

# Order matters: more specific patterns should come before generic ones.
# For instance, "DOORDASH*CHICK FIL A" should hit Dining, not Shopping.
RULES = [
    # ---- Income ----
    (["PAYROLL", "DIRECT DEPOSIT"], "Income"),
    (["INTEREST PAID"], "Income"),
    (["ZELLE FROM", "VENMO CASHOUT"], "Income"),

    # ---- Transfers ----
    (["TRANSFER TO", "TRANSFER FROM"], "Transfers"),
    (["ZELLE TO", "VENMO PAYMENT"], "Transfers"),
    (["CREDIT CARD PAYMENT", "CC PAYMENT"], "Transfers"),

    # ---- Dining (before shopping so DoorDash doesn't hit Amazon) ----
    (["DOORDASH", "UBER EATS", "GRUBHUB", "POSTMATES"], "Dining"),
    (["STARBUCKS", "DUNKIN", "BLUE BOTTLE"], "Dining"),
    (["CHIPOTLE", "PANERA", "SHAKE SHACK", "CHICK FIL A", "SWEETGREEN"], "Dining"),

    # ---- Groceries ----
    (["TRADER JOE", "WHOLE FOODS", "KROGER", "PUBLIX", "ALDI", "COSTCO"], "Groceries"),
    (["SAFEWAY", "WEGMANS", "SPROUTS"], "Groceries"),

    # ---- Transportation ----
    (["UBER TRIP", "LYFT"], "Transportation"),
    (["SHELL", "CHEVRON", "EXXON", "BP "], "Transportation"),
    (["MARTA", "PARKING", "METRO"], "Transportation"),

    # ---- Travel ----
    (["DELTA AIR", "UNITED ", "AMERICAN AIR", "SOUTHWEST AIR"], "Travel"),
    (["MARRIOTT", "HILTON", "AIRBNB", "HYATT"], "Travel"),
    (["HERTZ", "ENTERPRISE RENT", "AVIS"], "Travel"),

    # ---- Entertainment ----
    (["NETFLIX", "SPOTIFY", "HBOMAX", "HULU", "DISNEY+"], "Entertainment"),
    (["STEAM PURCHASE", "AUDIBLE"], "Entertainment"),
    (["AMC ", "REGAL CINEMA"], "Entertainment"),

    # ---- Bills & Utilities ----
    (["GEORGIA POWER", "CON EDISON", "WATER DEPT"], "Bills & Utilities"),
    (["ATT*", "VERIZON", "T-MOBILE", "GOOGLE *FI"], "Bills & Utilities"),
    (["COMCAST", "SPECTRUM", "XFINITY"], "Bills & Utilities"),

    # ---- Health & Fitness ----
    (["CVS", "WALGREENS", "RITE AID"], "Health & Fitness"),
    (["CLASSPASS", "ORANGETHEORY", "EQUINOX", "PLANET FITNESS"], "Health & Fitness"),
    (["KAISER", "AETNA", "CIGNA"], "Health & Fitness"),

    # ---- Shopping (broad, goes last) ----
    (["AMAZON", "AMZN"], "Shopping"),
    (["TARGET", "WALMART", "BEST BUY"], "Shopping"),
    (["SEPHORA", "ULTA", "NORDSTROM"], "Shopping"),
]


def categorize(description: str) -> str:
    """Assign a category to a transaction description. Returns 'Other' if nothing matches."""
    if not description:
        return "Other"

    upper = description.upper()
    for keywords, category in RULES:
        for kw in keywords:
            if kw in upper:
                return category
    return "Other"


def categorize_batch(descriptions: list[str]) -> list[str]:
    """Categorize a list of descriptions. Convenience for ETL."""
    return [categorize(d) for d in descriptions]


if __name__ == "__main__":
    # Quick sanity check when run directly
    test_cases = [
        ("STARBUCKS STORE 22981", "Dining"),
        ("AMAZON.COM*AB2X4", "Shopping"),
        ("PAYROLL DEPOSIT - SRI", "Income"),
        ("UBER TRIP", "Transportation"),
        ("DOORDASH*CHICK FIL A", "Dining"),
        ("RANDOM UNKNOWN THING", "Other"),
    ]

    all_pass = True
    for desc, expected in test_cases:
        result = categorize(desc)
        status = "OK" if result == expected else "FAIL"
        if result != expected:
            all_pass = False
        print(f"{status:4} | {desc:40} -> {result} (expected {expected})")

    print()
    print("All passed" if all_pass else "FAILURES above")
