import streamlit as st
import pandas as pd
import plotly.express as px
import os
from geopy.geocoders import Nominatim
from geopy.extra.rate_limiter import RateLimiter

# =========================
# CONFIG
# =========================
RAWDATA = "ev_charging_log_my.csv"
CURRENCY = "MYR"

st.set_page_config(
    page_title="Malaysia EV Charging Tracker",
    page_icon="⚡",
    layout="wide"
)

# Set Plotly map style
px.set_mapbox_access_token(os.environ.get("MAPBOX_TOKEN", ""))
px.defaults.template = "simple_white"

# =========================
# MINIMAL CSS
# =========================
st.markdown("""
<style>
section[data-testid="stSidebar"] { background-color: #fafafa; }
h1, h2, h3 { font-weight: 600; }
.plotly .mapboxgl-popup { z-index: 1000 !important; }
</style>
""", unsafe_allow_html=True)

# =========================
# HEADER
# =========================
st.markdown("""
# Malaysia EV Charging Tracker
<small style="color:gray">EV charging cost & usage insights</small>
""", unsafe_allow_html=True)

# =========================
# ENSURE CSV EXISTS
# =========================
EXPECTED_COLUMNS = ["Date","Provider","Location","Latitude","Longitude","Type","kWh","Total Cost","Cost_per_kWh","Month"]

if not os.path.isfile(RAWDATA) or os.path.getsize(RAWDATA) == 0:
    pd.DataFrame(columns=EXPECTED_COLUMNS).to_csv(RAWDATA, index=False)

# =========================
# LOAD DATA (FIXED)
# =========================
def load_data():
    try:
        df = pd.read_csv(RAWDATA)
        
        # 1. Ensure coordinate columns exist
        if "Latitude" not in df.columns: df["Latitude"] = pd.NA
        if "Longitude" not in df.columns: df["Longitude"] = pd.NA
        
        if not df.empty:
            # 2. Process Data Types
            df["Date"] = pd.to_datetime(df["Date"], errors="coerce")
            df["Month"] = df["Date"].dt.to_period("M").astype(str)
            df["Day"] = df["Date"].dt.day_name()
            df["Latitude"] = pd.to_numeric(df["Latitude"], errors='coerce')
            df["Longitude"] = pd.to_numeric(df["Longitude"], errors='coerce')

        # 3. Clean Reindexing (Prevents Duplicate 'Month' Column error)
        # We assume EXPECTED_COLUMNS already has 'Month', so we only add 'Day'
        cols_to_use = EXPECTED_COLUMNS + ["Day"]
        # Remove duplicates just in case to be safe
        cols_to_use = list(dict.fromkeys(cols_to_use))
        
        df = df.reindex(columns=cols_to_use)
        return df
    except Exception as e:
        st.error(f"Error loading data: {e}")
        return pd.DataFrame(columns=EXPECTED_COLUMNS)

df = load_data()

# =========================
# GEOCODING FUNCTION
# =========================
def get_coordinates(location_name):
    """
    Returns (lat, lon) for a given location name.
    """
    try:
        geolocator = Nominatim(user_agent="my_ev_tracker_v1")
        search_query = f"{location_name}, Malaysia"
        location = geolocator.geocode(search_query)
        if location:
            return location.latitude, location.longitude
        return None, None
    except Exception as e:
        return None, None

# =========================
# SIDEBAR FILTER
# =========================
filtered_df = df.copy()
with st.sidebar:
    st.header("Filters")
    # Check if Month column exists and acts as a Series (single column)
    if not df.empty and "Month" in df.columns:
        # Convert to list to avoid ambiguous truth value errors
        unique_months = df["Month"].dropna().unique().tolist()
        try:
            months = sorted(unique_months, reverse=True)
        except:
            months = unique_months 
        selected_month = st.selectbox("Month", ["All"] + months)
        if selected_month != "All":
            filtered_df = df[df["Month"] == selected_month]

# =========================
# TABS
# =========================
tab_log, tab_overview, tab_insights, tab_location, tab_data = st.tabs([
    "➕ Log Session",
    "📊 Overview",
    "📈 Insights",
    "📍 Locations (Map)",
    "🗂 Data (Edit)"
])

