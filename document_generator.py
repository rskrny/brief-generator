# document_generator.py
import os
from fpdf import FPDF
import sys
import json

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
FONT_PATH = os.path.join(SCRIPT_DIR, 'fonts', 'DejaVuSans.ttf')

class PDF(FPDF):
    def header(self):
        # ... (header remains the same)
    def footer(self):
        # ... (footer remains the same)
    def add_section_title(self, title):
        # ... (add_section_title remains the same)
    def add_body_text(self, text):
        # ... (add_body_text remains the same)

def create_pdf_brief(product_info, analysis_data, brief_json, screenshot_paths, output_path="brief.pdf"):
    pdf = PDF()
    pdf.add_font('DejaVu', '', FONT_PATH, uni=True)
    pdf.add_font('DejaVu', 'B', FONT_PATH, uni=True)
    pdf.add_page()

    # --- METADATA AND CONCEPT ---
    # ... (this section remains the same)

    # --- SHOT LIST TABLE ---
    pdf.add_section_title("Shot List")
    
    shot_list = brief_json.get("shotList")
    if not shot_list:
        pdf.add_body_text("No shot list was generated.")
        pdf.output(output_path)
        return output_path

    # --- NEW, ROBUST TABLE LOGIC ---
    line_height = pdf.font_size * 1.5
    col_widths = {"ts": 25, "dialogue": 55, "shot": 30, "direction": 50, "ref": 30}

    # Draw Header
    pdf.set_font('DejaVu', 'B', 9)
    for header, width in zip(["Timestamp", "Dialogue", "Shot Type", "Scene Direction", "Reference"], col_widths.values()):
        pdf.cell(width, line_height, header, border=1, align='C')
    pdf.ln(line_height)

    # Draw Rows
    pdf.set_font('DejaVu', '', 8)
    for i, shot in enumerate(shot_list):
        # Store current y position to draw all cells in the row at the same height
        y_start = pdf.get_y()
        
        # Draw text cells, wrapping text as needed
        pdf.multi_cell(col_widths["ts"], line_height / 1.5, shot.get("timestamp", "N/A"), border='LR', align='C')
        x_pos = pdf.l_margin + col_widths["ts"]
        pdf.set_xy(x_pos, y_start)

        pdf.multi_cell(col_widths["dialogue"], line_height / 1.5, shot.get("dialogue", ""), border='R', align='L')
        x_pos += col_widths["dialogue"]
        pdf.set_xy(x_pos, y_start)

        pdf.multi_cell(col_widths["shot"], line_height / 1.5, shot.get("shotType", ""), border='R', align='C')
        x_pos += col_widths["shot"]
        pdf.set_xy(x_pos, y_start)
        
        pdf.multi_cell(col_widths["direction"], line_height / 1.5, shot.get("sceneDirection", ""), border='R', align='L')
        
        # Find the max y position after drawing all text cells to determine row height
        y_end = pdf.get_y()

        # Draw the image in its cell
        if i < len(screenshot_paths):
            x_pos += col_widths["direction"]
            pdf.image(screenshot_paths[i], x=x_pos, y=y_start, w=col_widths["ref"], h=y_end - y_start)
        
        # Draw the bottom border of the row
        pdf.ln(0) # Go to the start of the line at the new y position
        pdf.cell(sum(col_widths.values()), 0, '', border='T')
        pdf.ln(y_end - y_start)

    pdf.output(output_path)
    return output_path
