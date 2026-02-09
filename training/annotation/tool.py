#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
训练模块 - 标注工具

提供可视化标注功能，支持鼠标框选、快捷键操作，自动生成YOLO格式的标签文件。
"""

import os
import sys
import logging
import cv2
import numpy as np
from PIL import Image, ImageDraw, ImageFont

from .visualizer import draw_annotations, show_status_info
from .yolo_formatter import convert_bbox_to_yolo, convert_yolo_to_bbox, validate_yolo_annotation
from .validator import validate_single_annotation_file, validate_dataset_annotations, get_annotation_statistics

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
                    annotation = convert_bbox_to_yolo(image, (x1, y1, x2, y2))
                    self.current_annotations.append(annotation)
                    logger.info(f"添加标注: {annotation}")
                    
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
            image_with_annotations = draw_annotations(image, self.current_annotations, 
                                                     self.is_drawing, self.start_point, self.end_point)
            image_with_status = show_status_info(image_with_annotations, self.current_image_index, 
                                               len(self.image_files), len(self.current_annotations), window_name)
            
            # 显示图片
            cv2.imshow(window_name, image_with_status)
            
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
                valid, errors = validate_single_annotation_file(label_path, label_filename)
                if not valid:
                    validation_result["valid"] = False
                    validation_result["errors"].extend(errors)
        
        return validation_result