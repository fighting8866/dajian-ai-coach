from abc import ABC, abstractmethod
from typing import Any


class PPTProvider(ABC):
    """PPT 解析与内容匹配（对应 `/api/ppt/*` 能力）。"""

    @abstractmethod
    def parse_ppt(self, file_path: str) -> list[dict]:
        """兼容旧流程：返回带 page_index / title / keywords 的页面列表。"""
        raise NotImplementedError

    @abstractmethod
    def extract_text_by_slide(self, file_path: str) -> dict[str, Any]:
        """全文 + 逐页文本（对应 `/api/ppt/parse`）。"""
        raise NotImplementedError

    @abstractmethod
    def match_page_content(self, page_info: dict, spoken_text: str) -> dict:
        """单页关键词匹配（对应 `/api/ppt/match`）。"""
        raise NotImplementedError

    @abstractmethod
    def match_transcript_with_ppt(self, transcript: str, full_text: str, slides: list) -> dict:
        """转写与整份 PPT 匹配（对应 `/api/ppt/match_v1`）。"""
        raise NotImplementedError
