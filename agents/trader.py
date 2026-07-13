"""交易员Agent - 综合决策"""
from agents.base import BaseAgent
from loguru import logger


class TraderAgent(BaseAgent):
    """
    交易员Agent: 综合分析师和研究员的报告，决定什么时候买、买多少
    MVP阶段: 基于技术指标的简单规则引擎
    """
    
    def __init__(self):
        super().__init__("交易员Agent")
    
    def analyze(self, data: dict) -> dict:
        """
        交易决策
        
        Args:
            data: {
                'symbol': str,
                'analyst_result': dict,    # 分析师结果
                'researcher_result': dict, # 研究员结果
            }
        
        Returns:
            {
                'agent': '交易员',
                'action': 'buy/sell/hold',
                'confidence': float,       # 置信度 0-1
                'position_pct': float,     # 建议仓位比例
                'stop_loss': float,        # 止损价
                'take_profit': float,      # 止盈价
                'reasoning': str,          # 推理过程
                'recommendation': str,
            }
        """
        analyst = data.get('analyst_result', {})
        researcher = data.get('researcher_result', {})
        indicators = analyst.get('indicators', {})
        
        score = analyst.get('score', 0)
        close_price = indicators.get('close', 0)
        atr = indicators.get('atr', 0)
        
        # 基于评分的交易决策
        if score > 0.4:
            action = "buy"
            confidence = min(0.9, abs(score) + 0.3)
            position_pct = 0.15  # 15%仓位
            reasoning = f"技术面偏强(评分{score:.2f})，均线多头排列，建议建仓"
        elif score < -0.4:
            action = "sell"
            confidence = min(0.9, abs(score) + 0.3)
            position_pct = 0.0
            reasoning = f"技术面偏弱(评分{score:.2f})，均线空头排列，建议减仓"
        elif score > 0.1:
            action = "hold_buy"
            confidence = 0.5
            position_pct = 0.05
            reasoning = "技术面略偏多，可轻仓试探"
        elif score < -0.1:
            action = "hold_sell"
            confidence = 0.5
            position_pct = 0.0
            reasoning = "技术面略偏空，建议观望"
        else:
            action = "hold"
            confidence = 0.3
            position_pct = 0.0
            reasoning = "震荡行情，建议观望"
        
        # 止损止盈
        stop_loss = close_price * 0.95 if close_price > 0 else 0
        take_profit = close_price * 1.10 if close_price > 0 else 0
        
        return {
            'agent': '交易员',
            'action': action,
            'confidence': round(confidence, 2),
            'position_pct': position_pct,
            'stop_loss': round(stop_loss, 2),
            'take_profit': round(take_profit, 2),
            'reasoning': reasoning,
            'recommendation': reasoning,
        }
