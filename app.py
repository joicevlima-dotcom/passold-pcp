import streamlit as st
import pandas as pd
import plotly.express as px
from datetime import datetime, timedelta
import sqlite3
import os

# Configuração da página do Streamlit
st.set_page_config(page_title="Passold Sistemas de Fachadas", layout="wide")

st.markdown("""
    <style>
    .main .block-container { padding-top: 2rem; }
    h1 { color: #1E3A8A; font-weight: 700; }
    h2 { color: #2563EB; }
    .stMetric { background-color: #F3F4F6; padding: 15px; border-radius: 10px; border-left: 5px solid #2563EB; }
    div.stButton > button {
        width: 100%;
        background-color: #1E3A8A;
        color: white;
        font-weight: bold;
        font-size: 16px;
        padding: 10px;
        border-radius: 8px;
    }
    div.stButton > button:hover {
        background-color: #2563EB;
        color: white;
    }
    </style>
""", unsafe_allow_html=True)

st.title("🏗️ Passold - Sistema Inteligente Antidoidice")
st.subheader("PCP Avançado - Controle de Capacidade Operacional com Banco de Dados Real")

# Data atual de simulação do projeto (Junho de 2026)
HOJE_PROJETO = datetime(2026, 6, 3) 

# ========================================================
# 🗄️ ESTRUTURA DO BANCO DE DADOS REAL (SQLITE)
# ========================================================
if os.path.exists("/data"):
    DB_NAME = "/data/passold_pcp.db"
else:
    DB_NAME = "passold_pcp.db"

def conectar_banco():
    return sqlite3.connect(DB_NAME)

