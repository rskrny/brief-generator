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

def generate_creative_brief(api_key, product_info, analysis_data, screenshot_paths):
    """
    Generates the creative brief using Gemini's Pass 2 "Creative Director" prompt.
    """
    print("Starting creative brief generation...")
    try:
        genai.configure(api_key=api_key)
        model = genai.GenerativeModel(model_name="models/gemini-1.5-pro-latest")

        # Prepare the prompt with the data we've gathered
        dna_profile_str = json.dumps(analysis_data.get('influencerDNA', {}), indent=2)
        prompt = CREATIVE_DIRECTOR_PROMPT.format(
            product_info=product_info,
            dna_profile=dna_profile_str
        )
        
        # Prepare the images to send along with the prompt
        content_parts = [prompt]
        for path in screenshot_paths:
            content_parts.append(Image.open(path))
            
        print("Generating creative brief with Gemini 1.5 Pro...")
        response = model.generate_content(content_parts)
        
        print("Creative brief generated successfully.")
        return response.text

    except Exception as e:
        print(f"An error occurred during creative brief generation: {e}")
        return None
