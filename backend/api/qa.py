import os
import re
from typing import Any

from config import settings
from factories.provider_factory import get_followup_model_backend
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, ConfigDict, Field

from services.mock_store import ppt_store
from services.question_generation_service import generate_question_for_page, generate_questions_batch
from services.followup_generation_service import empty_followup_payload, generate_followup_questions_payload

router = APIRouter()


def _normalize_question_for_log(q: str | None) -> str:
    t = re.sub(r"\s+", "", (q or "").strip())
    return t[:100]


def _apply_followup_api_provider_labels(payload: dict[str, Any]) -> None:
    """
    统一 /qa/followup 响应中的 followup_generation_meta.provider_label，与 followup_provider_kind 一致。
    （generation_common 骨架仍带「预留」字样；API 出口在此收口，避免 model/hybrid 已接入时仍显示占位文案。）
    """
    meta = payload.get("followup_generation_meta")
    if not isinstance(meta, dict):
        return
    kind = str(payload.get("followup_provider_kind") or "").strip().lower()
    fb = bool(payload.get("followup_fallback_to_rule"))
    if kind == "hybrid":
        meta["provider_label"] = "混合追问（已回退规则）" if fb else "混合追问"
    elif kind == "model":
        meta["provider_label"] = "模型追问"
    elif kind == "rule":
        meta["provider_label"] = "规则追问"


class QAGenerateRequest(BaseModel):
    """POST /qa/generate 仅接受 JSON body：批量不传 page_index，单页必传 page_index。"""

    model_config = ConfigDict(extra="ignore")

    ppt_id: str
    page_index: int | None = None
    count: int | None = Field(default=None, ge=1, le=12)


@router.post("/qa/generate")
async def generate_question(body: QAGenerateRequest):
    keys_sorted = sorted(body.model_dump(exclude_unset=True).keys())
    pid = (body.ppt_id or "").strip()
    if not pid:
        raise HTTPException(
            status_code=400,
            detail="缺少 ppt_id，请先上传并解析 PPT",
        )

    ppt_info = ppt_store.get(pid)
    pages_raw = ppt_info.get("pages") if ppt_info else None
    page_list = pages_raw if isinstance(pages_raw, list) else []
    has_doc = bool(ppt_info and ppt_info.get("document") is not None)
    print(
        "[qa.generate] requested ppt_id=",
        repr(pid),
        f"ppt_store_hit={ppt_info is not None}",
        f"has_document={has_doc}",
        f"has_pages={len(page_list) > 0}",
        flush=True,
    )
    if not ppt_info:
        raise HTTPException(
            status_code=404,
            detail="PPT 不存在或尚未解析，请重新上传",
        )
    if len(page_list) == 0 and not has_doc:
        raise HTTPException(
            status_code=400,
            detail="PPT 已上传，但解析结果不完整，请重新解析后重试",
        )

    if body.page_index is not None:
        print(
            "[qa.generate] mode=single_page",
            f"body_keys={keys_sorted}",
            f"ppt_id={pid!r}",
            f"page_index={body.page_index}",
            f"count={body.count}",
            flush=True,
        )
        target_page = None
        for page in page_list:
            if page.get("page_index") == body.page_index:
                target_page = page
                break

        if not target_page:
            raise HTTPException(status_code=404, detail="页面不存在")

        result = generate_question_for_page(target_page)
        _qm = result.get("question_generation_meta") or {}
        print(f"[qa.generate] provider_kind={result.get('question_provider_kind')!r}", flush=True)
        print(f"[qa.generate] generation_mode={_qm.get('generation_mode')!r}", flush=True)
        print(f"[qa.generate] fallback_to_rule={bool(result.get('question_fallback_to_rule'))}", flush=True)
        print(
            "[qa.generate] first question=",
            repr(str(result.get("question") or "")[:200]),
            flush=True,
        )
        return result

    count = 3 if body.count is None else body.count
    print(
        "[qa.generate] mode=batch",
        f"body_keys={keys_sorted}",
        f"ppt_id={pid!r}",
        f"page_index=None",
        f"count={count}",
        flush=True,
    )
    batch = generate_questions_batch(
        document=ppt_info.get("document"),
        pages=page_list,
        count=count,
    )
    questions = batch.get("questions") or []
    print("[qa.generate] batch questions count=", len(questions), flush=True)
    _bm = batch.get("question_generation_meta") or {}
    print(f"[qa.generate] provider_kind={batch.get('question_provider_kind')!r}", flush=True)
    print(f"[qa.generate] generation_mode={_bm.get('generation_mode')!r}", flush=True)
    print(f"[qa.generate] fallback_to_rule={bool(batch.get('question_fallback_to_rule'))}", flush=True)
    first_q = None
    if questions:
        q0 = questions[0]
        if isinstance(q0, dict):
            first_q = q0.get("question") or q0.get("text") or q0.get("q")
        else:
            first_q = str(q0)
    print(
        "[qa.generate] first question=",
        repr(str(first_q)[:200]) if first_q else None,
        flush=True,
    )
    return {
        "questions": questions,
        "question_provider_kind": batch.get("question_provider_kind"),
        "question_generation_meta": batch.get("question_generation_meta"),
        "question_fallback_to_rule": batch.get("question_fallback_to_rule"),
    }


