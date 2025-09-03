# document_generator.py
# Converts Analyzer JSON + Script JSON + Product Facts into a director-grade Markdown brief
# and a two-page PDF (summary + storyboard). Compatible with your app.py calls.

from __future__ import annotations

from typing import Dict, Any, List, Optional, Tuple
import json
import re
import math
from pathlib import Path

from PIL import Image
from fpdf import FPDF
from fpdf.errors import FPDFException

# ---------- Formatting constants ----------
_TABLE_SEPARATOR_RE = re.compile(r"^\|(?:\s*:?-+:?\s*\|)+\s*$")
_IMAGE_CELL_HEIGHT = 30  # fixed height for images in table cells
_IMAGE_EXTENSIONS = {".png", ".jpg", ".jpeg", ".gif", ".bmp"}

PADDING = 1          # small global padding
CELL_PADDING = 2     # padding inside table cells

# ---------- Small helpers ----------
def _num(v: Any) -> Optional[float]:
    try:
        if v is None:
            return None
        return float(v)
    except Exception:
        return None

def _append_list(lines: List[str], items: List[str], bullet: str = "- ") -> None:
    if not items:
        lines.append("> (none)")
        return
    for it in items:
        it = "" if it is None else str(it)
        if it.strip():
            lines.append(f"{bullet}{it}")

def _get_image_path(cell: Any) -> Optional[str]:
    if isinstance(cell, dict) and "image" in cell:
        return str(cell["image"])
    if isinstance(cell, (str, Path)):
        path = Path(cell)
        if path.suffix.lower() in _IMAGE_EXTENSIONS:
            return str(path)
    return None

# ==========================================================
# Public: Markdown builder
# ==========================================================
def make_brief_markdown(
    *,
    analyzer: Dict[str, Any],
    script: Dict[str, Any],
    product_facts: Dict[str, Any],
    title: str = "AI-Generated Influencer Brief (Director Mode)",
) -> str:
    """
    Build a single Markdown document summarizing the analysis and the new script.
    """
    lines: List[str] = []

    # Header
    brand = product_facts.get("brand") or ""
    product = product_facts.get("product_name") or ""
    lines.append(f"# {title}")
    if brand or product:
        lines.append(f"**Product**: {brand} {product}".strip())
    lines.append("")

    # Product facts
    lines.append("## Product Facts (Claims Whitelist)")
    _append_list(lines, product_facts.get("approved_claims", []), bullet="- ")
    if product_facts.get("required_disclaimers"):
        lines.append("\n**Required Disclaimers**")
        _append_list(lines, product_facts.get("required_disclaimers", []), bullet="- ")
    if product_facts.get("forbidden"):
        lines.append("\n**Forbidden / Restricted Claims**")
        _append_list(lines, product_facts.get("forbidden", []), bullet="- ")
    lines.append("")

    # Analyzer summary
    lines.append("## Reference Video — Director Breakdown")
    lines.extend(_analyzer_global_summary(analyzer))
    lines.append("")
    lines.extend(_influencer_dna_summary(analyzer))
    lines.append("")
    lines.extend(_edit_grammar_summary(analyzer))
    lines.append("")
    lines.extend(_beats_table(analyzer))
    lines.append("")
    lines.extend(_scenes_table(analyzer))
    lines.append("")

    # Script plan
    lines.append("## New Script for Target Brand/Product")
    lines.extend(_script_opening(script))
    lines.append("")
    lines.extend(_script_scenes_table(script))
    lines.append("")
    lines.extend(_cta_options(script))
    lines.append("")

    # Quality checklist & compliance
    lines.append("## Quality Checklist & Compliance")
    lines.extend(_script_checklist(script))
    lines.append("")
    lines.extend(_compliance_block(analyzer, product_facts))
    lines.append("")

    return "\n".join(lines)

