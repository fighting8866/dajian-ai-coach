from fastapi import APIRouter, HTTPException, Depends, Query
from api.auth import require_user
from api.training_scope import (
    coerce_user_id,
    memory_payload_owned_by,
    training_record_owned_by,
)
from models.result_model import (
    HistoryResponse,
    HistoryItem,
    HistoryDeleteOneResponse,
    HistoryClearInvalidResponse,
    MetricItem,
    SuggestionItem,
    ValidTrainingOverview,
)
from services.mock_store import sessions, results
from models.training_record import TrainingRecord
from models.user_model import User
from database.db import get_db
from sqlalchemy.orm import Session
from datetime import datetime
from services.scoring_service import ScoringService
from services.commentary_generation_service import (
    apply_training_focus_commentary_overlay,
    finalize_coach_bundle_providers,
    generate_coach_bundle,
)
from configs.scoring_profiles import get_scoring_profile
import json
import math

router = APIRouter()
scoring_service = ScoringService()


def _purge_training_session_storage(session_id: str, db: Session) -> dict:
    """删除单条训练在 DB 与内存 mock_store 中的痕迹（供历史管理接口使用）。"""
    sid = str(session_id or "").strip()
    had_db_record = False
    removed_results = False
    removed_sessions = False
    try:
        row = db.query(TrainingRecord).filter(TrainingRecord.session_id == sid).first()
        if row is not None:
            had_db_record = True
            db.delete(row)
            db.commit()
    except Exception as e:
        db.rollback()
        print(f"[history.purge] db delete failed: {e!r} session_id={sid}", flush=True)
    if sid in results:
        del results[sid]
        removed_results = True
    if sid in sessions:
        del sessions[sid]
        removed_sessions = True
    return {
        "had_db_record": had_db_record,
        "removed_results": removed_results,
        "removed_sessions": removed_sessions,
    }


def _log_result_api_ppt_fields(response_payload: dict, session_id: str) -> None:
    pm = response_payload.get("ppt_match")
    psrc = response_payload.get("ppt_match_source")
    has_pm = isinstance(pm, dict) and pm.get("page_index") is not None
    print(
        f"[result.api] has_ppt_match={has_pm} ppt_match_source={psrc!r} ppt_match={pm!r} "
        f"session_id={session_id}",
        flush=True,
    )


def _as_float(v, default=0.0):
    try:
        if v is None:
            return default
        return float(v)
    except Exception:
        return default


def _as_bool(v, default=True):
    if v is None:
        return default
    if isinstance(v, bool):
        return v
    if isinstance(v, (int, float)):
        return bool(v)
    s = str(v).strip().lower()
    if s in {"true", "1", "yes", "y", "on"}:
        return True
    if s in {"false", "0", "no", "n", "off"}:
        return False
    return default


def _normalize_training_focus_out(val: object) -> str:
    """与 session/training 对齐：仅允许五类取值，否则视为常规训练 none。"""
    s = str(val or "").strip().lower()
    if s in ("language", "posture", "qa", "content", "none"):
        return s
    return "none"


def _pick_training_focus_for_session(
    session_id: str,
    raw_stored: dict | None,
    db_record: object | None = None,
) -> object | None:
    """
    解析本轮 training_focus（不做归一化）：
    1) 内存 results（与当前 stop 写入一致，优先于库里的旧行）
    2) training_records.training_focus 列
    3) metrics_json 包内 training_focus
    """
    mem = results.get(session_id)
    if isinstance(mem, dict) and mem.get("training_focus") is not None:
        return mem.get("training_focus")
    if db_record is not None:
        col = getattr(db_record, "training_focus", None)
        if col is not None and str(col).strip() != "":
            return col
    if isinstance(raw_stored, dict) and raw_stored.get("training_focus") is not None:
        return raw_stored.get("training_focus")
    return None


def _compute_recommended_training_focus(
    score_breakdown: dict | None,
    summary: dict | None,
    defense_material_mode: str,
) -> str | None:
    """
    规则版下一轮专项训练推荐：在有效模块中取得分最低者；无有效模块时从 summary.weakest_aspect 文案回退。
    返回值：language | posture | content | qa；不改评分，仅辅助前端入口。
    """
    dm = str(defense_material_mode or "with_ppt").strip().lower()
    with_ppt = dm != "without_ppt"
    bd = score_breakdown if isinstance(score_breakdown, dict) else {}
    vm = bd.get("valid_modules") if isinstance(bd.get("valid_modules"), dict) else {}
    modules = bd.get("modules") if isinstance(bd.get("modules"), dict) else {}
    key_rank = {"language": 0, "posture": 1, "content": 2, "qa": 3}
    candidates: list[tuple[str, float]] = []
    for key in ("language", "posture", "qa"):
        if vm.get(key) and isinstance(modules.get(key), dict):
            try:
                sc = float(modules[key].get("score", 0.0))
            except (TypeError, ValueError):
                sc = 0.0
            candidates.append((key, sc))
    if with_ppt and vm.get("content") and isinstance(modules.get("content"), dict):
        try:
            sc = float(modules["content"].get("score", 0.0))
        except (TypeError, ValueError):
            sc = 0.0
        candidates.append(("content", sc))
    if candidates:
        candidates.sort(key=lambda x: (x[1], key_rank.get(x[0], 9)))
        return candidates[0][0]

    wa = ""
    if isinstance(summary, dict):
        wa = str(summary.get("weakest_aspect") or "")
    label_map = (
        ("语言表达", "language"),
        ("仪态表现", "posture"),
        ("内容讲解", "content"),
        ("问答表现", "qa"),
    )
    for label, key in label_map:
        if label in wa:
            if key == "content" and not with_ppt:
                continue
            return key
    return None


def _resolve_session_source_fields(
    raw_result: dict | None,
    ppt_match: dict | None,
    qa_result: dict | None,
) -> tuple[str | None, str | None]:
    """顶层 ppt_match_source / qa_source 优先，否则从 ppt_match.match_source、qa_result.qa_source 回退。"""
    base = raw_result if isinstance(raw_result, dict) else {}

    # 与 ppt_match 卡片一致：优先采用对象内 match_source（避免顶层字段与 body 不一致时误判来源）
    psrc = None
    if isinstance(ppt_match, dict):
        ms = ppt_match.get("match_source")
        if isinstance(ms, str) and ms.strip():
            psrc = ms.strip()
    if not psrc:
        psrc = base.get("ppt_match_source")
        if isinstance(psrc, str):
            psrc = psrc.strip() or None
        elif psrc is not None:
            psrc = str(psrc).strip() or None
        else:
            psrc = None

    qsrc = base.get("qa_source")
    if isinstance(qsrc, str):
        qsrc = qsrc.strip() or None
    elif qsrc is not None:
        qsrc = str(qsrc).strip() or None
    else:
        qsrc = None
    if not qsrc and isinstance(qa_result, dict):
        qs = qa_result.get("qa_source")
        if isinstance(qs, str) and qs.strip():
            qsrc = qs.strip()

    return psrc, qsrc


def _coach_pipeline_av_flags(
    raw_result: dict | None,
    metrics_items: list | None,
    transcript: str | None,
) -> tuple[bool | None, bool | None]:
    """供点评链判断语言/仪态样本是否足以形成分析（与评分侧口径对齐，不单写 technical invalid）。"""
    raw = raw_result if isinstance(raw_result, dict) else {}
    audio_analysis = raw.get("audio_analysis") if isinstance(raw.get("audio_analysis"), dict) else None
    av: bool | None = None
    if isinstance(audio_analysis, dict) and "audio_valid" in audio_analysis:
        av = _as_bool(audio_analysis.get("audio_valid"), False)
    else:
        tr = transcript if transcript is not None else raw.get("transcript")
        if isinstance(tr, str) and tr.strip():
            av = True
        elif tr is not None:
            av = False
    vs = _extract_vision_state(raw, metrics_items or [])
    vv_raw = vs.get("vision_valid")
    vv: bool | None
    if isinstance(vv_raw, bool):
        vv = vv_raw
    elif vv_raw is None:
        vv = None
    else:
        vv = _as_bool(vv_raw, True)
    return av, vv


def _metrics_list_to_dict(metrics_items: list) -> dict:
    name_to_key = {
        "语速": "speech_rate",
        "停顿次数": "pause_count",
        "平均停顿时长": "avg_pause_sec",
        "口头禅次数": "filler_count",
        "正视前方比例": "forward_gaze_ratio",
        "低头率": "downward_head_ratio",
        "姿态稳定度": "posture_stability",
    }
    out = {}
    for m in metrics_items or []:
        try:
            name = getattr(m, "name", None) or (m.get("name") if isinstance(m, dict) else None)
            val = getattr(m, "value", None) if not isinstance(m, dict) else m.get("value")
            if not name or name not in name_to_key:
                continue
            key = name_to_key[name]
            out[key] = _as_float(val, val)
        except Exception:
            continue
    return out


def _extract_vision_state(raw_result: dict | None, metrics_items: list | None) -> dict:
    raw = raw_result or {}
    vision_analysis = raw.get("vision_analysis") if isinstance(raw, dict) else None
    if isinstance(vision_analysis, dict):
        return {
            "vision_valid": _as_bool(vision_analysis.get("vision_valid"), True),
            "vision_message": str(vision_analysis.get("vision_message") or ""),
            "vision_debug_source": str(vision_analysis.get("vision_debug_source") or ""),
            "vision_debug_provider": str(vision_analysis.get("vision_debug_provider") or ""),
            "vision_debug_request_id": str(vision_analysis.get("vision_debug_request_id") or ""),
        }

    if isinstance(raw, dict) and (
        "vision_valid" in raw
        or "vision_message" in raw
        or "vision_debug_source" in raw
        or "vision_debug_provider" in raw
        or "vision_debug_request_id" in raw
    ):
        return {
            "vision_valid": _as_bool(raw.get("vision_valid"), True),
            "vision_message": str(raw.get("vision_message") or ""),
            "vision_debug_source": str(raw.get("vision_debug_source") or ""),
            "vision_debug_provider": str(raw.get("vision_debug_provider") or ""),
            "vision_debug_request_id": str(raw.get("vision_debug_request_id") or ""),
        }

    metrics = metrics_items or []
    valid_marker = None
    message_marker = ""
    debug_source = ""
    debug_provider = ""
    debug_request_id = ""
    for m in metrics:
        if isinstance(m, dict):
            name = m.get("name")
            value = m.get("value")
        else:
            name = getattr(m, "name", None)
            value = getattr(m, "value", None)
        if name == "视觉分析有效性":
            valid_marker = str(value or "")
        elif name == "视觉分析提示":
            message_marker = str(value or "")
        elif name == "视觉调试来源":
            debug_source = str(value or "")
        elif name == "视觉调试提供者":
            debug_provider = str(value or "")
        elif name == "视觉调试请求ID":
            debug_request_id = str(value or "")

    if valid_marker:
        is_valid = str(valid_marker).strip() not in {"无效", "false", "False", "0"}
        return {
            "vision_valid": is_valid,
            "vision_message": message_marker if not is_valid else "",
            "vision_debug_source": debug_source,
            "vision_debug_provider": debug_provider,
            "vision_debug_request_id": debug_request_id,
        }

    return {
        "vision_valid": True,
        "vision_message": "",
        "vision_debug_source": debug_source,
        "vision_debug_provider": debug_provider,
        "vision_debug_request_id": debug_request_id,
    }


def _extract_vision_metrics(raw_result: dict | None, metrics_items: list | None) -> dict:
    raw = raw_result or {}
    vision_analysis = raw.get("vision_analysis") if isinstance(raw, dict) else None
    if isinstance(vision_analysis, dict):
        return {
            "forward_gaze_ratio": vision_analysis.get("forward_gaze_ratio"),
            "downward_head_ratio": vision_analysis.get("downward_head_ratio"),
            "posture_stability": vision_analysis.get("posture_stability"),
        }

    if isinstance(raw, dict):
        has_top_level = any(
            k in raw for k in ("forward_gaze_ratio", "downward_head_ratio", "posture_stability")
        )
        if has_top_level:
            return {
                "forward_gaze_ratio": raw.get("forward_gaze_ratio"),
                "downward_head_ratio": raw.get("downward_head_ratio"),
                "posture_stability": raw.get("posture_stability"),
            }

    metrics = metrics_items or []
    mapped = {
        "forward_gaze_ratio": None,
        "downward_head_ratio": None,
        "posture_stability": None,
    }
    name_to_key = {
        "正视前方比例": "forward_gaze_ratio",
        "低头率": "downward_head_ratio",
        "姿态稳定度": "posture_stability",
    }
    for m in metrics:
        if isinstance(m, dict):
            name = m.get("name")
            value = m.get("value")
        else:
            name = getattr(m, "name", None)
            value = getattr(m, "value", None)
        key = name_to_key.get(name)
        if key is None:
            continue
        mapped[key] = _as_float(value, value)
    return mapped


