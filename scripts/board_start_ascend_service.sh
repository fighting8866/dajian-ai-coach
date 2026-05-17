#!/usr/bin/env bash
# Start the full ascend_service on the Linux board.
# Competition recommendation still keeps speech local and only routes vision here.

set -euo pipefail

ASCEND_SERVICE_ROOT="${ASCEND_SERVICE_ROOT:-$(cd "$(dirname "$0")/.." && pwd)}"
HOST="${ASCEND_HOST:-0.0.0.0}"
PORT="${ASCEND_PORT:-18081}"

if [[ ! -f "${ASCEND_SERVICE_ROOT}/ascend_service/app.py" ]]; then
  echo "ERROR: ascend_service not found under ASCEND_SERVICE_ROOT=${ASCEND_SERVICE_ROOT}" >&2
  echo "Set ASCEND_SERVICE_ROOT to the parent directory that contains ascend_service/." >&2
  exit 1
fi

cd "${ASCEND_SERVICE_ROOT}"

VENV="${ASCEND_VENV:-${ASCEND_SERVICE_ROOT}/.venv}"
if [[ -f "${VENV}/bin/activate" ]]; then
  # shellcheck source=/dev/null
  source "${VENV}/bin/activate"
elif [[ -f "${VENV}/bin/python" ]]; then
  export PATH="${VENV}/bin:${PATH}"
else
  echo "WARN: venv not found at ${VENV}; using current python3" >&2
fi

export PYTHONUNBUFFERED="${PYTHONUNBUFFERED:-1}"
export ASCEND_RUNTIME_LABEL="${ASCEND_RUNTIME_LABEL:-linux-board}"

echo "[board_start_ascend_service] ASCEND_SERVICE_ROOT=${ASCEND_SERVICE_ROOT}"
echo "[board_start_ascend_service] listening http://${HOST}:${PORT}"
echo "[board_start_ascend_service] runtime_label=${ASCEND_RUNTIME_LABEL}"
echo "[board_start_ascend_service] install file: ascend_service/requirements-board.txt for vision-only board deployment"
echo "[board_start_ascend_service] optional: VISION_TARGET_ANALYSIS_FPS=${VISION_TARGET_ANALYSIS_FPS:-<unset>} VISION_MAX_ANALYSIS_FRAMES=${VISION_MAX_ANALYSIS_FRAMES:-<unset>}"

exec python3 -m uvicorn ascend_service.app:app --host "${HOST}" --port "${PORT}"
