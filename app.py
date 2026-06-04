import streamlit as st
import pandas as pd
import plotly.express as px
from datetime import datetime, timedelta
import sqlite3
import os
import time

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
    .semana-card {
        background-color: #EFF6FF;
        padding: 10px;
        border-radius: 5px;
        border-top: 4px solid #2563EB;
        text-align: center;
        margin-bottom: 10px;
    }
    </style>
""", unsafe_allow_html=True)

st.title("Passold - Sistema de Planejamento e Controle de Produção")
st.subheader("Gestão de OPs Semanais e Capacidade Operacional Flexível")

# Data atual de simulação do projeto (Ancorada em Junho de 2026)
HOJE_PROJETO = datetime(2026, 6, 4) 

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
            Status TEXT,
            Prazo_Medicao TEXT,
            Prazo_Desenho TEXT,
            Status_Projeto TEXT,
            Validacao_Prazo TEXT,
            Nova_Data_Projetista TEXT,
            Motivo_Revisao TEXT
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
    
    # Migrações preventivas para garantir que todas as colunas existam no banco do cliente
    novas_colunas_macro = {
        "Subdivisao": "TEXT",
        "Prazo_Medicao": "TEXT",
        "Prazo_Desenho": "TEXT",
        "Status_Projeto": "TEXT",
        "Validacao_Prazo": "TEXT",
        "Nova_Data_Projetista": "TEXT",
        "Motivo_Revisao": "TEXT"
    }
    
    for col, tipo in novas_colunas_macro.items():
        try:
            cursor.execute(f"ALTER TABLE cronograma_macro ADD COLUMN {col} {tipo}")
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
        
        # Garantir preenchimento padrão de dados nulos
        df['Subdivisao'] = df['Subdivisao'].fillna("Geral")
        df['Status_Projeto'] = df['Status_Projeto'].fillna("Aguardando Medição")
        df['Validacao_Prazo'] = df['Validacao_Prazo'].fillna("Aguardando Análise")
        df['Nova_Data_Projetista'] = df['Nova_Data_Projetista'].fillna("")
        df['Motivo_Revisao'] = df['Motivo_Revisao'].fillna("")
        
        # Se os prazos estiverem vazios, calcula uma estimativa segura retroativa baseada no término da obra
        for idx, row in df.iterrows():
            if pd.isna(row['Prazo_Medicao']) or row['Prazo_Medicao'] == "":
                df.at[idx, 'Prazo_Medicao'] = (row['Termino_Obra'] - timedelta(days=30)).strftime('%Y-%m-%d')
            if pd.isna(row['Prazo_Desenho']) or row['Prazo_Desenho'] == "":
                df.at[idx, 'Prazo_Desenho'] = (row['Termino_Obra'] - timedelta(days=15)).strftime('%Y-%m-%d')
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

# Carregamento inicial da base
df_banco_macro = carregar_macro()
df_banco_micro = carregar_micro()

if not df_banco_macro.empty:
    lista_obras_disponiveis = sorted(list(df_banco_macro['Obra'].unique()))
    obra_selecionada = st.selectbox("Selecione a Obra de Trabalho para a Fábrica / Lotes:", lista_obras_disponiveis)
    df_macro_filtrado = df_banco_macro[df_banco_macro['Obra'] == obra_selecionada]
else:
    st.info("O sistema está limpo e pronto para uso. Acesse a aba 'Cadastrar Nova Obra' para inserir sua primeira obra.")
    obra_selecionada = None
    df_macro_filtrado = pd.DataFrame()

# Criação unificada de abas organizadas por fluxo lógico de processo
aba_projeto, aba_tv, aba_geracao_op, aba_geral, aba_cadastro_chapas, aba_nova_obra, aba_config_sistema = st.tabs([
    "📐 PAINEL DO PROJETO (Calendário & Prazos)",
    "PAINEL DA TV (Chão de Fábrica)", 
    "Liberar OPs da Semana",
    "Visão Macro (Diretoria)", 
    "Vincular Datas na Relação de Materiais",
    "Cadastrar Nova Obra",
    "Configurações"
])

# ========================================================
# ABA 1: PAINEL DO PROJETO (CALENDÁRIO & ACORDO EDITÁVEL)
# ========================================================
with aba_projeto:
    st.header("📐 Central de Planejamento de Engenharia e Projetos")
    st.markdown("Veja o horizonte de entregas por semanas e valide os prazos acordados com o PCP antes de enviar o lote para a produção.")
    
    df_proj_total = carregar_macro()
    
    if not df_proj_total.empty:
        # Filtro Global Macro (Todas as obras) ou Micro (Obra Isolada)
        opcoes_filtro_proj = ["VER TODAS AS OBRAS"] + sorted(list(df_proj_total['Obra'].unique()))
        filtro_proj_selecionado = st.selectbox("🔍 Filtrar Escopo de Engenharia:", opciones_filtro_proj, key="filtro_janela_projeto")
        
        df_proj_exibicao = df_proj_total.copy()
        if filtro_proj_selecionado != "VER TODAS AS OBRAS":
            df_proj_exibicao = df_proj_exibicao[df_proj_exibicao['Obra'] == filtro_proj_selecionado]
            
        # Calendário Visual em Formato de Linhas do Tempo Semanais
        st.markdown("### 🗓️ Calendário de Frentes Técnicas por Semanas")
        
        df_proj_exibicao['Identificador_Calendario'] = df_proj_exibicao['Obra'] + " - " + df_proj_exibicao['Tarefa'] + " (" + df_proj_exibicao['Subdivisao'] + ")"
        
        fig_gantt_projeto = px.timeline(
            df_proj_exibicao, 
            x_start="Inicio_Previsto", 
            x_end="Termino_Obra", 
            y="Identificador_Calendario", 
            color="Validacao_Prazo",
            color_discrete_map={
                "Aguardando Análise": "#FBBF24",
                "Aceito / Prazo OK": "#10B981",
                "Solicitar Revisão / Recusado": "#EF4444"
            },
            labels={"Identificador_Calendario": "Frente de Trabalho / Balancim"}
        )
        fig_gantt_projeto.update_yaxes(autorange="reversed")
        fig_gantt_projeto.update_xaxes(dtick="M1", hoverformat="%d/%m/%Y")
        fig_gantt_projeto.update_layout(margin=dict(t=10, b=10, l=10, r=10), height=250)
        st.plotly_chart(fig_gantt_projeto, use_container_width=True)
        
        # Grid Interativo para Acordo Colaborativo de Datas
        st.markdown("---")
        st.markdown("### 🤝 Pactuação de Prazos (Joice <> Projetistas)")
        st.caption("Dica: Joice preenche os prazos limites desejados. Os meninos do projeto alteram o status de validação. Caso recusem, preenchem a contraproposta.")
        
        df_editor_prazos = st.data_editor(
            df_proj_exibicao[['id', 'Obra', 'Tarefa', 'Subdivisao', 'Prazo_Medicao', 'Prazo_Desenho', 'Validacao_Prazo', 'Nova_Data_Projetista', 'Motivo_Revisao']],
            column_config={
                "id": None,
                "Obra": st.column_config.TextColumn("Obra", disabled=True),
                "Tarefa": st.column_config.TextColumn("Etapa", disabled=True),
                "Subdivisao": st.column_config.TextColumn("Frente / Balancim", disabled=True),
                "Prazo_Medicao": st.column_config.TextColumn("Prazo Medição (AAAA-MM-DD)"),
                "Prazo_Desenho": st.column_config.TextColumn("Prazo Desenho (AAAA-MM-DD)"),
                "Validacao_Prazo": st.column_config.SelectboxColumn(
                    "Validação do Time",
                    options=["Aguardando Análise", "Aceito / Prazo OK", "Solicitar Revisão / Recusado"]
                ),
                "Nova_Data_Projetista": st.column_config.TextColumn("Se Recusado, qual data entregam? (AAAA-MM-DD)"),
                "Motivo_Revisao": st.column_config.TextColumn("Motivo da Restrição / Ajuste Técnico")
            },
            hide_index=True,
            use_container_width=True,
            key="grid_projetos_sincronizado"
        )
        
        if st.button("💾 Sincronizar Prazos de Engenharia com PCP"):
            conn = conectar_banco()
            cursor = conn.cursor()
            for _, r_p in df_editor_prazos.iterrows():
                cursor.execute("""
                    UPDATE cronograma_macro
                    SET Prazo_Medicao = ?, Prazo_Desenho = ?, Validacao_Prazo = ?, Nova_Data_Projetista = ?, Motivo_Revisao = ?
                    WHERE id = ?
                """, (
                    r_p['Prazo_Medicao'], r_p['Prazo_Desenho'], r_p['Validacao_Prazo'],
                    r_p['Nova_Data_Projetista'], r_p['Motivo_Revisao'], int(r_p['id'])
                ))
            conn.commit()
            conn.close()
            st.toast("Prazos e Acordos sincronizados com sucesso!", icon="📐")
            time.sleep(0.4)
            st.rerun()
    else:
        st.info("Nenhuma obra disponível no cronograma macro para gerenciamento de projetos.")

# ========================================================
# ABA 2: PAINEL DA TV (CARROSSEL SEMANAL E FILA DE CORTE)
# ========================================================
with aba_tv:
    st.header("Quadro de Produção de Fábrica - Passold")
    
    if obra_selecionada and not df_banco_micro.empty:
        df_chapas_obra = df_banco_micro[(df_banco_micro['Obra_Vinculada'] == obra_selecionada) & (df_banco_micro['Status_Item'] == "Liberado para Fabrica")].copy()
        
        if not df_chapas_obra.empty:
            df_chapas_obra['Data_Producao_Programada'] = pd.to_datetime(df_chapas_obra['Data_Producao_Programada'])
            
            df_chapas_obra['Semana_Num'] = df_chapas_obra['Data_Producao_Programada'].dt.isocalendar().week
            df_chapas_obra['Ano'] = df_chapas_obra['Data_Producao_Programada'].dt.isocalendar().year
            df_chapas_obra['Semana_Label'] = "Semana " + df_chapas_obra['Semana_Num'].astype(str)
            
            st.markdown("### 🗓️ Calendário de Liberações para a Produção")
            st.markdown("Veja abaixo a carga de trabalho distribuída pelas próximas semanas:")
            
            df_semanas = df_chapas_obra.groupby(['Ano', 'Semana_Num', 'Semana_Label']).agg({
                'Qtd_Caixas': 'sum',
                'M2_Item': 'sum',
                'Data_Producao_Programada': ['min', 'max']
            }).reset_index()
            df_semanas.columns = ['Ano', 'Semana_Num', 'Semana_Label', 'Total_Caixas', 'Total_M2', 'Data_Min', 'Data_Max']
            df_semanas = df_semanas.sort_values(by=['Ano', 'Semana_Num'])
            
            cols_carrossel = st.columns(len(df_semanas) if len(df_semanas) <= 6 else 6)
            for idx, row_sem in enumerate(df_semanas.itertuples()):
                col_alvo = cols_carrossel[idx % 6]
                with col_alvo:
                    intervalo_datas = f"{row_sem.Data_Min.strftime('%d/%m')} até {row_sem.Data_Max.strftime('%d/%m')}"
                    st.markdown(f"""
                    <div class="semana-card">
                        <strong style="color: #1E3A8A; font-size: 16px;">{row_sem.Semana_Label}</strong><br>
                        <small style="color: #6B7280;">{intervalo_datas}</small><br>
                        <span style="font-weight: bold; color: #2563EB;">{int(row_sem.Total_Caixas)} cx</span> | 
                        <span style="font-weight: bold; color: #10B981;">{row_sem.Total_M2:,.1f} m²</span>
                    </div>
                    """, unsafe_allow_html=True)
            
            st.markdown("---")
            
            lista_semanas_filtro = ["VER TODAS AS SEMANAS"] + list(df_semanas['Semana_Label'].unique())
            semana_foco = st.selectbox("🎯 Filtrar Lista de Corte pelo Calendário Semanal:", lista_semanas_filtro)
            
            # Filtro com sintaxe corrigida e segura (sem colchetes duplos causadores de ValueError)
            if semana_foco != "VER TODAS AS SEMANAS":
                df_tv_filtrado = df_chapas_obra[df_chapas_obra['Semana_Label'] == semana_foco]
            else:
                df_tv_filtrado = df_chapas_obra.copy()
                
            df_tv_filtrado = df_tv_filtrado.sort_values(by="Data_Producao_Programada", ascending=True)
            
            if not df_tv_filtrado.empty:
                total_cx_periodo = df_tv_filtrado['Qtd_Caixas'].sum()
                total_m2_periodo = df_tv_filtrado['M2_Item'].sum()
                
                c_meta1, c_meta2 = st.columns(2)
                c_meta1.metric("VOLUME TOTAL DE CAIXAS EM EXECUÇÃO", f"{int(total_cx_periodo)} cx")
                c_meta2.metric("METRAGEM TOTAL EM PRODUÇÃO", f"{total_m2_periodo:,.2f} m2")
                
                st.markdown(f"#### 📋 Fila de Execução na Fábrica ({semana_foco}):")
                for idx, row in df_tv_filtrado.iterrows():
                    with st.container():
                        col_l1, col_l2, col_l3 = st.columns([2, 1, 1])
                        op_txt = row['Num_OP'] if row['Num_OP'] else "Sem OP"
                        fase = row['Fase_Produtiva'] if 'Fase_Produtiva' in row and row['Fase_Produtiva'] else "Corte/Montagem"
                        cor_fase = "🔴" if "CORTE" in fase.upper() else "🔵"
                        
                        col_l1.markdown(f"**OP:** `{op_txt}` | **Lote/Sublote:** `{row['Cod_Lote']}` | **Material:** {row['Tipo_Material']}")
                        col_l2.markdown(f"**Meta do Dia:** {int(row['Qtd_Caixas'])} cx | {row['M2_Item']} m2")
                        col_l3.markdown(f"{cor_fase} **Fase Alvo:** `{fase}`")
                        
                        st.caption(f"Pavimentos Destino: {row['Romaneio_Chapas']} | Dia de Execução: {row['Data_Producao_Programada'].strftime('%d/%m/%Y')} | Limite p/ Obra: {row['Data_Limite_Obra'].strftime('%d/%m/%Y')}")
                        st.markdown("---")
            else:
                st.info("Nenhum item em execução para o período filtrado.")
        else:
            st.info(f"Nenhuma Ordem de Produção (OP) liberada para a {obra_selecionada} no momento.")
    else:
        st.info("Aguardando liberação de fatias ou importação de materiais.")

# ========================================================
# ABA 3: MESA DE TRABALHO DO PCP - LIBERAR OP'S
# ========================================================
with aba_geracao_op:
    st.header("Gerenciador de Ordens de Produção Semanais")
    st.markdown("Marque a caixa de seleção dos lotes planejados para rodar na semana e gere o número de OP padrão automaticamente.")
    
    if obra_selecionada and not df_banco_micro.empty:
        df_pendentes = df_banco_micro[(df_banco_micro['Obra_Vinculada'] == obra_selecionada) & (df_banco_micro['Status_Item'] == "Pendente")].copy()
        
        if not df_pendentes.empty:
            df_pendentes['Data_Producao_Programada'] = pd.to_datetime(df_pendentes['Data_Producao_Programada'])
            df_pendentes = df_pendentes.sort_values(by='Data_Producao_Programada', ascending=True)
            df_pendentes['Selecionar'] = False
            
            df_edicao = st.data_editor(
                df_pendentes[['id', 'Cod_Lote', 'Tipo_Material', 'Qtd_Caixas', 'M2_Item', 'Fase_Produtiva', 'Data_Producao_Programada', 'Romaneio_Chapas', 'Selecionar']],
                column_config={
                    "Data_Producao_Programada": st.column_config.DateColumn("Data Programada", format="DD/MM/YYYY"),
                    "Selecionar": st.column_config.CheckboxColumn("Liberar?", default=False)
                },
                hide_index=True,
                use_container_width=True,
                disabled=['id', 'Cod_Lote', 'Tipo_Material', 'Qtd_Caixas', 'M2_Item', 'Fase_Produtiva', 'Data_Producao_Programada', 'Romaneio_Chapas']
            )
            
            ids_selecionados = df_edicao[df_edicao['Selecionar'] == True]['id'].tolist()
            
            col_op1, col_op2 = st.columns([1, 3])
            with col_op1:
                prefixo_op = st.text_input("Prefixo Sequencial:", value=f"OP-{datetime.now().strftime('%Y')}-")
            
            if st.button("Confirmar Liberação e Enviar para Painel da TV"):
                if ids_selecionados:
                    conn = conectar_banco()
                    cursor = conn.cursor()
                    for item_id in ids_selecionados:
                        num_op_gerada = f"{prefixo_op}{str(item_id).zfill(3)}"
                        cursor.execute("""
                            UPDATE itens_detalhado 
                            SET Status_Item = 'Liberado para Fabrica', Num_OP = ? 
                            WHERE id = ?
                        """, (num_op_gerada, item_id))
                    conn.commit()
                    conn.close()
                    st.toast("Ordens de Produção liberadas e disparadas com sucesso!", icon="✅")
                    time.sleep(0.4)
                    st.rerun()
                else:
                    st.warning("Selecione ao menos um registro na coluna 'Liberar?' antes de submeter.")
        else:
            st.success("Tudo em dia! Não há remessas pendentes de liberação no momento.")
    else:
        st.info("Nenhum material cadastrado para gerar OPs.")

# ========================================================
# ABA 4: VISÃO MACRO (DASHBOARD DA DIRETORIA E GANTT GLOBAL)
# ========================================================
with aba_geral:
    st.header("Dashboard Executivo e Cronograma Macro")
    
    df_macro_completo = carregar_macro()
    
    if not df_macro_completo.empty:
        df_macro_calculado_geral = aplicar_planejamento_reverso(df_macro_completo)
        
        lista_filtro_diretoria = ["TODAS AS OBRAS"] + sorted(list(df_macro_calculado_geral['Obra'].unique()))
        filtro_dir = st.selectbox("Filtrar Painel Executivo por Obra:", lista_filtro_diretoria, key="filtro_diretoria_global")
        
        if filtro_dir != "TODAS AS OBRAS":
            df_macro_calculado_geral = df_macro_calculado_geral[df_macro_calculado_geral['Obra'] == filtro_dir]
            
        m_col1, m_col2, m_col3 = st.columns(3)
        m_col1.metric("Metragem Total Mapeada", f"{df_macro_calculado_geral['M2_Total_Tarefa'].sum():,.2f} m2")
        m_col2.metric("Frentes / Balancins Monitorados", f"{len(df_macro_calculado_geral)} frentes")
        m_col3.metric("Prazo Máximo do Cronograma", df_macro_calculado_geral['Termino_Obra'].max().strftime('%d/%m/%Y'))
        
        st.markdown("---")
        st.markdown("### 📈 Avanço Físico Real vs Meta Programada")
        
        resumo_progresso = []
        df_micro_dados = carregar_micro()
        
        for idx, row_macro in df_macro_calculado_geral.iterrows():
            edt = row_macro['EDT']
            tarefa = row_macro['Tarefa']
            subdiv = row_macro['Subdivisao']
            obra_nome = row_macro['Obra']
            
            if not df_micro_dados.empty:
                df_frente_micro = df_micro_dados[df_micro_dados['EDT_Vinculado'] == edt]
                cx_liberadas = df_frente_micro[df_frente_micro['Status_Item'] == "Liberado para Fabrica"]['Qtd_Caixas'].sum()
                cx_pendentes = df_frente_micro[df_frente_micro['Status_Item'] == "Pendente"]['Qtd_Caixas'].sum()
                total_cx_frente = cx_liberadas + cx_pendentes
            else:
                cx_liberadas, cx_pendentes, total_cx_frente = 0, 0, 0
                
            percentual = (cx_liberadas / total_cx_frente) if total_cx_frente > 0 else 0.0
            
            status_real = "⚪ Aguardando Lote" if total_cx_frente == 0 else "🟢 100% na Fábrica" if cx_pendentes == 0 else "🔵 Em Produção" if cx_liberadas > 0 else "🟡 Programado"
                
            resumo_progresso.append({
                "Obra": obra_nome,
                "Código EDT": edt,
                "Frente / Balancim": f"{tarefa} ({subdiv})",
                "Status": status_real,
                "Liberado (cx)": int(cx_liberadas),
                "Pendente (cx)": int(cx_pendentes),
                "Total (cx)": int(total_cx_frente),
                "Progresso": percentual
            })
            
        df_progresso_painel = pd.DataFrame(resumo_progresso)
        
        st.data_editor(
            df_progresso_painel,
            column_config={
                "Progresso": st.column_config.ProgressColumn("Avanço Real", format="%.0f%%", min_value=0.0, max_value=1.0)
            },
            hide_index=True,
            use_container_width=True,
            disabled=df_progresso_painel.columns
        )
        
        st.markdown("---")
        st.markdown("### 📊 Linha de Tempo Operacional Macro")
        
        df_macro_calculado_geral['Identificador_Visual'] = df_macro_calculado_geral['Obra'] + " - " + df_macro_calculado_geral['Tarefa'] + " (" + df_macro_calculado_geral['Subdivisao'] + ")"
        fig_gantt_diretoria = px.timeline(df_macro_calculado_geral, x_start="Inicio_Previsto", x_end="Termino_Obra", y="Identificador_Visual", color="Status")
        fig_gantt_diretoria.update_yaxes(autorange="reversed")
        st.plotly_chart(fig_gantt_diretoria, use_container_width=True)
    else:
        st.info("Nenhuma informação disponível no cronograma macro.")

# ========================================================
# ABA 5: INTELEGENGIA TEMPORAL (FATIAMENTO E COMPENSAÇÃO)
# ========================================================
with aba_cadastro_chapas:
    st.header("Inteligência Temporal: Fatiamento de Lotes e Cadência Realista")
    st.markdown("Insira os dados quantitativos de engenharia recebidos para gerar o fracionamento diário automático por dias úteis.")
    
    if obra_selecionada and not df_macro_filtrado.empty:
        opcoes_edt = [f"{row['EDT']} - {row['Tarefa']} [{row['Subdivisao']}]" for idx, row in df_macro_filtrado.iterrows()]
        
        with st.form("form_fatiamento_realista"):
            st.markdown("### 1. Parametrização Logística de Datas")
            col_in1, col_in2, col_in3 = st.columns(3)
            with col_in1:
                edt_selecionado = st.selectbox("Selecione a amarração técnica macro:", opcoes_edt)
                edt_puro = edt_selecionado.split(" ")[0]
                cod_lote = st.text_input("Código identificador da remessa técnica:")
            with col_in2:
                data_necessidade_obra = st.date_input("Data de Entrega limite na Obra:", value=datetime(2026, 7, 10).date(), format="DD/MM/YYYY")
                recuo_dias_base = st.number_input("Dias de Pulmão (Segurança logística):", min_value=0, value=3)
            with col_in3:
                dias_uteis_fabricacao = st.number_input("Dias Úteis de Produção Desejados:", min_value=1, value=10)
                dificuldade_lote = st.selectbox("Nível de Complexidade da Carga:", [1, 2, 3, 4, 5], index=2)

            st.markdown("### 2. Dados de Carga do Projeto")
            col_dados1, col_dados2 = st.columns(2)
            with col_dados1:
                txt_pavimentos = st.text_area("Pavimentos de destino:", value="FRENTE SUL - BALANCIM 05")
                especificacao = st.text_input("Material / Chapa do Lote:", value="ACM PRATA METÁLICO")
            with col_dados2:
                total_cx = st.number_input("Quantidade Total de Caixas do Lote:", min_value=1, value=44)
                total_m2 = st.number_input("M² Total da Remessa:", min_value=0.1, value=99.67)

            if st.form_submit_button("Gerar e Fatiar Carga na Fábrica"):
                if not cod_lote.strip():
                    st.error("Por favor, estipule uma etiqueta/código de lote.")
                else:
                    dt_limite_conv = datetime.combine(data_necessidade_obra, datetime.min.time())
                    dia_fim_producao = dt_limite_conv - timedelta(days=int(recuo_dias_base))
                    
                    cx_padrao = max(1, int(total_cx // dias_uteis_fabricacao))
                    m2_padrao = float(round(total_m2 / dias_uteis_fabricacao, 2))
                    
                    novos_registros = []
                    dia_corrente = dia_fim_producao
                    lista_dias_uteis = []
                    
                    while len(lista_dias_uteis) < int(dias_uteis_fabricacao):
                        if dia_corrente.weekday() in [5, 6]:
                            dia_corrente -= timedelta(days=1)
                            continue
                        lista_dias_uteis.append(dia_corrente)
                        dia_corrente -= timedelta(days=1)
                    
                    total_cx_acumulado = 0
                    total_m2_acumulado = 0
                    
                    for idx, dt_freg in enumerate(lista_dias_uteis):
                        fase_atual = "MONTAGEM FINAL" if (idx < int(dias_uteis_fabricacao) / 2) else "CORTE E USINAGEM"
                        
                        # ALGORITMO DE COMPENSAÇÃO DE ARREDONDAMENTO ATIVO NO PRIMEIRO DIA DO LOTE (ÚLTIMO DO LOOP REVERSO)
                        if idx == len(lista_dias_uteis) - 1:
                            cx_final = int(total_cx - total_cx_acumulado)
                            m2_final = float(round(total_m2 - total_m2_acumulado, 2))
                        else:
                            cx_final = cx_padrao
                            m2_final = m2_padrao
                            
                        total_cx_acumulado += cx_final
                        total_m2_acumulado += m2_final
                        
                        novos_registros.append({
                            "Obra_Vinculada": obra_selecionada, "EDT_Vinculado": edt_puro, "Cod_Lote": cod_lote, "Num_OP": None,
                            "Tipo_Material": especificacao, "Qtd_Caixas": cx_final, "M2_Item": m2_final,
                            "Data_Producao_Programada": dt_freg.strftime('%Y-%m-%d %H:%M:%S'), "Data_Limite_Obra": dt_limite_conv.strftime('%Y-%m-%d %H:%M:%S'),
                            "Romaneio_Chapas": txt_pavimentos, "Status_Item": "Pendente", "Dificuldade": int(dificuldade_lote), "Fase_Produtiva": fase_atual
                        })
                    
                    salvar_lotes_micro(pd.DataFrame(novos_registros))
                    st.toast("Lote fatiado com compensação ativa e salvo com sucesso!", icon="✅")
                    time.sleep(0.4)
                    st.rerun()
    else:
        st.warning("Cadastre uma obra e suas subdivisões técnicas antes de realizar fatiamentos.")

# ========================================================
# ABA 6: CADASTRO E EDITOR DIRETO DO CRONOGRAMA MACRO
# ========================================================
with aba_nova_obra:
    st.header("Cadastrar Nova Obra e Frentes de Trabalho Macro")
    
    if 'm_obra' not in st.session_state: st.session_state.m_obra = ""
    if 'm_escopo' not in st.session_state: st.session_state.m_escopo = "ACM"
    
    with st.form("form_cadastro_macro"):
        nome_nova_obra = st.text_input("Nome Corporativo da Obra:", value=st.session_state.m_obra).upper()
        col_c1, col_c2 = st.columns(2)
        with col_c1:
            tipo_escopo_novo = st.selectbox("Segmento do Escopo:", ["ACM", "Vidro/Esquadria"], index=0 if st.session_state.m_escopo == "ACM" else 1)
            etapa_macro_nova = st.text_input("Etapa Macro (Ex: Fachada Frontal):")
            nome_tarefa_nova = st.text_input("Descrição Detalhada da Frente:")
        with col_c2:
            edt_nova_obra = st.text_input("Código EDT Único da Frente:")
            subdivisao_nova = st.text_input("Identificação do Balancim:").upper()
            m2_total_novo = st.number_input("Metragem Quadrada Total Contratada:", min_value=0.1, value=150.0)
            
        col_d1, col_d2 = st.columns(2)
        with col_d1: data_inicio_nova = st.date_input("Data Estimada para Start de Obra:")
        with col_d2: data_fim_nova = st.date_input("Data de Término Contratual:")
        
        if st.form_submit_button("Gravar Frente de Trabalho Macro"):
            if not nome_nova_obra.strip() or not edt_nova_obra.strip() or not subdivisao_nova.strip():
                st.error("Preencha Nome da Obra, Código EDT e Balancim.")
            else:
                st.session_state.m_obra = nome_nova_obra
                st.session_state.m_escopo = tipo_escopo_novo
                
                conn = conectar_banco()
                cursor = conn.cursor()
                try:
                    cursor.execute("""
                        INSERT INTO cronograma_macro (Obra, EDT, Tipo_Escopo, Etapa_Macro, Subdivisao, Tarefa, M2_Total_Tarefa, Inicio_Previsto, Termino_Obra, Status)
                        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, 'Pendente')
                    """, (nome_nova_obra, edt_nova_obra, tipo_escopo_novo, etapa_macro_nova, subdivisao_nova, nome_tarefa_nova, float(m2_total_novo), data_inicio_nova.strftime('%Y-%m-%d'), data_fim_nova.strftime('%Y-%m-%d')))
                    conn.commit()
                    st.toast("Frente macro registrada no cronograma geral!", icon="🚀")
                    time.sleep(0.4)
                    st.rerun()
                except sqlite3.IntegrityError:
                    st.error("Erro: Este código EDT já está sendo utilizado em outra frente.")
                finally:
                    conn.close()
                    
    st.markdown("---")
    st.markdown("### ✏️ Editor de Frentes Cadastradas (Modificação Direta de Prazos)")
    
    df_macro_edicao_total = carregar_macro()
    if not df_macro_edicao_total.empty:
        df_macro_edicao_total['Inicio_Previsto'] = df_macro_edicao_total['Inicio_Previsto'].dt.strftime('%Y-%m-%d')
        df_macro_edicao_total['Termino_Obra'] = df_macro_edicao_total['Termino_Obra'].dt.strftime('%Y-%m-%d')
        
        df_macro_editado = st.data_editor(
            df_macro_edicao_total[['id', 'Obra', 'EDT', 'Tipo_Escopo', 'Etapa_Macro', 'Subdivisao', 'Tarefa', 'M2_Total_Tarefa', 'Inicio_Previsto', 'Termino_Obra']],
            hide_index=True, use_container_width=True, disabled=['id', 'EDT']
        )
        
        if st.button("💾 Aplicar e Salvar Alterações do Cronograma Macro"):
            conn = conectar_banco()
            cursor = conn.cursor()
            for _, r_mac in df_macro_editado.iterrows():
                cursor.execute("""
                    UPDATE cronograma_macro
                    SET Obra = ?, Tipo_Escopo = ?, Etapa_Macro = ?, Subdivisao = ?, Tarefa = ?, M2_Total_Tarefa = ?, Inicio_Previsto = ?, Termino_Obra = ?
                    WHERE id = ?
                """, (r_mac['Obra'], r_mac['Tipo_Escopo'], r_mac['Etapa_Macro'], r_mac['Subdivisao'], r_mac['Tarefa'], float(r_mac['M2_Total_Tarefa']), r_mac['Inicio_Previsto'], r_mac['Termino_Obra'], int(r_mac['id'])))
            conn.commit()
            conn.close()
            st.toast("Cronograma macro sincronizado e atualizado!", icon="🔄")
            time.sleep(0.4)
            st.rerun()

# ========================================================
# ABA 7: CONFIGURAÇÕES E MANUTENÇÃO DO SISTEMA PCP
# ========================================================
with aba_config_sistema:
    st.header("Painel de Controle e Segurança do PCP")
    senha_digitada = st.text_input("Insira a senha mestra para comandos de auditoria:", type="password")
    
    if senha_digitada == "Jv568279.":
        st.success("Credenciais validadas. Controles de banco liberados.")
        if st.button("⚠️ CONFIRMAR EXCLUSÃO HISTÓRICA E RESETAR BANCO COMPLETAMENTE"):
            resetar_banco_dados_completo()
            st.toast("Banco limpo!", icon="🗑️")
            time.sleep(0.4)
            st.rerun()