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
            self.set_font("DejaVu", size=8)
            _safe_multi_cell(self, 0, 10, f"{self.page_no()}/{{nb}}", align="C")

    pdf = BriefPDF(orientation=orientation)
    pdf.set_margins(15, 15, 15)
    pdf.set_auto_page_break(auto=True, margin=15)
    pdf.alias_nb_pages()

    # Font (bundled DejaVu if present; fall back to core if missing)
    font_path = Path(__file__).parent / "fonts" / "DejaVuSans.ttf"
    if font_path.exists():
        pdf.add_font("DejaVu", "", str(font_path), uni=True)
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
            pdf.set_font(pdf.font_family, size=16)
            pdf.set_x(pdf.l_margin + PADDING / 2)  # reset to margin
            _safe_multi_cell(pdf, pdf.epw - PADDING, 8, line[2:].strip())
            pdf.set_font(pdf.font_family, size=12)
        elif line.startswith("## "):
            pdf.set_font(pdf.font_family, size=14)
            pdf.set_x(pdf.l_margin + PADDING / 2)
            _safe_multi_cell(pdf, pdf.epw - PADDING, 7, line[3:].strip())
            pdf.set_font(pdf.font_family, size=12)
        elif line.startswith("### "):
            pdf.set_font(pdf.font_family, size=12)
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
            pdf.set_font(pdf.font_family, size=16)
            pdf.set_x(pdf.l_margin + PADDING / 2)
            _safe_multi_cell(pdf, pdf.epw - PADDING, 8, line[2:].strip())
            pdf.set_font(pdf.font_family, size=12)
        elif line.startswith("## "):
            pdf.set_font(pdf.font_family, size=14)
            pdf.set_x(pdf.l_margin + PADDING / 2)
            _safe_multi_cell(pdf, pdf.epw - PADDING, 7, line[3:].strip())
            pdf.set_font(pdf.font_family, size=12)
        elif line.startswith("### "):
            pdf.set_font(pdf.font_family, size=12)
            pdf.set_x(pdf.l_margin + PADDING / 2)
            _safe_multi_cell(pdf, pdf.epw - PADDING, 6, line[4:].strip())
        elif line.startswith("- "):
            _render_list_item(pdf, line[2:].strip())
        else:
            pdf.set_x(pdf.l_margin + PADDING / 2)
            _safe_multi_cell(pdf, pdf.epw - PADDING, 6, line)
        i += 1

    pdf_bytes = pdf.output(dest="S")
    return bytes(pdf_bytes)

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
    width = max(width - PADDING, 0)
    try:
        x, y = pdf.get_x(), pdf.get_y()
        lines = pdf.multi_cell(width, 1, text, border=0, split_only=True)
        pdf.set_xy(x, y)
        return lines
    except FPDFException:
        char_w = pdf.get_string_width("M") or 1
        max_chars = max(int(width / char_w), 1)
        lines = textwrap.wrap(text, width=max_chars, break_long_words=True)
        while any(pdf.get_string_width(l) > width for l in lines) and max_chars > 1:
            max_chars -= 1
            lines = textwrap.wrap(text, width=max_chars, break_long_words=True)
        return lines

def _safe_multi_cell(pdf: FPDF, width: float, line_height: float, text: str, **kwargs: Any) -> None:
    if width <= 0:
        width = getattr(pdf, "epw", pdf.w - 2 * pdf.l_margin)
    width = max(width - PADDING, 0)
    lines = _wrap_text(pdf, width, text)
    start_x = pdf.get_x()
    for i, line in enumerate(lines):
        pdf.multi_cell(width, line_height, line, **kwargs)
        if i < len(lines) - 1:
            pdf.set_x(start_x)


def _render_list_item(
    pdf: FPDF, text: str, bullet: str = "\u2022", line_height: float = 6
) -> None:
    """Render a bullet list item ensuring wrapped text stays within margins."""

    bullet_text = f"{bullet} "
    bullet_width = pdf.get_string_width(bullet_text)
    start_x = pdf.get_x()

    pdf.cell(bullet_width, line_height, bullet_text)
    pdf.set_x(start_x + bullet_width)
    _safe_multi_cell(pdf, pdf.epw - bullet_width, line_height, text)

