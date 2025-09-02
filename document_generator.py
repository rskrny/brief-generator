# document_generator.py
# Converts Analyzer JSON + Script JSON + Product Facts into a director-grade Markdown brief.
# No external deps required. You can display the Markdown in Streamlit (st.markdown)
# or offer it as a downloadable .md file. If you later add a PDF pipeline, convert
# this Markdown to PDF with your preferred library.

from __future__ import annotations

from typing import Dict, Any, List, Optional
import json
import textwrap
from pathlib import Path

from fpdf import FPDF
from fpdf.errors import FPDFException


# =========================
# Public API
# =========================

def make_brief_markdown(
    *,
    analyzer: Dict[str, Any],
    script: Dict[str, Any],
    product_facts: Dict[str, Any],
    title: str = "AI-Generated Influencer Brief"
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
    lines.extend(_stills_section(analyzer))
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
) -> bytes:
    """Generate a PDF version of the brief.

    This is a lightweight conversion that renders the markdown produced by
    :func:`make_brief_markdown` into a text PDF using the bundled DejaVuSans
    font so Unicode characters render correctly.
    """

    md = make_brief_markdown(
        analyzer=analyzer, script=script, product_facts=product_facts, title=title
    )

    pdf = FPDF()
    pdf.set_auto_page_break(auto=True, margin=15)
    pdf.add_page()
    font_path = Path(__file__).parent / "fonts" / "DejaVuSans.ttf"
    pdf.add_font("DejaVu", "", str(font_path), uni=True)
    pdf.set_font("DejaVu", size=12)

    for line in md.split("\n"):
        if not line.strip():
            pdf.ln(5)
            continue
        try:
            if line.startswith("# "):
                pdf.set_font("DejaVu", size=16)
                pdf.multi_cell(0, 8, line[2:].strip())
                pdf.set_font("DejaVu", size=12)
            elif line.startswith("## "):
                pdf.set_font("DejaVu", size=14)
                pdf.multi_cell(0, 7, line[3:].strip())
                pdf.set_font("DejaVu", size=12)
            elif line.startswith("### "):
                pdf.set_font("DejaVu", size=12)
                pdf.multi_cell(0, 6, line[4:].strip())
            else:
                pdf.multi_cell(0, 6, line)
        except FPDFException:
            pdf.cell(0, 6, line, ln=1)
    stills = analyzer.get("key_frames", []) or []
    if stills:
        pdf.add_page()
        pdf.set_font("DejaVu", size=14)
        pdf.multi_cell(0, 7, "Reference Stills")
        pdf.set_font("DejaVu", size=12)
        for s in stills:
            t = _num(s.get("t"))
            caption = f"{t:.2f}s — {s.get('label','')}" if t is not None else s.get('label','')
            pdf.multi_cell(0, 6, caption)
            img = s.get("frame_path") or s.get("image") or s.get("image_path")
            if img and Path(img).exists():
                try:
                    pdf.image(img, w=100)
                except FPDFException:
                    pdf.multi_cell(0, 6, "(image failed)")
            pdf.ln(2)

    pdf_bytes = pdf.output(dest="S")
    return bytes(pdf_bytes)


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
        f"**Duration**: {duration:.2f}s" if duration is not None else "**Duration**: (unknown)",
        "**Aspect Ratio**: " + str(vm.get("aspect_ratio", "")),
        "",
        "**Hook Type(s)**: " + ", ".join(hook_types) if hook_types else "**Hook Type(s)**: (none)",
        "**Promise**: " + (promise or "(none)"),
        "**Payoff**: " + (payoff or "(none)"),
        "**Core CTA**: " + (cta_core or "(none)"),
        "",
        "**Music**: " + ", ".join([x for x in [music.get("genre"), f"{music.get('bpm','') or ''} BPM"] if x and str(x).strip()]),
    ]
    if risk_flags:
        lines.append("**Risk Flags**: " + ", ".join(risk_flags))
    return lines


def _influencer_dna_summary(analyzer: Dict[str, Any]) -> List[str]:
    dna = analyzer.get("influencer_DNA", {})
    delivery = dna.get("delivery", {})
    editing = dna.get("editing_style", {})

    lines = ["### Influencer DNA (Delivery Fingerprint)"]
    lines.append("**Persona Tags**: " + ", ".join(dna.get("persona_tags", [])) if dna.get("persona_tags") else "**Persona Tags**: (none)")
    lines.append(f"**Energy**: {dna.get('energy_1to5', '(unknown)')}/5")
    lines.append("**Pace**: " + str(dna.get("pace", "")))
    if dna.get("sentiment_arc"):
        lines.append("**Sentiment Arc**: " + " → ".join(dna.get("sentiment_arc", [])))
    lines.append("**POV**: " + str(delivery.get("POV", "")))
    lines.append(f"**Eye Contact**: {delivery.get('eye_contact_pct','?')}%")
    if delivery.get("rhetoric"):
        lines.append("**Rhetorical Devices**: " + ", ".join(delivery.get("rhetoric", [])))
    if editing:
        lines.append("**Editing Style**: " + ", ".join([editing.get("cuts",""), editing.get("text_style",""), "anim:"+",".join(editing.get("anim", []))]).strip(", "))
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
    lines = ["### Beat Grid", "", "| t (s) | type | note |", "|---:|---|---|"]
    for b in beats:
        t = _num(b.get("t"))
        lines.append(f"| {t:.2f} | {b.get('type','')} | {b.get('note','')} |" if t is not None else f"|  | {b.get('type','')} | {b.get('note','')} |")
    if len(beats) == 0:
        lines.append("> No beats detected.")
    return lines


