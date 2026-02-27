#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
训练集详情对话框

提供训练集的详细管理功能：导入图片、标注、训练等。
"""

import os
import logging
from typing import Dict, Any
from PyQt5.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QFormLayout, QPushButton,
    QLabel, QListWidget, QGroupBox, QTabWidget, QWidget,
    QMessageBox, QSpinBox, QComboBox, QTextEdit, QDialogButtonBox
)
from PyQt5.QtCore import Qt, pyqtSignal
from PyQt5.QtGui import QFont

from training.task.dataset_manager import DatasetManager
from training.dataset_path_manager import DatasetPathManager
from training.training.executor import TrainingExecutor

logger = logging.getLogger(__name__)


class DatasetDetailDialog(QDialog):
    """训练集详情对话框"""

    annotation_completed = pyqtSignal()  # 标注完成信号

    def __init__(self, dataset_name: str, dataset_remark: str = "", parent=None):
        super().__init__(parent)
        # 移除问号帮助按钮
        self.setWindowFlags(self.windowFlags() & ~Qt.WindowContextHelpButtonHint)
        self.dataset_name = dataset_name
        self.dataset_remark = dataset_remark
        self.dataset_manager = DatasetManager()
        self.training_executor = TrainingExecutor()

        # 保存状态
        self._last_saved_remark = dataset_remark

        self.init_ui()
        self.load_dataset_info()

        # 安装事件过滤器来监听焦点事件
        self.edit_remark.installEventFilter(self)

    def accept(self):
        """关闭对话框前立即保存备注"""
        # 保存当前备注
        current_remark = self.edit_remark.toPlainText().strip()
        if current_remark != self._last_saved_remark:
            self._save_remark_to_file(current_remark)
            self._last_saved_remark = current_remark
            self.dataset_remark = current_remark
            logger.info(f"备注已保存: {self.dataset_name}")

        # 调用父类的 accept 方法关闭对话框
        super().accept()

    def init_ui(self):
        """初始化界面"""
        self.setWindowTitle(f"训练集详情 - {self.dataset_name}")
        self.setMinimumSize(900, 600)

        layout = QVBoxLayout(self)

        # 训练集信息
        info_group = QGroupBox("训练集信息")
        info_layout = QFormLayout()

        self.label_name = QLabel(self.dataset_name)
        self.label_name.setFont(QFont("Arial", 12, QFont.Bold))

        self.edit_remark = QTextEdit()
        self.edit_remark.setPlaceholderText("输入备注信息...")
        self.edit_remark.setMaximumHeight(60)
        self.edit_remark.setText(self.dataset_remark)
        # 添加提示文本，说明会自动保存
        self.edit_remark.setToolTip("修改后失去焦点或关闭对话框时自动保存")

        info_layout.addRow("训练集名称:", self.label_name)
        info_layout.addRow("备注:", self.edit_remark)

        info_group.setLayout(info_layout)
        layout.addWidget(info_group)

        # 数据集统计信息
        stats_group = QGroupBox("数据统计")
        stats_layout = QHBoxLayout()

        self.label_total_images = QLabel("总图片数: 0")
        self.label_annotated_count = QLabel("已标注: 0")
        self.label_unannotated_count = QLabel("未标注: 0")
        self.label_annotation_progress = QLabel("标注进度: 0%")

        # 设置字体
        for label in [self.label_total_images, self.label_annotated_count,
                     self.label_unannotated_count, self.label_annotation_progress]:
            label.setFont(QFont("Arial", 10))

        stats_layout.addWidget(self.label_total_images)
        stats_layout.addWidget(self.label_annotated_count)
        stats_layout.addWidget(self.label_unannotated_count)
        stats_layout.addWidget(self.label_annotation_progress)

        stats_group.setLayout(stats_layout)
        layout.addWidget(stats_group)

        # 功能标签页
        tabs = QTabWidget()

        # 图片管理标签页
        images_tab = self.create_images_tab()
        tabs.addTab(images_tab, "图片管理")

        # 标注管理标签页
        annotation_tab = self.create_annotation_tab()
        tabs.addTab(annotation_tab, "标注管理")

        # 训练设置标签页
        training_tab = self.create_training_tab()
        tabs.addTab(training_tab, "训练设置")

        layout.addWidget(tabs)

        # 底部按钮
        button_layout = QHBoxLayout()
        button_layout.addStretch()

        self.btn_close = QPushButton("关闭")
        self.btn_close.clicked.connect(self.accept)

        button_layout.addWidget(self.btn_close)
        layout.addLayout(button_layout)

    def create_images_tab(self) -> QWidget:
        """创建图片管理标签页"""
        widget = QWidget()
        layout = QVBoxLayout(widget)

        # 图片列表
        self.image_list = QListWidget()
        layout.addWidget(self.image_list)

        # 操作按钮
        btn_layout = QHBoxLayout()
        btn_import = QPushButton("导入图片")
        btn_import.clicked.connect(self.import_images)

        btn_refresh = QPushButton("刷新列表")
        btn_refresh.clicked.connect(self.load_dataset_info)

        btn_delete_all = QPushButton("清空所有图片")
        btn_delete_all.clicked.connect(self.delete_all_images)
        btn_delete_all.setStyleSheet("background-color: #f44336; color: white;")

        btn_layout.addWidget(btn_import)
        btn_layout.addWidget(btn_refresh)
        btn_layout.addWidget(btn_delete_all)
        layout.addLayout(btn_layout)

        return widget

    def create_annotation_tab(self) -> QWidget:
        """创建标注管理标签页"""
        widget = QWidget()
        layout = QVBoxLayout(widget)

        # 标注操作说明
        hint = QLabel("点击下方按钮打开标注工具进行图片标注。标注数据将自动保存。")
        hint.setWordWrap(True)
        layout.addWidget(hint)

        # 操作按钮
        btn_layout = QHBoxLayout()
        btn_start = QPushButton("开始标注")
        btn_start.setStyleSheet("background-color: #4CAF50; color: white; font-size: 14px;")
        btn_start.clicked.connect(self.start_annotation)

        btn_layout.addStretch()
        btn_layout.addWidget(btn_start)
        layout.addLayout(btn_layout)

        return widget

    def create_training_tab(self) -> QWidget:
        """创建训练设置标签页"""
        widget = QWidget()
        layout = QVBoxLayout(widget)

        # 训练参数设置
        params_group = QGroupBox("训练参数")
        params_layout = QFormLayout()

        self.spin_epochs = QSpinBox()
        self.spin_epochs.setMinimum(1)
        self.spin_epochs.setMaximum(500)
        self.spin_epochs.setValue(50)
        self.spin_epochs.setPrefix("轮数: ")

        self.spin_batch_size = QSpinBox()
        self.spin_batch_size.setMinimum(1)
        self.spin_batch_size.setMaximum(64)
        self.spin_batch_size.setValue(8)
        self.spin_batch_size.setPrefix("批次: ")

        self.spin_img_size = QSpinBox()
        self.spin_img_size.setMinimum(320)
        self.spin_img_size.setMaximum(1280)
        self.spin_img_size.setValue(640)
        self.spin_img_size.setSingleStep(32)
        self.spin_img_size.setPrefix("尺寸: ")

        self.combo_model_type = QComboBox()
        self.combo_model_type.addItems([
            "yolov8n.pt (最快)",
            "yolov8s.pt (快速)",
            "yolov8m.pt (平衡)",
            "yolov8l.pt (精确)"
        ])
        self.combo_model_type.setCurrentIndex(0)

        params_layout.addRow(self.spin_epochs)
        params_layout.addRow(self.spin_batch_size)
        params_layout.addRow(self.spin_img_size)
        params_layout.addRow("模型类型:", self.combo_model_type)

        params_group.setLayout(params_layout)
        layout.addWidget(params_group)

        # 开始训练按钮
        btn_layout = QHBoxLayout()
        btn_layout.addStretch()

        self.btn_start_training = QPushButton("开始训练")
        self.btn_start_training.setStyleSheet("background-color: #2196F3; color: white; font-size: 14px;")
        self.btn_start_training.clicked.connect(self.start_training)
        self.btn_start_training.setEnabled(False)

        btn_layout.addWidget(self.btn_start_training)
        layout.addLayout(btn_layout)

        # 训练日志
        log_group = QGroupBox("训练日志")
        log_layout = QVBoxLayout()
        self.log_text = QTextEdit()
        self.log_text.setReadOnly(True)
        self.log_text.setMaximumHeight(200)
        log_layout.addWidget(self.log_text)
        log_group.setLayout(log_layout)
        layout.addWidget(log_group)

        return widget

    def load_dataset_info(self):
        """加载训练集信息"""
        try:
            dataset_info = self.dataset_manager.get_dataset_info_by_name(self.dataset_name)

            if dataset_info:
                total_images = dataset_info['total_images']
                annotated_images = dataset_info['annotated_images']
                unannotated = total_images - annotated_images
                progress = dataset_info['annotation_progress']

                self.label_total_images.setText(f"总图片数: {total_images}")
                self.label_annotated_count.setText(f"已标注: {annotated_images}")
                self.label_unannotated_count.setText(f"未标注: {unannotated}")
                self.label_annotation_progress.setText(f"标注进度: {progress:.1f}%")

                # 启用/禁用开始训练按钮
                self.btn_start_training.setEnabled(annotated_images > 0)

            # 加载图片列表
            self.image_list.clear()
            image_files = self.dataset_manager.get_image_list_by_name(self.dataset_name)
            for img_file in image_files:
                self.image_list.addItem(img_file)

            logger.info(f"加载训练集信息成功: {self.dataset_name}")

        except Exception as e:
            logger.error(f"加载训练集信息失败: {str(e)}")
            QMessageBox.warning(self, "错误", f"加载训练集信息失败: {str(e)}")

    def import_images(self):
        """导入图片"""
        try:
            from PyQt5.QtWidgets import QFileDialog

            file_paths, _ = QFileDialog.getOpenFileNames(
                self,
                "选择图片文件",
                "",
                "图片文件 (*.jpg *.jpeg *.png *.bmp)"
            )

            if file_paths:
                imported_count = self.dataset_manager.import_images_to_dataset(
                    self.dataset_name, file_paths
                )

                self.log_text.append(f"图片导入成功: 共 {imported_count} 张\n")
                self.load_dataset_info()

                QMessageBox.information(self, "成功", f"成功导入 {imported_count} 张图片")

        except Exception as e:
            logger.error(f"导入图片失败: {str(e)}")
            QMessageBox.critical(self, "错误", f"导入图片失败: {str(e)}")

    def delete_all_images(self):
        """清空所有图片"""
        reply = QMessageBox.question(
            self,
            "确认删除",
            f"确定要清空训练集 '{self.dataset_name}' 的所有图片吗？此操作不可恢复。",
            QMessageBox.Yes | QMessageBox.No
        )

        if reply == QMessageBox.Yes:
            try:
                import shutil
                from pathlib import Path

                images_dir = DatasetPathManager.get_images_path(self.dataset_name)
                labels_dir = DatasetPathManager.get_labels_path(self.dataset_name)

                # 清空图片目录
                if images_dir.exists():
                    for f in images_dir.iterdir():
                        if f.is_file():
                            f.unlink()

                # 清空标注目录
                if labels_dir.exists():
                    for f in labels_dir.iterdir():
                        if f.is_file():
                            f.unlink()

                self.log_text.append("已清空所有图片和标注\n")
                self.load_dataset_info()

                QMessageBox.information(self, "成功", "已清空所有图片和标注")

            except Exception as e:
                logger.error(f"清空图片失败: {str(e)}")
                QMessageBox.critical(self, "错误", f"清空图片失败: {str(e)}")

    def start_annotation(self):
        """开始标注"""
        try:
            from gui.annotation_window import open_annotation_window

            open_annotation_window(self.dataset_name, self)
            self.annotation_completed.emit()

        except Exception as e:
            logger.error(f"启动标注工具失败: {str(e)}")
            QMessageBox.critical(self, "错误", f"启动标注工具失败: {str(e)}")

    def start_training(self):
        """开始训练"""
        try:
            # 确认开始训练
            reply = QMessageBox.question(
                self,
                "确认训练",
                f"确定要开始训练 '{self.dataset_name}' 吗？训练过程可能需要较长时间。",
                QMessageBox.Yes | QMessageBox.No
            )

            if reply != QMessageBox.Yes:
                return

            # 获取模型类型
            model_type = self.combo_model_type.currentText().split()[0]

            # 构建训练参数
            training_params = {
                "epochs": self.spin_epochs.value(),
                "batch_size": self.spin_batch_size.value(),
                "image_size": self.spin_img_size.value(),
                "model_type": model_type
            }

            self.log_text.append(f"开始训练: {self.dataset_name}\n")
            self.log_text.append(f"训练参数: epochs={training_params['epochs']}, "
                             f"batch={training_params['batch_size']}, "
                             f"imgsz={training_params['image_size']}, "
                             f"model={model_type}\n")
            self.log_text.append("-" * 50 + "\n")

            self.btn_start_training.setEnabled(False)

            # 在单独线程中执行训练
            from threading import Thread

            def run_training():
                try:
                    result = self.training_executor.train_by_name(
                        self.dataset_name, training_params
                    )

                    if result.get("success"):
                        self.log_text.append("训练完成!\n")
                        self.log_text.append(f"模型已保存: {result.get('model_path')}\n")
                        self.log_text.append(f"结果管理: {result.get('model_result_path')}\n")
                        self.log_text.append(f"指标: {result.get('metrics', {})}\n")

                        self.annotation_completed.emit()

                        QMessageBox.information(
                            self, "训练完成",
                            f"训练 '{self.dataset_name}' 完成!\n模型已保存到训练结果管理模块。"
                        )
                    else:
                        self.log_text.append(f"训练失败: {result.get('error')}\n")
                        QMessageBox.critical(
                            self, "训练失败",
                            f"训练失败: {result.get('error', '未知错误')}"
                        )
                except Exception as e:
                    self.log_text.append(f"训练出错: {str(e)}\n")
                    QMessageBox.critical(
                        self, "训练错误",
                        f"训练过程中出错: {str(e)}"
                    )
                finally:
                    self.btn_start_training.setEnabled(True)

            thread = Thread(target=run_training, daemon=True)
            thread.start()

        except Exception as e:
            logger.error(f"启动训练失败: {str(e)}")
            QMessageBox.critical(self, "错误", f"启动训练失败: {str(e)}")

    def eventFilter(self, obj, event):
        """事件过滤器，用于监听焦点事件"""
        if obj == self.edit_remark:
            # 当失去焦点时保存
            if event.type() == event.FocusOut:
                self.save_remark_on_focus_out()
        return super().eventFilter(obj, event)

    def save_remark_on_focus_out(self):
        """失去焦点时保存备注"""
        current_remark = self.edit_remark.toPlainText().strip()

        # 如果内容没有变化，不保存
        if current_remark == self._last_saved_remark:
            return

        # 立即保存
        self._save_remark_to_file(current_remark)
        self._last_saved_remark = current_remark
        self.dataset_remark = current_remark
        logger.info(f"备注已自动保存: {self.dataset_name}")

    def _save_remark_to_file(self, remark: str) -> bool:
        """保存备注到文件"""
        try:
            remark_file = DatasetPathManager.get_dataset_path(self.dataset_name) / "remark.txt"
            with open(remark_file, 'w', encoding='utf-8') as f:
                f.write(remark)
            return True
        except Exception as e:
            logger.error(f"保存备注失败: {str(e)}")
            return False

    def save_remark(self):
        """保存备注（已废弃，保留用于兼容）"""
        pass

    def get_remark(self) -> str:
        """获取备注"""
        return self.edit_remark.toPlainText().strip()
