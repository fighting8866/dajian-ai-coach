"""
模型追问 provider（V2 追问增强：更强 prompt、few-shot、V2 质量门禁与调试字段）

- mock：无 HTTP，可读占位追问（默认主流程安全）。
- qwen | custom：`POST {BASE}/v1/chat/completions`，OpenAI Chat Completions 兼容（urllib，无额外依赖）。
  响应按 `choices[0].message.content` 解析；必要时回退整包 JSON 中的数组字段。

未知/未配置 BASE_URL 时不发起外呼，返回空列表供 hybrid 回退 rule。
V2 门禁不通过时同样返回空列表，供 hybrid 回退 rule。
"""

from __future__ import annotations

import json
import re
import time
import traceback
import urllib.error
import urllib.request
from typing import Any

from config import settings
from factories.provider_factory import get_followup_model_backend
from services.followup_generation_utils import (
    enrich_followup_item_list,
    followup_items_valid,
    prepare_model_followup_raw_items,
)
from services.followup_v2_gates import (
    assess_followup_v2_quality,
    build_weak_point_anchors,
    per_item_weak_hits,
    top_weak_point_for_telemetry,
)
from services.prompts.followup_prompt_v2 import FOLLOWUP_V2_SYSTEM_PROMPT


def _clip(s: str, n: int) -> str:
    t = (s or "").strip().replace("\n", " ")
    return t[: n - 1] + "…" if len(t) > n else t


# 控制 prompt 体积与补全长度，见 services.prompts.followup_prompt_v2
_CLIP_Q = 500
_CLIP_A = 1200
_MAX_COMPLETION_TOKENS = 896
# 略提高随机性，减少「模板腔」
_CHAT_TEMPERATURE = 0.42
_FOLLOWUP_MODE_VER = "v2"


def _v2_enrich_debug(
    enriched: list[dict[str, Any]],
    *,
    qa_result: dict | None,
    current_question: str,
    current_answer: str,
    http_ms: float | None = None,
) -> tuple[bool, str, dict[str, Any]]:
    w_anch = build_weak_point_anchors(qa_result=qa_result)
    v2_ok, v2_code, v2_debug = assess_followup_v2_quality(
        enriched,
        weak_only_anchors=w_anch,
        current_question=current_question,
        current_answer=current_answer,
    )
    v2_debug = dict(v2_debug)
    v2_debug["per_question_weak_hits"] = per_item_weak_hits(enriched, w_anch)
    v2_debug["v2_reject_code"] = v2_code
    v2_debug["weak_anchor_count"] = len(w_anch)
    v2_debug["top_weak_point"] = top_weak_point_for_telemetry(qa_result=qa_result)
    v2_debug["quality_gate_passed"] = v2_ok
    v2_debug["quality_gate_reason"] = v2_code
    if http_ms is not None:
        v2_debug["llm_elapsed_ms"] = round(float(http_ms), 2)
    return v2_ok, v2_code, v2_debug


def _emit_model_state_telemetry(
    state: dict[str, Any],
    *,
    qa_result: dict | None,
    model_candidate_count: int,
    quality_gate_passed: bool,
    quality_gate_reason: str,
) -> None:
    ms = state.get("followup_model_http_ms")
    state["llm_elapsed_ms"] = round(float(ms), 2) if ms is not None else None
    state["model_candidate_count"] = int(model_candidate_count)
    state["top_weak_point"] = top_weak_point_for_telemetry(qa_result=qa_result)
    state["quality_gate_passed"] = quality_gate_passed
    state["quality_gate_reason"] = quality_gate_reason
    state["fallback_reason"] = state.get("followup_model_reject_reason")


def _chat_completions_url(base: str) -> str:
    b = (base or "").strip().rstrip("/")
    if not b:
        return ""
    if b.endswith("/chat/completions"):
        return b
    if b.endswith("/v1"):
        return f"{b}/chat/completions"
    return f"{b}/v1/chat/completions"


