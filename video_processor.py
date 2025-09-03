# video_processor.py
import os
import tempfile
import uuid
import time
from typing import Tuple, Optional

import yt_dlp
import google.generativeai as genai

TEMP_DIR = tempfile.gettempdir()

def download_video(url: str) -> Tuple[Optional[str], Optional[float]]:
    """Downloads a video from a URL to a temporary directory and returns the path and duration."""
    video_id = str(uuid.uuid4())
    output_path = os.path.join(TEMP_DIR, f"{video_id}.mp4")

    ydl_opts = {
        'format': 'bestvideo[ext=mp4]+bestaudio[ext=m4a]/best[ext=mp4]/best',
        'outtmpl': output_path,
        'quiet': True,
    }

    actual_duration = None
    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info_dict = ydl.extract_info(url, download=True)
            actual_duration = info_dict.get('duration')

        # Verify the file was downloaded
        if not os.path.exists(output_path):
            # Fallback for cases where the filename is different
            base_name = os.path.splitext(output_path)[0]
            for f in os.listdir(TEMP_DIR):
                if f.startswith(video_id):
                    output_path = os.path.join(TEMP_DIR, f)
                    break
            if not os.path.exists(output_path):
                 raise FileNotFoundError(f"Failed to find downloaded video for URL: {url}")
        
        return output_path, actual_duration
    
    except Exception as e:
        print(f"Error downloading video: {e}")
        return None, None


def cleanup_temp_dir():
    """Removes temporary video files."""
    for f in os.listdir(TEMP_DIR):
        if f.endswith(".mp4"):
            try:
                os.remove(os.path.join(TEMP_DIR, f))
            except OSError as e:
                print(f"Error removing file {f}: {e}")

def upload_to_gemini(path: str, mime_type: str) -> Optional[genai.client.File]:
    """Uploads a file to Gemini."""
    try:
        return genai.upload_file(path=path, mime_type=mime_type)
    except Exception as e:
        print(f"Error uploading to Gemini: {e}")
        return None

def delete_uploaded_file(uri: str):
    """Deletes a file from Gemini."""
    try:
        genai.delete_file(name=uri)
    except Exception as e:
        print(f"Error deleting file {uri}: {e}")
