import streamlit as st
import pandas as pd
import plotly.express as px
import pydeck as pdk
from geopy.geocoders import Nominatim
from datetime import datetime
import time

# ===============================
# CONFIG
# ===============================
st.set_page_config(
    page_title="Malaysia EV Charging Dashboard",
    page_icon="⚡",
    layout="wide"
)

FILE_NAME = "ev_charging_log_my.csv"

# ===============================
# LOAD DATA
# ===============================
@st.cache_data
def load_data():
    df = pd.read_csv(FILE_NAME)
    df["Date"] = pd.to_datetime(df["Date"], errors="coerce")
    return df

df = load_data()

st.title("⚡ Malaysia EV Charging Analytics")

if df.empty:
    st.error("CSV is empty or not found.")
    st.stop()

# ===============================
# FREE AUTO GEOCODING (OSM)
# ===============================
@st.cache_data
def geocode_locations(locations):
    geolocator = Nominatim(user_agent="ev-charging-app")
    coords = {}

    for loc in locations:
        try:
            geo = geolocator.geocode(f"{loc}, Malaysia")
            if geo:
                coords[loc] = (geo.latitude, geo.longitude)
            else:
                coords[loc] = (None, None)
            time.sleep(1)  # respect free API rate
        except:
            coords[loc] = (None, None)

    return coords


if "Latitude" not in df.columns or "Longitude" not in df.columns:
    st.info("📍 Auto-geocoding locations (free OpenStreetMap)")
    loc_map = geocode_locations(df["Location"].dropna().unique())
    df["Latitude"] = df["Location"].map(lambda x: loc_map.get(x, (None, None))[0])
    df["Longitude"] = df["Location"].map(lambda x: loc_map.get(x, (None, None))[1])

# ===============================
# DERIVED FEATURES
# ===============================
df["Cost_per_kWh"] = df["Total Cost"] / df["kWh"]

# Session duration proxy (if no time)
df["Session_Duration_Proxy"] = df["kWh"] / df.groupby("Type")["kWh"].transform("mean")

df["Hour"] = df["Date"].dt.hour
df["Day"] = df["Date"].dt.day_name()

# ===============================
# TABS
# ===============================
tab_insights, tab_location = st.tabs(["📊 Insights", "📍 Locations"])

# ======================================================
# INSIGHTS TAB
# ======================================================
with tab_insights:
    col1, col2 = st.columns(2)

    with col1:
        daily_df = (
            df.groupby(df["Date"].dt.date)["Total Cost"]
            .sum()
            .reset_index(name="Total Cost")
        )

        fig_daily = px.bar(
            daily_df,
            x="Date",
            y="Total Cost",
            title="📅 Daily Charging Spend (MYR)"
        )
        st.plotly_chart(fig_daily, use_container_width=True)

        fig_type = px.pie(
            df,
            names="Type",
            values="Total Cost",
            hole=0.5,
            title="🔌 AC vs DC Cost Distribution"
        )
        st.plotly_chart(fig_type, use_container_width=True)

    with col2:
        fig_scatter = px.scatter(
            df,
            x="kWh",
            y="Total Cost",
            color="Provider",
            size="Cost_per_kWh",
            title="💰 Cost vs Energy",
            hover_data=["Location"]
        )
        st.plotly_chart(fig_scatter, use_container_width=True)

        fig_duration = px.box(
            df,
            x="Type",
            y="Session_Duration_Proxy",
            title="⏱ Session Duration Proxy (AC vs DC)"
        )
        st.plotly_chart(fig_duration, use_container_width=True)

    # Heatmap
    heat_df = (
        df.groupby(["Day", "Hour"])
        .size()
        .reset_index(name="Sessions")
    )

    fig_heat = px.density_heatmap(
        heat_df,
        x="Hour",
        y="Day",
        z="Sessions",
        color_continuous_scale="Turbo",
        title="🔥 Charging Behavior Heatmap (Day vs Hour)"
    )
    st.plotly_chart(fig_heat, use_container_width=True)

# ======================================================
# LOCATION TAB — BIG POPUPS MAP
# ======================================================
with tab_location:
    loc_stats = (
        df.dropna(subset=["Latitude", "Longitude"])
        .groupby("Location")
        .agg(
            Sessions=("Location", "count"),
            Total_Cost=("Total Cost", "sum"),
            Total_kWh=("kWh", "sum"),
            Latitude=("Latitude", "first"),
            Longitude=("Longitude", "first")
        )
        .reset_index()
    )

    if loc_stats.empty:
        st.warning("No valid geocoded locations.")
    else:
        st.subheader("📍 Charging Sessions by Location")

        loc_stats["popup"] = loc_stats.apply(
            lambda r: (
                f"<b>{r.Location}</b><br/>"
                f"🔌 Sessions: {r.Sessions}<br/>"
                f"⚡ Energy: {r.Total_kWh:.1f} kWh<br/>"
                f"💰 Cost: MYR {r.Total_Cost:.2f}"
            ),
            axis=1
        )

        deck = pdk.Deck(
            initial_view_state=pdk.ViewState(
                latitude=loc_stats["Latitude"].mean(),
                longitude=loc_stats["Longitude"].mean(),
                zoom=6
            ),
            layers=[
                pdk.Layer(
                    "ScatterplotLayer",
                    data=loc_stats,
                    get_position=["Longitude", "Latitude"],
                    get_radius="Sessions * 800",
                    radius_min_pixels=15,
                    radius_max_pixels=80,
                    get_fill_color=[0, 140, 255, 180],
                    get_line_color=[255, 255, 255],
                    line_width_min_pixels=2,
                    pickable=True
                )
            ],
            tooltip={
                "html": "{popup}",
                "style": {
                    "backgroundColor": "white",
                    "color": "black",
                    "fontSize": "14px",
                    "padding": "12px",
                    "borderRadius": "10px",
                    "boxShadow": "0 6px 18px rgba(0,0,0,0.25)"
                }
            }
        )

        st.pydeck_chart(deck, use_container_width=True)
