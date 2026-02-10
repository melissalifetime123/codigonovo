import streamlit as st
import pandas as pd
import numpy as np
import plotly.express as px
import plotly.graph_objects as go

# Configuração da Página
st.set_page_config(page_title="Offshore Asset Allocation", layout="wide")

# =========================
# FUNÇÃO DE CARREGAMENTO
# =========================
@st.cache_data
def load_data(file):
    try:
        # Se for Excel (.xlsx), usamos read_excel. Se for CSV, read_csv.
        if file.name.endswith('.csv'):
            df = pd.read_csv(file)
        else:
            df = pd.read_excel(file)
        
        # Limpeza básica: remover colunas totalmente vazias e renomear
        df = df.loc[:, ~df.columns.str.contains('^Unnamed')]
        
        # Ajuste de Data
        df['Date'] = pd.to_datetime(df['Date'])
        df = df.sort_values('Date').set_index('Date')
        
        # Garantir que os dados sejam numéricos
        df = df.apply(pd.to_numeric, errors='coerce').dropna()
        return df
    except Exception as e:
        st.error(f"Erro ao ler o arquivo: {e}")
        return None

# =========================
# BARRA LATERAL (SIDEBAR)
# =========================
with st.sidebar:
    st.header("📂 Base de Dados")
    uploaded_file = st.file_uploader("Suba sua planilha (Excel ou CSV)", type=["xlsx", "csv"])
    
    if uploaded_file:
        df_raw = load_data(uploaded_file)
        
        if df_raw is not None:
            # Classes identificadas no seu arquivo
            assets = ['Cash', 'High Yield', 'Investment Grade\n', 'Treasury 10y', 'Equity ', 'Alternatives']
            
            st.divider()
            st.subheader("⚖️ Definir Pesos (%)")
            
            user_weights = {}
            total_w = 0
            for a in assets:
                clean_name = a.strip()
                # Slider ou Number Input para os pesos
                val = st.number_input(f"% {clean_name}", 0, 100, 0, step=5)
                user_weights[a] = val / 100
                total_w += val
            
            st.divider()
            if total_w == 100:
                st.success(f"✅ Soma: {total_w}%")
                is_valid = True
            else:
                st.error(f"❌ Soma: {total_w}% (Ajuste para 100%)")
                is_valid = False

# =========================
# DASHBOARD PRINCIPAL
# =========================
if uploaded_file and is_valid:
    # 1. Preparar Retornos
    # Como os dados já estão em Base 100 (Price), calculamos a variação percentual
    rets = df_raw.pct_change().dropna()
    
    # 2. Calcular Perfis
    # Sua Carteira
    user_rets = sum(rets[a] * user_weights[a] for a in assets)
    # Benchmarks (Ex: B2 = 10% Equity / 90% Global Agg)
    b2_rets = (0.10 * rets['Equity ']) + (0.90 * rets['Bloomberg Global Aggregate'])
    b3_rets = (0.20 * rets['Equity ']) + (0.80 * rets['Bloomberg Global Aggregate'])
    
    # 3. Criar DataFrame de Performance (Base 100)
    perf_df = pd.DataFrame(index=rets.index)
    perf_df['Sua Carteira'] = (1 + user_rets).cumprod() * 100
    perf_all = perf_df.copy()
    perf_all['B2: 10/90'] = (1 + b2_rets).cumprod() * 100
    perf_all['B3: 20/80'] = (1 + b3_rets).cumprod() * 100
    perf_all['CPI (Inflação)'] = (df_raw['CPI'] / df_raw['CPI'].iloc[0]) * 100

    # --- TABS DO DASHBOARD ---
    tab1, tab2, tab3 = st.tabs(["📈 Performance & Risco", "🧱 Composição Histórica", "🎯 Correlação"])

    with tab1:
        st.subheader("Performance Acumulada")
        fig_perf = px.line(perf_all, template="plotly_white")
        fig_perf.update_traces(patch={"line": {"width": 4}}, selector={"name": "Sua Carteira"})
        st.plotly_chart(fig_perf, use_container_width=True)
        
        # Métricas
        st.subheader("📊 Métricas de Eficiência")
        rf = rets['Cash'].mean() * 12 # Risk free anualizado
        ann_ret = user_rets.mean() * 12
        ann_vol = user_rets.std() * np.sqrt(12)
        sharpe = (ann_ret - rf) / ann_vol
        
        c1, c2, c3 = st.columns(3)
        c1.metric("Retorno Anualizado", f"{ann_ret:.2%}")
        c2.metric("Volatilidade Anual", f"{ann_vol:.2%}")
        c3.metric("Sharpe Ratio", f"{sharpe:.2f}")

    with tab2:
        st.subheader("Visual de Colunas Empilhadas (Contribuição)")
        # Calculando a composição financeira de cada ativo na carteira
        comp_df = pd.DataFrame(index=df_raw.index)
        for a, w in user_weights.items():
            if w > 0:
                comp_df[a.strip()] = w * (df_raw[a] / df_raw[a].iloc[0]) * 100
        
        fig_area = px.area(comp_df, color_discrete_sequence=px.colors.qualitative.T10)
        fig_area.update_layout(yaxis_title="Valor Acumulado (Base 100)", hovermode="x unified")
        st.plotly_chart(fig_area, use_container_width=True)
        

    with tab3:
        st.subheader("Matriz de Correlação")
        # Criamos um DF com os ativos e a carteira final
        corr_data = rets[assets].copy()
        corr_data.columns = [c.strip() for c in corr_data.columns]
        corr_data['SUA CARTEIRA'] = user_rets
        
        matrix = corr_data.corr()
        fig_corr = px.imshow(matrix, text_auto=".2f", color_continuous_scale='RdBu_r', zmin=-1, zmax=1)
        st.plotly_chart(fig_corr, use_container_width=True)
        

else:
    st.info("Aguardando upload do arquivo e configuração de 100% dos pesos.")