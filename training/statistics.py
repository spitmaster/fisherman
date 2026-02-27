#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
训练模块 - 训练统计模块

负责收集、计算和提供训练任务的各种统计信息。
采用单一职责原则，只负责统计相关功能。
"""

import os
import logging
from typing import Dict, Any, List, Optional
from datetime import datetime

logger = logging.getLogger(__name__)


class TrainingStatistics:
    """训练统计类
    
    负责收集和计算训练任务的统计信息。
    """
    
    def __init__(self):
        """初始化统计类"""
        pass
    
    def get_task_statistics(self, task_id: int, task_info: Dict[str, Any], 
                          dataset_info: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """获取训练任务的统计信息
        
        Args:
            task_id: 任务ID
            task_info: 任务信息字典
            dataset_info: 数据集信息字典（可选）
            
        Returns:
            统计信息字典
        """
        try:
            statistics = {
                "task_id": task_id,
                "task_name": task_info.get("task_name", ""),
                "status": task_info.get("status", ""),
                "created_at": "",
                "total_images": 0,
                "annotated_images": 0,
                "annotation_progress": 0,
                "training_metrics": {}
            }
            
            # 格式化创建时间
            created_at = task_info.get("created_at")
            if created_at:
                if isinstance(created_at, datetime):
                    statistics["created_at"] = created_at.strftime("%Y-%m-%d %H:%M:%S")
                else:
                    statistics["created_at"] = str(created_at)
            
            # 数据集统计
            if dataset_info:
                statistics["total_images"] = dataset_info.get("total_images", 0)
                statistics["annotated_images"] = dataset_info.get("annotated_images", 0)
                
                if statistics["total_images"] > 0:
                    statistics["annotation_progress"] = (
                        statistics["annotated_images"] / statistics["total_images"] * 100
                    )
            else:
                # 从task_info获取
                statistics["total_images"] = task_info.get("total_images", 0)
                statistics["annotated_images"] = task_info.get("annotated_images", 0)
                
                if statistics["total_images"] > 0:
                    statistics["annotation_progress"] = (
                        statistics["annotated_images"] / statistics["total_images"] * 100
                    )
            
            # 训练指标（仅已完成或失败的任务）
            status = task_info.get("status", "")
            if status in ["completed", "failed"]:
                statistics["training_metrics"] = {
                    "mAP": task_info.get("mAP", 0),
                    "loss": task_info.get("loss", 0),
                    "model_path": task_info.get("model_path", "")
                }
            
            return statistics
            
        except Exception as e:
            logger.error(f"获取训练统计信息失败: {str(e)}", exc_info=True)
            return {}
    
    def get_annotation_statistics(self, task_dir: str) -> Dict[str, Any]:
        """获取标注统计信息
        
        Args:
            task_dir: 任务目录
            
        Returns:
            标注统计信息字典
        """
        image_dir = os.path.join(task_dir, "dataset/images/train")
        label_dir = os.path.join(task_dir, "dataset/labels/train")
        
        statistics = {
            "total_images": 0,
            "annotated_images": 0,
            "total_annotations": 0,
            "annotations_per_image": [],
            "class_distribution": {},
            "avg_annotations_per_image": 0
        }
        
        if not os.path.exists(image_dir):
            return statistics
        
        # 获取图片文件
        valid_extensions = ('.jpg', '.jpeg', '.png', '.bmp')
        image_files = [f for f in os.listdir(image_dir) 
                      if f.lower().endswith(valid_extensions)]
        
        statistics["total_images"] = len(image_files)
        
        if not os.path.exists(label_dir):
            return statistics
        
        # 统计标注信息
        for image_filename in image_files:
            label_filename = os.path.splitext(image_filename)[0] + ".txt"
            label_path = os.path.join(label_dir, label_filename)
            
            if os.path.exists(label_path) and os.path.getsize(label_path) > 0:
                statistics["annotated_images"] += 1
                
                try:
                    with open(label_path, 'r', encoding='utf-8') as f:
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
        
        # 计算平均每张图片的标注数
        if statistics["annotated_images"] > 0:
            statistics["avg_annotations_per_image"] = (
                statistics["total_annotations"] / statistics["annotated_images"]
            )
        
        return statistics
    
    def get_batch_statistics(self, tasks: List[Dict[str, Any]]) -> Dict[str, Any]:
        """获取批量任务的统计信息
        
        Args:
            tasks: 任务列表
            
        Returns:
            批量统计信息字典
        """
        total_tasks = len(tasks)
        status_counts = {}
        total_images = 0
        total_annotated = 0
        
        for task in tasks:
            # 统计状态
            status = task.get("status", "unknown")
            status_counts[status] = status_counts.get(status, 0) + 1
            
            # 统计图片
            total_images += task.get("total_images", 0)
            total_annotated += task.get("annotated_images", 0)
        
        return {
            "total_tasks": total_tasks,
            "status_distribution": status_counts,
            "total_images": total_images,
            "total_annotated_images": total_annotated,
            "overall_annotation_progress": (
                (total_annotated / total_images * 100) if total_images > 0 else 0
            ),
            "pending_tasks": status_counts.get("pending", 0),
            "training_tasks": status_counts.get("training", 0),
            "completed_tasks": status_counts.get("completed", 0),
            "failed_tasks": status_counts.get("failed", 0)
        }
    
    def get_progress_percentage(self, annotated: int, total: int) -> float:
        """计算标注进度百分比
        
        Args:
            annotated: 已标注数量
            total: 总数
            
        Returns:
            进度百分比
        """
        if total <= 0:
            return 0.0
        return round(annotated / total * 100, 1)
    
    def format_size(self, size_bytes: int) -> str:
        """格式化文件大小
        
        Args:
            size_bytes: 字节数
            
        Returns:
            格式化后的大小字符串
        """
        for unit in ['B', 'KB', 'MB', 'GB']:
            if size_bytes < 1024.0:
                return f"{size_bytes:.2f} {unit}"
            size_bytes /= 1024.0
        return f"{size_bytes:.2f} TB"


class ProgressCalculator:
    """进度计算器
    
    专门负责计算各种进度指标。
    """
    
    @staticmethod
    def calculate_annotation_progress(annotated: int, total: int) -> float:
        """计算标注进度
        
        Args:
            annotated: 已标注数量
            total: 总数
            
        Returns:
            进度百分比 (0-100)
        """
        if total <= 0:
            return 0.0
        return round(annotated / total * 100, 2)
    
    @staticmethod
    def calculate_training_progress(current_epoch: int, total_epochs: int) -> float:
        """计算训练进度
        
        Args:
            current_epoch: 当前轮次
            total_epochs: 总轮次
            
        Returns:
            进度百分比 (0-100)
        """
        if total_epochs <= 0:
            return 0.0
        return round(current_epoch / total_epochs * 100, 2)
    
    @staticmethod
    def estimate_remaining_time(elapsed_seconds: float, progress: float) -> str:
        """估算剩余时间
        
        Args:
            elapsed_seconds: 已用时间（秒）
            progress: 当前进度 (0-100)
            
        Returns:
            格式化的时间字符串
        """
        if progress <= 0:
            return "未知"
        
        remaining_ratio = (100 - progress) / progress
        remaining_seconds = elapsed_seconds * remaining_ratio
        
        if remaining_seconds < 60:
            return f"{int(remaining_seconds)}秒"
        elif remaining_seconds < 3600:
            return f"{int(remaining_seconds / 60)}分钟"
        elif remaining_seconds < 86400:
            return f"{int(remaining_seconds / 3600)}小时{int((remaining_seconds % 3600) / 60)}分钟"
        else:
            days = int(remaining_seconds / 86400)
            hours = int((remaining_seconds % 86400) / 3600)
            return f"{days}天{hours}小时"


# 全局统计实例
training_statistics = TrainingStatistics()
progress_calculator = ProgressCalculator()