# ==========================================================
# Public: PDF builder
# ==========================================================
def make_brief_pdf(
    *,
    analyzer: Dict[str, Any],
    script: Dict[str, Any],
    product_facts: Dict[str, Any],
    title: str = "AI-Generated Influencer Brief (Director Mode)",
    orientation: Optional[str] = "P",
) -> bytes:
    """
    Generate a two-page PDF with a summary and a storyboard table.
    """
    # Build content lines from Markdown helpers
    brand = product_facts.get("brand") or ""
    product = product_facts.get("product_name") or ""
    
    summary_lines = [f"# {title}"]
    if brand or product:
        summary_lines.append(f"**Product**: {brand} {product}".strip())
    summary_lines.append("")
    summary_lines.append("## Product Facts (Claims Whitelist)")
    _append_list(summary_lines, product_facts.get("approved_claims", []), bullet="- ")
    if product_facts.get("required_disclaimers"):
        summary_lines.append("\n**Required Disclaimers**")
        _append_list(summary_lines, product_facts.get("required_disclaimers", []), bullet="- ")
    if product_facts.get("forbidden"):
        summary_lines.append("\n**Forbidden / Restricted Claims**")
        _append_list(summary_lines, product_facts.get("forbidden", []), bullet="- ")
    summary_lines.append("\n## Reference Video — Director Breakdown")
    summary_lines.extend(_analyzer_global_summary(analyzer))
    
    storyboard_lines = _scenes_table(analyzer) # This returns a Markdown table

    class BriefPDF(FPDF):
        def footer(self) -> None:
            self.set_y(-15)
            self.set_font(self.font_family, size=8)
            self.cell(0, 10, f"{self.page_no()}/{{nb}}", align="C")

    pdf = BriefPDF(orientation=(orientation or "P")[0].upper())
    pdf.set_margins(15, 15, 15)
    pdf.set_auto_page_break(auto=True, margin=15)
    pdf.alias_nb_pages()

    # Add Unicode font support
    font_path = Path(__file__).parent / "fonts" / "DejaVuSans.ttf"
    bold_path = Path(__file__).parent / "fonts" / "DejaVuSans-Bold.ttf"
    if font_path.exists():
        pdf.add_font("DejaVu", "", str(font_path), uni=True)
        pdf.add_font("DejaVu", "B", str(bold_path) if bold_path.exists() else str(font_path), uni=True)
        pdf.set_font("DejaVu", size=12)
    else:
        pdf.set_font("Helvetica", size=12)

    # Render summary page
    pdf.add_page()
    _render_markdown_lines(pdf, summary_lines)

    # Render storyboard page
    pdf.add_page()
    _render_markdown_lines(pdf, storyboard_lines)

    pdf_bytes = pdf.output()
    return bytes(pdf_bytes)

# ==========================================================
# Compatibility wrapper for app.py
# ==========================================================
def brief_from_json_strings(
    *,
    analyzer_json_str: str,
    script_json_str: str,
    product_facts: Dict[str, Any],
    title: str = "AI-Generated Influencer Brief (Director Mode)",
) -> str:
    analyzer = json.loads(analyzer_json_str or "{}")
    script = json.loads(script_json_str or "{}")
    return make_brief_markdown(
        analyzer=analyzer, script=script, product_facts=product_facts, title=title
    )
    
# ==========================================================
# PDF Rendering Logic
# ==========================================================
def _render_markdown_lines(pdf: FPDF, lines: List[str]):
    """Renders a list of markdown-like strings to the PDF."""
    i = 0
    while i < len(lines):
        line = lines[i]

        if line.startswith("|") and i + 1 < len(lines) and _TABLE_SEPARATOR_RE.match(lines[i + 1]):
            headers, rows, i = _parse_table_block(lines, i)
            _render_table(pdf, headers, rows)
            continue
        
        style = ""
        size = 12
        if line.startswith("# "):
            line = line[2:]
            size = 18
            style = "B"
        elif line.startswith("## "):
            line = line[3:]
            size = 16
            style = "B"
        elif line.startswith("### "):
            line = line[4:]
            size = 14
            style = "B"
        
        pdf.set_font(pdf.font_family, style, size)
        
        if line.startswith("- "):
            _render_list_item(pdf, line[2:])
        elif "**" in line:
            _render_bold_inline(pdf, line)
        else:
            pdf.multi_cell(0, 6, line)
        
        pdf.set_font(pdf.font_family, size=12) # Reset font
        pdf.ln(2)
        i += 1

def _render_bold_inline(pdf: FPDF, text: str):
    """Renders text with inline bold markdown (**text**)."""
    parts = re.split(r'(\*\*.*?\*\*)', text)
    for part in parts:
        if part.startswith('**') and part.endswith('**'):
            pdf.set_font(pdf.font_family, "B", pdf.font_size_pt)
            pdf.write(pdf.font_size * 0.5, part[2:-2])
            pdf.set_font(pdf.font_family, "", pdf.font_size_pt)
        else:
            pdf.write(pdf.font_size * 0.5, part)
    pdf.ln()


def _render_list_item(pdf: FPDF, text: str):
    """Renders a bulleted list item with proper wrapping."""
    bullet = "\u2022"
    bullet_width = pdf.get_string_width(bullet + " ")
    
    x_before = pdf.get_x()
    y_before = pdf.get_y()
    
    pdf.cell(bullet_width, 6, bullet)
    pdf.set_xy(x_before + bullet_width, y_before)
    
    _render_bold_inline(pdf, text)

    pdf.set_x(x_before)


