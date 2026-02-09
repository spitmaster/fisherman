#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
标注可视化模块

提供标注框绘制和状态信息显示功能。
"""

import cv2
import numpy as np


def draw_annotations(image, annotations, is_drawing=False, start_point=(0, 0), end_point=(0, 0)):
    """在图片上绘制标注框
    
    Args:
        image: 原始图片（OpenCV格式）
        annotations: 标注列表，每个标注为 [class_id, x_center, y_center, width, height]
        is_drawing: 是否正在绘制
        start_point: 绘制起点 (x, y)
        end_point: 绘制终点 (x, y)
        
    Returns:
        绘制后的图片
    """
    if image is None:
        return None
        
    img_copy = image.copy()
    
    # 绘制已有的标注框
    for annotation in annotations:
        class_id, x_center, y_center, width, height = annotation
        
        # 计算边界框坐标
        img_height, img_width = img_copy.shape[:2]
        x1 = int((x_center - width / 2) * img_width)
        y1 = int((y_center - height / 2) * img_height)
        x2 = int((x_center + width / 2) * img_width)
        y2 = int((y_center + height / 2) * img_height)
        
        # 绘制边界框
        cv2.rectangle(img_copy, (x1, y1), (x2, y2), (0, 255, 0), 2)
        
        # 绘制类别标签
        label = f"Class {class_id}"
        font = cv2.FONT_HERSHEY_SIMPLEX
        font_scale = 0.5
        font_thickness = 1
        text_size = cv2.getTextSize(label, font, font_scale, font_thickness)[0]
        
        # 计算标签位置
        label_x = x1
        label_y = y1 - 10 if y1 - 10 > 10 else y1 + 20
        
        # 绘制标签背景
        cv2.rectangle(
            img_copy,
            (label_x, label_y - text_size[1] - 5),
            (label_x + text_size[0] + 5, label_y + 5),
            (0, 255, 0),
            -1
        )
        
        # 绘制标签文字
        cv2.putText(
            img_copy,
            label,
            (label_x, label_y),
            font,
            font_scale,
            (0, 0, 0),
            font_thickness
        )
    
    # 绘制正在绘制的标注框
    if is_drawing:
        cv2.rectangle(img_copy, start_point, end_point, (0, 0, 255), 2)
        
    return img_copy


def show_status_info(image, current_index, total_images, annotation_count, window_name="Fisherman - 标注工具"):
    """在图片上显示状态信息
    
    Args:
        image: 图片
        current_index: 当前图片索引（0-based）
        total_images: 总图片数
        annotation_count: 当前图片的标注数量
        window_name: 窗口名称
        
    Returns:
        添加状态信息后的图片
    """
    if image is None:
        return None
        
    img_height, img_width = image.shape[:2]
    
    # 绘制状态信息
    status_text = (
        f"图片: {current_index + 1}/{total_images} | "
        f"标注: {annotation_count} 个 | "
        f"快捷键: S保存/D下一张/A回退/Q退出"
    )
    
    font = cv2.FONT_HERSHEY_SIMPLEX
    font_scale = 0.6
    font_thickness = 2
    text_size = cv2.getTextSize(status_text, font, font_scale, font_thickness)[0]
    
    # 绘制背景
    cv2.rectangle(
        image,
        (0, img_height - text_size[1] - 10),
        (text_size[0] + 10, img_height),
        (0, 0, 0),
        -1
    )
    
    # 绘制文字
    cv2.putText(
        image,
        status_text,
        (5, img_height - 5),
        font,
        font_scale,
        (255, 255, 255),
        font_thickness
    )
    
    return image