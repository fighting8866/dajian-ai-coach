"""
老师追问生成：按 FOLLOWUP_PROVIDER 分发 rule | model | hybrid。
"""

from __future__ import annotations

from typing import Any

from factories.provider_factory import get_followup_generation_provider_kind, get_followup_model_backend
from services.generation_common import build_generation_meta, normalize_generation_provider_kind
from services.hybrid_followup_provider import generate_hybrid_followups
from services.model_followup_provider import generate_model_followups
from services.rule_followup_provider import generate_rule_followups


def empty_followup_payload() -> dict[str, Any]:
    configured = normalize_generation_provider_kind(get_followup_generation_provider_kind())
    meta = build_generation_meta("followup", configured)
    meta["fallback_to_rule"] = False
    meta["effective_item_provider"] = None
    meta["followup_model_backend"] = get_followup_model_backend() if configured != "rule" else None
    return {
        "followup_questions": [],
        "followup_provider_kind": configured,
        "followup_generation_meta": meta,
        "followup_fallback_to_rule": False,
    }


def generate_followup_questions_payload(
    *,
    qa_breakdown: dict | None,
    qa_result: dict | None,
    current_question: str = "",
    current_answer: str = "",
    content_breakdown: dict | None = None,
    content_document: dict | None = None,
    ppt_match: dict | None = None,
    ppt_match_analysis: dict | None = None,
    max_items: int = 3,
) -> dict[str, Any]:
    configured = normalize_generation_provider_kind(get_followup_generation_provider_kind())

    if configured == "rule":
        items, extra = generate_rule_followups(
            qa_breakdown=qa_breakdown,
            qa_result=qa_result,
            current_question=current_question,
            current_answer=current_answer,
            content_breakdown=content_breakdown,
            content_document=content_document,
            ppt_match=ppt_match,
            ppt_match_analysis=ppt_match_analysis,
            max_items=max_items,
        )
    elif configured == "model":
        items, extra = generate_model_followups(
            qa_breakdown=qa_breakdown,
            qa_result=qa_result,
            current_question=current_question,
            current_answer=current_answer,
            content_breakdown=content_breakdown,
            content_document=content_document,
            ppt_match=ppt_match,
            ppt_match_analysis=ppt_match_analysis,
            max_items=max_items,
        )
    else:
        items, extra = generate_hybrid_followups(
            qa_breakdown=qa_breakdown,
            qa_result=qa_result,
            current_question=current_question,
            current_answer=current_answer,
            content_breakdown=content_breakdown,
            content_document=content_document,
            ppt_match=ppt_match,
            ppt_match_analysis=ppt_match_analysis,
            max_items=max_items,
        )

    meta = build_generation_meta("followup", configured)
    meta["generation_mode"] = extra.get("generation_mode") or meta.get("generation_mode")
    meta["fallback_to_rule"] = bool(extra.get("fallback_to_rule"))
    meta["effective_item_provider"] = extra.get("effective_item_provider")
    if extra.get("followup_model_backend") is not None:
        meta["followup_model_backend"] = extra.get("followup_model_backend")
    if extra.get("followup_model_timeout_seconds") is not None:
        meta["followup_model_timeout_seconds"] = extra.get("followup_model_timeout_seconds")
    for k in (
        "followup_v2_debug",
        "followup_model_reject_reason",
        "followup_model_http_ms",
        "followup_model_total_ms",
        "llm_elapsed_ms",
        "quality_gate_passed",
        "quality_gate_reason",
        "top_weak_point",
        "model_candidate_count",
        "fallback_reason",
    ):
        if k in extra:
            meta[k] = extra[k]

    return {
        "followup_questions": items,
        "followup_provider_kind": configured,
        "followup_generation_meta": meta,
        "followup_fallback_to_rule": bool(extra.get("fallback_to_rule")),
    }
