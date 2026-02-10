import streamlit as st
import pandas as pd
import numpy as np
import plotly.graph_objects as go
import plotly.express as px

# =========================
# CONFIGURAÇÃO DA PÁGINA
# =========================
st.set_page_config(page_title="Asset Allocation Offshore", layout="wide")
st.title("📊 Asset Allocation | Offshore Dashboard")

# =========================
# CARREGAMENTO DE DADOS
# =========================
@st.cache_data
def load_offshore_data(file):
    # Lemos as duas primeiras linhas para capturar Classes e Tickers
    header_df = pd.read_csv(file, nrows=2, header=None)
    classes = header_df.iloc[0].tolist()
    
    # Carregamos o corpo dos dados (pulando a linha de tickers para o Pandas não se confundir)
    df = pd.read_csv(file, skiprows=[1])
    df.columns = classes # Nomeamos as colunas com as Classes
    
    # Tratamento de Data
    df['Date'] = pd.to_datetime(df['Date'])
    df = df.sort_values('Date').set_index('Date')
    
    # Garantir que tudo é numérico e remover NAs iniciais (filtro de data comum)
    df = df.apply(pd.to_numeric, errors='coerce')
    df = df.dropna()
    
    return df

uploaded_file = st.file_uploader("Suba seu arquivo CSV Offshore", type=["csv"])

if uploaded_file:
    df = load_offshore_data(uploaded_file)
    
    # =========================
    # CÁLCULO DOS 4 BENCHMARKS
    # =========================
    # Calculamos os retornos mensais primeiro
    returns = df.pct_change().dropna()
    
    # Criando os Benchmarks Sintéticos (Base 100)
    # B1: 100% BBG Global Agg
    df['B1: 100% Global Agg'] = df['Bloomberg Global Aggregate']
    
    # B2: 10% MSCI (Equity) + 90% Global Agg
    b2_ret = (0.10 * returns['Equity ']) + (0.90 * returns['Bloomberg Global Aggregate'])
    df['B2: 10/90 Hybrid'] = 100 * (1 + b2_ret).cumprod()
    
    # B3: 20% MSCI (Equity) + 80% Global Agg
    b3_ret = (0.20 * returns['Equity ']) + (0.80 * returns['Bloomberg Global Aggregate'])
    df['B3: 20/80 Hybrid'] = 100 * (1 + b3_ret).cumprod()
    
    # B4: CPI (Já está na base, vamos apenas renomear para clareza)
    df['B4: CPI Inflation'] = df['CPI']

    # Recalculamos retornos com os novos benchmarks incluídos
    all_returns = df.pct_change().dropna()

    # =========================
    # DASHBOARD - VISUALIZAÇÃO
    # =========================
    
    # Seletor de Ativos para o Gráfico
    st.subheader("📈 Performance Relativa (Base 100)")
    selected_assets = st.multiselect(
        "Selecione Ativos e Benchmarks para Comparar:",
        options=df.columns.tolist(),
        default=['Equity ', 'B1: 100% Global Agg', 'B2: 10/90 Hybrid', 'B4: CPI Inflation']
    )

    if selected_assets:
        fig = go.Figure()
        for asset in selected_assets:
            # Normalizando para base 100 no início do período selecionado
            series = (df[asset] / df[asset].iloc[0]) * 100
            fig.add_trace(go.Scatter(x=df.index, y=series, name=asset))
        
        fig.update_layout(template="simple_white", hovermode="x unified")
        st.plotly_chart(fig, use_container_width=True)

    # =========================
    # TABELA DE MÉTRICAS
    # =========================
    st.subheader("📊 Métricas de Risco e Retorno (Anualizado)")
    
    # Assumindo 12 meses para anualização (dados mensais)
    ann_ret = (1 + all_returns.mean())**12 - 1
    ann_vol = all_returns.std() * np.sqrt(12)
    
    # Sharpe Ratio usando a coluna 'Cash' como Risk-Free
    rf = all_returns['Cash'].mean() * 12
    sharpe = (ann_ret - rf) / ann_vol
    
    metrics_df = pd.DataFrame({
        "Retorno Anual": ann_ret,
        "Volatilidade": ann_vol,
        "Sharpe Ratio": sharpe
    }).loc[selected_assets]

    st.dataframe(metrics_df.style.format("{:.2%}", subset=["Retorno Anual", "Volatilidade"]).format("{:.2f}", subset=["Sharpe Ratio"]))

    # =========================
    # MATRIZ DE CORRELAÇÃO
    # =========================
    st.subheader("🎯 Matriz de Correlação")
    corr = all_returns[selected_assets].corr()
    fig_corr = px.imshow(corr, text_auto=True, color_continuous_scale='RdBu_r', zmin=-1, zmax=1)
    st.plotly_chart(fig_corr, use_container_width=True)

else:
    st.info("Aguardando o upload do arquivo CSV para processar a análise offshore.")