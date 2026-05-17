"""
AI 追问官 / 点评官 V1（规则预埋）

- 当前实现为 **rule-based**，仅用已有评分 / 问答 / 文档结构等数据做结构化输出，便于产品与前端先跑通。
- **V1 不实现**「自动猜当前页」「自动出题入口」或独立出题链路；追问条目由现有 `qa_breakdown`、
  `content_breakdown`、`content_document`、`ppt_match_analysis` 等规则拼装。
- 后续可替换为更贴近真实答辩的 **自动出题 / 自动追问链**；复杂多步流程可迁移为 **Agent** 或
  **流程编排框架**（如 LangGraph），本模块仍可作为统一入参/出参入口以保持 API 稳定。
- 不要在此文件直接引入外部 agent / 大模型依赖。
"""

from __future__ import annotations

import difflib
import random
import re
from typing import Any

COACH_VERSION = "v1-rule-based+commentary-chain"

_MODULE_LABELS = {
    "language": "语言表达",
    "posture": "仪态表现",
    "content": "内容讲解",
    "qa": "问答表现",
}


def _as_float(v: Any, default: float = 0.0) -> float:
    try:
        if v is None or v == "":
            return default
        return float(v)
    except (TypeError, ValueError):
        return default


def _norm_question_text(s: str) -> str:
    t = (s or "").strip()
    if t.startswith("可追问："):
        t = t[4:].strip()
    if t.startswith("请具体说明"):
        return t
    return t[:500]


def _followup_entry(question: str, reason: str, source: str) -> dict[str, str]:
    return {
        "question": question.strip()[:400],
        "reason": reason.strip()[:500],
        "source": source,
    }


def _build_followup_questions(
    *,
    qa_breakdown: dict[str, Any] | None,
    qa_result: dict[str, Any] | None,
    content_breakdown: dict[str, Any] | None,
    content_document: dict[str, Any] | None,
    ppt_match: dict[str, Any] | None,
    ppt_match_analysis: dict[str, Any] | None,
) -> list[dict[str, str]]:
    items: list[dict[str, str]] = []
    seen_q: set[str] = set()

    def push(q: str, reason: str, source: str) -> None:
        nq = _norm_question_text(q)
        key = nq[:80]
        if not nq or key in seen_q:
            return
        seen_q.add(key)
        items.append(_followup_entry(nq, reason, source))

    qa_bd = qa_breakdown if isinstance(qa_breakdown, dict) else None

    if qa_bd:
        for t in qa_bd.get("followup_candidate_topics") or []:
            if not isinstance(t, str) or not t.strip():
                continue
            push(
                t if "？" in t or "?" in t else f"{t}——请用一两句话说明你的看法。",
                "来自问答评估中生成的待追问主题（规则）。",
                "qa_weak_point",
            )
            if len(items) >= 3:
                return items[:3]

        miss_n = int(qa_bd.get("missing_keyword_count") or 0)
        rel = bool(qa_bd.get("is_relevant"))
        if (miss_n >= 2 or not rel) and len(items) < 3:
            push(
                "请对照参考要点，逐条说明你已覆盖哪些、还缺哪些？",
                "缺失关键词较多或切题度不足，需要把要点对齐讲清楚。",
                "qa_weak_point",
            )

        for w in qa_bd.get("weak_points") or []:
            if not isinstance(w, str) or not w.strip():
                continue
            push(
                f"针对「{w.strip()[:60]}」，你打算如何改进？请举一个具体例子。",
                w.strip()[:200],
                "qa_weak_point",
            )
            if len(items) >= 3:
                return items[:3]

    cb = content_breakdown if isinstance(content_breakdown, dict) else None
    if cb and len(items) < 3:
        cov = _as_float(cb.get("keyword_coverage"), 0.0)
        if 0 < cov <= 1.0:
            cov = cov * 100.0
        th = bool(cb.get("title_hit"))
        oh = bool(cb.get("outline_hit"))
        if (cov < 48 or (not th and not oh)) and ppt_match:
            push(
                "当前页与讲解的对应关系是什么？能否用一句话点出本页在整体中的位置？",
                "关键词覆盖偏低或标题/大纲未在口述中体现，建议强化结构表达。",
                "content_gap",
            )

    if content_document and isinstance(content_document, dict) and len(items) < 3:
        outline = content_document.get("outline") or []
        for o in outline[:2]:
            if not isinstance(o, dict):
                continue
            title = str(o.get("title") or "").strip()
            if len(title) >= 2:
                push(
                    f"关于大纲中的「{title[:50]}」，你认为听众最需要记住的一点是什么？",
                    "结合课件大纲生成的跟进问题，帮助把脉络讲透。",
                    "document_outline",
                )
                break

    if ppt_match_analysis and isinstance(ppt_match_analysis, dict) and len(items) < 3:
        missed = ppt_match_analysis.get("missed_pages") or []
        if missed:
            push(
                f"第 {missed[0]} 页（或其它漏讲页）若补讲，你会强调哪两个信息？",
                "逐页分析显示存在漏讲页，可用追问补齐讲解完整性。",
                "content_gap",
            )

    return items[:3]


