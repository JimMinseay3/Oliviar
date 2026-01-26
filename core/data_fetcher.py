import akshare as ak
import pandas as pd
from datetime import datetime, timedelta
import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry
import re
import time
import random
import os
import json

def get_session(retries=3, backoff_factor=0.3, status_forcelist=(500, 502, 504)):
    """创建一个带有重试机制的 requests Session"""
    session = requests.Session()
    retry = Retry(
        total=retries,
        read=retries,
        connect=retries,
        backoff_factor=backoff_factor,
        status_forcelist=status_forcelist,
        raise_on_status=False
    )
    adapter = HTTPAdapter(max_retries=retry)
    session.mount('http://', adapter)
    session.mount('https://', adapter)
    return session

DEFAULT_HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Accept": "*/*",
    "Accept-Language": "zh-CN,zh;q=0.9,en;q=0.8",
    "Referer": "https://quote.eastmoney.com/",
    "Connection": "keep-alive"
}

def safe_ak_call(func, *args, **kwargs):
    """安全地调用 akshare 函数，带重试和延迟"""
    max_retries = 3
    for attempt in range(max_retries):
        try:
            # 每次调用前随机延迟
            time.sleep(random.uniform(0.2, 0.5))
            return func(*args, **kwargs)
        except Exception as e:
            if "RemoteDisconnected" in str(e) or "Connection aborted" in str(e):
                print(f"网络连接中断 (尝试 {attempt + 1}/{max_retries}): {e}")
                time.sleep(2 * (attempt + 1))
                continue
            else:
                raise e
    return None


def get_stock_list(cache_file: str = "data/stock_list_cache.csv"):
    """获取所有 A 股列表，支持降级机制"""
    # 确保 data 目录存在
    os.makedirs(os.path.dirname(cache_file), exist_ok=True)
    
    # 检查缓存是否存在且是今天生成的
    if os.path.exists(cache_file):
        file_time = datetime.fromtimestamp(os.path.getmtime(cache_file)).strftime("%Y%m%d")
        current_time = datetime.now().strftime("%Y%m%d")
        if file_time == current_time:
            try:
                return pd.read_csv(cache_file, dtype={'代码': str})
            except Exception:
                pass
    
    print("正在更新 A 股列表缓存...")
    
    # --- Level 1: AKShare (East Money) ---
    df = safe_ak_call(ak.stock_zh_a_spot_em)
    
    # --- Level 2: Sina Finance ---
    if df is None or df.empty:
        print("AKShare 列表获取失败，尝试从新浪财经获取...")
        try:
            df_sina = ak.stock_zh_a_spot()
            if df_sina is not None and not df_sina.empty:
                df_sina['代码'] = df_sina['代码'].str.replace('sh', '').str.replace('sz', '').str.replace('bj', '')
                df = df_sina
        except Exception as e:
            print(f"从新浪获取列表失败: {e}")

    # --- Level 3: AKShare (Basic Info) ---
    if df is None or df.empty:
        print("新浪列表获取失败，尝试从 AKShare 基础信息接口获取...")
        try:
            df = ak.stock_info_a_code_name()
        except Exception as e:
            print(f"基础信息获取失败: {e}")

    if df is not None and not df.empty:
        df.to_csv(cache_file, index=False, encoding="utf-8-sig")
        return df
    
    if os.path.exists(cache_file):
        print("尝试拉取最新列表失败，使用现有缓存。")
        return pd.read_csv(cache_file, dtype={'代码': str})
    
    return pd.DataFrame()

def get_symbol_by_name(name: str):
    """通过名称匹配股票代码"""
    df = get_stock_list()
    if df.empty:
        return None
    match = df[df['名称'].str.contains(name, na=False)]
    if not match.empty:
        return match.iloc[0]['代码']
    return None

def get_market_prefix(symbol: str):
    """获取股票的市场前缀 (sh/sz/bj)"""
    if symbol.startswith('6') or symbol.startswith('9'):
        return "sh"
    elif symbol.startswith('0') or symbol.startswith('3'):
        return "sz"
    elif symbol.startswith('8') or symbol.startswith('4'):
        return "bj"
    return "sh"

def fetch_ths_hist_manual(symbol: str, start_date: str, end_date: str):
    """手动从同花顺获取 K 线数据 (Level 4 兜底)"""
    # 同花顺使用 hs_000001 格式
    url = f"http://d.10jqka.com.cn/v6/line/hs_{symbol}/01/last.js"
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        "Referer": "http://yuanchuang.10jqka.com.cn/",
        "Host": "d.10jqka.com.cn"
    }
    
    try:
        session = get_session()
        session.trust_env = False
        response = session.get(url, headers=headers, timeout=10)
        
        if response.status_code == 200:
            text = response.text
            match = re.search(r'\((.*)\)', text)
            if match:
                data_str = match.group(1)
                data_json = json.loads(data_str)
                if "data" in data_json:
                    lines = data_json["data"].split(';')
                    df_data = []
                    for line in lines:
                        if not line: continue
                        parts = line.split(',')
                        # THS format: 日期, 开盘, 最高, 最低, 收盘, 成交量, 成交额
                        df_data.append({
                            '日期': parts[0],
                            '开盘': float(parts[1]),
                            '最高': float(parts[2]),
                            '最低': float(parts[3]),
                            '收盘': float(parts[4]),
                            '成交量': float(parts[5]),
                            '成交额': float(parts[6])
                        })
                    df = pd.DataFrame(df_data)
                    # 转换日期格式 %Y%m%d -> %Y-%m-%d
                    df['日期'] = pd.to_datetime(df['日期']).dt.strftime('%Y-%m-%d')
                    # 过滤日期范围
                    start_date_fmt = f"{start_date[:4]}-{start_date[4:6]}-{start_date[6:]}"
                    df = df[df['日期'] >= start_date_fmt]
                    
                    # 补充东财需要的列名 (如果缺失)
                    if not df.empty:
                        if '涨跌幅' not in df.columns and len(df) > 1:
                            df['涨跌额'] = df['收盘'].diff()
                            df['涨跌幅'] = df['收盘'].pct_change() * 100
                            df['振幅'] = (df['最高'] - df['最低']) / df['收盘'].shift(1) * 100
                        return df
    except Exception as e:
        print(f"手动获取同花顺数据失败: {e}")
    return None


def get_stock_hist_data(symbol: str, days: int = 150):
    """获取股票历史日频行情数据，支持降级机制"""
    end_date = datetime.now().strftime("%Y%m%d")
    start_date = (datetime.now() - timedelta(days=days)).strftime("%Y%m%d")
    
    # --- Level 1: AKShare (East Money) ---
    res = safe_ak_call(ak.stock_zh_a_hist, symbol=symbol, period="daily", start_date=start_date, end_date=end_date, adjust="qfq")
    if res is not None and not res.empty:
        return res
        
    # --- Level 2: Sina Finance ---
    print(f"AKShare 历史数据获取失败，尝试从新浪财经获取 {symbol}...")
    try:
        prefix = get_market_prefix(symbol)
        sina_symbol = f"{prefix}{symbol}"
        df_sina = ak.stock_zh_a_daily(symbol=sina_symbol, adjust="qfq")
        
        if df_sina is not None and not df_sina.empty:
            # 转换新浪列名为东方财富格式
            df_sina = df_sina.rename(columns={
                'date': '日期', 'open': '开盘', 'close': '收盘', 'high': '最高', 'low': '最低',
                'volume': '成交量', 'amount': '成交额', 'turnover': '换手率'
            })
            df_sina['日期'] = pd.to_datetime(df_sina['日期']).dt.strftime('%Y-%m-%d')
            start_date_fmt = f"{start_date[:4]}-{start_date[4:6]}-{start_date[6:]}"
            df_sina = df_sina[df_sina['日期'] >= start_date_fmt]
            
            if '涨跌幅' not in df_sina.columns and len(df_sina) > 1:
                df_sina['涨跌额'] = df_sina['收盘'].diff()
                df_sina['涨跌幅'] = df_sina['收盘'].pct_change() * 100
                df_sina['振幅'] = (df_sina['最高'] - df_sina['最低']) / df_sina['收盘'].shift(1) * 100
            return df_sina
    except Exception as e:
        print(f"从新浪获取历史数据失败: {e}")

    # --- Level 3: THS (Manual) ---
    print(f"新浪财经数据获取失败，尝试手动从同花顺获取 {symbol}...")
    res = fetch_ths_hist_manual(symbol, start_date, end_date)
    if res is not None and not res.empty:
        return res
        
    return pd.DataFrame()

def get_realtime_quotes(symbol: str):
    """获取股票实时盘口数据 (五档买卖盘)"""
    res = safe_ak_call(ak.stock_bid_ask_em, symbol=symbol)
    return res if res is not None else pd.DataFrame()

def get_individual_info(symbol: str):
    """获取个股基本信息 (行业、总股本等)"""
    res = safe_ak_call(ak.stock_individual_info_em, symbol=symbol)
    return res if res is not None else pd.DataFrame()

def get_fund_flow(symbol: str):
    """获取个股主力资金流向"""
    market = get_market_prefix(symbol)
    res = safe_ak_call(ak.stock_individual_fund_flow, stock=symbol, market=market)
    return res if res is not None else pd.DataFrame()

def get_financial_deducted_profit(symbol: str):
    """获取个股扣除非经常性损益后的净利润"""
    try:
        df = safe_ak_call(ak.stock_financial_abstract_ths, symbol=symbol, indicator="主要指标")
        if df is None or df.empty: return "N/A"
        if '扣非净利润' in df.columns:
            df_sorted = df.sort_values('报告期', ascending=False)
            valid_rows = df_sorted[df_sorted['扣非净利润'] != 'False']
            if not valid_rows.empty:
                latest_row = valid_rows.iloc[0]
                return f"{latest_row['扣非净利润']} ({latest_row['报告期']})"
        return "N/A"
    except Exception as e:
        print(f"获取扣非净利润失败 ({symbol}): {e}")
        return "N/A"

def fetch_ths_spot_manual(symbol: str):
    """手动从同花顺获取单只股票实时行情 (Level 4 兜底)"""
    # 转换代码格式 000001 -> 000001
    url = f"http://d.10jqka.com.cn/v6/line/hs_{symbol}/01/last.js"
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        "Referer": "http://yuanchuang.10jqka.com.cn/",
        "Host": "d.10jqka.com.cn"
    }
    
    try:
        session = get_session()
        session.trust_env = False
        response = session.get(url, headers=headers, timeout=10)
        
        if response.status_code == 200:
            text = response.text
            match = re.search(r'\((.*)\)', text)
            if match:
                data_str = match.group(1)
                data_json = json.loads(data_str)
                if "data" in data_json:
                    # 获取最后一行数据作为实时数据
                    last_line = data_json["data"].split(';')[-1]
                    if last_line:
                        parts = last_line.split(',')
                        # parts: 日期, 开盘, 最高, 最低, 收盘, 成交量, 成交额
                        return {
                            '现价': float(parts[4]),
                            '最新价': float(parts[4]),
                            '今开': float(parts[1]),
                            '最高': float(parts[2]),
                            '最低': float(parts[3]),
                            '昨收': float(parts[4]), # 简单处理
                            '成交量': float(parts[5]),
                            '成交额': float(parts[6]),
                            '涨跌幅': 0.0, # 简单处理
                            '代码': symbol,
                            '名称': data_json.get('name', '')
                        }
    except Exception as e:
        print(f"手动获取同花顺实时数据失败: {e}")
    return None

def get_single_stock_spot(symbol: str):
    """获取单只股票的实时行情数据，支持降级机制"""
    
    # --- Level 1: Sina Finance (via AKShare) ---
    try:
        df_sina = ak.stock_zh_a_spot()
        if df_sina is not None and not df_sina.empty:
            match = df_sina[df_sina['代码'].str.contains(symbol)]
            if not match.empty:
                row = match.iloc[0]
                return {
                    "代码": symbol,
                    "名称": row.get('名称', 'N/A'),
                    "现价": row.get('最新价', 'N/A'),
                    "涨幅": f"{row.get('涨跌幅', 0):.2f}%",
                    "涨跌": row.get('涨跌额', 'N/A'),
                    "成交额": f"{row.get('成交额', 0) / 1e8:.2f}亿",
                    "换手率%": f"{row.get('换手率', 0):.2f}%",
                    "最高": row.get('最高', 'N/A'),
                    "最低": row.get('最低', 'N/A'),
                    "开盘": row.get('今开', 'N/A'),
                    "昨收": row.get('昨收', 'N/A'),
                    "振幅": "N/A", "量比": "N/A", "市盈率(TTM)": "N/A", "市盈(静)": "N/A", "市盈(动)": "N/A", "市净率(MRQ)": "N/A", "总市值": "N/A", "流通市值": "N/A", "股息率": "N/A", "涨速": "N/A"
                }
    except Exception as e:
        print(f"从新浪获取实时数据失败: {e}")

    # --- Level 2: THS (Manual) ---
    print(f"尝试手动从同花顺获取实时数据 {symbol}...")
    res = fetch_ths_spot_manual(symbol)
    if res:
        return {
            "代码": symbol,
            "名称": res.get('名称', 'N/A'),
            "现价": res.get('现价', 'N/A'),
            "涨幅": f"{res.get('涨跌幅', 0):.2f}%",
            "涨跌": "N/A",
            "成交额": f"{res.get('成交额', 0) / 1e8:.2f}亿",
            "换手率%": "N/A",
            "最高": res.get('最高', 'N/A'),
            "最低": res.get('最低', 'N/A'),
            "开盘": res.get('今开', 'N/A'),
            "昨收": res.get('昨收', 'N/A'),
            "振幅": "N/A", "量比": "N/A", "市盈率(TTM)": "N/A", "市盈(静)": "N/A", "市盈(动)": "N/A", "市净率(MRQ)": "N/A", "总市值": "N/A", "流通市值": "N/A", "股息率": "N/A", "涨速": "N/A"
        }
        
    return None

def get_comprehensive_financial_indicators(symbol: str):
    """获取全维度的财务指标 (市盈率、市净率、营收、利润、毛利、负债率等)"""
    indicators = {}
    abstract_df = pd.DataFrame()
    latest = {}
    
    try:
        # 1. 基础行情数据 (使用极速版接口替代 ak.stock_zh_a_spot_em)
        spot_data = get_single_stock_spot(symbol)
        if spot_data:
            indicators.update(spot_data)
            # 补充 60 日涨跌幅 (这个需要从历史数据算，或者通过其他接口)
            # 暂时设为 N/A，由 orchestrator 计算
            indicators["60日涨跌幅"] = "N/A"
            indicators["年初至今涨跌幅"] = "N/A"

        # 1.1 获取主力净额和净量 (资金流向)
        try:
            # 优化：单股资金流向接口通常很快
            # 注意：stock_individual_fund_flow_rank 不支持 symbol 参数，它是获取全市场排名的
            # 我们应该使用 stock_individual_fund_flow 来获取单只股票的资金流向
            fund_flow_df = safe_ak_call(ak.stock_individual_fund_flow, stock=symbol, market="sh" if symbol.startswith('6') else "sz")
            if fund_flow_df is not None and not fund_flow_df.empty:
                # 获取最新一天的
                f_row = fund_flow_df.iloc[0]
                indicators.update({
                    "主力净额": f"{f_row.get('主力净流入-净额', 0) / 1e4:.2f}万" if f_row.get('主力净流入-净额') is not None else 'N/A',
                    "主力净量": f"{f_row.get('主力净流入-净占比', 0):.2f}%" if f_row.get('主力净流入-净占比') is not None else 'N/A',
                })
        except Exception as e:
            print(f"获取主力资金数据失败 ({symbol}): {e}")

        # 2. 同花顺主要指标 (营收、利润及其同比、扣非、商誉)
        try:
            res = safe_ak_call(ak.stock_financial_abstract_ths, symbol=symbol, indicator="主要指标")
            if res is not None and not res.empty:
                # 按报告期排序，取最新
                abstract_df = res.sort_values('报告期', ascending=False)
                latest = abstract_df.iloc[0]
                indicators.update({
                    "营业总收入": latest.get('营业总收入', 'N/A'),
                    "营业利润": latest.get('营业利润', 'N/A'),
                    "归母净利润": latest.get('归母净利润', 'N/A'),
                    "扣非净利润": latest.get('扣非净利润', 'N/A'),
                    "商誉": latest.get('商誉', 'N/A'),
                    "基本每股收益": latest.get('基本每股收益', 'N/A'),
                    "每股净资产": latest.get('每股净资产', 'N/A'),
                    "每股经营现金流": latest.get('每股经营现金流', 'N/A'),
                })
        except Exception as e:
            print(f"获取主要财务指标失败: {e}")

        # 3. 同花顺财务指标 (ROE, 毛利, 净利, 负债率)
        try:
            analysis_df = safe_ak_call(ak.stock_financial_analysis_indicator_ths, symbol=symbol)
            if analysis_df is not None and not analysis_df.empty:
                analysis_df = analysis_df.sort_values('报告期', ascending=False)
                latest_analysis = analysis_df.iloc[0]
                indicators.update({
                    "净资产收益率(ROE)": f"{latest_analysis.get('净资产收益率', 'N/A')}%",
                    "销售毛利率": f"{latest_analysis.get('销售毛利率', 'N/A')}%",
                    "销售净利率": f"{latest_analysis.get('销售净利率', 'N/A')}%",
                    "资产负债率": f"{latest_analysis.get('资产负债率', 'N/A')}%",
                    "每股未分配利润": latest_analysis.get('每股未分配利润', 'N/A'),
                    "每股公积金": latest_analysis.get('每股资本公积金', 'N/A'),
                })
        except Exception as e:
            print(f"获取财务分析指标失败: {e}")

        # 4. 获取同比数据 (从 abstract_df 中计算或直接取)
        # 注意：akshare 的 abstract_df 有时直接包含同比，有时需要计算
        # 这里尝试从 abstract_df 的历史数据中寻找上一年同期数据计算同比
        if not abstract_df.empty and latest and len(abstract_df) >= 5:
            latest_period = latest['报告期']
            try:
                # 寻找去年同期 (例如 2024-09-30 对应 2023-09-30)
                year = int(latest_period[:4])
                last_year_period = f"{year-1}{latest_period[4:]}"
                prev_match = abstract_df[abstract_df['报告期'] == last_year_period]
                
                if not prev_match.empty:
                    prev = prev_match.iloc[0]
                    def calc_yoy(curr_val, prev_val):
                        try:
                            # 清理字符串中的“亿”等单位
                            def clean_val(v):
                                if isinstance(v, str):
                                    v = v.replace('亿', '').replace('万', '')
                                    return float(v)
                                return float(v)
                            c = clean_val(curr_val)
                            p = clean_val(prev_val)
                            if p == 0: return "N/A"
                            return f"{(c - p) / abs(p) * 100:.2f}%"
                        except: return "N/A"

                    indicators.update({
                        "营业总收入同比": calc_yoy(latest.get('营业总收入'), prev.get('营业总收入')),
                        "营业利润同比": calc_yoy(latest.get('营业利润'), prev.get('营业利润')),
                        "归母净利润同比": calc_yoy(latest.get('归母净利润'), prev.get('归母净利润')),
                        "扣非净利润同比": calc_yoy(latest.get('扣非净利润'), prev.get('扣非净利润')),
                    })
            except: pass

        # 5. 其他信息 (股息率、商誉等)
        info_df = safe_ak_call(ak.stock_individual_info_em, symbol=symbol)
        if info_df is not None and not info_df.empty:
            total_shares = info_df[info_df['item'] == '总股本']['value'].values
            flow_shares = info_df[info_df['item'] == '流通股']['value'].values
            indicators.update({
                "总股本": f"{float(total_shares[0])/1e8:.2f}亿股" if len(total_shares) > 0 else 'N/A',
                "流通股本": f"{float(flow_shares[0])/1e8:.2f}亿股" if len(flow_shares) > 0 else 'N/A',
            })

    except Exception as e:
        print(f"获取综合财务指标失败 ({symbol}): {e}")
        
    return indicators

def get_latest_financial_report(symbol: str, preferred_year: str = None):
    """获取最新的一份财报公告信息"""
    reports = get_all_financial_reports(symbol, preferred_year if preferred_year else datetime.now().strftime("%Y"))
    if not reports and not preferred_year:
        # 如果当前年份没搜到且没指定年份，搜上一年
        last_year = str(int(datetime.now().strftime("%Y")) - 1)
        reports = get_all_financial_reports(symbol, last_year)
    
    if reports:
        # 返回日期最近的一份
        return sorted(reports, key=lambda x: x['date'], reverse=True)[0]
    return None

def get_all_financial_reports(symbol: str, year: str):
    """获取指定年份内发布的所有财报公告信息 (极速版)"""
    try:
        start_date = f"{year}0101"
        end_date = f"{year}1231"
        
        all_reports_dict = {} # 使用字典去重，key 为公告 ID
        
        # 优化：不再使用 10 个关键词分别搜索，而是使用一个通用关键词
        # 大多数财报标题都包含“报告”二字
        keywords_to_try = ["报告", "摘要"]
        
        # 排除包含这些词的非核心公告
        exclude_kws = ["提示性", "业绩说明会", "说明会", "记录表", "英文版", "决议公告", "财务报表", "审计报告", "受托管理事务报告"]
        # 必须包含这些词之一才认为是财报
        must_include_kws = ["年度报告", "半年度报告", "季度报告", "年报", "半年报", "季报"]
        
        for kw in keywords_to_try:
            try:
                # 每次搜索尝试增加延时，防止触发反爬
                df = safe_ak_call(ak.stock_zh_a_disclosure_report_cninfo, symbol=symbol, market="沪深京", keyword=kw, start_date=start_date, end_date=end_date)
                if df is not None and not df.empty and '公告标题' in df.columns:
                    for _, row in df.iterrows():
                        title = row['公告标题'].replace('<em>', '').replace('</em>', '')
                        
                        # 过滤非核心公告
                        if any(ex in title for ex in exclude_kws):
                            continue
                        # 必须是真正的财报
                        if not any(mi in title for mi in must_include_kws):
                            continue
                            
                        date = str(row['公告时间'])
                        # 核心修复：确保日期格式为 YYYY-MM-DD，去掉可能存在的 00:00:00
                        if ' ' in date:
                            date = date.split(' ')[0]
                        
                        url = row['公告链接']
                        
                        # 提取公告 ID 用于去重
                        announcement_id = ""
                        if 'announcementId=' in url:
                            match = re.search(r'announcementId=([^&]+)', url)
                            if match: announcement_id = match.group(1)
                        elif 'detail/' in url:
                            match = re.search(r'detail/([^/?]+)', url)
                            if match: announcement_id = match.group(1)
                        
                        if not announcement_id:
                            continue
                            
                        if announcement_id not in all_reports_dict:
                            # 巨潮资讯 PDF 下载链接格式通常为: https://static.cninfo.com.cn/finalpage/YYYY-MM-DD/ID.PDF
                            download_url = f"https://static.cninfo.com.cn/finalpage/{date}/{announcement_id}.PDF"
                            all_reports_dict[announcement_id] = {"title": title, "date": date, "url": download_url}
                            print(f"找到财报: {title} ({date})")
                    
                    # 如果已经找到了关键报告，就不再尝试其他关键词
                    if len(all_reports_dict) > 0:
                        break
            except Exception:
                continue
        
        all_reports = list(all_reports_dict.values())
        # 按时间排序
        all_reports.sort(key=lambda x: x['date'])
        return all_reports
    except Exception as e:
        print(f"获取财报列表失败 ({symbol}): {e}")
        return []

def download_report_pdf(url: str, save_path: str):
    """下载财报 PDF 文件"""
    try:
        session = get_session(retries=5, backoff_factor=1) # 下载 PDF 时增加重试次数
        response = session.get(url, stream=True, timeout=60, headers=DEFAULT_HEADERS)
        if response.status_code == 200:
            with open(save_path, 'wb') as f:
                for chunk in response.iter_content(chunk_size=8192):
                    f.write(chunk)
            return True
        return False
    except Exception as e:
        print(f"下载过程中发生错误: {e}")
        return False

def get_industry_hist(industry: str, days: int = 150):
    """获取行业板块历史行情数据"""
    end_date = datetime.now().strftime("%Y%m%d")
    start_date = (datetime.now() - timedelta(days=days)).strftime("%Y%m%d")
    res = safe_ak_call(ak.stock_board_industry_hist_em, symbol=industry, start_date=start_date, end_date=end_date, period="日k")
    return res if res is not None else pd.DataFrame()
