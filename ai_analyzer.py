# ai_analyzer.py
import google.generativeai as genai
import time
import json
from prompts import ANALYST_PROMPT # Import the prompt we created earlier

def get_video_analysis(api_key, video_path):
    """
    Analyzes the video using Gemini's Pass 1 "Analyst" prompt.
    Returns a dictionary with the influencerDNA and keyMoments.
    """
    print("Starting AI video analysis...")
    try:
        genai.configure(api_key=api_key)

        # 1. Upload the video file to the Gemini API
        print("Uploading video file to Gemini...")
        video_file = genai.upload_file(path=video_path)

        # 2. Wait for the video to be processed by Gemini
        while video_file.state.name == "PROCESSING":
            print("Waiting for video processing...")
            time.sleep(10) # Wait 10 seconds before checking again
            video_file = genai.get_file(video_file.name)

        if video_file.state.name == "FAILED":
            raise ValueError("Gemini video processing failed.")
        
        print("Video processed successfully by Gemini.")

        # 3. Make the generative model call
        model = genai.GenerativeModel(model_name="models/gemini-1.5-pro-latest")
        print("Generating analysis with Gemini 1.5 Pro...")
        response = model.generate_content([ANALYST_PROMPT, video_file])
        
        # 4. Clean up the file from the Gemini server to save space
        print("Deleting uploaded file from Gemini server...")
        genai.delete_file(video_file.name)

        # 5. Parse the JSON response from the AI
        analysis_json = response.text.strip().replace("```json", "").replace("```", "")
        analysis_data = json.loads(analysis_json)
        
        print("AI analysis complete.")
        return analysis_data

    except Exception as e:
        print(f"An error occurred during AI analysis: {e}")
        return None