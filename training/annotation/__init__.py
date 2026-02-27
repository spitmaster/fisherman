#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
标注验证模块

提供基于策略模式的标注验证功能。
"""

from .annotation_validator import AnnotationValidator
from .validation_strategies import (
    ValidationStrategy,
    BasicFormatValidationStrategy,
    CoordinateRangeValidationStrategy,
    AnnotationSizeValidationStrategy,
    ClassIdValidationStrategy,
    DuplicateAnnotationValidationStrategy
)

__all__ = [
    'AnnotationValidator',
    'ValidationStrategy',
    'BasicFormatValidationStrategy',
    'CoordinateRangeValidationStrategy',
    'AnnotationSizeValidationStrategy',
    'ClassIdValidationStrategy',
    'DuplicateAnnotationValidationStrategy'
]
