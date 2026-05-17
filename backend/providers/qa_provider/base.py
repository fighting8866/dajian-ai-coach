from abc import ABC, abstractmethod


class QAProvider(ABC):
    """问答生成与评估（对应 `/api/qa/*`）。"""

    @abstractmethod
    def generate_question(self, page_info: dict) -> dict:
        raise NotImplementedError

    @abstractmethod
    def evaluate_answer(
        self,
        question: str,
        expected_keywords: list[str],
        answer_text: str,
    ) -> dict:
        raise NotImplementedError
