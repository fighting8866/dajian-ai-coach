"""会话开始/结束 API。"""

from __future__ import annotations

import json
import uuid
from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, Query, Request
from sqlalchemy.orm import Session

from api.auth import require_user
from api.training_scope import coerce_user_id
from configs.scoring_profiles import DEFAULT_SCORING_PROFILE, get_scoring_profile
from database.db import get_db
from models.session_model import (
    Metrics,
    SessionAbandonRequest,
    SessionAbandonResponse,
    SessionResumeStatusResponse,
    SessionStartRequest,
    SessionStartResponse,
    SessionStopRequest,
    SessionStopResponse,
)
from models.training_record import TrainingRecord
from models.user_model import User
from factories.provider_factory import get_ai_provider_status
from services.mock_store import results, sessions

router = APIRouter()


def _resolve_stop_fallback_transcript(
    payload: dict,
    audio_analysis: dict | None,
    qa_result: dict | None,
    body: SessionStopRequest,
) -> str:
    """合并多路文本供 stop 猜页兜底：音频转写、merged、口述框、问答作答（取最长非空）。"""
    chunks: list[str] = []
    if isinstance(audio_analysis, dict):
        t = str(audio_analysis.get("transcript") or "").strip()
        if t:
            chunks.append(t)
        m = str(audio_analysis.get("merged_transcript") or "").strip()
        if m and m not in chunks:
            chunks.append(m)
    raw_spoken = payload.get("lecture_spoken_text")
    if raw_spoken is None and isinstance(payload.get("spoken_text"), str):
        raw_spoken = payload.get("spoken_text")
    st = str(raw_spoken or "").strip()
    if not st and body.lecture_spoken_text:
        st = str(body.lecture_spoken_text or "").strip()
    if st:
        chunks.append(st)
    if isinstance(qa_result, dict):
        aq = str(qa_result.get("answer_text") or "").strip()
        if aq:
            chunks.append(aq)
    if not chunks:
        return ""
    return max(chunks, key=len)


def _normalize_ppt_match_for_scoring(pm: dict | None) -> dict | None:
    """与 scoring 使用的 PptMatch 口径对齐；兼容少量字段别名，避免前端与 Pydantic 已接受但缺省字段时计分为空。"""
    if not isinstance(pm, dict):
        return None
    out = dict(pm)
    if out.get("page_index") is None:
        for alt in ("current_page", "matched_page_index", "matched_page"):
            v = out.get(alt)
            if v is not None and v != "":
                try:
                    out["page_index"] = int(v)
                    break
                except (TypeError, ValueError):
                    continue
    try:
        pi = int(out["page_index"]) if out.get("page_index") is not None else None
    except (TypeError, ValueError):
        pi = None
    if pi is None:
        return None
    out["page_index"] = pi
    title = str(out.get("title") or "").strip()
    if not title:
        title = str(out.get("matched_title") or out.get("current_page_title") or "").strip()
    if not title:
        title = f"第 {pi} 页"
    out["title"] = title
    try:
        out["match_score"] = float(out.get("match_score") or 0.0)
    except (TypeError, ValueError):
        out["match_score"] = 0.0
    try:
        out["keyword_coverage"] = float(out.get("keyword_coverage") or 0.0)
    except (TypeError, ValueError):
        out["keyword_coverage"] = 0.0

    def _str_list(val) -> list[str]:
        if val is None:
            return []
        if isinstance(val, list):
            return [str(x).strip() for x in val if str(x).strip()]
        if isinstance(val, str) and val.strip():
            return [s.strip() for s in val.replace("，", ",").split(",") if s.strip()]
        return []

    mk = _str_list(out.get("matched_keywords")) or _str_list(out.get("hit_keywords"))
    out["matched_keywords"] = mk
    out["missing_keywords"] = _str_list(out.get("missing_keywords"))
    cmt = str(out.get("comment") or "").strip()
    if not cmt:
        cmt = str(out.get("recommendation") or "").strip()
    if not cmt:
        cmt = "（PPT 单页匹配）"
    out["comment"] = cmt
    ms = str(out.get("match_source") or "").strip()
    out["match_source"] = ms or None
    return out


_METRIC_ROWS = (
    ("语速", "speech_rate"),
    ("停顿次数", "pause_count"),
    ("平均停顿时长", "avg_pause_sec"),
    ("口头禅次数", "filler_count"),
    ("正视前方比例", "forward_gaze_ratio"),
    ("低头率", "downward_head_ratio"),
    ("姿态稳定度", "posture_stability"),
)


