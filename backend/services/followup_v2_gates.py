"""
追问增强 V2：在通用校验（followup_items_valid）之上增加「更像现场老师」的质量门禁，供 model / hybrid 使用。

不修改首问、点评、评分的业务逻辑，仅影响「模型追问是否被采纳」。
"""

from __future__ import annotations

import re
from typing import Any

from services.followup_generation_utils import _followup_questions_too_similar, _has_interrogative_tone

# 与 system prompt 中「8～220 字」一致，过长得罪用户体验且像说明文
V2_MAX_QUESTION_CHARS = 220

# 明显「套话追问」、信息量为 0 时常出现（无现场锚点则判太泛）
_V2_GENERIC_STEMS = (
    "请详细阐述",
    "请进一步阐述",
    "请进一步说明",
    "能再详细说说",
    "再详细说说",
    "请谈谈你的理解",
    "你还有什么要补充",
    "请结合实际",
    "请展开讲讲",
    "请举例说明",
    "请用两三句话",
    "简单说说",
    "顺便问一下",
    "还有什么看法",
    "综合上述",
    "基于以上",
)

# 短句 + 全抽象提示词 = 过泛
_V2_TRIVIAL_OPENERS = (
    "请说明",
    "请分析",
    "请解释",
    "请介绍",
    "请描述",
    "请回答",
)


def build_weak_point_anchors(*, qa_result: dict | None) -> list[str]:
    """
    仅来自 weak_points / missing_keywords / followup_candidate_topics，用于「是否扣住弱点」门禁。
    """
    raw: list[str] = []
    if isinstance(qa_result, dict):
        for key in ("weak_points", "missing_keywords", "followup_candidate_topics"):
            v = qa_result.get(key)
            if not isinstance(v, list):
                continue
            for x in v:
                s = str(x).strip()
                if s:
                    raw.append(s[:200])
    seen: set[str] = set()
    out: list[str] = []
    for a in raw:
        k = re.sub(r"\s+", "", a.casefold()) if a.isascii() else re.sub(r"\s+", "", a)
        if not k or k in seen or len(a) < 2:
            continue
        seen.add(k)
        out.append(a)
    return out[:24]


def top_weak_point_for_telemetry(*, qa_result: dict | None) -> str | None:
    """调试：展示当前轮最应盯的弱点点名（非评分逻辑）。"""
    if not isinstance(qa_result, dict):
        return None
    wp = qa_result.get("weak_points")
    if isinstance(wp, list) and wp:
        s = str(wp[0]).strip()
        if s:
            return s[:120]
    mk = qa_result.get("missing_keywords")
    if isinstance(mk, list) and mk:
        s = str(mk[0]).strip()
        if s:
            return s[:80]
    return None


def _norm_compact(s: str) -> str:
    return re.sub(r"\s+", "", (s or ""))


def _question_has_anchor_substring(question: str, anchor: str) -> bool:
    q = _norm_compact(question)
    a0 = re.sub(r"\s+", "", (anchor or "").strip())
    if len(a0) < 2 or not q:
        return False
    if a0 in q:
        return True
    if len(a0) > 6:
        return a0[:6] in q
    return False


def has_local_context_hit(
    question: str,
    *,
    current_question: str = "",
    current_answer: str = "",
) -> bool:
    """无弱点列表时，追问至少与题干/答句有二元共现，避免完全飘移。"""
    return _any_bigram_overlap(question, current_question) or _any_bigram_overlap(
        question, current_answer
    )


def _any_bigram_overlap(a: str, b: str) -> bool:
    x = _norm_compact(a)
    y = _norm_compact(b)
    if len(x) < 2 or len(y) < 2:
        return False
    for i in range(len(x) - 1):
        if x[i : i + 2] in y:
            return True
    return False


def per_item_weak_hits(
    items: list[dict[str, Any]],
    weak_only_anchors: list[str],
) -> list[list[str]]:
    """
    每条 question 上命中的弱点锚点（仅 weak_points + missing + candidate_topics 段，不含整段题干/答句）。
    """
    hits: list[list[str]] = []
    for it in items:
        q = str(it.get("question") or "")
        ph: list[str] = []
        for a in weak_only_anchors:
            if _question_has_anchor_substring(q, a):
                ph.append(a[:120])
        hits.append(ph)
    return hits


