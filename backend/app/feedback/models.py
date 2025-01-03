from sqlalchemy import Column, Integer, String, DateTime, Text, ForeignKey, LargeBinary
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship
from ..auth.database import Base
from ..auth.models import User
from ..knowledge_base.models import KnowledgeBase

class Feedback(Base):
    __tablename__ = "feedback"

    id = Column(Integer, primary_key=True, index=True)
    type = Column(String, nullable=False)
    content = Column(Text, nullable=False)
    contact = Column(String)
    user_id = Column(Integer, ForeignKey(User.id, ondelete='SET NULL'), nullable=True)
    kb_id = Column(Integer, ForeignKey(KnowledgeBase.id, ondelete='SET NULL'), nullable=True)
    kb_name = Column(String)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    
    # 添加文件相关字段
    file_name = Column(String)  # 文件名
    file_content = Column(LargeBinary)  # 文件内容
    file_type = Column(String)  # 文件MIME类型

    # 关系
    user = relationship(User, backref="feedbacks")
    knowledge_base = relationship(KnowledgeBase, back_populates="feedbacks")

    class Config:
        from_attributes = True