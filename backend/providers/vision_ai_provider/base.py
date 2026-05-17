from abc import ABC, abstractmethod


class VisionAIProvider(ABC):
    """视觉 AI 提供者：视频/图像仪态、视线等分析（与路由 `/api/vision/analyze` 对应）。"""

    @abstractmethod
    def analyze_video(self, video_path: str) -> dict:
        """分析已落盘的视频文件，返回结构化指标（具体字段由实现约定）。"""
        raise NotImplementedError
