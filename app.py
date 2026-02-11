import streamlit as st
import pandas as pd
import numpy as np
import plotly.graph_objects as go

# ================= CONFIGURAÇÃO =================
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
arquivo = st.sidebar.file_uploader("Upload da Base Excel", type=['xlsx'])

if arquivo:
    try:
        # --- LEITURA DO EXCEL ---
        df_raw = pd.read_excel(arquivo, index_col=0, parse_dates=True)
        df_raw = df_raw.apply(pd.to_numeric, errors='coerce').ffill().dropna(how='all')
        
        # Filtro de datas
        start, end = st.sidebar.slider("Janela de Análise:", 
                                       df_raw.index.min().to_pydatetime(), 
                                       df_raw.index.max().to_pydatetime(), 
                                       (df_raw.index.min().to_pydatetime(), df_raw.index.max().to_pydatetime()))
        df_f = df_raw.loc[start:end].copy()

        # --- CÁLCULO DE RETORNOS MENSALIZADOS ---
        df_ret = df_f.pct_change().dropna()
        
        # Identificação de colunas chaves
        col_cpi = "CPI"
        col_agg = "Bloomberg Global Aggregate"
        col_equity = "Equity"
        
        # --- CÁLCULO DOS BENCHMARKS (CORRIGIDO) ---
        ret_agg = df_ret[col_agg]
        ret_eq = df_ret[col_equity]
        
        bench_data = pd.DataFrame(index=df_ret.index)
        bench_data["CPI"] = df_ret[col_cpi]
        bench_data["100% BBG Global Agg"] = ret_agg
        bench_data["10% MSCI World + 90% Agg"] = (0.10 * ret_eq) + (0.90 * ret_agg)
        bench_data["20% MSCI World + 80% Agg"] = (0.20 * ret_eq) + (0.80 * ret_agg)

        # Classes de Ativos para Alocação (Removemos os benchmarks da lista de escolha)
        cols_para_remover = [col_cpi, col_agg]
        ret_classes = df_ret.drop(columns=[c for c in cols_para_remover if c in df_ret.columns])

        # Anualização (12 meses)
        freq = 12 
        agg_anual = (1 + ret_agg.mean())**freq - 1
        cpi_anual = (1 + df_ret[col_cpi].mean())**freq - 1

        # --- INPUT DE PESOS ---
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
            
            # Decomposição de Risco (MCTR)
            if vol_p > 0:
                marginal_risk = np.dot(cov_matrix, w) / vol_p
                risk_decomp[p] = (w * marginal_risk) / vol_p
            
            metrics[p] = {
                "Retorno Anualizado": r_anual,
                "Volatilidade": vol_p,
                "Sharpe (vs Agg)": (r_anual - agg_anual) / vol_p if vol_p > 0 else 0
            }
            perf_acum[p] = (1 + ret_p).cumprod() - 1

        # --- EXIBIÇÃO ---
        st.markdown("---")
        col_res, col_info = st.columns([3, 1])
        with col_res:
            st.write("📊 **Estatísticas dos Perfis**")
            st.dataframe(pd.DataFrame(metrics).style.format("{:.2%}", subset=pd.IndexSlice[["Retorno Anualizado", "Volatilidade"], :]).format("{:.2f}", subset=pd.IndexSlice[["Sharpe (vs Agg)"], :]), use_container_width=True)
        with col_info:
            st.markdown(f'<div class="metric-container"><small>INFLAÇÃO (CPI) ANUAL</small><br><strong>{cpi_anual:.2%}</strong><br><small>Ref. Agg: {agg_anual:.2%}</small></div>', unsafe_allow_html=True)

        # Gráfico de Performance
        
        st.subheader("📊 Performance Acumulada")
        fig_perf = go.Figure()
        for b in bench_data.columns:
            curva_b = (1 + bench_data[b]).cumprod() - 1
            fig_perf.add_trace(go.Scatter(x=curva_b.index, y=curva_b, name=b, line=dict(color=CORES_BENCH.get(b), dash='dot')))
        for i, p in enumerate(perfis):
            fig_perf.add_trace(go.Scatter(x=perf_acum.index, y=perf_acum[p], name=p, line=dict(color=CORES_LIFETIME[i], width=3)))
        fig_perf.update_layout(template="simple_white", yaxis_tickformat='.1%', hovermode="x unified")
        st.plotly_chart(fig_perf, use_container_width=True)

        # Matriz de Correlação
        st.subheader("🎯 Matriz de Correlação")
        st.dataframe(ret_classes.corr().style.background_gradient(cmap='RdYlGn_r', vmin=-1, vmax=1).format("{:.2f}"), use_container_width=True)

    except Exception as e:
        st.error(f"Erro no processamento: {e}")