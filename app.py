import streamlit as st
import pandas as pd
import numpy as np
import plotly.graph_objects as go
from datetime import datetime

# 1. CONFIGURAÇÃO DE PÁGINA [cite: 1]
st.set_page_config(page_title="Portfolio Analytics | Offshore", layout="wide")

st.markdown("""
    <style>
    [data-testid="stDataFrame"] { width: 100%; }
    th { min-width: 110px !important; text-align: center !important; white-space: pre-wrap !important; }
    .soma-discreta { font-size: 0.8rem; color: #888; margin-top: -15px; margin-bottom: 15px; }
    h1, h2, h3 { color: #1C2C54; font-family: 'Segoe UI', sans-serif; }
    .metric-container { 
        background-color: #F8F9FA; 
        padding: 15px; 
        border-radius: 10px; 
        border-left: 5px solid #1C2C54;
        margin-top: 55px; 
    }
    </style>
    """, unsafe_allow_html=True)

CORES_LIFETIME = ['#D1D5DB', '#9CA3AF', '#6B7280', '#4B5563', '#1C2C54']
CORES_BENCH = {"CPI": "#64748B", "100% BBG Global Agg": "#334155", "10% MSCI World + 90% Agg": "#1E293B", "20% MSCI World + 80% Agg": "#020617"}

st.title("🌍 Asset Allocation | Offshore")

st.sidebar.header("Configurações")
arquivo = st.sidebar.file_uploader("Upload da Base Offshore", type=['csv', 'xlsx'])