def _cq_theme_short(cq: str, limit: int = 42) -> str:
    """从当前题干抽一小段可嵌入追问的主题语，避免整题粘贴过长。"""
    t = (cq or "").strip().replace("\n", " ")
    if not t:
        return ""
    for sep in ("？", "?", "：", ":", "——", "—", "。", ".", "；", ";"):
        if sep in t:
            t = t.split(sep)[0].strip()
            break
    t = re.sub(r"\s+", " ", t).strip()
    if len(t) > limit:
        return t[: limit - 1].rstrip("，、 ") + "…"
    return t


def _pick_question_text(rng: random.Random, templates: list[str], slot: int) -> str:
    """同一轮内按 slot 与随机偏移轮换模板，减少三连相同句式。"""
    if not templates:
        return ""
    i = (slot * 5 + rng.randrange(0, max(1, len(templates) * 3))) % len(templates)
    return templates[i]


# ---------- 追问文案自然化：归一化 / 相似度 / 关键词过滤（仅用于 question 拼装）----------

def _normalize_for_similarity(q: str) -> str:
    t = (q or "").strip().lower()
    t = re.sub(r"\s+", "", t)
    t = re.sub(r"[「」“”\"'？?！!，,。.、；;:：]", "", t)
    return t[:120]


def _questions_too_similar(a: str, b: str, ratio: float = 0.82) -> bool:
    na, nb = _normalize_for_similarity(a), _normalize_for_similarity(b)
    if not na or not nb:
        return False
    if na == nb:
        return True
    shorter, longer = (na, nb) if len(na) <= len(nb) else (nb, na)
    if len(longer) >= 28 and longer.startswith(shorter[: min(28, len(shorter))]):
        return True
    return difflib.SequenceMatcher(None, na, nb).ratio() >= ratio


def _usable_keyword_for_question(k: str) -> bool:
    """过滤技术/占位字段，避免「要点对齐」等生硬塞进 question。"""
    s = (k or "").strip()
    if len(s) < 2:
        return False
    bad_sub = (
        "要点对齐",
        "结构对应",
        "qa_weak",
        "content_gap",
        "outline_gap",
    )
    low = s.lower()
    for b in bad_sub:
        if b in s or b in low:
            return False
    if re.fullmatch(r"第\d+页", s):
        return False
    return True


def _answer_theme_short(answer: str, limit: int = 24) -> str:
    """从上一轮回答抽一小段可用作口头呼应（次于题干优先级）。"""
    t = (answer or "").strip().replace("\n", " ")
    if not t:
        return ""
    for sep in ("。", "；", ";", "，", ",", "、", "：", ":"):
        if sep in t[:100]:
            t = t.split(sep)[0].strip()
            break
    t = re.sub(r"\s+", "", t)
    if len(t) > limit:
        t = t[: limit - 1] + "…"
    return t if len(t) >= 2 else ""


