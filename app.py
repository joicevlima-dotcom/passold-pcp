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
st.subheader("Gestao de OPs Semanais e Capacidade Operacional Flexivel")

# Data atual de simulacao do projeto (Ancorada em Junho de 2026)
HOJE_PROJETO = datetime(2026, 6, 3) 

# ========================================================
# ESTRUTURA DO BANCO DE DADOS (SQLITE)
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
            Subdivisao TEXT,
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
            Dificuldade INTEGER,
            Fase_Produtiva TEXT
        )
    """)
    
    # Remendos preventivos caso o banco local ja exista sem as colunas novas
    try:
        cursor.execute("ALTER TABLE cronograma_macro ADD COLUMN Subdivisao TEXT")
    except sqlite3.OperationalError:
        pass
        
    try:
        cursor.execute("ALTER TABLE itens_detalhado ADD COLUMN Fase_Produtiva TEXT")
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
        
        # Escudo anti-keyerror caso o banco antigo nao tenha a coluna
        if 'Subdivisao' not in df.columns:
            df['Subdivisao'] = None
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

def resetar_banco_dados_completo():
    conn = conectar_banco()
    cursor = conn.cursor()
    cursor.execute("DELETE FROM cronograma_macro")
    cursor.execute("DELETE FROM itens_detalhado")
    conn.commit()
    conn.close()

df_banco_macro = carregar_macro()
df_banco_micro = carregar_micro()

if not df_banco_macro.empty:
    lista_obras_disponiveis = sorted(list(df_banco_macro['Obra'].unique()))
    obra_selecionada = st.selectbox("Selecione a Obra de Trabalho para a Fabrica / Lotes:", lista_obras_disponiveis)
    df_macro_filtrado = df_banco_macro[df_banco_macro['Obra'] == obra_selecionada]
else:
    st.info("O sistema esta limpo e pronto para uso. Acesse a aba 'Cadastrar Nova Obra' para inserir sua primeira obra.")
    obra_selecionada = None
    df_macro_filtrado = pd.DataFrame()

if 'modo_visao_tv' not in st.session_state:
    st.session_state.modo_visao_tv = "SEMANA"

aba_tv, aba_geracao_op, aba_geral, aba_cadastro_chapas, aba_nova_obra, aba_config_sistema = st.tabs([
    "PAINEL DA TV (Chao de Fabrica)", 
    "Liberar OPs da Semana",
    "Visao Macro (Diretoria)", 
    "Vincular Datas na Relacao de Materiais",
    "Cadastrar Nova Obra",
    "Configuracoes"
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
                
                st.markdown("#### Sequencia Cronologica de Trabalho no Galpao:")
                for idx, row in df_tv_filtrado.iterrows():
                    with st.container():
                        col_l1, col_l2, col_l3 = st.columns([2, 1, 1])
                        op_txt = row['Num_OP'] if row['Num_OP'] else "Sem OP"
                        fase = row['Fase_Produtiva'] if 'Fase_Produtiva' in row and row['Fase_Produtiva'] else "Corte/Montagem"
                        
                        cor_fase = "🔴" if "CORTE" in fase else "🔵"
                        
                        col_l1.markdown(f"**OP:** `{op_txt}` | **Lote/Sublote:** `{row['Cod_Lote']}` | **Material:** {row['Tipo_Material']}")
                        col_l2.markdown(f"**Meta do Dia:** {int(row['Qtd_Caixas'])} cx | {row['M2_Item']} m2")
                        col_l3.markdown(f"{cor_fase} **Fase Alvo:** `{fase}`")
                        
                        st.caption(f"Pavimentos Destino: {row['Romaneio_Chapas']} | Dia de Execucao: {row['Data_Producao_Programada'].strftime('%d/%m/%Y')} | Limite p/ Obra: {row['Data_Limite_Obra'].strftime('%d/%m/%Y')}")
                        st.markdown("---")
            else:
                st.info(f"Nenhuma Ordem de Producao (OP) liberada para a {obra_selecionada} esta semana.")
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
            
            colunas_exibir = ['id', 'Cod_Lote', 'Tipo_Material', 'Qtd_Caixas', 'M2_Item', 'Fase_Produtiva', 'Data_Producao_Programada', 'Romaneio_Chapas', 'Selecionar']
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
# ABA 3: VISAO MACRO DIRETORIA
# ========================================================
with aba_geral:
    st.header("Dashboard Executivo e Cronograma Macro")
    
    df_macro_completo = carregar_macro()
    
    if not df_macro_completo.empty:
        df_macro_calculado_geral = aplicar_planejamento_reverso(df_macro_completo)
        
        lista_filtro_diretoria = ["TODAS AS OBRAS"] + sorted(list(df_macro_calculado_geral['Obra'].unique()))
        filtro_dir = st.selectbox("Filtrar Painel Executivo por Obra:", lista_filtro_diretoria)
        
        if filtro_dir != "TODAS AS OBRAS":
            df_macro_calculado_geral = df_macro_calculado_geral[df_macro_calculado_geral['Obra'] == filtro_dir]
            
        m_col1, m_col2, m_col3 = st.columns(3)
        m_col1.metric("Metragem Total no Filtro", f"{df_macro_calculado_geral['M2_Total_Tarefa'].sum():,.2f} m2")
        m_col2.metric("Subdivisoes / Balancins Exibidos", f"{len(df_macro_calculado_geral)} frentes")
        m_col3.metric("Prazo de Entrega Mais Distante", df_macro_calculado_geral['Termino_Obra'].max().strftime('%d/%m/%Y'))
        
        st.markdown("---")
        
        st.markdown("### 📊 Linha do Tempo de Execucao (Gantt)")
        df_macro_calculado_geral['Identificador_Visual'] = (
            df_macro_calculado_geral['Obra'] + " - " + 
            df_macro_calculado_geral['Tarefa'] + " (" + 
            df_macro_calculado_geral['Subdivisao'].fillna('Geral') + ")"
        )
        
        fig_gantt = px.timeline(
            df_macro_calculado_geral, 
            x_start="Inicio_Previsto", 
            x_end="Termino_Obra", 
            y="Identificador_Visual", 
            color="Obra" if filtro_dir == "TODAS AS OBRAS" else "Status",
            labels={"Identificador_Visual": "Frente de Trabalho / Balancim"}
        )
        fig_gantt.update_yaxes(autorange="reversed")
        fig_gantt.update_xaxes(dtick="M1", hoverformat="%d/%m/%Y")
        fig_gantt.update_layout(margin=dict(t=10, b=10, l=10, r=10))
        st.plotly_chart(fig_gantt, use_container_width=True)
    else:
        st.info("Aguardando inserção de dados no PCP.")

# ========================================================
# ABA 4: VINCULO DE DATAS E CADÊNCIA FLEXÍVEL (PADRÃO DD/MM/AAAA BR)
# ========================================================
with aba_cadastro_chapas:
    st.header("Inteligencia Temporal: Fatiamento de Lotes e Cadencia Realista")
    st.markdown("Lance o lote ou a remessa fatiada parcial combinada com o projetista para gerar uma distribuicao sem erros.")
    
    if 'lote_salvo_sucesso' in st.session_state and st.session_state.lote_salvo_sucesso:
        st.toast("Remessa salva com sucesso no banco da Passold!", icon="✅")
        st.success("Sucesso! Remessa gerada e salva como Pendente. Confira na aba 'Liberar OPs da Semana'.")
        st.session_state.lote_salvo_sucesso = False

    if obra_selecionada and not df_macro_filtrado.empty:
        opcoes_edt = []
        for idx, row in df_macro_filtrado.iterrows():
            sub_txt = f" [{row['Subdivisao']}]" if row['Subdivisao'] else ""
            opcoes_edt.append(f"{row['EDT']} - {row['Tarefa']}{sub_txt}")
        
        with st.form("form_injecao_datas_flexivel"):
            st.markdown("### 1. Dados Cronologicos Combinados (Projetista/Obra)")
            col_in1, col_in2, col_in3 = st.columns(3)
            with col_in1:
                edt_selecionado = st.selectbox("Esta relacao tecnica pertence a qual frente macro?", opcoes_edt)
                edt_puro = edt_selecionado.split(" ")[0]
                cod_lote = st.text_input("Codigo/Identificacao desta Remessa (Ex: LOTE 3-PARTE A):")
            with col_in2:
                # 🇧🇷 Mudamos aqui! Adicionado o format="DD/MM/YYYY" para ficar totalmente brasileiro!
                data_necessidade_obra = st.date_input("Data Limite de Despacho desta Remessa:", value=datetime(2026, 7, 10).date(), format="DD/MM/YYYY")
                recuo_dias_base = st.number_input("Dias de Pulmao (Seguranca antes do caminhao sair):", min_value=0, value=2)
            with col_in3:
                dias_uteis_fabricacao = st.number_input("Dias Uteis de Production Estimados p/ esta quantidade:", min_value=1, value=20)
                dificuldade_lote = st.selectbox("Nivel de Complexidade Tecnica:", [1, 2, 3, 4, 5], index=3)

            st.markdown("---")
            st.markdown("### 2. Dados Quantitativos Fatiados do Projeto")
            col_dados1, col_dados2 = st.columns(2)
            with col_dados1:
                txt_pavimentos = st.text_area("Pavimentos/Balancins Destino (Ex: Pav 39 ao 43):", value="Pav 39 ao 43")
                especificacao = st.text_input("Material / Chapa do Lote:", value="ACM BRANCO")
            with col_dados2:
                total_cx = st.number_input("Quantidade de Caixas desta Remessa Parcial:", min_value=1, value=50)
                total_m2 = st.number_input("Metragem Quadrada (m2) desta Remessa Parcial:", min_value=0.1, value=113.27)

            btn_calcular_tudo = st.form_submit_button("Distribuir Remessa Realista na Fabrica")

            if btn_calcular_tudo:
                if not cod_lote.strip():
                    st.error("Por favor, digite uma identificacao de lote/sublote para salvar.")
                else:
                    with st.spinner("Gerando cadencia inteligente por etapas..."):
                        dt_limite_conv = datetime.combine(data_necessidade_obra, datetime.min.time())
                        dia_fim_producao = dt_limite_conv - timedelta(days=int(recuo_dias_base))
                        
                        caixas_por_dia_real = total_cx / float(dias_uteis_fabricacao)
                        m2_por_dia_real = total_m2 / float(dias_uteis_fabricacao)
                        
                        novos_registros = []
                        dia_corrente = dia_fim_producao
                        
                        dias_uteis_contados = 0
                        
                        while dias_uteis_contados < int(dias_uteis_fabricacao):
                            if dia_corrente.weekday() in [5, 6]:
                                dia_corrente -= timedelta(days=1)
                                continue
                            
                            dias_uteis_contados += 1
                            
                            if dias_uteis_contados <= (int(dias_uteis_fabricacao) / 2):
                                fase_atual = "MONTAGEM FINAL"
                            else:
                                fase_atual = "CORTE E USINAGEM"
                                
                            novos_registros.append({
                                "Obra_Vinculada": obra_selecionada, 
                                "EDT_Vinculado": edt_puro,
                                "Cod_Lote": cod_lote,
                                "Num_OP": None,
                                "Tipo_Material": especificacao,
                                "Qtd_Caixas": max(1, int(round(caixas_por_dia_real))), 
                                "M2_Item": float(round(m2_por_dia_real, 2)),
                                "Data_Producao_Programada": dia_corrente.strftime('%Y-%m-%d %H:%M:%S'), 
                                "Data_Limite_Obra": dt_limite_conv.strftime('%Y-%m-%d %H:%M:%S'), 
                                "Romaneio_Chapas": txt_pavimentos, 
                                "Status_Item": "Pendente",
                                "Dificuldade": int(dificuldade_lote),
                                "Fase_Produtiva": fase_atual
                            })
                            
                            dia_corrente -= timedelta(days=1)
                        
                        df_novos = pd.DataFrame(novos_registros)
                        salvar_lotes_micro(df_novos)
                        time.sleep(0.5)
                        
                    st.session_state.lote_salvo_sucesso = True
                    st.rerun()
    else:
        st.warning("Antes de cadastrar materiais, registre a Obra e suas Frentes Técnicas Macro na última aba.")

# ========================================================
# ABA 5: CADASTRAR NOVA OBRA (PADRÃO DD/MM/AAAA BR)
# ========================================================
with aba_nova_obra:
    st.header("Cadastrar Nova Obra e Frentes de Trabalho Macro")
    st.markdown("Insira os dados da subdivisao. O sistema mantem a Obra, Escopo e Datas fixas para voce cadastrar multiplos balancins em sequencia.")

    if 'mem_obra' not in st.session_state: st.session_state.mem_obra = ""
    if 'mem_escopo' not in st.session_state: st.session_state.mem_escopo = "ACM"
    if 'mem_frente_macro' not in st.session_state: st.session_state.mem_frente_macro = ""
    if 'mem_tarefa' not in st.session_state: st.session_state.mem_tarefa = ""
    if 'mem_dt_inicio' not in st.session_state: st.session_state.mem_dt_inicio = datetime.now().date()
    if 'mem_dt_fim' not in st.session_state: st.session_state.mem_dt_fim = (datetime.now() + timedelta(days=30)).date()

    with st.form("form_nova_obra_sequencial"):
        nome_nova_obra = st.text_input("Nome Geral da Obra (Ex: OBRA OAS ou EDIFICIO MUNIQUE):", value=st.session_state.mem_obra).upper()
        
        col_o1, col_o2 = st.columns(2)
        with col_o1:
            tipo_escopo_novo = st.selectbox("Tipo de Escopo Fachada:", ["ACM", "Vidro/Esquadria"], index=0 if st.session_state.mem_escopo == "ACM" else 1)
            etapa_macro_nova = st.text_input("Frente Macro / Pavimentos (Ex: TORRE - ETAPA 3):", value=st.session_state.mem_frente_macro)
            nome_tarefa_nova = st.text_input("Nome Detalhado da Tarefa (Ex: Instalacao ACM vigas):", value=st.session_state.mem_tarefa)
        
        with col_o2:
            edt_nova_obra = st.text_input("Codigo EDT da Frente/Subdivisao ÚNICO (Ex: 1.1.1.1 ou 2.1):", value="")
            subdivisao_nova = st.text_input("Subdivisao / Balancim Especifico (Ex: Balancim 04 / Fachada Sul):", value="").upper()
            m2_total_novo = st.number_input("Metragem Quadrada Pactuada p/ esta subdivisao (m2):", min_value=0.1, value=100.0, step=10.0)
            
        col_d1, col_d2 = st.columns(2)
        with col_d1:
            # 🇧🇷 Mudamos aqui! Adicionado o format="DD/MM/YYYY" para ficar normal e legivel
            data_inicio_nova = st.date_input("Data Alvo para Inicio da Instalacao no Predio:", value=st.session_state.mem_dt_inicio, format="DD/MM/YYYY")
        with col_d2:
            # 🇧🇷 Mudamos aqui também!
            data_fim_nova = st.date_input("Prazo Maximo do Balancim Pronto na Obra:", value=st.session_state.mem_dt_fim, format="DD/MM/YYYY")
            
        btn_salvar_obra = st.form_submit_button("Registrar Subdivisao e Manter Base")
        
        if btn_salvar_obra:
            if not nome_nova_obra.strip() or not edt_nova_obra.strip() or not nome_tarefa_nova.strip() or not subdivisao_nova.strip():
                st.error("Por favor, preencha o Nome da Obra, o Código EDT, o Balancim e a Tarefa.")
            else:
                st.session_state.mem_obra = nome_nova_obra
                st.session_state.mem_escopo = tipo_escopo_novo
                st.session_state.mem_frente_macro = etapa_macro_nova
                st.session_state.mem_tarefa = nome_tarefa_nova
                st.session_state.mem_dt_inicio = data_inicio_nova
                st.session_state.mem_dt_fim = data_fim_nova
                
                conn = conectar_banco()
                cursor = conn.cursor()
                try:
                    cursor.execute("""
                        INSERT INTO cronograma_macro (Obra, EDT, Tipo_Escopo, Etapa_Macro, Subdivisao, Tarefa, M2_Total_Tarefa, Inicio_Previsto, Termino_Obra, Status)
                        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """, (
                        nome_nova_obra, 
                        edt_nova_obra, 
                        tipo_escopo_novo, 
                        etapa_macro_nova,
                        subdivisao_nova,
                        nome_tarefa_nova, 
                        float(m2_total_novo), 
                        data_inicio_nova.strftime('%Y-%m-%d'), 
                        data_fim_nova.strftime('%Y-%m-%d'), 
                        "Pendente"
                    ))
                    conn.commit()
                    st.toast(f"Pimba! Subdivisao {subdivisao_nova} inserida com sucesso. Insira a proxima!", icon="🚀")
                    time.sleep(0.4)
                    st.rerun()
                except sqlite3.IntegrityError:
                    st.error(f"Erro: O Codigo EDT '{edt_nova_obra}' ja existe no sistema. Cada subdivisao precisa de um EDT exclusivo.")
                finally:
                    conn.close()

# ========================================================
# ABA 6: CONFIGURAÇÕES E LIMPEZA DE BANCO
# ========================================================
with aba_config_sistema:
    st.header("Painel de Controle e Limpeza do Sistema")
    st.markdown("Use esta area se precisar deletar de vez registros antigos de teste e iniciar o software do zero.")
    
    st.warning("Atencao: Clicar no botao abaixo removera permanentemente todas as obras, frentes e lotes salvos no momento.")
    if st.button("LIMPAR BANCO DE DADOS DE TESTE COMPLETAMENTE"):
        resetar_banco_dados_completo()
        st.session_state.mem_obra = ""
        st.session_state.mem_frente_macro = ""
        st.session_state.mem_tarefa = ""
        st.toast("Banco de dados completamente resetado!", icon="🗑️")
        time.sleep(0.5)
        st.rerun()