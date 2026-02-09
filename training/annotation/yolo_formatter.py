#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
YOLO格式转换模块

提供边界框坐标与YOLO格式之间的转换功能。
"""


def convert_bbox_to_yolo(image, bbox, class_id=0):
    """将边界框坐标转换为YOLO格式
    
    Args:
        image: 图片（OpenCV格式）
        bbox: 边界框坐标 (x1, y1, x2, y2)
        class_id: 类别ID，默认为0
        
    Returns:
        YOLO格式坐标列表 [class_id, x_center, y_center, width, height]
    """
    img_height, img_width = image.shape[:2]
    
    x1, y1, x2, y2 = bbox
    
    # 计算YOLO格式坐标
    x_center = (x1 + x2) / 2 / img_width
    y_center = (y1 + y2) / 2 / img_height
    width = (x2 - x1) / img_width
    height = (y2 - y1) / img_height
    
    return [class_id, x_center, y_center, width, height]


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


def validate_yolo_annotation(annotation):
    """验证YOLO格式标注的合法性
    
    Args:
        annotation: YOLO格式标注列表 [class_id, x_center, y_center, width, height]
        
    Returns:
        验证结果 (valid, error_message)
    """
    if len(annotation) < 5:
        return False, "标注字段数量不足"
    
    try:
        class_id = int(annotation[0])
        x_center = float(annotation[1])
        y_center = float(annotation[2])
        width = float(annotation[3])
        height = float(annotation[4])
        
        # 验证坐标范围
        if not (0 <= x_center <= 1):
            return False, f"x_center {x_center} 超出范围 [0, 1]"
        if not (0 <= y_center <= 1):
            return False, f"y_center {y_center} 超出范围 [0, 1]"
        if not (0 < width <= 1):
            return False, f"width {width} 超出范围 (0, 1]"
        if not (0 < height <= 1):
            return False, f"height {height} 超出范围 (0, 1]"
            
        return True, "标注格式正确"
        
    except (ValueError, TypeError) as e:
        return False, f"标注格式错误: {str(e)}"