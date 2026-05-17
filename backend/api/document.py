"""
文档理解增强调试接口（不改变训练主流程）。
"""

from __future__ import annotations

import os
import uuid
from datetime import datetime

from fastapi import APIRouter, File, HTTPException, UploadFile

from factories.provider_factory import (
    get_document_parser_provider_kind,
    get_document_understanding_service,
)

router = APIRouter()

UPLOAD_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), "data", "uploads", "document_debug")
os.makedirs(UPLOAD_DIR, exist_ok=True)

_ALLOWED_EXT = {".pptx", ".pdf", ".png", ".jpg", ".jpeg", ".webp", ".bmp", ".gif", ".tif", ".tiff"}


@router.post("/parse")
async def parse_document_debug(file: UploadFile = File(...)):
    """
    上传单份文档，返回统一结构化理解结果（联调 / 验证用）。

    支持：.pptx、.pdf；图片扩展名会返回占位结构（未做 OCR）。
    """
    filename = file.filename or "upload"
    ext = os.path.splitext(filename.lower())[1]
    if ext not in _ALLOWED_EXT:
        raise HTTPException(
            status_code=400,
            detail=f"当前调试接口允许的后缀：{', '.join(sorted(_ALLOWED_EXT))}",
        )

    parse_id = str(uuid.uuid4())
    timestamp = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
    safe_ext = ext if ext else ".bin"
    saved_name = f"{parse_id}_{timestamp}{safe_ext}"
    file_path = os.path.join(UPLOAD_DIR, saved_name)

    try:
        content = await file.read()
        if not content:
            raise HTTPException(status_code=400, detail="上传文件为空")
        with open(file_path, "wb") as buffer:
            buffer.write(content)
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"保存文件失败: {repr(e)}") from e

    try:
        document = get_document_understanding_service().parse_by_path(
            file_path, original_filename=filename
        )
        return {
            "ok": True,
            "saved_path": file_path,
            "document_parser_provider": get_document_parser_provider_kind(),
            "document": document,
        }
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e)) from e
    except ImportError as e:
        raise HTTPException(status_code=500, detail=str(e)) from e
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"解析失败: {repr(e)}") from e
