import matplotlib.pyplot as plt
import os
import pandas as pd
from datetime import datetime
from matplotlib.lines import Line2D

def generate_fund_flow_pie_chart(symbol: str, fund_flow_df: pd.DataFrame, output_dir: str = "data", symbol_name: str = ""):
    """生成一周资金流向分析饼图"""
    if fund_flow_df.empty:
        return None
    
    # 确定最终保存路径
    folder_name = f"{symbol}_{symbol_name}" if symbol_name else symbol
    final_dir = os.path.join(output_dir, folder_name)
    if not os.path.exists(final_dir):
        os.makedirs(final_dir)
    
    try:
        # 取近5个交易日 (约一周)
        week_data = fund_flow_df.head(5)
        
        # 汇总各项流入净额
        cols = {
            '超大单': [c for c in week_data.columns if '超大单' in c and '净额' in c][0],
            '大单': [c for c in week_data.columns if '大单' in c and '净额' in c][0],
            '中单': [c for c in week_data.columns if '中单' in c and '净额' in c][0],
            '小单': [c for c in week_data.columns if '小单' in c and '净额' in c][0]
        }
        
        sums = {k: week_data[v].sum() for k, v in cols.items()}
        
        # 准备绘图数据逻辑优化
        size_order = ['小单', '中单', '大单', '超大单']
        color_palette = {
            '超大单': {'in': '#8B0000', 'out': '#006400'},
            '大单':   {'in': '#FF0000', 'out': '#008000'},
            '中单':   {'in': '#FF6347', 'out': '#32CD32'},
            '小单':   {'in': '#FFB6C1', 'out': '#98FB98'}
        }
        
        # 将数据分为流入和流出两组
        inflow_data = []
        outflow_data = []
        
        for size in size_order:
            val = sums[size]
            item = {
                'label': size,
                'raw_val': val,
                'abs_val': abs(val),
                'color': color_palette[size]['in'] if val >= 0 else color_palette[size]['out']
            }
            if val >= 0:
                inflow_data.append(item)
            else:
                outflow_data.append(item)
        
        # 组合排序：流入(从小到大) -> 流出(从小到大)
        plot_items = inflow_data + outflow_data
        
        labels = [f"{item['label']}\n({item['raw_val']/10000:.1f}万)" for item in plot_items]
        values = [item['abs_val'] for item in plot_items]
        colors = [item['color'] for item in plot_items]
        
        # 创建图形
        fig, ax = plt.subplots(figsize=(12, 8))
        
        # 绘制饼图
        wedges, texts, autotexts = ax.pie(
            values, 
            labels=labels,
            autopct='%1.1f%%', 
            startangle=140, 
            colors=colors,
            pctdistance=0.85,
            explode=[0.05] * len(plot_items)
        )
        
        plt.setp(autotexts, size=10, weight="bold", color="white")
        plt.setp(texts, size=11)
        
        ax.set_title(f"股票 {symbol} 近一周主力资金流向构成\n(排列：流入组[小->大] -> 流出组[小->大])", fontsize=14, pad=20)
        
        # 构造图例
        legend_elements = []
        for size in size_order:
            legend_elements.append(Line2D([0], [0], marker='o', color='w', label=f"{size} (流入)",
                                  markerfacecolor=color_palette[size]['in'], markersize=10))
        for size in size_order:
            legend_elements.append(Line2D([0], [0], marker='o', color='w', label=f"{size} (流出)",
                                  markerfacecolor=color_palette[size]['out'], markersize=10))
        
        ax.legend(handles=legend_elements, title="资金规模与流向全景图", 
                  loc="lower left", bbox_to_anchor=(-0.1, -0.1), ncol=2, frameon=True)
        
        plt.tight_layout()
        file_path = os.path.join(final_dir, f"fund_flow_pie_{symbol}_{datetime.now().strftime('%Y%m%d')}.png")
        plt.savefig(file_path, dpi=100)
        plt.close()
        return file_path
    except Exception as e:
        print(f"生成饼图失败: {e}")
        return None
