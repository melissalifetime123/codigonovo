import streamlit as st
import pandas as pd
import numpy as np
import plotly.graph_objects as go
import plotly.express as px

# =========================================================
# CONFIG
# =========================================================
st.set_page_config(
    page_title="Asset Allocation Offshore",
    layout="wide"
)

st.title("🌍 Asset Allocation – Offshore")

# =========================================================
# UPLOAD BASE
# =========================================================
st.sidebar.header("📂 Base de Dados")

uploaded_file = st.sidebar.file_uploader(
    "Faça upload da base (Excel)",
    type=["xlsx"]
)

if uploaded_file is None:
    st.info("⬅️ Faça upload da base de dados para iniciar as análises.")
    st.stop()

# =========================================================
# LOAD DATA (ROBUSTO)
# =========================================================
@st.cache_data
def load_data(file):
    df = pd.read_excel(file)

    # Detecta coluna de data automaticamente
    date_candidates = [c for c in df.columns if str(c).lower() in ["data", "date"]]

    if not date_candidates:
        raise ValueError(
            "❌ Nenhuma coluna de data encontrada. "
            "A base precisa ter uma coluna chamada 'Data' ou 'Date'."
        )

    date_col = date_candidates[0]
    df[date_col] = pd.to_datetime(df[date_col])
    df = df.sort_values(date_col)

    df = df.rename(columns={date_col: "Data"})
    return df

try:
    df = load_data(uploaded_file)
except Exception as e:
    st.error(str(e))
    st.stop()

# =========================================================
# IDENTIFICA COLUNAS
# =========================================================
meta_cols = ["Data", "Classe"]
ret_cols = [c for c in df.columns if c not in meta_cols]

if "Classe" not in df.columns:
    st.error("❌ A base precisa conter uma coluna chamada 'Classe'.")
    st.stop()

returns = (
    df[["Data"] + ret_cols]
    .set_index("Data")
    .pct_change()
    .dropna()
)

# =========================================================
# CLASSES
# =========================================================
classes = (
    df[["Classe"] + ret_cols]
    .drop_duplicates()
    .set_index("Classe")
)

# =========================================================
# PERFIS
# =========================================================
perfis = [
    "Ultra Conservador",
    "Conservador",
    "Moderado",
    "Moderado Arrojado",
    "Arrojado"
]

# =========================================================
# PESOS (OFFSHORE)
# =========================================================
pesos = pd.DataFrame({
    "Classe": classes.index,
    "Ultra Conservador": [40, 25, 25, 10, 0],
    "Conservador":       [25, 25, 25, 20, 5],
    "Moderado":          [15, 20, 25, 30, 10],
    "Moderado Arrojado": [10, 15, 20, 35, 20],
    "Arrojado":          [5, 10, 15, 40, 30],
}, index=classes.index)

pesos[perfis] = pesos[perfis].div(pesos[perfis].sum()) * 100

# =========================================================
# RISK FREE — TREASURY 10Y
# =========================================================
rf_candidates = [c for c in returns.columns if "treasury" in c.lower() and "10" in c]

if not rf_candidates:
    st.error("❌ Série Treasury 10Y não encontrada na base.")
    st.stop()

rf_col = rf_candidates[0]
rf_daily = returns[rf_col]

# =========================================================
# CARTEIRAS
# =========================================================
carteiras = {}

for p in perfis:
    w = pesos[p] / 100
    ativos = w.index.intersection(returns.columns)
    carteiras[p] = (returns[ativos] @ w.loc[ativos]).dropna()

carteiras = pd.DataFrame(carteiras)

# =========================================================
# PERFORMANCE
# =========================================================
st.subheader("📈 Performance das Carteiras")

perf = (1 + carteiras).cumprod() * 100

fig = go.Figure()
for c in perf.columns:
    fig.add_trace(go.Scatter(
        x=perf.index,
        y=perf[c],
        name=c
    ))

fig.update_layout(
    template="simple_white",
    yaxis_title="Base 100",
    height=450
)

st.plotly_chart(fig, use_container_width=True)

# =========================================================
# ALOCAÇÃO
# =========================================================
st.subheader("🧱 Alocação por Classe de Ativo")

alloc = pesos.groupby("Classe")[perfis].sum()

fig_alloc = go.Figure()
for classe in alloc.index:
    fig_alloc.add_trace(go.Bar(
        x=alloc.columns,
        y=alloc.loc[classe],
        name=classe
    ))

fig_alloc.update_layout(
    barmode="stack",
    template="simple_white",
    yaxis_title="Peso (%)",
    height=420
)

st.plotly_chart(fig_alloc, use_container_width=True)

# =========================================================
# MATRIZ DE CORRELAÇÃO
# =========================================================
st.subheader("🔗 Matriz de Correlação")

corr = returns.corr()

fig_corr = px.imshow(
    corr,
    color_continuous_scale="RdYlGn",
    zmin=-1,
    zmax=1
)

fig_corr.update_layout(height=650)
st.plotly_chart(fig_corr, use_container_width=True)

# =========================================================
# EFICIÊNCIA HISTÓRICA
# =========================================================
st.subheader("🎯 Análise de Eficiência (Histórico)")

ann = 252

stats = pd.DataFrame(index=carteiras.columns)
stats["Retorno (%)"] = carteiras.mean() * ann * 100
stats["Volatilidade (%)"] = carteiras.std() * np.sqrt(ann) * 100
stats["Sharpe"] = (
    (carteiras.mean() - rf_daily.mean()) /
    carteiras.std()
) * np.sqrt(ann)

st.dataframe(stats.style.format("{:.2f}"))

fig_eff = px.scatter(
    stats,
    x="Volatilidade (%)",
    y="Retorno (%)",
    text=stats.index
)

fig_eff.update_traces(textposition="top center")
fig_eff.update_layout(template="simple_white", height=450)

st.plotly_chart(fig_eff, use_container_width=True)

# =========================================================
# EFICIÊNCIA FORWARD
# =========================================================
st.subheader("🚀 Análise de Eficiência (Forward-looking)")

exp_returns = {}

for classe in pesos.index:
    exp_returns[classe] = st.number_input(
        f"Retorno esperado – {classe} (%)",
        value=5.0
    ) / 100

forward = {}

for p in perfis:
    w = pesos[p] / 100
    forward[p] = sum(w[c] * exp_returns.get(c, 0) for c in w.index)

df_fwd = pd.DataFrame.from_dict(
    forward,
    orient="index",
    columns=["Retorno Esperado (%)"]
) * 100

st.dataframe(df_fwd.style.format("{:.2f}"))

fig_fwd = px.scatter(
    df_fwd,
    y="Retorno Esperado (%)",
    x=df_fwd.index,
    text=df_fwd.index
)

fig_fwd.update_traces(textposition="top center")
fig_fwd.update_layout(template="simple_white", height=400)

st.plotly_chart(fig_fwd, use_container_width=True)
