# document_generator.py
import os
from fpdf import FPDF
import sys

# Get the base path to handle running in different environments
base_path = getattr(sys, '_MEIPASS', os.path.dirname(os.path.abspath(__file__)))
FONT_PATH = os.path.join(base_path, "fonts", "DejaVuSans.ttf")

class PDF(FPDF):
    def header(self):
        self.add_font('DejaVu', 'B', FONT_PATH, uni=True)
        self.set_font('DejaVu', 'B', 12)
        self.cell(0, 10, 'AI-Generated Influencer Brief', 0, 1, 'C')
        self.ln(10)

    def footer(self):
        self.set_y(-15)
        self.set_font('DejaVu', 'I', 8)
        self.cell(0, 10, f'Page {self.page_no()}', 0, 0, 'C')

    def add_section_title(self, title):
        self.set_font('DejaVu', 'B', 14)
        # Handle potential encoding issues in titles
        safe_title = title.encode('latin-1', 'replace').decode('latin-1')
        self.cell(0, 10, safe_title, 0, 1, 'L')
        self.ln(4)

    def add_body_text(self, text):
        self.set_font('DejaVu', '', 12)
        # Handle potential encoding issues in body text
        safe_text = text.encode('latin-1', 'replace').decode('latin-1')
        self.multi_cell(0, 10, safe_text)
        self.ln()

def create_pdf_brief(product_info, analysis_data, brief_text, screenshot_paths, output_path="brief.pdf"):
    pdf = PDF()
    pdf.add_font('DejaVu', '', FONT_PATH, uni=True) # Add regular font
    pdf.add_page()
    
    # Product Info
    pdf.add_section_title("Product Information")
    pdf.add_body_text(product_info)
    
    # Influencer DNA
    if analysis_data.get('influencerDNA'):
        pdf.add_section_title("Influencer DNA Profile")
        dna_text = ""
        for key, value in analysis_data['influencerDNA'].items():
            dna_text += f"{key.replace('_', ' ').title()}: {value}\n"
        pdf.add_body_text(dna_text)
        
    # Creative Brief Text from AI
    pdf.add_body_text(brief_text) # The title is now part of the markdown
    
    # Screenshots
    if screenshot_paths:
        pdf.add_section_title("Visual References (Key Moments)")
        for i, path in enumerate(screenshot_paths):
            pdf.add_body_text(f"Reference Screenshot {i+1}:")
            try:
                pdf.image(path, w=pdf.w / 2)
                pdf.ln(5)
            except Exception as e:
                pdf.add_body_text(f"[Could not embed image: {os.path.basename(path)} due to error: {e}]")
            
    pdf.output(output_path)
    print(f"PDF brief generated successfully at: {output_path}")
    return output_path
