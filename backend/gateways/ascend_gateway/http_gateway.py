from __future__ import annotations

import json
import os
import socket
import uuid
from urllib import error, request

from config import settings
from gateways.ascend_gateway.base import (
    AscendGatewayConfigError,
    AscendGatewayRequestError,
    AscendGatewayResponse,
    AscendSpeechAnalyzeRequest,
    AscendVisionAnalyzeRequest,
    BaseAscendGateway,
)


class AscendHttpGateway(BaseAscendGateway):
    """HTTP gateway placeholder for future Ascend board service."""

    SPEECH_ENDPOINT = "/speech/analyze"
    VISION_ENDPOINT = "/vision/analyze"

    def __init__(self, base_url: str | None = None, timeout_seconds: float | None = None) -> None:
        self.base_url = (base_url if base_url is not None else settings.ASCEND_BASE_URL).strip()
        self.timeout_seconds = (
            float(timeout_seconds) if timeout_seconds is not None else float(settings.ASCEND_TIMEOUT_SECONDS)
        )
        self.speech_timeout_seconds = float(
            getattr(settings, "ASCEND_SPEECH_TIMEOUT_SECONDS", self.timeout_seconds)
        )
        self.vision_timeout_seconds = float(
            getattr(settings, "ASCEND_VISION_TIMEOUT_SECONDS", self.timeout_seconds)
        )
        self.speech_endpoint = self._normalize_endpoint(
            settings.ASCEND_SPEECH_ENDPOINT or self.SPEECH_ENDPOINT
        )
        self.vision_endpoint = self._normalize_endpoint(
            settings.ASCEND_VISION_ENDPOINT or self.VISION_ENDPOINT
        )
        print(
            "[ascend.trace] GATEWAY_INIT provider=ascend "
            f"base_url={self.base_url[:96]!r} "
            f"speech_endpoint={self.speech_endpoint} vision_endpoint={self.vision_endpoint} "
            f"speech_timeout_s={self.speech_timeout_seconds} "
            f"vision_timeout_s={self.vision_timeout_seconds} "
            f"generic_timeout_s={self.timeout_seconds}"
        )

    def send_speech_request(self, request_payload: AscendSpeechAnalyzeRequest) -> AscendGatewayResponse:
        upload_file_path = str(request_payload.payload.get("upload_file_path") or "").strip()
        upload_file_name = str(request_payload.payload.get("upload_file_name") or "").strip()
        if not upload_file_name and upload_file_path:
            upload_file_name = os.path.basename(upload_file_path)
        final_url = (
            f"{self.base_url.rstrip('/')}{self.speech_endpoint}"
            if self.base_url and self.speech_endpoint
            else ""
        )
        print(
            f"[ascend.trace] speech SEND provider=ascend endpoint={self.speech_endpoint} "
            f"request_id={request_payload.request_id} timeout_s={self.speech_timeout_seconds} "
            f"url={final_url} file={upload_file_name!r}"
        )
        payload = request_payload.payload if isinstance(request_payload.payload, dict) else {}
        ap = str(payload.get("analysis_phase") or "").strip()
        extra_form: dict[str, str] | None = {"analysis_phase": ap} if ap else None
        return self._post_multipart_file(
            endpoint=self.speech_endpoint,
            request_id=request_payload.request_id,
            file_path=upload_file_path,
            file_name=upload_file_name,
            file_field_name="audio_file",
            missing_path_message="语音上传失败: 缺少 upload_file_path",
            timeout_seconds=self.speech_timeout_seconds,
            extra_form_fields=extra_form,
        )

    def send_vision_request(self, request_payload: AscendVisionAnalyzeRequest) -> AscendGatewayResponse:
        upload_file_path = str(request_payload.payload.get("upload_file_path") or "").strip()
        upload_file_name = str(request_payload.payload.get("upload_file_name") or "").strip()
        if not upload_file_name and upload_file_path:
            upload_file_name = os.path.basename(upload_file_path)
        final_url = (
            f"{self.base_url.rstrip('/')}{self.vision_endpoint}"
            if self.base_url and self.vision_endpoint
            else ""
        )
        print(
            f"[ascend.trace] vision SEND provider=ascend endpoint={self.vision_endpoint} "
            f"request_id={request_payload.request_id} timeout_s={self.vision_timeout_seconds} "
            f"url={final_url} file={upload_file_name!r}"
        )
        return self._post_multipart_file(
            endpoint=self.vision_endpoint,
            request_id=request_payload.request_id,
            file_path=upload_file_path,
            file_name=upload_file_name,
            file_field_name="video_file",
            missing_path_message="视觉上传失败: 缺少 upload_file_path",
            timeout_seconds=self.vision_timeout_seconds,
        )

    @staticmethod
    def _normalize_endpoint(endpoint: str) -> str:
        endpoint = str(endpoint or "").strip()
        if not endpoint:
            return ""
        return endpoint if endpoint.startswith("/") else f"/{endpoint}"

    def _post_json(self, endpoint: str, payload: dict) -> AscendGatewayResponse:
        if not self.base_url:
            raise AscendGatewayConfigError("当前未配置开发板服务地址")

        url = f"{self.base_url.rstrip('/')}{endpoint}"
        request_id = str(payload.get("request_id") or "")
        print(
            f"[ascend.trace] json POST provider=ascend endpoint={endpoint} "
            f"request_id={request_id} timeout_s={self.timeout_seconds} url={url}"
        )
        body = json.dumps(payload, ensure_ascii=False).encode("utf-8")
        http_request = request.Request(
            url=url,
            data=body,
            headers={"Content-Type": "application/json"},
            method="POST",
        )

        try:
            with request.urlopen(http_request, timeout=self.timeout_seconds) as response:
                content = response.read().decode("utf-8")
        except error.HTTPError as exc:
            print(
                f"[ascend.trace] json FAIL provider=ascend endpoint={endpoint} "
                f"request_id={request_id} timeout_s={self.timeout_seconds} "
                f"success=false reason=http_{exc.code}"
            )
            raise AscendGatewayRequestError(
                f"开发板服务请求失败: status={exc.code}, endpoint={endpoint}, reason={exc.reason}"
            ) from exc
        except error.URLError as exc:
            print(
                f"[ascend.trace] json FAIL provider=ascend endpoint={endpoint} "
                f"request_id={request_id} timeout_s={self.timeout_seconds} success=false reason=url_error"
            )
            raise AscendGatewayRequestError(
                f"开发板服务请求失败: endpoint={endpoint}, reason={exc.reason}"
            ) from exc
        except socket.timeout as exc:
            print(
                f"[ascend.trace] json FAIL provider=ascend endpoint={endpoint} "
                f"request_id={request_id} timeout_s={self.timeout_seconds} success=false reason=timeout"
            )
            raise AscendGatewayRequestError(
                f"开发板服务请求超时: endpoint={endpoint}, timeout={self.timeout_seconds}s"
            ) from exc

        try:
            raw_data = json.loads(content)
        except json.JSONDecodeError as exc:
            print(
                f"[ascend.trace] json FAIL provider=ascend endpoint={endpoint} "
                f"request_id={request_id} timeout_s={self.timeout_seconds} success=false reason=invalid_json"
            )
            raise AscendGatewayRequestError("开发板服务返回了非 JSON 响应") from exc

        if not isinstance(raw_data, dict):
            print(
                f"[ascend.trace] json FAIL provider=ascend endpoint={endpoint} "
                f"request_id={request_id} timeout_s={self.timeout_seconds} success=false reason=invalid_shape"
            )
            raise AscendGatewayRequestError("开发板服务返回结构非法，期望 JSON 对象")

        response = AscendGatewayResponse.from_dict(raw_data)
        print(
            f"[ascend.trace] json DONE provider=ascend endpoint={endpoint} "
            f"request_id={response.request_id} board_provider={response.provider} "
            f"success={response.success} timeout_s={self.timeout_seconds}"
        )
        return response

    def _post_multipart_file(
        self,
        *,
        endpoint: str,
        request_id: str,
        file_path: str,
        file_name: str,
        file_field_name: str,
        missing_path_message: str,
        timeout_seconds: float,
        extra_form_fields: dict[str, str] | None = None,
    ) -> AscendGatewayResponse:
        if not self.base_url:
            raise AscendGatewayConfigError("当前未配置开发板服务地址")
        if not file_path:
            raise AscendGatewayRequestError(missing_path_message)
        if not os.path.exists(file_path):
            raise AscendGatewayRequestError(f"上传失败: 文件不存在 {file_path}")

        url = f"{self.base_url.rstrip('/')}{endpoint}"
        req_id = str(request_id or "").strip()
        print(
            "[ascend.trace] multipart POST provider=ascend "
            f"endpoint={endpoint} request_id={req_id} timeout_s={timeout_seconds} "
            f"url={url} file={file_name or os.path.basename(file_path)!r}"
        )
        boundary = f"----AscendVisionBoundary{uuid.uuid4().hex}"
        body = self._build_multipart_body(
            boundary=boundary,
            request_id=req_id,
            file_path=file_path,
            file_name=file_name or os.path.basename(file_path),
            file_field_name=file_field_name,
            extra_form_fields=extra_form_fields,
        )
        http_request = request.Request(
            url=url,
            data=body,
            headers={"Content-Type": f"multipart/form-data; boundary={boundary}"},
            method="POST",
        )
        try:
            with request.urlopen(http_request, timeout=timeout_seconds) as response:
                content = response.read().decode("utf-8")
        except error.HTTPError as exc:
            print(
                f"[ascend.trace] multipart FAIL provider=ascend endpoint={endpoint} "
                f"request_id={req_id} timeout_s={timeout_seconds} success=false reason=http_{exc.code}"
            )
            raise AscendGatewayRequestError(
                f"开发板服务请求失败: status={exc.code}, endpoint={endpoint}, reason={exc.reason}"
            ) from exc
        except error.URLError as exc:
            print(
                f"[ascend.trace] multipart FAIL provider=ascend endpoint={endpoint} "
                f"request_id={req_id} timeout_s={timeout_seconds} success=false reason=url_error"
            )
            raise AscendGatewayRequestError(
                f"开发板服务请求失败: endpoint={endpoint}, reason={exc.reason}"
            ) from exc
        except socket.timeout as exc:
            print(
                f"[ascend.trace] multipart FAIL provider=ascend endpoint={endpoint} "
                f"request_id={req_id} timeout_s={timeout_seconds} success=false reason=timeout"
            )
            raise AscendGatewayRequestError(
                f"开发板服务请求超时: endpoint={endpoint}, timeout={timeout_seconds}s, request_id={req_id}"
            ) from exc

        try:
            raw_data = json.loads(content)
        except json.JSONDecodeError as exc:
            print(
                f"[ascend.trace] multipart FAIL provider=ascend endpoint={endpoint} "
                f"request_id={req_id} timeout_s={timeout_seconds} success=false reason=invalid_json"
            )
            raise AscendGatewayRequestError("开发板服务返回了非 JSON 响应") from exc
        if not isinstance(raw_data, dict):
            print(
                f"[ascend.trace] multipart FAIL provider=ascend endpoint={endpoint} "
                f"request_id={req_id} timeout_s={timeout_seconds} success=false reason=invalid_shape"
            )
            raise AscendGatewayRequestError("开发板服务返回结构非法，期望 JSON 对象")
        response = AscendGatewayResponse.from_dict(raw_data)
        print(
            f"[ascend.trace] multipart DONE provider=ascend endpoint={endpoint} "
            f"request_id={response.request_id} board_provider={response.provider} "
            f"success={response.success} timeout_s={timeout_seconds}"
        )
        return response

    @staticmethod
    def _build_multipart_body(
        *,
        boundary: str,
        request_id: str,
        file_path: str,
        file_name: str,
        file_field_name: str,
        extra_form_fields: dict[str, str] | None = None,
    ) -> bytes:
        newline = b"\r\n"
        with open(file_path, "rb") as f:
            file_bytes = f.read()

        chunks: list[bytes] = []
        chunks.append(f"--{boundary}".encode("utf-8"))
        chunks.append(b'Content-Disposition: form-data; name="request_id"')
        chunks.append(b"")
        chunks.append(str(request_id).encode("utf-8"))

        if extra_form_fields:
            for field_name, field_value in extra_form_fields.items():
                name = str(field_name or "").strip()
                if not name:
                    continue
                chunks.append(f"--{boundary}".encode("utf-8"))
                chunks.append(f'Content-Disposition: form-data; name="{name}"'.encode("utf-8"))
                chunks.append(b"")
                chunks.append(str(field_value).encode("utf-8"))

        chunks.append(f"--{boundary}".encode("utf-8"))
        chunks.append(
            f'Content-Disposition: form-data; name="{file_field_name}"; filename="{file_name}"'.encode("utf-8")
        )
        chunks.append(b"Content-Type: application/octet-stream")
        chunks.append(b"")
        chunks.append(file_bytes)

        chunks.append(f"--{boundary}--".encode("utf-8"))
        chunks.append(b"")
        return newline.join(chunks)
