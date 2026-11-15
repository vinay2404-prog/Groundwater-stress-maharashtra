import streamlit as st

import plotly.express as px

from visualization import COL_DISTRICT, COL_YEAR

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

DISTRICT_NAME_MAP = {
    "Ahmednagar": "Ahmednagar",
    "Akola": "Akola",
    "Amravati": "Amravati",
    "Beed": "Bid",
    "Bhandara": "Bhandara",
    "Buldhana": "Buldana",
    "Chandrapur": "Chandrapur",
    "Chh. Sambhajinagar": "Aurangabad",
    "Dharashiv": "Osmanabad",
    "Dhule": "Dhule",
    "Gadchiroli": "Garhchiroli",
    "Gondia": "Gondiya",
    "Hingoli": "Hingoli",
    "Jalgaon": "Jalgaon",
    "Jalna": "Jalna",
    "Kolhapur": "Kolhapur",
    "Latur": "Latur",
    "Mumbai City": "Greater Bombay",
    "Mumbai Suburban": "Greater Bombay",
    "Nagpur": "Nagpur",
    "Nanded": "Nanded",
    "Nandurbar": "Nandurbar",
    "Nashik": "Nashik",
    "Palghar": "Thane",
    "Parbhani": "Parbhani",
    "Pune": "Pune",
    "Raigad": "Raigarh",
    "Ratnagiri": "Ratnagiri",
    "Sangli": "Sangli",
    "Satara": "Satara",
    "Sindhudurg": "Sindhudurg",
    "Solapur": "Solapur",
    "Thane": "Thane",
    "Wardha": "Wardha",
    "Washim": "Washim",
    "Yavatmal": "Yavatmal",
}


@st.cache_data(show_spinner=False)
def _maharashtra_geojson():
    import json
    import urllib.request

    url = "https://raw.githubusercontent.com/geohacker/india/master/district/india_district.geojson"
    try:
        with urllib.request.urlopen(url, timeout=20) as resp:
            data = json.load(resp)
    except Exception:
        return None
    features = [f for f in data.get("features", []) if f.get("properties", {}).get("NAME_1") == "Maharashtra"]
    if not features:
        return None
    return {"type": "FeatureCollection", "features": features}


def district_map(df, color_col="Groundwater Category"):
    if df.empty:
        st.warning("No data available for map.")
        return

    latest_year = int(df[COL_YEAR].max())
    latest = (
        df[df[COL_YEAR] == latest_year]
        .groupby(COL_DISTRICT, as_index=False)
        .agg({color_col: "first", "Extraction Stage Numeric": "mean"})
    )
    latest["geo_district"] = latest[COL_DISTRICT].map(DISTRICT_NAME_MAP)
    latest = latest.dropna(subset=["geo_district"])

    geojson = _maharashtra_geojson()
    if geojson is not None:
        try:
            fig = px.choropleth(
                latest,
                geojson=geojson,
                locations="geo_district",
                featureidkey="properties.NAME_2",
                color=color_col,
                hover_name=COL_DISTRICT,
                hover_data={"Extraction Stage Numeric": ":.1f", "geo_district": False},
                title=f"District Groundwater Map ({latest_year})",
            )
            fig.update_geos(fitbounds="locations", visible=False)
            fig.update_layout(margin=dict(l=0, r=0, t=40, b=0), height=600)
            st.plotly_chart(fig, use_container_width=True)
            return
        except Exception:
            pass

    # Fallback to scatter map
    latest["lat"] = latest[COL_DISTRICT].map(lambda d: DISTRICT_COORDS.get(d, (None, None))[0])
    latest["lon"] = latest[COL_DISTRICT].map(lambda d: DISTRICT_COORDS.get(d, (None, None))[1])
    latest = latest.dropna(subset=["lat", "lon"])
    if latest.empty:
        st.warning("No coordinate data available for map.")
        return
    fig = px.scatter_map(
        latest,
        lat="lat",
        lon="lon",
        color=color_col,
        size="Extraction Stage Numeric",
        hover_name=COL_DISTRICT,
        hover_data={"Extraction Stage Numeric": ":.1f", "lat": False, "lon": False},
        zoom=5.5,
        height=600,
        title=f"District Groundwater Map ({latest_year})",
        map_style="carto-positron",
    )
    fig.update_layout(margin=dict(l=0, r=0, t=40, b=0))
    st.plotly_chart(fig, use_container_width=True)