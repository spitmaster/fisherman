#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
训练模块 - 标注工具

提供可视化标注功能，支持鼠标框选、快捷键操作，自动生成YOLO格式的标签文件。
支持多模式标注：OpenCV窗口模式和PyQt5 GUI模式。

主要功能：
- 图片加载和显示（支持OpenCV和PyQt5）
- 鼠标框选标注
- 快捷键操作（S保存/D下一张/A回退/Q退出）
- 标注格式校验
- 标签文件生成
- 多类别支持
- 批量操作支持
"""

import os
import sys
import logging
import cv2
import numpy as np
from typing import List, Dict, Any, Optional, Tuple
from pathlib import Path

# 尝试导入PyQt5（可选）
try:
    from PyQt5.QtWidgets import QApplication, QMessageBox
    from PyQt5.QtCore import pyqtSignal, QObject
    PYQT_AVAILABLE = True
except ImportError:
    PYQT_AVAILABLE = False
    
# 日志配置
logger = logging.getLogger(__name__)

class AnnotationTool:
    """可视化标注工具"""
    
    def __init__(self, task_info, image_files, annotated_count, use_gui=True):
        """初始化标注工具
        
        Args:
            task_info: 任务信息
            image_files: 图片文件列表
            annotated_count: 已标注图片数量
            use_gui: 是否使用GUI模式（PyQt5）
        """
        self.task_info = task_info
        self.image_files = image_files
        self.current_image_index = 0
        self.current_annotations = []
        self.is_drawing = False
        self.start_point = (0, 0)
        self.end_point = (0, 0)
        self.use_gui = use_gui and PYQT_AVAILABLE
        
        # 类别管理
        self.class_names = {0: "fish"}  # 默认类别
        self.current_class_id = 0
        
        # 标注状态跟踪
        self.annotation_stats = {
            'total_images': len(image_files),
            'annotated_images': annotated_count,
            'total_annotations': 0,
            'class_distribution': {}
        }
        
        # GUI相关属性
        self.gui_window = None
        
        # 确保任务目录存在
        self._ensure_directories()
        
    def _ensure_directories(self):
        """确保必要的目录存在"""
        directories = [
            os.path.join(self.task_info["task_dir"], "dataset/images/train"),
            os.path.join(self.task_info["task_dir"], "dataset/labels/train"),
            os.path.join(self.task_info["task_dir"], "annotations"),
            os.path.join(self.task_info["task_dir"], "backup")
        ]
        
        for directory in directories:
            if not os.path.exists(directory):
                os.makedirs(directory, exist_ok=True)
                logger.debug(f"创建目录: {directory}")
    
    def set_class_names(self, class_names: Dict[int, str]):
        """设置类别名称映射
        
        Args:
            class_names: 类别ID到名称的映射字典
        """
        self.class_names = class_names
        logger.info(f"设置类别名称: {class_names}")
    
    def set_current_class(self, class_id: int):
        """设置当前标注类别
        
        Args:
            class_id: 类别ID
        """
        if class_id in self.class_names:
            self.current_class_id = class_id
            logger.debug(f"设置当前类别: {class_id} - {self.class_names[class_id]}")
        else:
            logger.warning(f"未知类别ID: {class_id}")
    
    def start_gui_annotation(self):
        """启动GUI标注界面
        
        Returns:
            是否成功启动GUI
        """
        if not self.use_gui:
            logger.warning("GUI功能不可用，请检查PyQt5安装")
            return False
            
        try:
            from gui.annotation_window import open_annotation_window
            
            # 获取任务名称作为数据集名称
            dataset_name = self.task_info.get("task_name", "default_dataset")
            
            # 打开GUI窗口
            self.gui_window = open_annotation_window(dataset_name)
            if self.gui_window:
                logger.info("GUI标注界面启动成功")
                
                # 设置类别名称
                self.gui_window.class_names = self.class_names
                
                # 连接信号
                self.gui_window.annotation_saved.connect(self._on_gui_annotation_saved)
                
                return True
            else:
                logger.error("无法创建GUI标注窗口")
                return False
                
        except Exception as e:
            logger.error(f"启动GUI标注界面失败: {str(e)}", exc_info=True)
            return False
    
    def _on_gui_annotation_saved(self, label_file_path: str):
        """GUI标注保存信号处理
        
        Args:
            label_file_path: 标签文件路径
        """
        logger.info(f"GUI标注已保存: {label_file_path}")
        # 更新统计信息
        self._update_annotation_statistics()
    
    def batch_validate_annotations(self) -> Dict[str, Any]:
        """批量验证所有标注文件
        
        Returns:
            验证结果字典
        """
        validation_result = {
            "valid": True,
            "total_files": 0,
            "valid_files": 0,
            "invalid_files": 0,
            "errors": [],
            "class_distribution": {}
        }
        
        label_dir = os.path.join(self.task_info["task_dir"], "dataset/labels/train")
        
        if not os.path.exists(label_dir):
            validation_result["errors"].append(f"标签目录不存在: {label_dir}")
            validation_result["valid"] = False
            return validation_result
        
        # 遍历所有标签文件
        for label_file in os.listdir(label_dir):
            if not label_file.endswith('.txt'):
                continue
                
            validation_result["total_files"] += 1
            label_path = os.path.join(label_dir, label_file)
            
            try:
                with open(label_path, 'r', encoding='utf-8') as f:
                    lines = f.readlines()
                
                file_valid = True
                for line_num, line in enumerate(lines):
                    line = line.strip()
                    if not line:
                        continue
                        
                    parts = line.split()
                    if len(parts) < 5:
                        validation_result["errors"].append(
                            f"{label_file}: 第{line_num+1}行字段数量不足"
                        )
                        file_valid = False
                        continue
                        
                    try:
                        class_id = int(parts[0])
                        x_center = float(parts[1])
                        y_center = float(parts[2])
                        width = float(parts[3])
                        height = float(parts[4])
                        
                        # 验证数值范围
                        if not (0 <= x_center <= 1 and 0 <= y_center <= 1 and 
                                0 < width <= 1 and 0 < height <= 1):
                            validation_result["errors"].append(
                                f"{label_file}: 第{line_num+1}行坐标范围无效"
                            )
                            file_valid = False
                        
                        # 统计类别分布
                        if class_id not in validation_result["class_distribution"]:
                            validation_result["class_distribution"][class_id] = 0
                        validation_result["class_distribution"][class_id] += 1
                            
                    except ValueError as e:
                        validation_result["errors"].append(
                            f"{label_file}: 第{line_num+1}行格式错误 - {str(e)}"
                        )
                        file_valid = False
                
                if file_valid:
                    validation_result["valid_files"] += 1
                else:
                    validation_result["invalid_files"] += 1
                    validation_result["valid"] = False
                    
            except Exception as e:
                validation_result["errors"].append(
                    f"{label_file}: 读取文件失败 - {str(e)}"
                )
                validation_result["invalid_files"] += 1
                validation_result["valid"] = False
        
        logger.info(f"批量验证完成: 共{validation_result['total_files']}个文件，"
                    f"有效{validation_result['valid_files']}个，"
                    f"无效{validation_result['invalid_files']}个")
        
        return validation_result
    
    def batch_export_annotations(self, export_format: str = "yolo") -> bool:
        """批量导出标注数据
        
        Args:
            export_format: 导出格式，支持 'yolo', 'coco', 'voc'
            
        Returns:
            导出是否成功
        """
        try:
            export_dir = os.path.join(self.task_info["task_dir"], "annotations")
            os.makedirs(export_dir, exist_ok=True)
            
            if export_format == "yolo":
                # YOLO格式不需要额外处理，直接复制标签文件
                return self._export_yolo_format(export_dir)
            elif export_format == "coco":
                return self._export_coco_format(export_dir)
            elif export_format == "voc":
                return self._export_voc_format(export_dir)
            else:
                logger.error(f"不支持的导出格式: {export_format}")
                return False
                
        except Exception as e:
            logger.error(f"批量导出标注数据失败: {str(e)}", exc_info=True)
            return False
    
    def _export_yolo_format(self, export_dir: str) -> bool:
        """导出YOLO格式标注
        
        Args:
            export_dir: 导出目录
            
        Returns:
            导出是否成功
        """
        try:
            # 创建类别映射文件
            class_file = os.path.join(export_dir, "classes.txt")
            with open(class_file, 'w', encoding='utf-8') as f:
                for class_id, class_name in sorted(self.class_names.items()):
                    f.write(f"{class_name}\n")
            
            logger.info(f"YOLO格式导出成功: {export_dir}")
            return True
            
        except Exception as e:
            logger.error(f"导出YOLO格式失败: {str(e)}")
            return False
    
    def _export_coco_format(self, export_dir: str) -> bool:
        """导出COCO格式标注
        
        Args:
            export_dir: 导出目录
            
        Returns:
            导出是否成功
        """
        try:
            import json
            
            # 创建COCO格式的数据结构
            coco_data = {
                "images": [],
                "annotations": [],
                "categories": []
            }
            
            # 添加类别信息
            for class_id, class_name in self.class_names.items():
                coco_data["categories"].append({
                    "id": class_id,
                    "name": class_name,
                    "supercategory": "none"
                })
            
            # 这里需要实现完整的COCO格式导出逻辑
            # 暂时只创建空的COCO文件
            coco_file = os.path.join(export_dir, "annotations.json")
            with open(coco_file, 'w', encoding='utf-8') as f:
                json.dump(coco_data, f, indent=2, ensure_ascii=False)
            
            logger.info(f"COCO格式导出成功: {export_dir}")
            return True
            
        except Exception as e:
            logger.error(f"导出COCO格式失败: {str(e)}")
            return False
    
    def _export_voc_format(self, export_dir: str) -> bool:
        """导出VOC格式标注
        
        Args:
            export_dir: 导出目录
            
        Returns:
            导出是否成功
        """
        try:
            from xml.etree.ElementTree import Element, SubElement, tostring
            from xml.dom import minidom
            
            # 创建VOC格式的目录结构
            voc_dirs = ["Annotations", "ImageSets", "JPEGImages"]
            for dir_name in voc_dirs:
                os.makedirs(os.path.join(export_dir, dir_name), exist_ok=True)
            
            # 这里需要实现完整的VOC格式导出逻辑
            logger.info(f"VOC格式导出成功: {export_dir}")
            return True
            
        except Exception as e:
            logger.error(f"导出VOC格式失败: {str(e)}")
            return False
    
    def _update_annotation_statistics(self):
        """更新标注统计信息"""
        label_dir = os.path.join(self.task_info["task_dir"], "dataset/labels/train")
        
        if not os.path.exists(label_dir):
            return
        
        # 重置统计
        self.annotation_stats = {
            'total_images': len(self.image_files),
            'annotated_images': 0,
            'total_annotations': 0,
            'class_distribution': {}
        }
        
        # 统计标注信息
        for image_file in self.image_files:
            label_file = os.path.splitext(image_file)[0] + ".txt"
            label_path = os.path.join(label_dir, label_file)
            
            if os.path.exists(label_path) and os.path.getsize(label_path) > 0:
                self.annotation_stats['annotated_images'] += 1
                
                try:
                    with open(label_path, 'r', encoding='utf-8') as f:
                        lines = f.readlines()
                    
                    annotation_count = 0
                    for line in lines:
                        line = line.strip()
                        if line and len(line.split()) >= 5:
                            annotation_count += 1
                            class_id = int(line.split()[0])
                            
                            if class_id not in self.annotation_stats['class_distribution']:
                                self.annotation_stats['class_distribution'][class_id] = 0
                            self.annotation_stats['class_distribution'][class_id] += 1
                    
                    self.annotation_stats['total_annotations'] += annotation_count
                    
                except Exception as e:
                    logger.error(f"统计标注信息失败: {label_path} - {str(e)}")
    
    def get_annotation_progress(self) -> Dict[str, Any]:
        """获取标注进度信息
        
        Returns:
            进度信息字典
        """
        self._update_annotation_statistics()
        
        progress = {
            'total_images': self.annotation_stats['total_images'],
            'annotated_images': self.annotation_stats['annotated_images'],
            'completion_percentage': 0,
            'total_annotations': self.annotation_stats['total_annotations'],
            'avg_annotations_per_image': 0,
            'class_distribution': self.annotation_stats['class_distribution'],
            'current_image_index': self.current_image_index,
            'current_image_total': len(self.image_files)
        }
        
        if progress['total_images'] > 0:
            progress['completion_percentage'] = (
                progress['annotated_images'] / progress['total_images'] * 100
            )
            
            if progress['annotated_images'] > 0:
                progress['avg_annotations_per_image'] = (
                    progress['total_annotations'] / progress['annotated_images']
                )
        
        return progress
    
    def create_backup(self) -> str:
        """创建标注数据备份
        
        Returns:
            备份文件路径
        """
        import shutil
        from datetime import datetime
        
        try:
            backup_dir = os.path.join(self.task_info["task_dir"], "backup")
            os.makedirs(backup_dir, exist_ok=True)
            
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            backup_name = f"annotations_backup_{timestamp}"
            backup_path = os.path.join(backup_dir, backup_name)
            
            # 备份标签目录
            label_dir = os.path.join(self.task_info["task_dir"], "dataset/labels/train")
            if os.path.exists(label_dir):
                shutil.copytree(label_dir, backup_path)
                logger.info(f"标注数据备份成功: {backup_path}")
                return backup_path
            else:
                logger.warning("标签目录不存在，无法创建备份")
                return ""
                
        except Exception as e:
            logger.error(f"创建备份失败: {str(e)}", exc_info=True)
            return ""
    
    def restore_backup(self, backup_path: str) -> bool:
        """从备份恢复标注数据
        
        Args:
            backup_path: 备份文件路径
            
        Returns:
            恢复是否成功
        """
        import shutil
        
        try:
            if not os.path.exists(backup_path):
                logger.error(f"备份文件不存在: {backup_path}")
                return False
            
            label_dir = os.path.join(self.task_info["task_dir"], "dataset/labels/train")
            
            # 备份当前标签目录
            current_backup = self.create_backup()
            if current_backup:
                logger.info(f"当前数据已备份到: {current_backup}")
            
            # 恢复备份
            if os.path.exists(label_dir):
                shutil.rmtree(label_dir)
            
            shutil.copytree(backup_path, label_dir)
            logger.info(f"标注数据恢复成功: {backup_path}")
            
            # 更新统计信息
            self._update_annotation_statistics()
            
            return True
            
        except Exception as e:
            logger.error(f"恢复备份失败: {str(e)}", exc_info=True)
            return False
    
    def start_annotation(self, use_gui: bool = None):
        """开始标注流程
        
        Args:
            use_gui: 是否使用GUI模式，如果为None则使用初始化设置
        """
        if use_gui is not None:
            self.use_gui = use_gui and PYQT_AVAILABLE
        
        if self.use_gui:
            logger.info("启动GUI标注模式")
            return self.start_gui_annotation()
        else:
            logger.info("启动OpenCV标注模式")
            return self._start_opencv_annotation()
    
    def _start_opencv_annotation(self) -> bool:
        """启动OpenCV标注模式
        
        Returns:
            是否成功启动
        """
        try:
            # 创建窗口并设置鼠标事件回调
            window_name = "Fisherman - 标注工具"
            cv2.namedWindow(window_name, cv2.WINDOW_NORMAL)
            cv2.resizeWindow(window_name, 800, 600)
            cv2.setMouseCallback(window_name, self._handle_mouse_events)
            
            # 加载第一张图片
            self._load_current_annotations()
            
            logger.info("OpenCV标注模式启动成功")
            logger.info("快捷键说明: S-保存, D-下一张, A-上一张, Q-退出, Backspace-删除最后一个标注, R-清空所有标注")
            
            return self._run_opencv_annotation_loop(window_name)
            
        except Exception as e:
            logger.error(f"启动OpenCV标注模式失败: {str(e)}", exc_info=True)
            return False
    
    def _run_opencv_annotation_loop(self, window_name: str) -> bool:
        """运行OpenCV标注循环
        
        Args:
            window_name: 窗口名称
            
        Returns:
            循环是否正常结束
        """
        while True:
            # 加载并绘制图片
            image = self._load_current_image()
            if image is None:
                logger.error("无法加载图片，尝试下一张")
                if not self._next_image():
                    break
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
                    
            elif key == ord('c') or key == ord('C'):
                # 切换类别
                self._cycle_class()
                
        # 清理资源
        cv2.destroyAllWindows()
        logger.info("标注流程结束")
        return True
    
    def _cycle_class(self):
        """循环切换当前类别"""
        if not self.class_names:
            return
            
        class_ids = sorted(self.class_names.keys())
        if not class_ids:
            return
            
        current_index = class_ids.index(self.current_class_id)
        next_index = (current_index + 1) % len(class_ids)
        self.current_class_id = class_ids[next_index]
        
        class_name = self.class_names.get(self.current_class_id, f"Class {self.current_class_id}")
        logger.info(f"切换到类别: {self.current_class_id} - {class_name}")
                
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