"""
追问 V2 固定回归：质量门禁、去重、评分、hybrid 元数据字段（不发起真实 LLM）。

运行: cd backend && python -m pytest tests/test_followup_v2_cases.py -q
"""

from __future__ import annotations

import pytest

from services.followup_generation_utils import (
    followup_item_quality_score,
    followup_items_valid,
    prepare_model_followup_raw_items,
)
from services.followup_v2_gates import assess_followup_v2_quality, build_weak_point_anchors


def _item(q: str, r: str) -> dict:
    return {"question": q, "reason": r, "source": "qa_weak_point", "target_topic": ""}


def test_quality_score_prefers_interrogative_and_length():
    low = _item("请说明情况", "短")
    hi = _item("你在训练集上准确率很高，但验证集掉得很厉害——这是过拟合吗？怎么缓解？", "盯泛化差距。")
    assert followup_item_quality_score(hi) > followup_item_quality_score(low)


def test_followup_items_valid_rejects_duplicate_reason():
    a = _item("第一个问题是否成立，你依据是什么？", "理由一：与实验设置相关。")
    b = _item("第二个点与第一个是否矛盾，你怎么统一解释？", "理由一：与实验设置相关。")
    assert followup_items_valid([a]) is True
    assert followup_items_valid([a, b]) is False


def test_prepare_skips_invalid_then_keeps_best():
    raw = [
        _item("太短", "x" * 20),
        _item(
            "你提到 dropout——推理期与训练期行为是否一致，权重是否要 scale？",
            "盯推理期与缩放，是常见漏点。",
        ),
    ]
    got = prepare_model_followup_raw_items(raw, max_items=2)
    assert got is not None and len(got) == 1
    assert "dropout" in got[0]["question"] or "scale" in got[0]["question"]


def test_v2_gate_duplicate_pair():
    qa = {"weak_points": ["a"], "missing_keywords": [], "followup_candidate_topics": []}
    w = build_weak_point_anchors(qa_result=qa)
    it = [
        _item("你是否考虑过过拟合与泛化之间的折中问题呢？", "r1" * 5),
        _item("你是否考虑过过拟合与泛化之间的折中问题呢？", "r2" * 5),
    ]
    ok, code, _ = assess_followup_v2_quality(
        it, weak_only_anchors=w, current_question="x", current_answer="y"
    )
    assert not ok and code == "duplicate"


def test_v2_gate_weak_miss():
    qa = {"weak_points": ["过拟合"], "missing_keywords": ["验证集"], "followup_candidate_topics": []}
    w = build_weak_point_anchors(qa_result=qa)
    it = [_item("你认为未来 AI 会改变世界吗？", "与现场无关的泛问。")]
    ok, code, _ = assess_followup_v2_quality(
        it, weak_only_anchors=w, current_question="评估指标", current_answer="用准确率"
    )
    assert not ok and code == "weak_point_miss"


def test_v2_gate_ok_with_anchor():
    qa = {"weak_points": ["scale"], "missing_keywords": [], "followup_candidate_topics": []}
    w = build_weak_point_anchors(qa_result=qa)
    it = [
        _item(
            "你说用 dropout，那推理时是否保留同样比例，权重是否按 1-p 做 scale？",
            "盯你答里没提 scale。",
        )
    ]
    ok, code, dbg = assess_followup_v2_quality(
        it, weak_only_anchors=w, current_question="dropout 作用", current_answer="随机失活"
    )
    assert ok and code == "ok"
    assert dbg["per_item"][0].get("weak_hits_in_question")


@pytest.mark.parametrize(
    "bad_q,expect",
    [
        ("x" * 400 + "吗？", "too_long"),
    ],
)
def test_v2_length_gate(bad_q: str, expect: str):
    qa = {"weak_points": ["k"], "missing_keywords": [], "followup_candidate_topics": []}
    w = build_weak_point_anchors(qa_result=qa)
    ok, code, _ = assess_followup_v2_quality(
        [_item(bad_q, "reason" * 3)], weak_only_anchors=w, current_question="q", current_answer="a"
    )
    assert not ok
    assert code == expect
