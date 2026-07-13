"""Agent基类"""
from abc import ABC, abstractmethod
from loguru import logger


class BaseAgent(ABC):
    """所有Agent的基类"""
    
    def __init__(self, name: str = None):
        self.name = name or self.__class__.__name__
        logger.info(f"Agent初始化: {self.name}")
    
    @abstractmethod
    def analyze(self, data: dict) -> dict:
        """分析入口方法，返回分析报告"""
        pass
    
    def _format_report(self, title: str, content: str, emoji: str = "📋") -> str:
        """格式化报告输出"""
        return f"\n{'='*50}\n{emoji} {title}\n{'='*50}\n{content}\n{'='*50}"
