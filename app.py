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
    .login-container {
        max-width: 400px;
        margin: 0 auto;
        padding: 30px;
        background-color: #F8FAFC;
        border-radius: 10px;
        border: 1px solid #E2E8F0;
    }
    .card-engenharia {
        background-color: #FFFFFF;
        padding: 15px;
        border-radius: 8px;
        border: 1px solid #E2E8F0;
        margin-bottom: 15px;
        box-shadow: 0 2px 4px rgba(0,0,0,0.05);
    }
    .alerta-piscante {
        background-color: #FEE2E2;
        border: 2px solid #EF4444;
        padding: 10px;
        border-radius: 6px;
        color: #991B1B;
        font-weight: bold;
        animation: blinker 1.5s linear infinite;
        text-align: center;
        margin-top: 10px;
    }
    @keyframes blinker {
        50% { opacity: 0.5; }
    }
    </style>
""", unsafe_allow_html=True)

# Data atual de simulação do projeto (Ancorada em Junho de 2026)
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
            Status TEXT,
            Status_Engenharia TEXT DEFAULT '🔴 Aguardando Medição In Loco'
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

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS usuarios (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            usuario TEXT UNIQUE,
            nome TEXT,
            setor TEXT,
            senha TEXT
        )
    """)

    cursor.execute("SELECT COUNT(*) FROM usuarios")
    if cursor.fetchone()[0] == 0:
        cursor.execute("""
            INSERT INTO usuarios (usuario, nome, setor, senha)
            VALUES ('master', 'Joice Master', 'Master', 'Jv568279.')
        """)

    try:
        cursor.execute("ALTER TABLE cronograma_macro ADD COLUMN Subdivisao TEXT")
    except sqlite3.OperationalError:
        pass

    try:
        cursor.execute("ALTER TABLE cronograma_macro ADD COLUMN Status_Engenharia TEXT DEFAULT '🔴 Aguardando Medição In Loco'")
    except sqlite3.OperationalError:
        pass

    try:
        cursor.execute("ALTER TABLE itens_detalhado ADD COLUMN Fase_Produtiva TEXT")
    except sqlite3.OperationalError:
        pass

    conn.commit()
    conn.close()

inicializar_banco_de_dados()

# ========================================================
# FUNÇÕES DE BANCO DE DADOS
# ========================================================
def carregar_macro():
    conn = conectar_banco()
    df = pd.read_sql_query("SELECT * FROM cronograma_macro", conn)
    conn.close()
    if not df.empty:
        df['Inicio_Previsto'] = pd.to_datetime(df['Inicio_Previsto'])
        df['Termino_Obra'] = pd.to_datetime(df['Termino_Obra'])
        if 'Subdivisao' not in df.columns:
            df['Subdivisao'] = "Geral"
        if 'Status_Engenharia' not in df.columns:
            df['Status_Engenharia'] = "🔴 Aguardando Medição In Loco"
    return df

def carregar_micro():
    conn = conectar_banco()
    df = pd.read_sql_query("SELECT * FROM itens_detalhado", conn)
    conn.close()
    if not df.empty:
        df['Data_Producao_Programada'] = pd.to_datetime(df['Data_Producao_Programada'])
        df['Data_Limite_Obra'] = pd.to_datetime(df['Data_Limite_Obra'])
        # CORREÇÃO 5: Garantir que Fase_Produtiva existe mesmo em dados antigos
        if 'Fase_Produtiva' not in df.columns:
            df['Fase_Produtiva'] = "N/A"
    return df

def atualizar_status_engenharia(edt_id, novo_status):
    conn = conectar_banco()
    cursor = conn.cursor()
    cursor.execute("UPDATE cronograma_macro SET Status_Engenharia = ? WHERE id = ?", (novo_status, edt_id))
    conn.commit()
    conn.close()

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

def verificar_login(usuario, senha):
    conn = conectar_banco()
    cursor = conn.cursor()
    cursor.execute("SELECT nome, setor FROM usuarios WHERE usuario = ? AND senha = ?", (usuario, senha))
    resultado = cursor.fetchone()
    conn.close()
    return resultado

# ========================================================
# CONTROLE DE SESSÃO E LOGIN
# ========================================================
if 'autenticado' not in st.session_state:
    st.session_state.autenticado = False
    st.session_state.usuario_nome = ""
    st.session_state.usuario_setor = ""

if not st.session_state.autenticado:
    st.markdown("<h1 style='text-align: center; color: #1E3A8A;'>Passold Sistemas</h1>", unsafe_allow_html=True)
    st.markdown("<h4 style='text-align: center; color: #6B7280; margin-bottom: 30px;'>PCP & Controle Operacional</h4>", unsafe_allow_html=True)

    with st.container():
        st.markdown('<div class="login-container">', unsafe_allow_html=True)
        st.subheader("🔑 Login do Sistema")
        user_input = st.text_input("Usuário:")
        pass_input = st.text_input("Senha:", type="password")
        btn_login = st.button("Entrar no PCP")
        st.markdown('</div>', unsafe_allow_html=True)

        if btn_login:
            dados_user = verificar_login(user_input.strip(), pass_input)
            if dados_user:
                st.session_state.autenticado = True
                st.session_state.usuario_nome = dados_user[0]
                st.session_state.usuario_setor = dados_user[1]
                st.rerun()
            else:
                st.error("Usuário ou Senha inválidos.")
    st.stop()

# Título Principal do Sistema Logado
col_header1, col_header2 = st.columns([4, 1])
with col_header1:
    st.title("Passold - PCP Inteligente")
    st.caption(f"Usuário: **{st.session_state.usuario_nome}** | Setor: `{st.session_state.usuario_setor}`")
with col_header2:
    st.write("")
    if st.button("🚪 Sair / Logoff"):
        st.session_state.autenticado = False
        st.rerun()

# Carregar dados fundamentais
df_banco_macro = carregar_macro()
df_banco_micro = carregar_micro()

if not df_banco_macro.empty:
    lista_obras_disponiveis = sorted(list(df_banco_macro['Obra'].unique()))
    obra_selecionada = st.selectbox("Selecione a Obra de Trabalho:", lista_obras_disponiveis)
    df_macro_filtrado = df_banco_macro[df_banco_macro['Obra'] == obra_selecionada]
else:
    obra_selecionada = None
    df_macro_filtrado = pd.DataFrame()

# ========================================================
# FILTRO DINÂMICO DE ABAS POR PERFIL DE ACESSO
# ========================================================
setor = st.session_state.usuario_setor

abas_disponiveis = []
if setor in ["Master", "Produção", "Diretoria", "Engenharia"]:
    abas_disponiveis.append("PAINEL DA TV (Chão de Fábrica)")
if setor in ["Master"]:
    abas_disponiveis.append("Liberar OPs da Semana")
if setor in ["Master", "Diretoria"]:
    abas_disponiveis.append("Visão Macro (Diretoria)")
if setor in ["Master"]:
    abas_disponiveis.append("Vincular Datas (Materiais)")
    abas_disponiveis.append("Cadastrar Nova Obra")
if setor in ["Master", "Engenharia"]:
    abas_disponiveis.append("Painel Técnico da Engenharia")
if setor in ["Master"]:
    abas_disponiveis.append("Configurações do Sistema")

conteudo_sistema = st.container()

