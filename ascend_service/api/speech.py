from __future__ import annotations

import os
import tempfile
import time
from pathlib import Path

from fastapi import APIRouter, File, Form, UploadFile

from ascend_service.schemas.protocol import AscendResponse
from ascend_service.services.speech_service import analyze_audio, get_last_speech_analyze_debug

router = APIRouter()
TEMPLATE_CONTAMINATION_PHRASES = (
    "面试答辩现场录音转写",
    "中文口语内容",
    "录音转写",
    "现场录音转写",
)
TEMPLATE_CONTAMINATION_MESSAGE = "检测到模板化伪转写，请重新录音"


def _normalize_api_analysis_phase(
    analysis_phase: str | None,
    audio_source: str | None,
) -> str:
    raw = (analysis_phase or audio_source or "").strip().lower()
    if raw in ("qa_answer", "qa", "qa_answer_phase"):
        return "qa_answer"
    return "lecture"


def _normalize_for_template_match(text: str) -> str:
    normalized = str(text or "")
    normalized = normalized.replace(" ", "")
    normalized = "".join(ch for ch in normalized if ch.isalnum() or ("\u4e00" <= ch <= "\u9fff"))
    return normalized


def _compress_repeated_sentences(text: str) -> str:
    normalized = str(text or "").strip()
    normalized = normalized.replace("！", "。").replace("？", "。").replace(";", "。").replace("；", "。")
    normalized = normalized.replace(",", "。").replace("，", "。")
    parts = [p.strip() for p in normalized.split("。") if p.strip()]
    compressed: list[str] = []
    for part in parts:
        if not compressed or compressed[-1] != part:
            compressed.append(part)
    return "。".join(compressed)


def _api_detect_template_contamination(text: str) -> tuple[bool, str]:
    transcript = str(text or "").strip()
    compact = _normalize_for_template_match(transcript)
    compressed = _normalize_for_template_match(_compress_repeated_sentences(transcript))
    for phrase in TEMPLATE_CONTAMINATION_PHRASES:
        phrase_norm = _normalize_for_template_match(phrase)
        if phrase_norm and (phrase_norm in compact or phrase_norm in compressed):
            return True, f"命中 API 模板污染短语: {phrase}"
    return False, ""


def _normalize_result(raw_result: dict, request_id: str) -> dict:
    base = {
        "transcript": str(raw_result.get("transcript") or ""),
        "speech_rate": float(raw_result.get("speech_rate", 0.0)),
        "pause_count": int(raw_result.get("pause_count", 0)),
        "avg_pause_sec": float(raw_result.get("avg_pause_sec", 0.0)),
        "filler_count": int(raw_result.get("filler_count", 0)),
        "audio_valid": bool(raw_result.get("audio_valid", False)),
        "audio_message": str(raw_result.get("audio_message") or ""),
        "audio_debug_source": "ascend_service",
        "audio_debug_provider": "ascend-service",
        "audio_debug_request_id": request_id,
    }
    for key in (
        "merged_transcript",
        "total_audio_duration_sec",
        "transcribed_chunks",
        "skipped_chunks",
        "dropped_dirty_chunks",
        "total_chunks",
        "chunked_mode_used",
        "audio_metrics_scope",
        "adequacy_gate_hit",
        "adequacy_gate_reason",
        "short_adequacy_gate_hit",
        "short_adequacy_gate_reason",
        "transcript_chars_per_minute",
        "avg_chars_per_chunk",
    ):
        if key in raw_result and raw_result[key] is not None:
            base[key] = raw_result[key]
    return base


