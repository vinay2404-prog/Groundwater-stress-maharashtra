
from __future__ import annotations

import logging
import re
from pathlib import Path

import pandas as pd
import plotly.express as px
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
from forecasting import evaluate_forecasting, forecast_district
from map_view import district_map
from page_modules.reports import generate_report
from ui_components import (
    apply_global_filters,
    dataframe_panel,
    empty_state,
    metric_card,
    page_footer,
    section_header,
)
from ui_enhancements import PLOTLY_THEME
from utils import copy_df
from visualization import (
    category_metrics,
    download_buttons,
    forecast_chart,
    trend_chart,
)

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

BASE_DIR = Path(__file__).resolve().parent
LITERATURE_FILE = BASE_DIR / "LITERATURE_REVIEW.md"

st.set_page_config(
    page_title="JALNETRA | Groundwater Intelligence",
    page_icon="💧",
    layout="wide",
    initial_sidebar_state="expanded",
)


# ============================================================
# APPLICATION STATE AND NAVIGATION
# ============================================================

def init_state() -> None:
    defaults = {
        "main_navigation": "Home",
        "global_districts": [],
    }

    for key, value in defaults.items():
        st.session_state.setdefault(key, value)


def navigate(page: str) -> None:
    st.session_state["main_navigation"] = page
    st.rerun()


def topbar() -> None:
    st.subheader("💧 JALNETRA")


def get_available_years(df: pd.DataFrame) -> list[int]:
    if COL_YEAR not in df.columns:
        return []

    years = pd.to_numeric(df[COL_YEAR], errors="coerce").dropna()

    return sorted(years.astype(int).unique().tolist())


def read_literature_review() -> str:
    if not LITERATURE_FILE.exists():
        return (
            "Literature review file not found. "
            "Please place LITERATURE_REVIEW.md in the project root."
        )

    try:
        return LITERATURE_FILE.read_text(encoding="utf-8")
    except OSError:
        logger.exception("Could not read literature review.")
        return "Unable to read the literature review file."


def extract_references(markdown_text: str) -> str:
    """Extract the References section from the literature review."""

    match = re.search(
        r"(?im)^#{1,3}\s*(?:\d+[\.\)]?\s*)?References\s*$",
        markdown_text,
    )

    if not match:
        return "No References heading was found in LITERATURE_REVIEW.md."

    return markdown_text[match.end():].strip()


# ============================================================
# HOME PAGE
# ============================================================

def home_page() -> None:

    st.title("💧 JALNETRA")

    st.subheader(
        "Maharashtra Groundwater Intelligence "
        "& Decision Support Platform"
    )

    st.caption(
        "Understanding groundwater. Identifying risks. "
        "Supporting sustainable water management."
    )

    st.divider()

    with st.container(border=True):

        st.markdown("### Explore Maharashtra's Groundwater")

        st.write(
            "JALNETRA transforms groundwater assessment datasets "
            "into interactive insights, regional comparisons and "
            "historical analysis to support a better understanding "
            "of groundwater conditions across Maharashtra."
        )

        c1, c2 = st.columns(2)

        with c1:
            if st.button(
                "📊 Explore Dashboard",
                type="primary",
                use_container_width=True,
            ):
                navigate("State Dashboard")

        with c2:
            if st.button(
                "🗺️ Explore Districts",
                use_container_width=True,
            ):
                navigate("Regional Explorer")

    st.divider()

    section_header(
        "Platform Capabilities",
        "Explore the major analytical modules available in JALNETRA.",
    )

    capabilities = [
        (
            "💧 Groundwater Assessment",
            "Explore annual recharge, extractable resources, "
            "total extraction and extraction stages.",
        ),
        (
            "🗺️ Regional Intelligence",
            "Explore district and taluka-level groundwater "
            "conditions wherever data is available.",
        ),
        (
            "📈 Historical Analysis",
            "Understand historical groundwater-level "
            "variations and resource trends.",
        ),
        (
            "⚠️ Stress Identification",
            "Explore groundwater assessment categories "
            "and regional stress patterns.",
        ),
        (
            "🤖 AI Groundwater Assistant",
            "Ask natural-language questions about the "
            "available groundwater dataset.",
        ),
        (
            "📑 Research & Reporting",
            "Inspect underlying records and export "
            "datasets and district reports.",
        ),
    ]

    for start in range(0, len(capabilities), 2):

        left, right = st.columns(2)

        for col, item in zip(
            [left, right],
            capabilities[start:start + 2],
        ):
            with col:
                with st.container(border=True):
                    st.markdown(f"### {item[0]}")
                    st.write(item[1])

    st.divider()

    section_header(
        "How JALNETRA Works",
        "From structured datasets to analytical insights.",
    )

    steps = [
        ("01", "Data Collection", "Organize groundwater datasets."),
        ("02", "Data Processing", "Clean and structure available records."),
        ("03", "Analysis", "Calculate and examine groundwater indicators."),
        ("04", "Visualization", "Present findings through interactive charts."),
        ("05", "Insight Discovery", "Explore regional and historical patterns."),
    ]

    for number, title, description in steps:
        with st.container(border=True):
            st.markdown(f"**{number} · {title}**")
            st.caption(description)

    with st.expander("Data Sources & Methodology"):
        st.write(
            "JALNETRA uses available structured groundwater resource "
            "assessment datasets and supporting information. Data coverage, "
            "reporting periods, measurement definitions and geographic "
            "resolution may vary between datasets."
        )

    with st.expander("Who Can Use JALNETRA?"):
        st.markdown(
            """
            - Researchers and academic institutions
            - Students and environmental science enthusiasts
            - Water resource planners
            - Government and policy analysts
            - Data analysts and geospatial researchers
            """
        )

    with st.expander("Important Disclaimer"):
        st.warning(
            "JALNETRA is an independent academic and data visualization "
            "project. Its results are based on available datasets and "
            "implemented analytical methods. They are not official "
            "government recommendations or real-time measurements."
        )

    page_footer()


# ============================================================
# SIDEBAR NAVIGATION AND GLOBAL FILTERS
# ============================================================

