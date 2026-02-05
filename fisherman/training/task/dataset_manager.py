#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
数据集管理器

实现IDatasetManager接口，负责数据集的导入、管理和查询。
"""

import os
import shutil
import logging
from typing import List, Dict, Any, Optional

from fisherman.global_support.database import db_manager, TrainingTask

from ..core.interfaces import IDatasetManager
from ..core.base_manager import BaseManager

# 日志配置
logger = logging.getLogger(__name__)


class DatasetManager(IDatasetManager, BaseManager):
    """数据集管理器"""
    
    def __init__(self):
        """初始化数据集管理器"""
        super().__init__()
        
    def import_images(self, task_id: int, image_paths: List[str]) -> int:
        """导入图片到训练任务
        
        Args:
            task_id: 任务ID
            image_paths: 图片路径列表
            
        Returns:
            成功导入的图片数量
        """
        session = db_manager.get_session()
        try:
            task = session.query(TrainingTask).filter_by(id=task_id).first()
            if not task:
                self.log_operation("error", f"任务不存在: {task_id}")
                return 0
                
            task_dir = os.path.join("training_data", task.task_name)
            target_dir = os.path.join(task_dir, "dataset/images/train")
            
            # 确保目标目录存在
            os.makedirs(target_dir, exist_ok=True)
            
            imported_count = 0
            for image_path in image_paths:
                if os.path.exists(image_path):
                    # 获取文件名
                    filename = os.path.basename(image_path)
                    target_path = os.path.join(target_dir, filename)
                    
                    # 复制文件
                    shutil.copy2(image_path, target_path)
                    imported_count += 1
                    
                    self.log_operation("debug", f"图片导入成功: {filename}")
                else:
                    self.log_operation("error", f"图片文件不存在: {image_path}")
                    
            # 更新任务状态
            if imported_count > 0:
                if task.status == "pending":
                    task.status = "ready"
                    session.commit()
                    
                self.log_operation("info", f"图片导入完成: 成功导入 {imported_count} 张图片")
                
            return imported_count
            
        except Exception as e:
            self.log_operation("error", f"导入图片失败: {str(e)}", exc_info=True)
            return 0
            
        finally:
            session.close()
            
    def get_dataset_info(self, task_id: int) -> Optional[Dict[str, Any]]:
        """获取数据集信息
        
        Args:
            task_id: 任务ID
            
        Returns:
            数据集信息字典，包含以下字段：
            - total_images: 总图片数
            - annotated_images: 已标注图片数
            - annotation_progress: 标注进度百分比
            - dataset_path: 数据集路径
        """
        session = db_manager.get_session()
        try:
            task = session.query(TrainingTask).filter_by(id=task_id).first()
            if not task:
                return None
                
            dataset_info = {
                "total_images": 0,
                "annotated_images": 0,
                "annotation_progress": 0,
                "dataset_path": task.dataset_path
            }
            
            # 获取图片目录
            image_dir = os.path.join(os.path.dirname(task.dataset_path), "images", "train")
            label_dir = os.path.join(os.path.dirname(task.dataset_path), "labels", "train")
            
            if os.path.exists(image_dir):
                image_files = [f for f in os.listdir(image_dir) 
                             if f.lower().endswith(('.jpg', '.jpeg', '.png', '.bmp'))]
                dataset_info["total_images"] = len(image_files)
                
                # 获取标注信息
                if os.path.exists(label_dir):
                    annotated_count = 0
                    for img_file in image_files:
                        txt_file = os.path.splitext(img_file)[0] + ".txt"
                        if os.path.exists(os.path.join(label_dir, txt_file)):
                            annotated_count += 1
                    
                    dataset_info["annotated_images"] = annotated_count
                    
                    if len(image_files) > 0:
                        dataset_info["annotation_progress"] = (annotated_count / len(image_files)) * 100
            
            return dataset_info
            
        except Exception as e:
            self.log_operation("error", f"获取数据集信息失败: {str(e)}", exc_info=True)
            return None
            
        finally:
            session.close()
            
    def get_image_list(self, task_id: int) -> List[str]:
        """获取任务的图片列表
        
        Args:
            task_id: 任务ID
            
        Returns:
            图片文件名列表
        """
        session = db_manager.get_session()
        try:
            task = session.query(TrainingTask).filter_by(id=task_id).first()
            if not task:
                return []
                
            image_dir = os.path.join(os.path.dirname(task.dataset_path), "images", "train")
            
            if not os.path.exists(image_dir):
                return []
                
            image_files = [f for f in os.listdir(image_dir) 
                         if f.lower().endswith(('.jpg', '.jpeg', '.png', '.bmp'))]
            
            return sorted(image_files)
            
        except Exception as e:
            self.log_operation("error", f"获取图片列表失败: {str(e)}", exc_info=True)
            return []
            
        finally:
            session.close()
            
    def get_unannotated_images(self, task_id: int) -> List[str]:
        """获取未标注的图片列表
        
        Args:
            task_id: 任务ID
            
        Returns:
            未标注图片文件名列表
        """
        session = db_manager.get_session()
        try:
            task = session.query(TrainingTask).filter_by(id=task_id).first()
            if not task:
                return []
                
            image_dir = os.path.join(os.path.dirname(task.dataset_path), "images", "train")
            label_dir = os.path.join(os.path.dirname(task.dataset_path), "labels", "train")
            
            if not os.path.exists(image_dir):
                return []
                
            image_files = [f for f in os.listdir(image_dir) 
                         if f.lower().endswith(('.jpg', '.jpeg', '.png', '.bmp'))]
            
            unannotated_images = []
            for img_file in image_files:
                txt_file = os.path.splitext(img_file)[0] + ".txt"
                label_path = os.path.join(label_dir, txt_file)
                
                if not os.path.exists(label_path) or os.path.getsize(label_path) == 0:
                    unannotated_images.append(img_file)
            
            return sorted(unannotated_images)
            
        except Exception as e:
            self.log_operation("error", f"获取未标注图片列表失败: {str(e)}", exc_info=True)
            return []
            
        finally:
            session.close()