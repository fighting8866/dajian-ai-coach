import math
import re
from collections import Counter
from typing import Any


class PPTMatchService:
    """PPT 匹配服务（第一版：TF-IDF + cosine similarity）。"""

    # 自动猜页：低于此分视为「无有效命中」，不强行选页
    _ZERO_HIT_MAX_SCORE = 0.01

    def _normalize_match_text(self, s: str) -> str:
        """轻量归一化：小写、折叠空白、去掉常见中英文标点（不切分语义，不接模型）。"""
        if not s:
            return ""
        t = (s or "").strip().lower()
        t = re.sub(
            r'[-\s\.,;:!?，。！？、；：（）\[\]【】""''「」_/\\·•—]+',
            " ",
            t,
        )
        return re.sub(r"\s+", " ", t).strip()

    def _build_spoken_match_corpus(self, spoken_raw: str) -> str:
        """口述文本归一化 + 少量同义词扩展，供子串匹配。"""
        base = self._normalize_match_text(spoken_raw)
        if not base:
            return ""
        parts: list[str] = [base]
        if "vue" in base:
            parts.extend(["前端", "web端", "页面", "web"])
        if "web端" in spoken_raw or re.search(r"\bweb\b", base):
            parts.extend(["前端", "页面"])
        raw_for_cn = (spoken_raw or "").strip()
        if "系统架构" in raw_for_cn or "系统架构" in base:
            parts.append("架构")
        if "项目背景" in raw_for_cn or "项目背景" in base:
            parts.append("背景")
        return self._normalize_match_text(" ".join(parts))

    def _phrase_in_corpus(self, phrase: str, corpus: str) -> bool:
        p = self._normalize_match_text(phrase)
        if len(p) < 2:
            return False
        if not corpus:
            return False
        return p in corpus

    # 与 _build_spoken_match_corpus 扩展词一致，用于标题/大纲短词对齐（如「前端选型」↔ 口述 vue）
    _CORPUS_BRIDGE_TERMS = ("前端", "web端", "页面", "web", "架构", "背景")

    def _title_line_hits_corpus(self, phrase: str, corpus: str) -> bool:
        if self._phrase_in_corpus(phrase, corpus):
            return True
        pn = self._normalize_match_text(phrase)
        if len(pn) < 2 or not corpus:
            return False
        for h in self._CORPUS_BRIDGE_TERMS:
            if len(h) >= 2 and h in pn and h in corpus:
                return True
        return False

    # ---------- 旧接口（保留兼容） ----------
    def match_page_content(self, page_info: dict, spoken_text: str) -> dict:
        """匹配页面内容与讲解文本（旧版关键词逻辑，兼容当前前端调用）。"""
        keywords = page_info.get("keywords", [])
        if not keywords:
            return {
                "page_index": page_info.get("page_index", 0),
                "title": page_info.get("title", ""),
                "match_score": 0.0,
                "keyword_coverage": 0.0,
                "matched_keywords": [],
                "missing_keywords": [],
                "comment": "当前页无关键词，无法计算匹配度"
            }

        matched_keywords = []
        missing_keywords = []
        for keyword in keywords:
            if keyword in spoken_text:
                matched_keywords.append(keyword)
            else:
                missing_keywords.append(keyword)

        keyword_coverage = len(matched_keywords) / len(keywords)
        match_score = keyword_coverage * 100
        comment = self._generate_comment(keyword_coverage)

        return {
            "page_index": page_info.get("page_index", 0),
            "title": page_info.get("title", ""),
            "match_score": round(match_score, 2),
            "keyword_coverage": round(keyword_coverage, 2),
            "matched_keywords": matched_keywords,
            "missing_keywords": missing_keywords,
            "comment": comment
        }

    def match_best_page(
        self,
        pages: list[dict],
        spoken_text: str,
        document: dict[str, Any] | None = None,
        top_k: int = 5,
    ) -> dict[str, Any]:
        """对整册 PPT 页做规则打分，猜测与口述文本最匹配的页（V1：标题 / 关键词 / 大纲，无视觉、无大模型）。"""
        pages = pages or []
        spoken = (spoken_text or "").strip()
        corpus = self._build_spoken_match_corpus(spoken)

        doc_pages_by_no: dict[int, dict[str, Any]] = {}
        outline_title_by_no: dict[int, str] = {}
        if document and isinstance(document, dict):
            for p in document.get("pages") or []:
                if not isinstance(p, dict):
                    continue
                try:
                    no = int(p.get("page_no") or 0)
                except (TypeError, ValueError):
                    continue
                if no > 0:
                    doc_pages_by_no[no] = p
            for o in document.get("outline") or []:
                if not isinstance(o, dict):
                    continue
                try:
                    no = int(o.get("page_no") or 0)
                except (TypeError, ValueError):
                    continue
                if no > 0:
                    t = str(o.get("title") or "").strip()
                    if t:
                        outline_title_by_no[no] = t

        candidates: list[dict[str, Any]] = []
        for page in pages:
            if not isinstance(page, dict):
                continue
            try:
                idx = int(page.get("page_index", 0))
            except (TypeError, ValueError):
                continue
            title = str(page.get("title") or "").strip()
            kws = [str(k).strip() for k in (page.get("keywords") or []) if str(k).strip()]
            doc_p = doc_pages_by_no.get(idx)
            inferred = ""
            top_from_doc: list[str] = []
            plain = ""
            if doc_p:
                inferred = str(doc_p.get("inferred_title") or doc_p.get("title") or "").strip()
                top_from_doc = [
                    str(x).strip()
                    for x in (doc_p.get("top_keywords") or doc_p.get("keywords") or [])
                    if str(x).strip()
                ]
                plain = str(doc_p.get("plain_text") or "").strip()
            outline_title = outline_title_by_no.get(idx) or ""

            merged_kw: list[str] = []
            seen_kw: set[str] = set()
            for k in kws + top_from_doc:
                if k not in seen_kw:
                    seen_kw.add(k)
                    merged_kw.append(k)

            title_hit = False
            for phrase in (title, inferred, outline_title):
                if self._title_line_hits_corpus(phrase, corpus):
                    title_hit = True
                    break

            title_score = 40.0 if title_hit else 0.0

            matched_kw: list[str] = []
            if merged_kw and corpus:
                for k in merged_kw:
                    if self._phrase_in_corpus(k, corpus):
                        matched_kw.append(k)
                kw_cov = len(matched_kw) / len(merged_kw)
            else:
                kw_cov = 0.0
            keyword_score = round(kw_cov * 45.0, 4)

            outline_hit = False
            ot = outline_title.strip()
            if ot and self._title_line_hits_corpus(ot, corpus):
                outline_hit = True
            # 大纲标题常与页标题相同，避免与 title_score 重复加权
            if outline_hit and title_hit:
                outline_score = 6.0
            elif outline_hit:
                outline_score = 18.0
            else:
                outline_score = 0.0

            raw = min(100.0, title_score + keyword_score + outline_score)
            display_title = title or inferred or ot or f"第 {idx} 页"

            candidates.append({
                "page_index": idx,
                "title": display_title,
                "match_score": round(raw, 2),
                "title_hit": title_hit,
                "keyword_coverage": round(kw_cov, 4),
                "outline_hit": outline_hit,
                "matched_keywords": matched_kw,
            })

        candidates.sort(key=lambda x: x["match_score"], reverse=True)
        top_n = max(1, min(top_k, 20))
        top_candidates = candidates[:top_n]

        if not top_candidates:
            print(
                "[ppt_match_service.debug] match_best_page best_page_index=None best_score=0.0 "
                f"reason=no_candidates pages_len={len(pages)} spoken_len={len(spoken)}",
                flush=True,
            )
            return {
                "best_page_index": None,
                "best_title": "",
                "best_match_score": 0.0,
                "confidence": 0.0,
                "message": "未找到明显匹配页",
                "top_candidates": [],
            }

        max_score = max(c["match_score"] for c in candidates)
        zero_hit = max_score <= self._ZERO_HIT_MAX_SCORE

        public_top = [
            {
                "page_index": c["page_index"],
                "title": c["title"],
                "match_score": c["match_score"],
                "keyword_coverage": c["keyword_coverage"],
                "title_hit": c["title_hit"],
                "outline_hit": c["outline_hit"],
            }
            for c in top_candidates
        ]

        if zero_hit:
            print(
                "[ppt_match_service.debug] match_best_page best_page_index=None best_score=0.0 "
                f"reason=zero_hit max_score={max_score!r} spoken_len={len(spoken)}",
                flush=True,
            )
            return {
                "best_page_index": None,
                "best_title": "",
                "best_match_score": 0.0,
                "confidence": 0.0,
                "message": "未找到明显匹配页",
                "top_candidates": public_top,
            }

        best = top_candidates[0]
        second_score = top_candidates[1]["match_score"] if len(top_candidates) > 1 else 0.0
        margin = max(0.0, best["match_score"] - second_score)

        if not spoken:
            conf = 0.0
        else:
            strength = min(1.0, max(0.0, best["match_score"]) / 100.0)
            separation = min(1.0, margin / 25.0)
            conf = round(min(1.0, strength * (0.45 + 0.55 * separation)), 4)

        print(
            f"[ppt_match_service.debug] best_page_index={best['page_index']!r}",
            flush=True,
        )
        print(
            f"[ppt_match_service.debug] best_score={best['match_score']!r}",
            flush=True,
        )
        print(
            f"[ppt_match_service.debug] match_best_page confidence={conf!r} spoken_len={len(spoken)}",
            flush=True,
        )
        return {
            "best_page_index": best["page_index"],
            "best_title": best["title"],
            "best_match_score": best["match_score"],
            "confidence": conf,
            "top_candidates": public_top,
        }

    # ---------- 新接口：转写文本 vs PPT 全文 ----------
    def match_transcript_with_ppt(self, transcript: str, full_text: str, slides: list[dict]) -> dict:
        """第一版闭环匹配分析。

        输入：
          - transcript: 转写文本
          - full_text: 整份 PPT 文本
          - slides: [{"page": 1, "text": "..."}, ...]

        输出：
          {
            "overall_match_score": float,
            "slide_matches": [{"page": int, "score": float, "text_preview": str}],
            "missed_pages": [int, ...],
            "off_topic_segments": [str, ...]
          }
        """
        transcript = (transcript or "").strip()
        full_text = (full_text or "").strip()
        slides = slides or []

        if not transcript:
            return {
                "overall_match_score": 0.0,
                "slide_matches": [],
                "missed_pages": [s.get("page") for s in slides if s.get("page") is not None],
                "off_topic_segments": []
            }

        # 文档集合：转写 + 每页文本 + PPT全文
        docs = [transcript]
        slide_texts = []
        for s in slides:
            t = (s.get("text") or "").strip()
            slide_texts.append(t)
            docs.append(t)
        docs.append(full_text)

        vectors = self._tfidf_vectors(docs)
        transcript_vec = vectors[0]
        slide_vecs = vectors[1:1 + len(slides)]
        full_vec = vectors[-1]

        # 总体匹配度（转写 vs PPT全文）
        overall_score = self._cosine_similarity(transcript_vec, full_vec) * 100.0

        # 逐页匹配
        slide_matches = []
        for idx, slide in enumerate(slides):
            page = slide.get("page", idx + 1)
            text = (slide.get("text") or "").strip()
            sim = self._cosine_similarity(transcript_vec, slide_vecs[idx]) * 100.0
            preview = self._preview(text, 90)
            slide_matches.append({
                "page": page,
                "score": round(sim, 2),
                "text_preview": preview
            })

        # 低覆盖页（阈值可替换为模型输出阈值）
        missed_pages = [m["page"] for m in slide_matches if m["score"] < 8.0]

        # 跑题片段：按句切片后，与任一页最大相似度过低
        segments = self._split_segments(transcript)
        off_topic_segments = []
        if segments and slide_vecs:
            seg_docs = segments + slide_texts
            seg_vectors = self._tfidf_vectors(seg_docs)
            seg_vecs = seg_vectors[:len(segments)]
            seg_slide_vecs = seg_vectors[len(segments):]
            for i, seg in enumerate(segments):
                best = 0.0
                for sv in seg_slide_vecs:
                    best = max(best, self._cosine_similarity(seg_vecs[i], sv))
                if best < 0.08:
                    off_topic_segments.append(seg)

        return {
            "overall_match_score": round(overall_score, 2),
            "slide_matches": slide_matches,
            "missed_pages": missed_pages,
            "off_topic_segments": off_topic_segments
        }

    # ---------- 轻量 TF-IDF 组件（后续可替换为向量模型） ----------
    def _tokenize(self, text: str) -> list[str]:
        text = (text or "").lower()
        # 英文词 + 数字 + 连续中文片段
        tokens = re.findall(r"[\u4e00-\u9fff]+|[a-z0-9_]+", text)
        return [t for t in tokens if t.strip()]

    def _tfidf_vectors(self, docs: list[str]) -> list[dict]:
        token_docs = [self._tokenize(d) for d in docs]
        n_docs = len(token_docs)
        if n_docs == 0:
            return []

        # 文档频次 df
        df = Counter()
        for toks in token_docs:
            for t in set(toks):
                df[t] += 1

        vectors = []
        for toks in token_docs:
            tf = Counter(toks)
            total = max(len(toks), 1)
            vec = {}
            for term, cnt in tf.items():
                tf_norm = cnt / total
                idf = math.log((1 + n_docs) / (1 + df[term])) + 1.0
                vec[term] = tf_norm * idf
            vectors.append(vec)
        return vectors

    def _cosine_similarity(self, a: dict, b: dict) -> float:
        if not a or not b:
            return 0.0
        # 点积
        if len(a) > len(b):
            a, b = b, a
        dot = 0.0
        for k, v in a.items():
            dot += v * b.get(k, 0.0)
        # 模长
        na = math.sqrt(sum(v * v for v in a.values()))
        nb = math.sqrt(sum(v * v for v in b.values()))
        if na == 0.0 or nb == 0.0:
            return 0.0
        return dot / (na * nb)

    def _split_segments(self, transcript: str) -> list[str]:
        raw = re.split(r"[。！？!?；;\n]+", transcript or "")
        parts = [s.strip() for s in raw if s and s.strip()]
        # 过滤太短片段，避免噪声
        return [p for p in parts if len(p) >= 8]

    def _preview(self, text: str, max_len: int = 90) -> str:
        if not text:
            return ""
        t = re.sub(r"\s+", " ", text).strip()
        if len(t) <= max_len:
            return t
        return t[:max_len] + "..."

    def _generate_comment(self, keyword_coverage: float) -> str:
        if keyword_coverage >= 0.75:
            return "当前页讲解匹配度较高，核心内容覆盖较充分"
        elif keyword_coverage >= 0.4:
            return "当前页讲解部分覆盖，仍有若干关键点未讲到"
        else:
            return "当前页讲解匹配度较低，建议围绕页面核心内容展开"


