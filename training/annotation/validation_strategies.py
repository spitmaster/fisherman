#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
验证策略

使用策略模式实现开闭原则(OCP): 对扩展开放,对修改关闭
"""

from abc import ABC, abstractmethod
from typing import Dict, Any, Optional
import logging

logger = logging.getLogger(__name__)


class ValidationStrategy(ABC):
    """验证策略抽象基类"""

    def __init__(self, enabled: bool = True):
        """初始化验证策略

        Args:
            enabled: 是否启用
        """
        self.enabled = enabled
        self.error_message = ""

    @abstractmethod
    def validate(self, **kwargs) -> bool:
        """执行验证

        Args:
            **kwargs: 验证所需参数

        Returns:
            验证是否通过
        """
        pass

    def is_enabled(self) -> bool:
        """检查策略是否启用

        Returns:
            是否启用
        """
        return self.enabled

    def enable(self):
        """启用策略"""
        self.enabled = True

    def disable(self):
        """禁用策略"""
        self.enabled = False


class BasicFormatValidationStrategy(ValidationStrategy):
    """基本格式验证策略"""

    def __init__(self, enabled: bool = True, min_fields: int = 5):
        """初始化

        Args:
            enabled: 是否启用
            min_fields: 最少字段数
        """
        super().__init__(enabled)
        self.min_fields = min_fields
        self.error_message = f"标注文件格式错误: 字段数量不足(需要{min_fields}个)"

    def validate(self, parts: list, line_num: int = 0, **kwargs) -> bool:
        """验证格式

        Args:
            parts: 分割后的数据
            line_num: 行号
            **kwargs: 其他参数

        Returns:
            验证是否通过
        """
        if not self.enabled:
            return True

        if len(parts) < self.min_fields:
            logger.debug(f"第 {line_num + 1} 行字段数量不足: {len(parts)} < {self.min_fields}")
            return False

        return True


class CoordinateRangeValidationStrategy(ValidationStrategy):
    """坐标范围验证策略"""

    def __init__(self, enabled: bool = True, min_val: float = 0.0, max_val: float = 1.0):
        """初始化

        Args:
            enabled: 是否启用
            min_val: 最小值
            max_val: 最大值
        """
        super().__init__(enabled)
        self.min_val = min_val
        self.max_val = max_val
        self.error_message = f"坐标超出有效范围 [{min_val}, {max_val}]"

    def validate(self, x_center: float, y_center: float, width: float, height: float, **kwargs) -> bool:
        """验证坐标范围

        Args:
            x_center: x中心坐标
            y_center: y中心坐标
            width: 宽度
            height: 高度
            **kwargs: 其他参数

        Returns:
            验证是否通过
        """
        if not self.enabled:
            return True

        errors = []

        # 验证中心坐标
        if not (self.min_val <= x_center <= self.max_val):
            errors.append(f"x_center {x_center:.6f} 超出范围 [{self.min_val}, {self.max_val}]")
        if not (self.min_val <= y_center <= self.max_val):
            errors.append(f"y_center {y_center:.6f} 超出范围 [{self.min_val}, {self.max_val}]")

        # 验证边界
        x_min = x_center - width / 2
        x_max = x_center + width / 2
        y_min = y_center - height / 2
        y_max = y_center + height / 2

        if x_min < self.min_val or x_max > self.max_val:
            errors.append(f"标注框在x轴上超出图像边界: [{x_min:.6f}, {x_max:.6f}]")
        if y_min < self.min_val or y_max > self.max_val:
            errors.append(f"标注框在y轴上超出图像边界: [{y_min:.6f}, {y_max:.6f}]")

        if errors:
            self.error_message = "; ".join(errors)
            return False

        return True


class AnnotationSizeValidationStrategy(ValidationStrategy):
    """标注尺寸验证策略"""

    def __init__(self, enabled: bool = True, min_size: float = 0.001):
        """初始化

        Args:
            enabled: 是否启用
            min_size: 最小标注面积
        """
        super().__init__(enabled)
        self.min_size = min_size
        self.error_message = f"标注尺寸过小: < {min_size}"

    def validate(self, width: float, height: float, **kwargs) -> bool:
        """验证标注尺寸

        Args:
            width: 宽度
            height: 高度
            **kwargs: 其他参数

        Returns:
            验证是否通过
        """
        if not self.enabled:
            return True

        area = width * height
        if area < self.min_size:
            self.error_message = f"标注尺寸过小: {area:.6f} < {self.min_size}"
            return False

        return True


class ClassIdValidationStrategy(ValidationStrategy):
    """类别ID验证策略"""

    def __init__(self, enabled: bool = True, max_classes: int = 1000):
        """初始化

        Args:
            enabled: 是否启用
            max_classes: 最大类别数
        """
        super().__init__(enabled)
        self.max_classes = max_classes
        self.error_message = f"类别ID超出有效范围 [0, {max_classes - 1}]"

    def validate(self, class_id: int, **kwargs) -> bool:
        """验证类别ID

        Args:
            class_id: 类别ID
            **kwargs: 其他参数

        Returns:
            验证是否通过
        """
        if not self.enabled:
            return True

        if class_id < 0:
            self.error_message = f"类别ID {class_id} 不能为负数"
            return False
        elif class_id >= self.max_classes:
            self.error_message = f"类别ID {class_id} 超出最大限制 {self.max_classes - 1}"
            return False

        return True


class DuplicateAnnotationValidationStrategy(ValidationStrategy):
    """重复标注验证策略"""

    def __init__(self, enabled: bool = True):
        """初始化

        Args:
            enabled: 是否启用
        """
        super().__init__(enabled)
        self.error_message = "检测到重复的标注"
        self._annotations = []

    def reset(self):
        """重置标注记录"""
        self._annotations = []

    def validate(self, class_id: int, x_center: float, y_center: float,
                width: float, height: float, **kwargs) -> bool:
        """验证是否重复

        Args:
            class_id: 类别ID
            x_center: x中心坐标
            y_center: y中心坐标
            width: 宽度
            height: 高度
            **kwargs: 其他参数

        Returns:
            验证是否通过
        """
        if not self.enabled:
            return True

        annotation_key = (class_id, x_center, y_center, width, height)
        if annotation_key in self._annotations:
            self.error_message = f"检测到重复标注: {annotation_key}"
            return False

        self._annotations.append(annotation_key)
        return True
