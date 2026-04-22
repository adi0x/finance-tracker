"""
Personal Finance Analytics Dashboard.

Built on top of the SQLite database populated by src/etl.py.
All analytical logic lives in src/queries.py — this file is just the UI.
"""
import streamlit as st
import pandas as pd
import plotly.express as px
from datetime import date

from src import queries


st.set_page_config(
    page_title="Personal Finance Analytics",
    page_icon="💰",
    layout="wide",
    initial_sidebar_state="expanded",
)


# ── Minimal custom styling — keep it clean, not flashy ─────────────────────
st.markdown("""
<style>
    .main .block-container {padding-top: 2rem;}
    div[data-testid="stMetricValue"] {font-size: 1.7rem;}
    div[data-testid="stMetricLabel"] {font-size: 0.85rem; color: #6b7280;}
    h1 {letter-spacing: -0.02em;}
    .stPlotlyChart {background: white; border-radius: 4px;}
</style>
""", unsafe_allow_html=True)


# ── Header ─────────────────────────────────────────────────────────────────
st.title("Personal Finance Analytics")
st.caption("ETL pipeline → SQLite → Interactive dashboard. Built with Python, SQL, Streamlit, and Plotly.")


# ── Sidebar filters ────────────────────────────────────────────────────────
min_date_str, max_date_str = queries.date_bounds()
min_date = date.fromisoformat(min_date_str)
max_date = date.fromisoformat(max_date_str)

with st.sidebar:
    st.header("Filters")
    start_date = st.date_input("Start date", min_date, min_value=min_date, max_value=max_date)
    end_date = st.date_input("End date", max_date, min_value=min_date, max_value=max_date)

    st.divider()
    st.caption("**About this project**")
    st.caption(
        "Synthetic bank data modeled on real US bank export formats. "
        "Demonstrates end-to-end analytics: raw CSV, Python ETL, SQLite database "
        "with indexed queries, rule-based categorization, and an interactive dashboard."
    )
    st.caption("Code: [github.com/adi0x/finance-tracker](https://github.com)")


start_str = start_date.isoformat()
end_str = end_date.isoformat()


# ── KPI row ────────────────────────────────────────────────────────────────
kpis = queries.headline_kpis(start_str, end_str)

col1, col2, col3, col4 = st.columns(4)
col1.metric("Total Income", f"${kpis['total_income']:,.0f}")
col2.metric("Total Spending", f"${kpis['total_spending']:,.0f}")

net_color = "normal" if kpis["net_savings"] >= 0 else "inverse"
col3.metric(
    "Net Savings",
    f"${kpis['net_savings']:,.0f}",
    delta=f"{'Positive' if kpis['net_savings'] >= 0 else 'Overspending'}",
    delta_color=net_color,
)
col4.metric("Avg Monthly Spend", f"${kpis['avg_monthly_spend']:,.0f}")

st.divider()


# ── Row: monthly trend + category breakdown ────────────────────────────────
left, right = st.columns([3, 2])

with left:
    st.subheader("Income vs Spending — Monthly")
    monthly = queries.monthly_summary(start_str, end_str)

    if not monthly.empty:
        fig = px.bar(
            monthly,
            x="month_label",
            y=["income", "spending"],
            barmode="group",
            labels={"month_label": "Month", "value": "Amount ($)", "variable": ""},
            color_discrete_map={"income": "#10b981", "spending": "#ef4444"},
        )
        fig.update_layout(
            margin=dict(l=0, r=0, t=10, b=0),
            legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
            plot_bgcolor="white",
            height=340,
        )
        fig.update_xaxes(showgrid=False)
        fig.update_yaxes(gridcolor="#f3f4f6")
        st.plotly_chart(fig, use_container_width=True)
    else:
        st.info("No data in this range.")

with right:
    st.subheader("Spending by Category")
    cats = queries.spending_by_category(start_str, end_str)

    if not cats.empty:
        fig = px.pie(
            cats,
            names="category",
            values="total_spent",
            hole=0.55,
        )
        fig.update_layout(
            margin=dict(l=0, r=0, t=10, b=0),
            height=340,
            showlegend=True,
            legend=dict(orientation="v", yanchor="middle", y=0.5, xanchor="left", x=1.0),
        )
        fig.update_traces(textposition="inside", textinfo="percent")
        st.plotly_chart(fig, use_container_width=True)
    else:
        st.info("No spending in this range.")


# ── Row: category drill-down ──────────────────────────────────────────────
st.subheader("Category Drill-Down")

category_choices = cats["category"].tolist() if not cats.empty else []
if category_choices:
    selected = st.selectbox("Pick a category to see monthly trend", category_choices)
    trend = queries.category_trend(selected, start_str, end_str)

    if not trend.empty:
        c1, c2 = st.columns([3, 1])
        with c1:
            fig = px.line(
                trend,
                x="month_label",
                y="spent",
                markers=True,
                labels={"month_label": "Month", "spent": "Spent ($)"},
            )
            fig.update_traces(line_color="#6366f1", line_width=3, marker_size=8)
            fig.update_layout(
                margin=dict(l=0, r=0, t=10, b=0),
                plot_bgcolor="white",
                height=280,
            )
            fig.update_xaxes(showgrid=False)
            fig.update_yaxes(gridcolor="#f3f4f6")
            st.plotly_chart(fig, use_container_width=True)

        with c2:
            st.metric("Months tracked", len(trend))
            st.metric("Total spent", f"${trend['spent'].sum():,.0f}")
            st.metric("Avg per month", f"${trend['spent'].mean():,.0f}")
            st.metric("Peak month", trend.loc[trend["spent"].idxmax(), "month_label"])


st.divider()


# ── Row: top merchants + anomalies ─────────────────────────────────────────
left, right = st.columns(2)

with left:
    st.subheader("Top 10 Merchants")
    merchants = queries.top_merchants(start_str, end_str, limit=10)
    if not merchants.empty:
        st.dataframe(
            merchants.rename(columns={
                "merchant": "Merchant",
                "category": "Category",
                "visits": "Visits",
                "total_spent": "Total Spent ($)",
            }),
            use_container_width=True,
            hide_index=True,
        )

with right:
    st.subheader("Flagged Anomalies")
    st.caption("Transactions > 2 std-devs above their category average.")
    anomalies_df = queries.anomalies(z_threshold=2.0, start_date=start_str, end_date=end_str)
    if not anomalies_df.empty:
        st.dataframe(
            anomalies_df.rename(columns={
                "transaction_date": "Date",
                "description": "Description",
                "category": "Category",
                "amount": "Amount ($)",
                "z_score": "Z-Score",
            }),
            use_container_width=True,
            hide_index=True,
        )
    else:
        st.info("No anomalies detected in this range.")


# ── Footer ─────────────────────────────────────────────────────────────────
st.divider()
st.caption(
    "Built by Adithi Koppula · "
    "Python · SQLite · Streamlit · Plotly · "
    "[GitHub](https://github.com/adi0x/finance-tracker)"
)
