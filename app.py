import streamlit as st
import pandas as pd
import numpy as np
import plotly.graph_objects as go

# ===============================
# CONFIG
# ===============================
st.set_page_config(page_title="Offshore Asset Allocation", layout="wide")

CORES = ['#D1D5DB', '#9CA3AF', '#6B7280', '#4B5563', '#1C2C54']
COR_BENCH = "#64748b"

perfis = ["Ultra Conservador", "Conservador", "Moderado", "Mod Arroj", "Arrojado"]

ordem_classes = [
    "Cash", "Investment Grade", "Treasury 10Y",
    "High Yield", "Alternatives", "Equity"
]

# ===============================
# UPLOAD
# ===============================
st.sidebar.header("Configurações")
arquivo = st.sidebar.file_uploader("Upload Base Offshore", type=["csv", "xlsx"])

if not arquivo:
    st.stop()

# ===============================
# LOAD
# ===============================
if arquivo.name.endswith(".csv"):
    df = pd.read_csv(arquivo, header=[0,1], index_col=0, parse_dates=True)
else:
    df = pd.read_excel(arquivo, header=[0,1], index_col=0, parse_dates=True)

df = df.apply(pd.to_numeric, errors="coerce").dropna(how="all")

# ===============================
# JANELA
# ===============================
start, end = st.sidebar.slider(
    "Janela de Análise",
    df.index.min().to_pydatetime(),
    df.index.max().to_pydatetime(),
    (df.index.min().to_pydatetime(), df.index.max().to_pydatetime())
)

df = df.loc[start:end]

# ===============================
# RETORNOS & ANUALIZAÇÃO AUTOMÁTICA
# ===============================
ret = df.pct_change().dropna()

freq_days = ret.index.to_series().diff().median().days
ann_factor = int(round(365 / freq_days))

# ===============================
# IDENTIFICAÇÃO DAS SÉRIES
# ===============================
treasury_col = [c for c in ret.columns if c[0] == "Treasury 10Y"][0]

bench_cols = {
    "CPI": ("Benchmark", "CPI"),
    "Agg": ("Benchmark", "BBG Agg"),
    "MSCI": ("Equity", "MSCI World")
}

# ===============================
# BENCHMARKS
# ===============================
bench = {}

bench["CPI"] = (1 + ret[bench_cols["CPI"]]).cumprod() - 1
bench["Agg"] = (1 + ret[bench_cols["Agg"]]).cumprod() - 1

ret_agg = ret[bench_cols["Agg"]]
ret_msci = ret[bench_cols["MSCI"]]

bench["10/90"] = (1 + (0.1 * ret_msci + 0.9 * ret_agg)).cumprod() - 1
bench["20/80"] = (1 + (0.2 * ret_msci + 0.8 * ret_agg)).cumprod() - 1

# ===============================
# RISK-FREE ECONÔMICO
# ===============================
rf_curve = bench["Agg"] * 0
rf_curve[:] = (1 + ret[treasury_col]).cumprod() - 1
rf_ann = (1 + rf_curve.iloc[-1]) ** (ann_factor / len(ret)) - 1

# ===============================
# PESOS
# ===============================
st.subheader("🏗️ Pesos por Perfil")

df_pesos = pd.DataFrame({
    "Classe": [c[0] for c in ret.columns],
    "Ativo": [c[1] for c in ret.columns]
})

for p in perfis:
    df_pesos[p] = 0.0

pesos = st.data_editor(df_pesos, hide_index=True, use_container_width=True)

# ===============================
# CÁLCULOS
# ===============================
metrics = {}
perf = {}
cov = ret.cov() * ann_factor

for p in perfis:
    w = pesos[p].values / 100
    r_p = ret.dot(w)

    r_ann = (1 + (1 + r_p).prod() - 1) ** (ann_factor / len(r_p)) - 1
    vol = np.sqrt(w.T @ cov @ w)

    sharpe = (r_ann - rf_ann) / vol if vol > 0 else 0

    metrics[p] = {
        "Retorno Anualizado": r_ann,
        "Volatilidade": vol,
        "Sharpe (vs UST10)": sharpe
    }

    perf[p] = (1 + r_p).cumprod() - 1

# ===============================
# RESULTADOS
# ===============================
st.subheader("📊 Métricas das Carteiras")
st.dataframe(pd.DataFrame(metrics).T.style.format("{:.2%}"), use_container_width=True)

# ===============================
# PERFORMANCE
# ===============================
st.subheader("📈 Performance vs Benchmarks")

fig = go.Figure()

for b, serie in bench.items():
    fig.add_trace(go.Scatter(
        x=serie.index, y=serie,
        name=b, line=dict(dash="dot", color=COR_BENCH)
    ))

for i, p in enumerate(perfis):
    fig.add_trace(go.Scatter(
        x=perf[p].index, y=perf[p],
        name=p, line=dict(color=CORES[i], width=2.5)
    ))

fig.update_layout(
    template="simple_white",
    yaxis_tickformat=".1%",
    hovermode="x unified",
    height=600
)

st.plotly_chart(fig, use_container_width=True)
