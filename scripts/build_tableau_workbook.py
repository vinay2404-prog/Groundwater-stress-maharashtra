"""
Build a clean CSV + a Tableau workbook (.twb) for the JALNETRA groundwater data.

Run:
    python scripts/build_tableau_workbook.py

Outputs:
    data/groundwater_data_clean.csv
    JALNETRA_Groundwater_Stress.twb
"""

from __future__ import annotations

import re
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
RAW_CSV = ROOT / "data" / "groundwater_data.csv"
CLEAN_CSV = ROOT / "data" / "groundwater_data_clean.csv"
TWB = ROOT / "JALNETRA_Groundwater_Stress.twb"

# ---------------------------------------------------------------- clean data

df = pd.read_csv(RAW_CSV, dtype=str)

# The raw export contains the header row repeated inside the data 4 times.
df = df[df["State"].str.strip().str.lower() != "state"]
df = df[df["Year"].str.strip().str.lower() != "year"]

for col in ["State", "District", "Taluka", "Groundwater Category", "Subdivision"]:
    df[col] = df[col].str.strip()
    df[col] = df[col].str.replace(r"\s+", " ", regex=True)

df["Groundwater Category"] = df["Groundwater Category"].replace(
    {
        "Safe (Saline Risk)": "Safe (Saline Risk)",
        "Over Exploited": "Over-Exploited",
        "OverExploited": "Over-Exploited",
        "Semi Critical": "Semi-Critical",
    }
)

df["Extraction Stage (%)"] = (
    df["Extraction Stage (%)"].str.replace("%", "", regex=False).str.strip()
)

# Some talukas report the water table as a range ("6.5 - 12.0") instead of a
# single reading. Use the midpoint and flag the row so it stays traceable.
RANGE = re.compile(r"^\s*([0-9.]+)\s*[-\u2013]\s*([0-9.]+)\s*$")


def to_level(value: str) -> float | None:
    text = str(value).strip()
    if text.lower() in {"", "nan", "na", "-"}:
        return None
    match = RANGE.match(text)
    if match:
        low, high = float(match.group(1)), float(match.group(2))
        return round((low + high) / 2, 2)
    try:
        return float(text.replace("%", ""))
    except ValueError:
        return None


for col in ["Pre-Monsoon Level (mbgl)", "Post-Monsoon Level (mbgl)"]:
    df[col + " (reported)"] = df[col]
    df[col] = df[col].map(to_level)

is_range = df["Pre-Monsoon Level (mbgl) (reported)"].str.contains(
    r"^\s*[0-9.]+\s*[-\u2013]\s*[0-9.]+\s*$", regex=True
)
df["Level_Basis"] = "Reported Level"
df.loc[is_range, "Level_Basis"] = "Range Midpoint"

numeric = [
    "Pre-Monsoon Level (mbgl)",
    "Post-Monsoon Level (mbgl)",
    "Annual Recharge (MCM)",
    "Extractable Resource (MCM)",
    "Total Extraction (MCM)",
    "Extraction Stage (%)",
]
for col in numeric:
    df[col] = pd.to_numeric(df[col], errors="coerce")

df["Year"] = pd.to_numeric(df["Year"], errors="coerce").astype("Int64")
df = df.dropna(subset=numeric + ["Year", "District", "Taluka"])

clean = df[
    [
        "State",
        "Year",
        "District",
        "Taluka",
        "Pre-Monsoon Level (mbgl)",
        "Post-Monsoon Level (mbgl)",
        "Annual Recharge (MCM)",
        "Extractable Resource (MCM)",
        "Total Extraction (MCM)",
        "Extraction Stage (%)",
        "Groundwater Category",
        "Level_Basis",
    ]
].copy()

clean.columns = [
    "State",
    "Year",
    "District",
    "Taluka",
    "Pre_Monsoon_Level_mbgl",
    "Post_Monsoon_Level_mbgl",
    "Annual_Recharge_MCM",
    "Extractable_Resource_MCM",
    "Total_Extraction_MCM",
    "Extraction_Stage_Pct",
    "Groundwater_Category",
    "Level_Basis",
]

# Keep Year numeric so Tableau treats it as an ordinal dimension.
clean["Year"] = clean["Year"].astype(int)

clean.to_csv(CLEAN_CSV, index=False)
print(f"clean rows: {len(clean):,} -> {CLEAN_CSV}")

# ---------------------------------------------------------------- twb fields

DS = "federated.0"
DATA_DIR = str(CLEAN_CSV.parent).replace("\\", "/")
CSV_NAME = CLEAN_CSV.name
TABLE = "[groundwater_data_clean#csv]"

