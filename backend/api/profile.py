"""个人训练档案摘要（当前登录用户，基于已有历史聚合逻辑）。"""

import json
import logging
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from api.auth import require_user
from api.result import (
    _OVERVIEW_RECENT_N,
    _build_valid_training_overview,
    _collect_history_items,
)
from database.db import get_db
from models.user_model import User

router = APIRouter()
_log = logging.getLogger(__name__)

_DEFAULT_PREFS = {
    "default_scoring_profile": "defense",
    "default_defense_material_mode": "with_ppt",
    "history_valid_only_default": True,
    "show_first_time_hints": True,
    "show_recent_training_reminder": True,
}

_DEFAULT_GOALS = {
    "v": 1,
    "target_total_score": None,
    "target_focus": None,
    "target_valid_session_count": None,
}


def _normalize_stored_prefs(raw: dict) -> dict:
    sp = str(raw.get("default_scoring_profile") or "defense").strip().lower()
    if sp not in ("defense", "interview"):
        sp = "defense"
    dm = str(raw.get("default_defense_material_mode") or "with_ppt").strip().lower()
    if dm not in ("with_ppt", "without_ppt"):
        dm = "with_ppt"
    return {
        "default_scoring_profile": sp,
        "default_defense_material_mode": dm,
        "history_valid_only_default": raw.get("history_valid_only_default", True) is not False,
        "show_first_time_hints": raw.get("show_first_time_hints", True) is not False,
        "show_recent_training_reminder": raw.get("show_recent_training_reminder", True)
        is not False,
        "training_goal_json": _normalize_training_goals(raw.get("training_goal_json") or raw.get("training_goals")),
    }


def _normalize_training_goals(obj) -> dict:
    if not isinstance(obj, dict):
        return dict(_DEFAULT_GOALS)
    out = {"v": 1, "target_total_score": None, "target_focus": None, "target_valid_session_count": None}
    fk = str(obj.get("target_focus") or "").strip().lower()
    if fk in ("language", "posture", "qa", "content"):
        out["target_focus"] = fk
    tts = obj.get("target_total_score")
    if tts is not None and tts != "":
        try:
            n = float(tts)
            if n == n:
                out["target_total_score"] = min(100.0, max(0.0, n))
        except (TypeError, ValueError):
            pass
    tvc = obj.get("target_valid_session_count")
    if tvc is not None and tvc != "":
        try:
            c = int(float(tvc))
            if c > 0:
                out["target_valid_session_count"] = min(999, c)
        except (TypeError, ValueError):
            pass
    return out


def _parse_user_prefs_column(user: User) -> tuple[dict, bool]:
    """Returns (normalized dict, has_saved_preferences in DB)."""
    raw = getattr(user, "account_prefs_json", None)
    if not raw or not str(raw).strip():
        return _defaults_norm(), False
    try:
        data = json.loads(str(raw))
        if not isinstance(data, dict):
            return _defaults_norm(), False
        return _normalize_stored_prefs(data), True
    except json.JSONDecodeError:
        return _defaults_norm(), False


class TrainingGoalsPayload(BaseModel):
    v: int = 1
    target_total_score: float | None = None
    target_focus: str | None = None
    target_valid_session_count: int | None = None


class AccountPreferencesPayload(BaseModel):
    default_scoring_profile: str = "defense"
    default_defense_material_mode: str = "with_ppt"
    history_valid_only_default: bool = True
    show_first_time_hints: bool = True
    show_recent_training_reminder: bool = True
    training_goals: TrainingGoalsPayload = Field(default_factory=TrainingGoalsPayload)


class AccountPreferencesResponse(AccountPreferencesPayload):
    has_saved_preferences: bool = False


def _response_from_normalized(norm: dict, has_saved: bool) -> AccountPreferencesResponse:
    g = norm.get("training_goal_json") or _DEFAULT_GOALS
    return AccountPreferencesResponse(
        default_scoring_profile=norm["default_scoring_profile"],
        default_defense_material_mode=norm["default_defense_material_mode"],
        history_valid_only_default=norm["history_valid_only_default"],
        show_first_time_hints=norm["show_first_time_hints"],
        show_recent_training_reminder=norm["show_recent_training_reminder"],
        training_goals=TrainingGoalsPayload(**g),
        has_saved_preferences=has_saved,
    )


class ProfileSummaryResponse(BaseModel):
    username: str
    created_at: str | None = None
    valid_training_count: int = 0
    valid_training_count_recent: int = 0
    recent_window_size: int = Field(default=_OVERVIEW_RECENT_N)
    best_total_score: float | None = None
    overview_ready: bool = False
    overview_message: str | None = None
    latest_valid_session_id: str | None = None
    latest_valid_training_focus: str | None = None
    latest_valid_created_at: str | None = None
    latest_valid_total_score: float | None = None
    recommended_continue_focus: str | None = None
    focus_distribution_recent: dict[str, int] = Field(default_factory=dict)
    avg_total_score_recent: float | None = None


