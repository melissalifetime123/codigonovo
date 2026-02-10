import streamlit as st
import pandas as pd
import numpy as np
import plotly.graph_objects as go

# ================= CONFIG =================
st.set_page_config(page_title="Asset Allocation | Offshore", layout="wide")

CORES_LIFETIME = ['#D1D5DB', '#9CA3AF', '#6B7280', '#4B5563', '#1C2C54']
CORES_BENCH = {
    "CPI": "#64748B",
    "100% BBG Global Agg": "#334155",
    "10% MSCI World + 90% Agg": "#1E293B",
    "20% MSCI World + 80% Agg": "#020617"
}

st.markdown("""
<style>
[data-testid="stDataFrame"] { width: 100%; }
th { min-width: 110px !important; text-align: center !important; }
.metric-container {
    background-color: #F8F9FA;
    padding: 15px;
    border-radius: 10px;
    border-left: 5px solid #1C2C54;
}
</style>
""", unsafe_allow_html=True)

st.title("🌍 Asset Allocation | Offshore")

st.sidebar.header("Configurações")
arquivo = st.sidebar.file_uploader("Upload da Base Offshore", type=["xlsx", "csv"])

# ================= LOAD =================
if arquivo:
    try:
        # ---------- leitura ----------
        if arquivo.name.endswith(".csv"):
            df_raw = pd.read_csv(arquivo, index_col=0, parse_dates=True)
        else:
            df_raw = pd.read_excel(arquivo, index_col=0, parse_dates=True)

        df_raw = df_raw.apply(pd.to_numeric, errors="coerce")

        # ================= CPI (benchmark) =================
        cpi_level = df_raw["CPI"].dropna()

        cpi_anual = (c_
