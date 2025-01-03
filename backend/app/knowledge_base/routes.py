from fastapi import APIRouter, HTTPException, Depends, UploadFile, File, Form, status
from sqlalchemy.orm import Session
from pydantic import BaseModel
from ..auth.database import get_db
from ..auth.routes import get_current_user
from ..auth.permissions import check_permissions
from ..auth.models import User
from .models import KnowledgeBase, Document
from . import schemas
from ..pdf_processor import pdf_processor
import logging
import os
from typing import Optional

kb_router = APIRouter()
logger = logging.getLogger(__name__)

# 修改路由前缀
@kb_router.get("/knowledge-base")
async def list_knowledge_bases(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """获取知识库列表"""
    try:
        query = db.query(KnowledgeBase)
        if not current_user.is_admin:
            # 非管理员只能看到激活的知识库
            query = query.filter(KnowledgeBase.is_active == True)
            
        kbs = query.all()
        
        return [{
            "id": kb.id,
            "name": kb.name,
            "created_at": kb.created_at,
            "is_active": kb.is_active,
            "document_count": len(kb.documents)
        } for kb in kbs]
        
    except Exception as e:
        logger.error(f"Error listing knowledge bases: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )

def check_kb_permission(user: User):
    """检查用户是否有知识库管理权限"""
    if not (user.is_admin or user.can_manage_kb):
        raise HTTPException(
            status_code=403,
            detail="您没有权限管理知识库"
        )

# 添加 Pydantic 模型
class KnowledgeBaseCreate(BaseModel):
    name: str

    class Config:
        orm_mode = True

@kb_router.post("/knowledge-base")
async def create_knowledge_base(
    name: str = Form(...),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """创建知识库"""
    if not current_user.is_admin and not current_user.can_manage_kb:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="No permission to create knowledge base"
        )
        
    try:
        kb = KnowledgeBase(name=name)
        db.add(kb)
        db.commit()
        db.refresh(kb)
        
        return {
            "id": kb.id,
            "name": kb.name,
            "created_at": kb.created_at
        }
        
    except Exception as e:
        logger.error(f"Error creating knowledge base: {str(e)}")
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )

@kb_router.post("/knowledge-base/{kb_id}/upload")
async def upload_document(
    kb_id: int,
    file: UploadFile = File(...),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """上传文档到知识库"""
    logger.info(f"Received upload request for kb_id: {kb_id}")
    logger.info(f"File info: name={file.filename}, content_type={file.content_type}")

    try:
        # 检查知识库是否存在
        kb = db.query(KnowledgeBase).filter(KnowledgeBase.id == kb_id).first()
        if not kb:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Knowledge base {kb_id} not found"
            )
            
        # 检查权限
        if not current_user.is_admin and not current_user.can_manage_kb:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="No permission to upload documents"
            )
            
        # 检查文件类型
        allowed_types = ['.txt', '.pdf', '.md', '.doc', '.docx']
        file_ext = os.path.splitext(file.filename)[1].lower()
        if file_ext not in allowed_types:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"File type not allowed. Allowed types: {', '.join(allowed_types)}"
            )
            
        # 读取文件内容
        content = await file.read()
        
        # 处理文件内容
        if file_ext == '.pdf':
            # PDF 处理
            text_content = await pdf_processor.process_pdf(content)
        else:
            # 假设是文本文件
            try:
                text_content = content.decode('utf-8')
            except UnicodeDecodeError:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="File encoding not supported"
                )
            
        # 创建文档记录
        document = Document(
            name=file.filename,
            content=text_content,
            knowledge_base_id=kb_id
        )
        
        db.add(document)
        db.commit()
        db.refresh(document)
        
        logger.info(f"Document created: id={document.id}")
        
        return {
            "message": "Document uploaded successfully",
            "document_id": document.id
        }
        
    except HTTPException as e:
        logger.error(f"HTTP error during upload: {str(e)}")
        raise
    except Exception as e:
        logger.error(f"Error uploading document: {str(e)}")
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error uploading document: {str(e)}"
        )

@kb_router.get("/knowledge-base/{kb_id}/documents")
async def list_documents(
    kb_id: int,
    current_user: User = Depends(check_permissions(["doc:view"])),
    db: Session = Depends(get_db)
):
    """获取知识库下的文档列表"""
    try:
        docs = db.query(Document).filter(Document.knowledge_base_id == kb_id).all()
        return docs
    except Exception as e:
        logger.error(f"Error listing documents: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"Error listing documents: {str(e)}"
        )

@kb_router.get("/knowledge-base/{kb_id}")
async def get_knowledge_base(
    kb_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """获取知识库详情"""
    try:
        # 获取知识库信息
        kb = db.query(KnowledgeBase).filter(KnowledgeBase.id == kb_id).first()
        if not kb:
            raise HTTPException(
                status_code=404,
                detail="Knowledge base not found"
            )
            
        # 获取该知识库下的所有文档
        documents = db.query(Document)\
            .filter(Document.knowledge_base_id == kb_id)\
            .order_by(Document.created_at.desc())\
            .all()
            
        # 构建响应
        return {
            "id": kb.id,
            "name": kb.name,
            "created_at": kb.created_at,
            "documents": [{
                "id": doc.id,
                "name": doc.name,
                "content": doc.content,
                "created_at": doc.created_at
            } for doc in documents]
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting knowledge base: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"Error getting knowledge base: {str(e)}"
        )