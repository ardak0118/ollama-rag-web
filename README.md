# Ollama RAG Web

一个基于 Ollama 的本地知识库问答系统，支持中文 PDF 文档处理和智能问答。

## 功能特点

- 📚 支持 PDF 文档上传和处理
- 🔍 基于 RAG (检索增强生成) 的智能问答
- 💡 支持多知识库管理
- 🎯 优化的文档检索算法
- 🔄 实时对话历史记录
- 📊 文档分块和向量化存储
- 🛡️ 用户认证和权限管理

## 技术栈

### 后端
- FastAPI
- Langchain
- Ollama
- ChromaDB
- PDFMiner/PDFPlumber
- SQLite

### 前端
- Vue.js
- Vite
- Tailwind CSS

## 系统要求

- Python 3.8+
- Node.js 16+
- Ollama
- 8GB+ RAM 建议
- 支持 CUDA 的 GPU (可选，但推荐)

## 快速开始

### 1. 安装 Ollama
## Linux/MacOS
curl -fsSL https://ollama.com/install.sh | sh
Windows
从 https://ollama.com/download 下载安装包

### 2. 下载模型
ollama run qwen2.5:latest

### 3. 后端设置
创建虚拟环境

python -m venv venv

source venv/bin/activate # Linux/MacOS

.\venv\Scripts\activate # Windows

安装依赖

cd backend
pip install -r requirements.txt

初始化数据库

python init_db.py

启动后端服务

python run.py

### 4. 前端设置
安装依赖

cd frontend

npm install

启动开发服务器

npm run dev

构建生产版本

npm run build

## 项目结构

ollama-rag-web/

├── backend/

│ ├── app/

│ │ ├── main.py # FastAPI 主应用

│ │ ├── document_processor.py # 文档处理

│ │ ├── rag_service.py # RAG 服务

│ │ ├── rag_optimizers.py # RAG 优化器

│ │ └── models.json # 模型配置

│ └── requirements.txt

├── frontend/

│ ├── src/

│ │ ├── components/ # Vue 组件

│ │ ├── router/ # 路由配置

│ │ └── utils/ # 工具函数

│ └── package.json

└── README.md


## 配置说明

### 后端配置

1. 数据库配置 (backend/app/config.py)
DATABASE_URL = "sqlite:///./knowledge_base.db"
2. Ollama 配置

### 前端配置

1. API 配置 (frontend/src/utils/api.js)
const API_BASE_URL = 'http://localhost:8000/api'

## 使用说明

1. 创建知识库
2. 上传 PDF 文档
3. 等待文档处理完成
4. 开始提问

## 注意事项

1. PDF 文档需要是可复制的文本格式
2. 大文件处理可能需要较长时间
3. 首次使用需要下载模型
4. 建议定期备份数据库

## 常见问题

1. 模型下载失败
   - 检查网络连接
   - 确认 Ollama 服务正常运行

2. 文档处理失败
   - 检查 PDF 格式
   - 确认文件编码正确

3. 向量存储异常
   - 检查磁盘空间
   - 确认权限设置

## 贡献指南

欢迎提交 Issue 和 Pull Request！

## 许可证

MIT License
