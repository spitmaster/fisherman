#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
训练模块 - 训练备份恢复模块

负责训练任务和标注数据的备份与恢复功能。
采用单一职责原则，只负责备份恢复相关功能。
"""

import os
import shutil
import logging
from datetime import datetime
from typing import List, Dict, Any, Optional
from pathlib import Path

logger = logging.getLogger(__name__)


class TrainingBackupManager:
    """训练备份管理器
    
    负责训练任务的备份和恢复操作。
    """
    
    def __init__(self, backup_root: str = None):
        """初始化备份管理器
        
        Args:
            backup_root: 备份根目录，默认为 training_data/{task_name}/backup
        """
        self.backup_root = backup_root
    
    def _get_backup_dir(self, task_dir: str) -> str:
        """获取备份目录
        
        Args:
            task_dir: 任务目录
            
        Returns:
            备份目录路径
        """
        if self.backup_root:
            return self.backup_root
        return os.path.join(task_dir, "backup")
    
    def create_task_backup(self, task_id: int, task_info: Dict[str, Any]) -> str:
        """为训练任务创建备份
        
        Args:
            task_id: 任务ID
            task_info: 任务信息
            
        Returns:
            备份路径，如果失败则返回空字符串
        """
        try:
            task_name = task_info.get("task_name", "")
            if not task_name:
                logger.error("任务名称为空，无法创建备份")
                return ""
            
            task_dir = os.path.join("training_data", task_name)
            backup_dir = self._get_backup_dir(task_dir)
            os.makedirs(backup_dir, exist_ok=True)
            
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            backup_name = f"task_backup_{timestamp}"
            backup_path = os.path.join(backup_dir, backup_name)
            
            # 备份标签目录
            label_dir = os.path.join(task_dir, "dataset/labels/train")
            if os.path.exists(label_dir):
                shutil.copytree(label_dir, backup_path)
                logger.info(f"训练任务备份创建成功: {backup_path}")
                return backup_path
            else:
                logger.warning("标签目录不存在，无法创建备份")
                return ""
                
        except Exception as e:
            logger.error(f"创建备份失败: {str(e)}", exc_info=True)
            return ""
    
    def restore_task_backup(self, task_id: int, task_info: Dict[str, Any], 
                          backup_path: str) -> bool:
        """从备份恢复训练任务
        
        Args:
            task_id: 任务ID
            task_info: 任务信息
            backup_path: 备份路径
            
        Returns:
            恢复是否成功
        """
        try:
            if not os.path.exists(backup_path):
                logger.error(f"备份文件不存在: {backup_path}")
                return False
            
            task_name = task_info.get("task_name", "")
            if not task_name:
                logger.error("任务名称为空，无法恢复备份")
                return False
            
            task_dir = os.path.join("training_data", task_name)
            label_dir = os.path.join(task_dir, "dataset/labels/train")
            
            # 创建当前数据备份
            current_backup = self.create_task_backup(task_id, task_info)
            if current_backup:
                logger.info(f"当前数据已备份到: {current_backup}")
            
            # 恢复备份
            if os.path.exists(label_dir):
                shutil.rmtree(label_dir)
            
            shutil.copytree(backup_path, label_dir)
            logger.info(f"训练任务恢复成功: {backup_path}")
            
            return True
            
        except Exception as e:
            logger.error(f"恢复备份失败: {str(e)}", exc_info=True)
            return False
    
    def list_backups(self, task_dir: str) -> List[Dict[str, Any]]:
        """列出任务的备份列表
        
        Args:
            task_dir: 任务目录
            
        Returns:
            备份列表
        """
        backup_dir = self._get_backup_dir(task_dir)
        
        if not os.path.exists(backup_dir):
            return []
        
        backups = []
        for item in os.listdir(backup_dir):
            item_path = os.path.join(backup_dir, item)
            
            if os.path.isdir(item_path):
                # 获取备份信息
                stat = os.stat(item_path)
                file_count = len(os.listdir(item_path))
                
                backups.append({
                    "name": item,
                    "path": item_path,
                    "created_at": datetime.fromtimestamp(stat.st_ctime).strftime("%Y-%m-%d %H:%M:%S"),
                    "file_count": file_count,
                    "size": self._calculate_dir_size(item_path)
                })
        
        # 按创建时间倒序排列
        backups.sort(key=lambda x: x["created_at"], reverse=True)
        return backups
    
    def delete_backup(self, backup_path: str) -> bool:
        """删除备份
        
        Args:
            backup_path: 备份路径
            
        Returns:
            删除是否成功
        """
        try:
            if not os.path.exists(backup_path):
                logger.warning(f"备份不存在: {backup_path}")
                return False
            
            shutil.rmtree(backup_path)
            logger.info(f"备份已删除: {backup_path}")
            return True
            
        except Exception as e:
            logger.error(f"删除备份失败: {str(e)}", exc_info=True)
            return False
    
    def _calculate_dir_size(self, dir_path: str) -> int:
        """计算目录大小
        
        Args:
            dir_path: 目录路径
            
        Returns:
            目录大小（字节）
        """
        total_size = 0
        for dirpath, dirnames, filenames in os.walk(dir_path):
            for filename in filenames:
                filepath = os.path.join(dirpath, filename)
                if os.path.exists(filepath):
                    total_size += os.path.getsize(filepath)
        return total_size


class AnnotationBackupManager:
    """标注备份管理器
    
    负责标注数据的备份和恢复操作。
    """
    
    def __init__(self):
        """初始化标注备份管理器"""
        pass
    
    def create_annotation_backup(self, task_info: Dict[str, Any]) -> str:
        """创建标注数据备份
        
        Args:
            task_info: 任务信息
            
        Returns:
            备份文件路径
        """
        try:
            task_dir = task_info.get("task_dir", "")
            if not task_dir:
                logger.error("任务目录为空，无法创建备份")
                return ""
            
            backup_dir = os.path.join(task_dir, "backup")
            os.makedirs(backup_dir, exist_ok=True)
            
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            backup_name = f"annotations_backup_{timestamp}"
            backup_path = os.path.join(backup_dir, backup_name)
            
            # 备份标签目录
            label_dir = os.path.join(task_dir, "dataset/labels/train")
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
    
    def restore_annotation_backup(self, task_info: Dict[str, Any], backup_path: str) -> bool:
        """从备份恢复标注数据
        
        Args:
            task_info: 任务信息
            backup_path: 备份路径
            
        Returns:
            恢复是否成功
        """
        try:
            if not os.path.exists(backup_path):
                logger.error(f"备份文件不存在: {backup_path}")
                return False
            
            task_dir = task_info.get("task_dir", "")
            if not task_dir:
                logger.error("任务目录为空，无法恢复备份")
                return False
            
            label_dir = os.path.join(task_dir, "dataset/labels/train")
            
            # 备份当前标签目录
            current_backup = self.create_annotation_backup(task_info)
            if current_backup:
                logger.info(f"当前数据已备份到: {current_backup}")
            
            # 恢复备份
            if os.path.exists(label_dir):
                shutil.rmtree(label_dir)
            
            shutil.copytree(backup_path, label_dir)
            logger.info(f"标注数据恢复成功: {backup_path}")
            
            return True
            
        except Exception as e:
            logger.error(f"恢复备份失败: {str(e)}", exc_info=True)
            return False
    
    def get_backup_info(self, backup_path: str) -> Dict[str, Any]:
        """获取备份信息
        
        Args:
            backup_path: 备份路径
            
        Returns:
            备份信息字典
        """
        if not os.path.exists(backup_path):
            return {}
        
        stat = os.stat(backup_path)
        
        # 统计标签文件数量
        label_count = 0
        total_annotations = 0
        
        for root, dirs, files in os.walk(backup_path):
            for f in files:
                if f.endswith('.txt'):
                    label_count += 1
                    # 尝试统计标注数量
                    try:
                        with open(os.path.join(root, f), 'r') as fp:
                            lines = fp.readlines()
                            total_annotations += len([l for l in lines if l.strip()])
                    except:
                        pass
        
        return {
            "path": backup_path,
            "name": os.path.basename(backup_path),
            "created_at": datetime.fromtimestamp(stat.st_ctime).strftime("%Y-%m-%d %H:%M:%S"),
            "label_count": label_count,
            "total_annotations": total_annotations,
            "size": stat.st_size
        }


# 全局备份管理器实例
training_backup_manager = TrainingBackupManager()
annotation_backup_manager = AnnotationBackupManager()
