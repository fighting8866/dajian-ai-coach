from fastapi import APIRouter, HTTPException, Depends
from sqlalchemy.orm import Session
import json

from api.auth import require_user
from api.training_scope import memory_payload_owned_by, training_record_owned_by
from database.db import get_db
from models.training_record import TrainingRecord
from models.result_model import MetricItem
from models.user_model import User
from services.mock_store import results, sessions
from services.report_service import ReportService
from api.result import (
    _apply_training_focus_trend_to_payload,
    _apply_training_validity_to_payload,
    _compose_result_payload,
    _parse_metrics_json_blob,
    _pick_training_focus_for_session,
)

router = APIRouter()
report_service = ReportService()


def _training_record_has_reportable_snapshot(rec: TrainingRecord) -> bool:
    """True when the row has enough persisted data to build a report without relying on memory."""
    if rec.metrics_json and str(rec.metrics_json).strip():
        return True
    if rec.total_score is not None or rec.language_score is not None or rec.posture_score is not None:
        return True
    if rec.qa_result_json and str(rec.qa_result_json).strip():
        return True
    if rec.transcript_text and str(rec.transcript_text).strip():
        return True
    if rec.ppt_match_json and str(rec.ppt_match_json).strip():
        return True
    if rec.audio_metrics_json and str(rec.audio_metrics_json).strip():
        return True
    return False


def _payload_from_training_record(db_record: TrainingRecord, sid: str) -> dict:
    metrics: list[MetricItem] = []
    ppt_match = None
    ppt_match_analysis = None
    qa_result = None
    audio_metrics = None
    raw_stored: dict = {}
    if db_record.metrics_json:
        try:
            metrics_data, raw_stored = _parse_metrics_json_blob(db_record.metrics_json)
            metrics = [MetricItem(**m) for m in metrics_data]
        except Exception:
            metrics = []
            raw_stored = {}
    if db_record.ppt_match_json:
        try:
            ppt_match = json.loads(db_record.ppt_match_json)
        except Exception:
            ppt_match = None
    if db_record.ppt_match_analysis_json:
        try:
            ppt_match_analysis = json.loads(db_record.ppt_match_analysis_json)
        except Exception:
            ppt_match_analysis = None
    if db_record.qa_result_json:
        try:
            qa_result = json.loads(db_record.qa_result_json)
        except Exception:
            qa_result = None
    if db_record.audio_metrics_json:
        try:
            audio_metrics = json.loads(db_record.audio_metrics_json)
        except Exception:
            audio_metrics = None

    raw_for_payload = dict(raw_stored)
    if db_record.total_score is not None:
        raw_for_payload.setdefault("total_score", db_record.total_score)
    if db_record.language_score is not None:
        raw_for_payload.setdefault("language_score", db_record.language_score)
    if db_record.posture_score is not None:
        raw_for_payload.setdefault("posture_score", db_record.posture_score)

    sp_col = getattr(db_record, "scoring_profile", None)
    spl_col = getattr(db_record, "scoring_profile_label", None)
    if sp_col and raw_for_payload.get("scoring_profile") is None:
        raw_for_payload["scoring_profile"] = sp_col
    if spl_col and raw_for_payload.get("scoring_profile_label") is None:
        raw_for_payload["scoring_profile_label"] = spl_col

    picked_tf = _pick_training_focus_for_session(sid, raw_stored, db_record)
    if picked_tf is not None:
        raw_for_payload["training_focus"] = picked_tf

    result_payload = _compose_result_payload(
        session_id=db_record.session_id,
        raw_result=raw_for_payload,
        metrics_items=[m.model_dump() for m in metrics],
        transcript=db_record.transcript_text or None,
        audio_metrics=audio_metrics,
        ppt_match=ppt_match,
        ppt_match_analysis=ppt_match_analysis,
        qa_result=qa_result,
        summary=None,
    )
    return {
        "session_id": db_record.session_id,
        "session_name": db_record.session_name or f"训练_{sid[:8]}",
        "timestamp": db_record.start_time or "",
        "start_time": db_record.start_time,
        "end_time": db_record.end_time,
        "created_at": db_record.created_at,
        **result_payload,
    }


