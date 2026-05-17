"""规则点评：复用 coach_service.build_coach_output。"""

from __future__ import annotations

from typing import Any

from services.coach_service import build_coach_output
from services.commentary_generation_utils import attach_commentary_execution_meta


def generate_rule_commentary_bundle(**kw: Any) -> tuple[dict[str, Any], dict[str, Any]]:
    raw = build_coach_output(**kw)
    mode = "commentary_rule_v1"
    bundle = attach_commentary_execution_meta(
        raw,
        configured_kind="rule",
        generation_mode=mode,
        fallback_to_rule=False,
        model_backend=None,
        effective_provider="rule",
    )
    extra: dict[str, Any] = {
        "generation_mode": mode,
        "fallback_to_rule": False,
        "effective_provider": "rule",
        "commentary_model_backend": None,
    }
    return bundle, extra
