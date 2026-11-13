"""Interactive Traffic Violations dashboard."""

import pandas as pd
import plotly.express as px
import streamlit as st

DATA_FILE = "data/clean/traffic_violations_clean.parquet"
WEEKDAYS = [
    "Monday",
    "Tuesday",
    "Wednesday",
    "Thursday",
    "Friday",
    "Saturday",
    "Sunday",
]

st.set_page_config(page_title="Traffic Violations Dashboard", layout="wide")


@st.cache_data
def load_data():
    """Load the cleaned Parquet file once and keep it in memory."""
    return pd.read_parquet(DATA_FILE)


def multiselect_filter(df, column, label):
    """Sidebar multiselect; no selection means 'show all'."""
    options = sorted(df[column].dropna().unique())
    chosen = st.sidebar.multiselect(label, options)
    return df[df[column].isin(chosen)] if chosen else df


df = load_data()
st.title("Traffic Violations Insight Dashboard")

# ---- Filters ----
st.sidebar.header("Filters")
min_date = df["date_of_stop"].min().date()
max_date = df["date_of_stop"].max().date()
date_range = st.sidebar.date_input(
    "Date range", (min_date, max_date), min_value=min_date, max_value=max_date
)
if len(date_range) == 2:
    start, end = pd.Timestamp(date_range[0]), pd.Timestamp(date_range[1])
    df = df[df["date_of_stop"].between(start, end)]

df = multiselect_filter(df, "violation_category", "Violation category")
df = multiselect_filter(df, "vehicle_type", "Vehicle type")
df = multiselect_filter(df, "gender", "Gender")
df = multiselect_filter(df, "race", "Race")
df = multiselect_filter(df, "sub_agency", "Location (police district)")

if df.empty:
    st.warning("No records match these filters.")
    st.stop()

# ---- Summary statistics ----
col1, col2, col3, col4 = st.columns(4)
col1.metric("Total violations", f"{len(df):,}")
col2.metric("Unique stops", f"{df['seq_id'].nunique():,}")
col3.metric("Involving accidents", f"{int(df['accident'].sum()):,}")
col4.metric("Most cited make", str(df["make"].value_counts().index[0]))

# ---- Charts ----
left, right = st.columns(2)
with left:
    by_category = df["violation_category"].value_counts().reset_index()
    by_category.columns = ["violation_category", "count"]
    st.plotly_chart(
        px.bar(
            by_category,
            x="violation_category",
            y="count",
            title="Violations by category",
        ),
        width="stretch",
    )

    by_hour = df["stop_hour"].value_counts().sort_index().reset_index()
    by_hour.columns = ["hour", "count"]
    st.plotly_chart(
        px.bar(by_hour, x="hour", y="count", title="Violations by hour of day"),
        width="stretch",
    )
with right:
    monthly = df.groupby(df["date_of_stop"].dt.to_period("M")).size()
    monthly.index = monthly.index.to_timestamp()
    monthly = monthly.rename("violations").reset_index()
    st.plotly_chart(
        px.line(
            monthly, x="date_of_stop", y="violations", title="Violations per month"
        ),
        width="stretch",
    )

# ---- High-risk zones and top vehicles ----
zone_col, make_col = st.columns(2)
with zone_col:
    st.subheader("High-risk zones (most accidents)")
    risky = df[df["accident"]].groupby("sub_agency", observed=True).size()
    st.dataframe(risky.sort_values(ascending=False).head(5).rename("accidents"))
with make_col:
    st.subheader("Most cited makes")
    st.dataframe(df["make"].value_counts().head(10).rename("violations"))

# ---- Map ----
st.subheader("Incident locations (random sample of 5,000)")
points = df.dropna(subset=["latitude", "longitude"])
if not points.empty:
    map_points = points.sample(min(5000, len(points)))[["latitude", "longitude"]]
    st.map(map_points.astype("float64"))  # float32 is not supported by st.map
