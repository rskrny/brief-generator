# app.py
import streamlit as st
from video_processor import download_video, extract_screenshots
from ai_analyzer import get_video_analysis, generate_creative_brief
from document_generator import create_pdf_brief

st.set_page_config(page_title="AI Influencer Brief Generator", page_icon="🤖", layout="wide")

st.title("AI Influencer Brief Generator 🤖")
st.write("Enter a product and a reference video to automatically generate a detailed, second-by-second creative brief.")

st.header("Step 1: Provide Your Inputs")

# Initialize session state variables if they don't exist
if 'run_complete' not in st.session_state:
    st.session_state.run_complete = False
if 'pdf_path' not in st.session_state:
    st.session_state.pdf_path = ""
if 'pdf_filename' not in st.session_state:
    st.session_state.pdf_filename = ""

product_name = st.text_input("Product Name + Brand")
video_url = st.text_area("TikTok, Instagram, or YouTube URL")
    
if st.button("Generate Brief", type="primary"):
    gemini_api_key = st.secrets.get("GEMINI_API_KEY")
    if not product_name or not video_url:
        st.error("Please fill in all fields.")
    elif not gemini_api_key:
        st.error("Gemini API key not found in Streamlit Secrets.")
    else:
        st.session_state.run_complete = False  # Reset on new run
        with st.status("Starting high-detail workflow...", expanded=True) as status:
            try:
                # Full workflow execution
                status.update(label="Step 1/5: Downloading video...")
                video_path, duration = download_video(video_url)
                if not video_path:
                    raise RuntimeError("Video download failed.")
                st.write(f"✅ Video downloaded ({duration:.2f}s).")

                status.update(label="Step 2/5: Performing timeline analysis...")
                analysis_data = get_video_analysis(gemini_api_key, video_path, duration)
                if not analysis_data:
                    raise RuntimeError("AI timeline analysis failed.")
                st.write("✅ AI timeline analysis complete.")

                status.update(label="Step 3/5: Extracting key moments...")
                timestamps = [
                    scene["screenshot_timestamp"]
                    for scene in analysis_data.get("timeline", [])
                    if "screenshot_timestamp" in scene
                ]
                screenshot_paths = extract_screenshots(video_path, timestamps)
                if not screenshot_paths:
                    raise RuntimeError("No screenshots were extracted.")
                st.write(f"✅ Extracted {len(screenshot_paths)} screenshots.")

                status.update(label="Step 4/5: Generating creative brief...")
                brief_json = generate_creative_brief(
                    gemini_api_key, product_name, analysis_data, duration
                )
                if not brief_json:
                    raise RuntimeError("Creative brief generation failed.")

                # Normalize shot metadata
                for shot in brief_json.get("shotList", []):
                    shot_type = shot.get("shot_type") or shot.get("shotType")
                    if "shot_type" not in shot and shot_type:
                        shot["shot_type"] = shot_type
                    shot["screenshot_timestamp"] = (
                        shot.get("screenshotTimestamp") or shot.get("screenshot_timestamp")
                    )

                # Validate screenshot count against shot list
                shots = brief_json.get("shotList", [])
                if len(screenshot_paths) != len(shots):
                    st.warning("Screenshot count does not match shot list; adjusting.")
                    if len(screenshot_paths) < len(shots):
                        screenshot_paths += [""] * (len(shots) - len(screenshot_paths))
                    else:
                        screenshot_paths = screenshot_paths[: len(shots)]

                st.write("✅ Creative brief written.")

                status.update(label="Step 5/5: Assembling final PDF...")
                pdf_path = "brief.pdf"
                create_pdf_brief(product_name, brief_json, screenshot_paths, pdf_path)
                st.write("✅ PDF assembled.")

                # Store results for download button
                st.session_state.pdf_path = pdf_path
                st.session_state.pdf_filename = f"{product_name.replace(' ', '_')}_Brief.pdf"
            except Exception as e:
                st.error(f"An unexpected error occurred: {e}")
                status.update(state="error", expanded=False)
            else:
                st.session_state.run_complete = True  # Set to True only on full success
                status.update(label="Workflow complete!", state="complete", expanded=False)

if st.session_state.run_complete:
    st.header("Step 2: Download Your Brief")
    with open(st.session_state.pdf_path, "rb") as pdf_file:
        PDFbyte = pdf_file.read()

    st.download_button(
        label="Download Brief (PDF)",
        data=PDFbyte,
        file_name=st.session_state.pdf_filename,
        mime='application/octet-stream'
    )
