#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
训练集详情对话框

提供训练集的详细管理功能：导入图片、标注、训练等。
"""

import logging
from PyQt5.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QFormLayout, QPushButton,
    QLabel, QGroupBox, QMessageBox, QTextEdit, QLineEdit
)
from PyQt5.QtCore import Qt, pyqtSignal
from PyQt5.QtGui import QFont

from training.task.dataset_manager import DatasetManager
from training.dataset_path_manager import DatasetPathManager
from gui.detail_tabs.images_tab import ImagesTab
from global_support.database import db_manager, TrainingTask

logger = logging.getLogger(__name__)


class DatasetDetailDialog(QDialog):
    """训练集详情对话框"""

    annotation_completed = pyqtSignal()  # 标注完成信号

    def __init__(self, dataset_id: str, dataset_remark: str = "", parent=None):
        super().__init__(parent)
        # 移除问号帮助按钮
        self.setWindowFlags(self.windowFlags() & ~Qt.WindowContextHelpButtonHint)
        self.dataset_id = dataset_id  # UUID
        self.dataset_name = ""  # 从数据库加载的名称
        self.dataset_remark = dataset_remark
        self.dataset_manager = DatasetManager()

        # 保存状态
        self._last_saved_remark = dataset_remark
        self._last_saved_name = ""

        self.init_ui()
        self.load_dataset_info()

        # 安装事件过滤器来监听焦点事件
        self.edit_remark.installEventFilter(self)
        self.edit_name.installEventFilter(self)

    def accept(self):
        """关闭对话框前立即保存名称和备注"""
        # 保存当前名称
        current_name = self.edit_name.text().strip()
        if current_name and current_name != self._last_saved_name:
            self._save_dataset_name_to_db(current_name)
            self._last_saved_name = current_name
            self.dataset_name = current_name
            logger.info(f"训练集名称已保存: {current_name}")

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
        self.setWindowTitle(f"训练集详情 - {self.dataset_id}")
        self.setMinimumSize(900, 700)
        self.resize(900, 700)

        layout = QVBoxLayout(self)

        # 训练集信息(固定高度)
        info_group = QGroupBox("训练集信息")
        info_group.setFixedHeight(180)  # 固定训练集信息区域高度
        info_layout = QFormLayout()

        # 训练集ID (只读)
        self.edit_id = QLineEdit(self.dataset_id)
        self.edit_id.setReadOnly(True)
        self.edit_id.setStyleSheet("QLineEdit { background-color: #f0f0f0; }")

        # 训练集名称 (可编辑)
        self.edit_name = QLineEdit()
        self.edit_name.setPlaceholderText("输入训练集名称...")
        self.edit_name.setText(self.dataset_name)
        # 添加提示文本，说明会自动保存
        self.edit_name.setToolTip("修改后失去焦点或关闭对话框时自动保存")

        self.edit_remark = QTextEdit()
        self.edit_remark.setPlaceholderText("输入备注信息...")
        self.edit_remark.setText(self.dataset_remark)
        # 添加提示文本，说明会自动保存
        self.edit_remark.setToolTip("修改后失去焦点或关闭对话框时自动保存")

        info_layout.addRow("训练集ID:", self.edit_id)
        info_layout.addRow("训练集名称:", self.edit_name)
        info_layout.addRow("备注:", self.edit_remark)

        info_group.setLayout(info_layout)
        layout.addWidget(info_group)

        # 数据集统计信息(固定高度)
        stats_group = QGroupBox("数据统计")
        stats_group.setFixedHeight(60)  # 固定统计信息区域高度
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

        # 图片管理 (使用 dataset_id 而不是 dataset_name)
        self.images_tab = ImagesTab(self.dataset_id, self)
        self.images_tab.images_imported.connect(self.on_images_imported)
        self.images_tab.images_deleted.connect(self.on_images_deleted)
        self.images_tab.annotation_completed.connect(self.on_annotation_completed)
        self.images_tab.set_parent_dialog(self)  # 设置父对话框,用于启动标注工具

        layout.addWidget(self.images_tab)

        # 底部按钮
        button_layout = QHBoxLayout()
        button_layout.addStretch()

        self.btn_close = QPushButton("关闭")
        self.btn_close.clicked.connect(self.accept)

        button_layout.addWidget(self.btn_close)
        layout.addLayout(button_layout)

    def load_dataset_info(self):
        """加载训练集信息"""
        try:
            # 从数据库加载训练任务信息
            session = db_manager.get_session()
            try:
                task = session.query(TrainingTask).filter_by(id=self.dataset_id).first()
                if task:
                    self.dataset_name = task.task_name
                    self.edit_name.setText(self.dataset_name)
                    self._last_saved_name = self.dataset_name
            finally:
                session.close()

            # 加载数据集统计信息
            dataset_info = self.dataset_manager.get_dataset_info_by_name(self.dataset_id)

            if dataset_info:
                total_images = dataset_info['total_images']
                annotated_images = dataset_info['annotated_images']
                unannotated = total_images - annotated_images
                progress = dataset_info['annotation_progress']

                self.label_total_images.setText(f"总图片数: {total_images}")
                self.label_annotated_count.setText(f"已标注: {annotated_images}")
                self.label_unannotated_count.setText(f"未标注: {unannotated}")
                self.label_annotation_progress.setText(f"标注进度: {progress:.1f}%")

            # 加载图片列表
            self.images_tab.load_images()

            logger.info(f"加载训练集信息成功: {self.dataset_id}")

        except Exception as e:
            logger.error(f"加载训练集信息失败: {str(e)}")
            QMessageBox.warning(self, "错误", f"加载训练集信息失败: {str(e)}")

    def on_images_imported(self, count):
        """图片导入成功回调"""
        self.load_dataset_info()

    def on_images_deleted(self):
        """图片删除成功回调"""
        self.load_dataset_info()

    def on_annotation_completed(self):
        """标注完成回调"""
        self.load_dataset_info()
        self.annotation_completed.emit()

    def eventFilter(self, obj, event):
        """事件过滤器，用于监听焦点事件"""
        if obj == self.edit_name:
            # 当失去焦点时保存名称
            if event.type() == event.FocusOut:
                self.save_name_on_focus_out()
        elif obj == self.edit_remark:
            # 当失去焦点时保存备注
            if event.type() == event.FocusOut:
                self.save_remark_on_focus_out()
        return super().eventFilter(obj, event)

    def save_name_on_focus_out(self):
        """失去焦点时保存名称"""
        current_name = self.edit_name.text().strip()

        # 如果内容没有变化或为空，不保存
        if not current_name or current_name == self._last_saved_name:
            return

        # 立即保存
        self._save_dataset_name_to_db(current_name)
        self._last_saved_name = current_name
        self.dataset_name = current_name
        logger.info(f"训练集名称已自动保存: {current_name}")

    def _save_dataset_name_to_db(self, name: str) -> bool:
        """保存训练集名称到数据库"""
        try:
            session = db_manager.get_session()
            try:
                task = session.query(TrainingTask).filter_by(id=self.dataset_id).first()
                if task:
                    task.task_name = name
                    session.commit()
                    return True
            finally:
                session.close()
        except Exception as e:
            logger.error(f"保存训练集名称失败: {str(e)}")
        return False

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
