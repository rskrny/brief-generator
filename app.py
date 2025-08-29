# app.py
import streamlit as st
import json
import os
from video_processor import download_video, extract_screenshots
from ai_analyzer import get_video_analysis, generate_creative_brief
from document_generator import create_pdf_brief

# --- Page Configuration ---
st.set_page_config(page_title="AI Influencer Brief Generator", page_icon="🤖", layout="wide")

# --- App Header ---
st.title("AI Influencer Brief Generator 🤖")
st.write("Enter a product and a reference video to automatically generate a creative brief.")

# --- Input Fields ---
st.header("Step 1: Provide Your Inputs")
col1, col2 = st.columns(2)
with col1:
    product_name = st.text_input("Product Name + Brand", key="product_name")
with col2:
    video_url = st.text_area("TikTok, Instagram, or YouTube URL", key="video_url")
    
# --- Generate Button and Workflow Logic ---
if st.button("Generate Brief", type="primary"):
    gemini_api_key = st.secrets.get("GEMINI_API_KEY")
    if not product_name or not video_url:
        st.error("Please fill in the Product Name and Video URL fields.")
    elif not gemini_api_key:
        st.error("Gemini API key not found. Please add it to your .streamlit/secrets.toml file.")
    else:
        with st.status("Starting full workflow...", expanded=True) as status:
            try:
                # Full workflow execution
                status.update(label="Step 1/5: Downloading video...")
                video_path = download_video(video_url)
                st.write("✅ Video downloaded.")

                status.update(label="Step 2/5: Analyzing video style...")
                analysis_data = get_video_analysis(gemini_api_key, video_path)
                st.write("✅ AI analysis complete.")

                status.update(label="Step 3/5: Extracting key moments...")
                timestamps = [moment['timestamp'] for moment in analysis_data.get('keyMoments', [])]
                screenshot_paths = extract_screenshots(video_path, timestamps)
                st.write(f"✅ Extracted {len(screenshot_paths)} screenshots.")

                status.update(label="Step 4/5: Generating creative brief...")
                brief_text = generate_creative_brief(gemini_api_key, product_name, analysis_data, screenshot_paths)
                st.write("✅ Creative brief written.")

                status.update(label="Step 5/5: Assembling final PDF...")
                pdf_path = "brief.pdf"
                create_pdf_brief(product_name, analysis_data, brief_text, screenshot_paths, pdf_path)
                st.write("✅ PDF assembled.")
                
                # Store results for download button
                st.session_state.run_complete = True
                st.session_state.pdf_path = pdf_path
                status.update(label="Workflow complete!", state="complete", expanded=False)

            except Exception as e:
                st.error(f"An unexpected error occurred: {e}")
                status.update(state="error", expanded=False)

# --- Display Download Button ---
if 'run_complete' in st.session_state and st.session_state.run_complete:
    st.header("Step 2: Download Your Brief")
    with open(st.session_state.pdf_path, "rb") as pdf_file:
        PDFbyte = pdf_file.read()

    st.download_button(
        label="Download Brief (PDF)",
        data=PDFbyte,
        file_name=f"{product_name.replace(' ', '_')}_Brief.pdf",
        mime='application/octet-stream'
    )
