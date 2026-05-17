"""
统一 Provider 工厂：根据 `config.settings` 与环境变量选择实现。

兼容旧环境变量：
- SPEECH_AI_PROVIDER=local_whisper → 等价于 SPEECH_PROVIDER=local
- ANALYSIS_AI_PROVIDER=rule_based → 等价于 QA_PROVIDER=local
"""

from __future__ import annotations

import os
from functools import lru_cache

from config import settings
from providers.ppt_provider.base import PPTProvider
from providers.ppt_provider.local_ppt_provider import LocalPPTProvider
from providers.analysis_ai_provider.base import AnalysisAIProvider
from providers.analysis_ai_provider.rule_based_provider import RuleBasedAnalysisProvider
from providers.qa_provider.base import QAProvider
from providers.qa_provider.local_rule_qa_provider import LocalRuleQAProvider
from providers.speech_ai_provider.ascend_speech_provider import AscendSpeechAIProvider
from providers.speech_ai_provider.base import SpeechAIProvider
from providers.speech_ai_provider.local_whisper_provider import LocalWhisperSpeechProvider
from providers.vision_ai_provider.ascend_vision_provider import AscendVisionAIProvider
from providers.vision_ai_provider.base import VisionAIProvider
from providers.vision_ai_provider.local_vision_provider import LocalVisionAIProvider


def _speech_provider_kind() -> str:
    v = (os.getenv("SPEECH_PROVIDER") or "").strip().lower()
    if v:
        return v
    legacy = (os.getenv("SPEECH_AI_PROVIDER") or "local_whisper").strip().lower()
    if legacy == "local_whisper":
        return "local"
    return legacy if legacy in ("local", "ascend") else settings.SPEECH_PROVIDER.lower()


def _qa_provider_kind() -> str:
    v = (os.getenv("QA_PROVIDER") or "").strip().lower()
    if v:
        return v
    legacy = (os.getenv("ANALYSIS_AI_PROVIDER") or "rule_based").strip().lower()
    if legacy == "rule_based":
        return "local"
    return legacy if legacy in ("local", "ascend") else settings.QA_PROVIDER.lower()


def _vision_provider_kind() -> str:
    return (os.getenv("VISION_PROVIDER") or settings.VISION_PROVIDER).strip().lower()


def _ppt_provider_kind() -> str:
    return (os.getenv("PPT_PROVIDER") or settings.PPT_PROVIDER).strip().lower()


def get_document_parser_provider_kind() -> str:
    """文档解析增强线路：basic | markitdown | docling（后两者可渐进接入）。"""
    return (os.getenv("DOCUMENT_PARSER_PROVIDER") or settings.DOCUMENT_PARSER_PROVIDER).strip().lower()


def _normalize_cognitive_provider(kind: str, *, default: str = "rule") -> str:
    k = (kind or default).strip().lower()
    if k in ("rule", "model", "hybrid"):
        return k
    return default


def get_question_generation_provider_kind() -> str:
    """老师首问生成：rule（默认）| model（骨架）| hybrid（先模型占位，失败或不合法回退规则）。"""
    raw = (os.getenv("QUESTION_PROVIDER") or settings.QUESTION_PROVIDER or "rule").strip().lower()
    return _normalize_cognitive_provider(raw)


def get_question_model_backend() -> str:
    """首问模型后端：qwen | mock | custom（当前为占位，供后续接 GitHub 开源权重/服务）。"""
    raw = (
        os.getenv("QUESTION_MODEL_BACKEND") or getattr(settings, "QUESTION_MODEL_BACKEND", None) or "mock"
    ).strip().lower()
    if raw in ("qwen", "mock", "custom"):
        return raw
    return "mock"


def get_followup_generation_provider_kind() -> str:
    """老师追问生成：rule | model | hybrid（rule 为生产默认；model/hybrid 含占位与回退逻辑）。"""
    raw = (os.getenv("FOLLOWUP_PROVIDER") or settings.FOLLOWUP_PROVIDER or "rule").strip().lower()
    return _normalize_cognitive_provider(raw)


def get_followup_model_backend() -> str:
    """追问模型后端：mock | openai | qwen | custom（OpenAI 兼容 Chat Completions）| http_post（自定义 POST JSON）。"""
    raw = (
        os.getenv("FOLLOWUP_MODEL_BACKEND") or getattr(settings, "FOLLOWUP_MODEL_BACKEND", None) or "mock"
    ).strip().lower()
    if raw in ("http", "http_json"):
        raw = "http_post"
    allowed = ("mock", "qwen", "custom", "openai", "http_post","remote_ollama")
    if raw in allowed:
        return raw
    return "mock"


def get_commentary_generation_provider_kind() -> str:
    """老师点评生成：rule | model | hybrid（rule 默认；model/hybrid 含占位与回退）。"""
    raw = (os.getenv("COMMENTARY_PROVIDER") or settings.COMMENTARY_PROVIDER or "rule").strip().lower()
    return _normalize_cognitive_provider(raw)


def get_commentary_model_backend() -> str:
    """点评模型后端：qwen | mock | custom（当前为占位改写，供后续接开源模型）。"""
    raw = (
        os.getenv("COMMENTARY_MODEL_BACKEND") or getattr(settings, "COMMENTARY_MODEL_BACKEND", None) or "mock"
    ).strip().lower()
    if raw in ("qwen", "mock", "custom"):
        return raw
    return "mock"


