import streamlit as st
import pandas as pd
import numpy as np
import plotly.graph_objects as go
from datetime import datetime

# 1. CONFIGURAÇÃO DE PÁGINA
st.set_page_config(page_title="Asset Allocation | Offshore", layout="wide")

st.markdown("""
    <style>
    [data-testid="stDataFrame"] { width: 100%; }
    th { min-width: 110px !important; text-align: center !important; }
    .metric-container { 
        background-color: #F8F9FA; 
        padding: 15px; border-radius: 10px; border-left: 5px solid #1C2C54; margin-top: 55px; 
    }
    </style>
    """, unsafe_allow_html=True)

# Configuração de Cores
CORES_LIFETIME = ['#D1D5DB', '#9CA3AF', '#6B7280', '#4B5563', '#1C2C54']
CORES_BENCH = {
    "CPI": "#64748B", 
    "100% BBG Global Agg": "#334155", 
    "10% MSCI World + 90% Agg": "#1E293B", 
    "20% MSCI World + 80% Agg": "#020617"
}

st.title("🌍 Asset Allocation | Offshore")

st.sidebar.header("Configurações")
arquivo = st.sidebar.file_uploader("Upload da Base Offshore", type=['csv', 'xlsx'])

if arquivo:
    try:
        # --- LEITURA ---
        if arquivo.name.endswith('.csv'):
            df_raw = pd.read_csv(arquivo, index_col=0, parse_dates=True, sep=None, engine='python')
        else:
            df_raw = pd.read_excel(arquivo, index_col=0, parse_dates=True)
        
        # Limpeza e preenchimento de dados nulos (essencial para correlação)
        df_raw = df_raw.apply(pd.to_numeric, errors='coerce').ffill().dropna(how='all')
        
        # --- FILTRO DE DATAS ---
        start, end = st.sidebar.slider("Janela de Análise:", df_raw.index.min().to_pydatetime(), df_raw.index.max().to_pydatetime(), (df_raw.index.min().to_pydatetime(), df_raw.index.max().to_pydatetime()))
        df_f = df_raw.loc[start:end].copy()

        # --- PROCESSAMENTO DE RETORNOS ---
        # Calculamos a variação percentual para evitar erros com números nominais
        df_ret = df_f.pct_change().dropna()
        
        col_cpi = "CPI"
        col_agg = "Bloomberg Global Aggregate"
        col_equity = "Equity"
        
        if col_cpi not in df_f.columns or col_agg not in df_f.columns:
            st.error(f"As colunas '{col_cpi}' e '{col_agg}' são obrigatórias para os benchmarks.")
            st.stop()

        # --- CÁLCULO DOS BENCHMARKS ---
        num_anos = len(df_ret) / 12 # Assumindo dados mensais se for offshore clássico, ou 252 se diário
        # Ajuste automático de anualização
        freq = 252 if (df_f.index[1] - df_f.index[0]).days < 5 else 12
        
        ret_cpi = df_ret[col_cpi]
        cpi_anualizado = (1 + ret_cpi.mean())**freq - 1
        
        ret_agg = df_ret[col_agg]
        agg_anualizado = (1 + ret_agg.mean())**freq - 1
        
        ret_eq = df_ret[col_equity] if col_equity in df_ret.columns else ret_agg

        bench_map = {
            "CPI": ret_cpi,
            "100% BBG Global Agg": ret_agg,
            "10% MSCI World + 90% Agg": (0.10 * ret_eq) + (0.90 * ret_agg),
            "20% MSCI World + 80% Agg": (0.20 * ret_eq) + (0.80 * ret_agg)
        }

        # --- CLASSES PARA ALOCAÇÃO (Exclui os benchmarks fixos da edição) ---
        cols_excluir = [col_cpi, col_agg]
        ret_classes = df_ret.drop(columns=[c for c in cols_excluir if c in df_ret.columns])

        # --- DATA EDITOR (PESOS) ---
        st.subheader("🏗️ Definição de Pesos por Perfil")
        perfis = ["Ultra Conservador", "Conservador", "Moderado", "Arrojado", "Agressivo"]
        df_pesos_ui = pd.DataFrame({"Classe": ret_classes.columns})
        for p in perfis: df_pesos_ui[p] = 0.0
        
        edited = st.data_editor(df_pesos_ui, hide_index=True, use_container_width=True)
        
        # Validação visual da soma
        somas = edited[perfis].sum()
        st.markdown(f"<p style='color: #666; font-size: 0.8rem;'>Soma Check: " + " | ".join([f"{p}: {somas[p]:.1f}%" for p in perfis]) + "</p>", unsafe_allow_html=True)

        # --- CÁLCULOS DOS PERFIS ---
        metrics = {}
        perf_acum = pd.DataFrame(index=ret_classes.index)
        cov_matrix = ret_classes.cov() * freq

        for p in perfis:
            w = np.array(edited[p]) / 100
            ret_p = ret_classes.dot(w)
            
            # Métricas Anualizadas
            r_anual = (1 + ret_p.mean())**freq - 1
            vol_p = np.sqrt(np.dot(w.T, np.dot(cov_matrix, w)))
            
            metrics[p] = {
                "Retorno Anualizado": r_anual,
                "Volatilidade": vol_p,
                "Sharpe (vs Agg)": (r_anual - agg_anualizado) / vol_p if vol_p > 0 else 0
            }
            perf_acum[p] = (1 + ret_p).cumprod() - 1

        # --- DISPLAY RESULTADOS ---
        st.markdown("---")
        col_res, col_info = st.columns([3, 1])
        with col_res:
            st.write("📊 **Métricas de Performance**")
            res_df = pd.DataFrame(metrics)
            st.dataframe(res_df.style.format("{:.2%}", subset=pd.IndexSlice[["Retorno Anualizado", "Volatilidade"], :]).format("{:.2f}", subset=pd.IndexSlice[["Sharpe (vs Agg)"], :]), use_container_width=True)
        
        with col_info:
            st.markdown(f"""
            <div class="metric-container">
                <small>INFLAÇÃO (CPI) ANUAL</small><br><strong>{cpi_anualizado:.2%}</strong><br><br>
                <small>BBG GLOBAL AGG ANUAL</small><br><strong>{agg_anualizado:.2%}</strong>
            </div>
            """, unsafe_allow_html=True)

        # --- GRÁFICO DE PERFORMANCE ---
        
        st.subheader("📈 Performance Acumulada")
        fig = go.Figure()
        
        for b_name, b_ret in bench_map.items():
            fig.add_trace(go.Scatter(x=b_ret.index, y=(1+b_ret).cumprod()-1, name=b_name, line=dict(color=CORES_BENCH.get(b_name), dash='dot', width=1.5)))
        
        for i, p in enumerate(perfis):
            fig.add_trace(go.Scatter(x=perf_acum.index, y=perf_acum[p], name=p, line=dict(color=CORES_LIFETIME[i], width=3)))
            
        fig.update_layout(template="simple_white", yaxis_tickformat='.1%', height=500, hovermode="x unified")
        st.plotly_chart(fig, use_container_width=True)

        # --- CORRELAÇÃO ---
        st.markdown("---")
        st.subheader("🎯 Matriz de Correlação das Classes")
        corr = ret_classes.corr()
        st.dataframe(corr.style.background_gradient(cmap='RdYlGn_r', vmin=-1, vmax=1).format("{:.2f}"), use_container_width=True)

    except Exception as e:
        st.error(f"Erro no processamento: {e}")
        st.info("Dica: Verifique se os nomes das colunas no arquivo são exatamente 'CPI', 'Bloomberg Global Aggregate' e 'Equity'.")