def _scenes_table(analyzer: Dict[str, Any]) -> List[str]:
    scenes = analyzer.get("scenes", []) or []
    lines = [
        "### Scene-by-Scene (Reference Video)",
        "",
        "| # | start–end (s) | shot | camera | framing | action | dialogue/VO | on-screen text | SFX | transition | retention |",
        "|---:|---|---|---|---|---|---|---|---|---|"
    ]
    for s in scenes:
        start = _num(s.get("start_s"))
        end = _num(s.get("end_s"))
        dur = f"{start:.2f}–{end:.2f}" if start is not None and end is not None else "–"
        ontext = "; ".join([_osd_str(x) for x in s.get("on_screen_text", [])]) if s.get("on_screen_text") else ""
        retention = ", ".join(s.get("retention_device", []) or [])
        lines.append("| {idx} | {dur} | {shot} | {cam} | {frame} | {act} | {dlg} | {txt} | {sfx} | {tr} | {ret} |".format(
            idx=s.get("idx",""),
            dur=dur,
            shot=_safe(s.get("shot","")),
            cam=_safe(s.get("camera","")),
            frame=_safe(s.get("framing","")),
            act=_safe(s.get("action","")),
            dlg=_safe(s.get("dialogue_vo","")),
            txt=_safe(ontext),
            sfx=_safe(", ".join(s.get("sfx",[]) or [])),
            tr=_safe(s.get("transition_out","")),
            ret=_safe(retention),
        ))
    if len(scenes) == 0:
        lines.append("> No scenes provided.")
    return lines


def _stills_section(analyzer: Dict[str, Any]) -> List[str]:
    stills = analyzer.get("key_frames", []) or []
    lines = ["### Reference Stills"]
    if not stills:
        lines.append("> No still frames captured.")
        return lines
    for s in stills:
        t = _num(s.get("t"))
        label = s.get("label", "")
        lines.append(f"- {t:.2f}s — {label}" if t is not None else f"- {label}")
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
    ontext = "; ".join([_osd_str(x) for x in opening.get("on_screen_text", [])]) if opening.get("on_screen_text") else ""

    lines = ["### Opening Hook (Target Script)"]
    lines.append(f"**Timing**: {when}")
    lines.append("**Dialogue/VO**: " + (opening.get("dialogue","") or "(none)"))
    lines.append("**Visual**: " + (opening.get("visual","") or "(none)"))
    lines.append("**On-screen text**: " + (ontext or "(none)"))
    if opening.get("retention_device"):
        lines.append("**Retention Devices**: " + ", ".join(opening.get("retention_device", [])))
    return lines


def _script_scenes_table(script: Dict[str, Any]) -> List[str]:
    s = script.get("script", {})
    scenes = s.get("scenes", []) or []
    lines = [
        "### Scene-by-Scene (Target Script)",
        "",
        "| # | start–end (s) | shot | camera | framing | action | dialogue/VO | on-screen text | SFX | transition | retention | product focus |",
        "|---:|---|---|---|---|---|---|---|---|---|---|"
    ]
    for sc in scenes:
        start = _num(sc.get("start_s"))
        end = _num(sc.get("end_s"))
        dur = f"{start:.2f}–{end:.2f}" if start is not None and end is not None else "–"
        ontext = "; ".join([_osd_str(x) for x in sc.get("on_screen_text", [])]) if sc.get("on_screen_text") else ""
        retention = ", ".join(sc.get("retention_device", []) or [])
        lines.append("| {idx} | {dur} | {shot} | {cam} | {frame} | {act} | {dlg} | {txt} | {sfx} | {tr} | {ret} | {pf} |".format(
            idx=sc.get("idx",""),
            dur=dur,
            shot=_safe(sc.get("shot","")),
            cam=_safe(sc.get("camera","")),
            frame=_safe(sc.get("framing","")),
            act=_safe(sc.get("action","")),
            dlg=_safe(sc.get("dialogue_vo","")),
            txt=_safe(ontext),
            sfx=_safe(", ".join(sc.get("sfx",[]) or [])),
            tr=_safe(sc.get("transition_out","")),
            ret=_safe(retention),
            pf=_safe(sc.get("product_focus","")),
        ))
    if len(scenes) == 0:
        lines.append("> No scenes provided.")
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
        lines.append("- Dialogue/VO: " + (c.get("dialogue","") or "(none)"))
        if c.get("on_screen_text"):
            ontext = "; ".join([_osd_str(x) for x in c.get("on_screen_text", [])])
            lines.append("- On-screen text: " + ontext)
        lines.append("- Visual: " + (c.get("visual","") or "(none)"))
        lines.append("- Transition: " + (c.get("transition","") or "(none)"))
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


def _compliance_block(analyzer: Dict[str, Any], product_facts: Dict[str, Any]) -> List[str]:
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
    meta = " (" + ", ".join([p for p in [pos, style] if p]) + ")" if (pos or style) else ""
    return f"{tspan}{text}{meta}".strip()


# =========================
# Convenience: stringify
# =========================

def brief_from_json_strings(
    analyzer_json_str: str,
    script_json_str: str,
    product_facts: Dict[str, Any],
    title: str = "AI-Generated Influencer Brief"
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
    return make_brief_markdown(analyzer=analyzer, script=script, product_facts=product_facts, title=title)
