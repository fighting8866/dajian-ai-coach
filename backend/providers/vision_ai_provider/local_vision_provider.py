from providers.vision_ai_provider.base import VisionAIProvider
from services.vision_service import VisionService


class LocalVisionAIProvider(VisionAIProvider):
    """本地视觉实现：调用 `VisionService` 完成离线视频分析。"""

    def __init__(self) -> None:
        self._svc = VisionService()

    def analyze_video(self, video_path: str) -> dict:
        try:
            return self._svc.analyze_video(video_path)
        except Exception as e:
            raise RuntimeError(f"本地视觉分析失败: {repr(e)}") from e