# 老师口吻模板池（不按 weak 原文拼接进 question）
_TPL_A_VAGUE_OFF = [
    "你刚才的回答还比较笼统，能不能围绕这个问题本身再具体说一下？",
    "你提到了一些内容，但和问题核心的关系还不够清楚，请再解释一下。",
    "如果只围绕刚才这个问题来回答，你认为最关键的一点是什么？",
    "你的回答还没有真正落到这个问题上，请重新组织一下，重点说明你的核心结论。",
    "我听下来意思有了，但和题干之间的对应还不够紧，能不能再对准问题本身说一句？",
    "能不能用更直白的话，先点明你的核心判断，再简要展开理由？",
]

_TPL_B_MISSING_KW = [
    '你刚才还没有提到「{kw}」，这一点为什么重要？',
    '如果从「{kw}」这个角度补充，你会怎么说明？',
    '你前面的回答里还没把「{kw}」讲清楚，能再展开一两句吗？',
    '除了刚才说的这些，「{kw}」这一块也需要顾及到，请补上。',
    '现场听众在「{kw}」上容易留问号，你怎么用一句话把它说清楚？',
    '请你把「{kw}」和刚才的问题直接挂上钩，中间别跳步。',
]

_TPL_C_RELATION = [
    "你刚才的回答和前面这个问题之间，关系还不够清楚，请你重新对应一下。",
    "如果把你的回答和刚才的问题一一对上，你会怎么解释？",
    "你前面讲到的内容和这个问题的关联在哪里？请明确说一下。",
    "听众现在最容易疑惑的是「这和问题有什么关系」，你怎么解释？",
    "能不能先用一句话说明：你的结论是如何直接回应刚才这个问题的？",
    "请你把逻辑链条补全：从问题到结论，中间最关键的一环是什么？",
]

_TPL_D_DEEPEN = [
    "这个点你可以再往下讲一层吗？",
    "如果让你继续展开，你觉得最值得补充的是什么？",
    "这个部分你刚才讲得比较快，能不能再详细说明一下？",
    "听众听完这一段后，最应该记住什么？为什么？",
    "顺着刚才的问题往下，你觉得还有哪一层需要交代清楚？",
    "如果少讲一句就会让人误会，你会优先补哪一句？",
]

_TPL_C_MATERIAL = [
    "你刚才的回答和材料里这一部分的侧重点之间，是怎么呼应的？请对准了说。",
    "如果把课件里的要点和你刚才的表述对齐，中间还差哪一小步？",
    "听众会把你的回答和材料内容对照着听，你怎么帮他们把两者对上号？",
    "从材料回到刚才这个问题，你最想强调的一条支撑是什么？",
]

_TPL_D_OUTLINE = [
    "大纲里这一节和刚才的问题，顺着听应该从哪里连起来？",
    "如果听众只记住大纲里这一点，你希望是什么？为什么是它？",
    "顺着结构往下走，你认为最难解释清楚的环节是什么？怎么讲才让人听得懂？",
    "这一部分你刚才带得比较快，能不能再展开一层，把结构说透？",
]


def _merge_qa_signals_for_v2(
    qa_breakdown: dict[str, Any] | None,
    qa_result: dict[str, Any] | None,
) -> dict[str, Any]:
    """合并 qa_breakdown 与 qa_result 中的弱点信号，供 V2 追问链使用。"""
    merged: dict[str, Any] = {}
    if isinstance(qa_breakdown, dict):
        merged.update(qa_breakdown)
    if not isinstance(qa_result, dict):
        return merged
    for key in ("weak_points", "followup_candidate_topics", "is_relevant", "relevance_reason"):
        v = qa_result.get(key)
        if v is not None and (key not in merged or merged.get(key) in (None, [], "")):
            merged[key] = v
    mk = qa_result.get("missing_keywords")
    if isinstance(mk, list):
        cleaned = [str(x).strip() for x in mk if str(x).strip()]
        prev = merged.get("missing_keywords")
        if not isinstance(prev, list) or not prev:
            merged["missing_keywords"] = cleaned
        if merged.get("missing_keyword_count") is None:
            merged["missing_keyword_count"] = len(merged.get("missing_keywords") or cleaned)
    return merged


