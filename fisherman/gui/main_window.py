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
        
        # 任务操作按钮
        task_button_layout = QHBoxLayout()
        self.btn_create_task = QPushButton("创建任务")
        self.btn_create_task.clicked.connect(self.create_training_task)
        self.btn_delete_task = QPushButton("删除任务")
        self.btn_delete_task.clicked.connect(self.delete_training_task)
        self.btn_edit_task = QPushButton("编辑任务")
        self.btn_edit_task.clicked.connect(self.edit_training_task)
        task_button_layout.addWidget(self.btn_create_task)
        task_button_layout.addWidget(self.btn_edit_task)
        task_button_layout.addWidget(self.btn_delete_task)
        task_layout.addLayout(task_button_layout)
        
        # 任务列表
        from PyQt5.QtWidgets import QListWidget
        self.task_list_widget = QListWidget()
        self.task_list_widget.itemClicked.connect(self.on_task_selected)
        task_layout.addWidget(self.task_list_widget)
        
        # 任务信息显示
        task_info_layout = QHBoxLayout()
        self.label_task_name = QLabel("任务名称:")
        self.label_task_status = QLabel("状态:")
        self.label_task_images = QLabel("图片数量:")
        self.label_task_annotated = QLabel("已标注:")
        self.label_task_progress = QLabel("进度:")
        task_info_layout.addWidget(self.label_task_name)
        task_info_layout.addWidget(self.label_task_status)
        task_info_layout.addWidget(self.label_task_images)
        task_info_layout.addWidget(self.label_task_annotated)
        task_info_layout.addWidget(self.label_task_progress)
        task_layout.addLayout(task_info_layout)
        
        training_layout.addWidget(task_group)
        
        # 训练集管理区域
        dataset_group = QGroupBox("训练集管理")
        dataset_layout = QVBoxLayout(dataset_group)
        
        # 训练集操作按钮
        dataset_button_layout = QHBoxLayout()
        self.btn_import_images = QPushButton("导入图片")
        self.btn_import_images.clicked.connect(self.import_images)
        self.btn_clear_dataset = QPushButton("清空数据集")
        self.btn_clear_dataset.clicked.connect(self.clear_dataset)
        dataset_button_layout.addWidget(self.btn_import_images)
        dataset_button_layout.addWidget(self.btn_clear_dataset)
        dataset_layout.addLayout(dataset_button_layout)
        
        # 数据集信息
        dataset_info_layout = QHBoxLayout()
        self.label_total_images = QLabel("总图片数: 0")
        self.label_annotated_count = QLabel("已标注: 0")
        self.label_unannotated_count = QLabel("未标注: 0")
        self.label_annotation_progress = QLabel("标注进度: 0%")
        dataset_info_layout.addWidget(self.label_total_images)
        dataset_info_layout.addWidget(self.label_annotated_count)
        dataset_info_layout.addWidget(self.label_unannotated_count)
        dataset_info_layout.addWidget(self.label_annotation_progress)
        dataset_layout.addLayout(dataset_info_layout)
        
        training_layout.addWidget(dataset_group)
        
        # 标注区域
        annotation_group = QGroupBox("标注功能")
        annotation_layout = QVBoxLayout(annotation_group)
        
        # 创建标注操作按钮
        annotation_button_layout = QHBoxLayout()
        self.btn_start_annotation = QPushButton("开始标注")
        self.btn_start_annotation.clicked.connect(self.start_annotation)
        self.btn_start_annotation.setEnabled(False)
        self.btn_view_annotations = QPushButton("查看标注")
        self.btn_view_annotations.clicked.connect(self.view_annotations)
        self.btn_view_annotations.setEnabled(False)
        annotation_button_layout.addWidget(self.btn_start_annotation)
        annotation_button_layout.addWidget(self.btn_view_annotations)
        annotation_layout.addLayout(annotation_button_layout)
        
        # 标注快捷键说明
        annotation_hint = QLabel("快捷键: S 保存 / D 下一张 / A 回退 / Q 退出")
        annotation_layout.addWidget(annotation_hint)
        
        training_layout.addWidget(annotation_group)
        
        # 训练区域
        training_group = QGroupBox("训练功能")
        training_layout_group = QVBoxLayout(training_group)
        
        # 训练参数设置
        training_params_layout = QHBoxLayout()
        self.label_epochs = QLabel("训练轮数:")
        from PyQt5.QtWidgets import QSpinBox
        self.spin_epochs = QSpinBox()
        self.spin_epochs.setMinimum(1)
        self.spin_epochs.setMaximum(200)
        self.spin_epochs.setValue(50)
        
        self.label_batch_size = QLabel("批次大小:")
        self.spin_batch_size = QSpinBox()
        self.spin_batch_size.setMinimum(1)
        self.spin_batch_size.setMaximum(32)
        self.spin_batch_size.setValue(8)
        
        training_params_layout.addWidget(self.label_epochs)
        training_params_layout.addWidget(self.spin_epochs)
        training_params_layout.addWidget(self.label_batch_size)
        training_params_layout.addWidget(self.spin_batch_size)
        training_layout_group.addLayout(training_params_layout)
        
        # 训练操作按钮
        training_button_layout = QHBoxLayout()
        self.btn_start_training = QPushButton("开始训练")
        self.btn_start_training.clicked.connect(self.start_training)
        self.btn_start_training.setEnabled(False)
        self.btn_stop_training = QPushButton("停止训练")
        self.btn_stop_training.clicked.connect(self.stop_training)
        self.btn_stop_training.setEnabled(False)
        training_button_layout.addWidget(self.btn_start_training)
        training_button_layout.addWidget(self.btn_stop_training)
        training_layout_group.addLayout(training_button_layout)
        
        training_layout.addWidget(training_group)
        
        # 加载任务列表
        self.load_training_tasks()
        
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
        
        # PyTorch可用性检查
        pytorch_status = "可用"
        device_info = "CPU"
        try:
            import torch
            pytorch_status = f"可用 (版本: {torch.__version__})"
            if torch.cuda.is_available():
                device_info = f"GPU (CUDA: {torch.version.cuda})"
            else:
                device_info = "CPU"
        except Exception as e:
            pytorch_status = f"不可用: {str(e)}"
        
        system_layout.addWidget(QLabel(f"PyTorch库: {pytorch_status}"))
        system_layout.addWidget(QLabel(f"计算设备: {device_info}"))
        
        # 显示当前使用的PyTorch设备信息
        if device_info == "CPU":
            system_layout.addWidget(QLabel("当前使用CPU进行训练和推理"))
        
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
        
    def load_training_tasks(self):
        """加载训练任务列表"""
        self.task_list_widget.clear()
        
        tasks = training_manager.get_all_training_tasks()
        for task in tasks:
            from PyQt5.QtWidgets import QListWidgetItem
            item = QListWidgetItem(f"{task['task_name']} ({task['status']})")
            item.setData(Qt.UserRole, task['id'])
            self.task_list_widget.addItem(item)
        
        logger.info(f"加载训练任务成功: 共 {len(tasks)} 个任务")
        
    def on_task_selected(self, item):
        """任务选择事件"""
        task_id = item.data(Qt.UserRole)
        task_info = training_manager.get_training_task_status(task_id)
        
        if task_info:
            self.label_task_name.setText(f"任务名称: {task_info['name']}")
            self.label_task_status.setText(f"状态: {task_info['status']}")
            self.label_task_images.setText(f"图片数量: {task_info['total_images']}")
            self.label_task_annotated.setText(f"已标注: {task_info['annotated_images']}")
            self.label_task_progress.setText(f"进度: {task_info['annotation_progress']}%")
            
            # 更新数据集信息
            dataset_info = training_manager.get_dataset_info(task_id)
            if dataset_info:
                self.label_total_images.setText(f"总图片数: {dataset_info['total_images']}")
                self.label_annotated_count.setText(f"已标注: {dataset_info['annotated_images']}")
                self.label_unannotated_count.setText(f"未标注: {dataset_info['unannotated_images']}")
                progress = 0
                if dataset_info['total_images'] > 0:
                    progress = (dataset_info['annotated_images'] / dataset_info['total_images']) * 100
                self.label_annotation_progress.setText(f"标注进度: {progress:.1f}%")
            
            # 启用相应的按钮
            self.btn_start_annotation.setEnabled(task_info['total_images'] > 0)
            self.btn_view_annotations.setEnabled(task_info['annotated_images'] > 0)
            self.btn_start_training.setEnabled(task_info['annotated_images'] > 0)
            
            # 更新训练参数
            self.spin_epochs.setValue(task_info['epochs'])
            self.spin_batch_size.setValue(task_info['batch_size'])
            
    def create_training_task(self):
        """创建训练任务"""
        logger.info("创建训练任务")
        self.statusBar().showMessage("正在创建训练任务...")
        
        # 打开对话框让用户输入任务信息
        from PyQt5.QtWidgets import QDialog, QFormLayout, QLineEdit, QTextEdit, QDialogButtonBox
        dialog = QDialog(self)
        dialog.setWindowTitle("创建训练任务")
        
        layout = QFormLayout(dialog)
        
        task_name_edit = QLineEdit()
        task_name_edit.setPlaceholderText("请输入任务名称")
        layout.addRow("任务名称:", task_name_edit)
        
        task_description_edit = QTextEdit()
        task_description_edit.setPlaceholderText("请输入任务描述")
        layout.addRow("任务描述:", task_description_edit)
        
        button_box = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        button_box.accepted.connect(dialog.accept)
        button_box.rejected.connect(dialog.reject)
        layout.addWidget(button_box)
        
        if dialog.exec_() == QDialog.Accepted:
            task_name = task_name_edit.text().strip()
            task_description = task_description_edit.toPlainText().strip()
            
            if task_name:
                try:
                    task_id = training_manager.create_training_task(
                        task_name,
                        task_description,
                        epochs=self.spin_epochs.value(),
                        batch_size=self.spin_batch_size.value()
                    )
                    
                    if task_id:
                        self.load_training_tasks()
                        self.statusBar().showMessage(f"训练任务创建成功: {task_name}")
                    else:
                        self.statusBar().showMessage("训练任务创建失败")
                        
                except Exception as e:
                    logger.error(f"创建训练任务出错: {str(e)}")
                    self.statusBar().showMessage(f"创建训练任务出错: {str(e)}")
            else:
                self.statusBar().showMessage("任务名称不能为空")
                
    def edit_training_task(self):
        """编辑训练任务"""
        logger.info("编辑训练任务")
        
        current_item = self.task_list_widget.currentItem()
        if not current_item:
            self.statusBar().showMessage("请先选择要编辑的任务")
            return
            
        task_id = current_item.data(Qt.UserRole)
        task_info = training_manager.get_training_task_by_id(task_id)
        
        if not task_info:
            self.statusBar().showMessage("任务不存在")
            return
            
        # 打开对话框让用户编辑任务信息
        from PyQt5.QtWidgets import QDialog, QFormLayout, QLineEdit, QTextEdit, QDialogButtonBox
        dialog = QDialog(self)
        dialog.setWindowTitle("编辑训练任务")
        
        layout = QFormLayout(dialog)
        
        task_name_edit = QLineEdit(task_info['task_name'])
        layout.addRow("任务名称:", task_name_edit)
        
        task_description_edit = QTextEdit(task_info['task_description'])
        layout.addRow("任务描述:", task_description_edit)
        
        button_box = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        button_box.accepted.connect(dialog.accept)
        button_box.rejected.connect(dialog.reject)
        layout.addWidget(button_box)
        
        if dialog.exec_() == QDialog.Accepted:
            task_name = task_name_edit.text().strip()
            task_description = task_description_edit.toPlainText().strip()
            
            if task_name:
                try:
                    success = training_manager.update_training_task(
                        task_id,
                        task_name,
                        task_description,
                        self.spin_epochs.value(),
                        self.spin_batch_size.value()
                    )
                    
                    if success:
                        self.load_training_tasks()
                        self.statusBar().showMessage("训练任务更新成功")
                    else:
                        self.statusBar().showMessage("训练任务更新失败")
                        
                except Exception as e:
                    logger.error(f"编辑训练任务出错: {str(e)}")
                    self.statusBar().showMessage(f"编辑训练任务出错: {str(e)}")
            else:
                self.statusBar().showMessage("任务名称不能为空")
                
    def delete_training_task(self):
        """删除训练任务"""
        logger.info("删除训练任务")
        
        current_item = self.task_list_widget.currentItem()
        if not current_item:
            self.statusBar().showMessage("请先选择要删除的任务")
            return
            
        task_id = current_item.data(Qt.UserRole)
        
        # 确认删除
        from PyQt5.QtWidgets import QMessageBox
        reply = QMessageBox.question(
            self,
            "确认删除",
            "确定要删除选中的训练任务吗？此操作不可恢复。",
            QMessageBox.Yes | QMessageBox.No
        )
        
        if reply == QMessageBox.Yes:
            try:
                success = training_manager.delete_training_task(task_id)
                
                if success:
                    self.load_training_tasks()
                    # 重置显示信息
                    self.label_task_name.setText("任务名称:")
                    self.label_task_status.setText("状态:")
                    self.label_task_images.setText("图片数量:")
                    self.label_task_annotated.setText("已标注:")
                    self.label_task_progress.setText("进度:")
                    self.statusBar().showMessage("训练任务删除成功")
                else:
                    self.statusBar().showMessage("训练任务删除失败")
                    
            except Exception as e:
                logger.error(f"删除训练任务出错: {str(e)}")
                self.statusBar().showMessage(f"删除训练任务出错: {str(e)}")
                
    def import_images(self):
        """导入图片"""
        logger.info("导入图片")
        
        current_item = self.task_list_widget.currentItem()
        if not current_item:
            self.statusBar().showMessage("请先选择要导入图片的任务")
            return
            
        task_id = current_item.data(Qt.UserRole)
        
        from PyQt5.QtWidgets import QFileDialog
        file_paths, _ = QFileDialog.getOpenFileNames(
            self,
            "选择图片文件",
            "",
            "图片文件 (*.jpg *.jpeg *.png *.bmp)"
        )
        
        if file_paths:
            try:
                imported_count = training_manager.import_images(task_id, file_paths)
                self.statusBar().showMessage(f"图片导入成功: 共 {imported_count} 张")
                
                # 更新任务列表和信息
                self.load_training_tasks()
                # 重新选择当前任务以更新显示
                for i in range(self.task_list_widget.count()):
                    item = self.task_list_widget.item(i)
                    if item.data(Qt.UserRole) == task_id:
                        self.task_list_widget.setCurrentItem(item)
                        self.on_task_selected(item)
                        break
                        
            except Exception as e:
                logger.error(f"导入图片出错: {str(e)}")
                self.statusBar().showMessage(f"导入图片出错: {str(e)}")
                
    def clear_dataset(self):
        """清空数据集"""
        logger.info("清空数据集")
        
        current_item = self.task_list_widget.currentItem()
        if not current_item:
            self.statusBar().showMessage("请先选择要清空数据集的任务")
            return
            
        task_id = current_item.data(Qt.UserRole)
        
        # 确认清空
        from PyQt5.QtWidgets import QMessageBox
        reply = QMessageBox.question(
            self,
            "确认清空",
            "确定要清空该任务的数据集吗？此操作不可恢复。",
            QMessageBox.Yes | QMessageBox.No
        )
        
        if reply == QMessageBox.Yes:
            try:
                task_info = training_manager.get_training_task_by_id(task_id)
                if task_info and task_info['dataset_path']:
                    # 删除数据集目录下的所有文件
                    import os
                    import shutil
                    image_dir = os.path.join(os.path.dirname(task_info['dataset_path']), "images", "train")
                    label_dir = os.path.join(os.path.dirname(task_info['dataset_path']), "labels", "train")
                    
                    if os.path.exists(image_dir):
                        shutil.rmtree(image_dir)
                        os.makedirs(image_dir)
                        
                    if os.path.exists(label_dir):
                        shutil.rmtree(label_dir)
                        os.makedirs(label_dir)
                        
                    self.statusBar().showMessage("数据集清空成功")
                    # 更新显示
                    self.load_training_tasks()
                    for i in range(self.task_list_widget.count()):
                        item = self.task_list_widget.item(i)
                        if item.data(Qt.UserRole) == task_id:
                            self.task_list_widget.setCurrentItem(item)
                            self.on_task_selected(item)
                            break
                            
            except Exception as e:
                logger.error(f"清空数据集出错: {str(e)}")
                self.statusBar().showMessage(f"清空数据集出错: {str(e)}")
                
    def start_annotation(self):
        """开始标注任务"""
        logger.info("开始标注任务")
        self.statusBar().showMessage("正在启动标注工具...")
        
        current_item = self.task_list_widget.currentItem()
        if not current_item:
            self.statusBar().showMessage("请先选择要标注的任务")
            return
            
        task_id = current_item.data(Qt.UserRole)
        
        try:
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
            
    def view_annotations(self):
        """查看标注"""
        logger.info("查看标注")
        self.statusBar().showMessage("查看标注功能开发中...")
            
    def start_training(self):
        """开始训练任务"""
        logger.info("开始训练任务")
        self.statusBar().showMessage("正在启动训练任务...")
        
        current_item = self.task_list_widget.currentItem()
        if not current_item:
            self.statusBar().showMessage("请先选择要训练的任务")
            return
            
        task_id = current_item.data(Qt.UserRole)
        
        try:
            # 更新任务训练参数
            task_info = training_manager.get_training_task_by_id(task_id)
            if task_info:
                training_manager.update_training_task(
                    task_id,
                    task_info['task_name'],
                    task_info['task_description'],
                    self.spin_epochs.value(),
                    self.spin_batch_size.value()
                )
                
            success = training_manager.start_training(task_id)
            
            if success:
                self.btn_start_training.setEnabled(False)
                self.btn_stop_training.setEnabled(True)
                self.statusBar().showMessage("训练任务已启动")
            else:
                self.statusBar().showMessage("无法启动训练任务")
                
        except Exception as e:
            logger.error(f"启动训练任务出错: {str(e)}")
            self.statusBar().showMessage(f"启动训练任务出错: {str(e)}")
            
    def stop_training(self):
        """停止训练任务"""
        logger.info("停止训练任务")
        self.statusBar().showMessage("正在停止训练任务...")
        
        current_item = self.task_list_widget.currentItem()
        if not current_item:
            self.statusBar().showMessage("请先选择要停止的训练任务")
            return
            
        task_id = current_item.data(Qt.UserRole)
        
        try:
            # 这里应该调用训练管理器的停止方法
            # 暂时使用简单的实现
            from fisherman.global_support.task_scheduler import task_scheduler
            task_scheduler.stop_task(task_id)
            
            self.btn_start_training.setEnabled(True)
            self.btn_stop_training.setEnabled(False)
            self.statusBar().showMessage("训练任务已停止")
            
        except Exception as e:
            logger.error(f"停止训练任务出错: {str(e)}")
            self.statusBar().showMessage(f"停止训练任务出错: {str(e)}")
            
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