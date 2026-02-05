"""
训练模块 - 训练执行

提供训练执行、YOLOv8训练器、回调处理和结果保存功能。
"""

from .executor import TrainingExecutor
from .yolo_trainer import YOLOTrainer
from .callback_handler import TrainingCallbackHandler
from .result_saver import TrainingResultSaver

# 创建全局实例
training_executor = TrainingExecutor()
yolo_trainer = YOLOTrainer()
callback_handler = TrainingCallbackHandler()
result_saver = TrainingResultSaver()

__all__ = [
    'TrainingExecutor',
    'YOLOTrainer',
    'TrainingCallbackHandler',
    'TrainingResultSaver',
    'training_executor',
    'yolo_trainer',
    'callback_handler',
    'result_saver'
]