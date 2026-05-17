"""老师点评输出：清洗、校验、与 provider 元数据对齐（rule / model / hybrid 共用）。"""

from __future__ import annotations

from typing import Any

COMMENTARY_BUNDLE_VERSION = "v1"

_MAX_OVERALL = 900
_MAX_STRENGTHS = 6
_MAX_WEAKNESSES = 8
_MAX_ADVICE = 5
_MAX_LINE_LEN = 420


def _clean_str(s: str | None, max_len: int) -> str:
    t = (s or "").strip()
    if len(t) > max_len:
        return t[: max_len - 1].rstrip() + "…"
    return t


def clean_string_list(items: list[Any] | None, max_items: int, max_line_len: int = _MAX_LINE_LEN) -> list[str]:
    out: list[str] = []
    seen: set[str] = set()
    for raw in items or []:
        line = _clean_str(str(raw) if raw is not None else "", max_line_len)
        if not line:
            continue
        key = line[:48]
        if key in seen:
            continue
        seen.add(key)
        out.append(line)
        if len(out) >= max_items:
            break
    return out


def commentary_bundle_valid(bundle: dict[str, Any] | None) -> bool:
    if not isinstance(bundle, dict):
        return False
    oc = str(bundle.get("overall_commentary") or "").strip()
    if len(oc) < 24:
        return False
    st = bundle.get("strengths")
    wk = bundle.get("weaknesses")
    adv = bundle.get("next_round_advice")
    if not isinstance(st, list) or len(st) < 1:
        return False
    if not isinstance(wk, list) or len(wk) < 1:
        return False
    if not isinstance(adv, list) or len(adv) < 1:
        return False
    return True


def normalize_commentary_core_fields(bundle: dict[str, Any]) -> dict[str, Any]:
    """清洗 overall / 三个列表，并保持 coach_commentary、improvement_advice 与之一致。"""
    out = dict(bundle)
    oc = _clean_str(out.get("overall_commentary"), _MAX_OVERALL)
    st = clean_string_list(out.get("strengths"), _MAX_STRENGTHS)
    wk = clean_string_list(out.get("weaknesses"), _MAX_WEAKNESSES)
    adv = clean_string_list(out.get("next_round_advice"), _MAX_ADVICE)
    out["overall_commentary"] = oc
    out["strengths"] = st
    out["weaknesses"] = wk
    out["next_round_advice"] = adv
    out["coach_commentary"] = _clean_str(out.get("coach_commentary") or oc, _MAX_OVERALL) or oc
    out["improvement_advice"] = list(adv)
    return out


def attach_commentary_execution_meta(
    bundle: dict[str, Any],
    *,
    configured_kind: str,
    generation_mode: str,
    fallback_to_rule: bool,
    model_backend: str | None = None,
    effective_provider: str | None = None,
) -> dict[str, Any]:
    """写入顶层 commentary_generation_meta，并合并进 coach_metadata。"""
    from services.generation_common import build_generation_meta, normalize_generation_provider_kind

    ck = normalize_generation_provider_kind(configured_kind)
    base_meta = build_generation_meta("commentary", ck)
    exec_meta: dict[str, Any] = {
        **base_meta,
        "generation_mode": generation_mode,
        "version": COMMENTARY_BUNDLE_VERSION,
        "fallback_to_rule": bool(fallback_to_rule),
        "effective_provider": effective_provider or ("rule" if fallback_to_rule and ck == "hybrid" else ck),
    }
    if model_backend is not None:
        exec_meta["commentary_model_backend"] = model_backend

    out = normalize_commentary_core_fields(bundle)
    out["commentary_provider_kind"] = ck
    out["commentary_fallback_to_rule"] = bool(fallback_to_rule)
    out["commentary_generation_meta"] = exec_meta

    cm = dict(out.get("coach_metadata") or {})
    cm["commentary_generation_meta"] = exec_meta
    cm["commentary_fallback_to_rule"] = bool(fallback_to_rule)
    out["coach_metadata"] = cm
    return out
