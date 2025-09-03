# document_generator.py
# Converts Analyzer JSON + Script JSON + Product Facts into a director-grade Markdown brief
# and a two-page PDF (summary + storyboard) with a focus on professional, readable design.

from __future__ import annotations
from typing import Dict, Any, List, Optional
import json
from pathlib import Path
from fpdf import FPDF

# --- Configuration ---
PRIMARY_COLOR = (240, 240, 240)
BORDER_COLOR = (200, 200, 200)
FONT_FAMILY = "DejaVu"

# ==========================================================
# Public-Facing Functions (called by app.py)
# ==========================================================

def make_brief_markdown(
    *,
    analyzer: Dict[str, Any],
    script: Dict[str, Any],
    product_facts: Dict[str, Any],
    title: str = "AI-Generated Influencer Brief",
) -> str:
    """Builds a single Markdown document from the AI-generated data."""
    lines = [f"# {title}"]
    brand = product_facts.get("brand", "")
    product = product_facts.get("product_name", "")
    if brand or product:
        lines.append(f"**Product**: {brand} {product}".strip())
    lines.append("\n" + "="*20 + "\n")
    lines.extend(_get_product_facts_md(product_facts))
    lines.extend(_get_analyzer_summary_md(analyzer))
    lines.extend(_get_script_scenes_md(script))
    return "\n".join(lines)

def make_brief_pdf(
    *,
    analyzer: Dict[str, Any],
    script: Dict[str, Any],
    product_facts: Dict[str, Any],
    title: str = "AI-Generated Influencer Brief",
    orientation: Optional[str] = "P",
) -> bytes:
    """Generates a professional, readable PDF brief."""
    class BriefPDF(FPDF):
        def footer(self) -> None:
            self.set_y(-15)
            self.set_font(FONT_FAMILY, "I", 8)
            self.set_text_color(128)
            self.cell(0, 10, f"Page {self.page_no()}/{{nb}}", 0, 0, "C")

    pdf = BriefPDF(orientation=(orientation or "P")[0].upper(), unit="mm", format="A4")
    _setup_pdf(pdf)

    # --- Page 1: Summary in a single, clean column ---
    pdf.add_page()
    _draw_title(pdf, title, product_facts)
    _draw_info_section(pdf, "Product Facts", _get_product_facts_md(product_facts))
    _draw_info_section(pdf, "Reference Video Breakdown", _get_analyzer_summary_md(analyzer))
    
    # --- Page 2: Storyboard ---
    pdf.add_page()
    _draw_storyboard_table(pdf, script, "Generated Script Storyboard")

    return bytes(pdf.output())

def brief_from_json_strings(
    *,
    analyzer_json_str: str,
    script_json_str: str,
    product_facts: Dict[str, Any],
    title: str = "AI-Generated Influencer Brief",
) -> str:
    """Compatibility wrapper for app.py."""
    analyzer = json.loads(analyzer_json_str or "{}")
    script = json.loads(script_json_str or "{}")
    return make_brief_markdown(
        analyzer=analyzer, script=script, product_facts=product_facts, title=title
    )

# ==========================================================
# PDF Drawing Helpers
# ==========================================================

def _setup_pdf(pdf: FPDF):
    font_path = Path(__file__).parent / "fonts" / "DejaVuSans.ttf"
    if font_path.exists():
        pdf.add_font(FONT_FAMILY, "", str(font_path), uni=True)
        pdf.add_font(FONT_FAMILY, "B", str(font_path), uni=True)
        pdf.add_font(FONT_FAMILY, "I", str(font_path), uni=True)
    pdf.set_font(FONT_FAMILY, size=10)
    pdf.set_margins(15, 15, 15)
    pdf.set_auto_page_break(auto=True, margin=15)
    pdf.alias_nb_pages()

def _draw_title(pdf: FPDF, title: str, product_facts: Dict[str, Any]):
    pdf.set_font(FONT_FAMILY, "B", 20)
    pdf.cell(0, 10, title, 0, 1, "C")
    brand = product_facts.get("brand", "")
    product = product_facts.get("product_name", "")
    subtitle = f"Product: {brand} {product}".strip()
    pdf.set_font(FONT_FAMILY, "", 12)
    pdf.cell(0, 8, subtitle, 0, 1, "C")
    pdf.ln(10)

