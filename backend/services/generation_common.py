"""
统一「老师提问 / 老师追问 / 老师点评」生成侧的元数据契约（Agent 化前骨架 V1）。

- 不接大模型；仅定义 provider_kind / generation_meta 形状，便于后续接 model / hybrid。
"""

from __future__ import annotations

from typing import Any

PROVIDER_RULE = "rule"
PROVIDER_MODEL = "model"
PROVIDER_HYBRID = "hybrid"

_CAPABILITY_LABELS: dict[str, dict[str, str]] = {
    "question": {
        "rule": "规则生成",
        "model": "模型生成（预留）",
        "hybrid": "混合生成（预留）",
    },
    "followup": {
        "rule": "规则追问",
        "model": "模型追问（预留）",
        "hybrid": "混合追问（预留）",
    },
    "commentary": {
        "rule": "规则点评",
        "model": "模型点评（预留）",
        "hybrid": "混合点评（预留）",
    },
}


def normalize_generation_provider_kind(kind: str | None, *, default: str = PROVIDER_RULE) -> str:
    k = (kind or default).strip().lower()
    if k in (PROVIDER_RULE, PROVIDER_MODEL, PROVIDER_HYBRID):
        return k
    return default


def build_generation_meta(capability: str, provider_kind: str) -> dict[str, Any]:
    kind = normalize_generation_provider_kind(provider_kind)
    labels = _CAPABILITY_LABELS.get(capability, {})
    return {
        "capability": capability,
        "provider_kind": kind,
        "provider_label": labels.get(kind, kind),
        "generation_mode": f"{capability}_{kind}_v1",
        "version": "v1-skeleton",
    }
