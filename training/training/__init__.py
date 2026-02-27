"""
训练模块 - 训练执行

提供训练执行、YOLOv8训练器、回调处理和结果保存功能。
"""

from .executor import TrainingExecutor
from .config_builder import TrainingConfigBuilder
from .log_manager import TrainingLogManager
from .result_saver import TrainingResultSaver
from .training_callbacks import TrainingCallbacks

# 创建全局实例
training_executor = TrainingExecutor()
config_builder = TrainingConfigBuilder()

__all__ = [
    'TrainingExecutor',
    'TrainingConfigBuilder',
    'TrainingLogManager',
    'TrainingResultSaver',
    'TrainingCallbacks',
    'training_executor',
    'config_builder'
]