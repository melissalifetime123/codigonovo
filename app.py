import streamlit as st
import pandas as pd
import numpy as np
import plotly.graph_objects as go
import datetime
from dateutil.relativedelta import relativedelta

# ======================================================
# CONFIGURAÇÃO DA PÁGINA
# ======================================================
st.set_page_config(page_title="Offshore Portfolio Analytics", layout="wide")

st.markdown("""
<style>
[data-testid="stDataFrame"] { width: 100%; }
h1, h2, h3 { color: #1C2C54; font-family: 'Segoe UI', sans-serif; }
.stTabs [data-baseweb="tab-list"] { gap: 24px; }
.stTabs [data-baseweb="tab"] {
    height: 50px;
    background-color: #f0f2f6;
    border-radius: 4px;
    padding: 10px;
}
.stTabs [aria-selected="true"] {
    background-color: #1C2C54 !important;
    color: white !important;
}
</style>
""", unsafe_allow_html=True)

# ======================================================
# FUNÇÕES
# ======================================================
@st.cache_data
def load_offshore_data(file):
    df = pd.read_excel(file)
    df.columns = [str(c).replace('\n', ' ').strip() for c in df.columns]
    df['Date'] = pd.to_datetime(df['Date'], errors='coerce')
    df = df.dropna(subset=['Date']).sort_values('Date').set_index('Date')
    return df.apply(pd.to_numeric, errors='coerce').ffill()


def calculate_benchmarks(returns):
    benchmarks = {}

    if 'CPI' in returns.columns:
        benchmarks['CPI'] = returns['CPI']

    if 'Bloomberg Global Aggregate' in returns.columns:
        benchmarks['100% BBG Global Agg'] = returns['Bloomberg Global Aggregate']

    if {'Equity', 'Bloomberg Global Aggregate'}.issubset(returns.columns):
        benchmarks['10% MSCI World + 90% BBG Agg'] = (
            0.10 * returns['Equity'] +
            0.90 * returns['Bloomberg Global Aggregate']
        )
        benchmarks['20% MSCI World + 80% BBG Agg'] = (
            0.20 * returns['Equity'] +
            0.80 * returns['Bloomberg Global Aggregate']
        )

    return benchmarks

# ======================================================
# SIDEBAR
# ======================================================
with st.sidebar:
    st.title("📂 Configurações")
    uploaded_file = st.file_uploader("Upload do ficheiro database.xlsx", type=["xlsx"])

    start_date, end_date = None, None

    if uploaded_file:
        df_temp = load_offshore_data(uploaded_file)
        min_db = df_temp.index.min().to_pydatetime()
        max_db = df_temp.index.max().to_pydatetime()

        timeframe = st.radio(
            "Escolha o período:",
            ["Máximo", "YTD", "12 Meses", "24 Meses", "Personalizado"],
            index=2
        )

        if timeframe == "Máximo":
            start_date, end_date = min_db, max_db
        elif timeframe == "YTD":
            start_date = datetime.datetime(max_db.year, 1, 1)
            end_date = max_db
        elif timeframe == "12 Meses":
            start_date = max_db - relativedelta(months=12)
            end_date = max_db
        elif timeframe == "24 Meses":
            start_date = max_db - relativedelta(months=24)
            end_date = max_db
        elif timeframe == "Personalizado":
            periodo = st.date_input(
                "Selecione o intervalo:",
                value=(min_db, max_db),
                min_value=min_db,
                max_value=max_db
            )
            if isinstance(periodo, tuple):
                start_date, end_date = periodo

        if start_date and end_date:
            st.info(f"📍 {start_date:%d/%m/%Y} → {end_date:%d/%m/%Y}")

# ======================================================
# MAIN
# ======================================================
if uploaded_file and start_date and end_date:
    df = load_offshore_data(uploaded_file)
    df = df.loc[start_date:end_date]

    if df.empty:
        st.warning("Sem dados para o período.")
    else:
        st.title("📊 Análise de Portfólio Offshore")

        # ------------------------------
        # ALOCAÇÃO
        # ------------------------------
        perfis_df = pd.DataFrame({
            "Classe": ['Cash', 'High Yield', 'Investment Grade', 'Treasury 10y', 'Equity', 'Alternatives'],
            "Ultra Conservador": [90, 0, 10, 0, 0, 0],
            "Conservador": [60, 0, 30, 10, 0, 0],
            "Moderado": [20, 10, 30, 10, 20, 10],
            "Arrojado": [5, 15, 15, 5, 45, 15],
            "Agressivo": [0, 15, 5, 0, 60, 20]
        })

        edited_df = st.data_editor(perfis_df, hide_index=True, use_container_width=True)

        perfil = st.select_slider(
            "Selecione o perfil:",
            options=edited_df.columns[1:],
            valu