@router.get("/report/{session_id}")
def get_report(
    session_id: str,
    db: Session = Depends(get_db),
    user: User = Depends(require_user),
):
    sid = str(session_id or "").strip()
    print(f"[report.user] current_user_id={user.id}", flush=True)
    try:
        db_record = db.query(TrainingRecord).filter(TrainingRecord.session_id == sid).first()
    except Exception:
        db_record = None

    result_mem = results.get(sid)
    payload: dict | None = None

    if db_record and (
        db_record.status == "completed" or _training_record_has_reportable_snapshot(db_record)
    ):
        if not training_record_owned_by(db_record, user):
            raise HTTPException(status_code=404, detail="暂无该训练报告或无权查看")
        payload = _payload_from_training_record(db_record, sid)
    elif result_mem and isinstance(result_mem, dict):
        if not memory_payload_owned_by(result_mem, user):
            raise HTTPException(status_code=404, detail="暂无该训练报告或无权查看")
        result_data = result_mem
        result_payload = _compose_result_payload(
            session_id=result_data.get("session_id", sid),
            raw_result=result_data,
            metrics_items=result_data.get("metrics", []),
            transcript=result_data.get("transcript"),
            audio_metrics=result_data.get("audio_metrics"),
            ppt_match=result_data.get("ppt_match"),
            ppt_match_analysis=result_data.get("ppt_match_analysis"),
            qa_result=result_data.get("qa_result"),
            summary=result_data.get("summary"),
        )
        _ts = (
            result_data.get("timestamp")
            or result_data.get("start_time")
            or (sessions.get(sid, {}) or {}).get("start_time")
            or ""
        )
        payload = {
            "session_id": result_data.get("session_id", sid),
            "session_name": result_data.get("session_name") or f"训练_{sid[:8]}",
            "timestamp": _ts,
            "start_time": result_data.get("start_time") or (sessions.get(sid, {}) or {}).get("start_time"),
            "end_time": result_data.get("end_time"),
            "created_at": result_data.get("created_at"),
            **result_payload,
        }

    if payload is None:
        if db_record is not None and not training_record_owned_by(db_record, user):
            raise HTTPException(status_code=404, detail="暂无该训练报告或无权查看")
        if db_record is None and not (result_mem and isinstance(result_mem, dict)):
            raise HTTPException(status_code=404, detail="报告不存在：未找到对应训练记录")
        raise HTTPException(status_code=404, detail="报告不存在：该训练记录暂无可用结果数据")

    _trend_ts = (
        db_record.start_time
        if db_record and getattr(db_record, "status", None) == "completed"
        else payload.get("start_time")
        or payload.get("timestamp")
        or (sessions.get(sid, {}) or {}).get("start_time")
    )
    _apply_training_validity_to_payload(sid, payload)
    _apply_training_focus_trend_to_payload(db, sid, payload, _trend_ts, user.id)

    _qr_rep = payload.get("qa_result") if isinstance(payload.get("qa_result"), dict) else {}
    _fgm_rep = _qr_rep.get("followup_generation_meta") if isinstance(_qr_rep, dict) else {}
    _fpl_rep = _fgm_rep.get("provider_label") if isinstance(_fgm_rep, dict) else None
    print(
        f"[report.api] followup provider_kind={payload.get('followup_provider_kind')!r} "
        f"(qa_result.followup={_qr_rep.get('followup_provider_kind')!r}) session_id={session_id}",
        flush=True,
    )
    print(f"[report.api] followup provider_label={_fpl_rep!r} session_id={session_id}", flush=True)
    print(
        f"[report.api] followup fallback_to_rule={bool(_qr_rep.get('followup_fallback_to_rule'))} "
        f"session_id={session_id}",
        flush=True,
    )

    if not payload.get("audio_session_summary"):
        print(
            "[report.api] missing or empty audio_session_summary "
            f"session_id={session_id}"
        )
    if not payload.get("vision_session_summary"):
        print(
            "[report.api] missing or empty vision_session_summary "
            f"session_id={session_id}"
        )
    print(
        f"[report.api] vision_session_summary={payload.get('vision_session_summary')!r} "
        f"session_id={session_id}"
    )
    _rpm = payload.get("ppt_match")
    _rpm_ok = isinstance(_rpm, dict) and bool(_rpm)
    print(
        "[report.api] ppt_match_source=",
        payload.get("ppt_match_source"),
        "has_ppt_match=",
        _rpm_ok,
        "ppt_match summary=",
        (
            f"page_index={_rpm.get('page_index')!r} match_source={str(_rpm.get('match_source') or '')!r}"
            if _rpm_ok
            else "(none)"
        ),
        f"session_id={session_id}",
        flush=True,
    )

    report = report_service.build_report(payload)
    _bi = report.get("basic_info")
    if isinstance(_bi, dict) and payload.get("timestamp"):
        _bi["timestamp"] = payload.get("timestamp")
    breakdown = payload.get("score_breakdown") or {}
    score_explanations = payload.get("score_explanations") or {}
    print(
        "[report.api] score_explanations raw=",
        score_explanations,
    )
    print("[report.api] score_explanations type=", type(score_explanations).__name__)
    print(
        "[report.api] score_explanations keys=",
        list(score_explanations.keys()) if isinstance(score_explanations, dict) else None,
    )
    missing_explanations = [
        key for key in ("total", "language", "posture", "content", "qa")
        if not score_explanations.get(key)
    ]
    if missing_explanations:
        print(
            "[report.api] missing score_explanations keys: "
            f"session_id={session_id} missing={missing_explanations!r} "
            f"score_explanations={score_explanations!r}"
        )
    valid_modules = (breakdown.get("valid_modules") or {}) if isinstance(breakdown, dict) else {}
    audio_analysis_payload = payload.get("audio_analysis")
    audio_valid_export = None
    if isinstance(audio_analysis_payload, dict) and "audio_valid" in audio_analysis_payload:
        audio_valid_export = audio_analysis_payload.get("audio_valid")
    if audio_valid_export is None:
        audio_valid_export = valid_modules.get("language")

    vision_valid_export = payload.get("vision_valid")
    vision_analysis_payload = payload.get("vision_analysis")
    if isinstance(vision_analysis_payload, dict) and vision_valid_export is None:
        vision_valid_export = vision_analysis_payload.get("vision_valid")
    if vision_valid_export is None:
        vision_valid_export = valid_modules.get("posture")

    report.update({
        "defense_material_mode": payload.get("defense_material_mode"),
        "recommended_training_focus": payload.get("recommended_training_focus"),
        "training_focus": payload.get("training_focus"),
        "training_focus_trend": payload.get("training_focus_trend"),
        "recent_focus_scores": payload.get("recent_focus_scores"),
        "focus_trend_kind": payload.get("focus_trend_kind"),
        "training_focus_summary": payload.get("training_focus_summary"),
        "training_focus_primary_score": payload.get("training_focus_primary_score"),
        "training_focus_vs_recent": payload.get("training_focus_vs_recent"),
        "training_focus_next_action": payload.get("training_focus_next_action"),
        "training_focus_next_hint": payload.get("training_focus_next_hint"),
        "training_focus_next_action_label": payload.get("training_focus_next_action_label"),
        "training_focus_metric_compare": payload.get("training_focus_metric_compare"),
        "training_focus_metric_highlights": payload.get("training_focus_metric_highlights"),
        "training_valid": payload.get("training_valid", True),
        "invalid_reason_summary": payload.get("invalid_reason_summary") or "",
        "ppt_match_source": payload.get("ppt_match_source"),
        "qa_source": payload.get("qa_source"),
        "followup_questions_chain": payload.get("followup_questions_chain"),
        "followup_chain_depth": payload.get("followup_chain_depth"),
        "followup_used": payload.get("followup_used"),
        "selected_followup_reason": payload.get("selected_followup_reason"),
        "scoring_profile": payload.get("scoring_profile"),
        "scoring_profile_label": payload.get("scoring_profile_label"),
        "total_score": payload.get("total_score"),
        "language_score": payload.get("language_score"),
        "posture_score": payload.get("posture_score"),
        "content_score": payload.get("content_score"),
        "qa_score": payload.get("qa_score"),
        "content_breakdown": payload.get("content_breakdown"),
        "qa_breakdown": payload.get("qa_breakdown"),
        "followup_questions": payload.get("followup_questions"),
        "overall_commentary": payload.get("overall_commentary"),
        "strengths": payload.get("strengths"),
        "weaknesses": payload.get("weaknesses"),
        "next_round_advice": payload.get("next_round_advice"),
        "coach_commentary": payload.get("coach_commentary"),
        "improvement_advice": payload.get("improvement_advice"),
        "coach_metadata": payload.get("coach_metadata"),
        "question_provider_kind": payload.get("question_provider_kind"),
        "followup_provider_kind": payload.get("followup_provider_kind"),
        "commentary_provider_kind": payload.get("commentary_provider_kind"),
        "commentary_generation_meta": payload.get("commentary_generation_meta"),
        "commentary_fallback_to_rule": payload.get("commentary_fallback_to_rule"),
        "scores": {
            **(report.get("scores") or {}),
            "content_score": payload.get("content_score", 0.0),
            "qa_score": payload.get("qa_score", 0.0),
        },
        "score_breakdown": payload.get("score_breakdown") or {},
        "score_explanations": score_explanations,
        "modality_validity": valid_modules,
        "vision_analysis": payload.get("vision_analysis"),
        "audio_analysis": payload.get("audio_analysis"),
        "audio_valid": audio_valid_export,
        "vision_valid": vision_valid_export,
        "transcript": payload.get("transcript"),
        "audio_metrics": payload.get("audio_metrics"),
        "ppt_match_analysis": payload.get("ppt_match_analysis"),
        "audio_session_summary": payload.get("audio_session_summary"),
        "vision_session_summary": payload.get("vision_session_summary"),
        "inference_chain_snapshot": payload.get("inference_chain_snapshot"),
        "timestamp": payload.get("timestamp") or report.get("basic_info", {}).get("timestamp"),
        "start_time": payload.get("start_time"),
        "end_time": payload.get("end_time"),
        "created_at": payload.get("created_at"),
        "main_recommendations": [
            (item.get("content") if isinstance(item, dict) else str(item))
            for item in (report.get("suggestions") or [])
        ],
    })
    print(
        f"[report.api] scoring_profile raw={report.get('scoring_profile')!r} "
        f"scoring_profile_label raw={report.get('scoring_profile_label')!r}"
    )
    print(
        f"[report.api] defense_material_mode={report.get('defense_material_mode')!r} session_id={session_id}",
        flush=True,
    )
    print(
        f"[report.api] recommended_training_focus={report.get('recommended_training_focus')!r} session_id={session_id}",
        flush=True,
    )
    print(
        f"[report.api] training_focus={report.get('training_focus')!r} session_id={session_id}",
        flush=True,
    )
    print(
        f"[report.api] training_focus_vs_recent={report.get('training_focus_vs_recent')!r} session_id={session_id}",
        flush=True,
    )
    print(
        f"[report.api] training_focus_next_action={report.get('training_focus_next_action')!r} session_id={session_id}",
        flush=True,
    )
    print(
        "[report.api] ppt_match_source=",
        report.get("ppt_match_source"),
        "qa_source=",
        report.get("qa_source"),
        f"session_id={session_id}",
        flush=True,
    )
    print(
        f"[report.api] overall_commentary={report.get('overall_commentary')!r} session_id={session_id}",
        flush=True,
    )
    print(
        f"[report.api] strengths={report.get('strengths')!r} session_id={session_id}",
        flush=True,
    )
    print(
        f"[report.api] weaknesses={report.get('weaknesses')!r} session_id={session_id}",
        flush=True,
    )
    return report
