
# ============================================================
#  APP.PY — GABMA Sistema Técnico (Versão Completa)
# ============================================================

import streamlit as st
import requests
import base64
import json
import os
import pandas as pd
from fpdf import FPDF
import unicodedata
import re


# -----------------------------------------
#     CONFIGURAÇÕES DE ACESSO (SECRETS)
# -----------------------------------------
try:
    GITHUB_TOKEN = st.secrets["GITHUB_TOKEN"]
    REPO_OWNER = st.secrets["REPO_OWNER"]
    REPO_NAME = st.secrets["REPO_NAME"]
except:
    st.error("Configure os Secrets (GITHUB_TOKEN, REPO_OWNER, REPO_NAME) no Streamlit Cloud.")
    st.stop()

FILE_PATH = "dados.json"
BRANCH = "main"

# -----------------------------------------
#     DESIGN — PALETA MICROSOFT/MV
# -----------------------------------------

PRIMARY_COLOR = "#1F497D"     # Azul Microsoft/MV
PRIMARY_LIGHT = "#E8EEF5"     # Azul clarinho
BG_LIGHT = "#F5F7FA"          # Fundo clean
GREY_BORDER = "#D9D9D9"
TEXT_DARK = "#2D2D2D"

# CSS GLOBAL
st.markdown(
    f"""
    <style>

        /* Fundo geral */
        body {{
            background-color: {BG_LIGHT};
        }}

        /* Títulos */
        .main-title {{
            font-size: 36px;
            font-weight: 700;
            color: {PRIMARY_COLOR};
            padding: 10px 0 20px 0;
        }}

        /* Cards corporativos */
        .card {{
            background: white;
            padding: 22px;
            border-radius: 12px;
            border: 1px solid {GREY_BORDER};
            box-shadow: 0 2px 5px rgba(0,0,0,0.05);
            margin-bottom: 22px;
        }}

        .card-title {{
            font-size: 22px;
            font-weight: 700;
            color: {PRIMARY_COLOR};
            margin-bottom: 12px;
        }}

        .info-line {{
            font-size: 15px;
            padding: 4px 0;
            color: {TEXT_DARK};
        }}
        .value {{
            font-weight: 600;
        }}

    </style>
    """,
    unsafe_allow_html=True
)

# -----------------------------------------
#     FUNÇÕES DO GITHUB – CRUD JSON
# -----------------------------------------
def buscar_dados_github():
    url = f"https://api.github.com/repos/{REPO_OWNER}/{REPO_NAME}/contents/{FILE_PATH}?ref={BRANCH}"
    headers = {"Authorization": f"token {GITHUB_TOKEN}"}
    response = requests.get(url, headers=headers)
    
    if response.status_code == 200:
        content = response.json()
        decoded = base64.b64decode(content['content']).decode('utf-8')
        return json.loads(decoded), content['sha']
    else:
        return [], None


def sanitize_text(text):
    if text is None:
        return ""
    text = str(text)
    text = unicodedata.normalize("NFKD", text)
    text = re.sub(r"[\u200B-\u200F\u202A-\u202E\u2060-\u206F]", "", text)
    text = re.sub(r"[\x00-\x08\x0B\x0C\x0E-\x1F\x7F]", "", text)
    return text.replace("\r", "")


def salvar_dados_github(novos_dados, sha):
    url = f"https://api.github.com/repos/{REPO_OWNER}/{REPO_NAME}/contents/{FILE_PATH}"
    headers = {"Authorization": f"token {GITHUB_TOKEN}"}

    json_string = json.dumps(novos_dados, indent=4, ensure_ascii=False)
    encoded = base64.b64encode(json_string.encode('utf-8')).decode('utf-8')
    
    payload = {
        "message": "Update GABMA Database",
        "content": encoded,
        "branch": BRANCH
    }
    if sha:
        payload["sha"] = sha
    
    response = requests.put(url, headers=headers, json=payload)
    return response.status_code in [200, 201]


