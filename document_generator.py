# document_generator.py
import os
from fpdf import FPDF
import sys
import json

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
FONT_PATH = os.path.join(SCRIPT_DIR, 'fonts', 'DejaVuSans.ttf')

class PDF(FPDF):
    # ... (class definition remains the same as the last working version) ...

def create_pdf_brief(product_info, analysis_data, brief_json, screenshot_paths, output_path="brief.pdf"):
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

    line_height = pdf.font_size * 1.5
    col_widths = {"time": 20, "action": 55, "dialogue": 55, "shot": 30, "ref": 30}
    headers = ["Time", "Action / Direction", "Dialogue / Text", "Shot Type", "Reference"]

    pdf.set_font('DejaVu', 'B', 8)
    for i, header in enumerate(headers):
        pdf.cell(list(col_widths.values())[i], 10, header, border=1, align='C')
    pdf.ln(10)

    pdf.set_font('DejaVu', '', 8)
    for i, shot in enumerate(shot_list):
        y_start = pdf.get_y()
        time_text = f"{shot.get('start_time', 0):.1f}s - {shot.get('end_time', 0):.1f}s"
        
        pdf.multi_cell(col_widths["time"], 4, time_text, border='LR', align='C')
        x_pos = pdf.l_margin + col_widths["time"]
        pdf.set_xy(x_pos, y_start)

        pdf.multi_cell(col_widths["action"], 4, shot.get("action_description", ""), border='R', align='L')
        x_pos += col_widths["action"]
        pdf.set_xy(x_pos, y_start)

        pdf.multi_cell(col_widths["dialogue"], 4, shot.get("dialogue_or_text", ""), border='R', align='L')
        x_pos += col_widths["dialogue"]
        pdf.set_xy(x_pos, y_start)
        
        pdf.multi_cell(col_widths["shot"], 4, shot.get("shotType", ""), border='R', align='C')
        
        y_end = pdf.get_y()
        row_height = y_end - y_start

        if i < len(screenshot_paths):
            x_pos += col_widths["shot"]
            pdf.image(screenshot_paths[i], x=x_pos, y=y_start, w=col_widths["ref"], h=row_height)
        
        pdf.ln(0)
        pdf.cell(sum(col_widths.values()), 0, '', border='T')
        pdf.ln(row_height)

    pdf.output(output_path)
    return output_path
