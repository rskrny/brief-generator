# app.py
import streamlit as st
import json
import os
from video_processor import download_video, extract_screenshots
from ai_analyzer import get_video_analysis, generate_creative_brief
from document_generator import create_pdf_brief

st.set_page_config(page_title="AI Influencer Brief Generator", page_icon="🤖", layout="wide")

st.title("AI Influencer Brief Generator 🤖")
st.write("Enter a product and a reference video to automatically generate a detailed, second-by-second creative brief.")

st.header("Step 1: Provide Your Inputs")
product_name = st.text_input("Product Name + Brand", key="product_name")
video_url = st.text_area("TikTok, Instagram, or YouTube URL", key="video_url")
    
if st.button("Generate Brief", type="primary"):
    gemini_api_key = st.secrets.get("GEMINI_API_KEY")
    if not product_name or not video_url:
        st.error("Please fill in all fields.")
    elif not gemini_api_key:
        st.error("Gemini API key not found in Streamlit Secrets.")
    else:
        with st.status("Starting high-detail workflow...", expanded=True) as status:
            try:
                # Step 1: Download video and get duration
                status.update(label="Step 1/5: Downloading video...")
                video_path, duration = download_video(video_url)
                st.write(f"✅ Video downloaded ({duration:.2f}s).")

                # Step 2: Perform Full Timeline Analysis (Pass 1)
                status.update(label="Step 2/5: Performing timeline analysis with AI...")
                analysis_data = get_video_analysis(gemini_api_key, video_path, duration)
                st.write("✅ AI timeline analysis complete.")

                # Step 3: Extract screenshots based on the new analysis
                status.update(label="Step 3/5: Extracting key moments...")
                timestamps = [scene['screenshot_timestamp'] for scene in analysis_data.get('timeline', [])]
                screenshot_paths = extract_screenshots(video_path, timestamps)
                st.write(f"✅ Extracted {len(screenshot_paths)} screenshots.")

                # Step 4: Generate the creative brief (Pass 2)
                status.update(label="Step 4/5: Generating creative brief...")
                brief_json = generate_creative_brief(gemini_api_key, product_name, analysis_data, duration)
                st.write("✅ Creative brief written.")

                # Step 5: Assemble the final PDF
                status.update(label="Step 5/5: Assembling final PDF...")
                pdf_path = "brief.pdf"
                create_pdf_brief(product_name, analysis_data, brief_json, screenshot_paths, pdf_path)
                st.write("✅ PDF assembled.")
                
                st.session_state.run_complete = True
                st.session_state.pdf_path = pdf_path
                status.update(label="Workflow complete!", state="complete", expanded=False)

            except Exception as e:
                st.error(f"An unexpected error occurred: {e}")
                status.update(state="error", expanded=False)

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
