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

        cpi_anual = (cpi_level.iloc[-1] / cpi_level.iloc[0])**(252/len(cpi_level)) - 1
        cpi_ret_diario = (1 + cpi_anual)**(1/252) - 1

        cpi_ret = pd.Series(cpi_ret_diario, index=df_raw.index)

        # ================= ATIVOS (TODOS, exceto CPI) =================
        df_assets = df_raw.drop(columns=["CPI"]).dropna(how="any")
        ret_assets = df_assets.pct_change().dropna()
        num_dias = len(ret_assets)

        cpi_ret = cpi_ret.loc[ret_assets.index]

        # ================= BENCHMARKS =================
        ret_agg = ret_assets["Bloomberg Global Aggregate"]
        ret_eq = ret_assets["Equity"]

        benchmarks = {
            "CPI": cpi_ret,
            "100% BBG Global Agg": ret_agg,
            "10% MSCI World + 90% Agg": 0.10 * ret_eq + 0.90 * ret_agg,
            "20% MSCI World + 80% Agg": 0.20 * ret_eq + 0.80 * ret_agg
        }

        curvas_bench = {}
        bench_anual = {}

        for b, r in benchmarks.items():
            curva = (1 + r).cumprod() - 1
            curvas_bench[b] = curva
            bench_anual[b] = (1 + curva.iloc[-1])**(252/num_dias) - 1

        # ================= PESOS =================
        st.subheader("🏗️ Definição de Pesos por Perfil")

        perfis = ["Ultra", "Conservative", "Moderate", "Growth", "Aggressive"]

        df_pesos = pd.DataFrame({"Ativo": ret_assets.columns})
        for p in perfis:
            df_pesos[p] = 0.0

        pesos = st.data_editor(df_pesos, hide_index=True, use_container_width=True)

        # ================= CÁLCULOS =================
        cov = ret_assets.cov() * 252
        perf_acum = pd.DataFrame(index=ret_assets.index)
        metrics = {}

        for p in perfis:
            w = pesos[p].values / 100
            r_p = ret_assets.dot(w)

            perf_acum[p] = (1 + r_p).cumprod() - 1
            r_anual = (1 + perf_acum[p].iloc[-1])**(252/num_dias) - 1
            vol = np.sqrt(w.T @ cov @ w)

            m = {
                "Retorno Anualizado": r_anual,
                "Volatilidade": vol
            }

            for b in benchmarks:
                m[f"Sharpe vs {b}"] = (r_anual - bench_anual[b]) / vol if vol > 0 else 0

            metrics[p] = m

        # ================= RESULTADOS =================
        st.markdown("---")
        st.subheader("📈 Resultados Consolidados")

        res = pd.DataFrame(metrics)

        st.dataframe(
            res.style
            .format("{:.2%}", subset=res.index.intersection(["Retorno Anualizado", "Volatilidade"]))
            .format("{:.2f}", subset=[i for i in res.index if "Sharpe" in i]),
            use_container_width=True
        )

        # ================= PERFORMANCE =================
        st.markdown("---")
        st.subheader("📊 Performance das Carteiras vs Benchmarks")

        fig = go.Figure()

        for b, curva in curvas_bench.items():
            fig.add_trace(go.Scatter(
                x=curva.index,
                y=curva,
                name=b,
                line=dict(color=CORES_BENCH[b], dash="dot", width=1.5)
            ))

        for i, p in enumerate(perfis):
            fig.add_trace(go.Scatter(
                x=perf_acum.index,
                y=perf_acum[p],
                name=p,
                line=dict(color=CORES_LIFETIME[i], width=3 if p == "Aggressive" else 2)
            ))

        fig.update_layout(
            template="simple_white",
            yaxis_tickformat=".1%",
            hovermode="x unified",
            height=650
        )

        st.plotly_chart(fig, use_container_width=True)

    except Exception as e:
        st.error(f"Erro: {e}")