# ============================================================
#  PDF — GERADOR PREMIUM COM WRAP CORRIGIDO
# ============================================================
def gerar_pdf(dados):
    pdf = FPDF()
    pdf.set_margins(10, 10, 10)
    pdf.set_auto_page_break(auto=True, margin=15)
    pdf.add_page()

    # Fontes
    fonte_normal = "DejaVuSans.ttf"
    fonte_bold = "DejaVuSans-Bold.ttf"

    if os.path.exists(fonte_normal):
        pdf.add_font("DejaVu", "", fonte_normal, uni=True)
        pdf.add_font("DejaVu", "B", fonte_bold, uni=True)
        fonte_principal = "DejaVu"
    else:
        fonte_principal = "Helvetica"

    # ---- Funções internas ----
    def chunk_long_word(text, max_width):
        char_w = max(pdf.get_string_width("M"), 0.01)
        max_chars = max(int((max_width - 2) / char_w), 1)
        return [text[i:i+max_chars] for i in range(0, len(text), max_chars)]

    def wrap_text(txt, max_width):
        txt = sanitize_text(str(txt or ""))
        if not txt.strip():
            return [""]

        words = txt.split(" ")
        lines = []
        current = ""

        for w in words:
            # palavra gigante sem espaço
            if pdf.get_string_width(w) > max_width:
                lines.extend(chunk_long_word(w, max_width))
                continue

            candidate = f"{current} {w}".strip()
            if pdf.get_string_width(candidate) <= max_width:
                current = candidate
            else:
                lines.append(current)
                current = w

        if current:
            lines.append(current)

        return lines

    def draw_row(col_w, data, aligns=None, line_h=6, pad=1):
        aligns = aligns or ["L"] * len(col_w)
        col_lines = [wrap_text(t, col_w[i]) for i, t in enumerate(data)]
        max_lines = max(len(c) for c in col_lines)
        row_h = max_lines * line_h

        if pdf.get_y() + row_h > pdf.page_break_trigger:
            pdf.add_page()

        x0, y0 = pdf.get_x(), pdf.get_y()

        for i, w in enumerate(col_w):
            x, y = pdf.get_x(), pdf.get_y()
            pdf.rect(x, y, w, row_h)

            for j, l in enumerate(col_lines[i]):
                pdf.set_xy(x + pad, y + j * line_h)
                pdf.cell(w - pad * 2, line_h, l, border=0, align=aligns[i])

            pdf.set_xy(x + w, y)

        pdf.set_xy(x0, y0 + row_h)

    # ---- Cabeçalho ----
    pdf.set_fill_color(31, 73, 125)
    pdf.set_text_color(255, 255, 255)
    pdf.set_font(fonte_principal, "B", 16)
    pdf.cell(0, 15, f"GUIA TÉCNICA: {dados.get('nome','').upper()}", ln=True, align='C', fill=True)
    pdf.ln(5)

    # ---- Seção 1 ----
    pdf.set_text_color(0, 0, 0)
    pdf.set_fill_color(230, 230, 230)
    pdf.set_font(fonte_principal, "B", 11)
    pdf.cell(0, 8, " 1. DADOS DE IDENTIFICAÇÃO E ACESSO", ln=True, fill=True)
    pdf.ln(2)

    CONTENT_WIDTH = pdf.w - pdf.l_margin - pdf.r_margin
    pdf.set_font(fonte_principal, "", 9)

    # Empresa / Código
    pdf.multi_cell(CONTENT_WIDTH, 7,
                   sanitize_text(f"Empresa: {dados.get('empresa','N/A')} | Código: {dados.get('codigo','N/A')}"))

    # Portal longa (fix do erro!)
    portal_text = sanitize_text(f"Portal: {dados.get('site','')}")
    for line in wrap_text(portal_text, CONTENT_WIDTH):
        pdf.multi_cell(CONTENT_WIDTH, 7, line)

    pdf.multi_cell(CONTENT_WIDTH, 7,
                   sanitize_text(f"Login: {dados.get('login','')}  |  Senha: {dados.get('senha','')}"))
    pdf.multi_cell(CONTENT_WIDTH, 7,
                   sanitize_text(f"Sistema: {dados.get('sistema_utilizado','N/A')} | Retorno: {dados.get('prazo_retorno','N/A')}"))

    pdf.ln(5)

    # ---- Seção 2 Tabela ----
    pdf.set_fill_color(230, 230, 230)
    pdf.set_font(fonte_principal, "B", 11)
    pdf.cell(0, 8, " 2. CRONOGRAMA E REGRAS TÉCNICAS", ln=True, fill=True)
    pdf.ln(2)

    pdf.set_font(fonte_principal, "B", 8)
    col_w = [45, 30, 25, 25, 65]
    header = ["Prazo Envio", "Validade Guia", "XML / Versão", "Nota Fiscal", "Fluxo NF"]
    draw_row(col_w, header, aligns=['C'] * 5, line_h=7)

    pdf.set_font(fonte_principal, "", 8)
    draw_row(col_w, [
        dados.get("envio", ""),
        f"{dados.get('validade','')} dias",
        f"{dados.get('xml','')} / {dados.get('versao_xml','-')}",
        dados.get("nf",""),
        dados.get("fluxo_nf","N/A")
    ], aligns=['C']*5, line_h=7)

    pdf.ln(5)

    # ---- Blocos ----
    def bloco(titulo, conteudo):
        if not conteudo:
            return
        pdf.set_fill_color(240, 240, 240)
        pdf.set_font(fonte_principal, "B", 11)
        pdf.cell(0, 7, f" {titulo}", ln=True, fill=True)
        pdf.set_font(fonte_principal, "", 9)
        pdf.multi_cell(0, 5, sanitize_text(conteudo), border=1)
        pdf.ln(3)

    bloco("CONFIGURAÇÃO DO GERADOR XML", dados.get("config_gerador"))
    bloco("DIGITALIZAÇÃO E DOCUMENTAÇÃO", dados.get("doc_digitalizacao"))
    bloco("OBSERVAÇÕES CRÍTICAS", dados.get("observacoes"))

    # ---- Rodapé ----
    pdf.set_y(-20)
    pdf.set_text_color(120, 120, 120)
    pdf.set_font(fonte_principal, "", 8)
    pdf.cell(0, 10, "GABMA Consultoria - Sistema Técnico de Convênios", align='C')

    return bytes(pdf.output())


