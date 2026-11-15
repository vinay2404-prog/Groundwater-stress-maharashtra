from __future__ import annotations

import logging
from pathlib import Path

import plotly.express as px
import pandas as pd
import streamlit as st

from analytics import DataQueryEngine
from chatbot import chatbot_ui
from config import (
    APP_NAME,
    COL_CATEGORY,
    COL_DISTRICT,
    COL_TALUKA,
    COL_YEAR,
)
from data_loader import get_data_summary, load_master_dataframe
from forecasting import forecast_district
from page_modules.reports import generate_report
from utils import copy_df
from visualization import (
    category_metrics,
    download_buttons,
    forecast_chart,
    trend_chart,
)
from map_view import district_map
from ui_enhancements import PLOTLY_THEME

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

st.set_page_config(
    page_title=APP_NAME,
    page_icon="💧",
    layout="wide",
    initial_sidebar_state="collapsed",
)
if "page" not in st.session_state:
    st.session_state.page = "dashboard"
# (HTML/CSS removed for pure Streamlit)

def init_state() -> None:
    defaults = {
        "page": "dashboard",
    }
    for key, value in defaults.items():
        st.session_state.setdefault(key, value)


def navigate(page: str) -> None:
    st.session_state.page = page
    st.rerun()


# ── Public pages ───────────────────────────────────────────────────────────


def home_page() -> None:
    st.title("💧 JALNETRA")
    st.subheader("Smart Groundwater Monitoring & Forecasting System")
    st.caption(
        "AI-Driven Virtual Assistant for INGRES — intelligent groundwater resource "
        "management powered by XGBoost ML, RAG-based AI, and real-time analytics "
        "across Maharashtra's districts and talukas."
    )
    c1, c2, c3, c4 = st.columns([2.5, 1.1, 1.1, 2.5])
    with c2:
        if st.button("Get Started", use_container_width=True):
            navigate("dashboard")
    with c3:
        if st.button("Sign In", use_container_width=True):
            navigate("dashboard")

    st.subheader("Powerful Features")
    features = [
        ("🤖", "AI ChatBot", "Data-grounded RAG chatbot with conversation memory and ML forecasting."),
        ("📊", "Interactive Visualizations", "Dynamic Plotly charts for trends, rankings, and comparisons."),
        ("🔮", "Future Predictions", "XGBoost-powered forecasts with confidence scores."),
        ("🗄️", "Data Explorer", "Auto-loaded CSV/Excel datasets with validation and cleaning."),
        ("🌐", "Multilingual Support", "English, Hindi, and Marathi query understanding."),
        ("📥", "Export Center", "Download CSV, Excel, and PDF reports."),
    ]
    for row in range(0, len(features), 3):
        cols = st.columns(3)
        for col, (icon, title, text) in zip(cols, features[row : row + 3]):
            with col:
                st.container(border=True)
                st.markdown(f"### {icon} {title}")
                st.write(text)

    st.info(
        "Powered by AI & Machine Learning — JALNETRA combines XGBoost forecasting, "
        "RAG-based retrieval, NLP query understanding, and Plotly analytics into a "
        "unified groundwater intelligence platform."
    )


def topbar():
    st.subheader("💧 JALNETRA")


def sidebar_navigation() -> str:
    st.sidebar.markdown("## 💧 JALNETRA")
    menu = st.sidebar.radio(
        "Navigation",
        [
            "Dashboard",
            "Groundwater Overview",
            "District Analysis",
            "Taluka Analysis",
            "Trend Analysis",
            "Future Prediction",
            "AI ChatBot",
            "District Map",
            "Problem Insights",
            "Data Explorer",
            "Download Center",
            "Assessments",
            "Query History",
        ],
        label_visibility="collapsed",
    )
    st.sidebar.divider()
    summary = get_data_summary(load_master_dataframe())

    return menu


# ── Dashboard pages ────────────────────────────────────────────────────────


def dashboard_page(df: pd.DataFrame) -> None:
    st.title("Groundwater Intelligence Dashboard")
    st.caption("Welcome to JALNETRA – your AI-powered groundwater data assistant")
    category_metrics(df)
    summary = get_data_summary(df)
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Total Records", f"{summary['records']:,}")
    c2.metric("Districts", summary["districts"])
    c3.metric("Talukas", summary["talukas"])
    c4.metric("Years", f"{min(summary['years'])}–{max(summary['years'])}")
    st.info(
        "Use **AI ChatBot** for natural language queries or explore dedicated analysis pages from the sidebar."
    )


