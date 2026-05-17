from providers.analysis_ai_provider.rule_based_provider import RuleBasedAnalysisProvider
from providers.qa_provider.base import QAProvider


class LocalRuleQAProvider(QAProvider):
    """本地规则问答：复用现有 `RuleBasedAnalysisProvider` 逻辑。"""

    def __init__(self) -> None:
        self._inner = RuleBasedAnalysisProvider()

    def generate_question(self, page_info: dict) -> dict:
        return self._inner.generate_qa_question(page_info)

    def evaluate_answer(
        self,
        question: str,
        expected_keywords: list[str],
        answer_text: str,
    ) -> dict:
        return self._inner.evaluate_qa_answer(question, expected_keywords, answer_text)
