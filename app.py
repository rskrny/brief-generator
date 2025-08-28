# app.py
import streamlit as st
from video_processor import download_video, extract_screenshots
from ai_analyzer import get_video_analysis
# We'll use this in the final step
# from document_generator import create_pdf_brief

# --- Page Configuration ---
st.set_page_config(
    page_title="AI Influencer Brief Generator",
    page_icon="🤖",
    layout="wide"
)

# --- App Header ---
st.title("AI Influencer Brief Generator 🤖")
st.write("Enter a product and a reference video to automatically generate a creative brief.")

# --- Input Fields ---
st.header("Step 1: Provide Your Inputs")

# Use columns for a cleaner layout
col1, col2 = st.columns(2)

with col1:
    product_name = st.text_input("Product Name + Brand", key="product_name")

with col2:
    video_url = st.text_area("TikTok, Instagram, or YouTube URL", key="video_url")
    
# --- Generate Button and Workflow Logic ---
if st.button("Generate Brief", type="primary"):
    # Securely get the API key from the secrets file
    gemini_api_key = st.secrets.get("GEMINI_API_KEY")

    # Input validation
    if not product_name or not video_url:
        st.error("Please fill in the Product Name and Video URL fields.")
    elif not gemini_api_key:
        st.error("Gemini API key not found. Please add it to your .streamlit/secrets.toml file.")
    else:
        with st.status("Starting full analysis workflow...", expanded=True) as status:
            try:
                # Step 1: Download video
                status.update(label="Step 1/4: Downloading video...")
                video_path = download_video(video_url)
                if not video_path:
                    st.error("Video download failed.")
                    status.update(state="error", expanded=False)
                else:
                    st.write(f"✅ Video downloaded successfully.")

                    # Step 2: Analyze video with Gemini (Pass 1)
                    status.update(label="Step 2/4: Analyzing video style with AI...")
                    analysis_data = get_video_analysis(gemini_api_key, video_path)
                    if not analysis_data:
                        st.error("AI analysis failed.")
                        status.update(state="error", expanded=False)
                    else:
                        st.write("✅ AI analysis complete.")
                        
                        # Step 3: Extract screenshots
                        status.update(label="Step 3/4: Extracting key moments...")
                        timestamps = [moment['timestamp'] for moment in analysis_data.get('keyMoments', [])]
                        if not timestamps:
                             st.warning("AI did not return any key moments to screenshot.")
                             screenshot_paths = []
                        else:
                            screenshot_paths = extract_screenshots(video_path, timestamps)
                            st.write(f"✅ Extracted {len(screenshot_paths)} screenshots.")
                        
                        # Step 4: Display results
                        status.update(label="Step 4/4: Assembling results...")
                        st.session_state.analysis_data = analysis_data
                        st.session_state.screenshot_paths = screenshot_paths
                        st.session_state.run_complete = True
                        status.update(label="Workflow complete!", state="complete", expanded=False)

            except Exception as e:
                st.error(f"An unexpected error occurred: {e}")
                status.update(state="error", expanded=False)

# --- Display Results ---
if 'run_complete' in st.session_state and st.session_state.run_complete:
    st.header("Step 2: Analysis Results")
    # ... (rest of the display logic remains the same)