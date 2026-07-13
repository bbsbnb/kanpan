#!/usr/bin/env python3
"""AI智能看盘系统 - 主入口

使用方式:
    python main.py --code 600519              # 分析单只股票
    python main.py --codes 600519,000858       # 分析多只股票
    python main.py --watch                     # 持续监控模式
    python main.py --help                      # 查看帮助
"""
import argparse
import yaml
import sys
import os
import time
from datetime import datetime

from loguru import logger
from data.fetcher import DataFetcher
from data.cache import DataCache
from agents.analyst import AnalystAgent
from agents.researcher import ResearcherAgent
from agents.trader import TraderAgent
from agents.risk_manager import RiskManagerAgent
from agents.portfolio_mgr import PortfolioManagerAgent


def load_config(config_path: str = "config.yaml") -> dict:
    """加载配置文件"""
    if os.path.exists(config_path):
        with open(config_path, 'r', encoding='utf-8') as f:
            return yaml.safe_load(f)
    return {}


def run_single_stock(fetcher: DataFetcher, analyst: AnalystAgent, 
                     researcher: ResearcherAgent, trader: TraderAgent,
                     risk_mgr: RiskManagerAgent, portfolio_mgr: PortfolioManagerAgent,
                     symbol: str, config: dict):
    """运行单只股票的完整分析流程"""
    
    print(f"\n{'#'*60}")
    print(f"# AI智能看盘系统 — {symbol}")
    print(f"{'#'*60}")
    
    # ========== Step 0: 获取数据 ==========
    print("\n📡 [Step 0] 获取行情数据...")
    df = fetcher.get_historical_kline(symbol, days=config.get('indicators', {}).get('lookback_days', 120))
    
    if df.empty:
        print(f"❌ 无法获取 {symbol} 的K线数据，请检查股票代码")
        return None
    
    # 获取股票名称
    stock_info = fetcher.get_stock_info(symbol)
    stock_name = stock_info.get('name', symbol)
    current_price = stock_info.get('price', 0)
    change_pct = stock_info.get('change_pct', 0)
    
    print(f"   ✅ {stock_name}({symbol}) 当前价: ¥{current_price:.2f} ({change_pct:+.2f}%)")
    print(f"   📊 获取到 {len(df)} 条K线数据")
    
    # ========== Step 1: 分析师Agent ==========
    print("\n🔍 [Step 1] 分析师Agent - 技术面分析...")
    analyst_result = analyst.analyze({
        'symbol': symbol,
        'df': df,
        'stock_name': stock_name,
    })
    print(analyst_result.get('report', ''))
    
    indicators = analyst_result.get('indicators', {})
    
    # ========== Step 2: 研究员Agent ==========
    print("\n📰 [Step 2] 研究员Agent - 舆情分析(MVP预留)...")
    researcher_result = researcher.analyze({'symbol': symbol})
    print(researcher_result.get('report', ''))
    
    # ========== Step 3: 交易员Agent ==========
    print("\n💹 [Step 3] 交易员Agent - 交易决策...")
    trader_result = trader.analyze({
        'symbol': symbol,
        'analyst_result': analyst_result,
        'researcher_result': researcher_result,
    })
    print(f"   动作: {trader_result['action']}")
    print(f"   置信度: {trader_result['confidence']*100:.0f}%")
    print(f"   建议仓位: {trader_result['position_pct']*100:.1f}%")
    print(f"   止损价: ¥{trader_result['stop_loss']:.2f}")
    print(f"   止盈价: ¥{trader_result['take_profit']:.2f}")
    print(f"   理由: {trader_result['reasoning']}")
    
    # ========== Step 4: 风控Agent ==========
    print("\n🛡️  [Step 4] 风控Agent - 风险评估...")
    risk_result = risk_mgr.analyze({
        'symbol': symbol,
        'trader_result': trader_result,
        'indicators': indicators,
    })
    print(f"   风险等级: {risk_result['risk_level']}")
    print(f"   风险评分: {risk_result['risk_score']}")
    print(f"   是否通过: {'✅ 通过' if risk_result['pass'] else '❌ 不通过'}")
    for w in risk_result.get('warnings', []):
        print(f"   {w}")
    for s in risk_result.get('suggestions', []):
        print(f"   💡 {s}")
    
    # ========== Step 5: 投资经理Agent ==========
    print("\n👔 [Step 5] 投资经理Agent - 最终决策...")
    final_result = portfolio_mgr.analyze({
        'symbol': symbol,
        'analyst_result': analyst_result,
        'researcher_result': researcher_result,
        'trader_result': trader_result,
        'risk_result': risk_result,
    })
    print(final_result.get('summary', ''))
    
    return final_result


