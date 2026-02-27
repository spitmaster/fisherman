#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
设置标签页

提供系统信息显示和应用程序设置功能
"""

import logging
from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QGroupBox, QLabel
)

logger = logging.getLogger(__name__)


class SettingsTab(QWidget):
    """设置标签页"""

    def __init__(self, parent=None):
        """初始化设置标签页"""
        super().__init__(parent)
        self._init_ui()

    def _init_ui(self):
        """初始化界面"""
        layout = QVBoxLayout(self)

        # 应用程序设置
        app_group = QGroupBox("应用程序设置")
        app_layout = QVBoxLayout(app_group)

        app_layout.addWidget(QLabel("设置内容"))
        layout.addWidget(app_group)

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

        layout.addWidget(system_group)
