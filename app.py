import streamlit as st
from fpdf import FPDF

# Configuração da Página
st.set_page_config(page_title="Gerador de Formulários GABMA", layout="centered")

st.title("📄 Gerador de Formulário de Faturamento")
st.subheader("Cadastro de Regras por Convênio")

# --- INTERFACE DE ENTRADA ---
with st.form("form_convenio"):
    nome_convenio = st.text_input("NOME DO CONVÊNIO")
    
    st.markdown("### 1. Informações de Acesso e Portal")
    site = st.text_input("Site/Portal")
    login = st.text_input("Login")
    senha = st.text_input("Senha")
    sistema = st.selectbox("Sistema de Envio", ["Orizon", "Benner", "Maida", "Facil", "Próprio"])
    precisa_xml = st.radio("Precisa de XML?", ["Sim", "Não"])
    versao_xml = st.text_input("Versão XML")

    st.markdown("### 2. Cronograma e Prazos")
    data_envio = st.text_input("Data de Envio (Ex: 01 ao 05 dia útil)")
    validade_dias = st.text_input("Validade das Guias (Dias)")
    contar_a_partir = st.selectbox("Contar a partir de", ["1ª Sessão", "Última Sessão", "Data do Pedido"])

    st.markdown("### 3. Regras de Nota Fiscal (NF-e)")
    exige_nf = st.radio("Exige NF-e?", ["Sim", "Não"])
    fluxo_nf = st.selectbox("Fluxo de Emissão", ["Enviar XML primeiro, solicitar NF depois", "Enviar NF junto com o lote"])
    obs_divisao = st.text_area("Observação de Divisão (Ex: Uma nota para cada unidade)")

    st.markdown("### 4. Configurações do Gerador XML (Fhasso)")
    opcoes_xml = st.multiselect("Marcar as opções conforme manual", 
                                ["Guia Atribuída / Guia Operadora", "Guia Financeiro / Guia Prestador", 
                                 "Contratado / Solicitante", "Inibir Equipe Médica", "Aplicar CBO da Versão"])
    simpro = st.text_input("Simpro/Brasíndice (Dígitos)")

    st.markdown("### 5. Digitalização e Documentação")
    ordem_scanner = st.text_area("Ordem do Arquivo/Scanner")
    exigencias = st.multiselect("Exigências Específicas", ["RG/CPF (Frente e Verso)", "Carteirinha", "Relatório de Fisioterapia"])
    laudo_medico = st.text_input("Laudo Médico (Obrigatório para:)")
    limite_mb = st.text_input("Limite de Tamanho (MB)")

    st.markdown("### 6. Observações Críticas")
    obs_criticas = st.text_area("Particularidades")

    submit = st.form_submit_button("Gerar PDF do Convênio")

# --- LÓGICA DE GERAÇÃO DO PDF ---
if submit:
    pdf = FPDF()
    pdf.add_page()
    pdf.set_font("Arial", "B", 16)
    
    # Cabeçalho
    pdf.cell(200, 10, f"Formulário de Faturamento: {nome_convenio}", ln=True, align='C')
    pdf.ln(10)
    
    pdf.set_font("Arial", "B", 12)
    pdf.cell(200, 10, "1. Informações de Acesso e Portal", ln=True)
    pdf.set_font("Arial", "", 10)
    pdf.multi_cell(0, 7, f"Site/Portal: {site}\nLogin: {login} | Senha: {senha}\nSistema: {sistema} | XML: {precisa_xml} | Versão: {versao_xml}")
    
    pdf.ln(5)
    pdf.set_font("Arial", "B", 12)
    pdf.cell(200, 10, "2. Cronograma e Prazos", ln=True)
    pdf.set_font("Arial", "", 10)
    pdf.multi_cell(0, 7, f"Data de Envio: {data_envio}\nValidade: {validade_dias} dias | Contar a partir de: {contar_a_partir}")

    pdf.ln(5)
    pdf.set_font("Arial", "B", 12)
    pdf.cell(200, 10, "3. Regras de Nota Fiscal (NF-e)", ln=True)
    pdf.set_font("Arial", "", 10)
    pdf.multi_cell(0, 7, f"Exige NF: {exige_nf}\nFluxo: {fluxo_nf}\nDivisão: {obs_divisao}")

    pdf.ln(5)
    pdf.set_font("Arial", "B", 12)
    pdf.cell(200, 10, "4. Configurações do Gerador XML (Fhasso)", ln=True)
    pdf.set_font("Arial", "", 10)
    pdf.multi_cell(0, 7, f"Opções: {', '.join(opcoes_xml)}\nSimpro/Brasíndice: {simpro}")

    pdf.ln(5)
    pdf.set_font("Arial", "B", 12)
    pdf.cell(200, 10, "5. Digitalização e Documentação", ln=True)
    pdf.set_font("Arial", "", 10)
    pdf.multi_cell(0, 7, f"Ordem: {ordem_scanner}\nExigências: {', '.join(exigencias)}\nLaudo: {laudo_medico} | Limite: {limite_mb}MB")

    pdf.ln(5)
    pdf.set_font("Arial", "B", 12)
    pdf.cell(200, 10, "6. Observações Críticas", ln=True)
    pdf.set_font("Arial", "", 10)
    pdf.multi_cell(0, 7, obs_criticas)

    # Salva e oferece o download
    pdf_output = f"Formulario_{nome_convenio}.pdf"
    pdf.output(pdf_output)
    
    with open(pdf_output, "rb") as file:
        st.download_button(label="📥 Baixar PDF", data=file, file_name=pdf_output, mime="application/pdf")
    st.success(f"PDF de {nome_convenio} gerado com sucesso!")