def _build_summary(total_score: float, language_score: float, posture_score: float, metrics_dict: dict) -> dict:
    total = _as_float(total_score, 0.0)
    lang = _as_float(language_score, 0.0)
    post = _as_float(posture_score, 0.0)
    metrics = metrics_dict or {}
    if total >= 85:
        overall_comment = "整体表现优秀，已经具备较好的答辩表达能力"
    elif total >= 70:
        overall_comment = "整体表现良好，但还有进一步优化空间"
    else:
        overall_comment = "当前表达仍有明显提升空间，建议针对薄弱项重点训练"

    aspects = []
    if lang >= 40:
        aspects.append("语言表达")
    if post >= 40:
        aspects.append("仪态表现")

    sr = _as_float(metrics.get("speech_rate"), None)
    if sr is not None and 180 <= sr <= 260:
        aspects.append("语速控制")
    avg_pause = _as_float(metrics.get("avg_pause_sec"), None)
    pause_count = _as_float(metrics.get("pause_count"), None)
    if avg_pause is not None and pause_count is not None and 0.5 <= avg_pause <= 1.5 and 3 <= pause_count <= 15:
        aspects.append("停顿节奏")
    filler = _as_float(metrics.get("filler_count"), None)
    if filler is not None and filler <= 2:
        aspects.append("口头禅控制")
    gaze = _as_float(metrics.get("forward_gaze_ratio"), None)
    if gaze is not None and gaze >= 0.7:
        aspects.append("目光交流")
    head = _as_float(metrics.get("downward_head_ratio"), None)
    if head is not None and head < 0.1:
        aspects.append("抬头状态")
    stab = _as_float(metrics.get("posture_stability"), None)
    if stab is not None and stab >= 0.8:
        aspects.append("姿态稳定")
    strongest_aspect = "整体表现均衡" if not aspects else f"{aspects[0]}较好"

    weak_aspects = []
    if sr is not None and (sr > 300 or sr < 140):
        weak_aspects.append("语速")
    if avg_pause is not None and pause_count is not None and not (0.5 <= avg_pause <= 1.5 and 3 <= pause_count <= 15):
        weak_aspects.append("停顿节奏")
    if filler is not None and filler > 5:
        weak_aspects.append("口头禅")
    if gaze is not None and gaze < 0.5:
        weak_aspects.append("正视前方比例")
    if head is not None and head >= 0.2:
        weak_aspects.append("低头率")
    if stab is not None and stab < 0.65:
        weak_aspects.append("姿态稳定度")
    weakest_aspect = "无明显短板" if not weak_aspects else f"{weak_aspects[0]}需要改进"

    if weak_aspects:
        if "语速" in weak_aspects:
            training_tip = "建议练习控制语速，保持在180-260字/分钟"
        elif "停顿节奏" in weak_aspects:
            training_tip = "建议练习自然停顿，控制停顿时长和次数"
        elif "口头禅" in weak_aspects:
            training_tip = "建议注意减少口头禅的使用"
        elif "正视前方比例" in weak_aspects:
            training_tip = "建议增加与观众的眼神交流"
        elif "低头率" in weak_aspects:
            training_tip = "建议保持抬头状态，减少低头频率"
        else:
            training_tip = "建议加强姿态稳定性训练"
    else:
        training_tip = "继续保持练习，进一步提升演讲自信度"

    return {
        "overall_comment": overall_comment,
        "strongest_aspect": strongest_aspect,
        "weakest_aspect": weakest_aspect,
        "training_tip": training_tip,
    }


def _normalize_summary(summary: dict, total_score: float, language_score: float, posture_score: float, metrics_dict: dict) -> dict:
    base = _build_summary(total_score, language_score, posture_score, metrics_dict)
    if not isinstance(summary, dict):
        return base
    merged = {**base, **summary}
    for k in ("overall_comment", "strongest_aspect", "weakest_aspect", "training_tip"):
        v = merged.get(k)
        if v is None or str(v).strip() == "":
            merged[k] = base[k]
    return merged


def _materialize_suggestions(items: list | None) -> list[dict]:
    out = []
    for s in items or []:
        if hasattr(s, "model_dump"):
            out.append(s.model_dump())
        elif isinstance(s, dict):
            out.append({"category": s.get("category", ""), "content": s.get("content", "")})
        else:
            out.append({"category": "", "content": str(s)})
    return out


def _build_scoring_fields(
    session_id: str,
    raw_result: dict,
    metrics_items: list,
    transcript: str | None,
    audio_metrics: dict | None,
    ppt_match: dict | None,
    qa_result: dict | None,
    ppt_match_analysis: dict | None = None,
    content_document: dict | None = None,
):
    vision_state = _extract_vision_state(raw_result, metrics_items)
    vision_metrics = _extract_vision_metrics(raw_result, metrics_items)
    audio_analysis = raw_result.get("audio_analysis") if isinstance(raw_result.get("audio_analysis"), dict) else None
    resolved_audio_metrics = audio_metrics or (audio_analysis if isinstance(audio_analysis, dict) else None) or {}
    resolved_audio_valid = None
    if isinstance(audio_analysis, dict) and "audio_valid" in audio_analysis:
        resolved_audio_valid = _as_bool(audio_analysis.get("audio_valid"), False)
    elif transcript:
        resolved_audio_valid = True
    else:
        resolved_audio_valid = False

    pam = ppt_match_analysis if ppt_match_analysis is not None else raw_result.get("ppt_match_analysis")
    pam = pam if isinstance(pam, dict) else None
    cd = content_document if content_document is not None else raw_result.get("content_document")
    cd = cd if isinstance(cd, dict) else None
    _dm_raw = raw_result.get("defense_material_mode") if isinstance(raw_result, dict) else None
    _dm_norm = "without_ppt" if str(_dm_raw or "").strip().lower() == "without_ppt" else "with_ppt"
    score_result = scoring_service.score_session(
        session_id=session_id,
        metrics=_metrics_list_to_dict(metrics_items),
        audio_analysis=audio_analysis,
        audio_metrics=resolved_audio_metrics,
        transcript=transcript,
        audio_valid=resolved_audio_valid,
        vision_analysis={**vision_metrics, **vision_state},
        vision_valid=vision_state["vision_valid"],
        ppt_match=ppt_match,
        qa_result=qa_result,
        scoring_profile=raw_result.get("scoring_profile"),
        ppt_match_analysis=pam,
        content_document=cd,
        defense_material_mode=_dm_norm,
    )
    return score_result, vision_state, vision_metrics


def _resolve_coach_payload(
    raw_result: dict,
    score_result: dict,
    ppt_match: dict | None,
    ppt_match_analysis: dict | None,
    qa_result: dict | None,
    content_document: dict | None,
    metrics_items: list | None = None,
    transcript: str | None = None,
) -> dict:
    """优先使用 stop 时落库的教练输出；缺 overall_commentary 的旧缓存会按当前规则补全点评链。"""
    raw = raw_result if isinstance(raw_result, dict) else {}
    meta = raw.get("coach_metadata")
    oc0 = raw.get("overall_commentary")
    has_chain = isinstance(oc0, str) and oc0.strip()

    def _list_key(k: str) -> list:
        v = raw.get(k)
        return v if isinstance(v, list) else []

    if isinstance(meta, dict) and meta.get("version") and has_chain:
        adv = raw.get("improvement_advice")
        if not isinstance(adv, list):
            adv = _list_key("next_round_advice")
        elif not adv:
            adv = _list_key("next_round_advice")
        _cgm = raw.get("commentary_generation_meta")
        if not isinstance(_cgm, dict) and isinstance(meta, dict):
            _cgm = meta.get("commentary_generation_meta")
        _cfb = raw.get("commentary_fallback_to_rule")
        if _cfb is None and isinstance(meta, dict):
            _cfb = meta.get("commentary_fallback_to_rule")
        cached = {
            "followup_questions": raw.get("followup_questions")
            if isinstance(raw.get("followup_questions"), list)
            else [],
            "overall_commentary": oc0.strip(),
            "strengths": _list_key("strengths"),
            "weaknesses": _list_key("weaknesses"),
            "next_round_advice": _list_key("next_round_advice"),
            "coach_commentary": raw.get("coach_commentary") or oc0.strip(),
            "improvement_advice": adv,
            "coach_metadata": dict(meta),
            "commentary_generation_meta": _cgm if isinstance(_cgm, dict) else {},
            "commentary_fallback_to_rule": bool(_cfb) if _cfb is not None else False,
        }
        return finalize_coach_bundle_providers(cached, qa_result=qa_result)

    cd = content_document if isinstance(content_document, dict) else raw.get("content_document")
    cd = cd if isinstance(cd, dict) else None
    psrc, qsrc = _resolve_session_source_fields(raw, ppt_match, qa_result)
    av, vv = _coach_pipeline_av_flags(raw, metrics_items, transcript)
    built = generate_coach_bundle(
        scoring_profile=score_result.get("scoring_profile") or raw.get("scoring_profile"),
        scoring_profile_label=score_result.get("scoring_profile_label") or raw.get("scoring_profile_label"),
        score_explanations=score_result.get("score_explanations") or raw.get("score_explanations"),
        score_breakdown=score_result.get("score_breakdown") or raw.get("score_breakdown"),
        content_breakdown=score_result.get("content_breakdown") or raw.get("content_breakdown"),
        qa_breakdown=score_result.get("qa_breakdown") or raw.get("qa_breakdown"),
        qa_result=qa_result if isinstance(qa_result, dict) else raw.get("qa_result"),
        content_document=cd,
        ppt_match=ppt_match if isinstance(ppt_match, dict) else raw.get("ppt_match"),
        ppt_match_analysis=ppt_match_analysis
        if isinstance(ppt_match_analysis, dict)
        else raw.get("ppt_match_analysis"),
        total_score=score_result.get("total_score"),
        audio_valid=av,
        vision_valid=vv,
        ppt_match_source=psrc,
        qa_source=qsrc,
    )
    fq_stored = raw.get("followup_questions")
    if isinstance(fq_stored, list) and fq_stored:
        built["followup_questions"] = fq_stored
    if isinstance(meta, dict) and meta.get("version") and not has_chain:
        merged_meta = {**meta, **(built.get("coach_metadata") or {})}
        built["coach_metadata"] = merged_meta
    return finalize_coach_bundle_providers(built, qa_result=qa_result)


AUDIO_SESSION_SUMMARY_FIELDS = (
    "merged_transcript",
    "total_audio_duration_sec",
    "transcribed_chunks",
    "skipped_chunks",
    "dropped_dirty_chunks",
    "total_chunks",
    "chunked_mode_used",
    "audio_metrics_scope",
)
VISION_SESSION_SUMMARY_FIELDS = (
    "processed_frames",
    "skipped_frames",
    "total_video_duration_sec",
    "duration_source",
    "sampled_mode_used",
    "sampled_fps",
    "vision_metrics_scope",
    "forward_gaze_ratio",
    "downward_head_ratio",
    "posture_stability",
    "vision_valid",
    "vision_message",
)
# 写入 vision_analysis 供时长回填与排障（原仅合并 VISION_SESSION_SUMMARY_FIELDS 会丢掉 total_frames / vision_original_fps）
_VISION_ANALYSIS_METADATA_KEYS = (
    "total_frames",
    "valid_detection_frames",
    "vision_original_fps",
    "vision_sampled_fps",
    "vision_skipped_frames",
    "vision_analysis_elapsed_ms",
    "vision_sampled_mode_used",
)


def _pick_audio_session_summary(raw_result: dict, audio_analysis_payload: dict | None) -> dict | None:
    ss = raw_result.get("audio_session_summary") if isinstance(raw_result, dict) else None
    if isinstance(ss, dict) and ss:
        out = dict(ss)
        out.setdefault("session_summary_version", "v2_phase2")
        return out
    ad = audio_analysis_payload if isinstance(audio_analysis_payload, dict) else {}
    picked = {k: ad[k] for k in AUDIO_SESSION_SUMMARY_FIELDS if k in ad}
    if not picked:
        return None
    picked["session_summary_version"] = "v2_phase2"
    return picked


def _vision_summary_alias_fill(target: dict, source: dict) -> None:
    """把板侧/前端的 vision_* 别名写入规范字段，供长时摘要与 _pick 使用（不覆盖已有非 None 值）。"""
    if not isinstance(target, dict) or not isinstance(source, dict):
        return
    pairs = (
        ("skipped_frames", "vision_skipped_frames"),
        ("processed_frames", "valid_detection_frames"),
        ("sampled_fps", "vision_sampled_fps"),
        ("sampled_mode_used", "vision_sampled_mode_used"),
    )
    for canon, alt in pairs:
        cur = target.get(canon)
        if cur is None and alt in source and source.get(alt) is not None:
            target[canon] = source[alt]


def _vision_summary_duration_usable(v: object) -> bool:
    try:
        x = float(v)
    except (TypeError, ValueError):
        return False
    return math.isfinite(x) and x > 0.0


def _backfill_vision_summary_duration(picked: dict, vd: dict) -> None:
    """避免 summary 出现 processed/skip 有值但 total_video_duration_sec 为 0；不覆盖已存在的正时长。"""
    pf = int(picked.get("processed_frames") or vd.get("processed_frames") or 0)
    sk = int(picked.get("skipped_frames") or vd.get("skipped_frames") or 0)
    if pf <= 0 and sk <= 0:
        return
    if _vision_summary_duration_usable(picked.get("total_video_duration_sec")):
        return

    def _native_fps() -> float:
        for key in ("vision_original_fps", "sampled_fps", "vision_sampled_fps"):
            raw = vd.get(key)
            if raw is None:
                continue
            try:
                fps = float(raw)
            except (TypeError, ValueError):
                continue
            if math.isfinite(fps) and 0.5 <= fps <= 240.0:
                return fps
        return 30.0

    fps = _native_fps()
    tf = vd.get("total_frames")
    if tf is not None:
        try:
            tfn = int(tf)
        except (TypeError, ValueError):
            tfn = 0
        if tfn > 0:
            picked["total_video_duration_sec"] = round(float(tfn) / fps, 3)
            picked["duration_source"] = "backend_backfill_total_frames_div_fps"
            return
    # 与板端主循环一致：已解码帧数 ≈ processed + skipped，用容器原始 fps 估时长（优于 0）
    picked["total_video_duration_sec"] = round(float(pf + sk) / fps, 3)
    picked["duration_source"] = "backend_backfill_pf_plus_sk_div_fps"


def _pick_vision_session_summary(raw_result: dict, vision_analysis_payload: dict | None) -> dict | None:
    """合并 vision_analysis 中的长时字段与 raw 中已存的 vision_session_summary，避免仅有稀疏 ss 时丢失时长/帧数。"""
    vd = vision_analysis_payload if isinstance(vision_analysis_payload, dict) else {}
    picked: dict = {}
    for k in VISION_SESSION_SUMMARY_FIELDS:
        if k in vd and vd[k] is not None:
            picked[k] = vd[k]
    ss = raw_result.get("vision_session_summary") if isinstance(raw_result, dict) else None
    if isinstance(ss, dict):
        for k, v in ss.items():
            if v is None:
                continue
            if k == "total_video_duration_sec":
                try:
                    incoming = float(v)
                except (TypeError, ValueError):
                    picked[k] = v
                    continue
                if incoming <= 0 and _vision_summary_duration_usable(picked.get("total_video_duration_sec")):
                    continue
            picked[k] = v
    if not picked:
        return None
    picked.setdefault("session_summary_version", "v2_phase2")
    _backfill_vision_summary_duration(picked, vd)
    return picked