def _split_row_cells(
    pdf: FPDF, cells: List[Any], col_widths: List[float], line_height: float
) -> Tuple[List[Any], float]:
    cell_lines: List[Any] = []
    max_lines = 1
    for cell, cw in zip(cells, col_widths):
        img_path = _get_image_path(cell)
        if img_path:
            with Image.open(img_path) as im:
                img_w = _IMAGE_CELL_HEIGHT * im.width / im.height
            cell_lines.append({"image": img_path, "width": img_w, "height": _IMAGE_CELL_HEIGHT})
            max_lines = max(max_lines, math.ceil(_IMAGE_CELL_HEIGHT / line_height))
        else:
            text = "" if cell is None else str(cell)
            lines = _wrap_text(pdf, cw - CELL_PADDING, text)
            cell_lines.append(lines)
            max_lines = max(max_lines, len(lines))
    return cell_lines, line_height * max_lines

def _render_table_row(
    pdf: FPDF,
    row_cells: List[Any],
    col_widths: List[float],
    line_height: float,
) -> None:
    start_x = pdf.get_x()
    y_top = pdf.get_y()
    cell_lines, row_height = _split_row_cells(pdf, row_cells, col_widths, line_height)

    x = start_x
    for cell, cw in zip(cell_lines, col_widths):
        pdf.set_xy(x, y_top)
        if isinstance(cell, dict) and "image" in cell:
            # draw border
            pdf.rect(x, y_top, cw, row_height)
            # center image inside cell
            img_w = min(cell["width"], cw - CELL_PADDING)
            img_h = cell["height"]
            img_x = x + (cw - img_w) / 2
            img_y = y_top + (row_height - img_h) / 2
            pdf.image(cell["image"], x=img_x, y=img_y, w=img_w, h=img_h)
        else:
            # text cell
            # draw single border around the cell, then write wrapped lines
            pdf.rect(x, y_top, cw, row_height)
            pdf.set_xy(x + CELL_PADDING / 2, y_top + 1)
            for li, l in enumerate(cell):
                pdf.multi_cell(cw - CELL_PADDING, line_height, l)
        x += cw

    pdf.set_xy(start_x, y_top + row_height)

def _render_table(pdf: FPDF, headers: List[str], rows: List[List[str]]) -> None:
    # auto column sizing based on header + first few rows
    font_size = 10
    line_height = 6

    epw = getattr(pdf, "epw", pdf.w - 2 * pdf.l_margin) - PADDING
    n = max(len(headers), 1)
    base = epw / n

    col_widths = [base for _ in headers]

    if headers:
        pdf.set_font(pdf.font_family, style="B", size=font_size)
        _render_table_row(pdf, headers, col_widths, line_height)
        pdf.set_font(pdf.font_family, size=font_size)

    for row in rows:
        _render_table_row(pdf, row, col_widths, line_height)

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
    intro = script.get("intro", "") or script.get("opening", "")
    if not intro:
        return ["> No opening section."]
    return ["### Opening", "", intro]

def _script_scenes_table(script: Dict[str, Any]) -> List[str]:
    scenes = script.get("scenes", []) or []
    if not scenes:
        return ["> No generated scenes."]
    lines = ["### Generated Scenes", "", "| # | Action | Dialogue | On-Screen Text |", "|---:|---|---|---|"]
    for i, s in enumerate(scenes, 1):
        lines.append(
            f"| {i} | {s.get('action','')} | {s.get('dialogue','')} | {s.get('on_screen_text','')} |"
        )
    return lines

def _cta_options(script: Dict[str, Any]) -> List[str]:
    ctas = script.get("cta_options", []) or []
    if not ctas:
        return []
    lines = ["### CTA Options", ""]
    for c in ctas:
        lines.append(f"- {c}")
    return lines

def _script_checklist(script: Dict[str, Any]) -> List[str]:
    items = script.get("quality_checklist", []) or []
    if not items:
        return ["> (no checklist provided)"]
    return [f"- {x}" for x in items]

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
