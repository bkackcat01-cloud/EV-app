import streamlit as st
import pandas as pd
import plotly.express as px
import os

# =========================
# CONFIG
# =========================
RAWDATA = "rawdata.csv"
CURRENCY = "MYR"

st.set_page_config(
    page_title="Malaysia EV Charging Tracker",
    page_icon="⚡",
    layout="wide"
)

px.defaults.template = "simple_white"

# =========================
# MINIMAL CSS
# =========================
st.markdown("""
<style>
section[data-testid="stSidebar"] {
    background-color: #fafafa;
}
h1, h2, h3 {
    font-weight: 600;
}
</style>
""", unsafe_allow_html=True)

# =========================
# HEADER
# =========================
st.markdown("""
# Malaysia EV Charging Tracker
<small style="color:gray">Track charging cost, energy usage & providers</small>
""", unsafe_allow_html=True)

# =========================
# INPUT SECTION
# =========================
with st.expander("➕ Add New Charging Session", expanded=True):

    providers = [
        "Gentari", "JomCharge", "chargEV", "Shell Recharge",
        "TNB Electron", "ChargeSini", "Tesla Supercharger",
        "DC Handal", "Home", "Other"
    ]

    col_p1, col_p2 = st.columns(2)
    with col_p1:
        selected_provider = st.selectbox("Provider", providers)

    with col_p2:
        other_name = st.text_input(
            "Custom Provider",
            placeholder="e.g. JusEV",
            disabled=(selected_provider != "Other")
        )

    with st.form("charging_form", clear_on_submit=True):

        st.markdown("#### Session Details")

        c1, c2, c3 = st.columns(3)

        with c1:
            date_val = st.date_input("Date")
            location = st.text_input("Location", placeholder="Pavilion Bukit Jalil")

        with c2:
            output_type = st.radio("Type", ["AC", "DC"], horizontal=True)
            kwh_val = st.number_input("Energy (kWh)", min_value=0.1, step=0.1)

        with c3:
            total_cost = st.number_input(
                f"Total Cost ({CURRENCY})",
                min_value=0.0,
                step=0.01
            )

        submitted = st.form_submit_button("Save Session")

        if submitted:
            final_provider = other_name.strip() if selected_provider == "Other" else selected_provider

            if selected_provider == "Other" and not final_provider:
                st.error("Please specify the provider name.")
            else:
                cost_per_kwh = round(total_cost / kwh_val, 3)

                new_row = pd.DataFrame([{
                    "Date": pd.to_datetime(date_val),
                    "Provider": final_provider,
                    "Location": location,
                    "Type": output_type,
                    "kWh": kwh_val,
                    "Total Cost": total_cost,
                    "Cost_per_kWh": cost_per_kwh
                }])

                if not os.path.isfile(RAWDATA):
                    new_row.to_csv(RAWDATA, index=False)
                else:
                    new_row.to_csv(RAWDATA, mode="a", header=False, index=False)

                st.success(f"Session saved for {final_provider}")

# =========================
# LOAD DATA
# =========================
if not os.path.isfile(RAWDATA):
    st.info("No data yet. Add a charging session above.")
    st.stop()

df = pd.read_csv(RAWDATA)
df["Date"] = pd.to_datetime(df["Date"])
df["Month"] = df["Date"].dt.to_period("M").astype(str)

# =========================
# SIDEBAR FILTERS
# =========================
with st.sidebar:
    st.header("Filters")

    months = sorted(df["Month"].unique(), reverse=True)
    selected_month = st.selectbox("Month", ["All"] + months)

    if selected_month != "All":
        df = df[df["Month"] == selected_month]

if df.empty:
    st.warning("No data for the selected filter.")
    st.stop()

# =========================
# METRICS
# =========================
st.markdown("## Overview")

m1, m2, m3, m4 = st.columns(4)
m1.metric("Total Spent", f"{CURRENCY} {df['Total Cost'].sum():.2f}")
m2.metric("Avg / kWh", f"{CURRENCY} {df['Cost_per_kWh'].mean():.2f}")
m3.metric("Energy Used", f"{df['kWh'].sum():.1f} kWh")
m4.metric("Sessions", len(df))

# =========================
# CHARTS
# =========================
st.markdown("## Spending Analysis")

col_a, col_b = st.columns(2)

with col_a:
    daily_df = df.groupby(df["Date"].dt.date)["Total Cost"].sum().reset_index()

    fig_daily = px.bar(
        daily_df,
        x="Date",
        y="Total Cost",
        title="Daily Spending",
        color_discrete_sequence=["#111111"]
    )
    st.plotly_chart(fig_daily, use_container_width=True)

    fig_provider = px.pie(
        df,
        names="Provider",
        values="Total Cost",
        hole=0.5,
        title="Spending by Provider"
    )
    st.plotly_chart(fig_provider, use_container_width=True)

with col_b:
    fig_type = px.pie(
        df,
        names="Type",
        title="Charging Type Distribution",
        hole=0.5
    )
    st.plotly_chart(fig_type, use_container_width=True)

    fig_scatter = px.scatter(
        df,
        x="kWh",
        y="Total Cost",
        color="Provider",
        size="Cost_per_kWh",
        title="Cost vs Energy",
        labels={"Total Cost": f"Total Cost ({CURRENCY})"},
        hover_data=["Location"]
    )
    st.plotly_chart(fig_scatter, use_container_width=True)

# =========================
# TOP LOCATIONS
# =========================
st.markdown("## Top Locations")

top_locations = (
    df.groupby("Location")["Total Cost"]
    .sum()
    .sort_values(ascending=False)
    .head(5)
    .reset_index()
)

fig_top = px.bar(
    top_locations,
    x="Location",
    y="Total Cost",
    title="Top 5 Locations by Spending",
    text="Total Cost"
)
fig_top.update_traces(texttemplate="%{text:.2f}", textposition="outside")
st.plotly_chart(fig_top, use_container_width=True)

# =========================
# RAW DATA
# =========================
with st.expander("View & Edit Raw Data"):
    edited_df = st.data_editor(
        df.sort_values("Date", ascending=False),
        num_rows="dynamic"
    )

    if st.button("Save Changes"):
        edited_df.to_csv(RAWDATA, index=False)
        st.success("Changes saved successfully")
