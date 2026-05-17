import os
import time
import uuid
import traceback
from datetime import datetime

from fastapi import APIRouter, UploadFile, File, HTTPException

from factories.provider_factory import get_ai_provider_status, get_vision_ai_provider

router = APIRouter()

VIDEO_UPLOAD_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), "data", "video_uploads")
os.makedirs(VIDEO_UPLOAD_DIR, exist_ok=True)


@router.post("/vision/analyze")
async def analyze_vision_video(file: UploadFile = File(...)):
    """视觉分析：上传视频文件，返回仪态/视线等占位或真实指标（由 VisionAIProvider 决定）。"""
    if not file:
        raise HTTPException(status_code=400, detail="缺少视频文件")

    ext = os.path.splitext(file.filename or "")[1].lower() or ".webm"
    save_name = f"{uuid.uuid4().hex}_{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}{ext}"
    save_path = os.path.join(VIDEO_UPLOAD_DIR, save_name)

    upload_bytes = -1
    try:
        content = await file.read()
        with open(save_path, "wb") as f:
            f.write(content)
        upload_bytes = len(content)
        print(f"[vision.analyze.api] saved_video_path={save_path} size={upload_bytes}")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"保存视频失败: {e}")

    analyze_elapsed_ms = 0.0
    try:
        provider_kind = get_ai_provider_status().get("vision_provider", "unknown")
        t0 = time.perf_counter()
        try:
            result = get_vision_ai_provider().analyze_video(save_path)
        finally:
            analyze_elapsed_ms = (time.perf_counter() - t0) * 1000.0
        total_frames = result.get("total_frames")
        valid_frames = result.get("valid_detection_frames")
        v_ok = result.get("vision_valid") is True
        default_invalid_msg = (
            "本次视频未能形成稳定的仪态检测依据（例如有效画面过少或检测不稳），"
            "未将视觉指标作为有效评分依据。"
        )
        payload = {
            "forward_gaze_ratio": result.get("forward_gaze_ratio") if v_ok else 0.0,
            "downward_head_ratio": result.get("downward_head_ratio") if v_ok else 0.0,
            "posture_stability": result.get("posture_stability") if v_ok else 0.0,
            "vision_valid": result.get("vision_valid"),
            "vision_message": (result.get("vision_message") or "").strip()
            if v_ok
            else ((result.get("vision_message") or "").strip() or default_invalid_msg),
            "vision_debug_source": result.get("vision_debug_source"),
            "vision_debug_provider": result.get("vision_debug_provider"),
            "vision_debug_request_id": result.get("vision_debug_request_id"),
        }
        for key in (
            "processed_frames",
            "skipped_frames",
            "total_video_duration_sec",
            "duration_source",
            "sampled_mode_used",
            "sampled_fps",
            "vision_original_fps",
            "vision_sampled_fps",
            "vision_skipped_frames",
            "vision_sampled_mode_used",
            "vision_analysis_elapsed_ms",
            "vision_metrics_scope",
            "total_frames",
            "valid_detection_frames",
        ):
            if key in result and result.get(key) is not None:
                payload[key] = result[key]
        outcome = "success"
        if payload.get("vision_valid") is False:
            outcome = "invalid"
        print(
            "[vision.analyze.api] "
            f"total_frames={total_frames} valid_detection_frames={valid_frames} "
            f"forward_gaze_ratio={payload['forward_gaze_ratio']} "
            f"downward_head_ratio={payload['downward_head_ratio']} "
            f"posture_stability={payload['posture_stability']} "
            f"vision_valid={payload['vision_valid']} "
            f"vision_message={payload['vision_message']!r} "
            f"outcome={outcome}"
        )
        print(
            "[vision.analyze.api] final_metrics: "
            f"final forward_gaze_ratio={payload['forward_gaze_ratio']}, "
            f"final downward_head_ratio={payload['downward_head_ratio']}, "
            f"final posture_stability={payload['posture_stability']}"
        )
        print(f"[vision.api] returning result={payload}")
        print(
            "[vision.analyze.baseline] "
            f"upload_bytes={upload_bytes} analyze_elapsed_ms={analyze_elapsed_ms:.1f} "
            f"vision_valid={payload.get('vision_valid')} "
            f"forward_gaze_ratio={payload.get('forward_gaze_ratio')} "
            f"downward_head_ratio={payload.get('downward_head_ratio')} "
            f"posture_stability={payload.get('posture_stability')} "
            f"provider={provider_kind} board_provider={result.get('provider')!r} "
            f"outcome={outcome}"
        )
        print(
            "[vision.analyze.api] long_session_scalars "
            f"total_video_duration_sec={payload.get('total_video_duration_sec')} "
            f"duration_source={payload.get('duration_source')!r} "
            f"processed_frames={payload.get('processed_frames')} "
            f"skipped_frames={payload.get('skipped_frames')}"
        )
        return payload
    except Exception as e:
        traceback.print_exc()
        msg = str(e)
        msg_l = msg.lower()
        pk = get_ai_provider_status().get("vision_provider", "unknown")
        if "请求超时" in msg or "timeout=" in msg_l or "timed out" in msg_l:
            vision_msg = (
                "视频分析超时：经主后端转发至开发板时含本机到板上的上传与整段推理，耗时往往长于直打开发板。"
                "若同一条视频在板侧可完成，请增大主后端环境变量 ASCEND_VISION_TIMEOUT_SECONDS（如 300～600）后重启主后端，"
                "或改短/压缩视频后再试。"
            )
            outcome = "timeout"
        else:
            vision_msg = "视频分析失败，请稍后重试或更换较短片段"
            outcome = "exception"
        degraded = {
            "forward_gaze_ratio": 0.0,
            "downward_head_ratio": 0.0,
            "posture_stability": 0.0,
            "vision_valid": False,
            "vision_message": vision_msg,
            "vision_debug_source": None,
            "vision_debug_provider": None,
            "vision_debug_request_id": None,
            "processed_frames": 0,
            "skipped_frames": 0,
            "total_video_duration_sec": 0.0,
            "sampled_mode_used": False,
            "sampled_fps": 0.0,
            "vision_metrics_scope": "session_unavailable",
        }
        print(
            "[vision.analyze.baseline] "
            f"upload_bytes={upload_bytes} analyze_elapsed_ms={analyze_elapsed_ms:.1f} "
            f"vision_valid=False provider={pk} outcome={outcome} err={repr(e)[:200]}"
        )
        return degraded
