import sys
import os
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.append(project_root)
sys.path.append(os.path.join(project_root, "core"))
import QuantitativeTrading_Libs as lh

if __name__ == "__main__":
    # 执行 002182 (恩捷股份) 的分析
    symbol = "002182"
    print(f"开始分析股票: {symbol}")
    result = lh.perform_comprehensive_risk_analysis(symbol)
    
    print("\n--- 分析摘要 ---")
    for key, value in result.items():
        print(f"{key}: {value}")
