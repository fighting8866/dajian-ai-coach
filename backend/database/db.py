import os
from sqlalchemy import create_engine, text
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker

# 确保data目录存在
DATA_DIR = os.path.join(os.path.dirname(__file__), '..', 'data')
os.makedirs(DATA_DIR, exist_ok=True)

# 数据库文件路径
DB_PATH = os.path.join(DATA_DIR, 'dajian.db')

# 创建数据库引擎
engine = create_engine(
    f'sqlite:///{DB_PATH}',
    connect_args={"check_same_thread": False}
)

# 创建会话工厂
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# 创建基类
Base = declarative_base()

def get_db():
    """获取数据库会话"""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

def init_db():
    """初始化数据库表"""
    # 导入所有模型，确保它们被注册
    from models import session_model, result_model, training_record, user_model
    
    # 创建所有表
    Base.metadata.create_all(bind=engine)

    # 最小兼容迁移：为旧库补充 training_records.ppt_match_json 列
    with engine.connect() as conn:
        columns = conn.execute(text("PRAGMA table_info(training_records)")).fetchall()
        column_names = {row[1] for row in columns}
        if "ppt_match_json" not in column_names:
            conn.execute(text("ALTER TABLE training_records ADD COLUMN ppt_match_json TEXT"))
            conn.commit()
        if "ppt_match_analysis_json" not in column_names:
            conn.execute(text("ALTER TABLE training_records ADD COLUMN ppt_match_analysis_json TEXT"))
            conn.commit()
        if "qa_result_json" not in column_names:
            conn.execute(text("ALTER TABLE training_records ADD COLUMN qa_result_json TEXT"))
            conn.commit()
        if "transcript_text" not in column_names:
            conn.execute(text("ALTER TABLE training_records ADD COLUMN transcript_text TEXT"))
            conn.commit()
        if "audio_metrics_json" not in column_names:
            conn.execute(text("ALTER TABLE training_records ADD COLUMN audio_metrics_json TEXT"))
            conn.commit()
        if "scoring_profile" not in column_names:
            conn.execute(text("ALTER TABLE training_records ADD COLUMN scoring_profile TEXT"))
            conn.commit()
        if "scoring_profile_label" not in column_names:
            conn.execute(text("ALTER TABLE training_records ADD COLUMN scoring_profile_label TEXT"))
            conn.commit()
        if "training_focus" not in column_names:
            conn.execute(text("ALTER TABLE training_records ADD COLUMN training_focus TEXT"))
            conn.commit()
        if "user_id" not in column_names:
            conn.execute(text("ALTER TABLE training_records ADD COLUMN user_id INTEGER"))
            conn.commit()
            print(
                "[db.migrate] training_records: added column user_id (INTEGER NULL)",
                flush=True,
            )
        else:
            print(
                "[db.migrate] training_records: user_id column already present",
                flush=True,
            )

        user_cols = conn.execute(text("PRAGMA table_info(users)")).fetchall()
        user_col_names = {row[1] for row in user_cols}
        if "account_prefs_json" not in user_col_names:
            conn.execute(text("ALTER TABLE users ADD COLUMN account_prefs_json TEXT"))
            conn.commit()
            print(
                "[db.migrate] users: added column account_prefs_json (TEXT NULL) for account preferences / goals",
                flush=True,
            )
        else:
            print(
                "[db.migrate] users: account_prefs_json column already present",
                flush=True,
            )