def _parse_metrics_json_blob(metrics_json_str: str | None) -> tuple[list, dict]:
    """兼容旧版 metrics 列表与新版 { metric_items, score_explanations, ... } 包装。"""
    if not metrics_json_str:
        return [], {}
    try:
        parsed = json.loads(metrics_json_str)
    except Exception:
        return [], {}
    if isinstance(parsed, dict) and "metric_items" in parsed:
        stored = {
            k: parsed[k]
            for k in (
                "score_explanations",
                "score_breakdown",
                "scoring_profile",
                "scoring_profile_label",
                "content_breakdown",
                "content_document",
                "qa_breakdown",
                "followup_questions",
                "overall_commentary",
                "strengths",
                "weaknesses",
                "next_round_advice",
                "coach_commentary",
                "improvement_advice",
                "coach_metadata",
                "question_provider_kind",
                "followup_provider_kind",
                "commentary_provider_kind",
                "commentary_generation_meta",
                "commentary_fallback_to_rule",
                "audio_session_summary",
                "vision_session_summary",
                "defense_material_mode",
                "recommended_training_focus",
                "training_focus",
                "inference_chain_snapshot",
            )
            if parsed.get(k) is not None
        }
        items = parsed.get("metric_items") or []
        return items if isinstance(items, list) else [], stored
    if isinstance(parsed, list):
        return parsed, {}
    return [], {}


def _count_score_breakdown_valid_modules(breakdown: dict | None) -> int:
    """score_breakdown.valid_modules 中启用的模块数量（language/posture/content/qa）。"""
    if not isinstance(breakdown, dict):
        return 0
    vm = breakdown.get("valid_modules")
    if not isinstance(vm, dict):
        return 0
    keys = ("language", "posture", "content", "qa")
    return sum(1 for k in keys if vm.get(k))


def _compute_training_validity(
    *,
    total_score: float,
    score_breakdown: dict | None,
    audio_valid: bool | None,
    vision_valid: bool | None,
) -> tuple[bool, str]:
    """
    无效训练记录收口 V1（轻量规则，不改评分）：
    - 语音、视觉均明确无效 -> 无效
    - 总分近 0 且有效模块为空或极少 -> 无效
    - 其余：至少一个有效评分模块则视为有效；无 breakdown 时总分>0 视为兼容有效
    """
    ts = float(total_score or 0.0)
    n_valid = _count_score_breakdown_valid_modules(score_breakdown)

    if audio_valid is False and vision_valid is False:
        return False, "语音与视觉均未形成有效结果"

    if ts <= 0.01:
        if n_valid == 0:
            return False, "总分为 0 且无有效评分模块"
        if n_valid <= 1:
            return False, "总分为 0 且有效评分模块过少"

    if n_valid >= 1:
        return True, ""

    if ts > 0.01:
        return True, ""

    return False, "未启用有效评分模块或数据缺失"


def _apply_training_validity_to_payload(session_id: str, payload: dict) -> None:
    """写入 training_valid / invalid_reason_summary，并打 result.api 日志。"""
    if not isinstance(payload, dict):
        return
    bd = payload.get("score_breakdown") if isinstance(payload.get("score_breakdown"), dict) else None
    aa = payload.get("audio_analysis") if isinstance(payload.get("audio_analysis"), dict) else {}
    audio_v: bool | None = None
    if isinstance(aa, dict) and "audio_valid" in aa:
        audio_v = _as_bool(aa.get("audio_valid"), False)
    vv_raw = payload.get("vision_valid")
    vision_b: bool | None = None
    if vv_raw is not None:
        vision_b = _as_bool(vv_raw, True)
    tv, reason = _compute_training_validity(
        total_score=float(payload.get("total_score") or 0.0),
        score_breakdown=bd,
        audio_valid=audio_v,
        vision_valid=vision_b,
    )
    payload["training_valid"] = tv
    payload["invalid_reason_summary"] = "" if tv else reason
    print(f"[result.api] training_valid={tv} session_id={session_id}", flush=True)
    print(f"[result.api] invalid_reason_summary={reason!r} session_id={session_id}", flush=True)


def _pick_module_score(breakdown: dict, key: str) -> float | None:
    """仅当模块有效时返回分数；无效或缺失时返回 None（避免把 0 当作真实得分）。"""
    if not isinstance(breakdown, dict):
        return None
    valid_modules = breakdown.get("valid_modules")
    modules = breakdown.get("modules")
    if not isinstance(valid_modules, dict) or not isinstance(modules, dict):
        return None
    if not valid_modules.get(key):
        return None
    mod = modules.get(key)
    if not isinstance(mod, dict):
        return None
    try:
        return float(mod.get("score", 0.0))
    except Exception:
        return None


def _merge_stored_metrics(
    metrics_json_str: str | None,
    in_memory: dict | None,
) -> dict:
    """合并 DB metrics_json 与内存结果中的评分元数据，内存优先补全缺失字段。"""
    _, stored = _parse_metrics_json_blob(metrics_json_str)
    out = dict(stored) if stored else {}
    mem = in_memory if isinstance(in_memory, dict) else {}
    for k in (
        "score_breakdown",
        "scoring_profile",
        "scoring_profile_label",
        "content_breakdown",
        "content_document",
        "qa_breakdown",
        "followup_questions",
        "overall_commentary",
        "strengths",
        "weaknesses",
        "next_round_advice",
        "coach_commentary",
        "improvement_advice",
        "coach_metadata",
        "question_provider_kind",
        "followup_provider_kind",
        "commentary_provider_kind",
        "commentary_generation_meta",
        "commentary_fallback_to_rule",
        "ppt_match_source",
        "qa_source",
        "ppt_match",
        "qa_result",
        "followup_questions_chain",
        "followup_chain_depth",
        "followup_used",
        "selected_followup_reason",
        "defense_material_mode",
        "recommended_training_focus",
        "training_focus",
    ):
        if out.get(k) is None and mem.get(k) is not None:
            out[k] = mem[k]
    return out


def _normalize_merged_defense_material_mode(raw: object) -> str | None:
    """metrics / payload 中的 defense_material_mode -> with_ppt | without_ppt；无法识别则 None。"""
    if raw is None:
        return None
    s = str(raw).strip().lower()
    if s == "without_ppt":
        return "without_ppt"
    if s in ("with_ppt", "with-ppt", "withppt"):
        return "with_ppt"
    return None


def _compose_history_item(
    *,
    session_id: str,
    session_name: str,
    timestamp: str,
    created_at: str | None,
    total_score: float,
    language_col: float | None,
    posture_col: float | None,
    metrics_json_str: str | None,
    in_memory: dict | None,
    record_scoring_profile: str | None = None,
    record_scoring_profile_label: str | None = None,
    record_training_focus: str | None = None,
) -> HistoryItem:
    merged = _merge_stored_metrics(metrics_json_str, in_memory)
    if isinstance(in_memory, dict) and in_memory.get("training_focus") is not None:
        merged["training_focus"] = in_memory["training_focus"]
    elif merged.get("training_focus") is None and record_training_focus is not None:
        merged["training_focus"] = record_training_focus
    breakdown = merged.get("score_breakdown")
    scoring_profile = merged.get("scoring_profile")
    if isinstance(scoring_profile, str):
        profile_str: str | None = scoring_profile
    else:
        profile_str = record_scoring_profile if isinstance(record_scoring_profile, str) else None

    pl_raw = merged.get("scoring_profile_label")
    profile_label_str: str | None = pl_raw if isinstance(pl_raw, str) else None
    if not profile_label_str and isinstance(record_scoring_profile_label, str):
        profile_label_str = record_scoring_profile_label
    if not profile_label_str and profile_str:
        profile_label_str = get_scoring_profile(profile_str).get("label")

    language_score: float | None
    posture_score: float | None
    content_score: float | None
    qa_score: float | None
    audio_valid: bool | None
    vision_valid: bool | None

    if isinstance(breakdown, dict) and isinstance(breakdown.get("valid_modules"), dict):
        language_score = _pick_module_score(breakdown, "language")
        posture_score = _pick_module_score(breakdown, "posture")
        content_score = _pick_module_score(breakdown, "content")
        qa_score = _pick_module_score(breakdown, "qa")
        vm = breakdown["valid_modules"]
        audio_valid = bool(vm.get("language")) if "language" in vm else None
        vision_valid = bool(vm.get("posture")) if "posture" in vm else None
    else:
        if language_col is not None:
            language_score = float(language_col)
        else:
            language_score = None
        if posture_col is not None:
            posture_score = float(posture_col)
        else:
            posture_score = None
        content_score = None
        qa_score = None
        audio_valid = None
        vision_valid = None

    ts_created = created_at or timestamp
    training_focus_hist = _normalize_training_focus_out(merged.get("training_focus"))

    bd_for_valid = breakdown if isinstance(breakdown, dict) else None
    tv, inv_reason = _compute_training_validity(
        total_score=float(total_score or 0.0),
        score_breakdown=bd_for_valid,
        audio_valid=audio_valid,
        vision_valid=vision_valid,
    )

    dm_norm = _normalize_merged_defense_material_mode(merged.get("defense_material_mode"))
    if dm_norm is None and isinstance(in_memory, dict):
        dm_norm = _normalize_merged_defense_material_mode(in_memory.get("defense_material_mode"))

    return HistoryItem(
        session_id=session_id,
        session_name=session_name,
        timestamp=timestamp,
        created_at=ts_created,
        total_score=float(total_score or 0.0),
        language_score=language_score,
        posture_score=posture_score,
        content_score=content_score,
        qa_score=qa_score,
        scoring_profile=profile_str,
        scoring_profile_label=profile_label_str,
        defense_material_mode=dm_norm,
        audio_valid=audio_valid,
        vision_valid=vision_valid,
        training_focus=training_focus_hist,
        training_valid=tv,
        invalid_reason_summary=inv_reason if not tv else None,
    )


# --- 专项训练成效回看 V1（规则统计）---
_FOCUS_SCORE_FIELD = {
    "language": "language_score",
    "posture": "posture_score",
    "content": "content_score",
    "qa": "qa_score",
}

_FOCUS_LABEL_CN = {
    "language": "语言",
    "posture": "仪态",
    "content": "内容",
    "qa": "问答",
}

_FOCUS_LABEL_FULL_CN = {
    "language": "语言表达专项",
    "posture": "仪态表现专项",
    "content": "内容讲解专项",
    "qa": "问答表现专项",
}


def _normalize_optional_focus_key(raw: object) -> str | None:
    if raw is None:
        return None
    s = str(raw).strip().lower()
    if s in ("language", "posture", "qa", "content"):
        return s
    return None


def _round_focus_outcome_line(kind: str) -> str:
    if kind == "up":
        return "综合来看，这一轮同专项有看得见的进步。"
    if kind == "flat":
        return "综合来看，这一轮同专项和以往基本持平。"
    if kind == "volatile":
        return "综合来看，这一轮同专项起伏比较明显，适合放慢节奏、稳住发挥。"
    return "综合来看，同专项记录还偏少，先把几次训练攒起来再下结论。"


_VS_DELTA_THRESHOLD = 2.0


def _focus_vs_previous_short(scores: list[float]) -> str:
    """与上一条同专项核心分相比的轻量标签（阈值与 Result 一致）。"""
    if len(scores) < 2:
        return "暂无足够历史"
    d = scores[-1] - scores[-2]
    if d > _VS_DELTA_THRESHOLD:
        return "提升"
    if d < -_VS_DELTA_THRESHOLD:
        return "回落"
    return "持平"


_METRIC_COMPARE_INSUFFICIENT = "暂无足够同专项对比数据"


def _metric_float(v: object) -> float | None:
    if v is None:
        return None
    try:
        return float(v)
    except (TypeError, ValueError):
        return None


def _normalize_kw_coverage(v: float | None) -> float | None:
    if v is None:
        return None
    if v > 1.0001:
        return v / 100.0
    return v


def _load_compare_snapshot(db: Session, session_id: str | None, user_id: int) -> dict:
    """为指标对比加载会话快照（内存 results 优先，否则 TrainingRecord），仅当前用户。"""
    if not session_id:
        return {}
    mem = results.get(session_id)
    if isinstance(mem, dict) and mem:
        if coerce_user_id(mem.get("user_id")) != int(user_id):
            return {}
        return dict(mem)
    try:
        rec = (
            db.query(TrainingRecord)
            .filter(
                TrainingRecord.session_id == session_id,
                TrainingRecord.user_id == int(user_id),
            )
            .first()
        )
    except Exception:
        rec = None
    if not rec:
        return {}
    items, stored = _parse_metrics_json_blob(rec.metrics_json)
    mdict = _metrics_list_to_dict(items)
    raw: dict = {**stored} if isinstance(stored, dict) else {}
    raw["session_id"] = session_id
    aa = raw.get("audio_analysis") if isinstance(raw.get("audio_analysis"), dict) else None
    if rec.audio_metrics_json:
        try:
            am = json.loads(rec.audio_metrics_json)
            if isinstance(am, dict):
                raw.setdefault("audio_metrics", am)
                if not isinstance(aa, dict):
                    raw["audio_analysis"] = dict(am)
                    aa = raw["audio_analysis"]
                elif isinstance(aa, dict):
                    for k in ("speech_rate", "pause_count", "avg_pause_sec", "filler_count"):
                        if aa.get(k) is None and am.get(k) is not None:
                            aa[k] = am[k]
        except Exception:
            pass
    if rec.qa_result_json:
        try:
            qr = json.loads(rec.qa_result_json)
            if isinstance(qr, dict):
                raw["qa_result"] = qr
        except Exception:
            pass
    if rec.ppt_match_json:
        try:
            pm = json.loads(rec.ppt_match_json)
            if isinstance(pm, dict):
                raw["ppt_match"] = pm
        except Exception:
            pass
    for k in ("forward_gaze_ratio", "downward_head_ratio", "posture_stability"):
        if raw.get(k) is None and mdict.get(k) is not None:
            raw[k] = mdict[k]
    vs = raw.get("vision_session_summary")
    if isinstance(vs, dict):
        for k in ("forward_gaze_ratio", "downward_head_ratio", "posture_stability"):
            if raw.get(k) is None and vs.get(k) is not None:
                raw[k] = vs[k]
    va = raw.get("vision_analysis")
    if isinstance(va, dict):
        for k in ("forward_gaze_ratio", "downward_head_ratio", "posture_stability"):
            if raw.get(k) is None and va.get(k) is not None:
                raw[k] = va[k]
    return raw


