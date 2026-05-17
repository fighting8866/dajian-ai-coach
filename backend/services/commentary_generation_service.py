"""
老师点评生成：按 COMMENTARY_PROVIDER 分发 rule | model | hybrid，并与 question/followup provider 元数据合并。
"""

from __future__ import annotations

from typing import Any

from factories.provider_factory import (
    get_commentary_generation_provider_kind,
    get_followup_generation_provider_kind,
    get_question_generation_provider_kind,
)
from services.generation_common import build_generation_meta, normalize_generation_provider_kind
from services.hybrid_commentary_provider import generate_hybrid_commentary_bundle
from services.model_commentary_provider import generate_model_commentary_bundle
from services.rule_commentary_provider import generate_rule_commentary_bundle
from services.commentary_generation_utils import normalize_commentary_core_fields


def _norm_training_focus_out(raw: Any) -> str:
    s = str(raw or "").strip().lower()
    if s in ("language", "posture", "qa", "content"):
        return s
    return "none"


_FOCUS_FULL_CN = {
    "language": "语言表达专项",
    "posture": "仪态表现专项",
    "qa": "问答表现专项",
    "content": "内容讲解专项",
}

_FOCUS_ANCHOR_HINT = {
    "language": "语言专项下可优先关注语速是否清楚、停顿节奏是否自然、口头禅是否偏多。",
    "posture": "仪态专项下可优先关注正视比例、低头率与镜头前稳定度。",
    "qa": "问答专项下可优先关注是否切题、要点覆盖、表达清晰度与回答篇幅。",
    "content": "内容专项下可优先关注页内匹配、关键词覆盖与标题/大纲线索是否对齐。",
}


def _focus_vs_bridge_sentence(vs: str, trend_kind: str) -> str:
    vs_l = str(vs or "").strip()
    chunks: list[str] = []
    if trend_kind == "volatile":
        chunks.append("最近同专项起伏仍偏明显，建议先把发挥稳住，再追求上限。")
    if "较上次同专项有提升" in vs_l or (
        "提升" in vs_l and "回落" not in vs_l and "波动较大" not in vs_l
    ):
        chunks.append("较上次同专项已有可见提升，但仍要把优势巩固住，避免状态掉下去。")
    elif "有所回落" in vs_l or ("回落" in vs_l and "提升" not in vs_l):
        chunks.append("相较上次同专项有所回落，建议对照反馈把关键环节补回来。")
    elif "基本持平" in vs_l:
        chunks.append("与上次同专项相比大致持平，更适合做精细化打磨。")
    elif "波动较大" in vs_l and trend_kind != "volatile":
        chunks.append("同专项纵向波动仍偏明显。")
    elif not vs_l or "暂无足够" in vs_l:
        if not chunks:
            chunks.append("同专项纵向对比数据还不多，建议多完成几次同专项训练再下结论。")
    elif not chunks:
        chunks.append("请结合本次专项核心分与关键指标变化把握练习方向。")
    return " ".join(chunks).strip()


def _focus_metric_bridge(metric_line: str, highlights: list[str]) -> str:
    ml = str(metric_line or "").strip()
    if ml and "暂无足够" not in ml:
        return f"关键指标对比：{ml}"
    if highlights:
        h0 = str(highlights[0]).strip()
        if h0:
            return f"关键指标侧写：{h0}"
    return ""