def _draw_info_section(pdf: FPDF, title: str, content_lines: List[str]):
    """Draws a full-width information section with a title and content."""
    # Check if there is enough space, add a new page if needed
    required_height = 12 + len(content_lines) * 5 # Rough estimate
    if pdf.get_y() + required_height > pdf.page_break_trigger:
        pdf.add_page()

    pdf.set_font(FONT_FAMILY, "B", 12)
    pdf.cell(0, 8, title, 0, 1)
    pdf.line(pdf.get_x(), pdf.get_y(), pdf.get_x() + pdf.w - pdf.l_margin - pdf.r_margin, pdf.get_y())
    pdf.ln(3)

    pdf.set_font(FONT_FAMILY, "", 9)
    for line in content_lines[1:]: # Skip the title line from the markdown generator
        if line.startswith("**"):
            # Handle bold lead-in text like "**Approved Claims:**"
            parts = line.split("**")
            pdf.set_font(FONT_FAMILY, "B")
            pdf.write(5, parts[1])
            pdf.set_font(FONT_FAMILY, "")
            pdf.write(5, parts[2] + "\n")
        elif line.startswith("- "):
            # Handle bullet points
            pdf.write(5, f"     •  {line[2:]}\n")
        elif line.strip():
            pdf.multi_cell(0, 5, line)
    pdf.ln(8)

def _draw_storyboard_table(pdf: FPDF, script: Dict[str, Any], title: str):
    pdf.set_font(FONT_FAMILY, "B", 14)
    pdf.cell(0, 10, title, 0, 1)
    pdf.ln(2)
    headers = ["#", "Action / Visuals", "Dialogue / VO", "On-Screen Text"]
    try:
        scenes = script["script"]["scenes"]
        rows = [[str(s.get("idx", i+1)), s.get("action", ""), s.get("dialogue_vo", ""), "; ".join(item.get("text", "") for item in s.get("on_screen_text", []))] for i, s in enumerate(scenes)]
    except (KeyError, TypeError):
        rows = [["", "Could not parse script scenes.", "", ""]]
    _render_table(pdf, headers, rows)

def _render_table(pdf: FPDF, headers: List[str], rows: List[List[str]]):
    line_height, font_size = 6, 9
    page_width = pdf.w - pdf.l_margin - pdf.r_margin
    col_widths = _calculate_col_widths(pdf, headers, rows, page_width, font_size)

    # --- Render Header ---
    pdf.set_font(FONT_FAMILY, "B", font_size)
    pdf.set_fill_color(*PRIMARY_COLOR)
    pdf.set_text_color(0)
    pdf.set_draw_color(*BORDER_COLOR)
    pdf.set_line_width(0.3)
    for i, header in enumerate(headers):
        pdf.cell(col_widths[i], line_height * 1.5, header, border=1, fill=True, align="C")
    pdf.ln()

    # --- Render Rows ---
    pdf.set_font(FONT_FAMILY, "", font_size)
    fill = False
    for row in rows:
        row_height = _calculate_row_height(pdf, row, col_widths, line_height)
        if pdf.get_y() + row_height > pdf.page_break_trigger:
            pdf.add_page()
            # Re-draw headers on new page
            pdf.set_font(FONT_FAMILY, "B", font_size)
            for i, header in enumerate(headers):
                pdf.cell(col_widths[i], line_height * 1.5, header, border=1, fill=True, align="C")
            pdf.ln()
            pdf.set_font(FONT_FAMILY, "", font_size)

        x_start, y_start = pdf.get_x(), pdf.get_y()
        
        if fill:
            pdf.set_fill_color(*PRIMARY_COLOR)
        else:
            pdf.set_fill_color(255) # White

        for i, cell in enumerate(row):
            pdf.set_xy(x_start + sum(col_widths[:i]), y_start)
            pdf.multi_cell(col_widths[i], line_height, str(cell), border="LR", fill=True, align="L")
        
        pdf.set_xy(x_start, y_start + row_height)
        pdf.line(x_start, y_start + row_height, x_start + sum(col_widths), y_start + row_height)
        fill = not fill

