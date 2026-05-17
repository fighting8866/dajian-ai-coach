from __future__ import annotations

from adapters.ascend_request_adapter import build_vision_analyze_request
from adapters.ascend_response_adapter import adapt_vision_response_to_internal
from gateways.ascend_gateway.base import AscendGatewayConfigError, AscendGatewayRequestError
from gateways.ascend_gateway.http_gateway import AscendHttpGateway
from providers.vision_ai_provider.base import VisionAIProvider


class AscendVisionAIProvider(VisionAIProvider):
    """Ascend vision provider: forwards video analyze requests to ascend_service (multipart)."""

    def __init__(self, gateway: AscendHttpGateway | None = None) -> None:
        self.gateway = gateway or AscendHttpGateway()

    def analyze_video(self, video_path: str) -> dict:
        endpoint = getattr(self.gateway, "vision_endpoint", "")
        base_url = getattr(self.gateway, "base_url", "")
        final_url = f"{str(base_url).rstrip('/')}{endpoint}" if base_url and endpoint else ""
        req = build_vision_analyze_request(video_path=video_path)
        print(
            "[ascend.trace] vision BEGIN route=ascend provider_class=AscendVisionAIProvider "
            f"request_id={req.request_id} endpoint={endpoint} board_url={final_url!r} "
            f"transport=multipart/form-data local_file={video_path!r}"
        )
        try:
            resp = self.gateway.send_vision_request(req)
        except AscendGatewayConfigError as exc:
            print(
                f"[ascend.trace] vision END route=ascend request_id={req.request_id} "
                f"endpoint={endpoint} success=false error=config detail={str(exc)[:200]!r}"
            )
            raise RuntimeError("当前未配置开发板服务地址") from exc
        except AscendGatewayRequestError as exc:
            print(
                f"[ascend.trace] vision END route=ascend request_id={req.request_id} "
                f"endpoint={endpoint} success=false error=request detail={str(exc)[:200]!r}"
            )
            raise RuntimeError(f"开发板视觉分析失败: {exc}") from exc

        if not resp.success:
            print(
                f"[ascend.trace] vision END route=ascend request_id={resp.request_id} "
                f"endpoint={endpoint} success=false board_provider={resp.provider!r} "
                f"error={resp.error!r}"
            )
            raise RuntimeError(resp.error or "开发板视觉分析失败")

        adapted = adapt_vision_response_to_internal(resp)
        print(
            f"[ascend.trace] vision END route=ascend request_id={resp.request_id} "
            f"endpoint={endpoint} success=true board_provider={resp.provider!r}"
        )
        return adapted
