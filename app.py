import streamlit as st
import pandas as pd
import numpy as np
import plotly.express as px

# Configuração da Página
st.set_page_config(page_title="Portfolio Offshore", layout="wide")

# =========================
# FUNÇÃO DE CARREGAMENTO (AJUSTADA)
# =========================
@st.cache_data
def load_data(file):
    try:
        # Lendo o CSV e tratando colunas extras/vazias
        df = pd.read_csv(file)
        
        # Remove colunas que começam com 'Unnamed' ou que são totalmente vazias
        df = df.loc[:, ~df.columns.str.contains('^Unnamed')]
        df = df.dropna(axis=1, how='all')
        
        # Ajuste de Data: Converte e remove linhas onde a data é inválida
        df['Date'] = pd.to_datetime(df['Date'], errors='coerce')
        df = df.dropna(subset=['Date'])
        df = df.sort_values('Date').set_index('Date')
        
        # Garante que os valores financeiros sejam números (float)
        df = df.apply(pd.to_numeric, errors='coerce')
        return df
    except Exception as e:
        st.error(f"Erro na leitura do arquivo: {e}")
        return None

# =========================
# SIDEBAR
# =========================
with st.sidebar:
    st.header("📂 Upload de Dados")
    uploaded_file = st.file_uploader("Suba o arquivo 'comdinheiro.csv'", type=["csv", "xlsx"])
    
    if uploaded_file:
        df_raw = load_data(uploaded_file)
        
        if df_raw is not None:
            # Classes EXATAS do seu arquivo (incluindo espaços)
            assets = ['Cash', 'High Yield', 'Investment Grade\n', 'Treasury 10y', 'Equity ', 'Alternatives']
            
            st.subheader("⚖️ Alocação")
            user_weights = {}
            total_w = 0
            for a in assets:
                # Nome amigável para o usuário ver
                display_name = a.replace('\n', '').strip()
                val = st.number_input(f"% {display_name}", 0, 100, 0, step=5)
                user_weights[a] = val / 100
                total_w += val
            
            is_valid = total_w == 100
            if is_valid: st.success(f"Total: {total_w}% ✅")
            else: st.error(f"Soma: {total_w}% (Deve ser 100%)")

# =========================
# DASHBOARD
# =========================
if uploaded_file and is_valid:
    # Retornos Mensais
    rets = df_raw.pct_change().dropna()
    
    # Cálculos de Performance
    user_ret = sum(rets[a] * user_weights[a] for a in assets)
    # Benchmarks (B2 e B3 baseados nas suas colunas)
    b2_ret = (0.10 * rets['Equity ']) + (0.90 * rets['Bloomberg Global Aggregate'])
    
    # Criando Base 100 para Performance
    perf_df = pd.DataFrame(index=rets.index)
    perf_df['Sua Carteira'] = (1 + user_ret).cumprod() * 100
    perf_df['Benchmark B2'] = (1 + b2_ret).cumprod() * 100
    perf_df['CPI'] = (df_raw['CPI'] / df_raw['CPI'].iloc[0]) * 100
    
    # ABAS
    tab1, tab2, tab3 = st.tabs(["Performance", "Composição", "Correlação"])
    
    with tab1:
        st.subheader("📈 Rentabilidade Acumulada")
        st.line_chart(perf_df)
    
    with tab2:
        st.subheader("🧱 Evolução da Composição (Stacked)")
        # Gráfico empilhado usando a Base 100 de cada ativo
        comp_df = pd.DataFrame(index=df_raw.index)
        for a, w in user_weights.items():
            if w > 0:
                comp_df[a.strip()] = w * (df_raw[a] / df_raw[a].iloc[0]) * 100
        
        fig_area = px.area(comp_df, template="plotly_white")
        st.plotly_chart(fig_area, use_container_width=True)
        

    with tab3:
        st.subheader("🎯 Matriz de Correlação")
        corr_df = rets[assets].copy()
        corr_df.columns = [c.strip() for c in corr_df.columns]
        fig_corr = px.imshow(corr_data := corr_df.corr(), text_auto=".2f", color_continuous_scale='RdBu_r')
        st.plotly_chart(fig_corr, use_container_width=True)
        

else:
    st.info("Suba o arquivo e ajuste os pesos para 100% na barra lateral.")