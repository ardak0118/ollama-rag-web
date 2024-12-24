from fastapi import APIRouter, HTTPException, Depends, Form, Header, status
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from sqlalchemy.orm import Session
from datetime import timedelta, datetime
import logging
from typing import Optional
from . import models, schemas
from .database import get_db
from .utils import create_access_token, verify_token

# 配置日志
logger = logging.getLogger(__name__)

# 创建路由器
auth_router = APIRouter()
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/auth/login")

async def get_current_user(
    token: str = Depends(oauth2_scheme),
    db: Session = Depends(get_db)
) -> models.User:
    """获取当前用户"""
    credentials_exception = HTTPException(
        status_code=401,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    
    token_data = verify_token(token)
    if token_data is None:
        raise credentials_exception
        
    user = db.query(models.User).filter(models.User.username == token_data.username).first()
    if user is None:
        raise credentials_exception
        
    return user

@auth_router.get("/check-first-user")
async def check_first_user(db: Session = Depends(get_db)):
    """检查是否是第一个用户"""
    user_count = db.query(models.User).count()
    return {"is_first_user": user_count == 0}

@auth_router.post("/register")
async def register(user: schemas.UserCreate, db: Session = Depends(get_db)):
    """用户注册"""
    try:
        logger.info(f"Registration attempt for user: {user.username}")
        
        # 检查用户名是否已存在
        db_user = db.query(models.User).filter(models.User.username == user.username).first()
        if db_user:
            logger.warning(f"Username {user.username} already exists")
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Username already registered"
            )
        
        # 检查是否是第一个用户
        is_first_user = db.query(models.User).count() == 0
        logger.info(f"Is first user: {is_first_user}")
        
        # 确定是否设置为管理员
        is_admin = is_first_user or user.is_admin
        logger.info(f"Setting admin status: {is_admin}")
        
        # 创建新用户
        db_user = models.User(
            username=user.username,
            email=user.email,
            is_admin=is_admin
        )
        db_user.set_password(user.password)
        
        db.add(db_user)
        db.commit()
        db.refresh(db_user)
        logger.info(f"User {user.username} created successfully")
        
        # 生成访问令牌
        access_token = create_access_token(data={"sub": user.username})
        
        return {
            "access_token": access_token,
            "token_type": "bearer",
            "user": {
                "id": db_user.id,
                "username": db_user.username,
                "email": db_user.email,
                "is_admin": db_user.is_admin
            }
        }
    except HTTPException as he:
        raise he
    except Exception as e:
        logger.error(f"Registration error: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )

@auth_router.post("/login", response_model=schemas.Token)
async def login(
    form_data: OAuth2PasswordRequestForm = Depends(),
    db: Session = Depends(get_db)
):
    """用户登录"""
    try:
        # 查找用户
        user = db.query(models.User).filter(models.User.username == form_data.username).first()
        if not user:
            raise HTTPException(
                status_code=401,
                detail="Invalid username or password"
            )
        
        # 验证密码
        if not user.check_password(form_data.password):
            raise HTTPException(
                status_code=401,
                detail="Invalid username or password"
            )
        
        # 更新最后登录时间
        user.last_login = datetime.utcnow()
        db.commit()
        
        # 创建访问令牌
        access_token = create_access_token(
            data={"sub": user.username},
            expires_delta=timedelta(hours=24)
        )
        
        return {
            "access_token": access_token,
            "token_type": "bearer",
            "expires_in": 24 * 60 * 60
        }
    
    except HTTPException as he:
        raise he
    except Exception as e:
        logger.error(f"Login error: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"Login failed: {str(e)}"
        )

@auth_router.get("/me")
async def get_current_user_info(current_user: models.User = Depends(get_current_user)):
    """获取当前用户信息"""
    return {
        "id": current_user.id,
        "username": current_user.username,
        "email": current_user.email,
        "is_admin": current_user.is_admin
    }

# 确保这些是可导出的
__all__ = ['auth_router', 'get_current_user']