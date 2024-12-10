from typing import List, Dict, Any
import numpy as np
from langchain_community.embeddings import OllamaEmbeddings
from langchain_community.llms import Ollama
import logging

logger = logging.getLogger(__name__)

class HyDEOptimizer:
    def __init__(self, llm=None, embeddings=None):
        try:
            self.llm = llm or Ollama(
                base_url="http://localhost:11434",
                model="qwen2.5:latest"
            )
            self.embeddings = embeddings or OllamaEmbeddings(
                base_url="http://localhost:11434",
                model="qwen2.5:latest"
            )
        except Exception as e:
            logger.error(f"Error initializing HyDEOptimizer: {e}")
            raise
    
    def generate_hypothetical_answer(self, query: str) -> str:
        prompt = f"""基于以下问题，生成一个可能在相关文档中找到的假设性答案：
        问题：{query}
        假设答案："""
        try:
            return self.llm.predict(prompt)
        except Exception as e:
            logger.error(f"Error generating hypothetical answer: {e}")
            return query  # 如果生成失败，返回原始查询
    
    def optimize_query(self, query: str) -> np.ndarray:
        try:
            hypothetical_answer = self.generate_hypothetical_answer(query)
            return self.embeddings.embed_query(hypothetical_answer)
        except Exception as e:
            logger.error(f"Error optimizing query: {e}")
            return self.embeddings.embed_query(query)  # 如果优化失败，返回原始查询的向量

class HierarchicalIndexer:
    def __init__(self):
        try:
            self.llm = Ollama(
                base_url="http://localhost:11434",
                model="qwen2.5:latest"
            )
            self.embeddings = OllamaEmbeddings(
                base_url="http://localhost:11434",
                model="qwen2.5:latest"
            )
            self.summary_index = {}  # 第一级索引
            self.chunk_index = {}    # 第二级索引
        except Exception as e:
            logger.error(f"Error initializing HierarchicalIndexer: {e}")
            raise
    
    def create_document_summary(self, document: str) -> str:
        try:
            prompt = f"请总结以下文档的主要内容：\n{document[:2000]}..."
            return self.llm.predict(prompt)
        except Exception as e:
            logger.error(f"Error creating document summary: {e}")
            return document[:200]  # 如果生成摘要失败，返回文档开头
    
    def index_document(self, doc_id: str, document: str, chunks: List[str]):
        try:
            # 创建两级索引
            summary = self.create_document_summary(document)
            self.summary_index[doc_id] = {
                'summary': summary,
                'summary_vector': self.embeddings.embed_query(summary)
            }
            
            self.chunk_index[doc_id] = {
                'chunks': chunks,
                'chunk_vectors': [self.embeddings.embed_query(chunk) for chunk in chunks]
            }
        except Exception as e:
            logger.error(f"Error indexing document: {e}")
            raise
    
    def _search_summaries(self, query_vector: np.ndarray, top_k: int) -> List[str]:
        """在摘要级别搜索相关文档"""
        try:
            scores = {}
            for doc_id, data in self.summary_index.items():
                similarity = np.dot(query_vector, data['summary_vector'])
                scores[doc_id] = similarity
            
            return sorted(scores.keys(), key=lambda x: scores[x], reverse=True)[:top_k]
        except Exception as e:
            logger.error(f"Error searching summaries: {e}")
            return list(self.summary_index.keys())[:top_k]
    
    def _search_chunks(self, doc_id: str, query_vector: np.ndarray, top_k: int) -> List[str]:
        """在文档块级别搜索"""
        try:
            if doc_id not in self.chunk_index:
                return []
            
            chunks = self.chunk_index[doc_id]['chunks']
            chunk_vectors = self.chunk_index[doc_id]['chunk_vectors']
            
            scores = [np.dot(query_vector, vec) for vec in chunk_vectors]
            sorted_pairs = sorted(zip(chunks, scores), key=lambda x: x[1], reverse=True)
            
            return [chunk for chunk, _ in sorted_pairs[:top_k]]
        except Exception as e:
            logger.error(f"Error searching chunks: {e}")
            return []
    
    def search(self, query: str, top_k: int = 3) -> List[str]:
        """执行两级搜索"""
        try:
            query_vector = self.embeddings.embed_query(query)
            
            # 第一级搜索：找到相关文档
            relevant_docs = self._search_summaries(query_vector, top_k)
            
            # 第二级搜索：在相关文档中找到具体chunk
            results = []
            for doc_id in relevant_docs:
                chunks = self._search_chunks(doc_id, query_vector, top_k)
                results.extend(chunks)
            
            return results[:top_k]
        except Exception as e:
            logger.error(f"Error in search: {e}")
            return []