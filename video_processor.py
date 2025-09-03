# video_processor.py
import os
import yt_dlp
import ffmpeg
import sys
import shutil

TEMP_DIR = "temp"

def download_video(video_url):
    """
    Downloads a video from a given URL to a temporary directory
    and returns its file path and duration.
    """
    print(f"Attempting to download video from: {video_url}")
    
    # Ensure the temp directory exists
    if not os.path.exists(TEMP_DIR):
        os.makedirs(TEMP_DIR)
        print(f"Created temporary directory: {TEMP_DIR}")

    video_path = os.path.join(TEMP_DIR, 'video.mp4')
    
    ydl_opts = {
        'format': 'best[ext=mp4][height<=1080]', # Download best MP4 quality up to 1080p
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
        
        # Get video duration using ffmpeg
        print("Probing video file with ffmpeg to get duration...")
        probe = ffmpeg.probe(video_path)
        duration = float(probe['format']['duration'])
        print(f"Video duration detected: {duration:.2f} seconds")
        
        return video_path, duration
    except Exception as e:
        print(f"An error occurred during video download or processing: {e}", file=sys.stderr)
        return None, None

def extract_screenshots(video_path, timestamps):
    """
    Extracts screenshots from a video at specific timestamps.
    Returns a list of file paths for the extracted screenshots.
    """
    print(f"Extracting screenshots from: {video_path}")
    screenshot_paths = []
    for i, ts in enumerate(timestamps):
        screenshot_path = os.path.join(TEMP_DIR, f'screenshot_{i+1}.jpg')
        try:
            (
                ffmpeg
                .input(video_path, ss=ts)
                .output(screenshot_path, vframes=1, **{'q:v': 2})
                .overwrite_output()
                .run(quiet=True)
            )
            screenshot_paths.append(screenshot_path)
            print(f"  - Screenshot {i+1} saved to: {screenshot_path}")
        except ffmpeg.Error as e:
            print(f"An ffmpeg error occurred for timestamp {ts}. Stderr: {e.stderr.decode('utf8')}")
            continue
    
    print("Screenshot extraction complete.")
    return screenshot_paths


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
