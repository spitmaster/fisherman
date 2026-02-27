#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
训练模块 - 标注工具（向后兼容）

此文件保留以确保向后兼容性。
具体实现已移至 training/annotation/tool.py
"""

# 导入新实现以保持向后兼容
from .annotation.tool import AnnotationTool, AnnotationManager, annotation_manager

__all__ = ['AnnotationTool', 'AnnotationManager', 'annotation_manager']
