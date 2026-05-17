from __future__ import annotations

from models.result_model import SuggestionItem
from configs.scoring_profiles import DEFAULT_SCORING_PROFILE, get_scoring_profile


def _to_float(value, default=0.0):
    try:
        if value is None or value == "":
            return default
        return float(value)
    except Exception:
        return default


def _to_bool(value, default=False):
    if value is None:
        return default
    if isinstance(value, bool):
        return value
    if isinstance(value, (int, float)):
        return bool(value)
    text = str(value).strip().lower()
    if text in {"true", "1", "yes", "y", "on"}:
        return True
    if text in {"false", "0", "no", "n", "off"}:
        return False
    return default


def _normalize_percent(value) -> float:
    numeric = _to_float(value, 0.0)
    if numeric <= 1:
        numeric *= 100
    return max(0.0, min(100.0, numeric))


def _round_score(value: float) -> float:
    return round(max(0.0, min(100.0, float(value))), 1)


def _compact_for_match(text: str) -> str:
    s = str(text or "")
    s = "".join(ch for ch in s if not ch.isspace())
    return s.lower()


def _substring_match(hay_compact: str, needle: str) -> bool:
    n = _compact_for_match(needle)
    if len(n) < 2:
        return False
    return n in hay_compact


def _collect_outline_strings(
    content_document: dict | None,
    ppt_match_analysis: dict | None,
    ppt_match: dict | None,
) -> list[str]:
    titles: list[str] = []
    if content_document and isinstance(content_document, dict):
        for o in content_document.get("outline") or []:
            if isinstance(o, dict):
                t = str(o.get("title") or "").strip()
                if t:
                    titles.append(t)
        for p in content_document.get("pages") or []:
            if not isinstance(p, dict):
                continue
            for key in ("inferred_title", "title"):
                t = str(p.get(key) or "").strip()
                if t:
                    titles.append(t)
    if ppt_match and isinstance(ppt_match, dict):
        t = str(ppt_match.get("title") or "").strip()
        if t:
            titles.append(t)
    if ppt_match_analysis and isinstance(ppt_match_analysis, dict):
        for sm in ppt_match_analysis.get("slide_matches") or []:
            if not isinstance(sm, dict):
                continue
            preview = str(sm.get("text_preview") or "").strip()
            if not preview:
                continue
            first_line = preview.splitlines()[0].strip() if preview else ""
            if len(first_line) >= 2:
                titles.append(first_line[:120])
    seen: set[str] = set()
    out: list[str] = []
    for t in titles:
        c = _compact_for_match(t)
        if c and c not in seen:
            seen.add(c)
            out.append(t)
    return out[:48]


def _compute_title_outline_hits(
    transcript_text: str,
    ppt_match: dict | None,
    content_document: dict | None,
    ppt_match_analysis: dict | None,
) -> tuple[bool, bool]:
    hay = _compact_for_match(transcript_text)
    title_hit = False
    if hay and ppt_match and isinstance(ppt_match, dict):
        pt = str(ppt_match.get("title") or "").strip()
        if pt and _substring_match(hay, pt):
            title_hit = True
        if not title_hit and content_document and isinstance(content_document, dict):
            try:
                pi = int(ppt_match.get("page_index") or 0)
            except Exception:
                pi = 0
            if pi > 0:
                for p in content_document.get("pages") or []:
                    if not isinstance(p, dict):
                        continue
                    try:
                        if int(p.get("page_no") or 0) != pi:
                            continue
                    except Exception:
                        continue
                    for key in ("inferred_title", "title"):
                        t = str(p.get(key) or "").strip()
                        if t and _substring_match(hay, t):
                            title_hit = True
                            break
                    break
    outline_hit = False
    if hay:
        for cand in _collect_outline_strings(content_document, ppt_match_analysis, ppt_match):
            if _substring_match(hay, cand):
                outline_hit = True
                break
    return title_hit, outline_hit


def _document_quality_score(
    content_document: dict | None,
    ppt_match_analysis: dict | None,
    match_score: float,
    keyword_coverage: float,
) -> float:
    if content_document and isinstance(content_document, dict):
        meta = content_document.get("metadata") or {}
        sr = meta.get("structure_score_rule")
        if sr is not None:
            return _round_score(float(sr))
        oq = float(content_document.get("outline_quality") or meta.get("outline_quality") or 0)
        kd = float(content_document.get("keyword_density") or meta.get("keyword_density") or 0)
        if oq or kd:
            return _round_score(min(100.0, oq * 0.58 + kd * 0.32 + 10.0))
    if ppt_match_analysis and isinstance(ppt_match_analysis, dict):
        overall = _normalize_percent(ppt_match_analysis.get("overall_match_score"))
        slides = ppt_match_analysis.get("slide_matches") or []
        if slides:
            nonempty = sum(
                1
                for sm in slides
                if isinstance(sm, dict)
                and (
                    str(sm.get("text_preview") or "").strip()
                    or _to_float(sm.get("score"), 0.0) > 0
                )
            )
            ratio = nonempty / max(len(slides), 1)
            return _round_score(min(100.0, overall * 0.65 + ratio * 35.0))
        return _round_score(overall)
    return _round_score(min(100.0, match_score * 0.55 + keyword_coverage * 0.45))


