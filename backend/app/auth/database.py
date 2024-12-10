import sqlite3
from datetime import datetime
from typing import Optional
from .models import User
from .schemas import UserCreate
from .utils import get_password_hash

def init_auth_db(db_path: str):
    """初始化认证数据库"""
    conn = sqlite3.connect(db_path)
    c = conn.cursor()
    
    try:
        # 先删除旧表（如果存在）
        c.execute('DROP TABLE IF EXISTS login_history')
        c.execute('DROP TABLE IF EXISTS users')
        
        # 创建用户表
        c.execute('''
            CREATE TABLE users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                username TEXT UNIQUE NOT NULL,
                email TEXT UNIQUE NOT NULL,
                hashed_password TEXT NOT NULL,
                is_active BOOLEAN NOT NULL DEFAULT 1,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                last_login TIMESTAMP,
                avatar TEXT,
                role TEXT DEFAULT 'user',
                is_verified BOOLEAN DEFAULT 0
            )
        ''')
        
        # 创建用户登录历史表
        c.execute('''
            CREATE TABLE login_history (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                login_time TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                ip_address TEXT,
                user_agent TEXT,
                FOREIGN KEY (user_id) REFERENCES users (id)
            )
        ''')
        
        conn.commit()
        print("Auth database initialized successfully")
    except Exception as e:
        print(f"Error initializing auth database: {e}")
        conn.rollback()
        raise
    finally:
        conn.close()

def get_user_by_username(db_path: str, username: str) -> Optional[User]:
    """通过用户名获取用户"""
    conn = sqlite3.connect(db_path)
    c = conn.cursor()
    
    try:
        c.execute('''
            SELECT id, username, email, hashed_password, is_active, created_at, 
                   last_login, avatar, role, is_verified
            FROM users 
            WHERE username = ?
        ''', (username,))
        
        user = c.fetchone()
        if user:
            return User(
                id=user[0],
                username=user[1],
                email=user[2],
                hashed_password=user[3],
                is_active=bool(user[4]),
                created_at=datetime.fromisoformat(user[5]) if user[5] else None,
                last_login=datetime.fromisoformat(user[6]) if user[6] else None,
                avatar=user[7],
                role=user[8] or 'user',
                is_verified=bool(user[9])
            )
        return None
        
    except Exception as e:
        print(f"Error getting user: {e}")
        return None
    finally:
        conn.close()

def create_user(db_path: str, user: UserCreate) -> Optional[User]:
    """创建新用户"""
    conn = sqlite3.connect(db_path)
    c = conn.cursor()
    
    try:
        # 检查用户名是否已存在
        c.execute('SELECT 1 FROM users WHERE username = ?', (user.username,))
        if c.fetchone():
            raise ValueError("Username already exists")
            
        # 检查邮箱是否已存在
        c.execute('SELECT 1 FROM users WHERE email = ?', (user.email,))
        if c.fetchone():
            raise ValueError("Email already exists")
        
        # 生成密码哈希
        hashed_password = get_password_hash(user.password)
        print(f"Creating user {user.username} with hash: {hashed_password}")
        
        current_time = datetime.utcnow().isoformat()
        
        # 插入用户记录
        c.execute('''
            INSERT INTO users (
                username, 
                email, 
                hashed_password, 
                is_active, 
                created_at,
                role
            ) VALUES (?, ?, ?, ?, ?, ?)
        ''', (
            user.username,
            user.email,
            hashed_password,
            True,
            current_time,
            'user'
        ))
        
        conn.commit()
        
        # 获取创建的用户并验证
        created_user = get_user_by_username(db_path, user.username)
        if created_user:
            # 验证密码是否正确存储
            if not created_user.check_password(user.password):
                print("Warning: Password verification failed for newly created user")
        
        return created_user
        
    except Exception as e:
        print(f"Error creating user: {str(e)}")
        conn.rollback()
        raise
    finally:
        conn.close()

def record_login(db_path: str, user_id: int, ip_address: str, user_agent: str):
    """记录用户登录"""
    conn = sqlite3.connect(db_path)
    c = conn.cursor()
    
    try:
        current_time = datetime.utcnow().isoformat()
        
        # 更新用户最后登录时间
        c.execute(
            'UPDATE users SET last_login = ? WHERE id = ?',
            (current_time, user_id)
        )
        
        # 记录登录历史
        c.execute(
            'INSERT INTO login_history (user_id, ip_address, user_agent) VALUES (?, ?, ?)',
            (user_id, ip_address, user_agent)
        )
        
        conn.commit()
    except Exception as e:
        print(f"Error recording login: {e}")
        conn.rollback()
    finally:
        conn.close() 