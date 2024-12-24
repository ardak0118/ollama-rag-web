from pdfminer.high_level import extract_pages
from pdfminer.layout import LTTextContainer
import logging
from typing import List, Dict, Any
from .text_splitter import MarkdownTextSplitter
from langchain_community.embeddings import OllamaEmbeddings
from langchain.vectorstores import Chroma
from langchain.schema.document import Document
import os
import json
import time
from langchain.text_splitter import RecursiveCharacterTextSplitter
import re
from .rag_optimizers import HierarchicalIndexer
import pdfplumber

logger = logging.getLogger(__name__)

class DocumentProcessor:
    def __init__(self):
        # 主分块器 - 用于较大的语义单位
        self.text_splitter = RecursiveCharacterTextSplitter(
            chunk_size=800,  # 增加主块大小以保持更多上下文
            chunk_overlap=200,  # 增加重叠以避免切分关键信息
            separators=[
                "\n\n",  # 首先按段落分割
                "\n",    # 然后按行分割
                "。",    # 中文句号
                "！",    # 感叹号
                "？",    # 问号
                "；",    # 分号
                "，",    # 逗号
                " ",    # 空格
                ""
            ],
            length_function=len,
        )
        
        # 子分块器 - 用于更细粒度的检索
        self.sub_splitter = RecursiveCharacterTextSplitter(
            chunk_size=200,
            chunk_overlap=50,
            separators=["。", "���", "？", "；", "，", " ", ""]
        )
        
        # 确保数据目录存在
        persist_directory = os.path.join(os.path.dirname(__file__), "data", "chroma")
        os.makedirs(persist_directory, exist_ok=True)
        
        # 初始化 Ollama Embeddings
        self.embeddings = OllamaEmbeddings(
            base_url="http://localhost:11434",
            model="qwen2.5:latest"
        )
        
        # 初始化 ChromaDB
        self.vector_store = Chroma(
            collection_name="document_collection",
            embedding_function=self.embeddings,
            persist_directory=persist_directory
        )
        
        self.hierarchical_indexer = HierarchicalIndexer()

    def extract_text_from_pdf(self, file_path: str, method: str = 'pdfminer') -> str:
        """从 PDF 文件中提取文本
        
        Args:
            file_path: PDF 文件路径
            method: 使用的提取方法，'pdfminer' 或 'pdfplumber'
        """
        try:
            if method == 'pdfminer':
                return self._extract_with_pdfminer(file_path)
            elif method == 'pdfplumber':
                return self._extract_with_pdfplumber(file_path)
            else:
                raise ValueError(f"Unsupported extraction method: {method}")
            
        except Exception as e:
            logger.error(f"Error extracting text from PDF: {str(e)}")
            raise

    def _extract_with_pdfminer(self, file_path: str) -> str:
        """使用 PDFMiner 提取文本"""
        text = ""
        with open(file_path, 'rb') as file:
            for page_layout in extract_pages(file):
                for element in page_layout:
                    if isinstance(element, LTTextContainer):
                        text += element.get_text() + "\n"
        return text

    def _extract_with_pdfplumber(self, file_path: str) -> str:
        """使用 PDFPlumber 提取文本"""
        text = ""
        with pdfplumber.open(file_path) as pdf:
            for page in pdf.pages:
                text += page.extract_text() + "\n"
        return text

    def clean_text(self, text: str) -> str:
        """增强的文本清洗"""
        try:
            # 1. 确保文本是字符串类型
            if not isinstance(text, str):
                text = str(text)
            
            # 2. 基础清理
            text = re.sub(r'\s+', ' ', text)
            text = text.strip()
            
            # 3. 规范化标点符号
            text = text.replace('。。。', '。').replace('！！！', '！')
            
            # 4. 移除特������符，但保留重要记
            text = re.sub(r'[^\w\s\u4e00-\u9fff。，！？；：""''（）《》、第一二三四五六七八九十百千万章节条]', '', text)
            
            # 5. 处理实体一致性
            entity_map = {
                "LLM": "大语言模型",
                "大模型": "大语言模型",
                # 添加更多实体映射
            }
            for k, v in entity_map.items():
                text = text.replace(k, v)
            
            return text
        except Exception as e:
            logger.error(f"Error in clean_text: {str(e)}")
            return text

    async def process_document(self, file_path: str, file_name: str, kb_id: int):
        """处理文档并存储到向量数据库"""
        try:
            logger.info(f"Processing document: {file_name} for kb_id: {kb_id}")
            
            # 根据文件类型选择不同的读取方式
            file_ext = os.path.splitext(file_name)[1].lower()
            
            if file_ext == '.pdf':
                # PDF文件处理
                content = self.extract_text_from_pdf(file_path)
            else:
                # 其他文本文件处理，使用二进制模式读取
                with open(file_path, 'rb') as f:
                    content = f.read()
                    # 尝试不同的编码
                    encodings = ['utf-8', 'gbk', 'gb2312', 'gb18030', 'big5']
                    decoded_content = None
                    
                    for encoding in encodings:
                        try:
                            decoded_content = content.decode(encoding)
                            logger.info(f"Successfully decoded with {encoding}")
                            break
                        except UnicodeDecodeError:
                            continue
                    
                    if decoded_content is None:
                        raise ValueError("Unable to decode file with any known encoding")
                    content = decoded_content

            # 清理文本
            content = self.clean_text(content)
            logger.debug(f"Cleaned content length: {len(content)}")
            
            # 分块处理
            chunks = self.text_splitter.split_text(content)
            logger.info(f"Split document into {len(chunks)} chunks")
            
            # 打印每个块的大小
            for i, chunk in enumerate(chunks):
                logger.debug(f"Chunk {i} size: {len(chunk)} characters")
            
            # 准备元数据
            metadatas = [{
                "kb_id": kb_id,
                "filename": file_name,
                "chunk_index": i,
                "source": file_name,
                "file_type": file_ext[1:].upper()
            } for i in range(len(chunks))]
            
            # 存储到向量数据库
            try:
                self.vector_store.add_texts(
                    texts=chunks,
                    metadatas=metadatas
                )
                self.vector_store.persist()
                logger.info(f"Successfully added {len(chunks)} chunks to vector store")
                
                # 验证存储
                result = self.vector_store.get(
                    where={"kb_id": kb_id}
                )
                logger.info(f"Verified storage: found {len(result['ids'])} documents for kb_id {kb_id}")
                
            except Exception as e:
                logger.error(f"Error storing in vector database: {str(e)}")
                raise
            
            # 创建分层索引
            self.hierarchical_indexer.index_document(
                doc_id=file_name,
                document=content,
                chunks=chunks
            )
            
            return True
            
        except Exception as e:
            logger.error(f"Error processing document: {str(e)}")
            raise

    async def search_similar_chunks(self, query: str, kb_id: int, top_k: int = 3) -> List[Dict[str, Any]]:
        """搜索相似的文本块"""
        try:
            logger.info(f"Searching for query: {query} in kb_id: {kb_id}")
            
            # 使用向量相似度搜索
            results = self.vector_store.similarity_search_with_relevance_scores(
                query,
                k=top_k,
                filter={"kb_id": kb_id}
            )
            
            # 处理结果
            processed_results = []
            for doc, score in results:
                if score >= 0.3:  # 相似度阈值
                    processed_results.append({
                        "content": doc.page_content,
                        "metadata": doc.metadata,
                        "score": score
                    })
                    logger.info(f"Found chunk with score {score}: {doc.page_content[:100]}...")
            
            return processed_results
        except Exception as e:
            logger.error(f"Error searching similar chunks: {str(e)}")
            raise

    async def delete_kb_documents(self, kb_id: int) -> Dict[str, str]:
        """删除知识库相关的所有文档"""
        try:
            logger.info(f"Deleting all documents for kb_id: {kb_id}")
            try:
                existing_docs = self.vector_store.get(
                    where={"kb_id": kb_id}
                )
                if existing_docs and existing_docs["ids"]:
                    self.vector_store.delete(ids=existing_docs["ids"])
            except Exception as e:
                logger.warning(f"No documents found to delete: {str(e)}")
            
            self.vector_store.persist()
            logger.info(f"Successfully deleted all documents for kb_id: {kb_id}")
            return {"status": "success"}
        except Exception as e:
            logger.error(f"Error deleting documents: {str(e)}")
            raise

    async def process_and_store(self, file_content: str, file_name: str, kb_id: int):
        """处理文件内容并存储"""
        try:
            # 创建临时目录
            temp_dir = os.path.join(os.path.dirname(__file__), "temp")
            os.makedirs(temp_dir, exist_ok=True)
            
            # 创建临时文件
            temp_file_path = os.path.join(temp_dir, file_name)
            
            try:
                # 保存内容到临时文件
                with open(temp_file_path, 'w', encoding='utf-8') as f:
                    f.write(file_content)
                
                # 处理文档
                result = await self.process_document(temp_file_path, file_name, kb_id)
                return result
                
            finally:
                # 清理临时文件
                if os.path.exists(temp_file_path):
                    os.remove(temp_file_path)
                    
        except Exception as e:
            logger.error(f"Error in process_and_store: {str(e)}")
            raise

# 创建全局实例
doc_processor = DocumentProcessor()