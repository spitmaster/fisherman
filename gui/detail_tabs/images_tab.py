#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
图片管理标签页

提供训练集图片导入、查看、删除功能。
"""

import logging
from PyQt5.QtWidgets import QWidget, QVBoxLayout, QHBoxLayout, QListWidget, QPushButton, QMessageBox
from PyQt5.QtCore import pyqtSignal

from training.task.dataset_manager import DatasetManager

logger = logging.getLogger(__name__)


class ImagesTab(QWidget):
    """图片管理标签页"""

    # 定义信号
    images_imported = pyqtSignal(int)  # 图片导入成功信号，传入导入数量
    images_deleted = pyqtSignal()  # 图片删除信号
    annotation_completed = pyqtSignal()  # 标注完成信号

    def __init__(self, dataset_name: str, parent=None):
        super().__init__(parent)
        self.dataset_name = dataset_name
        self.dataset_manager = DatasetManager()
        self.parent_dialog = None  # 父对话框

        self.init_ui()

    def init_ui(self):
        """初始化界面"""
        layout = QVBoxLayout(self)

        # 图片列表
        self.image_list = QListWidget()
        layout.addWidget(self.image_list)

        # 操作按钮
        btn_layout = QHBoxLayout()
        btn_import = QPushButton("导入图片")
        btn_import.clicked.connect(self.import_images)

        btn_refresh = QPushButton("刷新列表")
        btn_refresh.clicked.connect(self.load_images)

        btn_start_annotation = QPushButton("开始标注")
        btn_start_annotation.setStyleSheet("background-color: #4CAF50; color: white;")
        btn_start_annotation.clicked.connect(self.start_annotation)

        btn_delete_all = QPushButton("清空所有图片")
        btn_delete_all.clicked.connect(self.delete_all_images)
        btn_delete_all.setStyleSheet("background-color: #f44336; color: white;")

        btn_layout.addWidget(btn_import)
        btn_layout.addWidget(btn_refresh)
        btn_layout.addWidget(btn_start_annotation)
        btn_layout.addWidget(btn_delete_all)
        layout.addLayout(btn_layout)

    def load_images(self):
        """加载图片列表"""
        try:
            self.image_list.clear()
            image_files = self.dataset_manager.get_image_list_by_name(self.dataset_name)
            for img_file in image_files:
                self.image_list.addItem(img_file)
            logger.info(f"加载图片列表成功: {len(image_files)} 张")
        except Exception as e:
            logger.error(f"加载图片列表失败: {str(e)}")

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

                self.load_images()
                self.images_imported.emit(imported_count)

                QMessageBox.information(self, "成功", f"成功导入 {imported_count} 张图片")
                logger.info(f"图片导入成功: {imported_count} 张")

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
                from pathlib import Path
                from training.dataset_path_manager import DatasetPathManager

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

                self.load_images()
                self.images_deleted.emit()

                QMessageBox.information(self, "成功", "已清空所有图片和标注")
                logger.info("已清空所有图片和标注")

            except Exception as e:
                logger.error(f"清空图片失败: {str(e)}")
                QMessageBox.critical(self, "错误", f"清空图片失败: {str(e)}")

    def set_parent_dialog(self, dialog):
        """设置父对话框"""
        self.parent_dialog = dialog

    def start_annotation(self):
        """开始标注"""
        try:
            from gui.annotation_window import open_annotation_window

            open_annotation_window(self.dataset_name, self.parent_dialog)
            self.annotation_completed.emit()
            logger.info("标注工具已启动")

        except Exception as e:
            logger.error(f"启动标注工具失败: {str(e)}")
            QMessageBox.critical(self, "错误", f"启动标注工具失败: {str(e)}")