def _parse_table_block(lines: List[str], start: int) -> Tuple[List[str], List[List[str]], int]:
    header = [c.strip() for c in lines[start].strip().strip("|").split("|")]
    i = start + 2
    rows = []
    while i < len(lines) and lines[i].startswith("|"):
        rows.append([c.strip() for c in lines[i].strip().strip("|").split("|")])
        i += 1
    return header, rows, i

def _render_table(pdf: FPDF, headers: List[str], rows: List[List[Any]]):
    """Renders a table with content-aware column widths and proper text wrapping."""
    line_height = 6
    font_size = 9
    
    # Set font for table content
    pdf.set_font(pdf.font_family, size=font_size)
    
    num_cols = len(headers)
    effective_page_width = pdf.epw - (num_cols * CELL_PADDING) # Total width available for text

    # --- Calculate optimal column widths based on content ---
    col_widths = [1/num_cols] * num_cols # Default to equal widths

    # Use a simple heuristic: calculate widths based on longest word in each column
    all_content = [headers] + rows
    max_word_widths = [0] * num_cols
    for row_data in all_content:
        for i, cell_text in enumerate(row_data):
            words = str(cell_text).split()
            if words:
                longest_word = max(words, key=lambda w: pdf.get_string_width(w))
                max_word_widths[i] = max(max_word_widths[i], pdf.get_string_width(longest_word))
    
    total_max_word_width = sum(max_word_widths)
    if total_max_word_width > 0:
        # Distribute width based on proportion of longest words
        col_widths = [(w / total_max_word_width) * effective_page_width for w in max_word_widths]
    else:
        # Fallback if no content
        col_widths = [effective_page_width / num_cols] * num_cols

    # --- Render Header ---
    pdf.set_font(pdf.font_family, "B", font_size)
    y_before_header = pdf.get_y()
    x_pos = pdf.get_x()
    for i, header in enumerate(headers):
        pdf.multi_cell(col_widths[i] + CELL_PADDING, line_height, header, border=1, align='C', ln=3)
        x_pos += col_widths[i] + CELL_PADDING
        pdf.set_xy(x_pos, y_before_header)
    pdf.ln(line_height)
    
    # --- Render Rows ---
    pdf.set_font(pdf.font_family, "", font_size)
    for row in rows:
        y_before_row = pdf.get_y()
        max_row_height = line_height

        # Calculate the required height for this row
        for i, cell_text in enumerate(row):
            lines = pdf.multi_cell(col_widths[i], line_height, str(cell_text), split_only=True)
            max_row_height = max(max_row_height, len(lines) * line_height)

        if pdf.get_y() + max_row_height > pdf.page_break_trigger:
            pdf.add_page()
            
        x_pos = pdf.get_x()
        for i, cell_text in enumerate(row):
            pdf.rect(x_pos, pdf.get_y(), col_widths[i] + CELL_PADDING, max_row_height)
            pdf.multi_cell(col_widths[i] + CELL_PADDING, line_height, str(cell_text), ln=3, align='L')
            x_pos += col_widths[i] + CELL_PADDING
            pdf.set_xy(x_pos, pdf.get_y() - (len(pdf.multi_cell(col_widths[i], line_height, str(cell_text), split_only=True)) * line_height))
        
        pdf.set_y(y_before_row + max_row_height)
        pdf.ln(0)
        
    # Reset font size after table
    pdf.set_font(pdf.font_family, size=12)

# ---------- Markdown Content Generation Helpers ----------

def _analyzer_global_summary(analyzer: Dict[str, Any]) -> List[str]:
    vm = analyzer.get("video_metadata", {})
    gs = analyzer.get("global_style", {})
    music = gs.get("music", {})
    duration = _num(vm.get("duration_s"))

    lines = [
        f"**Platform**: {vm.get('platform', 'N/A')}",
        f"**Duration**: {duration:.2f}s" if duration is not None else "**Duration**: N/A",
        f"**Aspect Ratio**: {vm.get('aspect_ratio', 'N/A')}",
        "",
        f"**Hook Type(s)**: {', '.join(gs.get('hook_type', ['N/A']))}",
        f"**Promise**: {gs.get('promise') or 'N/A'}",
        f"**Payoff**: {gs.get('payoff') or 'N/A'}",
        f"**Core CTA**: {gs.get('cta_core') or 'N/A'}",
        "",
        f"**Music**: {music.get('genre', '')}, {music.get('bpm', '')} BPM",
    ]
    if gs.get("risk_flags"):
        lines.append(f"**Risk Flags**: {', '.join(gs.get('risk_flags'))}")
    return lines