# =========================
# TAB 1 — LOG SESSION
# =========================
with tab_log:
    providers = [
        "Gentari", "JomCharge", "chargEV", "Shell Recharge",
        "TNB Electron", "ChargeSini", "Tesla Supercharger",
        "DC Handal", "Home", "Other"
    ]

    col1, col2 = st.columns(2)
    with col1:
        selected_provider = st.selectbox("Provider", providers)
    with col2:
        other_provider = st.text_input("Custom Provider", disabled=(selected_provider != "Other"))

    with st.form("log_form", clear_on_submit=True):
        st.write("---")
        c1, c2, c3 = st.columns(3)
        with c1:
            date_val = st.date_input("Date")
            location_name = st.text_input("Location Name (e.g. Suria KLCC)")
        with c2:
            output_type = st.radio("Type", ["AC", "DC"], horizontal=True)
            kwh_val = st.number_input("Energy (kWh)", min_value=0.1, step=0.1)
        with c3:
            total_cost = st.number_input(f"Total Cost ({CURRENCY})", min_value=0.0, step=0.01)

        st.write("---")
        st.caption("Coordinates (Leave 0.00 to auto-detect based on Location Name)")
        geo_c1, geo_c2 = st.columns(2)
        with geo_c1:
            lat_val = st.number_input("Latitude", value=0.00, format="%.5f")
        with geo_c2:
            lon_val = st.number_input("Longitude", value=0.00, format="%.5f")

        submitted = st.form_submit_button("Save Session", type="primary")

        if submitted:
            provider = other_provider.strip() if selected_provider == "Other" else selected_provider
            
            if not provider:
                st.error("Please specify provider name.")
            else:
                # --- AUTO GEOCODING LOGIC ---
                final_lat = lat_val
                final_lon = lon_val
                
                if (final_lat == 0.00 or final_lon == 0.00) and location_name.strip():
                    with st.spinner(f"Searching map for '{location_name}'..."):
                        found_lat, found_lon = get_coordinates(location_name)
                        if found_lat:
                            final_lat = found_lat
                            final_lon = found_lon
                            st.toast(f"📍 Coordinates found: {final_lat:.4f}, {final_lon:.4f}", icon="🗺️")
                        else:
                            st.warning(f"Could not auto-find '{location_name}'. Saved without coordinates.")
                            final_lat = pd.NA
                            final_lon = pd.NA
                elif final_lat == 0.00 and final_lon == 0.00:
                    final_lat = pd.NA
                    final_lon = pd.NA

                # Save Data
                cost_per_kwh = round(total_cost / kwh_val, 3) if kwh_val > 0 else 0
                month_str = str(pd.to_datetime(date_val).to_period("M"))

                new_data = {
                    "Date": date_val,
                    "Provider": provider,
                    "Location": location_name.strip(),
                    "Latitude": final_lat,
                    "Longitude": final_lon,
                    "Type": output_type,
                    "kWh": kwh_val,
                    "Total Cost": total_cost,
                    "Cost_per_kWh": cost_per_kwh,
                    "Month": month_str
                }
                
                new_row = pd.DataFrame([new_data])
                new_row_to_save = new_row[EXPECTED_COLUMNS]
                new_row_to_save.to_csv(RAWDATA, mode="a", header=False, index=False)
                
                st.toast("Charging session saved!", icon="✅")
                st.rerun()

# =========================
# TAB 2 — OVERVIEW
# =========================
with tab_overview:
    if filtered_df.empty:
        st.info("No data available for this selection.")
    else:
        m1, m2, m3, m4 = st.columns(4)
        m1.metric("Total Spent", f"{CURRENCY} {filtered_df['Total Cost'].sum():.2f}")
        avg_cost = filtered_df['Cost_per_kWh'].mean()
        m2.metric("Avg / kWh", f"{CURRENCY} {0.00 if pd.isna(avg_cost) else avg_cost:.2f}")
        m3.metric("Energy Used", f"{filtered_df['kWh'].sum():.1f} kWh")
        m4.metric("Sessions", len(filtered_df))

# =========================
# TAB 3 — INSIGHTS
# =========================
with tab_insights:
    if filtered_df.empty:
        st.info("No data available for this selection.")
    else:
        col1, col2 = st.columns(2)

        with col1:
            daily_df = filtered_df.groupby(filtered_df["Date"].dt.date)["Total Cost"].sum().reset_index()
            fig_daily = px.bar(daily_df, x="Date", y="Total Cost", title="Daily Spending")
            st.plotly_chart(fig_daily, use_container_width=True)

            fig_type = px.pie(filtered_df, names="Type", hole=0.5, title="AC vs DC Session Count")
            st.plotly_chart(fig_type, use_container_width=True)

        with col2:
            fig_scatter = px.scatter(
                filtered_df, x="kWh", y="Total Cost", color="Provider",
                size="Cost_per_kWh", title="Cost vs Energy",
                hover_data=["Location"]
            )
            st.plotly_chart(fig_scatter, use_container_width=True)

            if "Day" in filtered_df.columns:
                heatmap_df = filtered_df.groupby(["Day","Type"])["kWh"].sum().reset_index()
                day_order = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]
                fig_heatmap = px.density_heatmap(
                    heatmap_df, x="Day", y="Type", z="kWh",
                    category_orders={"Day": day_order},
                    color_continuous_scale="Viridis",
                    title="Charging Volume by Day (kWh)"
                )
                fig_heatmap.update_layout(xaxis_title=None, yaxis_title=None)
                st.plotly_chart(fig_heatmap, use_container_width=True)

