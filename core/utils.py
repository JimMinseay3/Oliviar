import matplotlib
matplotlib.use('Agg')  # 强制使用非交互式后端，避免 Tkinter 线程冲突
import matplotlib.pyplot as plt
import warnings
import os

def setup_matplotlib():
    """设置中文显示"""
    plt.rcParams['font.sans-serif'] = ['SimHei']  # Windows 系统常用中文字体
    plt.rcParams['axes.unicode_minus'] = False

def ignore_warnings():
    """忽略不必要的警告"""
    warnings.filterwarnings('ignore')

def ensure_dir(path):
    """确保目录存在"""
    if not os.path.exists(path):
        os.makedirs(path)
