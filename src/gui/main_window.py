import tkinter as tk
from tkinter import ttk
from gui.training_panel import TrainingPanel
from gui.monitoring_panel import MonitoringPanel
from monitoring.monitor import Monitor

class MainWindow:
    def __init__(self, root):
        self.root = root
        self.root.title("Fisherman - 物体晃动监控系统")
        self.root.geometry("1200x800")
        
        # 创建监控管理器
        self.monitor = Monitor()
        
        # 创建标签页控件
        self.notebook = ttk.Notebook(root)
        self.notebook.pack(fill=tk.BOTH, expand=True)
        
        # 训练模块标签页
        self.training_panel = TrainingPanel(self.notebook)
        self.notebook.add(self.training_panel.get_frame(), text="训练模块")
        
        # 使用模块标签页
        self.monitoring_panel = MonitoringPanel(self.notebook)
        self.monitoring_panel.set_monitor(self.monitor)
        self.notebook.add(self.monitoring_panel.get_frame(), text="使用模块")
        
        # 绑定窗口关闭事件
        self.root.protocol("WM_DELETE_WINDOW", self._on_closing)
    
    def _on_closing(self):
        """窗口关闭时的处理"""
        # 停止监控
        if self.monitor:
            self.monitor.stop_monitoring()
        
        # 关闭窗口
        self.root.destroy()