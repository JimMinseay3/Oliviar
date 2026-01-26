import os
import pandas as pd
import numpy as np
from datetime import datetime
from . import data_fetcher as df
from . import risk_analyzer as ra

def perform_comprehensive_risk_analysis(symbol: str, output_dir: str = "data", preferred_year: str = None, download_reports: bool = False):
    """对指定股票执行全维度的风险风控分析并生成报告"""
    if not os.path.exists(output_dir):
        os.makedirs(output_dir)
    
    report_data = {
        "分析标的": "",
        "证券代码": symbol,
        "分析时间": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    }

    # 1. 数据采集
    print(f"正在采集 {symbol} 的数据...")
    df_hist = df.get_stock_hist_data(symbol)
    if df_hist.empty:
        print(f"错误: 未能获取到股票 {symbol} 的历史数据，请检查代码是否正确。")
        return {"error": f"未能获取到股票 {symbol} 的历史数据"}
    
    # 确保按日期升序并重置索引，以便后续通过索引获取前一天数据
    df_hist = df_hist.sort_values('日期').reset_index(drop=True)
    
    # 计算多周期涨幅
    if len(df_hist) >= 20:
        latest_close = float(df_hist.iloc[-1]['收盘'])
        
        def calc_ret(days):
            if len(df_hist) > days:
                prev_close = float(df_hist.iloc[-(days+1)]['收盘'])
                return f"{(latest_close - prev_close) / prev_close * 100:.2f}%"
            return "N/A"
            
        report_data["5日涨幅"] = calc_ret(5)
        report_data["10日涨幅"] = calc_ret(10)
        report_data["20日涨幅"] = calc_ret(20)
        report_data["60日涨跌幅"] = calc_ret(60)
    else:
        report_data["5日涨幅"] = "N/A"
        report_data["10日涨幅"] = "N/A"
        report_data["20日涨幅"] = "N/A"
        report_data["60日涨跌幅"] = "N/A"

    tick_data = df.get_realtime_quotes(symbol)
    stock_info = df.get_individual_info(symbol)
    fund_flow = df.get_fund_flow(symbol)
    
    # 获取名称
    symbol_name = symbol
    if not stock_info.empty and 'item' in stock_info.columns:
        name_res = stock_info[stock_info['item'] == '股票简称']['value'].values
        if len(name_res) > 0:
            symbol_name = name_res[0]
    report_data["分析标的"] = symbol_name

    # 确定文件夹 (标的代码_标的简称)
    target_folder = f"{symbol}_{symbol_name}"
    final_dir = os.path.join(output_dir, target_folder)
    if not os.path.exists(final_dir):
        os.makedirs(final_dir)

    # 2. 波动率计算
    try:
        hv20 = ra.calculate_historical_volatility(df_hist, 20)
        hv60 = ra.calculate_historical_volatility(df_hist, 60)
        report_data["HV20"] = f"{hv20:.2%}" if hv20 else "N/A"
        report_data["HV60"] = f"{hv60:.2%}" if hv60 else "N/A"
    except Exception as e:
        print(f"波动率计算失败: {e}")
        report_data["HV20"] = "N/A"
        report_data["HV60"] = "N/A"

    # 3. 流动性评估
    try:
        liquidity = ra.analyze_liquidity_depth(tick_data)
        if liquidity:
            report_data["卖五深度(手)"] = liquidity["total_ask_depth"]
            report_data["买五深度(手)"] = liquidity["total_bid_depth"]
            report_data["买卖盘深度"] = f"买五:{liquidity['total_bid_depth']}, 卖五:{liquidity['total_ask_depth']}"
            report_data["流动性评估"] = liquidity["assessment"]
    except Exception as e:
        print(f"流动性评估失败: {e}")
        report_data["买卖盘深度"] = "N/A"
        report_data["流动性评估"] = "N/A"
    
    # 4. 板块共振分析
    industry_name = "N/A"
    if not stock_info.empty and 'item' in stock_info.columns:
        industry_res = stock_info[stock_info['item'] == '行业']['value'].values
        if len(industry_res) > 0:
            industry_name = industry_res[0]
    
    report_data["所属行业"] = industry_name
    df_industry = None
    if industry_name != "N/A":
        try:
            df_industry = df.get_industry_hist(industry_name)
            if df_industry is not None and not df_industry.empty:
                corr = ra.calculate_sector_correlation(df_hist, df_industry)
                report_data["行业相关性"] = f"{corr:.2f}" if (corr is not None and not np.isnan(corr)) else "N/A"
            else:
                report_data["行业相关性"] = "N/A"
        except Exception as e:
            print(f"板块共振分析失败: {e}")
            report_data["行业相关性"] = "N/A"

    # 5. 资金流向分析
    if not fund_flow.empty:
        col_main = [c for c in fund_flow.columns if '主力净流入' in c and '净额' in c]
        if col_main:
            # 今日主力
            flow_today = fund_flow.iloc[0][col_main[0]]
            report_data["今日主力净流入(万元)"] = f"{flow_today / 10000:.2f}"
            # 一周汇总
            flow_week = fund_flow.head(5)[col_main[0]].sum()
            report_data["近一周主力净流入(万元)"] = f"{flow_week / 10000:.2f}"

    # 6. 财务指标
    try:
        print(f"正在获取 {symbol} 的综合财务指标...")
        comprehensive_indicators = df.get_comprehensive_financial_indicators(symbol)
        if comprehensive_indicators:
            report_data.update(comprehensive_indicators)
        else:
            # 回退到旧的简单扣非净利润获取
            deducted_profit = df.get_financial_deducted_profit(symbol)
            report_data["扣非净利润"] = deducted_profit
    except Exception as e:
        print(f"获取财务指标失败: {e}")

    # 7. 财报公告处理
    try:
        target_year = preferred_year if preferred_year else datetime.now().strftime("%Y")
        if download_reports:
            print(f"正在下载 {symbol} 在 {target_year} 年的所有财报...")
            all_reports = df.get_all_financial_reports(symbol, target_year)
            
            # 增加回退机制：如果当前年份没有搜到，自动搜上一年
            if not all_reports and not preferred_year:
                last_year = str(int(target_year) - 1)
                print(f"未找到 {target_year} 年财报，尝试搜索 {last_year} 年...")
                all_reports = df.get_all_financial_reports(symbol, last_year)
                
            for r in all_reports:
                # 过滤掉文件名中的非法字符
                clean_title = r['title'].replace('/', '_').replace('\\', '_').replace(':', '_').replace('*', '_').replace('?', '_').replace('"', '_').replace('<', '_').replace('>', '_').replace('|', '_')
                file_name = f"{r['date']}_{clean_title}.pdf"
                save_path = os.path.join(final_dir, file_name)
                if not os.path.exists(save_path):
                    success = df.download_report_pdf(r['url'], save_path)
                    if success:
                        print(f"成功下载: {file_name}")
                    else:
                        print(f"下载失败: {file_name}, URL: {r['url']}")
                else:
                    print(f"文件已存在，跳过下载: {file_name}")
        else:
            print(f"正在获取 {symbol} 的最新财报公告信息...")
            report_info = df.get_latest_financial_report(symbol, preferred_year=target_year)
            if report_info:
                report_data["最新财报标题"] = report_info['title']
                report_data["最新财报发布日期"] = report_info['date']
            else:
                report_data["最新财报标题"] = "N/A"
                report_data["最新财报发布日期"] = "N/A"
    except Exception as e:
        print(f"财报公告处理失败: {e}")
        report_data["最新财报标题"] = "N/A"
        report_data["最新财报发布日期"] = "N/A"

    # 8. 收集最近一个月的历史数据 (用于 Excel 表格展示)
    print(f"正在收集 {symbol} 最近一个月的历史数据...")
    historical_records = []
    # 取最近 30 个交易日，按日期降序排列展示
    hist_month = df_hist.tail(30).sort_values('日期', ascending=False)
    
    # 获取历史资金流向 (用于对齐日期)
    fund_flow_hist = fund_flow.copy() if not fund_flow.empty else pd.DataFrame()
    if not fund_flow_hist.empty:
        # 确保日期列为字符串格式，方便后续匹配
        fund_flow_hist['日期'] = fund_flow_hist['日期'].apply(lambda x: str(x))
    
    # 获取当前最新的行业相关性等信息，作为历史记录的默认填充
    latest_corr = report_data.get("行业相关性", "N/A")
    latest_liquidity = report_data.get("流动性评估", "N/A")
    latest_depth = report_data.get("买卖盘深度", "N/A")

    for i, row in hist_month.iterrows():
        date_str = str(row['日期'])
        
        # 计算昨收 (通过收盘价和涨跌额反推，或者取前一行)
        # 如果 hist_month 是按日期降序，我们需要在 df_hist 中找前一天的收盘价
        try:
            current_idx = df_hist[df_hist['日期'] == row['日期']].index[0]
            if current_idx > 0:
                prev_close = df_hist.iloc[current_idx - 1]['收盘']
                prev_close_str = f"{prev_close:.2f}"
            else:
                prev_close_str = "N/A"
        except:
            prev_close_str = "N/A"

        record = {
            "日期": date_str,
            "现价": f"{row['收盘']:.2f}",
            "涨跌": f"{row['涨跌额']:.2f}" if '涨跌额' in row else "N/A",
            "涨幅": f"{row['涨跌幅']:.2f}%",
            "涨速": "N/A", # 历史数据无法获取实时涨速
            "成交额": f"{row['成交额']/1e8:.2f}亿" if '成交额' in row else "N/A",
            "换手率%": f"{row['换手率']:.2f}%" if '换手率' in row else "N/A",
            "振幅": f"{row['振幅']:.2f}%" if '振幅' in row else "N/A",
            "最高": f"{row['最高']:.2f}",
            "最低": f"{row['最低']:.2f}",
            "开盘": f"{row['开盘']:.2f}",
            "昨收": prev_close_str,
        }
        
        # 流动性评估和买卖盘深度仅对最新日期有效
        is_latest = (i == hist_month.index[0])
        record["流动性评估"] = latest_liquidity if is_latest else "N/A"
        record["买卖盘深度"] = latest_depth if is_latest else "N/A"
        
        # 匹配当天的资金流向 (4个级别：流入/流出)
        fund_map = {
            "特大单": "超大单净流入-净额",
            "大单": "大单净流入-净额",
            "中单": "中单净流入-净额",
            "小单": "小单净流入-净额"
        }
        
        for level in fund_map:
            record[f"流入{level}"] = "0.00"
            record[f"流出{level}"] = "0.00"

        if not fund_flow_hist.empty:
            # 这里的 date_str 已经是字符串，fund_flow_hist['日期'] 也转换成了字符串
            day_flow = fund_flow_hist[fund_flow_hist['日期'] == date_str]
            if not day_flow.empty:
                for level, source_col in fund_map.items():
                    if source_col in day_flow.columns:
                        try:
                            flow_val = day_flow.iloc[0][source_col]
                            flow_val_wan = float(flow_val) / 10000
                            if flow_val_wan > 0:
                                record[f"流入{level}"] = f"{flow_val_wan:.2f}"
                                record[f"流出{level}"] = "0.00"
                            else:
                                record[f"流入{level}"] = "0.00"
                                record[f"流出{level}"] = f"{abs(flow_val_wan):.2f}"
                        except:
                            pass
        
        # 财务指标处理
        if comprehensive_indicators:
            # 排除实时行情相关的字段，只保留基础财务和股本指标
            realtime_fields = {"现价", "涨幅", "涨跌", "成交额", "换手率%", "振幅", "最高", "最低", "开盘", "昨收", "涨速", "量比", "总市值", "流通市值", "市盈率(TTM)", "市盈(静)", "市盈(动)", "市净率(MRQ)"}
            for k, v in comprehensive_indicators.items():
                if k not in realtime_fields:
                    record[k] = v
            
            # 动态计算历史估值指标 (基于当日收盘价)
            try:
                close_price = float(row['收盘'])
                
                # 1. 市值计算
                total_shares_str = comprehensive_indicators.get("总股本", "N/A")
                circ_shares_str = comprehensive_indicators.get("流通股本", "N/A")
                
                def parse_shares(s):
                    try:
                        return float(s.replace('亿股', '')) * 1e8
                    except: return None
                    
                total_shares = parse_shares(total_shares_str)
                circ_shares = parse_shares(circ_shares_str)
                
                if total_shares:
                    record["总市值"] = f"{close_price * total_shares / 1e8:.2f}亿"
                if circ_shares:
                    record["流通市值"] = f"{close_price * circ_shares / 1e8:.2f}亿"
                    
                # 2. 估值计算 (PE, PB)
                eps = comprehensive_indicators.get("基本每股收益")
                bps = comprehensive_indicators.get("每股净资产")
                
                try:
                    eps_val = float(eps)
                    if eps_val > 0:
                        record["市盈率(TTM)"] = f"{close_price / eps_val:.2f}"
                    else:
                        record["市盈率(TTM)"] = "N/A"
                except: 
                    record["市盈率(TTM)"] = "N/A"
                
                try:
                    bps_val = float(bps)
                    if bps_val > 0:
                        record["市净率(MRQ)"] = f"{close_price / bps_val:.2f}"
                    else:
                        record["市净率(MRQ)"] = "N/A"
                except:
                    record["市净率(MRQ)"] = "N/A"
                
                # 静态指标 (PE静/动在历史中较难精确还原，保持 N/A 或使用当前值作为参考)
                record["市盈(静)"] = comprehensive_indicators.get("市盈(静)", "N/A")
                record["市盈(动)"] = comprehensive_indicators.get("市盈(动)", "N/A")
                
            except Exception as e:
                print(f"计算历史估值失败: {e}")

        # 确保财务同比指标存在，防止前端显示空白
        yoy_fields = ["营业总收入同比", "营业利润同比", "归母净利润同比", "扣非净利润同比"]
        for field in yoy_fields:
            if field not in record or not record[field]:
                record[field] = "N/A"
        
        # 量化指标计算
        try:
            current_idx = df_hist[df_hist['日期'] == row['日期']].index[0]
            sub_df = df_hist.loc[:current_idx]
            
            # 1. 历史波动率
            h20 = ra.calculate_historical_volatility(sub_df, 20)
            h60 = ra.calculate_historical_volatility(sub_df, 60)
            record["HV20"] = f"{h20:.2%}" if h20 else "N/A"
            record["HV60"] = f"{h60:.2%}" if h60 else "N/A"
            
            # 2. 多周期涨幅
            def calc_sub_ret(days):
                if len(sub_df) > days:
                    curr_c = float(sub_df.iloc[-1]['收盘'])
                    prev_c = float(sub_df.iloc[-(days+1)]['收盘'])
                    return f"{(curr_c - prev_c) / prev_c * 100:.2f}%"
                return "N/A"
            
            record["5日涨幅"] = calc_sub_ret(5)
            record["10日涨幅"] = calc_sub_ret(10)
            record["20日涨幅"] = calc_sub_ret(20)
            record["60日涨跌幅"] = calc_sub_ret(60)
            
            # 3. 行业相关性 (动态计算)
            if df_industry is not None and not df_industry.empty:
                # 筛选行业数据到当前日期
                sub_industry = df_industry[df_industry['日期'] <= row['日期']]
                corr = ra.calculate_sector_correlation(sub_df, sub_industry)
                record["行业相关性"] = f"{corr:.2f}" if (corr is not None and not np.isnan(corr)) else "N/A"
            else:
                record["行业相关性"] = "N/A"
                
        except Exception as e:
            print(f"计算历史量化指标失败 ({date_str}): {e}")
            record["HV20"] = "N/A"
            record["HV60"] = "N/A"
            record["5日涨幅"] = "N/A"
            record["10日涨幅"] = "N/A"
            record["20日涨幅"] = "N/A"
            record["60日涨跌幅"] = "N/A"
            record["行业相关性"] = "N/A"
            
        historical_records.append(record)
    
    report_data["historical_data"] = historical_records

    # 9. 移除资金流向饼图 (用户要求)
    report_data["资金流向饼图"] = ""

    # 10. 保存报告 CSV
    report_df = pd.DataFrame([report_data])
    output_path = os.path.join(final_dir, f"risk_report_{symbol}_{datetime.now().strftime('%Y%m%d')}.csv")
    report_df.to_csv(output_path, index=False, encoding="utf-8-sig")
    
    print(f"分析完成，报告保存至: {output_path}")
    return report_data
