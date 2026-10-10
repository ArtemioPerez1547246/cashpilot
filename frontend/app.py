import streamlit as st

st.set_page_config(page_title="CashPilot", layout="wide")
st.title("CashPilot")
st.caption("Paletería demo - forecast, optimize, and actions")

col1, col2, col3 = st.columns(3)
col1.metric("Cash today", "$8,000")
col2.metric("Min reserve", "$1,500")
col3.metric("Shortfall", "$0")

with st.sidebar:
    st.selectbox("Scenario", ["base", "disruption"])
    st.button("Reset demo")

st.write("Dashboard shell is live. Hook this to the real API when backend routes are ready.")
