"""
文档理解增强 V1：统一 PPT / PDF / 图片（占位）的结构化输出。

- 不引入大模型；以工程规则 + 可选开源解析器为主。
- enrich_document_for_scoring() 为内容评分 V1 提供可解释字段；更深版式理解可接 MarkItDown/Docling。
- PDF：basic 使用 pypdf 文本层；markitdown 优先 MarkItDown；docling 预留。
- 图片：V1 仅占位接口，完整 OCR（如 PaddleOCR）后续接入。
"""

from __future__ import annotations

import os
import re
from typing import Any

from services.ppt_service import PPTService, PPT_AVAILABLE


def _extract_keywords_rule(text: str, limit: int = 12) -> list[str]:
    """与 PPTService 一致的关键词规则（避免循环 import 实例方法）。"""
    if not text:
        return []
    t = text
    separators = [" ", "\n", "\t", "，", "。", "；", "、", ",", ".", ";", "：", ":"]
    for sep in separators:
        t = t.replace(sep, " ")
    words = t.split()
    stop_words = {
        "的", "了", "是", "在", "有", "和", "就", "不", "人", "都", "一", "一个",
        "上", "也", "很", "到", "说", "要", "去", "你", "会", "着", "没有", "看", "好", "自己", "这",
    }
    filtered: list[str] = []
    for word in words:
        if len(word) < 2 or word in stop_words or re.match(r"^\d+$", word):
            continue
        filtered.append(word)
    unique = list(dict.fromkeys(filtered))
    return unique[:limit] if len(unique) > limit else unique


def _pick_title_from_text(text: str) -> str:
    if not text:
        return ""
    first_line = next((line.strip() for line in text.splitlines() if line.strip()), "")
    return first_line[:80]


def _pick_title_from_plain_markdown(md_chunk: str) -> str:
    """从 Markdown 片段取标题：优先 ATX 标题行，否则首行。"""
    for line in (md_chunk or "").splitlines():
        s = line.strip()
        if not s:
            continue
        if s.startswith("#"):
            return re.sub(r"^#+\s*", "", s).strip()[:120]
        return s[:80]
    return ""


def _heading_like_from_plain(plain: str, max_lines: int = 5) -> list[str]:
    out: list[str] = []
    for line in (plain or "").splitlines():
        s = line.strip()
        if not s:
            continue
        if len(s) <= 48 and not s.endswith(("。", ".", "；", ";", "，", ",")):
            out.append(s)
        elif s.startswith("#"):
            out.append(s.lstrip("#").strip())
        if len(out) >= max_lines:
            break
    return out


def _plain_to_simple_markdown(title: str, plain: str) -> str:
    parts: list[str] = []
    if title:
        parts.append(f"# {title}")
    body = (plain or "").strip()
    if body:
        for para in body.split("\n\n"):
            p = para.strip()
            if p:
                parts.append(p)
    return "\n\n".join(parts).strip()


