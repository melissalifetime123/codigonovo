import streamlit as st
import pandas as pd
import numpy as np
import plotly.graph_objects as go

# 1. CONFIGURAÇÃO DE PÁGINA (Mantendo o estilo Senior)
st.set_page_config(page_title="Offshore Portfolio Analytics", layout="wide")

st.markdown("""
    <style>
    [data-testid="stDataFrame"] { width: 100%; }
    h1, h2, h3 { color: #1C2C54; font-family: 'Segoe UI', sans-serif; }
    .metric-container { 
        background-color: #F8F9FA; 
        padding: 15px; border-radius: 10px; border-left: 5px solid #1C2C54;
    }
    </style>
    """, unsafe_allow_html=True)

# 2. FUNÇÃO DE CARREGAMENTO (Adaptada para Offshore)
@st.cache_data
def load_offshore_data(file):
    try:
        df = pd.read_csv(file)
        # Limpeza agressiva de nomes de colunas
        df.columns = [c.replace('\n', ' ').replace('"', '').strip() for c in df.columns]
        
        # Tratamento de Data
        df['Date'] = pd.to_datetime(df['Date'], errors='coerce')
        df = df.dropna(subset=['Date']).sort_values('Date').set_index('Date')
        
        # Converte para numérico e remove colunas vazias
        df = df.apply(pd.to_numeric, errors='coerce')
        df = df.loc[:, df.columns.notna()]
        return df.dropna(how='all')
    except Exception as e:
        st.error(f"Erro no processamento: {e}")
        return None

# --- SIDEBAR: INPUTS ---
with st.sidebar:
    st.title("📂 Offshore Setup")
    uploaded_file = st.file_uploader("Upload 'comdinheiro.csv'", type=["csv"])
    
    # Lista de Ativos conforme sua base
    assets = ['Cash', 'High Yield', 'Investment Grade', 'Treasury 10y', 'Equity', 'Alternatives']
    user_weights = {}
    is_valid = False

    if uploaded_file:
        df_raw = load_offshore_data(uploaded_file)
        if df_raw is not None:
            st.subheader("⚖️ Alocação Alvo")
            total_w = 0
            for a in assets:
                val = st.number_input(f"% {a}", 0, 100, 0, step=5)
                user_weights[a] = val / 100
                total_w += val
            
            if total_w == 100:
                st.success("Soma: 100% ✅")
                is_valid = True
            else:
                st.warning(f"Soma: {total_w}% (Ajuste para 100%)")

# --- PROCESSAMENTO E DASHBOARD ---
if uploaded_file and is_valid:
    # 3. CÁLCULO DE RETORNOS
    rets = df_raw.pct_change().dropna()
    
    # Carteira do Usuário
    user_ret = sum(rets[a] * user_weights[a] for a in assets)
    
    # 4. BENCHMARKS OFFSHORE (SOLICITADOS)
    # Benchmark 1: 100% BBG Global Agg
    b1_global_agg = rets['Bloomberg Global Aggregate']
    
    # Benchmark 2: 10% MSCI (Equity) + 90% Global Agg
    b2_10_90 = (0.10 * rets['Equity']) + (0.90 * rets['Bloomberg Global Aggregate'])
    
    # Benchmark 3: 20% MSCI (Equity) + 80% Global Agg
    b3_20_80 = (0.20 * rets['Equity']) + (0.80 * rets['Bloomberg Global Aggregate'])
    
    # Benchmark 4: CPI (Inflação) - Usando variação do índice
    b4_cpi = rets['CPI']

    # 5. CONSTRUÇÃO DA PERFORMANCE ACUMULADA (Base 100)
    perf_df = pd.DataFrame(index=rets.index)
    perf_df['Sua Carteira'] = (1 + user_ret).cumprod() * 100
    perf_df['100% BBG Global Agg'] = (1 + b1_global_agg).cumprod() * 100
    perf_df['10/90 (Equity/Agg)'] = (1 + b2_10_90).cumprod() * 100
    perf_df['20/80 (Equity/Agg)'] = (1 + b3_20_80).cumprod() * 100
    perf_df['CPI (Inflação)'] = (1 + b4_cpi).cumprod() * 100

    # --- VISUALIZAÇÃO ESTILO SENIOR ---
    st.title("📊 Análise de Performance Offshore")
    
    # Gráfico de Linha Principal
    fig = go.Figure()
    for col in perf_df.columns:
        width = 3 if col == 'Sua Carteira' else 1.5
        dash = 'dash' if 'CPI' in col else 'solid'
        fig.add_trace(go.Scatter(x=perf_df.index, y=perf_df[col], name=col,
                                 line=dict(width=width, dash=dash)))
    
    fig.update_layout(template="simple_white", hovermode="x unified", title="Evolução Patrimonial (Base 100)")
    st.plotly_chart(fig, use_container_width=True)
    

    # --- TABELA DE MÉTRICAS ---
    st.subheader("🎯 Métricas de Risco e Retorno")
    
    def get_metrics(series):
        total_ret = (series.iloc[-1] / series.iloc[0]) - 1
        vol = series.pct_change().std() * np.sqrt(12)
        return f"{total_ret:.2%}", f"{vol:.2%}"

    m_data = []
    for col in perf_df.columns:
        ret, vol = get_metrics(perf_df[col])
        m_data.append({"Estratégia": col, "Retorno Total": ret, "Volatilidade (aa)": vol})
    
    st.table(pd.DataFrame(m_data))

    # --- COMPOSIÇÃO DE CARTEIRA ---
    st.subheader("🧱 Decomposição por Classe")
    comp_df = pd.DataFrame(index=df_raw.index)
    for a, w in user_weights.items():
        if w > 0:
            comp_df[a] = w * (df_raw[a] / df_raw[a].iloc[0]) * 100
    
    fig_area = go.Figure()
    for a in assets:
        if a in comp_df.columns:
            fig_area.add_trace(go.Scatter(x=comp_df.index, y=comp_df[a], name=a, stackgroup='one'))
    
    st.plotly_chart(fig_area, use_container_width=True)

else:
    st.info("💡 Aguardando upload do arquivo e ajuste dos pesos (100%) na barra lateral.")