def overview_page(df: pd.DataFrame) -> None:
    st.title("🌊 Groundwater Overview")
    st.caption("Statewide groundwater insights")
    engine = DataQueryEngine(df)
    result = engine.state_summary()
    st.markdown(result.answer)
    latest_year = int(df[COL_YEAR].max())
    year_df = df[df[COL_YEAR] == latest_year]
    fig = px.pie(
        year_df, names=COL_CATEGORY, title=f"Category Distribution ({latest_year})"
    )
    fig.update_layout(**PLOTLY_THEME)
    st.plotly_chart(fig, use_container_width=True)
    fig2 = px.bar(
        year_df.groupby(COL_DISTRICT, as_index=False)["Extraction Stage Numeric"]
        .mean()
        .sort_values("Extraction Stage Numeric", ascending=False)
        .head(15),
        x=COL_DISTRICT,
        y="Extraction Stage Numeric",
        title="Top 15 Districts by Extraction Stage",
    )
    fig2.update_layout(**PLOTLY_THEME)
    st.plotly_chart(fig2, use_container_width=True)


def district_analysis_page(df: pd.DataFrame) -> None:
    st.title("District Analysis")
    districts = sorted(df[COL_DISTRICT].dropna().unique())
    district = st.selectbox("Select District", districts)
    year = st.selectbox(
        "Year", ["Latest"] + sorted(df[COL_YEAR].unique(), reverse=True)
    )
    yr = None if year == "Latest" else int(year)
    engine = DataQueryEngine(df)
    result = engine.district_summary(district, year=yr)
    st.markdown(result.answer)
    if result.data is not None:
        st.plotly_chart(
            trend_chart(
                result.data,
                ["Annual Recharge (MCM)", "Total Extraction (MCM)"],
                f"{district} Trends",
            ),
            use_container_width=True,
        )
        display_df = result.data.tail(15).copy()

        if "Year" in display_df.columns:
            display_df["Year"] = display_df["Year"].astype(str)

        st.dataframe(display_df, use_container_width=True, hide_index=True)


def taluka_analysis_page(df: pd.DataFrame) -> None:
    st.title("Taluka Analysis")
    districts = sorted(df[COL_DISTRICT].dropna().unique())
    district = st.selectbox("District", districts, key="tal_district")
    talukas = sorted(df[df[COL_DISTRICT] == district][COL_TALUKA].dropna().unique())
    taluka = st.selectbox("Taluka", talukas)
    engine = DataQueryEngine(df)
    result = engine.taluka_summary(taluka)
    st.markdown(result.answer)
    if result.data is not None:
        st.plotly_chart(
            trend_chart(
                result.data, ["Extraction Stage Numeric"], f"{taluka} Extraction Stage"
            ),
            use_container_width=True,
        )


def trend_analysis_page(df: pd.DataFrame) -> None:
    st.title("Trend Analysis")
    c1, c2, c3 = st.columns(3)
    with c1:
        district = st.selectbox("District", ["All"] + sorted(df[COL_DISTRICT].unique()))
    with c2:
        metric = st.selectbox(
            "Metric",
            [
                "Annual Recharge (MCM)",
                "Total Extraction (MCM)",
                "Extraction Stage Numeric",
            ],
        )
    with c3:
        y_from, y_to = st.slider(
            "Year Range", int(df[COL_YEAR].min()), int(df[COL_YEAR].max()), (2021, 2025)
        )
    filtered = copy_df(df)
    if district != "All":
        filtered = filtered[filtered[COL_DISTRICT] == district]
    filtered = filtered[(filtered[COL_YEAR] >= y_from) & (filtered[COL_YEAR] <= y_to)]
    engine = DataQueryEngine(filtered)
    result = engine.trend(
        metric_col=metric,
        district=None if district == "All" else district,
        year_from=y_from,
        year_to=y_to,
    )
    st.markdown(result.answer)
    if result.data is not None:
        st.plotly_chart(
            trend_chart(filtered, [metric], f"Trend: {metric}"),
            use_container_width=True,
        )


