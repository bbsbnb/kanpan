"""投资经理Agent - 最终决策"""
from agents.base import BaseAgent
from loguru import logger


class PortfolioManagerAgent(BaseAgent):
    """
    投资经理Agent: 看风控报告，最终拍板批准或驳回交易
    """
    
    def __init__(self):
        super().__init__("投资经理Agent")
    
    def analyze(self, data: dict) -> dict:
        """
        最终决策
        
        Args:
            data: {
                'symbol': str,
                'analyst_result': dict,    # 分析师
                'researcher_result': dict, # 研究员
                'trader_result': dict,     # 交易员
                'risk_result': dict,       # 风控
            }
        
        Returns:
            {
                'agent': '投资经理',
                'final_action': 'buy/sell/hold/cancel',
                'approved': bool,
                'position_pct': float,
                'stop_loss': float,
                'take_profit': float,
                'summary': str,            # 综合总结
                'reasoning': str,          # 决策理由
            }
        """
        analyst = data.get('analyst_result', {})
        researcher = data.get('researcher_result', {})
        trader = data.get('trader_result', {})
        risk = data.get('risk_result', {})
        
        trader_action = trader.get('action', 'hold')
        risk_pass = risk.get('pass', True)
        risk_level = risk.get('risk_level', 'low')
        score = analyst.get('score', 0)
        
        # 投资决策逻辑
        if not risk_pass:
            final_action = "cancel"
            approved = False
            reasoning = f"风控未通过(风险等级:{risk_level})，驳回交易"
        elif trader_action in ['buy', 'hold_buy'] and score > 0.2:
            final_action = "buy"
            approved = True
            reasoning = f"技术面偏多(评分{score:.2f})，风控通过，批准买入"
        elif trader_action in ['sell', 'hold_sell'] and score < -0.2:
            final_action = "sell"
            approved = True
            reasoning = f"技术面偏空(评分{score:.2f})，风控通过，批准卖出"
        else:
            final_action = "hold"
            approved = True
            reasoning = "当前无明显信号，建议观望"
        
        # 仓位调整（风控可以调低仓位）
        position_pct = trader.get('position_pct', 0)
        if risk_level == 'high':
            position_pct *= 0.5  # 高风险时减半
        elif risk_level == 'medium':
            position_pct *= 0.8
        
        # 综合总结
        summary_lines = [
            f"📊 {data.get('symbol', '')} 投资决策",
            f"━━━━━━━━━━━━━━━━━━━━━━",
            f"📈 技术评分: {score:+.3f}",
            f"🎯 交易建议: {trader_action}",
            f"🛡️  风控状态: {'通过' if risk_pass else '未通过'}",
            f"⚠️  风险等级: {risk_level}",
            f"━━━━━━━━━━━━━━━━━━━━━━",
            f"✅ 最终决策: {final_action}",
            f"💰 建议仓位: {position_pct*100:.1f}%",
            f"📝 理由: {reasoning}",
        ]
        
        return {
            'agent': '投资经理',
            'final_action': final_action,
            'approved': approved,
            'position_pct': round(position_pct, 3),
            'stop_loss': trader.get('stop_loss', 0),
            'take_profit': trader.get('take_profit', 0),
            'summary': '\n'.join(summary_lines),
            'reasoning': reasoning,
        }
