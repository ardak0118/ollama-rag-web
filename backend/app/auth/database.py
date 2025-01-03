from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, Session
import os
from typing import Optional
import logging

logger = logging.getLogger(__name__)

# 获取项目根目录
BASE_DIR = os.path.dirname(os.path.dirname(os.path.dirname(__file__)))

# 数据库URL
SQLALCHEMY_DATABASE_URL = f"sqlite:///{os.path.join(BASE_DIR, 'app.db')}"

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
    try:
        # 导入所有模型以确保它们被注册
        from ..auth.models import User
        from ..knowledge_base.models import KnowledgeBase
        from ..feedback.models import Feedback
        
        # 删除所有表（如果存在）
        Base.metadata.drop_all(bind=engine)
        
        # 按正确的顺序创建表
        # 1. 先创建不依赖其他表的基础表
        tables = [
            User.__table__,
            KnowledgeBase.__table__
        ]
        Base.metadata.create_all(bind=engine, tables=tables)
        
        # 2. 创建依赖其他表的表
        tables = [
            Feedback.__table__
        ]
        Base.metadata.create_all(bind=engine, tables=tables)
        
        # 初始化会话
        db = SessionLocal()
        try:
            # 检查是否有用户
            if not db.query(User).first():
                # 创建默认管理员用户
                admin_user = User(
                    username="admin",
                    email="admin@example.com",
                    is_admin=True,
                    can_manage_kb=True
                )
                admin_user.set_password("admin")
                db.add(admin_user)
                db.commit()
                
                logger.info("Created default admin user")
        except Exception as e:
            logger.error(f"Error creating admin user: {e}")
            db.rollback()
            raise
        finally:
            db.close()
            
    except Exception as e:
        logger.error(f"Error initializing database: {e}")
        raise

def get_db():
    """获取数据库会话"""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()