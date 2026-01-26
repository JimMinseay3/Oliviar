import sys
import os
import time
import random

# 确保能找到项目根目录
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if project_root not in sys.path:
    sys.path.append(project_root)

# 直接从 core 导入分析模块
from core.orchestrator import perform_comprehensive_risk_analysis
from core.data_fetcher import get_symbol_by_name

def process_stocks(stock_names):
    print(f"--- 启动优化版批量处理器 (缓存模式) ---")
    
    results = []
    for name in stock_names:
        print(f"\n{'='*20} 正在检索: {name} {'='*20}")
        symbol = get_symbol_by_name(name)
        
        if not symbol:
            print(f"未找到股票: {name}")
            continue
            
        print(f"匹配成功: {name} -> {symbol}")
        try:
            # 执行综合分析并下载 2025 年所有财报到同一个文件夹
            perform_comprehensive_risk_analysis(symbol, preferred_year="2025", download_reports=True)
            print(f"[{name}] 处理完成。")
            results.append((name, symbol, "成功"))
        except Exception as e:
            print(f"[{name}] 处理失败: {e}")
            results.append((name, symbol, f"失败: {e}"))
        
        # 适当休眠，避免触发 API 限制
        time.sleep(random.uniform(0.5, 1.5))

    print(f"\n{'='*40}")
    print(f"任务报告 ({len(results)}/{len(stock_names)}):")
    for name, symbol, status in results:
        print(f"- {name} ({symbol}): {status}")
    print(f"{'='*40}")

if __name__ == "__main__":
    stocks = [
        "600981", "688981", "688360", "605133", # 之前的
        "顺控发展", "中超控股", "旋极信息", "立达信", "金隅集团", 
        "成飞集成", "达华智能", "国电南自", "榕基软件", "飞天诚信", 
        "华东重机", "大众交通", "士兰微", "东方新能", "金种子酒"
    ]
    process_stocks(stocks)
