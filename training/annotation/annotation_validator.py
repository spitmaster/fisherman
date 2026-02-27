#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
标注验证器 (重构版)

使用策略模式实现开闭原则 (OCP)
依赖倒置原则 (DIP): 依赖抽象的 ValidationStrategy
"""

import os
import logging
from typing import Dict, List, Any, Tuple, Optional
from pathlib import Path

from .validation_strategies import (
    ValidationStrategy,
    BasicFormatValidationStrategy,
    CoordinateRangeValidationStrategy,
    AnnotationSizeValidationStrategy,
    ClassIdValidationStrategy,
    DuplicateAnnotationValidationStrategy
)

logger = logging.getLogger(__name__)


class AnnotationValidator:
    """标注验证器 - 使用策略模式"""

    def __init__(self):
        """初始化验证器"""
        # 初始化验证策略
        self.strategies: Dict[str, ValidationStrategy] = {
            "basic_format": BasicFormatValidationStrategy(),
            "coordinate_range": CoordinateRangeValidationStrategy(),
            "annotation_size": AnnotationSizeValidationStrategy(),
            "class_id": ClassIdValidationStrategy(),
            "duplicate": DuplicateAnnotationValidationStrategy()
        }

    def add_strategy(self, name: str, strategy: ValidationStrategy):
        """添加验证策略 - 开闭原则: 对扩展开放

        Args:
            name: 策略名称
            strategy: 验证策略
        """
        self.strategies[name] = strategy
        logger.info(f"添加验证策略: {name}")

    def remove_strategy(self, name: str):
        """移除验证策略

        Args:
            name: 策略名称
        """
        if name in self.strategies:
            del self.strategies[name]
            logger.info(f"移除验证策略: {name}")

    def enable_strategy(self, name: str):
        """启用验证策略

        Args:
            name: 策略名称
        """
        if name in self.strategies:
            self.strategies[name].enable()

    def disable_strategy(self, name: str):
        """禁用验证策略

        Args:
            name: 策略名称
        """
        if name in self.strategies:
            self.strategies[name].disable()

    def validate_single_annotation_file(
        self,
        label_path: str,
        image_filename: str = "",
        image_width: int = None,
        image_height: int = None
    ) -> Dict[str, Any]:
        """验证单个标注文件

        Args:
            label_path: 标注文件路径
            image_filename: 图片文件名
            image_width: 图片宽度
            image_height: 图片高度

        Returns:
            验证结果字典
        """
        validation_result = {
            "valid": True,
            "file_path": label_path,
            "image_filename": image_filename,
            "total_annotations": 0,
            "valid_annotations": 0,
            "errors": [],
            "warnings": [],
            "class_ids": set(),
            "annotation_details": []
        }

        if not os.path.exists(label_path):
            validation_result["valid"] = False
            validation_result["errors"].append(f"标注文件不存在: {label_path}")
            return validation_result

        try:
            # 重置重复检查策略
            if "duplicate" in self.strategies:
                self.strategies["duplicate"].reset()

            with open(label_path, "r", encoding="utf-8") as f:
                lines = f.readlines()

            validation_result["total_annotations"] = len([l for l in lines if l.strip()])

            for line_num, line in enumerate(lines):
                line = line.strip()
                if not line:
                    continue

                annotation_detail = {
                    "line_number": line_num + 1,
                    "raw_line": line,
                    "valid": True,
                    "errors": []
                }

                parts = line.split()

                # 基本格式验证
                format_valid = self.strategies["basic_format"].validate(
                    parts=parts, line_num=line_num
                )
                if not format_valid:
                    annotation_detail["valid"] = False
                    annotation_detail["errors"].append(
                        self.strategies["basic_format"].error_message
                    )
                    validation_result["annotation_details"].append(annotation_detail)
                    continue

                # 解析数值
                try:
                    class_id = int(parts[0])
                    x_center = float(parts[1])
                    y_center = float(parts[2])
                    width = float(parts[3])
                    height = float(parts[4])

                    annotation_detail.update({
                        "class_id": class_id,
                        "x_center": x_center,
                        "y_center": y_center,
                        "width": width,
                        "height": height
                    })

                    # 执行各个验证策略
                    self._execute_validations(
                        annotation_detail, class_id, x_center, y_center,
                        width, height, image_width, image_height
                    )

                    if annotation_detail["valid"]:
                        validation_result["valid_annotations"] += 1
                        validation_result["class_ids"].add(class_id)
                    else:
                        validation_result["valid"] = False
                        validation_result["errors"].extend(annotation_detail["errors"])

                except Exception as e:
                    annotation_detail["valid"] = False
                    annotation_detail["errors"].append(f"数值解析错误: {str(e)}")
                    validation_result["valid"] = False
                    validation_result["errors"].extend(annotation_detail["errors"])

                validation_result["annotation_details"].append(annotation_detail)

        except Exception as e:
            validation_result["valid"] = False
            validation_result["errors"].append(f"读取文件出错: {str(e)}")

        return validation_result

    def _execute_validations(
        self,
        annotation_detail: Dict[str, Any],
        class_id: int,
        x_center: float,
        y_center: float,
        width: float,
        height: float,
        image_width: Optional[int] = None,
        image_height: Optional[int] = None
    ):
        """执行所有验证策略

        Args:
            annotation_detail: 标注详情
            class_id: 类别ID
            x_center: x中心坐标
            y_center: y中心坐标
            width: 宽度
            height: 高度
            image_width: 图片宽度
            image_height: 图片高度
        """
        # 类别ID验证
        if not self.strategies["class_id"].validate(class_id=class_id):
            annotation_detail["valid"] = False
            annotation_detail["errors"].append(self.strategies["class_id"].error_message)

        # 坐标范围验证
        if not self.strategies["coordinate_range"].validate(
            x_center=x_center, y_center=y_center,
            width=width, height=height
        ):
            annotation_detail["valid"] = False
            annotation_detail["errors"].append(
                self.strategies["coordinate_range"].error_message
            )

        # 尺寸验证
        if not self.strategies["annotation_size"].validate(
            width=width, height=height
        ):
            annotation_detail["valid"] = False
            annotation_detail["errors"].append(
                self.strategies["annotation_size"].error_message
            )

        # 重复验证
        if not self.strategies["duplicate"].validate(
            class_id=class_id, x_center=x_center, y_center=y_center,
            width=width, height=height
        ):
            annotation_detail["warnings"] = [self.strategies["duplicate"].error_message]

        # 像素级验证
        if image_width and image_height:
            self._validate_pixel_coordinates(
                annotation_detail, x_center, y_center, width, height,
                image_width, image_height
            )

    def _validate_pixel_coordinates(
        self,
        annotation_detail: Dict[str, Any],
        x_center: float,
        y_center: float,
        width: float,
        height: float,
        image_width: int,
        image_height: int
    ):
        """验证像素坐标

        Args:
            annotation_detail: 标注详情
            x_center: x中心坐标
            y_center: y中心坐标
            width: 宽度
            height: 高度
            image_width: 图片宽度
            image_height: 图片高度
        """
        pixel_x = int(x_center * image_width)
        pixel_y = int(y_center * image_height)
        pixel_width = int(width * image_width)
        pixel_height = int(height * image_height)

        if pixel_width < 1 or pixel_height < 1:
            annotation_detail.setdefault("warnings", []).append(
                f"标注框像素尺寸过小: {pixel_width}x{pixel_height}"
            )

        annotation_detail["pixel_coordinates"] = {
            "x": pixel_x,
            "y": pixel_y,
            "width": pixel_width,
            "height": pixel_height
        }
