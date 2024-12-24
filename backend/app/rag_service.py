from typing import List, Dict, Any, Set, Optional, Tuple
import logging
from langchain_community.embeddings import OllamaEmbeddings
from langchain_community.vectorstores import Chroma
import os
import httpx
import json
import re
import jieba
import jieba.analyse
import jieba.posseg as pseg
from collections import defaultdict
from .text_splitter import MarkdownTextSplitter
import numpy as np
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity
from .time_manager import TimeManager

logger = logging.getLogger(__name__)

class RAGService:
    def __init__(self):
        try:
            self.embeddings = OllamaEmbeddings(
                base_url="http://localhost:11434",
                model="qwen2.5:latest"
            )
            
            persist_directory = os.path.join(os.path.dirname(__file__), "data", "chroma")
            os.makedirs(persist_directory, exist_ok=True)
            
            self.vector_store = Chroma(
                collection_name="document_collection",
                embedding_function=self.embeddings,
                persist_directory=persist_directory
            )
            
            # 初始化 TF-IDF 向量化器用于关键词匹配
            self.tfidf = TfidfVectorizer(
                token_pattern=r"(?u)\b\w+\b",
                ngram_range=(1, 2)
            )
            
            # 添加同义词字典
            self.synonym_dict = {
                # 职位相关
                "任命": {"任职", "委任", "担任", "就任", "上任", "履职", "入职"},
                "免职": {"撤职", "解职", "离任", "卸任", "去职", "辞职", "辞任"},
                "主管": {"负责人", "管理者", "领导", "主任", "经理", "处长"},
                
                # 时间相关
                "现在": {"目前", "当前", "如今", "此时", "眼下"},
                "以前": {"之前", "从前", "原先", "先前", "过去"},
                
                # 地点相关
                "地区": {"区域", "地带", "片区", "区段", "辖区"},
                "周边": {"附近", "邻近", "四周", "周围", "附近"},
                
                # 行为相关
                "实施": {"执行", "开展", "进行", "展开", "推行"},
                "管理": {"监管", "治理", "规范", "控制", "督导"},
                
                # 可以继续添加更多同义词组
            }
            
            # 加载自定义词典
            self.load_custom_dict()
            
            # 添加���名缓存
            self.person_names_cache = set()
            
            # 人名相关词
            self.person_related_words = {
                "任命", "担任", "履职", "就任", "主持", "负责", "分管",
                "调任", "升任", "兼任", "离任", "免职", "辞职", "退休",
                "同志", "先生", "女士", "主任", "局长", "站长", "段长"
            }
            
            # 更新同义词字典，添加人名相关
            self.synonym_dict.update({
                "任职": {"任命", "担任", "就任", "履新", "上任", "到任"},
                "离职": {"离任", "免职", "辞职", "退休", "调离", "卸任"},
                "领导": {"负责人", "主管", "领导人", "管理者", "主要负责人"},
            })
            
            # 添加通用问题模式
            self.general_questions = {
                r'你好[啊吗]?[?？]*',
                r'(?:请问)?你是谁[?？]*',
                r'(?:你能)?做什么[?？]*',
                r'(?:你)?有什么功能[?？]*',
                r'(?:你)?会干什么[?？]*',
                r'(?:你能)?帮我[做干]什么[?？]*',
                r'在吗[?？]*',
                r'可以聊天吗[?？]*'
            }
            
            # 添加文档分块和检索配置
            self.chunk_size = 500      # 文档分块大小
            self.chunk_overlap = 100   # 增加重叠大小，提高上下文连贯性
            self.top_k_chunks = 10     # 增加初始检索数量
            self.rerank_top_k = 5      # 保留最相关的5个文档
            
            # 添加文档相似度阈值
            self.similarity_threshold = 0.3  # 降低相似度阈值
            self.context_window = 3     # 增加上下文窗口大小
            
            # 添加缓存配置
            self.cache_size = 1000
            self.cache_ttl = 3600      # 缓存有效期（秒）
            
            # 添加提示模板
            self.prompt_template = """基于以下参考文档回答用户的问题。请注意：
1. 如果问题无法从参考文档中得到完整答案，请明确指出。
2. 回答要简洁明了，直接引用相关文档内容。
3. 如果需要补充说明，请明确区分哪些是来自文档的内容，哪些是补充解释。
4. 保持客观，不要添加主观判断。
5. 如果文档内容相互矛盾，请指出这一点。
6. 优先使用相关度更高的文档内容。
7. 确保回答的完整性和准确性。
8. 如果上传的知识库文档是任职名单类似的，知���库会有（20xx年x月xx日新疆维吾尔自治区第xx届人民代表大会常务委员会第xx次会议通过）这样的时间信息，请特别注意
9. 如果知识库有多个任职名单，请特别注意
10. 如果知识库有（20xx年x月xx日新疆维吾尔自治区第xx届人民代表大会常务委员会第xx次会议通过），该时间就是所有人员的任职或免职时间
11. 一个人可能会在多个任职名单中出现，请特别注意，并给出所有任职名单中该人员的任职或免职时间
12. 如果知识库文档有（本会议任免的名单从202X年X月XX日开始成效），该时间就是所有人员的任职或免职时间

参考文档：
{context}

    用户问题：{query}

请提供准确、完整的回答："""
            
            logger.info("RAG Service initialized with config: chunk_size=%d, overlap=%d, top_k=%d, rerank_top_k=%d",
                       self.chunk_size, self.chunk_overlap, self.top_k_chunks, self.rerank_top_k)
            
            # 初始化时间管理器
            self.time_manager = TimeManager()
            
        except Exception as e:
            logger.error(f"Error initializing RAG Service: {e}")
            raise

    def load_custom_dict(self):
        """加载自定义词典和实体"""
        # 添加自定义词典
        custom_words = [
            # 机构名称
            "铁路局", "运输企业", "公安机关", "铁路公安机关",
            # 职位名称
            "段长", "站长", "主任", "负责人",
            # 专业术语
            "建筑限界", "线路", "轨道", "道岔",
            # 设施设备
            "杆塔", "广告牌", "烟囱", "风机",
            # 可以继续添加更多词语
        ]
        
        for word in custom_words:
            jieba.add_word(word)

    def expand_query_with_synonyms(self, query: str) -> str:
        """使用同义词扩展查询"""
        words = jieba.lcut(query)
        expanded_words = set(words)
        
        # 添加同义词
        for word in words:
            for key, synonyms in self.synonym_dict.items():
                if word in synonyms or word == key:
                    expanded_words.update(synonyms)
                    expanded_words.add(key)
        
        return " ".join(expanded_words)

    def extract_entities(self, text: str) -> Dict[str, Set[str]]:
        """提取命名实体"""
        entities = {
            "person": set(),    # 人名
            "location": set(),  # 地名
            "time": set(),      # 时间
            "org": set(),       # 组织机构
            "position": set(),  # 职位
        }
        
        # 使用 jieba 词性标注
        words = pseg.cut(text)
        for word, flag in words:
            if flag == 'nr':  # 人名
                entities["person"].add(word)
            elif flag == 'ns':  # 地名
                entities["location"].add(word)
            elif flag == 'nt':  # 机构名
                entities["org"].add(word)
            elif flag == 'nz':  # 其他专名
                if word in ["主任", "段长", "站长", "负责人"]:
                    entities["position"].add(word)
        
        # 提取时间表达式
        time_patterns = [
            r'\d{4}年\d{1,2}月\d{1,2}日',
            r'\d{4}年\d{1,2}月',
            r'\d{4}年',
            r'第[一二三四五六七八九十]季度',
            r'[一二三四五六七八九十]+月',
        ]
        
        for pattern in time_patterns:
            matches = re.finditer(pattern, text)
            for match in matches:
                entities["time"].add(match.group())
        
        return entities

    def calculate_entity_match_score(self, query_entities: Dict[str, Set[str]], doc_entities: Dict[str, Set[str]]) -> float:
        """计算实体匹配得分"""
        if not query_entities or not doc_entities:
            return 0.0
        
        weights = {
            "person": 1.0,    # 人名权重
            "location": 0.8,  # 地名权重
            "time": 0.9,     # 时间权重
            "org": 0.7,      # 组织机构权重
            "position": 0.6,  # 职位权重
        }
        
        total_score = 0.0
        total_weight = 0.0
        
        for entity_type, weight in weights.items():
            query_set = query_entities.get(entity_type, set())
            doc_set = doc_entities.get(entity_type, set())
            
            if query_set:
                intersection = len(query_set & doc_set)
                union = len(query_set | doc_set)
                if union > 0:
                    score = (intersection / union) * weight
                    total_score += score
                    total_weight += weight
        
        return total_score / total_weight if total_weight > 0 else 0.0

    async def rewrite_query(self, query: str) -> str:
        """查询重写方法"""
        return query  # 暂时直接返回原始查询，确保基本功能正常

    def update_person_names_cache(self, text: str):
        """更新人名缓存"""
        words = pseg.cut(text)
        for word, flag in words:
            if flag == 'nr':  # 人名词性标记
                self.person_names_cache.add(word)
                # 处理可能的姓名变体（比如姓或名的单独出现）
                if len(word) >= 2:
                    self.person_names_cache.add(word[0])  # 添加姓氏
                    self.person_names_cache.add(word[1:])  # 添加名字

    def is_person_related_context(self, text: str) -> bool:
        """判断文本是否与人物相关"""
        return any(word in text for word in self.person_related_words)

    def calculate_person_relevance_score(self, query: str, doc_content: str) -> float:
        """计算人名相关性得分"""
        # 提取查询和文档中的人名
        query_words = pseg.cut(query)
        query_names = {word for word, flag in query_words if flag == 'nr'}
        
        # 检查缓存的人名
        query_names.update(name for name in self.person_names_cache if name in query)
        
        if not query_names:
            return 0.0
        
        score = 0.0
        for name in query_names:
            if name in doc_content:
                score += 1.0
                # 如果文档包含人名相关上下文，增加得分
                if self.is_person_related_context(doc_content):
                    score += 0.5
        
        return min(score / len(query_names), 1.0)

    async def retrieve_documents(self, query: str, kb_id: int) -> List[Dict]:
        """检索相关文档"""
        try:
            logger.info(f"Retrieving documents for query: '{query}' in kb_id: {kb_id}")
            
            # 检测是否是人物相关查询
            is_person_query = self.is_person_related_query(query)
            if is_person_query:
                logger.info("Detected person-related query, using specialized retrieval")
                # 提取人名
                words = pseg.cut(query)
                person_names = {word for word, flag in words if flag == 'nr'}
                logger.info(f"Extracted person names: {person_names}")
                
                # 扩展查询
                expanded_query = f"{query} {' '.join(person_names)} {' '.join(self.person_related_words)}"
                logger.info(f"Expanded query: '{expanded_query}'")
            else:
                expanded_query = self.expand_query(query)
                logger.info(f"Expanded query: '{expanded_query}'")

            # 初始检索
            results = self.vector_store.similarity_search_with_score(
                expanded_query,
                k=self.top_k_chunks,
                filter={"kb_id": kb_id}
            )
            
            logger.info(f"Initial vector search returned {len(results)} results")

            # 处理检索结果
            processed_results = []
            for doc, score in results:
                # 计算语义相似度
                semantic_score = self.calculate_similarity(query, doc.page_content)
                
                # 计算关键词匹配分数
                keyword_score = self.calculate_keyword_match_score(query, doc.page_content)
                
                # 计算上下文相关性
                context_score = 1.0 if is_person_query and any(name in doc.page_content for name in person_names) else 0.0
                
                # 计算最终分数
                final_score = (semantic_score + keyword_score + context_score) / 3
                
                # 记录文档详情
                logger.info("\nDocument details:")
                logger.info(f"Score: {final_score:.3f}")
                logger.info(f"Content: {doc.page_content}")
                logger.info(f"Source: {doc.metadata.get('source', 'Unknown')}")
                logger.info(f"Semantic score: {semantic_score:.3f}")
                logger.info(f"Keyword score: {keyword_score:.3f}")
                logger.info(f"Context score: {context_score:.3f}")
                logger.info("-" * 80)

                if final_score > self.similarity_threshold:
                    processed_results.append({
                        "content": doc.page_content,
                        "metadata": doc.metadata,
                        "score": final_score
                    })

            # 按相关性排序
            processed_results.sort(key=lambda x: x["score"], reverse=True)
            
            # 只保留最相关的文档
            final_results = processed_results[:self.rerank_top_k]
            
            # 记录最终选择的文档
            logger.info("\nFinal selected documents:")
            for i, doc in enumerate(final_results, 1):
                logger.info(f"\nDocument {i}:")
                logger.info(f"Score: {doc['score']:.3f}")
                logger.info(f"Content: {doc['content']}")
                logger.info(f"Source: {doc['metadata'].get('source', 'Unknown')}")
                logger.info("-" * 80)
            
            # 修复 f-string 语法
            scores_str = ", ".join(f"{doc['score']:.3f}" for doc in final_results)
            logger.info(f"\nRetrieved {len(final_results)} relevant documents with scores: {scores_str}")
            
            return final_results

        except Exception as e:
            logger.error(f"Error retrieving documents: {str(e)}", exc_info=True)
            return []

    def extract_person_names(self, text: str) -> Set[str]:
        """提取文本中的人名"""
        names = set()
        words = pseg.cut(text)
        for word, flag in words:
            if flag == 'nr':  # 人名词性标记
                names.add(word)
        return names

    def calculate_context_relevance(self, query: str, content: str) -> float:
        """计算上下文相关性"""
        try:
            # 1. 提取查询关键信息
            query_info = {
                "names": self.extract_person_names(query),
                "keywords": set(jieba.analyse.extract_tags(query, topK=5)),
                "time_words": {"现在", "目前", "当前"} & set(query)
            }
            
            # 2. 提取文档关键信息
            content_info = {
                "names": self.extract_person_names(content),
                "keywords": set(jieba.analyse.extract_tags(content, topK=10)),
                "dates": set(re.findall(r'\d{4}年\d{1,2}月\d{1,2}日|\d{4}年\d{1,2}月|\d{4}年', content))
            }
            
            # 3. 计算相关性分数
            scores = []
            
            # 人名匹配
            if query_info["names"]:
                name_score = len(query_info["names"] & content_info["names"]) / len(query_info["names"])
                scores.append(name_score * 2)  # 加权
            
            # 关键词匹配
            if query_info["keywords"]:
                keyword_score = len(query_info["keywords"] & content_info["keywords"]) / len(query_info["keywords"])
                scores.append(keyword_score)
            
            # 时间相关性
            if query_info["time_words"] and content_info["dates"]:
                scores.append(1.0)  # 如果查询关注当前状态且文档包含日期，给予额外分数
            
            return sum(scores) / len(scores) if scores else 0.0
            
        except Exception as e:
            logger.error(f"Error calculating context relevance: {e}")
            return 0.0

    def get_document_context(self, doc, kb_id: int) -> str:
        """获取文档的上下文内容"""
        try:
            # 获取相邻的文档块
            nearby_docs = self.vector_store.similarity_search(
                doc.page_content,
                k=self.context_window * 2,
                filter={"kb_id": kb_id}
            )
            
            # 合并上下文
            context_parts = []
            for nearby_doc in nearby_docs:
                if self.calculate_similarity(
                    doc.page_content,
                    nearby_doc.page_content
                ) > 0.5:  # 相似度阈值
                    context_parts.append(nearby_doc.page_content)
            
            return "\n".join(context_parts)
        except Exception as e:
            logger.error(f"Error getting document context: {e}")
            return doc.page_content

    def expand_query(self, query: str) -> str:
        """查询扩展"""
        try:
            # 提取关键词
            keywords = jieba.analyse.extract_tags(query, topK=5)
            
            # 添加同义词
            expanded_terms = set(keywords)
            for term in keywords:
                if term in self.synonym_dict:
                    expanded_terms.update(self.synonym_dict[term])
            
            # 构建扩展查询
            expanded_query = f"{query} {' '.join(expanded_terms)}"
            return expanded_query
        except Exception as e:
            logger.error(f"Error expanding query: {e}")
            return query

    def calculate_relevance_score(self, query: str, content: str, metadata: Dict) -> float:
        """改进的相关性分数计算"""
        try:
            # 1. 基础相似度分数
            base_score = self.calculate_similarity(query, content)
            
            # 2. 关键词匹配分数
            keyword_score = self.calculate_keyword_match_score(query, content)
            
            # 3. 位置权重
            position_weight = 1.0
            if "chunk_index" in metadata:
                # 给予文档开头和结尾的内容较低的权重
                chunk_index = metadata["chunk_index"]
                if chunk_index == 0 or chunk_index == -1:
                    position_weight = 0.8
            
            # 4. 文件名相关性
            filename_score = 0.0
            if "filename" in metadata:
                filename_score = self.calculate_similarity(query, metadata["filename"]) * 0.3
            
            # 组合分数
            final_score = (
                0.4 * base_score +
                0.4 * keyword_score +
                0.1 * position_weight +
                0.1 * filename_score
            )
            
            return final_score
            
        except Exception as e:
            logger.error(f"Error calculating relevance score: {e}")
            return 0.0

    def merge_similar_results(self, results: List[Dict]) -> List[Dict]:
        """合并相似的检索结果"""
        merged = []
        seen_content = set()
        
        for result in results:
            content = result["content"]
            is_similar = False
            
            # 检查是否与已有内容过于相似
            for seen in seen_content:
                if self.calculate_similarity(content, seen) > 0.7:
                    is_similar = True
                    break
            
            if not is_similar:
                seen_content.add(content)
                merged.append(result)
        
        return merged

    def calculate_similarity(self, text1: str, text2: str) -> float:
        """计算两段文本的相似度"""
        # 使用 TF-IDF 计算相似度
        tfidf = TfidfVectorizer()
        try:
            tfidf_matrix = tfidf.fit_transform([text1, text2])
            return cosine_similarity(tfidf_matrix[0:1], tfidf_matrix[1:2])[0][0]
        except:
            return 0.0

    def preprocess_query(self, query: str) -> str:
        """增强的查询预处理"""
        try:
            # 1. 提取条款编号
            article_numbers = re.findall(r'第[一二三四五六七八九十百千万]+条|[0-9]+[.、]', query)
            
            # 2. 提取关键词
            keywords = jieba.analyse.extract_tags(query, topK=5)
            
            # 3. 移除停用词
            stopwords = {
                '的', '了', '和', '与', '或', '而', '及', '等', '地', '得', '之',
                '着', '往', '在', '上', '下', '里', '中', '对', '到', '从', '向',
                '是', '有', '个', '之', '些', '来', '去', '说', '要', '把', '那',
                '你', '我', '他', '它', '她', '这', '那', '哪', '什么', '怎么',
                '为', '以', '能', '会', '可以', '可能', '应该', '没有', '看'
            }
            
            # 4. 构建增强查询
            enhanced_query = query
            if article_numbers:
                enhanced_query = f"{' '.join(article_numbers)} {enhanced_query}"
            if keywords:
                enhanced_query = f"{enhanced_query} {' '.join(keywords)}"
            
            return enhanced_query
        except Exception as e:
            logger.error(f"Error in query preprocessing: {e}")
            return query

    def extract_key_phrases(self, text: str) -> List[str]:
        """提取关键短语"""
        # 1. 分词
        words = text.split()
        
        # 2. 提取单词和短语
        phrases = []
        for i in range(len(words)):
            phrases.append(words[i])
            if i < len(words) - 1:
                phrases.append(words[i] + words[i + 1])
        
        return phrases

    def calculate_keyword_match_score(self, query: str, content: str) -> float:
        """改进的关键词匹配分数计算"""
        try:
            # 提取查询关键词
            query_keywords = set(jieba.analyse.extract_tags(query, topK=10))
            
            # 提取内容关键词
            content_keywords = set(jieba.analyse.extract_tags(content, topK=20))
            
            # 计算关键词匹配度
            matched_keywords = query_keywords & content_keywords
            if not query_keywords:
                return 0.0
                
            return len(matched_keywords) / len(query_keywords)
            
        except Exception as e:
            logger.error(f"Error calculating keyword match score: {e}")
            return 0.0

    def clean_source_name(self, filename: str) -> str:
        """优化文档来源名称的显示"""
        try:
            # 1. 移除文件扩展名
            name = os.path.splitext(filename)[0]
            
            # 2. 移除常见的后缀模式
            patterns = [
                r'_[0-9]+$',  # 移除末尾的数字编号
                r'_文档$', r'_文件$',  # 移除常见后缀
                r'_人事任免$', r'_任免名单$',  # 移除文档类型后缀
                r'_新疆维吾尔自治区人民政府网$',  # 移除网站来源
            ]
            
            for pattern in patterns:
                name = re.sub(pattern, '', name)
            
            # 3. 如果文件名太长，进行截断
            if len(name) > 30:
                name = name[:27] + '...'
            
            return name
            
        except Exception as e:
            logger.error(f"Error cleaning source name: {e}")
            return filename

    def format_source_reference(self, filename: str) -> str:
        """格式化参考来源的显示"""
        try:
            # 1. 提取文件名和类型
            name, ext = os.path.splitext(filename)
            file_type = ext[1:].upper() if ext else "文档"
            
            # 2. 根据文件类型添加合适的描述
            type_descriptions = {
                "PDF": "政府公文",
                "DOC": "文档",
                "DOCX": "文档",
                "TXT": "文本",
                "MD": "文档",
            }
            
            # 3. 获取文档类型描述
            doc_type = type_descriptions.get(file_type, "文档")
            
            # 4. 构建格式化的来源描述
            # 例如：《政府公文：新疆维吾尔自治区第十四届人民代表大会常务委员会第十二次会议任免名单》
            formatted_source = f"《{doc_type}：{name}》"
            
            return formatted_source
            
        except Exception as e:
            logger.error(f"Error formatting source reference: {e}")
            return f"《{filename}》"

    def build_prompt(self, query: str, documents: List[Dict[str, Any]]) -> str:
        """改进的 prompt 构建"""
        try:
            # 1. 提取查询中的人名
            query_names = self.extract_person_names(query)
            is_person_query = bool(query_names)
            
            # 提取查询中的时间信息
            query_time_info = self.time_manager.extract_time_info(query)
            
            # 2. 提取和过滤相关内容
            relevant_contents = []
            person_related_contents = []
            
            for doc in documents:
                content = doc["content"].strip()
                score = doc.get("score", 0)
                
                # 使用格式化的参考来源
                source = self.format_source_reference(
                    doc.get("metadata", {}).get("source", "未知来源")
                )
                
                # 检查内容中是否包含查询的人名
                doc_names = self.extract_person_names(content)
                has_query_name = bool(query_names & doc_names)
                
                # 构建内容块
                content_block = f"参考来源：{source}\n{content}"
                
                # 如果包含查询的人名，优先添加到人名相关内容
                if has_query_name:
                    person_related_contents.append(content_block)
                else:
                    relevant_contents.append(content_block)
            
            # 3. 组合内容，确保人名相关内容在前
            final_contents = person_related_contents + relevant_contents
            
            # 4. 构建上下文
            context = "\n\n".join(final_contents)
            
            # 5. 根据查询类型选择模板
            if is_person_query:
                template = """基于以下参考信息回答关于人物的问题。请注意：
1. 请仔细查找关于 {names} 的最新信息
2. 如果找到相关信息，请明确指出信息的来源
3. 如果有职位变动，请按时间顺序说明
4. 如果找不到相关信息，请明确说明
5. 如果上传的知识库文档是任职名单类似的，知识库会有（20xx年x月xx日新疆维吾尔自治区第xx届人民代表大会常务委员会第xx次会议通过）这样的时间信息，请特别注意
6. 如果知识库有多个任职名单，请特别注意
7. 如果知识库有（20xx年x月xx日新疆维吾尔自治区第xx届人民代表大会常务委员会第xx次会议通过），该时间就是所有人员的任职或免职时间
8. 一个人可能会在多个任职名单中出现，请特别注意，并给出所有任职名单中该人员的任职或免职时间
9. 如果知识库文档有（本会议任免的名单从202X年X月XX日开始成效），该时间就是所有人员的任职或免职时间

参考信息：
{context}

问题：{query}

请提供准确、完整的回答："""
                # 填充模板，包含人名信息
                prompt = template.format(
                    names="、".join(query_names),
                    context=context,
                    query=query
                )
            else:
                # 如果是时间相关查询，使用特定模板
                if query_time_info["time_type"] == "current":
                    template = """基于以下参考信息回答问题。请注意：
1. 优先使用最新的信息回答
2. 明确说明信息的时间点
3. 如果信息可能过时，请说明这一点
4. 如果找不到最新信息，请说明使用的是哪个时间点的信息
5. 如果上传的知识库文档是任职名单类似的，知识库会有（20xx年x月xx日新疆维吾尔自治区第xx届人民代表大会常务委员会第xx次会议通过）这样的时间信息，请特别注意
6. 如果知识库有多个任职名单，请特别注意
7. 如果知识库有（20xx年x月xx日新疆维吾尔自治区第xx届人民代表大会常务委员会第xx次会议通过），该时间就是所有人员的任职或免职时间
8. 一个人可能会在多个任职名单中出现，请特别注意，并给出所有任职名单中该人员的任职或免职时间
9. 如果知识库文��有（本会议任免的名单从202X年X月XX日开始成效），该时间就是所有人员的任职或免职时间
参考信息：
{context}

问题：{query}

请提供准确、完整的回答："""
                else:
                    template = """基于以下参考信息回答问题。请注意：
1. 如果无法从参考信息中得到完整答案，请明确指出
2. 保持客观，只使用参考信息中的内容
3. 如果信息有冲突，请指出这一点
4. 如果信息可能不完整或过时，请说明这一点

参考信息：
{context}

问题：{query}

请提供准确、完整的回答："""
                
                prompt = template.format(
                    context=context,
                    query=query
                )
            
            return prompt
            
        except Exception as e:
            logger.error(f"Error building prompt: {e}")
            return self.default_template.format(
                context=documents[0]['content'] if documents else '无相关信息',
                query=query
            )

    async def get_llm_response(self, prompt: str, model: str = "qwen2.5:latest") -> Dict[str, Any]:
        """改进的 LLM 回答获取方法"""
        try:
            # 构建系统提示
            system_prompt = """你是一个专业的问答助手。在回答问题时请注意：
1. 如果找到相关信息，请直接引用参考信息回答
2. 如果是人物相关查询，要特别关注人名、职位、时间等信息
3. 如果参考信息中没有找到答案，请明确说明"在提供的参考信息中未找到相关内容"
4. 不要添加任何参考信息之外的内容
5. 保持回答的准确性和客观性
6. 如果上传的知识库文档是任职名单类似的，知识库会有（20xx年x月xx日新疆维吾尔自治区第xx届人民代表大会常务委员会第xx次会议通过）这样的时间信息，请特别注意
7. 如果知识库有多个任职名单，请特别注意
8. 如果知识库有（20xx年x月xx日新疆维吾尔自治区第xx届人民代表大会常务委员会第xx次会议通过），该时间就是所有人员的任职或免职时间
9. 一个人可能会在多个任职名单中出现，请特别注意，并给出所有任职名单中该人员的任职或免职时间
10. 如果知识库文档有（本会议任免的名单从202X年X月XX日开始成效），该时间就是所有人员的任职或免职时间
"""

            # 组合完整提示
            full_prompt = f"{system_prompt}\n\n{prompt}"
            
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.post(
                    "http://localhost:11434/api/generate",
                    json={
                        "model": model,
                        "prompt": full_prompt,
                        "system": "你是一个专业的问答助手，请基于提供的参考信息回答问题。",
                        "stream": False
                    }
                )
                
                if response.status_code == 200:
                    result = response.json()
                    answer = result.get("response", "")
                    
                    # 如果回答中包含"未找到"等否定词，降低置信度
                    if any(phrase in answer for phrase in ["未找到", "没有相关", "无法找到", "未能找到"]):
                        confidence = "低"
                    else:
                        confidence = "中"
                    
                    return {
                        "answer": answer,
                        "sources": [],
                        "confidence": confidence
                    }
                else:
                    logger.error(f"LLM API error: {response.text}")
                    return {
                        "answer": "抱歉，处理您的请求时出现错误。",
                        "sources": [],
                        "confidence": "低"
                    }
        except Exception as e:
            logger.error(f"Error in get_llm_response: {e}")
            return {
                "answer": "抱歉，调用 LLM 服务时出现错误。",
                "sources": [],
                "confidence": "低"
            }

    def is_general_question(self, query: str) -> bool:
        """判断是否是通用问题"""
        return any(re.match(pattern, query) for pattern in self.general_questions)

    async def process_rag_request(self, query: str, kb_id: int, model: str = "qwen2.5:latest") -> Dict:
        """改进的 RAG 处理方法"""
        try:
            logger.info(f"Processing RAG request - Query: '{query}', KB: {kb_id}, Model: {model}")
            
            # 1. 首先验证知识库状态
            try:
                kb_docs = self.vector_store.get(
                    where={"kb_id": kb_id}
                )
                if not kb_docs or not kb_docs['ids']:
                    logger.warning(f"Knowledge base {kb_id} is empty or not found")
                    return {
                        "answer": "抱歉，该知识库中暂无任何文档，请先添加文档。",
                        "sources": [],
                        "confidence": "低"
                    }
                logger.info(f"Knowledge base {kb_id} contains {len(kb_docs['ids'])} documents")
            except Exception as e:
                logger.error(f"Error checking knowledge base: {e}")
                return {
                    "answer": "抱歉，检查知识库状态时出现错误。",
                    "sources": [],
                    "confidence": "低"
                }

            # 2. 检索相关文档
            docs = await self.retrieve_documents(query, kb_id)
            
            if not docs:
                # 尝试使用更宽松的检索策略重试一次
                logger.info("Retrying with relaxed search parameters...")
                docs = await self.fallback_retrieval(query, kb_id)
                
            if not docs:
                return {
                    "answer": "抱歉，在知识库中没有找到与您问题相关的内容。请尝试换个方式提问，或确认知识库中是否含相关信息。",
                    "sources": [],
                    "confidence": "低"
                }

            # 3. 构建提示
            prompt = self.build_prompt(query, docs)
            logger.debug(f"Built prompt: {prompt[:200]}...")  # 只记录前200个字符

            # 4. 调用 LLM 生成回答
            llm_response = await self.get_llm_response(prompt, model)
            
            # 5. 评估答案可信度
            confidence = self.evaluate_confidence(docs, llm_response["answer"])
            
            # 6. 准备返回结果
            sources = [{
                "content": doc["content"],
                "metadata": {
                    **doc["metadata"],
                    "source": self.format_source_reference(doc["metadata"].get("source", "未知来源"))
                },
                "score": doc["score"]
            } for doc in docs]

            result = {
                "answer": llm_response["answer"],
                "sources": sources,
                "confidence": confidence
            }
            
            logger.info(f"Request completed - Confidence: {confidence}")
            return result
            
        except Exception as e:
            logger.error(f"Error in process_rag_request: {str(e)}", exc_info=True)
            return {
                "answer": "抱歉，处理请求时发生错误。请稍后重试。",
                "sources": [],
                "confidence": "低"
            }

    async def fallback_retrieval(self, query: str, kb_id: int) -> List[Dict]:
        """备用检索策略"""
        try:
            # 1. 使用更简单的查询
            simple_query = " ".join(jieba.analyse.extract_tags(query, topK=3))
            logger.info(f"Trying fallback search with simplified query: {simple_query}")
            
            # 2. 放宽检索参数
            results = self.vector_store.similarity_search_with_score(
                simple_query,
                k=30,  # 增加检索数量
                filter={"kb_id": kb_id}
            )
            
            # 3. 处理结果
            processed_results = []
            for doc, score in results:
                # 使用更宽松的相似度阈值
                if score < 2.0:  # 根据实际情况调整阈值
                    processed_results.append({
                        "content": doc.page_content,
                        "score": score,
                        "metadata": doc.metadata
                    })
            
            return processed_results[:5]  # 返回前5个结果
            
        except Exception as e:
            logger.error(f"Error in fallback retrieval: {e}")
            return []

    def evaluate_confidence(self, docs: List[Dict], answer: str) -> str:
        """评估答案的可信度"""
        try:
            # 基于多个因素评估可信度
            scores = []
            
            # 1. 文档相关性分数
            doc_scores = [doc["score"] for doc in docs]
            avg_doc_score = sum(doc_scores) / len(doc_scores)
            scores.append(avg_doc_score)
            
            # 2. 答案与文档的匹配度
            answer_match_scores = []
            for doc in docs:
                match_score = self.calculate_similarity(answer, doc["content"])
                answer_match_scores.append(match_score)
            avg_match_score = sum(answer_match_scores) / len(answer_match_scores)
            scores.append(avg_match_score)
            
            # 3. 文档数量评分I
            doc_count_score = min(len(docs) / self.rerank_top_k, 1.0)
            scores.append(doc_count_score)
            
            # 综合评分
            final_score = sum(scores) / len(scores)
            
            # 确定可信度级别
            if final_score > 0.8:
                return "高"
            elif final_score > 0.5:
                return "中"
            else:
                return "低"
                
        except Exception as e:
            logger.error(f"Error evaluating confidence: {str(e)}")
            return "低"

    async def get_response(self, query: str, kb_id: int) -> str:
        """获取回答"""
        try:
            result = await self.process_rag_request(query, kb_id)
            return result.get("answer", "抱歉，无法处理您的请求")
        except Exception as e:
            logger.error(f"Error in get_response: {e}")
            return "抱歉，处理您的请求时出现错误。请稍后重试。"

    def is_person_related_query(self, query: str) -> bool:
        """判断是否是人物相关查询"""
        # 检查是否包含人名
        words = pseg.cut(query)
        has_person = any(flag == 'nr' for word, flag in words)
        
        # 检查是否包含人物相关词
        has_person_related = any(word in query for word in self.person_related_words)
        
        return has_person or has_person_related

    # 添加特定类型的提示模板
    person_query_template = """基于以下参考信息回答关于人物的问题。请注意：
1. 优先提供最新信息
2. 如果信息有时间点，请明确指出
3. 如果有职位变动，请按时间顺序说明
4. 如果信息可能过时，请说明这一点
5. 如果是人物相关查询，请特别关注人名、职位、时间等信息
6. 如果上传的知识库文档是任职名单类似的，知识库会有（20xx年x月xx日新疆维吾尔自治区第xx届人民代表大会常务委员会第xx次会议通过）这样的时间信息，请特别注意
7. 如果知识库有多个任职名单，请特别注意
8. 如果知识库有（20xx年x月xx日新疆维吾尔自治区第xx届人民代表大会常务委员会第xx次会议通过），该时间就是所有人员的任职或免职时间
9. 一个人可能会在多个任职名单中出现，请特别注意
10. 如果知识库文档有（本会议任免的名单从202X年X月XX日开始成效），该时间就是所有人员的任职或免职时间
参考信息：
{context}

问题：{query}

请提供准确、完整的回答："""

    default_template = """基于以下参考信息回答问题。请注意：
1. 如果无法从参考信息中得到完整答案，请明确指出
2. 保持客观，只使用参考信息中的内容
3. 如果信息有冲突，请指出这一点
4. 如果信息可能不完整或过时，请说明这一点

参考信息：
{context}

问题：{query}

请提供准确、完整的回答："""

# 创建全局实例
rag_service = RAGService() 