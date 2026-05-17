from __future__ import annotations

import os
from typing import Any

import numpy as np

try:
    import cv2
except Exception:  # pragma: no cover - 运行时环境缺依赖时提示
    cv2 = None

try:
    import mediapipe as mp
except Exception:  # pragma: no cover - 运行时环境缺依赖时提示
    mp = None


class VisionService:
    """离线视觉分析（第一版规则法）：正视比例、低头率、姿态稳定度。"""

    # 经验阈值（第二版校准）
    # - forward: 允许一定 yaw 偏差和轻微看屏幕（小幅向下）
    # - downward: 仅在明显向下时才计入低头
    FORWARD_YAW_THRESHOLD = 0.34
    FORWARD_PITCH_UP_THRESHOLD = -0.22
    FORWARD_PITCH_DOWN_THRESHOLD = 0.42
    DOWNWARD_PITCH_THRESHOLD = 0.56

    # 姿态稳定度映射参数（第二版）
    # 使用 shoulder-width 归一化后，综合鼻子相对肩中心与肩部本身抖动
    POSTURE_JITTER_REF = 0.30
    FACE_FALLBACK_JITTER_REF = 0.18
    MIN_VALID_DETECTION_FRAMES = 8
    DEBUG_SAMPLE_EVERY_N_FRAMES = 10

    def analyze_video(self, video_path: str) -> dict[str, Any]:
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
        # 视觉稳定度中间量采样
        pose_nose_rel_samples: list[tuple[float, float]] = []
        pose_shoulder_center_rel_samples: list[tuple[float, float]] = []
        pose_shoulder_tilt_rel_samples: list[float] = []
        face_center_rel_samples: list[tuple[float, float]] = []
        sampled_debug_frames = 0

        print(
            "[vision.service] thresholds: "
            f"FORWARD_YAW_THRESHOLD={self.FORWARD_YAW_THRESHOLD}, "
            f"FORWARD_PITCH_UP_THRESHOLD={self.FORWARD_PITCH_UP_THRESHOLD}, "
            f"FORWARD_PITCH_DOWN_THRESHOLD={self.FORWARD_PITCH_DOWN_THRESHOLD}, "
            f"DOWNWARD_PITCH_THRESHOLD={self.DOWNWARD_PITCH_THRESHOLD}, "
            f"POSTURE_JITTER_REF={self.POSTURE_JITTER_REF}, "
            f"FACE_FALLBACK_JITTER_REF={self.FACE_FALLBACK_JITTER_REF}"
        )

        use_mediapipe = mp is not None
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

        # OpenCV 回退（无 mediapipe 时）
        face_cascade = cv2.CascadeClassifier(
            cv2.data.haarcascades + "haarcascade_frontalface_default.xml"
        )

        try:
            while True:
                ok, frame = cap.read()
                if not ok:
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
                    if face_result.detections:
                        detection = face_result.detections[0]
                        bbox = detection.location_data.relative_bounding_box
                        cx = float(bbox.xmin + bbox.width / 2.0)
                        cy = float(bbox.ymin + bbox.height / 2.0)
                        frame_valid = True

                        yaw_ratio = abs(cx - 0.5)
                        pitch_ratio = cy - 0.5
                        is_forward = (
                            yaw_ratio <= self.FORWARD_YAW_THRESHOLD
                            and self.FORWARD_PITCH_UP_THRESHOLD <= pitch_ratio <= self.FORWARD_PITCH_DOWN_THRESHOLD
                        )
                        is_downward = pitch_ratio >= self.DOWNWARD_PITCH_THRESHOLD
                        if is_forward:
                            forward_frames += 1
                        if is_downward:
                            downward_frames += 1
                        if total_frames % self.DEBUG_SAMPLE_EVERY_N_FRAMES == 0:
                            sampled_debug_frames += 1
                            print(
                                "[vision.service.frame] "
                                f"frame={total_frames} yaw={yaw_ratio:.4f} pitch={pitch_ratio:.4f} "
                                f"forward={is_forward} downward={is_downward}"
                            )

                        if pose_result.pose_landmarks:
                            lms = pose_result.pose_landmarks.landmark
                            nose = lms[mp.solutions.pose.PoseLandmark.NOSE]
                            l_shoulder = lms[mp.solutions.pose.PoseLandmark.LEFT_SHOULDER]
                            r_shoulder = lms[mp.solutions.pose.PoseLandmark.RIGHT_SHOULDER]
                            shoulder_mid_x = (l_shoulder.x + r_shoulder.x) / 2.0
                            shoulder_mid_y = (l_shoulder.y + r_shoulder.y) / 2.0
                            shoulder_width = abs(float(l_shoulder.x - r_shoulder.x))
                            # 以肩宽归一化，降低镜头远近变化影响
                            norm_scale = max(shoulder_width, 0.08)
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
                            # 无 pose 时退化为脸框中心相对画面中心，保持可用但置信较低
                            face_center_rel_samples.append((float(cx - 0.5), float(cy - 0.5)))

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
                        is_forward = (
                            yaw_ratio <= self.FORWARD_YAW_THRESHOLD
                            and self.FORWARD_PITCH_UP_THRESHOLD <= pitch_ratio <= self.FORWARD_PITCH_DOWN_THRESHOLD
                        )
                        is_downward = pitch_ratio >= self.DOWNWARD_PITCH_THRESHOLD
                        if is_forward:
                            forward_frames += 1
                        if is_downward:
                            downward_frames += 1
                        if total_frames % self.DEBUG_SAMPLE_EVERY_N_FRAMES == 0:
                            sampled_debug_frames += 1
                            print(
                                "[vision.service.frame] "
                                f"frame={total_frames} yaw={yaw_ratio:.4f} pitch={pitch_ratio:.4f} "
                                f"forward={is_forward} downward={is_downward}"
                            )
                        face_center_rel_samples.append((float(cx - 0.5), float(cy - 0.5)))

                if frame_valid:
                    valid_detection_frames += 1
        finally:
            cap.release()
            if face_detection is not None:
                face_detection.close()
            if pose is not None:
                pose.close()

        denom = max(valid_detection_frames, 1)
        forward_gaze_ratio = round(float(forward_frames) / float(denom), 4)
        downward_head_ratio = round(float(downward_frames) / float(denom), 4)

        posture_stability = 0.0
        posture_mode = "insufficient_samples"
        posture_debug: dict[str, float | int | None] = {
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

            nose_std_x = float(np.std(nose_arr[:, 0]))
            nose_std_y = float(np.std(nose_arr[:, 1]))
            shoulder_center_std_x = float(np.std(shoulder_center_arr[:, 0]))
            shoulder_center_std_y = float(np.std(shoulder_center_arr[:, 1]))
            shoulder_tilt_std = (
                float(np.std(shoulder_tilt_arr))
                if shoulder_tilt_arr.size > 0
                else 0.0
            )

            nose_motion = float(np.sqrt(nose_std_x * nose_std_x + nose_std_y * nose_std_y))
            shoulder_center_motion = float(
                np.sqrt(
                    shoulder_center_std_x * shoulder_center_std_x
                    + shoulder_center_std_y * shoulder_center_std_y
                )
            )
            shoulder_tilt_motion = abs(shoulder_tilt_std)

            # 组合抖动：鼻子相对肩中心 + 肩中心位移 + 双肩倾斜波动
            composite_jitter = (
                0.55 * nose_motion
                + 0.30 * shoulder_center_motion
                + 0.15 * shoulder_tilt_motion
            )
            posture_stability = float(np.exp(-composite_jitter / self.POSTURE_JITTER_REF))
            posture_mode = "pose_shoulder_normalized"
            posture_debug = {
                "nose_motion": round(nose_motion, 6),
                "shoulder_center_motion": round(shoulder_center_motion, 6),
                "shoulder_tilt_motion": round(shoulder_tilt_motion, 6),
                "composite_jitter": round(float(composite_jitter), 6),
                "face_fallback_motion": None,
            }
        elif len(face_center_rel_samples) >= 3:
            face_arr = np.array(face_center_rel_samples, dtype=np.float32)
            face_std_x = float(np.std(face_arr[:, 0]))
            face_std_y = float(np.std(face_arr[:, 1]))
            face_fallback_motion = float(np.sqrt(face_std_x * face_std_x + face_std_y * face_std_y))
            posture_stability = float(np.exp(-face_fallback_motion / self.FACE_FALLBACK_JITTER_REF))
            posture_mode = "face_center_fallback"
            posture_debug["face_fallback_motion"] = round(face_fallback_motion, 6)
        posture_stability = round(posture_stability, 4)
        posture_stability = max(0.0, min(1.0, posture_stability))

        print(
            "[vision.service] "
            f"total_frames={total_frames} valid_detection_frames={valid_detection_frames} "
            f"forward_frames={forward_frames} downward_frames={downward_frames} "
            f"posture_stability={posture_stability} "
            f"sampled_debug_frames={sampled_debug_frames}"
        )
        print(
            "[vision.service.posture] "
            f"mode={posture_mode} "
            f"pose_nose_samples={len(pose_nose_rel_samples)} "
            f"pose_shoulder_center_samples={len(pose_shoulder_center_rel_samples)} "
            f"pose_shoulder_tilt_samples={len(pose_shoulder_tilt_rel_samples)} "
            f"face_fallback_samples={len(face_center_rel_samples)} "
            f"debug={posture_debug}"
        )
        if valid_detection_frames < self.MIN_VALID_DETECTION_FRAMES:
            print(
                "[vision.service][warning] "
                f"有效检测帧过少: {valid_detection_frames} < {self.MIN_VALID_DETECTION_FRAMES}"
            )
            raise RuntimeError(
                "有效检测帧过少，无法生成稳定视觉指标"
            )

        return {
            "forward_gaze_ratio": forward_gaze_ratio,
            "downward_head_ratio": downward_head_ratio,
            "posture_stability": posture_stability,
            "total_frames": int(total_frames),
            "valid_detection_frames": int(valid_detection_frames),
        }