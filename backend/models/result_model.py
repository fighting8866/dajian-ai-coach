from pydantic import BaseModel, Field
from typing import Dict, List, Any, Optional, Union
from sqlalchemy import Column, String, Float, Text
from database.db import Base

class MetricItem(BaseModel):
    """指标项模型"""
    name: str
    value: Union[str, float, int]
    unit: str = ""
    description: Optional[str] = None
    score: Optional[float] = None

class SuggestionItem(BaseModel):
    """建议项模型"""
    category: str
    content: str


class PptMatchItem(BaseModel):
    """PPT 匹配结果模型"""
    page_index: int
    title: str
    match_score: float
    keyword_coverage: float
    matched_keywords: List[str]
    missing_keywords: List[str]
    comment: str


class QaResultItem(BaseModel):
    """问答评估结果模型"""
    question: str
    expected_keywords: List[str]
    answer_text: str
    is_relevant: bool
    coverage_score: float
    hit_keywords: List[str]
    missing_keywords: List[str]
    comment: str


class PptSlideMatchItem(BaseModel):
    page: int
    score: float
    text_preview: str = ""


class PptMatchAnalysisItem(BaseModel):
    overall_match_score: float
    slide_matches: List[PptSlideMatchItem] = []
    missed_pages: List[int] = []
    off_topic_segments: List[str] = []


class ResultResponse(BaseModel):
    """结果响应模型"""
    session_id: str
    total_score: float
    language_score: float
    posture_score: float
    scoring_profile: Optional[str] = None
    scoring_profile_label: Optional[str] = None
    metrics: List[MetricItem]
    suggestions: List[SuggestionItem]
    summary: Optional[Dict[str, Any]] = None
    ppt_match: Optional[PptMatchItem] = None
    ppt_match_analysis: Optional[PptMatchAnalysisItem] = None
    qa_result: Optional[QaResultItem] = None
    transcript: Optional[str] = None
    audio_metrics: Optional[Dict[str, Any]] = None

class HistoryItem(BaseModel):
    """历史记录项模型"""
    session_id: str
    session_name: str
    timestamp: str
    created_at: Optional[str] = None
    total_score: float
    language_score: Optional[float] = None
    posture_score: Optional[float] = None
    content_score: Optional[float] = None
    qa_score: Optional[float] = None
    scoring_profile: Optional[str] = None
    scoring_profile_label: Optional[str] = None
    # with_ppt | without_ppt，来自 metrics_json / 内存结果；无则 None
    defense_material_mode: Optional[str] = None
    audio_valid: Optional[bool] = None
    vision_valid: Optional[bool] = None
    # 本轮实际训练重点（language | posture | qa | content | none），缺省为 none 便于前端展示
    training_focus: str = "none"
    # 专项训练成效回看 V1（规则统计，仅 training_focus != none 时有意义）
    focus_trend_summary: Optional[str] = None
    focus_recent_scores: Optional[List[Dict[str, Any]]] = None
    # none | insufficient | up | flat | volatile
    focus_trend_kind: Optional[str] = None
    # 专项训练结果解释联动 V1（与 Result 规则一致；历史列表无 recommended 时 switch 较少触发）
    training_focus_summary: Optional[str] = None
    training_focus_primary_score: Optional[float] = None
    training_focus_vs_recent: Optional[str] = None
    training_focus_next_action: Optional[str] = None
    training_focus_next_hint: Optional[str] = None
    training_focus_next_action_label: Optional[str] = None
    # History 专项筛选与同专项对比 V1（轻量字段；training_focus == none 时为 None）
    focus_primary_score: Optional[float] = None
    focus_vs_previous: Optional[str] = None
    # 专项关键指标对比 V1：历史列表仅rollup；详情见 Result / Report
    focus_key_metrics_vs_previous: Optional[str] = None
    # 无效训练记录收口 V1：是否为有效训练；无效时 invalid_reason_summary 为简短原因
    training_valid: bool = True
    invalid_reason_summary: Optional[str] = None


class ValidTrainingOverview(BaseModel):
    """历史页有效训练总览 V1（仅规则汇总，基于 training_valid=true）。"""

    overview_ready: bool = False
    overview_message: Optional[str] = None
    valid_count_recent: int = 0
    recent_window_size: int = 7
    avg_total_score_recent: Optional[float] = None
    latest_valid_training_focus: Optional[str] = None
    latest_valid_session_id: Optional[str] = None
    latest_valid_created_at: Optional[str] = None
    latest_valid_total_score: Optional[float] = None
    latest_valid_scoring_profile: Optional[str] = None
    latest_valid_defense_material_mode: Optional[str] = None
    focus_distribution_recent: Dict[str, int] = Field(default_factory=dict)
    recommended_continue_focus: Optional[str] = None


class HistoryDeleteOneResponse(BaseModel):
    """删除单条历史训练记录 V1"""

    ok: bool = True
    session_id: str
    had_db_record: bool = False
    removed_results: bool = False
    removed_sessions: bool = False


class HistoryClearInvalidResponse(BaseModel):
    """批量清理无效训练记录 V1（仅 training_valid=false）"""

    ok: bool = True
    deleted_count: int = 0
    session_ids: List[str] = Field(default_factory=list)


class HistoryResponse(BaseModel):
    """历史记录响应模型"""
    history: List[HistoryItem]
    # 历史页专项复盘收口 V1：仅当请求带 review_focus=language|posture|qa|content 时填充
    focus_review_summary: Optional[str] = None
    focus_review_scores: Optional[List[float]] = None
    focus_review_trend: Optional[str] = None
    focus_review_next_action: Optional[str] = None
    # 历史页有效训练总览 V1
    valid_training_overview: Optional[ValidTrainingOverview] = None

class ResultRecord(Base):
    """结果记录数据库模型"""
    __tablename__ = "results"
    
    session_id = Column(String, primary_key=True, index=True)
    total_score = Column(Float)
    language_score = Column(Float)
    posture_score = Column(Float)
    metrics = Column(Text)  # JSON字符串
    suggestions = Column(Text)  # JSON字符串
    timestamp = Column(String)