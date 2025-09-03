# document_generator.py
# Converts Analyzer JSON + Script JSON + Product Facts into a director-grade Markdown brief
# and a two-page PDF (summary + storyboard) with a focus on professional, readable design.

from __future__ import annotations
from typing import Dict, Any, List, Optional, Tuple
import json
import re
from pathlib import Path
from fpdf import FPDF

# --- Configuration ---
PRIMARY_COLOR = (240, 240, 240)  # Light gray for table headers and alternating rows
BORDER_COLOR = (200, 200, 200)   # Light gray for borders
FONT_FAMILY = "DejaVu"

# ==========================================================
# Public-Facing Functions (called by app.py)
# ==========================================================

def make_brief_markdown(
    *,
    analyzer: Dict[str, Any],
    script: Dict[str, Any],
    product_facts: Dict[str, Any],
    title: str = "AI-Generated Influencer Brief (Director Mode)",
) -> str:
    """Builds a single Markdown document from the AI-generated data."""
    lines = [f"# {title}"]
    brand = product_facts.get("brand") or ""
    product = product_facts.get("product_name") or ""
    if brand or product:
        lines.append(f"**Product**: {brand} {product}".strip())
    lines.append("\n" + "="*20 + "\n")

    # Add sections
    lines.extend(_get_product_facts_md(product_facts))
    lines.extend(_get_analyzer_summary_md(analyzer))
    lines.extend(_get_script_scenes_md(script))

    return "\n".join(lines)

