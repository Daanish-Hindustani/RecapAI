import json
from typing import List, Dict, Tuple
from pydantic import BaseModel


class TranscriptEntry(BaseModel):
    start: float  # in seconds
    text: str

class TranscriptInput(BaseModel):
    transcript: List[TranscriptEntry]


class SummarySegment(BaseModel):
    start: float
    end: float
    summary: str    


class LLMOutput(BaseModel):
    segments: List[SummarySegment]