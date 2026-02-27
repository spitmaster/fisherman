#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
训练控制面板组件

负责训练控制按钮的状态管理。
"""

from PyQt5.QtWidgets import QWidget, QHBoxLayout, QPushButton, QSpacerItem, QSizePolicy


class TrainingControlPanel(QWidget):
    """训练控制面板 - 单一职责: 控制按钮管理"""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.init_ui()

    def init_ui(self):
        """初始化界面"""
        layout = QHBoxLayout(self)

        spacer = QSpacerItem(40, 20, QSizePolicy.Expanding, QSizePolicy.Minimum)
        layout.addItem(spacer)

        self.btn_start_training = QPushButton("开始训练")
        self.btn_start_training.setStyleSheet(
            "background-color: #2196F3; color: white; font-size: 14px; padding: 10px;"
        )

        self.btn_stop_training = QPushButton("停止训练")
        self.btn_stop_training.setStyleSheet(
            "background-color: #F44336; color: white; font-size: 14px; padding: 10px;"
        )

        layout.addWidget(self.btn_start_training)
        layout.addWidget(self.btn_stop_training)

        spacer2 = QSpacerItem(40, 20, QSizePolicy.Expanding, QSizePolicy.Minimum)
        layout.addItem(spacer2)

    def set_training_state(self, is_training: bool, can_start: bool = True):
        """设置训练状态

        Args:
            is_training: 是否正在训练
            can_start: 是否可以开始训练
        """
        if is_training:
            self.btn_start_training.setEnabled(False)
            self.btn_stop_training.setEnabled(True)
        else:
            self.btn_start_training.setEnabled(can_start)
            self.btn_stop_training.setEnabled(False)

    def bind_start_handler(self, handler):
        """绑定开始按钮事件

        Args:
            handler: 处理函数
        """
        self.btn_start_training.clicked.connect(handler)

    def bind_stop_handler(self, handler):
        """绑定停止按钮事件

        Args:
            handler: 处理函数
        """
        self.btn_stop_training.clicked.connect(handler)
