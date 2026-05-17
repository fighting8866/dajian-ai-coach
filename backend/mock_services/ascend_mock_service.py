from __future__ import annotations

from fastapi import FastAPI

app = FastAPI(title="Ascend Mock Service", version="v1")


def _pick_request_id(payload: dict) -> str:
    request_id = ""
    if isinstance(payload, dict):
        request_id = str(payload.get("request_id") or "").strip()
    return request_id or "mock-request"


@app.get("/health")
def health() -> dict:
    return {"status": "ok", "service": "ascend-mock"}


@app.post("/mock/speech/analyze")
def mock_speech_analyze(payload: dict) -> dict:
    request_id = _pick_request_id(payload)
    return {
        "success": True,
        "provider": "ascend-mock",
        "request_id": request_id,
        "result": {
            "transcript": "这是开发板模拟返回的语音分析结果",
            "speech_rate": 180,
            "pause_count": 3,
            "avg_pause_sec": 0.7,
            "filler_count": 1,
            "audio_valid": True,
            "audio_message": "",
        },
        "error": None,
    }


@app.post("/mock/vision/analyze")
def mock_vision_analyze(payload: dict) -> dict:
    request_id = _pick_request_id(payload)
    return {
        "success": True,
        "provider": "ascend-mock",
        "request_id": request_id,
        "result": {
            "forward_gaze_ratio": 0.72,
            "downward_head_ratio": 0.12,
            "posture_stability": 0.81,
        },
        "error": None,
    }
