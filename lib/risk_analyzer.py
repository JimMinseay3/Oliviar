import pandas as pd
import numpy as np

def calculate_historical_volatility(df: pd.DataFrame, window: int = 20):
    """计算历史年化波动率 (HV)"""
    if df is None or len(df) < window + 1:
        return None
    try:
        prices = pd.to_numeric(df['收盘'], errors='coerce').dropna()
        log_returns = np.log(prices / prices.shift(1))
        vol = log_returns.rolling(window=window).std() * np.sqrt(252)
        return vol.iloc[-1]
    except Exception:
        return None

def analyze_liquidity_depth(tick_data: pd.DataFrame):
    """基于五档买卖盘数据分析流动性深度"""
    try:
        ask_vols = [f'sell_{i}_vol' for i in range(1, 6)]
        bid_vols = [f'buy_{i}_vol' for i in range(1, 6)]
        total_ask = tick_data[tick_data['item'].isin(ask_vols)]['value'].sum()
        total_bid = tick_data[tick_data['item'].isin(bid_vols)]['value'].sum()
        assessment = "充裕" if total_ask > 10000 else "中/低"
        return {"total_ask_depth": total_ask, "total_bid_depth": total_bid, "assessment": assessment}
    except Exception:
        return None

def calculate_sector_correlation(stock_df: pd.DataFrame, industry_df: pd.DataFrame):
    """计算个股与行业板块的相关性"""
    try:
        stock_close = stock_df.set_index('日期')['收盘'].astype(float)
        industry_close = industry_df.set_index('日期')['收盘'].astype(float)
        combined = pd.concat([stock_close, industry_close], axis=1, join='inner')
        return combined.corr().iloc[0, 1]
    except Exception:
        return None
