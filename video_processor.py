# video_processor.py
import os
import yt_dlp
import ffmpeg
import sys
import shutil
import time
import google.generativeai as genai

TEMP_DIR = "temp"

def download_video(video_url):
    """
    Downloads a video from a given URL to a temporary directory
    and returns its file path and duration.
    """
    print(f"Attempting to download video from: {video_url}")
    
    if not os.path.exists(TEMP_DIR):
        os.makedirs(TEMP_DIR)
        print(f"Created temporary directory: {TEMP_DIR}")

    video_path = os.path.join(TEMP_DIR, 'video.mp4')
    
    ydl_opts = {
        'format': 'best[ext=mp4][height<=1080]',
        'outtmpl': video_path,
        'quiet': True,
        'merge_output_format': 'mp4',
        'overwrites': True,
    }
    
    try:
        print("Starting video download with yt-dlp...")
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            ydl.download([video_url])
        
        if not os.path.exists(video_path):
            print("Download failed: video file not found after yt-dlp execution.")
            return None, None
            
        print(f"Video downloaded successfully to: {video_path}")
        
        print("Probing video file with ffmpeg to get duration...")
        probe = ffmpeg.probe(video_path)
        duration = float(probe['format']['duration'])
        print(f"Video duration detected: {duration:.2f} seconds")
        
        return video_path, duration
    except Exception as e:
        print(f"An error occurred during video download or processing: {e}", file=sys.stderr)
        return None, None

def upload_to_gemini(path, mime_type=None):
    """Uploads a file to the Gemini API."""
    print(f"Uploading file: {path}")
    file = genai.upload_file(path, mime_type=mime_type)
    print(f"Uploaded file '{file.display_name}' as: {file.name}")
    return file

def delete_uploaded_file(uri: str):
    """Deletes a file that has been uploaded to the Gemini API."""
    print(f"Deleting uploaded file: {uri}")
    try:
        genai.delete_file(uri)
        print("File deleted successfully.")
    except Exception as e:
        print(f"Failed to delete file {uri}: {e}", file=sys.stderr)

def cleanup_temp_dir():
    """Remove all files and folders inside the temporary directory."""
    if not os.path.exists(TEMP_DIR):
        print("Temporary directory does not exist, nothing to clean up.")
        return
        
    print(f"Cleaning up temporary directory: {TEMP_DIR}")
    try:
        shutil.rmtree(TEMP_DIR)
        print("Temporary directory and its contents removed successfully.")
    except Exception as e:
        print(f"Failed to delete temporary directory {TEMP_DIR}: {e}", file=sys.stderr)