def _metrics_to_items(m: Metrics | None) -> list[dict]:
    base = m if m is not None else Metrics()
    out: list[dict] = []
    for label, attr in _METRIC_ROWS:
        out.append({"name": label, "value": getattr(base, attr)})
    return out


def _resolve_scoring_profile(stop_profile: str | None, stored: str | None) -> str:
    for p in (stop_profile, stored):
        if isinstance(p, str) and p.strip():
            return get_scoring_profile(p.strip())["key"]
    return DEFAULT_SCORING_PROFILE


def _normalize_defense_material_mode(val: object) -> str:
    s = str(val or "").strip().lower()
    if s == "without_ppt":
        return "without_ppt"
    return "with_ppt"


def _normalize_training_focus(val: object, *, fallback: object | None = None) -> str:
    for candidate in (val, fallback):
        if candidate is None:
            continue
        s = str(candidate).strip().lower()
        if s in ("language", "posture", "qa", "content", "none"):
            return s
    return "none"


def _persist_training_record_after_stop(
    db: Session,
    sid: str,
    rec: dict,
    composed: dict,
    bundle: dict,
    training_focus: str,
    end_time_iso: str,
    user_id: int,
) -> None:
    """写入 training_records，便于 Result/History 走读库分支时仍能还原 training_focus。"""
    try:
        row = db.query(TrainingRecord).filter(TrainingRecord.session_id == sid).first()
        if row is None:
            row = TrainingRecord(session_id=sid)
            db.add(row)
        row.user_id = int(user_id)
        row.session_name = bundle.get("session_name") or rec.get("session_name") or ""
        row.start_time = rec.get("start_time") or ""
        row.created_at = rec.get("created_at") or row.start_time
        row.end_time = end_time_iso
        row.status = "completed"
        row.total_score = float(composed.get("total_score") or 0.0)
        ls, ps = composed.get("language_score"), composed.get("posture_score")
        row.language_score = float(ls) if ls is not None else None
        row.posture_score = float(ps) if ps is not None else None
        row.scoring_profile = composed.get("scoring_profile")
        row.scoring_profile_label = composed.get("scoring_profile_label")
        row.training_focus = training_focus
        row.transcript_text = bundle.get("transcript")
        am = bundle.get("audio_metrics")
        if am is not None:
            row.audio_metrics_json = json.dumps(am, ensure_ascii=False)
        pm = bundle.get("ppt_match")
        if isinstance(pm, dict):
            row.ppt_match_json = json.dumps(pm, ensure_ascii=False)
        pma = bundle.get("ppt_match_analysis")
        if isinstance(pma, dict):
            row.ppt_match_analysis_json = json.dumps(pma, ensure_ascii=False)
        qr = bundle.get("qa_result")
        if isinstance(qr, dict):
            row.qa_result_json = json.dumps(qr, ensure_ascii=False)
        metrics_items = composed.get("metrics") or []
        serial_metrics: list = []
        for m in metrics_items:
            if hasattr(m, "model_dump"):
                serial_metrics.append(m.model_dump())
            elif isinstance(m, dict):
                serial_metrics.append(m)
            else:
                serial_metrics.append(
                    {"name": str(getattr(m, "name", m)), "value": getattr(m, "value", 0)}
                )
        wrap: dict = {
            "metric_items": serial_metrics,
            "score_breakdown": composed.get("score_breakdown"),
            "score_explanations": composed.get("score_explanations"),
            "training_focus": training_focus,
            "recommended_training_focus": composed.get("recommended_training_focus"),
            "defense_material_mode": composed.get("defense_material_mode"),
            "scoring_profile": composed.get("scoring_profile"),
            "scoring_profile_label": composed.get("scoring_profile_label"),
        }
        _ics = bundle.get("inference_chain_snapshot")
        if isinstance(_ics, dict):
            wrap["inference_chain_snapshot"] = _ics
        row.metrics_json = json.dumps(wrap, ensure_ascii=False, default=str)
        sugg = composed.get("suggestions")
        if sugg is not None:
            row.suggestions_json = json.dumps(sugg, ensure_ascii=False, default=str)
        db.commit()
        print(
            f"[session.stop] persisted training_focus={training_focus!r} session_id={sid}",
            flush=True,
        )
    except Exception as e:
        db.rollback()
        print(
            f"[session.stop] training_record persist failed: {e!r} session_id={sid}",
            flush=True,
        )


