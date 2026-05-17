"""老师首问输出：清洗、校验、字段对齐（rule / model / hybrid 共用）。"""

from __future__ import annotations

from typing import Any

QUESTION_ITEM_VERSION = "v1"

_ITEM_LABELS = {
    "rule": "规则首问",
    "model": "模型首问",
    "hybrid": "混合首问",
}


def clean_question_text(q: str | None, max_len: int = 500) -> str:
    t = (q or "").strip().replace("\n", " ")
    if len(t) > max_len:
        return t[: max_len - 1].rstrip() + "…"
    return t


def question_payload_valid(d: dict[str, Any] | None) -> bool:
    if not isinstance(d, dict):
        return False
    return len(clean_question_text(d.get("question"))) >= 6


def question_batch_valid(items: list[Any]) -> bool:
    if not items:
        return False
    for it in items:
        if isinstance(it, dict):
            if not question_payload_valid(it):
                return False
        else:
            if len(clean_question_text(str(it))) < 6:
                return False
    return True


def enrich_question_payload(
    payload: dict[str, Any],
    *,
    item_provider_kind: str,
    generation_mode: str,
    version: str = QUESTION_ITEM_VERSION,
) -> dict[str, Any]:
    """单页 / 单条首问：补齐 source、target_topic、provider_*（与 expected_keywords 等并存）。"""
    pk = (item_provider_kind or "rule").strip().lower()
    if pk not in ("rule", "model", "hybrid"):
        pk = "rule"
    out = dict(payload)
    out["question"] = clean_question_text(out.get("question"))
    out.setdefault("source", str(out.get("source") or "page_rule"))
    out.setdefault("target_topic", str(out.get("target_topic") or "").strip()[:120])
    out["provider_kind"] = pk
    out["provider_label"] = _ITEM_LABELS.get(pk, pk)
    out["generation_mode"] = generation_mode
    out["version"] = version
    return out


def build_question_top_level_meta(
    *,
    configured_kind: str,
    generation_mode: str,
    fallback_to_rule: bool,
    model_backend: str | None = None,
    timeout_seconds: float | None = None,
) -> dict[str, Any]:
    from services.generation_common import build_generation_meta, normalize_generation_provider_kind

    ck = normalize_generation_provider_kind(configured_kind)
    base = build_generation_meta("question", ck)
    meta: dict[str, Any] = {
        **base,
        "provider_label": _ITEM_LABELS.get(ck, base.get("provider_label", ck)),
        "generation_mode": generation_mode,
        "version": QUESTION_ITEM_VERSION,
        "fallback_to_rule": bool(fallback_to_rule),
    }
    if model_backend is not None:
        meta["question_model_backend"] = model_backend
    if timeout_seconds is not None:
        meta["question_model_timeout_seconds"] = timeout_seconds
    return meta


def wrap_batch_response(
    questions: list[dict[str, Any]],
    *,
    configured_kind: str,
    generation_mode: str,
    fallback_to_rule: bool,
    model_backend: str | None = None,
    timeout_seconds: float | None = None,
) -> dict[str, Any]:
    meta = build_question_top_level_meta(
        configured_kind=configured_kind,
        generation_mode=generation_mode,
        fallback_to_rule=fallback_to_rule,
        model_backend=model_backend,
        timeout_seconds=timeout_seconds,
    )
    return {
        "questions": questions,
        "question_provider_kind": configured_kind,
        "question_generation_meta": meta,
        "question_fallback_to_rule": bool(fallback_to_rule),
    }
