"""技术指标计算引擎"""
import pandas as pd
import numpy as np
from typing import Dict, List, Optional, Tuple
from loguru import logger


class TechnicalEngine:
    """技术指标计算引擎"""
    
    def __init__(self, config: dict = None):
        self.config = config or {}
        self.ma_periods = self.config.get("ma_periods", [5, 10, 20, 60, 120, 250])
        self.macd_fast = self.config.get("macd", {}).get("fast", 12)
        self.macd_slow = self.config.get("macd", {}).get("slow", 26)
        self.macd_signal = self.config.get("macd", {}).get("signal", 9)
        self.rsi_period = self.config.get("rsi_period", 14)
        self.boll_period = self.config.get("boll", {}).get("period", 20)
        self.boll_std = self.config.get("boll", {}).get("std", 2)
    
    def calculate_all(self, df: pd.DataFrame) -> pd.DataFrame:
        """计算所有技术指标"""
        logger.info(f"计算技术指标，数据量: {len(df)}")
        
        df = self._add_ma(df)
        df = self._add_macd(df)
        df = self._add_rsi(df)
        df = self._add_bollinger(df)
        df = self._add_kdj(df)
        df = self._add_volume_ratio(df)
        df = self._add_atr(df)
        
        return df
    
    def _add_ma(self, df: pd.DataFrame) -> pd.DataFrame:
        """均线系统"""
        for period in self.ma_periods:
            df[f'MA{period}'] = df['close'].rolling(window=period).mean()
        return df
    
    def _add_macd(self, df: pd.DataFrame) -> pd.DataFrame:
        """MACD指标"""
        ema_fast = df['close'].ewm(span=self.macd_fast, adjust=False).mean()
        ema_slow = df['close'].ewm(span=self.macd_slow, adjust=False).mean()
        df['DIF'] = ema_fast - ema_slow
        df['DEA'] = df['DIF'].ewm(span=self.macd_signal, adjust=False).mean()
        df['MACD'] = 2 * (df['DIF'] - df['DEA'])
        return df
    
    def _add_rsi(self, df: pd.DataFrame) -> pd.DataFrame:
        """RSI指标"""
        delta = df['close'].diff()
        gain = delta.where(delta > 0, 0).rolling(window=self.rsi_period).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(window=self.rsi_period).mean()
        rs = gain / loss
        df['RSI'] = 100 - (100 / (1 + rs))
        return df
    
    def _add_bollinger(self, df: pd.DataFrame) -> pd.DataFrame:
        """布林带"""
        df['BOLL_MID'] = df['close'].rolling(window=self.boll_period).mean()
        std = df['close'].rolling(window=self.boll_period).std()
        df['BOLL_UP'] = df['BOLL_MID'] + self.boll_std * std
        df['BOLL_DOWN'] = df['BOLL_MID'] - self.boll_std * std
        return df
    
    def _add_kdj(self, df: pd.DataFrame) -> pd.DataFrame:
        """KDJ指标"""
        low_min = df['low'].rolling(window=9).min()
        high_max = df['high'].rolling(window=9).max()
        rsv = (df['close'] - low_min) / (high_max - low_min) * 100
        
        k = rsv.ewm(com=2, adjust=False).mean()
        d = k.ewm(com=2, adjust=False).mean()
        j = 3 * k - 2 * d
        
        df['K'] = k
        df['D'] = d
        df['J'] = j
        return df
    
    def _add_volume_ratio(self, df: pd.DataFrame) -> pd.DataFrame:
        """量比"""
        df['volume_ma5'] = df['volume'].rolling(window=5).mean()
        df['volume_ratio'] = df['volume'] / df['volume_ma5']
        return df
    
    def _add_atr(self, df: pd.DataFrame) -> pd.DataFrame:
        """ATR平均真实波幅"""
        high_low = df['high'] - df['low']
        high_close = np.abs(df['high'] - df['close'].shift())
        low_close = np.abs(df['low'] - df['close'].shift())
        tr = pd.concat([high_low, high_close, low_close], axis=1).max(axis=1)
        df['ATR'] = tr.rolling(window=14).mean()
        return df
    
    def get_latest_indicators(self, df: pd.DataFrame) -> Dict:
        """获取最新一根K线的指标值"""
        if len(df) < 2:
            return {}
        
        latest = df.iloc[-1]
        prev = df.iloc[-2]
        
        # 计算趋势变化
        macd_trend = "金叉" if (prev['DIF'] < prev['DEA'] and latest['DIF'] > latest['DEA']) else \
                     "死叉" if (prev['DIF'] > prev['DEA'] and latest['DIF'] < latest['DEA']) else \
                     "持平"
        
        kdj_trend = "金叉" if (prev['K'] < prev['D'] and latest['K'] > latest['D']) else \
                    "死叉" if (prev['K'] > prev['D'] and latest['K'] < latest['D']) else \
                    "持平"
        
        return {
            'date': latest.get('date', ''),
            'close': latest['close'],
            'open': latest['open'],
            'high': latest['high'],
            'low': latest['low'],
            'volume': latest['volume'],
            'volume_ratio': latest.get('volume_ratio', 0),
            'ma5': latest.get('MA5', 0),
            'ma10': latest.get('MA10', 0),
            'ma20': latest.get('MA20', 0),
            'ma60': latest.get('MA60', 0),
            'dif': latest.get('DIF', 0),
            'dea': latest.get('DEA', 0),
            'macd': latest.get('MACD', 0),
            'macd_trend': macd_trend,
            'rsi': latest.get('RSI', 0),
            'k': latest.get('K', 0),
            'd': latest.get('D', 0),
            'j': latest.get('J', 0),
            'kdj_trend': kdj_trend,
            'boll_up': latest.get('BOLL_UP', 0),
            'boll_mid': latest.get('BOLL_MID', 0),
            'boll_down': latest.get('BOLL_DOWN', 0),
            'atr': latest.get('ATR', 0),
        }
    
    def generate_technical_report(self, df: pd.DataFrame, stock_name: str = "") -> str:
        """生成技术分析报告"""
        ind = self.get_latest_indicators(df)
        if not ind:
            return "无有效数据"
        
        lines = []
        lines.append(f"{'='*50}")
        lines.append(f"📊 {stock_name} 技术分析报告")
        lines.append(f"{'='*50}")
        lines.append(f"📅 日期: {ind['date']}")
        lines.append(f"💰 现价: ¥{ind['close']:.2f}")
        lines.append("")
        
        # 均线分析
        lines.append("📈 均线系统:")
        ma_status = self._analyze_ma(ind)
        lines.append(f"   {ma_status}")
        for period in [5, 10, 20, 60]:
            key = f'ma{period}'
            if key in ind and ind[key]:
                lines.append(f"   MA{period}: ¥{ind[key]:.2f}")
        lines.append("")
        
        # MACD分析
        lines.append("📊 MACD指标:")
        lines.append(f"   DIF: {ind['dif']:.4f}")
        lines.append(f"   DEA: {ind['dea']:.4f}")
        lines.append(f"   MACD柱: {ind['macd']:.4f}")
        lines.append(f"   信号: {ind['macd_trend']}")
        macd_status = self._analyze_macd(ind)
        lines.append(f"   解读: {macd_status}")
        lines.append("")
        
        # RSI分析
        lines.append("⚡ RSI指标:")
        lines.append(f"   RSI(14): {ind['rsi']:.2f}")
        rsi_status = self._analyze_rsi(ind)
        lines.append(f"   解读: {rsi_status}")
        lines.append("")
        
        # KDJ分析
        lines.append("🎯 KDJ指标:")
        lines.append(f"   K: {ind['k']:.2f}")
        lines.append(f"   D: {ind['d']:.2f}")
        lines.append(f"   J: {ind['j']:.2f}")
        lines.append(f"   信号: {ind['kdj_trend']}")
        kdj_status = self._analyze_kdj(ind)
        lines.append(f"   解读: {kdj_status}")
        lines.append("")
        
        # 布林带分析
        lines.append("📐 布林带:")
        lines.append(f"   上轨: ¥{ind['boll_up']:.2f}")
        lines.append(f"   中轨: ¥{ind['boll_mid']:.2f}")
        lines.append(f"   下轨: ¥{ind['boll_down']:.2f}")
        boll_status = self._analyze_boll(ind)
        lines.append(f"   解读: {boll_status}")
        lines.append("")
        
        # 量能分析
        lines.append("📊 量能分析:")
        vr = ind.get('volume_ratio', 0)
        lines.append(f"   量比: {vr:.2f}")
        vol_status = "放量" if vr > 1.5 else ("缩量" if vr < 0.8 else "平量")
        lines.append(f"   状态: {vol_status}")
        lines.append("")
        
        # 综合研判
        lines.append("🎯 综合研判:")
        score = self._calculate_score(ind)
        signals = self._collect_signals(ind)
        lines.append(f"   多头信号: {signals['bullish']}个")
        lines.append(f"   空头信号: {signals['bearish']}个")
        lines.append(f"   中性信号: {signals['neutral']}个")
        
        if score > 0.3:
            verdict = "偏多 📈"
        elif score < -0.3:
            verdict = "偏空 📉"
        else:
            verdict = "震荡 ⚖️"
        lines.append(f"   结论: {verdict}")
        lines.append(f"{'='*50}")
        
        return "\n".join(lines)
    
    def _analyze_ma(self, ind: Dict) -> str:
        """均线分析"""
        ma5 = ind.get('ma5', 0)
        ma10 = ind.get('ma10', 0)
        ma20 = ind.get('ma20', 0)
        close = ind['close']
        
        if close > ma5 > ma10 > ma20:
            return "多头排列 ✅"
        elif close < ma5 < ma10 < ma20:
            return "空头排列 ❌"
        else:
            return "均线纠缠 ⚠️"
    
    def _analyze_macd(self, ind: Dict) -> str:
        """MACD分析"""
        if ind['dif'] > 0 and ind['dea'] > 0:
            return "零轴上方，多头区域"
        elif ind['dif'] < 0 and ind['dea'] < 0:
            return "零轴下方，空头区域"
        else:
            return "零轴附近，方向不明"
    
    def _analyze_rsi(self, ind: Dict) -> str:
        """RSI分析"""
        rsi = ind['rsi']
        if rsi > 80:
            return "超买区域，注意回调风险"
        elif rsi > 60:
            return "强势区域"
        elif rsi < 20:
            return "超卖区域，关注反弹机会"
        elif rsi < 40:
            return "弱势区域"
        else:
            return "中性区域"
    
    def _analyze_kdj(self, ind: Dict) -> str:
        """KDJ分析"""
        j = ind['j']
        if j > 100:
            return "严重超买"
        elif j > 80:
            return "超买区域"
        elif j < 0:
            return "严重超卖"
        elif j < 20:
            return "超卖区域"
        else:
            return "中性区域"
    
    def _analyze_boll(self, ind: Dict) -> str:
        """布林带分析"""
        close = ind['close']
        up = ind['boll_up']
        down = ind['boll_down']
        mid = ind['boll_mid']
        
        if close >= up:
            return "触及上轨，可能承压"
        elif close <= down:
            return "触及下轨，可能支撑"
        elif close > mid:
            return "在中轨上方，偏强"
        else:
            return "在中轨下方，偏弱"
    
    def _calculate_score(self, ind: Dict) -> float:
        """综合打分 -1到1"""
        score = 0.0
        
        # 均线得分
        close = ind['close']
        if close > ind.get('ma5', 0): score += 0.1
        if close > ind.get('ma10', 0): score += 0.1
        if close > ind.get('ma20', 0): score += 0.15
        if close > ind.get('ma60', 0): score += 0.15
        
        # MACD得分
        if ind['dif'] > ind['dea']: score += 0.15
        if ind['macd'] > 0: score += 0.05
        
        # RSI得分
        rsi = ind.get('rsi', 50)
        if 45 < rsi < 70: score += 0.1  # 健康区间
        elif rsi > 80: score -= 0.1  # 超买扣分
        
        # KDJ得分
        if ind.get('k', 50) > ind.get('d', 50): score += 0.05
        
        return max(-1.0, min(1.0, score))
    
    def _collect_signals(self, ind: Dict) -> Dict:
        """收集买卖信号"""
        bullish = 0
        bearish = 0
        neutral = 0
        
        # 均线信号
        close = ind['close']
        if close > ind.get('ma5', 0): bullish += 1
        else: bearish += 1
        if close > ind.get('ma20', 0): bullish += 1
        else: bearish += 1
        
        # MACD信号
        if ind['dif'] > ind['dea']: bullish += 1
        else: bearish += 1
        
        # RSI信号
        rsi = ind.get('rsi', 50)
        if 40 < rsi < 70: bullish += 1
        elif rsi > 80: bearish += 1
        elif rsi < 20: bullish += 1
        else: neutral += 1
        
        # KDJ信号
        if ind.get('k', 50) > ind.get('d', 50): bullish += 1
        else: bearish += 1
        
        return {'bullish': bullish, 'bearish': bearish, 'neutral': neutral}
