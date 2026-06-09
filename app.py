import streamlit as st
import pandas as pd
import plotly.express as px
from datetime import datetime, timedelta
import sqlite3
import os
import time
import hashlib

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
    div.stButton > button:hover { background-color: #2563EB; color: white; }
    .login-container {
        max-width: 400px;
        margin: 0 auto;
        padding: 30px;
        background-color: #F8FAFC;
        border-radius: 10px;
        border: 1px solid #E2E8F0;
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
    @keyframes blinker { 50% { opacity: 0.5; } }
    </style>
""", unsafe_allow_html=True)

HOJE_PROJETO = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)

# ========================================================
# BANCO DE DADOS
# ========================================================
DB_NAME = "/data/passold_pcp.db" if os.path.exists("/data") else "passold_pcp.db"

def conectar_banco():
    return sqlite3.connect(DB_NAME)

def hash_senha(senha: str) -> str:
    """Retorna o SHA-256 da senha. Senhas nunca ficam em texto puro."""
    return hashlib.sha256(senha.encode()).hexdigest()

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
            Status TEXT DEFAULT 'Pendente',
            Status_Engenharia TEXT DEFAULT '🔴 Aguardando Medição In Loco',
            Prazo_Engenharia TEXT,
            Data_Limite_Despacho TEXT,
            Primeiro_Dia_Producao TEXT
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
            Status_Item TEXT DEFAULT 'Pendente',
            Dificuldade INTEGER DEFAULT 3,
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

    # Tabela de solicitações de prazo — PERSISTIDA no banco, não na sessão
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS solicitacoes_prazo (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            edt TEXT,
            tarefa TEXT,
            prazo_atual TEXT,
            prazo_solicitado TEXT,
            justificativa TEXT,
            criado_por TEXT,
            status TEXT DEFAULT '⏳ Pendente de Aprovação',
            criado_em TEXT
        )
    """)

    cursor.execute("SELECT COUNT(*) FROM usuarios")
    if cursor.fetchone()[0] == 0:
        cursor.execute(
            "INSERT INTO usuarios (usuario, nome, setor, senha) VALUES (?, ?, ?, ?)",
            ('master', 'Joice Master', 'Master', hash_senha('Jv568279.'))
        )

    # Migrações seguras para bancos já existentes
    migracoes = [
        "ALTER TABLE cronograma_macro ADD COLUMN Subdivisao TEXT",
        "ALTER TABLE cronograma_macro ADD COLUMN Status_Engenharia TEXT DEFAULT '🔴 Aguardando Medição In Loco'",
        "ALTER TABLE cronograma_macro ADD COLUMN Prazo_Engenharia TEXT",
        "ALTER TABLE cronograma_macro ADD COLUMN Data_Limite_Despacho TEXT",
        "ALTER TABLE cronograma_macro ADD COLUMN Primeiro_Dia_Producao TEXT",
        "ALTER TABLE itens_detalhado ADD COLUMN Fase_Produtiva TEXT",
        "ALTER TABLE itens_detalhado ADD COLUMN Dificuldade INTEGER DEFAULT 3",
    ]
    for sql in migracoes:
        try:
            cursor.execute(sql)
        except sqlite3.OperationalError:
            pass

    conn.commit()
    conn.close()

inicializar_banco_de_dados()

# ========================================================
# FUNÇÕES UTILITÁRIAS DE DATAS
# ========================================================

def subtrair_dias_uteis(data_base: datetime, n: int) -> datetime:
    """Subtrai n dias úteis (seg-sex) de data_base."""
    data = data_base
    contados = 0
    while contados < n:
        data -= timedelta(days=1)
        if data.weekday() < 5:
            contados += 1
    return data

def calcular_cronograma_reverso(inicio_previsto, dias_logistica: int, dias_uteis_fabricacao: int, dias_antecedencia_eng: int = 3):
    """
    ÂNCORA: Inicio_Previsto (data real que a obra precisa receber o material)
    Tudo é derivado DELA para trás — nenhuma data é digitada manualmente.

    Retorna: (prazo_engenharia, primeiro_dia_producao, data_limite_despacho)
    """
    dt = inicio_previsto if isinstance(inicio_previsto, datetime) \
         else datetime.combine(inicio_previsto, datetime.min.time())

    data_limite_despacho   = dt - timedelta(days=int(dias_logistica))
    primeiro_dia_producao  = subtrair_dias_uteis(data_limite_despacho, int(dias_uteis_fabricacao))
    prazo_engenharia       = subtrair_dias_uteis(primeiro_dia_producao, int(dias_antecedencia_eng))

    return prazo_engenharia, primeiro_dia_producao, data_limite_despacho

def gerar_lotes_ordenados(primeiro_dia_producao, data_limite_despacho, dias_uteis_fabricacao: int,
                           total_cx: int, total_m2: float, obra, edt, cod_lote,
                           especificacao, txt_pavimentos, dificuldade):
    """
    Gera lotes em ordem PROGRESSIVA (do primeiro ao último dia),
    com fase produtiva correta (CORTE primeiro, MONTAGEM depois)
    e garantindo que a soma de caixas e m² fecha exatamente o total.
    """
    n = int(dias_uteis_fabricacao)
    cx_por_dia  = total_cx / n
    m2_por_dia  = total_m2 / n
    cx_acum     = 0
    m2_acum     = 0.0
    lotes       = []
    dia         = primeiro_dia_producao
    contados    = 0

    while contados < n:
        if dia.weekday() in [5, 6]:        # pula fim de semana
            dia += timedelta(days=1)
            continue

        contados += 1
        fase = "CORTE E USINAGEM" if contados <= n // 2 else "MONTAGEM FINAL"

        # Último lote recebe o saldo para que a soma feche exatamente
        if contados == n:
            cx_dia = total_cx - cx_acum
            m2_dia = round(total_m2 - m2_acum, 2)
        else:
            cx_dia = max(1, round(cx_por_dia))
            m2_dia = round(m2_por_dia, 2)

        cx_acum  += cx_dia
        m2_acum  += m2_dia

        lotes.append({
            "Obra_Vinculada":           obra,
            "EDT_Vinculado":            edt,
            "Cod_Lote":                 cod_lote,
            "Num_OP":                   None,
            "Tipo_Material":            especificacao,
            "Qtd_Caixas":               int(cx_dia),
            "M2_Item":                  float(m2_dia),
            "Data_Producao_Programada": dia.strftime('%Y-%m-%d'),
            "Data_Limite_Obra":         data_limite_despacho.strftime('%Y-%m-%d'),
            "Romaneio_Chapas":          txt_pavimentos,
            "Status_Item":              "Pendente",
            "Dificuldade":              int(dificuldade),
            "Fase_Produtiva":           fase,
        })
        dia += timedelta(days=1)

    return lotes

def prazo_valido(valor) -> bool:
    if valor is None:
        return False
    try:
        return not pd.isnull(valor)
    except Exception:
        return False

# ========================================================
# FUNÇÕES DE BANCO
# ========================================================

def carregar_macro():
    conn = conectar_banco()
    df = pd.read_sql_query("SELECT * FROM cronograma_macro", conn)
    conn.close()
    if not df.empty:
        for col in ['Inicio_Previsto', 'Termino_Obra', 'Prazo_Engenharia',
                    'Data_Limite_Despacho', 'Primeiro_Dia_Producao']:
            if col not in df.columns:
                df[col] = None
            df[col] = pd.to_datetime(df[col], errors='coerce')
        if 'Subdivisao' not in df.columns:
            df['Subdivisao'] = ''
        if 'Status_Engenharia' not in df.columns:
            df['Status_Engenharia'] = '🔴 Aguardando Medição In Loco'
    return df

def carregar_micro():
    conn = conectar_banco()
    df = pd.read_sql_query("SELECT * FROM itens_detalhado", conn)
    conn.close()
    if not df.empty:
        df['Data_Producao_Programada'] = pd.to_datetime(df['Data_Producao_Programada'], errors='coerce')
        df['Data_Limite_Obra']         = pd.to_datetime(df['Data_Limite_Obra'],         errors='coerce')
        if 'Fase_Produtiva' not in df.columns:
            df['Fase_Produtiva'] = 'N/A'
    return df

def carregar_solicitacoes():
    conn = conectar_banco()
    df = pd.read_sql_query("SELECT * FROM solicitacoes_prazo ORDER BY id DESC", conn)
    conn.close()
    return df

def salvar_solicitacao(edt, tarefa, prazo_atual, prazo_solicitado, justificativa, criado_por):
    conn = conectar_banco()
    cursor = conn.cursor()
    cursor.execute("""
        INSERT INTO solicitacoes_prazo (edt, tarefa, prazo_atual, prazo_solicitado, justificativa, criado_por, status, criado_em)
        VALUES (?, ?, ?, ?, ?, ?, '⏳ Pendente de Aprovação', ?)
    """, (edt, tarefa, prazo_atual, prazo_solicitado, justificativa, criado_por,
          datetime.now().strftime('%d/%m/%Y %H:%M')))
    conn.commit()
    conn.close()

def atualizar_status_solicitacao(sol_id, novo_status):
    conn = conectar_banco()
    cursor = conn.cursor()
    cursor.execute("UPDATE solicitacoes_prazo SET status = ? WHERE id = ?", (novo_status, sol_id))
    conn.commit()
    conn.close()

def atualizar_status_engenharia(edt_id, novo_status):
    conn = conectar_banco()
    cursor = conn.cursor()
    cursor.execute("UPDATE cronograma_macro SET Status_Engenharia = ? WHERE id = ?", (novo_status, edt_id))
    conn.commit()
    conn.close()

def salvar_lotes_micro(lotes: list):
    """Salva lista de dicts como lotes no banco."""
    df = pd.DataFrame(lotes)
    conn = conectar_banco()
    df.to_sql('itens_detalhado', conn, if_exists='append', index=False)
    conn.close()

def deletar_lotes_por_edt_lote(obra, edt, cod_lote):
    """Remove lotes existentes antes de reinserir — evita duplicatas."""
    conn = conectar_banco()
    cursor = conn.cursor()
    cursor.execute(
        "DELETE FROM itens_detalhado WHERE Obra_Vinculada=? AND EDT_Vinculado=? AND Cod_Lote=?",
        (obra, edt, cod_lote)
    )
    conn.commit()
    conn.close()

def atualizar_cronograma_macro_datas(edt, prazo_eng, primeiro_prod, despacho):
    conn = conectar_banco()
    cursor = conn.cursor()
    cursor.execute("""
        UPDATE cronograma_macro
        SET Prazo_Engenharia=?, Primeiro_Dia_Producao=?, Data_Limite_Despacho=?
        WHERE EDT=?
    """, (prazo_eng.strftime('%Y-%m-%d'),
          primeiro_prod.strftime('%Y-%m-%d'),
          despacho.strftime('%Y-%m-%d'),
          edt))
    conn.commit()
    conn.close()

def resetar_banco_dados_completo():
    conn = conectar_banco()
    cursor = conn.cursor()
    cursor.execute("DELETE FROM cronograma_macro")
    cursor.execute("DELETE FROM itens_detalhado")
    cursor.execute("DELETE FROM solicitacoes_prazo")
    conn.commit()
    conn.close()

def verificar_login(usuario, senha):
    conn = conectar_banco()
    cursor = conn.cursor()
    cursor.execute(
        "SELECT nome, setor FROM usuarios WHERE usuario=? AND senha=?",
        (usuario, hash_senha(senha))
    )
    resultado = cursor.fetchone()
    conn.close()
    return resultado

# ========================================================
# LOGIN
# ========================================================
if 'autenticado' not in st.session_state:
    st.session_state.autenticado    = False
    st.session_state.usuario_nome   = ""
    st.session_state.usuario_setor  = ""

if not st.session_state.autenticado:
    st.markdown("<h1 style='text-align:center;color:#1E3A8A;'>Passold Sistemas</h1>", unsafe_allow_html=True)
    st.markdown("<h4 style='text-align:center;color:#6B7280;margin-bottom:30px;'>PCP & Controle Operacional</h4>", unsafe_allow_html=True)
    with st.container():
        st.markdown('<div class="login-container">', unsafe_allow_html=True)
        st.subheader("🔑 Login do Sistema")
        user_input = st.text_input("Usuário:")
        pass_input = st.text_input("Senha:", type="password")
        btn_login  = st.button("Entrar no PCP")
        st.markdown('</div>', unsafe_allow_html=True)
        if btn_login:
            dados = verificar_login(user_input.strip(), pass_input)
            if dados:
                st.session_state.autenticado   = True
                st.session_state.usuario_nome  = dados[0]
                st.session_state.usuario_setor = dados[1]
                st.rerun()
            else:
                st.error("Usuário ou Senha inválidos.")
    st.stop()

# ========================================================
# HEADER PRINCIPAL
# ========================================================
col_h1, col_h2 = st.columns([4, 1])
with col_h1:
    st.title("Passold - PCP Inteligente")
    st.caption(f"Usuário: **{st.session_state.usuario_nome}** | Setor: `{st.session_state.usuario_setor}`")
with col_h2:
    st.write("")
    if st.button("🚪 Sair"):
        st.session_state.autenticado = False
        st.rerun()

# Carrega dados base
df_banco_macro = carregar_macro()
df_banco_micro = carregar_micro()

if not df_banco_macro.empty:
    obras_lista    = sorted(df_banco_macro['Obra'].unique().tolist())
    obra_selecionada = st.selectbox("Selecione a Obra de Trabalho:", obras_lista)
    df_macro_filtrado = df_banco_macro[df_banco_macro['Obra'] == obra_selecionada].copy()
else:
    obra_selecionada  = None
    df_macro_filtrado = pd.DataFrame()

# ========================================================
# ABAS POR PERFIL
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

with st.container():
    abas_objetos = st.tabs(abas_disponiveis)

for nome_aba, aba_objeto in zip(abas_disponiveis, abas_objetos):

    # ====================================================
    # ABA: PAINEL DA TV
    # ====================================================
    if nome_aba == "PAINEL DA TV (Chão de Fábrica)":
        import calendar as py_calendar
        with aba_objeto:
            st.header("📆 Mural de Metas da Produção - Passold")

            obras_tv = ["TODAS AS OBRAS"] + (list(df_banco_micro['Obra_Vinculada'].dropna().unique()) if not df_banco_micro.empty else [])
            obra_tv  = st.selectbox("Filtrar por Obra:", obras_tv, key="sb_obra_tv")

            if not df_banco_micro.empty:
                df_base = df_banco_micro[df_banco_micro['Status_Item'] == "Liberado para Fábrica"].copy()
                df_base = df_base if obra_tv == "TODAS AS OBRAS" else df_base[df_base['Obra_Vinculada'] == obra_tv]

                if not df_base.empty:
                    df_base['Data_Producao_Programada'] = pd.to_datetime(df_base['Data_Producao_Programada']).dt.date

                    if "prog_mes" not in st.session_state: st.session_state.prog_mes = HOJE_PROJETO.month
                    if "prog_ano" not in st.session_state: st.session_state.prog_ano = HOJE_PROJETO.year

                    c1, c2, c3 = st.columns([1, 2, 1])
                    with c1:
                        if st.button("⬅️ Mês Anterior", use_container_width=True, key="btn_ant"):
                            st.session_state.prog_mes -= 1
                            if st.session_state.prog_mes == 0:
                                st.session_state.prog_mes = 12; st.session_state.prog_ano -= 1
                            st.rerun()
                    with c2:
                        nomes_meses = ["","Janeiro","Fevereiro","Março","Abril","Maio","Junho",
                                       "Julho","Agosto","Setembro","Outubro","Novembro","Dezembro"]
                        st.markdown(f"<h3 style='text-align:center;color:#1E3A8A;margin:0;'>📅 {nomes_meses[st.session_state.prog_mes]} / {st.session_state.prog_ano}</h3>", unsafe_allow_html=True)
                    with c3:
                        if st.button("Próximo Mês ➡️", use_container_width=True, key="btn_prox"):
                            st.session_state.prog_mes += 1
                            if st.session_state.prog_mes == 13:
                                st.session_state.prog_mes = 1; st.session_state.prog_ano += 1
                            st.rerun()

                    st.markdown("---")
                    cal = py_calendar.Calendar(firstweekday=6)
                    semanas = cal.monthdatescalendar(st.session_state.prog_ano, st.session_state.prog_mes)

                    for h_idx, h_nome in enumerate(["Dom","Seg","Ter","Qua","Qui","Sex","Sáb"]):
                        st.columns(7)[h_idx].markdown(f"<p style='text-align:center;font-weight:bold;color:#475569;'>{h_nome}</p>", unsafe_allow_html=True)

                    for semana in semanas:
                        cols = st.columns(7)
                        for i, data_dia in enumerate(semana):
                            with cols[i]:
                                if data_dia.month == st.session_state.prog_mes:
                                    ops_dia = df_base[df_base['Data_Producao_Programada'] == data_dia]
                                    n_ops   = len(ops_dia)
                                    eh_hoje = (data_dia == HOJE_PROJETO.date())
                                    bg = "#EFF6FF" if eh_hoje else "#F8FAFC"
                                    bd = "#3B82F6" if eh_hoje else "#E2E8F0"
                                    if n_ops > 0:
                                        if st.button(f"{data_dia.day}\n({n_ops} OPs)", key=f"btn_{data_dia}", use_container_width=True):
                                            st.session_state.dia_clicado_tv = data_dia
                                    else:
                                        st.markdown(f"<div style='background:{bg};border:1px solid {bd};padding:5px;border-radius:6px;text-align:center;height:75px;'><span style='color:#94A3B8;'>{data_dia.day}</span><br><span style='color:#94A3B8;font-size:11px;'>Vazio</span></div>", unsafe_allow_html=True)
                                else:
                                    st.markdown('<div style="height:75px;"></div>', unsafe_allow_html=True)

                    st.markdown("---")
                    if "dia_clicado_tv" not in st.session_state:
                        st.session_state.dia_clicado_tv = HOJE_PROJETO.date()

                    st.subheader(f"🔍 OPs para: {st.session_state.dia_clicado_tv.strftime('%d/%m/%Y')}")
                    df_dia = df_base[df_base['Data_Producao_Programada'] == st.session_state.dia_clicado_tv]

                    if df_dia.empty:
                        st.info("💡 Clique em um dia com OPs no calendário acima.")
                    else:
                        for _, row in df_dia.iterrows():
                            with st.container(border=True):
                                cd, ca = st.columns([4, 1])
                                with cd:
                                    st.markdown(f"""
                                        <span style="background:#FFEDD5;color:#EA580C;padding:3px 8px;border-radius:4px;font-weight:bold;font-size:13px;margin-right:8px;">🏗️ {row['Obra_Vinculada']}</span>
                                        <span style="background:#E0E7FF;color:#4338CA;padding:3px 8px;border-radius:4px;font-weight:bold;font-size:13px;">Lote: {row['Cod_Lote']}</span>
                                    """, unsafe_allow_html=True)
                                    op_txt = row['Num_OP'] if row['Num_OP'] else "S/ OP"
                                    st.markdown(f"#### 📦 OP: **{op_txt}**")
                                    st.markdown(f"**Material:** {row['Tipo_Material']} | **Fase:** `{row.get('Fase_Produtiva','—')}` | **Meta:** `{int(row['Qtd_Caixas'])} cx` ({row['M2_Item']:.2f} m²)")
                                    despacho_txt = pd.to_datetime(row['Data_Limite_Obra']).strftime('%d/%m/%Y') if pd.notna(row['Data_Limite_Obra']) else "—"
                                    st.caption(f"Pavimentos: {row['Romaneio_Chapas']} | Prazo despacho fábrica: {despacho_txt}")
                                with ca:
                                    st.write("")
                                    if st.button("✅ PRONTO", key=f"baixa_{row['id']}", type="primary", use_container_width=True):
                                        conn = conectar_banco(); cursor = conn.cursor()
                                        cursor.execute("UPDATE itens_detalhado SET Status_Item='Concluído' WHERE id=?", (row['id'],))
                                        conn.commit(); conn.close()
                                        st.toast(f"Lote {row['Cod_Lote']} concluído! 🚀")
                                        time.sleep(0.3); st.rerun()
                else:
                    st.success("🙌 Sem ordens liberadas para este filtro.")
            else:
                st.info("Nenhum lote liberado no sistema ainda.")

    # ====================================================
    # ABA: LIBERAR OPS DA SEMANA
    # ====================================================
    elif nome_aba == "Liberar OPs da Semana":
        with aba_objeto:
            st.header("Gerenciador de Ordens de Produção Semanais")
            if obra_selecionada and not df_banco_micro.empty:
                df_pend = df_banco_micro[
                    (df_banco_micro['Obra_Vinculada'] == obra_selecionada) &
                    (df_banco_micro['Status_Item'] == "Pendente")
                ].copy()

                if not df_pend.empty:
                    df_pend['Selecionar'] = False
                    cols_exib = [c for c in ['id','Cod_Lote','Tipo_Material','Qtd_Caixas','M2_Item',
                                              'Fase_Produtiva','Data_Producao_Programada','Romaneio_Chapas','Selecionar']
                                 if c in df_pend.columns]
                    df_ed = st.data_editor(df_pend[cols_exib], hide_index=True, use_container_width=True,
                                           disabled=[c for c in cols_exib if c != 'Selecionar'])
                    ids_sel = df_ed[df_ed['Selecionar'] == True]['id'].tolist()

                    prefixo = st.text_input("Prefixo da OP:", value=f"OP-{datetime.now().strftime('%Y')}-")
                    if st.button("Liberar Selecionados para a TV da Fábrica"):
                        if ids_sel:
                            conn = conectar_banco(); cursor = conn.cursor()
                            for item_id in ids_sel:
                                cursor.execute(
                                    "UPDATE itens_detalhado SET Status_Item='Liberado para Fábrica', Num_OP=? WHERE id=?",
                                    (f"{prefixo}{str(item_id).zfill(3)}", item_id)
                                )
                            conn.commit(); conn.close()
                            st.toast("OPs liberadas!", icon="✅"); time.sleep(0.5); st.rerun()
                        else:
                            st.warning("Selecione pelo menos um item.")
                else:
                    st.success("Todos os lotes já foram liberados.")
            else:
                st.info("Nenhum lote pendente encontrado.")

    # ====================================================
    # ABA: VISÃO MACRO (DIRETORIA)
    # ====================================================
    elif nome_aba == "Visão Macro (Diretoria)":
        with aba_objeto:
            st.header("📊 Dashboard Executivo e Cronograma Macro")
            df_dir = df_banco_micro[df_banco_micro['Obra_Vinculada'] == obra_selecionada].copy() \
                     if obra_selecionada and not df_banco_micro.empty else df_banco_micro.copy()

            if not df_dir.empty:
                data_max = df_dir['Data_Limite_Obra'].max()
                c1, c2, c3 = st.columns(3)
                c1.metric("Metragem Total", f"{df_dir['M2_Item'].sum():,.2f} m²")
                c2.metric("Subdivisões", f"{df_dir['EDT_Vinculado'].nunique()} frentes")
                c3.metric("Prazo Despacho Mais Distante", data_max.strftime('%d/%m/%Y') if pd.notna(data_max) else "N/A")

                st.markdown("---")
                st.subheader("📈 Carga Semanal de Produção")
                df_lib = df_dir[df_dir['Status_Item'].isin(["Liberado para Fábrica","Produção","Concluído"])].copy()

                if not df_lib.empty:
                    df_lib['Ano_Semana'] = df_lib['Data_Producao_Programada'].dt.isocalendar().year
                    df_lib['Num_Semana'] = df_lib['Data_Producao_Programada'].dt.isocalendar().week

                    def fmt_semana(row):
                        try:
                            seg = pd.to_datetime(f"{int(row['Ano_Semana'])}-W{int(row['Num_Semana'])}-1", format="%G-W%V-%u")
                            return f"Semana {int(row['Num_Semana']):02d} ({seg.strftime('%d/%m')} – {(seg+timedelta(days=6)).strftime('%d/%m/%Y')})"
                        except:
                            return f"Semana {row['Num_Semana']}"

                    df_lib['Período'] = df_lib.apply(fmt_semana, axis=1)
                    res = df_lib.groupby(['Ano_Semana','Num_Semana','Período','Obra_Vinculada']).agg(
                        Lotes=('id','count'), Caixas=('Qtd_Caixas','sum'), M2=('M2_Item','sum'),
                        Evolucao=('Status_Item', lambda x: f"{(x=='Concluído').sum()/len(x)*100:.0f}% concluído")
                    ).reset_index().sort_values(['Ano_Semana','Num_Semana'])
                    res.columns = ['Ano','Sem','Período Comercial','Obra','Lotes','Caixas (cx)','Volume (m²)','Evolução']
                    st.dataframe(res[['Período Comercial','Obra','Lotes','Caixas (cx)','Volume (m²)','Evolução']],
                                 hide_index=True, use_container_width=True)
                else:
                    st.warning("Nenhuma OP liberada ainda nesta obra.")

                st.subheader("📊 Gantt — Linha do Tempo")
                df_gantt = df_dir.groupby(['Obra_Vinculada','EDT_Vinculado','Romaneio_Chapas']).agg(
                    Inicio=('Data_Producao_Programada','min'), Fim=('Data_Limite_Obra','max'), M2=('M2_Item','sum')
                ).reset_index().dropna(subset=['Inicio','Fim'])

                if not df_gantt.empty:
                    fig = px.timeline(df_gantt, x_start="Inicio", x_end="Fim", y="EDT_Vinculado",
                                      color="Obra_Vinculada", hover_data=["Romaneio_Chapas","M2"],
                                      title="Ocupação de Fábrica vs Prazo de Despacho")
                    fig.update_yaxes(autorange="reversed")
                    fig.update_layout(height=400, margin=dict(l=20,r=20,t=40,b=20))
                    st.plotly_chart(fig, use_container_width=True)
            else:
                st.info("Nenhum dado encontrado para esta obra.")

    # ====================================================
    # ABA: VINCULAR DATAS (MATERIAIS)
    # LÓGICA CORRIGIDA COMPLETA
    # ====================================================
    elif nome_aba == "Vincular Datas (Materiais)":
        with aba_objeto:
            st.header("Inteligência Temporal: Fatiamento e Edição de Lotes")

            if st.session_state.get('lote_salvo_sucesso'):
                st.success("✅ Remessa gerada com sucesso e salva como Pendente.")
                st.session_state.lote_salvo_sucesso = False

            if obra_selecionada and not df_macro_filtrado.empty:
                opcoes_edt    = []
                mapa_edt_rows = {}

                for _, row in df_macro_filtrado.iterrows():
                    sub = f" [{row['Subdivisao']}]" if row.get('Subdivisao') else ""
                    label = f"{row['EDT']} - {row['Tarefa']}{sub}"
                    opcoes_edt.append(label)
                    mapa_edt_rows[label] = row

                st.markdown("### 🛠️ Fatiar Nova Remessa de Materiais")

                with st.form("form_fatiamento"):
                    col1, col2, col3 = st.columns(3)

                    with col1:
                        edt_sel   = st.selectbox("Frente macro (EDT):", opcoes_edt)
                        row_sel   = mapa_edt_rows[edt_sel]
                        edt_puro  = edt_sel.split(" - ")[0].strip()
                        cod_lote  = st.text_input("Código desta Remessa:")

                        inicio_prev = row_sel['Inicio_Previsto']
                        if prazo_valido(inicio_prev):
                            st.info(f"📅 Início instalação desta frente: **{inicio_prev.strftime('%d/%m/%Y')}**")
                        else:
                            st.warning("⚠️ Esta frente não tem data de instalação cadastrada.")

                    with col2:
                        dias_logistica = st.number_input(
                            "Dias logística despacho→obra (corridos):", min_value=1, value=5,
                            help="Quantos dias corridos entre o despacho da fábrica e o início da instalação na obra"
                        )
                        dificuldade = st.selectbox("Complexidade:", [1,2,3,4,5], index=3)

                    with col3:
                        dias_uteis_fab = st.number_input(
                            "Dias úteis de produção estimados:", min_value=1, value=20
                        )

                        # PREVIEW — calculado a partir do Inicio_Previsto
                        if prazo_valido(inicio_prev):
                            prev_prazo_eng, prev_primeiro, prev_despacho = calcular_cronograma_reverso(
                                inicio_prev, dias_logistica, dias_uteis_fab
                            )
                            st.success(
                                f"🗓️ **Cronograma calculado:**\n\n"
                                f"Prazo engenharia → PCP: **{prev_prazo_eng.strftime('%d/%m/%Y')}**\n\n"
                                f"1º dia produção: **{prev_primeiro.strftime('%d/%m/%Y')}**\n\n"
                                f"Despacho fábrica: **{prev_despacho.strftime('%d/%m/%Y')}**"
                            )
                        else:
                            st.error("Cadastre o Início de Instalação na obra antes de fatiar.")

                    st.markdown("---")
                    cd1, cd2 = st.columns(2)
                    with cd1:
                        txt_pavimentos = st.text_area("Pavimentos Destino:", value="Pav 39 ao 43")
                        especificacao  = st.text_input("Material / Chapa:", value="ACM BRANCO")
                    with cd2:
                        total_cx = st.number_input("Total de Caixas:", min_value=1, value=50)
                        total_m2 = st.number_input("Total m²:", min_value=0.1, value=113.27)

                    status_eng = row_sel.get('Status_Engenharia', '🔴 Aguardando Medição In Loco')
                    if "🟢" not in str(status_eng):
                        st.warning(f"⚠️ Engenharia ainda não liberou esta frente: `{status_eng}`")

                    submitted = st.form_submit_button("✅ Distribuir Remessa")

                    if submitted:
                        if not cod_lote.strip():
                            st.error("Digite o código da remessa.")
                        elif not prazo_valido(inicio_prev):
                            st.error("Esta frente não tem Início de Instalação cadastrado. Edite a obra primeiro.")
                        else:
                            prazo_eng, primeiro_prod, data_despacho = calcular_cronograma_reverso(
                                inicio_prev, dias_logistica, dias_uteis_fab
                            )

                            # Apaga lotes anteriores do mesmo EDT+Lote antes de inserir (evita duplicatas)
                            deletar_lotes_por_edt_lote(obra_selecionada, edt_puro, cod_lote.strip())

                            lotes = gerar_lotes_ordenados(
                                primeiro_prod, data_despacho, dias_uteis_fab,
                                int(total_cx), float(total_m2), obra_selecionada, edt_puro,
                                cod_lote.strip(), especificacao, txt_pavimentos, dificuldade
                            )
                            salvar_lotes_micro(lotes)
                            atualizar_cronograma_macro_datas(edt_puro, prazo_eng, primeiro_prod, data_despacho)

                            st.session_state.lote_salvo_sucesso = True
                            st.rerun()

                st.markdown("---")
                st.markdown("### 📝 Lotes Gerados")
                st.caption("Clique duplo para editar. Alterações são salvas automaticamente.")

                df_ed_raw = carregar_micro()
                if not df_ed_raw.empty:
                    df_obra = df_ed_raw[df_ed_raw['Obra_Vinculada'] == obra_selecionada].copy()
                    if not df_obra.empty:
                        df_obra['Data_Producao_Programada'] = df_obra['Data_Producao_Programada'].dt.strftime('%Y-%m-%d')
                        df_obra['Data_Limite_Obra']         = df_obra['Data_Limite_Obra'].dt.strftime('%Y-%m-%d')
                        df_obra_str = df_obra.copy()

                        df_editado = st.data_editor(
                            df_obra_str, key="editor_lotes", hide_index=True,
                            use_container_width=True, disabled=["id","Obra_Vinculada","Num_OP"]
                        )

                        # Salva só se houve diferença real
                        linhas_alteradas = []
                        for idx in df_editado.index:
                            if not df_editado.loc[idx].equals(df_obra_str.loc[idx]):
                                linhas_alteradas.append(df_editado.loc[idx])

                        if linhas_alteradas:
                            conn = conectar_banco(); cursor = conn.cursor()
                            for row in linhas_alteradas:
                                cursor.execute("""
                                    UPDATE itens_detalhado
                                    SET Cod_Lote=?, Tipo_Material=?, Qtd_Caixas=?, M2_Item=?,
                                        Data_Producao_Programada=?, Data_Limite_Obra=?,
                                        Romaneio_Chapas=?, Status_Item=?, Dificuldade=?, Fase_Produtiva=?
                                    WHERE id=?
                                """, (row['Cod_Lote'], row['Tipo_Material'], int(row['Qtd_Caixas']), float(row['M2_Item']),
                                      row['Data_Producao_Programada'], row['Data_Limite_Obra'],
                                      row['Romaneio_Chapas'], row['Status_Item'], int(row['Dificuldade']),
                                      row['Fase_Produtiva'], int(row['id'])))
                            conn.commit(); conn.close()
                            st.toast("Alterações salvas!", icon="💾")
                            time.sleep(0.3); st.rerun()

                        st.markdown("#### 🗑️ Remover Lote")
                        lotes_del = df_obra['Cod_Lote'].unique().tolist()
                        lote_del  = st.selectbox("Selecione o lote para excluir:", lotes_del)
                        if st.button(f"Excluir todos os registros do Lote {lote_del}"):
                            deletar_lotes_por_edt_lote(obra_selecionada, None, lote_del)
                            # versão mais genérica: apaga por obra+lote
                            conn = conectar_banco(); cursor = conn.cursor()
                            cursor.execute("DELETE FROM itens_detalhado WHERE Obra_Vinculada=? AND Cod_Lote=?",
                                           (obra_selecionada, lote_del))
                            conn.commit(); conn.close()
                            st.toast(f"Lote {lote_del} removido!", icon="🗑️")
                            time.sleep(0.5); st.rerun()
                    else:
                        st.info("Nenhum lote fatiado para esta obra ainda.")

    # ====================================================
    # ABA: CADASTRAR NOVA OBRA
    # ====================================================
    elif nome_aba == "Cadastrar Nova Obra":
        with aba_objeto:
            st.header("Cadastrar Nova Obra e Frentes de Trabalho")

            for k, v in [('mem_obra',''),('mem_escopo','ACM'),('mem_frente',''),
                         ('mem_tarefa',''),('mem_dt_ini',datetime.now().date()),
                         ('mem_dt_fim',(datetime.now()+timedelta(days=90)).date())]:
                if k not in st.session_state: st.session_state[k] = v

            with st.form("form_nova_obra"):
                nome_obra = st.text_input("Nome da Obra:", value=st.session_state.mem_obra).upper()
                co1, co2  = st.columns(2)
                with co1:
                    escopo   = st.selectbox("Tipo de Escopo:", ["ACM","Vidro/Esquadria"])
                    frente   = st.text_input("Frente Macro / Pavimentos:", value=st.session_state.mem_frente)
                    tarefa   = st.text_input("Nome da Tarefa / Balancim:", value=st.session_state.mem_tarefa)
                with co2:
                    edt_cod  = st.text_input("Código EDT (único):")
                    subdiv   = st.text_input("Subdivisão / Balancim:").upper()
                    m2_tot   = st.number_input("Metragem (m²):", min_value=0.1, value=100.0)

                cd1, cd2 = st.columns(2)
                with cd1:
                    dt_ini = st.date_input("📅 Data Alvo Início Instalação:", value=st.session_state.mem_dt_ini, format="DD/MM/YYYY",
                                           help="Esta é a âncora de todo o cálculo de prazos do PCP")
                with cd2:
                    dt_fim = st.date_input("Prazo Máximo Obra Pronta:", value=st.session_state.mem_dt_fim, format="DD/MM/YYYY")

                if st.form_submit_button("Registrar Frente"):
                    if not all([nome_obra.strip(), edt_cod.strip(), tarefa.strip(), subdiv.strip()]):
                        st.error("Preencha todos os campos obrigatórios.")
                    else:
                        st.session_state.mem_obra   = nome_obra
                        st.session_state.mem_frente = frente
                        st.session_state.mem_tarefa = tarefa
                        st.session_state.mem_dt_ini = dt_ini
                        st.session_state.mem_dt_fim = dt_fim
                        conn = conectar_banco(); cursor = conn.cursor()
                        try:
                            cursor.execute("""
                                INSERT INTO cronograma_macro
                                (Obra,EDT,Tipo_Escopo,Etapa_Macro,Subdivisao,Tarefa,M2_Total_Tarefa,
                                 Inicio_Previsto,Termino_Obra,Status,Status_Engenharia)
                                VALUES (?,?,?,?,?,?,?,?,?,'Pendente','🔴 Aguardando Medição In Loco')
                            """, (nome_obra, edt_cod, escopo, frente, subdiv, tarefa, float(m2_tot),
                                  dt_ini.strftime('%Y-%m-%d'), dt_fim.strftime('%Y-%m-%d')))
                            conn.commit()
                            st.toast("Frente registrada!", icon="🚀")
                            time.sleep(0.4); st.rerun()
                        except sqlite3.IntegrityError:
                            st.error(f"O EDT '{edt_cod}' já existe.")
                        finally:
                            conn.close()

            # Lista obras cadastradas
            if not df_banco_macro.empty:
                st.markdown("---")
                st.markdown("### 📋 Frentes Cadastradas")
                cols_exib = [c for c in ['Obra','EDT','Subdivisao','Tarefa','M2_Total_Tarefa',
                                          'Inicio_Previsto','Termino_Obra','Status_Engenharia']
                             if c in df_banco_macro.columns]
                df_show = df_banco_macro[cols_exib].copy()
                for col in ['Inicio_Previsto','Termino_Obra']:
                    if col in df_show.columns:
                        df_show[col] = pd.to_datetime(df_show[col]).dt.strftime('%d/%m/%Y')
                st.dataframe(df_show, hide_index=True, use_container_width=True)

    # ====================================================
    # ABA: PAINEL TÉCNICO DA ENGENHARIA
    # ====================================================
    elif nome_aba == "Painel Técnico da Engenharia":
        with aba_objeto:
            st.header("🏗️ Painel Técnico da Engenharia")
            st.caption(f"Data do sistema: {HOJE_PROJETO.strftime('%d/%m/%Y')} | Obra: **{obra_selecionada or 'Nenhuma'}**")

            df_eng = carregar_macro()
            if obra_selecionada:
                df_eng = df_eng[df_eng['Obra'] == obra_selecionada]
            else:
                df_eng = pd.DataFrame()

            ESTADOS = [
                "🔴 Aguardando Medição In Loco",
                "🟡 Medição Realizada — Em Projetos",
                "🔵 Projetos em Revisão Interna",
                "🟢 Projetos Liberados para o PCP",
                "⚪ Arquivado / Concluído",
            ]

            def classificar(dias_rest, status_tec):
                if status_tec == "🟢 Projetos Liberados para o PCP":
                    return "concluido", "✅ Liberado para o PCP", None
                if dias_rest is None:
                    return "sem_prazo", "⚪ Aguardando programação pelo PCP", None
                if dias_rest < 0:
                    return "vencido", f"🔴 VENCIDO há {abs(int(dias_rest))} dias", abs(int(dias_rest))
                if dias_rest <= 7:
                    return "critico", f"🟡 Crítico — faltam {int(dias_rest)} dias", int(dias_rest)
                return "ok", f"🟢 Dentro do prazo ({int(dias_rest)} dias)", int(dias_rest)

            frentes = []
            if not df_eng.empty:
                for _, row in df_eng.iterrows():
                    prazo_raw = row.get('Prazo_Engenharia')
                    prazo_eng = prazo_raw if prazo_valido(prazo_raw) else None
                    dias_rest = (prazo_eng - HOJE_PROJETO).days if prazo_eng is not None else None
                    sk, st_txt, dias_num = classificar(dias_rest, row.get('Status_Engenharia', ESTADOS[0]))

                    # Exibe o Inicio_Previsto como âncora principal
                    inicio_prev = row.get('Inicio_Previsto')
                    despacho    = row.get('Data_Limite_Despacho')
                    primeiro    = row.get('Primeiro_Dia_Producao')

                    frentes.append({
                        "id": row['id'], "edt": row['EDT'], "tarefa": row['Tarefa'],
                        "subdivisao": row.get('Subdivisao',''), "tipo_escopo": row.get('Tipo_Escopo',''),
                        "inicio_previsto": inicio_prev, "termino_obra": row['Termino_Obra'],
                        "despacho": despacho, "primeiro_prod": primeiro,
                        "m2": row.get('M2_Total_Tarefa', 0.0),
                        "prazo_eng": prazo_eng, "dias_restantes": dias_rest,
                        "situacao_key": sk, "situacao_txt": st_txt, "dias_num": dias_num,
                        "status_tecnico": row.get('Status_Engenharia', ESTADOS[0]),
                    })

            criticas = [f for f in frentes if f['situacao_key'] in ('critico','vencido')]

            # --- Expander 1: Frentes Críticas ---
            with st.expander(f"🚨 Frentes Críticas — {len(criticas)} alerta(s)", expanded=True):
                if not criticas:
                    st.success("✅ Nenhuma frente crítica. Tudo dentro do prazo!")
                else:
                    for fr in sorted(criticas, key=lambda x: x['dias_restantes'] or 0):
                        with st.container(border=True):
                            ci, cc = st.columns([7, 3])
                            with ci:
                                sub = f" · {fr['subdivisao']}" if fr['subdivisao'] else ""
                                st.markdown(f"### {fr['tarefa']}{sub}")
                                cm1, cm2 = st.columns(2)
                                with cm1:
                                    st.write(f"📌 **EDT:** `{fr['edt']}`")
                                    inicio_txt = fr['inicio_previsto'].strftime('%d/%m/%Y') if prazo_valido(fr['inicio_previsto']) else "—"
                                    st.write(f"📅 **Início instalação:** {inicio_txt}")
                                    primeiro_txt = fr['primeiro_prod'].strftime('%d/%m/%Y') if prazo_valido(fr['primeiro_prod']) else "Não calculado"
                                    st.write(f"🏭 **1º dia produção:** {primeiro_txt}")
                                with cm2:
                                    prazo_txt = fr['prazo_eng'].strftime('%d/%m/%Y') if fr['prazo_eng'] else "Não calculado"
                                    st.write(f"📐 **Prazo engenharia:** `{prazo_txt}`")
                                    desp_txt = fr['despacho'].strftime('%d/%m/%Y') if prazo_valido(fr['despacho']) else "Não calculado"
                                    st.write(f"🚚 **Despacho fábrica:** {desp_txt}")
                                    st.write(f"📊 **Metragem:** {fr['m2']:,.2f} m²")
                                st.write(f"🔧 **Status:** {fr['status_tecnico']}")
                            with cc:
                                if fr['situacao_key'] == 'vencido':
                                    st.error(f"⏰ VENCIDO\n\n**{fr['dias_num']} dias** atraso")
                                else:
                                    st.warning(f"⏳ FALTAM\n\n**{fr['dias_num']} dias**")

                            st.markdown("---")
                            ca1, ca2 = st.columns(2)
                            with ca1:
                                idx_at = ESTADOS.index(fr['status_tecnico']) if fr['status_tecnico'] in ESTADOS else 0
                                novo_s = st.selectbox("Atualizar status:", ESTADOS, index=idx_at, key=f"crit_s_{fr['id']}")
                            with ca2:
                                st.write(""); st.write("")
                                if st.button("💾 Salvar", key=f"crit_b_{fr['id']}", use_container_width=True):
                                    atualizar_status_engenharia(fr['id'], novo_s)
                                    st.toast("Status atualizado!", icon="✅"); time.sleep(0.3); st.rerun()

            # --- Expander 2: Todas as Frentes ---
            with st.expander(f"📋 Todas as Frentes — {len(frentes)} frente(s)", expanded=False):
                if not frentes:
                    st.info("Nenhuma frente cadastrada.")
                else:
                    cf1, cf2 = st.columns([3, 2])
                    with cf1:
                        filt_st = st.selectbox("Filtrar por status:", ["Todos"] + ESTADOS, key="eng_filt_st")
                    with cf2:
                        filt_sit = st.radio("Situação:", ["Todas","Críticas","Liberadas"], horizontal=True, key="eng_filt_sit")

                    exibir = frentes.copy()
                    if filt_st != "Todos":
                        exibir = [f for f in exibir if f['status_tecnico'] == filt_st]
                    if filt_sit == "Críticas":
                        exibir = [f for f in exibir if f['situacao_key'] in ('critico','vencido')]
                    elif filt_sit == "Liberadas":
                        exibir = [f for f in exibir if f['situacao_key'] == 'concluido']

                    st.markdown(f"**{len(exibir)} frente(s) exibida(s)**")
                    st.markdown("---")

                    for fr in exibir:
                        with st.container(border=True):
                            ci, cd, ca = st.columns([5, 3, 2])
                            with ci:
                                sub = f" · *{fr['subdivisao']}*" if fr['subdivisao'] else ""
                                st.markdown(f"**{fr['tarefa']}**{sub}")
                                st.caption(f"EDT: {fr['edt']} | {fr['tipo_escopo']} | {fr['m2']:,.2f} m²")
                                st.write(fr['status_tecnico'])
                            with cd:
                                inicio_txt = fr['inicio_previsto'].strftime('%d/%m/%Y') if prazo_valido(fr['inicio_previsto']) else "—"
                                st.caption("📅 Início instalação")
                                st.write(inicio_txt)
                                st.caption("📐 Prazo PCP p/ projetos")
                                prazo_txt = fr['prazo_eng'].strftime('%d/%m/%Y') if fr['prazo_eng'] else "—"
                                st.write(f"`{prazo_txt}`")
                                st.caption("🚚 Despacho fábrica")
                                desp_txt = fr['despacho'].strftime('%d/%m/%Y') if prazo_valido(fr['despacho']) else "—"
                                st.write(desp_txt)
                            with ca:
                                sk = fr['situacao_key']
                                if sk == 'vencido':     st.error(fr['situacao_txt'])
                                elif sk == 'critico':   st.warning(fr['situacao_txt'])
                                elif sk == 'concluido': st.success(fr['situacao_txt'])
                                elif sk == 'ok':        st.success(fr['situacao_txt'])
                                else:                   st.info(fr['situacao_txt'])

                            cs, cb = st.columns([4, 1])
                            with cs:
                                idx_at = ESTADOS.index(fr['status_tecnico']) if fr['status_tecnico'] in ESTADOS else 0
                                novo_s = st.selectbox("Status:", ESTADOS, index=idx_at,
                                                      key=f"all_s_{fr['id']}", label_visibility="collapsed")
                            with cb:
                                if st.button("💾", key=f"all_b_{fr['id']}", use_container_width=True):
                                    atualizar_status_engenharia(fr['id'], novo_s)
                                    st.toast("Atualizado!", icon="✅"); time.sleep(0.3); st.rerun()

            # --- Expander 3: Solicitações de Prazo (PERSISTIDO NO BANCO) ---
            df_sols = carregar_solicitacoes()
            n_pend  = len(df_sols[df_sols['status'] == '⏳ Pendente de Aprovação']) if not df_sols.empty else 0
            label_sol = f"📝 Solicitações de Prazo{f' — {n_pend} pendente(s)' if n_pend else ''}"

            with st.expander(label_sol, expanded=False):
                frentes_nao_lib = [f for f in frentes if f['situacao_key'] != 'concluido']

                if setor in ["Engenharia","Master"] and frentes_nao_lib:
                    st.markdown("#### ✍️ Nova Solicitação")
                    cs1, cs2 = st.columns(2)
                    with cs1:
                        opts_sol = [f"{f['edt']} — {f['tarefa']}" for f in frentes_nao_lib]
                        sel_sol  = st.selectbox("Frente:", opts_sol, key="sol_frente")
                        fr_obj   = frentes_nao_lib[opts_sol.index(sel_sol)]
                        prazo_at = fr_obj['prazo_eng'].strftime('%d/%m/%Y') if fr_obj['prazo_eng'] else "Não definido"
                        st.info(f"Prazo atual: **{prazo_at}**")
                    with cs2:
                        novo_prazo_sol = st.date_input(
                            "Novo prazo solicitado:",
                            value=(fr_obj['prazo_eng'] + timedelta(days=7)).date() if fr_obj['prazo_eng'] else HOJE_PROJETO.date(),
                            format="DD/MM/YYYY", key="sol_novo_prazo"
                        )
                        justif = st.text_area("Justificativa:", key="sol_justif",
                                              placeholder="Ex: Revisão de projeto pelo cliente...")

                    if st.button("📤 Enviar Solicitação", key="sol_enviar"):
                        if not justif.strip():
                            st.error("Informe a justificativa.")
                        else:
                            salvar_solicitacao(fr_obj['edt'], fr_obj['tarefa'], prazo_at,
                                               novo_prazo_sol.strftime('%d/%m/%Y'), justif.strip(),
                                               st.session_state.usuario_nome)
                            st.success("Solicitação enviada e salva!"); st.rerun()

                st.markdown("---")

                if setor == "Master" and not df_sols.empty:
                    pend = df_sols[df_sols['status'] == '⏳ Pendente de Aprovação']
                    if pend.empty:
                        st.info("Nenhuma solicitação pendente.")
                    else:
                        st.markdown("#### ✅ Decisões do PCP")
                        for _, sol in pend.iterrows():
                            with st.container(border=True):
                                csa, csb = st.columns([4, 2])
                                with csa:
                                    st.markdown(f"**{sol['tarefa']}** — EDT `{sol['edt']}`")
                                    st.write(f"`{sol['prazo_atual']}` → `{sol['prazo_solicitado']}`")
                                    st.caption(f"*{sol['justificativa']}* | Por: {sol['criado_por']} em {sol['criado_em']}")
                                with csb:
                                    cap, cre = st.columns(2)
                                    with cap:
                                        if st.button("✅", key=f"ap_{sol['id']}", use_container_width=True):
                                            atualizar_status_solicitacao(sol['id'], "✅ Aprovado")
                                            st.toast("Aprovado!"); st.rerun()
                                    with cre:
                                        if st.button("❌", key=f"rej_{sol['id']}", use_container_width=True):
                                            atualizar_status_solicitacao(sol['id'], "❌ Rejeitado")
                                            st.toast("Rejeitado."); st.rerun()

                if not df_sols.empty:
                    hist = df_sols[df_sols['status'] != '⏳ Pendente de Aprovação']
                    if not hist.empty:
                        st.markdown("#### 📂 Histórico")
                        for _, sol in hist.iterrows():
                            st.caption(f"{sol['status']} | **{sol['tarefa']}** | Pedido: {sol['prazo_solicitado']} | {sol['criado_por']}")

            # --- Expander 4: Carga da Fábrica ---
            with st.expander("🔍 Carga Ocupada da Fábrica por Semana", expanded=False):
                df_fab = df_banco_micro[df_banco_micro['Status_Item'] == "Liberado para Fábrica"].copy() \
                         if not df_banco_micro.empty else pd.DataFrame()
                if not df_fab.empty:
                    df_fab['Ano_Semana'] = df_fab['Data_Producao_Programada'].dt.isocalendar().year
                    df_fab['Num_Semana'] = df_fab['Data_Producao_Programada'].dt.isocalendar().week
                    def fmt_sem(r):
                        try:
                            s = pd.to_datetime(f"{int(r['Ano_Semana'])}-W{int(r['Num_Semana'])}-1", format="%G-W%V-%u")
                            return f"Semana {int(r['Num_Semana']):02d} ({s.strftime('%d/%m')} – {(s+timedelta(days=6)).strftime('%d/%m')})"
                        except: return f"Semana {r['Num_Semana']}"
                    df_fab['Período'] = df_fab.apply(fmt_sem, axis=1)
                    res_fab = df_fab.groupby(['Ano_Semana','Num_Semana','Período','Obra_Vinculada']).agg(
                        Caixas=('Qtd_Caixas','sum'), M2=('M2_Item','sum')
                    ).reset_index().sort_values(['Ano_Semana','Num_Semana'])
                    res_fab.columns = ['Ano','Sem','Período','Obra','Caixas (cx)','Metragem (m²)']
                    st.dataframe(res_fab[['Período','Obra','Caixas (cx)','Metragem (m²)']],
                                 hide_index=True, use_container_width=True)
                else:
                    st.success("🌴 Fábrica livre — nenhuma OP liberada ainda.")

    # ====================================================
    # ABA: CONFIGURAÇÕES DO SISTEMA
    # ====================================================
    elif nome_aba == "Configurações do Sistema":
        with aba_objeto:
            st.header("⚙️ Painel de Controle Master")
            st.markdown("### 👥 Usuários")

            with st.expander("➕ Cadastrar Novo Usuário"):
                with st.form("form_novo_user"):
                    nu = st.text_input("Login (sem espaços):").lower().strip()
                    nn = st.text_input("Nome:")
                    ns = st.selectbox("Setor:", ["Produção","Engenharia","Diretoria","Master"])
                    np = st.text_input("Senha:", type="password")
                    if st.form_submit_button("Salvar"):
                        if not all([nu, nn, np]):
                            st.error("Preencha todos os campos.")
                        else:
                            conn = conectar_banco(); cursor = conn.cursor()
                            try:
                                cursor.execute(
                                    "INSERT INTO usuarios (usuario,nome,setor,senha) VALUES (?,?,?,?)",
                                    (nu, nn, ns, hash_senha(np))
                                )
                                conn.commit()
                                st.success(f"Usuário {nn} criado!"); time.sleep(0.5); st.rerun()
                            except sqlite3.IntegrityError:
                                st.error("Login já existe.")
                            finally:
                                conn.close()

            conn = conectar_banco()
            df_u = pd.read_sql_query("SELECT id, usuario as Login, nome as Nome, setor as Setor FROM usuarios", conn)
            conn.close()
            st.dataframe(df_u, hide_index=True, use_container_width=True)

            if len(df_u) > 1:
                del_u = st.selectbox("Remover usuário:", df_u['Login'].tolist())
                if del_u == 'master':
                    st.caption("🔒 O master não pode ser deletado.")
                else:
                    if st.button(f"❌ Excluir {del_u}"):
                        conn = conectar_banco(); cursor = conn.cursor()
                        cursor.execute("DELETE FROM usuarios WHERE usuario=?", (del_u,))
                        conn.commit(); conn.close()
                        st.toast("Removido!", icon="🗑️"); time.sleep(0.5); st.rerun()

            st.markdown("---")
            st.markdown("### 🚨 Reset Geral")
            st.warning("Remove TODAS as obras, lotes e solicitações permanentemente.")
            if st.button("CONFIRMAR LIMPEZA TOTAL DO BANCO"):
                resetar_banco_dados_completo()
                for k in ['mem_obra','mem_frente','mem_tarefa']:
                    st.session_state[k] = ""
                st.toast("Banco resetado!", icon="🗑️"); time.sleep(0.5); st.rerun()