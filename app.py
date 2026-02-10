import streamlit as st
import pandas as pd
import numpy as np
import plotly.graph_objects as go

# 1. CONFIGURAÇÃO DE PÁGINA (Estilo Senior)
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

# 2. FUNÇÃO DE CARREGAMENTO PARA EXCEL
@st.cache_data
def load_offshore_data(file):
    try:
        # Lê Excel (aceita .xlsx e .xls)
        df = pd.read_excel(file)
        
        # Limpeza de nomes de colunas (remove \n e espaços extras)
        df.columns = [str(c).replace('\n', ' ').strip() for c in df.columns]
        
        # Garante que a coluna Date está no formato correto
        df['Date'] = pd.to_datetime(df['Date'], errors='coerce')
        df = df.dropna(subset=['Date']).sort_values('Date').set_index('Date')
        
        # Converte o restante para número
        df = df.apply(pd.to_numeric, errors='coerce')
        return df.fillna(method='ffill') # Preenche lacunas se houver
    except Exception as e:
        st.error(f"Erro ao ler o arquivo Excel: {e}")
        return None

# --- SIDEBAR: INPUTS ---
with st.sidebar:
    st.title("📂 Offshore Setup")
    # Agora aceita Excel
    uploaded_file = st.file_uploader("Upload 'database.xlsx'", type=["xlsx", "xls"])
    
    # Ativos da sua base offshore
    assets = ['Cash', 'High Yield', 'Investment Grade', 'Treasury 10y', 'Equity', 'Alternatives']
    user_weights = {}
    is_valid = False

    if uploaded_file:
        df_raw = load_offshore_data(uploaded_file)
        if df_raw is not None:
            st.subheader("⚖️ Alocação Alvo")
            total_w = 0
            for a in assets:
                # Se o ativo não existir na coluna do Excel, ele avisa
                if a in df_raw.columns:
                    val = st.number_input(f"% {a}", 0, 100, 0, step=5)
                    user_weights[a] = val / 100
                    total_w += val
                else:
                    st.error(f"Coluna '{a}' não encontrada no Excel.")
            
            if total_w == 100:
                st.success("Soma: 100% ✅")
                is_valid = True
            else:
                st.warning(f"Soma atual: {total_w}%")

# --- PROCESSAMENTO ---
if uploaded_file and is_valid:
    # Cálculo de retornos mensais
    rets = df_raw.pct_change().dropna()
    
    # 1. Retorno da Carteira Customizada
    user_ret = sum(rets[a] * user_weights[a] for a in assets if a in rets.columns)
    
    # 2. BENCHMARKS SOLICITADOS
    # Benchmark 1: 100% BBG Global Agg
    b1_agg = rets['Bloomberg Global Aggregate']
    
    # Benchmark 2: 10% MSCI (Equity) + 90% Global Agg
    b2_10_90 = (0.10 * rets['Equity']) + (0.90 * rets['Bloomberg Global Aggregate'])
    
    # Benchmark 3: 20% MSCI (Equity) + 80% Global Agg
    b3_20_80 = (0.20 * rets['Equity']) + (0.80 * rets['Bloomberg Global Aggregate'])
    
    # Benchmark 4: Apenas CPI (Inflação)
    b4_cpi = rets['CPI']

    # Criando Performance Acumulada (Base 100)
    perf_df = pd.DataFrame(index=rets.index)
    perf_df['Sua Carteira'] = (1 + user_ret).cumprod() * 100
    perf_df['100% BBG Global Agg'] = (1 + b1_agg).cumprod() * 100
    perf_df['10/90 (Equity/Agg)'] = (1 + b2_10_90).cumprod() * 100
    perf_df['20/80 (Equity/Agg)'] = (1 + b3_20_80).cumprod() * 100
    perf_df['CPI (Inflação)'] = (1 + b4_cpi).cumprod() * 100

    # --- DASHBOARD VISUAL ---
    st.title("📊 Relatório de Performance Offshore")

    # Gráfico Principal
    fig = go.Figure()
    cores = ['#1C2C54', '#888888', '#A6A6A6', '#D1D1D1', '#FF4B4B']
    for i, col in enumerate(perf_df.columns):
        dash = 'dash' if 'CPI' in col else 'solid'
        fig.add_trace(go.Scatter(x=perf_df.index, y=perf_df[col], name=col,
                                 line=dict(width=3 if i==0 else 1.5, dash=dash, color=cores[i])))
    
    fig.update_layout(template="simple_white", hovermode="x unified", title="Retorno Acumulado")
    st.plotly_chart(fig, use_container_width=True)
    

    # Tabela de Métricas (Igual ao padrão da Senior)
    st.subheader("🎯 Comparativo de Risco e Retorno")
    metrics = []
    for col in perf_df.columns:
        r_anual = (perf_df[col].iloc[-1]/100)**(12/len(perf_df)) - 1
        vol = rets[col].std() * np.sqrt(12) if col in rets else 0 # Simplificado
        # Ajuste para vol correta dos benchmarks calculados
        if col == 'Sua Carteira': vol = user_ret.std() * np.sqrt(12)
        elif col == '100% BBG Global Agg': vol = b1_agg.std() * np.sqrt(12)
        
        metrics.append({
            "Estratégia": col,
            "Retorno Anualizado": f"{r_anual:.2%}",
            "Volatilidade (aa)": f"{vol:.2%}" if vol > 0 else "N/A"
        })
    st.table(pd.DataFrame(metrics))

    # Área de Composição
    st.subheader("🧱 Exposição Histórica")
    comp_df = pd.DataFrame(index=df_raw.index)
    for a, w in user_weights.items():
        if w > 0:
            comp_df[a] = w * (df_raw[a] / df_raw[a].iloc[0]) * 100
    
    fig_stack = go.Figure()
    for col in comp_df.columns:
        fig_stack.add_trace(go.Scatter(x=comp_df.index, y=comp_df[col], name=col, stackgroup='one'))
    
    fig_stack.update_layout(template="simple_white", yaxis_title="Pontos (Base 100)")
    st.plotly_chart(fig_stack, use_container_width=True)

else:
    st.info("👋 Por favor, carregue o arquivo **Excel** e ajuste os pesos para 100% na barra lateral.")