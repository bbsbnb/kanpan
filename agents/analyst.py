"""分析师Agent - 技术面分析"""
import pandas as pd
from agents.base import BaseAgent
from indicators.ta_engine import TechnicalEngine
from loguru import logger


class AnalystAgent(BaseAgent):
    """
    分析师Agent: 负责看市场数据，分析技术指标，识别趋势
    输入: K线数据 + 股票代码
    输出: 技术分析报告
    """
    
    def __init__(self, config: dict = None):
        super().__init__("分析师Agent")
        self.engine = TechnicalEngine(config)
    
    def analyze(self, data: dict) -> dict:
        """
        技术面分析
        
        Args:
            data: {
                'symbol': str,           # 股票代码
                'df': pd.DataFrame,      # K线数据
                'stock_name': str,       # 股票名称
            }
        
        Returns:
            {
                'agent': '分析师',
                'report': str,           # 文字报告
                'indicators': dict,      # 指标快照
                'score': float,          # 综合评分
                'signals': dict,         # 信号统计
                'recommendation': str,   # 建议
            }
        """
        symbol = data.get('symbol', '')
        df = data.get('df')
        stock_name = data.get('stock_name', symbol)
        
        if df is None or df.empty:
            return {'error': '无K线数据'}
        
        logger.info(f"分析师开始分析: {symbol} ({stock_name})")
        
        # 计算技术指标
        df_ind = self.engine.calculate_all(df)
        
        # 生成报告
        report = self.engine.generate_technical_report(df_ind, stock_name)
        
        # 获取最新指标
        indicators = self.engine.get_latest_indicators(df_ind)
        
        # 打分和建议
        score = self.engine._calculate_score(indicators)
        signals = self.engine._collect_signals(indicators)
        
        if score > 0.3:
            recommendation = "建议关注，技术面偏多"
        elif score < -0.3:
            recommendation = "谨慎操作，技术面偏空"
        else:
            recommendation = "观望为主，震荡行情"
        
        result = {
            'agent': '分析师',
            'report': report,
            'indicators': indicators,
            'score': round(score, 3),
            'signals': signals,
            'recommendation': recommendation,
        }
        
        logger.info(f"分析师完成分析: score={score:.3f}")
        return result