def sidebar_navigation(df: pd.DataFrame) -> str:

    st.sidebar.markdown("# 💧 JALNETRA")
    st.sidebar.caption("Groundwater Intelligence Platform")
    st.sidebar.divider()

    menu_options = [
        "Home",
        "State Dashboard",
        "Regional Explorer",
        "Historical Analysis",
        "Forecasting & Risk",
        "AI Assistant",
        "Data & Reports",
        "About JALNETRA",
    ]

    current_page = st.session_state.get("main_navigation", "Home")

    if current_page not in menu_options:
        current_page = "Home"

    with st.sidebar:

        st.markdown("### Navigation")

        menu = st.radio(
            "Explore Platform",
            menu_options,
            index=menu_options.index(current_page),
            label_visibility="collapsed",
            key="main_navigation",
        )

        st.divider()

        with st.expander("Global Filters", expanded=True):

            districts = (
                sorted(df[COL_DISTRICT].dropna().unique().tolist())
                if COL_DISTRICT in df.columns
                else []
            )

            st.multiselect(
                "Select Districts",
                districts,
                default=[],
                key="global_districts",
            )

            years = get_available_years(df)

            if years:
                default_range = (min(years), max(years))

                st.slider(
                    "Assessment Year",
                    min_value=min(years),
                    max_value=max(years),
                    value=default_range,
                    key="global_year_range",
                )

            if st.button(
                "Reset Filters",
                use_container_width=True,
            ):
                st.session_state["global_districts"] = []

                if years:
                    st.session_state["global_year_range"] = (
                        min(years),
                        max(years),
                    )

                st.rerun()

        st.divider()

        summary = get_data_summary(df)

        with st.container(border=True):
            st.markdown("**Dataset Coverage**")
            st.metric("Records", f"{summary['records']:,}")
            st.metric("Districts", summary["districts"])
            st.metric("Talukas", summary["talukas"])

        st.divider()

        st.caption(
            "Data-driven insights for sustainable groundwater management."
        )

    return menu


# ============================================================
# GROUNDWATER RESOURCES AND CLASSIFICATION GUIDE
# ============================================================

def render_groundwater_classification_guide(
    show_section_number: bool = False,
) -> None:
    """Explain groundwater resources and assessment categories."""

    heading = (
        "11. Groundwater Resources & Assessment Classification"
        if show_section_number
        else "Understanding Groundwater Resources & Assessment Categories"
    )

    st.subheader(heading)

    st.markdown(
        "Understand how groundwater is replenished, how much resource is "
        "available for extraction, how much is being used, and how "
        "groundwater assessment categories are determined."
    )

    st.markdown("### Understanding Groundwater Resources")

    with st.expander("1. Annual Groundwater Recharge", expanded=True):

        st.markdown(
            """
            **What it means**

            The estimated quantity of water replenished into underground
            aquifers during a year.

            **Main sources of recharge**

            - Rainfall infiltration during monsoon and non-monsoon periods.
            - Seepage from rivers, canals, tanks and ponds.
            - Return flow from irrigation.
            - Water conservation and recharge structures.

            **Why it matters**

            It indicates how much groundwater is replenished through
            natural and other recharge processes.
            """
        )

    with st.expander("2. Annual Extractable Groundwater Resource"):

        st.markdown(
            """
            **What it means**

            The estimated quantity of groundwater available for extraction
            during a year after accounting for annual natural discharge.

            **Simplified relationship**

            Annual Extractable Groundwater Resource =
            Total Annual Groundwater Recharge − Total Annual Natural Discharge

            **Why it matters**

            It provides the resource base against which annual groundwater
            extraction is compared.
            """
        )

    with st.expander("3. Total Annual Groundwater Extraction"):

        st.markdown(
            """
            **What it means**

            The estimated quantity of groundwater withdrawn during a year
            for different uses.

            **Main uses**

            - Irrigation: agricultural activities.
            - Domestic: household and drinking water requirements.
            - Industrial: industrial activities.

            **Why it matters**

            It indicates the pressure that human groundwater use places
            on available groundwater resources.
            """
        )

    with st.expander("4. Stage of Groundwater Extraction"):

        st.markdown(
            """
            **What it means**

            The percentage of the annual extractable groundwater resource
            being used through groundwater extraction.
            """
        )

        st.latex(
            r"\text{Extraction Stage (\%)} = "
            r"\frac{\text{Total Annual Groundwater Extraction}}"
            r"{\text{Annual Extractable Groundwater Resource}}"
            r"\times 100"
        )

    st.divider()

    st.markdown("### Worked Example")

    st.caption(
        "Illustrative figures, not actual district measurements."
    )

    col1, col2 = st.columns(2)

    with col1:
        st.metric("Annual Groundwater Recharge", "1,000 MCM")
        st.metric("Natural Discharge", "200 MCM")

    with col2:
        st.metric("Extractable Groundwater Resource", "800 MCM")
        st.metric("Total Annual Extraction", "600 MCM")

    st.info(
        "**Calculation:** 600 / 800 × 100 = 75%. "
        "The extraction stage is 75%, which falls in the Semi-Critical "
        "range."
    )

    st.divider()

    st.markdown("### Groundwater Assessment Categories")

    st.markdown(
        "The following are the standard extraction-stage thresholds "
        "used in India's groundwater resource assessment. Official "
        "classification also considers additional assessment criteria."
    )

    col1, col2 = st.columns(2)

    with col1:

        st.success("**Safe**")
        st.markdown("Extraction stage: **≤ 70%**")
        st.caption(
            "Extraction stage is within the Safe threshold."
        )

        st.warning("**Semi-Critical**")
        st.markdown("Extraction stage: **> 70% to 90%**")
        st.caption(
            "Groundwater use is relatively high and needs attention."
        )

    with col2:

        st.warning("**Critical**")
        st.markdown("Extraction stage: **> 90% to 100%**")
        st.caption(
            "Extraction is approaching the available resource."
        )

        st.error("**Over-Exploited**")
        st.markdown("Extraction stage: **> 100%**")
        st.caption(
            "Extraction exceeds the annual extractable resource."
        )

    st.divider()

    st.markdown("### Why These Indicators Matter")

    st.markdown(
        """
        - **Resource assessment:** Understand groundwater replenishment
          and availability.
        - **Extraction monitoring:** Examine how much groundwater is
          being used.
        - **Regional comparison:** Compare resource availability and
          extraction across assessment areas.
        - **Groundwater stress identification:** Identify areas requiring
          attention and conservation measures.
        - **Historical analysis:** Study changes in recharge, extraction
          and assessment categories across years.
        """
    )

    with st.expander(
        "Important: Groundwater Level vs. Extraction Stage"
    ):

        st.markdown(
            """
            These are two different groundwater indicators.

            - **Groundwater level:** The depth at which groundwater is
              encountered in a well.
            - **Extraction stage:** The percentage of the annual
              extractable groundwater resource being extracted.

            A deeper groundwater level does not automatically mean an
            assessment unit is Critical or Over-Exploited.

            Official categorization also considers groundwater-level
            trends and other assessment criteria.
            """
        )

    st.caption(
        "Reference: Central Ground Water Board (CGWB), Ground Water "
        "Resource Assessment and GEC-2015 methodology. These explanations "
        "are simplified for dashboard users."
    )


