from fastapi import APIRouter, Depends, HTTPException, status, Query
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from sqlalchemy.orm import Session
from datetime import datetime, timedelta
from typing import Optional
import logging
from pydantic import BaseModel

# 从当前包导入所需模块
from . import models, schemas
from ..database import get_db  # 修改导入路径
from .utils import create_access_token, verify_token, get_password_hash, verify_password
from .models import User  # 确保从 models 中导入 User
from .schemas import UrlRegisterParams  # 添加导入

auth_router = APIRouter()
logger = logging.getLogger(__name__)

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/auth/login")

async def get_current_user(
    token: str = Depends(oauth2_scheme),
    db: Session = Depends(get_db)
) -> User:
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    
    try:
        # verify_token 现在直接返回用户名字符串
        username = verify_token(token)
        if not username:
            raise credentials_exception
            
        # 查询用户
        user = db.query(User).filter(User.username == username).first()
        if not user:
            raise credentials_exception
            
        return user
        
    except Exception as e:
        logger.error(f"Error in get_current_user: {str(e)}")
        raise credentials_exception

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
        
        # 检查用户名否已存在
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

class LoginRequest(BaseModel):
    username: str
    password: str

@auth_router.post("/login")
async def login(request: LoginRequest, db: Session = Depends(get_db)):
    logger.info(f"Login attempt for user: {request.username}")
    
    try:
        # 验证请求数据
        if not request.username or not request.password:
            logger.warning("Empty username or password")
            raise HTTPException(
                status_code=422,
                detail={"message": "用户名和密码不能为空"}
            )

        # 查找用户
        user = db.query(models.User).filter(models.User.username == request.username).first()
        if not user:
            logger.warning(f"User not found: {request.username}")
            raise HTTPException(
                status_code=401,
                detail={"message": "用户名或密码错误"}
            )

        # 验证密码
        if not user.verify_password(request.password):  # 使用模型的方法验证密码
            logger.warning(f"Invalid password for user: {request.username}")
            raise HTTPException(
                status_code=401,
                detail={"message": "用户名或密码错误"}
            )

        # 更新最后登录时间
        user.last_login = datetime.utcnow()
        db.commit()
        
        # 创建访问令牌
        access_token = create_access_token(
            data={"sub": user.username},
            expires_delta=timedelta(hours=24)
        )
        
        # 准备返回数据
        response_data = {
            "access_token": access_token,
            "token_type": "bearer",
            "user": {
                "id": user.id,
                "username": user.username,
                "email": user.email,
                "is_admin": user.is_admin
            }
        }
        
        logger.info(f"Login successful for user: {request.username}")
        return response_data
    
    except HTTPException as e:
        logger.error(f"Login failed for user {request.username}: {e.detail}")
        raise
    except Exception as e:
        logger.error(f"Unexpected error during login: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail={"message": f"服务器错误: {str(e)}"}
        )

@auth_router.get("/me")
async def get_current_user_info(current_user: User = Depends(get_current_user)):
    """获取当前用户信息"""
    return {
        "id": current_user.id,
        "username": current_user.username,
        "email": current_user.email,
        "is_admin": current_user.is_admin
    }

@auth_router.get("/users/me", response_model=schemas.User)
async def read_users_me(current_user: User = Depends(get_current_user)):
    """获取当前登录用户信息"""
    return {
        "id": current_user.id,
        "username": current_user.username,
        "email": current_user.email,
        "is_active": current_user.is_active,
        "is_admin": current_user.is_admin,
        "can_manage_kb": current_user.can_manage_kb,
        "last_login": current_user.last_login,
        "created_at": current_user.created_at
    }

@auth_router.post("/register-from-params")
async def register_from_params(
    name: str = Query(..., description="用户名"),
    mobile: str = Query(..., description="手机号"),
    db: Session = Depends(get_db)
):
    """从URL参数注册用户或自动登录"""
    try:
        # 构造邮箱
        email = f"{mobile}@habachat.com"
        
        # 检查用户是否已存在
        existing_user = db.query(User).filter(
            (User.username == name) | (User.email == email)
        ).first()
        
        if existing_user:
            # 用户已存在,执行自动登录
            if not existing_user.verify_password(mobile):
                raise HTTPException(
                    status_code=400,
                    detail="Invalid credentials"
                )
                
            # 创建访问令牌
            access_token = create_access_token(
                data={"sub": existing_user.username}
            )
            
            return {
                "message": "Login successful",
                "access_token": access_token,
                "token_type": "bearer",
                "user": {
                    "id": existing_user.id,
                    "username": existing_user.username,
                    "email": existing_user.email,
                    "is_admin": existing_user.is_admin
                }
            }
            
        # 用户不存在,创建新用户
        user = User(
            username=name,
            email=email,
            is_active=True
        )
        user.set_password(mobile)  # 使用手机号作为密码
        
        db.add(user)
        db.commit()
        db.refresh(user)
        
        # 创建访问令牌
        access_token = create_access_token(
            data={"sub": user.username}
        )
        
        return {
            "message": "User registered successfully",
            "access_token": access_token,
            "token_type": "bearer",
            "user": {
                "id": user.id,
                "username": user.username,
                "email": user.email,
                "is_admin": user.is_admin
            }
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error in register-from-params: {str(e)}")
        db.rollback()
        raise HTTPException(
            status_code=500,
            detail=str(e)
        )

# 确保这些是可导出的
__all__ = ['auth_router', 'get_current_user']