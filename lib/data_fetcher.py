import akshare as ak
import pandas as pd
from datetime import datetime, timedelta
import requests
import re

import os

def get_stock_list(cache_file: str = "data/stock_list_cache.csv"):
    """获取所有 A 股列表，支持本地缓存"""
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
    
    # 如果没有缓存或已过期，重新拉取
    try:
        print("正在从 API 更新 A 股列表缓存...")
        df = ak.stock_zh_a_spot_em()
        df.to_csv(cache_file, index=False, encoding="utf-8-sig")
        return df
    except Exception as e:
        print(f"更新 A 股列表失败: {e}")
        if os.path.exists(cache_file):
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

def get_stock_hist_data(symbol: str, days: int = 150):
    """获取股票历史日频行情数据"""
    end_date = datetime.now().strftime("%Y%m%d")
    start_date = (datetime.now() - timedelta(days=days)).strftime("%Y%m%d")
    return ak.stock_zh_a_hist(symbol=symbol, period="daily", start_date=start_date, end_date=end_date, adjust="qfq")

def get_realtime_quotes(symbol: str):
    """获取股票实时盘口数据 (五档买卖盘)"""
    return ak.stock_bid_ask_em(symbol=symbol)

def get_individual_info(symbol: str):
    """获取个股基本信息 (行业、总股本等)"""
    return ak.stock_individual_info_em(symbol=symbol)

def get_fund_flow(symbol: str):
    """获取个股主力资金流向"""
    if symbol.startswith('6'):
        market = "sh"
    elif symbol.startswith('0') or symbol.startswith('3'):
        market = "sz"
    elif symbol.startswith('8') or symbol.startswith('4'):
        market = "bj"
    else:
        market = "sh"
    return ak.stock_individual_fund_flow(stock=symbol, market=market)

def get_financial_deducted_profit(symbol: str):
    """获取个股扣除非经常性损益后的净利润"""
    try:
        df = ak.stock_financial_abstract_ths(symbol=symbol, indicator="主要指标")
        if df.empty: return "N/A"
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
    """获取指定年份内发布的所有财报公告信息 (一季报、半年报、三季报、年报)"""
    try:
        start_date = f"{year}0101"
        end_date = f"{year}1231"
        
        all_reports_dict = {} # 使用字典去重，key 为公告 ID
        # 扩展关键词，涵盖不同公司的命名习惯
        keywords = [
            "第一季度报告", "一季度报告", "一季报",
            "第三季度报告", "三季度报告", "三季报",
            "半年度报告", "半年报",
            "年度报告", "年报"
        ]
        
        # 排除包含这些词的非核心公告
        exclude_kws = ["摘要", "提示性", "业绩说明会", "说明会", "记录表", "英文版", "决议公告", "财务报表", "审计报告", "受托管理事务报告"]
        
        for kw in keywords:
            try:
                df = ak.stock_zh_a_disclosure_report_cninfo(symbol=symbol, market="沪深京", keyword=kw, start_date=start_date, end_date=end_date)
                if df is not None and not df.empty and '公告标题' in df.columns:
                    for _, row in df.iterrows():
                        title = row['公告标题'].replace('<em>', '').replace('</em>', '')
                        
                        # 过滤非核心公告
                        if any(ex in title for ex in exclude_kws):
                            continue
                            
                        date = row['公告时间']
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
                            continue # 无法获取 ID 则跳过，确保下载链接有效
                            
                        if announcement_id not in all_reports_dict:
                            download_url = f"https://static.cninfo.com.cn/finalpage/{date}/{announcement_id}.PDF"
                            all_reports_dict[announcement_id] = {"title": title, "date": date, "url": download_url}
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
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36",
            "Referer": "http://www.cninfo.com.cn/new/commonUrl/pageOfSearch?url=disclosure/list/search"
        }
        response = requests.get(url, stream=True, timeout=30, headers=headers)
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
    return ak.stock_board_industry_hist_em(symbol=industry, start_date=start_date, end_date=end_date, period="日k")
