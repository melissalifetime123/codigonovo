import streamlit as st
import pandas as pd
import numpy as np
import plotly.graph_objects as go

# 1. CONFIGURAÇÃO DE PÁGINA (Estilo Lifetime/Senior)
st.set_page_config(page_title="Offshore Portfolio Analytics", layout="wide")

st.markdown("""
    <style>
    [data-testid="stDataFrame"] { width: 100%; }
    h1, h2, h3 { color: #1C2C54; font-family: 'Segoe UI', sans-serif; }
    .stTabs [data-baseweb="tab-list"] { gap: 24px; }
    .stTabs [data-baseweb="tab"] { height: 50px; white-space: pre-wrap; background-color: #f0f2f6; border-radius: 4px 4px 0 0; gap: 1px; padding: 10px; }
    .stTabs [aria-selected="true"] { background-color: #1C2C54 !important; color: white !important; }
    </style>
    """, unsafe_allow_html=True)

# 2. FUNÇÃO DE CARREGAMENTO
@st.cache_data
def load_offshore_data(file):
    try:
        df = pd.read_excel(file)
        # Limpeza de nomes de colunas
        df.columns = [str(c).replace('\n', ' ').replace('"', '').strip() for c in df.columns]
        df['Date'] = pd.to_datetime(df['Date'], errors='coerce')
        df = df.dropna(subset=['Date']).sort_values('Date').set_index('Date')
        return df.apply(pd.to_numeric, errors='coerce').ffill()
    except Exception as e:
        st.error(f"Erro ao ler Excel: {e}")
        return None

# --- SIDEBAR: APENAS UPLOAD ---
with st.sidebar:
    st.title("📂 Dados")
    uploaded_file = st.file_uploader("Upload 'database.xlsx'", type=["xlsx", "xls"])
    st.info("O dashboard será atualizado automaticamente ao subir o arquivo.")

# --- ÁREA PRINCIPAL ---
if uploaded_file:
    df_raw = load_offshore_data(uploaded_file)
    
    if df_raw is not None:
        st.title("📊 Offshore Performance Analytics")
        
        # COLUNAS PARA PESOS E MÉTRICAS
        col_pesos, col_espaco, col_resumo = st.columns([1.5, 0.1, 1])
        
        with col_pesos:
            st.subheader("⚖️ Matriz de Alocação por Perfil")
            df_perfis = pd.DataFrame({
                "Classe": ['Cash', 'High Yield', 'Investment Grade', 'Treasury 10y', 'Equity', 'Alternatives'],
                "Conservador": [70, 0, 20, 10, 0, 0],
                "Moderado": [20, 10, 30, 10, 20, 10],
                "Arrojado": [5, 15, 15, 5, 45, 15]
            })
            # Tabela editável no centro da página
            edited_df = st.data_editor(df_perfis, hide_index=True, use_container_width=True)
            perfil_selecionado = st.radio("Selecione o perfil para destacar no gráfico:", ["Conservador", "Moderado", "Arrojado"], horizontal=True)

        # CÁLCULOS
        rets = df_raw.pct_change().dropna()
        weights = edited_df.set_index("Classe")[perfil_selecionado] / 100
        
        # Benchmarks
        b1_agg = rets['Bloomberg Global Aggregate']
        b2_10_90 = (0.10 * rets['Equity']) + (0.90 * rets['Bloomberg Global Aggregate'])
        b3_20_80 = (0.20 * rets['Equity']) + (0.80 * rets['Bloomberg Global Aggregate'])
        b4_cpi = rets['CPI']
        user_ret = sum(rets[asset] * weights[asset] for asset in weights.index if asset in rets.columns)

        with col_resumo:
            st.subheader("🎯 KPIs do Perfil")
            ret_total = ((1 + user_ret).prod() - 1)
            vol_anual = user_ret.std() * np.sqrt(12)
            
            st.markdown(f"""
            <div style="background-color:#F8F9FA; padding:20px; border-radius:10px; border-left: 5px solid #1C2C54;">
                <p style="margin-bottom:5px;">Retorno Acumulado</p>
                <h2 style="margin:0;">{ret_total:.2%}</h2>
                <p style="margin-top:15px; margin-bottom:5px;">Volatilidade (aa)</p>
                <h2 style="margin:0;">{vol_anual:.2%}</h2>
            </div>
            """, unsafe_allow_html=True)

        # GRÁFICOS EM ABAS
        st.divider()
        tab_perf, tab_comp = st.tabs(["📈 Performance Comparativa", "🧱 Composição da Carteira"])
        
        perf_df = pd.DataFrame(index=rets.index)
        perf_df['100% BBG Global Agg'] = (1 + b1_agg).cumprod() * 100
        perf_df['10/90 (Equity/Agg)'] = (1 + b2_10_90).cumprod() * 100
        perf_df['20/80 (Equity/Agg)'] = (1 + b3_20_80).cumprod() * 100
        perf_df['CPI (Inflação)'] = (1 + b4_cpi).cumprod() * 100
        perf_df[f'Perfil: {perfil_selecionado}'] = (1 + user_ret).cumprod() * 100

        with tab_perf:
            fig = go.Figure()
            # Estilização de cores
            cores = {'CPI (Inflação)': '#ef4444', f'Perfil: {perfil_selecionado}': '#1C2C54'}
            
            for col in perf_df.columns:
                is_destaque = col == f'Perfil: {perfil_selecionado}'
                fig.add_trace(go.Scatter(
                    x=perf_df.index, y=perf_df[col], name=col,
                    line=dict(width=4 if is_destaque else 2, 
                              dash='dash' if 'CPI' in col else 'solid',
                              color=cores.get(col))
                ))
            fig.update_layout(template="simple_white", hovermode="x unified", height=500)
            st.plotly_chart(fig, use_container_width=True)
            

        with tab_comp:
            comp_df = pd.DataFrame(index=df_raw.index)
            for asset, w in weights.items():
                if w > 0:
                    comp_df[asset] = w * (df_raw[asset] / df_raw[asset].iloc[0]) * 100
            
            fig_area = go.Figure()
            for col in comp_df.columns:
                fig_area.add_trace(go.Scatter(x=comp_df.index, y=comp_df[col], name=col, stackgroup='one'))
            fig_area.update_layout(template="simple_white", height=500, yaxis_title="Contribuição Base 100")
            st.plotly_chart(fig_area, use_container_width=True)

else:
    st.info("👋 **Aguardando arquivo.** Por favor, carregue o 'database.xlsx' na barra lateral para iniciar a análise.")