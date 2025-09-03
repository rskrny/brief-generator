# document_generator.py
# Converts Analyzer JSON + Script JSON + Product Facts into a director-grade Markdown brief
# and a two-page PDF (summary + storyboard). Compatible with your app.py calls.

from __future__ import annotations

from typing import Dict, Any, List, Optional, Tuple
import json
import re
import textwrap
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
# Public: Markdown builder (used by app.py via wrapper)
# ==========================================================
def make_brief_markdown(
    *,
    analyzer: Dict[str, Any],
    script: Dict[str, Any],
    product_facts: Dict[str, Any],
    title: str = "AI-Generated Influencer Brief (Director Mode)",
) -> str:
    """
    Build a single Markdown document summarizing the reference video analysis and
    the newly generated script for the target brand/product.
    """
    lines: List[str] = []

    # Header
    brand = product_facts.get("brand") or ""
    product = product_facts.get("product_name") or ""
    lines.append(f"# {title}")
    if brand or product:
        lines.append(f"**Product**: {brand} {product}".strip())
    lines.append("")

    # Product facts (claims whitelist)
    lines.append("## Product Facts (Claims Whitelist)")
    _append_list(lines, product_facts.get("approved_claims", []), bullet="- ")
    if product_facts.get("required_disclaimers"):
        lines.append("")
        lines.append("**Required Disclaimers**")
        _append_list(lines, product_facts.get("required_disclaimers", []), bullet="- ")
    if product_facts.get("forbidden"):
        lines.append("")
        lines.append("**Forbidden / Restricted Claims**")
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
# Public: PDF builder (used by app.py)
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
    Generate a two-page PDF consisting of a summary and reference scene table.
    The first page contains high-level info (header, product facts, reference video summary).
    The second page renders the scene-by-scene table.
    Returns PDF bytes for download.
    """

    # ---------- Build the content lines (Markdown-like) ----------
    lines: List[str] = []
    brand = product_facts.get("brand") or ""
    product = product_facts.get("product_name") or ""
    lines.append(f"# {title}")
    if brand or product:
        lines.append(f"**Product**: {brand} {product}".strip())
    lines.append("")

    lines.append("## Product Facts (Claims Whitelist)")
    _append_list(lines, product_facts.get("approved_claims", []), bullet="- ")
    if product_facts.get("required_disclaimers"):
        lines.append("")
        lines.append("**Required Disclaimers**")
        _append_list(lines, product_facts.get("required_disclaimers", []), bullet="- ")
    if product_facts.get("forbidden"):
        lines.append("")
        lines.append("**Forbidden / Restricted Claims**")
        _append_list(lines, product_facts.get("forbidden", []), bullet="- ")
    lines.append("")

    lines.append("## Reference Video — Director Breakdown")
    lines.extend(_analyzer_global_summary(analyzer))
    lines.append("")

    summary_lines = lines

    # Storyboard table lines
    storyboard_lines = _scenes_table(analyzer)

    orientation = (orientation or "P")[0].upper()

    # Layout spacing
    PARA_SPACING = 5
    SECTION_SPACING = 4

    class BriefPDF(FPDF):
        def footer(self) -> None:
            self.set_y(-15)
            # Use whichever font family is active to avoid missing-font errors
            self.set_font(self.font_family, size=8)
            _safe_multi_cell(self, 0, 10, f"{self.page_no()}/{{nb}}", align="C")

    pdf = BriefPDF(orientation=orientation)
    pdf.set_margins(15, 15, 15)
    pdf.set_auto_page_break(auto=True, margin=15)
    pdf.alias_nb_pages()

    # Font (bundled DejaVu if present; fall back to core if missing)
    font_path = Path(__file__).parent / "fonts" / "DejaVuSans.ttf"
    bold_path = Path(__file__).parent / "fonts" / "DejaVuSans-Bold.ttf"
    if font_path.exists():
        pdf.add_font("DejaVu", "", str(font_path), uni=True)
        if bold_path.exists():
            pdf.add_font("DejaVu", "B", str(bold_path), uni=True)
        else:
            # Register "B" style pointing to the same file so bold can be selected
            pdf.add_font("DejaVu", "B", str(font_path), uni=True)
        pdf.set_font("DejaVu", size=12)
    else:
        pdf.set_font("Helvetica", size=12)

    # ---------- Render summary page ----------
    pdf.add_page()
    i = 0
    while i < len(summary_lines):
        line = summary_lines[i]
        if not line.strip():
            pdf.ln(PARA_SPACING)
            i += 1
            continue
        if line.startswith("# "):
            pdf.set_font(pdf.font_family, "B", size=16)
            pdf.set_x(pdf.l_margin + PADDING / 2)  # reset to margin
            _safe_multi_cell(pdf, pdf.epw - PADDING, 8, line[2:].strip())
            pdf.set_font(pdf.font_family, size=12)
        elif line.startswith("## "):
            pdf.set_font(pdf.font_family, "B", size=14)
            pdf.set_x(pdf.l_margin + PADDING / 2)
            _safe_multi_cell(pdf, pdf.epw - PADDING, 7, line[3:].strip())
            pdf.set_font(pdf.font_family, size=12)
        elif line.startswith("### "):
            pdf.set_font(pdf.font_family, "B", size=12)
            pdf.set_x(pdf.l_margin + PADDING / 2)
            _safe_multi_cell(pdf, pdf.epw - PADDING, 6, line[4:].strip())
        elif line.startswith("- "):
            _render_list_item(pdf, line[2:].strip())
        else:
            pdf.set_x(pdf.l_margin + PADDING / 2)
            _safe_multi_cell(pdf, pdf.epw - PADDING, 6, line)
        i += 1

    # ---------- Render storyboard page ----------
    pdf.add_page()
    lines = storyboard_lines
    i = 0
    while i < len(lines):
        line = lines[i]

        # table block?
        if (
            line.startswith("|")
            and i + 1 < len(lines)
            and _TABLE_SEPARATOR_RE.match(lines[i + 1])
        ):
            headers, rows, i = _parse_table_block(lines, i)
            pdf.set_x(pdf.l_margin + PADDING / 2)  # reset before table
            _render_table(pdf, headers, rows)
            pdf.ln(SECTION_SPACING)
            pdf.set_x(pdf.l_margin + PADDING / 2)  # reset after table
            continue

        if not line.strip():
            pdf.ln(PARA_SPACING)
            i += 1
            continue
        if line.startswith("# "):
            pdf.set_font(pdf.font_family, "B", size=16)
            pdf.set_x(pdf.l_margin + PADDING / 2)
            _safe_multi_cell(pdf, pdf.epw - PADDING, 8, line[2:].strip())
            pdf.set_font(pdf.font_family, size=12)
        elif line.startswith("## "):
            pdf.set_font(pdf.font_family, "B", size=14)
            pdf.set_x(pdf.l_margin + PADDING / 2)
            _safe_multi_cell(pdf, pdf.epw - PADDING, 7, line[3:].strip())
            pdf.set_font(pdf.font_family, size=12)
        elif line.startswith("### "):
            pdf.set_font(pdf.font_family, "B", size=12)
            pdf.set_x(pdf.l_margin + PADDING / 2)
            _safe_multi_cell(pdf, pdf.epw - PADDING, 6, line[4:].strip())
        elif line.startswith("- "):
            _render_list_item(pdf, line[2:].strip())
        else:
            pdf.set_x(pdf.l_margin + PADDING / 2)
            _safe_multi_cell(pdf, pdf.epw - PADDING, 6, line)
        i += 1

    pdf_bytes = pdf.output(dest="S")
    pdf_bytes = pdf_bytes.encode("latin-1") if isinstance(pdf_bytes, str) else bytes(pdf_bytes)
    return pdf_bytes

# ==========================================================
# Backwards-compatible wrapper used by app.py
# ==========================================================
def brief_from_json_strings(
    *,
    analyzer_json_str: str,
    script_json_str: str,
    product_facts: Dict[str, Any],
    title: str = "AI-Generated Influencer Brief (Director Mode)",
) -> str:
    """
    Compatibility wrapper for app.py: takes JSON strings and returns Markdown.
    """
    analyzer = json.loads(analyzer_json_str or "{}")
    script = json.loads(script_json_str or "{}")
    return make_brief_markdown(
        analyzer=analyzer,
        script=script,
        product_facts=product_facts,
        title=title,
    )

# ==========================================================
# Parsing / rendering helpers used above
# ==========================================================
def _parse_table_block(
    lines: List[str], start: int
) -> (List[str], List[List[str]], int):
    header = [c.strip() for c in lines[start].strip().strip("|").split("|")]
    i = start + 2  # Skip header and separator line
    rows: List[List[str]] = []
    while i < len(lines) and lines[i].startswith("|"):
        rows.append([c.strip() for c in lines[i].strip().strip("|").split("|")])
        i += 1
    return header, rows, i

def _wrap_text(pdf: FPDF, width: float, text: str) -> List[str]:
    """Split *text* into lines that fit within *width*."""
    width = max(width, 0)
    if width == 0:
        return []

    lines = []
    for line in text.split('\n'):
        if not line:
            lines.append('')
            continue
        
        words = line.split(' ')
        current_line = ''
        for word in words:
            # Check if a single word is wider than the available width
            if pdf.get_string_width(word) > width:
                # Character-by-character wrapping for very long words
                temp_word = ''
                for char in word:
                    if pdf.get_string_width(temp_word + char) > width:
                        lines.append(temp_word)
                        temp_word = char
                    else:
                        temp_word += char
                if temp_word:
                    # After loop, add remaining part of word to a new line if it exists
                    if current_line:
                         lines.append(current_line)
                    current_line = temp_word

            elif pdf.get_string_width(current_line + ' ' + word) <= width:
                current_line += (' ' + word) if current_line else word
            else:
                lines.append(current_line)
                current_line = word
        if current_line:
            lines.append(current_line)

    return lines


def _safe_multi_cell(pdf: FPDF, width: float, line_height: float, text: str, **kwargs: Any) -> None:
    if width <= 0:
        width = getattr(pdf, "epw", pdf.w - 2 * pdf.l_margin)
    width = max(width - PADDING, 0)
    
    # Store start x position
    start_x = pdf.get_x()
    
    lines = _wrap_text(pdf, width, text)
    for i, line in enumerate(lines):
        pdf.multi_cell(width, line_height, line, **kwargs)
        # After each line, reset x position for the next line
        if i < len(lines) - 1:
            pdf.set_x(start_x)


def _render_list_item(
    pdf: FPDF, text: str, bullet: str = "\u2022", line_height: float = 6
) -> None:
    """Render a bullet list item ensuring wrapped text stays within margins."""
    bullet_text = f"{bullet} "
    bullet_width = pdf.get_string_width(bullet_text)
    start_x = pdf.get_x()

    # Set y manually for bullet to ensure alignment with multi-line text
    y_before = pdf.get_y()
    pdf.cell(bullet_width, line_height, bullet_text)
    pdf.set_xy(start_x + bullet_width, y_before)
    
    _safe_multi_cell(pdf, pdf.epw - bullet_width, line_height, text)

def _split_row_cells(
    pdf: FPDF, cells: List[Any], col_widths: List[float], line_height: float
) -> Tuple[List[Any], float]:
    cell_lines_data: List[Any] = []
    max_lines = 1
    
    for cell, cw in zip(cells, col_widths):
        img_path = _get_image_path(cell)
        if img_path:
            path = Path(img_path)
            if path.is_file():
                try:
                    with Image.open(img_path) as im:
                        img_w = _IMAGE_CELL_HEIGHT * im.width / im.height
                    cell_lines_data.append({"image": img_path, "width": img_w, "height": _IMAGE_CELL_HEIGHT})
                    max_lines = max(max_lines, math.ceil(_IMAGE_CELL_HEIGHT / line_height))
                    continue
                except Exception:
                    pass  # fallback to text handling below
            text = img_path
        else:
            text = "" if cell is None else str(cell)
        
        available_width = max(cw - CELL_PADDING * 2, 0)
        lines = _wrap_text(pdf, available_width, text)
        cell_lines_data.append(lines)
        max_lines = max(max_lines, len(lines))
        
    row_height = max_lines * line_height + (CELL_PADDING * 2)
    # Ensure image cells have enough height
    if any(isinstance(d, dict) and "image" in d for d in cell_lines_data):
        row_height = max(row_height, _IMAGE_CELL_HEIGHT + CELL_PADDING * 2)

    return cell_lines_data, row_height

def _render_table_row(
    pdf: FPDF,
    row_cells: List[Any],
    col_widths: List[float],
    line_height: float,
    is_header: bool = False
) -> None:
    start_x = pdf.get_x()
    y_top = pdf.get_y()
    
    # Store original font settings
    original_family = pdf.font_family
    original_style = pdf.font_style
    original_size = pdf.font_size_pt

    if is_header:
        if f"{original_family}B" in pdf.fonts:
            pdf.set_font(original_family, style="B", size=original_size)
        
    cell_lines_data, row_height = _split_row_cells(pdf, row_cells, col_widths, line_height)
    
    if pdf.get_y() + row_height > pdf.page_break_trigger:
        pdf.add_page()
        y_top = pdf.get_y()

    x = start_x
    for cell_data, cw in zip(cell_lines_data, col_widths):
        pdf.set_xy(x, y_top)
        
        # Draw border first
        pdf.rect(x, y_top, cw, row_height)
        
        if isinstance(cell_data, dict) and "image" in cell_data:
            # Center image inside cell
            img_w = min(cell_data["width"], cw - CELL_PADDING * 2)
            img_h = cell_data["height"]
            img_x = x + (cw - img_w) / 2
            img_y = y_top + (row_height - img_h) / 2
            pdf.image(cell_data["image"], x=img_x, y=img_y, w=img_w, h=img_h)
        else:
            # Text cell
            pdf.set_xy(x + CELL_PADDING, y_top + CELL_PADDING)
            for li, l in enumerate(cell_data):
                pdf.multi_cell(cw - CELL_PADDING * 2, line_height, l, align='L')
                if li < len(cell_data) - 1:
                    pdf.set_x(x + CELL_PADDING)
        x += cw

    pdf.set_xy(start_x, y_top + row_height)
    
    # Restore original font settings
    pdf.set_font(original_family, style=original_style, size=original_size)


def _render_table(pdf: FPDF, headers: List[str], rows: List[List[str]]) -> None:
    font_size = 9
    line_height = 5

    original_family = pdf.font_family
    original_style = pdf.font_style
    original_size = pdf.font_size_pt

    pdf.set_font_size(font_size)

    epw = getattr(pdf, "epw", pdf.w - 2 * pdf.l_margin) - PADDING
    num_cols = len(headers)
    
    # Calculate column widths based on content
    all_content = [headers] + rows
    max_content_widths = [0] * num_cols
    
    for row in all_content:
        for i, cell_content in enumerate(row):
            if i < num_cols:
                # Use max word width as a heuristic for minimum width
                words = str(cell_content).split()
                max_word_width = 0
                if words:
                    max_word_width = max(pdf.get_string_width(w) for w in words)
                
                max_content_widths[i] = max(max_content_widths[i], max_word_width)

    total_max_width = sum(max_content_widths)
    if total_max_width > 0:
        col_widths = [(w / total_max_width) * epw for w in max_content_widths]
    else: # Fallback for empty table
        col_widths = [epw / num_cols] * num_cols

    # Render header
    if headers:
        _render_table_row(pdf, headers, col_widths, line_height, is_header=True)

    # Render rows
    for row in rows:
        _render_table_row(pdf, row, col_widths, line_height)

    # Restore original font settings
    pdf.set_font(original_family, style=original_style, size=original_size)

# ---------- Analyzer → Markdown helpers ----------
def _analyzer_global_summary(analyzer: Dict[str, Any]) -> List[str]:
    vm = analyzer.get("video_metadata", {})
    gs = analyzer.get("global_style", {})
    music = gs.get("music", {})
    duration = _num(vm.get("duration_s"))

    lines = [
        "**Platform**: " + str(vm.get("platform", "")),
        (f"**Duration**: {duration:.2f}s" if duration is not None else "**Duration**: (unknown)"),
        "**Aspect Ratio**: " + str(vm.get("aspect_ratio", "")),
        "",
        ("**Hook Type(s)**: " + ", ".join(gs.get("hook_type", [])) if gs.get("hook_type") else "**Hook Type(s)**: (none)"),
        "**Promise**: " + (gs.get("promise") or "(none)"),
        "**Payoff**: " + (gs.get("payoff") or "(none)"),
        "**Core CTA**: " + (gs.get("cta_core") or "(none)"),
        "",
        "**Music**: " + ", ".join([x for x in [music.get("genre"), f"{music.get('bpm','') or ''} BPM"] if x and str(x).strip()]),
    ]
    if (gs.get("risk_flags") or []):
        lines.append("**Risk Flags**: " + ", ".join(gs.get("risk_flags")))
    return lines

def _influencer_dna_summary(analyzer: Dict[str, Any]) -> List[str]:
    dna = analyzer.get("influencer_DNA", {})
    delivery = dna.get("delivery", {})
    editing = dna.get("editing_style", {})

    lines = ["### Influencer DNA (Delivery Fingerprint)"]
    lines.append("**Persona Tags**: " + (", ".join(dna.get("persona_tags", [])) if dna.get("persona_tags") else "(none)"))
    lines.append(f"**Energy**: {dna.get('energy_1to5', '(unknown)')}/5")
    lines.append("**Pace**: " + str(dna.get("pace", "")))
    if dna.get("sentiment_arc"):
        lines.append("**Sentiment Arc**: " + " → ".join(dna.get("sentiment_arc", [])))
    lines.append("**POV**: " + str(delivery.get("POV", "")))
    lines.append(f"**Eye Contact**: {delivery.get('eye_contact_pct','?')}%")
    if delivery.get("rhetoric"):
        lines.append("**Rhetorical Devices**: " + ", ".join(delivery.get("rhetoric", [])))
    if editing:
        parts = [editing.get("cuts", ""), editing.get("text_style", "")]
        anim = editing.get("anim", [])
        if anim:
            parts.append("anim:" + ",".join(anim))
        lines.append("**Editing Style**: " + ", ".join([p for p in parts if p]).strip(", "))
    return lines

def _edit_grammar_summary(analyzer: Dict[str, Any]) -> List[str]:
    eg = (analyzer.get("global_style") or {}).get("edit_grammar") or {}
    lines = ["### Edit Grammar & Rhythm"]
    lines.append(f"**Average Cut Interval**: {eg.get('avg_cut_interval_s','?')}s")
    if eg.get("transition_types"):
        lines.append("**Transitions**: " + ", ".join(eg.get("transition_types")))
    lines.append(f"**B-roll Ratio**: {eg.get('broll_ratio','?')}")
    lines.append(f"**Overlay Density (per 10s)**: {eg.get('overlay_density_per_10s','?')}")
    return lines

def _beats_table(analyzer: Dict[str, Any]) -> List[str]:
    beats = analyzer.get("beats", []) or []
    lines = ["### Beat Grid"]
    if not beats:
        lines.extend(["", "> No beats detected."])
        return lines
    lines.extend(["", "| t (s) | type | note |", "|---:|---|---|"])
    for b in beats:
        t = _num(b.get("t"))
        lines.append(
            f"| {t:.2f} | {b.get('type','')} | {b.get('note','')} |"
            if t is not None
            else f"|  | {b.get('type','')} | {b.get('note','')} |"
        )
    return lines

def _scenes_table(analyzer: Dict[str, Any]) -> List[str]:
    scenes = analyzer.get("scenes", []) or []
    lines = ["### Scene-by-Scene (Reference Video)"]
    if not scenes:
        lines.extend(["", "> No scenes provided."])
        return lines

    lines.extend(
        [
            "",
            "| Timestamp | Shot Type | Framing | Action | Dialogue | On-Screen Text | Reference Thumbnail Screenshot |",
            "|---|---|---|---|---|---|---|",
        ]
    )
    for s in scenes:
        start = _num(s.get("start_s"))
        end = _num(s.get("end_s"))
        timestamp = f"{start:.2f}–{end:.2f}" if start is not None and end is not None else ""
        lines.append(
            "| " + " | ".join(
                [
                    timestamp,
                    str(s.get("shot_type", "")),
                    str(s.get("framing", "")),
                    str(s.get("action", "")),
                    str(s.get("dialogue", "")),
                    str(s.get("on_screen_text", "")),
                    str(s.get("screenshot_path", "")),  # optional local path or URL
                ]
            ) + " |"
        )
    return lines

# ---------- Script helpers ----------
def _script_opening(script: Dict[str, Any]) -> List[str]:
    try:
        opening = script["script"]["opening_hook"]
        dialogue = opening.get("dialogue", "")
        return ["### Opening", "", dialogue]
    except KeyError:
        return ["> No opening section defined in script."]


def _script_scenes_table(script: Dict[str, Any]) -> List[str]:
    try:
        scenes = script["script"]["scenes"]
        if not scenes:
            return ["> No generated scenes."]
        lines = ["### Generated Scenes", "", "| # | Action | Dialogue | On-Screen Text |", "|---:|---|---|---|"]
        for i, s in enumerate(scenes, 1):
            # Consolidate on-screen text for markdown view
            ost_list = s.get("on_screen_text", [])
            ost_str = "; ".join([item.get("text", "") for item in ost_list])
            
            lines.append(
                f"| {i} | {s.get('action','')} | {s.get('dialogue_vo','')} | {ost_str} |"
            )
        return lines
    except KeyError:
        return ["> Script format invalid or missing scenes."]


def _cta_options(script: Dict[str, Any]) -> List[str]:
    try:
        ctas = script["script"]["cta_options"]
        if not ctas:
            return []
        lines = ["### CTA Options"]
        for cta in ctas:
            lines.append(f"- **Variant {cta.get('variant', '')}:** {cta.get('dialogue', '')}")
        return lines
    except KeyError:
        return []

def _script_checklist(script: Dict[str, Any]) -> List[str]:
    try:
        checklist = script.get("checklist", {})
        if not checklist:
            return ["> (no checklist provided)"]
        
        lines = []
        for key, value in checklist.items():
            status = "✅" if value else "❌"
            lines.append(f"- {key.replace('_', ' ').title()}: {status}")
        return lines
    except Exception:
        return ["> Could not parse checklist."]

def _compliance_block(analyzer: Dict[str, Any], product_facts: Dict[str, Any]) -> List[str]:
    lines = ["### Compliance Notes"]
    rf = (analyzer.get("global_style") or {}).get("risk_flags", []) or []
    if rf:
        lines.append("**Risk Flags Detected**: " + ", ".join(rf))
    if product_facts.get("required_disclaimers"):
        lines.append("**Required Disclaimers**:")
        for d in product_facts["required_disclaimers"]:
            lines.append(f"- {d}")
    return lines
