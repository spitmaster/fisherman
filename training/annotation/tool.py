#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
训练模块 - 标注工具

提供可视化标注功能入口，采用Facade模式。
具体实现委托给子模块处理。

主要功能：
- 标注工具核心（来自原始实现）
- 标注验证（委托给validator.py）
- 标注导出（委托给exporter.py）
- 标注备份（委托给backup.py）
"""

import os
import logging
import cv2
from typing import Dict, Any, List, Optional

from .validator import (
    validate_single_annotation_file,
    validate_dataset_annotations,
    get_annotation_statistics as _get_annotation_statistics
)
from .exporter import AnnotationExporter
from ..backup import annotation_backup_manager

# 日志配置
logger = logging.getLogger(__name__)

# PyQt5可用性检查
try:
    from PyQt5.QtWidgets import QApplication, QMessageBox
    from PyQt5.QtCore import pyqtSignal, QObject
    PYQT_AVAILABLE = True
except ImportError:
    PYQT_AVAILABLE = False


class AnnotationTool:
    """可视化标注工具（Facade）
    
    采用Facade模式，统一管理标注功能的各个方面。
    """
    
    def __init__(self, task_info: Dict[str, Any], image_files: List[str], 
                 annotated_count: int, use_gui: bool = True):
        """初始化标注工具
        
        Args:
            task_info: 任务信息
            image_files: 图片文件列表
            annotated_count: 已标注数量
            use_gui: 是否使用GUI模式
        """
        self.task_info = task_info
        self.task_dir = task_info.get("task_dir", "")
        self.image_files = image_files
        self.current_image_index = 0
        self.current_annotations = []
        self.is_drawing = False
        self.start_point = (0, 0)
        self.end_point = (0, 0)
        self.use_gui = use_gui and PYQT_AVAILABLE
        
        # 类别管理
        self.class_names = {0: "object"}
        self.current_class_id = 0
        
        # 确保任务目录存在
        self._ensure_directories()
    
    def _ensure_directories(self):
        """确保必要的目录存在"""
        directories = [
            os.path.join(self.task_dir, "dataset/images/train"),
            os.path.join(self.task_dir, "dataset/labels/train"),
            os.path.join(self.task_dir, "annotations"),
            os.path.join(self.task_dir, "backup")
        ]
        
        for directory in directories:
            if not os.path.exists(directory):
                os.makedirs(directory, exist_ok=True)
    
    # ==================== 类别管理 ====================
    
    def set_class_names(self, class_names: Dict[int, str]):
        """设置类别名称映射"""
        self.class_names = class_names
        logger.info(f"设置类别名称: {class_names}")
    
    def set_current_class(self, class_id: int):
        """设置当前标注类别"""
        if class_id in self.class_names:
            self.current_class_id = class_id
    
    # ==================== 标注流程 ====================
    
    def start(self, use_gui: bool = None):
        """开始标注流程
        
        Args:
            use_gui: 是否使用GUI模式
        """
        if use_gui is not None:
            self.use_gui = use_gui and PYQT_AVAILABLE
        
        if self.use_gui:
            logger.info("启动GUI标注模式")
            return self._start_gui()
        else:
            logger.info("启动OpenCV标注模式")
            return self._start_opencv()
    
    def _start_gui(self) -> bool:
        """启动GUI标注"""
        if not PYQT_AVAILABLE:
            logger.warning("PyQt5不可用，回退到OpenCV模式")
            return self._start_opencv()
        
        try:
            from gui.annotation_window import open_annotation_window
            
            dataset_name = self.task_info.get("task_name", "default_dataset")
            gui_window = open_annotation_window(dataset_name)
            
            if gui_window:
                gui_window.class_names = self.class_names
                gui_window.annotation_saved.connect(self._on_annotation_saved)
                logger.info("GUI标注界面启动成功")
                return True
            return False
            
        except Exception as e:
            logger.error(f"启动GUI标注失败: {str(e)}", exc_info=True)
            return self._start_opencv()
    
    def _start_opencv(self) -> bool:
        """启动OpenCV标注"""
        try:
            window_name = "Fisherman - 标注工具"
            cv2.namedWindow(window_name, cv2.WINDOW_NORMAL)
            cv2.resizeWindow(window_name, 800, 600)
            cv2.setMouseCallback(window_name, self._handle_mouse_events)
            
            self._load_current_annotations()
            
            logger.info("OpenCV标注模式启动成功")
            logger.info("快捷键: S保存, D下一张, A上一张, Q退出, Backspace删除, R清空, C切换类别")
            
            return self._run_loop(window_name)
            
        except Exception as e:
            logger.error(f"启动OpenCV标注失败: {str(e)}", exc_info=True)
            return False
    
    def _run_loop(self, window_name: str) -> bool:
        """运行标注循环"""
        while True:
            image = self._load_current_image()
            if image is None:
                if not self._next_image():
                    break
                continue
            
            image_with_annotations = self._draw_annotations(image)
            self._show_status_info(image_with_annotations, window_name)
            
            cv2.imshow(window_name, image_with_annotations)
            
            key = cv2.waitKey(1) & 0xFF
            
            if key == ord('s') or key == ord('S'):
                if self._save_current_annotations():
                    logger.info("标注已保存")
            elif key == ord('d') or key == ord('D'):
                if not self._next_image():
                    logger.warning("已经是最后一张")
            elif key == ord('a') or key == ord('A'):
                if not self._previous_image():
                    logger.warning("已经是第一张")
            elif key == ord('q') or key == ord('Q'):
                break
            elif key == 8:  # Backspace
                if self.current_annotations:
                    self.current_annotations.pop()
            elif key == ord('r') or key == ord('R'):
                self.current_annotations = []
            elif key == ord('c') or key == ord('C'):
                self._cycle_class()
        
        cv2.destroyAllWindows()
        logger.info("标注流程结束")
        return True
    
    # ==================== 图片操作 ====================
    
    def _load_current_image(self):
        """加载当前图片"""
        if not self.image_files:
            return None
            
        image_filename = self.image_files[self.current_image_index]
        image_path = os.path.join(self.task_dir, "dataset/images/train", image_filename)
        
        if os.path.exists(image_path):
            return cv2.imread(image_path)
        
        logger.error(f"图片文件不存在: {image_path}")
        return None
    
    def _load_current_annotations(self):
        """加载当前图片的标注"""
        if not self.image_files:
            return
            
        image_filename = self.image_files[self.current_image_index]
        label_filename = os.path.splitext(image_filename)[0] + ".txt"
        label_path = os.path.join(self.task_dir, "dataset/labels/train", label_filename)
        
        self.current_annotations = []
        
        if os.path.exists(label_path):
            try:
                with open(label_path, "r", encoding="utf-8") as f:
                    for line in f:
                        line = line.strip()
                        if line:
                            parts = line.split()
                            if len(parts) >= 5:
                                self.current_annotations.append([
                                    int(parts[0]),
                                    float(parts[1]),
                                    float(parts[2]),
                                    float(parts[3]),
                                    float(parts[4])
                                ])
            except Exception as e:
                logger.error(f"加载标注失败: {e}")
    
    def _save_current_annotations(self) -> bool:
        """保存当前图片的标注"""
        if not self.image_files:
            return False
            
        image_filename = self.image_files[self.current_image_index]
        label_filename = os.path.splitext(image_filename)[0] + ".txt"
        label_path = os.path.join(self.task_dir, "dataset/labels/train", label_filename)
        
        try:
            with open(label_path, "w", encoding="utf-8") as f:
                for annotation in self.current_annotations:
                    class_id, x_center, y_center, width, height = annotation
                    f.write(f"{class_id} {x_center:.6f} {y_center:.6f} {width:.6f} {height:.6f}\n")
            
            return True
        except Exception as e:
            logger.error(f"保存标注失败: {e}")
            return False
    
    def _next_image(self) -> bool:
        """切换到下一张"""
        if self.current_image_index < len(self.image_files) - 1:
            self.current_image_index += 1
            self._load_current_annotations()
            return True
        return False
    
    def _previous_image(self) -> bool:
        """切换到上一张"""
        if self.current_image_index > 0:
            self.current_image_index -= 1
            self._load_current_annotations()
            return True
        return False
    
    def _cycle_class(self):
        """循环切换类别"""
        if not self.class_names:
            return
        class_ids = sorted(self.class_names.keys())
        if not class_ids:
            return
        current_index = class_ids.index(self.current_class_id)
        next_index = (current_index + 1) % len(class_ids)
        self.current_class_id = class_ids[next_index]
        logger.info(f"切换到类别: {self.current_class_id}")
    
    # ==================== 绘图 ====================
    
    def _draw_annotations(self, image):
        """绘制标注"""
        if image is None:
            return None
            
        img_copy = image.copy()
        h, w = img_copy.shape[:2]
        
        for annotation in self.current_annotations:
            class_id, x_center, y_center, width, height = annotation
            
            x1 = int((x_center - width / 2) * w)
            y1 = int((y_center - height / 2) * h)
            x2 = int((x_center + width / 2) * w)
            y2 = int((y_center + height / 2) * h)
            
            cv2.rectangle(img_copy, (x1, y1), (x2, y2), (0, 255, 0), 2)
            
            label = f"Class {class_id}"
            cv2.putText(img_copy, label, (x1, y1 - 5),
                       cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 255, 0), 1)
        
        if self.is_drawing:
            cv2.rectangle(img_copy, self.start_point, self.end_point, (0, 0, 255), 2)
        
        return img_copy
    
    def _show_status_info(self, image, window_name):
        """显示状态信息"""
        h, w = image.shape[:2]
        
        status_text = (f"图片: {self.current_image_index + 1}/{len(self.image_files)} | "
                      f"标注: {len(self.current_annotations)} | "
                      f"类别: {self.current_class_id} | "
                      f"快捷键: S保存/D下一张/A回退/Q退出")
        
        cv2.putText(image, status_text, (5, h - 10),
                   cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 255, 255), 1)
    
    def _handle_mouse_events(self, event, x, y, flags, param):
        """处理鼠标事件"""
        if event == cv2.EVENT_LBUTTONDOWN:
            self.is_drawing = True
            self.start_point = (x, y)
            self.end_point = (x, y)
        elif event == cv2.EVENT_MOUSEMOVE and self.is_drawing:
            self.end_point = (x, y)
        elif event == cv2.EVENT_LBUTTONUP:
            self.is_drawing = False
            if self.start_point != self.end_point:
                x1 = min(self.start_point[0], self.end_point[0])
                y1 = min(self.start_point[1], self.end_point[1])
                x2 = max(self.start_point[0], self.end_point[0])
                y2 = max(self.start_point[1], self.end_point[1])
                
                image = self._load_current_image()
                if image is not None:
                    h, w = image.shape[:2]
                    annotation = [
                        self.current_class_id,
                        (x1 + x2) / 2 / w,
                        (y1 + y2) / 2 / h,
                        (x2 - x1) / w,
                        (y2 - y1) / h
                    ]
                    self.current_annotations.append(annotation)
    
    def _on_annotation_saved(self, label_file_path: str):
        """GUI标注保存回调"""
        logger.info(f"标注已保存: {label_file_path}")
    
    # ==================== 验证功能 ====================
    
    def validate_annotations(self) -> Dict[str, Any]:
        """验证标注数据
        
        Returns:
            验证结果字典
        """
        return validate_dataset_annotations(self.task_dir)
    
    def get_annotation_statistics(self) -> Dict[str, Any]:
        """获取标注统计信息
        
        Returns:
            统计信息字典
        """
        return _get_annotation_statistics(self.task_dir)
    
    # ==================== 导出功能 ====================
    
    def export_annotations(self, export_format: str, export_dir: str = None) -> bool:
        """导出标注数据
        
        Args:
            export_format: 导出格式 ('yolo', 'coco', 'voc', 'csv')
            export_dir: 导出目录
            
        Returns:
            导出是否成功
        """
        exporter = AnnotationExporter({
            "task_dir": self.task_dir,
            "class_names": self.class_names
        })
        return exporter.export(export_format, export_dir)
    
    # ==================== 备份恢复 ====================
    
    def create_backup(self) -> str:
        """创建标注备份
        
        Returns:
            备份路径
        """
        return annotation_backup_manager.create_annotation_backup({
            "task_dir": self.task_dir
        })
    
    def restore_backup(self, backup_path: str) -> bool:
        """恢复标注备份
        
        Args:
            backup_path: 备份路径
            
        Returns:
            恢复是否成功
        """
        return annotation_backup_manager.restore_annotation_backup({
            "task_dir": self.task_dir
        }, backup_path)
    
    # ==================== 进度信息 ====================
    
    def get_progress(self) -> Dict[str, Any]:
        """获取标注进度
        
        Returns:
            进度信息字典
        """
        annotated = 0
        for img_file in self.image_files:
            label_file = os.path.splitext(img_file)[0] + ".txt"
            label_path = os.path.join(self.task_dir, "dataset/labels/train", label_file)
            if os.path.exists(label_path) and os.path.getsize(label_path) > 0:
                annotated += 1
        
        total = len(self.image_files)
        
        return {
            "total_images": total,
            "annotated_images": annotated,
            "current_index": self.current_image_index + 1,
            "progress": (annotated / total * 100) if total > 0 else 0
        }


class AnnotationManager:
    """标注管理器（Facade）
    
    简化版的标注管理器，提供统一的标注入口。
    """
    
    def __init__(self):
        """初始化标注管理器"""
        pass
    
    def create_annotation_tool(self, task_info: Dict[str, Any], 
                            image_files: List[str], 
                            annotated_count: int) -> AnnotationTool:
        """创建标注工具实例
        
        Args:
            task_info: 任务信息
            image_files: 图片文件列表
            annotated_count: 已标注数量
            
        Returns:
            标注工具实例
        """
        return AnnotationTool(task_info, image_files, annotated_count)
    
    def validate_dataset(self, task_dir: str) -> Dict[str, Any]:
        """验证数据集标注
        
        Args:
            task_dir: 任务目录
            
        Returns:
            验证结果
        """
        return validate_dataset_annotations(task_dir)
    
    def get_statistics(self, task_dir: str) -> Dict[str, Any]:
        """获取标注统计
        
        Args:
            task_dir: 任务目录
            
        Returns:
            统计信息
        """
        return _get_annotation_statistics(task_dir)


# 全局标注管理器实例
annotation_manager = AnnotationManager()
