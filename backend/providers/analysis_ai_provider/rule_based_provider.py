from providers.analysis_ai_provider.base import AnalysisAIProvider


class RuleBasedAnalysisProvider(AnalysisAIProvider):
    """默认分析提供者：规则实现（便于后续替换上板服务）。"""

    def generate_qa_question(self, page_info: dict) -> dict:
        title = (page_info.get("title") or "").strip()
        keywords = page_info.get("keywords") or []
        lower_title = title.lower()

        if "创新" in title or "innovation" in lower_title:
            question = "你的创新点是什么？"
        elif "系统架构" in title or "架构" in title or "architecture" in lower_title:
            question = "为什么这样设计系统架构？"
        elif "背景" in title or "background" in lower_title:
            question = "你们想解决什么问题？"
        else:
            question = "请概述这一页的核心内容"

        expected_keywords = keywords[:8] if keywords else ["核心思路", "关键方案", "实现效果"]
        return {
            "question": question,
            "expected_keywords": expected_keywords
        }

    def evaluate_qa_answer(self, question: str, expected_keywords: list, answer_text: str) -> dict:
        text = answer_text or ""
        expected = expected_keywords or []

        if not expected:
            coverage_score = 0.0
            hit_keywords = []
            missing_keywords = []
        else:
            hit_keywords = [k for k in expected if k and k in text]
            missing_keywords = [k for k in expected if k and k not in text]
            coverage_score = len(hit_keywords) / len(expected)

        is_relevant = coverage_score >= 0.3
        if coverage_score >= 0.75:
            comment = "回答较完整，切题且覆盖充分"
        elif coverage_score >= 0.4:
            comment = "回答基本切题，但仍缺少部分关键点"
        else:
            comment = "回答较空泛或偏题，建议围绕问题核心重新组织"

        return {
            "question": question,
            "expected_keywords": expected,
            "answer_text": text,
            "is_relevant": is_relevant,
            "coverage_score": round(coverage_score, 2),
            "hit_keywords": hit_keywords,
            "missing_keywords": missing_keywords,
            "comment": comment
        }

