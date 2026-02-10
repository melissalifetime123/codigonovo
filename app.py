import streamlit as st
import pandas as pd
import numpy as np
import plotly.graph_objects as go

# ================== CONFIG ==================
st.set_page_config(page_title="Portfolio Analytics | Offshore", layout="wide")

CORES_LIFETIME = ['#D1D5DB', '#9CA3AF', '#6B7280', '#4B5563', '#1C2C54']
COR_BENCH = '#64748B'

st.markdown("""
<style>
[data-testid="stDataFrame"] { width: 100%; }
th { min-width: 110px !important; text-align: center !important; }
.metric-container {
    background-color: #F8F9FA;
    padding: 15px;
    border-radius: 10px;
    border-left: 5px solid #1C2C54;
    margin-top: 55px;
}
</style>
""", unsafe_allow_html=True)

st.title("🌍 Asset Allocation | Offshore")

st.sidebar.header("Configurações")
arquivo = st.sidebar.file_uploader("Upload da Base Offshore", type=["xlsx", "csv"])

# ================== LOAD ==================
if arquivo:
    try:
        if arquivo.name.endswith(".csv"):
            df = pd.read_csv(arquivo, index_col=0, parse_dates=True)
        else:
            df = pd.read_excel(arquivo, index_col=0, parse_dates=True)

        df = df.apply(pd.to_numeric, errors="coerce").dropna(how="all")
        ret = df.pct_change().dropna()
        num_dias = len(ret)

        # ================== BENCHMARKS ==================
        ret_cpi = ret["CPI"]
        ret_agg = ret["Bloomberg Global Aggregate"]
        ret_eq = ret["Equity"]  # MSCI World

        benchmarks = {
            "CPI": ret_cpi,
            "100% BBG Global Agg": ret_agg,
            "10% MSCI World + 90% Agg": 0.10 * ret_eq + 0.90 * ret_agg,
            "20% MSCI World + 80% Agg": 0.20 * ret_eq + 0.80 * ret_agg
        }

        bench_sel = st.sidebar.selectbox("Benchmark", list(benchmarks.keys()))
        ret_bench = benchmarks[bench_sel]

        curva_bench = (1 + ret_bench).cumprod() - 1
        bench_anual = (1 + curva_bench.iloc[-1]) ** (252 / num_dias) - 1

        # ================== PESOS ==================
        st.subheader("🏗️ Definição de Pesos por Perfil")

        perfis = ["Ultra", "Conservative", "Moderate", "Growth", "Aggressive"]

        df_pesos = pd.DataFrame({
            "Classe": df.columns,
            "Ativo": df.columns
        })

        for p in perfis:
            df_pesos[p] = 0.0

        pesos = st.data_editor(df_pesos, hide_index=True, use_container_width=True)

        # ================== CÁLCULOS ==================
        metrics = {}
        perf_acum = pd.DataFrame(index=ret.index)
        risk_decomp = {}
        cov = ret.cov() * 252

        for p in perfis:
            w = pesos[p].values / 100
            r_p = ret.dot(w)

            r_anual = (1 + (1 + r_p).prod() - 1) ** (252 / num_dias) - 1
            vol = np.sqrt(w.T @ cov @ w)

            sharpe = (r_anual - bench_anual) / vol if vol > 0 else 0

            metrics[p] = {
                "Retorno Anualizado": r_anual,
                "Volatilidade": vol,
                "Sharpe": sharpe
            }

            perf_acum[p] = (1 + r_p).cumprod() - 1

            if vol > 0:
                rc = (w * (cov @ w)) / vol**2
                risk_decomp[p] = pd.Series(rc, index=df.columns)

        # ================== RESULTADOS ==================
        st.markdown("---")
        col_l, col_r = st.columns([3, 1])

        with col_l:
            res = pd.DataFrame(metrics)
            st.dataframe(
                res.style.format({
                    "Retorno Anualizado": "{:.2%}",
                    "Volatilidade": "{:.2%}",
                    "Sharpe": "{:.2f}"
                }),
                use_container_width=True
            )

        with col_r:
            st.markdown(
                f"""
                <div class="metric-container">
                <small>BENCHMARK DO PERÍODO</small><br>
                <strong>{bench_sel}</strong><br>
                <small>Retorno Anualizado: {bench_anual:.2%}</small>
                </div>
                """,
                unsafe_allow_html=True
            )

        # ================== PERFORMANCE ==================
        st.markdown("---")
        st.subheader("📈 Performance das Carteiras")

        fig = go.Figure()
        fig.add_trace(go.Scatter(
            x=curva_bench.index,
            y=curva_bench,
            name=bench_sel,
            line=dict(color=COR_BENCH, dash="dot")
        ))

        for i, p in enumerate(perfis):
            excesso = perf_acum[p] - curva_bench
            fig.add_trace(go.Scatter(
                x=perf_acum.index,
                y=perf_acum[p],
                name=p,
                line=dict(color=CORES_LIFETIME[i], width=2),
                customdata=excesso * 100,
                hovertemplate="%{y:.1%} (Alpha %{customdata:.1f}%)"
            ))

        fig.update_layout(
            template="simple_white",
            yaxis_tickformat=".1%",
            hovermode="x unified",
            height=600
        )

        st.plotly_chart(fig, use_container_width=True)

        # ================== CORRELAÇÃO ==================
        st.markdown("---")
        st.subheader("🔍 Matriz de Correlação")
        st.dataframe(
            ret.corr().style.background_gradient(cmap="RdYlGn_r", vmin=-1, vmax=1).format("{:.2f}"),
            use_container_width=True
        )

        # ================== RISCO x RETORNO ==================
        st.markdown("---")
        st.subheader("🎯 Risco vs Retorno (Histórico)")

        f = go.Figure()
        for i, p in enumerate(perfis):
            alpha = metrics[p]["Retorno Anualizado"] - bench_anual
            f.add_trace(go.Scatter(
                x=[metrics[p]["Volatilidade"]],
                y=[alpha],
                mode="markers+text",
                text=[p],
                textposition="top center",
                marker=dict(size=15, color=CORES_LIFETIME[i])
            ))

        f.add_hline(y=0, line_dash="dot", line_color="#475569")
        f.update_layout(
            template="simple_white",
            xaxis_title="Volatilidade",
            yaxis_title="Alpha vs Benchmark",
            yaxis_tickformat=".1%",
            xaxis_tickformat=".1%",
            height=450,
            showlegend=False
        )

        st.plotly_chart(f, use_container_width=True)

    except Exception as e:
        st.error(f"Erro: {e}")
