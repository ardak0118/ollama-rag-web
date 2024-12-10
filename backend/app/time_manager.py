import re
import logging
from typing import Dict, List, Set, Any, Optional
from datetime import datetime
import jieba
import jieba.posseg as pseg

logger = logging.getLogger(__name__)

class TimeManager:
    def __init__(self):
        # 时间表达式模式
        self.time_patterns = {
            "year_month_day": r'\d{4}年\d{1,2}月\d{1,2}日',
            "year_month": r'\d{4}年\d{1,2}月',
            "year": r'\d{4}年',
            "relative_time": r'(现在|目前|当前|如今|此时|眼下)',
            "time_ago": r'(之前|以前|过去|曾经)',
            "time_later": r'(之后|以后|未来|将来)',
        }
        
        # 时间关键词
        self.time_keywords = {
            "current": {"现在", "目前", "当前", "如今", "此时", "眼下"},
            "past": {"之前", "以前", "过去", "曾经", "原先", "此前"},
            "future": {"之后", "以后", "未来", "将来", "即将"},
        }
        
        # 时间状态缓存
        self.time_cache = {}
        
    def extract_time_info(self, text: str) -> Dict[str, Any]:
        """提取时间信息"""
        time_info = {
            "dates": set(),
            "relative_time": set(),
            "time_type": None,  # current, past, future
        }
        
        # 1. 提取具体日期
        for pattern_name, pattern in self.time_patterns.items():
            matches = re.finditer(pattern, text)
            for match in matches:
                time_info["dates"].add(match.group())
        
        # 2. 识别相对时间
        for time_type, keywords in self.time_keywords.items():
            if any(keyword in text for keyword in keywords):
                time_info["relative_time"].update(
                    keyword for keyword in keywords if keyword in text
                )
                time_info["time_type"] = time_type
        
        return time_info

    def normalize_date(self, date_str: str) -> Optional[datetime]:
        """标准化日期格式"""
        try:
            # 处理不同格式的日期
            if re.match(r'\d{4}年\d{1,2}月\d{1,2}日', date_str):
                return datetime.strptime(date_str, '%Y年%m月%d日')
            elif re.match(r'\d{4}年\d{1,2}月', date_str):
                return datetime.strptime(date_str + '1日', '%Y年%m月%d日')
            elif re.match(r'\d{4}年', date_str):
                return datetime.strptime(date_str + '1月1日', '%Y年%m月%d日')
            return None
        except Exception as e:
            logger.error(f"Error normalizing date {date_str}: {e}")
            return None

    def compare_dates(self, date1: str, date2: str) -> int:
        """比较两个日期的先后顺序"""
        d1 = self.normalize_date(date1)
        d2 = self.normalize_date(date2)
        
        if d1 and d2:
            if d1 < d2:
                return -1
            elif d1 > d2:
                return 1
            return 0
        return 0

    def get_latest_date(self, dates: Set[str]) -> Optional[str]:
        """获取最新日期"""
        if not dates:
            return None
            
        latest = None
        for date in dates:
            if not latest:
                latest = date
                continue
                
            if self.compare_dates(latest, date) < 0:
                latest = date
        
        return latest

    def calculate_time_relevance(self, query_time: Dict[str, Any], 
                               content_time: Dict[str, Any]) -> float:
        """计算时间相关性分数"""
        score = 0.0
        
        # 1. 检查时间类型匹配
        if query_time["time_type"] == content_time["time_type"]:
            score += 0.3
        
        # 2. 检查具体日期
        if query_time["dates"] & content_time["dates"]:
            score += 0.4
        
        # 3. 检查相对时间表达
        if query_time["relative_time"] & content_time["relative_time"]:
            score += 0.3
        
        # 4. 特殊处理"现在"相关查询
        if query_time["time_type"] == "current":
            # 如果内容包含最新日期，提高分数
            content_dates = content_time["dates"]
            if content_dates:
                latest_date = self.get_latest_date(content_dates)
                if latest_date:
                    score += 0.2
        
        return min(score, 1.0) 