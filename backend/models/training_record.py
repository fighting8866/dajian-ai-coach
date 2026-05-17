from sqlalchemy import Column, String, Float, Text, Integer
from database.db import Base

class TrainingRecord(Base):
    """训练记录数据库模型"""
    __tablename__ = "training_records"
    
    session_id = Column(String, primary_key=True, index=True)
    # 归属用户（可空：旧数据）；新写入必须带当前登录用户 id
    user_id = Column(Integer, nullable=True, index=True)
    session_name = Column(String)
    start_time = Column(String)
    end_time = Column(String, nullable=True)
    status = Column(String)
    total_score = Column(Float, nullable=True)
    language_score = Column(Float, nullable=True)
    posture_score = Column(Float, nullable=True)
    metrics_json = Column(Text, nullable=True)  # JSON字符串
    suggestions_json = Column(Text, nullable=True)  # JSON字符串
    ppt_match_json = Column(Text, nullable=True)  # JSON字符串
    ppt_match_analysis_json = Column(Text, nullable=True)  # JSON字符串
    qa_result_json = Column(Text, nullable=True)  # JSON字符串
    transcript_text = Column(Text, nullable=True)  # 转写文本
    audio_metrics_json = Column(Text, nullable=True)  # 音频语言指标JSON
    created_at = Column(String)
    scoring_profile = Column(String, nullable=True)
    scoring_profile_label = Column(String, nullable=True)
    # 本轮实际专项：language | posture | qa | content | none（与 session / metrics_json 一致）
    training_focus = Column(String, nullable=True)