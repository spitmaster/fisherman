"""
训练模块 - 核心接口和基类

提供抽象接口定义和基础管理器类。
"""

from .interfaces import (
    IAnnotationTool,
    ITrainingManager,
    IDatasetManager,
    ITrainer,
    ITaskStatusTracker
)

from .base_manager import BaseManager

__all__ = [
    'IAnnotationTool',
    'ITrainingManager',
    'IDatasetManager',
    'ITrainer',
    'ITaskStatusTracker',
    'BaseManager'
]