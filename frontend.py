import streamlit as st
import requests
import pandas as pd
import plotly.express as px

BACKEND_URL = "http://127.0.0.1:5000"

# ---------------- PAGE SETUP ----------------
st.set_page_config(
    page_title="AML Laundering Detection",
    layout="wide",
    initial_sidebar_state="expanded"
)

# ---------------- HEADER ----------------
st.markdown(
    """
    <h1 style='text-align:center;'> Blockchain Money Laundering Detection</h1>
    <p style='text-align:center; color:gray;'>
        Graph-based AML using Fan-In, Fan-Out, Peeling & Proximity Analysis
    </p>
    """,
    unsafe_allow_html=True
)

# ---------------- SIDEBAR ----------------
st.sidebar.header("Controls")

risk_filter = st.sidebar.selectbox(
    "Risk Level",
    ["All", "High Risk", "Medium Risk", "Safe"]
)

search_wallet = st.sidebar.text_input("Search Wallet")

# ---------------- BACKEND CHECK ----------------
try:
    health = requests.get(f"{BACKEND_URL}/health", timeout=3)
    backend_ok = health.status_code == 200
except:
    backend_ok = False

if not backend_ok:
    st.error("Backend is not running. Start backend.py first.")
    st.stop()
else:
    st.success("Backend connected")

# ---------------- SESSION STATE INIT ----------------
if "analysis_done" not in st.session_state:
    st.session_state.analysis_done = False

if "results_df" not in st.session_state:
    st.session_state.results_df = None

# ---------------- AUTO RUN ANALYSIS ----------------
if not st.session_state.analysis_done:
    with st.spinner("Analyzing blockchain transactions..."):
        data = requests.get(f"{BACKEND_URL}/results").json()
        st.session_state.results_df = pd.DataFrame(data)
        st.session_state.analysis_done = True

# ---------------- MAIN CONTENT ----------------
if st.session_state.analysis_done:
    df = st.session_state.results_df

    # ---------------- METRICS ----------------
    st.markdown("## Summary")

    col1, col2, col3, col4 = st.columns(4)
    col1.metric("Total Flagged", len(df))
    col2.metric("High Risk", (df["score"] >= 7).sum())
    col3.metric("Medium Risk", ((df["score"] >= 3) & (df["score"] < 7)).sum())
    col4.metric("Peeling Chains", df["peeling_chain"].sum())

    # ---------------- RISK LEGEND ----------------
    st.markdown("### Risk Legend")

    c1, c2, c3 = st.columns(3)
    c1.markdown("🔴 **High Risk**  \nScore ≥ 7")
    c2.markdown("🟠 **Medium Risk**  \nScore 3–6")
    c3.markdown("🟢 **Safe**  \nScore < 3")

    st.success("✔ Analysis completed successfully")

    # ---------------- FILTER DATA ----------------
    filtered = df.copy()

    if risk_filter == "High Risk":
        filtered = filtered[filtered["score"] >= 7]
    elif risk_filter == "Medium Risk":
        filtered = filtered[(filtered["score"] >= 3) & (filtered["score"] < 7)]
    elif risk_filter == "Safe":
        filtered = filtered[filtered["score"] < 3]

    if search_wallet:
        filtered = filtered[
            filtered["wallet"].str.contains(search_wallet, case=False)
        ]

    # ---------------- RISK DISTRIBUTION ----------------
    # ---------------- ADD RISK CATEGORY FOR COLORING ----------------
    df["risk_level"] = pd.cut(
        df["score"],
        bins=[-1, 2.9, 6.9, 100],
        labels=["Safe", "Medium Risk", "High Risk"]
    )

    
    st.markdown("## Risk Distribution")

    fig = px.histogram(
        df,
        x="score",
        color="risk_level",
        nbins=10,
        labels={
            "score": "Suspicion Score",
            "risk_level": "Risk Level"
        },
        color_discrete_map={
            "High Risk": "#EF4444",     # red
            "Medium Risk": "#F59E0B",   # orange
            "Safe": "#10B981"           # green
        }
    )


    st.plotly_chart(fig, use_container_width=True)

    # ---------------- RISK COMPOSITION ----------------
    st.markdown("## Risk Composition")

    risk_counts = pd.cut(
        df["score"],
        bins=[-1, 2.9, 6.9, 100],
        labels=["Safe", "Medium Risk", "High Risk"]
    ).value_counts().reset_index()

    risk_counts.columns = ["Risk Level", "Count"]

    fig2 = px.pie(
        risk_counts,
        names="Risk Level",
        values="Count",
        color="Risk Level",
        color_discrete_map={
            "High Risk": "#EF4444",
            "Medium Risk": "#F59E0B",
            "Safe": "#10B981"
        }
    )

    st.plotly_chart(fig2, use_container_width=True)

    # ---------------- TABLE ----------------
    def color_risk(row):
        if row["score"] >= 7:
            return ["background-color: #4a1f1f"] * len(row)
        elif row["score"] >= 3:
            return ["background-color: #3a2f1a"] * len(row)
        else:
            return ["background-color: #1f3a2f"] * len(row)

    if filtered.empty:
        st.warning("No wallets match the selected filters.")
        st.stop()

    st.markdown("## Wallet Details (Risk Highlighted)")

    st.dataframe(
        filtered
        .sort_values("score", ascending=False)
        .style.apply(color_risk, axis=1),
        use_container_width=True
    )

    # ---------------- WALLET DRILL-DOWN ----------------
    st.markdown("## Wallet Drill-Down")

    selected_wallet = st.selectbox(
        "Select a wallet to inspect",
        filtered["wallet"].unique(),
        key="wallet_selector"
    )

    wallet_row = filtered[filtered["wallet"] == selected_wallet].iloc[0]

    d1, d2, d3 = st.columns(3)
    d1.metric("Suspicion Score", wallet_row["score"])
    d2.metric("Fan-Out", "Yes" if wallet_row["fan_out"] else "No")
    d3.metric("Fan-In", "Yes" if wallet_row["fan_in"] else "No")

    st.markdown(
        f"""
        **Peeling Chain:** {'Yes' if wallet_row['peeling_chain'] else 'No'}  
        **Wallet ID:** `{wallet_row['wallet']}`
        """
    )
