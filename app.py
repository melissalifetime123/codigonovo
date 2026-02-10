import streamlit as st
import pandas as pd
import numpy as np
import plotly.graph_objects as go
import datetime
from dateutil.relativedelta import relativedelta

# 1. CONFIGURAÇÃO DA PÁGINA
st.set_page_config(page_title="Offshore Portfolio Analytics", layout="wide")

# Estilo CSS para deixar o visual mais "limpo" e profissional
st.markdown("""
    <style>
    [data-testid="stDataFrame"] { width: 100%; }
    h1, h2, h3 { color: #1C2C54; font-family: 'Segoe UI', sans-serif; }
    .stTabs [data-baseweb="tab-list"] { gap: 24px; }
    .stTabs [data-baseweb="tab"] { height: 50px; background-color: #f0f2f6; border-radius: 4px; padding: 10px; }
    .stTabs [aria-selected="true"] { background-color: #1C2C54 !important; color: white !important; }
    </style>
    """, unsafe_allow_html=True)

# 2. FUNÇÃO PARA CARREGAR DADOS
@st.cache_data
def load_offshore_data(file):
    try:
        # Lê o Excel (suporta .xlsx e .xls)
        df = pd.read_excel(file)
        # Limpa nomes de colunas (remove quebras de linha e espaços)
        df.columns = [str(c).replace('\n', ' ').replace('"', '').strip() for c in df.columns]
        # Converte a coluna Date
        df['Date'] = pd.to_datetime(df['Date'], errors='coerce')
        df = df.dropna(subset=['Date']).sort_values('Date').set_index('Date')
        # Garante que os dados são numéricos e preenche buracos (ffill)
        return df.apply(pd.to_numeric, errors='coerce').ffill()
    except Exception as e:
        st.error(f"Erro ao ler o ficheiro: {e}")
        return None

# --- SIDEBAR (BARRA LATERAL) ---
with st.sidebar:
    st.title("📂 Configurações")
    uploaded_file = st.file_uploader("Upload do ficheiro 'database.xlsx'", type=["xlsx", "xls"])
    
    st.divider()
    
    start_date = None
    end_date = None

    if uploaded_file:
        st.subheader("🗓️ Timeframe")
        
        # Carregamos os dados para saber as datas disponíveis
        df_temp = load_offshore_data(uploaded_file)
        
        if df_temp is not None:
            min_db = df_temp.index.min().to_pydatetime()
            max_db = df_temp.index.max().to_pydatetime()
            
            # Opções de Seleção de Tempo
            timeframe_opção = st.radio(
                "Escolha o período:",
                ["Máximo", "YTD (Este Ano)", "12 Meses", "24 Meses", "Personalizado"],
                index=2 # Começa marcado em 12 Meses
            )

            # Lógica das datas baseada na escolha
            if timeframe_opção == "Máximo":
                start_date, end_date = min_db, max_db
            elif timeframe_opção == "YTD (Este Ano)":
                start_date = datetime.datetime(max_db.year, 1, 1)
                end_date = max_db
            elif timeframe_opção == "12 Meses":
                start_date = max_db - relativedelta(months=12)
                end_date = max_db
            elif timeframe_opção == "24 Meses":
                start_date = max_db - relativedelta(months=24)
                end_date = max_db
            elif timeframe_opção == "Personalizado":
                # Mostra o calendário se escolher Personalizado
                periodo = st.date_input(
                    "Selecione o intervalo:",
                    value=(min_db, max_db),
                    min_value=min_db,
                    max_value=max_db
                )
                if isinstance(periodo, tuple) and len(periodo) == 2:
                    start_date, end_date = periodo

            # Ajuste de segurança (não sair do limite do Excel)
            if start_date and start_date < min_db: start_date = min_db
            
            if start_date and end_date:
                st.info(f"📍 **Período:** {start_date.strftime('%d/%m/%Y')} até {end_date.strftime('%d/%m/%Y')}")

