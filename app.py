import streamlit as st
import pandas as pd
import numpy as np
import plotly.graph_objects as go

# 1. CONFIGURAÇÃO DE PÁGINA
st.set_page_config(page_title="Portfolio Analytics | Offshore", layout="wide")

st.markdown("""
    <style>
    [data-testid="stDataFrame"] { width: 100%; }
    th { min-width: 110px !important; text-align: center !important; }
    .metric-container { 
        background-color: #F8F9FA; padding: 15px; border-radius: 10px; 
        border-left: 5px solid #1C2C54; margin-top: 55px; 
    }
    </style>
    """, unsafe_allow_html=True)

CORES_LIFETIME = ['#D1D5DB', '#9CA3AF', '#6B7280', '#4B5563', '#1C2C54']
CORES_BENCH = {
    "CPI": "#64748B", 
    "100% BBG Global Agg": "#334155", 
    "10% MSCI World + 90% Agg": "#1E293B", 
    "20% MSCI World + 80% Agg": "#020617"
}

st.title("🌍 Asset Allocation | Offshore")

st.sidebar.header("Configurações")
arquivo = st.sidebar.file_uploader("Upload da Base (comdinheiro.csv)", type=['csv'])

if arquivo:
    try:
        # --- LEITURA DO ARQUIVO CONSOLIDADO ---
        df_raw = pd.read_csv(arquivo, index_col=0, parse_dates=True)
        df_raw = df_raw.apply(pd.to_numeric, errors='coerce').ffill()
        
        # Filtro de datas
        start, end = st.sidebar.slider("Janela:", df_raw.index.min().to_pydatetime(), df_raw.index.max().to_pydatetime(), (df_raw.index.min().to_pydatetime(), df_raw.index.max().to_pydatetime()))
        df_f = df_raw.loc[start:end].copy()

        # --- PROCESSAMENTO DE RETORNOS ---
        # Como o arquivo contém índices (Base 100), usamos pct_change
        df_ret = df_f.pct_change().dropna()
        
        # Identificação de Benchmarks e Classes
        col_cpi, col_agg, col_equity = "CPI", "Bloomberg Global Aggregate", "Equity"
        cols_bench_fixos = [col_cpi, col_agg]
        ret_classes = df_ret.drop(columns=[c for c in cols_bench_fixos if c in df_ret.columns])

        # --- BENCHMARKS HÍBRIDOS ---
        ret_agg = df_ret[col_agg]
        ret_eq = df_ret[col_equity]
        bench_map = {
            "CPI": df_ret[col_cpi],
            "100% BBG Global Agg": ret_agg,
            "10% MSCI World + 90% Agg": (0.10 * ret_eq) + (0.90 * ret_agg),
            "20% MSCI World + 80% Agg": (0.20 * ret_eq) + (0.80 * ret_agg)
        }
        
        # Anualização baseada na frequência dos dados (mensal = 12)
        freq = 12 
        rf_anual_ref = (1 + ret_agg.mean())**freq - 1
        cpi_anualizado = (1 + df_ret[col_cpi].mean())**freq - 1

        # --- BLOCO 1: PESOS ---
        st.subheader("🏗️ Definição de Pesos por Perfil")
        perfis = ["Ultra Conservador", "Conservador", "Moderado", "Arrojado", "Agressivo"]
        df_pesos_ui = pd.DataFrame({"Classe": ret_classes.columns})
        for p in perfis: df_pesos_ui[p] = 0.0
        
        edited = st.data_editor(df_pesos_ui, hide_index=True, use_container_width=True)
        
        # --- CÁLCULOS TÉCNICOS ---
        metrics, risk_decomp, perf_acum = {}, {}, pd.DataFrame(index=ret_classes.index)
        cov_matrix = ret_classes.cov() * freq

        for p in perfis:
            w = np.array(edited[p]) / 100
            ret_p = ret_classes.dot(w)
            
            r_anual = (1 + ret_p.mean())**freq - 1
            vol_p = np.sqrt(np.dot(w.T, np.dot(cov_matrix, w)))
            
            # Decomposição de Risco (MCTR) - Igual ao primeiro código
            if vol_p > 0:
                marginal_risk = np.dot(cov_matrix, w) / vol_p
                risk_contribution = w * marginal_risk
                risk_decomp[p] = risk_contribution / vol_p # Em % do total
            
            metrics[p] = {
                "Retorno Anualizado": r_anual,
                "Volatilidade": vol_p,
                "Sharpe (vs Agg)": (r_anual - rf_anual_ref) / vol_p if vol_p > 0 else 0
            }
            perf_acum[p] = (1 + ret_p).cumprod() - 1

        # --- EXIBIÇÃO ---
        st.markdown("---")
        col_res, col_info = st.columns([3, 1])
        with col_res:
            st.write("📈 **Resultados Consolidados**")
            st.dataframe(pd.DataFrame(metrics).style.format("{:.2%}", subset=["Retorno Anualizado", "Volatilidade"]).format("{:.2f}", subset=["Sharpe (vs Agg)"]), use_container_width=True)
        with col_info:
            st.markdown(f'<div class="metric-container"><small>CPI ANUALIZADO</small><br><strong>{cpi_anualizado:.2%}</strong><br><small>Ref. Agg: {rf_anual_ref:.2%}</small></div>', unsafe_allow_html=True)

        # Gráfico de Performance
        st.subheader("📊 Performance vs Benchmarks")
        fig_perf = go.Figure()
        for b, r_b in bench_map.items():
            fig_perf.add_trace(go.Scatter(x=r_b.index, y=(1+r_b).cumprod()-1, name=b, line=dict(color=CORES_BENCH.get(b), dash='dot')))
        for i, p in enumerate(perfis):
            fig_perf.add_trace(go.Scatter(x=perf_acum.index, y=perf_acum[p], name=p, line=dict(color=CORES_LIFETIME[i], width=3)))
        st.plotly_chart(fig_perf, use_container_width=True)

        # --- NOVO: DECOMPOSIÇÃO DE RISCO (Igual ao código 1) ---
        st.markdown("---")
        st.subheader("🔍 Decomposição de Risco por Ativo (%)")
        st.dataframe(pd.DataFrame(risk_decomp).style.format("{:.1%").background_gradient(cmap='Reds'), use_container_width=True)

        # --- CORRELAÇÃO ---
        st.subheader("🎯 Correlação entre Classes")
        st.dataframe(ret_classes.corr().style.background_gradient(cmap='RdYlGn_r', vmin=-1, vmax=1).format("{:.2f}"), use_container_width=True)

        # --- PROJEÇÕES (FORWARD-LOOKING) ---
        st.markdown("---")
        st.subheader("🚀 Eficiência Projetada (Risco vs Alpha)")
        col_p1, col_p2 = st.columns([1, 2])
        with col_p1:
            df_proj = pd.DataFrame({"Classe": ret_classes.columns, "Retorno Esperado (%)": 6.0})
            e_p = st.data_editor(df_proj, hide_index=True, use_container_width=True)
            map_e = dict(zip(e_p["Classe"], e_p["Retorno Esperado (%)"] / 100))
        with col_p2:
            f_pr = go.Figure()
            for p in perfis:
                w_perfil = edited[p].values / 100
                ret_total_proj = sum(w_perfil[i] * map_e.get(ret_classes.columns[i], 0) for i in range(len(ret_classes.columns)))
                # Alpha em relação ao Global Agg
                alpha_proj = ret_total_proj - rf_anual_ref
                
                f_pr.add_trace(go.Scatter(x=[metrics[p]["Volatilidade"]], y=[alpha_proj], mode='markers+text', name=p, text=[p], textposition="top center", marker=dict(size=15, color=CORES_LIFETIME[perfis.index(p)], symbol='diamond')))
            f_pr.add_hline(y=0, line_dash="dash", line_color="gray", annotation_text="Break-even Agg")
            f_pr.update_layout(template="simple_white", xaxis_title="Volatilidade Histórica", yaxis_title="Alpha Projetado (vs Agg)", yaxis_tickformat='.1%')
            st.plotly_chart(f_pr, use_container_width=True)

    except Exception as e:
        st.error(f"Erro: {e}")