def inicializar_banco_de_dados():
    conn = conectar_banco()
    cursor = conn.cursor()
    
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS cronograma_macro (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            Obra TEXT,
            EDT TEXT UNIQUE,
            Tipo_Escopo TEXT,
            Etapa_Macro TEXT,
            Tarefa TEXT,
            M2_Total_Tarefa REAL,
            Inicio_Previsto TEXT,
            Termino_Obra TEXT,
            Status TEXT
        )
    """)
    
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS itens_detalhado (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            Obra_Vinculada TEXT,
            EDT_Vinculado TEXT,
            Cod_Lote TEXT,
            Tipo_Material TEXT,
            Qtd_Caixas INTEGER,
            M2_Item REAL,
            Data_Producao_Programada TEXT,
            Data_Limite_Obra TEXT,
            Romaneio_Chapas TEXT,
            Status_Item TEXT
        )
    """)
    
    cursor.execute("SELECT COUNT(*) FROM cronograma_macro")
    if cursor.fetchone()[0] == 0:
        dados_iniciais = [
            ("OBRA OAS", "1.1.1.1", "ACM", "TORRE - ETAPA 1 (6º ao 24º pav)", "Instalação ACM vigas Balancim 02, 03 e 04", 1780.26, "2026-01-19", "2026-06-24", "Em Andamento"),
            ("OBRA OAS", "1.1.1.2", "ACM", "TORRE - ETAPA 1 (6º ao 24º pav)", "Instalação ACM vigas Balancim 05 e 06", 1780.26, "2026-01-19", "2026-06-24", "Em Andamento"),
            ("OBRA OAS", "1.1.2.1", "Porcelanato", "TORRE - ETAPA 1 (6º ao 24º pav)", "Instalação Porcelanato Balancim 02, 03 e 04", 950.00, "2026-02-02", "2026-06-15", "Em Andamento"),
            ("OBRA OAS", "2.1.1", "ACM", "TORRE - ETAPA 2 (26º ao 37º pav)", "Instalação ACM viga embasamento esquerdo", 267.70, "2026-04-20", "2026-06-30", "Pendente"),
            ("OBRA OAS", "3.1.1.1", "ACM", "TORRE - ETAPA 3 (39º ao 48º pav.)", "Instalação ACM vigas Balancim 23; 24 e 25", 212.95, "2026-07-10", "2026-07-30", "Pendente"),
            ("OBRA OAS", "3.1.1.2", "ACM", "TORRE - ETAPA 3 (39º ao 48º pav.)", "Instalação ACM vigas Balancim 26 e 07", 141.97, "2026-07-31", "2026-08-14", "Pendente"),
            ("OBRA OAS", "4.1.1", "Vidro/Esquadria", "COBERTURA", "Instalação de Esquadrias e Vidros Lojas Terras", 540.00, "2026-08-15", "2026-09-30", "Pendente")
        ]
        cursor.executemany("""
            INSERT INTO cronograma_macro (Obra, EDT, Tipo_Escopo, Etapa_Macro, Tarefa, M2_Total_Tarefa, Inicio_Previsto, Termino_Obra, Status)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, dados_iniciais)
        
    conn.commit()
    conn.close()

inicializar_banco_de_dados()

def carregar_macro():
    conn = conectar_banco()
    df = pd.read_sql_query("SELECT * FROM cronograma_macro", conn)
    conn.close()
    df['Inicio_Previsto'] = pd.to_datetime(df['Inicio_Previsto'])
    df['Termino_Obra'] = pd.to_datetime(df['Termino_Obra'])
    return df

def carregar_micro():
    conn = conectar_banco()
    df = pd.read_sql_query("SELECT * FROM itens_detalhado", conn)
    conn.close()
    if not df.empty:
        df['Data_Producao_Programada'] = pd.to_datetime(df['Data_Producao_Programada'])
        df['Data_Limite_Obra'] = pd.to_datetime(df['Data_Limite_Obra'])
    return df

def salvar_lotes_micro(df_novos_lotes):
    conn = conectar_banco()
    df_novos_lotes.to_sql('itens_detalhado', conn, if_exists='append', index=False)
    conn.close()

def aplicar_planejamento_reverso(df):
    df_novo = df.copy()
    df_novo['Prazo_Final_Fabrica'] = pd.NaT
    df_novo['Prazo_Fase_Intermediaria'] = pd.NaT
    df_novo['Prazo_Medicao_InLoco'] = pd.NaT
    
    for idx, row in df_novo.iterrows():
        dt_fim = pd.to_datetime(row['Termino_Obra'])
        if row['Tipo_Escopo'] == "ACM":
            df_novo.at[idx, 'Prazo_Final_Fabrica'] = dt_fim - timedelta(days=10)
            df_novo.at[idx, 'Prazo_Fase_Intermediaria'] = dt_fim - timedelta(days=17)
            df_novo.at[idx, 'Prazo_Medicao_InLoco'] = dt_fim - timedelta(days=32)
        else:
            df_novo.at[idx, 'Prazo_Final_Fabrica'] = dt_fim - timedelta(days=15)
            df_novo.at[idx, 'Prazo_Fase_Intermediaria'] = dt_fim - timedelta(days=35)
            df_novo.at[idx, 'Prazo_Medicao_InLoco'] = dt_fim - timedelta(days=50)
    return df_novo

df_banco_macro = carregar_macro()
df_banco_micro = carregar_micro()

lista_obras_disponiveis = sorted(list(df_banco_macro['Obra'].unique()))
obra_selecionada = st.selectbox("Selecione a Obra Ativa para Visualizar no Painel:", lista_obras_disponiveis)

df_macro_filtrado = df_banco_macro[df_banco_macro['Obra'] == obra_selecionada]
df_macro_calculado = aplicar_planejamento_reverso(df_macro_filtrado)

if 'modo_visao_tv' not in st.session_state:
    st.session_state.modo_visao_tv = "VER_TUDO"
if 'data_filtro_tv' not in st.session_state:
    st.session_state.data_filtro_tv = HOJE_PROJETO.date()
if 'mensagem_sucesso' not in st.session_state:
    st.session_state.mensagem_sucesso = None

aba_tv, aba_geral, aba_cadastro_chapas = st.tabs(["📺 PAINEL DA TV (Chão de Fábrica)", "📊 Visão Macro (Diretoria)", "📐 Vincular Datas na Relação de Materiais"])

# ========================================================
# ABA 1: PAINEL DA TV
# ========================================================
with aba_tv:
    st.header(f"📺 Quadro de Produção de Fábrica - Passold")
    
    st.markdown("### ⚡ Escolha o período de visualização para os operadores:")
    v_col1, v_col2, v_col3 = st.columns(3)
    if v_col1.button("📋 VER TODA A PROGRAMAÇÃO ATIVA (Recomendado)"): st.session_state.modo_visao_tv = "VER_TUDO"
    if v_col2.button("🗓️ ESTA SEMANA (Simulação)"): st.session_state.modo_visao_tv = "SEMANA"
    if v_col3.button("🔍 ESCOLHER DIA ESPECÍFICO"): st.session_state.modo_visao_tv = "DIÁRIO"
        
    if st.session_state.modo_visao_tv == "DIÁRIO":
        st.session_state.data_filtro_tv = st.date_input("Selecione o Dia de Trabalho:", value=datetime(2026, 7, 8).date())

    st.markdown("---")
    
    if not df_banco_micro.empty:
        df_chapas_obra = df_banco_micro[df_banco_micro['Obra_Vinculada'] == obra_selecionada].copy()
        df_chapas_obra['Data_Producao_Programada'] = pd.to_datetime(df_chapas_obra['Data_Producao_Programada'])
        
        if st.session_state.modo_visao_tv == "DIÁRIO":
            df_tv_filtrado = df_chapas_obra[df_chapas_obra['Data_Producao_Programada'].dt.date == st.session_state.data_filtro_tv]
        elif st.session_state.modo_visao_tv == "SEMANA":
            segunda = HOJE_PROJETO.date() - timedelta(days=HOJE_PROJETO.weekday())
            domingo = segunda + timedelta(days=6)
            df_tv_filtrado = df_chapas_obra[(df_chapas_obra['Data_Producao_Programada'].dt.date >= segunda) & (df_chapas_obra['Data_Producao_Programada'].dt.date <= domingo)]
        else:
            df_tv_filtrado = df_chapas_obra.copy()

        if not df_tv_filtrado.empty:
            df_tv_filtrado = df_tv_filtrado.sort_values(by="Data_Producao_Programada", ascending=True)
            total_cx_periodo = df_tv_filtrado['Qtd_Caixas'].sum()
            
            c_meta1, c_meta2 = st.columns(2)
            c_meta1.metric("📦 VOLUME TOTAL DE CAIXAS", f"{int(total_cx_periodo)} cx")
            c_meta2.metric("📐 METRAGEM TOTAL DE PRODUÇÃO", f"{df_tv_filtrado['M2_Item'].sum():,.2f} m²")
            
            st.markdown("#### 🕒 Sequência Diária de Corte e Montagem (Divisões do Lote):")
            for idx, row in df_tv_filtrado.iterrows():
                with st.container():
                    col_l1, col_l2, col_l3 = st.columns([2, 1, 1])
                    col_l1.markdown(f"🏭 **Lote:** `{row['Cod_Lote']}` | **Material:** {row['Tipo_Material']}")
                    col_l2.markdown(f"📦 **Meta do Dia:** {int(row['Qtd_Caixas'])} cx | 📐 {row['M2_Item']} m²")
                    col_l3.markdown(f"📅 **Data de Execução:** {row['Data_Producao_Programada'].strftime('%d/%m/%Y')}")
                    if row['Romaneio_Chapas']:
                        st.caption(f"📍 Setor / Pavimentos destino: {row['Romaneio_Chapas']}")
                    st.markdown("---")
        else:
            st.success("🎉 Nenhum fracionamento agendado encontrado para o período selecionado.")
    else:
        st.info("Nenhum lote técnico importado ainda. Vá na terceira aba para injetar as datas na relação de materiais dos meninos!")

# ========================================================
# ABA 2: VISÃO MACRO (Diretoria)
# ========================================================
with aba_geral:
    st.header(f"📊 Dashboard Executivo e Cronograma Macro - {obra_selecionada}")
    
    col1, col2, col3 = st.columns(3)
    col1.metric("Metragem Total Pactuada", f"{df_macro_calculado['M2_Total_Tarefa'].sum():,.2f} m²")
    col2.metric("Frentes Ativas Rastreadas", f"{len(df_macro_calculado)} frentes")
    col3.metric("Fim Previsto da Instalação", df_macro_calculado['Termino_Obra'].max().strftime('%d/%m/%Y') if not df_macro_calculado.empty else "N/A")
    
    st.markdown("---")
    if not df_macro_calculado.empty:
        st.markdown("### 📋 Tabela de Planejamento Reverso Estratégico")
        st.dataframe(df_macro_calculado, hide_index=True, use_container_width=True)
        
        st.markdown("### 📅 Linha do Tempo Macro (Gantt)")
        fig_gantt = px.timeline(df_macro_calculado, x_start="Inicio_Previsto", x_end="Termino_Obra", y="Tarefa", color="Status")
        fig_gantt.update_yaxes(autorange="reversed")
        st.plotly_chart(fig_gantt, use_container_width=True)

# ========================================================
# ABA 3: INTELIGÊNCIA REVERSA E FRACIONAMENTO
# ========================================================
with aba_cadastro_chapas:
    st.header("📐 Inteligência Temporal: Injetar Datas e Cadência na Relação Técnica")
    
    if st.session_state.mensagem_sucesso:
        st.success(st.session_state.mensagem_sucesso)
        if st.button("Limpar Notificação / Adicionar Outro Lote"):
            st.session_state.mensagem_sucesso = None
            st.rerun()

    if not df_macro_filtrado.empty:
        opcoes_edt = [f"{row['EDT']} - {row['Tarefa']}" for idx, row in df_macro_filtrado.iterrows()]
        
        with st.form("form_injecao_datas"):
            st.markdown("### 1. Vínculo com Cronograma de Obra")
            col_in1, col_in2, col_in3 = st.columns(3)
            with col_in1:
                edt_selecionado = st.selectbox("Esta relação técnica pertence a qual frente macro?", opcoes_edt)
                edt_puro = edt_selecionado.split(" ")[0]
                cod_lote = st.text_input("Código de Identificação Interna:", value="RV02-LOTE-39_48").upper()
            with col_in2:
                data_necessidade_obra = st.date_input("🏁 Data de Despacho / Envio p/ Obra:", value=datetime(2026, 7, 10).date())
                recuo_dias_base = st.number_input("Dias de Pulmão Mínimo de Segurança antes do Despacho:", min_value=1, value=2)
            with col_in3:
                limite_caixas_dia = st.number_input("Capacidade MÁXIMA real de montagem (caixas/dia):", min_value=1, value=10)
                pulmao_embarque = st.number_input("Estoque Mínimo Pronto para o 1º Caminhão:", min_value=1, value=50)

            st.markdown("---")
            st.markdown("### 2. Dados Extraídos da Planilha Técnica Bruta")
            col_dados1, col_dados2 = st.columns(2)
            with col_dados1:
                txt_pavimentos = st.text_area("Pavimentos/Balancins afetados de acordo com o PDF:", value="Pav 39 ao 48")
                especificacao = st.text_input("Material / Chapa do Lote:", value="ACM BRANCO - OAS")
            with col_dados2:
                total_cx = st.number_input("Quantidade Total de Caixas Identificadas na Planilha:", min_value=1, value=94)
                total_m2 = st.number_input("Metragem Quadrada Total (m2) da Planilha:", min_value=0.1, value=212.95)

            btn_calcular_tudo = st.form_submit_button("⚡ Processar Fluxo Real de Fábrica e Salvar no Banco")

            if btn_calcular_tudo:
                if cod_lote and total_m2 > 0:
                    dt_limite_conv = datetime.combine(data_necessidade_obra, datetime.min.time())
                    day_start = dt_limite_conv - timedelta(days=int(recuo_dias_base))
                    
                    caixas_restantes = total_cx
                    m2_por_caixa = total_m2 / total_cx
                    
                    novos_registros = []
                    dia_corrente = day_start
                    
                    while caixas_restantes > 0:
                        if dia_corrente.weekday() in [5, 6]: # Pula Finais de Semana
                            dia_corrente -= timedelta(days=1)
                            continue
                            
                        caixas_do_dia = min(int(limite_caixas_dia), int(caixas_restantes))
                        m2_do_dia = caixas_do_dia * m2_por_caixa
                        
                        novos_registros.append({
                            "Obra_Vinculada": obra_selecionada, 
                            "EDT_Vinculado": edt_puro,
                            "Cod_Lote": cod_lote, 
                            "Tipo_Material": especificacao, # <--- Corrigido de "Callahan_especificacao" para "especificacao"
                            "Qtd_Caixas": int(caixas_do_dia), 
                            "M2_Item": float(round(m2_do_dia, 2)),
                            "Data_Producao_Programada": dia_corrente.strftime('%Y-%m-%d %H:%M:%S'), 
                            "Data_Limite_Obra": dt_limite_conv.strftime('%Y-%m-%d %H:%M:%S'), 
                            "Romaneio_Chapas": txt_pavimentos, 
                            "Status_Item": "Pendente"
                        })
                        
                        caixas_restantes -= caixas_do_dia # <--- Corrigido operador de subtração
                        dia_corrente -= timedelta(days=1) # <--- Corrigido operador de data
                    
                    df_novos = pd.DataFrame(novos_registros)
                    salvar_lotes_micro(df_novos)
                    
                    st.session_state.mensagem_sucesso = f"💾 SUCESSO! Divisão gerada e salva no banco de dados da Passold! Vá para a aba da TV conferir o cronograma diário completo."
                    st.rerun()