import os
import platform
import socket
import sys
import tempfile
from pathlib import Path
from typing import Optional

from fastapi import APIRouter

router = APIRouter()


def _local_ip_or_none() -> Optional[str]:
    sock: Optional[socket.socket] = None
    try:
        sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        sock.settimeout(0.3)
        sock.connect(("8.8.8.8", 80))
        return sock.getsockname()[0]
    except OSError:
        return None
    finally:
        if sock is not None:
            sock.close()


def _runtime_label() -> str:
    env_label = str(os.getenv("ASCEND_RUNTIME_LABEL") or "").strip()
    if env_label:
        return env_label

    system_name = platform.system()
    machine = (platform.machine() or "").lower()
    if system_name == "Windows":
        return "windows-local"
    if system_name == "Linux":
        if machine in ("aarch64", "arm64", "armv8l", "armv7l") or "arm" in machine:
            return "linux-board"
        return "linux-host"
    if system_name == "Darwin":
        return "macos-host"
    return "other"


@router.get("/health")
def health() -> dict:
    py_ver = f"{sys.version_info.major}.{sys.version_info.minor}.{sys.version_info.micro}"
    service_root = str(Path(__file__).resolve().parents[2])
    return {
        "status": "ok",
        "service": "ascend-service",
        "version": "v1",
        "transport": "multipart_file_upload",
        "endpoints": {
            "speech_analyze": "/speech/analyze",
            "vision_analyze": "/vision/analyze",
        },
        "note": "Backend should call this service through ASCEND_BASE_URL over HTTP multipart upload.",
        "hostname": socket.gethostname(),
        "platform_system": platform.system(),
        "platform_machine": platform.machine() or "",
        "platform_release": platform.release() or "",
        "python_version": py_ver,
        "python_executable": sys.executable,
        "cwd": os.getcwd(),
        "service_root": service_root,
        "temp_dir": tempfile.gettempdir(),
        "local_ip": _local_ip_or_none(),
        "process_id": os.getpid(),
        "runtime_label": _runtime_label(),
    }
