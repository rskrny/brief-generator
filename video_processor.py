# video_processor.py
import os
import tempfile
import uuid
from typing import Tuple, Optional

import yt_dlp
import google.generativeai as genai
# Correctly import the 'File' type for type hinting from the 'types' module
from google.generativeai.types import File

TEMP_DIR = tempfile.gettempdir()

def download_video(url: str) -> Tuple[Optional[str], Optional[float]]:
    """Downloads a video from a URL to a temporary directory and returns the path and duration."""
    video_id = str(uuid.uuid4())
    # Note: yt-dlp might append a different extension, so we just use the ID as a base name.
    output_tmpl = os.path.join(TEMP_DIR, f"{video_id}.%(ext)s")
    
    ydl_opts = {
        'format': 'bestvideo[ext=mp4]+bestaudio[ext=m4a]/best[ext=mp4]/best',
        'outtmpl': output_tmpl,
        'quiet': True,
    }

    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info_dict = ydl.extract_info(url, download=True)
            duration = info_dict.get('duration')
            # Get the actual path of the downloaded file
            downloaded_path = ydl.prepare_filename(info_dict)

        if not os.path.exists(downloaded_path):
            raise FileNotFoundError(f"yt-dlp reported a downloaded path that does not exist: {downloaded_path}")

        return downloaded_path, duration
    
    except Exception as e:
        print(f"Error downloading video: {e}")
        # Clean up any partial files if download fails
        for f in os.listdir(TEMP_DIR):
            if f.startswith(video_id):
                os.remove(os.path.join(TEMP_DIR, f))
        return None, None


def cleanup_temp_dir():
    """Removes temporary video files created by this tool."""
    # A simple cleanup: find files created in the last hour with our UUID pattern.
    # This is not perfect but avoids deleting other apps' temp files.
    for f in os.listdir(TEMP_DIR):
        try:
            # Check if filename matches UUID pattern (e.g., 12345678-1234-...)
            uuid.UUID(f.split('.')[0], version=4)
            file_path = os.path.join(TEMP_DIR, f)
            os.remove(file_path)
        except (ValueError, IndexError):
            # Not a file created by our app, skip it
            continue
        except OSError as e:
            print(f"Error removing temp file {f}: {e}")


# The type hint Optional[File] is now correct because of the updated import
def upload_to_gemini(path: str, mime_type: str) -> Optional[File]:
    """Uploads a file to Gemini."""
    try:
        return genai.upload_file(path=path, mime_type=mime_type)
    except Exception as e:
        print(f"Error uploading to Gemini: {e}")
        return None

def delete_uploaded_file(uri: str):
    """Deletes a file from Gemini."""
    print(f"Deleting uploaded file: {uri}")
    try:
        genai.delete_file(name=uri)
    except Exception as e:
        # Don't raise an error here, just log it, as it's a cleanup step.
        print(f"Error deleting file {uri}: {e}")
