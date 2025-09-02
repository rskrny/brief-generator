# document_generator.py
# Converts Analyzer JSON + Script JSON + Product Facts into a director-grade Markdown brief.
# No external deps required. You can display the Markdown in Streamlit (st.markdown)
# or offer it as a downloadable .md file. If you later add a PDF pipeline, convert
# this Markdown to PDF with your preferred library.

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


_TABLE_SEPARATOR_RE = re.compile(r"^\|(?:\s*:?-+:?\s*\|)+\s*$")

_IMAGE_CELL_HEIGHT = 30  # fixed height for images in table cells
_IMAGE_EXTENSIONS = {".png", ".jpg", ".jpeg", ".gif", ".bmp"}


def _get_image_path(cell: Any) -> Optional[str]:
    """Return an image path if *cell* represents an image, otherwise ``None``."""
    if isinstance(cell, dict) and "image" in cell:
        return str(cell["image"])
    if isinstance(cell, (str, Path)):
        path = Path(cell)
        if path.suffix.lower() in _IMAGE_EXTENSIONS:
            return str(path)
    return None


# =========================
# Public API
# =========================


def make_brief_markdown(
    *,
    analyzer: Dict[str, Any],
    script: Dict[str, Any],
    product_facts: Dict[str, Any],
    title: str = "AI-Generated Influencer Brief",
) -> str:
    """
    Build a single Markdown document summarizing the reference video analysis and
    the newly generated script for the target brand/product.

    Required keys:
      analyzer: Analyzer JSON (as parsed dict, not string)
      script:   Script JSON (as parsed dict, not string)
      product_facts: dict with keys like brand, product_name, approved_claims, forbidden, required_disclaimers

    Returns a Markdown string.
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


def make_brief_pdf(
    *,
    analyzer: Dict[str, Any],
    script: Dict[str, Any],
    product_facts: Dict[str, Any],
    title: str = "AI-Generated Influencer Brief",
    orientation: Optional[str] = None,
    column_threshold: int = 8,
) -> bytes:
    """Generate a two-page PDF consisting of a summary and reference scene table.

    The first page contains only high-level information (header, product facts,
    reference video summary). The second page renders the scene-by-scene table
    describing the reference video. ``orientation`` is determined from that
    table unless explicitly provided.
    """

    # =========================
    # Build summary lines
    # =========================
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

    # =========================
    # Build storyboard table lines
    # =========================
    storyboard_lines = _scenes_table(analyzer)

    # Determine orientation from storyboard table
    if orientation is None:
        max_cols = _max_table_columns("\n".join(storyboard_lines))
        orientation = "L" if max_cols > column_threshold else "P"
    else:
        orientation = orientation[0].upper()

    # Spacing constants
    PARA_SPACING = 5
    SECTION_SPACING = 4

    class BriefPDF(FPDF):
        def footer(self) -> None:  # pragma: no cover - simple rendering
            self.set_y(-15)
            self.set_font("DejaVu", size=8)
            self.cell(0, 10, f"{self.page_no()}/{{nb}}", align="C")

    pdf = BriefPDF(orientation=orientation)
    pdf.set_margins(15, 15, 15)
    pdf.set_auto_page_break(auto=True, margin=15)
    pdf.alias_nb_pages()
    font_path = Path(__file__).parent / "fonts" / "DejaVuSans.ttf"
    pdf.add_font("DejaVu", "", str(font_path), uni=True)
    pdf.add_font("DejaVu", "B", str(font_path), uni=True)

    # ---- Render summary page ----
    pdf.add_page()
    pdf.set_font("DejaVu", size=12)
    i = 0
    while i < len(summary_lines):
        line = summary_lines[i]
        if not line.strip():
            pdf.ln(PARA_SPACING)
            i += 1
            continue
        if line.startswith("# "):
            pdf.set_font("DejaVu", size=16)
            pdf.multi_cell(pdf.epw, 8, line[2:].strip())
            pdf.set_font("DejaVu", size=12)
        elif line.startswith("## "):
            pdf.set_font("DejaVu", size=14)
            pdf.multi_cell(pdf.epw, 7, line[3:].strip())
            pdf.set_font("DejaVu", size=12)
        elif line.startswith("### "):
            pdf.set_font("DejaVu", size=12)
            pdf.multi_cell(pdf.epw, 6, line[4:].strip())
        elif line.startswith("- "):
            _render_list_item(pdf, line[2:].strip())
        else:
            pdf.multi_cell(pdf.epw, 6, line)
        i += 1

    # ---- Render storyboard page ----
    pdf.add_page()
    pdf.set_font("DejaVu", size=12)
    lines = storyboard_lines
    i = 0
    while i < len(lines):
        line = lines[i]

        if (
            line.startswith("|")
            and i + 1 < len(lines)
            and _TABLE_SEPARATOR_RE.match(lines[i + 1])
        ):
            headers, rows, i = _parse_table_block(lines, i)
            _render_table(pdf, headers, rows)
            pdf.ln(SECTION_SPACING)
            continue

        if not line.strip():
            pdf.ln(PARA_SPACING)
            i += 1
            continue
        if line.startswith("# "):
            pdf.set_font("DejaVu", size=16)
            pdf.multi_cell(pdf.epw, 8, line[2:].strip())
            pdf.set_font("DejaVu", size=12)
        elif line.startswith("## "):
            pdf.set_font("DejaVu", size=14)
            pdf.multi_cell(pdf.epw, 7, line[3:].strip())
            pdf.set_font("DejaVu", size=12)
        elif line.startswith("### "):
            pdf.set_font("DejaVu", size=12)
            pdf.multi_cell(pdf.epw, 6, line[4:].strip())
        elif line.startswith("- "):
            _render_list_item(pdf, line[2:].strip())
        else:
            pdf.multi_cell(pdf.epw, 6, line)
        i += 1

    pdf_bytes = pdf.output(dest="S")
    return bytes(pdf_bytes)


def _parse_table_block(
    lines: List[str], start: int
) -> (List[str], List[List[str]], int):
    """Parse a markdown table block starting at ``start`` index.

    Returns headers, rows and the index of the next line after the table.
    """
    header = [c.strip() for c in lines[start].strip().strip("|").split("|")]
    i = start + 2  # Skip header and separator line
    rows: List[List[str]] = []
    while i < len(lines) and lines[i].startswith("|"):
        rows.append([c.strip() for c in lines[i].strip().strip("|").split("|")])
        i += 1
    return header, rows, i


def _max_table_columns(md: str) -> int:
    """Return the maximum number of columns across all markdown tables."""
    lines = md.split("\n")
    max_cols = 0
    i = 0
    while i < len(lines):
        line = lines[i]
        if (
            line.startswith("|")
            and i + 1 < len(lines)
            and _TABLE_SEPARATOR_RE.match(lines[i + 1])
        ):
            cols = len([c for c in line.strip().strip("|").split("|")])
            max_cols = max(max_cols, cols)
            i += 2
            while i < len(lines) and lines[i].startswith("|"):
                cols = len([c for c in lines[i].strip().strip("|").split("|")])
                max_cols = max(max_cols, cols)
                i += 1
            continue
        i += 1
    return max_cols


def _split_row_cells(
    pdf: FPDF, cells: List[Any], col_widths: List[float], line_height: float
) -> Tuple[List[Any], float]:
    """Split text cells into lines and capture image cell metadata."""
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
            try:
                lines = pdf.multi_cell(cw, line_height, text, border=0, split_only=True)
            except FPDFException:
                lines = [text]
            cell_lines.append(lines)
            max_lines = max(max_lines, len(lines))
    return cell_lines, line_height * max_lines


def _render_table_row(
    pdf: FPDF,
    cells: List[Any],
    col_widths: List[float],
    line_height: float,
) -> float:
    cell_lines, row_height = _split_row_cells(pdf, cells, col_widths, line_height)
    max_lines = int(row_height / line_height)
    x_start = pdf.get_x()
    y_start = pdf.get_y()
    for line_idx in range(max_lines):
        x = x_start
        for idx, lines in enumerate(cell_lines):
            cw = col_widths[idx]
            if isinstance(lines, dict) and lines.get("image"):
                if line_idx == 0:
                    pdf.rect(x, y_start, cw, row_height)
                    img_w = min(lines["width"], cw - 2)
                    img_x = x + (cw - img_w) / 2
                    img_y = y_start + (row_height - lines["height"]) / 2
                    pdf.image(lines["image"], x=img_x, y=img_y, h=lines["height"])
                x += cw
                continue
            txt = lines[line_idx] if line_idx < len(lines) else ""
            if line_idx == 0 and max_lines == 1:
                border = "LTRB"
            elif line_idx == 0:
                border = "LTR"
            elif line_idx == max_lines - 1:
                border = "LBR"
            else:
                border = "LR"
            pdf.set_xy(x, y_start + line_idx * line_height)
            pdf.multi_cell(cw, line_height, txt, border=border)
            x += cw
    pdf.set_xy(x_start, y_start + row_height)
    return row_height


def _render_table(pdf: FPDF, headers: List[str], rows: List[List[Any]]) -> None:
    """Render a table of ``headers`` and ``rows`` to ``pdf``.

    Each cell in ``rows`` may be a plain string or a mapping ``{"image": path}``
    (or other path-like object) pointing to an image file. Image cells are drawn
    with a fixed height of ``_IMAGE_CELL_HEIGHT`` and column widths are scaled to
    accommodate the rendered image widths.
    """

    col_count = max(len(headers), max((len(r) for r in rows), default=0))
    epw = getattr(pdf, "epw", pdf.w - 2 * pdf.l_margin)

    # Normalize row lengths
    headers = headers + [""] * (col_count - len(headers))
    rows = [r + [""] * (col_count - len(r)) for r in rows]

    font_size = 12
    pdf.set_font("DejaVu", size=font_size)

    # Determine column widths based on content
    col_widths: List[float] = []
    for idx in range(col_count):
        column = [headers[idx]] + [row[idx] for row in rows]
        max_w = 0.0
        for cell in column:
            img_path = _get_image_path(cell)
            if img_path:
                with Image.open(img_path) as im:
                    w = _IMAGE_CELL_HEIGHT * im.width / im.height
            else:
                w = pdf.get_string_width("" if cell is None else str(cell)) + 4
            max_w = max(max_w, w)
        col_widths.append(max_w)
    total_width = sum(col_widths) or epw
    scale = epw / total_width
    col_widths = [w * scale for w in col_widths]

    # Reduce font size when columns get narrow
    min_col_width = min(col_widths) if col_widths else epw
    if min_col_width < 25:
        font_size = 10
    if min_col_width < 20:
        font_size = 8
    if min_col_width < 15:
        font_size = 6
    line_height = font_size * 0.5

    pdf.set_font("DejaVu", style="B", size=font_size)
    _, header_height = _split_row_cells(pdf, headers, col_widths, line_height)
    if pdf.get_y() + header_height > pdf.page_break_trigger:
        pdf.add_page()
    _render_table_row(pdf, headers, col_widths, line_height)
    pdf.set_font("DejaVu", size=font_size)

    for row in rows:
        _, row_height = _split_row_cells(pdf, row, col_widths, line_height)
        if pdf.get_y() + row_height > pdf.page_break_trigger:
            pdf.add_page()
            pdf.set_font("DejaVu", style="B", size=font_size)
            _render_table_row(pdf, headers, col_widths, line_height)
            pdf.set_font("DejaVu", size=font_size)
        _render_table_row(pdf, row, col_widths, line_height)


# =========================
# List helpers
# =========================


def _render_list_item(pdf: FPDF, text: str, bullet: str = "-") -> None:
    """Render a markdown list item with proper bullet indentation."""
    line_height = 6
    bullet_str = f"{bullet} "
    indent = pdf.get_string_width(bullet_str)
    epw = getattr(pdf, "epw", pdf.w - 2 * pdf.l_margin)
    max_width = epw - indent

    pdf.cell(indent, line_height, bullet_str)
    pdf.multi_cell(max_width, line_height, text)


# =========================
# Analyzer helpers
# =========================


def _analyzer_global_summary(analyzer: Dict[str, Any]) -> List[str]:
    vm = analyzer.get("video_metadata", {})
    gs = analyzer.get("global_style", {})
    music = gs.get("music", {})
    duration = _num(vm.get("duration_s"))
    hook_types = gs.get("hook_type", [])
    promise = gs.get("promise", "")
    payoff = gs.get("payoff", "")
    cta_core = gs.get("cta_core", "")
    risk_flags = gs.get("risk_flags", [])

    lines = [
        "**Platform**: " + str(vm.get("platform", "")),
        (
            f"**Duration**: {duration:.2f}s"
            if duration is not None
            else "**Duration**: (unknown)"
        ),
        "**Aspect Ratio**: " + str(vm.get("aspect_ratio", "")),
        "",
        (
            "**Hook Type(s)**: " + ", ".join(hook_types)
            if hook_types
            else "**Hook Type(s)**: (none)"
        ),
        "**Promise**: " + (promise or "(none)"),
        "**Payoff**: " + (payoff or "(none)"),
        "**Core CTA**: " + (cta_core or "(none)"),
        "",
        "**Music**: "
        + ", ".join(
            [
                x
                for x in [music.get("genre"), f"{music.get('bpm','') or ''} BPM"]
                if x and str(x).strip()
            ]
        ),
    ]
    if risk_flags:
        lines.append("**Risk Flags**: " + ", ".join(risk_flags))
    return lines


def _influencer_dna_summary(analyzer: Dict[str, Any]) -> List[str]:
    dna = analyzer.get("influencer_DNA", {})
    delivery = dna.get("delivery", {})
    editing = dna.get("editing_style", {})

    lines = ["### Influencer DNA (Delivery Fingerprint)"]
    lines.append(
        "**Persona Tags**: " + ", ".join(dna.get("persona_tags", []))
        if dna.get("persona_tags")
        else "**Persona Tags**: (none)"
    )
    lines.append(f"**Energy**: {dna.get('energy_1to5', '(unknown)')}/5")
    lines.append("**Pace**: " + str(dna.get("pace", "")))
    if dna.get("sentiment_arc"):
        lines.append("**Sentiment Arc**: " + " → ".join(dna.get("sentiment_arc", [])))
    lines.append("**POV**: " + str(delivery.get("POV", "")))
    lines.append(f"**Eye Contact**: {delivery.get('eye_contact_pct','?')}%")
    if delivery.get("rhetoric"):
        lines.append(
            "**Rhetorical Devices**: " + ", ".join(delivery.get("rhetoric", []))
        )
    if editing:
        lines.append(
            "**Editing Style**: "
            + ", ".join(
                [
                    editing.get("cuts", ""),
                    editing.get("text_style", ""),
                    "anim:" + ",".join(editing.get("anim", [])),
                ]
            ).strip(", ")
        )
    return lines


def _edit_grammar_summary(analyzer: Dict[str, Any]) -> List[str]:
    eg = (analyzer.get("global_style") or {}).get("edit_grammar") or {}
    lines = ["### Edit Grammar & Rhythm"]
    lines.append(f"**Average Cut Interval**: {eg.get('avg_cut_interval_s','?')}s")
    if eg.get("transition_types"):
        lines.append("**Transitions**: " + ", ".join(eg.get("transition_types")))
    lines.append(f"**B-roll Ratio**: {eg.get('broll_ratio','?')}")
    lines.append(
        f"**Overlay Density (per 10s)**: {eg.get('overlay_density_per_10s','?')}"
    )
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
            else f"|  | {b.get('type','')} |{b.get('note','')} |"
        )
    return lines


def _scenes_table(analyzer: Dict[str, Any]) -> List[str]:
    """Return a markdown table describing reference video scenes.

    Columns: Timestamp, Shot Type, Framing, Action, Dialogue,
    On-Screen Text and Reference Thumbnail Screenshot.
    """

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
        timestamp = (
            f"{start:.2f}–{end:.2f}" if start is not None and end is not None else ""
        )
        ontext = (
            "; ".join([_osd_str(x) for x in s.get("on_screen_text", [])])
            if s.get("on_screen_text")
            else ""
        )
        thumb = (
            s.get("reference_thumbnail")
            or s.get("thumbnail_url")
            or s.get("thumbnail")
            or s.get("image_url")
            or s.get("img_url")
            or ""
        )
        lines.append(
            "| {ts} | {shot} | {frame} | {act} | {dlg} | {txt} | {thumb} |".format(
                ts=_safe(timestamp),
                shot=_safe(s.get("shot", "")),
                frame=_safe(s.get("framing", "")),
                act=_safe(s.get("action", "")),
                dlg=_safe(s.get("dialogue_vo", "")),
                txt=_safe(ontext),
                thumb=_safe(thumb),
            )
        )

    return lines


# =========================
# Script helpers
# =========================


def _script_opening(script: Dict[str, Any]) -> List[str]:
    s = script.get("script", {})
    opening = s.get("opening_hook", {}) or {}
    start = _num(opening.get("start_s"))
    end = _num(opening.get("end_s"))
    when = f"{start:.2f}–{end:.2f}s" if start is not None and end is not None else "0–?"
    ontext = (
        "; ".join([_osd_str(x) for x in opening.get("on_screen_text", [])])
        if opening.get("on_screen_text")
        else ""
    )

    lines = ["### Opening Hook (Target Script)"]
    lines.append(f"**Timing**: {when}")
    lines.append("**Dialogue/VO**: " + (opening.get("dialogue", "") or "(none)"))
    lines.append("**Visual**: " + (opening.get("visual", "") or "(none)"))
    lines.append("**On-screen text**: " + (ontext or "(none)"))
    if opening.get("retention_device"):
        lines.append(
            "**Retention Devices**: " + ", ".join(opening.get("retention_device", []))
        )
    return lines


def _script_scenes_table(script: Dict[str, Any]) -> List[str]:
    s = script.get("script", {})
    scenes = s.get("scenes", []) or []
    lines = ["### Scene-by-Scene (Target Script)"]
    if not scenes:
        lines.extend(["", "> No scenes provided."])
        return lines
    lines.extend(
        [
            "",
            "| # | start–end (s) | shot | camera | framing | action | dialogue/VO | on-screen text | SFX | transition | retention | product focus |",
            "|---:|---|---|---|---|---|---|---|---|---|---|",
        ]
    )
    for sc in scenes:
        start = _num(sc.get("start_s"))
        end = _num(sc.get("end_s"))
        dur = f"{start:.2f}–{end:.2f}" if start is not None and end is not None else "–"
        ontext = (
            "; ".join([_osd_str(x) for x in sc.get("on_screen_text", [])])
            if sc.get("on_screen_text")
            else ""
        )
        retention = ", ".join(sc.get("retention_device", []) or [])
        lines.append(
            "| {idx} | {dur} | {shot} | {cam} | {frame} | {act} | {dlg} | {txt} | {sfx} | {tr} | {ret} | {pf} |".format(
                idx=sc.get("idx", ""),
                dur=dur,
                shot=_safe(sc.get("shot", "")),
                cam=_safe(sc.get("camera", "")),
                frame=_safe(sc.get("framing", "")),
                act=_safe(sc.get("action", "")),
                dlg=_safe(sc.get("dialogue_vo", "")),
                txt=_safe(ontext),
                sfx=_safe(", ".join(sc.get("sfx", []) or [])),
                tr=_safe(sc.get("transition_out", "")),
                ret=_safe(retention),
                pf=_safe(sc.get("product_focus", "")),
            )
        )
    return lines


def _cta_options(script: Dict[str, Any]) -> List[str]:
    s = script.get("script", {})
    ctas = s.get("cta_options", []) or []
    lines = ["### CTA Variants"]
    if not ctas:
        lines.append("> No CTA options provided.")
        return lines
    for c in ctas:
        variant = c.get("variant", "")
        lines.append(f"**Variant {variant}**")
        lines.append("- Dialogue/VO: " + (c.get("dialogue", "") or "(none)"))
        if c.get("on_screen_text"):
            ontext = "; ".join([_osd_str(x) for x in c.get("on_screen_text", [])])
            lines.append("- On-screen text: " + ontext)
        lines.append("- Visual: " + (c.get("visual", "") or "(none)"))
        lines.append("- Transition: " + (c.get("transition", "") or "(none)"))
        lines.append("")
    return lines


def _script_checklist(script: Dict[str, Any]) -> List[str]:
    chk = script.get("checklist", {}) or {}

    def _yn(x: Optional[bool]) -> str:
        return "✅" if x else "⚠️" if x is not None else "?"

    lines = [
        f"- Forbidden claims present: {_yn(chk.get('forbidden_claims_present') is False)}",
        f"- Brand terms OK: {_yn(chk.get('brand_terms_ok'))}",
        f"- Captions safe-area OK: {_yn(chk.get('captions_safe_area_ok'))}",
    ]
    notes = script.get("notes_for_legal", []) or []
    if notes:
        lines.append("")
        lines.append("**Notes for Legal**")
        _append_list(lines, notes, bullet="- ")
    return lines


def _compliance_block(
    analyzer: Dict[str, Any], product_facts: Dict[str, Any]
) -> List[str]:
    comp = analyzer.get("compliance", {}) or {}
    forbidden = comp.get("forbidden_claims", []) or []
    req = (product_facts.get("required_disclaimers") or [])[:]
    lines = []
    if forbidden:
        lines.append("**Compliance — Reference Video Flags**")
        _append_list(lines, forbidden, bullet="- ")
    if req:
        lines.append("")
        lines.append("**Compliance — Required Disclaimers for Target Script**")
        _append_list(lines, req, bullet="- ")
    if not lines:
        lines.append("> No additional compliance notes.")
    return lines


# =========================
# Utility helpers
# =========================


def _append_list(lines: List[str], items: List[str], bullet: str = "- ") -> None:
    for it in items:
        if it is None:
            continue
        s = str(it).strip()
        if s:
            lines.append(f"{bullet}{s}")


def _num(x: Any) -> Optional[float]:
    try:
        return float(x)
    except Exception:
        return None


def _safe(x: Any) -> str:
    return (str(x) if x is not None else "").replace("\n", " ").strip()


def _osd_str(obj: Dict[str, Any]) -> str:
    """
    Render an on-screen text object {text,t_in,t_out,position,style} into a compact string.
    """
    if not isinstance(obj, dict):
        return ""
    text = obj.get("text", "")
    t_in = obj.get("t_in", None)
    t_out = obj.get("t_out", None)
    pos = obj.get("position", "")
    style = obj.get("style", "")
    tspan = ""
    try:
        if t_in is not None and t_out is not None:
            tspan = f"[{float(t_in):.2f}–{float(t_out):.2f}s] "
    except Exception:
        pass
    meta = (
        " (" + ", ".join([p for p in [pos, style] if p]) + ")" if (pos or style) else ""
    )
    return f"{tspan}{text}{meta}".strip()


# =========================
# Convenience: stringify
# =========================


def brief_from_json_strings(
    analyzer_json_str: str,
    script_json_str: str,
    product_facts: Dict[str, Any],
    title: str = "AI-Generated Influencer Brief",
) -> str:
    """
    Convenience wrapper if you have raw JSON strings instead of parsed dicts.
    `product_facts` should be a unified packet (research data preferred,
    manual inputs as fallback) so downstream renderers receive a consistent
    view of brand, claims, and disclaimers.
    """
    try:
        analyzer = json.loads(analyzer_json_str or "{}")
    except Exception:
        analyzer = {}
    try:
        script = json.loads(script_json_str or "{}")
    except Exception:
        script = {}
    return make_brief_markdown(
        analyzer=analyzer, script=script, product_facts=product_facts, title=title
    )
