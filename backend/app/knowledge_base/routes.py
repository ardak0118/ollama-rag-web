from fastapi import APIRouter, HTTPException, Depends, UploadFile, File, status
from sqlalchemy.orm import Session
from ..auth.database import get_db
from ..auth.routes import get_current_user
from ..auth.permissions import check_permissions
from ..auth.models import User
from .models import KnowledgeBase, Document
from . import schemas
import logging
import os
from typing import Optional

kb_router = APIRouter()
logger = logging.getLogger(__name__)

# 确保上传目录存在
UPLOAD_DIR = "uploads"
os.makedirs(UPLOAD_DIR, exist_ok=True)

@kb_router.get("/knowledge-bases")
async def list_knowledge_bases(
    current_user: User = Depends(check_permissions(["kb:view"])),
    db: Session = Depends(get_db)
):
    """获取知识库列表"""
    try:
        kbs = db.query(KnowledgeBase).all()
        logger.info(f"Found {len(kbs)} knowledge bases")
        return kbs
    except Exception as e:
        logger.error(f"Error listing knowledge bases: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"Error listing knowledge bases: {str(e)}"
        )

@kb_router.get("/knowledge-bases/{kb_id}")
async def get_knowledge_base(
    kb_id: int,
    current_user: User = Depends(check_permissions(["kb:view"])),
    db: Session = Depends(get_db)
):
    """获取知识库详情"""
    kb = db.query(KnowledgeBase).filter(KnowledgeBase.id == kb_id).first()
    if not kb:
        raise HTTPException(status_code=404, detail="Knowledge base not found")
    return kb

@kb_router.post("/knowledge-bases")
async def create_knowledge_base(
    kb: schemas.KnowledgeBaseCreate,
    current_user: User = Depends(check_permissions(["kb:manage"])),
    db: Session = Depends(get_db)
):
    """创建知识库"""
    try:
        db_kb = KnowledgeBase(**kb.dict())
        db.add(db_kb)
        db.commit()
        db.refresh(db_kb)
        logger.info(f"Created knowledge base: {db_kb.id}")
        return db_kb
    except Exception as e:
        logger.error(f"Error creating knowledge base: {str(e)}")
        db.rollback()
        raise HTTPException(
            status_code=500,
            detail=f"Error creating knowledge base: {str(e)}"
        )

@kb_router.get("/knowledge-bases/{kb_id}/documents")
async def list_documents(
    kb_id: int,
    current_user: User = Depends(check_permissions(["doc:view"])),
    db: Session = Depends(get_db)
):
    """获取知识库下的文档��表"""
    try:
        docs = db.query(Document).filter(Document.knowledge_base_id == kb_id).all()
        return docs
    except Exception as e:
        logger.error(f"Error listing documents: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"Error listing documents: {str(e)}"
        )

@kb_router.post("/knowledge-bases/{kb_id}/documents")
async def upload_document(
    kb_id: int,
    file: UploadFile = File(...),
    current_user: User = Depends(check_permissions(["doc:manage"])),
    db: Session = Depends(get_db)
):
    """上传文档到知识库"""
    try:
        # 检查知识库是否存在
        kb = db.query(KnowledgeBase).filter(KnowledgeBase.id == kb_id).first()
        if not kb:
            raise HTTPException(status_code=404, detail="Knowledge base not found")

        logger.info(f"Processing file upload: {file.filename}")
        
        # 处理文件上传
        try:
            content = await file.read()
            logger.info(f"File read successfully, size: {len(content)} bytes")
        except Exception as read_error:
            logger.error(f"Error reading file: {str(read_error)}")
            raise HTTPException(
                status_code=400,
                detail=f"Error reading file: {str(read_error)}"
            )
        
        try:
            # 根据文件类型处理内容
            if file.filename.lower().endswith('.pdf'):
                # PDF文件保存为二进制
                file_path = os.path.join(UPLOAD_DIR, f"{kb_id}_{file.filename}")
                with open(file_path, 'wb') as f:
                    f.write(content)
                content_str = f"[PDF file saved at: {file_path}]"
                logger.info(f"PDF file saved: {file_path}")
            else:
                # 尝试不同的编码方式
                encodings = ['utf-8', 'gbk', 'latin1']
                content_str = None
                for encoding in encodings:
                    try:
                        content_str = content.decode(encoding)
                        logger.info(f"File decoded successfully with {encoding}")
                        break
                    except UnicodeDecodeError:
                        continue
                
                if content_str is None:
                    content_str = "[Binary content]"
                    logger.warning("Could not decode file content with any encoding")
            
            # 创建文档记录
            doc = Document(
                name=file.filename,
                content=content_str,
                knowledge_base_id=kb_id
            )
            
            logger.info("Adding document to database")
            db.add(doc)
            db.commit()
            db.refresh(doc)
            
            logger.info(f"Document uploaded successfully: {doc.id}")
            return {
                "status": "success",
                "document": {
                    "id": doc.id,
                    "name": doc.name,
                    "created_at": doc.created_at
                }
            }
            
        except Exception as process_error:
            logger.error(f"Error processing file content: {str(process_error)}")
            if 'db' in locals() and doc in locals():
                db.rollback()
            raise HTTPException(
                status_code=500,
                detail=f"Error processing file: {str(process_error)}"
            )
            
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Unexpected error in upload_document: {str(e)}")
        if 'db' in locals():
            db.rollback()
        raise HTTPException(
            status_code=500,
            detail=f"Unexpected error during upload: {str(e)}"
        )