# ============================================================
#       APP – INÍCIO
# ============================================================
st.set_page_config(page_title="GABMA – Sistema Técnico", layout="wide")

st.markdown(f"<div class='main-title'>💼 Sistema de Gestão GABMA</div>", unsafe_allow_html=True)

dados_atuais, sha_atual = buscar_dados_github()

# MENU
menu = st.sidebar.radio(
    "Navegação",
    ["Cadastrar / Editar", "Consulta de Convênios", "Visualizar Banco"]
)


# ============================================================
#           CADASTRO & EDIÇÃO
# ============================================================
if menu == "Cadastrar / Editar":

    st.markdown("<div class='card'><div class='card-title'>📝 Cadastro de Convênio</div>", unsafe_allow_html=True)

    nomes = ["+ Novo Convênio"] + sorted([c["nome"] for c in dados_atuais])
    escolha = st.selectbox("Selecione um convênio:", nomes)

    dados_conv = next((c for c in dados_atuais if c["nome"] == escolha), None)

    VERSOES_TISS = ["4.03.00", "4.02.00", "4.01.00", "01.06.00", "3.05.00", "3.04.01"]

    with st.form("form_cadastro"):
        col1, col2, col3 = st.columns(3)

        # Coluna 1
        with col1:
            nome = st.text_input("Nome do Convênio", value=dados_conv["nome"] if dados_conv else "")
            codigo = st.text_input("Código", value=dados_conv.get("codigo", "") if dados_conv else "")
            empresa = st.text_input("Empresa Faturamento", value=dados_conv.get("empresa", "") if dados_conv else "")
            sistema = st.selectbox("Sistema", ["Orizon", "Benner", "Maida", "Facil", "Visual TISS", "Próprio"])

        # Coluna 2
        with col2:
            site = st.text_input("Site/Portal", value=dados_conv["site"] if dados_conv else "")
            login = st.text_input("Login", value=dados_conv["login"] if dados_conv else "")
            senha = st.text_input("Senha", value=dados_conv["senha"] if dados_conv else "")
            retorno = st.text_input("Prazo Retorno", value=dados_conv.get("prazo_retorno", "") if dados_conv else "")

        # Coluna 3
        with col3:
            envio = st.text_input("Prazo Envio", value=dados_conv["envio"] if dados_conv else "")
            validade = st.text_input("Validade Guia", value=dados_conv["validade"] if dados_conv else "")
            xml = st.radio("Envia XML?", ["Sim", "Não"], index=0 if not dados_conv or dados_conv["xml"] == "Sim" else 1)
            nf = st.radio("Exige NF?", ["Sim", "Não"], index=0 if not dados_conv or dados_conv["nf"] == "Sim" else 1)

        st.markdown("</div>", unsafe_allow_html=True)
        st.markdown("<br>", unsafe_allow_html=True)

        col_a, col_b = st.columns(2)

        v_xml = col_a.selectbox(
            "Versão XML (Padrão TISS)",
            VERSOES_TISS,
            index=(VERSOES_TISS.index(dados_conv.get("versao_xml"))
                if dados_conv and dados_conv.get("versao_xml") in VERSOES_TISS else 0)
        )

        fluxo_nf = col_b.selectbox(
            "Fluxo Nota",
            ["Envia XML sem nota", "Envia NF junto com o lote"]
        )

        config_gerador = st.text_area("Configuração Gerador XML", value=dados_conv.get("config_gerador", "") if dados_conv else "")
        doc_dig = st.text_area("Digitalização e Documentação", value=dados_conv.get("doc_digitalizacao", "") if dados_conv else "")
        obs = st.text_area("Observações Críticas", value=dados_conv["observacoes"] if dados_conv else "")

        if st.form_submit_button("💾 Salvar Dados"):
            novo = {
                "nome": nome,
                "codigo": codigo,
                "empresa": empresa,
                "sistema_utilizado": sistema,
                "site": site,
                "login": login,
                "senha": senha,
                "prazo_retorno": retorno,
                "envio": envio,
                "validade": validade,
                "nf": nf,
                "fluxo_nf": fluxo_nf,
                "xml": xml,
                "versao_xml": v_xml,
                "config_gerador": config_gerador,
                "doc_digitalizacao": doc_dig,
                "observacoes": obs
            }

            if escolha == "+ Novo Convênio":
                dados_atuais.append(novo)
            else:
                idx = next(i for i, c in enumerate(dados_atuais) if c["nome"] == escolha)
                dados_atuais[idx] = novo

            if salvar_dados_github(dados_atuais, sha_atual):
                st.success("Dados salvos com sucesso!")
                st.rerun()

    if dados_conv:
        st.download_button(
            "📥 Baixar PDF do Convênio",
            gerar_pdf(dados_conv),
            f"GABMA_{escolha}.pdf",
            "application/pdf"
        )


