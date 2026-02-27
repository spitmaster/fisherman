#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
运行日志查看对话框

提供查看应用程序运行日志的功能。
"""

import os
import logging
from PyQt5.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QPushButton,
    QTextEdit, QComboBox, QLabel
)
from PyQt5.QtCore import Qt
from PyQt5.QtGui import QFont

logger = logging.getLogger(__name__)


class LogViewerDialog(QDialog):
    """日志查看对话框"""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.init_ui()
        self.load_logs()

    def init_ui(self):
        """初始化界面"""
        self.setWindowTitle("运行日志")
        self.setMinimumSize(800, 600)

        layout = QVBoxLayout(self)

        # 日志级别选择
        top_layout = QHBoxLayout()
        top_layout.addWidget(QLabel("日志级别:"))

        self.combo_level = QComboBox()
        self.combo_level.addItems(["全部", "DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"])
        self.combo_level.currentIndexChanged.connect(self.filter_logs)
        top_layout.addWidget(self.combo_level)

        top_layout.addStretch()

        # 刷新按钮
        self.btn_refresh = QPushButton("刷新")
        self.btn_refresh.clicked.connect(self.load_logs)
        top_layout.addWidget(self.btn_refresh)

        # 清空按钮
        self.btn_clear = QPushButton("清空")
        self.btn_clear.clicked.connect(self.clear_logs)
        top_layout.addWidget(self.btn_clear)

        # 关闭按钮
        self.btn_close = QPushButton("关闭")
        self.btn_close.clicked.connect(self.accept)
        top_layout.addWidget(self.btn_close)

        layout.addLayout(top_layout)

        # 日志显示区域
        self.log_text = QTextEdit()
        self.log_text.setReadOnly(True)
        self.log_text.setFont(QFont("Courier New", 9))
        layout.addWidget(self.log_text)

    def load_logs(self):
        """加载日志"""
        try:
            self.log_text.clear()

            # 查找日志目录
            log_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), "logs")
            if not os.path.exists(log_dir):
                self.log_text.setText("日志目录不存在")
                return

            # 读取最新的日志文件
            log_files = sorted([f for f in os.listdir(log_dir) if f.endswith('.log')], reverse=True)

            if not log_files:
                self.log_text.setText("暂无日志文件")
                return

            log_file = os.path.join(log_dir, log_files[0])

            if os.path.exists(log_file):
                with open(log_file, 'r', encoding='utf-8') as f:
                    content = f.read()
                    self._original_log_content = content  # 保存原始内容用于过滤
                    self.filter_logs()
            else:
                self.log_text.setText(f"日志文件不存在: {log_file}")

        except Exception as e:
            self.log_text.setText(f"读取日志失败: {str(e)}")
            logger.error(f"读取日志失败: {str(e)}")

    def filter_logs(self):
        """根据级别过滤日志"""
        if not hasattr(self, '_original_log_content'):
            return

        level = self.combo_level.currentText()

        if level == "全部":
            self.log_text.setText(self._original_log_content)
            return

        # 过滤指定级别的日志
        lines = self._original_log_content.split('\n')
        filtered_lines = []

        for line in lines:
            if f" - {level} - " in line:
                filtered_lines.append(line)

        if filtered_lines:
            self.log_text.setText('\n'.join(filtered_lines))
        else:
            self.log_text.setText(f"没有找到 {level} 级别的日志")

    def clear_logs(self):
        """清空日志显示"""
        self.log_text.clear()
