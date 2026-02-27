#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
训练模块初始化

统一导出所有子模块的主要类和实例。
"""

# 主入口
from .training_manager import TrainingManager, training_manager
from .annotation_tool import AnnotationTool, AnnotationManager, annotation_manager

# 验证模块
from .validator import TrainingValidator, DatasetValidator, training_validator, dataset_validator

# 统计模块
from .statistics import TrainingStatistics, ProgressCalculator, training_statistics, progress_calculator

# 备份模块
from .backup import TrainingBackupManager, AnnotationBackupManager, training_backup_manager, annotation_backup_manager

# 标注子模块
from .annotation.exporter import AnnotationExporter, create_exporter

__all__ = [
    # 主入口
    'TrainingManager',
    'training_manager',
    'AnnotationTool',
    'AnnotationManager', 
    'annotation_manager',
    
    # 验证模块
    'TrainingValidator',
    'DatasetValidator',
    'training_validator',
    'dataset_validator',
    
    # 统计模块
    'TrainingStatistics',
    'ProgressCalculator',
    'training_statistics',
    'progress_calculator',
    
    # 备份模块
    'TrainingBackupManager',
    'AnnotationBackupManager',
    'training_backup_manager',
    'annotation_backup_manager',
    
    # 标注导出器
    'AnnotationExporter',
    'create_exporter',
]
