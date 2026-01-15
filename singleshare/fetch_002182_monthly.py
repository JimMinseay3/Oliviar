import sys
import os
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.append(project_root)
sys.path.append(os.path.join(project_root, "core"))
import QuantitativeTrading_Libs as lh
from datetime import datetime

if __name__ == "__main__":
    symbol = "002182"
    data_dir = "data"
    
    if not os.path.exists(data_dir):
        os.makedirs(data_dir)
        
    print(f"正在获取 {symbol} 近一个月的所有数据...")
    
    # 获取个股信息以确定名称
    info = lh.get_individual_info(symbol)
    name_res = info[info['item'] == '股票简称']['value'].values
    symbol_name = name_res[0] if len(name_res) > 0 else "Unknown"
    
    # 确定分类文件夹：data/代码_名称/
    target_folder = f"{symbol}_{symbol_name}"
    final_dir = os.path.join(data_dir, target_folder)
    if not os.path.exists(final_dir):
        os.makedirs(final_dir)
        
    # 获取近30天的数据
    df = lh.get_stock_hist_data(symbol, days=30)
    
    if not df.empty:
        file_name = f"hist_data_monthly_{symbol}_{datetime.now().strftime('%Y%m%d')}.csv"
        file_path = os.path.join(final_dir, file_name)
        
        # 保存为 CSV
        df.to_csv(file_path, index=False, encoding="utf-8-sig")
        print(f"数据已成功保存至: {file_path}")
        print(f"包含数据行数: {len(df)}")
    else:
        print("未获取到数据，请检查网络或代码。")
