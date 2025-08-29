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

def create_pdf_brief(product_info, brief_json, screenshot_paths, output_path="brief.pdf"):
    pdf = PDF()
    pdf.add_font('DejaVu', '', FONT_PATH, uni=True)
    pdf.add_font('DejaVu', 'B', FONT_PATH, uni=True)
    pdf.add_page()

    pdf.add_section_title("Product Information")
    pdf.add_body_text(product_info)
    
    pdf.add_section_title("Creative Concept")
    pdf.add_body_text(brief_json.get("creativeConcept", "N/A"))
    
    pdf.add_section_title("Shot-by-Shot Timeline")
    
    shot_list = brief_json.get("shotList")
    if not shot_list:
        pdf.add_body_text("No shot list was generated.")
        pdf.output(output_path)
        return output_path

    # --- NEW, ROBUST TABLE LOGIC ---
    col_widths = (20, 55, 55, 30, 30)  # Timestamp, Action, Dialogue, Shot Type, Reference
    headers = ("Time (s)", "Action / Direction", "Dialogue / Text", "Shot Type", "Reference")
    
    pdf.set_font("DejaVu", "B", 8)
    pdf.set_fill_color(230, 230, 230)
    for i, header in enumerate(headers):
        pdf.cell(col_widths[i], 7, header, 1, 0, 'C', 1)
    pdf.ln()

    pdf.set_font("DejaVu", "", 8)
    for i, shot in enumerate(shot_list):
        row = [
            f"{shot.get('start_time', 0):.1f}s - {shot.get('end_time', 0):.1f}s",
            shot.get("action_description", ""),
            shot.get("dialogue_or_text", ""),
            shot.get("shotType", "")
        ]

        # Calculate max height of the row before writing
        max_height = 0
        for i_col, text in enumerate(row):
            lines = pdf.multi_cell(col_widths[i_col], 4, text, split_only=True)
            text_height = len(lines) * 4
            if text_height > max_height:
                max_height = text_height
        
        # Ensure a minimum height for the image
        img_height = 30
        final_row_height = max(max_height, img_height)

        # Draw text cells
        start_y = pdf.get_y()
        pdf.multi_cell(col_widths[0], 4, row[0], border='LR', align='C')
        pdf.set_xy(pdf.l_margin + col_widths[0], start_y)
        pdf.multi_cell(col_widths[1], 4, row[1], border='R', align='L')
        pdf.set_xy(pdf.l_margin + col_widths[0] + col_widths[1], start_y)
        pdf.multi_cell(col_widths[2], 4, row[2], border='R', align='L')
        pdf.set_xy(pdf.l_margin + col_widths[0] + col_widths[1] + col_widths[2], start_y)
        pdf.multi_cell(col_widths[3], 4, row[3], border='R', align='C')
        
        # Draw image cell
        if i < len(screenshot_paths):
            x_pos = pdf.l_margin + sum(col_widths[:4])
            pdf.image(screenshot_paths[i], x=x_pos, y=start_y, w=col_widths[4], h=final_row_height)
        
        # Draw border on the right of the image cell
        pdf.set_xy(pdf.l_margin + sum(col_widths[:4]), start_y)
        pdf.cell(col_widths[4], final_row_height, '', border='R')

        pdf.set_y(start_y + final_row_height)
        pdf.cell(sum(col_widths), 0, '', border='T')
        pdf.ln()

    pdf.output(output_path)
    return output_path
