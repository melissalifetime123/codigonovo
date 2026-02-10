import streamlit as st
import pandas as pd
import numpy as np
import plotly.graph_objects as go

# 1. CONFIGURAÇÃO DE PÁGINA
st.set_page_config(page_title="Offshore Portfolio Analytics", layout="wide")

st.markdown("""
    <style>
    [data-testid="stDataFrame"] { width: 100%; }
    h1, h2, h3 { color: #1C2C54; font-family: 'Segoe UI', sans-serif; }
    .stTabs [data-baseweb="tab-list"] { gap: 24px; }
    .stTabs [data-baseweb="tab"] { height: 50px; background-color: #f0f2f6; border-radius: 4px; padding: 10px; }
    .stTabs [aria-selected="true"] { background-color: #1C2C54 !important; color: white !important; }
    </style>
    """, unsafe_allow_html=True)

# 2. CARREGAMENTO E LIMPEZA
@st.cache_data
def load_offshore_data(file):
    try:
        df = pd.read_excel(file)
        df.columns = [str(c).replace('\n', ' ').replace('"', '').strip() for c in df.columns]
        df['Date'] = pd.to_datetime(df['Date'], errors='coerce')
        df = df.dropna(subset=['Date']).sort_values('Date').set_index('Date')
        return df.apply(pd.to_numeric, errors='coerce').ffill()
    except Exception as e:
        st.error(f"Erro ao ler Excel: {e}")
        return None

# --- SIDEBAR: UPLOAD E FILTRO DE DATA ---
with st.sidebar:
    st.title("📂 Configurações")
    uploaded_file = st.file_uploader("Upload 'database.xlsx'", type=["xlsx", "xls"])
    
    st.divider()
    st.subheader("🗓️ Período de Análise")
    
    # Inicializamos variáveis de data
    start_date = None
    end_date = None

    if uploaded_file:
        # Carregamento temporário apenas para pegar as datas limites
        temp_df = load_offshore_data(uploaded_file)
        if temp_df is not None:
            min_date = temp_df.index.min().to_pydatetime()
            max_date = temp_df.index.max().to_pydatetime()
            
            # Seletor de intervalo de datas
            periodo = st.date_input(
                "Selecione o intervalo:",
                value=(min_date, max_date),
                min_value=min_date,
                max_value=max_date
            )
            
            # Ajuste para garantir que temos as duas datas (início e fim)
            if isinstance(periodo, tuple) and len(periodo) == 2:
                start_date, end_date = periodo
            else:
                st.warning("Selecione a data de início e fim.")

# --- ÁREA PRINCIPAL ---
if uploaded_file and start_date and end_date:
    df_raw = load_offshore_data(uploaded_file)
    
    if df_raw is not None:
        # FILTRAGEM POR DATA
        # Transformamos start/end para datetime64 para bater com o index
        mask = (df_raw.index >= pd.Timestamp(start_date)) & (df_raw.index <= pd.Timestamp(end_date))
        df_filtered = df_raw.loc[mask]

        if df_filtered.empty:
            st.error("O período selecionado não possui dados.")
        else:
            st.title("📊 Offshore Performance Analytics")
            
            # 3. MATRIZ DE 5 PERFIS
            st.subheader("⚖️ Matriz de Alocação por Perfil")
            df_perfis = pd.DataFrame({
                "Classe": ['Cash', 'High Yield', 'Investment Grade', 'Treasury 10y', 'Equity', 'Alternatives'],
                "Ultra Conservador": [90, 0, 10, 0, 0, 0],
                "Conservador": [60, 0, 30, 10, 0, 0],
                "Moderado": [20, 10, 30, 10, 20, 10],
                "Arrojado": [5, 15, 15, 5, 45, 15],
                "Agressivo": [0, 15, 5, 0, 60, 20]
            })
            
            edited_df = st.data_editor(df_perfis, hide_index=True, use_container_width=True)
            perfis_lista = ["Ultra Conservador", "Conservador", "Moderado", "Arrojado", "Agressivo"]
            perfil_ativo = st.select_slider("Selecione o perfil:", options=perfis_lista, value="Moderado")

            # 4. CÁLCULOS (Baseados no Filtro)
            # Retornos sobre o DF filtrado
            rets = df_filtered.pct_change().dropna()
            weights = edited_df.set_index("Classe")[perfil_ativo] / 100
            
            # Benchmarks
            b1_agg = rets['Bloomberg Global Aggregate']
            b2_10_90 = (0.10 * rets['Equity']) + (0.90 * rets['Bloomberg Global Aggregate'])
            b3_20_80 = (0.20 * rets['Equity']) + (0.80 * rets['Bloomberg Global Aggregate'])
            b4_cpi = rets['CPI']
            user_ret = sum(rets[asset] * weights[asset] for asset in weights.index if asset in rets.columns)

            # 5. KPIS
            c1, c2, c3, c4 = st.columns(4)
            with c1:
                st.metric(f"Retorno {perfil_ativo}", f"{((1 + user_ret).prod() - 1):.2%}")
            with c2:
                st.metric("Volatilidade (aa)", f"{(user_ret.std() * np.sqrt(12)):.2%}")
            with c3:
                st.metric("Benchmark: 20/80", f"{((1 + b3_20_80).prod()-1):.2%}")
            with c4:
                st.metric("CPI (Janela)", f"{((1 + b4_cpi).prod()-1):.2%}")

            # 6. GRÁFICOS
            st.divider()
            tab_perf, tab_comp = st.tabs(["📈 Performance no Período", "🧱 Evolução Patrimonial"])
            
            with tab_perf:
                # Normalização Base 100 no início da janela filtrada
                perf_df = pd.DataFrame(index=rets.index)
                perf_df['100% BBG Global Agg'] = (1 + b1_agg).cumprod() * 100
                perf_df['10/90 (Equity/Agg)'] = (1 + b2_10_90).cumprod() * 100
                perf_df['20/80 (Equity/Agg)'] = (1 + b3_20_80).cumprod() * 100
                perf_df['CPI (Inflação)'] = (1 + b4_cpi).cumprod() * 100
                perf_df[f'Perfil: {perfil_ativo}'] = (1 + user_ret).cumprod() * 100

                fig = go.Figure()
                cores = {f'Perfil: {perfil_ativo}': '#1C2C54', 'CPI (Inflação)': '#ef4444'}
                
                for col in perf_df.columns:
                    is_p = 'Perfil' in col
                    fig.add_trace(go.Scatter(
                        x=perf_df.index, y=perf_df[col], name=col,
                        line=dict(width=4 if is_p else 2, dash='dash' if 'CPI' in col else 'solid', color=cores.get(col))
                    ))
                fig.update_layout(template="simple_white", hovermode="x unified", height=500)
                st.plotly_chart(fig, use_container_width=True)
                

            with tab_comp:
                # Mostra como os ativos se comportariam saindo de 100 no início da janela
                comp_df = pd.DataFrame(index=df_filtered.index)
                for asset, w in weights.items():
                    if w > 0:
                        comp_df[asset] = w * (df_filtered[asset] / df_filtered[asset].iloc[0]) * 100
                
                fig_area = go.Figure()
                for col in comp_df.columns:
                    fig_area.add_trace(go.Scatter(x=comp_df.index, y=comp_df[col], name=col, stackgroup='one'))
                fig_area.update_layout(template="simple_white", height=500)
                st.plotly_chart(fig_area, use_container_width=True)

else:
    st.info("👋 **Aguardando dados.** Carregue o arquivo Excel e defina o período na barra lateral.")