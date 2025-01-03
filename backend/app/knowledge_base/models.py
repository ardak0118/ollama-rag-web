from sqlalchemy import Column, Integer, String, DateTime, Boolean, ForeignKey
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship
from ..auth.database import Base

class KnowledgeBase(Base):
    __tablename__ = "knowledge_bases"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, unique=True, index=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    is_active = Column(Boolean, default=True)
    
    # 添加关系
    documents = relationship("Document", back_populates="knowledge_base", cascade="all, delete-orphan")
    feedbacks = relationship("Feedback", back_populates="knowledge_base")

class Document(Base):
    __tablename__ = "documents"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String)
    content = Column(String)
    knowledge_base_id = Column(Integer, ForeignKey('knowledge_bases.id', ondelete='CASCADE'))
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    
    # 添加关系
    knowledge_base = relationship("KnowledgeBase", back_populates="documents")