import streamlit as st
import pandas as pd
import numpy as np
import plotly.graph_objects as go
import plotly.express as px

# ================= CONFIGURAÇÃO =================
st.set_page_config(page_title="Portfolio Analytics | Offshore", layout="wide")

# Estilos CSS para alinhar tabelas e métricas
st.markdown("""
    <style>
    [data-testid="stDataFrame"] { width: 100%; }
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

st.title("🌍 Asset Allocation | Offshore (Base 100)")

st.sidebar.header("Configurações")
arquivo = st.sidebar.file_uploader("Upload da Base Excel", type=['xlsx'])

if arquivo:
    try:
        # --- LEITURA DO EXCEL (Tratando Base 100) ---
        df_raw = pd.read_excel(arquivo, index_col=0, parse_dates=True)
        df_raw = df_raw.apply(pd.to_numeric, errors='coerce').ffill().dropna(how='all')
        
        # Filtro de datas
        start, end = st.sidebar.slider("Janela de Análise:", 
                                       df_raw.index.min().to_pydatetime(), 
                                       df_raw.index.max().to_pydatetime(), 
                                       (df_raw.index.min().to_pydatetime(), df_raw.index.max().to_pydatetime()))
        df_f = df_raw.loc[start:end].copy()

        # --- TRANSFORMAÇÃO: BASE 100 -> RETORNO MENSAL ---
        df_ret = df_f.pct_change().dropna()
        
        # Mapeamento de colunas
        col_cpi = "CPI"
        col_agg = "Bloomberg Global Aggregate"
        col_equity = "Equity" # MSCI World

        # --- CÁLCULO DOS BENCHMARKS CORRIGIDO ---
        ret_agg = df_ret[col_agg]
        ret_eq = df_ret[col_equity]
        
        bench_ret = pd.DataFrame(index=df_ret.index)
        bench_ret["CPI"] = df_ret[col_cpi]
        bench_ret["100% BBG Global Agg"] = ret_agg
        # Fórmula híbrida aplicada mês a mês (rebalanceamento mensal)
        bench_ret["10% MSCI World + 90% Agg"] = (0.10 * ret_eq) + (0.90 * ret_agg)
        bench_ret["20% MSCI World + 80% Agg"] = (0.20 * ret_eq) + (0.80 * ret_agg)

        # Classes disponíveis para alocação
        ret_classes = df_ret.drop(columns=[col_cpi, col_agg])

        # --- INPUT DE PESOS ---
        st.subheader("🏗️ Definição de Pesos por Perfil")
        perfis = ["Ultra Conservador", "Conservador", "Moderado", "Arrojado", "Agressivo"]
        df_pesos_ui = pd.DataFrame({"Classe": ret_classes.columns})
        for p in perfis: df_pesos_ui[p] = 0.0
        edited = st.data_editor(df_pesos_ui, hide_index=True, use_container_width=True)
        
        # --- PROCESSAMENTO DOS PERFIS ---
        metrics, perf_acum, drawdowns = {}, pd.DataFrame(index=ret_classes.index), pd.DataFrame(index=ret_classes.index)
        freq = 12 
        agg_anual_hist = (1 + ret_agg.mean())**freq - 1

        for p in perfis:
            w = np.array(edited[p]) / 100
            ret_p = ret_classes.dot(w)
            
            # Rentabilidade Acumulada
            acum = (1 + ret_p).cumprod()
            perf_acum[p] = acum - 1
            
            # Cálculo de Drawdown
            picos = acum.expanding(min_periods=1).max()
            dd = (acum / picos) - 1
            drawdowns[p] = dd
            
            metrics[p] = {
                "Retorno Anualizado": (1 + ret_p.mean())**freq - 1,
                "Volatilidade": ret_p.std() * np.sqrt(freq),
                "Max Drawdown": dd.min(),
                "Sharpe (vs Agg)": (((1 + ret_p.mean())**freq - 1) - agg_anual_hist) / (ret_p.std() * np.sqrt(freq))
            }

        # --- DASHBOARD VISUAL ---
        st.markdown("---")
        col_table, col_metric = st.columns([3, 1])
        
        with col_table:
            st.write("📊 **Resumo de Risco e Retorno**")
            st.dataframe(pd.DataFrame(metrics).style.format("{:.2%}", subset=pd.IndexSlice[["Retorno Anualizado", "Volatilidade", "Max Drawdown"], :]).format("{:.2f}", subset=pd.IndexSlice[["Sharpe (vs Agg)"], :]), use_container_width=True)

        with col_metric:
            cpi_anual = (1 + df_ret[col_cpi].mean())**freq - 1
            st.markdown(f'<div class="metric-container"><small>INFLAÇÃO (CPI) NO PERÍODO</small><br><strong>{cpi_anual:.2%} a.a.</strong></div>', unsafe_allow_html=True)

        # Gráfico de Performance
        st.subheader("📈 Performance vs Benchmarks Híbridos")
        fig_perf = go.Figure()
        for b in bench_ret.columns:
            curva_b = (1 + bench_ret[b]).cumprod() - 1
            fig_perf.add_trace(go.Scatter(x=curva_b.index, y=curva_b, name=b, line=dict(color=CORES_BENCH.get(b), dash='dot')))
        for i, p in enumerate(perfis):
            fig_perf.add_trace(go.Scatter(x=perf_acum.index, y=perf_acum[p], name=p, line=dict(color=CORES_LIFETIME[i], width=3)))
        fig_perf.update_layout(template="simple_white", yaxis_tickformat='.1%', hovermode="x unified")
        st.plotly_chart(fig_perf, use_container_width=True)

        # Gráfico de Drawdown
        st.subheader("📉 Drawdown (Janela de Stress)")
        
        fig_dd = go.Figure()
        for i, p in enumerate(perfis):
            fig_dd.add_trace(go.Scatter(x=drawdowns.index, y=drawdowns[p], name=p, fill='tozeroy', line=dict(color=CORES_LIFETIME[i], width=1)))
        fig_dd.update_layout(template="simple_white", yaxis_tickformat='.1%', title="Queda em relação à máxima histórica")
        st.plotly_chart(fig_dd, use_container_width=True)

        # Matriz de Correlação (Plotly Heatmap - Sem erro de matplotlib)
        st.subheader("🎯 Matriz de Correlação entre Ativos")
        corr = ret_classes.corr()
        fig_corr = px.imshow(corr, text_auto=".2f", color_continuous_scale='RdBu_r')
        st.plotly_chart(fig_corr, use_container_width=True)

    except Exception as e:
        st.error(f"Erro no processamento: {e}")