def build_followup_questions_v2(
    *,
    qa_breakdown: dict[str, Any] | None = None,
    qa_result: dict[str, Any] | None = None,
    current_question: str = "",
    current_answer: str = "",
    content_breakdown: dict[str, Any] | None = None,
    content_document: dict[str, Any] | None = None,
    ppt_match: dict[str, Any] | None = None,
    ppt_match_analysis: dict[str, Any] | None = None,
    max_items: int = 3,
) -> list[dict[str, str]]:
    """
    V2 规则版弱点驱动追问链：信号优先级与来源字段不变（qa_weak_point | content_gap | outline_gap）。
    文案自然化：按 A/B/C/D 类老师口吻模板生成 question；weak 原文与脏关键词不硬塞进 question，
    reason / target_topic 仍承载可解释性。
    """
    nmax = max(1, min(int(max_items or 3), 3))
    qa_merged = _merge_qa_signals_for_v2(qa_breakdown, qa_result)
    items: list[dict[str, str]] = []
    seen_keys: set[str] = set()

    cq_full = (current_question or "").strip()
    cq_theme = _cq_theme_short(cq_full, 42)
    anchor = cq_theme or "刚才这个问题"
    ca = (current_answer or "").strip()
    ans_hint = _answer_theme_short(ca, 26)
    ca_hint = f"上一轮回答约 {len(ca)} 字。" if ca else ""

    seed_bits = f"{cq_full[:160]}|{ca[:200]}"
    rng = random.Random((hash(seed_bits) & 0x7FFFFFFF) or 1)

    def push(q: str, reason: str, source: str, target_topic: str = "") -> None:
        if source not in ("qa_weak_point", "content_gap", "outline_gap"):
            source = "qa_weak_point"
        nq = _norm_question_text(q)
        if not nq:
            return
        for ex in items:
            if _questions_too_similar(nq, ex["question"]):
                return
        key = nq[:80]
        if key in seen_keys:
            return
        seen_keys.add(key)
        items.append(
            {
                "question": nq[:400],
                "reason": reason.strip()[:500],
                "source": source,
                "target_topic": (target_topic or "").strip()[:120],
            }
        )

    def personalize_anchor(q: str) -> str:
        """优先用题干主题替换泛称「刚才这个问题 / 这个问题本身」，概率混入避免句句相同。"""
        if not anchor or anchor == "刚才这个问题":
            return q
        if "刚才这个问题" in q and rng.random() < 0.5:
            return q.replace("刚才这个问题", f"「{anchor}」", 1)
        if "这个问题本身" in q and rng.random() < 0.5:
            return q.replace("这个问题本身", f"「{anchor}」本身", 1)
        return q

    def maybe_lead_answer(q: str, slot: int) -> str:
        """其次呼应上一轮回答中出现的短主题（不粘贴长原文）。"""
        if (
            ans_hint
            and len(ans_hint) >= 4
            and slot % 2 == 1
            and rng.random() < 0.42
            and not q.startswith("你前面")
        ):
            return f"你前面已经谈到了「{ans_hint}」，{q}"
        return q

    slot = 0

    # 1) 待追问主题：深挖型 D，主题细节放在 reason / target_topic
    for t in qa_merged.get("followup_candidate_topics") or []:
        if len(items) >= nmax:
            return items[:nmax]
        if not isinstance(t, str) or not t.strip():
            continue
        topic = t.strip()[:100]
        if "？" in topic or "?" in topic:
            qtext = topic
            rsn = f"评估规则建议沿此方向再答。{ca_hint}"
        else:
            raw = _pick_question_text(rng, _TPL_D_DEEPEN, slot)
            qtext = maybe_lead_answer(personalize_anchor(raw), slot)
            rsn = f"规则归纳的延伸方向：{topic[:180]}。{ca_hint}"
        push(qtext, rsn, "qa_weak_point", topic[:120])
        slot += 1

    # 2) weak_points：仅 A 类笼统切题/聚焦，不把 weak 原文拼进 question
    for w in qa_merged.get("weak_points") or []:
        if len(items) >= nmax:
            return items[:nmax]
        if not isinstance(w, str) or not w.strip():
            continue
        wk = w.strip()
        raw = _pick_question_text(rng, _TPL_A_VAGUE_OFF, slot)
        qtext = maybe_lead_answer(personalize_anchor(raw), slot)
        push(
            qtext,
            f"问答评估中的薄弱点（规则）：{wk[:200]}。{ca_hint}",
            "qa_weak_point",
            wk[:120],
        )
        slot += 1

    # 3) 缺失关键词：B 类；过滤不宜进题干的占位词
    miss_kw = qa_merged.get("missing_keywords") or []
    if isinstance(miss_kw, list):
        for kw in miss_kw[:2]:
            if len(items) >= nmax:
                return items[:nmax]
            if not isinstance(kw, str) or not str(kw).strip():
                continue
            k = str(kw).strip()[:40]
            if not _usable_keyword_for_question(k):
                continue
            tpl = _pick_question_text(rng, _TPL_B_MISSING_KW, slot)
            qtext = tpl.format(kw=k)
            push(
                qtext,
                f"参考要点尚未充分覆盖（规则）。{ca_hint}",
                "qa_weak_point",
                k,
            )
            slot += 1

    miss_n = int(qa_merged.get("missing_keyword_count") or 0)
    rel = bool(qa_merged.get("is_relevant"))
    if (miss_n >= 2 or not rel) and len(items) < nmax:
        pool = list(_TPL_A_VAGUE_OFF)
        if miss_n >= 2:
            pool.append(
                "请你对照刚才的问题，把关键点再讲清楚：哪些已经说到、哪些还需要补强？"
            )
        raw = _pick_question_text(rng, pool, slot)
        qtext = maybe_lead_answer(personalize_anchor(raw), slot)
        push(
            qtext,
            "切题或要点覆盖不足（规则）；题干不使用内部评分字段字样。",
            "qa_weak_point",
            "",
        )
        slot += 1

    cb = content_breakdown if isinstance(content_breakdown, dict) else None
    if cb and len(items) < nmax:
        cov = _as_float(cb.get("keyword_coverage"), 0.0)
        if 0 < cov <= 1.0:
            cov = cov * 100.0
        th = bool(cb.get("title_hit"))
        oh = bool(cb.get("outline_hit"))
        if cov < 48 or (not th and not oh):
            mix = list(_TPL_C_MATERIAL) + list(_TPL_D_DEEPEN)
            raw = _pick_question_text(rng, mix, slot)
            qtext = maybe_lead_answer(personalize_anchor(raw), slot)
            push(
                qtext,
                "讲解与材料要点对齐偏弱（规则）。",
                "content_gap",
                "",
            )
            slot += 1

    if ppt_match and isinstance(ppt_match, dict) and len(items) < nmax:
        title = str(ppt_match.get("title") or "").strip()
        if len(title) >= 2:
            mix = list(_TPL_C_MATERIAL) + list(_TPL_C_RELATION)
            raw = _pick_question_text(rng, mix, slot)
            qtext = maybe_lead_answer(personalize_anchor(raw), slot)
            push(
                qtext,
                "结合当前内容页做衔接追问（规则）。",
                "content_gap",
                title[:80],
            )
            slot += 1
        mks = ppt_match.get("matched_keywords") or ppt_match.get("missing_keywords")
        if isinstance(mks, list) and mks and len(items) < nmax:
            k0 = str(mks[0]).strip()[:30]
            if k0 and _usable_keyword_for_question(k0):
                tpl = _pick_question_text(rng, _TPL_B_MISSING_KW, slot)
                qtext = tpl.format(kw=k0)
                push(
                    qtext,
                    "结合当前页关键词补充说明（规则）。",
                    "content_gap",
                    k0,
                )
                slot += 1

    if content_document and isinstance(content_document, dict) and len(items) < nmax:
        outline = content_document.get("outline") or []
        for o in outline[:2]:
            if not isinstance(o, dict):
                continue
            otitle = str(o.get("title") or "").strip()
            if len(otitle) >= 2:
                mix = list(_TPL_D_OUTLINE) + list(_TPL_C_RELATION)
                raw = _pick_question_text(rng, mix, slot)
                qtext = maybe_lead_answer(personalize_anchor(raw), slot)
                push(
                    qtext,
                    "结合课件大纲做的结构延展（规则）。",
                    "outline_gap",
                    otitle[:80],
                )
                break

    if ppt_match_analysis and isinstance(ppt_match_analysis, dict) and len(items) < nmax:
        missed = ppt_match_analysis.get("missed_pages") or []
        if missed:
            mix = list(_TPL_D_DEEPEN) + list(_TPL_C_RELATION)
            raw = _pick_question_text(rng, mix, slot)
            qtext = maybe_lead_answer(personalize_anchor(raw), slot)
            push(
                qtext,
                "逐页分析提示讲解完整性可加强（规则）。",
                "content_gap",
                f"第{missed[0]}页",
            )

    return items[:nmax]


