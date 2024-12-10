import logging
import time
from typing import Dict, List, Set, Any
import jieba.posseg as pseg

logger = logging.getLogger(__name__)

class DialogueContextManager:
    def __init__(self, max_history: int = 5):
        self.max_history = max_history
        self.dialogue_history = []
        self.entity_memory = {}
        self.current_intent = None
        
    def update_context(self, query: str, response: str, entities: Dict[str, Set[str]]):
        """更新对话上下文"""
        try:
            # 1. 更新对话历史
            self.dialogue_history.append({
                "query": query,
                "response": response,
                "entities": entities,
                "timestamp": time.time()
            })
            
            # 保持历史记录在最大长度以内
            if len(self.dialogue_history) > self.max_history:
                self.dialogue_history = self.dialogue_history[-self.max_history:]
            
            # 2. 更新实体记忆
            for entity_type, entity_values in entities.items():
                if entity_type not in self.entity_memory:
                    self.entity_memory[entity_type] = {}
                for entity in entity_values:
                    if entity not in self.entity_memory[entity_type]:
                        self.entity_memory[entity_type][entity] = []
                    self.entity_memory[entity_type][entity].append({
                        "mention": entity,
                        "context": query,
                        "timestamp": time.time()
                    })
            
            logger.debug(f"Context updated - History size: {len(self.dialogue_history)}, "
                        f"Entities: {len(self.entity_memory)}")
                        
        except Exception as e:
            logger.error(f"Error updating context: {e}")
    
    def get_relevant_context(self, query: str) -> Dict[str, Any]:
        """获取相关上下文"""
        try:
            # 1. 提取查询中的实体
            query_entities = self.extract_entities(query)
            
            # 2. 获取相关的历史对话
            relevant_history = self.get_relevant_history(query, query_entities)
            
            # 3. 获取实体相关信息
            entity_context = self.get_entity_context(query_entities)
            
            return {
                "history": relevant_history,
                "entities": entity_context
            }
            
        except Exception as e:
            logger.error(f"Error getting relevant context: {e}")
            return {"history": [], "entities": {}}
    
    def extract_entities(self, text: str) -> Dict[str, Set[str]]:
        """提取文本中的实体"""
        entities = {
            "person": set(),    # 人名
            "location": set(),  # 地名
            "org": set(),       # 组织机构
            "time": set(),      # 时间
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
            elif word in ["主任", "局长", "处长", "科长"]:  # 职位词
                entities["position"].add(word)
        
        return entities
    
    def get_relevant_history(self, query: str, query_entities: Dict[str, Set[str]], 
                           max_turns: int = 3) -> List[Dict]:
        """获取相关的历史对话"""
        try:
            relevant_turns = []
            
            # 1. 检查最近的对话
            recent_history = self.dialogue_history[-max_turns:]
            
            # 2. 计算相关性并筛选
            for turn in recent_history:
                # 检查实体重叠
                turn_entities = turn.get("entities", {})
                has_common_entity = False
                
                for entity_type, entities in query_entities.items():
                    if entity_type in turn_entities:
                        if entities & turn_entities[entity_type]:
                            has_common_entity = True
                            break
                
                if has_common_entity:
                    relevant_turns.append({
                        "query": turn["query"],
                        "response": turn["response"],
                        "timestamp": turn["timestamp"]
                    })
            
            return relevant_turns
            
        except Exception as e:
            logger.error(f"Error getting relevant history: {e}")
            return []
    
    def get_entity_context(self, entities: Dict[str, Set[str]]) -> Dict[str, List[Dict]]:
        """获取实体相关上下文"""
        try:
            context = {}
            
            for entity_type, entity_set in entities.items():
                if entity_type in self.entity_memory:
                    context[entity_type] = {}
                    for entity in entity_set:
                        if entity in self.entity_memory[entity_type]:
                            context[entity_type][entity] = self.entity_memory[entity_type][entity]
            
            return context
            
        except Exception as e:
            logger.error(f"Error getting entity context: {e}")
            return {} 