# ============================================================
# STATE DASHBOARD
# ============================================================

def dashboard_page(df: pd.DataFrame) -> None:

    st.title("💧 Groundwater Intelligence")

    st.caption(
        "Maharashtra | Groundwater Resource Monitoring "
        "& Regional Decision Support"
    )

    if df.empty:
        empty_state("No records available for the selected filters.")
        return

    required_columns = [
        COL_YEAR,
        COL_DISTRICT,
        COL_CATEGORY,
    ]

    missing_columns = [
        column for column in required_columns
        if column not in df.columns
    ]

    if missing_columns:
        st.error(
            "Dashboard cannot load because these required columns "
            f"are missing: {', '.join(missing_columns)}"
        )
        return

    summary = get_data_summary(df)

    numeric_years = pd.to_numeric(df[COL_YEAR], errors="coerce")
    valid_df = df[numeric_years.notna()].copy()
    valid_df[COL_YEAR] = numeric_years[numeric_years.notna()].astype(int)

    if valid_df.empty:
        empty_state("No valid assessment years are available.")
        return

    latest_year = valid_df[COL_YEAR].max()
    latest = valid_df[valid_df[COL_YEAR] == latest_year].copy()

    section_header(
        "Statewide Overview",
        f"Assessment data for {int(latest_year)}",
        "📊",
    )

    years = get_available_years(df)

    c1, c2, c3, c4 = st.columns(4)

    with c1:
        metric_card("Total Records", f"{summary['records']:,}")

    with c2:
        metric_card("Districts", summary["districts"])

    with c3:
        metric_card("Talukas", summary["talukas"])

    with c4:
        year_label = (
            f"{min(years)}–{max(years)}"
            if years
            else "N/A"
        )
        metric_card("Assessment Years", year_label)

    st.divider()

    tab1, tab2, tab3 = st.tabs([
        "📊 Resource Overview",
        "⚠️ Groundwater Stress",
        "📈 Regional Rankings",
    ])

    with tab1:

        section_header(
            "Groundwater Resource Indicators",
            "Explore recharge, extraction and resource utilization.",
        )

        category_metrics(df)

        left, right = st.columns(2)

        with left:

            category_data = latest[COL_CATEGORY].dropna()

            if not category_data.empty:

                fig = px.pie(
                    names=category_data.value_counts().index,
                    values=category_data.value_counts().values,
                    title="Groundwater Category Distribution",
                    hole=0.45,
                )

                fig.update_layout(**PLOTLY_THEME)

                st.plotly_chart(
                    fig,
                    use_container_width=True,
                    key="dashboard_category_chart",
                )

            else:
                st.info("No category information is available.")

        with right:

            available = [
                column for column in [
                    "Annual Recharge (MCM)",
                    "Total Extraction (MCM)",
                    "Extractable Resource (MCM)",
                ]
                if column in latest.columns
            ]

            if available:

                metric = st.selectbox(
                    "Select Resource Indicator",
                    available,
                    key="dashboard_resource_metric",
                )

                ranked = (
                    latest.groupby(COL_DISTRICT, as_index=False)[metric]
                    .mean()
                    .dropna(subset=[metric])
                    .sort_values(metric, ascending=False)
                    .head(15)
                )

                if not ranked.empty:

                    fig = px.bar(
                        ranked.sort_values(metric),
                        x=metric,
                        y=COL_DISTRICT,
                        orientation="h",
                        title=f"District Comparison: {metric}",
                    )

                    fig.update_layout(**PLOTLY_THEME)

                    st.plotly_chart(
                        fig,
                        use_container_width=True,
                        key="dashboard_resource_chart",
                    )

                else:
                    st.info("No numeric values are available for this indicator.")

            else:
                st.info("Resource indicator columns are unavailable.")

    with tab2:

        section_header(
            "Groundwater Stress Assessment",
            "Explore the distribution of assessment categories.",
            "⚠️",
        )

        category_counts = (
            latest[COL_CATEGORY]
            .dropna()
            .value_counts()
            .rename_axis("Category")
            .reset_index(name="Assessment Records")
        )

        left, right = st.columns(2)

        with left:

            if not category_counts.empty:

                fig = px.bar(
                    category_counts,
                    x="Category",
                    y="Assessment Records",
                    title="Assessment Category Distribution",
                    text="Assessment Records",
                )

                fig.update_layout(**PLOTLY_THEME)

                st.plotly_chart(
                    fig,
                    use_container_width=True,
                )

            else:
                st.info("No assessment categories are available.")

        with right:

            st.markdown("#### Category Summary")

            total = category_counts["Assessment Records"].sum()

            if total:

                for _, row in category_counts.iterrows():

                    count = int(row["Assessment Records"])
                    percentage = count / total * 100

                    with st.container(border=True):
                        st.write(f"**{row['Category']}**")
                        st.progress(percentage / 100)
                        st.caption(
                            f"{count:,} assessment records · "
                            f"{percentage:.1f}%"
                        )

            else:
                st.info("No category records to summarize.")

        st.info(
            "Assessment categories reflect the underlying dataset. "
            "They are not independently verified by this dashboard."
        )

    with tab3:

        section_header(
            "Regional Rankings",
            "Compare districts using the extraction-stage indicator.",
            "🏆",
        )

        stage_column = "Extraction Stage Numeric"

        if stage_column not in latest.columns:

            st.warning(
                "Extraction-stage data is unavailable in the current dataset."
            )

        else:

            ranking = (
                latest.groupby(COL_DISTRICT, as_index=False)[stage_column]
                .mean()
                .dropna(subset=[stage_column])
                .sort_values(stage_column, ascending=False)
            )

            if not ranking.empty:

                st.dataframe(
                    ranking,
                    use_container_width=True,
                    hide_index=True,
                )

                top = ranking.iloc[0]

                with st.container(border=True):

                    st.markdown(
                        "**Highest recorded average extraction stage**"
                    )

                    st.metric(
                        str(top[COL_DISTRICT]),
                        f"{top[stage_column]:.2f}%",
                    )

            else:
                st.info("No valid extraction-stage values are available.")

    st.divider()

    with st.expander("View Latest Assessment Records"):

        display_df = latest.copy()

        display_df[COL_YEAR] = display_df[COL_YEAR].astype(str)

        st.dataframe(
            display_df,
            use_container_width=True,
            hide_index=True,
        )

    st.divider()

    render_groundwater_classification_guide()

    page_footer()


