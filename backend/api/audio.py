import os
import time
import uuid
import traceback

from datetime import datetime



from fastapi import APIRouter, UploadFile, File, HTTPException, Query



from factories.provider_factory import get_ai_provider_status, get_speech_ai_provider



router = APIRouter()
TEMPLATE_CONTAMINATION_PHRASES = (
    "面试答辩现场录音转写",
    "中文口语内容",
    "录音转写",
    "现场录音转写",
)
TEMPLATE_CONTAMINATION_MESSAGE = "检测到模板化伪转写，请重新录音"



AUDIO_UPLOAD_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), "data", "audio_uploads")

os.makedirs(AUDIO_UPLOAD_DIR, exist_ok=True)


def _normalize_for_template_match(text: str) -> str:
    normalized = str(text or "")
    normalized = "".join(ch for ch in normalized if not ch.isspace())
    normalized = "".join(ch for ch in normalized if ch.isalnum() or ("\u4e00" <= ch <= "\u9fff"))
    return normalized


def _compress_repeated_sentences(text: str) -> str:
    normalized = str(text or "").strip()
    for ch in ("！", "？", "；", ";", ",", "，"):
        normalized = normalized.replace(ch, "。")
    parts = [p.strip() for p in normalized.split("。") if p.strip()]
    compressed: list[str] = []
    for part in parts:
        if not compressed or compressed[-1] != part:
            compressed.append(part)
    return "。".join(compressed)


def _resolve_http_analysis_phase(
    *,
    analysis_phase: str | None,
    audio_source: str | None,
    audio_context: str | None,
) -> str:
    """归一为 ascend / speech_service 使用的 phase：lecture | qa_answer。"""
    raw = (analysis_phase or audio_source or "").strip().lower()
    if raw in ("qa_answer", "qa", "qa_answer_phase"):
        return "qa_answer"
    if raw in ("lecture", "lecture_phase"):
        return "lecture"
    if raw:
        if "qa" in raw:
            return "qa_answer"
        return "lecture"
    _ctx_raw = (audio_context or "").strip()
    _legacy = {
        "lecture_session": "lecture_phase",
        "qa_answer": "qa_answer_phase",
    }
    _ctx = _legacy.get(_ctx_raw, _ctx_raw) or "lecture_phase"
    if _ctx == "qa_answer_phase":
        return "qa_answer"
    return "lecture"


def _contains_template_contamination(text: str) -> bool:
    transcript = str(text or "").strip()
    compact = _normalize_for_template_match(transcript)
    compressed = _normalize_for_template_match(_compress_repeated_sentences(transcript))
    for phrase in TEMPLATE_CONTAMINATION_PHRASES:
        phrase_norm = _normalize_for_template_match(phrase)
        if phrase_norm and (phrase_norm in compact or phrase_norm in compressed):
            return True
    return False





@router.post("/audio/analyze")

