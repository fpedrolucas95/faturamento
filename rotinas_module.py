
# rotinas_module.py
# Módulo "Rotinas do Setor" — Cadastro/Edição + PDF Premium + Exclusão permanente

from typing import Callable, Any, List, Tuple
from fpdf import FPDF
import streamlit as st
import pandas as pd
import time
import re
import base64
import io

from streamlit_quill import st_quill
from streamlit_paste_button import paste_image_button


class RotinasModule:
    """
    Módulo independente para cadastro/edição de Rotinas do Setor.
    Usa injeção de dependências vindas do app principal.
    """

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

    # =============================
    # UTILITÁRIOS INTERNOS
    # =============================
    def _clean_html(self, raw_html: str) -> str:
        """Remove tags HTML para PDF"""
        if not raw_html:
            return ""
        cleanr = re.compile('<.*?>|&nbsp;')
        cleantext = re.sub(cleanr, ' ', raw_html)
        return re.sub(r' +', ' ', cleantext).strip()

    def _image_to_base64(self, img):
        """Converte imagem PIL para base64 string"""
        if img is None:
            return ""
        buf = io.BytesIO()
        img.save(buf, format="PNG")
        return "data:image/png;base64," + base64.b64encode(buf.getvalue()).decode()


    # ============================================================
    # GERAR PDF PREMIUM DA ROTINA
    # ============================================================
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
            pdf.set_font(FONT, "B" if bold else "", size)

        def bar_title(txt):
            pdf.ln(3)
            pdf.set_fill_color(*GREY_BAR)
            set_font(12, True)
            pdf.cell(0, 8, " " + txt.upper(), ln=1, fill=True)
            pdf.ln(2)

        # ===== TÍTULO =====
        nome_rot = self.sanitize_text(self.safe_get(dados, "nome")).upper()
        pdf.set_fill_color(*BLUE)
        pdf.set_text_color(255, 255, 255)
        set_font(18, True)
        pdf.cell(0, 14, nome_rot or "ROTINA", ln=1, align="C", fill=True)

        pdf.set_text_color(0, 0, 0)
        pdf.ln(4)

        # ===== SETOR =====
        setor = self.sanitize_text(self.safe_get(dados, "setor"))
        if setor:
            set_font(11)
            pdf.set_text_color(80, 80, 80)
            pdf.cell(0, 7, f"Setor: {setor}", ln=1, align="C")
            pdf.ln(2)
        pdf.set_text_color(0, 0, 0)

        # ===== IMAGEM =====
        img_b64 = self.safe_get(dados, "print_b64")
        if img_b64 and "base64" in img_b64:
            try:
                raw = base64.b64decode(img_b64.split(",")[1])
                buf = io.BytesIO(raw)
                pdf.image(buf, x=pdf.l_margin, w=120)
                pdf.ln(10)
            except:
                pass

        # ===== DESCRIÇÃO =====
        bar_title("Descrição")

        texto = self._clean_html(self.safe_get(dados, "descricao"))
        set_font(10)

        usable_w = CONTENT_W - 4
        line_h = 6.4
        bullet_indent = 4

        linhas = self.build_wrapped_lines(texto, pdf, usable_w, line_h, bullet_indent)

        for ln, indent in linhas:
            pdf.set_x(pdf.l_margin + 2 + indent)
            pdf.cell(usable_w - indent, line_h, ln, ln=1)

        out = pdf.output(dest="S")
        return out.encode("latin-1", "ignore") if isinstance(out, str) else bytes(out)


    # ============================================================
    # PÁGINA STREAMLIT
    # ============================================================
    def page(self):

        try:
            rotinas_atuais, _ = self.db.load(force=True)
        except:
            rotinas_atuais = []

        if not isinstance(rotinas_atuais, list):
            rotinas_atuais = []

        st.markdown(
            "<div class='card'><div class='card-title'>🗂️ Rotinas do Setor</div>",
            unsafe_allow_html=True,
        )

        opcoes = ["+ Nova Rotina"] + [
            f"{r.get('id')} — {self.safe_get(r, 'nome', 'Sem Nome')}"
            for r in rotinas_atuais
        ]

        escolha = st.selectbox("Selecione uma rotina:", opcoes)

        if escolha == "+ Nova Rotina":
            rotina_id = "novo"
            dados_rotina = {"print_b64": ""}
        else:
            rotina_id = escolha.split(" — ")[0]
            dados_rotina = next(
                (r for r in rotinas_atuais if str(r.get("id")) == str(rotina_id)),
                {"print_b64": ""}
            )

        st.markdown("</div>", unsafe_allow_html=True)

        # =============================
        # CAMPOS
        # =============================
        st.markdown("### Detalhes da Rotina")
        nome = st.text_input("Nome", value=self.safe_get(dados_rotina, "nome"))

        setor_atual = self.safe_get(dados_rotina, "setor")
        if self.setores_opcoes:
            if setor_atual not in self.setores_opcoes:
                setor_atual = self.setores_opcoes[0]
            setor = st.selectbox("Setor", self.setores_opcoes, index=self.setores_opcoes.index(setor_atual))
        else:
            setor = st.text_input("Setor", value=setor_atual)

        # =============================
        # QUILL
        # =============================
        st.markdown("##### 🖋️ Descrição")
        desc_inicial = str(self.safe_get(dados_rotina, "descricao"))
        descricao_html = st_quill(
            value=desc_inicial,
            key=f"quill_rotina_{rotina_id}",
            placeholder="Digite a descrição completa...",
            html=True,
        )

        # =============================
        # IMAGEM
        # =============================
        st.markdown("##### 📸 Print da Rotina (Opcional)")

        colA, colB = st.columns([1, 1])

        with colA:
            st.info("Cole o print aqui (Ctrl+V)")
            pasted = paste_image_button(label="📋 Colar Print", key=f"paste_rotina_{rotina_id}")

        img_b64_salvo = self.safe_get(dados_rotina, "print_b64")

        if pasted.image_data is not None:
            with colB:
                st.image(pasted.image_data, use_container_width=True)
            img_para_salvar = self._image_to_base64(pasted.image_data)

        elif img_b64_salvo:
            with colB:
                st.image(img_b64_salvo, use_container_width=True)
            img_para_salvar = img_b64_salvo

        else:
            img_para_salvar = ""


        # =============================
        # SALVAR
        # =============================
        if st.button("💾 Salvar Rotina", use_container_width=True):

            if not nome:
                st.error("O nome é obrigatório.")
                return

            id_final = self.generate_id(rotinas_atuais) if rotina_id == "novo" else int(rotina_id)

            novo_registro = {
                "id": id_final,
                "nome": nome,
                "setor": setor,
                "descricao": descricao_html,
                "print_b64": img_para_salvar,
            }

            if rotina_id == "novo":
                rotinas_atuais.append(novo_registro)
            else:
                for i, r in enumerate(rotinas_atuais):
                    if str(r.get("id")) == str(rotina_id):
                        rotinas_atuais[i] = novo_registro
                        break

            self.db.save(rotinas_atuais)
            st.success("✔ Rotina salva!")
            time.sleep(0.8)
            st.rerun()

        # =============================
        # PDF
        # =============================
        if rotina_id != "novo" and dados_rotina:
            pdf_bytes = self.gerar_pdf_rotina(dados_rotina)
            st.download_button(
                "📥 Baixar PDF da Rotina",
                pdf_bytes,
                file_name=f"Rotina_{self.safe_get(dados_rotina,'nome')}.pdf",
                mime="application/pdf",
            )

        # =============================
        # EXCLUSÃO
        # =============================
        if rotina_id != "novo":
            rotina_id_str = str(dados_rotina.get("id"))
            with st.expander("🗑️ Excluir rotina", expanded=False):
                st.warning("Digite o ID para confirmar a exclusão permanente.")
                confirm = st.text_input("Confirme:", key=f"conf_del_{rotina_id_str}")

                if confirm.strip() == rotina_id_str:
                    if st.button("Excluir DEFINITIVO", type="primary"):
                        def _upd(data):
                            return [r for r in data if str(r.get("id")) != rotina_id_str]

                        self.db.update(_upd)
                        st.success("✔ Rotina excluída!")
                        st.rerun()

        # =============================
        # VISUALIZAR TABELA
        # =============================
        st.markdown(
            "<div class='card'><div class='card-title'>📋 Banco de Rotinas</div>",
            unsafe_allow_html=True,
        )

        if rotinas_atuais:
            df = pd.DataFrame(rotinas_atuais)
            st.dataframe(df, use_container_width=True)
        else:
            st.info("Nenhuma rotina cadastrada ainda.")

        st.markdown("</div>", unsafe_allow_html=True)



