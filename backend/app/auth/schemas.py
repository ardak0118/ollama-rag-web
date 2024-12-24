from pydantic import BaseModel, EmailStr
from typing import Optional, List
from datetime import datetime

# 基础用户模型
class UserBase(BaseModel):
    username: str
    email: EmailStr

# 创建用户时的模型
class UserCreate(UserBase):
    username: str
    email: EmailStr
    password: str
    is_admin: Optional[bool] = False
    is_active: Optional[bool] = True

# 用户信息模型
class User(UserBase):
    id: int
    is_admin: bool

    class Config:
        orm_mode = True

# 数据库中的用户模型
class UserInDB(UserBase):
    id: Optional[int] = None
    hashed_password: str
    is_active: bool = True
    created_at: Optional[datetime] = None
    last_login: Optional[datetime] = None
    avatar: Optional[str] = None
    role: str = "user"
    is_verified: bool = False
    is_admin: bool = False

# Token 相关模型
class Token(BaseModel):
    access_token: str
    token_type: str = "bearer"
    expires_in: int

class TokenData(BaseModel):
    username: Optional[str] = None

# 登录历史模型
class LoginHistory(BaseModel):
    id: Optional[int] = None
    user_id: int
    login_time: datetime
    ip_address: Optional[str]
    user_agent: Optional[str]

class UserInfo(BaseModel):
    id: int
    username: str
    email: EmailStr
    is_admin: bool
    is_active: bool
    last_login: Optional[datetime]
    created_at: datetime

    class Config:
        orm_mode = True

class UserUpdate(BaseModel):
    email: Optional[EmailStr]
    password: Optional[str]
    is_admin: Optional[bool]
    is_active: Optional[bool]

class BatchUserCreate(BaseModel):
    users: List[UserCreate]