@kb_router.put("/knowledge-bases/{kb_id}")
async def update_knowledge_base(
    kb_id: int,
    kb_update: schemas.KnowledgeBaseUpdate,
    current_user: User = Depends(check_permissions(["kb:manage"])),
    db: Session = Depends(get_db)
):
    """更新知识库 - 仅管理员"""
    db_kb = db.query(KnowledgeBase).filter(KnowledgeBase.id == kb_id).first()
    if not db_kb:
        raise HTTPException(status_code=404, detail="Knowledge base not found")
    
    for key, value in kb_update.dict(exclude_unset=True).items():
        setattr(db_kb, key, value)
    
    db.commit()
    db.refresh(db_kb)
    return db_kb

@kb_router.delete("/knowledge-bases/{kb_id}")
async def delete_knowledge_base(
    kb_id: int,
    current_user: User = Depends(check_permissions(["kb:manage"])),
    db: Session = Depends(get_db)
):
    """删除知识库 - 仅管理员"""
    db_kb = db.query(KnowledgeBase).filter(KnowledgeBase.id == kb_id).first()
    if not db_kb:
        raise HTTPException(status_code=404, detail="Knowledge base not found")
    
    db.delete(db_kb)
    db.commit()
    return {"status": "success"}

@kb_router.delete("/knowledge-bases/{kb_id}/documents/{doc_id}")
async def delete_document(
    kb_id: int,
    doc_id: int,
    current_user: User = Depends(check_permissions(["doc:manage"])),
    db: Session = Depends(get_db)
):
    """删除文档 - 仅管理员"""
    doc = db.query(Document).filter(
        Document.id == doc_id,
        Document.knowledge_base_id == kb_id
    ).first()
    
    if not doc:
        raise HTTPException(status_code=404, detail="Document not found")
    
    db.delete(doc)
    db.commit()
    return {"status": "success"}

@kb_router.get("/knowledge-bases/{kb_id}/documents/{doc_id}")
async def get_document(
    kb_id: int,
    doc_id: int,
    current_user: User = Depends(check_permissions(["doc:view"])),
    db: Session = Depends(get_db)
):
    """获取单个文档的详细内容"""
    try:
        # 检查知识库是否存在
        kb = db.query(KnowledgeBase).filter(KnowledgeBase.id == kb_id).first()
        if not kb:
            raise HTTPException(status_code=404, detail="Knowledge base not found")
            
        # 获取文档
        doc = db.query(Document).filter(
            Document.id == doc_id,
            Document.knowledge_base_id == kb_id
        ).first()
        
        if not doc:
            raise HTTPException(status_code=404, detail="Document not found")
        
        # 如果是 PDF 文件，需要读取文件内容
        if doc.file_path and doc.file_path.lower().endswith('.pdf'):
            try:
                with open(doc.file_path, 'rb') as f:
                    from pdfminer.high_level import extract_text
                    content = extract_text(f)
            except Exception as e:
                logger.error(f"Error reading PDF file: {str(e)}")
                content = "Error: Could not read PDF content"
        else:
            content = doc.content
            
        return {
            "id": doc.id,
            "name": doc.name,
            "content": content,
            "created_at": doc.created_at,
            "updated_at": doc.updated_at,
            "file_path": doc.file_path
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting document: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"Error getting document: {str(e)}"
        )