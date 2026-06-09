import streamlit as st
import pandas as pd
import plotly.express as px
from datetime import datetime, timedelta
import os
import time
import hashlib
import psycopg2
import psycopg2.extras

st.set_page_config(page_title="Passold Sistemas de Fachadas", layout="wide")

st.markdown("""
    <style>
    .main .block-container { padding-top: 2rem; }
    h1 { color: #1E3A8A; font-weight: 700; }
    h2 { color: #2563EB; }
    .stMetric { background-color: #F3F4F6; padding: 15px; border-radius: 10px; border-left: 5px solid #2563EB; }
    div.stButton > button {
        width: 100%; background-color: #1E3A8A; color: white;
        font-weight: bold; font-size: 16px; padding: 10px; border-radius: 8px;
    }
    div.stButton > button:hover { background-color: #2563EB; color: white; }
    .login-container {
        max-width: 400px; margin: 0 auto; padding: 30px;
        background-color: #F8FAFC; border-radius: 10px; border: 1px solid #E2E8F0;
    }
    @keyframes blinker { 50% { opacity: 0.5; } }
    </style>
""", unsafe_allow_html=True)

HOJE_PROJETO = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)

# ========================================================
# CONEXÃO SUPABASE (via st.secrets)
# ========================================================
def conectar_banco():
    """
    Lê a URL de conexão dos Streamlit Secrets.
    No arquivo .streamlit/secrets.toml coloque:
      [supabase]
      url = "postgresql://postgres:[SENHA]@db.[REF].supabase.co:5432/postgres"
    """
    url = st.secrets["supabase"]["url"]
    conn = psycopg2.connect(url)
    conn.autocommit = False
    return conn

def hash_senha(senha: str) -> str:
    return hashlib.sha256(senha.encode()).hexdigest()

# ========================================================
# INICIALIZAÇÃO DAS TABELAS
# ========================================================
def inicializar_banco_de_dados():
    conn = conectar_banco()
    cursor = conn.cursor()

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS cronograma_macro (
            id SERIAL PRIMARY KEY,
            Obra TEXT,
            EDT TEXT UNIQUE,
            Tipo_Escopo TEXT,
            Etapa_Macro TEXT,
            Subdivisao TEXT,
            Tarefa TEXT,
            M2_Total_Tarefa REAL,
            Inicio_Previsto DATE,
            Termino_Obra DATE,
            Status TEXT DEFAULT 'Pendente',
            Status_Engenharia TEXT DEFAULT '🔴 Aguardando Medição In Loco',
            Prazo_Engenharia DATE,
            Data_Limite_Despacho DATE,
            Primeiro_Dia_Producao DATE
        )
    """)

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS itens_detalhado (
            id SERIAL PRIMARY KEY,
            Obra_Vinculada TEXT,
            EDT_Vinculado TEXT,
            Cod_Lote TEXT,
            Num_OP TEXT,
            Tipo_Material TEXT,
            Qtd_Caixas INTEGER,
            M2_Item REAL,
            Data_Producao_Programada DATE,
            Data_Limite_Obra DATE,
            Romaneio_Chapas TEXT,
            Status_Item TEXT DEFAULT 'Pendente',
            Dificuldade INTEGER DEFAULT 3,
            Fase_Produtiva TEXT,
            Enviado_Logistica INTEGER DEFAULT 0
        )
    """)

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS usuarios (
            id SERIAL PRIMARY KEY,
            usuario TEXT UNIQUE,
            nome TEXT,
            setor TEXT,
            senha TEXT
        )
    """)

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS solicitacoes_prazo (
            id SERIAL PRIMARY KEY,
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

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS logistica_envios (
            id SERIAL PRIMARY KEY,
            item_id INTEGER,
            Obra_Vinculada TEXT,
            EDT_Vinculado TEXT,
            Cod_Lote TEXT,
            Num_OP TEXT,
            Tipo_Material TEXT,
            Qtd_Caixas INTEGER,
            M2_Item REAL,
            Romaneio_Chapas TEXT,
            Data_Limite_Despacho DATE,
            Data_Envio_Agendado DATE,
            Transportadora TEXT,
            Veiculo TEXT,
            Observacoes TEXT,
            Status_Logistica TEXT DEFAULT 'Aguardando Agendamento',
            Confirmado_Por TEXT,
            Confirmado_Em TEXT
        )
    """)

    # Cria usuário master se não existir
    cursor.execute("SELECT COUNT(*) FROM usuarios")
    if cursor.fetchone()[0] == 0:
        cursor.execute(
            "INSERT INTO usuarios (usuario, nome, setor, senha) VALUES (%s, %s, %s, %s)",
            ('master', 'Joice Master', 'Master', hash_senha('Jv568279.'))
        )

    conn.commit()
    conn.close()

inicializar_banco_de_dados()

# ========================================================
# FUNÇÕES UTILITÁRIAS DE DATAS
# ========================================================
def subtrair_dias_uteis(data_base: datetime, n: int) -> datetime:
    data = data_base
    contados = 0
    while contados < n:
        data -= timedelta(days=1)
        if data.weekday() < 5:
            contados += 1
    return data

def calcular_cronograma_reverso(inicio_previsto, dias_logistica: int, dias_uteis_fabricacao: int, dias_antecedencia_eng: int = 3):
    dt = inicio_previsto if isinstance(inicio_previsto, datetime) \
         else datetime.combine(inicio_previsto, datetime.min.time())
    data_limite_despacho  = dt - timedelta(days=int(dias_logistica))
    primeiro_dia_producao = subtrair_dias_uteis(data_limite_despacho, int(dias_uteis_fabricacao))
    prazo_engenharia      = subtrair_dias_uteis(primeiro_dia_producao, int(dias_antecedencia_eng))
    return prazo_engenharia, primeiro_dia_producao, data_limite_despacho

def gerar_lotes_ordenados(primeiro_dia, data_despacho, dias_uteis_fab, total_cx, total_m2,
                           obra, edt, cod_lote, especificacao, txt_pav, dificuldade):
    """
    Gera 1 registro por dia útil, em ordem progressiva.
    FASE: os primeiros 50% dos dias = CORTE E USINAGEM (fase completa)
          os últimos 50% dos dias   = MONTAGEM FINAL (fase completa)
    A soma de caixas e m² fecha exatamente o total informado.
    """
    n = int(dias_uteis_fab)
    dias_corte    = n // 2          # primeira metade → CORTE
    cx_por_dia    = total_cx / n
    m2_por_dia    = total_m2 / n
    cx_acum = 0; m2_acum = 0.0
    lotes = []; dia = primeiro_dia; contados = 0

    while contados < n:
        if dia.weekday() in [5, 6]:
            dia += timedelta(days=1); continue
        contados += 1
        # CORTE nos primeiros dias, MONTAGEM nos últimos
        fase = "CORTE E USINAGEM" if contados <= dias_corte else "MONTAGEM FINAL"
        # Último lote recebe o saldo para fechar o total exato
        if contados == n:
            cx_dia = total_cx - cx_acum
            m2_dia = round(total_m2 - m2_acum, 2)
        else:
            cx_dia = max(1, round(cx_por_dia))
            m2_dia = round(m2_por_dia, 2)
        cx_acum += cx_dia; m2_acum += m2_dia
        lotes.append({
            "Obra_Vinculada": obra, "EDT_Vinculado": edt, "Cod_Lote": cod_lote,
            "Num_OP": None, "Tipo_Material": especificacao,
            "Qtd_Caixas": int(cx_dia), "M2_Item": float(m2_dia),
            "Data_Producao_Programada": dia.strftime('%Y-%m-%d'),
            "Data_Limite_Obra": data_despacho.strftime('%Y-%m-%d'),
            "Romaneio_Chapas": txt_pav, "Status_Item": "Pendente",
            "Dificuldade": int(dificuldade), "Fase_Produtiva": fase,
            "Enviado_Logistica": 0
        })
        dia += timedelta(days=1)
    return lotes

def prazo_valido(valor) -> bool:
    if valor is None: return False
    try: return not pd.isnull(valor)
    except: return False

