"""应用用户（最小登录体系 V1）"""

from datetime import datetime

from sqlalchemy import Column, DateTime, Integer, String, Text

from database.db import Base


class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, autoincrement=True)
    username = Column(String(64), unique=True, nullable=False, index=True)
    password_hash = Column(String(255), nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    # JSON：默认评分/材料、历史筛选、提示开关、训练目标等（账号级云端同步 V1）
    account_prefs_json = Column(Text, nullable=True)
