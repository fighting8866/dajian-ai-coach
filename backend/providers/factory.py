"""
兼容入口：请优先使用 `factories.provider_factory`。

保留本模块 re-export，避免历史 `from providers.factory import ...` 报错。
"""

from factories.provider_factory import (
    get_analysis_ai_provider,
    get_ppt_provider,
    get_qa_provider,
    get_speech_ai_provider,
    get_vision_ai_provider,
)

__all__ = [
    "get_speech_ai_provider",
    "get_vision_ai_provider",
    "get_ppt_provider",
    "get_qa_provider",
    "get_analysis_ai_provider",
]