def enrich_document_for_scoring(doc: dict[str, Any]) -> dict[str, Any]:
    """
    为内容评分补充可解释字段（纯规则）。
    后续 MarkItDown/Docling 提升正文结构后，outline_quality / keyword_density 会更稳定。
    """
    pages_in = doc.get("pages") or []
    new_pages: list[dict[str, Any]] = []
    total_kw = 0
    total_len = 0
    heading_lines_count = 0
    for p in pages_in:
        if not isinstance(p, dict):
            continue
        plain = (p.get("plain_text") or "").strip()
        title = (p.get("title") or "").strip()
        kws = list(p.get("keywords") or _extract_keywords_rule(plain))
        inferred = title or _pick_title_from_text(plain)
        hl = _heading_like_from_plain(plain)
        heading_lines_count += len(hl)
        top_kw = kws[:8]
        clen = len(plain)
        total_kw += len(kws)
        total_len += clen
        new_pages.append(
            {
                **p,
                "inferred_title": inferred,
                "top_keywords": top_kw,
                "content_length": clen,
                "heading_like_lines": hl,
            }
        )
    np = max(len(new_pages), 1)
    outline = doc.get("outline") or []
    outline_titles = [
        str(o.get("title") or "").strip()
        for o in outline
        if isinstance(o, dict) and str(o.get("title") or "").strip()
    ]
    outline_quality = min(
        100.0,
        (len([t for t in outline_titles if len(t) >= 2]) / float(np)) * 100.0,
    )
    if heading_lines_count > 0:
        outline_quality = min(100.0, (outline_quality + min(100.0, heading_lines_count * 10.0)) / 2.0)

    full_text = (doc.get("full_text") or "").strip()
    if not full_text and new_pages:
        full_text = "\n\n".join((p.get("plain_text") or "").strip() for p in new_pages if isinstance(p, dict))
    keyword_density = 0.0
    if full_text:
        keyword_density = min(100.0, (total_kw / max(len(full_text), 1)) * 900.0)

    avg_len = total_len / float(np) if np else 0.0
    length_score = min(100.0, max(15.0, avg_len * 0.12))
    structure_blend = min(100.0, outline_quality * 0.55 + keyword_density * 0.25 + length_score * 0.2)

    meta = dict(doc.get("metadata") or {})
    meta["total_pages"] = np
    meta["outline_quality"] = round(outline_quality, 1)
    meta["keyword_density"] = round(keyword_density, 1)
    meta["avg_page_chars"] = round(avg_len, 1)
    meta["structure_score_rule"] = round(structure_blend, 1)
    meta.setdefault(
        "note_scoring",
        "结构质量由规则估计；接入 MarkItDown/Docling 后可提升大纲与版式理解。",
    )
    return {
        **doc,
        "pages": new_pages,
        "full_text": full_text,
        "outline_quality": round(outline_quality, 1),
        "keyword_density": round(keyword_density, 1),
        "total_pages": np,
        "metadata": meta,
    }


def build_document_from_ppt_text_data(data: dict[str, Any] | None) -> dict[str, Any] | None:
    """由训练 stop 时传入的 ppt_text_data 构建统一 document（无文件路径）。"""
    if not data or not isinstance(data, dict):
        return None
    full_text = (data.get("full_text") or "").strip()
    slides = data.get("slides") or []
    if not slides and not full_text:
        return None
    pages: list[dict[str, Any]] = []
    for i, s in enumerate(slides):
        if not isinstance(s, dict):
            continue
        page_no = int(s.get("page") or i + 1)
        plain = (s.get("text") or "").strip()
        title = _pick_title_from_text(plain)
        kws = _extract_keywords_rule(plain)
        pages.append(
            {
                "page_no": page_no,
                "title": title,
                "plain_text": plain,
                "markdown_text": _plain_to_simple_markdown(title, plain),
                "keywords": kws,
                "blocks": [{"type": "slide_text", "text": plain}] if plain else [],
            }
        )
    if not full_text and pages:
        full_text = "\n\n".join((p.get("plain_text") or "").strip() for p in pages)
    outline = [{"page_no": p["page_no"], "title": p.get("title") or f"第 {p['page_no']} 页"} for p in pages]
    doc: dict[str, Any] = {
        "doc_type": "pptx",
        "pages": pages,
        "full_text": full_text,
        "outline": outline,
        "metadata": {"parser": "ppt_text_data", "source": "session.ppt_text_data"},
    }
    return enrich_document_for_scoring(doc)


