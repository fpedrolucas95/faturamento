Para implementar o streamlit-quill no seu módulo de rotinas, precisamos realizar três ajustes principais:

Limpar o HTML antes de gerar o PDF: Como o Quill salva o conteúdo com tags HTML, precisamos remover essas tags (ou convertê-las em texto simples) para que o PDF não exiba códigos como <p> ou <strong>.

Trocar o st.text_area pelo st_quill: Substituir o campo de entrada no formulário.

Importar o componente: Garantir que o st_quill esteja disponível no escopo do módulo.

Aqui está o código atualizado do seu arquivo rotinas_module.py:

Python

# rotinas_module.py
from typing import Callable, Any, List, Tuple
from fpdf import FPDF
import streamlit as st
import pandas as pd
import time
import re
from streamlit_quill import st_quill # <--- IMPORT NOVO

class RotinasModule:
    def __init__(
        self,
        db_rotinas: Any,
        sanitize_text: Callable[[str], str],
        build_wrapped_lines: Callable[[str, FPDF, float, float, float], List[Tuple[str, float]]],
        _pdf_set_fonts: Callable[[FPDF], str],
        generate_id: Callable[[list], int],
        safe_get: Callable[[dict, str, str], str],
        primary_color: str = "#1F497D",
        setores_opcoes: List[str] = None,
    ):
        self.db = db_rotinas
        self.sanitize_text = sanitize_text
        self.build_wrapped_lines = build_wrapped_lines
        self._pdf_set_fonts = _pdf_set_fonts
        self.generate_id = generate_id
        self.safe_get = safe_get
        self.primary_color = primary_color
        self.setores_opcoes = list(setores_opcoes or [])

    # ============================================================
    # UTILITÁRIO: Limpeza de HTML para o PDF
    # ============================================================
    def _clean_html(self, raw_html: str) -> str:
        """Remove tags HTML para que o PDF processe texto limpo."""
        if not raw_html: return ""
        # Remove tags e converte &nbsp; em espaço
        cleanr = re.compile('<.*?>|&nbsp;')
        cleantext = re.sub(cleanr, ' ', raw_html)
        # Remove espaços duplos resultantes da limpeza
        return re.sub(r' +', ' ', cleantext).strip()

    # =========================
    # PDF de uma rotina (premium)
    # =========================
    def gerar_pdf_rotina(self, dados: dict) -> bytes:
        pdf = FPDF(orientation="P", unit="mm", format="A4")
        pdf.set_margins(15, 12, 15)
        pdf.set_auto_page_break(auto=True, margin=15)
        pdf.add_page()

        BLUE = (31, 73, 125)
        GREY_BAR = (230, 230, 230)
        TEXT = (0, 0, 0)
        CONTENT_W = pdf.w - pdf.l_margin - pdf.r_margin

        FONT = self._pdf_set_fonts(pdf)

        def set_font(size=10, bold=False):
            style = "B" if bold else ""
            try:
                pdf.set_font(FONT, style, size)
            except Exception:
                pdf.set_font("Helvetica", style, size)

        def bar_title(texto: str, top_margin: float = 3.0, height: float = 8.0):
            pdf.ln(top_margin)
            pdf.set_fill_color(*GREY_BAR)
            set_font(12, True)
            pdf.cell(0, height, f" {texto.upper()}", ln=1, fill=True)
            pdf.ln(1.5)

        nome_rot = self.sanitize_text(self.safe_get(dados, "nome")).upper()
        pdf.set_fill_color(*BLUE)
        pdf.set_text_color(255, 255, 255)
        set_font(18, True)
        pdf.cell(0, 14, nome_rot, ln=1, align="C", fill=True)
        pdf.set_text_color(*TEXT)
        pdf.ln(5)

        setor_val = self.sanitize_text(self.safe_get(dados, "setor"))
        if setor_val:
            pdf.set_text_color(80, 80, 80)
            set_font(11, False)
            pdf.cell(0, 7, f"Setor: {setor_val}", ln=1, align="C")
            pdf.set_text_color(*TEXT)
            pdf.ln(2)

        bar_title("Descrição")

        # ✅ LIMPEZA DE HTML ANTES DE ENVIAR PARA O BUILDER DO PDF
        descricao_raw = self.safe_get(dados, "descricao")
        descricao = self._clean_html(descricao_raw) 
        
        width = CONTENT_W
        line_h = 6.6
        padding = 1.8
        bullet_indent = 4.0
        usable_w = width - 2 * padding
        set_font(10, False)

        wrapped_lines = self.build_wrapped_lines(descricao, pdf, usable_w, line_h, bullet_indent=bullet_indent)

        i = 0
        while i < len(wrapped_lines):
            y_top = pdf.get_y()
            space = pdf.page_break_trigger - y_top
            avail_h = max(0.0, space - 2 * padding - 0.5)
            lines_per_page = int(avail_h // line_h) if avail_h > 0 else 0
            if lines_per_page <= 0:
                pdf.add_page()
                continue

            end = min(len(wrapped_lines), i + lines_per_page)
            slice_lines = wrapped_lines[i:end]
            box_h = 2 * padding + len(slice_lines) * line_h
            pdf.rect(pdf.l_margin, y_top, width, box_h)

            x_text_base = pdf.l_margin + padding
            y_text = y_top + padding
            for (ln_text, indent_mm) in slice_lines:
                pdf.set_xy(x_text_base + indent_mm, y_text)
                pdf.cell(usable_w - indent_mm, line_h, ln_text)
                y_text += line_h

            pdf.set_y(y_top + box_h)
            i = end

        result = pdf.output(dest="S")
        if isinstance(result, str):
            result = result.encode("latin-1", "ignore")
        elif isinstance(result, bytearray):
            result = bytes(result)
        return bytes(result)

    # =========================
    # Página Streamlit do módulo
    # =========================
    def page(self):
        try:
            rotinas_atuais, _ = self.db.load(force=True)
        except Exception:
            rotinas_atuais = []
        if not isinstance(rotinas_atuais, list): rotinas_atuais = []
        rotinas_atuais = list(rotinas_atuais)

        st.markdown("<div class='card'><div class='card-title'>🗂️ Rotinas do Setor — Cadastro / Edição</div>", unsafe_allow_html=True)

        opcoes = ["+ Nova Rotina"] + [f"{r.get('id')} — {self.safe_get(r, 'nome')}" for r in rotinas_atuais]
        escolha = st.selectbox("Selecione uma rotina para editar:", opcoes)

        if escolha == "+ Nova Rotina":
            rotina_id = None
            dados_rotina = None
        else:
            rotina_id = escolha.split(" — ")[0]
            dados_rotina = next((r for r in rotinas_atuais if str(r.get('id')) == str(rotina_id)), None)

        st.markdown("</div>", unsafe_allow_html=True)

        # ✅ REMOVIDO st.form() pois o st_quill não funciona bem dentro de forms do Streamlit 
        # (O Quill não envia o estado para o submit do form de forma nativa às vezes)
        # Vamos usar um container simples.
        
        st.markdown("### Detalhes da Rotina")
        nome = st.text_input("Nome da Rotina", value=self.safe_get(dados_rotina, "nome"))

        setor_atual = self.safe_get(dados_rotina, "setor")
        if self.setores_opcoes:
            if setor_atual not in self.setores_opcoes: setor_atual = self.setores_opcoes[0]
            idx_setor = self.setores_opcoes.index(setor_atual) if setor_atual in self.setores_opcoes else 0
            setor = st.selectbox("Setor", self.setores_opcoes, index=idx_setor)
        else:
            setor = st.text_input("Setor", value=setor_atual or "")

        st.write("Descrição da Rotina (Editor Rico)")
        # ✅ IMPLEMENTAÇÃO DO ST_QUILL
        descricao_html = st_quill(
            value=self.safe_get(dados_rotina, "descricao"),
            placeholder="Descreva o passo a passo da rotina...",
            key=f"quill_rotina_{rotina_id}"
        )

        if st.button("💾 Salvar Rotina", use_container_width=True):
            novo_registro = {
                "id": int(rotina_id) if rotina_id else self.generate_id(rotinas_atuais),
                "nome": nome,
                "setor": setor,
                "descricao": descricao_html, # Salva o HTML gerado pelo Quill
            }

            if rotina_id is None:
                rotinas_atuais.append(novo_registro)
            else:
                for i, r in enumerate(rotinas_atuais):
                    if str(r.get("id")) == str(rotina_id):
                        rotinas_atuais[i] = novo_registro
                        break

            if self.db.save(rotinas_atuais):
                st.success(f"✔ Rotina salva com sucesso!")
                self.db._cache_data = None
                time.sleep(1)
                st.rerun()

        # ---- Botão PDF ----
        if dados_rotina:
            st.markdown("---")
            try:
                pdf_bytes = self.gerar_pdf_rotina(dados_rotina)
                st.download_button(
                    label="📥 Baixar PDF da Rotina",
                    data=pdf_bytes,
                    file_name=f"Rotina_{setor}_{nome}.pdf".replace(" ", "_"),
                    mime="application/pdf",
                )
            except Exception as e:
                st.error("Falha ao gerar o PDF.")

            # ---- Exclusão ----
            rotina_id_str = str(dados_rotina.get("id") or "")
            with st.expander("🗑️ Excluir rotina (permanente)", expanded=False):
                confirm_val = st.text_input(f"Confirmação: digite **{rotina_id_str}**", key=f"del_rot_{rotina_id_str}")
                if st.button("Excluir permanentemente", type="primary", disabled=(confirm_val != rotina_id_str)):
                    def _update(data):
                        return [r for r in (data or []) if str(r.get("id")) != rotina_id_str]
                    self.db.update(_update)
                    st.success("Excluído!")
                    time.sleep(1)
                    st.rerun()

        # ---- Visualização do banco ----
        st.markdown("<div class='card'><div class='card-title'>📋 Banco de Rotinas</div>", unsafe_allow_html=True)
        if rotinas_atuais:
            df = pd.DataFrame(rotinas_atuais)
            st.dataframe(df, use_container_width=True)
        st.markdown("</div>", unsafe_allow_html=True)
