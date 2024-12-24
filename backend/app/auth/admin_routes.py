from fastapi import APIRouter, HTTPException, Depends, UploadFile, File, status
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session
from typing import List
from . import models, schemas
from .database import get_db
from .routes import get_current_user
from .permissions import check_permissions
import logging
from datetime import datetime
import csv
import io
from ..auth.utils import get_password_hash
from fastapi.responses import Response

logger = logging.getLogger(__name__)
admin_router = APIRouter()

# 管理员权限检查
async def get_current_admin(
    current_user: models.User = Depends(get_current_user)
) -> models.User:
    """检查当前用户是否是管理员"""
    if not current_user.is_admin:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not enough permissions"
        )
    return current_user

@admin_router.get("/users", response_model=List[schemas.UserInfo])
async def get_users(
    current_admin: models.User = Depends(get_current_admin),
    db: Session = Depends(get_db)
):
    """获取所有用户列表"""
    users = db.query(models.User).all()
    return users

@admin_router.post("/users", response_model=schemas.UserInfo)
async def create_user(
    user: schemas.UserCreate,
    current_admin: models.User = Depends(get_current_admin),
    db: Session = Depends(get_db)
):
    """创建新用户"""
    try:
        logger.info(f"Creating new user: {user.username}")
        logger.info(f"User data: {user.dict()}")
        
        # 检查用户名是否已存在
        if db.query(models.User).filter(models.User.username == user.username).first():
            logger.warning(f"Username {user.username} already exists")
            raise HTTPException(
                status_code=400,
                detail="Username already registered"
            )
        
        # 创建新用户
        db_user = models.User(
            username=user.username,
            email=user.email,
            is_admin=user.is_admin,
            is_active=True,
            created_at=datetime.utcnow()
        )
        db_user.set_password(user.password)
        
        logger.info(f"Adding user to database: {db_user.username}")
        db.add(db_user)
        db.commit()
        db.refresh(db_user)
        
        logger.info(f"User {db_user.username} created successfully")
        return db_user
        
    except HTTPException as he:
        raise he
    except Exception as e:
        logger.error(f"Error creating user: {str(e)}")
        db.rollback()
        raise HTTPException(
            status_code=500,
            detail=f"Error creating user: {str(e)}"
        )

@admin_router.put("/users/{user_id}", response_model=schemas.UserInfo)
async def update_user(
    user_id: int,
    user_update: schemas.UserUpdate,
    current_admin: models.User = Depends(get_current_admin),
    db: Session = Depends(get_db)
):
    """更新用户信息"""
    db_user = db.query(models.User).filter(models.User.id == user_id).first()
    if not db_user:
        raise HTTPException(status_code=404, detail="User not found")
    
    # 防止取消最后一个管理员的管理员权限
    if db_user.is_admin and not user_update.is_admin:
        admin_count = db.query(models.User).filter(models.User.is_admin == True).count()
        if admin_count <= 1:
            raise HTTPException(
                status_code=400,
                detail="Cannot remove the last admin"
            )
    
    # 更新用户信息
    for key, value in user_update.dict(exclude_unset=True).items():
        if key == "password" and value:
            db_user.set_password(value)
        else:
            setattr(db_user, key, value)
    
    db.commit()
    db.refresh(db_user)
    return db_user

@admin_router.delete("/users/{user_id}")
async def delete_user(
    user_id: int,
    current_admin: models.User = Depends(get_current_admin),
    db: Session = Depends(get_db)
):
    """删除用户"""
    db_user = db.query(models.User).filter(models.User.id == user_id).first()
    if not db_user:
        raise HTTPException(status_code=404, detail="User not found")
    
    # 防止删除最后一个管理员
    if db_user.is_admin:
        admin_count = db.query(models.User).filter(models.User.is_admin == True).count()
        if admin_count <= 1:
            raise HTTPException(
                status_code=400,
                detail="Cannot delete the last admin"
            )
    
    # 防止自删除
    if db_user.id == current_admin.id:
        raise HTTPException(
            status_code=400,
            detail="Cannot delete yourself"
        )
    
    db.delete(db_user)
    db.commit()
    return {"status": "success"}

@admin_router.post("/users/batch")
async def batch_create_users(
    users: List[schemas.UserCreate],
    current_admin: models.User = Depends(get_current_admin),
    db: Session = Depends(get_db)
):
    """批量创建用户"""
    created_users = []
    errors = []
    
    for user in users:
        try:
            # 检查用户名是否已存在
            if db.query(models.User).filter(models.User.username == user.username).first():
                errors.append({
                    "username": user.username,
                    "error": "Username already exists"
                })
                continue
            
            # 创建新用户
            db_user = models.User(
                username=user.username,
                email=user.email,
                is_admin=user.is_admin
            )
            db_user.set_password(user.password)
            
            db.add(db_user)
            db.commit()
            db.refresh(db_user)
            
            created_users.append(db_user)
            
        except Exception as e:
            errors.append({
                "username": user.username,
                "error": str(e)
            })
    
    return {
        "success": created_users,
        "errors": errors
    } 

