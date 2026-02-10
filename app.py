import streamlit as st
import pandas as pd
import numpy as np
import plotly.express as px

st.set_page_config(page_title="Portfolio Offshore", layout="wide")

# 1. Função de carregamento com limpeza de nomes
@st.cache_data
def load_data(file):
    try:
        df = pd.read_csv(file)
        # Limpa colunas vazias
        df = df.loc[:, ~df.columns.str.contains('^Unnamed')]
        df = df.dropna(axis=1, how='all')
        
        # LIMPEZA CRUCIAL: Remove espaços e quebras de linha dos nomes das colunas
        df.columns = [c.replace('\n', ' ').strip() for c in df.columns]
        
        df['Date'] = pd.to_datetime(df['Date'], errors='coerce')
        df = df.dropna(subset=['Date']).sort_values('Date').set_index('Date')
        df = df.apply(pd.to_numeric, errors='coerce')
        return df
    except Exception as e:
        st.error(f"Erro ao ler arquivo: {e}")
        return None

# Inicializa variáveis para evitar o erro "NameError"
is_valid = False
user_weights = {}

with st.sidebar:
    st.header("📂 Upload de Dados")
    uploaded_file = st.file_uploader("Suba o arquivo 'comdinheiro.csv'", type=["csv"])
    
    if uploaded_file:
        df_raw = load_data(uploaded_file)
        
        if df_raw is not None:
            # Lista de ativos (agora com nomes limpos pelo código acima)
            assets = ['Cash', 'High Yield', 'Investment Grade', 'Treasury 10y', 'Equity', 'Alternatives']
            
            st.subheader("⚖️ Alocação")
            total_w = 0
            for a in assets:
                val = st.number_input(f"% {a}", 0, 100, 0, step=5)
                user_weights[a] = val / 100
                total_w += val
            
            is_valid = (total_w == 100)
            if is_valid:
                st.success(f"Total: {total_w}% ✅")
            else:
                st.warning(f"Soma atual: {total_w}% (Ajuste para 100%)")

# DASHBOARD
if uploaded_file and is_valid:
    # Cálculo de Retornos
    rets = df_raw.pct_change().dropna()
    
    # Carteira do Usuário
    user_ret = sum(rets[a] * user_weights[a] for a in assets)
    
    # Benchmarks (Ajustados para os nomes limpos)
    # B2 = 10% Equity / 90% Global Agg
    b2_ret = (0.10 * rets['Equity']) + (0.90 * rets['Bloomberg Global Aggregate'])
    
    # Criando DataFrame de Performance
    perf_df = pd.DataFrame(index=rets.index)
    perf_df['Sua Carteira'] = (1 + user_ret).cumprod() * 100
    perf_df['Benchmark B2'] = (1 + b2_ret).cumprod() * 100
    perf_df['CPI (Inflação)'] = (df_raw['CPI'] / df_raw['CPI'].iloc[0]) * 100

    # Visualização
    tab1, tab2 = st.tabs(["📈 Performance", "🧱 Composição"])
    
    with tab1:
        st.subheader("Retorno Acumulado (Base 100)")
        st.line_chart(perf_df)
        
    with tab2:
        st.subheader("Evolução do Patrimônio por Classe")
        comp_df = pd.DataFrame(index=df_raw.index)
        for a, w in user_weights.items():
            if w > 0:
                # Mostra quanto cada classe vale dentro da base 100 original
                comp_df[a] = w * (df_raw[a] / df_raw[a].iloc[0]) * 100
        
        fig_area = px.area(comp_df, template="plotly_white", labels={"value": "Pontos", "variable": "Ativo"})
        st.plotly_chart(fig_area, use_container_width=True)
        

else:
    if not uploaded_file:
        st.info("👋 Boas-vindas! Comece subindo o seu arquivo CSV na barra lateral.")
    elif not is_valid:
        st.info("⚠️ Ajuste os pesos da carteira na barra lateral para que a soma seja exatamente 100%.")