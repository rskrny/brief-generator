# app.py
# Brief Generator — Director Mode (Gemini 1.5 Pro Multimodal)
# - Uses Streamlit Cloud Secrets for GOOGLE_API_KEY
# - Downloads video, uploads to Gemini, and performs direct multimodal analysis.
# - Simplified UI for a more automated workflow.

import os
import json
import time
import traceback
from typing import Optional, List, Dict
import base64

import streamlit as st
import google.generativeai as genai
from google.generativeai.types import generation_types

from prompts import (
    build_analyzer_messages,
    build_script_generator_messages,
    build_product_research_messages,
    validate_analyzer_json,
    validate_script_json,
)
from document_generator import make_brief_markdown, make_brief_pdf
from web_utils import fetch_product_page_text
from video_processor import download_video, cleanup_temp_dir, upload_to_gemini, delete_uploaded_file

# --- Configuration ---
MODEL_CHOICE = "gemini-1.5-pro-latest"
TEMPERATURE_CHOICE = 0.2

# =========================
# Key loading & Configuration
# =========================
def _get_google_api_key() -> str:
    """Gets the Google API key from Streamlit secrets or environment variables."""
    try:
        key = st.secrets["GOOGLE_API_KEY"]
        if key: return str(key).strip()
    except (KeyError, FileNotFoundError):
        key = os.getenv("GOOGLE_API_KEY")
        if key: return key.strip()
    raise RuntimeError("GOOGLE_API_KEY not found in st.secrets or environment variables.")

def _ensure_gemini_configured():
    """Ensures the Gemini client is configured."""
    try:
        genai.configure(api_key=_get_google_api_key())
    except Exception as e:
        st.error(f"Failed to configure Gemini: {e}")
        st.stop()

_ensure_gemini_configured()

# =========================
# Gemini Call Logic
# =========================
class GeminiAPIError(Exception):
    """Custom exception for Gemini API errors."""
    pass

def call_gemini_multimodal_json(prompt: str, video_file_uri: str) -> str:
    """Calls Gemini with multimodal input (video + text) and expects a JSON response."""
    model = genai.GenerativeModel(MODEL_CHOICE)
    
    print(f"Calling Gemini with video URI: {video_file_uri}")
    video_file = genai.get_file(name=video_file_uri)

    try:
        response = model.generate_content(
            [prompt, video_file],
            generation_config={
                "temperature": TEMPERATURE_CHOICE,
                "response_mime_type": "application/json",
            }
        )
        
        if response.prompt_feedback and response.prompt_feedback.block_reason:
            raise GeminiAPIError(f"Response blocked by safety filters: {response.prompt_feedback.block_reason.name}")
        
        if not response.candidates or not response.text:
            finish_reason = response.candidates[0].finish_reason if response.candidates else "UNKNOWN"
            raise GeminiAPIError(f"Gemini returned an empty response. Finish Reason: {finish_reason}")
            
        return response.text
        
    except Exception as e:
        raise GeminiAPIError(f"Gemini API call failed: {e}")

# =========================
# Streamlit UI
# =========================
st.set_page_config(page_title="Brief Generator — Director Mode", layout="wide")
st.title("🎬 Brief Generator — Director Mode")

with st.sidebar:
    st.header("How It Works")
    st.info(
        "This app uses a fully automated workflow:\n\n"
        "1. **Provide a URL** to a reference video.\n"
        "2. The app **downloads the video** and uploads it to Gemini.\n"
        "3. Gemini performs a **deep multimodal analysis** of the video's content, style, and structure.\n"
        "4. The analysis is used to **generate a new script** for your product that mimics the reference video's successful formula."
    )
    st.markdown("---")
    st.header("Configuration")
    st.markdown(f"**Model:** `{MODEL_CHOICE}`")
    st.markdown(f"**Platform:**")
    platform = st.selectbox("Platform", ["tiktok", "reels", "ytshorts"], index=0, label_visibility="collapsed")


st.markdown(
    "This app runs a two-step pipeline: **Analyzer** → **Script Generator**. "
    "The Analyzer performs a deep, multimodal analysis of the reference video file. "
    "The Script Generator then adapts that successful formula to your brand and product."
)

# ========== Inputs ==========
st.header("1) Reference Video")
video_url = st.text_input("Reference video URL", value="", placeholder="https://www.tiktok.com/... or https://www.youtube.com/shorts/...")

st.markdown("---")
st.header("2) Target Product Facts")
brand_name = st.text_input("Brand", value="", placeholder="Enter brand name")
product_name = st.text_input("Product", value="", placeholder="Enter product name")
product_page_url = st.text_input("Product page URL", value="", placeholder="https://…")

if "claims_text" not in st.session_state: st.session_state["claims_text"] = ""
if "product_facts" not in st.session_state: st.session_state["product_facts"] = {}

# ... (Product Research button and text areas remain the same as previous versions) ...

# ========== State Management ==========
for key in ["analyzer_json_str", "analyzer_parsed", "script_json_str", "script_parsed", "target_runtime_s"]:
    if key not in st.session_state:
        st.session_state[key] = None

st.markdown("---")
analyze_col, script_col = st.columns(2)

# ---- Analyzer ----
with analyze_col:
    if st.button("🔎 Run Full Video Analysis", use_container_width=True):
        # Reset state
        for key in st.session_state.keys():
            st.session_state[key] = None

        if not video_url:
            st.warning("Please provide a reference video URL.")
        else:
            video_path, uploaded_file = None, None
            try:
                with st.spinner("Downloading reference video..."):
                    video_path, actual_duration = download_video(video_url)
                if not video_path or not actual_duration:
                    raise FileNotFoundError("Failed to download video. Check the URL.")
                
                st.session_state["target_runtime_s"] = actual_duration
                st.info(f"✅ Video downloaded. Detected duration: {actual_duration:.2f}s")
                
                with st.spinner("Uploading video to Gemini for analysis..."):
                    uploaded_file = upload_to_gemini(video_path, "video/mp4")
                if not uploaded_file:
                    raise ConnectionError("Failed to upload video file to Gemini.")
                
                st.info(f"✅ Video uploaded. Starting multimodal analysis...")

                prompt = build_analyzer_messages(duration_s=actual_duration, platform=platform)

                with st.spinner(f"Analyzing video with {MODEL_CHOICE}... (This may take a minute)"):
                    analyzer_json_str = call_gemini_multimodal_json(prompt, uploaded_file.name)
                
                analyzer_parsed = json.loads(analyzer_json_str)
                errs = validate_analyzer_json(analyzer_parsed)

                st.session_state["analyzer_json_str"] = analyzer_json_str
                st.session_state["analyzer_parsed"] = analyzer_parsed

                if errs:
                    st.error("Analyzer JSON has issues:\n- " + "\n- ".join(errs))
                else:
                    st.success("✅ Deep video analysis complete!")

            except Exception as e:
                st.error(f"An error occurred during analysis: {e}")
                st.code(traceback.format_exc())
            finally:
                if uploaded_file:
                    with st.spinner("Cleaning up uploaded file..."):
                        delete_uploaded_file(uploaded_file.name)
                cleanup_temp_dir()

# ---- Script Generator ----
with script_col:
    if st.button("🎬 Generate Script from Analysis", use_container_width=True):
        st.session_state["script_json_str"] = None
        st.session_state["script_parsed"] = None
        if not st.session_state.get("analyzer_parsed"):
            st.warning("Please run the video analysis first.")
        else:
            # ... (Script generation logic remains the same) ...
            pass
    
# ========== Output / Export ==========
# ... (Output section remains the same) ...
