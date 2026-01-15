import flet as ft
import flet.plotly_chart as ft_plotly
import sys
import os
import pandas as pd
from datetime import datetime
import plotly.express as px

# 确保能找到 core 目录
project_root = os.path.dirname(os.path.abspath(__file__))
sys.path.append(os.path.join(project_root, "core"))

import QuantitativeTrading_Libs as lh

def main(page: ft.Page):
    page.title = "Oliviar 量化交易助手"
    page.theme_mode = ft.ThemeMode.LIGHT
    page.window_width = 1100
    page.window_height = 850
    page.padding = 0
    page.spacing = 0
    
    # 颜色主题
    primary_color = ft.colors.BLUE_700
    bg_color = ft.colors.GREY_50

    # --- 状态变量 ---
    symbol_input = ft.TextField(
        label="股票代码", 
        hint_text="如 002701",
        width=250, 
        border_radius=10,
        prefix_icon=ft.icons.SEARCH
    )
    
    result_content = ft.Column(spacing=15, scroll=ft.ScrollMode.AUTO, expand=True)
    history_content = ft.Column(spacing=10, scroll=ft.ScrollMode.AUTO, expand=True)
    reports_content = ft.Column(spacing=15, scroll=ft.ScrollMode.AUTO, expand=True)
    dashboard_content = ft.Column([ft.Text("市场实时看板 (开发中...)", size=30)], expand=True)
    
    content_area = ft.Stack([
        ft.Container(content=result_content, visible=True),
        ft.Container(content=dashboard_content, visible=False),
        ft.Container(content=history_content, visible=False),
        ft.Container(content=reports_content, visible=False),
    ], expand=True)

    def load_dashboard():
        dashboard_content.controls.clear()
        dashboard_content.controls.append(ft.Text("市场行情概览", size=24, weight="bold"))
        
        # 模拟一些数据用于展示 Plotly 图表
        df = pd.DataFrame({
            "Sector": ["科技", "金融", "消费", "医疗", "能源"],
            "Change": [2.5, -1.2, 0.8, 1.5, -0.5]
        })
        fig = px.bar(df, x="Sector", y="Change", color="Change", 
                     title="行业涨跌幅 (示例)",
                     color_continuous_scale="RdYlGn")
        
        dashboard_content.controls.append(
            ft.Container(
                content=ft_plotly.PlotlyChart(fig, expand=True),
                height=400,
                padding=10,
                bgcolor=ft.colors.WHITE,
                border_radius=10
            )
        )
        page.update()

    def navigate(e):
        idx = e.control.selected_index
        # 切换可见性
        content_area.controls[0].visible = (idx == 0)
        content_area.controls[1].visible = (idx == 1)
        content_area.controls[2].visible = (idx == 2)
        content_area.controls[3].visible = (idx == 3)
        
        # 只有在个股分析和个股财报页面才显示搜索栏
        main_view.content.controls[0].visible = (idx == 0 or idx == 3)
        
        if idx == 1:
            load_dashboard()
        elif idx == 2:
            load_history()
        elif idx == 3:
            # 如果已有搜索代码，自动加载财报
            if symbol_input.value.strip():
                load_reports_ui()
            
        page.update()

    def load_reports_ui():
        symbol = symbol_input.value.strip()
        if not symbol:
            reports_content.controls.clear()
            reports_content.controls.append(ft.Text("请先输入股票代码", size=20))
            page.update()
            return

        reports_content.controls.clear()
        reports_content.controls.append(ft.Row([
            ft.ProgressRing(width=20, height=20),
            ft.Text(f"正在获取 {symbol} 的财报列表...")
        ]))
        page.update()

        try:
            current_year = datetime.now().year
            all_reports = []
            # 获取最近两年的财报
            for year in [str(current_year), str(current_year - 1)]:
                reports = lh.get_all_financial_reports(symbol, year)
                all_reports.extend(reports)
            
            reports_content.controls.clear()
            if not all_reports:
                reports_content.controls.append(ft.Text(f"未找到 {symbol} 的相关财报公告", size=18))
            else:
                reports_content.controls.append(ft.Text(f"{symbol} 历史财报公告", size=24, weight="bold"))
                for r in all_reports:
                    reports_content.controls.append(
                        ft.Card(
                            content=ft.Container(
                                content=ft.Row([
                                    ft.Column([
                                        ft.Text(r['title'], weight="bold", size=16),
                                        ft.Text(f"发布日期: {r['date']}", size=12, color=ft.colors.GREY_600),
                                    ], expand=True),
                                    ft.IconButton(
                                        icon=ft.icons.DOWNLOAD,
                                        tooltip="打开公告链接",
                                        on_click=lambda _, url=r['url']: page.launch_url(url)
                                    )
                                ], alignment=ft.MainAxisAlignment.SPACE_BETWEEN),
                                padding=15
                            )
                        )
                    )
        except Exception as ex:
            reports_content.controls.clear()
            reports_content.controls.append(ft.Text(f"获取财报失败: {str(ex)}", color=ft.colors.RED_400))
        
        page.update()

    def load_history():
        history_content.controls.clear()
        history_content.controls.append(ft.Text("最近生成的分析报告", size=24, weight="bold"))
        
        data_dir = os.path.join(project_root, "data")
        if os.path.exists(data_dir):
            # 遍历 data 目录下的子目录
            for folder in os.listdir(data_dir):
                folder_path = os.path.join(data_dir, folder)
                if os.path.isdir(folder_path):
                    history_content.controls.append(
                        ft.Card(
                            content=ft.Container(
                                content=ft.Row([
                                    ft.Icon(ft.icons.FOLDER, color=ft.colors.AMBER_600),
                                    ft.Text(folder, weight="bold"),
                                    ft.IconButton(ft.icons.OPEN_IN_NEW, on_click=lambda _, p=folder_path: os.startfile(p))
                                ], alignment=ft.MainAxisAlignment.SPACE_BETWEEN),
                                padding=15
                            )
                        )
                    )
        else:
            history_content.controls.append(ft.Text("暂无历史记录"))
        page.update()
    
    # --- 功能函数 ---
    def analyze_stock(e):
        symbol = symbol_input.value.strip()
        if not symbol:
            show_snack("请输入股票代码！")
            return

        # 显示进度条
        result_content.controls.clear()
        progress_ring = ft.Column([
            ft.ProgressRing(width=50, height=50, stroke_width=4),
            ft.Text("正在深度分析中，请稍候...", italic=True)
        ], horizontal_alignment=ft.CrossAxisAlignment.CENTER, alignment=ft.MainAxisAlignment.CENTER, expand=True)
        
        result_content.controls.append(progress_ring)
        page.update()

        try:
            # 1. 获取个股基本信息
            info = lh.get_individual_info(symbol)

            # 2. 执行综合风险分析
            analysis = lh.perform_comprehensive_risk_analysis(symbol)
            
            result_content.controls.clear()
            
            # 头部标题
            stock_name = "未知股票"
            if not info.empty:
                name_res = info[info['item'] == '股票简称']['value'].values
                stock_name = name_res[0] if len(name_res) > 0 else symbol

            result_content.controls.append(
                ft.Row([
                    ft.Text(f"{stock_name} ({symbol})", size=28, weight=ft.FontWeight.BOLD),
                    ft.Container(
                        content=ft.Text(f"综合分析: {analysis.get('流动性评估', 'N/A')}", size=12, color=ft.colors.GREEN_700, weight="bold"),
                        bgcolor=ft.colors.GREEN_100,
                        padding=ft.padding.symmetric(horizontal=10, vertical=5),
                        border_radius=20
                    )
                ], alignment=ft.MainAxisAlignment.SPACE_BETWEEN)
            )

            # 核心指标卡片组
            metrics_row = ft.ResponsiveRow([
                create_metric_card("波动率 (HV20)", analysis.get("HV20", "N/A"), ft.icons.SHOW_CHART, ft.colors.ORANGE_400),
                create_metric_card("今日主力流入", f"{analysis.get('今日主力净流入(万元)', '0')} 万", ft.icons.ATTACH_MONEY, ft.colors.GREEN_400),
                create_metric_card("扣非净利润", f"{analysis.get('扣非净利润', 'N/A')}", ft.icons.BUSINESS_CENTER, ft.colors.BLUE_400),
                create_metric_card("流动性", analysis.get("流动性评估", "N/A"), ft.icons.WATER_DROP, ft.colors.CYAN_400),
            ], spacing=10)
            
            result_content.controls.append(metrics_row)
            
            # 详细信息表格
            if not info.empty:
                data_table = ft.DataTable(
                    columns=[
                        ft.DataColumn(ft.Text("项目")),
                        ft.DataColumn(ft.Text("数值")),
                    ],
                    rows=[
                        ft.DataRow(cells=[ft.DataCell(ft.Text(row['item'])), ft.DataCell(ft.Text(row['value']))])
                        for _, row in info.iterrows()
                    ],
                    border=ft.border.all(1, ft.colors.GREY_200),
                    border_radius=10,
                )
                result_content.controls.append(ft.Text("个股基本信息", size=20, weight="bold"))
                result_content.controls.append(ft.Container(content=data_table, padding=10))

            # 资金流向图表 (如果有)
            chart_path = analysis.get("资金流向饼图")
            if chart_path and os.path.exists(chart_path):
                result_content.controls.append(ft.Text("资金流向分析", size=20, weight="bold"))
                result_content.controls.append(
                    ft.Container(
                        content=ft.Image(
                            src=chart_path,
                            width=600,
                            height=400,
                            fit=ft.ImageFit.CONTAIN,
                        ),
                        alignment=ft.alignment.center,
                        padding=10,
                        bgcolor=ft.colors.WHITE,
                        border_radius=10,
                        border=ft.border.all(1, ft.colors.GREY_100)
                    )
                )

        except Exception as ex:
            result_content.controls.clear()
            result_content.controls.append(
                ft.Container(
                    content=ft.Text(f"分析出错: {str(ex)}", color=ft.colors.RED_400),
                    padding=20, bgcolor=ft.colors.RED_50, border_radius=10
                )
            )
        
        page.update()

    def create_metric_card(title, value, icon, icon_color):
        return ft.Container(
            content=ft.Column([
                ft.ListTile(
                    leading=ft.Icon(icon, color=icon_color, size=30),
                    title=ft.Text(value, size=20, weight="bold"),
                    subtitle=ft.Text(title, size=12),
                )
            ]),
            bgcolor=ft.colors.WHITE,
            border_radius=12,
            padding=5,
            col={"sm": 6, "md": 3},
            border=ft.border.all(1, ft.colors.GREY_100),
            shadow=ft.BoxShadow(blur_radius=5, color=ft.colors.with_opacity(0.05, ft.colors.BLACK))
        )

    def show_snack(message):
        page.snack_bar = ft.SnackBar(ft.Text(message))
        page.snack_bar.open = True
        page.update()

    # --- 侧边栏与主布局 ---
    sidebar = ft.NavigationRail(
        selected_index=0,
        label_type=ft.NavigationRailLabelType.ALL,
        min_width=100,
        min_extended_width=200,
        leading=ft.Icon(ft.icons.SETTINGS_INPUT_COMPONENT, size=40, color=primary_color),
        group_alignment=-0.9,
        destinations=[
            ft.NavigationRailDestination(
                icon=ft.icons.ANALYTICS_OUTLINED,
                selected_icon=ft.icons.ANALYTICS,
                label="个股分析",
            ),
            ft.NavigationRailDestination(
                icon=ft.icons.DASHBOARD_OUTLINED,
                selected_icon=ft.icons.DASHBOARD,
                label="市场看板",
            ),
            ft.NavigationRailDestination(
                icon=ft.icons.HISTORY_OUTLINED,
                selected_icon=ft.icons.HISTORY,
                label="历史记录",
            ),
            ft.NavigationRailDestination(
                icon=ft.icons.ARTICLE_OUTLINED,
                selected_icon=ft.icons.ARTICLE,
                label="个股财报",
            ),
        ],
        on_change=navigate,
    )

    main_view = ft.Container(
        content=ft.Column([
            # 顶部搜索栏
            ft.Container(
                content=ft.Row([
                    symbol_input,
                    ft.ElevatedButton(
                        "开始分析", 
                        icon=ft.icons.PLAY_ARROW_ROUNDED,
                        on_click=analyze_stock,
                        style=ft.ButtonStyle(
                            color=ft.colors.WHITE,
                            bgcolor=primary_color,
                            padding=20,
                            shape=ft.RoundedRectangleBorder(radius=10)
                        )
                    ),
                ], alignment=ft.MainAxisAlignment.START, spacing=20),
                padding=20,
                bgcolor=ft.colors.WHITE,
                border=ft.border.only(bottom=ft.border.BorderSide(1, ft.colors.GREY_200)),
                visible=True # 默认显示，但在导航到其他页面时可能需要隐藏
            ),
            # 内容展示区
            ft.Container(
                content=content_area,
                padding=30,
                expand=True,
                bgcolor=bg_color
            )
        ], spacing=0),
        expand=True
    )

    page.add(
        ft.Row([
            sidebar,
            ft.VerticalDivider(width=1),
            main_view
        ], expand=True)
    )

if __name__ == "__main__":
    # 使用桌面模式运行
    ft.app(target=main)
