#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
PhotoWatermark - 图片水印工具
主程序入口文件
"""

import sys
import os
import tkinter as tk
from tkinter import ttk, messagebox
import traceback

# 添加当前目录到Python路径
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

try:
    from src.watermark_app import WatermarkApp
except ImportError as e:
    print(f"导入错误: {e}")
    print("请确保已安装所有依赖包：pip install -r requirements.txt")
    sys.exit(1)

def main():
    """主函数"""
    try:
        # 尝试使用TkinterDnD创建主窗口（支持拖拽）
        try:
            from tkinterdnd2 import TkinterDnD
            root = TkinterDnD.Tk()
        except ImportError:
            # 如果TkinterDnD不可用，使用标准Tkinter
            root = tk.Tk()
        
        # 设置窗口图标和标题
        root.title("PhotoWatermark - 图片水印工具")
        root.geometry("1200x800")
        root.minsize(1000, 600)
        
        # 设置窗口居中
        root.update_idletasks()
        x = (root.winfo_screenwidth() // 2) - (1200 // 2)
        y = (root.winfo_screenheight() // 2) - (800 // 2)
        root.geometry(f"1200x800+{x}+{y}")
        
        # 创建应用实例
        app = WatermarkApp(root)
        
        # 启动主循环
        root.mainloop()
        
    except Exception as e:
        error_msg = f"应用程序启动失败:\n{str(e)}\n\n详细错误信息:\n{traceback.format_exc()}"
        print(error_msg)
        
        # 尝试显示错误对话框
        try:
            root = tk.Tk()
            root.withdraw()  # 隐藏主窗口
            messagebox.showerror("启动错误", error_msg)
        except:
            pass
        
        sys.exit(1)

if __name__ == "__main__":
    main()