def _iso_user_created_at(user: User) -> str | None:
    raw = getattr(user, "created_at", None)
    if raw is None:
        return None
    if isinstance(raw, datetime):
        if raw.tzinfo is None:
            return raw.replace(tzinfo=timezone.utc).isoformat()
        return raw.isoformat()
    return str(raw)


@router.get("/summary", response_model=ProfileSummaryResponse)
def profile_summary(
    db: Session = Depends(get_db),
    user: User = Depends(require_user),
):
    items = _collect_history_items(db, user.id)
    overview = _build_valid_training_overview(items, recent_n=_OVERVIEW_RECENT_N)
    valid_all = [h for h in items if h.training_valid]
    best: float | None = None
    for h in valid_all:
        try:
            sc = float(h.total_score or 0.0)
        except (TypeError, ValueError):
            continue
        if best is None or sc > best:
            best = sc
    if best is not None:
        best = round(best, 2)

    return ProfileSummaryResponse(
        username=user.username,
        created_at=_iso_user_created_at(user),
        valid_training_count=len(valid_all),
        valid_training_count_recent=overview.valid_count_recent,
        recent_window_size=overview.recent_window_size,
        best_total_score=best,
        overview_ready=overview.overview_ready,
        overview_message=overview.overview_message,
        latest_valid_session_id=overview.latest_valid_session_id,
        latest_valid_training_focus=overview.latest_valid_training_focus,
        latest_valid_created_at=overview.latest_valid_created_at,
        latest_valid_total_score=overview.latest_valid_total_score,
        recommended_continue_focus=overview.recommended_continue_focus,
        focus_distribution_recent=dict(overview.focus_distribution_recent or {}),
        avg_total_score_recent=overview.avg_total_score_recent,
    )


def _defaults_norm() -> dict:
    return {
        "default_scoring_profile": _DEFAULT_PREFS["default_scoring_profile"],
        "default_defense_material_mode": _DEFAULT_PREFS["default_defense_material_mode"],
        "history_valid_only_default": _DEFAULT_PREFS["history_valid_only_default"],
        "show_first_time_hints": _DEFAULT_PREFS["show_first_time_hints"],
        "show_recent_training_reminder": _DEFAULT_PREFS["show_recent_training_reminder"],
        "training_goal_json": dict(_DEFAULT_GOALS),
    }


@router.get("/preferences", response_model=AccountPreferencesResponse)
def get_account_preferences(
    db: Session = Depends(get_db),
    user: User = Depends(require_user),
):
    norm, has_saved = _parse_user_prefs_column(user)
    loaded = "stored" if has_saved else "defaults"
    resp = _response_from_normalized(norm, has_saved)
    _log.info(
        "[profile.preferences] user_id=%s loaded=%s has_saved_preferences=%s",
        user.id,
        loaded,
        has_saved,
    )
    print(
        f"[profile.preferences] user_id={user.id} loaded={loaded} has_saved_preferences={has_saved}",
        flush=True,
    )
    return resp


@router.put("/preferences", response_model=AccountPreferencesResponse)
def put_account_preferences(
    body: AccountPreferencesPayload,
    db: Session = Depends(get_db),
    user: User = Depends(require_user),
):
    g_raw = body.training_goals.model_dump() if body.training_goals else {}
    to_store = {
        "default_scoring_profile": str(body.default_scoring_profile or "defense").strip().lower(),
        "default_defense_material_mode": str(body.default_defense_material_mode or "with_ppt")
        .strip()
        .lower(),
        "history_valid_only_default": body.history_valid_only_default,
        "show_first_time_hints": body.show_first_time_hints,
        "show_recent_training_reminder": body.show_recent_training_reminder,
        "training_goal_json": _normalize_training_goals(g_raw),
    }
    if to_store["default_scoring_profile"] not in ("defense", "interview"):
        raise HTTPException(status_code=400, detail="invalid default_scoring_profile")
    if to_store["default_defense_material_mode"] not in ("with_ppt", "without_ppt"):
        raise HTTPException(status_code=400, detail="invalid default_defense_material_mode")

    user.account_prefs_json = json.dumps(to_store, ensure_ascii=False)
    db.add(user)
    db.commit()
    db.refresh(user)

    norm, _ = _parse_user_prefs_column(user)
    resp = _response_from_normalized(norm, True)
    _log.info(
        "[profile.preferences] user_id=%s updated=1 scoring=%s material=%s",
        user.id,
        resp.default_scoring_profile,
        resp.default_defense_material_mode,
    )
    print(
        f"[profile.preferences] user_id={user.id} updated=1 "
        f"default_scoring_profile={resp.default_scoring_profile} "
        f"default_defense_material_mode={resp.default_defense_material_mode}",
        flush=True,
    )
    return resp