def _resolve_model_name(*, backend: str) -> str:
    """OpenAI 兼容请求体中的 model；未配置名称时按 backend 给常用默认。"""
    n = (getattr(settings, "FOLLOWUP_MODEL_NAME", None) or "").strip()
    if n:
        return n

    b = (backend or "custom").strip().lower()
    if b == "qwen":
        return "qwen-turbo"
    if b == "remote_ollama":
        return "qwen3.5:4b"

    return "gpt-3.5-turbo"

def _compact_llm_context(
    *,
    qa_breakdown: dict | None,
    qa_result: dict | None,
    current_question: str,
    current_answer: str,
    content_breakdown: dict | None,
    ppt_match: dict | None,
    max_items: int,
) -> dict[str, Any]:
    ctx: dict[str, Any] = {
        "current_question": _clip(current_question, _CLIP_Q),
        "current_answer": _clip(current_answer, _CLIP_A),
        "max_items": max(1, min(int(max_items or 3), 3)),
        "weak_points": [],
        "missing_keywords": [],
        "followup_candidate_topics": [],
    }
    if isinstance(qa_result, dict):
        wp = qa_result.get("weak_points")
        if isinstance(wp, list):
            ctx["weak_points"] = [str(x).strip()[:200] for x in wp if str(x).strip()]
        mk = qa_result.get("missing_keywords")
        if isinstance(mk, list):
            ctx["missing_keywords"] = [str(x).strip()[:80] for x in mk if str(x).strip()]
        ft = qa_result.get("followup_candidate_topics")
        if isinstance(ft, list):
            ctx["followup_candidate_topics"] = [str(x).strip()[:200] for x in ft if str(x).strip()]
        for k in ("is_relevant", "coverage_score", "comment", "missing_keywords"):
            if qa_result.get(k) is not None:
                ctx.setdefault("qa_result_summary", {})[k] = qa_result.get(k)
    if isinstance(qa_breakdown, dict):
        slim = {
            k: qa_breakdown.get(k)
            for k in (
                "is_relevant",
                "coverage_score",
                "hit_keyword_count",
                "missing_keyword_count",
                "clarity_score",
                "answer_information_level",
            )
            if qa_breakdown.get(k) is not None
        }
        if slim:
            ctx["qa_breakdown"] = slim
    if isinstance(content_breakdown, dict):
        slim_c = {
            k: content_breakdown.get(k)
            for k in ("match_score", "keyword_coverage", "title_hit", "outline_hit", "final_content_score")
            if content_breakdown.get(k) is not None
        }
        if slim_c:
            ctx["content_breakdown"] = slim_c
    if isinstance(ppt_match, dict):
        ctx["ppt_match"] = {
            "page_index": ppt_match.get("page_index"),
            "title": _clip(str(ppt_match.get("title") or ""), 120),
            "match_score": ppt_match.get("match_score"),
        }
        mkp = ppt_match.get("missing_keywords")
        if isinstance(mkp, list) and mkp:
            ctx.setdefault("ppt_missing_keywords", [str(x).strip()[:60] for x in mkp if str(x).strip()][:12])
    ca = (current_answer or "").strip()
    if len(ca) > 240:
        ctx["answer_tail_snippet"] = _clip(ca[-240:], 240)
    cq = (current_question or "").strip()
    if cq:
        ctx["question_head_snippet"] = _clip(cq[:220], 220)
    if isinstance(qa_result, dict) and (qa_result.get("comment") or "").strip():
        ctx["qa_comment_brief"] = _clip(str(qa_result.get("comment") or ""), 280)
    wpl = ctx.get("weak_points") or []
    mkl = ctx.get("missing_keywords") or []
    fpl = ctx.get("followup_candidate_topics") or []
    if wpl or mkl or fpl:
        ctx["primary_weak_focus"] = {
            "first_weak": (wpl[0][:100] if wpl else None),
            "first_missing": (mkl[0][:80] if mkl else None),
            "first_topic": (fpl[0][:100] if fpl else None),
        }
    return ctx


