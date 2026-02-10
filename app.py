import streamlit as st
import pandas as pd
import numpy as np
import plotly.graph_objects as go
import plotly.express as px

# =========================
# CONFIGURAÇÃO E ESTILO
# =========================
st.set_page_config(page_title="Asset Allocation Offshore", layout="wide")

@st.cache_data
def load_data(file):
    # Tratamento para o seu CSV com duplo cabeçalho
    header = pd.read_csv(file, nrows=0).columns.tolist()
    df = pd.read_csv(file, skiprows=[1])
    df.columns = header
    df = df.loc[:, ~df.columns.str.contains('^Unnamed')]
    df['Date'] = pd.to_datetime(df['Date'])
    df = df.set_index('Date').apply(pd.to_numeric, errors='coerce').dropna()
    return df

# =========================
# SIDEBAR - FILTROS E PESOS
# =========================
with st.sidebar:
    st.header("⚙️ Painel de Alocação")
    uploaded_file = st.file_uploader("Suba o database Offshore (CSV)", type=["csv"])
    
    if uploaded_file:
        raw_df = load_data(uploaded_file)
        # Classes exatas da sua planilha
        assets = ['Cash', 'High Yield', 'Investment Grade\n', 'Treasury 10y', 'Equity ', 'Alternatives']
        
        st.subheader("Simular Sua Carteira")
        user_weights = {}
        total_w = 0
        for a in assets:
            val = st.number_input(f"% {a.strip()}", 0, 100, 0, step=5)
            user_weights[a] = val / 100
            total_w += val
        
        valid = total_w == 100
        if valid: 
            st.success(f"✅ Soma: {total_w}%")
        else: 
            st.error(f"❌ Soma: {total_w}% (Ajuste para 100%)")

# =========================
# PROCESSAMENTO DOS DADOS
# =========================
if uploaded_file and valid:
    rets = raw_df.pct_change().dropna()
    
    # 1. Séries de Retorno dos Perfis
    user_ret = sum(rets[a] * user_weights[a] for a in assets)
    b2_ret = (0.10 * rets['Equity ']) + (0.90 * rets['Bloomberg Global Aggregate'])
    b3_ret = (0.20 * rets['Equity ']) + (0.80 * rets['Bloomberg Global Aggregate'])

    # 2. Lógica para as Colunas Empilhadas (Base 100)
    def calc_stacked(w_dict, prices):
        stack_df = pd.DataFrame(index=prices.index)
        for asset, w in w_dict.items():
            if w > 0:
                stack_df[asset.strip()] = w * (prices[asset] / prices[asset].iloc[0]) * 100
        return stack_df

    comp_user = calc_stacked(user_weights, raw_df)
    comp_b2 = calc_stacked({'Equity ': 0.10, 'Bloomberg Global Aggregate': 0.90}, raw_df)
    comp_b3 = calc_stacked({'Equity ': 0.20, 'Bloomberg Global Aggregate': 0.80}, raw_df)

    # =========================
    # DASHBOARD PRINCIPAL
    # =========================
    st.title("📊 Asset Allocation Offshore | Dash Final")
    
    tab1, tab2, tab3 = st.tabs(["📈 Performance", "🧱 Composição (Stacked)", "🎯 Correlação"])

    with tab1:
        st.subheader("Performance Acumulada vs Benchmarks")
        perf_all = pd.DataFrame(index=raw_df.index)
        perf_all['Sua Carteira'] = (1 + user_ret).cumprod() * 100
        perf_all['B2: 10/90 Hybrid'] = (1 + b2_ret).cumprod() * 100
        perf_all['B3: 20/80 Hybrid'] = (1 + b3_ret).cumprod() * 100
        perf_all['CPI (Inflação)'] = (raw_df['CPI'] / raw_df['CPI'].iloc[0]) * 100
        perf_all.iloc[0] = 100
        
        fig_line = px.line(perf_all, template="plotly_white")
        fig_line.update_traces(patch={"line": {"width": 4}}, selector={"name": "Sua Carteira"})
        st.plotly_chart(fig_line, use_container_width=True)

        # KPIs Rápidos
        c1, c2, c3 = st.columns(3)
        rf = (1 + rets['Cash'].mean())**12 - 1
        vol = user_ret.std() * np.sqrt(12)
        ret_aa = (1 + user_ret.mean())**12 - 1
        
        c1.metric("Retorno Anualizado", f"{ret_aa:.2%}")
        c2.metric("Volatilidade Anualizada", f"{vol:.2%}")
        c3.metric("Sharpe Ratio", f"{(ret_aa - rf)/vol:.2f}")

    with tab2:
        st.subheader("Quebra por Perfil (Visual Empilhado)")
        p_choice = st.selectbox("Selecione o perfil para ver a composição:", 
                                ["Sua Carteira", "Benchmark B2 (10/90)", "Benchmark B3 (20/80)"])
        
        map_plots = {"Sua Carteira": comp_user, "Benchmark B2 (10/90)": comp_b2, "Benchmark B3 (20/80)": comp_b3}
        
        fig_stack = px.area(map_plots[p_choice], title=f"Contribuição Histórica: {p_choice}")
        fig_stack.update_layout(yaxis_title="Peso Acumulado (Base 100)", hovermode="x unified")
        st.plotly_chart(fig_stack, use_container_width=True)
        

    with tab3:
        st.subheader("Matriz de Correlação dos Ativos")
        corr_df = rets[assets].copy()
        corr_df.columns = [c.strip() for c in corr_df.columns]
        corr_df['Sua Carteira'] = user_ret
        
        matrix = corr_df.corr()
        fig_corr = px.imshow(matrix, text_auto=".2f", color_continuous_scale='RdBu_r', zmin=-1, zmax=1)
        st.plotly_chart(fig_corr, use_container_width=True)
        

else:
    st.info("💡 Suba o arquivo e ajuste os pesos na sidebar para 100% para carregar o dashboard.")