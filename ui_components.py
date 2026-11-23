"""Reusable native Streamlit UI helpers for JALNETRA."""

from __future__ import annotations

import pandas as pd
import streamlit as st

from config import COL_DISTRICT, COL_YEAR


def section_header(title: str, description: str = "", icon: str = "💧"):
    st.markdown(f"## {icon} {title}")
    if description:
        st.caption(description)


def metric_card(label, value, delta=None, help_text=None):
    with st.container(border=True):
        st.metric(
            label=label,
            value=value,
            delta=delta,
            help=help_text,
            border=False,
        )


def info_panel(title, content, icon="ℹ️"):
    with st.container(border=True):
        st.markdown(f"**{icon} {title}**")
        st.write(content)


def page_footer():
    st.divider()
    st.caption(
        "JALNETRA · Maharashtra Groundwater Intelligence Platform"
        " · Academic & Research Project"
    )


def empty_state(message, suggestion=None):
    with st.container(border=True):
        st.info(message)
        if suggestion:
            st.caption(suggestion)


def dataframe_panel(df, title="Dataset Preview"):
    with st.container(border=True):
        st.subheader(title)
        st.caption(f"{len(df):,} records available")
        st.dataframe(
            df,
            use_container_width=True,
            hide_index=True,
            height=400,
        )


def apply_global_filters(df):
    selected = st.session_state.get("global_districts", [])
    year_range = st.session_state.get("global_year_range")

    if selected:
        df = df[df[COL_DISTRICT].isin(selected)]

    if year_range:
        df = df[
            (df[COL_YEAR] >= year_range[0])
            & (df[COL_YEAR] <= year_range[1])
        ]

    return df.copy()