# (name, caption, datatype, role, type, remote-type, debug-type)
FIELDS = [
    ("State", "State", "string", "dimension", "nominal", 129, "WSTR"),
    ("Year", "Year", "integer", "dimension", "quantitative", 20, "I4"),
    ("District", "District", "string", "dimension", "nominal", 129, "WSTR"),
    ("Taluka", "Taluka", "string", "dimension", "nominal", 129, "WSTR"),
    ("Pre_Monsoon_Level_mbgl", "Pre-Monsoon Level (mbgl)", "real", "measure", "quantitative", 5, "R8"),
    ("Post_Monsoon_Level_mbgl", "Post-Monsoon Level (mbgl)", "real", "measure", "quantitative", 5, "R8"),
    ("Annual_Recharge_MCM", "Annual Recharge (MCM)", "real", "measure", "quantitative", 5, "R8"),
    ("Extractable_Resource_MCM", "Extractable Resource (MCM)", "real", "measure", "quantitative", 5, "R8"),
    ("Total_Extraction_MCM", "Total Extraction (MCM)", "real", "measure", "quantitative", 5, "R8"),
    ("Extraction_Stage_Pct", "Extraction Stage (%)", "real", "measure", "quantitative", 5, "R8"),
    ("Groundwater_Category", "Groundwater Category", "string", "dimension", "nominal", 129, "WSTR"),
    ("Level_Basis", "Level Basis", "string", "dimension", "nominal", 129, "WSTR"),
]

COLUMN_XML: dict[str, str] = {}
METADATA_XML: list[str] = []
RELATION_COLUMNS: list[str] = []

for ordinal, (name, caption, dtype, role, typ, rtype, debug) in enumerate(FIELDS):
    fmt = " default-format='0.0'" if dtype == "real" else ""
    COLUMN_XML[name] = (
        f"      <column caption='{caption}' datatype='{dtype}' name='[{name}]' "
        f"role='{role}' type='{typ}'{fmt} />"
    )
    RELATION_COLUMNS.append(
        f"          <column datatype='{dtype}' name='{name}' ordinal='{ordinal}' />"
    )
    collation = (
        "          <collation flag='0' name='binary' />\n" if dtype == "string" else ""
    )
    METADATA_XML.append(
        f"""        <metadata-record class='column'>
          <remote-name>{name}</remote-name>
          <remote-type>{rtype}</remote-type>
          <local-name>[{name}]</local-name>
          <parent-name>[{CSV_NAME}]</parent-name>
          <remote-alias>{name}</remote-alias>
          <ordinal>{ordinal}</ordinal>
          <local-type>{dtype}</local-type>
          <aggregation>{"Count" if dtype == "string" else "Sum"}</aggregation>
          <contains-null>true</contains-null>
{collation}          <attributes>
            <attribute datatype='string' name='DebugRemoteType'>&quot;{debug}&quot;</attribute>
          </attributes>
        </metadata-record>"""
    )

COLUMN_XML["Number of Records"] = (
    "      <column datatype='integer' name='[Number of Records]' role='measure' "
    "type='quantitative' />"
)


def ref(field: str, agg: str = "none", kind: str = "nk") -> str:
    return f"[{DS}].[{agg}:{field}:{kind}]"


def dependency(*fields: str) -> str:
    rows = "\n".join(COLUMN_XML[f] for f in fields)
    return (
        f"          <datasource-dependencies datasource='{DS}'>\n"
        f"{rows}\n"
        f"          </datasource-dependencies>"
    )


def sheet(
    name: str,
    fields: list[str],
    rows: str,
    cols: str,
    mark: str,
    encodings: str = "",
    sort: str = "",
    viz: str = "",
) -> str:
    enc = f"\n            <encodings>\n{encodings}\n            </encodings>" if encodings else ""
    sort_xml = f"\n{sort}" if sort else ""
    viz_xml = f"\n{viz}" if viz else ""
    return f"""    <worksheet name='{name}'>
      <table>
        <view>
          <datasources>
            <datasource caption='Groundwater (Maharashtra)' name='{DS}' />
          </datasources>
{dependency(*fields)}{sort_xml}
          <aggregation value='true' />
        </view>
        <style />{viz_xml}
        <panes>
          <pane selection-relaxation-option='selection-relaxation-allow'>
            <view>
              <breakdown value='auto' />
            </view>
            <mark class='{mark}' />{enc}
          </pane>
        </panes>
        <rows>{rows}</rows>
        <cols>{cols}</cols>
      </table>
    </worksheet>"""