async def analyze_audio(
    file: UploadFile = File(...),
    audio_context: str | None = Query(
        default=None,
        description="兼容旧参数：lecture_phase / qa_answer_phase 等；优先使用 analysis_phase。",
    ),
    analysis_phase: str | None = Query(
        default=None,
        description="讲解 lecture | 问答语音 qa_answer（透传 ascend 污染闸门口径）。",
    ),
    audio_source: str | None = Query(
        default=None,
        description="与 analysis_phase 二选一，供前端别名。",
    ),
):

    if not file:

        raise HTTPException(status_code=400, detail="缺少音频文件")

    api_phase = _resolve_http_analysis_phase(
        analysis_phase=analysis_phase,
        audio_source=audio_source,
        audio_context=audio_context,
    )
    _phase_lane = "qa_answer_phase" if api_phase == "qa_answer" else "lecture_phase"
    print(f"[audio.analyze.phase] {_phase_lane} resolved_api_phase={api_phase!r}", flush=True)
    _raw = (audio_context or "").strip()
    _legacy = {
        "lecture_session": "lecture_phase",
        "qa_answer": "qa_answer_phase",
    }
    _ctx = _legacy.get(_raw, _raw) or "lecture_phase"
    print(
        f"[audio.analyze.api] phase={api_phase} audio_context={_ctx!r} filename={file.filename!r}",
        flush=True,
    )



    ext = os.path.splitext(file.filename or "")[1].lower() or ".webm"

    save_name = f"{uuid.uuid4().hex}_{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}{ext}"

    save_path = os.path.join(AUDIO_UPLOAD_DIR, save_name)



    try:

        content = await file.read()

        with open(save_path, "wb") as f:

            f.write(content)

    except Exception as e:

        raise HTTPException(status_code=500, detail=f"保存音频失败: {e}")



    try:

        file_size = os.path.getsize(save_path)

        print(f"[audio.analyze] file_path={save_path} ext={ext} size={file_size}")

    except Exception:

        file_size = -1



    analyze_elapsed_ms = 0.0
    provider_kind = "unknown"
    try:

        # 成功时返回 JSON，可含 audio_valid / audio_message（静音保护时 transcript 为空，HTTP 仍为 200）
        st = get_ai_provider_status()
        provider_kind = st.get("speech_provider", "unknown")
        if provider_kind == "ascend":
            print(
                "[backend.speech] formal_route=frontend->main_backend(/api/audio/analyze)"
                "->multipart->ascend_service(/speech/analyze) "
                f"speech_inference_backend={st.get('speech_inference_backend')!r} "
                f"speech_full_url_hint={st.get('speech_full_url_hint')!r} "
                f"ascend_speech_timeout_seconds={st.get('ascend_speech_timeout_seconds')} "
                f"speech_ascend_url_ready={st.get('speech_ascend_url_ready')}",
                flush=True,
            )
        else:
            print(
                "[backend.speech] formal_route=frontend->main_backend(/api/audio/analyze)"
                f"->local_whisper speech_inference_backend={st.get('speech_inference_backend')!r}",
                flush=True,
            )
        t_analyze = time.perf_counter()
        result = get_speech_ai_provider().analyze_audio(save_path, analysis_phase=api_phase)
        analyze_elapsed_ms = (time.perf_counter() - t_analyze) * 1000.0
        if provider_kind == "ascend" and isinstance(result, dict):
            print(
                "[backend.speech] ascend_service_returned "
                f"request_id={result.get('request_id')!r} "
                f"board_provider={result.get('provider')!r} "
                f"audio_valid={result.get('audio_valid')}",
                flush=True,
            )
        if isinstance(result, dict) and result.get("audio_valid") is False:
            # 防御式兜底：低质量/无语音场景不向前端透传幻觉文本，且数值勿伪装成有效分析
            result["transcript"] = ""
            result["speech_rate"] = 0
            result["pause_count"] = 0
            result["avg_pause_sec"] = 0.0
            result["filler_count"] = 0
            if not (result.get("audio_message") or "").strip():
                result["audio_message"] = (
                    "本轮未能从录音中稳定识别有效语音，可能环境过静、过短或识别不稳定。"
                    "下方数值为占位，不作为有效语言分析依据。"
                )
        if isinstance(result, dict):
            original_transcript = str(result.get("transcript") or "")
            if _contains_template_contamination(original_transcript):
                rewritten = {
                    "transcript": "",
                    "merged_transcript": "",
                    "speech_rate": 0,
                    "pause_count": 0,
                    "avg_pause_sec": 0,
                    "filler_count": 0,
                    "audio_valid": False,
                    "audio_message": TEMPLATE_CONTAMINATION_MESSAGE,
                    "total_audio_duration_sec": 0.0,
                    "transcribed_chunks": 0,
                    "skipped_chunks": 0,
                    "dropped_dirty_chunks": 0,
                    "total_chunks": 0,
                    "chunked_mode_used": False,
                    "audio_metrics_scope": "session_invalid_contamination",
                }
                print(
                    "[audio.analyze.api] contamination fallback triggered "
                    f"original_transcript={original_transcript!r} rewritten_result={rewritten}"
                )
                result = rewritten

        print(f"[audio.analyze.api] result={result}")
        if isinstance(result, dict):
            tr = str(result.get("transcript") or "")
            outcome = "success"
            if result.get("audio_valid") is False:
                outcome = "invalid"
            print(
                "[audio.analyze.api] FINAL "
                f"audio_valid={result.get('audio_valid')} "
                f"audio_message={result.get('audio_message')!r} transcript_len={len(tr)} "
                f"speech_rate={result.get('speech_rate')} outcome={outcome} "
                f"adequacy_gate_hit={result.get('adequacy_gate_hit')} "
                f"adequacy_gate_reason={result.get('adequacy_gate_reason')!r} "
                f"total_audio_duration_sec={result.get('total_audio_duration_sec')}"
            )
            if result.get("adequacy_gate_hit") is not None or result.get("adequacy_gate_reason"):
                print(
                    "[audio.analyze.api] adequacy_debug "
                    f"adequacy_gate_hit={result.get('adequacy_gate_hit')} "
                    f"adequacy_gate_reason={result.get('adequacy_gate_reason')!r} "
                    f"transcript_chars_per_minute={result.get('transcript_chars_per_minute')} "
                    f"avg_chars_per_chunk={result.get('avg_chars_per_chunk')}"
                )
            print(
                "[audio.analyze.baseline] "
                f"upload_bytes={file_size} analyze_elapsed_ms={analyze_elapsed_ms:.1f} "
                f"audio_valid={result.get('audio_valid')} transcript_len={len(tr)} "
                f"provider={provider_kind} "
                f"board_provider={result.get('provider')!r} "
                f"outcome={outcome}"
            )

        if isinstance(result, dict) and result.get("audio_valid") is False:
            result["merged_transcript"] = ""
        return result

    except Exception as e:

        traceback.print_exc()
        msg = str(e)
        msg_l = msg.lower()
        if "请求超时" in msg or "timeout=" in msg_l or "timed out" in msg_l:
            degraded = {
                "transcript": "",
                "merged_transcript": "",
                "speech_rate": 0,
                "pause_count": 0,
                "avg_pause_sec": 0.0,
                "filler_count": 0,
                "audio_valid": False,
                "audio_message": "语音分析超时，请缩短录音时长或稍后重试",
                "total_audio_duration_sec": 0.0,
                "transcribed_chunks": 0,
                "skipped_chunks": 0,
                "dropped_dirty_chunks": 0,
                "total_chunks": 0,
                "chunked_mode_used": False,
                "audio_metrics_scope": "session_timeout",
            }
            print(f"[audio.analyze.api] timeout degraded result={degraded} err={repr(e)}")
            print(
                "[backend.speech] ascend_timeout_fallback=main_backend_session_timeout_payload "
                f"speech_provider={provider_kind!r}",
                flush=True,
            )
            pk = get_ai_provider_status().get("speech_provider", "unknown")
            print(
                "[audio.analyze.baseline] "
                f"upload_bytes={file_size} analyze_elapsed_ms={analyze_elapsed_ms:.1f} "
                f"audio_valid=False transcript_len=0 provider={pk} outcome=timeout"
            )
            return degraded
        pk = get_ai_provider_status().get("speech_provider", "unknown")
        print(
            "[audio.analyze.baseline] "
            f"upload_bytes={file_size} analyze_elapsed_ms={analyze_elapsed_ms:.1f} "
            f"provider={pk} outcome=exception err={repr(e)[:200]}"
        )
        raise HTTPException(status_code=500, detail=f"音频分析失败: {repr(e)}")

