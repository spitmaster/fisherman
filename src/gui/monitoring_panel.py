import tkinter as tk
from tkinter import ttk, filedialog, messagebox
from PIL import Image, ImageTk
import threading
import time
import cv2
import numpy as np

class MonitoringPanel:
    """监控模块面板"""
    
    def __init__(self, parent_frame):
        self.parent = parent_frame
        self.frame = ttk.Frame(parent_frame)
        
        # 监控管理器
        self.monitor = None
        
        
        # 当前预览图像
        self.current_preview = None
        self.is_monitoring = False
        
        # 事件记录
        self.event_records = []
        
        # 初始化UI
        self._init_ui()
    
    def _init_ui(self):
        """初始化UI"""
        # 创建主布局
        main_frame = ttk.Frame(self.frame)
        main_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        
        # 左侧面板 - 预览和控制
        left_panel = ttk.Frame(main_frame)
        left_panel.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        
        # 预览区域
        preview_frame = ttk.LabelFrame(left_panel, text="实时预览", padding=10)
        preview_frame.pack(fill=tk.BOTH, expand=True)
        
        self.preview_canvas = tk.Canvas(preview_frame, bg="black")
        self.preview_canvas.pack(fill=tk.BOTH, expand=True)
        
        # 控制按钮区域
        control_frame = ttk.Frame(left_panel)
        control_frame.pack(fill=tk.X, pady=(10, 0))
        
        self.start_button = ttk.Button(control_frame, text="开始监控", command=self._toggle_monitoring)
        self.start_button.pack(side=tk.LEFT, padx=5)
        
        ttk.Button(control_frame, text="截图", command=self._capture_screenshot).pack(side=tk.LEFT, padx=5)
        ttk.Button(control_frame, text="导出数据", command=self._export_data).pack(side=tk.LEFT, padx=5)
        
        # 右侧面板 - 参数配置和事件记录
        right_panel = ttk.Frame(main_frame)
        right_panel.pack(side=tk.RIGHT, fill=tk.Y, padx=(10, 0))
        
        # 参数配置区域
        config_frame = ttk.LabelFrame(right_panel, text="监控参数", padding=10)
        config_frame.pack(fill=tk.X, pady=(0, 10))
        
        # 监控范围选择
        ttk.Label(config_frame, text="监控范围:").pack(anchor=tk.W)
        self.capture_type_var = tk.StringVar(value="fullscreen")
        
        capture_frame = ttk.Frame(config_frame)
        capture_frame.pack(fill=tk.X, pady=(0, 5))
        
        ttk.Radiobutton(capture_frame, text="全屏", variable=self.capture_type_var, 
                       value="fullscreen").pack(side=tk.LEFT, padx=5)
        ttk.Radiobutton(capture_frame, text="窗口", variable=self.capture_type_var, 
                       value="window").pack(side=tk.LEFT, padx=5)
        
        # 窗口选择
        window_frame = ttk.Frame(config_frame)
        window_frame.pack(fill=tk.X, pady=(0, 5))
        
        ttk.Label(window_frame, text="窗口标题:").pack(side=tk.LEFT)
        self.window_entry = ttk.Entry(window_frame)
        self.window_entry.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=(5, 0))
        
        ttk.Button(window_frame, text="刷新", command=self._refresh_windows, width=8).pack(side=tk.RIGHT)
        
        # 模型选择
        ttk.Label(config_frame, text="模型文件:").pack(anchor=tk.W)
        model_frame = ttk.Frame(config_frame)
        model_frame.pack(fill=tk.X, pady=(0, 5))
        
        self.model_entry = ttk.Entry(model_frame)
        self.model_entry.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=(0, 5))
        
        ttk.Button(model_frame, text="浏览", command=self._browse_model, width=8).pack(side=tk.RIGHT)
        
        # 参数配置
        params_frame = ttk.Frame(config_frame)
        params_frame.pack(fill=tk.X)
        
        # 置信度阈值
        ttk.Label(params_frame, text="置信度阈值:").grid(row=0, column=0, sticky=tk.W, pady=2)
        self.confidence_var = tk.DoubleVar(value=0.5)
        ttk.Scale(params_frame, from_=0.1, to=1.0, variable=self.confidence_var, 
                 orient=tk.HORIZONTAL, length=150).grid(row=0, column=1, sticky=tk.W, padx=5)
        self.confidence_label = ttk.Label(params_frame, text="0.5")
        self.confidence_label.grid(row=0, column=2, sticky=tk.W)
        
        # 晃动阈值
        ttk.Label(params_frame, text="晃动阈值:").grid(row=1, column=0, sticky=tk.W, pady=2)
        self.shake_var = tk.DoubleVar(value=5.0)
        ttk.Scale(params_frame, from_=1.0, to=50.0, variable=self.shake_var, 
                 orient=tk.HORIZONTAL, length=150).grid(row=1, column=1, sticky=tk.W, padx=5)
        self.shake_label = ttk.Label(params_frame, text="5.0")
        self.shake_label.grid(row=1, column=2, sticky=tk.W)
        
        # 帧率
        ttk.Label(params_frame, text="帧率:").grid(row=2, column=0, sticky=tk.W, pady=2)
        self.fps_var = tk.IntVar(value=30)
        ttk.Scale(params_frame, from_=1, to=60, variable=self.fps_var, 
                 orient=tk.HORIZONTAL, length=150).grid(row=2, column=1, sticky=tk.W, padx=5)
        self.fps_label = ttk.Label(params_frame, text="30")
        self.fps_label.grid(row=2, column=2, sticky=tk.W)
        
        # 绑定变量变化
        self.confidence_var.trace("w", self._update_confidence_label)
        self.shake_var.trace("w", self._update_shake_label)
        self.fps_var.trace("w", self._update_fps_label)
        
        # 事件记录区域
        event_frame = ttk.LabelFrame(right_panel, text="晃动事件记录", padding=10)
        event_frame.pack(fill=tk.BOTH, expand=True)
        
        # 事件列表
        columns = ("时间", "物体", "位置", "状态")
        self.event_tree = ttk.Treeview(event_frame, columns=columns, show="headings", height=12)
        
        for col in columns:
            self.event_tree.heading(col, text=col)
            self.event_tree.column(col, width=80)
        
        self.event_tree.pack(fill=tk.BOTH, expand=True)
        
        # 滚动条
        scrollbar = ttk.Scrollbar(event_frame, orient=tk.VERTICAL, command=self.event_tree.yview)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        self.event_tree.configure(yscrollcommand=scrollbar.set)
        
        # 状态栏
        self.status_label = ttk.Label(self.frame, text="准备就绪", relief=tk.SUNKEN, anchor=tk.W)
        self.status_label.pack(side=tk.BOTTOM, fill=tk.X, padx=10, pady=(0, 10))
    
    def _update_confidence_label(self, *args):
        """更新置信度标签"""
        self.confidence_label.config(text=f"{self.confidence_var.get():.2f}")
    
    def _update_shake_label(self, *args):
        """更新晃动阈值标签"""
        self.shake_label.config(text=f"{self.shake_var.get():.1f}")
    
    def _update_fps_label(self, *args):
        """更新帧率标签"""
        self.fps_label.config(text=f"{self.fps_var.get()}")
    
    def _toggle_monitoring(self):
        """切换监控状态"""
        if self.is_monitoring:
            self._stop_monitoring()
        else:
            self._start_monitoring()
    
    def _start_monitoring(self):
        """开始监控"""
        if self.monitor is None:
            messagebox.showwarning("警告", "请先初始化监控管理器")
            return
        
        # 收集参数
        params = {
            'capture_type': self.capture_type_var.get(),
            'window_title': self.window_entry.get().strip(),
            'model_path': self.model_entry.get().strip(),
            'confidence_threshold': self.confidence_var.get(),
            'shake_threshold': self.shake_var.get(),
            'fps': self.fps_var.get()
        }
        
        # 验证参数
        if params['capture_type'] == 'window' and not params['window_title']:
            messagebox.showwarning("警告", "窗口捕获需要指定窗口标题")
            return
        
        if not params['model_path']:
            messagebox.showwarning("警告", "请选择模型文件")
            return
        
        # 设置参数并开始监控
        try:
            self.monitor.set_params(params)
            self.monitor.set_preview_callback(self._update_preview)
            self.monitor.set_callback(self._handle_monitor_callback)
            self.monitor.start_monitoring()
            
            self.is_monitoring = True
            self.start_button.config(text="停止监控")
            self.status_label.config(text="监控中...")
            
        except Exception as e:
            messagebox.showerror("错误", f"启动监控失败: {e}")
    
    def _stop_monitoring(self):
        """停止监控"""
        if self.monitor:
            self.monitor.stop_monitoring()
        
        self.is_monitoring = False
        self.start_button.config(text="开始监控")
        self.status_label.config(text="监控已停止")
    
    def _update_preview(self, frame):
        """更新预览图像"""
        try:
            # 转换OpenCV图像为PIL图像
            frame_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            image = Image.fromarray(frame_rgb)
            
            # 调整图像大小以适应画布
            canvas_width = self.preview_canvas.winfo_width()
            canvas_height = self.preview_canvas.winfo_height()
            
            if canvas_width > 1 and canvas_height > 1:
                # 计算缩放比例
                img_width, img_height = image.size
                width_ratio = canvas_width / img_width
                height_ratio = canvas_height / img_height
                scale = min(width_ratio, height_ratio) * 0.95  # 保留5%边距
                
                new_width = int(img_width * scale)
                new_height = int(img_height * scale)
                
                if new_width > 0 and new_height > 0:
                    image = image.resize((new_width, new_height), Image.Resampling.LANCZOS)
            
            # 显示图像
            self.photo = ImageTk.PhotoImage(image)
            self.preview_canvas.delete("all")
            self.preview_canvas.create_image(
                canvas_width // 2, canvas_height // 2,
                image=self.photo, anchor=tk.CENTER
            )
            
        except Exception as e:
            print(f"更新预览失败: {e}")
    
    def _handle_monitor_callback(self, data):
        """处理监控回调"""
        status = data.get('status', '')
        
        if status == 'monitoring_update':
            # 更新状态栏
            frame_count = data.get('frame_count', 0)
            detection_count = data.get('detection_count', 0)
            shake_count = data.get('shake_count', 0)
            
            self.status_label.config(
                text=f"帧: {frame_count} | 检测: {detection_count} | 晃动: {shake_count}"
            )
            
            # 添加晃动事件到列表
            detections = data.get('detections', [])
            for detection in detections:
                if detection.get('shake_status', False):
                    self._add_event_record(detection, data.get('timestamp', time.time()))
        
        elif status == 'monitoring_error':
            error = data.get('error', '未知错误')
            self.status_label.config(text=f"错误: {error}")
    
    def _add_event_record(self, detection, timestamp):
        """添加事件记录"""
        class_name = detection.get('class_name', '未知')
        confidence = detection.get('confidence', 0)
        bbox = detection.get('bbox', [])
        tracking_id = detection.get('tracking_id', -1)
        
        # 格式化时间
        time_str = time.strftime("%H:%M:%S", time.localtime(timestamp))
        
        # 计算位置
        if len(bbox) == 4:
            x1, y1, x2, y2 = bbox
            position = f"({int(x1)},{int(y1)})"
        else:
            position = "未知"
        
        # 添加到树形视图
        item_id = self.event_tree.insert("", 0, values=(
            time_str,
            f"{class_name} (ID:{tracking_id})",
            position,
            f"晃动 {confidence:.2f}"
        ))
        
        # 限制记录数量
        items = self.event_tree.get_children()
        if len(items) > 100:
            self.event_tree.delete(items[-1])
        
        # 保存到事件记录列表
        self.event_records.append({
            'timestamp': timestamp,
            'detection': detection,
            'item_id': item_id
        })
    
    def _capture_screenshot(self):
        """截图"""
        if not self.is_monitoring:
            messagebox.showwarning("警告", "请先开始监控")
            return
        
        # 这里需要实现截图逻辑
        messagebox.showinfo("截图", "截图功能开发中")
    
    def _export_data(self):
        """导出数据"""
        if not self.monitor:
            messagebox.showwarning("警告", "监控管理器未初始化")
            return
        
        # 选择导出格式
        file_path = filedialog.asksaveasfilename(
            title="导出数据",
            defaultextension=".csv",
            filetypes=[("CSV文件", "*.csv"), ("JSON文件", "*.json")]
        )
        
        if file_path:
            try:
                if file_path.endswith(".csv"):
                    self.monitor.export_data('csv', file_path)
                else:
                    self.monitor.export_data('json', file_path)
                
                messagebox.showinfo("导出", f"数据已导出到: {file_path}")
            except Exception as e:
                messagebox.showerror("错误", f"导出失败: {e}")
    
    def _refresh_windows(self):
        """刷新窗口列表"""
        if self.monitor:
            windows = self.monitor.get_window_list()
            
            # 这里可以显示窗口列表供用户选择
            if windows:
                window_titles = [w['title'] for w in windows[:20]]  # 只显示前20个窗口
                messagebox.showinfo("窗口列表", "\n".join(window_titles))
            else:
                messagebox.showinfo("窗口列表", "没有找到窗口")
        else:
            messagebox.showwarning("警告", "监控管理器未初始化")
    
    def _browse_model(self):
        """浏览模型文件"""
        file_path = filedialog.askopenfilename(
            title="选择模型文件",
            filetypes=[("模型文件", "*.pt *.pth *.onnx")]
        )
        
        if file_path:
            self.model_entry.delete(0, tk.END)
            self.model_entry.insert(0, file_path)
    
    def set_monitor(self, monitor):
        """设置监控管理器"""
        self.monitor = monitor
    
    def get_frame(self):
        """获取面板框架"""
        return self.frame