def _pick_strong_weak(
    score_breakdown: dict[str, Any] | None,
) -> tuple[tuple[str, str, float] | None, tuple[str, str, float] | None]:
    if not isinstance(score_breakdown, dict):
        return None, None
    modules = score_breakdown.get("modules") or {}
    vm = score_breakdown.get("valid_modules") or {}
    scored: list[tuple[str, str, float]] = []
    for key, label in _MODULE_LABELS.items():
        if not vm.get(key):
            continue
        m = modules.get(key)
        if not isinstance(m, dict):
            continue
        scored.append((key, label, _as_float(m.get("score"), 0.0)))
    if not scored:
        return None, None
    scored.sort(key=lambda x: x[2], reverse=True)
    return scored[0], scored[-1]


def _valid_modules_map(score_breakdown: dict[str, Any] | None) -> dict[str, Any]:
    if not isinstance(score_breakdown, dict):
        return {}
    vm = score_breakdown.get("valid_modules")
    return vm if isinstance(vm, dict) else {}


def _language_analysis_missing(
    valid_modules: dict[str, Any],
    audio_valid: bool | None,
) -> bool:
    if audio_valid is False:
        return True
    if valid_modules.get("language") is False:
        return True
    return False


def _posture_analysis_missing(
    valid_modules: dict[str, Any],
    vision_valid: bool | None,
) -> bool:
    if vision_valid is False:
        return True
    if valid_modules.get("posture") is False:
        return True
    return False


