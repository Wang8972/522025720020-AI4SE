#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
构建脚本 - 使用PyInstaller创建可执行文件
"""

import os
import sys
import subprocess
import shutil

def install_pyinstaller():
    """安装PyInstaller"""
    try:
        import PyInstaller
        print("PyInstaller already installed")
        return True
    except ImportError:
        print("Installing PyInstaller...")
        result = subprocess.run([sys.executable, "-m", "pip", "install", "pyinstaller"], 
                              capture_output=True, text=True)
        if result.returncode == 0:
            print("PyInstaller installed successfully")
            return True
        else:
            print(f"Failed to install PyInstaller: {result.stderr}")
            return False

def build_executable():
    """构建可执行文件"""
    print("Building executable...")
    
    # PyInstaller命令参数
    cmd = [
        sys.executable, "-m", "PyInstaller",
        "--onefile",  # 打包成单个文件
        "--windowed",  # Windows下不显示控制台
        "--name", "PhotoWatermark",  # 可执行文件名
        "--icon", "icon.ico" if os.path.exists("icon.ico") else None,  # 图标文件（如果存在）
        "--add-data", "src;src",  # 包含源代码目录
        "--hidden-import", "PIL._tkinter_finder",  # 隐式导入
        "--hidden-import", "tkinterdnd2",
        "main.py"
    ]
    
    # 移除None值
    cmd = [arg for arg in cmd if arg is not None]
    
    try:
        result = subprocess.run(cmd, capture_output=True, text=True)
        if result.returncode == 0:
            print("Build successful!")
            print("Executable created in 'dist' folder")
            
            # 复制必要文件到dist目录
            dist_dir = "dist"
            if os.path.exists(dist_dir):
                # 复制README
                if os.path.exists("README.md"):
                    shutil.copy2("README.md", dist_dir)
                
                # 创建示例配置文件
                example_config = {
                    "watermark_text": "Sample Watermark",
                    "watermark_font_family": "Arial",
                    "watermark_font_size": 36,
                    "watermark_color": "#FFFFFF",
                    "watermark_opacity": 70,
                    "watermark_position": "bottom_right"
                }
                
                import json
                with open(os.path.join(dist_dir, "example_config.json"), "w", encoding="utf-8") as f:
                    json.dump(example_config, f, ensure_ascii=False, indent=2)
                
                print(f"Additional files copied to {dist_dir}")
            
            return True
        else:
            print(f"Build failed: {result.stderr}")
            return False
    except Exception as e:
        print(f"Build error: {e}")
        return False

def main():
    """主函数"""
    print("PhotoWatermark Build Script")
    print("=" * 40)
    
    # 检查当前目录
    if not os.path.exists("main.py"):
        print("Error: main.py not found. Please run this script from the project root directory.")
        return False
    
    # 安装PyInstaller
    if not install_pyinstaller():
        return False
    
    # 构建可执行文件
    if not build_executable():
        return False
    
    print("\nBuild completed successfully!")
    print("You can find the executable in the 'dist' folder.")
    print("To create a release, zip the contents of the 'dist' folder.")
    
    return True

if __name__ == "__main__":
    success = main()
    if not success:
        sys.exit(1)