def _audio_metric(src: dict, key: str) -> float | None:
    aa = src.get("audio_analysis") if isinstance(src.get("audio_analysis"), dict) else {}
    am = src.get("audio_metrics") if isinstance(src.get("audio_metrics"), dict) else {}
    for d in (aa, am):
        if key in d and d.get(key) is not None:
            return _metric_float(d.get(key))
    return None


def _vision_metric_flat(src: dict, key: str) -> float | None:
    v = src.get(key)
    if v is not None:
        return _metric_float(v)
    va = src.get("vision_analysis") if isinstance(src.get("vision_analysis"), dict) else {}
    if va.get(key) is not None:
        return _metric_float(va.get(key))
    vs = src.get("vision_session_summary") if isinstance(src.get("vision_session_summary"), dict) else {}
    if vs.get(key) is not None:
        return _metric_float(vs.get(key))
    return None


def _compare_language_metrics(cur: dict, prev: dict) -> list[str]:
    out: list[str] = []
    csr = _audio_metric(cur, "speech_rate")
    psr = _audio_metric(prev, "speech_rate")
    if csr is not None and psr is not None:
        d = csr - psr
        if d > 15:
            out.append("本轮「语速」较上次略快，可留意听感是否仍然清楚。")
        elif d < -15:
            out.append("本轮「语速」较上次更从容。")
    cpc = _audio_metric(cur, "pause_count")
    ppc = _audio_metric(prev, "pause_count")
    if cpc is not None and ppc is not None:
        if cpc - ppc >= 2:
            out.append("本轮「停顿次数」较上次更多。")
        elif ppc - cpc >= 2:
            out.append("本轮「停顿次数」较上次更少。")
    cap = _audio_metric(cur, "avg_pause_sec")
    pap = _audio_metric(prev, "avg_pause_sec")
    if cap is not None and pap is not None:
        if cap - pap >= 0.2:
            out.append("本轮「平均停顿时长」较上次略长。")
        elif pap - cap >= 0.2:
            out.append("本轮「平均停顿时长」较上次更短。")
    cf = _audio_metric(cur, "filler_count")
    pf = _audio_metric(prev, "filler_count")
    if cf is not None and pf is not None:
        if pf - cf >= 1:
            out.append("本轮「口头禅」较上次减少。")
        elif cf - pf >= 1:
            out.append("本轮「口头禅」较上次略多。")
    return out


def _compare_posture_metrics(cur: dict, prev: dict) -> list[str]:
    out: list[str] = []
    cg = _vision_metric_flat(cur, "forward_gaze_ratio")
    pg = _vision_metric_flat(prev, "forward_gaze_ratio")
    if cg is not None and pg is not None:
        if cg - pg > 0.03:
            out.append("本轮正视前方的比例较上次更高。")
        elif pg - cg > 0.03:
            out.append("本轮正视前方的比例较上次略低。")
    ch = _vision_metric_flat(cur, "downward_head_ratio")
    ph = _vision_metric_flat(prev, "downward_head_ratio")
    if ch is not None and ph is not None:
        if ch - ph > 0.03:
            out.append("本轮低头占比较上次略高。")
        elif ph - ch > 0.03:
            out.append("本轮低头占比较上次降低。")
    cs = _vision_metric_flat(cur, "posture_stability")
    ps = _vision_metric_flat(prev, "posture_stability")
    if cs is not None and ps is not None:
        if cs - ps > 0.03:
            out.append("本轮镜头前稳定度较上次更好。")
        elif ps - cs > 0.03:
            out.append("本轮镜头前稳定度较上次略弱。")
    return out


def _compare_qa_metrics(cur: dict, prev: dict) -> list[str]:
    cqa = cur.get("qa_result") if isinstance(cur.get("qa_result"), dict) else {}
    pqa = prev.get("qa_result") if isinstance(prev.get("qa_result"), dict) else {}
    if not cqa or not pqa:
        return []
    out: list[str] = []
    cir, pir = cqa.get("is_relevant"), pqa.get("is_relevant")
    if isinstance(cir, bool) and isinstance(pir, bool) and cir != pir:
        if cir and not pir:
            out.append("本轮「是否切题」较上次更理想。")
        else:
            out.append("本轮「是否切题」较上次偏弱。")
    cc = _metric_float(cqa.get("coverage_score"))
    pc = _metric_float(pqa.get("coverage_score"))
    if cc is not None and pc is not None:
        ccn = cc if cc <= 1.0001 else cc / 100.0
        pcn = pc if pc <= 1.0001 else pc / 100.0
        if ccn - pcn >= 0.08:
            out.append("本轮「要点覆盖」较上次更好。")
        elif pcn - ccn >= 0.08:
            out.append("本轮「要点覆盖」较上次偏弱，可再对齐提问要点。")
    cl = _metric_float(cqa.get("clarity_score"))
    pl = _metric_float(pqa.get("clarity_score"))
    if cl is not None and pl is not None:
        if cl - pl >= 0.6:
            out.append("本轮「表达清晰度」较上次更好。")
        elif pl - cl >= 0.6:
            out.append("本轮「表达清晰度」较上次略弱。")
    als_c = _metric_float(cqa.get("answer_length_score"))
    als_p = _metric_float(pqa.get("answer_length_score"))
    if als_c is not None and als_p is not None:
        if als_c - als_p >= 0.6:
            out.append("本轮「回答长度」较上次更充分。")
        elif als_p - als_c >= 0.6:
            out.append("本轮「回答长度」较上次更短。")
    elif _metric_float(cqa.get("answer_length")) is not None and _metric_float(pqa.get("answer_length")) is not None:
        alc = float(cqa.get("answer_length") or 0)
        alp = float(pqa.get("answer_length") or 0)
        if alc - alp >= 40:
            out.append("本轮「回答篇幅」较上次更长。")
        elif alp - alc >= 40:
            out.append("本轮「回答篇幅」较上次更短。")
    return out


def _content_metric_fields(src: dict) -> tuple[float | None, float | None, bool | None, bool | None]:
    cb = src.get("content_breakdown") if isinstance(src.get("content_breakdown"), dict) else {}
    pm = src.get("ppt_match") if isinstance(src.get("ppt_match"), dict) else {}

    def pick(cbk: str, pmk: str):
        v = cb.get(cbk)
        if v is None:
            v = pm.get(pmk)
        return v

    ms = _metric_float(pick("match_score", "match_score"))
    kw = _metric_float(pick("keyword_coverage", "keyword_coverage"))
    th_raw = pick("title_hit", "title_hit")
    oh_raw = pick("outline_hit", "outline_hit")

    def _as_bool_opt(raw: object) -> bool | None:
        if raw is None:
            return None
        if isinstance(raw, bool):
            return raw
        return _as_bool(raw, False)

    th_b = _as_bool_opt(th_raw)
    oh_b = _as_bool_opt(oh_raw)
    return ms, kw, th_b, oh_b


def _compare_content_metrics(cur: dict, prev: dict) -> list[str]:
    cms, ckw, cth, coh = _content_metric_fields(cur)
    pms, pkw, pth, poh = _content_metric_fields(prev)
    out: list[str] = []
    if cms is not None and pms is not None:
        if cms - pms >= 5:
            out.append("本轮「页内匹配表现」较上次更好。")
        elif pms - cms >= 5:
            out.append("本轮「页内匹配表现」较上次略弱。")
    ckw_n = _normalize_kw_coverage(ckw)
    pkw_n = _normalize_kw_coverage(pkw)
    if ckw_n is not None and pkw_n is not None:
        if ckw_n - pkw_n >= 0.08:
            out.append("本轮「关键词覆盖」较上次更充分。")
        elif pkw_n - ckw_n >= 0.08:
            out.append("本轮「关键词覆盖」较上次略紧。")
    if isinstance(cth, bool) and isinstance(pth, bool) and cth != pth:
        if cth and not pth:
            out.append("本轮「标题要点对齐」较上次更理想。")
        else:
            out.append("本轮「标题要点对齐」较上次略弱。")
    if isinstance(coh, bool) and isinstance(poh, bool) and coh != poh:
        if coh and not poh:
            out.append("本轮「大纲/结构线索」较上次更容易对上。")
        else:
            out.append("本轮「大纲/结构线索」较上次略弱。")
    return out


def _build_training_focus_metric_highlights(focus: str, cur_src: dict, prev_src: dict) -> list[str]:
    if focus == "language":
        return _compare_language_metrics(cur_src, prev_src)
    if focus == "posture":
        return _compare_posture_metrics(cur_src, prev_src)
    if focus == "qa":
        return _compare_qa_metrics(cur_src, prev_src)
    if focus == "content":
        return _compare_content_metrics(cur_src, prev_src)
    return []


def _build_training_focus_metric_bundle(
    focus: str,
    cur_src: dict,
    prev_src: dict | None,
) -> tuple[str, list[str]]:
    if not prev_src:
        return _METRIC_COMPARE_INSUFFICIENT, []
    hil = _build_training_focus_metric_highlights(focus, cur_src, prev_src)
    hil = [h for h in hil if isinstance(h, str) and h.strip()][:4]
    if not hil:
        return _METRIC_COMPARE_INSUFFICIENT, []
    if len(hil) == 1:
        return hil[0], hil
    return f"{hil[0]}；{hil[1]}", hil


def _rollup_key_metrics_vs_previous(highlights: list[str]) -> str:
    if not highlights:
        return "暂无足够历史"
    pos = neg = 0
    for h in highlights:
        if any(
            t in h
            for t in (
                "更高",
                "更好",
                "减少",
                "降低",
                "更从容",
                "更充分",
                "更理想",
                "更容易",
            )
        ):
            pos += 1
        if any(
            t in h
            for t in (
                "略低",
                "略高",
                "略多",
                "偏弱",
                "略弱",
                "略紧",
                "更短",
            )
        ):
            neg += 1
    if pos > neg:
        return "提升"
    if neg > pos:
        return "回落"
    return "持平"


def _previous_same_focus_session_id(
    all_items_desc: list[HistoryItem],
    target: HistoryItem,
    focus: str,
) -> str | None:
    window = _same_focus_window(all_items_desc, target, max_n=500, valid_only=True)
    if len(window) < 2:
        return None
    return window[-2].session_id


def _apply_training_focus_metrics_compare_to_payload(
    db: Session,
    payload: dict,
    merged: list[HistoryItem],
    cur: HistoryItem,
    focus: str,
    user_id: int,
) -> None:
    prev_sid = _previous_same_focus_session_id(merged, cur, focus)
    prev_src = _load_compare_snapshot(db, prev_sid, user_id) if prev_sid else None
    cur_src = payload if isinstance(payload, dict) else {}
    line, hil = _build_training_focus_metric_bundle(focus, cur_src, prev_src)
    payload["training_focus_metric_compare"] = line
    payload["training_focus_metric_highlights"] = hil
    print(
        f"[result.api] training_focus_metric_compare={line!r} session_id={payload.get('session_id')}",
        flush=True,
    )
    print(
        f"[result.api] training_focus_metric_highlights={hil!r} session_id={payload.get('session_id')}",
        flush=True,
    )


def _enrich_history_focus_key_metrics(
    db: Session,
    all_items_desc: list[HistoryItem],
    item: HistoryItem,
    user_id: int,
) -> HistoryItem:
    if not item.training_valid:
        return item.model_copy(update={"focus_key_metrics_vs_previous": None})
    focus = _normalize_training_focus_out(item.training_focus)
    if focus == "none":
        return item.model_copy(update={"focus_key_metrics_vs_previous": None})
    prev_sid = _previous_same_focus_session_id(all_items_desc, item, focus)
    if not prev_sid:
        return item.model_copy(update={"focus_key_metrics_vs_previous": "暂无足够历史"})
    cur_src = _load_compare_snapshot(db, item.session_id, user_id)
    prev_src = _load_compare_snapshot(db, prev_sid, user_id)
    _line, hil = _build_training_focus_metric_bundle(focus, cur_src, prev_src)
    if not hil:
        return item.model_copy(update={"focus_key_metrics_vs_previous": "暂无足够历史"})
    return item.model_copy(
        update={"focus_key_metrics_vs_previous": _rollup_key_metrics_vs_previous(hil)}
    )


def _build_training_focus_vs_recent(scores: list[float], trend_kind: str) -> str:
    """与上一次同专项核心分对比 + 波动提示（规则版）。"""
    parts: list[str] = []
    if len(scores) >= 3 and trend_kind == "volatile":
        parts.append("最近同专项波动较大。")
    if len(scores) >= 2:
        prev, cur = scores[-2], scores[-1]
        d = cur - prev
        if d > _VS_DELTA_THRESHOLD:
            parts.append("较上次同专项有提升。")
        elif d < -_VS_DELTA_THRESHOLD:
            parts.append("较上次同专项有所回落。")
        else:
            parts.append("较上次同专项基本持平。")
        return "".join(parts)
    return "暂无足够历史"


def _primary_core_score_from_payload(payload: dict, focus: str) -> float | None:
    """优先 score_breakdown 有效模块，否则顶层 *_*_score（与 Result 展示一致）。"""
    if focus not in _FOCUS_SCORE_FIELD:
        return None
    bd = payload.get("score_breakdown") if isinstance(payload.get("score_breakdown"), dict) else {}
    vm = bd.get("valid_modules") if isinstance(bd.get("valid_modules"), dict) else {}
    modules = bd.get("modules") if isinstance(bd.get("modules"), dict) else {}
    if vm.get(focus) and isinstance(modules.get(focus), dict):
        try:
            return float(modules[focus].get("score", 0.0))
        except (TypeError, ValueError):
            pass
    key = _FOCUS_SCORE_FIELD[focus]
    v = payload.get(key)
    if v is None:
        return None
    try:
        return float(v)
    except (TypeError, ValueError):
        return None