def _extract_json_array(text: str) -> list[Any] | None:
    t = (text or "").strip()
    m = re.search(r"```(?:json)?\s*([\s\S]*?)\s*```", t, re.IGNORECASE)
    if m:
        t = m.group(1).strip()
    start = t.find("[")
    if start < 0:
        return None
    depth = 0
    for i in range(start, len(t)):
        if t[i] == "[":
            depth += 1
        elif t[i] == "]":
            depth -= 1
            if depth == 0:
                chunk = t[start : i + 1]
                try:
                    parsed = json.loads(chunk)
                    return parsed if isinstance(parsed, list) else None
                except json.JSONDecodeError:
                    return None
    return None


def _post_chat_completions(
    *,
    url: str,
    api_key: str,
    model: str,
    messages: list[dict[str, str]],
    timeout: float,
) -> tuple[int, str]:
    payload: dict[str, Any] = {
        "model": model,
        "messages": messages,
        "temperature": _CHAT_TEMPERATURE,
        "max_tokens": _MAX_COMPLETION_TOKENS,
    }
    body = json.dumps(payload, ensure_ascii=False).encode("utf-8")
    req = urllib.request.Request(url, data=body, method="POST")
    req.add_header("Content-Type", "application/json; charset=utf-8")
    ak = (api_key or "").strip()
    if ak:
        req.add_header("Authorization", f"Bearer {ak}")
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            return int(resp.status), resp.read().decode("utf-8", errors="replace")
    except urllib.error.HTTPError as e:
        raw = e.read().decode("utf-8", errors="replace") if e.fp else ""
        return int(e.code), raw
    except Exception:
        raise


def _openai_content_from_body(body: str) -> str:
    try:
        data = json.loads(body)
    except json.JSONDecodeError:
        return ""
    ch = data.get("choices")
    if not isinstance(ch, list) or not ch:
        return ""
    msg = ch[0].get("message") if isinstance(ch[0], dict) else None
    if isinstance(msg, dict):
        return str(msg.get("content") or "")
    return ""


def _parse_followup_http_body(body: str) -> list[Any] | None:
    """自定义 HTTP：解析 JSON 数组或常见包装结构；失败返回 None。"""
    raw = (body or "").strip()
    if not raw:
        return None
    try:
        data = json.loads(raw)
    except json.JSONDecodeError:
        parsed = _extract_json_array(raw)
        return parsed if isinstance(parsed, list) else None
    if isinstance(data, list):
        return data
    if isinstance(data, dict):
        for key in ("items", "followup_questions", "followups", "data", "result"):
            v = data.get(key)
            if isinstance(v, list):
                return v
        content = _openai_content_from_body(raw)
        if (content or "").strip():
            parsed = _extract_json_array(content)
            if isinstance(parsed, list):
                return parsed
        for key in ("output", "text", "content", "message"):
            s = data.get(key)
            if isinstance(s, str) and s.strip():
                parsed = _extract_json_array(s)
                if isinstance(parsed, list):
                    return parsed
    return None


def _generate_placeholder_items(
    *,
    backend: str,
    qa_result: dict | None,
    current_question: str,
    current_answer: str,
    max_items: int,
) -> list[dict[str, Any]]:
    """mock 后端：可朗读的占位追问（非 LLM）。"""
    cq = _clip(current_question, 80)
    weak: list[str] = []
    if isinstance(qa_result, dict):
        for w in qa_result.get("weak_points") or []:
            if isinstance(w, str) and w.strip():
                weak.append(w.strip()[:120])
        for t in qa_result.get("followup_candidate_topics") or []:
            if isinstance(t, str) and t.strip() and t not in weak:
                weak.append(t.strip()[:120])
    nmax = max(1, min(int(max_items or 3), 3))
    items: list[dict[str, Any]] = []
    tag = {"qwen": "Qwen", "custom": "Custom", "mock": "Mock"}.get(backend, backend)
    if weak:
        for w in weak[:nmax]:
            items.append(
                {
                    "question": f"就你刚才的回答，请再具体说说：{_clip(w, 100)} 与「{_clip(cq, 40) or '当前问题'}」的关系？",
                    "reason": f"[模型骨架·{tag}] 由弱点信号占位生成；配置为真实 backend 时将改为模型输出。",
                    "source": "qa_weak_point",
                    "target_topic": _clip(w, 80),
                }
            )
    if len(items) < nmax and cq:
        items.append(
            {
                "question": f"如果把「{cq}」用一句话总结你的核心结论，你会怎么说？",
                "reason": f"[模型骨架·{tag}] 题干聚焦占位追问。",
                "source": "qa_weak_point",
                "target_topic": "",
            }
        )
    ca = _clip(current_answer, 60)
    if len(items) < nmax and ca:
        items.append(
            {
                "question": f"你提到「{ca}」，能再举一个简短例子支撑你的观点吗？",
                "reason": f"[模型骨架·{tag}] 基于回答片段的占位延伸。",
                "source": "qa_weak_point",
                "target_topic": "",
            }
        )
    while len(items) < nmax:
        items.append(
            {
                "question": "请用两三句话，直接回应刚才的问题本身，并给出你的核心依据？",
                "reason": f"[模型骨架·{tag}] 泛化占位追问。",
                "source": "qa_weak_point",
                "target_topic": "",
            }
        )
    return items[:nmax]


