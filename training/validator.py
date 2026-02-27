#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
训练模块 - 训练验证器

负责验证训练任务配置、数据集、标注数据等的合法性。
采用单一职责原则，只负责验证相关功能。
"""

import os
import logging
from typing import Dict, Any, Tuple, List
from pathlib import Path

logger = logging.getLogger(__name__)


class TrainingValidator:
    """训练验证器
    
    负责验证训练任务的各种配置和数据是否符合要求。
    """
    
    # 有效状态列表
    VALID_STATUSES = ['pending', 'annotating', 'training', 'completed', 'failed', 'stopped']
    
    # 最小配置值
    MIN_EPOCHS = 1
    MAX_EPOCHS = 1000
    MIN_BATCH_SIZE = 1
    MAX_BATCH_SIZE = 128
    MIN_LEARNING_RATE = 1e-6
    MAX_LEARNING_RATE = 1.0
    
    def __init__(self):
        """初始化验证器"""
        self._errors: List[str] = []
        self._warnings: List[str] = []
    
    def reset(self):
        """重置验证结果"""
        self._errors = []
        self._warnings = []
    
    @property
    def errors(self) -> List[str]:
        """获取验证错误列表"""
        return self._errors.copy()
    
    @property
    def warnings(self) -> List[str]:
        """获取验证警告列表"""
        return self._warnings.copy()
    
    @property
    def is_valid(self) -> bool:
        """验证是否通过"""
        return len(self._errors) == 0
    
    def validate_task_for_training(self, task_info: Dict[str, Any], dataset_info: Dict[str, Any]) -> Tuple[bool, str]:
        """验证训练任务是否可以进行训练
        
        Args:
            task_info: 任务信息字典
            dataset_info: 数据集信息字典
            
        Returns:
            (验证结果, 错误消息)
        """
        self.reset()
        
        # 检查任务信息
        if not task_info:
            return False, "任务信息为空"
        
        # 检查任务状态
        status = task_info.get("status", "")
        if status not in ["pending", "annotating"]:
            return False, f"任务状态不适合开始训练: {status}"
        
        # 检查标注数据
        annotated_images = task_info.get("annotated_images", 0)
        if annotated_images == 0:
            return False, "标注数据不足，无法开始训练"
        
        # 检查数据集
        if not dataset_info or dataset_info.get("total_images", 0) == 0:
            return False, "数据集为空，无法开始训练"
        
        # 检查YAML配置文件
        task_name = task_info.get("task_name", "")
        task_dir = os.path.join("training_data", task_name)
        yaml_path = os.path.join(task_dir, "data.yaml")
        
        if not os.path.exists(yaml_path):
            return False, f"数据配置文件不存在: {yaml_path}"
        
        # 检查模型输出目录
        models_dir = os.path.join(task_dir, "models")
        if not os.path.exists(models_dir):
            os.makedirs(models_dir, exist_ok=True)
        
        if self._warnings:
            logger.warning(f"任务验证警告: {', '.join(self._warnings)}")
        
        return True, "任务验证通过"
    
    def validate_training_config(self, config: Dict[str, Any]) -> Tuple[bool, str]:
        """验证训练配置参数
        
        Args:
            config: 训练配置字典
            
        Returns:
            (验证结果, 错误消息)
        """
        self.reset()
        
        # 必需参数检查
        required_params = ["epochs", "batch_size"]
        for param in required_params:
            if param not in config:
                self._errors.append(f"缺少必需参数: {param}")
        
        if self._errors:
            return False, "; ".join(self._errors)
        
        # 参数范围验证 - epochs
        epochs = config.get("epochs", 0)
        if epochs <= 0:
            self._errors.append("epochs必须大于0")
        elif epochs > self.MAX_EPOCHS:
            self._errors.append(f"epochs不能超过{self.MAX_EPOCHS}")
        
        # 参数范围验证 - batch_size
        batch_size = config.get("batch_size", 0)
        if batch_size <= 0:
            self._errors.append("batch_size必须大于0")
        elif batch_size > self.MAX_BATCH_SIZE:
            self._errors.append(f"batch_size不能超过{self.MAX_BATCH_SIZE}")
        
        # 学习率验证（如果提供）
        if "learning_rate" in config:
            lr = config["learning_rate"]
            if lr <= 0:
                self._errors.append("learning_rate必须大于0")
            elif lr > self.MAX_LEARNING_RATE:
                self._errors.append(f"learning_rate不能超过{self.MAX_LEARNING_RATE}")
        
        # 图像大小验证
        if "imgsz" in config:
            imgsz = config["imgsz"]
            if not isinstance(imgsz, int) or imgsz < 32 or imgsz > 4096:
                self._errors.append("imgsz必须是32到4096之间的整数")
        
        if self._errors:
            return False, "; ".join(self._errors)
        
        return True, "配置验证通过"
    
    def validate_status(self, status: str) -> Tuple[bool, str]:
        """验证任务状态
        
        Args:
            status: 任务状态字符串
            
        Returns:
            (验证结果, 错误消息)
        """
        if status not in self.VALID_STATUSES:
            return False, f"无效的任务状态: {status}，有效状态: {', '.join(self.VALID_STATUSES)}"
        return True, ""
    
    def validate_dataset_path(self, dataset_path: str) -> Tuple[bool, str]:
        """验证数据集路径
        
        Args:
            dataset_path: 数据集路径
            
        Returns:
            (验证结果, 错误消息)
        """
        if not dataset_path:
            return False, "数据集路径为空"
        
        if not os.path.exists(dataset_path):
            return False, f"数据集路径不存在: {dataset_path}"
        
        # 检查必要的子目录
        image_dir = os.path.join(dataset_path, "images", "train")
        if not os.path.exists(image_dir):
            self._warnings.append(f"训练图片目录不存在: {image_dir}")
        
        label_dir = os.path.join(dataset_path, "labels", "train")
        if not os.path.exists(label_dir):
            self._warnings.append(f"训练标签目录不存在: {label_dir}")
        
        return True, ""
    
    def validate_image_files(self, image_dir: str) -> Tuple[bool, str]:
        """验证图片文件
        
        Args:
            image_dir: 图片目录
            
        Returns:
            (验证结果, 错误消息)
        """
        if not os.path.exists(image_dir):
            return False, f"图片目录不存在: {image_dir}"
        
        valid_extensions = ('.jpg', '.jpeg', '.png', '.bmp')
        image_files = [f for f in os.listdir(image_dir) 
                      if f.lower().endswith(valid_extensions)]
        
        if not image_files:
            return False, f"目录中没有图片文件: {image_dir}"
        
        return True, f"找到 {len(image_files)} 个图片文件"
    
    def validate_label_format(self, label_path: str) -> Tuple[bool, str]:
        """验证单个标签文件格式
        
        Args:
            label_path: 标签文件路径
            
        Returns:
            (验证结果, 错误消息)
        """
        if not os.path.exists(label_path):
            return False, f"标签文件不存在: {label_path}"
        
        if os.path.getsize(label_path) == 0:
            return True, ""  # 空文件是合法的（表示没有标注）
        
        try:
            with open(label_path, 'r', encoding='utf-8') as f:
                lines = f.readlines()
            
            for line_num, line in enumerate(lines):
                line = line.strip()
                if not line:
                    continue
                
                parts = line.split()
                if len(parts) < 5:
                    return False, f"第{line_num+1}行字段数量不足，需要5个字段（class_id, x_center, y_center, width, height）"
                
                try:
                    class_id = int(parts[0])
                    x_center = float(parts[1])
                    y_center = float(parts[2])
                    width = float(parts[3])
                    height = float(parts[4])
                    
                    # 验证坐标范围
                    if not (0 <= x_center <= 1 and 0 <= y_center <= 1 and 
                            0 < width <= 1 and 0 < height <= 1):
                        return False, f"第{line_num+1}行坐标范围无效（应在0-1之间）"
                        
                except ValueError as e:
                    return False, f"第{line_num+1}行格式错误: {str(e)}"
            
            return True, ""
            
        except Exception as e:
            return False, f"读取标签文件失败: {str(e)}"


class DatasetValidator:
    """数据集验证器
    
    负责验证数据集的完整性和合法性。
    """
    
    def __init__(self):
        """初始化数据集验证器"""
        self._errors: List[str] = []
        self._warnings: List[str] = []
    
    def reset(self):
        """重置验证结果"""
        self._errors = []
        self._warnings = []
    
    @property
    def errors(self) -> List[str]:
        return self._errors.copy()
    
    @property
    def warnings(self) -> List[str]:
        return self._warnings.copy()
    
    @property
    def is_valid(self) -> bool:
        return len(self._errors) == 0
    
    def validate_dataset_structure(self, task_dir: str) -> Tuple[bool, str]:
        """验证数据集目录结构
        
        Args:
            task_dir: 任务目录
            
        Returns:
            (验证结果, 错误消息)
        """
        self.reset()
        
        if not os.path.exists(task_dir):
            self._errors.append(f"任务目录不存在: {task_dir}")
            return False, "; ".join(self._errors)
        
        # 检查必要的子目录
        required_dirs = [
            "dataset/images/train",
            "dataset/labels/train"
        ]
        
        for dir_path in required_dirs:
            full_path = os.path.join(task_dir, dir_path)
            if not os.path.exists(full_path):
                self._errors.append(f"缺少必要目录: {dir_path}")
        
        # 检查可选目录
        optional_dirs = [
            "dataset/images/val",
            "dataset/images/test",
            "dataset/labels/val",
            "dataset/labels/test"
        ]
        
        for dir_path in optional_dirs:
            full_path = os.path.join(task_dir, dir_path)
            if not os.path.exists(full_path):
                self._warnings.append(f"可选目录不存在: {dir_path}")
        
        if self._errors:
            return False, "; ".join(self._errors)
        
        msg = "数据集结构验证通过"
        if self._warnings:
            msg += f"（警告: {', '.join(self._warnings)}）"
        return True, msg
    
    def validate_image_label_pairs(self, task_dir: str) -> Dict[str, Any]:
        """验证图片和标签的配对情况
        
        Args:
            task_dir: 任务目录
            
        Returns:
            验证结果字典
        """
        self.reset()
        
        image_dir = os.path.join(task_dir, "dataset/images/train")
        label_dir = os.path.join(task_dir, "dataset/labels/train")
        
        if not os.path.exists(image_dir):
            self._errors.append("图片目录不存在")
            return {"valid": False, "errors": self._errors}
        
        # 获取图片文件
        valid_extensions = ('.jpg', '.jpeg', '.png', '.bmp')
        image_files = {os.path.splitext(f)[0]: f 
                      for f in os.listdir(image_dir) 
                      if f.lower().endswith(valid_extensions)}
        
        # 获取标签文件
        label_files = set()
        if os.path.exists(label_dir):
            label_files = {os.path.splitext(f)[0] 
                          for f in os.listdir(label_dir) 
                          if f.endswith('.txt')}
        
        # 分类图片
        annotated = []
        unannotated = []
        orphan_labels = []
        
        for img_name, img_file in image_files.items():
            if img_name in label_files:
                annotated.append(img_file)
            else:
                unannotated.append(img_file)
        
        for label_name in label_files:
            if label_name not in image_files:
                orphan_labels.append(label_name + ".txt")
        
        result = {
            "total_images": len(image_files),
            "annotated_count": len(annotated),
            "unannotated_count": len(unannotated),
            "orphan_labels_count": len(orphan_labels),
            "annotated_images": annotated[:10],  # 只返回前10个作为示例
            "unannotated_images": unannotated[:10],
            "orphan_labels": orphan_labels[:10],
            "valid": len(self._errors) == 0,
            "errors": self._errors,
            "warnings": self._warnings
        }
        
        # 如果有孤立标签，给出警告
        if orphan_labels:
            self._warnings.append(f"存在{len(orphan_labels)}个孤立标签文件（没有对应的图片）")
        
        return result


# 全局验证器实例
training_validator = TrainingValidator()
dataset_validator = DatasetValidator()