@admin_router.get("/test")
async def test_admin_access(
    current_admin: models.User = Depends(get_current_admin),
    db: Session = Depends(get_db)
):
    """测试管理员权限"""
    try:
        # 获取一些基本统计信息
        total_users = db.query(models.User).count()
        admin_users = db.query(models.User).filter(models.User.is_admin == True).count()
        active_users = db.query(models.User).filter(models.User.is_active == True).count()
        
        return {
            "status": "success",
            "message": "Admin access verified",
            "admin_info": {
                "username": current_admin.username,
                "email": current_admin.email,
                "created_at": current_admin.created_at
            },
            "stats": {
                "total_users": total_users,
                "admin_users": admin_users,
                "active_users": active_users
            }
        }
    except Exception as e:
        logger.error(f"Error in admin test: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"Admin test failed: {str(e)}"
        )

@admin_router.get("/stats")
async def get_admin_stats(
    current_admin: models.User = Depends(get_current_admin),
    db: Session = Depends(get_db)
):
    """获取管理统计信息"""
    try:
        # 用户统计
        total_users = db.query(models.User).count()
        admin_users = db.query(models.User).filter(models.User.is_admin == True).count()
        active_users = db.query(models.User).filter(models.User.is_active == True).count()
        
        # 最近注册的用户
        recent_users = db.query(models.User)\
            .order_by(models.User.created_at.desc())\
            .limit(5)\
            .all()
        
        # 最近登录的用户
        recent_logins = db.query(models.User)\
            .filter(models.User.last_login.isnot(None))\
            .order_by(models.User.last_login.desc())\
            .limit(5)\
            .all()
        
        return {
            "user_stats": {
                "total_users": total_users,
                "admin_users": admin_users,
                "active_users": active_users
            },
            "recent_users": [
                {
                    "username": user.username,
                    "email": user.email,
                    "created_at": user.created_at
                }
                for user in recent_users
            ],
            "recent_logins": [
                {
                    "username": user.username,
                    "last_login": user.last_login
                }
                for user in recent_logins
            ]
        }
    except Exception as e:
        logger.error(f"Error getting admin stats: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"Error getting admin stats: {str(e)}"
        ) 

@admin_router.post("/users/import")
async def import_users(
    file: UploadFile = File(...),
    current_user: models.User = Depends(check_permissions(["user:manage"])),
    db: Session = Depends(get_db)
):
    """批量导入用户"""
    if not file.filename.endswith('.csv'):
        raise HTTPException(
            status_code=400,
            detail="Only CSV files are allowed"
        )
    
    # 读取并验证CSV文件
    try:
        contents = await file.read()
        csv_file = io.StringIO(contents.decode('utf-8-sig'))
        csv_reader = csv.DictReader(csv_file)
        
        required_fields = {'username', 'password', 'email', 'is_admin'}
        if not all(field in csv_reader.fieldnames for field in required_fields):
            raise HTTPException(
                status_code=400,
                detail="CSV file must contain username, password, email, and is_admin fields"
            )
        
        success_count = 0
        failed_count = 0
        error_messages = []
        
        for row in csv_reader:
            try:
                # 验证必填字段
                if not all(row.get(field) for field in required_fields):
                    raise ValueError("Missing required fields")
                
                # 检查用户名是否已存在
                if db.query(models.User).filter(models.User.username == row['username']).first():
                    raise ValueError(f"Username {row['username']} already exists")
                
                # 创建用户
                user = models.User(
                    username=row['username'],
                    email=row['email'],
                    hashed_password=get_password_hash(row['password']),
                    is_admin=row['is_admin'].lower() == 'true',
                    is_active=True
                )
                
                db.add(user)
                db.commit()
                success_count += 1
                
            except Exception as e:
                failed_count += 1
                error_messages.append(f"Row {csv_reader.line_num}: {str(e)}")
                db.rollback()
        
        return {
            "success_count": success_count,
            "failed_count": failed_count,
            "errors": error_messages if error_messages else None
        }
        
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Error processing CSV file: {str(e)}"
        )

@admin_router.get("/users/template")
async def get_user_template(
    current_user: models.User = Depends(check_permissions(["user:manage"]))
):
    """获取用户导入模板"""
    try:
        # 创建一个内存中的CSV文件
        output = io.StringIO()
        writer = csv.writer(output)
        
        # 写入表头
        writer.writerow(['username', 'password', 'email', 'is_admin'])
        # 写入示例数据
        writer.writerow(['example', 'password123', 'example@email.com', 'false'])
        
        # 将指针移到开始位置
        output.seek(0)
        
        # 返回CSV文件
        return StreamingResponse(
            iter([output.getvalue()]),
            media_type="text/csv",
            headers={
                "Content-Disposition": "attachment; filename=users_template.csv",
                "Access-Control-Expose-Headers": "Content-Disposition",
                "Access-Control-Allow-Origin": "*",
                "Access-Control-Allow-Methods": "GET",
            }
        )
    except Exception as e:
        logger.error(f"Error generating template: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"Error generating template: {str(e)}"
        )