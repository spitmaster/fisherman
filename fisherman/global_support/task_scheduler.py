#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
全局支撑模块 - 任务调度中心

负责统一调度训练/识别任务，避免资源冲突，确保任务按计划执行。

主要功能：
- 任务队列管理
- 任务调度策略
- 资源分配管理
- 任务状态监控
"""

import os
import sys
import logging
import threading
import time
from datetime import datetime
from enum import Enum

# 日志配置
logger = logging.getLogger(__name__)

class TaskType(Enum):
    """任务类型枚举"""
    TRAINING = "training"
    RECOGNITION = "recognition"

class TaskStatus(Enum):
    """任务状态枚举"""
    PENDING = "pending"
    RUNNING = "running"
    PAUSED = "paused"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"

class Task:
    """任务基类"""
    
    def __init__(self, task_id, task_type, task_name, priority=1):
        """初始化任务
        
        Args:
            task_id: 任务唯一标识符
            task_type: 任务类型（TRAINING或RECOGNITION）
            task_name: 任务名称
            priority: 任务优先级（1-5，数字越小优先级越高）
        """
        self.task_id = task_id
        self.task_type = task_type
        self.task_name = task_name
        self.priority = priority
        self.status = TaskStatus.PENDING
        self.created_at = datetime.now()
        self.started_at = None
        self.completed_at = None
        self.result = None
        self.error = None
        
        # 任务执行的回调函数
        self.on_start = None
        self.on_progress = None
        self.on_completed = None
        self.on_error = None
        
    def start(self):
        """启动任务"""
        if self.status == TaskStatus.PENDING:
            self.status = TaskStatus.RUNNING
            self.started_at = datetime.now()
            logger.info(f"任务启动: {self.task_name} (ID: {self.task_id})")
            
            if self.on_start:
                self.on_start(self)
                
    def pause(self):
        """暂停任务"""
        if self.status == TaskStatus.RUNNING:
            self.status = TaskStatus.PAUSED
            logger.info(f"任务暂停: {self.task_name} (ID: {self.task_id})")
            
    def resume(self):
        """恢复任务"""
        if self.status == TaskStatus.PAUSED:
            self.status = TaskStatus.RUNNING
            logger.info(f"任务恢复: {self.task_name} (ID: {self.task_id})")
            
    def complete(self, result=None):
        """完成任务"""
        if self.status in [TaskStatus.RUNNING, TaskStatus.PAUSED]:
            self.status = TaskStatus.COMPLETED
            self.completed_at = datetime.now()
            self.result = result
            logger.info(f"任务完成: {self.task_name} (ID: {self.task_id})")
            
            if self.on_completed:
                self.on_completed(self, result)
                
    def fail(self, error):
        """任务失败"""
        if self.status in [TaskStatus.RUNNING, TaskStatus.PAUSED]:
            self.status = TaskStatus.FAILED
            self.completed_at = datetime.now()
            self.error = error
            logger.error(f"任务失败: {self.task_name} (ID: {self.task_id}) - {str(error)}")
            
            if self.on_error:
                self.on_error(self, error)
                
    def cancel(self):
        """取消任务"""
        if self.status in [TaskStatus.PENDING, TaskStatus.RUNNING, TaskStatus.PAUSED]:
            self.status = TaskStatus.CANCELLED
            self.completed_at = datetime.now()
            logger.info(f"任务取消: {self.task_name} (ID: {self.task_id})")
            
    def update_progress(self, progress, message=""):
        """更新任务进度"""
        if self.status == TaskStatus.RUNNING and self.on_progress:
            self.on_progress(self, progress, message)
            
    def get_duration(self):
        """获取任务执行时间"""
        if self.started_at:
            end_time = self.completed_at or datetime.now()
            return end_time - self.started_at
        return None

class TaskScheduler:
    """任务调度器"""
    
    def __init__(self):
        """初始化任务调度器"""
        self.task_queue = []
        self.running_tasks = []
        self.max_concurrent_tasks = 1  # 默认最大并发任务数
        self.scheduler_running = False
        self.scheduler_thread = None
        self.condition = threading.Condition()
        
        logger.info("任务调度器初始化完成")
        
    def add_task(self, task):
        """添加任务到调度队列
        
        Args:
            task: 要添加的任务对象
        """
        with self.condition:
            self.task_queue.append(task)
            self.task_queue.sort(key=lambda x: (x.priority, x.created_at))
            logger.info(f"任务添加到队列: {task.task_name} (ID: {task.task_id})")
            self.condition.notify()
            
    def remove_task(self, task_id):
        """从队列中移除任务
        
        Args:
            task_id: 要移除的任务ID
        """
        with self.condition:
            self.task_queue = [task for task in self.task_queue if task.task_id != task_id]
            logger.info(f"任务从队列中移除: {task_id}")
            
    def get_task(self, task_id):
        """获取任务
        
        Args:
            task_id: 任务ID
            
        Returns:
            Task对象或None
        """
        with self.condition:
            # 先在运行任务中查找
            for task in self.running_tasks:
                if task.task_id == task_id:
                    return task
                    
            # 再在队列中查找
            for task in self.task_queue:
                if task.task_id == task_id:
                    return task
                    
            return None
            
    def get_all_tasks(self):
        """获取所有任务"""
        with self.condition:
            return self.running_tasks + self.task_queue
            
    def get_task_queue_length(self):
        """获取队列长度"""
        with self.condition:
            return len(self.task_queue)
            
    def get_running_tasks_count(self):
        """获取运行中任务数"""
        with self.condition:
            return len(self.running_tasks)
            
    def set_max_concurrent_tasks(self, max_tasks):
        """设置最大并发任务数
        
        Args:
            max_tasks: 最大并发任务数
        """
        with self.condition:
            self.max_concurrent_tasks = max_tasks
            logger.info(f"最大并发任务数设置为: {self.max_concurrent_tasks}")
            self.condition.notify()
            
    def start_scheduler(self):
        """启动调度器"""
        if not self.scheduler_running:
            self.scheduler_running = True
            self.scheduler_thread = threading.Thread(target=self._scheduler_loop, daemon=True)
            self.scheduler_thread.start()
            logger.info("任务调度器启动成功")
            
    def stop_scheduler(self):
        """停止调度器"""
        self.scheduler_running = False
        if self.scheduler_thread:
            self.scheduler_thread.join()
            self.scheduler_thread = None
        logger.info("任务调度器停止")
            
    def _scheduler_loop(self):
        """调度器主循环"""
        while self.scheduler_running:
            with self.condition:
                # 检查是否可以启动新任务
                while (len(self.running_tasks) < self.max_concurrent_tasks and
                       len(self.task_queue) > 0):
                    # 取出优先级最高的任务
                    task = self.task_queue.pop(0)
                    self.running_tasks.append(task)
                    
                    # 启动任务执行线程
                    task_thread = threading.Thread(target=self._execute_task, args=(task,), daemon=True)
                    task_thread.start()
                    
                # 等待条件变化
                self.condition.wait(timeout=1)
                
    def _execute_task(self, task):
        """执行任务的线程函数
        
        Args:
            task: 要执行的任务对象
        """
        try:
            # 启动任务
            task.start()
            
            # 执行任务逻辑（需要子类实现）
            if hasattr(task, 'run'):
                task.run()
            else:
                logger.warning(f"任务 {task.task_name} 没有实现run方法")
                
        except Exception as e:
            logger.error(f"任务执行错误: {task.task_name} - {str(e)}", exc_info=True)
            task.fail(e)
            
        finally:
            # 任务完成后从运行任务列表中移除
            with self.condition:
                if task in self.running_tasks:
                    self.running_tasks.remove(task)
                self.condition.notify()
            
class TrainingTask(Task):
    """训练任务类"""
    
    def __init__(self, task_id, task_name, dataset_path, model_path, epochs=50, batch_size=8, priority=1):
        """初始化训练任务
        
        Args:
            task_id: 任务ID
            task_name: 任务名称
            dataset_path: 数据集路径
            model_path: 模型路径
            epochs: 训练轮数
            batch_size: 批次大小
            priority: 优先级
        """
        super().__init__(task_id, TaskType.TRAINING, task_name, priority)
        self.dataset_path = dataset_path
        self.model_path = model_path
        self.epochs = epochs
        self.batch_size = batch_size
        
    def run(self):
        """运行训练任务"""
        try:
            logger.info(f"开始训练任务: {self.task_name}")
            
            # 这里应该调用训练模块的实际训练逻辑
            # 模拟训练过程
            for epoch in range(self.epochs):
                if self.status in [TaskStatus.CANCELLED, TaskStatus.FAILED]:
                    break
                    
                self.update_progress((epoch + 1) / self.epochs, f"Epoch {epoch + 1}/{self.epochs}")
                time.sleep(0.1)
                
            self.complete("训练完成")
            
        except Exception as e:
            self.fail(e)
            
class RecognitionTask(Task):
    """识别任务类"""
    
    def __init__(self, task_id, task_name, model_path, confidence_threshold=0.7, click_cooldown=5, priority=1):
        """初始化识别任务
        
        Args:
            task_id: 任务ID
            task_name: 任务名称
            model_path: 模型路径
            confidence_threshold: 置信度阈值
            click_cooldown: 点击冷却时间（秒）
            priority: 优先级
        """
        super().__init__(task_id, TaskType.RECOGNITION, task_name, priority)
        self.model_path = model_path
        self.confidence_threshold = confidence_threshold
        self.click_cooldown = click_cooldown
        
    def run(self):
        """运行识别任务"""
        try:
            logger.info(f"开始识别任务: {self.task_name}")
            
            # 这里应该调用识别模块的实际识别逻辑
            # 模拟识别过程
            recognition_count = 0
            click_count = 0
            
            while self.status == TaskStatus.RUNNING:
                recognition_count += 1
                
                # 模拟识别到目标的概率
                if recognition_count % 10 == 0:
                    click_count += 1
                    self.update_progress(recognition_count, f"识别到 {click_count} 个目标")
                    
                time.sleep(1)
                
            if self.status != TaskStatus.FAILED:
                self.complete(f"识别任务停止，共识别 {recognition_count} 次，点击 {click_count} 次")
                
        except Exception as e:
            self.fail(e)

# 全局任务调度器实例
task_scheduler = TaskScheduler()