# ============================================================
#       CONSULTA DE CONVÊNIOS
# ============================================================
elif menu == "Consulta de Convênios":

    st.markdown("<div class='card'><div class='card-title'>🔎 Consulta de Convênios</div>", unsafe_allow_html=True)

    if not dados_atuais:
        st.info("Nenhum convênio cadastrado.")
        st.stop()

    nomes_conv = sorted([c["nome"] for c in dados_atuais])
    escolha = st.selectbox("Selecione o convênio:", nomes_conv)

    dados = next(c for c in dados_atuais if c["nome"] == escolha)

    st.markdown(
        f"""
        <div style="
            margin-top:20px;
            padding:25px;
            text-align:center;
            color:white;
            background:{PRIMARY_COLOR};
            border-radius:10px;
            font-size:26px;
            font-weight:700;">
            {dados["nome"].upper()}
        </div>
        """,
        unsafe_allow_html=True
    )

    # Identificação
    st.markdown("<div class='card'><div class='card-title'>🧾 Dados de Identificação</div>", unsafe_allow_html=True)
    st.markdown(f"""
        <div class='info-line'>Empresa: <span class='value'>{dados.get('empresa','N/A')}</span></div>
        <div class='info-line'>Código: <span class='value'>{dados.get('codigo','N/A')}</span></div>
        <div class='info-line'>Sistema: <span class='value'>{dados.get('sistema_utilizado','N/A')}</span></div>
        <div class='info-line'>Retorno: <span class='value'>{dados.get('prazo_retorno','N/A')}</span></div>
    """, unsafe_allow_html=True)
    st.markdown("</div>", unsafe_allow_html=True)

    # Acesso
    st.markdown("<div class='card'><div class='card-title'>🔐 Acesso ao Portal</div>", unsafe_allow_html=True)
    st.markdown(f"""
        <div class='info-line'>Portal: <span class='value'>{dados['site']}</span></div>
        <div class='info-line'>Login: <span class='value'>{dados['login']}</span></div>
        <div class='info-line'>Senha: <span class='value'>{dados['senha']}</span></div>
    """, unsafe_allow_html=True)
    st.markdown("</div>", unsafe_allow_html=True)

    # Técnicos
    st.markdown("<div class='card'><div class='card-title'>📦 Regras Técnicas</div>", unsafe_allow_html=True)
    st.markdown(f"""
        <div class='info-line'>Prazo Envio: <span class='value'>{dados['envio']}</span></div>
        <div class='info-line'>Validade Guia: <span class='value'>{dados['validade']} dias</span></div>
        <div class='info-line'>Envia XML? <span class='value'>{dados['xml']}</span></div>
        <div class='info-line'>Versão XML: <span class='value'>{dados.get('versao_xml','N/A')}</span></div>
        <div class='info-line'>Exige NF? <span class='value'>{dados['nf']}</span></div>
        <div class='info-line'>Fluxo da Nota: <span class='value'>{dados.get('fluxo_nf','N/A')}</span></div>
    """, unsafe_allow_html=True)
    st.markdown("</div>", unsafe_allow_html=True)

    # Blocos extras
    if dados.get("config_gerador"):
        st.markdown("<div class='card'><div class='card-title'>⚙️ Configuração XML</div>", unsafe_allow_html=True)
        st.code(dados["config_gerador"])
        st.markdown("</div>", unsafe_allow_html=True)

    if dados.get("doc_digitalizacao"):
        st.markdown("<div class='card'><div class='card-title'>🗂 Digitalização e Documentação</div>", unsafe_allow_html=True)
        st.info(dados["doc_digitalizacao"])
        st.markdown("</div>", unsafe_allow_html=True)

    if dados.get("observacoes"):
        st.markdown("<div class='card'><div class='card-title'>⚠️ Observações Críticas</div>", unsafe_allow_html=True)
        st.markdown(
            f"""
            <div style="
                background-color: white;
                color: {TEXT_DARK};
                border-left: 4px solid {PRIMARY_COLOR};
                padding: 12px 16px;
                border-radius: 6px;
                font-size: 15px;
                line-height: 1.5;">
                {dados["observacoes"]}
            </div>
            """,
            unsafe_allow_html=True
        )
        st.markdown("</div>", unsafe_allow_html=True)

    st.caption("GABMA Consultoria — Visualização Premium")


