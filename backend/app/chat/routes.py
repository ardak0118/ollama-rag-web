from fastapi import APIRouter, HTTPException, Depends, status
from sqlalchemy.orm import Session
from ..auth.database import get_db
from ..auth.routes import get_current_user
from ..auth.permissions import require_permissions
from . import models, schemas

chat_router = APIRouter()

@chat_router.get("/conversations")
async def list_conversations(
    current_user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """获取聊天记录列表"""
    try:
        # 管理员可以看到所有聊天记录，普通用户只能看到自己的
        if current_user.is_admin:
            conversations = db.query(models.Conversation).all()
        else:
            conversations = db.query(models.Conversation).filter(
                models.Conversation.user_id == current_user.id
            ).all()
        return conversations
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Error fetching conversations: {str(e)}"
        )

@chat_router.get("/conversations/{conversation_id}")
async def get_conversation(
    conversation_id: str,
    current_user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """获取特定聊天记录"""
    conversation = db.query(models.Conversation).filter(
        models.Conversation.conversation_id == conversation_id
    ).first()
    
    if not conversation:
        raise HTTPException(status_code=404, detail="Conversation not found")
    
    # 检查权限：只能查看自己的聊天记录，除非是管理员
    if not current_user.is_admin and conversation.user_id != current_user.id:
        raise HTTPException(
            status_code=403,
            detail="You don't have permission to view this conversation"
        )
    
    return conversation