# API 模块初始化文件
# 显式导入子模块，避免导入链导致路由未加载
from . import session, result, ppt, qa, report, audio, vision  # noqa: F401

__all__ = ["session", "result", "ppt", "qa", "report", "audio", "vision"]