def _handle_speech_upload(
    request_id: str,
    audio_file: UploadFile,
    *,
    analysis_phase: str = "",
    audio_source: str = "",
) -> AscendResponse:
    req_id = str(request_id or "").strip() or "mock-request"
    api_phase = _normalize_api_analysis_phase(analysis_phase or None, audio_source or None)
    suffix = Path(audio_file.filename or "").suffix or ".wav"
    tmp_path: str | None = None
    dbg: dict = {}
    try:
        with tempfile.NamedTemporaryFile(prefix="ascend_speech_", suffix=suffix, delete=False) as tmp:
            content = audio_file.file.read()
            tmp.write(content)
            tmp_path = tmp.name
        print(
            "[ascend_service.api.speech] uploaded file saved "
            f"request_id={req_id} phase={api_phase} filename={audio_file.filename!r} "
            f"tmp_path={tmp_path} bytes={len(content)}"
        )
        t_svc0 = time.perf_counter()
        raw_result = analyze_audio(tmp_path, analysis_phase=api_phase)
        svc_wall_ms = (time.perf_counter() - t_svc0) * 1000.0
        dbg = get_last_speech_analyze_debug()
        result = _normalize_result(raw_result, req_id)
        transcript = str(result.get("transcript") or "")
        contamination_hit, contamination_reason = _api_detect_template_contamination(transcript)
        print(
            "[ascend_service.api.speech] contamination gate "
            f"api_contamination_hit={contamination_hit} "
            f"api_contamination_reason={contamination_reason!r}"
        )
        if result.get("audio_valid") is False or contamination_hit:
            result["transcript"] = ""
            result["audio_valid"] = False
            if contamination_hit:
                result["audio_message"] = TEMPLATE_CONTAMINATION_MESSAGE
        tr_show = str(result.get("transcript") or "")
        print(
            "[ascend_service.api.speech] SUMMARY "
            f"request_id={req_id} audio_valid={result.get('audio_valid')} "
            f"audio_message={result.get('audio_message')!r} "
            f"contamination_hit={contamination_hit} contamination_reason={contamination_reason!r} "
            f"speech_rate={result.get('speech_rate')} transcript_len={len(tr_show)} "
            f"pause_count={result.get('pause_count')} avg_pause_sec={result.get('avg_pause_sec')} "
            f"filler_count={result.get('filler_count')} "
            f"transcript_preview={tr_show[:180]!r}"
        )
        print(
            "[ascend_service.api.speech] FINAL "
            f"request_id={req_id} phase={api_phase} audio_valid={result.get('audio_valid')} "
            f"audio_message={result.get('audio_message')!r} transcript_len={len(tr_show)} "
            f"speech_rate={result.get('speech_rate')} contamination_hit={contamination_hit} "
            f"model_size_used={dbg.get('model_size_used')} model_cache_hit={dbg.get('model_cache_hit')} "
            f"normalize_elapsed_ms={dbg.get('normalize_elapsed_ms')} "
            f"chunk_asr_elapsed_ms={dbg.get('chunk_asr_elapsed_ms')} "
            f"metrics_elapsed_ms={dbg.get('metrics_elapsed_ms')} "
            f"final_gate_elapsed_ms={dbg.get('final_gate_elapsed_ms')} "
            f"chunked_mode_used={dbg.get('chunked_mode_used')} total_chunks={dbg.get('total_chunks')} "
            f"skipped_chunks={dbg.get('skipped_chunks')} transcribed_chunks={dbg.get('transcribed_chunks')} "
            f"dropped_dirty_chunks={dbg.get('dropped_dirty_chunks')} "
            f"total_elapsed_ms={dbg.get('total_elapsed_ms')} api_handler_elapsed_ms={svc_wall_ms:.1f} "
            f"adequacy_gate_hit={result.get('adequacy_gate_hit')} "
            f"adequacy_gate_reason={result.get('adequacy_gate_reason')!r} "
            f"short_adequacy_gate_hit={result.get('short_adequacy_gate_hit')} "
            f"short_adequacy_gate_reason={result.get('short_adequacy_gate_reason')!r} "
            f"total_audio_duration_sec={result.get('total_audio_duration_sec')}"
        )
        return AscendResponse(
            success=True,
            provider="ascend-service",
            request_id=req_id,
            result=result,
            error=None,
        )
    except Exception as e:
        dbg = get_last_speech_analyze_debug()
        print(f"[ascend_service.api.speech] analyze failed request_id={req_id} err={repr(e)}")
        result = _normalize_result(
            {
                "transcript": "",
                "speech_rate": 0.0,
                "pause_count": 0,
                "avg_pause_sec": 0.0,
                "filler_count": 0,
                "audio_valid": False,
                "audio_message": "语音分析失败，请重试",
            },
            req_id,
        )
        print(f"[ascend_service.api.speech] degrade return result={result}")
        return AscendResponse(
            success=True,
            provider="ascend-service",
            request_id=req_id,
            result=result,
            error=None,
        )
    finally:
        try:
            if tmp_path and os.path.exists(tmp_path):
                os.remove(tmp_path)
                print(
                    "[ascend_service.api.speech] temp file cleaned "
                    f"request_id={req_id} tmp_path={tmp_path}"
                )
        except Exception as cleanup_err:
            print(
                "[ascend_service.api.speech] temp file cleanup failed "
                f"request_id={req_id} tmp_path={tmp_path} err={repr(cleanup_err)}"
            )


@router.post("/speech/analyze", response_model=AscendResponse)
def speech_analyze(
    request_id: str = Form(default=""),
    analysis_phase: str = Form(default=""),
    audio_source: str = Form(default=""),
    audio_file: UploadFile = File(...),
) -> AscendResponse:
    return _handle_speech_upload(
        request_id=request_id,
        audio_file=audio_file,
        analysis_phase=analysis_phase,
        audio_source=audio_source,
    )


# 兼容当前主项目 mock 联调路径，不影响标准路径
@router.post("/mock/speech/analyze", response_model=AscendResponse)
def speech_analyze_mock_compat(
    request_id: str = Form(default=""),
    analysis_phase: str = Form(default=""),
    audio_source: str = Form(default=""),
    audio_file: UploadFile = File(...),
) -> AscendResponse:
    return _handle_speech_upload(
        request_id=request_id,
        audio_file=audio_file,
        analysis_phase=analysis_phase,
        audio_source=audio_source,
    )