# ============================================================
#       VISUALIZAR BANCO
# ============================================================
elif menu == "Visualizar Banco":

    st.markdown("<div class='card'><div class='card-title'>📋 Banco de Dados Completo</div>", unsafe_allow_html=True)

    if dados_atuais:
        st.dataframe(pd.DataFrame(dados_atuais))
    else:
        st.info("Banco vazio.")

    st.markdown("</div>", unsafe_allow_html=True)


# ============================================================
#  DESIGN FLUENT 2 + HEADER FIXO
# ============================================================
st.markdown(
    f"""
    <style>
        .card {{
            transition: all 0.18s ease-in-out;
        }}
        .card:hover {{
            transform: translateY(-2px);
            box-shadow: 0 4px 12px rgba(0,0,0,0.08);
        }}

        .header-premium {{
            position: sticky;
            top: 0;
            z-index: 999;
            background: white;
            padding: 18px 10px;
            border-bottom: 2px solid {PRIMARY_COLOR}22;
            backdrop-filter: blur(4px);
        }}

        .header-title {{
            font-size: 30px;
            font-weight: 700;
            color: {PRIMARY_COLOR};
        }}

        .stButton>button {{
            background-color: {PRIMARY_COLOR};
            color: white;
            border-radius: 6px;
            padding: 8px 16px;
            border: none;
            font-weight: 600;
            transition: 0.2s;
        }}
        .stButton>button:hover {{
            background-color: #16375E;
        }}

        .block-container {{
            padding-top: 0px !important;
        }}
    </style>
    """,
    unsafe_allow_html=True
)

# HEADER FIXO
st.markdown(
    f"""
    <div class="header-premium">
        <span class="header-title">💼 GABMA — Sistema Técnico Corporativo</span>
    </div>
    """,
    unsafe_allow_html=True
)
st.write("")

# Sidebar Refresh
st.sidebar.markdown("### 🔄 Atualização")
if st.sidebar.button("Recarregar Sistema"):
    st.rerun()

# Footer
st.markdown(
    f"""
    <br><br>
    <div style='text-align:center; color:#777; font-size:13px; padding:10px;'>
        © 2026 — GABMA Consultoria · Sistema Técnico de Convênios<br>
        Desenvolvido com design corporativo Microsoft/MV
    </div>
    """,
    unsafe_allow_html=True
)
