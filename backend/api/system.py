from __future__ import annotations

import json
import urllib.request
from typing import Any

from fastapi import APIRouter

from config import settings
from factories.provider_factory import get_ai_provider_status

router = APIRouter()

_ASCEND_HEALTH_PROBE_TIMEOUT_S = 3.0

_RUNTIME_EVIDENCE_KEYS = (
    "hostname",
    "platform_system",
    "platform_machine",
    "platform_release",
    "python_version",
    "python_executable",
    "cwd",
    "service_root",
    "temp_dir",
    "local_ip",
    "process_id",
    "runtime_label",
)


def _ascend_service_runtime_from_body(body: Any) -> dict[str, Any] | None:
    if not isinstance(body, dict):
        return None
    if "runtime_label" not in body and "hostname" not in body:
        return None
    return {key: body.get(key) for key in _RUNTIME_EVIDENCE_KEYS if key in body}


@router.get("/system/provider-status")
def provider_status() -> dict[str, Any]:
    base = get_ai_provider_status()
    url = (settings.ASCEND_BASE_URL or "").strip().rstrip("/")
    checked_url: str | None = None
    ascend_reachable: bool | None = None
    ascend_body: dict[str, Any] | None = None
    ascend_error: str | None = None

    if url:
        checked_url = f"{url}/health"
        try:
            req = urllib.request.Request(checked_url, method="GET")
            with urllib.request.urlopen(req, timeout=_ASCEND_HEALTH_PROBE_TIMEOUT_S) as resp:
                raw = resp.read().decode("utf-8", errors="replace")
                ascend_body = json.loads(raw) if raw.strip().startswith("{") else {"raw": raw[:800]}
                ascend_reachable = True
        except Exception as exc:
            ascend_reachable = False
            ascend_error = str(exc)[:500]
            ascend_body = None
    else:
        ascend_body = {
            "note": "ASCEND_BASE_URL is not configured, so backend cannot probe the board service.",
        }

    speech_provider = str(base.get("speech_provider") or "").strip().lower()
    vision_provider = str(base.get("vision_provider") or "").strip().lower()
    board_inference_enabled = speech_provider == "ascend" or vision_provider == "ascend"
    board_address_ready = bool(base.get("ascend_base_url_configured"))

    if board_inference_enabled and not board_address_ready:
        system_health_hint = "board_url_missing"
    elif board_inference_enabled and ascend_reachable is False:
        system_health_hint = "board_unreachable"
    else:
        system_health_hint = "ok"

    ascend_service_runtime = (
        _ascend_service_runtime_from_body(ascend_body) if isinstance(ascend_body, dict) else None
    )

    return {
        **base,
        "board_inference_enabled": board_inference_enabled,
        "board_address_ready": board_address_ready,
        "system_health_hint": system_health_hint,
        "ascend_service_runtime": ascend_service_runtime,
        "recommended_long_session_strategy": {
            "current_mode": "whole-file-upload",
            "next_stage_target": "chunked-audio-and-windowed-vision",
            "note": "For competition demo, keep the current full-upload path stable before evolving long-session slicing.",
            "doc": "docs/long_session_support_v1.md",
        },
        "ascend_health_check": {
            "reachable": ascend_reachable,
            "checked_url": checked_url,
            "probe_timeout_seconds": _ASCEND_HEALTH_PROBE_TIMEOUT_S,
            "response": ascend_body,
            "error": ascend_error,
        },
    }