# =========================
# TAB 4 — LOCATIONS (MAP)
# =========================
with tab_location:
    st.header("Location Analysis")
    
    map_df = filtered_df.dropna(subset=["Latitude", "Longitude"])
    
    if map_df.empty:
        st.warning("No data with coordinates found based on current filters.")
        st.info("💡 Tip: When logging a new session, leave Latitude/Longitude as 0.00. The app will try to auto-find the location name!")
    else:
        location_agg = map_df.groupby(["Location", "Latitude", "Longitude"]).agg(
            Total_Sessions=("Date", "count"),
            Total_Spent=("Total Cost", "sum")
        ).reset_index()

        fig_map = px.scatter_mapbox(
            location_agg,
            lat="Latitude",
            lon="Longitude",
            size="Total_Sessions",  
            size_max=30, 
            color="Total_Spent", 
            color_continuous_scale=px.colors.sequential.Plasma,
            hover_name="Location",
            hover_data={
                "Latitude": False, 
                "Longitude": False,
                "Total_Sessions": True,
                "Total_Spent": ":.2f"
            },
            zoom=10, 
            title=f"Charging Locations ({len(location_agg)} distinct sites)"
        )
        
        fig_map.update_layout(mapbox_style="open-street-map")
        fig_map.update_layout(margin={"r":0,"t":40,"l":0,"b":0})
        st.plotly_chart(fig_map, use_container_width=True)

    st.divider()

    st.subheader("Top Spending Locations (All Data)")
    named_loc_df = filtered_df[filtered_df["Location"].notna() & (filtered_df["Location"].str.strip() != "")]
    
    if named_loc_df.empty:
        st.info("No location names logged yet.")
    else:
        top_locations = (
            named_loc_df.groupby("Location")["Total Cost"]
            .sum().sort_values(ascending=False)
            .head(5).reset_index()
        )
        fig_loc = px.bar(top_locations, x="Total Cost", y="Location",
                            text="Total Cost", orientation='h')
        fig_loc.update_traces(texttemplate="%{text:.2f}", textposition="outside")
        fig_loc.update_layout(yaxis_title=None, xaxis_title=f"Total Cost ({CURRENCY})")
        st.plotly_chart(fig_loc, use_container_width=True)

# =========================
# TAB 5 — DATA (EDIT FULL DB)
# =========================
with tab_data:
    st.warning("⚠️ Editing data here changes the raw CSV file permanently.")
    
    if df.empty:
        st.info("No data available yet.")
    else:
        display_cols = ["Date", "Provider", "Location", "Latitude", "Longitude", "Type", "kWh", "Total Cost", "Month"]
        existing_cols = [c for c in display_cols if c in df.columns]
        
        edited_df = st.data_editor(
            df.sort_values("Date", ascending=False)[existing_cols], 
            num_rows="dynamic",
            use_container_width=True,
            column_config={
                "Latitude": st.column_config.NumberColumn(format="%.5f"),
                "Longitude": st.column_config.NumberColumn(format="%.5f"),
            }
        )
        
        if st.button("Save Changes to CSV", type="primary"):
            try:
                edited_df["Date"] = pd.to_datetime(edited_df["Date"])
                edited_df["Cost_per_kWh"] = edited_df.apply(
                    lambda x: round(x["Total Cost"] / x["kWh"], 3) if pd.notnull(x["kWh"]) and x["kWh"] > 0 else 0, 
                    axis=1
                )
                edited_df["Month"] = edited_df["Date"].dt.to_period("M").astype(str)

                final_save_df = edited_df[EXPECTED_COLUMNS]
                final_save_df.to_csv(RAWDATA, index=False)
                st.toast("Data saved successfully!", icon="💾")
                st.rerun()
            except Exception as e:
                st.error(f"Error saving data: {e}")
