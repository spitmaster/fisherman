#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
训练模块 - 标注工具

提供可视化标注功能，支持鼠标框选、快捷键操作，自动生成YOLO格式的标签文件。

主要功能：
- 图片加载和显示
- 鼠标框选标注
- 快捷键操作（S保存/D下一张/A回退/Q退出）
- 标注格式校验
- 标签文件生成
"""

import os
import sys
import logging
import cv2
import numpy as np
from PIL import Image, ImageDraw, ImageFont

# 日志配置
logger = logging.getLogger(__name__)

class AnnotationTool:
    """可视化标注工具"""
    
    def __init__(self, task_info, image_files, annotated_count):
        """初始化标注工具
        
        Args:
            task_info: 任务信息
            image_files: 图片文件列表
            annotated_count: 已标注图片数量
        """
        self.task_info = task_info
        self.image_files = image_files
        self.current_image_index = 0
        self.current_annotations = []
        self.is_drawing = False
        self.start_point = (0, 0)
        self.end_point = (0, 0)
        
        # 确保任务目录存在
        self._ensure_directories()
        
    def _ensure_directories(self):
        """确保必要的目录存在"""
        directories = [
            os.path.join(self.task_info["task_dir"], "dataset/images/train"),
            os.path.join(self.task_info["task_dir"], "dataset/labels/train")
        ]
        
        for directory in directories:
            if not os.path.exists(directory):
                os.makedirs(directory, exist_ok=True)
                
    def _load_current_image(self):
        """加载当前图片"""
        image_filename = self.image_files[self.current_image_index]
        image_path = os.path.join(
            self.task_info["task_dir"], 
            "dataset/images/train", 
            image_filename
        )
        
        if os.path.exists(image_path):
            return cv2.imread(image_path)
        else:
            logger.error(f"图片文件不存在: {image_path}")
            return None
            
    def _load_current_annotations(self):
        """加载当前图片的标注"""
        image_filename = self.image_files[self.current_image_index]
        label_filename = os.path.splitext(image_filename)[0] + ".txt"
        label_path = os.path.join(
            self.task_info["task_dir"], 
            "dataset/labels/train", 
            label_filename
        )
        
        self.current_annotations = []
        
        if os.path.exists(label_path):
            try:
                with open(label_path, "r", encoding="utf-8") as f:
                    lines = f.readlines()
                    
                for line in lines:
                    line = line.strip()
                    if line:
                        parts = line.split()
                        if len(parts) >= 5:
                            class_id = int(parts[0])
                            x_center = float(parts[1])
                            y_center = float(parts[2])
                            width = float(parts[3])
                            height = float(parts[4])
                            self.current_annotations.append([class_id, x_center, y_center, width, height])
                        
            except Exception as e:
                logger.error(f"加载标注文件出错: {label_path} - {str(e)}")
                
    def _save_current_annotations(self):
        """保存当前图片的标注"""
        image_filename = self.image_files[self.current_image_index]
        label_filename = os.path.splitext(image_filename)[0] + ".txt"
        label_path = os.path.join(
            self.task_info["task_dir"], 
            "dataset/labels/train", 
            label_filename
        )
        
        try:
            with open(label_path, "w", encoding="utf-8") as f:
                for annotation in self.current_annotations:
                    class_id, x_center, y_center, width, height = annotation
                    f.write(f"{class_id} {x_center:.6f} {y_center:.6f} {width:.6f} {height:.6f}\n")
                    
            logger.info(f"标注文件保存成功: {label_path}")
            return True
            
        except Exception as e:
            logger.error(f"保存标注文件出错: {label_path} - {str(e)}")
            return False
            
    def _draw_annotations(self, image):
        """在图片上绘制标注"""
        if image is None:
            return None
            
        # 创建副本以避免修改原始图片
        img_copy = image.copy()
        
        # 绘制已有的标注框
        for annotation in self.current_annotations:
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
        if self.is_drawing:
            cv2.rectangle(img_copy, self.start_point, self.end_point, (0, 0, 255), 2)
            
        return img_copy
        
    def _convert_bbox_to_yolo_format(self, image, bbox):
        """将边界框坐标转换为YOLO格式
        
        Args:
            image: 图片
            bbox: 边界框坐标 (x1, y1, x2, y2)
            
        Returns:
            YOLO格式坐标 (class_id, x_center, y_center, width, height)
        """
        img_height, img_width = image.shape[:2]
        
        x1, y1, x2, y2 = bbox
        
        # 计算YOLO格式坐标
        x_center = (x1 + x2) / 2 / img_width
        y_center = (y1 + y2) / 2 / img_height
        width = (x2 - x1) / img_width
        height = (y2 - y1) / img_height
        
        # 默认类别ID为0
        class_id = 0
        
        return [class_id, x_center, y_center, width, height]
        
    def _handle_mouse_events(self, event, x, y, flags, param):
        """处理鼠标事件"""
        if event == cv2.EVENT_LBUTTONDOWN:
            # 开始绘制边界框
            self.is_drawing = True
            self.start_point = (x, y)
            self.end_point = (x, y)
            
        elif event == cv2.EVENT_MOUSEMOVE and self.is_drawing:
            # 更新边界框终点
            self.end_point = (x, y)
            
        elif event == cv2.EVENT_LBUTTONUP:
            # 完成绘制边界框
            self.is_drawing = False
            
            # 确保边界框有效
            if self.start_point != self.end_point:
                # 调整边界框坐标（确保x1 < x2, y1 < y2）
                x1 = min(self.start_point[0], self.end_point[0])
                y1 = min(self.start_point[1], self.end_point[1])
                x2 = max(self.start_point[0], self.end_point[0])
                y2 = max(self.start_point[1], self.end_point[1])
                
                # 转换为YOLO格式
                image = self._load_current_image()
                if image is not None:
                    annotation = self._convert_bbox_to_yolo_format(image, (x1, y1, x2, y2))
                    self.current_annotations.append(annotation)
                    logger.info(f"添加标注: {annotation}")
                    
    def _show_status_info(self, image, window_name):
        """显示状态信息"""
        img_height, img_width = image.shape[:2]
        
        # 绘制状态信息
        status_text = (
            f"图片: {self.current_image_index + 1}/{len(self.image_files)} | "
            f"标注: {len(self.current_annotations)} 个 | "
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
        
    def start_annotation(self):
        """开始标注流程"""
        logger.info("开始标注流程")
        
        # 创建窗口并设置鼠标事件回调
        window_name = "Fisherman - 标注工具"
        cv2.namedWindow(window_name, cv2.WINDOW_NORMAL)
        cv2.resizeWindow(window_name, 800, 600)
        cv2.setMouseCallback(window_name, self._handle_mouse_events)
        
        # 加载第一张图片
        self._load_current_annotations()
        
        while True:
            # 加载并绘制图片
            image = self._load_current_image()
            if image is None:
                logger.error("无法加载图片，尝试下一张")
                self._next_image()
                continue
                
            # 绘制标注
            image_with_annotations = self._draw_annotations(image)
            self._show_status_info(image_with_annotations, window_name)
            
            # 显示图片
            cv2.imshow(window_name, image_with_annotations)
            
            # 等待按键
            key = cv2.waitKey(1) & 0xFF
            
            if key == ord('s') or key == ord('S'):
                # 保存标注
                if self._save_current_annotations():
                    logger.info("标注已保存")
                    
            elif key == ord('d') or key == ord('D'):
                # 下一张图片
                if self._next_image():
                    logger.info("切换到下一张图片")
                else:
                    logger.warning("已经是最后一张图片")
                    
            elif key == ord('a') or key == ord('A'):
                # 上一张图片
                if self._previous_image():
                    logger.info("切换到上一张图片")
                else:
                    logger.warning("已经是第一张图片")
                    
            elif key == ord('q') or key == ord('Q'):
                # 退出标注
                logger.info("退出标注流程")
                break
                
            elif key == 8:  # Backspace
                # 删除最后一个标注
                if self.current_annotations:
                    deleted = self.current_annotations.pop()
                    logger.info(f"删除标注: {deleted}")
                    
            elif key == ord('r') or key == ord('R'):
                # 清空所有标注
                if self.current_annotations:
                    self.current_annotations = []
                    logger.info("所有标注已清空")
                    
        # 清理资源
        cv2.destroyAllWindows()
        logger.info("标注流程结束")
        
    def _next_image(self):
        """切换到下一张图片"""
        if self.current_image_index < len(self.image_files) - 1:
            self.current_image_index += 1
            self._load_current_annotations()
            return True
        return False
        
    def _previous_image(self):
        """切换到上一张图片"""
        if self.current_image_index > 0:
            self.current_image_index -= 1
            self._load_current_annotations()
            return True
        return False
        
    def get_annotation_status(self):
        """获取标注状态信息
        
        Returns:
            标注状态字典
        """
        annotated_files = 0
        total_files = len(self.image_files)
        
        for image_filename in self.image_files:
            label_filename = os.path.splitext(image_filename)[0] + ".txt"
            label_path = os.path.join(
                self.task_info["task_dir"], 
                "dataset/labels/train", 
                label_filename
            )
            
            if os.path.exists(label_path) and os.path.getsize(label_path) > 0:
                annotated_files += 1
                
        return {
            "total_images": total_files,
            "annotated_images": annotated_files,
            "current_image": self.current_image_index + 1,
            "current_annotations": len(self.current_annotations),
            "annotation_progress": (annotated_files / total_files) * 100 if total_files > 0 else 0
        }
        
    def validate_annotations(self):
        """验证标注数据的合法性
        
        Returns:
            验证结果字典
        """
        validation_result = {
            "valid": True,
            "errors": []
        }
        
        for image_filename in self.image_files:
            label_filename = os.path.splitext(image_filename)[0] + ".txt"
            label_path = os.path.join(
                self.task_info["task_dir"], 
                "dataset/labels/train", 
                label_filename
            )
            
            if os.path.exists(label_path):
                try:
                    with open(label_path, "r", encoding="utf-8") as f:
                        lines = f.readlines()
                        
                    for line_num, line in enumerate(lines):
                        line = line.strip()
                        if line:
                            parts = line.split()
                            if len(parts) < 5:
                                validation_result["valid"] = False
                                validation_result["errors"].append(
                                    f"{label_filename}: 第 {line_num + 1} 行字段数量不足"
                                )
                                continue
                                
                            # 验证数值范围
                            try:
                                class_id = int(parts[0])
                                x_center = float(parts[1])
                                y_center = float(parts[2])
                                width = float(parts[3])
                                height = float(parts[4])
                                
                                # 验证坐标范围
                                if not (0 <= x_center <= 1 and 0 <= y_center <= 1 and 
                                        0 < width <= 1 and 0 < height <= 1):
                                    validation_result["valid"] = False
                                    validation_result["errors"].append(
                                        f"{label_filename}: 第 {line_num + 1} 行坐标范围无效"
                                    )
                                    
                            except Exception as e:
                                validation_result["valid"] = False
                                validation_result["errors"].append(
                                    f"{label_filename}: 第 {line_num + 1} 行格式错误 - {str(e)}"
                                )
                                
                except Exception as e:
                    validation_result["valid"] = False
                    validation_result["errors"].append(
                        f"{label_filename}: 读取文件出错 - {str(e)}"
                    )
                    
        return validation_result

class AnnotationManager:
    """标注管理器"""
    
    def __init__(self):
        """初始化标注管理器"""
        pass
        
    def create_annotation_tool(self, task_info, image_files, annotated_count):
        """创建标注工具实例
        
        Args:
            task_info: 任务信息
            image_files: 图片文件列表
            annotated_count: 已标注图片数量
            
        Returns:
            标注工具实例
        """
        return AnnotationTool(task_info, image_files, annotated_count)
        
    def validate_dataset_annotations(self, task_dir):
        """验证数据集的标注数据
        
        Args:
            task_dir: 任务目录
            
        Returns:
            验证结果
        """
        image_dir = os.path.join(task_dir, "dataset/images/train")
        label_dir = os.path.join(task_dir, "dataset/labels/train")
        
        image_files = [f for f in os.listdir(image_dir) if f.lower().endswith(('.jpg', '.jpeg', '.png', '.bmp'))]
        
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
                
                try:
                    with open(label_path, "r", encoding="utf-8") as f:
                        lines = f.readlines()
                        
                    for line_num, line in enumerate(lines):
                        line = line.strip()
                        if line:
                            parts = line.split()
                            if len(parts) < 5:
                                validation_result["valid"] = False
                                validation_result["errors"].append(
                                    f"{image_filename}: 标注文件格式错误"
                                )
                                break
                                
                            try:
                                class_id = int(parts[0])
                                x_center = float(parts[1])
                                y_center = float(parts[2])
                                width = float(parts[3])
                                height = float(parts[4])
                                
                                if not (0 <= x_center <= 1 and 0 <= y_center <= 1 and 
                                        0 < width <= 1 and 0 < height <= 1):
                                    validation_result["valid"] = False
                                    validation_result["errors"].append(
                                        f"{image_filename}: 标注坐标无效"
                                    )
                                    break
                                    
                            except Exception as e:
                                validation_result["valid"] = False
                                validation_result["errors"].append(
                                    f"{image_filename}: 标注格式错误 - {str(e)}"
                                )
                                break
                                
                except Exception as e:
                    validation_result["valid"] = False
                    validation_result["errors"].append(
                        f"{image_filename}: 读取标注文件出错 - {str(e)}"
                    )
                    
        return validation_result
        
    def get_dataset_annotation_statistics(self, task_dir):
        """获取数据集标注统计信息
        
        Args:
            task_dir: 任务目录
            
        Returns:
            统计信息字典
        """
        image_dir = os.path.join(task_dir, "dataset/images/train")
        label_dir = os.path.join(task_dir, "dataset/labels/train")
        
        image_files = [f for f in os.listdir(image_dir) if f.lower().endswith(('.jpg', '.jpeg', '.png', '.bmp'))]
        
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

# 全局标注管理器实例
annotation_manager = AnnotationManager()