#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
训练日志显示组件

负责训练日志的显示和管理。
"""

from PyQt5.QtWidgets import QWidget, QVBoxLayout, QGroupBox, QTextEdit
from PyQt5.QtCore import pyqtSignal


class TrainingLogWidget(QWidget):
    """训练日志组件 - 单一职责: 日志显示"""

    log_updated = pyqtSignal(str)  # 日志更新信号

    def __init__(self, parent=None):
        super().__init__(parent)
        self.init_ui()

        # 连接信号
        self.log_updated.connect(self._append_log)

    def init_ui(self):
        """初始化界面"""
        layout = QVBoxLayout(self)

        log_group = QGroupBox("训练日志")
        log_layout = QVBoxLayout()
        self.log_text = QTextEdit()
        self.log_text.setReadOnly(True)
        self.log_text.setMaximumHeight(200)
        log_layout.addWidget(self.log_text)
        log_group.setLayout(log_layout)
        layout.addWidget(log_group)

    def append_log(self, message: str):
        """追加日志

        Args:
            message: 日志消息
        """
        self.log_updated.emit(message)

    def _append_log(self, message: str):
        """内部方法: 在主线程中追加日志

        Args:
            message: 日志消息
        """
        self.log_text.insertPlainText(message + "\n")
        self.log_text.ensureCursorVisible()
        self.log_text.update()

    def clear(self):
        """清空日志"""
        self.log_text.clear()

    def insert_initial_message(self, message: str):
        """插入初始消息

        Args:
            message: 消息内容
        """
        self.log_text.insertPlainText(message + "\n")
        self.log_text.ensureCursorVisible()
