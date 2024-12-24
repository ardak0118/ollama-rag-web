from fastapi import FastAPI, HTTPException, File, UploadFile, Depends
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import httpx
import logging
import sqlite3
from datetime import datetime
from typing import List, Optional, Dict
import asyncio
from .document_processor import DocumentProcessor
import os
import json
from .rag_service import rag_service
from langchain_community.vectorstores import Chroma
from .auth.routes import auth_router, get_current_user
from .auth.database import init_db
from .auth.models import User
from .auth.utils import verify_token
from .pdf_processor import pdf_processor
from .auth.admin_routes import admin_router
from .knowledge_base.routes import kb_router

# 初始化文档处理器
doc_processor = DocumentProcessor()

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)

logger = logging.getLogger(__name__)

app = FastAPI()

# 开发环境允许的源
ALLOWED_ORIGINS = [
    "http://localhost:5173",
    "http://192.168.1.21:5173",  # 开发服务器
    "http://192.168.1.21",       # 生产环境
    "http://localhost"
]

# 配置 CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=ALLOWED_ORIGINS,  # 替换为具体的域名列表
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
    expose_headers=["*"]
)

# 数据库配置
DATABASE_URL = os.path.join(os.path.dirname(__file__), "chat_history.db")

# 确保数据库目录存在
os.makedirs(os.path.dirname(DATABASE_URL), exist_ok=True)

