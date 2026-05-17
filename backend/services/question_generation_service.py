"""
老师首问生成服务 V1：按 QUESTION_PROVIDER 分发 rule / model / hybrid。
"""

from __future__ import annotations

from typing import Any

from factories.provider_factory import get_question_generation_provider_kind
from services.generation_common import normalize_generation_provider_kind
from services.hybrid_question_provider import (
    generate_hybrid_question_for_page,
    generate_hybrid_questions_batch,
)
from services.model_question_provider import (
    generate_model_question_for_page,
    generate_model_questions_batch,
)
from services.question_generation_utils import build_question_top_level_meta
from services.rule_question_provider import (
    generate_rule_question_for_page,
    generate_rule_questions_batch,
)


def generate_question_for_page(page_info: dict) -> dict[str, Any]:
    configured = normalize_generation_provider_kind(get_question_generation_provider_kind())
    if configured == "model":
        payload, extra = generate_model_question_for_page(page_info)
    elif configured == "hybrid":
        payload, extra = generate_hybrid_question_for_page(page_info)
    else:
        payload, extra = generate_rule_question_for_page(page_info)

    meta = build_question_top_level_meta(
        configured_kind=configured,
        generation_mode=str(extra.get("generation_mode") or ""),
        fallback_to_rule=bool(extra.get("fallback_to_rule")),
        model_backend=extra.get("question_model_backend"),
        timeout_seconds=extra.get("question_model_timeout_seconds"),
    )
    return {
        **payload,
        "question_provider_kind": configured,
        "question_generation_meta": meta,
        "question_fallback_to_rule": bool(extra.get("fallback_to_rule")),
    }


def generate_questions_batch(
    *,
    document: dict | None,
    pages: list,
    count: int,
) -> dict[str, Any]:
    configured = normalize_generation_provider_kind(get_question_generation_provider_kind())
    items: list[dict[str, Any]] = []
    extra: dict[str, Any] = {}

    if configured == "model":
        items, extra = generate_model_questions_batch(document=document, pages=pages, count=count)
        if not items:
            items, r_extra = generate_rule_questions_batch(document=document, pages=pages, count=count)
            extra = {
                **r_extra,
                "fallback_to_rule": True,
                "generation_mode": f"{r_extra.get('generation_mode', 'question_rule_batch_v1')}_model_batch_invalid_fallback",
                "question_model_backend": extra.get("question_model_backend"),
            }
    elif configured == "hybrid":
        items, extra = generate_hybrid_questions_batch(document=document, pages=pages, count=count)
    else:
        items, extra = generate_rule_questions_batch(document=document, pages=pages, count=count)

    meta = build_question_top_level_meta(
        configured_kind=configured,
        generation_mode=str(extra.get("generation_mode") or ""),
        fallback_to_rule=bool(extra.get("fallback_to_rule")),
        model_backend=extra.get("question_model_backend"),
        timeout_seconds=extra.get("question_model_timeout_seconds"),
    )
    return {
        "questions": items,
        "question_provider_kind": configured,
        "question_generation_meta": meta,
        "question_fallback_to_rule": bool(extra.get("fallback_to_rule")),
    }
