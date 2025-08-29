# video_processor.py
import os
import yt_dlp
import ffmpeg
import sys
import shutil

TEMP_DIR = "temp"
if not os.path.exists(TEMP_DIR):
    os.makedirs(TEMP_DIR)

def download_video(video_url):
    """
    Downloads a video from a given URL and returns its file path and duration.
    """
    print(f"Downloading video from: {video_url}")
    try:
        video_path = os.path.join(TEMP_DIR, 'video.mp4')
        ydl_opts = {
            'format': 'best[ext=mp4][height<=1080]',
            'outtmpl': video_path,
            'quiet': True,
            'merge_output_format': 'mp4',
            'overwrites': True,
        }
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            ydl.download([video_url])
        
        print(f"Video downloaded successfully to: {video_path}")
        
        # Get video duration using ffmpeg
        probe = ffmpeg.probe(video_path)
        duration = float(probe['format']['duration'])
        print(f"Video duration: {duration:.2f} seconds")
        
        return video_path, duration
    except Exception as e:
        print(f"An error occurred during video download/probing: {e}")
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
        return
    for name in os.listdir(TEMP_DIR):
        path = os.path.join(TEMP_DIR, name)
        try:
            if os.path.isfile(path) or os.path.islink(path):
                os.unlink(path)
            elif os.path.isdir(path):
                shutil.rmtree(path)
        except Exception as e:
            print(f"Failed to delete {path}: {e}")
