#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
YOLO格式转换模块

提供全面的YOLO格式转换、验证和批量处理功能。
支持多种数据格式的导入导出和格式转换。
"""

import os
import json
import yaml
import logging
import numpy as np
from typing import List, Tuple, Dict, Any, Optional, Union
from pathlib import Path
from enum import Enum

logger = logging.getLogger(__name__)


class YOLOFormat(Enum):
    """YOLO格式类型枚举"""
    STANDARD = "standard"        # 标准YOLO格式
    EXTENDED = "extended"        # 扩展格式（包含置信度等）
    CUSTOM = "custom"            # 自定义格式


class YOLOFormatter:
    """YOLO格式转换器
    
    提供完整的YOLO格式转换、验证和批量处理功能。
    """
    
    def __init__(self, format_type: YOLOFormat = YOLOFormat.STANDARD, 
                 max_classes: int = 1000, normalize_coordinates: bool = True):
        """初始化格式转换器
        
        Args:
            format_type: 格式类型
            max_classes: 最大类别数量
            normalize_coordinates: 是否归一化坐标
        """
        self.format_type = format_type
        self.max_classes = max_classes
        self.normalize_coordinates = normalize_coordinates
        
        # 格式配置
        self.format_configs = {
            YOLOFormat.STANDARD.value: {
                "fields": ["class_id", "x_center", "y_center", "width", "height"],
                "separator": " ",
                "precision": 6
            },
            YOLOFormat.EXTENDED.value: {
                "fields": ["class_id", "x_center", "y_center", "width", "height", "confidence"],
                "separator": " ",
                "precision": 6
            },
            YOLOFormat.CUSTOM.value: {
                "fields": ["class_id", "x_center", "y_center", "width", "height"],
                "separator": " ",
                "precision": 6
            }
        }
    
    def convert_bbox_to_yolo(self, image_shape: Tuple[int, int], bbox: Tuple[int, int, int, int], 
                            class_id: int = 0, confidence: float = None) -> List[float]:
        """将边界框坐标转换为YOLO格式
        
        Args:
            image_shape: 图片尺寸 (height, width)
            bbox: 边界框坐标 (x1, y1, x2, y2)
            class_id: 类别ID
            confidence: 置信度（可选）
            
        Returns:
            YOLO格式坐标列表
        """
        img_height, img_width = image_shape
        x1, y1, x2, y2 = bbox
        
        # 验证边界框
        if not self._validate_bbox_coordinates(x1, y1, x2, y2, img_width, img_height):
            raise ValueError("边界框坐标无效")
        
        # 计算YOLO格式坐标
        if self.normalize_coordinates:
            x_center = (x1 + x2) / 2 / img_width
            y_center = (y1 + y2) / 2 / img_height
            width = (x2 - x1) / img_width
            height = (y2 - y1) / img_height
        else:
            x_center = (x1 + x2) / 2
            y_center = (y1 + y2) / 2
            width = x2 - x1
            height = y2 - y1
        
        # 构建结果
        result = [class_id, x_center, y_center, width, height]
        
        # 添加置信度（如果支持且提供）
        if self.format_type == YOLOFormat.EXTENDED and confidence is not None:
            result.append(confidence)
        
        return result
    
    def convert_yolo_to_bbox(self, image_shape: Tuple[int, int], yolo_annotation: List[float], 
                           normalize_coordinates: bool = None) -> Tuple[int, int, int, int]:
        """将YOLO格式坐标转换为边界框坐标
        
        Args:
            image_shape: 图片尺寸 (height, width)
            yolo_annotation: YOLO格式坐标
            normalize_coordinates: 是否归一化坐标（覆盖默认设置）
            
        Returns:
            边界框坐标元组 (x1, y1, x2, y2)
        """
        img_height, img_width = image_shape
        
        # 验证YOLO标注
        if not self._validate_yolo_annotation(yolo_annotation):
            raise ValueError("YOLO标注格式无效")
        
        # 确定是否归一化
        use_normalized = normalize_coordinates if normalize_coordinates is not None else self.normalize_coordinates
        
        # 提取坐标
        class_id = int(yolo_annotation[0])
        x_center = yolo_annotation[1]
        y_center = yolo_annotation[2]
        width = yolo_annotation[3]
        height = yolo_annotation[4]
        
        # 计算边界框坐标
        if use_normalized:
            x1 = int((x_center - width / 2) * img_width)
            y1 = int((y_center - height / 2) * img_height)
            x2 = int((x_center + width / 2) * img_width)
            y2 = int((y_center + height / 2) * img_height)
        else:
            x1 = int(x_center - width / 2)
            y1 = int(y_center - height / 2)
            x2 = int(x_center + width / 2)
            y2 = int(y_center + height / 2)
        
        # 确保坐标在有效范围内
        x1 = max(0, min(x1, img_width - 1))
        y1 = max(0, min(y1, img_height - 1))
        x2 = max(0, min(x2, img_width - 1))
        y2 = max(0, min(y2, img_height - 1))
        
        return (x1, y1, x2, y2)
    
    def convert_annotations_to_yolo_format(self, image_shape: Tuple[int, int], 
                                        annotations: List[Tuple[Tuple[int, int, int, int], int]],
                                        confidences: List[float] = None) -> List[List[float]]:
        """批量转换标注为YOLO格式
        
        Args:
            image_shape: 图片尺寸
            annotations: 标注列表，每个元素为 (bbox, class_id)
            confidences: 置信度列表（可选）
            
        Returns:
            YOLO格式标注列表
        """
        yolo_annotations = []
        
        for i, (bbox, class_id) in enumerate(annotations):
            confidence = confidences[i] if confidences and i < len(confidences) else None
            
            try:
                yolo_annotation = self.convert_bbox_to_yolo(image_shape, bbox, class_id, confidence)
                yolo_annotations.append(yolo_annotation)
            except Exception as e:
                logger.warning(f"转换标注失败: {str(e)}")
        
        return yolo_annotations
    
    def convert_yolo_to_annotations(self, image_shape: Tuple[int, int], 
                                  yolo_annotations: List[List[float]]) -> List[Tuple[Tuple[int, int, int, int], int]]:
        """批量转换YOLO格式为标注
        
        Args:
            image_shape: 图片尺寸
            yolo_annotations: YOLO格式标注列表
            
        Returns:
            标注列表，每个元素为 (bbox, class_id)
        """
        annotations = []
        
        for yolo_annotation in yolo_annotations:
            try:
                bbox = self.convert_yolo_to_bbox(image_shape, yolo_annotation)
                class_id = int(yolo_annotation[0])
                annotations.append((bbox, class_id))
            except Exception as e:
                logger.warning(f"转换YOLO标注失败: {str(e)}")
        
        return annotations
    
    def save_yolo_annotations_to_file(self, file_path: str, yolo_annotations: List[List[float]], 
                                     classes: List[str] = None) -> bool:
        """保存YOLO标注到文件
        
        Args:
            file_path: 文件路径
            yolo_annotations: YOLO格式标注列表
            classes: 类别名称列表（用于生成注释）
            
        Returns:
            是否保存成功
        """
        try:
            # 确保目录存在
            os.makedirs(os.path.dirname(file_path), exist_ok=True)
            
            with open(file_path, 'w', encoding='utf-8') as f:
                # 写入注释（如果有类别信息）
                if classes:
                    f.write("# YOLO格式标注文件\n")
                    f.write("# 格式: class_id x_center y_center width height\n")
                    f.write("# 类别映射:\n")
                    for i, class_name in enumerate(classes):
                        f.write(f"# {i}: {class_name}\n")
                    f.write("\n")
                
                # 写入标注数据
                config = self.format_configs[self.format_type.value]
                precision = config["precision"]
                separator = config["separator"]
                
                for annotation in yolo_annotations:
                    # 格式化每个字段
                    formatted_fields = []
                    for field in annotation:
                        if isinstance(field, float):
                            formatted_fields.append(f"{field:.{precision}f}")
                        else:
                            formatted_fields.append(str(field))
                    
                    # 写入一行
                    line = separator.join(formatted_fields)
                    f.write(line + "\n")
            
            logger.info(f"YOLO标注已保存到: {file_path}")
            return True
            
        except Exception as e:
            logger.error(f"保存YOLO标注失败: {str(e)}")
            return False
    
    def load_yolo_annotations_from_file(self, file_path: str) -> List[List[float]]:
        """从文件加载YOLO标注
        
        Args:
            file_path: 文件路径
            
        Returns:
            YOLO格式标注列表
        """
        yolo_annotations = []
        
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                lines = f.readlines()
            
            for line_num, line in enumerate(lines):
                line = line.strip()
                
                # 跳过空行和注释行
                if not line or line.startswith('#'):
                    continue
                
                # 解析标注行
                try:
                    fields = line.split()
                    
                    # 验证字段数量
                    expected_fields = len(self.format_configs[self.format_type.value]["fields"])
                    if len(fields) < expected_fields:
                        logger.warning(f"第 {line_num + 1} 行字段数量不足: {len(fields)} < {expected_fields}")
                        continue
                    
                    # 转换字段类型
                    annotation = []
                    for i, field in enumerate(fields[:expected_fields]):
                        if i == 0:  # class_id
                            annotation.append(int(field))
                        else:  # 坐标值
                            annotation.append(float(field))
                    
                    # 验证标注格式
                    if self._validate_yolo_annotation(annotation):
                        yolo_annotations.append(annotation)
                    else:
                        logger.warning(f"第 {line_num + 1} 行标注格式无效")
                        
                except Exception as e:
                    logger.warning(f"解析第 {line_num + 1} 行失败: {str(e)}")
            
            logger.info(f"从文件加载了 {len(yolo_annotations)} 个YOLO标注: {file_path}")
            
        except Exception as e:
            logger.error(f"加载YOLO标注失败: {str(e)}")
        
        return yolo_annotations
    
    def convert_to_other_format(self, yolo_annotations: List[List[float]], 
                              target_format: str, classes: List[str] = None) -> Dict[str, Any]:
        """将YOLO格式转换为其他格式
        
        Args:
            yolo_annotations: YOLO格式标注列表
            target_format: 目标格式 (coco, pascal_voc, etc.)
            classes: 类别名称列表
            
        Returns:
            转换后的标注数据
        """
        if target_format.lower() == "coco":
            return self._convert_to_coco_format(yolo_annotations, classes)
        elif target_format.lower() == "pascal_voc":
            return self._convert_to_pascal_voc_format(yolo_annotations, classes)
        else:
            raise ValueError(f"不支持的格式: {target_format}")
    
    def _convert_to_coco_format(self, yolo_annotations: List[List[float]], 
                              classes: List[str]) -> Dict[str, Any]:
        """转换为COCO格式
        
        Args:
            yolo_annotations: YOLO格式标注
            classes: 类别列表
            
        Returns:
            COCO格式数据
        """
        # 这里实现COCO格式转换逻辑
        # 返回COCO格式的字典
        return {
            "info": {"description": "Converted from YOLO format"},
            "images": [],
            "annotations": [],
            "categories": [{"id": i, "name": name} for i, name in enumerate(classes)] if classes else []
        }
    
    def _convert_to_pascal_voc_format(self, yolo_annotations: List[List[float]], 
                                    classes: List[str]) -> Dict[str, Any]:
        """转换为Pascal VOC格式
        
        Args:
            yolo_annotations: YOLO格式标注
            classes: 类别列表
            
        Returns:
            Pascal VOC格式数据
        """
        # 这里实现Pascal VOC格式转换逻辑
        # 返回Pascal VOC格式的字典
        return {
            "annotation": {
                "folder": "images",
                "filename": "",
                "size": {"width": 0, "height": 0, "depth": 3},
                "objects": []
            }
        }


def convert_yolo_to_bbox(image, yolo_annotation):
    """将YOLO格式坐标转换为边界框坐标
    
    Args:
        image: 图片（OpenCV格式）
        yolo_annotation: YOLO格式坐标 [class_id, x_center, y_center, width, height]
        
    Returns:
        边界框坐标元组 (x1, y1, x2, y2)
    """
    img_height, img_width = image.shape[:2]
    
    class_id, x_center, y_center, width, height = yolo_annotation
    
    # 计算边界框坐标
    x1 = int((x_center - width / 2) * img_width)
    y1 = int((y_center - height / 2) * img_height)
    x2 = int((x_center + width / 2) * img_width)
    y2 = int((y_center + height / 2) * img_height)
    
    return (x1, y1, x2, y2)


    def _validate_yolo_annotation(self, annotation: List[float]) -> bool:
        """验证YOLO格式标注的合法性
        
        Args:
            annotation: YOLO格式标注列表
            
        Returns:
            是否有效
        """
        config = self.format_configs[self.format_type.value]
        expected_fields = len(config["fields"])
        
        if len(annotation) < expected_fields:
            return False
        
        try:
            class_id = int(annotation[0])
            
            # 验证类别ID
            if class_id < 0 or class_id >= self.max_classes:
                return False
            
            # 验证坐标值
            x_center = annotation[1]
            y_center = annotation[2]
            width = annotation[3]
            height = annotation[4]
            
            # 验证坐标范围
            if not (0 <= x_center <= 1):
                return False
            if not (0 <= y_center <= 1):
                return False
            if not (0 < width <= 1):
                return False
            if not (0 < height <= 1):
                return False
            
            # 验证边界框有效性
            x_min = x_center - width / 2
            x_max = x_center + width / 2
            y_min = y_center - height / 2
            y_max = y_center + height / 2
            
            if x_min < 0 or x_max > 1 or y_min < 0 or y_max > 1:
                return False
            
            # 验证置信度（如果适用）
            if self.format_type == YOLOFormat.EXTENDED and len(annotation) > 5:
                confidence = annotation[5]
                if not (0 <= confidence <= 1):
                    return False
            
            return True
            
        except (ValueError, TypeError, IndexError):
            return False
    
    def _validate_bbox_coordinates(self, x1: int, y1: int, x2: int, y2: int, 
                                 img_width: int, img_height: int) -> bool:
        """验证边界框坐标的合法性
        
        Args:
            x1, y1, x2, y2: 边界框坐标
            img_width, img_height: 图片尺寸
            
        Returns:
            是否有效
        """
        # 检查坐标范围
        if x1 < 0 or y1 < 0 or x2 < 0 or y2 < 0:
            return False
        
        if x1 >= img_width or y1 >= img_height or x2 >= img_width or y2 >= img_height:
            return False
        
        # 检查坐标顺序
        if x1 >= x2 or y1 >= y2:
            return False
        
        # 检查边界框尺寸
        if (x2 - x1) < 1 or (y2 - y1) < 1:
            return False
        
        return True
    
    def validate_yolo_file(self, file_path: str) -> Dict[str, Any]:
        """验证YOLO格式文件
        
        Args:
            file_path: 文件路径
            
        Returns:
            验证结果字典
        """
        validation_result = {
            "valid": True,
            "file_path": file_path,
            "total_annotations": 0,
            "valid_annotations": 0,
            "errors": [],
            "warnings": [],
            "class_distribution": {}
        }
        
        if not os.path.exists(file_path):
            validation_result["valid"] = False
            validation_result["errors"].append("文件不存在")
            return validation_result
        
        try:
            yolo_annotations = self.load_yolo_annotations_from_file(file_path)
            validation_result["total_annotations"] = len(yolo_annotations)
            
            for annotation in yolo_annotations:
                if self._validate_yolo_annotation(annotation):
                    validation_result["valid_annotations"] += 1
                    
                    # 统计类别分布
                    class_id = int(annotation[0])
                    if class_id not in validation_result["class_distribution"]:
                        validation_result["class_distribution"][class_id] = 0
                    validation_result["class_distribution"][class_id] += 1
                else:
                    validation_result["valid"] = False
                    validation_result["errors"].append(f"无效标注: {annotation}")
            
            # 检查有效标注比例
            if validation_result["total_annotations"] > 0:
                valid_ratio = validation_result["valid_annotations"] / validation_result["total_annotations"]
                if valid_ratio < 0.9:
                    validation_result["warnings"].append(
                        f"有效标注比例较低: {valid_ratio:.1%}"
                    )
            
        except Exception as e:
            validation_result["valid"] = False
            validation_result["errors"].append(f"文件读取失败: {str(e)}")
        
        return validation_result
    
    def get_format_info(self) -> Dict[str, Any]:
        """获取格式信息
        
        Returns:
            格式信息字典
        """
        config = self.format_configs[self.format_type.value]
        
        return {
            "format_type": self.format_type.value,
            "fields": config["fields"],
            "separator": config["separator"],
            "precision": config["precision"],
            "max_classes": self.max_classes,
            "normalize_coordinates": self.normalize_coordinates
        }
    
    def set_format_type(self, format_type: YOLOFormat):
        """设置格式类型
        
        Args:
            format_type: 格式类型
        """
        self.format_type = format_type
    
    def set_custom_format(self, fields: List[str], separator: str = " ", precision: int = 6):
        """设置自定义格式
        
        Args:
            fields: 字段列表
            separator: 分隔符
            precision: 精度
        """
        self.format_type = YOLOFormat.CUSTOM
        self.format_configs[YOLOFormat.CUSTOM.value] = {
            "fields": fields,
            "separator": separator,
            "precision": precision
        }


# 保持向后兼容的函数
def convert_bbox_to_yolo(image, bbox, class_id=0):
    """将边界框坐标转换为YOLO格式（兼容性函数）
    
    Args:
        image: 图片
        bbox: 边界框坐标
        class_id: 类别ID
        
    Returns:
        YOLO格式坐标列表
    """
    formatter = YOLOFormatter()
    img_height, img_width = image.shape[:2]
    return formatter.convert_bbox_to_yolo((img_height, img_width), bbox, class_id)


def convert_yolo_to_bbox(image, yolo_annotation):
    """将YOLO格式坐标转换为边界框坐标（兼容性函数）
    
    Args:
        image: 图片
        yolo_annotation: YOLO格式坐标
        
    Returns:
        边界框坐标元组
    """
    formatter = YOLOFormatter()
    img_height, img_width = image.shape[:2]
    return formatter.convert_yolo_to_bbox((img_height, img_width), yolo_annotation)


def validate_yolo_annotation(annotation):
    """验证YOLO格式标注的合法性（兼容性函数）
    
    Args:
        annotation: YOLO格式标注列表
        
    Returns:
        验证结果 (valid, error_message)
    """
    formatter = YOLOFormatter()
    valid = formatter._validate_yolo_annotation(annotation)
    return valid, "标注格式正确" if valid else "标注格式无效"