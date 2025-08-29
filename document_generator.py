# document_generator.py
import os
from fpdf import FPDF
import sys

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

    line_height = pdf.font_size * 1.5
    col_widths = {"time": 20, "action": 55, "dialogue": 55, "shot": 30, "ref": 30}
    headers = ["Time (s)", "Action / Direction", "Dialogue / Text", "Shot Type", "Reference"]

    pdf.set_font('DejaVu', 'B', 8)
    for i, header in enumerate(headers):
        pdf.cell(list(col_widths.values())[i], 10, header, border=1, align='C')
    pdf.ln(10)

    pdf.set_font('DejaVu', '', 8)
    for i, shot in enumerate(shot_list):
        y_start = pdf.get_y()
        time_text = f"{shot.get('start_time', 0):.1f}s - {shot.get('end_time', 0):.1f}s"
        
        # Calculate row height based on the tallest cell
        h1 = pdf.multi_cell(col_widths["time"], 4, time_text, border=0, align='C', split_only=True)
        h2 = pdf.multi_cell(col_widths["action"], 4, shot.get("action_description", ""), border=0, align='L', split_only=True)
        h3 = pdf.multi_cell(col_widths["dialogue"], 4, shot.get("dialogue_or_text", ""), border=0, align='L', split_only=True)
        h4 = pdf.multi_cell(col_widths["shot"], 4, shot.get("shotType", ""), border=0, align='C', split_only=True)
        row_height = max(len(h1), len(h2), len(h3), len(h4)) * 4 + 2 # Add padding

        # Draw text cells with calculated height
        pdf.multi_cell(col_widths["time"], row_height, time_text, border='LR', align='C')
        x_pos = pdf.l_margin + col_widths["time"]
        pdf.set_xy(x_pos, y_start)
        pdf.multi_cell(col_widths["action"], row_height, shot.get("action_description", ""), border='R', align='L')
        x_pos += col_widths["action"]
        pdf.set_xy(x_pos, y_start)
        pdf.multi_cell(col_widths["dialogue"], row_height, shot.get("dialogue_or_text", ""), border='R', align='L')
        x_pos += col_widths["dialogue"]
        pdf.set_xy(x_pos, y_start)
        pdf.multi_cell(col_widths["shot"], row_height, shot.get("shotType", ""), border='R', align='C')

        # Draw the image in its cell
        if i < len(screenshot_paths):
            x_pos += col_widths["shot"]
            pdf.image(screenshot_paths[i], x=x_pos, y=y_start, w=col_widths["ref"], h=row_height)
        
        # Draw the bottom border of the row
        pdf.set_xy(pdf.l_margin, y_start + row_height)
        pdf.cell(sum(col_widths.values()), 0, '', border='T')
        pdf.ln(0)

    pdf.output(output_path)
    return output_path
