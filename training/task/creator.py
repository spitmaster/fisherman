#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
训练任务创建器

负责训练任务的创建和初始化。
支持全面的参数校验和详细的错误提示。
"""

import os
import shutil
import yaml
import logging
import re
from typing import Optional, Dict, Any

from global_support.database import db_manager, TrainingTask

from ..core.base_manager import BaseManager
from ..core.interfaces import IErrorHandler
from ..utils.file_ops import create_task_directory, copy_dataset, create_default_dataset_structure, create_data_yaml

# 日志配置
logger = logging.getLogger(__name__)


class TaskCreator(BaseManager, IErrorHandler):
    """训练任务创建器
    
    提供全面的参数校验和详细的错误提示功能。
    """
    
    def __init__(self):
        """初始化任务创建器"""
        super().__init__("task_creator")
        
        # 参数验证规则
        self.validation_rules = {
            "task_name": {
                "required": True,
                "min_length": 1,
                "max_length": 100,
                "pattern": r"^[a-zA-Z0-9_\-\s]+$",
                "error_messages": {
                    "required": "任务名称不能为空",
                    "min_length": "任务名称长度不能少于1个字符",
                    "max_length": "任务名称长度不能超过100个字符",
                    "pattern": "任务名称只能包含字母、数字、下划线、连字符和空格"
                }
            },
            "task_description": {
                "required": False,
                "max_length": 500,
                "error_messages": {
                    "max_length": "任务描述长度不能超过500个字符"
                }
            },
            "dataset_path": {
                "required": False,
                "validate_path": True,
                "error_messages": {
                    "validate_path": "数据集路径不存在或不可访问"
                }
            },
            "epochs": {
                "required": False,
                "default": 50,
                "min_value": 1,
                "max_value": 1000,
                "error_messages": {
                    "min_value": "训练轮数不能少于1",
                    "max_value": "训练轮数不能超过1000"
                }
            },
            "batch_size": {
                "required": False,
                "default": 8,
                "min_value": 1,
                "max_value": 64,
                "error_messages": {
                    "min_value": "批次大小不能少于1",
                    "max_value": "批次大小不能超过64"
                }
            }
        }
    
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
        # 创建操作上下文
        context = self.create_operation_context(
            "create_training_task",
            task_name=task_name,
            task_description=task_description,
            dataset_path=dataset_path,
            epochs=epochs,
            batch_size=batch_size
        )
        
        try:
            # 参数验证
            validation_result = self._validate_creation_parameters(
                task_name, task_description, dataset_path, epochs, batch_size
            )
            
            if not validation_result["valid"]:
                error_message = ", ".join(validation_result["errors"])
                self.log_operation("error", f"参数验证失败: {error_message}")
                
                # 完成操作上下文（失败）
                self.complete_operation_context(context, False, error=error_message)
                self._notify_event("task_creation_failed", {
                    "task_name": task_name,
                    "errors": validation_result["errors"]
                })
                
                return None
            
            # 检查任务名称是否已存在
            if self._is_task_name_exists(task_name):
                error_message = f"任务名称 '{task_name}' 已存在"
                self.log_operation("error", error_message)
                
                self.complete_operation_context(context, False, error=error_message)
                self._notify_event("task_creation_failed", {
                    "task_name": task_name,
                    "error": error_message
                })
                
                return None
            
            # 创建任务文件夹结构
            task_dir = self._create_task_directory_safe(task_name)
            
            # 创建数据集目录
            if dataset_path and os.path.exists(dataset_path):
                # 如果提供了数据集路径，复制到任务目录
                self._copy_dataset_safe(dataset_path, task_dir)
            else:
                # 否则创建空的数据集结构
                create_default_dataset_structure(task_dir)
            
            # 创建data.yaml配置文件
            self._create_data_yaml_safe(task_dir, task_name)
            
            # 在数据库中创建任务记录
            task_id = self._create_database_record(
                task_name, task_description, task_dir, epochs, batch_size
            )
            
            if task_id is None:
                # 清理已创建的文件
                self._cleanup_on_failure(task_dir)
                
                self.complete_operation_context(context, False, error="数据库记录创建失败")
                return None
            
            # 完成操作上下文（成功）
            self.complete_operation_context(context, True, result=task_id)
            
            self.log_operation("info", f"训练任务创建成功: {task_name} (ID: {task_id})")
            self._notify_event("task_created", {
                "task_id": task_id,
                "task_name": task_name,
                "task_dir": task_dir
            })
            
            return task_id
            
        except Exception as e:
            self.log_operation("error", f"创建训练任务失败: {str(e)}", exc_info=True)
            
            # 完成操作上下文（失败）
            self.complete_operation_context(context, False, error=str(e))
            self._notify_event("task_creation_error", {
                "task_name": task_name,
                "error": str(e)
            })
            
            return None
    
    # 参数验证方法
    
    def _validate_creation_parameters(self, task_name: str, task_description: str, 
                                    dataset_path: Optional[str], epochs: int, batch_size: int) -> Dict[str, Any]:
        """验证创建任务的参数
        
        Args:
            task_name: 任务名称
            task_description: 任务描述
            dataset_path: 数据集路径
            epochs: 训练轮数
            batch_size: 批次大小
            
        Returns:
            验证结果字典
        """
        validation_result = {
            "valid": True,
            "errors": [],
            "warnings": []
        }
        
        # 验证任务名称
        name_validation = self._validate_task_name(task_name)
        if not name_validation["valid"]:
            validation_result["valid"] = False
            validation_result["errors"].extend(name_validation["errors"])
        
        # 验证任务描述
        desc_validation = self._validate_task_description(task_description)
        if not desc_validation["valid"]:
            validation_result["warnings"].extend(desc_validation["warnings"])
        
        # 验证数据集路径
        if dataset_path:
            dataset_validation = self._validate_dataset_path(dataset_path)
            if not dataset_validation["valid"]:
                validation_result["valid"] = False
                validation_result["errors"].extend(dataset_validation["errors"])
        
        # 验证训练参数
        epochs_validation = self._validate_epochs(epochs)
        if not epochs_validation["valid"]:
            validation_result["valid"] = False
            validation_result["errors"].extend(epochs_validation["errors"])
        
        batch_validation = self._validate_batch_size(batch_size)
        if not batch_validation["valid"]:
            validation_result["valid"] = False
            validation_result["errors"].extend(batch_validation["errors"])
        
        return validation_result
    
    def _validate_task_name(self, task_name: str) -> Dict[str, Any]:
        """验证任务名称
        
        Args:
            task_name: 任务名称
            
        Returns:
            验证结果
        """
        rules = self.validation_rules["task_name"]
        result = {"valid": True, "errors": []}
        
        # 检查是否为空
        if not task_name or not task_name.strip():
            result["valid"] = False
            result["errors"].append(rules["error_messages"]["required"])
            return result
        
        # 检查长度
        if len(task_name) < rules["min_length"]:
            result["valid"] = False
            result["errors"].append(rules["error_messages"]["min_length"])
        
        if len(task_name) > rules["max_length"]:
            result["valid"] = False
            result["errors"].append(rules["error_messages"]["max_length"])
        
        # 检查格式
        if not re.match(rules["pattern"], task_name):
            result["valid"] = False
            result["errors"].append(rules["error_messages"]["pattern"])
        
        return result
    
    def _validate_task_description(self, task_description: str) -> Dict[str, Any]:
        """验证任务描述
        
        Args:
            task_description: 任务描述
            
        Returns:
            验证结果
        """
        rules = self.validation_rules["task_description"]
        result = {"valid": True, "warnings": []}
        
        if task_description and len(task_description) > rules["max_length"]:
            result["warnings"].append(rules["error_messages"]["max_length"])
        
        return result
    
    def _validate_dataset_path(self, dataset_path: str) -> Dict[str, Any]:
        """验证数据集路径
        
        Args:
            dataset_path: 数据集路径
            
        Returns:
            验证结果
        """
        rules = self.validation_rules["dataset_path"]
        result = {"valid": True, "errors": []}
        
        if not os.path.exists(dataset_path):
            result["valid"] = False
            result["errors"].append(rules["error_messages"]["validate_path"])
        elif not os.access(dataset_path, os.R_OK):
            result["valid"] = False
            result["errors"].append("数据集路径不可读")
        
        return result
    
    def _validate_epochs(self, epochs: int) -> Dict[str, Any]:
        """验证训练轮数
        
        Args:
            epochs: 训练轮数
            
        Returns:
            验证结果
        """
        rules = self.validation_rules["epochs"]
        result = {"valid": True, "errors": []}
        
        if epochs < rules["min_value"]:
            result["valid"] = False
            result["errors"].append(rules["error_messages"]["min_value"])
        
        if epochs > rules["max_value"]:
            result["valid"] = False
            result["errors"].append(rules["error_messages"]["max_value"])
        
        return result
    
    def _validate_batch_size(self, batch_size: int) -> Dict[str, Any]:
        """验证批次大小
        
        Args:
            batch_size: 批次大小
            
        Returns:
            验证结果
        """
        rules = self.validation_rules["batch_size"]
        result = {"valid": True, "errors": []}
        
        if batch_size < rules["min_value"]:
            result["valid"] = False
            result["errors"].append(rules["error_messages"]["min_value"])
        
        if batch_size > rules["max_value"]:
            result["valid"] = False
            result["errors"].append(rules["error_messages"]["max_value"])
        
        return result
    
    def _is_task_name_exists(self, task_name: str) -> bool:
        """检查任务名称是否已存在
        
        Args:
            task_name: 任务名称
            
        Returns:
            是否存在
        """
        session = db_manager.get_session()
        try:
            existing_task = session.query(TrainingTask).filter_by(task_name=task_name).first()
            return existing_task is not None
        finally:
            session.close()
    
    # 安全操作方法
    
    def _create_task_directory_safe(self, task_name: str) -> str:
        """安全创建任务目录
        
        Args:
            task_name: 任务名称
            
        Returns:
            任务目录路径
        """
        try:
            return create_task_directory(task_name)
        except Exception as e:
            self.log_operation("error", f"创建任务目录失败: {str(e)}")
            raise
    
    def _copy_dataset_safe(self, source_path: str, target_dir: str) -> None:
        """安全复制数据集
        
        Args:
            source_path: 源路径
            target_dir: 目标目录
        """
        try:
            copy_dataset(source_path, target_dir)
        except Exception as e:
            self.log_operation("error", f"复制数据集失败: {str(e)}")
            raise
    
    def _create_data_yaml_safe(self, task_dir: str, task_name: str) -> None:
        """安全创建数据配置文件
        
        Args:
            task_dir: 任务目录
            task_name: 任务名称
        """
        try:
            create_data_yaml(task_dir, task_name)
        except Exception as e:
            self.log_operation("error", f"创建数据配置文件失败: {str(e)}")
            raise
    
    def _create_database_record(self, task_name: str, task_description: str, 
                              task_dir: str, epochs: int, batch_size: int) -> Optional[int]:
        """创建数据库记录
        
        Args:
            task_name: 任务名称
            task_description: 任务描述
            task_dir: 任务目录
            epochs: 训练轮数
            batch_size: 批次大小
            
        Returns:
            任务ID，失败时返回None
        """
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
            
            return training_task.id
            
        except Exception as e:
            self.log_operation("error", f"创建训练任务数据库记录失败: {str(e)}", exc_info=True)
            session.rollback()
            return None
            
        finally:
            session.close()
    
    def _cleanup_on_failure(self, task_dir: str) -> None:
        """失败时清理已创建的文件
        
        Args:
            task_dir: 任务目录
        """
        try:
            if os.path.exists(task_dir):
                shutil.rmtree(task_dir)
                self.log_operation("info", f"清理任务目录: {task_dir}")
        except Exception as e:
            self.log_operation("warning", f"清理任务目录失败: {task_dir} - {str(e)}")
    
    # IErrorHandler接口实现
    
    def _handle_database_error(self, error: Exception, operation: str, 
                             task_id: int = None) -> Dict[str, Any]:
        """处理数据库错误
        
        Args:
            error: 错误对象
            operation: 操作名称
            task_id: 任务ID（可选）
            
        Returns:
            错误响应
        """
        return super()._handle_database_error(error, operation, task_id)
    
    def _handle_file_operation_error(self, error: Exception, operation: str, 
                                   file_path: str = None) -> Dict[str, Any]:
        """处理文件操作错误
        
        Args:
            error: 错误对象
            operation: 操作名称
            file_path: 文件路径（可选）
            
        Returns:
            错误响应
        """
        return super()._handle_file_operation_error(error, operation, file_path)
    
    def validate_file_path(self, file_path: str, check_exists: bool = True, 
                          check_readable: bool = False, check_writable: bool = False) -> Dict[str, Any]:
        """验证文件路径
        
        Args:
            file_path: 文件路径
            check_exists: 检查文件是否存在
            check_readable: 检查文件是否可读
            check_writable: 检查文件是否可写
            
        Returns:
            验证结果
        """
        return super().validate_file_path(file_path, check_exists, check_readable, check_writable)