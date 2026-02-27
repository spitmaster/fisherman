#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
训练控制组件

负责训练的状态管理和执行控制。
"""

import logging
from PyQt5.QtCore import QObject, pyqtSignal
from threading import Thread

from training.training.executor import TrainingExecutor

logger = logging.getLogger(__name__)


class TrainingController(QObject):
    """训练控制器 - 遵循单一职责原则"""

    # 定义信号
    training_started = pyqtSignal()
    training_stopped = pyqtSignal()
    training_completed = pyqtSignal(dict)
    training_failed = pyqtSignal(str)
    progress_updated = pyqtSignal(int, str)

    def __init__(self, executor: TrainingExecutor = None):
        """初始化训练控制器

        Args:
            executor: 训练执行器
        """
        super().__init__()
        self.executor = executor or TrainingExecutor()
        self.is_training = False
        self.training_thread = None

    def start_training(self, dataset_name: str, training_params: dict) -> bool:
        """开始训练

        Args:
            dataset_name: 数据集名称
            training_params: 训练参数

        Returns:
            是否成功启动
        """
        if self.is_training:
            logger.warning("训练正在进行中")
            return False

        self.is_training = True
        self.training_started.emit()

        def run_training():
            try:
                result = self.executor.train_by_name(dataset_name, training_params)
                if result.get("success"):
                    self.training_completed.emit(result)
                else:
                    self.training_failed.emit(result.get("error", "未知错误"))
            except Exception as e:
                logger.error(f"训练执行失败: {str(e)}")
                self.training_failed.emit(str(e))
            finally:
                self.is_training = False

        self.training_thread = Thread(target=run_training, daemon=True)
        self.training_thread.start()
        return True

    def stop_training(self) -> bool:
        """停止训练

        Returns:
            是否成功停止
        """
        if not self.is_training:
            return False

        TrainingExecutor.stop_training()
        self.is_training = False
        self.training_stopped.emit()
        return True

    def reset(self):
        """重置控制器状态"""
        self.is_training = False
        self.training_thread = None
