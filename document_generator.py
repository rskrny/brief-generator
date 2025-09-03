# document_generator.py
from typing import Dict, Any
from fpdf import FPDF

def _write_section(pdf, title, content):
    """Helper to write a section with a title and multi-line content."""
    pdf.set_font("DejaVu", "B", 14)
    pdf.cell(0, 10, title, ln=True, align="L")
    pdf.set_font("DejaVu", "", 11)
    pdf.multi_cell(0, 6, content)
    pdf.ln(5)

def make_brief_markdown(analyzer: Dict[str, Any], script: Dict[str, Any], product_facts: Dict[str, Any]) -> str:
    """Generates a markdown brief from the analyzer and script data."""
    md = f"# Creative Brief: {product_facts.get('brand', 'N/A')} - {product_facts.get('product_name', 'N/A')}\n\n"
    
    md += "## 🎯 **Objective**\n"
    md += f"{analyzer.get('objective', 'N/A')}\n\n"
    
    md += "## 👥 **Target Audience**\n"
    md += f"{analyzer.get('target_audience', 'N/A')}\n\n"
    
    md += "## 🔑 **Key Message**\n"
    md += f"{analyzer.get('key_message', 'N/A')}\n\n"
    
    md += "## 🎬 **Creative Strategy**\n"
    md += f"- **Hook:** {analyzer.get('hook_strategy', {}).get('description', 'N/A')}\n"
    md += f"- **Pacing:** {analyzer.get('pacing_and_editing', {}).get('description', 'N/A')}\n"
    md += f"- **Tone & Vibe:** {analyzer.get('tone_and_vibe', 'N/A')}\n\n"

    md += "## 📋 **Script**\n"
    for i, scene in enumerate(script.get("scenes", [])):
        md += f"### Scene {i+1} (Duration: {scene.get('duration_s', 'N/A')}s)\n"
        md += f"**Visuals:** {scene.get('visuals_description', 'N/A')}\n"
        md += f"**Audio/VO:** {scene.get('audio_description', 'N/A')}\n\n"
        
    return md

def make_brief_pdf(analyzer: Dict[str, Any], script: Dict[str, Any], product_facts: Dict[str, Any]) -> bytes:
    """Generates a PDF brief from the analyzer and script data."""

    pdf = FPDF()
    pdf.add_page()
    
    # CRITICAL: Add a font that supports a wider range of characters (like emojis)
    pdf.add_font("DejaVu", "", "fonts/DejaVuSans.ttf", uni=True)
    pdf.set_font("DejaVu", "B", 16)
    
    # --- Header ---
    pdf.cell(0, 10, "Creative Brief: Director Mode", ln=True, align="C")
    pdf.set_font("DejaVu", "", 12)
    pdf.cell(0, 10, f"Brand: {product_facts.get('brand', 'N/A')} | Product: {product_facts.get('product_name', 'N/A')}", ln=True, align="C")
    pdf.ln(10)
    
    # --- Sections ---
    _write_section(pdf, "🎯 Objective", analyzer.get("objective", "Not specified."))
    _write_section(pdf, "👥 Target Audience", analyzer.get("target_audience", "Not specified."))
    _write_section(pdf, "🔑 Key Message", analyzer.get("key_message", "Not specified."))

    # --- Creative Strategy ---
    pdf.set_font("DejaVu", "B", 14)
    pdf.cell(0, 10, "🎨 Creative Strategy", ln=True, align="L")
    pdf.set_font("DejaVu", "", 11)
    pdf.multi_cell(0, 6, 
        f"Hook: {analyzer.get('hook_strategy', {}).get('description', 'N/A')}\n"
        f"Pacing: {analyzer.get('pacing_and_editing', {}).get('description', 'N/A')}\n"
        f"Tone & Vibe: {analyzer.get('tone_and_vibe', 'N/A')}"
    )
    pdf.ln(5)
    
    # --- Script ---
    pdf.set_font("DejaVu", "B", 14)
    pdf.cell(0, 10, "🎬 Scene-by-Scene Script", ln=True, align="L")
    for i, scene in enumerate(script.get("scenes", [])):
        pdf.set_font("DejaVu", "B", 12)
        pdf.cell(0, 8, f"Scene {i+1} (Duration: {scene.get('duration_s', 'N/A')}s)", ln=True)
        pdf.set_font("DejaVu", "", 11)
        pdf.multi_cell(0, 6, 
            f"Visuals: {scene.get('visuals_description', 'N/A')}\n"
            f"Audio/VO: {scene.get('audio_description', 'N/A')}"
        )
        pdf.ln(3)

    return pdf.output(dest='S').encode('latin-1')
