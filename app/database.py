from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker

import os

# 数据库文件路径
# 优先使用环境变量 (Docker 环境), 否则使用本地路径 (开发环境)
# 本地开发时，数据库文件位于 app/../data/nutrition.db
if os.getenv("DATABASE_URL"):
    SQLALCHEMY_DATABASE_URL = os.getenv("DATABASE_URL")
else:
    # 获取当前文件 (database.py) 的目录
    BASE_DIR = os.path.dirname(os.path.abspath(__file__))
    # 这里假设数据目录在 app 的同级目录 data 下
    DB_PATH = os.path.join(os.path.dirname(BASE_DIR), "data", "nutrition.db")
    SQLALCHEMY_DATABASE_URL = f"sqlite:///{DB_PATH}"

# 创建数据库引擎
# check_same_thread=False 是 SQLite 必须的配置，因为 FastAPI 是多线程的
engine = create_engine(
    SQLALCHEMY_DATABASE_URL, connect_args={"check_same_thread": False}
)

# 创建会话工厂
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# 创建基类
Base = declarative_base()

# 获取数据库会话的依赖函数
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
