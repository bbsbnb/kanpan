"""AI智能看盘系统 — Web服务入口
使用方式:
    python app.py                      # 开发模式 (localhost:8000)
    
云平台 (Render/Heroku):
    自动读取 $PORT 环境变量
"""
import os
import sys
import threading
import time

# 将项目根目录加入 Python 路径
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, HTMLResponse
from pydantic import BaseModel
from typing import Optional, List
from datetime import datetime
import yaml
import math
import numpy as np

# ========== 导入项目模块 ==========
from data.fetcher import DataFetcher
from data.cache import DataCache
from agents.analyst import AnalystAgent
from agents.researcher import ResearcherAgent
from agents.trader import TraderAgent
from agents.risk_manager import RiskManagerAgent
from agents.portfolio_mgr import PortfolioManagerAgent
# 导入main里的持续监控函数
from main import run_watch_mode

# ========== 配置加载 ==========
CONFIG_PATH = os.path.join(os.path.dirname(__file__), 'config.yaml')
with open(CONFIG_PATH, 'r', encoding='utf-8') as f:
    CONFIG = yaml.safe_load(f)

# ========== 初始化组件（全局单例） ==========
cache = DataCache(
    cache_dir=CONFIG.get('data', {}).get('cache_dir', './data/cache'),
    ttl_hours=CONFIG.get('data', {}).get('cache_ttl', 24),
)
fetcher = DataFetcher(cache)
indicator_config = CONFIG.get('indicators', {})
risk_config = CONFIG.get('risk', {})

analyst = AnalystAgent(indicator_config)
researcher = ResearcherAgent()
trader = TraderAgent()
risk_mgr = RiskManagerAgent(risk_config)
portfolio_mgr = PortfolioManagerAgent()

# ========== 后台持续股票监控任务（守护线程，不阻塞Web主线程） ==========
def stock_monitor_daemon():
    print("后台股票监控线程已启动，循环刷新自选股...")
    # 调用main里的持续监控逻辑
    run_watch_mode(fetcher, CONFIG)

# ========== Numpy 类型转换 ==========
def convert_numpy_types(obj):
    """递归将 numpy/pandas 类型转换为 Python 原生类型"""
    if isinstance(obj, dict):
        return {k: convert_numpy_types(v) for k, v in obj.items()}
    elif isinstance(obj, list):
        return [convert_numpy_types(item) for item in obj]
    elif isinstance(obj, (np.integer,)):
        return int(obj)
    elif isinstance(obj, (np.floating,)):
        val = float(obj)
        if math.isnan(val) or math.isinf(val):
            return None
        return val
    elif isinstance(obj, np.ndarray):
        return convert_numpy_types(obj.tolist())
    elif isinstance(obj, float):
        if math.isnan(obj) or math.isinf(obj):
            return None
        return obj
    elif isinstance(obj, np.bool_):
        return bool(obj)
    else:
        return obj

# ========== FastAPI App ==========
app = FastAPI(
    title="AI智能看盘系统",
    description="5-Agent协同分析股票",
    version="0.1.0",
)

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ========== 服务启动钩子：Web启动同时拉起后台监控 ==========
@app.on_event("startup")
def start_monitor_thread():
    if os.environ.get('ENABLE_WEB_MONITOR', '0') != '1':
        print("后台股票监控线程未启动；如需启用，请设置 ENABLE_WEB_MONITOR=1")
        return
    # 创建守护线程，主服务退出时自动销毁监控
    monitor_thread = threading.Thread(target=stock_monitor_daemon, daemon=True)
    monitor_thread.start()
    print("Web服务启动完成，后台监控线程已后台运行")

# ========== 数据模型 ==========
class StockCodeRequest(BaseModel):
    code: str
    days: int = 120

class BatchCodesRequest(BaseModel):
    codes: List[str]
    days: int = 120

# ========== 首页 ==========
@app.get("/", response_class=HTMLResponse)
async def index():
    html_path = os.path.join(os.path.dirname(__file__), 'web', 'templates', 'index.html')
    if os.path.exists(html_path):
        with open(html_path, 'r', encoding='utf-8') as f:
            return f.read()
    return HTMLResponse("""
    <html><head><title>AI智能看盘系统</title></head>
    <body style="font-family:system-ui;padding:40px;">
    <h1>🤖 AI智能看盘系统</h1>
    <p>状态: <strong>运行中</strong></p>
    <ul>
        <li><a href="/docs">API 文档</a></li>
        <li><a href="/api/health">健康检查</a></li>
    </ul>
    </body></html>
    """)

