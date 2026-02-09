import streamlit as st
import pandas as pd
import numpy as np
import plotly.graph_objects as go

# ===============================
# CONFIG
# ===============================
st.set_page_config(page_title="Offshore Asset Allocation", layout="wide")

st.title("Offshore Asset Allocation")
st.caption("Análise de carteiras offshore em USD • índices base 100")

# ===============================
# PERFIS
# ===============================
perfis = [
    "Ultra Conservador",
    "Conservador",
    "Moderado",
    "Mod Arroj",
    "Arrojado"
]

# ===============================
# SIDEBAR
# ===============================
st.sidebar.header("Configurações")

arquivo = st.sidebar.file_uploader(
    "Upload da base",
    type=["xlsx", "csv"]
)

if arquivo is None:
    st.info("Faça o upload da base para iniciar.")
    st.stop()

# ===============================
# LEITURA DOS DADOS
# ===============================
df = pd.read_excel(
    arquivo,
    header=[0, 1],
    index_col=0,
    parse_dates=True
)

df.columns = pd.MultiIndex.from_tuples(
    [(str(a).strip(), str(b).strip()) for a, b in df.columns]
)

df = df.apply(pd.to_numeric, errors="coerce").dropna(how="all")

# ===============================
# JANELA DE TEMPO
# ===============================
inicio, fim = st.sidebar.slider(
    "Janela de análise",
    min_value=df.index.min().to_pydatetime(),
    max_value=df.index.max().to_pydatetime(),
    value=(df.index.min().to_pydatetime(), df.index.max().to_pydatetime())
)

df = df.loc[inicio:fim]

# ===============================
# RETORNOS
# ===============================
ret = df.pct_change().dropna()

freq = ret.index.to_series().diff().median().days
ann_factor = int(round(365 / freq))

# ===============================
# TREASURY 10Y (RISK FREE)
# ===============================
treasury_cols = [c for c in ret.columns if "TREASURY" in c[0].upper() or "10Y" in c[0].upper()]

if treasury_cols:
    rf = ret[treasury_cols[0]]
    rf_curve = (1 + rf).cumprod() - 1
    rf_ann = (1 + rf_curve.iloc[-1]) ** (ann_factor / len(rf)) - 1
else:
    rf_curve = pd.Series(0.0, index=ret.index)
    rf_ann = 0.0

# ===============================
# PESOS
# ===============================
st.subheader("Alocação por Perfil")

pesos = pd.DataFrame({
    "Classe": [c[0] for c in ret.columns],
    "Ativo": [c[1] for c in ret.columns]
})

for p in perfis:
    pesos[p] = 0.0

pesos = st.data_editor(pesos, hide_index=True, use_container_width=True)

somas = pesos[perfis].sum()
cols = st.columns(len(perfis))

for i, p in enumerate(perfis):
    if 99.5 <= somas[p] <= 100.5:
        cols[i].success(f"{p}: {somas[p]:.1f}%")
    else:
        cols[i].warning(f"{p}: {somas[p]:.1f}%")

# ===============================
# CÁLCULOS
# ===============================
metrics = {}
perf = {}

cov = ret.cov() * ann_factor

for p in perfis:
    w = pesos[p].values / 100
    r = ret.dot(w)

    if w.sum() > 0:
        r_ann = (1 + (1 + r).prod() - 1) ** (ann_factor / len(r)) - 1
        vol = np.sqrt(w.T @ cov @ w)
        sharpe = (r_ann - rf_ann) / vol if vol > 0 else np.nan
    else:
        r_ann = 0.0
        vol = 0.0
        sharpe = np.nan

    metrics[p] = {
        "Retorno Anualizado": r_ann,
        "Volatilidade": vol,
        "Sharpe": sharpe
    }

    perf[p] = (1 + r).cumprod() - 1

# ===============================
# MÉTRICAS
# ===============================
st.subheader("Métricas")

df_m = pd.DataFrame(metrics).T

st.dataframe(
    df_m.style.format({
        "Retorno Anualizado": "{:.2%}",
        "Volatilidade": "{:.2%}",
        "Sharpe": "{:.2f}"
    }),
    use_container_width=True
)

# ===============================
# PERFORMANCE
# ===============================
st.subheader("Performance Histórica")

fig = go.Figure()

fig.add_trace(
    go.Scatter(
        x=rf_curve.index,
        y=rf_curve,
        name="Treasury 10Y",
        line=dict(dash="dot")
    )
)

for p in perfis:
    fig.add_trace(
        go.Scatter(
            x=perf[p].index,
            y=perf[p],
            name=p
        )
    )

fig.update_layout(
    template="simple_white",
    hovermode="x unified",
    yaxis_tickformat=".1%",
    height=420
)

st.plotly_chart(fig, use_container_width=True)