def _influencer_dna_summary(analyzer: Dict[str, Any]) -> List[str]:
    dna = analyzer.get("influencer_DNA", {})
    delivery = dna.get("delivery", {})
    editing = dna.get("editing_style", {})
    lines = ["### Influencer DNA (Delivery Fingerprint)"]
    lines.append(f"**Persona Tags**: {', '.join(dna.get('persona_tags', ['N/A']))}")
    # ... (rest of the DNA summary)
    return lines

def _edit_grammar_summary(analyzer: Dict[str, Any]) -> List[str]:
    eg = (analyzer.get("global_style") or {}).get("edit_grammar") or {}
    lines = ["### Edit Grammar & Rhythm"]
    lines.append(f"**Average Cut Interval**: {eg.get('avg_cut_interval_s','?')}s")
    # ... (rest of edit grammar)
    return lines
    
def _beats_table(analyzer: Dict[str, Any]) -> List[str]:
    beats = analyzer.get("beats", []) or []
    lines = ["### Beat Grid"]
    if not beats:
        return lines + ["", "> No beats detected."]
    lines.extend(["", "| t (s) | type | note |", "|---:|---|---|"])
    for b in beats:
        t = _num(b.get("t"))
        lines.append(f"| {t:.2f} | {b.get('type','')} | {b.get('note','')} |" if t is not None else f"| | {b.get('type','')} | {b.get('note','')} |")
    return lines

def _scenes_table(analyzer: Dict[str, Any]) -> List[str]:
    scenes = analyzer.get("scenes", []) or []
    lines = ["### Scene-by-Scene (Reference Video)"]
    if not scenes:
        return lines + ["", "> No scenes provided."]
    lines.extend([
        "",
        "| Timestamp | Shot Type | Framing | Action | Dialogue | On-Screen Text | Reference Thumbnail Screenshot |",
        "|---|---|---|---|---|---|---|",
    ])
    for s in scenes:
        start, end = _num(s.get("start_s")), _num(s.get("end_s"))
        ts = f"{start:.2f}–{end:.2f}" if start is not None and end is not None else ""
        lines.append(f"| {ts} | {s.get('shot_type', '')} | {s.get('framing', '')} | {s.get('action', '')} | {s.get('dialogue', '')} | {s.get('on_screen_text', '')} | {s.get('screenshot_path', '')} |")
    return lines

def _script_opening(script: Dict[str, Any]) -> List[str]:
    try:
        opening = script["script"]["opening_hook"]
        return ["### Opening", "", opening.get("dialogue", "")]
    except KeyError:
        return ["> No opening section defined."]

def _script_scenes_table(script: Dict[str, Any]) -> List[str]:
    try:
        scenes = script["script"]["scenes"]
        if not scenes: return ["> No generated scenes."]
        lines = ["### Generated Scenes", "", "| # | Action | Dialogue | On-Screen Text |", "|---:|---|---|---|"]
        for i, s in enumerate(scenes, 1):
            ost = "; ".join([item.get("text", "") for item in s.get("on_screen_text", [])])
            lines.append(f"| {i} | {s.get('action','')} | {s.get('dialogue_vo','')} | {ost} |")
        return lines
    except KeyError:
        return ["> Invalid script format."]

def _cta_options(script: Dict[str, Any]) -> List[str]:
    try:
        ctas = script["script"]["cta_options"]
        if not ctas: return []
        lines = ["### CTA Options"]
        for cta in ctas:
            lines.append(f"- **Variant {cta.get('variant', '')}:** {cta.get('dialogue', '')}")
        return lines
    except KeyError:
        return []

def _script_checklist(script: Dict[str, Any]) -> List[str]:
    try:
        checklist = script.get("checklist", {})
        if not checklist: return ["> (no checklist)"]
        return [f"- {k.replace('_', ' ').title()}: {'✅' if v else '❌'}" for k, v in checklist.items()]
    except Exception:
        return ["> Could not parse checklist."]

def _compliance_block(analyzer: Dict[str, Any], product_facts: Dict[str, Any]) -> List[str]:
    lines = ["### Compliance Notes"]
    rf = (analyzer.get("global_style") or {}).get("risk_flags", [])
    if rf: lines.append(f"**Risk Flags Detected**: {', '.join(rf)}")
    if product_facts.get("required_disclaimers"):
        lines.append("**Required Disclaimers**:")
        lines.extend([f"- {d}" for d in product_facts["required_disclaimers"]])
    return lines