# ========== API端点 ==========

@app.get("/api/health")
async def health_check():
    return {"status": "ok", "time": datetime.now().isoformat(), "version": "0.1.0"}

@app.get("/api/default-codes")
async def get_default_codes():
    return {"codes": CONFIG.get('trading', {}).get('default_codes', ['600519'])}

@app.get("/api/watchlist")
async def get_watchlist():
    codes = CONFIG.get('trading', {}).get('default_codes', ['600519'])
    results = []
    for code in codes:
        info = fetcher.get_stock_info(code)
        if info.get('name'):
            results.append(info)
    return {"stocks": results}

@app.post("/api/analyze")
async def analyze_stock(req: StockCodeRequest):
    symbol = req.code
    
    df = fetcher.get_historical_kline(symbol, days=req.days)
    if df.empty:
        raise HTTPException(status_code=400, detail=f"无法获取 {symbol} 的K线数据")
    
    stock_info = fetcher.get_stock_info(symbol)
    stock_name = stock_info.get('name', symbol)
    
    analyst_result = analyst.analyze({'symbol': symbol, 'df': df, 'stock_name': stock_name})
    researcher_result = researcher.analyze({'symbol': symbol, 'stock_name': stock_name})
    trader_result = trader.analyze({
        'symbol': symbol,
        'analyst_result': analyst_result,
        'researcher_result': researcher_result,
    })
    risk_result = risk_mgr.analyze({
        'symbol': symbol,
        'trader_result': trader_result,
        'indicators': analyst_result.get('indicators', {}),
    })
    final_result = portfolio_mgr.analyze({
        'symbol': symbol,
        'analyst_result': analyst_result,
        'researcher_result': researcher_result,
        'trader_result': trader_result,
        'risk_result': risk_result,
    })
    
    # 转换numpy类型
    analyst_result = convert_numpy_types(analyst_result)
    researcher_result = convert_numpy_types(researcher_result)
    trader_result = convert_numpy_types(trader_result)
    risk_result = convert_numpy_types(risk_result)
    final_result = convert_numpy_types(final_result)
    kline_data = convert_numpy_types(df.tail(60).to_dict('records'))
    
    return {
        'symbol': symbol, 'name': stock_name,
        'price': stock_info.get('price', 0),
        'change_pct': stock_info.get('change_pct', 0),
        'kline': kline_data,
        'analyst': analyst_result,
        'researcher': researcher_result,
        'trader': trader_result,
        'risk': risk_result,
        'final': final_result,
    }

@app.post("/api/batch-analyze")
async def batch_analyze(req: BatchCodesRequest):
    results = []
    for code in req.codes:
        try:
            result = await analyze_stock(StockCodeRequest(code=code, days=req.days))
            results.append(result)
        except Exception as e:
            results.append({'code': code, 'error': str(e)})
    return {"results": results}

@app.get("/api/kline/{symbol}")
async def get_kline(symbol: str, days: int = 60):
    df = fetcher.get_historical_kline(symbol, days=days)
    if df.empty:
        raise HTTPException(status_code=400, detail=f"无数据: {symbol}")
    return {'symbol': symbol, 'data': convert_numpy_types(df.tail(days).to_dict('records'))}

@app.get("/api/info/{symbol}")
async def get_stock_info(symbol: str):
    info = fetcher.get_stock_info(symbol)
    if not info.get('name'):
        raise HTTPException(status_code=404, detail=f"未找到股票: {symbol}")
    return info

# ========== 启动入口 ==========
if __name__ == '__main__':
    import uvicorn
    port = int(os.environ.get('PORT', 8000))
    print(f"\n{'='*50}")
    print(f"AI智能看盘系统 Web服务 启动中...")
    print(f"本地访问: http://localhost:{port}")
    print(f"API文档: http://localhost:{port}/docs")
    print(f"{'='*50}\n")
    # 监听0.0.0.0，兼容Render外网扫描端口
    uvicorn.run(app, host='0.0.0.0', port=port)
