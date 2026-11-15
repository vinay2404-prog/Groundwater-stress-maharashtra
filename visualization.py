"""Plotly visualization helpers for JALNETRA."""

from __future__ import annotations

from io import BytesIO

import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st

from config import COL_CATEGORY, COL_DISTRICT, COL_YEAR
from utils import metric_label
from ui_enhancements import PLOTLY_THEME


def category_metrics(df):
    if df.empty or COL_CATEGORY not in df.columns:
        return

    latest_year = int(df[COL_YEAR].max())
    latest = df[df[COL_YEAR] == latest_year]
    counts = latest[COL_CATEGORY].value_counts()

    c1, c2, c3, c4 = st.columns(4)

    with c1:
        st.metric("Safe", counts.get("Safe", 0))

    with c2:
        st.metric("Semi-Critical", counts.get("Semi-Critical", 0))

    with c3:
        st.metric("Critical", counts.get("Critical", 0))

    with c4:
        st.metric("Over-Exploited", counts.get("Over-Exploited", 0))


def trend_chart(df: pd.DataFrame, metrics: list[str], title: str):
    """Multi-metric year-wise trend chart."""

    if df.empty:
        return px.line(title=title)

    if COL_YEAR in df.columns:
        plot_df = (
            df.groupby(COL_YEAR, as_index=False)[metrics].mean().sort_values(COL_YEAR)
        )
        plot_df[COL_YEAR] = plot_df[COL_YEAR].astype(str)
        x_col = COL_YEAR
    else:
        plot_df = df.copy()
        x_col = plot_df.columns[0]

    fig = px.line(
        plot_df,
        x=x_col,
        y=metrics,
        markers=True,
        title=title,
    )

    fig.update_xaxes(type="category")
    fig.update_xaxes(
        type="category",
        title_font=dict(color="black", size=14),
        tickfont=dict(color="black", size=12),
    )

    fig.update_yaxes(
        title_font=dict(color="black", size=14), tickfont=dict(color="black", size=12)
    )

    fig.update_layout(**PLOTLY_THEME)
    fig.update_layout(
        paper_bgcolor="white",
        plot_bgcolor="white",
        font=dict(color="#111111"),
    )

    return fig


def download_buttons(df: pd.DataFrame, prefix: str) -> None:
    """Render CSV and Excel download buttons."""
    csv_data = df.to_csv(index=False).encode("utf-8")
    st.download_button(
        "Download CSV",
        csv_data,
        file_name=f"{prefix}.csv",
        mime="text/csv",
        key=f"{prefix}_csv",
    )

    buffer = BytesIO()
    df.to_excel(buffer, index=False, engine="openpyxl")
    st.download_button(
        "Download Excel",
        buffer.getvalue(),
        file_name=f"{prefix}.xlsx",
        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        key=f"{prefix}_xlsx",
    )


def category_pie(df: pd.DataFrame, title: str = "Groundwater Category Distribution"):
    return px.pie(df, names="Groundwater Category", title=title, hole=0.35)


def trend_line(
    df: pd.DataFrame,
    x: str,
    y: str | list[str],
    *,
    color: str | None = None,
    title: str,
):
    return px.line(df, x=x, y=y, color=color, markers=True, title=title)


def ranking_bar(
    df: pd.DataFrame, x: str, y: str, *, title: str, color: str | None = None
):
    return px.bar(df, x=x, y=y, color=color, title=title, text=y)


def comparison_chart(df: pd.DataFrame, x: str, y: str, color: str, title: str):
    return px.line(df, x=x, y=y, color=color, markers=True, title=title)


def recharge_extraction_bar(df: pd.DataFrame, x: str, title: str):
    return px.bar(
        df,
        x=x,
        y=["Annual Recharge (MCM)", "Total Extraction (MCM)"],
        barmode="group",
        title=title,
    )


def forecast_chart(
    historical_or_forecast: pd.DataFrame,
    forecast_or_entity,
    metric: str | None = None,
    entity: str | None = None,
):
    """Combined historical + forecast chart, or district forecast summary chart."""
    if isinstance(forecast_or_entity, str) and metric is None:
        return multi_metric_forecast_chart(historical_or_forecast, forecast_or_entity)

    hist = historical_or_forecast.copy()
    hist["Series"] = "Historical"
    fut = forecast_or_entity.copy()
    fut["Series"] = "Forecast"
    metric_col = metric or "Extraction Stage Numeric"
    entity_label = entity or "Forecast"

    combined = pd.concat(
        [
            hist[["Year", metric_col, "Series"]],
            fut[["Year", metric_col, "Series"]],
        ],
        ignore_index=True,
    )

    fig = px.line(
        combined,
        x="Year",
        y=metric_col,
        color="Series",
        markers=True,
        title=f"{entity_label} — {metric_label(metric_col)} Forecast",
    )

    fig.update_xaxes(
        type="category",
        title_font=dict(color="black", size=14),
        tickfont=dict(color="black", size=12),
    )

    fig.update_yaxes(
        title_font=dict(color="black", size=14), tickfont=dict(color="black", size=12)
    )
    fig.update_layout(**PLOTLY_THEME)
    fig.update_layout(
        paper_bgcolor="white",
        plot_bgcolor="white",
        font=dict(color="#111111"),
    )
    return fig


