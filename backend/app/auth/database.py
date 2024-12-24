from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, Session
import os
from typing import Optional

# 获取项目根目录
BASE_DIR = os.path.dirname(os.path.dirname(os.path.dirname(__file__)))

# 数据库URL
SQLALCHEMY_DATABASE_URL = f"sqlite:///{os.path.join(BASE_DIR, 'auth.db')}"

# 创建数据库引擎
engine = create_engine(
    SQLALCHEMY_DATABASE_URL, connect_args={"check_same_thread": False}
)

# 创建会话工厂
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# 创建基本模型类
Base = declarative_base()

def init_db():
    """初始化数据库"""
    # 导入所有模型以确保它们被注册
    from . import models
    
    # 创建所有表
    Base.metadata.create_all(bind=engine)
    
    # 初始化会话
    db = SessionLocal()
    try:
        # 检查是否需要创建初始管理员用户
        if not db.query(models.User).first():
            print("No users found, database initialized successfully")
    finally:
        db.close()

def get_db():
    """获取数据库会话"""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()