def _history_session_core_score(
    item: HistoryItem,
    focus: str,
    live_payload: dict | None = None,
) -> float | None:
    """历史项核心分：HistoryItem → 与 live 同会话的 payload → 内存 results。"""
    x = _core_score_from_history_item(item, focus)
    if x is not None:
        return x
    if live_payload:
        sid = str(live_payload.get("session_id") or "")
        if sid and str(item.session_id) == sid:
            return _primary_core_score_from_payload(live_payload, focus)
    mem = results.get(str(item.session_id))
    if isinstance(mem, dict):
        return _primary_core_score_from_payload(mem, focus)
    return None


def _next_action_label_zh(focus: str, action: str, recommended_raw: object) -> str:
    full = _FOCUS_LABEL_FULL_CN.get(focus, "本专项")
    rec = _normalize_optional_focus_key(recommended_raw)
    rec_full = _FOCUS_LABEL_FULL_CN.get(rec, "") if rec else ""
    if action == "observe_more":
        return "建议继续积累专项记录后再判断下一轮重点。"
    if action == "switch_focus" and rec and rec != focus and rec_full:
        return f"建议下一轮转为{rec_full}，把薄弱项也带起来。"
    if action == "switch_focus":
        return "建议下一轮可以尝试轮换到其他薄弱项，练得更均衡。"
    return f"建议继续{full}再练 1～2 轮，把稳定感练出来。"


def _decide_training_focus_next_action(
    focus: str,
    kind: str,
    primary: float | None,
    recommended_raw: object,
) -> str:
    rec = _normalize_optional_focus_key(recommended_raw)
    if primary is None or kind == "insufficient":
        return "observe_more"
    # 明显提升且系统推荐的薄弱项已不是本轮专项 → 轮换
    if kind == "up" and rec and rec != focus:
        return "switch_focus"
    if primary < 60:
        return "continue_same_focus"
    if kind == "volatile":
        return "continue_same_focus"
    if kind == "flat" and primary < 70:
        return "continue_same_focus"
    return "continue_same_focus"


def _build_training_focus_explanation(
    focus: str,
    kind: str,
    primary: float | None,
    scores: list[float],
    recommended_raw: object,
) -> dict:
    full = _FOCUS_LABEL_FULL_CN.get(focus, "专项")
    vs = _build_training_focus_vs_recent(scores, kind)
    action = _decide_training_focus_next_action(focus, kind, primary, recommended_raw)
    outcome = _round_focus_outcome_line(kind)
    hint = _next_action_label_zh(focus, action, recommended_raw)
    if primary is not None:
        head = f"本轮练的是「{full}」，本专项核心分为 {primary:.1f} 分。"
    else:
        head = f"本轮练的是「{full}」，本专项核心分暂无法从有效分项中读出。"
    summary = f"{head} {vs} {outcome} {hint}".strip()
    return {
        "training_focus_summary": summary,
        "training_focus_primary_score": primary,
        "training_focus_vs_recent": vs,
        "training_focus_next_action": action,
        "training_focus_next_hint": hint,
        "training_focus_next_action_label": hint,
    }


def _core_score_from_history_item(item: HistoryItem, focus: str) -> float | None:
    if focus not in _FOCUS_SCORE_FIELD:
        return None
    v = getattr(item, _FOCUS_SCORE_FIELD[focus], None)
    if v is None:
        return None
    try:
        return float(v)
    except (TypeError, ValueError):
        return None


def _history_item_ts_key(item: HistoryItem) -> tuple[str, str]:
    return (item.timestamp or "", item.session_id)


def _same_focus_window(
    all_items_desc: list[HistoryItem],
    target: HistoryItem,
    max_n: int = 5,
    *,
    valid_only: bool = True,
) -> list[HistoryItem]:
    focus = _normalize_training_focus_out(target.training_focus)
    if focus == "none":
        return []
    tkey = _history_item_ts_key(target)
    same: list[HistoryItem] = []
    for h in all_items_desc:
        if _normalize_training_focus_out(h.training_focus) != focus:
            continue
        if valid_only and not h.training_valid:
            continue
        if _history_item_ts_key(h) <= tkey:
            same.append(h)
    same.sort(key=_history_item_ts_key)
    if len(same) > max_n:
        same = same[-max_n:]
    return same


def _rule_focus_trend(scores: list[float]) -> str:
    if len(scores) < 2:
        return "insufficient"
    first, last = scores[0], scores[-1]
    spread = max(scores) - min(scores)
    n = len(scores)
    dirs: list[int] = []
    for i in range(1, n):
        d = scores[i] - scores[i - 1]
        if d > 1.5:
            dirs.append(1)
        elif d < -1.5:
            dirs.append(-1)
        else:
            dirs.append(0)
    nonzero = [x for x in dirs if x != 0]
    sign_changes = 0
    for i in range(1, len(nonzero)):
        if nonzero[i] * nonzero[i - 1] < 0:
            sign_changes += 1
    if n >= 3 and spread >= 8 and sign_changes >= 1:
        return "volatile"
    if n >= 3 and spread >= 10:
        return "volatile"
    if last - first >= 3:
        return "up"
    if first - last >= 3:
        return "volatile"
    if abs(last - first) < 3 and spread < 6:
        return "flat"
    if spread >= 6:
        return "volatile"
    return "flat"


def _format_scores_chain(scores: list[float]) -> str:
    parts: list[str] = []
    for s in scores:
        if abs(s - round(s)) < 0.05:
            parts.append(str(int(round(s))))
        else:
            parts.append(f"{s:.1f}")
    return " → ".join(parts)


def _focus_review_trend_label_cn(trend: str) -> str:
    if trend == "up":
        return "上升"
    if trend == "flat":
        return "持平"
    if trend == "volatile":
        return "波动"
    return "数据不足"


def _focus_review_main_issue_cn(focus: str, trend: str) -> str:
    if focus == "language":
        return "近期主要问题仍容易集中在语速、停顿节奏与口头禅等表达节奏类指标。"
    if focus == "posture":
        if trend == "volatile":
            return "近期主要问题仍容易集中在正视比例、低头率与身姿稳定度等镜头前表现。"
        return "近期可重点关注正视比例与身姿稳定，尽量减少低头与身体晃动。"
    if focus == "qa":
        return "近期主要问题仍容易集中在切题度、要点覆盖、清晰度与回答篇幅等问答指标。"
    if focus == "content":
        return "近期主要问题仍容易集中在页面对齐、关键词覆盖与标题/大纲线索等讲解指标。"
    return "建议对照最近一次结果页的明细，定位薄弱环节。"


def _focus_review_metrics_digest(rows: list[HistoryItem]) -> str:
    labels = [
        h.focus_key_metrics_vs_previous
        for h in rows
        if isinstance(h.focus_key_metrics_vs_previous, str) and h.focus_key_metrics_vs_previous.strip()
        and h.focus_key_metrics_vs_previous != "暂无足够历史"
    ]
    if not labels:
        return "同专项「关键指标较上次」的对比记录仍偏少，可结合各条卡片与结果页单次明细查看。"
    up = sum(1 for x in labels if x == "提升")
    down = sum(1 for x in labels if x == "回落")
    flat = sum(1 for x in labels if x == "持平")
    if up > down and up >= flat:
        return "关键指标变化摘要：最近几次里，多数记录相对上次更偏「提升」。"
    if down > up and down >= flat:
        return "关键指标变化摘要：最近几次里，多数记录相对上次更常出现「回落」，适合对照反馈逐项收紧。"
    return "关键指标变化摘要：最近几次里，多数记录在「持平」附近小幅波动。"


def _focus_review_next_action_cn(focus: str, trend: str, scores: list[float]) -> str:
    full = _FOCUS_LABEL_FULL_CN.get(focus, "本专项")
    if len(scores) < 2 or trend == "insufficient":
        return f"建议继续{full}再练 1～2 次，把同专项记录攒够后再决定是否轮换重点。"
    last = scores[-1]
    if trend == "up" and last >= 68:
        return "本专项已有明显提升，下一轮可尝试轮换到其他薄弱项，练得更均衡。"
    if trend == "volatile":
        return f"建议继续{full}再练 1～2 轮，优先把发挥稳住、减少大起大落。"
    if trend == "flat" and last < 62:
        return f"建议继续{full}再练 1～2 轮，先把基础分抬上来。"
    return f"建议继续{full}再练 1～2 轮，巩固当前手感。"


def _build_history_focus_review_fields(
    enriched: list[HistoryItem],
    review_focus_raw: str | None,
    max_n: int = 5,
) -> dict:
    fk = _normalize_training_focus_out(review_focus_raw or "")
    empty = {
        "focus_review_summary": None,
        "focus_review_scores": None,
        "focus_review_trend": None,
        "focus_review_next_action": None,
    }
    if fk not in ("language", "posture", "qa", "content"):
        return empty
    rows = [
        h
        for h in enriched
        if _normalize_training_focus_out(h.training_focus) == fk and h.training_valid
    ]
    rows.sort(key=_history_item_ts_key)
    if len(rows) > max_n:
        rows = rows[-max_n:]
    scores: list[float] = []
    for h in rows:
        p = h.focus_primary_score
        if p is None:
            p = h.training_focus_primary_score
        if p is not None:
            try:
                scores.append(float(p))
            except (TypeError, ValueError):
                continue
    lab_full = _FOCUS_LABEL_FULL_CN.get(fk, fk)
    trend_kind = _rule_focus_trend(scores) if len(scores) >= 2 else "insufficient"
    trend_cn = _focus_review_trend_label_cn(trend_kind)
    digest = _focus_review_metrics_digest(rows)
    next_act = _focus_review_next_action_cn(fk, trend_kind, scores)
    if not scores:
        summary = (
            f"暂无可用的{lab_full}专项核心分序列。{digest} "
            f"{_focus_review_main_issue_cn(fk, trend_kind)}"
        ).strip()
        return {
            "focus_review_summary": summary,
            "focus_review_scores": [],
            "focus_review_trend": trend_cn,
            "focus_review_next_action": next_act,
        }
    chain = _format_scores_chain(scores)
    line1 = f"最近 {len(scores)} 次{lab_full}核心分：{chain}，当前整体趋势为「{trend_cn}」。"
    main_issue = _focus_review_main_issue_cn(fk, trend_kind)
    summary = f"{line1} {digest} {main_issue}".strip()
    return {
        "focus_review_summary": summary,
        "focus_review_scores": list(scores),
        "focus_review_trend": trend_cn,
        "focus_review_next_action": next_act,
    }


_OVERVIEW_RECENT_N = 7


def _overview_recommend_continue_focus(
    recent: list[HistoryItem],
    dist: dict[str, int],
) -> str | None:
    """规则版：专项占比明显领先则跟占比；否则用近几次分项均分最低者。"""
    key_rank = {"language": 0, "posture": 1, "content": 2, "qa": 3, "none": 9}
    spec_keys = ("language", "posture", "qa", "content")
    spec_counts = [(k, int(dist.get(k, 0))) for k in spec_keys]
    spec_counts.sort(key=lambda x: (-x[1], key_rank[x[0]]))
    top_k, top_v = spec_counts[0]
    second_v = spec_counts[1][1] if len(spec_counts) > 1 else 0
    if top_v > second_v and top_v > 0:
        return top_k
    field_map = {
        "language": "language_score",
        "posture": "posture_score",
        "content": "content_score",
        "qa": "qa_score",
    }
    acc: dict[str, list[float]] = {k: [] for k in spec_keys}
    for h in recent:
        for k, attr in field_map.items():
            v = getattr(h, attr, None)
            if v is None:
                continue
            try:
                acc[k].append(float(v))
            except (TypeError, ValueError):
                continue
    candidates: list[tuple[str, float]] = []
    for k in spec_keys:
        xs = acc[k]
        if xs:
            candidates.append((k, sum(xs) / len(xs)))
    if candidates:
        candidates.sort(key=lambda x: (x[1], key_rank[x[0]]))
        return candidates[0][0]
    if dist.get("none", 0) >= len(recent) and len(recent) > 0:
        return "none"
    if top_v > 0:
        return top_k
    return "language"


def _build_valid_training_overview(
    enriched: list[HistoryItem],
    *,
    recent_n: int = _OVERVIEW_RECENT_N,
) -> ValidTrainingOverview:
    """历史页有效训练总览 V1：仅 training_valid=true，默认最近 recent_n 条。"""
    valid = [h for h in enriched if h.training_valid]
    empty_msg = "暂无足够有效训练数据"
    if not valid:
        return ValidTrainingOverview(
            overview_ready=False,
            overview_message=empty_msg,
            valid_count_recent=0,
            recent_window_size=recent_n,
            avg_total_score_recent=None,
            latest_valid_training_focus=None,
            latest_valid_session_id=None,
            latest_valid_created_at=None,
            latest_valid_total_score=None,
            latest_valid_scoring_profile=None,
            latest_valid_defense_material_mode=None,
            focus_distribution_recent={},
            recommended_continue_focus=None,
        )

    recent = valid[:recent_n]
    n = len(recent)
    avg_total = sum(float(h.total_score or 0.0) for h in recent) / max(n, 1)
    latest = recent[0]
    latest_focus = _normalize_training_focus_out(latest.training_focus)
    latest_at = (latest.created_at or latest.timestamp or "").strip() or None
    try:
        latest_total = float(latest.total_score or 0.0)
    except (TypeError, ValueError):
        latest_total = None

    dist: dict[str, int] = {k: 0 for k in ("language", "posture", "qa", "content", "none")}
    for h in recent:
        fk = _normalize_training_focus_out(h.training_focus)
        if fk in dist:
            dist[fk] += 1
        else:
            dist["none"] += 1

    rec = _overview_recommend_continue_focus(recent, dist)
    sparse: str | None = None
    if n < 3:
        sparse = f"当前有效训练仅 {n} 条，以下汇总仅供参考，多练几次会更稳。"

    latest_sp: str | None = None
    if isinstance(latest.scoring_profile, str):
        spc = latest.scoring_profile.strip().lower()
        if spc in ("defense", "interview"):
            latest_sp = spc
    latest_dm = None
    if isinstance(latest.defense_material_mode, str):
        latest_dm = _normalize_merged_defense_material_mode(latest.defense_material_mode)

    return ValidTrainingOverview(
        overview_ready=True,
        overview_message=sparse,
        valid_count_recent=n,
        recent_window_size=recent_n,
        avg_total_score_recent=round(avg_total, 2),
        latest_valid_training_focus=latest_focus,
        latest_valid_session_id=(latest.session_id or "").strip() or None,
        latest_valid_created_at=latest_at,
        latest_valid_total_score=round(latest_total, 2) if latest_total is not None else None,
        latest_valid_scoring_profile=latest_sp,
        latest_valid_defense_material_mode=latest_dm,
        focus_distribution_recent=dict(dist),
        recommended_continue_focus=rec,
    )


