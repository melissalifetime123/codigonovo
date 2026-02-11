import streamlit as st
import pandas as pd
import numpy as np
import plotly.graph_objects as go

# ================= CONFIGURAÇÃO DE INTERFACE =================
st.set_page_config(page_title="Portfolio Analytics | Offshore", layout="wide")

st.markdown("""
    <style>
    [data-testid="stDataFrame"] { width: 100%; }
    .validator-text {
        font-weight: bold; font-size: 14px; margin-top: 5px;
    }
    </style>
    """, unsafe_allow_html=True)

# Cores Padrão
CORES_LIFETIME = ['#D1D5DB', '#9CA3AF', '#6B7280', '#4B5563', '#1C2C54']
CORES_BENCH = {
    "CPI": "#64748B", 
    "Bloomberg Global Aggregate": "#334155", 
    "10% MSCI + 90% BBG Global Agg": "#1E293B", 
    "20% MSCI + 80% BBG Global Agg": "#020617"
}

st.title("🌍 Asset Allocation | Offshore")

st.sidebar.header("Configurações")
arquivo = st.sidebar.file_uploader("Upload da Base Excel", type=['xlsx'])

if arquivo:
    try:
        # --- 1. LEITURA (Aba específica enviada) ---
        # Lendo a aba 'comdinheiro' que contém todos os dados consolidados
        df_raw = pd.read_excel(arquivo, sheet_name='comdinheiro', index_col=0, parse_dates=True)
        df_raw = df_raw.apply(pd.to_numeric, errors='coerce').ffill().dropna(how='all')
        
        start, end = st.sidebar.slider("Janela de Análise:", 
                                       df_raw.index.min().to_pydatetime(), 
                                       df_raw.index.max().to_pydatetime(), 
                                       (df_raw.index.min().to_pydatetime(), df_raw.index.max().to_pydatetime()))
        df_f = df_raw.loc[start:end].copy()

        # Cálculo de retornos mensais
        df_ret = df_f.pct_change().dropna()
        
        # --- 2. MAPEAMENTO DE COLUNAS CONFORME PLANILHA ---
        lista_benchmarks = [
            "CPI", 
            "Bloomberg Global Aggregate", 
            "10% MSCI + 90% BBG Global Agg", 
            "20% MSCI + 80% BBG Global Agg"
        ]
        
        bench_presentes = [c for c in lista_benchmarks if c in df_ret.columns]
        bench_ret = df_ret[bench_presentes]
        
        # Classes de ativos (o que não é benchmark)
        ret_classes = df_ret.drop(columns=bench_presentes)

        # --- 3. INPUT DE PESOS E VALIDADOR DE SOMA ---
        st.subheader("🏗️ Definição de Pesos por Perfil")
        perfis = ["Ultra Conservador", "Conservador", "Moderado", "Arrojado", "Agressivo"]
        
        df_pesos_ui = pd.DataFrame({"Classe": ret_classes.columns})
        for p in perfis:
            df_pesos_ui[p] = 0.0
            
        edited = st.data_editor(df_pesos_ui, hide_index=True, use_container_width=True)

        cols_val = st.columns(len(perfis))
        for i, p in enumerate(perfis):
            soma = edited[p].sum()
            cor = "#28A745" if round(soma, 2) == 100.0 else "#DC3545"
            cols_val[i].markdown(f"<div class='validator-text' style='color:{cor}'>Soma {p}: {soma:.1f}%</div>", unsafe_allow_html=True)
        
        if any(round(edited[p].sum(), 2) != 100.0 for p in perfis):
            st.warning("⚠️ Ajuste os pesos para totalizar 100% em cada perfil.")

        # --- 4. CÁLCULOS DE MÉTRICAS ---
        metrics, perf_acum, drawdowns = {}, pd.DataFrame(index=ret_classes.index), pd.DataFrame(index=ret_classes.index)
        freq = 12 

        for p in perfis:
            w = np.array(edited[p]) / 100
            ret_p = ret_classes.dot(w)
            
            # Rentabilidade Acumulada
            acum = (1 + ret_p).cumprod()
            perf_acum[p] = acum - 1
            
            # Max Drawdown
            picos = acum.expanding().max()
            dd = (acum / picos) - 1
            drawdowns[p] = dd
            
            # Estatísticas Anualizadas
            # Nota: Usando média aritmética simples anualizada para retorno conforme padrão offshore
            r_anual = (1 + ret_p.mean())**freq - 1
            vol_anual = ret_p.std() * np.sqrt(freq)
            
            metrics[p] = {
                "Retorno Anualizado": r_anual,
                "Volatilidade": vol_anual,
                "Max Drawdown": dd.min()
            }

        # --- 5. EXIBIÇÃO DE RESULTADOS ---
        st.markdown("---")
        st.write("📊 **Estatísticas Comparativas**")
        st.dataframe(pd.DataFrame(metrics).style.format("{:.2%}"), use_container_width=True)

        # Gráfico Performance
        st.subheader("📈 Performance vs Benchmarks Híbridos")
        fig_perf = go.Figure()
        
        # Benchmarks da Planilha
        for b in bench_ret.columns:
            curva_b = (1 + bench_ret[b]).cumprod() - 1
            fig_perf.add_trace(go.Scatter(x=curva_b.index, y=curva_b, name=b, 
                                          line=dict(color=CORES_BENCH.get(b, "#888"), dash='dot')))
        
        # Perfis Calculados
        for i, p in enumerate(perfis):
            fig_perf.add_trace(go.Scatter(x=perf_acum.index, y=perf_acum[p], name=p, 
                                          line=dict(color=CORES_LIFETIME[i], width=3)))
            
        fig_perf.update_layout(template="simple_white", yaxis_tickformat='.1%', hovermode="x unified")
        st.plotly_chart(fig_perf, use_container_width=True)

        # Gráfico Drawdown
        st.subheader("📉 Drawdown (Janela de Stress)")
        fig_dd = go.Figure()
        for i, p in enumerate(perfis):
            fig_dd.add_trace(go.Scatter(x=drawdowns.index, y=drawdowns[p], name=p, 
                                          fill='tozeroy', line=dict(color=CORES_LIFETIME[i], width=1)))
        fig_dd.update_layout(template="simple_white", yaxis_tickformat='.1%')
        st.plotly_chart(fig_dd, use_container_width=True)

        # Matriz de Correlação
        st.subheader("🎯 Matriz de Correlação entre Ativos")
        corr_matrix = ret_classes.corr()
        st.dataframe(corr_matrix.style.format("{:.2f}").background_gradient(cmap='RdYlGn_r', axis=None), use_container_width=True)

    except Exception as e:
        st.error(f"Erro ao processar: {e}. Certifique-se de que a aba se chama 'comdinheiro'.")