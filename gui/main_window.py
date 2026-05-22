#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Fisherman - 主窗口

这是Fisherman应用程序的主界面，使用PyQt5实现，提供直观的用户交互。
"""

import logging
from PyQt5.QtWidgets import (
    QMainWindow, QWidget, QVBoxLayout,
    QTabWidget, QPushButton, QLabel, QGroupBox, QHBoxLayout
)
from PyQt5.QtCore import QTimer
from PyQt5.QtGui import QCloseEvent

from global_support.task_scheduler import task_scheduler
from recognition.screen_recognition import recognition_manager
from gui.tabs import (
    TrainingTab, TrainingResultTab, RecognitionTab,
    RecognitionTestTab, RecognitionActionTab,
    DisplacementTestTab, DisplacementActionTab,
    ImageLibraryTab, SettingsTab,
)

logger = logging.getLogger(__name__)


class MainWindow(QMainWindow):
    """Fisherman主窗口"""

    def __init__(self):
        """初始化主窗口"""
        super().__init__()

        # 初始化应用程序状态
        self.init_application()

        # 设置窗口属性
        self.setWindowTitle("Fisherman - 视觉自动化程序")
        self.setGeometry(100, 100, 1200, 800)
        self.setMinimumSize(800, 600)

        # 创建界面组件
        self.create_central_widget()
        self.create_menu_bar()
        self.create_status_bar()

        # 初始化定时器
        self.init_timers()

        logger.info("主窗口初始化完成")

    def init_application(self):
        """初始化应用程序"""
        # 连接到数据库并创建表
        from global_support.database import db_manager
        db_manager.connect()
        db_manager.create_tables()

        # 启动任务调度器
        task_scheduler.start_scheduler()

        logger.info("应用程序初始化完成")

    def create_central_widget(self):
        """创建中央部件"""
        central_widget = QWidget()
        self.setCentralWidget(central_widget)

        # 主布局
        main_layout = QVBoxLayout(central_widget)

        # 创建标签页组件
        self.tabs = QTabWidget()

        # 创建各个标签页
        self.training_tab = TrainingTab()
        self.tabs.addTab(self.training_tab, "训练")

        self.training_result_tab = TrainingResultTab()
        self.tabs.addTab(self.training_result_tab, "训练结果")

        self.image_library_tab = ImageLibraryTab()
        self.tabs.addTab(self.image_library_tab, "图库")

        # 识别标签页 - 保留原有的识别标签页（或可替换为新的两个标签页）
        # self.recognition_tab = RecognitionTab()
        # self.tabs.addTab(self.recognition_tab, "识别")

        # 新增：识别测试和识别操作标签页
        self.recognition_test_tab = RecognitionTestTab()
        self.tabs.addTab(self.recognition_test_tab, "识别测试")

        self.recognition_action_tab = RecognitionActionTab()
        self.tabs.addTab(self.recognition_action_tab, "识别操作")

        self.displacement_test_tab = DisplacementTestTab()
        self.tabs.addTab(self.displacement_test_tab, "位移测试")

        self.displacement_action_tab = DisplacementActionTab()
        self.tabs.addTab(self.displacement_action_tab, "位移操作")

        self.settings_tab = SettingsTab()
        self.tabs.addTab(self.settings_tab, "设置")

        main_layout.addWidget(self.tabs)

        # 创建日志显示区域
        self.create_log_display()

    def create_log_display(self):
        """创建日志显示区域"""
        log_widget = QGroupBox("日志")
        log_layout = QHBoxLayout(log_widget)

        # 运行日志按钮
        self.btn_log_viewer = QPushButton("运行日志")
        self.btn_log_viewer.clicked.connect(self.open_log_viewer)
        log_layout.addWidget(self.btn_log_viewer)
        log_layout.addStretch()

        # 将日志组件添加到主布局
        self.centralWidget().layout().addWidget(log_widget)

    def create_menu_bar(self):
        """创建菜单栏"""
        menubar = self.menuBar()

        # 文件菜单
        file_menu = menubar.addMenu("文件")

        # 帮助菜单
        help_menu = menubar.addMenu("帮助")

    def create_status_bar(self):
        """创建状态栏"""
        self.statusBar().showMessage("准备就绪")

        # 创建状态标签
        self.status_label = QLabel("状态: 就绪")
        self.statusBar().addPermanentWidget(self.status_label)

    def init_timers(self):
        """初始化定时器"""
        # 统计信息更新定时器
        self.stats_timer = QTimer()
        self.stats_timer.timeout.connect(self.update_recognition_stats)
        self.stats_timer.start(1000)  # 每秒更新一次

    def update_recognition_stats(self):
        """更新识别统计信息"""
        # 更新识别测试标签页统计
        if hasattr(self, 'recognition_test_tab'):
            self.recognition_test_tab._update_stats()

        # 更新识别操作标签页统计
        if hasattr(self, 'recognition_action_tab'):
            self.recognition_action_tab._update_stats()

        # 更新位移测试/操作标签页统计
        if hasattr(self, 'displacement_test_tab'):
            self.displacement_test_tab._update_stats()
        if hasattr(self, 'displacement_action_tab'):
            self.displacement_action_tab._update_stats()

    def open_log_viewer(self):
        """打开日志查看窗口"""
        try:
            from gui.log_viewer_dialog import LogViewerDialog

            dialog = LogViewerDialog(self)
            dialog.exec_()

        except Exception as e:
            logger.error(f"打开日志查看器失败: {str(e)}")
            from PyQt5.QtWidgets import QMessageBox
            QMessageBox.critical(self, "错误", f"打开日志查看器失败: {str(e)}")

    def closeEvent(self, event: QCloseEvent):
        """关闭事件处理"""
        logger.info("应用程序即将关闭")

        # 停止识别测试标签页的识别任务
        if hasattr(self, 'recognition_test_tab'):
            self.recognition_test_tab.close()

        # 停止识别操作标签页的识别任务
        if hasattr(self, 'recognition_action_tab'):
            self.recognition_action_tab.close()

        # 停止位移测试/操作标签页
        if hasattr(self, 'displacement_test_tab'):
            self.displacement_test_tab.close()
        if hasattr(self, 'displacement_action_tab'):
            self.displacement_action_tab.close()

        # 停止所有任务（原有的识别管理器）
        if recognition_manager.is_recognition_active():
            recognition_manager.stop_recognition_task()

        # 停止任务调度器
        task_scheduler.stop_scheduler()

        logger.info("应用程序已关闭")
        event.accept()
