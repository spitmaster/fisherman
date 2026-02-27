#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
训练设置标签页

重构版本: 遵循SOLID原则
- SRP: 每个组件单一职责
- OCP: 对扩展开放,对修改关闭
- LSP: 可替换的子组件
- ISP: 接口分离
- DIP: 依赖抽象而非具体实现
"""

import logging
from PyQt5.QtWidgets import QWidget, QVBoxLayout, QMessageBox
from PyQt5.QtCore import pyqtSignal

from training.training.executor import TrainingExecutor
from .training.training_controller import TrainingController
from .training.training_params_widget import TrainingParamsWidget
from .training.training_control_panel import TrainingControlPanel
from .training.training_log_widget import TrainingLogWidget

logger = logging.getLogger(__name__)


class TrainingTab(QWidget):
    """训练设置标签页 - Facade模式组合各子组件"""

    # 定义信号
    training_completed = pyqtSignal()  # 训练完成信号

    def __init__(self, dataset_name: str, annotated_count: int = 0, parent=None):
        super().__init__(parent)
        self.dataset_name = dataset_name
        self.annotated_count = annotated_count

        # 初始化子组件 (依赖注入)
        self.training_executor = TrainingExecutor()
        self.training_controller = TrainingController(self.training_executor)
        self.params_widget = TrainingParamsWidget()
        self.control_panel = TrainingControlPanel()
        self.log_widget = TrainingLogWidget()

        # 连接信号
        self._connect_signals()

        # 初始化界面
        self.init_ui()
        self._update_button_state()

        # 初始日志
        self.log_widget.insert_initial_message("训练日志初始化完成\n")

    def init_ui(self):
        """初始化界面"""
        layout = QVBoxLayout(self)
        layout.addWidget(self.params_widget)
        layout.addWidget(self.control_panel)
        layout.addWidget(self.log_widget)

    def _connect_signals(self):
        """连接信号和槽"""
        # 控制器信号 -> 界面
        self.training_controller.training_started.connect(self._on_training_started)
        self.training_controller.training_stopped.connect(self._on_training_stopped)
        self.training_controller.training_completed.connect(self._on_training_completed)
        self.training_controller.training_failed.connect(self._on_training_failed)

        # 设置日志回调
        TrainingExecutor.set_log_callback(self.log_widget.append_log)

        # 绑定控制面板按钮
        self.control_panel.bind_start_handler(self.start_training)
        self.control_panel.bind_stop_handler(self.stop_training)

    def update_annotated_count(self, count: int):
        """更新已标注数量

        Args:
            count: 已标注数量
        """
        self.annotated_count = count
        self._update_button_state()

    def start_training(self):
        """开始训练"""
        try:
            # 确认对话框
            reply = QMessageBox.question(
                self,
                "确认训练",
                f"确定要开始训练 '{self.dataset_name}' 吗？训练过程可能需要较长时间。",
                QMessageBox.Yes | QMessageBox.No
            )
            if reply != QMessageBox.Yes:
                return

            # 获取训练参数
            training_params = self.params_widget.get_training_params()

            # 记录初始日志
            self.log_widget.append_log(f"开始训练: {self.dataset_name}")
            self.log_widget.append_log(
                f"训练参数: epochs={training_params['epochs']}, "
                f"batch={training_params['batch_size']}, "
                f"imgsz={training_params['image_size']}, "
                f"model={training_params['model_type']}"
            )
            self.log_widget.append_log("-" * 50)

            # 启动训练
            self.training_controller.start_training(self.dataset_name, training_params)

        except Exception as e:
            logger.error(f"启动训练失败: {str(e)}")
            QMessageBox.critical(self, "错误", f"启动训练失败: {str(e)}")

    def stop_training(self):
        """停止训练"""
        try:
            reply = QMessageBox.question(
                self,
                "确认停止",
                "确定要停止当前训练吗？训练将在当前epoch完成后停止,当前进度不会保存。",
                QMessageBox.Yes | QMessageBox.No
            )
            if reply != QMessageBox.Yes:
                return

            self.log_widget.append_log("正在停止训练...")
            self.log_widget.append_log("训练将在当前epoch完成后停止...")
            self.training_controller.stop_training()

        except Exception as e:
            logger.error(f"停止训练失败: {str(e)}")
            QMessageBox.critical(self, "错误", f"停止训练失败: {str(e)}")

    def _on_training_started(self):
        """训练开始回调"""
        self._update_button_state()

    def _on_training_stopped(self):
        """训练停止回调"""
        self.log_widget.append_log("训练已被用户停止")
        self._update_button_state()

    def _on_training_completed(self, result: dict):
        """训练完成回调"""
        result_info = result.get('result', {})
        self.log_widget.append_log(f"模型已保存: {result_info.get('model_path')}")
        self.log_widget.append_log(f"结果管理: {result_info.get('model_result_path')}")
        self.log_widget.append_log(f"指标: {result_info.get('metrics', {})}")

        self.training_completed.emit()
        QMessageBox.information(
            self, "训练完成",
            f"训练 '{self.dataset_name}' 完成!\n模型已保存到训练结果管理模块。"
        )
        self._update_button_state()

    def _on_training_failed(self, error: str):
        """训练失败回调"""
        self.log_widget.append_log(f"训练失败: {error}")

        # 如果不是用户停止,显示错误对话框
        if "用户停止" not in error:
            QMessageBox.critical(self, "训练失败", f"训练失败: {error}")

        self._update_button_state()

    def _update_button_state(self):
        """更新按钮状态"""
        is_training = self.training_controller.is_training
        can_start = self.annotated_count > 0
        self.control_panel.set_training_state(is_training, can_start)
        self.params_widget.set_enabled(not is_training)
