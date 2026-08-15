from io import BytesIO
from datetime import datetime
from pathlib import Path

from fpdf import FPDF

_FONT_DIR = Path(__file__).resolve().parent.parent / "static" / "fonts"


class LegalPDF(FPDF):
    def __init__(self, site_name):
        super().__init__()
        self.site_name = site_name
        self.set_auto_page_break(auto=True, margin=22)
        self.set_left_margin(18)
        self.set_right_margin(18)
        self.add_font("DejaVu", "", str(_FONT_DIR / "DejaVuSans.ttf"))
        self.add_font("DejaVu", "B", str(_FONT_DIR / "DejaVuSans-Bold.ttf"))
        self.add_font("DejaVu", "I", str(_FONT_DIR / "DejaVuSans-Oblique.ttf"))

    def header(self):
        if self.page_no() == 1:
            return
        self.set_font("DejaVu", "", 9)
        self.set_text_color(44, 62, 125)
        self.cell(0, 8, f"{self.site_name}  |  Legal policies and statements")
        self.ln(4)
        self.set_draw_color(44, 62, 125)
        self.line(18, self.get_y(), 192, self.get_y())
        self.ln(8)

    def footer(self):
        self.set_y(-16)
        self.set_font("DejaVu", "", 8)
        self.set_text_color(107, 119, 140)
        self.cell(0, 8, f"Page {self.page_no()}", align="C")


def _heading(pdf, text, size=13):
    pdf.set_font("DejaVu", "B", size)
    pdf.set_text_color(31, 58, 122)
    pdf.multi_cell(0, 7, text)
    pdf.ln(2)


def _intro(pdf, text):
    pdf.set_font("DejaVu", "I", 11)
    pdf.set_text_color(68, 80, 102)
    pdf.multi_cell(0, 6.5, text)
    pdf.ln(4)


def _paragraph(pdf, text):
    pdf.set_font("DejaVu", "", 11)
    pdf.set_text_color(68, 80, 102)
    pdf.multi_cell(0, 6.4, text)
    pdf.ln(3)


def _write_document(pdf, title, intro, sections):
    pdf.add_page()
    _heading(pdf, title, 16)
    if intro:
        _intro(pdf, intro)
    for section in sections:
        _heading(pdf, section.get("heading", ""), 12)
        for paragraph in section.get("paragraphs", []):
            _paragraph(pdf, paragraph)


def build_legal_pdf(site, legal, security):
    pdf = LegalPDF(site.get("name", "AfriCloud Institute"))
    year = datetime.now().year

    pdf.add_page()
    pdf.set_fill_color(44, 62, 125)
    pdf.rect(0, 0, 210, 297, "F")
    pdf.set_text_color(255, 255, 255)
    pdf.set_y(90)
    pdf.set_font("DejaVu", "B", 26)
    pdf.multi_cell(0, 12, site.get("name", "AfriCloud Institute"), align="C")
    pdf.ln(6)
    pdf.set_font("DejaVu", "", 16)
    pdf.multi_cell(0, 9, "Legal policies and statements", align="C")
    pdf.ln(10)
    pdf.set_font("DejaVu", "", 11)
    pdf.multi_cell(
        0,
        7,
        f"Last reviewed: {year}\n{site.get('location', '')}\n{site.get('email', '')}  ·  {site.get('phone_display', '')}",
        align="C",
    )
    pdf.ln(16)
    pdf.set_font("DejaVu", "I", 11)
    pdf.multi_cell(0, 7, legal.get("intro", ""), align="C")

    pdf.add_page()
    _heading(pdf, "Contents", 16)
    items = [policy["title"] for policy in legal.get("policies", [])]
    items.append(security.get("title", "Information Security Statement"))
    for index, title in enumerate(items, start=1):
        _paragraph(pdf, f"{index}.  {title}")

    for policy in legal.get("policies", []):
        _write_document(
            pdf,
            policy.get("title", ""),
            policy.get("intro", ""),
            policy.get("sections", []),
        )

    _write_document(
        pdf,
        security.get("title", "Information Security Statement"),
        security.get("intro", ""),
        security.get("sections", []),
    )

    output = pdf.output()
    if isinstance(output, (bytes, bytearray)):
        return bytes(output)
    return output.encode("latin-1")
