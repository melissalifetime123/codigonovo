from dateutil.relativedelta import relativedelta # Importante adicionar isso no topo se for usar lógica de datas complexa
import datetime

# ... (Mantenha o código anterior até a parte da SIDEBAR) ...

# --- SIDEBAR: UPLOAD E FILTRO DE DATA ---
with st.sidebar:
    st.title("📂 Configurações")
    uploaded_file = st.file_uploader("Upload 'database.xlsx'", type=["xlsx", "xls"])
    
    st.divider()
    
    # Inicializamos variáveis de data com valores padrão (caso nada seja carregado)
    start_date = None
    end_date = None

    if uploaded_file:
        st.subheader("🗓️ Período de Análise")
        
        # Carregamento temporário para pegar limites
        temp_df = load_offshore_data(uploaded_file)
        
        if temp_df is not None:
            min_date = temp_df.index.min().to_pydatetime()
            max_date = temp_df.index.max().to_pydatetime()
            
            # Opções de Filtro Rápido
            filtro_tempo = st.radio(
                "Selecione o Período:",
                ["YTD (Ano Atual)", "12 Meses", "36 Meses", "Máximo", "Personalizado"],
                index=1 # Padrão: 12 Meses
            )
            
            # Lógica dos Botões
            if filtro_tempo == "Máximo":
                start_date = min_date
                end_date = max_date
                
            elif filtro_tempo == "YTD (Ano Atual)":
                end_date = max_date
                start_date = datetime.datetime(max_date.year, 1, 1)
                # Se o início do ano for antes do dado mais antigo, ajusta
                if start_date < min_date: start_date = min_date

            elif filtro_tempo == "12 Meses":
                end_date = max_date
                start_date = max_date - relativedelta(months=12)
                if start_date < min_date: start_date = min_date

            elif filtro_tempo == "36 Meses":
                end_date = max_date
                start_date = max_date - relativedelta(months=36)
                if start_date < min_date: start_date = min_date

            elif filtro_tempo == "Personalizado":
                periodo = st.date_input(
                    "Defina o intervalo:",
                    value=(min_date, max_date),
                    min_value=min_date,
                    max_value=max_date
                )
                if isinstance(periodo, tuple) and len(periodo) == 2:
                    start_date, end_date = periodo
            
            # Mostra o resumo das datas selecionadas
            if start_date and end_date:
                st.info(f"De: {start_date.strftime('%d/%m/%Y')}\n\nAté: {end_date.strftime('%d/%m/%Y')}")

# ... (Continue com a ÁREA PRINCIPAL) ...