def synthesize_pages_from_ppt_text_data(ppt_text_data: dict[str, Any] | None) -> list[dict[str, Any]]:
    """session.stop fallback：ppt_store 无 pages 时，用前端提交的 ppt_text_data.slides 构造 match_best_page 所需页列表（规则分主体不变）。"""
    if not isinstance(ppt_text_data, dict):
        return []
    slides = ppt_text_data.get("slides") or []
    out: list[dict[str, Any]] = []
    for s in slides:
        if not isinstance(s, dict):
            continue
        try:
            idx = int(s.get("page") or 0)
        except (TypeError, ValueError):
            continue
        if idx < 1:
            continue
        text = str(s.get("text") or "").strip()
        kws = [t for t in re.split(r"[\s\n，,。；;、]+", text) if len(t) >= 2][:40]
        title = re.sub(r"\s+", " ", text).strip()[:60] or f"第 {idx} 页"
        out.append({"page_index": idx, "title": title, "keywords": kws})
    return out


def build_plain_ppt_match_from_best_page(
    guess: dict[str, Any],
    pages: list[dict] | None = None,
) -> dict[str, Any] | None:
    """将 match_best_page 的 guess 转为与 PptMatch / score_session 一致的正式 dict（不改匹配算法，仅结构对齐）。"""
    if not guess or not isinstance(guess, dict):
        print("[ppt_match_service.debug] plain_ppt_match skip: invalid guess", flush=True)
        return None
    bpi = guess.get("best_page_index")
    if bpi is None or bpi == "":
        print(
            "[ppt_match_service.debug] plain_ppt_match skip: no best_page_index in guess",
            flush=True,
        )
        return None
    try:
        page_idx = int(bpi)
    except (TypeError, ValueError):
        return None
    tops = guess.get("top_candidates")
    top_list: list[dict] = tops if isinstance(tops, list) else []
    def _pi_eq(d: dict, target: int) -> bool:
        try:
            return int(d.get("page_index")) == target
        except (TypeError, ValueError):
            return False

    top0 = next((c for c in top_list if isinstance(c, dict) and _pi_eq(c, page_idx)), None)
    if top0 is None and top_list:
        t0 = top_list[0]
        top0 = t0 if isinstance(t0, dict) else None
    page_rows = pages if isinstance(pages, list) else []
    page_row = next((p for p in page_rows if isinstance(p, dict) and _pi_eq(p, page_idx)), None)
    if top0 and top0.get("match_score") is not None:
        try:
            match_score = float(top0["match_score"])
        except (TypeError, ValueError):
            match_score = float(guess.get("best_match_score") or 0.0)
    else:
        try:
            match_score = float(guess.get("best_match_score") or 0.0)
        except (TypeError, ValueError):
            match_score = 0.0
    kw_cov = float((top0 or {}).get("keyword_coverage") or 0.0)
    title = str((top0 or {}).get("title") or guess.get("best_title") or "").strip()
    if not title and isinstance(page_row, dict):
        title = str(page_row.get("title") or "").strip()
    if not title:
        title = f"第 {page_idx} 页"
    matched_kw: list[str] = []
    missing_kw: list[str] = []
    if top0 and isinstance(top0.get("matched_keywords"), list):
        matched_kw = [str(k).strip() for k in top0["matched_keywords"] if str(k).strip()]
        mk = top0.get("missing_keywords")
        if isinstance(mk, list):
            missing_kw = [str(k).strip() for k in mk if str(k).strip()]
    elif isinstance(page_row, dict) and isinstance(page_row.get("keywords"), list):
        missing_kw = [str(k).strip() for k in page_row["keywords"] if str(k).strip()]
    conf = guess.get("confidence")
    comment = f"自动猜页（置信度 {conf!s}；规则分 {match_score}）"
    plain = {
        "page_index": page_idx,
        "title": title,
        "match_score": match_score,
        "keyword_coverage": kw_cov,
        "matched_keywords": matched_kw,
        "missing_keywords": missing_kw,
        "comment": comment,
        "match_source": "auto_guess",
    }
    print(
        "[ppt_match_service.debug] plain_ppt_match "
        f"page_index={page_idx!r} match_score={match_score!r} title_preview={title[:48]!r}",
        flush=True,
    )
    return plain