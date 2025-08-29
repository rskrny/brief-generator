# ai_analyzer.py


import google.generativeai as genai
import time
import json
from prompts import ANALYST_PROMPT, CREATIVE_DIRECTOR_PROMPT





def parse_gemini_json(raw: str) -> dict | None:
    """Parse JSON output from Gemini, stripping code fences.

    Args:
        raw: Raw string returned by Gemini which may include code fences.

    Returns:
        Parsed JSON as a dictionary or ``None`` if parsing fails.
    """
    cleaned = raw.strip()
    if cleaned.startswith("```") and cleaned.endswith("```"):
        lines = cleaned.splitlines()
        if lines[0].startswith("```"):
            lines = lines[1:]
        if lines and lines[-1].startswith("```"):
            lines = lines[:-1]
        cleaned = "\n".join(lines)
    try:
        return json.loads(cleaned)
    except json.JSONDecodeError as exc:
        print(f"Warning: failed to parse Gemini JSON response: {exc}")
        return None

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

        analysis_data = parse_gemini_json(response.text)
        if analysis_data is None:
            print("Failed to parse timeline analysis JSON.")
            return None

        print("AI timeline analysis complete.")
        return analysis_data

    except Exception as e:
        print(f"An error occurred during AI analysis: {e}")
        return None

def generate_creative_brief(api_key, product_name, analysis_data, duration):
    """
    Generates the creative brief using the "Creative Director" prompt.
    """
    print("Starting creative brief generation...")
    try:
        genai.configure(api_key=api_key)
        model = genai.GenerativeModel(model_name="models/gemini-1.5-pro-latest")

        timeline_analysis_str = json.dumps(analysis_data, indent=2)

        prompt = CREATIVE_DIRECTOR_PROMPT.format(
            video_duration=duration,
            product_name=product_name,
            timeline_analysis=timeline_analysis_str
        )
        
        print("Generating creative brief with Gemini 1.5 Pro...")
        response = model.generate_content(prompt)
        
        brief_data = parse_gemini_json(response.text)
        if brief_data is None:
            print("Failed to parse creative brief JSON.")
            return None

        print("Creative brief generated successfully.")
        return brief_data

    except Exception as e:
        print(f"An error occurred during creative brief generation: {e}")
        return None

