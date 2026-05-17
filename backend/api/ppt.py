from fastapi import APIRouter, UploadFile, File, HTTPException
import os
import uuid
from datetime import datetime
import traceback
from typing import Any

from pydantic import BaseModel, ConfigDict

from factories.provider_factory import get_document_understanding_service, get_ppt_provider
from services.mock_store import ppt_store
from services.ppt_match_service import PPTMatchService

router = APIRouter()

UNSUPPORTED_PPTX_MESSAGE = "当前仅支持上传 .pptx 文件，请先将 PPT 另存为 .pptx 后再上传。"
PPTX_DEP_MISSING_MESSAGE = "后端缺少 python-pptx 依赖，请在 backend 目录执行：pip install python-pptx"


def _is_python_pptx_missing(exc: Exception) -> bool:
    msg = str(exc or "").lower()
    return "python-pptx" in msg or "pptx" in msg


def _friendly_ppt_parse_error(exc: Exception, default_message: str) -> HTTPException:
    if isinstance(exc, ImportError) and _is_python_pptx_missing(exc):
        return HTTPException(status_code=500, detail=PPTX_DEP_MISSING_MESSAGE)
    return HTTPException(status_code=400, detail=default_message)


class PPTMatchV1Request(BaseModel):
    """POST /match_v1 仅接受 JSON body；自动猜页与旧 TF-IDF 二选一。"""

    model_config = ConfigDict(extra="ignore")

    ppt_id: str | None = None
    spoken_text: str | None = None
    transcript: str | None = None
    slides: list[Any] | None = None
    full_text: str | None = None


# 确保上传目录存在
UPLOAD_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'data', 'uploads')
os.makedirs(UPLOAD_DIR, exist_ok=True)


@router.post("/parse")
async def parse_ppt_text(file: UploadFile = File(...)):
    """第一阶段：上传并解析 .pptx，返回逐页结构化文本。"""
    filename = file.filename or ""
    filename_lower = filename.lower()
    if not filename_lower.endswith(".pptx"):
        raise HTTPException(status_code=400, detail=UNSUPPORTED_PPTX_MESSAGE)

    # 保存上传文件
    parse_id = str(uuid.uuid4())
    timestamp = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
    saved_name = f"{parse_id}_{timestamp}.pptx"
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
        raise HTTPException(status_code=500, detail=f"保存文件失败: {repr(e)}")

    # 解析文本（保留原字段 + 统一 document 结构，供后续评分 / 问答复用）
    try:
        parsed = get_ppt_provider().extract_text_by_slide(file_path)
        slides = parsed.get("slides", [])
        if len(slides) == 0:
            raise HTTPException(status_code=400, detail="PPT 解析完成，但未提取到任何页面")
        # document：统一结构 + enrich_document_for_scoring（每页 inferred_title / top_keywords 等，供内容评分 V1）
        document = None
        try:
            document = get_document_understanding_service().parse_pptx(file_path)
        except Exception as du_err:
            print("[ppt.parse] document_understanding 附加结构失败（不影响基础解析）:", repr(du_err))
        out = {
            "full_text": parsed.get("full_text", ""),
            "slides": slides,
        }
        if document is not None:
            out["document"] = document
        return out
    except HTTPException:
        raise
    except ImportError as e:
        raise _friendly_ppt_parse_error(e, "PPT 解析失败，请确认文件为可读取的 .pptx。")
    except Exception as e:
        print("PPT 文本解析失败:")
        traceback.print_exc()
        raise _friendly_ppt_parse_error(e, "PPT 文本解析失败，请确认文件完整后重试。")

