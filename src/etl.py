"""
ETL pipeline: transactions.csv -> cleaned -> categorized -> SQLite.

This is the kind of pipeline an operations analyst ships for a business team:
raw data comes in, gets cleaned and enriched, lands in a queryable database
that powers dashboards and ad-hoc reports.
"""
import csv
import sqlite3
from datetime import datetime
from pathlib import Path

from src.categorizer import categorize

PROJECT_ROOT = Path(__file__).parent.parent
CSV_PATH = PROJECT_ROOT / "data" / "transactions.csv"
DB_PATH = PROJECT_ROOT / "finance.db"


def create_schema(conn: sqlite3.Connection) -> None:
    """Drop and recreate the transactions table. Idempotent reruns."""
    conn.execute("DROP TABLE IF EXISTS transactions")
    conn.execute("""
        CREATE TABLE transactions (
            id              INTEGER PRIMARY KEY AUTOINCREMENT,
            transaction_date DATE NOT NULL,
            description     TEXT NOT NULL,
            amount          REAL NOT NULL,
            txn_type        TEXT CHECK(txn_type IN ('credit', 'debit')),
            category        TEXT NOT NULL,
            year            INTEGER NOT NULL,
            month           INTEGER NOT NULL,
            month_label     TEXT NOT NULL
        )
    """)
    # Indexes on the fields we filter/group by most — standard analyst move
    conn.execute("CREATE INDEX idx_date ON transactions(transaction_date)")
    conn.execute("CREATE INDEX idx_category ON transactions(category)")
    conn.execute("CREATE INDEX idx_month ON transactions(year, month)")
    conn.commit()


def load_and_transform(csv_path: Path) -> list[tuple]:
    """Read CSV, clean, categorize, and return rows ready to insert."""
    rows = []
    with open(csv_path, newline="") as f:
        reader = csv.DictReader(f)
        for r in reader:
            # Parse date — coerce, skip if bad
            try:
                dt = datetime.strptime(r["Date"].strip(), "%Y-%m-%d").date()
            except ValueError:
                continue

            description = r["Description"].strip()
            try:
                amount = float(r["Amount"])
            except ValueError:
                continue

            txn_type = r["Type"].strip().lower()
            category = categorize(description)

            rows.append((
                dt.isoformat(),
                description,
                amount,
                txn_type,
                category,
                dt.year,
                dt.month,
                dt.strftime("%Y-%m"),
            ))
    return rows


def insert_rows(conn: sqlite3.Connection, rows: list[tuple]) -> int:
    """Bulk insert. Returns count inserted."""
    conn.executemany("""
        INSERT INTO transactions
        (transaction_date, description, amount, txn_type, category, year, month, month_label)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
    """, rows)
    conn.commit()
    return len(rows)


def run_data_quality_checks(conn: sqlite3.Connection) -> dict:
    """Basic checks an analyst runs after every load — count, null-scan, anomalies."""
    cur = conn.cursor()
    report = {}

    cur.execute("SELECT COUNT(*) FROM transactions")
    report["total_rows"] = cur.fetchone()[0]

    cur.execute("SELECT COUNT(*) FROM transactions WHERE category = 'Other'")
    report["uncategorized_rows"] = cur.fetchone()[0]

    cur.execute("SELECT MIN(transaction_date), MAX(transaction_date) FROM transactions")
    min_d, max_d = cur.fetchone()
    report["date_range"] = f"{min_d} to {max_d}"

    cur.execute("SELECT COUNT(DISTINCT category) FROM transactions")
    report["distinct_categories"] = cur.fetchone()[0]

    return report


def main():
    print("Creating SQLite schema...")
    conn = sqlite3.connect(DB_PATH)
    create_schema(conn)

    print(f"Loading from {CSV_PATH}...")
    rows = load_and_transform(CSV_PATH)
    count = insert_rows(conn, rows)
    print(f"Inserted {count} rows")

    print("\nData quality checks:")
    report = run_data_quality_checks(conn)
    for k, v in report.items():
        print(f"  {k}: {v}")

    uncategorized_pct = (report["uncategorized_rows"] / report["total_rows"]) * 100
    print(f"\nUncategorized rate: {uncategorized_pct:.1f}%")
    if uncategorized_pct > 10:
        print("  WARNING: uncategorized rate > 10%, consider adding rules")
    else:
        print("  OK")

    conn.close()


if __name__ == "__main__":
    main()
