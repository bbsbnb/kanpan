"""数据获取模块 - 直连Sina/Tencent API（绕过AKShare代理问题）"""
import urllib.request
import json
import pandas as pd
from datetime import datetime, timedelta
from loguru import logger
from data.cache import DataCache


class DataFetcher:
    """行情数据获取器（Sina + Tencent直连API）"""
    
    def __init__(self, cache: DataCache = None):
        self.cache = cache or DataCache()
    
    def _market_prefix(self, symbol: str) -> str:
        """根据A股代码判断交易所前缀。"""
        if symbol.startswith(('4', '8')):
            return 'bj'
        return 'sh' if symbol.startswith('6') else 'sz'
    
    def _get_sina_quote(self, symbol: str) -> dict:
        """获取新浪实时报价"""
        market = self._market_prefix(symbol)
        url = f"https://hq.sinajs.cn/list={market}{symbol}"
        req = urllib.request.Request(url, headers={"Referer": "https://finance.sina.com.cn"})
        
        resp = urllib.request.urlopen(req, timeout=10)
        text = resp.read().decode('gbk')
        
        parts = text.split('"')[1].split(',')
        if len(parts) < 32:
            return {}
        
        return {
            'name': parts[0],
            'open': float(parts[1]),
            'prev_close': float(parts[2]),
            'close': float(parts[3]),
            'high': float(parts[4]),
            'low': float(parts[5]),
            'volume': float(parts[8]),
            'amount': float(parts[9]),
            'date': parts[30] if len(parts) > 30 else '',
            'time': parts[31] if len(parts) > 31 else '',
        }
    
    def _get_sina_kline(self, symbol: str, days: int = 120) -> pd.DataFrame:
        """
        获取新浪历史K线数据
        返回: DataFrame with [date, open, close, high, low, volume]
        """
        market = self._market_prefix(symbol)
        cache_key = f"sina_kline_{market}{symbol}_{days}"
        cached = self.cache.get(cache_key)
        if cached is not None:
            logger.debug(f"使用新浪K线缓存: {cache_key}")
            return pd.DataFrame(cached)
        
        try:
            url = (f"https://money.finance.sina.com.cn/quotes_service/api/"
                   f"json_v2.php/CN_MarketData.getKLineData?"
                   f"symbol={market}{symbol}&scale=240&ma=no&datalen={days}")
            
            resp = urllib.request.urlopen(url, timeout=10)
            raw = resp.read().decode('utf-8')
            records = json.loads(raw)
            
            if not records:
                logger.warning(f"新浪K线数据为空: {symbol}")
                return pd.DataFrame()
            
            df = pd.DataFrame(records)
            df = df.rename(columns={'day': 'date'})
            
            for col in ['open', 'close', 'high', 'low', 'volume']:
                df[col] = pd.to_numeric(df[col], errors='coerce')
            
            df = df.sort_values('date').reset_index(drop=True)
            
            self.cache.set(cache_key, df.to_dict('records'))
            logger.info(f"获取新浪K线数据成功: {symbol}, {len(df)}条")
            return df
            
        except Exception as e:
            logger.error(f"获取新浪K线失败: {e}")
            return pd.DataFrame()
    
    def get_stock_realtime(self, symbol: str) -> dict:
        """获取实时行情"""
        cache_key = f"realtime_{symbol}"
        cached = self.cache.get(cache_key)
        if cached is not None:
            return cached
        
        try:
            quote = self._get_sina_quote(symbol)
            if quote:
                quote['code'] = symbol
                quote['change'] = quote['close'] - quote['prev_close']
                quote['change_pct'] = (quote['change'] / quote['prev_close'] * 100) if quote['prev_close'] else 0
                self.cache.set(cache_key, quote)
                return quote
        except Exception as e:
            logger.error(f"获取新浪实时行情失败: {e}")
        
        return {'code': symbol}
    
    def get_historical_kline(self, symbol: str, period: str = "daily", 
                             days: int = 120) -> pd.DataFrame:
        """获取历史K线数据（主方法）"""
        logger.info(f"获取K线数据: {symbol}, {days}天")
        return self._get_sina_kline(symbol, days)
    
    def get_stock_info(self, symbol: str) -> dict:
        """获取股票基本信息"""
        cache_key = f"info_{symbol}"
        cached = self.cache.get(cache_key)
        if cached is not None:
            return cached
        
        try:
            quote = self._get_sina_quote(symbol)
            if quote:
                result = {
                    'code': symbol,
                    'name': quote.get('name', ''),
                    'price': quote.get('close', 0),
                    'change_pct': quote.get('change_pct', 0),
                    'volume': quote.get('volume', 0),
                    'amount': quote.get('amount', 0),
                }
                self.cache.set(cache_key, result)
                return result
        except Exception as e:
            logger.error(f"获取股票信息失败: {e}")
        
        return {'code': symbol}
    
    def get_watchlist(self, codes: list) -> list:
        """批量获取自选股实时行情"""
        results = []
        for code in codes:
            info = self.get_stock_info(code)
            if info.get('name'):
                results.append(info)
        return results
