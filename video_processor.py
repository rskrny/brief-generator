# video_processor.py
import os
import yt_dlp
import ffmpeg
import sys

# --- UPDATED SECTION ---
# Get the base path for PyInstaller or local execution
base_path = getattr(sys, '_MEIPASS', os.path.dirname(os.path.abspath(__file__)))

# Define platform-agnostic paths to our local executables
# We remove the .exe so it works on both Windows and Linux
TEMP_DIR = os.path.join(base_path, "temp")
FFMPEG_PATH = os.path.join(base_path, "bin", "ffmpeg")
YT_DLP_PATH = os.path.join(base_path, "bin", "yt-dlp")
# --- END UPDATED SECTION ---


if not os.path.exists(TEMP_DIR):
    os.makedirs(TEMP_DIR)

def download_video(video_url):
    """
    Downloads a video from a given URL to the temporary directory.
    Returns the file path of the downloaded video.
    """
    print(f"Downloading video from: {video_url}")
    try:
        ydl_opts = {
            'format': 'best[ext=mp4][height<=1080]',
            'outtmpl': os.path.join(TEMP_DIR, 'video.mp4'),
            'quiet': True,
            'merge_output_format': 'mp4',
            'overwrites': True,
            'ffmpeg_location': FFMPEG_PATH,
            # yt-dlp library now uses an internal exe, so yt_dlp_path is not needed
        }
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            ydl.download([video_url])
        
        video_path = os.path.join(TEMP_DIR, 'video.mp4')
        print(f"Video downloaded successfully to: {video_path}")
        return video_path
    except Exception as e:
        print(f"An error occurred during video download: {e}")
        return None

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
                .output(screenshot_path, vframes=1, qscale_v=2)
                .overwrite_output()
                .run(cmd=FFMPEG_PATH, quiet=True)
            )
            screenshot_paths.append(screenshot_path)
            print(f"  - Screenshot {i+1} saved to: {screenshot_path}")
        except ffmpeg.Error as e:
            print(f"An ffmpeg error occurred for timestamp {ts}: {e}")
            continue
    
    print("Screenshot extraction complete.")
    return screenshot_paths
