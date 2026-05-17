"""规则首问：复用 QAProvider.generate_question（单页）与 generate_mock_questions（批量）。"""

from __future__ import annotations

from typing import Any

from factories.provider_factory import get_qa_provider
from services.qa_service import generate_mock_questions
from services.question_generation_utils import enrich_question_payload


def generate_rule_question_for_page(page_info: dict) -> tuple[dict[str, Any], dict[str, Any]]:
    inner = get_qa_provider().generate_question(page_info)
    if not isinstance(inner, dict):
        inner = {"question": str(inner)}
    inner.setdefault("source", "page_rule")
    title = str((page_info or {}).get("title") or "").strip()
    inner.setdefault("target_topic", title[:120])
    mode = "question_rule_v1"
    enriched = enrich_question_payload(inner, item_provider_kind="rule", generation_mode=mode)
    extra: dict[str, Any] = {
        "generation_mode": mode,
        "fallback_to_rule": False,
        "effective_item_provider": "rule",
        "question_model_backend": None,
    }
    return enriched, extra


def generate_rule_questions_batch(
    *,
    document: dict | None,
    pages: list,
    count: int,
) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    raw = generate_mock_questions(document=document, pages=pages, count=count)
    mode = "question_rule_batch_v1"
    enriched_list: list[dict[str, Any]] = []
    for it in raw:
        if not isinstance(it, dict):
            continue
        d = dict(it)
        d.setdefault("target_topic", "")
        enriched_list.append(
            enrich_question_payload(d, item_provider_kind="rule", generation_mode=mode)
        )
    extra: dict[str, Any] = {
        "generation_mode": mode,
        "fallback_to_rule": False,
        "effective_item_provider": "rule",
        "question_model_backend": None,
    }
    return enriched_list, extra