def assess_followup_v2_quality(
    items: list[dict[str, Any]],
    *,
    weak_only_anchors: list[str],
    current_question: str = "",
    current_answer: str = "",
) -> tuple[bool, str, dict[str, Any]]:
    """
    返回 (是否通过, 不通过原因码, 调试信息 dict)。
    原因码：ok / too_long / not_question / too_generic / weak_point_miss / duplicate
    """
    w_only = [a for a in weak_only_anchors if len(_norm_compact(a)) >= 2]
    debug: dict[str, Any] = {
        "weak_anchors": [a[:80] for a in w_only],
        "per_item": [],
    }
    if not items:
        return False, "weak_point_miss", debug

    for it0 in items:
        if not isinstance(it0, dict):
            return False, "not_question", debug
    qs = [str(it.get("question") or "").strip() for it in items]
    for i in range(len(qs)):
        for j in range(i + 1, len(qs)):
            if _followup_questions_too_similar(qs[i], qs[j]):
                debug["per_item"] = [{"idx": i, "j": j, "fail": "duplicate"}]
                return False, "duplicate", debug

    for i, it in enumerate(items):
        q = str(it.get("question") or "").strip()
        rsn = str(it.get("reason") or "").strip()
        one: dict[str, Any] = {"idx": i, "q_len": len(q)}
        if len(q) > V2_MAX_QUESTION_CHARS:
            one["fail"] = "too_long"
            debug["per_item"].append(one)
            return False, "too_long", debug

        if not _has_interrogative_tone(q):
            one["fail"] = "not_question"
            debug["per_item"].append(one)
            return False, "not_question", debug

        if _is_too_generic_question(
            q,
            weak_anchors=w_only,
            current_question=current_question,
            current_answer=current_answer,
            question_idx=i,
        ):
            one["fail"] = "too_generic"
            debug["per_item"].append(one)
            return False, "too_generic", debug

        if w_only and not _item_covers_weak_anchor(q, rsn, w_only):
            one["fail"] = "weak_point_miss"
            debug["per_item"].append(one)
            return False, "weak_point_miss", debug

        wh = [a for a in w_only if _question_has_anchor_substring(q, a)]
        one["weak_hits_in_question"] = wh
        if w_only and not wh:
            one["weak_hits_in_reason"] = [a for a in w_only if _norm_compact(a) in _norm_compact(rsn)]
        if not w_only and not has_local_context_hit(
            q, current_question=current_question, current_answer=current_answer
        ):
            one["fail"] = "weak_point_miss"
            one["note"] = "no_local_context"
            debug["per_item"].append(one)
            return False, "weak_point_miss", debug
        debug["per_item"].append(one)

    return True, "ok", debug


def _item_covers_weak_anchor(q: str, rsn: str, w_only: list[str]) -> bool:
    if not w_only:
        return True
    comb = _norm_compact(q) + _norm_compact(rsn)
    for a in w_only:
        a0 = _norm_compact(a)
        if len(a0) < 2:
            continue
        if a0 in _norm_compact(q) or a0 in _norm_compact(rsn) or a0 in comb:
            return True
        if len(a0) > 4 and a0[:4] in _norm_compact(q):
            return True
    return False


def _is_too_generic_question(
    q: str,
    *,
    weak_anchors: list[str],
    current_question: str = "",
    current_answer: str = "",
    question_idx: int = 0,
) -> bool:
    """有弱点锚时须扣词；无弱点时须与题干/答句有现场关联，避免纯套话。"""
    t = (q or "").strip()
    if not t:
        return True
    if weak_anchors:
        for a in weak_anchors:
            if _question_has_anchor_substring(t, a):
                return False
        if len(t) > 64:
            return False
        for stem in _V2_GENERIC_STEMS:
            if stem in t:
                return True
        if len(t) <= 28:
            for op in _V2_TRIVIAL_OPENERS:
                if t.startswith(op) and "？" not in t and "?" not in t:
                    return True
        return False
    if has_local_context_hit(t, current_question=current_question, current_answer=current_answer):
        return False
    if len(t) > 64:
        return False
    for stem in _V2_GENERIC_STEMS:
        if stem in t:
            return True
    if len(t) <= 28:
        for op in _V2_TRIVIAL_OPENERS:
            if t.startswith(op) and "？" not in t and "?" not in t:
                return True
    if len(t) <= 22 and question_idx == 0 and not any(x in t for x in ("？", "吗", "呢", "么")):
        return True
    return False
