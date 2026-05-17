# Ascend Service

`ascend_service` is the Linux board-side FastAPI service used by the backend when `VISION_PROVIDER=ascend`.

## Scope for this repo

- Keep the main training flow on the PC backend.
- Keep speech local for the competition demo.
- Move only vision analysis to the board.

Recommended backend config:

```env
VISION_PROVIDER=ascend
SPEECH_PROVIDER=local
PPT_PROVIDER=local
QA_PROVIDER=local
QUESTION_PROVIDER=rule
FOLLOWUP_PROVIDER=rule
COMMENTARY_PROVIDER=rule
ASCEND_BASE_URL=http://<board-ip>:18081
```

## Board install

Vision-only board install:

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -U pip
pip install -r ascend_service/requirements-board.txt
```

If you need the full service dependency set, use:

```bash
pip install -r ascend_service/requirements.txt
```

## Board start

From the repository root on the Linux board:

```bash
chmod +x scripts/board_start_vision_service.sh
export ASCEND_SERVICE_ROOT=$(pwd)
export ASCEND_RUNTIME_LABEL=linux-board
./scripts/board_start_vision_service.sh
```

The service exposes:

- `GET /health`
- `POST /vision/analyze`
- `POST /speech/analyze`

## Proof that it is running on the board

`GET /health` returns runtime evidence fields, including:

- `hostname`
- `platform_system`
- `platform_machine`
- `platform_release`
- `python_version`
- `python_executable`
- `cwd`
- `service_root`
- `temp_dir`
- `local_ip`
- `process_id`
- `runtime_label`

For a board demo, you should expect `platform_system=Linux` and usually `runtime_label=linux-board`.

## Quick smoke test

Health only:

```bash
./scripts/smoke_test_vision_board.sh http://127.0.0.1:18081
```

Health plus direct vision analyze:

```bash
./scripts/smoke_test_vision_board.sh http://127.0.0.1:18081 /path/to/test.webm
```

## Board dependency risk

高风险包通常是 **mediapipe** 与 **OpenCV 的 pip 轮子**（aarch64 / glibc 差异）。

- **OpenCV**：`requirements-board.txt` 使用 `opencv-python`（不强制 `headless`）。若 `pip` 仍失败，可用系统包 `apt install python3-opencv` 并在**同一**解释器下验证 `import cv2`。
- **MediaPipe**：优先 `pip install "mediapipe>=0.10.9,<0.11"`，让 PyPI 选择本机有 wheel 的版本；**无 MediaPipe 时**仍运行服务，但 `vision_service` 走 **Haar 人脸检测** 且有效帧门限可放宽（默认 4 帧，见 `VISION_MIN_VALID_FRAMES_HAAR`），日志会打印 `mediapipe_unavailable`。
- 启动时控制台一行 **`ascend_service vision_backend=mediapipe`** 或 **`haar-fallback`** 表示实际路径。

仅当**必须**全功能 MediaPipe 且板子无法安装时，才考虑将主后端 `VISION_PROVIDER=local` 作为赛时退路。
