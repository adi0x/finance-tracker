"""
Central SQL query module.

Keeping queries here (rather than in the Streamlit app) means:
  - SQL is auditable and reusable across notebooks, reports, and the app
  - The dashboard stays lean — it just calls functions
  - Future ops analyst (or you) can read one file to understand the analytics

This is the pattern teams use when analytics grow past 'one-off scripts.'
"""
import sqlite3
import pandas as pd
from pathlib import Path


DB_PATH = Path(__file__).parent.parent / "finance.db"


def _conn():
    return sqlite3.connect(DB_PATH)


def monthly_summary(start_date: str = None, end_date: str = None) -> pd.DataFrame:
    """Income, spending, and net per month. Excludes Transfers (internal movement)."""
    where_clauses = ["category != 'Transfers'"]
    params = []
    if start_date:
        where_clauses.append("transaction_date >= ?")
        params.append(start_date)
    if end_date:
        where_clauses.append("transaction_date <= ?")
        params.append(end_date)
    where_sql = " AND ".join(where_clauses)

    query = f"""
        SELECT
            month_label,
            SUM(CASE WHEN amount > 0 THEN amount ELSE 0 END)   AS income,
            SUM(CASE WHEN amount < 0 THEN -amount ELSE 0 END)  AS spending,
            SUM(amount) AS net_cash_flow
        FROM transactions
        WHERE {where_sql}
        GROUP BY month_label
        ORDER BY month_label
    """
    with _conn() as conn:
        return pd.read_sql(query, conn, params=params)


def spending_by_category(start_date: str = None, end_date: str = None) -> pd.DataFrame:
    """Total spend per category over the period. Excludes Income and Transfers."""
    where_clauses = ["amount < 0", "category NOT IN ('Transfers', 'Income')"]
    params = []
    if start_date:
        where_clauses.append("transaction_date >= ?")
        params.append(start_date)
    if end_date:
        where_clauses.append("transaction_date <= ?")
        params.append(end_date)
    where_sql = " AND ".join(where_clauses)

    query = f"""
        SELECT
            category,
            SUM(-amount) AS total_spent,
            COUNT(*)     AS transaction_count,
            ROUND(AVG(-amount), 2) AS avg_transaction
        FROM transactions
        WHERE {where_sql}
        GROUP BY category
        ORDER BY total_spent DESC
    """
    with _conn() as conn:
        return pd.read_sql(query, conn, params=params)


def category_trend(category: str, start_date: str = None, end_date: str = None) -> pd.DataFrame:
    """Monthly spend trend for a single category — used for drill-down."""
    where_clauses = ["amount < 0", "category = ?"]
    params = [category]
    if start_date:
        where_clauses.append("transaction_date >= ?")
        params.append(start_date)
    if end_date:
        where_clauses.append("transaction_date <= ?")
        params.append(end_date)
    where_sql = " AND ".join(where_clauses)

    query = f"""
        SELECT
            month_label,
            SUM(-amount) AS spent,
            COUNT(*)     AS transactions
        FROM transactions
        WHERE {where_sql}
        GROUP BY month_label
        ORDER BY month_label
    """
    with _conn() as conn:
        return pd.read_sql(query, conn, params=params)


def top_merchants(start_date: str = None, end_date: str = None, limit: int = 10) -> pd.DataFrame:
    """Merchants with the highest total spend — useful for finding silent budget holes."""
    where_clauses = ["amount < 0", "category NOT IN ('Transfers', 'Income')"]
    params = []
    if start_date:
        where_clauses.append("transaction_date >= ?")
        params.append(start_date)
    if end_date:
        where_clauses.append("transaction_date <= ?")
        params.append(end_date)
    where_sql = " AND ".join(where_clauses)

    query = f"""
        SELECT
            description                AS merchant,
            category,
            COUNT(*)                   AS visits,
            ROUND(SUM(-amount), 2)     AS total_spent
        FROM transactions
        WHERE {where_sql}
        GROUP BY description, category
        ORDER BY total_spent DESC
        LIMIT ?
    """
    params.append(limit)
    with _conn() as conn:
        return pd.read_sql(query, conn, params=params)


def anomalies(z_threshold: float = 2.0, start_date: str = None, end_date: str = None) -> pd.DataFrame:
    """
    Flag transactions more than z_threshold std-devs above each category's mean.
    Catches unusual spend the way an ops analyst looks for data anomalies.
    """
    base_where = ["amount < 0", "category NOT IN ('Transfers', 'Income')"]
    params = []
    if start_date:
        base_where.append("transaction_date >= ?")
        params.append(start_date)
    if end_date:
        base_where.append("transaction_date <= ?")
        params.append(end_date)
    where_sql = " AND ".join(base_where)

    # Pull everything then compute z-score in pandas — SQLite doesn't have STDDEV
    query = f"""
        SELECT transaction_date, description, category, -amount AS amount
        FROM transactions
        WHERE {where_sql}
    """
    with _conn() as conn:
        df = pd.read_sql(query, conn, params=params)

    if df.empty:
        return df

    df["cat_mean"] = df.groupby("category")["amount"].transform("mean")
    df["cat_std"] = df.groupby("category")["amount"].transform("std")
    df["z_score"] = (df["amount"] - df["cat_mean"]) / df["cat_std"].replace(0, 1)
    anomalies_df = df[df["z_score"] > z_threshold].copy()
    anomalies_df["z_score"] = anomalies_df["z_score"].round(2)
    return anomalies_df[
        ["transaction_date", "description", "category", "amount", "z_score"]
    ].sort_values("z_score", ascending=False).reset_index(drop=True)


def headline_kpis(start_date: str = None, end_date: str = None) -> dict:
    """The four numbers that belong at the top of the dashboard."""
    summary = monthly_summary(start_date, end_date)
    if summary.empty:
        return {"total_income": 0, "total_spending": 0, "net_savings": 0, "avg_monthly_spend": 0}

    return {
        "total_income": round(summary["income"].sum(), 2),
        "total_spending": round(summary["spending"].sum(), 2),
        "net_savings": round(summary["net_cash_flow"].sum(), 2),
        "avg_monthly_spend": round(summary["spending"].mean(), 2),
    }


def date_bounds() -> tuple[str, str]:
    """Return (min_date, max_date) as ISO strings — used to set dashboard filters."""
    with _conn() as conn:
        cur = conn.execute("SELECT MIN(transaction_date), MAX(transaction_date) FROM transactions")
        return cur.fetchone()


if __name__ == "__main__":
    # Quick smoke test when run directly
    print("Date bounds:", date_bounds())
    print("\nHeadline KPIs:")
    for k, v in headline_kpis().items():
        print(f"  {k}: ${v:,.2f}")
    print("\nTop 5 spending categories:")
    print(spending_by_category().head())
    print("\nTop 5 merchants:")
    print(top_merchants(limit=5))
    print("\nAnomalies (top 5):")
    print(anomalies().head())