def prediction_page(df: pd.DataFrame) -> None:
    st.title("Future Prediction Center")
    st.caption(
        "AI-generated forecasts using XGBoost ML models and historical trend analysis"
    )
    districts = sorted(df[COL_DISTRICT].dropna().unique())
    district = st.selectbox("District", districts, key="pred_district")
    horizon = st.slider("Forecast Horizon (years)", 1, 10, 5)
    if st.button("Generate Forecast", type="primary"):
        fc = forecast_district(df, district, horizon=horizon)
        if fc.empty:
            st.error("No data available for forecasting.")
            return
        st.warning(
            "⚠️ Results below are **AI-generated predictions**, not observed data."
        )
        display_df = fc.copy()

        if "Year" in display_df.columns:
            display_df["Year"] = display_df["Year"].astype(str)

        st.dataframe(display_df, use_container_width=True, hide_index=True)
        st.plotly_chart(forecast_chart(fc, district), use_container_width=True)
        last = fc.iloc[-1]
        c1, c2, c3 = st.columns(3)
        c1.metric("Predicted Extraction Stage", f"{last['Predicted Stage']:.1f}%")
        c2.metric("Groundwater Category", last["Predicted Category"])
        c3.metric("Model Confidence", f"{last['Confidence Score']:.1f}%")
        download_buttons(fc, f"forecast_{district}")


def data_explorer_page(df: pd.DataFrame) -> None:
    st.title("Data Explorer")
    c1, c2, c3 = st.columns(3)
    with c1:
        d = st.selectbox(
            "District", ["All"] + sorted(df[COL_DISTRICT].unique()), key="exp_d"
        )
    with c2:
        t = st.selectbox(
            "Taluka", ["All"] + sorted(df[COL_TALUKA].unique()), key="exp_t"
        )
    with c3:
        y = st.selectbox(
            "Year", ["All"] + sorted(df[COL_YEAR].unique(), reverse=True), key="exp_y"
        )
    filtered = copy_df(df)
    if d != "All":
        filtered = filtered[filtered[COL_DISTRICT] == d]
    if t != "All":
        filtered = filtered[filtered[COL_TALUKA] == t]
    if y != "All":
        filtered = filtered[filtered[COL_YEAR] == int(y)]
    st.metric("Matching Records", len(filtered))
    display_df = filtered.copy()

    if "Year" in display_df.columns:
        display_df["Year"] = display_df["Year"].astype(str)

    st.dataframe(display_df, use_container_width=True, hide_index=True)


def download_center_page(df: pd.DataFrame) -> None:
    st.title("Download Center")
    st.subheader("Export Dataset")
    download_buttons(df, "jalnetra_groundwater")
    st.subheader("Generate PDF Report")
    districts = sorted(df[COL_DISTRICT].unique())
    district = st.selectbox("District for PDF", districts, key="pdf_d")
    latest = df[df[COL_DISTRICT] == district].sort_values(COL_YEAR).iloc[-1]
    stage = latest.get(
        "Extraction Stage Numeric", latest.get("Extraction Stage (%)", 0)
    )
    if st.button("Generate PDF"):
        path = Path("exports") / f"report_{district}.pdf"
        path.parent.mkdir(exist_ok=True)
        result = generate_report(str(path), district, stage, latest[COL_CATEGORY])
        if result:
            with path.open("rb") as f:
                st.download_button(
                    "Download PDF Report",
                    f,
                    file_name=path.name,
                    mime="application/pdf",
                )
            st.success("Report generated.")
        else:
            st.error("Report generation failed.")


def assessments_page(df: pd.DataFrame) -> None:
    st.title("Assessment Units")
    search = st.text_input("Search by district, taluka, category, or year")
    category = st.selectbox(
        "Category", ["All", "Safe", "Semi-Critical", "Critical", "Over-Exploited"]
    )
    filtered = copy_df(df)
    if search:
        mask = filtered.astype(str).apply(
            lambda r: r.str.contains(search, case=False, na=False).any(), axis=1
        )
        filtered = filtered[mask]
    if category != "All":
        filtered = filtered[filtered[COL_CATEGORY] == category]
    cols = [
        COL_DISTRICT,
        COL_TALUKA,
        COL_YEAR,
        "Pre-Monsoon Level (mbgl)",
        "Post-Monsoon Level (mbgl)",
        "Annual Recharge (MCM)",
        "Extractable Resource (MCM)",
        "Total Extraction (MCM)",
        "Extraction Stage (%)",
        COL_CATEGORY,
    ]
    display_df = filtered[cols].copy()

    if "Year" in display_df.columns:
        display_df["Year"] = display_df["Year"].astype(str)

    st.dataframe(display_df, use_container_width=True, hide_index=True)