@router.get("/resume_status", response_model=SessionResumeStatusResponse)
def resume_status(
    session_id: str = Query(default=""),
    user: User = Depends(require_user),
):
    """轻量：判断内存中会话是否仍在进行中（供前端中断恢复）。"""
    print(f"[session.user] current_user_id={user.id}", flush=True)
    sid = str(session_id or "").strip()
    if not sid:
        return SessionResumeStatusResponse(recoverable=False, reason="no_session_id")
    rec = sessions.get(sid)
    if not rec:
        return SessionResumeStatusResponse(recoverable=False, reason="not_found_or_server_restarted")
    if rec.get("status") != "active":
        return SessionResumeStatusResponse(recoverable=False, reason="already_completed")
    rid = coerce_user_id(rec.get("user_id"))
    if rid is None:
        return SessionResumeStatusResponse(recoverable=False, reason="session_missing_owner")
    if rid != int(user.id):
        return SessionResumeStatusResponse(recoverable=False, reason="not_owner")
    tf = _normalize_training_focus(rec.get("training_focus"))
    dm = _normalize_defense_material_mode(rec.get("defense_material_mode"))
    sp = rec.get("scoring_profile")
    return SessionResumeStatusResponse(
        recoverable=True,
        session_id=sid,
        scoring_profile=sp if isinstance(sp, str) else None,
        training_focus=tf,
        defense_material_mode=dm,
        start_time=str(rec.get("start_time") or "") or None,
    )


@router.post("/abandon", response_model=SessionAbandonResponse)
def abandon_session(body: SessionAbandonRequest, user: User = Depends(require_user)):
    """放弃未结束会话：从内存 sessions 移除，避免占用 resume。"""
    print(f"[session.user] current_user_id={user.id}", flush=True)
    sid = str(body.session_id or "").strip()
    if not sid:
        return SessionAbandonResponse(ok=False, discarded=False)
    rec = sessions.get(sid)
    if not rec:
        return SessionAbandonResponse(ok=True, discarded=False)
    if rec.get("status") != "active":
        return SessionAbandonResponse(ok=True, discarded=False)
    rid = coerce_user_id(rec.get("user_id"))
    if rid is not None and rid != int(user.id):
        return SessionAbandonResponse(ok=False, discarded=False)
    del sessions[sid]
    print(f"[session.abandon] discarded active session_id={sid}", flush=True)
    return SessionAbandonResponse(ok=True, discarded=True)


@router.post("/start", response_model=SessionStartResponse)
def start_session(body: SessionStartRequest, user: User = Depends(require_user)):
    print(f"[session.user] current_user_id={user.id}", flush=True)
    session_id = str(uuid.uuid4())
    start_time = datetime.utcnow().isoformat()
    profile_key = None
    if body.scoring_profile and str(body.scoring_profile).strip():
        profile_key = get_scoring_profile(str(body.scoring_profile).strip())["key"]
    training_focus = _normalize_training_focus(getattr(body, "training_focus", None))
    dm_start = _normalize_defense_material_mode(getattr(body, "defense_material_mode", None))
    sessions[session_id] = {
        "user_id": int(user.id),
        "session_name": body.session_name or "",
        "start_time": start_time,
        "created_at": start_time,
        "status": "active",
        "scoring_profile": profile_key,
        "training_focus": training_focus,
        "defense_material_mode": dm_start,
    }
    print(
        f"[session.start] user_id={user.id} training_focus={training_focus!r} session_id={session_id}",
        flush=True,
    )
    return SessionStartResponse(
        session_id=session_id,
        start_time=start_time,
        message="训练已开始",
    )


