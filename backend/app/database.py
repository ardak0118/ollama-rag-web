from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
import os

# 获取项目根目录
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

# 数据库URL
SQLALCHEMY_DATABASE_URL = f"sqlite:///{os.path.join(BASE_DIR, 'app.db')}"

# 创建数据库引擎
engine = create_engine(
    SQLALCHEMY_DATABASE_URL,
    connect_args={"check_same_thread": False}  # SQLite 特定配置
)

# 创建会话工厂
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# 创建基类
Base = declarative_base()

# 获取数据库会话
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

# 初始化数据库
def init_db():
    # 导入所有模型，确保它们被注册
    from .auth import models
    from .feedback.models import Feedback
    from .knowledge_base.models import KnowledgeBase
    
    # 删除所有表（如果存在）
    Base.metadata.drop_all(bind=engine)
    # 创建所有表
    Base.metadata.create_all(bind=engine)
    
    # 初始化会话
    db = SessionLocal()
    try:
        # 检查是否有用户
        if not db.query(models.User).first():
            # 创建默认管理员用户
            admin_user = models.User(
                username="admin",
                email="admin@example.com",
                is_admin=True,
                can_manage_kb=True
            )
            admin_user.set_password("admin")
            db.add(admin_user)
            db.commit()
    finally:
        db.close()