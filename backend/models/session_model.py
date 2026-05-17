from pydantic import BaseModel, Field, AliasChoices
from datetime import datetime
from typing import Optional, Dict, Any, List
from sqlalchemy import Column, String, DateTime
from database.db import Base

class Metrics(BaseModel):
    """训练指标模型"""
    speech_rate: float = 238.0
    pause_count: int = 11
    avg_pause_sec: float = 0.9
    filler_count: int = 4
    forward_gaze_ratio: float = 0.63
    downward_head_ratio: float = 0.18
    posture_stability: float = 0.76

class SessionStartRequest(BaseModel):
    """开始会话请求模型"""
    user_id: str = ""
    session_name: str = ""
    # 本轮专项训练重点（可选）：language | posture | qa | content | none；旧客户端不传则服务端按 none 处理
    training_focus: Optional[str] = None
    # 评分模式：defense=答辩模式，interview=面试模式；未传则默认答辩（见 configs.scoring_profiles）
    # 兼容前端字段名 mode
    scoring_profile: Optional[str] = Field(
        default=None,
        validation_alias=AliasChoices("scoring_profile", "mode"),
    )
    # 材料模式（可选）：与 stop 口径一致，供中断恢复时还原；未传默认 with_ppt
    defense_material_mode: Optional[str] = Field(
        default=None,
        validation_alias=AliasChoices("defense_material_mode", "defenseMaterialMode"),
    )

class SessionStartResponse(BaseModel):
    """开始会话响应模型"""
    session_id: str
    start_time: str
    message: str

class PptMatch(BaseModel):
    """PPT 匹配结果模型"""
    page_index: int
    title: str
    match_score: float
    keyword_coverage: float
    matched_keywords: list[str]
    missing_keywords: list[str]
    comment: str
    match_source: Optional[str] = None


class QaResult(BaseModel):
    """问答评估结果模型"""
    question: str
    expected_keywords: list[str]
    answer_text: str
    is_relevant: bool
    coverage_score: float
    hit_keywords: list[str]
    missing_keywords: list[str]
    comment: str
    # --- V1 规则增强（可选，旧客户端不传亦可）---
    answer_length: Optional[int] = None
    answer_length_score: Optional[float] = None
    answer_keyword_density: Optional[float] = None
    answer_information_level: Optional[float] = None
    relevance_reason: Optional[str] = None
    clarity_score: Optional[float] = None
    followup_candidate_topics: Optional[list[str]] = None
    weak_points: Optional[list[str]] = None
    qa_source: Optional[str] = None
    # 弱点驱动追问链（V2）：可选，仅 followup_generated 时有值
    followup_reason: Optional[str] = None
    followup_target_topic: Optional[str] = None
    # 作答方式：voice=语音转写后评估，text=文本兜底（可选，供结果页展示）
    answer_input_mode: Optional[str] = None
    # 追问轮实际使用的 provider（与 /qa/followup 返回一致；stop 时必须保留供 Result/Report 展示）
    followup_provider_kind: Optional[str] = None
    followup_generation_meta: Optional[Dict[str, Any]] = None
    followup_fallback_to_rule: Optional[bool] = None


class AudioAnalysis(BaseModel):
    """音频分析结果模型"""
    transcript: str
    speech_rate: float
    pause_count: int
    avg_pause_sec: float
    filler_count: int
    audio_valid: Optional[bool] = None
    audio_message: Optional[str] = None


class VisionAnalysis(BaseModel):
    """视觉分析结果模型（第一版真实链路）。"""
    forward_gaze_ratio: Optional[float] = None
    downward_head_ratio: Optional[float] = None
    posture_stability: Optional[float] = None


class PptSlideMatchItem(BaseModel):
    page: int
    score: float
    text_preview: str = ""


class PptMatchAnalysis(BaseModel):
    overall_match_score: float
    slide_matches: list[PptSlideMatchItem] = []
    missed_pages: list[int] = []
    off_topic_segments: list[str] = []


class PptTextSlide(BaseModel):
    page: int
    text: str = ""


class PptTextData(BaseModel):
    full_text: str = ""
    slides: list[PptTextSlide] = []


class SessionStopRequest(BaseModel):
    """停止会话请求模型"""
    session_id: str
    # 可选：供 session.stop 在无 ppt_match 时用转写 + ppt_store 做自动猜页兜底
    ppt_id: Optional[str] = None
    # 讲解阶段口述框文本；音频转写为空时仍可供 stop fallback 猜页（不参与评分公式变更）
    lecture_spoken_text: Optional[str] = None
    metrics: Optional[Metrics] = None
    ppt_match: Optional[PptMatch] = None
    ppt_text_data: Optional[PptTextData] = None
    # 可选：前端课件解析的统一 document（与 /ppt/parse 的 document 对齐，供内容评分结构分项复用）
    content_document: Optional[Dict[str, Any]] = None
    ppt_match_analysis: Optional[PptMatchAnalysis] = None
    qa_result: Optional[QaResult] = None
    # 与嵌套对象中的 match_source / qa_source 一致，便于日志与前端展示
    ppt_match_source: Optional[str] = None
    qa_source: Optional[str] = None
    audio_analysis: Optional[AudioAnalysis] = None
    vision_analysis: Optional[VisionAnalysis] = None
    scoring_profile: Optional[str] = Field(
        default=None,
        validation_alias=AliasChoices("scoring_profile", "mode"),
    )
    # --- 长时会话基线观测（可选；仅日志与排障，不参与评分逻辑）---
    client_audio_blob_bytes: Optional[int] = None
    client_video_blob_bytes: Optional[int] = None
    client_audio_analyze_elapsed_ms: Optional[float] = None
    client_vision_analyze_elapsed_ms: Optional[float] = None
    # V2 追问链快照（可选，供 Result/Report 展示）
    followup_questions_chain: Optional[List[Dict[str, Any]]] = None
    followup_chain_depth: Optional[int] = None
    followup_used: Optional[bool] = None
    selected_followup_reason: Optional[str] = None
    # 材料模式：with_ppt=有课件答辩（内容匹配可参与）；without_ppt=无课件答辩（内容匹配未启用）。旧客户端不传则默认 with_ppt。
    defense_material_mode: Optional[str] = Field(
        default=None,
        validation_alias=AliasChoices("defense_material_mode", "defenseMaterialMode"),
    )
    # 本轮专项训练重点（可选，stop 时优先于 start 时记录；用于结果沉淀）
    training_focus: Optional[str] = None

class SessionStopResponse(BaseModel):
    """停止会话响应模型"""
    session_id: str
    status: str
    message: str


class SessionResumeStatusResponse(BaseModel):
    """GET /session/resume_status：是否可恢复未结束训练（内存会话）。"""

    recoverable: bool = False
    reason: Optional[str] = None
    session_id: Optional[str] = None
    scoring_profile: Optional[str] = None
    training_focus: str = "none"
    defense_material_mode: str = "with_ppt"
    start_time: Optional[str] = None


class SessionAbandonRequest(BaseModel):
    """放弃未结束会话（仅清理内存 sessions，不写结果）。"""

    session_id: str = Field(min_length=1)


class SessionAbandonResponse(BaseModel):
    ok: bool = True
    discarded: bool = False

class SessionRecord(Base):
    """会话记录数据库模型"""
    __tablename__ = "sessions"
    
    session_id = Column(String, primary_key=True, index=True)
    user_id = Column(String)
    session_name = Column(String)
    start_time = Column(DateTime, default=datetime.utcnow)
    end_time = Column(DateTime, nullable=True)
    status = Column(String, default="active")