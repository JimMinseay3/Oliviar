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

def get_single_stock_spot(symbol: str):
    """获取单只股票的实时行情数据 (极速版)"""
    try:
        # 确定市场前缀
        if symbol.startswith('6') or symbol.startswith('9'):
            secid = f"1.{symbol}"
        else:
            secid = f"0.{symbol}"
            
        url = "http://push2.eastmoney.com/api/qt/stock/get"
        params = {
            "secid": secid,
            "fields": "f43,f44,f45,f46,f60,f47,f48,f49,f50,f51,f52,f57,f58,f107,f108,f162,f163,f164,f167,f116,f117,f3,f4,f5,f6,f7,f8,f9,f10,f12,f13,f14,f15,f16,f17,f18,f19,f20,f31,f32,f33,f34,f35,f36,f37,f38,f39,f40,f127,f128"
        }
        
        resp = requests.get(url, params=params, timeout=5)
        data = resp.json()
        
        if data and data.get("data"):
            d = data["data"]
            # 这里的字段对应关系与 Rust fetcher.rs 中一致
            # f43: 现价, f3: 涨幅, f4: 涨跌, f6: 成交额, f8: 换手率, f7: 振幅, f44: 最高, f45: 最低, f46: 开盘, f60: 昨收
            # f162: PE(TTM), f163: PE(静), f164: PE(动), f167: PB(MRQ)
            # f116: 总市值, f117: 流通市值, f108: 股息率
            
            res = {
                "代码": symbol,
                "名称": d.get("f58", "N/A"),
                "现价": d.get("f43", 0) / 100.0 if d.get("f43") != "-" else "N/A",
                "涨幅": f"{d.get('f3', 0) / 100.0:.2f}%" if d.get("f3") != "-" else "N/A",
                "涨跌": d.get("f4", 0) / 100.0 if d.get("f4") != "-" else "N/A",
                "成交额": f"{d.get('f6', 0) / 1e8:.2f}亿" if d.get("f6") != "-" else "N/A",
                "换手率%": f"{d.get('f8', 0) / 100.0:.2f}%" if d.get("f8") != "-" else "N/A",
                "振幅": f"{d.get('f7', 0) / 100.0:.2f}%" if d.get("f7") != "-" else "N/A",
                "最高": d.get("f44", 0) / 100.0 if d.get("f44") != "-" else "N/A",
                "最低": d.get("f45", 0) / 100.0 if d.get("f45") != "-" else "N/A",
                "开盘": d.get("f46", 0) / 100.0 if d.get("f46") != "-" else "N/A",
                "昨收": d.get("f60", 0) / 100.0 if d.get("f60") != "-" else "N/A",
                "量比": d.get("f10", 0) / 100.0 if d.get("f10") != "-" else "N/A",
                "市盈率(TTM)": d.get("f162", 0) / 100.0 if d.get("f162") != "-" else "N/A",
                "市盈(静)": d.get("f163", 0) / 100.0 if d.get("f163") != "-" else "N/A",
                "市盈(动)": d.get("f164", 0) / 100.0 if d.get("f164") != "-" else "N/A",
                "市净率(MRQ)": d.get("f167", 0) / 100.0 if d.get("f167") != "-" else "N/A",
                "总市值": f"{d.get('f116', 0) / 1e8:.2f}亿" if d.get("f116") != "-" else "N/A",
                "流通市值": f"{d.get('f117', 0) / 1e8:.2f}亿" if d.get("f117") != "-" else "N/A",
                "股息率": f"{d.get('f108', 0) / 100.0:.2f}%" if d.get("f108") != "-" else "N/A",
                "涨速": f"{d.get('f9', 0) / 100.0:.2f}%" if d.get("f9") != "-" else "N/A",
            }
            return res
    except Exception as e:
        print(f"获取单股行情失败: {e}")
    return None

def get_comprehensive_financial_indicators(symbol: str):
    """获取全维度的财务指标 (市盈率、市净率、营收、利润、毛利、负债率等)"""
    indicators = {}
    
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
            fund_flow_df = ak.stock_individual_fund_flow(stock=symbol, market="sh" if symbol.startswith('6') else "sz")
            if not fund_flow_df.empty:
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
            abstract_df = ak.stock_financial_abstract_ths(symbol=symbol, indicator="主要指标")
            if not abstract_df.empty:
                # 按报告期排序，取最新
                abstract_df = abstract_df.sort_values('报告期', ascending=False)
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
            analysis_df = ak.stock_financial_analysis_indicator_ths(symbol=symbol)
            if not analysis_df.empty:
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
        if not abstract_df.empty and len(abstract_df) >= 5:
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
        info_df = ak.stock_individual_info_em(symbol=symbol)
        if not info_df.empty:
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
                df = ak.stock_zh_a_disclosure_report_cninfo(symbol=symbol, market="沪深京", keyword=kw, start_date=start_date, end_date=end_date)
                if df is not None and not df.empty and '公告标题' in df.columns:
                    for _, row in df.iterrows():
                        title = row['公告标题'].replace('<em>', '').replace('</em>', '')
                        
                        # 过滤非核心公告
                        if any(ex in title for ex in exclude_kws):
                            continue
                        # 必须是真正的财报
                        if not any(mi in title for mi in must_include_kws):
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
                            continue
                            
                        if announcement_id not in all_reports_dict:
                            download_url = f"https://static.cninfo.com.cn/finalpage/{date}/{announcement_id}.PDF"
                            all_reports_dict[announcement_id] = {"title": title, "date": date, "url": download_url}
                    
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
