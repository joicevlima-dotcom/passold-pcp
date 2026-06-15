import streamlit as st
import pandas as pd
import plotly.express as px
from datetime import datetime, timedelta
import calendar as py_calendar
import os
import time
import bcrypt
import psycopg2
import psycopg2.extras
from psycopg2 import pool
from zoneinfo import ZoneInfo

FUSO_BR = ZoneInfo('America/Sao_Paulo')
HOJE_PROJETO = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)

st.set_page_config(page_title="Passold Sistemas de Fachadas", layout="wide")

st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700&family=JetBrains+Mono:wght@400;500&display=swap');
:root {
    --primary-color: #0F172A;
    --primary-light: #334155;
    --accent-color: #EA580C;
    --success-color: #059669;
    --warning-color: #D97706;
    --danger-color: #DC2626;
    --bg-body: #F8FAFC;
    --bg-card: #FFFFFF;
    --border-color: #E2E8F0;
    --text-main: #1E293B;
    --text-muted: #64748B;
    --shadow-sm: 0 1px 3px rgba(0,0,0,0.1);
    --shadow-md: 0 4px 6px -1px rgba(0,0,0,0.1), 0 2px 4px -1px rgba(0,0,0,0.06);
    --radius: 8px;
}
.stApp { background-color: var(--bg-body); font-family: 'Inter', sans-serif; color: var(--text-main); }
section[data-testid="stSidebar"] { background-color: var(--bg-card); border-right: 1px solid var(--border-color); box-shadow: var(--shadow-sm); }
h1, h2, h3, h4, h5, h6 { color: var(--primary-color)!important; font-weight: 700!important; letter-spacing: -0.02em; margin-bottom: 1rem!important; }
p, label, div[data-testid="stWidgetLabel"] { color: var(--text-main); font-size: 0.95rem; }
div[data-testid="metric-container"] { background: var(--bg-card)!important; border: 1px solid var(--border-color)!important; border-left: 5px solid var(--primary-color)!important; border-radius: var(--radius)!important; padding: 16px!important; box-shadow: var(--shadow-sm)!important; transition: transform 0.2s ease, box-shadow 0.2s ease; }
div[data-testid="metric-container"]:hover { transform: translateY(-2px); box-shadow: var(--shadow-md)!important; border-left-color: var(--accent-color)!important; }
div[data-testid="stMetricValue"] { font-size: 1.8rem!important; font-weight: 700!important; color: var(--primary-color)!important; }
div[data-testid="stMetricLabel"] { color: var(--text-muted)!important; font-weight: 500!important; text-transform: uppercase; font-size: 0.75rem!important; letter-spacing: 0.05em; }
.stButton > button { background-color: var(--primary-color)!important; color: #FFFFFF!important; font-weight: 600!important; border-radius: 6px!important; border: none!important; padding: 10px 24px!important; font-size: 0.9rem!important; box-shadow: var(--shadow-sm)!important; transition: all 0.2s ease!important; }
.stButton > button p, .stButton > button span, .stButton > button div { color: #FFFFFF!important; }
.stButton > button:hover { background-color: var(--primary-light)!important; transform: translateY(-1px); box-shadow: var(--shadow-md)!important; color: #FFFFFF!important; }
.stButton > button[kind="primary"] { background-color: var(--accent-color)!important; }
.stButton > button[kind="primary"]:hover { background-color: #c2410c!important; }
.stTextInput > div > div > input, .stSelectbox > div > div > select, .stNumberInput > div > div > input { background-color: var(--bg-card)!important; border: 1px solid var(--border-color)!important; border-radius: 6px!important; color: var(--text-main)!important; padding: 10px!important; font-size: 0.9rem!important; box-shadow: none!important; }
div[data-testid="stDataFrame"] { border-radius: var(--radius)!important; border: 1px solid var(--border-color)!important; overflow: hidden; }
.stTabs [data-baseweb="tab-list"] { gap: 24px; border-bottom: 1px solid var(--border-color); }
.stTabs [data-baseweb="tab"] { height: 50px; background-color: transparent; border-radius: 4px 4px 0px 0px; color: var(--text-muted); font-weight: 500; transition: all 0.2s; }
.stTabs [aria-selected="true"] { background-color: var(--bg-body); color: var(--accent-color); font-weight: 700; border-bottom: 3px solid var(--accent-color); }
.badge-obra { background:#FFF7ED; color:#C2410C; padding:4px 10px; border-radius:6px; font-weight:700; font-size:11px; text-transform:uppercase; letter-spacing:0.05em; }
.badge-edt  { background:#F1F5F9; color:#334155; padding:4px 10px; border-radius:6px; font-weight:600; font-size:11px; border:1px solid #E2E8F0; }
.badge-lote { background:#ECFDF5; color:#047857; padding:4px 10px; border-radius:6px; font-weight:700; font-size:11px; }
.bar-ok      { border-left: 5px solid var(--success-color); background: #F0FDF4; padding: 12px 16px; border-radius: 6px; margin-bottom: 10px; box-shadow: var(--shadow-sm); }
.bar-warn    { border-left: 5px solid var(--warning-color); background: #FFFBEB; padding: 12px 16px; border-radius: 6px; margin-bottom: 10px; box-shadow: var(--shadow-sm); }
.bar-danger  { border-left: 5px solid var(--danger-color);  background: #FEF2F2; padding: 12px 16px; border-radius: 6px; margin-bottom: 10px; box-shadow: var(--shadow-sm); }
.bar-neutral { border-left: 5px solid var(--text-muted);    background: #F8FAFC; padding: 12px 16px; border-radius: 6px; margin-bottom: 10px; box-shadow: var(--shadow-sm); }
#MainMenu { visibility: hidden; }
footer    { visibility: hidden; }
header    { visibility: hidden; }
</style>
""", unsafe_allow_html=True)

# ========================================================
# CONNECTION POOL — criado uma única vez para todos os usuários
# ========================================================
@st.cache_resource
def get_connection_pool():
    return pool.ThreadedConnectionPool(
        minconn=2,
        maxconn=20,
        dsn=st.secrets["supabase"]["url"]
    )

def conectar_banco():
    return get_connection_pool().getconn()

def liberar_conexao(conn):
    try:
        get_connection_pool().putconn(conn)
    except Exception:
        pass

# ========================================================
# SENHAS — bcrypt com salt
# ========================================================
def hash_senha(senha: str) -> str:
    return bcrypt.hashpw(senha.encode(), bcrypt.gensalt()).decode()

def verificar_senha(senha: str, hash_salvo: str) -> bool:
    try:
        return bcrypt.checkpw(senha.encode(), hash_salvo.encode())
    except Exception:
        return False

# ========================================================
# INICIALIZAÇÃO DAS TABELAS
# ========================================================
def inicializar_banco_de_dados():
    conn = conectar_banco()
    cursor = conn.cursor()
    try:
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
                Status_Engenharia TEXT DEFAULT 'Aguardando Medicao In Loco',
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
                Data_Despacho DATE,
                Romaneio_Chapas TEXT,
                Status_Item TEXT DEFAULT 'Pendente',
                Dificuldade INTEGER DEFAULT 3,
                Fase_Produtiva TEXT,
                Enviado_Logistica INTEGER DEFAULT 0,
                updated_at TIMESTAMP DEFAULT NOW()
            )
        """)
        cursor.execute("ALTER TABLE itens_detalhado ADD COLUMN IF NOT EXISTS Data_Despacho DATE")
        cursor.execute("ALTER TABLE itens_detalhado ADD COLUMN IF NOT EXISTS updated_at TIMESTAMP DEFAULT NOW()")
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
                status TEXT DEFAULT 'Pendente de Aprovacao',
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
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS componentes_op (
                id SERIAL PRIMARY KEY,
                item_id INTEGER,
                Obra_Vinculada TEXT,
                Cod_Lote TEXT,
                Num_OP TEXT,
                Nome_Componente TEXT,
                Quantidade REAL,
                Unidade TEXT,
                Status_Item TEXT DEFAULT 'Aguardando Conferencia',
                Observacao TEXT,
                Conferido_Por TEXT,
                Conferido_Em TEXT
            )
        """)
        # ── TABELAS DO SISTEMA DE MEDIÇÃO ──────────────────────────
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS medicao_obras (
                id SERIAL PRIMARY KEY,
                nome TEXT NOT NULL,
                valor_m2_global REAL NOT NULL,
                metragem_geral REAL NOT NULL,
                criado_em TIMESTAMP DEFAULT NOW()
            )
        """)
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS medicao_servicos (
                id SERIAL PRIMARY KEY,
                obra_id INTEGER NOT NULL REFERENCES medicao_obras(id) ON DELETE CASCADE,
                nome TEXT NOT NULL,
                valor_m2_servico REAL NOT NULL
            )
        """)
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS medicao_subdivisoes (
                id SERIAL PRIMARY KEY,
                servico_id INTEGER NOT NULL REFERENCES medicao_servicos(id) ON DELETE CASCADE,
                nome TEXT NOT NULL,
                m2 REAL NOT NULL DEFAULT 0,
                percentual REAL NOT NULL DEFAULT 0
            )
        """)
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS medicao_historico (
                id SERIAL PRIMARY KEY,
                obra_id INTEGER NOT NULL REFERENCES medicao_obras(id) ON DELETE CASCADE,
                periodo TEXT NOT NULL,
                total_medido REAL NOT NULL DEFAULT 0,
                snapshot JSONB,
                criado_em TIMESTAMP DEFAULT NOW(),
                UNIQUE(obra_id, periodo)
            )
        """)
        # ── TABELA DE PEÇAS DAS OPs ────────────────────────────────
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS op_pecas (
                id SERIAL PRIMARY KEY,
                lote_id INTEGER REFERENCES itens_detalhado(id) ON DELETE CASCADE,
                obra TEXT,
                cod_lote TEXT,
                num_op TEXT,
                codigo TEXT NOT NULL,
                localizacao TEXT,
                medida TEXT,
                qtd_total INTEGER DEFAULT 0,
                qtd_enviada INTEGER DEFAULT 0,
                saldo INTEGER DEFAULT 0,
                m2_op_real REAL DEFAULT 0,
                componentes_status TEXT DEFAULT 'Aguardando Projetista',
                criado_em TIMESTAMP DEFAULT NOW()
            )
        """)
        # Coluna de m2 executado na etapa
        cursor.execute("ALTER TABLE cronograma_macro ADD COLUMN IF NOT EXISTS m2_executado REAL DEFAULT 0")
        cursor.execute("ALTER TABLE cronograma_macro ADD COLUMN IF NOT EXISTS Numero_Projeto TEXT DEFAULT ''")
        cursor.execute("ALTER TABLE op_pecas ADD COLUMN IF NOT EXISTS m2_op_real REAL DEFAULT 0")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_op_pecas_lote ON op_pecas(lote_id)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_op_pecas_obra ON op_pecas(obra)")

        # ── ÍNDICES DE PERFORMANCE ──────────────────────────────────
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_itens_obra ON itens_detalhado(Obra_Vinculada)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_itens_status ON itens_detalhado(Status_Item)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_itens_edt ON itens_detalhado(EDT_Vinculado)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_macro_obra ON cronograma_macro(Obra)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_logistica_status ON logistica_envios(Status_Logistica)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_medicao_hist_obra ON medicao_historico(obra_id)")

        cursor.execute("SELECT COUNT(*) FROM usuarios")
        if cursor.fetchone()[0] == 0:
            cursor.execute(
                "INSERT INTO usuarios (usuario, nome, setor, senha) VALUES (%s, %s, %s, %s)",
                ('master', 'Joice Master', 'Master', hash_senha('Jv568279.'))
            )
        conn.commit()
    except Exception as e:
        conn.rollback()
        st.error(f"Erro na inicialização: {e}")
    finally:
        liberar_conexao(conn)

inicializar_banco_de_dados()

# ========================================================
# UTILITÁRIOS DE DATAS
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
    dt = inicio_previsto if isinstance(inicio_previsto, datetime) else datetime.combine(inicio_previsto, datetime.min.time())
    data_limite_despacho  = dt - timedelta(days=int(dias_logistica))
    primeiro_dia_producao = subtrair_dias_uteis(data_limite_despacho, int(dias_uteis_fabricacao))
    prazo_engenharia      = subtrair_dias_uteis(primeiro_dia_producao, int(dias_antecedencia_eng))
    return prazo_engenharia, primeiro_dia_producao, data_limite_despacho

def gerar_lote_unico(data_limite_obra, dias_logistica, dias_uteis_fab,
                     total_cx, total_m2, obra, edt, cod_lote,
                     especificacao, txt_pav, dificuldade):
    if isinstance(data_limite_obra, datetime):
        dt_limite = data_limite_obra
    else:
        dt_limite = datetime.combine(data_limite_obra, datetime.min.time())
    dt_despacho = dt_limite - timedelta(days=int(dias_logistica))
    dt_inicio   = subtrair_dias_uteis(dt_despacho, int(dias_uteis_fab))
    return [{
        "Obra_Vinculada":           obra,
        "EDT_Vinculado":            edt,
        "Cod_Lote":                 cod_lote,
        "Num_OP":                   None,
        "Tipo_Material":            especificacao,
        "Qtd_Caixas":               int(total_cx),
        "M2_Item":                  float(round(total_m2, 2)),
        "Data_Producao_Programada": dt_inicio.strftime('%Y-%m-%d'),
        "Data_Limite_Obra":         dt_limite.strftime('%Y-%m-%d'),
        "Data_Despacho":            dt_despacho.strftime('%Y-%m-%d'),
        "Romaneio_Chapas":          txt_pav,
        "Status_Item":              "Pendente",
        "Dificuldade":              int(dificuldade),
        "Fase_Produtiva":           f"CORTE→MONTAGEM ({dias_uteis_fab} dias uteis)",
        "Enviado_Logistica":        0
    }]

def prazo_valido(valor) -> bool:
    if valor is None:
        return False
    try:
        return not pd.isnull(valor)
    except Exception:
        return False

# ========================================================
# FUNÇÕES DE BANCO — com cache, pool e try/finally
# ========================================================
@st.cache_data(ttl=30)
def carregar_macro():
    conn = conectar_banco()
    try:
        with st.spinner("Carregando cronograma..."):
            df = pd.read_sql_query("SELECT * FROM cronograma_macro ORDER BY id", conn)
    finally:
        liberar_conexao(conn)
    for col in ['inicio_previsto', 'termino_obra', 'prazo_engenharia', 'data_limite_despacho', 'primeiro_dia_producao']:
        if col in df.columns:
            df[col] = pd.to_datetime(df[col], errors='coerce')
    df.columns = [c.replace('_', ' ').title().replace(' ', '_') if c != 'id' else c for c in df.columns]
    rename = {
        'Inicio_Previsto': 'Inicio_Previsto', 'Termino_Obra': 'Termino_Obra',
        'Prazo_Engenharia': 'Prazo_Engenharia', 'Data_Limite_Despacho': 'Data_Limite_Despacho',
        'Primeiro_Dia_Producao': 'Primeiro_Dia_Producao', 'Edt': 'EDT',
        'M2_Total_Tarefa': 'M2_Total_Tarefa', 'Status_Engenharia': 'Status_Engenharia',
        'Tipo_Escopo': 'Tipo_Escopo', 'Etapa_Macro': 'Etapa_Macro',
    }
    return df.rename(columns=rename)

@st.cache_data(ttl=30)
def carregar_micro():
    conn = conectar_banco()
    try:
        with st.spinner("Carregando lotes..."):
            df = pd.read_sql_query(
                "SELECT * FROM itens_detalhado ORDER BY Data_Producao_Programada ASC", conn
            )
    finally:
        liberar_conexao(conn)
    for col in ['data_producao_programada', 'data_limite_obra', 'data_despacho']:
        if col in df.columns:
            df[col] = pd.to_datetime(df[col], errors='coerce')
    df.columns = [c.replace('_', ' ').title().replace(' ', '_') if c != 'id' else c for c in df.columns]
    rename = {
        'Data_Producao_Programada': 'Data_Producao_Programada', 'Data_Limite_Obra': 'Data_Limite_Obra',
        'Data_Despacho': 'Data_Despacho', 'Edt_Vinculado': 'EDT_Vinculado',
        'Obra_Vinculada': 'Obra_Vinculada', 'Cod_Lote': 'Cod_Lote', 'Num_Op': 'Num_OP',
        'Tipo_Material': 'Tipo_Material', 'Qtd_Caixas': 'Qtd_Caixas', 'M2_Item': 'M2_Item',
        'Romaneio_Chapas': 'Romaneio_Chapas', 'Status_Item': 'Status_Item',
        'Fase_Produtiva': 'Fase_Produtiva', 'Enviado_Logistica': 'Enviado_Logistica',
    }
    return df.rename(columns=rename)

@st.cache_data(ttl=30)
def carregar_micro_por_obra(obra: str):
    conn = conectar_banco()
    try:
        df = pd.read_sql_query(
            "SELECT * FROM itens_detalhado WHERE Obra_Vinculada = %s ORDER BY Data_Producao_Programada ASC",
            conn, params=(obra,)
        )
    finally:
        liberar_conexao(conn)
    for col in ['data_producao_programada', 'data_limite_obra', 'data_despacho']:
        if col in df.columns:
            df[col] = pd.to_datetime(df[col], errors='coerce')
    df.columns = [c.replace('_', ' ').title().replace(' ', '_') if c != 'id' else c for c in df.columns]
    rename = {
        'Data_Producao_Programada': 'Data_Producao_Programada', 'Data_Limite_Obra': 'Data_Limite_Obra',
        'Data_Despacho': 'Data_Despacho', 'Edt_Vinculado': 'EDT_Vinculado',
        'Obra_Vinculada': 'Obra_Vinculada', 'Cod_Lote': 'Cod_Lote', 'Num_Op': 'Num_OP',
        'Tipo_Material': 'Tipo_Material', 'Qtd_Caixas': 'Qtd_Caixas', 'M2_Item': 'M2_Item',
        'Romaneio_Chapas': 'Romaneio_Chapas', 'Status_Item': 'Status_Item',
        'Fase_Produtiva': 'Fase_Produtiva', 'Enviado_Logistica': 'Enviado_Logistica',
    }
    return df.rename(columns=rename)

@st.cache_data(ttl=30)
def carregar_macro_por_obra(obra: str):
    conn = conectar_banco()
    try:
        df = pd.read_sql_query(
            "SELECT * FROM cronograma_macro WHERE Obra = %s ORDER BY id", conn, params=(obra,)
        )
    finally:
        liberar_conexao(conn)
    for col in ['inicio_previsto', 'termino_obra', 'prazo_engenharia', 'data_limite_despacho', 'primeiro_dia_producao']:
        if col in df.columns:
            df[col] = pd.to_datetime(df[col], errors='coerce')
    df.columns = [c.replace('_', ' ').title().replace(' ', '_') if c != 'id' else c for c in df.columns]
    rename = {
        'Inicio_Previsto': 'Inicio_Previsto', 'Termino_Obra': 'Termino_Obra',
        'Prazo_Engenharia': 'Prazo_Engenharia', 'Data_Limite_Despacho': 'Data_Limite_Despacho',
        'Primeiro_Dia_Producao': 'Primeiro_Dia_Producao', 'Edt': 'EDT',
        'M2_Total_Tarefa': 'M2_Total_Tarefa', 'Status_Engenharia': 'Status_Engenharia',
        'Tipo_Escopo': 'Tipo_Escopo', 'Etapa_Macro': 'Etapa_Macro',
    }
    return df.rename(columns=rename)

@st.cache_data(ttl=30)
def carregar_fila_logistica():
    conn = conectar_banco()
    try:
        df = pd.read_sql_query(
            "SELECT * FROM logistica_envios ORDER BY data_limite_despacho ASC NULLS LAST", conn
        )
    finally:
        liberar_conexao(conn)
    for col in ['data_limite_despacho', 'data_envio_agendado']:
        if col in df.columns:
            df[col] = pd.to_datetime(df[col], errors='coerce')
    df.columns = [c.replace('_', ' ').title().replace(' ', '_') if c != 'id' else c for c in df.columns]
    rename = {
        'Data_Limite_Despacho': 'Data_Limite_Despacho', 'Data_Envio_Agendado': 'Data_Envio_Agendado',
        'Obra_Vinculada': 'Obra_Vinculada', 'Cod_Lote': 'Cod_Lote', 'Num_Op': 'Num_OP',
        'Tipo_Material': 'Tipo_Material', 'Qtd_Caixas': 'Qtd_Caixas', 'M2_Item': 'M2_Item',
        'Romaneio_Chapas': 'Romaneio_Chapas', 'Status_Logistica': 'Status_Logistica',
        'Transportadora': 'Transportadora', 'Veiculo': 'Veiculo', 'Observacoes': 'Observacoes',
        'Confirmado_Por': 'Confirmado_Por', 'Confirmado_Em': 'Confirmado_Em',
        'Item_Id': 'item_id', 'Edt_Vinculado': 'EDT_Vinculado',
    }
    return df.rename(columns=rename)

@st.cache_data(ttl=30)
def carregar_solicitacoes():
    conn = conectar_banco()
    try:
        df = pd.read_sql_query("SELECT * FROM solicitacoes_prazo ORDER BY id DESC", conn)
    finally:
        liberar_conexao(conn)
    return df

def _limpar_cache_geral():
    carregar_macro.clear()
    carregar_micro.clear()
    carregar_fila_logistica.clear()
    carregar_solicitacoes.clear()
    try:
        carregar_macro_por_obra.clear()
        carregar_micro_por_obra.clear()
    except Exception:
        pass

def salvar_lotes_micro(lotes: list):
    if not lotes:
        return
    conn = conectar_banco()
    try:
        cursor = conn.cursor()
        for l in lotes:
            cursor.execute("""
                INSERT INTO itens_detalhado
                (Obra_Vinculada, EDT_Vinculado, Cod_Lote, Num_OP, Tipo_Material,
                 Qtd_Caixas, M2_Item, Data_Producao_Programada, Data_Limite_Obra,
                 Data_Despacho, Romaneio_Chapas, Status_Item, Dificuldade, Fase_Produtiva, Enviado_Logistica)
                VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)
            """, (
                l['Obra_Vinculada'], l['EDT_Vinculado'], l['Cod_Lote'], l['Num_OP'],
                l['Tipo_Material'], l['Qtd_Caixas'], l['M2_Item'],
                l['Data_Producao_Programada'], l['Data_Limite_Obra'], l['Data_Despacho'],
                l['Romaneio_Chapas'], l['Status_Item'], l['Dificuldade'],
                l['Fase_Produtiva'], l['Enviado_Logistica']
            ))
        conn.commit()
        _limpar_cache_geral()
    except Exception as e:
        conn.rollback()
        st.error(f"Erro ao salvar lotes: {e}")
    finally:
        liberar_conexao(conn)

def deletar_lotes_por_edt_lote(obra, edt, cod_lote):
    conn = conectar_banco()
    try:
        cursor = conn.cursor()
        if edt:
            cursor.execute(
                "DELETE FROM itens_detalhado WHERE Obra_Vinculada=%s AND EDT_Vinculado=%s AND Cod_Lote=%s",
                (obra, edt, cod_lote)
            )
        else:
            cursor.execute(
                "DELETE FROM itens_detalhado WHERE Obra_Vinculada=%s AND Cod_Lote=%s",
                (obra, cod_lote)
            )
        conn.commit()
        _limpar_cache_geral()
    except Exception as e:
        conn.rollback()
        st.error(f"Erro ao deletar lote: {e}")
    finally:
        liberar_conexao(conn)

def atualizar_cronograma_macro_datas(edt, prazo_eng, primeiro_prod, despacho):
    conn = conectar_banco()
    try:
        cursor = conn.cursor()
        cursor.execute(
            "SELECT prazo_engenharia, primeiro_dia_producao, data_limite_despacho FROM cronograma_macro WHERE EDT=%s",
            (edt,)
        )
        row = cursor.fetchone()
        def to_dt(v):
            try:
                return pd.to_datetime(v) if v else None
            except Exception:
                return None
        if row:
            pa, pp, pd_ = to_dt(row[0]), to_dt(row[1]), to_dt(row[2])
            novo_prazo    = min(pa,  pd.to_datetime(prazo_eng))     if pa  else pd.to_datetime(prazo_eng)
            novo_primeiro = min(pp,  pd.to_datetime(primeiro_prod)) if pp  else pd.to_datetime(primeiro_prod)
            novo_despacho = min(pd_, pd.to_datetime(despacho))      if pd_ else pd.to_datetime(despacho)
        else:
            novo_prazo    = pd.to_datetime(prazo_eng)
            novo_primeiro = pd.to_datetime(primeiro_prod)
            novo_despacho = pd.to_datetime(despacho)
        cursor.execute("""
            UPDATE cronograma_macro
            SET Prazo_Engenharia=%s, Primeiro_Dia_Producao=%s, Data_Limite_Despacho=%s
            WHERE EDT=%s
        """, (
            novo_prazo.strftime('%Y-%m-%d'),
            novo_primeiro.strftime('%Y-%m-%d'),
            novo_despacho.strftime('%Y-%m-%d'),
            edt
        ))
        conn.commit()
        _limpar_cache_geral()
    except Exception as e:
        conn.rollback()
        st.error(f"Erro ao atualizar datas: {e}")
    finally:
        liberar_conexao(conn)

def atualizar_status_engenharia(edt_id, novo_status):
    conn = conectar_banco()
    try:
        cursor = conn.cursor()
        cursor.execute("UPDATE cronograma_macro SET Status_Engenharia=%s WHERE id=%s", (novo_status, edt_id))
        conn.commit()
        _limpar_cache_geral()
    except Exception as e:
        conn.rollback()
        st.error(f"Erro ao atualizar status: {e}")
    finally:
        liberar_conexao(conn)

def salvar_solicitacao(edt, tarefa, prazo_atual, prazo_sol, justif, criado_por):
    conn = conectar_banco()
    try:
        cursor = conn.cursor()
        cursor.execute("""
            INSERT INTO solicitacoes_prazo (edt, tarefa, prazo_atual, prazo_solicitado, justificativa, criado_por, status, criado_em)
            VALUES (%s,%s,%s,%s,%s,%s,'Pendente de Aprovacao',%s)
        """, (edt, tarefa, prazo_atual, prazo_sol, justif, criado_por, datetime.now().strftime('%d/%m/%Y %H:%M')))
        conn.commit()
        carregar_solicitacoes.clear()
    except Exception as e:
        conn.rollback()
        st.error(f"Erro ao salvar solicitação: {e}")
    finally:
        liberar_conexao(conn)

def atualizar_status_solicitacao(sol_id, novo_status):
    conn = conectar_banco()
    try:
        cursor = conn.cursor()
        cursor.execute("UPDATE solicitacoes_prazo SET status=%s WHERE id=%s", (novo_status, sol_id))
        conn.commit()
        carregar_solicitacoes.clear()
    except Exception as e:
        conn.rollback()
        st.error(f"Erro ao atualizar solicitação: {e}")
    finally:
        liberar_conexao(conn)

def enviar_para_logistica(row, limite_despacho):
    conn = conectar_banco()
    try:
        cursor = conn.cursor()
        cursor.execute("SELECT id FROM logistica_envios WHERE item_id=%s", (int(row['id']),))
        if cursor.fetchone():
            return
        cursor.execute("""
            INSERT INTO logistica_envios
            (item_id, Obra_Vinculada, EDT_Vinculado, Cod_Lote, Num_OP, Tipo_Material,
             Qtd_Caixas, M2_Item, Romaneio_Chapas, Data_Limite_Despacho, Status_Logistica)
            VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,'Aguardando Agendamento')
        """, (
            int(row['id']), row['Obra_Vinculada'], row['EDT_Vinculado'], row['Cod_Lote'],
            row.get('Num_OP') or '', row['Tipo_Material'], int(row['Qtd_Caixas']), float(row['M2_Item']),
            row['Romaneio_Chapas'],
            limite_despacho.strftime('%Y-%m-%d') if prazo_valido(limite_despacho) else None
        ))
        cursor.execute("UPDATE itens_detalhado SET Enviado_Logistica=1 WHERE id=%s", (int(row['id']),))
        conn.commit()
        _limpar_cache_geral()
    except Exception as e:
        conn.rollback()
        st.error(f"Erro ao enviar para logística: {e}")
    finally:
        liberar_conexao(conn)

def agendar_envio(log_id, data_envio, transportadora, veiculo, obs, usuario):
    conn = conectar_banco()
    try:
        cursor = conn.cursor()
        cursor.execute("""
            UPDATE logistica_envios
            SET Data_Envio_Agendado=%s, Transportadora=%s, Veiculo=%s, Observacoes=%s, Status_Logistica='Envio Agendado'
            WHERE id=%s
        """, (
            data_envio.strftime('%Y-%m-%d') if data_envio else None,
            transportadora, veiculo, obs, log_id
        ))
        conn.commit()
        carregar_fila_logistica.clear()
    except Exception as e:
        conn.rollback()
        st.error(f"Erro ao agendar envio: {e}")
    finally:
        liberar_conexao(conn)

def confirmar_despacho(log_id, usuario):
    conn = conectar_banco()
    try:
        cursor = conn.cursor()
        cursor.execute("""
            UPDATE logistica_envios
            SET Status_Logistica='Despachado', Confirmado_Por=%s, Confirmado_Em=%s
            WHERE id=%s
        """, (usuario, datetime.now().strftime('%d/%m/%Y %H:%M'), log_id))
        conn.commit()
        carregar_fila_logistica.clear()
    except Exception as e:
        conn.rollback()
        st.error(f"Erro ao confirmar despacho: {e}")
    finally:
        liberar_conexao(conn)

def verificar_login(usuario, senha):
    conn = conectar_banco()
    try:
        cursor = conn.cursor()
        cursor.execute("SELECT nome, setor, senha FROM usuarios WHERE usuario=%s", (usuario,))
        resultado = cursor.fetchone()
        if resultado and verificar_senha(senha, resultado[2]):
            return resultado[0], resultado[1]
        return None
    except Exception:
        return None
    finally:
        liberar_conexao(conn)

def resetar_banco_dados_completo():
    conn = conectar_banco()
    try:
        cursor = conn.cursor()
        for tabela in ['cronograma_macro', 'itens_detalhado', 'solicitacoes_prazo', 'logistica_envios',
                       'medicao_historico', 'medicao_subdivisoes', 'medicao_servicos', 'medicao_obras']:
            cursor.execute(f"DELETE FROM {tabela}")
        conn.commit()
        _limpar_cache_geral()
        carregar_medicao_obras.clear()
    except Exception as e:
        conn.rollback()
        st.error(f"Erro no reset: {e}")
    finally:
        liberar_conexao(conn)

def salvar_componentes(item_id, obra, cod_lote, num_op, componentes: list):
    conn = conectar_banco()
    try:
        cursor = conn.cursor()
        cursor.execute("DELETE FROM componentes_op WHERE item_id=%s", (item_id,))
        for c in componentes:
            cursor.execute("""
                INSERT INTO componentes_op
                (item_id, Obra_Vinculada, Cod_Lote, Num_OP, Nome_Componente, Quantidade, Unidade,
                 Status_Item, Observacao)
                VALUES (%s,%s,%s,%s,%s,%s,%s,'Aguardando Conferencia',NULL)
            """, (item_id, obra, cod_lote, num_op, c['nome'], c['qtd'], c['unidade']))
        conn.commit()
    except Exception as e:
        conn.rollback()
        st.error(f"Erro ao salvar componentes: {e}")
    finally:
        liberar_conexao(conn)

@st.cache_data(ttl=30)
def carregar_componentes_op(item_id):
    conn = conectar_banco()
    try:
        df = pd.read_sql_query(
            "SELECT * FROM componentes_op WHERE item_id=%s ORDER BY id", conn, params=(item_id,)
        )
    finally:
        liberar_conexao(conn)
    return df

@st.cache_data(ttl=30)
def carregar_todas_ops_com_componentes():
    conn = conectar_banco()
    try:
        df = pd.read_sql_query("""
            SELECT DISTINCT item_id, Obra_Vinculada, Cod_Lote, Num_OP
            FROM componentes_op ORDER BY Obra_Vinculada, Cod_Lote
        """, conn)
    finally:
        liberar_conexao(conn)
    return df

def atualizar_componente(comp_id, status, obs, usuario):
    conn = conectar_banco()
    try:
        cursor = conn.cursor()
        cursor.execute("""
            UPDATE componentes_op
            SET Status_Item=%s, Observacao=%s, Conferido_Por=%s, Conferido_Em=%s
            WHERE id=%s
        """, (status, obs, usuario, datetime.now().strftime('%d/%m/%Y %H:%M'), comp_id))
        conn.commit()
        carregar_componentes_op.clear()
        carregar_todas_ops_com_componentes.clear()
    except Exception as e:
        conn.rollback()
        st.error(f"Erro ao atualizar componente: {e}")
    finally:
        liberar_conexao(conn)

# ========================================================
# FUNÇÕES DE OP_PECAS
# ========================================================
@st.cache_data(ttl=30)
def carregar_pecas_lote(lote_id: int):
    conn = conectar_banco()
    try:
        df = pd.read_sql_query(
            "SELECT * FROM op_pecas WHERE lote_id=%s ORDER BY id", conn, params=(lote_id,)
        )
    finally:
        liberar_conexao(conn)
    return df

@st.cache_data(ttl=30)
def carregar_todas_pecas_obra(obra: str):
    conn = conectar_banco()
    try:
        df = pd.read_sql_query(
            "SELECT * FROM op_pecas WHERE obra=%s ORDER BY cod_lote, id", conn, params=(obra,)
        )
    finally:
        liberar_conexao(conn)
    return df

def salvar_pecas_lote(lote_id: int, obra: str, cod_lote: str, num_op: str,
                      pecas: list, componentes_status: str, m2_op_real: float):
    """Salva lista de peças vinculada ao lote. Substitui a lista anterior."""
    conn = conectar_banco()
    try:
        cursor = conn.cursor()
        cursor.execute("DELETE FROM op_pecas WHERE lote_id=%s", (lote_id,))
        for p in pecas:
            qtd = int(p.get('qtd', 0))
            cursor.execute("""
                INSERT INTO op_pecas
                (lote_id, obra, cod_lote, num_op, codigo, localizacao, medida,
                 qtd_total, qtd_enviada, saldo, m2_op_real, componentes_status)
                VALUES (%s,%s,%s,%s,%s,%s,%s,%s,0,%s,%s,%s)
            """, (
                lote_id, obra, cod_lote, num_op,
                p.get('codigo', '').strip().upper(),
                p.get('localizacao', '').strip().upper(),
                p.get('medida', '').strip().upper(),
                qtd, qtd, float(m2_op_real), componentes_status
            ))
        # Abate m2 REAL informado pelo usuário na etapa
        cursor.execute(
            "SELECT EDT_Vinculado FROM itens_detalhado WHERE id=%s", (lote_id,)
        )
        row_lote = cursor.fetchone()
        if row_lote:
            edt = row_lote[0]
            cursor.execute("""
                UPDATE cronograma_macro
                SET m2_executado = COALESCE(m2_executado, 0) + %s
                WHERE EDT = %s
            """, (float(m2_op_real), edt))
        conn.commit()
        carregar_pecas_lote.clear()
        carregar_todas_pecas_obra.clear()
        _limpar_cache_geral()
    except Exception as e:
        conn.rollback()
        st.error(f"Erro ao salvar peças: {e}")
    finally:
        liberar_conexao(conn)

def atualizar_componentes_status_pecas(lote_id: int, novo_status: str):
    conn = conectar_banco()
    try:
        cursor = conn.cursor()
        cursor.execute(
            "UPDATE op_pecas SET componentes_status=%s WHERE lote_id=%s",
            (novo_status, lote_id)
        )
        conn.commit()
        carregar_pecas_lote.clear()
    except Exception as e:
        conn.rollback()
        st.error(f"Erro ao atualizar status: {e}")
    finally:
        liberar_conexao(conn)

def gerar_op_xlsx(lote_row, pecas_df, macro_row, campos_extras: dict) -> bytes:
    """Gera o documento de Ordem de Produção em xlsx."""
    from openpyxl import Workbook
    from openpyxl.styles import Font, PatternFill, Alignment, Border, Side
    from io import BytesIO

    wb = Workbook()
    ws = wb.active
    ws.title = "Ordem de Producao"
    ws.sheet_view.showGridLines = False

    bd      = Side(style='thin', color="000000")
    borda   = Border(left=bd, right=bd, top=bd, bottom=bd)
    bd_bot  = Border(bottom=bd)
    fill_az = PatternFill(start_color="0F172A", end_color="0F172A", fill_type="solid")
    fill_lz = PatternFill(start_color="EFF6FF", end_color="EFF6FF", fill_type="solid")
    fill_gz = PatternFill(start_color="F1F5F9", end_color="F1F5F9", fill_type="solid")

    ws.column_dimensions['A'].width = 6
    ws.column_dimensions['B'].width = 20
    ws.column_dimensions['C'].width = 30
    ws.column_dimensions['D'].width = 18
    ws.column_dimensions['E'].width = 10
    ws.column_dimensions['F'].width = 10

    tipo_escopo = str(macro_row.get('Tipo_Escopo', 'ACM') or 'ACM')
    num_projeto  = str(macro_row.get('Numero_Projeto', '') or '')

    # ── CABEÇALHO ──────────────────────────────────────────
    ws.merge_cells("A1:F1")
    ws["A1"] = "PASSOLD SISTEMAS DE FACHADAS LTDA"
    ws["A1"].font = Font(name="Arial", size=14, bold=True, color="FFFFFF")
    ws["A1"].fill = fill_az
    ws["A1"].alignment = Alignment(horizontal="center", vertical="center")
    ws.row_dimensions[1].height = 28

    ws.merge_cells("A2:F2")
    ws["A2"] = f"ORDEM DE PRODUÇÃO — {tipo_escopo.upper()}"
    ws["A2"].font = Font(name="Arial", size=12, bold=True, color="FFFFFF")
    ws["A2"].fill = fill_az
    ws["A2"].alignment = Alignment(horizontal="center", vertical="center")
    ws.row_dimensions[2].height = 22

    # ── INFO PRINCIPAL ─────────────────────────────────────
    def info_row(ws, linha, label, valor, fill=None):
        ws.cell(linha, 1, label).font = Font(name="Arial", size=11, bold=True)
        ws.cell(linha, 1).fill = fill_gz
        ws.merge_cells(start_row=linha, start_column=2, end_row=linha, end_column=6)
        ws.cell(linha, 2, str(valor).upper()).font = Font(name="Arial", size=11)
        for c in range(1, 7):
            ws.cell(linha, c).border = borda
            ws.cell(linha, c).alignment = Alignment(vertical="center")
        ws.row_dimensions[linha].height = 18

    linha = 3
    info_row(ws, linha,   "Nº OP:",          lote_row.get('Num_OP', '—'))
    info_row(ws, linha+1, "DATA:",            datetime.now().strftime('%d/%m/%Y'))
    info_row(ws, linha+2, "OBRA:",            lote_row.get('Obra_Vinculada', '—'))
    info_row(ws, linha+3, "PROJETO:",         f"{num_projeto} — {macro_row.get('Tarefa', '—')}" if num_projeto else macro_row.get('Tarefa', '—'))
    info_row(ws, linha+4, "LOTE:",            lote_row.get('Cod_Lote', '—'))
    info_row(ws, linha+5, "ETAPA/PAVIMENTOS:",lote_row.get('Romaneio_Chapas', '—'))
    info_row(ws, linha+6, "MATERIAL:",        campos_extras.get('material', lote_row.get('Tipo_Material', '—')))

    linha = 10

    # ── CAMPOS ESPECÍFICOS POR TIPO ────────────────────────
    if tipo_escopo.upper() == "ACM":
        info_row(ws, linha,   "ÁREA TOTAL (m²):", f"{campos_extras.get('area_total', lote_row.get('M2_Item', 0)):.2f} m²")
        info_row(ws, linha+1, "DIFICULDADE:",     campos_extras.get('dificuldade', lote_row.get('Dificuldade', '—')))
        info_row(ws, linha+2, "QTD CHAPAS:",      lote_row.get('Qtd_Caixas', '—'))
        info_row(ws, linha+3, "QTD FOLHAS PROJ:", campos_extras.get('qtd_folhas', '—'))
        linha += 4
    elif "ESQUADRIA" in tipo_escopo.upper() or "VIDRO" in tipo_escopo.upper():
        info_row(ws, linha,   "PESO TOTAL:",      campos_extras.get('peso_total', '—'))
        info_row(ws, linha+1, "QTD FOLHAS PROJ:", campos_extras.get('qtd_folhas', '—'))
        linha += 2
    else:  # Terceirizada
        info_row(ws, linha,   "EMPRESA RESP.:",   campos_extras.get('empresa', '—'))
        linha += 1

    linha += 1

    # ── OBSERVAÇÕES ────────────────────────────────────────
    ws.merge_cells(f"A{linha}:F{linha}")
    ws[f"A{linha}"] = "LIBERAÇÃO PARA PRODUÇÃO"
    ws[f"A{linha}"].font = Font(name="Arial", size=11, bold=True, color="FFFFFF")
    ws[f"A{linha}"].fill = fill_az
    ws[f"A{linha}"].alignment = Alignment(horizontal="center", vertical="center")
    ws.row_dimensions[linha].height = 20
    linha += 1

    obs_txt = campos_extras.get('observacoes', '')
    ws.merge_cells(f"A{linha}:F{linha+2}")
    ws[f"A{linha}"] = obs_txt
    ws[f"A{linha}"].font = Font(name="Arial", size=11)
    ws[f"A{linha}"].alignment = Alignment(wrap_text=True, vertical="top")
    for r in range(linha, linha+3):
        for c in range(1, 7):
            ws.cell(r, c).border = borda
    ws.row_dimensions[linha].height = 45
    linha += 3

    linha += 1

    # ── TABELA DE PEÇAS ────────────────────────────────────
    if not pecas_df.empty:
        ws.merge_cells(f"A{linha}:F{linha}")
        ws[f"A{linha}"] = "RELAÇÃO DE PEÇAS"
        ws[f"A{linha}"].font = Font(name="Arial", size=11, bold=True, color="FFFFFF")
        ws[f"A{linha}"].fill = fill_az
        ws[f"A{linha}"].alignment = Alignment(horizontal="center", vertical="center")
        ws.row_dimensions[linha].height = 20
        linha += 1

        titulos_p = ["#", "CÓDIGO", "DESCRIÇÃO / LOCAL", "MEDIDA", "QTD", "SALDO"]
        for ci, t in enumerate(titulos_p, 1):
            cel = ws.cell(linha, ci, t)
            cel.font = Font(name="Arial", size=10, bold=True)
            cel.fill = fill_gz
            cel.alignment = Alignment(horizontal="center")
            cel.border = borda
        linha += 1

        for i, (_, peca) in enumerate(pecas_df.iterrows(), 1):
            bg = fill_lz if i % 2 == 0 else PatternFill()
            vals = [i, peca.get('codigo',''), peca.get('localizacao',''), peca.get('medida',''),
                    peca.get('qtd_total',0), peca.get('saldo',0)]
            for ci, v in enumerate(vals, 1):
                cel = ws.cell(linha, ci, v)
                cel.font = Font(name="Arial", size=10)
                cel.alignment = Alignment(horizontal="center", vertical="center")
                cel.border = borda
                if i % 2 == 0:
                    cel.fill = fill_lz
            ws.row_dimensions[linha].height = 16
            linha += 1

        # Total
        ws.merge_cells(f"A{linha}:D{linha}")
        ws.cell(linha, 1, "TOTAL DE PEÇAS:").font = Font(name="Arial", size=10, bold=True)
        ws.cell(linha, 5, int(pecas_df['qtd_total'].sum())).font = Font(name="Arial", size=10, bold=True)
        for c in range(1, 7):
            ws.cell(linha, c).border = borda
        linha += 2

    # ── ASSINATURAS ────────────────────────────────────────
    assinaturas = ["Responsável PCP", "Responsável Produção", "Conferência"]
    for ass in assinaturas:
        ws.merge_cells(f"A{linha}:D{linha}")
        ws.cell(linha, 1).border = bd_bot
        ws.cell(linha+1, 1, ass).font = Font(name="Arial", size=10, bold=True)
        ws.cell(linha, 5, "____/____/______").font = Font(name="Arial", size=10)
        linha += 3

    buf = BytesIO()
    wb.save(buf)
    buf.seek(0)
    return buf.getvalue()

def gerar_romaneio_xlsx(lote_row, pecas_df, endereco_obra: str, digitado_por: str) -> bytes:
    """Gera o romaneio .xlsx com as peças do lote."""
    from openpyxl import Workbook
    from openpyxl.styles import Font, PatternFill, Alignment, Border, Side
    from io import BytesIO

    wb = Workbook()
    ws = wb.active
    ws.title = "Romaneio"
    ws.sheet_view.showGridLines = False
    ws.page_setup.orientation = "portrait"

    bd = Side(style='thin', color="000000")
    borda = Border(left=bd, right=bd, top=bd, bottom=bd)
    fill_cab = PatternFill(start_color="1E3A8A", end_color="1E3A8A", fill_type="solid")
    fill_sub = PatternFill(start_color="F1F5F9", end_color="F1F5F9", fill_type="solid")

    ws.column_dimensions['A'].width = 18
    ws.column_dimensions['B'].width = 20
    ws.column_dimensions['C'].width = 20
    ws.column_dimensions['D'].width = 14
    ws.column_dimensions['E'].width = 14

    # Cabeçalho
    ws.merge_cells("A1:E1")
    ws["A1"] = "PASSOLD SISTEMAS DE FACHADAS"
    ws["A1"].font = Font(name="Arial", size=14, bold=True, color="FFFFFF")
    ws["A1"].fill = fill_cab
    ws["A1"].alignment = Alignment(horizontal="center", vertical="center")
    ws.row_dimensions[1].height = 30

    ws.merge_cells("A2:E2")
    ws["A2"] = "ROMANEIO DE DESPACHO"
    ws["A2"].font = Font(name="Arial", size=12, bold=True, color="FFFFFF")
    ws["A2"].fill = fill_cab
    ws["A2"].alignment = Alignment(horizontal="center", vertical="center")

    # Informações do lote
    infos = [
        ("OP:", str(lote_row.get('Num_OP', '—'))),
        ("Obra:", str(lote_row.get('Obra_Vinculada', '—'))),
        ("Lote:", str(lote_row.get('Cod_Lote', '—'))),
        ("Endereço:", str(endereco_obra)),
        ("Digitado por:", str(digitado_por)),
        ("Data:", datetime.now().strftime('%d/%m/%Y')),
    ]
    linha = 3
    for label, valor in infos:
        ws.cell(linha, 1, label).font = Font(name="Arial", size=11, bold=True)
        ws.merge_cells(start_row=linha, start_column=2, end_row=linha, end_column=5)
        ws.cell(linha, 2, valor).font = Font(name="Arial", size=11)
        for c in range(1, 6):
            ws.cell(linha, c).border = borda
        linha += 1

    linha += 1

    # Cabeçalho da tabela de peças
    titulos = ["CÓDIGO", "LOCALIZAÇÃO", "MEDIDA", "QTD TOTAL", "QTD ENVIADA"]
    for col, titulo in enumerate(titulos, 1):
        cel = ws.cell(linha, col, titulo)
        cel.font = Font(name="Arial", size=11, bold=True, color="FFFFFF")
        cel.fill = fill_cab
        cel.alignment = Alignment(horizontal="center", vertical="center")
        cel.border = borda
    linha += 1

    # Peças
    for i, (_, peca) in enumerate(pecas_df.iterrows()):
        bg = fill_sub if i % 2 == 0 else PatternFill()
        dados = [
            peca.get('codigo', ''),
            peca.get('localizacao', ''),
            peca.get('medida', ''),
            peca.get('qtd_total', 0),
            peca.get('qtd_enviada', 0),
        ]
        for col, val in enumerate(dados, 1):
            cel = ws.cell(linha, col, val)
            cel.font = Font(name="Arial", size=11)
            cel.alignment = Alignment(horizontal="center", vertical="center")
            cel.border = borda
            if i % 2 == 0:
                cel.fill = fill_sub
        linha += 1

    # Totais
    linha += 1
    ws.merge_cells(start_row=linha, start_column=1, end_row=linha, end_column=3)
    ws.cell(linha, 1, "TOTAL DE PEÇAS:").font = Font(name="Arial", size=11, bold=True)
    ws.cell(linha, 4, int(pecas_df['qtd_total'].sum()) if not pecas_df.empty else 0).font = Font(name="Arial", size=11, bold=True)
    for c in range(1, 6):
        ws.cell(linha, c).border = borda

    # Assinaturas
    linha += 3
    assinaturas = [
        "Conferência Interna",
        "Nome Motorista / Data",
        "Recebedor na Obra / Data",
        "Engenheiro Responsável",
    ]
    for ass in assinaturas:
        ws.merge_cells(start_row=linha, start_column=1, end_row=linha, end_column=3)
        ws.cell(linha, 1).border = Border(bottom=bd)
        ws.cell(linha, 1, "").font = Font(name="Arial", size=11)
        ws.cell(linha+1, 1, ass).font = Font(name="Arial", size=10, bold=True)
        ws.cell(linha, 4, "____/____/______").font = Font(name="Arial", size=11)
        linha += 3

    buf = BytesIO()
    wb.save(buf)
    buf.seek(0)
    return buf.getvalue()

# ========================================================
# FUNÇÕES DO SISTEMA DE MEDIÇÃO — agora no banco
# ========================================================
@st.cache_data(ttl=30)
def carregar_medicao_obras():
    conn = conectar_banco()
    try:
        df = pd.read_sql_query("SELECT * FROM medicao_obras ORDER BY id", conn)
    finally:
        liberar_conexao(conn)
    return df

@st.cache_data(ttl=30)
def carregar_medicao_servicos(obra_id: int):
    conn = conectar_banco()
    try:
        df = pd.read_sql_query(
            "SELECT * FROM medicao_servicos WHERE obra_id=%s ORDER BY id", conn, params=(obra_id,)
        )
    finally:
        liberar_conexao(conn)
    return df

@st.cache_data(ttl=30)
def carregar_medicao_subdivisoes(servico_id: int):
    conn = conectar_banco()
    try:
        df = pd.read_sql_query(
            "SELECT * FROM medicao_subdivisoes WHERE servico_id=%s ORDER BY id", conn, params=(servico_id,)
        )
    finally:
        liberar_conexao(conn)
    return df

@st.cache_data(ttl=30)
def carregar_medicao_historico(obra_id: int):
    conn = conectar_banco()
    try:
        df = pd.read_sql_query(
            "SELECT * FROM medicao_historico WHERE obra_id=%s ORDER BY periodo", conn, params=(obra_id,)
        )
    finally:
        liberar_conexao(conn)
    return df

def salvar_medicao_obra(nome, valor_m2, metragem):
    conn = conectar_banco()
    try:
        cursor = conn.cursor()
        cursor.execute(
            "INSERT INTO medicao_obras (nome, valor_m2_global, metragem_geral) VALUES (%s,%s,%s) RETURNING id",
            (nome, valor_m2, metragem)
        )
        new_id = cursor.fetchone()[0]
        conn.commit()
        carregar_medicao_obras.clear()
        return new_id
    except Exception as e:
        conn.rollback()
        st.error(f"Erro ao salvar obra: {e}")
        return None
    finally:
        liberar_conexao(conn)

def excluir_medicao_obra(obra_id):
    conn = conectar_banco()
    try:
        cursor = conn.cursor()
        cursor.execute("DELETE FROM medicao_obras WHERE id=%s", (obra_id,))
        conn.commit()
        carregar_medicao_obras.clear()
        carregar_medicao_servicos.clear()
        carregar_medicao_subdivisoes.clear()
        carregar_medicao_historico.clear()
    except Exception as e:
        conn.rollback()
        st.error(f"Erro ao excluir obra: {e}")
    finally:
        liberar_conexao(conn)

def salvar_servicos_medicao(obra_id: int, periodo: str, servicos: list):
    """Salva serviços, subdivisões e snapshot do histórico para o período."""
    conn = conectar_banco()
    try:
        cursor = conn.cursor()
        # Apaga serviços antigos e recria (substituição total)
        cursor.execute("DELETE FROM medicao_servicos WHERE obra_id=%s", (obra_id,))
        total_medido = 0.0
        snapshot = []
        for srv in servicos:
            cursor.execute(
                "INSERT INTO medicao_servicos (obra_id, nome, valor_m2_servico) VALUES (%s,%s,%s) RETURNING id",
                (obra_id, srv['nome'], srv['valor_m2_servico'])
            )
            srv_id = cursor.fetchone()[0]
            subs_snap = []
            for sub in srv['subdivisoes']:
                cursor.execute(
                    "INSERT INTO medicao_subdivisoes (servico_id, nome, m2, percentual) VALUES (%s,%s,%s,%s)",
                    (srv_id, sub['nome'], sub['m2'], sub['percentual'])
                )
                val = sub['m2'] * (srv['valor_m2_servico'] * (sub['percentual'] / 100))
                total_medido += val
                subs_snap.append({**sub, 'subtotal': val})
            snapshot.append({**srv, 'subdivisoes': subs_snap})
        import json
        cursor.execute("""
            INSERT INTO medicao_historico (obra_id, periodo, total_medido, snapshot)
            VALUES (%s,%s,%s,%s)
            ON CONFLICT (obra_id, periodo)
            DO UPDATE SET total_medido=EXCLUDED.total_medido, snapshot=EXCLUDED.snapshot, criado_em=NOW()
        """, (obra_id, periodo, total_medido, json.dumps(snapshot)))
        conn.commit()
        carregar_medicao_servicos.clear()
        carregar_medicao_subdivisoes.clear()
        carregar_medicao_historico.clear()
        return total_medido
    except Exception as e:
        conn.rollback()
        st.error(f"Erro ao salvar serviços: {e}")
        return None
    finally:
        liberar_conexao(conn)

# ========================================================
# HELPER — BLOCOS SEMANAIS
# ========================================================
def blocos_semanais(df_input):
    if df_input.empty:
        st.info("Nenhum lote encontrado.")
        return
    df_input = df_input.copy()
    df_input['Ano_Semana'] = df_input['Data_Producao_Programada'].dt.isocalendar().year
    df_input['Num_Semana'] = df_input['Data_Producao_Programada'].dt.isocalendar().week

    def fmt_sem(r):
        try:
            s = pd.to_datetime(f"{int(r['Ano_Semana'])}-W{int(r['Num_Semana'])}-1", format="%G-W%V-%u")
            return f"Semana {int(r['Num_Semana']):02d} ({s.strftime('%d/%m')} – {(s + timedelta(days=6)).strftime('%d/%m/%Y')})"
        except Exception:
            return f"Semana {r['Num_Semana']}"

    df_input['Periodo'] = df_input.apply(fmt_sem, axis=1)
    semanas_unicas = df_input[['Ano_Semana', 'Num_Semana', 'Periodo']].drop_duplicates().sort_values(['Ano_Semana', 'Num_Semana'])

    for _, sem_row in semanas_unicas.iterrows():
        lotes_sem = df_input[df_input['Periodo'] == sem_row['Periodo']]
        total_m2  = lotes_sem['M2_Item'].sum()
        n_lotes   = len(lotes_sem)
        with st.expander(f"📅 {sem_row['Periodo']}  —  {n_lotes} lote(s)  |  {total_m2:.2f} m²", expanded=False):
            for _, lrow in lotes_sem.iterrows():
                dt_ini = pd.to_datetime(lrow['Data_Producao_Programada']).strftime('%d/%m/%Y')
                dt_fim = pd.to_datetime(lrow['Data_Limite_Obra']).strftime('%d/%m/%Y')
                st.markdown(
                    f'<span class="badge-obra">{lrow["Obra_Vinculada"]}</span>&nbsp;'
                    f'<span class="badge-edt">{lrow["EDT_Vinculado"]}</span>&nbsp;'
                    f'<span class="badge-lote">{lrow["Cod_Lote"]}</span>',
                    unsafe_allow_html=True
                )
                st.markdown(f"**{lrow['Tipo_Material']}** &nbsp;|&nbsp; `{int(lrow['Qtd_Caixas'])} caixas` — {lrow['M2_Item']:.2f} m²")
                st.caption(f"Período: {dt_ini} a {dt_fim} &nbsp;|&nbsp; {lrow['Romaneio_Chapas']}")
                op_txt = lrow['Num_OP'] if lrow.get('Num_OP') else "Aguardando OP"
                st.caption(f"OP: {op_txt} &nbsp;|&nbsp; {lrow.get('Fase_Produtiva', '—')}")
                st.markdown("---")

# ========================================================
# LOGIN
# ========================================================
if 'autenticado' not in st.session_state:
    st.session_state.autenticado   = False
    st.session_state.usuario_nome  = ""
    st.session_state.usuario_setor = ""

if not st.session_state.autenticado:
    col1, col2, col3 = st.columns([1, 2, 1])
    with col2:
        ci1, ci2, ci3 = st.columns([1, 2, 1])
        with ci2:
            st.image("assets/LOGO_BAUDENPASSOLD.png", use_container_width=True)
        st.markdown("""
        <p style='text-align:center; color:#64748B; font-size:13px; margin-top:8px; letter-spacing:0.05em;'>
        PCP & Controle Operacional
        </p>
        """, unsafe_allow_html=True)
        with st.container(border=True):
            st.markdown("<p style='text-align:center;font-size:16px;font-weight:600;color:#0F172A;margin-bottom:8px;'>Acesso ao Sistema</p>", unsafe_allow_html=True)
            user_input = st.text_input("Usuário:")
            pass_input = st.text_input("Senha:", type="password")
            if st.button("Entrar", use_container_width=True):
                with st.spinner("Verificando..."):
                    dados = verificar_login(user_input.strip(), pass_input)
                if dados:
                    st.session_state.autenticado   = True
                    st.session_state.usuario_nome  = dados[0]
                    st.session_state.usuario_setor = dados[1]
                    st.rerun()
                else:
                    st.error("Usuário ou senha inválidos.")
    st.stop()

# ========================================================
# HEADER
# ========================================================
ch1, ch2 = st.columns([4, 1])
with ch1:
    st.title("Passold Sistemas de Fachadas - Gestão Industrial")
    st.caption(f"Usuário: **{st.session_state.usuario_nome}** | Setor: `{st.session_state.usuario_setor}`")
with ch2:
    st.write("")
    if st.button("Sair"):
        st.session_state.autenticado = False
        st.rerun()

df_banco_macro = carregar_macro()
df_banco_micro = carregar_micro()

if not df_banco_macro.empty:
    obras_lista      = sorted(df_banco_macro['Obra'].unique().tolist())
    obra_selecionada = st.selectbox("Obra de trabalho:", obras_lista)
    df_macro_filtrado = carregar_macro_por_obra(obra_selecionada)
else:
    obra_selecionada  = None
    df_macro_filtrado = pd.DataFrame()

# ========================================================
# ABAS
# ========================================================
setor = st.session_state.usuario_setor
abas_disponiveis = []
if setor in ["Master", "Producao", "Diretoria", "Engenharia"]:
    abas_disponiveis.append("Painel da Producao - ACM")
if setor in ["Master", "Producao", "Diretoria"]:
    abas_disponiveis.append("Painel TV — ACM")
if setor in ["Master", "PCP"]:
    abas_disponiveis.append("Liberar OPs da Semana")
if setor in ["Master", "Diretoria"]:
    abas_disponiveis.append("Visao Macro")
if setor in ["Master"]:
    abas_disponiveis.append("Vincular Datas")
    abas_disponiveis.append("Cadastrar Obra")
if setor in ["Master", "Engenharia"]:
    abas_disponiveis.append("Painel de Engenharia")
if setor in ["Master", "Logistica"]:
    abas_disponiveis.append("Logistica")
if setor in ["Master", "Almoxarifado"]:
    abas_disponiveis.append("Almoxarifado")
if setor in ["Master", "Medicao"]:
    abas_disponiveis.append("Sistema de Medicao")
if setor in ["Master"]:
    abas_disponiveis.append("Configuracoes")

with st.container():
    abas_objetos = st.tabs(abas_disponiveis)

for nome_aba, aba_objeto in zip(abas_disponiveis, abas_objetos):

    # ==================================================
    # PAINEL DA PRODUCAO ACM
    # ==================================================
    if nome_aba == "Painel da Producao - ACM":
        with aba_objeto:
            st.header("Mural de Metas — Producao")
            obras_tv = ["Todas as obras"] + (
                list(df_banco_micro['Obra_Vinculada'].dropna().unique()) if not df_banco_micro.empty else []
            )
            obra_tv = st.selectbox("Filtrar por obra:", obras_tv, key="sb_obra_tv")

            st.markdown("### 📋 Previsão de Entrada em Produção")
            st.caption("Lotes planejados no Vincular Datas — ainda não liberados oficialmente.")
            df_prev = df_banco_micro.copy() if not df_banco_micro.empty else pd.DataFrame()
            if obra_tv != "Todas as obras" and not df_prev.empty:
                df_prev = df_prev[df_prev['Obra_Vinculada'] == obra_tv]
            df_prev_pend = df_prev[df_prev['Status_Item'] == 'Pendente'].copy() if not df_prev.empty else pd.DataFrame()
            if df_prev_pend.empty:
                st.info("Nenhuma previsão pendente.")
            else:
                blocos_semanais(df_prev_pend)

            st.markdown("---")
            st.markdown("### 📆 Calendário de Produção — OPs Liberadas")
            st.caption("Apenas lotes liberados oficialmente na aba 'Liberar OPs da Semana'.")
            if not df_banco_micro.empty:
                df_base = df_banco_micro[df_banco_micro['Status_Item'].isin(["Liberado para Fabrica", "Parcialmente Concluido"])].copy()
                if obra_tv != "Todas as obras":
                    df_base = df_base[df_base['Obra_Vinculada'] == obra_tv]
                if not df_base.empty:
                    registros_exp = []
                    for _, row in df_base.iterrows():
                        dt_ini = pd.to_datetime(row['Data_Producao_Programada']).date()
                        dt_fim = pd.to_datetime(row['Data_Limite_Obra']).date()
                        ini_ultima_semana = (pd.to_datetime(dt_fim) - timedelta(days=6)).date()
                        ini_ultima_semana = max(ini_ultima_semana, dt_ini)
                        dia = dt_ini
                        while dia <= dt_fim:
                            r = row.to_dict()
                            r['_dia'] = dia
                            r['_pode_concluir'] = (dia >= ini_ultima_semana)
                            registros_exp.append(r)
                            dia += timedelta(days=1)
                    df_exp = pd.DataFrame(registros_exp) if registros_exp else pd.DataFrame()

                    if "prog_mes" not in st.session_state:
                        st.session_state.prog_mes = HOJE_PROJETO.month
                    if "prog_ano" not in st.session_state:
                        st.session_state.prog_ano = HOJE_PROJETO.year

                    c1, c2, c3 = st.columns([1, 2, 1])
                    with c1:
                        if st.button("Mes Anterior", use_container_width=True, key="btn_ant"):
                            st.session_state.prog_mes -= 1
                            if st.session_state.prog_mes == 0:
                                st.session_state.prog_mes = 12
                                st.session_state.prog_ano -= 1
                            st.rerun()
                    with c2:
                        nomes_meses = ["", "Janeiro", "Fevereiro", "Marco", "Abril", "Maio", "Junho",
                                       "Julho", "Agosto", "Setembro", "Outubro", "Novembro", "Dezembro"]
                        st.markdown(
                            f"<h3 style='text-align:center;color:#1E3A8A;margin:0;'>"
                            f"{nomes_meses[st.session_state.prog_mes]} / {st.session_state.prog_ano}</h3>",
                            unsafe_allow_html=True
                        )
                    with c3:
                        if st.button("Proximo Mes", use_container_width=True, key="btn_prox"):
                            st.session_state.prog_mes += 1
                            if st.session_state.prog_mes == 13:
                                st.session_state.prog_mes = 1
                                st.session_state.prog_ano += 1
                            st.rerun()

                    st.markdown("---")
                    cal     = py_calendar.Calendar(firstweekday=6)
                    semanas = cal.monthdatescalendar(st.session_state.prog_ano, st.session_state.prog_mes)
                    cols_h  = st.columns(7)
                    for i, nome in enumerate(["Dom", "Seg", "Ter", "Qua", "Qui", "Sex", "Sab"]):
                        cols_h[i].markdown(
                            f"<div style='text-align:center;font-weight:600;color:#475569;padding:4px 0;font-size:13px;'>{nome}</div>",
                            unsafe_allow_html=True
                        )
                    for semana in semanas:
                        cols = st.columns(7)
                        for i, data_dia in enumerate(semana):
                            with cols[i]:
                                if data_dia.month == st.session_state.prog_mes:
                                    lotes_dia = df_exp[df_exp['_dia'] == data_dia] if not df_exp.empty else pd.DataFrame()
                                    n_lotes   = lotes_dia['Cod_Lote'].nunique() if not lotes_dia.empty else 0
                                    eh_hoje   = (data_dia == HOJE_PROJETO.date())
                                    if n_lotes > 0:
                                        obras_d   = lotes_dia['Obra_Vinculada'].unique()
                                        label_o   = obras_d[0] if len(obras_d) == 1 else f"{len(obras_d)} obras"
                                        btn_label = f"{data_dia.day}  |  {n_lotes} lote(s)\n{label_o}"
                                        if st.button(btn_label, key=f"btn_{data_dia}", use_container_width=True):
                                            st.session_state.dia_clicado_tv = data_dia
                                    else:
                                        css_class = "cal-day-today" if eh_hoje else "cal-day-empty"
                                        st.markdown(
                                            f"<div class='{css_class}'><span style='color:#94A3B8;font-size:15px;'>{data_dia.day}</span>"
                                            f"<br><span style='color:#CBD5E1;font-size:10px;'>—</span></div>",
                                            unsafe_allow_html=True
                                        )
                                else:
                                    st.markdown('<div style="height:70px;"></div>', unsafe_allow_html=True)

                    st.markdown("---")
                    if "dia_clicado_tv" not in st.session_state:
                        st.session_state.dia_clicado_tv = HOJE_PROJETO.date()
                    dia_sel   = st.session_state.dia_clicado_tv
                    st.subheader(f"Lotes em producao — {dia_sel.strftime('%d/%m/%Y')}")
                    lotes_sel = (
                        df_exp[df_exp['_dia'] == dia_sel].drop_duplicates(subset=['id'])
                        if not df_exp.empty else pd.DataFrame()
                    )
                    if lotes_sel.empty:
                        st.info("Clique em um dia com lotes no calendario acima.")
                    else:
                        kc1, kc2, kc3 = st.columns(3)
                        kc1.metric("Lotes em producao", lotes_sel['Cod_Lote'].nunique())
                        kc2.metric("Total caixas", int(lotes_sel['Qtd_Caixas'].sum()))
                        kc3.metric("Total m²", f"{lotes_sel['M2_Item'].sum():.2f}")
                        st.markdown("---")
                        for _, row in lotes_sel.iterrows():
                            pode_concluir = bool(row.get('_pode_concluir', False))
                            dt_i = pd.to_datetime(row['Data_Producao_Programada']).strftime('%d/%m/%Y')
                            dt_f = pd.to_datetime(row['Data_Limite_Obra']).strftime('%d/%m/%Y')
                            border_color = "#EA580C" if pode_concluir else "#3B82F6"
                            bg_color     = "#FFF7ED" if pode_concluir else "#F8FAFC"
                            st.markdown(
                                f"<div style='border-left:4px solid {border_color};background:{bg_color};"
                                f"padding:12px 16px;border-radius:6px;margin-bottom:4px;'></div>",
                                unsafe_allow_html=True
                            )
                            with st.container(border=True):
                                cd, ca = st.columns([4, 1])
                                with cd:
                                    st.markdown(
                                        f'<span class="badge-obra">{row["Obra_Vinculada"]}</span>&nbsp;'
                                        f'<span class="badge-edt">{row["EDT_Vinculado"]}</span>&nbsp;'
                                        f'<span class="badge-lote">{row["Cod_Lote"]}</span>',
                                        unsafe_allow_html=True
                                    )
                                    st.markdown(f"**{row['Tipo_Material']}** &nbsp;|&nbsp; `{int(row['Qtd_Caixas'])} caixas` — {row['M2_Item']:.2f} m²")
                                    st.caption(f"Periodo: {dt_i} a {dt_f} &nbsp;|&nbsp; {row['Romaneio_Chapas']}")
                                    op_txt = row['Num_OP'] if row.get('Num_OP') else "Aguardando OP"
                                    st.caption(f"OP: {op_txt} &nbsp;|&nbsp; {row.get('Fase_Produtiva', '—')}")
                                    if pode_concluir:
                                        status_atual = row.get('Status_Item', '')
                                        if status_atual == 'Parcialmente Concluido':
                                            st.markdown("<span style='color:#D97706;font-size:12px;font-weight:700;'>🟠 Envio parcial anterior registrado — ainda há peças pendentes</span>", unsafe_allow_html=True)
                                        else:
                                            st.markdown("<span style='color:#EA580C;font-size:12px;font-weight:600;'>Ultima semana — liberado para concluir</span>", unsafe_allow_html=True)
                                    else:
                                        dias_restantes = (pd.to_datetime(row['Data_Limite_Obra']).date() - dia_sel).days
                                        st.markdown(f"<span style='color:#3B82F6;font-size:12px;'>Em producao — {dias_restantes} dias ate o prazo</span>", unsafe_allow_html=True)
                                with ca:
                                    if pode_concluir:
                                        st.write("")
                                        if st.button("✅ Pronto", key=f"baixa_{row['id']}", type="primary", use_container_width=True):
                                            st.session_state[f"modal_pronto_{row['id']}"] = not st.session_state.get(f"modal_pronto_{row['id']}", False)
                                            st.rerun()
                                    else:
                                        st.markdown("<div style='text-align:center;color:#94A3B8;font-size:12px;padding:8px;'>Em producao</div>", unsafe_allow_html=True)

                            # ── MODAL EM LARGURA TOTAL ─────────────────────────
                            if st.session_state.get(f"modal_pronto_{row['id']}", False):
                                with st.container(border=True):
                                    st.markdown(f"#### 📦 `{row['Cod_Lote']}` — {row['Obra_Vinculada']} — Tipo de Envio")
                                    limite_desp = None
                                    if not df_banco_macro.empty:
                                        fr = df_banco_macro[df_banco_macro['EDT'] == row['EDT_Vinculado']]
                                        if not fr.empty:
                                            limite_desp = fr.iloc[0].get('Data_Limite_Despacho')

                                    me1, me2 = st.columns([2, 3])
                                    with me1:
                                        tipo_envio = st.radio(
                                            "Este envio é:",
                                            ["Envio Total", "Envio Parcial"],
                                            key=f"tipo_envio_{row['id']}",
                                            horizontal=True
                                        )

                                    if tipo_envio == "Envio Total":
                                        with me2:
                                            st.info("Todas as peças serão marcadas como concluídas e enviadas para logística.")
                                        bt1, bt2, _ = st.columns([2, 2, 4])
                                        with bt1:
                                            if st.button("✅ Confirmar Total", key=f"conf_total_{row['id']}", type="primary", use_container_width=True):
                                                conn = conectar_banco()
                                                try:
                                                    cursor = conn.cursor()
                                                    cursor.execute(
                                                        "UPDATE itens_detalhado SET Status_Item='Concluido' WHERE id=%s",
                                                        (row['id'],)
                                                    )
                                                    conn.commit()
                                                    _limpar_cache_geral()
                                                except Exception as e:
                                                    conn.rollback()
                                                    st.error(f"Erro: {e}")
                                                finally:
                                                    liberar_conexao(conn)
                                                enviar_para_logistica(row, limite_desp if prazo_valido(limite_desp) else pd.NaT)
                                                st.session_state[f"modal_pronto_{row['id']}"] = False
                                                st.toast(f"✅ {row['Cod_Lote']} concluido!")
                                                time.sleep(0.3)
                                                st.rerun()
                                        with bt2:
                                            if st.button("Cancelar", key=f"cancel_total_{row['id']}", use_container_width=True):
                                                st.session_state[f"modal_pronto_{row['id']}"] = False
                                                st.rerun()

                                    else:
                                        # Envio Parcial
                                        df_pecas_parc = carregar_pecas_lote(int(row['id']))
                                        if df_pecas_parc.empty:
                                            st.warning("⚠️ Nenhuma peça lançada para este lote. Lance as peças na aba 'Liberar OPs da Semana' primeiro.")
                                            if st.button("Fechar", key=f"cancel_parc_{row['id']}"):
                                                st.session_state[f"modal_pronto_{row['id']}"] = False
                                                st.rerun()
                                        else:
                                            st.caption("Informe quantas unidades de cada peça estão prontas para este envio:")
                                            st.markdown("---")

                                            pecas_envio = []
                                            # Cabeçalho da tabela
                                            th1, th2, th3, th4, th5 = st.columns([3, 2, 2, 1, 2])
                                            th1.markdown("**Código**")
                                            th2.markdown("**Localização**")
                                            th3.markdown("**Medida**")
                                            th4.markdown("**Saldo**")
                                            th5.markdown("**Enviar agora**")
                                            st.markdown("<hr style='margin:4px 0;'>", unsafe_allow_html=True)

                                            for _, peca in df_pecas_parc.iterrows():
                                                saldo_peca = int(peca.get('saldo', 0))
                                                if saldo_peca <= 0:
                                                    pc1, pc2, pc3, pc4, pc5 = st.columns([3, 2, 2, 1, 2])
                                                    pc1.markdown(f"~~{peca['codigo']}~~")
                                                    pc5.markdown("✅ enviado")
                                                    continue
                                                pc1, pc2, pc3, pc4, pc5 = st.columns([3, 2, 2, 1, 2])
                                                pc1.markdown(f"**{peca['codigo']}**")
                                                pc2.markdown(peca.get('localizacao', '—'))
                                                pc3.markdown(peca.get('medida', '—'))
                                                pc4.markdown(f"`{saldo_peca}`")
                                                with pc5:
                                                    qtd_enviar = st.number_input(
                                                        "",
                                                        min_value=0,
                                                        max_value=saldo_peca,
                                                        value=saldo_peca,
                                                        key=f"parc_{row['id']}_{peca['id']}",
                                                        label_visibility="collapsed"
                                                    )
                                                if qtd_enviar > 0:
                                                    pecas_envio.append({
                                                        "peca_id":    int(peca['id']),
                                                        "codigo":     peca['codigo'],
                                                        "qtd_enviar": qtd_enviar,
                                                        "saldo_atual": saldo_peca
                                                    })

                                            st.markdown("---")
                                            bp1, bp2, _ = st.columns([2, 2, 4])
                                            with bp1:
                                                if st.button("🟠 Confirmar Envio Parcial", key=f"conf_parc_{row['id']}", type="primary", use_container_width=True):
                                                    if not pecas_envio:
                                                        st.error("Selecione pelo menos uma peça.")
                                                    else:
                                                        conn = conectar_banco()
                                                        try:
                                                            cursor = conn.cursor()
                                                            todas_zeradas = True
                                                            for pe in pecas_envio:
                                                                novo_saldo = pe['saldo_atual'] - pe['qtd_enviar']
                                                                if novo_saldo > 0:
                                                                    todas_zeradas = False
                                                                cursor.execute("""
                                                                    UPDATE op_pecas
                                                                    SET qtd_enviada = qtd_enviada + %s,
                                                                        saldo = saldo - %s
                                                                    WHERE id=%s
                                                                """, (pe['qtd_enviar'], pe['qtd_enviar'], pe['peca_id']))
                                                            novo_status = 'Concluido' if todas_zeradas else 'Parcialmente Concluido'
                                                            cursor.execute(
                                                                "UPDATE itens_detalhado SET Status_Item=%s WHERE id=%s",
                                                                (novo_status, int(row['id']))
                                                            )
                                                            conn.commit()
                                                            _limpar_cache_geral()
                                                            carregar_pecas_lote.clear()
                                                        except Exception as e:
                                                            conn.rollback()
                                                            st.error(f"Erro: {e}")
                                                        finally:
                                                            liberar_conexao(conn)
                                                        enviar_para_logistica(row, limite_desp if prazo_valido(limite_desp) else pd.NaT)
                                                        st.session_state[f"modal_pronto_{row['id']}"] = False
                                                        emoji_t = "✅" if todas_zeradas else "🟠"
                                                        st.toast(f"{emoji_t} {row['Cod_Lote']} — {'Concluido!' if todas_zeradas else 'Envio parcial registrado!'}")
                                                        time.sleep(0.3)
                                                        st.rerun()
                                            with bp2:
                                                if st.button("Cancelar", key=f"cancel_parc2_{row['id']}", use_container_width=True):
                                                    st.session_state[f"modal_pronto_{row['id']}"] = False
                                                    st.rerun()
                else:
                    st.info("Nenhuma OP liberada para este filtro ainda.")
            else:
                st.info("Nenhum lote liberado no sistema ainda.")

    # ==================================================
    # PAINEL TV — ACM
    # ==================================================
    elif nome_aba == "Painel TV — ACM":
        with aba_objeto:
            if 'tv_last_refresh' not in st.session_state:
                st.session_state.tv_last_refresh = time.time()
            agora   = time.time()
            elapsed = agora - st.session_state.tv_last_refresh
            segundos_restantes = max(0, int(30 - elapsed))

            st.markdown(f"""
            <div style='background: linear-gradient(135deg, #0F172A 0%, #1E3A8A 100%);
                        padding: 18px 28px; border-radius: 12px; display: flex;
                        align-items: center; justify-content: space-between; margin-bottom: 24px;'>
                <div>
                    <span style='color:#FFFFFF;font-size:26px;font-weight:800;letter-spacing:-0.03em;'>
                        Passold — Painel de Produção ACM
                    </span><br>
                    <span style='color:#93C5FD;font-size:13px;'>
                        {datetime.now(FUSO_BR).strftime('%d/%m/%Y  %H:%M')}
                    </span>
                </div>
                <div style='text-align:right;'>
                    <span style='color:#94A3B8;font-size:12px;'>Atualiza em</span><br>
                    <span style='color:#FCD34D;font-size:22px;font-weight:700;'>{segundos_restantes}s</span>
                </div>
            </div>
            """, unsafe_allow_html=True)

            df_tv = carregar_micro()
            if df_tv.empty:
                st.markdown("<div style='text-align:center;padding:60px;color:#94A3B8;font-size:20px;'>Nenhum lote cadastrado.</div>", unsafe_allow_html=True)
            else:
                def urgencia(row):
                    prazo = row.get('Data_Limite_Obra')
                    if not prazo_valido(prazo): return 'sem_prazo'
                    dias = (pd.to_datetime(prazo).normalize() - HOJE_PROJETO).days
                    if dias < 0:   return 'vencido'
                    if dias <= 3:  return 'critico'
                    if dias <= 7:  return 'atencao'
                    return 'ok'

                df_tv['_urgencia'] = df_tv.apply(urgencia, axis=1)
                df_tv['_dias_restantes'] = df_tv['Data_Limite_Obra'].apply(
                    lambda x: (pd.to_datetime(x).normalize() - HOJE_PROJETO).days if prazo_valido(x) else 9999
                )
                df_tv = df_tv.sort_values('_dias_restantes')

                STATUS_EMOJI = {
                    'Pendente':                ('⏳', '#64748B', '#F1F5F9'),
                    'Liberado para Fabrica':   ('🔧', '#1D4ED8', '#EFF6FF'),
                    'Parcialmente Concluido':  ('🟠', '#D97706', '#FFFBEB'),
                    'Concluido':               ('✅', '#15803D', '#F0FDF4'),
                }
                URG_CONFIG = {
                    'vencido':   {'border': '#DC2626', 'bg': '#FEF2F2', 'tag': '🔴 VENCIDO',  'tag_color': '#DC2626'},
                    'critico':   {'border': '#EA580C', 'bg': '#FFF7ED', 'tag': '🟠 URGENTE',  'tag_color': '#EA580C'},
                    'atencao':   {'border': '#D97706', 'bg': '#FFFBEB', 'tag': '🟡 ATENÇÃO',  'tag_color': '#D97706'},
                    'ok':        {'border': '#059669', 'bg': '#F0FDF4', 'tag': '🟢 NO PRAZO', 'tag_color': '#059669'},
                    'sem_prazo': {'border': '#94A3B8', 'bg': '#F8FAFC', 'tag': '⚪ SEM PRAZO','tag_color': '#94A3B8'},
                }

                urgentes = df_tv[df_tv['_urgencia'].isin(['vencido', 'critico'])]
                demais   = df_tv[df_tv['_urgencia'].isin(['atencao', 'ok', 'sem_prazo'])]

                if not urgentes.empty:
                    st.markdown(f"""
                    <div style='background:#FEF2F2;border:1px solid #FECACA;border-radius:8px;padding:10px 18px;margin-bottom:16px;'>
                        <span style='color:#DC2626;font-weight:700;font-size:15px;'>⚠️ {len(urgentes)} lote(s) crítico(s) ou vencido(s)</span>
                    </div>
                    """, unsafe_allow_html=True)
                    cols_urg = st.columns(min(len(urgentes), 3))
                    for i, (_, row) in enumerate(urgentes.iterrows()):
                        urg  = row['_urgencia']
                        cfg  = URG_CONFIG[urg]
                        dias = row['_dias_restantes']
                        dias_txt  = f"Vencido há {abs(dias)}d" if dias < 0 else f"Faltam {dias} dia(s)"
                        em, ec, _ = STATUS_EMOJI.get(row['Status_Item'], ('❓', '#64748B', '#F8FAFC'))
                        prazo_fmt = pd.to_datetime(row['Data_Limite_Obra']).strftime('%d/%m/%Y') if prazo_valido(row['Data_Limite_Obra']) else '—'
                        op_txt    = row['Num_OP'] if row.get('Num_OP') else 'S/ OP'
                        with cols_urg[i % 3]:
                            st.markdown(f"""
                            <div style='border:2px solid {cfg["border"]};background:{cfg["bg"]};border-radius:10px;padding:18px 20px;margin-bottom:12px;box-shadow:0 4px 12px rgba(0,0,0,0.10);'>
                                <div style='display:flex;justify-content:space-between;align-items:center;margin-bottom:10px;'>
                                    <span style='font-size:11px;font-weight:700;color:{cfg["tag_color"]};border:1px solid {cfg["border"]};padding:2px 8px;border-radius:4px;'>{cfg["tag"]}</span>
                                    <span style='font-size:11px;color:#64748B;font-weight:600;'>{dias_txt}</span>
                                </div>
                                <div style='font-size:20px;font-weight:800;color:#0F172A;margin-bottom:4px;'>{row["Obra_Vinculada"]}</div>
                                <div style='font-size:13px;color:#475569;margin-bottom:12px;'>{row["Tipo_Material"]} · {row["Romaneio_Chapas"] or "—"}</div>
                                <div style='display:grid;grid-template-columns:1fr 1fr;gap:8px;'>
                                    <div style='background:white;border-radius:6px;padding:8px 10px;'><div style='font-size:10px;color:#94A3B8;text-transform:uppercase;'>OP</div><div style='font-size:15px;font-weight:700;color:#1E293B;'>{op_txt}</div></div>
                                    <div style='background:white;border-radius:6px;padding:8px 10px;'><div style='font-size:10px;color:#94A3B8;text-transform:uppercase;'>M²</div><div style='font-size:15px;font-weight:700;color:#1E293B;'>{row["M2_Item"]:.2f}</div></div>
                                    <div style='background:white;border-radius:6px;padding:8px 10px;'><div style='font-size:10px;color:#94A3B8;text-transform:uppercase;'>Status</div><div style='font-size:13px;font-weight:700;color:{ec};'>{em} {row["Status_Item"]}</div></div>
                                    <div style='background:white;border-radius:6px;padding:8px 10px;'><div style='font-size:10px;color:#94A3B8;text-transform:uppercase;'>Prazo</div><div style='font-size:15px;font-weight:700;color:{cfg["tag_color"]};'>{prazo_fmt}</div></div>
                                </div>
                            </div>
                            """, unsafe_allow_html=True)

                if not demais.empty:
                    st.markdown("---")
                    st.markdown("<span style='font-size:15px;font-weight:700;color:#334155;'>📋 Demais lotes em andamento</span>", unsafe_allow_html=True)
                    st.markdown("<br>", unsafe_allow_html=True)
                    hc = st.columns([2, 3, 2, 2, 2])
                    for col_h, label in zip(hc, ["OP", "OBRA / MATERIAL", "M²", "STATUS", "PRAZO"]):
                        col_h.markdown(f"<div style='font-size:11px;font-weight:700;color:#94A3B8;text-transform:uppercase;letter-spacing:0.07em;'>{label}</div>", unsafe_allow_html=True)
                    st.markdown("<hr style='margin:4px 0 8px 0;border-color:#E2E8F0;'>", unsafe_allow_html=True)
                    for _, row in demais.iterrows():
                        urg = row['_urgencia']
                        cfg = URG_CONFIG[urg]
                        em, ec, ebg = STATUS_EMOJI.get(row['Status_Item'], ('❓', '#64748B', '#F8FAFC'))
                        prazo_fmt = pd.to_datetime(row['Data_Limite_Obra']).strftime('%d/%m/%Y') if prazo_valido(row['Data_Limite_Obra']) else '—'
                        dias      = row['_dias_restantes']
                        dias_txt  = f"+{dias}d" if dias < 9999 else "—"
                        op_txt    = row['Num_OP'] if row.get('Num_OP') else 'S/ OP'
                        rc = st.columns([2, 3, 2, 2, 2])
                        rc[0].markdown(f"<span style='font-size:13px;font-weight:600;color:#1E293B;'>{op_txt}</span>", unsafe_allow_html=True)
                        rc[1].markdown(f"<span style='font-size:13px;font-weight:700;color:#0F172A;'>{row['Obra_Vinculada']}</span><br><span style='font-size:11px;color:#64748B;'>{row['Tipo_Material']}</span>", unsafe_allow_html=True)
                        rc[2].markdown(f"<span style='font-size:14px;font-weight:700;color:#1E293B;'>{row['M2_Item']:.2f}</span>", unsafe_allow_html=True)
                        rc[3].markdown(f"<span style='background:{ebg};color:{ec};padding:3px 8px;border-radius:4px;font-size:12px;font-weight:600;'>{em} {row['Status_Item']}</span>", unsafe_allow_html=True)
                        rc[4].markdown(f"<span style='font-size:13px;font-weight:700;color:{cfg['tag_color']};'>{prazo_fmt}</span><br><span style='font-size:11px;color:#94A3B8;'>{dias_txt}</span>", unsafe_allow_html=True)
                        st.markdown("<hr style='margin:4px 0;border-color:#F1F5F9;'>", unsafe_allow_html=True)

            progress_val = (30 - segundos_restantes) / 30
            st.markdown("<br>", unsafe_allow_html=True)
            st.progress(progress_val, text=f"Próxima atualização em {segundos_restantes}s")
            if segundos_restantes == 0:
                st.session_state.tv_last_refresh = time.time()
                st.rerun()

    # ==================================================
    # LIBERAR OPS
    # ==================================================
    elif nome_aba == "Liberar OPs da Semana":
        with aba_objeto:
            st.header("Ordens de Producao — Liberacao Semanal")

            # ── SEÇÃO 1: LOTES PENDENTES DO FATIAMENTO ────────────
            st.markdown("### 📋 Seção 1 — Lotes Pendentes do Fatiamento")
            if obra_selecionada and not df_banco_micro.empty:
                df_pend = df_banco_micro[
                    (df_banco_micro['Obra_Vinculada'] == obra_selecionada) &
                    (df_banco_micro['Status_Item'] == "Pendente")
                ].copy()
                if not df_pend.empty:
                    df_pend['Selecionar'] = False
                    cols_exib = [c for c in ['id', 'Cod_Lote', 'Tipo_Material', 'Qtd_Caixas', 'M2_Item',
                                             'Fase_Produtiva', 'Data_Producao_Programada', 'Romaneio_Chapas', 'Selecionar']
                                 if c in df_pend.columns]
                    df_ed = st.data_editor(df_pend[cols_exib], hide_index=True, use_container_width=True,
                                           disabled=[c for c in cols_exib if c != 'Selecionar'])
                    ids_sel = df_ed[df_ed['Selecionar'] == True]['id'].tolist()
                    prefixo = st.text_input("Prefixo da OP:", value=f"OP-{datetime.now().strftime('%Y')}-")
                    if st.button("Liberar para producao"):
                        if ids_sel:
                            conn = conectar_banco()
                            try:
                                cursor = conn.cursor()
                                for item_id in ids_sel:
                                    cursor.execute(
                                        "UPDATE itens_detalhado SET Status_Item='Liberado para Fabrica', Num_OP=%s WHERE id=%s",
                                        (f"{prefixo}{str(item_id).zfill(3)}", item_id)
                                    )
                                conn.commit()
                                _limpar_cache_geral()
                            except Exception as e:
                                conn.rollback()
                                st.error(f"Erro: {e}")
                            finally:
                                liberar_conexao(conn)
                            st.toast("OPs liberadas!")
                            time.sleep(0.5)
                            st.rerun()
                        else:
                            st.warning("Selecione pelo menos um item.")
                else:
                    st.success("Todos os lotes ja foram liberados.")
            else:
                st.info("Nenhum lote pendente encontrado.")

            st.markdown("---")

            # ── SEÇÃO 2: LANÇAR PEÇAS DA OP ───────────────────────
            st.markdown("### 🔩 Seção 2 — Lançar Peças da OP")
            st.caption("Vincule os códigos reais das peças ao lote já liberado.")

            df_lib = df_banco_micro[
                (df_banco_micro['Obra_Vinculada'] == obra_selecionada) &
                (df_banco_micro['Status_Item'].isin(["Liberado para Fabrica", "Parcialmente Concluido"]))
            ].copy() if obra_selecionada and not df_banco_micro.empty else pd.DataFrame()

            if not df_lib.empty:
                opcoes_lotes = [
                    f"{row['Num_OP']} — {row['Cod_Lote']} | {row['Tipo_Material']} | {row['M2_Item']:.2f}m²"
                    for _, row in df_lib.iterrows() if row.get('Num_OP')
                ]
                if opcoes_lotes:
                    lote_sel_str = st.selectbox("Selecione o Lote / OP:", opcoes_lotes, key="sel_lote_pecas")
                    num_op_sel   = lote_sel_str.split(" — ")[0].strip()
                    row_lote     = df_lib[df_lib['Num_OP'] == num_op_sel].iloc[0]
                    lote_id      = int(row_lote['id'])
                    edt_lote     = row_lote.get('EDT_Vinculado', '')

                    # Info da etapa em cards limpos
                    if not df_banco_macro.empty and edt_lote:
                        fr_edt = df_banco_macro[df_banco_macro['EDT'] == edt_lote]
                        if not fr_edt.empty:
                            macro_row_sel   = fr_edt.iloc[0]
                            m2_total_edt    = float(macro_row_sel.get('M2_Total_Tarefa', 0) or 0)
                            m2_exec_edt     = float(macro_row_sel.get('m2_executado', 0) or 0)
                            m2_saldo_edt    = m2_total_edt - m2_exec_edt
                            num_proj_edt    = str(macro_row_sel.get('Numero_Projeto', '') or '')
                            tipo_esc_edt    = str(macro_row_sel.get('Tipo_Escopo', 'ACM') or 'ACM')
                            se1, se2, se3, se4 = st.columns(4)
                            se1.metric("Etapa", edt_lote)
                            se2.metric("Projeto", num_proj_edt or "—")
                            se3.metric("m² Total Etapa", f"{m2_total_edt:.2f}")
                            se4.metric("Saldo Etapa", f"{m2_saldo_edt:.2f} m²")
                        else:
                            macro_row_sel = {}
                            tipo_esc_edt  = "ACM"
                            num_proj_edt  = ""
                    else:
                        macro_row_sel = {}
                        tipo_esc_edt  = "ACM"
                        num_proj_edt  = ""

                    st.markdown("---")

                    # Peças já lançadas
                    df_pecas_existentes = carregar_pecas_lote(lote_id)

                    if not df_pecas_existentes.empty:
                        pc1, pc2 = st.columns([3, 1])
                        with pc1:
                            st.success(f"✅ {len(df_pecas_existentes)} peça(s) lançadas | "
                                       f"Total: {int(df_pecas_existentes['qtd_total'].sum())} un | "
                                       f"Saldo: {int(df_pecas_existentes['saldo'].sum())} un")
                        with pc2:
                            st.caption(f"Status comp.: **{df_pecas_existentes.iloc[0].get('componentes_status','—')}**")

                        with st.expander("📋 Ver peças lançadas", expanded=False):
                            st.dataframe(
                                df_pecas_existentes[['codigo', 'localizacao', 'medida', 'qtd_total', 'qtd_enviada', 'saldo']],
                                hide_index=True, use_container_width=True
                            )

                        # Gerar OP
                        st.markdown("#### 📄 Gerar Ordem de Produção")
                        with st.expander("Configurar e Gerar OP", expanded=False):
                            obs_op = st.text_area("Observações:", key="obs_op",
                                                   placeholder="Informações adicionais para a produção...")
                            campos_extras = {"observacoes": obs_op, "material": row_lote.get('Tipo_Material', '')}

                            if tipo_esc_edt.upper() == "ACM":
                                gf1, gf2 = st.columns(2)
                                with gf1:
                                    qtd_folhas = st.text_input("Qtd Folhas Projeto:", key="op_folhas", placeholder="Ex: 2")
                                with gf2:
                                    area_real = st.number_input("Área Total (m²):", value=float(row_lote.get('M2_Item', 0)), key="op_area")
                                campos_extras.update({
                                    "qtd_folhas": qtd_folhas,
                                    "area_total": area_real,
                                    "dificuldade": row_lote.get('Dificuldade', '—'),
                                    "material": row_lote.get('Tipo_Material', 'ACM')
                                })
                            elif "ESQUADRIA" in tipo_esc_edt.upper() or "VIDRO" in tipo_esc_edt.upper():
                                gf1, gf2 = st.columns(2)
                                with gf1:
                                    peso_total = st.text_input("Peso Total (kg):", key="op_peso", placeholder="Ex: 67,08kg")
                                with gf2:
                                    qtd_folhas = st.text_input("Qtd Folhas Projeto:", key="op_folhas2", placeholder="Ex: 2")
                                campos_extras.update({
                                    "peso_total": peso_total,
                                    "qtd_folhas": qtd_folhas,
                                    "material": "PERFIL EM ALUMINIO"
                                })
                            else:  # Terceirizada
                                empresa = st.text_input("Empresa Responsável:", key="op_empresa")
                                mat_terc = st.text_input("Material:", key="op_mat_terc")
                                campos_extras.update({"empresa": empresa, "material": mat_terc})

                            if st.button("🖨️ Gerar OP", key="btn_gerar_op", type="primary"):
                                op_bytes = gerar_op_xlsx(row_lote, df_pecas_existentes, macro_row_sel, campos_extras)
                                st.download_button(
                                    label="📥 Baixar Ordem de Produção",
                                    data=op_bytes,
                                    file_name=f"OP_{num_op_sel}_{row_lote['Cod_Lote']}.xlsx",
                                    mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                                    key="dl_op"
                                )

                    # Lançar/Substituir peças
                    with st.expander(
                        "✏️ Editar / Substituir Peças" if not df_pecas_existentes.empty else "➕ Lançar Peças",
                        expanded=df_pecas_existentes.empty
                    ):
                        st.caption("Cole os dados abaixo — um item por linha em cada campo.")

                        # m² REAL
                        gm1, gm2 = st.columns([2, 3])
                        with gm1:
                            m2_op_real = st.number_input(
                                "📐 m² real desta OP:",
                                min_value=0.0,
                                value=float(row_lote.get('M2_Item', 0)),
                                step=0.1,
                                format="%.2f",
                                key="m2_op_real_input",
                                help="Será abatido do saldo da etapa."
                            )
                        with gm2:
                            if not df_banco_macro.empty and edt_lote:
                                fr2 = df_banco_macro[df_banco_macro['EDT'] == edt_lote]
                                if not fr2.empty:
                                    m2_exec2  = float(fr2.iloc[0].get('m2_executado', 0) or 0)
                                    m2_total2 = float(fr2.iloc[0].get('M2_Total_Tarefa', 0) or 0)
                                    saldo_apos = m2_total2 - m2_exec2 - m2_op_real
                                    st.metric("Saldo após este lançamento", f"{saldo_apos:.2f} m²")

                        p1, p2, p3, p4 = st.columns(4)
                        with p1:
                            codigos_txt = st.text_area("Códigos:", height=180, key="pecas_codigos",
                                                        placeholder="B24-01C\nB25-01C\nRF.JA.11/CNT")
                        with p2:
                            qtds_txt = st.text_area("Quantidades:", height=180, key="pecas_qtds",
                                                     placeholder="3\n3\n1")
                        with p3:
                            locs_txt = st.text_area("Localização:", height=180, key="pecas_locs",
                                                     placeholder="Pav 27-37\nPav 27-37\n(opcional)")
                        with p4:
                            medidas_txt = st.text_area("Medidas:", height=180, key="pecas_medidas",
                                                        placeholder="550x390\n550x400\n(opcional)")

                        comp_status = st.radio(
                            "Status dos componentes:",
                            ["Aguardando Projetista", "Componentes OK"],
                            horizontal=True,
                            key="comp_status_radio"
                        )

                        if st.button("💾 Salvar Peças", key="btn_salvar_pecas", type="primary"):
                            codigos = [l.strip() for l in codigos_txt.strip().split('\n') if l.strip()]
                            qtds    = [l.strip() for l in qtds_txt.strip().split('\n') if l.strip()]
                            locs    = [l.strip() for l in locs_txt.strip().split('\n')] if locs_txt.strip() else []
                            medidas = [l.strip() for l in medidas_txt.strip().split('\n')] if medidas_txt.strip() else []

                            if not codigos:
                                st.error("Informe pelo menos um código.")
                            else:
                                pecas_list = []
                                for i, cod in enumerate(codigos):
                                    pecas_list.append({
                                        "codigo":      cod,
                                        "qtd":         int(qtds[i]) if i < len(qtds) and qtds[i].isdigit() else 1,
                                        "localizacao": locs[i] if i < len(locs) else "",
                                        "medida":      medidas[i] if i < len(medidas) else "",
                                    })
                                salvar_pecas_lote(
                                    lote_id, row_lote['Obra_Vinculada'],
                                    row_lote['Cod_Lote'], row_lote['Num_OP'],
                                    pecas_list, comp_status, m2_op_real
                                )
                                st.toast(f"{len(pecas_list)} peça(s) salvas!")
                                time.sleep(0.3)
                                st.rerun()
                else:
                    st.info("Nenhuma OP com número gerado ainda. Libere os lotes primeiro.")
            else:
                st.info("Nenhuma OP liberada para esta obra ainda.")

            st.markdown("---")

            # ── SEÇÃO 3: COMPONENTES POR OP ───────────────────────
            st.markdown("### 📦 Seção 3 — Componentes por OP")
            st.caption("Cadastre os componentes necessários para cada OP liberada.")

            df_lib_ops = df_banco_micro[
                (df_banco_micro['Obra_Vinculada'] == obra_selecionada) &
                (df_banco_micro['Status_Item'] == "Liberado para Fabrica")
            ].copy() if obra_selecionada and not df_banco_micro.empty else pd.DataFrame()

            if not df_lib_ops.empty:
                opcoes_ops = [
                    f"{row['Num_OP']} — {row['Cod_Lote']} | {row['Tipo_Material']}"
                    for _, row in df_lib_ops.iterrows() if row.get('Num_OP')
                ]
                if opcoes_ops:
                    op_sel  = st.selectbox("OP:", opcoes_ops, key="sel_op_comp")
                    row_op  = df_lib_ops[df_lib_ops['Num_OP'] == op_sel.split(" — ")[0].strip()].iloc[0]

                    # Verificar status dos componentes via op_pecas
                    df_pecas_op = carregar_pecas_lote(int(row_op['id']))
                    comp_st = df_pecas_op.iloc[0]['componentes_status'] if not df_pecas_op.empty else "Aguardando Projetista"

                    if comp_st == "Aguardando Projetista":
                        st.warning("🟠 Componentes: **Aguardando Projetista** — cadastre as peças na Seção 2 primeiro e marque como 'Componentes OK'.")
                    else:
                        comp_existentes = carregar_componentes_op(int(row_op['id']))
                        if not comp_existentes.empty:
                            st.success(f"✅ {len(comp_existentes)} componente(s) já cadastrado(s) para esta OP.")

                        with st.expander(
                            "➕ Adicionar / Substituir lista de componentes",
                            expanded=comp_existentes.empty
                        ):
                            st.caption("⚠️ Salvar substitui a lista anterior desta OP.")
                            num_itens = st.number_input("Quantos componentes?", min_value=1, max_value=30, value=3, key="num_comp")
                            componentes_input = []
                            for idx in range(int(num_itens)):
                                c1, c2, c3 = st.columns([4, 2, 2])
                                with c1:
                                    nome = st.text_input(f"Componente {idx+1}:", key=f"comp_nome_{idx}")
                                with c2:
                                    qtd  = st.number_input(f"Qtd {idx+1}:", min_value=0.0, value=1.0, key=f"comp_qtd_{idx}")
                                with c3:
                                    und  = st.selectbox(f"Un {idx+1}:", ["un", "kg", "m", "m²", "cx", "pç", "rolo"], key=f"comp_und_{idx}")
                                if nome.strip():
                                    componentes_input.append({"nome": nome.strip(), "qtd": qtd, "unidade": und})
                            if st.button("💾 Salvar lista de componentes", key="btn_salvar_comp"):
                                if not componentes_input:
                                    st.error("Preencha pelo menos um componente.")
                                else:
                                    salvar_componentes(int(row_op['id']), row_op['Obra_Vinculada'], row_op['Cod_Lote'], row_op['Num_OP'], componentes_input)
                                    st.toast(f"Lista salva para {row_op['Num_OP']}!")
                                    time.sleep(0.3)
                                    st.rerun()
                else:
                    st.info("Nenhuma OP com número gerado ainda.")
            else:
                st.info("Nenhuma OP liberada para esta obra ainda.")

    # ==================================================
    # VISAO MACRO
    # ==================================================
    elif nome_aba == "Visao Macro":
        with aba_objeto:
            st.header("Dashboard Executivo")
            if obra_selecionada and not df_banco_micro.empty:
                df_dir = df_banco_micro[df_banco_micro['Obra_Vinculada'] == obra_selecionada].copy()
            else:
                df_dir = df_banco_micro.copy()

            if not df_dir.empty:
                data_max = df_dir['Data_Limite_Obra'].max()
                c1, c2, c3 = st.columns(3)
                c1.metric("Metragem Total", f"{df_dir['M2_Item'].sum():,.2f} m²")
                c2.metric("Subdivisoes", f"{df_dir['EDT_Vinculado'].nunique()} frentes")
                c3.metric("Prazo Mais Distante", data_max.strftime('%d/%m/%Y') if prazo_valido(data_max) else "N/A")

                st.markdown("---")
                st.subheader("Carga Semanal")
                obras_macro = ["Todas as obras"] + (
                    sorted(df_banco_micro['Obra_Vinculada'].dropna().unique().tolist())
                    if not df_banco_micro.empty else []
                )

                st.markdown("#### 📋 Previsão")
                col_f1, _ = st.columns([2, 3])
                with col_f1:
                    filtro_prev = st.selectbox("🔍 Obra:", obras_macro, key="filtro_prev")
                df_prev = df_banco_micro.copy() if not df_banco_micro.empty else pd.DataFrame()
                if not df_prev.empty:
                    if filtro_prev != "Todas as obras":
                        df_prev = df_prev[df_prev['Obra_Vinculada'] == filtro_prev]
                    df_prev = df_prev[df_prev['Status_Item'] == 'Pendente']
                blocos_semanais(df_prev)

                st.markdown("---")
                st.markdown("#### 🔧 Em Produção")
                col_f2, _ = st.columns([2, 3])
                with col_f2:
                    filtro_prod = st.selectbox("🔍 Obra:", obras_macro, key="filtro_prod")
                df_prod = df_banco_micro.copy() if not df_banco_micro.empty else pd.DataFrame()
                if not df_prod.empty:
                    if filtro_prod != "Todas as obras":
                        df_prod = df_prod[df_prod['Obra_Vinculada'] == filtro_prod]
                    df_prod = df_prod[df_prod['Status_Item'] == 'Liberado para Fabrica']
                blocos_semanais(df_prod)

                st.markdown("---")
                st.markdown("#### ✅ Concluídos")
                col_f3, _ = st.columns([2, 3])
                with col_f3:
                    filtro_conc = st.selectbox("🔍 Obra:", obras_macro, key="filtro_conc")
                df_conc = df_banco_micro.copy() if not df_banco_micro.empty else pd.DataFrame()
                if not df_conc.empty:
                    if filtro_conc != "Todas as obras":
                        df_conc = df_conc[df_conc['Obra_Vinculada'] == filtro_conc]
                    df_conc = df_conc[df_conc['Status_Item'] == 'Concluido']
                blocos_semanais(df_conc)

                st.markdown("---")
                st.subheader("Gantt — Ocupacao da Fabrica")
                df_gantt = df_dir.groupby(['Obra_Vinculada', 'EDT_Vinculado', 'Romaneio_Chapas']).agg(
                    Inicio=('Data_Producao_Programada', 'min'),
                    Fim=('Data_Limite_Obra', 'max'),
                    M2=('M2_Item', 'sum')
                ).reset_index().dropna(subset=['Inicio', 'Fim'])
                if not df_gantt.empty:
                    fig = px.timeline(
                        df_gantt, x_start="Inicio", x_end="Fim", y="EDT_Vinculado",
                        color="Obra_Vinculada", hover_data=["Romaneio_Chapas", "M2"],
                        title="Ocupacao Fabrica vs Prazo Despacho",
                        color_discrete_sequence=["#1E3A8A", "#EA580C", "#0891B2", "#15803D"]
                    )
                    fig.update_yaxes(autorange="reversed")
                    fig.update_layout(height=400, margin=dict(l=20, r=20, t=40, b=20))
                    st.plotly_chart(fig, use_container_width=True)
            else:
                st.info("Nenhum dado encontrado.")

    # ==================================================
    # VINCULAR DATAS
    # ==================================================
    elif nome_aba == "Vincular Datas":
        with aba_objeto:
            st.header("Fatiamento de Lotes")
            if st.session_state.get('lote_salvo_sucesso'):
                st.success("Lote gerado com sucesso!")
                st.session_state.lote_salvo_sucesso = False

            if obra_selecionada and not df_macro_filtrado.empty:
                opcoes_edt = []
                mapa_rows  = {}
                for _, row in df_macro_filtrado.iterrows():
                    sub   = f" [{row['Subdivisao']}]" if row.get('Subdivisao') else ""
                    label = f"{row['EDT']} - {row['Tarefa']}{sub}"
                    opcoes_edt.append(label)
                    mapa_rows[label] = row

                st.markdown("### Nova Entrega")
                with st.form("form_fatiamento"):
                    c1, c2 = st.columns(2)
                    with c1:
                        edt_sel  = st.selectbox("Frente (EDT):", opcoes_edt)
                        row_sel  = mapa_rows[edt_sel]
                        edt_puro = edt_sel.split(" - ")[0].strip()
                        cod_lote = st.text_input("Nome do Lote (ex: LOTE 1, LOTE 2):")
                        txt_pav  = st.text_area("Pavimentos / Destino:", value="Pav 39 ao 43")
                        espec    = st.text_input("Material:", value="ACM BRANCO")
                        dific    = st.selectbox("Complexidade:", [1, 2, 3, 4, 5], index=2)
                    with c2:
                        inicio_prev = row_sel['Inicio_Previsto']
                        default_dt  = (
                            pd.to_datetime(inicio_prev).date() if prazo_valido(inicio_prev)
                            else (datetime.now() + timedelta(days=30)).date()
                        )
                        data_alvo = st.date_input("Precisa estar na obra ate:", value=default_dt, format="DD/MM/YYYY")
                        dias_log  = st.number_input("Dias de transporte (corridos):", min_value=1, value=3)
                        dias_fab  = st.number_input("Dias uteis de producao:", min_value=1, value=10)
                        total_cx  = st.number_input("Quantidade de caixas:", min_value=1, value=31)
                        total_m2  = st.number_input("Metragem (m²):", min_value=0.1, value=70.0)
                        dt_alvo   = datetime.combine(data_alvo, datetime.min.time())
                        dt_desp   = dt_alvo - timedelta(days=int(dias_log))
                        dt_inicio = subtrair_dias_uteis(dt_desp, int(dias_fab))
                        st.success(
                            f"Cronograma calculado:\n\n"
                            f"Inicio producao: **{dt_inicio.strftime('%d/%m/%Y')}**\n\n"
                            f"Saida da fabrica: **{dt_desp.strftime('%d/%m/%Y')}**\n\n"
                            f"Chegada na obra: **{data_alvo.strftime('%d/%m/%Y')}**"
                        )
                    if "Liberados" not in str(row_sel.get('Status_Engenharia', '')):
                        st.warning(f"Atencao — Engenharia: `{row_sel.get('Status_Engenharia', '—')}`")
                    if st.form_submit_button("Gerar Lote"):
                        if not cod_lote.strip():
                            st.error("Digite o nome do lote.")
                        else:
                            deletar_lotes_por_edt_lote(obra_selecionada, edt_puro, cod_lote.strip())
                            lote = gerar_lote_unico(
                                data_alvo, int(dias_log), int(dias_fab),
                                int(total_cx), float(total_m2),
                                obra_selecionada, edt_puro, cod_lote.strip(), espec, txt_pav, dific
                            )
                            salvar_lotes_micro(lote)
                            prazo_eng = subtrair_dias_uteis(dt_inicio, 3)
                            atualizar_cronograma_macro_datas(edt_puro, prazo_eng, dt_inicio, dt_desp)
                            st.session_state.lote_salvo_sucesso = True
                            st.rerun()

                st.markdown("---")
                st.markdown("### Lotes Gerados")
                df_ed_raw = carregar_micro_por_obra(obra_selecionada)
                if not df_ed_raw.empty:
                    df_obra = df_ed_raw.copy()
                    df_obra['Data_Producao_Programada'] = df_obra['Data_Producao_Programada'].dt.strftime('%Y-%m-%d')
                    df_obra['Data_Limite_Obra']         = df_obra['Data_Limite_Obra'].dt.strftime('%Y-%m-%d')
                    df_str  = df_obra.copy()
                    df_edit = st.data_editor(df_str, key="editor_lotes", hide_index=True, use_container_width=True,
                                             disabled=["id", "Obra_Vinculada", "Num_OP"])
                    alteradas = []
                    for i in df_edit.index:
                        try:
                            if not df_edit.loc[i].equals(df_str.loc[i]):
                                alteradas.append(df_edit.loc[i])
                        except Exception:
                            pass
                    if alteradas:
                        conn = conectar_banco()
                        try:
                            cursor = conn.cursor()
                            for row in alteradas:
                                cursor.execute("""
                                    UPDATE itens_detalhado
                                    SET Cod_Lote=%s, Tipo_Material=%s, Qtd_Caixas=%s, M2_Item=%s,
                                        Data_Producao_Programada=%s, Data_Limite_Obra=%s,
                                        Romaneio_Chapas=%s, Status_Item=%s, Dificuldade=%s, Fase_Produtiva=%s,
                                        updated_at=NOW()
                                    WHERE id=%s
                                """, (
                                    row['Cod_Lote'], row['Tipo_Material'], int(row['Qtd_Caixas']),
                                    float(row['M2_Item']), row['Data_Producao_Programada'],
                                    row['Data_Limite_Obra'], row['Romaneio_Chapas'],
                                    row['Status_Item'], int(row['Dificuldade']),
                                    row['Fase_Produtiva'], int(row['id'])
                                ))
                            conn.commit()
                            _limpar_cache_geral()
                        except Exception as e:
                            conn.rollback()
                            st.error(f"Erro ao salvar: {e}")
                        finally:
                            liberar_conexao(conn)
                        st.toast("Salvo!")
                        time.sleep(0.3)
                        st.rerun()

                    st.markdown("#### Remover Lote")
                    lote_del = st.selectbox("Lote para excluir:", df_obra['Cod_Lote'].unique().tolist())
                    if st.button(f"Excluir {lote_del}"):
                        deletar_lotes_por_edt_lote(obra_selecionada, None, lote_del)
                        st.toast(f"Lote {lote_del} removido!")
                        time.sleep(0.5)
                        st.rerun()
                else:
                    st.info("Nenhum lote fatiado ainda.")

    # ==================================================
    # CADASTRAR OBRA
    # ==================================================
    elif nome_aba == "Cadastrar Obra":
        with aba_objeto:
            st.header("Cadastrar Nova Obra")
            for k, v in [
                ('mem_obra', ''), ('mem_frente', ''), ('mem_tarefa', ''),
                ('mem_dt_ini', datetime.now().date()),
                ('mem_dt_fim', (datetime.now() + timedelta(days=90)).date())
            ]:
                if k not in st.session_state:
                    st.session_state[k] = v

            with st.form("form_obra"):
                nome_obra = st.text_input("Nome da Obra:", value=st.session_state.mem_obra).upper()
                co1, co2  = st.columns(2)
                with co1:
                    escopo      = st.selectbox("Escopo:", ["ACM", "Vidro/Esquadria", "Terceirizada"])
                    num_projeto = st.text_input("Número do Projeto:", placeholder="Ex: 1068")
                    frente      = st.text_input("Frente Macro:", value=st.session_state.mem_frente)
                    tarefa      = st.text_input("Nome da Tarefa:", value=st.session_state.mem_tarefa)
                with co2:
                    edt_cod = st.text_input("Codigo EDT (unico):")
                    subdiv  = st.text_input("Subdivisao / Balancim:").upper()
                    m2_tot  = st.number_input("Metragem (m²):", min_value=0.1, value=100.0)
                cd1, cd2 = st.columns(2)
                with cd1:
                    dt_ini = st.date_input("Inicio da Instalacao:", value=st.session_state.mem_dt_ini, format="DD/MM/YYYY")
                with cd2:
                    dt_fim = st.date_input("Prazo Maximo Obra:", value=st.session_state.mem_dt_fim, format="DD/MM/YYYY")
                if st.form_submit_button("Registrar Frente"):
                    if not all([nome_obra.strip(), edt_cod.strip(), tarefa.strip(), subdiv.strip()]):
                        st.error("Preencha todos os campos.")
                    else:
                        st.session_state.mem_obra   = nome_obra
                        st.session_state.mem_frente = frente
                        st.session_state.mem_tarefa = tarefa
                        st.session_state.mem_dt_ini = dt_ini
                        st.session_state.mem_dt_fim = dt_fim
                        conn = conectar_banco()
                        try:
                            cursor = conn.cursor()
                            cursor.execute("""
                                INSERT INTO cronograma_macro
                                (Obra, EDT, Tipo_Escopo, Etapa_Macro, Subdivisao, Tarefa,
                                 M2_Total_Tarefa, Inicio_Previsto, Termino_Obra, Status,
                                 Status_Engenharia, Numero_Projeto)
                                VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,'Pendente','Aguardando Medicao In Loco',%s)
                            """, (nome_obra, edt_cod, escopo, frente, subdiv, tarefa,
                                  float(m2_tot), dt_ini.strftime('%Y-%m-%d'),
                                  dt_fim.strftime('%Y-%m-%d'), num_projeto.strip()))
                            conn.commit()
                            _limpar_cache_geral()
                            st.toast("Frente registrada!")
                            time.sleep(0.4)
                            st.rerun()
                        except Exception as e:
                            conn.rollback()
                            st.error(f"EDT '{edt_cod}' ja existe ou erro: {e}")
                        finally:
                            liberar_conexao(conn)

            if not df_banco_macro.empty:
                st.markdown("---")
                st.markdown("### Frentes Cadastradas")
                df_show = df_banco_macro.copy()
                for col in ['Inicio_Previsto', 'Termino_Obra']:
                    if col in df_show.columns:
                        df_show[col] = pd.to_datetime(df_show[col], errors='coerce').dt.strftime('%d/%m/%Y')
                cols_s = [c for c in ['Obra', 'EDT', 'Subdivisao', 'Tarefa', 'M2_Total_Tarefa',
                                      'Inicio_Previsto', 'Termino_Obra', 'Status_Engenharia'] if c in df_show.columns]
                st.dataframe(df_show[cols_s], hide_index=True, use_container_width=True)

                st.markdown("#### Excluir Frente")
                st.warning("Isso remove a frente do cronograma macro.")
                opcoes_del = [
                    f"{row['EDT']} — {row['Tarefa']} [{row.get('Subdivisao','')}]"
                    for _, row in df_banco_macro[df_banco_macro['Obra'] == obra_selecionada].iterrows()
                ] if not df_banco_macro.empty else []
                if opcoes_del:
                    frente_del = st.selectbox("Frente para excluir:", opcoes_del, key="sel_del_frente")
                    edt_del    = frente_del.split(" — ")[0].strip()
                    if st.button(f"Excluir frente {edt_del}", key="btn_del_frente"):
                        conn = conectar_banco()
                        try:
                            cursor = conn.cursor()
                            cursor.execute("DELETE FROM cronograma_macro WHERE EDT=%s", (edt_del,))
                            conn.commit()
                            _limpar_cache_geral()
                            st.toast(f"Frente {edt_del} removida!")
                            time.sleep(0.5)
                            st.rerun()
                        except Exception as e:
                            conn.rollback()
                            st.error(f"Erro: {e}")
                        finally:
                            liberar_conexao(conn)

    # ==================================================
    # PAINEL DE ENGENHARIA
    # ==================================================
    elif nome_aba == "Painel de Engenharia":
        with aba_objeto:
            st.header("Painel Tecnico da Engenharia")
            st.caption(f"Hoje: {HOJE_PROJETO.strftime('%d/%m/%Y')} | Obra: **{obra_selecionada or 'Nenhuma'}**")
            df_eng = carregar_macro_por_obra(obra_selecionada) if obra_selecionada else pd.DataFrame()

            ESTADOS = [
                "Aguardando Medicao In Loco", "Medicao Realizada — Em Projetos",
                "Projetos em Revisao Interna", "Projetos Liberados para o PCP", "Arquivado / Concluido"
            ]
            STATUS_CORES = {
                "Aguardando Medicao In Loco":      "#EF4444",
                "Medicao Realizada — Em Projetos": "#EAB308",
                "Projetos em Revisao Interna":     "#3B82F6",
                "Projetos Liberados para o PCP":   "#22C55E",
                "Arquivado / Concluido":           "#94A3B8",
            }

            def classificar(dias_rest, status_tec):
                if status_tec == "Projetos Liberados para o PCP":
                    return "concluido", "Liberado para o PCP", None
                if dias_rest is None:
                    return "sem_prazo", "Aguardando programacao pelo PCP", None
                if dias_rest < 0:
                    return "vencido", f"VENCIDO ha {abs(int(dias_rest))} dias", abs(int(dias_rest))
                if dias_rest <= 7:
                    return "critico", f"Critico — faltam {int(dias_rest)} dias", int(dias_rest)
                return "ok", f"Dentro do prazo ({int(dias_rest)} dias)", int(dias_rest)

            frentes = []
            if not df_eng.empty:
                for _, row in df_eng.iterrows():
                    prazo_raw = row.get('Prazo_Engenharia')
                    prazo_eng = prazo_raw if prazo_valido(prazo_raw) else None
                    dias_rest = (pd.to_datetime(prazo_eng) - HOJE_PROJETO).days if prazo_eng is not None else None
                    sk, situacao_txt, dias_num = classificar(dias_rest, row.get('Status_Engenharia', ESTADOS[0]))
                    frentes.append({
                        "id": row['id'], "edt": row['EDT'], "tarefa": row['Tarefa'],
                        "subdivisao": row.get('Subdivisao', ''), "tipo_escopo": row.get('Tipo_Escopo', ''),
                        "inicio_previsto": row.get('Inicio_Previsto'), "despacho": row.get('Data_Limite_Despacho'),
                        "primeiro_prod": row.get('Primeiro_Dia_Producao'), "termino_obra": row.get('Termino_Obra'),
                        "m2": row.get('M2_Total_Tarefa', 0.0), "prazo_eng": prazo_eng,
                        "dias_restantes": dias_rest, "situacao_key": sk, "situacao_txt": situacao_txt,
                        "dias_num": dias_num, "status_tecnico": row.get('Status_Engenharia', ESTADOS[0]),
                    })

            criticas = [f for f in frentes if f['situacao_key'] in ('critico', 'vencido')]

            with st.expander(f"Frentes Criticas — {len(criticas)} alerta(s)", expanded=True):
                if not criticas:
                    st.success("Tudo dentro do prazo!")
                else:
                    for fr in sorted(criticas, key=lambda x: x['dias_restantes'] or 0):
                        with st.container(border=True):
                            ci, cc = st.columns([7, 3])
                            with ci:
                                sub = f" · {fr['subdivisao']}" if fr['subdivisao'] else ""
                                st.markdown(f"### {fr['tarefa']}{sub}")
                                cm1, cm2 = st.columns(2)
                                with cm1:
                                    st.write(f"EDT: `{fr['edt']}`")
                                    ini = pd.to_datetime(fr['inicio_previsto']).strftime('%d/%m/%Y') if prazo_valido(fr['inicio_previsto']) else "—"
                                    st.write(f"Inicio instalacao: {ini}")
                                    pp = pd.to_datetime(fr['primeiro_prod']).strftime('%d/%m/%Y') if prazo_valido(fr['primeiro_prod']) else "—"
                                    st.write(f"1º dia producao: {pp}")
                                with cm2:
                                    pe = pd.to_datetime(fr['prazo_eng']).strftime('%d/%m/%Y') if fr['prazo_eng'] else "—"
                                    st.write(f"Prazo engenharia: `{pe}`")
                                    dp = pd.to_datetime(fr['despacho']).strftime('%d/%m/%Y') if prazo_valido(fr['despacho']) else "—"
                                    st.write(f"Despacho: {dp}")
                                cor_status = STATUS_CORES.get(fr['status_tecnico'], "#94A3B8")
                                st.markdown(f"<span style='background:{cor_status}20;color:{cor_status};padding:3px 8px;border-radius:4px;font-size:12px;font-weight:600;'>{fr['status_tecnico']}</span>", unsafe_allow_html=True)
                            with cc:
                                if fr['situacao_key'] == 'vencido':
                                    st.error(f"VENCIDO\n\n**{fr['dias_num']} dias**")
                                else:
                                    st.warning(f"FALTAM\n\n**{fr['dias_num']} dias**")
                            st.markdown("---")
                            ca1, ca2 = st.columns(2)
                            with ca1:
                                idx = ESTADOS.index(fr['status_tecnico']) if fr['status_tecnico'] in ESTADOS else 0
                                ns  = st.selectbox("Atualizar status:", ESTADOS, index=idx, key=f"cs_{fr['id']}")
                            with ca2:
                                st.write("")
                                st.write("")
                                if st.button("Salvar", key=f"cb_{fr['id']}", use_container_width=True):
                                    atualizar_status_engenharia(fr['id'], ns)
                                    st.toast("Atualizado!")
                                    time.sleep(0.3)
                                    st.rerun()

            with st.expander(f"Todas as Frentes — {len(frentes)}", expanded=False):
                if not frentes:
                    st.info("Nenhuma frente cadastrada.")
                else:
                    cf1, cf2 = st.columns([3, 2])
                    with cf1:
                        filt_st  = st.selectbox("Status:", ["Todos"] + ESTADOS, key="eng_fst")
                    with cf2:
                        filt_sit = st.radio("Situacao:", ["Todas", "Criticas", "Liberadas"], horizontal=True, key="eng_fsi")
                    exibir = frentes.copy()
                    if filt_st != "Todos":
                        exibir = [f for f in exibir if f['status_tecnico'] == filt_st]
                    if filt_sit == "Criticas":
                        exibir = [f for f in exibir if f['situacao_key'] in ('critico', 'vencido')]
                    elif filt_sit == "Liberadas":
                        exibir = [f for f in exibir if f['situacao_key'] == 'concluido']
                    st.markdown(f"**{len(exibir)} frente(s)**")
                    st.markdown("---")
                    for fr in exibir:
                        with st.container(border=True):
                            ci, cd, ca = st.columns([5, 3, 2])
                            with ci:
                                sub = f" · *{fr['subdivisao']}*" if fr['subdivisao'] else ""
                                st.markdown(f"**{fr['tarefa']}**{sub}")
                                st.caption(f"EDT: {fr['edt']} | {fr['tipo_escopo']} | {fr['m2']:,.2f} m²")
                                cor_status = STATUS_CORES.get(fr['status_tecnico'], "#94A3B8")
                                st.markdown(f"<span style='background:{cor_status}20;color:{cor_status};padding:2px 8px;border-radius:4px;font-size:12px;font-weight:600;'>{fr['status_tecnico']}</span>", unsafe_allow_html=True)
                            with cd:
                                ini = pd.to_datetime(fr['inicio_previsto']).strftime('%d/%m/%Y') if prazo_valido(fr['inicio_previsto']) else "—"
                                st.caption("Inicio instalacao")
                                st.write(ini)
                                pe = pd.to_datetime(fr['prazo_eng']).strftime('%d/%m/%Y') if fr['prazo_eng'] else "—"
                                st.caption("Prazo PCP")
                                st.write(f"`{pe}`")
                                dp = pd.to_datetime(fr['despacho']).strftime('%d/%m/%Y') if prazo_valido(fr['despacho']) else "—"
                                st.caption("Despacho")
                                st.write(dp)
                            with ca:
                                sk = fr['situacao_key']
                                if sk == 'vencido':      st.error(fr['situacao_txt'])
                                elif sk == 'critico':    st.warning(fr['situacao_txt'])
                                elif sk in ('concluido', 'ok'): st.success(fr['situacao_txt'])
                                else:                    st.info(fr['situacao_txt'])
                            cs, cb = st.columns([4, 1])
                            with cs:
                                idx = ESTADOS.index(fr['status_tecnico']) if fr['status_tecnico'] in ESTADOS else 0
                                ns  = st.selectbox("", ESTADOS, index=idx, key=f"as_{fr['id']}", label_visibility="collapsed")
                            with cb:
                                if st.button("Salvar", key=f"ab_{fr['id']}", use_container_width=True):
                                    atualizar_status_engenharia(fr['id'], ns)
                                    st.toast("Atualizado!")
                                    time.sleep(0.3)
                                    st.rerun()

            df_sols = carregar_solicitacoes()
            n_pend  = len(df_sols[df_sols['status'] == 'Pendente de Aprovacao']) if not df_sols.empty else 0
            with st.expander(f"Solicitacoes de Prazo{f' — {n_pend} pendente(s)' if n_pend else ''}", expanded=False):
                nao_lib = [f for f in frentes if f['situacao_key'] != 'concluido']
                if setor in ["Engenharia", "Master"] and nao_lib:
                    st.markdown("#### Nova Solicitacao")
                    cs1, cs2 = st.columns(2)
                    with cs1:
                        opts = [f"{f['edt']} — {f['tarefa']}" for f in nao_lib]
                        sel  = st.selectbox("Frente:", opts, key="sol_fr")
                        fobj = nao_lib[opts.index(sel)]
                        pat  = pd.to_datetime(fobj['prazo_eng']).strftime('%d/%m/%Y') if fobj['prazo_eng'] else "Nao definido"
                        st.info(f"Prazo atual: **{pat}**")
                    with cs2:
                        nps = st.date_input("Novo prazo:", format="DD/MM/YYYY", key="sol_np",
                                            value=((pd.to_datetime(fobj['prazo_eng']) + timedelta(days=7)).date() if fobj['prazo_eng'] else HOJE_PROJETO.date()))
                        jus = st.text_area("Justificativa:", key="sol_jus")
                    if st.button("Enviar solicitacao", key="sol_env"):
                        if not jus.strip():
                            st.error("Informe a justificativa.")
                        else:
                            salvar_solicitacao(fobj['edt'], fobj['tarefa'], pat, nps.strftime('%d/%m/%Y'), jus.strip(), st.session_state.usuario_nome)
                            st.success("Enviado!")
                            st.rerun()
                st.markdown("---")
                if setor == "Master" and not df_sols.empty:
                    pend = df_sols[df_sols['status'] == 'Pendente de Aprovacao']
                    if pend.empty:
                        st.info("Nenhuma pendente.")
                    else:
                        for _, sol in pend.iterrows():
                            with st.container(border=True):
                                sa, sb = st.columns([4, 2])
                                with sa:
                                    st.markdown(f"**{sol['tarefa']}** — `{sol['edt']}`")
                                    st.write(f"`{sol['prazo_atual']}` → `{sol['prazo_solicitado']}`")
                                    st.caption(f"*{sol['justificativa']}* | {sol['criado_por']} em {sol['criado_em']}")
                                with sb:
                                    cap, cre = st.columns(2)
                                    with cap:
                                        if st.button("Aprovar", key=f"ap_{sol['id']}", use_container_width=True):
                                            atualizar_status_solicitacao(sol['id'], "Aprovado")
                                            st.rerun()
                                    with cre:
                                        if st.button("Rejeitar", key=f"rj_{sol['id']}", use_container_width=True):
                                            atualizar_status_solicitacao(sol['id'], "Rejeitado")
                                            st.rerun()
                if not df_sols.empty:
                    hist = df_sols[df_sols['status'] != 'Pendente de Aprovacao']
                    if not hist.empty:
                        st.markdown("#### Historico")
                        for _, sol in hist.iterrows():
                            st.caption(f"{sol['status']} | **{sol['tarefa']}** | {sol['prazo_solicitado']} | {sol['criado_por']}")

            with st.expander("Carga da Fabrica por Semana", expanded=False):
                df_fab = (df_banco_micro[df_banco_micro['Status_Item'] == "Liberado para Fabrica"].copy()
                          if not df_banco_micro.empty else pd.DataFrame())
                if not df_fab.empty:
                    df_fab['Ano_Semana'] = df_fab['Data_Producao_Programada'].dt.isocalendar().year
                    df_fab['Num_Semana'] = df_fab['Data_Producao_Programada'].dt.isocalendar().week
                    def fmt_s(r):
                        try:
                            s = pd.to_datetime(f"{int(r['Ano_Semana'])}-W{int(r['Num_Semana'])}-1", format="%G-W%V-%u")
                            return f"Semana {int(r['Num_Semana']):02d} ({s.strftime('%d/%m')} – {(s + timedelta(days=6)).strftime('%d/%m')})"
                        except Exception:
                            return f"Semana {r['Num_Semana']}"
                    df_fab['Periodo'] = df_fab.apply(fmt_s, axis=1)
                    res_fab = df_fab.groupby(['Ano_Semana', 'Num_Semana', 'Periodo', 'Obra_Vinculada']).agg(
                        Caixas=('Qtd_Caixas', 'sum'), M2=('M2_Item', 'sum')
                    ).reset_index().sort_values(['Ano_Semana', 'Num_Semana'])
                    res_fab.columns = ['Ano', 'Sem', 'Periodo', 'Obra', 'Caixas (cx)', 'Metragem (m²)']
                    st.dataframe(res_fab[['Periodo', 'Obra', 'Caixas (cx)', 'Metragem (m²)']], hide_index=True, use_container_width=True)
                else:
                    st.success("Fabrica livre!")

    # ==================================================
    # LOGISTICA
    # ==================================================
    elif nome_aba == "Logistica":
        with aba_objeto:
            st.header("Logistica — Gestao de Despachos")
            st.caption(f"Hoje: {HOJE_PROJETO.strftime('%d/%m/%Y')}")
            df_log = carregar_fila_logistica()

            if not df_log.empty:
                n_aguard   = len(df_log[df_log['Status_Logistica'] == 'Aguardando Agendamento'])
                n_agendado = len(df_log[df_log['Status_Logistica'] == 'Envio Agendado'])
                n_despach  = len(df_log[df_log['Status_Logistica'] == 'Despachado'])
                df_ativos  = df_log[df_log['Status_Logistica'] != 'Despachado']
                n_atrasado = (
                    len(df_ativos[df_ativos['Data_Limite_Despacho'].apply(
                        lambda x: prazo_valido(x) and pd.to_datetime(x) < HOJE_PROJETO
                    )]) if not df_ativos.empty else 0
                )
                c1, c2, c3, c4 = st.columns(4)
                c1.metric("Aguardando Agendamento", n_aguard)
                c2.metric("Envios Agendados",       n_agendado)
                c3.metric("Despachados",             n_despach)
                if n_atrasado > 0:
                    c4.metric("Atrasados", n_atrasado, delta=f"-{n_atrasado}", delta_color="inverse")
                else:
                    c4.metric("Atrasos", "Nenhum")
            else:
                st.info("Nenhum lote na fila ainda.")

            st.markdown("---")

            with st.expander("Fila Prioritaria — Aguardando Agendamento", expanded=True):
                if df_log.empty or df_log[df_log['Status_Logistica'] == 'Aguardando Agendamento'].empty:
                    st.success("Todos os lotes ja agendados!")
                else:
                    df_ag = df_log[df_log['Status_Logistica'] == 'Aguardando Agendamento'].copy().sort_values('Data_Limite_Despacho', na_position='last')
                    for _, row in df_ag.iterrows():
                        prazo_d = row['Data_Limite_Despacho']
                        if prazo_valido(prazo_d):
                            dias_r = (pd.to_datetime(prazo_d) - HOJE_PROJETO).days
                            if dias_r < 0:    css_bar = "bar-danger"; tag = f"ATRASADO {abs(dias_r)}d"
                            elif dias_r <= 3: css_bar = "bar-warn";   tag = f"URGENTE — {dias_r}d restantes"
                            else:             css_bar = "bar-ok";     tag = f"{dias_r} dias restantes"
                        else:
                            css_bar = "bar-neutral"; tag = "Sem prazo definido"

                        st.markdown(f"<div class='{css_bar}'>", unsafe_allow_html=True)
                        ci, cp, ca = st.columns([5, 3, 2])
                        with ci:
                            st.markdown(f'<span class="badge-obra">{row["Obra_Vinculada"]}</span>&nbsp;<span class="badge-lote">Lote: {row["Cod_Lote"]}</span>', unsafe_allow_html=True)
                            st.markdown(f"**{row['Tipo_Material']}** | `{int(row['Qtd_Caixas'])} cx` — {row['M2_Item']:.2f} m²")
                            st.caption(f"Pavimentos: {row['Romaneio_Chapas']} | OP: {row.get('Num_OP') or 'S/OP'}")
                        with cp:
                            ptxt = pd.to_datetime(prazo_d).strftime('%d/%m/%Y') if prazo_valido(prazo_d) else "—"
                            st.caption("Prazo maximo despacho")
                            st.markdown(f"**{ptxt}**")
                            st.markdown(f"`{tag}`")
                        with ca:
                            if st.button("Agendar", key=f"ag_btn_{row['id']}", use_container_width=True):
                                st.session_state[f"ag_open_{row['id']}"] = True
                        st.markdown("</div>", unsafe_allow_html=True)

                        if st.session_state.get(f"ag_open_{row['id']}", False):
                            with st.container(border=True):
                                st.markdown(f"#### Agendar — Lote `{row['Cod_Lote']}` | {row['Obra_Vinculada']}")
                                fa1, fa2 = st.columns(2)
                                with fa1:
                                    dt_env = st.date_input("Data envio:", format="DD/MM/YYYY", key=f"dt_env_{row['id']}",
                                                           value=(pd.to_datetime(prazo_d).date() if prazo_valido(prazo_d) else HOJE_PROJETO.date()))
                                    transp = st.selectbox("Transporte:", ["Frota Propria (Passold)", "Transportadora Terceira", "Retirada pelo Cliente"], key=f"tr_{row['id']}")
                                with fa2:
                                    veic = st.text_input("Veiculo / Placa:", key=f"ve_{row['id']}")
                                    obs  = st.text_area("Observacoes:", key=f"ob_{row['id']}", height=80)
                                cb1, cb2 = st.columns(2)
                                with cb1:
                                    if st.button("Confirmar agendamento", key=f"conf_{row['id']}", use_container_width=True, type="primary"):
                                        agendar_envio(row['id'], dt_env, transp, veic, obs, st.session_state.usuario_nome)
                                        st.session_state[f"ag_open_{row['id']}"] = False
                                        st.toast(f"Agendado para {dt_env.strftime('%d/%m/%Y')}!")
                                        time.sleep(0.3)
                                        st.rerun()
                                with cb2:
                                    if st.button("Cancelar", key=f"can_{row['id']}", use_container_width=True):
                                        st.session_state[f"ag_open_{row['id']}"] = False
                                        st.rerun()

            with st.expander("Envios Agendados — Confirmar Saida", expanded=True):
                if df_log.empty or df_log[df_log['Status_Logistica'] == 'Envio Agendado'].empty:
                    st.info("Nenhum envio agendado.")
                else:
                    df_agend = df_log[df_log['Status_Logistica'] == 'Envio Agendado'].copy().sort_values('Data_Envio_Agendado', na_position='last')
                    for _, row in df_agend.iterrows():
                        pd_d = row['Data_Limite_Despacho']
                        de_d = row['Data_Envio_Agendado']
                        no_prazo = (pd.to_datetime(de_d) <= pd.to_datetime(pd_d)) if prazo_valido(pd_d) and prazo_valido(de_d) else True
                        css_bar  = "bar-ok" if no_prazo else "bar-danger"
                        st.markdown(f"<div class='{css_bar}'>", unsafe_allow_html=True)
                        ci2, cp2, ca2 = st.columns([5, 3, 2])
                        with ci2:
                            st.markdown(f'<span class="badge-obra">{row["Obra_Vinculada"]}</span>&nbsp;<span class="badge-lote">Lote: {row["Cod_Lote"]}</span>', unsafe_allow_html=True)
                            st.markdown(f"**{row['Tipo_Material']}** | `{int(row['Qtd_Caixas'])} cx` — {row['M2_Item']:.2f} m²")
                            st.caption(f"{row.get('Transportadora', '—')} | {row.get('Veiculo', '—')}")
                            if row.get('Observacoes'):
                                st.caption(f"Obs: {row['Observacoes']}")
                        with cp2:
                            et = pd.to_datetime(de_d).strftime('%d/%m/%Y') if prazo_valido(de_d) else "—"
                            pt = pd.to_datetime(pd_d).strftime('%d/%m/%Y') if prazo_valido(pd_d) else "—"
                            st.caption("Data envio agendada")
                            st.markdown(f"**{et}**")
                            st.caption("Prazo maximo")
                            st.write(pt)
                            if not no_prazo:
                                st.error("Fora do prazo!")
                        with ca2:
                            st.write("")
                            if st.button("Confirmar Despacho", key=f"des_{row['id']}", use_container_width=True, type="primary"):
                                confirmar_despacho(row['id'], st.session_state.usuario_nome)
                                st.toast("Despachado!")
                                time.sleep(0.3)
                                st.rerun()
                            if st.button("Reagendar", key=f"rag_{row['id']}", use_container_width=True):
                                conn = conectar_banco()
                                try:
                                    cursor = conn.cursor()
                                    cursor.execute("UPDATE logistica_envios SET Status_Logistica='Aguardando Agendamento' WHERE id=%s", (row['id'],))
                                    conn.commit()
                                    carregar_fila_logistica.clear()
                                except Exception as e:
                                    conn.rollback()
                                    st.error(f"Erro: {e}")
                                finally:
                                    liberar_conexao(conn)
                                st.rerun()
                        st.markdown("</div>", unsafe_allow_html=True)

            with st.expander("Historico de Despachos", expanded=False):
                if df_log.empty or df_log[df_log['Status_Logistica'] == 'Despachado'].empty:
                    st.info("Nenhum despacho realizado ainda.")
                else:
                    df_hist = df_log[df_log['Status_Logistica'] == 'Despachado'].copy()
                    for col in ['Data_Limite_Despacho', 'Data_Envio_Agendado']:
                        df_hist[col] = df_hist[col].apply(lambda x: pd.to_datetime(x).strftime('%d/%m/%Y') if prazo_valido(x) else "—")
                    cols_h = [c for c in ['Obra_Vinculada', 'Cod_Lote', 'Tipo_Material', 'Qtd_Caixas', 'M2_Item',
                                          'Transportadora', 'Veiculo', 'Data_Envio_Agendado', 'Data_Limite_Despacho',
                                          'Confirmado_Por', 'Confirmado_Em'] if c in df_hist.columns]
                    st.dataframe(df_hist[cols_h], hide_index=True, use_container_width=True)
                    df_pont = df_log[df_log['Status_Logistica'] == 'Despachado'].copy()
                    df_pont = df_pont[df_pont['Data_Limite_Despacho'].apply(prazo_valido) & df_pont['Data_Envio_Agendado'].apply(prazo_valido)]
                    if not df_pont.empty:
                        ok = (pd.to_datetime(df_pont['Data_Envio_Agendado']) <= pd.to_datetime(df_pont['Data_Limite_Despacho'])).sum()
                        st.metric("Pontualidade nos despachos", f"{ok / len(df_pont) * 100:.0f}%")

    # ==================================================
    # ALMOXARIFADO
    # ==================================================
    elif nome_aba == "Almoxarifado":
        with aba_objeto:
            st.header("Almoxarifado — Conferência de Componentes")
            st.caption(f"Hoje: {HOJE_PROJETO.strftime('%d/%m/%Y')} | Usuário: {st.session_state.usuario_nome}")
            df_ops_comp = carregar_todas_ops_com_componentes()

            if df_ops_comp.empty:
                st.info("Nenhuma OP com lista de componentes cadastrada ainda.")
            else:
                conn_alm = conectar_banco()
                try:
                    todos_comps = pd.read_sql_query("SELECT * FROM componentes_op ORDER BY item_id, id", conn_alm)
                finally:
                    liberar_conexao(conn_alm)

                n_aguard  = len(todos_comps[todos_comps['status_item'] == 'Aguardando Conferencia'])
                n_ok      = len(todos_comps[todos_comps['status_item'] == 'Disponivel'])
                n_falta   = len(todos_comps[todos_comps['status_item'] == 'Indisponivel'])
                c1, c2, c3 = st.columns(3)
                c1.metric("⏳ Aguardando", n_aguard)
                c2.metric("✅ Disponíveis", n_ok)
                c3.metric("❌ Indisponíveis", n_falta)
                st.markdown("---")

                for _, op_row in df_ops_comp.iterrows():
                    df_comp = carregar_componentes_op(int(op_row['item_id']))
                    if df_comp.empty:
                        continue
                    n_total   = len(df_comp)
                    n_conf    = len(df_comp[df_comp['status_item'] != 'Aguardando Conferencia'])
                    n_indisp  = len(df_comp[df_comp['status_item'] == 'Indisponivel'])
                    if n_indisp > 0:   css_bar = "bar-danger"; icone = "❌"
                    elif n_conf == n_total: css_bar = "bar-ok"; icone = "✅"
                    else:              css_bar = "bar-warn";  icone = "⏳"

                    with st.expander(
                        f"{icone} OP: {op_row['num_op']} — {op_row['cod_lote']} | {op_row['obra_vinculada']}  "
                        f"({n_conf}/{n_total} conferidos{f' — {n_indisp} FALTANDO' if n_indisp > 0 else ''})",
                        expanded=(n_indisp > 0 or n_conf < n_total)
                    ):
                        hc = st.columns([4, 2, 2, 3, 2])
                        for col_h, label in zip(hc, ["COMPONENTE", "QTD", "UN", "STATUS", "AÇÃO"]):
                            col_h.markdown(f"<div style='font-size:11px;font-weight:700;color:#94A3B8;text-transform:uppercase;letter-spacing:0.07em;'>{label}</div>", unsafe_allow_html=True)
                        st.markdown("<hr style='margin:4px 0 8px 0;border-color:#E2E8F0;'>", unsafe_allow_html=True)

                        for _, comp in df_comp.iterrows():
                            st_item = comp['status_item']
                            if st_item == 'Disponivel':     cor = "#15803D"; bg = "#F0FDF4"; emoji = "✅"
                            elif st_item == 'Indisponivel': cor = "#DC2626"; bg = "#FEF2F2"; emoji = "❌"
                            else:                           cor = "#D97706"; bg = "#FFFBEB"; emoji = "⏳"
                            rc = st.columns([4, 2, 2, 3, 2])
                            rc[0].markdown(f"**{comp['nome_componente']}**")
                            rc[1].markdown(f"`{comp['quantidade']}`")
                            rc[2].markdown(f"{comp['unidade']}")
                            rc[3].markdown(f"<span style='background:{bg};color:{cor};padding:3px 8px;border-radius:4px;font-size:12px;font-weight:600;'>{emoji} {st_item}</span>", unsafe_allow_html=True)
                            with rc[4]:
                                acao = st.selectbox(
                                    "", ["Aguardando Conferencia", "Disponivel", "Indisponivel"],
                                    index=["Aguardando Conferencia", "Disponivel", "Indisponivel"].index(st_item),
                                    key=f"alm_st_{comp['id']}", label_visibility="collapsed"
                                )
                                if acao != st_item:
                                    atualizar_componente(comp['id'], acao, comp.get('observacao') or '', st.session_state.usuario_nome)
                                    st.rerun()
                            obs_atual = comp.get('observacao') or ''
                            obs_nova  = st.text_input(f"Obs — {comp['nome_componente']}:", value=obs_atual,
                                                      key=f"alm_obs_{comp['id']}", placeholder="Ex: em falta, previsão 20/06...")
                            if obs_nova != obs_atual:
                                atualizar_componente(comp['id'], st_item, obs_nova, st.session_state.usuario_nome)
                            st.markdown("<hr style='margin:4px 0;border-color:#F1F5F9;'>", unsafe_allow_html=True)

                        if n_indisp > 0:
                            itens_falt = df_comp[df_comp['status_item'] == 'Indisponivel']['nome_componente'].tolist()
                            st.error(f"⚠️ Itens em falta: {', '.join(itens_falt)}")
                        elif n_conf == n_total:
                            st.success("✅ Todos os componentes conferidos e disponíveis!")

    # ==================================================
    # SISTEMA DE MEDICAO — agora 100% no banco
    # ==================================================
    elif nome_aba == "Sistema de Medicao":
        with aba_objeto:
            st.header("Sistema de Medição — Gestão de Saldos & Escopos")
            st.caption(f"Usuário: {st.session_state.usuario_nome}")

            import json as _json

            tab_cad, tab_srv, tab_med, tab_dash = st.tabs([
                "1. Cadastrar Obra Base",
                "2. Serviços & Etapas",
                "3. Relatório de Saldos",
                "4. Dashboards"
            ])

            # ── ABA 1: CADASTRAR OBRA ─────────────────────────────
            with tab_cad:
                with st.form("form_med_obra"):
                    st.markdown("#### Nova Obra / Contrato")
                    mc1, mc2, mc3 = st.columns(3)
                    with mc1:
                        med_nome = st.text_input("Nome da Obra / Contrato")
                    with mc2:
                        med_valm2 = st.number_input("Valor m² Teto (R$/m²)", min_value=0.01, value=500.0)
                    with mc3:
                        med_metro = st.number_input("Metragem Geral (m²)", min_value=0.01, value=1500.0)
                    if st.form_submit_button("Salvar Obra"):
                        if not med_nome.strip():
                            st.error("Informe o nome da obra.")
                        else:
                            with st.spinner("Salvando..."):
                                new_id = salvar_medicao_obra(med_nome.strip(), med_valm2, med_metro)
                            if new_id:
                                st.success(f"Obra '{med_nome}' cadastrada!")
                                st.rerun()

                st.markdown("---")
                st.markdown("#### Obras Cadastradas")
                df_med_obras = carregar_medicao_obras()
                if df_med_obras.empty:
                    st.info("Nenhuma obra cadastrada ainda.")
                else:
                    cols_obra = st.columns(min(len(df_med_obras), 3))
                    for i, (_, obra_row) in enumerate(df_med_obras.iterrows()):
                        total = obra_row['valor_m2_global'] * obra_row['metragem_geral']
                        with cols_obra[i % 3]:
                            with st.container(border=True):
                                st.markdown(f"**{obra_row['nome']}**")
                                st.caption(f"Metragem: {obra_row['metragem_geral']:.2f} m²")
                                st.caption(f"Valor limite m²: R$ {obra_row['valor_m2_global']:.2f}")
                                st.metric("Total Contratado", f"R$ {total:,.2f}")
                                if st.button("Excluir", key=f"del_med_obra_{obra_row['id']}", type="primary"):
                                    excluir_medicao_obra(int(obra_row['id']))
                                    st.toast("Obra removida!")
                                    time.sleep(0.3)
                                    st.rerun()

            # ── ABA 2: SERVIÇOS & ETAPAS ──────────────────────────
            with tab_srv:
                df_med_obras2 = carregar_medicao_obras()
                if df_med_obras2.empty:
                    st.info("Cadastre uma obra primeiro.")
                else:
                    opcoes_med = {row['nome']: row['id'] for _, row in df_med_obras2.iterrows()}
                    obra_med_sel = st.selectbox("Obra:", list(opcoes_med.keys()), key="sel_obra_srv")
                    obra_med_id  = opcoes_med[obra_med_sel]
                    periodo_ref  = st.text_input("Período de referência (MM/AAAA):",
                                                  value=datetime.now().strftime('%m/%Y'),
                                                  placeholder="Ex: 06/2025")

                    obra_med_info = df_med_obras2[df_med_obras2['id'] == obra_med_id].iloc[0]
                    st.info(f"Teto da obra: **R$ {obra_med_info['valor_m2_global']:.2f}/m²**")

                    df_srvs = carregar_medicao_servicos(obra_med_id)
                    if "med_num_servicos" not in st.session_state:
                        st.session_state.med_num_servicos = max(1, len(df_srvs))

                    st.markdown(f"#### Serviços ({st.session_state.med_num_servicos})")

                    servicos_form = []
                    for si in range(st.session_state.med_num_servicos):
                        srv_existente = df_srvs.iloc[si] if si < len(df_srvs) else None
                        with st.expander(f"Serviço {si+1}", expanded=(si == 0)):
                            s1, s2 = st.columns(2)
                            with s1:
                                srv_nome = st.text_input("Nome:", value=srv_existente['nome'] if srv_existente is not None else "", key=f"srv_nome_{si}")
                            with s2:
                                srv_val  = st.number_input("Valor m²:", min_value=0.0, value=float(srv_existente['valor_m2_servico']) if srv_existente is not None else 0.0, key=f"srv_val_{si}")

                            df_subs = carregar_medicao_subdivisoes(int(srv_existente['id'])) if srv_existente is not None else pd.DataFrame()
                            if "med_num_subs" not in st.session_state:
                                st.session_state[f"med_num_subs_{si}"] = max(1, len(df_subs))
                            n_subs = st.number_input(f"Qtd subdivisões:", min_value=1, max_value=20, value=st.session_state.get(f"med_num_subs_{si}", max(1, len(df_subs))), key=f"n_subs_{si}")

                            subdivisoes_form = []
                            for subi in range(int(n_subs)):
                                sub_existente = df_subs.iloc[subi] if subi < len(df_subs) else None
                                sb1, sb2, sb3, sb4 = st.columns([3, 2, 2, 2])
                                with sb1:
                                    sub_nome = st.text_input("Subdivisão:", value=sub_existente['nome'] if sub_existente is not None else "", key=f"sub_nome_{si}_{subi}")
                                with sb2:
                                    sub_m2   = st.number_input("m²:", min_value=0.0, value=float(sub_existente['m2']) if sub_existente is not None else 0.0, key=f"sub_m2_{si}_{subi}")
                                with sb3:
                                    sub_pct  = st.number_input("% serv:", min_value=0.0, max_value=100.0, value=float(sub_existente['percentual']) if sub_existente is not None else 0.0, key=f"sub_pct_{si}_{subi}")
                                with sb4:
                                    val_calc = srv_val * (sub_pct / 100)
                                    sub_total = sub_m2 * val_calc
                                    st.metric("Subtotal", f"R$ {sub_total:,.2f}")
                                if sub_nome.strip():
                                    subdivisoes_form.append({"nome": sub_nome, "m2": sub_m2, "percentual": sub_pct})

                            if srv_nome.strip():
                                servicos_form.append({"nome": srv_nome, "valor_m2_servico": srv_val, "subdivisoes": subdivisoes_form})

                    col_add, col_save = st.columns([1, 2])
                    with col_add:
                        if st.button("+ Serviço"):
                            st.session_state.med_num_servicos += 1
                            st.rerun()
                    with col_save:
                        if st.button("💾 Salvar Lançamentos", type="primary"):
                            if not periodo_ref.strip():
                                st.error("Informe o período.")
                            elif not servicos_form:
                                st.error("Adicione pelo menos um serviço.")
                            else:
                                with st.spinner("Salvando..."):
                                    total = salvar_servicos_medicao(obra_med_id, periodo_ref.strip(), servicos_form)
                                if total is not None:
                                    st.success(f"Salvo! Total medido: R$ {total:,.2f}")
                                    st.rerun()

            # ── ABA 3: RELATÓRIO DE SALDOS ────────────────────────
            with tab_med:
                df_med_obras3 = carregar_medicao_obras()
                if df_med_obras3.empty:
                    st.info("Nenhuma obra cadastrada.")
                else:
                    opcoes_med3 = {row['nome']: row['id'] for _, row in df_med_obras3.iterrows()}
                    obra_med3   = st.selectbox("Obra:", list(opcoes_med3.keys()), key="sel_obra_med")
                    obra_id3    = opcoes_med3[obra_med3]
                    df_hist3    = carregar_medicao_historico(obra_id3)

                    if df_hist3.empty:
                        st.info("Nenhuma medição salva para esta obra.")
                    else:
                        periodos = df_hist3['periodo'].tolist()
                        per_sel  = st.selectbox("Período:", periodos, index=len(periodos)-1, key="sel_per_med")
                        hist_row = df_hist3[df_hist3['periodo'] == per_sel].iloc[0]
                        snapshot = hist_row['snapshot'] if isinstance(hist_row['snapshot'], list) else (_json.loads(hist_row['snapshot']) if isinstance(hist_row['snapshot'], str) else [])
                        obra_info3 = df_med_obras3[df_med_obras3['id'] == obra_id3].iloc[0]
                        total_contratado = obra_info3['valor_m2_global'] * obra_info3['metragem_geral']

                        if snapshot:
                            st.markdown("---")
                            # Tabela
                            rows_table = []
                            for srv in snapshot:
                                for sub in srv.get('subdivisoes', []):
                                    preco_m2 = srv['valor_m2_servico'] * (sub['percentual'] / 100)
                                    rows_table.append({
                                        "Serviço": srv['nome'],
                                        "Subdivisão": f"{sub['nome']} ({sub['percentual']:.0f}%)",
                                        "m²": f"{sub['m2']:.2f}",
                                        "R$/m²": f"R$ {preco_m2:.2f}",
                                        "Subtotal": f"R$ {sub.get('subtotal', sub['m2']*preco_m2):,.2f}"
                                    })
                            if rows_table:
                                st.dataframe(pd.DataFrame(rows_table), hide_index=True, use_container_width=True)

                        mc1, mc2 = st.columns(2)
                        mc1.metric("Total Contratado", f"R$ {total_contratado:,.2f}")
                        mc2.metric(f"Medição — {per_sel}", f"R$ {hist_row['total_medido']:,.2f}")

            # ── ABA 4: DASHBOARDS ─────────────────────────────────
            with tab_dash:
                df_med_obras4 = carregar_medicao_obras()
                if df_med_obras4.empty:
                    st.info("Nenhuma obra cadastrada.")
                else:
                    opcoes_med4 = {row['nome']: row['id'] for _, row in df_med_obras4.iterrows()}
                    obra_med4   = st.selectbox("Obra:", list(opcoes_med4.keys()), key="sel_obra_dash")
                    obra_id4    = opcoes_med4[obra_med4]
                    df_hist4    = carregar_medicao_historico(obra_id4)
                    obra_info4  = df_med_obras4[df_med_obras4['id'] == obra_id4].iloc[0]
                    total_contratado4 = obra_info4['valor_m2_global'] * obra_info4['metragem_geral']

                    if df_hist4.empty:
                        st.info("Nenhuma medição salva para esta obra.")
                    else:
                        # Gráfico de evolução
                        fig_evo = px.bar(
                            df_hist4, x='periodo', y='total_medido',
                            title="Evolução de Medições por Período",
                            labels={'periodo': 'Período', 'total_medido': 'R$ Medido'},
                            color_discrete_sequence=["#1E3A8A"]
                        )
                        fig_evo.add_hline(
                            y=total_contratado4, line_dash="dash",
                            line_color="#EA580C", annotation_text="Total Contratado"
                        )
                        fig_evo.update_layout(height=350, margin=dict(l=20, r=20, t=40, b=20))
                        st.plotly_chart(fig_evo, use_container_width=True)

                        # Acumulado e saldo
                        total_medido_acum = df_hist4['total_medido'].sum()
                        saldo = total_contratado4 - total_medido_acum

                        d1, d2, d3 = st.columns(3)
                        d1.metric("Total Contratado", f"R$ {total_contratado4:,.2f}")
                        d2.metric("Total Medido (acumulado)", f"R$ {total_medido_acum:,.2f}")
                        d3.metric("Saldo Remanescente", f"R$ {saldo:,.2f}",
                                  delta=f"{(total_medido_acum/total_contratado4*100):.1f}% executado" if total_contratado4 > 0 else "—")

                        st.markdown("---")
                        st.markdown("#### Tabela Comparativa por Período")
                        rows_comp = []
                        for _, h in df_hist4.iterrows():
                            snap = h['snapshot'] if isinstance(h['snapshot'], list) else (_json.loads(h['snapshot']) if isinstance(h['snapshot'], str) else [])
                            for srv in snap:
                                for sub in srv.get('subdivisoes', []):
                                    preco_m2 = srv['valor_m2_servico'] * (sub['percentual'] / 100)
                                    rows_comp.append({
                                        "Período": h['periodo'],
                                        "Serviço": srv['nome'],
                                        "Subdivisão": sub['nome'],
                                        "m²": sub['m2'],
                                        "R$/m²": preco_m2,
                                        "Subtotal (R$)": sub.get('subtotal', sub['m2'] * preco_m2)
                                    })
                        if rows_comp:
                            df_comp_tab = pd.DataFrame(rows_comp)
                            st.dataframe(
                                df_comp_tab.style.format({"m²": "{:.2f}", "R$/m²": "R$ {:.2f}", "Subtotal (R$)": "R$ {:,.2f}"}),
                                hide_index=True, use_container_width=True
                            )

    # ==================================================
    # CONFIGURACOES
    # ==================================================
    elif nome_aba == "Configuracoes":
        with aba_objeto:
            st.header("Painel de Controle Master")

            with st.expander("Cadastrar Novo Usuario"):
                with st.form("form_user"):
                    nu = st.text_input("Login:").lower().strip()
                    nn = st.text_input("Nome:")
                    ns = st.selectbox("Setor:", ["Producao", "Engenharia", "Diretoria", "Logistica", "Almoxarifado", "Medicao", "Master"])
                    np = st.text_input("Senha:", type="password")
                    if st.form_submit_button("Salvar"):
                        if not all([nu, nn, np]):
                            st.error("Preencha tudo.")
                        else:
                            conn = conectar_banco()
                            try:
                                cursor = conn.cursor()
                                cursor.execute(
                                    "INSERT INTO usuarios (usuario, nome, setor, senha) VALUES (%s,%s,%s,%s)",
                                    (nu, nn, ns, hash_senha(np))
                                )
                                conn.commit()
                                st.success(f"{nn} criado!")
                                time.sleep(0.5)
                                st.rerun()
                            except Exception as e:
                                conn.rollback()
                                st.error(f"Erro: {e}")
                            finally:
                                liberar_conexao(conn)

            conn_cfg = conectar_banco()
            try:
                df_u = pd.read_sql_query("SELECT id, usuario, nome, setor FROM usuarios ORDER BY id", conn_cfg)
            finally:
                liberar_conexao(conn_cfg)
            st.dataframe(df_u, hide_index=True, use_container_width=True)

            if len(df_u) > 1:
                del_u = st.selectbox("Remover usuario:", df_u['usuario'].tolist())
                if del_u == 'master':
                    st.caption("Conta master nao pode ser removida.")
                else:
                    if st.button(f"Excluir {del_u}"):
                        conn = conectar_banco()
                        try:
                            cursor = conn.cursor()
                            cursor.execute("DELETE FROM usuarios WHERE usuario=%s", (del_u,))
                            conn.commit()
                            st.toast("Removido!")
                            time.sleep(0.5)
                            st.rerun()
                        except Exception as e:
                            conn.rollback()
                            st.error(f"Erro: {e}")
                        finally:
                            liberar_conexao(conn)

            st.markdown("---")
            st.markdown("### ⚠️ Reset Geral")
            st.error("Esta ação remove TODOS os dados permanentemente e não pode ser desfeita.")
            confirma_reset = st.text_input("Digite CONFIRMAR para habilitar o reset:")
            if confirma_reset == "CONFIRMAR":
                if st.button("🗑️ Executar limpeza total", type="primary"):
                    resetar_banco_dados_completo()
                    st.toast("Sistema resetado!")
                    time.sleep(1)
                    st.rerun()
            else:
                st.caption("Digite CONFIRMAR no campo acima para liberar o botão de reset.")