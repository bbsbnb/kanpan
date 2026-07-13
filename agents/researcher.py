"""研究员Agent - 舆情/资金流分析"""
import urllib.request
import json
import re
from datetime import datetime
from agents.base import BaseAgent
from loguru import logger


class ResearcherAgent(BaseAgent):
    """
    研究员Agent: 读新闻、研报、社交媒体，判断市场情绪
    数据源: 新浪财经API + 东方财富资金流
    """
    
    def __init__(self):
        super().__init__("研究员Agent")
    
    def _fetch_sina_news(self, symbol: str = "", limit: int = 10) -> list:
        """获取新浪财经新闻"""
        try:
            url = f"https://feed.mix.sina.com.cn/api/roll/get?pageid=153&lid=2516&k=&num={limit}&page=1&r=0.1"
            req = urllib.request.Request(url, headers={
                "User-Agent": "Mozilla/5.0",
                "Referer": "https://finance.sina.com.cn/"
            })
            resp = urllib.request.urlopen(req, timeout=10)
            data = json.loads(resp.read().decode('utf-8'))
            
            result = data.get('result', data)
            if isinstance(result, dict):
                news_list = result.get('data', result.get('list', []))
            else:
                news_list = result if isinstance(result, list) else []
            
            return news_list[:limit]
        except Exception as e:
            logger.error(f"获取新浪新闻失败: {e}")
            return []
    
    def _fetch_capital_flow(self, symbol: str) -> dict:
        """
        获取东方财富资金流向数据
        secid: 1.600519(沪A) / 0.000858(深A)
        """
        try:
            import http.client
            from urllib.parse import urlparse
            
            market = 1 if symbol.startswith('6') else 0
            secid = f"{market}.{symbol}"
            api_url = (f"https://push2his.eastmoney.com/api/qt/stock/fflow/daykline/get?"
                       f"secid={secid}&fields1=f1,f2,f3,f7&fields2=f51,f52,f53,f54,f55,f56,"
                       f"f57,f58,f59,f60,f61,f62,f63,f64,f65")
            
            parsed = urlparse(api_url)
            conn = http.client.HTTPSConnection(parsed.netloc, timeout=10)
            conn.request("GET", parsed.path + parsed.query, headers={
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)",
                "Referer": "https://quote.eastmoney.com/"
            })
            resp = conn.getresponse()
            raw = resp.read().decode('utf-8')
            conn.close()
            data = json.loads(raw)
            
            d = data.get('data', {})
            klines = d.get('klines', [])
            
            # 解析最近5天资金流
            recent = []
            for kl in klines[-5:]:
                parts = kl.split(',')
                if len(parts) >= 5:
                    recent.append({
                        'date': parts[0],
                        'main_net_inflow': float(parts[1]),    # 主力净流入
                        'small_net_inflow': float(parts[2]),     # 小单净流入
                        'mid_net_inflow': float(parts[3]),       # 中单净流入
                        'large_net_inflow': float(parts[4]),     # 大单净流入
                        'super_large_net_inflow': float(parts[5]) if len(parts) > 5 else 0,  # 超大单
                    })
            
            # 计算最新一天的资金流向占比
            if recent:
                latest = recent[-1]
                total = abs(latest['main_net_inflow']) + abs(latest['small_net_inflow']) + \
                        abs(latest['mid_net_inflow']) + abs(latest['large_net_inflow'])
                latest['total_flow'] = total
                if total > 0:
                    latest['main_pct'] = latest['main_net_inflow'] / total * 100
                    latest['large_pct'] = latest['large_net_inflow'] / total * 100
            
            return {'recent': recent, 'latest': recent[-1] if recent else {}}
            
        except Exception as e:
            logger.error(f"获取资金流向失败: {e}")
            return {'recent': [], 'latest': {}}
    
    def _analyze_sentiment(self, news: list, capital: dict) -> dict:
        """
        基于关键词的情绪分析
        """
        positive_words = ['利好', '上涨', '突破', '增长', '盈利', '分红', '回购', 
                         '增持', '创新高', '放量', '资金流入', '超预期', '景气']
        negative_words = ['利空', '下跌', '暴跌', '亏损', '减持', '解禁', '质押',
                         '处罚', '退市', '爆雷', '资金流出', '破位', '回调', '风险']
        
        score = 0.0
        positive_count = 0
        negative_count = 0
        key_phrases = []
        
        for news_item in news:
            title = news_item.get('title', '') if isinstance(news_item, dict) else str(news_item)
            for word in positive_words:
                if word in title:
                    score += 1
                    positive_count += 1
                    key_phrases.append(title)
                    break
            for word in negative_words:
                if word in title:
                    score -= 1
                    negative_count += 1
                    key_phrases.append(title)
                    break
        
        # 资金流情绪加成
        latest_cap = capital.get('latest', {})
        main_flow = latest_cap.get('main_net_inflow', 0)
        if main_flow > 0:
            score += 1
        elif main_flow < 0:
            score -= 1
        
        # 归一化到 -1 ~ 1
        sentiment_score = max(-1.0, min(1.0, score / max(len(news), 1)))
        
        if sentiment_score > 0.3:
            sentiment = "积极 🟢"
        elif sentiment_score < -0.3:
            sentiment = "消极 🔴"
        else:
            sentiment = "中性 🟡"
        
        return {
            'sentiment': sentiment,
            'sentiment_score': round(sentiment_score, 3),
            'positive_count': positive_count,
            'negative_count': negative_count,
            'key_phrases': key_phrases[:5],
        }
    
    def analyze(self, data: dict) -> dict:
        """
        舆情分析主入口
        
        Returns:
            {
                'agent': '研究员',
                'report': str,
                'sentiment': str,
                'sentiment_score': float,
                'news_summary': list,
                'capital_flow': dict,
                'recommendation': str,
            }
        """
        symbol = data.get('symbol', '')
        stock_name = data.get('stock_name', symbol)
        
        logger.info(f"研究员开始分析: {symbol} ({stock_name})")
        
        # 获取数据
        news = self._fetch_sina_news(symbol, limit=10)
        capital = self._fetch_capital_flow(symbol)
        sentiment = self._analyze_sentiment(news, capital)
        
        # 生成报告
        lines = []
        lines.append(f"📰 {stock_name} 舆情与资金分析报告")
        lines.append("")
        
        # 情绪概览
        lines.append(f"🎭 市场情绪: {sentiment['sentiment']}")
        lines.append(f"   情绪评分: {sentiment['sentiment_score']:+.3f}")
        lines.append(f"   利好词出现: {sentiment['positive_count']}次 | 利空词出现: {sentiment['negative_count']}次")
        if sentiment['key_phrases']:
            lines.append(f"   关键线索:")
            for phrase in sentiment['key_phrases'][:3]:
                lines.append(f"     • {phrase[:50]}")
        lines.append("")
        
        # 新闻摘要
        lines.append("📋 最新财经要闻:")
        if news:
            for i, item in enumerate(news[:5]):
                if isinstance(item, dict):
                    title = item.get('title', '无标题')[:50]
                    time_str = item.get('ctime', item.get('time', ''))
                    lines.append(f"   {i+1}. [{time_str}] {title}")
                else:
                    lines.append(f"   {i+1}. {str(item)[:50]}")
        else:
            lines.append("   暂无最新新闻")
        lines.append("")
        
        # 资金流向
        lines.append("💰 资金流向（近5日）:")
        recent = capital.get('recent', [])
        if recent:
            for day in reversed(recent[-5:]):
                date = day.get('date', '')
                main = day.get('main_net_inflow', 0)
                main_str = f"+{main:.0f}" if main > 0 else f"{main:.0f}"
                direction = "主力流入 🟢" if main > 0 else "主力流出 🔴"
                lines.append(f"   {date}: {main_str}万 {direction}")
        else:
            lines.append("   暂无资金流向数据")
        lines.append("")
        
        # 综合建议
        cap_score = sentiment['sentiment_score']
        main_flow = capital.get('latest', {}).get('main_net_inflow', 0)
        
        if cap_score > 0.2 and main_flow > 0:
            recommendation = "舆情偏多且资金流入，可关注"
        elif cap_score < -0.2 or main_flow < 0:
            recommendation = "舆情偏空或资金流出，需谨慎"
        else:
            recommendation = "舆情中性，结合技术面综合判断"
        
        return {
            'agent': '研究员',
            'report': '\n'.join(lines),
            'sentiment': sentiment['sentiment'],
            'sentiment_score': sentiment['sentiment_score'],
            'news_summary': news[:5],
            'capital_flow': capital,
            'recommendation': recommendation,
        }
