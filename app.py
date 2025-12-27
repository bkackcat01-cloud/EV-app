import streamlit as st
import pandas as pd
import plotly.express as px
import os
from datetime import datetime

# --- Configuration ---
FILE_NAME = 'ev_charging_log_my.csv'
CURRENCY = "MYR"

st.set_page_config(page_title="Malaysia EV Tracker", page_icon="⚡", layout="wide")
st.title("🇲🇾 Malaysia EV Charging Tracker")

# --- 1. Input Section ---
st.subheader("📝 Record New Session")
providers = [
    "Gentari", "JomCharge", "chargEV", "Shell Recharge (ParkEasy)", 
    "TNB Electron", "ChargeSini", "Tesla Supercharger", "DC Handal", "Home", "Other"
]

col_p1, col_p2 = st.columns([1, 2])
with col_p1:
    selected_provider = st.selectbox("Select Provider", providers)
with col_p2:
    other_name = ""
    if selected_provider == "Other":
        other_name = st.text_input("✍️ Specify Provider Name", placeholder="e.g. JusEV")

with st.form("charging_form", clear_on_submit=True):
    col1, col2, col3 = st.columns(3)
    with col1:
        date_val = st.date_input("Date")
        location = st.text_input("Location", placeholder="e.g. Pavilion Bukit Jalil")
    with col2:
        output_type = st.radio("Output Type", ["AC", "DC"], horizontal=True)
        kwh_val = st.number_input("Energy (kWh)", min_value=0.1, step=0.1)
    with col3:
        total_cost = st.number_input(f"Total Cost ({CURRENCY})", min_value=0.0, step=0.01)

    submitted = st.form_submit_button("💾 Save Session Data")
    if submitted:
        final_provider = other_name if selected_provider == "Other" else selected_provider
        if selected_provider == "Other" and not other_name.strip():
            st.error("Please enter a provider name in the 'Specify' box.")
        else:
            cost_per_kwh = total_cost / kwh_val if kwh_val > 0 else 0
            new_data = pd.DataFrame([{
                "Date": pd.to_datetime(date_val),
                "Provider": final_provider,
                "Location": location,
                "Type": output_type,
                "kWh": kwh_val,
                "Total Cost": total_cost,
                "Cost_per_kWh": round(cost_per_kwh, 3)
            }])
            if not os.path.isfile(FILE_NAME):
                new_data.to_csv(FILE_NAME, index=False)
            else:
                new_data.to_csv(FILE_NAME, mode='a', header=False, index=False)
            st.success(f"✅ Session recorded for {final_provider}!")

# --- 2. Analytics Section ---
if os.path.isfile(FILE_NAME):
    df = pd.read_csv(FILE_NAME)
    df['Date'] = pd.to_datetime(df['Date'])
    df['kWh'] = pd.to_numeric(df['kWh'], errors='coerce')
    df['Total Cost'] = pd.to_numeric(df['Total Cost'], errors='coerce')
    df['Cost_per_kWh'] = pd.to_numeric(df['Cost_per_kWh'], errors='coerce')

    # Month selector
    df['Month'] = df['Date'].dt.to_period('M').astype(str)
    months = sorted(df['Month'].unique(), reverse=True)
    selected_month = st.selectbox("📅 Select Month", options=["All"] + months, index=0)
    if selected_month != "All":
        df = df[df['Month'] == selected_month]

    if df.empty:
        st.warning("⚠️ No data for selected month.")
        st.stop()

    # KPIs
    st.divider()
    m1, m2, m3, m4 = st.columns(4)
    m1.metric("💰 Total Spent", f"{CURRENCY} {df['Total Cost'].sum():.2f}")
    m2.metric("⚡ Avg Price / kWh", f"{CURRENCY} {df['Cost_per_kWh'].mean():.2f}")
    m3.metric("🔋 Total Energy", f"{df['kWh'].sum():.1f} kWh")
    m4.metric("🔌 Sessions", len(df))

    # Graphs
    col_a, col_b = st.columns(2)

    with col_a:
        # Daily spending
        daily_df = df.groupby(df['Date'].dt.date, as_index=False)['Total Cost'].sum()
        fig_daily = px.bar(daily_df, x='Date', y='Total Cost', text_auto=True, title=f"📈 Daily Spending ({CURRENCY})")
        st.plotly_chart(fig_daily, use_container_width=True)

        # Provider spending
        fig_provider = px.pie(df, names='Provider', values='Total Cost', hole=0.4, title="🏢 Spending by Provider")
        st.plotly_chart(fig_provider, use_container_width=True)

    with col_b:
        # AC vs DC
        type_cost = df.groupby('Type', as_index=False)['Total Cost'].sum()
        fig_type = px.bar(type_cost, x='Type', y='Total Cost', text_auto=True, title="⚡ AC vs DC Cost Comparison")
        st.plotly_chart(fig_type, use_container_width=True)

        # Efficiency scatter
        fig_scatter = px.scatter(df, x="kWh", y="Total Cost", color="Provider", size="Cost_per_kWh",
                                 hover_data=['Location', 'Type'], title="📈 Energy vs Cost (Bubble = Price/kWh)",
                                 labels={'Total Cost': f'Total Cost ({CURRENCY})'})
        st.plotly_chart(fig_scatter, use_container_width=True)

    # Top 5 expensive chargers
    st.subheader("🏆 Top 5 Most Expensive Chargers (RM/kWh)")
    top5 = df.sort_values("Cost_per_kWh", ascending=False).head(5)
    fig_top5 = px.bar(top5, x="Cost_per_kWh", y="Location", orientation='h', color="Provider",
                      text_auto=True, title="Top 5 Most Expensive Chargers")
    st.plotly_chart(fig_top5, use_container_width=True)

    # Provider efficiency ranking
    st.subheader("📊 Provider Efficiency Ranking (RM/kWh)")
    provider_eff = df.groupby('Provider', as_index=False)['Cost_per_kWh'].mean().sort_values('Cost_per_kWh')
    fig_eff = px.bar(provider_eff, x='Cost_per_kWh', y='Provider', orientation='h', text_auto=True,
                     title="Average Cost per kWh by Provider")
    st.plotly_chart(fig_eff, use_container_width=True)

    # Monthly trend line
    st.subheader("📈 Monthly Trend Line (Total Spending)")
    monthly_df = df.groupby(df['Date'].dt.to_period('M'), as_index=False)['Total Cost'].sum()
    monthly_df['Date'] = monthly_df['Date'].dt.to_timestamp()
    fig_monthly = px.line(monthly_df, x='Date', y='Total Cost', text='Total Cost',
                          title="Monthly Total Spending", markers=True)
    st.plotly_chart(fig_monthly, use_container_width=True)

    # Raw Data
    with st.expander("📂 View Raw Data Log"):
        st.dataframe(df.sort_values(by="Date", ascending=False), use_container_width=True)

else:
    st.info("Awaiting data... Log a session above to see the analysis! 🚗⚡")
