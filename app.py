import streamlit as st
import pandas as pd
import numpy as np
import plotly.graph_objects as go
import plotly.express as px

# =========================
# CONFIGURAÇÃO
# =========================
st.set_page_config(page_title="Asset Allocation Offshore", layout="wide")
st.title("📊 Asset Allocation | Offshore")

@st.cache_data
def load_data(file):
    # Verifica a extensão e carrega
    if file.name.endswith('.csv'):
        # Lemos primeiro os nomes das classes (linha 0)
        df_classes = pd.read_csv(file, nrows=0).columns.tolist()
        # Carregamos os dados pulando a linha do ticker (linha 1)
        df = pd.read_csv(file, skiprows=[1])
    else:
        df_classes = pd.read_excel(file, nrows=0).columns.tolist()
        df = pd.read_excel(file, skiprows=[1])

    # Renomear colunas e limpar colunas sem nome (vazias no Excel)
    df.columns = df_classes
    df = df.loc[:, ~df.columns.str.contains('^Unnamed')]
    
    # Tratamento de Data
    date_col = df.columns[0] # Assume que a primeira coluna é a data
    df[date_col] = pd.to_datetime(df[date_col])
    df = df.sort_values(date_col).set_index(date_col)
    
    # Converte tudo para numérico e remove linhas onde não há dados para TODOS os ativos
    df = df.apply(pd.to_numeric, errors='coerce')
    df = df.dropna() 
    
    return df

# =========================
# UPLOAD DO ARQUIVO
# =========================
uploaded_file = st.file_uploader("Suba sua base Offshore (CSV ou Excel)", type=["csv", "xlsx"])

if uploaded_file:
    try:
        df = load_data(uploaded_file)
        
        # --- CÁLCULO DOS BENCHMARKS HÍBRIDOS ---
        # Usamos retornos mensais para construir as séries
        rets = df.pct_change().dropna()
        
        # B1: 100% Global Agg
        df['B1: 100% Global Agg'] = df['Bloomberg Global Aggregate']
        
        # B2: 10% Equity + 90% Global Agg
        b2_rets = (0.10 * rets['Equity ']) + (0.90 * rets['Bloomberg Global Aggregate'])
        df['B2: 10/90 Hybrid'] = 100 * (1 + b2_rets).cumprod()
        
        # B3: 20% Equity + 80% Global Agg
        b3_rets = (0.20 * rets['Equity ']) + (0.80 * rets['Bloomberg Global Aggregate'])
        df['B3: 20/80 Hybrid'] = 100 * (1 + b3_rets).cumprod()
        
        # B4: CPI (Já está na base 100 no seu arquivo)
        df['B4: CPI Inflation'] = df['CPI']

        # Lista final de colunas para o usuário escolher
        all_options = df.columns.tolist()

        # --- INTERFACE ---
        st.subheader("📈 Comparação de Performance")
        selected = st.multiselect(
            "Selecione o que visualizar:", 
            all_options, 
            default=['Equity ', 'B1: 100% Global Agg', 'B2: 10/90 Hybrid']
        )

        if selected:
            # Re-normalização para o início do gráfico (garante que todos partam de 100)
            fig_df = (df[selected] / df[selected].iloc[0]) * 100
            
            fig = go.Figure()
            for col in selected:
                fig.add_trace(go.Scatter(x=fig_df.index, y=fig_df[col], name=col))
            
            fig.update_layout(template="plotly_white", hovermode="x unified", yaxis_title="Base 100")
            st.plotly_chart(fig, use_container_width=True)

            # --- MÉTRICAS ---
            st.subheader("📊 Estatísticas Anualizadas")
            
            # Retornos mensais atualizados com os benchmarks
            final_rets = df[selected].pct_change().dropna()
            
            # Métricas (Assumindo dados mensais = 12 janelas)
            ann_ret = (1 + final_rets.mean())**12 - 1
            ann_vol = final_rets.std() * np.sqrt(12)
            
            # Sharpe Ratio (Usando 'Cash' como Risk-Free)
            # Se 'Cash' não estiver selecionado, buscamos do DF original
            rf_rate = (1 + df['Cash'].pct_change().mean())**12 - 1
            sharpe = (ann_ret - rf_rate) / ann_vol
            
            metrics_table = pd.DataFrame({
                "Retorno (a.a.)": ann_ret,
                "Volatilidade (a.a.)": ann_vol,
                "Sharpe Ratio": sharpe
            })
            
            st.table(metrics_table.style.format({
                "Retorno (a.a.)": "{:.2%}",
                "Volatilidade (a.a.)": "{:.2%}",
                "Sharpe Ratio": "{:.2f}"
            }))

    except Exception as e:
        st.error(f"Erro ao processar o arquivo: {e}")
        st.warning("Verifique se os nomes das colunas 'Equity ', 'Bloomberg Global Aggregate', 'CPI' e 'Cash' estão escritos exatamente assim (incluindo espaços).")

else:
    st.info("💡 Por favor, suba o arquivo 'database.xlsx' ou o CSV correspondente.")