from fastapi import FastAPI

from ascend_service.api.health import router as health_router
from ascend_service.api.speech import router as speech_router
from ascend_service.api.vision import router as vision_router

app = FastAPI(title="Ascend Service", version="v1")

app.include_router(health_router)
app.include_router(speech_router)
app.include_router(vision_router)


def _vision_backend_tag() -> str:
    try:
        import mediapipe  # noqa: F401

        return "mediapipe"
    except ImportError:
        return "haar-fallback"


@app.on_event("startup")
def log_startup_version() -> None:
    # 与 vision_service 是否可用 mp 一致，便于板侧日志一眼区分
    print(f"ascend_service vision_backend={_vision_backend_tag()}", flush=True)
