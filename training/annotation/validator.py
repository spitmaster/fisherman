#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
标注验证模块

提供全面的标注数据验证功能，包括格式验证、数值范围检查、完整性验证等。
支持多种验证规则和详细的错误报告。
"""

import os
import re
import logging
import json
from typing import Dict, List, Tuple, Optional, Any
from pathlib import Path

logger = logging.getLogger(__name__)


class AnnotationValidator:
    """标注验证器类
    
    提供完整的标注验证功能，支持多种验证规则和配置。
    """
    
    def __init__(self, max_classes: int = 1000, min_annotation_size: float = 0.001):
        """初始化验证器
        
        Args:
            max_classes: 最大类别数量
            min_annotation_size: 最小标注尺寸（相对图像尺寸）
        """
        self.max_classes = max_classes
        self.min_annotation_size = min_annotation_size
        
        # 验证规则配置
        self.validation_rules = {
            "file_format": {
                "enabled": True,
                "description": "文件格式验证",
                "error_message": "标注文件格式错误"
            },
            "coordinate_range": {
                "enabled": True,
                "description": "坐标范围验证",
                "error_message": "坐标超出有效范围 [0, 1]"
            },
            "annotation_size": {
                "enabled": True,
                "description": "标注尺寸验证",
                "error_message": "标注尺寸过小"
            },
            "class_id_range": {
                "enabled": True,
                "description": "类别ID范围验证",
                "error_message": "类别ID超出有效范围"
            },
            "duplicate_annotations": {
                "enabled": True,
                "description": "重复标注检测",
                "error_message": "检测到重复的标注"
            }
        }
    
    def validate_single_annotation_file(self, label_path: str, image_filename: str = "", 
                                       image_width: int = None, image_height: int = None) -> Dict[str, Any]:
        """验证单个标注文件
        
        Args:
            label_path: 标注文件路径
            image_filename: 图片文件名（用于错误信息）
            image_width: 图片宽度（像素）
            image_height: 图片高度（像素）
            
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
                if not self._validate_basic_format(parts, line_num, image_filename, annotation_detail):
                    validation_result["valid_annotations"] += 1
                    validation_result["annotation_details"].append(annotation_detail)
                    continue
                
                # 数值解析和验证
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
                    
                    # 执行各种验证
                    self._validate_class_id(class_id, annotation_detail)
                    self._validate_coordinate_range(x_center, y_center, width, height, annotation_detail)
                    self._validate_annotation_size(width, height, annotation_detail)
                    
                    # 如果提供了图片尺寸，进行像素级验证
                    if image_width and image_height:
                        self._validate_pixel_coordinates(x_center, y_center, width, height, 
                                                       image_width, image_height, annotation_detail)
                    
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
            
            # 检查类别数量
            if len(validation_result["class_ids"]) > self.max_classes:
                validation_result["warnings"].append(f"类别数量过多: {len(validation_result['class_ids'])} > {self.max_classes}")
            
            # 检查重复标注
            self._check_duplicate_annotations(validation_result)
            
        except Exception as e:
            validation_result["valid"] = False
            validation_result["errors"].append(f"读取文件出错: {str(e)}")
        
        return validation_result
    
    def _validate_basic_format(self, parts: List[str], line_num: int, image_filename: str, 
                              annotation_detail: Dict[str, Any]) -> bool:
        """验证基本格式
        
        Args:
            parts: 分割后的行数据
            line_num: 行号
            image_filename: 图片文件名
            annotation_detail: 标注详情字典
            
        Returns:
            是否通过基本格式验证
        """
        if len(parts) < 5:
            annotation_detail["valid"] = False
            annotation_detail["errors"].append(
                f"{image_filename or '未知文件'}: 第 {line_num + 1} 行字段数量不足 (需要5个，实际{len(parts)}个)"
            )
            return False
        
        # 验证字段数量一致性
        if len(parts) > 5:
            annotation_detail["warnings"] = [f"第 {line_num + 1} 行包含额外字段，将被忽略"]
        
        return True
    
    def _validate_class_id(self, class_id: int, annotation_detail: Dict[str, Any]):
        """验证类别ID
        
        Args:
            class_id: 类别ID
            annotation_detail: 标注详情字典
        """
        if not self.validation_rules["class_id_range"]["enabled"]:
            return
        
        if class_id < 0:
            annotation_detail["valid"] = False
            annotation_detail["errors"].append(
                f"类别ID {class_id} 不能为负数"
            )
        elif class_id >= self.max_classes:
            annotation_detail["valid"] = False
            annotation_detail["errors"].append(
                f"类别ID {class_id} 超出最大限制 {self.max_classes - 1}"
            )
    
    def _validate_coordinate_range(self, x_center: float, y_center: float, 
                                 width: float, height: float, annotation_detail: Dict[str, Any]):
        """验证坐标范围
        
        Args:
            x_center: x中心坐标
            y_center: y中心坐标
            width: 宽度
            height: 高度
            annotation_detail: 标注详情字典
        """
        if not self.validation_rules["coordinate_range"]["enabled"]:
            return
        
        errors = []
        
        # 验证中心坐标
        if not (0 <= x_center <= 1):
            errors.append(f"x_center {x_center:.6f} 超出范围 [0, 1]")
        if not (0 <= y_center <= 1):
            errors.append(f"y_center {y_center:.6f} 超出范围 [0, 1]")
        
        # 验证边界
        x_min = x_center - width/2
        x_max = x_center + width/2
        y_min = y_center - height/2
        y_max = y_center + height/2
        
        if x_min < 0 or x_max > 1:
            errors.append(f"标注框在x轴上超出图像边界: [{x_min:.6f}, {x_max:.6f}]")
        if y_min < 0 or y_max > 1:
            errors.append(f"标注框在y轴上超出图像边界: [{y_min:.6f}, {y_max:.6f}]")
        
        if errors:
            annotation_detail["valid"] = False
            annotation_detail["errors"].extend(errors)
    
    def _validate_annotation_size(self, width: float, height: float, annotation_detail: Dict[str, Any]):
        """验证标注尺寸
        
        Args:
            width: 宽度
            height: 高度
            annotation_detail: 标注详情字典
        """
        if not self.validation_rules["annotation_size"]["enabled"]:
            return
        
        area = width * height
        
        if area < self.min_annotation_size:
            annotation_detail["valid"] = False
            annotation_detail["errors"].append(
                f"标注尺寸过小: {area:.6f} < {self.min_annotation_size}"
            )
    
    def _validate_pixel_coordinates(self, x_center: float, y_center: float, 
                                  width: float, height: float, 
                                  image_width: int, image_height: int, 
                                  annotation_detail: Dict[str, Any]):
        """验证像素坐标
        
        Args:
            x_center: x中心坐标
            y_center: y中心坐标
            width: 宽度
            height: 高度
            image_width: 图片宽度
            image_height: 图片高度
            annotation_detail: 标注详情字典
        """
        # 计算像素坐标
        pixel_x = int(x_center * image_width)
        pixel_y = int(y_center * image_height)
        pixel_width = int(width * image_width)
        pixel_height = int(height * image_height)
        
        # 检查像素级有效性
        if pixel_width < 1 or pixel_height < 1:
            annotation_detail["warnings"].append(
                f"标注框像素尺寸过小: {pixel_width}x{pixel_height}"
            )
        
        annotation_detail["pixel_coordinates"] = {
            "x": pixel_x,
            "y": pixel_y,
            "width": pixel_width,
            "height": pixel_height
        }
    
    def _check_duplicate_annotations(self, validation_result: Dict[str, Any]):
        """检查重复标注
        
        Args:
            validation_result: 验证结果字典
        """
        if not self.validation_rules["duplicate_annotations"]["enabled"]:
            return
        
        annotations = []
        for detail in validation_result["annotation_details"]:
            if detail.get("valid", False):
                annotation_key = (
                    detail.get("class_id"),
                    detail.get("x_center"),
                    detail.get("y_center"),
                    detail.get("width"),
                    detail.get("height")
                )
                annotations.append(annotation_key)
        
        if len(annotations) != len(set(annotations)):
            validation_result["warnings"].append("检测到可能的重复标注")
    
    def enable_validation_rule(self, rule_name: str, enabled: bool = True):
        """启用或禁用验证规则
        
        Args:
            rule_name: 规则名称
            enabled: 是否启用
        """
        if rule_name in self.validation_rules:
            self.validation_rules[rule_name]["enabled"] = enabled
    
    def get_validation_rules(self) -> Dict[str, Any]:
        """获取验证规则配置
        
        Returns:
            验证规则配置字典
        """
        return self.validation_rules


    def validate_dataset_annotations(self, task_dir: str, validate_split: str = "train") -> Dict[str, Any]:
        """验证整个数据集的标注数据
        
        Args:
            task_dir: 任务目录
            validate_split: 验证的数据集划分 (train/val/test)
            
        Returns:
            验证结果字典
        """
        image_dir = os.path.join(task_dir, f"dataset/images/{validate_split}")
        label_dir = os.path.join(task_dir, f"dataset/labels/{validate_split}")
        
        if not os.path.exists(image_dir):
            return {
                "valid": False,
                "split": validate_split,
                "total_images": 0,
                "annotated_images": 0,
                "valid_annotations": 0,
                "total_annotations": 0,
                "errors": [f"图片目录不存在: {image_dir}"],
                "warnings": [],
                "file_validation_results": []
            }
        
        if not os.path.exists(label_dir):
            return {
                "valid": False,
                "split": validate_split,
                "total_images": 0,
                "annotated_images": 0,
                "valid_annotations": 0,
                "total_annotations": 0,
                "errors": [f"标注目录不存在: {label_dir}"],
                "warnings": [],
                "file_validation_results": []
            }
        
        image_files = [f for f in os.listdir(image_dir) 
                       if f.lower().endswith(('.jpg', '.jpeg', '.png', '.bmp', '.tiff', '.tif'))]
        
        dataset_result = {
            "valid": True,
            "split": validate_split,
            "total_images": len(image_files),
            "annotated_images": 0,
            "valid_annotations": 0,
            "total_annotations": 0,
            "errors": [],
            "warnings": [],
            "class_distribution": {},
            "file_validation_results": []
        }
        
        # 获取图片尺寸信息（如果可能）
        image_sizes = self._get_image_sizes(image_dir, image_files)
        
        for image_filename in image_files:
            label_filename = os.path.splitext(image_filename)[0] + ".txt"
            label_path = os.path.join(label_dir, label_filename)
            
            image_width, image_height = image_sizes.get(image_filename, (None, None))
            
            if os.path.exists(label_path):
                dataset_result["annotated_images"] += 1
                
                file_result = self.validate_single_annotation_file(
                    label_path, image_filename, image_width, image_height
                )
                
                dataset_result["file_validation_results"].append(file_result)
                
                if not file_result["valid"]:
                    dataset_result["valid"] = False
                    dataset_result["errors"].extend(file_result["errors"])
                
                dataset_result["valid_annotations"] += file_result["valid_annotations"]
                dataset_result["total_annotations"] += file_result["total_annotations"]
                
                # 更新类别分布
                for class_id in file_result["class_ids"]:
                    if class_id not in dataset_result["class_distribution"]:
                        dataset_result["class_distribution"][class_id] = 0
                    dataset_result["class_distribution"][class_id] += 1
            else:
                # 没有标注文件的图片
                dataset_result["warnings"].append(f"图片 {image_filename} 没有对应的标注文件")
        
        # 数据集级别验证
        self._validate_dataset_level(dataset_result)
        
        return dataset_result
    
    def _get_image_sizes(self, image_dir: str, image_files: List[str]) -> Dict[str, Tuple[int, int]]:
        """获取图片尺寸信息
        
        Args:
            image_dir: 图片目录
            image_files: 图片文件列表
            
        Returns:
            图片文件名到尺寸的映射
        """
        image_sizes = {}
        
        try:
            from PIL import Image
            
            for image_filename in image_files:
                image_path = os.path.join(image_dir, image_filename)
                try:
                    with Image.open(image_path) as img:
                        image_sizes[image_filename] = img.size
                except Exception as e:
                    logger.warning(f"无法获取图片尺寸 {image_filename}: {str(e)}")
                    image_sizes[image_filename] = (None, None)
                    
        except ImportError:
            logger.warning("PIL库未安装，无法获取图片尺寸信息")
            # 如果没有PIL，返回空尺寸
            for image_filename in image_files:
                image_sizes[image_filename] = (None, None)
        
        return image_sizes
    
    def _validate_dataset_level(self, dataset_result: Dict[str, Any]):
        """执行数据集级别的验证
        
        Args:
            dataset_result: 数据集验证结果
        """
        # 检查标注比例
        if dataset_result["total_images"] > 0:
            annotation_ratio = dataset_result["annotated_images"] / dataset_result["total_images"]
            if annotation_ratio < 0.1:  # 10% 阈值
                dataset_result["warnings"].append(
                    f"标注比例过低: {annotation_ratio:.1%} ({dataset_result['annotated_images']}/{dataset_result['total_images']})"
                )
        
        # 检查类别分布
        if dataset_result["class_distribution"]:
            total_annotations = sum(dataset_result["class_distribution"].values())
            
            # 检查类别平衡性
            if len(dataset_result["class_distribution"]) > 1:
                class_counts = list(dataset_result["class_distribution"].values())
                max_count = max(class_counts)
                min_count = min(class_counts)
                
                if min_count > 0:
                    imbalance_ratio = max_count / min_count
                    if imbalance_ratio > 10:  # 10倍阈值
                        dataset_result["warnings"].append(
                            f"类别分布不平衡: 最大类别是最小类别的 {imbalance_ratio:.1f} 倍"
                        )
        
        # 检查有效标注比例
        if dataset_result["total_annotations"] > 0:
            valid_ratio = dataset_result["valid_annotations"] / dataset_result["total_annotations"]
            if valid_ratio < 0.9:  # 90% 阈值
                dataset_result["warnings"].append(
                    f"有效标注比例较低: {valid_ratio:.1%} ({dataset_result['valid_annotations']}/{dataset_result['total_annotations']})"
                )


    def get_annotation_statistics(self, task_dir: str, split: str = "train") -> Dict[str, Any]:
        """获取数据集标注统计信息
        
        Args:
            task_dir: 任务目录
            split: 数据集划分 (train/val/test)
            
        Returns:
            统计信息字典
        """
        # 先进行验证以获取详细信息
        validation_result = self.validate_dataset_annotations(task_dir, split)
        
        statistics = {
            "split": split,
            "total_images": validation_result["total_images"],
            "annotated_images": validation_result["annotated_images"],
            "total_annotations": validation_result["total_annotations"],
            "valid_annotations": validation_result["valid_annotations"],
            "avg_annotations_per_image": 0,
            "max_annotations_per_image": 0,
            "min_annotations_per_image": 0,
            "annotations_per_image": [],
            "class_distribution": validation_result["class_distribution"],
            "annotation_quality": {
                "valid_ratio": 0.0,
                "annotation_ratio": 0.0
            },
            "file_stats": {
                "valid_files": 0,
                "invalid_files": 0,
                "files_with_errors": []
            }
        }
        
        # 计算每张图片的标注数量
        for file_result in validation_result["file_validation_results"]:
            if file_result["total_annotations"] > 0:
                statistics["annotations_per_image"].append(file_result["total_annotations"])
                
                if file_result["valid"]:
                    statistics["file_stats"]["valid_files"] += 1
                else:
                    statistics["file_stats"]["invalid_files"] += 1
                    statistics["file_stats"]["files_with_errors"].append({
                        "filename": file_result["image_filename"],
                        "errors": file_result["errors"][:5]  # 只保留前5个错误
                    })
        
        # 计算统计指标
        if statistics["annotated_images"] > 0:
            statistics["avg_annotations_per_image"] = statistics["total_annotations"] / statistics["annotated_images"]
            
            if statistics["annotations_per_image"]:
                statistics["max_annotations_per_image"] = max(statistics["annotations_per_image"])
                statistics["min_annotations_per_image"] = min(statistics["annotations_per_image"])
        
        if statistics["total_annotations"] > 0:
            statistics["annotation_quality"]["valid_ratio"] = statistics["valid_annotations"] / statistics["total_annotations"]
        
        if statistics["total_images"] > 0:
            statistics["annotation_quality"]["annotation_ratio"] = statistics["annotated_images"] / statistics["total_images"]
        
        return statistics


# 保持向后兼容的函数
def validate_single_annotation_file(label_path, image_filename=""):
    """验证单个标注文件（兼容性函数）
    
    Args:
        label_path: 标注文件路径
        image_filename: 图片文件名
        
    Returns:
        (valid, errors) - valid为布尔值，errors为错误列表
    """
    validator = AnnotationValidator()
    result = validator.validate_single_annotation_file(label_path, image_filename)
    return result["valid"], result["errors"]


def validate_dataset_annotations(task_dir):
    """验证整个数据集的标注数据（兼容性函数）
    
    Args:
        task_dir: 任务目录
        
    Returns:
        验证结果字典
    """
    validator = AnnotationValidator()
    return validator.validate_dataset_annotations(task_dir)


def get_annotation_statistics(task_dir):
    """获取数据集标注统计信息（兼容性函数）
    
    Args:
        task_dir: 任务目录
        
    Returns:
        统计信息字典
    """
    validator = AnnotationValidator()
    return validator.get_annotation_statistics(task_dir)