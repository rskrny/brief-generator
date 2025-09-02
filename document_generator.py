import json
from fpdf import FPDF
from typing import Any, Dict, List

PADDING = 10
SECTION_SPACING = 4
PARA_SPACING = 5

class PDF(FPDF):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.set_auto_page_break(auto=True, margin=15)
        self.add_page()
        self.add_font("DejaVu", "", fname="DejaVuSans.ttf", uni=True)
        self.set_font("DejaVu", size=12)

def _safe_multi_cell(pdf: FPDF, w, h, txt, border=0, align="", fill=False):
    pdf.multi_cell(w, h, txt, border=border, align=align, fill=fill)

def _wrap_text(pdf: FPDF, max_width: float, text: str) -> List[str]:
    words = text.split(" ")
    lines, current = [], ""
    for word in words:
        test_line = (current + " " + word).strip()
        if pdf.get_string_width(test_line) <= max_width:
            current = test_line
        else:
            lines.append(current)
            current = word
    if current:
        lines.append(current)
    return lines

def _render_list_item(pdf: FPDF, text: str, bullet: str = "-") -> None:
    line_height = 6
    bullet_str = f"{bullet} "
    indent = pdf.get_string_width(bullet_str)
    epw = getattr(pdf, "epw", pdf.w - 2 * pdf.l_margin) - PADDING
    max_width = epw - indent
    lines = _wrap_text(pdf, max_width, text)

    pdf.set_x(pdf.l_margin + PADDING / 2)
    _safe_multi_cell(pdf, max_width + indent, line_height, bullet_str + lines[0])

    for line in lines[1:]:
        pdf.set_x(pdf.l_margin + indent + PADDING / 2)
        _safe_multi_cell(pdf, max_width, line_height, line)

def _render_table(pdf: FPDF, headers: List[str], rows: List[List[str]]) -> None:
    col_width = (pdf.epw - PADDING) / len(headers)
    pdf.set_font("DejaVu", "B", 11)
    for header in headers:
        pdf.cell(col_width, 8, header, border=1)
    pdf.ln()
    pdf.set_font("DejaVu", "", 10)
    for row in rows:
        for item in row:
            pdf.multi_cell(col_width, 6, str(item), border=1, ln=3, max_line_height=pdf.font_size)
        pdf.ln()

def make_brief_pdf(
    *, analyzer: Dict[str, Any], script: Dict[str, Any], output_path: str
) -> None:
    pdf = PDF(format="A4")

    pdf.set_font("DejaVu", "B", 16)
    pdf.cell(0, 10, "AI-Generated Influencer Brief", ln=True, align="C")
    pdf.ln(5)
    pdf.set_font("DejaVu", size=12)

    # Summary
    summary_text = analyzer.get("summary", "")
    for line in summary_text.splitlines():
        if line.startswith("# "):
            pdf.set_font("DejaVu", size=16)
            pdf.set_x(pdf.l_margin + PADDING / 2)
            _safe_multi_cell(pdf, pdf.epw - PADDING, 8, line[2:].strip())
            pdf.set_font("DejaVu", size=12)
        elif line.startswith("## "):
            pdf.set_font("DejaVu", size=14)
            pdf.set_x(pdf.l_margin + PADDING / 2)
            _safe_multi_cell(pdf, pdf.epw - PADDING, 7, line[3:].strip())
            pdf.set_font("DejaVu", size=12)
        elif line.startswith("### "):
            pdf.set_font("DejaVu", size=12)
            pdf.set_x(pdf.l_margin + PADDING / 2)
            _safe_multi_cell(pdf, pdf.epw - PADDING, 6, line[4:].strip())
        elif line.startswith("- "):
            _render_list_item(pdf, line[2:].strip())
        elif line.strip():
            pdf.set_x(pdf.l_margin + PADDING / 2)
            _safe_multi_cell(pdf, pdf.epw - PADDING, 6, line)
        pdf.ln(PARA_SPACING)

    pdf.ln(SECTION_SPACING)

    # Storyboard
    storyboard_text = analyzer.get("storyboard", "")
    for line in storyboard_text.splitlines():
        if line.startswith("# "):
            pdf.set_font("DejaVu", size=16)
            pdf.set_x(pdf.l_margin + PADDING / 2)
            _safe_multi_cell(pdf, pdf.epw - PADDING, 8, line[2:].strip())
            pdf.set_font("DejaVu", size=12)
        elif line.startswith("## "):
            pdf.set_font("DejaVu", size=14)
            pdf.set_x(pdf.l_margin + PADDING / 2)
            _safe_multi_cell(pdf, pdf.epw - PADDING, 7, line[3:].strip())
            pdf.set_font("DejaVu", size=12)
        elif line.startswith("### "):
            pdf.set_font("DejaVu", size=12)
            pdf.set_x(pdf.l_margin + PADDING / 2)
            _safe_multi_cell(pdf, pdf.epw - PADDING, 6, line[4:].strip())
        elif line.startswith("- "):
            _render_list_item(pdf, line[2:].strip())
        elif line.strip():
            pdf.set_x(pdf.l_margin + PADDING / 2)
            _safe_multi_cell(pdf, pdf.epw - PADDING, 6, line)
        pdf.ln(PARA_SPACING)

    pdf.ln(SECTION_SPACING)

    # Scene-by-scene table
    scenes = script.get("scenes", [])
    if scenes:
        headers = scenes[0].keys()
        rows = [list(scene.values()) for scene in scenes]
        pdf.set_x(pdf.l_margin + PADDING / 2)
        _render_table(pdf, headers, rows)
        pdf.ln(SECTION_SPACING)
        pdf.set_x(pdf.l_margin + PADDING / 2)

    pdf.output(output_path)

def brief_from_json_strings(analyzer_json: str, script_json: str, output_path: str) -> None:
    """Wrapper for compatibility with app.py: takes JSON strings, parses, and calls make_brief_pdf."""
    analyzer = json.loads(analyzer_json)
    script = json.loads(script_json)
    make_brief_pdf(analyzer=analyzer, script=script, output_path=output_path)
