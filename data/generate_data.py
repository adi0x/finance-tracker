"""
Generate synthetic bank transactions that look like a real export.

Why synthetic: avoids PII, reproducible, and the structure matches
what Chase, Bank of America, and most US banks export as CSV.
"""
import csv
import random
from datetime import datetime, timedelta
from pathlib import Path

random.seed(42)

# Real merchants grouped by category — what the ETL will have to figure out
MERCHANTS = {
    "Groceries": [
        "TRADER JOE'S #547", "WHOLE FOODS MKT 10155", "KROGER #412",
        "PUBLIX SUPER MARKET", "ALDI 63 STORE", "COSTCO WHSE #1187",
    ],
    "Dining": [
        "STARBUCKS STORE 22981", "CHIPOTLE 2847", "DOORDASH*CHICK FIL A",
        "UBER EATS", "PANERA BREAD #204876", "SWEETGREEN ATLANTA",
        "BLUE BOTTLE COFFEE", "SHAKE SHACK ATL",
    ],
    "Transportation": [
        "UBER TRIP", "LYFT *RIDE", "SHELL OIL 12496", "CHEVRON 0092846",
        "MARTA BREEZE CARD RELOAD", "PARKING METER ATLANTA",
    ],
    "Shopping": [
        "AMAZON.COM*AB2X4", "TARGET 00023847", "AMAZON MKTPL*AC7",
        "SEPHORA #0529", "NORDSTROM #358", "BEST BUY #1234",
    ],
    "Entertainment": [
        "NETFLIX.COM", "SPOTIFY USA", "AMC ATLANTIC STATION",
        "STEAM PURCHASE", "HBOMAX.COM", "AUDIBLE*GLJ4PL20",
    ],
    "Bills & Utilities": [
        "GEORGIA POWER", "ATT*BILL PAYMENT", "COMCAST CABLE COMM",
        "VERIZON WIRELESS", "GOOGLE *FI", "WATER DEPT ATL",
    ],
    "Health & Fitness": [
        "CVS/PHARMACY #03847", "WALGREENS #12897", "CLASSPASS INC",
        "ORANGETHEORY FITNESS", "KAISER PERMANENTE",
    ],
    "Travel": [
        "DELTA AIR 0062847123", "MARRIOTT HOTELS", "AIRBNB * HMZX8",
        "HERTZ CAR RENTAL", "UNITED 0162948273",
    ],
    "Income": [
        "PAYROLL DEPOSIT - SRI", "VENMO CASHOUT", "ZELLE FROM MOM",
        "INTEREST PAID - SAVINGS",
    ],
    "Transfers": [
        "TRANSFER TO SAVINGS", "VENMO PAYMENT", "ZELLE TO ROOMMATE",
        "CREDIT CARD PAYMENT",
    ],
}

# How much each category typically costs — (min, max) in dollars
AMOUNT_RANGES = {
    "Groceries": (25, 180),
    "Dining": (8, 65),
    "Transportation": (6, 45),
    "Shopping": (15, 250),
    "Entertainment": (10, 80),
    "Bills & Utilities": (45, 220),
    "Health & Fitness": (12, 180),
    "Travel": (80, 600),
    "Income": (2800, 3400),
    "Transfers": (50, 800),
}

# How often each category appears — weights used in random.choices
FREQUENCY = {
    "Groceries": 0.15,
    "Dining": 0.30,
    "Transportation": 0.16,
    "Shopping": 0.14,
    "Entertainment": 0.07,
    "Bills & Utilities": 0.06,
    "Health & Fitness": 0.04,
    "Travel": 0.03,
    "Transfers": 0.05,
}


def generate(n_transactions=1200, months_back=14):
    """Produce n transactions spread over the last months_back months."""
    end_date = datetime(2026, 4, 20)
    start_date = end_date - timedelta(days=months_back * 30)

    rows = []
    categories = list(FREQUENCY.keys())
    weights = list(FREQUENCY.values())

    for _ in range(n_transactions):
        category = random.choices(categories, weights=weights, k=1)[0]
        merchant = random.choice(MERCHANTS[category])
        lo, hi = AMOUNT_RANGES[category]
        amount = round(random.uniform(lo, hi), 2)

        # Income is positive, everything else is negative (money out)
        if category == "Income":
            signed_amount = amount
        else:
            signed_amount = -amount

        # Random date in the range, biased toward recent
        days_offset = int(random.triangular(0, months_back * 30, months_back * 25))
        date = start_date + timedelta(days=days_offset)

        rows.append({
            "Date": date.strftime("%Y-%m-%d"),
            "Description": merchant,
            "Amount": signed_amount,
            "Type": "credit" if signed_amount > 0 else "debit",
        })

    # Sort by date for realism
    rows.sort(key=lambda r: r["Date"])

    # Add recurring monthly income on the 1st of each month
    current = start_date.replace(day=1)
    while current <= end_date:
        rows.append({
            "Date": current.strftime("%Y-%m-%d"),
            "Description": "PAYROLL DEPOSIT - SRI",
            "Amount": 3150.00,
            "Type": "credit",
        })
        # Move to the 1st of the next month
        if current.month == 12:
            current = current.replace(year=current.year + 1, month=1)
        else:
            current = current.replace(month=current.month + 1)

    rows.sort(key=lambda r: r["Date"])
    return rows


def main():
    out_path = Path(__file__).parent / "transactions.csv"
    rows = generate()

    with open(out_path, "w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=["Date", "Description", "Amount", "Type"])
        writer.writeheader()
        writer.writerows(rows)

    print(f"Generated {len(rows)} transactions")
    print(f"Written to {out_path}")
    print(f"Date range: {rows[0]['Date']} to {rows[-1]['Date']}")


if __name__ == "__main__":
    main()