# --- ÁREA PRINCIPAL ---
if uploaded_file and start_date and end_date:
    df_raw = load_offshore_data(uploaded_file)
    
    if df_raw is not None:
        # Filtrar o DataFrame pelo Timeframe escolhido
        mask = (df_raw.index >= pd.Timestamp(start_date)) & (df_raw.index <= pd.Timestamp(end_date))
        df_filtered = df_raw.loc[mask]

        if df_filtered.empty:
            st.warning("Sem dados para este período!")
        else:
            st.title("📊 Análise de Portfólio Offshore")
            
            # 3. MATRIZ DE ALOCAÇÃO (Editável)
            st.subheader("⚖️ Alocação por Perfil")
            perfis_df = pd.DataFrame({
                "Classe": ['Cash', 'High Yield', 'Investment Grade', 'Treasury 10y', 'Equity', 'Alternatives'],
                "Ultra Conservador": [90, 0, 10, 0, 0, 0],
                "Conservador": [60, 0, 30, 10, 0, 0],
                "Moderado": [20, 10, 30, 10, 20, 10],
                "Arrojado": [5, 15, 15, 5, 45, 15],
                "Agressivo": [0, 15, 5, 0, 60, 20]
            })
            
            # Deixa o utilizador mudar os pesos na tabela
            edited_df = st.data_editor(perfis_df, hide_index=True, use_container_width=True)
            
            perfil_escolhido = st.select_slider("Selecione o perfil para ver os gráficos:", 
                                               options=["Ultra Conservador", "Conservador", "Moderado", "Arrojado", "Agressivo"], 
                                               value="Moderado")

            # 4. CÁLCULOS
            returns = df_filtered.pct_change().dropna()
            weights = edited_df.set_index("Classe")[perfil_escolhido] / 100
            
            # Retorno da Carteira do Utilizador
            user_portfolio_return = sum(returns[asset] * weights[asset] for asset in weights.index if asset in returns.columns)
            
            # 5. CARTÕES DE MÉTRICAS (KPIs)
            c1, c2, c3 = st.columns(3)
            with c1:
                total_ret = (1 + user_portfolio_return).prod() - 1
                st.metric("Retorno no Período", f"{total_ret:.2%}")
            with c2:
                vol = user_portfolio_return.std() * np.sqrt(12) # Anualizada (dados mensais)
                st.metric("Volatilidade (a.a.)", f"{vol:.2%}")
            with c3:
                cpi_col = 'CPI' if 'CPI' in returns.columns else None
                if cpi_col:
                    cpi_ret = (1 + returns[cpi_col]).prod() - 1
                    st.metric("Inflação (CPI)", f"{cpi_ret:.2%}")

            # 6. GRÁFICOS EM ABAS
            tab1, tab2 = st.tabs(["📈 Performance Acumulada", "🧱 Composição"])
            
            with tab1:
                # Evolução de 100 dólares
                fig = go.Figure()
                cum_ret = (1 + user_portfolio_return).cumprod() * 100
                fig.add_trace(go.Scatter(x=cum_ret.index, y=cum_ret, name=f"Carteira: {perfil_escolhido}", line=dict(width=4, color='#1C2C54')))
                
                # Adiciona Benchmarks se existirem no Excel
                for bench in ['Bloomberg Global Aggregate', 'CPI']:
                    if bench in returns.columns:
                        b_cum = (1 + returns[bench]).cumprod() * 100
                        fig.add_trace(go.Scatter(x=b_cum.index, y=b_cum, name=bench, line=dict(dash='dot')))
                
                fig.update_layout(template="simple_white", hovermode="x unified", title="Evolução Patrimonial (Base 100)")
                st.plotly_chart(fig, use_container_width=True)

            with tab2:
                # Gráfico de Área da Composição
                comp_df = pd.DataFrame(index=df_filtered.index)
                for asset, w in weights.items():
                    if w > 0 and asset in df_filtered.columns:
                        comp_df[asset] = w * (df_filtered[asset] / df_filtered[asset].iloc[0]) * 100
                
                fig_area = go.Figure()
                for col in comp_df.columns:
                    fig_area.add_trace(go.Scatter(x=comp_df.index, y=comp_df[col], name=col, stackgroup='one', mode='none'))
                
                fig_area.update_layout(template="simple_white", title="Exposição por Ativo ao longo do tempo")
                st.plotly_chart(fig_area, use_container_width=True)

else:
    st.info("💡 Por favor, faz o upload do ficheiro Excel na barra lateral para começar.")