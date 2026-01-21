import sys
import json
import os
import io
from lib.orchestrator import perform_comprehensive_risk_analysis

# 强制设置 stdout 为 UTF-8 编码，防止 Windows 下输出乱码
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

def main():
    if len(sys.argv) < 2:
        print(json.dumps({"error": "No symbol provided"}))
        return

    symbol = sys.argv[1]
    download = "--download" in sys.argv
    output_dir = "data"
    
    # 查找 --output-dir 参数
    for i, arg in enumerate(sys.argv):
        if arg == "--output-dir" and i + 1 < len(sys.argv):
            output_dir = sys.argv[i + 1]
            break
    
    try:
        # 运行分析
        from io import StringIO
        import contextlib
        
        f = StringIO()
        with contextlib.redirect_stdout(f):
            # 根据参数决定是否下载财报
            result = perform_comprehensive_risk_analysis(symbol, output_dir=output_dir, download_reports=download)
        
        # 如果 orchestrator 返回了 report_data，我们就打印它
        if result:
            # 使用 json.dumps 直接处理，如果需要自定义序列化可以在这里添加 default 处理
            # orchestrator 返回的应该是标准 python 类型 (dict, list, str, etc.)
            print(json.dumps(result, ensure_ascii=False))
        else:
            # 如果没有返回值，尝试从结果文件中读取（如果生成了）
            print(json.dumps({"error": "Analysis failed to return data", "logs": f.getvalue()}, ensure_ascii=False))
            
    except Exception as e:
        print(json.dumps({"error": str(e)}, ensure_ascii=False))

if __name__ == "__main__":
    main()