# ============================================================
# DISTRICT ANALYSIS
# ============================================================

def district_analysis_page(df: pd.DataFrame) -> None:

    st.title("🗺️ District Intelligence")

    st.caption(
        "Explore district-specific groundwater conditions "
        "and historical resource patterns."
    )

    if df.empty:
        empty_state("No district records are available.")
        return

    districts = sorted(df[COL_DISTRICT].dropna().unique())

    if not districts:
        empty_state("No district information available.")
        return

    with st.container(border=True):

        district = st.selectbox(
            "Select District",
            districts,
            key="district_analysis_select",
        )

        years = sorted(
            pd.to_numeric(df[COL_YEAR], errors="coerce")
            .dropna()
            .astype(int)
            .unique(),
            reverse=True,
        )

        year_options = ["Latest"] + years

        selected_year = st.selectbox(
            "Assessment Year",
            year_options,
            key="district_analysis_year",
        )

    filtered = df[df[COL_DISTRICT] == district].copy()

    if selected_year != "Latest":
        filtered = filtered[
            pd.to_numeric(filtered[COL_YEAR], errors="coerce")
            == selected_year
        ]

    if filtered.empty:
        empty_state(
            "No records available for this district and assessment year."
        )
        return

    engine = DataQueryEngine(df)

    result = engine.district_summary(
        district,
        year=None if selected_year == "Latest" else selected_year,
    )

    st.divider()

    if result.data is not None and not result.data.empty:

        latest = (
            filtered.sort_values(COL_YEAR).iloc[-1]
        )

        c1, c2, c3 = st.columns(3)

        for col, label, key in [
            (c1, "Annual Recharge", "Annual Recharge (MCM)"),
            (c2, "Total Extraction", "Total Extraction (MCM)"),
            (c3, "Extraction Stage", "Extraction Stage Numeric"),
        ]:

            value = latest.get(key)

            with col:

                metric_card(
                    label,
                    (
                        f"{value:,.2f}"
                        if pd.notna(value)
                        else "N/A"
                    ),
                )

    overview, trends, records = st.tabs([
        "📋 Summary",
        "📈 Historical Trends",
        "📑 Assessment Records",
    ])

    with overview:

        section_header("District Summary")

        st.markdown(result.answer)

        with st.expander("About This Assessment"):
            st.write(
                "The displayed indicators are derived from "
                "the available district assessment records."
            )

    with trends:

        section_header("Historical Groundwater Trends")

        if result.data is not None and not result.data.empty:

            available = [
                metric for metric in [
                    "Annual Recharge (MCM)",
                    "Total Extraction (MCM)",
                    "Extraction Stage Numeric",
                ]
                if metric in result.data.columns
            ]

            selected_metrics = st.multiselect(
                "Indicators",
                available,
                default=available[:2],
                key="district_trend_metrics",
            )

            if selected_metrics:

                fig = trend_chart(
                    result.data,
                    selected_metrics,
                    f"{district} Historical Trends",
                )

                st.plotly_chart(
                    fig,
                    use_container_width=True,
                )

            else:
                st.info("Select at least one indicator.")

    with records:

        section_header("Assessment Records")

        st.dataframe(
            filtered,
            use_container_width=True,
            hide_index=True,
        )

        download_buttons(
            filtered,
            f"{district}_groundwater",
        )

    page_footer()


# ============================================================
# TALUKA ANALYSIS
# ============================================================

def taluka_analysis_page(df: pd.DataFrame) -> None:

    st.title("Taluka Analysis")

    st.caption(
        "Analyze a selected taluka's groundwater metrics "
        "and extraction-stage trend."
    )

    if df.empty:
        empty_state("No taluka records are available.")
        return

    districts = sorted(df[COL_DISTRICT].dropna().unique())

    if not districts:
        empty_state("No district information is available.")
        return

    district = st.selectbox(
        "District",
        districts,
        key="tal_district",
    )

    district_df = df[df[COL_DISTRICT] == district]

    talukas = sorted(
        district_df[COL_TALUKA].dropna().unique()
    )

    if not talukas:
        empty_state("No taluka information is available for this district.")
        return

    taluka = st.selectbox(
        "Taluka",
        talukas,
        key="tal_taluka",
    )

    engine = DataQueryEngine(district_df)

    result = engine.taluka_summary(taluka)

    st.markdown(result.answer)

    if result.data is not None and not result.data.empty:

        if "Extraction Stage Numeric" in result.data.columns:

            st.plotly_chart(
                trend_chart(
                    result.data,
                    ["Extraction Stage Numeric"],
                    f"{taluka} Extraction Stage",
                ),
                use_container_width=True,
            )

        with st.expander("View Taluka Records"):

            st.dataframe(
                result.data,
                use_container_width=True,
                hide_index=True,
            )


