#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
标注验证模块

提供标注数据验证功能，确保标注格式正确和合法性。
"""

import os
import logging

logger = logging.getLogger(__name__)


def validate_single_annotation_file(label_path, image_filename=""):
    """验证单个标注文件
    
    Args:
        label_path: 标注文件路径
        image_filename: 图片文件名（用于错误信息）
        
    Returns:
        (valid, errors) - valid为布尔值，errors为错误列表
    """
    errors = []
    
    if not os.path.exists(label_path):
        return False, [f"标注文件不存在: {label_path}"]
    
    try:
        with open(label_path, "r", encoding="utf-8") as f:
            lines = f.readlines()
            
        for line_num, line in enumerate(lines):
            line = line.strip()
            if not line:
                continue
                
            parts = line.split()
            if len(parts) < 5:
                errors.append(f"{image_filename or os.path.basename(label_path)}: 第 {line_num + 1} 行字段数量不足")
                continue
            
            # 验证数值范围
            try:
                class_id = int(parts[0])
                x_center = float(parts[1])
                y_center = float(parts[2])
                width = float(parts[3])
                height = float(parts[4])
                
                # 验证坐标范围
                if not (0 <= x_center <= 1):
                    errors.append(f"{image_filename or os.path.basename(label_path)}: 第 {line_num + 1} 行 x_center {x_center} 超出范围 [0, 1]")
                if not (0 <= y_center <= 1):
                    errors.append(f"{image_filename or os.path.basename(label_path)}: 第 {line_num + 1} 行 y_center {y_center} 超出范围 [0, 1]")
                if not (0 < width <= 1):
                    errors.append(f"{image_filename or os.path.basename(label_path)}: 第 {line_num + 1} 行 width {width} 超出范围 (0, 1]")
                if not (0 < height <= 1):
                    errors.append(f"{image_filename or os.path.basename(label_path)}: 第 {line_num + 1} 行 height {height} 超出范围 (0, 1]")
                    
            except Exception as e:
                errors.append(f"{image_filename or os.path.basename(label_path)}: 第 {line_num + 1} 行格式错误 - {str(e)}")
                
    except Exception as e:
        errors.append(f"{image_filename or os.path.basename(label_path)}: 读取文件出错 - {str(e)}")
    
    return len(errors) == 0, errors


def validate_dataset_annotations(task_dir):
    """验证整个数据集的标注数据
    
    Args:
        task_dir: 任务目录
        
    Returns:
        验证结果字典
    """
    image_dir = os.path.join(task_dir, "dataset/images/train")
    label_dir = os.path.join(task_dir, "dataset/labels/train")
    
    if not os.path.exists(image_dir):
        return {
            "valid": False,
            "total_images": 0,
            "annotated_images": 0,
            "errors": [f"图片目录不存在: {image_dir}"]
        }
    
    if not os.path.exists(label_dir):
        return {
            "valid": False,
            "total_images": 0,
            "annotated_images": 0,
            "errors": [f"标注目录不存在: {label_dir}"]
        }
    
    image_files = [f for f in os.listdir(image_dir) 
                   if f.lower().endswith(('.jpg', '.jpeg', '.png', '.bmp'))]
    
    validation_result = {
        "valid": True,
        "total_images": len(image_files),
        "annotated_images": 0,
        "errors": []
    }
    
    for image_filename in image_files:
        label_filename = os.path.splitext(image_filename)[0] + ".txt"
        label_path = os.path.join(label_dir, label_filename)
        
        if os.path.exists(label_path):
            validation_result["annotated_images"] += 1
            
            valid, errors = validate_single_annotation_file(label_path, image_filename)
            if not valid:
                validation_result["valid"] = False
                validation_result["errors"].extend(errors)
    
    return validation_result


def get_annotation_statistics(task_dir):
    """获取数据集标注统计信息
    
    Args:
        task_dir: 任务目录
        
    Returns:
        统计信息字典
    """
    image_dir = os.path.join(task_dir, "dataset/images/train")
    label_dir = os.path.join(task_dir, "dataset/labels/train")
    
    if not os.path.exists(image_dir):
        return {
            "total_images": 0,
            "annotated_images": 0,
            "total_annotations": 0,
            "avg_annotations_per_image": 0,
            "annotations_per_image": [],
            "class_distribution": {}
        }
    
    image_files = [f for f in os.listdir(image_dir) 
                   if f.lower().endswith(('.jpg', '.jpeg', '.png', '.bmp'))]
    
    statistics = {
        "total_images": len(image_files),
        "annotated_images": 0,
        "total_annotations": 0,
        "annotations_per_image": [],
        "class_distribution": {}
    }
    
    for image_filename in image_files:
        label_filename = os.path.splitext(image_filename)[0] + ".txt"
        label_path = os.path.join(label_dir, label_filename)
        
        if os.path.exists(label_path):
            statistics["annotated_images"] += 1
            
            try:
                with open(label_path, "r", encoding="utf-8") as f:
                    lines = f.readlines()
                    
                annotations_count = 0
                for line in lines:
                    line = line.strip()
                    if line and len(line.split()) >= 5:
                        annotations_count += 1
                        parts = line.split()
                        class_id = int(parts[0])
                        
                        if class_id not in statistics["class_distribution"]:
                            statistics["class_distribution"][class_id] = 0
                        statistics["class_distribution"][class_id] += 1
                        
                if annotations_count > 0:
                    statistics["total_annotations"] += annotations_count
                    statistics["annotations_per_image"].append(annotations_count)
                    
            except Exception as e:
                logger.error(f"统计标注信息出错: {image_filename} - {str(e)}")
    
    if statistics["annotated_images"] > 0:
        avg_annotations = statistics["total_annotations"] / statistics["annotated_images"]
    else:
        avg_annotations = 0
        
    statistics["avg_annotations_per_image"] = avg_annotations
    
    return statistics