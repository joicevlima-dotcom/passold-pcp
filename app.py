import streamlit as st
import pandas as pd
import plotly.express as px
from datetime import datetime, timedelta
import calendar as py_calendar
import os
import time
import hashlib
import psycopg2
import psycopg2.extras
from zoneinfo import ZoneInfo
FUSO_BR = ZoneInfo('America/Sao_Paulo')

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
.stButton > button *, .stButton > button p, .stButton > button span { color: white!important; }
.stButton > button[kind="primary"] { background-color: var(--accent-color)!important; }
.stButton > button[kind="primary"]:hover { background-color: #c2410c!important; }
.stTextInput > div > div > input, .stSelectbox > div > div > select, .stNumberInput > div > div > input { background-color: var(--bg-card)!important; border: 1px solid var(--border-color)!important; border-radius: 6px!important; color: var(--text-main)!important; padding: 10px!important; font-size: 0.9rem!important; box-shadow: none!important; }
.stTextInput > div > div > input:focus, .stSelectbox > div > div > select:focus { border-color: var(--primary-color)!important; box-shadow: 0 0 0 2px rgba(15, 23, 42, 0.1)!important; }
div[data-testid="stDataFrame"] { border-radius: var(--radius)!important; border: 1px solid var(--border-color)!important; overflow: hidden; }
thead tr th { background-color: #F1F5F9!important; color: var(--primary-light)!important; font-weight: 600!important; text-transform: uppercase; font-size: 0.75rem!important; letter-spacing: 0.05em; border-bottom: 2px solid var(--border-color)!important; }
.stTabs [data-baseweb="tab-list"] { gap: 24px; border-bottom: 1px solid var(--border-color); }
.stTabs [data-baseweb="tab"] { height: 50px; white-space: pre-wrap; background-color: transparent; border-radius: 4px 4px 0px 0px; color: var(--text-muted); font-weight: 500; transition: all 0.2s; }
.stTabs [aria-selected="true"] { background-color: var(--bg-body); color: var(--accent-color); font-weight: 700; border-bottom: 3px solid var(--accent-color); }
.badge-obra { background:#FFF7ED; color:#C2410C; padding:4px 10px; border-radius:6px; font-weight:700; font-size:11px; text-transform:uppercase; letter-spacing:0.05em; }
.badge-edt  { background:#F1F5F9; color:#334155; padding:4px 10px; border-radius:6px; font-weight:600; font-size:11px; border:1px solid #E2E8F0; }
.badge-lote { background:#ECFDF5; color:#047857; padding:4px 10px; border-radius:6px; font-weight:700; font-size:11px; }
.cal-day-active, .cal-day-today { background: linear-gradient(135deg, #EFF6FF 0%, #DBEAFE 100%); border: 1px solid #3B82F6; box-shadow: 0 2px 4px rgba(59, 130, 246, 0.2); }
.bar-ok      { border-left: 5px solid var(--success-color); background: #F0FDF4; padding: 12px 16px; border-radius: 6px; margin-bottom: 10px; box-shadow: var(--shadow-sm); }
.bar-warn    { border-left: 5px solid var(--warning-color); background: #FFFBEB; padding: 12px 16px; border-radius: 6px; margin-bottom: 10px; box-shadow: var(--shadow-sm); }
.bar-danger  { border-left: 5px solid var(--danger-color);  background: #FEF2F2; padding: 12px 16px; border-radius: 6px; margin-bottom: 10px; box-shadow: var(--shadow-sm); }
.bar-neutral { border-left: 5px solid var(--text-muted);    background: #F8FAFC; padding: 12px 16px; border-radius: 6px; margin-bottom: 10px; box-shadow: var(--shadow-sm); }
.login-container { background: var(--bg-card); padding: 40px; border-radius: 12px; box-shadow: 0 10px 25px -5px rgba(0,0,0,0.1), 0 8px 10px -6px rgba(0,0,0,0.1); border: 1px solid var(--border-color); text-align: center; }
#MainMenu { visibility: hidden; }
footer    { visibility: hidden; }
header    { visibility: hidden; }
</style>
""", unsafe_allow_html=True)

HOJE_PROJETO = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)

# ========================================================
# CONEXÃO SUPABASE
# ========================================================
def conectar_banco():
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
            Enviado_Logistica INTEGER DEFAULT 0
        )
    """)
    cursor.execute("ALTER TABLE itens_detalhado ADD COLUMN IF NOT EXISTS Data_Despacho DATE")
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

def ultima_semana_producao(dt_inicio, dt_fim):
    dt_fim_dt    = pd.to_datetime(dt_fim)
    dt_inicio_dt = pd.to_datetime(dt_inicio)
    inicio_ultima_semana = dt_fim_dt - timedelta(days=6)
    return max(inicio_ultima_semana, dt_inicio_dt)

# ========================================================
# FUNÇÕES DE BANCO
# ========================================================
def carregar_macro():
    conn = conectar_banco()
    df = pd.read_sql_query("SELECT * FROM cronograma_macro ORDER BY id", conn)
    conn.close()
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
    df = df.rename(columns=rename)
    return df

def carregar_micro():
    conn = conectar_banco()
    df = pd.read_sql_query("SELECT * FROM itens_detalhado ORDER BY Data_Producao_Programada ASC", conn)
    conn.close()
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
    df = df.rename(columns=rename)
    return df

def carregar_fila_logistica():
    conn = conectar_banco()
    df = pd.read_sql_query("SELECT * FROM logistica_envios ORDER BY data_limite_despacho ASC NULLS LAST", conn)
    conn.close()
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
    df = df.rename(columns=rename)
    return df

def carregar_solicitacoes():
    conn = conectar_banco()
    df = pd.read_sql_query("SELECT * FROM solicitacoes_prazo ORDER BY id DESC", conn)
    conn.close()
    return df

def salvar_lotes_micro(lotes: list):
    if not lotes:
        return
    conn = conectar_banco()
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
    conn.close()

def deletar_lotes_por_edt_lote(obra, edt, cod_lote):
    conn = conectar_banco()
    cursor = conn.cursor()
    if edt:
        cursor.execute("DELETE FROM itens_detalhado WHERE Obra_Vinculada=%s AND EDT_Vinculado=%s AND Cod_Lote=%s", (obra, edt, cod_lote))
    else:
        cursor.execute("DELETE FROM itens_detalhado WHERE Obra_Vinculada=%s AND Cod_Lote=%s", (obra, cod_lote))
    conn.commit()
    conn.close()

def atualizar_cronograma_macro_datas(edt, prazo_eng, primeiro_prod, despacho):
    conn = conectar_banco()
    cursor = conn.cursor()
    cursor.execute("SELECT prazo_engenharia, primeiro_dia_producao, data_limite_despacho FROM cronograma_macro WHERE EDT=%s", (edt,))
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
    """, (novo_prazo.strftime('%Y-%m-%d'), novo_primeiro.strftime('%Y-%m-%d'), novo_despacho.strftime('%Y-%m-%d'), edt))
    conn.commit()
    conn.close()

def atualizar_status_engenharia(edt_id, novo_status):
    conn = conectar_banco()
    cursor = conn.cursor()
    cursor.execute("UPDATE cronograma_macro SET Status_Engenharia=%s WHERE id=%s", (novo_status, edt_id))
    conn.commit()
    conn.close()

def salvar_solicitacao(edt, tarefa, prazo_atual, prazo_sol, justif, criado_por):
    conn = conectar_banco()
    cursor = conn.cursor()
    cursor.execute("""
        INSERT INTO solicitacoes_prazo (edt, tarefa, prazo_atual, prazo_solicitado, justificativa, criado_por, status, criado_em)
        VALUES (%s,%s,%s,%s,%s,%s,'Pendente de Aprovacao',%s)
    """, (edt, tarefa, prazo_atual, prazo_sol, justif, criado_por, datetime.now().strftime('%d/%m/%Y %H:%M')))
    conn.commit()
    conn.close()

def atualizar_status_solicitacao(sol_id, novo_status):
    conn = conectar_banco()
    cursor = conn.cursor()
    cursor.execute("UPDATE solicitacoes_prazo SET status=%s WHERE id=%s", (novo_status, sol_id))
    conn.commit()
    conn.close()

def enviar_para_logistica(row, limite_despacho):
    conn = conectar_banco()
    cursor = conn.cursor()
    cursor.execute("SELECT id FROM logistica_envios WHERE item_id=%s", (int(row['id']),))
    if cursor.fetchone():
        conn.close()
        return
    cursor.execute("""
        INSERT INTO logistica_envios
        (item_id, Obra_Vinculada, EDT_Vinculado, Cod_Lote, Num_OP, Tipo_Material,
         Qtd_Caixas, M2_Item, Romaneio_Chapas, Data_Limite_Despacho, Status_Logistica)
        VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,'Aguardando Agendamento')
    """, (
        int(row['id']), row['Obra_Vinculada'], row['EDT_Vinculado'], row['Cod_Lote'],
        row.get('Num_OP') or '', row['Tipo_Material'], int(row['Qtd_Caixas']), float(row['M2_Item']),
        row['Romaneio_Chapas'], limite_despacho.strftime('%Y-%m-%d') if prazo_valido(limite_despacho) else None
    ))
    cursor.execute("UPDATE itens_detalhado SET Enviado_Logistica=1 WHERE id=%s", (int(row['id']),))
    conn.commit()
    conn.close()

def agendar_envio(log_id, data_envio, transportadora, veiculo, obs, usuario):
    conn = conectar_banco()
    cursor = conn.cursor()
    cursor.execute("""
        UPDATE logistica_envios
        SET Data_Envio_Agendado=%s, Transportadora=%s, Veiculo=%s, Observacoes=%s, Status_Logistica='Envio Agendado'
        WHERE id=%s
    """, (data_envio.strftime('%Y-%m-%d') if data_envio else None, transportadora, veiculo, obs, log_id))
    conn.commit()
    conn.close()

def confirmar_despacho(log_id, usuario):
    conn = conectar_banco()
    cursor = conn.cursor()
    cursor.execute("""
        UPDATE logistica_envios
        SET Status_Logistica='Despachado', Confirmado_Por=%s, Confirmado_Em=%s
        WHERE id=%s
    """, (usuario, datetime.now().strftime('%d/%m/%Y %H:%M'), log_id))
    conn.commit()
    conn.close()

def verificar_login(usuario, senha):
    conn = conectar_banco()
    cursor = conn.cursor()
    cursor.execute("SELECT nome, setor FROM usuarios WHERE usuario=%s AND senha=%s", (usuario, hash_senha(senha)))
    resultado = cursor.fetchone()
    conn.close()
    return resultado

def resetar_banco_dados_completo():
    conn = conectar_banco()
    cursor = conn.cursor()
    for tabela in ['cronograma_macro', 'itens_detalhado', 'solicitacoes_prazo', 'logistica_envios']:
        cursor.execute(f"DELETE FROM {tabela}")
    conn.commit()
    conn.close()

def salvar_componentes(item_id, obra, cod_lote, num_op, componentes: list):
    conn = conectar_banco()
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
    conn.close()

def carregar_componentes_op(item_id):
    conn = conectar_banco()
    df = pd.read_sql_query("SELECT * FROM componentes_op WHERE item_id=%s ORDER BY id", conn, params=(item_id,))
    conn.close()
    return df

def carregar_todas_ops_com_componentes():
    conn = conectar_banco()
    df = pd.read_sql_query("""
        SELECT DISTINCT item_id, Obra_Vinculada, Cod_Lote, Num_OP
        FROM componentes_op
        ORDER BY Obra_Vinculada, Cod_Lote
    """, conn)
    conn.close()
    return df

def atualizar_componente(comp_id, status, obs, usuario):
    conn = conectar_banco()
    cursor = conn.cursor()
    cursor.execute("""
        UPDATE componentes_op
        SET Status_Item=%s, Observacao=%s, Conferido_Por=%s, Conferido_Em=%s
        WHERE id=%s
    """, (status, obs, usuario, datetime.now().strftime('%d/%m/%Y %H:%M'), comp_id))
    conn.commit()
    conn.close()

# ========================================================
# HELPER — BLOCOS SEMANAIS (reutilizável)
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
        <p style='text-align:center; color:#64748B; font-size:13px;
                    margin-top:8px; letter-spacing:0.05em;'>
        PCP & Controle Operacional
        </p>
        """, unsafe_allow_html=True)
        with st.container(border=True):
            st.markdown("<p style='text-align:center;font-size:16px;font-weight:600;color:#0F172A;margin-bottom:8px;'>Acesso ao Sistema</p>", unsafe_allow_html=True)
            user_input = st.text_input("Usuário:")
            pass_input = st.text_input("Senha:", type="password")
            if st.button("Entrar", use_container_width=True):
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
    obras_lista       = sorted(df_banco_macro['Obra'].unique().tolist())
    obra_selecionada  = st.selectbox("Obra de trabalho:", obras_lista)
    df_macro_filtrado = df_banco_macro[df_banco_macro['Obra'] == obra_selecionada].copy()
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
if setor in ["Master"]:
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

            # SEÇÃO 1 — PREVISÃO
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

            # SEÇÃO 2 — CALENDÁRIO
            st.markdown("### 📆 Calendário de Produção — OPs Liberadas")
            st.caption("Apenas lotes liberados oficialmente na aba 'Liberar OPs da Semana'.")
            if not df_banco_micro.empty:
                df_base = df_banco_micro[df_banco_micro['Status_Item'] == "Liberado para Fabrica"].copy()
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
                                        st.markdown("<span style='color:#EA580C;font-size:12px;font-weight:600;'>Ultima semana de producao — liberado para concluir</span>", unsafe_allow_html=True)
                                    else:
                                        dias_restantes = (pd.to_datetime(row['Data_Limite_Obra']).date() - dia_sel).days
                                        st.markdown(f"<span style='color:#3B82F6;font-size:12px;'>Em producao — {dias_restantes} dias ate o prazo</span>", unsafe_allow_html=True)
                                with ca:
                                    if pode_concluir:
                                        st.write("")
                                        if st.button("Pronto", key=f"baixa_{row['id']}", type="primary", use_container_width=True):
                                            limite_desp = None
                                            if not df_banco_macro.empty:
                                                fr = df_banco_macro[df_banco_macro['EDT'] == row['EDT_Vinculado']]
                                                if not fr.empty:
                                                    limite_desp = fr.iloc[0].get('Data_Limite_Despacho')
                                            conn = conectar_banco()
                                            cursor = conn.cursor()
                                            cursor.execute("UPDATE itens_detalhado SET Status_Item='Concluido' WHERE id=%s", (row['id'],))
                                            conn.commit()
                                            conn.close()
                                            enviar_para_logistica(row, limite_desp if prazo_valido(limite_desp) else pd.NaT)
                                            st.toast(f"{row['Cod_Lote']} concluido — enviado para Logistica!")
                                            time.sleep(0.3)
                                            st.rerun()
                                    else:
                                        st.write("")
                                        st.markdown("<div style='text-align:center;color:#94A3B8;font-size:12px;padding:8px;'>Em producao</div>", unsafe_allow_html=True)
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
                st.markdown("<div style='text-align:center;padding:60px;color:#94A3B8;font-size:20px;'>Nenhum lote cadastrado no sistema.</div>", unsafe_allow_html=True)
            else:
                def urgencia(row):
                    prazo = row.get('Data_Limite_Obra')
                    if not prazo_valido(prazo):
                        return 'sem_prazo'
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
                    'Pendente':              ('⏳', '#64748B', '#F1F5F9'),
                    'Liberado para Fabrica': ('🔧', '#1D4ED8', '#EFF6FF'),
                    'Concluido':             ('✅', '#15803D', '#F0FDF4'),
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
                                    <span style='font-size:11px;font-weight:700;color:{cfg["tag_color"]};background:{cfg["bg"]};border:1px solid {cfg["border"]};padding:2px 8px;border-radius:4px;'>{cfg["tag"]}</span>
                                    <span style='font-size:11px;color:#64748B;font-weight:600;'>{dias_txt}</span>
                                </div>
                                <div style='font-size:20px;font-weight:800;color:#0F172A;margin-bottom:4px;'>{row["Obra_Vinculada"]}</div>
                                <div style='font-size:13px;color:#475569;margin-bottom:12px;'>{row["Tipo_Material"]} &nbsp;·&nbsp; {row["Romaneio_Chapas"] or "—"}</div>
                                <div style='display:grid;grid-template-columns:1fr 1fr;gap:8px;'>
                                    <div style='background:white;border-radius:6px;padding:8px 10px;'><div style='font-size:10px;color:#94A3B8;text-transform:uppercase;letter-spacing:0.05em;'>OP</div><div style='font-size:15px;font-weight:700;color:#1E293B;'>{op_txt}</div></div>
                                    <div style='background:white;border-radius:6px;padding:8px 10px;'><div style='font-size:10px;color:#94A3B8;text-transform:uppercase;letter-spacing:0.05em;'>M²</div><div style='font-size:15px;font-weight:700;color:#1E293B;'>{row["M2_Item"]:.2f}</div></div>
                                    <div style='background:white;border-radius:6px;padding:8px 10px;'><div style='font-size:10px;color:#94A3B8;text-transform:uppercase;letter-spacing:0.05em;'>Status</div><div style='font-size:13px;font-weight:700;color:{ec};'>{em} {row["Status_Item"]}</div></div>
                                    <div style='background:white;border-radius:6px;padding:8px 10px;'><div style='font-size:10px;color:#94A3B8;text-transform:uppercase;letter-spacing:0.05em;'>Prazo</div><div style='font-size:15px;font-weight:700;color:{cfg["tag_color"]};'>{prazo_fmt}</div></div>
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
                            cursor = conn.cursor()
                            for item_id in ids_sel:
                                cursor.execute(
                                    "UPDATE itens_detalhado SET Status_Item='Liberado para Fabrica', Num_OP=%s WHERE id=%s",
                                    (f"{prefixo}{str(item_id).zfill(3)}", item_id)
                                )
                            conn.commit()
                            conn.close()
                            st.toast("OPs liberadas!")
                            time.sleep(0.5)
                            st.rerun()
                        else:
                            st.warning("Selecione pelo menos um item.")
                else:
                    st.success("Todos os lotes ja foram liberados.")

                # ------------------------------------------------
                # INSERIR COMPONENTES POR OP
                # ------------------------------------------------
                st.markdown("---")
                st.markdown("### 📦 Inserir Componentes por OP")
                st.caption("Selecione uma OP já liberada e insira a lista de componentes para o almoxarifado.")

                df_lib_ops = df_banco_micro[
                    (df_banco_micro['Obra_Vinculada'] == obra_selecionada) &
                    (df_banco_micro['Status_Item'] == "Liberado para Fabrica")
                ].copy() if not df_banco_micro.empty else pd.DataFrame()

                if not df_lib_ops.empty:
                    opcoes_ops = [
                        f"{row['Num_OP']} — {row['Cod_Lote']} | {row['Tipo_Material']}"
                        for _, row in df_lib_ops.iterrows()
                        if row.get('Num_OP')
                    ]
                    if opcoes_ops:
                        op_sel = st.selectbox("OP:", opcoes_ops, key="sel_op_comp")
                        row_op = df_lib_ops[df_lib_ops['Num_OP'] == op_sel.split(" — ")[0].strip()].iloc[0]

                        comp_existentes = carregar_componentes_op(int(row_op['id']))
                        if not comp_existentes.empty:
                            st.success(f"✅ {len(comp_existentes)} componente(s) já cadastrado(s) para esta OP.")

                        with st.expander("➕ Adicionar / Substituir lista de componentes", expanded=comp_existentes.empty):
                            st.caption("⚠️ Salvar substitui a lista anterior desta OP.")
                            num_itens = st.number_input("Quantos componentes?", min_value=1, max_value=30, value=3, key="num_comp")
                            componentes_input = []
                            for idx in range(int(num_itens)):
                                c1, c2, c3 = st.columns([4, 2, 2])
                                with c1:
                                    nome = st.text_input(f"Componente {idx+1}:", key=f"comp_nome_{idx}")
                                with c2:
                                    qtd = st.number_input(f"Qtd {idx+1}:", min_value=0.0, value=1.0, key=f"comp_qtd_{idx}")
                                with c3:
                                    und = st.selectbox(f"Un {idx+1}:", ["un", "kg", "m", "m²", "cx", "pç", "rolo"], key=f"comp_und_{idx}")
                                if nome.strip():
                                    componentes_input.append({"nome": nome.strip(), "qtd": qtd, "unidade": und})

                            if st.button("💾 Salvar lista de componentes", key="btn_salvar_comp"):
                                if not componentes_input:
                                    st.error("Preencha pelo menos um componente.")
                                else:
                                    salvar_componentes(
                                        int(row_op['id']),
                                        row_op['Obra_Vinculada'],
                                        row_op['Cod_Lote'],
                                        row_op['Num_OP'],
                                        componentes_input
                                    )
                                    st.toast(f"Lista salva para {row_op['Num_OP']}!")
                                    time.sleep(0.3)
                                    st.rerun()
                    else:
                        st.info("Nenhuma OP com número gerado ainda. Libere as OPs primeiro.")
                else:
                    st.info("Nenhuma OP liberada para esta obra ainda.")

            else:
                st.info("Nenhum lote pendente encontrado.")

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
                c3.metric("Prazo de Despacho Mais Distante", data_max.strftime('%d/%m/%Y') if prazo_valido(data_max) else "N/A")

                st.markdown("---")
                st.subheader("Carga Semanal")

                obras_macro = ["Todas as obras"] + (
                    sorted(df_banco_micro['Obra_Vinculada'].dropna().unique().tolist())
                    if not df_banco_micro.empty else []
                )

                # BLOCO 1: PREVISÃO
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

                # BLOCO 2: EM PRODUÇÃO
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

                # BLOCO 3: CONCLUÍDOS
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
                st.caption("1 lote = 1 entrega. Informe quantas caixas e ate quando — o sistema calcula quando comeca a producao.")

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
                        data_alvo = st.date_input("Precisa estar na obra ate:", value=default_dt, format="DD/MM/YYYY",
                                                  help="Data limite — tudo e calculado retroativamente a partir daqui")
                        dias_log  = st.number_input("Dias de transporte ate a obra (corridos):", min_value=1, value=3)
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
                df_ed_raw = carregar_micro()
                if not df_ed_raw.empty:
                    df_obra = df_ed_raw[df_ed_raw['Obra_Vinculada'] == obra_selecionada].copy()
                    if not df_obra.empty:
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
                            cursor = conn.cursor()
                            for row in alteradas:
                                cursor.execute("""
                                    UPDATE itens_detalhado
                                    SET Cod_Lote=%s, Tipo_Material=%s, Qtd_Caixas=%s, M2_Item=%s,
                                        Data_Producao_Programada=%s, Data_Limite_Obra=%s,
                                        Romaneio_Chapas=%s, Status_Item=%s, Dificuldade=%s, Fase_Produtiva=%s
                                    WHERE id=%s
                                """, (
                                    row['Cod_Lote'], row['Tipo_Material'], int(row['Qtd_Caixas']),
                                    float(row['M2_Item']), row['Data_Producao_Programada'],
                                    row['Data_Limite_Obra'], row['Romaneio_Chapas'],
                                    row['Status_Item'], int(row['Dificuldade']),
                                    row['Fase_Produtiva'], int(row['id'])
                                ))
                            conn.commit()
                            conn.close()
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
                    escopo = st.selectbox("Escopo:", ["ACM", "Vidro/Esquadria"])
                    frente = st.text_input("Frente Macro:", value=st.session_state.mem_frente)
                    tarefa = st.text_input("Nome da Tarefa:", value=st.session_state.mem_tarefa)
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
                        cursor = conn.cursor()
                        try:
                            cursor.execute("""
                                INSERT INTO cronograma_macro
                                (Obra, EDT, Tipo_Escopo, Etapa_Macro, Subdivisao, Tarefa,
                                 M2_Total_Tarefa, Inicio_Previsto, Termino_Obra, Status, Status_Engenharia)
                                VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,'Pendente','Aguardando Medicao In Loco')
                            """, (nome_obra, edt_cod, escopo, frente, subdiv, tarefa,
                                  float(m2_tot), dt_ini.strftime('%Y-%m-%d'), dt_fim.strftime('%Y-%m-%d')))
                            conn.commit()
                            st.toast("Frente registrada!")
                            time.sleep(0.4)
                            st.rerun()
                        except Exception as e:
                            st.error(f"EDT '{edt_cod}' ja existe ou erro: {e}")
                        finally:
                            conn.close()

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
                st.warning("Isso remove a frente do cronograma macro. Lotes vinculados NÃO são removidos automaticamente.")
                opcoes_del = [
                    f"{row['EDT']} — {row['Tarefa']} [{row.get('Subdivisao','')}]"
                    for _, row in df_banco_macro[df_banco_macro['Obra'] == obra_selecionada].iterrows()
                ] if not df_banco_macro.empty else []
                if opcoes_del:
                    frente_del = st.selectbox("Frente para excluir:", opcoes_del, key="sel_del_frente")
                    edt_del    = frente_del.split(" — ")[0].strip()
                    if st.button(f"Excluir frente {edt_del}", key="btn_del_frente"):
                        conn = conectar_banco()
                        cursor = conn.cursor()
                        cursor.execute("DELETE FROM cronograma_macro WHERE EDT=%s", (edt_del,))
                        conn.commit()
                        conn.close()
                        st.toast(f"Frente {edt_del} removida!")
                        time.sleep(0.5)
                        st.rerun()

    # ==================================================
    # PAINEL DE ENGENHARIA
    # ==================================================
    elif nome_aba == "Painel de Engenharia":
        with aba_objeto:
            st.header("Painel Tecnico da Engenharia")
            st.caption(f"Hoje: {HOJE_PROJETO.strftime('%d/%m/%Y')} | Obra: **{obra_selecionada or 'Nenhuma'}**")
            df_eng = carregar_macro()
            if obra_selecionada:
                df_eng = df_eng[df_eng['Obra'] == obra_selecionada]
            else:
                df_eng = pd.DataFrame()

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
                st.info("Nenhum lote na fila. Quando a producao marcar como pronto, aparece aqui automaticamente.")

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
                            if dias_r < 0:   css_bar = "bar-danger"; tag = f"ATRASADO {abs(dias_r)}d"
                            elif dias_r <= 3: css_bar = "bar-warn";  tag = f"URGENTE — {dias_r}d restantes"
                            else:             css_bar = "bar-ok";    tag = f"{dias_r} dias restantes"
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
                                cursor = conn.cursor()
                                cursor.execute("UPDATE logistica_envios SET Status_Logistica='Aguardando Agendamento' WHERE id=%s", (row['id'],))
                                conn.commit()
                                conn.close()
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
                # métricas rápidas
                todos_comps = pd.read_sql_query(
                    "SELECT * FROM componentes_op ORDER BY item_id, id",
                    conectar_banco()
                )
                n_aguard  = len(todos_comps[todos_comps['status_item'] == 'Aguardando Conferencia'])
                n_ok      = len(todos_comps[todos_comps['status_item'] == 'Disponivel'])
                n_falta   = len(todos_comps[todos_comps['status_item'] == 'Indisponivel'])

                c1, c2, c3 = st.columns(3)
                c1.metric("⏳ Aguardando", n_aguard)
                c2.metric("✅ Disponíveis", n_ok)
                c3.metric("❌ Indisponíveis", n_falta)
                st.markdown("---")

                # agrupa por OP
                for _, op_row in df_ops_comp.iterrows():
                    df_comp = carregar_componentes_op(int(op_row['item_id']))
                    if df_comp.empty:
                        continue

                    n_total   = len(df_comp)
                    n_conf    = len(df_comp[df_comp['status_item'] != 'Aguardando Conferencia'])
                    n_indisp  = len(df_comp[df_comp['status_item'] == 'Indisponivel'])

                    if n_indisp > 0:
                        css_bar = "bar-danger"
                        icone   = "❌"
                    elif n_conf == n_total:
                        css_bar = "bar-ok"
                        icone   = "✅"
                    else:
                        css_bar = "bar-warn"
                        icone   = "⏳"

                    with st.expander(
                        f"{icone} OP: {op_row['num_op']} — {op_row['cod_lote']} | {op_row['obra_vinculada']}  "
                        f"({n_conf}/{n_total} conferidos{f' — {n_indisp} FALTANDO' if n_indisp > 0 else ''})",
                        expanded=(n_indisp > 0 or n_conf < n_total)
                    ):
                        # cabeçalho
                        hc = st.columns([4, 2, 2, 3, 2])
                        for col_h, label in zip(hc, ["COMPONENTE", "QTD", "UN", "STATUS", "AÇÃO"]):
                            col_h.markdown(
                                f"<div style='font-size:11px;font-weight:700;color:#94A3B8;"
                                f"text-transform:uppercase;letter-spacing:0.07em;'>{label}</div>",
                                unsafe_allow_html=True
                            )
                        st.markdown("<hr style='margin:4px 0 8px 0;border-color:#E2E8F0;'>", unsafe_allow_html=True)

                        for _, comp in df_comp.iterrows():
                            st_item = comp['status_item']
                            if st_item == 'Disponivel':
                                cor = "#15803D"; bg = "#F0FDF4"; emoji = "✅"
                            elif st_item == 'Indisponivel':
                                cor = "#DC2626"; bg = "#FEF2F2"; emoji = "❌"
                            else:
                                cor = "#D97706"; bg = "#FFFBEB"; emoji = "⏳"

                            rc = st.columns([4, 2, 2, 3, 2])
                            rc[0].markdown(f"**{comp['nome_componente']}**")
                            rc[1].markdown(f"`{comp['quantidade']}`")
                            rc[2].markdown(f"{comp['unidade']}")
                            rc[3].markdown(
                                f"<span style='background:{bg};color:{cor};padding:3px 8px;"
                                f"border-radius:4px;font-size:12px;font-weight:600;'>{emoji} {st_item}</span>",
                                unsafe_allow_html=True
                            )
                            with rc[4]:
                                acao = st.selectbox(
                                    "", ["Aguardando Conferencia", "Disponivel", "Indisponivel"],
                                    index=["Aguardando Conferencia", "Disponivel", "Indisponivel"].index(st_item),
                                    key=f"alm_st_{comp['id']}",
                                    label_visibility="collapsed"
                                )
                                if acao != st_item:
                                    atualizar_componente(comp['id'], acao, comp.get('observacao') or '', st.session_state.usuario_nome)
                                    st.rerun()

                            # campo de observação livre por item
                            obs_atual = comp.get('observacao') or ''
                            obs_nova  = st.text_input(
                                f"Obs — {comp['nome_componente']}:",
                                value=obs_atual,
                                key=f"alm_obs_{comp['id']}",
                                placeholder="Ex: em falta, previsão 20/06..."
                            )
                            if obs_nova != obs_atual:
                                atualizar_componente(comp['id'], st_item, obs_nova, st.session_state.usuario_nome)

                            st.markdown("<hr style='margin:4px 0;border-color:#F1F5F9;'>", unsafe_allow_html=True)

                        # resumo da OP
                        if n_indisp > 0:
                            itens_falt = df_comp[df_comp['status_item'] == 'Indisponivel']['nome_componente'].tolist()
                            st.error(f"⚠️ Itens em falta: {', '.join(itens_falt)}")
                        elif n_conf == n_total:
                            st.success("✅ Todos os componentes conferidos e disponíveis!")
    
    # ==================================================
    # SISTEMA DE MEDICAO
    # ==================================================
    elif nome_aba == "Sistema de Medicao":
        with aba_objeto:
            st.components.v1.html("""
<!DOCTYPE html>
<html lang="pt-BR">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <script src="https://cdn.tailwindcss.com"></script>
    <script src="https://cdn.jsdelivr.net/npm/chart.js"></script>
    <style>
        .tab-active { border-color: #1e40af; color: #1e40af; font-weight: 700; background-color: #f8fafc; }
        @media print { .no-print { display: none !important; } body { background-color: #fff; } }
    </style>
</head>
<body class="bg-slate-50 min-h-screen text-slate-800 font-sans">
    <header class="bg-white border-b border-slate-200 shadow-sm">
        <div class="max-w-7xl mx-auto px-6 py-4 flex flex-col sm:flex-row items-center justify-between gap-4">
            <div class="flex items-center gap-4">
                <span class="text-lg font-black text-slate-900 tracking-tight">Passold Sistemas de Fachadas</span>
                <div class="h-8 w-px bg-slate-200 hidden sm:block"></div>
                <span class="text-xs font-bold uppercase tracking-wider text-slate-400 hidden sm:block">Sistema de Medição</span>
            </div>
            <p class="text-xs text-slate-500 font-medium">Gestão de Saldos & Escopos Físicos</p>
        </div>
    </header>

    <nav class="bg-white border-b border-slate-200 sticky top-0 z-50 shadow-xs">
        <div class="max-w-7xl mx-auto px-4 flex overflow-x-auto space-x-1 sm:space-x-4">
            <button onclick="mudarAba('aba-cadastro')" id="btn-cadastro" class="py-3.5 px-4 border-b-2 border-transparent text-xs sm:text-sm font-semibold transition-all cursor-pointer text-slate-600 hover:text-slate-900 tab-active whitespace-nowrap">1. Cadastrar Obra Base</button>
            <button onclick="mudarAba('aba-servicos')" id="btn-servicos" class="py-3.5 px-4 border-b-2 border-transparent text-xs sm:text-sm font-semibold transition-all cursor-pointer text-slate-600 hover:text-slate-900 whitespace-nowrap">2. Parâmetros de Serviços & Etapas</button>
            <button onclick="mudarAba('aba-medicao')" id="btn-medicao" class="py-3.5 px-4 border-b-2 border-transparent text-xs sm:text-sm font-semibold transition-all cursor-pointer text-slate-600 hover:text-slate-900 whitespace-nowrap">3. Relatório de Saldos e Medições</button>
            <button onclick="mudarAba('aba-relatorios')" id="btn-relatorios" class="py-3.5 px-4 border-b-2 border-transparent text-xs sm:text-sm font-bold transition-all cursor-pointer text-blue-600 hover:text-blue-800 whitespace-nowrap">📊 4. Dashboards & Comparativos</button>
        </div>
    </nav>

    <main class="max-w-7xl mx-auto p-4 md:p-8">
        <section id="aba-cadastro" class="space-y-6">
            <div class="bg-white rounded-xl shadow-sm border border-slate-200 p-6">
                <div class="border-l-4 border-blue-800 pl-3 mb-6">
                    <h2 class="text-lg font-bold text-slate-900">Cadastrar Nova Obra (Teto Geral)</h2>
                    <p class="text-xs text-slate-500">Defina os limites orçamentários base do contrato</p>
                </div>
                <div class="grid grid-cols-1 md:grid-cols-3 gap-5 mb-6">
                    <div>
                        <label class="block text-xs font-bold uppercase text-slate-500 mb-1.5">Nome da Obra / Contrato</label>
                        <input type="text" id="cad-nome-obra" placeholder="Ex: Residencial Bella Vista" class="w-full bg-slate-50 border border-slate-200 rounded-lg p-2.5 text-sm focus:ring-2 focus:ring-blue-600 focus:bg-white outline-none">
                    </div>
                    <div>
                        <label class="block text-xs font-bold uppercase text-slate-500 mb-1.5">Valor m² Teto da Obra (R$/m²)</label>
                        <input type="number" id="cad-valor-m2" placeholder="Ex: 500.00" step="any" class="w-full bg-slate-50 border border-slate-200 rounded-lg p-2.5 text-sm focus:ring-2 focus:ring-blue-600 focus:bg-white outline-none font-bold">
                    </div>
                    <div>
                        <label class="block text-xs font-bold uppercase text-slate-500 mb-1.5">Metragem Geral da Obra (m²)</label>
                        <input type="number" id="cad-metragem-geral" placeholder="Ex: 1500.00" step="any" class="w-full bg-slate-50 border border-slate-200 rounded-lg p-2.5 text-sm focus:ring-2 focus:ring-blue-600 focus:bg-white outline-none">
                    </div>
                </div>
                <div class="flex justify-end border-t border-slate-100 pt-4">
                    <button onclick="salvarObraBase()" class="bg-blue-800 hover:bg-blue-900 text-white font-bold px-6 py-2.5 rounded-lg text-xs uppercase tracking-wider shadow-sm transition cursor-pointer">Salvar Obra</button>
                </div>
            </div>
            <div class="bg-white rounded-xl shadow-sm border border-slate-200 p-6">
                <h3 class="text-sm font-bold uppercase tracking-wider text-slate-400 mb-4">Obras Cadastradas</h3>
                <div id="grid-obras" class="grid grid-cols-1 md:grid-cols-3 gap-4"></div>
            </div>
        </section>

        <section id="aba-servicos" class="space-y-6 hidden">
            <div class="bg-white rounded-xl shadow-sm border border-slate-200 p-6">
                <div class="flex flex-col lg:flex-row lg:items-center justify-between gap-4 border-b border-slate-100 pb-4 mb-6">
                    <div class="flex flex-col md:flex-row md:items-center gap-6">
                        <div class="border-l-4 border-blue-800 pl-3">
                            <h2 class="text-lg font-bold text-slate-900">Configurar Preços e Subdivisões por Serviço</h2>
                            <p class="text-xs text-slate-500 mt-0.5" id="info-teto-obra-ativa"></p>
                        </div>
                        <div class="flex flex-col">
                            <label class="text-xs font-bold text-slate-400 uppercase mb-1">Período de Referência</label>
                            <input type="month" id="mes-servicos-referencia" class="bg-slate-50 border border-slate-200 rounded-lg p-2 text-xs outline-none focus:ring-2 focus:ring-blue-600 font-bold text-slate-700">
                        </div>
                    </div>
                    <div class="w-full lg:w-72">
                        <label class="block text-xs font-bold text-slate-400 uppercase mb-1">Selecione a Obra Alvo</label>
                        <select id="select-obra-servicos" onchange="selecionarObraServicos()" class="w-full bg-slate-50 border border-slate-200 rounded-lg p-2.5 text-sm font-bold text-slate-900 outline-none focus:ring-2 focus:ring-blue-600">
                            <option value="">-- Escolha uma Obra --</option>
                        </select>
                    </div>
                </div>
                <div id="aviso-selecao-servicos" class="text-center py-12 text-slate-400 border border-dashed border-slate-200 rounded-xl bg-slate-50/50 text-sm">Selecione uma obra acima para liberar a planilha de engenharia e custos locais.</div>
                <div id="container-lista-servicos" class="space-y-6"></div>
                <div class="flex justify-between items-center pt-4 border-t border-slate-100 mt-6">
                    <button id="btn-novo-servico" onclick="criarCardServicoDOM()" class="bg-slate-800 hover:bg-slate-900 text-white text-xs font-bold uppercase tracking-wider px-4 py-2.5 rounded-lg shadow-sm cursor-pointer hidden transition-all">+ Adicionar Novo Serviço</button>
                    <button id="btn-salvar-servicos" onclick="salvarServicosObra()" class="bg-blue-700 hover:bg-blue-800 text-white font-bold px-6 py-2.5 rounded-lg text-xs uppercase tracking-wider shadow-md transition cursor-pointer hidden">Salvar Lançamentos</button>
                </div>
            </div>
        </section>

        <section id="aba-medicao" class="space-y-6 hidden">
            <div class="bg-white rounded-xl shadow-sm border border-slate-200 p-6">
                <div class="grid grid-cols-1 md:grid-cols-3 gap-4 border-b border-slate-200 pb-6 mb-6 items-end">
                    <div>
                        <label class="block text-xs font-bold uppercase text-slate-500 mb-1">Selecione o Contrato</label>
                        <select id="select-obra-medicao" onchange="configurarFiltrosMesesMedicao(); carregarPlanilhaMedicao();" class="w-full bg-slate-50 border border-slate-200 rounded-lg p-2.5 text-sm font-bold text-slate-900 outline-none focus:ring-2 focus:ring-blue-600">
                            <option value="">-- Escolha uma Obra --</option>
                        </select>
                    </div>
                    <div>
                        <label class="block text-xs font-bold uppercase text-slate-500 mb-1">Mês de Referência Histórico</label>
                        <select id="select-mes-medicao-historico" onchange="carregarPlanilhaMedicao()" class="w-full bg-slate-50 border border-slate-200 rounded-lg p-2.5 text-sm font-bold text-slate-900 outline-none focus:ring-2 focus:ring-blue-600">
                            <option value="">-- Selecione uma Obra Primeiro --</option>
                        </select>
                    </div>
                    <div class="flex justify-end no-print">
                        <button onclick="window.print()" class="w-full bg-blue-800 hover:bg-blue-900 text-white font-bold uppercase tracking-wider p-2.5 rounded-lg text-xs shadow-sm cursor-pointer transition">🖨️ Imprimir Medição Atual</button>
                    </div>
                </div>
                <div id="painel-calculos" class="hidden space-y-6">
                    <div class="overflow-x-auto rounded-lg border border-slate-200">
                        <table class="w-full text-left border-collapse overflow-hidden">
                            <thead>
                                <tr class="bg-blue-900 text-white text-xs uppercase tracking-wider font-bold">
                                    <th class="p-3 border-r border-blue-800 w-1/4">Serviço</th>
                                    <th class="p-3 border-r border-blue-800 w-1/4">Subdivisão / Etapa</th>
                                    <th class="p-3 text-right border-r border-blue-800 w-32 bg-blue-950/40">Metragem (m²)</th>
                                    <th class="p-3 text-right border-r border-blue-800 w-32 text-blue-100">Preço m²</th>
                                    <th class="p-3 text-right bg-slate-900 w-44">Subtotal Orçado</th>
                                </tr>
                            </thead>
                            <tbody id="corpo-tabela-medicao" class="text-sm divide-y divide-slate-200"></tbody>
                        </table>
                    </div>
                    <div class="grid grid-cols-1 md:grid-cols-2 gap-4 bg-slate-50 p-5 rounded-xl border border-slate-200">
                        <div>
                            <span class="block text-xs font-bold text-slate-400 uppercase tracking-wider">TOTAL CONTRATADO</span>
                            <span id="tot-meta-reais" class="text-xl font-black text-slate-900">R$ 0,00</span>
                        </div>
                        <div class="border-t md:border-t-0 md:border-l border-slate-200 md:pl-6">
                            <span class="block text-xs font-bold text-blue-600 uppercase tracking-wider">MEDIÇÃO DO MÊS SELECIONADO</span>
                            <span id="tot-medido-reais" class="text-xl font-black text-blue-800">R$ 0,00</span>
                        </div>
                    </div>
                    <div class="pt-16 grid grid-cols-2 gap-12 text-center text-xs text-slate-600 mt-12 border-t border-dashed border-slate-200">
                        <div>
                            <div class="w-full border-t border-slate-300 mx-auto max-w-xs mb-1.5"></div>
                            <p class="font-bold text-slate-800">Responsável Técnico / Engenharia</p>
                            <p class="text-[10px] text-slate-400 uppercase tracking-wider">Passold Sistemas de Fachada</p>
                        </div>
                        <div>
                            <div class="w-full border-t border-slate-300 mx-auto max-w-xs mb-1.5"></div>
                            <p class="font-bold text-slate-800">Fiscalização / Aprovação do Cliente</p>
                            <p class="text-[10px] text-slate-400">Data: ____/____/_______</p>
                        </div>
                    </div>
                </div>
                <div id="aviso-selecao" class="text-center py-12 text-slate-400 text-sm">Selecione um Contrato e um Mês correspondente para abrir a folha operacional consolidada.</div>
            </div>
        </section>

        <section id="aba-relatorios" class="space-y-6 hidden">
            <div class="bg-white rounded-xl shadow-sm border border-slate-200 p-6">
                <div class="grid grid-cols-1 md:grid-cols-4 gap-4 border-b border-slate-200 pb-6 mb-6 items-end">
                    <div>
                        <label class="block text-xs font-bold uppercase text-slate-500 mb-1">Selecione o Contrato</label>
                        <select id="select-obra-relatorios" onchange="configurarFiltrosPeriodo(); configurarFiltroServicosDashboard(); gerarDashboardsEComparativosGlobal();" class="w-full bg-slate-50 border border-slate-200 rounded-lg p-2.5 text-sm font-bold text-slate-900 outline-none focus:ring-2 focus:ring-blue-600">
                            <option value="">-- Escolha uma Obra --</option>
                        </select>
                    </div>
                    <div class="no-print">
                        <label class="block text-xs font-bold uppercase text-slate-500 mb-1">Filtrar por Serviço</label>
                        <select id="select-servico-dashboard" onchange="gerarDashboardsEComparativosGlobal();" class="w-full bg-slate-50 border border-slate-200 rounded-lg p-2.5 text-sm font-bold text-slate-900 outline-none focus:ring-2 focus:ring-blue-600">
                            <option value="">Todos os Serviços</option>
                        </select>
                    </div>
                    <div class="no-print">
                        <label class="block text-xs font-bold uppercase text-slate-500 mb-1">Mês Inicial</label>
                        <select id="select-mes-inicial" onchange="gerarDashboardsEComparativosGlobal();" class="w-full bg-slate-50 border border-slate-200 rounded-lg p-2.5 text-sm font-semibold text-slate-800 outline-none focus:ring-2 focus:ring-blue-600">
                            <option value="">-- Selecione a Obra --</option>
                        </select>
                    </div>
                    <div class="no-print">
                        <label class="block text-xs font-bold uppercase text-slate-500 mb-1">Mês Final</label>
                        <select id="select-mes-final" onchange="gerarDashboardsEComparativosGlobal();" class="w-full bg-slate-50 border border-slate-200 rounded-lg p-2.5 text-sm font-semibold text-slate-800 outline-none focus:ring-2 focus:ring-blue-600">
                            <option value="">-- Selecione a Obra --</option>
                        </select>
                    </div>
                </div>
                <div id="painel-vazio-relatorios" class="text-center py-12 text-slate-400 text-sm">Selecione um contrato com históricos salvos para renderizar a evolução e matrizes gráficas.</div>
                <div id="dashboard-visual" class="hidden grid grid-cols-1 md:grid-cols-2 gap-6 mb-6">
                    <div class="bg-slate-50 p-4 border border-slate-200 rounded-xl">
                        <h4 class="text-xs font-bold text-slate-700 uppercase tracking-wider mb-4 text-center">Evolução Cronológica de Medições</h4>
                        <div class="h-64 flex items-center justify-center"><canvas id="chartEvolucao"></canvas></div>
                    </div>
                    <div class="bg-slate-50 p-4 border border-slate-200 rounded-xl">
                        <h4 id="titulo-grafico-distribuicao" class="text-xs font-bold text-slate-700 uppercase tracking-wider mb-4 text-center">Distribuição Física Financeira (%)</h4>
                        <div class="h-64 flex items-center justify-center"><canvas id="chartDistribuicao"></canvas></div>
                    </div>
                </div>
                <div id="painel-tabela-comparativa" class="hidden space-y-6">
                    <h3 class="text-sm font-bold uppercase tracking-wider text-slate-900 border-l-4 border-blue-800 pl-2">Painel de Evolução Cronológica das Medições</h3>
                    <div class="overflow-x-auto rounded-lg border border-slate-200">
                        <table id="tabela-evolucao-global" class="w-full text-left border-collapse">
                            <thead id="head-tabela-comparativa" class="bg-slate-800 text-white text-xs uppercase tracking-wider font-semibold"></thead>
                            <tbody id="corpo-tabela-comparativa" class="text-sm divide-y divide-slate-200 bg-white"></tbody>
                            <tfoot id="foot-tabela-comparativa" class="bg-slate-100 text-slate-900 font-bold border-t-2 border-slate-300 text-right"></tfoot>
                        </table>
                    </div>
                    <div class="bg-slate-900 text-white p-5 rounded-xl border border-slate-800 flex flex-col md:flex-row md:items-center justify-between gap-6">
                        <div class="space-y-1">
                            <span class="block text-xs font-bold text-slate-400 uppercase tracking-wider">Dedução de Saldo Global</span>
                            <div class="text-xs md:text-sm text-slate-300 flex flex-wrap gap-2 items-center">
                                <span>Contrato Base: <strong id="calc-txt-contrato" class="text-white font-bold">R$ 0,00</strong></span>
                                <span class="text-slate-600 font-bold">−</span>
                                <span>Medido no Período: <strong id="calc-txt-medicoes" class="text-blue-400 font-bold">R$ 0,00</strong></span>
                            </div>
                        </div>
                        <div class="bg-slate-800 px-6 py-3 rounded-lg border border-slate-700/60 flex flex-col items-start md:items-end min-w-[240px]">
                            <span class="text-[10px] font-bold text-cyan-400 uppercase tracking-wider">Saldo Remanescente Total</span>
                            <span id="calc-txt-saldo-restante" class="text-xl md:text-2xl font-black text-cyan-400 tracking-tight">R$ 0,00</span>
                        </div>
                    </div>
                </div>
            </div>
        </section>
    </main>

    <script>
        let OBRAS = JSON.parse(localStorage.getItem('passold_medicao_v1')) || [];
        let chartLineInstance = null;
        let chartPieInstance = null;

        function mudarAba(idAba) {
            ['aba-cadastro','aba-servicos','aba-medicao','aba-relatorios'].forEach(id => document.getElementById(id).classList.add('hidden'));
            ['btn-cadastro','btn-servicos','btn-medicao','btn-relatorios'].forEach(id => document.getElementById(id).classList.remove('tab-active'));
            document.getElementById(idAba).classList.remove('hidden');
            const btnMap = {'aba-cadastro':'btn-cadastro','aba-servicos':'btn-servicos','aba-medicao':'btn-medicao','aba-relatorios':'btn-relatorios'};
            document.getElementById(btnMap[idAba]).classList.add('tab-active');
            if(idAba==='aba-cadastro') renderizarCardsObras();
            if(idAba==='aba-servicos'){atualizarSelectObras('select-obra-servicos');selecionarObraServicos();}
            if(idAba==='aba-medicao'){atualizarSelectObras('select-obra-medicao');configuterFiltrosMesesMedicaoPadrao();}
            if(idAba==='aba-relatorios'){atualizarSelectObras('select-obra-relatorios');configurarFiltrosPeriodo();configurarFiltroServicosDashboard();gerarDashboardsEComparativosGlobal();}
        }

        function salvarObraBase() {
            const nome = document.getElementById('cad-nome-obra').value.trim();
            const valorM2Geral = parseFloat(document.getElementById('cad-valor-m2').value)||0;
            const metragemGeral = parseFloat(document.getElementById('cad-metragem-geral').value)||0;
            if(!nome||valorM2Geral<=0||metragemGeral<=0) return alert("Preencha todas as especificações da obra.");
            OBRAS.push({id:'obra_'+Date.now(),nome,valorM2Global:valorM2Geral,metragemGeral,servicos:[],historicoMedicoes:{}});
            salvarDados();
            document.getElementById('cad-nome-obra').value='';
            document.getElementById('cad-valor-m2').value='';
            document.getElementById('cad-metragem-geral').value='';
            renderizarCardsObras();
        }

        function renderizarCardsObras() {
            const container = document.getElementById('grid-obras');
            container.innerHTML='';
            if(OBRAS.length===0){container.innerHTML='<p class="text-sm text-slate-400 col-span-3">Nenhum contrato arquivado.</p>';return;}
            OBRAS.forEach(obra=>{
                const total=obra.valorM2Global*obra.metragemGeral;
                const card=document.createElement('div');
                card.className="bg-white p-4 rounded-xl border border-slate-200 flex flex-col justify-between shadow-xs";
                card.innerHTML=`<div><h4 class="font-bold text-slate-900 text-base mb-2 border-b border-slate-100 pb-1">${obra.nome}</h4><div class="text-xs text-slate-600 space-y-1.5"><div class="flex justify-between"><span>Metragem Geral:</span><strong>${obra.metragemGeral.toFixed(2)} m²</strong></div><div class="flex justify-between"><span>Valor Limite m²:</span><strong>R$ ${obra.valorM2Global.toFixed(2)}</strong></div><div class="flex justify-between border-t border-slate-100 pt-1.5 font-bold text-blue-800 text-xs uppercase"><span>TOTAL CONTRATADO:</span><span>${total.toLocaleString('pt-BR',{style:'currency',currency:'BRL'})}</span></div></div></div><div class="mt-4 flex justify-end border-t border-slate-50 pt-2"><button onclick="excluirObra('${obra.id}')" class="text-[11px] font-bold uppercase tracking-wider text-red-500 hover:text-red-700 cursor-pointer">✕ Excluir</button></div>`;
                container.appendChild(card);
            });
        }

        function excluirObra(id){if(confirm("Deseja deletar permanentemente esta obra?")){OBRAS=OBRAS.filter(o=>o.id!==id);salvarDados();renderizarCardsObras();}}
        function atualizarSelectObras(selectId){const s=document.getElementById(selectId);const a=s.value;s.innerHTML='<option value="">-- Escolha uma Obra --</option>';OBRAS.forEach(o=>{s.innerHTML+=`<option value="${o.id}">${o.nome}</option>`;});s.value=a;}

        function selecionarObraServicos(){
            const idObra=document.getElementById('select-obra-servicos').value;
            const container=document.getElementById('container-lista-servicos');
            const infoTeto=document.getElementById('info-teto-obra-ativa');
            container.innerHTML='';infoTeto.innerText='';
            if(!idObra){document.getElementById('btn-novo-servico').classList.add('hidden');document.getElementById('btn-salvar-servicos').classList.add('hidden');document.getElementById('aviso-selecao-servicos').classList.remove('hidden');return;}
            document.getElementById('btn-novo-servico').classList.remove('hidden');document.getElementById('btn-salvar-servicos').classList.remove('hidden');document.getElementById('aviso-selecao-servicos').classList.add('hidden');
            const obra=OBRAS.find(o=>o.id===idObra);
            infoTeto.innerHTML=`Teto Obra Base: <strong class="text-blue-800">R$ ${obra.valorM2Global.toFixed(2)}</strong>`;
            if(obra.servicos&&obra.servicos.length>0){obra.servicos.forEach(srv=>criarCardServicoDOM(srv));}else{criarCardServicoDOM();}
            recalcularTudoServicosTab();
        }

        function criarCardServicoDOM(dadosSrv=null){
            const container=document.getElementById('container-lista-servicos');
            const srvDiv=document.createElement('div');
            srvDiv.className="bg-slate-50/70 p-5 rounded-xl border border-slate-200 space-y-4 card-servico-item";
            srvDiv.dataset.srvId=dadosSrv?dadosSrv.id:'srv_'+Math.random().toString(36).substr(2,5);
            srvDiv.innerHTML=`<div class="grid grid-cols-1 md:grid-cols-3 gap-4 border-b border-slate-200 pb-4 items-end"><div><label class="block text-xs font-bold text-slate-500 uppercase mb-1">Nome do Serviço</label><input type="text" value="${dadosSrv?dadosSrv.nome:''}" placeholder="Ex: Pintura" class="w-full bg-white border border-slate-200 rounded-lg p-2 text-sm font-semibold text-slate-800 input-nome-servico outline-none focus:ring-2 focus:ring-blue-600"></div><div><label class="block text-xs font-bold text-slate-500 uppercase mb-1">Valor m² Próprio do Serviço (R$)</label><input type="number" value="${dadosSrv?dadosSrv.valorM2Servico:''}" oninput="recalcularTudoServicosTab()" class="w-full bg-white border border-slate-200 rounded-lg p-2 text-sm font-bold text-blue-900 input-val-m2-servico outline-none focus:ring-2 focus:ring-blue-600"></div><div class="flex justify-end"><button onclick="this.closest('.card-servico-item').remove();recalcularTudoServicosTab();" class="text-red-500 hover:text-red-700 text-xs font-bold uppercase tracking-wide cursor-pointer mb-2">✕ Remover Serviço</button></div></div><div><div class="overflow-x-auto rounded-lg border border-slate-200"><table class="w-full text-left border-collapse text-sm bg-white"><thead><tr class="bg-slate-200/60 text-xs text-slate-600 uppercase border-b border-slate-300 font-bold"><th class="p-2">Nome da Subdivisão</th><th class="p-2 w-32 text-right">Metragem (m²)</th><th class="p-2 w-28 text-right">% da Subdivisão</th><th class="p-2 w-32 text-right text-blue-800">R$/m² Local</th><th class="p-2 w-36 text-right text-slate-900">Subtotal Orçado</th><th class="p-2 w-12 text-center">Ação</th></tr></thead><tbody class="container-subdivisoes divide-y divide-slate-200"></tbody></table></div><button onclick="adicionarLinhaSubdivisaoDOM(this.closest('.card-servico-item').querySelector('.container-subdivisoes'))" class="mt-3 bg-white hover:bg-slate-50 text-slate-700 text-xs font-bold uppercase tracking-wider px-3 py-1.5 border border-slate-300 rounded shadow-xs cursor-pointer">+ Adicionar Linha de Subdivisão</button></div>`;
            container.appendChild(srvDiv);
            const tbody=srvDiv.querySelector('.container-subdivisoes');
            if(dadosSrv&&dadosSrv.subdivisoes){dadosSrv.subdivisoes.forEach(sub=>adicionarLinhaSubdivisaoDOM(tbody,sub));}else{adicionarLinhaSubdivisaoDOM(tbody);}
        }

        function adicionarLinhaSubdivisaoDOM(tbody,dadosSub=null){
            const tr=document.createElement('tr');
            tr.className="linha-subdivisao-item";
            tr.dataset.subId=dadosSub?dadosSub.id:'sub_'+Math.random().toString(36).substr(2,5);
            tr.innerHTML=`<td class="p-2"><input type="text" value="${dadosSub?dadosSub.nome:''}" class="w-full bg-white border border-slate-200 rounded p-1.5 text-xs outline-none focus:ring-1 focus:ring-blue-600 input-sub-nome"></td><td class="p-2"><input type="number" value="${dadosSub?dadosSub.m2:''}" oninput="recalcularTudoServicosTab()" class="w-full bg-white border border-slate-200 rounded p-1.5 text-xs text-right input-sub-m2 focus:ring-1 focus:ring-blue-600"></td><td class="p-2"><input type="number" value="${dadosSub?dadosSub.percentual:''}" oninput="recalcularTudoServicosTab()" class="w-full bg-white border border-slate-200 rounded p-1.5 text-xs text-right input-sub-pct focus:ring-1 focus:ring-blue-600"></td><td class="p-2 text-right text-blue-800 font-bold text-xs pr-3 span-sub-val-m2">R$ 0,00</td><td class="p-2 text-right text-slate-900 font-black text-xs pr-3 span-sub-total">R$ 0,00</td><td class="p-2 text-center"><button onclick="this.closest('tr').remove();recalcularTudoServicosTab();" class="text-red-500 font-black text-lg hover:text-red-700">&times;</button></td>`;
            tbody.appendChild(tr);
            recalcularTudoServicosTab();
        }

        function recalcularTudoServicosTab(){
            const idObra=document.getElementById('select-obra-servicos').value;
            if(!idObra)return;
            const obra=OBRAS.find(o=>o.id===idObra);
            const valM2TetoObra=obra.valorM2Global;
            document.querySelectorAll('.card-servico-item').forEach(card=>{
                const inputValM2Servico=card.querySelector('.input-val-m2-servico');
                let valM2Servico=parseFloat(inputValM2Servico.value)||0;
                if(valM2Servico>valM2TetoObra){inputValM2Servico.classList.add('border-red-500','bg-red-50','text-red-700');valM2Servico=valM2TetoObra;}
                else{inputValM2Servico.classList.remove('border-red-500','bg-red-50','text-red-700');}
                card.querySelectorAll('.linha-subdivisao-item').forEach(tr=>{
                    const m2=parseFloat(tr.querySelector('.input-sub-m2').value)||0;
                    const pct=parseFloat(tr.querySelector('.input-sub-pct').value)||0;
                    const valM2CalcSub=valM2Servico*(pct/100);
                    const totalCalcSub=m2*valM2CalcSub;
                    tr.querySelector('.span-sub-val-m2').innerText=valM2CalcSub.toLocaleString('pt-BR',{style:'currency',currency:'BRL'});
                    tr.querySelector('.span-sub-total').innerText=totalCalcSub.toLocaleString('pt-BR',{style:'currency',currency:'BRL'});
                });
            });
        }

        function salvarServicosObra(){
            const idObra=document.getElementById('select-obra-servicos').value;
            const periodoReferencia=document.getElementById('mes-servicos-referencia').value;
            if(!idObra||!periodoReferencia)return alert("Selecione a Obra Alvo e preencha o Período de Referência.");
            const idxObra=OBRAS.findIndex(o=>o.id===idObra);
            let novosServicos=[];let valido=true;let totalMedidoCalculadoSrv=0;
            document.querySelectorAll('.card-servico-item').forEach(card=>{
                const nomeServico=card.querySelector('.input-nome-servico').value.trim();
                const valorM2Servico=parseFloat(card.querySelector('.input-val-m2-servico').value)||0;
                if(!nomeServico||valorM2Servico<=0)valido=false;
                let subdivisoes=[];
                card.querySelectorAll('.linha-subdivisao-item').forEach(lin=>{
                    const subM2=parseFloat(lin.querySelector('.input-sub-m2').value)||0;
                    const subPct=parseFloat(lin.querySelector('.input-sub-pct').value)||0;
                    subdivisoes.push({id:lin.dataset.subId,nome:lin.querySelector('.input-sub-nome').value.trim(),m2:subM2,percentual:subPct});
                    totalMedidoCalculadoSrv+=(subM2*(valorM2Servico*(subPct/100)));
                });
                novosServicos.push({id:card.dataset.srvId,nome:nomeServico,valorM2Servico,subdivisoes});
            });
            if(!valido)return alert("Verifique as informações dos serviços e valores.");
            OBRAS[idxObra].servicos=novosServicos;
            if(!OBRAS[idxObra].historicoMedicoes)OBRAS[idxObra].historicoMedicoes={};
            OBRAS[idxObra].historicoMedicoes[periodoReferencia]={totalMedidoMesa:totalMedidoCalculadoSrv,snapshotServicos:JSON.parse(JSON.stringify(novosServicos))};
            salvarDados();
            alert(`Medição do mês (${periodoReferencia.split('-')[1]}/${periodoReferencia.split('-')[0]}) salva com sucesso!`);
            document.getElementById('select-obra-medicao').value=idObra;
            configurarFiltrosMesesMedicao(periodoReferencia);
            mudarAba('aba-medicao');
        }

        function configuterFiltrosMesesMedicaoPadrao(){configurarFiltrosMesesMedicao();carregarPlanilhaMedicao();}

        function configurarFiltrosMesesMedicao(mesSelecionarForcado=null){
            const idObra=document.getElementById('select-obra-medicao').value;
            const selectMes=document.getElementById('select-mes-medicao-historico');
            const valorAtual=selectMes.value;
            selectMes.innerHTML='';
            if(!idObra){selectMes.innerHTML='<option value="">-- Selecione uma Obra Primeiro --</option>';return;}
            const obra=OBRAS.find(o=>o.id===idObra);
            if(obra.historicoMedicoes&&Object.keys(obra.historicoMedicoes).length>0){
                const mesesSorted=Object.keys(obra.historicoMedicoes).sort();
                mesesSorted.forEach(m=>{const[ano,mes]=m.split('-');selectMes.innerHTML+=`<option value="${m}">${mes}/${ano}</option>`;});
                if(mesSelecionarForcado&&mesesSorted.includes(mesSelecionarForcado)){selectMes.value=mesSelecionarForcado;}
                else if(mesesSorted.includes(valorAtual)){selectMes.value=valorAtual;}
                else{selectMes.value=mesesSorted[mesesSorted.length-1];}
            }else{selectMes.innerHTML='<option value="">Sem históricos salvos nesta obra</option>';}
        }

        function carregarPlanilhaMedicao(){
            const idObra=document.getElementById('select-obra-medicao').value;
            const mesSelecionado=document.getElementById('select-mes-medicao-historico').value;
            if(!idObra||!mesSelecionado){document.getElementById('painel-calculos').classList.add('hidden');document.getElementById('aviso-selecao').classList.remove('hidden');return;}
            document.getElementById('painel-calculos').classList.remove('hidden');document.getElementById('aviso-selecao').classList.add('hidden');
            const obra=OBRAS.find(o=>o.id===idObra);
            const corpo=document.getElementById('corpo-tabela-medicao');corpo.innerHTML='';
            const totalContratado=(obra.valorM2Global||0)*(obra.metragemGeral||0);
            const historicoDoMes=obra.historicoMedicoes[mesSelecionado];
            const listaServicosExibir=historicoDoMes?historicoDoMes.snapshotServicos:[];
            let medicaoDoMesAcumulada=historicoDoMes?historicoDoMes.totalMedidoMesa:0;
            if(listaServicosExibir.length===0){corpo.innerHTML='<tr><td colspan="5" class="p-4 text-center text-slate-400">Nenhum registro encontrado.</td></tr>';document.getElementById('tot-meta-reais').innerText=totalContratado.toLocaleString('pt-BR',{style:'currency',currency:'BRL'});document.getElementById('tot-medido-reais').innerText="R$ 0,00";return;}
            listaServicosExibir.forEach(servico=>{
                const qtdSubdivisoes=servico.subdivisoes.length;
                servico.subdivisoes.forEach((sub,index)=>{
                    const precoM2Sub=servico.valorM2Servico*(sub.percentual/100);
                    const subtotalOrcadoSubdivisao=sub.m2*precoM2Sub;
                    const tr=document.createElement('tr');
                    tr.className="bg-white border-b border-slate-200";
                    let tdServicoHtml=index===0?`<td rowspan="${qtdSubdivisoes}" class="p-3 border-r border-slate-200 align-middle font-bold text-slate-900 bg-white">${servico.nome}</td>`:'';
                    tr.innerHTML=`${tdServicoHtml}<td class="p-3 border-r border-slate-200 text-slate-700"><span class="block text-xs font-semibold text-slate-600 bg-slate-100 px-1.5 py-0.5 rounded w-max">${sub.nome} (${sub.percentual}%)</span></td><td class="p-3 text-right font-bold text-slate-700 bg-slate-50/50 border-r border-slate-200">${sub.m2.toFixed(2)} m²</td><td class="p-3 text-right border-r border-slate-200 text-slate-500 font-medium">R$ ${precoM2Sub.toFixed(2)}</td><td class="p-3 text-right font-bold text-slate-950">${subtotalOrcadoSubdivisao.toLocaleString('pt-BR',{style:'currency',currency:'BRL'})}</td>`;
                    corpo.appendChild(tr);
                });
            });
            document.getElementById('tot-meta-reais').innerText=totalContratado.toLocaleString('pt-BR',{style:'currency',currency:'BRL'});
            document.getElementById('tot-medido-reais').innerText=medicaoDoMesAcumulada.toLocaleString('pt-BR',{style:'currency',currency:'BRL'});
        }

        function configurarFiltrosPeriodo(){
            const idObra=document.getElementById('select-obra-relatorios').value;
            const sI=document.getElementById('select-mes-inicial');const sF=document.getElementById('select-mes-final');
            sI.innerHTML='';sF.innerHTML='';
            if(!idObra){sI.innerHTML='<option value="">-- Selecione a Obra --</option>';sF.innerHTML='<option value="">-- Selecione a Obra --</option>';return;}
            const obra=OBRAS.find(o=>o.id===idObra);
            const meses=Object.keys(obra.historicoMedicoes||{}).sort();
            if(meses.length===0){sI.innerHTML='<option value="">Sem históricos</option>';sF.innerHTML='<option value="">Sem históricos</option>';return;}
            meses.forEach(m=>{const[ano,mes]=m.split('-');sI.innerHTML+=`<option value="${m}">${mes}/${ano}</option>`;sF.innerHTML+=`<option value="${m}">${mes}/${ano}</option>`;});
            sI.value=meses[0];sF.value=meses[meses.length-1];
        }

        function configurarFiltroServicosDashboard(){
            const idObra=document.getElementById('select-obra-relatorios').value;
            const s=document.getElementById('select-servico-dashboard');
            s.innerHTML='<option value="">Todos os Serviços</option>';
            if(!idObra)return;
            const obra=OBRAS.find(o=>o.id===idObra);
            if(obra&&obra.servicos)obra.servicos.forEach(sv=>{s.innerHTML+=`<option value="${sv.nome}">${sv.nome}</option>`;});
        }

        function gerarDashboardsEComparativosGlobal(){
            const idObra=document.getElementById('select-obra-relatorios').value;
            const servicoFiltrado=document.getElementById('select-servico-dashboard').value;
            const painelVazio=document.getElementById('painel-vazio-relatorios');
            const dashVisual=document.getElementById('dashboard-visual');
            const painelTabela=document.getElementById('painel-tabela-comparativa');
            if(!idObra){painelVazio.classList.remove('hidden');dashVisual.classList.add('hidden');painelTabela.classList.add('hidden');return;}
            const obra=OBRAS.find(o=>o.id===idObra);
            const todosMeses=Object.keys(obra.historicoMedicoes||{}).sort();
            if(todosMeses.length===0){painelVazio.innerHTML="Esta obra ainda não possui históricos de medições gravados.";painelVazio.classList.remove('hidden');dashVisual.classList.add('hidden');painelTabela.classList.add('hidden');return;}
            const mesInicial=document.getElementById('select-mes-inicial').value;
            const mesFinal=document.getElementById('select-mes-final').value;
            let mesesDisponiveis=todosMeses.filter(m=>m>=mesInicial&&m<=mesFinal);
            if(mesesDisponiveis.length===0){painelVazio.innerHTML="Nenhum registro encontrado para o intervalo selecionado.";painelVazio.classList.remove('hidden');dashVisual.classList.add('hidden');painelTabela.classList.add('hidden');return;}
            painelVazio.classList.add('hidden');dashVisual.classList.remove('hidden');painelTabela.classList.remove('hidden');
            const thead=document.getElementById('head-tabela-comparativa');
            let headerHtml=`<tr><th class="p-3 border-r border-slate-600">Serviço</th><th class="p-3 border-r border-slate-600">Subdivisão</th>`;
            mesesDisponiveis.forEach(m=>{const[ano,mes]=m.split('-');headerHtml+=`<th class="p-3 text-right border-r border-slate-600 bg-blue-900/90">${mes}/${ano}</th>`;});
            headerHtml+=`<th class="p-3 text-right bg-emerald-900 text-white">Acumulado Período</th></tr>`;
            thead.innerHTML=headerHtml;
            let chavesUnicas=new Set();let mapeamentoLinhas={};
            obra.servicos.forEach(s=>{
                if(servicoFiltrado&&s.nome!==servicoFiltrado)return;
                s.subdivisoes.forEach(sub=>{const chave=`${s.nome}|||${sub.nome}`;chavesUnicas.add(chave);mapeamentoLinhas[chave]={servicoNome:s.nome,subdivisaoNome:sub.nome,valoresMensais:{}};});
            });
            mesesDisponiveis.forEach(m=>{
                const snapshot=obra.historicoMedicoes[m].snapshotServicos||[];
                snapshot.forEach(s=>{
                    if(servicoFiltrado&&s.nome!==servicoFiltrado)return;
                    s.subdivisoes.forEach(sub=>{
                        const chave=`${s.nome}|||${sub.nome}`;
                        chavesUnicas.add(chave);
                        const precoM2Sub=s.valorM2Servico*(sub.percentual/100);
                        const valorMedidoNoMes=sub.m2*precoM2Sub;
                        if(!mapeamentoLinhas[chave])mapeamentoLinhas[chave]={servicoNome:s.nome,subdivisaoNome:sub.nome,valoresMensais:{}};
                        mapeamentoLinhas[chave].valoresMensais[m]=valorMedidoNoMes;
                    });
                });
            });
            const corpo=document.getElementById('corpo-tabela-comparativa');corpo.innerHTML='';
            const chavesOrdenadas=Array.from(chavesUnicas).sort();
            let contagemServicos={};chavesOrdenadas.forEach(ch=>{const sNome=mapeamentoLinhas[ch].servicoNome;contagemServicos[sNome]=(contagemServicos[sNome]||0)+1;});
            let servicosRenderizados={};let totaisColunasMensais={};mesesDisponiveis.forEach(m=>totaisColunasMensais[m]=0);let totalGeralAcumulado=0;
            chavesOrdenadas.forEach(chave=>{
                const item=mapeamentoLinhas[chave];
                const tr=document.createElement('tr');tr.className="bg-white hover:bg-slate-50 border-b border-slate-100";
                let tdServicoHtml='';
                if(!servicosRenderizados[item.servicoNome]){const totalLinhas=contagemServicos[item.servicoNome];tdServicoHtml=`<td rowspan="${totalLinhas}" class="p-3 border-r border-slate-200 align-middle font-bold text-slate-900 bg-white">${item.servicoNome}</td>`;servicosRenderizados[item.servicoNome]=true;}
                let acumuladoLinha=0;let colunasMesesHtml='';
                mesesDisponiveis.forEach(m=>{const valMes=item.valoresMensais[m]||0;acumuladoLinha+=valMes;totaisColunasMensais[m]+=valMes;colunasMesesHtml+=`<td class="p-3 text-right border-r border-slate-200 font-semibold text-slate-600">${valMes>0?valMes.toLocaleString('pt-BR',{style:'currency',currency:'BRL'}):'−'}</td>`;});
                totalGeralAcumulado+=acumuladoLinha;
                tr.innerHTML=`${tdServicoHtml}<td class="p-3 font-medium border-r border-slate-200 text-slate-700">${item.subdivisaoNome}</td>${colunasMesesHtml}<td class="p-3 text-right font-bold bg-emerald-50 text-emerald-800">${acumuladoLinha.toLocaleString('pt-BR',{style:'currency',currency:'BRL'})}</td>`;
                corpo.appendChild(tr);
            });
            const tfoot=document.getElementById('foot-tabela-comparativa');
            let footHtml=`<tr class="bg-slate-200 font-black text-slate-950"><td colspan="2" class="p-3 border-r border-slate-300 uppercase tracking-wider text-left text-xs">Totalização do Período:</td>`;
            mesesDisponiveis.forEach(m=>{footHtml+=`<td class="p-3 border-r border-slate-300 text-right text-blue-950 bg-blue-100/60">${totaisColunasMensais[m].toLocaleString('pt-BR',{style:'currency',currency:'BRL'})}</td>`;});
            footHtml+=`<td class="p-3 text-right bg-emerald-200 text-emerald-950">${totalGeralAcumulado.toLocaleString('pt-BR',{style:'currency',currency:'BRL'})}</td></tr>`;
            tfoot.innerHTML=footHtml;
            const totalContratadoGlobal=obra.valorM2Global*obra.metragemGeral;
            let totalMedidoAcumuladoTudo=0;
            Object.keys(obra.historicoMedicoes).forEach(mesKey=>{let snapshot=obra.historicoMedicoes[mesKey].snapshotServicos||[];snapshot.forEach(s=>{s.subdivisoes.forEach(sub=>{totalMedidoAcumuladoTudo+=sub.m2*(s.valorM2Servico*(sub.percentual/100));});});});
            document.getElementById('calc-txt-contrato').innerText=totalContratadoGlobal.toLocaleString('pt-BR',{style:'currency',currency:'BRL'});
            document.getElementById('calc-txt-medicoes').innerText=totalGeralAcumulado.toLocaleString('pt-BR',{style:'currency',currency:'BRL'});
            document.getElementById('calc-txt-saldo-restante').innerText=(totalContratadoGlobal-totalMedidoAcumuladoTudo).toLocaleString('pt-BR',{style:'currency',currency:'BRL'});
            renderizarGraficosObra(obra,mesesDisponiveis,servicoFiltrado);
        }

        function renderizarGraficosObra(obra,mesesFiltrados,servicoFiltrado=""){
            const valoresHistorico=mesesFiltrados.map(m=>{
                if(!servicoFiltrado)return obra.historicoMedicoes[m].totalMedidoMesa;
                let totalMesSrv=0;
                const snapshot=obra.historicoMedicoes[m].snapshotServicos||[];
                snapshot.forEach(s=>{if(s.nome===servicoFiltrado){s.subdivisoes.forEach(sub=>{totalMesSrv+=sub.m2*(s.valorM2Servico*(sub.percentual/100));});}});
                return totalMesSrv;
            });
            const labelsMesesFormatados=mesesFiltrados.map(m=>`${m.split('-')[1]}/${m.split('-')[0]}`);
            if(chartLineInstance)chartLineInstance.destroy();
            const ctxLine=document.getElementById('chartEvolucao').getContext('2d');
            chartLineInstance=new Chart(ctxLine,{type:'line',data:{labels:labelsMesesFormatados,datasets:[{label:servicoFiltrado?`${servicoFiltrado} (R$)`:'Produção do Mês (R$)',data:valoresHistorico,borderColor:'#1e3a8a',backgroundColor:'rgba(30,58,138,0.08)',borderWidth:3,fill:true,tension:0.25}]},options:{responsive:true,maintainAspectRatio:false}});
            let servicosLabels=[];let servicosValores=[];
            const tituloGrafico=document.getElementById('titulo-grafico-distribuicao');
            if(!servicoFiltrado){
                tituloGrafico.innerText="Distribuição Física Financeira por Serviço (%)";
                obra.servicos.forEach(s=>{
                    servicosLabels.push(s.nome);let totalAcumuladoServico=0;
                    mesesFiltrados.forEach(m=>{if(obra.historicoMedicoes[m]&&obra.historicoMedicoes[m].snapshotServicos){const srvM=obra.historicoMedicoes[m].snapshotServicos.find(srv=>srv.nome===s.nome||srv.id===s.id);if(srvM){srvM.subdivisoes.forEach(subM=>{const precoM2Sub=srvM.valorM2Servico*(subM.percentual/100);totalAcumuladoServico+=subM.m2*precoM2Sub;});}}});
                    servicosValores.push(totalAcumuladoServico);
                });
            }else{
                tituloGrafico.innerText=`Distribuição por Etapas: ${servicoFiltrado} (%)`;
                const srvBase=obra.servicos.find(s=>s.nome===servicoFiltrado);
                if(srvBase){srvBase.subdivisoes.forEach(sub=>{servicosLabels.push(sub.nome);let totalAcumuladoSub=0;mesesFiltrados.forEach(m=>{if(obra.historicoMedicoes[m]&&obra.historicoMedicoes[m].snapshotServicos){const srvM=obra.historicoMedicoes[m].snapshotServicos.find(srv=>srv.nome===servicoFiltrado);if(srvM){const subM=srvM.subdivisoes.find(sb=>sb.nome===sub.nome);if(subM){totalAcumuladoSub+=subM.m2*(srvM.valorM2Servico*(subM.percentual/100));}}}});servicosValores.push(totalAcumuladoSub);});}
            }
            if(chartPieInstance)chartPieInstance.destroy();
            const ctxPie=document.getElementById('chartDistribuicao').getContext('2d');
            chartPieInstance=new Chart(ctxPie,{type:'doughnut',data:{labels:servicosLabels,datasets:[{data:servicosValores,backgroundColor:['#1e293b','#1e3a8a','#0284c7','#0d9488','#b45309','#475569','#312e81']}]},options:{responsive:true,maintainAspectRatio:false}});
        }

        function salvarDados(){localStorage.setItem('passold_medicao_v1',JSON.stringify(OBRAS));}
        window.onload=function(){renderizarCardsObras();};
    </script>
</body>
</html>
            """, height=900, scrolling=True)

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
                            cursor = conn.cursor()
                            try:
                                cursor.execute("INSERT INTO usuarios (usuario, nome, setor, senha) VALUES (%s,%s,%s,%s)", (nu, nn, ns, hash_senha(np)))
                                conn.commit()
                                st.success(f"{nn} criado!")
                                time.sleep(0.5)
                                st.rerun()
                            except Exception as e:
                                st.error(f"Erro: {e}")
                            finally:
                                conn.close()

            conn = conectar_banco()
            df_u = pd.read_sql_query("SELECT id, usuario, nome, setor FROM usuarios ORDER BY id", conn)
            conn.close()
            st.dataframe(df_u, hide_index=True, use_container_width=True)

            if len(df_u) > 1:
                del_u = st.selectbox("Remover usuario:", df_u['usuario'].tolist())
                if del_u == 'master':
                    st.caption("Conta master nao pode ser removida.")
                else:
                    if st.button(f"Excluir {del_u}"):
                        conn = conectar_banco()
                        cursor = conn.cursor()
                        cursor.execute("DELETE FROM usuarios WHERE usuario=%s", (del_u,))
                        conn.commit()
                        conn.close()
                        st.toast("Removido!")
                        time.sleep(0.5)
                        st.rerun()

            st.markdown("---")
            st.markdown("### Reset Geral")
            st.warning("Remove TODOS os dados permanentemente.")
            if st.button("Confirmar limpeza total"):
                resetar_banco_dados_completo()
                st.toast("Resetado!")
                time.sleep(0.5)
                st.rerun()