# ============================================================
# REGIONAL EXPLORER
# ============================================================

def district_map_page(df: pd.DataFrame) -> None:

    st.title("District Map")

    st.caption(
        "Interactive map of groundwater districts."
    )

    if df.empty:
        empty_state("No records are available for the map.")
        return

    district_map(df)


def regional_explorer_page(df: pd.DataFrame) -> None:

    st.title("Regional Explorer")

    st.caption(
        "District and taluka analysis, comparisons, and regional records."
    )

    tab1, tab2, tab3 = st.tabs([
        "District Analysis",
        "Taluka Analysis",
        "District Map",
    ])

    with tab1:
        district_analysis_page(df)

    with tab2:
        taluka_analysis_page(df)

    with tab3:
        district_map_page(df)


# ============================================================
# HISTORICAL ANALYSIS
# ============================================================

def trend_analysis_page(df: pd.DataFrame) -> None:

    st.title("📈 Historical Trend Analysis")

    st.caption(
        "Explore long-term groundwater changes and regional differences."
    )

    if df.empty:
        empty_state("No historical records are available.")
        return

    available_metrics = [
        metric for metric in [
            "Annual Recharge (MCM)",
            "Total Extraction (MCM)",
            "Extraction Stage Numeric",
        ]
        if metric in df.columns
    ]

    if not available_metrics:
        st.warning("No historical indicators are available.")
        return

    with st.container(border=True):

        c1, c2 = st.columns(2)

        with c1:

            selected_districts = st.multiselect(
                "Compare Districts",
                sorted(df[COL_DISTRICT].dropna().unique()),
                key="trend_districts",
            )

        with c2:

            selected_metrics = st.multiselect(
                "Select Indicators",
                available_metrics,
                default=available_metrics[:1],
                key="trend_metrics",
            )

        years = get_available_years(df)

        if not years:
            st.warning("No year information available.")
            return

        year_range = st.slider(
            "Historical Period",
            min_value=min(years),
            max_value=max(years),
            value=(min(years), max(years)),
            key="trend_year_range",
        )

    filtered = df.copy()

    if selected_districts:
        filtered = filtered[
            filtered[COL_DISTRICT].isin(selected_districts)
        ]

    numeric_year = pd.to_numeric(filtered[COL_YEAR], errors="coerce")

    filtered = filtered[
        numeric_year.between(*year_range)
    ].copy()

    if filtered.empty:
        empty_state("No data matches your selected filters.")
        return

    if not selected_metrics:
        st.info("Select at least one indicator.")
        return

    section_header("Trend Visualization")

    for metric in selected_metrics:

        with st.container(border=True):

            st.subheader(metric)

            if len(selected_districts) > 1:

                chart_data = (
                    filtered.groupby(
                        [COL_YEAR, COL_DISTRICT],
                        as_index=False,
                    )[metric]
                    .mean()
                )

                fig = px.line(
                    chart_data,
                    x=COL_YEAR,
                    y=metric,
                    color=COL_DISTRICT,
                    markers=True,
                    title=f"{metric} — District Comparison",
                )

                fig.update_layout(**PLOTLY_THEME)

                st.plotly_chart(
                    fig,
                    use_container_width=True,
                )

            else:

                chart_data = (
                    filtered.groupby(COL_YEAR, as_index=False)[metric]
                    .mean()
                )

                fig = trend_chart(
                    chart_data,
                    [metric],
                    f"Historical {metric}",
                )

                st.plotly_chart(
                    fig,
                    use_container_width=True,
                )

    with st.expander("View Filtered Data"):

        st.dataframe(
            filtered,
            use_container_width=True,
            hide_index=True,
        )

    page_footer()


# ============================================================
# FORECASTING AND RISK
# ============================================================

def prediction_page(df: pd.DataFrame) -> None:

    st.title("Future Prediction Center")

    st.caption(
        "Forecast groundwater indicators using the implemented "
        "machine learning and historical trend models."
    )

    if df.empty:
        empty_state("No records are available for forecasting.")
        return

    districts = sorted(df[COL_DISTRICT].dropna().unique())

    if not districts:
        empty_state("No district information is available.")
        return

    district = st.selectbox(
        "District",
        districts,
        key="pred_district",
    )

    horizon = st.slider(
        "Forecast Horizon (years)",
        1,
        10,
        5,
        key="forecast_horizon",
    )

    if st.button(
        "Generate Forecast",
        type="primary",
    ):

        with st.spinner("Generating forecast..."):

            fc = forecast_district(
                df,
                district,
                horizon=horizon,
            )

        if fc is None or fc.empty:
            st.error("No data available for forecasting.")
            return

        st.warning(
            "Results below are model-generated estimates, "
            "not observed groundwater measurements."
        )

        display_df = fc.copy()

        if "Year" in display_df.columns:
            display_df["Year"] = display_df["Year"].astype(str)

        st.dataframe(
            display_df,
            use_container_width=True,
            hide_index=True,
        )

        st.plotly_chart(
            forecast_chart(fc, district),
            use_container_width=True,
        )

        with st.expander("Model Validation (Chronological Holdout)"):

            result = evaluate_forecasting(df)

            metrics = result.get("metrics", {})

            if metrics:

                m1, m2 = st.columns(2)

                if "xgboost" in metrics:

                    m1.metric(
                        "XGBoost MAE",
                        metrics["xgboost"]["mae"],
                    )

                    m1.metric(
                        "XGBoost RMSE",
                        metrics["xgboost"]["rmse"],
                    )

                    m1.metric(
                        "XGBoost R²",
                        metrics["xgboost"]["r2"],
                    )

                if "persistence" in metrics:

                    m2.metric(
                        "Persistence MAE",
                        metrics["persistence"]["mae"],
                    )

                    m2.metric(
                        "Persistence RMSE",
                        metrics["persistence"]["rmse"],
                    )

                    m2.metric(
                        "Persistence R²",
                        metrics["persistence"]["r2"],
                    )

                st.caption(result.get("note", ""))

                predictions = result.get(
                    "predictions",
                    pd.DataFrame(),
                )

                if isinstance(predictions, pd.DataFrame) and not predictions.empty:
                    st.dataframe(
                        predictions.head(20),
                        use_container_width=True,
                        hide_index=True,
                    )

            else:
                st.warning("Insufficient data for validation.")

        required_forecast_columns = [
            "Predicted Stage",
            "Predicted Category",
            "Confidence Score",
        ]

        if all(
            column in fc.columns
            for column in required_forecast_columns
        ):

            last = fc.iloc[-1]

            c1, c2, c3 = st.columns(3)

            c1.metric(
                "Predicted Extraction Stage",
                f"{last['Predicted Stage']:.1f}%",
            )

            c2.metric(
                "Groundwater Category",
                str(last["Predicted Category"]),
            )

            c3.metric(
                "Model Confidence",
                f"{last['Confidence Score']:.1f}%",
            )

        download_buttons(
            fc,
            f"forecast_{district}",
        )


