import akshare as ak
import pandas as pd
from datetime import datetime, timedelta
import requests
import re

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
        
        all_reports = []
        keywords = ["第一季度报告", "半年度报告", "第三季度报告", "年度报告"]
        
        for kw in keywords:
            try:
                df = ak.stock_zh_a_disclosure_report_cninfo(symbol=symbol, market="沪深京", keyword=kw, start_date=start_date, end_date=end_date)
                if df is not None and not df.empty and '公告标题' in df.columns:
                    # 过滤摘要
                    reports = df[~df['公告标题'].str.contains('摘要', na=False)]
                    for _, row in reports.iterrows():
                        title = row['公告标题'].replace('<em>', '').replace('</em>', '')
                        date = row['公告时间']
                        url = row['公告链接']
                        
                        # 尝试从链接提取 ID，支持多种格式
                        announcement_id = ""
                        if 'announcementId=' in url:
                            match = re.search(r'announcementId=([^&]+)', url)
                            if match: announcement_id = match.group(1)
                        elif 'detail/' in url:
                            match = re.search(r'detail/([^/?]+)', url)
                            if match: announcement_id = match.group(1)
                            
                        download_url = f"https://static.cninfo.com.cn/finalpage/{date}/{announcement_id}.PDF" if announcement_id else url
                        all_reports.append({"title": title, "date": date, "url": download_url})
            except Exception as e_kw:
                print(f"获取关键字 {kw} 失败: {e_kw}")
                continue
        
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
