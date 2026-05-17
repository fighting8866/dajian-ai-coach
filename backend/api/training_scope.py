"""训练数据归属（V1）：与 users.id 对齐的最小校验。"""

from __future__ import annotations

from models.training_record import TrainingRecord
from models.user_model import User


def coerce_user_id(val: object) -> int | None:
    if val is None:
        return None
    if isinstance(val, bool):
        return None
    if isinstance(val, int):
        return val
    s = str(val).strip()
    if not s:
        return None
    try:
        return int(s)
    except ValueError:
        return None


def training_record_owned_by(record: TrainingRecord | None, user: User) -> bool:
    if record is None:
        return False
    uid = getattr(record, "user_id", None)
    if uid is None:
        return False
    try:
        return int(uid) == int(user.id)
    except (TypeError, ValueError):
        return False


def memory_payload_owned_by(data: dict | None, user: User) -> bool:
    if not isinstance(data, dict):
        return False
    uid = coerce_user_id(data.get("user_id"))
    if uid is None:
        return False
    return uid == int(user.id)
