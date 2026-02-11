import streamlit as st
import pandas as pd
import numpy as np
import plotly.graph_objects as go

# ================= CONFIGURAÇÃO =================
st.set_page_config(page_title="Portfolio Analytics | Offshore", layout="wide")

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

st.title("🌍 Asset Allocation | Offshore")

st.sidebar.header("Configurações")
arquivo = st.sidebar.file_uploader("Upload da Base Excel", type=['xlsx'])

if arquivo:
    try:
        # --- LEITURA E CONVERSÃO (Base 100 para Retorno) ---
        df_raw = pd.read_excel(arquivo, index_col=0, parse_dates=True)
        df_raw = df_raw.apply(pd.to_numeric, errors='coerce').ffill().dropna(how='all')
        
        # Filtro de datas
        start, end = st.sidebar.slider("Janela:", df_raw.index.min().to_pydatetime(), df_raw.index.max().to_pydatetime(), (df_raw.index.min().to_pydatetime(), df_raw.index.max().to_pydatetime()))
        df_f = df_raw.loc[start:end].copy()

        # Transformação crucial: Variação percentual mensal
        df_ret = df_f.pct_change().dropna()
        
        # Mapeamento exato das colunas da sua base
        col_cpi = "CPI"
        col_agg = "Bloomberg Global Aggregate"
        col_equity = "Equity" 

        # --- CÁLCULO DOS BENCHMARKS (Ponderação Mensal) ---
        r_agg = df_ret[col_agg]
        r_eq = df_ret[col_equity]
        
        bench_ret = pd.DataFrame(index=df_ret.index)
        bench_ret["CPI"] = df_ret[col_cpi]
        bench_ret["100% BBG Global Agg"] = r_agg
        # Aqui está a fórmula exata que você pediu:
        bench_ret["10% MSCI World + 90% Agg"] = (0.10 * r_eq) + (0.90 * r_agg)
        bench_ret["20% MSCI World + 80% Agg"] = (0.20 * r_eq) + (0.80 * r_agg)

        # Classes para alocação
        ret_classes = df_ret.drop(columns=[col_cpi, col_agg])

        # --- INPUT DE PESOS ---
        st.subheader("🏗️ Definição de Pesos por Perfil")
        perfis = ["Ultra Conservador", "Conservador", "Moderado", "Arrojado", "Agressivo"]
        df_pesos_ui = pd.DataFrame({"Classe": ret_classes.columns})
        for p in perfis: df_pesos_ui[p] = 0.0
        edited = st.data_editor(df_pesos_ui, hide_index=True, use_container_width=True)
        
        # --- CÁLCULOS DOS PERFIS ---
        metrics, perf_acum, drawdowns = {}, pd.DataFrame(index=ret_classes.index), pd.DataFrame(index=ret_classes.index)
        freq = 12 

        for p in perfis:
            w = np.array(edited[p]) / 100
            ret_p = ret_classes.dot(w)
            
            acum = (1 + ret_p).cumprod()
            perf_acum[p] = acum - 1
            
            # Drawdown
            picos = acum.expanding().max()
            dd = (acum / picos) - 1
            drawdowns[p] = dd
            
            metrics[p] = {
                "Retorno Anualizado": (1 + ret_p.mean())**freq - 1,
                "Volatilidade": ret_p.std() * np.sqrt(freq),
                "Max Drawdown": dd.min(),
                "Sharpe": ((1 + ret_p.mean())**freq - 1 - ((1 + r_agg.mean())**freq - 1)) / (ret_p.std() * np.sqrt(freq))
            }

        # --- OUTPUTS ---
        st.write("📊 **Estatísticas Comparativas**")
        st.dataframe(pd.DataFrame(metrics).style.format("{:.2%}"), use_container_width=True)

        # Performance Acumulada
        st.subheader("📈 Performance vs Benchmarks Híbridos")
        fig_perf = go.Figure()
        for b in bench_ret.columns:
            curva_b = (1 + bench_ret[b]).cumprod() - 1
            fig_perf.add_trace(go.Scatter(x=curva_b.index, y=curva_b, name=b, line=dict(color=CORES_BENCH.get(b), dash='dot')))
        for i, p in enumerate(perfis):
            fig_perf.add_trace(go.Scatter(x=perf_acum.index, y=perf_acum[p], name=p, line=dict(color=CORES_LIFETIME[i], width=3)))
        st.plotly_chart(fig_perf, use_container_width=True)

        # Drawdown
        st.subheader("📉 Drawdown (Risco de Perda)")
        
        fig_dd = go.Figure()
        for i, p in enumerate(perfis):
            fig_dd.add_trace(go.Scatter(x=drawdowns.index, y=drawdowns[p], name=p, fill='tozeroy', line=dict(color=CORES_LIFETIME[i])))
        st.plotly_chart(fig_dd, use_container_width=True)

        # VOLTA DA MATRIZ ANTIGA (Formatada)
        st.subheader("🎯 Matriz de Correlação")
        corr_matrix = ret_classes.corr()
        # Usando estilo Pandas que simula o background sem erro de matplotlib se possível, 
        # ou apenas a tabela limpa e bem formatada:
        st.dataframe(corr_matrix.style.format("{:.2f}").background_gradient(cmap='RdYlGn_r', axis=None), use_container_width=True)

    except Exception as e:
        st.error(f"Erro: {e}")