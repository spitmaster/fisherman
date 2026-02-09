#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
训练任务创建器

负责训练任务的创建和初始化。
"""

import os
import shutil
import yaml
import logging
from typing import Optional

from global_support.database import db_manager, TrainingTask

from ..core.base_manager import BaseManager
from ..utils.file_ops import create_task_directory, copy_dataset, create_default_dataset_structure, create_data_yaml

# 日志配置
logger = logging.getLogger(__name__)


class TaskCreator(BaseManager):
    """训练任务创建器"""
    
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
            训练任务ID，创建失败时返回None
        """
        try:
            # 创建任务文件夹结构
            task_dir = create_task_directory(task_name)
            
            # 创建数据集目录
            if dataset_path:
                # 如果提供了数据集路径，复制到任务目录
                copy_dataset(dataset_path, task_dir)
            else:
                # 否则创建空的数据集结构
                create_default_dataset_structure(task_dir)
            
            # 创建data.yaml配置文件
            create_data_yaml(task_dir, task_name)
            
            # 在数据库中创建任务记录
            session = db_manager.get_session()
            try:
                training_task = TrainingTask(
                    task_name=task_name,
                    task_description=task_description,
                    dataset_path=os.path.join(task_dir, "dataset"),
                    epochs=epochs,
                    batch_size=batch_size
                )
                
                session.add(training_task)
                session.commit()
                
                self.log_operation("info", f"训练任务创建成功: {task_name} (ID: {training_task.id})")
                
                return training_task.id
                
            except Exception as e:
                self.log_operation("error", f"创建训练任务数据库记录失败: {str(e)}", exc_info=True)
                session.rollback()
                return None
                
            finally:
                session.close()
                
        except Exception as e:
            self.log_operation("error", f"创建训练任务失败: {str(e)}", exc_info=True)
            return None