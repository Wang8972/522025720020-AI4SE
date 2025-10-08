#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
PhotoWatermark - 主应用程序类
"""

import tkinter as tk
from tkinter import ttk, filedialog, messagebox, colorchooser, font
import os
import json
from PIL import Image, ImageTk, ImageDraw, ImageFont, ImageFilter
import threading
from typing import List, Dict, Optional, Tuple
import traceback

try:
    from tkinterdnd2 import DND_FILES, TkinterDnD
    DND_AVAILABLE = True
except ImportError:
    DND_AVAILABLE = False
    print("警告: tkinterdnd2 未安装，拖拽功能将不可用")

class WatermarkApp:
    """水印应用程序主类"""
    
    def __init__(self, root):
        self.root = root
        self.setup_variables()
        self.setup_ui()
        self.load_settings()
        
    def setup_variables(self):
        """初始化变量"""
        # 图片相关
        self.image_list = []  # 存储图片路径列表
        self.current_image_index = 0
        self.current_image = None
        self.preview_image = None
        self.watermarked_image = None
        
        # 水印设置
        self.watermark_type = tk.StringVar(value="text")  # text 或 image
        self.watermark_text = tk.StringVar(value="Sample Watermark")
        self.watermark_font_family = tk.StringVar(value="Arial")
        self.watermark_font_size = tk.IntVar(value=36)
        self.watermark_color = "#FFFFFF"
        self.watermark_opacity = tk.IntVar(value=70)
        self.watermark_position = tk.StringVar(value="bottom_right")
        self.watermark_rotation = tk.IntVar(value=0)
        self.watermark_shadow = tk.BooleanVar(value=True)
        self.watermark_outline = tk.BooleanVar(value=False)
        
        # 图片水印设置
        self.watermark_image_path = tk.StringVar()
        self.watermark_image_scale = tk.DoubleVar(value=1.0)
        self.watermark_image = None
        
        # 导出设置
        self.output_format = tk.StringVar(value="PNG")
        self.output_quality = tk.IntVar(value=95)
        self.output_folder = tk.StringVar()
        self.filename_prefix = tk.StringVar(value="")
        self.filename_suffix = tk.StringVar(value="_watermarked")
        self.keep_original_name = tk.BooleanVar(value=True)
        
        # 支持的图片格式
        self.supported_formats = {
            '.jpg', '.jpeg', '.png', '.bmp', '.tiff', '.tif'
        }
        
    def setup_ui(self):
        """设置用户界面"""
        # 配置样式
        style = ttk.Style()
        style.theme_use('clam')
        
        # 主框架
        main_frame = ttk.Frame(self.root)
        main_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        
        # 创建左右分割的面板
        paned_window = ttk.PanedWindow(main_frame, orient=tk.HORIZONTAL)
        paned_window.pack(fill=tk.BOTH, expand=True)
        
        # 左侧面板（图片列表和预览）
        left_frame = ttk.Frame(paned_window)
        paned_window.add(left_frame, weight=3)
        
        # 右侧面板（水印设置）
        right_frame = ttk.Frame(paned_window)
        paned_window.add(right_frame, weight=1)
        
        self.setup_left_panel(left_frame)
        self.setup_right_panel(right_frame)
        
        # 设置拖拽功能
        if DND_AVAILABLE:
            self.root.drop_target_register(DND_FILES)
            self.root.dnd_bind('<<Drop>>', self.on_drop)
    
    def setup_left_panel(self, parent):
        """设置左侧面板"""
        # 工具栏
        toolbar = ttk.Frame(parent)
        toolbar.pack(fill=tk.X, pady=(0, 10))
        
        ttk.Button(toolbar, text="导入图片", command=self.import_images).pack(side=tk.LEFT, padx=(0, 5))
        ttk.Button(toolbar, text="导入文件夹", command=self.import_folder).pack(side=tk.LEFT, padx=(0, 5))
        ttk.Button(toolbar, text="清空列表", command=self.clear_images).pack(side=tk.LEFT, padx=(0, 5))
        
        # 分割面板（上下）
        content_paned = ttk.PanedWindow(parent, orient=tk.VERTICAL)
        content_paned.pack(fill=tk.BOTH, expand=True)
        
        # 图片列表区域
        list_frame = ttk.LabelFrame(content_paned, text="图片列表")
        content_paned.add(list_frame, weight=1)
        
        # 创建图片列表
        list_container = ttk.Frame(list_frame)
        list_container.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        
        # 滚动条
        list_scrollbar = ttk.Scrollbar(list_container)
        list_scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        
        # 列表框
        self.image_listbox = tk.Listbox(
            list_container, 
            yscrollcommand=list_scrollbar.set,
            selectmode=tk.SINGLE
        )
        self.image_listbox.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        list_scrollbar.config(command=self.image_listbox.yview)
        
        # 绑定选择事件
        self.image_listbox.bind('<<ListboxSelect>>', self.on_image_select)
        
        # 预览区域
        preview_frame = ttk.LabelFrame(content_paned, text="预览")
        content_paned.add(preview_frame, weight=2)
        
        # 预览画布
        self.preview_canvas = tk.Canvas(
            preview_frame, 
            bg='white',
            cursor='hand2'
        )
        self.preview_canvas.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        
        # 绑定画布事件
        self.preview_canvas.bind('<Button-1>', self.on_canvas_click)
        self.preview_canvas.bind('<B1-Motion>', self.on_canvas_drag)
        self.preview_canvas.bind('<ButtonRelease-1>', self.on_canvas_release)
        
        # 拖拽相关变量
        self.dragging = False
        self.drag_start_x = 0
        self.drag_start_y = 0
        self.watermark_x = 0
        self.watermark_y = 0
    
    def setup_right_panel(self, parent):
        """设置右侧面板"""
        # 创建滚动区域
        canvas = tk.Canvas(parent)
        scrollbar = ttk.Scrollbar(parent, orient="vertical", command=canvas.yview)
        scrollable_frame = ttk.Frame(canvas)
        
        scrollable_frame.bind(
            "<Configure>",
            lambda e: canvas.configure(scrollregion=canvas.bbox("all"))
        )
        
        canvas.create_window((0, 0), window=scrollable_frame, anchor="nw")
        canvas.configure(yscrollcommand=scrollbar.set)
        
        canvas.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")
        
        # 水印设置区域
        self.setup_watermark_settings(scrollable_frame)
        
        # 导出设置区域
        self.setup_export_settings(scrollable_frame)
        
        # 操作按钮
        self.setup_action_buttons(scrollable_frame)
    
    def setup_watermark_settings(self, parent):
        """设置水印配置区域"""
        # 水印类型选择
        type_frame = ttk.LabelFrame(parent, text="水印类型")
        type_frame.pack(fill=tk.X, padx=5, pady=5)
        
        ttk.Radiobutton(
            type_frame,
            text="文本水印",
            variable=self.watermark_type,
            value="text",
            command=self.on_watermark_type_change
        ).pack(side=tk.LEFT, padx=5, pady=5)
        
        ttk.Radiobutton(
            type_frame,
            text="图片水印",
            variable=self.watermark_type,
            value="image",
            command=self.on_watermark_type_change
        ).pack(side=tk.LEFT, padx=5, pady=5)
        
        # 文本水印设置
        self.text_frame = ttk.LabelFrame(parent, text="文本水印设置")
        self.text_frame.pack(fill=tk.X, padx=5, pady=5)
        
        # 水印文本
        ttk.Label(self.text_frame, text="水印文本:").pack(anchor=tk.W, padx=5, pady=2)
        text_entry = ttk.Entry(self.text_frame, textvariable=self.watermark_text)
        text_entry.pack(fill=tk.X, padx=5, pady=2)
        text_entry.bind('<KeyRelease>', lambda e: self.update_preview())
        
        # 字体设置
        font_frame = ttk.Frame(self.text_frame)
        font_frame.pack(fill=tk.X, padx=5, pady=2)
        
        ttk.Label(font_frame, text="字体:").pack(side=tk.LEFT)
        font_combo = ttk.Combobox(
            font_frame, 
            textvariable=self.watermark_font_family,
            values=list(font.families()),
            state="readonly",
            width=15
        )
        font_combo.pack(side=tk.LEFT, padx=(5, 10))
        font_combo.bind('<<ComboboxSelected>>', lambda e: self.update_preview())
        
        ttk.Label(font_frame, text="大小:").pack(side=tk.LEFT)
        size_spin = ttk.Spinbox(
            font_frame,
            from_=8,
            to=200,
            textvariable=self.watermark_font_size,
            width=8,
            command=self.update_preview
        )
        size_spin.pack(side=tk.LEFT, padx=5)
        size_spin.bind('<KeyRelease>', lambda e: self.update_preview())
        size_spin.bind('<ButtonRelease-1>', lambda e: self.update_preview())
        size_spin.bind('<MouseWheel>', lambda e: self.update_preview())
        
        # 颜色和透明度
        color_frame = ttk.Frame(self.text_frame)
        color_frame.pack(fill=tk.X, padx=5, pady=2)
        
        ttk.Label(color_frame, text="颜色:").pack(side=tk.LEFT)
        self.color_button = tk.Button(
            color_frame,
            text="选择颜色",
            bg=self.watermark_color,
            command=self.choose_color,
            width=10
        )
        self.color_button.pack(side=tk.LEFT, padx=5)
        
        ttk.Label(color_frame, text="透明度:").pack(side=tk.LEFT, padx=(10, 5))
        opacity_scale = ttk.Scale(
            color_frame,
            from_=0,
            to=100,
            variable=self.watermark_opacity,
            orient=tk.HORIZONTAL,
            length=100,
            command=lambda v: self.update_preview()
        )
        opacity_scale.pack(side=tk.LEFT, padx=5)
        
        opacity_label = ttk.Label(color_frame, text="70%")
        opacity_label.pack(side=tk.LEFT, padx=5)
        
        # 更新透明度标签
        def update_opacity_label(value):
            opacity_label.config(text=f"{int(float(value))}%")
            self.update_preview()
        opacity_scale.config(command=update_opacity_label)
        
        # 图片水印设置
        self.image_frame = ttk.LabelFrame(parent, text="图片水印设置")
        # 初始状态下不显示图片水印设置框架
        
        # 图片选择
        image_select_frame = ttk.Frame(self.image_frame)
        image_select_frame.pack(fill=tk.X, padx=5, pady=5)
        
        ttk.Label(image_select_frame, text="水印图片:").pack(anchor=tk.W)
        image_path_frame = ttk.Frame(image_select_frame)
        image_path_frame.pack(fill=tk.X, pady=2)
        
        self.image_path_entry = ttk.Entry(image_path_frame, textvariable=self.watermark_image_path)
        self.image_path_entry.pack(side=tk.LEFT, fill=tk.X, expand=True)
        
        ttk.Button(
            image_path_frame,
            text="浏览",
            command=self.choose_watermark_image,
            width=8
        ).pack(side=tk.RIGHT, padx=(5, 0))
        
        # 图片缩放
        scale_frame = ttk.Frame(self.image_frame)
        scale_frame.pack(fill=tk.X, padx=5, pady=5)
        
        ttk.Label(scale_frame, text="缩放比例:").pack(side=tk.LEFT)
        scale_scale = ttk.Scale(
            scale_frame,
            from_=0.1,
            to=3.0,
            variable=self.watermark_image_scale,
            orient=tk.HORIZONTAL,
            length=150,
            command=lambda v: self.update_preview()
        )
        scale_scale.pack(side=tk.LEFT, padx=5)
        
        scale_label = ttk.Label(scale_frame, text="1.0x")
        scale_label.pack(side=tk.LEFT, padx=5)
        
        def update_scale_label(value):
            scale_label.config(text=f"{float(value):.1f}x")
            self.update_preview()
        scale_scale.config(command=update_scale_label)
        
        # 图片透明度
        img_opacity_frame = ttk.Frame(self.image_frame)
        img_opacity_frame.pack(fill=tk.X, padx=5, pady=5)
        
        ttk.Label(img_opacity_frame, text="透明度:").pack(side=tk.LEFT)
        img_opacity_scale = ttk.Scale(
            img_opacity_frame,
            from_=0,
            to=100,
            variable=self.watermark_opacity,
            orient=tk.HORIZONTAL,
            length=150,
            command=lambda v: self.update_preview()
        )
        img_opacity_scale.pack(side=tk.LEFT, padx=5)
        
        img_opacity_label = ttk.Label(img_opacity_frame, text="70%")
        img_opacity_label.pack(side=tk.LEFT, padx=5)
        
        def update_img_opacity_label(value):
            img_opacity_label.config(text=f"{int(float(value))}%")
            self.update_preview()
        img_opacity_scale.config(command=update_img_opacity_label)
        
        # 位置设置
        position_frame = ttk.LabelFrame(parent, text="位置设置")
        position_frame.pack(fill=tk.X, padx=5, pady=5)
        
        ttk.Label(position_frame, text="预设位置:").pack(anchor=tk.W, padx=5, pady=2)
        
        # 九宫格位置按钮
        grid_frame = ttk.Frame(position_frame)
        grid_frame.pack(padx=5, pady=5)
        
        positions = [
            ("左上", "top_left"), ("上中", "top_center"), ("右上", "top_right"),
            ("左中", "middle_left"), ("中心", "center"), ("右中", "middle_right"),
            ("左下", "bottom_left"), ("下中", "bottom_center"), ("右下", "bottom_right")
        ]
        
        for i, (text, value) in enumerate(positions):
            row, col = divmod(i, 3)
            btn = ttk.Radiobutton(
                grid_frame,
                text=text,
                variable=self.watermark_position,
                value=value,
                command=self.update_preview
            )
            btn.grid(row=row, column=col, padx=2, pady=2, sticky="ew")
        
        # 旋转设置
        rotation_frame = ttk.Frame(position_frame)
        rotation_frame.pack(fill=tk.X, padx=5, pady=5)
        
        ttk.Label(rotation_frame, text="旋转角度:").pack(side=tk.LEFT)
        rotation_scale = ttk.Scale(
            rotation_frame,
            from_=-180,
            to=180,
            variable=self.watermark_rotation,
            orient=tk.HORIZONTAL,
            length=150,
            command=lambda v: self.update_preview()
        )
        rotation_scale.pack(side=tk.LEFT, padx=5)
        
        rotation_label = ttk.Label(rotation_frame, text="0°")
        rotation_label.pack(side=tk.LEFT, padx=5)
        
        def update_rotation_label(value):
            rotation_label.config(text=f"{int(float(value))}°")
            self.update_preview()
        rotation_scale.config(command=update_rotation_label)
        
        # 效果设置
        effects_frame = ttk.LabelFrame(parent, text="效果设置")
        effects_frame.pack(fill=tk.X, padx=5, pady=5)
        
        shadow_check = ttk.Checkbutton(
            effects_frame,
            text="阴影效果",
            variable=self.watermark_shadow,
            command=self.update_preview
        )
        shadow_check.pack(anchor=tk.W, padx=5, pady=2)
        
        outline_check = ttk.Checkbutton(
            effects_frame,
            text="描边效果",
            variable=self.watermark_outline,
            command=self.update_preview
        )
        outline_check.pack(anchor=tk.W, padx=5, pady=2)
        
        # 初始化水印类型显示
        self.on_watermark_type_change()
    
    def setup_export_settings(self, parent):
        """设置导出配置区域"""
        export_frame = ttk.LabelFrame(parent, text="导出设置")
        export_frame.pack(fill=tk.X, padx=5, pady=5)
        
        # 输出格式
        format_frame = ttk.Frame(export_frame)
        format_frame.pack(fill=tk.X, padx=5, pady=2)
        
        ttk.Label(format_frame, text="输出格式:").pack(side=tk.LEFT)
        format_combo = ttk.Combobox(
            format_frame,
            textvariable=self.output_format,
            values=["PNG", "JPEG"],
            state="readonly",
            width=10
        )
        format_combo.pack(side=tk.LEFT, padx=5)
        
        # JPEG质量设置
        quality_frame = ttk.Frame(export_frame)
        quality_frame.pack(fill=tk.X, padx=5, pady=2)
        
        ttk.Label(quality_frame, text="JPEG质量:").pack(side=tk.LEFT)
        quality_scale = ttk.Scale(
            quality_frame,
            from_=1,
            to=100,
            variable=self.output_quality,
            orient=tk.HORIZONTAL,
            length=100
        )
        quality_scale.pack(side=tk.LEFT, padx=5)
        
        quality_label = ttk.Label(quality_frame, text="95")
        quality_label.pack(side=tk.LEFT, padx=5)
        
        def update_quality_label(value):
            quality_label.config(text=str(int(float(value))))
        quality_scale.config(command=update_quality_label)
        
        # 输出文件夹
        folder_frame = ttk.Frame(export_frame)
        folder_frame.pack(fill=tk.X, padx=5, pady=2)
        
        ttk.Label(folder_frame, text="输出文件夹:").pack(anchor=tk.W)
        folder_entry_frame = ttk.Frame(folder_frame)
        folder_entry_frame.pack(fill=tk.X, pady=2)
        
        folder_entry = ttk.Entry(folder_entry_frame, textvariable=self.output_folder)
        folder_entry.pack(side=tk.LEFT, fill=tk.X, expand=True)
        
        ttk.Button(
            folder_entry_frame,
            text="浏览",
            command=self.choose_output_folder,
            width=8
        ).pack(side=tk.RIGHT, padx=(5, 0))
        
        # 文件命名
        naming_frame = ttk.LabelFrame(export_frame, text="文件命名")
        naming_frame.pack(fill=tk.X, padx=5, pady=5)
        
        ttk.Checkbutton(
            naming_frame,
            text="保留原文件名",
            variable=self.keep_original_name
        ).pack(anchor=tk.W, padx=5, pady=2)
        
        prefix_frame = ttk.Frame(naming_frame)
        prefix_frame.pack(fill=tk.X, padx=5, pady=2)
        ttk.Label(prefix_frame, text="前缀:").pack(side=tk.LEFT)
        ttk.Entry(prefix_frame, textvariable=self.filename_prefix, width=15).pack(side=tk.LEFT, padx=5)
        
        suffix_frame = ttk.Frame(naming_frame)
        suffix_frame.pack(fill=tk.X, padx=5, pady=2)
        ttk.Label(suffix_frame, text="后缀:").pack(side=tk.LEFT)
        ttk.Entry(suffix_frame, textvariable=self.filename_suffix, width=15).pack(side=tk.LEFT, padx=5)
    
    def setup_action_buttons(self, parent):
        """设置操作按钮"""
        button_frame = ttk.Frame(parent)
        button_frame.pack(fill=tk.X, padx=5, pady=10)
        
        ttk.Button(
            button_frame,
            text="保存模板",
            command=self.save_template
        ).pack(fill=tk.X, pady=2)
        
        ttk.Button(
            button_frame,
            text="加载模板",
            command=self.load_template
        ).pack(fill=tk.X, pady=2)
        
        ttk.Button(
            button_frame,
            text="导出当前图片",
            command=self.export_current_image
        ).pack(fill=tk.X, pady=2)
        
        ttk.Button(
            button_frame,
            text="批量导出",
            command=self.export_all_images
        ).pack(fill=tk.X, pady=2)
    
    def import_images(self):
        """导入图片文件"""
        filetypes = [
            ("图片文件", "*.jpg *.jpeg *.png *.bmp *.tiff *.tif"),
            ("JPEG文件", "*.jpg *.jpeg"),
            ("PNG文件", "*.png"),
            ("BMP文件", "*.bmp"),
            ("TIFF文件", "*.tiff *.tif"),
            ("所有文件", "*.*")
        ]
        
        files = filedialog.askopenfilenames(
            title="选择图片文件",
            filetypes=filetypes
        )
        
        if files:
            self.add_images(files)
    
    def import_folder(self):
        """导入文件夹中的所有图片"""
        folder = filedialog.askdirectory(title="选择图片文件夹")
        if folder:
            image_files = []
            for root, dirs, files in os.walk(folder):
                for file in files:
                    if any(file.lower().endswith(ext) for ext in self.supported_formats):
                        image_files.append(os.path.join(root, file))
            
            if image_files:
                self.add_images(image_files)
            else:
                messagebox.showinfo("提示", "所选文件夹中没有找到支持的图片文件")
    
    def add_images(self, file_paths):
        """添加图片到列表"""
        added_count = 0
        for file_path in file_paths:
            if file_path not in self.image_list:
                try:
                    # 验证图片文件
                    with Image.open(file_path) as img:
                        img.verify()
                    
                    self.image_list.append(file_path)
                    filename = os.path.basename(file_path)
                    self.image_listbox.insert(tk.END, filename)
                    added_count += 1
                except Exception as e:
                    print(f"无法加载图片 {file_path}: {e}")
        
        if added_count > 0:
            # 选择第一张图片
            if len(self.image_list) == added_count:
                self.image_listbox.selection_set(0)
                self.on_image_select(None)
            
            messagebox.showinfo("成功", f"成功添加 {added_count} 张图片")
        else:
            messagebox.showwarning("警告", "没有添加任何有效的图片文件")
    
    def clear_images(self):
        """清空图片列表"""
        if self.image_list:
            result = messagebox.askyesno("确认", "确定要清空所有图片吗？")
            if result:
                self.image_list.clear()
                self.image_listbox.delete(0, tk.END)
                self.current_image = None
                self.preview_image = None
                self.watermarked_image = None
                self.preview_canvas.delete("all")
    
    def on_image_select(self, event):
        """图片选择事件"""
        selection = self.image_listbox.curselection()
        if selection:
            self.current_image_index = selection[0]
            self.load_current_image()
    
    def load_current_image(self):
        """加载当前选中的图片"""
        if 0 <= self.current_image_index < len(self.image_list):
            try:
                image_path = self.image_list[self.current_image_index]
                self.current_image = Image.open(image_path)
                self.update_preview()
            except Exception as e:
                messagebox.showerror("错误", f"无法加载图片: {e}")
    
    def update_preview(self):
        """更新预览"""
        if self.current_image is None:
            return
        
        try:
            # 创建水印图片
            watermarked = self.add_watermark_to_image(self.current_image.copy())
            
            # 调整图片大小以适应画布
            canvas_width = self.preview_canvas.winfo_width()
            canvas_height = self.preview_canvas.winfo_height()
            
            if canvas_width > 1 and canvas_height > 1:
                # 计算缩放比例
                img_width, img_height = watermarked.size
                scale_x = canvas_width / img_width
                scale_y = canvas_height / img_height
                scale = min(scale_x, scale_y, 1.0)  # 不放大图片
                
                new_width = int(img_width * scale)
                new_height = int(img_height * scale)
                
                # 调整图片大小
                preview_img = watermarked.resize((new_width, new_height), Image.Resampling.LANCZOS)
                
                # 转换为PhotoImage
                self.preview_image = ImageTk.PhotoImage(preview_img)
                
                # 清空画布并显示图片
                self.preview_canvas.delete("all")
                
                # 居中显示
                x = (canvas_width - new_width) // 2
                y = (canvas_height - new_height) // 2
                
                self.preview_canvas.create_image(
                    x, y,
                    anchor=tk.NW,
                    image=self.preview_image
                )
                
                # 保存水印图片用于导出
                self.watermarked_image = watermarked
                
        except Exception as e:
            print(f"预览更新错误: {e}")
            traceback.print_exc()
    
    def add_watermark_to_image(self, image):
        """为图片添加水印"""
        if image.mode != 'RGBA':
            image = image.convert('RGBA')
        
        # 创建透明图层用于水印
        watermark_layer = Image.new('RGBA', image.size, (0, 0, 0, 0))
        
        watermark_type = self.watermark_type.get()
        
        if watermark_type == "text":
            return self.add_text_watermark(image, watermark_layer)
        else:
            return self.add_image_watermark(image, watermark_layer)
    
    def add_text_watermark(self, image, watermark_layer):
        """添加文本水印"""
        draw = ImageDraw.Draw(watermark_layer)
        
        # 获取水印文本
        text = self.watermark_text.get()
        if not text:
            return image
        
        # 设置字体
        try:
            font_size = self.watermark_font_size.get()
            font_family = self.watermark_font_family.get()
            
            # 尝试加载系统字体
            try:
                watermark_font = ImageFont.truetype(font_family, font_size)
            except:
                # 如果失败，使用默认字体
                watermark_font = ImageFont.load_default()
        except:
            watermark_font = ImageFont.load_default()
        
        # 获取文本尺寸
        bbox = draw.textbbox((0, 0), text, font=watermark_font)
        text_width = bbox[2] - bbox[0]
        text_height = bbox[3] - bbox[1]
        
        # 计算位置
        img_width, img_height = image.size
        position = self.watermark_position.get()
        
        if position == "top_left":
            x, y = 20, 20
        elif position == "top_center":
            x, y = (img_width - text_width) // 2, 20
        elif position == "top_right":
            x, y = img_width - text_width - 20, 20
        elif position == "middle_left":
            x, y = 20, (img_height - text_height) // 2
        elif position == "center":
            x, y = (img_width - text_width) // 2, (img_height - text_height) // 2
        elif position == "middle_right":
            x, y = img_width - text_width - 20, (img_height - text_height) // 2
        elif position == "bottom_left":
            x, y = 20, img_height - text_height - 20
        elif position == "bottom_center":
            x, y = (img_width - text_width) // 2, img_height - text_height - 20
        else:  # bottom_right
            x, y = img_width - text_width - 20, img_height - text_height - 20
        
        # 应用手动调整的位置
        x += self.watermark_x
        y += self.watermark_y
        
        # 解析颜色
        color = self.watermark_color
        if color.startswith('#'):
            r = int(color[1:3], 16)
            g = int(color[3:5], 16)
            b = int(color[5:7], 16)
        else:
            r, g, b = 255, 255, 255
        
        # 计算透明度
        opacity = int(255 * self.watermark_opacity.get() / 100)
        text_color = (r, g, b, opacity)
        
        # 绘制阴影效果
        if self.watermark_shadow.get():
            shadow_color = (0, 0, 0, opacity // 2)
            draw.text((x + 2, y + 2), text, font=watermark_font, fill=shadow_color)
        
        # 绘制描边效果
        if self.watermark_outline.get():
            outline_color = (0, 0, 0, opacity)
            for dx in [-1, 0, 1]:
                for dy in [-1, 0, 1]:
                    if dx != 0 or dy != 0:
                        draw.text((x + dx, y + dy), text, font=watermark_font, fill=outline_color)
        
        # 绘制主文本
        draw.text((x, y), text, font=watermark_font, fill=text_color)
        
        # 应用旋转
        rotation = self.watermark_rotation.get()
        if rotation != 0:
            watermark_layer = watermark_layer.rotate(rotation, expand=False)
        
        # 合并图层
        result = Image.alpha_composite(image, watermark_layer)
        
        return result
    
    def add_image_watermark(self, image, watermark_layer):
        """添加图片水印"""
        if self.watermark_image is None:
            return image
        
        try:
            # 加载水印图片
            watermark_img = self.watermark_image.copy()
            
            # 确保水印图片有透明通道
            if watermark_img.mode != 'RGBA':
                watermark_img = watermark_img.convert('RGBA')
            
            # 应用缩放
            scale = self.watermark_image_scale.get()
            if scale != 1.0:
                new_width = int(watermark_img.width * scale)
                new_height = int(watermark_img.height * scale)
                watermark_img = watermark_img.resize((new_width, new_height), Image.Resampling.LANCZOS)
            
            # 计算位置
            img_width, img_height = image.size
            wm_width, wm_height = watermark_img.size
            position = self.watermark_position.get()
            
            if position == "top_left":
                x, y = 20, 20
            elif position == "top_center":
                x, y = (img_width - wm_width) // 2, 20
            elif position == "top_right":
                x, y = img_width - wm_width - 20, 20
            elif position == "middle_left":
                x, y = 20, (img_height - wm_height) // 2
            elif position == "center":
                x, y = (img_width - wm_width) // 2, (img_height - wm_height) // 2
            elif position == "middle_right":
                x, y = img_width - wm_width - 20, (img_height - wm_height) // 2
            elif position == "bottom_left":
                x, y = 20, img_height - wm_height - 20
            elif position == "bottom_center":
                x, y = (img_width - wm_width) // 2, img_height - wm_height - 20
            else:  # bottom_right
                x, y = img_width - wm_width - 20, img_height - wm_height - 20
            
            # 应用手动调整的位置
            x += self.watermark_x
            y += self.watermark_y
            
            # 应用透明度
            opacity = self.watermark_opacity.get() / 100.0
            if opacity < 1.0:
                # 创建透明度蒙版
                alpha = watermark_img.split()[-1]
                alpha = alpha.point(lambda p: int(p * opacity))
                watermark_img.putalpha(alpha)
            
            # 应用旋转
            rotation = self.watermark_rotation.get()
            if rotation != 0:
                watermark_img = watermark_img.rotate(rotation, expand=True)
                # 重新计算位置（旋转后尺寸可能改变）
                wm_width, wm_height = watermark_img.size
            
            # 确保水印在图片范围内
            x = max(0, min(x, img_width - wm_width))
            y = max(0, min(y, img_height - wm_height))
            
            # 粘贴水印到图层
            watermark_layer.paste(watermark_img, (x, y), watermark_img)
            
            # 合并图层
            result = Image.alpha_composite(image, watermark_layer)
            
            return result
            
        except Exception as e:
            print(f"添加图片水印失败: {e}")
            return image
    
    def choose_color(self):
        """选择水印颜色"""
        color = colorchooser.askcolor(
            color=self.watermark_color,
            title="选择水印颜色"
        )
        if color[1]:
            self.watermark_color = color[1]
            self.color_button.config(bg=self.watermark_color)
            self.update_preview()
    
    def choose_output_folder(self):
        """选择输出文件夹"""
        folder = filedialog.askdirectory(title="选择输出文件夹")
        if folder:
            self.output_folder.set(folder)
    
    def export_current_image(self):
        """导出当前图片"""
        if self.watermarked_image is None:
            messagebox.showwarning("警告", "没有可导出的图片")
            return
        
        if not self.output_folder.get():
            messagebox.showwarning("警告", "请选择输出文件夹")
            return
        
        try:
            self.export_single_image(self.current_image_index)
            messagebox.showinfo("成功", "图片导出成功")
        except Exception as e:
            messagebox.showerror("错误", f"导出失败: {e}")
    
    def export_all_images(self):
        """批量导出所有图片"""
        if not self.image_list:
            messagebox.showwarning("警告", "没有可导出的图片")
            return
        
        if not self.output_folder.get():
            messagebox.showwarning("警告", "请选择输出文件夹")
            return
        
        # 确认对话框
        result = messagebox.askyesno(
            "确认",
            f"确定要导出 {len(self.image_list)} 张图片吗？"
        )
        if not result:
            return
        
        # 创建进度窗口
        progress_window = tk.Toplevel(self.root)
        progress_window.title("导出进度")
        progress_window.geometry("400x150")
        progress_window.resizable(False, False)
        
        # 居中显示
        progress_window.transient(self.root)
        progress_window.grab_set()
        
        ttk.Label(progress_window, text="正在导出图片...").pack(pady=10)
        
        progress_var = tk.DoubleVar()
        progress_bar = ttk.Progressbar(
            progress_window,
            variable=progress_var,
            maximum=len(self.image_list)
        )
        progress_bar.pack(fill=tk.X, padx=20, pady=10)
        
        status_label = ttk.Label(progress_window, text="")
        status_label.pack(pady=5)
        
        # 在后台线程中执行导出
        def export_thread():
            success_count = 0
            error_count = 0
            
            for i, image_path in enumerate(self.image_list):
                try:
                    # 更新状态
                    filename = os.path.basename(image_path)
                    status_label.config(text=f"正在处理: {filename}")
                    progress_window.update()
                    
                    # 导出图片
                    self.export_single_image(i)
                    success_count += 1
                    
                except Exception as e:
                    print(f"导出图片 {image_path} 失败: {e}")
                    error_count += 1
                
                # 更新进度
                progress_var.set(i + 1)
                progress_window.update()
            
            # 关闭进度窗口
            progress_window.destroy()
            
            # 显示结果
            if error_count == 0:
                messagebox.showinfo("成功", f"成功导出 {success_count} 张图片")
            else:
                messagebox.showwarning(
                    "部分成功",
                    f"成功导出 {success_count} 张图片\n失败 {error_count} 张图片"
                )
        
        # 启动导出线程
        threading.Thread(target=export_thread, daemon=True).start()
    
    def export_single_image(self, image_index):
        """导出单张图片"""
        if image_index >= len(self.image_list):
            return
        
        image_path = self.image_list[image_index]
        
        # 加载原图
        original_image = Image.open(image_path)
        
        # 添加水印
        watermarked = self.add_watermark_to_image(original_image.copy())
        
        # 生成输出文件名
        original_name = os.path.splitext(os.path.basename(image_path))[0]
        
        if self.keep_original_name.get():
            output_name = original_name
        else:
            output_name = "watermarked"
        
        # 添加前缀和后缀
        prefix = self.filename_prefix.get()
        suffix = self.filename_suffix.get()
        output_name = f"{prefix}{output_name}{suffix}"
        
        # 确定输出格式和扩展名
        output_format = self.output_format.get()
        if output_format == "JPEG":
            ext = ".jpg"
            # 转换为RGB模式（JPEG不支持透明度）
            if watermarked.mode == 'RGBA':
                background = Image.new('RGB', watermarked.size, (255, 255, 255))
                background.paste(watermarked, mask=watermarked.split()[-1])
                watermarked = background
        else:
            ext = ".png"
        
        output_path = os.path.join(self.output_folder.get(), f"{output_name}{ext}")
        
        # 确保不覆盖现有文件
        counter = 1
        base_output_path = output_path
        while os.path.exists(output_path):
            name_part = os.path.splitext(base_output_path)[0]
            ext_part = os.path.splitext(base_output_path)[1]
            output_path = f"{name_part}_{counter}{ext_part}"
            counter += 1
        
        # 保存图片
        save_kwargs = {}
        if output_format == "JPEG":
            save_kwargs['quality'] = self.output_quality.get()
            save_kwargs['optimize'] = True
        
        watermarked.save(output_path, format=output_format, **save_kwargs)
    
    def save_template(self):
        """保存水印模板"""
        template = {
            'watermark_text': self.watermark_text.get(),
            'watermark_font_family': self.watermark_font_family.get(),
            'watermark_font_size': self.watermark_font_size.get(),
            'watermark_color': self.watermark_color,
            'watermark_opacity': self.watermark_opacity.get(),
            'watermark_position': self.watermark_position.get(),
            'watermark_rotation': self.watermark_rotation.get(),
            'watermark_shadow': self.watermark_shadow.get(),
            'watermark_outline': self.watermark_outline.get(),
            'output_format': self.output_format.get(),
            'output_quality': self.output_quality.get(),
            'filename_prefix': self.filename_prefix.get(),
            'filename_suffix': self.filename_suffix.get(),
            'keep_original_name': self.keep_original_name.get()
        }
        
        file_path = filedialog.asksaveasfilename(
            title="保存水印模板",
            defaultextension=".json",
            filetypes=[("JSON文件", "*.json"), ("所有文件", "*.*")]
        )
        
        if file_path:
            try:
                with open(file_path, 'w', encoding='utf-8') as f:
                    json.dump(template, f, ensure_ascii=False, indent=2)
                messagebox.showinfo("成功", "模板保存成功")
            except Exception as e:
                messagebox.showerror("错误", f"保存模板失败: {e}")
    
    def load_template(self):
        """加载水印模板"""
        file_path = filedialog.askopenfilename(
            title="加载水印模板",
            filetypes=[("JSON文件", "*.json"), ("所有文件", "*.*")]
        )
        
        if file_path:
            try:
                with open(file_path, 'r', encoding='utf-8') as f:
                    template = json.load(f)
                
                # 应用模板设置
                self.watermark_text.set(template.get('watermark_text', ''))
                self.watermark_font_family.set(template.get('watermark_font_family', 'Arial'))
                self.watermark_font_size.set(template.get('watermark_font_size', 36))
                self.watermark_color = template.get('watermark_color', '#FFFFFF')
                self.color_button.config(bg=self.watermark_color)
                self.watermark_opacity.set(template.get('watermark_opacity', 70))
                self.watermark_position.set(template.get('watermark_position', 'bottom_right'))
                self.watermark_rotation.set(template.get('watermark_rotation', 0))
                self.watermark_shadow.set(template.get('watermark_shadow', True))
                self.watermark_outline.set(template.get('watermark_outline', False))
                self.output_format.set(template.get('output_format', 'PNG'))
                self.output_quality.set(template.get('output_quality', 95))
                self.filename_prefix.set(template.get('filename_prefix', ''))
                self.filename_suffix.set(template.get('filename_suffix', '_watermarked'))
                self.keep_original_name.set(template.get('keep_original_name', True))
                
                # 更新预览
                self.update_preview()
                
                messagebox.showinfo("成功", "模板加载成功")
            except Exception as e:
                messagebox.showerror("错误", f"加载模板失败: {e}")
    
    def save_settings(self):
        """保存设置到配置文件"""
        settings = {
            'watermark_text': self.watermark_text.get(),
            'watermark_font_family': self.watermark_font_family.get(),
            'watermark_font_size': self.watermark_font_size.get(),
            'watermark_color': self.watermark_color,
            'watermark_opacity': self.watermark_opacity.get(),
            'watermark_position': self.watermark_position.get(),
            'watermark_rotation': self.watermark_rotation.get(),
            'watermark_shadow': self.watermark_shadow.get(),
            'watermark_outline': self.watermark_outline.get(),
            'output_format': self.output_format.get(),
            'output_quality': self.output_quality.get(),
            'output_folder': self.output_folder.get(),
            'filename_prefix': self.filename_prefix.get(),
            'filename_suffix': self.filename_suffix.get(),
            'keep_original_name': self.keep_original_name.get()
        }
        
        try:
            config_path = os.path.join(os.path.dirname(__file__), 'config.json')
            with open(config_path, 'w', encoding='utf-8') as f:
                json.dump(settings, f, ensure_ascii=False, indent=2)
        except Exception as e:
            print(f"保存设置失败: {e}")
    
    def load_settings(self):
        """从配置文件加载设置"""
        try:
            config_path = os.path.join(os.path.dirname(__file__), 'config.json')
            if os.path.exists(config_path):
                with open(config_path, 'r', encoding='utf-8') as f:
                    settings = json.load(f)
                
                # 应用设置
                self.watermark_text.set(settings.get('watermark_text', 'Sample Watermark'))
                self.watermark_font_family.set(settings.get('watermark_font_family', 'Arial'))
                self.watermark_font_size.set(settings.get('watermark_font_size', 36))
                self.watermark_color = settings.get('watermark_color', '#FFFFFF')
                self.color_button.config(bg=self.watermark_color)
                self.watermark_opacity.set(settings.get('watermark_opacity', 70))
                self.watermark_position.set(settings.get('watermark_position', 'bottom_right'))
                self.watermark_rotation.set(settings.get('watermark_rotation', 0))
                self.watermark_shadow.set(settings.get('watermark_shadow', True))
                self.watermark_outline.set(settings.get('watermark_outline', False))
                self.output_format.set(settings.get('output_format', 'PNG'))
                self.output_quality.set(settings.get('output_quality', 95))
                self.output_folder.set(settings.get('output_folder', ''))
                self.filename_prefix.set(settings.get('filename_prefix', ''))
                self.filename_suffix.set(settings.get('filename_suffix', '_watermarked'))
                self.keep_original_name.set(settings.get('keep_original_name', True))
        except Exception as e:
            print(f"加载设置失败: {e}")
    
    def on_drop(self, event):
        """处理拖拽文件事件"""
        files = self.root.tk.splitlist(event.data)
        image_files = []
        
        for file_path in files:
            if os.path.isfile(file_path):
                # 检查是否为支持的图片格式
                if any(file_path.lower().endswith(ext) for ext in self.supported_formats):
                    image_files.append(file_path)
            elif os.path.isdir(file_path):
                # 如果是文件夹，递归查找图片文件
                for root, dirs, files in os.walk(file_path):
                    for file in files:
                        if any(file.lower().endswith(ext) for ext in self.supported_formats):
                            image_files.append(os.path.join(root, file))
        
        if image_files:
            self.add_images(image_files)
    
    def on_canvas_click(self, event):
        """画布点击事件"""
        self.dragging = True
        self.drag_start_x = event.x
        self.drag_start_y = event.y
    
    def on_canvas_drag(self, event):
        """画布拖拽事件"""
        if self.dragging:
            dx = event.x - self.drag_start_x
            dy = event.y - self.drag_start_y
            self.watermark_x += dx
            self.watermark_y += dy
            self.drag_start_x = event.x
            self.drag_start_y = event.y
            self.update_preview()
    
    def on_canvas_release(self, event):
        """画布释放事件"""
        self.dragging = False
    
    def on_watermark_type_change(self):
        """水印类型切换事件"""
        watermark_type = self.watermark_type.get()
        if watermark_type == "text":
            self.text_frame.pack(fill=tk.X, padx=5, pady=5)
            self.image_frame.pack_forget()
        else:
            self.text_frame.pack_forget()
            self.image_frame.pack(fill=tk.X, padx=5, pady=5)
        self.update_preview()
    
    def choose_watermark_image(self):
        """选择水印图片"""
        filetypes = [
            ("图片文件", "*.png *.jpg *.jpeg *.bmp *.tiff *.tif"),
            ("PNG文件", "*.png"),
            ("JPEG文件", "*.jpg *.jpeg"),
            ("所有文件", "*.*")
        ]
        
        file_path = filedialog.askopenfilename(
            title="选择水印图片",
            filetypes=filetypes
        )
        
        if file_path:
            try:
                # 验证图片文件
                test_img = Image.open(file_path)
                test_img.verify()
                
                self.watermark_image_path.set(file_path)
                self.watermark_image = Image.open(file_path)
                self.update_preview()
            except Exception as e:
                messagebox.showerror("错误", f"无法加载水印图片: {e}")
    
    def __del__(self):
        """析构函数，保存设置"""
        try:
            self.save_settings()
        except:
            pass