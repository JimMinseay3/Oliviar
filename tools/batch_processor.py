import sys
import os

# 将项目根目录和 core 目录添加到路径
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.append(project_root)
sys.path.append(os.path.join(project_root, "core"))

import QuantitativeTrading_Libs as lh
import pandas as pd
from datetime import datetime

def batch_process_stocks(symbols, preferred_year=None):
    data_dir = os.path.join(project_root, "data")
    if not os.path.exists(data_dir):
        os.makedirs(data_dir)

    for symbol in symbols:
        print(f"\n{'='*50}")
        print(f"正在处理标的: {symbol}")
        print(f"{'='*50}")

        try:
            # 1. 执行综合分析 (含扣非净利润、风险评估、饼图)
            result = lh.perform_comprehensive_risk_analysis(symbol, output_dir=data_dir, preferred_year=preferred_year)
            
            # 获取标的名称用于后续文件分类
            info = lh.get_individual_info(symbol)
            name_res = info[info['item'] == '股票简称']['value'].values
            symbol_name = name_res[0] if len(name_res) > 0 else "Unknown"
            target_folder = f"{symbol}_{symbol_name}"
            final_dir = os.path.join(data_dir, target_folder)

            # 2. 获取月度历史数据
            print(f"正在获取 {symbol} 的月度历史行情...")
            df_hist = lh.get_stock_hist_data(symbol, days=30)
            if not df_hist.empty:
                hist_file = os.path.join(final_dir, f"hist_data_monthly_{symbol}_{datetime.now().strftime('%Y%m%d')}.csv")
                df_hist.to_csv(hist_file, index=False, encoding="utf-8-sig")
                print(f"月度历史数据已保存: {hist_file}")

            # 3. 分析周资金流向明细
            print(f"正在分析 {symbol} 的周资金流向明细...")
            fund_flow_raw = lh.get_fund_flow(symbol)
            if not fund_flow_raw.empty:
                week_flow = fund_flow_raw.head(5).copy()
                
                # 提取并转换列
                cols_map = {
                    '日期': '日期',
                    '超大单(万元)': [c for c in week_flow.columns if '超大单' in c and '净额' in c][0],
                    '大单(万元)': [c for c in week_flow.columns if '大单' in c and '净额' in c][0],
                    '中单(万元)': [c for c in week_flow.columns if '中单' in c and '净额' in c][0],
                    '小单(万元)': [c for c in week_flow.columns if '小单' in c and '净额' in c][0],
                    '主力(万元)': [c for c in week_flow.columns if '主力净流入' in c and '净额' in c][0]
                }
                
                analysis_df = week_flow[list(cols_map.values())].copy()
                analysis_df.columns = list(cols_map.keys())
                
                numeric_cols = ['超大单(万元)', '大单(万元)', '中单(万元)', '小单(万元)', '主力(万元)']
                for col in numeric_cols:
                    analysis_df[col] = analysis_df[col] / 10000
                
                # 计算增量
                analysis_df = analysis_df.sort_values('日期')
                for col in numeric_cols:
                    col_base = col.replace('(万元)', '')
                    analysis_df[f'{col_base}日增量(万元)'] = analysis_df[col].diff()
                
                analysis_df = analysis_df.sort_values('日期', ascending=False)
                
                detail_file = os.path.join(final_dir, f"fund_flow_weekly_detail_{symbol}_{datetime.now().strftime('%Y%m%d')}.csv")
                analysis_df.to_csv(detail_file, index=False, encoding="utf-8-sig")
                print(f"周资金明细已保存: {detail_file}")

            # 4. 获取并下载指定年份内发布的所有财报 PDF
            print(f"正在尝试下载 {symbol} 在 {preferred_year} 年内发布的所有财报 PDF...")
            all_reports = lh.get_all_financial_reports(symbol, preferred_year)
            if all_reports:
                for report_info in all_reports:
                    # 清理文件名中的非法字符
                    safe_title = report_info['title'].replace(':', '_').replace('*', '_').replace('/', '_').replace('\\', '_')
                    pdf_name = f"{safe_title}.pdf"
                    pdf_path = os.path.join(final_dir, pdf_name)
                    
                    if not os.path.exists(pdf_path):
                        print(f"  -> 正在下载: {safe_title}...")
                        success = lh.download_report_pdf(report_info['url'], pdf_path)
                        if success:
                            print(f"     成功: {pdf_path}")
                        else:
                            print(f"     失败: {report_info['url']}")
                    else:
                        print(f"  -> 财报已存在，跳过下载: {safe_title}")
            else:
                print(f"未找到 {preferred_year} 年内发布的财报链接")

            print(f"标多 {symbol} ({symbol_name}) 处理完成。")

        except Exception as e:
            print(f"处理标的 {symbol} 时发生错误: {e}")

if __name__ == "__main__":
    stocks_to_process = ["688591", "600151"]
    batch_process_stocks(stocks_to_process, preferred_year="2025")
