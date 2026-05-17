"""追问条目校验与字段补齐（多 provider 共用）。"""

from __future__ import annotations

import re
from typing import Any

FOLLOWUP_ITEM_VERSION = "v1"

_ITEM_LABELS = {
    "rule": "规则追问",
    "model": "模型追问",
    "hybrid": "混合追问",
}

_Q_META_MARKERS = (
    "json数组",
    "json 数组",
    "json array",
    "```json",
    "```",
    "返回仅",
    "只输出json",
    "输出格式",
    "作为人工智能",
    "我是ai",
    "i'm sorry",
    "sorry,",
    "i cannot",
    "cannot answer",
    "here are",
    "以下是",
    "如下所示",
    "综上所述",
    "总的来说",
    "基于以上材料",
    "根据上述材料",
    "希望对你有帮助",
    "如果您还有其他问题",
)

# 整段像作文/综述而非现场追问
_QUESTION_FLUFF_SNIPPETS = (
    "综上所述",
    "总的来说",
    "以上是",
    "基于以上分析",
    "根据您的描述",
    "作为一名人工智能",
    "希望对你有帮助",
    "值得一提的是",
    "不难发现",
    "需要注意的是",
    "首先，",
    "其次，",
    "最后，",
    "总而言之",
    "简要来说",
)


def _followup_question_dedupe_key(q: str) -> str:
    return re.sub(r"\s+", "", (q or "").strip().lower())


def followup_item_quality_score(item: dict[str, Any] | Any) -> float:
    """
    0～1 粗分，用于在 prepare 阶段优先保留更「可追问」的条目（非评分业务主链路）。
    """
    if not isinstance(item, dict):
        return 0.0
    q = str(item.get("question") or "").strip()
    rsn = str(item.get("reason") or "").strip()
    topic = str(item.get("target_topic") or "").strip()
    s = 0.45
    ln = len(q)
    if 10 <= ln <= 160:
        s += 0.15
    elif 160 < ln <= 220:
        s += 0.08
    if "？" in q or "?" in q or "吗" in q or "呢" in q:
        s += 0.12
    if _has_interrogative_tone(q):
        s += 0.1
    if len(rsn) >= 10:
        s += 0.1
    if topic and len(topic) >= 2:
        s += 0.08
    return min(1.0, s)


def followup_list_mean_quality_score(items: list[Any]) -> float:
    if not items:
        return 0.0
    xs = [followup_item_quality_score(x) for x in items if isinstance(x, dict)]
    if not xs:
        return 0.0
    return sum(xs) / max(len(xs), 1)


def _is_valid_followup_reason(reason: str) -> bool:
    r = (reason or "").strip()
    if len(r) < 4:
        return False
    if len(r) > 520:
        return False
    low = r.lower()
    for m in _Q_META_MARKERS:
        if m.lower() in low:
            return False
    return True


def _cjk_char_count(q: str) -> int:
    return sum(1 for c in q if "\u4e00" <= c <= "\u9fff")


def _bigrams(s: str) -> set[str]:
    t = re.sub(r"\s+", "", (s or "").strip().lower())
    if len(t) < 2:
        return {t} if t else set()
    return {t[i : i + 2] for i in range(len(t) - 1)}


def _has_interrogative_tone(q: str) -> bool:
    """短中句追问：应有明显问句/追问语气，减少说明文体。"""
    return any(
        x in q
        for x in (
            "？",
            "?",
            "吗",
            "呢",
            "么",
            "哪",
            "哪些",
            "谁",
            "何时",
            "何处",
            "可否",
            "好不好",
            "行不行",
            "为啥",
            "为什么",
            "怎么",
            "如何",
            "能否",
            "是否",
        )
    )


def _followup_questions_too_similar(a: str, b: str) -> bool:
    """近似重复：包含关系或 bigram Jaccard 过高（模型常吐多条换皮同义句）。"""
    ka = _followup_question_dedupe_key(a)
    kb = _followup_question_dedupe_key(b)
    if not ka or not kb:
        return False
    if ka == kb:
        return True
    short, long = (ka, kb) if len(ka) <= len(kb) else (kb, ka)
    if len(short) >= 12 and short in long:
        return True
    ba, bb = _bigrams(ka), _bigrams(kb)
    if not ba or not bb:
        return False
    inter = len(ba & bb)
    union = len(ba | bb)
    if union <= 0:
        return False
    return (inter / union) >= 0.78


