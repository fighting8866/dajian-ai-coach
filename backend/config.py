"""
最小运行时配置（可通过环境变量覆盖）。

昇腾 / 开发板侧联调（详见 docs/ascend_deployment_v1.md）：
- 设置 ASCEND_BASE_URL 指向运行 ascend_service 的主机（如 http://192.168.1.10:18081）
- VISION_PROVIDER=ascend：视觉经主后端 AscendHttpGateway multipart 转发至板侧 /vision/analyze
- SPEECH_PROVIDER=ascend：语音**正式路径**为「前端 → 主后端 POST /api/audio/analyze → 网关 multipart → 板侧 /speech/analyze」；
  前端不直连开发板；未就绪或演示本机 ASR 时保持 SPEECH_PROVIDER=local
不改 /api 路径与 multipart 协议，仅切换 provider。
"""

import os
from pathlib import Path


def _load_backend_dotenv() -> None:
    """加载与 config.py 同目录下的 `.env`：仅当对应键尚未出现在 `os.environ` 时写入（进程环境优先）。"""
    try:
        path = Path(__file__).resolve().parent / ".env"
        if not path.is_file():
            return
        for raw in path.read_text(encoding="utf-8").splitlines():
            line = raw.strip()
            if not line or line.startswith("#"):
                continue
            if "=" not in line:
                continue
            key, _, val = line.partition("=")
            key = key.strip()
            if not key:
                continue
            val = val.strip()
            if len(val) >= 2 and val[0] == val[-1] and val[0] in "\"'":
                val = val[1:-1]
            if os.getenv(key) is None:
                os.environ[key] = val
    except OSError:
        pass


_load_backend_dotenv()


def _env(name: str, default: str) -> str:
    v = os.getenv(name)
    if v is None or str(v).strip() == "":
        return default
    return str(v).strip()


def _env_float(name: str, default: float) -> float:
    v = os.getenv(name)
    if v is None or str(v).strip() == "":
        return float(default)
    try:
        return float(str(v).strip())
    except ValueError:
        return float(default)


def _env_int(name: str, default: int) -> int:
    v = os.getenv(name)
    if v is None or str(v).strip() == "":
        return int(default)
    try:
        return int(str(v).strip())
    except ValueError:
        return int(default)


