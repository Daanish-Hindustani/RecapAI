import json
from typing import List, Dict, Tuple
from models import TranscriptEntry, TranscriptInput, SummarySegment, LLMOutput
from youtube_transcript_api import YouTubeTranscriptApi
from ollama import chat
from saved_data import val
from prompt import get_prompt
from google import genai
import os
from dotenv import load_dotenv
load_dotenv()
client = genai.Client(api_key=os.getenv("GEMINI_API_KEY"))

# --- Get Transcript Function ---

def get_transcript(video_id: str) -> List[TranscriptEntry]:
    try:
        raw_transcript = YouTubeTranscriptApi.get_transcript(video_id)
        return [TranscriptEntry(start=entry['start'], text=entry['text']) for entry in raw_transcript]
    except Exception as e:
        raise RuntimeError(f"Transcript fetch error: {e}")


# --- LLM Query Function ---

def llm_query(data: TranscriptInput) -> LLMOutput:
    response_content = "" # Initialize to an empty string for error handling scope
    try:
        chunks = "\n".join([f"[{entry.start:.2f}s] {entry.text}" for entry in data.transcript])
        print(chunks)
        prompt = get_prompt(chunks)

        response = chat(
            messages=[
                {
                'role': 'user',
                'content': prompt,
                }
            ],
            model='deepseek-r1:1.5b',
            format=LLMOutput.model_json_schema(),
        )
        # response = client.models.generate_content(
        #     model='gemini-2.0-flash',
        #     contents=prompt,
        #     config={
        #         'response_mime_type': 'application/json',
        #         'response_schema': LLMOutput,
        #     },
        # )
        #response_content: LLMOutput = response.parsed
        response_content: LLMOutput = LLMOutput.model_validate_json(response.message.content)
        print(response_content)
        return response_content

    except json.JSONDecodeError as e:
        # Include the raw content in the error message for debugging
        raise ValueError(f"Failed to parse LLM output as JSON. Raw output: '{response_content}'. Error: {e}")
    except KeyError as e:
        raise ValueError(f"Unexpected structure in Ollama response. Missing key: {e}. Full response: {response}")
    except Exception as e:
        raise ValueError(f"An unexpected error occurred in llm_query: {e}")


# --- Example Usage ---

if __name__ == "__main__":
    video_id = "9-Jl0dxWQs8"
    # transcript = get_transcript(video_id)
    transcript = val
    print(transcript)
    input_model = TranscriptInput(transcript=transcript)
    
    result = llm_query(input_model)
    for seg in result.segments:
        print(f"[{seg.start:.2f}s - {seg.end:.2f}s]: {seg.summary}")