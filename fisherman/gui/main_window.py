#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Fisherman - 主窗口组件

这是Fisherman应用程序的主界面，使用PyQt5实现，提供直观的用户交互。

主要功能：
- 标签页导航：训练、训练结果、识别、设置
- 实时状态显示
- 日志输出
- 全局操作按钮
"""

import os
import sys
import logging
from datetime import datetime
from PyQt5.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, 
    QTabWidget, QPushButton, QLabel, QTextEdit, QGroupBox, QSplitter
)
from PyQt5.QtCore import Qt, QTimer
from PyQt5.QtGui import QFont, QIcon

from fisherman.training.training_manager import training_manager
from fisherman.training.annotation_tool import annotation_manager
from fisherman.training_result.model_manager import model_manager
from fisherman.recognition.screen_recognition import recognition_manager
from fisherman.global_support.task_scheduler import task_scheduler

# 日志配置
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
        # 连接到数据库
        from fisherman.global_support.database import db_manager
        db_manager.connect()
        
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
        self.create_training_tab()
        self.create_training_result_tab()
        self.create_recognition_tab()
        self.create_settings_tab()
        
        main_layout.addWidget(self.tabs)
        
        # 创建日志显示区域
        self.create_log_display()
        
    def create_training_tab(self):
        """创建训练标签页"""
        training_widget = QWidget()
        training_layout = QVBoxLayout(training_widget)
        
        # 训练任务管理区域
        task_group = QGroupBox("训练任务管理")
        task_layout = QVBoxLayout(task_group)
        
        # 创建任务列表和操作按钮
        task_layout.addWidget(QLabel("训练任务列表"))
        
        training_layout.addWidget(task_group)
        
        # 标注区域
        annotation_group = QGroupBox("标注功能")
        annotation_layout = QVBoxLayout(annotation_group)
        
        # 创建标注操作按钮
        self.btn_start_annotation = QPushButton("开始标注")
        self.btn_start_annotation.clicked.connect(self.start_annotation)
        
        annotation_layout.addWidget(self.btn_start_annotation)
        
        training_layout.addWidget(annotation_group)
        
        # 训练区域
        training_group = QGroupBox("训练功能")
        training_layout_group = QVBoxLayout(training_group)
        
        # 创建训练操作按钮
        self.btn_start_training = QPushButton("开始训练")
        self.btn_start_training.clicked.connect(self.start_training)
        
        training_layout_group.addWidget(self.btn_start_training)
        
        training_layout.addWidget(training_group)
        
        self.tabs.addTab(training_widget, "训练")
        
    def create_training_result_tab(self):
        """创建训练结果管理标签页"""
        result_widget = QWidget()
        result_layout = QVBoxLayout(result_widget)
        
        # 模型管理区域
        model_group = QGroupBox("模型管理")
        model_layout = QVBoxLayout(model_group)
        
        # 创建模型列表和操作按钮
        model_layout.addWidget(QLabel("训练模型列表"))
        
        # 模型操作按钮
        btn_import_model = QPushButton("导入模型")
        btn_import_model.clicked.connect(self.import_model)
        
        btn_delete_model = QPushButton("删除模型")
        btn_delete_model.clicked.connect(self.delete_model)
        
        btn_compare_models = QPushButton("对比模型")
        btn_compare_models.clicked.connect(self.compare_models)
        
        btn_set_default = QPushButton("设置默认模型")
        btn_set_default.clicked.connect(self.set_default_model)
        
        button_layout = QHBoxLayout()
        button_layout.addWidget(btn_import_model)
        button_layout.addWidget(btn_delete_model)
        button_layout.addWidget(btn_compare_models)
        button_layout.addWidget(btn_set_default)
        
        model_layout.addLayout(button_layout)
        
        result_layout.addWidget(model_group)
        
        self.tabs.addTab(result_widget, "训练结果")
        
    def create_recognition_tab(self):
        """创建识别标签页"""
        recognition_widget = QWidget()
        recognition_layout = QVBoxLayout(recognition_widget)
        
        # 识别任务管理区域
        task_group = QGroupBox("识别任务管理")
        task_layout = QVBoxLayout(task_group)
        
        # 创建模型选择和操作按钮
        task_layout.addWidget(QLabel("选择模型："))
        
        self.btn_start_recognition = QPushButton("开始识别")
        self.btn_start_recognition.clicked.connect(self.start_recognition)
        
        self.btn_stop_recognition = QPushButton("停止识别")
        self.btn_stop_recognition.clicked.connect(self.stop_recognition)
        self.btn_stop_recognition.setEnabled(False)
        
        button_layout = QHBoxLayout()
        button_layout.addWidget(self.btn_start_recognition)
        button_layout.addWidget(self.btn_stop_recognition)
        
        task_layout.addLayout(button_layout)
        
        # 识别参数设置
        params_group = QGroupBox("识别参数")
        params_layout = QVBoxLayout(params_group)
        
        # 置信度阈值
        self.confidence_label = QLabel("置信度阈值: 0.7")
        params_layout.addWidget(self.confidence_label)
        
        # 点击冷却时间
        self.cooldown_label = QLabel("点击冷却时间: 5秒")
        params_layout.addWidget(self.cooldown_label)
        
        task_layout.addWidget(params_group)
        
        # 统计信息
        stats_group = QGroupBox("识别统计")
        stats_layout = QVBoxLayout(stats_group)
        
        self.stats_label = QLabel("识别次数: 0 | 点击次数: 0 | FPS: 0")
        stats_layout.addWidget(self.stats_label)
        
        task_layout.addWidget(stats_group)
        
        recognition_layout.addWidget(task_group)
        
        self.tabs.addTab(recognition_widget, "识别")
        
    def create_settings_tab(self):
        """创建设置标签页"""
        settings_widget = QWidget()
        settings_layout = QVBoxLayout(settings_widget)
        
        # 应用程序设置
        app_group = QGroupBox("应用程序设置")
        app_layout = QVBoxLayout(app_group)
        
        app_layout.addWidget(QLabel("设置内容"))
        
        settings_layout.addWidget(app_group)
        
        # 系统信息
        system_group = QGroupBox("系统信息")
        system_layout = QVBoxLayout(system_group)
        
        system_layout.addWidget(QLabel("系统信息显示"))
        
        settings_layout.addWidget(system_group)
        
        self.tabs.addTab(settings_widget, "设置")
        
    def create_log_display(self):
        """创建日志显示区域"""
        log_widget = QGroupBox("运行日志")
        log_layout = QVBoxLayout(log_widget)
        
        self.log_text = QTextEdit()
        self.log_text.setReadOnly(True)
        self.log_text.setMaximumHeight(200)
        
        log_layout.addWidget(self.log_text)
        
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
        
        # 日志更新定时器
        self.log_timer = QTimer()
        self.log_timer.timeout.connect(self.update_log)
        self.log_timer.start(500)  # 每0.5秒更新一次
        
    def start_annotation(self):
        """开始标注任务"""
        logger.info("开始标注任务")
        self.statusBar().showMessage("正在启动标注工具...")
        
        # 这里应该调用标注工具
        try:
            # 示例代码：获取任务ID
            task_id = 1  # 实际应用中应该从界面选择
            result = training_manager.start_annotation(task_id)
            
            if result:
                annotation_tool = annotation_manager.create_annotation_tool(
                    result["task_info"],
                    result["image_files"],
                    result["annotated_count"]
                )
                
                # 启动标注工具（这会阻塞主线程，需要在单独的线程中运行）
                from threading import Thread
                def run_annotation():
                    annotation_tool.start_annotation()
                
                thread = Thread(target=run_annotation, daemon=True)
                thread.start()
                
                self.statusBar().showMessage("标注工具已启动")
            else:
                self.statusBar().showMessage("无法启动标注工具")
                
        except Exception as e:
            logger.error(f"启动标注任务出错: {str(e)}")
            self.statusBar().showMessage(f"启动标注任务出错: {str(e)}")
            
    def start_training(self):
        """开始训练任务"""
        logger.info("开始训练任务")
        self.statusBar().showMessage("正在启动训练任务...")
        
        # 这里应该调用训练管理器
        try:
            task_id = 1  # 实际应用中应该从界面选择
            success = training_manager.start_training(task_id)
            
            if success:
                self.statusBar().showMessage("训练任务已启动")
            else:
                self.statusBar().showMessage("无法启动训练任务")
                
        except Exception as e:
            logger.error(f"启动训练任务出错: {str(e)}")
            self.statusBar().showMessage(f"启动训练任务出错: {str(e)}")
            
    def import_model(self):
        """导入模型文件"""
        logger.info("导入模型文件")
        self.statusBar().showMessage("正在导入模型...")
        
        # 这里应该打开文件对话框让用户选择模型文件
        from PyQt5.QtWidgets import QFileDialog
        
        file_path, _ = QFileDialog.getOpenFileName(
            self, 
            "导入模型文件", 
            "", 
            "模型文件 (*.pt)"
        )
        
        if file_path:
            try:
                result = model_manager.import_model(file_path)
                
                if result:
                    self.statusBar().showMessage(f"模型导入成功: {result['filename']}")
                else:
                    self.statusBar().showMessage("模型导入失败")
                    
            except Exception as e:
                logger.error(f"导入模型文件出错: {str(e)}")
                self.statusBar().showMessage(f"导入模型文件出错: {str(e)}")
        else:
            self.statusBar().showMessage("未选择模型文件")
            
    def delete_model(self):
        """删除模型文件"""
        logger.info("删除模型文件")
        self.statusBar().showMessage("正在删除模型...")
        
        # 这里应该实现删除模型的逻辑
        # 需要从界面选择要删除的模型
        
    def compare_models(self):
        """对比模型"""
        logger.info("对比模型")
        self.statusBar().showMessage("正在对比模型...")
        
        # 这里应该实现模型对比功能
        
    def set_default_model(self):
        """设置默认模型"""
        logger.info("设置默认模型")
        self.statusBar().showMessage("正在设置默认模型...")
        
        # 这里应该实现设置默认模型的逻辑
        
    def start_recognition(self):
        """开始识别任务"""
        logger.info("开始识别任务")
        self.statusBar().showMessage("正在启动识别任务...")
        
        try:
            # 这里应该从界面获取模型路径
            # 暂时使用默认模型
            model_info = model_manager.get_default_model()
            
            if model_info:
                # 启动识别任务
                recognition_manager.start_recognition_task(
                    model_info["path"],
                    confidence_threshold=0.7,
                    click_cooldown=5
                )
                
                # 更新按钮状态
                self.btn_start_recognition.setEnabled(False)
                self.btn_stop_recognition.setEnabled(True)
                
                self.statusBar().showMessage(f"识别任务已启动: {model_info['filename']}")
            else:
                self.statusBar().showMessage("未找到可用的模型")
                
        except Exception as e:
            logger.error(f"启动识别任务出错: {str(e)}")
            self.statusBar().showMessage(f"启动识别任务出错: {str(e)}")
            
    def stop_recognition(self):
        """停止识别任务"""
        logger.info("停止识别任务")
        self.statusBar().showMessage("正在停止识别任务...")
        
        try:
            recognition_manager.stop_recognition_task()
            
            # 更新按钮状态
            self.btn_start_recognition.setEnabled(True)
            self.btn_stop_recognition.setEnabled(False)
            
            self.statusBar().showMessage("识别任务已停止")
            
        except Exception as e:
            logger.error(f"停止识别任务出错: {str(e)}")
            self.statusBar().showMessage(f"停止识别任务出错: {str(e)}")
            
    def update_recognition_stats(self):
        """更新识别统计信息"""
        stats = recognition_manager.get_statistics()
        
        if stats["is_running"]:
            self.stats_label.setText(
                f"识别次数: {stats['recognitions_count']} | "
                f"点击次数: {stats['clicks_count']} | "
                f"FPS: {stats['fps']:.1f}"
            )
            
    def update_log(self):
        """更新日志显示"""
        # 这里应该实现日志内容的更新
        # 可以通过重定向日志输出到界面来实现
        pass
        
    def closeEvent(self, event):
        """关闭事件处理"""
        logger.info("应用程序即将关闭")
        
        # 停止所有任务
        if recognition_manager.is_recognition_active():
            recognition_manager.stop_recognition_task()
            
        # 停止任务调度器
        task_scheduler.stop_scheduler()
        
        logger.info("应用程序已关闭")
        event.accept()