from __future__ import annotations

from adapters.ascend_request_adapter import build_speech_analyze_request
from adapters.ascend_response_adapter import adapt_speech_response_to_internal
from gateways.ascend_gateway.base import AscendGatewayConfigError, AscendGatewayRequestError
from gateways.ascend_gateway.http_gateway import AscendHttpGateway
from providers.speech_ai_provider.base import SpeechAIProvider


class AscendSpeechAIProvider(SpeechAIProvider):
    """Ascend speech provider: forwards audio analyze requests to ascend_service (multipart)."""

    def __init__(self, gateway: AscendHttpGateway | None = None) -> None:
        self.gateway = gateway or AscendHttpGateway()

    def transcribe(self, wav_path: str, *, initial_prompt: str = "") -> str:
        _ = wav_path
        _ = initial_prompt
        raise NotImplementedError("AscendSpeechAIProvider 当前仅支持 analyze_audio，请走 /api/audio/analyze")

    def analyze_audio(self, audio_path: str, *, analysis_phase: str = "lecture") -> dict:
        endpoint = getattr(self.gateway, "speech_endpoint", "")
        base_url = getattr(self.gateway, "base_url", "")
        final_url = f"{str(base_url).rstrip('/')}{endpoint}" if base_url and endpoint else ""
        req = build_speech_analyze_request(audio_path=audio_path, analysis_phase=analysis_phase)
        print(
            "[ascend.trace] speech BEGIN route=main_backend->ascend_service "
            "provider_class=AscendSpeechAIProvider "
            f"request_id={req.request_id} endpoint={endpoint} board_url={final_url!r} "
            f"transport=multipart/form-data local_file={audio_path!r}"
        )
        try:
            resp = self.gateway.send_speech_request(req)
        except AscendGatewayConfigError as exc:
            print(
                f"[ascend.trace] speech END route=main_backend->ascend_service request_id={req.request_id} "
                f"endpoint={endpoint} success=false error=config detail={str(exc)[:200]!r}"
            )
            raise RuntimeError("当前未配置开发板服务地址") from exc
        except AscendGatewayRequestError as exc:
            msg = str(exc)
            print(
                f"[ascend.trace] speech END route=main_backend->ascend_service request_id={req.request_id} "
                f"endpoint={endpoint} success=false error=request detail={msg[:200]!r}"
            )
            if "请求超时" in msg or "timeout=" in msg.lower():
                degraded = {
                    "transcript": "",
                    "speech_rate": 0,
                    "pause_count": 0,
                    "avg_pause_sec": 0.0,
                    "filler_count": 0,
                    "audio_valid": False,
                    "audio_message": "语音分析超时，请缩短录音时长或稍后重试",
                    "provider": "ascend-timeout-degraded",
                    "request_id": req.request_id,
                    "audio_debug_provider": "ascend",
                    "audio_debug_request_id": req.request_id,
                    "audio_debug_error": msg,
                }
                print(
                    f"[ascend.trace] speech END route=main_backend->ascend_service request_id={req.request_id} "
                    f"endpoint={endpoint} success=false mode=timeout_degraded board_provider=n/a"
                )
                return degraded
            raise RuntimeError(f"开发板语音分析失败: {msg}") from exc

        if not resp.success:
            print(
                f"[ascend.trace] speech END route=main_backend->ascend_service request_id={resp.request_id} "
                f"endpoint={endpoint} success=false board_provider={resp.provider!r} "
                f"error={resp.error!r}"
            )
            raise RuntimeError(resp.error or "开发板语音分析失败")

        adapted = adapt_speech_response_to_internal(resp)
        print(
            f"[ascend.trace] speech END route=main_backend->ascend_service request_id={resp.request_id} "
            f"endpoint={endpoint} success=true board_provider={resp.provider!r}"
        )
        return adapted
