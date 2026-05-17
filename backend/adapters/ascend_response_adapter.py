from __future__ import annotations

from gateways.ascend_gateway.base import AscendGatewayResponse


def adapt_speech_response_to_internal(response: AscendGatewayResponse) -> dict:
    result = dict(response.result or {})
    print(
        f"[ascend.adapter.response] speech request_id={response.request_id} "
        f"provider={response.provider}"
    )
    merged = {
        "transcript": result.get("transcript", ""),
        "speech_rate": result.get("speech_rate", 0),
        "pause_count": result.get("pause_count", 0),
        "avg_pause_sec": result.get("avg_pause_sec", 0.0),
        "filler_count": result.get("filler_count", 0),
        "audio_valid": bool(result.get("audio_valid", response.success)),
        "audio_message": result.get("audio_message", ""),
        "provider": response.provider,
        "request_id": response.request_id,
    }
    for key, value in result.items():
        if key not in merged:
            merged[key] = value
    return merged


def adapt_vision_response_to_internal(response: AscendGatewayResponse) -> dict:
    result = dict(response.result or {})
    print(f"[ascend.adapter.response] raw vision result={result}")
    print(
        f"[ascend.adapter.response] vision request_id={response.request_id} "
        f"provider={response.provider}"
    )
    merged = {
        "status": result.get("status", "ascend_remote"),
        "message": result.get("message", ""),
        "forward_gaze_ratio": result.get("forward_gaze_ratio"),
        "downward_head_ratio": result.get("downward_head_ratio"),
        "posture_stability": result.get("posture_stability"),
        "vision_valid": result.get("vision_valid"),
        "vision_message": result.get("vision_message", ""),
        "vision_debug_source": result.get("vision_debug_source"),
        "vision_debug_provider": result.get("vision_debug_provider"),
        "vision_debug_request_id": result.get("vision_debug_request_id"),
        "provider": response.provider,
        "request_id": response.request_id,
    }
    for key, value in result.items():
        if key not in merged:
            merged[key] = value
    print(f"[ascend.adapter.response] mapped vision result={merged}")
    return merged
