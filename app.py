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

    start_date = None
    end_date = None

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
            if isinstance(periodo, tuple) and len(periodo) == 2:
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
            options=list(edited_df.columns[1:]),
            value="Moderado"
        )

        # ------------------------------
        # CÁLCULOS
        # ------------------------------
        returns = df.pct_change().dropna()
        weights = edited_df.set_index("Classe")[perfil] / 100

        portfolio_return = sum(
            returns[col] * weights[col]
            for col in weights.index if col in returns.columns
        )

        benchmarks = calculate_benchmarks(returns)

        # ------------------------------
        # KPIs
        # ------------------------------
        c1, c2, c3 = st.columns(3)

        with c1:
            total_ret = (1 + portfolio_return).prod() - 1
            st.metric("Retorno no Período", f"{total_ret:.2%}")

        with c2:
            vol = portfolio_return.std() * np.sqrt(12)
            st.metric("Volatilidade (a.a.)", f"{vol:.2%}")

        with c3:
            for name, series in benchmarks.items():
                b_ret = (1 + series).prod() - 1
                st.caption(f"{name}: {b_ret:.2%}")

        # ------------------------------
        # GRÁFICOS
        # ------------------------------
        tab1, tab2 = st.tabs(["📈 Performance", "🧱 Composição"])

        with tab1:
            fig = go.Figure()

            cum_port = (1 + portfolio_return).cumprod() * 100
            fig.add_trace(go.Scatter(
                x=cum_port.index,
                y=cum_port,
                name=f"Carteira {perfil}",
                line=dict(width=4, color="#1C2C54")
            ))

            for name, series in benchmarks.items():
                cum_b = (1 + series).cumprod() * 100
                fig.add_trace(go.Scatter(
                    x=cum_b.index,
                    y=cum_b,
                    name=name,
                    line=dict(dash='dot', width=2)
                ))

            fig.update_layout(
                template="simple_white",
                hovermode="x unified",
                title="Evolução Patrimonial (Base 100)"
            )

            st.plotly_chart(fig, use_container_width=True)

        with tab2:
            comp_df = pd.DataFrame(index=df.index)

            for asset, w in weights.items():
                if asset in df.columns and w > 0:
                    comp_df[asset] = w * (df[asset] / df[asset].iloc[0]) * 100

            fig_area = go.Figure()
            for col in comp_df.columns:
                fig_area.add_trace(go.Scatter(
                    x=comp_df.index,
                    y=comp_df[col],
                    stackgroup='one',
                    name=col,
                    mode='none'
                ))

            fig_area.update_layout(
                template="simple_white",
                title="Exposição por Ativo"
            )

            st.plotly_chart(fig_area, use_container_width=True)

else:
    st.info("Faça upload do ficheiro para começar.")