# ============================================================
# DATA EXPLORER
# ============================================================

def data_explorer_page(df: pd.DataFrame) -> None:

    st.title("🗃️ Groundwater Data Explorer")

    st.caption(
        "Search, filter, inspect and export groundwater assessment records."
    )

    if df.empty:
        empty_state("No groundwater records are available.")
        return

    with st.container(border=True):

        st.subheader("Data Filters")

        with st.form("data_explorer_filters"):

            c1, c2, c3 = st.columns(3)

            with c1:

                district = st.selectbox(
                    "District",
                    ["All"] + sorted(
                        df[COL_DISTRICT].dropna().unique().tolist()
                    ),
                )

            with c2:

                taluka = st.selectbox(
                    "Taluka",
                    ["All"] + sorted(
                        df[COL_TALUKA].dropna().unique().tolist()
                    ),
                )

            with c3:

                years = sorted(
                    df[COL_YEAR].dropna().unique().tolist(),
                    reverse=True,
                )

                year = st.selectbox(
                    "Assessment Year",
                    ["All"] + years,
                )

            search = st.text_input(
                "Search records",
                placeholder="Enter district, taluka or category...",
            )

            submitted = st.form_submit_button(
                "Apply Filters",
                type="primary",
                use_container_width=True,
            )

    filtered = df.copy()

    if submitted:

        if district != "All":
            filtered = filtered[
                filtered[COL_DISTRICT] == district
            ]

        if taluka != "All":
            filtered = filtered[
                filtered[COL_TALUKA] == taluka
            ]

        if year != "All":
            filtered = filtered[
                filtered[COL_YEAR] == year
            ]

        if search:

            mask = filtered.astype(str).apply(
                lambda row: row.str.contains(
                    search,
                    case=False,
                    na=False,
                ).any(),
                axis=1,
            )

            filtered = filtered[mask]

    st.divider()

    section_header(
        "Query Results",
        "Filtered groundwater records.",
    )

    c1, c2, c3 = st.columns(3)

    with c1:
        metric_card("Matching Records", f"{len(filtered):,}")

    with c2:
        metric_card(
            "Districts",
            filtered[COL_DISTRICT].nunique()
            if not filtered.empty else 0,
        )

    with c3:
        metric_card(
            "Talukas",
            filtered[COL_TALUKA].nunique()
            if not filtered.empty else 0,
        )

    if filtered.empty:
        empty_state("No records match your search criteria.")
        return

    tab1, tab2, tab3 = st.tabs([
        "📋 Records",
        "🔍 Data Quality",
        "📊 Summary",
    ])

    with tab1:

        st.dataframe(
            filtered,
            use_container_width=True,
            hide_index=True,
            height=450,
        )

        download_buttons(
            filtered,
            "jalnetra_filtered_data",
        )

    with tab2:

        missing = filtered.isna().sum()
        missing = missing[missing > 0]

        duplicate_count = int(filtered.duplicated().sum())

        c1, c2 = st.columns(2)

        with c1:
            metric_card(
                "Missing Values",
                f"{int(filtered.isna().sum().sum()):,}",
            )

        with c2:
            metric_card(
                "Duplicate Rows",
                f"{duplicate_count:,}",
            )

        if missing.empty:

            st.success(
                "No missing values detected in the filtered records."
            )

        else:

            st.dataframe(
                missing.rename("Missing Count").to_frame(),
                use_container_width=True,
            )

        with st.expander("Missing Value Details"):

            st.dataframe(
                (
                    filtered.isna().mean() * 100
                ).round(2).rename("Missing Percentage"),
                use_container_width=True,
            )

        st.caption(
            "These are basic record-level checks, not a complete "
            "validation of source accuracy or measurement quality."
        )

    with tab3:

        section_header("Dataset Distribution")

        c1, c2 = st.columns(2)

        with c1:

            category_data = (
                filtered[COL_CATEGORY]
                .value_counts()
                .reset_index()
            )

            category_data.columns = [
                "Category",
                "Records",
            ]

            fig = px.pie(
                category_data,
                names="Category",
                values="Records",
                hole=0.4,
                title="Category Distribution",
            )

            fig.update_layout(**PLOTLY_THEME)

            st.plotly_chart(
                fig,
                use_container_width=True,
            )

        with c2:

            yearly = (
                filtered.groupby(COL_YEAR)
                .size()
                .reset_index(name="Records")
            )

            fig = px.bar(
                yearly,
                x=COL_YEAR,
                y="Records",
                title="Year-wise Records",
            )

            fig.update_layout(**PLOTLY_THEME)

            st.plotly_chart(
                fig,
                use_container_width=True,
            )

    page_footer()


# ============================================================
# ASSESSMENTS
# ============================================================

def assessments_page(df: pd.DataFrame) -> None:

    st.title("Assessment Units")

    st.caption(
        "Search and filter groundwater assessment records."
    )

    search = st.text_input(
        "Search by district, taluka, category, or year"
    )

    category = st.selectbox(
        "Category",
        [
            "All",
            "Safe",
            "Semi-Critical",
            "Critical",
            "Over-Exploited",
        ],
    )

    filtered = copy_df(df)

    if search:

        mask = filtered.astype(str).apply(
            lambda row: row.str.contains(
                search,
                case=False,
                na=False,
            ).any(),
            axis=1,
        )

        filtered = filtered[mask]

    if category != "All":

        filtered = filtered[
            filtered[COL_CATEGORY] == category
        ]

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

    available_cols = [
        column for column in cols
        if column in filtered.columns
    ]

    if filtered.empty:

        st.warning(
            "No assessment units match the selected filters."
        )
        return

    display_df = filtered[available_cols].copy()

    if COL_YEAR in display_df.columns:
        display_df[COL_YEAR] = display_df[COL_YEAR].astype(str)

    st.dataframe(
        display_df,
        use_container_width=True,
        hide_index=True,
    )

    download_buttons(
        display_df,
        "jalnetra_assessment_units",
    )


