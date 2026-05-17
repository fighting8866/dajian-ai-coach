from abc import ABC, abstractmethod


class SpeechAIProvider(ABC):
    """语音 AI 提供者：底层转写 + 完整音频分析（与 `/api/audio/analyze` 对齐）。"""

    @abstractmethod
    def transcribe(self, wav_path: str, *, initial_prompt: str = "") -> str:
        """将标准化 wav 音频转为文本。"""
        raise NotImplementedError

    @abstractmethod
    def analyze_audio(self, audio_path: str, *, analysis_phase: str = "lecture") -> dict:
        """完整链路：标准化、有效语音判定、转写、语速/停顿等指标；供 HTTP 层直接调用。"""
        raise NotImplementedError

