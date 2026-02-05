#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
标注管理器模块

提供标注任务的统一管理接口。
"""

import os
import logging

from .tool import AnnotationTool
from .validator import validate_dataset_annotations, get_annotation_statistics

# 日志配置
logger = logging.getLogger(__name__)


class AnnotationManager:
    """标注管理器"""
    
    def __init__(self):
        """初始化标注管理器"""
        pass
        
    def create_annotation_tool(self, task_info, image_files, annotated_count):
        """创建标注工具实例
        
        Args:
            task_info: 任务信息
            image_files: 图片文件列表
            annotated_count: 已标注图片数量
            
        Returns:
            标注工具实例
        """
        return AnnotationTool(task_info, image_files, annotated_count)
        
    def validate_dataset_annotations(self, task_dir):
        """验证数据集的标注数据
        
        Args:
            task_dir: 任务目录
            
        Returns:
            验证结果
        """
        return validate_dataset_annotations(task_dir)
        
    def get_dataset_annotation_statistics(self, task_dir):
        """获取数据集标注统计信息
        
        Args:
            task_dir: 任务目录
            
        Returns:
            统计信息字典
        """
        return get_annotation_statistics(task_dir)