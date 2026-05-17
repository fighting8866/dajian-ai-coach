#!/usr/bin/env bash

set -euo pipefail

BASE_URL="${1:-${ASCEND_BASE_URL:-http://127.0.0.1:18081}}"
VIDEO_PATH="${2:-}"
REQUEST_ID="${REQUEST_ID:-smoke-vision-$(date +%Y%m%d-%H%M%S)}"

echo "[smoke_test_vision_board] base_url=${BASE_URL}"
echo "[smoke_test_vision_board] request_id=${REQUEST_ID}"

echo "[smoke_test_vision_board] GET ${BASE_URL}/health"
curl -fsS "${BASE_URL%/}/health"
echo

if [[ -z "${VIDEO_PATH}" ]]; then
  echo "[smoke_test_vision_board] skip POST /vision/analyze because no video path was provided"
  echo "[smoke_test_vision_board] usage: $0 http://BOARD_IP:18081 /path/to/test.webm"
  exit 0
fi

if [[ ! -f "${VIDEO_PATH}" ]]; then
  echo "[smoke_test_vision_board] ERROR: video not found: ${VIDEO_PATH}" >&2
  exit 1
fi

echo "[smoke_test_vision_board] POST ${BASE_URL}/vision/analyze video=${VIDEO_PATH}"
curl -fsS -X POST "${BASE_URL%/}/vision/analyze" \
  -F "request_id=${REQUEST_ID}" \
  -F "video_file=@${VIDEO_PATH}"
echo