def query_history_page(df=None):
    if st.button("Clear History"):
        st.session_state.messages = []
        if "chat_memory" in st.session_state:
            st.session_state.chat_memory.history = []
        st.rerun()
    st.title("Query History")
    # The chat page owns this key, so it may not exist yet on a fresh session.
    messages = st.session_state.get("messages", [])
    if not messages:
        st.info("No query history yet.")
        return
    for msg in messages:
        label = "User" if msg["role"] == "user" else APP_NAME
        st.markdown(f"### {label}\n\n{msg['content']}")
        st.divider()


def district_map_page(df: pd.DataFrame) -> None:
    st.title("District Map")
    st.caption("Interactive map of groundwater districts")
    district_map(df)


def problem_insights_page(df: pd.DataFrame) -> None:
    st.title("Problem Insights")
    st.caption("Key groundwater problems identified from the data")

    # Heatmap: extraction stage by district and year
    pivot = df.pivot_table(
        index=COL_DISTRICT, columns=COL_YEAR, values="Extraction Stage Numeric", aggfunc="mean"
    )
    if not pivot.empty:
        st.subheader("Extraction Stage Heatmap (District vs Year)")
        st.caption(
            "Shows which districts have worsening extraction over time. Darker red cells "
            "indicate districts approaching or exceeding sustainable extraction levels."
        )
        fig = px.imshow(
            pivot,
            labels=dict(x="Year", y="District", color="Stage %"),
            title="District-wise Extraction Stage Over Years",
            aspect="auto",
            color_continuous_scale="RdYlGn_r",
        )
        fig.update_layout(height=700)
        st.plotly_chart(fig, use_container_width=True)

    # Top districts where extraction exceeds recharge
    latest_year = int(df[COL_YEAR].max())
    latest = df[df[COL_YEAR] == latest_year].copy()
    latest["Gap (MCM)"] = latest["Total Extraction (MCM)"] - latest["Annual Recharge (MCM)"]
    gap_df = (
        latest.groupby(COL_DISTRICT, as_index=False)["Gap (MCM)"].mean()
        .sort_values("Gap (MCM)", ascending=False)
        .head(10)
    )
    if not gap_df.empty:
        st.subheader("Top 10 Districts: Extraction − Recharge Gap")
        st.caption(
            "Highlights districts where groundwater extraction exceeds annual recharge, "
            "indicating unsustainable usage and potential depletion."
        )
        fig2 = px.bar(
            gap_df,
            x=COL_DISTRICT,
            y="Gap (MCM)",
            title="Over-Extraction Gap (Latest Year)",
            color="Gap (MCM)",
            color_continuous_scale="Reds",
        )
        st.plotly_chart(fig2, use_container_width=True)

    # Category trend over years
    cat_trend = (
        df.groupby([COL_YEAR, COL_CATEGORY]).size().reset_index(name="Count")
    )
    if not cat_trend.empty:
        st.subheader("Groundwater Category Trend Over Years")
        st.caption(
            "Tracks how many assessment units fall into Safe, Semi-Critical, Critical, "
            "and Over-Exploited categories each year, revealing overall resource health."
        )
        fig3 = px.bar(
            cat_trend,
            x=COL_YEAR,
            y="Count",
            color=COL_CATEGORY,
            title="Category Counts by Year",
            barmode="stack",
        )
        st.plotly_chart(fig3, use_container_width=True)


def app_dashboard() -> None:
    df = load_master_dataframe()
    topbar()
    menu = sidebar_navigation()
    pages = {
        "Dashboard": dashboard_page,
        "Groundwater Overview": overview_page,
        "District Analysis": district_analysis_page,
        "Taluka Analysis": taluka_analysis_page,
        "Trend Analysis": trend_analysis_page,
        "Future Prediction": prediction_page,
        "AI ChatBot": lambda d: (st.title("AI Groundwater Assistant"), chatbot_ui(d)),
        "District Map": district_map_page,
        "Problem Insights": problem_insights_page,
        "Data Explorer": data_explorer_page,
        "Download Center": download_center_page,
        "Assessments": assessments_page,
        "Query History": query_history_page,
    }
    handler = pages.get(menu, dashboard_page)
    handler(df)


def main() -> None:
    init_state()
    if st.session_state.page == "home":
        home_page()
    elif st.session_state.page == "dashboard":
        app_dashboard()
    else:
        navigate("home")


if __name__ == "__main__":
    main()
