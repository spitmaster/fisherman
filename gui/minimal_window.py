from PyQt5.QtWidgets import QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, QTabWidget, QGroupBox, QTextEdit, QSplitter
from PyQt5.QtCore import Qt, QTimer
from PyQt5.QtGui import QFont, QIcon
import sys
import logging

class MinimalWindow(QMainWindow):
    """
    不包含PyTorch依赖的最小化版本主窗口
    显示程序基本功能和错误信息
    """
    def __init__(self):
        super().__init__()
        
        # 初始化界面
        self.initUI()
        
        # 初始化定时器
        self.init_timers()
        
        # 记录程序启动信息
        logging.info("最小化版本程序启动成功")
    
    def initUI(self):
        """初始化用户界面"""
        self.setWindowTitle("Fisherman - 视觉自动化程序（最小化版本）")
        self.setGeometry(100, 100, 1000, 700)
        
        # 创建中央部件
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        
        # 创建垂直布局
        main_layout = QVBoxLayout(central_widget)
        
        # 创建标签页
        self.tabs = QTabWidget()
        
        # 创建信息标签页
        self.create_info_tab()
        
        # 创建日志标签页
        self.create_log_tab()
        
        main_layout.addWidget(self.tabs)
        
        # 创建状态栏
        self.statusBar().showMessage("准备就绪")
        
    def create_info_tab(self):
        """创建程序信息标签页"""
        info_widget = QWidget()
        info_layout = QVBoxLayout(info_widget)
        
        # 程序信息组
        info_group = QGroupBox("程序信息")
        info_group_layout = QVBoxLayout(info_group)
        
        # 程序名称和版本
        name_label = QLabel("Fisherman - 视觉自动化程序")
        name_label.setFont(QFont("Arial", 16, QFont.Bold))
        info_group_layout.addWidget(name_label)
        
        version_label = QLabel("版本: 1.0.0 (最小化版本)")
        info_group_layout.addWidget(version_label)
        
        info_layout.addWidget(info_group)
        
        # 系统状态组
        status_group = QGroupBox("系统状态")
        status_layout = QVBoxLayout(status_group)
        
        # PyTorch状态
        torch_status_label = QLabel("PyTorch库: ❌ 不可用")
        torch_status_label.setStyleSheet("color: red;")
        status_layout.addWidget(torch_status_label)
        
        status_layout.addWidget(QLabel("提示: 程序运行在最小化模式下，PyTorch相关功能不可用"))
        status_layout.addWidget(QLabel("请确保已正确安装Visual C++ Redistributable和PyTorch库"))
        
        status_layout.addWidget(QLabel())
        status_layout.addWidget(QLabel("最小化版本功能:"))
        status_layout.addWidget(QLabel("• 程序框架和界面显示"))
        status_layout.addWidget(QLabel("• 数据库操作和任务调度"))
        status_layout.addWidget(QLabel("• 日志记录"))
        
        status_layout.addWidget(QLabel())
        status_layout.addWidget(QLabel("不可用功能:"))
        status_layout.addWidget(QLabel("• 图像识别功能"))
        status_layout.addWidget(QLabel("• 模型训练功能"))
        status_layout.addWidget(QLabel("• 实时监控和自动化操作"))
        
        info_layout.addWidget(status_group)
        
        # 操作按钮组
        button_group = QGroupBox("操作")
        button_layout = QHBoxLayout(button_group)
        
        # 退出按钮
        exit_button = QPushButton("退出程序")
        exit_button.clicked.connect(self.close)
        button_layout.addWidget(exit_button)
        
        info_layout.addWidget(button_group)
        
        self.tabs.addTab(info_widget, "程序信息")
        
    def create_log_tab(self):
        """创建日志显示标签页"""
        log_widget = QWidget()
        log_layout = QVBoxLayout(log_widget)
        
        log_group = QGroupBox("程序日志")
        log_group_layout = QVBoxLayout(log_group)
        
        self.log_text = QTextEdit()
        self.log_text.setReadOnly(True)
        self.log_text.setMinimumHeight(300)
        
        log_group_layout.addWidget(self.log_text)
        
        log_layout.addWidget(log_group)
        
        self.tabs.addTab(log_widget, "程序日志")
        
    def init_timers(self):
        """初始化定时器"""
        # 日志更新定时器
        self.log_timer = QTimer()
        self.log_timer.timeout.connect(self.update_log)
        self.log_timer.start(500)
        
        # 系统状态更新定时器
        self.status_timer = QTimer()
        self.status_timer.timeout.connect(self.update_status)
        self.status_timer.start(1000)
        
    def update_log(self):
        """更新日志显示"""
        # 在实际应用中，这里会显示程序日志
        # 现在我们只显示一些基础信息
        if self.log_text.toPlainText() == "":
            self.log_text.append("=== Fisherman 程序启动 ===")
            self.log_text.append("程序运行在最小化模式下")
            self.log_text.append("PyTorch库不可用，请检查依赖安装")
            self.log_text.append("程序基础功能正常")
            
    def update_status(self):
        """更新状态栏信息"""
        self.statusBar().showMessage("程序运行在最小化模式下，PyTorch相关功能不可用")
        
    def closeEvent(self, event):
        """关闭事件"""
        logging.info("程序已关闭")
        event.accept()