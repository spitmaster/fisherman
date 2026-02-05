#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
训练任务管理器

实现ITrainingManager接口，提供训练任务的统一管理。
"""

import os
import logging
from typing import List, Dict, Any, Optional

from fisherman.global_support.database import db_manager, TrainingTask

from ..core.interfaces import ITrainingManager
from ..core.base_manager import BaseManager
from .creator import TaskCreator
from .status_tracker import TaskStatusTracker
from .dataset_manager import DatasetManager
from ..training.executor import TrainingExecutor

# 日志配置
logger = logging.getLogger(__name__)


class TrainingTaskManager(ITrainingManager, BaseManager):
    """训练任务管理器"""
    
    def __init__(self):
        """初始化训练任务管理器"""
        super().__init__()
        self.task_creator = TaskCreator()
        self.status_tracker = TaskStatusTracker()
        self.dataset_manager = DatasetManager()
        self.training_executor = TrainingExecutor()
        self.training_tasks = {}
        
        # 加载所有训练任务
        self._load_all_training_tasks()
        
    def _load_all_training_tasks(self):
        """加载所有训练任务"""
        session = db_manager.get_session()
        try:
            tasks = session.query(TrainingTask).all()
            for task in tasks:
                task_info = {
                    "task_dir": os.path.join("training_data", task.task_name),
                    "status": task.status,
                    "annotated_images": 0,
                    "total_images": 0
                }
                
                # 获取数据集信息
                if task.dataset_path and os.path.exists(task.dataset_path):
                    image_dir = os.path.join(os.path.dirname(task.dataset_path), "images", "train")
                    label_dir = os.path.join(os.path.dirname(task.dataset_path), "labels", "train")
                    
                    if os.path.exists(image_dir):
                        image_files = [f for f in os.listdir(image_dir) 
                                     if f.lower().endswith(('.jpg', '.jpeg', '.png', '.bmp'))]
                        task_info["total_images"] = len(image_files)
                        
                        if os.path.exists(label_dir):
                            annotated_count = 0
                            for img_file in image_files:
                                txt_file = os.path.splitext(img_file)[0] + ".txt"
                                if os.path.exists(os.path.join(label_dir, txt_file)):
                                    annotated_count += 1
                            task_info["annotated_images"] = annotated_count
                
                self.training_tasks[task.id] = task_info
                
            self.log_operation("info", f"加载训练任务成功: 共 {len(tasks)} 个任务")
            
        except Exception as e:
            self.log_operation("error", f"加载训练任务出错: {str(e)}", exc_info=True)
            
        finally:
            session.close()
            
    # ITrainingManager接口实现
    
    def create_training_task(self, task_name: str, task_description: str, 
                           dataset_path: Optional[str] = None, 
                           epochs: int = 50, batch_size: int = 8) -> Optional[int]:
        """创建新的训练任务
        
        Args:
            task_name: 任务名称
            task_description: 任务描述
            dataset_path: 数据集路径
            epochs: 训练轮数
            batch_size: 批次大小
            
        Returns:
            训练任务ID
        """
        return self.task_creator.create_training_task(
            task_name, task_description, dataset_path, epochs, batch_size
        )
    
    def get_all_training_tasks(self) -> List[Dict[str, Any]]:
        """获取所有训练任务
        
        Returns:
            训练任务列表
        """
        session = db_manager.get_session()
        try:
            tasks = session.query(TrainingTask).all()
            
            task_list = []
            for task in tasks:
                task_info = self.training_tasks.get(task.id)
                if not task_info:
                    task_info = {
                        "task_dir": os.path.join("training_data", task.task_name),
                        "status": task.status,
                        "annotated_images": 0,
                        "total_images": 0
                    }
                
                task_list.append({
                    "id": task.id,
                    "task_name": task.task_name,
                    "task_description": task.task_description,
                    "status": task.status,
                    "created_at": task.created_at,
                    "updated_at": task.updated_at,
                    "dataset_path": task.dataset_path,
                    "model_path": task.model_path,
                    "epochs": task.epochs,
                    "batch_size": task.batch_size,
                    "annotated_images": task_info["annotated_images"],
                    "total_images": task_info["total_images"]
                })
                
            return task_list
            
        except Exception as e:
            self.log_operation("error", f"获取训练任务列表出错: {str(e)}", exc_info=True)
            return []
            
        finally:
            session.close()
    
    def get_training_task_by_id(self, task_id: int) -> Optional[Dict[str, Any]]:
        """根据ID获取训练任务
        
        Args:
            task_id: 任务ID
            
        Returns:
            训练任务信息字典
        """
        session = db_manager.get_session()
        try:
            task = session.query(TrainingTask).filter_by(id=task_id).first()
            if not task:
                return None
                
            task_info = self.training_tasks.get(task.id)
            if not task_info:
                task_info = {
                    "task_dir": os.path.join("training_data", task.task_name),
                    "status": task.status,
                    "annotated_images": 0,
                    "total_images": 0
                }
            
            return {
                "id": task.id,
                "task_name": task.task_name,
                "task_description": task.task_description,
                "status": task.status,
                "created_at": task.created_at,
                "updated_at": task.updated_at,
                "dataset_path": task.dataset_path,
                "model_path": task.model_path,
                "epochs": task.epochs,
                "batch_size": task.batch_size,
                "annotated_images": task_info["annotated_images"],
                "total_images": task_info["total_images"],
                "task_dir": task_info["task_dir"]
            }
            
        except Exception as e:
            self.log_operation("error", f"获取训练任务出错: {task_id} - {str(e)}", exc_info=True)
            return None
            
        finally:
            session.close()
    
    def update_training_task(self, task_id: int, **kwargs) -> bool:
        """更新训练任务信息
        
        Args:
            task_id: 任务ID
            **kwargs: 要更新的字段
            
        Returns:
            更新是否成功
        """
        session = db_manager.get_session()
        try:
            task = session.query(TrainingTask).filter_by(id=task_id).first()
            if not task:
                self.log_operation("error", f"任务不存在: {task_id}")
                return False
                
            # 更新允许的字段
            allowed_fields = ["task_name", "task_description", "epochs", "batch_size", "status"]
            for field, value in kwargs.items():
                if field in allowed_fields and hasattr(task, field):
                    setattr(task, field, value)
                    
            session.commit()
            self.log_operation("info", f"训练任务更新成功: {task_id}")
            return True
            
        except Exception as e:
            self.log_operation("error", f"更新训练任务失败: {task_id} - {str(e)}", exc_info=True)
            session.rollback()
            return False
            
        finally:
            session.close()
    
    def delete_training_task(self, task_id: int) -> bool:
        """删除训练任务
        
        Args:
            task_id: 任务ID
            
        Returns:
            删除是否成功
        """
        session = db_manager.get_session()
        try:
            task = session.query(TrainingTask).filter_by(id=task_id).first()
            if not task:
                self.log_operation("error", f"任务不存在: {task_id}")
                return False
                
            # 删除任务目录
            task_dir = os.path.join("training_data", task.task_name)
            if os.path.exists(task_dir):
                import shutil
                try:
                    shutil.rmtree(task_dir)
                    self.log_operation("info", f"删除任务目录: {task_dir}")
                except Exception as e:
                    self.log_operation("error", f"删除任务目录失败: {task_dir} - {str(e)}")
            
            # 从数据库中删除任务
            session.delete(task)
            session.commit()
            
            # 从内存中移除任务信息
            if task_id in self.training_tasks:
                del self.training_tasks[task_id]
                
            self.log_operation("info", f"训练任务删除成功: {task_id}")
            return True
            
        except Exception as e:
            self.log_operation("error", f"删除训练任务失败: {task_id} - {str(e)}", exc_info=True)
            session.rollback()
            return False
            
        finally:
            session.close()
    
    def start_training(self, task_id: int) -> bool:
        """开始训练任务
        
        Args:
            task_id: 任务ID
            
        Returns:
            启动是否成功
        """
        # 获取任务信息
        task_info = self.get_training_task_by_id(task_id)
        if not task_info:
            self.log_operation("error", f"任务不存在: {task_id}")
            return False
            
        # 更新任务状态为训练中
        if not self.status_tracker.update_task_status(task_id, "training"):
            self.log_operation("error", f"更新任务状态失败: {task_id}")
            return False
            
        # 准备训练参数
        dataset_config = {
            "data": os.path.join(task_info["task_dir"], "dataset", "data.yaml")
        }
        
        training_params = {
            "epochs": task_info["epochs"],
            "batch_size": task_info["batch_size"]
        }
        
        # 执行训练
        result = self.training_executor.train(task_id, dataset_config, training_params)
        
        return result.get("success", False)
    
    # 委托方法到各个组件
    
    def import_images(self, task_id: int, image_paths: List[str]) -> int:
        """导入图片到训练任务
        
        Args:
            task_id: 任务ID
            image_paths: 图片路径列表
            
        Returns:
            成功导入的图片数量
        """
        return self.dataset_manager.import_images(task_id, image_paths)
    
    def get_dataset_info(self, task_id: int) -> Optional[Dict[str, Any]]:
        """获取数据集信息
        
        Args:
            task_id: 任务ID
            
        Returns:
            数据集信息字典
        """
        return self.dataset_manager.get_dataset_info(task_id)
    
    def get_image_list(self, task_id: int) -> List[str]:
        """获取任务的图片列表
        
        Args:
            task_id: 任务ID
            
        Returns:
            图片文件名列表
        """
        return self.dataset_manager.get_image_list(task_id)
    
    def get_unannotated_images(self, task_id: int) -> List[str]:
        """获取未标注的图片列表
        
        Args:
            task_id: 任务ID
            
        Returns:
            未标注图片文件名列表
        """
        return self.dataset_manager.get_unannotated_images(task_id)
    
    def update_task_status(self, task_id: int, status: str) -> bool:
        """更新任务状态
        
        Args:
            task_id: 任务ID
            status: 新状态
            
        Returns:
            更新是否成功
        """
        return self.status_tracker.update_task_status(task_id, status)
    
    def get_task_status(self, task_id: int) -> Optional[str]:
        """获取任务状态
        
        Args:
            task_id: 任务ID
            
        Returns:
            任务状态字符串
        """
        return self.status_tracker.get_task_status(task_id)
    
    def get_task_progress(self, task_id: int) -> Optional[Dict[str, Any]]:
        """获取任务进度信息
        
        Args:
            task_id: 任务ID
            
        Returns:
            进度信息字典
        """
        return self.status_tracker.get_task_progress(task_id)
    
    def get_training_task_status(self, task_id: int) -> Optional[Dict[str, Any]]:
        """获取训练任务状态（向后兼容方法）
        
        Args:
            task_id: 任务ID
            
        Returns:
            任务状态信息字典
        """
        # 这个方法是为了向后兼容，返回包含状态和进度的字典
        status = self.get_task_status(task_id)
        progress = self.get_task_progress(task_id)
        
        if status is None:
            return None
            
        result = {
            "status": status,
            "progress": progress or {}
        }
        
        return result
    
    def start_annotation(self, task_id: int) -> Dict[str, Any]:
        """开始标注任务（向后兼容方法）
        
        Args:
            task_id: 任务ID
            
        Returns:
            标注任务结果字典
        """
        try:
            # 获取任务信息
            task_info = self.get_training_task_by_id(task_id)
            if not task_info:
                return {"success": False, "error": f"任务不存在: {task_id}"}
            
            # 获取未标注的图片
            unannotated_images = self.get_unannotated_images(task_id)
            
            if not unannotated_images:
                return {"success": False, "error": "没有需要标注的图片"}
            
            # 更新任务状态为标注中
            if not self.update_task_status(task_id, "annotating"):
                return {"success": False, "error": "更新任务状态失败"}
            
            # 创建标注工具
            # 注意：这里需要从annotation_manager创建工具，但为了简化先返回成功
            # 在实际实现中，这里应该启动标注界面
            result = {
                "success": True,
                "task_id": task_id,
                "message": f"标注任务已准备，共有 {len(unannotated_images)} 张图片需要标注",
                "unannotated_images": unannotated_images,
                "task_info": task_info
            }
            
            return result
            
        except Exception as e:
            self.log_operation("error", f"开始标注任务失败: {str(e)}", exc_info=True)
            return {"success": False, "error": str(e)}