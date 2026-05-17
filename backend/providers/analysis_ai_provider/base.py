from abc import ABC, abstractmethod


class AnalysisAIProvider(ABC):
    """分析 AI 提供者抽象：负责问答生成与评估。"""

    @abstractmethod
    def generate_qa_question(self, page_info: dict) -> dict:
        raise NotImplementedError

    @abstractmethod
    def evaluate_qa_answer(self, question: str, expected_keywords: list, answer_text: str) -> dict:
        raise NotImplementedError