def apply_training_focus_commentary_overlay(payload: dict[str, Any]) -> None:
    """
    专项训练点评联动 V1：在已有 overall / strengths / weaknesses / advice 上叠加专项语境（规则版）。
    依赖 payload 内已由 result.api 写入的 training_focus_* / focus_trend_kind 等字段。
    """
    if not isinstance(payload, dict):
        return
    if not payload.get("training_valid", True):
        return
    focus = _norm_training_focus_out(payload.get("training_focus"))
    if focus == "none":
        return

    full = _FOCUS_FULL_CN.get(focus, "本专项")
    primary = payload.get("training_focus_primary_score")
    prim_txt = ""
    if primary is not None:
        try:
            prim_txt = f"本专项核心分约 {float(primary):.1f} 分。"
        except (TypeError, ValueError):
            prim_txt = ""

    vs = str(payload.get("training_focus_vs_recent") or "").strip()
    trend_kind = str(payload.get("focus_trend_kind") or "").strip().lower()
    metric_line = str(payload.get("training_focus_metric_compare") or "").strip()
    hil = payload.get("training_focus_metric_highlights")
    highlights: list[str] = []
    if isinstance(hil, list):
        highlights = [str(x).strip() for x in hil if str(x).strip()][:2]

    bridge = _focus_vs_bridge_sentence(vs, trend_kind)
    metric_br = _focus_metric_bridge(metric_line, highlights)
    hint = _FOCUS_ANCHOR_HINT.get(focus, "")

    lead_parts = [f"本轮为「{full}」训练。", prim_txt, bridge, metric_br, hint]
    focus_lead = " ".join(p for p in lead_parts if p).strip()
    if not focus_lead:
        return

    old_oc = str(payload.get("overall_commentary") or "").strip()
    merged_oc = f"{focus_lead}\n\n{old_oc}".strip() if old_oc else focus_lead

    st0: list[str] = []
    wk0: list[str] = []
    adv0: list[str] = []

    if vs and "无提升" not in vs and "提升" in vs and "回落" not in vs:
        st0.append(f"「{full}」视角：与最近同专项相比，整体方向更偏积极，值得延续当前练习节奏。")
    if trend_kind == "up" and not st0:
        st0.append(f"「{full}」视角：同专项核心分呈上升趋势，说明练习在起作用。")

    if trend_kind == "volatile" or "波动较大" in vs:
        wk0.append(
            f"「{full}」视角：专项表现仍不够稳定，容易出现状态起伏，建议把「稳」放在优先级更高的位置。"
        )
    elif vs and "回落" in vs:
        wk0.append(f"「{full}」视角：相较上次同专项有所回落，需要逐项对照反馈收紧。")

    if focus == "language" and (trend_kind == "volatile" or (vs and "回落" in vs)):
        wk0.append("「语言表达」仍要留意语速、停顿与口头禅对听感的影响。")
    if focus == "posture" and (trend_kind == "volatile" or (vs and "回落" in vs)):
        wk0.append("「仪态表现」仍要留意正视比例、低头率与镜头前稳定度。")
    if focus == "qa" and (trend_kind == "volatile" or (vs and "回落" in vs)):
        wk0.append("「问答表现」仍要留意切题度、要点覆盖与表达清晰度。")
    if focus == "content" and (trend_kind == "volatile" or (vs and "回落" in vs)):
        wk0.append("「内容讲解」仍要留意页内匹配、关键词覆盖与结构线索对齐。")

    next_hint = str(
        payload.get("training_focus_next_action_label") or payload.get("training_focus_next_hint") or ""
    ).strip()
    if next_hint:
        adv0.append(f"专项训练安排：{next_hint}")

    def _merge_lists(prefix: list[str], original: Any) -> list[str]:
        tail = original if isinstance(original, list) else []
        out: list[str] = []
        seen: set[str] = set()
        for block in (prefix, tail):
            for x in block:
                line = str(x or "").strip()
                if not line:
                    continue
                key = line[:52]
                if key in seen:
                    continue
                seen.add(key)
                out.append(line)
        return out

    payload["overall_commentary"] = merged_oc
    payload["strengths"] = _merge_lists(st0, payload.get("strengths"))
    payload["weaknesses"] = _merge_lists(wk0, payload.get("weaknesses"))
    payload["next_round_advice"] = _merge_lists(adv0, payload.get("next_round_advice"))

    if not payload.get("strengths"):
        payload["strengths"] = [
            f"「{full}」训练视角：建议把本专项的进步拆成可验收的小目标，便于持续强化。",
        ]
    if not payload.get("weaknesses"):
        payload["weaknesses"] = [
            f"「{full}」训练视角：请优先处理对专项得分影响最大的 1～2 个薄弱点。",
        ]
    if not payload.get("next_round_advice"):
        payload["next_round_advice"] = (
            [f"专项训练安排：{next_hint}"]
            if next_hint
            else ["下一轮先明确本专项的练习重点，再对照本次反馈逐项过关。"]
        )

    norm = normalize_commentary_core_fields(
        {
            "overall_commentary": payload.get("overall_commentary"),
            "strengths": payload.get("strengths"),
            "weaknesses": payload.get("weaknesses"),
            "next_round_advice": payload.get("next_round_advice"),
            "coach_commentary": payload.get("coach_commentary"),
            "improvement_advice": payload.get("improvement_advice"),
        }
    )
    for k in (
        "overall_commentary",
        "strengths",
        "weaknesses",
        "next_round_advice",
        "coach_commentary",
        "improvement_advice",
    ):
        if k in norm:
            payload[k] = norm[k]

    print(
        f"[commentary.focus] training_focus={focus!r} summary={focus_lead[:200]!r} "
        f"next_action={next_hint[:160]!r}",
        flush=True,
    )


def merge_generation_providers_into_metadata(
    meta: dict | None,
    *,
    question_kind: str,
    followup_kind: str,
    commentary_kind: str,
) -> dict[str, Any]:
    m: dict[str, Any] = dict(meta or {})
    qk = normalize_generation_provider_kind(question_kind)
    fk = normalize_generation_provider_kind(followup_kind)
    ck = normalize_generation_provider_kind(commentary_kind)
    m["question_provider_kind"] = qk
    m["followup_provider_kind"] = fk
    m["commentary_provider_kind"] = ck
    m["generation_providers"] = {
        "question": build_generation_meta("question", qk),
        "followup": build_generation_meta("followup", fk),
        "commentary": build_generation_meta("commentary", ck),
    }
    return m


