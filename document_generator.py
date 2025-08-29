# document_generator.py
import os
from fpdf import FPDF
import sys
import json

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
FONT_PATH = os.path.join(SCRIPT_DIR, 'fonts', 'DejaVuSans.ttf')

class PDF(FPDF):
    def header(self):
        try:
            self.add_font('DejaVu', 'B', FONT_PATH, uni=True)
            self.set_font('DejaVu', 'B', 12)
        except RuntimeError:
            self.set_font('Arial', 'B', 12)
        self.cell(0, 10, 'AI-Generated Influencer Brief', 0, 1, 'C')
        self.ln(5)

    def footer(self):
        self.set_y(-15)
        self.set_font('Arial', 'I', 8)
        self.cell(0, 10, f'Page {self.page_no()}', 0, 0, 'C')

    def add_section_title(self, title):
        self.set_font('DejaVu', 'B', 14)
        safe_title = title.encode('latin-1', 'replace').decode('latin-1')
        self.cell(0, 10, safe_title, 0, 1, 'L')
        self.ln(4)

    def add_body_text(self, text):
        self.set_font('DejaVu', '', 12)
        safe_text = str(text).encode('latin-1', 'replace').decode('latin-1')
        self.multi_cell(0, 8, safe_text)
        self.ln()

def create_pdf_brief(product_info, analysis_data, brief_json, screenshot_paths, output_path="brief.pdf"):
    pdf = PDF()
    pdf.add_font('DejaVu', '', FONT_PATH, uni=True)
    pdf.add_page()

    # --- METADATA ---
    pdf.add_section_title("Product Information")
    pdf.add_body_text(product_info)
    
    if analysis_data.get('influencerDNA'):
        pdf.add_section_title("Influencer DNA Profile")
        dna_text = ""
        for key, value in analysis_data['influencerDNA'].items():
            dna_text += f"{key.replace('_', ' ').title()}: {value}\n"
        pdf.add_body_text(dna_text)

    # --- CREATIVE ---
    pdf.add_section_title("Creative Concept")
    pdf.add_body_text(brief_json.get("creativeConcept", "N/A"))
    
    # --- SHOT LIST TABLE ---
    pdf.add_section_title("Shot List")
    
    if not brief_json.get("shotList"):
        pdf.add_body_text("No shot list was generated.")
        pdf.output(output_path)
        return output_path

    # Table Header
    pdf.set_font('DejaVu', 'B', 10)
    col_widths = [25, 45, 30, 60, 30] # Column widths
    headers = ["Timestamp", "Dialogue", "Shot Type", "Scene Direction", "Reference"]
    for i, header in enumerate(headers):
        pdf.cell(col_widths[i], 10, header, border=1, align='C')
    pdf.ln()

    # Table Rows
    pdf.set_font('DejaVu', '', 9)
    for i, shot in enumerate(brief_json["shotList"]):
        row = [
            shot.get("timestamp", "N/A"),
            shot.get("dialogue", ""),
            shot.get("shotType", ""),
            shot.get("sceneDirection", ""),
        ]
        
        # Calculate row height based on the tallest cell
        max_lines = 0
        for i, text in enumerate(row):
            lines = pdf.multi_cell(col_widths[i], 5, text, split_only=True)
            if len(lines) > max_lines:
                max_lines = len(lines)
        row_height = max_lines * 5
        
        # Draw the cells
        for i, text in enumerate(row):
             pdf.multi_cell(col_widths[i], 5, text, border='LR', align='L')
        
        # Add the image in the last cell
        if i < len(screenshot_paths):
            pdf.image(screenshot_paths[i], x=pdf.l_margin + sum(col_widths[:4]), y=pdf.get_y() - row_height, w=col_widths[4])

        pdf.set_y(pdf.get_y() + row_height - (max_lines*5))
        pdf.cell(sum(col_widths), 0, '', border='T') # Draw bottom border of the row
        pdf.ln(row_height)

    pdf.output(output_path)
    return output_path
