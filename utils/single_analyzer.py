import sys
import os

# 确保能找到项目根目录
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if project_root not in sys.path:
    sys.path.append(project_root)

from core.orchestrator import perform_comprehensive_risk_analysis
from core.data_fetcher import get_symbol_by_name

def run_single_analysis():
    print("\n" + "="*40)
    print("      股票全维度分析工具 (单票模式)")
    print("="*40)
    
    # 优先从命令行获取参数，如果没有则进入交互模式
    if len(sys.argv) > 1:
        target = sys.argv[1]
    else:
        target = input("请输入股票名称或代码 (例如: '宝武镁业' 或 '002182'): ").strip()
    
    if not target:
        print("未输入有效内容，退出。")
        return

    # 自动识别名称或代码并获取标准代码 (Symbol)
    symbol = get_symbol_by_name(target)
    if not symbol:
        print(f"❌ 无法识别标的: {target}")
        return

    print(f"🚀 正在分析: {target} ({symbol})...")
    
    try:
        # 调用核心调度器，开启所有导出选项
        perform_comprehensive_risk_analysis(
            symbol, 
            preferred_year="2025", 
            download_reports=True, 
            export_hist=True, 
            export_fund_flow=True
        )
        print(f"\n✅ [成功] {target} 的分析已完成。")
        print(f"📂 结果文件已保存在 data 目录下对应的标的文件夹中。")
    except Exception as e:
        print(f"\n❌ [错误] 分析过程中发生异常: {e}")

if __name__ == "__main__":
    run_single_analysis()
