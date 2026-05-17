from __future__ import annotations

import re
from typing import Any

from factories.provider_factory import get_qa_provider

_FILLER_RE = re.compile(r"(嗯|啊|那个|就是|然后|呃|这个|反正|怎么说呢|其实)")


def _coverage_as_ratio(raw: Any) -> float:
    try:
        v = float(raw or 0.0)
    except (TypeError, ValueError):
        return 0.0
    if v > 1.0:
        return max(0.0, min(1.0, v / 100.0))
    return max(0.0, min(1.0, v))


def _information_level_from_length(answer_len: int) -> float:
    if answer_len >= 220:
        return 90.0
    if answer_len >= 140:
        return 80.0
    if answer_len >= 90:
        return 68.0
    if answer_len >= 50:
        return 55.0
    if answer_len >= 25:
        return 42.0
    if answer_len > 0:
        return 28.0
    return 5.0


def _length_score_from_chars(answer_len: int) -> float:
    """0–100：回答长度是否足以支撑说明（规则近似）。"""
    if answer_len >= 180:
        return 92.0
    if answer_len >= 120:
        return 82.0
    if answer_len >= 70:
        return 68.0
    if answer_len >= 40:
        return 52.0
    if answer_len >= 15:
        return 35.0
    if answer_len > 0:
        return 18.0
    return 0.0


def _keyword_density_hits_per_100(hit_count: int, answer_len: int) -> float:
    if answer_len <= 0:
        return 0.0
    return round(float(hit_count) / float(answer_len) * 100.0, 4)


def _clarity_rule_score(answer_text: str, comment: str) -> float:
    """0–100：句长、分段、口头禅密度等规则近似（非 NLP 模型）。"""
    text = (answer_text or "").strip()
    if not text:
        return 5.0
    base = 68.0
    parts = re.split(r"[。！？!?\n;；]+", text)
    sentences = [p.strip() for p in parts if p.strip()]
    sc = len(sentences)
    if len(text) > 80 and sc < 2:
        base -= 14.0
    elif sc >= 3:
        base += 6.0
    fillers = len(_FILLER_RE.findall(text))
    if fillers >= 6:
        base -= 12.0
    elif fillers >= 3:
        base -= 6.0
    avg_seg = len(text) / max(sc, 1)
    if avg_seg > 120:
        base -= 8.0
    c = (comment or "").strip()
    if any(x in c for x in ("偏题", "空泛", "缺少", "不足")):
        base -= 5.0
    return max(8.0, min(100.0, base))


def _relevance_reason_text(is_relevant: bool, coverage_ratio: float, answer_len: int) -> str:
    pct = coverage_ratio * 100.0
    if answer_len <= 0:
        return "回答文本为空，无法判断与问题的实质关联。"
    if is_relevant:
        return f"参考关键词命中率约 {pct:.0f}%，达到规则切题阈值，且回答非空。"
    return f"参考关键词命中率约 {pct:.0f}%，未达到规则切题阈值或要点覆盖偏弱。"


def _rule_followup_topics(missing_keywords: list[str], question: str) -> list[str]:
    topics: list[str] = []
    for m in (missing_keywords or [])[:5]:
        if m:
            topics.append(f"可追问：请具体说明「{m}」")
    if not topics and (question or "").strip():
        topics.append("可追问：请结合问题中的核心概念补充一条论据或例子")
    return topics[:6]


def _rule_weak_points(
    is_relevant: bool,
    missing_keywords: list[str],
    answer_len: int,
    clarity: float,
) -> list[str]:
    weak: list[str] = []
    miss = [m for m in (missing_keywords or []) if m]
    if miss:
        head = "、".join(miss[:5])
        more = "…" if len(miss) > 5 else ""
        weak.append(f"未覆盖参考要点：{head}{more}")
    if answer_len < 30:
        weak.append("回答偏短，信息量可能不足")
    if not is_relevant:
        weak.append("切题度不足，建议先直接回应问题再展开细节")
    if clarity < 45:
        weak.append("表述结构偏松散，可减少口头禅并分句说明")
    return weak[:8] if weak else ["暂无额外规则弱项（后续可由 AI 点评官细化）"]


def compute_answer_length_score(answer_len: int) -> float:
    """对外暴露：回答长度折算分（0–100），供评分引擎在缺字段时回退。"""
    return round(_length_score_from_chars(int(answer_len)), 1)