def _call_real_model(
    *,
    backend: str,
    qa_breakdown: dict | None,
    qa_result: dict | None,
    current_question: str,
    current_answer: str,
    content_breakdown: dict | None,
    ppt_match: dict | None,
    max_items: int,
    timeout: float,
) -> tuple[list[dict[str, Any]], bool, dict[str, Any]]:
    state: dict[str, Any] = {
        "followup_model_reject_reason": None,
        "followup_v2_debug": None,
        "followup_model_http_ms": None,
    }
    tw_base = top_weak_point_for_telemetry(qa_result=qa_result)
    base = (getattr(settings, "FOLLOWUP_MODEL_BASE_URL", None) or "").strip()
    print(
        f"[followup.model.v2] backend={backend!r} version={_FOLLOWUP_MODE_VER} invoke=real_http_openai_compat",
        flush=True,
    )
    if not base:
        state["followup_model_reject_reason"] = "no_base_url"
        state["followup_model_http_ms"] = 0.0
        _emit_model_state_telemetry(
            state,
            qa_result=qa_result,
            model_candidate_count=0,
            quality_gate_passed=False,
            quality_gate_reason="no_llm",
        )
        print(
            f"[followup.model.v2] llm_elapsed_ms=0.0 quality_gate_passed=False quality_gate_reason=no_llm "
            f"top_weak_point={tw_base!r} fallback_reason={state.get('fallback_reason')!r}",
            flush=True,
        )
        print("[followup.model] request built (skipped: FOLLOWUP_MODEL_BASE_URL empty)", flush=True)
        print("[followup.model] http request start (skipped, no base URL)", flush=True)
        print("[followup.model] raw response status=0 preview=''", flush=True)
        print("[followup.model] normalized items=[]", flush=True)
        print("[followup.model] validation passed=False", flush=True)
        print(
            f"[followup.model.v2] reject={state['followup_model_reject_reason']!r} http_ms=0.0 v2=skipped",
            flush=True,
        )
        return [], False, state

    url = _chat_completions_url(base)
    ctx = _compact_llm_context(
        qa_breakdown=qa_breakdown,
        qa_result=qa_result,
        current_question=current_question,
        current_answer=current_answer,
        content_breakdown=content_breakdown,
        ppt_match=ppt_match,
        max_items=max_items,
    )
    user_text = json.dumps(ctx, ensure_ascii=False)
    messages = [
        {"role": "system", "content": FOLLOWUP_V2_SYSTEM_PROMPT},
        {"role": "user", "content": user_text},
    ]
    print("[followup.model] request built", flush=True)

    model = _resolve_model_name(backend=backend)
    api_key = getattr(settings, "FOLLOWUP_MODEL_API_KEY", "") or ""
    print(f"[followup.model] http request start method=POST url={url!r} model={model!r}", flush=True)
    t0 = time.perf_counter()
    try:
        status, raw_body = _post_chat_completions(
            url=url,
            api_key=api_key,
            model=model,
            messages=messages,
            timeout=timeout,
        )
    except Exception:
        http_ms = (time.perf_counter() - t0) * 1000.0
        state["followup_model_http_ms"] = round(http_ms, 2)
        state["followup_model_reject_reason"] = "http_exception"
        _emit_model_state_telemetry(
            state,
            qa_result=qa_result,
            model_candidate_count=0,
            quality_gate_passed=False,
            quality_gate_reason="llm_error",
        )
        print(
            f"[followup.model.v2] llm_elapsed_ms={http_ms:.2f} quality_gate_passed=False quality_gate_reason=llm_error "
            f"top_weak_point={tw_base!r} fallback_reason={state.get('fallback_reason')!r}",
            flush=True,
        )
        print("[followup.model] http error:\n" + traceback.format_exc(), flush=True)
        print("[followup.model] raw response preview='(exception)'", flush=True)
        print("[followup.model] normalized items=[]", flush=True)
        print("[followup.model] validation passed=False", flush=True)
        print(
            f"[followup.model.v2] reject={state['followup_model_reject_reason']!r} http_ms={http_ms:.2f} v2=skipped",
            flush=True,
        )
        return [], False, state

    http_ms = (time.perf_counter() - t0) * 1000.0
    state["followup_model_http_ms"] = round(http_ms, 2)

    preview = raw_body[:2000] + ("…" if len(raw_body) > 2000 else "")
    print(
        f"[followup.model] raw response status={status} len={len(raw_body)} preview={preview!r}",
        flush=True,
    )
    if status < 200 or status >= 300:
        state["followup_model_reject_reason"] = f"http_status_{status}"
        _emit_model_state_telemetry(
            state,
            qa_result=qa_result,
            model_candidate_count=0,
            quality_gate_passed=False,
            quality_gate_reason="llm_http_error",
        )
        print(
            f"[followup.model.v2] llm_elapsed_ms={state['followup_model_http_ms']} quality_gate_passed=False "
            f"quality_gate_reason=llm_http_error top_weak_point={tw_base!r} "
            f"fallback_reason={state.get('fallback_reason')!r}",
            flush=True,
        )
        print("[followup.model] normalized items=[]", flush=True)
        print("[followup.model] validation passed=False", flush=True)
        print(
            f"[followup.model.v2] reject={state['followup_model_reject_reason']!r} "
            f"http_ms={state['followup_model_http_ms']} v2=skipped",
            flush=True,
        )
        return [], False, state

    content = _openai_content_from_body(raw_body)
    parsed = _extract_json_array(content)
    if not isinstance(parsed, list):
        parsed = _parse_followup_http_body(raw_body)
    if not isinstance(parsed, list):
        state["followup_model_reject_reason"] = "parse_not_array"
        _emit_model_state_telemetry(
            state,
            qa_result=qa_result,
            model_candidate_count=0,
            quality_gate_passed=False,
            quality_gate_reason="parse_error",
        )
        print(
            f"[followup.model.v2] llm_elapsed_ms={state['followup_model_http_ms']} quality_gate_passed=False "
            f"quality_gate_reason=parse_error top_weak_point={tw_base!r} model_candidate_count=0",
            flush=True,
        )
        print(f"[followup.model] normalized items={parsed!r}", flush=True)
        print("[followup.model] validation passed=False", flush=True)
        print(
            f"[followup.model.v2] reject={state['followup_model_reject_reason']!r} "
            f"http_ms={state['followup_model_http_ms']} v2=skipped",
            flush=True,
        )
        return [], False, state

    n_raw_dict = len([x for x in (parsed or []) if isinstance(x, dict)])
    prepared = prepare_model_followup_raw_items(parsed, max_items=max_items)
    if prepared is None:
        state["followup_model_reject_reason"] = "raw_items_unusable"
        _emit_model_state_telemetry(
            state,
            qa_result=qa_result,
            model_candidate_count=n_raw_dict,
            quality_gate_passed=False,
            quality_gate_reason="raw_unusable",
        )
        print(
            f"[followup.model.v2] llm_elapsed_ms={state['followup_model_http_ms']} model_candidate_count={n_raw_dict} "
            f"quality_gate_passed=False quality_gate_reason=raw_unusable top_weak_point={tw_base!r}",
            flush=True,
        )
        print(f"[followup.model] normalized items={parsed!r}", flush=True)
        print("[followup.model] validation passed=False", flush=True)
        print(
            f"[followup.model.v2] reject={state['followup_model_reject_reason']!r} "
            f"http_ms={state['followup_model_http_ms']} v2=skipped",
            flush=True,
        )
        return [], False, state

    _prev = [
        {"question": (it.get("question") or "")[:100], "reason": (it.get("reason") or "")[:80]}
        for it in prepared
    ]
    print(f"[followup.model] normalized items={_prev!r}", flush=True)
    gmode = f"followup_model_{backend}_{_FOLLOWUP_MODE_VER}"
    enriched = enrich_followup_item_list(
        prepared, provider_kind="model", generation_mode=gmode
    )
    ok = followup_items_valid(enriched)
    print(f"[followup.model] validation passed={ok}", flush=True)
    if not ok:
        state["followup_model_reject_reason"] = "item_schema_invalid"
        state["followup_v2_debug"] = {"v2_reject_code": "skipped", "note": "schema failed before v2"}
        _emit_model_state_telemetry(
            state,
            qa_result=qa_result,
            model_candidate_count=len(prepared),
            quality_gate_passed=False,
            quality_gate_reason="schema_invalid",
        )
        print(
            f"[followup.model.v2] llm_elapsed_ms={state['followup_model_http_ms']} model_candidate_count={len(prepared)} "
            f"quality_gate_passed=False quality_gate_reason=schema_invalid top_weak_point={tw_base!r} "
            f"fallback_reason={state.get('fallback_reason')!r}",
            flush=True,
        )
        print(
            f"[followup.model.v2] reject={state['followup_model_reject_reason']!r} "
            f"http_ms={state['followup_model_http_ms']} v2=skipped",
            flush=True,
        )
        return [], False, state

    v2_ok, v2_code, v2_debug = _v2_enrich_debug(
        enriched,
        qa_result=qa_result,
        current_question=current_question,
        current_answer=current_answer,
        http_ms=state["followup_model_http_ms"],
    )
    state["followup_v2_debug"] = v2_debug
    wh = v2_debug.get("per_question_weak_hits", [])
    print(
        f"[followup.model.v2] gate v2_reject={v2_code!r} v2_ok={v2_ok} "
        f"weak_hits={wh!r} http_ms={state['followup_model_http_ms']}",
        flush=True,
    )
    if not v2_ok:
        state["followup_model_reject_reason"] = f"v2_{v2_code}"
        _emit_model_state_telemetry(
            state,
            qa_result=qa_result,
            model_candidate_count=len(prepared),
            quality_gate_passed=False,
            quality_gate_reason=v2_code,
        )
        print(
            f"[followup.model.v2] llm_elapsed_ms={state['followup_model_http_ms']} model_candidate_count={len(prepared)} "
            f"quality_gate_passed=False quality_gate_reason={v2_code!r} top_weak_point={v2_debug.get('top_weak_point')!r} "
            f"fallback_reason={state.get('followup_model_reject_reason')!r}",
            flush=True,
        )
        print(
            f"[followup.model.v2] reject={state['followup_model_reject_reason']!r} "
            f"http_ms={state['followup_model_http_ms']}",
            flush=True,
        )
        return [], False, state

    _emit_model_state_telemetry(
        state,
        qa_result=qa_result,
        model_candidate_count=len(prepared),
        quality_gate_passed=True,
        quality_gate_reason="ok",
    )
    state["fallback_reason"] = None
    print(
        f"[followup.model.v2] accept model_path backend={backend!r} "
        f"llm_elapsed_ms={state['llm_elapsed_ms']} model_candidate_count={len(prepared)} quality_gate_passed=True "
        f"top_weak_point={state.get('top_weak_point')!r}",
        flush=True,
    )
    return enriched, True, state


