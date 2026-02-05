#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
任务状态跟踪器

实现ITaskStatusTracker接口，负责训练任务的状态跟踪和管理。
"""

import os
import logging
from typing import Dict, Any, Optional

from fisherman.global_support.database import db_manager, TrainingTask, TrainingLog
from fisherman.global_support.task_scheduler import task_scheduler, TrainingTask as SchedulerTrainingTask

from ..core.interfaces import ITaskStatusTracker
from ..core.base_manager import BaseManager

# 日志配置
logger = logging.getLogger(__name__)


class TaskStatusTracker(ITaskStatusTracker, BaseManager):
    """任务状态跟踪器"""
    
    def __init__(self):
        """初始化状态跟踪器"""
        super().__init__()
        
    def update_task_status(self, task_id: int, status: str) -> bool:
        """更新任务状态
        
        Args:
            task_id: 任务ID
            status: 新状态
            
        Returns:
            更新是否成功
        """
        session = db_manager.get_session()
        try:
            task = session.query(TrainingTask).filter_by(id=task_id).first()
            if not task:
                self.log_operation("error", f"任务不存在: {task_id}")
                return False
                
            task.status = status
            session.commit()
            
            # 记录状态变更日志
            training_log = TrainingLog(
                task_id=task_id,
                log_type="status_change",
                message=f"任务状态更新为: {status}"
            )
            session.add(training_log)
            session.commit()
            
            self.log_operation("info", f"任务状态更新成功: {task_id} -> {status}")
            return True
            
        except Exception as e:
            self.log_operation("error", f"更新任务状态失败: {str(e)}", exc_info=True)
            session.rollback()
            return False
            
        finally:
            session.close()
            
    def get_task_status(self, task_id: int) -> Optional[str]:
        """获取任务状态
        
        Args:
            task_id: 任务ID
            
        Returns:
            任务状态字符串，任务不存在时返回None
        """
        session = db_manager.get_session()
        try:
            task = session.query(TrainingTask).filter_by(id=task_id).first()
            if task:
                return task.status
            else:
                return None
                
        except Exception as e:
            self.log_operation("error", f"获取任务状态失败: {str(e)}", exc_info=True)
            return None
            
        finally:
            session.close()
            
    def get_task_progress(self, task_id: int) -> Optional[Dict[str, Any]]:
        """获取任务进度信息
        
        Args:
            task_id: 任务ID
            
        Returns:
            进度信息字典，包含以下字段：
            - status: 当前状态
            - progress_percentage: 进度百分比
            - current_epoch: 当前训练轮数
            - total_epochs: 总训练轮数
            - message: 进度消息
        """
        session = db_manager.get_session()
        try:
            task = session.query(TrainingTask).filter_by(id=task_id).first()
            if not task:
                return None
                
            progress_info = {
                "status": task.status,
                "progress_percentage": 0,
                "current_epoch": 0,
                "total_epochs": task.epochs,
                "message": ""
            }
            
            # 根据状态设置进度信息
            if task.status == "annotating":
                # 获取标注进度
                task_dir = os.path.join("training_data", task.task_name)
                image_dir = os.path.join(task_dir, "dataset/images/train")
                label_dir = os.path.join(task_dir, "dataset/labels/train")
                
                if os.path.exists(image_dir):
                    image_files = [f for f in os.listdir(image_dir) 
                                 if f.lower().endswith(('.jpg', '.jpeg', '.png', '.bmp'))]
                    total_images = len(image_files)
                    
                    annotated_count = 0
                    if os.path.exists(label_dir):
                        for img_file in image_files:
                            txt_file = os.path.splitext(img_file)[0] + ".txt"
                            if os.path.exists(os.path.join(label_dir, txt_file)):
                                annotated_count += 1
                    
                    if total_images > 0:
                        progress_percentage = (annotated_count / total_images) * 100
                        progress_info["progress_percentage"] = progress_percentage
                        progress_info["message"] = f"标注进度: {annotated_count}/{total_images}"
                        
            elif task.status == "training":
                # 从调度器获取训练进度
                scheduler_task = task_scheduler.get_task(f"training_{task_id}")
                if scheduler_task:
                    progress_info.update(scheduler_task.progress_info)
                    
            elif task.status == "completed":
                progress_info["progress_percentage"] = 100
                progress_info["message"] = "训练完成"
                
            return progress_info
            
        except Exception as e:
            self.log_operation("error", f"获取任务进度失败: {str(e)}", exc_info=True)
            return None
            
        finally:
            session.close()