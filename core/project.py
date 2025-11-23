# core/project.py
from dataclasses import dataclass, field
from typing import List, Dict

@dataclass
class Subtitle:
    start: float
    end: float
    text: str

class ProjectState:
    def __init__(self):
        self.video_path: str = None
        self.duration: float = 0.0
        self.subtitles: List[Dict] = [] # Stores dictionaries of subtitles
        self.waveform_points: List[float] = []
        self.video_clip = None # Store MoviePy clip ref if needed (optional)

    def clear(self):
        self.video_path = None
        self.duration = 0.0
        self.subtitles = []
        self.waveform_points = []