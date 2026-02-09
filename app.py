import streamlit as st
import pandas as pd
import numpy as np
import plotly.graph_objects as go

# ======================================================
# CONFIGURAÇÃO DA PÁGINA
# ======================================================
st.set_page_config(
    page_title="Offshore Asset Allocation",
    layout="wide"
)

st.title("🌍 Offshore Asset Allocation")
st.caption(
    "Análise de alocação offshore em USD baseada em índices de mercado (base 100). "
    "Defina os pesos por perfil e avalie risco, retorno e performance histórica."
)

st.markdown("---")

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

CORES = ['#CBD5E1', '#94A3B8', '#64748B', '#475569', '#1E293B']

# ======================================================
# UPLOAD
# ======================================================
st.sidebar.header("Configurações")
arquivo = st.sidebar.file_uploader(
    "Upload da base offshore",
    type=["xlsx", "csv"]
)

if not arquivo:
    st.info("⬅️ Faça o upload da base para iniciar a análise.")
    st.stop()

# ======================================================
# LEITURA DA BASE
# ======================================================
df = pd.read_excel(
    arquivo,
    header=[0, 1],
    index_col=0,
    parse_dates=True
)

# Limpeza dos nomes das colunas
df.columns = pd.MultiIndex.from_tuples([
    (c[0].replace("\n", "").strip(), c[1].replace("\n", "").strip())
    for c in df.columns
])

df = df.apply(pd.to_numeric, errors="coerce").dropna(how="all")

# ======================================================
# JANELA DE ANÁLISE
# ======================================================
start, end = st.sidebar.slider(
    "Janela de análise",
    df.index.min().to_pydatetime(),
    df.index.max().to_pydatetime(),
    (df.index.min().to_pydatetime(), df.index.max().to_pydatetime())
)

df = df.loc[start:end]

# ======================================================
# RETORNOS E ANUALIZAÇÃO AUTOMÁTICA
# ======================================================
ret = df.pct_change().dropna()

freq_days = ret.index.to_series().diff().median().days
ann_factor = int(round(365 / freq_days))

# ======================================================
# IDENTIFICAÇÃO DO TREASURY 10Y (REFERÊNCIA)
# ======================================================
treasury_cols = [
    c for c in ret.columns
    if "TREASURY" in c[0].upper() or "10Y" in c[0].upper()
]

if treasury_cols:
    treasury_col = treasury_cols[0]
    rf_curve = (1 + ret[treasury_col]).cumprod() - 1
    rf_ann = (1 + rf_curve.iloc[-1]) ** (ann_factor / len(ret)) - 1
else:
    rf_curve = pd.Series(0.0, index=ret.index)
    rf_ann = 0.0

# ======================================================
# PESOS DAS CARTEIRAS
# ======================================================
st.subheader("🏗️ Alocação por Perfil")
st.caption("Pesos em %. A soma recomendada por perfil é 100%.")

df_pesos = pd.DataFrame({
    "Classe": [c[0] for c in ret.columns],
    "Ativo": [c[1] for c in ret.columns]
})

for p in perfis:
    df_pesos[p] = 0.0

pesos = st.data_editor(
    df_pesos,
    hide_index=True,
    use_container_width=True
)

# Validação visual das somas
somas = pesos[perfis].sum()
cols = st.columns(len(perfis))

for i, p in enumerate(perfis):
    if 99.5 <= somas[p] <= 100.5:
        cols[i].success(f"{p}: {somas[p]:.1f}%")
    else:
        cols[i].warning(f"{p}: {somas[p]:.1f}%")

# ======================================================
# CÁLCULO DAS CARTEIRAS
# ======================================================
metrics = {}
perf = {}

cov = ret.cov() * ann_factor

for p in perfis:
    w = pesos[p].values / 100
    r_p = ret.dot(w)

    r_ann = (1 + (1 + r_p).prod() - 1) ** (ann_factor / len(r_p)) - 1
    vol = np.sqrt(w.T @ cov @ w) if w.sum() > 0 else 0.0
    sharpe = (r_ann - rf_ann) / vol if vol > 0 else np.nan

    metrics[p] = {
        "Retorno Anualizado": r_ann,
        "Volatilidade": vol,
        "Sharpe (vs Treasury 10Y)": sharpe
    }

    perf[p] = (1 + r_p).cumprod() - 1

# ======================================================
# MÉTRICAS
# ======================================================
st.markdown("---")
st.subheader("📊 Métricas das Carteiras")

st.dataframe(
    pd.DataFrame(metrics).T.style.format({
        "Retorno Anualizado": "{:.2%}",
        "Volatilidade": "{:.2%}",
        "Sharpe (vs Treasury 10Y)": "{:.2f}"
    }),
    use_container_width=True
)

# ======================================================
# PERFORMANCE
# ======================================================
st.markdown("---")
st.subheader("📈 Performance Histórica")

fig = go.Figure()

if treasury_cols:
    fig.add_trace(go.Scatter(
        x=rf_curve.index,
        y=rf_curve,