def make_brief_pdf(
    *,
    analyzer: Dict[str, Any],
    script: Dict[str, Any],
    product_facts: Dict[str, Any],
    title: str = "AI-Generated Influencer Brief (Director Mode)",
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

    # --- Page 1: Summary ---
    pdf.add_page()
    _draw_title(pdf, title, product_facts)
    _draw_summary_columns(pdf, product_facts, analyzer)
    
    # --- Page 2: Storyboard ---
    pdf.add_page()
    _draw_storyboard_table(pdf, script, "Generated Script Storyboard")

    return bytes(pdf.output())

def brief_from_json_strings(
    *,
    analyzer_json_str: str,
    script_json_str: str,
    product_facts: Dict[str, Any],
    title: str = "AI-Generated Influencer Brief (Director Mode)",
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
    """Adds fonts and sets default margins."""
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
    """Draws the main title and subtitle for the brief."""
    pdf.set_font(FONT_FAMILY, "B", 20)
    pdf.cell(0, 10, title, 0, 1, "C")
    
    brand = product_facts.get("brand", "")
    product = product_facts.get("product_name", "")
    subtitle = f"Product: {brand} {product}".strip()
    
    pdf.set_font(FONT_FAMILY, "", 12)
    pdf.cell(0, 8, subtitle, 0, 1, "C")
    pdf.ln(10)

def _draw_summary_columns(pdf: FPDF, product_facts: Dict[str, Any], analyzer: Dict[str, Any]):
    """Draws the two-column summary for product facts and video analysis."""
    col_width = (pdf.w - pdf.l_margin - pdf.r_margin - 10) / 2
    
    # --- Column 1: Product Facts ---
    y_start_col1 = pdf.get_y()
    _draw_info_box(pdf, "Product Facts", _get_product_facts_md(product_facts), col_width)
    y_end_col1 = pdf.get_y()

    # --- Column 2: Reference Video Breakdown ---
    pdf.set_y(y_start_col1) # Reset Y to start of first column
    pdf.set_x(pdf.l_margin + col_width + 10)
    _draw_info_box(pdf, "Reference Video Breakdown", _get_analyzer_summary_md(analyzer), col_width)
    y_end_col2 = pdf.get_y()

    # Ensure the next section starts below the longest column
    pdf.set_y(max(y_end_col1, y_end_col2))
    pdf.set_x(pdf.l_margin)
    pdf.ln(10)

def _draw_info_box(pdf: FPDF, title: str, content_lines: List[str], width: float):
    """Draws a titled box with content."""
    pdf.set_font(FONT_FAMILY, "B", 12)
    pdf.cell(width, 8, title, 0, 1)
    pdf.line(pdf.get_x(), pdf.get_y(), pdf.get_x() + width, pdf.get_y())
    pdf.ln(2)

    pdf.set_font(FONT_FAMILY, "", 9)
    x_start = pdf.get_x()

    for line in content_lines[1:]: # Skip title line
        if line.startswith("**"):
            parts = line.split("**")
            pdf.set_font(FONT_FAMILY, "B")
            pdf.cell(pdf.get_string_width(parts[1]), 5, parts[1])
            pdf.set_font(FONT_FAMILY, "")
            pdf.multi_cell(width - pdf.get_string_width(parts[1]), 5, parts[2])
            pdf.set_x(x_start)
        elif line.strip():
             pdf.multi_cell(width, 5, line)
             pdf.set_x(x_start)
    pdf.ln(5)

def _draw_storyboard_table(pdf: FPDF, script: Dict[str, Any], title: str):
    """Draws the main storyboard table with professional styling."""
    pdf.set_font(FONT_FAMILY, "B", 14)
    pdf.cell(0, 10, title, 0, 1)
    pdf.ln(2)

    headers = ["#", "Action / Visuals", "Dialogue / VO", "On-Screen Text"]
    
    try:
        scenes = script["script"]["scenes"]
        rows = [
            [
                str(s.get("idx", i+1)),
                s.get("action", ""),
                s.get("dialogue_vo", ""),
                "; ".join(item.get("text", "") for item in s.get("on_screen_text", []))
            ] for i, s in enumerate(scenes)
        ]
    except (KeyError, TypeError):
        rows = [["", "Could not parse script scenes.", "", ""]]

    _render_table(pdf, headers, rows)

def _render_table(pdf: FPDF, headers: List[str], rows: List[List[str]]):
    """Renders a table with dynamic column widths and alternating row colors."""
    num_cols = len(headers)
    line_height = 6
    font_size = 9
    
    # Calculate column widths based on content
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
    pdf.set_fill_color(255) # Reset fill color for rows
    
    fill = False
    for row in rows:
        row_height = _calculate_row_height(pdf, row, col_widths, line_height)
        
        # Check for page break before drawing the row
        if pdf.get_y() + row_height > pdf.page_break_trigger:
            pdf.add_page()

        x_start = pdf.get_x()
        y_start = pdf.get_y()
        
        pdf.set_fill_color(*PRIMARY_COLOR if fill else 255, 255, 255)

        for i, cell in enumerate(row):
            pdf.set_xy(x_start + sum(col_widths[:i]), y_start)
            pdf.multi_cell(col_widths[i], line_height, str(cell), border="LR", fill=True, align="L")

        pdf.set_xy(x_start, y_start + row_height)
        pdf.line(x_start, y_start + row_height, x_start + sum(col_widths), y_start + row_height) # Bottom border
        fill = not fill

# ==========================================================
# Table Calculation Helpers
# ==========================================================

def _calculate_col_widths(pdf: FPDF, headers: List[str], rows: List[List[str]], total_width: float, font_size: int) -> List[float]:
    """Calculates optimal column widths based on content."""
    pdf.set_font(FONT_FAMILY, size=font_size)
    num_cols = len(headers)
    
    # Assign minimum widths based on headers
    min_widths = [pdf.get_string_width(h) + 6 for h in headers]
    
    # Assign weights based on average cell content length
    weights = [0] * num_cols
    all_content = [headers] + rows
    for row in all_content:
        for i, cell in enumerate(row):
            weights[i] += len(str(cell))
            
    total_weight = sum(weights)
    if total_weight == 0: # Avoid division by zero
        return [total_width / num_cols] * num_cols

    # Calculate initial widths based on weights
    col_widths = [(w / total_weight) * total_width for w in weights]

    # Adjust if any column is below its minimum width
    total_assigned_width = sum(col_widths)
    under_min_indices = {i for i, w in enumerate(col_widths) if w < min_widths[i]}
    
    if under_min_indices:
        # Lock the under-minimum columns to their minimum width
        for i in under_min_indices:
            total_assigned_width -= col_widths[i]
            col_widths[i] = min_widths[i]
            total_assigned_width += col_widths[i]
        
        # Redistribute the remaining width among the other columns
        remaining_width = total_width - sum(col_widths[i] for i in under_min_indices)
        remaining_weight = sum(weights[i] for i in range(num_cols) if i not in under_min_indices)
        
        if remaining_weight > 0:
            for i in range(num_cols):
                if i not in under_min_indices:
                    col_widths[i] = (weights[i] / remaining_weight) * remaining_width

    return col_widths

def _calculate_row_height(pdf: FPDF, row: List[str], col_widths: List[float], line_height: float) -> float:
    """Calculates the required height for a single table row."""
    max_lines = 1
    for i, cell in enumerate(row):
        lines = pdf.multi_cell(col_widths[i] - 2, line_height, str(cell), split_only=True)
        max_lines = max(max_lines, len(lines))
    return max_lines * line_height

# ==========================================================
# Markdown Content Generation Helpers
# ==========================================================

def _get_product_facts_md(product_facts: Dict[str, Any]) -> List[str]:
    """Generates Markdown lines for the product facts section."""
    lines = ["**Product Facts**"]
    lines.append("\n**Approved Claims:**")
    for claim in product_facts.get("approved_claims", ["None provided."]):
        lines.append(f"- {claim}")
    
    lines.append("\n**Forbidden Claims:**")
    for claim in product_facts.get("forbidden", ["None provided."]):
        lines.append(f"- {claim}")

    lines.append("\n**Required Disclaimers:**")
    for disclaimer in product_facts.get("required_disclaimers", ["None provided."]):
        lines.append(f"- {disclaimer}")
        
    return lines

def _get_analyzer_summary_md(analyzer: Dict[str, Any]) -> List[str]:
    """Generates Markdown lines for the video analysis summary."""
    vm = analyzer.get("video_metadata", {})
    gs = analyzer.get("global_style", {})
    
    lines = ["**Reference Video Breakdown**"]
    lines.append(f"**Platform:** {vm.get('platform', 'N/A')}")
    lines.append(f"**Duration:** {vm.get('duration_s', 'N/A')}s")
    lines.append(f"**Hook Type:** {', '.join(gs.get('hook_type', ['N/A']))}")
    lines.append(f"**Core CTA:** {gs.get('cta_core', 'N/A')}")
    
    return lines

def _get_script_scenes_md(script: Dict[str, Any]) -> List[str]:
    """Generates Markdown lines for the generated script."""
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