def generate_model_followups(
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
    """
    对外稳定签名与 rule/hybrid 一致；content_document / ppt_match_analysis 预留多模态扩展。
    """
    _ = content_document
    _ = ppt_match_analysis
    backend = get_followup_model_backend()
    timeout = float(getattr(settings, "FOLLOWUP_MODEL_TIMEOUT_SECONDS", 30) or 30)

    if backend == "mock":
        t_m0 = time.perf_counter()
        print(
            f"[followup.model.v2] backend={backend!r} version={_FOLLOWUP_MODE_VER} invoke=mock_local",
            flush=True,
        )
        print("[followup.model] request built (mock placeholder, no HTTP)", flush=True)
        print("[followup.model] http request start (skipped, backend=mock)", flush=True)
        print("[followup.model] raw response preview='(mock)'", flush=True)
        raw = _generate_placeholder_items(
            backend=backend,
            qa_result=qa_result,
            current_question=current_question,
            current_answer=current_answer,
            max_items=max_items,
        )
        prepared = prepare_model_followup_raw_items(raw, max_items=max_items)
        if prepared is None:
            prepared = [
                {
                    "question": "请直接说明你对该问题的结论，并补充一条依据？",
                    "reason": "mock 占位兜底。",
                    "source": "qa_weak_point",
                    "target_topic": "",
                }
            ]
        gmode = f"followup_model_{backend}_{_FOLLOWUP_MODE_VER}"
        items = enrich_followup_item_list(prepared, provider_kind="model", generation_mode=gmode)
        ok = followup_items_valid(items)
        eff_mode = gmode
        m_state: dict[str, Any] = {
            "followup_model_reject_reason": None,
            "followup_v2_debug": None,
            "followup_model_http_ms": 0.0,
        }
        if not ok:
            fb_raw = [
                {
                    "question": "就刚才老师的问题，用一句话说清你的核心结论，并点出一个关键依据，可以吗？",
                    "reason": "mock 路径统一校验未通过时的安全兜底，避免污染主流程。",
                    "source": "qa_weak_point",
                    "target_topic": "",
                }
            ]
            fb_prep = prepare_model_followup_raw_items(fb_raw, max_items=max_items)
            eff_mode = f"{gmode}_sanitized"
            items = enrich_followup_item_list(
                fb_prep or fb_raw,
                provider_kind="model",
                generation_mode=eff_mode,
            )
            ok = followup_items_valid(items)
            print("[followup.model] validation recovered with mock single-item fallback", flush=True)
        _prev_m = [
            {"question": (it.get("question") or "")[:100], "reason": (it.get("reason") or "")[:80]}
            for it in items
        ]
        print(f"[followup.model] normalized items={_prev_m!r}", flush=True)
        print(f"[followup.model] validation passed={ok}", flush=True)
        total_ms = (time.perf_counter() - t_m0) * 1000.0
        n_prepared = len(prepared) if prepared else 0
        m_state["llm_elapsed_ms"] = round(total_ms, 2)
        if ok:
            v2_ok, v2_code, v2_debug = _v2_enrich_debug(
                items,
                qa_result=qa_result,
                current_question=current_question,
                current_answer=current_answer,
                http_ms=0.0,
            )
            v2_debug["followup_model_total_ms"] = round(total_ms, 2)
            m_state["followup_v2_debug"] = v2_debug
            wh = v2_debug.get("per_question_weak_hits", [])
            print(
                f"[followup.model.v2] gate v2_reject={v2_code!r} v2_ok={v2_ok} weak_hits={wh!r} http_ms=0.0",
                flush=True,
            )
            if not v2_ok:
                ok = False
                m_state["followup_model_reject_reason"] = f"v2_{v2_code}"
                items = []
                print(
                    f"[followup.model.v2] reject={m_state['followup_model_reject_reason']!r} total_ms={total_ms:.2f}",
                    flush=True,
                )
        else:
            m_state["followup_model_reject_reason"] = "item_schema_invalid"

        if ok:
            _emit_model_state_telemetry(
                m_state,
                qa_result=qa_result,
                model_candidate_count=n_prepared,
                quality_gate_passed=True,
                quality_gate_reason="ok",
            )
            m_state["fallback_reason"] = None
        else:
            rj = m_state.get("followup_model_reject_reason") or "unknown"
            if rj == "item_schema_invalid":
                _emit_model_state_telemetry(
                    m_state,
                    qa_result=qa_result,
                    model_candidate_count=n_prepared,
                    quality_gate_passed=False,
                    quality_gate_reason="schema_invalid",
                )
            elif str(rj).startswith("v2_"):
                _emit_model_state_telemetry(
                    m_state,
                    qa_result=qa_result,
                    model_candidate_count=n_prepared,
                    quality_gate_passed=False,
                    quality_gate_reason=str(rj).replace("v2_", "", 1),
                )
            else:
                _emit_model_state_telemetry(
                    m_state,
                    qa_result=qa_result,
                    model_candidate_count=0,
                    quality_gate_passed=False,
                    quality_gate_reason="unknown",
                )
        extra: dict[str, Any] = {
            "generation_mode": (eff_mode if ok else f"followup_model_{backend}_invalid_{_FOLLOWUP_MODE_VER}"),
            "fallback_to_rule": False,
            "effective_item_provider": "model" if ok else None,
            "followup_model_backend": backend,
            "followup_model_timeout_seconds": timeout,
            "followup_model_effective_name": _resolve_model_name(backend=backend),
            "followup_model_reject_reason": m_state.get("followup_model_reject_reason"),
            "followup_v2_debug": m_state.get("followup_v2_debug"),
            "followup_model_http_ms": 0.0,
            "followup_model_total_ms": round(total_ms, 2),
            "llm_elapsed_ms": m_state.get("llm_elapsed_ms"),
            "quality_gate_passed": m_state.get("quality_gate_passed", False),
            "quality_gate_reason": m_state.get("quality_gate_reason"),
            "top_weak_point": m_state.get("top_weak_point"),
            "model_candidate_count": m_state.get("model_candidate_count", n_prepared),
            "fallback_reason": m_state.get("fallback_reason"),
        }
        return items, extra

    items, ok, st = _call_real_model(
        backend=backend,
        qa_breakdown=qa_breakdown,
        qa_result=qa_result,
        current_question=current_question,
        current_answer=current_answer,
        content_breakdown=content_breakdown,
        ppt_match=ppt_match,
        max_items=max_items,
        timeout=timeout,
    )
    gmode = f"followup_model_{backend}_{_FOLLOWUP_MODE_VER}"
    mode = gmode if ok else f"followup_model_{backend}_invalid_{_FOLLOWUP_MODE_VER}"
    v2d = st.get("followup_v2_debug")
    if isinstance(v2d, dict) and st.get("followup_model_reject_reason") is not None:
        v2d = {**v2d, "followup_model_reject": st.get("followup_model_reject_reason")}
    extra: dict[str, Any] = {
        "generation_mode": mode,
        "fallback_to_rule": False,
        "effective_item_provider": "model" if ok else None,
        "followup_model_backend": backend,
        "followup_model_timeout_seconds": timeout,
        "followup_model_effective_name": _resolve_model_name(backend=backend),
        "followup_model_reject_reason": st.get("followup_model_reject_reason"),
        "followup_v2_debug": v2d,
        "followup_model_http_ms": st.get("followup_model_http_ms"),
        "llm_elapsed_ms": st.get("llm_elapsed_ms"),
        "quality_gate_passed": st.get("quality_gate_passed"),
        "quality_gate_reason": st.get("quality_gate_reason"),
        "top_weak_point": st.get("top_weak_point"),
        "model_candidate_count": st.get("model_candidate_count"),
        "fallback_reason": st.get("fallback_reason"),
    }
    print(
        f"[followup.model.v2] result ok={ok} mode={mode!r} "
        f"reject={extra.get('followup_model_reject_reason')!r} http_ms={extra.get('followup_model_http_ms')}",
        flush=True,
    )
    return items, extra
