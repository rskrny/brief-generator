# document_generator.py
import os
from fpdf import FPDF

class PDF(FPDF):
    def header(self):
        self.set_font('Arial', 'B', 12)
        self.cell(0, 10, 'AI-Generated Influencer Brief', 0, 1, 'C')
        self.ln(10)

    def footer(self):
        self.set_y(-15)
        self.set_font('Arial', 'I', 8)
        self.cell(0, 10, f'Page {self.page_no()}', 0, 0, 'C')

    def add_section_title(self, title):
        self.set_font('Arial', 'B', 14)
        self.cell(0, 10, title, 0, 1, 'L')
        self.ln(4)

    def add_body_text(self, text):
        self.set_font('Arial', '', 12)
        self.multi_cell(0, 10, text)
        self.ln()

def create_pdf_brief(product_info, analysis_data, brief_text, screenshot_paths, output_path="brief.pdf"):
    pdf = PDF()
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
    pdf.add_section_title("Creative Brief")
    pdf.add_body_text(brief_text)
    
    # Screenshots
    if screenshot_paths:
        pdf.add_section_title("Visual References (Key Moments)")
        for i, path in enumerate(screenshot_paths):
            pdf.add_body_text(f"Reference Screenshot {i+1}:")
            pdf.image(path, w=pdf.w / 2) # Display image at half the page width
            pdf.ln(5)
            
    pdf.output(output_path)
    print(f"PDF brief generated successfully at: {output_path}")
    return output_path