# ========================================================
# FUNÇÕES DE BANCO — todas usando psycopg2 + %s
# ========================================================
def carregar_macro():
    conn = conectar_banco()
    df = pd.read_sql_query("SELECT * FROM cronograma_macro ORDER BY id", conn)
    conn.close()
    for col in ['inicio_previsto','termino_obra','prazo_engenharia',
                'data_limite_despacho','primeiro_dia_producao']:
        if col in df.columns:
            df[col] = pd.to_datetime(df[col], errors='coerce')
    # Normaliza nomes de colunas para o padrão do código
    df.columns = [c.replace('_',' ').title().replace(' ','_') if c != 'id' else c for c in df.columns]
    # Re-mapeia para os nomes exatos esperados
    rename = {
        'Inicio_Previsto':'Inicio_Previsto','Termino_Obra':'Termino_Obra',
        'Prazo_Engenharia':'Prazo_Engenharia','Data_Limite_Despacho':'Data_Limite_Despacho',
        'Primeiro_Dia_Producao':'Primeiro_Dia_Producao','Edt':'EDT',
        'M2_Total_Tarefa':'M2_Total_Tarefa','Status_Engenharia':'Status_Engenharia',
        'Tipo_Escopo':'Tipo_Escopo','Etapa_Macro':'Etapa_Macro',
    }
    df = df.rename(columns=rename)
    return df

def carregar_micro():
    conn = conectar_banco()
    df = pd.read_sql_query("SELECT * FROM itens_detalhado ORDER BY Data_Producao_Programada ASC", conn)
    conn.close()
    for col in ['data_producao_programada','data_limite_obra']:
        if col in df.columns:
            df[col] = pd.to_datetime(df[col], errors='coerce')
    df.columns = [c.replace('_',' ').title().replace(' ','_') if c != 'id' else c for c in df.columns]
    rename = {
        'Data_Producao_Programada':'Data_Producao_Programada',
        'Data_Limite_Obra':'Data_Limite_Obra','Edt_Vinculado':'EDT_Vinculado',
        'Obra_Vinculada':'Obra_Vinculada','Cod_Lote':'Cod_Lote',
        'Num_Op':'Num_OP','Tipo_Material':'Tipo_Material',
        'Qtd_Caixas':'Qtd_Caixas','M2_Item':'M2_Item',
        'Romaneio_Chapas':'Romaneio_Chapas','Status_Item':'Status_Item',
        'Fase_Produtiva':'Fase_Produtiva','Enviado_Logistica':'Enviado_Logistica',
    }
    df = df.rename(columns=rename)
    return df

def carregar_fila_logistica():
    conn = conectar_banco()
    df = pd.read_sql_query(
        "SELECT * FROM logistica_envios ORDER BY data_limite_despacho ASC NULLS LAST", conn)
    conn.close()
    for col in ['data_limite_despacho','data_envio_agendado']:
        if col in df.columns:
            df[col] = pd.to_datetime(df[col], errors='coerce')
    df.columns = [c.replace('_',' ').title().replace(' ','_') if c != 'id' else c for c in df.columns]
    rename = {
        'Data_Limite_Despacho':'Data_Limite_Despacho',
        'Data_Envio_Agendado':'Data_Envio_Agendado',
        'Obra_Vinculada':'Obra_Vinculada','Cod_Lote':'Cod_Lote',
        'Num_Op':'Num_OP','Tipo_Material':'Tipo_Material',
        'Qtd_Caixas':'Qtd_Caixas','M2_Item':'M2_Item',
        'Romaneio_Chapas':'Romaneio_Chapas',
        'Status_Logistica':'Status_Logistica',
        'Transportadora':'Transportadora','Veiculo':'Veiculo',
        'Observacoes':'Observacoes','Confirmado_Por':'Confirmado_Por',
        'Confirmado_Em':'Confirmado_Em','Item_Id':'item_id',
        'Edt_Vinculado':'EDT_Vinculado',
    }
    df = df.rename(columns=rename)
    return df

def carregar_solicitacoes():
    conn = conectar_banco()
    df = pd.read_sql_query("SELECT * FROM solicitacoes_prazo ORDER BY id DESC", conn)
    conn.close()
    return df

def salvar_lotes_micro(lotes: list):
    if not lotes: return
    conn = conectar_banco(); cursor = conn.cursor()
    for l in lotes:
        cursor.execute("""
            INSERT INTO itens_detalhado
            (Obra_Vinculada,EDT_Vinculado,Cod_Lote,Num_OP,Tipo_Material,
             Qtd_Caixas,M2_Item,Data_Producao_Programada,Data_Limite_Obra,
             Romaneio_Chapas,Status_Item,Dificuldade,Fase_Produtiva,Enviado_Logistica)
            VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)
        """, (l['Obra_Vinculada'],l['EDT_Vinculado'],l['Cod_Lote'],l['Num_OP'],
              l['Tipo_Material'],l['Qtd_Caixas'],l['M2_Item'],
              l['Data_Producao_Programada'],l['Data_Limite_Obra'],
              l['Romaneio_Chapas'],l['Status_Item'],l['Dificuldade'],
              l['Fase_Produtiva'],l['Enviado_Logistica']))
    conn.commit(); conn.close()

def deletar_lotes_por_edt_lote(obra, edt, cod_lote):
    conn = conectar_banco(); cursor = conn.cursor()
    if edt:
        cursor.execute(
            "DELETE FROM itens_detalhado WHERE Obra_Vinculada=%s AND EDT_Vinculado=%s AND Cod_Lote=%s",
            (obra, edt, cod_lote))
    else:
        cursor.execute(
            "DELETE FROM itens_detalhado WHERE Obra_Vinculada=%s AND Cod_Lote=%s",
            (obra, cod_lote))
    conn.commit(); conn.close()

def atualizar_cronograma_macro_datas(edt, prazo_eng, primeiro_prod, despacho):
    conn = conectar_banco(); cursor = conn.cursor()
    cursor.execute("""
        UPDATE cronograma_macro
        SET Prazo_Engenharia=%s, Primeiro_Dia_Producao=%s, Data_Limite_Despacho=%s
        WHERE EDT=%s
    """, (prazo_eng.strftime('%Y-%m-%d'), primeiro_prod.strftime('%Y-%m-%d'),
          despacho.strftime('%Y-%m-%d'), edt))
    conn.commit(); conn.close()

def atualizar_status_engenharia(edt_id, novo_status):
    conn = conectar_banco(); cursor = conn.cursor()
    cursor.execute("UPDATE cronograma_macro SET Status_Engenharia=%s WHERE id=%s", (novo_status, edt_id))
    conn.commit(); conn.close()

def salvar_solicitacao(edt, tarefa, prazo_atual, prazo_sol, justif, criado_por):
    conn = conectar_banco(); cursor = conn.cursor()
    cursor.execute("""
        INSERT INTO solicitacoes_prazo (edt,tarefa,prazo_atual,prazo_solicitado,justificativa,criado_por,status,criado_em)
        VALUES (%s,%s,%s,%s,%s,%s,'⏳ Pendente de Aprovação',%s)
    """, (edt, tarefa, prazo_atual, prazo_sol, justif, criado_por,
          datetime.now().strftime('%d/%m/%Y %H:%M')))
    conn.commit(); conn.close()

def atualizar_status_solicitacao(sol_id, novo_status):
    conn = conectar_banco(); cursor = conn.cursor()
    cursor.execute("UPDATE solicitacoes_prazo SET status=%s WHERE id=%s", (novo_status, sol_id))
    conn.commit(); conn.close()

def enviar_para_logistica(row, limite_despacho):
    conn = conectar_banco(); cursor = conn.cursor()
    cursor.execute("SELECT id FROM logistica_envios WHERE item_id=%s", (int(row['id']),))
    if cursor.fetchone():
        conn.close(); return
    cursor.execute("""
        INSERT INTO logistica_envios
        (item_id,Obra_Vinculada,EDT_Vinculado,Cod_Lote,Num_OP,Tipo_Material,
         Qtd_Caixas,M2_Item,Romaneio_Chapas,Data_Limite_Despacho,Status_Logistica)
        VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,'Aguardando Agendamento')
    """, (int(row['id']), row['Obra_Vinculada'], row['EDT_Vinculado'],
          row['Cod_Lote'], row.get('Num_OP') or '',
          row['Tipo_Material'], int(row['Qtd_Caixas']), float(row['M2_Item']),
          row['Romaneio_Chapas'],
          limite_despacho.strftime('%Y-%m-%d') if prazo_valido(limite_despacho) else None))
    cursor.execute("UPDATE itens_detalhado SET Enviado_Logistica=1 WHERE id=%s", (int(row['id']),))
    conn.commit(); conn.close()

