from pydantic import BaseModel, EmailStr, validator
from typing import Optional
from datetime import datetime

class UserBase(BaseModel):
    username: str
    email: EmailStr

class UserCreate(UserBase):
    password: str
    
    @validator('username')
    def username_validator(cls, v):
        if len(v) < 3:
            raise ValueError('Username must be at least 3 characters')
        if len(v) > 20:
            raise ValueError('Username must be less than 20 characters')
        return v
    
    @validator('password')
    def password_validator(cls, v):
        if len(v) < 6:
            raise ValueError('Password must be at least 6 characters')
        return v

class UserInDB(UserBase):
    id: Optional[int] = None
    hashed_password: str
    is_active: bool = True
    created_at: Optional[datetime] = None
    last_login: Optional[datetime] = None
    avatar: Optional[str] = None
    role: str = "user"
    is_verified: bool = False

class User(UserBase):
    id: Optional[int] = None
    is_active: bool = True
    created_at: Optional[datetime] = None
    last_login: Optional[datetime] = None
    avatar: Optional[str] = None
    role: str = "user"
    is_verified: bool = False

class Token(BaseModel):
    access_token: str
    token_type: str = "bearer"
    expires_in: int

class TokenData(BaseModel):
    username: Optional[str] = None

class LoginHistory(BaseModel):
    id: Optional[int] = None
    user_id: int
    login_time: datetime
    ip_address: Optional[str]
    user_agent: Optional[str] 