def _mock_doc_from_pages(pages: list[dict]) -> dict[str, Any]:
    """无 document 时，由 upload 的 pages 构造最小结构供规则出题。"""
    outline: list[dict[str, Any]] = []
    doc_pages: list[dict[str, Any]] = []
    for p in pages or []:
        if not isinstance(p, dict):
            continue
        try:
            no = int(p.get("page_index") or len(doc_pages) + 1)
        except (TypeError, ValueError):
            no = len(doc_pages) + 1
        title = str(p.get("title") or "").strip() or f"第 {no} 页"
        kws = [str(k).strip() for k in (p.get("keywords") or []) if str(k).strip()]
        outline.append({"page_no": no, "title": title})
        doc_pages.append(
            {
                "page_no": no,
                "title": title,
                "plain_text": "",
                "keywords": kws,
                "top_keywords": kws[:8],
                "inferred_title": title,
            }
        )
    return {"outline": outline, "pages": doc_pages, "full_text": ""}


def generate_mock_questions(
    document: dict[str, Any] | None = None,
    count: int = 3,
    pages: list[dict] | None = None,
) -> list[dict[str, Any]]:
    """
    规则版模拟答辩问题（不接大模型）。优先使用 document 的标题、大纲、关键词与正文摘要。
    """
    n = max(1, min(int(count or 3), 12))
    doc = document if (document and isinstance(document, dict)) else None
    if doc is None and pages:
        doc = _mock_doc_from_pages(pages)
    if not doc:
        return []

    out: list[dict[str, str]] = []
    seen: set[str] = set()

    def push(q: str, source: str) -> None:
        key = re.sub(r"\s+", "", (q or "").strip())
        if len(key) < 6 or key in seen:
            return
        seen.add(key)
        out.append({"question": q.strip(), "source": source})

    for o in doc.get("outline") or []:
        if not isinstance(o, dict):
            continue
        t = str(o.get("title") or "").strip()
        if len(t) >= 2:
            push(f"大纲中「{t}」这一部分，主要结论与依据是什么？", "outline")

    for p in doc.get("pages") or []:
        if not isinstance(p, dict):
            continue
        title = str(p.get("inferred_title") or p.get("title") or "").strip()
        if len(title) >= 2:
            push(f"针对「{title}」，评审可能会质疑哪一点？你如何应对？", "title")
        for kw in (p.get("top_keywords") or p.get("keywords") or [])[:4]:
            k = str(kw).strip()
            if len(k) >= 2:
                push(f"请具体解释关键词「{k}」在本页中的作用与边界。", "keyword")
        plain = str(p.get("plain_text") or "").strip()
        if len(plain) >= 24:
            snippet = plain[:48].replace("\n", " ").strip()
            if snippet:
                push(f"材料提到「{snippet}…」，请补充其技术要点或实验/数据支撑。", "content")

    return out[:n]


def enrich_qa_evaluation(result: dict[str, Any], question: str = "") -> dict[str, Any]:
    """
    在 provider 输出上叠加 V1 规则字段；后续 Qwen-Agent / LangGraph 可写入
    followup_candidate_topics、weak_points 等覆盖本函数结果。
    """
    out = dict(result)
    text = str(out.get("answer_text") or "")
    q = str(question or out.get("question") or "")
    hit = list(out.get("hit_keywords") or [])
    miss = list(out.get("missing_keywords") or [])
    cov_r = _coverage_as_ratio(out.get("coverage_score"))
    out["coverage_score"] = round(cov_r, 4)

    alen = len(text)
    out["answer_length"] = alen
    out["answer_length_score"] = round(_length_score_from_chars(alen), 1)
    out["answer_keyword_density"] = _keyword_density_hits_per_100(len(hit), alen)
    out["answer_information_level"] = round(_information_level_from_length(alen), 1)

    ir = bool(out.get("is_relevant"))
    out["relevance_reason"] = _relevance_reason_text(ir, cov_r, alen)
    out["clarity_score"] = round(_clarity_rule_score(text, str(out.get("comment") or "")), 1)

    out["followup_candidate_topics"] = _rule_followup_topics(miss, q)
    out["weak_points"] = _rule_weak_points(ir, miss, alen, float(out["clarity_score"]))

    return out


class QAService:
    """问答服务（通过 QAProvider 抽象，便于后续上板替换）。"""

    def __init__(self):
        self.provider = get_qa_provider()

    def generate_question(self, page_info: dict) -> dict:
        return self.provider.generate_question(page_info)

    def evaluate_answer(self, question: str, expected_keywords: list, answer_text: str) -> dict:
        base = self.provider.evaluate_answer(question, expected_keywords, answer_text)
        return enrich_qa_evaluation(base, question)
