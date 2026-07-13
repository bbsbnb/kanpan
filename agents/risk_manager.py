"""风控Agent - 风险评估"""
from agents.base import BaseAgent
from loguru import logger


class RiskManagerAgent(BaseAgent):
    """
    风控Agent: 评估市场波动性、流动性风险，检查交易策略有没有漏洞
    """
    
    def __init__(self, config: dict = None):
        super().__init__("风控Agent")
        self.config = config or {}
        self.max_position_pct = self.config.get("max_position_pct", 0.2)
        self.stop_loss_pct = self.config.get("stop_loss_pct", 0.05)
        self.max_drawdown_pct = self.config.get("max_drawdown_pct", 0.10)
    
    def analyze(self, data: dict) -> dict:
        """
        风险评估
        
        Args:
            data: {
                'symbol': str,
                'trader_result': dict,     # 交易员结果
                'portfolio': dict,         # 持仓信息
            }
        
        Returns:
            {
                'agent': '风控',
                'risk_level': 'low/medium/high',
                'risk_score': float,       # 0-1
                'pass': bool,              # 是否通过风控
                'warnings': list,          # 警告信息
                'suggestions': list,       # 建议
                'recommendation': str,
            }
        """
        trader = data.get('trader_result', {})
        indicators = data.get('indicators', {})
        
        warnings = []
        risk_score = 0.0
        
        # 检查波动率
        atr = indicators.get('atr', 0)
        close = indicators.get('close', 0)
        if atr > 0 and close > 0:
            atr_pct = atr / close
            if atr_pct > 0.03:
                warnings.append(f"⚠️ 波动率偏高(ATR占比{atr_pct*100:.1f}%)")
                risk_score += 0.3
        
        # 检查RSI超买超卖
        rsi = indicators.get('rsi', 50)
        if rsi > 80:
            warnings.append("⚠️ RSI超买，回调风险大")
            risk_score += 0.2
        elif rsi < 20:
            warnings.append("⚠️ RSI超卖，可能继续下跌")
            risk_score += 0.1
        
        # 检查成交量异常
        vol_ratio = indicators.get('volume_ratio', 1)
        if vol_ratio > 3:
            warnings.append("⚠️ 成交量异常放大，注意异动")
            risk_score += 0.1
        
        # 检查交易员建议的仓位
        position = trader.get('position_pct', 0)
        if position > self.max_position_pct:
            warnings.append(f"⚠️ 建议仓位({position*100:.0f}%)超过上限({self.max_position_pct*100:.0f}%)")
            risk_score += 0.2
        
        # 确定风险等级
        if risk_score > 0.5:
            risk_level = "high"
        elif risk_score > 0.2:
            risk_level = "medium"
        else:
            risk_level = "low"
        
        # 决定是否放行
        pass_risk = risk_score <= 0.5
        
        suggestions = []
        if not pass_risk:
            suggestions.append("建议降低仓位或暂缓操作")
        if rsi > 70:
            suggestions.append("RSI偏高，注意回调风险")
        if atr_pct > 0.02 if 'atr_pct' in dir() else False:
            suggestions.append("波动较大，设置更紧的止损")
        
        return {
            'agent': '风控',
            'risk_level': risk_level,
            'risk_score': round(risk_score, 2),
            'pass': pass_risk,
            'warnings': warnings,
            'suggestions': suggestions,
            'recommendation': "通过 ✅" if pass_risk else "不通过 ❌",
        }
