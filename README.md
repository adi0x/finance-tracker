# Personal Finance Analytics Dashboard

An end-to-end analytics project: raw bank CSV → Python ETL → SQLite database → interactive Streamlit dashboard.

Built to demonstrate the full analyst workflow that a business team would actually use — not just a notebook, not just a chart. The pipeline is reproducible, the SQL is auditable, and the dashboard answers real questions a user would ask about their spending.

---

## What it does

Point it at a bank transaction CSV and it gives you:

- **Monthly income vs spending** with net cash flow per month
- **Spending breakdown by category** — rule-based auto-categorization, no ML required
- **Category drill-down** — pick any category, see monthly trend and top merchants
- **Top 10 merchants** by total spend over the selected period
- **Anomaly detection** — flags transactions more than 2 standard deviations above each category's mean (the kind of check an ops analyst runs to catch data issues or unusual activity)
- **Date range filtering** so the whole dashboard reacts to the selected period

## Why this design

A few choices worth calling out:

**SQLite, not Pandas-only.** Pandas would have been faster to build, but real analytics stacks run on SQL databases. Storing the cleaned data in SQLite means queries are indexed, reusable across notebooks and apps, and the code mirrors what you'd do in Postgres or Snowflake at work.

**Rules before ML for categorization.** Mint, Copilot, and YNAB all use rule-based categorization as their baseline. Rules are interpretable — when a recruiter or user asks "why did this get categorized as Dining?" you can point at the line in `categorizer.py`. Shipping rules first is also how real ops analysts work: get a baseline that's debuggable, layer ML on only when the rules hit a ceiling.

**Queries separated from the UI.** All SQL lives in `src/queries.py` as small reusable functions. The dashboard just calls them. This is the pattern teams use once analytics grow past one-off scripts — it keeps the SQL auditable and lets you plug the same functions into notebooks, reports, or a new dashboard without rewriting anything.

**Data quality checks after every ETL run.** The ETL prints a report: total rows, uncategorized rate, date range, distinct categories. If uncategorized rate goes above 10%, it warns. Small detail, but the kind of thing that catches silent bugs in production pipelines.

## Stack

- **Python 3.10+** — ETL and app logic
- **SQLite** — indexed storage with real SQL
- **Streamlit** — dashboard framework
- **Plotly** — interactive charts
- **Pandas** — data manipulation inside queries

## Project structure

```
finance-tracker/
├── data/
│   ├── generate_data.py       # Realistic synthetic bank CSV generator
│   └── transactions.csv       # 1,215 transactions across 14 months
├── src/
│   ├── categorizer.py         # Rule-based category assignment + unit tests
│   ├── etl.py                 # CSV → cleaned → categorized → SQLite
│   └── queries.py             # Reusable SQL analytics queries
├── app.py                     # Streamlit dashboard
├── requirements.txt
└── README.md
```

## Getting started

```bash
# Install dependencies
pip install -r requirements.txt

# Generate synthetic data (1,200+ transactions over 14 months)
python data/generate_data.py

# Run the ETL — populates finance.db
python -m src.etl

# Launch the dashboard
streamlit run app.py
```

The dashboard opens at `http://localhost:8501`.

## About the data

The included dataset is **synthetic**, modeled on real US bank CSV export formats (Chase, Bank of America, Capital One). Synthetic was chosen over a public dataset because it:
- Avoids any PII concerns
- Is reproducible on any machine with one command
- Lets me control the distribution so category tests have enough samples

To run the dashboard on your own data, export a CSV from your bank with columns `Date, Description, Amount, Type`, drop it in `data/transactions.csv`, and rerun the ETL.

## What I learned building this

- SQLite's lack of `STDDEV` pushed me to compute z-scores in Pandas instead of pure SQL — a good reminder that the right tool depends on which stage of the pipeline you're in.
- Keyword ordering matters in rule-based categorization. `"DOORDASH*CHICK FIL A"` needs to hit the Dining rule before the catch-all Shopping rule, which means specificity-first rule ordering.
- Separating queries from UI pays off fast. Adding a new chart was a 3-line change because the SQL already existed.

## Built by

Adithi Koppula — [GitHub](https://github.com/adi0x) · [LinkedIn](https://www.linkedin.com/in/adithi-k-784990228/)
