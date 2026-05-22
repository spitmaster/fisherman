#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
训练参数配置组件

负责训练参数的配置和验证。
"""

from PyQt5.QtWidgets import (
    QWidget, QFormLayout, QSpinBox, QComboBox
)
from global_support.device_resolver import get_available_devices, device_display_name


class TrainingParamsWidget(QWidget):
    """训练参数配置组件 - 单一职责: 参数配置"""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.init_ui()

    def init_ui(self):
        """初始化界面"""
        layout = QFormLayout(self)

        self.spin_epochs = QSpinBox()
        self.spin_epochs.setMinimum(1)
        self.spin_epochs.setMaximum(500)
        self.spin_epochs.setValue(50)

        self.spin_batch_size = QSpinBox()
        self.spin_batch_size.setMinimum(1)
        self.spin_batch_size.setMaximum(64)
        self.spin_batch_size.setValue(8)

        self.spin_img_size = QSpinBox()
        self.spin_img_size.setMinimum(320)
        self.spin_img_size.setMaximum(1280)
        self.spin_img_size.setValue(640)
        self.spin_img_size.setSingleStep(32)

        self.combo_model_type = QComboBox()
        self.combo_model_type.addItems([
            "yolov8n.pt (最快)",
            "yolov8s.pt (快速)",
            "yolov8m.pt (平衡)",
            "yolov8l.pt (精确)"
        ])
        self.combo_model_type.setCurrentIndex(0)

        self.combo_device = QComboBox()
        for info in get_available_devices():
            self.combo_device.addItem(device_display_name(info), info.spec)

        layout.addRow("轮数:", self.spin_epochs)
        layout.addRow("批次:", self.spin_batch_size)
        layout.addRow("尺寸:", self.spin_img_size)
        layout.addRow("模型类型:", self.combo_model_type)
        layout.addRow("计算设备:", self.combo_device)

    def get_training_params(self) -> dict:
        """获取训练参数

        Returns:
            训练参数字典
        """
        model_type = self.combo_model_type.currentText().split()[0]
        return {
            "epochs": self.spin_epochs.value(),
            "batch_size": self.spin_batch_size.value(),
            "image_size": self.spin_img_size.value(),
            "model_type": model_type,
            "device": self.combo_device.currentData() or "cpu",
        }

    def set_enabled(self, enabled: bool):
        """启用/禁用所有控件

        Args:
            enabled: 是否启用
        """
        self.spin_epochs.setEnabled(enabled)
        self.spin_batch_size.setEnabled(enabled)
        self.spin_img_size.setEnabled(enabled)
        self.combo_model_type.setEnabled(enabled)
        self.combo_device.setEnabled(enabled)
