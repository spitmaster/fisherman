#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
训练回调处理器

处理训练过程中的各种回调事件，如进度更新、状态变更等。
"""

import logging
from typing import Dict, Any, Callable

from ..core.base_manager import BaseManager

# 日志配置
logger = logging.getLogger(__name__)


class TrainingCallbackHandler(BaseManager):
    """训练回调处理器"""
    
    def __init__(self):
        """初始化回调处理器"""
        super().__init__()
        self.callbacks = {
            "on_training_start": [],
            "on_training_progress": [],
            "on_training_completed": [],
            "on_training_error": [],
            "on_epoch_end": [],
            "on_batch_end": []
        }
        
    def register_callback(self, event_type: str, callback: Callable) -> bool:
        """注册回调函数
        
        Args:
            event_type: 事件类型
            callback: 回调函数
            
        Returns:
            注册是否成功
        """
        if event_type not in self.callbacks:
            self.log_operation("error", f"未知的事件类型: {event_type}")
            return False
            
        self.callbacks[event_type].append(callback)
        self.log_operation("debug", f"回调函数注册成功: {event_type}")
        return True
        
    def trigger_callbacks(self, event_type: str, *args, **kwargs) -> None:
        """触发指定事件类型的回调函数
        
        Args:
            event_type: 事件类型
            *args: 回调函数参数
            **kwargs: 回调函数关键字参数
        """
        if event_type not in self.callbacks:
            self.log_operation("warning", f"未知的事件类型: {event_type}")
            return
            
        callbacks = self.callbacks[event_type]
        if not callbacks:
            return
            
        for callback in callbacks:
            try:
                callback(*args, **kwargs)
            except Exception as e:
                self.log_operation("error", f"回调函数执行失败: {callback.__name__} - {str(e)}", exc_info=True)
                
    def on_training_start(self, task_id: int, task_info: Dict[str, Any]) -> None:
        """训练开始回调
        
        Args:
            task_id: 任务ID
            task_info: 任务信息
        """
        self.log_operation("info", f"训练开始: 任务 {task_id}")
        self.trigger_callbacks("on_training_start", task_id, task_info)
        
    def on_training_progress(self, task_id: int, progress: float, message: str = "") -> None:
        """训练进度回调
        
        Args:
            task_id: 任务ID
            progress: 进度百分比 (0-100)
            message: 进度消息
        """
        self.log_operation("debug", f"训练进度: 任务 {task_id}, 进度 {progress}%, {message}")
        self.trigger_callbacks("on_training_progress", task_id, progress, message)
        
    def on_training_completed(self, task_id: int, result: Dict[str, Any]) -> None:
        """训练完成回调
        
        Args:
            task_id: 任务ID
            result: 训练结果
        """
        self.log_operation("info", f"训练完成: 任务 {task_id}")
        self.trigger_callbacks("on_training_completed", task_id, result)
        
    def on_training_error(self, task_id: int, error: str) -> None:
        """训练错误回调
        
        Args:
            task_id: 任务ID
            error: 错误信息
        """
        self.log_operation("error", f"训练错误: 任务 {task_id}, 错误: {error}")
        self.trigger_callbacks("on_training_error", task_id, error)
        
    def on_epoch_end(self, task_id: int, epoch: int, total_epochs: int, metrics: Dict[str, Any]) -> None:
        """训练轮次结束回调
        
        Args:
            task_id: 任务ID
            epoch: 当前轮次
            total_epochs: 总轮次数
            metrics: 训练指标
        """
        progress_percentage = (epoch / total_epochs) * 100 if total_epochs > 0 else 0
        self.log_operation("debug", f"训练轮次结束: 任务 {task_id}, 轮次 {epoch}/{total_epochs}")
        self.trigger_callbacks("on_epoch_end", task_id, epoch, total_epochs, metrics)
        self.on_training_progress(task_id, progress_percentage, f"轮次 {epoch}/{total_epochs}")
        
    def on_batch_end(self, task_id: int, batch: int, total_batches: int, loss: float) -> None:
        """训练批次结束回调
        
        Args:
            task_id: 任务ID
            batch: 当前批次
            total_batches: 总批次数
            loss: 损失值
        """
        self.trigger_callbacks("on_batch_end", task_id, batch, total_batches, loss)
        
    def clear_callbacks(self, event_type: str = None) -> None:
        """清除回调函数
        
        Args:
            event_type: 事件类型，如果为None则清除所有回调
        """
        if event_type is None:
            for key in self.callbacks:
                self.callbacks[key] = []
            self.log_operation("info", "所有回调函数已清除")
        elif event_type in self.callbacks:
            self.callbacks[event_type] = []
            self.log_operation("info", f"回调函数已清除: {event_type}")
        else:
            self.log_operation("warning", f"未知的事件类型: {event_type}")