import streamlit as st
import pandas as pd
import numpy as np
import plotly.graph_objects as go

# 1. CONFIGURAÇÃO DE PÁGINA (Padrão Sênior)
st.set_page_config(page_title="Offshore Portfolio Analytics", layout="wide")

st.markdown("""
    <style>
    [data-testid="stDataFrame"] { width: 100%; }
    h1, h2, h3 { color: #1C2C54; font-family: 'Segoe UI', sans-serif; }
    .metric-container { 
        background-color: #F8F9FA; padding: 15px; border-radius: 10px; 
        border-left: 5px solid #1C2C54; margin-top: 20px;
    }
    </style>
    """, unsafe_allow_html=True)

# 2. FUNÇÃO DE CARREGAMENTO
@st.cache_data
def load_offshore_data(file):
    try:
        df = pd.read_excel(file)
        # Limpeza agressiva de nomes de colunas
        df.columns = [str(c).replace('\n', ' ').replace('"', '').strip() for c in df.columns]
        df['Date'] = pd.to_datetime(df['Date'], errors='coerce')
        df = df.dropna(subset=['Date']).sort_values('Date').set_index('Date')
        return df.apply(pd.to_numeric, errors='coerce').ffill()
    except Exception as e:
        st.error(f"Erro ao ler Excel: {e}")
        return None

# --- SIDEBAR: CONFIGURAÇÕES ---
with st.sidebar:
    st.title("📂 Offshore Setup")
    uploaded_file = st.file_uploader("Upload 'database.xlsx'", type=["xlsx", "xls"])
    
    st.subheader("⚖️ Matriz de Perfis")
    # Tabela de pesos pré-preenchida para não travar o início
    df_perfis = pd.DataFrame({
        "Classe": ['Cash', 'High Yield', 'Investment Grade', 'Treasury 10y', 'Equity', 'Alternatives'],
        "Conservador": [70, 0, 20, 10, 0, 0],
        "Moderado": [20, 10, 30, 10, 20, 10],
        "Arrojado": [5, 15, 15, 5, 45, 15]
    })
    edited_df = st.data_editor(df_perfis, hide_index=True)
    perfil_selecionado = st.selectbox("Perfil em Destaque", ["Conservador", "Moderado", "Arrojado"])

# --- PROCESSAMENTO PRINCIPAL ---
if uploaded_file:
    df_raw = load_offshore_data(uploaded_file)
    
    if df_raw is not None:
        # A. CÁLCULO DOS RETORNOS (Independente de pesos)
        rets = df_raw.pct_change().dropna()
        
        # Benchmarks Solicitados
        b1_agg = rets['Bloomberg Global Aggregate']
        b2_10_90 = (0.10 * rets['Equity']) + (0.90 * rets['Bloomberg Global Aggregate'])
        b3_20_80 = (0.20 * rets['Equity']) + (0.80 * rets['Bloomberg Global Aggregate'])
        b4_cpi = rets['CPI']

        # B. CÁLCULO DA CARTEIRA DO PERFIL (Opcional)
        weights = edited_df.set_index("Classe")[perfil_selecionado] / 100
        user_ret = sum(rets[asset] * weights[asset] for asset in weights.index if asset in rets.columns)
        
        # DataFrame de Performance (Base 100)
        perf_df = pd.DataFrame(index=rets.index)
        perf_df['100% BBG Global Agg'] = (1 + b1_agg).cumprod() * 100
        perf_df['10/90 (Equity/Agg)'] = (1 + b2_10_90).cumprod() * 100
        perf_df['20/80 (Equity/Agg)'] = (1 + b3_20_80).cumprod() * 100
        perf_df['CPI (Inflação)'] = (1 + b4_cpi).cumprod() * 100
        
        # Só adiciona o perfil se a soma for 100%
        if abs(weights.sum() - 1.0) < 0.01:
            perf_df[f'Perfil: {perfil_selecionado}'] = (1 + user_ret).cumprod() * 100

        # --- DASHBOARD VISUAL ---
        st.title("📊 Offshore Performance Dashboard")

        # 1. Gráfico de Performance
        fig = go.Figure()
        # Cores Lifetime/Senior
        colors = {'100% BBG Global Agg': '#94a3b8', '10/90 (Equity/Agg)': '#64748b', 
                  '20/80 (Equity/Agg)': '#334155', 'CPI (Inflação)': '#ef4444'}
        colors[f'Perfil: {perfil_selecionado}'] = '#1e293b'

        for col in perf_df.columns:
            is_perfil = 'Perfil' in col
            fig.add_trace(go.Scatter(
                x=perf_df.index, y=perf_df[col], name=col,
                line=dict(width=4 if is_perfil else 2, 
                          dash='dash' if 'CPI' in col else 'solid',
                          color=colors.get(col))
            ))
        
        fig.update_layout(template="simple_white", hovermode="x unified", title="Retorno Acumulado")
        st.plotly_chart(fig, use_container_width=True)
        

        # 2. Tabela de Métricas Rápidas
        st.subheader("🎯 Estatísticas do Período")
        
        metrics_list = []
        for col in perf_df.columns:
            # Retorno total
            r_total = (perf_df[col].iloc[-1] / 100) - 1
            # Volatilidade (aa)
            if col in [f'Perfil: {perfil_selecionado}']:
                vol = user_ret.std() * np.sqrt(12)
            elif col == '100% BBG Global Agg':
                vol = b1_agg.std() * np.sqrt(12)
            else:
                vol = 0 # Para benchmarks compostos, cálculo simplificado ou omitido
            
            metrics_list.append({
                "Estratégia": col,
                "Retorno Total": f"{r_total:.2%}",
                "Volatilidade (aa)": f"{vol:.2%}" if vol > 0 else "---"
            })
        
        st.table(pd.DataFrame(metrics_list))

        # 3. Composição (Gráfico de área apenas se o perfil estiver ativo)
        if f'Perfil: {perfil_selecionado}' in perf_df.columns:
            st.subheader(f"🧱 Alocação Interna: {perfil_selecionado}")
            comp_df = pd.DataFrame(index=df_raw.index)
            for asset, w in weights.items():
                if w > 0:
                    comp_df[asset] = w * (df_raw[asset] / df_raw[asset].iloc[0]) * 100
            
            fig_area = go.Figure()
            for col in comp_df.columns:
                fig_area.add_trace(go.Scatter(x=comp_df.index, y=comp_df[col], name=col, stackgroup='one'))
            fig_area.update_layout(template="simple_white", yaxis_title="Pontos")
            st.plotly_chart(fig_area, use_container_width=True)

else:
    st.info("👋 **Aguardando arquivo.** Suba o seu Excel para visualizar os benchmarks offshore instantaneamente.")