# ============================================================
# DOWNLOAD CENTER AND REPORTS
# ============================================================

def download_center_page(df: pd.DataFrame) -> None:

    st.title("Download Center")

    st.caption(
        "Export filtered datasets and generate district PDF reports."
    )

    if df.empty:
        empty_state("No records are available for export.")
        return

    st.subheader("Export Dataset")

    download_buttons(
        df,
        "jalnetra_groundwater",
    )

    st.divider()

    st.subheader("Generate PDF Report")

    districts = sorted(
        df[COL_DISTRICT].dropna().unique()
    )

    if not districts:
        st.warning("No districts are available.")
        return

    district = st.selectbox(
        "District for PDF",
        districts,
        key="pdf_d",
    )

    district_df = df[
        df[COL_DISTRICT] == district
    ].sort_values(COL_YEAR)

    if district_df.empty:
        st.warning("No records available for this district.")
        return

    latest = district_df.iloc[-1]

    stage = latest.get(
        "Extraction Stage Numeric",
        latest.get("Extraction Stage (%)", 0),
    )

    if pd.isna(stage):
        stage = 0

    if st.button(
        "Generate PDF",
        type="primary",
    ):

        path = (
            BASE_DIR
            / "exports"
            / f"report_{district}.pdf"
        )

        path.parent.mkdir(
            parents=True,
            exist_ok=True,
        )

        result = generate_report(
            str(path),
            district,
            stage,
            latest[COL_CATEGORY],
        )

        if result and path.exists():

            with path.open("rb") as file:

                st.download_button(
                    "Download PDF Report",
                    file,
                    file_name=path.name,
                    mime="application/pdf",
                )

            st.success("Report generated.")

        else:
            st.error("Report generation failed.")


# ============================================================
# QUERY HISTORY
# ============================================================

def query_history_page(df=None) -> None:

    st.title("Query History")

    st.caption(
        "Review your recent AI assistant conversations."
    )

    messages = st.session_state.get("messages", [])

    if st.button("Clear History"):

        st.session_state["messages"] = []

        if "chat_memory" in st.session_state:
            st.session_state.chat_memory.history = []

        st.rerun()

    if not messages:
        st.info("No query history yet.")
        return

    for msg in messages:

        label = (
            "User"
            if msg.get("role") == "user"
            else APP_NAME
        )

        st.markdown(f"### {label}")

        st.markdown(
            msg.get("content", "")
        )

        st.divider()


# ============================================================
# DATA AND REPORTS PAGE
# ============================================================

def data_reports_page(df: pd.DataFrame) -> None:

    st.title("Data & Reports")

    st.caption(
        "Assessment records, data quality, exports, and PDF reports."
    )

    tab1, tab2, tab3, tab4 = st.tabs([
        "Data Explorer",
        "Assessments",
        "Download Center",
        "Query History",
    ])

    with tab1:
        data_explorer_page(df)

    with tab2:
        assessments_page(df)

    with tab3:
        download_center_page(df)

    with tab4:
        query_history_page(df)


# ============================================================
# ABOUT JALNETRA
# ============================================================

