import subprocess
import os
import tempfile
from moviepy import VideoFileClip, TextClip, CompositeVideoClip, ColorClip, AudioClip, video
from typing import List
import numpy as np
from moviepy.audio.AudioClip import AudioArrayClip

# Placeholder for SummarySegment - assuming it's defined elsewhere, e.g., in models.py
# If you don't have a models.py, uncomment and use this simple class:
class SummarySegment:
    def __init__(self, start: float, end: float, summary: str):
        self.start = start
        self.end = end
        self.summary = summary

def download_youtube_video(video_url: str, output_path: str = "downloaded_video.mp4") -> str:
    """
    Downloads a YouTube video using yt-dlp with performance optimizations.
    Returns the path to the downloaded video file.
    """
    if os.path.exists(output_path):
        print(f"Video already downloaded at {output_path}. Skipping download.")
        return output_path

    print(f"Downloading video from {video_url}...")
    try:
        command = [
            "yt-dlp",
            "--no-playlist",
            "--no-check-certificate",
            "-f", "bestvideo[ext=mp4]+bestaudio[ext=m4a]/mp4",
            "-o", output_path,
            video_url
        ]
        # Use capture_output=True for better error reporting
        result = subprocess.run(command, check=True, capture_output=True, text=True)
        print(f"Video downloaded to: {output_path}")
        print(f"yt-dlp stdout:\n{result.stdout}") # Add stdout for more info
        return output_path
    except subprocess.CalledProcessError as e:
        print(f"Error during video download: {e.stderr}")
        raise RuntimeError(f"Failed to download video: {e.stderr}")
    except FileNotFoundError:
        raise RuntimeError("yt-dlp not found. Install it and ensure it's in your PATH.")


def create_summary_interstitial(summary_text: str, duration: int = 5, video_width: int = 1280, video_height: int = 720) -> ColorClip:
    """
    Creates a short video clip with the summary text on a black background, **ensuring it is silent**.
    """
    bg_clip = ColorClip(size=(video_width, video_height), color=(0, 0, 0), duration=duration)

    try:
        # Using a common font for broader compatibility if 'cmunbi.ttf' is not guaranteed
        # You can specify the full path if it's a custom font not in system paths.
        font_path = 'Arial-Bold' # A common system font
        if not os.path.exists(font_path): # Check if it's a full path, otherwise assume system font name
            font_path = 'sans' # Fallback to a generic sans-serif if Arial-Bold isn't found
            print(f"Warning: '{font_path}' font not found or not specified as full path. Falling back to generic sans-serif.")

        text_clip = TextClip(
            text=summary_text,
            fontsize=70, # Corrected to fontsize
            color='white',
            font=font_path,
            size=(int(video_width*0.8), int(video_height*0.5)),
            duration=duration,
            method='caption',
            align="center", # Corrected to align
        )
        text_clip = text_clip.set_position(("center", "center")) # Use set_position for clarity
    except Exception as e:
        print(f"TextClip creation failed: {e}. Using fallback text and font.")
        text_clip = TextClip("Summary unavailable", fontsize=60, color='white', duration=duration, method='caption', align="center", font='sans')

    final_clip = CompositeVideoClip([bg_clip, text_clip])

    # --- Explicitly create a silent audio track for the interstitial ---
    # The 'get_frame' function for the AudioClip always returns 0 for silence.
    # A standard audio sample rate (e.g., 44100 Hz) is used.
    # This is crucial for seamless audio concatenation by FFmpeg.
    silent_array = np.zeros((int(final_clip.duration * 44100), 2))
    silent_audio = AudioArrayClip(silent_array, fps=44100)
    return final_clip


