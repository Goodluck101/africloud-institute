from datetime import datetime
from pathlib import Path

from fpdf import FPDF

_ROOT = Path(__file__).resolve().parent.parent
_FONT_DIR = _ROOT / "static" / "fonts"
_LOGO = _ROOT / "static" / "images" / "logo.jpg"

NAVY = (26, 37, 80)
NAVY_MID = (44, 62, 125)
GREEN = (61, 155, 58)
MUTED = (107, 119, 140)
BODY = (68, 80, 102)
LINE = (231, 237, 245)
SOFT = (247, 249, 252)


class LegalPDF(FPDF):
    def __init__(self, site):
        super().__init__()
        self.site = site or {}
        self.site_name = self.site.get("name", "AfriCloud Institute")
        self.logo_path = _LOGO if _LOGO.exists() else None
        self.set_auto_page_break(auto=True, margin=24)
        self.set_left_margin(20)
        self.set_right_margin(20)
        self.set_top_margin(32)
        self.add_font("DejaVu", "", str(_FONT_DIR / "DejaVuSans.ttf"))
        self.add_font("DejaVu", "B", str(_FONT_DIR / "DejaVuSans-Bold.ttf"))
        self.add_font("DejaVu", "I", str(_FONT_DIR / "DejaVuSans-Oblique.ttf"))

    def header(self):
        if self.page_no() == 1:
            return

        if self.logo_path:
            self.image(str(self.logo_path), x=20, y=11, h=12)

        self.set_xy(70, 13)
        self.set_font("DejaVu", "", 9)
        self.set_text_color(*NAVY)
        self.cell(0, 5, self.site_name, align="R", new_x="LMARGIN", new_y="NEXT")
        self.set_x(70)
        self.set_font("DejaVu", "", 8)
        self.set_text_color(*MUTED)
        self.cell(0, 4, "Legal policies and statements", align="R")

        self.set_draw_color(*GREEN)
        self.set_line_width(0.7)
        self.line(20, 27, 190, 27)
        self.set_line_width(0.2)
        self.set_y(34)

    def footer(self):
        if self.page_no() == 1:
            return
        self.set_y(-18)
        self.set_draw_color(*LINE)
        self.set_line_width(0.3)
        self.line(20, self.get_y(), 190, self.get_y())
        self.set_y(-14)
        self.set_font("DejaVu", "", 8)
        self.set_text_color(*MUTED)
        self.cell(95, 6, self.site_name, align="L")
        self.cell(75, 6, f"Page {self.page_no()}", align="R")


def _heading(pdf, text, size=13):
    pdf.set_font("DejaVu", "B", size)
    pdf.set_text_color(*NAVY)
    pdf.multi_cell(0, 7, text)
    pdf.ln(2)


def _intro(pdf, text):
    pdf.set_font("DejaVu", "I", 10.5)
    pdf.set_text_color(*BODY)
    pdf.multi_cell(0, 6.2, text)
    pdf.ln(4)


def _paragraph(pdf, text):
    pdf.set_font("DejaVu", "", 10.5)
    pdf.set_text_color(*BODY)
    pdf.multi_cell(0, 6.2, text)
    pdf.ln(2.5)


def _write_document(pdf, title, intro, sections):
    pdf.add_page()
    _heading(pdf, title, 16)
    pdf.set_draw_color(*GREEN)
    pdf.set_line_width(0.6)
    pdf.line(20, pdf.get_y(), 70, pdf.get_y())
    pdf.set_line_width(0.2)
    pdf.ln(6)
    if intro:
        _intro(pdf, intro)
    for section in sections:
        heading = section.get("heading", "")
        if heading:
            _heading(pdf, heading, 12)
        for paragraph in section.get("paragraphs", []):
            _paragraph(pdf, paragraph)
        pdf.ln(1.5)


def _cover(pdf, site, legal, year):
    pdf.add_page()
    pdf.set_top_margin(20)

    pdf.set_fill_color(*NAVY)
    pdf.rect(0, 0, 210, 88, "F")
    pdf.set_fill_color(*GREEN)
    pdf.rect(0, 88, 210, 5, "F")

    if pdf.logo_path:
        pdf.set_fill_color(255, 255, 255)
        pdf.rect(75, 22, 60, 28, "F")
        pdf.image(str(pdf.logo_path), x=80, y=25, w=50)

    pdf.set_y(108)
    pdf.set_font("DejaVu", "", 11)
    pdf.set_text_color(*GREEN)
    pdf.cell(0, 8, "OFFICIAL DOCUMENT", align="C", new_x="LMARGIN", new_y="NEXT")
    pdf.ln(4)
    pdf.set_font("DejaVu", "B", 26)
    pdf.set_text_color(*NAVY)
    pdf.multi_cell(0, 12, site.get("name", "AfriCloud Institute"), align="C")
    pdf.ln(2)
    pdf.set_font("DejaVu", "", 16)
    pdf.set_text_color(*NAVY_MID)
    pdf.multi_cell(0, 9, "Legal policies and statements", align="C")

    pdf.ln(10)
    pdf.set_fill_color(*SOFT)
    box_y = pdf.get_y()
    pdf.rect(36, box_y, 138, 28, "F")
    pdf.set_y(box_y + 6)
    pdf.set_font("DejaVu", "", 10)
    pdf.set_text_color(*BODY)
    details = [
        f"Last reviewed  {year}",
        site.get("location", ""),
        f"{site.get('email', '')}  ·  {site.get('phone_display', '')}",
    ]
    pdf.multi_cell(0, 5.5, "\n".join(item for item in details if item), align="C")

    pdf.set_y(box_y + 38)
    pdf.set_font("DejaVu", "I", 10.5)
    pdf.set_text_color(*BODY)
    pdf.set_x(28)
    pdf.multi_cell(154, 6.2, legal.get("intro", ""), align="C")
    pdf.set_top_margin(32)


def build_legal_pdf(site, legal, security):
    pdf = LegalPDF(site)
    year = datetime.now().year
    _cover(pdf, site, legal, year)

    pdf.add_page()
    _heading(pdf, "Contents", 16)
    pdf.set_draw_color(*GREEN)
    pdf.set_line_width(0.6)
    pdf.line(20, pdf.get_y(), 70, pdf.get_y())
    pdf.set_line_width(0.2)
    pdf.ln(8)

    items = [policy["title"] for policy in legal.get("policies", [])]
    items.append(security.get("title", "Information Security Statement"))
    for index, title in enumerate(items, start=1):
        pdf.set_fill_color(*SOFT)
        y = pdf.get_y()
        pdf.rect(20, y, 170, 10, "F")
        pdf.set_xy(24, y + 2)
        pdf.set_font("DejaVu", "B", 10)
        pdf.set_text_color(*GREEN)
        pdf.cell(10, 6, f"{index:02d}")
        pdf.set_font("DejaVu", "", 11)
        pdf.set_text_color(*NAVY)
        pdf.cell(0, 6, title)
        pdf.set_y(y + 13)

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