if arquivo:
    try:
        # --- CARREGAMENTO [cite: 3, 4] ---
        if arquivo.name.endswith('.csv'):
            df_raw = pd.read_csv(arquivo, index_col=0, parse_dates=True, sep=None, decimal='.', engine='python')
        else:
            df_raw = pd.read_excel(arquivo, index_col=0, parse_dates=True)
        
        df_raw = df_raw.apply(pd.to_numeric, errors='coerce').dropna(how='all')
        
        # --- JANELA DE ANÁLISE [cite: 4] ---
        start, end = st.sidebar.slider("Janela de Análise:", df_raw.index.min().to_pydatetime(), df_raw.index.max().to_pydatetime(), (df_raw.index.min().to_pydatetime(), df_raw.index.max().to_pydatetime()))
        df_f = df_raw.loc[start:end].copy()
        num_dias = len(df_f)

        # --- BENCHMARKS (CPI E HÍBRIDOS) ---
        cpi_level = df_f["CPI"].dropna()
        cpi_anual = (cpi_level.iloc[-1] / cpi_level.iloc[0])**(252 / len(cpi_level)) - 1
        cpi_ret_diario = (1 + cpi_anual)**(1 / 252) - 1
        cpi_ret_serie = pd.Series(cpi_ret_diario, index=df_f.index)

        df_assets = df_f.drop(columns=["CPI"])
        ret_assets = df_assets.pct_change().dropna()
        
        ret_agg = ret_assets["Bloomberg Global Aggregate"]
        ret_eq = ret_assets["Equity"]

        bench_map = {
            "CPI": cpi_ret_serie,
            "100% BBG Global Agg": ret_agg,
            "10% MSCI World + 90% Agg": 0.10 * ret_eq + 0.90 * ret_agg,
            "20% MSCI World + 80% Agg": 0.20 * ret_eq + 0.80 * ret_agg
        }
        
        # Referência para o Sharpe [cite: 10]
        rf_anual_ref = (1 + (1 + ret_agg).prod() - 1)**(252/num_dias) - 1

        # --- BLOCO 1: PESOS [cite: 6, 7] ---
        st.subheader("🏗️ Definição de Pesos por Perfil")
        perfis = ["Ultra", "Conservative", "Moderate", "Growth", "Aggressive"]
        df_pesos_ui = pd.DataFrame({"Ativo": ret_assets.columns})
        for p in perfis: df_pesos_ui[p] = 0.0
        edited = st.data_editor(df_pesos_ui, hide_index=True, use_container_width=True)
        
        somas = edited[perfis].sum()
        st.markdown(f"<p class='soma-discreta'>Valid. Somatórios: " + " | ".join([f"{p}: {somas[p]:.1f}%" for p in somas.index]) + "</p>", unsafe_allow_html=True)

        # --- CÁLCULOS [cite: 8, 9] ---
        metrics, risk_decomp, perf_acum = {}, {}, pd.DataFrame(index=ret_assets.index)
        cov_matrix = ret_assets.cov() * 252

        for p in perfis:
            w = np.array(edited[p]) / 100
            ret_p = ret_assets.dot(w)
            
            r_anual = (1 + (1 + ret_p).prod() - 1)**(252/num_dias) - 1 if num_dias > 0 else 0
            vol_p = np.sqrt(np.dot(w.T, np.dot(cov_matrix, w)))
            
            if vol_p > 0:
                risk_decomp[p] = pd.Series((w * np.dot(cov_matrix, w)) / vol_p**2, index=ret_assets.columns)
            
            metrics[p] = {
                "Retorno Anualizado": r_anual, 
                "Volatilidade": vol_p, 
                "Sharpe (vs Agg)": (r_anual - rf_anual_ref) / vol_p if vol_p > 0.0001 else 0
            }
            perf_acum[p] = (1 + ret_p).cumprod() - 1

        # --- RESULTADOS CONSOLIDADOS [cite: 10, 11] ---
        st.markdown("---")
        col_res, col_info = st.columns([3, 1])
        with col_res:
            st.write("📈 Resultados Consolidados:")
            res_df = pd.DataFrame(metrics)
            st.dataframe(res_df.style.format(lambda x: f"{x:.2f}" if "Sharpe" in str(res_df.index[res_df.isin([x]).any(axis=1)].tolist()) else f"{x:.2%}"), use_container_width=True)
        with col_info:
            st.markdown(f'<div class="metric-container"><small>INFLAÇÃO (CPI) PERÍODO</small><br><strong>Acumulado: {(1+cpi_anual)**(num_dias/252)-1:.2%}</strong><br><small>Anualizado: {cpi_anual:.2%}</small></div>', unsafe_allow_html=True)

        # --- PERFORMANCE [cite: 13, 14, 15] ---
        st.markdown("---")
        st.subheader("📈 Performance das Carteiras vs Benchmarks")
        fig_comp = go.Figure()
        for b, r_bench in bench_map.items():
            curva_b = (1 + r_bench).cumprod() - 1
            fig_comp.add_trace(go.Scatter(x=curva_b.index, y=curva_b, name=b, line=dict(color=CORES_BENCH.get(b, "#94a3b8"), dash='dot', width=1.5)))
        for i, p in enumerate(perfis):
            fig_comp.add_trace(go.Scatter(x=perf_acum.index, y=perf_acum[p], name=p, line=dict(color=CORES_LIFETIME[i], width=2.5)))
        fig_comp.update_layout(template="simple_white", yaxis_tickformat='.1%', height=550, hovermode="x unified")
        st.plotly_chart(fig_comp, use_container_width=True)

        # --- ANÁLISE DE ATIVOS E CORRELAÇÃO [cite: 21, 23] ---
        st.markdown("---")
        st.subheader("🔍 Análise de Ativos e Diversificação")
        st.write("📋 **Estatísticas Individuais e Matriz de Correlação:**")
        col_stats_L, col_stats_R = st.columns(2)
        with col_stats_L:
            ret_an_ind = (1 + (1 + ret_assets).prod() - 1)**(252/num_dias) - 1
            vol_an_ind = ret_assets.std() * np.sqrt(252)
            stats_ind = pd.DataFrame({"Retorno": ret_an_ind, "Vol": vol_an_ind}).T
            st.dataframe(stats_ind.style.format("{:.2%}"), use_container_width=True)
        with col_stats_R:
            st.dataframe(ret_assets.corr().style.background_gradient(cmap='RdYlGn_r', vmin=-1, vmax=1).format("{:.2f}"), use_container_width=True)

        # --- BLOCO 4: HISTÓRICO [cite: 24, 25, 26] ---
        st.markdown("---")
        st.subheader("🔍 Análise de Eficiência (Histórico)")
        col_4_L, col_4_R = st.columns(2)
        with col_4_L:
            st.write("**⚠️ Contribuição de Risco por Ativo:**")
            df_rd = pd.DataFrame(risk_decomp)
            st.dataframe(df_rd.style.format("{:.1%}").background_gradient(cmap='Reds'), use_container_width=True, height=300)
        with col_4_R:
            f_h = go.Figure()
            for p in perfis:
                f_h.add_trace(go.Scatter(
                    x=[metrics[p]["Volatilidade"]], y=[metrics[p]["Retorno Anualizado"]], 
                    mode='markers+text', name=p, text=[p], textposition="top center",
                    marker=dict(size=15, color=CORES_LIFETIME[perfis.index(p)], line=dict(width=2, color='white'))
                ))
            f_h.update_layout(template="simple_white", xaxis_title="Volatilidade", yaxis_title="Retorno Anualizado", yaxis_tickformat='.1%', height=400)
            st.plotly_chart(f_h, use_container_width=True)

        # --- BLOCO 5: PROJEÇÕES (FORWARD-LOOKING) [cite: 30, 32, 33] ---
        st.markdown("---")
        st.subheader("🚀 Análise de Eficiência (Forward-looking)")
        col_5_L, col_5_R = st.columns(2)
        with col_5_L:
            st.write("**📋 Tabela de Retorno Esperado (%):**")
            df_proj = pd.DataFrame({"Ativo": ret_assets.columns, "Retorno Esperado (%)": 5.0})
            e_p = st.data_editor(df_proj, hide_index=True, use_container_width=True, height=300)
            map_e = dict(zip(e_p["Ativo"], e_p["Retorno Esperado (%)"] / 100))
        with col_5_R:
            st.write("**🎯 Risco Histórico vs Retorno Projetado:**")
            f_pr = go.Figure()
            for p in perfis:
                w_perfil = edited[p].values / 100
                ret_proj = sum(w_perfil[j] * map_e.get(ret_assets.columns[j], 0) for j in range(len(w_perfil)))
                f_pr.add_trace(go.Scatter(
                    x=[metrics[p]["Volatilidade"]], y=[ret_proj], 
                    mode='markers+text', name=p, text=[p], textposition="top center",
                    marker=dict(size=18, color=CORES_LIFETIME[perfis.index(p)], symbol='diamond', line=dict(width=2, color='white'))
                ))
            f_pr.update_layout(template="simple_white", xaxis_title="Volatilidade Histórica", yaxis_title="Retorno Projetado", yaxis_tickformat='.1%', height=400)
            st.plotly_chart(f_pr, use_container_width=True)

    except Exception as e:
        st.error(f"Erro: {e}")