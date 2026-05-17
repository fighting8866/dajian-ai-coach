from __future__ import annotations

import os
import tempfile
import time
from pathlib import Path

from fastapi import APIRouter, File, Form, UploadFile

from ascend_service.schemas.protocol import AscendResponse
from ascend_service.services.vision_service import analyze_video

router = APIRouter()


def _normalize_result(raw_result: dict, request_id: str) -> dict:
    result = {
        "forward_gaze_ratio": float(raw_result.get("forward_gaze_ratio", 0.0)),
        "downward_head_ratio": float(raw_result.get("downward_head_ratio", 0.0)),
        "posture_stability": float(raw_result.get("posture_stability", 0.0)),
        "vision_valid": bool(raw_result.get("vision_valid", True)),
        "vision_message": str(raw_result.get("vision_message") or ""),
        "vision_debug_source": "ascend_service",
        "vision_debug_provider": "ascend-service",
        "vision_debug_request_id": request_id,
    }
    if result["vision_valid"] is False and not result["vision_message"]:
        result["vision_message"] = "有效检测帧过少，无法生成稳定视觉指标"
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
        if key in raw_result and raw_result[key] is not None:
            result[key] = raw_result[key]
    return result


def _handle_vision_upload(request_id: str, video_file: UploadFile) -> AscendResponse:
    request_id = str(request_id or "").strip() or "mock-request"
    suffix = Path(video_file.filename or "").suffix or ".webm"
    tmp_path: str | None = None
    try:
        with tempfile.NamedTemporaryFile(prefix="ascend_vision_", suffix=suffix, delete=False) as tmp:
            content = video_file.file.read()
            tmp.write(content)
            tmp_path = tmp.name
        print(
            "[ascend_service.api.vision] uploaded file saved "
            f"request_id={request_id} filename={video_file.filename!r} "
            f"tmp_path={tmp_path} bytes={len(content)}"
        )

        t_svc0 = time.perf_counter()
        raw_result = analyze_video(tmp_path)
        svc_wall_ms = (time.perf_counter() - t_svc0) * 1000.0
        result = _normalize_result(raw_result, request_id)
        if result["vision_valid"] is False:
            print(f"[ascend_service.api.vision] degrade return result={result}")
        tf = raw_result.get("total_frames")
        vf = raw_result.get("valid_detection_frames")
        print(
            "[ascend_service.api.vision] SUMMARY "
            f"request_id={request_id} "
            f"total_frames={tf} valid_detection_frames={vf} "
            f"forward_gaze_ratio={result.get('forward_gaze_ratio')} "
            f"downward_head_ratio={result.get('downward_head_ratio')} "
            f"posture_stability={result.get('posture_stability')} "
            f"vision_valid={result.get('vision_valid')} "
            f"vision_message={result.get('vision_message')!r}"
        )
        pf = result.get("processed_frames")
        sf = result.get("skipped_frames")
        tv = result.get("total_video_duration_sec")
        dsrc = result.get("duration_source")
        sfps = result.get("sampled_fps")
        sampled = result.get("sampled_mode_used")
        if sampled is None:
            sampled = result.get("vision_sampled_mode_used")
        print(
            "[ascend_service.api.vision] FINAL "
            f"request_id={request_id} "
            f"forward_gaze_ratio={result.get('forward_gaze_ratio')} "
            f"downward_head_ratio={result.get('downward_head_ratio')} "
            f"posture_stability={result.get('posture_stability')} "
            f"vision_valid={result.get('vision_valid')} "
            f"vision_message={result.get('vision_message')!r} "
            f"total_video_duration_sec={tv} duration_source={dsrc!r} "
            f"processed_frames={pf} skipped_frames={sf} "
            f"sampled_fps={sfps} sampled_mode_used={sampled} "
            f"total_elapsed_ms={raw_result.get('vision_analysis_elapsed_ms')} "
            f"api_handler_elapsed_ms={svc_wall_ms:.1f}"
        )
        return AscendResponse(
            success=True,
            provider="ascend-service",
            request_id=request_id,
            result=result,
            error=None,
        )
    except Exception as e:
        print(f"[ascend_service.api.vision] analyze failed request_id={request_id} err={repr(e)}")
        msg = str(e)
        if "有效检测帧过少" in msg:
            msg = "有效检测帧过少，无法生成稳定视觉指标"
        elif "不存在" in msg or "无法打开" in msg:
            msg = "无法读取视频文件，请确认格式与编码是否受支持"
        else:
            msg = "视频分析失败，请稍后重试或更换较短片段"
        result = _normalize_result(
            {
                "forward_gaze_ratio": 0.0,
                "downward_head_ratio": 0.0,
                "posture_stability": 0.0,
                "vision_valid": False,
                "vision_message": msg,
            },
            request_id,
        )
        print(f"[ascend_service.api.vision] degrade return result={result}")
        print(
            "[ascend_service.api.vision] SUMMARY "
            f"request_id={request_id} "
            f"forward_gaze_ratio={result.get('forward_gaze_ratio')} "
            f"downward_head_ratio={result.get('downward_head_ratio')} "
            f"posture_stability={result.get('posture_stability')} "
            f"vision_valid={result.get('vision_valid')} "
            f"vision_message={result.get('vision_message')!r}"
        )
        print(
            "[ascend_service.api.vision] FINAL "
            f"request_id={request_id} outcome=exception_degraded "
            f"total_video_duration_sec=n/a duration_source=n/a "
            f"processed_frames=0 skipped_frames=n/a "
            f"sampled_fps=n/a sampled_mode_used=False total_elapsed_ms=n/a"
        )
        return AscendResponse(
            success=True,
            provider="ascend-service",
            request_id=request_id,
            result=result,
            error=None,
        )
    finally:
        try:
            if tmp_path and os.path.exists(tmp_path):
                os.remove(tmp_path)
                print(
                    "[ascend_service.api.vision] temp file cleaned "
                    f"request_id={request_id} tmp_path={tmp_path}"
                )
        except Exception as cleanup_err:
            print(
                "[ascend_service.api.vision] temp file cleanup failed "
                f"request_id={request_id} tmp_path={tmp_path} err={repr(cleanup_err)}"
            )


@router.post("/vision/analyze", response_model=AscendResponse)
def vision_analyze(
    request_id: str = Form(default=""),
    video_file: UploadFile = File(...),
) -> AscendResponse:
    return _handle_vision_upload(request_id=request_id, video_file=video_file)


# 兼容当前主项目 mock 联调路径，不影响标准路径
@router.post("/mock/vision/analyze", response_model=AscendResponse)
def vision_analyze_mock_compat(
    request_id: str = Form(default=""),
    video_file: UploadFile = File(...),
) -> AscendResponse:
    return _handle_vision_upload(request_id=request_id, video_file=video_file)