@router.post("/upload")
async def upload_ppt(file: UploadFile = File(...)):
    """上传 PPT 文件并解析"""
    filename_lower = (file.filename or "").lower()
    if not filename_lower.endswith(".pptx"):
        raise HTTPException(status_code=400, detail=UNSUPPORTED_PPTX_MESSAGE)

    # 业务用 ppt_id：由本接口生成 UUID，并写入 ppt_store；与 provider 实现无关
    ppt_id = str(uuid.uuid4())
    timestamp = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
    file_ext = ".pptx"
    filename = f"{ppt_id}_{timestamp}{file_ext}"
    file_path = os.path.join(UPLOAD_DIR, filename)

    # 保存文件
    try:
        with open(file_path, "wb") as buffer:
            content = await file.read()
            buffer.write(content)
    except Exception as e:
        print(f"保存文件失败: {e}")
        raise HTTPException(status_code=500, detail=f"保存文件失败: {repr(e)}")

    # 解析 PPT
    try:
        pages = get_ppt_provider().parse_ppt(file_path)
        if not pages:
            raise HTTPException(status_code=400, detail="PPT 解析失败，文件可能为空或格式不兼容")
    except ImportError as e:
        raise _friendly_ppt_parse_error(e, "PPT 解析失败，请确认文件为可读取的 .pptx。")
    except Exception as e:
        # 打印详细的错误信息
        print("PPT 解析失败:")
        traceback.print_exc()
        raise _friendly_ppt_parse_error(e, "PPT 解析失败，请确认文件完整后重试。")

    # 与 /parse 一致：附加统一 document（失败不影响上传主流程）
    document = None
    try:
        document = get_document_understanding_service().parse_pptx(file_path)
    except Exception as du_err:
        print("[ppt.upload] document_understanding 附加结构失败（不影响上传）:", repr(du_err))

    # 存储到内存（可选附带 document，供猜页 V1 / 模拟出题使用）
    entry: dict = {
        "file_path": file_path,
        "pages": pages,
        "upload_time": datetime.utcnow().isoformat(),
    }
    if document is not None:
        entry["document"] = document
    ppt_store[ppt_id] = entry
    print(
        "[ppt.upload] saved ppt_id=",
        ppt_id,
        f"has_document={document is not None}",
        f"page_count={len(pages)}",
        f"ppt_store_has_key={ppt_id in ppt_store}",
        flush=True,
    )

    out = {
        "ppt_id": ppt_id,
        "source_ext": ".pptx",
        "parsed_file_ext": ".pptx",
        "pages": pages
    }
    if document is not None:
        out["document"] = document
    return out

@router.post("/match")
async def match_ppt_content(request: dict):
    """匹配 PPT 页面与讲解内容"""
    ppt_id = request.get("ppt_id")
    page_index = request.get("page_index")
    spoken_text = request.get("spoken_text", "")

    if not ppt_id or page_index is None:
        raise HTTPException(status_code=400, detail="缺少必要参数")

    # 从内存获取 PPT 信息
    ppt_info = ppt_store.get(ppt_id)
    if not ppt_info:
        raise HTTPException(status_code=404, detail="PPT 不存在")

    # 找到对应页面
    target_page = None
    for page in ppt_info["pages"]:
        if page["page_index"] == page_index:
            target_page = page
            break

    if not target_page:
        raise HTTPException(status_code=404, detail="页面不存在")

    # 计算匹配度
    match_result = get_ppt_provider().match_page_content(target_page, spoken_text)

    return match_result


@router.get("/status/{ppt_id}")
async def ppt_status(ppt_id: str):
    """调试用：查询 ppt_id 是否仍在内存 store 中。"""
    pid = (ppt_id or "").strip()
    if not pid:
        raise HTTPException(status_code=400, detail="缺少 ppt_id")
    info = ppt_store.get(pid)
    pages = (info or {}).get("pages") if info else None
    page_list = pages if isinstance(pages, list) else []
    return {
        "ppt_id": pid,
        "exists": info is not None,
        "has_document": bool(info and info.get("document") is not None),
        "has_pages": len(page_list) > 0,
        "page_count": len(page_list),
    }


