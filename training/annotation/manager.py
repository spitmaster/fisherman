#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
标注管理器模块

提供标注任务的统一管理、调度和并发控制功能。
支持任务队列管理、进度监控、回调通知等高级特性。
"""

import os
import time
import threading
import queue
import logging
from typing import Dict, List, Optional, Any, Callable
from concurrent.futures import ThreadPoolExecutor, Future
from enum import Enum

from ..core.base_manager import BaseManager
from ..core.interfaces import ICallbackManager, IEventManager, IErrorHandler
from .tool import AnnotationTool
from .validator import validate_dataset_annotations, get_annotation_statistics

# 日志配置
logger = logging.getLogger(__name__)


class AnnotationTaskStatus(Enum):
    """标注任务状态枚举"""
    PENDING = "pending"      # 等待中
    RUNNING = "running"      # 运行中
    PAUSED = "paused"        # 已暂停
    COMPLETED = "completed"  # 已完成
    FAILED = "failed"        # 已失败
    CANCELLED = "cancelled"  # 已取消


class AnnotationTask:
    """标注任务类
    
    封装单个标注任务的信息和状态
    """
    
    def __init__(self, task_id: int, task_name: str, dataset_path: str, 
                 image_files: List[str], callback: Optional[Callable] = None):
        """初始化标注任务
        
        Args:
            task_id: 任务ID
            task_name: 任务名称
            dataset_path: 数据集路径
            image_files: 图片文件列表
            callback: 回调函数
        """
        self.task_id = task_id
        self.task_name = task_name
        self.dataset_path = dataset_path
        self.image_files = image_files
        self.callback = callback
        self.status = AnnotationTaskStatus.PENDING
        self.progress = 0.0  # 进度百分比
        self.current_image = ""
        self.start_time = None
        self.end_time = None
        self.error_message = ""
        
    def update_progress(self, progress: float, current_image: str = ""):
        """更新任务进度
        
        Args:
            progress: 进度百分比 (0-100)
            current_image: 当前处理的图片
        """
        self.progress = max(0.0, min(100.0, progress))
        self.current_image = current_image
        
    def set_status(self, status: AnnotationTaskStatus, error_message: str = ""):
        """设置任务状态
        
        Args:
            status: 任务状态
            error_message: 错误信息
        """
        self.status = status
        self.error_message = error_message
        
        if status == AnnotationTaskStatus.RUNNING and self.start_time is None:
            self.start_time = time.time()
        elif status in [AnnotationTaskStatus.COMPLETED, AnnotationTaskStatus.FAILED, AnnotationTaskStatus.CANCELLED]:
            self.end_time = time.time()


class AnnotationManager(BaseManager, ICallbackManager, IEventManager, IErrorHandler):
    """标注管理器
    
    提供完整的标注任务调度、并发控制和状态管理功能。
    """
    
    def __init__(self, max_workers: int = 2):
        """初始化标注管理器
        
        Args:
            max_workers: 最大并发工作线程数
        """
        super().__init__("annotation_manager")
        
        # 线程池配置
        self.max_workers = max_workers
        self.executor = ThreadPoolExecutor(max_workers=max_workers)
        
        # 任务管理
        self.tasks: Dict[int, AnnotationTask] = {}  # 任务ID -> 任务对象
        self.task_queue = queue.Queue()  # 任务队列
        self.running_tasks: Dict[int, Future] = {}  # 运行中的任务
        
        # 状态管理
        self.is_running = False
        self._lock = threading.RLock()  # 重入锁，用于线程安全
        
        # 回调系统
        self.callbacks: Dict[str, List[Callable]] = {
            "task_started": [],
            "task_progress": [],
            "task_completed": [],
            "task_failed": [],
            "task_cancelled": []
        }
        
        # 启动任务调度器
        self._start_scheduler()
    
    def create_annotation_task(self, task_id: int, task_name: str, dataset_path: str, 
                              image_files: List[str]) -> bool:
        """创建新的标注任务
        
        Args:
            task_id: 任务ID
            task_name: 任务名称
            dataset_path: 数据集路径
            image_files: 图片文件列表
            
        Returns:
            是否创建成功
        """
        # 创建操作上下文
        context = self.create_operation_context(
            "create_annotation_task",
            task_id=task_id,
            task_name=task_name,
            dataset_path=dataset_path,
            image_count=len(image_files)
        )
        
        try:
            # 验证参数
            if not self._validate_task_parameters(task_id, task_name, dataset_path, image_files):
                error_message = "参数验证失败"
                self.log_operation("error", error_message)
                self.complete_operation_context(context, False, error=error_message)
                return False
            
            # 检查任务是否已存在
            if task_id in self.tasks:
                error_message = f"任务ID {task_id} 已存在"
                self.log_operation("error", error_message)
                self.complete_operation_context(context, False, error=error_message)
                return False
            
            # 创建任务对象
            task = AnnotationTask(task_id, task_name, dataset_path, image_files)
            
            # 添加到任务字典和队列
            with self._lock:
                self.tasks[task_id] = task
                self.task_queue.put(task_id)
            
            self.log_operation("info", f"创建标注任务成功: {task_name} (ID: {task_id})")
            self.complete_operation_context(context, True, result=task_id)
            
            # 通知任务创建事件
            self._notify_event("task_created", {
                "task_id": task_id,
                "task_name": task_name,
                "image_count": len(image_files)
            })
            
            return True
            
        except Exception as e:
            self.log_operation("error", f"创建标注任务失败: {str(e)}", exc_info=True)
            self.complete_operation_context(context, False, error=str(e))
            return False
    
    def start_task(self, task_id: int) -> bool:
        """启动标注任务
        
        Args:
            task_id: 任务ID
            
        Returns:
            是否启动成功
        """
        with self._lock:
            if task_id not in self.tasks:
                self.log_operation("error", f"任务ID {task_id} 不存在")
                return False
            
            task = self.tasks[task_id]
            
            if task.status != AnnotationTaskStatus.PENDING:
                self.log_operation("warning", f"任务 {task_id} 状态为 {task.status.value}，无法启动")
                return False
            
            # 提交任务到线程池
            future = self.executor.submit(self._execute_annotation_task, task)
            self.running_tasks[task_id] = future
            task.set_status(AnnotationTaskStatus.RUNNING)
            
            self.log_operation("info", f"启动标注任务: {task.task_name} (ID: {task_id})")
            
            # 通知任务启动事件
            self._notify_callbacks("task_started", task_id, task.task_name)
            
            return True
    
    def pause_task(self, task_id: int) -> bool:
        """暂停标注任务
        
        Args:
            task_id: 任务ID
            
        Returns:
            是否暂停成功
        """
        with self._lock:
            if task_id not in self.tasks:
                return False
            
            task = self.tasks[task_id]
            
            if task.status != AnnotationTaskStatus.RUNNING:
                return False
            
            task.set_status(AnnotationTaskStatus.PAUSED)
            self.log_operation("info", f"暂停标注任务: {task.task_name} (ID: {task_id})")
            
            return True
    
    def resume_task(self, task_id: int) -> bool:
        """恢复标注任务
        
        Args:
            task_id: 任务ID
            
        Returns:
            是否恢复成功
        """
        with self._lock:
            if task_id not in self.tasks:
                return False
            
            task = self.tasks[task_id]
            
            if task.status != AnnotationTaskStatus.PAUSED:
                return False
            
            task.set_status(AnnotationTaskStatus.RUNNING)
            self.log_operation("info", f"恢复标注任务: {task.task_name} (ID: {task_id})")
            
            return True
    
    def cancel_task(self, task_id: int) -> bool:
        """取消标注任务
        
        Args:
            task_id: 任务ID
            
        Returns:
            是否取消成功
        """
        with self._lock:
            if task_id not in self.tasks:
                return False
            
            task = self.tasks[task_id]
            
            if task.status in [AnnotationTaskStatus.COMPLETED, AnnotationTaskStatus.FAILED, AnnotationTaskStatus.CANCELLED]:
                return False
            
            # 如果任务正在运行，取消future
            if task_id in self.running_tasks:
                future = self.running_tasks[task_id]
                future.cancel()
                del self.running_tasks[task_id]
            
            task.set_status(AnnotationTaskStatus.CANCELLED, "用户取消")
            self.log_operation("info", f"取消标注任务: {task.task_name} (ID: {task_id})")
            
            # 通知任务取消事件
            self._notify_callbacks("task_cancelled", task_id, task.task_name)
            
            return True
    
    def get_task_status(self, task_id: int) -> Optional[Dict[str, Any]]:
        """获取任务状态信息
        
        Args:
            task_id: 任务ID
            
        Returns:
            任务状态信息字典，任务不存在时返回None
        """
        with self._lock:
            if task_id not in self.tasks:
                return None
            
            task = self.tasks[task_id]
            
            return {
                "task_id": task.task_id,
                "task_name": task.task_name,
                "status": task.status.value,
                "progress": task.progress,
                "current_image": task.current_image,
                "start_time": task.start_time,
                "end_time": task.end_time,
                "error_message": task.error_message
            }
    
    def get_all_tasks_status(self) -> List[Dict[str, Any]]:
        """获取所有任务状态信息
        
        Returns:
            所有任务状态信息列表
        """
        with self._lock:
            return [self.get_task_status(task_id) for task_id in self.tasks.keys()]
    
    # 调度器方法
    
    def _start_scheduler(self):
        """启动任务调度器"""
        self.is_running = True
        scheduler_thread = threading.Thread(target=self._scheduler_loop, daemon=True)
        scheduler_thread.start()
        self.log_operation("info", "标注任务调度器已启动")
    
    def _scheduler_loop(self):
        """调度器主循环"""
        while self.is_running:
            try:
                # 从队列获取任务ID
                task_id = self.task_queue.get(timeout=1.0)
                
                # 检查任务状态
                with self._lock:
                    if task_id not in self.tasks:
                        continue
                    
                    task = self.tasks[task_id]
                    
                    # 如果任务不是等待状态，跳过
                    if task.status != AnnotationTaskStatus.PENDING:
                        continue
                    
                    # 检查线程池容量
                    if len(self.running_tasks) >= self.max_workers:
                        # 线程池已满，将任务放回队列
                        self.task_queue.put(task_id)
                        continue
                
                # 启动任务
                self.start_task(task_id)
                
            except queue.Empty:
                # 队列为空，继续等待
                continue
            except Exception as e:
                self.log_operation("error", f"调度器错误: {str(e)}", exc_info=True)
    
    def _execute_annotation_task(self, task: AnnotationTask):
        """执行标注任务
        
        Args:
            task: 标注任务对象
        """
        try:
            # 创建标注工具
            annotation_tool = AnnotationTool(
                {"id": task.task_id, "name": task.task_name},
                task.image_files,
                0  # 从0开始标注
            )
            
            total_images = len(task.image_files)
            
            # 遍历所有图片进行标注
            for i, image_file in enumerate(task.image_files):
                # 检查任务是否被取消或暂停
                with self._lock:
                    if task.status == AnnotationTaskStatus.CANCELLED:
                        return
                    elif task.status == AnnotationTaskStatus.PAUSED:
                        # 等待任务恢复
                        while task.status == AnnotationTaskStatus.PAUSED:
                            time.sleep(0.5)
                            if task.status == AnnotationTaskStatus.CANCELLED:
                                return
                
                # 更新进度
                progress = (i / total_images) * 100
                task.update_progress(progress, os.path.basename(image_file))
                
                # 模拟标注过程（实际应该调用标注工具）
                time.sleep(0.1)  # 模拟处理时间
                
                # 通知进度更新
                self._notify_callbacks("task_progress", task.task_id, task.task_name, progress, task.current_image)
            
            # 任务完成
            task.update_progress(100.0)
            task.set_status(AnnotationTaskStatus.COMPLETED)
            
            with self._lock:
                if task.task_id in self.running_tasks:
                    del self.running_tasks[task.task_id]
            
            self.log_operation("info", f"标注任务完成: {task.task_name} (ID: {task.task_id})")
            
            # 通知任务完成事件
            self._notify_callbacks("task_completed", task.task_id, task.task_name)
            
        except Exception as e:
            # 任务失败
            task.set_status(AnnotationTaskStatus.FAILED, str(e))
            
            with self._lock:
                if task.task_id in self.running_tasks:
                    del self.running_tasks[task.task_id]
            
            self.log_operation("error", f"标注任务失败: {task.task_name} (ID: {task.task_id}) - {str(e)}", exc_info=True)
            
            # 通知任务失败事件
            self._notify_callbacks("task_failed", task.task_id, task.task_name, str(e))
    
    # 参数验证方法
    
    def _validate_task_parameters(self, task_id: int, task_name: str, dataset_path: str, image_files: List[str]) -> bool:
        """验证任务参数
        
        Args:
            task_id: 任务ID
            task_name: 任务名称
            dataset_path: 数据集路径
            image_files: 图片文件列表
            
        Returns:
            参数是否有效
        """
        # 验证任务ID
        if not isinstance(task_id, int) or task_id <= 0:
            return False
        
        # 验证任务名称
        if not isinstance(task_name, str) or not task_name.strip():
            return False
        
        # 验证数据集路径
        if not isinstance(dataset_path, str) or not os.path.exists(dataset_path):
            return False
        
        # 验证图片文件列表
        if not isinstance(image_files, list) or len(image_files) == 0:
            return False
        
        # 验证每个图片文件是否存在
        for image_file in image_files:
            if not isinstance(image_file, str) or not os.path.exists(image_file):
                return False
        
        return True
    
    # 回调系统方法
    
    def _notify_callbacks(self, event_type: str, task_id: int, task_name: str, *args, **kwargs):
        """通知回调函数
        
        Args:
            event_type: 事件类型
            task_id: 任务ID
            task_name: 任务名称
            *args: 额外参数
            **kwargs: 关键字参数
        """
        if event_type in self.callbacks:
            for callback in self.callbacks[event_type]:
                try:
                    callback(task_id, task_name, *args, **kwargs)
                except Exception as e:
                    self.log_operation("error", f"回调函数执行失败: {str(e)}", exc_info=True)
    
    # ICallbackManager接口实现
    
    def register_callback(self, event_type: str, callback: Callable) -> bool:
        """注册回调函数
        
        Args:
            event_type: 事件类型
            callback: 回调函数
            
        Returns:
            是否注册成功
        """
        if event_type not in self.callbacks:
            return False
        
        self.callbacks[event_type].append(callback)
        return True
    
    def unregister_callback(self, event_type: str, callback: Callable) -> bool:
        """注销回调函数
        
        Args:
            event_type: 事件类型
            callback: 回调函数
            
        Returns:
            是否注销成功
        """
        if event_type not in self.callbacks:
            return False
        
        if callback in self.callbacks[event_type]:
            self.callbacks[event_type].remove(callback)
            return True
        
        return False
    
    # 原有的标注工具相关方法
    
    def create_annotation_tool(self, task_info, image_files, annotated_count):
        """创建标注工具实例
        
        Args:
            task_info: 任务信息
            image_files: 图片文件列表
            annotated_count: 已标注图片数量
            
        Returns:
            标注工具实例
        """
        return AnnotationTool(task_info, image_files, annotated_count)
        
    def validate_dataset_annotations(self, task_dir):
        """验证数据集的标注数据
        
        Args:
            task_dir: 任务目录
            
        Returns:
            验证结果
        """
        return validate_dataset_annotations(task_dir)
        
    def get_dataset_annotation_statistics(self, task_dir):
        """获取数据集标注统计信息
        
        Args:
            task_dir: 任务目录
            
        Returns:
            统计信息字典
        """
        return get_annotation_statistics(task_dir)
    
    # 清理资源
    
    def shutdown(self):
        """关闭标注管理器，释放资源"""
        self.is_running = False
        
        # 取消所有运行中的任务
        with self._lock:
            for task_id in list(self.running_tasks.keys()):
                self.cancel_task(task_id)
        
        # 关闭线程池
        self.executor.shutdown(wait=True)
        
        self.log_operation("info", "标注管理器已关闭")