def _dedupe_lines(lines: list[str], max_items: int) -> list[str]:
    out: list[str] = []
    seen: set[str] = set()
    for raw in lines:
        t = (raw or "").strip()
        if not t:
            continue
        k = t[:48]
        if k in seen:
            continue
        seen.add(k)
        out.append(t[:400])
        if len(out) >= max_items:
            break
    return out


def _build_coach_narrative(
    *,
    scoring_profile: str | None,
    scoring_profile_label: str | None,
    score_explanations: dict[str, Any] | None,
    score_breakdown: dict[str, Any] | None,
    total_score: float | None,
    qa_breakdown: dict[str, Any] | None,
    content_breakdown: dict[str, Any] | None,
    audio_valid: bool | None,
    vision_valid: bool | None,
    ppt_match_source: str | None,
    qa_source: str | None,
) -> dict[str, Any]:
    """规则化「老师口吻」点评链：综合点评 / 优点 / 问题 / 下一轮建议（不接模型）。"""
    se = score_explanations if isinstance(score_explanations, dict) else {}
    total_expl = se.get("total") or {}
    total_summary = str(total_expl.get("summary") or "").strip()
    total_items = total_expl.get("items") if isinstance(total_expl.get("items"), list) else []

    mode_label = str(scoring_profile_label or "").strip() or (
        "答辩模式" if str(scoring_profile or "defense").strip() == "defense" else "面试模式"
    )
    ts = _as_float(total_score, 0.0)
    vm = _valid_modules_map(score_breakdown)
    strong, weak = _pick_strong_weak(score_breakdown)
    if strong and weak and strong[0] == weak[0]:
        weak = None

    strengths: list[str] = []
    weaknesses: list[str] = []
    next_round: list[str] = []

    if _language_analysis_missing(vm, audio_valid):
        weaknesses.append(
            "本轮语言样本不足，尚未形成有效的语言分析；请在相对安静的环境里连续讲解，并确认麦克风可用。"
        )
    if _posture_analysis_missing(vm, vision_valid):
        weaknesses.append(
            "本轮仪态/画面分析未能形成稳定结论，可能与机位、光线或上半身未持续入镜有关；下次请固定机位、让面部清晰出现在画面中。"
        )

    if strong:
        _, slab, sscore = strong
        strengths.append(
            f"{slab}这一轮相对最稳（大约 {sscore:.1f} 分），可以当作你的信心支点，下一轮继续发扬。"
        )
    else:
        if any(vm.get(k) for k in ("language", "posture", "content", "qa")):
            strengths.append(
                "你已经把完整流程走了一遍，这本身就是很好的训练积累；接下来可以逐项把短板补厚。"
            )

    pms = str(ppt_match_source or "").strip().lower()
    if pms == "auto_guess" and vm.get("content"):
        strengths.append("讲解主线已基本被识别，课件对应关系整体是清楚的。")

    qas = str(qa_source or "").strip().lower()
    if qas == "followup_generated" and vm.get("qa"):
        strengths.append(
            "系统已进一步追问你的薄弱点，说明你完成了更有针对性的答辩练习，这是很好的深度训练。"
        )

    if weak:
        wkey, wlab, wscore = weak
        weaknesses.append(
            f"当前最需要加把劲的是「{wlab}」（大约 {wscore:.1f} 分），建议下一轮刻意围绕这一块多练几次。"
        )
        mod_expl = se.get(wkey)
        if isinstance(mod_expl, dict):
            for line in (mod_expl.get("items") or [])[:1]:
                if isinstance(line, str) and line.strip():
                    weaknesses.append(f"具体一点说：{line.strip()[:200]}")

    qa_bd = qa_breakdown if isinstance(qa_breakdown, dict) else None
    if qa_bd:
        for wp in (qa_bd.get("weak_points") or [])[:2]:
            if isinstance(wp, str) and wp.strip():
                weaknesses.append(f"问答上还可以再抠细节：{wp.strip()[:180]}")

    cb = content_breakdown if isinstance(content_breakdown, dict) else None
    if cb and vm.get("content"):
        cov = _as_float(cb.get("keyword_coverage"), 0.0)
        if 0 < cov <= 1.0:
            cov = cov * 100.0
        th = bool(cb.get("title_hit"))
        if cov < 42 and not th:
            weaknesses.append("内容和当前页的咬合还可以更紧，试着把页标题里的关键词直接嵌进你的口述里。")

    strengths = _dedupe_lines(strengths, 4)
    weaknesses = _dedupe_lines(weaknesses, 5)

    if not strengths:
        strengths.append(
            "老师看到你认真走完了这一轮；先把流程跑顺、把表达说完整，就是很好的起点。"
        )
    if not weaknesses:
        weaknesses.append(
            "整体没有特别拖后腿的单项，可以尝试把语速、停顿和互动感再打磨一下，让听众更跟得上。"
        )

    if weak:
        wkey_nr, wlab_nr, _wscore_nr = weak
        next_round.append(
            f"下一轮开场先用 5 分钟，只练「{wlab_nr}」这一项，练到你自己觉得顺口为止。"
        )
        mod_nr = se.get(wkey_nr)
        if isinstance(mod_nr, dict):
            for line in (mod_nr.get("items") or [])[:2]:
                if isinstance(line, str) and line.strip():
                    next_round.append(line.strip()[:200])
    if qa_bd:
        for wp in (qa_bd.get("weak_points") or [])[:1]:
            if isinstance(wp, str) and wp.strip():
                next_round.append(f"问答复盘：针对「{wp.strip()[:40]}…」准备两句更具体的例子，下次脱口而出。")
    if total_items:
        next_round.append(str(total_items[0]).strip()[:220])
    if not next_round:
        next_round.append("建议固定同一套设备与机位，每一轮对照录像与分数，看进步是否看得见、摸得着。")
    next_round.append("下一轮可以先录音听一遍自己的开头 30 秒，把「第一句」说到更清楚、更有把握。")

    next_round = _dedupe_lines(next_round, 5)
    while len(next_round) < 3:
        next_round.append("把本轮暴露的问题记三条便签，下次训练前先看一遍再开口。")
    next_round = next_round[:5]

    bridge = ""
    if qas == "followup_generated":
        bridge = " 系统结合你的回答做了进一步追问，请把这类针对性问答也当成主课来练。"
    elif pms == "auto_guess":
        bridge = " 内容与课件的对应关系已由规则初步对齐，你可在下一轮把「页与话」扣得更紧。"

    head = (
        f"同学你好，老师帮你小结一下：这是「{mode_label}」的一次完整练习，总分大约在 {ts:.1f} 分。"
        f"{bridge}"
    ).strip()
    overall_parts = [
        head,
        strengths[0],
        weaknesses[0],
    ]
    if total_summary:
        overall_parts.append(total_summary[:260])
    overall_commentary = " ".join(p for p in overall_parts if p).strip()[:900]

    coach_commentary = overall_commentary
    improvement_advice = list(next_round)

    return {
        "overall_commentary": overall_commentary,
        "strengths": strengths,
        "weaknesses": weaknesses,
        "next_round_advice": next_round,
        "coach_commentary": coach_commentary,
        "improvement_advice": improvement_advice,
    }


