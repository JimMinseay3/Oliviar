import os
import pandas as pd
from datetime import datetime
from . import data_fetcher as df
from . import risk_analyzer as ra
from . import visualizer as vs

def perform_comprehensive_risk_analysis(symbol: str, output_dir: str = "data", preferred_year: str = None):
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
    tick_data = df.get_realtime_quotes(symbol)
    stock_info = df.get_individual_info(symbol)
    fund_flow = df.get_fund_flow(symbol)
    
    # 获取名称
    name_res = stock_info[stock_info['item'] == '股票简称']['value'].values
    symbol_name = name_res[0] if len(name_res) > 0 else symbol
    report_data["分析标的"] = symbol_name

    # 确定文件夹
    target_folder = f"{symbol}_{symbol_name}"
    final_dir = os.path.join(output_dir, target_folder)
    if not os.path.exists(final_dir):
        os.makedirs(final_dir)

    # 2. 波动率计算
    hv20 = ra.calculate_historical_volatility(df_hist, 20)
    hv60 = ra.calculate_historical_volatility(df_hist, 60)
    report_data["HV20"] = f"{hv20:.2%}" if hv20 else "N/A"
    report_data["HV60"] = f"{hv60:.2%}" if hv60 else "N/A"

    # 3. 流动性评估
    liquidity = ra.analyze_liquidity_depth(tick_data)
    if liquidity:
        report_data["卖五深度(手)"] = liquidity["total_ask_depth"]
        report_data["买五深度(手)"] = liquidity["total_bid_depth"]
        report_data["流动性评估"] = liquidity["assessment"]
    
    # 4. 板块共振分析
    industry_res = stock_info[stock_info['item'] == '行业']['value'].values
    if len(industry_res) > 0:
        industry_name = industry_res[0]
        report_data["所属行业"] = industry_name
        df_industry = df.get_industry_hist(industry_name)
        corr = ra.calculate_sector_correlation(df_hist, df_industry)
        report_data["行业相关性"] = f"{corr:.2f}" if corr else "N/A"

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

    # 6. 财务指标：扣非净利润
    print(f"正在获取 {symbol} 的财务指标...")
    deducted_profit = df.get_financial_deducted_profit(symbol)
    report_data["扣非净利润"] = deducted_profit

    # 7. 财报公告 (巨潮)
    print(f"正在获取 {symbol} 的最新财报公告...")
    report_info = df.get_latest_financial_report(symbol, preferred_year=preferred_year)
    if report_info:
        report_data["最新财报标题"] = report_info['title']
        report_data["最新财报发布日期"] = report_info['date']
    else:
        report_data["最新财报标题"] = "N/A"
        report_data["最新财报发布日期"] = "N/A"

    # 8. 资金流向饼图
    pie_path = vs.generate_fund_flow_pie_chart(symbol, fund_flow, output_dir=output_dir, symbol_name=symbol_name)
    report_data["资金流向饼图"] = pie_path

    # 8. 保存报告 CSV
    report_df = pd.DataFrame([report_data])
    output_path = os.path.join(final_dir, f"risk_report_{symbol}_{datetime.now().strftime('%Y%m%d')}.csv")
    report_df.to_csv(output_path, index=False, encoding="utf-8-sig")
    
    print(f"分析完成，报告保存至: {output_path}")
    return report_data