def agendar_envio(log_id, data_envio, transportadora, veiculo, obs, usuario):
    conn = conectar_banco(); cursor = conn.cursor()
    cursor.execute("""
        UPDATE logistica_envios
        SET Data_Envio_Agendado=%s, Transportadora=%s, Veiculo=%s,
            Observacoes=%s, Status_Logistica='Envio Agendado'
        WHERE id=%s
    """, (data_envio.strftime('%Y-%m-%d') if data_envio else None,
          transportadora, veiculo, obs, log_id))
    conn.commit(); conn.close()

def confirmar_despacho(log_id, usuario):
    conn = conectar_banco(); cursor = conn.cursor()
    cursor.execute("""
        UPDATE logistica_envios
        SET Status_Logistica='Despachado ✅', Confirmado_Por=%s, Confirmado_Em=%s
        WHERE id=%s
    """, (usuario, datetime.now().strftime('%d/%m/%Y %H:%M'), log_id))
    conn.commit(); conn.close()

def verificar_login(usuario, senha):
    conn = conectar_banco(); cursor = conn.cursor()
    cursor.execute(
        "SELECT nome, setor FROM usuarios WHERE usuario=%s AND senha=%s",
        (usuario, hash_senha(senha)))
    resultado = cursor.fetchone()
    conn.close(); return resultado

def resetar_banco_dados_completo():
    conn = conectar_banco(); cursor = conn.cursor()
    for tabela in ['cronograma_macro','itens_detalhado','solicitacoes_prazo','logistica_envios']:
        cursor.execute(f"DELETE FROM {tabela}")
    conn.commit(); conn.close()

# ========================================================
# LOGIN
# ========================================================
if 'autenticado' not in st.session_state:
    st.session_state.autenticado   = False
    st.session_state.usuario_nome  = ""
    st.session_state.usuario_setor = ""

if not st.session_state.autenticado:
    st.markdown("<h1 style='text-align:center;color:#1E3A8A;'>Passold Sistemas</h1>", unsafe_allow_html=True)
    st.markdown("<h4 style='text-align:center;color:#6B7280;margin-bottom:30px;'>PCP & Controle Operacional</h4>", unsafe_allow_html=True)
    with st.container():
        st.markdown('<div class="login-container">', unsafe_allow_html=True)
        st.subheader("🔑 login do Sistema")
        user_input = st.text_input("Usuário:")
        pass_input = st.text_input("Senha:", type="password")
        if st.button("Entrar no PCP"):
            dados = verificar_login(user_input.strip(), pass_input)
            if dados:
                st.session_state.autenticado   = True
                st.session_state.usuario_nome  = dados[0]
                st.session_state.usuario_setor = dados[1]
                st.rerun()
            else:
                st.error("Usuário ou Senha inválidos.")
        st.markdown('</div>', unsafe_allow_html=True)
    st.stop()

# ========================================================
# HEADER
# ========================================================
ch1, ch2 = st.columns([4, 1])
with ch1:
    st.title("Passold - PCP Inteligente")
    st.caption(f"Usuário: **{st.session_state.usuario_nome}** | Setor: `{st.session_state.usuario_setor}`")
with ch2:
    st.write("")
    if st.button("🚪 Sair"):
        st.session_state.autenticado = False; st.rerun()

df_banco_macro = carregar_macro()
df_banco_micro = carregar_micro()

if not df_banco_macro.empty:
    obras_lista      = sorted(df_banco_macro['Obra'].unique().tolist())
    obra_selecionada = st.selectbox("Selecione a Obra de Trabalho:", obras_lista)
    df_macro_filtrado = df_banco_macro[df_banco_macro['Obra'] == obra_selecionada].copy()
else:
    obra_selecionada  = None
    df_macro_filtrado = pd.DataFrame()

# ========================================================
# ABAS
# ========================================================
setor = st.session_state.usuario_setor
abas_disponiveis = []
if setor in ["Master","Produção","Diretoria","Engenharia"]:
    abas_disponiveis.append("PAINEL DA TV (Chão de Fábrica)")
if setor in ["Master"]:
    abas_disponiveis.append("Liberar OPs da Semana")
if setor in ["Master","Diretoria"]:
    abas_disponiveis.append("Visão Macro (Diretoria)")
if setor in ["Master"]:
    abas_disponiveis.append("Vincular Datas (Materiais)")
    abas_disponiveis.append("Cadastrar Nova Obra")
if setor in ["Master","Engenharia"]:
    abas_disponiveis.append("Painel Técnico da Engenharia")
if setor in ["Master","Logística"]:
    abas_disponiveis.append("Painel de Logística")
if setor in ["Master"]:
    abas_disponiveis.append("Configurações do Sistema")

with st.container():
    abas_objetos = st.tabs(abas_disponiveis)

