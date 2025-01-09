import csv
import io
from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, status
from sqlalchemy.orm import Session
from ..auth.database import get_db
from ..auth.models import User
from ..auth.routes import get_current_user
from ..auth.utils import get_password_hash
from ..auth.schemas import UserCreate
import logging
from fastapi.responses import StreamingResponse, JSONResponse
import chardet
from datetime import datetime, timedelta
import httpx
from sqlalchemy import func

admin_router = APIRouter()
logger = logging.getLogger(__name__)

@admin_router.post("/users/import")
async def import_users(
    file: UploadFile = File(...),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """批量导入用户"""
    if not current_user.is_admin:
        raise HTTPException(
            status_code=403,
            detail="Only administrators can import users"
        )

    try:
        content = await file.read()
        
        # 尝试检测文件编码
        result = chardet.detect(content)
        detected_encoding = result['encoding']
        
        logger.info(f"Detected file encoding: {detected_encoding}")
        
        try:
            text = content.decode(detected_encoding or 'utf-8')
        except UnicodeDecodeError:
            # 如果检测到的编码不工作，尝试其他编码
            encodings = ['utf-8-sig', 'utf-8', 'gbk', 'gb2312', 'iso-8859-1']
            for encoding in encodings:
                try:
                    text = content.decode(encoding)
                    logger.info(f"Successfully decoded with {encoding}")
                    break
                except UnicodeDecodeError:
                    continue
            else:
                raise HTTPException(
                    status_code=400,
                    detail="无法解析文件编码，请确保文件使用 UTF-8 编码保存"
                )
        
        # 记录成功使用的编码
        logger.info(f"File successfully decoded using {detected_encoding} encoding")
        
        csv_file = io.StringIO(text)
        csv_reader = csv.DictReader(csv_file)

        # 添加调试日志
        logger.info(f"CSV headers: {csv_reader.fieldnames}")

        required_fields = ['username', 'email', 'password']

        # 验证CSV头部，不区分大小写且去除空格
        headers = [h.lower().strip() for h in (csv_reader.fieldnames or [])]
        logger.info(f"Processed headers: {headers}")

        # 规范化 CSV 头部
        header_map = {}
        for h in csv_reader.fieldnames or []:
            normalized = h.lower().strip()
            if normalized in required_fields:
                header_map[h] = normalized

        missing_fields = [field for field in required_fields if not any(h.lower().strip() == field for h in (csv_reader.fieldnames or []))]

        if missing_fields:
            logger.error(f"Missing required fields: {missing_fields}")
            logger.error(f"Found fields: {headers}")
            raise HTTPException(
                status_code=400,
                detail=f"CSV文件缺少必要的列：{', '.join(missing_fields)}"
            )

        imported_count = 0
        errors = []

        for row_num, row in enumerate(csv_reader, start=2):
            try:
                # 使用规范化的字段名获取值
                user_data = {
                    'username': row.get(next(k for k in row.keys() if k.lower().strip() == 'username'), '').strip(),
                    'email': row.get(next(k for k in row.keys() if k.lower().strip() == 'email'), '').strip(),
                    'password': row.get(next(k for k in row.keys() if k.lower().strip() == 'password'), '').strip(),
                    'role': row.get(next((k for k in row.keys() if k.lower().strip() == 'role'), ''), '').strip()
                }

                # 验证必填字段
                missing_values = [field for field in required_fields if not user_data.get(field)]
                if missing_values:
                    errors.append(f"第 {row_num} 行：缺少必要的值：{', '.join(missing_values)}")
                    continue

                # 验证邮箱格式
                email = user_data['email']
                if not '@' in email:
                    errors.append(f"第 {row_num} 行：邮箱格式无效")
                    continue

                # 检查用户是否已存在
                existing_user = db.query(User).filter(
                    (User.username == user_data['username']) | 
                    (User.email == email)
                ).first()

                if existing_user:
                    errors.append(f"第 {row_num} 行：用户名 {user_data['username']} 或邮箱 {email} 已存在")
                    continue

                # 创建新用户
                new_user = User(
                    username=user_data['username'],
                    email=email,
                    is_active=True,
                    is_admin=user_data.get('role', '').lower() == 'admin'
                )
                new_user.set_password(user_data['password'])

                db.add(new_user)
                imported_count += 1

            except Exception as e:
                errors.append(f"第 {row_num} 行处理失败：{str(e)}")
                logger.error(f"Error processing row {row_num}: {str(e)}")

        # 提交事务
        if imported_count > 0:
            db.commit()

        result = {
            "status": "success" if not errors else "partial_success",
            "imported_count": imported_count,
            "errors": errors
        }

        if not imported_count and errors:
            raise HTTPException(
                status_code=400,
                detail={
                    "message": "导入失败，没有用户被成功导入",
                    "errors": errors
                }
            )

        return result

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error importing users: {str(e)}")
        db.rollback()
        raise HTTPException(
            status_code=500,
            detail=f"导入用户时发生错误：{str(e)}"
        )

@admin_router.get("/users/template")
async def get_user_template(current_user: User = Depends(get_current_user)):
    """获取用户导入模板"""
    if not current_user.is_admin:
        raise HTTPException(
            status_code=403,
            detail="Only administrators can download the template"
        )

    try:
        # 创建CSV模板
        output = io.StringIO()
        writer = csv.writer(output)
        
        # 写入头部
        writer.writerow(['username', 'email', 'password', 'role'])
        writer.writerow(['example_user', 'user@example.com', 'password123', 'user'])
        
        # 将指针移到开始
        output.seek(0)
        
        # 添加日志
        logger.info("Template file generated successfully")
        
        return StreamingResponse(
            iter([output.getvalue()]),
            media_type="text/csv",
            headers={
                'Content-Disposition': 'attachment; filename=users_template.csv',
                'Content-Type': 'text/csv; charset=utf-8',
                'Content-Security-Policy': "default-src * 'unsafe-inline' 'unsafe-eval' data: blob:",
                'X-Content-Type-Options': 'nosniff'
            }
        )
    except Exception as e:
        logger.error(f"Error generating template: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"Error generating template: {str(e)}"
        )

@admin_router.get("/users")
async def list_users(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """获取用户列表"""
    if not current_user.is_admin:
        raise HTTPException(
            status_code=403,
            detail="Only administrators can view user list"
        )

    try:
        users = db.query(User).all()
        return [
            {
                "id": user.id,
                "username": user.username,
                "email": user.email,
                "is_active": user.is_active,
                "is_admin": user.is_admin,
                "can_manage_kb": user.can_manage_kb,
                "last_login": user.last_login,
                "created_at": user.created_at
            }
            for user in users
        ]
    except Exception as e:
        logger.error(f"Error listing users: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"Error listing users: {str(e)}"
        )

@admin_router.post("/users")
async def create_user(
    user: UserCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """创建用户"""
    if not current_user.is_admin:
        raise HTTPException(
            status_code=403,
            detail="Only administrators can create users"
        )

    try:
        # 检查用户名是否已存在
        if db.query(User).filter(User.username == user.username).first():
            raise HTTPException(
                status_code=400,
                detail="Username already registered"
            )

        # 检查邮箱是否已存在
        if db.query(User).filter(User.email == user.email).first():
            raise HTTPException(
                status_code=400,
                detail="Email already registered"
            )

        # 创建新用户
        db_user = User(
            username=user.username,
            email=user.email,
            is_admin=user.is_admin
        )
        db_user.set_password(user.password)

        db.add(db_user)
        db.commit()
        db.refresh(db_user)

        return {
            "id": db_user.id,
            "username": db_user.username,
            "email": db_user.email,
            "is_admin": db_user.is_admin,
            "is_active": db_user.is_active,
            "created_at": db_user.created_at.isoformat() if db_user.created_at else None
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error creating user: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"Error creating user: {str(e)}"
        )

@admin_router.get("/stats")
async def get_admin_stats(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """获取管理统计信息"""
    if not current_user.is_admin:
        raise HTTPException(
            status_code=403,
            detail="Only administrators can view stats"
        )

    try:
        # 获取用户统计
        total_users = db.query(func.count(User.id)).scalar()
        admin_users = db.query(func.count(User.id)).filter(User.is_admin == True).scalar()
        active_users = db.query(func.count(User.id)).filter(User.is_active == True).scalar()
        
        # 获取最近注册的用户
        recent_users = db.query(User).order_by(User.created_at.desc()).limit(5).all()
        
        # 获取最近登录的用户
        recent_logins = db.query(User)\
            .filter(User.last_login.isnot(None))\
            .order_by(User.last_login.desc())\
            .limit(5).all()
            
        return {
            "user_stats": {
                "total": total_users,
                "admin": admin_users,
                "active": active_users
            },
            "recent_users": [{
                "id": user.id,
                "username": user.username,
                "email": user.email,
                "created_at": user.created_at
            } for user in recent_users],
            "recent_logins": [{
                "id": user.id,
                "username": user.username,
                "last_login": user.last_login
            } for user in recent_logins]
        }
        
    except Exception as e:
        logger.error(f"Error getting admin stats: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"Error getting admin stats: {str(e)}"
        )

@admin_router.get("/test")
async def test_admin_api(current_user: User = Depends(get_current_user)):
    """测试管理员 API"""
    if not current_user.is_admin:
        raise HTTPException(status_code=403, detail="需要管理员权限")
    return {"message": "管理员 API 测试成功"}

@admin_router.put("/users/{user_id}/kb-permission")
async def update_user_kb_permission(
    user_id: int,
    permission: dict,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """更新用户的知识库管理权限"""
    if not current_user.is_admin:
        raise HTTPException(
            status_code=403,
            detail="Only administrators can modify user permissions"
        )

    try:
        # 获取目标用户
        user = db.query(User).filter(User.id == user_id).first()
        if not user:
            raise HTTPException(
                status_code=404,
                detail="User not found"
            )

        # 不允许修改管理员的权限
        if user.is_admin:
            raise HTTPException(
                status_code=400,
                detail="Cannot modify admin user's permissions"
            )

        # 不允许修改自己的权限
        if user.id == current_user.id:
            raise HTTPException(
                status_code=400,
                detail="Cannot modify your own permissions"
            )

        # 更新权限
        user.can_manage_kb = permission.get('can_manage_kb', False)
        db.commit()

        return {
            "id": user.id,
            "username": user.username,
            "can_manage_kb": user.can_manage_kb
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error updating user permission: {str(e)}")
        db.rollback()
        raise HTTPException(
            status_code=500,
            detail=f"Error updating user permission: {str(e)}"
        ) 

@admin_router.put("/users/{user_id}")
async def update_user(
    user_id: int,
    user_update: dict,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """更新用户状态"""
    if not current_user.is_admin:
        raise HTTPException(
            status_code=403,
            detail="Only administrators can modify users"
        )

    try:
        # 获取目标用户
        user = db.query(User).filter(User.id == user_id).first()
        if not user:
            raise HTTPException(
                status_code=404,
                detail="User not found"
            )

        # 不允许修改自己的状态
        if user.id == current_user.id:
            raise HTTPException(
                status_code=400,
                detail="Cannot modify your own status"
            )

        # 更新用户状态
        if "is_active" in user_update:
            user.is_active = user_update["is_active"]

        db.commit()

        return {
            "id": user.id,
            "username": user.username,
            "is_active": user.is_active
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error updating user: {str(e)}")
        db.rollback()
        raise HTTPException(
            status_code=500,
            detail=f"Error updating user: {str(e)}"
        )

@admin_router.delete("/users/{user_id}")
async def delete_user(
    user_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """删除用户"""
    if not current_user.is_admin:
        raise HTTPException(
            status_code=403,
            detail="Only administrators can delete users"
        )

    try:
        # 获取目标用户
        user = db.query(User).filter(User.id == user_id).first()
        if not user:
            raise HTTPException(
                status_code=404,
                detail="User not found"
            )

        # 不允许删除自己
        if user.id == current_user.id:
            raise HTTPException(
                status_code=400,
                detail="Cannot delete your own account"
            )

        # 不允许删除其他管理员
        if user.is_admin:
            raise HTTPException(
                status_code=400,
                detail="Cannot delete admin users"
            )

        # 删除用户
        db.delete(user)
        db.commit()

        return {"message": "User deleted successfully"}

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error deleting user: {str(e)}")
        db.rollback()
        raise HTTPException(
            status_code=500,
            detail=f"Error deleting user: {str(e)}"
        ) 
@admin_router.post("/test-url")
async def test_url(
    url: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """测试URL是否可访问"""
    try:
        # 检查权限
        if not current_user.is_admin:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Only administrators can use this endpoint"
            )

        # 尝试访问URL
        async with httpx.AsyncClient(timeout=10.0) as client:
            response = await client.get(url)
            
            return {
                "status": "success",
                "status_code": response.status_code,
                "headers": dict(response.headers),
                "content_type": response.headers.get("content-type"),
                "url": str(response.url),
                "is_redirect": response.is_redirect,
                "message": "URL可以访问"
            }

    except httpx.TimeoutException:
        raise HTTPException(
            status_code=status.HTTP_504_GATEWAY_TIMEOUT,
            detail="URL访问超时"
        )
    except httpx.RequestError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"无法访问URL: {str(e)}"
        )
    except Exception as e:
        logger.error(f"Error testing URL: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"测试URL时发生错误: {str(e)}"
        ) 
