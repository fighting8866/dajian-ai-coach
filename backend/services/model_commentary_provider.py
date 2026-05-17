"""
模型点评 provider（V1 骨架）：稳定签名，占位改写规则输出，不接真实大模型。

正式接入时：在本文件将 `_apply_model_commentary_placeholder` 替换为真实推理即可。
"""

from __future__ import annotations

from typing import Any

from config import settings
from factories.provider_factory import get_commentary_model_backend
from services.coach_service import build_coach_output
from services.commentary_generation_utils import attach_commentary_execution_meta, clean_string_list


def _tag_for_backend(backend: str) -> str:
    return {"qwen": "Qwen", "mock": "Mock", "custom": "Custom"}.get(backend, backend)


def _apply_model_commentary_placeholder(base: dict[str, Any], backend: str) -> dict[str, Any]:
    """在规则点评结构上套一层「模型骨架」文案，保持字段形状不变。"""
    tag = _tag_for_backend(backend)
    out = dict(base)
    prefix = f"【模型点评骨架·{tag}】"
    oc = str(out.get("overall_commentary") or "").strip()
    out["overall_commentary"] = (prefix + oc)[:900] if oc else f"{prefix}本轮综合点评占位：请接入真实模型后替换本段。"
    st = list(out.get("strengths") or [])
    if st:
        st = [f"〔{tag}〕{s}"[:420] for s in clean_string_list(st, 6)]
    else:
        st = [f"〔{tag}〕已完成本轮练习，具体优点将由模型在接入后细化。"]
    wk = list(out.get("weaknesses") or [])
    if wk:
        wk = [f"〔{tag}〕{s}"[:420] for s in clean_string_list(wk, 8)]
    else:
        wk = [f"〔{tag}〕薄弱点分析占位，接入模型后可结合多模态信号加强。"]
    adv = list(out.get("next_round_advice") or [])
    if adv:
        adv = [f"〔{tag}〕{s}"[:420] for s in clean_string_list(adv, 5)]
    else:
        adv = [f"〔{tag}〕下一轮请先固定机位与麦克风，再对照得分项逐项练习。"]
    out["strengths"] = st
    out["weaknesses"] = wk
    out["next_round_advice"] = adv
    out["coach_commentary"] = out["overall_commentary"]
    out["improvement_advice"] = list(adv)
    return out


def generate_model_commentary_bundle(**kw: Any) -> tuple[dict[str, Any], dict[str, Any]]:
    backend = get_commentary_model_backend()
    timeout = float(getattr(settings, "COMMENTARY_MODEL_TIMEOUT_SECONDS", 45) or 45)
    base = build_coach_output(**kw)
    overlaid = _apply_model_commentary_placeholder(base, backend)
    mode = f"commentary_model_{backend}_v1"
    bundle = attach_commentary_execution_meta(
        overlaid,
        configured_kind="model",
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
        "commentary_model_timeout_seconds": timeout,
    }
    return bundle, extra