with conteudo_sistema:
    abas_objetos = st.tabs(abas_disponiveis)

# CORREÇÃO 4: Todas as abas usam elif de forma consistente dentro do loop
for nome_aba, aba_objeto in zip(abas_disponiveis, abas_objetos):

    # ----------------------------------------------------
    # ABA: PAINEL DA TV (MURAL OPERACIONAL DA PRODUÇÃO)
    # ----------------------------------------------------
    if nome_aba == "PAINEL DA TV (Chão de Fábrica)":
        import calendar as py_calendar

        with aba_objeto:
            st.header("📆 Mural de Metas da Produção - Passold")
            st.markdown("Navegue pelos meses para ver os dias programados. Clique em qualquer dia com OPs para ver a lista e dar baixa!")

            obras_producao = ["TODAS AS OBRAS"] + list(df_banco_micro['Obra_Vinculada'].dropna().unique()) if not df_banco_micro.empty else ["TODAS AS OBRAS"]
            obra_tv = st.selectbox("Filtrar Painel da TV por Obra:", obras_producao, key="sb_obra_tv")

            if not df_banco_micro.empty:
                df_chapas_base = df_banco_micro[df_banco_micro['Status_Item'] == "Liberado para Fábrica"].copy()

                if obra_tv == "TODAS AS OBRAS":
                    df_chapas_obra = df_chapas_base.copy()
                else:
                    df_chapas_obra = df_chapas_base[df_chapas_base['Obra_Vinculada'] == obra_tv].copy()

                if not df_chapas_obra.empty:
                    df_chapas_obra['Data_Producao_Programada'] = pd.to_datetime(df_chapas_obra['Data_Producao_Programada']).dt.date

                    if "prog_mes" not in st.session_state:
                        st.session_state.prog_mes = HOJE_PROJETO.month
                    if "prog_ano" not in st.session_state:
                        st.session_state.prog_ano = HOJE_PROJETO.year

                    col_nav1, col_nav2, col_nav3 = st.columns([1, 2, 1])
                    with col_nav1:
                        if st.button("⬅️ Mês Anterior", use_container_width=True, key="btn_mes_ant"):
                            st.session_state.prog_mes -= 1
                            if st.session_state.prog_mes == 0:
                                st.session_state.prog_mes = 12
                                st.session_state.prog_ano -= 1
                            st.rerun()

                    with col_nav2:
                        meses_nomes = ["", "Janeiro", "Fevereiro", "Março", "Abril", "Maio", "Junho", "Julho", "Agosto", "Setembro", "Outubro", "Novembro", "Dezembro"]
                        st.markdown(f"<h3 style='text-align: center; color: #1E3A8A; margin:0;'>📅 {meses_nomes[st.session_state.prog_mes]} / {st.session_state.prog_ano}</h3>", unsafe_allow_html=True)

                    with col_nav3:
                        if st.button("Próximo Mês ➡️", use_container_width=True, key="btn_mes_prox"):
                            st.session_state.prog_mes += 1
                            if st.session_state.prog_mes == 13:
                                st.session_state.prog_mes = 1
                                st.session_state.prog_ano += 1
                            st.rerun()

                    st.markdown("---")

                    cal = py_calendar.Calendar(firstweekday=6)
                    semanas_mes = cal.monthdatescalendar(st.session_state.prog_ano, st.session_state.prog_mes)

                    dias_da_semana_nomes = ["Dom", "Seg", "Ter", "Qua", "Qui", "Sex", "Sáb"]
                    colunas_headers = st.columns(7)
                    for idx, nome_d in enumerate(dias_da_semana_nomes):
                        colunas_headers[idx].markdown(f"<p style='text-align:center; font-weight:bold; color:#475569;'>{nome_d}</p>", unsafe_allow_html=True)

                    for semana in semanas_mes:
                        colunas_dias = st.columns(7)
                        for idx_dia, data_dia in enumerate(semana):
                            with colunas_dias[idx_dia]:
                                do_mes_corrente = (data_dia.month == st.session_state.prog_mes)

                                if do_mes_corrente:
                                    df_dia_ops = df_chapas_obra[df_chapas_obra['Data_Producao_Programada'] == data_dia]
                                    total_ops_dia = len(df_dia_ops)

                                    eh_hoje = (data_dia == HOJE_PROJETO.date())
                                    bg_cor = "#EFF6FF" if eh_hoje else "#F8FAFC"
                                    borda_cor = "#3B82F6" if eh_hoje else "#E2E8F0"

                                    if total_ops_dia > 0:
                                        if st.button(f"{data_dia.day}\n({total_ops_dia} OPs)", key=f"btn_dia_{data_dia}", use_container_width=True):
                                            st.session_state.dia_clicado_tv = data_dia
                                    else:
                                        texto_card = f"<span style='color:#94A3B8;'>{data_dia.day}</span><br><span style='color:#94A3B8; font-size:11px;'>Vazio</span><br><br>"
                                        st.markdown(f"""
                                            <div style="background-color: {bg_cor}; border: 1px solid {borda_cor}; padding: 5px; border-radius: 6px; text-align: center; height: 75px;">
                                                {texto_card}
                                            </div>
                                        """, unsafe_allow_html=True)
                                else:
                                    st.markdown('<div style="height: 75px;"></div>', unsafe_allow_html=True)

                    st.markdown("---")

                    if "dia_clicado_tv" not in st.session_state:
                        st.session_state.dia_clicado_tv = HOJE_PROJETO.date()

                    st.subheader(f"🔍 Ordens de Trabalho para o dia: {st.session_state.dia_clicado_tv.strftime('%d/%m/%Y')}")

                    df_detalhe_dia = df_chapas_obra[df_chapas_obra['Data_Producao_Programada'] == st.session_state.dia_clicado_tv]

                    if df_detalhe_dia.empty:
                        st.info("💡 Toque em um dia marcado com as OPs no calendário acima para gerenciar a produção.")
                    else:
                        for idx, row in df_detalhe_dia.iterrows():
                            id_item = row['id']
                            op_txt = row['Num_OP'] if row['Num_OP'] else "S/ OP"
                            nome_da_obra = row['Obra_Vinculada']

                            with st.container(border=True):
                                col_dados, col_acao = st.columns([4, 1])
                                with col_dados:
                                    st.markdown(f"""
                                        <span style="background-color: #FFEDD5; color: #EA580C; padding: 3px 8px; border-radius: 4px; font-weight: bold; font-size: 13px; margin-right: 8px;">🏗️ OBRA: {nome_da_obra}</span>
                                        <span style="background-color: #E0E7FF; color: #4338CA; padding: 3px 8px; border-radius: 4px; font-weight: bold; font-size: 13px;">Lote Técnico: {row['Cod_Lote']}</span>
                                    """, unsafe_allow_html=True)

                                    st.markdown(f"#### 📦 OP: **{op_txt}**")
                                    st.markdown(f"**Material:** {row['Tipo_Material']} | **Meta do Dia:** `{int(row['Qtd_Caixas'])} caixas` ({row['M2_Item']:.2f} m²)")
                                    st.caption(f"Pavimentos atendidos: {row['Romaneio_Chapas']} | Prazo Final de Engenharia: {pd.to_datetime(row['Data_Limite_Obra']).strftime('%d/%m/%Y')}")

                                with col_acao:
                                    st.write("")
                                    if st.button("✅ PRONTO", key=f"baixa_mural_{id_item}", type="primary", use_container_width=True):
                                        conn = conectar_banco()
                                        cursor = conn.cursor()
                                        cursor.execute("UPDATE itens_detalhado SET Status_Item = 'Concluído' WHERE id = ?", (id_item,))
                                        conn.commit()
                                        conn.close()
                                        st.toast(f"Boa! Lote {row['Cod_Lote']} da obra {nome_da_obra} concluído! 🚀")
                                        time.sleep(0.3)
                                        st.rerun()
                else:
                    st.success("🙌 Sem ordens liberadas para os filtros selecionados!")
            else:
                st.info("Nenhum lote técnico importado ou liberado no sistema ainda.")

    # ----------------------------------------------------
    # ABA: LIBERAR OPS DA SEMANA
    # ----------------------------------------------------
    elif nome_aba == "Liberar OPs da Semana":
        with aba_objeto:
            st.header("Gerenciador de Ordens de Produção Semanais")

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
                        prefixo_op = st.text_input("Prefixo da OP:", value=f"OP-{datetime.now().strftime('%Y')}-")

                    if st.button("Liberar Itens Selecionados para a TV da Fábrica"):
                        if ids_selecionados:
                            conn = conectar_banco()
                            cursor = conn.cursor()

                            for index, item_id in enumerate(ids_selecionados):
                                num_op_gerada = f"{prefixo_op}{str(item_id).zfill(3)}"
                                cursor.execute("""
                                    UPDATE itens_detalhado
                                    SET Status_Item = 'Liberado para Fábrica', Num_OP = ?
                                    WHERE id = ?
                                """, (num_op_gerada, item_id))

                            conn.commit()
                            conn.close()
                            st.toast("Ordens de Produção liberadas com sucesso!", icon="✅")
                            time.sleep(0.5)
                            st.rerun()
                else:
                    st.success("Todos os lotes cadastrados já foram liberados.")
            else:
                st.info("Nenhum lote pendente encontrado.")

    # ----------------------------------------------------
    # ABA: VISÃO MACRO (DIRETORIA)
    # ----------------------------------------------------
    elif nome_aba == "Visão Macro (Diretoria)":
        with aba_objeto:
            st.header("📊 Dashboard Executivo e Cronograma Macro")

            obras_disponiveis = ["TODAS AS OBRAS"] + list(df_banco_micro['Obra_Vinculada'].dropna().unique()) if not df_banco_micro.empty else ["TODAS AS OBRAS"]
            obra_exec = st.selectbox("Filtrar Painel Executivo por Obra:", obras_disponiveis, key="sb_obra_exec")

            if obra_exec == "TODAS AS OBRAS":
                df_diretoria = df_banco_micro.copy()
            else:
                df_diretoria = df_banco_micro[df_banco_micro['Obra_Vinculada'] == obra_exec].copy()

            if not df_diretoria.empty:
                kpi_m2 = df_diretoria['M2_Item'].sum()
                kpi_frentes = df_diretoria['EDT_Vinculado'].nunique()

                df_diretoria['Data_Limite_Obra'] = pd.to_datetime(df_diretoria['Data_Limite_Obra'])
                data_max = df_diretoria['Data_Limite_Obra'].max().strftime('%d/%m/%Y') if not df_diretoria['Data_Limite_Obra'].isna().all() else "N/A"

                c1, c2, c3 = st.columns(3)
                with c1:
                    st.metric("Metragem Total no Filtro", f"{kpi_m2:,.2f} m²")
                with c2:
                    st.metric("Subdivisões Exibidas", f"{kpi_frentes} frentes")
                with c3:
                    st.metric("Prazo de Entrega Mais Distante", data_max)

                st.markdown("---")

                st.subheader("📈 Planejamento de Carga Semanal da Produção")
                st.markdown("Veja abaixo a distribuição exata do volume que está liberado para a fábrica por semanas e obras específicas:")

                df_liberados = df_diretoria[df_diretoria['Status_Item'].isin(["Liberado para Fábrica", "Produção", "Concluído"])].copy()

                if not df_liberados.empty:
                    df_liberados['Data_Producao_Programada'] = pd.to_datetime(df_liberados['Data_Producao_Programada'])
                    df_liberados['Ano_Semana'] = df_liberados['Data_Producao_Programada'].dt.isocalendar().year
                    df_liberados['Num_Semana'] = df_liberados['Data_Producao_Programada'].dt.isocalendar().week

                    def formatar_periodo_semana(row):
                        try:
                            segunda = pd.to_datetime(f"{int(row['Ano_Semana'])}-W{int(row['Num_Semana'])}-1", format="%G-W%V-%u")
                            domingo = segunda + timedelta(days=6)
                            return f"Semana {int(row['Num_Semana']):02d} ({segunda.strftime('%d/%m')} até {domingo.strftime('%d/%m/%Y')})"
                        except:
                            return f"Semana {row['Num_Semana']}"

                    df_liberados['Período Semanal'] = df_liberados.apply(formatar_periodo_semana, axis=1)

                    df_semanal_resumo = df_liberados.groupby(['Ano_Semana', 'Num_Semana', 'Período Semanal', 'Obra_Vinculada']).agg({
                        'id': 'count',
                        'Qtd_Caixas': 'sum',
                        'M2_Item': 'sum',
                        'Status_Item': lambda x: f"{((x == 'Concluído').sum() / len(x)) * 100:.0f}% concluído"
                    }).reset_index()

                    df_semanal_resumo = df_semanal_resumo.sort_values(by=['Ano_Semana', 'Num_Semana', 'Obra_Vinculada'])
                    df_semanal_resumo.columns = ['Ano', 'Semana Nº', 'Período Comercial', 'Obra', 'Qtd Lotes técnicos', 'Total Caixas (cx)', 'Volume Total (m²)', 'Status de Evolução']

                    st.dataframe(
                        df_semanal_resumo[['Período Comercial', 'Obra', 'Qtd Lotes técnicos', 'Total Caixas (cx)', 'Volume Total (m²)', 'Status de Evolução']],
                        hide_index=True,
                        use_container_width=True
                    )
                else:
                    st.warning("⚠️ Nenhuma Ordem de Produção foi liberada para a fábrica ainda nesta obra, portanto não há carga semanal cadastrada.")

                st.subheader("📊 Linha do Tempo de Execução (Gantt)")

                df_gantt = df_diretoria.groupby(['Obra_Vinculada', 'EDT_Vinculado', 'Romaneio_Chapas']).agg({
                    'Data_Producao_Programada': 'min',
                    'Data_Limite_Obra': 'max',
                    'M2_Item': 'sum'
                }).reset_index()

                df_gantt['Data_Producao_Programada'] = pd.to_datetime(df_gantt['Data_Producao_Programada'])
                df_gantt['Data_Limite_Obra'] = pd.to_datetime(df_gantt['Data_Limite_Obra'])
                df_gantt = df_gantt.dropna(subset=['Data_Producao_Programada', 'Data_Limite_Obra'])

                if not df_gantt.empty:
                    fig = px.timeline(
                        df_gantt,
                        x_start="Data_Producao_Programada",
                        x_end="Data_Limite_Obra",
                        y="EDT_Vinculado",
                        color="Obra_Vinculada",
                        hover_data=["Romaneio_Chapas", "M2_Item"],
                        labels={"EDT_Vinculado": "Frente de Trabalho / Balancim"},
                        title="Período Estimado Ocupação de Fábrica vs Entrega"
                    )
                    fig.update_yaxes(autorange="reversed")
                    fig.update_layout(height=400, margin=dict(l=20, r=20, t=40, b=20))
                    st.plotly_chart(fig, use_container_width=True)
                else:
                    st.info("Insira datas válidas de fabricação e limite de obra para plotar a linha do tempo.")
            else:
                st.info("Nenhum dado encontrado para gerar a visão macro.")

    # ----------------------------------------------------
    # ABA: VINCULAR DATAS MATERIAIS
    # ----------------------------------------------------
    elif nome_aba == "Vincular Datas (Materiais)":
        with aba_objeto:
            st.header("Inteligência Temporal: Fatiamento e Edição de Lotes")

            if 'lote_salvo_sucesso' in st.session_state and st.session_state.lote_salvo_sucesso:
                st.success("Sucesso! Remessa gerada e salva como Pendente.")
                st.session_state.lote_salvo_sucesso = False

            if obra_selecionada and not df_macro_filtrado.empty:
                opcoes_edt = []
                status_eng_map = {}

                for idx, row in df_macro_filtrado.iterrows():
                    sub_txt = f" [{row['Subdivisao']}]" if 'Subdivisao' in row and row['Subdivisao'] else ""
                    label_edt = f"{row['EDT']} - {row['Tarefa']}{sub_txt}"
                    opcoes_edt.append(label_edt)
                    # CORREÇÃO 3: Chave corrigida de 'Status_Engineharia' para 'Status_Engenharia'
                    status_eng_map[row['EDT']] = row.get('Status_Engenharia', '🔴 Aguardando Medição In Loco')

                st.markdown("### 🛠️ Fatiar Nova Remessa de Materiais")
                with st.form("form_injecao_datas_flexivel"):
                    col_in1, col_in2, col_in3 = st.columns(3)
                    with col_in1:
                        edt_selecionado = st.selectbox("Pertence a qual frente macro?", opcoes_edt)
                        edt_puro = edt_selecionado.split(" ")[0]
                        cod_lote = st.text_input("Identificação desta Remessa:")
                    with col_in2:
                        data_necessidade_obra = st.date_input("Data Limite de Despacho:", value=datetime(2026, 7, 10).date(), format="DD/MM/YYYY")
                        recuo_dias_base = st.number_input("Dias de Pulmão (Segurança):", min_value=0, value=2)
                    with col_in3:
                        dias_uteis_fabricacao = st.number_input(
                            "Dias Úteis de Produção Estimados:",
                            min_value=1,
                            value=20
                        )
                        dificuldade_lote = st.selectbox(
                            "Nível de Complexidade:",
                            [1, 2, 3, 4, 5],
                            index=3
                        )

                        dt_limite_preview = datetime.combine(data_necessidade_obra, datetime.min.time())
                        dia_fim_preview = dt_limite_preview - timedelta(days=int(recuo_dias_base))
                        dias_engenharia = 3
                        prazo_engenharia = (
                            dia_fim_preview
                            - timedelta(days=int(dias_uteis_fabricacao))
                            - timedelta(days=dias_engenharia)
                        )

                        st.info(
                            f"📐 Engenharia deve liberar até:\n\n"
                            f"**{prazo_engenharia.strftime('%d/%m/%Y')}**"
                        )

                    st.markdown("---")
                    col_dados1, col_dados2 = st.columns(2)
                    with col_dados1:
                        txt_pavimentos = st.text_area("Pavimentos Destino:", value="Pav 39 ao 43")
                        especificacao = st.text_input("Material / Chapa do Lote:", value="ACM BRANCO")
                    with col_dados2:
                        total_cx = st.number_input("Quantidade de Caixas:", min_value=1, value=50)
                        total_m2 = st.number_input("Metragem Quadrada (m²):", min_value=0.1, value=113.27)

                    status_da_frente = status_eng_map.get(edt_puro, "🔴 Aguardando Medição In Loco")
                    if "🟢" not in status_da_frente:
                        st.warning(f"⚠️ Atenção Joice: A engenharia marcou essa frente como `{status_da_frente}`. Tem certeza que deseja fatiar agora?")

                    btn_calcular_tudo = st.form_submit_button("Distribuir Remessa Realista")

                    if btn_calcular_tudo:
                        if not cod_lote.strip():
                            st.error("Por favor, digite uma identificação de lote.")
                        else:
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
                                # CORREÇÃO 2: Fase produtiva com lógica correta (primeiro corte, depois montagem)
                                fase_atual = "CORTE E USINAGEM" if dias_uteis_contados <= (int(dias_uteis_fabricacao) / 2) else "MONTAGEM FINAL"

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
                            st.session_state.lote_salvo_sucesso = True
                            st.rerun()

                st.markdown("---")
                st.markdown("### 📝 Lotes Gerados (Clique duplo para editar qualquer campo)")
                st.caption("Qualquer alteração feita na tabela abaixo é salva automaticamente no banco de dados.")

                df_micro_editar = carregar_micro()
                if not df_micro_editar.empty:
                    df_obra_atual = df_micro_editar[df_micro_editar['Obra_Vinculada'] == obra_selecionada].copy()

                    if not df_obra_atual.empty:
                        df_obra_atual['Data_Producao_Programada'] = df_obra_atual['Data_Producao_Programada'].dt.strftime('%Y-%m-%d')
                        df_obra_atual['Data_Limite_Obra'] = df_obra_atual['Data_Limite_Obra'].dt.strftime('%Y-%m-%d')

                        df_editado = st.data_editor(
                            df_obra_atual,
                            key="editor_lotes_reais",
                            hide_index=True,
                            use_container_width=True,
                            disabled=["id", "Obra_Vinculada", "Num_OP"]
                        )

                        if not df_editado.equals(df_obra_atual):
                            conn = conectar_banco()
                            cursor = conn.cursor()

                            for idx, row in df_editado.iterrows():
                                cursor.execute("""
                                    UPDATE itens_detalhado
                                    SET Cod_Lote = ?, Tipo_Material = ?, Qtd_Caixas = ?, M2_Item = ?,
                                        Data_Producao_Programada = ?, Data_Limite_Obra = ?,
                                        Romaneio_Chapas = ?, Status_Item = ?, Dificuldade = ?, Fase_Produtiva = ?
                                    WHERE id = ?
                                """, (
                                    row['Cod_Lote'], row['Tipo_Material'], int(row['Qtd_Caixas']), float(row['M2_Item']),
                                    row['Data_Producao_Programada'], row['Data_Limite_Obra'],
                                    row['Romaneio_Chapas'], row['Status_Item'], int(row['Dificuldade']), row['Fase_Produtiva'],
                                    int(row['id'])
                                ))
                            conn.commit()
                            conn.close()
                            st.toast("Alterações salvas com sucesso!", icon="💾")
                            time.sleep(0.3)
                            st.rerun()

                        st.markdown("#### 🗑️ Remover Linha Incorreta")
                        lotes_para_deletar = df_obra_atual['Cod_Lote'].unique().tolist()
                        lote_alvo_del = st.selectbox("Selecione o Código do Lote para remover completamente:", lotes_para_deletar)

                        if st.button(f"Excluir Lote {lote_alvo_del} da Obra"):
                            conn = conectar_banco()
                            cursor = conn.cursor()
                            cursor.execute("DELETE FROM itens_detalhado WHERE Obra_Vinculada = ? AND Cod_Lote = ?", (obra_selecionada, lote_alvo_del))
                            conn.commit()
                            conn.close()
                            st.toast(f"Lote {lote_alvo_del} removido!", icon="🗑️")
                            time.sleep(0.5)
                            st.rerun()
                    else:
                        st.info("Nenhum lote fatiado para esta obra ainda.")
                else:
                    st.info("Nenhum lote técnico encontrado no banco de dados.")

    # ----------------------------------------------------
    # ABA: CADASTRAR NOVA OBRA
    # ----------------------------------------------------
    elif nome_aba == "Cadastrar Nova Obra":
        with aba_objeto:
            st.header("Cadastrar Nova Obra e Frentes de Trabalho Macro")

            if 'mem_obra' not in st.session_state: st.session_state.mem_obra = ""
            if 'mem_escopo' not in st.session_state: st.session_state.mem_escopo = "ACM"
            if 'mem_frente_macro' not in st.session_state: st.session_state.mem_frente_macro = ""
            if 'mem_tarefa' not in st.session_state: st.session_state.mem_tarefa = ""
            if 'mem_dt_inicio' not in st.session_state: st.session_state.mem_dt_inicio = datetime.now().date()
            if 'mem_dt_fim' not in st.session_state: st.session_state.mem_dt_fim = (datetime.now() + timedelta(days=30)).date()

            with st.form("form_nova_obra_sequencial"):
                nome_nova_obra = st.text_input("Nome Geral da Obra:", value=st.session_state.mem_obra).upper()

                col_o1, col_o2 = st.columns(2)
                with col_o1:
                    tipo_escopo_novo = st.selectbox("Tipo de Escopo Fachada:", ["ACM", "Vidro/Esquadria"], index=0 if st.session_state.mem_escopo == "ACM" else 1)
                    etapa_macro_nova = st.text_input("Frente Macro / Pavimentos:", value=st.session_state.mem_frente_macro)
                    nome_tarefa_nova = st.text_input("Nome Detalhado da Tarefa:", value=st.session_state.mem_tarefa)
                with col_o2:
                    edt_nova_obra = st.text_input("Código EDT ÚNICO:", value="")
                    subdivisao_nova = st.text_input("Subdivisão / Balancim:", value="").upper()
                    m2_total_novo = st.number_input("Metragem Quadrada Pactuada (m²):", min_value=0.1, value=100.0)

                col_d1, col_d2 = st.columns(2)
                with col_d1:
                    data_inicio_nova = st.date_input("Data Alvo Início Instalação:", value=st.session_state.mem_dt_inicio, format="DD/MM/YYYY")
                with col_d2:
                    data_fim_nova = st.date_input("Prazo Máximo Balancim Pronto:", value=st.session_state.mem_dt_fim, format="DD/MM/YYYY")

                btn_salvar_obra = st.form_submit_button("Registrar Subdivisão")

                if btn_salvar_obra:
                    if not nome_nova_obra.strip() or not edt_nova_obra.strip() or not nome_tarefa_nova.strip() or not subdivisao_nova.strip():
                        st.error("Preencha todos os campos obrigatórios.")
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
                                INSERT INTO cronograma_macro (Obra, EDT, Tipo_Escopo, Etapa_Macro, Subdivisao, Tarefa, M2_Total_Tarefa, Inicio_Previsto, Termino_Obra, Status, Status_Engenharia)
                                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                            """, (nome_nova_obra, edt_nova_obra, tipo_escopo_novo, etapa_macro_nova, subdivisao_nova, nome_tarefa_nova, float(m2_total_novo), data_inicio_nova.strftime('%Y-%m-%d'), data_fim_nova.strftime('%Y-%m-%d'), "Pendente", "🔴 Aguardando Medição In Loco"))
                            conn.commit()
                            st.toast("Frente registrada com sucesso!", icon="🚀")
                            time.sleep(0.4)
                            st.rerun()
                        except sqlite3.IntegrityError:
                            st.error(f"O Código EDT '{edt_nova_obra}' já existe.")
                        finally:
                            conn.close()

    # ----------------------------------------------------
    # ABA: PAINEL TÉCNICO DA ENGENHARIA
    # ----------------------------------------------------
    elif nome_aba == "Painel Técnico da Engenharia":
        with aba_objeto:
            st.header("🏗️ Painel Técnico da Engenharia — Central de Gestão de Frentes")
            st.caption(f"Referência de data do sistema: {HOJE_PROJETO.strftime('%d/%m/%Y')} | Obra selecionada: **{obra_selecionada or 'Nenhuma'}**")

            # ================================================================
            # FUNÇÃO PURA: Cálculo do prazo da engenharia
            # Isolada aqui para fácil reutilização futura e persistência em BD
            # ================================================================
            def calcular_prazo_engenharia(data_limite_obra, dias_producao, dias_pulmao, margem_eng=3):
                """
                Calcula a data limite para a Engenharia entregar os desenhos.
                Parâmetros:
                    data_limite_obra : datetime — data de entrega final na obra
                    dias_producao    : int      — dias úteis estimados de fabricação
                    dias_pulmao      : int      — dias de segurança/buffer
                    margem_eng       : int      — margem técnica fixa da engenharia (padrão: 3)
                Retorna: datetime
                """
                return data_limite_obra - timedelta(days=int(dias_pulmao) + int(dias_producao) + int(margem_eng))

            # ================================================================
            # FUNÇÃO AUXILIAR: Calcular prazo a partir dos lotes micro da frente
            # Busca o lote mais restritivo (menor data de produção programada)
            # vinculado à frente (EDT), extrai dias de produção e pulmão reais
            # ================================================================
            def obter_prazo_engenharia_da_frente(edt, df_micro):
                """
                Tenta derivar o prazo da engenharia a partir dos lotes já fatiados
                para a frente. Se não houver lotes, retorna None.
                """
                if df_micro.empty:
                    return None
                lotes_frente = df_micro[df_micro['EDT_Vinculado'] == edt].copy()
                if lotes_frente.empty:
                    return None

                lotes_frente['Data_Producao_Programada'] = pd.to_datetime(lotes_frente['Data_Producao_Programada'])
                lotes_frente['Data_Limite_Obra'] = pd.to_datetime(lotes_frente['Data_Limite_Obra'])

                data_limite = lotes_frente['Data_Limite_Obra'].max()
                data_inicio_prod = lotes_frente['Data_Producao_Programada'].min()

                # Dias de produção = diferença em dias úteis entre início e limite
                dias_producao_est = max(1, (data_limite - data_inicio_prod).days)
                dias_pulmao_est = 2  # padrão do sistema

                return calcular_prazo_engenharia(data_limite, dias_producao_est, dias_pulmao_est)

            # ================================================================
            # FUNÇÃO AUXILIAR: Ícone e texto de situação com base nos dias restantes
            # ================================================================
            def classificar_situacao(dias_restantes, status_tecnico):
                STATUS_LIBERADO = "🟢 Desenhos Liberados para o PCP"
                if status_tecnico == STATUS_LIBERADO:
                    return "concluido", "✅ Liberado para o PCP", None
                if dias_restantes is None:
                    return "sem_prazo", "⚪ Sem prazo definido", None
                if dias_restantes < 0:
                    return "vencido", f"🔴 VENCIDO há {abs(int(dias_restantes))} dias", abs(int(dias_restantes))
                if dias_restantes <= 7:
                    return "critico", f"🟡 Crítico — faltam {int(dias_restantes)} dias", int(dias_restantes)
                return "ok", f"🟢 Dentro do prazo ({int(dias_restantes)} dias)", int(dias_restantes)

            # ================================================================
            # ESTADOS TÉCNICOS DISPONÍVEIS (máquina de estados)
            # ================================================================
            ESTADOS_TECNICOS = [
                "🔴 Aguardando Medição In Loco",
                "🟡 Medição Realizada — Em Desenho",
                "🔵 Desenho em Revisão Interna",
                "🟢 Desenhos Liberados para o PCP",
                "⚪ Arquivado / Concluído",
            ]

            # ================================================================
            # PRÉ-PROCESSAMENTO: montar lista enriquecida de frentes
            # ================================================================
            frentes_processadas = []

            if not df_macro_filtrado.empty:
                for _, row in df_macro_filtrado.iterrows():
                    prazo_eng = obter_prazo_engenharia_da_frente(row['EDT'], df_banco_micro)
                    dias_rest = (prazo_eng - HOJE_PROJETO).days if prazo_eng else None
                    situacao_key, situacao_txt, dias_num = classificar_situacao(
                        dias_rest,
                        row.get('Status_Engenharia', ESTADOS_TECNICOS[0])
                    )
                    frentes_processadas.append({
                        "id": row['id'],
                        "edt": row['EDT'],
                        "tarefa": row['Tarefa'],
                        "subdivisao": row.get('Subdivisao', ''),
                        "tipo_escopo": row.get('Tipo_Escopo', ''),
                        "inicio_previsto": row['Inicio_Previsto'],
                        "termino_obra": row['Termino_Obra'],
                        "m2": row.get('M2_Total_Tarefa', 0.0),
                        "prazo_eng": prazo_eng,
                        "dias_restantes": dias_rest,
                        "situacao_key": situacao_key,
                        "situacao_txt": situacao_txt,
                        "dias_num": dias_num,
                        "status_tecnico": row.get('Status_Engenharia', ESTADOS_TECNICOS[0]),
                    })

            # Separar críticas: vencidas ou com ≤ 7 dias E não liberadas
            frentes_criticas = [
                f for f in frentes_processadas
                if f['situacao_key'] in ('critico', 'vencido')
            ]

            # ================================================================
            # EXPANDER 1 — 🚨 FRENTES CRÍTICAS  (sempre aberto)
            # ================================================================
            label_criticas = f"🚨 Frentes Críticas — {len(frentes_criticas)} alerta(s)"
            with st.expander(label_criticas, expanded=True):

                if not frentes_criticas:
                    st.success("✅ Nenhuma frente crítica no momento. Tudo dentro do prazo!")
                else:
                    st.caption("Frentes com prazo vencido ou com menos de 7 dias para entrega dos desenhos ao PCP.")
                    st.markdown("---")

                    for frente in sorted(frentes_criticas, key=lambda x: (x['dias_restantes'] or 0)):
                        with st.container(border=True):
                            col_id, col_contador = st.columns([7, 3])

                            with col_id:
                                # Título da frente
                                sub_txt = f" · {frente['subdivisao']}" if frente['subdivisao'] else ""
                                st.markdown(f"### {frente['tarefa']}{sub_txt}")

                                col_meta1, col_meta2 = st.columns(2)
                                with col_meta1:
                                    st.write(f"📌 **EDT:** `{frente['edt']}`")
                                    st.write(f"📅 **Início instalação:** {frente['inicio_previsto'].strftime('%d/%m/%Y')}")
                                with col_meta2:
                                    prazo_txt = frente['prazo_eng'].strftime('%d/%m/%Y') if frente['prazo_eng'] else "Não calculado"
                                    st.write(f"📐 **Prazo PCP:** `{prazo_txt}`")
                                    st.write(f"📊 **Metragem:** {frente['m2']:,.2f} m²")

                                # Status técnico atual
                                st.write(f"🔧 **Status técnico:** {frente['status_tecnico']}")

                            with col_contador:
                                # Contador de dias — elemento visual dominante
                                if frente['situacao_key'] == 'vencido':
                                    st.error(f"⏰ VENCIDO\n\n**{frente['dias_num']} dias**\natraso")
                                else:
                                    st.warning(f"⏳ FALTAM\n\n**{frente['dias_num']} dias**\npara entrega")

                            st.markdown("---")

                            # Ações rápidas no card crítico
                            col_acao1, col_acao2 = st.columns(2)
                            with col_acao1:
                                chave_sel = f"eng_crit_status_{frente['id']}"
                                idx_atual = ESTADOS_TECNICOS.index(frente['status_tecnico']) if frente['status_tecnico'] in ESTADOS_TECNICOS else 0
                                novo_status_crit = st.selectbox(
                                    "Atualizar status técnico:",
                                    ESTADOS_TECNICOS,
                                    index=idx_atual,
                                    key=chave_sel
                                )
                            with col_acao2:
                                st.write("")
                                st.write("")
                                if st.button("💾 Salvar Status", key=f"eng_crit_save_{frente['id']}", use_container_width=True):
                                    atualizar_status_engenharia(frente['id'], novo_status_crit)
                                    st.toast(f"Status de '{frente['tarefa']}' atualizado!", icon="✅")
                                    time.sleep(0.3)
                                    st.rerun()

            # ================================================================
            # EXPANDER 2 — 📋 TODAS AS FRENTES  (fechado por padrão)
            # ================================================================
            with st.expander(f"📋 Todas as Frentes da Engenharia — {len(frentes_processadas)} frente(s)", expanded=False):

                if not frentes_processadas:
                    st.info("Nenhuma frente cadastrada para esta obra.")
                else:
                    # Filtros acima da lista
                    col_f1, col_f2 = st.columns([3, 2])
                    with col_f1:
                        filtro_status = st.selectbox(
                            "Filtrar por status técnico:",
                            ["Todos os status"] + ESTADOS_TECNICOS,
                            key="eng_filtro_status"
                        )
                    with col_f2:
                        filtro_situacao = st.radio(
                            "Filtrar por situação:",
                            ["Todas", "Somente críticas", "Já liberadas"],
                            horizontal=True,
                            key="eng_filtro_situacao"
                        )

                    # Aplicar filtros
                    frentes_exibir = frentes_processadas.copy()
                    if filtro_status != "Todos os status":
                        frentes_exibir = [f for f in frentes_exibir if f['status_tecnico'] == filtro_status]
                    if filtro_situacao == "Somente críticas":
                        frentes_exibir = [f for f in frentes_exibir if f['situacao_key'] in ('critico', 'vencido')]
                    elif filtro_situacao == "Já liberadas":
                        frentes_exibir = [f for f in frentes_exibir if f['situacao_key'] == 'concluido']

                    if not frentes_exibir:
                        st.info("Nenhuma frente corresponde aos filtros selecionados.")
                    else:
                        st.markdown(f"**{len(frentes_exibir)} frente(s) exibida(s)**")
                        st.markdown("---")

                        for frente in frentes_exibir:
                            with st.container(border=True):
                                col_ident, col_datas, col_acao = st.columns([5, 3, 2])

                                with col_ident:
                                    sub_txt = f" · *{frente['subdivisao']}*" if frente['subdivisao'] else ""
                                    st.markdown(f"**{frente['tarefa']}**{sub_txt}")
                                    st.caption(f"EDT: {frente['edt']} | {frente['tipo_escopo']} | {frente['m2']:,.2f} m²")
                                    st.write(frente['status_tecnico'])

                                with col_datas:
                                    st.caption("Início instalação")
                                    st.write(frente['inicio_previsto'].strftime('%d/%m/%Y'))
                                    st.caption("Prazo PCP p/ desenhos")
                                    prazo_txt = frente['prazo_eng'].strftime('%d/%m/%Y') if frente['prazo_eng'] else "—"
                                    st.write(f"`{prazo_txt}`")

                                with col_acao:
                                    # Badge de situação
                                    sk = frente['situacao_key']
                                    if sk == 'vencido':
                                        st.error(frente['situacao_txt'])
                                    elif sk == 'critico':
                                        st.warning(frente['situacao_txt'])
                                    elif sk == 'concluido':
                                        st.success(frente['situacao_txt'])
                                    elif sk == 'ok':
                                        st.success(frente['situacao_txt'])
                                    else:
                                        st.info(frente['situacao_txt'])

                                # Linha de atualização de status — inline
                                col_sel, col_btn = st.columns([4, 1])
                                with col_sel:
                                    idx_atual = ESTADOS_TECNICOS.index(frente['status_tecnico']) if frente['status_tecnico'] in ESTADOS_TECNICOS else 0
                                    novo_status_all = st.selectbox(
                                        "Atualizar status:",
                                        ESTADOS_TECNICOS,
                                        index=idx_atual,
                                        key=f"eng_all_status_{frente['id']}",
                                        label_visibility="collapsed"
                                    )
                                with col_btn:
                                    if st.button("💾", key=f"eng_all_save_{frente['id']}", use_container_width=True, help="Salvar status"):
                                        atualizar_status_engenharia(frente['id'], novo_status_all)
                                        st.toast(f"Status atualizado!", icon="✅")
                                        time.sleep(0.3)
                                        st.rerun()

            # ================================================================
            # EXPANDER 3 — 📝 SOLICITAÇÕES DE PRAZO  (fechado por padrão)
            # Arquitetura preparada para persistência futura:
            # Tabela sugerida: solicitacoes_prazo (id, edt, prazo_solicitado,
            #   justificativa, status, criado_por, criado_em, decidido_por, decidido_em)
            # ================================================================
            frentes_nao_liberadas = [
                f for f in frentes_processadas
                if f['situacao_key'] != 'concluido'
            ]
            pendentes_solicitacao = st.session_state.get('eng_solicitacoes_pendentes', [])
            label_sol = f"📝 Solicitações de Prazo" + (f" — {len(pendentes_solicitacao)} pendente(s)" if pendentes_solicitacao else "")

            with st.expander(label_sol, expanded=False):
                st.caption("Use esta seção para registrar pedidos de extensão de prazo ao PCP. Em breve com persistência no banco de dados.")

                # --- VISÃO ENGENHARIA: criar nova solicitação ---
                if setor in ["Engenharia", "Master"]:
                    st.markdown("#### ✍️ Nova Solicitação de Extensão de Prazo")

                    if not frentes_nao_liberadas:
                        st.success("Todas as frentes já estão liberadas. Nenhuma solicitação necessária.")
                    else:
                        col_sol1, col_sol2 = st.columns(2)
                        with col_sol1:
                            opcoes_frentes_sol = [f"{f['edt']} — {f['tarefa']}" for f in frentes_nao_liberadas]
                            frente_sol_sel = st.selectbox(
                                "Frente que precisa de extensão:",
                                opcoes_frentes_sol,
                                key="eng_sol_frente"
                            )
                            frente_sol_idx = opcoes_frentes_sol.index(frente_sol_sel)
                            frente_sol_obj = frentes_nao_liberadas[frente_sol_idx]

                            prazo_atual_txt = frente_sol_obj['prazo_eng'].strftime('%d/%m/%Y') if frente_sol_obj['prazo_eng'] else "Não definido"
                            st.info(f"Prazo atual do PCP: **{prazo_atual_txt}**")

                        with col_sol2:
                            novo_prazo_sol = st.date_input(
                                "Novo prazo solicitado:",
                                value=(frente_sol_obj['prazo_eng'] + timedelta(days=7)).date() if frente_sol_obj['prazo_eng'] else HOJE_PROJETO.date(),
                                format="DD/MM/YYYY",
                                key="eng_sol_novo_prazo"
                            )
                            justificativa_sol = st.text_area(
                                "Justificativa técnica:",
                                placeholder="Ex: Revisão de projeto estrutural pelo cliente, pendência de aprovação...",
                                key="eng_sol_justificativa"
                            )

                        if st.button("📤 Enviar Solicitação ao PCP", key="eng_sol_enviar", use_container_width=False):
                            if not justificativa_sol.strip():
                                st.error("Informe a justificativa técnica antes de enviar.")
                            else:
                                nova_sol = {
                                    "edt": frente_sol_obj['edt'],
                                    "tarefa": frente_sol_obj['tarefa'],
                                    "prazo_atual": prazo_atual_txt,
                                    "prazo_solicitado": novo_prazo_sol.strftime('%d/%m/%Y'),
                                    "justificativa": justificativa_sol.strip(),
                                    "criado_por": st.session_state.usuario_nome,
                                    "status": "⏳ Pendente de Aprovação",
                                }
                                lista_atual = st.session_state.get('eng_solicitacoes_pendentes', [])
                                lista_atual.append(nova_sol)
                                st.session_state['eng_solicitacoes_pendentes'] = lista_atual
                                st.success(f"Solicitação enviada para o PCP! O prazo atual permanece até aprovação.")
                                st.rerun()

                st.markdown("---")

                # --- VISÃO PCP/MASTER: aprovar ou rejeitar ---
                if setor in ["Master"]:
                    st.markdown("#### ✅ Decisão do PCP sobre Solicitações Recebidas")
                    lista_sol = st.session_state.get('eng_solicitacoes_pendentes', [])
                    pendentes = [s for s in lista_sol if s['status'] == "⏳ Pendente de Aprovação"]

                    if not pendentes:
                        st.info("Nenhuma solicitação pendente de decisão no momento.")
                    else:
                        for i, sol in enumerate(pendentes):
                            with st.container(border=True):
                                col_s1, col_s2 = st.columns([4, 2])
                                with col_s1:
                                    st.markdown(f"**{sol['tarefa']}** — EDT `{sol['edt']}`")
                                    st.write(f"Prazo atual: `{sol['prazo_atual']}` → Prazo pedido: `{sol['prazo_solicitado']}`")
                                    st.caption(f"Justificativa: *{sol['justificativa']}*")
                                    st.caption(f"Solicitado por: {sol['criado_por']}")
                                with col_s2:
                                    col_ap, col_rej = st.columns(2)
                                    with col_ap:
                                        if st.button("✅ Aprovar", key=f"sol_aprovar_{i}", use_container_width=True):
                                            st.session_state['eng_solicitacoes_pendentes'][
                                                lista_sol.index(sol)
                                            ]['status'] = "✅ Aprovado"
                                            st.toast("Solicitação aprovada!", icon="✅")
                                            st.rerun()
                                    with col_rej:
                                        if st.button("❌ Rejeitar", key=f"sol_rejeitar_{i}", use_container_width=True):
                                            st.session_state['eng_solicitacoes_pendentes'][
                                                lista_sol.index(sol)
                                            ]['status'] = "❌ Rejeitado"
                                            st.toast("Solicitação rejeitada.", icon="❌")
                                            st.rerun()

                # Histórico de decisões tomadas (aprovadas/rejeitadas)
                lista_sol_full = st.session_state.get('eng_solicitacoes_pendentes', [])
                historico = [s for s in lista_sol_full if s['status'] != "⏳ Pendente de Aprovação"]
                if historico:
                    st.markdown("#### 📂 Histórico desta Sessão")
                    for sol in historico:
                        st.caption(f"{sol['status']} | **{sol['tarefa']}** | Pedido: {sol['prazo_solicitado']} | Por: {sol['criado_por']}")

            # ================================================================
            # EXPANDER 4 — 🔍 CARGA DA FÁBRICA  (inalterado — já funcionava)
            # ================================================================
            with st.expander("🔍 Verificar Capacidade / Carga Ocupada da Fábrica Semanal", expanded=False):
                st.markdown("#### 📈 Carga Total Já Liberada para Produção por Semana:")
                st.caption("Consulte esta tabela antes de prometer novos prazos para garantir que a fábrica não seja sobrecarregada.")

                if not df_banco_micro.empty:
                    df_eng_ver = df_banco_micro[df_banco_micro['Status_Item'] == "Liberado para Fábrica"].copy()

                    if not df_eng_ver.empty:
                        df_eng_ver['Data_Producao_Programada'] = pd.to_datetime(df_eng_ver['Data_Producao_Programada'])
                        df_eng_ver['Ano_Semana'] = df_eng_ver['Data_Producao_Programada'].dt.isocalendar().year
                        df_eng_ver['Num_Semana'] = df_eng_ver['Data_Producao_Programada'].dt.isocalendar().week

                        def texto_semana_eng(row):
                            try:
                                seg = pd.to_datetime(f"{int(row['Ano_Semana'])}-W{int(row['Num_Semana'])}-1", format="%G-W%V-%u")
                                dom = seg + timedelta(days=6)
                                return f"Semana {int(row['Num_Semana']):02d} ({seg.strftime('%d/%m')} até {dom.strftime('%d/%m')})"
                            except:
                                return f"Semana {row['Num_Semana']}"

                        df_eng_ver['Período Semanal'] = df_eng_ver.apply(texto_semana_eng, axis=1)

                        resumo_eng = df_eng_ver.groupby(['Ano_Semana', 'Num_Semana', 'Período Semanal', 'Obra_Vinculada']).agg({
                            'id': 'count',
                            'Qtd_Caixas': 'sum',
                            'M2_Item': 'sum'
                        }).reset_index()

                        resumo_eng = resumo_eng.sort_values(by=['Ano_Semana', 'Num_Semana', 'Obra_Vinculada'])
                        resumo_eng.columns = ['Ano', 'Semana', 'Período Semanal', 'Obra', 'Qtd Lotes na Fábrica', 'Total Caixas (cx)', 'Metragem Alocada (m²)']

                        st.dataframe(
                            resumo_eng[['Período Semanal', 'Obra', 'Total Caixas (cx)', 'Metragem Alocada (m²)']],
                            hide_index=True,
                            use_container_width=True
                        )
                    else:
                        st.success("🌴 A fábrica está sem OPs pendentes no momento. Capacidade 100% livre!")
                else:
                    st.info("Sem dados de OPs disponíveis para consulta de carga.")

    # ----------------------------------------------------
    # ABA: CONFIGURAÇÕES DO SISTEMA
    # ----------------------------------------------------
    elif nome_aba == "Configurações do Sistema":
        with aba_objeto:
            st.header("⚙️ Painel de Controle Master e Segurança do PCP")

            st.markdown("### 👥 Gerenciador de Usuários da Passold")

            with st.expander("➕ Cadastrar Novo Usuário / Setor"):
                with st.form("form_novo_usuario"):
                    new_user = st.text_input("Username (Login único sem espaços):").lower().strip()
                    new_name = st.text_input("Nome do Colaborador:")
                    new_setor = st.selectbox("Setor / Perfil de Acesso:", ["Produção", "Engenharia", "Diretoria", "Master"])
                    new_password = st.text_input("Senha de Acesso:", type="password")
                    btn_add_user = st.form_submit_button("Salvar Usuário")

                    if btn_add_user:
                        if not new_user or not new_name or not new_password:
                            st.error("Preencha todos os campos do usuário!")
                        else:
                            conn = conectar_banco()
                            cursor = conn.cursor()
                            try:
                                cursor.execute("""
                                    INSERT INTO usuarios (usuario, nome, setor, senha)
                                    VALUES (?, ?, ?, ?)
                                """, (new_user, new_name, new_setor, new_password))
                                conn.commit()
                                st.success(f"Usuário {new_name} criado com sucesso!")
                                time.sleep(0.5)
                                st.rerun()
                            except sqlite3.IntegrityError:
                                # CORREÇÃO 1: 'East.error' corrigido para 'st.error'
                                st.error("Este nome de usuário (Login) já existe.")
                            finally:
                                conn.close()

            conn = conectar_banco()
            df_users = pd.read_sql_query("SELECT id, usuario as 'Login', nome as 'Nome', setor as 'Setor' FROM usuarios", conn)
            conn.close()

            st.markdown("**Usuários Cadastrados Ativos:**")
            st.dataframe(df_users, hide_index=True, use_container_width=True)

            if len(df_users) > 1:
                user_to_delete = st.selectbox("Selecione um usuário para remover do sistema:", df_users['Login'].tolist())
                if user_to_delete == "master":
                    st.caption("🔒 O usuário master original não pode ser deletado.")
                else:
                    if st.button(f"❌ Excluir usuário: {user_to_delete}"):
                        conn = conectar_banco()
                        cursor = conn.cursor()
                        cursor.execute("DELETE FROM usuarios WHERE usuario = ?", (user_to_delete,))
                        conn.commit()
                        conn.close()
                        st.toast("Usuário removido!", icon="🗑️")
                        time.sleep(0.5)
                        st.rerun()

            st.markdown("---")
            st.markdown("### 🚨 Limpeza Geral de Dados")
            st.warning("Atenção: Clicar no botão abaixo removerá permanentemente todas as obras e lotes salvos no momento.")
            if st.button("CONFIRMAR E LIMPAR BANCO DE DADOS COMPLETAMENTE"):
                resetar_banco_dados_completo()
                st.session_state.mem_obra = ""
                st.session_state.mem_frente_macro = ""
                st.session_state.mem_tarefa = ""
                st.toast("Banco de dados completamente resetado!", icon="🗑️")
                time.sleep(0.5)
                st.rerun()