# ==========================================================
# Table Calculation & Markdown Helpers
# ==========================================================

def _calculate_col_widths(pdf: FPDF, headers: List[str], rows: List[List[str]], total_width: float, font_size: int) -> List[float]:
    """Calculates robust column widths based on content."""
    pdf.set_font(FONT_FAMILY, size=font_size)
    num_cols = len(headers)
    
    # Start with a default ratio for storyboard
    if num_cols == 4: 
        ratios = [0.05, 0.40, 0.30, 0.25]
    else:
        ratios = [1/num_cols] * num_cols
        
    col_widths = [total_width * r for r in ratios]

    # Adjust based on the longest word in each column to prevent extreme cutoff
    # This ensures that even with a small ratio, a column is wide enough for its largest single word
    all_content = [headers] + rows
    for i in range(num_cols):
        max_word_width = 0
        for row in all_content:
            if i < len(row):
                words = str(row[i]).split()
                if not words: continue
                longest_word = max(words, key=lambda w: pdf.get_string_width(w))
                max_word_width = max(max_word_width, pdf.get_string_width(longest_word))
        
        min_width = max_word_width + 4 # Add padding
        if col_widths[i] < min_width:
            col_widths[i] = min_width

    # Normalize widths to fit the total page width after adjustments
    current_total_width = sum(col_widths)
    if current_total_width > 0:
        scale_factor = total_width / current_total_width
        col_widths = [w * scale_factor for w in col_widths]

    return col_widths

def _calculate_row_height(pdf: FPDF, row: List[str], col_widths: List[float], line_height: float) -> float:
    max_lines = 1
    for i, cell in enumerate(row):
        # The -2 provides a small internal padding for the cell
        if i < len(col_widths):
            lines = pdf.multi_cell(col_widths[i] - 2, line_height, str(cell), split_only=True)
            max_lines = max(max_lines, len(lines))
    return max_lines * line_height

def _get_product_facts_md(product_facts: Dict[str, Any]) -> List[str]:
    lines = ["**Product Facts**"]
    lines.append("\n**Approved Claims:**")
    for claim in product_facts.get("approved_claims", ["None provided."]): lines.append(f"- {claim}")
    lines.append("\n**Forbidden Claims:**")
    for claim in product_facts.get("forbidden", ["None provided."]): lines.append(f"- {claim}")
    lines.append("\n**Required Disclaimers:**")
    for dis in product_facts.get("required_disclaimers", ["None provided."]): lines.append(f"- {dis}")
    return lines

def _get_analyzer_summary_md(analyzer: Dict[str, Any]) -> List[str]:
    vm = analyzer.get("video_metadata", {})
    gs = analyzer.get("global_style", {})
    lines = ["**Reference Video Breakdown**"]
    lines.append(f"**Platform:** {vm.get('platform', 'N/A')}")
    lines.append(f"**Duration:** {vm.get('duration_s', 'N/A')}s")
    lines.append(f"**Hook Type:** {', '.join(gs.get('hook_type', ['N/A']))}")
    lines.append(f"**Core CTA:** {gs.get('cta_core', 'N/A')}")
    return lines

def _get_script_scenes_md(script: Dict[str, Any]) -> List[str]:
    try:
        scenes = script["script"]["scenes"]
        lines = ["**Generated Script**"]
        for s in scenes:
            lines.append(f"\n**Scene {s.get('idx', '')}**")
            lines.append(f"- **Action:** {s.get('action', '')}")
            lines.append(f"- **Dialogue:** {s.get('dialogue_vo', '')}")
            ost = "; ".join(item.get("text", "") for item in s.get("on_screen_text", []))
            lines.append(f"- **On-Screen Text:** {ost}")
        return lines
    except (KeyError, TypeError):
        return ["**Generated Script**", "Could not parse script scenes."]
