#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
标注可视化模块

提供丰富的标注框绘制、样式定制和交互效果。
支持多种颜色方案、动画效果和可视化配置。
"""

import cv2
import numpy as np
import math
from typing import List, Tuple, Dict, Any, Optional
from enum import Enum


class ColorScheme(Enum):
    """颜色方案枚举"""
    DEFAULT = "default"
    VIBRANT = "vibrant"
    PASTEL = "pastel"
    DARK = "dark"
    CUSTOM = "custom"


class AnnotationStyle(Enum):
    """标注样式枚举"""
    RECTANGLE = "rectangle"
    ROUNDED_RECTANGLE = "rounded_rectangle"
    CORNER_MARKERS = "corner_markers"
    FILLED = "filled"


class AnnotationVisualizer:
    """标注可视化器
    
    提供丰富的标注可视化功能，支持多种样式和交互效果。
    """
    
    def __init__(self, color_scheme: ColorScheme = ColorScheme.DEFAULT, 
                 annotation_style: AnnotationStyle = AnnotationStyle.RECTANGLE):
        """初始化可视化器
        
        Args:
            color_scheme: 颜色方案
            annotation_style: 标注样式
        """
        self.color_scheme = color_scheme
        self.annotation_style = annotation_style
        
        # 颜色配置
        self.color_palettes = self._initialize_color_palettes()
        
        # 样式配置
        self.line_thickness = 2
        self.corner_radius = 8
        self.marker_size = 6
        self.fill_alpha = 0.3
        
        # 动画效果
        self.highlight_duration = 0.3  # 秒
        self.pulse_enabled = True
        self.fade_enabled = True
        
        # 缓存最近使用的颜色
        self._color_cache = {}
    
    def _initialize_color_palettes(self) -> Dict[str, List[Tuple[int, int, int]]]:
        """初始化颜色调色板
        
        Returns:
            颜色调色板字典
        """
        return {
            ColorScheme.DEFAULT.value: [
                (0, 255, 0),    # 绿色
                (255, 0, 0),    # 蓝色
                (0, 0, 255),    # 红色
                (255, 255, 0),  # 青色
                (255, 0, 255),  # 紫色
                (0, 255, 255),  # 黄色
            ],
            ColorScheme.VIBRANT.value: [
                (255, 50, 50),   # 鲜艳红
                (50, 255, 50),   # 鲜艳绿
                (50, 50, 255),   # 鲜艳蓝
                (255, 255, 50),  # 鲜艳黄
                (255, 50, 255),  # 鲜艳紫
                (50, 255, 255),  # 鲜艳青
            ],
            ColorScheme.PASTEL.value: [
                (255, 182, 193),  # 浅粉红
                (173, 216, 230),  # 浅蓝
                (152, 251, 152),  # 浅绿
                (255, 228, 196),  # 浅黄
                (216, 191, 216),  # 浅紫
                (175, 238, 238),  # 浅青
            ],
            ColorScheme.DARK.value: [
                (139, 0, 0),      # 深红
                (0, 100, 0),      # 深绿
                (0, 0, 139),      # 深蓝
                (139, 139, 0),    # 深黄
                (139, 0, 139),    # 深紫
                (0, 139, 139),    # 深青
            ]
        }
    
    def get_class_color(self, class_id: int) -> Tuple[int, int, int]:
        """获取类别对应的颜色
        
        Args:
            class_id: 类别ID
            
        Returns:
            BGR颜色元组
        """
        if class_id in self._color_cache:
            return self._color_cache[class_id]
        
        palette = self.color_palettes.get(self.color_scheme.value, 
                                         self.color_palettes[ColorScheme.DEFAULT.value])
        
        color_index = class_id % len(palette)
        color = palette[color_index]
        
        self._color_cache[class_id] = color
        return color
    
    def draw_annotations(self, image: np.ndarray, annotations: List[List[float]], 
                        is_drawing: bool = False, start_point: Tuple[int, int] = (0, 0), 
                        end_point: Tuple[int, int] = (0, 0), selected_annotation: int = -1,
                        show_confidences: bool = False, confidences: List[float] = None) -> np.ndarray:
        """在图片上绘制标注框
        
        Args:
            image: 原始图片（OpenCV格式）
            annotations: 标注列表
            is_drawing: 是否正在绘制
            start_point: 绘制起点
            end_point: 绘制终点
            selected_annotation: 选中的标注索引
            show_confidences: 是否显示置信度
            confidences: 置信度列表
            
        Returns:
            绘制后的图片
        """
        if image is None:
            return None
            
        img_copy = image.copy()
        img_height, img_width = img_copy.shape[:2]
        
        # 绘制已有的标注框
        for i, annotation in enumerate(annotations):
            if len(annotation) < 5:
                continue
                
            class_id, x_center, y_center, width, height = annotation[:5]
            
            # 计算边界框坐标
            x1 = int((x_center - width / 2) * img_width)
            y1 = int((y_center - height / 2) * img_height)
            x2 = int((x_center + width / 2) * img_width)
            y2 = int((y_center + height / 2) * img_height)
            
            # 获取颜色
            color = self.get_class_color(int(class_id))
            
            # 检查是否被选中
            is_selected = (i == selected_annotation)
            
            # 根据样式绘制标注框
            self._draw_annotation_box(img_copy, (x1, y1, x2, y2), color, is_selected)
            
            # 绘制类别标签
            self._draw_class_label(img_copy, (x1, y1), int(class_id), color, 
                                  confidences[i] if show_confidences and confidences and i < len(confidences) else None)
        
        # 绘制正在绘制的标注框
        if is_drawing:
            self._draw_drawing_box(img_copy, start_point, end_point)
        
        return img_copy
    
    def _draw_annotation_box(self, image: np.ndarray, bbox: Tuple[int, int, int, int], 
                           color: Tuple[int, int, int], is_selected: bool = False):
        """绘制标注框
        
        Args:
            image: 图片
            bbox: 边界框 (x1, y1, x2, y2)
            color: 颜色
            is_selected: 是否被选中
        """
        x1, y1, x2, y2 = bbox
        
        # 调整选中状态的样式
        thickness = self.line_thickness * 2 if is_selected else self.line_thickness
        highlight_color = self._adjust_color_brightness(color, 1.3) if is_selected else color
        
        if self.annotation_style == AnnotationStyle.ROUNDED_RECTANGLE:
            self._draw_rounded_rectangle(image, bbox, highlight_color, thickness)
        elif self.annotation_style == AnnotationStyle.CORNER_MARKERS:
            self._draw_corner_markers(image, bbox, highlight_color, thickness)
        elif self.annotation_style == AnnotationStyle.FILLED:
            self._draw_filled_box(image, bbox, highlight_color, thickness)
        else:  # RECTANGLE
            cv2.rectangle(image, (x1, y1), (x2, y2), highlight_color, thickness)
        
        # 如果被选中，绘制额外的效果
        if is_selected and self.pulse_enabled:
            self._draw_selection_highlight(image, bbox, highlight_color)
    
    def _draw_rounded_rectangle(self, image: np.ndarray, bbox: Tuple[int, int, int, int], 
                              color: Tuple[int, int, int], thickness: int):
        """绘制圆角矩形
        
        Args:
            image: 图片
            bbox: 边界框
            color: 颜色
            thickness: 线宽
        """
        x1, y1, x2, y2 = bbox
        r = self.corner_radius
        
        # 绘制圆角
        cv2.ellipse(image, (x1 + r, y1 + r), (r, r), 180, 0, 90, color, thickness)
        cv2.ellipse(image, (x2 - r, y1 + r), (r, r), 270, 0, 90, color, thickness)
        cv2.ellipse(image, (x1 + r, y2 - r), (r, r), 90, 0, 90, color, thickness)
        cv2.ellipse(image, (x2 - r, y2 - r), (r, r), 0, 0, 90, color, thickness)
        
        # 绘制直线
        cv2.line(image, (x1 + r, y1), (x2 - r, y1), color, thickness)
        cv2.line(image, (x1 + r, y2), (x2 - r, y2), color, thickness)
        cv2.line(image, (x1, y1 + r), (x1, y2 - r), color, thickness)
        cv2.line(image, (x2, y1 + r), (x2, y2 - r), color, thickness)
    
    def _draw_corner_markers(self, image: np.ndarray, bbox: Tuple[int, int, int, int], 
                           color: Tuple[int, int, int], thickness: int):
        """绘制角标记
        
        Args:
            image: 图片
            bbox: 边界框
            color: 颜色
            thickness: 线宽
        """
        x1, y1, x2, y2 = bbox
        marker_size = self.marker_size
        
        # 绘制角标记
        cv2.line(image, (x1, y1), (x1 + marker_size, y1), color, thickness)
        cv2.line(image, (x1, y1), (x1, y1 + marker_size), color, thickness)
        
        cv2.line(image, (x2, y1), (x2 - marker_size, y1), color, thickness)
        cv2.line(image, (x2, y1), (x2, y1 + marker_size), color, thickness)
        
        cv2.line(image, (x1, y2), (x1 + marker_size, y2), color, thickness)
        cv2.line(image, (x1, y2), (x1, y2 - marker_size), color, thickness)
        
        cv2.line(image, (x2, y2), (x2 - marker_size, y2), color, thickness)
        cv2.line(image, (x2, y2), (x2, y2 - marker_size), color, thickness)
    
    def _draw_filled_box(self, image: np.ndarray, bbox: Tuple[int, int, int, int], 
                        color: Tuple[int, int, int], thickness: int):
        """绘制填充框
        
        Args:
            image: 图片
            bbox: 边界框
            color: 颜色
            thickness: 线宽
        """
        x1, y1, x2, y2 = bbox
        
        # 创建填充层
        overlay = image.copy()
        cv2.rectangle(overlay, (x1, y1), (x2, y2), color, -1)
        
        # 混合填充层
        cv2.addWeighted(overlay, self.fill_alpha, image, 1 - self.fill_alpha, 0, image)
        
        # 绘制边框
        cv2.rectangle(image, (x1, y1), (x2, y2), color, thickness)
    
    def _draw_class_label(self, image: np.ndarray, position: Tuple[int, int], class_id: int, 
                         color: Tuple[int, int, int], confidence: float = None):
        """绘制类别标签
        
        Args:
            image: 图片
            position: 位置
            class_id: 类别ID
            color: 颜色
            confidence: 置信度
        """
        x, y = position
        
        # 构建标签文本
        label = f"Class {class_id}"
        if confidence is not None:
            label += f" ({confidence:.2f})"
        
        font = cv2.FONT_HERSHEY_SIMPLEX
        font_scale = 0.6
        font_thickness = 1
        
        # 计算文本尺寸
        text_size = cv2.getTextSize(label, font, font_scale, font_thickness)[0]
        
        # 计算标签位置
        label_x = x
        label_y = y - 10 if y - 10 > 10 else y + text_size[1] + 10
        
        # 确保标签在图片范围内
        if label_x + text_size[0] > image.shape[1]:
            label_x = image.shape[1] - text_size[0] - 5
        if label_y < 0:
            label_y = text_size[1] + 5
        
        # 绘制标签背景
        bg_color = self._adjust_color_brightness(color, 0.7)
        cv2.rectangle(
            image,
            (label_x - 2, label_y - text_size[1] - 2),
            (label_x + text_size[0] + 2, label_y + 2),
            bg_color,
            -1
        )
        
        # 绘制标签边框
        cv2.rectangle(
            image,
            (label_x - 2, label_y - text_size[1] - 2),
            (label_x + text_size[0] + 2, label_y + 2),
            color,
            1
        )
        
        # 绘制标签文字
        cv2.putText(
            image,
            label,
            (label_x, label_y),
            font,
            font_scale,
            (255, 255, 255),  # 白色文字
            font_thickness
        )
    
    def _draw_drawing_box(self, image: np.ndarray, start_point: Tuple[int, int], 
                         end_point: Tuple[int, int]):
        """绘制正在绘制的标注框
        
        Args:
            image: 图片
            start_point: 起点
            end_point: 终点
        """
        if start_point != (0, 0) and end_point != (0, 0):
            # 使用虚线样式绘制
            self._draw_dashed_rectangle(image, start_point, end_point, (0, 0, 255), 2)
    
    def _draw_dashed_rectangle(self, image: np.ndarray, pt1: Tuple[int, int], 
                             pt2: Tuple[int, int], color: Tuple[int, int, int], 
                             thickness: int, dash_length: int = 10):
        """绘制虚线矩形
        
        Args:
            image: 图片
            pt1: 点1
            pt2: 点2
            color: 颜色
            thickness: 线宽
            dash_length: 虚线长度
        """
        x1, y1 = pt1
        x2, y2 = pt2
        
        # 绘制四条虚线边
        self._draw_dashed_line(image, (x1, y1), (x2, y1), color, thickness, dash_length)
        self._draw_dashed_line(image, (x2, y1), (x2, y2), color, thickness, dash_length)
        self._draw_dashed_line(image, (x2, y2), (x1, y2), color, thickness, dash_length)
        self._draw_dashed_line(image, (x1, y2), (x1, y1), color, thickness, dash_length)
    
    def _draw_dashed_line(self, image: np.ndarray, pt1: Tuple[int, int], 
                         pt2: Tuple[int, int], color: Tuple[int, int, int], 
                         thickness: int, dash_length: int):
        """绘制虚线
        
        Args:
            image: 图片
            pt1: 点1
            pt2: 点2
            color: 颜色
            thickness: 线宽
            dash_length: 虚线长度
        """
        x1, y1 = pt1
        x2, y2 = pt2
        
        # 计算线段长度和方向
        dx = x2 - x1
        dy = y2 - y1
        dist = math.sqrt(dx*dx + dy*dy)
        
        if dist == 0:
            return
        
        # 计算单位向量
        dx = dx / dist
        dy = dy / dist
        
        # 绘制虚线
        for i in range(0, int(dist), dash_length * 2):
            start = i
            end = min(i + dash_length, int(dist))
            
            x_start = int(x1 + dx * start)
            y_start = int(y1 + dy * start)
            x_end = int(x1 + dx * end)
            y_end = int(y1 + dy * end)
            
            cv2.line(image, (x_start, y_start), (x_end, y_end), color, thickness)
    
    def _draw_selection_highlight(self, image: np.ndarray, bbox: Tuple[int, int, int, int], 
                                 color: Tuple[int, int, int]):
        """绘制选中高亮效果
        
        Args:
            image: 图片
            bbox: 边界框
            color: 颜色
        """
        x1, y1, x2, y2 = bbox
        
        # 绘制外发光效果
        glow_color = self._adjust_color_brightness(color, 1.5)
        cv2.rectangle(image, (x1 - 3, y1 - 3), (x2 + 3, y2 + 3), glow_color, 1)
        cv2.rectangle(image, (x1 - 2, y1 - 2), (x2 + 2, y2 + 2), glow_color, 1)
    
    def _adjust_color_brightness(self, color: Tuple[int, int, int], factor: float) -> Tuple[int, int, int]:
        """调整颜色亮度
        
        Args:
            color: 原始颜色
            factor: 亮度因子
            
        Returns:
            调整后的颜色
        """
        b, g, r = color
        
        b = min(255, max(0, int(b * factor)))
        g = min(255, max(0, int(g * factor)))
        r = min(255, max(0, int(r * factor)))
        
        return (b, g, r)
    
    def set_color_scheme(self, color_scheme: ColorScheme):
        """设置颜色方案
        
        Args:
            color_scheme: 颜色方案
        """
        self.color_scheme = color_scheme
        self._color_cache.clear()
    
    def set_annotation_style(self, annotation_style: AnnotationStyle):
        """设置标注样式
        
        Args:
            annotation_style: 标注样式
        """
        self.annotation_style = annotation_style
    
    def set_custom_colors(self, custom_colors: List[Tuple[int, int, int]]):
        """设置自定义颜色
        
        Args:
            custom_colors: 自定义颜色列表
        """
        if custom_colors:
            self.color_scheme = ColorScheme.CUSTOM
            self.color_palettes[ColorScheme.CUSTOM.value] = custom_colors
            self._color_cache.clear()


# 保持向后兼容的函数
def draw_annotations(image, annotations, is_drawing=False, start_point=(0, 0), end_point=(0, 0)):
    """在图片上绘制标注框（兼容性函数）
    
    Args:
        image: 原始图片
        annotations: 标注列表
        is_drawing: 是否正在绘制
        start_point: 绘制起点
        end_point: 绘制终点
        
    Returns:
        绘制后的图片
    """
    visualizer = AnnotationVisualizer()
    return visualizer.draw_annotations(image, annotations, is_drawing, start_point, end_point)


    def show_status_info(self, image: np.ndarray, current_index: int, total_images: int, 
                        annotation_count: int, total_annotations: int = 0,
                        selected_class: int = -1, classes: List[str] = None,
                        mode: str = "标注模式", additional_info: str = "") -> np.ndarray:
        """在图片上显示状态信息
        
        Args:
            image: 图片
            current_index: 当前图片索引（0-based）
            total_images: 总图片数
            annotation_count: 当前图片的标注数量
            total_annotations: 总标注数量
            selected_class: 选中的类别ID
            classes: 类别名称列表
            mode: 当前模式
            additional_info: 额外信息
            
        Returns:
        添加状态信息后的图片
        """
        if image is None:
            return None
            
        img_height, img_width = image.shape[:2]
        
        # 构建状态信息
        status_parts = [
            f"图片: {current_index + 1}/{total_images}",
            f"标注: {annotation_count} 个"
        ]
        
        if total_annotations > 0:
            status_parts.append(f"总计: {total_annotations} 个")
        
        if selected_class >= 0 and classes and selected_class < len(classes):
            class_name = classes[selected_class]
            status_parts.append(f"类别: {class_name}")
        
        status_parts.append(f"模式: {mode}")
        
        if additional_info:
            status_parts.append(additional_info)
        
        # 添加快捷键信息
        shortcut_info = "快捷键: [S]保存 [D]下一张 [A]回退 [C]切换类别 [Q]退出"
        
        # 计算文本尺寸
        font = cv2.FONT_HERSHEY_SIMPLEX
        font_scale = 0.5
        font_thickness = 1
        
        # 主状态信息
        main_text = " | ".join(status_parts)
        main_text_size = cv2.getTextSize(main_text, font, font_scale, font_thickness)[0]
        
        # 快捷键信息
        shortcut_text_size = cv2.getTextSize(shortcut_info, font, font_scale - 0.1, font_thickness)[0]
        
        # 计算总高度
        total_height = main_text_size[1] + shortcut_text_size[1] + 25
        
        # 绘制背景
        bg_color = (40, 40, 40)  # 深灰色背景
        cv2.rectangle(
            image,
            (0, img_height - total_height),
            (img_width, img_height),
            bg_color,
            -1
        )
        
        # 绘制分隔线
        line_y = img_height - shortcut_text_size[1] - 10
        cv2.line(image, (0, line_y), (img_width, line_y), (100, 100, 100), 1)
        
        # 绘制主状态信息
        cv2.putText(
            image,
            main_text,
            (10, img_height - shortcut_text_size[1] - 15),
            font,
            font_scale,
            (255, 255, 255),  # 白色
            font_thickness
        )
        
        # 绘制快捷键信息
        cv2.putText(
            image,
            shortcut_info,
            (10, img_height - 5),
            font,
            font_scale - 0.1,
            (200, 200, 200),  # 浅灰色
            font_thickness
        )
        
        # 绘制进度条（如果总图片数大于1）
        if total_images > 1:
            progress_width = img_width - 20
            progress_height = 4
            progress_x = 10
            progress_y = img_height - total_height - 10
            
            # 进度条背景
            cv2.rectangle(
                image,
                (progress_x, progress_y),
                (progress_x + progress_width, progress_y + progress_height),
                (100, 100, 100),
                -1
            )
            
            # 进度条前景
            if total_images > 0:
                progress = (current_index + 1) / total_images
                progress_fill_width = int(progress_width * progress)
                
                cv2.rectangle(
                    image,
                    (progress_x, progress_y),
                    (progress_x + progress_fill_width, progress_y + progress_height),
                    (0, 200, 0),  # 绿色进度条
                    -1
                )
            
            # 进度文本
            progress_text = f"{current_index + 1}/{total_images} ({progress*100:.1f}%)"
            progress_text_size = cv2.getTextSize(progress_text, font, font_scale - 0.1, font_thickness)[0]
            
            cv2.putText(
                image,
                progress_text,
                (progress_x + progress_width - progress_text_size[0] - 5, progress_y - 5),
                font,
                font_scale - 0.1,
                (200, 200, 200),
                font_thickness
            )
        
        return image
    
    def show_class_distribution(self, image: np.ndarray, class_distribution: Dict[int, int], 
                              classes: List[str] = None, max_bars: int = 10) -> np.ndarray:
        """在图片上显示类别分布
        
        Args:
            image: 图片
            class_distribution: 类别分布字典
            classes: 类别名称列表
            max_bars: 最大显示条数
            
        Returns:
            添加类别分布后的图片
        """
        if image is None or not class_distribution:
            return image
        
        img_height, img_width = image.shape[:2]
        
        # 计算图表区域
        chart_width = min(300, img_width // 3)
        chart_height = min(200, img_height // 3)
        chart_x = img_width - chart_width - 10
        chart_y = 10
        
        # 绘制图表背景
        cv2.rectangle(
            image,
            (chart_x, chart_y),
            (chart_x + chart_width, chart_y + chart_height),
            (40, 40, 40),
            -1
        )
        
        # 绘制标题
        title = "类别分布"
        font = cv2.FONT_HERSHEY_SIMPLEX
        font_scale = 0.5
        font_thickness = 1
        
        cv2.putText(
            image,
            title,
            (chart_x + 10, chart_y + 20),
            font,
            font_scale,
            (255, 255, 255),
            font_thickness
        )
        
        # 排序类别分布
        sorted_distribution = sorted(class_distribution.items(), key=lambda x: x[1], reverse=True)
        
        # 限制显示数量
        if len(sorted_distribution) > max_bars:
            sorted_distribution = sorted_distribution[:max_bars]
        
        # 计算最大数量
        max_count = max(class_distribution.values()) if class_distribution else 1
        
        # 绘制条形图
        bar_width = chart_width // (len(sorted_distribution) + 1)
        bar_spacing = bar_width // 2
        
        for i, (class_id, count) in enumerate(sorted_distribution):
            # 计算条形位置和高度
            bar_x = chart_x + bar_spacing + i * (bar_width + bar_spacing)
            bar_height = int((count / max_count) * (chart_height - 40))
            bar_y = chart_y + chart_height - 20 - bar_height
            
            # 获取颜色
            color = self.get_class_color(class_id)
            
            # 绘制条形
            cv2.rectangle(
                image,
                (bar_x, bar_y),
                (bar_x + bar_width, chart_y + chart_height - 20),
                color,
                -1
            )
            
            # 绘制数量文本
            count_text = str(count)
            count_text_size = cv2.getTextSize(count_text, font, font_scale - 0.2, font_thickness)[0]
            
            cv2.putText(
                image,
                count_text,
                (bar_x + (bar_width - count_text_size[0]) // 2, bar_y - 5),
                font,
                font_scale - 0.2,
                (255, 255, 255),
                font_thickness
            )
            
            # 绘制类别标签
            if classes and class_id < len(classes):
                class_name = classes[class_id]
                class_text = class_name[:3]  # 限制长度
                
                cv2.putText(
                    image,
                    class_text,
                    (bar_x + (bar_width - 15) // 2, chart_y + chart_height - 5),
                    font,
                    font_scale - 0.2,
                    (200, 200, 200),
                    font_thickness
                )
        
        return image


# 保持向后兼容的函数
def show_status_info(image, current_index, total_images, annotation_count, window_name="Fisherman - 标注工具"):
    """在图片上显示状态信息（兼容性函数）
    
    Args:
        image: 图片
        current_index: 当前图片索引
        total_images: 总图片数
        annotation_count: 标注数量
        window_name: 窗口名称
        
    Returns:
        添加状态信息后的图片
    """
    visualizer = AnnotationVisualizer()
    return visualizer.show_status_info(image, current_index, total_images, annotation_count)