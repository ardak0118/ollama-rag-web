from fastapi import APIRouter, HTTPException, Depends, Form, Header
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from .database import get_user_by_username, create_user, record_login
from .models import User
from .schemas import Token, UserCreate
from .utils import create_access_token, verify_token
from datetime import timedelta
import os
from typing import Optional

# 将 router 重命名为 auth_router
auth_router = APIRouter()
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/auth/login")

# 数据库路径
DB_PATH = os.path.join(os.path.dirname(os.path.dirname(__file__)), "auth.db")

async def get_current_user(token: str = Depends(oauth2_scheme)) -> User:
    credentials_exception = HTTPException(
        status_code=401,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    
    token_data = verify_token(token)
    if token_data is None:
        raise credentials_exception
        
    user = get_user_by_username(DB_PATH, token_data.username)
    if user is None:
        raise credentials_exception
        
    return user

@auth_router.post("/register", response_model=Token)
async def register(user_data: UserCreate):
    try:
        print(f"Registering user: {user_data}")  # 添加调试日志
        
        # 数据验证
        if len(user_data.username) < 3:
            raise HTTPException(
                status_code=400,
                detail="Username must be at least 3 characters"
            )
        if len(user_data.password) < 6:
            raise HTTPException(
                status_code=400,
                detail="Password must be at least 6 characters"
            )
            
        # 验证用户名是否已存在
        existing_user = get_user_by_username(DB_PATH, user_data.username)
        if existing_user:
            raise HTTPException(
                status_code=400,
                detail="Username already exists"
            )
            
        try:
            # 创建新用户
            user = create_user(DB_PATH, user_data)
            if not user:
                raise HTTPException(
                    status_code=500,
                    detail="Failed to create user"
                )
            
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
            
        except ValueError as ve:
            raise HTTPException(
                status_code=400,
                detail=str(ve)
            )
            
    except HTTPException as he:
        print(f"HTTP Exception in register: {he.detail}")  # 添加错误日志
        raise he
    except Exception as e:
        print(f"Unexpected error in register: {str(e)}")  # 添加错误日志
        raise HTTPException(
            status_code=500,
            detail=f"Registration failed: {str(e)}"
        )

@auth_router.post("/login", response_model=Token)
async def login(form_data: OAuth2PasswordRequestForm = Depends()):
    try:
        print(f"Login attempt for user: {form_data.username}")
        print(f"Form data: {form_data}")
        
        user = get_user_by_username(DB_PATH, form_data.username)
        
        if not user:
            print(f"User not found: {form_data.username}")
            raise HTTPException(
                status_code=401,
                detail="Invalid username or password"
            )
        
        print(f"Found user: {user.username}")
        print(f"Stored hash: {user.hashed_password}")
        print(f"Input password length: {len(form_data.password)}")
        
        # 验证密码
        if not user.check_password(form_data.password):
            print(f"Password verification failed for user: {user.username}")
            raise HTTPException(
                status_code=401,
                detail="Invalid username or password"
            )
            
        # 创建访问令牌
        access_token = create_access_token(
            data={"sub": user.username},
            expires_delta=timedelta(hours=24)
        )
        
        print(f"Login successful for user: {user.username}")
        return {
            "access_token": access_token,
            "token_type": "bearer",
            "expires_in": 24 * 60 * 60
        }
    
    except HTTPException as he:
        raise he
    except Exception as e:
        print(f"Unexpected error in login: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"Login failed: {str(e)}"
        )

@auth_router.get("/me", response_model=dict)
async def read_users_me(current_user: User = Depends(get_current_user)):
    """获取当前用户信息"""
    try:
        if not current_user:
            raise HTTPException(
                status_code=401,
                detail="Not authenticated",
                headers={"WWW-Authenticate": "Bearer"},
            )
            
        # 返回用户信息，排除敏感字段
        return {
            "id": current_user.id,
            "username": current_user.username,
            "email": current_user.email,
            "role": current_user.role,
            "avatar": current_user.avatar,
            "is_active": current_user.is_active,
            "is_verified": current_user.is_verified,
            "created_at": current_user.created_at,
            "last_login": current_user.last_login
        }
        
    except HTTPException as he:
        raise he
    except Exception as e:
        logger.error(f"Error in read_users_me: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"Internal server error: {str(e)}"
        )

# 确保这些是可导出的
__all__ = ['auth_router', 'get_current_user']