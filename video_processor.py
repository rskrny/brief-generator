# video_processor.py
import os
import yt_dlp
import ffmpeg
import sys

TEMP_DIR = "temp"
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
                .run(quiet=True)
            )
            screenshot_paths.append(screenshot_path)
            print(f"  - Screenshot {i+1} saved to: {screenshot_path}")
        except ffmpeg.Error as e:
            # This line is updated to provide a more detailed error
            print(f"An ffmpeg error occurred for timestamp {ts}. Stderr: {e.stderr.decode('utf8')}")
            continue
    
    print("Screenshot extraction complete.")
    return screenshot_paths
