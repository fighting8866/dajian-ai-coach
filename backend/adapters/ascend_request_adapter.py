from __future__ import annotations

import os
import uuid
from typing import Any

from gateways.ascend_gateway.base import AscendSpeechAnalyzeRequest, AscendVisionAnalyzeRequest


def build_speech_analyze_request(
    audio_path: str,
    *,
    analysis_phase: str = "lecture",
    options: dict[str, Any] | None = None,
    request_id: str | None = None,
) -> AscendSpeechAnalyzeRequest:
    normalized_path = str(audio_path or "").strip()
    upload_file_name = os.path.basename(normalized_path) or "speech_upload.wav"
    phase = str(analysis_phase or "lecture").strip() or "lecture"
    req = AscendSpeechAnalyzeRequest(
        request_id=request_id or uuid.uuid4().hex,
        payload={
            # 兼容保留：仅用于日志或回溯，不再用于远端读取
            "audio_path": normalized_path,
            # 文件上传协议字段
            "upload_file_path": normalized_path,
            "upload_file_name": upload_file_name,
            "analysis_phase": phase,
            "options": options or {},
        },
    )
    print(
        "[ascend.adapter.request] speech request_id="
        f"{req.request_id} upload_file_name={upload_file_name} "
        f"upload_file_path={normalized_path} analysis_phase={phase!r}"
    )
    return req


def build_vision_analyze_request(
    video_path: str,
    *,
    options: dict[str, Any] | None = None,
    request_id: str | None = None,
) -> AscendVisionAnalyzeRequest:
    normalized_path = str(video_path or "").strip()
    upload_file_name = os.path.basename(normalized_path) or "vision_upload.webm"
    req = AscendVisionAnalyzeRequest(
        request_id=request_id or uuid.uuid4().hex,
        payload={
            # 兼容保留：仅用于日志或回溯，不再用于远端读取
            "video_path": normalized_path,
            # 文件上传协议字段
            "upload_file_path": normalized_path,
            "upload_file_name": upload_file_name,
            "options": options or {},
        },
    )
    print(
        "[ascend.adapter.request] vision request_id="
        f"{req.request_id} upload_file_name={upload_file_name} "
        f"upload_file_path={normalized_path}"
    )
    return req
