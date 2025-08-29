# ai_analyzer.py
import google.generativeai as genai
import time
import json
from prompts import ANALYST_PROMPT, CREATIVE_DIRECTOR_PROMPT, STRATEGY_PROMPT
from PIL import Image

def get_video_analysis(api_key, video_path, duration):
    """
    Analyzes the video using the full timeline "Analyst" prompt.
    """
    print("Starting AI timeline analysis...")
    try:
        genai.configure(api_key=api_key)
        
        prompt = ANALYST_PROMPT.format(video_duration=duration)
        
        print("Uploading video file to Gemini...")
        video_file = genai.upload_file(path=video_path)
        while video_file.state.name == "PROCESSING":
            print("Waiting for video processing...")
            time.sleep(10)
            video_file = genai.get_file(video_file.name)
        if video_file.state.name == "FAILED":
            raise ValueError("Gemini video processing failed.")
        
        print("Video processed. Generating timeline analysis...")
        model = genai.GenerativeModel(model_name="models/gemini-1.5-pro-latest")
        response = model.generate_content([prompt, video_file])
        
        print("Deleting uploaded file...")
        genai.delete_file(video_file.name)

        analysis_json = response.text.strip().replace("```json", "").replace("```", "")
        analysis_data = json.loads(analysis_json)
        
        print("AI timeline analysis complete.")
        return analysis_data

    except Exception as e:
        print(f"An error occurred during AI analysis: {e}")
        return None


def generate_strategy_map(api_key, reference_product, reference_features, new_features, analysis_data):
    """Generate a translation map from reference product features to new product features."""
    print("Starting strategy map generation...")
    try:
        genai.configure(api_key=api_key)
        model = genai.GenerativeModel(model_name="models/gemini-1.5-pro-latest")

        timeline_analysis_str = json.dumps(analysis_data, indent=2)

        prompt = STRATEGY_PROMPT.format(
            reference_product=reference_product,
            reference_features=reference_features,
            new_features=new_features,
            timeline_analysis=timeline_analysis_str,
        )

        response = model.generate_content(prompt)
        strategy_json = response.text.strip().replace("```json", "").replace("```", "")
        strategy_data = json.loads(strategy_json)

        print("Strategy map generated successfully.")
        return strategy_data

    except Exception as e:
        print(f"An error occurred during strategy map generation: {e}")
        return None


def generate_creative_brief(api_key, product_name, product_features, strategy_map, analysis_data, duration):
    """Generates the creative brief using the "Creative Director" prompt."""
    print("Starting creative brief generation...")
    try:
        genai.configure(api_key=api_key)
        model = genai.GenerativeModel(model_name="models/gemini-1.5-pro-latest")

        timeline_analysis_str = json.dumps(analysis_data, indent=2)
        strategy_map_str = json.dumps(strategy_map, indent=2)

        prompt = CREATIVE_DIRECTOR_PROMPT.format(
            video_duration=duration,
            product_name=product_name,
            product_features=product_features,
            strategy_map=strategy_map_str,
            timeline_analysis=timeline_analysis_str,
        )

        print("Generating creative brief with Gemini 1.5 Pro...")
        response = model.generate_content(prompt)

        brief_json_str = response.text.strip().replace("```json", "").replace("```", "")
        brief_data = json.loads(brief_json_str)

        print("Creative brief generated successfully.")
        return brief_data

    except Exception as e:
        print(f"An error occurred during creative brief generation: {e}")
        return None
