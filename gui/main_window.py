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
    QTabWidget, QPushButton, QLabel, QTextEdit, QGroupBox, QSplitter,
    QMessageBox, QDialog
)
from PyQt5.QtCore import Qt, QTimer
from PyQt5.QtGui import QFont, QIcon, QColor

from training.training_manager import training_manager
from training.annotation_tool import annotation_manager
from training_result.model_manager import model_manager
from recognition.screen_recognition import recognition_manager
from global_support.task_scheduler import task_scheduler

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
        from global_support.database import db_manager
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

        # 训练集管理区域
        dataset_group = QGroupBox("训练集管理")
        dataset_layout = QVBoxLayout(dataset_group)

        # 训练集操作按钮
        dataset_button_layout = QHBoxLayout()
        self.btn_create_dataset = QPushButton("新建训练集")
        self.btn_create_dataset.clicked.connect(self.create_dataset)
        dataset_button_layout.addWidget(self.btn_create_dataset)
        dataset_layout.addLayout(dataset_button_layout)

        # 训练集表格（带按钮列）
        from PyQt5.QtWidgets import QTableWidget, QTableWidgetItem, QHeaderView, QAbstractItemView
        self.dataset_table = QTableWidget()
        self.dataset_table.setColumnCount(6)
        self.dataset_table.setHorizontalHeaderLabels(["名称", "备注", "总图片数", "已标注", "标注进度", "操作"])
        # 名称列调窄
        self.dataset_table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeToContents)
        self.dataset_table.horizontalHeader().setSectionResizeMode(1, QHeaderView.Stretch)
        self.dataset_table.horizontalHeader().setSectionResizeMode(2, QHeaderView.ResizeToContents)
        self.dataset_table.horizontalHeader().setSectionResizeMode(3, QHeaderView.ResizeToContents)
        self.dataset_table.horizontalHeader().setSectionResizeMode(4, QHeaderView.ResizeToContents)
        self.dataset_table.horizontalHeader().setSectionResizeMode(5, QHeaderView.ResizeToContents)
        self.dataset_table.setSelectionBehavior(QTableWidget.SelectRows)
        self.dataset_table.setSelectionMode(QTableWidget.SingleSelection)
        self.dataset_table.setSelectionMode(QAbstractItemView.SingleSelection)
        self.dataset_table.verticalHeader().setVisible(False)
        self.dataset_table.cellDoubleClicked.connect(self.on_dataset_double_clicked)

        # 表格占满整个区域
        dataset_layout.addWidget(self.dataset_table)

        training_layout.addWidget(dataset_group)
        training_layout.setStretch(0, 1)  # 训练集组拉伸占满空间

        # 加载训练集列表
        self.load_datasets()

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
        
        # 日志更新定时器
        self.log_timer = QTimer()
        self.log_timer.timeout.connect(self.update_log)
        self.log_timer.start(500)  # 每0.5秒更新一次
        
    def load_datasets(self):
        """加载训练集列表"""
        self.dataset_table.setRowCount(0)

        from training.task.dataset_manager import DatasetManager
        from training.dataset_path_manager import DatasetPathManager
        from PyQt5.QtWidgets import QTableWidgetItem, QPushButton, QWidget

        dataset_manager = DatasetManager()
        datasets = dataset_manager.list_all_datasets()

        self.datasets_info = {}  # 保存训练集信息（名称 -> 备注）

        for dataset_info in datasets:
            dataset_path = dataset_info.get("dataset_path", "")
            dataset_name = dataset_path.split(os.sep)[-1]
            has_weights = dataset_info.get("has_weights", False)

            total_images = dataset_info.get('total_images', 0)
            annotated_images = dataset_info.get('annotated_images', 0)
            progress = dataset_info.get('annotation_progress', 0)

            row = self.dataset_table.rowCount()
            self.dataset_table.insertRow(row)

            # 名称
            item_name = QTableWidgetItem(dataset_name)
            self.dataset_table.setItem(row, 0, item_name)

            # 备注（从文件中读取）
            remark = self._load_dataset_remark(dataset_name)
            item_remark = QTableWidgetItem(remark)
            self.dataset_table.setItem(row, 1, item_remark)
            self.datasets_info[dataset_name] = remark

            # 总图片数
            item_total = QTableWidgetItem(str(total_images))
            item_total.setTextAlignment(Qt.AlignCenter)
            self.dataset_table.setItem(row, 2, item_total)

            # 已标注
            item_annotated = QTableWidgetItem(str(annotated_images))
            item_annotated.setTextAlignment(Qt.AlignCenter)
            self.dataset_table.setItem(row, 3, item_annotated)

            # 标注进度
            item_progress = QTableWidgetItem(f"{progress:.1f}%")
            item_progress.setTextAlignment(Qt.AlignCenter)
            self.dataset_table.setItem(row, 4, item_progress)

            # 操作按钮列
            btn_widget = QWidget()
            btn_layout = QHBoxLayout(btn_widget)
            btn_layout.setContentsMargins(4, 2, 4, 2)

            btn_open = QPushButton("打开详情")
            btn_open.setStyleSheet("padding: 4px 8px;")
            # 使用闭包绑定行号
            btn_open.clicked.connect(lambda checked, r=row: self.open_dataset_detail(r))

            btn_delete = QPushButton("删除")
            btn_delete.setStyleSheet("padding: 4px 8px; background-color: #f44336; color: white;")
            btn_delete.clicked.connect(lambda checked, r=row: self.delete_dataset_by_row(r))

            btn_layout.addWidget(btn_open)
            btn_layout.addWidget(btn_delete)
            btn_layout.addStretch()
            self.dataset_table.setCellWidget(row, 5, btn_widget)

            # 如果有训练好的模型，高亮显示
            if has_weights:
                for col in range(5):
                    self.dataset_table.item(row, col).setBackground(QColor(144, 238, 144, 50))

        logger.info(f"加载训练集成功: 共 {len(datasets)} 个训练集")

    def _load_dataset_remark(self, dataset_name: str) -> str:
        """从文件加载训练集备注"""
        try:
            from training.dataset_path_manager import DatasetPathManager

            remark_file = DatasetPathManager.get_dataset_path(dataset_name) / "remark.txt"
            if remark_file.exists():
                with open(remark_file, 'r', encoding='utf-8') as f:
                    return f.read().strip()
            return ""
        except:
            return ""

    def _save_dataset_remark(self, dataset_name: str, remark: str) -> bool:
        """保存训练集备注到文件"""
        try:
            from training.dataset_path_manager import DatasetPathManager

            remark_file = DatasetPathManager.get_dataset_path(dataset_name) / "remark.txt"
            with open(remark_file, 'w', encoding='utf-8') as f:
                f.write(remark)
            return True
        except Exception as e:
            logger.error(f"保存备注失败: {str(e)}")
            return False

    def on_dataset_selected(self, item):
        """训练集选择事件（已废弃，保留用于兼容）"""
        pass

    def create_dataset(self):
        """创建新训练集"""
        logger.info("创建训练集")
        self.statusBar().showMessage("正在创建训练集...")

        from PyQt5.QtWidgets import QDialog, QFormLayout, QLineEdit, QTextEdit, QDialogButtonBox
        dialog = QDialog(self)
        dialog.setWindowTitle("创建训练集")

        layout = QFormLayout(dialog)

        dataset_name_edit = QLineEdit()
        dataset_name_edit.setPlaceholderText("请输入训练集名称")
        layout.addRow("训练集名称:", dataset_name_edit)

        dataset_remark_edit = QTextEdit()
        dataset_remark_edit.setPlaceholderText("请输入备注信息（可选）")
        dataset_remark_edit.setMaximumHeight(80)
        layout.addRow("备注:", dataset_remark_edit)

        button_box = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        button_box.accepted.connect(dialog.accept)
        button_box.rejected.connect(dialog.reject)
        layout.addWidget(button_box)

        if dialog.exec_() == QDialog.Accepted:
            dataset_name = dataset_name_edit.text().strip()
            remark = dataset_remark_edit.toPlainText().strip()

            if dataset_name:
                try:
                    from training.dataset_path_manager import DatasetPathManager

                    # 检查训练集是否已存在
                    if DatasetPathManager.dataset_exists(dataset_name):
                        QMessageBox.warning(self, "警告", f"训练集 '{dataset_name}' 已存在!")
                        return

                    # 创建训练集目录结构
                    DatasetPathManager.create_dataset_dirs(dataset_name)

                    # 保存备注
                    if remark:
                        self._save_dataset_remark(dataset_name, remark)

                    self.load_datasets()
                    self.statusBar().showMessage(f"训练集创建成功: {dataset_name}")

                except Exception as e:
                    logger.error(f"创建训练集出错: {str(e)}")
                    self.statusBar().showMessage(f"创建训练集出错: {str(e)}")
            else:
                self.statusBar().showMessage("训练集名称不能为空")

    def delete_dataset(self):
        """删除训练集"""
        logger.info("删除训练集")

        # 获取选中行
        current_row = self.dataset_table.currentRow()
        if current_row < 0:
            self.statusBar().showMessage("请先选择要删除的训练集")
            return

        item_name = self.dataset_table.item(current_row, 0)
        if not item_name:
            return

        dataset_name = item_name.text()

        # 确认删除
        from PyQt5.QtWidgets import QMessageBox
        reply = QMessageBox.question(
            self,
            "确认删除",
            f"确定要删除训练集 '{dataset_name}' 吗？此操作将删除所有图片和标注，不可恢复。",
            QMessageBox.Yes | QMessageBox.No
        )

        if reply == QMessageBox.Yes:
            try:
                from training.dataset_path_manager import DatasetPathManager
                import shutil

                dataset_path = DatasetPathManager.get_dataset_path(dataset_name)
                if dataset_path.exists():
                    shutil.rmtree(dataset_path)

                self.load_datasets()
                self.statusBar().showMessage(f"训练集 '{dataset_name}' 删除成功")

            except Exception as e:
                logger.error(f"删除训练集出错: {str(e)}")
                self.statusBar().showMessage(f"删除训练集出错: {str(e)}")

    def import_images_to_dataset(self):
        """导入图片到训练集（已废弃，保留用于兼容）"""
        pass

    def load_training_tasks(self):
        """加载训练任务列表（已废弃，保留用于兼容）"""
        self.dataset_list_widget.clear()

        from training.task.dataset_manager import DatasetManager
        dataset_manager = DatasetManager()
        datasets = dataset_manager.list_all_datasets()

        for dataset_info in datasets:
            from PyQt5.QtWidgets import QListWidgetItem
            name = dataset_info.get("dataset_path", "").split(os.sep)[-1]
            item = QListWidgetItem(name)
            item.setData(Qt.UserRole, name)
            self.dataset_list_widget.addItem(item)

        logger.info(f"加载训练集成功: 共 {len(datasets)} 个训练集")

    def on_task_selected(self, item):
        """任务选择事件（已废弃，保留用于兼容）"""
        pass
            
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

    def start_annotation(self):
        """开始标注任务（已废弃，保留用于兼容）"""
        pass

    def view_annotations(self):
        """查看标注（已废弃，保留用于兼容）"""
        pass

    def start_training(self):
        """开始训练任务（已废弃，保留用于兼容）"""
        pass

    def stop_training(self):
        """停止训练任务"""
        logger.info("停止训练任务")
        self.statusBar().showMessage("停止训练功能暂未实现")
            
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

    def on_dataset_double_clicked(self, row: int, column: int):
        """双击训练集打开详情"""
        self.open_dataset_detail(row)

    def open_dataset_detail_dialog(self, dataset_name: str, remark: str):
        """打开训练集详情对话框"""
        try:
            from gui.dataset_detail_dialog import DatasetDetailDialog

            dialog = DatasetDetailDialog(dataset_name, remark, self)
            dialog.annotation_completed.connect(self.load_datasets)

            dialog.exec_()

            # 关闭对话框后刷新列表，因为备注可能已经被修改
            self.load_datasets()

        except Exception as e:
            logger.error(f"打开训练集详情失败: {str(e)}")
            QMessageBox.critical(self, "错误", f"打开训练集详情失败: {str(e)}")

    def open_log_viewer(self):
        """打开日志查看窗口"""
        try:
            from gui.log_viewer_dialog import LogViewerDialog

            dialog = LogViewerDialog(self)
            dialog.exec_()

        except Exception as e:
            logger.error(f"打开日志查看器失败: {str(e)}")
            QMessageBox.critical(self, "错误", f"打开日志查看器失败: {str(e)}")

    def open_dataset_detail(self, row: int):
        """根据行号打开训练集详情"""
        try:
            item_name = self.dataset_table.item(row, 0)
            item_remark = self.dataset_table.item(row, 1)

            if item_name:
                dataset_name = item_name.text()
                remark = item_remark.text() if item_remark else ""
                self.open_dataset_detail_dialog(dataset_name, remark)
        except Exception as e:
            logger.error(f"打开训练集详情失败: {str(e)}")
            QMessageBox.critical(self, "错误", f"打开训练集详情失败: {str(e)}")

    def delete_dataset_by_row(self, row: int):
        """根据行号删除训练集"""
        try:
            item_name = self.dataset_table.item(row, 0)
            if not item_name:
                return

            dataset_name = item_name.text()

            # 二次确认
            reply = QMessageBox.question(
                self,
                "确认删除",
                f"确定要删除训练集 '{dataset_name}' 吗？\n此操作将删除所有图片和标注，不可恢复。",
                QMessageBox.Yes | QMessageBox.No,
                QMessageBox.No
            )

            if reply == QMessageBox.Yes:
                try:
                    from training.dataset_path_manager import DatasetPathManager
                    import shutil

                    dataset_path = DatasetPathManager.get_dataset_path(dataset_name)
                    if dataset_path.exists():
                        shutil.rmtree(dataset_path)

                    self.load_datasets()
                    self.statusBar().showMessage(f"训练集 '{dataset_name}' 删除成功")

                except Exception as e:
                    logger.error(f"删除训练集出错: {str(e)}")
                    self.statusBar().showMessage(f"删除训练集出错: {str(e)}")
                    QMessageBox.critical(self, "错误", f"删除训练集出错: {str(e)}")

        except Exception as e:
            logger.error(f"删除训练集失败: {str(e)}")
            QMessageBox.critical(self, "错误", f"删除训练集失败: {str(e)}")