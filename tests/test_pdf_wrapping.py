import io
from pathlib import Path
import sys

from fpdf import FPDF
from pdfminer.high_level import extract_pages
from pdfminer.layout import LTTextLine

sys.path.append(str(Path(__file__).resolve().parent.parent))
from document_generator import _safe_multi_cell, _render_list_item, _render_table


def _iter_text_lines(layout_obj):
    from pdfminer.layout import LTTextContainer, LTFigure

    if isinstance(layout_obj, LTTextLine):
        yield layout_obj
    elif isinstance(layout_obj, (LTTextContainer, LTFigure)):
        for child in layout_obj:
            yield from _iter_text_lines(child)


def assert_pdf_lines_fit(page_iter):
    for page in page_iter:
        width = page.width
        for line in _iter_text_lines(page):
            assert line.x1 <= width + 1  # allow tiny rounding tolerance


def test_long_unbroken_word_and_bullet_list():
    font_path = Path(__file__).resolve().parent.parent / "fonts" / "DejaVuSans.ttf"

    pdf = FPDF()
    pdf.add_font("DejaVu", "", str(font_path), uni=True)
    pdf.add_page()
    pdf.set_font("DejaVu", size=12)

    long_word = (
        "Lopadotemachoselachogaleokranioleipsanodrimhypotrimmatosilphioparaome"
        "litokatakechymenokichlepikossyphophattoperisteralektryonoptekefallio"
        "lagoiosiraiobaphetraganopterygon"
    )

    _safe_multi_cell(pdf, pdf.epw, 6, long_word)
    _render_list_item(pdf, long_word)

    pdf_bytes = bytes(pdf.output(dest="S"))
    assert_pdf_lines_fit(extract_pages(io.BytesIO(pdf_bytes)))


def test_narrow_table_columns_wrap():
    font_path = Path(__file__).resolve().parent.parent / "fonts" / "DejaVuSans.ttf"

    pdf = FPDF()
    pdf.add_font("DejaVu", "", str(font_path), uni=True)
    pdf.add_font("DejaVu", "B", str(font_path), uni=True)
    pdf.add_page()
    pdf.set_font("DejaVu", size=12)

    headers = [f"C{i}" for i in range(8)]
    long_word = "Supercalifragilisticexpialidocious" * 2
    rows = [[long_word for _ in headers]]

    _render_table(pdf, headers, rows)

    pdf_bytes = bytes(pdf.output(dest="S"))
    assert_pdf_lines_fit(extract_pages(io.BytesIO(pdf_bytes)))
