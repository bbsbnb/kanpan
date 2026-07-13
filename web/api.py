"""FastAPI后端 — AI智能看盘系统Web看板"""
import asyncio
import json
import yaml
from datetime import datetime
from typing import Optional, List, Any
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse, HTMLResponse
from pydantic import BaseModel
import os

# 自定义JSON编码器，处理numpy类型
class NumpyEncoder(json.JSONEncoder):
    def default(self, obj):
        import numpy as np
        if isinstance(obj, (np.integer,)):
            return int(obj)
        elif isinstance(obj, (np.floating,)):
            return float(obj)
        elif isinstance(obj, np.ndarray):
            return obj.tolist()
        return super().default(obj)

def custom_json_dumps(obj, **kwargs):
    """使用自定义编码器序列化为JSON"""
    return json.dumps(obj, cls=NumpyEncoder, **kwargs)

# 导入项目模块
sys_path = os.path.join(os.path.dirname(__file__), '..')
if sys_path not in __import__('sys').path:
    __import__('sys').path.insert(0, sys_path)

from data.fetcher import DataFetcher
from data.cache import DataCache
from agents.analyst import AnalystAgent
from agents.researcher import ResearcherAgent
from agents.trader import TraderAgent
from agents.risk_manager import RiskManagerAgent
from agents.portfolio_mgr import PortfolioManagerAgent
from indicators.ta_engine import TechnicalEngine

# ========== 配置 ==========
CONFIG_PATH = os.path.join(sys_path, 'config.yaml')
with open(CONFIG_PATH, 'r', encoding='utf-8') as f:
    CONFIG = yaml.safe_load(f)

# ========== 初始化组件 ==========
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

# ========== FastAPI App ==========
app = FastAPI(title="AI智能看盘系统", version="0.1.0")

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

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
    html_path = os.path.join(os.path.dirname(__file__), 'templates', 'index.html')
    if os.path.exists(html_path):
        with open(html_path, 'r', encoding='utf-8') as f:
            return f.read()
    return "<h1>AI智能看盘系统</h1><p>请安装前端模板</p>"

# ========== API端点 ==========

@app.get("/api/health")
async def health_check():
    """健康检查"""
    return {"status": "ok", "time": datetime.now().isoformat()}

@app.get("/api/default-codes")
async def get_default_codes():
    """获取默认监控列表"""
    return {
        "codes": CONFIG.get('trading', {}).get('default_codes', ['600519'])
    }

@app.get("/api/watchlist")
async def get_watchlist():
    """获取自选股实时行情"""
    codes = CONFIG.get('trading', {}).get('default_codes', ['600519'])
    results = []
    for code in codes:
        info = fetcher.get_stock_info(code)
        if info.get('name'):
            results.append(info)
    return {"stocks": results}

@app.post("/api/analyze")
async def analyze_stock(req: StockCodeRequest):
    """分析单只股票（完整5-Agent流水线）"""
    symbol = req.code
    
    # 获取K线
    df = fetcher.get_historical_kline(symbol, days=req.days)
    if df.empty:
        raise HTTPException(status_code=400, detail=f"无法获取 {symbol} 的K线数据")
    
    # 获取基本信息
    stock_info = fetcher.get_stock_info(symbol)
    stock_name = stock_info.get('name', symbol)
    
    # Agent 1: 分析师
    analyst_result = analyst.analyze({
        'symbol': symbol, 'df': df, 'stock_name': stock_name,
    })
    
    # Agent 2: 研究员
    researcher_result = researcher.analyze({
        'symbol': symbol, 'stock_name': stock_name,
    })
    
    # Agent 3: 交易员
    trader_result = trader.analyze({
        'symbol': symbol,
        'analyst_result': analyst_result,
        'researcher_result': researcher_result,
    })
    
    # Agent 4: 风控
    risk_result = risk_mgr.analyze({
        'symbol': symbol,
        'trader_result': trader_result,
        'indicators': analyst_result.get('indicators', {}),
    })
    
    # Agent 5: 投资经理
    final_result = portfolio_mgr.analyze({
        'symbol': symbol,
        'analyst_result': analyst_result,
        'researcher_result': researcher_result,
        'trader_result': trader_result,
        'risk_result': risk_result,
    })
    
    # 转换numpy类型为Python原生类型，并处理NaN/Inf等特殊值
    import numpy as np
    import math
    
    def convert_numpy_types(obj):
        if isinstance(obj, dict):
            return {k: convert_numpy_types(v) for k, v in obj.items()}
        elif isinstance(obj, list):
            return [convert_numpy_types(item) for item in obj]
        elif isinstance(obj, (np.integer,)):
            return int(obj)
        elif isinstance(obj, (np.floating,)):
            val = float(obj)
            if math.isnan(val) or math.isinf(val):
                return 0.0
            return val
        elif isinstance(obj, np.ndarray):
            arr = obj.tolist()
            return convert_numpy_types(arr)
        elif isinstance(obj, float):
            if math.isnan(obj) or math.isinf(obj):
                return 0.0
            return obj
        else:
            return obj
    
    # 递归转换所有结果
    analyst_result = convert_numpy_types(analyst_result)
    researcher_result = convert_numpy_types(researcher_result)
    trader_result = convert_numpy_types(trader_result)
    risk_result = convert_numpy_types(risk_result)
    final_result = convert_numpy_types(final_result)
    
    # 返回K线数据用于图表
    kline_data = df.tail(60).to_dict('records')
    kline_data = convert_numpy_types(kline_data)
    
    return {
        'symbol': symbol,
        'name': stock_name,
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
    """批量分析多只股票"""
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
    """获取K线数据（供前端图表使用）"""
    df = fetcher.get_historical_kline(symbol, days=days)
    if df.empty:
        raise HTTPException(status_code=400, detail=f"无数据: {symbol}")
    return {
        'symbol': symbol,
        'data': df.tail(days).to_dict('records'),
    }

@app.get("/api/info/{symbol}")
async def get_stock_info(symbol: str):
    """获取股票基本信息"""
    info = fetcher.get_stock_info(symbol)
    if not info.get('name'):
        raise HTTPException(status_code=404, detail=f"未找到股票: {symbol}")
    return info
