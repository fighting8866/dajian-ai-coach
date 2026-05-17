"""
模型首问（V1 骨架）：单页与批量均在规则结果上套占位前缀，不接真实大模型。

接入真实模型时：在本文件替换 `_apply_model_question_placeholder` / `_apply_batch_item_placeholder`。
"""

from __future__ import annotations

from typing import Any

from config import settings
from factories.provider_factory import get_question_model_backend
from services.question_generation_utils import enrich_question_payload, question_batch_valid
from services.rule_question_provider import generate_rule_question_for_page, generate_rule_questions_batch


def _tag(backend: str) -> str:
    return {"qwen": "Qwen", "mock": "Mock", "custom": "Custom"}.get(backend, backend)


def _apply_model_question_placeholder(payload: dict[str, Any], backend: str) -> dict[str, Any]:
    tag = _tag(backend)
    out = dict(payload)
    q = str(out.get("question") or "").strip()
    out["question"] = f"【模型首问骨架·{tag}】{q}"[:500] if q else f"【模型首问骨架·{tag}】请概述本页核心观点与依据。"
    out["source"] = f"model_skeleton_{backend}"
    return out


def _apply_batch_item_placeholder(item: dict[str, Any], backend: str, mode: str) -> dict[str, Any]:
    tag = _tag(backend)
    d = dict(item)
    q = str(d.get("question") or "").strip()
    d["question"] = f"【模型首问骨架·{tag}】{q}"[:500] if q else f"【模型首问骨架·{tag}】请结合材料回答。"
    d["source"] = f"model_skeleton_{backend}"
    d.setdefault("target_topic", str(d.get("target_topic") or ""))
    return enrich_question_payload(d, item_provider_kind="model", generation_mode=mode)


def generate_model_question_for_page(page_info: dict) -> tuple[dict[str, Any], dict[str, Any]]:
    backend = get_question_model_backend()
    timeout = float(getattr(settings, "QUESTION_MODEL_TIMEOUT_SECONDS", 30) or 30)
    base, _ = generate_rule_question_for_page(page_info)
    overlaid = _apply_model_question_placeholder(base, backend)
    mode = f"question_model_{backend}_v1"
    enriched = enrich_question_payload(overlaid, item_provider_kind="model", generation_mode=mode)
    extra: dict[str, Any] = {
        "generation_mode": mode,
        "fallback_to_rule": False,
        "effective_item_provider": "model",
        "question_model_backend": backend,
        "question_model_timeout_seconds": timeout,
    }
    return enriched, extra


def generate_model_questions_batch(
    *,
    document: dict | None,
    pages: list,
    count: int,
) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    backend = get_question_model_backend()
    timeout = float(getattr(settings, "QUESTION_MODEL_TIMEOUT_SECONDS", 30) or 30)
    raw_list, _ = generate_rule_questions_batch(document=document, pages=pages, count=count)
    mode = f"question_model_{backend}_batch_v1"
    enriched = [_apply_batch_item_placeholder(x, backend, mode) for x in raw_list]
    extra: dict[str, Any] = {
        "generation_mode": mode,
        "fallback_to_rule": False,
        "effective_item_provider": "model",
        "question_model_backend": backend,
        "question_model_timeout_seconds": timeout,
    }
    if not question_batch_valid(enriched):
        return [], {**extra, "generation_mode": f"{mode}_invalid", "effective_item_provider": "model"}
    return enriched, extra
