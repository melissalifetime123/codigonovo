import streamlit as st
import pandas as pd
import numpy as np
import plotly.graph_objects as go
from datetime import datetime

# 1. CONFIGURAÇÃO DE PÁGINA
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
arquivo = st.sidebar.file_uploader("Upload da Base Offshore (Consolidada)", type=['csv', 'xlsx'])

if arquivo:
    try:
        # --- CARREGAMENTO ---
        if arquivo.name.endswith('.csv'):
            df_raw = pd.read_csv(arquivo, index_col=0, parse_dates=True, sep=None, engine='python')
        else:
            df_raw = pd.read_excel(arquivo, index_col=0, parse_dates=True)
        
        df_raw = df_raw.apply(pd.to_numeric, errors='coerce').dropna(how='all')
        
        # --- JANELA DE ANÁLISE ---
        start, end = st.sidebar.slider("Janela de Análise:", df_raw.index.min().to_pydatetime(), df_raw.index.max().to_pydatetime(), (df_raw.index.min().to_pydatetime(), df_raw.index.max().to_pydatetime()))
        df_f = df_raw.loc[start:end].copy()
        num_dias = len(df_f)

        # --- SEPARAÇÃO: BENCHMARKS VS CLASSES ---
        # Definimos o que é estritamente benchmark
        cols_bench_fixos = ["CPI", "Bloomberg Global Aggregate"]
        
        # Calculamos retornos para todos
        ret_all = df_f.pct_change().dropna()
        
        # Criamos a série do CPI (Benchmark 1)
        cpi_level = df_f["CPI"].dropna()
        cpi_anual = (cpi_level.iloc[-1] / cpi_level.iloc[0])**(252 / len(cpi_level)) - 1
        cpi_ret_serie = pd.Series((1 + cpi_anual)**(1 / 252) - 1, index=ret_all.index)

        # Preparamos os retornos das classes (Removendo os benchmarks da alocação)
        # Se 'Equity' estiver no arquivo, ela pode ser classe E benchmark ao mesmo tempo? 
        # Aqui, removemos apenas o que você pediu para ser "apenas benchmark"
        ret_assets = ret_all.drop(columns=[c for c in cols_bench_fixos if c in ret_all.columns])
        
        # Benchmarks Híbridos
        ret_agg = ret_all["Bloomberg Global Aggregate"] if "Bloomberg Global Aggregate" in ret_all.columns else pd.Series(0, index=ret_all.index)
        ret_eq = ret_all["Equity"] if "Equity" in ret_all.columns else pd.Series(0, index=ret_all.index)

        bench_map = {
            "CPI": cpi_ret_serie,
            "100% BBG Global Agg": ret_agg,
            "10% MSCI World + 90% Agg": 0.10 * ret_eq + 0.90 * ret_agg,
            "20% MSCI World + 80% Agg": 0.20 * ret_eq + 0.80 * ret_agg
        }
        
        rf_anual_ref = (1 + (1 + ret_agg).prod() - 1)**(252/num_dias) - 1

        # --- BLOCO 1: PESOS (APENAS CLASSES) ---
        st.subheader("🏗️ Definição de Pesos por Perfil")
        perfis = ["Ultra", "Conservative", "Moderate", "Growth", "Aggressive"]
        df_pesos_ui = pd.DataFrame({"Ativo": ret_assets.columns})
        for p in perfis: df_pesos_ui[p] = 0.0
        
        edited = st.data_editor(df_pesos_ui, hide_index=True, use_container_width=True)
        
        somas = edited[perfis].sum()
        st.markdown(f"<p class='soma-discreta'>Soma dos Pesos: " + " | ".join([f"{p}: {somas[p]:.1f}%" for p in perfis]) + "</p>", unsafe_allow_html=True)

        # --- CÁLCULOS DE PERFORMANCE ---
        metrics, risk_decomp, perf_acum = {}, {}, pd.DataFrame(index=ret_assets.index)
        cov_matrix = ret_assets.cov() * 252

        for p in perfis:
            w = np.array(edited[p]) / 100
            ret_p = ret_assets.dot(w)
            
            r_anual = (1 + (1 + ret_p).prod() - 1)**(252/num_dias) - 1
            vol_p = np.sqrt(np.dot(w.T, np.dot(cov_matrix, w)))
            
            if vol_p > 0:
                risk_decomp[p] = pd.Series((w * np.dot(cov_matrix, w)) / vol_p**2, index=ret_assets.columns)
            
            metrics[p] = {
                "Retorno Anualizado": r_anual, 
                "Volatilidade": vol_p, 
                "Sharpe (vs Agg)": (r_anual - rf_anual_ref) / vol_p if vol_p > 0.001 else 0
            }
            perf_acum[p] = (1 + ret_p).cumprod() - 1

        # --- DASHBOARD VISUAL ---
        st.markdown("---")
        col_res, col_info = st.columns([3, 1])
        with col_res:
            st.write("📈 Resultados Consolidados:")
            res_df = pd.DataFrame(metrics)
            st.dataframe(res_df.style.format(lambda x: f"{x:.2f}" if x > 2 or x < -2 else f"{x:.2%}"), use_container_width=True)
        with col_info:
            st.markdown(f'<div class="metric-container"><small>INFLAÇÃO (CPI) ANUALIZADA</small><br><strong>{cpi_anual:.2%}</strong><br><small>Ref. Bloomberg Agg: {rf_anual_ref:.2%}</small></div>', unsafe_allow_html=True)

        # Gráfico de Performance
        fig_comp = go.Figure()
        for b, r_bench in bench_map.items():
            curva_b = (1 + r_bench).cumprod() - 1
            fig_comp.add_trace(go.Scatter(x=curva_b.index, y=curva_b, name=b, line=dict(color=CORES_BENCH.get(b, "#94a3b8"), dash='dot', width=1.5)))
        for i, p in enumerate(perfis):
            fig_comp.add_trace(go.Scatter(x=perf_acum.index, y=perf_acum[p], name=p, line=dict(color=CORES_LIFETIME[i], width=3)))
        fig_comp.update_layout(template="simple_white", yaxis_tickformat='.1%', height=500, hovermode="x unified", title="Evolução Patrimonial")
        st.plotly_chart(fig_comp, use_container_width=True)

        # Matriz de Correlação (Apenas Classes)
        st.markdown("---")
        st.subheader("🎯 Correlação entre Classes")
        st.dataframe(ret_assets.corr().style.background_gradient(cmap='RdYlGn_r', vmin=-1, vmax=1).format("{:.2f}"), use_container_width=True)

        # Projeções
        st.markdown("---")
        st.subheader("🚀 Projeções Forward-looking")
        col_p1, col_p2 = st.columns(2)
        with col_p1:
            df_proj = pd.DataFrame({"Classe": ret_assets.columns, "Retorno Esperado (%)": 6.0})
            e_p = st.data_editor(df_proj, hide_index=True, use_container_width=True)
            map_e = dict(zip(e_p["Classe"], e_p["Retorno Esperado (%)"] / 100))
        with col_p2:
            f_pr = go.Figure()
            for p in perfis:
                w_perfil = edited[p].values / 100
                ret_proj = sum(w_perfil[j] * map_e.get(ret_assets.columns[j], 0) for j in range(len(w_perfil)))
                f_pr.add_trace(go.Scatter(x=[metrics[p]["Volatilidade"]], y=[ret_proj], mode='markers+text', name=p, text=[p], textposition="top center", marker=dict(size=15, color=CORES_LIFETIME[perfis.index(p)])))
            f_pr.update_layout(template="simple_white", xaxis_title="Risco Histórico", yaxis_title="Retorno Projetado", yaxis_tickformat='.1%')
            st.plotly_chart(f_pr, use_container_width=True)

    except Exception as e:
        st.error(f"Erro ao processar dados: {e}")