@router.post("/match_v1")
async def match_ppt_v1(body: PPTMatchV1Request):
    """V1：spoken_text 非空 + ppt_id → 自动猜页；否则 transcript + slides → 旧 TF-IDF。"""
    body_keys = sorted(body.model_dump(exclude_unset=True).keys())
    spoken = (body.spoken_text or "").strip()
    transcript = (body.transcript or "").strip()
    slides = body.slides
    slides_count = len(slides) if isinstance(slides, list) else 0
    ppt_id_raw = (body.ppt_id or "").strip() if body.ppt_id is not None else ""

    # —— 自动猜页：仅当 spoken_text 非空（与 JSON 是否含 key 无关）——
    if spoken:
        print(
            "[ppt.match_v1] mode=auto_guess",
            f"body_keys={body_keys}",
            f"ppt_id={ppt_id_raw!r}",
            f"spoken_text_len={len(spoken)}",
            f"transcript_present={bool(transcript)}",
            f"slides_count={slides_count}",
            flush=True,
        )
        if not ppt_id_raw:
            raise HTTPException(
                status_code=400,
                detail="自动猜页需要提供 ppt_id，请先上传 PPT",
            )
        print(
            "[ppt.match_v1] requested ppt_id=",
            repr(ppt_id_raw),
            f"ppt_store_hit={ppt_id_raw in ppt_store}",
            f"available_keys_count={len(ppt_store)}",
            flush=True,
        )
        ppt_info = ppt_store.get(ppt_id_raw)
        if not ppt_info:
            raise HTTPException(
                status_code=404,
                detail="PPT 不存在或尚未解析，请重新上传",
            )
        pages = ppt_info.get("pages") or []
        document = ppt_info.get("document")
        if not isinstance(pages, list) or len(pages) == 0:
            raise HTTPException(
                status_code=400,
                detail="PPT 已上传，但解析结果不完整，请重新解析后重试",
            )
        try:
            matcher = PPTMatchService()
            guess = matcher.match_best_page(pages, spoken, document=document)
            zero_hit = guess.get("best_page_index") is None
            print(
                "[ppt.match_v1] zero_hit=",
                zero_hit,
                "best_page_index=",
                guess.get("best_page_index"),
                "best_match_score=",
                guess.get("best_match_score"),
                "confidence=",
                guess.get("confidence"),
                flush=True,
            )
            return guess
        except Exception as e:
            print("PPT 猜页匹配失败:")
            traceback.print_exc()
            raise HTTPException(status_code=500, detail=f"PPT 猜页匹配失败: {repr(e)}")

    # —— 旧 TF-IDF：transcript + slides ——
    print(
        "[ppt.match_v1] mode=legacy_tfidf",
        f"body_keys={body_keys}",
        f"ppt_id={ppt_id_raw!r}",
        f"spoken_text_len={len(spoken)}",
        f"transcript_present={bool(transcript)}",
        f"slides_count={slides_count}",
        flush=True,
    )
    if not transcript:
        raise HTTPException(
            status_code=400,
            detail="未检测到有效的 spoken_text（自动猜页）或 transcript（全文匹配），请检查 JSON 字段是否使用 spoken_text / transcript",
        )
    if not isinstance(slides, list):
        raise HTTPException(status_code=400, detail="slides 必须是数组")
    full_text = (body.full_text or "").strip()
    if not full_text:
        # 容错：允许前端只传 slides，后端自动拼 full_text
        full_text = "\n".join([(s.get("text") or "").strip() for s in slides if isinstance(s, dict)]).strip()

    # 基础结构校验
    normalized_slides = []
    for idx, item in enumerate(slides):
        if not isinstance(item, dict):
            raise HTTPException(status_code=400, detail=f"slides[{idx}] 必须是对象")
        page = item.get("page", idx + 1)
        text = item.get("text", "")
        normalized_slides.append({
            "page": page,
            "text": text or ""
        })

    try:
        result = get_ppt_provider().match_transcript_with_ppt(
            transcript=transcript,
            full_text=full_text,
            slides=normalized_slides
        )
        return result
    except Exception as e:
        print("PPT 匹配分析失败:")
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"PPT 匹配分析失败: {repr(e)}")
