from __future__ import annotations

"""
视觉分析精调收口 V1（板侧）

- **姿态 / 关键点**：MediaPipe Pose（`mp.solutions.pose`）为主，FaceDetection 辅助；
  无 MediaPipe 时 Haar 降级。
- 阈值与 proxy 逻辑见 `VisionService` 类常量；后续若换用更重的头部姿态估计，建议只替换
  本文件内几何 proxy，保持出口字段 `forward_gaze_ratio` / `downward_head_ratio` /
  `posture_stability` / `vision_valid` 不变。
- **长时答辩 V2 第一阶段**：按目标 FPS 抽帧 + 单段最大分析帧数上限，降低长视频全帧 MediaPipe 耗时；
  指标仍在采样帧上统计（与 `VISION_TARGET_ANALYSIS_FPS` / `VISION_MAX_ANALYSIS_FRAMES` 对齐主后端 config 环境变量名）。
"""

import math
import os
import shutil
import subprocess
import time
from typing import Any

import numpy as np

try:
    import cv2
except Exception:  # pragma: no cover
    cv2 = None

try:
    import mediapipe as mp
except Exception:  # pragma: no cover
    mp = None


def _vision_env_float(name: str, default: float) -> float:
    v = os.getenv(name)
    if v is None or str(v).strip() == "":
        return float(default)
    try:
        return float(str(v).strip())
    except ValueError:
        return float(default)


def _vision_env_int(name: str, default: int) -> int:
    v = os.getenv(name)
    if v is None or str(v).strip() == "":
        return int(default)
    try:
        return int(str(v).strip())
    except ValueError:
        return int(default)


def _sanitize_video_fps(raw_fps: float) -> float:
    """OpenCV 对 WebM/VFR 常返回 0 / NaN / 荒谬值；用于时长必须用有限且合理的 fps。"""
    try:
        x = float(raw_fps)
    except (TypeError, ValueError):
        return 30.0
    if not math.isfinite(x) or x < 0.5 or x > 240.0:
        return 30.0
    return x


def _full_decode_frame_metrics(video_path: str) -> tuple[int, float]:
    """整段逐帧解码：帧数 + 最后一帧 CAP_PROP_POS_MSEC（不少容器 FRAME_COUNT=0 时仍可用）。"""
    if cv2 is None or not video_path:
        return 0, 0.0
    c = cv2.VideoCapture(video_path)
    if not c.isOpened():
        return 0, 0.0
    n = 0
    last_msec = 0.0
    try:
        while True:
            ok, _ = c.read()
            if not ok:
                break
            n += 1
            last_msec = float(c.get(cv2.CAP_PROP_POS_MSEC) or 0.0)
    finally:
        c.release()
    dur_sec = (last_msec / 1000.0) if last_msec > 0.5 else 0.0
    return n, dur_sec


def _count_all_frames_cv2(video_path: str) -> int:
    """容器未报告总帧数时，逐帧读完以得到整段真实帧数。"""
    n, _ = _full_decode_frame_metrics(video_path)
    return n


def _try_ffprobe_duration_sec(video_path: str) -> float | None:
    """部分编码下 OpenCV 全量解码仍得 0 帧时，用 ffprobe 读 format.duration（可选）。"""
    if not video_path or not os.path.exists(video_path):
        return None
    ff = shutil.which("ffprobe")
    if not ff:
        return None
    path = os.path.normpath(video_path)
    try:
        kwargs: dict[str, Any] = dict(
            args=[
                ff,
                "-v",
                "error",
                "-show_entries",
                "format=duration",
                "-of",
                "default=noprint_wrappers=1:nokey=1",
                path,
            ],
            capture_output=True,
            text=True,
            timeout=120,
        )
        if os.name == "nt":
            kwargs["creationflags"] = subprocess.CREATE_NO_WINDOW  # type: ignore[attr-defined]
        cp = subprocess.run(**kwargs)
        if cp.returncode != 0:
            return None
        s = (cp.stdout or "").strip()
        if not s:
            return None
        d = float(s)
        if math.isfinite(d) and d > 0.05:
            return d
    except Exception:
        return None
    return None