# 数据库初始化
def init_chat_db():
    """初始化聊天数据库"""
    try:
        conn = sqlite3.connect(DATABASE_URL)
        c = conn.cursor()
        
        # 统一的对话表
        c.execute('''
            CREATE TABLE IF NOT EXISTS conversations (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                conversation_id TEXT NOT NULL,
                message TEXT NOT NULL,
                role TEXT NOT NULL,
                model TEXT NOT NULL,
                kb_id INTEGER DEFAULT NULL,    -- 知识库ID，为空表示普通对话
                sources TEXT DEFAULT NULL,     -- 知识库引用源
                timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (kb_id) REFERENCES knowledge_bases (id)
            )
        ''')
        
        # 知识库表
        c.execute('''
            CREATE TABLE IF NOT EXISTS knowledge_bases (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL,
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        # 文档表
        c.execute('''
            CREATE TABLE IF NOT EXISTS documents (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                knowledge_base_id INTEGER NOT NULL,
                name TEXT NOT NULL,
                content TEXT NOT NULL,
                file_path TEXT,
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (knowledge_base_id) REFERENCES knowledge_bases (id)
            )
        ''')
        
        conn.commit()
        logger.info("Chat database initialized successfully")
    except Exception as e:
        logger.error(f"Error initializing chat database: {str(e)}")
        raise
    finally:
        if conn:
            conn.close()

# 在应用启动时执行初始化
@app.on_event("startup")
async def startup_event():
    """应用启动时的事件处理"""
    try:
        # 初始化认证数据库
        init_db()
        # 初始化聊天数据库
        init_chat_db()
        logger.info("All databases initialized successfully")
    except Exception as e:
        logger.error(f"Error during startup: {str(e)}")
        raise

# 添加认证路由
app.include_router(auth_router, prefix="/api/auth", tags=["auth"])

# Ollama API 配置
OLLAMA_API_URL = "http://localhost:11434/api/generate"
OLLAMA_MODEL = "qwen2.5:latest"

class ChatMessage(BaseModel):
    message: str
    model: str = "qwen2.5:latest"
    conversation_id: Optional[str] = None
    kb_id: Optional[int] = None

class ConversationResponse(BaseModel):
    conversation_id: str
    messages: List[dict]

class KnowledgeBase(BaseModel):
    name: str

class Document(BaseModel):
    name: str
    content: str

class ChatRequest(BaseModel):
    query: str
    kb_id: int
    model: str = "qwen2.5:latest"

def save_message(conversation_id: str, message: str, role: str, model: str, kb_id: Optional[int] = None, sources: List[Dict] = None):
    """统一的消息保存函数"""
    try:
        conn = sqlite3.connect(DATABASE_URL)
        c = conn.cursor()
        
        if kb_id:
            # 保存知识库对话消息
            c.execute('''
                INSERT INTO rag_conversations 
                (conversation_id, message, role, model, kb_id, sources, timestamp)
                VALUES (?, ?, ?, ?, ?, ?, CURRENT_TIMESTAMP)
            ''', (conversation_id, message, role, model, kb_id, json.dumps(sources or [])))
        else:
            # 保存普通对话消息
            c.execute('''
                INSERT INTO conversations 
                (conversation_id, message, role, model, timestamp)
                VALUES (?, ?, ?, ?, CURRENT_TIMESTAMP)
            ''', (conversation_id, message, role, model))
            
        conn.commit()
        logger.info(f"Message saved successfully for conversation {conversation_id}")
    except Exception as e:
        logger.error(f"Error saving message: {str(e)}")
        raise
    finally:
        if conn:
            conn.close()

@app.get("/api/conversations")
async def get_conversations(current_user: User = Depends(get_current_user)):
    """获取所有对话历史，包括普通对话和知识库对话"""
    try:
        conn = sqlite3.connect(DATABASE_URL)
        c = conn.cursor()
        
        # 获取所有对话（普通对话和知识库对话）
        c.execute('''
            SELECT 
                conversation_id,
                kb_id,
                MAX(timestamp) as last_time,
                MIN(CASE WHEN role = 'user' THEN message ELSE NULL END) as first_message
            FROM conversations 
            GROUP BY conversation_id
            
            UNION ALL
            
            SELECT 
                conversation_id,
                kb_id,
                MAX(timestamp) as last_time,
                MIN(CASE WHEN role = 'user' THEN message ELSE NULL END) as first_message
            FROM rag_conversations 
            GROUP BY conversation_id
            
            ORDER BY last_time DESC
        ''')
        
        conversations = []
        for row in c.fetchall():
            conv_id, kb_id, timestamp, first_message = row
            
            # 构建对话信息
            title = first_message[:30] + "..." if first_message else "新对话"
            
            conversations.append({
                "id": conv_id,
                "title": title,
                "type": "rag" if kb_id else "normal",
                "kb_id": kb_id,
                "timestamp": timestamp
            })
        
        return {"conversations": conversations}
        
    except Exception as e:
        logger.error(f"Error getting conversations: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"Error getting conversations: {str(e)}"
        )
    finally:
        if conn:
            conn.close()

@app.get("/api/conversations/{conversation_id}")
async def get_conversation(conversation_id: str, current_user: User = Depends(get_current_user)):
    """获取特定对话的所有消息"""
    try:
        conn = sqlite3.connect(DATABASE_URL)
        c = conn.cursor()
        
        # 首先检查是哪种类型的对话
        c.execute('SELECT COUNT(*) FROM rag_conversations WHERE conversation_id = ?', (conversation_id,))
        is_rag = c.fetchone()[0] > 0
        
        if is_rag:
            # 获取知识库对话消息
            c.execute('''
                SELECT message, role, model, sources, timestamp, kb_id
                FROM rag_conversations
                WHERE conversation_id = ?
                ORDER BY timestamp
            ''', (conversation_id,))
            messages = [{
                "content": msg[0],
                "role": msg[1],
                "model": msg[2],
                "sources": json.loads(msg[3]) if msg[3] else [],
                "timestamp": msg[4],
                "kb_id": msg[5]
            } for msg in c.fetchall()]
        else:
            # 获取普通对话消息
            c.execute('''
                SELECT message, role, model, timestamp
                FROM conversations
                WHERE conversation_id = ?
                ORDER BY timestamp
            ''', (conversation_id,))
            messages = [{
                "content": msg[0],
                "role": msg[1],
                "model": msg[2],
                "timestamp": msg[3]
            } for msg in c.fetchall()]
        
        return {
            "conversation_id": conversation_id,
            "messages": messages,
            "type": "rag" if is_rag else "normal"
        }
        
    except Exception as e:
        logger.error(f"Error getting conversation: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"Error getting conversation: {str(e)}"
        )
    finally:
        if conn:
            conn.close()

@app.delete("/api/conversations/{conversation_id}")
async def delete_conversation(conversation_id: str):
    """删除对话（支持普通对话和知识库对话）"""
    try:
        conn = sqlite3.connect(DATABASE_URL)
        c = conn.cursor()
        
        # 删除普通对话
        c.execute('DELETE FROM conversations WHERE conversation_id = ?', (conversation_id,))
        
        # 删除知识库对话
        c.execute('DELETE FROM rag_conversations WHERE conversation_id = ?', (conversation_id,))
        
        conn.commit()
        return {"status": "success", "message": "Conversation deleted"}
    except Exception as e:
        logger.error(f"Error deleting conversation: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"Error deleting conversation: {str(e)}"
        )
    finally:
        if conn:
            conn.close()

async def check_model_availability(model_name: str = None) -> bool:
    """检查指定模型是否可用"""
    try:
        async with httpx.AsyncClient(timeout=5.0) as client:
            response = await client.get("http://localhost:11434/api/tags")
            if response.status_code == 200:
                data = response.json()
                if "models" in data:
                    available_models = [
                        model["name"] 
                        for model in data["models"] 
                        if isinstance(model, dict) and "name" in model
                    ]
                    if model_name:
                        return model_name in available_models
                    return len(available_models) > 0
            return False
    except Exception as e:
        logger.error(f"Error checking model availability: {e}")
        return False

@app.get("/api/models")
async def get_models():
    """获取可用的模型列表"""
    logger.info("Getting models list from Ollama...")
    try:
        async with httpx.AsyncClient(timeout=5.0) as client:
            try:
                # 使用正确的 Ollama API 端点
                response = await client.get("http://localhost:11434/api/tags")
                if response.status_code == 200:
                    data = response.json()
                    logger.info(f"Raw Ollama response: {data}")
                    
                    # 从 Ollama 响应中提取模型列表
                    if "models" in data:
                        models = []
                        for model in data["models"]:
                            if isinstance(model, dict) and "name" in model:
                                models.append(model["name"])
                        
                        logger.info(f"Available models from Ollama: {models}")
                        if models:  # 如果成功获取到模型列表
                            return {"models": models}
                    
                    logger.warning("No models found in Ollama response, using default list")
            except Exception as e:
                logger.error(f"Error connecting to Ollama: {str(e)}")
        
        # 如果无法从 Ollama 获取模型列表，使用本地已知的模型列表
        default_models = await get_local_models()
        logger.info(f"Using default models: {default_models}")
        return {"models": default_models}
    
    except Exception as e:
        logger.error(f"Error in get_models: {str(e)}")
        return {"models": ["qwen2.5:latest"]}  # 最后的后备选项

async def get_local_models():
    """获取本地已知的模型列表"""
    try:
        # 尝试从本地文件获取模型列表
        models_file = os.path.join(os.path.dirname(__file__), "models.json")
        if os.path.exists(models_file):
            with open(models_file, 'r', encoding='utf-8') as f:
                return json.load(f)
    except Exception as e:
        logger.error(f"Error reading local models file: {str(e)}")
    
    # 默认的模型列表
    return [
        "qwen:7b",
        "qwen:14b",
        "qwen:72b",
        "qwen:latest",
        "llama2:7b",
        "llama2:13b",
        "llama2:70b",
        "codellama:7b",
        "codellama:13b",
        "codellama:34b",
        "mistral:7b",
        "mixtral:8x7b",
        "neural-chat:7b",
        "yi:6b",
        "yi:34b"
    ]

@app.get("/health")
async def health_check():
    logger.info("Health check endpoint called")
    try:
        model_available = await check_model_availability()
        return {
            "status": "healthy",
            "message": "API is running",
            "model_available": model_available
        }
    except Exception as e:
        logger.error(f"Health check failed: {e}")
        return {
            "status": "unhealthy",
            "error": str(e)
        }

@app.get("/")
async def root():
    return {"message": "API is running"}

@app.post("/api/chat")
async def chat(chat_message: ChatMessage, current_user: User = Depends(get_current_user)):
    """统一的对话接口"""
    try:
        if not chat_message.conversation_id:
            chat_message.conversation_id = datetime.now().strftime("%Y%m%d_%H%M%S")

        # 保存用户消息
        save_message(
            chat_message.conversation_id,
            chat_message.message,
            "user",
            chat_message.model,
            chat_message.kb_id
        )

        # 根据是否有知识库ID决定使用哪种对话模式
        if chat_message.kb_id:
            # 使用 RAG 服务
            result = await rag_service.process_rag_request(
                query=chat_message.message,
                kb_id=chat_message.kb_id,
                model=chat_message.model
            )
            response = result["answer"]
            sources = result.get("sources", [])
        else:
            # 普通 LLM 对话
            async with httpx.AsyncClient(timeout=30.0) as client:
                ollama_response = await client.post(
                    "http://localhost:11434/api/generate",
                    json={
                        "model": chat_message.model,
                        "prompt": chat_message.message,
                        "stream": False
                    }
                )
                result = ollama_response.json()
                response = result.get("response", "")
                sources = []

        # 保存 AI 响应
        save_message(
            chat_message.conversation_id,
            response,
            "assistant",
            chat_message.model,
            chat_message.kb_id,
            sources
        )

        return {
            "response": response,
            "conversation_id": chat_message.conversation_id,
            "sources": sources
        }

    except Exception as e:
        logger.error(f"Error in chat: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"Error processing chat: {str(e)}"
        )

@app.get("/api/knowledge-base")
async def get_knowledge_bases():
    """获取所有知识库"""
    conn = sqlite3.connect(DATABASE_URL)
    c = conn.cursor()
    
    # 获取知识库列表及其文档数量
    c.execute('''
        SELECT kb.id, kb.name, COUNT(d.id) as doc_count
        FROM knowledge_bases kb
        LEFT JOIN documents d ON kb.id = d.knowledge_base_id
        GROUP BY kb.id
        ORDER BY kb.created_at DESC
    ''')
    
    results = c.fetchall()
    conn.close()
    
    return {
        "knowledge_bases": [
            {
                "id": row[0],
                "name": row[1],
                "documentCount": row[2]
            }
            for row in results
        ]
    }

@app.post("/api/knowledge-base")
async def create_knowledge_base(kb: KnowledgeBase):
    """创建知识库"""
    try:
        conn = sqlite3.connect(DATABASE_URL)
        c = conn.cursor()
        
        c.execute(
            'INSERT INTO knowledge_bases (name) VALUES (?)',
            (kb.name,)
        )
        
        kb_id = c.lastrowid
        conn.commit()
        
        return {
            "id": kb_id,
            "name": kb.name,
            "documentCount": 0
        }
    except Exception as e:
        logger.error(f"Error creating knowledge base: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"Error creating knowledge base: {str(e)}"
        )
    finally:
        if conn:
            conn.close()

@app.put("/api/knowledge-base/{kb_id}")
async def update_knowledge_base(kb_id: int, kb: KnowledgeBase):
    """更新知识库"""
    conn = sqlite3.connect(DATABASE_URL)
    c = conn.cursor()
    
    c.execute(
        'UPDATE knowledge_bases SET name = ? WHERE id = ?',
        (kb.name, kb_id)
    )
    
    conn.commit()
    conn.close()
    
    return {"status": "success"}

@app.delete("/api/knowledge-base/{kb_id}")
async def delete_knowledge_base(kb_id: int):
    """删除知识库"""
    conn = sqlite3.connect(DATABASE_URL)
    c = conn.cursor()
    
    # 首先删除相关的文档
    c.execute('DELETE FROM documents WHERE knowledge_base_id = ?', (kb_id,))
    # 然后删除知识库
    c.execute('DELETE FROM knowledge_bases WHERE id = ?', (kb_id,))
    
    conn.commit()
    conn.close()
    
    return {"status": "success"}

@app.post("/api/knowledge-base/{kb_id}/upload")
async def upload_document(kb_id: int, file: UploadFile = File(...)):
    """上传文档到知识库"""
    try:
        logger.info(f"Processing upload for kb_id: {kb_id}, file: {file.filename}")
        
        # 验证知识库是否存在
        conn = sqlite3.connect(DATABASE_URL)
        c = conn.cursor()
        c.execute('SELECT id FROM knowledge_bases WHERE id = ?', (kb_id,))
        if not c.fetchone():
            raise HTTPException(
                status_code=404,
                detail=f"Knowledge base {kb_id} not found"
            )

        # 处理 PDF 文件
        if file.filename.lower().endswith('.pdf'):
            # 保存文件并获取内容
            result = await pdf_processor.save_pdf(file)
            logger.info(f"PDF saved: {result['filename']}")
            
            # 存文档记录到数据库
            c.execute('''
                INSERT INTO documents (knowledge_base_id, name, content, file_path)
                VALUES (?, ?, ?, ?)
            ''', (kb_id, result['filename'], result['content'], result['path']))
            
            doc_id = c.lastrowid
            conn.commit()
            logger.info(f"Document record created with id: {doc_id}")

            # 处理向量存储
            try:
                await doc_processor.process_document(
                    result['path'],
                    result['filename'],
                    kb_id
                )
                logger.info("Vector storage processing completed")
            except Exception as e:
                logger.error(f"Error processing vector storage: {str(e)}")
                # 继续处理，即使向量存储失败
            
            # 验证文档是否成功存储到向量数据库
            docs = rag_service.vector_store.get(
                where={"kb_id": kb_id}
            )
            logger.info(f"Verified document storage: found {len(docs['ids'])} documents for kb_id {kb_id}")
            
            return {
                "message": "Document uploaded and indexed successfully",
                "id": doc_id,
                "filename": result['filename'],
                "vector_count": len(docs['ids'])
            }
        else:
            raise HTTPException(
                status_code=400,
                detail="Only PDF files are supported"
            )

    except Exception as e:
        logger.error(f"Error uploading document: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"Error uploading document: {str(e)}"
        )
    finally:
        if conn:
            conn.close()

@app.get("/api/knowledge-base/{kb_id}/documents/{doc_id}")
async def get_document(
    kb_id: int,
    doc_id: int,
    current_user: User = Depends(get_current_user)
):
    """获取文档内容"""
    try:
        conn = sqlite3.connect(DATABASE_URL)
        c = conn.cursor()
        
        # 获取文档信息
        c.execute('''
            SELECT name, content, file_path 
            FROM documents 
            WHERE id = ? AND knowledge_base_id = ?
        ''', (doc_id, kb_id))
        
        doc = c.fetchone()
        if not doc:
            raise HTTPException(
                status_code=404,
                detail="Document not found"
            )
            
        name, content, file_path = doc
        
        # 如果是 PDF 文件，重读取内容
        if name.lower().endswith('.pdf') and file_path and os.path.exists(file_path):
            try:
                logger.info(f"Reading PDF content from: {file_path}")
                content = pdf_processor.get_pdf_content(file_path)
                logger.info(f"Successfully read PDF content, length: {len(content)}")
            except Exception as e:
                logger.error(f"Error reading PDF content: {str(e)}")
                # 如果读取失败，使用数据库中存储的内容
                logger.info("Falling back to stored content")
        
        return {
            "name": name,
            "content": content,
            "is_pdf": name.lower().endswith('.pdf')
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting document: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"Error getting document: {str(e)}"
        )
    finally:
        if conn:
            conn.close()

@app.get("/api/knowledge-base/{kb_id}/documents")
async def get_documents(kb_id: int):
    """获取知识库的所有文档"""
    try:
        conn = sqlite3.connect(DATABASE_URL)
        c = conn.cursor()
        
        # 获取文档列表
        c.execute('''
            SELECT id, name, created_at 
            FROM documents 
            WHERE knowledge_base_id = ?
            ORDER BY created_at DESC
        ''', (kb_id,))
        
        documents = [{
            "id": row[0],
            "name": row[1],
            "created_at": row[2]
        } for row in c.fetchall()]
        
        return {
            "documents": documents
        }
    except Exception as e:
        logger.error(f"Error getting documents: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"Error getting documents: {str(e)}"
        )
    finally:
        if conn:
            conn.close()

@app.delete("/api/knowledge-base/{kb_id}/documents/{doc_id}")
async def delete_document(kb_id: int, doc_id: int):
    """删除文档"""
    conn = sqlite3.connect(DATABASE_URL)
    c = conn.cursor()
    
    c.execute(
        'DELETE FROM documents WHERE id = ? AND knowledge_base_id = ?',
        (doc_id, kb_id)
    )
    
    conn.commit()
    conn.close()
    
    return {"status": "success"}

@app.post("/api/chat/upload")
async def upload_file_for_chat(file: UploadFile = File(...)):
    """处理上传文并返回内容"""
    try:
        # 创建临时目录
        temp_dir = os.path.join(os.path.dirname(__file__), "temp")
        os.makedirs(temp_dir, exist_ok=True)
        
        # 存上传的文件到临时目录
        file_path = os.path.join(temp_dir, file.filename)
        try:
            content = await file.read()
            with open(file_path, "wb") as buffer:
                buffer.write(content)
            
            # 根据文件类型处理内容
            if file.filename.lower().endswith('.pdf'):
                text_content = "\n".join(doc_processor.extract_text_from_pdf(file_path))
            elif file.filename.lower().endswith('.txt'):
                with open(file_path, 'r', encoding='utf-8') as f:
                    text_content = f.read()
            elif file.filename.lower().endswith(('.doc', '.docx')):
                # 如果需要处理 Word 文档，需要添加相应的处理逻辑
                text_content = "暂不支持 Word 文档格式"
            else:
                text_content = "不支持的文件格式"
            
            return {
                "status": "success",
                "content": text_content,
                "filename": file.filename
            }
            
        except Exception as e:
            logger.error(f"Error processing file content: {str(e)}")
            raise HTTPException(
                status_code=500,
                detail=f"Error processing file content: {str(e)}"
            )
        finally:
            # 清理临时文件
            if os.path.exists(file_path):
                try:
                    os.remove(file_path)
                except Exception as e:
                    logger.error(f"Error removing temp file: {str(e)}")
                
    except Exception as e:
        logger.error(f"Error handling file upload: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"Error handling file upload: {str(e)}"
        )

# RAG 相关接口
@app.post("/api/rag/search")
async def search_documents(query: str, kb_id: int = None):
    """搜索相关文档"""
    try:
        results = await doc_processor.search_similar_chunks(query, kb_id)
        return {
            "status": "success",
            "results": results
        }
    except Exception as e:
        logger.error(f"Error searching documents: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"Error searching documents: {str(e)}"
        )

# 添加新的请求模型
class RAGChatMessage(BaseModel):
    message: str
    model: str = "qwen2.5:latest"
    conversation_id: Optional[str] = None
    kb_id: int

def save_rag_message(conversation_id: str, message: str, role: str, model: str, kb_id: int, sources: List[str] = None):
    """保存 RAG 对话消息"""
    try:
        conn = sqlite3.connect(DATABASE_URL)
        c = conn.cursor()
        c.execute('''
            INSERT INTO rag_conversations (conversation_id, message, role, model, kb_id, sources)
            VALUES (?, ?, ?, ?, ?, ?)
        ''', (conversation_id, message, role, model, kb_id, json.dumps(sources or [])))
        conn.commit()
        logger.info(f"RAG message saved successfully for conversation {conversation_id}")
    except Exception as e:
        logger.error(f"Error saving RAG message: {str(e)}")
        raise
    finally:
        if conn:
            conn.close()

@app.post("/api/rag/chat")
async def rag_chat(
    chat_message: RAGChatMessage,
    current_user: User = Depends(get_current_user)  # 添加用户认证
):
    """基于知识库的对话"""
    logger.info(f"User {current_user.username} sent message: {chat_message.message}")
    logger.info(f"Received RAG chat message: {chat_message.message}, model: {chat_message.model}, kb_id: {chat_message.kb_id}")
    try:
        # 1. 检查知识库是否存在
        conn = sqlite3.connect(DATABASE_URL)
        c = conn.cursor()
        c.execute('SELECT id FROM knowledge_bases WHERE id = ?', (chat_message.kb_id,))
        if not c.fetchone():
            raise HTTPException(
                status_code=404,
                detail=f"Knowledge base with id {chat_message.kb_id} not found"
            )
        
        # 2. 使用 RAG 服务处理请求
        try:
            result = await rag_service.process_rag_request(
                query=chat_message.message,
                kb_id=chat_message.kb_id,
                model=chat_message.model
            )
            
            # 3. 保存对话记录
            if not chat_message.conversation_id:
                chat_message.conversation_id = datetime.now().strftime("%Y%m%d_%H%M%S")
            
            # 保存用户消息
            save_rag_message(
                chat_message.conversation_id,
                chat_message.message,
                "user",
                chat_message.model,
                chat_message.kb_id,
                []
            )
            
            # 保存 AI 响应
            save_rag_message(
                chat_message.conversation_id,
                result["answer"],
                "assistant",
                chat_message.model,
                chat_message.kb_id,
                result.get("sources", [])
            )
            
            # 4. 返回结果
            return {
                "response": result["answer"],
                "conversation_id": chat_message.conversation_id,
                "sources": result.get("sources", [])
            }
            
        except Exception as e:
            logger.error(f"Error processing RAG request: {str(e)}")
            logger.exception(e)  # 添加详细的错误日志
            raise HTTPException(
                status_code=500,
                detail=f"Error processing RAG request: {str(e)}"
            )
            
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error in RAG chat: {str(e)}")
        logger.exception(e)  # 添加详细的错误日志
        raise HTTPException(
            status_code=500,
            detail=f"Error in RAG chat: {str(e)}"
        )
    finally:
        if conn:
            conn.close()

@app.get("/api/rag/documents/{kb_id}")
async def get_kb_documents(
    kb_id: int,
    current_user: User = Depends(get_current_user)  # 添加用户认证
):
    """知识库中的所有文档"""
    logger.info(f"User {current_user.username} accessing documents for kb_id: {kb_id}")
    try:
        conn = sqlite3.connect(DATABASE_URL)
        c = conn.cursor()
        
        # 获取文档列表
        c.execute('''
            SELECT id, name, content, created_at
            FROM documents
            WHERE knowledge_base_id = ?
            ORDER BY created_at DESC
        ''', (kb_id,))
        
        documents = [{
            "id": row[0],
            "name": row[1],
            "content": row[2],
            "created_at": row[3]
        } for row in c.fetchall()]
        
        return {
            "status": "success",
            "documents": documents
        }
    except Exception as e:
        logger.error(f"Error getting documents: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"Error getting documents: {str(e)}"
        )
    finally:
        if conn:
            conn.close()

@app.delete("/api/rag/documents/{kb_id}/{doc_id}")
async def delete_kb_document(
    kb_id: int, 
    doc_id: int,
    current_user: User = Depends(get_current_user)  # 添加用户认证
):
    """删除知识库中的文档"""
    logger.info(f"User {current_user.username} deleting document {doc_id} from kb_id: {kb_id}")
    try:
        # 从向量数据库中删除
        await doc_processor.delete_kb_documents(kb_id)
        
        # 从 SQLite 中删除
        conn = sqlite3.connect(DATABASE_URL)
        c = conn.cursor()
        c.execute(
            'DELETE FROM documents WHERE id = ? AND knowledge_base_id = ?',
            (doc_id, kb_id)
        )
        conn.commit()
        
        return {"status": "success"}
    except Exception as e:
        logger.error(f"Error deleting document: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"Error deleting document: {str(e)}"
        )
    finally:
        if conn:
            conn.close()

@app.get("/api/rag/chat/history/{kb_id}")
async def get_rag_conversations(
    kb_id: int,
    current_user: User = Depends(get_current_user)  # 添加用户认证
):
    """获取知识库的所有 RAG 对话"""
    logger.info(f"User {current_user.username} accessing chat history for kb_id: {kb_id}")
    try:
        conn = sqlite3.connect(DATABASE_URL)
        c = conn.cursor()
        
        # 获取该知识库的所有对话
        c.execute('''
            SELECT DISTINCT conversation_id, message, timestamp
            FROM rag_conversations
            WHERE kb_id = ? AND role = 'user'
            GROUP BY conversation_id
            ORDER BY timestamp DESC
        ''', (kb_id,))
        
        conversations = []
        for row in c.fetchall():
            conversations.append({
                "id": row[0],
                "title": row[1][:50] + "..." if len(row[1]) > 50 else row[1],
                "timestamp": row[2]
            })
        
        return {
            "status": "success",
            "histories": conversations
        }
    except Exception as e:
        logger.error(f"Error getting RAG conversations: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"Error getting RAG conversations: {str(e)}"
        )
    finally:
        if conn:
            conn.close()

@app.get("/api/rag/chat/messages/{conversation_id}")
async def get_rag_conversation_messages(
    conversation_id: str,
    current_user: User = Depends(get_current_user)  # 添加用户认证
):
    """获取特定 RAG 对话的所有消息"""
    logger.info(f"User {current_user.username} accessing messages for conversation: {conversation_id}")
    try:
        conn = sqlite3.connect(DATABASE_URL)
        c = conn.cursor()
        
        c.execute('''
            SELECT message, role, model, sources, timestamp
            FROM rag_conversations
            WHERE conversation_id = ?
            ORDER BY timestamp
        ''', (conversation_id,))
        
        messages = [{
            "content": row[0],
            "role": row[1],
            "model": row[2],
            "sources": json.loads(row[3]) if row[3] else [],
            "timestamp": row[4]
        } for row in c.fetchall()]
        
        return {
            "status": "success",
            "messages": messages
        }
    except Exception as e:
        logger.error(f"Error getting RAG conversation messages: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"Error getting RAG conversation messages: {str(e)}"
        )
    finally:
        if conn:
            conn.close()

@app.delete("/api/rag/chat/{conversation_id}")
async def delete_rag_conversation(
    conversation_id: str,
    current_user: User = Depends(get_current_user)  # 添加用户认证
):
    """删除特定的 RAG 对话"""
    logger.info(f"User {current_user.username} deleting conversation: {conversation_id}")
    try:
        conn = sqlite3.connect(DATABASE_URL)
        c = conn.cursor()
        
        # 先检查对话是否存在
        c.execute('SELECT COUNT(*) FROM rag_conversations WHERE conversation_id = ?', (conversation_id,))
        if c.fetchone()[0] == 0:
            raise HTTPException(
                status_code=404,
                detail=f"Conversation {conversation_id} not found"
            )
        
        # 删除对话
        c.execute('DELETE FROM rag_conversations WHERE conversation_id = ?', (conversation_id,))
        conn.commit()
        
        return {
            "status": "success",
            "message": f"Conversation {conversation_id} deleted successfully"
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error deleting RAG conversation: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"Error deleting conversation: {str(e)}"
        )
    finally:
        if conn:
            conn.close()

@app.put("/api/knowledge-base/{kb_id}/documents/{doc_id}")
async def update_document(
    kb_id: int,
    doc_id: int,
    content: dict,
    current_user: User = Depends(get_current_user)
):
    """更新文档内容"""
    try:
        logger.info(f"Updating document {doc_id} in knowledge base {kb_id}")
        logger.info(f"New content length: {len(content.get('content', ''))}")
        
        conn = sqlite3.connect(DATABASE_URL)
        c = conn.cursor()
        
        # 检查文档是否存在
        c.execute('''
            SELECT id, name, file_path 
            FROM documents 
            WHERE id = ? AND knowledge_base_id = ?
        ''', (doc_id, kb_id))
        
        doc = c.fetchone()
        if not doc:
            raise HTTPException(
                status_code=404,
                detail="Document not found"
            )
            
        # 更新文档内容
        c.execute('''
            UPDATE documents 
            SET content = ? 
            WHERE id = ? AND knowledge_base_id = ?
        ''', (content['content'], doc_id, kb_id))
        
        conn.commit()
        
        # 如果是 PDF 文件，同时更新文件内容
        if doc[2] and doc[1].lower().endswith('.pdf'):
            try:
                # 更新 PDF 文件内容
                with open(doc[2], 'w', encoding='utf-8') as f:
                    f.write(content['content'])
            except Exception as e:
                logger.error(f"Error updating PDF file: {str(e)}")
                # 继续处理，即使 PDF 文件更新失败
        
        # 重新处理向量存储
        try:
            await doc_processor.process_document(
                doc_id,
                content['content'],
                kb_id,
                doc[1]  # 使用原始文件名
            )
            logger.info("Vector store updated successfully")
        except Exception as e:
            logger.error(f"Error updating vector store: {str(e)}")
            # 继续处理，即使向��存储更新失败
        
        return {
            "message": "Document updated successfully",
            "document_id": doc_id
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error updating document: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"Error updating document: {str(e)}"
        )
    finally:
        if conn:
            conn.close()

@app.post("/api/knowledge-base/{kb_id}/documents/{doc_id}/reprocess")
async def reprocess_document(
    kb_id: int,
    doc_id: int,
    current_user: User = Depends(get_current_user)
):
    """重新处理文档的向量存储"""
    try:
        conn = sqlite3.connect(DATABASE_URL)
        c = conn.cursor()
        
        # 获取文档信息
        c.execute('''
            SELECT content, name, file_path 
            FROM documents 
            WHERE id = ? AND knowledge_base_id = ?
        ''', (doc_id, kb_id))
        
        doc = c.fetchone()
        if not doc:
            raise HTTPException(
                status_code=404,
                detail="Document not found"
            )
            
        content, name, file_path = doc
        
        # 重新处理文档
        if file_path and os.path.exists(file_path):
            # 如果有文件路径且文件存在，使用文件路径处理
            await doc_processor.process_document(
                file_path=file_path,
                file_name=name,
                kb_id=kb_id
            )
        else:
            # 否则使用内容处理
            await doc_processor.process_and_store(
                file_content=content,
                file_name=name,
                kb_id=kb_id
            )
        
        return {"message": "Document reprocessed successfully"}
        
    except Exception as e:
        logger.error(f"Error reprocessing document: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"Error reprocessing document: {str(e)}"
        )
    finally:
        if conn:
            conn.close()

@app.post("/api/upload")
async def upload_file(
    file: UploadFile, 
    kb_id: int,
    current_user: User = Depends(get_current_user)  # 添加用户认证
):
    logger.info(f"User {current_user.username} uploading file: {file.filename}")
    try:
        content = await file.read()
        content_str = content.decode('utf-8')
        
        logger.info(f"Processing file {file.filename} for kb_id {kb_id}")
        result = await doc_processor.process_and_store(content_str, file.filename, kb_id)
        logger.info(f"File processing result: {result}")
        
        return result
    except Exception as e:
        logger.error(f"Error processing file: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/chat")
async def chat(
    request: ChatRequest,
    current_user: User = Depends(get_current_user)  # 添加用户认证
):
    logger.info(f"User {current_user.username} sent chat request: {request.query}")
    try:
        logger.info(f"Chat request: {request.query} for kb_id {request.kb_id}")
        response = await rag_service.get_response(request.query, request.kb_id)
        logger.info(f"Chat response: {response[:100]}...")
        return {"response": response}
    except Exception as e:
        logger.error(f"Error in chat: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/debug/vector-store/{kb_id}")
async def debug_vector_store(
    kb_id: int,
    current_user: User = Depends(get_current_user)  # 添加用户认证
):
    """调试端点：检查向量存储中的文档"""
    logger.info(f"User {current_user.username} accessing debug endpoint for kb_id: {kb_id}")
    try:
        # 获取所有文档
        results = rag_service.vector_store.get(
            where={"kb_id": kb_id}
        )
        
        return {
            "total_documents": len(results["ids"]),
            "documents": [
                {
                    "id": id_,
                    "metadata": meta,
                    "content": content[:200] + "..."  # 只返回前200个字符
                }
                for id_, meta, content in zip(
                    results["ids"],
                    results["metadatas"],
                    results["documents"]
                )
            ]
        }
    except Exception as e:
        logger.error(f"Error in debug endpoint: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/rag/test")
async def test_rag_system(kb_id: int):
    """测试 RAG 系统的点"""
    try:
        # 1. 检查知识库是否存在
        conn = sqlite3.connect(DATABASE_URL)
        c = conn.cursor()
        c.execute('SELECT id, name FROM knowledge_bases WHERE id = ?', (kb_id,))
        kb = c.fetchone()
        if not kb:
            raise HTTPException(
                status_code=404,
                detail=f"Knowledge base {kb_id} not found"
            )
        
        # 2. 获取知识库中的文档
        c.execute('SELECT COUNT(*) FROM documents WHERE knowledge_base_id = ?', (kb_id,))
        doc_count = c.fetchone()[0]
        
        # 3. 检查向量存储中的文档
        vector_docs = rag_service.vector_store.get(
            where={"kb_id": kb_id}
        )
        vector_count = len(vector_docs["ids"]) if vector_docs else 0
        
        # 4. 执行测试查询
        test_queries = [
            "第十四条的内容是什么？",
            "铁路线路两侧杆塔要求是什么？",
            "关于树木等植物的规定有哪些？"
        ]
        
        test_results = []
        for query in test_queries:
            # 执行查询
            retrieved_docs = await rag_service.retrieve_documents(query, kb_id)
            
            # 获取回答
            response = await rag_service.process_rag_request(query, kb_id)
            
            test_results.append({
                "query": query,
                "retrieved_docs_count": len(retrieved_docs),
                "top_doc_score": retrieved_docs[0]["score"] if retrieved_docs else 0,
                "response": response.get("answer", ""),
                "confidence": response.get("confidence", "低")
            })
            
            # 添加详细的检索日志
            logger.info(f"Test query: {query}")
            logger.info(f"Retrieved {len(retrieved_docs)} documents")
            if retrieved_docs:
                logger.info(f"Top document score: {retrieved_docs[0]['score']}")
                logger.info(f"Top document preview: {retrieved_docs[0]['content'][:100]}...")
        
        return {
            "status": "success",
            "knowledge_base": {
                "id": kb[0],
                "name": kb[1],
                "document_count": doc_count,
                "vector_document_count": vector_count
            },
            "test_results": test_results,
            "system_status": {
                "vector_store_initialized": hasattr(rag_service.vector_store, "index"),
                "embeddings_model": rag_service.embeddings.model,
                "chunk_size": doc_processor.text_splitter.chunk_size,
                "chunk_overlap": doc_processor.text_splitter.chunk_overlap
            }
        }
        
    except Exception as e:
        logger.error(f"Error in RAG system test: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"Error testing RAG system: {str(e)}"
        )
    finally:
        if conn:
            conn.close()

# 修改 Ollama 代理接口
@app.get("/api/proxy/models")
async def proxy_models():
    """代理 Ollama 模型列表请求"""
    try:
        async with httpx.AsyncClient(timeout=10.0) as client:  # 增加超时时
            response = await client.get(
                "http://localhost:11434/api/tags",
                headers={
                    'Accept': 'application/json',
                    'Content-Type': 'application/json'
                }
            )
            
            if response.status_code == 200:
                data = response.json()
                # 处理返回的模型数据
                if isinstance(data, dict) and "models" in data:
                    models = []
                    for model in data["models"]:
                        if isinstance(model, dict) and "name" in model:
                            models.append(model["name"])
                    return {"models": models}
                else:
                    logger.warning("Unexpected response format from Ollama")
                    return {"models": ["qwen2.5:latest"]}
            else:
                logger.error(f"Failed to fetch models: {response.status_code}")
                return {"models": ["qwen2.5:latest"]}
                
    except Exception as e:
        logger.error(f"Error proxying models request: {e}")
        # 返回默认模型列表
        return {
            "models": [
                "qwen2.5:latest",
                "qwen:7b",
                "qwen:14b",
                "llama2:7b",
                "llama2:13b",
                "mistral:7b"
            ]
        }

@app.post("/api/proxy/generate")
async def proxy_generate(request: dict):
    """代理 Ollama 生成请求"""
    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            headers = {
                'Accept': 'application/json',
                'Content-Type': 'application/json'
            }
            
            # 确保请求包含必要的字段
            if not request.get("model"):
                request["model"] = "qwen2.5:latest"
            
            response = await client.post(
                "http://localhost:11434/api/generate",
                headers=headers,
                json=request
            )
            
            if response.status_code == 200:
                return response.json()
            else:
                logger.error(f"Ollama generate error: {response.status_code}")
                raise HTTPException(
                    status_code=response.status_code,
                    detail=f"Ollama generate error: {response.text}"
                )
                
    except httpx.TimeoutException:
        logger.error("Request to Ollama timed out")
        raise HTTPException(
            status_code=504,
            detail="Request to Ollama timed out"
        )
    except Exception as e:
        logger.error(f"Error proxying generate request: {e}")
        raise HTTPException(
            status_code=500,
            detail=str(e)
        )

# 添加一个健康检查端点
@app.get("/api/proxy/health")
async def check_ollama_health():
    """检查 Ollama 服务是可用"""
    try:
        async with httpx.AsyncClient(timeout=5.0) as client:
            response = await client.get("http://localhost:11434/api/tags")
            return {
                "status": "healthy" if response.status_code == 200 else "unhealthy",
                "message": "Ollama service is running" if response.status_code == 200 else "Ollama service is not available"
            }
    except Exception as e:
        return {
            "status": "unhealthy",
            "message": f"Error connecting to Ollama: {str(e)}"
        }

# 添加管理员路由
app.include_router(
    admin_router,
    prefix="/api/admin",
    tags=["admin"]
)

# 注册知识库路由
app.include_router(
    kb_router,
    prefix="/api",
    tags=["knowledge-base"]
)

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000) 






