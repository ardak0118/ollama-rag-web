from fastapi import APIRouter, Depends, HTTPException, status, UploadFile, File, Form
from fastapi.responses import FileResponse, StreamingResponse
from sqlalchemy.orm import Session
from ..auth.database import get_db
from ..auth.routes import get_current_user
from ..auth.models import User
from .models import Feedback
from .schemas import FeedbackCreate, FeedbackResponse
from typing import Optional, List
import logging
import io
import urllib.parse

feedback_router = APIRouter()
logger = logging.getLogger(__name__)

@feedback_router.get("", response_model=dict)
async def list_feedback(
    type: Optional[str] = None,
    page: int = 1,
    size: int = 10,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """获取反馈列表（仅管理员）"""
    try:
        if not current_user.is_admin:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Only administrators can view feedback list"
            )
        
        # 构建查询
        query = db.query(Feedback)
        if type and type != 'all':
            query = query.filter(Feedback.type == type)
            
        # 计算总数
        total = query.count()
        
        # 分页
        feedbacks = query.order_by(Feedback.created_at.desc())\
                        .offset((page - 1) * size)\
                        .limit(size)\
                        .all()
        
        # 构建响应
        items = [{
            "id": f.id,
            "type": f.type,
            "content": f.content,
            "contact": f.contact,
            "created_at": f.created_at,
            "username": f.user.username if f.user else "未知用户",
            "kb_id": f.kb_id,
            "kb_name": f.kb_name,
            # 添加文件相关信息
            "file_name": f.file_name,
            "file_type": f.file_type,
            "has_file": bool(f.file_content)  # 添加文件存在标志
        } for f in feedbacks]
        
        return {
            "total": total,
            "items": items
        }
        
    except HTTPException as e:
        logger.error(f"Permission error in list_feedback: {e.detail}")
        raise
    except Exception as e:
        logger.error(f"Error listing feedback: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )

@feedback_router.post("")
async def create_feedback(
    type: str = Form(...),
    content: str = Form(...),
    contact: Optional[str] = Form(None),
    kb_id: Optional[int] = Form(None),
    kb_name: Optional[str] = Form(None),
    file: Optional[UploadFile] = File(None),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """创建反馈"""
    try:
        feedback_data = {
            "type": type,
            "content": content,
            "contact": contact,
            "user_id": current_user.id,
            "kb_id": kb_id,
            "kb_name": kb_name
        }

        # 如果有文件上传
        if file:
            # 读取文件内容
            file_content = await file.read()
            feedback_data.update({
                "file_name": file.filename,
                "file_content": file_content,
                "file_type": file.content_type
            })

        feedback = Feedback(**feedback_data)
        db.add(feedback)
        db.commit()
        db.refresh(feedback)

        return {"message": "反馈提交成功", "id": feedback.id}

    except Exception as e:
        logger.error(f"Error creating feedback: {str(e)}")
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error creating feedback: {str(e)}"
        )

@feedback_router.delete("/{feedback_id}", response_model=dict)
async def delete_feedback(
    feedback_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """删除反馈（仅管理员）"""
    try:
        if not current_user.is_admin:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Only administrators can delete feedback"
            )
        
        feedback = db.query(Feedback).filter(Feedback.id == feedback_id).first()
        if not feedback:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Feedback not found"
            )
            
        db.delete(feedback)
        db.commit()
        
        return {"message": "Feedback deleted successfully"}
        
    except HTTPException as e:
        logger.error(f"Error in delete_feedback: {e.detail}")
        raise
    except Exception as e:
        logger.error(f"Error deleting feedback: {str(e)}")
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error deleting feedback: {str(e)}"
        )

@feedback_router.get("/download/{feedback_id}")
async def download_feedback_file(
    feedback_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """下载反馈附件"""
    try:
        # 检查权限
        if not current_user.is_admin:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Only administrators can download feedback files"
            )

        # 获取反馈记录
        feedback = db.query(Feedback).filter(Feedback.id == feedback_id).first()
        if not feedback:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Feedback not found"
            )

        if not feedback.file_content:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="No file attached to this feedback"
            )

        # 创建文件流
        file_stream = io.BytesIO(feedback.file_content)
        
        # URL编码文件名以处理中文
        encoded_filename = urllib.parse.quote(feedback.file_name)
        
        # 设置响应头，使用 RFC 5987 编码处理中文文件名
        headers = {
            'Content-Disposition': f"attachment; filename*=UTF-8''{encoded_filename}",
            'Content-Type': feedback.file_type or 'application/octet-stream',
            'Access-Control-Expose-Headers': 'Content-Disposition'
        }

        # 返回流式响应
        return StreamingResponse(
            file_stream,
            headers=headers,
            media_type=feedback.file_type or 'application/octet-stream'
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error downloading feedback file: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error downloading file: {str(e)}"
        )