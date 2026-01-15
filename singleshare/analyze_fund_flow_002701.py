import sys
import os
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.append(project_root)
sys.path.append(os.path.join(project_root, "core"))
import QuantitativeTrading_Libs as lh
import pandas as pd
from datetime import datetime

def analyze_weekly_fund_flow_details(symbol: str, data_dir: str = "data"):
    print(f"开始深度分析 {symbol} 近一周资金流向明细...")
    
    # 1. 获取基础信息和资金流向数据
    info = lh.get_individual_info(symbol)
    name_res = info[info['item'] == '股票简称']['value'].values
    symbol_name = name_res[0] if len(name_res) > 0 else "Unknown"
    
    fund_flow_raw = lh.get_fund_flow(symbol)
    if fund_flow_raw.empty:
        print("未能获取到资金流向数据。")
        return
    
    # 2. 筛选近一周 (5个交易日) 的明细数据
    week_flow = fund_flow_raw.head(5).copy()
    
    # 提取关键列 (日期 + 各类单净额)
    cols_map = {
        '日期': '日期',
        '超大单(万元)': [c for c in week_flow.columns if '超大单' in c and '净额' in c][0],
        '大单(万元)': [c for c in week_flow.columns if '大单' in c and '净额' in c][0],
        '中单(万元)': [c for c in week_flow.columns if '中单' in c and '净额' in c][0],
        '小单(万元)': [c for c in week_flow.columns if '小单' in c and '净额' in c][0],
        '主力(万元)': [c for c in week_flow.columns if '主力净流入' in c and '净额' in c][0]
    }
    
    # 转换为万元
    analysis_df = week_flow[list(cols_map.values())].copy()
    analysis_df.columns = list(cols_map.keys())
    
    numeric_cols = ['超大单(万元)', '大单(万元)', '中单(万元)', '小单(万元)', '主力(万元)']
    for col in numeric_cols:
        analysis_df[col] = analysis_df[col] / 10000 # 转为万元
        
    # 计算每日变化量 (环比涨跌额) - 注意数据通常是按日期降序排列的
    # 我们先按日期升序排列来计算变化
    analysis_df = analysis_df.sort_values('日期')
    for col in numeric_cols:
        # 去掉原有的 (万元) 后缀再加日增量后缀，或者直接加
        col_base = col.replace('(万元)', '')
        analysis_df[f'{col_base}日增量(万元)'] = analysis_df[col].diff()
    
    # 恢复降序显示
    analysis_df = analysis_df.sort_values('日期', ascending=False)
    
    # 3. 确定保存路径
    target_folder = f"{symbol}_{symbol_name}"
    final_dir = os.path.join(data_dir, target_folder)
    if not os.path.exists(final_dir):
        os.makedirs(final_dir)
        
    file_name = f"fund_flow_weekly_detail_{symbol}_{datetime.now().strftime('%Y%m%d')}.csv"
    file_path = os.path.join(final_dir, file_name)
    
    # 4. 保存文件
    analysis_df.to_csv(file_path, index=False, encoding="utf-8-sig")
    print(f"分析完成！详细资金流向变化已保存至: {file_path}")
    
    # 打印简要摘要
    print("\n--- 近一周资金流向摘要 (万元) ---")
    summary_cols = ['日期', '主力(万元)', '超大单(万元)', '大单(万元)', '中单(万元)', '小单(万元)']
    print(analysis_df[summary_cols].to_string(index=False))

if __name__ == "__main__":
    analyze_weekly_fund_flow_details("002701")