@router.post("/stop", response_model=SessionStopResponse)
async def stop_session(
    request: Request,
    user: User = Depends(require_user),
    db: Session = Depends(get_db),
):
    # 延后导入，避免与 app 初始化顺序产生循环依赖
    from api.result import _compose_result_payload

    print(f"[session.user] current_user_id={user.id}", flush=True)
    payload = await request.json()
    print(
        "[session.stop.debug] raw request keys",
        sorted(payload.keys()) if isinstance(payload, dict) else None,
        flush=True,
    )
    _raw_pm_in = payload.get("ppt_match")
    print("[session.stop] raw request ppt_match=", _raw_pm_in, flush=True)
    body = SessionStopRequest.model_validate(payload)
    defense_material_mode = _normalize_defense_material_mode(
        getattr(body, "defense_material_mode", None) or payload.get("defense_material_mode") or payload.get("defenseMaterialMode")
    )
    print(f"[session.stop] defense_material_mode={defense_material_mode!r}", flush=True)
    print(
        "[session.stop.debug] request.ppt_match=",
        _raw_pm_in,
        "request.ppt_match_source=",
        payload.get("ppt_match_source"),
        "request.ppt_id=",
        payload.get("ppt_id"),
        flush=True,
    )

    sid = body.session_id
    if sid not in sessions:
        raise HTTPException(status_code=404, detail="会话不存在")

    rec = sessions[sid]
    rid = coerce_user_id(rec.get("user_id"))
    if rid is None:
        rec["user_id"] = int(user.id)
        print(
            f"[session.stop] claimed legacy active session user_id={user.id} session_id={sid}",
            flush=True,
        )
    elif rid != int(user.id):
        raise HTTPException(status_code=404, detail="会话不存在")
    if rec.get("status") == "completed":
        raise HTTPException(status_code=400, detail="会话已结束")

    tf_from_body = getattr(body, "training_focus", None)
    if tf_from_body is None and isinstance(payload, dict):
        tf_from_body = payload.get("training_focus")
    print(
        f"[session.stop] request.training_focus={tf_from_body!r} session_id={sid}",
        flush=True,
    )
    training_focus = _normalize_training_focus(tf_from_body, fallback=rec.get("training_focus"))
    print(
        f"[session.stop] resolved training_focus={training_focus!r} session_id={sid}",
        flush=True,
    )

    profile = _resolve_scoring_profile(body.scoring_profile, rec.get("scoring_profile"))
    metrics_items = _metrics_to_items(body.metrics)
    ppt_match = body.ppt_match.model_dump() if body.ppt_match else None
    ppt_match = _normalize_ppt_match_for_scoring(ppt_match)
    if isinstance(_raw_pm_in, dict) and _raw_pm_in and ppt_match is None:
        print(
            "[session.stop] note: client ppt_match present but normalize returned None "
            f"raw_keys={list(_raw_pm_in.keys())!r}",
            flush=True,
        )
    ppt_match_analysis = (
        body.ppt_match_analysis.model_dump() if body.ppt_match_analysis else None
    )
    qa_result = body.qa_result.model_dump() if body.qa_result else None
    ppt_match_source = (body.ppt_match_source or "").strip() or (
        (ppt_match or {}).get("match_source") if isinstance(ppt_match, dict) else None
    )
    qa_source = (body.qa_source or "").strip() or (
        (qa_result or {}).get("qa_source") if isinstance(qa_result, dict) else None
    )
    ppt_match_source = (str(ppt_match_source).strip() if ppt_match_source else None) or None
    qa_source = (str(qa_source).strip() if qa_source else None) or None
    _has_pm_stop = isinstance(ppt_match, dict) and bool(ppt_match)
    print(
        "[session.stop] ppt_match_source=",
        ppt_match_source or "(none)",
        "has_ppt_match=",
        _has_pm_stop,
        flush=True,
    )
    print("[session.stop] qa_source=", qa_source or "(none)", flush=True)
    print(f"[session.stop] qa_source_in_payload={qa_source!r}", flush=True)
    if isinstance(ppt_match, dict) and ppt_match:
        _ppi = ppt_match.get("page_index")
        _pms = str(ppt_match.get("match_source") or "").strip()
        _pti = str(ppt_match.get("title") or "")[:80]
        print(
            "[session.stop] ppt_match summary=",
            f"page_index={_ppi!r}",
            f"match_source={_pms!r}",
            f"match_score={ppt_match.get('match_score')!r}",
            f"title_preview={_pti!r}",
            flush=True,
        )
    else:
        print("[session.stop] ppt_match summary=(none)", flush=True)
    if isinstance(qa_result, dict) and qa_result:
        _qq = str(qa_result.get("question") or "")[:120]
        _aim = qa_result.get("answer_input_mode")
        _at_len = len(str(qa_result.get("answer_text") or "").strip())
        print(
            "[session.stop] qa_result summary=",
            f"is_relevant={qa_result.get('is_relevant')!r}",
            f"coverage_score={qa_result.get('coverage_score')!r}",
            f"qa_source_in_payload={qa_source!r}",
            f"answer_input_mode={_aim!r}",
            f"answer_text_len={_at_len}",
            f"question_preview={_qq!r}",
            flush=True,
        )
        _fgm = qa_result.get("followup_generation_meta")
        _fpl = _fgm.get("provider_label") if isinstance(_fgm, dict) else None
        print(f"[session.stop] followup provider_kind={qa_result.get('followup_provider_kind')!r}", flush=True)
        print(f"[session.stop] followup provider_label={_fpl!r}", flush=True)
        print(
            f"[session.stop] followup fallback_to_rule={bool(qa_result.get('followup_fallback_to_rule'))}",
            flush=True,
        )
        if (
            str(qa_result.get("answer_input_mode") or "").strip().lower() == "voice"
            and str(qa_result.get("answer_text") or "").strip()
        ):
            print("[session.stop] qa voice transcript accepted for qa evaluation", flush=True)
    else:
        print("[session.stop] qa_result summary=(none)", flush=True)
    # 保留客户端原始 audio/vision 字典中的长时会话汇总字段（Pydantic 子模型会丢弃未声明字段）
    _raw_a = payload.get("audio_analysis") if isinstance(payload.get("audio_analysis"), dict) else None
    _raw_v = payload.get("vision_analysis") if isinstance(payload.get("vision_analysis"), dict) else None
    audio_analysis = _raw_a if _raw_a is not None else (
        body.audio_analysis.model_dump() if body.audio_analysis else None
    )
    vision_analysis = _raw_v if _raw_v is not None else (
        body.vision_analysis.model_dump() if body.vision_analysis else None
    )
    content_document = body.content_document
    ppt_text_data = body.ppt_text_data.model_dump() if body.ppt_text_data else None

    transcript = None
    audio_metrics = None
    if audio_analysis:
        transcript = audio_analysis.get("transcript") or None
        audio_metrics = {
            "speech_rate": audio_analysis.get("speech_rate", 0),
            "pause_count": audio_analysis.get("pause_count", 0),
            "avg_pause_sec": audio_analysis.get("avg_pause_sec", 0),
            "filler_count": audio_analysis.get("filler_count", 0),
        }

    _tr_audio_only = str(transcript or "").strip()
    print("[session.stop.debug] transcript_text length (audio field only)", len(_tr_audio_only), flush=True)
    fb_tr = _resolve_stop_fallback_transcript(payload, audio_analysis, qa_result, body)
    print("[session.stop.debug] resolved fallback transcript_text length", len(fb_tr), flush=True)

    # 无 ppt_match：合并文本 + ppt_id + ppt_store（或 ppt_text_data 合成页）→ 自动猜页兜底（无课件答辩模式跳过）
    if not ppt_match and defense_material_mode != "without_ppt":
        from services.mock_store import ppt_store
        from services.ppt_match_service import (
            PPTMatchService,
            build_plain_ppt_match_from_best_page,
            synthesize_pages_from_ppt_text_data,
        )

        fb_ppt_id = (str(body.ppt_id).strip() if body.ppt_id is not None else "") or ""
        info = ppt_store.get(fb_ppt_id) if fb_ppt_id else None
        pages = list(info.get("pages") or []) if isinstance(info, dict) else []
        document = info.get("document") if isinstance(info, dict) else None
        if content_document and isinstance(content_document, dict) and not document:
            document = content_document

        pages_source = "ppt_store"
        if (not pages) and ppt_text_data:
            syn = synthesize_pages_from_ppt_text_data(ppt_text_data)
            if syn:
                pages = syn
                pages_source = "ppt_text_data_synthetic"
                print(
                    "[session.stop.debug] synthesized pages from ppt_text_data count=",
                    len(pages),
                    flush=True,
                )

        has_pages = isinstance(pages, list) and len(pages) > 0
        print(
            "[session.stop.debug] fallback eligibility:",
            f"has_ppt_id={bool(fb_ppt_id)}",
            f"has_transcript_text={bool(fb_tr)}",
            f"transcript_len={len(fb_tr)}",
            f"ppt_store_hit={info is not None}",
            f"has_pages={has_pages}",
            f"pages_source={pages_source!r}",
            f"has_document={bool(document)}",
            flush=True,
        )

        if not fb_ppt_id:
            print("[session.stop.debug] fallback blocked: missing ppt_id", flush=True)
        elif not fb_tr:
            print(
                "[session.stop.debug] fallback blocked: empty transcript "
                "(audio transcript / merged / lecture_spoken_text / qa answer_text)",
                flush=True,
            )
        elif info is None and pages_source != "ppt_text_data_synthetic":
            print(
                "[session.stop.debug] fallback blocked: ppt_id not in ppt_store (no entry; restart 丢内存时需 ppt_text_data)",
                flush=True,
            )
        elif not has_pages:
            print(
                "[session.stop.debug] fallback blocked: no pages (store empty and ppt_text_data unusable)",
                flush=True,
            )
        else:
            print("[session.stop.debug] fallback triggered", flush=True)
            print(f"[session.stop.debug] transcript_text len={len(fb_tr)}", flush=True)
            print(f"[session.stop.debug] ppt_id={fb_ppt_id!r}", flush=True)
            print(f"[session.stop.debug] ppt_store_hit={info is not None}", flush=True)
            print(
                "[session.stop.debug] fallback auto_guess request preview",
                {"text_len": len(fb_tr), "preview": fb_tr[:200]},
                flush=True,
            )
            try:
                matcher = PPTMatchService()
                guess = matcher.match_best_page(pages, fb_tr, document=document)
                print("[session.stop.debug] fallback auto_guess result=", guess, flush=True)
                plain_fb = build_plain_ppt_match_from_best_page(guess, pages)
                print("[session.stop.debug] fallback plain ppt_match=", plain_fb, flush=True)
                pm_norm = _normalize_ppt_match_for_scoring(plain_fb)
                if pm_norm:
                    ppt_match = pm_norm
                    ppt_match_source = "auto_guess"
                    print(
                        "[session.stop.debug] fallback ppt_match after normalize: non-null page_index=",
                        pm_norm.get("page_index"),
                        flush=True,
                    )
                else:
                    print(
                        "[session.stop.debug] fallback ppt_match after normalize: NULL "
                        f"plain_fb={plain_fb!r}",
                        flush=True,
                    )
            except Exception as e:
                print(f"[session.stop.debug] fallback auto_guess exception: {e!r}", flush=True)
    elif not ppt_match and defense_material_mode == "without_ppt":
        print(
            "[session.stop] skip ppt_match auto_guess: defense_material_mode=without_ppt "
            "(本轮未启用课件内容匹配)",
            flush=True,
        )

    raw: dict = {
        "session_id": sid,
        "session_name": rec.get("session_name") or f"训练_{sid[:8]}",
        "scoring_profile": profile,
        "scoring_profile_label": get_scoring_profile(profile).get("label"),
        "ppt_match": ppt_match,
        "ppt_match_analysis": ppt_match_analysis,
        "qa_result": qa_result,
        "audio_analysis": audio_analysis,
        "vision_analysis": vision_analysis,
        "content_document": content_document,
        "ppt_text_data": ppt_text_data,
        "ppt_match_source": ppt_match_source,
        "qa_source": qa_source,
        "defense_material_mode": defense_material_mode,
        "training_focus": training_focus,
    }
    if body.client_audio_blob_bytes is not None:
        raw["client_audio_blob_bytes"] = body.client_audio_blob_bytes
    if body.client_video_blob_bytes is not None:
        raw["client_video_blob_bytes"] = body.client_video_blob_bytes
    if body.client_audio_analyze_elapsed_ms is not None:
        raw["client_audio_analyze_elapsed_ms"] = body.client_audio_analyze_elapsed_ms
    if body.client_vision_analyze_elapsed_ms is not None:
        raw["client_vision_analyze_elapsed_ms"] = body.client_vision_analyze_elapsed_ms
    if body.followup_questions_chain is not None:
        raw["followup_questions_chain"] = body.followup_questions_chain
    if body.followup_chain_depth is not None:
        raw["followup_chain_depth"] = body.followup_chain_depth
    if body.followup_used is not None:
        raw["followup_used"] = body.followup_used
    if body.selected_followup_reason is not None and str(body.selected_followup_reason).strip():
        raw["selected_followup_reason"] = str(body.selected_followup_reason).strip()
    elif isinstance(qa_result, dict) and qa_result.get("followup_reason"):
        raw["selected_followup_reason"] = str(qa_result.get("followup_reason") or "").strip() or None

    print(f"[session.stop] request.vision_analysis raw={payload.get('vision_analysis')!r}")

    composed = _compose_result_payload(
        session_id=sid,
        raw_result=raw,
        metrics_items=metrics_items,
        transcript=transcript,
        audio_metrics=audio_metrics,
        ppt_match=ppt_match,
        ppt_match_analysis=ppt_match_analysis,
        qa_result=qa_result,
        summary=None,
    )

    print(f"[session.stop] audio_session_summary={composed.get('audio_session_summary')!r}")
    _vss = composed.get("vision_session_summary")
    _vss_d = _vss if isinstance(_vss, dict) else {}
    print(f"[session.stop] vision_session_summary={composed.get('vision_session_summary')!r}")
    print(
        "[session.stop] vision_session_summary saved_ok "
        f"total_video_duration_sec={_vss_d.get('total_video_duration_sec')} "
        f"duration_source={_vss_d.get('duration_source')!r} "
        f"processed_frames={_vss_d.get('processed_frames')} "
        f"skipped_frames={_vss_d.get('skipped_frames')} "
        f"sampled_mode_used={_vss_d.get('sampled_mode_used')}"
    )
    print(
        f"[session.stop] result_data snapshot vision_analysis keys="
        f"{list((composed.get('vision_analysis') or {}).keys())} "
        f"vision_session_summary present={composed.get('vision_session_summary') is not None}"
    )

    end_time = datetime.utcnow().isoformat()
    _pst = get_ai_provider_status()
    inference_chain_snapshot = {
        "speech_provider": _pst.get("speech_provider"),
        "vision_provider": _pst.get("vision_provider"),
        "document_parser_provider": _pst.get("document_parser_provider"),
        "ascend_base_url_configured": _pst.get("ascend_base_url_configured"),
        "recommended_board_module": _pst.get("recommended_board_module"),
    }
    results[sid] = {
        "session_id": sid,
        "user_id": int(user.id),
        "session_name": composed.get("session_name") or raw["session_name"],
        "scoring_profile": composed.get("scoring_profile"),
        "scoring_profile_label": composed.get("scoring_profile_label"),
        "metrics": composed.get("metrics") or metrics_items,
        "suggestions": composed.get("suggestions"),
        "summary": composed.get("summary"),
        "score_breakdown": composed.get("score_breakdown"),
        "score_explanations": composed.get("score_explanations"),
        "content_breakdown": composed.get("content_breakdown"),
        "qa_breakdown": composed.get("qa_breakdown"),
        "followup_questions": composed.get("followup_questions"),
        "coach_commentary": composed.get("coach_commentary"),
        "improvement_advice": composed.get("improvement_advice"),
        "coach_metadata": composed.get("coach_metadata"),
        "question_provider_kind": composed.get("question_provider_kind"),
        "followup_provider_kind": composed.get("followup_provider_kind"),
        "commentary_provider_kind": composed.get("commentary_provider_kind"),
        "transcript": transcript,
        "audio_metrics": audio_metrics,
        "audio_analysis": composed.get("audio_analysis"),
        "ppt_match": ppt_match,
        "ppt_match_analysis": ppt_match_analysis,
        "qa_result": qa_result,
        "vision_analysis": composed.get("vision_analysis"),
        "audio_session_summary": composed.get("audio_session_summary"),
        "vision_session_summary": composed.get("vision_session_summary"),
        "content_document": content_document,
        "ppt_text_data": ppt_text_data,
        "ppt_match_source": ppt_match_source,
        "qa_source": qa_source,
        "followup_questions_chain": raw.get("followup_questions_chain"),
        "followup_chain_depth": raw.get("followup_chain_depth"),
        "followup_used": raw.get("followup_used"),
        "selected_followup_reason": raw.get("selected_followup_reason"),
        "defense_material_mode": defense_material_mode,
        "training_focus": training_focus,
        "inference_chain_snapshot": inference_chain_snapshot,
    }
    print(
        "[session.stop] result_data bundle ppt_match_source=",
        ppt_match_source or "(none)",
        "has_ppt_match=",
        isinstance(ppt_match, dict) and bool(ppt_match),
        "qa_source=",
        qa_source or "(none)",
        "session_id=",
        sid,
        flush=True,
    )

    rec["status"] = "completed"
    rec["end_time"] = end_time

    _persist_training_record_after_stop(
        db, sid, rec, composed, results[sid], training_focus, end_time, int(user.id)
    )
    print(f"[session.stop] user_id={user.id} session_id={sid}", flush=True)

    return SessionStopResponse(
        session_id=sid,
        status="completed",
        message="训练已结束",
    )
