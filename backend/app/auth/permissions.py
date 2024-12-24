from functools import wraps
from fastapi import HTTPException, Depends, status
from .routes import get_current_user
from . import models
import logging

logger = logging.getLogger(__name__)

def check_permissions(required_permissions):
    """检查用户权限"""
    async def _check_permissions(current_user: models.User = Depends(get_current_user)):
        # 管理员拥有所有权限
        if current_user.is_admin:
            return current_user
        
        # 普通用户权限检查
        allowed_permissions = ['kb:view', 'doc:view']  # 普通用户允许的权限
        
        if any(perm not in allowed_permissions for perm in required_permissions):
            logger.warning(f"User {current_user.username} attempted to access restricted endpoint requiring {required_permissions}")
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Not enough permissions"
            )
        
        return current_user
    
    return _check_permissions

def require_permissions(*permissions):
    """权限检查装饰器"""
    return Depends(check_permissions(permissions))