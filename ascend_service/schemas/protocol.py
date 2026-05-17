from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field


class SpeechAnalyzePayload(BaseModel):
    audio_path: str = ""
    options: dict[str, Any] = Field(default_factory=dict)


class VisionAnalyzePayload(BaseModel):
    video_path: str = ""
    options: dict[str, Any] = Field(default_factory=dict)


class SpeechAnalyzeResult(BaseModel):
    transcript: str
    speech_rate: float
    pause_count: int
    avg_pause_sec: float
    filler_count: int
    audio_valid: bool
    audio_message: str


class VisionAnalyzeResult(BaseModel):
    forward_gaze_ratio: float
    downward_head_ratio: float
    posture_stability: float


class AscendSpeechAnalyzeRequest(BaseModel):
    request_id: str = ""
    task: str = "speech_analyze"
    payload: SpeechAnalyzePayload


class AscendVisionAnalyzeRequest(BaseModel):
    request_id: str = ""
    task: str = "vision_analyze"
    payload: VisionAnalyzePayload


class AscendResponse(BaseModel):
    success: bool
    provider: str
    request_id: str
    result: dict[str, Any] = Field(default_factory=dict)
    error: str | None = None
