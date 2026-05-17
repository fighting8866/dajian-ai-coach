# Vision-on-Board Deployment V1

This document narrows the deployment target to the smallest competition-ready path:

- Frontend stays on the PC
- Main backend stays on the PC
- Only `ascend_service` runs on the Linux board
- Only vision is routed to the board

## 1. Actual request path

Frontend upload flow:

```text
Frontend
-> PC backend /api/vision/analyze
-> backend/providers/vision_ai_provider/ascend_vision_provider.py
-> backend/gateways/ascend_gateway/http_gateway.py
-> Linux board ascend_service /vision/analyze
-> ascend_service/services/vision_service.py
```

Proof flow:

```text
PC backend /api/system/provider-status
-> GET ${ASCEND_BASE_URL}/health
-> return board runtime evidence
```

## 2. Recommended competition config

Use `backend/.env.board.vision.example` as the baseline.

```env
ASCEND_BASE_URL=http://<board-ip>:18081
VISION_PROVIDER=ascend
SPEECH_PROVIDER=local
PPT_PROVIDER=local
QA_PROVIDER=local
QUESTION_PROVIDER=rule
FOLLOWUP_PROVIDER=rule
COMMENTARY_PROVIDER=rule
```

## 3. Board-side install

From the repo root on the Linux board:

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -U pip
pip install -r ascend_service/requirements-board.txt
```

If you explicitly want speech dependencies too:

```bash
pip install -r ascend_service/requirements.txt
```

## 4. Board-side start

```bash
chmod +x scripts/board_start_vision_service.sh
export ASCEND_SERVICE_ROOT=$(pwd)
export ASCEND_HOST=0.0.0.0
export ASCEND_PORT=18081
export ASCEND_RUNTIME_LABEL=linux-board
./scripts/board_start_vision_service.sh
```

Expected startup behavior:

- listens on `http://0.0.0.0:18081`
- exposes `GET /health`
- exposes `POST /vision/analyze`

## 5. PC backend start

From the repo root on the PC:

```powershell
Copy-Item backend\.env.board.vision.example backend\.env
# edit backend\.env and replace ASCEND_BASE_URL with the real board IP
cd backend
uvicorn app:app --host 0.0.0.0 --port 8000
```

## 6. Verification commands

### 6.1 Direct board health

```bash
curl -sS http://<board-ip>:18081/health
```

Success means:

- `status` is `ok`
- `platform_system` is `Linux`
- `runtime_label` is `linux-board` or another explicit Linux board label

If you see `platform_system=Windows` or `runtime_label=windows-local`, you are still hitting a Windows-local process.

### 6.2 Direct board vision analyze

```bash
./scripts/smoke_test_vision_board.sh http://<board-ip>:18081 /path/to/test.webm
```

Success means:

- `/health` returns Linux board runtime evidence
- `POST /vision/analyze` returns HTTP 200
- response top-level `success=true`

### 6.3 PC provider-status

```powershell
.\scripts\print_provider_status.ps1 -BackendBaseUrl http://127.0.0.1:8000
```

Success means:

- `vision_provider=ascend`
- `speech_provider=local`
- `ascend_health_check.reachable=true`
- `ascend_service_runtime.platform_system=Linux`
- `ascend_service_runtime.runtime_label=linux-board` if you exported it on the board

### 6.4 End-to-end backend route

Call the normal backend route and then check backend logs for `[ascend.trace]`.

Expected:

- `[ascend.trace] vision BEGIN`
- `[ascend.trace] vision SEND`
- `[ascend.trace] multipart DONE`
- same `request_id` across the backend trace and the board-side `ascend_service` log

## 7. What indicates each failure type

- Windows-local mistake:
  `provider-status` or direct board `/health` shows `platform_system=Windows` or `runtime_label=windows-local`
- Network/config problem:
  `ascend_health_check.reachable=false`, timeout, connection refused, or wrong `checked_url`
- Board dependency problem:
  board service cannot start because `mediapipe` or `opencv-python-headless` cannot be installed

## 8. Board dependency risk and fallback

Highest-risk board packages:

- `mediapipe==0.10.21`
- `opencv-python-headless`

These are the most likely reasons the current vision service fails to start on ARM/Linux boards.

Fast fallback:

```env
VISION_PROVIDER=local
SPEECH_PROVIDER=local
PPT_PROVIDER=local
QA_PROVIDER=local
QUESTION_PROVIDER=rule
FOLLOWUP_PROVIDER=rule
COMMENTARY_PROVIDER=rule
```

This keeps the training demo path stable without changing scoring, QA, PPT, or the main session flow.
