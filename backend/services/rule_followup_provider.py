"""规则追问 provider：复用 build_followup_questions_v2。"""

from __future__ import annotations

from typing import Any

from services.coach_service import build_followup_questions_v2
from services.followup_generation_utils import enrich_followup_item_list


def generate_rule_followups(
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
    raw = build_followup_questions_v2(
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
    mode = "followup_rule_v2"
    items = enrich_followup_item_list(raw, provider_kind="rule", generation_mode=mode)
    extra: dict[str, Any] = {
        "generation_mode": mode,
        "fallback_to_rule": False,
        "effective_item_provider": "rule",
    }
    return items, extra
