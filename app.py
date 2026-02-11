import streamlit as st
import pandas as pd
import numpy as np
import plotly.graph_objects as go
import plotly.express as px

# ================= CONFIGURAÇÃO DE INTERFACE =================
st.set_page_config(page_title="Portfolio Analytics | Offshore", layout="wide")

st.markdown("""
    <style>
    [data-testid="stDataFrame"] { width: 100%; }
    .validator-text { font-weight: bold; font-size: 14px; margin-top: 5px; }
    .stTabs [data-baseweb="tab-list"] { gap: 24px; }
    .stTabs [data-baseweb="tab"] { height: 50px; font-weight: bold; }
    </style>
    """, unsafe_allow_html=True)

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
        # --- 1. LEITURA (Aba 'comdinheiro') ---
        df_raw = pd.read_excel(arquivo, sheet_name='comdinheiro', index_col=0, parse_dates=True)
        df_raw = df_raw.apply(pd.to_numeric, errors='coerce').ffill().dropna(how='all')
        
        start, end = st.sidebar.slider("Janela de Análise:", 
                                       df_raw.index.min().to_pydatetime(), 
                                       df_raw.index.max().to_pydatetime(), 
                                       (df_raw.index.min().to_pydatetime(), df_raw.index.max().to_pydatetime()))
        df_f = df_raw.loc[start:end].copy()
        df_ret = df_f.pct_change().dropna()
        
        # --- 2. MAPEAMENTO DE COLUNAS ---
        lista_benchmarks = ["CPI", "Bloomberg Global Aggregate", "10% MSCI + 90% BBG Global Agg", "20% MSCI + 80% BBG Global Agg"]
        bench_presentes = [c for c in lista_benchmarks if c in df_ret.columns]
        bench_ret = df_ret[bench_presentes]
        ret_classes = df_ret.drop(columns=bench_presentes)

        # --- 3. INPUT DE PESOS ---
        st.subheader("🏗️ Definição de Pesos por Perfil")
        perfis = ["Ultra Conservador", "Conservador", "Moderado", "Arrojado", "Agressivo"]
        df_pesos_ui = pd.DataFrame({"Classe": ret_classes.columns})
        for p in perfis: df_pesos_ui[p] = 0.0
        
        edited = st.data_editor(df_pesos_ui, hide_index=True, use_container_width=True)

        cols_val = st.columns(len(perfis))
        for i, p in enumerate(perfis):
            soma = edited[p].sum()
            cor = "#28A745" if round(soma, 2) == 100.0 else "#DC3545"
            cols_val[i].markdown(f"<div class='validator-text' style='color:{cor}'>Soma {p}: {soma:.1f}%</div>", unsafe_allow_html=True)

        # --- 4. CÁLCULOS DE PERFORMANCE ---
        metrics, perf_acum, drawdowns = {}, pd.DataFrame(index=ret_classes.index), pd.DataFrame(index=ret_classes.index)
        freq = 12 
        
        for p in perfis:
            w = np.array(edited[p]) / 100
            ret_p = ret_classes.dot(w)
            
            # Acumulado e Drawdown
            acum = (1 + ret_p).cumprod()
            perf_acum[p] = acum - 1
            picos = acum.expanding().max()
            drawdowns[p] = (acum / picos) - 1
            
            # Métricas
            metrics[p] = {
                "Retorno Anualizado": (1 + ret_p.mean())**freq - 1,
                "Volatilidade": ret_p.std() * np.sqrt(freq),
                "Max Drawdown": drawdowns[p].min()
            }

        # --- 5. ADIÇÃO DE ABAS PARA O EXERCÍCIO TEÓRICO ---
        tab_main, tab_frontier, tab_stress, tab_real = st.tabs([
            "📊 Dashboard Principal", 
            "🎯 Fronteira Eficiente", 
            "🧪 Stress Test", 
            "📉 Retorno Real (Fisher)"
        ])

        with tab_main:
            st.write("### Estatísticas Comparativas")
            st.dataframe(pd.DataFrame(metrics).style.format("{:.2%}"), use_container_width=True)

            st.subheader("📈 Performance vs Benchmarks")
            fig_perf = go.Figure()
            for b in bench_ret.columns:
                fig_perf.add_trace(go.Scatter(x=perf_acum.index, y=(1 + bench_ret[b]).cumprod() - 1, name=b, line=dict(color=CORES_BENCH.get(b), dash='dot')))
            for i, p in enumerate(perfis):
                fig_perf.add_trace(go.Scatter(x=perf_acum.index, y=perf_acum[p], name=p, line=dict(color=CORES_LIFETIME[i], width=3)))
            st.plotly_chart(fig_perf, use_container_width=True)

            st.subheader("📉 Histórico de Drawdown")
            fig_dd = go.Figure()
            for i, p in enumerate(perfis):
                fig_dd.add_trace(go.Scatter(x=drawdowns.index, y=drawdowns[p], name=p, fill='tozeroy', line=dict(color=CORES_LIFETIME[i], width=1)))
            st.plotly_chart(fig_dd, use_container_width=True)

        with tab_frontier:
            st.subheader("🎯 Otimização Teórica: Risco x Retorno")
            
            df_metrics = pd.DataFrame(metrics).T
            fig_ef = px.scatter(df_metrics, x="Volatilidade", y="Retorno Anualizado", text=df_metrics.index, 
                                color=df_metrics.index, color_discrete_sequence=CORES_LIFETIME)
            fig_ef.update_traces(marker=dict(size=18), textposition='top center')
            fig_ef.update_layout(xaxis_tickformat='.1%', yaxis_tickformat='.1%', template="simple_white")
            st.plotly_chart(fig_ef, use_container_width=True)
            
            st.subheader("🎯 Matriz de Correlação dos Ativos")
            corr_matrix = ret_classes.corr()
            st.dataframe(corr_matrix.style.format("{:.2f}").background_gradient(cmap='RdYlGn_r', axis=None), use_container_width=True)

        with tab_stress:
            st.subheader("🧪 Simulação de Eventos de Cauda (Black Swan)")
            st.info("Ajuste os valores abaixo para simular uma queda hipotética e ver o impacto imediato nos perfis.")
            
            col_choque = st.columns(len(ret_classes.columns))
            choques = {}
            for i, classe in enumerate(ret_classes.columns):
                choques[classe] = col_choque[i].number_input(f"Choque {classe} (%)", value=0.0, step=5.0) / 100
            
            stress_res = {}
            for p in perfis:
                w = np.array(edited[p]) / 100
                stress_res[p] = np.sum(w * list(choques.values()))
            
            st.write("#### Resultado do Choque no Patrimônio")
            st.dataframe(pd.DataFrame([stress_res], index=["Variação Estimada"]).style.format("{:.2%}"), use_container_width=True)

        with tab_real:
            st.subheader("📉 Retorno Real (Descontando a Inflação)")
            if "CPI" in df_ret.columns:
                cpi_anual = (1 + df_ret["CPI"].mean())**12 - 1
                real_table = {}
                for p in perfis:
                    nom = metrics[p]["Retorno Anualizado"]
                    real_table[p] = {
                        "Retorno Nominal": nom,
                        "Inflação (CPI)": cpi_anual,
                        "Ganho Real (Fisher)": ((1 + nom) / (1 + cpi_anual)) - 1
                    }
                st.dataframe(pd.DataFrame(real_table).style.format("{:.2%}"), use_container_width=True)
                st.markdown("> **Equação de Fisher:** $(1 + i) = (1 + r)(1 + \pi)$, onde $i$ é o retorno nominal, $r$ o real e $\pi$ a inflação.")
            else:
                st.warning("Coluna 'CPI' não detectada para este cálculo.")

    except Exception as e:
        st.error(f"Erro no processamento: {e}")