@router.post("/qa/evaluate")
async def evaluate_answer(request: dict):
    from factories.provider_factory import get_qa_provider

    question = request.get("question", "")
    expected_keywords = request.get("expected_keywords", [])
    answer_text = request.get("answer_text", "")

    if not question:
        raise HTTPException(status_code=400, detail="缺少问题内容")

    return get_qa_provider().evaluate_answer(question, expected_keywords, answer_text)


class QAFollowupRequest(BaseModel):
    """POST /qa/followup：基于上一轮问答弱点与内容信号生成追问（rule | model | hybrid，由 FOLLOWUP_PROVIDER 决定）。"""

    model_config = ConfigDict(extra="ignore")

    ppt_id: str = ""
    current_question: str = ""
    current_answer: str = ""
    qa_result: dict | None = None
    qa_breakdown: dict | None = None
    ppt_match: dict | None = None
    content_breakdown: dict | None = None
    ppt_match_analysis: dict | None = None
    max_items: int | None = Field(default=3, ge=1, le=3)
    client_followup_trigger: str | None = Field(
        default=None,
        description="可选：前端口径，如 auto_after_first_eval（仅日志，不参与生成逻辑）。",
    )


@router.post("/qa/followup")
async def qa_followup(body: QAFollowupRequest):
    print("[qa.followup] route hit", flush=True)
    print(
        "[qa.followup] env "
        f"FOLLOWUP_PROVIDER={os.getenv('FOLLOWUP_PROVIDER')!r} "
        f"FOLLOWUP_MODEL_BACKEND={os.getenv('FOLLOWUP_MODEL_BACKEND')!r}",
        flush=True,
    )
    print(
        "[qa.followup] resolved "
        f"FOLLOWUP_PROVIDER={settings.FOLLOWUP_PROVIDER!r} "
        f"FOLLOWUP_MODEL_BACKEND={settings.FOLLOWUP_MODEL_BACKEND!r}",
        flush=True,
    )
    _eff_be = get_followup_model_backend()
    _base_cfg = (getattr(settings, "FOLLOWUP_MODEL_BASE_URL", None) or "").strip()
    print(
        "[qa.followup] followup_probe "
        f"effective_followup_model_backend={_eff_be!r} "
        f"base_url_configured={bool(_base_cfg)} "
        f"base_url_preview={_base_cfg[:72]!r}",
        flush=True,
    )
    keys_sorted = sorted(body.model_dump(exclude_unset=True).keys())
    pid = (body.ppt_id or "").strip()
    cq = (body.current_question or "").strip()
    ppt_info = ppt_store.get(pid) if pid else None
    content_document = ppt_info.get("document") if isinstance(ppt_info, dict) else None

    qa_res = body.qa_result if isinstance(body.qa_result, dict) else None
    has_qa = bool(qa_res)
    print(
        "[qa.followup] body_keys=",
        keys_sorted,
        "ppt_id=",
        repr(pid),
        "current_question_preview=",
        repr(cq[:120]) if cq else "",
        "has_qa_result=",
        has_qa,
        flush=True,
    )
    if not qa_res:
        print("[qa.followup] followup count=0 (no qa_result, return empty)", flush=True)
        empty_p = empty_followup_payload()
        _apply_followup_api_provider_labels(empty_p)
        _em = empty_p.get("followup_generation_meta") or {}
        print(f"[qa.followup] provider_kind={empty_p.get('followup_provider_kind')!r}", flush=True)
        print(f"[qa.followup] provider_label={_em.get('provider_label')!r}", flush=True)
        print(f"[qa.followup] generation_mode={_em.get('generation_mode')!r}", flush=True)
        print(f"[qa.followup] fallback_to_rule={bool(empty_p.get('followup_fallback_to_rule'))}", flush=True)
        return empty_p

    _trig = (body.client_followup_trigger or "").strip()
    if _trig == "auto_after_first_eval":
        print("[qa.followup] auto-trigger request", flush=True)

    payload = generate_followup_questions_payload(
        qa_breakdown=body.qa_breakdown if isinstance(body.qa_breakdown, dict) else None,
        qa_result=qa_res,
        current_question=body.current_question or "",
        current_answer=body.current_answer or "",
        content_breakdown=body.content_breakdown if isinstance(body.content_breakdown, dict) else None,
        content_document=content_document,
        ppt_match=body.ppt_match if isinstance(body.ppt_match, dict) else None,
        ppt_match_analysis=body.ppt_match_analysis if isinstance(body.ppt_match_analysis, dict) else None,
        max_items=3 if body.max_items is None else body.max_items,
    )
    _apply_followup_api_provider_labels(payload)
    _fmeta = payload.get("followup_generation_meta") or {}
    print(f"[qa.followup] provider_kind={payload.get('followup_provider_kind')!r}", flush=True)
    print(f"[qa.followup] provider_label={_fmeta.get('provider_label')!r}", flush=True)
    print(f"[qa.followup] generation_mode={_fmeta.get('generation_mode')!r}", flush=True)
    print(f"[qa.followup] fallback_to_rule={bool(payload.get('followup_fallback_to_rule'))}", flush=True)
    _fmb = _fmeta.get("followup_model_backend")
    print(f"[qa.followup] followup_model_backend={_fmb!r}", flush=True)
    _pk = (payload.get("followup_provider_kind") or "").strip().lower()
    _gm_final = str(_fmeta.get("generation_mode") or "")
    _invalid_model = "_invalid_" in _gm_final
    print(
        "[qa.followup] followup_result_probe "
        f"generation_mode={_gm_final!r} "
        f"fallback_to_rule={bool(payload.get('followup_fallback_to_rule'))} "
        f"item_count={len(payload.get('followup_questions') or [])} "
        f"model_validation_failed_hint={_invalid_model}",
        flush=True,
    )
    if _pk == "rule":
        print("[qa.followup] model_invoke_path=n/a (rule provider)", flush=True)
    elif _fmb == "mock":
        print("[qa.followup] model_invoke_path=mock_local_placeholder", flush=True)
    elif _fmb in ("qwen", "custom", "openai", "http_post"):
        print("[qa.followup] model_invoke_path=http_openai_compat_chat_completions", flush=True)
    else:
        print(f"[qa.followup] model_invoke_path=unknown backend={_fmb!r}", flush=True)
    items = payload.get("followup_questions") or []
    print(f"[qa.followup] followup count={len(items)}", flush=True)
    if items:
        print(
            "[qa.followup] first followup=",
            repr(str(items[0].get("question") or "")[:240]),
            flush=True,
        )
    print(
        "[qa.followup] generated questions=",
        [it.get("question") for it in items],
        flush=True,
    )
    print(
        "[qa.followup] normalized questions=",
        [_normalize_question_for_log(it.get("question")) for it in items],
        flush=True,
    )
    print("[qa.followup] sources=", [it.get("source") for it in items], flush=True)
    return payload