def create_recap_video(
    video_path: str,
    summary_segments: List['SummarySegment'],
    output_filename: str = "recap_video.mp4",
    interstitial_duration: int = 5
) -> str:
    """
    Creates a recap video by clipping segments and adding summary interstitials.
    Ensures summary sections are silent.
    """
    if not os.path.exists(video_path):
        raise FileNotFoundError(f"Original video not found at: {video_path}")

    temp_dir = tempfile.mkdtemp()
    clip_paths = []
    original_video = None # Initialize to None for finally block

    try:
        original_video = VideoFileClip(video_path)
        video_width, video_height = original_video.w, original_video.h

        # Determine a consistent audio sample rate for all temporary clips
        # Default to 44100 Hz if original video has no audio or its audio.fps is None
        target_audio_fps = original_video.audio.fps if original_video.audio and original_video.audio.fps else 44100
        print(f"Using target audio sample rate: {target_audio_fps} Hz")

        for i, segment in enumerate(summary_segments):
            start_time = segment.start
            end_time = segment.end

            print(f"Processing segment {i+1}: [{start_time:.2f}s - {end_time:.2f}s] - {segment.summary}")

            # --- Create and save Interstitial Clip (SILENT) ---
            interstitial_clip = create_summary_interstitial(
                f"Summary {i+1}: {segment.summary}",
                duration=interstitial_duration,
                video_width=video_width,
                video_height=video_height,
            )
            interstitial_path = os.path.join(temp_dir, f"interstitial_{i}.mp4")

            print(f"Writing silent interstitial to: {interstitial_path}")
            interstitial_clip.write_videofile(
                interstitial_path,
                codec="libx264",
                audio_codec="aac", # AAC is good for compatibility
                fps=24, # Standardize video FPS for output clips
                audio_fps=target_audio_fps, # Crucial for audio consistency
                # Suppress output of moviepy writes for cleaner console during loop
                verbose=False, logger=None
            )
            clip_paths.append(interstitial_path)
            interstitial_clip.close() # Close to release resources

            # --- Create and save Original Video Subclip ---
            clip_start = max(0, start_time)
            clip_end = min(original_video.duration, end_time)
            if clip_end <= clip_start:
                print(f"Warning: Segment {i+1} has invalid times ({start_time}-{end_time}). Skipping video clip.")
                continue

            try:
                # Extract subclip
                video_clip = original_video.subclip(clip_start, clip_end)

                # Apply fade effects only if the clip duration allows (e.g., longer than fade duration * 2)
                # This check prevents errors on very short clips where fade duration is too long.
                fade_duration = 2
                if video_clip.duration > (fade_duration * 2):
                    video_clip = video_clip.fx(video.fadein, fade_duration).fx(video.fadeout, fade_duration)
                else:
                    print(f"Note: Segment {i+1} duration ({video_clip.duration:.2f}s) too short for {fade_duration}s fades. Skipping fade effects.")

                clip_path = os.path.join(temp_dir, f"clip_{i}.mp4")
                print(f"Writing video segment to: {clip_path}")
                video_clip.write_videofile(
                    clip_path,
                    codec="libx264",
                    audio_codec="aac",
                    fps=24, # Standardize video FPS
                    audio_fps=target_audio_fps, # Crucial for audio consistency
                    # Suppress output of moviepy writes
                    verbose=False, logger=None
                )
                clip_paths.append(clip_path)
                video_clip.close() # Close to release resources
            except Exception as e:
                print(f"Error creating subclip for segment {i+1} ({start_time}-{end_time}): {e}. Skipping video clip.")
                continue

        if not clip_paths:
            raise ValueError("No video clips or interstitials were generated. Check segment data or processing errors.")

        print("Concatenating all video segments and summaries using FFmpeg complex filtergraph...")

        # --- Construct FFmpeg command for concat filtergraph ---
        input_args = []
        filter_str_video = ""
        filter_str_audio = ""

        for idx, path in enumerate(clip_paths):
            input_args.extend(["-i", path])
            # [idx:v:0] selects the first video stream from the idx-th input
            filter_str_video += f"[{idx}:v:0]"
            # [idx:a:0] selects the first audio stream from the idx-th input
            filter_str_audio += f"[{idx}:a:0]"

        # Concatenate all video streams and all audio streams separately
        # 'v=1:a=0' for video output only, 'v=0:a=1' for audio output only
        filter_str_video += f"concat=n={len(clip_paths)}:v=1:a=0[outv]"
        filter_str_audio += f"concat=n={len(clip_paths)}:v=0:a=1[outa]"

        command = [
            "ffmpeg",
            *input_args, # Unpack all -i arguments
            "-filter_complex", f"{filter_str_video};{filter_str_audio}",
            "-map", "[outv]", # Map the concatenated video stream
            "-map", "[outa]", # Map the concatenated audio stream
            "-c:v", "libx264",
            "-preset", "ultrafast", # Good balance of speed and quality
            "-crf", "23", # Constant Rate Factor for quality control (lower is better, 18-28 common)
            "-c:a", "aac",
            "-b:a", "192k", # Audio bitrate for AAC
            "-threads", str(os.cpu_count() or 4), # Use available CPU threads
            "-y", # Overwrite output file without asking
            output_filename
        ]

        # Print the FFmpeg command for debugging
        print("\nFFmpeg command:")
        print(" ".join(command))
        print("-" * 50)

        # Execute FFmpeg command
        process = subprocess.run(command, check=True, capture_output=True, text=True)
        print(f"FFmpeg stdout:\n{process.stdout}")
        print(f"FFmpeg stderr:\n{process.stderr}") # FFmpeg often prints progress to stderr

        print(f"Recap video saved to: {output_filename}")
        return output_filename

    except subprocess.CalledProcessError as e:
        print(f"FFmpeg command failed with error: {e.stderr}")
        raise RuntimeError(f"FFmpeg error during final video creation: {e.stderr}")
    except Exception as e:
        print(f"An unexpected error occurred: {e}")
        raise
    finally:
        if original_video:
            original_video.close()
        # Clean up temporary directory and files
        if os.path.exists(temp_dir):
            for f in os.listdir(temp_dir):
                try:
                    os.remove(os.path.join(temp_dir, f))
                except OSError as e:
                    print(f"Error removing temporary file {f}: {e}")
            try:
                os.rmdir(temp_dir)
                print(f"Temporary directory {temp_dir} removed.")
            except OSError as e:
                print(f"Error removing temporary directory {temp_dir}: {e}")