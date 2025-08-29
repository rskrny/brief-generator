# ai_analyzer.py
import google.generativeai as genai
import time
import json
from prompts import ANALYST_PROMPT, CREATIVE_DIRECTOR_PROMPT # Import both prompts
from PIL import Image

def get_video_analysis(api_key, video_path):
    # ... (this function remains exactly the same as before)
    print("Starting AI video analysis...")
    try:
        genai.configure(api_key=api_key)
        print("Uploading video file to Gemini...")
        video_file = genai.upload_file(path=video_path)
        while video_file.state.name == "PROCESSING":
            print("Waiting for video processing...")
            time.sleep(10)
            video_file = genai.get_file(video_file.name)
        if video_file.state.name == "FAILED":
            raise ValueError("Gemini video processing failed.")
        print("Video processed successfully by Gemini.")
        model = genai.GenerativeModel(model_name="models/gemini-1.5-pro-latest")
        print("Generating analysis with Gemini 1.5 Pro...")
        response = model.generate_content([ANALYST_PROMPT, video_file])
        print("Deleting uploaded file from Gemini server...")
        genai.delete_file(video_file.name)
        analysis_json = response.text.strip().replace("```json", "").replace("```", "")
        analysis_data = json.loads(analysis_json)
        print("AI analysis complete.")
        return analysis_data
    except Exception as e:
        print(f"An error occurred during AI analysis: {e}")
        return None

# In ai_analyzer.py

def generate_creative_brief(api_key, product_info, analysis_data, screenshot_paths):
    """
    Generates the creative brief and returns a structured dictionary.
    """
    print("Starting creative brief generation...")
    try:
        genai.configure(api_key=api_key)
        model = genai.GenerativeModel(model_name="models/gemini-1.5-pro-latest")

        dna_profile_str = json.dumps(analysis_data.get('influencerDNA', {}), indent=2)
        prompt = CREATIVE_DIRECTOR_PROMPT.format(
            product_info=product_info,
            dna_profile=dna_profile_str
        )
        
        content_parts = [prompt]
        images = []
        for path in screenshot_paths:
            img = Image.open(path)
            images.append(img)
            content_parts.append(img)
            
        print("Generating creative brief with Gemini 1.5 Pro...")
        response = model.generate_content(content_parts)
        
        # Clean and parse the JSON response
        brief_json_str = response.text.strip().replace("```json", "").replace("```", "")
        brief_data = json.loads(brief_json_str)
        
        print("Creative brief generated successfully.")
        return brief_data

    except Exception as e:
        print(f"An error occurred during creative brief generation: {e}")
        return None
