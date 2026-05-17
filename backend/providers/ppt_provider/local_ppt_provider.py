from typing import Any

from providers.ppt_provider.base import PPTProvider
from services.ppt_match_service import PPTMatchService
from services.ppt_service import PPTService

# 注意：`ppt_id` 由 `api/ppt.py` 的 `/upload` 生成并写入 `ppt_store`；本层只做解析/匹配，不生成业务 ID。


class LocalPPTProvider(PPTProvider):
    """本地实现：委托 `PPTService` 与 `PPTMatchService`。"""

    def __init__(self) -> None:
        self._ppt = PPTService()
        self._match = PPTMatchService()

    def parse_ppt(self, file_path: str) -> list[dict]:
        return self._ppt.parse_ppt(file_path)

    def extract_text_by_slide(self, file_path: str) -> dict[str, Any]:
        return self._ppt.extract_text_by_slide(file_path)

    def match_page_content(self, page_info: dict, spoken_text: str) -> dict:
        return self._match.match_page_content(page_info, spoken_text)

    def match_transcript_with_ppt(self, transcript: str, full_text: str, slides: list) -> dict:
        return self._match.match_transcript_with_ppt(
            transcript=transcript,
            full_text=full_text,
            slides=slides,
        )
