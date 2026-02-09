import streamlit as st
import pandas as pd
import numpy as np
import plotly.graph_objects as go
import plotly.express as px

# =========================
# CONFIG
# =========================
st.set_page_config(
    page_title="Asset Allocation Offshore",
    layout="wide"
)

st.title("📊 Asset Allocation | Offshore")

# =========================
# FUNÇÕES AUXILIARES
# =========================

@st.cache_data
def load_data(file):
    if file.name.endswith(".csv"):
        df = pd.read_csv(file)
    else:
        df = pd.read_excel(file)

    # Detecta coluna de data automaticamente
    date_col = None
    for c in df.columns:
        if "date" in c.lower() or "data" in c.lower():
            date_col = c
            break

    if date_col is None:
        st.error("❌ Nenhuma coluna de data encontrada.")
        st.stop()

    df[date_col] = pd.to_datetime(df[date_col])
    df = df.sort_values(date_col)
    df = df.set_index(date_col)

    return df


def calc_returns(price_df):
    return price_df.pct_change().dropna()


def annualize_return(r, freq=252):
    return (1 + r.mean()) ** freq - 1


def annualize_vol(r, freq=252):
    return r.std() * np.sqrt(freq)


def sharpe_ratio(r, rf):
    excess = r.sub(rf, axis=0)
    return annualize_return(excess) / annualize_vol(excess)


# =========================
# SIDEBAR
# =========================

st.sidebar.header("⚙️ Configurações")

uploaded_file = st.sidebar.file_uploader(
    "Upload da Base Master",
    type=["xlsx", "csv"]
)

if uploaded_file is None:
    st.info("⬅️ Faça upload da base para começar")
    st.stop()

df = load_data(uploaded_file)

# =========================
# MAPEAMENTO DE CLASSES
# =========================

class_map = {
    "Cash": ["US:USG_EFFR"],
    "High Yield": ["US:HYG"],
    "Investment Grade": ["IE:AGGU"],
    "Treasury 10y": ["IE:IE00BYSZ5V04"],
    "Equity": ["US:MSCI_WORLD"],
    "Alternatives": []  # placeholder
}

# Filtra colunas existentes
assets = {
    k: [c for c in v if c in df.columns]
    for k, v in class_map.items()
}

price_df = df[[c for cols in assets.values() for c in cols]]

returns = calc_returns(price_df)

# Risk-free = Treasury 10Y
rf_series = returns[assets["Treasury 10y"][0]] if assets["Treasury 10y"] else returns.mean(axis=1) * 0

# =========================
# PERFIS OFFSHORE
# =========================

profiles = {
    "Ultra Conservador": {
        "Cash": 0.30,
        "Investment Grade": 0.40,
        "Treasury 10y": 0.30
    },
    "Conservador": {
        "Cash": 0.20,
        "Investment Grade": 0.40,
        "Equity": 0.40
    },
    "Moderado": {
        "Investment Grade": 0.30,
        "Equity": 0.70
    },
    "Moderado Arrojado": {
        "Equity": 0.85,
        "High Yield": 0.15
    },
    "Arrojado": {
        "Equity": 1.00
    }
}

# =========================
# CARTEIRAS
# =========================

portfolio_returns = {}

for p, weights in profiles.items():
    r = 0
    for cls, w in weights.items():
        if assets[cls]:
            r += returns[assets[cls]].mean(axis=1) * w
    portfolio_returns[p] = r

portfolio_df = pd.DataFrame(portfolio_returns)

# =========================
# RESULTADOS CONSOLIDADOS
# =========================

st.subheader("📌 Resultados Consolidados")

stats = pd.DataFrame(index=["Retorno Anualizado", "Volatilidade", "Sharpe"])

stats.loc["Retorno Anualizado"] = annualize_return(portfolio_df)
stats.loc["Volatilidade"] = annualize_vol(portfolio_df)
stats.loc["Sharpe"] = sharpe_ratio(portfolio_df, rf_series)

st.dataframe(stats.style.format("{:.2%}"))

# =========================
# ALOCAÇÃO POR CLASSE
# =========================

st.subheader("🏢 Alocação por Classe de Ativo")

alloc_df = pd.DataFrame(profiles).fillna(0)

fig_alloc = px.bar(
    alloc_df.T,
    barmode="stack"
)
st.plotly_chart(fig_alloc, use_container_width=True)

# =========================
# PERFORMANCE DAS CARTEIRAS
# =========================

st.subheader("📈 Performance das Carteiras")

cum_perf = (1 + portfolio_df).cumprod() - 1

fig_perf = go.Figure()
for c in cum_perf.columns:
    fig_perf.add_trace(go.Scatter(
        x=cum_perf.index,
        y=cum_perf[c],
        name=c
    ))

st.plotly_chart(fig_perf, use_container_width=True)

# =========================
# ESTATÍSTICAS DOS ATIVOS
# =========================

st.subheader("📊 Estatísticas das Séries Individuais")

asset_stats = pd.DataFrame({
    "Retorno": annualize_return(returns),
    "Vol": annualize_vol(returns),
    "Sharpe": sharpe_ratio(returns, rf_series)
})

st.dataframe(asset_stats.style.format("{:.2%}"))

# =========================
# MATRIZ DE CORRELAÇÃO
# =========================

st.subheader("🎯 Matriz de Correlação")

corr = returns.corr()

fig_corr = px.imshow(
    corr,
    color_continuous_scale="RdYlGn",
    zmin=-1,
    zmax=1
)

st.plotly_chart(fig_corr, use_container_width=True)

# =========================
# EFICIÊNCIA HISTÓRICA
# =========================

st.subheader("🔎 Análise de Eficiência (Histórico)")

eff_df = pd.DataFrame({
    "Retorno": annualize_return(portfolio_df),
    "Risco": annualize_vol(portfolio_df)
})

fig_eff = px.scatter(
    eff_df,
    x="Risco",
    y="Retorno",
    text=eff_df.index
)

st.plotly_chart(fig_eff, use_container_width=True)

# =========================
# EFICIÊNCIA FORWARD-LOOKING
# =========================

st.subheader("🚀 Análise de Eficiência (Forward-looking)")

st.info("📌 Estrutura pronta. Retornos esperados podem ser adicionados manualmente futuramente.")

