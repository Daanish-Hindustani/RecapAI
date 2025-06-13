# main.py
import os
from utilities import get_transcript, llm_query, TranscriptInput
from video_editor import download_youtube_video, create_recap_video
from saved_data import val

def main():
    # --- Configuration ---
    video_url = "https://www.youtube.com/watch?v=9-Jl0dxWQs8" # Replace with your target video URL
    video_id = "9-Jl0dxWQs8" # Extracted from the URL
    target_recap_duration_minutes = 5 # Desired length of the summarized content
    download_output_path = "original_video.mp4"
    final_output_path = "final_recap_video.mp4"
    interstitial_clip_duration = 5 # Duration of the summary text clips in seconds

    print("--- Starting Video Recap Generation ---")

    try:
        # 1. Download the YouTube video
        #downloaded_video_file = download_youtube_video(video_url, download_output_path)

        # 2. Get the transcript (either fetched or pre-saved)
        # transcript = get_transcript(video_id=video_id) # Fetch new transcript
        #transcript = get_transcript(video_id) # Use pre-saved transcript (if setup in utilities.py)
        transcript = val
        # 3. Query LLM for summary segments
        print(f"Querying LLM for summary...")
        input_model = TranscriptInput(
            transcript=transcript,
        )
        llm_output = llm_query(input_model)
        
        if not llm_output.segments:
            print("LLM returned no summary segments. Exiting.")
            return

        print("\n--- LLM Summary Segments ---")
        for seg in llm_output.segments:
            print(f"[{seg.start:.2f}s - {seg.end:.2f}s]: {seg.summary}")
        print("----------------------------")

        # 4. Create the recap video with interstitials
        print("Starting video editing process...")
        create_recap_video(
            #video_path=downloaded_video_file,
            video_path= download_output_path,
            summary_segments=llm_output.segments,
            output_filename=final_output_path,
            interstitial_duration=interstitial_clip_duration
        )
        print(f"\n--- Recap video successfully created: {final_output_path} ---")

    except Exception as e:
        print(f"\nAn error occurred: {e}")
    finally:
        # Optional: Clean up downloaded video after processing
        # if os.path.exists(download_output_path):
        #     os.remove(download_output_path)
        #     print(f"Cleaned up {download_output_path}")
        pass

if __name__ == "__main__":
    main()