def _human_focus_trend_line(focus: str, trend: str, scores: list[float]) -> str:
    label = _FOCUS_LABEL_CN.get(focus, focus)
    if trend == "insufficient" or len(scores) < 2:
        if len(scores) == 1:
            return (
                f"目前已记入 1 次{label}专项，核心分 {_format_scores_chain(scores)}。"
                "再多练几次，趋势会更清晰。"
            )
        return "暂无足够同专项历史，建议多完成几次同专项训练后再看进步情况。"
    chain = _format_scores_chain(scores)
    if trend == "up":
        return f"最近 {len(scores)} 次{label}专项核心分：{chain}，整体在往上走，继续保持。"
    if trend == "flat":
        return f"最近 {len(scores)} 次{label}专项核心分：{chain}，大致持平，可再抠一抠细节。"
    return f"最近 {len(scores)} 次{label}专项核心分：{chain}，起伏比较明显，建议稳定节奏、减少大起大落。"


def _build_focus_recent_entries(
    window: list[HistoryItem],
    focus: str,
    live_payload: dict | None = None,
) -> list[dict]:
    out: list[dict] = []
    for h in window:
        cs = _history_session_core_score(h, focus, live_payload)
        out.append(
            {
                "session_id": h.session_id,
                "timestamp": h.timestamp,
                "core_score": cs,
                "total_score": h.total_score,
            }
        )
    return out


def _enrich_history_item_focus_trend(
    all_items_desc: list[HistoryItem],
    item: HistoryItem,
    live_payload: dict | None = None,
    recommended_raw: object | None = None,
) -> HistoryItem:
    focus = _normalize_training_focus_out(item.training_focus)
    if focus == "none":
        return item.model_copy(
            update={
                "focus_trend_summary": None,
                "focus_recent_scores": [],
                "focus_trend_kind": "none",
                "training_focus_summary": None,
                "training_focus_primary_score": None,
                "training_focus_vs_recent": None,
                "training_focus_next_action": None,
                "training_focus_next_hint": None,
                "training_focus_next_action_label": None,
                "focus_primary_score": None,
                "focus_vs_previous": None,
                "focus_key_metrics_vs_previous": None,
            }
        )
    if not item.training_valid:
        hint = "建议检查麦克风、摄像头与环境后重新训练。"
        summ = (item.invalid_reason_summary or "本轮未形成有效训练结果。").strip()
        return item.model_copy(
            update={
                "focus_trend_summary": "本轮记录未计入同专项趋势统计。",
                "focus_recent_scores": [],
                "focus_trend_kind": "insufficient",
                "training_focus_summary": summ,
                "training_focus_primary_score": None,
                "training_focus_vs_recent": None,
                "training_focus_next_action": None,
                "training_focus_next_hint": hint,
                "training_focus_next_action_label": hint,
                "focus_primary_score": None,
                "focus_vs_previous": None,
                "focus_key_metrics_vs_previous": None,
            }
        )
    window = _same_focus_window(all_items_desc, item, 5, valid_only=True)
    scores = [
        s
        for s in (_history_session_core_score(h, focus, live_payload) for h in window)
        if s is not None
    ]
    if len(scores) < 2:
        trend = "insufficient"
    else:
        trend = _rule_focus_trend(scores)
    summary = _human_focus_trend_line(focus, trend, scores)
    recent = _build_focus_recent_entries(window, focus, live_payload)
    kind = trend if trend in ("up", "flat", "volatile", "insufficient") else "insufficient"
    primary = _history_session_core_score(item, focus, live_payload)
    expl = _build_training_focus_explanation(focus, kind, primary, scores, recommended_raw)
    vs_prev = _focus_vs_previous_short(scores)
    return item.model_copy(
        update={
            "focus_trend_summary": summary,
            "focus_recent_scores": recent,
            "focus_trend_kind": kind,
            "training_focus_summary": expl["training_focus_summary"],
            "training_focus_primary_score": expl["training_focus_primary_score"],
            "training_focus_vs_recent": expl["training_focus_vs_recent"],
            "training_focus_next_action": expl["training_focus_next_action"],
            "training_focus_next_hint": expl["training_focus_next_hint"],
            "training_focus_next_action_label": expl.get("training_focus_next_action_label"),
            "focus_primary_score": primary,
            "focus_vs_previous": vs_prev,
        }
    )


def _collect_history_items(db: Session, user_id: int) -> list[HistoryItem]:
    db_records = (
        db.query(TrainingRecord)
        .filter(
            TrainingRecord.status == "completed",
            TrainingRecord.user_id == int(user_id),
        )
        .order_by(TrainingRecord.start_time.desc())
        .all()
    )

    history_items: list[HistoryItem] = []
    seen_ids: set[str] = set()

    if db_records:
        for record in db_records:
            seen_ids.add(record.session_id)
            history_items.append(
                _compose_history_item(
                    session_id=record.session_id,
                    session_name=record.session_name,
                    timestamp=record.start_time,
                    created_at=record.created_at,
                    total_score=record.total_score or 0.0,
                    language_col=record.language_score,
                    posture_col=record.posture_score,
                    metrics_json_str=record.metrics_json,
                    in_memory=results.get(record.session_id),
                    record_scoring_profile=getattr(record, "scoring_profile", None),
                    record_scoring_profile_label=getattr(record, "scoring_profile_label", None),
                    record_training_focus=getattr(record, "training_focus", None),
                )
            )

    for session_id, session_data in sessions.items():
        if session_data.get("status") != "completed":
            continue
        if coerce_user_id(session_data.get("user_id")) != int(user_id):
            continue
        if session_id in seen_ids:
            continue
        result_data = results.get(session_id, {})
        ts = session_data.get("start_time", datetime.utcnow().isoformat())
        history_items.append(
            _compose_history_item(
                session_id=session_id,
                session_name=session_data.get("session_name", f"训练_{session_id[:8]}"),
                timestamp=ts,
                created_at=session_data.get("created_at") or ts,
                total_score=result_data.get("total_score", 0.0),
                language_col=result_data.get("language_score"),
                posture_col=result_data.get("posture_score"),
                metrics_json_str=None,
                in_memory=result_data,
                record_scoring_profile=session_data.get("scoring_profile"),
                record_scoring_profile_label=session_data.get("scoring_profile_label"),
            )
        )

    history_items.sort(key=lambda x: x.timestamp, reverse=True)
    return history_items


def _history_item_from_result_payload(
    session_id: str,
    payload: dict,
    timestamp: str | None,
) -> HistoryItem:
    focus = _normalize_training_focus_out(payload.get("training_focus"))

    def _opt_float(k: str) -> float | None:
        v = payload.get(k)
        if v is None:
            return None
        try:
            return float(v)
        except (TypeError, ValueError):
            return None

    name = str(payload.get("session_name") or f"训练_{session_id[:8]}")
    ts = str(timestamp or datetime.utcnow().isoformat())
    sp = payload.get("scoring_profile")
    spl = payload.get("scoring_profile_label")
    bd = payload.get("score_breakdown") if isinstance(payload.get("score_breakdown"), dict) else None
    aa = payload.get("audio_analysis") if isinstance(payload.get("audio_analysis"), dict) else {}
    audio_v: bool | None = None
    if isinstance(aa, dict) and "audio_valid" in aa:
        audio_v = _as_bool(aa.get("audio_valid"), False)
    vv_raw = payload.get("vision_valid")
    vision_b: bool | None = None
    if vv_raw is not None:
        vision_b = _as_bool(vv_raw, True)
    audio_hist = audio_v
    vision_hist = vision_b
    if isinstance(bd, dict) and isinstance(bd.get("valid_modules"), dict):
        vm = bd["valid_modules"]
        if "language" in vm:
            audio_hist = bool(vm.get("language"))
        if "posture" in vm:
            vision_hist = bool(vm.get("posture"))
    if isinstance(payload.get("training_valid"), bool):
        tv = bool(payload["training_valid"])
        inv_reason = str(payload.get("invalid_reason_summary") or "").strip() or None
        if tv:
            inv_reason = None
    else:
        _tv, _reason = _compute_training_validity(
            total_score=float(payload.get("total_score") or 0.0),
            score_breakdown=bd,
            audio_valid=audio_v,
            vision_valid=vision_b,
        )
        tv = _tv
        inv_reason = _reason if not _tv else None
    dm_hist = _normalize_merged_defense_material_mode(payload.get("defense_material_mode"))
    return HistoryItem(
        session_id=session_id,
        session_name=name,
        timestamp=ts,
        created_at=ts,
        total_score=float(payload.get("total_score") or 0.0),
        language_score=_opt_float("language_score"),
        posture_score=_opt_float("posture_score"),
        content_score=_opt_float("content_score"),
        qa_score=_opt_float("qa_score"),
        scoring_profile=sp if isinstance(sp, str) else None,
        scoring_profile_label=spl if isinstance(spl, str) else None,
        defense_material_mode=dm_hist,
        audio_valid=audio_hist,
        vision_valid=vision_hist,
        training_focus=focus,
        training_valid=tv,
        invalid_reason_summary=inv_reason,
    )


def _apply_training_focus_trend_to_payload(
    db: Session,
    session_id: str,
    payload: dict,
    result_timestamp: str | None,
    user_id: int,
) -> None:
    focus = _normalize_training_focus_out(payload.get("training_focus"))
    if focus == "none":
        payload["training_focus_trend"] = None
        payload["recent_focus_scores"] = []
        payload["focus_trend_kind"] = "none"
        payload["training_focus_summary"] = None
        payload["training_focus_primary_score"] = None
        payload["training_focus_vs_recent"] = None
        payload["training_focus_next_action"] = None
        payload["training_focus_next_hint"] = None
        payload["training_focus_next_action_label"] = None
        payload["training_focus_metric_compare"] = None
        payload["training_focus_metric_highlights"] = []
        print(
            f"[result.api] training_focus_trend=(skipped, focus=none) session_id={session_id}",
            flush=True,
        )
        print(
            f"[result.api] focus_commentary_ready=(skipped, focus=none) session_id={session_id}",
            flush=True,
        )
        return
    if not payload.get("training_valid", True):
        ir = str(payload.get("invalid_reason_summary") or "").strip()
        payload["training_focus_trend"] = None
        payload["recent_focus_scores"] = []
        payload["focus_trend_kind"] = "insufficient"
        payload["training_focus_summary"] = ir or "本轮未形成有效训练结果。"
        payload["training_focus_primary_score"] = None
        payload["training_focus_vs_recent"] = "本轮未计入同专项趋势"
        payload["training_focus_next_action"] = None
        payload["training_focus_next_hint"] = "建议检查麦克风、摄像头与环境后重新完成一次训练。"
        payload["training_focus_next_action_label"] = payload["training_focus_next_hint"]
        payload["training_focus_metric_compare"] = None
        payload["training_focus_metric_highlights"] = []
        print(
            f"[result.api] training_focus_trend=(skipped, training_valid=False) session_id={session_id}",
            flush=True,
        )
        print(
            f"[result.api] focus_commentary_ready=(skipped, training_valid=False) session_id={session_id}",
            flush=True,
        )
        return
    all_h = _collect_history_items(db, user_id)
    cur = _history_item_from_result_payload(session_id, payload, result_timestamp)
    merged: list[HistoryItem] = [h for h in all_h if h.session_id != session_id]
    merged.append(cur)
    merged.sort(key=_history_item_ts_key, reverse=True)
    enriched = _enrich_history_item_focus_trend(
        merged,
        cur,
        live_payload=payload,
        recommended_raw=payload.get("recommended_training_focus"),
    )
    payload["training_focus_trend"] = enriched.focus_trend_summary
    payload["recent_focus_scores"] = list(enriched.focus_recent_scores or [])
    payload["focus_trend_kind"] = enriched.focus_trend_kind
    payload["training_focus_summary"] = enriched.training_focus_summary
    payload["training_focus_primary_score"] = enriched.training_focus_primary_score
    payload["training_focus_vs_recent"] = enriched.training_focus_vs_recent
    payload["training_focus_next_action"] = enriched.training_focus_next_action
    payload["training_focus_next_hint"] = enriched.training_focus_next_hint
    payload["training_focus_next_action_label"] = (
        enriched.training_focus_next_action_label or enriched.training_focus_next_hint
    )
    if not payload.get("training_focus_vs_recent"):
        payload["training_focus_vs_recent"] = "暂无足够历史"
    if not payload.get("training_focus_next_hint"):
        payload["training_focus_next_hint"] = "建议继续积累专项记录后再判断下一轮重点。"
    if not payload.get("training_focus_next_action_label"):
        payload["training_focus_next_action_label"] = payload["training_focus_next_hint"]
    if not payload.get("training_focus_next_action"):
        payload["training_focus_next_action"] = "observe_more"
    print(
        f"[result.api] training_focus_trend={enriched.focus_trend_summary!r} session_id={session_id}",
        flush=True,
    )
    print(
        f"[result.api] training_focus_summary={enriched.training_focus_summary!r} session_id={session_id}",
        flush=True,
    )
    print(
        f"[result.api] training_focus_vs_recent={payload.get('training_focus_vs_recent')!r} session_id={session_id}",
        flush=True,
    )
    print(
        f"[result.api] training_focus_next_action={payload.get('training_focus_next_action')!r} session_id={session_id}",
        flush=True,
    )
    _apply_training_focus_metrics_compare_to_payload(db, payload, merged, cur, focus, user_id)
    apply_training_focus_commentary_overlay(payload)
    print(
        f"[result.api] focus_commentary_ready=focus={focus!r} session_id={session_id}",
        flush=True,
    )