def about_project_page(df: pd.DataFrame) -> None:

    st.title("About JALNETRA")

    st.caption(
        "Maharashtra Groundwater Intelligence & Decision Support Platform"
    )

    st.write(
        "Understanding groundwater. Identifying risks. "
        "Supporting sustainable water management."
    )

    st.divider()

    st.subheader("1. About the Project")

    st.write(
        "JALNETRA is a data-driven groundwater intelligence platform "
        "designed to analyze, visualize, and communicate groundwater "
        "conditions across Maharashtra, India. The platform transforms "
        "groundwater resource assessment data into meaningful insights "
        "through interactive visualizations, district-level comparisons, "
        "historical analysis, and groundwater stress indicators. JALNETRA "
        "aims to make complex groundwater information more accessible, "
        "understandable, and useful for researchers, policymakers, students, "
        "environmental analysts, and water resource planners."
    )

    st.subheader("2. The Problem")

    st.write(
        "Groundwater is one of Maharashtra's most important natural "
        "resources, supporting agriculture, domestic consumption, and "
        "industrial activities. However, increasing water demand, uneven "
        "rainfall distribution, excessive groundwater extraction, and "
        "changing recharge patterns create significant challenges for "
        "sustainable groundwater management. Understanding these challenges "
        "requires examining multiple indicators, including groundwater "
        "recharge, extractable groundwater resources, extraction levels, "
        "extraction stages, and groundwater availability. Raw datasets "
        "often make it difficult to identify regional differences, "
        "historical patterns, and areas experiencing groundwater stress."
    )

    st.subheader("3. Literature Review")

    literature_text = read_literature_review()

    st.markdown(literature_text)

    st.subheader("4. Our Solution")

    st.write(
        "JALNETRA addresses this information gap by providing an integrated "
        "analytical environment for exploring groundwater conditions across "
        "Maharashtra. The platform converts structured groundwater datasets "
        "into interactive dashboards and visual insights, helping users "
        "explore groundwater resource conditions across districts and "
        "talukas, identify areas with high groundwater extraction stages, "
        "compare groundwater recharge, extraction, and available resources, "
        "analyze pre-monsoon and post-monsoon groundwater levels, examine "
        "historical groundwater trends and variations, identify potential "
        "groundwater stress hotspots, and compare groundwater conditions "
        "across administrative regions."
    )

    st.subheader("5. Key Features")

    st.markdown(
        """
        - **Groundwater Intelligence:** Interactive indicators for recharge,
          extractable resources, groundwater extraction, and extraction stage.
        - **Regional Analysis:** Explore groundwater conditions at available
          district and taluka levels.
        - **Historical Analysis:** Understand changes in groundwater levels
          and resource conditions over time.
        - **Comparative Analysis:** Compare groundwater indicators across
          administrative regions.
        - **Groundwater Stress Identification:** Explore areas classified
          as Safe, Semi-Critical, Critical, and Over-Exploited, based on
          the underlying assessment data.
        - **Data Transparency:** Present source information, data coverage,
          and analytical indicators to support informed interpretation.
        """
    )

    st.subheader("6. Data & Methodology")

    st.write(
        "JALNETRA uses structured groundwater resource assessment datasets "
        "and related supporting information to generate analytical "
        "indicators and visualizations. The analysis focuses on groundwater "
        "recharge, extractable groundwater resources, extraction, extraction "
        "stage, and groundwater-level variations. All indicators are "
        "interpreted according to their underlying data definitions and "
        "units. Data availability and geographic coverage may vary across "
        "reporting periods and administrative regions. The platform is "
        "intended for exploratory analysis and research, not as a "
        "replacement for official groundwater assessments."
    )

    if not df.empty:

        records = len(df)

        districts = (
            df[COL_DISTRICT].nunique()
            if COL_DISTRICT in df.columns
            else 0
        )

        talukas = (
            df[COL_TALUKA].nunique()
            if COL_TALUKA in df.columns
            else 0
        )

        years = get_available_years(df)

        year_text = (
            f"{min(years)} to {max(years)}"
            if years
            else "Not available"
        )

        st.markdown("#### Current Dataset Coverage")

        c1, c2, c3, c4 = st.columns(4)

        c1.metric("Records", f"{records:,}")
        c2.metric("Districts", districts)
        c3.metric("Talukas", talukas)
        c4.metric("Assessment Period", year_text)

    st.subheader("7. Project Objectives")

    st.markdown(
        """
        1. Improve accessibility to groundwater resource information.
        2. Simplify the interpretation of complex groundwater datasets.
        3. Identify regional variations in groundwater stress.
        4. Support data-driven understanding of groundwater sustainability.
        5. Encourage awareness and research on groundwater conservation.
        """
    )

    st.subheader("8. Who Can Use JALNETRA?")

    st.markdown(
        """
        - Researchers and academic institutions
        - Students and environmental science enthusiasts
        - Water resource planners
        - Government and policy analysts
        - Data analysts and geospatial researchers
        - Individuals interested in groundwater sustainability
        """
    )

    st.subheader("9. Disclaimer")

    st.write(
        "JALNETRA is an independent academic and data visualization project "
        "developed for educational, analytical, and research purposes. "
        "The insights presented are based on available datasets and the "
        "methodology implemented in the platform. They should not be "
        "interpreted as official government recommendations, real-time "
        "groundwater measurements, or definitive assessments of local "
        "groundwater availability. For regulatory decisions and official "
        "groundwater information, users should consult the relevant "
        "government authorities and original data sources."
    )

    st.subheader("10. Vision")

    st.markdown(
        "**Making groundwater data understandable, accessible, and actionable.**"
    )

    st.write(
        "JALNETRA envisions a future where accessible data and analytical "
        "tools contribute to better groundwater awareness, informed "
        "decision-making, and sustainable water resource management."
    )

    st.markdown(
        "**JALNETRA | Groundwater Intelligence for a Sustainable Maharashtra**"
    )

    st.divider()

    render_groundwater_classification_guide(
        show_section_number=True,
    )

    st.divider()

    st.subheader("12. References")

    st.markdown(
        """
        1. CGWB - Ground Water Resource Assessment. Official explanation of India's groundwater assessment framework and GEC methodology.
        2. Rodell, M., Velicogna, I., & Famiglietti, J. S. (2009). Satellite-based estimates of groundwater depletion in India. Nature, 460, 999-1002. DOI: 10.1038/nature08238.
        3. Asoka, A., et al. (2017). Relative contribution of monsoon precipitation and pumping to changes in groundwater storage in India. Nature Geoscience, 10, 109-117.
        4. CGWB (2025). Dynamic Ground Water Resources of Maharashtra - Assessment 2024.
        """
    )
    st.markdown(
        """
        5. Kale, A. A., et al. (2025). Spatio-Temporal Variation of Groundwater Table in the Palghar and Thane Districts of the North Konkan Region. Journal of Agricultural Research and Technology, 50(3), 286-298.
        """
    )


# ============================================================
# LITERATURE REVIEW PAGE
# ============================================================

def literature_review_page(df: pd.DataFrame) -> None:

    st.title("Literature Review")

    st.caption(
        "Research background and methodology context for JALNETRA."
    )

    literature_text = read_literature_review()

    st.markdown(literature_text)


# ============================================================
# MAIN APPLICATION
# ============================================================

def app_dashboard() -> None:

    # Load the master dataset once.
    master_df = load_master_dataframe()

    if master_df is None:
        st.error("Unable to load the groundwater dataset.")
        return

    if master_df.empty:
        st.error("The groundwater dataset is empty.")
        return

    # Navigation
    menu = sidebar_navigation(master_df)

    # Apply global filters
    df = apply_global_filters(master_df)

    topbar()

    pages = {
        "Home": lambda data: home_page(),

        "State Dashboard": dashboard_page,

        "Regional Explorer": regional_explorer_page,

        "Historical Analysis": trend_analysis_page,

        "Forecasting & Risk": prediction_page,

        "AI Assistant": lambda data: (
            st.title("🤖 AI Groundwater Assistant"),
            chatbot_ui(data),
        ),

        "Data & Reports": data_reports_page,

        "About JALNETRA": about_project_page,
    }

    handler = pages.get(menu, dashboard_page)

    # Home and About pages describe the complete project,
    # so they use the master dataset rather than filtered records.
    if menu in ["Home", "About JALNETRA", "Literature Review"]:
        handler(master_df)
    else:
        handler(df)

    page_footer()


# ============================================================
# ENTRY POINT
# ============================================================

def main() -> None:

    init_state()

    app_dashboard()


if __name__ == "__main__":
    main()