def run_watch_mode(fetcher: DataFetcher, config: dict):
    """持续监控模式"""
    codes = config.get('trading', {}).get('default_codes', ['600519'])
    interval = 60  # 刷新间隔(秒)
    
    print(f"\n🔔 监控模式启动")
    print(f"   监控标的: {', '.join(codes)}")
    print(f"   刷新间隔: {interval}秒")
    print(f"   按 Ctrl+C 退出\n")
    
    try:
        while True:
            now = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            print(f"\n{'='*60}")
            print(f"⏰ {now}")
            
            for code in codes:
                info = fetcher.get_stock_info(code)
                if info:
                    name = info.get('name', code)
                    price = info.get('price', 0)
                    pct = info.get('change_pct', 0)
                    emoji = "🔴" if pct < 0 else ("🟢" if pct > 0 else "⚪")
                    print(f"   {emoji} {name}({code}): ¥{price:.2f} ({pct:+.2f}%)")
            
            time.sleep(interval)
            
    except KeyboardInterrupt:
        print("\n\n👋 监控已停止")


def main():
    parser = argparse.ArgumentParser(
        description="AI智能看盘系统 - MVP版本",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
示例:
  python main.py --code 600519              # 分析贵州茅台
  python main.py --codes 600519,000858      # 分析多只股票
  python main.py --watch                    # 持续监控模式
        """
    )
    
    parser.add_argument('--code', type=str, help='股票代码，如 600519')
    parser.add_argument('--codes', type=str, help='多只股票代码，逗号分隔，如 600519,000858')
    parser.add_argument('--watch', action='store_true', help='持续监控模式')
    parser.add_argument('--config', type=str, default='config.yaml', help='配置文件路径')
    
    args = parser.parse_args()
    
    # 加载配置
    config = load_config(args.config)
    
    # 初始化组件
    cache = DataCache(
        cache_dir=config.get('data', {}).get('cache_dir', './data/cache'),
        ttl_hours=config.get('data', {}).get('cache_ttl', 24),
    )
    fetcher = DataFetcher(cache)
    indicator_config = config.get('indicators', {})
    risk_config = config.get('risk', {})
    
    analyst = AnalystAgent(indicator_config)
    researcher = ResearcherAgent()
    trader = TraderAgent()
    risk_mgr = RiskManagerAgent(risk_config)
    portfolio_mgr = PortfolioManagerAgent()
    
    if args.watch:
        run_watch_mode(fetcher, config)
    elif args.code:
        run_single_stock(fetcher, analyst, researcher, trader, risk_mgr, portfolio_mgr, 
                        args.code, config)
    elif args.codes:
        codes = [c.strip() for c in args.codes.split(',')]
        results = []
        for code in codes:
            result = run_single_stock(fetcher, analyst, researcher, trader, risk_mgr, 
                                     portfolio_mgr, code, config)
            if result:
                results.append((code, result))
        
        # 汇总
        if results:
            print(f"\n{'='*60}")
            print("📋 汇总报告")
            print(f"{'='*60}")
            for code, result in results:
                action = result.get('final_action', 'hold')
                approved = result.get('approved', False)
                position = result.get('position_pct', 0)
                status = "✅" if approved and action != 'hold' else ("⏸️" if not approved else "➖")
                print(f"   {status} {code}: {action.upper()} (仓位:{position*100:.1f}%)")
    else:
        # 默认分析配置中的股票
        default_codes = config.get('trading', {}).get('default_codes', ['600519'])
        results = []
        for code in default_codes:
            result = run_single_stock(fetcher, analyst, researcher, trader, risk_mgr, 
                                     portfolio_mgr, code, config)
            if result:
                results.append((code, result))
        
        if results:
            print(f"\n{'='*60}")
            print("📋 汇总报告")
            print(f"{'='*60}")
            for code, result in results:
                action = result.get('final_action', 'hold')
                approved = result.get('approved', False)
                position = result.get('position_pct', 0)
                status = "✅" if approved and action != 'hold' else ("⏸️" if not approved else "➖")
                print(f"   {status} {code}: {action.upper()} (仓位:{position*100:.1f}%)")


if __name__ == '__main__':
    main()