for nome_aba, aba_objeto in zip(abas_disponiveis, abas_objetos):

    # ==================================================
    # PAINEL DA TV
    # ==================================================
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
                    cal     = py_calendar.Calendar(firstweekday=6)
                    semanas = cal.monthdatescalendar(st.session_state.prog_ano, st.session_state.prog_mes)

                    # Cabeçalho e dias sempre numa única chamada st.columns(7) por linha
                    nomes_dias = ["Dom","Seg","Ter","Qua","Qui","Sex","Sáb"]
                    cols_h = st.columns(7)
                    for i, nome in enumerate(nomes_dias):
                        cols_h[i].markdown(f"<div style='text-align:center;font-weight:bold;color:#475569;padding:4px 0;'>{nome}</div>", unsafe_allow_html=True)

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
                                        st.markdown(f"<div style='background:{bg};border:1px solid {bd};padding:5px;border-radius:6px;text-align:center;height:70px;'><span style='color:#94A3B8;font-size:15px;'>{data_dia.day}</span><br><span style='color:#CBD5E1;font-size:10px;'>—</span></div>", unsafe_allow_html=True)
                                else:
                                    st.markdown('<div style="height:70px;"></div>', unsafe_allow_html=True)

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
                                    st.markdown(f"**Material:** {row['Tipo_Material']} | **Fase:** `{row.get('Fase_Produtiva','—')}` | `{int(row['Qtd_Caixas'])} cx` ({row['M2_Item']:.2f} m²)")
                                    desp_txt = pd.to_datetime(row['Data_Limite_Obra']).strftime('%d/%m/%Y') if prazo_valido(row['Data_Limite_Obra']) else "—"
                                    st.caption(f"Pavimentos: {row['Romaneio_Chapas']} | Despacho: {desp_txt}")
                                with ca:
                                    st.write("")
                                    if st.button("✅ PRONTO", key=f"baixa_{row['id']}", type="primary", use_container_width=True):
                                        limite_desp = None
                                        if not df_banco_macro.empty:
                                            fr = df_banco_macro[df_banco_macro['EDT'] == row['EDT_Vinculado']]
                                            if not fr.empty:
                                                limite_desp = fr.iloc[0].get('Data_Limite_Despacho')
                                        conn = conectar_banco(); cursor = conn.cursor()
                                        cursor.execute("UPDATE itens_detalhado SET Status_Item='Concluído' WHERE id=%s", (row['id'],))
                                        conn.commit(); conn.close()
                                        enviar_para_logistica(row, limite_desp if prazo_valido(limite_desp) else pd.NaT)
                                        st.toast(f"✅ Lote {row['Cod_Lote']} concluído → enviado para Logística! 🚚")
                                        time.sleep(0.3); st.rerun()
                else:
                    st.success("🙌 Sem ordens liberadas para este filtro.")
            else:
                st.info("Nenhum lote liberado no sistema ainda.")

    # ==================================================
    # LIBERAR OPS
    # ==================================================
    elif nome_aba == "Liberar OPs da Semana":
        with aba_objeto:
            st.header("Gerenciador de Ordens de Produção Semanais")
            if obra_selecionada and not df_banco_micro.empty:
                df_pend = df_banco_micro[
                    (df_banco_micro['Obra_Vinculada'] == obra_selecionada) &
                    (df_banco_micro['Status_Item'] == "Pendente")].copy()

                if not df_pend.empty:
                    df_pend['Selecionar'] = False
                    cols_exib = [c for c in ['id','Cod_Lote','Tipo_Material','Qtd_Caixas','M2_Item',
                                              'Fase_Produtiva','Data_Producao_Programada','Romaneio_Chapas','Selecionar']
                                 if c in df_pend.columns]
                    df_ed = st.data_editor(df_pend[cols_exib], hide_index=True, use_container_width=True,
                                           disabled=[c for c in cols_exib if c != 'Selecionar'])
                    ids_sel  = df_ed[df_ed['Selecionar'] == True]['id'].tolist()
                    prefixo  = st.text_input("Prefixo da OP:", value=f"OP-{datetime.now().strftime('%Y')}-")
                    if st.button("Liberar Selecionados para a TV"):
                        if ids_sel:
                            conn = conectar_banco(); cursor = conn.cursor()
                            for item_id in ids_sel:
                                cursor.execute(
                                    "UPDATE itens_detalhado SET Status_Item='Liberado para Fábrica', Num_OP=%s WHERE id=%s",
                                    (f"{prefixo}{str(item_id).zfill(3)}", item_id))
                            conn.commit(); conn.close()
                            st.toast("OPs liberadas!", icon="✅"); time.sleep(0.5); st.rerun()
                        else:
                            st.warning("Selecione pelo menos um item.")
                else:
                    st.success("Todos os lotes já foram liberados.")
            else:
                st.info("Nenhum lote pendente encontrado.")

    # ==================================================
    # VISÃO MACRO
    # ==================================================
    elif nome_aba == "Visão Macro (Diretoria)":
        with aba_objeto:
            st.header("📊 Dashboard Executivo")
            df_dir = df_banco_micro[df_banco_micro['Obra_Vinculada'] == obra_selecionada].copy() \
                     if obra_selecionada and not df_banco_micro.empty else df_banco_micro.copy()

            if not df_dir.empty:
                data_max = df_dir['Data_Limite_Obra'].max()
                c1, c2, c3 = st.columns(3)
                c1.metric("Metragem Total", f"{df_dir['M2_Item'].sum():,.2f} m²")
                c2.metric("Subdivisões", f"{df_dir['EDT_Vinculado'].nunique()} frentes")
                c3.metric("Prazo Despacho Mais Distante", data_max.strftime('%d/%m/%Y') if prazo_valido(data_max) else "N/A")

                st.markdown("---")
                st.subheader("📈 Carga Semanal")
                df_lib = df_dir[df_dir['Status_Item'].isin(["Liberado para Fábrica","Produção","Concluído"])].copy()
                if not df_lib.empty:
                    df_lib['Ano_Semana'] = df_lib['Data_Producao_Programada'].dt.isocalendar().year
                    df_lib['Num_Semana'] = df_lib['Data_Producao_Programada'].dt.isocalendar().week
                    def fmt_sem(r):
                        try:
                            s = pd.to_datetime(f"{int(r['Ano_Semana'])}-W{int(r['Num_Semana'])}-1", format="%G-W%V-%u")
                            return f"Semana {int(r['Num_Semana']):02d} ({s.strftime('%d/%m')} – {(s+timedelta(days=6)).strftime('%d/%m/%Y')})"
                        except: return f"Semana {r['Num_Semana']}"
                    df_lib['Período'] = df_lib.apply(fmt_sem, axis=1)
                    res = df_lib.groupby(['Ano_Semana','Num_Semana','Período','Obra_Vinculada']).agg(
                        Lotes=('id','count'), Caixas=('Qtd_Caixas','sum'), M2=('M2_Item','sum'),
                        Evolucao=('Status_Item', lambda x: f"{(x=='Concluído').sum()/len(x)*100:.0f}% concluído")
                    ).reset_index().sort_values(['Ano_Semana','Num_Semana'])
                    res.columns = ['Ano','Sem','Período','Obra','Lotes','Caixas','Volume (m²)','Evolução']
                    st.dataframe(res[['Período','Obra','Lotes','Caixas','Volume (m²)','Evolução']], hide_index=True, use_container_width=True)
                else:
                    st.warning("Nenhuma OP liberada ainda.")

                st.subheader("📊 Gantt")
                df_gantt = df_dir.groupby(['Obra_Vinculada','EDT_Vinculado','Romaneio_Chapas']).agg(
                    Inicio=('Data_Producao_Programada','min'), Fim=('Data_Limite_Obra','max'), M2=('M2_Item','sum')
                ).reset_index().dropna(subset=['Inicio','Fim'])
                if not df_gantt.empty:
                    fig = px.timeline(df_gantt, x_start="Inicio", x_end="Fim", y="EDT_Vinculado",
                                      color="Obra_Vinculada", hover_data=["Romaneio_Chapas","M2"],
                                      title="Ocupação Fábrica vs Prazo Despacho")
                    fig.update_yaxes(autorange="reversed")
                    fig.update_layout(height=400, margin=dict(l=20,r=20,t=40,b=20))
                    st.plotly_chart(fig, use_container_width=True)
            else:
                st.info("Nenhum dado encontrado.")

    # ==================================================
    # VINCULAR DATAS
    # ==================================================
    elif nome_aba == "Vincular Datas (Materiais)":
        with aba_objeto:
            st.header("Inteligência Temporal: Fatiamento de Lotes")
            if st.session_state.get('lote_salvo_sucesso'):
                st.success("✅ Lote gerado com sucesso!")
                st.session_state.lote_salvo_sucesso = False

            if obra_selecionada and not df_macro_filtrado.empty:
                opcoes_edt = []
                mapa_rows  = {}
                for _, row in df_macro_filtrado.iterrows():
                    sub   = f" [{row['Subdivisao']}]" if row.get('Subdivisao') else ""
                    label = f"{row['EDT']} - {row['Tarefa']}{sub}"
                    opcoes_edt.append(label); mapa_rows[label] = row

                st.markdown("### 🛠️ Criar Nova Entrega")
                st.caption("Cada entrega é um lote independente. Você define quantas caixas quer prontas e até quando — o sistema calcula tudo retroativamente.")

                with st.form("form_fatiamento"):
                    c1, c2 = st.columns(2)
                    with c1:
                        edt_sel  = st.selectbox("Frente (EDT):", opcoes_edt)
                        row_sel  = mapa_rows[edt_sel]
                        edt_puro = edt_sel.split(" - ")[0].strip()
                        cod_lote = st.text_input("Nome desta Entrega (ex: LOTE 1, ENTREGA A):")
                        txt_pav  = st.text_area("Pavimentos / Destino:", value="Pav 39 ao 43")
                        espec    = st.text_input("Material:", value="ACM BRANCO")

                    with c2:
                        # ÂNCORA: data que você quer o material NA OBRA
                        inicio_prev = row_sel['Inicio_Previsto']
                        data_alvo_default = pd.to_datetime(inicio_prev).date() if prazo_valido(inicio_prev) else (datetime.now() + timedelta(days=30)).date()

                        data_alvo_obra = st.date_input(
                            "📅 Data que precisa estar na obra:",
                            value=data_alvo_default,
                            format="DD/MM/YYYY",
                            help="Âncora do cálculo — tudo é calculado retroativamente a partir desta data"
                        )
                        dias_log = st.number_input("Dias de logística/transporte (corridos):", min_value=1, value=3,
                                                   help="Quantos dias entre sair da fábrica e chegar na obra")
                        dias_fab = st.number_input("Dias úteis de produção:", min_value=1, value=10,
                                                   help="Quantos dias úteis a fábrica precisa para produzir esta entrega")
                        total_cx = st.number_input("Quantidade de caixas desta entrega:", min_value=1, value=24)
                        total_m2 = st.number_input("Metragem desta entrega (m²):", min_value=0.1, value=50.0)
                        dific    = st.selectbox("Complexidade:", [1,2,3,4,5], index=2)

                        # Preview do cronograma calculado retroativamente
                        dt_alvo   = datetime.combine(data_alvo_obra, datetime.min.time())
                        despacho  = dt_alvo - timedelta(days=int(dias_log))
                        prim_prod = subtrair_dias_uteis(despacho, int(dias_fab))

                        st.markdown("---")
                        st.success(
                            f"🗓️ **Cronograma desta entrega:**\n\n"
                            f"🏭 Começa produção: **{prim_prod.strftime('%d/%m/%Y')}**\n\n"
                            f"🚚 Sai da fábrica: **{despacho.strftime('%d/%m/%Y')}**\n\n"
                            f"🏗️ Chega na obra: **{data_alvo_obra.strftime('%d/%m/%Y')}**"
                        )

                    if "🟢" not in str(row_sel.get('Status_Engenharia','')):
                        st.warning(f"⚠️ Engenharia ainda não liberou: `{row_sel.get('Status_Engenharia','—')}`")

                    if st.form_submit_button("✅ Gerar Esta Entrega"):
                        if not cod_lote.strip():
                            st.error("Digite o nome desta entrega.")
                        else:
                            dt_alvo_calc  = datetime.combine(data_alvo_obra, datetime.min.time())
                            despacho_calc = dt_alvo_calc - timedelta(days=int(dias_log))
                            prim_prod_calc = subtrair_dias_uteis(despacho_calc, int(dias_fab))

                            # Apaga lotes anteriores do mesmo EDT+Lote (evita duplicata se refazer)
                            deletar_lotes_por_edt_lote(obra_selecionada, edt_puro, cod_lote.strip())

                            lotes = gerar_lotes_ordenados(
                                prim_prod_calc, despacho_calc, dias_fab,
                                int(total_cx), float(total_m2),
                                obra_selecionada, edt_puro, cod_lote.strip(),
                                espec, txt_pav, dific
                            )
                            salvar_lotes_micro(lotes)

                            # Atualiza o cronograma macro com a data de despacho desta entrega
                            # (usa a mais próxima como referência para o prazo de engenharia)
                            prazo_eng = subtrair_dias_uteis(prim_prod_calc, 3)
                            atualizar_cronograma_macro_datas(edt_puro, prazo_eng, prim_prod_calc, despacho_calc)

                            st.session_state.lote_salvo_sucesso = True
                            st.rerun()

                st.markdown("---")
                st.markdown("### 📝 Lotes Gerados")
                df_ed_raw = carregar_micro()
                if not df_ed_raw.empty:
                    df_obra = df_ed_raw[df_ed_raw['Obra_Vinculada'] == obra_selecionada].copy()
                    if not df_obra.empty:
                        df_obra['Data_Producao_Programada'] = df_obra['Data_Producao_Programada'].dt.strftime('%Y-%m-%d')
                        df_obra['Data_Limite_Obra']         = df_obra['Data_Limite_Obra'].dt.strftime('%Y-%m-%d')
                        df_str = df_obra.copy()
                        df_edit = st.data_editor(df_str, key="editor_lotes", hide_index=True,
                                                 use_container_width=True, disabled=["id","Obra_Vinculada","Num_OP"])
                        alteradas = [df_edit.loc[i] for i in df_edit.index if not df_edit.loc[i].equals(df_str.loc[i])]
                        if alteradas:
                            conn = conectar_banco(); cursor = conn.cursor()
                            for row in alteradas:
                                cursor.execute("""
                                    UPDATE itens_detalhado
                                    SET Cod_Lote=%s,Tipo_Material=%s,Qtd_Caixas=%s,M2_Item=%s,
                                        Data_Producao_Programada=%s,Data_Limite_Obra=%s,
                                        Romaneio_Chapas=%s,Status_Item=%s,Dificuldade=%s,Fase_Produtiva=%s
                                    WHERE id=%s
                                """, (row['Cod_Lote'],row['Tipo_Material'],int(row['Qtd_Caixas']),float(row['M2_Item']),
                                      row['Data_Producao_Programada'],row['Data_Limite_Obra'],
                                      row['Romaneio_Chapas'],row['Status_Item'],int(row['Dificuldade']),
                                      row['Fase_Produtiva'],int(row['id'])))
                            conn.commit(); conn.close()
                            st.toast("Salvo!", icon="💾"); time.sleep(0.3); st.rerun()

                        st.markdown("#### 🗑️ Remover Lote")
                        lote_del = st.selectbox("Lote para excluir:", df_obra['Cod_Lote'].unique().tolist())
                        if st.button(f"Excluir Lote {lote_del}"):
                            deletar_lotes_por_edt_lote(obra_selecionada, None, lote_del)
                            st.toast(f"Lote {lote_del} removido!", icon="🗑️"); time.sleep(0.5); st.rerun()
                    else:
                        st.info("Nenhum lote fatiado ainda.")

    # ==================================================
    # CADASTRAR OBRA
    # ==================================================
    elif nome_aba == "Cadastrar Nova Obra":
        with aba_objeto:
            st.header("Cadastrar Nova Obra")
            for k,v in [('mem_obra',''),('mem_frente',''),('mem_tarefa',''),
                        ('mem_dt_ini',datetime.now().date()),
                        ('mem_dt_fim',(datetime.now()+timedelta(days=90)).date())]:
                if k not in st.session_state: st.session_state[k] = v

            with st.form("form_obra"):
                nome_obra = st.text_input("Nome da Obra:", value=st.session_state.mem_obra).upper()
                co1, co2  = st.columns(2)
                with co1:
                    escopo = st.selectbox("Escopo:", ["ACM","Vidro/Esquadria"])
                    frente = st.text_input("Frente Macro:", value=st.session_state.mem_frente)
                    tarefa = st.text_input("Nome da Tarefa:", value=st.session_state.mem_tarefa)
                with co2:
                    edt_cod = st.text_input("Código EDT (único):")
                    subdiv  = st.text_input("Subdivisão / Balancim:").upper()
                    m2_tot  = st.number_input("Metragem (m²):", min_value=0.1, value=100.0)
                cd1, cd2 = st.columns(2)
                with cd1:
                    dt_ini = st.date_input("📅 Início Instalação (âncora do PCP):",
                                           value=st.session_state.mem_dt_ini, format="DD/MM/YYYY")
                with cd2:
                    dt_fim = st.date_input("Prazo Máximo Obra:", value=st.session_state.mem_dt_fim, format="DD/MM/YYYY")

                if st.form_submit_button("Registrar Frente"):
                    if not all([nome_obra.strip(), edt_cod.strip(), tarefa.strip(), subdiv.strip()]):
                        st.error("Preencha todos os campos.")
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
                                VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,'Pendente','🔴 Aguardando Medição In Loco')
                            """, (nome_obra,edt_cod,escopo,frente,subdiv,tarefa,float(m2_tot),
                                  dt_ini.strftime('%Y-%m-%d'),dt_fim.strftime('%Y-%m-%d')))
                            conn.commit()
                            st.toast("Frente registrada!", icon="🚀"); time.sleep(0.4); st.rerun()
                        except Exception as e:
                            st.error(f"EDT '{edt_cod}' já existe ou erro: {e}")
                        finally:
                            conn.close()

            if not df_banco_macro.empty:
                st.markdown("---")
                st.markdown("### 📋 Frentes Cadastradas")
                df_show = df_banco_macro.copy()
                for col in ['Inicio_Previsto','Termino_Obra']:
                    if col in df_show.columns:
                        df_show[col] = pd.to_datetime(df_show[col], errors='coerce').dt.strftime('%d/%m/%Y')
                cols_s = [c for c in ['Obra','EDT','Subdivisao','Tarefa','M2_Total_Tarefa',
                                       'Inicio_Previsto','Termino_Obra','Status_Engenharia'] if c in df_show.columns]
                st.dataframe(df_show[cols_s], hide_index=True, use_container_width=True)

    # ==================================================
    # PAINEL DA ENGENHARIA
    # ==================================================
    elif nome_aba == "Painel Técnico da Engenharia":
        with aba_objeto:
            st.header("🏗️ Painel Técnico da Engenharia")
            st.caption(f"Hoje: {HOJE_PROJETO.strftime('%d/%m/%Y')} | Obra: **{obra_selecionada or 'Nenhuma'}**")

            df_eng = carregar_macro()
            if obra_selecionada:
                df_eng = df_eng[df_eng['Obra'] == obra_selecionada]
            else:
                df_eng = pd.DataFrame()

            ESTADOS = ["🔴 Aguardando Medição In Loco","🟡 Medição Realizada — Em Projetos",
                       "🔵 Projetos em Revisão Interna","🟢 Projetos Liberados para o PCP","⚪ Arquivado / Concluído"]

            def classificar(dias_rest, status_tec):
                if status_tec == "🟢 Projetos Liberados para o PCP": return "concluido","✅ Liberado para o PCP",None
                if dias_rest is None: return "sem_prazo","⚪ Aguardando programação pelo PCP",None
                if dias_rest < 0:    return "vencido",f"🔴 VENCIDO há {abs(int(dias_rest))} dias",abs(int(dias_rest))
                if dias_rest <= 7:   return "critico",f"🟡 Crítico — faltam {int(dias_rest)} dias",int(dias_rest)
                return "ok",f"🟢 Dentro do prazo ({int(dias_rest)} dias)",int(dias_rest)

            frentes = []
            if not df_eng.empty:
                for _, row in df_eng.iterrows():
                    prazo_raw = row.get('Prazo_Engenharia')
                    prazo_eng = prazo_raw if prazo_valido(prazo_raw) else None
                    dias_rest = (pd.to_datetime(prazo_eng) - HOJE_PROJETO).days if prazo_eng is not None else None
                    sk,st_txt,dias_num = classificar(dias_rest, row.get('Status_Engenharia', ESTADOS[0]))
                    frentes.append({
                        "id":row['id'],"edt":row['EDT'],"tarefa":row['Tarefa'],
                        "subdivisao":row.get('Subdivisao',''),"tipo_escopo":row.get('Tipo_Escopo',''),
                        "inicio_previsto":row.get('Inicio_Previsto'),
                        "despacho":row.get('Data_Limite_Despacho'),
                        "primeiro_prod":row.get('Primeiro_Dia_Producao'),
                        "termino_obra":row.get('Termino_Obra'),
                        "m2":row.get('M2_Total_Tarefa',0.0),
                        "prazo_eng":prazo_eng,"dias_restantes":dias_rest,
                        "situacao_key":sk,"situacao_txt":st_txt,"dias_num":dias_num,
                        "status_tecnico":row.get('Status_Engenharia',ESTADOS[0]),
                    })

            criticas = [f for f in frentes if f['situacao_key'] in ('critico','vencido')]

            with st.expander(f"🚨 Frentes Críticas — {len(criticas)} alerta(s)", expanded=True):
                if not criticas:
                    st.success("✅ Tudo dentro do prazo!")
                else:
                    for fr in sorted(criticas, key=lambda x: x['dias_restantes'] or 0):
                        with st.container(border=True):
                            ci,cc = st.columns([7,3])
                            with ci:
                                sub = f" · {fr['subdivisao']}" if fr['subdivisao'] else ""
                                st.markdown(f"### {fr['tarefa']}{sub}")
                                cm1,cm2 = st.columns(2)
                                with cm1:
                                    st.write(f"📌 EDT: `{fr['edt']}`")
                                    ini = pd.to_datetime(fr['inicio_previsto']).strftime('%d/%m/%Y') if prazo_valido(fr['inicio_previsto']) else "—"
                                    st.write(f"📅 Início instalação: {ini}")
                                    pp = pd.to_datetime(fr['primeiro_prod']).strftime('%d/%m/%Y') if prazo_valido(fr['primeiro_prod']) else "—"
                                    st.write(f"🏭 1º dia produção: {pp}")
                                with cm2:
                                    pe = pd.to_datetime(fr['prazo_eng']).strftime('%d/%m/%Y') if fr['prazo_eng'] else "—"
                                    st.write(f"📐 Prazo engenharia: `{pe}`")
                                    dp = pd.to_datetime(fr['despacho']).strftime('%d/%m/%Y') if prazo_valido(fr['despacho']) else "—"
                                    st.write(f"🚚 Despacho: {dp}")
                                st.write(f"🔧 {fr['status_tecnico']}")
                            with cc:
                                if fr['situacao_key']=='vencido': st.error(f"⏰ VENCIDO\n\n**{fr['dias_num']} dias**")
                                else: st.warning(f"⏳ FALTAM\n\n**{fr['dias_num']} dias**")
                            st.markdown("---")
                            ca1,ca2 = st.columns(2)
                            with ca1:
                                idx = ESTADOS.index(fr['status_tecnico']) if fr['status_tecnico'] in ESTADOS else 0
                                ns  = st.selectbox("Atualizar:", ESTADOS, index=idx, key=f"cs_{fr['id']}")
                            with ca2:
                                st.write(""); st.write("")
                                if st.button("💾 Salvar", key=f"cb_{fr['id']}", use_container_width=True):
                                    atualizar_status_engenharia(fr['id'], ns)
                                    st.toast("Atualizado!", icon="✅"); time.sleep(0.3); st.rerun()

            with st.expander(f"📋 Todas as Frentes — {len(frentes)}", expanded=False):
                if not frentes:
                    st.info("Nenhuma frente cadastrada.")
                else:
                    cf1,cf2 = st.columns([3,2])
                    with cf1: filt_st = st.selectbox("Status:", ["Todos"]+ESTADOS, key="eng_fst")
                    with cf2: filt_sit = st.radio("Situação:", ["Todas","Críticas","Liberadas"], horizontal=True, key="eng_fsi")
                    exibir = frentes.copy()
                    if filt_st != "Todos": exibir = [f for f in exibir if f['status_tecnico']==filt_st]
                    if filt_sit=="Críticas": exibir = [f for f in exibir if f['situacao_key'] in ('critico','vencido')]
                    elif filt_sit=="Liberadas": exibir = [f for f in exibir if f['situacao_key']=='concluido']
                    st.markdown(f"**{len(exibir)} frente(s)**"); st.markdown("---")
                    for fr in exibir:
                        with st.container(border=True):
                            ci,cd,ca = st.columns([5,3,2])
                            with ci:
                                sub = f" · *{fr['subdivisao']}*" if fr['subdivisao'] else ""
                                st.markdown(f"**{fr['tarefa']}**{sub}")
                                st.caption(f"EDT: {fr['edt']} | {fr['tipo_escopo']} | {fr['m2']:,.2f} m²")
                                st.write(fr['status_tecnico'])
                            with cd:
                                ini = pd.to_datetime(fr['inicio_previsto']).strftime('%d/%m/%Y') if prazo_valido(fr['inicio_previsto']) else "—"
                                st.caption("📅 Início instalação"); st.write(ini)
                                pe = pd.to_datetime(fr['prazo_eng']).strftime('%d/%m/%Y') if fr['prazo_eng'] else "—"
                                st.caption("📐 Prazo PCP"); st.write(f"`{pe}`")
                                dp = pd.to_datetime(fr['despacho']).strftime('%d/%m/%Y') if prazo_valido(fr['despacho']) else "—"
                                st.caption("🚚 Despacho"); st.write(dp)
                            with ca:
                                sk=fr['situacao_key']
                                if sk=='vencido': st.error(fr['situacao_txt'])
                                elif sk=='critico': st.warning(fr['situacao_txt'])
                                elif sk in ('concluido','ok'): st.success(fr['situacao_txt'])
                                else: st.info(fr['situacao_txt'])
                            cs,cb = st.columns([4,1])
                            with cs:
                                idx = ESTADOS.index(fr['status_tecnico']) if fr['status_tecnico'] in ESTADOS else 0
                                ns  = st.selectbox("", ESTADOS, index=idx, key=f"as_{fr['id']}", label_visibility="collapsed")
                            with cb:
                                if st.button("💾", key=f"ab_{fr['id']}", use_container_width=True):
                                    atualizar_status_engenharia(fr['id'], ns)
                                    st.toast("Atualizado!"); time.sleep(0.3); st.rerun()

            df_sols  = carregar_solicitacoes()
            n_pend   = len(df_sols[df_sols['status']=='⏳ Pendente de Aprovação']) if not df_sols.empty else 0
            with st.expander(f"📝 Solicitações de Prazo{f' — {n_pend} pendente(s)' if n_pend else ''}", expanded=False):
                nao_lib = [f for f in frentes if f['situacao_key']!='concluido']
                if setor in ["Engenharia","Master"] and nao_lib:
                    st.markdown("#### ✍️ Nova Solicitação")
                    cs1,cs2 = st.columns(2)
                    with cs1:
                        opts = [f"{f['edt']} — {f['tarefa']}" for f in nao_lib]
                        sel  = st.selectbox("Frente:", opts, key="sol_fr")
                        fobj = nao_lib[opts.index(sel)]
                        pat  = pd.to_datetime(fobj['prazo_eng']).strftime('%d/%m/%Y') if fobj['prazo_eng'] else "Não definido"
                        st.info(f"Prazo atual: **{pat}**")
                    with cs2:
                        nps = st.date_input("Novo prazo:", format="DD/MM/YYYY", key="sol_np",
                                            value=(pd.to_datetime(fobj['prazo_eng'])+timedelta(days=7)).date() if fobj['prazo_eng'] else HOJE_PROJETO.date())
                        jus = st.text_area("Justificativa:", key="sol_jus")
                    if st.button("📤 Enviar", key="sol_env"):
                        if not jus.strip(): st.error("Informe a justificativa.")
                        else:
                            salvar_solicitacao(fobj['edt'],fobj['tarefa'],pat,nps.strftime('%d/%m/%Y'),jus.strip(),st.session_state.usuario_nome)
                            st.success("Enviado!"); st.rerun()
                st.markdown("---")
                if setor=="Master" and not df_sols.empty:
                    pend = df_sols[df_sols['status']=='⏳ Pendente de Aprovação']
                    if pend.empty: st.info("Nenhuma pendente.")
                    else:
                        for _,sol in pend.iterrows():
                            with st.container(border=True):
                                sa,sb = st.columns([4,2])
                                with sa:
                                    st.markdown(f"**{sol['tarefa']}** — `{sol['edt']}`")
                                    st.write(f"`{sol['prazo_atual']}` → `{sol['prazo_solicitado']}`")
                                    st.caption(f"*{sol['justificativa']}* | {sol['criado_por']} em {sol['criado_em']}")
                                with sb:
                                    cap,cre = st.columns(2)
                                    with cap:
                                        if st.button("✅",key=f"ap_{sol['id']}",use_container_width=True):
                                            atualizar_status_solicitacao(sol['id'],"✅ Aprovado"); st.rerun()
                                    with cre:
                                        if st.button("❌",key=f"rj_{sol['id']}",use_container_width=True):
                                            atualizar_status_solicitacao(sol['id'],"❌ Rejeitado"); st.rerun()
                if not df_sols.empty:
                    hist = df_sols[df_sols['status']!='⏳ Pendente de Aprovação']
                    if not hist.empty:
                        st.markdown("#### 📂 Histórico")
                        for _,sol in hist.iterrows():
                            st.caption(f"{sol['status']} | **{sol['tarefa']}** | {sol['prazo_solicitado']} | {sol['criado_por']}")

            with st.expander("🔍 Carga da Fábrica por Semana", expanded=False):
                df_fab = df_banco_micro[df_banco_micro['Status_Item']=="Liberado para Fábrica"].copy() if not df_banco_micro.empty else pd.DataFrame()
                if not df_fab.empty:
                    df_fab['Ano_Semana'] = df_fab['Data_Producao_Programada'].dt.isocalendar().year
                    df_fab['Num_Semana'] = df_fab['Data_Producao_Programada'].dt.isocalendar().week
                    def fmt_s(r):
                        try:
                            s = pd.to_datetime(f"{int(r['Ano_Semana'])}-W{int(r['Num_Semana'])}-1",format="%G-W%V-%u")
                            return f"Semana {int(r['Num_Semana']):02d} ({s.strftime('%d/%m')} – {(s+timedelta(days=6)).strftime('%d/%m')})"
                        except: return f"Semana {r['Num_Semana']}"
                    df_fab['Período'] = df_fab.apply(fmt_s,axis=1)
                    res_fab = df_fab.groupby(['Ano_Semana','Num_Semana','Período','Obra_Vinculada']).agg(
                        Caixas=('Qtd_Caixas','sum'),M2=('M2_Item','sum')).reset_index().sort_values(['Ano_Semana','Num_Semana'])
                    res_fab.columns=['Ano','Sem','Período','Obra','Caixas (cx)','Metragem (m²)']
                    st.dataframe(res_fab[['Período','Obra','Caixas (cx)','Metragem (m²)']],hide_index=True,use_container_width=True)
                else:
                    st.success("🌴 Fábrica livre!")

    # ==================================================
    # PAINEL DE LOGÍSTICA
    # ==================================================
    elif nome_aba == "Painel de Logística":
        with aba_objeto:
            st.header("🚚 Painel de Logística — Gestão de Despachos")
            st.caption(f"Hoje: {HOJE_PROJETO.strftime('%d/%m/%Y')}")
            df_log = carregar_fila_logistica()

            if not df_log.empty:
                n_aguard   = len(df_log[df_log['Status_Logistica']=='Aguardando Agendamento'])
                n_agendado = len(df_log[df_log['Status_Logistica']=='Envio Agendado'])
                n_despach  = len(df_log[df_log['Status_Logistica']=='Despachado ✅'])
                df_ativos  = df_log[df_log['Status_Logistica']!='Despachado ✅']
                n_atrasado = len(df_ativos[df_ativos['Data_Limite_Despacho'].apply(lambda x: prazo_valido(x) and pd.to_datetime(x)<HOJE_PROJETO)]) if not df_ativos.empty else 0
                c1,c2,c3,c4 = st.columns(4)
                c1.metric("⏳ Aguardando Agendamento", n_aguard)
                c2.metric("📅 Envios Agendados",       n_agendado)
                c3.metric("✅ Despachados",             n_despach)
                if n_atrasado>0: c4.metric("🔴 Atrasados",n_atrasado,delta=f"-{n_atrasado}",delta_color="inverse")
                else: c4.metric("🟢 Sem Atrasos","OK")
            else:
                st.info("📭 Nenhum lote na fila. Quando a produção marcar PRONTO, aparece aqui automaticamente.")

            st.markdown("---")

            with st.expander("⚠️ Fila Prioritária — Aguardando Agendamento", expanded=True):
                if df_log.empty or df_log[df_log['Status_Logistica']=='Aguardando Agendamento'].empty:
                    st.success("✅ Todos os lotes já agendados!")
                else:
                    df_ag = df_log[df_log['Status_Logistica']=='Aguardando Agendamento'].copy().sort_values('Data_Limite_Despacho',na_position='last')
                    for _,row in df_ag.iterrows():
                        prazo_d = row['Data_Limite_Despacho']
                        if prazo_valido(prazo_d):
                            dias_r = (pd.to_datetime(prazo_d) - HOJE_PROJETO).days
                            if dias_r<0:    cor="#FEE2E2";bord="#EF4444";tag=f"🔴 ATRASADO {abs(dias_r)}d"
                            elif dias_r<=3: cor="#FEF9C3";bord="#EAB308";tag=f"🟡 URGENTE — {dias_r}d"
                            else:           cor="#F0FDF4";bord="#22C55E";tag=f"🟢 {dias_r}d restantes"
                        else:
                            cor="#F8FAFC";bord="#CBD5E1";tag="⚪ Sem prazo"
                        st.markdown(f"<div style='border-left:5px solid {bord};background:{cor};padding:12px 16px;border-radius:6px;margin-bottom:8px;'>", unsafe_allow_html=True)
                        ci,cp,ca = st.columns([5,3,2])
                        with ci:
                            st.markdown(f"<span style='background:#FFEDD5;color:#EA580C;padding:2px 8px;border-radius:4px;font-weight:bold;font-size:12px;'>🏗️ {row['Obra_Vinculada']}</span>&nbsp;<span style='background:#E0E7FF;color:#4338CA;padding:2px 8px;border-radius:4px;font-weight:bold;font-size:12px;'>Lote: {row['Cod_Lote']}</span>", unsafe_allow_html=True)
                            st.markdown(f"**{row['Tipo_Material']}** | `{int(row['Qtd_Caixas'])} cx` — {row['M2_Item']:.2f} m²")
                            st.caption(f"Pavimentos: {row['Romaneio_Chapas']} | OP: {row.get('Num_OP') or 'S/OP'}")
                        with cp:
                            ptxt = pd.to_datetime(prazo_d).strftime('%d/%m/%Y') if prazo_valido(prazo_d) else "—"
                            st.caption("Prazo máximo despacho"); st.markdown(f"**{ptxt}**"); st.markdown(f"`{tag}`")
                        with ca:
                            if st.button("📅 Agendar", key=f"ag_btn_{row['id']}", use_container_width=True):
                                st.session_state[f"ag_open_{row['id']}"] = True
                        st.markdown("</div>", unsafe_allow_html=True)

                        if st.session_state.get(f"ag_open_{row['id']}", False):
                            with st.container(border=True):
                                st.markdown(f"#### 📋 Agendar — Lote `{row['Cod_Lote']}` | {row['Obra_Vinculada']}")
                                fa1,fa2 = st.columns(2)
                                with fa1:
                                    dt_env = st.date_input("Data envio:", format="DD/MM/YYYY", key=f"dt_env_{row['id']}",
                                                           value=pd.to_datetime(prazo_d).date() if prazo_valido(prazo_d) else HOJE_PROJETO.date())
                                    transp = st.selectbox("Transporte:", ["Frota Própria (Passold)","Transportadora Terceira","Retirada pelo Cliente"], key=f"tr_{row['id']}")
                                with fa2:
                                    veic = st.text_input("Veículo / Placa:", key=f"ve_{row['id']}")
                                    obs  = st.text_area("Observações:", key=f"ob_{row['id']}", height=80)
                                cb1,cb2 = st.columns(2)
                                with cb1:
                                    if st.button("✅ Confirmar", key=f"conf_{row['id']}", use_container_width=True, type="primary"):
                                        agendar_envio(row['id'],dt_env,transp,veic,obs,st.session_state.usuario_nome)
                                        st.session_state[f"ag_open_{row['id']}"] = False
                                        st.toast(f"Agendado para {dt_env.strftime('%d/%m/%Y')}! 📅"); time.sleep(0.3); st.rerun()
                                with cb2:
                                    if st.button("Cancelar", key=f"can_{row['id']}", use_container_width=True):
                                        st.session_state[f"ag_open_{row['id']}"] = False; st.rerun()

            with st.expander("📅 Envios Agendados — Confirmar Saída", expanded=True):
                if df_log.empty or df_log[df_log['Status_Logistica']=='Envio Agendado'].empty:
                    st.info("Nenhum envio agendado.")
                else:
                    df_agend = df_log[df_log['Status_Logistica']=='Envio Agendado'].copy().sort_values('Data_Envio_Agendado',na_position='last')
                    for _,row in df_agend.iterrows():
                        pd_d = row['Data_Limite_Despacho']; de_d = row['Data_Envio_Agendado']
                        no_prazo = (pd.to_datetime(de_d)<=pd.to_datetime(pd_d)) if prazo_valido(pd_d) and prazo_valido(de_d) else True
                        bord="#22C55E" if no_prazo else "#EF4444"; bg="#F0FDF4" if no_prazo else "#FEE2E2"
                        st.markdown(f"<div style='border-left:5px solid {bord};background:{bg};padding:12px 16px;border-radius:6px;margin-bottom:8px;'>", unsafe_allow_html=True)
                        ci2,cp2,ca2 = st.columns([5,3,2])
                        with ci2:
                            st.markdown(f"<span style='background:#FFEDD5;color:#EA580C;padding:2px 8px;border-radius:4px;font-weight:bold;font-size:12px;'>🏗️ {row['Obra_Vinculada']}</span>&nbsp;<span style='background:#E0E7FF;color:#4338CA;padding:2px 8px;border-radius:4px;font-weight:bold;font-size:12px;'>Lote: {row['Cod_Lote']}</span>", unsafe_allow_html=True)
                            st.markdown(f"**{row['Tipo_Material']}** | `{int(row['Qtd_Caixas'])} cx` — {row['M2_Item']:.2f} m²")
                            st.caption(f"🚛 {row.get('Transportadora','—')} | {row.get('Veiculo','—')}")
                            if row.get('Observacoes'): st.caption(f"📝 {row['Observacoes']}")
                        with cp2:
                            et = pd.to_datetime(de_d).strftime('%d/%m/%Y') if prazo_valido(de_d) else "—"
                            pt = pd.to_datetime(pd_d).strftime('%d/%m/%Y') if prazo_valido(pd_d) else "—"
                            st.caption("Data envio agendada"); st.markdown(f"**{et}**")
                            st.caption("Prazo máximo"); st.write(pt)
                            if not no_prazo: st.error("⚠️ Fora do prazo!")
                        with ca2:
                            st.write("")
                            if st.button("🚚 DESPACHADO!", key=f"des_{row['id']}", use_container_width=True, type="primary"):
                                confirmar_despacho(row['id'], st.session_state.usuario_nome)
                                st.toast("Despachado! ✅"); time.sleep(0.3); st.rerun()
                            if st.button("✏️ Reagendar", key=f"rag_{row['id']}", use_container_width=True):
                                conn=conectar_banco();cursor=conn.cursor()
                                cursor.execute("UPDATE logistica_envios SET Status_Logistica='Aguardando Agendamento' WHERE id=%s",(row['id'],))
                                conn.commit();conn.close(); st.rerun()
                        st.markdown("</div>", unsafe_allow_html=True)

            with st.expander("📦 Histórico de Despachos", expanded=False):
                if df_log.empty or df_log[df_log['Status_Logistica']=='Despachado ✅'].empty:
                    st.info("Nenhum despacho realizado ainda.")
                else:
                    df_hist = df_log[df_log['Status_Logistica']=='Despachado ✅'].copy()
                    for col in ['Data_Limite_Despacho','Data_Envio_Agendado']:
                        df_hist[col] = df_hist[col].apply(lambda x: pd.to_datetime(x).strftime('%d/%m/%Y') if prazo_valido(x) else "—")
                    cols_h = [c for c in ['Obra_Vinculada','Cod_Lote','Tipo_Material','Qtd_Caixas','M2_Item',
                                           'Transportadora','Veiculo','Data_Envio_Agendado','Data_Limite_Despacho',
                                           'Confirmado_Por','Confirmado_Em'] if c in df_hist.columns]
                    st.dataframe(df_hist[cols_h], hide_index=True, use_container_width=True)
                    df_pont = df_log[df_log['Status_Logistica']=='Despachado ✅'].copy()
                    df_pont = df_pont[df_pont['Data_Limite_Despacho'].apply(prazo_valido) & df_pont['Data_Envio_Agendado'].apply(prazo_valido)]
                    if not df_pont.empty:
                        ok = (pd.to_datetime(df_pont['Data_Envio_Agendado'])<=pd.to_datetime(df_pont['Data_Limite_Despacho'])).sum()
                        st.metric("📊 Pontualidade", f"{ok/len(df_pont)*100:.0f}%")

    # ==================================================
    # CONFIGURAÇÕES
    # ==================================================
    elif nome_aba == "Configurações do Sistema":
        with aba_objeto:
            st.header("⚙️ Painel de Controle Master")
            with st.expander("➕ Cadastrar Novo Usuário"):
                with st.form("form_user"):
                    nu=st.text_input("login:").lower().strip()
                    nn=st.text_input("Nome:")
                    ns=st.selectbox("Setor:",["Produção","Engenharia","Diretoria","Logística","Master"])
                    np=st.text_input("Senha:",type="password")
                    if st.form_submit_button("Salvar"):
                        if not all([nu,nn,np]): st.error("Preencha tudo.")
                        else:
                            conn=conectar_banco();cursor=conn.cursor()
                            try:
                                cursor.execute("INSERT INTO usuarios (usuario,nome,setor,senha) VALUES (%s,%s,%s,%s)",
                                               (nu,nn,ns,hash_senha(np)))
                                conn.commit(); st.success(f"{nn} criado!"); time.sleep(0.5); st.rerun()
                            except Exception as e: st.error(f"Erro: {e}")
                            finally: conn.close()

            conn=conectar_banco()
            df_u=pd.read_sql_query("SELECT id, usuario as login, nome as Nome, setor as Setor FROM usuarios",conn)
            conn.close()
            st.dataframe(df_u,hide_index=True,use_container_width=True)
            if len(df_u)>1:
                del_u=st.selectbox("Remover:",df_u['login'].tolist())
                if del_u=='master': st.caption("🔒 Master não pode ser deletado.")
                else:
                    if st.button(f"❌ Excluir {del_u}"):
                        conn=conectar_banco();cursor=conn.cursor()
                        cursor.execute("DELETE FROM usuarios WHERE usuario=%s",(del_u,))
                        conn.commit();conn.close()
                        st.toast("Removido!",icon="🗑️"); time.sleep(0.5); st.rerun()

            st.markdown("---")
            st.markdown("### 🚨 Reset Geral")
            st.warning("Remove TODOS os dados permanentemente.")
            if st.button("CONFIRMAR LIMPEZA TOTAL"):
                resetar_banco_dados_completo()
                st.toast("Resetado!",icon="🗑️"); time.sleep(0.5); st.rerun()