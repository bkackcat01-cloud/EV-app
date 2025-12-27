import streamlit as st
import pandas as pd
import plotly.express as px
import os

# --- Configuration ---
FILE_NAME = 'ev_charging_log_my.csv'
CURRENCY = "MYR"

st.set_page_config(page_title="Malaysia EV Tracker", page_icon="⚡", layout="wide")
st.title("🇲🇾 Malaysia EV Charging Tracker")

# --- 1. INSTANT INPUT SECTION ---
# ... (你的原本输入代码保持不变)

# --- 3. ANALYTICS SECTION ---
if os.path.isfile(FILE_NAME):
    df = pd.read_csv(FILE_NAME)
    df['Date'] = pd.to_datetime(df['Date'])

    # Month selector
    df['Month'] = df['Date'].dt.to_period('M').astype(str)
    months = sorted(df['Month'].unique(), reverse=True)
    selected_month = st.selectbox("📅 Select Month", options=["All"] + months, index=0)
    if selected_month != "All":
        df = df[df['Month'] == selected_month]

    if df.empty:
        st.warning("⚠️ No data for the selected month.")
        st.stop()

    # Key metrics
    st.divider()
    m1, m2, m3, m4 = st.columns(4)
    m1.metric("Total Spent", f"{CURRENCY} {df['Total Cost'].sum():.2f}")
    m2.metric("Avg Price/kWh", f"{CURRENCY} {df['Cost_per_kWh'].mean():.2f}")
    m3.metric("Total Energy", f"{df['kWh'].sum():.1f} kWh")
    m4.metric("Sessions", len(df))

    # Graphs
    # ... (你的原本图表代码保持不变)

    # --- Raw Data with Edit Option ---
    with st.expander("📂 View & Edit Raw Data Log"):
        edited_df = st.data_editor(df.sort_values(by="Date", ascending=False), num_rows="dynamic")
        st.markdown("### ⚡ Save Edited Data")
        if st.button("💾 Save Changes"):
            edited_df.to_csv(FILE_NAME, index=False)
            st.success("✅ Changes saved successfully!")
else:
    st.info("Awaiting data... Log a session above to see the analysis!")