def get_ai_provider_status() -> dict:
    """
    统一 provider 状态汇总（比赛自检 /health、GET /api/system/provider-status）。
    不含密钥；含 document_parser_provider 便于与文档理解配置一并确认。
    """
    speech = _speech_provider_kind()
    vision = _vision_provider_kind()
    base = (settings.ASCEND_BASE_URL or "").strip().rstrip("/")
    speech_ep = (settings.ASCEND_SPEECH_ENDPOINT or "").strip() or "/speech/analyze"
    vision_ep = (settings.ASCEND_VISION_ENDPOINT or "").strip() or "/vision/analyze"
    if speech_ep and not speech_ep.startswith("/"):
        speech_ep = f"/{speech_ep}"
    if vision_ep and not vision_ep.startswith("/"):
        vision_ep = f"/{vision_ep}"
    speech_url = f"{base}{speech_ep}" if base else None
    vision_url = f"{base}{vision_ep}" if base else None
    speech_t = float(getattr(settings, "ASCEND_SPEECH_TIMEOUT_SECONDS", settings.ASCEND_TIMEOUT_SECONDS))
    vision_t = float(getattr(settings, "ASCEND_VISION_TIMEOUT_SECONDS", settings.ASCEND_TIMEOUT_SECONDS))
    generic_t = float(settings.ASCEND_TIMEOUT_SECONDS)
    speech_inference_backend = "ascend_service" if speech == "ascend" else "local_whisper"
    speech_ascend_url_ready = bool(base) if speech == "ascend" else True
    return {
        "speech_provider": speech,
        "vision_provider": vision,
        # 语音实际推理落点（与 speech_provider 一致；供 provider-status / 演示说明，不改变协议）
        "speech_inference_backend": speech_inference_backend,
        # ascend 模式下是否已配置板址（未配置时网关无法出站，与 ascend_base_url_configured 在 ascend 时同义）
        "speech_ascend_url_ready": speech_ascend_url_ready,
        "document_parser_provider": get_document_parser_provider_kind(),
        "ascend_base_url": base or None,
        "ascend_base_url_configured": bool(base),
        "speech_endpoint": speech_ep,
        "vision_endpoint": vision_ep,
        "speech_full_url_hint": speech_url,
        "vision_full_url_hint": vision_url,
        "ascend_speech_timeout_seconds": speech_t,
        "ascend_vision_timeout_seconds": vision_t,
        "ascend_generic_timeout_seconds": generic_t,
        "recommended_board_module": "vision",
        "recommended_board_module_note": "比赛展示优先让视觉分析走 ascend_service；语音正式链路同为「主后端 → ascend_service」，可按 SPEECH_PROVIDER 切换 local",
        "question_generation_provider": get_question_generation_provider_kind(),
        "question_model_backend": get_question_model_backend(),
        "followup_generation_provider": get_followup_generation_provider_kind(),
        "followup_model_backend": get_followup_model_backend(),
        "commentary_generation_provider": get_commentary_generation_provider_kind(),
        "commentary_model_backend": get_commentary_model_backend(),
    }


def get_document_understanding_service():
    """统一文档理解服务（PPT/PDF/图片占位），供调试接口与 PPT 解析增强复用。"""
    from services.document_understanding_service import DocumentUnderstandingService

    return DocumentUnderstandingService(parser_provider=get_document_parser_provider_kind())


@lru_cache(maxsize=1)
def get_speech_ai_provider() -> SpeechAIProvider:
    kind = _speech_provider_kind()
    print(
        "[provider.factory] SPEECH_PROVIDER resolved: "
        f"kind={kind!r} ascend_base_url={(settings.ASCEND_BASE_URL or '')[:64]!r}"
    )
    if kind == "local":
        return LocalWhisperSpeechProvider()
    if kind == "ascend":
        return AscendSpeechAIProvider()
    raise ValueError(f"未知 SPEECH_PROVIDER / SPEECH_AI_PROVIDER: {kind!r}")


@lru_cache(maxsize=1)
def get_vision_ai_provider() -> VisionAIProvider:
    kind = _vision_provider_kind()
    print(
        "[provider.factory] VISION_PROVIDER resolved: "
        f"kind={kind!r} ascend_base_url={(settings.ASCEND_BASE_URL or '')[:64]!r}"
    )
    if kind == "local":
        return LocalVisionAIProvider()
    if kind == "ascend":
        return AscendVisionAIProvider()
    raise ValueError(f"未知 VISION_PROVIDER: {kind!r}")


@lru_cache(maxsize=1)
def get_ppt_provider() -> PPTProvider:
    kind = _ppt_provider_kind()
    if kind == "local":
        return LocalPPTProvider()
    if kind == "ascend":
        raise NotImplementedError(
            "PPT_PROVIDER=ascend 尚未实现，可接入远端解析/匹配服务"
        )
    raise ValueError(f"未知 PPT_PROVIDER: {kind!r}")


@lru_cache(maxsize=1)
def get_qa_provider() -> QAProvider:
    kind = _qa_provider_kind()
    if kind == "local":
        return LocalRuleQAProvider()
    if kind == "ascend":
        raise NotImplementedError(
            "QA_PROVIDER=ascend 尚未实现，请补充 AscendQAProvider"
        )
    raise ValueError(f"未知 QA_PROVIDER / ANALYSIS_AI_PROVIDER: {kind!r}")


# --- 兼容旧 `providers.factory` 中的命名（接口仍为 generate_qa_question / evaluate_qa_answer） ---


@lru_cache(maxsize=1)
def get_analysis_ai_provider() -> AnalysisAIProvider:
    """与历史代码兼容；与 `LocalRuleQAProvider` 共用同一套规则逻辑。"""
    return RuleBasedAnalysisProvider()