def multi_metric_forecast_chart(forecast: pd.DataFrame, entity: str):
    """Forecast chart for core groundwater metrics."""
    melted = forecast.melt(
        id_vars=["Year"],
        value_vars=[
            "Annual Recharge (MCM)",
            "Extractable Resource (MCM)",
            "Total Extraction (MCM)",
            "Extraction Stage Numeric",
        ],
        var_name="Metric",
        value_name="Value",
    )

    fig = px.line(
        melted,
        x="Year",
        y="Value",
        color="Metric",
        markers=True,
        title=f"{entity} — 2026-2030 Forecast",
    )
    fig.update_xaxes(type="category")
    fig.update_xaxes(
        type="category",
        title_font=dict(color="black", size=14),
        tickfont=dict(color="black", size=12),
    )

    fig.update_yaxes(
        title_font=dict(color="black", size=14), tickfont=dict(color="black", size=12)
    )
    fig.update_layout(**PLOTLY_THEME)
    fig.update_layout(
        paper_bgcolor="white",
        plot_bgcolor="white",
        font=dict(color="#111111"),
    )
    return fig


def risk_heatmap(risk_df: pd.DataFrame):
    """Bar chart of districts by predicted risk."""
    fig = px.bar(
        risk_df,
        x="District",
        y="Predicted Stage 2030",
        color="Risk Level",
        title="District Groundwater Risk Forecast (2030)",
        text="Predicted Stage 2030",
    )
    fig.update_traces(texttemplate="%{text:.1f}%", textposition="outside")
    fig.update_layout(**PLOTLY_THEME)
    fig.update_layout(
        paper_bgcolor="white",
        plot_bgcolor="white",
        font=dict(color="#111111"),
    )
    return fig


def scatter_recharge_extraction(
    df: pd.DataFrame, title: str = "Recharge vs Extraction"
):
    return px.scatter(
        df,
        x="Annual Recharge (MCM)",
        y="Total Extraction (MCM)",
        color="Groundwater Category",
        hover_data=["District", "Taluka", "Year"],
        title=title,
    )


def stage_gauge(stage: float, title: str = "Extraction Stage"):
    """Simple gauge chart for extraction stage."""
    fig = go.Figure(
        go.Indicator(
            mode="gauge+number",
            value=stage,
            title={"text": title},
            gauge={
                "axis": {"range": [0, 150]},
                "bar": {"color": "#0b84ff"},
                "steps": [
                    {"range": [0, 70], "color": "#d1fae5"},
                    {"range": [70, 90], "color": "#fef3c7"},
                    {"range": [90, 100], "color": "#fee2e2"},
                    {"range": [100, 150], "color": "#fecaca"},
                ],
            },
        )
    )
    fig.update_layout(
        paper_bgcolor="white",
        plot_bgcolor="white",
        font=dict(color="#111111"),
    )
    return fig


DISTRICT_COORDS = {
    "Ahmednagar": (19.09, 74.74),
    "Akola": (20.70, 77.00),
    "Amravati": (20.93, 77.75),
    "Beed": (18.99, 75.75),
    "Bhandara": (21.17, 79.65),
    "Buldhana": (20.53, 76.18),
    "Chandrapur": (19.97, 79.30),
    "Chh. Sambhajinagar": (19.88, 75.34),
    "Dharashiv": (18.18, 76.04),
    "Dhule": (20.90, 74.77),
    "Gadchiroli": (20.10, 80.00),
    "Gondia": (21.46, 80.20),
    "Hingoli": (19.72, 77.15),
    "Jalgaon": (21.01, 75.56),
    "Jalna": (19.84, 75.89),
    "Kolhapur": (16.70, 74.24),
    "Latur": (18.40, 76.56),
    "Mumbai City": (18.93, 72.83),
    "Mumbai Suburban": (19.08, 72.87),
    "Nagpur": (21.15, 79.09),
    "Nanded": (19.15, 77.32),
    "Nandurbar": (21.37, 74.24),
    "Nashik": (20.00, 73.79),
    "Palghar": (19.70, 72.77),
    "Parbhani": (19.27, 76.78),
    "Pune": (18.52, 73.86),
    "Raigad": (18.52, 73.18),
    "Ratnagiri": (16.99, 73.30),
    "Sangli": (16.85, 74.58),
    "Satara": (17.68, 74.00),
    "Sindhudurg": (16.35, 73.55),
    "Solapur": (17.66, 75.90),
    "Thane": (19.22, 72.98),
    "Wardha": (20.75, 78.60),
    "Washim": (20.11, 77.13),
    "Yavatmal": (20.40, 78.13),
}


