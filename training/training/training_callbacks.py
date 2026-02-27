#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
YOLO训练回调处理器

负责处理YOLO训练过程中的回调事件。
"""

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from .log_manager import TrainingLogManager


class TrainingCallbacks:
    """YOLO训练回调处理器"""

    # 类级别的停止标志
    should_stop: bool = False

    def __init__(self, log_manager: "TrainingLogManager"):
        """初始化回调处理器

        Args:
            log_manager: 日志管理器实例
        """
        self.log_manager = log_manager

    @classmethod
    def set_stop_flag(cls, should_stop: bool):
        """设置停止标志

        Args:
            should_stop: 是否应该停止训练
        """
        cls.should_stop = should_stop

    @classmethod
    def stop_training(cls):
        """停止训练"""
        cls.should_stop = True

    @classmethod
    def reset_stop_flag(cls):
        """重置停止标志"""
        cls.should_stop = False

    def on_train_start(self, trainer):
        """训练开始回调

        Args:
            trainer: YOLO训练器对象
        """
        self.log_manager.emit_log("训练开始...")
        self.log_manager.emit_log(f"Epochs: {trainer.epochs}, Batch size: {trainer.batch_size}")

    def on_train_epoch_end(self, trainer):
        """每个epoch结束时调用

        Args:
            trainer: YOLO训练器对象

        Raises:
            KeyboardInterrupt: 当需要停止训练时抛出
        """
        # 检查是否应该停止训练
        if self.should_stop:
            self.log_manager.emit_log("训练已停止")
            # 抛出KeyboardInterrupt来终止训练
            raise KeyboardInterrupt("训练被用户停止")

        # 获取训练指标
        metrics = trainer.metrics if hasattr(trainer, 'metrics') else {}
        loss = metrics.get('loss', 'N/A')

        # 发送日志
        self.log_manager.emit_log(f"Epoch {trainer.epoch}/{trainer.epochs} - Loss: {loss}")

    def on_train_end(self, trainer):
        """训练结束回调

        Args:
            trainer: YOLO训练器对象
        """
        # 不在这里输出"训练完成",让调用方统一处理
        pass

    def register_to_model(self, model):
        """将回调注册到YOLO模型

        Args:
            model: YOLO模型对象
        """
        model.add_callback("on_train_epoch_end", self.on_train_epoch_end)
        model.add_callback("on_train_start", self.on_train_start)
        model.add_callback("on_train_end", self.on_train_end)
