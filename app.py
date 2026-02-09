import streamlit as st
import pandas as pd
import numpy as np
import plotly.graph_objects as go

# ======================================================
# CONFIG
# ======================================================
st.set_page_config(page_title="Offshore Asset Allocation", layout="wide")

st.title("Offshore Asset Allocation")
st.caption("Análise de alocação offshore em USD • índices base 100 • Treasury 10Y como risk-free")

# ======================================================
# PERFIS
# ======================================================
perfis = [
    "Ultra Conservador",
    "Conservador",
    "Moderado",
    "Mod Arroj",
    "Arrojado"
]

# ======================================================
# SIDEBAR
# ======================================================
st.sidebar.header("Configurações")

arquivo = st.sidebar.file_uploader(
    "Upload da base offshore",
    type=["xlsx", "csv"]
)

if arquivo is None:
    st.info("Faça o upload da base para iniciar a análise.")
    st.stop()

# ======================================================
# LEITURA DOS DADOS
# ======================================================
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

# ======================================================
# JANELA DE ANÁLISE
# ======================================================
inicio, fim = st.sidebar.slider(
    "Janela de análise",
    min_value=df.index.min().to_pydatetime(),
    max_value=df.index.max().to_pydatetime(),
    value=(df.index.min().to_pydatetime(), df.index.max().to_pydatetime())
)

df = df.loc[inicio:fim]

# ======================================================
# RETORNOS E ANUALIZAÇÃO
# ======================================================
ret = df.pct_change().dropna()

freq_days = ret.index.to_series().diff().median().days
ann_factor = int(round(365 / freq_days))

# ======================================================
# TREASURY 10Y (RISK-FREE)
# ======================================================
treasury_cols = [
    c for c in ret.columns
    if "TREASURY" in c[0].upper() or "10Y" in c[0].upper()
]

if treasury_cols:
    rf = ret[treasury_cols[0]]
    rf_curve = (1 + rf).cumprod() - 1
    rf_ann = (1 + rf_curve.iloc[-1]) ** (ann_factor / len(rf)) - 1
else:
    rf_curve = pd.Series(0.0, index=ret.index)
    rf_ann = 0.0

# ======================================================
# PESOS DAS CARTEIRAS
# ======================================================
st.markdown("---")
st.subheader("Alocação por Perfil")
st.caption("Pesos em %. A soma recomendada por perfil é 100%.")

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

# ======================================================
# ALOCAÇÃO POR CLASSE DE ATIVO
# ======================================================
st.markdown("---")
st.subheader("Alocação por Classe de Ativo")

aloc_classe = {}
for p in perfis:
    aloc_classe[p] = pesos.groupby("Classe")[p].sum()

df_aloc = pd.DataFrame(aloc_classe).fillna(0)

st.dataframe(
    df_aloc.style.format("{:.1f}%"),
    use_container_width=True
)

fig_alloc = go.Figure()
for classe in df_aloc.index:
    fig_alloc.add_trace(
        go.Bar(
            name=classe,
            x=df_aloc.columns,
            y=df_aloc.loc[classe]
        )
    )

fig_alloc.update_layout(
    barmode="stack",
    template="simple_white",
    yaxis_title="Peso (%)",
    height=420
)

st.plotly_chart(fig_alloc, use_container_width=True)

# ======================================================
# CÁLCULO DAS CARTEIRAS
# ======================================================
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
        "Sharpe (vs Treasury 10Y)": sharpe
    }

    perf[p] = (1 + r).cumprod() - 1

# ======================================================
# MÉTRICAS DAS CARTEIRAS
# ======================================================
st.markdown("---")
st.subheader("Métricas das Carteiras")

df_metrics = pd.DataFrame(metrics).T

st.dataframe(
    df_metrics.style.format({
        "Retorno Anualizado": "{:.2%}",
        "Volatilidade": "{:.2%}",
        "Sharpe (vs Treasury 10Y)": "{:.2f}"
    }),
    use_container_width=True
)

# ======================================================
# PERFORMANCE DAS CARTEIRAS
# ======================================================
st.markdown("---")
st.subheader("Performance das Carteiras")
st.caption("Curvas acumuladas em USD • base 100")

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
    height=450
)

st.plotly_chart(fig, use_container_width=True)
