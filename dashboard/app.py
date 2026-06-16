"""
Streamlit dashboard — live wallet risk monitor.
Run with: streamlit run dashboard/app.py
"""
import streamlit as st
import pandas as pd
import plotly.express as px
import requests

API_BASE = "http://localhost:8000/api/v1"

st.set_page_config(page_title="Blockchain Threat Monitor", layout="wide")
st.title("🔗 Blockchain Threat Detection Pipeline")
st.caption("Real-time wallet risk scoring — ETH + BTC")

# ── Sidebar controls ─────────────────────────────────────
st.sidebar.header("Filters")
risk_threshold = st.sidebar.slider("Min risk score", 0, 100, 70)
limit          = st.sidebar.number_input("Max wallets", 10, 500, 100)

# ── Fetch flagged wallets ─────────────────────────────────
@st.cache_data(ttl=10)
def fetch_flagged():
    try:
        r = requests.get(f"{API_BASE}/flagged?limit=500", timeout=5)
        return r.json().get("wallets", [])
    except Exception:
        return []

wallets = fetch_flagged()
df      = pd.DataFrame(wallets) if wallets else pd.DataFrame()

if df.empty:
    st.info("No flagged wallets yet — pipeline may still be warming up.")
    st.stop()

df = df[df["final_score"] >= risk_threshold].head(limit)

# ── Key metrics ───────────────────────────────────────────
col1, col2, col3, col4 = st.columns(4)
col1.metric("Flagged wallets",   len(df))
col2.metric("Avg risk score",    f"{df['final_score'].mean():.1f}")
col3.metric("Max risk score",    f"{df['final_score'].max():.1f}")
col4.metric("Rule-only flags",   int((df["rule_score"] > df["risk_score"]).sum()))

st.divider()

# ── Risk score distribution ───────────────────────────────
col_a, col_b = st.columns(2)
with col_a:
    st.subheader("Risk score distribution")
    fig = px.histogram(df, x="final_score", nbins=20,
                       color_discrete_sequence=["#E24B4A"])
    fig.update_layout(margin=dict(t=10, b=10), height=280)
    st.plotly_chart(fig, use_container_width=True)

with col_b:
    st.subheader("ML score vs rule score")
    fig2 = px.scatter(df, x="risk_score", y="rule_score",
                      hover_data=["wallet", "final_score"],
                      color="final_score",
                      color_continuous_scale="Reds")
    fig2.update_layout(margin=dict(t=10, b=10), height=280)
    st.plotly_chart(fig2, use_container_width=True)

# ── Flagged wallet table ──────────────────────────────────
st.subheader("Flagged wallets")
st.dataframe(
    df[["wallet", "final_score", "risk_score", "rule_score", "triggered_rules"]]
      .sort_values("final_score", ascending=False)
      .reset_index(drop=True),
    use_container_width=True,
)

# ── Single wallet lookup ──────────────────────────────────
st.subheader("Look up a wallet")
addr = st.text_input("Wallet address (ETH 0x… or BTC…)")
if addr:
    try:
        r = requests.get(f"{API_BASE}/wallet/{addr}", timeout=5)
        if r.status_code == 200:
            data = r.json()
            st.json(data)
            st.progress(int(data["final_score"]))
        else:
            st.warning("Wallet not found in current window.")
    except Exception as e:
        st.error(f"API error: {e}")
