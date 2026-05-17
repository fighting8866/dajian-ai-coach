"""混合点评：优先模型占位，校验失败或异常则回退规则。"""

from __future__ import annotations

import traceback
from typing import Any

from factories.provider_factory import get_commentary_model_backend
from services.commentary_generation_utils import attach_commentary_execution_meta, commentary_bundle_valid
from services.model_commentary_provider import generate_model_commentary_bundle
from services.rule_commentary_provider import generate_rule_commentary_bundle


def generate_hybrid_commentary_bundle(**kw: Any) -> tuple[dict[str, Any], dict[str, Any]]:
    backend = get_commentary_model_backend()
    try:
        m_bundle, m_extra = generate_model_commentary_bundle(**kw)
        if commentary_bundle_valid(m_bundle):
            mode = f"commentary_hybrid_model_{backend}_v1"
            bundle = attach_commentary_execution_meta(
                m_bundle,
                configured_kind="hybrid",
                generation_mode=mode,
                fallback_to_rule=False,
                model_backend=backend,
                effective_provider="model",
            )
            extra: dict[str, Any] = {
                "generation_mode": mode,
                "fallback_to_rule": False,
                "effective_provider": "model",
                "commentary_model_backend": backend,
            }
            return bundle, extra
    except Exception:
        print("[hybrid_commentary] model path failed:\n" + traceback.format_exc(), flush=True)

    r_bundle, r_extra = generate_rule_commentary_bundle(**kw)
    mode = f"commentary_hybrid_fallback_rule_{backend}_v1"
    bundle = attach_commentary_execution_meta(
        r_bundle,
        configured_kind="hybrid",
        generation_mode=mode,
        fallback_to_rule=True,
        model_backend=backend,
        effective_provider="rule",
    )
    extra = {
        "generation_mode": mode,
        "fallback_to_rule": True,
        "effective_provider": "rule",
        "commentary_model_backend": backend,
    }
    return bundle, extra