def _compose_result_payload(session_id: str, raw_result: dict, metrics_items: list, transcript: str | None, audio_metrics: dict | None, ppt_match: dict | None, ppt_match_analysis: dict | None, qa_result: dict | None, summary: dict | None):
    def _ppt_usable(pm: dict | None) -> bool:
        return isinstance(pm, dict) and pm.get("page_index") is not None

    raw_pm_fallback = raw_result.get("ppt_match") if isinstance(raw_result.get("ppt_match"), dict) else None
    effective_ppt_match = ppt_match if _ppt_usable(ppt_match) else None
    if not effective_ppt_match and _ppt_usable(raw_pm_fallback):
        effective_ppt_match = raw_pm_fallback
        print(
            "[result.api] ppt_match merged from raw_result (param missing/invalid) "
            f"session_id={session_id} page_index={effective_ppt_match.get('page_index')!r}",
            flush=True,
        )
    ppt_match = effective_ppt_match

    score_result, vision_state, vision_metrics = _build_scoring_fields(
        session_id=session_id,
        raw_result=raw_result,
        metrics_items=metrics_items,
        transcript=transcript,
        audio_metrics=audio_metrics,
        ppt_match=ppt_match,
        qa_result=qa_result,
        ppt_match_analysis=ppt_match_analysis,
        content_document=raw_result.get("content_document") if isinstance(raw_result.get("content_document"), dict) else None,
    )
    metrics_payload = metrics_items or score_result.get("metrics") or []
    suggestions_payload = raw_result.get("suggestions") or score_result.get("suggestions") or []
    suggestions_payload = _materialize_suggestions(suggestions_payload)
    summary_payload = _normalize_summary(
        summary or score_result.get("summary"),
        score_result.get("total_score", 0.0),
        score_result.get("language_score", 0.0),
        score_result.get("posture_score", 0.0),
        _metrics_list_to_dict(metrics_payload),
    )
    _ppt_match_src, _qa_match_src = _resolve_session_source_fields(raw_result, ppt_match, qa_result)
    audio_analysis_payload = raw_result.get("audio_analysis") if isinstance(raw_result.get("audio_analysis"), dict) else None
    if not audio_analysis_payload:
        if transcript:
            audio_analysis_payload = {
                "transcript": transcript,
                "speech_rate": (audio_metrics or {}).get("speech_rate", 0),
                "pause_count": (audio_metrics or {}).get("pause_count", 0),
                "avg_pause_sec": (audio_metrics or {}).get("avg_pause_sec", 0),
                "filler_count": (audio_metrics or {}).get("filler_count", 0),
                "audio_valid": True,
                "audio_message": "",
            }
        else:
            audio_analysis_payload = {
                "transcript": "",
                "speech_rate": 0,
                "pause_count": 0,
                "avg_pause_sec": 0,
                "filler_count": 0,
                "audio_valid": False,
                "audio_message": "未检测到有效语音，请靠近麦克风后重试",
            }

    response_payload = {
        "session_id": session_id,
        "total_score": score_result.get("total_score", 0.0),
        "language_score": score_result.get("language_score", 0.0),
        "posture_score": score_result.get("posture_score", 0.0),
        "content_score": score_result.get("content_score", 0.0),
        "qa_score": score_result.get("qa_score", 0.0),
        "scoring_profile": score_result.get("scoring_profile") or raw_result.get("scoring_profile"),
        "scoring_profile_label": score_result.get("scoring_profile_label")
        or raw_result.get("scoring_profile_label"),
        "score_breakdown": score_result.get("score_breakdown")
        or raw_result.get("score_breakdown")
        or {},
        "score_explanations": score_result.get("score_explanations")
        or raw_result.get("score_explanations")
        or {},
        "metrics": metrics_payload,
        "suggestions": suggestions_payload,
        "summary": summary_payload,
        "ppt_match": ppt_match,
        "ppt_match_analysis": ppt_match_analysis,
        "ppt_match_source": _ppt_match_src,
        "qa_source": _qa_match_src,
        "content_breakdown": score_result.get("content_breakdown")
        or raw_result.get("content_breakdown"),
        "qa_breakdown": score_result.get("qa_breakdown") or raw_result.get("qa_breakdown"),
        "qa_result": qa_result,
        "transcript": transcript,
        "audio_metrics": audio_metrics,
        "audio_analysis": audio_analysis_payload,
        "vision_valid": vision_state["vision_valid"],
        "vision_message": vision_state["vision_message"],
        "vision_debug_source": vision_state["vision_debug_source"],
        "vision_debug_provider": vision_state["vision_debug_provider"],
        "vision_debug_request_id": vision_state["vision_debug_request_id"],
        "forward_gaze_ratio": vision_metrics["forward_gaze_ratio"],
        "downward_head_ratio": vision_metrics["downward_head_ratio"],
        "posture_stability": vision_metrics["posture_stability"],
        "vision_analysis": {
            "forward_gaze_ratio": vision_metrics["forward_gaze_ratio"],
            "downward_head_ratio": vision_metrics["downward_head_ratio"],
            "posture_stability": vision_metrics["posture_stability"],
            "vision_valid": vision_state["vision_valid"],
            "vision_message": vision_state["vision_message"],
            "vision_debug_source": vision_state["vision_debug_source"],
            "vision_debug_provider": vision_state["vision_debug_provider"],
            "vision_debug_request_id": vision_state["vision_debug_request_id"],
        },
    }
    _dm_out = None
    if isinstance(raw_result, dict):
        _dm_out = raw_result.get("defense_material_mode")
    _dm_out_s = str(_dm_out or "").strip().lower()
    response_payload["defense_material_mode"] = "without_ppt" if _dm_out_s == "without_ppt" else "with_ppt"
    _rtf = _compute_recommended_training_focus(
        response_payload.get("score_breakdown"),
        summary_payload,
        response_payload["defense_material_mode"],
    )
    response_payload["recommended_training_focus"] = _rtf
    print(
        f"[result.api] recommended_training_focus={_rtf!r} session_id={session_id}",
        flush=True,
    )
    _tf_out = _normalize_training_focus_out(
        raw_result.get("training_focus") if isinstance(raw_result, dict) else None
    )
    response_payload["training_focus"] = _tf_out
    print(
        f"[result.api] training_focus={_tf_out!r} session_id={session_id}",
        flush=True,
    )
    raw_vis_in = raw_result.get("vision_analysis") if isinstance(raw_result.get("vision_analysis"), dict) else {}
    for vk in VISION_SESSION_SUMMARY_FIELDS:
        if vk in (raw_result or {}) and raw_result.get(vk) is not None:
            response_payload["vision_analysis"][vk] = raw_result[vk]
        elif vk in raw_vis_in and raw_vis_in.get(vk) is not None:
            response_payload["vision_analysis"][vk] = raw_vis_in[vk]
    _vision_summary_alias_fill(response_payload["vision_analysis"], raw_vis_in)
    for vk in _VISION_ANALYSIS_METADATA_KEYS:
        if vk in raw_vis_in and raw_vis_in.get(vk) is not None:
            response_payload["vision_analysis"][vk] = raw_vis_in[vk]
        elif vk in (raw_result or {}) and raw_result.get(vk) is not None:
            response_payload["vision_analysis"][vk] = raw_result[vk]
    response_payload["audio_session_summary"] = _pick_audio_session_summary(
        raw_result, audio_analysis_payload
    )
    response_payload["vision_session_summary"] = _pick_vision_session_summary(
        raw_result, response_payload["vision_analysis"]
    )
    coach_part = _resolve_coach_payload(
        raw_result,
        score_result,
        ppt_match,
        ppt_match_analysis,
        qa_result,
        raw_result.get("content_document") if isinstance(raw_result.get("content_document"), dict) else None,
        metrics_items=metrics_payload,
        transcript=transcript,
    )
    response_payload["followup_questions"] = coach_part.get("followup_questions") or []
    response_payload["overall_commentary"] = coach_part.get("overall_commentary") or ""
    response_payload["strengths"] = coach_part.get("strengths") if isinstance(coach_part.get("strengths"), list) else []
    response_payload["weaknesses"] = coach_part.get("weaknesses") if isinstance(coach_part.get("weaknesses"), list) else []
    response_payload["next_round_advice"] = (
        coach_part.get("next_round_advice") if isinstance(coach_part.get("next_round_advice"), list) else []
    )
    response_payload["coach_commentary"] = coach_part.get("coach_commentary") or ""
    response_payload["improvement_advice"] = coach_part.get("improvement_advice") or []
    response_payload["coach_metadata"] = coach_part.get("coach_metadata") or {}
    response_payload["question_provider_kind"] = coach_part.get("question_provider_kind") or ""
    response_payload["followup_provider_kind"] = coach_part.get("followup_provider_kind") or ""
    response_payload["commentary_provider_kind"] = coach_part.get("commentary_provider_kind") or ""
    _qr_fu = qa_result if isinstance(qa_result, dict) else {}
    _fgm_r = _qr_fu.get("followup_generation_meta") if isinstance(_qr_fu, dict) else {}
    _fpl_r = _fgm_r.get("provider_label") if isinstance(_fgm_r, dict) else None
    print(
        f"[result.api] followup provider_kind={response_payload.get('followup_provider_kind')!r} "
        f"(qa_result.followup={_qr_fu.get('followup_provider_kind')!r}) session_id={session_id}",
        flush=True,
    )
    print(f"[result.api] followup provider_label={_fpl_r!r} session_id={session_id}", flush=True)
    print(
        f"[result.api] followup fallback_to_rule={bool(_qr_fu.get('followup_fallback_to_rule'))} "
        f"session_id={session_id}",
        flush=True,
    )
    _cgm_out = coach_part.get("commentary_generation_meta")
    if not isinstance(_cgm_out, dict):
        _cgm_out = (coach_part.get("coach_metadata") or {}).get("commentary_generation_meta") or {}
    response_payload["commentary_generation_meta"] = _cgm_out if isinstance(_cgm_out, dict) else {}
    _cfb_out = coach_part.get("commentary_fallback_to_rule")
    if _cfb_out is None and isinstance(coach_part.get("coach_metadata"), dict):
        _cfb_out = coach_part["coach_metadata"].get("commentary_fallback_to_rule")
    response_payload["commentary_fallback_to_rule"] = bool(_cfb_out) if _cfb_out is not None else False
    print(
        f"[result.api] commentary_provider_kind={response_payload.get('commentary_provider_kind')!r} session_id={session_id}",
        flush=True,
    )
    print(
        f"[result.api] commentary_generation_mode={(response_payload.get('commentary_generation_meta') or {}).get('generation_mode')!r} session_id={session_id}",
        flush=True,
    )
    print(
        f"[result.api] overall_commentary={response_payload.get('overall_commentary')!r} session_id={session_id}",
        flush=True,
    )
    print(
        f"[result.api] defense_material_mode={response_payload.get('defense_material_mode')!r} session_id={session_id}",
        flush=True,
    )
    print(
        f"[result.api] strengths={response_payload.get('strengths')!r} session_id={session_id}",
        flush=True,
    )
    print(
        f"[result.api] weaknesses={response_payload.get('weaknesses')!r} session_id={session_id}",
        flush=True,
    )
    if isinstance(raw_result, dict):
        response_payload["followup_questions_chain"] = raw_result.get("followup_questions_chain")
        response_payload["followup_chain_depth"] = raw_result.get("followup_chain_depth")
        response_payload["followup_used"] = raw_result.get("followup_used")
        response_payload["selected_followup_reason"] = raw_result.get("selected_followup_reason")
        _ics = raw_result.get("inference_chain_snapshot")
        if isinstance(_ics, dict):
            response_payload["inference_chain_snapshot"] = _ics
    else:
        response_payload["followup_questions_chain"] = None
        response_payload["followup_chain_depth"] = None
        response_payload["followup_used"] = None
        response_payload["selected_followup_reason"] = None
    score_explanations = response_payload.get("score_explanations") or {}
    print("[result.api] score_explanations raw=", score_explanations)
    print("[result.api] score_explanations type=", type(score_explanations).__name__)
    print(
        "[result.api] score_explanations keys=",
        list(score_explanations.keys()) if isinstance(score_explanations, dict) else None,
    )
    missing_explanations = [
        key for key in ("total", "language", "posture", "content", "qa")
        if not score_explanations.get(key)
    ]
    if missing_explanations:
        print(
            "[result.api] missing score_explanations keys: "
            f"session_id={session_id} missing={missing_explanations!r} "
            f"score_explanations={score_explanations!r}"
        )
    ass = response_payload.get("audio_session_summary")
    if not isinstance(ass, dict) or not ass:
        print(
            "[result.api] missing or empty audio_session_summary "
            f"session_id={session_id} audio_analysis_keys="
            f"{list((audio_analysis_payload or {}).keys()) if isinstance(audio_analysis_payload, dict) else None}"
        )
    vss = response_payload.get("vision_session_summary")
    if not isinstance(vss, dict) or not vss:
        print(
            "[result.api] missing or empty vision_session_summary "
            f"session_id={session_id} vision_analysis_keys="
            f"{list((response_payload.get('vision_analysis') or {}).keys())}"
        )
        _rv = raw_result.get("vision_analysis") if isinstance(raw_result.get("vision_analysis"), dict) else {}
        _long = (
            "total_video_duration_sec",
            "processed_frames",
            "skipped_frames",
            "sampled_mode_used",
            "sampled_fps",
            "valid_detection_frames",
        )
        if not any(_rv.get(k) is not None for k in _long) and not any(
            _rv.get(k) is not None for k in ("vision_skipped_frames", "vision_sampled_fps", "vision_sampled_mode_used")
        ):
            print(
                "[result.api] gap: 入参 raw_result.vision_analysis 未带长时视频标量（Training stop 未传或 vision 未返回） "
                f"session_id={session_id} keys={list(_rv.keys())}"
            )
    print(
        f"[result.api] raw vision_analysis={raw_result.get('vision_analysis')!r} "
        f"session_id={session_id}"
    )
    print(
        f"[result.api] raw vision_session_summary={raw_result.get('vision_session_summary')!r} "
        f"session_id={session_id}"
    )
    _vss_out = response_payload.get("vision_session_summary")
    print(
        f"[result.api] vision_session_summary={_vss_out!r} "
        f"session_id={session_id}"
    )
    _pm_out = response_payload.get("ppt_match")
    _has_pm = isinstance(_pm_out, dict) and bool(_pm_out)
    _pm_sum = ""
    if _has_pm:
        _pm_sum = (
            f"page_index={_pm_out.get('page_index')!r} "
            f"match_source={str(_pm_out.get('match_source') or '')!r} "
            f"match_score={_pm_out.get('match_score')!r}"
        )
    print(
        "[result.api] has_ppt_match=",
        _has_pm,
        "ppt_match_source=",
        response_payload.get("ppt_match_source"),
        "ppt_match=",
        _pm_out,
        "qa_source=",
        response_payload.get("qa_source"),
        f"session_id={session_id}",
        flush=True,
    )
    if _pm_sum:
        print("[result.api] ppt_match summary=", _pm_sum, f"session_id={session_id}", flush=True)
    return response_payload