def generate_coach_bundle(**kw: Any) -> dict[str, Any]:
    q_conf = normalize_generation_provider_kind(get_question_generation_provider_kind())
    f_conf = normalize_generation_provider_kind(get_followup_generation_provider_kind())
    c_conf = normalize_generation_provider_kind(get_commentary_generation_provider_kind())

    if c_conf == "rule":
        bundle, _c_extra = generate_rule_commentary_bundle(**kw)
    elif c_conf == "model":
        bundle, _c_extra = generate_model_commentary_bundle(**kw)
    else:
        bundle, _c_extra = generate_hybrid_commentary_bundle(**kw)

    meta = merge_generation_providers_into_metadata(
        bundle.get("coach_metadata"),
        question_kind=q_conf,
        followup_kind=f_conf,
        commentary_kind=c_conf,
    )
    exec_meta = bundle.get("commentary_generation_meta")
    if isinstance(exec_meta, dict):
        meta["commentary_generation_meta"] = exec_meta
    if bundle.get("commentary_fallback_to_rule") is not None:
        meta["commentary_fallback_to_rule"] = bool(bundle.get("commentary_fallback_to_rule"))

    bundle["coach_metadata"] = meta
    bundle["followup_provider_kind"] = f_conf
    bundle["commentary_provider_kind"] = c_conf
    if not isinstance(bundle.get("commentary_generation_meta"), dict):
        bundle["commentary_generation_meta"] = meta.get("commentary_generation_meta") or {}
    if bundle.get("commentary_fallback_to_rule") is None and meta.get("commentary_fallback_to_rule") is not None:
        bundle["commentary_fallback_to_rule"] = bool(meta.get("commentary_fallback_to_rule"))
    return bundle


def finalize_coach_bundle_providers(bundle: dict[str, Any], *, qa_result: dict | None) -> dict[str, Any]:
    """合并会话内已落库的提问侧 provider，并统一顶层字段。"""
    qk_stored = None
    fk_stored = None
    fgm_stored = None
    if isinstance(qa_result, dict):
        qk_stored = qa_result.get("question_provider_kind")
        fk_stored = qa_result.get("followup_provider_kind")
        fgm_stored = qa_result.get("followup_generation_meta")
    qk = normalize_generation_provider_kind(
        qk_stored or get_question_generation_provider_kind()
    )
    fk = normalize_generation_provider_kind(
        fk_stored or bundle.get("followup_provider_kind") or get_followup_generation_provider_kind()
    )
    ck = normalize_generation_provider_kind(
        bundle.get("commentary_provider_kind") or get_commentary_generation_provider_kind()
    )
    meta = merge_generation_providers_into_metadata(
        bundle.get("coach_metadata"),
        question_kind=qk,
        followup_kind=fk,
        commentary_kind=ck,
    )
    # 追问：以本轮 qa_result 中落库的 meta 为准（含 model 真实标签），覆盖骨架「预留」文案
    if isinstance(fgm_stored, dict) and fgm_stored:
        gps = meta.get("generation_providers")
        if isinstance(gps, dict):
            fu = gps.get("followup")
            if isinstance(fu, dict):
                nu = {**fu}
                for k in ("provider_kind", "provider_label", "generation_mode", "capability", "version"):
                    if fgm_stored.get(k) is not None:
                        nu[k] = fgm_stored.get(k)
                gps = {**gps, "followup": nu}
                meta["generation_providers"] = gps
    if isinstance(bundle.get("commentary_generation_meta"), dict):
        meta["commentary_generation_meta"] = bundle["commentary_generation_meta"]
    if bundle.get("commentary_fallback_to_rule") is not None:
        meta["commentary_fallback_to_rule"] = bool(bundle.get("commentary_fallback_to_rule"))
    out = {
        **bundle,
        "coach_metadata": meta,
        "question_provider_kind": qk,
        "followup_provider_kind": fk,
        "commentary_provider_kind": ck,
    }
    if not isinstance(out.get("commentary_generation_meta"), dict) or not out.get("commentary_generation_meta"):
        if isinstance(meta.get("commentary_generation_meta"), dict):
            out["commentary_generation_meta"] = meta["commentary_generation_meta"]
    if out.get("commentary_fallback_to_rule") is None and meta.get("commentary_fallback_to_rule") is not None:
        out["commentary_fallback_to_rule"] = bool(meta["commentary_fallback_to_rule"])
    return out