class Settings:
    """主后端运行时配置；昇腾联调项见下（完整说明 docs/ascend_deployment_v1.md）。"""

    # --- 音视频 AI：local=本机；ascend=经 AscendHttpGateway multipart 转发至 ascend_service（协议不变）---
    SPEECH_PROVIDER = _env("SPEECH_PROVIDER", "local")
    VISION_PROVIDER = _env("VISION_PROVIDER", "local")
    PPT_PROVIDER = _env("PPT_PROVIDER", "local")
    QA_PROVIDER = _env("QA_PROVIDER", "local")
    # 文档解析（与开发板无关；供 /health、provider-status 汇总）
    DOCUMENT_PARSER_PROVIDER = _env("DOCUMENT_PARSER_PROVIDER", "basic")

    # --- 认知生成骨架（老师提问 / 追问 / 点评）：与 QA_PROVIDER 独立；默认 rule，model/hybrid 供后续 LLM 或 GitHub 开源方案接入 ---
    QUESTION_PROVIDER = _env("QUESTION_PROVIDER", "rule")
    # 首问模型后端（仅当 QUESTION_PROVIDER=model|hybrid 时有意义；当前 model 为占位骨架）
    QUESTION_MODEL_BACKEND = _env("QUESTION_MODEL_BACKEND", "mock")
    QUESTION_MODEL_TIMEOUT_SECONDS = _env_float("QUESTION_MODEL_TIMEOUT_SECONDS", 30)
    # 老师追问：rule=现有规则 V2；model=结构化上下文 + LLM（见 FOLLOWUP_MODEL_*）；hybrid=先走 model 路径，失败或校验不过再 rule
    FOLLOWUP_PROVIDER = _env("FOLLOWUP_PROVIDER", "rule")
    # 追问模型后端（仅当 FOLLOWUP_PROVIDER=model|hybrid 时生效；工厂层另认 openai|http_post 为 OpenAI 兼容别名）：
    # - mock：无 HTTP，本地可读占位追问（默认，安全主流程）
    # - qwen | custom：POST OpenAI 兼容 Chat Completions（`{BASE}/v1/chat/completions`，BASE 可已含 /v1 或已以 /chat/completions 结尾）
    # BASE_URL 示例：
    # - 本地 Ollama：`http://127.0.0.1:11434/v1`
    # - vLLM：`http://127.0.0.1:8000/v1`
    # - 阿里云 DashScope 兼容：`https://dashscope.aliyuncs.com/compatible-mode/v1`（需 FOLLOWUP_MODEL_API_KEY + FOLLOWUP_MODEL_NAME，如 qwen-turbo）
    FOLLOWUP_MODEL_BACKEND = _env("FOLLOWUP_MODEL_BACKEND", "mock")
    FOLLOWUP_MODEL_BASE_URL = _env("FOLLOWUP_MODEL_BASE_URL", "")
    # 可选：Authorization Bearer；本地无鉴权可留空
    FOLLOWUP_MODEL_API_KEY = _env("FOLLOWUP_MODEL_API_KEY", "")
    # Chat Completions 请求体中的 model；空则按 backend 默认（qwen→qwen-turbo，其余→gpt-3.5-turbo）
    FOLLOWUP_MODEL_NAME = _env("FOLLOWUP_MODEL_NAME", "")
    FOLLOWUP_MODEL_TIMEOUT_SECONDS = _env_float("FOLLOWUP_MODEL_TIMEOUT_SECONDS", 30)
    # 老师点评：rule=现有规则链；model=占位/后续模型；hybrid=先模型后规则回退
    COMMENTARY_PROVIDER = _env("COMMENTARY_PROVIDER", "rule")
    COMMENTARY_MODEL_BACKEND = _env("COMMENTARY_MODEL_BACKEND", "mock")
    COMMENTARY_MODEL_TIMEOUT_SECONDS = _env_float("COMMENTARY_MODEL_TIMEOUT_SECONDS", 45)

    # ASCEND_BASE_URL：ascend_service 根地址，无尾斜杠，例 http://192.168.1.10:18081
    # 为空时 SPEECH_PROVIDER/VISION_PROVIDER=ascend 会在网关层报「未配置开发板地址」
    ASCEND_BASE_URL = _env("ASCEND_BASE_URL", "")

    # ASCEND_TIMEOUT_SECONDS：网关 JSON 类请求（若有）及未单独指定时的通用超时（秒）
    ASCEND_TIMEOUT_SECONDS = _env_float("ASCEND_TIMEOUT_SECONDS", 20)
    # ASCEND_SPEECH_TIMEOUT_SECONDS：multipart 上传语音分析超时（长时答辩 V2 第一阶段默认放宽，避免 ~1min 音频被网关掐断）
    ASCEND_SPEECH_TIMEOUT_SECONDS = _env_float("ASCEND_SPEECH_TIMEOUT_SECONDS", 120)
    # ASCEND_VISION_TIMEOUT_SECONDS：主后端 → 板侧 multipart 的**整段**超时（urllib 一次请求含：本机读盘组包、
    # 发送至板、板侧解码+推理、回包）。直打板子只含后两段，故经主后端更容易触达上限；长视频或弱网建议 300s+。
    ASCEND_VISION_TIMEOUT_SECONDS = _env_float("ASCEND_VISION_TIMEOUT_SECONDS", 300)

    # --- 长时答辩 V2 第一阶段（板侧 ascend_service 读同名环境变量；此处默认值与文档对齐，便于本机/脚本 export）---
    # 固定窗口分段 ASR：15~20s 为宜；过短则窗数多、边界多，过长则单窗 ASR 慢
    AUDIO_CHUNK_SECONDS = _env_float("AUDIO_CHUNK_SECONDS", 15.0)
    AUDIO_CHUNK_OVERLAP_SECONDS = _env_float("AUDIO_CHUNK_OVERLAP_SECONDS", 1.0)
    # 视觉采样：1~2 fps 可将 3min+ 视频控制在有限次 MediaPipe 调用；帧数上限防止极端 fps 或长片
    VISION_TARGET_ANALYSIS_FPS = _env_float("VISION_TARGET_ANALYSIS_FPS", 1.0)
    VISION_MAX_ANALYSIS_FRAMES = _env_int("VISION_MAX_ANALYSIS_FRAMES", 240)

    # ASCEND_SPEECH_ENDPOINT / ASCEND_VISION_ENDPOINT：板侧路径，须与 ascend_service 路由一致
    ASCEND_SPEECH_ENDPOINT = _env("ASCEND_SPEECH_ENDPOINT", "/speech/analyze")
    ASCEND_VISION_ENDPOINT = _env("ASCEND_VISION_ENDPOINT", "/vision/analyze")

    # --- 轻量登录 V1：生产环境务必设置 JWT_SECRET ---
    JWT_SECRET = _env("JWT_SECRET", "dajian-dev-jwt-secret-change-me")
    JWT_EXPIRE_DAYS = _env_int("JWT_EXPIRE_DAYS", 7)


settings = Settings()