class DocumentUnderstandingService:
    """统一文档理解入口。"""

    def __init__(self, parser_provider: str | None = None) -> None:
        self._provider = (parser_provider or "basic").strip().lower()

    def parse_by_path(self, file_path: str, original_filename: str | None = None) -> dict[str, Any]:
        name = (original_filename or os.path.basename(file_path) or "").lower()
        ext = os.path.splitext(name)[1].lstrip(".")
        if ext in ("pptx",):
            return self.parse_pptx(file_path)
        if ext in ("pdf",):
            return self.parse_pdf(file_path)
        if ext in ("png", "jpg", "jpeg", "webp", "bmp", "gif", "tiff", "tif"):
            return self.parse_image(file_path, original_filename=name)
        raise ValueError(f"暂不支持的扩展名: {ext or 'unknown'}")

    def parse_pptx(self, file_path: str) -> dict[str, Any]:
        if not PPT_AVAILABLE:
            raise ImportError("python-pptx 未安装，无法解析 pptx")
        ppt = PPTService()
        raw = ppt.extract_text_by_slide(file_path)
        pages: list[dict[str, Any]] = []
        for slide in raw.get("slides") or []:
            page_no = int(slide.get("page") or len(pages) + 1)
            plain = (slide.get("text") or "").strip()
            title = _pick_title_from_text(plain)
            kws = _extract_keywords_rule(plain)
            blocks_raw = slide.get("blocks")
            if isinstance(blocks_raw, list) and blocks_raw:
                blocks: list[dict[str, Any]] = [
                    {"type": str(b.get("type") or "text"), "text": str(b.get("text") or "")}
                    for b in blocks_raw
                    if isinstance(b, dict) and (b.get("text") or "").strip()
                ]
            else:
                blocks = [{"type": "slide_text", "text": plain}] if plain else []
            pages.append(
                {
                    "page_no": page_no,
                    "title": title,
                    "plain_text": plain,
                    "markdown_text": _plain_to_simple_markdown(title, plain),
                    "keywords": kws,
                    "blocks": blocks,
                }
            )
        outline = [
            {"page_no": p["page_no"], "title": p.get("title") or f"第 {p['page_no']} 页"}
            for p in pages
        ]
        doc = {
            "doc_type": "pptx",
            "pages": pages,
            "full_text": (raw.get("full_text") or "").strip(),
            "outline": outline,
            "metadata": {
                "parser": "python-pptx+rules",
                "document_parser_provider": self._provider,
                "slide_count": len(pages),
                "structure": "per_shape_blocks",
            },
        }
        return enrich_document_for_scoring(doc)

    def parse_pdf(self, file_path: str) -> dict[str, Any]:
        meta_backend = "pypdf_text_layer"
        pdf_notes: list[str] = []

        if self._provider == "docling":
            pdf_notes.append(
                "docling：V1 已预留（未调用 Docling SDK）；当前仍使用 pypdf 文本层，"
                "后续可在此分支接入 IBM docling 流水线。"
            )
            meta_backend = "pypdf_text_layer_docling_reserved"

        if self._provider == "markitdown":
            try:
                return self._parse_pdf_markitdown(file_path)
            except ImportError as e:
                pdf_notes.append(f"markitdown 不可用，已回退 pypdf：{e}")
            except Exception as e:
                pdf_notes.append(f"markitdown 转换失败，已回退 pypdf：{e!r}")

        return self._parse_pdf_pypdf(file_path, meta_backend, pdf_notes)

    def _split_markdown_into_pages(self, md_text: str) -> list[str]:
        """轻量分页：换页符优先，否则按 Markdown 标题切分，否则整篇一页。"""
        raw = (md_text or "").strip()
        if not raw:
            return []
        if "\f" in raw:
            return [p.strip() for p in raw.split("\f") if p.strip()]
        parts = re.split(r"\n(?=#{1,6}\s+\S)", raw)
        if len(parts) > 1:
            return [p.strip() for p in parts if p.strip()]
        return [raw]

    def _parse_pdf_markitdown(self, file_path: str) -> dict[str, Any]:
        try:
            from markitdown import MarkItDown
        except ImportError as e:
            raise ImportError("请安装 markitdown，例如: pip install 'markitdown[pdf]'") from e

        md = MarkItDown()
        result = md.convert(file_path)
        md_text = (getattr(result, "text_content", None) or "").strip()
        chunks = self._split_markdown_into_pages(md_text)
        if not chunks:
            chunks = [""]
        pages: list[dict[str, Any]] = []
        outline: list[dict[str, Any]] = []
        full_parts: list[str] = []
        for i, chunk in enumerate(chunks, start=1):
            plain = chunk.strip()
            title = _pick_title_from_plain_markdown(plain)
            pages.append(
                {
                    "page_no": i,
                    "title": title,
                    "plain_text": plain,
                    "markdown_text": chunk,
                    "keywords": _extract_keywords_rule(plain),
                    "blocks": [{"type": "markdown", "text": chunk}] if chunk else [],
                }
            )
            outline.append({"page_no": i, "title": title or f"章节 {i}"})
            if plain:
                full_parts.append(plain)
        meta_m = {
            "parser": "markitdown",
            "document_parser_provider": self._provider,
            "note": "分页：优先换页符 \\f，否则按 Markdown 标题切分；单页仍可能较大。",
            "markitdown_page_count": len(pages),
        }
        joined = "\n\n".join(full_parts).strip()
        if len(joined) < 80:
            meta_m["weak_text_layer"] = True
            meta_m["paddleocr"] = "reserved"
            meta_m["weak_text_hint"] = "MarkItDown 输出过短，可能是扫描 PDF；OCR 未启用。"
        doc = {
            "doc_type": "pdf",
            "pages": pages,
            "full_text": joined,
            "outline": outline,
            "metadata": meta_m,
        }
        return enrich_document_for_scoring(doc)

    def _parse_pdf_pypdf(
        self, file_path: str, backend: str, notes: list[str]
    ) -> dict[str, Any]:
        try:
            from pypdf import PdfReader
        except ImportError as e:
            raise ImportError("请安装 pypdf 以解析 PDF 文本层：pip install pypdf") from e

        reader = PdfReader(file_path)
        pages: list[dict[str, Any]] = []
        full_parts: list[str] = []
        for i, page in enumerate(reader.pages, start=1):
            try:
                plain = (page.extract_text() or "").strip()
            except Exception:
                plain = ""
            title = _pick_title_from_text(plain)
            kws = _extract_keywords_rule(plain)
            pages.append(
                {
                    "page_no": i,
                    "title": title,
                    "plain_text": plain,
                    "markdown_text": _plain_to_simple_markdown(title, plain),
                    "keywords": kws,
                    "blocks": [{"type": "pdf_page_text", "text": plain}] if plain else [],
                }
            )
            if plain:
                full_parts.append(plain)
        outline = [{"page_no": p["page_no"], "title": p.get("title") or f"第 {p['page_no']} 页"} for p in pages]
        meta: dict[str, Any] = {
            "parser": backend,
            "document_parser_provider": self._provider,
            "page_count": len(pages),
        }
        if notes:
            meta["notes"] = notes
        nonempty = sum(1 for p in pages if (p.get("plain_text") or "").strip())
        if pages and nonempty < max(1, len(pages) // 2):
            meta["weak_text_layer"] = True
            meta["paddleocr"] = "reserved"
            meta["weak_text_hint"] = (
                "超过半数页面文本层为空，可能是扫描件；V1 未启用 OCR，后续可接 PaddleOCR。"
            )
        if self._provider == "docling":
            meta["docling"] = "reserved_v1"

        doc = {
            "doc_type": "pdf",
            "pages": pages,
            "full_text": "\n\n".join(full_parts).strip(),
            "outline": outline,
            "metadata": meta,
        }
        return enrich_document_for_scoring(doc)

    def parse_image(self, file_path: str, original_filename: str | None = None) -> dict[str, Any]:
        """图片 / 扫描件：V1 占位，后续可接 PaddleOCR 等。"""
        fname = original_filename or os.path.basename(file_path)
        return {
            "doc_type": "image",
            "pages": [],
            "full_text": "",
            "outline": [],
            "metadata": {
                "parser": "placeholder",
                "document_parser_provider": self._provider,
                "file": fname,
                "status": "not_implemented",
                "message": "图片 OCR 增强（如 PaddleOCR）将在后续版本接入；当前未做识别。",
                "paddleocr": "reserved",
            },
        }
