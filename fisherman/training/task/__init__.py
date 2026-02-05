"""
训练模块 - 训练任务管理

提供训练任务的创建、管理、状态跟踪和数据集管理功能。
"""

from .manager import TrainingTaskManager
from .creator import TaskCreator
from .status_tracker import TaskStatusTracker
from .dataset_manager import DatasetManager

# 创建全局管理器实例
training_manager = TrainingTaskManager()

__all__ = [
    'TrainingTaskManager',
    'training_manager',
    'TaskCreator',
    'TaskStatusTracker',
    'DatasetManager'
]