# 1. Average extraction stage per district, heat-coloured by the same measure.
sheet_district = sheet(
    name="Stage by District",
    fields=["District", "Extraction_Stage_Pct"],
    rows=ref("District"),
    cols=ref("Extraction_Stage_Pct", "avg", "qk"),
    mark="Bar",
    encodings=f"              <color column='{ref('Extraction_Stage_Pct', 'avg', 'qk')}' />",
)

# 2. How many talukas fall in each stress category.
sheet_category = sheet(
    name="Category Count",
    fields=["Groundwater_Category", "Number of Records"],
    rows=ref("Number of Records", "cnt", "qk"),
    cols=ref("Groundwater_Category"),
    mark="Bar",
    encodings=f"              <color column='{ref('Groundwater_Category')}' />",
)

# 3. State-wide extraction stress trend, 2021 -> 2025.
sheet_trend = sheet(
    name="Stress Trend",
    fields=["Year", "Extraction_Stage_Pct"],
    rows=ref("Extraction_Stage_Pct", "avg", "qk"),
    cols=ref("Year", "none", "qk"),
    mark="Line",
)

# 4. Pre vs post monsoon depth, one dot per taluka, coloured by category.
sheet_scatter = sheet(
    name="Pre vs Post Levels",
    fields=["Pre_Monsoon_Level_mbgl", "Post_Monsoon_Level_mbgl", "Groundwater_Category", "Taluka", "District"],
    rows=ref("Post_Monsoon_Level_mbgl", "avg", "qk"),
    cols=ref("Pre_Monsoon_Level_mbgl", "avg", "qk"),
    mark="Circle",
    encodings="\n".join(
        [
            f"              <color column='{ref('Groundwater_Category')}' />",
            f"              <lod column='{ref('Taluka')}' />",
            f"              <lod column='{ref('District')}' />",
        ]
    ),
)

DATA = "\n".join(COLUMN_XML[f[0]] for f in FIELDS)
DATA += "\n" + COLUMN_XML["Number of Records"]
META = "\n".join(METADATA_XML)

TITLE = "JALNETRA  |  Maharashtra Groundwater Stress"

workbook = f"""<?xml version='1.0' encoding='utf-8' ?>
<!-- Generated by scripts/build_tableau_workbook.py -->
<workbook original-version='18.1' source-build='2021.1.0 (20211.21.0307.1526)' source-platform='win' version='18.1'>
  <preferences>
    <preference name='ui.encoding.shelf.height' value='24' />
    <preference name='ui.shelf.height' value='26' />
  </preferences>
  <datasources>
    <datasource caption='Groundwater (Maharashtra)' inline='true' name='{DS}' version='18.1'>
      <connection class='federated'>
        <named-connections>
          <named-connection caption='groundwater_data_clean' name='textscan.0'>
            <connection class='textscan' directory='{DATA_DIR}' filename='{CSV_NAME}' password='' server='' />
          </named-connection>
        </named-connections>
        <relation connection='textscan.0' name='{CSV_NAME}' table='{TABLE}' type='table' />
        <metadata-records>
{META}
        </metadata-records>
      </connection>
      <aliases enabled='yes' />
{DATA}
    </datasource>
  </datasources>
  <worksheets>
{sheet_district}
{sheet_category}
{sheet_trend}
{sheet_scatter}
  </worksheets>
  <dashboards>
    <dashboard name='Water Stress Overview'>
      <style />
      <size maxheight='820' maxwidth='1200' minheight='820' minwidth='1200' />
      <zones>
        <zone h='100000' id='1' type='layout-basic' w='100000' x='0' y='0' />
        <zone h='6500' id='2' type='text' w='100000' x='0' y='0'>
          <formatted-text>
            <run bold='true' fontsize='20'>{TITLE}</run>
          </formatted-text>
        </zone>
        <zone h='46750' id='3' name='Stage by District' w='50000' x='0' y='6500' type='worksheet' />
        <zone h='46750' id='4' name='Category Count' w='50000' x='50000' y='6500' type='worksheet' />
        <zone h='46750' id='5' name='Stress Trend' w='50000' x='0' y='53250' type='worksheet' />
        <zone h='46750' id='6' name='Pre vs Post Levels' w='50000' x='50000' y='53250' type='worksheet' />
      </zones>
    </dashboard>
  </dashboards>
</workbook>
"""

TWB.write_text(workbook, encoding="utf-8")
print(f"workbook -> {TWB}")