@router.get("/history", response_model=HistoryResponse)
def get_history(
    db: Session = Depends(get_db),
    user: User = Depends(require_user),
    review_focus: str | None = Query(
        None,
        description="language | posture | qa | content 时返回 focus_review_* 专项复盘摘要",
    ),
):
    print(f"[history.user] current_user_id={user.id}", flush=True)
    print(f"[history.user] filtered_by_user={user.id}", flush=True)
    history_items = _collect_history_items(db, user.id)
    enriched: list[HistoryItem] = []
    for item in history_items:
        e = _enrich_history_item_focus_trend(history_items, item)
        e = _enrich_history_focus_key_metrics(db, history_items, e, user.id)
        enriched.append(e)
        focus = _normalize_training_focus_out(item.training_focus)
        if focus != "none":
            rs = e.focus_recent_scores or []
            scores_only = [x.get("core_score") for x in rs if x.get("core_score") is not None]
            print(
                f"[history.api] focus trend training_focus={focus!r} session_id={item.session_id}",
                flush=True,
            )
            print(
                f"[history.api] recent_scores={scores_only!r} session_id={item.session_id}",
                flush=True,
            )
    for hi in enriched:
        print(
            f"[history.api] item training_focus={hi.training_focus!r} session_id={hi.session_id}",
            flush=True,
        )
        print(
            f"[history.api] training_valid={hi.training_valid} session_id={hi.session_id}",
            flush=True,
        )
        print(
            f"[history.api] invalid_reason_summary={hi.invalid_reason_summary!r} session_id={hi.session_id}",
            flush=True,
        )
        _fp = hi.focus_primary_score
        _vp = hi.focus_vs_previous
        if _normalize_training_focus_out(hi.training_focus) != "none":
            print(
                f"[history.api] item focus_primary_score={_fp!r} focus_vs_previous={_vp!r} "
                f"session_id={hi.session_id}",
                flush=True,
            )
    review = _build_history_focus_review_fields(enriched, review_focus)
    if review.get("focus_review_summary"):
        print(
            f"[history.api] focus_review_summary={review['focus_review_summary']!r} "
            f"review_focus={review_focus!r}",
            flush=True,
        )
        print(
            f"[history.api] focus_review_next_action={review.get('focus_review_next_action')!r} "
            f"review_focus={review_focus!r}",
            flush=True,
        )
    valid_training_overview = _build_valid_training_overview(enriched, recent_n=_OVERVIEW_RECENT_N)
    print(
        f"[history.api] valid_training_overview={valid_training_overview.model_dump()!r}",
        flush=True,
    )
    print(
        "[history.api] latest_valid_config="
        + repr(
            {
                "scoring_profile": valid_training_overview.latest_valid_scoring_profile,
                "defense_material_mode": valid_training_overview.latest_valid_defense_material_mode,
                "training_focus": valid_training_overview.latest_valid_training_focus,
            }
        ),
        flush=True,
    )
    return HistoryResponse(
        history=enriched,
        focus_review_summary=review.get("focus_review_summary"),
        focus_review_scores=review.get("focus_review_scores"),
        focus_review_trend=review.get("focus_review_trend"),
        focus_review_next_action=review.get("focus_review_next_action"),
        valid_training_overview=valid_training_overview,
    )


@router.delete("/history/{session_id}", response_model=HistoryDeleteOneResponse)
def delete_history_session(
    session_id: str,
    db: Session = Depends(get_db),
    user: User = Depends(require_user),
):
    sid = str(session_id or "").strip()
    if not sid:
        raise HTTPException(status_code=400, detail="缺少 session_id")
    print(f"[history.user] current_user_id={user.id}", flush=True)
    print(f"[history.user] filtered_by_user={user.id}", flush=True)
    print(f"[history.api] delete session_id={sid}", flush=True)
    items = _collect_history_items(db, user.id)
    if not any(x.session_id == sid for x in items):
        raise HTTPException(status_code=404, detail="记录不存在或已删除")
    purged = _purge_training_session_storage(sid, db)
    print(
        f"[history.api] deleted_count=1 session_id={sid} "
        f"had_db_record={purged.get('had_db_record')} "
        f"removed_results={purged.get('removed_results')} "
        f"removed_sessions={purged.get('removed_sessions')}",
        flush=True,
    )
    return HistoryDeleteOneResponse(
        ok=True,
        session_id=sid,
        had_db_record=bool(purged.get("had_db_record")),
        removed_results=bool(purged.get("removed_results")),
        removed_sessions=bool(purged.get("removed_sessions")),
    )


@router.post("/history/clear-invalid", response_model=HistoryClearInvalidResponse)
def clear_invalid_history_sessions(
    db: Session = Depends(get_db),
    user: User = Depends(require_user),
):
    print(f"[history.user] current_user_id={user.id}", flush=True)
    print(f"[history.user] filtered_by_user={user.id}", flush=True)
    print("[history.api] delete invalid_only=true", flush=True)
    items = _collect_history_items(db, user.id)
    invalid_ids = [x.session_id for x in items if x.training_valid is False]
    deleted_count = 0
    for iid in invalid_ids:
        _purge_training_session_storage(iid, db)
        deleted_count += 1
    print(f"[history.api] deleted_count={deleted_count}", flush=True)
    return HistoryClearInvalidResponse(
        ok=True,
        deleted_count=deleted_count,
        session_ids=list(invalid_ids),
    )


@router.get("/result/{session_id}")
def get_result(
    session_id: str,
    db: Session = Depends(get_db),
    user: User = Depends(require_user),
):
    sid = str(session_id or "").strip()
    print(f"[result.user] current_user_id={user.id}", flush=True)
    db_record = db.query(TrainingRecord).filter(TrainingRecord.session_id == sid).first()
    result_mem = results.get(sid)
    owner_log = None
    if db_record is not None and getattr(db_record, "user_id", None) is not None:
        owner_log = db_record.user_id
    elif isinstance(result_mem, dict) and result_mem.get("user_id") is not None:
        owner_log = coerce_user_id(result_mem.get("user_id"))
    print(f"[result.user] result_owner_id={owner_log}", flush=True)

    if db_record and db_record.status == "completed":
        if not training_record_owned_by(db_record, user):
            raise HTTPException(status_code=404, detail="暂无该训练结果或无权查看")
        metrics = []
        metrics_data = []
        ppt_match = None
        ppt_match_analysis = None
        qa_result = None
        transcript = db_record.transcript_text or None
        audio_metrics = None

        raw_stored: dict = {}
        if db_record.metrics_json:
            try:
                metrics_data, raw_stored = _parse_metrics_json_blob(db_record.metrics_json)
                metrics = [MetricItem(**m) for m in metrics_data]
            except Exception:
                metrics = []
                metrics_data = []
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
        sp_col = getattr(db_record, "scoring_profile", None)
        spl_col = getattr(db_record, "scoring_profile_label", None)
        if sp_col and raw_for_payload.get("scoring_profile") is None:
            raw_for_payload["scoring_profile"] = sp_col
        if spl_col and raw_for_payload.get("scoring_profile_label") is None:
            raw_for_payload["scoring_profile_label"] = spl_col

        picked_tf = _pick_training_focus_for_session(session_id, raw_stored, db_record)
        if picked_tf is not None:
            raw_for_payload["training_focus"] = picked_tf

        response_payload = _compose_result_payload(
            session_id=db_record.session_id,
            raw_result=raw_for_payload,
            metrics_items=[m.model_dump() for m in metrics],
            transcript=transcript,
            audio_metrics=audio_metrics,
            ppt_match=ppt_match,
            ppt_match_analysis=ppt_match_analysis,
            qa_result=qa_result,
            summary=None,
        )
        print(
            "[result.api] returning vision fields="
            f"{ {k: response_payload.get(k) for k in ('forward_gaze_ratio', 'downward_head_ratio', 'posture_stability', 'vision_valid', 'vision_message', 'vision_debug_source', 'vision_debug_provider', 'vision_debug_request_id')} }"
        )
        print(
            f"[result.api] scoring_profile raw={response_payload.get('scoring_profile')!r} "
            f"scoring_profile_label raw={response_payload.get('scoring_profile_label')!r}"
        )
        _vo = response_payload.get("vision_session_summary")
        _vod = _vo if isinstance(_vo, dict) else {}
        print(
            f"[result.api] vision_session_summary={response_payload.get('vision_session_summary')!r} "
            f"session_id={session_id}"
        )
        print(
            f"[result.api] get_result OUT session_id={session_id} "
            f"vision_analysis keys={list((response_payload.get('vision_analysis') or {}).keys())} "
            f"total_video_duration_sec={_vod.get('total_video_duration_sec')} "
            f"duration_source={_vod.get('duration_source')!r} "
            f"processed_frames={_vod.get('processed_frames')} "
            f"skipped_frames={_vod.get('skipped_frames')}"
        )
        print(
            "[result.api.debug] raw_result keys",
            sorted(raw_for_payload.keys()) if isinstance(raw_for_payload, dict) else None,
            f"session_id={session_id}",
            flush=True,
        )
        print(
            "[result.api.debug] stored ppt_match",
            response_payload.get("ppt_match"),
            "stored ppt_match_source",
            response_payload.get("ppt_match_source"),
            f"session_id={session_id}",
            flush=True,
        )
        _log_result_api_ppt_fields(response_payload, session_id)
        print(
            f"[result.api] get_result defense_material_mode={response_payload.get('defense_material_mode')!r} "
            f"session_id={session_id}",
            flush=True,
        )
        print(
            f"[result.api] get_result training_focus={response_payload.get('training_focus')!r} "
            f"session_id={session_id}",
            flush=True,
        )
        if not response_payload.get("session_name"):
            response_payload["session_name"] = db_record.session_name
        _apply_training_validity_to_payload(sid, response_payload)
        _apply_training_focus_trend_to_payload(
            db, sid, response_payload, db_record.start_time, user.id
        )
        return response_payload
    elif result_mem and isinstance(result_mem, dict):
        if not memory_payload_owned_by(result_mem, user):
            raise HTTPException(status_code=404, detail="暂无该训练结果或无权查看")
        result_data = result_mem
        response_payload = _compose_result_payload(
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
        print(
            "[result.api] returning vision fields="
            f"{ {k: response_payload.get(k) for k in ('forward_gaze_ratio', 'downward_head_ratio', 'posture_stability', 'vision_valid', 'vision_message', 'vision_debug_source', 'vision_debug_provider', 'vision_debug_request_id')} }"
        )
        print(
            f"[result.api] scoring_profile raw={response_payload.get('scoring_profile')!r} "
            f"scoring_profile_label raw={response_payload.get('scoring_profile_label')!r}"
        )
        _vo = response_payload.get("vision_session_summary")
        _vod = _vo if isinstance(_vo, dict) else {}
        print(
            f"[result.api] vision_session_summary={response_payload.get('vision_session_summary')!r} "
            f"session_id={session_id}"
        )
        print(
            f"[result.api] get_result OUT session_id={session_id} "
            f"vision_analysis keys={list((response_payload.get('vision_analysis') or {}).keys())} "
            f"total_video_duration_sec={_vod.get('total_video_duration_sec')} "
            f"duration_source={_vod.get('duration_source')!r} "
            f"processed_frames={_vod.get('processed_frames')} "
            f"skipped_frames={_vod.get('skipped_frames')}"
        )
        print(
            "[result.api.debug] raw_result keys",
            sorted(result_data.keys()) if isinstance(result_data, dict) else None,
            f"session_id={session_id}",
            flush=True,
        )
        print(
            "[result.api.debug] stored ppt_match",
            response_payload.get("ppt_match"),
            "stored ppt_match_source",
            response_payload.get("ppt_match_source"),
            f"session_id={session_id}",
            flush=True,
        )
        _log_result_api_ppt_fields(response_payload, session_id)
        print(
            f"[result.api] get_result defense_material_mode={response_payload.get('defense_material_mode')!r} "
            f"session_id={session_id}",
            flush=True,
        )
        print(
            f"[result.api] get_result training_focus={response_payload.get('training_focus')!r} "
            f"session_id={session_id}",
            flush=True,
        )
        if not response_payload.get("session_name"):
            response_payload["session_name"] = result_data.get("session_name") or f"训练_{sid[:8]}"
        _ts = sessions.get(sid, {}).get("start_time") if sid in sessions else None
        _apply_training_validity_to_payload(sid, response_payload)
        _apply_training_focus_trend_to_payload(db, sid, response_payload, _ts, user.id)
        return response_payload
    else:
        raise HTTPException(status_code=404, detail="结果不存在")