def _is_valid_followup_question_text(q: str) -> bool:
    """单条题干：长度、去噪、防整段废话 / 复述指令 / 非中文噪声。"""
    q = (q or "").strip()
    ln = len(q)
    if ln < 8 or ln > 400:
        return False
    low = q.lower()
    for m in _Q_META_MARKERS:
        if m.lower() in low:
            return False
    for f in _QUESTION_FLUFF_SNIPPETS:
        if f.lower() in low:
            return False
    # 过长且无问号：更像说明文而非追问
    if ln > 120 and "？" not in q and "?" not in q:
        return False
    # 中短句：要求明显追问语气（ hybrid 校验失败则回退 rule）
    if ln <= 200 and not _has_interrogative_tone(q):
        return False
    qmarks = q.count("？") + q.count("?")
    if qmarks > 4:
        return False
    # 答辩场景：偏长文本应含一定比例汉字，避免模型英文废话填充
    if ln >= 24:
        cjk = _cjk_char_count(q)
        if cjk / ln < 0.18:
            return False
    # 单字重复占比过高
    if ln >= 16:
        mc = max(q.count(c) for c in set(q))
        if mc / ln > 0.42:
            return False
    # 枚举式罗列（多轮数字/字母序号），更像提纲不像追问
    if sum(1 for x in ("1.", "2.", "3.", "（1）", "(1)", "①", "②") if x in q) >= 2:
        return False
    # 标点 / 空白占比过高
    non_word = sum(1 for c in q if c.isspace() or c in "，。、；：""''（）()[]【】《》…—·")
    if non_word / max(ln, 1) > 0.55:
        return False
    # 过短且缺少实质字符（全标点或数字）
    alnum_cjk = sum(1 for c in q if c.isalnum() or ("\u4e00" <= c <= "\u9fff"))
    if alnum_cjk < 6:
        return False
    return True


def followup_items_valid(items: list[Any]) -> bool:
    """至少 1 条有效追问；去重/防近似同义/防 reason 全同；结构校验。返回 False 时 hybrid 应回退 rule。"""
    if not items or not isinstance(items, list):
        return False
    if len(items) > 3:
        return False
    seen: set[str] = set()
    reason_seen: set[str] = set()
    questions: list[str] = []
    for it in items:
        if not isinstance(it, dict):
            return False
        q = str(it.get("question") or "").strip()
        if not q:
            return False
        if not _is_valid_followup_question_text(q):
            return False
        rsn = str(it.get("reason") or "").strip()
        if not _is_valid_followup_reason(rsn):
            return False
        rk = _followup_question_dedupe_key(rsn)
        if len(rk) >= 4 and rk in reason_seen:
            return False
        reason_seen.add(rk)
        k = _followup_question_dedupe_key(q)
        if not k or k in seen:
            return False
        for prev in questions:
            if _followup_questions_too_similar(prev, q):
                return False
        seen.add(k)
        questions.append(q)
    return len(seen) >= 1


def prepare_model_followup_raw_items(
    raw: list[Any],
    *,
    max_items: int = 3,
) -> list[dict[str, Any]] | None:
    """
    解析模型 JSON 数组：先按质量分排序、再过滤/去重/防近似同义/截断与补齐，优先保留更「可追问」的条。
    若无任何有效条目则返回 None（调用方应视为模型输出不合格）。
    """
    if not isinstance(raw, list) or not raw:
        return None
    nmax = max(1, min(int(max_items or 3), 3))
    # 可评分的 dict 先行排序，少依赖模型输出顺序
    dict_rows = [x for x in raw if isinstance(x, dict)]
    other_order = [i for i, x in enumerate(raw) if not isinstance(x, dict)]
    dict_rows.sort(key=lambda d: followup_item_quality_score(d), reverse=True)
    raw_ordered = dict_rows + [raw[i] for i in other_order]

    seen: set[str] = set()
    reason_seen: set[str] = set()
    out: list[dict[str, Any]] = []
    for it in raw_ordered:
        if not isinstance(it, dict):
            continue
        q = str(it.get("question") or "").strip()
        if not _is_valid_followup_question_text(q):
            continue
        k = _followup_question_dedupe_key(q)
        if k in seen:
            continue
        reason = str(it.get("reason") or "").strip()[:500]
        if not _is_valid_followup_reason(reason):
            reason = "由模型基于答题弱点生成。"
        rk = _followup_question_dedupe_key(reason)
        if len(rk) >= 4 and rk in reason_seen:
            continue
        src = str(it.get("source") or "qa_weak_point").strip() or "qa_weak_point"
        topic = str(it.get("target_topic") or "").strip()[:120]
        if any(_followup_questions_too_similar(p.get("question") or "", q) for p in out):
            continue
        seen.add(k)
        reason_seen.add(rk)
        out.append(
            {
                "question": q[:400],
                "reason": reason,
                "source": src,
                "target_topic": topic,
            }
        )
        if len(out) >= nmax:
            break
    if len(out) < 1:
        return None
    return out


def enrich_followup_item(
    item: dict[str, Any],
    *,
    provider_kind: str,
    generation_mode: str,
    version: str = FOLLOWUP_ITEM_VERSION,
) -> dict[str, Any]:
    pk = (provider_kind or "rule").strip().lower()
    if pk not in ("rule", "model", "hybrid"):
        pk = "rule"
    out = dict(item)
    out["question"] = str(out.get("question") or "").strip()[:400]
    out["reason"] = str(out.get("reason") or "").strip()[:500]
    out["source"] = str(out.get("source") or "qa_weak_point").strip()
    out["target_topic"] = str(out.get("target_topic") or "").strip()[:120]
    out["provider_kind"] = pk
    out["provider_label"] = _ITEM_LABELS.get(pk, pk)
    out["generation_mode"] = generation_mode
    out["version"] = version
    return out


def enrich_followup_item_list(
    items: list[dict[str, Any]],
    *,
    provider_kind: str,
    generation_mode: str,
    version: str = FOLLOWUP_ITEM_VERSION,
) -> list[dict[str, Any]]:
    return [
        enrich_followup_item(x, provider_kind=provider_kind, generation_mode=generation_mode, version=version)
        for x in items
    ]
