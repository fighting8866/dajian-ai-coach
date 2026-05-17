"""混合追问：优先真实/占位模型输出，不合格或异常时回退规则。"""

from __future__ import annotations

import traceback
from typing import Any

from factories.provider_factory import get_followup_model_backend
from services.followup_generation_utils import followup_items_valid
from services.model_followup_provider import generate_model_followups
from services.rule_followup_provider import generate_rule_followups


def generate_hybrid_followups(
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
) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    backend = get_followup_model_backend()
    model_ok = False
    m_items: list[dict[str, Any]] = []
    m_extra: dict[str, Any] = {}
    try:
        m_items, m_extra = generate_model_followups(
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
        model_ok = bool(m_items) and followup_items_valid(m_items)
    except Exception:
        print("[followup.hybrid] model path failed:\n" + traceback.format_exc(), flush=True)
        m_items = []
        model_ok = False

    fallback_to_rule = not model_ok
    print(f"[followup.hybrid] followup_model_backend={backend!r}", flush=True)
    print(f"[followup.hybrid] model_success={model_ok}", flush=True)
    print(f"[followup.hybrid] fallback_to_rule={fallback_to_rule}", flush=True)
    rj = m_extra.get("followup_model_reject_reason")
    if rj is not None:
        print(f"[followup.hybrid] model_reject_reason={rj!r}", flush=True)
    v2d = m_extra.get("followup_v2_debug")
    if v2d is not None:
        print(f"[followup.hybrid] followup_v2_debug={v2d!r}", flush=True)
    h_ms = m_extra.get("followup_model_http_ms")
    if h_ms is not None:
        print(f"[followup.hybrid] followup_model_http_ms={h_ms!r}", flush=True)
    print(
        f"[followup.hybrid] quality_gate={m_extra.get('quality_gate_passed')!r} "
        f"reason={m_extra.get('quality_gate_reason')!r} n_cand={m_extra.get('model_candidate_count')!r} "
        f"top_weak={m_extra.get('top_weak_point')!r} fallback={m_extra.get('fallback_reason')!r}",
        flush=True,
    )

    if model_ok:
        mode = f"followup_hybrid_model_{backend}_v2"
        extra: dict[str, Any] = {
            "generation_mode": mode,
            "fallback_to_rule": False,
            "effective_item_provider": "model",
            "followup_model_backend": backend,
            "followup_model_reject_reason": m_extra.get("followup_model_reject_reason"),
            "followup_v2_debug": m_extra.get("followup_v2_debug"),
            "followup_model_http_ms": m_extra.get("followup_model_http_ms"),
            "llm_elapsed_ms": m_extra.get("llm_elapsed_ms"),
            "quality_gate_passed": m_extra.get("quality_gate_passed"),
            "quality_gate_reason": m_extra.get("quality_gate_reason"),
            "top_weak_point": m_extra.get("top_weak_point"),
            "model_candidate_count": m_extra.get("model_candidate_count"),
            "fallback_reason": m_extra.get("fallback_reason"),
        }
        if m_extra.get("followup_model_timeout_seconds") is not None:
            extra["followup_model_timeout_seconds"] = m_extra["followup_model_timeout_seconds"]
        for it in m_items:
            it["generation_mode"] = mode
        return m_items, extra

    r_items, _r_extra = generate_rule_followups(
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
    mode = f"followup_hybrid_fallback_rule_{backend}_v2"
    fb = m_extra.get("fallback_reason") or m_extra.get("followup_model_reject_reason")
    extra = {
        "generation_mode": mode,
        "fallback_to_rule": True,
        "effective_item_provider": "rule",
        "followup_model_backend": backend,
        "followup_model_reject_reason": m_extra.get("followup_model_reject_reason"),
        "followup_v2_debug": m_extra.get("followup_v2_debug"),
        "followup_model_http_ms": m_extra.get("followup_model_http_ms"),
        "llm_elapsed_ms": m_extra.get("llm_elapsed_ms"),
        "quality_gate_passed": m_extra.get("quality_gate_passed"),
        "quality_gate_reason": m_extra.get("quality_gate_reason"),
        "top_weak_point": m_extra.get("top_weak_point"),
        "model_candidate_count": m_extra.get("model_candidate_count"),
        "fallback_reason": fb,
    }
    for it in r_items:
        it["generation_mode"] = mode
    return r_items, extra
