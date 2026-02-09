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
# UPLOAD
# =========================================================
uploaded_file = st.sidebar.file_uploader(
    "📂 Upload da base (Excel)",
    type=["xlsx"]
)

if uploaded_file is None:
    st.info("⬅️ Faça upload da base para iniciar.")
    st.stop()

# =========================================================
# LOAD DATA — AJUSTADO À SUA BASE
# =========================================================
@st.cache_data
def load_data(file):
    df = pd.read_excel(file)

    # Usa primeira coluna como data
    date_col = df.columns[0]

    # Remove linha de descrição (linha 0)
    df = df.iloc[1:].copy()

    # Renomeia data
    df = df.rename(columns={date_col: "Data"})
    df["Data"] = pd.to_datetime(df["Data"])

    # Limpa nomes das colunas
    df.columns = [c.strip().replace("\n", " ") for c in df.columns]

    # Converte valores para numérico
    for c in df.columns:
        if c != "Data":
            df[c] = pd.to_numeric(df[c], errors="coerce")

    return df.sort_values("Data").reset_index(drop=True)

df = load_data(uploaded_file)

# =========================================================
# CLASSES OFFSHORE (FIXAS)
# =========================================================
classes = {
    "Cash": "Cash",
    "High Yield": "High Yield",
    "Investment Grade": "Investment Grade",
    "Treasury 10y": "Treasury 10y",
    "Equity": "Equity"
}

# =========================================================
# RETURNS (base 100 → retorno diário)
# =========================================================
returns = df.set_index("Data").pct_change().dropna()

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
# PESOS
# =========================================================
pesos = pd.DataFrame({
    "Classe": classes.keys(),
    "Ultra Conservador": [40, 25, 25, 10, 0],
    "Conservador":       [25, 25, 25, 20, 5],
    "Moderado":          [15, 20, 25, 30, 10],
    "Moderado Arrojado": [10, 15, 20, 35, 20],
    "Arrojado":          [5, 10, 15, 40, 30],
}).set_index("Classe")

pesos = pesos.div(pesos.sum())

# =========================================================
# RISK FREE — TREASURY 10Y
# =========================================================
rf_col = "Treasury 10y"
rf_daily = returns[rf_col]

# =========================================================
# CARTEIRAS
# =========================================================
carteiras = {}

for p in perfis:
    carteiras[p] = (returns[list(classes.keys())] * pesos[p]).sum(axis=1)

carteiras = pd.DataFrame(carteiras)

# =========================================================
# PERFORMANCE
# =========================================================
st.subheader("📈 Performance das Carteiras")

perf = (1 + carteiras).cumprod() * 100

fig = go.Figure()
for c in perf.columns:
    fig.add_trace(go.Scatter(x=perf.index, y=perf[c], name=c))

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

fig_alloc = go.Figure()
for classe in pesos.index:
    fig_alloc.add_trace(go.Bar(
        x=pesos.columns,
        y=pesos.loc[classe] * 100,
        name=classe
    ))

fig_alloc.update_layout(
    barmode="stack",
    yaxis_title="Peso (%)",
    template="simple_white",
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

fig_corr.update_layout(height=600)
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

exp = {}

for c in classes.keys():
    exp[c] = st.number_input(
        f"Retorno esperado – {c} (%)",
        value=5.0
    ) / 100

forward = {}

for p in perfis:
    forward[p] = sum(pesos.loc[c, p] * exp[c] for c in classes.keys())

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