class VisionService:
    """Ascend 服务规则版视觉分析（第一版真实化）。"""

    # 精调：略放宽「正视」pitch 上界、略提高低头 proxy/强 pitch 门槛，减少看屏幕误判为严重低头
    FORWARD_YAW_THRESHOLD = 0.34
    FORWARD_PITCH_UP_THRESHOLD = -0.22
    FORWARD_PITCH_DOWN_THRESHOLD = 0.44
    DOWNWARD_HEAD_PROXY_THRESHOLD = 0.17
    DOWNWARD_PROXY2_MIN_THRESHOLD = -0.62
    DOWNWARD_FALLBACK_PITCH_THRESHOLD = 0.20
    DOWNWARD_FALLBACK_PITCH_THRESHOLD_STRONG = 0.21
    POSTURE_JITTER_REF = 0.37
    FACE_FALLBACK_JITTER_REF = 0.21
    RATIO_LAPLACE_ALPHA = 1.0
    MIN_VALID_DETECTION_FRAMES = 8
    DEBUG_SAMPLE_EVERY_N_FRAMES = 10

    def _min_valid_frames_for(self, use_mediapipe: bool) -> int:
        """有 MediaPipe 时默认 8 帧；无则走 Haar，默认放宽到 4 帧，可用环境变量覆盖。"""
        if use_mediapipe:
            return _vision_env_int("VISION_MIN_VALID_FRAMES", self.MIN_VALID_DETECTION_FRAMES)
        return _vision_env_int("VISION_MIN_VALID_FRAMES_HAAR", 4)

    @staticmethod
    def _invalid_result(message: str, *, degraded: bool) -> dict[str, Any]:
        return {
            "forward_gaze_ratio": 0.0,
            "downward_head_ratio": 0.0,
            "posture_stability": 0.0,
            "vision_valid": False,
            "vision_message": message,
            "degraded_path": degraded,
        }

    def analyze_video(self, video_path: str) -> dict[str, Any]:
        if not video_path:
            raise RuntimeError("payload.video_path 为空")
        if not os.path.exists(video_path):
            raise RuntimeError(f"视频文件不存在: {video_path}")
        if cv2 is None:
            raise RuntimeError("当前环境缺少 opencv-python，无法进行视觉分析")

        cap = cv2.VideoCapture(video_path)
        if not cap.isOpened():
            raise RuntimeError("无法打开视频文件，请确认编码格式可被后端解码")

        total_frames = 0
        valid_detection_frames = 0
        forward_frames = 0
        downward_frames = 0
        pose_nose_rel_samples: list[tuple[float, float]] = []
        pose_shoulder_center_rel_samples: list[tuple[float, float]] = []
        pose_shoulder_tilt_rel_samples: list[float] = []
        face_center_rel_samples: list[tuple[float, float]] = []
        sampled_debug_frames = 0
        pose_only_downward_frames = 0
        proxy_path_frames = 0
        fallback_pitch_path_frames = 0
        hybrid_pitch_rescue_frames = 0
        suspicious_downward_miss_frames = 0
        proxy_downward_frames = 0
        strong_pitch_downward_frames = 0

        print(
            "[ascend_service.vision] thresholds: "
            f"FORWARD_YAW_THRESHOLD={self.FORWARD_YAW_THRESHOLD}, "
            f"FORWARD_PITCH_UP_THRESHOLD={self.FORWARD_PITCH_UP_THRESHOLD}, "
            f"FORWARD_PITCH_DOWN_THRESHOLD={self.FORWARD_PITCH_DOWN_THRESHOLD}, "
            f"DOWNWARD_HEAD_PROXY_THRESHOLD={self.DOWNWARD_HEAD_PROXY_THRESHOLD}, "
            f"DOWNWARD_PROXY2_MIN_THRESHOLD={self.DOWNWARD_PROXY2_MIN_THRESHOLD}, "
            f"DOWNWARD_FALLBACK_PITCH_THRESHOLD={self.DOWNWARD_FALLBACK_PITCH_THRESHOLD}, "
            f"DOWNWARD_FALLBACK_PITCH_THRESHOLD_STRONG={self.DOWNWARD_FALLBACK_PITCH_THRESHOLD_STRONG}"
        )
        print(
            "[ascend_service.vision] pitch definition: "
            "pitch_ratio = center_y - 0.5; image_y_positive_is_down=True; "
            "downward_main_judgement = head_down_proxy based on nose/eyes/shoulders geometry"
        )

        use_mediapipe = mp is not None
        min_valid_needed = self._min_valid_frames_for(use_mediapipe)
        if not use_mediapipe:
            print(
                "[ascend_service.vision] mediapipe_unavailable: using Haar face cascade; "
                f"min_valid_frames={min_valid_needed} (set VISION_MIN_VALID_FRAMES_HAAR to override)"
            )
        face_detection = None
        pose = None
        if use_mediapipe:
            face_detection = mp.solutions.face_detection.FaceDetection(
                model_selection=0, min_detection_confidence=0.5
            )
            pose = mp.solutions.pose.Pose(
                static_image_mode=False,
                model_complexity=1,
                min_detection_confidence=0.5,
                min_tracking_confidence=0.5,
            )

        face_cascade = cv2.CascadeClassifier(
            cv2.data.haarcascades + "haarcascade_frontalface_default.xml"
        )

        _raw_fps = float(cap.get(cv2.CAP_PROP_FPS) or 0.0)
        video_fps = _sanitize_video_fps(_raw_fps)
        original_total_frames_prop = int(cap.get(cv2.CAP_PROP_FRAME_COUNT) or 0)
        if original_total_frames_prop < 0:
            original_total_frames_prop = 0
        target_fps = max(0.25, _vision_env_float("VISION_TARGET_ANALYSIS_FPS", 1.0))
        max_analysis = _vision_env_int("VISION_MAX_ANALYSIS_FRAMES", 240)
        step = max(1, int(round(video_fps / target_fps)))
        sampled_fps_effective = video_fps / float(step)
        video_read_frames = 0
        skipped_video_frames = 0
        max_pos_msec_during_read = 0.0
        reached_eof = False
        t_vision0 = time.perf_counter()
        sampled_mode_used = True

        try:
            while True:
                ok, frame = cap.read()
                if not ok:
                    reached_eof = True
                    break
                video_read_frames += 1
                try:
                    _pm = float(cap.get(cv2.CAP_PROP_POS_MSEC) or 0.0)
                    if _pm > max_pos_msec_during_read:
                        max_pos_msec_during_read = _pm
                except Exception:
                    pass
                if (video_read_frames - 1) % step != 0:
                    skipped_video_frames += 1
                    continue
                if max_analysis > 0 and total_frames >= max_analysis:
                    skipped_video_frames += 1
                    break

                total_frames += 1
                h, w = frame.shape[:2]
                if h <= 0 or w <= 0:
                    continue

                rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
                frame_valid = False

                if use_mediapipe and face_detection is not None and pose is not None:
                    face_result = face_detection.process(rgb)
                    pose_result = pose.process(rgb)
                    pose_landmarks = pose_result.pose_landmarks.landmark if pose_result.pose_landmarks else None
                    if face_result.detections:
                        detection = face_result.detections[0]
                        bbox = detection.location_data.relative_bounding_box
                        cx = float(bbox.xmin + bbox.width / 2.0)
                        cy = float(bbox.ymin + bbox.height / 2.0)
                        frame_valid = True

                        if pose_landmarks:
                            lms = pose_landmarks
                            nose = lms[mp.solutions.pose.PoseLandmark.NOSE]
                            l_eye = lms[mp.solutions.pose.PoseLandmark.LEFT_EYE]
                            r_eye = lms[mp.solutions.pose.PoseLandmark.RIGHT_EYE]
                            l_shoulder = lms[mp.solutions.pose.PoseLandmark.LEFT_SHOULDER]
                            r_shoulder = lms[mp.solutions.pose.PoseLandmark.RIGHT_SHOULDER]
                            shoulder_mid_x = (l_shoulder.x + r_shoulder.x) / 2.0
                            shoulder_mid_y = (l_shoulder.y + r_shoulder.y) / 2.0
                            shoulder_width = abs(float(l_shoulder.x - r_shoulder.x))
                            norm_scale = max(shoulder_width, 0.08)
                            eye_center_y = float((l_eye.y + r_eye.y) / 2.0)
                            head_down_proxy_1 = float((nose.y - eye_center_y) / norm_scale)
                            head_down_proxy_2 = float((nose.y - shoulder_mid_y) / norm_scale)
                            yaw_ratio = abs(cx - 0.5)
                            pitch_ratio = cy - 0.5
                            use_proxy_path = True
                            downward_path = "proxy"
                            proxy_path_frames += 1
                            proxy_downward = (
                                head_down_proxy_1 >= self.DOWNWARD_HEAD_PROXY_THRESHOLD
                                and head_down_proxy_2 >= self.DOWNWARD_PROXY2_MIN_THRESHOLD
                            )
                            strong_pitch_downward = (
                                pitch_ratio >= self.DOWNWARD_FALLBACK_PITCH_THRESHOLD_STRONG
                            )
                            # 先判 downward，再判 forward，保证互斥；proxy 可用时启用 hybrid 兜底
                            is_downward = proxy_downward or strong_pitch_downward
                            if proxy_downward:
                                proxy_downward_frames += 1
                            if strong_pitch_downward:
                                strong_pitch_downward_frames += 1
                            if strong_pitch_downward and not proxy_downward:
                                downward_path = "proxy+strong_pitch_hybrid"
                                hybrid_pitch_rescue_frames += 1
                                print(
                                    "[ascend_service.vision.warning] suspicious downward miss "
                                    f"frame={total_frames} pitch={pitch_ratio:.4f} "
                                    f"head_down_proxy_1={head_down_proxy_1:.4f} "
                                    f"head_down_proxy_2={head_down_proxy_2:.4f} "
                                    f"use_proxy_path={use_proxy_path} rescued_by_hybrid=True"
                                )
                            elif (not is_downward) and pitch_ratio >= self.DOWNWARD_FALLBACK_PITCH_THRESHOLD_STRONG:
                                suspicious_downward_miss_frames += 1
                                print(
                                    "[ascend_service.vision.warning] suspicious downward miss "
                                    f"frame={total_frames} pitch={pitch_ratio:.4f} "
                                    f"head_down_proxy_1={head_down_proxy_1:.4f} "
                                    f"head_down_proxy_2={head_down_proxy_2:.4f} "
                                    f"use_proxy_path={use_proxy_path}"
                                )
                            is_forward = (
                                (not is_downward)
                                and yaw_ratio <= self.FORWARD_YAW_THRESHOLD
                                and pitch_ratio < self.DOWNWARD_FALLBACK_PITCH_THRESHOLD_STRONG
                                and self.FORWARD_PITCH_UP_THRESHOLD <= pitch_ratio <= self.FORWARD_PITCH_DOWN_THRESHOLD
                            )
                            if is_downward:
                                downward_frames += 1
                            if is_forward:
                                forward_frames += 1
                            if total_frames % self.DEBUG_SAMPLE_EVERY_N_FRAMES == 0:
                                sampled_debug_frames += 1
                                print(
                                    "[ascend_service.vision.frame] "
                                    f"frame={total_frames} source=pose+face "
                                    f"yaw={yaw_ratio:.4f} pitch={pitch_ratio:.4f} "
                                    f"head_down_proxy_1={head_down_proxy_1:.4f} "
                                    f"head_down_proxy_2={head_down_proxy_2:.4f} "
                                    f"proxy_downward={proxy_downward} "
                                    f"strong_pitch_downward={strong_pitch_downward} "
                                    f"use_proxy_path={use_proxy_path} "
                                    f"is_downward={is_downward} is_forward={is_forward}"
                                )
                                print(f"[ascend_service.vision] downward_path={downward_path}")
                            nose_rel_x = float((nose.x - shoulder_mid_x) / norm_scale)
                            nose_rel_y = float((nose.y - shoulder_mid_y) / norm_scale)
                            shoulder_center_rel_x = float((shoulder_mid_x - 0.5) / norm_scale)
                            shoulder_center_rel_y = float((shoulder_mid_y - 0.5) / norm_scale)
                            shoulder_tilt_rel = float((l_shoulder.y - r_shoulder.y) / norm_scale)
                            pose_nose_rel_samples.append((nose_rel_x, nose_rel_y))
                            pose_shoulder_center_rel_samples.append(
                                (shoulder_center_rel_x, shoulder_center_rel_y)
                            )
                            pose_shoulder_tilt_rel_samples.append(shoulder_tilt_rel)
                        else:
                            yaw_ratio = abs(cx - 0.5)
                            pitch_ratio = cy - 0.5
                            head_down_proxy_1 = None
                            head_down_proxy_2 = None
                            use_proxy_path = False
                            downward_path = "fallback_pitch"
                            fallback_pitch_path_frames += 1
                            # 无 pose 关键点时仅走降级策略（非主判定）
                            proxy_downward = False
                            strong_pitch_downward = (
                                pitch_ratio >= self.DOWNWARD_FALLBACK_PITCH_THRESHOLD_STRONG
                            )
                            is_downward = pitch_ratio >= self.DOWNWARD_FALLBACK_PITCH_THRESHOLD
                            if strong_pitch_downward:
                                strong_pitch_downward_frames += 1
                            is_forward = (
                                (not is_downward)
                                and yaw_ratio <= self.FORWARD_YAW_THRESHOLD
                                and pitch_ratio < self.DOWNWARD_FALLBACK_PITCH_THRESHOLD_STRONG
                                and self.FORWARD_PITCH_UP_THRESHOLD <= pitch_ratio <= self.FORWARD_PITCH_DOWN_THRESHOLD
                            )
                            if is_downward:
                                downward_frames += 1
                            if is_forward:
                                forward_frames += 1
                            if total_frames % self.DEBUG_SAMPLE_EVERY_N_FRAMES == 0:
                                sampled_debug_frames += 1
                                print(
                                    "[ascend_service.vision.frame] "
                                    f"frame={total_frames} source=face_only "
                                    f"yaw={yaw_ratio:.4f} pitch={pitch_ratio:.4f} "
                                    f"head_down_proxy_1={head_down_proxy_1} "
                                    f"head_down_proxy_2={head_down_proxy_2} "
                                    f"proxy_downward={proxy_downward} "
                                    f"strong_pitch_downward={strong_pitch_downward} "
                                    f"use_proxy_path={use_proxy_path} "
                                    f"is_downward={is_downward} is_forward={is_forward}"
                                )
                                print(f"[ascend_service.vision] downward_path={downward_path}")
                            face_center_rel_samples.append((float(cx - 0.5), float(cy - 0.5)))
                    elif pose_landmarks:
                        # 弱场景降级：face 不稳但 pose 可用时，仍参与 downward 判定，避免低头场景被整体丢帧
                        nose = pose_landmarks[mp.solutions.pose.PoseLandmark.NOSE]
                        l_eye = pose_landmarks[mp.solutions.pose.PoseLandmark.LEFT_EYE]
                        r_eye = pose_landmarks[mp.solutions.pose.PoseLandmark.RIGHT_EYE]
                        l_shoulder = pose_landmarks[mp.solutions.pose.PoseLandmark.LEFT_SHOULDER]
                        r_shoulder = pose_landmarks[mp.solutions.pose.PoseLandmark.RIGHT_SHOULDER]
                        shoulder_vis = min(float(l_shoulder.visibility), float(r_shoulder.visibility))
                        eye_vis = min(float(l_eye.visibility), float(r_eye.visibility))
                        if shoulder_vis >= 0.25 and float(nose.visibility) >= 0.25 and eye_vis >= 0.25:
                            frame_valid = True
                            shoulder_mid_y = float((l_shoulder.y + r_shoulder.y) / 2.0)
                            shoulder_width = max(abs(float(l_shoulder.x - r_shoulder.x)), 0.08)
                            eye_center_y = float((l_eye.y + r_eye.y) / 2.0)
                            head_down_proxy_1 = float((nose.y - eye_center_y) / shoulder_width)
                            head_down_proxy_2 = float((nose.y - shoulder_mid_y) / shoulder_width)
                            pitch_ratio = float(nose.y - 0.5)
                            use_proxy_path = True
                            downward_path = "proxy"
                            proxy_path_frames += 1
                            proxy_downward = (
                                head_down_proxy_1 >= self.DOWNWARD_HEAD_PROXY_THRESHOLD
                                and head_down_proxy_2 >= self.DOWNWARD_PROXY2_MIN_THRESHOLD
                            )
                            strong_pitch_downward = (
                                pitch_ratio >= self.DOWNWARD_FALLBACK_PITCH_THRESHOLD_STRONG
                            )
                            is_downward = proxy_downward or strong_pitch_downward
                            if proxy_downward:
                                proxy_downward_frames += 1
                            if strong_pitch_downward:
                                strong_pitch_downward_frames += 1
                            if strong_pitch_downward and not proxy_downward:
                                downward_path = "proxy+strong_pitch_hybrid"
                                hybrid_pitch_rescue_frames += 1
                                print(
                                    "[ascend_service.vision.warning] suspicious downward miss "
                                    f"frame={total_frames} pitch={pitch_ratio:.4f} "
                                    f"head_down_proxy_1={head_down_proxy_1:.4f} "
                                    f"head_down_proxy_2={head_down_proxy_2:.4f} "
                                    f"use_proxy_path={use_proxy_path} rescued_by_hybrid=True"
                                )
                            elif (not is_downward) and pitch_ratio >= self.DOWNWARD_FALLBACK_PITCH_THRESHOLD_STRONG:
                                suspicious_downward_miss_frames += 1
                                print(
                                    "[ascend_service.vision.warning] suspicious downward miss "
                                    f"frame={total_frames} pitch={pitch_ratio:.4f} "
                                    f"head_down_proxy_1={head_down_proxy_1:.4f} "
                                    f"head_down_proxy_2={head_down_proxy_2:.4f} "
                                    f"use_proxy_path={use_proxy_path}"
                                )
                            if is_downward:
                                downward_frames += 1
                                pose_only_downward_frames += 1
                            is_forward = False
                            if total_frames % self.DEBUG_SAMPLE_EVERY_N_FRAMES == 0:
                                sampled_debug_frames += 1
                                print(
                                    "[ascend_service.vision.frame] "
                                    f"frame={total_frames} source=pose_only "
                                    f"yaw=nan pitch={pitch_ratio:.4f} "
                                    f"head_down_proxy_1={head_down_proxy_1:.4f} "
                                    f"head_down_proxy_2={head_down_proxy_2:.4f} "
                                    f"proxy_downward={proxy_downward} "
                                    f"strong_pitch_downward={strong_pitch_downward} "
                                    f"use_proxy_path={use_proxy_path} "
                                    f"is_downward={is_downward} is_forward={is_forward}"
                                )
                                print(f"[ascend_service.vision] downward_path={downward_path}")
                else:
                    gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
                    faces = face_cascade.detectMultiScale(
                        gray, scaleFactor=1.1, minNeighbors=5, minSize=(40, 40)
                    )
                    if len(faces) > 0:
                        x, y, fw, fh = max(faces, key=lambda item: item[2] * item[3])
                        cx = (x + fw / 2.0) / max(float(w), 1.0)
                        cy = (y + fh / 2.0) / max(float(h), 1.0)
                        frame_valid = True

                        yaw_ratio = abs(cx - 0.5)
                        pitch_ratio = cy - 0.5
                        head_down_proxy_1 = None
                        head_down_proxy_2 = None
                        use_proxy_path = False
                        downward_path = "fallback_pitch"
                        fallback_pitch_path_frames += 1
                        proxy_downward = False
                        strong_pitch_downward = (
                            pitch_ratio >= self.DOWNWARD_FALLBACK_PITCH_THRESHOLD_STRONG
                        )
                        is_downward = pitch_ratio >= self.DOWNWARD_FALLBACK_PITCH_THRESHOLD
                        if strong_pitch_downward:
                            strong_pitch_downward_frames += 1
                        is_forward = (
                            (not is_downward)
                            and yaw_ratio <= self.FORWARD_YAW_THRESHOLD
                            and pitch_ratio < self.DOWNWARD_FALLBACK_PITCH_THRESHOLD_STRONG
                            and self.FORWARD_PITCH_UP_THRESHOLD <= pitch_ratio <= self.FORWARD_PITCH_DOWN_THRESHOLD
                        )
                        if is_downward:
                            downward_frames += 1
                        if is_forward:
                            forward_frames += 1
                        if total_frames % self.DEBUG_SAMPLE_EVERY_N_FRAMES == 0:
                            sampled_debug_frames += 1
                            print(
                                "[ascend_service.vision.frame] "
                                f"frame={total_frames} source=haar yaw={yaw_ratio:.4f} pitch={pitch_ratio:.4f} "
                                f"head_down_proxy_1={head_down_proxy_1} "
                                f"head_down_proxy_2={head_down_proxy_2} "
                                f"proxy_downward={proxy_downward} "
                                f"strong_pitch_downward={strong_pitch_downward} "
                                f"use_proxy_path={use_proxy_path} "
                                f"is_downward={is_downward} is_forward={is_forward}"
                            )
                            print(f"[ascend_service.vision] downward_path={downward_path}")
                        face_center_rel_samples.append((float(cx - 0.5), float(cy - 0.5)))

                if frame_valid:
                    valid_detection_frames += 1
        finally:
            cap.release()
            if face_detection is not None:
                face_detection.close()
            if pose is not None:
                pose.close()

        vision_elapsed_ms = (time.perf_counter() - t_vision0) * 1000.0
        # 整段真实时长主口径：total_video_duration_sec = original_total_frames / original_fps（fps 异常时用 _sanitize_video_fps 兜底，避免除零与非有限）。
        # 若容器未报帧数：EOF 解码帧、全量扫帧+POS_MSEC、ffprobe、再一致性 repair。禁止仅用 processed_frames/sampled_fps 作为主时长。
        fps_dur = max(float(video_fps), 1e-6)
        original_total_frames_effective = 0
        duration_source = "unset"
        computed_total_video_duration_sec = 0.0
        if original_total_frames_prop > 0:
            computed_total_video_duration_sec = float(original_total_frames_prop) / fps_dur
            original_total_frames_effective = original_total_frames_prop
            duration_source = "container_frame_count"
        elif reached_eof and video_read_frames > 0:
            computed_total_video_duration_sec = float(video_read_frames) / fps_dur
            original_total_frames_effective = video_read_frames
            duration_source = "decoded_to_eof"
        else:
            fc_full, dur_pos_msec = _full_decode_frame_metrics(video_path)
            if fc_full > 0:
                dur_from_frames = float(fc_full) / fps_dur
                if dur_pos_msec > 0.01:
                    computed_total_video_duration_sec = max(dur_from_frames, dur_pos_msec)
                    duration_source = "full_frame_scan_max_frames_or_pos_msec"
                else:
                    computed_total_video_duration_sec = dur_from_frames
                    duration_source = "full_frame_scan"
                original_total_frames_effective = fc_full
            else:
                computed_total_video_duration_sec = float(video_read_frames) / fps_dur
                original_total_frames_effective = video_read_frames
                duration_source = "partial_read_fallback"
                print(
                    "[ascend_service.vision.duration_v1] WARN "
                    "全量解码帧数为 0，退回已读前缀估算（总长可能偏短）"
                )

        if (not math.isfinite(computed_total_video_duration_sec)) or computed_total_video_duration_sec <= 0:
            fp_dur = _try_ffprobe_duration_sec(video_path)
            if fp_dur is not None:
                computed_total_video_duration_sec = fp_dur
                duration_source = "ffprobe_format_duration"
                if original_total_frames_effective <= 0:
                    original_total_frames_effective = int(round(fp_dur * fps_dur))
            elif video_read_frames > 0:
                computed_total_video_duration_sec = float(video_read_frames) / fps_dur
                duration_source = "decode_prefix_fallback"
                print(
                    "[ascend_service.vision.duration_v1] WARN "
                    "ffprobe 不可用或失败，使用已解码帧数估算时长（可能短于整段）"
                )

        dur_from_main_pos_msec = float(max_pos_msec_during_read) / 1000.0
        if dur_from_main_pos_msec > 0.01:
            if (not math.isfinite(computed_total_video_duration_sec)) or computed_total_video_duration_sec <= 0:
                computed_total_video_duration_sec = dur_from_main_pos_msec
                duration_source = "main_read_max_pos_msec"
            elif reached_eof and dur_from_main_pos_msec > float(computed_total_video_duration_sec) + 0.02:
                computed_total_video_duration_sec = max(
                    float(computed_total_video_duration_sec), dur_from_main_pos_msec
                )
                duration_source = f"{duration_source}|main_read_pos_msec_align"

        total_video_duration_sec = float(computed_total_video_duration_sec)

        # 一致性收口：只要已做采样读帧（processed>0 或 skipped>0），禁止 total_video_duration_sec 仍为 0 / 非有限
        def _duration_usable(x: float) -> bool:
            return math.isfinite(x) and x > 0.0

        has_sampling_activity = int(total_frames) > 0 or int(skipped_video_frames) > 0
        sampling_inconsistent = has_sampling_activity and not _duration_usable(total_video_duration_sec)
        if sampling_inconsistent or (
            int(video_read_frames) > 0 and not _duration_usable(total_video_duration_sec)
        ):
            repair_cand: list[float] = []
            if _duration_usable(float(computed_total_video_duration_sec)):
                repair_cand.append(float(computed_total_video_duration_sec))
            fp_r = _try_ffprobe_duration_sec(video_path)
            if fp_r is not None and math.isfinite(fp_r) and fp_r > 0:
                repair_cand.append(float(fp_r))
            fc_r, dm_r = _full_decode_frame_metrics(video_path)
            if fc_r > 0:
                repair_cand.append(float(fc_r) / fps_dur)
            if dm_r > 0.01:
                repair_cand.append(float(dm_r))
            if original_total_frames_prop > 0:
                repair_cand.append(float(original_total_frames_prop) / fps_dur)
            if video_read_frames > 0:
                repair_cand.append(float(video_read_frames) / fps_dur)
            if max_pos_msec_during_read > 10.0:
                repair_cand.append(float(max_pos_msec_during_read) / 1000.0)
            if repair_cand:
                total_video_duration_sec = float(max(repair_cand))
                duration_source = f"{duration_source}|repair_max_nonzero"
                print(
                    "[ascend_service.vision.duration_v1] REPAIR "
                    f"applied sampling_inconsistent={sampling_inconsistent} "
                    f"new_total_video_duration_sec={total_video_duration_sec:.3f} "
                    f"candidates={[round(c,3) for c in repair_cand]}"
                )

        # 最后兜底：仍有读帧活动但时长不可用 → 用 (processed+skipped)/fps 与 video_read_frames/fps 取较大者（非伪 0）
        if has_sampling_activity and not _duration_usable(total_video_duration_sec):
            fb_pf = float(int(total_frames) + int(skipped_video_frames)) / fps_dur
            fb_vr = float(video_read_frames) / fps_dur if video_read_frames > 0 else 0.0
            total_video_duration_sec = round(max(fb_pf, fb_vr, 1.0 / fps_dur), 3)
            duration_source = f"{duration_source}|forced_sampling_wallclock"
            print(
                "[ascend_service.vision.duration_v1] FORCED "
                f"total_video_duration_sec={total_video_duration_sec:.3f} "
                f"from_pf_sk={fb_pf:.3f} from_video_read={fb_vr:.3f}"
            )

        if not math.isfinite(total_video_duration_sec) or total_video_duration_sec < 0:
            total_video_duration_sec = 0.0
        else:
            total_video_duration_sec = round(min(float(total_video_duration_sec), 86400.0), 3)

        print(
            "[ascend_service.vision.duration_v1] "
            f"original_total_frames={original_total_frames_prop} "
            f"original_fps={video_fps:.4f} "
            f"computed_total_video_duration_sec={computed_total_video_duration_sec:.3f} "
            f"duration_basis_frames={original_total_frames_effective} "
            f"final_total_video_duration_sec={total_video_duration_sec:.3f} "
            f"duration_source={duration_source!r} "
            f"main_read_max_pos_msec={max_pos_msec_during_read:.1f} "
            f"processed_frames={total_frames} "
            f"skipped_frames={skipped_video_frames} "
            f"sampled_fps={sampled_fps_effective:.4f} "
            f"video_read_frames={video_read_frames} reached_eof={reached_eof} "
            f"container_prop_frames={original_total_frames_prop}"
        )
        print(
            "[ascend_service.vision.sample_v1] "
            f"original_fps={video_fps:.4f} sampled_fps={sampled_fps_effective:.4f} step={step} "
            f"processed_frames={total_frames} skipped_frames={skipped_video_frames} "
            f"video_read_frames={video_read_frames} max_analysis_frames={max_analysis} "
            f"total_video_duration_sec={total_video_duration_sec:.3f} "
            f"total_elapsed_ms={vision_elapsed_ms:.1f} sampled_mode_used={sampled_mode_used}"
        )

        denom = max(valid_detection_frames, 1)
        a = float(self.RATIO_LAPLACE_ALPHA)
        forward_gaze_ratio = round(float(forward_frames + a) / float(denom + 2.0 * a), 4)
        downward_head_ratio = round(float(downward_frames + a) / float(denom + 2.0 * a), 4)

        posture_stability = 0.0
        posture_mode = "insufficient_samples"
        posture_debug: dict[str, float | None] = {
            "nose_motion": None,
            "shoulder_center_motion": None,
            "shoulder_tilt_motion": None,
            "composite_jitter": None,
            "face_fallback_motion": None,
        }

        if len(pose_nose_rel_samples) >= 3 and len(pose_shoulder_center_rel_samples) >= 3:
            nose_arr = np.array(pose_nose_rel_samples, dtype=np.float32)
            shoulder_center_arr = np.array(pose_shoulder_center_rel_samples, dtype=np.float32)
            shoulder_tilt_arr = np.array(pose_shoulder_tilt_rel_samples, dtype=np.float32)
            nose_motion = float(np.sqrt(np.std(nose_arr[:, 0]) ** 2 + np.std(nose_arr[:, 1]) ** 2))
            shoulder_center_motion = float(
                np.sqrt(np.std(shoulder_center_arr[:, 0]) ** 2 + np.std(shoulder_center_arr[:, 1]) ** 2)
            )
            shoulder_tilt_motion = float(np.std(shoulder_tilt_arr)) if shoulder_tilt_arr.size > 0 else 0.0
            composite_jitter = (
                0.55 * nose_motion
                + 0.30 * shoulder_center_motion
                + 0.15 * abs(shoulder_tilt_motion)
            )
            jitter_for_score = float(np.sqrt(max(composite_jitter, 1e-9)))
            posture_stability = float(np.exp(-jitter_for_score / self.POSTURE_JITTER_REF))
            posture_mode = "pose_shoulder_normalized"
            posture_debug = {
                "nose_motion": round(nose_motion, 6),
                "shoulder_center_motion": round(shoulder_center_motion, 6),
                "shoulder_tilt_motion": round(abs(shoulder_tilt_motion), 6),
                "composite_jitter": round(float(composite_jitter), 6),
                "jitter_sqrt_for_score": round(jitter_for_score, 6),
                "face_fallback_motion": None,
            }
        elif len(face_center_rel_samples) >= 3:
            face_arr = np.array(face_center_rel_samples, dtype=np.float32)
            face_fallback_motion = float(np.sqrt(np.std(face_arr[:, 0]) ** 2 + np.std(face_arr[:, 1]) ** 2))
            face_j = float(np.sqrt(max(face_fallback_motion, 1e-9)))
            posture_stability = float(np.exp(-face_j / self.FACE_FALLBACK_JITTER_REF))
            posture_mode = "face_center_fallback"
            posture_debug["face_fallback_motion"] = round(face_fallback_motion, 6)

        posture_stability = round(float(max(0.0, min(1.0, posture_stability))), 4)

        print(
            "[ascend_service.vision] "
            f"total_frames={total_frames} valid_detection_frames={valid_detection_frames} "
            f"forward_frames={forward_frames} downward_frames={downward_frames} "
            f"forward_gaze_ratio={forward_gaze_ratio} downward_head_ratio={downward_head_ratio} "
            f"posture_stability={posture_stability} laplace_alpha={self.RATIO_LAPLACE_ALPHA} "
            f"sampled_debug_frames={sampled_debug_frames} "
            f"downward_summary={downward_frames}/{max(valid_detection_frames, 1)} "
            f"pose_only_downward_frames={pose_only_downward_frames}"
        )
        print(
            "[ascend_service.vision] downward_path_used_summary="
            f"proxy_frames={proxy_path_frames}, "
            f"fallback_pitch_frames={fallback_pitch_path_frames}, "
            f"hybrid_pitch_rescue_frames={hybrid_pitch_rescue_frames}, "
            f"suspicious_downward_miss_frames={suspicious_downward_miss_frames}, "
            f"proxy_downward_frames={proxy_downward_frames}, "
            f"strong_pitch_downward_frames={strong_pitch_downward_frames}, "
            f"final_downward_frames={downward_frames}"
        )
        print(
            "[ascend_service.vision.posture] "
            f"mode={posture_mode} debug={posture_debug}"
        )

        if valid_detection_frames < min_valid_needed:
            if use_mediapipe:
                msg = "有效检测帧过少，无法生成稳定视觉指标"
            else:
                msg = (
                    f"有效人脸检测帧不足（当前 {valid_detection_frames}，需≥{min_valid_needed}，"
                    "未安装 MediaPipe 时仅使用 OpenCV Haar 人脸检测）。"
                    "请保证正脸、光线充足、视频足够长，或在板端安装 MediaPipe 后重试；"
                    "也可将环境变量 VISION_MIN_VALID_FRAMES_HAAR 调到 3 做赛时权宜（指标噪声可能略大）。"
                )
            result = self._invalid_result(msg, degraded=True)
            result.update(
                {
                    "total_frames": int(video_read_frames),
                    "valid_detection_frames": int(valid_detection_frames),
                    "processed_frames": int(total_frames),
                    "skipped_frames": int(skipped_video_frames),
                    "total_video_duration_sec": round(float(total_video_duration_sec), 3),
                    "duration_source": str(duration_source),
                    "sampled_mode_used": bool(sampled_mode_used),
                    "sampled_fps": round(float(sampled_fps_effective), 4),
                    "vision_original_fps": round(float(video_fps), 4),
                    "vision_sampled_fps": round(float(sampled_fps_effective), 4),
                    "vision_skipped_frames": int(skipped_video_frames),
                    "vision_analysis_elapsed_ms": round(float(vision_elapsed_ms), 1),
                    "vision_sampled_mode_used": sampled_mode_used,
                    "vision_metrics_scope": "session_sampled_full_video",
                }
            )
            print(
                "[ascend_service.vision] insufficient valid frames "
                f"sampled_frames={total_frames} valid_detection_frames={valid_detection_frames} "
                f"video_read_frames={video_read_frames}"
            )
            print(f"[ascend_service.vision] insufficient valid frames result={result}")
            print(
                "[ascend_service.vision.tune_v1] "
                f"total_frames={total_frames} valid_detection_frames={valid_detection_frames} "
                f"forward_frames={forward_frames} downward_frames={downward_frames} "
                f"forward_gaze_ratio={forward_gaze_ratio} downward_head_ratio={downward_head_ratio} "
                f"posture_stability={posture_stability} posture_mode={posture_mode} "
                f"vision_valid=False vision_message={msg!r}"
            )
            return result

        result = {
            "forward_gaze_ratio": forward_gaze_ratio,
            "downward_head_ratio": downward_head_ratio,
            "posture_stability": posture_stability,
            "vision_valid": True,
            "vision_message": "",
            "degraded_path": False,
            "total_frames": int(video_read_frames),
            "valid_detection_frames": int(valid_detection_frames),
            "processed_frames": int(total_frames),
            "skipped_frames": int(skipped_video_frames),
            "total_video_duration_sec": round(float(total_video_duration_sec), 3),
            "duration_source": str(duration_source),
            "sampled_mode_used": bool(sampled_mode_used),
            "sampled_fps": round(float(sampled_fps_effective), 4),
            "vision_original_fps": round(float(video_fps), 4),
            "vision_sampled_fps": round(float(sampled_fps_effective), 4),
            "vision_skipped_frames": int(skipped_video_frames),
            "vision_analysis_elapsed_ms": round(float(vision_elapsed_ms), 1),
            "vision_sampled_mode_used": sampled_mode_used,
            "vision_metrics_scope": "session_sampled_full_video",
        }
        print(
            "[ascend_service.vision] degrade_path=False "
            "vision_valid=True vision_message=''"
        )
        print(
            "[ascend_service.vision.tune_v1] "
            f"total_frames={total_frames} valid_detection_frames={valid_detection_frames} "
            f"forward_frames={forward_frames} downward_frames={downward_frames} "
            f"forward_gaze_ratio={forward_gaze_ratio} downward_head_ratio={downward_head_ratio} "
            f"posture_stability={posture_stability} posture_mode={posture_mode} "
            f"vision_valid=True vision_message=''"
        )
        return result


def analyze_video(video_path: str) -> dict[str, Any]:
    return VisionService().analyze_video(video_path)


def analyze_vision(payload: dict) -> dict:
    video_path = str((payload or {}).get("video_path") or "").strip()
    return analyze_video(video_path)
