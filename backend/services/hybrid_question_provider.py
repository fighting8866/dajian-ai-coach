"""混合首问：优先模型占位，校验失败或异常则回退规则。"""

from __future__ import annotations

import traceback
from typing import Any

from factories.provider_factory import get_question_model_backend
from services.model_question_provider import generate_model_question_for_page, generate_model_questions_batch
from services.question_generation_utils import question_batch_valid, question_payload_valid
from services.rule_question_provider import generate_rule_question_for_page, generate_rule_questions_batch


def generate_hybrid_question_for_page(page_info: dict) -> tuple[dict[str, Any], dict[str, Any]]:
    backend = get_question_model_backend()
    try:
        m_payload, m_extra = generate_model_question_for_page(page_info)
        if question_payload_valid(m_payload):
            mode = f"question_hybrid_model_{backend}_v1"
            m_payload["generation_mode"] = mode
            extra: dict[str, Any] = {
                "generation_mode": mode,
                "fallback_to_rule": False,
                "effective_item_provider": "model",
                "question_model_backend": backend,
            }
            return m_payload, extra
    except Exception:
        print("[hybrid_question] model single-page path failed:\n" + traceback.format_exc(), flush=True)

    r_payload, _ = generate_rule_question_for_page(page_info)
    mode = f"question_hybrid_fallback_rule_{backend}_v1"
    r_payload["generation_mode"] = mode
    extra = {
        "generation_mode": mode,
        "fallback_to_rule": True,
        "effective_item_provider": "rule",
        "question_model_backend": backend,
    }
    return r_payload, extra


def generate_hybrid_questions_batch(
    *,
    document: dict | None,
    pages: list,
    count: int,
) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    backend = get_question_model_backend()
    try:
        items, m_extra = generate_model_questions_batch(document=document, pages=pages, count=count)
        if question_batch_valid(items):
            mode = f"question_hybrid_model_{backend}_batch_v1"
            for it in items:
                it["generation_mode"] = mode
            extra: dict[str, Any] = {
                "generation_mode": mode,
                "fallback_to_rule": False,
                "effective_item_provider": "model",
                "question_model_backend": backend,
            }
            if m_extra.get("question_model_timeout_seconds") is not None:
                extra["question_model_timeout_seconds"] = m_extra["question_model_timeout_seconds"]
            return items, extra
    except Exception:
        print("[hybrid_question] model batch path failed:\n" + traceback.format_exc(), flush=True)

    items, _ = generate_rule_questions_batch(document=document, pages=pages, count=count)
    mode = f"question_hybrid_fallback_rule_{backend}_batch_v1"
    for it in items:
        it["generation_mode"] = mode
    extra = {
        "generation_mode": mode,
        "fallback_to_rule": True,
        "effective_item_provider": "rule",
        "question_model_backend": backend,
    }
    return items, extra
