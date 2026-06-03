import streamlit as st
import pandas as pd
import plotly.express as px
from datetime import datetime, timedelta
import sqlite3
import os
import time

# Configuracao da pagina do Streamlit
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

st.title("Passold - Sistema de Planejamento e Controle de Producao")
st.subheader("Gestao de OPs Semanais e Capacidade Operacional")

# Data atual de simulacao do projeto (Junho de 2026)
HOJE_PROJETO = datetime(2026, 6, 3) 

# ========================================================
# ESTRUTURA DO BANCO DE DADOS REAL (SQLITE)
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
            Num_OP TEXT,
            Tipo_Material TEXT,
            Qtd_Caixas INTEGER,
            M2_Item REAL,
            Data_Producao_Programada TEXT,
            Data_Limite_Obra TEXT,
            Romaneio_Chapas TEXT,
            Status_Item TEXT,
            Dificuldade INTEGER
        )
    """)
    
    # Atualizacoes de colunas para bancos ja criados
    try:
        cursor.execute("ALTER TABLE itens_detalhado ADD COLUMN Num_OP TEXT")
    except sqlite3.OperationalError:
        pass

    try:
        cursor.execute("ALTER TABLE itens_detalhado ADD COLUMN Dificuldade INTEGER")
    except sqlite3.OperationalError:
        pass
        
    conn.commit()
    conn.close()

inicializar_banco_de_dados()

def carregar_macro():
    conn = conectar_banco()
    df = pd.read_sql_query("SELECT * FROM cronograma_macro", conn)
    conn.close()
    if not df.empty:
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

# Controle de fluxo caso o sistema esteja completamente zerado
if not df_banco_macro.empty:
    lista_obras_disponiveis = sorted(list(df_banco_macro['Obra'].unique()))
    obra_selecionada = st.selectbox("Selecione a Obra Ativa para Visualizar no Painel:", lista_obras_disponiveis)
    df_macro_filtrado = df_banco_macro[df_banco_macro['Obra'] == obra_selecionada]
    df_macro_calculado = aplicar_planejamento_reverso(df_macro_filtrado)
else:
    st.info("Nenhuma obra cadastrada no sistema. Vá até a última aba 'Cadastrar Nova Obra' para começar a alimentar o PCP.")
    obra_selecionada = None
    df_macro_filtrado = pd.DataFrame()
    df_macro_calculado = pd.DataFrame()

if 'modo_visao_tv' not in st.session_state:
    st.session_state.modo_visao_tv = "SEMANA"

aba_tv, aba_geracao_op, aba_geral, aba_cadastro_chapas, aba_nova_obra = st.tabs([
    "PAINEL DA TV (Chao de Fabrica)", 
    "Liberar OPs da Semana",
    "Visao Macro (Diretoria)", 
    "Vincular Datas na Relacao de Materiais",
    "Cadastrar Nova Obra"
])

# ========================================================
# ABA 1: PAINEL DA TV
# ========================================================
with aba_tv:
    st.header("Quadro de Producao de Fabrica - Passold")
    
    st.markdown("### Filtro de visualizacao para os operadores:")
    v_col1, v_col2 = st.columns(2)
    if v_col1.button("VER OP'S LIBERADAS DA SEMANA ATUAL"): st.session_state.modo_visao_tv = "SEMANA"
    if v_col2.button("VER TODA A PROGRAMACAO COMPLETA"): st.session_state.modo_visao_tv = "VER_TUDO"
        
    st.markdown("---")
    
    if obra_selecionada and not df_banco_micro.empty:
        df_chapas_obra = df_banco_micro[df_banco_micro['Obra_Vinculada'] == obra_selecionada].copy()
        if not df_chapas_obra.empty:
            df_chapas_obra['Data_Producao_Programada'] = pd.to_datetime(df_chapas_obra['Data_Producao_Programada'])
            
            if st.session_state.modo_visao_tv == "SEMANA":
                df_tv_filtrado = df_chapas_obra[df_chapas_obra['Status_Item'] == "Liberado para Fabrica"]
            else:
                df_tv_filtrado = df_chapas_obra.copy()

            if not df_tv_filtrado.empty:
                df_tv_filtrado = df_tv_filtrado.sort_values(by="Data_Producao_Programada", ascending=True)
                total_cx_periodo = df_tv_filtrado['Qtd_Caixas'].sum()
                
                c_meta1, c_meta2 = st.columns(2)
                c_meta1.metric("VOLUME TOTAL DE CAIXAS EM EXECUCAO", f"{int(total_cx_periodo)} cx")
                c_meta2.metric("METRAGEM TOTAL EM PRODUCAO", f"{df_tv_filtrado['M2_Item'].sum():,.2f} m2")
                
                st.markdown("#### Sequencia Semanal de Corte e Montagem:")
                for idx, row in df_tv_filtrado.iterrows():
                    with st.container():
                        col_l1, col_l2, col_l3 = st.columns([2, 1, 1])
                        op_txt = row['Num_OP'] if row['Num_OP'] else "Sem OP"
                        dif_txt = f"Nivel {row['Dificuldade']}" if 'Dificuldade' in row and row['Dificuldade'] else "Nao informada"
                        col_l1.markdown(f"**OP:** `{op_txt}` | **Lote:** {row['Cod_Lote']} | **Material:** {row['Tipo_Material']}")
                        col_l2.markdown(f"**Meta:** {int(row['Qtd_Caixas'])} cx | {row['M2_Item']} m2")
                        col_l3.markdown(f"**Dificuldade:** {dif_txt} | **Status:** {row['Status_Item']}")
                        if row['Romaneio_Chapas']:
                            st.caption(f"Pavimentos destino: {row['Romaneio_Chapas']} | Previsao de Producao: {row['Data_Producao_Programada'].strftime('%d/%m/%Y')}")
                        st.markdown("---")
            else:
                st.info("Nenhuma Ordem de Producao (OP) liberada para esta semana ate o momento.")
        else:
            st.info("Nenhum lote associado a esta obra especifica.")
    else:
        st.info("Nenhum lote tecnico importado ainda. Va na aba de Vinculo de Datas para cadastrar.")

# ========================================================
# ABA 2: LIBERAR OP'S DA SEMANA
# ========================================================
with aba_geracao_op:
    st.header("Gerenciador de Ordens de Producao Semanais")
    st.markdown("Selecione os lotes fatiados abaixo para liberar o corte e montagem na fabrica para a proxima semana.")
    
    if obra_selecionada and not df_banco_micro.empty:
        df_pendentes = df_banco_micro[(df_banco_micro['Obra_Vinculada'] == obra_selecionada) & (df_banco_micro['Status_Item'] == "Pendente")].copy()
        
        if not df_pendentes.empty:
            df_pendentes['Data_Producao_Programada'] = pd.to_datetime(df_pendentes['Data_Producao_Programada'])
            df_pendentes['Selecionar'] = False
            
            colunas_exibir = ['id', 'Cod_Lote', 'Tipo_Material', 'Qtd_Caixas', 'M2_Item', 'Dificuldade', 'Data_Producao_Programada', 'Romaneio_Chapas', 'Selecionar']
            colunas_existentes = [c for c in colunas_exibir if c in df_pendentes.columns]
            
            df_edicao = st.data_editor(
                df_pendentes[colunas_existentes],
                hide_index=True,
                use_container_width=True,
                disabled=[c for c in colunas_existentes if c != 'Selecionar']
            )
            
            ids_selecionados = df_edicao[df_edicao['Selecionar'] == True]['id'].tolist()
            
            col_op1, col_op2 = st.columns([1, 3])
            with col_op1:
                prefixo_op = st.text_input("Prefixo da OP Semanal:", value=f"OP-{datetime.now().strftime('%Y')}-")
            
            if st.button("Liberar Itens Selecionados para a TV da Fabrica"):
                if ids_selecionados:
                    conn = conectar_banco()
                    cursor = conn.cursor()
                    
                    for index, item_id in enumerate(ids_selecionados):
                        num_op_gerada = f"{prefixo_op}{str(item_id).zfill(3)}"
                        cursor.execute("""
                            UPDATE itens_detalhado 
                            SET Status_Item = 'Liberado para Fabrica', Num_OP = ? 
                            WHERE id = ?
                        """, (num_op_gerada, item_id))
                        
                    conn.commit()
                    conn.close()
                    st.toast("Ordens de Producao liberadas com sucesso para a TV!", icon="✅")
                    time.sleep(0.5)
                    st.rerun()
                else:
                    st.warning("Por favor, marque a caixa Selecionar de pelo menos um dia na tabela acima.")
        else:
            st.success("Todos os lotes cadastrados ja foram transformados em OPs ou nao existem pendencias.")
    else:
        st.info("Nenhum lote cadastrado no banco de dados para gerar OPs.")

# ========================================================
# ABA 3: VISAO MACRO
# ========================================================
with aba_geral:
    st.header("Dashboard Executivo e Cronograma Macro")
    
    if obra_selecionada and not df_macro_calculado.empty:
        st.subheader(f"Obra Ativa: {obra_selecionada}")
        col1, col2, col3 = st.columns(3)
        col1.metric("Metragem Total Pactuada", f"{df_macro_calculado['M2_Total_Tarefa'].sum():,.2f} m2")
        col2.metric("Frentes Ativas Rastreadas", f"{len(df_macro_calculado)} frentes")
        col3.metric("Fim Previsto da Instalacao", df_macro_calculado['Termino_Obra'].max().strftime('%d/%m/%Y') if not df_macro_calculado.empty else "N/A")
        
        st.markdown("---")
        st.markdown("### Tabela de Planejamento Reverso Estrategico")
        st.dataframe(df_macro_calculado, hide_index=True, use_container_width=True)
        
        st.markdown("### Linha do Tempo Macro (Gantt)")
        fig_gantt = px.timeline(df_macro_calculado, x_start="Inicio_Previsto", x_end="Termino_Obra", y="Tarefa", color="Status")
        fig_gantt.update_yaxes(autorange="reversed")
        st.plotly_chart(fig_gantt, use_container_width=True)
    else:
        st.info("Aguardando inserção de dados de planejamento macro.")

# ========================================================
# ABA 4: INTELIGENCIA REVERSA E FRACIONAMENTO
# ========================================================
with aba_cadastro_chapas:
    st.header("Inteligencia Temporal: Injetar Datas e Cadencia na Relacao Tecnica")
    
    if 'lote_salvo_sucesso' in st.session_state and st.session_state.lote_salvo_sucesso:
        st.toast("Lote salvo com sucesso no banco de dados da Passold!", icon="✅")
        st.success("Sucesso! Divisao gerada e salva como Pendente. Acesse a aba 'Liberar OPs da Semana' para enviar o planejamento para a TV da fabrica.")
        st.session_state.lote_salvo_sucesso = False

    if obra_selecionada and not df_macro_filtrado.empty:
        opcoes_edt = [f"{row['EDT']} - {row['Tarefa']}" for idx, row in df_macro_filtrado.iterrows()]
        
        with st.form("form_injecao_datas"):
            st.markdown("### 1. Vinculo com Cronograma de Obra")
            col_in1, col_in2, col_in3 = st.columns(3)
            with col_in1:
                edt_selecionado = st.selectbox("Esta relacao tecnica pertence a qual frente macro?", opcoes_edt)
                edt_puro = edt_selecionado.split(" ")[0]
                cod_lote = st.text_input("Codigo de Identificacao Interna:")
            with col_in2:
                data_necessidade_obra = st.date_input("Data de Despacho / Envio p/ Obra:", value=datetime(2026, 7, 10).date())
                recuo_dias_base = st.number_input("Dias de Pulmao Minimo de Seguranca antes do Despacho:", min_value=1, value=2)
            with col_in3:
                limite_caixas_dia = st.number_input("Capacidade MÁXIMA real de montagem (caixas de nivel 1/dia):", min_value=1, value=10)
                dificuldade_lote = st.selectbox("Dificuldade tecnica das pecas deste lote:", [1, 2, 3, 4, 5], index=0, 
                                                help="Nivel 1 representa pecas faceis. Nivel 5 representa pecas complexas (reduz o ritmo diario para ate 1/4 da capacidade).")

            st.markdown("---")
            st.markdown("### 2. Dados Extraidos da Planilha Tecnica Bruta")
            col_dados1, col_dados2 = st.columns(2)
            with col_dados1:
                txt_pavimentos = st.text_area("Pavimentos/Balancins afetados de acordo com o PDF:", value="Pav 39 ao 48")
                especificacao = st.text_input("Material / Chapa do Lote:", value="ACM BRANCO - OAS")
            with col_dados2:
                total_cx = st.number_input("Quantidade Total de Caixas Identificadas na Planilha:", min_value=1, value=94)
                total_m2 = st.number_input("Metragem Quadrada Total (m2) da Planilha:", min_value=0.1, value=212.95)

            btn_calcular_tudo = st.form_submit_button("Processar Fluxo Real de Fabrica e Salvar no Banco")

            if btn_calcular_tudo:
                if not cod_lote.strip():
                    st.error("Atencao! Voce precisa digitar um 'Codigo de Identificacao Interna' para conseguir salvar.")
                elif total_m2 <= 0:
                    st.error("Atencao! A Metragem Quadrada Total deve ser maior que zero.")
                else:
                    with st.spinner("Fracionando lotes e considerando complexidade das pecas..."):
                        dt_limite_conv = datetime.combine(data_necessidade_obra, datetime.min.time())
                        day_start = dt_limite_conv - timedelta(days=int(recuo_dias_base))
                        
                        caixas_restantes = total_cx
                        m2_por_caixa = total_m2 / total_cx
                        
                        peso_esforco = float(dificuldade_lote)
                        if dificuldade_lote == 5:
                            peso_esforco = 4.0
                            
                        capacidade_ajustada_dia = max(1.0, float(limite_caixas_dia) / peso_esforco)
                        
                        novos_registros = []
                        dia_corrente = day_start
                        
                        while caixas_restantes > 0:
                            if dia_corrente.weekday() in [5, 6]:
                                dia_corrente -= timedelta(days=1)
                                continue
                                
                            caixas_do_dia = min(int(round(capacidade_ajustada_dia)), int(caixas_restantes))
                            if caixas_do_dia == 0 and caixas_restantes > 0:
                                caixas_do_dia = 1
                                
                            m2_do_dia = caixas_do_dia * m2_por_caixa
                            
                            novos_registros.append({
                                "Obra_Vinculada": obra_selecionada, 
                                "EDT_Vinculado": edt_puro,
                                "Cod_Lote": cod_lote,
                                "Num_OP": None,
                                "Tipo_Material": especificacao,
                                "Qtd_Caixas": int(caixas_do_dia), 
                                "M2_Item": float(round(m2_do_dia, 2)),
                                "Data_Producao_Programada": dia_corrente.strftime('%Y-%m-%d %H:%M:%S'), 
                                "Data_Limite_Obra": dt_limite_conv.strftime('%Y-%m-%d %H:%M:%S'), 
                                "Romaneio_Chapas": txt_pavimentos, 
                                "Status_Item": "Pendente",
                                "Dificuldade": int(dificuldade_lote)
                            })
                            
                            caixas_restantes -= caixas_do_dia
                            dia_corrente -= timedelta(days=1)
                        
                        df_novos = pd.DataFrame(novos_registros)
                        salvar_lotes_micro(df_novos)
                        time.sleep(0.5)
                        
                    st.session_state.lote_salvo_sucesso = True
                    st.rerun()
    else:
        st.warning("Antes de cadastrar materiais, registre a Obra e suas Frentes Técnicas Macro na última aba.")

# ========================================================
# ABA 5: CADASTRAR NOVA OBRA / INCLUIR VÁRIAS ETAPAS
# ========================================================
with aba_nova_obra:
    st.header("Cadastrar Nova Obra e Frentes de Trabalho Macro")
    st.markdown("Insira os dados técnicos abaixo para registrar uma etapa. Você pode usar este formulário consecutivamente para injetar múltiplas etapas na mesma obra.")
    
    with st.form("form_nova_obra", clear_on_submit=True):
        nome_nova_obra = st.text_input("Nome Geral da Obra (Ex: OBRA OAS ou EDIFICIO MUNIQUE):").upper()
        
        col_o1, col_o2 = st.columns(2)
        with col_o1:
            edt_nova_obra = st.text_input("Codigo EDT da Etapa/Frente (Ex: 1.1.1.1 ou 2.1):")
            tipo_escopo_novo = st.selectbox("Tipo de Escopo Fachada:", ["ACM", "Vidro/Esquadria"])
            etapa_macro_nova = st.text_input("Frente Macro / Pavimentos (Ex: TORRE - ETAPA 3):")
        with col_o2:
            nome_tarefa_nova = st.text_input("Nome Detalhado da Tarefa (Ex: Instalacao ACM vigas Balancim 23):")
            m2_total_novo = st.number_input("Metragem Quadrada Macro Pactuada (m2):", min_value=0.1, value=100.0)
            
        col_d1, col_d2 = st.columns(2)
        with col_d1:
            data_inicio_nova = st.date_input("Data de Inicio Prevista:", value=datetime.now().date())
        with col_d2:
            data_fim_nova = st.date_input("Data Limite de Entrega final na Obra:", value=(datetime.now() + timedelta(days=30)).date())
            
        btn_salvar_obra = st.form_submit_button("Registrar e Validar Nova Obra no PCP")
        
        if btn_salvar_obra:
            if not nome_nova_obra.strip() or not edt_nova_obra.strip() or not nome_tarefa_nova.strip():
                st.error("Por favor, preencha o Nome da Obra, o Código EDT e o Nome Detalhado da Tarefa.")
            else:
                conn = conectar_banco()
                cursor = conn.cursor()
                try:
                    cursor.execute("""
                        INSERT INTO cronograma_macro (Obra, EDT, Tipo_Escopo, Etapa_Macro, Tarefa, M2_Total_Tarefa, Inicio_Previsto, Termino_Obra, Status)
                        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """, (
                        nome_nova_obra, 
                        edt_nova_obra, 
                        tipo_escopo_novo, 
                        etapa_macro_nova, 
                        nome_tarefa_nova, 
                        float(m2_total_novo), 
                        data_inicio_nova.strftime('%Y-%m-%d'), 
                        data_fim_nova.strftime('%Y-%m-%d'), 
                        "Pendente"
                    ))
                    conn.commit()
                    st.toast(f"Etapa {edt_nova_obra} salva! O formulário foi limpo para a próxima.", icon="✅")
                    time.sleep(0.5)
                    st.rerun()
                except sqlite3.IntegrityError:
                    st.error("Erro: Este Codigo EDT ja esta sendo usado em outra frente. Insira um codigo exclusivo.")
                finally:
                    conn.close()