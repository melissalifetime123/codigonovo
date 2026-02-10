import streamlit as st
import pandas as pd
import numpy as np
import plotly.express as px
import plotly.graph_objects as go

# Configuração da Página
st.set_page_config(page_title="Gestão de Carteira Offshore", layout="wide")

# =========================
# FUNÇÃO DE CARREGAMENTO DE DADOS
# =========================
@st.cache_data
def load_data(file):
    try:
        # Lê o ficheiro (ajustado para a estrutura que enviaste)
        df = pd.read_csv(file)
        
        # Limpa colunas vazias (como aquela entre Alternatives e CPI)
        df = df.loc[:, ~df.columns.str.contains('^Unnamed')]
        
        # Converte Data
        df['Date'] = pd.to_datetime(df['Date'])
        df = df.sort_values('Date').set_index('Date')
        
        # Garante que todos os valores são numéricos
        df = df.apply(pd.to_numeric, errors='coerce').dropna()
        return df
    except Exception as e:
        st.error(f"Erro ao carregar o ficheiro: {e}")
        return None

# =========================
# BARRA LATERAL - INPUT DE PESOS
# =========================
with st.sidebar:
    st.header("📂 Configuração")
    uploaded_file = st.file_uploader("Carrega a tua base (CSV ou Excel)", type=["csv", "xlsx"])
    
    if uploaded_file:
        data = load_data(uploaded_file)
        
        if data is not None:
            # Classes exatas do teu ficheiro
            assets = ['Cash', 'High Yield', 'Investment Grade\n', 'Treasury 10y', 'Equity ', 'Alternatives']
            
            st.subheader("⚖️ Alocação por Classe")
            weights = {}
            total_w = 0
            
            for asset in assets:
                clean_name = asset.replace('\n', '').strip()
                val = st.number_input(f"% {clean_name}", min_value=0, max_value=100, value=0, step=5)
                weights[asset] = val / 100
                total_w += val
            
            st.divider()
            if total_w == 100:
                st.success(f"Total: {total_w}% ✅")
                valid_setup = True
            else:
                st.error(f"Total: {total_w}% (Deve ser 100%)")
                valid_setup = False

# =========================
# PROCESSAMENTO E DASHBOARD
# =========================
if uploaded_file and valid_setup:
    # 1. Cálculo de Retornos Mensais
    rets = data.pct_change().dropna()
    
    # 2. Performance da "Sua Carteira"
    user_portfolio_rets = sum(rets[asset] * weights[asset] for asset in assets)
    
    # 3. Benchmarks Híbridos (Ex: B2 = 10% Equity / 90% Global Agg)
    b2_rets = (0.10 * rets['Equity ']) + (0.90 * rets['Bloomberg Global Aggregate'])
    b3_rets = (0.20 * rets['Equity ']) + (0.80 * rets['Bloomberg Global Aggregate'])
    
    # 4. DataFrames de Performance (Base 100)
    perf_df = pd.DataFrame(index=data.index)
    perf_df['Sua Carteira'] = (1 + user_portfolio_rets).cumprod() * 100
    perf_df['B2: 10/90 Hybrid'] = (1 + b2_rets).cumprod() * 100
    perf_df['B3: 20/80 Hybrid'] = (1 + b3_rets).cumprod() * 100
    perf_df['CPI (Inflação)'] = (data['CPI'] / data['CPI'].iloc[0]) * 100
    perf_df.iloc[0] = 100 # Garantir início em 100

    # --- LAYOUT DE ABAS ---
    tab1, tab2, tab3 = st.tabs(["📈 Comparativo Geral", "🧱 Composição (Stacked)", "🎯 Matriz de Correlação"])

    with tab1:
        st.subheader("Performance Acumulada")
        fig_line = px.line(perf_df, template="plotly_white")
        fig_line.update_traces(patch={"line": {"width": 4}}, selector={"name": "Sua Carteira"})
        st.plotly_chart(fig_line, use_container_width=True)
        
        # Métricas de Risco/Retorno
        st.divider()
        c1, c2, c3 = st.columns(3)
        
        # Cálculo Sharpe (usando Cash como Risk-Free)
        rf_anual = (1 + rets['Cash'].mean())**12 - 1
        ret_anual = (1 + user_portfolio_rets.mean())**12 - 1
        vol_anual = user_portfolio_rets.std() * np.sqrt(12)
        sharpe = (ret_anual - rf_anual) / vol_anual
        
        c1.metric("Retorno Anualizado", f"{ret_anual:.2%}")
        c2.metric("Volatilidade Anual", f"{vol_anual:.2%}")
        c3.metric("Sharpe Ratio", f"{sharpe:.2f}")

    with tab2:
        st.subheader("Anatomia da Carteira (Evolução dos Ativos)")
        # Cálculo da composição empilhada
        stacked_df = pd.DataFrame(index=data.index)
        for asset, w in weights.items():
            if w > 0:
                stacked_df[asset.strip()] = w * (data[asset] / data[asset].iloc[0]) * 100
        
        fig_area = px.area(stacked_df, color_discrete_sequence=px.colors.qualitative.T10)
        fig_area.update_layout(yaxis_title="Contribuição (Base 100)", hovermode="x unified")
        st.plotly_chart(fig_area, use_container_width=True)
        

    with tab3:
        st.subheader("Matriz de Correlação")
        # Criar matriz com ativos + carteira final
        corr_df = rets[assets].copy()
        corr_df.columns = [c.strip() for c in corr_df.columns]
        corr_df['SUA CARTEIRA'] = user_portfolio_rets
        
        corr_matrix = corr_df.corr()
        fig_corr = px.imshow(corr_matrix, text_auto=".2f", color_continuous_scale='RdBu_r', zmin=-1, zmax=1)
        st.plotly_chart(fig_corr, use_container_width=True)
        

else:
    st.info("💡 Por favor, carrega o ficheiro e ajusta os pesos na barra lateral para 100%.")