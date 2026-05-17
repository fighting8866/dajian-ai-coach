from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any


class AscendGatewayError(RuntimeError):
    """Base error type for Ascend gateway operations."""


class AscendGatewayConfigError(AscendGatewayError):
    """Raised when required Ascend gateway configuration is missing."""


class AscendGatewayRequestError(AscendGatewayError):
    """Raised when Ascend gateway request fails."""


@dataclass
class AscendSpeechAnalyzeRequest:
    task: str = "speech_analyze"
    request_id: str = ""
    payload: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "task": self.task,
            "request_id": self.request_id,
            "payload": self.payload,
        }


@dataclass
class AscendVisionAnalyzeRequest:
    task: str = "vision_analyze"
    request_id: str = ""
    payload: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "task": self.task,
            "request_id": self.request_id,
            "payload": self.payload,
        }


@dataclass
class AscendGatewayResponse:
    success: bool
    provider: str
    request_id: str
    result: dict[str, Any]
    error: str | None = None

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "AscendGatewayResponse":
        return cls(
            success=bool(data.get("success", False)),
            provider=str(data.get("provider") or "ascend"),
            request_id=str(data.get("request_id") or ""),
            result=data.get("result") if isinstance(data.get("result"), dict) else {},
            error=data.get("error"),
        )


class BaseAscendGateway(ABC):
    """Abstract board gateway for speech/vision communication."""

    @abstractmethod
    def send_speech_request(self, request: AscendSpeechAnalyzeRequest) -> AscendGatewayResponse:
        raise NotImplementedError

    @abstractmethod
    def send_vision_request(self, request: AscendVisionAnalyzeRequest) -> AscendGatewayResponse:
        raise NotImplementedError