def build_coach_output(
    *,
    scoring_profile: str | None = None,
    scoring_profile_label: str | None = None,
    score_explanations: dict[str, Any] | None = None,
    score_breakdown: dict[str, Any] | None = None,
    content_breakdown: dict[str, Any] | None = None,
    qa_breakdown: dict[str, Any] | None = None,
    qa_result: dict[str, Any] | None = None,
    content_document: dict[str, Any] | None = None,
    ppt_match: dict[str, Any] | None = None,
    ppt_match_analysis: dict[str, Any] | None = None,
    total_score: float | None = None,
    audio_valid: bool | None = None,
    vision_valid: bool | None = None,
    ppt_match_source: str | None = None,
    qa_source: str | None = None,
) -> dict[str, Any]:
    """
    统一追问官 + 点评官输出。字段稳定，便于前端与后续 Agent 替换实现。
    """
    followup_questions = _build_followup_questions(
        qa_breakdown=qa_breakdown,
        qa_result=qa_result,
        content_breakdown=content_breakdown,
        content_document=content_document,
        ppt_match=ppt_match,
        ppt_match_analysis=ppt_match_analysis,
    )
    narrative = _build_coach_narrative(
        scoring_profile=scoring_profile,
        scoring_profile_label=scoring_profile_label,
        score_explanations=score_explanations,
        score_breakdown=score_breakdown,
        total_score=total_score,
        qa_breakdown=qa_breakdown,
        content_breakdown=content_breakdown,
        audio_valid=audio_valid,
        vision_valid=vision_valid,
        ppt_match_source=ppt_match_source,
        qa_source=qa_source,
    )
    coach_metadata = {
        "mode": str(scoring_profile or "defense"),
        "mode_label": str(scoring_profile_label or ""),
        "version": COACH_VERSION,
        "engine": "rule",
        "commentary_chain": "v1",
    }
    return {
        "followup_questions": followup_questions,
        "overall_commentary": narrative["overall_commentary"],
        "strengths": narrative["strengths"],
        "weaknesses": narrative["weaknesses"],
        "next_round_advice": narrative["next_round_advice"],
        "coach_commentary": narrative["coach_commentary"],
        "improvement_advice": narrative["improvement_advice"],
        "coach_metadata": coach_metadata,
    }