class ScoringService:
    def score_session(
        self,
        session_id: str,
        metrics: dict | None = None,
        audio_analysis: dict | None = None,
        audio_metrics: dict | None = None,
        transcript: str | None = None,
        audio_valid: bool | None = None,
        vision_analysis: dict | None = None,
        vision_valid: bool | None = None,
        ppt_match: dict | None = None,
        qa_result: dict | None = None,
        scoring_profile: str | None = None,
        ppt_match_analysis: dict | None = None,
        content_document: dict | None = None,
        defense_material_mode: str | None = None,
    ) -> dict:
        """scoring_profile 传入 defense / interview 等配置键；None 时与旧行为一致，使用默认答辩模式权重。"""
        _dm_raw = str(defense_material_mode or "with_ppt").strip().lower()
        defense_material_mode_norm = "without_ppt" if _dm_raw == "without_ppt" else "with_ppt"
        print(f"[scoring_service] scoring_profile input={scoring_profile!r}")
        profile = get_scoring_profile(scoring_profile)
        print(
            f"[scoring_service] scoring_profile resolved key={profile['key']!r} label={profile['label']!r}"
        )
        metrics = dict(metrics or {})
        audio_analysis = dict(audio_analysis or {})
        audio_metrics = dict(audio_metrics or {})
        vision_analysis = dict(vision_analysis or {})
        ppt_match = dict(ppt_match or {}) if isinstance(ppt_match, dict) else None
        qa_result = dict(qa_result or {}) if isinstance(qa_result, dict) else None
        ppt_match_analysis = (
            dict(ppt_match_analysis) if isinstance(ppt_match_analysis, dict) else None
        )
        content_document = dict(content_document) if isinstance(content_document, dict) else None

        transcript_text = str(
            transcript
            if transcript is not None
            else audio_analysis.get("transcript") or ""
        ).strip()
        resolved_audio_valid = (
            _to_bool(audio_valid, False)
            if audio_valid is not None
            else _to_bool(audio_analysis.get("audio_valid"), bool(transcript_text))
        )
        resolved_vision_valid = (
            _to_bool(vision_valid, False)
            if vision_valid is not None
            else _to_bool(vision_analysis.get("vision_valid"), bool(vision_analysis))
        )

        audio_source = {
            "speech_rate": audio_analysis.get("speech_rate", audio_metrics.get("speech_rate", metrics.get("speech_rate"))),
            "pause_count": audio_analysis.get("pause_count", audio_metrics.get("pause_count", metrics.get("pause_count"))),
            "avg_pause_sec": audio_analysis.get("avg_pause_sec", audio_metrics.get("avg_pause_sec", metrics.get("avg_pause_sec"))),
            "filler_count": audio_analysis.get("filler_count", audio_metrics.get("filler_count", metrics.get("filler_count"))),
        }
        vision_source = {
            "forward_gaze_ratio": vision_analysis.get("forward_gaze_ratio", metrics.get("forward_gaze_ratio")),
            "downward_head_ratio": vision_analysis.get("downward_head_ratio", metrics.get("downward_head_ratio")),
            "posture_stability": vision_analysis.get("posture_stability", metrics.get("posture_stability")),
        }

        language_module = self._score_language(audio_source, transcript_text, resolved_audio_valid, audio_analysis)
        posture_module = self._score_posture(vision_source, resolved_vision_valid, vision_analysis)
        content_module = self._score_content(
            ppt_match,
            transcript_text,
            ppt_match_analysis,
            content_document,
            defense_material_mode_norm,
        )
        qa_module = self._score_qa(qa_result)

        modules = {
            "language": language_module,
            "posture": posture_module,
            "content": content_module,
            "qa": qa_module,
        }
        original_weights = dict(profile["weights"])
        valid_keys = [key for key, value in modules.items() if value["valid"]]
        valid_weight_sum = sum(original_weights.get(key, 0) for key in valid_keys)
        effective_weights = {}
        for key in original_weights:
            if key in valid_keys and valid_weight_sum > 0:
                effective_weights[key] = round(original_weights[key] / valid_weight_sum, 4)
            else:
                effective_weights[key] = 0.0

        total_score = 0.0
        for key, module in modules.items():
            total_score += module["score"] * effective_weights.get(key, 0.0)
        total_score = _round_score(total_score if valid_weight_sum > 0 else 0.0)

        score_breakdown = {
            "profile_key": profile["key"],
            "profile_label": profile["label"],
            "original_weights": original_weights,
            "effective_weights": effective_weights,
            "valid_modules": {key: value["valid"] for key, value in modules.items()},
            "modules": modules,
            "total": {
                "score": total_score,
                "valid_weight_sum": valid_weight_sum,
                "rule": "仅对有效模块按当前评分模式权重重新归一化后汇总总分",
            },
        }
        score_explanations = self._build_score_explanations(
            modules=modules,
            profile=profile,
            effective_weights=effective_weights,
            total_score=total_score,
            audio_source=audio_source,
            transcript_text=transcript_text,
            audio_valid=resolved_audio_valid,
            audio_analysis=audio_analysis,
            vision_source=vision_source,
            vision_valid=resolved_vision_valid,
            vision_analysis=vision_analysis,
            ppt_match=ppt_match,
            qa_result=qa_result,
            defense_material_mode=defense_material_mode_norm,
        )
        print(
            "[scoring_service] final score_explanations=",
            score_explanations,
        )

        language_score = language_module["score"]
        posture_score = posture_module["score"]
        content_score = content_module["score"]
        qa_score = qa_module["score"]
        suggestions = self._build_suggestions(modules, defense_material_mode_norm)
        summary = self._build_summary(total_score, modules)
        detailed_metrics = self._build_metrics(audio_source, vision_source)

        return {
            "session_id": session_id,
            "scoring_profile": profile["key"],
            "scoring_profile_label": profile["label"],
            "total_score": total_score,
            "language_score": language_score,
            "posture_score": posture_score,
            "content_score": content_score,
            "qa_score": qa_score,
            "content_breakdown": (content_module or {}).get("content_breakdown"),
            "qa_breakdown": (qa_module or {}).get("qa_breakdown"),
            "score_breakdown": score_breakdown,
            "score_explanations": score_explanations,
            "summary": summary,
            "suggestions": suggestions,
            "metrics": detailed_metrics,
        }

    def _score_language(self, audio_source: dict, transcript_text: str, audio_valid: bool, audio_analysis: dict) -> dict:
        if not audio_valid:
            reason = str(audio_analysis.get("audio_message") or "音频无效，本轮不纳入语言评分")
            return self._invalid_module("语言表达", reason)

        speech_rate = _to_float(audio_source.get("speech_rate"), 0.0)
        pause_count = _to_float(audio_source.get("pause_count"), 0.0)
        avg_pause_sec = _to_float(audio_source.get("avg_pause_sec"), 0.0)
        filler_count = _to_float(audio_source.get("filler_count"), 0.0)
        transcript_len = len(transcript_text)

        components = [
            self._component(
                "语速控制",
                speech_rate,
                40,
                self._range_score(
                    speech_rate,
                    [(180, 260, 40), (150, 300, 30), (120, 340, 20)],
                    10,
                ),
                "180-260 字/分钟最好，偏快或偏慢会扣分",
            ),
            self._component(
                "停顿节奏",
                {"pause_count": pause_count, "avg_pause_sec": avg_pause_sec},
                30,
                self._pause_score(pause_count, avg_pause_sec),
                "停顿次数与平均停顿时长共同评分，过密或过长都会扣分",
            ),
            self._component(
                "口头禅控制",
                filler_count,
                20,
                self._filler_score(filler_count),
                "口头禅越少越好",
            ),
            self._component(
                "转写信息量",
                transcript_len,
                10,
                self._transcript_richness_score(transcript_len),
                "转写文本过短时，语言表达的信息量得分会降低",
            ),
        ]
        return self._finalize_module("语言表达", components)

    def _score_posture(self, vision_source: dict, vision_valid: bool, vision_analysis: dict) -> dict:
        if not vision_valid:
            reason = str(vision_analysis.get("vision_message") or "视觉无效，本轮不纳入仪态评分")
            return self._invalid_module("仪态表现", reason)

        gaze = _to_float(vision_source.get("forward_gaze_ratio"), 0.0)
        downward = _to_float(vision_source.get("downward_head_ratio"), 0.0)
        stability = _to_float(vision_source.get("posture_stability"), 0.0)

        components = [
            self._component(
                "正视前方比例",
                gaze,
                40,
                self._ratio_score(gaze, [(0.75, 40), (0.6, 32), (0.45, 22), (0.3, 14)], 8),
                "正视前方比例越高越好",
            ),
            self._component(
                "低头率",
                downward,
                30,
                self._descending_ratio_score(downward, [(0.08, 30), (0.15, 24), (0.25, 16), (0.35, 10)], 5),
                "低头率越低越好",
            ),
            self._component(
                "姿态稳定度",
                stability,
                30,
                self._ratio_score(stability, [(0.85, 30), (0.72, 24), (0.58, 18), (0.42, 10)], 5),
                "姿态稳定度越高越好",
            ),
        ]
        return self._finalize_module("仪态表现", components)

    def _score_content(
        self,
        ppt_match: dict | None,
        transcript_text: str | None,
        ppt_match_analysis: dict | None,
        content_document: dict | None,
        defense_material_mode: str = "with_ppt",
    ) -> dict:
        """
        内容讲解 V1：在仍有 ppt_match 时才为有效模块；综合页内匹配、关键词覆盖、标题/大纲命中与文档结构（规则）。
        解析器升级（MarkItDown/Docling）后可提升 content_document 侧结构分稳定性。
        """
        _pms_hint = (ppt_match or {}).get("match_source") if isinstance(ppt_match, dict) else None
        print(
            "[scoring_service.content] incoming ppt_match=",
            ppt_match,
            "ppt_match_source=",
            _pms_hint,
            flush=True,
        )
        tr = str(transcript_text or "").strip()
        dq_baseline = _document_quality_score(content_document, ppt_match_analysis, 0.0, 0.0)
        if not ppt_match:
            breakdown = {
                "match_score": 0.0,
                "keyword_coverage": 0.0,
                "title_hit": False,
                "outline_hit": False,
                "document_quality": dq_baseline,
                "final_content_score": 0.0,
            }
            th, oh = _compute_title_outline_hits(tr, None, content_document, ppt_match_analysis)
            breakdown["title_hit"] = th
            breakdown["outline_hit"] = oh
            if defense_material_mode == "without_ppt":
                mod = self._invalid_module(
                    "内容讲解",
                    "本轮为无课件答辩训练，未启用内容匹配模块；内容模块本轮未参与评分。",
                )
                print(
                    "[scoring_service.content] content_valid=False (without_ppt, content matching disabled)",
                    flush=True,
                )
            else:
                mod = self._invalid_module(
                    "内容讲解",
                    "未提供当前页 PPT 匹配结果（ppt_match），本轮不纳入内容评分",
                )
                print("[scoring_service.content] content_valid=False (no ppt_match)", flush=True)
            mod["content_breakdown"] = breakdown
            return mod

        match_score = _normalize_percent(ppt_match.get("match_score"))
        coverage = _normalize_percent(ppt_match.get("keyword_coverage"))
        hit_keywords = len(ppt_match.get("matched_keywords") or [])
        missing_keywords = len(ppt_match.get("missing_keywords") or [])
        title_hit, outline_hit = _compute_title_outline_hits(
            tr, ppt_match, content_document, ppt_match_analysis
        )
        document_quality = _document_quality_score(
            content_document, ppt_match_analysis, match_score, coverage
        )

        structure_penalty = 0.0
        if document_quality < 28:
            structure_penalty = 6.0
        elif document_quality < 40:
            structure_penalty = 3.0

        comp_match = round(match_score * 0.5, 1)
        comp_kw = round(coverage * 0.25, 1)
        if title_hit and outline_hit:
            comp_outline = 15.0
        elif title_hit or outline_hit:
            comp_outline = 10.0
        else:
            comp_outline = 0.0
        comp_doc = max(0.0, round(document_quality * 0.1, 1) - structure_penalty)

        kw_bonus = 0.0
        if hit_keywords > 0 and missing_keywords == 0:
            kw_bonus = 3.0
        elif hit_keywords >= missing_keywords and hit_keywords > 0:
            kw_bonus = 1.5

        components = [
            self._component(
                "页内匹配度",
                match_score,
                50,
                comp_match,
                "当前页匹配分映射到 50 分档（内容对齐主信号）",
            ),
            self._component(
                "关键词覆盖率",
                coverage,
                25,
                comp_kw,
                "关键词覆盖率映射到 25 分档",
            ),
            self._component(
                "标题与大纲命中",
                {"title_hit": title_hit, "outline_hit": outline_hit},
                15,
                min(15.0, comp_outline + kw_bonus),
                "转写是否命中当前页标题或课件大纲标题；关键词全命中时略有加成",
            ),
            self._component(
                "文档结构质量",
                document_quality,
                10,
                comp_doc,
                "由统一 document 元数据（outline_quality 等）或逐页分析规则估计；结构偏弱会适度减分",
            ),
        ]
        module = self._finalize_module("内容讲解", components)
        module["content_breakdown"] = {
            "match_score": round(match_score, 1),
            "keyword_coverage": round(coverage, 1),
            "title_hit": title_hit,
            "outline_hit": outline_hit,
            "document_quality": document_quality,
            "final_content_score": module["score"],
        }
        print(
            "[scoring_service.content] content_valid=",
            module.get("valid"),
            flush=True,
        )
        return module

    def _score_qa(self, qa_result: dict | None) -> dict:
        """
        问答表现 V1：规则综合切题、覆盖/缺失、回答长度与清晰度；profile 权重不变。
        followup_candidate_topics / weak_points 预留追问官、点评官（当前规则生成）。
        """
        if not qa_result:
            bd = {
                "is_relevant": False,
                "coverage_score": 0.0,
                "hit_keyword_count": 0,
                "missing_keyword_count": 0,
                "answer_length": 0,
                "answer_length_score": 0.0,
                "answer_information_level": 0.0,
                "answer_keyword_density": 0.0,
                "clarity_score": 0.0,
                "relevance_reason": "未收到问答评估结果（qa_result）。",
                "followup_candidate_topics": [],
                "weak_points": ["未提供 qa_result，无法计算问答得分"],
                "final_qa_score": 0.0,
            }
            mod = self._invalid_module("问答表现", "未提供问答结果（qa_result），本轮不纳入问答评分")
            mod["qa_breakdown"] = bd
            return mod

        try:
            from services.qa_service import enrich_qa_evaluation

            qa = enrich_qa_evaluation(dict(qa_result), str(qa_result.get("question") or ""))
        except Exception:
            qa = dict(qa_result)

        answer_text = str(qa.get("answer_text") or "")
        is_relevant = _to_bool(qa.get("is_relevant"), False)
        cov_r = _to_float(qa.get("coverage_score"), 0.0)
        if cov_r > 1.0:
            cov_r = cov_r / 100.0
        cov_r = max(0.0, min(1.0, cov_r))
        coverage_pct = cov_r * 100.0

        hit_kw = qa.get("hit_keywords") or []
        miss_kw = qa.get("missing_keywords") or []
        hit = len(hit_kw)
        miss = len(miss_kw)

        alen = qa.get("answer_length")
        try:
            alen_i = int(alen) if alen is not None else len(answer_text)
        except (TypeError, ValueError):
            alen_i = len(answer_text)

        len_score = _to_float(qa.get("answer_length_score"), None)
        if len_score is None:
            from services.qa_service import compute_answer_length_score

            len_score = compute_answer_length_score(alen_i)

        clarity = _to_float(qa.get("clarity_score"), None)
        if clarity is None:
            clarity = 58.0

        comp_rel = 36.0 if is_relevant else 9.0
        comp_kw = round(coverage_pct * 0.26, 1) + min(8.0, hit * 1.1)
        comp_kw -= min(14.0, miss * 2.2)
        comp_kw = max(0.0, min(34.0, comp_kw))

        comp_len = round(float(len_score) * 0.20, 1)
        comp_clr = round(float(clarity) * 0.10, 1)

        components = [
            self._component(
                "切题度",
                is_relevant,
                36,
                comp_rel,
                "回答切题时大幅加分，明显偏题时显著扣分",
            ),
            self._component(
                "关键词覆盖与要点",
                {"hit": hit, "missing": miss, "coverage_ratio": round(cov_r, 3)},
                34,
                comp_kw,
                "参考关键词覆盖率与命中数加分，缺失关键词按条减分",
            ),
            self._component(
                "回答信息量",
                {"chars": alen_i, "length_score": len_score},
                20,
                comp_len,
                "回答长度与可展开程度（规则近似）",
            ),
            self._component(
                "表达清晰度",
                clarity,
                10,
                comp_clr,
                "分句、口头禅密度等规则近似；后续可由 AI 点评官替代",
            ),
        ]
        module = self._finalize_module("问答表现", components)
        info_lvl = _to_float(qa.get("answer_information_level"), 0.0)
        module["qa_breakdown"] = {
            "is_relevant": is_relevant,
            "coverage_score": round(cov_r, 4),
            "hit_keyword_count": hit,
            "missing_keyword_count": miss,
            "answer_length": alen_i,
            "answer_length_score": round(float(len_score), 1),
            "answer_information_level": round(info_lvl, 1),
            "answer_keyword_density": round(_to_float(qa.get("answer_keyword_density"), 0.0), 4),
            "clarity_score": round(float(clarity), 1),
            "relevance_reason": str(qa.get("relevance_reason") or ""),
            "followup_candidate_topics": list(qa.get("followup_candidate_topics") or []),
            "weak_points": list(qa.get("weak_points") or []),
            "final_qa_score": module["score"],
        }
        return module

    def _build_metrics(self, audio_source: dict, vision_source: dict) -> list[dict]:
        return [
            {
                "name": "语速",
                "value": _round_score(_to_float(audio_source.get("speech_rate"), 0.0)),
                "unit": "字/分钟",
                "description": "演讲平均语速",
            },
            {
                "name": "停顿次数",
                "value": int(_to_float(audio_source.get("pause_count"), 0.0)),
                "unit": "次",
                "description": "演讲中的停顿次数",
            },
            {
                "name": "平均停顿时长",
                "value": _round_score(_to_float(audio_source.get("avg_pause_sec"), 0.0)),
                "unit": "秒",
                "description": "平均每次停顿时长",
            },
            {
                "name": "口头禅次数",
                "value": int(_to_float(audio_source.get("filler_count"), 0.0)),
                "unit": "次",
                "description": "无意义填充词出现次数",
            },
            {
                "name": "正视前方比例",
                "value": _round_score(_to_float(vision_source.get("forward_gaze_ratio"), 0.0)),
                "unit": "",
                "description": "面向听众的时间比例",
            },
            {
                "name": "低头率",
                "value": _round_score(_to_float(vision_source.get("downward_head_ratio"), 0.0)),
                "unit": "",
                "description": "低头看稿或屏幕的比例",
            },
            {
                "name": "姿态稳定度",
                "value": _round_score(_to_float(vision_source.get("posture_stability"), 0.0)),
                "unit": "",
                "description": "站姿和身体稳定程度",
            },
        ]

    def _build_score_explanations(
        self,
        modules: dict,
        profile: dict,
        effective_weights: dict,
        total_score: float,
        audio_source: dict,
        transcript_text: str,
        audio_valid: bool,
        audio_analysis: dict,
        vision_source: dict,
        vision_valid: bool,
        vision_analysis: dict,
        ppt_match: dict | None,
        qa_result: dict | None,
        defense_material_mode: str = "with_ppt",
    ) -> dict:
        score_explanations = {
            "total": self._build_total_explanations(
                modules, profile, effective_weights, total_score, defense_material_mode
            ),
            "language": self._build_language_explanations(audio_source, transcript_text, audio_valid, audio_analysis, modules["language"]["score"]),
            "posture": self._build_posture_explanations(vision_source, vision_valid, vision_analysis, modules["posture"]["score"]),
            "content": self._build_content_explanations(
                ppt_match,
                modules["content"]["score"],
                modules["content"].get("content_breakdown"),
                transcript_text,
                modules["content"]["valid"],
                modules["content"].get("invalid_reason"),
                defense_material_mode,
            ),
            "qa": self._build_qa_explanations(
                qa_result,
                modules["qa"]["score"],
                modules["qa"].get("qa_breakdown"),
                modules["qa"]["valid"],
                modules["qa"].get("invalid_reason"),
            ),
        }
        for key in ("total", "language", "posture", "content", "qa"):
            value = score_explanations.get(key)
            if not isinstance(value, dict) or "summary" not in value or "items" not in value:
                raise ValueError(f"score_explanations[{key}] must be an object with summary and items, got {value!r}")
        return score_explanations

    def _build_total_explanations(
        self,
        modules: dict,
        profile: dict,
        effective_weights: dict,
        total_score: float,
        defense_material_mode: str = "with_ppt",
    ) -> dict:
        valid_items = [(key, value) for key, value in modules.items() if value["valid"]]
        invalid_items = [(key, value) for key, value in modules.items() if not value["valid"]]
        valid_labels = [value["label"] for _, value in valid_items]

        def _invalid_label(key: str, mod: dict) -> str:
            if key == "content" and defense_material_mode == "without_ppt" and not mod["valid"]:
                return "内容讲解（本轮未启用课件匹配）"
            return mod["label"]

        invalid_labels = [_invalid_label(key, value) for key, value in invalid_items]
        explanations = []
        explanations.append(
            f"当前评分模式为{profile['label']}，原始权重为语言 {profile['weights']['language']}%、仪态 {profile['weights']['posture']}%、内容 {profile['weights']['content']}%、问答 {profile['weights']['qa']}%。"
        )
        explanations.append(
            f"本次有效模块：{'、'.join(valid_labels) if valid_labels else '无'}；无效模块：{'、'.join(invalid_labels) if invalid_labels else '无'}。"
        )
        problem_invalid = [
            (k, v)
            for k, v in invalid_items
            if not (k == "content" and defense_material_mode == "without_ppt")
        ]
        if invalid_items:
            if problem_invalid:
                explanations.append(
                    "由于存在无效或缺失模块，总分已按有效模块重新归一化计算，未让缺失模块直接拉低总分。"
                )
            else:
                explanations.append(
                    "本轮为无课件答辩训练，课件内容匹配未启用；总分已按有效模块重新归一化计算。"
                )
        else:
            explanations.append("本次四个模块均有效，总分按原始权重直接汇总。")

        normalized_weight_text = "，".join(
            f"{modules[key]['label']} {round(effective_weights.get(key, 0.0) * 100, 1)}%"
            for key in ("language", "posture", "content", "qa")
            if effective_weights.get(key, 0.0) > 0
        ) or "无有效模块权重"
        explanations.append(f"当前参与总分的有效权重分配为：{normalized_weight_text}。")

        if valid_items:
            strongest = max(valid_items, key=lambda item: item[1]["score"])
            weakest = min(valid_items, key=lambda item: item[1]["score"])
            explanations.append(
                f"拉高总分的主要模块是{strongest[1]['label']}（{strongest[1]['score']}分）；拉低总分的主要模块是{weakest[1]['label']}（{weakest[1]['score']}分）。"
            )
        else:
            explanations.append("当前没有有效评分模块，因此总分为 0。")
        explanations.append(f"最终总分为 {total_score} 分。")
        summary = (
            f"总分 {total_score} 分，当前使用{profile['label']}；"
            f"有效模块为{'、'.join(valid_labels) if valid_labels else '无'}，"
            f"无效模块为{'、'.join(invalid_labels) if invalid_labels else '无'}。"
        )
        return {
            "summary": summary,
            "items": explanations,
        }

    def _build_language_explanations(
        self,
        audio_source: dict,
        transcript_text: str,
        audio_valid: bool,
        audio_analysis: dict,
        score: float,
    ) -> dict:
        if not audio_valid:
            reason = str(audio_analysis.get("audio_message") or "未检测到有效语音")
            return {
                "summary": "本轮语言模块无效，未纳入总分。",
                "items": [f"本轮语言模块无效，未纳入总分。原因：{reason}。"],
            }

        speech_rate = _to_float(audio_source.get("speech_rate"), 0.0)
        pause_count = _to_float(audio_source.get("pause_count"), 0.0)
        avg_pause_sec = _to_float(audio_source.get("avg_pause_sec"), 0.0)
        filler_count = _to_float(audio_source.get("filler_count"), 0.0)
        transcript_len = len(transcript_text or "")

        if 180 <= speech_rate <= 260:
            speech_text = f"语速 {speech_rate:.0f} 字/分钟，处于合理区间。"
        elif speech_rate > 260:
            speech_text = f"语速 {speech_rate:.0f} 字/分钟，整体偏快。"
        else:
            speech_text = f"语速 {speech_rate:.0f} 字/分钟，整体偏慢。"

        if 3 <= pause_count <= 15 and 0.5 <= avg_pause_sec <= 1.5:
            pause_text = f"停顿较自然，停顿次数 {pause_count:.0f} 次，平均停顿 {avg_pause_sec:.1f} 秒。"
        elif pause_count > 15 or avg_pause_sec > 1.5:
            pause_text = f"停顿偏多或偏长，停顿次数 {pause_count:.0f} 次，平均停顿 {avg_pause_sec:.1f} 秒。"
        else:
            pause_text = f"停顿偏少或偏短，停顿次数 {pause_count:.0f} 次，平均停顿 {avg_pause_sec:.1f} 秒。"

        if filler_count <= 2:
            filler_text = f"口头禅控制较好，本轮检测到 {filler_count:.0f} 次。"
        elif filler_count <= 5:
            filler_text = f"口头禅略多，本轮检测到 {filler_count:.0f} 次。"
        else:
            filler_text = f"口头禅偏多，本轮检测到 {filler_count:.0f} 次。"

        if transcript_len >= 60:
            transcript_text_line = f"转写文本信息量较充分，转写长度约 {transcript_len} 字。"
        elif transcript_len > 0:
            transcript_text_line = f"转写文本较短，信息量一般，转写长度约 {transcript_len} 字。"
        else:
            transcript_text_line = "转写文本为空，语言信息量不足。"

        return {
            "summary": f"语言模块得分 {score} 分，语速、停顿和口头禅共同决定该分数。",
            "items": [
                f"语言模块得分 {score} 分。",
                speech_text,
                pause_text,
                filler_text,
                transcript_text_line,
            ],
        }

    def _build_posture_explanations(
        self,
        vision_source: dict,
        vision_valid: bool,
        vision_analysis: dict,
        score: float,
    ) -> dict:
        if not vision_valid:
            reason = str(vision_analysis.get("vision_message") or "视觉分析无有效结果")
            return {
                "summary": "本轮仪态模块无效，未纳入总分。",
                "items": [f"本轮仪态模块无效，未纳入总分。原因：{reason}。"],
            }

        gaze = _to_float(vision_source.get("forward_gaze_ratio"), 0.0)
        downward = _to_float(vision_source.get("downward_head_ratio"), 0.0)
        stability = _to_float(vision_source.get("posture_stability"), 0.0)

        if gaze >= 0.6:
            gaze_text = f"正视前方较稳定，正视前方比例为 {gaze:.2f}。"
        elif gaze >= 0.4:
            gaze_text = f"正视前方表现一般，正视前方比例为 {gaze:.2f}。"
        else:
            gaze_text = f"正视前方较少，正视前方比例仅为 {gaze:.2f}。"

        if downward < 0.15:
            downward_text = f"低头控制较好，低头率为 {downward:.2f}。"
        elif downward < 0.25:
            downward_text = f"低头略多，低头率为 {downward:.2f}。"
        else:
            downward_text = f"低头较多，低头率为 {downward:.2f}。"

        if stability >= 0.72:
            stability_text = f"姿态较稳定，稳定度为 {stability:.2f}。"
        elif stability >= 0.5:
            stability_text = f"姿态稳定度一般，稳定度为 {stability:.2f}。"
        else:
            stability_text = f"姿态晃动偏多，稳定度仅为 {stability:.2f}。"

        return {
            "summary": f"仪态模块得分 {score} 分，主要由正视前方、低头率和姿态稳定度决定。",
            "items": [
                f"仪态模块得分 {score} 分。",
                gaze_text,
                downward_text,
                stability_text,
            ],
        }

    def _build_content_explanations(
        self,
        ppt_match: dict | None,
        score: float,
        breakdown: dict | None,
        transcript_text: str,
        valid: bool,
        invalid_reason: str | None,
        defense_material_mode: str = "with_ppt",
    ) -> dict:
        bd = breakdown if isinstance(breakdown, dict) else {}
        tr = str(transcript_text or "").strip()
        if not valid:
            if defense_material_mode == "without_ppt":
                items = [
                    "本轮为无课件答辩训练，未启用内容匹配模块。",
                    "内容模块本轮未参与评分；系统仍可从语言、仪态、问答等维度给出统一总分与建议。",
                ]
                dq = bd.get("document_quality")
                if dq is not None:
                    items.append(
                        f"课件结构化程度（规则估计，仅供复盘参考）：约 {_to_float(dq, 0.0):.1f} 分；"
                        "本轮未启用课件内容匹配，该估计不参与内容分项计分。"
                    )
                if tr:
                    items.append(
                        f"转写长度约 {len(tr)} 字；本轮未启用课件页面对齐，讲解文本不参与内容匹配计分。"
                    )
                return {
                    "summary": "本轮为无课件答辩训练，未启用内容匹配模块；内容模块本轮未参与评分。",
                    "items": items,
                }

            items = [
                str(invalid_reason or "内容讲解本轮未计分。"),
            ]
            dq = bd.get("document_quality")
            if dq is not None:
                items.append(
                    f"课件结构化程度（规则估计，供复盘）：约 {_to_float(dq, 0.0):.1f} 分；"
                    "接入 MarkItDown/Docling 后该分项会更贴近真实版式。"
                )
            if tr:
                items.append(f"转写长度约 {len(tr)} 字，但若未回传当前页 ppt_match，内容模块仍无法计分。")
            th, oh = bool(bd.get("title_hit")), bool(bd.get("outline_hit"))
            if th or oh:
                items.append(
                    f"转写侧检测到标题/大纲用语命中（title_hit={th}, outline_hit={oh}），"
                    "但因缺少 ppt_match 仍无法纳入内容得分。"
                )
            return {
                "summary": "内容模块无效：缺少当前页 ppt_match，未纳入总分。",
                "items": items,
            }

        match_score = _normalize_percent(bd.get("match_score", ppt_match.get("match_score") if ppt_match else 0))
        keyword_coverage = _normalize_percent(
            bd.get("keyword_coverage", ppt_match.get("keyword_coverage") if ppt_match else 0)
        )
        title_hit = bool(bd.get("title_hit"))
        outline_hit = bool(bd.get("outline_hit"))
        doc_q = _to_float(bd.get("document_quality"), 0.0)

        if match_score >= 75:
            match_text = f"当前页匹配较好，页内匹配分为 {match_score:.1f}。"
        elif match_score >= 50:
            match_text = f"当前页匹配一般，页内匹配分为 {match_score:.1f}。"
        else:
            match_text = f"当前页匹配偏低，页内匹配分为 {match_score:.1f}。"

        if keyword_coverage >= 70:
            coverage_text = f"关键词覆盖较充分，覆盖率为 {keyword_coverage:.1f}%。"
        elif keyword_coverage >= 40:
            coverage_text = f"关键词覆盖一般，覆盖率为 {keyword_coverage:.1f}%。"
        else:
            coverage_text = f"关键词覆盖不足，覆盖率仅为 {keyword_coverage:.1f}%。"

        hit_line = (
            f"标题/大纲命中：当前页标题命中={'是' if title_hit else '否'}，"
            f"大纲或其它页标题命中={'是' if outline_hit else '否'}。"
        )
        doc_line = f"文档结构质量（规则估计）：{doc_q:.1f} 分，用于适度调节内容分。"

        src_items: list[str] = []
        ms = (ppt_match or {}).get("match_source") if isinstance(ppt_match, dict) else None
        if ms == "auto_guess":
            src_items.append(
                "本轮内容对齐来源：自动猜页（规则），在训练页由口述文本推断当前页后参与评分；非手动「选页 + 单页匹配」路径。"
            )
        elif ms == "manual":
            src_items.append("本轮内容对齐来源：手动匹配（选定页面后与讲解文本做单页匹配）。")

        return {
            "summary": f"内容模块得分 {score} 分：综合页内匹配、关键词覆盖、标题/大纲命中与课件结构质量。",
            "items": [
                *src_items,
                f"内容模块得分 {score} 分。",
                match_text,
                coverage_text,
                hit_line,
                doc_line,
            ],
        }

    def _build_qa_explanations(
        self,
        qa_result: dict | None,
        score: float,
        breakdown: dict | None,
        valid: bool,
        invalid_reason: str | None,
    ) -> dict:
        bd = breakdown if isinstance(breakdown, dict) else {}
        if not valid:
            items = [str(invalid_reason or "问答模块本轮未计分。")]
            rr = bd.get("relevance_reason")
            if rr:
                items.append(str(rr))
            wk = bd.get("weak_points") or []
            if isinstance(wk, list) and wk:
                items.append(f"规则弱项摘要：{wk[0]}")
            items.append("完成一次问答并回传 qa_result 后，本项即可参与统一评分。")
            return {
                "summary": "问答模块无效：缺少 qa_result，未纳入总分。",
                "items": items,
            }

        is_relevant = _to_bool(bd.get("is_relevant", qa_result.get("is_relevant") if qa_result else False), False)
        cov_r = _to_float(bd.get("coverage_score"), 0.0)
        if cov_r > 1.0:
            cov_r /= 100.0
        coverage_pct = max(0.0, min(1.0, cov_r)) * 100.0
        hit = int(bd.get("hit_keyword_count", 0))
        miss = int(bd.get("missing_keyword_count", 0))
        alen = int(bd.get("answer_length", 0))
        len_sc = _to_float(bd.get("answer_length_score"), 0.0)
        info_lv = _to_float(bd.get("answer_information_level"), 0.0)
        clr = _to_float(bd.get("clarity_score"), 0.0)
        rr = str(bd.get("relevance_reason") or "")

        rel_line = "回答在规则判断下切题，与问题要点对齐较好。" if is_relevant else "回答在规则判断下切题度不足，与问题要点对齐偏弱。"
        cov_line = f"参考关键词覆盖率约 {coverage_pct:.1f}%，命中 {hit} 个、缺失 {miss} 个。"
        info_line = f"回答长度约 {alen} 字；信息量分约 {info_lv:.1f}，长度折算分约 {len_sc:.1f}。"
        clr_line = f"表达清晰度（规则近似）约 {clr:.1f} 分。"
        rr_line = f"切题依据：{rr}" if rr else ""

        qa_src_items: list[str] = []
        qs = (qa_result or {}).get("qa_source") if isinstance(qa_result, dict) else None
        if qs == "auto_generated":
            qa_src_items.append(
                "本轮问答来源：从「批量规则生成问题」中选定一题后作答并评估；非单页「生成问题」路径。"
            )
        elif qs == "manual":
            qa_src_items.append("本轮问答来源：手动单题（按所选 PPT 页生成的评审问题）。")
        elif qs == "followup_generated":
            qa_src_items.append("本轮问答来自弱点驱动追问。")

        items = [
            *qa_src_items,
            f"问答模块得分 {score} 分（综合切题、关键词、长度与清晰度）。",
            rel_line,
            cov_line,
            info_line,
            clr_line,
        ]
        if rr_line:
            items.append(rr_line)
        cm = str((qa_result or {}).get("comment") or "").strip()
        if cm:
            items.append(f"评估备注摘要：{cm[:160]}{'…' if len(cm) > 160 else ''}")

        return {
            "summary": f"问答模块得分 {score} 分：切题度、关键词覆盖/缺失、回答信息量与清晰度共同决定。",
            "items": items,
        }

    def _build_suggestions(self, modules: dict, defense_material_mode: str = "with_ppt") -> list[SuggestionItem]:
        suggestions = []
        for key in ("language", "posture", "content", "qa"):
            module = modules[key]
            if not module["valid"]:
                if key == "content" and defense_material_mode == "without_ppt":
                    continue
                suggestions.append(SuggestionItem(category=module["label"], content=module["invalid_reason"]))
                continue
            weakest = min(module["components"], key=lambda item: item["score"]) if module["components"] else None
            if weakest is not None and weakest["score"] < weakest["max_score"] * 0.7:
                suggestions.append(
                    SuggestionItem(
                        category=module["label"],
                        content=f"{weakest['name']}偏弱：{weakest['rule']}",
                    )
                )
        if len(suggestions) < 3:
            suggestions.append(SuggestionItem(category="整体", content="建议结合评分解释查看扣分项，优先提升最低分模块。"))
        return suggestions[:4]

    def _build_summary(self, total_score: float, modules: dict) -> dict:
        valid_modules = [module for module in modules.values() if module["valid"]]
        if total_score >= 85:
            overall_comment = "整体表现优秀，关键评分模块较为均衡。"
        elif total_score >= 70:
            overall_comment = "整体表现良好，但仍有可解释的优化空间。"
        else:
            overall_comment = "当前表现仍有较大提升空间，建议先处理最低分模块。"

        if valid_modules:
            strongest = max(valid_modules, key=lambda item: item["score"])
            weakest = min(valid_modules, key=lambda item: item["score"])
            strongest_aspect = f"{strongest['label']}较好"
            weakest_aspect = f"{weakest['label']}需要改进"
            training_tip = strongest["explanations"][0] if weakest["label"] == strongest["label"] else weakest["explanations"][-1]
        else:
            strongest_aspect = "暂无有效评分模块"
            weakest_aspect = "暂无有效评分模块"
            training_tip = "请先完成至少一个有效模块采集，再查看统一评分结果。"

        return {
            "overall_comment": overall_comment,
            "strongest_aspect": strongest_aspect,
            "weakest_aspect": weakest_aspect,
            "training_tip": training_tip,
        }

    def _component(self, name: str, value, max_score: float, score: float, rule: str) -> dict:
        return {
            "name": name,
            "value": value,
            "score": _round_score(score),
            "max_score": max_score,
            "rule": rule,
        }

    def _finalize_module(self, label: str, components: list[dict]) -> dict:
        total = _round_score(sum(item["score"] for item in components))
        explanations = [f"{label}得分 {total}，规则法拆分如下。"]
        for component in components:
            explanations.append(
                f"{component['name']}：{component['score']}/{component['max_score']}，依据：{component['rule']}"
            )
        return {
            "label": label,
            "valid": True,
            "invalid_reason": "",
            "score": total,
            "components": components,
            "explanations": explanations,
        }

    def _invalid_module(self, label: str, reason: str) -> dict:
        return {
            "label": label,
            "valid": False,
            "invalid_reason": reason,
            "score": 0.0,
            "components": [],
            "explanations": [f"{label}未计分：{reason}"],
        }

    def _range_score(self, value: float, ranges: list[tuple[float, float, float]], fallback: float) -> float:
        for lower, upper, score in ranges:
            if lower <= value <= upper:
                return score
        return fallback

    def _ratio_score(self, value: float, thresholds: list[tuple[float, float]], fallback: float) -> float:
        for threshold, score in thresholds:
            if value >= threshold:
                return score
        return fallback

    def _descending_ratio_score(self, value: float, thresholds: list[tuple[float, float]], fallback: float) -> float:
        for threshold, score in thresholds:
            if value <= threshold:
                return score
        return fallback

    def _pause_score(self, pause_count: float, avg_pause_sec: float) -> float:
        if 3 <= pause_count <= 15 and 0.5 <= avg_pause_sec <= 1.5:
            return 30
        if 2 <= pause_count <= 18 and 0.3 <= avg_pause_sec <= 1.8:
            return 22
        if 1 <= pause_count <= 22 and 0.2 <= avg_pause_sec <= 2.2:
            return 14
        return 6

    def _filler_score(self, filler_count: float) -> float:
        if filler_count <= 2:
            return 20
        if filler_count <= 5:
            return 15
        if filler_count <= 8:
            return 10
        return 5

    def _transcript_richness_score(self, transcript_len: int) -> float:
        if transcript_len >= 120:
            return 10
        if transcript_len >= 60:
            return 8
        if transcript_len >= 20:
            return 5
        if transcript_len > 0:
            return 2
        return 0
